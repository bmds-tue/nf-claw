"""Pin nf-core's institutional configs to the nf-core/configs commit a run reads.

Every nf-core release includes `nfcore_custom.config` (and often `pipeline/<name>.config`) from
`https://raw.githubusercontent.com/nf-core/configs/${params.custom_config_version}` at launch, with
`custom_config_version` defaulting to the moving `master` branch. Its institutional profiles set
executors, container options and resources, and a broken commit there breaks every launch, so the
run and its replay would read whatever `master` holds on the day. nfclaw resolves the branch to its
commit before launch and passes that commit as `custom_config_version`, exactly as nf-core documents
for pinning institutional configs: the run reads an immutable revision, `params.json` records it,
and `commands.sh` replays it.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

REPOSITORY = "https://github.com/nf-core/configs"
PARAM = "custom_config_version"
BASE_PARAM = "custom_config_base"
_INCLUDED = re.compile(
    r"raw\.githubusercontent\.com/nf-core/configs/\$\{\s*params\.custom_config_version\s*\}")
_DEFAULT = re.compile(r"^\s*custom_config_version\s*=\s*['\"]([^'\"]+)['\"]", re.M)
_COMMIT = re.compile(r"[0-9a-f]{40}")


def _ls_remote(repository: str, ref: str) -> tuple[str | None, str | None]:
    """(commit, None) for a branch head, or (None, why it could not be resolved)."""
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--exit-code", repository, f"refs/heads/{ref}"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"git ls-remote could not run: {exc}"
    fields = result.stdout.split()
    if result.returncode == 0 and fields and _COMMIT.fullmatch(fields[0]):
        return fields[0], None
    reason = (result.stderr.strip().splitlines() or [f"exit status {result.returncode}"])[-1]
    return None, f"git ls-remote {repository} {ref} failed: {reason[:200]}"


def pin(merged: dict, schema_params, upstream: Path, env: dict[str, str], *,
        previous: str | None = None) -> tuple[dict, dict | None, str | None]:
    """(params, manifest record, advisory) with `custom_config_version` pinned to a commit.

    Applies only where the pinned release includes nf-core/configs by `custom_config_version`, the
    caller set neither that nor `custom_config_base`, and NXF_OFFLINE (which skips the include) is
    unset. `previous` is the commit an earlier attempt of a resumed run pinned: it is kept, so every
    attempt of one run reads the same configs.
    """
    if PARAM not in schema_params or env.get("NXF_OFFLINE"):
        return merged, None, None
    if merged.get(PARAM) is not None or merged.get(BASE_PARAM) is not None:
        value = merged.get(PARAM)
        if merged.get(BASE_PARAM) is None and isinstance(value, str) and _COMMIT.fullmatch(value):
            return merged, {"repository": REPOSITORY, "ref": value, "commit": value}, None
        return merged, None, None
    try:
        config = (upstream / "nextflow.config").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return merged, None, None
    default = _DEFAULT.search(config)
    if not _INCLUDED.search(config) or default is None:
        return merged, None, None
    ref = default[1]
    if _COMMIT.fullmatch(ref):
        return merged, None, None                       # the release already pins a commit
    commit, error = ((previous, None) if previous and _COMMIT.fullmatch(previous)
                     else _ls_remote(REPOSITORY, ref))
    if commit is None:
        if error is None:
            return merged, None, None
        return merged, {"repository": REPOSITORY, "ref": ref, "commit": None, "error": error}, (
            f"nf-core institutional configs are not pinned ({error}); the run reads "
            f"nf-core/configs `{ref}` as it is at launch, and a replay reads it as it is then")
    record = {"repository": REPOSITORY, "ref": ref, "commit": commit}
    return {**merged, PARAM: commit}, record, (
        f"nf-core institutional configs pinned to nf-core/configs@{commit[:12]} (`{ref}` at "
        f"launch) via --{PARAM.replace('_', '-')}; the replay reads the same revision")


def previous_commit(outdir: Path) -> str | None:
    """The configs commit an earlier attempt in this outdir pinned, from its params.json."""
    try:
        params = json.loads((outdir / "provenance" / "params.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    value = params.get(PARAM) if isinstance(params, dict) else None
    return value if isinstance(value, str) and _COMMIT.fullmatch(value) else None
