"""Shell access to the same durable jobs MCP owns; no pipeline engine needed."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

from runner import cli, job_reports, jobs, mcp_tools
from runner.mcp_server import Context

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def private_state(tmp_path, monkeypatch):
    monkeypatch.setenv("NFCLAW_STATE_DIR", str(tmp_path / "state"))


def record(tmp_path, state="succeeded", *, label="demo", kind="run"):
    directory = jobs.create_dir(label)
    spec = jobs.Job(id=directory.name, kind=kind, argv=["run", label],
                    command=[sys.executable, "-c", "pass"], cwd=str(tmp_path),
                    outdir=str(tmp_path / "out"), created_at="2026-10-30T10:00:00Z",
                    pipeline=label, dir=directory)
    (directory / jobs.JOB_FILE).write_text(json.dumps(spec.spec()))
    terminal = {"succeeded": 0, "failed": 7, "cancelled": 143}
    if state in terminal:
        (directory / jobs.SUPERVISOR_FILE).write_text(json.dumps({
            "exit_code": terminal[state], "finished_at": "2026-10-30T10:01:00Z"}))
    if state == "cancelled":
        (directory / jobs.CANCEL_FILE).write_text("requested\n")
    return jobs.load(spec.id)


def invoke(capsys, *args):
    code = cli.main(["jobs", *args, "--json"])
    output = capsys.readouterr()
    return code, json.loads(output.out), output.err


def test_empty_list_works_without_pipeline_checkout(capsys, monkeypatch):
    monkeypatch.setattr(cli, "_repo_root", lambda: pytest.fail("jobs need no pipeline checkout"))
    assert invoke(capsys, "list") == (0, {"version": 1, "exit_code": 0, "jobs": []}, "")


@pytest.mark.parametrize("state,expected", [
    ("succeeded", 0), ("failed", 1), ("cancelled", 1), ("lost", 1),
])
@pytest.mark.parametrize("kind", ["run", "chain", "replay"])
def test_terminal_status_and_mcp_agree(tmp_path, capsys, state, expected, kind):
    job = record(tmp_path, state, kind=kind)
    (job.dir / jobs.OUTPUT_LOG).write_text("first\nsecond\nthird\n")
    code, result, err = invoke(capsys, "status", job.id, "--log-lines", "2")
    mcp = mcp_tools.NfclawTools(ROOT).call_tool(
        "get_job", {"job_id": job.id, "log_lines": 2}, Context())["structuredContent"]
    assert code == result["exit_code"] == expected
    assert result["version"] == 1 and err == ""
    assert result["job"]["state"] == state
    assert result["job"]["output_tail"] == ["second", "third"]
    assert {k: v for k, v in result["job"].items() if k != "next"} == {
        k: v for k, v in mcp.items() if k != "next"}
    assert "resume=true" not in result["job"]["next"]


def test_list_filters_before_limit_and_matches_mcp(tmp_path, capsys):
    older = record(tmp_path, "failed", label="old")
    newer = record(tmp_path, "succeeded", label="new")
    spec = json.loads((newer.dir / jobs.JOB_FILE).read_text())
    spec["created_at"] = "2026-10-30T11:00:00Z"
    (newer.dir / jobs.JOB_FILE).write_text(json.dumps(spec))
    code, result, _ = invoke(capsys, "list", "--limit", "1")
    assert code == 0 and [r["job_id"] for r in result["jobs"]] == [newer.id]
    _, filtered, _ = invoke(capsys, "list", "--state", "failed", "--limit", "1")
    assert [r["job_id"] for r in filtered["jobs"]] == [older.id]
    mcp = mcp_tools.NfclawTools(ROOT).call_tool(
        "list_jobs", {"state": "failed", "limit": 1}, Context())["structuredContent"]
    assert filtered["jobs"] == mcp["jobs"]


def test_terminal_job_uses_its_private_report(tmp_path, capsys):
    job = record(tmp_path, "failed")
    frozen = {"status_report": "status: old failure", "run_state": "not successful",
              "caveats": True}
    (job.dir / jobs.STATUS_FILE).write_text(json.dumps(frozen))
    # A later run sharing the outdir must never supply this job's report.
    log = Path(job.outdir) / "provenance/logs/run.log"
    log.parent.mkdir(parents=True)
    log.write_text("==> nfclaw run finished 2026-10-30T12:00:00Z: success\n")
    _, result, _ = invoke(capsys, "status", job.id, "--log-lines", "0")
    assert all(result["job"][k] == v for k, v in frozen.items())
    assert result["job"]["output_tail"] == []


@pytest.mark.parametrize("command", ["status", "cancel"])
@pytest.mark.parametrize("job_id", ["../escape", "20261030T100000-unknown-abcdef"])
def test_unknown_job_is_a_json_error(capsys, command, job_id):
    code, result, err = invoke(capsys, command, job_id)
    assert code == result["exit_code"] == 1
    assert result["version"] == 1 and result["job"] is None
    assert result["error"] and "Traceback" not in err


def test_bad_record_does_not_hide_good_jobs(tmp_path, capsys):
    job = record(tmp_path)
    bad = jobs.create_dir("broken")
    (bad / jobs.JOB_FILE).write_text("{}")
    _, result, _ = invoke(capsys, "list")
    assert [r["job_id"] for r in result["jobs"]] == [job.id]
    code, result, _ = invoke(capsys, "status", bad.name)
    assert code == 1 and result["job"] is None and result["error"]


@pytest.mark.parametrize("args", [[], ["list", "--limit", "0"],
    ["list", "--state", "nonsense"], ["status", "x", "--log-lines", "-1"],
    ["status", "x", "--log-lines", "bad"], ["list", "--typo"]])
def test_invalid_usage_is_argparse_error(args, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["jobs", *args])
    assert exc.value.code == 2 and "Traceback" not in capsys.readouterr().err


def test_text_output_includes_human_status_and_tail(tmp_path, capsys):
    job = record(tmp_path)
    (job.dir / jobs.OUTPUT_LOG).write_text("my scientific output\n")
    assert cli.main(["jobs", "status", job.id]) == 0
    assert f"job {job.id}: succeeded" in (out := capsys.readouterr().out)
    assert "my scientific output" in out and job.outdir in out
    assert cli.main(["jobs", "list"]) == 0
    assert job.id in capsys.readouterr().out


@pytest.mark.parametrize("state", ["failed", "cancelled", "lost"])
def test_text_output_names_shell_commands_not_mcp_tools(tmp_path, capsys, state):
    # The shell report is read by someone at a shell: it names `nfclaw` commands, never the MCP
    # tools (`run_status(outdir)`, `get_job`, `read_doc(...)`) or the JSON fields behind them.
    job = record(tmp_path, state)
    supervisor = job.dir / jobs.SUPERVISOR_FILE
    if supervisor.exists():
        data = json.loads(supervisor.read_text())
        data["status_error"] = "could not freeze this job's run status: OSError: disk full"
        supervisor.write_text(json.dumps(data))
    cli.main(["jobs", "status", job.id])
    out = capsys.readouterr().out
    for mcp_only in ("run_status(", "get_job(", "read_doc(", "resume=true", "status_report",
                     "output_tail", "verify_replay"):
        assert mcp_only not in out
    if state == "failed":
        assert f"nfclaw status {job.outdir}" in out


def test_failed_job_without_a_run_report_points_at_its_output_only(tmp_path):
    view = {"state": "failed", "job_id": "x", "kind": "run", "check": False}
    assert "status_report" not in job_reports.next_step(view)
    assert "output_tail" in job_reports.next_step(view)
    assert "status_report" in job_reports.next_step({**view, "status_report": "status: failed"})


@pytest.mark.parametrize("state", ["succeeded", "failed", "cancelled", "lost"])
def test_cancel_terminal_job_signals_nothing(tmp_path, capsys, monkeypatch, state):
    job = record(tmp_path, state)
    monkeypatch.setattr(os, "kill", lambda *_: pytest.fail("terminal job must not be signalled"))
    code, result, _ = invoke(capsys, "cancel", job.id)
    assert code == result["exit_code"] == 0
    assert result["cancel_requested"] is False
    assert result["job"]["state"] == state
    assert (job.dir / jobs.CANCEL_FILE).exists() == (state == "cancelled")


def until(predicate):
    end = time.monotonic() + 15
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.03)
    return False


@pytest.mark.skipif(jobs.fcntl is None, reason="detached jobs need POSIX")
def test_running_job_is_visible_then_cancelled_from_cli(tmp_path, capsys):
    directory = jobs.create_dir("native")
    command = [sys.executable, "-c", "import time; print('ready', flush=True); time.sleep(60)"]
    job = jobs.launch(directory, kind="run", argv=["run", "demo"], cwd=str(tmp_path),
                      outdir=str(tmp_path / "out"), command=command)
    try:
        assert until(lambda: "ready" in jobs.output_tail(jobs.load(job.id), 10))
        code, result, _ = invoke(capsys, "status", job.id)
        assert code == result["exit_code"] == 3
        assert result["job"]["state"] == "running"
        assert result["job"]["phase"] == "preparing"
        assert f"nfclaw jobs cancel {job.id}" in result["job"]["next"]
        _, listing, _ = invoke(capsys, "list", "--state", "running")
        assert [r["job_id"] for r in listing["jobs"]] == [job.id]
        code, result, _ = invoke(capsys, "cancel", job.id)
        assert code == 0 and result["cancel_requested"] is True
        assert result["job"]["state"] in ("running", "cancelled")
        assert until(lambda: not jobs.alive(jobs.load(job.id)))
        code, final, _ = invoke(capsys, "status", job.id)
        assert code == 1 and final["job"]["state"] == "cancelled"
    finally:
        jobs.cancel(jobs.load(job.id))
        assert until(lambda: not jobs.alive(jobs.load(job.id)))


def test_operating_system_failure_still_returns_json(capsys, monkeypatch):
    def denied():
        raise PermissionError("job store is unreadable")
    monkeypatch.setattr(jobs, "list_jobs", denied)
    code, result, err = invoke(capsys, "list")
    assert code == 1 and result == {"version": 1, "exit_code": 1, "jobs": [],
                                    "error": "job store is unreadable"}
    assert "job store is unreadable" in err and "Traceback" not in err


@pytest.mark.skipif(jobs.fcntl is None, reason="running jobs need POSIX locks")
@pytest.mark.parametrize("finished", [False, True])
def test_launched_job_report_matches_mcp(tmp_path, capsys, finished):
    import subprocess
    from runner import runlog
    job = record(tmp_path, "lost")
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "runner"])
    log_dir = Path(job.outdir) / "provenance/logs"
    log = runlog.RunLog.open(log_dir, command=["nextflow"], launch_dir=Path(job.outdir))
    try:
        log.note(f"    pid: {process.pid}")
        if finished:
            log.outcome = "success"
            log.finish()
        spec = json.loads((job.dir / jobs.JOB_FILE).read_text())
        spec["log_path"] = str(log_dir / "run.log")
        (job.dir / jobs.JOB_FILE).write_text(json.dumps(spec))
        with (job.dir / jobs.LOCK_FILE).open("w") as lock:
            jobs.fcntl.flock(lock, jobs.fcntl.LOCK_EX | jobs.fcntl.LOCK_NB)
            _, result, _ = invoke(capsys, "status", job.id)
            mcp = mcp_tools.NfclawTools(ROOT).call_tool(
                "get_job", {"job_id": job.id}, Context())["structuredContent"]
            assert result["job"]["phase"] == ("finishing" if finished else "launched")
            assert result["job"]["run_state"] == ("success" if finished else "running")
            assert {k: v for k, v in result["job"].items() if k != "next"} == {
                k: v for k, v in mcp.items() if k != "next"}
    finally:
        log.finish()
        process.terminate()
        process.wait(timeout=15)


def test_job_status_works_from_another_directory(tmp_path):
    import subprocess
    job = record(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    proc = subprocess.run([sys.executable, "-m", "runner", "jobs", "status", job.id, "--json"],
                          cwd=elsewhere, env=jobs.child_env(), capture_output=True, text=True,
                          timeout=15, check=False)
    assert proc.returncode == 0 and proc.stderr == ""
    assert json.loads(proc.stdout)["job"]["job_id"] == job.id


@pytest.mark.parametrize("command", ["status", "list"])
@pytest.mark.parametrize("outcome,state,code", [
    (0, "succeeded", 0), (7, "failed", 1), (143, "cancelled", 1),
])
def test_completion_between_load_and_liveness_refreshes_report(
        tmp_path, capsys, monkeypatch, command, outcome, state, code):
    job = record(tmp_path, "lost")
    def just_finished(_):
        (job.dir / jobs.SUPERVISOR_FILE).write_text(json.dumps({
            "exit_code": outcome, "finished_at": "2026-10-30T10:01:00Z"}))
        if state == "cancelled":
            (job.dir / jobs.CANCEL_FILE).write_text("requested\n")
        return False
    monkeypatch.setattr(jobs, "alive", just_finished)
    args = (job.id,) if command == "status" else ("--state", state)
    exit_code, result, _ = invoke(capsys, command, *args)
    if command == "status":
        assert exit_code == code
        assert result["job"]["exit_code"] == outcome
        assert result["job"]["state"] == state
        assert result["job"]["finished_at"] == "2026-10-30T10:01:00Z"
    else:
        assert exit_code == 0 and len(result["jobs"]) == 1
        assert result["jobs"][0]["state"] == state
        assert result["jobs"][0]["finished_at"] == "2026-10-30T10:01:00Z"


@pytest.mark.parametrize("field", ["cwd", "outdir", "log_path"])
def test_embedded_nul_path_is_isolated_and_reported_as_json(tmp_path, capsys, field):
    good = record(tmp_path, label="good")
    bad = record(tmp_path, label="bad")
    spec = json.loads((bad.dir / jobs.JOB_FILE).read_text())
    spec[field] = "/bad\x00path"
    (bad.dir / jobs.JOB_FILE).write_text(json.dumps(spec))
    _, listing, _ = invoke(capsys, "list")
    assert [row["job_id"] for row in listing["jobs"]] == [good.id]
    for command in ("status", "cancel"):
        code, result, err = invoke(capsys, command, bad.id)
        assert code == 1 and result["job"] is None and result["error"]
        assert "Traceback" not in err


@pytest.mark.parametrize("filename", [jobs.JOB_FILE, jobs.SUPERVISOR_FILE, jobs.STATUS_FILE])
def test_deeply_nested_durable_json_does_not_break_job_commands(tmp_path, capsys, filename):
    good = record(tmp_path, label="good")
    damaged = record(tmp_path, label="damaged")
    # Exceeds decoder nesting bounds on all supported interpreters without a huge file.
    (damaged.dir / filename).write_text('{"nested":' + '[' * 10000 + '0' + ']' * 10000 + '}')
    code, listing, err = invoke(capsys, "list")
    assert code == 0 and err == ""
    visible = {row["job_id"]: row["state"] for row in listing["jobs"]}
    assert visible[good.id] == "succeeded"
    if filename == jobs.JOB_FILE:
        assert damaged.id not in visible
        for command in ("status", "cancel"):
            code, result, err = invoke(capsys, command, damaged.id)
            assert code == result["exit_code"] == 1
            assert result["version"] == 1 and result["job"] is None and result["error"]
            assert "Traceback" not in err
    else:
        expected = "lost" if filename == jobs.SUPERVISOR_FILE else "succeeded"
        assert visible[damaged.id] == expected
        code, result, err = invoke(capsys, "status", damaged.id)
        assert code == (1 if expected == "lost" else 0)
        assert result["job"]["state"] == expected and err == ""
        code, result, err = invoke(capsys, "cancel", damaged.id)
        assert code == 0 and result["cancel_requested"] is False and err == ""
