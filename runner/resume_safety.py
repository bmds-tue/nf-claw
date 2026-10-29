"""Preserve a prior run before a changed directory namespace requires a fresh cache session."""
from __future__ import annotations

import os
import json
import shutil
import stat
import tempfile
import uuid
from contextlib import ExitStack
from pathlib import Path

from runner import execution, outputs
from runner.errors import ErrorCode, NfclawError
from runner.replay_guard import input_files, read_checksums


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
    if state.state == "unreadable":
        # Whether its engine still runs cannot be judged: never move a tree that may be live.
        raise NfclawError(ErrorCode.ENVIRONMENT,
                          f"Cannot preserve the previous run: its run log cannot be read "
                          f"({'; '.join(state.error)}) in {original}.",
                          fix="Make the run log readable, and stop any engine still running "
                              "there, before resuming.")
    if state.nextflow_alive or state.state == "elsewhere":
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
            raise NfclawError(
                ErrorCode.ENVIRONMENT,
                f"Cannot preserve the previous run: a Nextflow session is active or "
                f"locked in {original}.",
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
                              fix="Keep pipeline code and configuration outside "
                                  "the output directory.")

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
            locks.enter_context(execution.stop_on_signals())
            _lock_inactive_sessions(original, locks)
            return _move_previous_run(original, archive)
    except (OSError, RuntimeError) as exc:
        raise NfclawError(ErrorCode.ENVIRONMENT,
                          f"Could not preserve the previous run before recomputation: {exc}. "
                          f"Check {original} and {archive}; Nextflow was not launched.") from exc


def _internal_link_target(path: Path, original: Path) -> Path | None:
    # Keep intermediate publications: a link can traverse the old run before reaching an
    # external task directory. Resolving its final target alone would lose that relationship.
    lexical = Path(os.path.normpath(path.parent / os.readlink(path)))
    if lexical.is_relative_to(original):
        return lexical.relative_to(original)
    # A supplied outdir alias can name the same tree. Resolve prefixes until we enter it,
    # preserving the remainder instead of collapsing nested publication links.
    for prefix in [*reversed(lexical.parents), lexical]:
        resolved = prefix.resolve()
        if resolved.is_relative_to(original):
            return resolved.relative_to(original) / lexical.relative_to(prefix)
    return None


def _move_previous_run(original: Path, archive: Path) -> Path:
    links = []
    for folder, directories, files in os.walk(original, onerror=_raise_walk_error,
                                               followlinks=False):
        for name in [*directories, *files]:
            path = Path(folder) / name
            if path.is_symlink():
                target = _internal_link_target(path, original)
                if target is not None:
                    relative, text = path.relative_to(original), os.readlink(path)
                    future = Path(os.path.normpath((archive / relative).parent / text))
                    if not Path(text).is_absolute() and future == archive / target:
                        continue
                    links.append((relative, target, text))
    fresh = Path(tempfile.mkdtemp(prefix=".nfclaw-resume-", dir=original.parent))
    staged = []
    replaced = []
    staged_record = None
    replaced_record = False
    try:
        logs = original / "provenance/logs"
        if logs.is_dir():
            shutil.copytree(logs, fresh / "provenance/logs")
        record = original / "provenance/outputs.inventory.json"
        if record.is_file():
            original_bytes = record.read_bytes()
            try:
                hashes = read_checksums(original / "provenance/outputs.sha256", relative=True)
                inventory = outputs.read_inventory(record, hashes)
            except ValueError:
                inventory = None
            # Rebase only a complete namespace that agreed with the historical tree. Preserve
            # malformed or already changed evidence without inventing a successful record.
            if inventory is not None and inventory == outputs.snapshot(original)[1]:
                for relative, target, _ in links:
                    if relative.as_posix() in inventory:
                        inventory[relative.as_posix()]["link_target"] = {
                            "scope": "outdir", "path": target.as_posix()}
                rel = record.relative_to(original)
                temp = rel.with_name(f".nfclaw-inventory-{uuid.uuid4().hex}")
                staged_record = (rel, temp, original_bytes, stat.S_IMODE(record.stat().st_mode))
                (original / temp).write_text(json.dumps({"version": 1, "entries": inventory},
                                                       indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
                (original / temp).chmod(staged_record[3])
        # Prepare every replacement while the complete original tree still exists. Permission
        # or copy failures therefore cannot strand historical publications after the rename.
        for relative, target, old_target in links:
            temp_relative = relative.with_name(f".nfclaw-link-{uuid.uuid4().hex}")
            staged.append((relative, temp_relative, old_target))
            (original / temp_relative).symlink_to(archive / target)
        original.rename(archive)
        for relative, temp_relative, old_target in staged:
            replaced.append((relative, old_target))
            os.replace(archive / temp_relative, archive / relative)
        if staged_record is not None:
            rel, temp, _, _ = staged_record
            replaced_record = True
            os.replace(archive / temp, archive / rel)
        fresh.rename(original)
    except BaseException:
        # Inspect our unique archive as well as the flag: cancellation can arrive immediately
        # after a successful rename, before Python records the new ownership state.
        if archive.exists():
            if not fresh.exists() and original.exists():
                original.rename(fresh)
            if replaced_record:
                rel, _, original_bytes, mode = staged_record
                temp = (archive / rel).with_name(f".nfclaw-inventory-{uuid.uuid4().hex}")
                try:
                    temp.write_bytes(original_bytes)
                    temp.chmod(mode)
                    os.replace(temp, archive / rel)
                finally:
                    temp.unlink(missing_ok=True)
            for relative, old_target in reversed(replaced):
                link = archive / relative
                temp = link.with_name(f".nfclaw-link-{uuid.uuid4().hex}")
                try:
                    temp.symlink_to(old_target)
                    os.replace(temp, link)
                finally:
                    temp.unlink(missing_ok=True)
            archive.rename(original)
        raise
    finally:
        tree = archive if archive.exists() else original
        for _, temp_relative, _ in staged:
            (tree / temp_relative).unlink(missing_ok=True)
        if staged_record is not None:
            (tree / staged_record[1]).unlink(missing_ok=True)
        if fresh.exists():
            shutil.rmtree(fresh)
    return archive
