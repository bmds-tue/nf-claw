import json
import hashlib

import pytest

from runner import cli, orchestration, resources
from runner.errors import ErrorCode, NfclawError


def test_overlapping_resume_cannot_overwrite_active_run(library, tmp_path, monkeypatch):
    root = library("mini")
    outdir = tmp_path / "results"
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **kwargs: [])
    monkeypatch.setattr(orchestration.engine_version, "check", lambda *args, **kwargs: [])
    entered = []

    def launch(*args, **kwargs):
        entered.append(True)
        if len(entered) == 1:
            with pytest.raises(NfclawError, match="another nfclaw run") as exc:
                orchestration.run_pipeline(
                    "mini", repo_root=root, input_path=None, outdir=outdir,
                    profile="docker", params_file=None, cli_overrides={"aligner": "hisat2"},
                    resume=True, demo=True, check_only=False, write_provenance=False,
                    timeout_seconds=None)
            assert exc.value.code == ErrorCode.ENVIRONMENT

    monkeypatch.setattr(orchestration.execution, "run", launch)
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=outdir,
        profile="docker", params_file=None, cli_overrides={"aligner": "star"},
        resume=False, demo=True, check_only=False, write_provenance=False,
        timeout_seconds=None)
    assert len(entered) == 1
    assert json.loads((outdir / "provenance" / "params.json").read_text())["aligner"] == "star"


@pytest.mark.parametrize("value", ["0.GB", "0.0 MB"])
def test_zero_memory_limit_is_refused(value):
    with pytest.raises(NfclawError, match="--limit-memory"):
        resources.parse(None, value, None)


@pytest.mark.parametrize("value", ["0.h", "0.0 ms"])
def test_zero_time_limit_is_refused(value):
    with pytest.raises(NfclawError, match="--limit-time"):
        resources.parse(None, None, value)


def test_environment_nul_is_refused_before_subprocess_launch():
    with pytest.raises(NfclawError, match="NXF_JVM_ARGS"):
        resources.parse_nxf_env({"NXF_JVM_ARGS": "value\x00broken"})


def test_strict_verification_rejects_changed_scientific_result(tmp_path, monkeypatch):
    original, replay = tmp_path / "original", tmp_path / "replay"
    for out, text in ((original, "chr1\t10\tA\tG\n"), (replay, "chr1\t10\tA\tT\n")):
        out.mkdir()
        (out / "calls.tsv").write_text(text)
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    assert cli.main(["verify", str(replay), "--against", str(original), "--strict"]) == 1


def test_provenance_snapshots_sheet_data_and_config_before_execution(library, tmp_path, monkeypatch):
    root = library("mini")
    data = tmp_path / "reads.fastq.gz"
    data.write_bytes(b"original reads")
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f"sample,fastq_1\nsample1,{data}\n")
    config = tmp_path / "analysis.config"
    original_config = b"params.aligner = 'star'\n"
    config.write_bytes(original_config)
    outdir = tmp_path / "results"
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **kwargs: [])
    monkeypatch.setattr(orchestration.engine_version, "check", lambda *args, **kwargs: [])
    monkeypatch.setattr(orchestration.provenance, "_nextflow_version", lambda *args: "test")

    def launch(*args, **kwargs):
        data.write_bytes(b"changed reads")
        config.write_bytes(b"params.aligner = 'hisat2'\n")

    monkeypatch.setattr(orchestration.execution, "run", launch)
    orchestration.run_pipeline(
        "mini", repo_root=root, input_path=sheet, outdir=outdir,
        profile="docker", params_file=None, cli_overrides={}, configs=[str(config)],
        resume=False, demo=False, check_only=False, write_provenance=True,
        timeout_seconds=None)
    assert f"{hashlib.sha256(b'original reads').hexdigest()}  {data}" in (
        outdir / "provenance" / "inputs.sha256").read_text()
    assert f"{hashlib.sha256(original_config).hexdigest()}  {config}" in (
        outdir / "provenance" / "configs.sha256").read_text()


def test_planned_pipeline_tree_is_reused_for_check(library, tmp_path, monkeypatch):
    root = library("mini")
    planned = orchestration.versions.ensure(
        "mini", None, pipelines_dir=root / "pipelines", repo_root=root)

    def unexpected_resolution(*args, **kwargs):
        pytest.fail("a frozen chain must not resolve its pipeline version a second time")

    monkeypatch.setattr(orchestration.versions, "ensure", unexpected_resolution)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **kwargs: [])
    monkeypatch.setattr(orchestration.engine_version, "check", lambda *args, **kwargs: [])
    result = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "results",
        profile="docker", params_file=None, cli_overrides={}, resume=False,
        demo=True, check_only=True, write_provenance=False,
        timeout_seconds=None, resolved_tree=planned)
    assert str(planned.path) in result.command


@pytest.mark.parametrize("exists", [None, False])
def test_pipeline_can_create_an_optional_path_destination(library, tmp_path, monkeypatch, exists):
    root = library("mini")
    source = root / "pipelines/mini/upstream/nextflow_schema.json"
    schema = json.loads(source.read_text())
    field = {"type": "string", "format": "directory-path"}
    if exists is not None:
        field["exists"] = exists
    schema["definitions"]["reference_genome_options"]["properties"]["reference_cache"] = field
    source.write_text(json.dumps(schema))
    cache = tmp_path / "new-cache"
    outdir = tmp_path / "results"
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **kwargs: [])
    monkeypatch.setattr(orchestration.engine_version, "check", lambda *args, **kwargs: [])
    monkeypatch.setattr(orchestration.provenance, "_nextflow_version", lambda *args: "test")

    def launch(*args, **kwargs):
        cache.mkdir()
        (cache / "database.bin").write_bytes(b"generated reference")

    monkeypatch.setattr(orchestration.execution, "run", launch)
    result = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=outdir,
        profile="docker", params_file=None, cli_overrides={"reference_cache": str(cache)},
        resume=False, demo=True, check_only=False, write_provenance=True, timeout_seconds=None)
    assert (cache / "database.bin").is_file()
    manifest = json.loads((outdir / "provenance/run_manifest.json").read_text())
    assert manifest["unverified_local_paths"] == {"reference_cache": str(cache)}
    assert any("reference_cache" in warning for warning in result.warnings)


def test_missing_schema_required_path_is_still_refused(library, tmp_path, monkeypatch):
    root = library("mini")
    source = root / "pipelines/mini/upstream/nextflow_schema.json"
    schema = json.loads(source.read_text())
    schema["definitions"]["reference_genome_options"]["properties"]["fasta"]["exists"] = True
    source.write_text(json.dumps(schema))
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **kwargs: [])
    monkeypatch.setattr(orchestration.engine_version, "check", lambda *args, **kwargs: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *args, **kwargs: pytest.fail("launched"))
    with pytest.raises(NfclawError, match="cannot snapshot local run dependencies"):
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "results",
            profile="docker", params_file=None, cli_overrides={"fasta": str(tmp_path / "missing.fa")},
            resume=False, demo=True, check_only=False, write_provenance=True, timeout_seconds=None)


@pytest.mark.parametrize("kind", ["directory", "glob"])
def test_optional_existing_source_with_broken_member_is_refused(
        library, tmp_path, monkeypatch, kind):
    root = library("mini")
    source = root / "pipelines/mini/upstream/nextflow_schema.json"
    schema = json.loads(source.read_text())
    schema["definitions"]["reference_genome_options"]["properties"]["reference_cache"] = {
        "type": "string", "format": "file-path-pattern" if kind == "glob" else "directory-path"}
    source.write_text(json.dumps(schema))
    cache = tmp_path / "existing-cache"
    cache.mkdir()
    (cache / "index.bin").write_bytes(b"important reference bytes")
    (cache / "dangling.bin").symlink_to(tmp_path / "missing-reference")
    if kind == "glob":
        value = tmp_path / "existing-*"
    else:
        value = cache
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **kwargs: [])
    monkeypatch.setattr(orchestration.engine_version, "check", lambda *args, **kwargs: [])
    monkeypatch.setattr(orchestration.execution, "run", lambda *args, **kwargs: pytest.fail("launched"))
    # Directory inputs and patterns inspect staged entries before the dependency snapshot.
    # Broken members must remain fatal and never reach pipeline execution.
    with pytest.raises(NfclawError, match="cannot inspect local input filenames") as exc:
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=None, outdir=tmp_path / "results",
            profile="docker", params_file=None, cli_overrides={"reference_cache": str(value)},
            resume=False, demo=True, check_only=False, write_provenance=True, timeout_seconds=None)
    assert exc.value.code == ErrorCode.PARAMS_INVALID
    assert not (tmp_path / "results").exists()


@pytest.mark.parametrize("check_only", [True, False])
def test_unsafe_remote_input_is_refused_before_environment_probe_or_launch(
        library, tmp_path, monkeypatch, check_only):
    root = library("mini")
    outdir = tmp_path / "results"

    def must_not_reach(*args, **kwargs):
        pytest.fail("unsafe input reached environment probing or task execution")

    monkeypatch.setattr(orchestration.preflight, "check_environment", must_not_reach)
    monkeypatch.setattr(orchestration.execution, "run", must_not_reach)
    with pytest.raises(NfclawError) as exc:
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path="https://example.org/reads$(id).csv",
            outdir=outdir, profile="docker", params_file=None, cli_overrides={},
            resume=False, demo=False, check_only=check_only, write_provenance=True,
            timeout_seconds=None)
    assert exc.value.code == ErrorCode.PARAMS_INVALID
    assert "unsafe remote input filename" in str(exc.value)
    assert not outdir.exists()


@pytest.mark.parametrize("check_only", [True, False])
def test_unsafe_directory_child_is_refused_before_probing_or_execution(
        library, tmp_path, monkeypatch, check_only):
    root = library("mini")
    tree = root / "pipelines/mini/upstream"
    (tree / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "directory-path"},
        "outdir": {"type": "string", "format": "directory-path"}}}))
    source = tmp_path / "data"
    source.mkdir()
    (source / "unsafe$(id)").mkdir()
    outdir = tmp_path / "results"

    def must_not_reach(*args, **kwargs):
        pytest.fail("unsafe directory entry reached environment probing or task execution")

    monkeypatch.setattr(orchestration.preflight, "check_environment", must_not_reach)
    monkeypatch.setattr(orchestration.execution, "run", must_not_reach)
    with pytest.raises(NfclawError) as exc:
        orchestration.run_pipeline(
            "mini", repo_root=root, input_path=source, outdir=outdir,
            profile="docker", params_file=None, cli_overrides={}, resume=False,
            demo=False, check_only=check_only, write_provenance=True,
            timeout_seconds=None)
    assert exc.value.code == ErrorCode.PARAMS_INVALID
    assert "unsafe local input filename" in str(exc.value)
    assert not outdir.exists()
