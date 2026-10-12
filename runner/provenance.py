from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from runner.outputs import result_files
from runner import outputs
from runner.engine_version import version_text
from runner.probes import capture
from runner.replay_guard import (MissingInputSource as MissingInputSource,
                                 hash_inputs as hash_inputs, hash_pipeline as hash_pipeline,
                                 input_files as input_files,
                                 snapshot_inputs as snapshot_inputs,
                                 read_input_inventory as read_input_inventory,
                                 read_checksums as read_checksums)
from runner.samplesheet import delimiter_for, serialized_rows
from runner.schema import InputSchema, PATH_FORMATS
from runner.submodule import SubmoduleStatus


_SENSITIVE_KEY_PARTS = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "API_KEY",
                        "ACCESS_KEY", "PRIVATE_KEY", "AUTH")
_SENSITIVE_VALUE_RE = re.compile(
    r"(?i)(?:token|secret|password|credential|api[_-]?key|access[_-]?key|private[_-]?key)\s*[=:]"
)
_URI_CREDENTIALS_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^/\s?#]*@")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def samplesheet_input_paths(path: Path, schema: InputSchema) -> list[Path]:
    """Local data sources in schema-declared CSV/TSV or flat JSON/YAML path fields.

    Remote URLs and nested or pipeline-specific inputs need separate identity handling and are not guessed.
    The sheet has already been validated by the runner, including its absolute-path requirement.
    """
    columns = [column.name for column in schema.columns if column.fmt in PATH_FORMATS]
    paths: set[Path] = set()
    if path.suffix.lower() not in (".csv", ".tsv"):
        for row in serialized_rows(path) or []:
            for column in columns:
                value = row.get(column)
                if isinstance(value, str) and value and "://" not in value:
                    paths.add(Path(value))
        return sorted(paths)
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream, delimiter=delimiter_for(path), strict=True):
            for column in columns:
                value = (row.get(column) or "").strip()
                if value and "://" not in value:
                    paths.add(Path(value))
    return sorted(paths)


def _atomic_bytes(path: Path, content: bytes, *, mode: int | None = None) -> None:
    """Replace one bundle file without exposing a truncated write."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as fh:
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


def _nextflow_version(env_extra: dict[str, str] | None = None) -> str:
    # Probe with the same env overlay the run used, so a pinned NXF_VER reports the version that
    # actually ran, not the launcher default.
    env = {**os.environ, **env_extra} if env_extra else None
    try:
        r = capture(["nextflow", "-version"], timeout=30, env=env)
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


def output_checksums(outdir: Path) -> dict[str, str]:
    """The run's result files as {path relative to outdir: sha256}, in sorted order.

    The single definition of "what this run produced": the provenance bundle records it, and
    `nfclaw verify` measures a directory with it. Nextflow's own state (`.nextflow*`) and nfclaw's
    provenance bundle are excluded — they describe the run, they are not its results, and a replay
    would never reproduce them byte-for-byte anyway.
    """
    return {
        rel.as_posix(): _sha256(p)
        for p in sorted(result_files(outdir))
        for rel in (p.relative_to(outdir),)
    }


# The replay logs itself exactly as `nfclaw run` does: everything it prints, in order, in
# <target>/provenance/logs/run.log, ending with its outcome — so it needs no redirect of its own, and
# `nfclaw status <target>` reads it. `provenance/` is not a result, so the log never shows up in
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
python3 "$_script_dir/replay_guard.py" --run "$log" bash -c __COMMAND_SCRIPT__ nfclaw-replay "$_script_dir" "$target" >"$console" 2>&1 &
supervisor_pid=$!
if [ -n "$stopped_by" ]; then kill -TERM "$supervisor_pid" 2>/dev/null; fi
while :; do
  wait "$supervisor_pid"
  status=$?
  kill -0 "$supervisor_pid" 2>/dev/null || break
done
wait "$tee_pid"
rm -f -- "$console"
set -e
if [ -n "$stopped_by" ]; then
  outcome="$stopped_by"
  status="$stopped_status"
elif [ "$status" -eq 0 ]; then
  outcome=success
else
  outcome="failed (exit status $status)"
fi
echo "==> nfclaw replay finished $(date -u +%Y-%m-%dT%H:%M:%S+00:00): $outcome" >>"$log"
echo "nfclaw replay: $outcome (log: $log)" >&2
exit "$status"
"""


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
          nextflow_version: str | None = None) -> Path:
    prov = outdir / "provenance"
    prov.mkdir(parents=True, exist_ok=True)
    manifest_path = prov / "run_manifest.json"
    # An old successful bundle must not survive a failed attempt to record the latest run. Publish
    # the new outcome only after every dependent artifact is complete.
    manifest_path.unlink(missing_ok=True)

    nxf_env = effective_nxf_env(env_extra)
    recorded_env, redacted_env = safe_env(nxf_env)
    manifest = {
        "pipeline": pipeline,
        "version": submodule.version,
        "commit": submodule.commit,
        "command": command_str,
        "outcome": outcome,
        "outdir": str(outdir.absolute()),
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nextflow": _nextflow_version(env_extra) if nextflow_version is None else nextflow_version,
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
    if invalid_names := [key for key in nxf_env if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)]:
        manifest["unreplayable_environment_names"] = sorted(invalid_names)
    # A stage of a chain records which chain it belongs to and which run (and handoff) fed it, so
    # the whole chain can be reconstructed from any one stage. A plain run's manifest is unchanged.
    if chain:
        manifest["chain"] = chain
    if unverified_local_paths:
        manifest["unverified_local_paths"] = dict(unverified_local_paths)
    if pipeline_checksums is not None or submodule.path.is_dir():
        manifest["pipeline_path"] = str(submodule.path.absolute())
        manifest["pipeline_git_head"] = (
            submodule.commit if re.fullmatch(r"[0-9a-fA-F]{40,64}", submodule.commit) else None)
        pipeline_hashes = hash_pipeline(submodule.path) if pipeline_checksums is None else pipeline_checksums
        _atomic_text(prov / "pipeline.sha256", "".join(
            f"{digest}  {path}\n" for path, digest in sorted(pipeline_hashes.items())))
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
        lines = [f"{digest}  {path}" for path, digest in sorted(hashes.items())]
        _atomic_text(prov / f"{kind}.sha256", "\n".join(lines) + ("\n" if lines else ""))
        _atomic_text(prov / f"{kind}.sources.json", json.dumps(
            sorted({str(p.expanduser().absolute()) for p in paths}), indent=2) + "\n")
        _atomic_text(prov / f"{kind}.inventory.json", json.dumps(inventory, indent=2, sort_keys=True) + "\n")
    _atomic_bytes(prov / "replay_guard.py", Path(__file__).with_name("replay_guard.py").read_bytes())

    output_hashes, output_inventory, _ = outputs.snapshot(outdir, _sha256)
    out_lines = [f"{digest}  {rel}" for rel, digest in output_hashes.items()]
    _atomic_text(prov / "outputs.sha256", "\n".join(out_lines) + ("\n" if out_lines else ""))
    _atomic_text(prov / "outputs.inventory.json", json.dumps(
        {"version": 1, "entries": output_inventory}, indent=2, sort_keys=True) + "\n")

    # Copy the run's collated software-versions YAML into the bundle. nf-core publishes it under two
    # names across template generations: the older `software_versions.yml` and the newer
    # `nf_core_<pipeline>_software_mqc_versions.yml` (used by rnaseq, chipseq, fetchngs, crisprseq,
    # nascent, callingcards, metaboigniter, …). Match whatever the run actually wrote into
    # pipeline_info — both forms contain "software" then "version" — instead of assuming one name, and
    # keep each file's own name so the bundle records exactly what was produced. A hardcoded
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
    #    command line overrides the value in the params file, so one argument redirects the whole run.
    #  - `cd` into that directory first: nfclaw launches Nextflow from the outdir, so the engine
    #    state (`.nextflow/`) lands beside the results it belongs to and never touches the original.
    #  - re-export every NXF_* variable the run actually saw: the overlay nfclaw applied (--nxf-ver,
    #    --nxf-env) *and* whatever the shell already exported (NXF_OFFLINE, NXF_VER, …). Nextflow
    #    reads all of them, so a run that only succeeds with a pinned engine, an IPv6 flag or offline
    #    mode would not reproduce unless the script carries them — the manifest alone is not enough.
    # `--config` files and the params file are absolute in `command_str`, so they replay as-is.
    env_exports = "".join(
        f"export {shlex.quote(key)}={shlex.quote(value)}\n"
        for key, value in sorted(nxf_env.items())
        if key not in redacted_env
    )
    # Preserve the original effective environment in the manifest, but remove the launcher's
    # moving default from the replay: its actual observed version is an explicit replay pin.
    if isinstance(manifest["nextflow"], str):
        if match := re.search(r"\bversion\s+(\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?)", manifest["nextflow"]):
            env_exports += f"export NXF_VER={shlex.quote(match[1])}\n"
    if redacted_env:
        names = " ".join(name.encode("unicode_escape").decode("ascii") for name in redacted_env)
        env_exports += ("# Sensitive values were omitted from provenance. Export these before "
                        f"replay: {names}\n")
    default_target = shlex.quote(f"{outdir}.replay")
    commands = prov / "commands.sh"
    # Relocate arguments inside this bundle; external dependencies keep their recorded paths.
    replay_command = command_str
    command_args = shlex.split(command_str)
    if command_args and Path(command_args[0]).name == "nextflow" and command_args[-1] == "-resume":
        replay_command = shlex.join(command_args[:-1])
    bundle_prefix = str(prov.absolute()) + "/"
    if bundle_prefix in replay_command:
        replay_command = " ".join(
            '"$_script_dir"/' + shlex.quote(arg[len(bundle_prefix):])
            if arg.startswith(bundle_prefix) else shlex.quote(arg)
            for arg in shlex.split(replay_command))
    _atomic_text(commands,
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        '_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"\n'
        "# Replay of this run. Reproduces it into a FRESH output directory — an nf-core pipeline\n"
        "# publishes into --outdir and cannot re-publish over a previous run's files, so replaying\n"
        "# into the original one fails immediately. Pass a directory to choose the target:\n"
        "#     ./commands.sh /path/to/fresh-dir\n"
        # The default is assigned on its own line, not inlined into ${1:-...}: inside the parameter
        # expansion the shell would treat shlex's quotes as literal characters of the path.
        f"default_target={default_target}\n"
        "target=\"${1:-$default_target}\"\n"
        'if ! python3 "$_script_dir/replay_guard.py" --check-lock "$target" "$$"; then\n'
        '  exec python3 "$_script_dir/replay_guard.py" --lock "$target" "$_script_dir/commands.sh"\n'
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
                      .replace("__COMMAND_SCRIPT__", shlex.quote(
                          '_script_dir="$1"\ntarget="$2"\n' + replay_command + ' --outdir "$target"')),
        mode=0o755)
    _atomic_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return prov
