#!/usr/bin/env python3
"""Run a command with a deadline: the acceptance gate's stand-in for GNU `timeout` on a host that
has neither `timeout` nor `gtimeout` (macOS without coreutils).

    run_with_timeout.py [--kill-after GRACE] SECONDS COMMAND [ARG ...]

As with `timeout --kill-after=GRACE SECONDS COMMAND`, the command runs in its own process group,
which receives SIGTERM at the deadline and SIGKILL GRACE seconds later if the command is still
running; a duration of 0 disables that deadline. SIGINT, SIGTERM and SIGHUP sent to this process are
passed on to the group and also start the GRACE countdown. Unlike GNU `timeout`, this process stays
in the caller's process group, so a terminal's Ctrl-C reaches it and, through it, the command.

Exit status, as GNU `timeout` reports it: 124 when the deadline stopped the command (137 when it had
to be killed), otherwise the command's own status (128+N when signal N ended it); 125 for a usage
error, 126 when the command cannot be run and 127 when it is not found.
"""
from __future__ import annotations

import argparse
import math
import os
import signal
import subprocess
import sys
import time

TIMED_OUT = 124
_FORWARDED = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
_POLL = 0.1                    # how often deadlines and received signals are acted on, in seconds


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise SystemExit(125)


def _seconds(text: str) -> float:
    value = float(text)
    if not math.isfinite(value) or value < 0:
        raise ValueError(text)
    return value


def _signal_group(proc: subprocess.Popen, signum: int) -> None:
    # Only while the leader is unreaped: its pid, and so the group id, cannot have been reused.
    if proc.returncode is None:
        try:
            os.killpg(proc.pid, signum)
        except (ProcessLookupError, PermissionError):
            pass


def run(seconds: float, command: list[str], kill_after: float | None = None) -> int:
    received: list[int] = []
    previous = {signum: signal.signal(signum, lambda signum, _frame: received.append(signum))
                for signum in _FORWARDED}
    try:
        if received:                                  # stopped before the command started
            return 128 + received[0]
        try:
            proc = subprocess.Popen(command, process_group=0)
        except FileNotFoundError as exc:
            print(f"run_with_timeout: {exc}", file=sys.stderr)
            return 127
        except OSError as exc:
            print(f"run_with_timeout: {exc}", file=sys.stderr)
            return 126
        deadline = time.monotonic() + seconds if seconds > 0 else math.inf
        kill_at = math.inf
        timed_out = False
        while True:
            try:
                proc.wait(timeout=_POLL)
            except subprocess.TimeoutExpired:
                pass
            if proc.returncode is not None:
                break
            now = time.monotonic()
            stop = []
            while received:
                stop.append(received.pop(0))
            if not timed_out and now >= deadline:
                timed_out = True
                stop.append(signal.SIGTERM)
            for signum in stop:
                _signal_group(proc, signum)
            if stop and kill_after and kill_at == math.inf:
                kill_at = now + kill_after
            if now >= kill_at:
                _signal_group(proc, signal.SIGKILL)
                kill_at = math.inf
                kill_after = None                     # SIGKILL is sent once
    finally:
        for signum, handler in previous.items():
            if handler is not None:                   # None: not installed from Python
                signal.signal(signum, handler)
    code = proc.returncode
    if code < 0:
        if timed_out and code == -signal.SIGKILL:
            return 128 + signal.SIGKILL
        code = 128 - code
    return TIMED_OUT if timed_out else code


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="run_with_timeout.py", description=__doc__.split("\n\n")[0],
                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kill-after", type=_seconds, metavar="GRACE",
                        help="send SIGKILL this many seconds after SIGTERM if the command "
                             "still runs")
    parser.add_argument("seconds", type=_seconds, metavar="SECONDS")
    parser.add_argument("command", nargs=argparse.REMAINDER, metavar="COMMAND")
    args = parser.parse_args(argv)
    if not args.command:
        parser.error("a command to run is required")
    return run(args.seconds, args.command, args.kill_after)


if __name__ == "__main__":
    raise SystemExit(main())
