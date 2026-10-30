"""Replace a file whole: a reader sees the old bytes or the new ones, never half a write."""
from __future__ import annotations

import os
from pathlib import Path


def write_bytes(path: Path, content: bytes, *, mode: int | None = None) -> None:
    """Write `content` to a new file beside `path`, then rename it over `path`.

    Without `mode` the file gets the permissions any newly created file gets (0o666 less the
    umask), like the rest of a run's directory: `tempfile` creates its files 0o600, which left
    provenance bundles unreadable to the group a run's results are shared with. A `mode` is set
    before the rename, and a private one (0o600) never has a readable moment.
    """
    while True:
        temporary = path.with_name(f".{path.name}.{os.urandom(4).hex()}.tmp")
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                         0o666 if mode is None else 0o600)
            break
        except FileExistsError:
            continue
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def write_text(path: Path, content: str, *, mode: int | None = None) -> None:
    write_bytes(path, content.encode("utf-8"), mode=mode)
