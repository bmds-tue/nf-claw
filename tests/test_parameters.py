import json
import math
import pathlib
from datetime import datetime
from pathlib import Path

import pytest

from runner import parameters, schema
from runner.errors import ErrorCode, NfclawError
from runner.schema import Param, ParamSchema

FIX = Path(__file__).parent / "fixtures"


def test_validate_params_flags_unknown():
    ps = schema.load_param_schema(FIX / "mini")
    errs = parameters.validate_params({"alnger": "star"}, ps)   # typo'd flag
    assert errs and "alnger" in errs[0] and "unknown" in errs[0]


def test_validate_params_accepts_known_and_valid_enum():
    ps = schema.load_param_schema(FIX / "mini")
    assert parameters.validate_params({"aligner": "star"}, ps) == []   # star is in the enum


def test_validate_params_flags_value_outside_enum():
    ps = schema.load_param_schema(FIX / "mini")
    errs = parameters.validate_params({"aligner": "bowtie"}, ps)   # not in (star, hisat2)
    assert errs and "must be one of" in errs[0] and "star" in errs[0]


def test_validate_params_boolean_enum_uses_json_literals(tmp_path):
    (tmp_path / "nextflow_schema.json").write_text(json.dumps(
        {"definitions": {"g": {"properties": {"flag": {"type": "boolean", "enum": [False]}}}}}))
    ps = schema.load_param_schema(tmp_path)
    assert parameters.validate_params(parameters.coerce_to_schema({"flag": "false"}, ps), ps) == []
    assert parameters.validate_params({"flag": False}, ps) == []     # native bool from a params-file → ok
    assert parameters.validate_params({"flag": "False"}, ps)         # Python casing → rejected
    assert parameters.validate_params({"flag": "true"}, ps)          # not in enum → rejected


def _schema_with_types(tmp_path):
    (tmp_path / "nextflow_schema.json").write_text(json.dumps({"definitions": {"g": {"properties": {
        "skip_busco": {"type": "boolean"},
        "max_cpus": {"type": "integer"},
        "ratio": {"type": "number"},
        "genome": {"type": "string"},
        "flexible": {"type": ["integer", "string"]},
    }}}}))
    return schema.load_param_schema(tmp_path)


def test_coerce_to_schema_converts_cli_strings_by_declared_type(tmp_path):
    ps = _schema_with_types(tmp_path)
    out = parameters.coerce_to_schema(
        {"skip_busco": "true", "max_cpus": "4", "ratio": "0.5",
         "genome": "GRCh38", "flexible": "7", "unknown_flag": "x"}, ps)
    assert out["skip_busco"] is True
    assert out["max_cpus"] == 4 and isinstance(out["max_cpus"], int)
    assert out["ratio"] == 0.5 and isinstance(out["ratio"], float)
    assert out["genome"] == "GRCh38"          # string param → untouched
    assert out["flexible"] == "7"             # union type → ambiguous → left for nf-schema
    assert out["unknown_flag"] == "x"         # not in schema → left


def test_coerce_to_schema_is_case_insensitive_and_safe(tmp_path):
    ps = _schema_with_types(tmp_path)
    assert parameters.coerce_to_schema({"skip_busco": "FALSE"}, ps)["skip_busco"] is False
    assert parameters.coerce_to_schema({"skip_busco": True}, ps)["skip_busco"] is True   # bare flag untouched
    # unparseable values are left as-is so nf-schema reports a precise error
    assert parameters.coerce_to_schema({"max_cpus": "lots"}, ps)["max_cpus"] == "lots"
    assert parameters.coerce_to_schema({"skip_busco": "maybe"}, ps)["skip_busco"] == "maybe"


def test_merge_resolve_and_write(tmp_path):
    ps = schema.load_param_schema(FIX / "mini")
    merged = parameters.merge(cli_overrides={"aligner": "hisat2"}, params_file=None,
                              input_path=Path("rel/ss.csv"), outdir=tmp_path / "out")
    resolved = parameters.resolve_path_params(merged, ps)
    data = json.loads(parameters.write_params_file(resolved, tmp_path / "params.json").read_text())
    assert data["aligner"] == "hisat2"
    assert data["outdir"].endswith("/out")
    assert data["input"].startswith("/") and data["input"].endswith("rel/ss.csv")  # made absolute


def test_params_file_non_object_raises_clean_error(tmp_path):
    # A params file must be an object (param -> value). A top-level list/scalar is malformed and
    # must fail with a clear NfclawError, not a cryptic dict.update TypeError.
    for content in ("[1, 2, 3]", '"a string"', "42"):
        pf = tmp_path / "p.json"
        pf.write_text(content)
        with pytest.raises(NfclawError) as exc:
            parameters.merge(cli_overrides={}, params_file=pf, input_path=None, outdir=tmp_path / "o")
        assert exc.value.code == ErrorCode.PARAMS_INVALID
        assert "object of parameters" in str(exc.value)


def test_malformed_params_file_raises_clean_error(tmp_path):
    # Malformed JSON and a binary file must fail with a clear NfclawError, not a raw
    # JSONDecodeError/UnicodeDecodeError traceback.
    bad_json = tmp_path / "bad.json"
    bad_json.write_text('{"aligner": "star"')                    # unterminated
    with pytest.raises(NfclawError) as exc:
        parameters.merge(cli_overrides={}, params_file=bad_json, input_path=None, outdir=tmp_path / "o")
    assert exc.value.code == ErrorCode.PARAMS_INVALID and "not valid JSON" in str(exc.value)

    binary = tmp_path / "book.json"
    binary.write_bytes(bytes([0xff, 0xfe, 0x00, 0x01]))
    with pytest.raises(NfclawError) as exc:
        parameters.merge(cli_overrides={}, params_file=binary, input_path=None, outdir=tmp_path / "o")
    assert exc.value.code == ErrorCode.PARAMS_INVALID and "not valid UTF-8" in str(exc.value)


def test_params_file_empty_object_is_ok(tmp_path):
    pf = tmp_path / "p.json"
    pf.write_text("{}")
    merged = parameters.merge(cli_overrides={}, params_file=pf, input_path=None, outdir=tmp_path / "o")
    assert merged["outdir"].endswith("/o")   # empty params object merges cleanly


def test_params_file_with_utf8_bom_loads(tmp_path):
    # A JSON params file saved with a leading UTF-8 BOM (e.g. a Windows editor) must load, not fail
    # with a cryptic json error: the loader reads utf-8-sig so the BOM is stripped.
    pf = tmp_path / "p.json"
    pf.write_bytes(b"\xef\xbb\xbf" + b'{"aligner": "star"}')
    merged = parameters.merge(cli_overrides={}, params_file=pf, input_path=None, outdir=tmp_path / "o")
    assert merged["aligner"] == "star"


def test_params_file_values_are_validated(tmp_path):
    # A typo or bad enum inside a --params-file must fail fast, exactly like a CLI flag.
    ps = schema.load_param_schema(FIX / "mini")
    pf = tmp_path / "p.json"
    pf.write_text('{"aligner": "bowtie", "alnger": "star"}')        # bad enum + typo'd key
    merged = parameters.merge(cli_overrides={}, params_file=pf, input_path=None, outdir=tmp_path / "o")
    errs = parameters.validate_params(merged, ps)
    assert any("bowtie" in e and "must be one of" in e for e in errs)   # enum caught
    assert any("alnger" in e and "unknown" in e for e in errs)         # typo caught


def test_missing_required_without_default_is_reported(tmp_path):
    ps = schema.load_param_schema(FIX / "mini")
    errs = parameters.missing_required_params({"outdir": str(tmp_path / "out")}, ps)
    assert errs == ["missing required parameter '--input'"]


def test_missing_required_ignores_schema_defaults():
    ps = schema.ParamSchema(title="t", description="d", params={
        "outdir": schema.Param("outdir", "string", None, None, "out", None, True, "io"),
        "step": schema.Param("step", "string", "mapping", ("mapping", "annotate"),
                             "start step", None, True, "io"),
    })
    assert parameters.missing_required_params({"outdir": "/tmp/out"}, ps) == []


def test_validate_params_checks_schema_value_constraints():
    ps = schema.ParamSchema(title="t", description="d", params={
        "input": schema.Param("input", "string", None, None, "ss", None, False, "io",
                              pattern=r"^\S+\.csv$"),
        "percent": schema.Param("percent", "number", None, None, "p", None, False, "io",
                                minimum=0, maximum=100),
        "label": schema.Param("label", "string", None, None, "l", None, False, "io",
                              min_length=2, max_length=4),
    })
    errs = parameters.validate_params({"input": "samples.xlsx", "percent": 120, "label": "x"}, ps)
    assert any("--input" in e and "must match" in e for e in errs)
    assert any("--percent" in e and "<= 100" in e for e in errs)
    assert any("--label" in e and "length >= 2" in e for e in errs)


def _schema_with_report_suffix(tmp_path):
    (tmp_path / "nextflow_schema.json").write_text(json.dumps(
        {"definitions": {"generic_options": {"properties": {
            "trace_report_suffix": {"type": "string", "hidden": True}}}}}))
    return schema.load_param_schema(tmp_path)


def test_pin_report_suffix_fixes_the_runs_report_filenames(tmp_path):
    # nf-core defaults this to a fresh timestamp per launch, which is interpolated into the
    # execution report/timeline/trace/DAG filenames. Pinning it is what makes a replay reproduce
    # the original run's outputs instead of writing a second, differently-named set beside them.
    ps = _schema_with_report_suffix(tmp_path)
    out = parameters.pin_report_suffix({}, ps, now=datetime(2026, 7, 13, 9, 5, 1))
    assert out["trace_report_suffix"] == "2026-07-13_09-05-01"   # the pipeline's own date format


def test_pin_report_suffix_never_overrides_a_value_the_caller_set(tmp_path):
    ps = _schema_with_report_suffix(tmp_path)
    out = parameters.pin_report_suffix({"trace_report_suffix": "mine"}, ps)
    assert out["trace_report_suffix"] == "mine"


def test_pin_report_suffix_is_a_no_op_when_the_release_lacks_the_param():
    # Older releases predate the parameter; setting it would be an unknown param and fail validation.
    ps = schema.load_param_schema(FIX / "mini")
    assert "trace_report_suffix" not in parameters.pin_report_suffix({}, ps)


def test_falsy_values_are_left_to_nf_schema(tmp_path):
    # Whether false/"" are valid depends on the release's nf-schema (verified: 2.5.1 and 2.6.1 drop
    # them before validating, 2.7.2 rejects them for a string/enum); null is dropped by all three. An
    # error that only some plugin versions raise is not unambiguous, so nfclaw does not pre-judge it.
    ps = schema.load_param_schema(FIX / "mini")
    assert parameters.validate_params({"input": False, "aligner": ""}, ps) == []
    assert parameters.validate_params({"aligner": None}, ps) == []
    assert parameters.validate_params({"alnger": False}, ps)          # an unknown name is still unknown
    # 0 is not dropped by nf-schema, so it is still checked
    (tmp_path / "nextflow_schema.json").write_text(json.dumps({"definitions": {"g": {"properties": {
        "threads": {"type": "integer", "minimum": 1}}}}}))
    assert parameters.validate_params({"threads": 0}, schema.load_param_schema(tmp_path))


def test_merge_input_false_unsets_the_input(tmp_path):
    # `--input false` overrides a params-file `input` by leaving it unset (see inputs.resolve).
    pf = tmp_path / "p.json"
    pf.write_text(json.dumps({"input": "/data/ss.csv", "genome": "GRCh38"}))
    merged = parameters.merge(cli_overrides={}, params_file=pf, input_path=False,
                              outdir=tmp_path / "out")
    assert "input" not in merged and merged["genome"] == "GRCh38"


def test_resolve_path_params_covers_every_nf_schema_path_format(tmp_path, monkeypatch):
    # Nextflow launches from --outdir, so every relative path parameter must be made absolute —
    # including nf-schema's `path` (a file or directory, e.g. mag --busco-db) and
    # `file-path-pattern` (a glob, e.g. sarek --known-indels), not only file-path/directory-path.
    (tmp_path / "nextflow_schema.json").write_text(json.dumps({"definitions": {"g": {"properties": {
        "db": {"type": "string", "format": "path"},
        "vcfs": {"type": "string", "format": "file-path-pattern"},
        "remote": {"type": "string", "format": "path"}}}}}))
    ps = schema.load_param_schema(tmp_path)
    monkeypatch.chdir(tmp_path)
    out = parameters.resolve_path_params(
        {"db": "dbs/busco", "vcfs": "vcf/*.vcf.gz", "remote": "s3://bucket/db"}, ps)
    assert out == {"db": str(tmp_path / "dbs" / "busco"),
                   "vcfs": str(tmp_path / "vcf" / "*.vcf.gz"),
                   "remote": "s3://bucket/db"}


def test_non_finite_numbers_never_reach_the_params_file(tmp_path):
    # `nan`/`inf` parse as floats, and json.dumps would write the non-standard NaN/Infinity literals
    # Nextflow cannot read. A CLI string is left uncoerced (and reported); a params-file value (a
    # YAML `.nan`) is reported whatever the declared type; writing one is refused as a backstop.
    ps = _schema_with_types(tmp_path)
    for text in ("nan", "inf", "-Infinity"):
        assert parameters.coerce_to_schema({"ratio": text}, ps)["ratio"] == text
        assert parameters.validate_params({"ratio": text}, ps)          # "expects a number"
    for value in (math.nan, math.inf, [1.0, math.nan]):
        errs = parameters.validate_params({"flexible": value}, ps)
        assert any("finite" in e for e in errs), errs
    with pytest.raises(NfclawError) as exc:
        parameters.write_params_file({"ratio": math.nan}, tmp_path / "params.json")
    assert exc.value.code == ErrorCode.PARAMS_INVALID
    assert not (tmp_path / "params.json").exists()


def test_empty_path_param_is_left_unset_not_resolved_to_cwd(tmp_path, monkeypatch):
    # `--fasta ""` means "not set"; resolving it made it the caller's working directory.
    (tmp_path / "nextflow_schema.json").write_text(json.dumps({"definitions": {"g": {"properties": {
        "fasta": {"type": "string", "format": "file-path"}}}}}))
    ps = schema.load_param_schema(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert parameters.resolve_path_params({"fasta": ""}, ps) == {"fasta": ""}
    assert parameters.resolve_path_params({"fasta": "  "}, ps) == {"fasta": "  "}


def test_unreadable_params_file_is_a_clean_error(tmp_path, monkeypatch):
    pf = tmp_path / "p.json"
    pf.write_text("{}")
    real_open = pathlib.Path.open

    def deny(self, *a, **k):
        if self == pf:
            raise PermissionError(13, "Permission denied", str(self))
        return real_open(self, *a, **k)

    monkeypatch.setattr(pathlib.Path, "open", deny)
    with pytest.raises(NfclawError) as exc:
        parameters.load_params_file(pf)
    assert exc.value.code == ErrorCode.PARAMS_INVALID and "cannot be read" in str(exc.value)


def test_load_params_file_names_the_file_by_its_label(tmp_path):
    # A chain spec is read with the same loader; its errors must not call it a "--params-file".
    bad = tmp_path / "chain.json"
    bad.write_text("{nope")
    with pytest.raises(NfclawError, match="chain spec is not valid JSON"):
        parameters.load_params_file(bad, label="chain spec")


def test_a_required_param_the_pipeline_config_sets_is_not_missing():
    ps = schema.load_param_schema(FIX / "mini")
    required = {n for n, p in ps.params.items() if p.required and p.default is None}
    assert "input" in required
    merged = {"outdir": "/o"}
    assert any("--input" in e for e in parameters.missing_required_params(merged, ps))
    assert not any("--input" in e for e in parameters.missing_required_params(
        merged, ps, configured={"input": "'/data/sheet.csv'"}))
    for unset in ("null", "''", '""'):                    # assigned, but to nothing
        assert any("--input" in e for e in parameters.missing_required_params(
            merged, ps, configured={"input": unset}))


def test_declared_local_reference_filename_cannot_reach_unescaped_task_scripts(tmp_path):
    (tmp_path / "nextflow_schema.json").write_text(json.dumps({"$defs": {"io": {"properties": {
        "fasta": {"type": "string", "format": "file-path"}}}}}))
    ps = schema.load_param_schema(tmp_path)
    assert parameters.validate_params({"fasta": str(tmp_path / "ref$(>MARKER).fa")}, ps)


def test_path_resolution_cannot_reintroduce_unsafe_symlink_target_name(tmp_path):
    (tmp_path / "nextflow_schema.json").write_text(json.dumps({"$defs": {"io": {"properties": {
        "fasta": {"type": "string", "format": "file-path"}}}}}))
    target = tmp_path / "ref$(>MARKER).fa"
    target.write_text(">chr\nACGT\n")
    alias = tmp_path / "safe.fa"
    alias.symlink_to(target)
    assert parameters.validate_params({"fasta": str(alias)}, schema.load_param_schema(tmp_path))


def test_finite_number_validation_does_not_expand_shared_yaml_value_graphs():
    visits = []
    class SharedList(list):
        def __iter__(self):
            visits.append(id(self))
            assert len(visits) <= 20, "Validation re-expanded shared values"
            return super().__iter__()
    value = SharedList([1.0])
    for _ in range(12):
        value = SharedList([value, value, value, value])
    assert parameters._finite(value)
    assert len(visits) == 13


def test_finite_number_validation_handles_deep_values_and_finds_nonfinite_leaves():
    value = float("inf")
    for _ in range(2000):
        value = [value]
    assert not parameters._finite(value)


def test_path_resolution_keeps_alias_format_and_checks_both_names(tmp_path):
    (tmp_path / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "fasta": {"type": "string", "format": "file-path", "pattern": r"\.fa$"}}}))
    ps = schema.load_param_schema(tmp_path)
    target = tmp_path / "stored.data"
    target.write_text(">chr\nACGT\n")
    alias = tmp_path / "reference.fa"
    alias.symlink_to(target)
    resolved = parameters.resolve_path_params({"fasta": str(alias)}, ps)
    assert resolved == {"fasta": str(alias)}
    assert parameters.validate_params(resolved, ps) == []
    unsafe = tmp_path / "reference$(id).fa"
    unsafe.symlink_to(target)
    assert parameters.validate_params(parameters.resolve_path_params({"fasta": str(unsafe)}, ps), ps)


def test_schema_declared_local_file_uri_must_use_a_recordable_filesystem_path(tmp_path):
    (tmp_path / "nextflow_schema.json").write_text(json.dumps({"$defs": {"io": {"properties": {
        "fasta": {"type": "string", "format": "file-path"}}}}}))
    problems = parameters.validate_params({"fasta": "file:///tmp/ref$(>MARKER).fa"},
                                          schema.load_param_schema(tmp_path))
    assert any("absolute filesystem path" in issue for issue in problems)


def _numeric_schema():
    def p(name, type_, enum=None):
        return Param(name, type_, None, enum, "", None, False, "g")
    return ParamSchema("t", "", {"threads": p("threads", "integer"),
                                 "mode": p("mode", "integer", ("1", "2")),
                                 "ratio": p("ratio", "number", ("0.5", "1"))})


@pytest.mark.parametrize("given,expected", [
    ({"threads": 4.0}, {"threads": 4}), ({"mode": 1.0}, {"mode": 1}), ({"ratio": 1.0}, {"ratio": 1.0})])
def test_numbers_valid_under_json_schema_are_not_rejected(given, expected):
    # JSON Schema: 4.0 is an integer, and 1.0 equals the allowed value 1. A params file writing
    # them that way is valid for nf-schema, so the preflight must not refuse it.
    ps = _numeric_schema()
    coerced = parameters.coerce_to_schema(given, ps)
    assert coerced == expected and type(coerced[next(iter(expected))]) is type(next(iter(expected.values())))
    assert parameters.validate_params(coerced, ps) == []


@pytest.mark.parametrize("given", [{"threads": 4.5}, {"mode": 3}, {"mode": 1.5}, {"ratio": 2}])
def test_numbers_invalid_under_json_schema_are_still_rejected(given):
    ps = _numeric_schema()
    assert parameters.validate_params(parameters.coerce_to_schema(given, ps), ps)


@pytest.mark.parametrize("parameter", ["input", "fasta", "database"])
def test_explicit_remote_path_parameters_have_staged_name_guards(tmp_path, parameter):
    (tmp_path / "nextflow_schema.json").write_text(json.dumps({"properties": {
        parameter: {"type": "string", "format": "file-path"}}}))
    ps = schema.load_param_schema(tmp_path)
    issues = parameters.validate_params(
        {parameter: "https://example.org/ref$(id).fa"}, ps)
    assert any("unsafe remote input filename" in issue for issue in issues)
    assert parameters.validate_params(
        {parameter: "https://example.org/ref.fa?token=a+b/c=&signature=$signed"}, ps) == []
