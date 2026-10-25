"""Resolve pipeline content separately from the installed Python distribution."""
from __future__ import annotations

import os
from pathlib import Path

from runner.errors import ErrorCode, NfclawError


def resolve() -> Path:
    configured = os.environ.get("NFCLAW_LIBRARY_ROOT")
    root = (Path(configured).expanduser() if configured
            else Path(__file__).resolve().parent.parent).resolve()
    if not (root / "pipelines").is_dir():
        raise NfclawError(ErrorCode.ENVIRONMENT,
            (f"NFCLAW_LIBRARY_ROOT does not contain a pipeline library: {root}" if configured else
             "nf-claw pipeline library content was not found beside the installed package."),
            fix="git clone https://github.com/bmds-tue/nf-claw.git /path/to/nf-claw; "
                "set NFCLAW_LIBRARY_ROOT=/path/to/nf-claw. Pinned sources initialize on demand. "
                "An editable checkout also works with pip install -e .")
    return root
