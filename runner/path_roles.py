"""Conservative path roles from source audits of exact, clean pipeline revisions."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

from runner.schema import ParamSchema
from runner.probes import capture
from runner.settings import seconds
from runner.submodule import SubmoduleStatus, _git_env, _own_head


_REGISTRY = Path(__file__).with_name("path_roles.json")


def output_only_directories(st: SubmoduleStatus, schema: ParamSchema) -> frozenset[str]:
    """Audited destination parameters; unknown, changed or unverifiable trees stay inputs.

    Schema annotations and names cannot establish direction: reusable storeDir caches are
    inputs too. Never waive a basename check, only descendant inspection/input capture.
    """
    try:
        registry = json.loads(_REGISTRY.read_text(encoding="utf-8"))
        entries = registry.get(st.commit, {})
        if not isinstance(entries, dict):
            return frozenset()
        names = frozenset(name for name, evidence in entries.items()
                          if isinstance(evidence, dict) and evidence.get("pipeline") == st.name
                          and name in schema.params and schema.params[name].type == "string"
                          and schema.params[name].fmt == "directory-path")
        if not names or _own_head(st.path) != st.commit:
            return frozenset()
        status = capture(
            ["git", "status", "--porcelain", "--untracked-files=all", "--ignore-submodules=none"],
            cwd=st.path, timeout=seconds("NFCLAW_GIT_TIMEOUT", 30), env=_git_env())
        status.check_returncode()
        return names if not status.stdout.strip() else frozenset()
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return frozenset()


def shell_path_directories(st: SubmoduleStatus, schema: ParamSchema) -> frozenset[str]:
    """A bounded source audit also identifies destinations passed as whole shell arguments."""
    verified = output_only_directories(st, schema)
    try:
        entries = json.loads(_REGISTRY.read_text(encoding="utf-8"))[st.commit]
        return frozenset(name for name in verified if entries[name].get("shell_path") is True)
    except (OSError, ValueError, KeyError, AttributeError, TypeError):
        return frozenset()
