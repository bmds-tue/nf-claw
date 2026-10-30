"""Apply the provenance secret policy to wrapper commands and diagnostics."""
from __future__ import annotations

import os

from runner.provenance import safe_env


def argv_env(argv: list[str]) -> dict[str, str]:
    """Extract even malformed options before validation can fail."""
    env = {k: v for k, v in os.environ.items() if k.startswith("NXF_")}
    for i, arg in enumerate(argv):
        value = (argv[i + 1] if arg == "--nxf-env" and i + 1 < len(argv)
                 else arg[len("--nxf-env="):] if arg.startswith("--nxf-env=") else "")
        key, sep, value = value.partition("=")
        if sep:
            env[key] = value
    return env


def text(value: str, env: dict[str, str]) -> str:
    _, names = safe_env(env)
    secrets = {env[name] for name in names if env[name]}
    for secret in sorted(secrets, key=len, reverse=True):
        value = value.replace(secret, "<redacted>")
    return value


def argv(args: list[str]) -> list[str]:
    env = argv_env(args)
    return [text(arg, env) for arg in args]
