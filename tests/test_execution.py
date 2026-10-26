import _thread
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import types
from pathlib import Path

import pytest

from runner import execution
from runner.errors import NfclawError
from runner.runlog import read_state

PY = sys.executable


def test_success_writes_logs(tmp_path):
    res = execution.run([PY, "-c", "print('hi')"], cwd=tmp_path,
                        logs_dir=tmp_path / "logs", timeout_seconds=30)
    assert res.exit_code == 0
    assert (tmp_path / "logs" / "stdout.txt").read_text().strip() == "hi"


def test_nonzero_raises(tmp_path):
    with pytest.raises(NfclawError):
        execution.run([PY, "-c", "import sys; sys.exit(3)"], cwd=tmp_path,
                      logs_dir=tmp_path / "logs", timeout_seconds=30)


def test_timeout_raises(tmp_path):
    with pytest.raises(NfclawError):
        execution.run([PY, "-c", "import time; time.sleep(5)"], cwd=tmp_path,
                      logs_dir=tmp_path / "logs", timeout_seconds=1)


def test_env_extra_is_applied_to_subprocess(tmp_path):
    execution.run([PY, "-c", "import os; print(os.environ.get('NXF_VER', 'MISSING'))"],
                  cwd=tmp_path, logs_dir=tmp_path / "logs", timeout_seconds=30,
                  env_extra={"NXF_VER": "25.10.2"})
    assert (tmp_path / "logs" / "stdout.txt").read_text().strip() == "25.10.2"


def test_env_extra_preserves_inherited_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("INHERITED_MARKER", "yes")
    execution.run([PY, "-c", "import os; print(os.environ.get('INHERITED_MARKER', 'MISSING'))"],
                  cwd=tmp_path, logs_dir=tmp_path / "logs", timeout_seconds=30,
                  env_extra={"NXF_VER": "1"})
    assert (tmp_path / "logs" / "stdout.txt").read_text().strip() == "yes"


def test_failure_quotes_nextflow_error_and_points_at_the_real_logs(tmp_path):
    # Nextflow prints its error report on *stdout*; stderr only carries launcher chatter (the
    # "Nextflow X is available" notice). Pointing at stderr.txt sent every reader to an empty file.
    nf_log = tmp_path / ".nextflow.log"
    nf_log.write_text("engine detail")
    child = ("import sys; print('Nextflow 99 is available', file=sys.stderr); "
             "print('ERROR ~ Error executing process > BOOM'); "
             "print(); print('Caused by:'); print('  the real cause'); sys.exit(1)")
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", child], cwd=tmp_path, logs_dir=tmp_path / "logs",
                      timeout_seconds=30, nextflow_log=nf_log)
    text = str(exc.value)
    assert "ERROR ~ Error executing process > BOOM" in text and "the real cause" in text
    assert exc.value.details["run_log"] == str(tmp_path / "logs" / "run.log")
    assert exc.value.details["nextflow_log"] == str(nf_log)
    assert exc.value.details["exit_code"] == 1
    assert "known-issues.md" in exc.value.fix
    assert "stderr.txt" not in text


def test_failure_explains_a_task_that_ran_past_its_time_limit(tmp_path):
    # Before Nextflow 26.10.0 a local task killed at its time limit aborts the session with an
    # IllegalThreadStateException, quoted as "process hasn't exited" (nextflow-io/nextflow#7569).
    child = ("import sys; print(\"ERROR ~ Error executing process > 'CLIPKIT (x)'\"); print(); "
             "print('Caused by:'); print(\"  process hasn't exited\"); sys.exit(1)")
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", child], cwd=tmp_path, logs_dir=tmp_path / "logs",
                      timeout_seconds=30)
    assert "time limit" in exc.value.fix and "nextflow-io/nextflow#7569" in exc.value.fix
    assert "--resume" in exc.value.fix and "26.10.0" in exc.value.fix


def test_failure_without_that_message_gives_no_time_limit_hint(tmp_path):
    child = "import sys; print('ERROR ~ Error executing process > BOOM'); sys.exit(1)"
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", child], cwd=tmp_path, logs_dir=tmp_path / "logs",
                      timeout_seconds=30)
    assert "time limit" not in exc.value.fix
    assert "--nxf-ver" not in exc.value.fix


def test_failure_names_the_engine_a_release_requires_when_nextflow_refuses_an_older_one(tmp_path):
    # Nextflow enforces `manifest.nextflowVersion` itself (nf-core's strict `!>=` form); nfclaw
    # does not pre-check it, so the refusal is where the engine to pin is named. Console text as
    # Nextflow 25.10.2 prints it for nf-core/demo 1.2.0.
    child = ("import sys; print(' N E X T F L O W   ~  version 25.10.2'); "
             "print('Nextflow 26.10.3 is available - Please consider updating your version to it', "
             "file=sys.stderr); print('Nextflow version 25.10.2 does not match workflow required "
             "version: >=25.10.4', file=sys.stderr); sys.exit(1)")
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", child], cwd=tmp_path, logs_dir=tmp_path / "logs",
                      timeout_seconds=30)
    assert "does not match workflow required version: >=25.10.4" in str(exc.value)
    assert "--nxf-ver 25.10.4" in exc.value.fix and "nxf_ver" in exc.value.fix


def test_failure_quotes_the_underlying_cause_from_the_nextflow_log(tmp_path):
    # The console said only "Unable to parse config file"; the cause is in Nextflow's log alone.
    nf_log = tmp_path / ".nextflow.log"
    shutil.copy(Path(__file__).parent / "fixtures" / "nextflow_console" /
                "nextflow_log_config_unreachable.log", nf_log)
    child = "import sys; print('ERROR ~ Unable to parse config file'); sys.exit(1)"
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", child], cwd=tmp_path, logs_dir=tmp_path / "logs",
                      timeout_seconds=30, nextflow_log=nf_log)
    text = str(exc.value)
    assert "Caused by: java.net.SocketException: Network is unreachable" in text
    assert "nfcore_custom.config" in text


_JVM_OPTION_VARS = ("NXF_JVM_ARGS", "NXF_OPTS", "JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS")


@pytest.mark.parametrize("env_extra, hinted", [
    (None, True),
    ({"NXF_JVM_ARGS": "-Djava.net.preferIPv6Addresses=true"}, False),
    ({"NXF_OPTS": "-Xms1g -Djava.net.preferIPv6Addresses=true"}, False),
])
def test_an_unreachable_network_in_nextflows_own_log_gets_the_ipv6_fix(tmp_path, monkeypatch,
                                                                       env_extra, hinted):
    # Nextflow's JVM tries IPv4 first: on a host without an IPv4 route (IPv6-only, NAT64) its own
    # download of nf-core/configs fails, and only its log says why. Agents driving nfclaw through
    # MCP spent several attempts finding the flag; once the JVM already prefers IPv6 the hint
    # would point at the wrong cause.
    for name in _JVM_OPTION_VARS:
        monkeypatch.delenv(name, raising=False)
    nf_log = tmp_path / ".nextflow.log"
    shutil.copy(Path(__file__).parent / "fixtures" / "nextflow_console" /
                "nextflow_log_config_unreachable.log", nf_log)
    child = "import sys; print('ERROR ~ Unable to parse config file'); sys.exit(1)"
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", child], cwd=tmp_path, logs_dir=tmp_path / "logs",
                      timeout_seconds=30, nextflow_log=nf_log, env_extra=env_extra)
    fix = exc.value.fix
    assert ("--nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true" in fix) is hinted
    assert "known-issues.md" in fix


def test_an_unreachable_network_reported_only_by_a_task_gets_no_ipv6_hint(tmp_path, monkeypatch):
    # A task's own JVM (inside its container) is not Nextflow's: NXF_JVM_ARGS cannot fix it.
    for name in _JVM_OPTION_VARS:
        monkeypatch.delenv(name, raising=False)
    child = ("import sys; print(\"ERROR ~ Error executing process > 'BBMAP_SENDSKETCH (x)'\"); "
             "print(); print('Caused by:'); "
             "print('  java.net.ConnectException: Network is unreachable'); sys.exit(1)")
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", child], cwd=tmp_path, logs_dir=tmp_path / "logs",
                      timeout_seconds=30)
    assert "preferIPv6Addresses" not in exc.value.fix


def test_failure_quotes_what_nextflow_wrote_on_stderr(tmp_path):
    # nf-schema writes *which* parameter is invalid to stderr; stdout only says that
    # validation failed.
    child = ("import sys; print('Nextflow 99 is available - Please consider updating your version "
             "to it', file=sys.stderr); print('ERROR ~ Validation of pipeline parameters "
             "failed!'); print(' -- Check .nextflow.log file for details'); sys.stdout.flush(); "
             "print('* --publish_dir_mode (bogus): Expected any of [copy, link]', "
             "file=sys.stderr); sys.exit(1)")
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", child], cwd=tmp_path, logs_dir=tmp_path / "logs",
                      timeout_seconds=30)
    text = str(exc.value)
    assert "ERROR ~ Validation of pipeline parameters failed!" in text
    assert "* --publish_dir_mode (bogus): Expected any of [copy, link]" in text
    assert "is available" not in text


def test_failure_without_a_report_quotes_stderr_rather_than_the_stdout_banner(tmp_path):
    child = ("import sys; print('BANNER LINE'); print('params summary'); "
             "print('java.lang.OutOfMemoryError: Java heap space', file=sys.stderr); sys.exit(1)")
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", child], cwd=tmp_path, logs_dir=tmp_path / "logs",
                      timeout_seconds=30)
    text = str(exc.value)
    assert "java.lang.OutOfMemoryError: Java heap space" in text
    assert "BANNER LINE" not in text


def test_failure_without_any_report_quotes_the_stdout_tail(tmp_path):
    # `error "..."` in a workflow body prints only its message, on stdout.
    child = ("import sys; print('pipeline-level failure: missing --fasta'); "
             "print('Nextflow 99 is available - Please consider updating your version to it', "
             "file=sys.stderr); sys.exit(1)")
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", child], cwd=tmp_path, logs_dir=tmp_path / "logs",
                      timeout_seconds=30)
    assert "pipeline-level failure: missing --fasta" in str(exc.value)


def test_failure_does_not_point_at_a_nextflow_log_that_was_never_written(tmp_path):
    # Nextflow can fail before it creates its log (e.g. the launcher cannot fetch NXF_VER).
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", "import sys; sys.exit(1)"], cwd=tmp_path,
                      logs_dir=tmp_path / "logs", timeout_seconds=30,
                      nextflow_log=tmp_path / ".nextflow.log")
    assert "nextflow_log" not in exc.value.details
    assert exc.value.details["run_log"] == str(tmp_path / "logs" / "run.log")


def test_failure_points_at_the_failing_task_files(tmp_path):
    task = tmp_path / "work" / "ca" / "546a82"
    task.mkdir(parents=True)
    (task / ".command.err").write_text("samtools: could not open input.bam")
    child = (f"import sys; print('ERROR ~ Error executing process > BOOM'); print('Work dir:'); "
             f"print('  {task}'); sys.exit(1)")
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", child], cwd=tmp_path, logs_dir=tmp_path / "logs",
                      timeout_seconds=30)
    assert exc.value.details["failing_task"] == str(task / ".command.err")


def test_run_log_records_the_whole_launch_in_order(tmp_path):
    # One file holds everything a launch printed — nfclaw's header, Nextflow's stdout and stderr
    # interleaved as produced — and ends with the outcome, so a background run needs no redirect.
    child = ("import sys, time; print('OUT1', flush=True); time.sleep(0.2); "
             "print('ERR1', file=sys.stderr, flush=True); time.sleep(0.2); print('OUT2')")
    execution.run([PY, "-c", child], cwd=tmp_path, logs_dir=tmp_path / "logs",
                  timeout_seconds=30, notes=["engine older than required"])
    log = (tmp_path / "logs" / "run.log").read_text()
    assert log.index("==> nfclaw run started") < log.index("OUT1") < log.index("ERR1") \
        < log.index("OUT2")
    assert "warning: engine older than required" in log
    assert f"launch dir: {tmp_path}" in log
    assert log.rstrip().splitlines()[-1].startswith("==> nfclaw run finished")
    assert log.rstrip().endswith(": success")


def test_failed_run_log_ends_with_the_outcome_after_the_error(tmp_path):
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", "import sys; print('ERROR ~ boom'); sys.exit(4)"], cwd=tmp_path,
                      logs_dir=tmp_path / "logs", timeout_seconds=30)
    log = (tmp_path / "logs" / "run.log").read_text()
    # Quoting protects controls in the log; status reconstructs the exact terminal error.
    assert "\n".join(read_state(tmp_path / "logs" / "run.log").error) == str(exc.value)
    assert log.rstrip().splitlines()[-1].endswith(": failed (exit status 4)")


def test_timed_out_run_is_logged(tmp_path):
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", "import time; print('started', flush=True); time.sleep(10)"],
                      cwd=tmp_path, logs_dir=tmp_path / "logs", timeout_seconds=1)
    assert exc.value.details["run_log"] == str(tmp_path / "logs" / "run.log")
    log = (tmp_path / "logs" / "run.log").read_text()
    assert "started" in log
    assert log.rstrip().splitlines()[-1].endswith(": timed out after 1 s")


def test_a_relaunch_appends_to_the_logs_instead_of_overwriting_them(tmp_path):
    # `--resume` relaunches into the same --outdir; the failed attempt's log is the evidence of what
    # went wrong and must survive the retry.
    with pytest.raises(NfclawError):
        execution.run([PY, "-c", "import sys; print('ATTEMPT1'); sys.exit(1)"], cwd=tmp_path,
                      logs_dir=tmp_path / "logs", timeout_seconds=30)
    execution.run([PY, "-c", "print('ATTEMPT2')"], cwd=tmp_path, logs_dir=tmp_path / "logs",
                  timeout_seconds=30)
    log = (tmp_path / "logs" / "run.log").read_text()
    assert log.count("==> nfclaw run started") == 2
    assert log.index("ATTEMPT1") < log.index("ATTEMPT2")
    out = (tmp_path / "logs" / "stdout.txt").read_text()
    assert "ATTEMPT1" in out and "ATTEMPT2" in out


def test_launch_announces_where_the_run_is_logged(tmp_path, capfd):
    execution.run([PY, "-c", "print('x')"], cwd=tmp_path, logs_dir=tmp_path / "logs",
                  timeout_seconds=30)
    assert f"nfclaw: logging this run to {tmp_path / 'logs' / 'run.log'}" in capfd.readouterr().err


def test_launch_failure_is_logged(tmp_path):
    with pytest.raises(NfclawError) as exc:
        execution.run([str(tmp_path / "no-such-binary")], cwd=tmp_path,
                      logs_dir=tmp_path / "logs", timeout_seconds=30)
    assert exc.value.details["run_log"] == str(tmp_path / "logs" / "run.log")
    log = (tmp_path / "logs" / "run.log").read_text()
    assert log.rstrip().splitlines()[-1].endswith(": could not launch")


def test_output_is_streamed_live_to_the_terminal_and_the_logs(tmp_path, capfd):
    # The wrapper must not stay mute during a run: the child's stdout/stderr are teed to the
    # terminal as they are produced *and* still captured to the log files (which the provenance
    # bundle and error messages reference). capfd captures at the file-descriptor level, which is
    # where the tee writes (sys.stdout/err .buffer).
    execution.run([PY, "-c", "import sys; print('LIVE_OUT'); print('LIVE_ERR', file=sys.stderr)"],
                  cwd=tmp_path, logs_dir=tmp_path / "logs", timeout_seconds=30)
    captured = capfd.readouterr()
    assert "LIVE_OUT" in captured.out and "LIVE_ERR" in captured.err   # reached the terminal
    assert (tmp_path / "logs" / "stdout.txt").read_text().strip() == "LIVE_OUT"   # and the logs
    assert (tmp_path / "logs" / "stderr.txt").read_text().strip() == "LIVE_ERR"


@pytest.mark.skipif(not hasattr(os, "killpg"), reason="needs POSIX process groups")
def test_keyboard_interrupt_tears_down_the_child_and_its_children(tmp_path):
    # Ctrl-C during a run must not leave Nextflow (or the task processes it launched) running in the
    # background. Reproduce the interrupt with interrupt_main() while run() is blocked in wait(),
    # and confirm both the child and a grandchild it spawned are gone afterwards.
    pids = tmp_path / "pids.txt"
    script = (
        "import os, sys, subprocess, time;"
        "g = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']);"
        f"open(r'{pids}', 'w').write(f'{{os.getpid()}} {{g.pid}}');"
        "sys.stdout.flush();"
        "time.sleep(60)"
    )

    # interrupt_main() does nothing when SIGINT is ignored — as it is for a job a shell started in
    # the background (`nohup … &`) — so give this test the handler an interactive Ctrl-C
    # would reach.
    previous = signal.signal(signal.SIGINT, signal.default_int_handler)
    timer = threading.Timer(1.5, _thread.interrupt_main)
    timer.start()
    try:
        with pytest.raises(KeyboardInterrupt):
            execution.run([PY, "-c", script], cwd=tmp_path,
                          logs_dir=tmp_path / "logs", timeout_seconds=60)
    finally:
        timer.cancel()
        signal.signal(signal.SIGINT, previous)
    log = (tmp_path / "logs" / "run.log").read_text()
    assert log.rstrip().splitlines()[-1].endswith(": interrupted")   # the log says how it ended
    assert _gone(int(x) for x in pids.read_text().split()), "a process survived the interrupt"


def _gone(pids, within=5.0):
    """Whether every pid exits within `within` seconds (waiting out the teardown)."""
    deadline = time.time() + within
    for pid in pids:
        while time.time() < deadline:
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except ProcessLookupError:
                break
        else:
            return False
    return True


@pytest.mark.skipif(not hasattr(os, "killpg"), reason="needs POSIX process groups")
def test_sigterm_stops_the_run_cleanly_and_is_logged(tmp_path):
    # `kill <pid>` is how a run started in the background is stopped. It used to kill nfclaw on the
    # spot: Nextflow went on running orphaned and run.log never got its outcome line, so polling
    # `tail -n 1 run.log` waited forever.
    pids = tmp_path / "pids.txt"
    script = (
        "import os, sys, subprocess, time;"
        "g = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']);"
        f"open(r'{pids}', 'w').write(f'{{os.getpid()}} {{g.pid}}');"
        "sys.stdout.flush();"
        "time.sleep(60)"
    )
    timer = threading.Timer(1.5, os.kill, args=(os.getpid(), signal.SIGTERM))
    timer.start()
    try:
        with execution.stop_on_signals():
            with pytest.raises(execution.Terminated) as exc:
                execution.run([PY, "-c", script], cwd=tmp_path,
                              logs_dir=tmp_path / "logs", timeout_seconds=60)
    finally:
        timer.cancel()
    assert exc.value.signum == signal.SIGTERM
    log = (tmp_path / "logs" / "run.log").read_text()
    assert log.rstrip().splitlines()[-1].endswith(": terminated by SIGTERM")
    assert _gone(int(x) for x in pids.read_text().split()), "Nextflow outlived nfclaw"


def test_stop_on_signals_restores_the_previous_handlers():
    before = signal.getsignal(signal.SIGTERM)
    with execution.stop_on_signals():
        assert signal.getsignal(signal.SIGTERM) is not before
    assert signal.getsignal(signal.SIGTERM) is before


@pytest.mark.skipif(not hasattr(signal, "SIGHUP"), reason="needs SIGHUP")
def test_a_signal_the_caller_ignores_stays_ignored():
    # `nohup` ignores SIGHUP so a run survives its terminal closing; nfclaw must not undo that.
    previous = signal.signal(signal.SIGHUP, signal.SIG_IGN)
    try:
        with execution.stop_on_signals():
            assert signal.getsignal(signal.SIGHUP) is signal.SIG_IGN
    finally:
        signal.signal(signal.SIGHUP, previous)


def test_no_timeout_waits_for_the_run_to_finish(tmp_path):
    # `nfclaw run` sets no wall-clock limit by default; None must mean "wait", not "time out".
    res = execution.run([PY, "-c", "import time; time.sleep(0.2); print('done')"], cwd=tmp_path,
                        logs_dir=tmp_path / "logs", timeout_seconds=None)
    assert res.exit_code == 0
    assert (tmp_path / "logs" / "stdout.txt").read_text().strip() == "done"


def test_teardown_kills_a_task_that_outlives_sigterm(tmp_path):
    # Nextflow exiting on SIGTERM does not mean its tasks did: one that ignores (or is still
    # handling) SIGTERM was left running in the background once the leader had exited.
    if sys.platform != "linux":
        pytest.skip("reads process state from /proc")
    pid_file = tmp_path / "task.pid"
    leader = tmp_path / "leader.sh"
    leader.write_text(
        "#!/bin/bash\n"
        f"bash -c 'trap \"\" TERM; echo $$ > {pid_file}; exec sleep 300' "
        ">/dev/null 2>&1 </dev/null &\n"
        "sleep 300\n")
    leader.chmod(0o755)
    proc = subprocess.Popen([str(leader)], start_new_session=True)
    deadline = time.monotonic() + 10
    while not pid_file.exists() or not pid_file.read_text().strip():
        assert time.monotonic() < deadline
        time.sleep(0.05)
    task = int(pid_file.read_text())

    def state():
        try:
            return Path(f"/proc/{task}/stat").read_text().split()[2]
        except FileNotFoundError:
            return "gone"

    try:
        execution._terminate(proc, grace=1)
        time.sleep(0.2)
        assert state() in ("gone", "Z", "X"), state()      # dead (a zombie until init reaps it)
    finally:
        if state() not in ("gone", "Z", "X"):
            os.kill(task, 9)


def test_a_second_interrupt_during_teardown_still_kills_the_group(monkeypatch):
    # A second Ctrl-C while waiting out the grace period aborted the teardown before SIGKILL.
    sent = []
    monkeypatch.setattr(execution.os, "killpg", lambda pgid, sig: sent.append(sig))

    def interrupted_wait(timeout=None):
        if timeout is not None:
            raise KeyboardInterrupt
        return 0

    proc = types.SimpleNamespace(pid=4242, wait=interrupted_wait)
    with pytest.raises(KeyboardInterrupt):
        execution._terminate(proc, grace=5)
    assert sent == [signal.SIGTERM, signal.SIGKILL]


def test_run_log_header_command_carries_the_nxf_overlay(tmp_path):
    # `--nxf-ver`/`--nxf-env` are part of how the command runs: the header's command line must say
    # so, or a copy of it runs a different Nextflow engine than the run did.
    execution.run([PY, "-c", "print('x')"], cwd=tmp_path, logs_dir=tmp_path / "logs",
                  timeout_seconds=30, env_extra={"NXF_VER": "25.10.4"})
    log = (tmp_path / "logs" / "run.log").read_text()
    assert f"    command: NXF_VER=25.10.4 {PY}" in log


def test_run_log_header_records_who_runs_it(tmp_path):
    # pid + host let `nfclaw status` tell a live run from one whose nfclaw was killed outright.
    execution.run([PY, "-c", "import os; print('CHILD', os.getpid())"], cwd=tmp_path,
                  logs_dir=tmp_path / "logs", timeout_seconds=30)
    log = (tmp_path / "logs" / "run.log").read_text()
    child = int((tmp_path / "logs" / "stdout.txt").read_text().split("CHILD ")[1].split()[0])
    assert f"    pid: {os.getpid()}\n" in log
    assert f"    host: {socket.gethostname()}\n" in log
    assert f"    nextflow pid: {child}\n" in log
    assert log.index("    nextflow pid:") < log.index("\n| CHILD ")   # before any console output


def test_recorded_error_is_marked_in_the_run_log(tmp_path):
    with pytest.raises(NfclawError) as exc:
        execution.run([PY, "-c", "import sys; print('ERROR ~ boom'); sys.exit(2)"], cwd=tmp_path,
                      logs_dir=tmp_path / "logs", timeout_seconds=30)
    log = (tmp_path / "logs" / "run.log").read_text()
    assert "==> nfclaw error:\n| " in log
    assert "\n".join(read_state(tmp_path / "logs" / "run.log").error) == str(exc.value)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="PR_SET_PDEATHSIG is Linux-only")
def test_nextflow_does_not_outlive_an_nfclaw_killed_with_sigkill(tmp_path):
    # SIGKILL (kill -9, the OOM killer) cannot be caught, so nfclaw cannot stop Nextflow itself: on
    # Linux the kernel does it — Nextflow is told to exit when the nfclaw that launched it dies.
    pidfile = tmp_path / "child.pid"
    launcher = (
        "import sys; from pathlib import Path; from runner import execution;"
        "execution.run([sys.executable, '-c', "
        f"\"import os, time; open(r'{pidfile}', 'w').write(str(os.getpid())); time.sleep(60)\"], "
        f"cwd=Path(r'{tmp_path}'), logs_dir=Path(r'{tmp_path}') / 'logs', timeout_seconds=None)"
    )
    nfclaw = subprocess.Popen([PY, "-c", launcher], cwd=Path(__file__).parent.parent,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 15
    while not pidfile.exists() and time.time() < deadline:
        time.sleep(0.1)
    child = int(pidfile.read_text())
    nfclaw.send_signal(signal.SIGKILL)
    nfclaw.wait()
    gone = False
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            os.kill(child, 0)
            time.sleep(0.1)
        except ProcessLookupError:
            gone = True
            break
    if not gone:
        os.kill(child, signal.SIGKILL)
    assert gone, "Nextflow outlived an nfclaw killed with SIGKILL"
