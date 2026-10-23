# ruff: noqa: F811
"""Historical evidence stays strict while checksum-only file chains remain usable."""
import json

import pytest

from runner import chain, handoff, provenance
from runner.errors import NfclawError
from test_chain import _spec, fake_runs  # noqa: F401
from test_handoff import _rule, _trees


def _record_input(outdir, path):
    hashes, nodes = provenance.snapshot_inputs([path])
    prov = outdir / "provenance"
    hashes = {**provenance.read_checksums(prov / "inputs.sha256", relative=False), **hashes}
    nodes = {**provenance.read_input_inventory(prov / "inputs.inventory.json"), **nodes}
    with (prov / "inputs.sha256").open("w") as stream:
        stream.write("".join(f"{digest}  {name}\n" for name, digest in hashes.items()))
    (prov / "inputs.inventory.json").write_text(json.dumps(nodes))


@pytest.mark.parametrize("damage",
                         ["missing-version", "unsupported-version", "unverified", None, 0])
def test_external_directory_handoff_requires_verified_prelaunch_namespace(
        library, finished_run, tmp_path, damage):
    _, down = _trees(library("mini_up", "mini"))
    reference = tmp_path / "index"
    reference.mkdir()
    (reference / "data.bin").write_bytes(b"index")
    up = finished_run(tmp_path / "up", {}, params={"gtf": str(reference)})
    _record_input(up, reference)
    manifest = up / "provenance/run_manifest.json"
    data = json.loads(manifest.read_text())
    data["dependency_inventory_version"] = 1
    manifest.write_text(json.dumps(data))
    rule = _rule({"params": {"fasta": {"upstream_param": "gtf"}}})
    handoff.materialize(rule, upstream_outdir=up, downstream_tree=down, dest=tmp_path / "before")
    if damage == "missing-version":
        del data["dependency_inventory_version"]
    elif damage == "unsupported-version":
        data["dependency_inventory_version"] = 99
    else:
        data["unverified_dependency_inventories"] = ["inputs"] if damage == "unverified" else damage
    manifest.write_text(json.dumps(data))
    with pytest.raises(NfclawError, match="reference"):
        handoff.materialize(rule, upstream_outdir=up, downstream_tree=down, dest=tmp_path / "after")


def test_legacy_file_reference_chain_retains_checksum_verification(
        library, fake_runs, tmp_path, monkeypatch):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): {
        "params": {"fasta": {"upstream_param": "gtf"}}}})
    reference = tmp_path / "legacy.gtf"
    reference.write_bytes(b"legacy annotation")
    launch = chain.orchestration.run_pipeline

    def run(name, **kw):
        result = launch(name, **kw)
        if not kw["check_only"]:
            prov = kw["outdir"] / "provenance"
            if name == "mini_up":
                (prov / "params.json").write_text(json.dumps({"gtf": str(reference)}))
            _record_input(kw["outdir"], reference)
            for artifact in ("inputs.inventory.json", "outputs.inventory.json"):
                (prov / artifact).unlink()
            path = prov / "run_manifest.json"
            manifest = json.loads(path.read_text())
            for field in ("dependency_inventory_version", "output_inventory_version"):
                manifest.pop(field, None)
            path.write_text(json.dumps(manifest))
        return result

    monkeypatch.setattr(chain.orchestration, "run_pipeline", run)
    out = tmp_path / "chain"
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    state, problems = chain.status(out)
    assert problems == []
    assert chain.status_exit_code(state, problems) == 0
    reference.write_bytes(b"changed legacy annotation")
    state, problems = chain.status(out)
    assert problems and chain.status_exit_code(state, problems) == 1
