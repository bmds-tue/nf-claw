"""Real process controls: foreground cancellation owns detached metadata helpers too."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from runner import jobs, mcp_tools, process_identity
from runner.mcp_server import Context


@pytest.mark.parametrize("stop", ["timeout", "cancel", "disconnect", "success"])
def test_foreground_owns_independently_grouped_helpers(tmp_path, monkeypatch, stop):
    pidfile = tmp_path / "helper.json"
    # Exit the intermediate parent immediately, before the foreground worker's next inventory.
    # Linux's subreaper must adopt the escaped grandchild. On Darwin retain the intermediate
    # until an inventory can record it; Darwin does not provide Linux's subreaper facility.
    delay = "0" if sys.platform == "linux" else "0.5"
    helper = ("import json, os, time; from pathlib import Path; "
              "from runner import process_identity; "
              f"Path({str(pidfile)!r}).write_text(json.dumps(process_identity.read(os.getpid()))); "
              "time.sleep(60)")
    intermediate = ("import subprocess, sys, time; "
                    f"subprocess.Popen([sys.executable, '-c', {helper!r}], "
                    "start_new_session=True); "
                    f"time.sleep({delay})")
    command = [sys.executable, "-c", (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {intermediate!r}], start_new_session=True); "
        f"time.sleep({1 if stop == 'success' else 60})")]
    monkeypatch.setattr(jobs, "cli_command", lambda _argv: command)
    tools = mcp_tools.NfclawTools(Path(__file__).resolve().parent.parent, cwd=str(tmp_path))
    tools.command_timeout = 2
    ctx = Context()
    outcome = []

    def invoke():
        outcome.append(tools.call_tool("list_versions", {"pipeline": "rnaseq"}, ctx))

    worker = threading.Thread(target=invoke)
    worker.start()
    identity = None
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                identity = json.loads(pidfile.read_text())
                if identity:
                    break
            except (OSError, ValueError):
                pass
            time.sleep(0.02)
        assert identity, outcome
        if stop in ("cancel", "disconnect"):
            ctx.cancelled.set()  # transport sets this on withdrawal and on EOF
        worker.join(10)
        assert not worker.is_alive()
        assert not process_identity.matches(identity)
        assert bool(outcome[0].get("isError")) == (stop != "success")
        if stop == "timeout":
            assert "did not finish" in outcome[0]["content"][0]["text"]
    finally:
        ctx.cancelled.set()
        worker.join(10)
        if identity:
            process_identity.send(identity, signal.SIGKILL)


def test_process_birth_identity_rejects_pid_only_and_reused_birth():
    identity = process_identity.read(os.getpid())
    assert identity and process_identity.matches(identity)
    assert not process_identity.matches({"pid": os.getpid()})
    assert not process_identity.matches({**identity, "start": "another birth"})


def test_killed_mcp_parent_stops_foreground_work(tmp_path):
    pidfile = tmp_path / "foreground-child.json"
    helper = ("import json, os, time; from pathlib import Path; "
              "from runner import process_identity; "
              f"Path({str(pidfile)!r}).write_text(json.dumps(process_identity.read(os.getpid()))); "
              "time.sleep(60)")
    root = Path(__file__).resolve().parent.parent
    parent = subprocess.Popen([sys.executable, "-c", (
        "import sys; from pathlib import Path; from runner import jobs, mcp_tools; "
        f"jobs.cli_command=lambda _: [sys.executable, '-c', {helper!r}]; "
        f"mcp_tools.NfclawTools(Path({str(root)!r}))._cli(['versions', 'rnaseq'])")],
        cwd=tmp_path, env=jobs.child_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    identity = None
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                identity = json.loads(pidfile.read_text())
                if identity:
                    break
            except (OSError, ValueError):
                pass
            time.sleep(0.02)
        assert identity
        parent.kill()
        parent.wait(timeout=5)
        deadline = time.monotonic() + 10
        while process_identity.matches(identity) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not process_identity.matches(identity)
    finally:
        if parent.poll() is None:
            parent.kill()
        parent.wait(timeout=5)
        if identity:
            process_identity.send(identity, signal.SIGKILL)


def test_foreground_refuses_to_spawn_without_an_inventory(tmp_path, monkeypatch, capsys):
    from runner import foreground

    def denied():
        raise PermissionError("process inspection denied")

    monkeypatch.setattr(process_identity, "parents", denied)
    marker = tmp_path / "must-not-run"
    assert foreground.run([sys.executable, "-c", f"open({str(marker)!r}, 'w').close()"]) == 125
    assert not marker.exists()
    assert "supervision unavailable" in capsys.readouterr().err
