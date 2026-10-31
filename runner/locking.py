"""Keep a run's parameters, logs and provenance under one writer."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

from runner.errors import ErrorCode, NfclawError

try:
    import fcntl
except ImportError:
    fcntl = None


def posix_required(what: str) -> NfclawError:
    """The refusal for a run or chain where POSIX file locks are not available (native Windows):
    Nextflow itself runs only on POSIX systems, and an unlocked writer would race another one."""
    return NfclawError(
        ErrorCode.ENVIRONMENT,
        f"{what} needs a POSIX system with file locking (Linux or macOS); this Python has no "
        "`fcntl`.",
        fix="On Windows, install and run nfclaw inside WSL 2, where Nextflow and its container "
            "engines run too.")


@contextmanager
def exclusive(lock: Path, *, what: str, mode: int, busy: NfclawError, unavailable: str,
              private_directory: bool = False):
    """Hold an flock on `lock` for the block, or raise `busy` at once if another process holds it.

    Where there is no flock (native Windows), `what` is refused before anything is created. The
    directory holding `lock` is created first (0o700 when `private_directory`). Anything the
    filesystem refuses raises an environment error that starts with `unavailable`.
    """
    if fcntl is None:
        raise posix_required(what)
    fd = None
    try:
        lock.parent.mkdir(parents=True, exist_ok=True, mode=0o700 if private_directory else 0o777)
        if private_directory:
            lock.parent.chmod(0o700)
        fd = os.open(lock, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), mode)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            fd = None
            raise busy from None
    except OSError as exc:
        if fd is not None:
            os.close(fd)
            fd = None
        raise NfclawError(
            ErrorCode.ENVIRONMENT, f"{unavailable}: {exc.strerror or exc}",
            fix="Use an output directory whose parent you can write to.") from exc
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)


@contextmanager
def output_writer(outdir: Path, *, check_only: bool = False):
    """Acquire only after dependency separation is checked; keep it through final recording."""
    if check_only:
        yield
        return
    outdir = outdir.expanduser().resolve()
    # A persistent sibling file leaves a fresh output directory untouched. Never unlink it:
    # a third process could otherwise lock a new inode while a second still holds the old one.
    with exclusive(
            outdir.parent / f".{outdir.name}.nfclaw.lock", what="nfclaw run", mode=0o600,
            busy=NfclawError(
                ErrorCode.ENVIRONMENT, f"another nfclaw run is active in {outdir}",
                fix="Wait for the active run to finish or stop it before resuming.",
                details={"active_run": True}),
            unavailable=f"--outdir could not be created or locked: {outdir}"):
        yield
