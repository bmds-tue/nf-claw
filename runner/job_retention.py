"""Prune completed-job metadata under an exclusive lease, preserving run data."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from runner import jobs

_METADATA = (jobs.JOB_FILE, jobs.SUPERVISOR_FILE, jobs.OUTPUT_LOG, jobs.CANCEL_FILE)


def _dependencies(recorded: list[jobs.Job]) -> set[Path]:
    paths = set()
    for job in recorded:
        paths.add(Path(job.outdir).resolve())
        for kind in ("inputs", "configs"):
            path = Path(job.outdir) / "provenance" / f"{kind}.inventory.json"
            try:
                inventory = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(inventory, dict):
                continue
            for name, entry in inventory.items():
                if isinstance(name, str) and Path(name).is_absolute():
                    paths.add(Path(name).resolve())
                if isinstance(entry, dict) and isinstance(entry.get("resolved_path"), str):
                    paths.add(Path(entry["resolved_path"]).resolve())
        for token in job.argv:
            value = token.partition("=")[2] if token.startswith("--") and "=" in token else token
            if Path(value).is_absolute():
                paths.add(Path(value).resolve())
    return paths


def prune(*, older_than_days: int = 30, keep: int = 20, apply: bool = False,
          now: datetime | None = None) -> dict:
    """Preview by default; delete only known metadata, retaining specs and unknown files.

    Active, unfinished, recent and dependency-bearing records are protected.
    Scientific output directories, engine/work caches and replay specs are never removed.
    """
    if type(older_than_days) is not int or older_than_days < 1 or type(keep) is not int or keep < 0:
        raise jobs.JobError("older_than_days must be positive and keep must be nonnegative")
    if jobs.fcntl is None:
        raise jobs.JobError("safe job pruning requires POSIX locking")
    cutoff = (now or datetime.now(UTC)) - timedelta(days=older_than_days)
    recorded = jobs.list_jobs()
    dependencies = _dependencies(recorded)
    candidates, protected, removed = [], [], []
    completed_seen = 0
    for job in recorded:
        reason = None
        if jobs.alive(job) or job.exit_code is None or not job.finished_at:
            reason = "active or no recorded terminal outcome"
        else:
            completed_seen += 1
            try:
                finished = datetime.fromisoformat(job.finished_at)
                if finished.tzinfo is None or finished >= cutoff or completed_seen <= keep:
                    reason = "recent, retained, or ambiguous completion time"
            except (ValueError, TypeError):
                reason = "invalid completion time"
        directory = job.dir.resolve()
        outdir = Path(job.outdir).resolve()
        if outdir.is_relative_to(directory):
            reason = "scientific output directory is inside job metadata"
        files = [job.dir / name for name in _METADATA if (job.dir / name).exists()]
        if any(path.resolve() == dependency or path.resolve().is_relative_to(dependency)
               for path in files for dependency in dependencies):
            reason = "metadata is required by a recorded run dependency"
        if reason:
            protected.append({"job_id": job.id, "reason": reason})
            continue
        try:
            fd = os.open(job.dir / jobs.LOCK_FILE, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        except OSError:
            protected.append({"job_id": job.id, "reason": "job lease cannot be inspected"})
            continue
        try:
            try:
                jobs.fcntl.flock(fd, jobs.fcntl.LOCK_EX | jobs.fcntl.LOCK_NB)
            except (OSError, BlockingIOError):
                protected.append({"job_id": job.id, "reason": "job supervisor holds its lease"})
                continue
            latest = jobs.load(job.id)
            if latest.finished_at != job.finished_at or latest.exit_code != job.exit_code:
                protected.append({"job_id": job.id, "reason": "job outcome changed during pruning"})
                continue
            candidates.append({"job_id": job.id, "files": [str(p) for p in files]})
            if apply:
                for path in files:
                    path.unlink(missing_ok=True)
                removed.append(job.id)
        except jobs.JobError:
            protected.append({"job_id": job.id, "reason": "job record changed during pruning"})
        finally:
            os.close(fd)
    return {"schema_version": 1, "kind": "job_pruning", "applied": apply,
            "older_than_days": older_than_days, "keep": keep, "candidates": candidates,
            "protected": protected, "removed": removed}
