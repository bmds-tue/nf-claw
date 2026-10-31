"""Shared shell/MCP presentation of durable supervised jobs."""
from __future__ import annotations

import shlex
from collections.abc import Callable
from pathlib import Path

from runner import jobs


def launched(job: jobs.Job) -> bool:
    """Whether nfclaw has opened this job's run (or chain) log: it passed validation and
    preflight and is starting Nextflow."""
    if not job.log_path or job.check:
        return False
    try:
        size = Path(job.log_path).stat().st_size
    except OSError:
        return False
    return job.log_size_before is None or size > job.log_size_before


def _snapshot(job: jobs.Job) -> tuple[jobs.Job, str]:
    state = jobs.state(job)
    if state != "running":
        # Final metadata is written before the supervisor releases its lock. The original load
        # may predate that write; once unlocked, reload before deriving any terminal outcome.
        job = jobs.load(job.id)
        state = jobs.state(job)
    return job, state


def view(job: jobs.Job, *, log_lines: int, live_status: Callable[[str], dict],
         cli: bool = False) -> dict:
    job, state = _snapshot(job)
    command = job.command if job.kind == "replay" else ["nfclaw", *job.argv]
    view = {"job_id": job.id, "kind": job.kind, "pipeline": job.pipeline, "state": state,
            "check": job.check, "outdir": job.outdir,
            "command": shlex.join(command),
            "cwd": job.cwd,
            "created_at": job.created_at, "finished_at": job.finished_at,
            "exit_code": job.exit_code}
    has_launched = launched(job)
    frozen = jobs.run_status(job) if state != "running" else {}
    if frozen:
        view.update(frozen)
        view["log"] = job.log_path
    elif has_launched and state == "running":
        view.update(live_status(job.outdir))
        view["log"] = job.log_path
    if state == "running":
        view["phase"] = ("launched" if view.get("run_state") == "running"
                         else "finishing" if has_launched else "preparing")
    if job.error:
        view["error"] = job.error
    if job.status_error and not frozen:
        # The job ended, but its own run report was not retained: say why it is absent.
        view["status_error"] = job.status_error
    view["output_tail"] = jobs.output_tail(job, log_lines)
    view["output_log"] = str(job.dir / jobs.OUTPUT_LOG)
    view["next"] = next_step(view, cli=cli)
    if cli:
        view["next"] = (view["next"].replace("resume=true", "--resume")
                        .replace("verify_replay", "nfclaw verify"))
    return view


def list_views(*, state: str | None = None, limit: int = 20) -> list[dict]:
    """Newest valid jobs, filtering before limiting, for both shell and MCP consumers."""
    rows = []
    for job in jobs.list_jobs():
        try:
            job, current = _snapshot(job)
        except jobs.JobError:
            continue                         # a record removed or damaged during listing
        if state and current != state:
            continue
        rows.append({"job_id": job.id, "kind": job.kind, "pipeline": job.pipeline,
                     "state": current, "check": job.check, "outdir": job.outdir,
                     "created_at": job.created_at, "finished_at": job.finished_at})
        if len(rows) >= limit:
            break
    return rows


def render_list(rows: list[dict]) -> str:
    return "\n".join(f"{r['job_id']}  {r['state']:<9}  {'check ' if r['check'] else ''}"
                     f"{r['kind']}  {r['outdir']}" for r in rows) or "No jobs."


def next_step(view: dict, *, cli: bool = False) -> str:
    state, jid = view["state"], view["job_id"]
    if state == "running" and cli:
        return f"nfclaw jobs status {jid} to follow it; nfclaw jobs cancel {jid} to stop it."
    if state == "running":
        return (f"get_job(job_id={jid!r}, wait_seconds=60) to follow it; "
                f"cancel_job(job_id={jid!r}) to stop it.")
    if view["kind"] == "replay":
        if state == "succeeded":
            return (f"Replay results are in {view['outdir']}. Retain the original replay bundle "
                    "and compare the outputs with verify_replay before using them.")
        return "Inspect this replay's status and logs; retry into a new empty destination."
    if state == "succeeded":
        if view["check"]:
            return "Validation passed: run the same arguments without check to launch it."
        return (f"Results are in {view['outdir']} (provenance/ holds the replay bundle)."
                + (" Read the caveats in status_report before using them." if view.get("caveats")
                   else ""))
    if state == "cancelled":
        return "Stopped. Resubmit with resume=true to continue from Nextflow's cache."
    if state == "lost":
        return ("The job's supervisor was killed (or the host restarted). status_report says "
                "whether nfclaw itself is still running; otherwise resubmit with resume=true.")
    known_issues = ("docs/known-issues.md" if cli else
                    'look it up with read_doc(guide="known-issues", search=...)')
    return (f"Read status_report / output_tail for the cause ({known_issues}), "
            "fix it, then resubmit" + (" with resume=true." if view.get("status_report") and
                                   not view["check"] else "."))


def render(view: dict) -> str:
    phase = f" ({view['phase']})" if view.get("phase") else ""
    kind = ("check " if view["check"] else "") + view["kind"]
    lines = [f"job {view['job_id']}: {view['state']}{phase}",
             f"{kind}: {view['command']}", f"outdir: {view['outdir']}"]
    if view.get("exit_code") is not None:
        lines.append(f"exit code: {view['exit_code']}")
    if view.get("error"):
        lines.append(f"error: {view['error']}")
    if view.get("status_error"):
        lines.append(f"status: {view['status_error']}; run_status(outdir) reads the live log")
    if view.get("status_report"):
        lines += ["", "nfclaw status:", view["status_report"]]
    if view.get("output_tail"):
        lines += ["", f"output (last {len(view['output_tail'])} lines of {view['output_log']}):",
                  *view["output_tail"]]
    lines += ["", f"next: {view['next']}"]
    return "\n".join(lines)
