"""What a pipeline's `--input` value is: a samplesheet, another local path, or a plain value.

Each schema below mirrors a real pinned release, so these pin the behaviour against the shapes
nf-core actually ships rather than an idealised `--input samplesheet.csv`.
"""
import json

import pytest

from runner import inputs


@pytest.mark.parametrize("value", ["file:///tmp/reads.fastq", "FILE:///tmp/reads.fastq",
                                   "file:/tmp/reads.fastq", "file://user:secret@host/reads.fastq"])
def test_local_file_uri_cannot_bypass_preflight_or_dependency_recording(tmp_path, value):
    from runner.errors import NfclawError
    repo = _pipeline(tmp_path, SAREK)
    with pytest.raises(NfclawError, match="absolute filesystem path") as error:
        inputs.resolve(value, repo)
    assert "secret" not in str(error.value)


def _pipeline(tmp_path, input_param, *, samplesheet_schema=True):
    repo = tmp_path / "upstream"
    repo.mkdir()
    props = {"outdir": {"type": "string", "format": "directory-path"}}
    if input_param is not None:
        props["input"] = input_param
    (repo / "nextflow_schema.json").write_text(json.dumps(
        {"$defs": {"input_output_options": {"properties": props}}}))
    if samplesheet_schema:
        (repo / "assets").mkdir()
        (repo / "assets" / "schema_input.json").write_text(json.dumps(
            {"items": {"properties": {"sample": {"type": "string"}}, "required": ["sample"]}}))
    return repo


# sarek / rnadnavar: a samplesheet, which their docs also tell you to unset with `--input false`.
SAREK = {"type": "string", "format": "file-path", "exists": True,
         "schema": "assets/schema_input.json", "pattern": r"^\S+\.(csv|tsv|json|yml|yaml)$"}
# mhcquant 3.3.0: a samplesheet TSV, an SDRF file, or a PRIDE accession.
MHCQUANT = {"type": "string", "pattern": r"^(PXD\d{6,}|\S+\.sdrf\.tsv|\S+\.tsv)$",
            "if": {"pattern": r"\.tsv$", "not": {"pattern": r"\.sdrf\.tsv$"}},
            "then": {"format": "file-path", "exists": True, "schema": "assets/schema_input.json"}}
# rangeland: a directory or tarball of imagery; the release still ships the template schema_input.json.
RANGELAND = {"type": "string", "format": "path", "exists": True}
# atacseq and other older releases: a samplesheet with no `schema` key on the parameter.
LEGACY = {"type": "string", "format": "file-path", "mimetype": "text/csv"}


def test_input_false_means_no_input_not_a_path(tmp_path):
    # `--input false` is how sarek documents "no samplesheet" (e.g. --build_only_index). It must not
    # become <cwd>/false; `False` marks the input as unset (see parameters.merge).
    repo = _pipeline(tmp_path, SAREK)
    for raw in ("false", "False"):
        res = inputs.resolve(raw, repo)
        assert res.value is False
        assert res.samplesheet_schema is None and res.local_path is None


def test_url_is_forwarded_unchanged(tmp_path):
    repo = _pipeline(tmp_path, SAREK)
    url = "https://raw.githubusercontent.com/nf-core/test-datasets/sarek/samplesheet.csv"
    res = inputs.resolve(url, repo)
    assert res.value == url and res.samplesheet_schema is None and res.local_path is None


def test_accession_is_not_turned_into_a_local_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    repo = _pipeline(tmp_path, MHCQUANT)
    res = inputs.resolve("PXD009752", repo)
    assert res.value == "PXD009752"                    # not /cwd/PXD009752
    assert res.samplesheet_schema is None and res.local_path is None


def test_sdrf_file_is_a_local_path_but_not_a_samplesheet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "study.sdrf.tsv").write_text("source name\n")
    repo = _pipeline(tmp_path, MHCQUANT)
    res = inputs.resolve("study.sdrf.tsv", repo)
    assert res.value == str(tmp_path / "study.sdrf.tsv")   # absolute: Nextflow runs from --outdir
    assert res.samplesheet_schema is None              # the `then` branch does not apply to SDRF


def test_conditional_samplesheet_mode_is_prechecked(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    repo = _pipeline(tmp_path, MHCQUANT)
    res = inputs.resolve("samples.tsv", repo)
    assert res.samplesheet_schema == "assets/schema_input.json"
    assert res.local_path == tmp_path / "samples.tsv"


def test_directory_input_is_a_path_not_a_samplesheet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "imagery").mkdir()
    repo = _pipeline(tmp_path, RANGELAND)
    res = inputs.resolve("imagery", repo)
    assert res.local_path == tmp_path / "imagery" and res.value == str(tmp_path / "imagery")
    assert res.samplesheet_schema is None              # the template schema_input.json is unused
    assert res.must_exist is True


def test_legacy_input_without_schema_key_still_uses_the_conventional_samplesheet(tmp_path):
    repo = _pipeline(tmp_path, LEGACY)
    res = inputs.resolve(str(tmp_path / "ss.csv"), repo)
    assert res.samplesheet_schema == "assets/schema_input.json"


def test_schema_reference_with_a_leading_slash(tmp_path):
    # molkart declares `"schema": "/assets/schema_input.json"` — relative to the pipeline, not `/`.
    repo = _pipeline(tmp_path, dict(SAREK, schema="/assets/schema_input.json"))
    assert inputs.resolve(str(tmp_path / "ss.csv"), repo).samplesheet_schema == \
        "assets/schema_input.json"


def test_relative_samplesheet_is_made_absolute_against_the_callers_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    repo = _pipeline(tmp_path, SAREK)
    res = inputs.resolve("sheets/ss.csv", repo)
    assert res.value == str(tmp_path / "sheets" / "ss.csv")


def test_path_value_is_accepted(tmp_path):
    repo = _pipeline(tmp_path, SAREK)
    ss = tmp_path / "ss.csv"
    assert inputs.resolve(ss, repo).local_path == ss


@pytest.mark.parametrize("suffix", ["csv", "tsv", "json", "yaml"])
def test_samplesheet_alias_retains_its_declared_format(tmp_path, suffix):
    from runner import parameters, samplesheet, schema
    if suffix == "yaml":
        pytest.importorskip("yaml")
    repo = _pipeline(tmp_path, SAREK)
    target = tmp_path / "stored.data"
    target.write_text({"csv": "sample\nS\n", "tsv": "sample\nS\n",
                       "json": '[{"sample":"S"}]', "yaml": "- sample: S\n"}[suffix])
    alias = tmp_path / f"sheet.{suffix}"
    alias.symlink_to(target)
    result = inputs.resolve(alias, repo)
    assert result.value == str(alias) and result.local_path == alias
    assert result.samplesheet_schema == "assets/schema_input.json"
    assert parameters.validate_params({"input": result.value}, schema.load_param_schema(repo)) == []
    assert samplesheet.validate(result.local_path, schema.load_input_schema(repo)) == []


def test_conditional_schema_and_staged_alias_use_the_same_filename(tmp_path):
    repo = _pipeline(tmp_path, MHCQUANT)
    target = tmp_path / "stored.sdrf.tsv"
    target.write_text("sample\nS\n")
    alias = tmp_path / "samples.tsv"
    alias.symlink_to(target)
    result = inputs.resolve(alias, repo)
    assert result.value == str(alias)
    assert result.samplesheet_schema == "assets/schema_input.json"


def test_absolute_path_preserves_final_alias_and_kernel_parent_traversal(tmp_path):
    from runner import provenance
    (tmp_path / "real" / "nested").mkdir(parents=True)
    (tmp_path / "route").symlink_to(tmp_path / "real" / "nested", target_is_directory=True)
    target = tmp_path / "real" / "stored.data"
    target.write_bytes(b"scientific data")
    alias = tmp_path / "real" / "reads.fastq"
    alias.symlink_to("stored.data")
    requested = tmp_path / "route" / ".." / "reads.fastq"
    effective = inputs.absolute_local_path(requested)
    assert effective == alias and effective.read_bytes() == b"scientific data"
    assert inputs.absolute_local_path(tmp_path / "route" / "..") == tmp_path / "real"
    hashes, nodes = provenance.snapshot_inputs([effective])
    assert set(hashes) == {str(alias)}
    assert nodes[str(alias)] == {"type": "file", "link_target": "stored.data",
                                "resolved_path": str(target)}


@pytest.mark.parametrize("separator", ["\n", "\r"])
@pytest.mark.parametrize("alias", [False, True])
def test_line_breaks_in_source_or_resolved_parent_cannot_enter_staging(tmp_path, separator, alias):
    parent = tmp_path / f"parent{separator}next"
    parent.mkdir()
    source = parent / "reads.fastq"
    source.write_bytes(b"fixed data")
    if alias:
        link = tmp_path / "safe.fastq"
        link.symlink_to(source)
        source = link
    assert any("line break" in issue for issue in inputs.local_name_issues(str(source), "file-path"))


def test_parent_traversal_route_matches_the_normalized_parameter_but_not_raw_table_field(tmp_path):
    (tmp_path / "real/nested").mkdir(parents=True)
    (tmp_path / "route").symlink_to("real/nested", target_is_directory=True)
    (tmp_path / "real/reads.fastq").write_bytes(b"actual data")
    (tmp_path / "reads.fastq").write_bytes(b"wrong decoy")
    source = tmp_path / "route/../reads.fastq"
    assert any("different data" in issue for issue in inputs.local_name_issues(str(source), "file-path"))
    assert inputs.local_name_issues(str(source), "file-path", resolve_parent=True) == []
    assert inputs.absolute_local_path(source).read_bytes() == b"actual data"


@pytest.mark.parametrize("fmt", ["file-path", "file-path-pattern"])
def test_parent_glob_matches_receive_staging_route_checks(tmp_path, fmt):
    parent = tmp_path / "data\nnext"
    parent.mkdir()
    (parent / "reads.fastq").write_bytes(b"fixed data")
    assert any("line break" in issue for issue in inputs.local_name_issues(str(tmp_path / "data*/reads.fastq"), fmt))


def test_wildcard_parent_traversal_is_refused_before_parameter_resolution(tmp_path):
    repo = _pipeline(tmp_path, {"type": "string", "format": "file-path-pattern"})
    from runner.errors import NfclawError
    with pytest.raises(NfclawError, match="wildcard"):
        inputs.resolve(str(tmp_path / "data*/../reads.fastq"), repo)
    assert any("wildcard" in issue for issue in inputs.local_name_issues(
        str(tmp_path / "data*/../reads.fastq"), "file-path-pattern", resolve_parent=True))


def test_colon_and_repeated_slashes_in_an_absolute_parent_are_local_dependencies(tmp_path):
    from runner import provenance, samplesheet, schema
    repo = _pipeline(tmp_path, SAREK)
    data = tmp_path / "data:"
    data.mkdir()
    source = data / "reads.fastq"
    source.write_bytes(b"fixed scientific input")
    value = str(source).replace("data:/", "data://", 1)
    assert not inputs.is_remote_url(value)
    resolved = inputs.resolve(value, repo)
    assert resolved.local_path == source and resolved.value == str(source)
    (repo / "assets/schema_input.json").write_text(json.dumps({"items": {"properties": {
        "sample": {"type": "string"}, "reads": {"type": "string", "format": "file-path"}}}}))
    sheet = tmp_path / "samples.json"
    sheet.write_text(json.dumps([{"sample": "S", "reads": value}]))
    columns = schema.load_input_schema(repo)
    assert samplesheet.validate(sheet, columns) == []
    assert provenance.samplesheet_input_paths(sheet, columns) == [source]
    for scheme in ("https", "s3", "ftp", "gs", "custom+protocol"):
        assert inputs.is_remote_url(f"{scheme}://host/reads.fastq")


def test_no_input_gives_none(tmp_path):
    assert inputs.resolve(None, _pipeline(tmp_path, SAREK)) is None


@pytest.mark.parametrize("param, expected", [
    (SAREK, "assets/schema_input.json"),
    (MHCQUANT, "assets/schema_input.json"),            # one of its input modes is a samplesheet
    (LEGACY, "assets/schema_input.json"),
    (RANGELAND, None),                                 # a directory/tarball, never a samplesheet
    (None, None),                                      # no `--input` parameter at all
])
def test_documented_samplesheet_schema(tmp_path, param, expected):
    assert inputs.samplesheet_schema(_pipeline(tmp_path, param)) == expected


def test_no_samplesheet_schema_when_the_file_is_absent(tmp_path):
    assert inputs.samplesheet_schema(_pipeline(tmp_path, LEGACY, samplesheet_schema=False)) is None


def test_undecidable_condition_skips_the_precheck(tmp_path, monkeypatch):
    # A condition nfclaw cannot evaluate exactly is left to nf-schema at runtime, never guessed.
    monkeypatch.chdir(tmp_path)
    param = dict(MHCQUANT, **{"if": {"minLength": 3}})
    res = inputs.resolve("samples.tsv", _pipeline(tmp_path, param))
    assert res.samplesheet_schema is None


def test_empty_input_is_not_resolved_to_the_working_directory(tmp_path, monkeypatch):
    # An empty params-file `input` is "not set" (so a required --input is reported missing), never
    # the caller's directory pre-checked as a samplesheet.
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "nextflow_schema.json").write_text(json.dumps({"$defs": {"io": {"properties": {
        "input": {"type": "string", "format": "file-path"}}}}}))
    monkeypatch.chdir(tmp_path)
    for raw in ("", "   "):
        res = inputs.resolve(raw, repo)
        assert res.value == raw and res.local_path is None and res.samplesheet_schema is None


def test_samplesheet_schema_for_a_named_parameter(tmp_path):
    # A samplesheet can feed a parameter other than --input (taxprofiler's --databases names its own
    # schema); a chain's handoff must find it the same way.
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "databases.json").write_text("{}")
    (tmp_path / "assets" / "schema_input.json").write_text("{}")
    (tmp_path / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "file-path"},
        "fasta": {"type": "string", "format": "file-path"},
        "databases": {"type": "string", "format": "file-path",
                      "schema": "assets/databases.json"}}}))
    assert inputs.samplesheet_schema(tmp_path, param="databases") == "assets/databases.json"
    assert inputs.samplesheet_schema(tmp_path) == "assets/schema_input.json"   # legacy convention
    assert inputs.samplesheet_schema(tmp_path, param="fasta") is None          # ...is input-only
    assert inputs.samplesheet_schema(tmp_path, param="missing") is None


def test_auxiliary_conditional_schema_and_primary_only_legacy_convention(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    repo = _pipeline(tmp_path, SAREK)
    data = json.loads((repo / "nextflow_schema.json").read_text())
    props = data["$defs"]["input_output_options"]["properties"]
    props["references"] = {"type": "string", "if": {"pattern": r"\.csv$"},
                           "then": {"schema": "assets/schema_input.json", "format": "file-path"},
                           "else": {"type": "string"}}
    props["other_file"] = {"type": "string", "format": "file-path"}
    (repo / "nextflow_schema.json").write_text(json.dumps(data))
    assert inputs.samplesheet_parameters(repo) == ("input", "references")
    sheet = inputs.resolve("reference.csv", repo, param_name="references")
    assert sheet.samplesheet_schema == "assets/schema_input.json"
    assert sheet.local_path == tmp_path / "reference.csv"
    assert inputs.resolve("ACCESSION", repo, param_name="references").local_path is None
    assert inputs.resolve("other.csv", repo, param_name="other_file").samplesheet_schema is None
    # The string filename "false" is not the primary --input false sentinel for another parameter.
    assert inputs.resolve("false", repo, param_name="other_file").value == str(tmp_path / "false")


def test_conditional_remote_input_names_are_guarded_before_returning(tmp_path):
    from runner.errors import NfclawError
    (tmp_path / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "if": {"pattern": "^PRIDE"},
                  "else": {"format": "file-path"}}}}))
    with pytest.raises(NfclawError, match="unsafe remote input filename"):
        inputs.resolve("https://example.org/reads$(id).sdrf.tsv", tmp_path)
    result = inputs.resolve("https://example.org/reads.sdrf.tsv?token=x&y=2", tmp_path)
    assert result.value == "https://example.org/reads.sdrf.tsv?token=x&y=2"
    assert result.local_path is None
