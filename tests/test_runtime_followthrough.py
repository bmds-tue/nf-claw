"""Runtime audit regressions: child ownership, stream coverage and attributable evidence."""
import http.server
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from runner import environment_record, execution, orchestration, runlog


@pytest.mark.parametrize("phase", ["native_spawn", "spawn", "launched", "reader1", "reader2"])
def test_stop_during_child_registration_cleans_up_every_owned_process(tmp_path, monkeypatch, phase):
    """A stop in any setup operation must have the same teardown as a stop in wait()."""
    monkeypatch.setenv("NFCLAW_SHUTDOWN_GRACE", "1")
    created, readers = [], []
    original_popen, original_start = subprocess.Popen, threading.Thread.start
    original_execute = original_popen._execute_child
    pid_file = tmp_path / "child.ready"
    script = f"""import os, signal, subprocess, sys, time
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
def stop(signum, frame):
    child.wait(timeout=5)
    sys.exit(0)
signal.signal(signal.SIGTERM, stop)
open({str(pid_file)!r}, 'w').write(str(child.pid))
time.sleep(60)
"""

    def stop():
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if pid_file.exists() and pid_file.read_text().isdigit():
                break
            time.sleep(0.005)
        else:
            pytest.fail("child did not reach its readiness point")
        os.kill(os.getpid(), signal.SIGTERM)

    def popen(*args, **kwargs):
        child = original_popen(*args, **kwargs)
        if script not in args[0]:
            return child  # Host identity and cleanup probes are not the launched analysis.
        if child not in created:
            created.append(child)
        if phase == "spawn":
            stop()  # Before Popen's caller can assign the successfully spawned child.
        return child

    def execute(child, *args, **kwargs):
        original_execute(child, *args, **kwargs)
        if phase == "native_spawn" and script in args[0]:
            created.append(child)
            stop()  # The OS child exists but the native Popen constructor has not returned.

    def start(thread):
        readers.append(thread)
        if phase == f"reader{len(readers)}":
            stop()
        return original_start(thread)

    monkeypatch.setattr(execution.subprocess, "Popen", popen)
    monkeypatch.setattr(original_popen, "_execute_child", execute)
    monkeypatch.setattr(execution.threading.Thread, "start", start)
    if phase == "launched":
        monkeypatch.setattr(runlog.RunLog, "launched", lambda *args: stop())
    try:
        with execution.stop_on_signals(), pytest.raises(execution.Terminated):
            execution.run([sys.executable, "-c", script], cwd=tmp_path,
                          logs_dir=tmp_path / "logs", timeout_seconds=5)
        assert created and all(child.poll() is not None for child in created)
        with pytest.raises(ProcessLookupError):
            os.kill(int(pid_file.read_text()), 0)
        assert all(not thread.is_alive() for thread in readers)
        assert all(child.stdout.closed and child.stderr.closed for child in created)
        assert runlog.read_state(tmp_path / "logs/run.log").outcome == "terminated by SIGTERM"
    finally:
        if created and pid_file.exists() and pid_file.read_text().isdigit():
            try:
                # Keep a failing descendant assertion from orphaning the regression fixture.
                if os.getpgid(int(pid_file.read_text())) == created[0].pid:
                    os.killpg(created[0].pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for child in created:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()


@pytest.mark.parametrize("failed_reader", [1, 2])
@pytest.mark.parametrize("extra_probe", [False, True])
def test_partial_reader_startup_failure_stops_child_and_started_readers(
        tmp_path, monkeypatch, failed_reader, extra_probe):
    monkeypatch.setenv("NFCLAW_SHUTDOWN_GRACE", "0.1")
    created, readers = [], []
    original_popen, original_start = subprocess.Popen, threading.Thread.start
    original_discovery = execution._die_with_parent
    script = "import time; time.sleep(60) # partial-reader analysis"

    def popen(*args, **kwargs):
        child = original_popen(*args, **kwargs)
        if script in args[0]:
            created.append(child)
        return child

    def discovery():
        # Model libc discovery's unrelated subprocess, including its absent stderr pipe.
        subprocess.run([sys.executable, "-c", "pass"], stdout=subprocess.PIPE, check=True)
        return original_discovery()

    def start(thread):
        readers.append(thread)
        if len(readers) == failed_reader:
            raise RuntimeError("reader allocation failed")
        return original_start(thread)

    monkeypatch.setattr(execution.subprocess, "Popen", popen)
    monkeypatch.setattr(execution.threading.Thread, "start", start)
    if extra_probe:
        monkeypatch.setattr(execution, "_die_with_parent", discovery)
    try:
        with pytest.raises(RuntimeError, match="reader allocation failed"):
            execution.run([sys.executable, "-c", script], cwd=tmp_path,
                          logs_dir=tmp_path / "logs", timeout_seconds=5)
        assert created and all(child.poll() is not None for child in created)
        assert all(not thread.is_alive() for thread in readers)
        assert all(child.stdout.closed and child.stderr.closed for child in created)
    finally:
        for child in created:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()


@pytest.mark.parametrize("streams", [("out",), ("err",), ("out", "err")])
def test_completion_caveats_cover_both_streams_without_duplicates(library, tmp_path,
                                                                 monkeypatch, streams):
    root = library("mini")
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **kw: [])
    monkeypatch.setattr(orchestration.container_watch, "engine_for", lambda profile: None)
    monkeypatch.setattr(environment_record, "capture", lambda *a, **k: {"issues": []})
    summary = (b"-[nf-core/mini] Pipeline completed successfully, but with skipped sampl(es) -\n"
               b"-[nf-core/mini] SAMPLE_A failed QC -\n")

    def completed(*args, **kwargs):
        for stream in streams:
            kwargs["run_log"].write(summary, stream)

    monkeypatch.setattr(execution, "run", completed)
    warnings = []
    result = orchestration.run_pipeline(
        "mini", repo_root=root, input_path=None, outdir=tmp_path / "out", profile="standard",
        params_file=None, cli_overrides={}, resume=False, demo=True, check_only=False,
        write_provenance=True, timeout_seconds=10, on_warning=warnings.append)
    expected = ["[nf-core/mini] Pipeline completed successfully, but with skipped sampl(es)",
                "[nf-core/mini] SAMPLE_A failed QC"]
    manifest = json.loads((tmp_path / "out/provenance/run_manifest.json").read_text())
    assert manifest.get("completion_caveats") == expected
    assert [w for w in result.warnings if w.startswith("the pipeline completed")] == [
        "the pipeline completed but reported: " + item for item in expected]
    assert [w for w in warnings if w.startswith("the pipeline completed")] == [
        "the pipeline completed but reported: " + item for item in expected]


SESSION = "11111111-1111-1111-1111-111111111111"
OTHER_SESSION = "22222222-2222-2222-2222-222222222222"


def _log(session, plugin="old@1.0.0"):
    return (f"x DEBUG nextflow.Session - Session UUID: {session}\n"
            "  Version: 25.10.4 build 123\n  Runtime: old runtime\n"
            f"x DEBUG Plugin started {plugin}\n"
            "x Validation of file 'https://example.org/old.csv' passed\n"
            "x Copying foreign file https://example.org/read.fq to work dir: /old/read.fq\n")


@pytest.mark.parametrize("damage", ["missing", "foreign", "mixed", "unreadable"])
@pytest.mark.parametrize("rotation_session", [SESSION, OTHER_SESSION])
def test_current_environment_observations_cannot_come_from_rotations_or_foreign_sessions(
        tmp_path, monkeypatch, damage, rotation_session):
    log = tmp_path / ".nextflow.log"
    rotation = tmp_path / ".nextflow.log.1"
    rotation.write_text(_log(rotation_session))
    if damage != "missing":
        log.write_text(_log(OTHER_SESSION if damage == "foreign" else SESSION))
        if damage == "mixed":
            log.write_text(_log(SESSION) + _log(OTHER_SESSION))
    if damage == "unreadable":
        original_open = type(log).open

        def denied(path, *args, **kwargs):
            if path == log:
                raise PermissionError("current log unavailable")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(type(log), "open", denied)
    facts = environment_record.log_facts(log, SESSION)
    assert facts["build"] is None
    assert facts["runtime"] is None
    assert facts["plugins"] is None  # Unknown, distinct from an observed empty inventory.
    assert facts["validated"] == []
    assert facts["issues"]
    assert facts["staged"] == ({"https://example.org/read.fq": "/old/read.fq"}
                                if rotation_session == SESSION else {})


def test_valid_current_log_preserves_observed_empty_plugin_inventory(tmp_path):
    log = tmp_path / ".nextflow.log"
    log.write_text(f"x DEBUG nextflow.Session - Session UUID: {SESSION}\n")
    facts = environment_record.log_facts(log, SESSION)
    assert facts["plugins"] == []
    assert facts["issues"] == []


def test_missing_current_log_records_an_unknown_plugin_inventory_without_malformed_evidence(
        tmp_path, monkeypatch):
    history = tmp_path / ".nextflow/history"
    history.parent.mkdir()
    history.write_text(f"today\t1s\trun_name\tOK\targ\t{SESSION}\n")
    monkeypatch.setattr(environment_record, "tasks", lambda *a, **kw: [])
    record = environment_record.capture(tmp_path, log_path=tmp_path / ".nextflow.log")
    assert "nextflow_plugins" not in record
    assert any("current Nextflow log" in gap for gap in record["issues"])
    assert environment_record.comparison_issues(record) == []
    assert environment_record.compare(record, record)["status"] == "unverified"


@pytest.fixture
def trickle_server():
    disconnected = threading.Event()
    connected = threading.Event()

    class Trickle(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path.startswith("/fast"):
                content = b"staged remote bytes"
                self.send_response(200)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                connected.set()
                self.wfile.write(content)
                return
            self.send_response(200)
            self.send_header("Content-Length", "100")
            self.end_headers()
            connected.set()
            try:
                for _ in range(100):
                    self.wfile.write(b"x")
                    self.wfile.flush()
                    time.sleep(0.02)
            except (BrokenPipeError, ConnectionResetError):
                disconnected.set()

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Trickle)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, connected, disconnected
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("budgeted", [True, False])
def test_slow_progress_download_obeys_absolute_deadline_and_closes_worker_socket(
        monkeypatch, budgeted, trickle_server):
    server, _, disconnected = trickle_server
    created = []
    original_popen = subprocess.Popen

    def popen(*args, **kwargs):
        child = original_popen(*args, **kwargs)
        created.append(child)
        return child

    monkeypatch.setattr(environment_record.subprocess, "Popen", popen)
    try:
        start = time.monotonic()
        monkeypatch.setattr(environment_record, "_deadline", start + 0.8 if budgeted else None)
        monkeypatch.setattr(environment_record, "FETCH_TIMEOUT", 0.8, raising=False)
        result = environment_record.fetch_digest(f"http://127.0.0.1:{server.server_port}/sheet")
        elapsed = time.monotonic() - start
        assert "unresolved" in result
        assert elapsed < 1.8, f"download exceeded its absolute budget: {elapsed}"
        assert disconnected.wait(1), "the cancelled download left its HTTP connection open"
        assert all(child.poll() is not None for child in created)
    finally:
        for child in created:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()


@pytest.mark.parametrize("phase", ["spawn", "download"])
def test_interrupted_refetch_reaps_worker_and_closes_connection(monkeypatch, trickle_server, phase):
    server, connected, disconnected = trickle_server
    created = []
    original_popen = subprocess.Popen

    def stop():
        assert connected.wait(5), "refetch never connected"
        os.kill(os.getpid(), signal.SIGTERM)

    def popen(*args, **kwargs):
        child = original_popen(*args, **kwargs)
        created.append(child)
        if phase == "spawn":
            os.kill(os.getpid(), signal.SIGTERM)
        return child

    monkeypatch.setattr(environment_record.subprocess, "Popen", popen)
    thread = threading.Thread(target=stop, daemon=True) if phase == "download" else None
    try:
        with execution.stop_on_signals(), pytest.raises(execution.Terminated):
            if thread is not None:
                thread.start()
            environment_record.fetch_digest(f"http://127.0.0.1:{server.server_port}/sheet")
        assert created and all(child.poll() is not None for child in created)
        if phase == "spawn":
            assert not connected.is_set()  # The private URL has not been sent over stdin yet.
        else:
            assert disconnected.wait(1), "interrupted refetch retained its connection"
        assert all(child.stdout.closed and child.stderr.closed for child in created)
    finally:
        for child in created:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        if thread is not None:
            thread.join(timeout=5)


def test_refetch_signed_url_stays_out_of_helper_argv(monkeypatch, trickle_server, capsys):
    server, _, _ = trickle_server
    url = f"http://127.0.0.1:{server.server_port}/fast?signature=synthetic-private-marker"
    commands = []
    original_popen = subprocess.Popen

    def popen(command, **kwargs):
        commands.append(command)
        return original_popen(command, **kwargs)

    monkeypatch.setattr(environment_record.subprocess, "Popen", popen)
    result = environment_record.fetch_digest(url)
    assert result["sha256"] == hashlib.sha256(b"staged remote bytes").hexdigest()
    assert commands and all("synthetic-private-marker" not in word
                            for command in commands for word in command)
    captured = capsys.readouterr()
    assert "synthetic-private-marker" not in captured.out + captured.err + json.dumps(result)


def test_copied_recorder_refetches_without_installed_nfclaw(tmp_path, trickle_server):
    server, _, _ = trickle_server
    copied = tmp_path / "environment_record.py"
    copied.write_bytes(Path(environment_record.__file__).read_bytes())
    bootstrap = ("import json,runpy,sys; ns=runpy.run_path(sys.argv[1]); "
                 "print(json.dumps(ns['fetch_digest'](sys.stdin.read())))")
    result = subprocess.run([sys.executable, "-I", "-S", "-c", bootstrap, str(copied)],
                            cwd=tmp_path, input=f"http://127.0.0.1:{server.server_port}/fast",
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["sha256"] == hashlib.sha256(b"staged remote bytes").hexdigest()
