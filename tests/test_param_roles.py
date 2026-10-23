"""Source-audited value roles: a parameter a release mislabels as a file is passed as written."""
import hashlib
import json
import subprocess
from pathlib import Path

from runner import inputs, schema

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "runner" / "param_roles.json").read_text(encoding="utf-8"))

# The shape nanoseq 2.0.0-3.0.0 ship: --protocol is a string (DNA, cDNA or directRNA) that the
# schema annotates as a samplesheet file.
MISLABELLED = {"$defs": {"input_output_options": {"properties": {
    "input": {"type": "string", "format": "file-path", "schema": "assets/schema_input.json"},
    "protocol": {"type": "string", "format": "file-path", "mimetype": "text/csv",
                 "schema": "assets/schema_input.json"}}}}}
GIT = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid"]


def _release(tmp_path, monkeypatch):
    repo = tmp_path / "pipeline"
    (repo / "assets").mkdir(parents=True)
    (repo / "assets/schema_input.json").write_text("{}")
    (repo / "nextflow_schema.json").write_text(json.dumps(MISLABELLED))
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(GIT + ["-C", str(repo), "add", "-A"], check=True)
    subprocess.run(GIT + ["-C", str(repo), "commit", "-q", "-m", "release"], check=True)
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    digest = hashlib.sha256((repo / "nextflow_schema.json").read_bytes()).hexdigest()
    registry = tmp_path / "param_roles.json"
    registry.write_text(json.dumps({digest: {
        "pipeline": "fixture", "releases": {"1.0.0": head},
        "values": {"protocol": {"source": ["workflows/fixture.nf:1"],
                                "use": "compared with literals"}}}}))
    monkeypatch.setattr(schema, "_PARAM_ROLES", registry)
    monkeypatch.chdir(tmp_path)
    return repo


def test_audited_value_parameter_is_passed_as_written(tmp_path, monkeypatch):
    repo = _release(tmp_path, monkeypatch)
    assert inputs.samplesheet_parameters(repo) == ("input",)
    assert schema.load_param_schema(repo).params["protocol"].fmt is None
    for protocol in ("DNA", "cDNA", "directRNA"):
        resolved = inputs.resolve(protocol, repo, param_name="protocol")
        assert resolved.value == protocol
        assert resolved.local_path is None and resolved.samplesheet_schema is None
    # The input keeps its own path and samplesheet annotations.
    assert inputs.samplesheet_schema(repo) == "assets/schema_input.json"


def test_value_role_does_not_extend_to_other_revisions(tmp_path, monkeypatch):
    repo = _release(tmp_path, monkeypatch)
    subprocess.run(
        GIT + ["-C", str(repo), "commit", "-q", "--allow-empty", "-m", "unaudited"], check=True)
    assert inputs.samplesheet_parameters(repo) == ("input", "protocol")
    assert schema.load_param_schema(repo).params["protocol"].fmt == "file-path"


def test_registry_records_exact_releases_and_audited_sources():
    assert REGISTRY
    for digest, audit in REGISTRY.items():
        assert len(digest) == 64 and audit["pipeline"] and audit["values"]
        assert audit["releases"] and all(len(commit) == 40 for commit in audit["releases"].values())
        assert all(evidence["source"] and evidence["use"] for evidence in audit["values"].values())
