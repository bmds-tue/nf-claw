from __future__ import annotations

import re
import subprocess
from pathlib import Path
from runner.probes import capture

# nf-core pins the engine in the manifest, e.g. `nextflowVersion = '!>=25.04.3'`.
# We surface a NON-blocking advisory when the installed engine is clearly too old;
# Nextflow itself is the authority and enforces this at launch. To avoid ever
# contradicting it with a false positive, we judge only the unambiguous `>=`/`>`
# constraint and stay silent on anything we cannot parse with confidence.

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
        r = capture(["nextflow", "-version"], timeout=30)
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None
    return version_text(r)


def _tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def warning(spec: str | None, installed: str | None) -> str | None:
    """An advisory string if `installed` clearly fails `spec`, else None (silent)."""
    if not spec or not installed:
        return None
    sm = _SPEC_RE.match(spec)
    im = _INSTALLED_RE.search(installed)
    if sm is None or im is None:               # not a constraint/version we model → stay silent
        return None
    op, req, have = sm.group(1), sm.group(2), im.group(1)
    req_t, have_t = _tuple(req), _tuple(have)
    n = max(len(req_t), len(have_t))
    req_t += (0,) * (n - len(req_t))
    have_t += (0,) * (n - len(have_t))
    satisfied = have_t >= req_t if op == ">=" else have_t > req_t
    if satisfied:
        return None
    return (f"Nextflow {have} is older than this pipeline's required {op}{req}; "
            f"Nextflow will likely reject the run "
            f"(advisory — Nextflow enforces the engine version).")


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


def check(upstream: Path, *, nxf_ver: str | None = None) -> list[str]:
    """Zero or one advisory about the Nextflow engine vs. the pipeline's requirement.

    When `nxf_ver` is given (the user pinned the engine via --nxf-ver / NXF_VER), that is the
    version Nextflow will actually run, so judge the requirement against it — not the installed
    launcher, which Nextflow only uses to bootstrap the requested version."""
    spec = required_spec(upstream / "nextflow.config")
    if spec is None:                           # no declared constraint → nothing to advise
        return []
    effective = f"version {nxf_ver}" if nxf_ver else _installed_raw()
    w = warning(spec, effective)
    return [w] if w else []
