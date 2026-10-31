"""Own all processes of one foreground MCP command, including independently grouped probes.

The worker is separate from the threaded MCP server. On Linux it is a subreaper: even a
double-forked helper that exits between inventories is adopted here, never by the host init.
Detached analyses use runner.jobs and do not pass through this worker.
"""
from __future__ import annotations

import ctypes
import os
import signal
import subprocess
import sys
import time

from runner import process_identity


def run(command: list[str], *, parent: int | None = None) -> int:
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    previous = {sig: signal.signal(sig, stop)
                for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}
    owned: dict[int, dict] = {}
    proc = None
    try:
        if sys.platform == "linux":
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
                raise OSError(ctypes.get_errno(), "cannot supervise foreground descendants")
            if parent is not None and libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
                raise OSError(ctypes.get_errno(), "cannot observe foreground parent death")
        process_identity.parents()  # refuse before spawning if cleanup cannot inspect processes
        if stopping or parent is not None and os.getppid() != parent:
            return 143
        proc = subprocess.Popen(command, stdin=subprocess.DEVNULL)
        while True:
            for pid in process_identity.descendants(os.getpid()):
                if identity := process_identity.read(pid):
                    owned[pid] = identity
            if stopping or parent is not None and os.getppid() != parent:
                return 143
            code = proc.poll()
            if code is not None:
                return code if code >= 0 else 128 - code
            time.sleep(0.05)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"nfclaw: foreground supervision unavailable: {exc}", file=sys.stderr, flush=True)
        return 125
    finally:
        if proc is not None and proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        # Stop parents before children so they cannot replenish the tree during cleanup.
        # Refresh adopted children at each pass; remember birth identities across reparenting.
        for _ in range(3):
            try:
                for pid in process_identity.descendants(os.getpid()):
                    if identity := process_identity.read(pid):
                        owned[pid] = identity
            except (OSError, subprocess.SubprocessError):
                pass
            for identity in owned.values():
                process_identity.send(identity, signal.SIGKILL)
            time.sleep(0.02)
        if proc is not None:
            proc.wait(timeout=2)
        if sys.platform == "linux":
            try:
                while os.waitpid(-1, os.WNOHANG)[0]:
                    pass
            except ChildProcessError:
                pass
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[2:], parent=int(sys.argv[1])))
