"""Identify the analysis whose publications an output directory may certify.

Component hashes avoid persisting environment secrets. This supplements the
input byte/namespace guard; it does not establish identities for remote data or
arbitrary runtime configuration includes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from runner import exact_json as json
from runner import provenance

RECORD = "analysis.json"


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def capture(*, params: dict, profile: str, environment: dict, engine: str | None,
            pipeline: Path, commit: str, configurations: list[Path], limits) -> dict:
    configs = list(configurations)
    # Nextflow reads the user's global config in addition to the pipeline and explicit configs.
    nextflow_home = Path(environment.get("NXF_HOME") or Path.home() / ".nextflow").expanduser()
    global_config = nextflow_home / "config"
    if global_config.exists():
        configs.insert(0, global_config)
    hashes, inventory = provenance.snapshot_inputs(configs)
    components = {
        "parameters": params, "profiles": profile, "environment": environment, "engine": engine,
        "pipeline": {"commit": commit, "source": provenance.hash_pipeline(pipeline)},
        "configuration": {"order": [str(p) for p in configs], "hashes": hashes,
                          "inventory": inventory},
        "resource_limits": None if limits is None or limits.is_empty() else limits.config_text(),
        "runtime_recipes": {name: provenance._sha256(Path(__file__).with_name(name)) for name in
                            ("resources.py", "plugin_compat.py", "fastqrepair_compat.py")},
    }
    return {"version": 1, "components": {key: _digest(value)
                                          for key, value in components.items()}}


def resume_warning(outdir: Path, current: dict) -> str | None:
    try:
        previous = json.loads((outdir / "provenance" / RECORD).read_text(encoding="utf-8"))
        if (not isinstance(previous, dict) or type(previous.get("version")) is not int
                or previous["version"] != 1 or previous != current):
            raise ValueError("analysis identity differs")
    except (OSError, ValueError, TypeError):
        return ("--resume starts a fresh Nextflow cache session because the analysis configuration "
                "changed or its previous identity is unavailable. Effective parameters, profiles, "
                "engine/environment, configuration and pipeline source must agree before reusing "
                "publications. All tasks will be recomputed; the previous run will be preserved "
                "in a sibling archive.")
    return None


def write(outdir: Path, identity: dict) -> None:
    path = outdir / "provenance" / RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    provenance._atomic_bytes(path, (json.dumps(identity, sort_keys=True, indent=2) + "\n").encode())


def retain_report_suffix(outdir: Path, params: dict) -> dict:
    """Reuse an automatically generated suffix during an unchanged resume.

    Explicit user values continue to win. A missing/invalid historical identity
    causes archiving independently, even when an older params file is readable.
    """
    if params.get("trace_report_suffix"):
        return params
    try:
        previous = json.loads((outdir / "provenance/params.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return params
    if isinstance(previous, dict) and isinstance(previous.get("trace_report_suffix"), str):
        return {**params, "trace_report_suffix": previous["trace_report_suffix"]}
    return params
