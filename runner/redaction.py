"""Apply the provenance secret policy to wrapper commands and diagnostics."""
from __future__ import annotations

import os

from runner.provenance import safe_env


def assignments(argv: list[str]) -> list[tuple[str, str]]:
    """Retain every assignment, including overwritten secrets in duplicate options."""
    env = [(k, v) for k, v in os.environ.items() if k.startswith("NXF_")]
    for i, arg in enumerate(argv):
        value = (argv[i + 1] if arg == "--nxf-env" and i + 1 < len(argv)
                 else arg[len("--nxf-env="):] if arg.startswith("--nxf-env=") else "")
        key, sep, value = value.partition("=")
        if sep:
            env.append((key, value))
    return env


def text(value: str, env: list[tuple[str, str]]) -> str:
    secrets = {item for key, item in env if item and safe_env({key: item})[1]}
    for secret in sorted(secrets, key=len, reverse=True):
        value = value.replace(secret, "<redacted>")
        value = value.replace(repr(secret)[1:-1], "<redacted>")
    return value


def argv(args: list[str]) -> list[str]:
    env = assignments(args)
    return [text(arg, env) for arg in args]
