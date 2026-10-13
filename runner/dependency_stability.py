"""Compare declared local dependencies at launch and completion, without trusting timestamps."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from subprocess import SubprocessError

from runner.replay_guard import hash_pipeline, pipeline_head, snapshot_inputs

FAILED_OUTCOME = "failed after Nextflow succeeded (local dependencies changed)"
FAILED_EXECUTION_OUTCOME = "failed (local dependencies changed during execution)"


def compare(*, inputs: list[Path], input_checksums: dict, input_inventory: dict,
            configs: tuple[Path, ...], config_checksums: dict, config_inventory: dict,
            pipeline: Path, pipeline_checksums: dict, git_head: str | None) -> dict:
    issues = []
    for kind, paths, before_hashes, before_nodes in (
        ("inputs", inputs, input_checksums, input_inventory),
        ("configs", list(configs), config_checksums, config_inventory),
    ):
        try:
            after_hashes, after_nodes = snapshot_inputs(paths)
        except (OSError, ValueError) as exc:
            issues.append({"kind": kind, "change": "unreadable", "error": str(exc)})
            continue
        for name in sorted(before_nodes.keys() | after_nodes.keys()):
            if before_nodes.get(name) != after_nodes.get(name):
                issues.append({"kind": kind, "path": name, "change": "namespace",
                               "before": before_nodes.get(name), "after": after_nodes.get(name)})
        for name in sorted(before_hashes.keys() | after_hashes.keys()):
            if before_hashes.get(name) != after_hashes.get(name):
                issues.append({"kind": kind, "path": name, "change": "content",
                               "before": before_hashes.get(name), "after": after_hashes.get(name)})
    try:
        after_hashes = hash_pipeline(pipeline)
        after_head = pipeline_head(pipeline)
    except (OSError, ValueError, SubprocessError) as exc:
        issues.append({"kind": "pipeline", "change": "unreadable", "error": str(exc)})
    else:
        if after_head != git_head:
            issues.append({"kind": "pipeline", "path": str(pipeline), "change": "revision",
                           "before": git_head, "after": after_head})
        for name in sorted(pipeline_checksums.keys() | after_hashes.keys()):
            if pipeline_checksums.get(name) != after_hashes.get(name):
                issues.append({"kind": "pipeline", "path": str(pipeline / name), "change": "content",
                               "before": pipeline_checksums.get(name), "after": after_hashes.get(name)})
    return {"version": 1, "status": "changed" if issues else "unchanged",
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "issues": issues}
