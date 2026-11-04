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


def test_output_redaction_precedes_tail_slicing_and_line_splitting(tmp_path):
    job = _launch(tmp_path, _py("pass"))
    assert _finished(job.id)
    secret = "synthetic-credential-first\nsynthetic-credential-second"
    job.argv += [f"--nxf-env=NXF_API_TOKEN={secret}"]
    # The ordinary byte window begins inside the second half of the credential.
    padding = "x" * (jobs._TAIL_BYTES - 12)
    (job.dir / jobs.OUTPUT_LOG).write_text("prefix\n" + secret + "\n" + padding + "\nend\n")
    tail = "\n".join(jobs.output_tail(job, 100))
    assert "credential" not in tail
    assert "synthetic" not in tail
    assert tail.endswith("end")


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


@pytest.mark.parametrize("missing_supervisor_record", [False, True])
def test_a_supervisor_killed_outright_leaves_a_recoverable_job(
        tmp_path, missing_supervisor_record, monkeypatch):
    job = _launch(tmp_path, _py("import time; print('up', flush=True); time.sleep(60)"))
    assert _until(lambda: "up" in jobs.output_tail(jobs.load(job.id), 5))
    job = jobs.load(job.id)
    os.kill(job.supervisor_pid, signal.SIGKILL)
    try:
        assert _finished(job.id)
        if missing_supervisor_record:
            (job.dir / jobs.SUPERVISOR_FILE).unlink()
        job = jobs.load(job.id)
        assert job.exit_code is None and jobs.state(job) == "running"
        assert jobs.orphan_alive(job)
        with monkeypatch.context() as patch:
            patch.setattr(jobs.process_identity, 'send', lambda *_args: False)
            with pytest.raises(jobs.JobError, match='still running'):
                jobs.cancel(job)
            assert jobs.state(job) == 'running'
        assert jobs.cancel(job)
        assert _until(lambda: not jobs.orphan_alive(jobs.load(job.id)))
        assert jobs.state(jobs.load(job.id)) == "cancelled"
    finally:
        try:
            os.kill(job.child_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def test_orphan_recovery_never_signals_a_reused_or_unreadable_identity(tmp_path, monkeypatch):
    job = _launch(tmp_path, _py("import time; print('up', flush=True); time.sleep(60)"))
    assert _until(lambda: "up" in jobs.output_tail(jobs.load(job.id), 5))
    assert _until(lambda: jobs.load(job.id).child_identity is not None)
    job = jobs.load(job.id)
    os.kill(job.supervisor_pid, signal.SIGKILL)
    assert _finished(job.id)
    try:
        job.child_identity = {**job.child_identity, "start": "a different process"}
        assert not jobs.cancel(job)
        assert jobs.state(job) == "lost"
        monkeypatch.setattr(jobs.process_identity, "read", lambda _pid: None)
        assert not jobs.cancel(jobs.load(job.id))
        assert not job.cancel_requested
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


def test_state_dir_is_one_place_whatever_directory_a_process_starts_in(monkeypatch, tmp_path):
    # The server, its job supervisors and `nfclaw jobs` in another shell must find one job store.
    # A relative XDG_STATE_HOME is invalid by the XDG base-directory spec and is ignored; a
    # relative NFCLAW_STATE_DIR is taken from where it is read, and kept absolute from then on.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NFCLAW_STATE_DIR")
    monkeypatch.setenv("XDG_STATE_HOME", "relative-xdg")
    assert jobs.state_dir() == Path.home() / ".local" / "state" / "nfclaw"
    monkeypatch.setenv("NFCLAW_STATE_DIR", "relative-state")
    assert jobs.state_dir() == tmp_path / "relative-state"
    assert jobs.state_dir().is_absolute()


def test_load_recovers_supervisor_identity_after_submitter_crash(tmp_path):
    import json
    job = _launch(tmp_path, _py('import time; print("up", flush=True); time.sleep(60)'))
    try:
        assert _until(lambda: jobs.load(job.id).child_pid is not None)
        path = job.dir / jobs.JOB_FILE
        record = json.loads(path.read_text())
        record['supervisor_pid'] = None  # server crashed before its second atomic write
        path.write_text(json.dumps(record))
        recovered = jobs.load(job.id)
        assert recovered.supervisor_pid == job.supervisor_pid
        assert jobs.cancel(recovered)
        assert _finished(job.id)
        assert jobs.state(jobs.load(job.id)) == 'cancelled'
    finally:
        jobs.cancel(job)
        _finished(job.id)


@pytest.mark.parametrize('damage', [None, [], {'kind': 'invalid'}, {'id': 'wrong'},
                                    {'created_at': []}, {'argv': 'run demo'}, {'dir': '/other'},
                                    {'supervisor_pid': 'not-a-pid'},
                                    {'supervisor_pid': 2**40}, {'supervisor_pid': 0}])
def test_malformed_job_is_isolated_from_listing_and_new_submissions(tmp_path, damage):
    import json
    first = _launch(tmp_path, _py('pass'))
    assert _finished(first.id)
    damaged = jobs.create_dir('broken')
    record = first.spec()
    record['id'] = damaged.name
    if isinstance(damage, dict):
        record.update(damage)
    else:
        record = damage
    (damaged / jobs.JOB_FILE).write_text(json.dumps(record))
    with pytest.raises(jobs.JobError):
        jobs.load(damaged.name)
    assert [j.id for j in jobs.list_jobs()] == [first.id]
    later = _launch(tmp_path, _py('pass'))
    assert _finished(later.id)
    assert set(j.id for j in jobs.list_jobs()) == {first.id, later.id}


def test_frozen_replay_status_retains_ignored_task_caveats_from_its_engine_log(tmp_path):
    import json
    d = jobs.create_dir('replay')
    out = tmp_path / 'replay'
    log = out / 'provenance/logs/run.log'
    log.parent.mkdir(parents=True)
    log.write_text('==> nfclaw replay started 2026-10-26T00:00:00Z\n'
                   '    pid: 222\n'
                   '==> nfclaw replay finished 2026-10-26T00:00:01Z: success\n')
    (out / '.nextflow.log').write_text(
        'Workflow completed > WorkflowStats[ignoredCount=2; cachedCount=0]\n')
    jobs._freeze_run_status(d, {'log_path': str(log), 'log_size_before': None,
                               'child_pid': 222})
    frozen = json.loads((d / jobs.STATUS_FILE).read_text())
    assert frozen['caveats'] is True
    assert 'Nextflow ignored 2 failed task(s)' in frozen['status_report']


def test_a_job_that_never_opened_its_run_log_freezes_nothing_and_reports_no_error(tmp_path):
    # A run refused before launch into a fresh --outdir (an invalid parameter, a missing
    # samplesheet) never creates its run log. That is no failure to retain a report: the
    # supervisor used to record "could not freeze this job's run status: FileNotFoundError", and
    # get_job / `nfclaw jobs status` showed it beside the real refusal as if nfclaw had broken.
    import json
    handlers = {sig: signal.getsignal(sig)
                for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}
    d = jobs.create_dir('refused')
    job = jobs.Job(id=d.name, kind='run', argv=['run', 'demo'], command=_py('raise SystemExit(1)'),
                   cwd=str(tmp_path), outdir=str(tmp_path / 'out'), created_at=jobs._now(),
                   log_path=str(tmp_path / 'out/provenance/logs/run.log'), dir=d)
    (d / jobs.JOB_FILE).write_text(json.dumps(job.spec()))
    try:
        assert jobs.supervise(d) == 0
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
    loaded = jobs.load(d.name)
    assert loaded.exit_code == 1 and loaded.status_error is None
    assert not (d / jobs.STATUS_FILE).exists() and not (d / 'run.log').exists()


def test_refused_concurrent_job_never_borrows_the_accepted_jobs_log(tmp_path):
    d = jobs.create_dir('refused')
    log = tmp_path / 'out/provenance/logs/run.log'
    log.parent.mkdir(parents=True)
    log.write_text('==> nfclaw run started 2026-10-26T00:00:00Z\n'
                   '    pid: 111\n'
                   '==> nfclaw run finished 2026-10-26T00:00:01Z: success\n')
    jobs._freeze_run_status(d, {'log_path': str(log), 'log_size_before': None,
                               'child_pid': 222})
    assert not (d / jobs.STATUS_FILE).exists()


def test_concurrent_job_snapshot_selects_its_own_pid_segment(tmp_path):
    import json
    d = jobs.create_dir('accepted')
    log = tmp_path / 'out/provenance/logs/run.log'
    log.parent.mkdir(parents=True)
    log.write_text('==> nfclaw run started 2026-10-26T00:00:00Z\n'
                   '    pid: 111\n'
                   '==> nfclaw run finished 2026-10-26T00:00:01Z: refused before launch\n'
                   '==> nfclaw run started 2026-10-26T00:00:02Z\n'
                   '    pid: 222\n'
                   '==> nfclaw run finished 2026-10-26T00:00:03Z: success\n')
    jobs._freeze_run_status(d, {'log_path': str(log), 'log_size_before': None,
                               'child_pid': 222})
    assert json.loads((d / jobs.STATUS_FILE).read_text())['run_state'] == 'success'


@pytest.mark.parametrize('recorded', [False, True])
@pytest.mark.parametrize('absolute', [False, True])
def test_frozen_replay_status_uses_effective_custom_engine_log(
        tmp_path, monkeypatch, recorded, absolute):
    import json
    from runner import replay_guard
    d = jobs.create_dir('replay')
    out = tmp_path / 'replay'
    original = tmp_path / 'original'
    bundle = original / 'provenance'
    bundle.mkdir(parents=True)
    raw = str(tmp_path / 'engine.log') if absolute else 'custom-engine.log'
    env = {'NXF_LOG_FILE': raw} if recorded else {}
    (bundle / 'run_manifest.json').write_text(json.dumps({'nextflow_env': env}))
    monkeypatch.setenv('NXF_LOG_FILE', 'wrong-ambient.log' if recorded else raw)
    log = out / 'provenance/logs/run.log'
    log.parent.mkdir(parents=True)
    engine = (Path(raw) if absolute else out / raw) if recorded else out / '.nextflow.log'
    engine.write_text('Workflow completed > WorkflowStats[ignoredCount=2; cachedCount=0]\n')
    decoy = out / '.nextflow.log' if recorded else (Path(raw) if absolute else out / raw)
    decoy.write_text('Workflow completed > WorkflowStats[ignoredCount=0]\n')
    replay_guard.start_replay_log(log, str(original), '222')
    with log.open('a') as stream:
        stream.write('==> nfclaw replay finished 2026-10-26T00:00:03Z: success\n')
    jobs._freeze_run_status(d, {'log_path': str(log), 'child_pid': 222})
    frozen = json.loads((d / jobs.STATUS_FILE).read_text())
    assert frozen['caveats'] is True
    assert 'Nextflow ignored 2 failed task(s)' in frozen['status_report']


@pytest.mark.parametrize('pid', [2**40, 0, -3, 'x', 1.5])
def test_a_supervisor_record_with_an_impossible_pid_is_refused(tmp_path, pid):
    # A pid beyond the platform's range made `cancel_job` raise OverflowError from os.kill.
    import json
    job = _launch(tmp_path, _py('pass'))
    assert _finished(job.id)
    record = json.loads((job.dir / jobs.SUPERVISOR_FILE).read_text())
    (job.dir / jobs.SUPERVISOR_FILE).write_text(json.dumps({**record, 'child_pid': pid}))
    with pytest.raises(jobs.JobError, match='malformed supervisor record'):
        jobs.load(job.id)


def test_the_exit_code_is_recorded_whatever_freezing_the_status_raises(tmp_path, monkeypatch):
    # Only OSError/ValueError were caught: any other exception while freezing the run's status
    # killed the supervisor before it recorded the exit code, and a finished job read as `lost`.
    import json
    handlers = {sig: signal.getsignal(sig)
                for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}

    def broken(job_dir, spec):
        raise RuntimeError('unexpected')
    monkeypatch.setattr(jobs, '_freeze_run_status', broken)
    d = jobs.create_dir('demo')
    job = jobs.Job(id=d.name, kind='run', argv=['run', 'demo'], command=_py('pass'),
                   cwd=str(tmp_path), outdir=str(tmp_path / 'out'), created_at=jobs._now(),
                   log_path=str(tmp_path / 'out/provenance/logs/run.log'), dir=d)
    (d / jobs.JOB_FILE).write_text(json.dumps(job.spec()))
    try:
        assert jobs.supervise(d) == 0
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
    loaded = jobs.load(d.name)
    assert loaded.exit_code == 0 and loaded.finished_at
    assert loaded.status_error == ("could not freeze this job's run status: "
                                   "RuntimeError: unexpected")
