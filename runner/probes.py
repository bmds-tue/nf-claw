"""Bounded metadata probes, including cleanup of bootstrap subprocesses."""
from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path

from runner import budget, replay_guard


def capture(command: list[str], *, timeout: float,
            env: dict[str, str] | None = None,
            cwd: str | Path | None = None,
            text: bool = True) -> subprocess.CompletedProcess:
    """Capture a probe and stop its process group on timeout or interruption.

    A Nextflow launcher can spawn curl or Java even for ``-version``. The standard
    subprocess.run timeout kills only its leader, leaving those children behind.
    These metadata probes require no pipeline shutdown grace period.
    """
    from runner import execution  # here: execution's own imports lead back to this module
    timeout = budget.remaining(timeout)
    grouped = hasattr(os, "killpg")
    proc = None
    try:
        try:
            # A stop that arrives while Popen is still returning waits until the child is
            # assigned: raised inside Popen, it lost the group, and the probe's helpers ran on.
            with execution._defer_stop_signals():
                proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=text, env=env, cwd=cwd, start_new_session=grouped)
            stdout, stderr = proc.communicate(timeout=budget.remaining(timeout))
            budget.check()
        except BaseException as exc:
            if proc is None:
                raise
            try:
                if grouped:
                    replay_guard.signal_process_group(proc.pid, signal.SIGKILL)
                else:
                    proc.kill()
            except ProcessLookupError:
                pass
            try:
                proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                # An escaped descendant must not make pipe drainage wait forever.
                proc.stdout.close()
                proc.stderr.close()
                proc.wait(timeout=2)
            if isinstance(exc, subprocess.TimeoutExpired):
                budget.check()
            raise
        return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)
    finally:
        if proc is not None:
            proc.stdout.close()
            proc.stderr.close()
