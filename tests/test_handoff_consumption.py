"""Producer evidence must describe the actual local data consumed by its successor."""
# ruff: noqa: F811
import json
from pathlib import Path

import pytest

from runner import chain, consumption, handoff, provenance
from runner.errors import NfclawError
from runner.inputs import absolute_local_path
from test_chain import RULE, _spec, fake_runs  # noqa: F401
from test_handoff import _rule, _trees
from test_output_namespace import record


def _database_schema(tree):
    (tree / "assets/schema_input.json").write_text(json.dumps({"items": {
        "properties": {"sample": {"type": "string"},
                       "db_path": {"type": "string", "format": "path"}},
        "required": ["sample", "db_path"]}}))


def _linked_state(up, down, evidence, destination, sources):
    destination.mkdir(parents=True)
    path = destination / "handoff.json"
    path.write_text(json.dumps(evidence.record))
    record(down, inputs=sources)
    stages = []
    for index, out in enumerate((up, down), start=1):
        manifest_path = out / "provenance/run_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        sid = f"stage{index}"
        manifest["chain"] = {"id": "audit", "stage": sid, "index": index,
                             "upstream": None if index == 1 else
                             {"handoff_sha256": provenance._sha256(path)}}
        manifest_path.write_text(json.dumps(manifest))
        stages.append({"id": sid, "pipeline": "fixture", "index": index, "outdir": str(out),
                       "status": "success", "version": manifest["version"], "commit": manifest["commit"],
                       "handoff": None if index == 1 else str(path)})
    return {"chain_id": "audit", "outcome": "success", "stages": stages}


def test_database_samplesheet_refuses_directory_bytes_changed_after_publication(library, tmp_path):
    _, tree = _trees(library("mini_up", "mini"))
    _database_schema(tree)
    up = tmp_path / "up"
    (up / "db/empty").mkdir(parents=True)
    (up / "db/index.bin").write_bytes(b"original database")
    (up / "database.csv").write_text(f"sample,db_path\nDB,{up}/db\n")
    record(up)
    (up / "db/index.bin").write_bytes(b"modified database")
    rule = _rule({"params": {"input": {"samplesheet": "database.csv",
                                         "provides": ["sample", "db_path"]}}})
    with pytest.raises(NfclawError, match="changed|historical"):
        handoff.materialize(rule, upstream_outdir=up, downstream_tree=tree, dest=tmp_path / "handoff")


@pytest.mark.parametrize("kind", ["file", "sheet", "directory", "glob", "published_reference"])
@pytest.mark.parametrize("damage", ["bytes", "missing"])
@pytest.mark.parametrize("legacy", [False, True])
def test_lineage_matches_downstream_prelaunch_data_to_producer(library, tmp_path, kind, damage, legacy):
    _, tree = _trees(library("mini_up", "mini"))
    up, down = tmp_path / "up", tmp_path / "down"
    (up / "db/empty").mkdir(parents=True)
    data = up / "db/index.bin"
    data.write_bytes(b"original data")
    if kind == "file":
        rule = _rule({"params": {"fasta": {"file": "db/index.bin"}}})
    elif kind == "published_reference":
        rule = _rule({"params": {"fasta": {"upstream_param": "gtf"}}})
    else:
        _database_schema(tree)
        sheet_value = up / "db" if kind == "directory" else data
        if kind == "glob":
            sheet_value = up / "db/*.bin"
            schema = json.loads((tree / "assets/schema_input.json").read_text())
            schema["items"]["properties"]["db_path"]["format"] = "file-path-pattern"
            (tree / "assets/schema_input.json").write_text(json.dumps(schema))
        (up / "database.csv").write_text(f"sample,db_path\nDB,{sheet_value}\n")
        rule = _rule({"params": {"input": {"samplesheet": "database.csv",
                                             "provides": ["sample", "db_path"]}}})
    record(up, params={"gtf": str(data)} if kind == "published_reference" else None)
    evidence = handoff.materialize(rule, upstream_outdir=up, downstream_tree=tree, dest=tmp_path / "snapshot")
    if legacy:
        for item in evidence.record["params"].values():
            for key in ("consumed_sources", "consumed_dependencies", "consumed_inventory"):
                item.pop(key, None)
    sources = [data] if kind in ("file", "published_reference") else [tmp_path / "snapshot/input.csv", sheet_value]
    state = _linked_state(up, down, evidence, tmp_path / "link", sources)
    assert chain._integrity_problems(state) == []
    checksums = down / "provenance/inputs.sha256"
    consumed = provenance.read_checksums(checksums, relative=False)
    if damage == "bytes":
        consumed[str(data)] = "0" * 64
    else:
        consumed.pop(str(data))
    checksums.write_text(provenance.checksum_text(consumed))
    problems = chain._integrity_problems(state)
    assert problems, "restored producer bytes cannot hide different or unrecorded consumed data"
    assert chain.status_exit_code(state, problems) == 1


def test_lineage_refuses_extra_glob_members_consumed_then_removed(library, tmp_path):
    _, tree = _trees(library("mini_up", "mini"))
    _database_schema(tree)
    schema = json.loads((tree / "assets/schema_input.json").read_text())
    schema["items"]["properties"]["db_path"]["format"] = "file-path-pattern"
    (tree / "assets/schema_input.json").write_text(json.dumps(schema))
    up, down = tmp_path / "up", tmp_path / "down"
    (up / "db").mkdir(parents=True)
    (up / "db/original.bin").write_bytes(b"original")
    pattern = up / "db/*.bin"
    (up / "database.csv").write_text(f"sample,db_path\nDB,{pattern}\n")
    record(up)
    evidence = handoff.materialize(_rule({"params": {"input": {
        "samplesheet": "database.csv", "provides": ["sample", "db_path"]}}}),
        upstream_outdir=up, downstream_tree=tree, dest=tmp_path / "snapshot")
    extra = up / "db/extra.bin"
    extra.write_bytes(b"extra data consumed downstream")
    state = _linked_state(up, down, evidence, tmp_path / "link", [tmp_path / "snapshot/input.csv", pattern])
    extra.unlink()
    assert chain._integrity_problems(state), "glob membership must use recorded consumption, not live matches"


@pytest.mark.parametrize("pattern", ["*.fa", "**/*.fa"])
def test_glob_consumption_does_not_include_separately_declared_hidden_references(tmp_path, pattern):
    up = tmp_path / "up"
    up.mkdir()
    data, hidden = up / "ordinary.fa", up / ".reference.fa"
    data.write_bytes(b">ordinary\nACGT\n")
    hidden.write_bytes(b">reference\nTGCA\n")
    record(up)
    evidence = handoff.consumption_evidence([up / pattern], up)
    hashes, nodes = provenance.snapshot_inputs([up / pattern, hidden])
    assert consumption.agrees(evidence, hashes, nodes)
    hidden_folder = up / ".hidden"
    hidden_folder.mkdir()
    nested = hidden_folder / "ordinary.fa"
    nested.write_bytes(data.read_bytes())
    hashes, nodes = provenance.snapshot_inputs([up / pattern, nested])
    assert consumption.agrees(evidence, hashes, nodes)


def test_scalar_handoff_preserves_parent_resolution_and_final_basename(library, tmp_path):
    _, tree = _trees(library("mini_up", "mini"))
    up, down = tmp_path / "up", tmp_path / "down"
    (up / "db").mkdir(parents=True)
    (up / "db/index.bin").write_bytes(b"correct data")
    (up / "alias").symlink_to(up / "db", target_is_directory=True)
    record(up)
    evidence = handoff.materialize(_rule({"params": {"fasta": {"file": "alias/index.bin"}}}),
        upstream_outdir=up, downstream_tree=tree, dest=tmp_path / "snapshot")
    state = _linked_state(up, down, evidence, tmp_path / "link", [absolute_local_path(up / "alias/index.bin")])
    assert chain._integrity_problems(state) == []


def test_chain_cannot_report_success_after_consuming_changed_then_restored_data(
        library, fake_runs, tmp_path, monkeypatch):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): RULE})
    out = tmp_path / "chain"
    original = chain.orchestration.run_pipeline

    def changed_before_consumption(name, **options):
        if name != "mini" or options["check_only"]:
            return original(name, **options)
        data = out / "01-mini_up/fastq/A_1.fastq.gz"
        data.write_bytes(b"different data consumed downstream")
        try:
            return original(name, **options)
        finally:
            data.write_bytes(b"1")

    monkeypatch.setattr(chain.orchestration, "run_pipeline", changed_before_consumption)
    with pytest.raises(NfclawError, match="lineage|consumed"):
        chain.run_chain(_spec(), repo_root=root, outdir=out)
    state, problems = chain.status(out)
    assert state["outcome"] != "success" and problems


@pytest.mark.parametrize("kind", ["direct", "build"])
@pytest.mark.parametrize("changed", [False, True])
def test_mixed_pattern_and_declared_paths_bind_the_actual_consumer_bytes(library, tmp_path, kind, changed):
    _, tree = _trees(library("mini_up", "mini"))
    (tree / "assets/schema_input.json").write_text(json.dumps({"items": {
        "properties": {"sample": {"type": "string"},
                       "fastq_1": {"type": "string", "pattern": r"^\S+\.fastq\.gz$"},
                       "reference": {"type": "string", "format": "file-path"}},
        "required": ["sample", "fastq_1", "reference"]}}))
    up, down = tmp_path / "up", tmp_path / "down"
    up.mkdir()
    reads, reference = up / "A.fastq.gz", up / "reference.fa"
    original = b"original read identity"
    reads.write_bytes(original)
    reference.write_bytes(b">reference\nACGT\n")
    (up / "samples.csv").write_text("sample,fastq_1,reference\nA,A.fastq.gz,reference.fa\n")
    record(up)
    spec = ({"samplesheet": "samples.csv", "provides": ["sample", "fastq_1", "reference"]}
            if kind == "direct" else {"build": {"rows": "{sample}.fastq.gz", "columns": {
                "sample": "{sample}", "fastq_1": "{sample}.fastq.gz", "reference": "reference.fa"}}})
    evidence = handoff.materialize(_rule({"params": {"input": spec}}), upstream_outdir=up,
                                  downstream_tree=tree, dest=tmp_path / "snapshot")
    if changed:
        reads.write_bytes(b"different bytes observed by the consumer")
    state = _linked_state(up, down, evidence, tmp_path / "link",
                          [Path(evidence.params["input"]), reads, reference])
    reads.write_bytes(original)
    problems = chain._integrity_problems(state)
    if changed:
        assert problems, "a declared reference must not mask different pattern-only read bytes"
    else:
        assert problems == []
        assert evidence.record["params"]["input"]["consumed_sources"] == sorted(map(str, (reads, reference)))
