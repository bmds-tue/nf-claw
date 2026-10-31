"""Whether a pipeline's configuration compiles with the engine a run will use.

`nextflow config` resolves the pipeline's config and selected profiles without running anything (a
few seconds). It catches the one failure no schema can predict: a release whose configuration the
engine rejects outright — an older release on Nextflow 26.04's strict parser — which would
otherwise surface only at launch (after every stage before it, in a chain). It runs from a scratch
directory, so nothing lands in an output directory. A probe that cannot run or does not finish
cannot establish that the configuration parses, and says so.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from runner import budget, engine_version, runlog
from runner.probes import capture
from runner.settings import seconds

PROBE_TIMEOUT = 300
# What the Nextflow launcher prints when it cannot set an engine up at all (no jars, no Java).
_ENGINE_DOWN = re.compile(r"Unable to initialize nextflow environment|CAPSULE EXCEPTION|"
                          r"Cannot download nextflow|Unable to download")


def probe(*, pipeline: Path, profile: str, configs, overlay: dict[str, str], label: str,
          spelling: str = "run", timeout_seconds: float | None = None) -> list[str]:
    """Why `pipeline`'s configuration does not parse under `profile` and the extra `configs` with
    the engine `overlay` selects (its NXF_VER, else the installed one), or [] when it parses.
    `spelling` names the remedies as `nfclaw run` flags ("run") or as chain spec keys ("chain")."""
    pinned = overlay.get("NXF_VER")
    engine = f"Nextflow {pinned}" if pinned else "the installed Nextflow"
    if shutil.which("nextflow") is None:
        return [f"{label}: configuration could not be verified — nextflow is not on PATH"]
    # `-c` is the launcher's own option for `nextflow config` (`nextflow -c x.config config …`);
    # after the command it is rejected as unknown, unlike `nextflow run … -c x.config`.
    cmd = ["nextflow"]
    for cfg in configs:
        cmd += ["-c", str(cfg)]
    cmd += ["config", str(pipeline), "-profile", profile]
    operation_timeout = seconds("NFCLAW_CONFIG_TIMEOUT", PROBE_TIMEOUT)
    probe_timeout = budget.remaining(min(operation_timeout, timeout_seconds)
                                     if timeout_seconds is not None else operation_timeout)
    with tempfile.TemporaryDirectory(prefix="nfclaw-probe-") as scratch:
        try:
            r = capture(cmd, cwd=scratch, env={**os.environ, **overlay}, timeout=probe_timeout)
        except subprocess.TimeoutExpired:
            return [f"{label}: configuration could not be verified — {engine} did not finish "
                    f"its configuration probe within {probe_timeout:g} seconds"]
        except (OSError, subprocess.SubprocessError) as exc:
            return [f"{label}: configuration could not be verified — {engine}'s "
                    f"configuration probe could not run: {exc}"]
    if r.returncode == 0:
        return []
    report = (runlog.error_excerpt(r.stdout or "")
              + runlog.stderr_excerpt(r.stderr or "")) or [f"exit status {r.returncode}"]
    if _ENGINE_DOWN.search((r.stdout or "") + (r.stderr or "")):
        # The launcher could not set the engine up (a pinned version is downloaded on first use):
        # the run could not start either, but not because of its configuration.
        return [f"{label}: {engine} could not be started — Nextflow downloads a pinned engine on "
                "first use; check this host can:\n" + "\n".join(f"      {line}" for line in report)]
    chain = spelling == "chain"
    # The engine the release was written for is the one it declares (docs/compatibility.md).
    declared = engine_version.minimum_version(
        engine_version.required_spec(pipeline / "nextflow.config"))
    hint = ""
    if declared and declared != pinned:
        hint = (f" — the release declares Nextflow {declared}: try "
                + (f'"nxf_ver": "{declared}"' if chain else f"--nxf-ver {declared}"))
    # From 26.04 strict syntax is the default; the legacy parser stays selectable in place.
    if overlay.get("NXF_SYNTAX_PARSER", "").strip() != "v1":
        hint += (f"{';' if hint else ' —'} on Nextflow 26.04+ the legacy parser may parse it: "
                 + ('"nxf_env": {"NXF_SYNTAX_PARSER": "v1"}' if chain
                    else "--nxf-env NXF_SYNTAX_PARSER=v1"))
    return [f"{label}: {engine} cannot parse its configuration{hint}:\n"
            + "\n".join(f"      {line}" for line in report)]
