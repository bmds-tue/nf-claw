"""Standalone record of the execution environment a run used, copied into each provenance bundle.

The bytes a run starts from (local inputs, configuration, pipeline source) are checksummed before
launch. What the engine fetched while it ran is recorded here afterwards, from Nextflow's own
records of that run:

- the container image each process ran, resolved to an immutable identity: the registry digest the
  engine pulled (and its local image ID), or the SHA-256 of a local image file;
- the Nextflow plugins and Java runtime the engine loaded;
- every remote file Nextflow staged for a task: its URL and the SHA-256 of the staged copy.

From the digests it writes a Nextflow config pinning each process to the image it ran, so a replay
pulls the same image bytes even after a tag has moved. A replay records the same facts for itself
and compares them: another image, plugin or remote file makes it a different execution.

Standard library only, and compatible with older Python 3 releases: a recorded replay must not
import whatever version of nfclaw happens to be installed later.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
import platform
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VERSION = 1
RECORD_NAME = "environment.json"
PINS_NAME = "containers.config"
CHECK_NAME = "environment_check.json"

# Engines whose images are registry references, resolved through their own CLI.
REGISTRY_ENGINES = ("docker", "podman")
# Engines that run a local image file (Nextflow pulls or converts the image into its cache).
FILE_ENGINES = ("singularity", "apptainer")
ENGINES = REGISTRY_ENGINES + FILE_ENGINES + ("charliecloud", "shifter", "sarus")

# How each engine appears in a task's .command.run, the wrapper Nextflow generates for every task.
_ENGINE_COMMANDS = (
    ("docker", re.compile(r"\bdocker\s+run\b")),
    ("podman", re.compile(r"\bpodman\s+run\b")),
    ("apptainer", re.compile(r"\bapptainer\s+(?:exec|run)\b")),
    ("singularity", re.compile(r"\bsingularity\s+(?:exec|run)\b")),
    ("charliecloud", re.compile(r"\bch-run\b")),
    ("sarus", re.compile(r"\bsarus\s+run\b")),
    ("shifter", re.compile(r"\bshifter\s")),
)
_PROCESS = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?::[A-Za-z_][A-Za-z0-9_]*)*")
_RUN_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
# A registry reference safe to write into a single-quoted Groovy string.
_REFERENCE = re.compile(r"[a-z0-9][a-z0-9._-]*(?::[0-9]+)?(?:/[a-z0-9._-]+)+@sha256:[0-9a-f]{64}")
# Registries whose references are short-lived per-request augmentations (Wave's `wt` tokens).
_EPHEMERAL_REGISTRIES = ("wave.seqera.io",)
_FOREIGN = (
    re.compile(r"Copying foreign file (?P<source>\S+) to work dir: (?P<staged>\S+)\s*$"),
    re.compile(r"Local cache found for foreign file (?P<source>\S+) at (?P<staged>\S+)\s*$"),
)
# A file nf-schema read and validated itself (a samplesheet given as a URL): Nextflow never
# stages it.
_VALIDATED = re.compile(r"Validation of file '(?P<url>(?:https?|ftp)://[^']+)' passed")
# Files read that way are tables; a larger one is left unhashed rather than downloaded again.
FETCH_LIMIT = 100 * 1024 * 1024
_PLUGIN = (re.compile(r"Plugin started (?P<id>[A-Za-z0-9_.-]+@[A-Za-z0-9_.+-]+)"),
           re.compile(r"Start plugin '(?P<id>[A-Za-z0-9_.-]+@[A-Za-z0-9_.+-]+)'"))
_RUNTIME = re.compile(r"^\s*Runtime: (?P<runtime>.+?)\s*$")
_SESSION = re.compile(r"nextflow\.Session - Session UUID: (?P<session>[0-9a-fA-F-]{36})")
_BUILD = re.compile(r"^\s*Version: (?P<version>\S+) build (?P<build>\d+)")


class CaptureError(Exception):
    """Nextflow's records of the run could not be read."""


# A monotonic time after which no further probe starts (the run's own deadline, when it has one).
_deadline: float | None = None


def _run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None,
         timeout: float = 120) -> subprocess.CompletedProcess | None:
    """Run a bounded probe; stop its whole process group on timeout or interruption."""
    if _deadline is not None:
        left = _deadline - time.monotonic()
        if left <= 0:
            return None
        timeout = min(timeout, left)
    try:
        proc = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                errors="replace", start_new_session=True)
    except OSError:
        return None
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except BaseException as exc:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        if isinstance(exc, subprocess.TimeoutExpired):
            return None
        raise
    return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)


def _first_line(text: str, limit: int = 300) -> str:
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()[:limit]
    return ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def history(launch_dir: Path) -> list[dict[str, str]]:
    """Nextflow's run history in a launch directory, oldest first (`.nextflow/history`)."""
    try:
        text = (launch_dir / ".nextflow" / "history").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    runs = []
    for line in text.splitlines():
        fields = line.split("\t")
        if len(fields) >= 6 and _RUN_NAME.fullmatch(fields[2]):
            runs.append({"started": fields[0], "name": fields[2], "status": fields[3],
                         "session_id": fields[5]})
    return runs


def tasks(launch_dir: Path, run_name: str, env: dict[str, str] | None,
          timeout: float = 600) -> list[dict[str, str | None]]:
    """Every task of a run as Nextflow recorded it, cached tasks of a resumed run included."""
    result = _run(["nextflow", "log", run_name, "-f", "process,container,status,workdir"],
                  cwd=launch_dir, env=env, timeout=timeout)
    if result is None:
        raise CaptureError("`nextflow log` could not be run or did not finish")
    if result.returncode != 0:
        raise CaptureError(f"`nextflow log {run_name}` failed: "
                           f"{_first_line(result.stderr) or _first_line(result.stdout)}")
    records = []
    for line in result.stdout.splitlines():
        fields = [field.strip() for field in line.split("\t")]
        if len(fields) != 4 or not _PROCESS.fullmatch(fields[0]):
            continue
        process, container, status, workdir = (None if value in ("", "-", "null") else value
                                               for value in fields)
        records.append({"process": process, "container": container, "status": status,
                        "workdir": workdir})
    return records


def engine_of(task_records: list[dict], profile: str | None = None) -> str | None:
    """The container engine the tasks ran under, read from the wrapper Nextflow generated."""
    checked = 0
    for task in task_records:
        workdir = task.get("workdir")
        if not task.get("container") or not workdir or not workdir.startswith("/"):
            continue
        checked += 1
        if checked > 20:
            break
        try:
            with open(os.path.join(workdir, ".command.run"), encoding="utf-8",
                      errors="replace") as stream:
                text = stream.read(2_000_000)
        except OSError:
            continue
        for name, pattern in _ENGINE_COMMANDS:
            if pattern.search(text):
                return name
    for name in (part.strip() for part in (profile or "").split(",")):
        if name in ENGINES:
            return name
    return None


def split_reference(reference: str) -> tuple[str, str | None, str | None]:
    """A container reference as (repository, tag, digest)."""
    name, _, digest = reference.partition("@")
    tag = None
    slash, colon = name.rfind("/"), name.rfind(":")
    if colon > slash:
        name, tag = name[:colon], name[colon + 1:]
    return name, tag, digest or None


def normalize_repository(repository: str) -> str:
    """A repository name as a registry would spell it in full (Docker Hub's implicit host too)."""
    first, separator, rest = repository.partition("/")
    if separator and ("." in first or ":" in first or first == "localhost"):
        if first in ("docker.io", "index.docker.io", "registry-1.docker.io"):
            # Docker Hub's official images live under `library/`, however the name spells them.
            return "docker.io/" + (rest if "/" in rest else "library/" + rest)
        return repository
    return "docker.io/" + (repository if separator else "library/" + repository)


def resolve_registry_image(engine: str, reference: str, env: dict[str, str] | None,
                           at_start: bool = False) -> dict:
    """The local engine's identity of an image it ran: image ID, registry digests, platform.

    `at_start` marks an inspection made as a task container started from the reference (while the
    image was in use) rather than after the run. A reference by digest identifies its image even
    after the engine has removed it: the engine verified the pulled content against that digest.
    """
    repository, _, pinned = split_reference(reference)
    repository = normalize_repository(repository)
    result = _run([engine, "image", "inspect", reference], env=env, timeout=60)
    failure = None
    if result is None:
        failure = f"`{engine} image inspect` could not be run"
    elif result.returncode != 0:
        failure = f"`{engine} image inspect` failed: {_first_line(result.stderr)}"
    else:
        try:
            data = json.loads(result.stdout)
            data = data[0] if isinstance(data, list) else data
            if not isinstance(data, dict):
                raise ValueError
        except (ValueError, IndexError):
            failure = f"`{engine} image inspect` returned no image"
    if failure is not None:
        if pinned and _DIGEST.fullmatch(pinned):
            return {"kind": "registry", "repository": repository, "id": None, "digest": pinned,
                    "repo_digests": [f"{repository}@{pinned}"], "platform": None, "size": None,
                    "source": "reference digest"}
        return {"kind": "unresolved", "reason": failure}
    image_id = data.get("Id") if isinstance(data.get("Id"), str) else None
    if image_id and re.fullmatch(r"[0-9a-f]{64}", image_id):
        image_id = "sha256:" + image_id                       # podman omits the algorithm
    repo_digests = []
    for item in data.get("RepoDigests") or []:
        if isinstance(item, str) and "@" in item:
            name, _, digest = item.partition("@")
            if _DIGEST.fullmatch(digest):
                repo_digests.append(f"{normalize_repository(name)}@{digest}")
    repo_digests = sorted(set(repo_digests))
    own = sorted({item.partition("@")[2] for item in repo_digests
                  if item.partition("@")[0] == repository})
    record = {"kind": "registry", "repository": repository, "id": image_id,
              "repo_digests": repo_digests,
              "platform": "/".join(str(data[key]) for key in ("Os", "Architecture", "Variant")
                                   if isinstance(data.get(key), str) and data[key]),
              "size": data.get("Size") if isinstance(data.get("Size"), int) else None}
    record["source"] = "task container at start" if at_start else "image inspected after the run"
    if pinned and _DIGEST.fullmatch(pinned):
        record["digest"] = pinned                       # a reference by digest names itself
    elif len(own) == 1:
        record["digest"] = own[0]
    elif own:
        record["digest_candidates"] = own               # pulled by more than one manifest
    return record


def resolve_file_image(path: str) -> dict:
    image = Path(path)
    try:
        if image.is_file():
            return {"kind": "file", "path": path, "sha256": _sha256(image),
                    "size": image.stat().st_size}
    except OSError as exc:
        return {"kind": "unresolved", "reason": f"the image file could not be read: {exc}"}
    if image.is_dir():
        return {"kind": "unresolved", "reason": "a sandbox directory image is not hashed"}
    return {"kind": "unresolved", "reason": "the image file no longer exists"}


def engine_details(engine: str | None, env: dict[str, str] | None) -> dict | None:
    if engine is None:
        return None
    details = {"name": engine}
    command = {"docker": ["docker", "version", "--format", "{{.Server.Version}}"],
               "podman": ["podman", "version", "--format", "{{.Client.Version}}"],
               "singularity": ["singularity", "--version"],
               "apptainer": ["apptainer", "--version"]}.get(engine)
    if command:
        result = _run(command, env=env, timeout=30)
        if result is not None and result.returncode == 0 and _first_line(result.stdout):
            details["version"] = _first_line(result.stdout, 120)
    return details


def _log_files(log_path: Path) -> list[Path]:
    """The run's Nextflow log and the rotated logs of earlier attempts beside it."""
    files = [log_path]
    files += [log_path.with_name(f"{log_path.name}.{n}") for n in range(1, 10)]
    return [path for path in files if path.is_file()]


def log_facts(log_path: Path, session_id: str | None) -> dict:
    """Plugins, runtime and staged remote files from Nextflow's own log of the run.

    Plugins and runtime come from the run's own log. Staged remote files are also collected from
    the rotated logs of the same session (each log names it: `Session UUID: …`): a resumed run
    reuses files an earlier attempt staged, and only that attempt's log names their source. The
    staging layout differs between engines (`stage-<session>/` since Nextflow 23, a shared `stage/`
    before), so the session is read from the log, not from the staged path.
    """
    facts = {"runtime": None, "build": None, "plugins": [], "staged": {}, "validated": []}
    plugins = set()
    for index, path in enumerate(_log_files(log_path)):
        current = index == 0
        session = None
        staged = []
        try:
            with path.open(encoding="utf-8", errors="replace") as stream:
                for line in stream:
                    if session is None and (match := _SESSION.search(line)):
                        session = match["session"]
                    if current:
                        if facts["runtime"] is None and (match := _RUNTIME.match(line)):
                            facts["runtime"] = match["runtime"]
                        if facts["build"] is None and (match := _BUILD.match(line)):
                            facts["build"] = f"{match['version']} build {match['build']}"
                        for pattern in _PLUGIN:
                            for match in pattern.finditer(line):
                                plugins.add(match["id"])
                        if ((match := _VALIDATED.search(line))
                                and match["url"] not in facts["validated"]):
                            facts["validated"].append(match["url"])
                    if "foreign file" not in line:
                        continue
                    for pattern in _FOREIGN:
                        if match := pattern.search(line):
                            staged.append((match["source"], match["staged"]))
        except OSError:
            continue
        # A rotated log counts only when it names this run's session; the run's own log counts
        # unless it names another one.
        if session_id and session is not None and session != session_id:
            continue
        if not current and (not session_id or session is None):
            continue
        for source, copy in staged:
            # The newest log wins: it describes the attempt that finished.
            facts["staged"].setdefault(source, copy)
    facts["plugins"] = sorted(plugins)
    return facts


def _raise(error: OSError) -> None:
    raise error


def _tree_digest(root: Path) -> dict:
    """One digest for a staged directory. A directory that cannot be listed, or a symlink back
    into one of its own ancestors, leaves it without one rather than a digest of part of it."""
    lines = []
    count = size = 0
    ancestors = {os.fspath(root): frozenset()}
    for directory, subdirs, files in os.walk(root, followlinks=True, onerror=_raise):
        real = os.path.realpath(directory)
        chain = ancestors.pop(directory, frozenset())
        if real in chain:
            raise OSError(errno.ELOOP, "cyclic directory symlink", directory)
        subdirs.sort()
        for name in subdirs:
            ancestors[os.path.join(directory, name)] = chain | {real}
        for name in sorted(files):
            path = Path(directory, name)
            relative = path.relative_to(root).as_posix()
            lines.append(f"{_sha256(path)}  {relative}\n")
            count += 1
            size += path.stat().st_size
    return {"type": "directory", "sha256": hashlib.sha256("".join(lines).encode()).hexdigest(),
            "files": count, "size": size}


def remote_inputs(staged: dict[str, str]) -> dict[str, dict]:
    """The SHA-256 of each remote file as Nextflow staged it for the run's tasks."""
    recorded = {}
    for source, copy in sorted(staged.items()):
        path = Path(copy)
        try:
            if not copy.startswith("/"):
                recorded[source] = {"unresolved": "staged outside the local filesystem"}
            elif path.is_file():
                recorded[source] = {"sha256": _sha256(path), "size": path.stat().st_size}
            elif path.is_dir():
                recorded[source] = _tree_digest(path)
            else:
                recorded[source] = {"unresolved": "the staged copy no longer exists"}
        except OSError as exc:
            recorded[source] = {"unresolved": f"the staged copy could not be read: {exc}"}
    return recorded


def fetch_digest(url: str) -> dict:
    """The SHA-256 of a remote file the pipeline read without staging it, downloaded again now."""
    timeout = 60.0
    if _deadline is not None:
        timeout = min(timeout, _deadline - time.monotonic())
        if timeout <= 0:
            return {"unresolved": "the run's deadline ended the recording first"}
    digest = hashlib.sha256()
    size = 0
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "nfclaw-provenance"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                size += len(chunk)
                if size > FETCH_LIMIT:
                    return {"unresolved": f"larger than {FETCH_LIMIT // (1024 * 1024)} "
                                          "MiB; not hashed"}
                digest.update(chunk)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        return {"unresolved": f"could not be read again: {exc}"}
    return {"sha256": digest.hexdigest(), "size": size,
            "read_by": "parameter validation (not staged); bytes read again after the run"}


def capture(launch_dir: Path, *, log_path: Path, env: dict[str, str] | None = None,
            history_offset: int | None = None, profile: str | None = None,
            observed: dict[str, list[dict]] | None = None,
            previous: dict | None = None, deadline: float | None = None) -> dict:
    """See `_capture`; `deadline` (monotonic) bounds every probe, and a probe it cuts short leaves
    the gap recorded under `issues` rather than an identity."""
    global _deadline
    _deadline = deadline
    try:
        record = _capture(launch_dir, log_path=log_path, env=env, history_offset=history_offset,
                          profile=profile, observed=observed, previous=previous)
    finally:
        _deadline = None
    if deadline is not None and time.monotonic() >= deadline:
        record["issues"].append("the run's deadline ended the recording of "
                                "its execution environment")
    return record


def _capture(launch_dir: Path, *, log_path: Path, env: dict[str, str] | None = None,
             history_offset: int | None = None, profile: str | None = None,
             observed: dict[str, list[dict]] | None = None,
             previous: dict | None = None) -> dict:
    """The execution environment of the run Nextflow last recorded in `launch_dir`.

    `history_offset` is how many runs the history held before this launch: the run is the newest
    entry after it, and none means Nextflow never registered a session (it stopped before running).
    `observed` holds, by reference, the identities of the images task containers started with while
    the run went on (runner.container_watch): the exact image each ran, even if it was removed or
    its tag re-pulled since. Other references are inspected now, and an image the engine no longer
    has keeps the identity an earlier attempt of the same run recorded (`previous`, a resumed run).
    Never raises for what it cannot read; that is recorded under `issues` instead.
    """
    record = {"version": VERSION, "run": None, "nextflow_build": None, "nextflow_runtime": None,
              "nextflow_plugins": [], "container_engine": None, "processes": {}, "images": {},
              "pinned_containers": {}, "remote_inputs": {}, "issues": [],
              "host": {"system": platform.system(), "machine": platform.machine()}}
    runs = history(launch_dir)
    candidates = runs[history_offset:] if history_offset is not None else runs
    run = candidates[-1] if candidates else None
    facts = log_facts(log_path, run["session_id"] if run else None)
    record["nextflow_build"] = facts["build"]
    record["nextflow_runtime"] = facts["runtime"]
    record["nextflow_plugins"] = facts["plugins"]
    if run is None:
        record["issues"].append("Nextflow recorded no session for this launch: no task ran")
        return record
    record["run"] = {"name": run["name"], "session_id": run["session_id"]}
    record["remote_inputs"] = remote_inputs(facts["staged"])
    for url in facts["validated"]:
        if url not in record["remote_inputs"]:
            record["remote_inputs"][url] = fetch_digest(url)
    try:
        task_records = tasks(launch_dir, run["name"], env)
    except CaptureError as exc:
        record["issues"].append(f"task records could not be read: {exc}")
        return record
    processes: dict[str, dict] = {}
    for task in task_records:
        entry = processes.setdefault(task["process"], {"containers": set(), "tasks": 0,
                                                       "without_container": 0})
        entry["tasks"] += 1
        if task["container"]:
            entry["containers"].add(task["container"])
        else:
            entry["without_container"] += 1
    record["processes"] = {name: {**entry, "containers": sorted(entry["containers"])}
                           for name, entry in sorted(processes.items())}
    engine = engine_of(task_records, profile)
    record["container_engine"] = engine_details(engine, env)
    names = sorted({name for entry in processes.values() for name in entry["containers"]})
    earlier = (previous or {}).get("images") or {}
    for name in names:
        seen = (observed or {}).get(name) or []
        distinct = {json.dumps(item, sort_keys=True): item for item in seen}
        if engine in REGISTRY_ENGINES and len(distinct) == 1:
            record["images"][name] = next(iter(distinct.values()))
        elif engine in REGISTRY_ENGINES and distinct:
            record["images"][name] = {"kind": "multiple", "variants": sorted(
                distinct.values(), key=lambda item: str(item.get("id"))), "reason": (
                "task containers started from more than one image under this reference")}
        elif engine in REGISTRY_ENGINES and not name.startswith("/"):
            image = resolve_registry_image(engine, name, env)
            if image["kind"] == "unresolved" and earlier.get(name, {}).get("kind") == "registry":
                image = {**earlier[name], "source": "recorded by an earlier attempt of this run"}
            record["images"][name] = image
        elif name.startswith("/") and engine in FILE_ENGINES + (None,):
            record["images"][name] = resolve_file_image(name)
        else:
            record["images"][name] = {"kind": "unresolved", "reason": (
                f"images run by {engine} are not resolved" if engine
                else "the container engine could not be determined")}
    record["pinned_containers"] = pins(record)
    unresolved = sorted(name for name, image in record["images"].items()
                        if image.get("kind") in ("unresolved", "multiple"))
    if unresolved:
        record["issues"].append(f"{len(unresolved)} container image(s) have no recorded identity: "
                                + ", ".join(unresolved))
    unpinned = sorted(name for name, entry in record["processes"].items()
                      if entry["containers"] and name not in record["pinned_containers"]
                      and engine in REGISTRY_ENGINES)
    if unpinned:
        record["issues"].append(f"{len(unpinned)} process(es) are not pinned to an image digest "
                                "for replay: " + ", ".join(unpinned))
    return record


def pins(record: dict) -> dict[str, str]:
    """Each process that ran exactly one registry image with a known digest: that image
    by digest."""
    engine = (record.get("container_engine") or {}).get("name")
    if engine not in REGISTRY_ENGINES:
        return {}
    pinned = {}
    for process, entry in sorted(record.get("processes", {}).items()):
        if len(entry.get("containers", [])) != 1 or entry.get("without_container"):
            continue
        image = record.get("images", {}).get(entry["containers"][0], {})
        if image.get("kind") != "registry" or not image.get("digest"):
            continue
        reference = f"{image['repository']}@{image['digest']}"
        host = image["repository"].split("/", 1)[0]
        if host in _EPHEMERAL_REGISTRIES or not _PROCESS.fullmatch(process) \
                or not _REFERENCE.fullmatch(reference):
            continue
        pinned[process] = reference
    return pinned


def pin_config(record: dict) -> str | None:
    """A Nextflow config that runs each pinned process on the image digest it ran."""
    pinned = record.get("pinned_containers") or {}
    if not pinned:
        return None
    blocks = "".join(f"    withName: '{process}' {{\n        container = '{reference}'\n    }}\n"
                     for process, reference in sorted(pinned.items()))
    return ("// Generated by nfclaw from environment.json: the container image each process of the\n"  # noqa: E501
            "// recorded run used, by registry digest, so a replay runs the same image bytes even\n"
            "// after a tag has moved. A fully qualified process selector takes precedence over\n"
            "// the pipeline's own selectors.\n"
            "process {\n" + blocks + "}\n")


def _identity(image: dict | None):
    if not image or image.get("kind") in ("unresolved", "multiple"):
        return None
    return image


def _same_image(original: dict, replay: dict) -> bool | None:
    """True or False when the identities decide it, None when they cannot."""
    if original.get("kind") != replay.get("kind"):
        return None
    if original["kind"] == "registry":
        if original.get("digest") and replay.get("digest"):
            return original["digest"] == replay["digest"]
        if original.get("id") and replay.get("id") and original["id"] == replay["id"]:
            return True
        return None                   # local IDs differ between storage drivers and hosts
    if original["kind"] == "file":
        if original.get("sha256") == replay.get("sha256"):
            return True
        # The same cached file with other bytes is another image. A file pulled or converted
        # elsewhere can differ in container-filesystem packaging only, so it is not decidable.
        return False if original.get("path") == replay.get("path") else None
    return None


def completeness_issues(record) -> list[str]:
    """Gaps that prohibit a claim of complete recorded environment evidence.

    This does not discover undeclared dependencies or prove continuous input immutability.
    """
    if not isinstance(record, dict):
        return ["no readable environment object was recorded"]
    issues = []
    if type(record.get("version")) is not int or record["version"] != VERSION:
        issues.append("missing or unsupported environment record version")
    for field in ("nextflow_build", "nextflow_runtime"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            issues.append(f"{field} was not recorded")
    for field, keys in (("container_engine", ("name", "version")),
                        ("host", ("system", "machine"))):
        value = record.get(field)
        if not isinstance(value, dict) or any(
                not isinstance(value.get(key), str) or not value[key].strip() for key in keys):
            issues.append(f"complete {field} evidence was not recorded")
    plugins = record.get("nextflow_plugins")
    if not isinstance(plugins, list) or any(not isinstance(p, str) for p in plugins):
        issues.append("the plugin inventory was not recorded")
    problems = record.get("issues")
    if not isinstance(problems, list) or problems:
        issues.append("the environment recorder reported gaps or has no issue inventory")
    processes, images = record.get("processes"), record.get("images")
    if not isinstance(processes, dict) or not processes:
        issues.append("no complete process inventory was recorded")
    elif not isinstance(images, dict):
        issues.append("no image inventory was recorded")
    else:
        for name, process in processes.items():
            containers = process.get("containers") if isinstance(process, dict) else None
            if (not isinstance(name, str) or not isinstance(containers, list) or not containers
                    or any(not isinstance(image, str) for image in containers)
                    or type(process.get("tasks")) is not int or process["tasks"] <= 0
                    or type(process.get("without_container")) is not int
                    or process["without_container"] != 0):
                issues.append(f"{name}: incomplete or containerless process evidence")
                continue
            for reference in containers:
                image = images.get(reference)
                valid = isinstance(image, dict) and (
                    image.get("kind") == "registry"
                    and any(image.get(key) for key in ("digest", "id"))
                    and all(image.get(key) is None or isinstance(image[key], str)
                            and _DIGEST.fullmatch(image[key]) for key in ("digest", "id"))
                    or image.get("kind") == "file" and isinstance(image.get("sha256"), str)
                    and re.fullmatch(r"[0-9a-f]{64}", image["sha256"]))
                if not valid:
                    issues.append(f"{name}: {reference} has no immutable image identity")
    remote = record.get("remote_inputs")
    if not isinstance(remote, dict):
        issues.append("the remote input inventory was not recorded")
    else:
        for source, entry in remote.items():
            if (not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])):
                issues.append(f"remote input {source}: consumed-byte hash was not recorded")
            elif entry.get("read_by"):
                issues.append(f"remote input {source}: refetched bytes do not establish "
                              "the bytes originally consumed")
    return issues


def compare(original: dict, replay: dict) -> dict:
    """What differs between a recorded execution environment and a replay's."""
    mismatches, unverified, notes = [], [], []
    recorded_plugins = original.get("nextflow_plugins") or []
    replay_plugins = replay.get("nextflow_plugins") or []
    if recorded_plugins != replay_plugins:
        mismatches.append("Nextflow plugins differ: recorded "
                          f"{', '.join(recorded_plugins) or 'none'}; replay "
                          f"{', '.join(replay_plugins) or 'none'}")
    if original.get("nextflow_runtime") != replay.get("nextflow_runtime"):
        notes.append(f"Nextflow runtime differs: recorded {original.get('nextflow_runtime')}; "
                     f"replay {replay.get('nextflow_runtime')}")
    recorded_engine = (original.get("container_engine") or {}).get("name")
    replay_engine = (replay.get("container_engine") or {}).get("name")
    if recorded_engine != replay_engine:
        mismatches.append(f"container engine differs: recorded "
                          f"{recorded_engine}; replay {replay_engine}")
    recorded, replayed = original.get("processes") or {}, replay.get("processes") or {}
    if bool(recorded) != bool(replayed):
        side = "recording" if not recorded else "replay"
        unverified.append(f"the {side} holds no task records to compare containers with"
                          + "".join(f"; {issue}" for issue in
                                    ((original if not recorded else replay).get("issues") or [])))
    for process in sorted(recorded.keys() & replayed.keys()):
        before = [_identity(original.get("images", {}).get(name))
                  for name in recorded[process].get("containers", [])]
        after = [_identity(replay.get("images", {}).get(name))
                 for name in replayed[process].get("containers", [])]
        if not before and not after:
            continue
        if len(before) != len(after) or (bool(before) != bool(after)):
            mismatches.append(f"{process}: ran {len(after)} image(s) where the recording ran "
                              f"{len(before)}")
            continue
        if None in before or None in after:
            unverified.append(f"{process}: the image identity was not recorded in both runs")
            continue
        verdicts = []
        for image in before:
            results = [_same_image(image, other) for other in after]
            verdicts.append(True if True in results else
                            False if all(result is False for result in results) else None)
        if False in verdicts:
            mismatches.append(f"{process}: ran {', '.join(replayed[process]['containers'])}, "
                              f"another image than the recorded "
                              f"{', '.join(recorded[process]['containers'])}")
        elif None in verdicts:
            unverified.append(f"{process}: the image could not be compared across hosts")
    only_recorded = sorted(recorded.keys() - replayed.keys())
    only_replay = sorted(replayed.keys() - recorded.keys())
    if only_recorded:
        notes.append("processes that ran only in the recording: " + ", ".join(only_recorded))
    if only_replay:
        notes.append("processes that ran only in the replay: " + ", ".join(only_replay))
    before_inputs = original.get("remote_inputs") or {}
    after_inputs = replay.get("remote_inputs") or {}
    for source in sorted(before_inputs.keys() & after_inputs.keys()):
        a, b = before_inputs[source], after_inputs[source]
        if "sha256" not in a or "sha256" not in b:
            unverified.append(f"remote input {source}: its staged bytes were not recorded "
                              "in both runs")
        elif a["sha256"] != b["sha256"]:
            mismatches.append(f"remote input {source} changed: recorded sha256 {a['sha256']}, "
                              f"replay staged {b['sha256']}")
    # The same parameters stage the same remote files: one staged by only one run means its
    # inputs differed (a remote samplesheet that changed, another reference URL).
    if before_inputs.keys() - after_inputs.keys():
        mismatches.append("remote inputs staged only in the recording: "
                          + ", ".join(sorted(before_inputs.keys() - after_inputs.keys())))
    if after_inputs.keys() - before_inputs.keys():
        mismatches.append("remote inputs staged only in the replay: "
                          + ", ".join(sorted(after_inputs.keys() - before_inputs.keys())))
    status = "differs" if mismatches else ("unverified" if unverified else "identical")
    return {"version": VERSION, "status": status, "mismatches": mismatches,
            "unverified": unverified, "notes": notes}


def _profile_of(manifest: dict) -> str | None:
    command = manifest.get("command") if isinstance(manifest, dict) else None
    if not isinstance(command, str):
        return None
    match = re.search(r"(?:^|\s)-profile\s+'?([^'\s]+)", command)
    return match[1] if match else None


def verify_replay(bundle: Path, target: Path) -> int:
    """Record a finished replay's environment in its target and compare it with the recording.

    Exit status 0: identical, or not decidable for some entries (reported); 3: it differs.
    """
    try:
        original = json.loads((bundle / RECORD_NAME).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("nfclaw replay: the bundle records no execution environment; nothing to compare")
        return 0
    manifest = {}
    try:
        manifest = json.loads((bundle / "run_manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    log_name = os.environ.get("NXF_LOG_FILE") or ".nextflow.log"
    log_path = Path(log_name) if os.path.isabs(log_name) else target / log_name
    replay = capture(target, log_path=log_path, env=None, profile=_profile_of(manifest))
    result = compare(original, replay)
    output = target / "provenance"
    output.mkdir(parents=True, exist_ok=True)
    for name, data in ((RECORD_NAME, replay), (CHECK_NAME, result)):
        temporary = output / f".{name}.tmp"
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(output / name)
    print(f"nfclaw replay: execution environment {result['status']} "
          f"({len(replay.get('processes') or {})} processes, {len(replay.get('images') or {})} "
          f"images, {len(replay.get('remote_inputs') or {})} remote inputs compared "
          "with the recording)")
    for kind, label in (("mismatches", "mismatch"), ("unverified", "unverified"),
                        ("notes", "note")):
        for line in result[kind]:
            print(f"nfclaw replay: {label}: {line}")
    for issue in replay.get("issues") or []:
        print(f"nfclaw replay: note: {issue}")
    return 3 if result["status"] == "differs" else 0


if __name__ == "__main__":
    try:
        if len(sys.argv) == 4 and sys.argv[1] == "verify":
            sys.exit(verify_replay(Path(sys.argv[2]), Path(sys.argv[3])))
        print("usage: environment_record.py verify <provenance bundle> <replay target>",
              file=sys.stderr)
        sys.exit(2)
    except (OSError, ValueError) as exc:
        print(f"nfclaw replay: execution environment check failed: {exc}", file=sys.stderr)
        sys.exit(1)
