# ruff: noqa: F811
"""An explicit timeout covers validation, execution and final scientific attribution."""
import json
import os
import subprocess
import sys
import time

import pytest

from runner import budget, chain, orchestration, probes, provenance
from runner.errors import ErrorCode, NfclawError
from test_chain import fake_runs  # noqa: F401


@pytest.fixture
def clock(monkeypatch):
    value = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: value[0])
    return value


def _run(root, outdir, *, timeout=5, write_provenance=True):
    return orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=outdir, profile="docker",
        params_file=None, cli_overrides={}, resume=False, demo=True, check_only=False,
        write_provenance=write_provenance, timeout_seconds=timeout)


@pytest.fixture
def prepared(library, monkeypatch):
    root = library("mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **kw: [])
    return root


def test_pipeline_does_not_launch_after_input_snapshot_exhausts_deadline(
        prepared, monkeypatch, clock, tmp_path):
    snapshot = provenance.snapshot_inputs
    launches = []

    def slow_snapshot(*args, **kwargs):
        result = snapshot(*args, **kwargs)
        clock[0] = 10
        return result

    monkeypatch.setattr(provenance, "snapshot_inputs", slow_snapshot)
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **kw: launches.append(kw))
    with pytest.raises(NfclawError) as error:
        _run(prepared, tmp_path / "out")
    assert error.value.code is ErrorCode.EXECUTION_FAILED
    assert error.value.details["timeout_seconds"] == 5
    assert launches == []


def test_pipeline_launch_receives_fractional_budget_after_preparation(
        prepared, monkeypatch, clock, tmp_path):
    launches = []

    def preflight(**kwargs):
        clock[0] = 0.25
        return []

    monkeypatch.setattr(orchestration.preflight, "check_environment", preflight)
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **kw: launches.append(kw))
    _run(prepared, tmp_path / "out", timeout=1)
    assert launches[0]["timeout_seconds"] == pytest.approx(0.75)


def test_expiry_while_hashing_outputs_preserves_failed_bundle_without_rehashing(
        prepared, monkeypatch, clock, tmp_path):
    outdir = tmp_path / "out"
    hashed = []
    sha256 = provenance._sha256

    def execute(*args, **kwargs):
        (outdir / "result.txt").write_text("scientific evidence\n")

    def slow_hash(path):
        digest = sha256(path)
        if path.name == "result.txt":
            hashed.append(path)
            clock[0] = 10
        return digest

    monkeypatch.setattr(orchestration.execution, "run", execute)
    monkeypatch.setattr(provenance, "_sha256", slow_hash)
    with pytest.raises(NfclawError) as error:
        _run(prepared, outdir)
    assert error.value.details["timeout_seconds"] == 5
    assert hashed == [outdir / "result.txt"]
    bundle = outdir / "provenance"
    assert json.loads((bundle / "run_manifest.json").read_text())["outcome"] == "failed"
    assert (bundle / "commands.sh").is_file()
    assert "result.txt" in (bundle / "outputs.sha256").read_text()
    assert not (bundle / "logs/run.log").read_text().splitlines()[-1].endswith(": success")


def test_no_provenance_still_refuses_success_after_attribution_exhausts_deadline(
        prepared, monkeypatch, clock, tmp_path):
    compare = orchestration.dependency_stability.compare

    def slow_compare(**kwargs):
        result = compare(**kwargs)
        clock[0] = 10
        return result

    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **kw: None)
    monkeypatch.setattr(orchestration.dependency_stability, "compare", slow_compare)
    outdir = tmp_path / "out"
    with pytest.raises(NfclawError) as error:
        _run(prepared, outdir, write_provenance=False)
    assert error.value.details["timeout_seconds"] == 5
    last_line = (outdir / "provenance/logs/run.log").read_text().splitlines()[-1]
    assert not last_line.endswith(": success")


def test_unlimited_default_survives_long_preparation(prepared, monkeypatch, clock, tmp_path):
    launches = []

    def preflight(**kwargs):
        clock[0] = 100000
        return []

    monkeypatch.setattr(orchestration.preflight, "check_environment", preflight)
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **kw: launches.append(kw))
    result = _run(prepared, tmp_path / "out", timeout=None)
    assert not result.checked_only
    assert launches[0]["timeout_seconds"] is None


def test_chain_preserves_fractional_remainder_for_stage_launch(
        library, fake_runs, monkeypatch, clock, tmp_path):
    root = library("mini")
    validate = chain._check

    def slow_validation(*args, **kwargs):
        result = validate(*args, **kwargs)
        clock[0] = 0.8
        return result

    monkeypatch.setattr(chain, "_check", slow_validation)
    spec = chain.parse_spec({"stages": [{"pipeline": "mini", "demo": True}]})
    result = chain.run_chain(spec, repo_root=root, outdir=tmp_path / "chain", timeout_seconds=1)
    assert result.outcome == "success"
    assert fake_runs.calls[0]["timeout_seconds"] == pytest.approx(0.2)


def test_chain_final_lineage_cannot_publish_success_after_deadline(
        library, fake_runs, monkeypatch, clock, tmp_path):
    root = library("mini")
    integrity = chain._integrity_problems

    def slow_integrity(*args, **kwargs):
        result = integrity(*args, **kwargs)
        clock[0] = 10
        return result

    monkeypatch.setattr(chain, "_integrity_problems", slow_integrity)
    spec = chain.parse_spec({"stages": [{"pipeline": "mini", "demo": True}]})
    outdir = tmp_path / "chain"
    with pytest.raises(NfclawError) as error:
        chain.run_chain(spec, repo_root=root, outdir=outdir, timeout_seconds=5)
    assert error.value.details["timeout_seconds"] == 5
    state = json.loads((outdir / "chain/state.json").read_text())
    assert state["outcome"] != "success"
    assert not (outdir / "chain/logs/chain.log").read_text().splitlines()[-1].endswith(": success")


def test_nested_unlimited_scope_inherits_original_deadline_and_resets(clock):
    @budget.bounded
    def validate(*, timeout_seconds):
        assert budget.remaining(30) == pytest.approx(0.75)
        clock[0] = 2
        budget.check()

    with budget.scope(1):
        clock[0] = 0.25
        with pytest.raises(NfclawError) as error:
            validate(timeout_seconds=None)
        assert error.value.details["timeout_seconds"] == 1
        with budget.suspend():
            assert budget.remaining() is None
        with pytest.raises(NfclawError):
            budget.check()
    assert budget.remaining() is None
    assert budget.remaining(30) == 30


def test_probe_respects_overall_deadline_for_real_child(tmp_path):
    marker = tmp_path / "late"
    started = time.monotonic()
    with budget.scope(0.1):
        with pytest.raises(NfclawError) as error:
            probes.capture([sys.executable, "-c",
                "import pathlib,sys,time; time.sleep(2); pathlib.Path(sys.argv[1]).touch()",
                str(marker)], timeout=5)
    assert error.value.details["timeout_seconds"] == 0.1
    assert time.monotonic() - started < 1.5
    assert not marker.exists()


def test_probe_operation_limit_does_not_become_overall_timeout():
    with budget.scope(5):
        with pytest.raises(subprocess.TimeoutExpired):
            probes.capture([sys.executable, "-c", "import time; time.sleep(2)"], timeout=0.03)


def test_deadline_detected_after_probe_exit_still_stops_its_process_group(
        monkeypatch, clock, tmp_path):
    if not hasattr(os, "killpg"):
        pytest.skip("process groups require POSIX")
    marker = tmp_path / "orphan"
    communicate = subprocess.Popen.communicate

    def complete_then_expire(proc, *args, **kwargs):
        result = communicate(proc, *args, **kwargs)
        clock[0] = 2
        return result

    monkeypatch.setattr(subprocess.Popen, "communicate", complete_then_expire)
    child = "import pathlib,sys,time; time.sleep(.2); pathlib.Path(sys.argv[1]).touch()"
    parent = (
        "import subprocess,sys; subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]],"
        "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)")
    with budget.scope(1):
        with pytest.raises(NfclawError):
            probes.capture([sys.executable, "-c", parent, child, str(marker)], timeout=5)
    time.sleep(0.3)
    assert not marker.exists()


def test_version_metadata_uses_configured_operation_limit(monkeypatch):
    observed = []
    monkeypatch.setenv("NFCLAW_VERSION_TIMEOUT", "0.125")

    def capture(command, **kwargs):
        observed.append(kwargs["timeout"])
        return subprocess.CompletedProcess(command, 0, "nextflow version 25.10.4", "")

    monkeypatch.setattr(provenance, "capture", capture)
    assert provenance._nextflow_version() == "nextflow version 25.10.4"
    assert observed == [0.125]


def test_deadline_crossing_manifest_publication_rewrites_only_failed_metadata(
        prepared, monkeypatch, clock, tmp_path):
    outdir = tmp_path / "out"
    atomic_text = provenance._atomic_text
    publications = []

    def slow_publication(path, content, **kwargs):
        atomic_text(path, content, **kwargs)
        if path.name == "run_manifest.json":
            publications.append(json.loads(content)["outcome"])
            clock[0] = 10

    monkeypatch.setattr(provenance, "_atomic_text", slow_publication)
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **kw: None)
    with pytest.raises(NfclawError) as error:
        _run(prepared, outdir)
    assert error.value.details["timeout_seconds"] == 5
    assert publications == ["success", "failed"]
    assert json.loads((outdir / "provenance/run_manifest.json").read_text())["outcome"] == "failed"


def test_original_failure_and_bundle_survive_expired_deadline(
        prepared, monkeypatch, clock, tmp_path):
    outdir = tmp_path / "out"
    original = NfclawError(ErrorCode.EXECUTION_FAILED, "original analysis failure")

    def execute(*args, **kwargs):
        (outdir / "partial.txt").write_text("completed task evidence")
        clock[0] = 10
        raise original

    monkeypatch.setattr(orchestration.execution, "run", execute)
    with pytest.raises(NfclawError) as error:
        _run(prepared, outdir)
    assert error.value is original
    bundle = outdir / "provenance"
    assert json.loads((bundle / "run_manifest.json").read_text())["outcome"] == "failed"
    assert "partial.txt" in (bundle / "outputs.sha256").read_text()
    assert (bundle / "commands.sh").is_file()


def test_last_success_checkpoint_downgrades_completed_manifest_without_rehashing(
        prepared, monkeypatch, clock, tmp_path):
    outdir = tmp_path / "out"
    record = provenance.write
    calls = []

    def complete_then_expire(**kwargs):
        calls.append(kwargs["outcome"])
        result = record(**kwargs)
        clock[0] = 10
        return result

    monkeypatch.setattr(provenance, "write", complete_then_expire)
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **kw: None)
    with pytest.raises(NfclawError) as error:
        _run(prepared, outdir)
    assert error.value.details["timeout_seconds"] == 5
    assert calls == ["success"]
    assert json.loads((outdir / "provenance/run_manifest.json").read_text())["outcome"] == "failed"
    last_line = (outdir / "provenance/logs/run.log").read_text().splitlines()[-1]
    assert not last_line.endswith(": success")


def test_failed_timeout_metadata_rewrite_cannot_leave_successful_manifest(
        prepared, monkeypatch, clock, tmp_path):
    outdir = tmp_path / "out"
    atomic_text = provenance._atomic_text

    def disk_full_after_publication(path, content, **kwargs):
        if path.name == "run_manifest.json":
            if json.loads(content)["outcome"] == "failed":
                raise OSError("disk full")
            atomic_text(path, content, **kwargs)
            clock[0] = 10
        else:
            atomic_text(path, content, **kwargs)

    monkeypatch.setattr(provenance, "_atomic_text", disk_full_after_publication)
    monkeypatch.setattr(orchestration.execution, "run", lambda *a, **kw: None)
    with pytest.raises(NfclawError) as error:
        _run(prepared, outdir)
    assert error.value.details["timeout_seconds"] == 5
    manifest = outdir / "provenance/run_manifest.json"
    assert not manifest.exists() or json.loads(manifest.read_text())["outcome"] == "failed"


def test_shorter_nested_budget_resets_without_extending_parent(clock):
    with budget.scope(5):
        clock[0] = 1
        with budget.scope(100):
            assert budget.remaining() == 4
        with budget.scope(1):
            assert budget.remaining() == 1
            clock[0] = 2
            with pytest.raises(NfclawError) as error:
                budget.check()
            assert error.value.details["timeout_seconds"] == 1
        assert budget.remaining() == 3


def test_metadata_probe_deadline_still_emits_failed_bundle(prepared, monkeypatch, tmp_path):
    def slow_version(env_extra=None):
        probes.capture([sys.executable, "-c", "import time; time.sleep(2)"], timeout=30)
        pytest.fail("the metadata probe must exhaust the overall budget")

    monkeypatch.setattr(provenance, "_nextflow_version", slow_version)
    st = orchestration.versions.ensure("mini", None, pipelines_dir=prepared / "pipelines",
                                       repo_root=prepared)
    outdir = tmp_path / "out"
    with budget.scope(0.05):
        with pytest.raises(NfclawError) as error:
            provenance.write(outdir=outdir, pipeline="mini", command_str="nextflow run mini",
                             submodule=st, input_paths=[])
    assert error.value.details["timeout_seconds"] == 0.05
    assert json.loads((outdir / "provenance/run_manifest.json").read_text())["outcome"] == "failed"
    assert (outdir / "provenance/commands.sh").is_file()


def test_quick_chain_status_reports_unchecked_lineage_without_hashing(
        library, fake_runs, monkeypatch, tmp_path):
    root = library("mini")
    spec = chain.parse_spec({"stages": [{"pipeline": "mini", "demo": True}]})
    outdir = tmp_path / "chain"
    chain.run_chain(spec, repo_root=root, outdir=outdir)
    # A quick poll describes execution even when live results no longer match their bundle.
    (outdir / "01-mini/result.txt").write_text("changed after execution")

    def forbidden_hashing(*args, **kwargs):
        pytest.fail("quick status must not verify lineage")

    with monkeypatch.context() as local:
        local.setattr(chain, "_integrity_problems", forbidden_hashing)
        state, problems = chain.status(outdir, quick=True)
    assert problems == []
    assert state["lineage_verification"] == "not_checked"
    assert "lineage: not checked" in chain.format_status(state, problems)
    assert "lineage: verified" not in chain.format_status(state, problems)
    full_state, full_problems = chain.status(outdir)
    assert full_problems
    assert full_state["lineage_verification"] == "broken"
