"""JSON numbers without a lossy decimal -> binary float -> decimal round trip.

Ordinary values keep the standard-library implementation. A Decimal is retained only when
the standard float's JSON text would change its value; it is emitted as a number, never a
quoted string. Nextflow parameters use a decimal point for large integer values because its
JSON integer parsing otherwise wraps them to signed 64-bit values. Other records keep integer
literal types. Decimal serialization needs no arithmetic context.
"""
from __future__ import annotations

import json as _json
import math
import sys
from decimal import Decimal, InvalidOperation, localcontext


JSONDecodeError = _json.JSONDecodeError
NUMBER_TYPES = (int, float, Decimal)
_LONG_MIN, _LONG_MAX = -(1 << 63), (1 << 63) - 1


def number(token: str):
    """Parse a finite decimal, keeping a float only when its JSON text has the same value."""
    try:
        approximate = float(token)  # retain the CLI's established numeric-token grammar
        exact = Decimal(token)
    except (ValueError, InvalidOperation) as exc:
        raise ValueError(f"invalid number {token!r}") from exc
    if not exact.is_finite():
        raise ValueError(f"non-finite number {token!r}")
    return (approximate if math.isfinite(approximate) and Decimal(str(approximate)) == exact
            else exact)


def decimal(value):
    """The number represented by its emitted JSON text (rather than a float's binary bits)."""
    return Decimal(str(value)) if isinstance(value, float) else value


def integral(value):
    """Whole JSON values as ints, retaining extreme exponents without allocating expanded digits."""
    exact = Decimal(str(value)) if not isinstance(value, Decimal) else value
    if not exact.is_finite() or exact != exact.to_integral_value():
        raise ValueError("not an integer")
    # An exponent token can describe billions of digits. Keep its compact Decimal form beyond
    # Python's integer-text budget; it is still emitted and validated as a JSON integer value.
    budget = sys.get_int_max_str_digits() or sys.int_info.default_max_str_digits
    return int(exact) if exact.adjusted() < budget else exact


def yaml_float(loader, node):
    """SafeLoader's floating scalar formats, retaining the source's decimal value."""
    token = loader.construct_scalar(node).replace("_", "").lower()
    if token in {".nan", ".inf", "+.inf", "-.inf"}:
        return float(token.replace(".", ""))  # existing finite-number validation rejects these
    if ":" in token:
        with localcontext() as context:
            context.prec = len(token) + 10
            exact = Decimal(0)
            negative = token.startswith("-")
            for part in token.lstrip("+-").split(":"):
                exact = exact * 60 + Decimal(part)
            return number(str(-exact if negative else exact))
    return number(token)


def loads(text, **kwargs):
    kwargs.setdefault("parse_float", number)
    return _json.loads(text, **kwargs)


def _needs_exact_encoding(value, nextflow_compatible):
    pending, seen = [value], set()
    while pending:
        item = pending.pop()
        if (isinstance(item, Decimal)
                or nextflow_compatible and isinstance(item, int)
            and not _LONG_MIN <= item <= _LONG_MAX):
            return True
        if isinstance(item, (list, tuple, dict)) and id(item) not in seen:
            seen.add(id(item))
            if isinstance(item, dict):
                pending.extend(item.keys())
                pending.extend(item.values())
            else:
                pending.extend(item)
    return False


def dumps(value, *, indent=None, sort_keys=False, separators=None, default=None,
          ensure_ascii=True, allow_nan=True, nextflow_compatible=False):
    """Emit exact numbers; `nextflow_compatible` avoids its signed-long parser overflow."""
    options = dict(indent=indent, sort_keys=sort_keys, separators=separators, default=default,
                   ensure_ascii=ensure_ascii, allow_nan=allow_nan)
    if not _needs_exact_encoding(value, nextflow_compatible):
        return _json.dumps(value, **options)
    unit = (indent if isinstance(indent, str)
            else " " * max(0, indent) if indent is not None else None)
    item_sep, key_sep = separators or ((",", ": ") if unit is not None else (", ", ": "))
    active = set()

    def scalar(item):
        return _json.dumps(item, ensure_ascii=ensure_ascii, allow_nan=allow_nan)

    def key_text(key):
        if isinstance(key, str):
            return scalar(key)
        if key is None or isinstance(key, (bool, int, float)):
            return scalar(scalar(key))
        raise TypeError(f"keys must be str, int, float, bool or None, not {type(key).__name__}")

    def encode(item, depth):
        if isinstance(item, Decimal):
            if not item.is_finite():
                raise ValueError("Out of range Decimal values are not JSON compliant")
            text = str(item)
            if nextflow_compatible and "." not in text and "E" not in text:
                text += ".0"
            return text
        if nextflow_compatible and isinstance(item, int) and not _LONG_MIN <= item <= _LONG_MAX:
            return str(item) + ".0"  # force exact BigDecimal rather than a wrapped Long in Nextflow
        if item is None or isinstance(item, (str, bool, int, float)):
            return scalar(item)
        identity = id(item)
        if identity in active:
            raise ValueError("Circular reference detected")
        active.add(identity)
        try:
            if isinstance(item, (list, tuple, dict)):
                if isinstance(item, dict):
                    entries = sorted(item.items()) if sort_keys else item.items()
                    pieces = [key_text(key) + key_sep + encode(child, depth + 1)
                              for key, child in entries]
                    opening, closing = "{", "}"
                else:
                    pieces = [encode(child, depth + 1) for child in item]
                    opening, closing = "[", "]"
                if not pieces:
                    return opening + closing
                if unit is None:
                    return opening + item_sep.join(pieces) + closing
                prefix = "\n" + unit * (depth + 1)
                return (opening + prefix + (item_sep + prefix).join(pieces)
                        + "\n" + unit * depth + closing)
            if default is None:
                raise TypeError(f"Object of type {type(item).__name__} is not JSON serializable")
            return encode(default(item), depth)
        finally:
            active.remove(identity)

    return encode(value, 0)
