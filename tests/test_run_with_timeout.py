"""scripts/run_with_timeout.py: the acceptance gate's portable stand-in for GNU `timeout`."""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_with_timeout.py"


def _run(*args, **kwargs):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          timeout=60, **kwargs)


def _gone(pid, within=5.0):
    deadline = time.monotonic() + within
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


def _wait_for(path, within=10.0):
    deadline = time.monotonic() + within
    while not path.exists() or not path.read_text().strip():
        assert time.monotonic() < deadline, f"{path} never appeared"
        time.sleep(0.05)
    return path.read_text().strip()


def test_the_command_status_and_arguments_pass_through():
    # Arguments that look like this script's own options belong to the command.
    process = _run("30", sys.executable, "-c", "import sys; print(sys.argv[1:]); sys.exit(7)",
                   "--kill-after", "-h")
    assert process.returncode == 7
    assert process.stdout.strip() == "['--kill-after', '-h']"


def test_the_deadline_stops_the_whole_process_group(tmp_path):
    child = tmp_path / "child.pid"
    started = time.monotonic()
    process = _run("--kill-after", "10", "1", "sh", "-c", f'sleep 30 & echo $! > {child}; wait')
    assert process.returncode == 124
    assert time.monotonic() - started < 8
    assert _gone(int(child.read_text())), "a process the command started outlived the deadline"


def test_a_command_ignoring_sigterm_is_killed_after_the_grace_period():
    started = time.monotonic()
    process = _run("--kill-after", "1", "1", "sh", "-c", 'trap "" TERM; sleep 30 & wait; wait')
    assert process.returncode == 128 + signal.SIGKILL
    assert time.monotonic() - started < 8


def test_without_a_grace_period_sigterm_is_the_only_signal():
    process = _run("1", "sh", "-c", 'trap "" TERM; sleep 2')
    assert process.returncode == 124


def test_a_command_ended_by_a_signal_reports_it_as_a_shell_does():
    process = _run("30", "sh", "-c", "kill -USR1 $$")
    assert process.returncode == 128 + signal.SIGUSR1


def test_a_zero_duration_disables_the_deadline():
    assert _run("0", "sh", "-c", "sleep 1.2; exit 3").returncode == 3


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM, signal.SIGHUP])
def test_a_signal_to_the_supervisor_reaches_the_command(tmp_path, signum):
    ready, got = tmp_path / "ready", tmp_path / "got"
    supervisor = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--kill-after", "10", "60", "sh", "-c",
         f'trap "echo caught > {got}; exit 3" {signum.name[3:]}; echo $$ > {ready}; '
         'while :; do sleep 0.1; done'])
    try:
        _wait_for(ready)
        supervisor.send_signal(signum)
        assert supervisor.wait(timeout=20) == 3
        assert got.read_text() == "caught\n"
    finally:
        if supervisor.poll() is None:
            supervisor.kill()
            supervisor.wait()


def test_a_forwarded_signal_also_starts_the_grace_period(tmp_path):
    ready = tmp_path / "ready"
    supervisor = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--kill-after", "1", "60", "sh", "-c",
         f'trap "" TERM; echo $$ > {ready}; while :; do sleep 0.1; done'])
    try:
        _wait_for(ready)
        started = time.monotonic()
        supervisor.send_signal(signal.SIGTERM)
        assert supervisor.wait(timeout=20) == 128 + signal.SIGKILL
        assert time.monotonic() - started < 8
    finally:
        if supervisor.poll() is None:
            supervisor.kill()
            supervisor.wait()


@pytest.mark.parametrize("args, code", [
    ((), 125), (("30",), 125), (("soon", "true"), 125), (("-1", "true"), 125),
    (("--kill-after", "nan", "30", "true"), 125),
    (("30", "/nonexistent/command"), 127), (("30", "{not executable}"), 126),
])
def test_failures_of_its_own_use_gnu_timeout_statuses(tmp_path, args, code):
    plain = tmp_path / "plain.txt"
    plain.write_text("not a program\n")
    process = _run(*(str(plain) if arg == "{not executable}" else arg for arg in args))
    assert process.returncode == code
    assert process.stderr
