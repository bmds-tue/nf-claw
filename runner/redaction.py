"""Apply the provenance secret policy to wrapper commands and diagnostics."""
from __future__ import annotations

import os
import json
import shlex

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
        forms = {secret, repr(secret)[1:-1], shlex.quote(secret),
                 json.dumps(secret, ensure_ascii=False)[1:-1],
                 json.dumps(secret, ensure_ascii=True)[1:-1]}
        for form in sorted(forms, key=len, reverse=True):
            value = value.replace(form, "<redacted>")
    return value


def argv(args: list[str]) -> list[str]:
    env = assignments(args)
    return [text(arg, env) for arg in args]


def data(value, env: list[tuple[str, str]]):
    """Redact every string in a presentation, before rendering or JSON serialization."""
    if isinstance(value, str):
        return text(value, env)
    if isinstance(value, list):
        return [data(item, env) for item in value]
    if isinstance(value, dict):
        return {key: data(item, env) for key, item in value.items()}
    return value
