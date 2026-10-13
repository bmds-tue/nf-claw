from runner.schema import Column, InputSchema, load_input_schema
from runner import samplesheet
import pytest

SCH = InputSchema(columns=(
    Column("sample", "string", True, None, None),
    Column("fastq_1", "string", True, None, "file-path"),
))


@pytest.mark.parametrize("identifier", ["safe$(touch${IFS}MARKER)", "`touch${IFS}MARKER`",
                                      "../other", "/absolute", "-option", ".hidden",
                                      "A;touch${IFS}MARKER", "A*", "A\nB", "   "])
def test_schema_declared_identifier_rejects_code_paths_and_glob_expansion(tmp_path, identifier):
    import csv
    import json
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/schema_input.json").write_text(json.dumps({"items": {"properties": {
        "specimen_label": {"type": "string", "meta": ["id"]},
        "description": {"type": "string"}}, "required": ["specimen_label"]}}))
    schema = load_input_schema(tmp_path)
    sheet = tmp_path / "samples.csv"
    with sheet.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["specimen_label", "description"])
        writer.writerow([identifier, "unrestricted $(annotation); free text"])
    issues = samplesheet.validate(sheet, schema)
    assert any("identifier" in issue and "specimen_label" in issue for issue in issues)


@pytest.mark.parametrize("identifier", ["Sample1", "_control", "α-sample.2", "e\u0301chantillon"])
def test_identifier_guard_preserves_safe_names_and_descriptive_text(tmp_path, identifier):
    import csv
    import json
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/schema_input.json").write_text(json.dumps({"items": {"properties": {
        "specimen_label": {"type": "string", "meta": "id"},
        "description": {"type": "string"}}}}))
    sheet = tmp_path / "samples.csv"
    with sheet.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["specimen_label", "description"])
        writer.writerow([identifier, "annotation $x; 'quotes'\nand newlines"])
    assert samplesheet.validate(sheet, load_input_schema(tmp_path)) == []


def test_legacy_named_sample_identifier_is_protected_without_meta_annotation(tmp_path):
    sheet = tmp_path / "samples.csv"
    sheet.write_text('sample\nsafe$(touch${IFS}MARKER)\n')
    assert any("identifier" in issue for issue in samplesheet.validate(sheet, InputSchema(columns=(
        Column("sample", "string", True, None),))))


@pytest.mark.parametrize("extension", ["json", "yaml", "yml"])
def test_serialized_sample_identity_cannot_bypass_the_guard(tmp_path, extension):
    import json
    data = [{"sample": "safe$(touch${IFS}MARKER)"}]
    sheet = tmp_path / f"samples.{extension}"
    if extension == "json":
        sheet.write_text(json.dumps(data))
    else:
        yaml = pytest.importorskip("yaml")
        sheet.write_text(yaml.safe_dump(data))
    assert any("identifier" in issue for issue in samplesheet.validate(sheet, SCH))


@pytest.mark.parametrize("extension,content", [
    ("json", '[{"sample":"A","sample":"B"}]'),
    ("yaml", '- sample: A\n  sample: B\n'),
])
def test_serialized_samplesheet_duplicate_keys_cannot_silently_change_identity(tmp_path, extension, content):
    if extension == "yaml":
        pytest.importorskip("yaml")
    sheet = tmp_path / f"samples.{extension}"
    sheet.write_text(content)
    assert any("duplicate" in issue for issue in samplesheet.validate(sheet, SCH))


def test_relative_glob_paths_cannot_bind_to_a_different_launch_directory(tmp_path):
    schema = InputSchema(columns=(Column("reads", "string", True, None, "file-path-pattern"),))
    sheet = tmp_path / "samples.csv"
    sheet.write_text('reads\nreads/*.fastq.gz\n')
    assert any("relative path" in issue for issue in samplesheet.validate(sheet, schema))


def test_absolute_glob_paths_are_not_treated_as_literal_filenames(tmp_path):
    schema = InputSchema(columns=(Column("reads", "string", True, None, "file-path-pattern"),))
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f'reads\n{tmp_path}/reads/*.fastq.gz\n')
    assert samplesheet.validate(sheet, schema) == []


@pytest.mark.parametrize("extension,delimiter", [("csv", ","), ("tsv", "\t")])
def test_incomplete_quoted_record_cannot_silently_change_sample_metadata(tmp_path, extension, delimiter):
    schema = InputSchema(columns=(Column("sample", "string", True, None, None),
                                  Column("description", "string", False, None, None)))
    sheet = tmp_path / f"samples.{extension}"
    sheet.write_text(f'sample{delimiter}description\nA{delimiter}"unfinished\nB{delimiter}other\n')
    assert any("not parseable" in issue for issue in samplesheet.validate(sheet, schema))


def test_valid_quoted_multiline_field_remains_supported(tmp_path):
    schema = InputSchema(columns=(Column("sample", "string", True, None, None),
                                  Column("description", "string", False, None, None)))
    sheet = tmp_path / "samples.csv"
    sheet.write_text('sample,description\nA,"two\nlines"\nB,"quoted ""word"""\n')
    assert samplesheet.validate(sheet, schema) == []

def test_missing_required_column(tmp_path):
    ss = tmp_path / "ss.csv"
    ss.write_text("sample\nA\n")
    issues = samplesheet.validate(ss, SCH)
    assert any("fastq_1" in i for i in issues)

def test_missing_input_file(tmp_path):
    ss = tmp_path / "ss.csv"
    ss.write_text(f"sample,fastq_1\nA,{tmp_path / 'missing_R1.fastq.gz'}\n")
    issues = samplesheet.validate(ss, SCH)
    assert any("file not found" in i for i in issues)

def test_binary_samplesheet_is_flagged_not_crashed(tmp_path):
    # A non-text file (e.g. an .xlsx handed in as a .csv) must return a clear issue, not raise
    # UnicodeDecodeError. Covers both the named-column and headerless branches.
    ss = tmp_path / "book.csv"
    ss.write_bytes(bytes([0x50, 0x4b, 0x03, 0x04]) + bytes(range(200, 256)))   # not UTF-8
    named = samplesheet.validate(ss, SCH)
    assert named and "not valid UTF-8" in named[0]
    unnamed = samplesheet.validate(ss, InputSchema(columns=(Column("", "string", False, None, None),)))
    assert unnamed and "not valid UTF-8" in unnamed[0]


def test_directory_as_samplesheet_is_flagged_not_crashed(tmp_path):
    # --input pointing at a directory must return a clear issue, not raise IsADirectoryError.
    d = tmp_path / "adir"
    d.mkdir()
    issues = samplesheet.validate(d, SCH)
    assert issues and "not a file" in issues[0]


def test_valid_sheet(tmp_path):
    (tmp_path / "r1.fq.gz").write_text("x")
    ss = tmp_path / "ss.csv"
    ss.write_text(f"sample,fastq_1\nA,{tmp_path / 'r1.fq.gz'}\n")
    assert samplesheet.validate(ss, SCH) == []


# TSV samplesheets (e.g. nf-core/airrflow requires a strictly `.tsv` input): the validator must
# split on TAB by file extension, not read the whole comma-delimited header as one column (which
# reported every required column missing).
def test_tsv_delimiter_detected(tmp_path):
    (tmp_path / "r1.fq.gz").write_text("x")
    ss = tmp_path / "ss.tsv"
    ss.write_text(f"sample\tfastq_1\nA\t{tmp_path / 'r1.fq.gz'}\n")
    assert samplesheet.validate(ss, SCH) == []

def test_tsv_missing_column_still_detected(tmp_path):
    ss = tmp_path / "ss.tsv"
    ss.write_text("sample\nA\n")               # tab-parsed header has only 'sample'
    issues = samplesheet.validate(ss, SCH)
    assert any("fastq_1" in i for i in issues)


def test_non_tabular_named_input_is_deferred_to_nf_schema(tmp_path):
    # nf-core/sarek accepts YAML/JSON inputs even though it ships schema_input.json for tabular
    # samplesheets. The local pre-check must not parse those files as CSV and reject them before
    # Nextflow/nf-schema gets the format-specific validation.
    ss = tmp_path / "samples.json"
    ss.write_text('[{"patient": "P1", "sample": "S1"}]\n')
    assert samplesheet.validate(ss, SCH) == []


SAREK_LIKE = InputSchema(
    columns=(
        Column("patient", "string", True, None, None),
        Column("sample", "string", True, None, None),
        Column("lane", "integer or string", False, r"^\S+$", None),
        Column("fastq_1", "string", False, None, "file-path"),
        Column("fastq_2", "string", False, None, "file-path"),
        Column("spring_1", "string", False, None, "file-path"),
        Column("bam", "string", False, None, "file-path"),
    ),
    dependent_required=(("fastq_2", ("fastq_1",)),),
    any_of_dependent_required=(
        (("lane", ("fastq_1",)),),
        (("lane", ("spring_1",)),),
        (("lane", ("bam",)),),
    ),
)


def test_dependent_required_column_rule_is_reported(tmp_path):
    ss = tmp_path / "ss.csv"
    ss.write_text("patient,sample,fastq_2\nP1,S1,R2.fastq.gz\n")
    issues = samplesheet.validate(ss, SAREK_LIKE)
    assert "row 2: 'fastq_2' requires 'fastq_1'" in issues


def test_anyof_dependent_required_column_rule_is_reported(tmp_path):
    ss = tmp_path / "ss.csv"
    ss.write_text("patient,sample,lane\nP1,S1,1\n")
    issues = samplesheet.validate(ss, SAREK_LIKE)
    assert any("when 'lane' is set" in i and "fastq_1" in i and "bam" in i for i in issues)


def test_anyof_dependent_required_accepts_one_valid_branch(tmp_path):
    (tmp_path / "reads.bam").write_text("x")
    ss = tmp_path / "ss.csv"
    ss.write_text(f"patient,sample,lane,bam\nP1,S1,1,{tmp_path / 'reads.bam'}\n")
    assert samplesheet.validate(ss, SAREK_LIKE) == []


def test_column_enum_pattern_and_range_rules_are_reported(tmp_path):
    (tmp_path / "r1.fq.gz").write_text("x")
    sch = InputSchema(columns=(
        Column("sample", "string", True, r"^\S+$", None),
        Column("fastq_1", "string", True, r".+\.f(ast)?q\.gz$", "file-path"),
        Column("strandedness", "string", True, None, None,
               enum=("forward", "reverse", "unstranded", "auto")),
        Column("percent_mapped", "number", False, None, None, minimum=0, maximum=100),
    ))
    ss = tmp_path / "ss.csv"
    ss.write_text("sample,fastq_1,strandedness,percent_mapped\n"
                  f"bad sample,{tmp_path / 'r1.fq.gz'},sideways,101\n")
    issues = samplesheet.validate(ss, sch)
    assert any("sample" in i and "must match" in i for i in issues)
    assert any("strandedness" in i and "must be one of" in i for i in issues)
    assert any("percent_mapped" in i and "<= 100" in i for i in issues)


def test_column_integer_type_rule_is_reported(tmp_path):
    sch = InputSchema(columns=(
        Column("patient", "string", True, None, None),
        Column("sample", "string", True, None, None),
        Column("status", "integer", False, None, None, enum=("0", "1")),
    ))
    ss = tmp_path / "ss.csv"
    ss.write_text("patient,sample,status\nP1,S1,tumor\n")
    issues = samplesheet.validate(ss, sch)
    assert any("status" in i and "integer" in i for i in issues)


# A UTF-8 BOM (common in spreadsheet-exported CSVs) must not make the first required column read
# as missing: the validator reads utf-8-sig so a leading BOM is stripped before header parsing.
def test_utf8_bom_header_is_stripped(tmp_path):
    (tmp_path / "r1.fq.gz").write_text("x")
    ss = tmp_path / "ss.csv"
    ss.write_bytes(b"\xef\xbb\xbf" + f"sample,fastq_1\nA,{tmp_path / 'r1.fq.gz'}\n".encode())  # BOM
    assert samplesheet.validate(ss, SCH) == []                          # was "missing column 'sample'"

def test_bom_does_not_mask_a_genuinely_missing_column(tmp_path):
    ss = tmp_path / "ss.csv"
    ss.write_bytes(b"\xef\xbb\xbf" + b"sample\nA\n")                     # BOM + fastq_1 truly absent
    assert any("fastq_1" in i for i in samplesheet.validate(ss, SCH))


# Headerless single-column input (nf-core/fetchngs id list): DictReader must NOT eat line 1.
UNNAMED = InputSchema(columns=(Column("", "string", False, "^SRR", None),))

def test_unnamed_single_column_accepts_one_value(tmp_path):
    f = tmp_path / "ids.txt"
    f.write_text("SRR123456\n")
    assert samplesheet.validate(f, UNNAMED) == []          # was wrongly "no data rows"

def test_unnamed_single_column_rejects_empty(tmp_path):
    f = tmp_path / "ids.txt"
    f.write_text("\n   \n")
    assert samplesheet.validate(f, UNNAMED) == ["input file has no values"]


# nf-schema resolves a relative samplesheet path against Nextflow's launch directory — which nfclaw
# sets to --outdir — not against the samplesheet's own folder. A relative path that exists next to
# the samplesheet therefore passed this check and then failed at runtime ("does not exist"), after
# --outdir and the provenance bundle had already been created. Reject it up front instead.
def test_relative_path_is_rejected_even_when_it_exists_next_to_the_samplesheet(tmp_path):
    (tmp_path / "r1.fq.gz").write_text("x")
    ss = tmp_path / "ss.csv"
    ss.write_text("sample,fastq_1\nA,r1.fq.gz\n")
    issues = samplesheet.validate(ss, SCH)
    assert len(issues) == 1
    assert "relative path" in issues[0] and "absolute" in issues[0] and "--outdir" in issues[0]


def test_tilde_path_is_relative_to_nextflow(tmp_path):
    # nf-schema does not expand `~` in samplesheet values (verified with nf-schema 2.6.1).
    ss = tmp_path / "ss.csv"
    ss.write_text("sample,fastq_1\nA,~/r1.fq.gz\n")
    assert any("relative path" in i for i in samplesheet.validate(ss, SCH))


def test_remote_paths_are_not_checked_locally(tmp_path):
    ss = tmp_path / "ss.csv"
    ss.write_text("sample,fastq_1\nA,s3://bucket/r1.fq.gz\n")
    assert samplesheet.validate(ss, SCH) == []


PATTERN_TYPED = InputSchema(columns=(
    # atacseq/hic: FastQ columns typed by their pattern alone, without a path format.
    Column("sample", "string", True, "^\\S+$", None),
    Column("fastq_1", "string", True, "^\\S+\\.f(ast)?q\\.gz$", None),
    # bacass: `NA` marks a missing read file and names no file.
    Column("LongFastQ", "string", False, "^(\\S+\\.f(ast)?q\\.gz|NA)$", None),
    # nanostring: a column that only names the file another column stages.
    Column("RCC_FILE", "string", False, "^\\S+\\.RCC$", "file-path"),
    Column("RCC_FILE_NAME", "string", False, "^\\S+\\.RCC$", None),
), metadata_columns=("RCC_FILE_NAME",))


@pytest.mark.parametrize("extension", [".csv", ".json"])
def test_pattern_typed_file_columns_refuse_relative_paths(tmp_path, extension):
    # The pipelines open these values with file(), which resolves a relative path against the launch
    # directory (nfclaw's --outdir): it can only fail late, after launch, or name another file.
    rcc = tmp_path / "a.RCC"
    rcc.write_text("x")
    ss = tmp_path / f"ss{extension}"
    if extension == ".csv":
        ss.write_text("sample,fastq_1,LongFastQ,RCC_FILE,RCC_FILE_NAME\n"
                      f"A,reads/a_R1.fastq.gz,NA,{rcc},a.RCC\n"
                      f"B,{tmp_path / 'b_R1.fastq.gz'},long.fq.gz,{rcc},a.RCC\n")
    else:
        import json
        ss.write_text(json.dumps([
            {"sample": "A", "fastq_1": "reads/a_R1.fastq.gz", "LongFastQ": "NA",
             "RCC_FILE": str(rcc), "RCC_FILE_NAME": "a.RCC"},
            {"sample": "B", "fastq_1": str(tmp_path / "b_R1.fastq.gz"), "LongFastQ": "long.fq.gz",
             "RCC_FILE": str(rcc), "RCC_FILE_NAME": "a.RCC"}]))
    issues = samplesheet.validate(ss, PATTERN_TYPED)
    row_a, row_b = ("row 2", "row 3") if extension == ".csv" else ("row 1", "row 2")
    assert len(issues) == 2, issues
    assert any(row_a in i and "'fastq_1' is a relative path" in i and "--outdir" in i
               for i in issues)
    assert any(row_b in i and "'LongFastQ' is a relative path" in i for i in issues)


def test_a_column_naming_a_staged_file_stays_a_name_without_an_audit(tmp_path):
    # nanostring 1.3.0-1.3.2 (run with --pipeline-version) publish RCC_FILE_NAME beside RCC_FILE
    # with no audited contract: a bare file name there is metadata, not a relative path.
    import dataclasses
    unaudited = dataclasses.replace(PATTERN_TYPED, metadata_columns=())
    rcc = tmp_path / "a.RCC"
    rcc.write_text("x")
    ss = tmp_path / "ss.csv"
    ss.write_text(f"sample,fastq_1,RCC_FILE,RCC_FILE_NAME\nA,{tmp_path / 'a_R1.fastq.gz'},{rcc},a.RCC\n")
    assert samplesheet.validate(ss, unaudited) == []
    assert "RCC_FILE_NAME" not in samplesheet.pattern_file_columns(unaudited)
    assert "fastq_1" in samplesheet.pattern_file_columns(unaudited)


def test_pattern_typed_file_columns_keep_remote_and_absolute_values(tmp_path):
    ss = tmp_path / "ss.csv"
    ss.write_text("sample,fastq_1\n"
                  "A,https://example.org/a_R1.fastq.gz\n"
                  f"B,{tmp_path / 'b_R1.fastq.gz'}\n")
    assert samplesheet.validate(ss, PATTERN_TYPED) == []


@pytest.mark.parametrize("extension", [".csv", ".json"])
def test_matching_read_patterns_do_not_turn_an_unformatted_mate_into_metadata(tmp_path, extension):
    pattern = r"^\S+\.fastq\.gz$"
    contract = InputSchema(columns=(Column("sample", "string", True, None),
        Column("fastq_1", "string", True, pattern, "file-path"),
        Column("fastq_2", "string", True, pattern)))
    read = tmp_path / "A_1.fastq.gz"
    read.write_bytes(b"first mate identity")
    sheet = tmp_path / f"samples{extension}"
    if extension == ".csv":
        sheet.write_text(f"sample,fastq_1,fastq_2\nA,{read},A_2.fastq.gz\n")
    else:
        import json
        sheet.write_text(json.dumps([{"sample": "A", "fastq_1": str(read), "fastq_2": "A_2.fastq.gz"}]))
    assert any("fastq_2" in issue and "relative path" in issue for issue in samplesheet.validate(sheet, contract))


@pytest.mark.parametrize("extension", [".csv", ".json"])
@pytest.mark.parametrize("location", ["local", "remote"])
def test_pattern_only_read_paths_receive_the_same_literal_filename_guard(tmp_path, extension, location):
    contract = InputSchema(columns=(Column("sample", "string", True, None),
        Column("reads", "string", True, r"^\S+\.fastq\.gz$")))
    data = tmp_path / "O'Brien.fastq.gz"
    data.write_bytes(b"read identity; preflight does not decode sequence content")
    value = str(data) if location == "local" else "https://example.org/O'Brien.fastq.gz"
    sheet = tmp_path / f"samples{extension}"
    if extension == ".csv":
        sheet.write_text(f"sample,reads\nA,{value}\n")
    else:
        import json
        sheet.write_text(json.dumps([{"sample": "A", "reads": value}]))
    assert any("unsafe" in issue and "filename" in issue for issue in samplesheet.validate(sheet, contract))


def test_path_format_columns_are_checked_too(tmp_path):
    # nf-schema's `path` format (a file or a directory; e.g. mhcquant's ReplicateFileName, sopa's
    # data_path) resolves exactly like `file-path`.
    sch = InputSchema(columns=(Column("sample", "string", True, None, None),
                               Column("data", "string", True, None, "path")))
    ss = tmp_path / "ss.csv"
    ss.write_text(f"sample,data\nA,data_dir\nB,{tmp_path / 'absent'}\n")
    issues = samplesheet.validate(ss, sch)
    assert any("row 2" in i and "relative path" in i for i in issues)
    assert any("row 3" in i and "file not found" in i for i in issues)


def test_unbalanced_quote_in_a_large_sheet_is_flagged_not_crashed(tmp_path):
    # One stray quote turns the rest of the file into a single field; past the csv module's field
    # size limit that raised a raw csv.Error traceback instead of a samplesheet issue.
    p = tmp_path / "ss.csv"
    p.write_text('sample\n"A\n' + "B\n" * 70000)
    issues = samplesheet.validate(p, SCH)
    assert len(issues) == 1 and "not parseable as CSV" in issues[0] and "quote" in issues[0]
    t = tmp_path / "ss.tsv"
    t.write_text('sample\n"A\n' + "B\n" * 70000)
    assert "not parseable as TSV" in samplesheet.validate(t, SCH)[0]


def test_unreadable_sheet_is_flagged_not_crashed(tmp_path, monkeypatch):
    # A sheet that exists but cannot be read (another user's file) raised a raw PermissionError.
    import pathlib
    ss = tmp_path / "ss.csv"
    ss.write_text("sample,fastq_1\n")
    real_open = pathlib.Path.open

    def deny(self, *a, **k):
        if self == ss:
            raise PermissionError(13, "Permission denied", str(self))
        return real_open(self, *a, **k)

    monkeypatch.setattr(pathlib.Path, "open", deny)
    assert samplesheet.validate(ss, SCH) == [f"samplesheet cannot be read: Permission denied: {ss}"]


# --- header_issues: the column-level half of validate, for a sheet that does not exist yet ---

_HEADER_SCH = InputSchema(
    columns=(Column("sample", "string", True, None),
             Column("fastq_1", "string", True, None, fmt="file-path"),
             Column("fastq_2", "string", False, None, fmt="file-path"),
             Column("lane", "string", False, None)),
    dependent_required=(("fastq_2", ("fastq_1",)),),
    any_of_dependent_required=((("lane", ("fastq_1",)),),),
)


def test_delimiter_follows_the_extension():
    from pathlib import Path
    assert samplesheet.delimiter_for(Path("a.tsv")) == "\t"
    assert samplesheet.delimiter_for(Path("a.TSV")) == "\t"
    assert samplesheet.delimiter_for(Path("a.csv")) == ","


def test_header_issues_accepts_a_header_that_can_satisfy_the_schema():
    assert samplesheet.header_issues(["sample", "fastq_1", "fastq_2", "extra"], _HEADER_SCH) == []


def test_header_issues_reports_missing_required_and_dependent_columns():
    issues = samplesheet.header_issues(["sample", "fastq_2"], _HEADER_SCH)
    assert "missing required column 'fastq_1'" in issues
    assert "'fastq_2' requires 'fastq_1'" in issues


def test_header_issues_requires_one_column_group():
    sheet = InputSchema(columns=(), one_of=(("sampleID", "forwardReads"), ("sample", "fastq_1")))
    assert samplesheet.header_issues(["sample", "fastq_1"], sheet) == []
    assert samplesheet.header_issues(["sample"], sheet) == [
        "needs one of these column sets: sampleID, forwardReads; sample, fastq_1"]


@pytest.mark.parametrize("content", [
    '- ? [sample, other]\n  : A\n',
    '- sample: !!python/object/apply:os.system ["touch UNEXPECTED"]\n',
    '- sample: 2026-10-09\n',
    '- sample: &recursive [*recursive]\n',
])
def test_yaml_invalid_keys_tags_and_nonliteral_identity_are_refused(tmp_path, content):
    pytest.importorskip("yaml")
    sheet = tmp_path / "samples.yaml"
    sheet.write_text(content)
    assert samplesheet.validate(sheet, SCH)
    assert not (tmp_path / "UNEXPECTED").exists()


def test_yaml_merge_overrides_and_quoted_identity_preserve_valid_records(tmp_path):
    pytest.importorskip("yaml")
    sheet = tmp_path / "samples.yaml"
    sheet.write_text('- &base\n  sample: A\n  description: free text $x\n'
                     '- <<: *base\n  sample: "2026-10-09"\n')
    assert samplesheet.validate(sheet, SCH) == []
    assert [row["sample"] for row in samplesheet.serialized_rows(sheet)] == ["A", "2026-10-09"]


def test_yaml_without_optional_parser_fails_closed(tmp_path, monkeypatch):
    import sys
    sheet = tmp_path / "samples.yaml"
    sheet.write_text('- sample: A\n')
    monkeypatch.setitem(sys.modules, "yaml", None)
    assert any("nfclaw[yaml]" in issue for issue in samplesheet.validate(sheet, SCH))


@pytest.mark.parametrize("extension", ["json", "yaml"])
def test_serialized_local_paths_cannot_rebind_against_launch_directory(tmp_path, extension):
    import json
    sheet = tmp_path / f"samples.{extension}"
    data = [{"sample": "A", "fastq_1": "relative.fastq.gz"}]
    if extension == "json":
        sheet.write_text(json.dumps(data))
    else:
        yaml = pytest.importorskip("yaml")
        sheet.write_text(yaml.safe_dump(data))
    assert any("relative path" in issue for issue in samplesheet.validate(sheet, SCH))


def test_nested_legacy_named_field_keeps_its_schema_contract(tmp_path):
    import json
    sheet = tmp_path / "samples.json"
    sheet.write_text(json.dumps([{"sample": {"description": "free text $x"}}]))
    schema = InputSchema(columns=(Column("sample", "object", True, None),))
    assert samplesheet.validate(sheet, schema) == []


@pytest.mark.parametrize("key", ["genome_name", "db_name"])
def test_auxiliary_resource_identity_cannot_inject_into_task_prefixes(tmp_path, key):
    sheet = tmp_path / "resources.csv"
    sheet.write_text(f"{key}\nsafe$(touch${{IFS}}MARKER)\n")
    schema = InputSchema(columns=(Column(key, "string", True, None, meta=(key,)),))
    assert any("identifier" in issue for issue in samplesheet.validate(sheet, schema))


@pytest.mark.parametrize("filename", ["reads$(>MARKER).fastq.gz", "reads`id`.fastq.gz",
                                     "reads;true.fastq.gz", "reads*.fastq.gz", "-reads.fastq.gz",
                                     "reads with spaces.fastq.gz", "reads\nnext.fastq.gz"])
def test_existing_local_file_names_cannot_become_shell_syntax(tmp_path, filename):
    import csv
    reads = tmp_path / filename
    reads.write_bytes(b"reads")
    sheet = tmp_path / "samples.csv"
    with sheet.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample", "fastq_1"])
        writer.writerow(["A", str(reads)])
    assert any("filename" in issue for issue in samplesheet.validate(sheet, SCH))


def test_glob_matching_cannot_hide_a_shell_active_file_name(tmp_path):
    reads = tmp_path / "reads$(>MARKER).fastq.gz"
    reads.write_bytes(b"reads")
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f"reads\n{tmp_path}/*.fastq.gz\n")
    schema = InputSchema(columns=(Column("reads", "string", True, None, "file-path-pattern"),))
    assert any("filename" in issue for issue in samplesheet.validate(sheet, schema))


@pytest.mark.parametrize("extension", ["json", "yaml"])
def test_serialized_data_names_have_the_same_shell_safety_guard(tmp_path, extension):
    import json
    reads = tmp_path / "reads$(>MARKER).fastq.gz"
    reads.write_bytes(b"reads")
    data = [{"sample": "A", "fastq_1": str(reads)}]
    sheet = tmp_path / f"samples.{extension}"
    if extension == "json":
        sheet.write_text(json.dumps(data))
    else:
        yaml = pytest.importorskip("yaml")
        sheet.write_text(yaml.safe_dump(data))
    assert any("filename" in issue for issue in samplesheet.validate(sheet, SCH))


@pytest.mark.parametrize("filename", ["muestra_é-1.fastq.gz", "sample_e\u0301.fastq.gz",
                                     "reads+lane@run%=1,part:2~copy.fastq.gz"])
def test_literal_unicode_names_and_parent_directories_with_spaces_remain_valid(tmp_path, filename):
    import csv
    parent = tmp_path / "parent with spaces"
    parent.mkdir()
    reads = parent / filename
    reads.write_bytes(b"reads")
    sheet = tmp_path / "samples.csv"
    with sheet.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample", "fastq_1"])
        writer.writerow(["A", str(reads)])
    assert samplesheet.validate(sheet, SCH) == []
    assert reads.exists()


def test_declared_glob_keeps_literal_safe_matches_and_nested_paths(tmp_path):
    parent = tmp_path / "parent with spaces"
    parent.mkdir()
    for name in ("reads_A.fastq.gz", "reads_é.fastq.gz"):
        (parent / name).write_bytes(b"reads")
    sheet = tmp_path / "paths.csv"
    sheet.write_text(f"reads\n{parent}/reads_*.fastq.gz\n")
    schema = InputSchema(columns=(Column("reads", "string", True, None, "file-path-pattern"),))
    assert samplesheet.validate(sheet, schema) == []


@pytest.mark.parametrize("uri", ["file:///tmp/reads$(>MARKER).fastq.gz",
                                "file:///tmp/reads%24%28%3EMARKER%29.fastq.gz",
                                "FILE:///tmp/safe.fastq.gz"])
def test_local_file_uri_cannot_be_treated_as_unchecked_remote_data(tmp_path, uri):
    import csv
    sheet = tmp_path / "samples.csv"
    with sheet.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample", "fastq_1"])
        writer.writerow(["A", uri])
    assert any("absolute filesystem path" in issue for issue in samplesheet.validate(sheet, SCH))


def test_real_remote_data_and_local_colon_names_remain_supported(tmp_path):
    from runner.inputs import local_name_issues
    assert local_name_issues("https://example.org/reads.fastq.gz", "file-path") == []
    assert local_name_issues(str(tmp_path / "file:reads.fastq.gz"), "file-path") == []


@pytest.mark.parametrize("scheme", ["https", "http", "ftp", "s3", "gs", "az"])
@pytest.mark.parametrize("filename", ["reads$(id).fastq.gz", "reads`id`.fastq.gz",
                                     "reads;true.fastq.gz", "-reads.fastq.gz",
                                     "~reads.fastq.gz", "reads with spaces.fastq.gz"])
def test_remote_staged_names_cannot_bypass_shell_safety(tmp_path, scheme, filename):
    import csv
    sheet = tmp_path / "samples.csv"
    with sheet.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample", "fastq_1"])
        writer.writerow(["A", f"{scheme}://bucket/{filename}"])
    assert any("unsafe remote input filename" in issue
               for issue in samplesheet.validate(sheet, SCH))


@pytest.mark.parametrize("extension", ["json", "yaml"])
def test_remote_staged_name_guard_applies_to_serialized_records(tmp_path, extension):
    import json
    data = [{"sample": "A", "fastq_1": "https://example.org/reads$(id).fastq.gz"}]
    sheet = tmp_path / f"samples.{extension}"
    if extension == "json":
        sheet.write_text(json.dumps(data))
    else:
        yaml = pytest.importorskip("yaml")
        sheet.write_text(yaml.safe_dump(data))
    assert any("unsafe remote input filename" in issue
               for issue in samplesheet.validate(sheet, SCH))


@pytest.mark.parametrize("url", [
    "https://example.org/reads%20space.fastq.gz",
    "https://example.org/reads%24%28id%29.fastq.gz",
    "https://example.org/reads.fastq.gz?token=a+b/c=&signature=$signed#fragment",
    "https://example.org/parent;name/reads+lane@run%=1,part:2~copy.fastq.gz",
    "s3://bucket/muestra_é-1.fastq.gz",
])
def test_safe_remote_names_keep_percent_escapes_and_transport_metadata(url):
    from runner.inputs import local_name_issues
    assert local_name_issues(url, "file-path") == []


@pytest.mark.parametrize("url", ["https://example.org/reads\nfile.fastq.gz",
                                 "https://example.org/reads\tfile.fastq.gz",
                                 "https://[broken/reads.fastq.gz"])
def test_unparseable_remote_names_fail_clearly(url):
    from runner.inputs import local_name_issues
    assert local_name_issues(url, "file-path")


@pytest.mark.parametrize("url", ["s3://bucket/reads.txt?token=x&y=2",
                                 "s3://bucket/reads.txt#fragment",
                                 "s3://bucket/reads$(id).txt?token=x"])
def test_object_store_keys_retain_query_and_fragment_characters(url):
    from runner.inputs import local_name_issues
    assert any("unsafe remote input filename" in issue
               for issue in local_name_issues(url, "file-path"))


@pytest.mark.parametrize("scheme", ["https", "http", "ftp"])
@pytest.mark.parametrize("fragment", ["fragment", "$(id)", "`id`"])
def test_standalone_remote_fragments_remain_staged_filename_characters(scheme, fragment):
    from runner.inputs import local_name_issues
    assert local_name_issues(f"{scheme}://example.org/reads#{fragment}.txt", "file-path")
