from __future__ import annotations

import errno
import os
import re
import shutil
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

from runner import budget, replay_guard, runlog, settings
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
        if t.ident is not None:  # Setup can fail before either reader starts.
            t.join(timeout=5)


@contextmanager
def _defer_stop_signals():
    """Retain a stop until Popen has returned its child handle to the cleanup owner.

    Raising from a signal handler during Popen can lose a successfully created child before
    assignment. Reader startup has the same handover to an OS thread. Only defer these small
    ownership transfers; ordinary waits and logging remain immediately interruptible.
    """
    previous, requested = {}, []

    def remember(signum, frame):
        if not requested:
            requested.append((signum, frame))

    if threading.current_thread() is threading.main_thread():
        for sig in (*_STOP_SIGNALS, signal.SIGINT):
            handler = signal.getsignal(sig)
            if handler is not signal.SIG_IGN:
                previous[sig] = signal.signal(sig, remember)
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        if requested:
            sig, frame = requested[0]
            handler = previous[sig]
            if callable(handler):
                handler(sig, frame)
            elif sig == signal.SIGINT:
                raise KeyboardInterrupt
            else:
                raise Terminated(sig)


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
    # Inherit the full environment, then overlay the caller's NXF_* overrides (engine version,
    # JVM args, …). Inheriting keeps shell-set vars (proxies, JAVA_HOME) working as before.
    env = {**os.environ, **env_extra} if env_extra else None
    with out_p.open("ab") as out_fh, err_p.open("ab") as err_fh:
        budget.check()
        proc = None
        readers = []
        completed = False
        try:
            try:
                launch = command
                if die_with_nfclaw is not None:
                    program = _program(command[0], cwd, env)
                    if program is None:
                        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), command[0])
                    launch = [*die_with_nfclaw, program, *command]
                with _defer_stop_signals():
                    proc = subprocess.Popen(launch, cwd=str(cwd), stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, env=env, **popen_kwargs)
            except OSError as exc:
                err = NfclawError(ErrorCode.EXECUTION_FAILED, f"Could not launch process: {exc}",
                                  fix="Ensure `nextflow` is installed and on PATH.",
                                  details={"run_log": str(run_log.path)})
                run_log.fail("could not launch", str(err))
                raise err from exc
            run_log.launched(proc.pid)
            # Keep both readers registered before startup; cleanup also owns a partially
            # started pair when thread allocation or a signal interrupts setup.
            readers = [
                threading.Thread(target=_tee,
                                 args=(proc.stdout, sys.stdout, out_fh, run_log, "out"),
                                 daemon=True),
                threading.Thread(target=_tee,
                                 args=(proc.stderr, sys.stderr, err_fh, run_log, "err"),
                                 daemon=True),
            ]
            for t in readers:
                with _defer_stop_signals():
                    t.start()
            code = proc.wait(timeout=budget.remaining(timeout_seconds))
            budget.check()
            completed = True
        except subprocess.TimeoutExpired as exc:
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
            if proc is not None:
                if isinstance(exc, NfclawError) and "timeout_seconds" in exc.details:
                    outcome = f"timed out after {exc.details['timeout_seconds']:g} s"
                elif isinstance(exc, (KeyboardInterrupt, Terminated)):
                    outcome = stop_outcome(exc)
                else:
                    outcome = f"failed during process supervision ({type(exc).__name__})"
                run_log.fail(outcome)
            raise
        finally:
            # Even PID logging and reader setup are inside the child's ownership scope.
            # On success the leader is already reaped; the ordinary completion path still
            # drains its streams without terminating a completed run.
            try:
                if proc is not None and not completed:
                    _terminate(proc, grace=grace, run_log=run_log)
            finally:
                _join(readers)
                if proc is not None and not any(t.is_alive() for t in readers):
                    for pipe in (proc.stdout, proc.stderr):
                        pipe.close()
    if code != 0:
        err = _failure(code, run_log, env if env is not None else os.environ, command)
        run_log.fail(f"failed (exit status {code})", str(err))
        raise err
    run_log.outcome = "success"
    return ExecResult(code, out_p, err_p)


# Run as `python -I -S -c _PDEATHSIG_LAUNCHER <nfclaw pid> <libc> <program> <argv…>`: ask the kernel
# for SIGTERM when nfclaw dies, then become the program (same pid, same open pipes and environment).
# The death signal survives `exec`, so it reaches Nextflow's launcher and the JVM it execs.
_PDEATHSIG_LAUNCHER = """\
import ctypes, os, signal, sys
parent, libc, program, argv = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4:]
ctypes.CDLL(libc, use_errno=True).prctl(1, signal.SIGTERM, 0, 0, 0)  # PR_SET_PDEATHSIG
if os.getppid() != parent:  # nfclaw died before the request took effect
    os._exit(1)
try:
    os.execv(program, argv)
except OSError as exc:
    sys.stderr.write(f"nfclaw: could not launch {program}: {exc}\\n")
    os._exit(127)
"""


def _die_with_parent() -> list[str] | None:
    """On Linux, the launcher that asks the kernel to send the child SIGTERM when nfclaw dies.

    nfclaw stops Nextflow itself on Ctrl-C, SIGTERM and SIGHUP; SIGKILL (`kill -9`, the out-of-
    memory killer) cannot be caught, and Nextflow — in its own session — would run on orphaned.
    The request is made by a fresh single-threaded interpreter that then execs the program, not by a
    `preexec_fn`: Python code between fork and exec can deadlock in a parent that runs threads, and
    nfclaw's container watch is running by then. None elsewhere, or if libc cannot be loaded."""
    if not sys.platform.startswith("linux") or not sys.executable:
        return None
    try:
        import ctypes
        import ctypes.util
        libc = ctypes.util.find_library("c") or "libc.so.6"
        if not hasattr(ctypes.CDLL(libc, use_errno=True), "prctl"):
            return None
    except OSError:
        return None
    return [sys.executable, "-I", "-S", "-c", _PDEATHSIG_LAUNCHER, str(os.getpid()), libc]


def _program(name: str, cwd: Path, env: Mapping[str, str] | None) -> str | None:
    """The executable `name` runs, found as Popen finds it: a path relative to the launch
    directory, else a search of the child's PATH. None when there is none."""
    if os.sep in name:
        path = Path(cwd, name)
        return str(path) if path.is_file() and os.access(path, os.X_OK) else None
    return shutil.which(name, path=(env if env is not None else os.environ).get("PATH",
                                                                                 os.defpath))


def _log_details(run_log: runlog.RunLog) -> dict[str, str]:
    """The files that hold the rest of the story, as absolute paths — only ones that exist."""
    details = {"run_log": str(run_log.path)}
    if run_log.nextflow_log is not None and run_log.nextflow_log.is_file():
        details["nextflow_log"] = str(run_log.nextflow_log)
    return details


def _failure(code: int, run_log: runlog.RunLog, env: Mapping[str, str],
             command: list[str] = ()) -> NfclawError:
    """The error for a launch that exited non-zero: what Nextflow itself reported, quoted from this
    launch's console, plus where the full logs are. Nextflow prints its error reports on stdout and
    some details on stderr (nf-schema's list of invalid values), and refers to its log relative to a
    directory the reader is not in. `env` is the environment Nextflow ran with, `command` what it
    ran."""
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
    # Nextflow refused an engine older than the release's `manifest.nextflowVersion`; nfclaw leaves
    # that check to Nextflow and only names the engine to pin.
    required = next((m.group(1) for line in on_stdout + on_stderr
                     if (m := _REQUIRED_ENGINE.search(line))), None)
    engine_hint = (f"The release requires Nextflow {required} or later (its manifest's "
                   f"nextflowVersion); add --nxf-ver {required} (a chain stage's \"nxf_ver\"). "
                   if required else "")
    parser_hint = _strict_parser_hint(on_stdout + on_stderr, run_log.nextflow_version, env,
                                      command)
    # A configuration or script the engine refused to compile stops the run before any task, so
    # resuming the same command cannot get further: the parser hint says what to change instead.
    retry = ("Fix the cause Nextflow reports, then run again with that change." if parser_hint else
             "Fix the cause Nextflow reports, then re-run the same command with --resume.")
    return NfclawError(
        ErrorCode.EXECUTION_FAILED, message,
        fix=(f"{time_limit_hint}{ipv6_hint}{engine_hint}{parser_hint}{retry}{task_hint} The whole "
             f"launch is in `run_log`. Common causes and fixes: {runlog.known_issues_path()}."),
        details=details)


def _strict_parser_hint(reported: list[str], banner: str | None, env: Mapping[str, str],
                        command: list[str]) -> str:
    """The fix for a release the strict syntax parser rejects, or "".

    Nextflow 26.04 made its strict parser the default; releases written for the legacy one fail
    to compile before any task (methylseq 4.2.0's `Invalid include source`, `def check_max(...)` in
    older configs). Only when the engine that ran parses strictly by default, the legacy parser was
    not already selected, and no file it rejected is one of the run's own `-c` configs (Nextflow
    names a failing file by its basename), which would be the caller's to fix."""
    if not any(_COMPILE_FAILED.search(line) for line in reported):
        return ""
    version = _ENGINE_VERSION.search(banner or "")
    if (version is None or (int(version[1]), int(version[2])) < _STRICT_PARSER_DEFAULT
            or env.get("NXF_SYNTAX_PARSER", "").strip() == "v1"):
        return ""
    rejected = {m[1] for line in reported if (m := _REJECTED_FILE.match(line))}
    own = {Path(value).name for flag, value in zip(command, command[1:], strict=False)
           if flag == "-c"}
    if not rejected or rejected & own:
        return ""
    return ("Nextflow 26.04 and later parse with strict syntax by default, which rejects syntax "
            "this release was written with: run it with the legacy parser, --nxf-env "
            "NXF_SYNTAX_PARSER=v1, or with an engine that defaults to it, --nxf-ver 25.10.4 "
            "(if the release's nextflowVersion allows; a chain stage's \"nxf_env\"/\"nxf_ver\"). ")


_TIME_LIMIT_ABORT = "process hasn't exited"
# Nextflow's verdict on a configuration or script it could not compile, the location of what it
# rejected (`Error nextflow.config:251:23: …`), and the engine its banner names.
_COMPILE_FAILED = re.compile(r"^ERROR ~ (?:Config parsing|Script compilation) failed")
_REJECTED_FILE = re.compile(r"^Error (\S+?):\d+:\d+: ")
_ENGINE_VERSION = re.compile(r"(\d+)\.(\d+)\.\d+")
_STRICT_PARSER_DEFAULT = (26, 4)
# Nextflow's refusal of an engine older than `manifest.nextflowVersion`: "Nextflow version 25.10.2
# does not match workflow required version: >=25.10.4".
_REQUIRED_ENGINE = re.compile(r"does not match workflow required version: !?\s*>=\s*"
                              r"(\d+(?:\.\d+)+)")
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


def _terminate(proc: subprocess.Popen, grace: float = _GRACE_SECONDS,
               run_log: runlog.RunLog | None = None) -> None:
    """Stop the child and everything it launched.

    Signals the whole process group, because killing just the child would orphan the task processes
    it spawned: SIGTERM first, so Nextflow runs its JVM shutdown hooks and cleans up its own tasks,
    then SIGKILL for whatever is still running once the grace period is over. The group is waited
    on, not just its leader — Nextflow exiting does not mean its tasks did, and a task that ignores
    or is still handling SIGTERM would otherwise be left running in the background.

    A task container is not in the group: the engine runs it, and only its client is. The
    containers the group's clients started are noted before each signal and removed once the group
    is gone, whichever of them the task wrappers did not remove in time (see
    `replay_guard.task_containers`).
    """
    if not hasattr(os, "killpg"):                     # Windows: no process groups to signal
        proc.kill()
        proc.wait()
        return
    pgid = proc.pid                                   # start_new_session: the child leads its group
    if proc.returncode is not None and not _group_alive(pgid):
        return                                        # reaped, and nothing of the group is left
    containers = _observe_task_containers(pgid, run_log)
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
        # group running — skip the rest of the wait, but still kill it. An unreaped leader keeps
        # its pid, and a live member the group's number; once both are gone the number is free for
        # another group, so it is neither searched nor signalled.
        held = proc.returncode is None or _group_alive(pgid)
        try:
            if held:
                for engine, names in _observe_task_containers(pgid, run_log).items():
                    containers.setdefault(engine, set()).update(names)
        finally:
            if held:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except OSError:
                    pass                              # the group is already gone
            proc.wait()
        if containers:                                # a second Ctrl-C still stops them too
            _remove_task_containers(containers, run_log)


def _observe_task_containers(pgid: int, run_log: runlog.RunLog | None) -> dict:
    containers = replay_guard.task_containers(pgid)
    for issue in getattr(containers, "issues", []):
        message = f"nfclaw: {issue}"
        print(message, file=sys.stderr, flush=True)
        if run_log is not None:
            run_log.note(message)
    return containers


def _remove_task_containers(containers: dict[tuple[str, ...], set[str]],
                            run_log: runlog.RunLog | None) -> None:
    """Remove the task containers a stopped run left behind, and say so."""
    removed, problems = replay_guard.remove_task_containers(containers)
    messages = ([f"nfclaw: removed {len(removed)} task container(s) the stopped run left behind: "
                 f"{', '.join(removed)}"] if removed else []) + \
        [f"nfclaw: a task container of the stopped run could not be removed: {problem}"
         for problem in problems]
    for message in messages:
        print(message, file=sys.stderr, flush=True)
        if run_log is not None:
            run_log.note(message)
