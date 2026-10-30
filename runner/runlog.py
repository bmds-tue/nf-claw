"""The run log: one complete, fixed-place record of every launch, and the facts a failure needs.

`nfclaw run` launches Nextflow from `--outdir`, so everything a reader needs after the fact sits at
paths that do not depend on where they are standing:

- `<outdir>/provenance/logs/run.log` — the whole launch, with child-output lines prefixed by `| `
  to distinguish them from nfclaw's status controls: nfclaw's
  header (command, launch dir, Nextflow log, advisories), Nextflow's stdout and stderr interleaved
  as produced, and a last line stating the outcome. A relaunch (`--resume`) appends, so the attempt
  that failed is never overwritten by the one that fixes it.
- Nextflow's own log — `<outdir>/.nextflow.log` (or `NXF_LOG_FILE`, resolved against `--outdir`).

Nothing here guesses a cause. On failure nfclaw quotes Nextflow's own error report verbatim — plus
the exception chain behind it from Nextflow's log, where the real reason is often the only thing
written — and names the files that hold the rest; the reader (or agent) does the diagnosis.
"""
from __future__ import annotations

import os
import json
import re
import shlex
import socket
import stat
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from runner import nextflow_command
from runner.errors import NfclawError
from runner.locking import output_writer
from runner.replay_guard import host_identity, quote_console, log_cursor_path, write_log_cursor

RUN_LOG_NAME = "run.log"
ERROR_MARK = "==> nfclaw error:"          # precedes the error nfclaw records, up to the last line

# The tail of a launch's console kept in memory for quoting its error. Nextflow ends a failed run
# with its error report, so the tail always holds it; a bound keeps a days-long run cheap.
_TAIL_BYTES = 256 * 1024
_MAX_EXCERPT_LINES = 50
_CONTEXT_LINES = 6           # at most this much of the paragraph just above an `ERROR ~` report
_TAIL_LINES = 15             # the last paragraph, quoted when Nextflow printed no `ERROR ~` line
_STDERR_LINES = 25
# The launcher's only routine stderr line; every real run's stderr holds nothing else (even `WARN:`
# lines go to stdout), so on a failure whatever else is on stderr is part of the error.
_UPDATE_NOTICE = re.compile(r"^Nextflow \S+ is available - Please consider updating")

# `.nextflow.log` entries: "Oct-05 21:57:35.089 [main] ERROR nextflow.cli.Launcher - …". The month
# is the JVM locale's abbreviation (`oct-05` in Spanish, `Okt.-05` in German, `10月-05`), so it is
# matched as any token rather than as English.
_LOG_STAMP = r"^[^\s\[\]-]{1,12}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} \[[^\]]*\] "
_LOG_ENTRY = re.compile(_LOG_STAMP)
_LOG_ERROR = re.compile(_LOG_STAMP + "ERROR ")
_LOG_TAIL_BYTES = 2 * 1024 * 1024
_MAX_CAUSES = 8
_MAX_CAUSE_LINES = 6         # continuation lines kept per cause message
_STACK_FRAME = re.compile(r"^\s+(at |\.\.\. \d+ (common frames omitted|more))")

_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b[@-_]")
_ENGINE_BANNER = re.compile(
    r"^[ \t]*N E X T F L O W[ \t]*~[ \t]*version[ \t]+"
    r"(\d+(?:\.\d+)+(?:-[A-Za-z0-9.-]+)?)[ \t]*\r?\n", re.MULTILINE)
_ENGINE_HEAD_BYTES = 64 * 1024
# Lines that end the context above `ERROR ~`: Nextflow's banner and launch line, and the end (or
# start) of an earlier report — Nextflow re-renders a report when stdout is not a terminal.
_CONTEXT_STOP = re.compile(r"N E X T F L O W|^Launching `|^\s*-- Check |^ERROR ~")
_REPORT_END = re.compile(r"^\s*-- Check ")
# A plugin logger (nf-co2footprint) relays console records as `<colour>LEVEL - [plugin]
# message<reset>` with no line break between them, so Nextflow's `ERROR ~` report arrives as `ERROR
# - [plugin] …` glued onto the record before it. Each relayed record starts a line, as a
# terminal shows it.
_RELAYED_RECORD = re.compile(r"(?:\x1b\[[0-9;]*m)+(?=(?:TRACE|DEBUG|INFO|WARN|ERROR) - "
                             r"\[[\w.@-]+\] )")
_RELAY_PREFIX = re.compile(r"^(?:TRACE|DEBUG|INFO|WARN|ERROR) - \[[\w.@-]+\] ")
_REPORT_START = re.compile(r"^ERROR (?:~|- \[[\w.@-]+\] )")


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def nextflow_log_path(launch_dir: Path, env_extra: dict[str, str] | None = None) -> Path:
    """Where Nextflow writes its own log for a run launched from `launch_dir`.

    `.nextflow.log` in the launch directory unless `NXF_LOG_FILE` names another file (the overlay
    wins over the shell, as it does at launch); a relative name resolves against the launch
    directory because that is Nextflow's cwd. Nextflow's console only ever says "Check
    '.nextflow.log'" — relative to a directory the reader is usually not in."""
    raw = (env_extra or {}).get("NXF_LOG_FILE") or os.environ.get("NXF_LOG_FILE")
    path = Path(raw) if raw else Path(".nextflow.log")
    return path if path.is_absolute() else launch_dir / path


def known_issues_path() -> str:
    """The symptom→fix map, as an absolute path when the repository is present (it is for the
    documented `pip install -e .`), so the pointer works from any working directory."""
    doc = Path(__file__).resolve().parent.parent / "docs" / "known-issues.md"
    return str(doc) if doc.is_file() else "docs/known-issues.md"


def _clean(text: str) -> list[str]:
    """Console text as a terminal would show it: no colour/cursor sequences, and a line redrawn with
    carriage returns reduced to its final state."""
    lines = []
    for raw in text.split("\n"):
        line = raw.rstrip("\r").rsplit("\r", 1)[-1]
        records = _RELAYED_RECORD.split(line)
        if len(records) > 1 and not records[0]:
            records = records[1:]                        # the line itself starts with a record
        lines += [_ANSI.sub("", record).rstrip() for record in records]
    return lines


def _squeeze(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        if line or (out and out[-1]):                     # collapse runs of blank lines
            out.append(line)
    while out and not out[-1]:
        out.pop()
    return out


def _reports(lines: list[str]) -> list[tuple[int, tuple[str, ...]]]:
    """Each `ERROR ~` report in the console as (start index, lines): from its `ERROR ~` line through
    Nextflow's closing "-- Check '.nextflow.log' file for details" (or up to the next report)."""
    reports = []
    i = 0
    while i < len(lines):
        if not _REPORT_START.match(lines[i]):
            i += 1
            continue
        j = i + 1
        while j < len(lines) and not _REPORT_START.match(lines[j]):
            j += 1
            if _REPORT_END.match(lines[j - 1]):
                break
        reports.append((i, tuple(_squeeze(lines[i:j]))))
        i = j
    return reports


def error_excerpt(console: str, *, tail_if_no_report: bool = True) -> list[str]:
    """Nextflow's own error reports from a launch's console output, quoted verbatim.

    Deterministic: every distinct `ERROR ~` report (Nextflow's error prefix), once each, in the
    order they first appear — Nextflow re-renders the same report when stdout is not a terminal, and
    the nf-core template follows the real one with a generic "ERROR ~ Pipeline failed" — preceded by
    the paragraph printed just above the last rendering of the first: the failed step's progress
    lines, or a config/script syntax error described above `ERROR ~ Config parsing failed`. Without
    an `ERROR ~` line (an `error "…"` raised by a pipeline prints only its message) it is the
    console's last paragraph, unless `tail_if_no_report` is off. A long excerpt keeps its head and
    its tail."""
    lines = _clean(console)
    distinct: dict[tuple[str, ...], int] = {}             # report → start of its last rendering
    for at, report in _reports(lines):
        distinct[report] = at                            # insertion order = first appearance
    if distinct:
        block = _paragraph_above(lines, next(iter(distinct.values())))
        for report in distinct:
            block += ([""] if block else []) + list(report)
    elif tail_if_no_report:
        end = len(lines)
        while end > 0 and not lines[end - 1]:
            end -= 1
        block = _last_paragraph(lines, end)
        if len(block) == 1 and _REPORT_END.match(block[0]):
            # A message closed by Nextflow's "-- Check script …" line: the message is just above.
            block = _squeeze(_last_paragraph(lines, end - 1) + [""] + block)
    else:
        block = []
    return _cap(block)


def _paragraph_above(lines: list[str], at: int) -> list[str]:
    """The run of non-blank lines just above line `at` (blank lines in between skipped), at most
    `_CONTEXT_LINES` of it, never reaching into the banner or an earlier report."""
    end = at
    while end > 0 and not lines[end - 1]:
        end -= 1
    start = end
    while start > 0 and lines[start - 1] and end - start < _CONTEXT_LINES \
            and not _CONTEXT_STOP.search(lines[start - 1]):
        start -= 1
    return lines[start:end]


def _last_paragraph(lines: list[str], at: int) -> list[str]:
    """The run of non-blank lines ending just above line `at` (blank lines skipped), at most
    `_TAIL_LINES` of it."""
    end = at
    while end > 0 and not lines[end - 1]:
        end -= 1
    start = end
    while start > 0 and lines[start - 1] and end - start < _TAIL_LINES:
        start -= 1
    return lines[start:end]


def _cap(block: list[str]) -> list[str]:
    """A long excerpt keeps its head (`Caused by`) and its tail (`Command error`, `Work dir`)."""
    if len(block) <= _MAX_EXCERPT_LINES:
        return block
    head, tail = 15, _MAX_EXCERPT_LINES - 16
    omitted = len(block) - head - tail
    return block[:head] + [f"… {omitted} lines omitted (full report in the run log) …"] + \
        block[-tail:]


def stderr_excerpt(text: str) -> list[str]:
    """What a failed launch wrote on stderr, minus the launcher's update notice — nf-schema's
    validation details ("* --param (value): Expected …"), a JVM or launcher error. A successful
    run's stderr carries nothing but that notice, so nothing here is noise."""
    lines = [line for line in _clean(text) if not _UPDATE_NOTICE.match(line)]
    return _cap(_squeeze(lines)[-_STDERR_LINES:])


def failing_task_dir(excerpt: list[str]) -> Path | None:
    """The work directory of the task that failed, as Nextflow's report names it (`Work dir:` and
    the path on the next line). Its `.command.err`/`.command.log` hold the tool's
    complete output."""
    for i, line in enumerate(excerpt):
        if line.strip() == "Work dir:":
            for nxt in excerpt[i + 1:]:
                if nxt.strip():
                    path = nxt.strip()
                    return Path(path) if path.startswith("/") else None
    return None


def nextflow_log_causes(log: Path) -> list[str]:
    """The exception chain behind Nextflow's last error, from its own log: the `Caused by: …` lines
    of the last ERROR entry, each with the rest of its message when it spans several lines.
    Deterministic, and often the only place the real reason is written — the console says "Unable
    to parse config file" while the log says "Network is unreachable". Empty when the entry carries
    no chain (a failed task's entry just repeats the console report)."""
    try:
        with log.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - _LOG_TAIL_BYTES))
            lines = fh.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return []
    errors = [i for i, line in enumerate(lines) if _LOG_ERROR.match(line)]
    if not errors:
        return []
    causes: list[list[str]] = []
    current: list[str] | None = None                     # the cause whose message is being read
    for line in lines[errors[-1] + 1:]:
        if _LOG_ENTRY.match(line):
            break                                        # the next entry: the error's chain is over
        if line.startswith("Caused by: ") and line[len("Caused by: "):].strip():
            current = [line.rstrip()]
            causes.append(current)
        elif _STACK_FRAME.match(line):
            current = None                               # the message ends where the frames begin
        elif current is not None and line.strip() and len(current) <= _MAX_CAUSE_LINES:
            current.append("  " + line.rstrip())         # a message that spans several lines
    distinct: list[list[str]] = []
    for cause in causes:
        if cause not in distinct:
            distinct.append(cause)
    return [line for cause in distinct[:_MAX_CAUSES] for line in cause]


# The nf-core template's completion summary, `-[nf-core/<name>] Pipeline completed successfully…-`,
# and the lines a pipeline prints right after it in the same form (rnaseq's skipped samples).
_SUMMARY_LINE = re.compile(r"^-\[(?P<name>[^\]\s]+)\]\s+(?P<message>.*?)\s*-?$")
_COMPLETED = "Pipeline completed successfully"
_WORKFLOW_STATS = re.compile(r"Workflow completed > WorkflowStats\[.*?\bignoredCount=(\d+)")


def completion_caveats(console: str, nextflow_log: Path | None = None) -> list[str]:
    """What a pipeline that exited 0 reported as missing from its results, in its own words.

    An exit status of 0 is all Nextflow and nfclaw judge a run by, yet a pipeline can finish
    "successfully" without some of its samples or tasks: nf-core's template says so in its
    completion summary ("…, but with errored process(es)" when failed tasks were ignored), rnaseq
    adds "with skipped sampl(es)" and names the QC threshold each sample failed, and Nextflow counts
    the ignored task failures in its log. These are quoted, never interpreted, so they reach the
    reader with the success instead of staying buried in the console."""
    caveats: list[str] = []
    lines = [_RELAY_PREFIX.sub("", line) for line in _clean(console)]
    starts = [i for i, line in enumerate(lines)
              if (m := _SUMMARY_LINE.match(line)) and m["message"].startswith(_COMPLETED)]
    if starts:
        first = _SUMMARY_LINE.match(lines[starts[-1]])
        if first["message"][len(_COMPLETED):].strip(" ,."):
            caveats.append(f"[{first['name']}] {first['message']}")
        for line in lines[starts[-1] + 1:]:
            m = _SUMMARY_LINE.match(line)
            if m is None or m["name"] != first["name"]:
                break
            if not m["message"].startswith("Sent summary e-mail"):   # the template's mail notice
                caveats.append(f"[{m['name']}] {m['message']}")
    if nextflow_log is not None:
        try:
            with nextflow_log.open("rb") as fh:
                fh.seek(0, os.SEEK_END)
                fh.seek(max(0, fh.tell() - _LOG_TAIL_BYTES))
                stats = _WORKFLOW_STATS.findall(fh.read().decode("utf-8", errors="replace"))
        except OSError:
            stats = []
        if stats and int(stats[-1]) > 0:
            caveats.append(f"Nextflow ignored {stats[-1]} failed task(s) (errorStrategy 'ignore'); "
                           "their results are missing")
    return caveats


class RunLog:
    """`run.log` for one launch: appended to (never truncated) and safe to write from both of the
    child's stream readers at once. Keeps the tail of this launch's console for quoting its error.

    Whoever opens it closes it with `finish()`, once nfclaw is done with the run — after the
    provenance bundle is written — so the final line never announces an outcome early."""

    def __init__(self, path: Path, *, nextflow_log: Path | None = None, label: str = "run"):
        self.path = path
        self.nextflow_log = nextflow_log
        self.label = label                               # what finished: a `run`, or a `chain`
        self.outcome = "failed"                          # until the run says otherwise
        self.shutdown_grace_seconds: float | None = None
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("ab")
        self._lock = threading.Lock()
        self._tails = {"out": bytearray(), "err": bytearray()}
        self._engine_heads = {"out": bytearray(), "err": bytearray()}
        self.nextflow_version: str | None = None
        self._finished = False
        self._console_line_start = True
        self._needs_separator = self._fh.tell() > 0

    @classmethod
    def open(cls, logs_dir: Path, *, command: list[str], launch_dir: Path,
             nextflow_log: Path | None = None, notes: list[str] | tuple[str, ...] = (),
             env: dict[str, str] | None = None,
             caveats: list[str] | tuple[str, ...] = ()) -> RunLog:
        """Start the record of a launch: its header, and one line on the terminal saying where it
        is — before anything else prints, since a long run's own output soon buries it. `env` is
        the overlay the command runs under (NXF_VER, …); the header's command line carries it."""
        log = cls(logs_dir / RUN_LOG_NAME, nextflow_log=nextflow_log)
        log.note(f"==> nfclaw run started {now()}")
        log.note(f"    command: {nextflow_command.shell_line(shlex.join(command), env)}")
        log.note(f"    launch dir: {launch_dir}")
        if nextflow_log is not None:
            log.note(f"    nextflow log: {nextflow_log}")
        # Who runs it: `nfclaw status` tells a live run from one whose nfclaw was killed outright
        # (SIGKILL, out of memory, a restart) — the only way a launch can end without a last line.
        for line in host_header():
            log.note(line)
        log.note(f"    pid: {os.getpid()}")
        for note in notes:
            log.note(f"    warning: {note}")
        # Known before launch and true of any success it ends in (a stub-run profile): `status`
        # reports these with the success, ahead of what the pipeline itself prints.
        for caveat in caveats:
            log.note(f"    caveat: {caveat}")
        print(f"nfclaw: logging this run to {log.path}", file=sys.stderr, flush=True)
        return log

    def note(self, text: str) -> None:
        """A line of nfclaw's own (header, error, outcome) — not part of the console tails."""
        text = text.rstrip("\n")
        if text.startswith("    "):
            text = text.replace("\r", "\\r").replace("\n", "\\n")
        else:
            text = text.replace("\n", "\n| ")
        started = bool(_STARTED.fullmatch(text))
        if started:
            try:
                log_cursor_path(self.path).unlink(missing_ok=True)
            except OSError:
                pass
            offset = self._fh.tell() + int(self._needs_separator or not self._console_line_start)
            text += "\n    console format: prefixed"
        self._write((text + "\n").encode("utf-8"), stream=None)
        if started:
            write_log_cursor(self.path, offset)

    def write(self, chunk: bytes, stream: str = "out") -> None:
        """Child bytes; retain raw tails and quote log lines so they cannot forge controls."""
        self._write(chunk, stream=stream)

    def _write(self, data: bytes, *, stream: str | None) -> None:
        with self._lock:
            if stream is not None:
                if (self.nextflow_version is None
                        and len(self._engine_heads[stream]) < _ENGINE_HEAD_BYTES):
                    head = self._engine_heads[stream]
                    head += data[:max(0, _ENGINE_HEAD_BYTES - len(head))]
                    text = "\n".join(_clean(head.decode("utf-8", errors="replace")))
                    if banner := _ENGINE_BANNER.search(text):
                        self.nextflow_version = f"nextflow version {banner[1]}"
                        self._engine_heads.clear()
                tail = self._tails[stream]
                tail += data
                del tail[:-_TAIL_BYTES]
                data, self._console_line_start = quote_console(data, self._console_line_start)
            else:
                if not self._console_line_start:
                    data = b"\n" + data
                self._console_line_start = data.endswith(b"\n")
            if self._needs_separator:
                data = b"\n" + data
                self._needs_separator = False
            try:
                self._fh.write(data)
                self._fh.flush()
            except (OSError, ValueError):
                pass                                     # a full disk must not kill the run itself

    def console_tail(self, stream: str = "out") -> str:
        with self._lock:
            return self._tails[stream].decode("utf-8", errors="replace")

    def launched(self, pid: int) -> None:
        """Record Nextflow's pid, before any of its output."""
        self.note(f"    nextflow pid: {pid}")

    def fail(self, outcome: str, error: str = "") -> None:
        """Record how the run failed: the error text now (after `ERROR_MARK`, so it can be read
        back apart from the console), the outcome for the final line."""
        self.outcome = outcome
        if error:
            self.note(ERROR_MARK)
            self.note("| " + error)

    def finish(self) -> None:
        """Close the record with its last line — `==> nfclaw run finished <time>: <outcome>` (or
        `nfclaw chain finished` for a chain's log)."""
        if self._finished:
            return
        self._finished = True
        outcome = self.outcome.replace("\r", "\\r").replace("\n", "\\n")
        self.note(f"==> nfclaw {self.label} finished {now()}: {outcome}")
        try:
            self._fh.close()
        except OSError:
            pass


def record_unlaunched(log: Path, *, command: str, outcome: str, error: str) -> None:
    """Append an attempt nfclaw refused (or was stopped) before launching to an existing run log.

    Without it a relaunch into the same --outdir that fails validation or preflight leaves the
    *previous* attempt's outcome as the log's last line — read by anyone polling a background run as
    the result of the new one. Only ever appended to a run log that already exists: a fresh
    --outdir is left untouched, so the next attempt is not refused as "not empty"."""
    try:
        if (not log.is_file() or log.is_symlink() or log.stat().st_nlink != 1
                or not log.resolve().is_relative_to(log.parent.parent.parent.resolve())):
            return
    except OSError:
        return
    command = command.replace("\r", "\\r").replace("\n", "\\n")
    error = "| " + error.rstrip("\n").replace("\n", "\n| ")
    lines = [f"==> nfclaw run started {now()}", "    console format: prefixed",
             f"    command: {command}", *host_header(), f"    pid: {os.getpid()}",
             ERROR_MARK, error, f"==> nfclaw run finished {now()}: {outcome}"]
    try:
        # Validation precedes the main writer lock. A refused attempt must not append status
        # markers to a live writer's log; use that same lock around this separate append.
        with output_writer(log.parent.parent.parent):
            log_cursor_path(log).unlink(missing_ok=True)
            with log.open("a", encoding="utf-8") as fh:
                offset = fh.tell() + 1
                fh.write("\n" + "\n".join(lines) + "\n")
            write_log_cursor(log, offset)
    except OSError:
        pass                                             # never mask the refusal itself
    except NfclawError:
        pass                                             # a live writer owns its status markers


# --- reading a run's state back (`nfclaw status`) -------------------------------------------------

_CONTROL_PREFIX = b"==> nfclaw "                 # every status control line, and only those
_STARTED = re.compile(r"^==> nfclaw (run|replay|chain) started (\S+)")
_FINISHED = re.compile(r"^==> nfclaw (run|replay|chain) finished (\S+): (.*)$")
_HEADER = re.compile(r"^    (command|launch dir|nextflow log|replay of|host|host id|pid|nextflow "
                     r"pid|replay supervisor pid|warning|caveat|console format): (.*)$")
_HEAD_BYTES = 64 * 1024
_STATE_TAIL_BYTES = 512 * 1024
_LAST_OUTPUT_LINES = 5
# A recorded pid as nfclaw writes it: ASCII digits within the platform's pid range (`str.isdigit`
# also accepts superscripts and other scripts' digits, which `int()` then refuses).
_PID = re.compile(r"[0-9]{1,10}")
_PID_MAX = 2**31 - 1
# What the recorded pid must be running, so a pid reused after a restart is not taken for the run:
# the `nfclaw` entry point (or `python -m runner`) for a run, the replay script for a replay.
_RUN_NAMES = {"run": ("nfclaw", "runner"), "replay": ("commands.sh",),
              "chain": ("nfclaw", "runner")}


@dataclass
class RunState:
    """The state of the last launch recorded in a run log.

    `state` is one of: `success`; `ended` (finished any other way — see `outcome`); `running`;
    `dead` (no last line and its nfclaw is gone: killed with SIGKILL, out of memory, a restart);
    `elsewhere` (unfinished, launched on another host — not judged from here); `missing`;
    `unreadable` (the log exists but cannot be read — `error` says why — so nothing is known)."""

    log: Path
    state: str
    kind: str = "run"
    outcome: str | None = None
    started: str | None = None
    finished: str | None = None
    host: str | None = None
    host_id: str | None = None
    pid: int | None = None
    nextflow_pid: int | None = None
    nextflow_alive: bool = False
    supervisor_pid: int | None = None
    supervisor_alive: bool = False
    nextflow_log: str | None = None
    error: list[str] = field(default_factory=list)
    console: str = ""                                    # the tail of the launch's console output
    last_output: list[str] = field(default_factory=list)
    # A successful launch's own report of what its results lack (`completion_caveats`).
    caveats: list[str] = field(default_factory=list)


def _argv(pid: int) -> list[str] | None:
    """A live process's command line, or None when it cannot be read."""
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return [a for a in raw.decode("utf-8", errors="replace").split("\0") if a]
    except OSError:
        pass
    try:
        out = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True,
                             text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.split() if out.returncode == 0 else []


def host_header() -> list[str]:
    lines = [f"    host: {socket.gethostname()}"]
    if identity := host_identity():
        lines.append(f"    host id: {identity}")
    return lines


def _is_process(pid: int | None, names: tuple[str, ...]) -> bool:
    """Whether `pid` is alive and running one of `names` (an argument's basename, or the argument
    itself) — a zombie or a reused pid is not."""
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass                                             # alive, but another user's
    except (OSError, OverflowError):                     # beyond this platform's pid range
        return False
    argv = _argv(pid)
    if argv is None:
        return True                                      # alive; nothing more can be checked
    return any(a in names or os.path.basename(a) in names for a in argv)


def _physical_lines(data: bytes) -> list[str]:
    # Control records use LF, matching quote_console. splitlines() would turn child
    # carriage returns or Unicode separators into unquoted status controls.
    lines = data.decode("utf-8", errors="replace").split("\n")
    if lines[-1] == "":
        lines.pop()
    return [line.removesuffix("\r") for line in lines]  # retain legacy CRLF logs


def _pid(value: str) -> int | None:
    """A header's pid, or None for a value no process can have (a damaged or edited log)."""
    if not _PID.fullmatch(value):
        return None
    pid = int(value)
    return pid if 0 < pid <= _PID_MAX else None


def _unreadable(log: Path, exc: OSError) -> RunState:
    where = f" ({exc.filename})" if exc.filename and str(exc.filename) != str(log) else ""
    return RunState(log, "unreadable", error=[f"{exc.strerror or exc}{where}"])


def read_state(log: Path, *, replay_engine_log: Path | None = None) -> RunState:
    """The state of the last launch in `log`, deterministically: its last line if it has one,
    otherwise whether the nfclaw that wrote it is still running. A writer index locates the latest
    launch; legacy logs are searched backward in blocks. Only its header and tail are parsed, so a
    days-long run's log stays cheap to check. A log that exists but cannot be read (another
    user's run, a directory that cannot be searched) is `unreadable`, never a traceback."""
    try:
        metadata = log.stat()
    except (FileNotFoundError, NotADirectoryError):
        return RunState(log, "missing")
    except OSError as exc:
        return _unreadable(log, exc)
    if not stat.S_ISREG(metadata.st_mode):
        return RunState(log, "missing")
    start = None
    offset = 0
    try:
        with log.open("rb") as fh:
            info = os.fstat(fh.fileno())
            offset = info.st_size
            start = None
            try:
                with log_cursor_path(log).open("rb") as cursor_file:
                    cursor_bytes = cursor_file.read(4097)
                if len(cursor_bytes) > 4096:
                    raise ValueError("oversized log cursor")
                cursor = json.loads(cursor_bytes)
                position = cursor["start"]
                if (cursor["device"] == info.st_dev and cursor["inode"] == info.st_ino
                        and type(position) is int and 0 <= position < cursor["size"] <= offset):
                    fh.seek(max(0, position - 1))
                    prefix = fh.read(1) if position else b"\n"
                    header = fh.read(128).decode("utf-8", errors="replace")
                    if prefix == b"\n" and _STARTED.match(header):
                        start = position
            except (OSError, ValueError, KeyError, TypeError):
                pass
            if start is None:
                # Legacy logs have no seek index. Scan backward in bounded blocks, stopping at
                # the newest header; never materialize the whole log or split a huge child line.
                end, overlap = offset, b""
                pattern = re.compile(rb"(?:^|\n)==> nfclaw (?:run|replay|chain) started [^\r\n ]+")
                while end > 0 and start is None:
                    begin = max(0, end - _STATE_TAIL_BYTES)
                    fh.seek(begin)
                    block = fh.read(end - begin) + overlap
                    matches = list(pattern.finditer(block))
                    matches = [m for m in matches if m.start() > 0 or begin == 0]
                    if matches:
                        match = matches[-1]
                        start = begin + match.start() + int(block[match.start():].startswith(b"\n"))
                    overlap = block[:256]
                    end = begin
            if start is None:
                return RunState(log, "missing")
            fh.seek(start)
            head = _physical_lines(fh.read(_HEAD_BYTES))
            tail_from = max(start, offset - _STATE_TAIL_BYTES)
            fh.seek(tail_from)
            tail = _physical_lines(fh.read(offset - tail_from))
    except OSError as exc:
        return _unreadable(log, exc)
    if tail_from > start and tail:
        tail = tail[1:]                                  # the first line may be cut mid-way

    m = _STARTED.match(head[0]) if head else None
    if m is None:
        return RunState(log, "missing")  # The log was truncated or replaced while reading.
    st = RunState(log, "missing", kind=m.group(1), started=m.group(2))
    header_lines = 1
    prefixed_console = False
    header_caveats: list[str] = []
    for line in head[1:]:
        h = _HEADER.match(line)
        if not h:
            break
        header_lines += 1
        key, value = h.group(1), h.group(2).strip()
        if key == "console format":
            prefixed_console = value == "prefixed"
        elif key == "host":
            st.host = value
        elif key == "host id":
            st.host_id = value
        elif key == "pid":
            st.pid = _pid(value)
        elif key == "nextflow pid":
            st.nextflow_pid = _pid(value)
        elif key == "replay supervisor pid":
            st.supervisor_pid = _pid(value)
        elif key == "nextflow log":
            st.nextflow_log = value
        elif key == "caveat":
            header_caveats.append(value)
    body = tail[header_lines:] if tail_from == start else tail

    if body and (f := _FINISHED.match(body[-1])):
        st.finished, st.outcome = f.group(2), f.group(3)
        body = body[:-1]
    if ERROR_MARK in body:
        at = len(body) - 1 - body[::-1].index(ERROR_MARK)
        st.error, body = body[at + 1:], body[:at]
    if prefixed_console:
        body = [line[2:] if line.startswith("| ") else line for line in body]
        st.error = [line[2:] if line.startswith("| ") else line for line in st.error]
    st.console = "\n".join(body)
    st.last_output = [line for line in _clean(st.console) if line][-_LAST_OUTPUT_LINES:]
    if st.outcome is not None:
        st.state = "success" if st.outcome == "success" else "ended"
        if st.state == "success":
            # A replay's header names no Nextflow log: it runs from its target, as a run does.
            nextflow_log = (Path(st.nextflow_log) if st.nextflow_log else
                            (replay_engine_log or log.parent.parent.parent / ".nextflow.log")
                            if st.kind == "replay" else None)
            st.caveats = header_caveats + completion_caveats(st.console, nextflow_log)
    elif ((st.host_id and st.host_id != host_identity())
          or (not st.host_id and st.host and st.host != socket.gethostname())):
        st.state = "elsewhere"
    else:
        st.nextflow_alive = _is_process(st.nextflow_pid, ("nextflow", "java"))
        st.supervisor_alive = st.kind == "replay" and _is_process(
            st.supervisor_pid, ("replay_guard.py",))
        st.state = "running" if _is_process(st.pid, _RUN_NAMES[st.kind]) else "dead"
    return st
