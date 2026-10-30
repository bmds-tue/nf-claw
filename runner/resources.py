from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from runner.errors import ErrorCode, NfclawError


# Nextflow's own literal formats: memory is parsed by MemoryUnit, time by Duration. Accepting
# exactly the units those two parsers document means a value nfclaw accepts is a value Nextflow
# can parse — the check fails fast on a typo instead of letting the engine die mid-run. Both
# tolerate the `15.GB` / `15 GB` / `15GB` spellings, so all three are allowed here.
_MEMORY_RE = re.compile(r"(?i)^\d+(?:\.\d+)?\s*\.?\s*(?:B|KB|MB|GB|TB|PB|EB|ZB)$")
_TIME_RE = re.compile(
    r"(?i)^\d+(?:\.\d+)?\s*\.?\s*"
    r"(?:ms|milli|millis|s|sec|secs|second|seconds|m|min|mins|minute|minutes"
    r"|h|hour|hours|d|day|days)$"
)


_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_NXF_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-edge)?$")


def parse_nxf_env(items: list[str] | dict[str, str]) -> dict[str, str]:
    """`NXF_*` variables for one run, from repeatable `--nxf-env KEY=VALUE` (a list) or a chain
    spec's `nxf_env` (an object).

    Restricting to NXF_* keeps the knob focused on Nextflow's own runtime (and the provenance record
    meaningful); any other environment a run needs is still inherited from the shell."""
    pairs: list[tuple[str, object]] = []
    if isinstance(items, dict):
        if not all(isinstance(k, str) for k in items):
            raise NfclawError(ErrorCode.PARAMS_INVALID, "nxf_env keys must be strings.")
        pairs = list(items.items())
    elif isinstance(items, list) and all(isinstance(item, str) for item in items):
        for item in items:
            key, sep, value = item.partition("=")
            if not sep:
                raise NfclawError(ErrorCode.PARAMS_INVALID,
                                  f"--nxf-env must be KEY=VALUE (got {item!r}).")
            pairs.append((key, value))
    else:
        raise NfclawError(ErrorCode.PARAMS_INVALID,
                          "nxf_env must be an object or a list of KEY=VALUE strings.")
    env: dict[str, str] = {}
    for key, value in pairs:
        key = key.strip()
        if not key.startswith("NXF_"):
            raise NfclawError(ErrorCode.PARAMS_INVALID,
                              f"--nxf-env only accepts NXF_* variables (got {key!r}); "
                              "other environment is inherited from the shell.")
        if not _ENV_NAME_RE.fullmatch(key):
            raise NfclawError(ErrorCode.PARAMS_INVALID,
                              f"--nxf-env has an invalid environment variable name: {key!r}.")
        if not isinstance(value, str):
            raise NfclawError(ErrorCode.PARAMS_INVALID,
                              f"--nxf-env {key} must be a string (got {value!r}).")
        if "\x00" in value:
            raise NfclawError(ErrorCode.PARAMS_INVALID,
                              f"--nxf-env {key} contains a NUL character.")
        env[key] = value
    return env


def check_nxf_version(raw: str) -> str:
    """A full Nextflow version for `--nxf-ver` (sets NXF_VER), or a clear error."""
    if not isinstance(raw, str) or not _NXF_VERSION_RE.fullmatch(raw):
        raise NfclawError(ErrorCode.PARAMS_INVALID,
                          "--nxf-ver must be a full Nextflow version such as 25.10.2 or "
                          f"25.10.2-edge (got {raw!r})")
    return raw


@dataclass(frozen=True)
class ResourceLimits:
    """The ceiling a run may request, as nf-core documents it: `process.resourceLimits`.

    nf-core pipelines size each process from a label (`process_high` is 12 CPUs / 72 GB in the
    stock base.config), and Nextflow retries a failed task with more. `resourceLimits` caps every
    one of those requests at what the machine actually has, so a task is never submitted asking for
    more memory than exists. It is the mechanism nf-core's own `test` profiles use, and the one its
    configuration docs prescribe for a workstation:
    https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources

    It is deliberately *not* a `withName:` override: `withName` changes one named process's initial
    request, so capping that way means naming every process that might exceed the machine (and
    re-doing it whenever the pipeline adds one). `resourceLimits` is a single ceiling that applies
    to every process and every retry.
    """

    cpus: int | None = None
    memory: str | None = None
    time: str | None = None

    def is_empty(self) -> bool:
        return self.cpus is None and self.memory is None and self.time is None

    def config_text(self) -> str:
        """The Nextflow config that applies this ceiling, in nf-core's own layout."""
        entries = []
        if self.cpus is not None:
            entries.append(f"        cpus: {self.cpus},")
        if self.memory is not None:
            entries.append(f"        memory: '{self.memory}',")
        if self.time is not None:
            entries.append(f"        time: '{self.time}',")
        entries[-1] = entries[-1].rstrip(",")             # Groovy list: no trailing comma
        body = "\n".join(entries)
        return (
            "// Generated by `nfclaw run --limit-cpus/--limit-memory/--limit-time`.\n"
            "// Caps every process request (and every retry) at the resources this machine has,\n"
            "// per https://nf-co.re/docs/running/configuration/nextflow-for-your-system\n"
            "process {\n"
            "    resourceLimits = [\n"
            f"{body}\n"
            "    ]\n"
            "}\n"
        )


def parse(cpus: int | None, memory: str | None, time: str | None) -> ResourceLimits:
    """Validate the three limits and return them. Raises NfclawError on a value Nextflow
    could not parse, naming the offending flag — a deterministic check, not a guess."""
    if cpus is not None and (type(cpus) is not int or cpus <= 0):
        raise NfclawError(ErrorCode.PARAMS_INVALID,
                          f"--limit-cpus must be a positive whole number of CPUs (got {cpus}).")
    if memory is not None and (not isinstance(memory, str)
                               or not _MEMORY_RE.fullmatch(memory.strip())):
        raise NfclawError(
            ErrorCode.PARAMS_INVALID,
            f"--limit-memory is not a Nextflow memory value: {memory!r}.",
            fix="Use a number and a unit, e.g. 15.GB, 16 GB or 512.MB.")
    if time is not None and (not isinstance(time, str) or not _TIME_RE.fullmatch(time.strip())):
        raise NfclawError(
            ErrorCode.PARAMS_INVALID,
            f"--limit-time is not a Nextflow duration value: {time!r}.",
            fix="Use a number and a unit, e.g. 1.h, 90.min or 2.d.")
    for flag, value in (("--limit-memory", memory), ("--limit-time", time)):
        if value is not None and float(re.match(r"\d+(?:\.\d+)?", value.strip()).group()) <= 0:
            raise NfclawError(ErrorCode.PARAMS_INVALID, f"{flag} must be greater than zero.")
    return ResourceLimits(
        cpus=cpus,
        memory=memory.strip() if memory else None,
        time=time.strip() if time else None,
    )


def write_config(limits: ResourceLimits, dest: Path) -> Path:
    """Materialise the ceiling as a config file Nextflow is given with `-c`.

    It is written inside the provenance bundle, so the exact ceiling a run used is recorded and
    `commands.sh` — which carries the same `-c <path>` — replays it."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(limits.config_text(), encoding="utf-8")
    return dest
