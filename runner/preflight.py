from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

from runner.probes import capture
from runner.settings import seconds
from runner.submodule import SubmoduleStatus, _git_env

# The software an nf-core template engine profile runs every task with, and the commands that
# provide it (Apptainer installs a `singularity` alias; Nextflow's conda engine also drives mamba
# and micromamba).
_ENGINE_COMMANDS = {
    "singularity": ("singularity", "apptainer"),
    "apptainer": ("apptainer", "singularity"),
    "podman": ("podman",),
    "conda": ("conda", "mamba", "micromamba"),
    "mamba": ("mamba", "micromamba"),
    "charliecloud": ("ch-run",),
    "shifter": ("shifter",),
}


def check_environment(*, profile: str, output_dir: Path, submodule: SubmoduleStatus,
                      repo_root: Path, resume: bool, work_dir: Path | None = None,
                      allow_spaces: bool = False, check_only: bool = False,
                      env: Mapping[str, str] | None = None) -> list[str]:
    """`env` is the environment Nextflow runs with: the shell's plus the run's NXF_* overlay."""
    issues: list[str] = []
    for tool in ("git", "nextflow"):
        if shutil.which(tool) is None:
            issues.append(f"{tool} not found on PATH")
    if not _java_found(os.environ if env is None else env):
        issues.append("java not found on PATH, NXF_JAVA_HOME or JAVA_HOME "
                      "(Nextflow needs Java 17+)")
    tokens = {t.strip() for t in profile.split(",")}
    if "docker" in tokens and shutil.which("docker") is None:
        issues.append("profile uses docker but docker not found on PATH")
    for engine, commands in _ENGINE_COMMANDS.items():
        if engine in tokens and not any(shutil.which(c) for c in commands):
            issues.append(f"profile uses {engine} but {'/'.join(commands)} not found on PATH")
    if "docker" in tokens and shutil.which("docker"):
        try:
            ok = capture(["docker", "info"], timeout=10, text=False).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            ok = False
        if not ok:
            issues.append("docker daemon not responding (is Docker running?)")
    if not submodule.complete:
        issues.append(f"pipeline submodule incomplete: missing {list(submodule.missing_files)}")
    try:
        output_dir.resolve().relative_to(repo_root.resolve())
    except ValueError:
        pass                                                  # outside the repo — fine
    else:
        # Inside the repo is OK only if git ignores it (so run outputs never pollute tracked
        # files or trip the drift gate) — this is what lets the documented `--outdir results`
        # work. Probe a child path so a directory-only rule (`results/`) still matches.
        try:
            ignored = capture(
                ["git", "-C", str(repo_root), "check-ignore", "-q", str(output_dir / "_probe")],
                timeout=seconds("NFCLAW_GIT_TIMEOUT", 10), text=False,
                env=_git_env()).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            ignored = False
        if not ignored:
            issues.append("--outdir must be outside the repo or a gitignored "
                          f"path (got {output_dir})")
    if issue := outdir_issue(output_dir, resume=resume, check_only=check_only):
        issues.append(issue)
    if work_dir is not None and (work_issue := _work_dir_issue(work_dir)):
        issues.append(work_issue)
    issues += _space_issues(repo_root=repo_root, output_dir=output_dir,
                            work_dir=work_dir, allow_spaces=allow_spaces)
    return issues


def _java_found(env: Mapping[str, str]) -> bool:
    """Whether the Nextflow launcher finds a Java: NXF_JAVA_HOME's or JAVA_HOME's `bin/java`, else
    `java` on PATH — the places it looks (it also checks the version, so that is left to it). Only
    PATH counted before, which refused a Java the launcher runs from JAVA_HOME."""
    home = env.get("NXF_JAVA_HOME") or env.get("JAVA_HOME")
    return bool(home and os.access(Path(home, "bin", "java"), os.X_OK)) or (
        shutil.which("java") is not None)


def outdir_issue(output_dir: Path, *, resume: bool, check_only: bool) -> str | None:
    """Why `--outdir` cannot take this run, or None.

    Every probe here can meet a directory the caller may not search (`--outdir /root/x` as another
    user), where Path.exists()/is_dir() raise PermissionError instead of answering; that is reported
    as an issue like the others, never a traceback."""
    try:
        is_dir = output_dir.is_dir()
        # An --outdir that exists but is a file can never work — nfclaw creates it and writes the
        # provenance bundle under it.
        if not is_dir and output_dir.exists():
            return f"--outdir exists but is not a directory: {output_dir}"
        if (unwritable := _unwritable(output_dir, "--outdir")) is not None:
            return unwritable
        # A non-empty outdir is a guard for an actual run — it would clobber a previous run's
        # results. `--check` only validates params and prints the command without launching, so
        # this guard must not block it: a dry run against an existing results directory
        # is legitimate.
        if is_dir and not resume and not check_only and any(output_dir.iterdir()):
            return (f"--outdir is not empty: {output_dir} (pass --resume to continue that run, "
                    "or use a fresh --outdir)")
    except OSError as exc:
        return f"--outdir cannot be reached: {exc.strerror or exc} ({exc.filename or output_dir})"
    return None


def _unwritable(path: Path, label: str) -> str | None:
    """Why the run could not write the directory `path` (or create it), or None.

    nfclaw creates --outdir and writes its provenance bundle there before Nextflow starts, so a path
    under a directory the caller cannot write (`--outdir /data/results` with a root-owned /data)
    failed with a raw PermissionError. Judged on the directory itself, or on its nearest existing
    ancestor when it does not exist yet — the one `mkdir` would have to write into. May raise
    OSError for a path whose ancestors cannot be searched; callers report that."""
    target = path
    while not target.exists() and target != target.parent:
        target = target.parent
    if target != path and not target.is_dir():
        return f"{label} cannot be created: {target} is not a directory"
    if not os.access(target, os.W_OK | os.X_OK):
        return (f"{label} is not writable: {path}" if target == path else
                f"{label} cannot be created: {target} is not writable ({path})")
    return None


def _work_dir_issue(work_dir: Path) -> str | None:
    """Why Nextflow could not use its work directory, or None. The default, `<repo>/work`, belongs
    to whoever ran first, so on a clone shared by several users the others cannot write it."""
    fix = "set a writable one with --nxf-env NXF_WORK=/a/writable/dir"
    try:
        if work_dir.exists() and not work_dir.is_dir():
            return f"the Nextflow work directory is not a directory: {work_dir} — {fix}"
        issue = _unwritable(work_dir, "the Nextflow work directory")
    except OSError as exc:
        issue = (f"the Nextflow work directory cannot be reached: {exc.strerror or exc} "
                 f"({exc.filename or work_dir})")
    return f"{issue} — {fix}" if issue else None


def _space_issues(*, repo_root: Path, output_dir: Path, work_dir: Path | None,
                  allow_spaces: bool) -> list[str]:
    """Fail-fast, deterministic: a space in the repo tree, the Nextflow work directory or the
    output path breaks many bioinformatics tools (they build shell commands without quoting
    their work paths) and Docker on macOS outright. A path either contains a space or it does
    not — there is no heuristic here. `--allow-spaces` is the explicit opt-out."""
    issues: list[str] = []
    for label, path in (("the repo path", repo_root),
                        ("the Nextflow work directory", work_dir),
                        ("--outdir", output_dir)):
        if path is None:
            continue
        if "\n" in str(path) or "\r" in str(path):
            issues.append(f"{label} contains a line break: {path!s} — Nextflow can put it into "
                          "generated shell commands; use a safely named parent path")
        if allow_spaces or " " not in str(path):
            continue
        fix = ("set the work directory off it with --nxf-env NXF_WORK=/a/space-free/dir"
               if "work" in label else "use a space-free path")
        issues.append(f"{label} contains a space: {path} — bioinformatics tools and Nextflow's "
                      f"work directory mishandle spaces (Docker on macOS fails outright). "
                      f"{fix}, or pass --allow-spaces to run anyway.")
    return issues
