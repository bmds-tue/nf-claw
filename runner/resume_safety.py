"""Preserve a prior run before a changed directory namespace requires a fresh cache session."""
from __future__ import annotations

import os
import shutil
import stat
import uuid
from contextlib import ExitStack
from pathlib import Path

from runner.errors import ErrorCode, NfclawError
from runner.replay_guard import input_files


def _raise_walk_error(error):
    raise error


def _lock_inactive_sessions(original: Path, locks: ExitStack) -> None:
    """Retain POSIX record locks used by Nextflow's local LevelDB cache until the move ends.

    A surviving engine can outlive its nfclaw parent. Its database lock must still prevent a new
    cache session from bypassing the normal engine exclusion and moving a live output tree.
    """
    try:
        import fcntl
    except ImportError:
        raise NfclawError(ErrorCode.ENVIRONMENT,
                          "Preserving a previous run requires POSIX cache-session locking.",
                          fix="Use a fresh output directory on this platform.") from None
    from runner import runlog
    state = runlog.read_state(original / "provenance/logs/run.log")
    if state and (state.nextflow_alive or state.state == "elsewhere"):
        raise NfclawError(ErrorCode.ENVIRONMENT,
                          f"Cannot preserve the previous run: its Nextflow process is active "
                          f"or its remote outcome is unknown in {original}.",
                          fix="Stop the existing engine and its tasks before resuming.")
    cache = original / ".nextflow/cache"
    if not cache.exists() and not cache.is_symlink():
        return
    for path in input_files([cache]):
        if path.name != "LOCK":
            continue
        fd = os.open(path, os.O_RDWR | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
        locks.callback(os.close, fd)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(f"Nextflow cache lock is not a regular file: {path}")
        try:
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise NfclawError(ErrorCode.ENVIRONMENT,
                              f"Cannot preserve the previous run: a Nextflow session is active "
                              f"or locked in {original}.",
                              fix="Stop the existing engine and its tasks before resuming.") from None


def archive_previous_run(outdir: Path, inventory: dict[str, dict[str, str]],
                         configurations: list[Path]) -> Path:
    original = outdir.resolve()
    # Moving a run must not move any dependency that the new command still addresses. Likewise,
    # a run nested inside its own directory input would change that input while being archived.
    for name, entry in inventory.items():
        dependency = Path(entry.get("resolved_path", name))
        if dependency.is_relative_to(original) or (
                entry["type"] == "directory" and original.is_relative_to(dependency)):
            raise NfclawError(ErrorCode.ENVIRONMENT,
                              f"Cannot preserve the previous run: input {name} overlaps {outdir}.",
                              fix="Use a separate output directory and keep input data outside it.")
    for config in configurations:
        if config.resolve().is_relative_to(original):
            raise NfclawError(ErrorCode.ENVIRONMENT,
                              f"Cannot preserve the previous run: pipeline/configuration {config} "
                              f"is inside {outdir}.",
                              fix="Keep pipeline code and configuration outside the output directory.")

    suffix = f".previous-{uuid.uuid4().hex}"
    prefix = original.name
    try:
        maximum = os.pathconf(original.parent, "PC_NAME_MAX")
        if 0 < maximum < len(os.fsencode(suffix)):
            raise NfclawError(ErrorCode.ENVIRONMENT,
                              f"The filesystem filename limit ({maximum} bytes) is too small "
                              "to preserve a previous run with a unique archive name.")
        while maximum > 0 and len(os.fsencode(prefix + suffix)) > maximum:
            prefix = prefix[:-1]
        archive = original.with_name(prefix + suffix)
    except OSError as exc:
        raise NfclawError(ErrorCode.ENVIRONMENT,
                          f"Cannot determine an archive filename for {original}: {exc}") from exc
    try:
        with ExitStack() as locks:
            _lock_inactive_sessions(original, locks)
            return _move_previous_run(original, archive)
    except OSError as exc:
        raise NfclawError(ErrorCode.ENVIRONMENT,
                          f"Could not preserve the previous run before recomputation: {exc}. "
                          f"Check {original} and {archive}; Nextflow was not launched.") from exc


def _move_previous_run(original: Path, archive: Path) -> Path:
    # Relative links retain their meaning when the entire tree moves to a sibling. Absolute
    # publications pointing into an internal work directory need their targets rebased.
    links = []
    for folder, directories, files in os.walk(original, onerror=_raise_walk_error,
                                               followlinks=False):
        for name in [*directories, *files]:
            path = Path(folder) / name
            if path.is_symlink():
                target = Path(os.readlink(path))
                if target.is_absolute() and target.is_relative_to(original):
                    links.append((path.relative_to(original), target.relative_to(original)))
    original.rename(archive)
    for relative, target in links:
        link = archive / relative
        temp = link.with_name(f".nfclaw-link-{uuid.uuid4().hex}")
        try:
            temp.symlink_to(archive / target)
            os.replace(temp, link)
        finally:
            temp.unlink(missing_ok=True)
    original.mkdir()
    logs = archive / "provenance/logs"
    if logs.is_dir():
        shutil.copytree(logs, original / "provenance/logs")
    return archive
