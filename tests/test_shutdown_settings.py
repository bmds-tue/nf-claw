"""Operational shutdown margins must not change scientific parameters or launch deadlines."""
import json
import signal
import subprocess
import sys

import pytest

from runner import budget, execution, provenance, replay_guard
from runner.errors import NfclawError
from runner.submodule import SubmoduleStatus


def test_run_uses_configured_shutdown_grace(tmp_path, monkeypatch):
    monkeypatch.setenv("NFCLAW_SHUTDOWN_GRACE", "0.25")
    observed = []
    stop = execution._terminate

    def record(proc, grace=10, **kwargs):
        observed.append(grace)
        stop(proc, grace=grace, **kwargs)

    monkeypatch.setattr(execution, "_terminate", record)
    with pytest.raises(NfclawError):
        execution.run([sys.executable, "-c", "import time; time.sleep(30)"],
                      cwd=tmp_path, logs_dir=tmp_path / "logs", timeout_seconds=0.1)
    assert observed == [0.25]
    assert "timed out" in (tmp_path / "logs/run.log").read_text()


def test_invalid_shutdown_grace_never_starts_a_process(tmp_path, monkeypatch):
    monkeypatch.setenv("NFCLAW_SHUTDOWN_GRACE", "nan")
    receipt = tmp_path / "started"
    with pytest.raises(NfclawError, match="NFCLAW_SHUTDOWN_GRACE"):
        execution.run([sys.executable, "-c", f"open({str(receipt)!r}, 'w').close()"],
                      cwd=tmp_path, logs_dir=tmp_path / "logs", timeout_seconds=None)
    assert not receipt.exists()


def test_replay_command_uses_explicit_grace(tmp_path, monkeypatch):
    observed = []
    stop = replay_guard._stop_replay_group

    def record(proc, grace=10):
        observed.append(grace)
        stop(proc, grace=grace)

    monkeypatch.setattr(replay_guard, "_stop_replay_group", record)
    result = replay_guard.run_replay_command(
        [sys.executable, "-c", "print('finished')"], log=tmp_path / "run.log", grace=0.25)
    assert result == 0 and observed == [0.25]


@pytest.mark.parametrize("grace", [0, -1, float("nan"), float("inf")])
def test_replay_rejects_invalid_grace_before_launch(tmp_path, grace):
    receipt = tmp_path / "started"
    with pytest.raises(ValueError, match="shutdown grace"):
        replay_guard.run_replay_command(
            [sys.executable, "-c", f"open({str(receipt)!r}, 'w').close()"],
            log=tmp_path / "run.log", grace=grace)
    assert not receipt.exists()


def test_historical_replay_command_retains_default_grace(tmp_path, monkeypatch):
    observed = []
    stop = replay_guard._stop_replay_group

    def record(proc, grace=10):
        observed.append(grace)
        stop(proc, grace=grace)

    monkeypatch.setattr(replay_guard, "_stop_replay_group", record)
    assert replay_guard.run_replay_command(
        [sys.executable, "-c", "pass"], log=tmp_path / "run.log") == 0
    assert observed == [10]


def test_bundle_records_and_replays_its_original_shutdown_grace(tmp_path, monkeypatch,
                                                                no_engine_probe):
    monkeypatch.setenv("NFCLAW_SHUTDOWN_GRACE", "0.25")
    out = tmp_path / "out"
    tree = tmp_path / "tree"
    tree.mkdir()
    st = SubmoduleStatus("mini", tree, True, True, "1.0.0", "deadbeef", ())
    prov = provenance.write(outdir=out, pipeline="mini", command_str="echo replayed",
                            submodule=st, input_paths=[])
    manifest = json.loads((prov / "run_manifest.json").read_text())
    assert manifest["shutdown_grace_seconds"] == 0.25
    script = (prov / "commands.sh").read_text()
    assert '--shutdown-grace 0.25' in script
    # Changing ambient policy cannot rewrite the generated bundle's explicit margin.
    monkeypatch.setenv("NFCLAW_SHUTDOWN_GRACE", "nan")
    replay = subprocess.run([str(prov / "commands.sh"), str(tmp_path / "replay")],
                            capture_output=True, text=True, timeout=15)
    assert replay.returncode == 0, replay.stdout + replay.stderr


def test_nohup_signal_preference_is_preserved():
    previous = signal.getsignal(signal.SIGHUP)
    try:
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        with execution.stop_on_signals():
            assert signal.getsignal(signal.SIGHUP) is signal.SIG_IGN
    finally:
        signal.signal(signal.SIGHUP, previous)


def test_execution_setup_cannot_launch_after_absolute_deadline(tmp_path, monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(budget.time, "monotonic", lambda: clock[0])

    def delayed_setup():
        clock[0] = 2.0
        return None

    monkeypatch.setattr(execution, "_die_with_parent", delayed_setup)
    receipt = tmp_path / "started"
    with budget.scope(1), pytest.raises(NfclawError) as err:
        execution.run([sys.executable, "-c", f"open({str(receipt)!r}, 'w').close()"],
                      cwd=tmp_path, logs_dir=tmp_path / "logs", timeout_seconds=1)
    assert err.value.details["timeout_seconds"] == 1
    assert not receipt.exists()


@pytest.mark.parametrize("grace", [0, -1, float("nan"), float("inf"), "1; echo unsafe"])
def test_explicit_bundle_grace_is_validated_before_any_write(tmp_path, no_engine_probe, grace):
    out = tmp_path / "out"
    st = SubmoduleStatus("mini", tmp_path / "tree", False, False, "1.0.0", "deadbeef", ())
    with pytest.raises(NfclawError, match="shutdown_grace_seconds"):
        provenance.write(outdir=out, pipeline="mini", command_str="echo replayed",
                         submodule=st, input_paths=[], shutdown_grace_seconds=grace)
    assert not out.exists()
