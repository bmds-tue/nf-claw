"""Independent regressions for result directories and scientific handoff identities."""
import json

import pytest

from runner import chain, handoff, outputs, provenance, verify
from runner.errors import NfclawError
from runner.submodule import SubmoduleStatus
from test_handoff import _rule, _trees


def record(out, inputs=(), params=None):
    (out / "provenance").mkdir(parents=True, exist_ok=True)
    (out / "provenance/params.json").write_text(json.dumps(params or {}))
    provenance.write(outdir=out, pipeline="fixture", command_str="echo AUDIT",
        submodule=SubmoduleStatus("fixture", out.parent / "no-source", True, True, "1.0.0", "deadbeef", ()),
        input_paths=list(inputs), nextflow_version="25.10.4", env_extra={"NXF_VER": "25.10.4"})


@pytest.mark.parametrize("change", ["add", "remove", "rename", "alias"])
def test_output_directory_changes_cannot_hide_behind_identical_file_bytes(tmp_path, change):
    original, replay = tmp_path / "original", tmp_path / "replay"
    for root in (original, replay):
        (root / "sample_A").mkdir(parents=True)
        (root / "counts.tsv").write_bytes(b"gene\t10\n")
    record(original)
    if change == "add":
        (replay / "sample_B").mkdir()
    elif change == "remove":
        (replay / "sample_A").rmdir()
    elif change == "rename":
        (replay / "sample_A").rename(replay / "sample_B")
    else:
        (replay / "sample_B").symlink_to(replay / "sample_A", target_is_directory=True)
    comparison = verify.compare(original, replay)
    assert comparison.identical == ["counts.tsv"] and not comparison.changed
    assert not comparison.structurally_equal and not comparison.byte_identical
    assert comparison.missing_directories or comparison.extra_directories


def test_historical_empty_directories_are_used_even_after_the_original_changes(tmp_path):
    original, replay = tmp_path / "original", tmp_path / "replay"
    (original / "sample_A").mkdir(parents=True)
    record(original)
    (original / "sample_A").rename(original / "sample_B")
    (replay / "sample_A").mkdir(parents=True)
    comparison = verify.compare(original, replay)
    assert comparison.byte_identical
    assert not comparison.missing_directories and not comparison.extra_directories


def test_legacy_file_only_manifest_cannot_certify_the_historical_directory_structure(tmp_path):
    original, replay = tmp_path / "original", tmp_path / "replay"
    original.mkdir()
    replay.mkdir()
    record(original)
    (original / "provenance/outputs.inventory.json").unlink()
    comparison = verify.compare(original, replay)
    assert comparison.unverified_structure and not comparison.structurally_equal
    assert not comparison.byte_identical and "directory agreement is unverified" in verify.report(comparison)


def test_live_directories_without_bundles_can_still_be_compared(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for root in (a, b):
        (root / "empty").mkdir(parents=True)
    assert verify.compare(a, b).byte_identical


@pytest.mark.parametrize("damage", ["version", "duplicate", "missing_parent", "bad_parent",
                                    "type", "target", "unrecorded_file", "reserved"])
def test_malformed_output_namespace_is_a_clear_error_not_an_ignored_record(tmp_path, damage):
    out = tmp_path / "out"
    (out / "data").mkdir(parents=True)
    (out / "data/counts.tsv").write_bytes(b"counts")
    record(out)
    path = out / "provenance/outputs.inventory.json"
    data = json.loads(path.read_text())
    if damage == "version":
        data["version"] = True
    elif damage == "duplicate":
        path.write_text('{"version":1,"entries":{"sample":{"type":"directory"},"sample":{"type":"file"}}}')
    elif damage == "missing_parent":
        del data["entries"]["data"]
    elif damage == "bad_parent":
        data["entries"] = {"data/counts.tsv": {"type": "file"}, "data": []}
    elif damage == "type":
        data["entries"]["data"]["type"] = []
    elif damage == "target":
        data["entries"]["data"]["link_target"] = {"scope": [], "path": "other"}
    elif damage == "unrecorded_file":
        data["entries"]["new.tsv"] = {"type": "file"}
    else:
        data["entries"]["provenance"] = {"type": "directory"}
    if damage != "duplicate":
        path.write_text(json.dumps(data))
    with pytest.raises(NfclawError, match="output"):
        verify.compare(out, out)


@pytest.mark.parametrize("internal", [False, True])
@pytest.mark.parametrize("change", ["add", "remove", "rename", "alias"])
def test_directory_handoff_refuses_namespace_changes_without_byte_changes(library, tmp_path, internal, change):
    _, down = _trees(library("mini_up", "mini"))
    up = tmp_path / "producer"
    reference = up / "index" if internal else tmp_path / "reference"
    (reference / "sample_A").mkdir(parents=True)
    (reference / "index.bin").write_bytes(b"identical index bytes")
    record(up, inputs=[] if internal else [reference], params={"gtf": str(reference)})
    before = provenance.hash_inputs([reference])
    if change == "add":
        (reference / "sample_B").mkdir()
    elif change == "remove":
        (reference / "sample_A").rmdir()
    elif change == "rename":
        (reference / "sample_A").rename(reference / "sample_B")
    else:
        (reference / "sample_B").symlink_to(reference / "sample_A", target_is_directory=True)
    assert before == provenance.hash_inputs([reference])
    with pytest.raises(NfclawError, match="reference|namespace"):
        handoff.materialize(_rule({"params": {"fasta": {"upstream_param": "gtf"}}}),
            upstream_outdir=up, downstream_tree=down, dest=tmp_path / "handoff")


@pytest.mark.parametrize("internal", [False, True])
def test_an_unchanged_empty_reference_directory_has_real_handoff_evidence(library, tmp_path, internal):
    _, down = _trees(library("mini_up", "mini"))
    up = tmp_path / "producer"
    reference = up / "index" if internal else tmp_path / "reference"
    reference.mkdir(parents=True)
    record(up, inputs=[] if internal else [reference], params={"gtf": str(reference)})
    result = handoff.materialize(_rule({"params": {"fasta": {"upstream_param": "gtf"}}}),
        upstream_outdir=up, downstream_tree=down, dest=tmp_path / "handoff")
    evidence = result.record["params"]["fasta"]
    assert evidence["directory_inventory"] == {str(reference): {"type": "directory"}}
    assert evidence["directory_source"] == ("outputs" if internal else "inputs")


def test_result_aliases_are_preserved_and_hashed_once(tmp_path):
    out = tmp_path / "out"
    (out / "data/empty").mkdir(parents=True)
    (out / "data/reads.txt").write_bytes(b"reads")
    (out / "alias").symlink_to(out / "data", target_is_directory=True)
    calls = []
    def hash_file(path):
        calls.append(path)
        return provenance._sha256(path)
    hashes, inventory, raw = outputs.snapshot(out, hash_file)
    assert len(calls) == 1 and set(hashes) == {"data/reads.txt", "alias/reads.txt"}
    assert set(inventory) == {"data", "data/empty", "data/reads.txt", "alias", "alias/empty", "alias/reads.txt"}
    assert inventory["alias"]["link_target"] == {"scope": "outdir", "path": "data"}
    assert raw[str(out / "alias")]["resolved_path"] == str(out / "data")


def test_link_retargeting_with_identical_bytes_is_reported_separately(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_bytes(b"same bytes")
    b.write_bytes(b"same bytes")
    alias = out / "data.txt"
    alias.symlink_to(a)
    record(out)
    alias.unlink()
    alias.symlink_to(b)
    comparison = verify.compare(out, out)
    assert comparison.identical == ["data.txt"] and comparison.changed_links == ["data.txt"]
    assert comparison.structurally_equal and not comparison.byte_identical


@pytest.mark.parametrize("mode", ["external", "internal", "alias", "bundle", "file_alias"])
@pytest.mark.parametrize("legacy_resolution", [False, True])
def test_chain_lineage_verifies_directory_consumption_and_detects_later_changes(library, tmp_path, mode,
                                                                              legacy_resolution):
    _, down_tree = _trees(library("mini_up", "mini"))
    data = json.loads((down_tree / "nextflow_schema.json").read_text())
    data["definitions"]["reference_genome_options"]["properties"]["fasta"]["format"] = (
        "file-path" if mode == "file_alias" else "directory-path")
    (down_tree / "nextflow_schema.json").write_text(json.dumps(data))
    up, down = tmp_path / "producer", tmp_path / "consumer"
    if mode == "file_alias":
        target = tmp_path / "first.gtf"
        target.write_bytes(b"identical annotation")
        reference = tmp_path / "annotation.gtf"
        reference.symlink_to(target)
    elif mode == "bundle":
        reference = up
        (up / "empty_sample").mkdir(parents=True)
        (up / "index.bin").write_bytes(b"index bytes")
    else:
        target = up / "index" if mode == "internal" else tmp_path / "reference"
        (target / "sample_A").mkdir(parents=True)
        (target / "nested_alias").symlink_to("sample_A", target_is_directory=True)
        (target / "index.bin").write_bytes(b"index bytes")
        reference = target
        if mode == "alias":
            up.mkdir()
            reference = up / "published_alias"
            reference.symlink_to(target, target_is_directory=True)
    record(up, inputs=[reference] if mode in ("external", "file_alias") else [],
           params={"gtf": str(reference)})
    identifier = "namespace-audit"
    up_manifest = up / "provenance/run_manifest.json"
    up_data = json.loads(up_manifest.read_text())
    up_data["chain"] = {"id": identifier, "stage": "producer", "index": 1}
    up_manifest.write_text(json.dumps(up_data))
    hand = handoff.materialize(_rule({"params": {"fasta": {"upstream_param": "gtf"}}}),
        upstream_outdir=up, downstream_tree=down_tree, dest=tmp_path / "handoff")
    hand_path = tmp_path / "handoff.json"
    hand_path.write_text(json.dumps(hand.record))
    from runner.inputs import absolute_local_path
    canonical = reference.resolve() if legacy_resolution else absolute_local_path(reference)
    record(down, inputs=[canonical], params={"fasta": str(canonical)})
    down_manifest = down / "provenance/run_manifest.json"
    down_data = json.loads(down_manifest.read_text())
    down_data["chain"] = {"id": identifier, "stage": "consumer", "index": 2,
                          "upstream": {"handoff_sha256": handoff.sha256_file(hand_path)}}
    down_manifest.write_text(json.dumps(down_data))
    state = {"chain_id": identifier, "outcome": "success", "stages": [
        {"id": "producer", "pipeline": "fixture", "index": 1, "outdir": str(up),
         "status": "success", "version": "1.0.0", "commit": "deadbeef"},
        {"id": "consumer", "pipeline": "fixture", "index": 2, "outdir": str(down),
         "status": "success", "version": "1.0.0", "commit": "deadbeef", "handoff": str(hand_path)}]}
    assert chain._integrity_problems(state) == []
    parameters_path = down / "provenance/params.json"
    original_parameters = parameters_path.read_text()
    parameters_path.write_text(original_parameters + "\n")
    assert any("config checksum" in problem for problem in chain._integrity_problems(state))
    parameters_path.write_text(original_parameters)
    assert chain._integrity_problems(state) == []
    if mode == "file_alias":
        second = tmp_path / "second.gtf"
        second.write_bytes(b"identical annotation")
        reference.unlink()
        reference.symlink_to(second)
    elif mode == "bundle":
        (up / "provenance/boundary-record.txt").write_bytes(b"new execution record")
    else:
        (canonical / "sample_B").mkdir()
    problems = chain._integrity_problems(state)
    assert any("namespace" in problem or "directory" in problem or "reference" in problem
               for problem in problems)


def test_file_and_directory_types_cannot_be_equated_at_the_same_path(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "sample").write_bytes(b"")
    (b / "sample").mkdir()
    comparison = verify.compare(a, b)
    assert comparison.missing == ["sample"] and comparison.extra_directories == ["sample"]
    assert not comparison.structurally_equal


def test_relative_link_spellings_and_internal_parent_traversal_remain_valid(tmp_path):
    out = tmp_path / "out"
    (out / "data").mkdir(parents=True)
    (out / "data/index.bin").write_bytes(b"index")
    (out / "relative.bin").symlink_to("./data/../data/index.bin")
    (out / "absolute.bin").symlink_to(str(out / "data") + "/../data/index.bin")
    record(out)
    assert verify.compare(out, out).byte_identical
    inventory = outputs.read_inventory(out / "provenance/outputs.inventory.json",
                                       provenance.output_checksums(out))
    assert inventory["relative.bin"]["link_target"]["path"] == "./data/../data/index.bin"
    assert inventory["absolute.bin"]["link_target"]["path"] == "data/../data/index.bin"


def test_external_file_alias_retargeting_is_refused_even_with_identical_data(library, tmp_path):
    _, down = _trees(library("mini_up", "mini"))
    a, b = tmp_path / "first.gtf", tmp_path / "second.gtf"
    a.write_bytes(b"identical annotation")
    b.write_bytes(b"identical annotation")
    alias = tmp_path / "annotation.gtf"
    alias.symlink_to(a)
    up = tmp_path / "producer"
    record(up, inputs=[alias], params={"gtf": str(alias)})
    alias.unlink()
    alias.symlink_to(b)
    with pytest.raises(NfclawError, match="reference"):
        handoff.materialize(_rule({"params": {"fasta": {"upstream_param": "gtf"}}}),
            upstream_outdir=up, downstream_tree=down, dest=tmp_path / "handoff")


def test_nonregular_external_reference_is_refused_without_opening_a_fifo(library, tmp_path):
    import os
    _, down = _trees(library("mini_up", "mini"))
    source = tmp_path / "annotation.gtf"
    source.write_bytes(b"annotation")
    up = tmp_path / "producer"
    record(up, inputs=[source], params={"gtf": str(source)})
    source.unlink()
    os.mkfifo(source)
    with pytest.raises(NfclawError, match="reference"):
        handoff.materialize(_rule({"params": {"fasta": {"upstream_param": "gtf"}}}),
            upstream_outdir=up, downstream_tree=down, dest=tmp_path / "handoff")
