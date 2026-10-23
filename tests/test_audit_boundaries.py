"""Execution and inventory regressions for the repository audit."""
import csv
import json
import os

import pytest

from runner import chain, handoff, parameters, provenance, verify
from runner.errors import NfclawError
from test_handoff import _rule, _trees


@pytest.mark.parametrize("change", ["bytes", "extra", "missing", "unrecorded"])
def test_directory_reference_handoff_requires_historical_inventory(
        library, finished_run, tmp_path, change):
    _, down = _trees(library("mini_up", "mini"))
    schema_path = down / "nextflow_schema.json"
    data = json.loads(schema_path.read_text())
    data["definitions"]["reference_genome_options"]["properties"]["fasta"]["format"] = "directory-path"
    schema_path.write_text(json.dumps(data))
    reference = tmp_path / "index"
    reference.mkdir()
    index = reference / "index.bin"
    index.write_bytes(b"original")
    up = finished_run(tmp_path / "up", {}, params={"gtf": str(reference)})
    if change == "unrecorded":
        (up / "provenance/inputs.sha256").write_text("")
        (up / "provenance/inputs.inventory.json").write_text("{}")
    else:
        snapshot, inventory = provenance.snapshot_inputs([reference])
        (up / "provenance/inputs.sha256").write_text("".join(
            f"{digest}  {path}\n" for path, digest in snapshot.items()))
        (up / "provenance/inputs.inventory.json").write_text(json.dumps(inventory))
    if change == "bytes":
        index.write_bytes(b"different")
    elif change == "extra":
        (reference / "new.bin").write_bytes(b"extra")
    elif change == "missing":
        index.unlink()
    rule = _rule({"params": {"fasta": {"upstream_param": "gtf", "optional": True}}})
    with pytest.raises(NfclawError, match="reference"):
        handoff.materialize(rule, upstream_outdir=up, downstream_tree=down, dest=tmp_path / "h")


def test_verification_cannot_certify_two_unreadable_result_trees(tmp_path, monkeypatch):
    original, replay = tmp_path / "original", tmp_path / "replay"
    for root in (original, replay):
        root.mkdir()
        (root / "counts.tsv").write_bytes(b"gene\t10\n")
    scandir = os.scandir

    def denied(path):
        if str(path) in (str(original), str(replay)):
            raise PermissionError(13, "Permission denied", str(path))
        return scandir(path)

    monkeypatch.setattr(os, "scandir", denied)
    with pytest.raises(NfclawError, match="read"):
        verify.compare(original, replay)


def test_broken_output_symlink_cannot_look_like_an_empty_success(tmp_path):
    (tmp_path / "counts.tsv").symlink_to(tmp_path / "missing.tsv")
    with pytest.raises(OSError):
        provenance.output_checksums(tmp_path)


@pytest.mark.parametrize("suffix,text", [
    ("json", '{"threshold": 0.01, "threshold": 0.99}'),
    ("yaml", "threshold: 0.01\nthreshold: 0.99\n"),
    ("json", '{"nested": {"threshold": 0.01, "threshold": 0.99}}'),
    ("yaml", "nested:\n  threshold: 0.01\n  threshold: 0.99\n"),
])
def test_duplicate_parameter_keys_are_rejected(tmp_path, suffix, text):
    if suffix == "yaml":
        pytest.importorskip("yaml")
    path = tmp_path / f"params.{suffix}"
    path.write_text(text)
    with pytest.raises(NfclawError, match="duplicate"):
        parameters.load_params_file(path)


def test_yaml_merge_override_remains_valid(tmp_path):
    pytest.importorskip("yaml")
    path = tmp_path / "params.yaml"
    path.write_text("base: &base {threshold: 0.01}\nsettings: {<<: *base, threshold: 0.99}\n")
    assert parameters.load_params_file(path)["settings"] == {"threshold": 0.99}


def test_recursive_yaml_parameter_alias_is_a_clear_validation_error(tmp_path):
    pytest.importorskip("yaml")
    path = tmp_path / "params.yaml"
    path.write_text("settings: &settings {again: *settings}\n")
    with pytest.raises(NfclawError, match="cyclic"):
        parameters.load_params_file(path)


def test_yaml_object_tags_cannot_execute_code(tmp_path):
    pytest.importorskip("yaml")
    path = tmp_path / "params.yaml"
    marker = tmp_path / "executed"
    path.write_text(f'object: !!python/object/apply:os.system ["touch {marker}"]\n')
    with pytest.raises(NfclawError, match="YAML"):
        parameters.load_params_file(path)
    assert not marker.exists()


def test_directory_symlink_outputs_keep_their_published_paths(tmp_path):
    data = tmp_path / "work"
    data.mkdir()
    (data / "counts.tsv").write_bytes(b"gene\t10\n")
    out = tmp_path / "out"
    out.mkdir()
    (out / "published").symlink_to(data, target_is_directory=True)
    assert set(provenance.output_checksums(out)) == {"published/counts.tsv"}


def test_cyclic_directory_symlink_outputs_fail_explicitly(tmp_path):
    (tmp_path / "cycle").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(OSError, match="cyclic"):
        provenance.output_checksums(tmp_path)


def test_added_directory_alias_is_a_changed_input_inventory(tmp_path):
    data = tmp_path / "data"
    original = data / "original"
    original.mkdir(parents=True)
    (original / "reads.txt").write_bytes(b"reads")
    before = provenance.hash_inputs([data])
    (data / "alias").symlink_to(original, target_is_directory=True)
    after = provenance.hash_inputs([data])
    assert set(after) == {str(original / "reads.txt"), str(data / "alias/reads.txt")}
    assert after != before


def test_cyclic_input_directory_is_refused_before_snapshot(tmp_path):
    (tmp_path / "cycle").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(OSError, match="cyclic"):
        provenance.hash_inputs([tmp_path])


@pytest.mark.parametrize("internal", [False, True])
def test_unchanged_reference_directory_has_complete_handoff_lineage(
        library, finished_run, tmp_path, internal):
    _, down = _trees(library("mini_up", "mini"))
    up = finished_run(tmp_path / "up", {"index/index.bin": "original"} if internal else {})
    reference = up / "index" if internal else tmp_path / "index"
    if not internal:
        reference.mkdir()
        (reference / "index.bin").write_bytes(b"original")
        hashes, inventory = provenance.snapshot_inputs([reference])
        (up / "provenance/inputs.sha256").write_text("".join(
            f"{digest}  {path}\n" for path, digest in hashes.items()))
        (up / "provenance/inputs.inventory.json").write_text(json.dumps(inventory))
    (up / "provenance/params.json").write_text(json.dumps({"gtf": str(reference)}))
    rule = _rule({"params": {"fasta": {"upstream_param": "gtf"}}})
    result = handoff.materialize(rule, upstream_outdir=up, downstream_tree=down, dest=tmp_path / "h")
    record = result.record["params"]["fasta"]
    assert result.params["fasta"] == str(reference)
    assert record["directory_reference"] == str(reference)
    key = "derived_from" if internal else "input_dependencies"
    assert len(record[key]) == 1


@pytest.mark.parametrize("options", [
    {"demo": "false"}, {"demo": 0}, {"params": False}, {"params": []},
    {"retries": False}, {"retries": 0.0}, {"retries": ""},
    {"config": False}, {"config": ""}, {"limits": False}, {"limits": []},
])
def test_chain_stage_rejects_falsey_values_of_the_wrong_shape(options):
    with pytest.raises(NfclawError):
        chain.parse_spec({"stages": [{"pipeline": "fixture", **options}]})


@pytest.mark.parametrize("options", [
    {"allow_spaces": "false"}, {"allow_spaces": 0},
    {"config": False}, {"config": ""}, {"limits": False}, {"limits": []},
])
def test_chain_run_options_reject_values_of_the_wrong_shape(options):
    with pytest.raises(NfclawError):
        chain.parse_spec({"stages": [{"pipeline": "fixture"}], **options})


def test_repeated_handoff_placeholder_matches_one_consistent_sample(
        library, finished_run, tmp_path):
    _, down = _trees(library("mini_up", "mini"))
    up = finished_run(tmp_path / "up", {
        "fastq/A/A_1.fastq.gz": "A reads",
        "fastq/B/C_1.fastq.gz": "inconsistent sample path"})
    rule = _rule({"params": {"input": {"build": {
        "rows": "fastq/{sample}/{sample}_1.fastq.gz",
        "columns": {"sample": "{sample}", "fastq_1": "fastq/{sample}/{sample}_1.fastq.gz"}}}}})
    result = handoff.materialize(rule, upstream_outdir=up, downstream_tree=down, dest=tmp_path / "h")
    with open(result.params["input"], newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows == [{"sample": "A", "fastq_1": str(up / "fastq/A/A_1.fastq.gz")}]
