"""Which nfclaw this is: its package version, and the commit of the checkout it runs from.

The package version alone does not change from one commit to the next, so the checkout's commit is
what identifies the code: `nfclaw --version` prints both, and every provenance bundle records them
beside the pipeline's own revision.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def package_version() -> str:
    """This checkout's `pyproject.toml` version, else the installed distribution's."""
    try:
        import tomllib
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        if isinstance(found := project.get("project", {}).get("version"), str) and found:
            return found
    except (OSError, ValueError, AttributeError):
        pass
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version("nfclaw")
    except PackageNotFoundError:
        return "unknown"


@lru_cache(maxsize=1)
def commit() -> str | None:
    """The checkout's Git HEAD, or None for an installed copy outside one."""
    from runner.replay_guard import pipeline_head
    head = pipeline_head(ROOT)
    return head if head and re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", head) else None


def identity() -> dict[str, str | None]:
    """What a provenance bundle records about the nfclaw that wrote it."""
    return {"version": package_version(), "commit": commit()}


def describe() -> str:
    """`nfclaw --version`: `nfclaw 1.0.0 (commit 0123456789ab)`."""
    head = commit()
    return f"nfclaw {package_version()}" + (f" (commit {head[:12]})" if head else "")
