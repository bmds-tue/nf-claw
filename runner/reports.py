"""Version 1 machine-readable results, shared by the CLI and MCP adapter."""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from runner import acceptance, runlog


def task_progress(outdir: Path) -> dict:
    """Count only observed trace rows. A workflow's eventual task count stays unknown."""
    unknown = {"source": None, "observed_tasks": None, "expected_tasks": None, "counts": {}}
    try:
        candidates = sorted((outdir / "pipeline_info").glob("*trace*.txt"),
                            key=lambda p: p.stat().st_mtime_ns, reverse=True)
        for path in candidates:
            counts = Counter()
            seen = set()
            truncated = False
            with path.open(encoding="utf-8", errors="replace", newline="") as stream:
                reader = csv.DictReader(stream, delimiter="\t")
                if not {"task_id", "status"} <= set(reader.fieldnames or []):
                    continue
                for row in reader:
                    if len(seen) >= 100_000:
                        truncated = True
                        break
                    tid, status = row.get("task_id"), row.get("status")
                    if tid and status and tid not in seen:
                        seen.add(tid)
                        counts[status] += 1
            return {"source": str(path), "observed_tasks": len(seen), "expected_tasks": None,
                    "counts": dict(counts), "truncated": truncated}
    except (OSError, csv.Error):
        pass
    return unknown


def status(outdir: Path, state: runlog.RunState, *, report: str) -> dict:
    code = 0 if state.state == "success" else 3 if state.state == "running" else 1
    manifest = {}
    try:
        found = json.loads((outdir / "provenance/run_manifest.json").read_text(encoding="utf-8"))
        if isinstance(found, dict):
            manifest = found
    except (OSError, ValueError):
        pass
    caveats = manifest.get("completion_caveats", state.caveats)
    if not isinstance(caveats, list) or not all(isinstance(c, str) for c in caveats):
        caveats = state.caveats
    return {"schema_version": 1, "kind": state.kind, "outdir": str(outdir),
            "state": state.state, "outcome": state.outcome, "exit_code": code,
            "started_at": state.started, "finished_at": state.finished,
            "log": str(state.log), "nextflow_log": state.nextflow_log,
            "last_output": state.last_output, "errors": state.error,
            "completion_caveats": caveats,
            "completion_conditions": acceptance.evaluate(caveats)["conditions"],
            "acceptance": manifest.get("acceptance"), "progress": task_progress(outdir),
            "report": report}


def verification(comparison, *, strict: bool, report: str) -> dict:
    passed = ((comparison.byte_identical and comparison.same_environment) if strict
              else comparison.structurally_equal)
    return {"schema_version": 1, "kind": "verification", "passed": passed, "strict": strict,
            "exit_code": 0 if passed else 1, "comparison": asdict(comparison), "report": report}
