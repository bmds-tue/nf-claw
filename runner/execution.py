from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runner import budget, runlog, settings
from runner.errors import ErrorCode, NfclawError


class Terminated(BaseException):
    """nfclaw was told to stop by a signal — `kill <pid>` (SIGTERM), or the terminal it ran in
    closing (SIGHUP). A BaseException like KeyboardInterrupt, so it takes the same teardown path and
    is never mistaken for a failure of the run itself."""

    def __init__(self, signum: int):
        super().__init__(signum)
        self.signum = signum

    @property
    def name(self) -> str:
        return signal.Signals(self.signum).name

    def __str__(self) -> str:
        return self.name


_STOP_SIGNALS = tuple(getattr(signal, n) for n in ("SIGTERM", "SIGHUP") if hasattr(signal, n))


def _raise_terminated(signum, _frame) -> None:
    raise Terminated(signum)


@contextmanager
def stop_on_signals() -> Iterator[None]:
    """While active, SIGTERM and SIGHUP raise `Terminated` in the main thread, so a stopped run
    tears Nextflow's process group down and records its outcome. Python's default for both is to die
    on the spot: Nextflow, in its own session, went on running orphaned, and run.log never got its
    last line. A signal the caller ignores stays ignored (`nohup` ignores SIGHUP so a run survives
    its terminal), and the previous handlers come back on exit. Outside the main thread it
    changes nothing."""
    previous: dict[int, Any] = {}
    if threading.current_thread() is threading.main_thread():
        for sig in _STOP_SIGNALS:
            if signal.getsignal(sig) is not signal.SIG_IGN:
                previous[sig] = signal.signal(sig, _raise_terminated)
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler if handler is not None else signal.SIG_DFL)


def stop_outcome(exc: BaseException) -> str:
    """How a run that was stopped ended, for the run log's last line."""
    return f"terminated by {exc.name}" if isinstance(exc, Terminated) else "interrupted"


@dataclass(frozen=True)
class ExecResult:
    exit_code: int
    stdout_path: Path
    stderr_path: Path


def _tee(src, term_stream, log_file, run_log: runlog.RunLog, stream: str) -> None:
    """Forward a child stream to the terminal, its own log file and the run log at once, live.

    Reads whatever is already available (`read1`) instead of waiting for a full buffer or a whole
    line, so a long pipeline's progress reaches the terminal as Nextflow produces it rather than
    only when the run ends. Bytes are copied verbatim to preserve the child's own formatting
    (carriage returns, colour). The terminal and the files are written independently: a closed or
    unusable terminal never costs the run its captured logs, which the provenance bundle and error
    messages point at.
    """
    term = getattr(term_stream, "buffer", None)          # write bytes; None if not a real byte sink
    try:
        for chunk in iter(lambda: src.read1(65536), b""):
            try:
                log_file.write(chunk)
                log_file.flush()
            except (OSError, ValueError):
                pass
            run_log.write(chunk, stream)
            if term is not None:
                try:
                    term.write(chunk)
                    term.flush()
                except (OSError, ValueError):
                    term = None                          # stop writing to a broken terminal
    finally:
        try:
            src.close()
        except OSError:
            pass


def _join(threads: list[threading.Thread]) -> None:
    for t in threads:
        t.join(timeout=5)


def run(command: list[str], *, cwd: Path, logs_dir: Path,
        timeout_seconds: float | None, env_extra: dict[str, str] | None = None,
        nextflow_log: Path | None = None, notes: list[str] | tuple[str, ...] = (),
        run_log: runlog.RunLog | None = None) -> ExecResult:
    """Run `command` from `cwd`, streaming its output live and recording it under `logs_dir`.

    `stdout.txt`/`stderr.txt` keep the child's two streams; `run.log` keeps the whole launch in
    order (see `runner.runlog`). All three are appended to, so a relaunch (`--resume`) never
    overwrites the attempt that failed. A caller that does more work after the launch (`nfclaw run`
    writes the provenance bundle) passes its own open `run_log` and finishes it itself; otherwise
    one is opened here — with `nextflow_log` and the `notes` advisories in its header — and finished
    on return."""
    own = run_log is None
    if run_log is None:
        run_log = runlog.RunLog.open(logs_dir, command=command, launch_dir=cwd,
                                     nextflow_log=nextflow_log, notes=notes, env=env_extra)
    try:
        return _run(command, cwd=cwd, logs_dir=logs_dir, timeout_seconds=timeout_seconds,
                    env_extra=env_extra, run_log=run_log)
    finally:
        if own:
            run_log.finish()


def _run(command: list[str], *, cwd: Path, logs_dir: Path, timeout_seconds: float | None,
         env_extra: dict[str, str] | None, run_log: runlog.RunLog) -> ExecResult:
    grace = settings.seconds("NFCLAW_SHUTDOWN_GRACE", _GRACE_SECONDS)
    run_log.shutdown_grace_seconds = grace
    logs_dir.mkdir(parents=True, exist_ok=True)
    out_p, err_p = logs_dir / "stdout.txt", logs_dir / "stderr.txt"
    # start_new_session puts the child in its own process group, so nfclaw owns its shutdown: the
    # terminal's Ctrl-C reaches nfclaw as a KeyboardInterrupt (not the child), and nfclaw then tears
    # down the whole group below. Without this the child kept running in the background
    # after Ctrl-C.
    popen_kwargs: dict[str, Any] = {} if sys.platform == "win32" else {"start_new_session": True}
    die_with_nfclaw = _die_with_parent()
    if die_with_nfclaw is not None:
        popen_kwargs["preexec_fn"] = die_with_nfclaw
    # Inherit the full environment, then overlay the caller's NXF_* overrides (engine version,
    # JVM args, …). Inheriting keeps shell-set vars (proxies, JAVA_HOME) working as before.
    env = {**os.environ, **env_extra} if env_extra else None
    with out_p.open("ab") as out_fh, err_p.open("ab") as err_fh:
        budget.check()
        try:
            # Pipe the child's streams so nfclaw can tee them; without a pipe the output would go
            # straight to files (the terminal stays mute) or straight to the terminal (nothing is
            # captured). Teeing gives both.
            proc = subprocess.Popen(command, cwd=str(cwd), stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, env=env, **popen_kwargs)
        except OSError as exc:
            err = NfclawError(ErrorCode.EXECUTION_FAILED, f"Could not launch process: {exc}",
                              fix="Ensure `nextflow` is installed and on PATH.",
                              details={"run_log": str(run_log.path)})
            run_log.fail("could not launch", str(err))
            raise err from exc
        run_log.launched(proc.pid)
        # One drainer per stream: both pipes must be read concurrently, or a child that fills one
        # while nfclaw is blocked reading the other would deadlock. Daemon threads so a wedged
        # reader can never keep the process alive on its own.
        readers = [
            threading.Thread(target=_tee, args=(proc.stdout, sys.stdout, out_fh, run_log, "out"),
                             daemon=True),
            threading.Thread(target=_tee, args=(proc.stderr, sys.stderr, err_fh, run_log, "err"),
                             daemon=True),
        ]
        for t in readers:
            t.start()
        try:
            code = proc.wait(timeout=budget.remaining(timeout_seconds))
            budget.check()
        except subprocess.TimeoutExpired as exc:
            _terminate(proc, grace=grace)
            _join(readers)
            elapsed_budget = timeout_seconds
            try:
                budget.check()
            except NfclawError as expired:
                elapsed_budget = expired.details["timeout_seconds"]
            err = NfclawError(ErrorCode.EXECUTION_FAILED, "Execution timed out.",
                              fix="Increase --timeout or use a smaller dataset; the run log shows "
                                  "how far the run got.",
                              details={"timeout_seconds": elapsed_budget,
                                       **_log_details(run_log)})
            run_log.fail(f"timed out after {elapsed_budget:g} s", str(err))
            raise err from exc
        except BaseException as exc:
            # Ctrl-C (KeyboardInterrupt), `kill` (Terminated) or any other interruption of the wait:
            # tear down the child group so Nextflow — and every task process, container or JVM it
            # launched — is stopped, never left running in the background. Then re-raise so the
            # interrupt is not swallowed. The outcome is recorded first: a second signal during the
            # teardown's grace period must not cost the log its last line.
            outcome = (f"timed out after {exc.details['timeout_seconds']:g} s"
                       if isinstance(exc, NfclawError) and "timeout_seconds" in exc.details
                       else stop_outcome(exc))
            run_log.fail(outcome)
            _terminate(proc, grace=grace)
            _join(readers)
            raise
        _join(readers)
    if code != 0:
        err = _failure(code, run_log, env if env is not None else os.environ)
        run_log.fail(f"failed (exit status {code})", str(err))
        raise err
    run_log.outcome = "success"
    return ExecResult(code, out_p, err_p)


def _die_with_parent():
    """On Linux, a pre-exec hook asking the kernel to send the child SIGTERM when nfclaw dies.

    nfclaw stops Nextflow itself on Ctrl-C, SIGTERM and SIGHUP; SIGKILL (`kill -9`, the out-of-
    memory killer) cannot be caught, and Nextflow — in its own session — would run on orphaned.
    PR_SET_PDEATHSIG survives the launcher's `exec` of the JVM, so Nextflow gets its normal SIGTERM
    shutdown and stops its tasks. None elsewhere, or if libc cannot be loaded."""
    if not sys.platform.startswith("linux"):
        return None
    try:
        import ctypes
        import ctypes.util
        libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)
    except (OSError, AttributeError):
        return None
    parent = os.getpid()

    def preexec() -> None:
        libc.prctl(1, signal.SIGTERM, 0, 0, 0)          # PR_SET_PDEATHSIG
        if os.getppid() != parent:                      # nfclaw died before the hook took effect
            os._exit(1)

    return preexec


def _log_details(run_log: runlog.RunLog) -> dict[str, str]:
    """The files that hold the rest of the story, as absolute paths — only ones that exist."""
    details = {"run_log": str(run_log.path)}
    if run_log.nextflow_log is not None and run_log.nextflow_log.is_file():
        details["nextflow_log"] = str(run_log.nextflow_log)
    return details


def _failure(code: int, run_log: runlog.RunLog, env: Mapping[str, str]) -> NfclawError:
    """The error for a launch that exited non-zero: what Nextflow itself reported, quoted from this
    launch's console, plus where the full logs are. Nextflow prints its error reports on stdout and
    some details on stderr (nf-schema's list of invalid values), and refers to its log relative to a
    directory the reader is not in. `env` is the environment Nextflow ran with."""
    on_stderr = runlog.stderr_excerpt(run_log.console_tail("err"))
    # Without an `ERROR ~` report on stdout its tail is only worth quoting when stderr is silent too
    # (an `error "…"` in a workflow prints just its message there); otherwise it is the banner.
    on_stdout = runlog.error_excerpt(run_log.console_tail("out"),
                                     tail_if_no_report=not on_stderr)
    details: dict = {"exit_code": code, **_log_details(run_log)}
    task = runlog.failing_task_dir(on_stdout + on_stderr)
    if task is not None and task.is_dir():
        details["failing_task"] = str(task / ".command.err")
    message = f"Nextflow execution failed (exit status {code})."
    if on_stdout:
        message += " Nextflow reported:\n" + _quote(on_stdout)
    if on_stderr:
        message += ("\n  and on stderr:\n" if on_stdout else " Nextflow reported on stderr:\n") + \
            _quote(on_stderr)
    causes = (runlog.nextflow_log_causes(run_log.nextflow_log)
              if "nextflow_log" in details and run_log.nextflow_log is not None else [])
    if causes:
        message += "\n  The underlying cause, from the Nextflow log:\n" + _quote(causes)
    task_hint = (" The failing task's complete output is in .command.err and .command.log beside "
                 "`failing_task`." if "failing_task" in details else "")
    # Before Nextflow 26.10.0 the local executor reads the exit status of a task it has just killed
    # at its time limit without waiting for it to exit; the IllegalThreadStateException aborts the
    # whole session ("process hasn't exited") instead of letting the task be retried.
    time_limit_hint = ("`process hasn't exited` means a task ran past its time limit, and Nextflow "
                       "before 26.10.0 then aborts the whole run instead of retrying that task "
                       "(nextflow-io/nextflow#7569). Pulling the task's container image counts "
                       "toward the limit, so --resume often completes it; if it times out again, "
                       "raise that process's `time` with --config or use Nextflow "
                       "26.10.0 or later. "
                       if any(_TIME_LIMIT_ABORT in line for line in on_stdout + on_stderr + causes)
                       else "")
    # Nextflow's own JVM (its log's exception chain, not a task's output) could not reach a host,
    # and nothing told it to prefer IPv6: on a host without an IPv4 route (IPv6-only, NAT64) the
    # JVM still tries IPv4 first, so remote configs, test data and plugins all fail this way.
    ipv6_hint = ("`Network is unreachable` in Nextflow's own log: on a host without IPv4 "
                 "connectivity (IPv6-only or NAT64) its JVM still tries IPv4 first; add --nxf-env "
                 f"NXF_JVM_ARGS={_PREFER_IPV6}. "
                 if any(_NETWORK_UNREACHABLE in line for line in causes)
                 and not any(_PREFER_IPV6 in env.get(name, "") for name in _JVM_OPTION_VARS)
                 else "")
    return NfclawError(
        ErrorCode.EXECUTION_FAILED, message,
        fix=(f"{time_limit_hint}{ipv6_hint}Fix the cause Nextflow reports, then re-run the same "
             f"command with "
             f"--resume.{task_hint} The whole launch is in `run_log`. Common causes and fixes: "
             f"{runlog.known_issues_path()}."),
        details=details)


_TIME_LIMIT_ABORT = "process hasn't exited"
_NETWORK_UNREACHABLE = "Network is unreachable"
_PREFER_IPV6 = "-Djava.net.preferIPv6Addresses=true"
# Where the Nextflow launcher and the JVM read JVM options from.
_JVM_OPTION_VARS = ("NXF_JVM_ARGS", "NXF_OPTS", "JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS")


def _quote(lines: list[str]) -> str:
    return "\n".join(f"    {line}" if line else "" for line in lines)


_GRACE_SECONDS = 10


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except OSError:                       # members exist that we may not signal: still not gone
        return True
    return True


def _terminate(proc: subprocess.Popen, grace: float = _GRACE_SECONDS) -> None:
    """Stop the child and everything it launched.

    Signals the whole process group, because killing just the child would orphan the task processes
    it spawned: SIGTERM first, so Nextflow runs its JVM shutdown hooks and cleans up its own tasks,
    then SIGKILL for whatever is still running once the grace period is over. The group is waited
    on, not just its leader — Nextflow exiting does not mean its tasks did, and a task that ignores
    or is still handling SIGTERM would otherwise be left running in the background.
    """
    if not hasattr(os, "killpg"):                     # Windows: no process groups to signal
        proc.kill()
        proc.wait()
        return
    pgid = proc.pid                                   # start_new_session: the child leads its group
    deadline = time.monotonic() + grace
    try:
        os.killpg(pgid, signal.SIGTERM)
    except OSError:
        pass
    try:
        try:
            proc.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            pass
        while _group_alive(pgid) and time.monotonic() < deadline:
            time.sleep(0.1)
    finally:
        # Also on a second Ctrl-C during the grace period: that asks to stop now, not to leave the
        # group running — skip the rest of the wait, but still kill it.
        try:
            os.killpg(pgid, signal.SIGKILL)
        except OSError:
            pass                                      # the group is already gone
        proc.wait()
