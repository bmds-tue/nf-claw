"""Validated environment overrides for setup and shutdown operation limits."""
from __future__ import annotations

import math
import os

from runner.errors import ErrorCode, NfclawError


def seconds(name: str, default: float) -> float:
    """Read a finite, strictly positive number of seconds, or the caller's default."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    if not math.isfinite(value) or value <= 0:
        raise NfclawError(
            ErrorCode.PARAMS_INVALID,
            f"{name} must be a finite, strictly positive number of seconds.",
            fix=f"Set {name} to a number greater than zero, or unset it to use the default.")
    return value
