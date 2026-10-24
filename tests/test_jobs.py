"""Detached jobs (runner.jobs): started, supervised, stopped and read back from disk alone.

The commands here are stand-ins for the nfclaw CLI (a few lines of Python), so the job machinery is
tested on its own: what it records, when it reports a job as running, and how a stop reaches the
command. Each test keeps its state in its own directory through NFCLAW_STATE_DIR.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from runner import jobs

pytestmark = pytest.mark.skipif(jobs.fcntl is None, reason="detached jobs need POSIX")


@pytest.fixture(autouse=True)
def _state(tmp_path, monkeypatch):
    monkeypatch.setenv("NFCLAW_STATE_DIR", str(tmp_path / "state"))


def _until(predicate, timeout=30.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def _py(code: str) -> list[str]:
    return [sys.executable, "-c", textwrap.dedent(code)]


def _launch(tmp_path, command, *, label="demo"):
    d = jobs.create_dir(label)
    return jobs.launch(d, kind="run", argv=["run", label], cwd=str(tmp_path),
                       outdir=str(tmp_path / "out"), pipeline=label, command=command)


def _finished(job_id):
    return _until(lambda: not jobs.alive(jobs.load(job_id)))


def test_a_job_that_exits_zero_is_succeeded_with_its_output_kept(tmp_path):
    job = _launch(tmp_path, _py("print('hello from the run')"))
    assert _finished(job.id)
    job = jobs.load(job.id)
    assert jobs.state(job) == "succeeded"
    assert job.exit_code == 0 and job.finished_at
    assert "hello from the run" in jobs.output_tail(job, 10)


def test_a_job_that_exits_nonzero_is_failed_with_its_exit_code(tmp_path):
    job = _launch(tmp_path, _py("import sys; print('boom', file=sys.stderr); sys.exit(3)"))
    assert _finished(job.id)
    job = jobs.load(job.id)
    assert jobs.state(job) == "failed" and job.exit_code == 3
    assert "boom" in jobs.output_tail(job, 5)


def test_a_job_runs_in_the_directory_it_was_given(tmp_path):
    job = _launch(tmp_path, _py("import os; print(os.getcwd())"))
    assert _finished(job.id)
    assert os.path.realpath(jobs.output_tail(jobs.load(job.id), 1)[0]) == \
        os.path.realpath(tmp_path)


def test_a_running_job_is_running_and_its_record_names_both_processes(tmp_path):
    job = _launch(tmp_path, _py("import time; print('up', flush=True); time.sleep(30)"))
    try:
        assert _until(lambda: "up" in jobs.output_tail(jobs.load(job.id), 5))
        # The supervisor records the child's pid once Popen returns; on a busy host the child can
        # print before that.
        assert _until(lambda: jobs.load(job.id).child_pid is not None)
        job = jobs.load(job.id)
        assert jobs.state(job) == "running"
        assert job.supervisor_pid and job.child_pid and job.child_pid != job.supervisor_pid
    finally:
        jobs.cancel(jobs.load(job.id))
        _finished(job.id)


def test_cancel_relays_sigterm_to_the_command_and_records_a_cancelled_job(tmp_path):
    job = _launch(tmp_path, _py("""
        import signal, sys, time
        def stop(*_):
            print('shutting down cleanly', flush=True)
            sys.exit(143)
        signal.signal(signal.SIGTERM, stop)
        print('ready', flush=True)
        time.sleep(60)
    """))
    assert _until(lambda: "ready" in jobs.output_tail(jobs.load(job.id), 5))
    assert jobs.cancel(jobs.load(job.id)) is True
    assert _finished(job.id)
    job = jobs.load(job.id)
    assert jobs.state(job) == "cancelled"
    assert job.cancel_requested and job.exit_code == 143
    assert "shutting down cleanly" in jobs.output_tail(job, 5)


def test_a_job_cancelled_before_its_supervisor_started_never_runs(tmp_path):
    # cancel() can land between the record being written and the supervisor existing.
    d = jobs.create_dir("demo")
    (d / jobs.CANCEL_FILE).write_text("now\n")
    marker = tmp_path / "ran"
    job = jobs.launch(d, kind="run", argv=["run", "demo"], cwd=str(tmp_path), outdir="/o",
                      command=_py(f"open({str(marker)!r}, 'w').close()"))
    assert _finished(job.id)
    job = jobs.load(job.id)
    assert jobs.state(job) == "cancelled" and not marker.exists()
    assert job.error == "cancelled before it started"


def test_cancel_of_a_finished_job_signals_nothing(tmp_path):
    job = _launch(tmp_path, _py("pass"))
    assert _finished(job.id)
    assert jobs.cancel(jobs.load(job.id)) is False
    job = jobs.load(job.id)
    assert not job.cancel_requested and jobs.state(job) == "succeeded"


def test_a_job_outlives_the_process_that_launched_it(tmp_path):
    # The MCP server is that process: closing the client (or restarting the server) must not stop
    # an analysis. Launch from a short-lived interpreter, then read the job back from here.
    launcher = textwrap.dedent(f"""
        import sys
        from runner import jobs
        d = jobs.create_dir("demo")
        jobs.launch(d, kind="run", argv=["run", "demo"], cwd={str(tmp_path)!r},
                    outdir={str(tmp_path / 'out')!r},
                    command=[sys.executable, "-c",
                             "import time; time.sleep(4); print('still here', flush=True)"])
        print(d.name)
    """)
    out = subprocess.run([sys.executable, "-c", launcher], capture_output=True, text=True,
                         env={**os.environ, "PYTHONPATH": str(Path(jobs.__file__).parent.parent)},
                         timeout=60, check=True)
    job_id = out.stdout.strip().splitlines()[-1]
    assert jobs.state(jobs.load(job_id)) == "running"      # the launcher is gone, the job is not
    assert _finished(job_id)
    job = jobs.load(job_id)
    assert jobs.state(job) == "succeeded" and "still here" in jobs.output_tail(job, 3)


def test_a_supervisor_killed_outright_leaves_a_lost_job(tmp_path):
    job = _launch(tmp_path, _py("import time; print('up', flush=True); time.sleep(60)"))
    assert _until(lambda: "up" in jobs.output_tail(jobs.load(job.id), 5))
    job = jobs.load(job.id)
    os.kill(job.supervisor_pid, signal.SIGKILL)
    try:
        assert _finished(job.id)
        job = jobs.load(job.id)
        assert job.exit_code is None and jobs.state(job) == "lost"
    finally:
        os.kill(job.child_pid, signal.SIGKILL)


def test_a_command_that_cannot_start_is_a_failed_job_saying_why(tmp_path):
    job = _launch(tmp_path, [str(tmp_path / "no-such-program")])
    assert _finished(job.id)
    job = jobs.load(job.id)
    assert jobs.state(job) == "failed" and job.exit_code == 127
    assert "could not start" in job.error


def test_launch_refuses_a_missing_working_directory(tmp_path):
    d = jobs.create_dir("demo")
    with pytest.raises(jobs.JobError, match="working directory"):
        jobs.launch(d, kind="run", argv=[], cwd=str(tmp_path / "gone"), outdir="/x",
                    command=_py("pass"))


@pytest.mark.parametrize("bad", ["../etc", "x", "", "20261016T000000-demo-zzzzzz", None])
def test_load_accepts_only_job_ids(bad):
    with pytest.raises(jobs.JobError):
        jobs.load(bad)


def test_load_of_an_unknown_id_says_so():
    with pytest.raises(jobs.JobError, match="no such job"):
        jobs.load("20261016T000000-demo-abcdef")


def test_jobs_are_listed_newest_first(tmp_path):
    first = _launch(tmp_path, _py("pass"), label="first")
    time.sleep(1.1)                                     # ids and timestamps have 1 s resolution
    second = _launch(tmp_path, _py("pass"), label="second")
    assert [j.id for j in jobs.list_jobs()][:2] == [second.id, first.id]
    _finished(first.id)
    _finished(second.id)


def test_state_dir_follows_the_environment(monkeypatch, tmp_path):
    monkeypatch.delenv("NFCLAW_STATE_DIR")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg"))
    assert jobs.state_dir() == tmp_path / "xdg" / "nfclaw"
    monkeypatch.delenv("XDG_STATE_HOME")
    assert jobs.state_dir() == Path.home() / ".local" / "state" / "nfclaw"
