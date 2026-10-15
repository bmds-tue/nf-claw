"""An opt-in absolute deadline shared by nested run preparation and execution."""
from __future__ import annotations

import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps

from runner.errors import ErrorCode, NfclawError


@dataclass(frozen=True)
class _Budget:
    deadline: float
    timeout_seconds: float


_current: ContextVar[_Budget | None] = ContextVar("nfclaw_budget", default=None)


@contextmanager
def scope(timeout_seconds: float | None):
    """Start a budget, or inherit a parent's earlier deadline without extending it."""
    current = _current.get()
    if timeout_seconds is not None:
        candidate = _Budget(time.monotonic() + timeout_seconds, timeout_seconds)
        if current is None or candidate.deadline < current.deadline:
            current = candidate
    token = _current.set(current)
    try:
        check()
        yield
    finally:
        _current.reset(token)


def bounded(function):
    """Scope a public run's keyword-only ``timeout_seconds`` argument."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        with scope(kwargs.get("timeout_seconds")):
            return function(*args, **kwargs)
    return wrapped


def remaining(ceiling: float | None = None) -> float | None:
    """The positive time left, capped by an operation limit when supplied."""
    current = _current.get()
    if current is None:
        return ceiling
    left = current.deadline - time.monotonic()
    if left <= 0:
        raise NfclawError(
            ErrorCode.EXECUTION_FAILED, "The run's --timeout ran out.",
            fix="Retry with a larger --timeout; completed evidence is retained when available.",
            details={"timeout_seconds": current.timeout_seconds})
    return left if ceiling is None else min(left, ceiling)


def check() -> None:
    """Refuse another preparation step or a success claim after cancellation."""
    remaining()


@contextmanager
def suspend():
    """Allow failure recording and cleanup to retain evidence after cancellation."""
    token = _current.set(None)
    try:
        yield
    finally:
        _current.reset(token)
