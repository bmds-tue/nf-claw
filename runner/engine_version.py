from __future__ import annotations

import re
import subprocess
from pathlib import Path

from runner.probes import capture
from runner.settings import seconds

# nf-core pins the engine in the manifest, e.g. `nextflowVersion = '!>=25.04.3'`. Nextflow enforces
# it at launch — every pinned release uses the strict `!` form, so a too-old engine is refused with
# "does not match workflow required version" before the pipeline runs — and nfclaw does not repeat
# that check (runner.execution names the engine to pin from that refusal). The declaration is read
# here to document it (skill.md) and to name the engine to pin when a chain stage's configuration
# probe fails (runner.chain).

_REQUIRED_RE = re.compile(r"""nextflowVersion\s*=\s*['"]([^'"]+)['"]""")
_SPEC_RE = re.compile(r"^\s*!?\s*(>=?)\s*(\d+(?:\.\d+)*)\s*$")
_INSTALLED_RE = re.compile(r"version\s+(\d+(?:\.\d+)+)")
_VERSION_LINE = re.compile(
    r"^nextflow[ \t]+version[ \t]+\d+(?:\.\d+)+(?:-[A-Za-z0-9.-]+)?"
    r"(?:[ \t]+build[ \t]+\d+)?[ \t\r]*$", re.MULTILINE | re.IGNORECASE)
# What `nextflow -version` actually prints: its banner, whose second line is the version, e.g.
#       N E X T F L O W
#       version 26.04.3 build 12259
_BANNER_VERSION = re.compile(
    r"^[ \t]*N E X T F L O W[ \t\r]*\n[ \t]*version[ \t]+(\d+(?:\.\d+)+(?:-[A-Za-z0-9.-]+)?)"
    r"[ \t]+build[ \t]+(\d+)[ \t\r]*$", re.MULTILINE)


def version_text(result: subprocess.CompletedProcess[str]) -> str | None:
    """Accept one unambiguous engine version from a successful metadata probe, as
    `nextflow version X build N` (or the `nextflow version …` line `nextflow -v` prints).

    Bootstrap diagnostics are not engine identity and can contain private URLs.
    Do not retain them in provenance or treat a failed probe as version evidence.
    """
    if result.returncode != 0:
        return None
    lines = set()
    for output in (result.stdout, result.stderr):
        lines.update(match.group().strip() for match in _VERSION_LINE.finditer(output or ""))
        lines.update(f"nextflow version {m.group(1)} build {m.group(2)}"
                     for m in _BANNER_VERSION.finditer(output or ""))
    return next(iter(lines)) if len(lines) == 1 else None


def required_spec(config_path: Path) -> str | None:
    """The `manifest.nextflowVersion` constraint declared in nextflow.config, or None."""
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _REQUIRED_RE.search(text)
    return m.group(1) if m else None


def minimum_version(spec: str | None) -> str | None:
    """The concrete version a `>=`/`>` spec names — the one to pass to `--nxf-ver`.

    `'!>=25.10.4'` → `'25.10.4'`. None for a spec shape we do not model, so a caller never
    invents an engine version to pin."""
    if not spec:
        return None
    m = _SPEC_RE.match(spec)
    return m.group(2) if m else None


def _installed_raw() -> str | None:
    try:
        r = capture(["nextflow", "-version"], timeout=seconds("NFCLAW_VERSION_TIMEOUT", 30))
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None
    return version_text(r)


def _tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def effective(nxf_ver: str | None = None) -> str | None:
    """The engine version a launch will run (`1.2.3`), or None when it cannot be determined: the
    `--nxf-ver` pin when given, else what the launcher reports (it honours an exported NXF_VER)."""
    if nxf_ver:
        m = re.match(r"\d+(?:\.\d+)+", nxf_ver)
        return m.group() if m else None
    raw = _installed_raw()
    m = _INSTALLED_RE.search(raw) if raw else None
    return m.group(1) if m else None


# `process.resourceLimits` first shipped in Nextflow 24.04.0. Older engines accept the setting
# without a word and apply no ceiling at all (verified with 23.10.1: a 16-CPU/64 GB request ran
# uncapped under a 2-CPU/4 GB limit), so a requested ceiling must not be passed to one.
RESOURCE_LIMITS_SINCE = (24, 4, 0)


def supports_resource_limits(version: str) -> bool:
    parts = _tuple(re.match(r"\d+(?:\.\d+)*", version).group())
    return parts + (0,) * (3 - len(parts)) >= RESOURCE_LIMITS_SINCE


# Java 17 support arrived in Nextflow 21.10.0. An older engine cannot even compile a pipeline config
# on Java 17+ ("Unsupported class file major version 61": verified with 21.04.0 on OpenJDK 17.0.20,
# while 21.10.3 runs), so a release declaring such a minimum is run on a later engine instead —
# the one the acceptance gate checks those releases on (scripts/nextflow_accept.sh).
JAVA17_SINCE = (21, 10, 0)
LEGACY_RELEASE_ENGINE = "24.10.5"
_JAVA_VERSION = re.compile(r'version\s+"(\d+)(?:\.(\d+))?')


def predates_java17(version: str | None) -> bool:
    """Whether Nextflow `version` is older than its Java 17 support; False when unparseable."""
    m = re.match(r"\d+(?:\.\d+)*", version or "")
    if m is None:
        return False
    parts = _tuple(m.group())
    return parts + (0,) * (3 - len(parts)) < JAVA17_SINCE


def runs_on_java(version: str, java: int) -> bool:
    """Whether Nextflow `version` can run on Java major release `java`."""
    return java < 17 or not predates_java17(version)


def java_major(version_output: str) -> int | None:
    """The major release in `java -version` output: `"17.0.2"` → 17, legacy `"1.8.0_402"` → 8."""
    m = _JAVA_VERSION.search(version_output or "")
    if m is None:
        return None
    first = int(m.group(1))
    return int(m.group(2)) if first == 1 and m.group(2) else first


def java_command(env: dict[str, str]) -> str:
    """The Java the Nextflow launcher runs on: NXF_JAVA_HOME, else JAVA_HOME, else `java`."""
    home = env.get("NXF_JAVA_HOME") or env.get("JAVA_HOME")
    return f"{home}/bin/java" if home else "java"


def java_major_for_nextflow(env: dict[str, str]) -> int | None:
    """The major Java release Nextflow would run on, or None when it cannot be determined."""
    try:
        r = capture([java_command(env), "-version"], timeout=seconds("NFCLAW_VERSION_TIMEOUT", 30))
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None
    return java_major(f"{r.stderr or ''}\n{r.stdout or ''}") if r.returncode == 0 else None
