"""Shared shell/MCP presentation of durable supervised jobs."""
from __future__ import annotations

import shlex
from collections.abc import Callable
from pathlib import Path

from runner import jobs, redaction


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
            "command": shlex.join(redaction.argv(command)),
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
        if not jobs.alive(job):
            view["phase"] = "orphaned"
            view["supervision_error"] = ("The supervisor stopped, but its command is still alive. "
                                         "Cancellation uses its verified birth identity.")
    elif state == "lost":
        view["supervision_error"] = ("The supervisor stopped without an outcome. No surviving "
                                     "command could be authenticated; inspect the executor before "
                                     "resuming. Unreadable identity is not proof of exit.")
    if job.error:
        view["error"] = job.error
    if job.status_error and not frozen:
        # The job ended, but its own run report was not retained: say why it is absent.
        view["status_error"] = job.status_error
    view["output_tail"] = jobs.output_tail(job, log_lines)
    view["output_log"] = str(job.dir / jobs.OUTPUT_LOG)
    view["next"] = next_step(view, cli=cli)
    return redaction.data(view, redaction.assignments([*job.command, *job.argv]))


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
    """What to do about the job, in the words of whoever reads it: `nfclaw` commands at a shell,
    the MCP tools and the fields of this view for a client."""
    state, jid = view["state"], view["job_id"]
    resume = "--resume" if cli else "resume=true"
    if state == "running" and cli:
        return f"nfclaw jobs status {jid} to follow it; nfclaw jobs cancel {jid} to stop it."
    if state == "running":
        return (f"get_job(job_id={jid!r}, wait_seconds=60) to follow it; "
                f"cancel_job(job_id={jid!r}) to stop it.")
    if view["kind"] == "replay":
        if state == "succeeded":
            return (f"Replay results are in {view['outdir']}. Retain the original replay bundle "
                    f"and compare the outputs with {'nfclaw verify' if cli else 'verify_replay'} "
                    "before using them.")
        return "Inspect this replay's status and logs; retry into a new empty destination."
    if state == "succeeded":
        if view["check"]:
            check = "--check" if cli else "check"
            return f"Validation passed: run the same arguments without {check} to launch it."
        return (f"Results are in {view['outdir']} (provenance/ holds the replay bundle)."
                + (f" Read the caveats in {'its nfclaw status report' if cli else 'status_report'} "
                   "before using them." if view.get("caveats") else ""))
    if state == "cancelled":
        return f"Stopped. Resubmit with {resume} to continue from Nextflow's cache."
    if state == "lost":
        status = f"`nfclaw status {view['outdir']}`" if cli else "status_report"
        return (f"The job's supervisor was killed (or the host restarted). {status} says "
                f"whether nfclaw itself is still running; otherwise resubmit with {resume}.")
    known_issues = ("docs/known-issues.md" if cli else
                    'look it up with read_doc(guide="known-issues", search=...)')
    # A job refused before launch has no run report of its own: its output says why.
    report = view.get("status_report")
    evidence = (("the nfclaw status report and output above" if report else "the output above")
                if cli else ("status_report / output_tail" if report else "output_tail"))
    return (f"Read {evidence} for the cause ({known_issues}), fix it, then resubmit"
            + (f" with {resume}." if report and not view["check"] else "."))


def render(view: dict, *, cli: bool = False) -> str:
    phase = f" ({view['phase']})" if view.get("phase") else ""
    kind = ("check " if view["check"] else "") + view["kind"]
    lines = [f"job {view['job_id']}: {view['state']}{phase}",
             f"{kind}: {view['command']}", f"outdir: {view['outdir']}"]
    if view.get("exit_code") is not None:
        lines.append(f"exit code: {view['exit_code']}")
    if view.get("error"):
        lines.append(f"error: {view['error']}")
    if view.get("status_error"):
        live = f"`nfclaw status {view['outdir']}`" if cli else "run_status(outdir)"
        lines.append(f"status: {view['status_error']}; {live} reads the live log")
    if view.get("supervision_error"):
        lines.append(view["supervision_error"])
    if view.get("status_report"):
        lines += ["", "nfclaw status:", view["status_report"]]
    if view.get("output_tail"):
        lines += ["", f"output (last {len(view['output_tail'])} lines of {view['output_log']}):",
                  *view["output_tail"]]
    lines += ["", f"next: {view['next']}"]
    return "\n".join(lines)
