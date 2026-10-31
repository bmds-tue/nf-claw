"""Process birth identities for recovery; a persisted PID alone never authorizes a signal."""
from __future__ import annotations

import ctypes
import os
import signal
import subprocess
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _boot() -> str | None:
    try:
        if sys.platform == "linux":
            boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            return f"{boot}:{Path('/proc/self/ns/pid').stat().st_ino}"
        if sys.platform == "darwin":
            result = subprocess.run(["/usr/sbin/sysctl", "-n", "kern.boottime"],
                                    capture_output=True, text=True, timeout=2, check=True)
            return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        pass
    return None


class _BsdInfo(ctypes.Structure):
    _fields_ = ([(name, ctypes.c_uint32) for name in (
        "flags", "status", "xstatus", "pid", "ppid", "uid", "gid", "ruid", "rgid",
        "svuid", "svgid", "rfu")]
        + [("comm", ctypes.c_char * 16), ("name", ctypes.c_char * 32)]
        + [(name, ctypes.c_uint32) for name in (
            "nfiles", "pgrp", "pjobc", "e_tdev", "e_tpgid", "nice")]
        + [("start_sec", ctypes.c_uint64), ("start_usec", ctypes.c_uint64)])


def read(pid: int) -> dict | None:
    """Birth time, boot/namespace and owner, or None if absent, zombie or uninspectable.

    Darwin's libproc supplies microseconds; `ps lstart` rounds to a second and is unsafe
    for recovery on a host that reuses PIDs rapidly.
    """
    if type(pid) is not int or pid <= 0 or pid > 2**31 - 1 or not (boot := _boot()):
        return None
    try:
        if sys.platform == "linux":
            path = Path(f"/proc/{pid}")
            stat = (path / "stat").read_text()
            fields = stat[stat.rindex(")") + 2:].split()
            if fields[0] in ("Z", "X"):
                return None
            start, uid = fields[19], path.stat().st_uid
        elif sys.platform == "darwin":
            info = _BsdInfo()
            lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
            size = lib.proc_pidinfo(pid, 3, 0, ctypes.byref(info), ctypes.sizeof(info))
            if size != ctypes.sizeof(info) or info.pid != pid or info.status == 5:
                return None
            start, uid = f"{info.start_sec}:{info.start_usec}", info.uid
        else:
            return None
    except (OSError, ValueError, IndexError):
        return None
    return {"pid": pid, "boot": boot, "start": start, "uid": uid}


def matches(record: dict | None) -> bool:
    return isinstance(record, dict) and read(record.get("pid")) == record


def send(record: dict | None, signum: int = signal.SIGTERM) -> bool:
    """Validate birth identity immediately before signalling. Linux pins the process with pidfd."""
    if not matches(record):
        return False
    pid = record["pid"]
    fd = None
    try:
        if hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal"):
            fd = os.pidfd_open(pid)
            if not matches(record):
                return False
            signal.pidfd_send_signal(fd, signum)
        else:
            os.kill(pid, signum)
        return True
    except (ProcessLookupError, PermissionError):
        return False
    finally:
        if fd is not None:
            os.close(fd)


def parents() -> dict[int, int]:
    """Readable process ancestry. Failure is explicit, never an empty successful inventory."""
    if sys.platform == "linux":
        result = {}
        for path in Path("/proc").iterdir():
            if not path.name.isdigit():
                continue
            try:
                line = (path / "stat").read_text()
                result[int(path.name)] = int(line[line.rindex(")") + 2:].split()[1])
            except (OSError, ValueError, IndexError):
                continue  # processes may end during enumeration
        if os.getpid() not in result:
            raise OSError("process ancestry is not readable")
        return result
    result = subprocess.run(["/bin/ps", "-A", "-o", "pid=", "-o", "ppid="],
                            capture_output=True, text=True, timeout=2, check=True)
    rows = {int(pid): int(parent) for pid, parent in
            (line.split() for line in result.stdout.splitlines())}
    if os.getpid() not in rows:
        raise OSError("process ancestry is not readable")
    return rows


def descendants(root: int) -> set[int]:
    rows = parents()
    found = {root}
    while more := {pid for pid, parent in rows.items() if parent in found} - found:
        found.update(more)
    return found - {root}
