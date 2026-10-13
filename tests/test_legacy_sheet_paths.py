"""Real pinned legacy schemas must protect the files their pipelines consume."""
import json
import hashlib
import subprocess
import sys
import csv
from pathlib import Path

import pytest

from runner import handoff, provenance, replay_guard, samplesheet, schema
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
    _, contract, sheet, _ = _sheet(tmp_path, relative=damage == "relative", missing=damage == "missing")
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
    spec = ({"samplesheet": "samples.csv", "provides": ["sample", "fastq_1", "fastq_2", "replicate"]}
            if kind == "direct" else {"build": {"rows": "fastq/{sample}_1.fastq.gz",
                "columns": {"sample": "{sample}", "fastq_1": "fastq/{sample}_1.fastq.gz",
                            "fastq_2": "fastq/{sample}_2.fastq.gz", "replicate": "1"}}})
    result = handoff.materialize(_rule({"params": {"input": spec}}), upstream_outdir=up,
                                 downstream_tree=tree, dest=tmp_path / "handoff")
    item = result.record["params"]["input"]
    assert item["consumed_sources"] == sorted(map(str, reads))
    assert provenance.samplesheet_input_paths(Path(result.params["input"]), contract) == sorted(reads)


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


AUDITS = json.loads((ROOT / "runner/input_roles.json").read_text())


@pytest.mark.parametrize("digest,audit", sorted(AUDITS.items()),
                         ids=[a["pipeline"] + ":" + a["schema"] for _, a in sorted(AUDITS.items())])
def test_audited_schema_roles_match_the_pins_and_capture_each_data_cell(tmp_path, digest, audit):
    tree = ROOT / "pipelines" / audit["pipeline"] / "upstream"
    source = tree / audit["schema"]
    if not source.exists():
        pytest.skip("requires initialized pinned pipeline source")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tree, text=True).strip() == audit["commit"]
    for reference in audit["source"]:
        assert (tree / reference.partition(":")[0]).is_file(), reference
    contract = schema.load_input_schema(tree, audit["schema"])
    row = {}
    expected = []
    for name, role in audit["columns"].items():
        path = tmp_path / f"{name}.data"
        if role["format"] == "path":
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
    from runner import sheetgen
    tree, contract = _pinned(name)
    assert sheetgen.plan(contract, schema.load_param_schema(tree).params["input"]).problem


def test_nanoseq_positional_header_cannot_be_reordered(tmp_path):
    _, contract = _pinned("nanoseq")
    sheet = tmp_path / "samples.csv"
    sheet.write_text("replicate,group,barcode,input_file,fasta,gtf\n1,A,1,,,\n")
    assert any("header" in issue for issue in samplesheet.validate(sheet, contract))


@pytest.mark.parametrize("damage", ["revision", "source"])
def test_consumer_schema_corrections_fail_closed_when_audited_identity_changes(tmp_path, damage):
    tree, _ = _pinned("hgtseq")
    copy = tmp_path / "pipeline"
    subprocess.run(["git", "clone", "--shared", "--quiet", str(tree), str(copy)], check=True)
    assert {c.name for c in schema.load_input_schema(copy).columns} == {"sample", "input1", "input2"}
    if damage == "revision":
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "commit", "--quiet", "--allow-empty", "-m", "unreviewed revision"], cwd=copy, check=True)
    else:
        source = copy / "workflows/hgtseq.nf"
        source.write_text(source.read_text() + "\n// modified consumer\n")
    with pytest.raises(NfclawError, match="audited samplesheet"):
        schema.load_input_schema(copy)


def test_nanoseq_configured_reference_name_remains_metadata_but_local_references_are_hashed(tmp_path):
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
