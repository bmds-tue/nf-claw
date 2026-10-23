"""Standalone checksum handling, copied into each provenance bundle for replay guards.

This module deliberately needs only Python's standard library: a recorded replay must not import
whatever version of nfclaw happens to be installed later.
"""
from __future__ import annotations

import errno
import glob
import hashlib
import json
import math
import os
import re
import select
import signal
import socket
import stat
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from functools import partial
from pathlib import Path


def quote_console(data: bytes, at_line_start: bool) -> tuple[bytes, bool]:
    """Prefix each physical child-output line without depending on stream chunk boundaries."""
    if not data:
        return data, at_line_start
    quoted = (b"| " if at_line_start else b"") + data.replace(b"\n", b"\n| ")
    at_line_start = data.endswith(b"\n")
    return (quoted[:-2] if at_line_start else quoted), at_line_start


def stub_caveat(profiles: list[str]) -> str:
    """What a run's results lack when a selected profile runs every task as a stub."""
    names = ", ".join(f"`{name}`" for name in profiles)
    return (f"stub run: the {names} profile sets `stubRun = true`, so every task ran its stub "
            "block and wrote placeholder files instead of running its tool; the outputs hold "
            "no analysis results")


def _recorded_stub_profiles(original: str) -> list[str]:
    try:
        manifest = json.loads((Path(original) / "provenance" / "run_manifest.json")
                              .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    names = manifest.get("stub_profiles") if isinstance(manifest, dict) else None
    return ([name for name in names if isinstance(name, str) and re.fullmatch(r"\w+", name)]
            if isinstance(names, list) else [])


def start_replay_log(log: Path, original: str, pid: str) -> None:
    """Write trusted replay controls independently of arbitrary path text."""
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    stubbed = _recorded_stub_profiles(original)          # a replay runs the same stubs
    original = original.replace("\r", "\\r").replace("\n", "\\n")
    host = socket.gethostname().replace("\r", "\\r").replace("\n", "\\n")
    lines = [f"==> nfclaw replay started {stamp}", "    console format: prefixed",
             f"    replay of: {original}", f"    host: {host}"]
    if identity := host_identity():
        lines.append(f"    host id: {identity}")
    if not pid.isdigit():
        raise ValueError("invalid replay pid")
    lines.append(f"    pid: {pid}")
    if stubbed:
        lines.append(f"    caveat: {stub_caveat(stubbed)}")
    with log.open("a", encoding="utf-8") as handle:
        handle.write("\n" + "\n".join(lines) + "\n")


def host_identity() -> str | None:
    """A hashed machine identity independent of DHCP/DNS hostname changes.

    Linux also includes the PID namespace, since a copied container log's PID
    cannot be inspected from a different namespace. Unknown systems fall back
    to the legacy hostname check; never invent an identity when probing fails.
    """
    identity = None
    if sys.platform == "linux":
        for name in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            try:
                machine = Path(name).read_text(encoding="ascii").strip().lower()
                namespace = Path("/proc/self/ns/pid").stat().st_ino
            except (OSError, UnicodeError):
                continue
            if re.fullmatch(r"[0-9a-f]{32}", machine) and machine != "0" * 32:
                identity = f"{machine}:{namespace}"
                break
    elif sys.platform == "darwin":
        try:
            result = subprocess.run(["/usr/sbin/ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                                    capture_output=True, text=True, timeout=2)
            match = re.search(r'"IOPlatformUUID"\s*=\s*"([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-'
                              r'[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})"', result.stdout)
            if result.returncode == 0 and match and match.group(1).replace("-", "") != "0" * 32:
                identity = match.group(1).lower()
        except (OSError, subprocess.SubprocessError):
            pass
    return (hashlib.sha256(f"nfclaw-host-v1:{sys.platform}:{identity}".encode()).hexdigest()
            if identity is not None else None)


def checksum_text(checksums: dict[str, str]) -> str:
    """GNU checksum records: escape backslashes, LF and CR with a marked digest line."""
    lines = []
    for name, digest in sorted(checksums.items()):
        escaped = name.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")
        marker = "\\" if escaped != name else ""
        lines.append(f"{marker}{digest}  {escaped}\n")
    return "".join(lines)


def read_checksums(path: Path, *, relative: bool = True) -> dict[str, str]:
    """Read a manifest; malformed/duplicate paths raise ValueError, I/O retains OSError."""
    out: dict[str, str] = {}
    # Only LF separates records. Unicode line separators are valid filesystem characters.
    with path.open(encoding="utf-8", newline="") as stream:
        records = stream.read().split("\n")
    if records and records[-1] == "":
        records.pop()
    for number, line in enumerate(records, start=1):
        if line.endswith("\r"):
            line = line[:-1]  # CRLF records; literal terminal CR is escaped by the writer.
        marked = line.startswith("\\")
        if marked:
            line = line[1:]
        digest, separator, name = line.partition("  ")
        if marked:
            decoded = []
            position = 0
            escapes = {"\\": "\\", "n": "\n", "r": "\r"}
            while position < len(name):
                char = name[position]
                if char == "\\":
                    position += 1
                    if position == len(name) or name[position] not in escapes:
                        raise ValueError(f"invalid checksum escape in {path} at line {number}")
                    char = escapes[name[position]]
                decoded.append(char)
                position += 1
            name = "".join(decoded)
        parts = name.split("/")
        absolute = name.startswith("/")
        valid_path = bool(name) and "\x00" not in name and not any(
            p in (".", "") or p == ".." and not absolute
            for p in (parts[1:] if absolute else parts)
        ) and (not absolute if relative else absolute)
        if not separator or not re.fullmatch(r"[0-9a-fA-F]{64}", digest) or not valid_path:
            raise ValueError(f"invalid checksum record in {path} at line {number}")
        if name in out:
            raise ValueError(f"duplicate checksum path {name!r} in {path} at line {number}")
        out[name] = digest.lower()
    return out


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _glob_patterns(pattern: str) -> list[str]:
    """Expand Java/Nextflow brace alternatives and its recursive ``**.ext`` shorthand."""
    if match := re.search(r"\{([^{}]+)\}", pattern):
        return [expanded for option in match[1].split(",")
                for expanded
                in _glob_patterns(pattern[:match.start()] + option + pattern[match.end():])]
    return [re.sub(r"(?<=/)\*\*(?=[^/])", "**/*", pattern)]


class MissingInputSource(FileNotFoundError):
    """A top-level source is absent, distinct from an incomplete source inventory."""


def _input_inventory(paths: list[Path], visit: Callable[[Path], None] | None,
                     retain_files: bool) -> list[Path]:
    files: set[Path] = set()

    def walk(directory: Path, ancestors: frozenset[Path]) -> None:
        real = directory.resolve()
        if real in ancestors:
            raise OSError(errno.ELOOP, "cyclic input directory symlink", str(directory))
        with os.scandir(directory) as entries:
            for entry in sorted(entries, key=lambda e: e.name):
                item = directory / entry.name
                if visit is not None:
                    visit(item)
                if entry.is_dir(follow_symlinks=True):
                    walk(item, ancestors | {real})
                elif entry.is_file(follow_symlinks=True):
                    if retain_files:
                        files.add(item)
                else:
                    raise FileNotFoundError(f"input is missing or not a regular file: {item}")

    for source in paths:
        source = source.expanduser().absolute()
        pattern = str(source)
        if source.exists() or source.is_symlink():
            matches = [source]
        elif glob.has_magic(pattern) or "{" in pattern:
            matches = sorted({Path(p) for expanded in _glob_patterns(pattern)
                              for p in glob.glob(expanded, recursive=True)})
        else:
            raise MissingInputSource(f"input source is missing: {source}")
        if not matches:
            raise MissingInputSource(f"input pattern matches no files: {source}")
        for path in matches:
            if visit is not None:
                visit(path)
            if path.is_file():
                if retain_files:
                    files.add(path)
            elif path.is_dir():
                # Track ancestors per branch, not a global set of resolved directories: a second
                # published alias is a second logical input path and can change sample multiplicity.
                walk(path, frozenset())
            else:
                raise FileNotFoundError(f"input is missing or not a regular file: {path}")
    return sorted(files)


def input_files(paths: list[Path]) -> list[Path]:
    """Expand explicit files, directories and globs, with cycle-safe symlink traversal."""
    return _input_inventory(paths, None, True)


def inspect_input_paths(paths: list[Path], visit: Callable[[Path], None]) -> None:
    """Visit matched paths and every directory entry, including empty directories.

    Uses the same traversal and error handling as the replay inventory, without retaining a second
    file list or reading data bytes. A visitor can refuse an unsafe staged name immediately.
    """
    _input_inventory(paths, visit, False)


def hash_inputs(paths: list[Path]) -> dict[str, str]:
    """Content snapshot of local sources, including directory and glob contents."""
    return {str(path): _sha256(path) for path in input_files(paths)}


def _capture_input_inventory(paths: list[Path]) -> tuple[list[Path], dict[str, dict[str, str]]]:
    inventory = {}

    def record(path: Path):
        if path.is_dir():
            entry = {"type": "directory"}
        elif path.is_file():
            entry = {"type": "file"}
        else:
            raise FileNotFoundError(f"input is missing or not a regular file: {path}")
        if path.is_symlink():
            entry["link_target"] = os.readlink(path)
        resolved = str(path.resolve())
        if resolved != str(path):
            entry["resolved_path"] = resolved
        inventory[str(path)] = entry

    files = _input_inventory(paths, record, True)
    return files, dict(sorted(inventory.items()))


def snapshot_inputs(paths: list[Path]) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """Capture file bytes and the logical input namespace, including empty directory aliases."""
    files, inventory = _capture_input_inventory(paths)
    digests = {}
    checksums = {}
    for path in files:
        real = Path(inventory[str(path)].get("resolved_path", str(path)))
        if real not in digests:
            digests[real] = _sha256(real)
        checksums[str(path)] = digests[real]
    return checksums, inventory


def read_input_inventory(path: Path) -> dict[str, dict[str, str]]:
    """Read a namespace record without silently accepting duplicate or malformed entries."""
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError(f"duplicate inventory key {key!r} in {path}")
            obj[key] = value
        return obj

    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    if not isinstance(data, dict):
        raise ValueError(f"invalid input inventory in {path}")

    def absolute_name(value):
        return (isinstance(value, str) and value.startswith("/") and "\x00" not in value
                and (value == "/" or not any(part in ("", ".") for part in value.split("/")[1:])))

    for name, entry in data.items():
        if (not absolute_name(name)
                or not isinstance(entry, dict) or entry.get("type") not in ("file", "directory")
                or set(entry) - {"type", "link_target", "resolved_path"}
                or ("resolved_path" in entry and not absolute_name(entry["resolved_path"]))
                or ("link_target" in entry and (not isinstance(entry["link_target"], str)
                                                or not entry["link_target"]
                                                or "\x00" in entry["link_target"]))):
            raise ValueError(f"invalid input inventory entry {name!r} in {path}")
    return data


def check_replay_destination(bundle: Path, target: Path) -> None:
    """Refuse writing locks, logs or results into a recorded scientific input directory."""
    inventory = read_input_inventory(bundle / "inputs.inventory.json")
    target = target.expanduser().resolve()
    for name, entry in inventory.items():
        if entry["type"] == "directory":
            roots = {Path(entry.get("resolved_path", name)), Path(name).resolve()}
            if any(target.is_relative_to(root) for root in roots):
                raise ValueError(f"replay output directory {target} overlaps recorded input "
                                 f"directory {name}; choose a separate output directory")


def pipeline_head(repo: Path) -> str | None:
    """HEAD only when repo is the exact working-tree root, never a surrounding repository."""
    try:
        result = subprocess.run(["git", "-C", str(repo), "rev-parse", "--show-toplevel", "HEAD"],
                                capture_output=True, check=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    # Decode raw filesystem bytes without newline translation; only the last LF frames HEAD.
    lines = os.fsdecode(result.stdout).rstrip("\n").rsplit("\n", 1)
    if len(lines) == 2 and Path(lines[0]).resolve() == repo.resolve():
        return lines[1]
    return None


def hash_pipeline(repo: Path) -> dict[str, str]:
    """Snapshot every tracked source file's working bytes, including dirty modifications.

    For fixtures without their own git repository, snapshot the directory contents except .git.
    Tracked inventory changes are detected even if HEAD stays unchanged.
    """
    if pipeline_head(repo) is not None:
        result = subprocess.run(["git", "-C", str(repo), "ls-files", "--cached", "-z"],
                                capture_output=True, text=True, check=True, timeout=30)
        paths = [repo / name for name in result.stdout.split("\x00") if name]
    else:
        paths = [path for path in input_files([repo]) if ".git" not in path.relative_to(repo).parts]
    return {path.relative_to(repo).as_posix(): _sha256(path) for path in sorted(set(paths))}


PIPELINE_ARCHIVE = "pipeline-source.tar.gz"
# Bundle files written after the run whose bytes the manifest records: the execution environment
# (container identities, plugins, remote inputs) and the container pins a replay passes with `-c`.
RECORDED_FILES = {"environment_record": "environment.json", "container_pins": "containers.config"}


def write_pipeline_archive(repo: Path, checksums: dict[str, str], destination: Path) -> str:
    """Archive exactly the pipeline source bytes recorded in `checksums`; return the archive digest.

    Every member is a regular file with a fixed owner, time and mode, in sorted order, inside a
    gzip stream without a timestamp: the same source always yields the same archive bytes. A file
    whose bytes no longer match its prelaunch checksum is refused, so the archive never holds code
    other than the code that ran. Tracked symlinks are stored as the content they resolved to.
    """
    import gzip
    import io
    import tarfile
    import tempfile

    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=f".{destination.name}.",
                                         delete=False) as raw:
            temporary = Path(raw.name)
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as gz:
                with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
                    for name in sorted(checksums):
                        path = repo / name
                        data = path.read_bytes()
                        if hashlib.sha256(data).hexdigest() != checksums[name]:
                            raise ValueError(f"pipeline source changed since launch: {path}")
                        info = tarfile.TarInfo(name)
                        info.size = len(data)
                        info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                        info.mtime = 0
                        info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        tar.addfile(info, io.BytesIO(data))
        digest = _sha256(temporary)
        temporary.replace(destination)
        temporary = None
        return digest
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _recorded_file(bundle: Path, manifest: dict, key: str, name: str) -> Path | None:
    """A bundle file the manifest records by digest, verified; None when none is recorded."""
    record = manifest.get(key)
    if record is None:
        return None
    if (not isinstance(record, dict) or record.get("file") != name
            or not isinstance(record.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])):
        raise ValueError(f"invalid {key} record in the run manifest")
    path = bundle / name
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"provenance bundle is incomplete: {name} is missing")
    if _sha256(path) != record["sha256"]:
        raise ValueError(f"recorded bundle file changed: {name}")
    return path


def check_pipeline_archive(bundle: Path, manifest: dict, destination: Path | None = None) -> None:
    """Verify every archived source file against pipeline.sha256; optionally extract it.

    The archive must hold exactly the recorded files, each with its recorded digest. Extraction
    creates `destination` (which must not exist) and writes only those relative paths into it.
    """
    import tarfile

    archive = _recorded_file(bundle, manifest, "pipeline_archive", PIPELINE_ARCHIVE)
    if archive is None:
        raise ValueError("the bundle holds no pipeline source archive")
    expected = read_checksums(bundle / "pipeline.sha256")
    if destination is not None:
        destination.mkdir(parents=True)
    seen = set()
    with tarfile.open(archive, mode="r:gz") as tar:
        for member in tar:
            name = member.name
            if not member.isreg() or name not in expected or name in seen:
                raise ValueError(f"unexpected entry in the pipeline source archive: {name!r}")
            stream = tar.extractfile(member)
            digest = hashlib.sha256()
            target = None
            output = None
            if destination is not None:
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                output = open(target, "xb")
            try:
                for chunk in iter(partial(stream.read, 1024 * 1024), b""):
                    digest.update(chunk)
                    if output is not None:
                        output.write(chunk)
            finally:
                if output is not None:
                    output.close()
            if target is not None:
                os.chmod(target, 0o755 if member.mode & 0o111 else 0o644)
            if digest.hexdigest() != expected[name]:
                raise ValueError(f"archived pipeline source differs from its checksum: {name}")
            seen.add(name)
    if missing := sorted(expected.keys() - seen):
        raise ValueError(f"the pipeline source archive is incomplete; missing: {missing[:5]}")


def _bundled_configs(manifest: dict) -> dict[str, dict]:
    """External `-c` configs copied into the bundle, by their original absolute path."""
    bundled = manifest.get("bundled_configs", {})
    if not isinstance(bundled, dict):
        raise ValueError("invalid bundled configs in the run manifest")
    for original, entry in bundled.items():
        file = entry.get("file") if isinstance(entry, dict) else None
        if (not isinstance(original, str) or not original.startswith("/")
                or not isinstance(file, str) or not re.fullmatch(r"configs/[^/\x00]+", file)
                or file in ("configs/.", "configs/..") or type(entry.get("replay")) is not bool):
            raise ValueError(f"invalid bundled config record for {original!r}")
    return bundled


def check_pipeline_checkout(bundle: Path, manifest: dict) -> None:
    """The recorded pipeline checkout still holds exactly the recorded revision and source bytes."""
    repo = Path(manifest["pipeline_path"])
    if not repo.is_dir():
        raise ValueError(f"pipeline checkout is missing: {repo}")
    if (expected_head := manifest.get("pipeline_git_head")) is not None \
            and pipeline_head(repo) != expected_head:
        raise ValueError(f"pipeline revision changed: {repo} (expected {expected_head})")
    expected = read_checksums(bundle / "pipeline.sha256")
    try:
        current = hash_pipeline(repo)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError(f"pipeline source is unreadable: {repo} ({exc})") from exc
    if current.keys() != expected.keys():
        raise ValueError(f"pipeline source inventory changed: {repo}")
    for name, digest in expected.items():
        if current[name] != digest:
            raise ValueError(f"pipeline source content changed: {repo / name}")


PIPELINE_SOURCE_RECORD = "pipeline-source.json"


def replay_pipeline_source(target: Path) -> dict | None:
    try:
        record = json.loads(
            (target / "provenance" / PIPELINE_SOURCE_RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) else None


def choose_pipeline_source(bundle: Path, target: Path) -> str:
    """The pipeline directory a replay runs, recorded in the replay's provenance.

    The recorded checkout, while it still holds exactly the recorded revision and source bytes: the
    replay then runs from the same path, so parameters and outputs that embed the pipeline directory
    (nf-core's `${projectDir}/assets/...` defaults) keep their values. Otherwise the bundle's source
    archive, extracted and checked file by file into the replay's provenance/pipeline.
    """
    manifest = json.loads((bundle / "run_manifest.json").read_text(encoding="utf-8"))
    reason = None
    try:
        check_pipeline_checkout(bundle, manifest)
        source = {"from": "checkout", "path": manifest["pipeline_path"]}
    except (ValueError, KeyError) as exc:
        reason = str(exc)
        destination = target / "provenance" / "pipeline"
        check_pipeline_archive(bundle, manifest, destination)
        source = {"from": "archive", "path": str(destination), "reason": reason}
    record = target / "provenance" / PIPELINE_SOURCE_RECORD
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if reason is None:
        print(f"nfclaw replay: running the recorded pipeline checkout {source['path']}",
              file=sys.stderr)
    else:
        print(f"nfclaw replay: running the bundle's pipeline source archive ({reason})",
              file=sys.stderr)
    return source["path"]


def verify_dependencies(bundle: Path, replay_target: Path | None = None) -> None:
    """Require the recorded local input inventory and config bytes before replay starts.

    With `replay_target` (a finished replay), the pipeline checkout the replay ran is checked too.
    """
    manifest = json.loads((bundle / "run_manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("outcome"), str):
        raise ValueError(f"provenance bundle is incomplete: {bundle}")
    stability = manifest.get("dependency_stability")
    if stability is not None:
        if (not isinstance(stability, dict) or type(stability.get("version")) is not int
                or stability["version"] != 1
                or stability.get("status") not in {"unchanged", "changed", "not_checked"}):
            raise ValueError("invalid dependency stability record")
        if stability["status"] == "changed":
            raise ValueError("local dependencies changed or could not be verified during the "
                             "original run; these outputs have no verified launch-input "
                             "attribution. Start a fresh run.")
    if type(manifest.get("dependency_inventory_version")) is not int \
            or manifest["dependency_inventory_version"] != 1:
        raise ValueError("dependency inventory version is missing or unsupported; "
                         "a fresh run with complete directory provenance is required")
    unverified = manifest.get("unverified_dependency_inventories", [])
    if not isinstance(unverified, list) or any(kind not in ("inputs", "configs")
                                               for kind in unverified):
        raise ValueError("invalid unverified dependency inventories in the run manifest")
    if manifest.get("unverified_engine"):
        raise ValueError("the engine version was neither observed nor pinned; "
                         "replay on a moving default is refused")
    if manifest.get("unreplayable_environment_names"):
        raise ValueError("recorded environment names are not valid shell identifiers; "
                         "restore a valid environment and start a fresh run")
    for key, name in RECORDED_FILES.items():
        _recorded_file(bundle, manifest, key, name)
    if manifest.get("pipeline_archive") is not None:
        # The replay runs the archived source, so the original checkout may have moved on.
        check_pipeline_archive(bundle, manifest)
    elif manifest.get("pipeline_path"):
        check_pipeline_checkout(bundle, manifest)
    # After a replay: the source it ran must still be the recorded source.
    if replay_target is not None:
        used = replay_pipeline_source(replay_target)
        if used is not None and used.get("from") == "checkout":
            check_pipeline_checkout(bundle, manifest)
    for kind in ("inputs", "configs"):
        expected = read_checksums(bundle / f"{kind}.sha256", relative=False)
        sources = json.loads((bundle / f"{kind}.sources.json").read_text(encoding="utf-8"))
        if not isinstance(sources, list) or not all(isinstance(p, str) for p in sources):
            raise ValueError(f"invalid {kind} sources in {bundle}")
        # Keep original logical checksum keys, but find moved internal configs in this bundle.
        recorded_bundle = None
        if kind == "configs" and isinstance(manifest.get("outdir"), str):
            recorded_bundle = Path(manifest["outdir"]) / "provenance"
            original_real = manifest.get("provenance_real_path")
            if not isinstance(original_real, str) or not Path(original_real).is_absolute():
                raise ValueError("the recorded provenance directory identity is missing or invalid")
        # External configs replayed from their bundle copies: the copy stands in for the original,
        # which a replay no longer reads (it may have been moved or edited since the run).
        replayed = (
            {source for source, entry in _bundled_configs(manifest).items() if entry["replay"]}
            if kind == "configs" else set())
        current_files = {}
        current_inventory = {}
        for source in sources:
            path = Path(source)
            if source in replayed:
                copy = bundle / _bundled_configs(manifest)[source]["file"]
                if not copy.is_file() or copy.is_symlink():
                    raise ValueError(f"provenance bundle is incomplete: {copy.name} is missing")
                current_files[source] = copy
                current_inventory[source] = {"type": "file"}
                continue
            relocated = path
            if recorded_bundle is not None and path.is_relative_to(recorded_bundle):
                relocated = bundle / path.relative_to(recorded_bundle)
            files, nodes = _capture_input_inventory([relocated])
            for name, entry in nodes.items():
                current = Path(name)
                logical = (recorded_bundle / current.relative_to(bundle)
                           if relocated != path else current)
                if relocated != path:
                    real = Path(entry.get("resolved_path", name))
                    current_real = bundle.resolve()
                    if real.is_relative_to(current_real):
                        rebased = str(Path(original_real) / real.relative_to(current_real))
                        entry = dict(entry)
                        if rebased != str(logical):
                            entry["resolved_path"] = rebased
                        else:
                            entry.pop("resolved_path", None)
                current_inventory[str(logical)] = entry
            for current in files:
                logical = (recorded_bundle / current.relative_to(bundle)
                           if relocated != path else current)
                current_files[str(logical)] = current
        missing = sorted(expected.keys() - current_files.keys())
        extra = sorted(current_files.keys() - expected.keys())
        if missing or extra:
            raise ValueError(f"{kind} inventory changed; missing: {missing}; extra: {extra}")
        digests = {}
        for name, path in current_files.items():
            real = path.resolve()
            if real not in digests:
                digests[real] = _sha256(real)
            if digests[real] != expected[name]:
                raise ValueError(f"recorded {kind} content changed: {name}")
        if kind in unverified:
            raise ValueError(f"prelaunch {kind} directory inventory was not captured; "
                             "start a fresh run")
        inventory = read_input_inventory(bundle / f"{kind}.inventory.json")
        if ({name for name, entry in inventory.items() if entry["type"] == "file"}
                != expected.keys()):
            raise ValueError(f"{kind} inventory disagrees with its recorded file checksums")
        # A bundle copy is a regular file holding the recorded bytes; the original's link identity
        # belongs to a path the replay does not read.
        inventory = {name: ({"type": entry["type"]} if name in replayed else entry)
                     for name, entry in inventory.items()}
        if inventory != current_inventory:
            missing = sorted(inventory.keys() - current_inventory.keys())
            extra = sorted(current_inventory.keys() - inventory.keys())
            changed = sorted(name for name in inventory.keys() & current_inventory.keys()
                             if inventory[name] != current_inventory[name])
            raise ValueError(f"{kind} directory inventory changed; missing: {missing}; "
                             f"extra: {extra}; type or link changed: {changed}")


def _stop_replay_group(proc: subprocess.Popen, grace: float = 10) -> None:
    """Give the replay's tasks a shutdown grace period, then stop all survivors."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        proc.wait()
        return
    deadline = time.monotonic() + grace
    try:
        while time.monotonic() < deadline:
            proc.poll()  # Reap the leader without assuming its tasks have also exited.
            try:
                os.killpg(proc.pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=2)


def run_replay_command(command: list[str], *, log: Path, grace: float = 10) -> int:
    """Run a replay in its own process group while the outer shell holds its lock.

    The shell signals this controller. Recording the signal before polling avoids
    exceptions between process creation and ownership registration. Descendants
    are stopped even when the leader exits first or handles SIGTERM with exit zero.
    """
    if not math.isfinite(grace) or grace <= 0:
        raise ValueError("shutdown grace must be a finite positive number of seconds")
    requested_stop = None

    def request_stop(signum, _frame):
        nonlocal requested_stop
        if requested_stop is None:
            requested_stop = signum

    handlers = {sig: signal.signal(sig, request_stop)
                for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)}
    proc = None
    reader = None
    console_log = None
    reader_done = threading.Event()
    reader_errors = []
    status = 1

    def copy_output():
        at_line_start = True
        while True:
            readable, _, _ = select.select([proc.stdout], [], [], 0.1)
            if not readable:
                if reader_done.is_set():
                    break
                continue
            chunk = os.read(proc.stdout.fileno(), 64 * 1024)
            if not chunk:
                break
            quoted, at_line_start = quote_console(chunk, at_line_start)
            for handle, content in ((console_log, quoted), (sys.stdout.buffer, chunk)):
                try:
                    handle.write(content)
                    handle.flush()
                except OSError as exc:
                    if not reader_errors:
                        reader_errors.append(str(exc))
        if not at_line_start:
            try:
                console_log.write(b"\n")
                console_log.flush()
            except OSError as exc:
                if not reader_errors:
                    reader_errors.append(str(exc))

    try:
        # Write the header before launching anything that can produce console output.
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"    replay supervisor pid: {os.getpid()}\n")
        if requested_stop is None:
            console_log = log.open("ab")
            proc = subprocess.Popen(command, start_new_session=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            reader = threading.Thread(target=copy_output, daemon=True)
            reader.start()
            while requested_stop is None:
                try:
                    status = proc.wait(timeout=0.1)
                    break
                except subprocess.TimeoutExpired:
                    continue
        if requested_stop is not None:
            status = 128 + requested_stop
        elif status < 0:
            status = 128 - status
    finally:
        try:
            if proc is not None:
                _stop_replay_group(proc, grace=grace)
        finally:
            reader_done.set()
            if reader is not None:
                reader.join(timeout=5)
                if reader.is_alive():
                    reader_errors.append("console forwarding did not stop")
            if console_log is not None and (reader is None or not reader.is_alive()):
                console_log.close()
            for sig, handler in handlers.items():
                signal.signal(sig, handler)
    if requested_stop is not None:
        status = 128 + requested_stop
    if reader_errors:
        print("nfclaw replay: could not retain or forward console output", file=sys.stderr)
        return status or 1
    return status


def lock_replay(target: Path, script: Path) -> None:
    """Hold the runner's sibling flock across exec of the replay shell, with no extra parent.

    The shell keeps the inherited descriptor until its traps, logs and tasks have finished.
    Using exactly the runner's lock prevents replay/replay and replay/run writer races.
    """
    import fcntl

    target = target.expanduser().resolve()
    # This precedes parent creation and the sibling lock: either would otherwise alter an input
    # directory before the dependency guard has even run. Non-bundle lock fixtures remain valid.
    if (script.parent / "run_manifest.json").exists():
        check_replay_destination(script.parent, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = target.parent / f".{target.name}.nfclaw.lock"
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError(f"another nfclaw run or replay is active in {target}") from None
        os.set_inheritable(fd, True)
        env = {**os.environ, "NFCLAW_REPLAY_LOCK_PID": str(os.getpid()),
               "NFCLAW_REPLAY_LOCK_FD": str(fd)}
        os.execvpe("bash", ["bash", str(script), str(target)], env)
    finally:
        os.close(fd)


def replay_lock_held(target: Path, shell_pid: str) -> bool:
    """Validate the inherited lock itself; an environment PID is not ownership proof."""
    import fcntl

    if os.environ.get("NFCLAW_REPLAY_LOCK_PID") != shell_pid:
        return False
    probe = None
    try:
        fd = int(os.environ.get("NFCLAW_REPLAY_LOCK_FD", ""))
        if fd < 3:
            return False
        target = target.expanduser().resolve()
        lock = target.parent / f".{target.name}.nfclaw.lock"
        probe = os.open(lock, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        inherited, expected = os.fstat(fd), os.fstat(probe)
        if not stat.S_ISREG(inherited.st_mode) or (inherited.st_dev, inherited.st_ino) != (
                expected.st_dev, expected.st_ino):
            return False
        # A competing writer blocks the inherited descriptor. A separately opened descriptor
        # must then conflict with our inherited lock, even within the same process.
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        return False
    except (OSError, ValueError, OverflowError):
        return False
    finally:
        if probe is not None:
            os.close(probe)


if __name__ == "__main__":
    try:
        if sys.argv[1] == "--host-id":
            print(host_identity() or "")
        elif sys.argv[1] == "--log-start":
            start_replay_log(Path(sys.argv[2]), sys.argv[3], sys.argv[4])
        elif sys.argv[1] == "--lock":
            lock_replay(Path(sys.argv[2]), Path(sys.argv[3]))
        elif sys.argv[1] == "--check-lock":
            sys.exit(0 if replay_lock_held(Path(sys.argv[2]), sys.argv[3]) else 1)
        elif sys.argv[1] == "--run":
            if sys.argv[3:4] == ["--shutdown-grace"]:
                sys.exit(run_replay_command(sys.argv[5:], log=Path(sys.argv[2]),
                                            grace=float(sys.argv[4])))
            sys.exit(run_replay_command(sys.argv[3:], log=Path(sys.argv[2])))
        elif sys.argv[1] == "--pipeline-source":
            try:
                print(choose_pipeline_source(Path(sys.argv[2]), Path(sys.argv[3])))
            except (OSError, ValueError) as exc:
                print(f"nfclaw replay: the recorded pipeline source could not be restored: {exc}",
                      file=sys.stderr)
                sys.exit(1)
        else:
            verify_dependencies(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else None)
    except (OSError, ValueError, IndexError) as exc:
        print(f"nfclaw replay: dependency check failed: {exc}", file=sys.stderr)
        sys.exit(1)
