"""Detached nfclaw commands for the MCP server: a run or a chain that outlives whoever started it.

A job is one `nfclaw` command line (`run …`, `chain run …`), executed by the unmodified CLI, exactly
as if typed in a shell. It is started in its own session by a small supervisor process
(`python -m runner.jobs`), so neither the MCP client closing nor the MCP server restarting stops the
analysis. Everything about a job is on disk, in `<state dir>/jobs/<id>/`:

- `job.json`        what to run (argv, working directory, outdir) — written only by the server;
- `supervisor.json` the supervisor's pid, the CLI's pid, and finally the CLI's exit code;
- `output.log`      everything the CLI printed (its own messages and Nextflow's console);
- `cancel`          present once a stop was requested;
- `lock`            held (flock) by the supervisor for exactly as long as it lives.

The lock is taken by the server *before* the supervisor exists and handed to it as an inherited file
descriptor, so "is this job still running?" never depends on a pid that could have been reused.
How the analysis itself went is not recorded here: nfclaw's own run log (`nfclaw status`) says that.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import signal
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime
from pathlib import Path

try:
    import fcntl
except ImportError:                                       # Windows: no detached jobs
    fcntl = None

JOB_FILE = "job.json"
SUPERVISOR_FILE = "supervisor.json"
OUTPUT_LOG = "output.log"
CANCEL_FILE = "cancel"
LOCK_FILE = "lock"
# The directory `runner` is imported from: put on PYTHONPATH so `python -m runner` works for a job
# whether nfclaw is pip-installed or run from a checkout with `python3 -m runner`.
_IMPORT_ROOT = Path(__file__).resolve().parent.parent
_ID = re.compile(r"^\d{8}T\d{6}-[a-z0-9][a-z0-9-]{0,39}-[0-9a-f]{6}$")
_TAIL_BYTES = 64 * 1024


class JobError(Exception):
    """A job request that cannot be honoured (unknown id, unsupported platform, launch failure)."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def state_dir() -> Path:
    """Where nfclaw keeps state that belongs to no single run: `$NFCLAW_STATE_DIR`, else
    `$XDG_STATE_HOME/nfclaw`, else `~/.local/state/nfclaw`."""
    if raw := os.environ.get("NFCLAW_STATE_DIR"):
        return Path(raw).expanduser()
    base = os.environ.get("XDG_STATE_HOME")
    return (Path(base).expanduser() if base else Path.home() / ".local" / "state") / "nfclaw"


def jobs_dir() -> Path:
    return state_dir() / "jobs"


def cli_command(argv: list[str]) -> list[str]:
    """The process a job runs: the nfclaw CLI itself (`python -m runner`, which `nfclaw status`
    recognises as a live nfclaw), under the same interpreter as the server."""
    return [sys.executable, "-m", "runner", *argv]


def child_env() -> dict[str, str]:
    """The environment for an nfclaw process started on a client's behalf: this one, with `runner`
    importable and output unbuffered (so a job's log follows it live)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(_IMPORT_ROOT), env.get("PYTHONPATH", "")) if p)
    env["PYTHONUNBUFFERED"] = "1"
    return env


@dataclass
class Job:
    id: str
    kind: str                                  # "run" or "chain"
    argv: list[str]                            # the nfclaw command line, without the program name
    command: list[str]                         # what the supervisor executes
    cwd: str                                   # relative paths in argv mean what they would here
    outdir: str                                # absolute
    check: bool = False                        # `--check`: validates and prints, launches nothing
    pipeline: str | None = None
    created_at: str = ""
    log_path: str | None = None                # the run/chain log nfclaw keeps for this outdir
    log_size_before: int | None = None         # its size before this job (None: did not exist)
    supervisor_pid: int | None = None
    # Written by the supervisor (supervisor.json), read back on every load:
    child_pid: int | None = None
    started_at: str | None = None
    exit_code: int | None = None
    finished_at: str | None = None
    error: str | None = None
    cancel_requested: bool = False
    dir: Path = field(default=Path("."), repr=False)

    def spec(self) -> dict:
        """What job.json holds: the fields the server writes."""
        own = {"child_pid", "started_at", "exit_code", "finished_at", "error", "cancel_requested",
               "dir"}
        return {k: v for k, v in asdict(self).items() if k not in own}


def _write_json(path: Path, data: dict) -> None:
    """Replace `path` atomically, so a reader never sees half a record."""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def create_dir(label: str) -> Path:
    """A fresh, private directory for a new job. `label` (a pipeline name, `chain`) goes in its id."""
    slug = re.sub(r"[^a-z0-9-]+", "-", label.lower()).strip("-")[:40] or "job"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    root = jobs_dir()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    while True:
        path = root / f"{stamp}-{slug}-{secrets.token_hex(3)}"
        try:
            path.mkdir(mode=0o700)
            return path
        except FileExistsError:
            continue


def launch(job_dir: Path, *, kind: str, argv: list[str], cwd: str, outdir: str,
           check: bool = False, pipeline: str | None = None, log_path: str | None = None,
           command: list[str] | None = None) -> Job:
    """Start `nfclaw <argv>` detached, supervised, and return its record."""
    if fcntl is None:
        raise JobError("detached jobs need a POSIX system (Linux or macOS)")
    if not Path(cwd).is_dir():
        raise JobError(f"working directory does not exist: {cwd}")
    log_size = None
    if log_path:
        try:
            log_size = Path(log_path).stat().st_size
        except OSError:
            log_size = None
    job = Job(id=job_dir.name, kind=kind, argv=list(argv),
              command=list(command) if command else cli_command(argv), cwd=cwd, outdir=outdir,
              check=check, pipeline=pipeline, created_at=_now(), log_path=log_path,
              log_size_before=log_size, dir=job_dir)
    _write_json(job_dir / JOB_FILE, job.spec())
    lock_fd = os.open(job_dir / LOCK_FILE, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (job_dir / OUTPUT_LOG).open("ab") as out:
            proc = subprocess.Popen(
                [sys.executable, "-m", "runner.jobs", str(job_dir)],
                cwd=cwd, env=child_env(), stdin=subprocess.DEVNULL, stdout=out,
                stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(lock_fd,))
    except OSError as exc:
        _write_json(job_dir / SUPERVISOR_FILE,
                    {"exit_code": 127, "finished_at": _now(), "error": f"could not start: {exc}"})
        raise JobError(f"could not start the job: {exc}") from exc
    finally:
        os.close(lock_fd)                             # the supervisor's inherited copy keeps it held
    # Reap the supervisor while this server lives, so it never lingers as a zombie. Its outcome is
    # on disk; nothing waits for this thread.
    threading.Thread(target=proc.wait, daemon=True).start()
    job.supervisor_pid = proc.pid
    _write_json(job_dir / JOB_FILE, job.spec())
    return job


def load(job_id: str) -> Job:
    if not isinstance(job_id, str) or not _ID.fullmatch(job_id):
        raise JobError(f"not a job id: {job_id!r}")
    job_dir = jobs_dir() / job_id
    spec = _read_json(job_dir / JOB_FILE)
    if not spec:
        raise JobError(f"no such job: {job_id}")
    known = {f.name for f in fields(Job)}
    job = Job(**{k: v for k, v in spec.items() if k in known}, dir=job_dir)
    sup = _read_json(job_dir / SUPERVISOR_FILE)
    for key in ("child_pid", "started_at", "exit_code", "finished_at", "error"):
        if key in sup:
            setattr(job, key, sup[key])
    job.cancel_requested = (job_dir / CANCEL_FILE).exists()
    return job


def list_jobs() -> list[Job]:
    """Every recorded job, newest first."""
    root = jobs_dir()
    if not root.is_dir():
        return []
    out = []
    for d in root.iterdir():
        try:
            out.append(load(d.name))
        except JobError:
            continue
    return sorted(out, key=lambda j: (j.created_at, j.id), reverse=True)


def alive(job: Job) -> bool:
    """Whether the job's supervisor is still running: it holds the job's lock until it exits."""
    if fcntl is None:
        return False
    try:
        fd = os.open(job.dir / LOCK_FILE, os.O_RDWR)
    except OSError:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    except OSError:
        return False
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def state(job: Job) -> str:
    """`running`, or how the job ended: `succeeded`, `failed`, `cancelled`, or `lost` (its
    supervisor stopped without recording an outcome — killed outright, or the host restarted)."""
    if alive(job):
        return "running"
    if job.exit_code == 0:
        return "succeeded"
    if job.cancel_requested:
        return "cancelled"
    return "failed" if job.exit_code is not None else "lost"


def cancel(job: Job) -> bool:
    """Ask a running job to stop the way `kill <nfclaw pid>` does: nfclaw shuts Nextflow and its
    tasks down, closes its run log with the outcome and writes provenance. False if it had ended."""
    if not alive(job):
        return False
    (job.dir / CANCEL_FILE).write_text(_now() + "\n", encoding="utf-8")
    if job.supervisor_pid and alive(job):             # the lock proves the pid is still ours
        try:
            os.kill(job.supervisor_pid, signal.SIGTERM)
        except ProcessLookupError:
            return False
    return True


def output_tail(job: Job, lines: int) -> list[str]:
    """The last `lines` lines the job's command printed."""
    if lines <= 0:
        return []
    try:
        with (job.dir / OUTPUT_LOG).open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - _TAIL_BYTES))
            data = fh.read()
    except OSError:
        return []
    text = data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    out = text.split("\n")
    if size > _TAIL_BYTES and out:
        out = out[1:]                                 # the first line may be cut mid-way
    while out and not out[-1].strip():
        out.pop()
    return out[-lines:]


# --- the supervisor (`python -m runner.jobs <job dir>`) -------------------------------------------

def supervise(job_dir: Path) -> int:
    """Run the job's command, forward a stop request to it, and record how it exited.

    The lock fd inherited from the server stays open, unused, for this process's lifetime: that is
    what tells a reader the job is still running. The command is the CLI, which turns SIGTERM into a
    clean stop of Nextflow and its tasks; the supervisor only relays the signal and keeps the record.
    """
    child: list[subprocess.Popen] = []
    stopping: list[int] = []

    def relay(signum, _frame) -> None:
        stopping.append(signum)
        if child and child[0].poll() is None:
            try:
                child[0].send_signal(signal.SIGTERM)
            except OSError:
                pass

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, relay)
    record_path = job_dir / SUPERVISOR_FILE
    record: dict = {"supervisor_pid": os.getpid(), "started_at": _now()}
    if (job_dir / CANCEL_FILE).exists():              # stopped before there was anything to stop
        record.update(exit_code=143, finished_at=_now(), error="cancelled before it started")
        _write_json(record_path, record)
        return 0
    try:
        spec = _read_json(job_dir / JOB_FILE)
        proc = subprocess.Popen(spec["command"], cwd=spec["cwd"], stdin=subprocess.DEVNULL)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        record.update(exit_code=127, finished_at=_now(), error=f"could not start: {exc}")
        print(f"nfclaw job: could not start the command: {exc}", file=sys.stderr, flush=True)
        _write_json(record_path, record)
        return 1
    child.append(proc)
    if stopping:                                      # asked to stop before the command existed
        relay(stopping[0], None)
    record["child_pid"] = proc.pid
    _write_json(record_path, record)
    code = proc.wait()
    record.update(exit_code=code, finished_at=_now())
    _write_json(record_path, record)
    return 0


if __name__ == "__main__":
    raise SystemExit(supervise(Path(sys.argv[1])))
