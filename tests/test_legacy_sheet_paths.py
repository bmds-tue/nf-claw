"""Real pinned legacy schemas must protect the files their pipelines consume."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from runner import handoff, provenance, replay_guard, samplesheet, schema, sheetgen
from runner.errors import NfclawError
from test_handoff import _rule
from test_output_namespace import record


ROOT = Path(__file__).resolve().parents[1]
LEGACY_READS = ("atacseq", "chipseq", "circdna", "cutandrun", "hic", "hicar",
                "marsseq", "pixelator", "rnasplice", "viralintegration")


def _pinned(name):
    tree = ROOT / "pipelines" / name / "upstream"
    if not (tree / "assets/schema_input.json").exists():
        pytest.skip("requires initialized pinned pipeline source")
    return tree, schema.load_input_schema(tree)


def _write_row(sheet, row):
    """Write `row` as a one-row CSV samplesheet, quoting values as csv does."""
    with sheet.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def _sheet(tmp_path, name="atacseq", *, relative=False, missing=False):
    tree, contract = _pinned(name)
    reads = [tmp_path / f"mate{i}.fastq.gz" for i in (1, 2)]
    for read in reads:
        read.write_bytes(b"fixture FASTQ identity")
    values = [read.name if relative else str(read) for read in reads]
    if missing:
        reads[1].unlink()
    sheet = tmp_path / "samples.csv"
    sheet.write_text("sample,fastq_1,fastq_2,replicate\nA," + ",".join(values) + ",1\n")
    return tree, contract, sheet, reads


@pytest.mark.parametrize("name", LEGACY_READS)
def test_legacy_read_paths_are_captured_from_pinned_schemas(tmp_path, name):
    _, contract, sheet, reads = _sheet(tmp_path, name)
    assert provenance.samplesheet_input_paths(sheet, contract) == sorted(reads)


@pytest.mark.parametrize("damage,expected", [("relative", "relative path"),
                                             ("missing", "file not found")])
def test_legacy_read_validation_rejects_unresolvable_data(tmp_path, damage, expected):
    _, contract, sheet, _ = _sheet(tmp_path, relative=damage == "relative",
                                   missing=damage == "missing")
    assert any(expected in issue for issue in samplesheet.validate(sheet, contract))


@pytest.mark.parametrize("suffix", ["csv", "json", "yaml"])
def test_legacy_reads_remain_replay_dependencies_in_flat_sheets(tmp_path, suffix):
    _, contract, sheet, reads = _sheet(tmp_path)
    if suffix != "csv":
        sheet = tmp_path / f"samples.{suffix}"
        # JSON is also a valid YAML document; this tests each supported flat reader.
        sheet.write_text(json.dumps([{"sample": "A", "fastq_1": str(reads[0]),
                                      "fastq_2": str(reads[1]), "replicate": 1}]))
    out = tmp_path / "run"
    record(out, inputs=[sheet, *provenance.samplesheet_input_paths(sheet, contract)])
    replay_guard.verify_dependencies(out / "provenance")
    reads[1].write_bytes(b"changed read bytes")
    with pytest.raises(ValueError, match="changed"):
        replay_guard.verify_dependencies(out / "provenance")


@pytest.mark.parametrize("kind", ["direct", "build"])
def test_legacy_handoffs_absolutize_and_bind_both_mates(tmp_path, kind):
    tree, contract = _pinned("atacseq")
    up = tmp_path / "producer"
    (up / "fastq").mkdir(parents=True)
    reads = [up / "fastq" / f"A_{i}.fastq.gz" for i in (1, 2)]
    for read in reads:
        read.write_bytes(b"fixture FASTQ identity")
    (up / "samples.csv").write_text("sample,fastq_1,fastq_2,replicate\n"
                                    "A,fastq/A_1.fastq.gz,fastq/A_2.fastq.gz,1\n")
    record(up)
    spec = (
        {"samplesheet": "samples.csv", "provides": ["sample", "fastq_1", "fastq_2", "replicate"]}
        if kind == "direct" else {"build": {"rows": "fastq/{sample}_1.fastq.gz",
            "columns": {"sample": "{sample}", "fastq_1": "fastq/{sample}_1.fastq.gz",
                        "fastq_2": "fastq/{sample}_2.fastq.gz", "replicate": "1"}}})
    result = handoff.materialize(_rule({"params": {"input": spec}}), upstream_outdir=up,
                                 downstream_tree=tree, dest=tmp_path / "handoff")
    item = result.record["params"]["input"]
    assert item["consumed_sources"] == sorted(map(str, reads))
    handed_over = Path(result.params["input"])
    assert provenance.samplesheet_input_paths(handed_over, contract) == sorted(reads)


def test_branch_declared_path_and_literal_sentinel_are_distinct(tmp_path):
    _, contract = _pinned("isoseq")
    bam, index = tmp_path / "A.bam", tmp_path / "A.bam.pbi"
    bam.write_bytes(b"sequence bytes")
    index.write_bytes(b"index bytes")
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f"sample,seq_data,pbi,start_from\nA,{bam},{index},ccs\nB,{bam},none,lima\n")
    assert samplesheet.validate(sheet, contract) == []
    assert provenance.samplesheet_input_paths(sheet, contract) == sorted([bam, index])


def test_filename_metadata_is_not_guessed_to_be_a_local_input(tmp_path):
    _, contract = _pinned("nanostring")
    data = tmp_path / "A.RCC"
    data.write_bytes(b"counts")
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f"SAMPLE_ID,RCC_FILE,RCC_FILE_NAME\nA,{data},A.RCC\n")
    assert samplesheet.validate(sheet, contract) == []
    assert provenance.samplesheet_input_paths(sheet, contract) == [data]


@pytest.mark.parametrize("suffix", ["csv", "json"])
def test_nanostring_existing_absolute_filename_metadata_is_not_a_data_dependency(tmp_path, suffix):
    _, contract = _pinned("nanostring")
    data, label = tmp_path / "A.RCC", tmp_path / "label.RCC"
    data.write_bytes(b"actual instrument data identity")
    label.write_bytes(b"unrelated file whose absolute name is used as metadata")
    sheet = tmp_path / f"samples.{suffix}"
    row = {"SAMPLE_ID": "A", "RCC_FILE": str(data), "RCC_FILE_NAME": str(label)}
    if suffix == "json":
        sheet.write_text(json.dumps([row]))
    else:
        _write_row(sheet, row)
    assert samplesheet.validate(sheet, contract) == []
    assert provenance.samplesheet_input_paths(sheet, contract) == [data]
    assert provenance.samplesheet_file_paths(sheet, contract) == []


@pytest.mark.parametrize("kind", ["direct", "build"])
def test_nanostring_handoff_keeps_filename_metadata_out_of_file_derivation(tmp_path, kind):
    tree, _ = _pinned("nanostring")
    up = tmp_path / "producer"
    (up / "labels").mkdir(parents=True)
    data, label = up / "A.RCC", up / "labels/metadata.RCC"
    data.write_bytes(b"instrument data identity")
    label.write_bytes(b"unrelated producer file named by metadata")
    (up / "samples.csv").write_text(f"SAMPLE_ID,RCC_FILE,RCC_FILE_NAME\nA,A.RCC,{label}\n")
    record(up)
    spec = ({"samplesheet": "samples.csv", "provides": ["SAMPLE_ID", "RCC_FILE", "RCC_FILE_NAME"]}
            if kind == "direct" else {"build": {"rows": "{sample}.RCC", "columns": {
                "SAMPLE_ID": "{sample}", "RCC_FILE": "{sample}.RCC", "RCC_FILE_NAME": str(label)}}})
    result = handoff.materialize(_rule({"params": {"input": spec}}, down="nanostring"),
        upstream_outdir=up, downstream_tree=tree, dest=tmp_path / "snapshot")
    item = result.record["params"]["input"]
    assert "labels/metadata.RCC" not in item["derived_from"]
    assert item["consumed_sources"] == [str(data)]


AUDITS = json.loads((ROOT / "runner/input_roles.json").read_text())


@pytest.mark.parametrize("digest,audit", sorted(AUDITS.items()),
                         ids=[a["pipeline"] + ":" + a["schema"] for _, a in sorted(AUDITS.items())])
def test_audited_schema_roles_match_the_pins_and_capture_each_data_cell(tmp_path, digest, audit):
    tree = ROOT / "pipelines" / audit["pipeline"] / "upstream"
    source = tree / audit["schema"]
    if not source.exists():
        pytest.skip("requires initialized pinned pipeline source")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tree, text=True).strip()
    if head != audit["commit"]:
        pytest.skip(f"{audit['pipeline']} is no longer pinned at the audited "
                    f"commit {audit['commit'][:12]}")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    for reference in audit["source"]:
        assert (tree / reference.partition(":")[0]).is_file(), reference
    for reference, expected_digest in audit.get("source_sha256", {}).items():
        actual = hashlib.sha256((tree / reference).read_bytes()).hexdigest()
        assert actual == expected_digest, reference
    contract = schema.load_input_schema(tree, audit["schema"])
    row = {}
    expected = []
    for name, role in audit["columns"].items():
        path = tmp_path / f"{name}.data"
        if role["format"] in {"path", "directory-path"}:
            path.mkdir()
        else:
            path.write_bytes(b"known data")
        row[name] = str(path)
        expected.append(path)
    sheet = tmp_path / "data.json"
    sheet.write_text(json.dumps([row]))
    assert provenance.samplesheet_input_paths(sheet, contract) == sorted(expected)
    for name, role in audit["columns"].items():
        for sentinel in role.get("sentinels", []):
            sentinel_row = {name: sentinel}
            sheet.write_text(json.dumps([sentinel_row]))
            assert provenance.samplesheet_input_paths(sheet, contract) == []


def test_unknown_changed_schema_does_not_guess_filename_metadata_as_paths(tmp_path):
    tree, _ = _pinned("atacseq")
    data = json.loads((tree / "assets/schema_input.json").read_text())
    data["title"] += " changed, unaudited contract"
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/schema_input.json").write_text(json.dumps(data))
    contract = schema.load_input_schema(tmp_path)
    sheet = tmp_path / "samples.csv"
    sheet.write_text("sample,fastq_1,fastq_2\nA,not-a-path.fastq.gz,other.fastq.gz\n")
    assert provenance.samplesheet_input_paths(sheet, contract) == []


def test_declared_alternative_formats_apply_to_values_in_unknown_schemas(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/schema_input.json").write_text(json.dumps({"items": {"properties": {
        "data": {"anyOf": [{"type": "string", "pattern": r"\.bam$", "format": "file-path"},
                           {"type": "string", "pattern": "^none$"}]}}}}))
    contract = schema.load_input_schema(tmp_path)
    bam = tmp_path / "A.bam"
    bam.write_bytes(b"known data")
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f"data\n{bam}\nnone\n")
    assert samplesheet.validate(sheet, contract) == []
    assert provenance.samplesheet_input_paths(sheet, contract) == [bam]


@pytest.mark.parametrize("name", ["hgtseq", "nanoseq"])
def test_stale_templates_use_the_pinned_consumers_actual_sheet_contract(tmp_path, name):
    _, contract = _pinned(name)
    data = tmp_path / "reads.fastq.gz"
    data.write_bytes(b"known read data")
    sheet = tmp_path / "samples.csv"
    if name == "hgtseq":
        sheet.write_text(f"sample,input1,input2\nA,{data},\n")
    else:
        sheet.write_text(f"group,replicate,barcode,input_file,fasta,gtf\nA,1,,{data},,\n")
    assert samplesheet.validate(sheet, contract) == []
    assert provenance.samplesheet_input_paths(sheet, contract) == [data]
    sheet.write_text(f"sample,fastq_1,fastq_2\nA,{data},\n")
    assert samplesheet.validate(sheet, contract), "obsolete template columns cannot pass the runner"


@pytest.mark.parametrize("name", ["hgtseq", "nanoseq"])
def test_stale_templates_cannot_generate_a_sheet_that_the_consumer_rejects(name):
    tree, contract = _pinned(name)
    assert sheetgen.plan(contract, schema.load_param_schema(tree).params["input"]).problem


def test_nanoseq_positional_header_cannot_be_reordered(tmp_path):
    _, contract = _pinned("nanoseq")
    sheet = tmp_path / "samples.csv"
    sheet.write_text("replicate,group,barcode,input_file,fasta,gtf\n1,A,1,,,\n")
    assert any("header" in issue for issue in samplesheet.validate(sheet, contract))


def _shared_copy(tmp_path, name):
    tree, _ = _pinned(name)
    copy = tmp_path / "pipeline"
    subprocess.run(["git", "clone", "--shared", "--quiet", str(tree), str(copy)], check=True)
    return copy


def _other_revision(copy):
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                    "commit", "--quiet", "--allow-empty", "-m", "unreviewed revision"],
                   cwd=copy, check=True)


def _published_columns(copy):
    published = json.loads((copy / "assets/schema_input.json").read_text())
    return set(published["items"]["properties"])


def test_consumer_schema_corrections_fail_closed_when_audited_source_changes(tmp_path):
    copy = _shared_copy(tmp_path, "hgtseq")
    assert ({c.name for c in schema.load_input_schema(copy).columns}
            == {"sample", "input1", "input2"})
    source = copy / "workflows/hgtseq.nf"
    source.write_text(source.read_text() + "\n// modified consumer\n")
    with pytest.raises(NfclawError, match="audited samplesheet"):
        schema.load_input_schema(copy)


def test_consumer_schema_corrections_leave_other_revisions_their_published_contract(tmp_path):
    # An older release sharing the schema (nfclaw show/run --pipeline-version) or a newer pin
    # awaiting its audit is not the audited consumer: it keeps the columns its schema declares.
    copy = _shared_copy(tmp_path, "hgtseq")
    _other_revision(copy)
    contract = schema.load_input_schema(copy)
    assert ({c.name for c in contract.columns} == _published_columns(copy)
            != {"sample", "input1", "input2"})
    assert contract.header_prefix == () and contract.generation_problem is None


def test_nanoseq_configured_reference_name_remains_metadata_but_local_references_are_hashed(
        tmp_path):
    _, contract = _pinned("nanoseq")
    reads, fasta, gtf = (tmp_path / n for n in ("A.fastq.gz", "genome.fa", "genes.gtf"))
    for data in (reads, fasta, gtf):
        data.write_bytes(b"known bytes")
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f"group,replicate,barcode,input_file,fasta,gtf\nA,1,,{reads},mm10,\n"
                     f"B,1,,{reads},{fasta},{gtf}\n")
    assert samplesheet.validate(sheet, contract) == []
    assert provenance.samplesheet_input_paths(sheet, contract) == sorted((reads, fasta, gtf))


def test_corrected_nanoseq_sheet_is_accepted_by_the_actual_pinned_checker(tmp_path):
    tree, contract = _pinned("nanoseq")
    data = tmp_path / "A.fastq.gz"
    data.write_bytes(b"known identity; checker inspects metadata, not read content")
    sheet, result = tmp_path / "samples.csv", tmp_path / "checked.csv"
    sheet.write_text(f"group,replicate,barcode,input_file,fasta,gtf\nA,1,,{data},,\n")
    assert samplesheet.validate(sheet, contract) == []
    checker = tree / "bin/check_samplesheet.py"
    process = subprocess.run([sys.executable, str(checker), str(sheet), "not_changed", str(result)],
                             capture_output=True, text=True)
    assert process.returncode == 0, process.stdout + process.stderr
    with result.open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1 and rows[0]["sample"] == "A_R1" and rows[0]["input_file"] == str(data)
    sheet.write_text(f"sample,fastq_1,fastq_2\nA,{data},\n")
    process = subprocess.run([sys.executable, str(checker), str(sheet), "not_changed", str(result)],
                             capture_output=True, text=True)
    assert process.returncode != 0 and "header" in process.stdout


def test_generated_isoseq_sheet_keeps_none_literal_out_of_data_snapshot(tmp_path):
    tree, _ = _pinned("isoseq")
    data = tmp_path / "A.bam"
    data.write_bytes(b"known BAM identity; sheet generation does not interpret alignments")
    source = sheetgen.detect(str(data), tree)
    generated = sheetgen.generate(source, tree, pipeline="isoseq",
                                  assignments={"start_from": "mapping", "pbi": "none"},
                                  outdir=tmp_path / "results", work_dir=tmp_path / "work")
    assert generated.rows[0]["pbi"] == "none"
    assert generated.files == (data,)
    checksums, inventory = provenance.snapshot_inputs(list(generated.files))
    assert set(checksums) == {str(data)} and set(inventory) == {str(data)}


def _onco_sheet(tmp_path, *, value=None, filetype="fastq", info="library_id:LIB;lane:1"):
    tree, contract = _pinned("oncoanalyser")
    reads = [tmp_path / f"A_R{i}.fastq.gz" for i in (1, 2)]
    for data in reads:
        data.write_bytes(b"known read identity")
    sheet = tmp_path / "samples.csv"
    row = {"group_id": "G", "subject_id": "P", "sample_id": "A", "sample_type": "tumor",
           "sequence_type": "dna", "info": info, "filetype": filetype,
           "filepath": value or ";".join(map(str, reads))}
    _write_row(sheet, row)
    return tree, contract, sheet, reads, row


@pytest.mark.parametrize("filetype", ["fastq", "FASTQ"])
@pytest.mark.parametrize("suffix", ["csv", "json"])
def test_oncoanalyser_consumed_fastq_members_are_separate_replay_dependencies(tmp_path,
                                                                              filetype, suffix):
    _, contract, sheet, reads, row = _onco_sheet(tmp_path, filetype=filetype)
    if suffix == "json":
        sheet = tmp_path / "samples.json"
        sheet.write_text(json.dumps([row]))
    assert samplesheet.validate(sheet, contract) == []
    dependencies = provenance.samplesheet_input_paths(sheet, contract)
    assert dependencies == sorted(reads)
    out = tmp_path / "run"
    record(out, inputs=[sheet, *dependencies])
    replay_guard.verify_dependencies(out / "provenance")
    reads[1].write_bytes(b"changed second mate")
    with pytest.raises(ValueError, match="changed"):
        replay_guard.verify_dependencies(out / "provenance")


@pytest.mark.parametrize("value,expected", [("relative.fastq.gz;/other.fastq.gz", "relative path"),
                                           ("/one.fastq.gz", "exactly 2"),
                                           ("/one;/two;/three", "exactly 2")])
def test_oncoanalyser_fastq_contract_rejects_unresolvable_or_wrong_cardinality(tmp_path,
                                                                               value, expected):
    _, contract, sheet, _, _ = _onco_sheet(tmp_path, value=value)
    assert any(expected in issue for issue in samplesheet.validate(sheet, contract))


@pytest.mark.parametrize("field", ["group_id", "subject_id", "library_id", "lane", "flowcell"])
def test_oncoanalyser_actual_filename_identifiers_receive_literal_alias_guards(tmp_path, field):
    _, contract, sheet, _, row = _onco_sheet(tmp_path)
    if field in row:
        row[field] = "unsafe;id"
    else:
        row["info"] = f"library_id:LIB;lane:1;{field}:L$(id)"
    sheet = tmp_path / "unsafe.json"
    sheet.write_text(json.dumps([row]))
    assert any("identifier" in issue for issue in samplesheet.validate(sheet, contract))


def test_methylong_pod5_directory_members_are_replay_dependencies(tmp_path):
    _, contract = _pinned("methylong")
    directory = tmp_path / "pod5"
    directory.mkdir()
    data, reference = directory / "A.pod5", tmp_path / "ref.fa"
    data.write_bytes(b"known instrument data identity")
    reference.write_bytes(b">ref\nACGT\n")
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f"group,sample,path,ref,method\nG,A,{directory},{reference},ont\n")
    assert samplesheet.validate(sheet, contract) == []
    dependencies = provenance.samplesheet_input_paths(sheet, contract)
    assert dependencies == sorted((directory, reference))
    out = tmp_path / "run"
    record(out, inputs=[sheet, *dependencies])
    data.write_bytes(b"changed instrument data")
    with pytest.raises(ValueError, match="changed"):
        replay_guard.verify_dependencies(out / "provenance")


def test_oncoanalyser_compound_tokens_match_the_pinned_tokenize_semantics(tmp_path):
    _, contract, sheet, reads, row = _onco_sheet(tmp_path)
    row["filepath"] = ";;" + str(reads[0]) + ";;;" + str(reads[1]) + ";"
    sheet = tmp_path / "tokenized.json"
    sheet.write_text(json.dumps([row]))
    assert samplesheet.validate(sheet, contract) == []
    assert provenance.samplesheet_input_paths(sheet, contract) == sorted(reads)
    row.update(filetype="ALN", filepath=str(reads[0]), info="")
    sheet.write_text(json.dumps([row]))
    assert samplesheet.validate(sheet, contract) == []
    assert provenance.samplesheet_input_paths(sheet, contract) == [reads[0]]


@pytest.mark.parametrize("kind", ["direct", "build"])
def test_oncoanalyser_handoffs_normalize_and_trace_each_fastq_member(tmp_path, kind):
    tree, _ = _pinned("oncoanalyser")
    up = tmp_path / "producer"
    up.mkdir()
    _, _, sheet, reads, row = _onco_sheet(up)
    row["filepath"] = ";".join(data.name for data in reads)
    _write_row(sheet, row)
    record(up)
    if kind == "direct":
        spec = {"samplesheet": sheet.name, "provides": list(row)}
    else:
        # Complete row context must exist before a compound path is normalized, even
        # when the selector field follows the path in the rule's column order.
        columns = {"filepath": "{sample}_R1.fastq.gz;{sample}_R2.fastq.gz",
                   **{key: value for key, value in row.items() if key != "filepath"}}
        spec = {"build": {"rows": "{sample}_R1.fastq.gz", "columns": columns}}
    result = handoff.materialize(_rule({"params": {"input": spec}}), upstream_outdir=up,
                                 downstream_tree=tree, dest=tmp_path / "handoff")
    assert result.record["params"]["input"]["consumed_sources"] == sorted(map(str, reads))
    captured = result.record["params"]["input"]["consumed_dependencies"]
    assert set(captured) == set(map(str, reads))
    assert all(data.name in result.record["params"]["input"]["derived_from"] for data in reads)


@pytest.mark.parametrize("key", ["LIBRARY_ID", "lıbrary_ıd", "flowcell"])
def test_oncoanalyser_info_alias_keys_follow_the_consumers_uppercase_normalization(tmp_path, key):
    _, contract, sheet, _, _ = _onco_sheet(tmp_path, info=f"{key}:O'Brien;lane:1")
    assert any("identifier" in issue for issue in samplesheet.validate(sheet, contract))


@pytest.mark.parametrize("key",
                         ["read_group_overrides", "READ_GROUP_OVERRIDES", "read_group_overrıdes"])
def test_oncoanalyser_read_group_apostrophe_is_refused_before_single_quoted_argument(tmp_path, key):
    _, contract, sheet, _, _ = _onco_sheet(
        tmp_path, info=f"library_id:LIB;lane:1;{key}:CN=O'Brien|DS=Study")
    assert any("single quote" in issue for issue in samplesheet.validate(sheet, contract))


def test_oncoanalyser_read_group_description_keeps_colons_and_double_quotes(tmp_path):
    _, contract, sheet, _, _ = _onco_sheet(
        tmp_path, info='library_id:LIB;lane:1;read_group_overrides:CN=Research_Centre|DS=Study:"A"')
    assert samplesheet.validate(sheet, contract) == []


def test_datasync_destination_is_not_captured_as_consumed_input(tmp_path):
    _, contract = _pinned("datasync")
    source, destination = tmp_path / "source.data", tmp_path / "destination.data"
    source.write_bytes(b"source bytes")
    destination.write_bytes(b"destination location is not read as input")
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f"input,output_path\n{source},{destination}\n")
    assert provenance.samplesheet_input_paths(sheet, contract) == [source]
    assert provenance.samplesheet_file_paths(sheet, contract) == []


def test_datasync_destination_exclusion_requires_the_audited_consumer(tmp_path):
    copy = _shared_copy(tmp_path, "datasync")
    assert schema.load_input_schema(copy).destination_columns == ("output_path",)
    source = copy / "modules/nf-core/rclone/copy/main.nf"
    source.write_text(source.read_text() + "\n// modified consumer\n")
    with pytest.raises(NfclawError, match="audited samplesheet"):
        schema.load_input_schema(copy)


def test_datasync_destination_exclusion_does_not_extend_to_other_revisions(tmp_path):
    copy = _shared_copy(tmp_path, "datasync")
    _other_revision(copy)
    contract = schema.load_input_schema(copy)
    assert contract.destination_columns == ()
    assert not any(c.audited_double_quoted for c in contract.columns)


@pytest.mark.parametrize("destination", ['/archive/Study"A', '/archive/Study\\A'])
@pytest.mark.parametrize("suffix", ["csv", "json"])
def test_datasync_destination_must_survive_the_consumers_double_quoted_argument(
        tmp_path, destination, suffix):
    _, contract = _pinned("datasync")
    source, checksum = tmp_path / "source.data", tmp_path / "checksum.sha256"
    source.write_bytes(b"source identity")
    checksum.write_text("fixture checksum metadata")
    row = {"sample": "A", "input": str(source), "output_path": destination,
           "checksum_sha": str(checksum)}
    sheet = tmp_path / f"samples.{suffix}"
    if suffix == "json":
        sheet.write_text(json.dumps([row]))
    else:
        _write_row(sheet, row)
    assert any("double-quoted" in issue for issue in samplesheet.validate(sheet, contract))


@pytest.mark.parametrize("destination",
                         ["/archive/O'Brien", "s3://bucket/Study_A", "/archive/new-directory"])
def test_datasync_valid_destination_is_not_required_to_exist_or_inspected_as_input(
        tmp_path, destination):
    _, contract = _pinned("datasync")
    source, checksum = tmp_path / "source.data", tmp_path / "checksum.sha256"
    source.write_bytes(b"source identity")
    checksum.write_text("fixture checksum metadata")
    sheet = tmp_path / "samples.json"
    sheet.write_text(json.dumps([{"sample": "A", "input": str(source), "output_path": destination,
                                  "checksum_sha": str(checksum)}]))
    assert samplesheet.validate(sheet, contract) == []
    assert provenance.samplesheet_input_paths(sheet, contract) == sorted((source, checksum))
    assert provenance.samplesheet_file_paths(sheet, contract) == []


def test_datasync_checks_the_complete_source_string_including_parent_names(tmp_path):
    _, contract = _pinned("datasync")
    folder = tmp_path / 'Study"A'
    folder.mkdir()
    source = folder / "source.data"
    source.write_bytes(b"source identity")
    sheet = tmp_path / "samples.json"
    sheet.write_text(
        json.dumps([{"sample": "A", "input": str(source), "output_path": "/archive/A"}]))
    assert any("double-quoted" in issue for issue in samplesheet.validate(sheet, contract))
