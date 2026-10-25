"""Read-only environment diagnostics. No analysis or service changes."""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from runner import library
from runner.engine_version import version_text
from runner.errors import NfclawError
from runner.probes import capture


def collect() -> dict:
    issues = []
    try:
        content = str(library.resolve())
    except NfclawError as exc:
        content = None
        issues.append(str(exc))
    tools = {name: shutil.which(name) for name in
             ("git", "java", "nextflow", "docker", "podman", "apptainer", "singularity")}
    for name in ("git", "java", "nextflow"):
        if tools[name] is None:
            issues.append(f"{name} is missing from PATH; install it before running a pipeline.")
    versions = {"python": platform.python_version()}
    for name, arguments in (("git", ["--version"]), ("java", ["-version"]),
                             ("nextflow", ["-version"])):
        versions[name] = None
        if tools[name] is None:
            continue
        try:
            result = capture([name, *arguments], timeout=5)
            if name == "nextflow":
                versions[name] = version_text(result)
            elif result.returncode == 0:
                match = re.search(r'version[\s"]+([0-9][0-9.A-Za-z_+-]*)',
                                  (result.stdout or "") + (result.stderr or ""))
                if match:
                    versions[name] = match[1]
        except (OSError, subprocess.SubprocessError):
            pass
        if versions[name] is None:
            issues.append(f"{name} version could not be established within the 5-second "
                          "metadata probe; prepare or repair that executable before execution.")
    engines = {}
    for engine in ("docker", "podman"):
        if not tools[engine]:
            continue
        try:
            result = capture([engine, "info", "--format", "{{.ServerVersion}}"], timeout=5)
            accessible = result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            accessible = False
        engines[engine] = {"accessible": accessible}
        if not accessible:
            issues.append(f"{engine} is installed but its engine is not accessible; "
                          "check its service and your user permissions.")
    profiles = [name for name, facts in engines.items() if facts["accessible"]]
    profiles += [name for name in ("apptainer", "singularity") if tools[name]]
    if not profiles:
        issues.append("No accessible container profile was found; configure Docker, Podman "
                      "or Apptainer/Singularity, or deliberately select a native profile.")
    destination = Path.cwd()
    disk = shutil.disk_usage(destination)
    return {"schema_version": 1, "kind": "diagnostics", "ok": not issues,
            "platform": {"system": platform.system(), "machine": platform.machine(),
                         "python": platform.python_version(), "executable": sys.executable,
                         "cpus": os.cpu_count()},
            "library_root": content, "tools": tools, "versions": versions,
            "container_engines": engines,
            "available_container_profiles": profiles,
            "disk": {"path": str(destination), "free_bytes": disk.free, "total_bytes": disk.total},
            "issues": issues}
