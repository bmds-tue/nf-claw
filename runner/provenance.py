from __future__ import annotations

import csv
import hashlib
import math
import os
import platform
import re
import shlex
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from runner import budget, environment_record, outputs, sheetgen
from runner import exact_json as json
from runner.engine_version import version_text
from runner.errors import ErrorCode, NfclawError
from runner.inputs import is_remote_url
from runner.outputs import result_files
from runner.probes import capture
# Re-exported (`X as X`): callers read the bundle's checksum helpers from this module.
from runner.replay_guard import (PIPELINE_ARCHIVE, write_pipeline_archive,
                                 MissingInputSource as MissingInputSource,
                                 checksum_text as checksum_text,
                                 hash_inputs as hash_inputs, hash_pipeline as hash_pipeline,
                                 input_files as input_files,
                                 snapshot_inputs as snapshot_inputs,
                                 read_input_inventory as read_input_inventory,
                                 read_checksums as read_checksums)
from runner.samplesheet import delimiter_for, serialized_rows
from runner.schema import InputSchema
from runner.settings import seconds
from runner.submodule import SubmoduleStatus


_SENSITIVE_KEY_PARTS = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "API_KEY",
                        "ACCESS_KEY", "PRIVATE_KEY", "AUTH")
_SENSITIVE_VALUE_RE = re.compile(
    r"(?i)(?:token|secret|password|credential|api[_-]?key|access[_-]?key|private[_-]?key)\s*[=:]"
)
_URI_CREDENTIALS_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^/\s?#]*@")
# The standalone scripts a bundle carries, read once with the code that writes `commands.sh`: an
# nfclaw upgraded while a long run goes on must not pair the old script with the new helpers.
_BUNDLED_SCRIPTS = {name: Path(__file__).with_name(name).read_bytes()
                    for name in ("replay_guard.py", "environment_record.py")}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def samplesheet_input_paths(path: Path, schema: InputSchema) -> list[Path]:
    """Local data sources in schema-declared CSV/TSV or flat JSON/YAML path fields.

    Remote URLs and nested or pipeline-specific inputs need separate identity handling and are not
    guessed. The sheet has already been validated by the runner, including its
    absolute-path requirement.
    """
    columns = [column for column in schema.columns
               if column.path_format()
               and column.name not in {*schema.destination_columns, *schema.metadata_columns}]
    paths: set[Path] = set()
    if path.suffix.lower() not in (".csv", ".tsv"):
        for row in serialized_rows(path) or []:
            for column in columns:
                value = row.get(column.name)
                if isinstance(value, str) and value:
                    paths.update(Path(part) for part in column.path_values(value, row)
                                 if not is_remote_url(part))
        return sorted(paths)
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream, delimiter=delimiter_for(path), strict=True):
            for column in columns:
                value = (row.get(column.name) or "").strip()
                if value:
                    paths.update(Path(part) for part in column.path_values(value, row)
                                 if not is_remote_url(part))
    return sorted(paths)


def samplesheet_file_paths(path: Path, schema: InputSchema) -> list[Path]:
    """Local data a samplesheet names outside its path-format fields.

    Some pinned schemas type data columns by their pattern alone (hic's `fastq_1`, phaseimpute's
    `vcf`), and some parsers read columns the schema leaves undeclared (hgtseq's `input1`). Their
    bytes are part of the run's inputs too: record an existing absolute value of a file-typed
    column (file or directory) and an existing absolute regular file in any other column. Relative
    and remote values are not guessed at, and a missing file stays the pipeline's own error.
    """
    declared = {column.name for column in schema.columns if column.path_format()}
    declared.update(schema.destination_columns)
    declared.update(schema.metadata_columns)
    typed = set(sheetgen.file_columns(schema))
    if path.suffix.lower() in (".csv", ".tsv"):
        with path.open(newline="", encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream, delimiter=delimiter_for(path), strict=True))
    else:
        rows = serialized_rows(path) or []
    paths: set[Path] = set()
    for row in rows:
        for column, value in (row.items() if isinstance(row, dict) else ()):
            if column in declared or not isinstance(value, str):
                continue
            value = value.strip()
            if not value or "://" in value or not Path(value).is_absolute():
                continue
            candidate = Path(value)
            if candidate.is_file() or (column in typed and candidate.is_dir()):
                paths.add(candidate)
    return sorted(paths)


def samplesheet_dependencies(path: Path, schema: InputSchema) -> list[Path]:
    """The same local dependency boundary for run snapshots and producer handoffs.

    Effective path roles and conservative existing-file capture are combined after
    source-guarded metadata/destination exclusions; neither side may omit a member.
    """
    return sorted(set(samplesheet_input_paths(path, schema))
                  | set(samplesheet_file_paths(path, schema)))


def _atomic_bytes(path: Path, content: bytes, *, mode: int | None = None) -> None:
    """Replace one bundle file without exposing a truncated write."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.",
                                         delete=False) as fh:
            temporary = Path(fh.name)
            fh.write(content)
        if mode is not None:
            temporary.chmod(mode)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _atomic_text(path: Path, content: str, *, mode: int | None = None) -> None:
    _atomic_bytes(path, content.encode("utf-8"), mode=mode)


def mark_timed_out(outdir: Path, timeout_seconds: float) -> None:
    """Downgrade completed success metadata without repeating the scientific inventories."""
    path = outdir / "provenance" / "run_manifest.json"
    if not path.is_file():
        return
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(manifest, dict) and manifest.get("outcome") == "success":
        manifest.update(outcome="failed", timeout_seconds=timeout_seconds)
        try:
            _atomic_text(path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        except OSError:
            # If failed metadata cannot be published, absence refuses verification too; an old
            # success must not survive a full disk during this small final correction.
            path.unlink(missing_ok=True)
            raise


def _nextflow_version(env_extra: dict[str, str] | None = None) -> str:
    # Probe with the same env overlay the run used, so a pinned NXF_VER reports the version that
    # actually ran, not the launcher default.
    env = {**os.environ, **env_extra} if env_extra else None
    try:
        r = capture(["nextflow", "-version"],
                    timeout=seconds("NFCLAW_VERSION_TIMEOUT", 30), env=env)
        return version_text(r) or ""
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return ""


def _sensitive_env(key: str, value: str) -> bool:
    upper = key.upper()
    return (any(part in upper for part in _SENSITIVE_KEY_PARTS)
            or bool(_SENSITIVE_VALUE_RE.search(value))
            or bool(_URI_CREDENTIALS_RE.search(value)))


def safe_env(env: dict[str, str] | None) -> tuple[dict[str, str], list[str]]:
    """Return provenance-safe values and the names whose values were redacted."""
    recorded: dict[str, str] = {}
    redacted: list[str] = []
    for key, value in sorted((env or {}).items()):
        if _sensitive_env(key, value):
            recorded[key] = "<redacted>"
            redacted.append(key)
        else:
            recorded[key] = value
    return recorded, redacted


def effective_nxf_env(env_extra: dict[str, str] | None = None) -> dict[str, str]:
    """Every NXF_* variable the run actually saw: inherited from the shell, then the overlay.

    Nextflow reads its settings from the ambient environment, so an exported NXF_OFFLINE or NXF_VER
    shapes the run just as much as `--nxf-env`/`--nxf-ver` does. Recording only the overlay would
    leave the replay script silently missing whatever made the run work.
    """
    env = {k: v for k, v in os.environ.items() if k.startswith("NXF_")}
    env.update(env_extra or {})        # the overlay wins, exactly as it does at launch
    return env


def _profile(command_str: str) -> str | None:
    try:
        args = shlex.split(command_str)
    except ValueError:
        return None
    return next((args[i + 1] for i, arg in enumerate(args[:-1]) if arg == "-profile"), None)


def _bundle_configs(prov: Path, command_str: str,
                    config_checksums: dict[str, str] | None) -> dict[str, dict]:
    """Copy each external `-c` config into `<bundle>/configs/`, keyed by its original path.

    A replay passes the copy, so it no longer depends on the file staying where it was. A copy is
    taken only when its bytes still match the prelaunch snapshot. A config that includes others
    (`includeConfig`) resolves relative includes against its own directory, so it is kept for the
    record but replayed from its original path, where those includes still resolve.
    """
    directory = prov / "configs"
    if directory.is_dir():
        for stale in directory.iterdir():
            if stale.is_file() and not stale.is_symlink():
                stale.unlink()
    try:
        args = shlex.split(command_str)
    except ValueError:
        return {}
    if not args or Path(args[0]).name != "nextflow":
        return {}
    bundle = prov.absolute()
    bundled: dict[str, dict] = {}
    for index, arg in enumerate(args[1:-1], start=1):
        if arg not in ("-c", "-config"):
            continue
        source = Path(args[index + 1]).expanduser().absolute()
        key = str(source)
        if source.is_relative_to(bundle) or key in bundled:
            continue
        try:
            data = source.read_bytes()
        except OSError:
            continue
        digest = hashlib.sha256(data).hexdigest()
        if config_checksums is not None and config_checksums.get(key) != digest:
            continue
        directory.mkdir(exist_ok=True)
        name = f"configs/{len(bundled) + 1:02d}-{source.name}"
        _atomic_bytes(prov / name, data)
        text = data.decode("utf-8", errors="replace")
        bundled[key] = {"file": name, "sha256": digest,
                        "replay": not re.search(r"\bincludeConfig\b", text)}
    return bundled


def record_environment(outdir: Path, *, env_extra: dict[str, str] | None,
                       history_offset: int | None, profile: str | None,
                       nextflow_log: Path | None,
                       observed: dict[str, list[dict]] | None = None) -> dict:
    """The execution environment of the run (runner.environment_record); never raises.

    The record of an earlier attempt in this outdir (a resumed run) still names the images its
    cached tasks ran: it is the fallback for an image the engine no longer has.
    """
    from runner import runlog

    try:
        previous = json.loads((outdir / "provenance" / environment_record.RECORD_NAME)
                              .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = None
    # An opt-in --timeout bounds this recording too; the bundle notes what it did not reach.
    try:
        left = budget.remaining()
    except NfclawError:
        left = 0.0
    try:
        return environment_record.capture(
            outdir, log_path=nextflow_log or runlog.nextflow_log_path(outdir, env_extra),
            env={**os.environ, **env_extra} if env_extra else None,
            history_offset=history_offset, profile=profile, observed=observed,
            previous=previous if isinstance(previous, dict) else None,
            deadline=None if left is None else time.monotonic() + left)
    except Exception as exc:                  # a recording gap must not lose the rest of the bundle
        return {"version": environment_record.VERSION, "processes": {}, "images": {},
                "pinned_containers": {}, "remote_inputs": {}, "nextflow_plugins": [],
                "issues": [f"the execution environment could not be recorded: "
                           f"{type(exc).__name__}: {exc}"]}


def recorded_environment_issues(outdir: Path) -> list[str]:
    try:
        environment = json.loads((outdir / "provenance" / environment_record.RECORD_NAME)
                                 .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    issues = environment.get("issues") if isinstance(environment, dict) else None
    return [issue for issue in issues if isinstance(issue, str)] if isinstance(issues, list) else []


def environment_summary(environment: dict) -> dict:
    """The manifest's overview of environment.json."""
    images = environment.get("images") or {}
    engine = environment.get("container_engine") or {}
    return {
        "container_engine": engine.get("name"),
        "container_engine_version": engine.get("version"),
        "images": len(images),
        "images_with_identity": sum(1 for image in images.values()
                                    if image.get("kind") != "unresolved"),
        "pinned_processes": len(environment.get("pinned_containers") or {}),
        "remote_inputs": len(environment.get("remote_inputs") or {}),
        "nextflow_plugins": list(environment.get("nextflow_plugins") or []),
        "nextflow_runtime": environment.get("nextflow_runtime"),
        "issues": list(environment.get("issues") or []),
    }


def output_checksums(outdir: Path) -> dict[str, str]:
    """The run's result files as {path relative to outdir: sha256}, in sorted order.

    The file checksums of `outputs.snapshot`, which records a bundle's `outputs.sha256` and which
    `nfclaw verify` measures a replay with. Nextflow's own state (`.nextflow*`) and nfclaw's
    provenance bundle are excluded — they describe the run, they are not its results, and a replay
    would never reproduce them byte-for-byte anyway.
    """
    return {
        rel.as_posix(): sha256_file(p)
        for p in sorted(result_files(outdir))
        for rel in (p.relative_to(outdir),)
    }


# The replay logs itself exactly as `nfclaw run` does: everything it prints, in order, in
# <target>/provenance/logs/run.log, ending with its outcome — so it needs no redirect of its own,
# and `nfclaw status <target>` reads it. `provenance/` is not a result, so the log never shows up in
# `nfclaw verify`. Nextflow runs in the background while the script waits for it: a trap set on a
# command running in the foreground only fires once that command has finished, so `kill <replay>`
# used to leave Nextflow running and the log without an outcome. Its output reaches the terminal
# through a FIFO; the controller quotes child lines into the log separately, so its status markers
# cannot be forged by console text. The last line is written after the last of that output.
# Portable to bash 3.2 (macOS's /bin/bash).
_REPLAY_TAIL = r"""original=__ORIGINAL__
if [ -f "$_script_dir/replay_guard.py" ] && [ -f "$_script_dir/run_manifest.json" ]; then
  original="$(cd "$_script_dir/.." && pwd)"
fi
python3 "$original/provenance/replay_guard.py" "$original/provenance"
log="$target/provenance/logs/run.log"
mkdir -p -- "$target/provenance/logs"
echo "nfclaw replay: logging this replay to $log" >&2
python3 "$_script_dir/replay_guard.py" --log-start "$log" "$original" "$$"
console="$target/provenance/logs/.replay-console"
rm -f -- "$console"
mkfifo -- "$console"
cat <"$console" &
tee_pid=$!
stopped_by=""
stopped_status=""
supervisor_pid=""
stop() {
  stopped_by="$1"
  stopped_status="$2"
  if [ -n "$supervisor_pid" ]; then kill -TERM "$supervisor_pid" 2>/dev/null; fi
}
trap 'stop "terminated by SIGTERM" 143' TERM
trap 'stop "terminated by SIGHUP" 129' HUP
trap 'stop "interrupted" 130' INT
set +e
python3 "$_script_dir/replay_guard.py" --run "$log" --shutdown-grace __SHUTDOWN_GRACE__ bash -c __COMMAND_SCRIPT__ nfclaw-replay "$_script_dir" "$target" >"$console" 2>&1 &
supervisor_pid=$!
if [ -n "$stopped_by" ]; then kill -TERM "$supervisor_pid" 2>/dev/null; fi
while :; do
  wait "$supervisor_pid"
  status=$?
  kill -0 "$supervisor_pid" 2>/dev/null || break
done
supervisor_pid=""
wait "$tee_pid"
rm -f -- "$console"
set -e
if [ -n "$stopped_by" ]; then
  outcome="$stopped_by"
  status="$stopped_status"
elif [ "$status" -eq 0 ]; then
  verification_log="$target/provenance/logs/.replay-verification"
  set +e
  python3 "$_script_dir/replay_guard.py" "$original/provenance" "$target" >"$verification_log" 2>&1 &
  supervisor_pid=$!
  if [ -n "$stopped_by" ]; then kill -TERM "$supervisor_pid" 2>/dev/null; fi
  while :; do
    wait "$supervisor_pid"
    verification_status=$?
    kill -0 "$supervisor_pid" 2>/dev/null || break
  done
  supervisor_pid=""
  set -e
  sed 's/^/| /' "$verification_log" >>"$log"
  rm -f -- "$verification_log"
  if [ -n "$stopped_by" ]; then
    outcome="$stopped_by"
    status="$stopped_status"
  elif [ "$verification_status" -ne 0 ]; then
    outcome="failed after Nextflow succeeded (local dependencies changed)"
    status=1
    echo "nfclaw replay: local dependencies changed during execution; start a fresh run" >&2
  else
    # Record the replay's own execution environment and compare it with the recording: the same
    # image digests, plugins and staged remote bytes, or the replay is not a reproduction.
    environment_log="$target/provenance/logs/.replay-environment"
    set +e
    python3 "$_script_dir/environment_record.py" verify "$_script_dir" "$target" >"$environment_log" 2>&1 &
    supervisor_pid=$!
    if [ -n "$stopped_by" ]; then kill -TERM "$supervisor_pid" 2>/dev/null; fi
    while :; do
      wait "$supervisor_pid"
      environment_status=$?
      kill -0 "$supervisor_pid" 2>/dev/null || break
    done
    supervisor_pid=""
    set -e
    sed 's/^/| /' "$environment_log" >>"$log"
    cat "$environment_log" >&2
    rm -f -- "$environment_log"
    if [ -n "$stopped_by" ]; then
      outcome="$stopped_by"
      status="$stopped_status"
    elif [ "$environment_status" -eq 0 ]; then
      outcome=success
    elif [ "$environment_status" -eq 3 ]; then
      outcome="failed after Nextflow succeeded (execution environment differs from the recording)"
      status=1
    else
      outcome="failed after Nextflow succeeded (execution environment could not be checked)"
      status=1
    fi
  fi
else
  outcome="failed (exit status $status)"
fi
echo "==> nfclaw replay finished $(date -u +%Y-%m-%dT%H:%M:%S+00:00): $outcome" >>"$log"
echo "nfclaw replay: $outcome (log: $log)" >&2
exit "$status"
"""  # noqa: E501 -- shell, written into commands.sh byte for byte


def write(*, outdir: Path, pipeline: str, command_str: str,
          submodule: SubmoduleStatus, input_paths: list[Path],
          env_extra: dict[str, str] | None = None,
          outcome: str = "success", chain: dict | None = None,
          input_checksums: dict[str, str] | None = None,
          input_inventory: dict[str, dict[str, str]] | None = None,
          config_paths: tuple[Path, ...] = (),
          config_checksums: dict[str, str] | None = None,
          config_inventory: dict[str, dict[str, str]] | None = None,
          pipeline_checksums: dict[str, str] | None = None,
          unverified_local_paths: dict[str, str] | None = None,
          nextflow_version: str | None = None,
          generated_samplesheet: dict | None = None,
          dependency_stability: dict | None = None,
          completion_caveats: list[str] | None = None,
          stub_profiles: list[str] | None = None,
          stub_configs: list[str] | None = None,
          shutdown_grace_seconds: float | None = None,
          nextflow_log: Path | None = None,
          history_offset: int | None = None,
          institutional_configs: dict | None = None,
          observed_images: dict[str, list[dict]] | None = None) -> Path:
    try:
        grace = (seconds("NFCLAW_SHUTDOWN_GRACE", 10)
                 if shutdown_grace_seconds is None else float(shutdown_grace_seconds))
    except (ValueError, TypeError, OverflowError):
        grace = math.nan
    if not math.isfinite(grace) or grace <= 0:
        raise NfclawError(ErrorCode.PARAMS_INVALID,
                          "shutdown_grace_seconds must be finite and strictly positive.")
    prov = outdir / "provenance"
    prov.mkdir(parents=True, exist_ok=True)
    manifest_path = prov / "run_manifest.json"
    # An old successful bundle must not survive a failed attempt to record the latest run. Publish
    # the new outcome only after every dependent artifact is complete.
    manifest_path.unlink(missing_ok=True)

    nxf_env = effective_nxf_env(env_extra)
    recorded_env, redacted_env = safe_env(nxf_env)
    deadline_failure = None
    try:
        observed_version = (_nextflow_version(env_extra) if nextflow_version is None
                            else nextflow_version)
    except NfclawError as exc:
        if "timeout_seconds" not in exc.details:
            raise
        # A bounded metadata probe can be where cancellation arrives. Retain the rest of the
        # evidence and publish a failed bundle before propagating that deadline.
        observed_version, deadline_failure = "", exc
    manifest = {
        "pipeline": pipeline,
        "version": submodule.version,
        "commit": submodule.commit,
        "command": command_str,
        "outcome": outcome,
        "shutdown_grace_seconds": grace,
        "outdir": str(outdir.absolute()),
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "nextflow": observed_version,
        "nextflow_env": recorded_env,
        "redacted_nextflow_env": redacted_env,
        "os": platform.platform(),
        "dependency_inventory_version": 1,
        "output_inventory_version": 1,
        "provenance_real_path": str(prov.resolve()),
    }
    concrete_pin = (isinstance(nxf_env.get("NXF_VER"), str) and re.fullmatch(
        r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", nxf_env["NXF_VER"]))
    if not manifest["nextflow"] and not concrete_pin:
        manifest["unverified_engine"] = True
    if invalid_names := [key for key in nxf_env
                         if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)]:
        manifest["unreplayable_environment_names"] = sorted(invalid_names)
    # A stage of a chain records which chain it belongs to and which run (and handoff) fed it, so
    # the whole chain can be reconstructed from any one stage. A plain run's manifest is unchanged.
    if chain:
        manifest["chain"] = chain
    if unverified_local_paths:
        manifest["unverified_local_paths"] = dict(unverified_local_paths)
    # A samplesheet nfclaw generated from data files (runner.sheetgen): what it was generated from
    # and how. The sheet itself sits in this bundle, checksummed with the configs.
    if generated_samplesheet:
        manifest["generated_samplesheet"] = dict(generated_samplesheet)
    if dependency_stability is not None:
        manifest["dependency_stability"] = dependency_stability
    # What the pipeline reported missing from a successful run, in its own words (runner.runlog).
    if completion_caveats:
        manifest["completion_caveats"] = list(completion_caveats)
    # Selected profiles that run every task as a stub; a replay (replay_guard) reports it too.
    if stub_profiles:
        manifest["stub_profiles"] = list(stub_profiles)
    if stub_configs:
        manifest["stub_configs"] = list(stub_configs)
    # The nf-core/configs revision the run's institutional config include
    # read (runner.institutional).
    if institutional_configs:
        manifest["institutional_configs"] = dict(institutional_configs)
    if pipeline_checksums is not None or submodule.path.is_dir():
        manifest["pipeline_path"] = str(submodule.path.absolute())
        manifest["pipeline_git_head"] = (
            submodule.commit if re.fullmatch(r"[0-9a-fA-F]{40,64}", submodule.commit) else None)
        pipeline_hashes = (hash_pipeline(submodule.path) if pipeline_checksums is None
                           else pipeline_checksums)
        _atomic_text(prov / "pipeline.sha256", checksum_text(pipeline_hashes))
        # The source itself, not only its checksums: a replay runs this archive, so it reproduces
        # the run after the checkout has moved to another release, been edited or been deleted.
        archive = prov / PIPELINE_ARCHIVE
        if submodule.path.is_dir():
            try:
                manifest["pipeline_archive"] = {
                    "file": PIPELINE_ARCHIVE, "files": len(pipeline_hashes),
                    "sha256": write_pipeline_archive(submodule.path, pipeline_hashes, archive)}
            except (OSError, ValueError) as exc:
                archive.unlink(missing_ok=True)
                manifest["pipeline_archive_error"] = str(exc)
        else:
            archive.unlink(missing_ok=True)
    # params.json is itself a scientific dependency. Direct recording callers get its guard too;
    # the runner supplies a prelaunch config snapshot containing it, preserving the bytes used.
    params = prov / "params.json"
    if params.is_file():
        config_paths = tuple(dict.fromkeys((*config_paths, params)))
        if config_checksums is not None and str(params.absolute()) not in config_checksums:
            params_checksums, params_inventory = snapshot_inputs([params])
            config_checksums = {**config_checksums, **params_checksums}
            if config_inventory is not None:
                config_inventory = {**config_inventory, **params_inventory}
    snapshots = {
        "inputs": (input_paths, input_checksums, input_inventory),
        "configs": (list(config_paths), config_checksums, config_inventory),
    }
    for kind, (paths, snapshot, inventory) in snapshots.items():
        if snapshot is None:
            if inventory is not None:
                raise ValueError(f"{kind} inventory requires its prelaunch file checksums")
            hashes, inventory = snapshot_inputs(paths)
        else:
            hashes = snapshot
            if inventory is None:
                inventory = {}
                if paths:
                    manifest.setdefault("unverified_dependency_inventories", []).append(kind)
        _atomic_text(prov / f"{kind}.sha256", checksum_text(hashes))
        _atomic_text(prov / f"{kind}.sources.json", json.dumps(
            sorted({str(p.expanduser().absolute()) for p in paths}), indent=2) + "\n")
        _atomic_text(prov / f"{kind}.inventory.json",
                     json.dumps(inventory, indent=2, sort_keys=True) + "\n")
    for name, script in _BUNDLED_SCRIPTS.items():
        _atomic_bytes(prov / name, script)
    bundled_configs = _bundle_configs(prov, command_str, config_checksums)
    if bundled_configs:
        manifest["bundled_configs"] = bundled_configs

    # What the engine fetched while it ran: container images by digest, plugins, staged
    # remote files.
    environment = record_environment(
        outdir, env_extra=env_extra, history_offset=history_offset, profile=_profile(command_str),
        nextflow_log=nextflow_log, observed=observed_images)
    _atomic_text(prov / environment_record.RECORD_NAME,
                 json.dumps(environment, indent=2, sort_keys=True) + "\n")
    manifest["environment_record"] = {"file": environment_record.RECORD_NAME,
                                      "sha256": sha256_file(prov / environment_record.RECORD_NAME)}
    manifest["execution_environment"] = environment_summary(environment)
    pins = prov / environment_record.PINS_NAME
    if pin_text := environment_record.pin_config(environment):
        _atomic_text(pins, pin_text)
        manifest["container_pins"] = {"file": environment_record.PINS_NAME,
                                      "sha256": sha256_file(pins)}
    else:
        pins.unlink(missing_ok=True)

    output_hashes, output_inventory, _ = outputs.snapshot(outdir, sha256_file)
    _atomic_text(prov / "outputs.sha256", checksum_text(output_hashes))
    _atomic_text(prov / "outputs.inventory.json", json.dumps(
        {"version": 1, "entries": output_inventory}, indent=2, sort_keys=True) + "\n")

    # Copy the run's collated software-versions YAML into the bundle. nf-core publishes it under two
    # names across template generations: the older `software_versions.yml` and the newer
    # `nf_core_<pipeline>_software_mqc_versions.yml` (used by rnaseq, chipseq, fetchngs, crisprseq,
    # nascent, callingcards, metaboigniter, …). Match whatever the run actually wrote into
    # pipeline_info — both forms contain "software" then "version" — instead of assuming one name,
    # and keep each file's own name so the bundle records exactly what was produced. A hardcoded
    # `software_versions.yml` silently copied nothing for every pipeline on the newer template.
    pinfo = outdir / "pipeline_info"
    if pinfo.is_dir():
        for sv in sorted(pinfo.glob("*software*version*.yml")):
            if sv.is_file():
                _atomic_bytes(prov / sv.name, sv.read_bytes())

    # A faithful, self-contained replay:
    #  - reproduce into a FRESH output directory, never the original. An nf-core pipeline publishes
    #    into `--outdir`, and re-publishing over a previous run's files does not work: Nextflow
    #    refuses to overwrite the reports it is configured to write (`pipeline_info/
    #    execution_trace_*.txt` and friends), and modules that emit a fixed-name artefact — sarek's
    #    BCO `pipeline_info/manifest_*.bco.json` — collide outright. Replaying in place therefore
    #    failed on contact, which is also what made the bundle unusable as a *check*: a reproduction
    #    you can compare against `outputs.sha256` has to land somewhere clean. `--outdir` on the
    #    command line overrides the value in the params file, so one argument redirects
    #    the whole run.
    #  - `cd` into that directory first: nfclaw launches Nextflow from the outdir, so the engine
    #    state (`.nextflow/`) lands beside the results it belongs to and never touches the original.
    #  - re-export every NXF_* variable the run actually saw: the overlay nfclaw applied (--nxf-ver,
    #    --nxf-env) *and* whatever the shell already exported (NXF_OFFLINE, NXF_VER, …). Nextflow
    #    reads all of them, so a run that only succeeds with a pinned engine, an IPv6 flag or
    #    offline mode would not reproduce unless the script carries them — the manifest alone
    #    is not enough.
    #  - run the recorded pipeline checkout while it holds exactly the recorded source (paths that
    #    embed the pipeline directory then keep their values), otherwise the bundle's source
    #    archive, extracted into the replay's provenance/ directory and checked file by file; the
    #    bundle's copies of external `--config` files; and a config pinning every process to the
    #    container image digest it ran.
    env_exports = "".join(
        f"export {shlex.quote(key)}={shlex.quote(value)}\n"
        for key, value in sorted(nxf_env.items())
        if key not in redacted_env
    )
    # Preserve the original effective environment in the manifest, but remove the launcher's
    # moving default from the replay: its actual observed version is an explicit replay pin.
    if isinstance(manifest["nextflow"], str):
        if match := re.search(r"\bversion\s+(\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?)",
                              manifest["nextflow"]):
            env_exports += f"export NXF_VER={shlex.quote(match[1])}\n"
    if redacted_env:
        names = " ".join(name.encode("unicode_escape").decode("ascii") for name in redacted_env)
        env_exports += ("# Sensitive values were omitted from provenance. Export these before "
                        f"replay: {names}\n")
    default_target = shlex.quote(f"{outdir}.replay")
    commands = prov / "commands.sh"
    # Relocate arguments inside this bundle; external input data keep their recorded paths.
    replay_command = command_str
    replay_setup = ""
    command_args = shlex.split(command_str)
    bundle_prefix = str(prov.absolute()) + "/"
    if command_args and Path(command_args[0]).name == "nextflow":
        if command_args[-1] == "-resume":
            command_args = command_args[:-1]
        rendered = []
        for index, arg in enumerate(command_args):
            previous = command_args[index - 1] if index else ""
            config = bundled_configs.get(str(Path(arg).expanduser().absolute())) \
                if previous in ("-c", "-config") else None
            if (index == 2 and command_args[1] == "run" and "pipeline_archive" in manifest
                    and str(Path(arg).absolute()) == manifest.get("pipeline_path")):
                rendered.append('"$pipeline"')
                replay_setup = ('pipeline="$(python3 "$_script_dir/replay_guard.py" '
                                '--pipeline-source "$_script_dir" "$target")" || exit 1\n')
            elif config is not None and config["replay"]:
                rendered.append('"$_script_dir"/' + shlex.quote(config["file"]))
            elif arg.startswith(bundle_prefix):
                rendered.append('"$_script_dir"/' + shlex.quote(arg[len(bundle_prefix):]))
            else:
                rendered.append(shlex.quote(arg))
        if "container_pins" in manifest:
            rendered += ["-c", '"$_script_dir"/' + environment_record.PINS_NAME]
        replay_command = " ".join(rendered)
    elif bundle_prefix in replay_command:
        replay_command = " ".join(
            '"$_script_dir"/' + shlex.quote(arg[len(bundle_prefix):])
            if arg.startswith(bundle_prefix) else shlex.quote(arg)
            for arg in shlex.split(replay_command))
    _atomic_text(commands,
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        '_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"\n'
        "# Replay of this run. Reproduces it into a FRESH output directory — an nf-core pipeline\n"
        "# publishes into --outdir and cannot re-publish over a previous run's files, so replaying\n"  # noqa: E501
        "# into the original one fails immediately. Pass a directory to choose the target:\n"
        "#     ./commands.sh /path/to/fresh-dir\n"
        # The default is assigned on its own line, not inlined into ${1:-...}: inside the parameter
        # expansion the shell would treat shlex's quotes as literal characters of the path.
        f"default_target={default_target}\n"
        "target=\"${1:-$default_target}\"\n"
        'if ! python3 "$_script_dir/replay_guard.py" --check-lock "$target" "$$"; then\n'
        '  exec python3 "$_script_dir/replay_guard.py" --lock "$target" "$_script_dir/commands.sh"\n'  # noqa: E501
        'fi\n'
        "mkdir -p -- \"$target\"\n"
        # Absolute before the `cd` below: Nextflow resolves a relative --outdir against its launch
        # directory, so `./commands.sh fresh` would otherwise publish into fresh/fresh/.
        "target=\"$(cd -- \"$target\" && pwd)\"\n"
        "if [ -n \"$(ls -A -- \"$target\")\" ]; then\n"
        "  echo \"nfclaw replay: target directory is not empty: $target\" >&2\n"
        "  echo \"Pass an empty or non-existent directory: ./commands.sh /path/to/fresh-dir\" >&2\n"
        "  exit 1\n"
        "fi\n"
        "cd -- \"$target\"\n"
        f"{env_exports}"
        + _REPLAY_TAIL.replace("__ORIGINAL__", shlex.quote(str(outdir)))
                      .replace("__SHUTDOWN_GRACE__", str(grace))
                      .replace("__COMMAND_SCRIPT__", shlex.quote(
                          '_script_dir="$1"\ntarget="$2"\n' + replay_setup + replay_command
                          + ' --outdir "$target"')),
        mode=0o755)
    if outcome == "success":
        try:
            budget.check()
        except NfclawError as exc:
            deadline_failure = exc
    if deadline_failure is not None:
        manifest.update(outcome="failed",
                        timeout_seconds=deadline_failure.details["timeout_seconds"])
    _atomic_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if outcome == "success" and deadline_failure is None:
        try:
            budget.check()
        except NfclawError as exc:
            # Atomic publication itself may cross the deadline. Only rewrite its small metadata;
            # the completed checksums and result inventory must not be discarded or rehashed.
            try:
                mark_timed_out(outdir, exc.details["timeout_seconds"])
            except OSError:
                pass  # the invalid success metadata was removed; preserve the deadline cause
            raise
    if deadline_failure is not None:
        raise deadline_failure
    return prov
