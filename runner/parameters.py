from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from runner.errors import ErrorCode, NfclawError
from runner.inputs import absolute_local_path, is_remote_url, local_name_issues, shell_path_issues
from runner.schema import PATH_FORMATS, Param, ParamSchema, json_scalar

# The nf-core template parameter that suffixes the execution report/timeline/trace/DAG filenames.
_REPORT_SUFFIX = "trace_report_suffix"


def _unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate parameter key {key!r}")
        out[key] = value
    return out


def _reject_cycles(value: Any) -> None:
    """YAML aliases may share values, but recursive aliases have no JSON representation."""
    active, completed = set(), set()
    pending = [(value, False)]
    while pending:
        item, leaving = pending.pop()
        if not isinstance(item, (Mapping, list, tuple)):
            continue
        identity = id(item)
        if leaving:
            active.remove(identity)
            completed.add(identity)
        elif identity in active:
            raise ValueError("cyclic parameter value (recursive YAML alias)")
        elif identity not in completed:
            active.add(identity)
            pending.append((item, True))
            pending.extend((child, False) for child in
                           (item.values() if isinstance(item, Mapping) else item))


def validate_params(cli_overrides: dict[str, Any], schema: ParamSchema, *,
                    output_only_dirs: frozenset[str] = frozenset(),
                    shell_paths: frozenset[str] = frozenset()) -> list[str]:
    """Deterministic, schema-driven validation of agent-supplied flags (errors, not heuristics).

    Settles the two classes the schema makes unambiguous: unknown flags (not in the schema)
    and values outside an enum's allowed set. Required-ness and types are left to nf-schema
    at runtime, which handles the schema's conditionals correctly (so we never false-positive).
    """
    known = schema.known_params()
    errors: list[str] = []
    for key, value in cli_overrides.items():
        if not isinstance(key, str):
            errors.append(f"parameter name must be a string, got {key!r}")
            continue
        flag = f"--{key.replace('_', '-')}"
        if key not in known:
            errors.append(f"unknown parameter '{flag}' (not in the pipeline schema)")
        elif not _finite(value):
            # NaN/Infinity (a YAML `.nan`/`.inf`) has no JSON form: the params file Nextflow reads
            # would be invalid, whatever type the schema declares.
            errors.append(f"parameter '{flag}' must be a finite number, got {value!r}")
        elif value is None or value is False or value == "":
            # null is dropped by every nf-schema release; false/"" are dropped by 2.5–2.6 but rejected
            # by 2.7 (verified). A verdict that depends on the plugin version is not unambiguous, so
            # it is left to nf-schema at runtime rather than risk rejecting a valid run.
            continue
        else:
            param = schema.params[key]
            if key != "outdir" and param.fmt in PATH_FORMATS and isinstance(value, str) and value.strip():
                errors.extend(f"parameter '{flag}': {issue}"
                              for issue in local_name_issues(
                                  value, param.fmt, resolve_parent=True, inspect_contents=key not in output_only_dirs))
                if key in shell_paths:
                    errors.extend(f"parameter '{flag}': {issue}" for issue in shell_path_issues(value))
            if param.enum and not _in_enum(value, param.enum):
                errors.append(f"parameter '{flag}={value}' is not allowed; "
                              f"must be one of: {', '.join(param.enum)}")
            if not (param.enum and _in_enum(value, param.enum)):
                errors.extend(_value_shape_errors(flag, value, param))
    return errors


def _in_enum(value: Any, enum: tuple[str, ...]) -> bool:
    """Whether `value` is one of a schema's allowed values. JSON Schema compares numbers by value
    (`1.0` equals `1`), so a numeric value matches a numeric entry written either way."""
    if json_scalar(value) in enum:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        for entry in enum:
            try:
                if float(entry) == value:
                    return True
            except ValueError:
                continue
    return False


_UNSET = ("null", "''", '""')


def missing_required_params(merged: dict[str, Any], schema: ParamSchema,
                            configured: Mapping[str, str] | None = None) -> list[str]:
    """Schema-required params without defaults must be supplied before launching Nextflow.

    Required params that carry a default are intentionally not flagged — in the schema, or in the
    pipeline's own `nextflow.config` (`configured`, from `schema.config_param_defaults`): nf-schema
    validates the value a parameter ends up with, and generated docs surface the schema's default so
    agents do not need to invent a value. A config assignment to null or "" supplies nothing.
    """
    errors: list[str] = []
    for name, param in schema.params.items():
        if not param.required or param.default is not None:
            continue
        if (configured or {}).get(name, "null") not in _UNSET:
            continue
        value = merged.get(name)
        if value is None or value == "":
            errors.append(f"missing required parameter '--{name.replace('_', '-')}'")
    return errors


def _value_shape_errors(flag: str, value: Any, param: Param) -> list[str]:
    errors: list[str] = []
    scalar_type = param.type
    if scalar_type == "string" and not isinstance(value, str):
        errors.append(f"parameter '{flag}' expects a string, got {type(value).__name__}")
        return errors
    if scalar_type == "boolean" and not isinstance(value, bool):
        errors.append(f"parameter '{flag}' expects a boolean, got {type(value).__name__}")
        return errors
    if scalar_type == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        errors.append(f"parameter '{flag}' expects an integer, got {type(value).__name__}")
        return errors
    if scalar_type == "number" and (
        not isinstance(value, (int, float)) or isinstance(value, bool)
    ):
        errors.append(f"parameter '{flag}' expects a number, got {type(value).__name__}")
        return errors
    if param.pattern and isinstance(value, str):
        try:
            matches = re.search(param.pattern, value) is not None
        except re.error:
            matches = True
        if not matches:
            errors.append(f"parameter '{flag}' value {value!r} must match {param.pattern}")
    if param.min_length is not None and isinstance(value, str) and len(value) < param.min_length:
        errors.append(f"parameter '{flag}' length >= {param.min_length} required")
    if param.max_length is not None and isinstance(value, str) and len(value) > param.max_length:
        errors.append(f"parameter '{flag}' length <= {param.max_length} required")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if param.minimum is not None and value < param.minimum:
            errors.append(f"parameter '{flag}' must be >= {param.minimum}")
        if param.maximum is not None and value > param.maximum:
            errors.append(f"parameter '{flag}' must be <= {param.maximum}")
    return errors


_LEAVE = object()       # sentinel: "not coercible — leave the value untouched"


def _coerce_scalar(value: str, type_: str):
    """Convert a CLI string to its schema scalar type, or `_LEAVE` if it can't be done
    unambiguously (so nf-schema reports a precise error on the original string)."""
    if type_ == "boolean":
        low = value.strip().lower()
        return True if low == "true" else False if low == "false" else _LEAVE
    if type_ == "integer":
        try:
            return int(value.strip())
        except ValueError:
            return _LEAVE
    if type_ == "number":
        try:
            number = float(value.strip())
        except ValueError:
            return _LEAVE
        # `nan`/`inf` parse as floats but have no JSON form; left as a string, they are reported.
        return number if math.isfinite(number) else _LEAVE
    return _LEAVE           # string, or a union like "integer or string" — ambiguous, leave it


def coerce_to_schema(merged: dict[str, Any], schema: ParamSchema) -> dict[str, Any]:
    """Coerce CLI-string values to their schema-declared scalar type so `--skip-busco true` or
    `--max-cpus 4` reach nf-schema as a real boolean/integer/number, not a string. Only the
    unambiguous scalar types are touched; strings, union types and unparseable values are left
    as-is. Values from a params-file are already typed, so this is a no-op for them."""
    out = dict(merged)
    for key, val in merged.items():
        param = schema.params.get(key)
        if param is None:
            continue
        if (param.type == "integer" and isinstance(val, float) and math.isfinite(val)
                and val.is_integer()):
            # JSON Schema counts 4.0 as an integer; pass the pipeline the integer its schema
            # declares rather than a float it may interpolate as "4.0".
            out[key] = int(val)
            continue
        if not isinstance(val, str):
            continue
        coerced = _coerce_scalar(val, param.type)
        if coerced is not _LEAVE:
            out[key] = coerced
    return out


def pin_report_suffix(merged: dict[str, Any], schema: ParamSchema,
                      *, now: datetime | None = None) -> dict[str, Any]:
    """Pin `trace_report_suffix` so the run's report filenames are fixed, not "whenever this ran".

    The nf-core template defaults this parameter to `new java.util.Date().format('yyyy-MM-dd_HH-mm-ss')`
    — a *fresh timestamp evaluated on every launch* — and interpolates it into the names of the
    execution report, timeline, trace and DAG under `pipeline_info/`. Left alone, replaying a run
    through `provenance/commands.sh` writes a second set of reports under new names instead of
    reproducing the original run's outputs, so the bundle is not a strict reproduction and
    `outputs.sha256` can never be checked against it.

    Recording the value the run actually used turns that timestamp from an implicit, unrepeatable
    default into a recorded input: it lands in `provenance/params.json`, which `commands.sh` passes
    back with `-params-file`, so a replay names its reports exactly as the original did.

    Only applied when the pinned release declares the parameter (older releases predate it) and
    never overrides a value the caller supplied. The format matches the pipeline's own, so the
    filenames look exactly as they would from a plain `nextflow run`.
    """
    if _REPORT_SUFFIX not in schema.params or merged.get(_REPORT_SUFFIX):
        return merged
    stamp = (now or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    return {**merged, _REPORT_SUFFIX: stamp}


def load_params_file(path: Path, *, label: str = "--params-file") -> dict:
    """A JSON or YAML map of parameters. `label` names the file in errors (a chain spec is
    read with the same loader)."""
    # utf-8-sig so a leading UTF-8 BOM (e.g. from a Windows editor) is stripped: json.loads rejects
    # a BOM outright, so without this a BOM'd params file fails with a cryptic parse error. No-op
    # without a BOM. A binary file (e.g. an .xlsx by mistake) raises UnicodeDecodeError — report it
    # as a clear error rather than a raw traceback.
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise NfclawError(
            ErrorCode.PARAMS_INVALID,
            f"{label} is not valid UTF-8 text: {path}",
            fix="Pass a plain-text JSON or YAML file, not a binary one.") from exc
    except OSError as exc:
        raise NfclawError(
            ErrorCode.PARAMS_INVALID,
            f"{label} cannot be read: {exc.strerror or exc}: {path}",
            fix="Pass a params file you can read.") from exc
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text, object_pairs_hook=_unique_pairs)
        except (ValueError, RecursionError) as exc:
            raise NfclawError(
                ErrorCode.PARAMS_INVALID,
                f"{label} is not valid JSON: {path} ({exc})",
                fix="Fix the JSON syntax, or use a .yaml params file.") from exc
    else:
        try:
            import yaml  # optional dependency
        except ModuleNotFoundError as exc:
            raise NfclawError(
                ErrorCode.ENVIRONMENT,
                f"Reading YAML {label} '{path}' requires pyyaml.",
                fix="Use a .json params file, or `pip install pyyaml`.",
            ) from exc
        try:
            class UniqueLoader(yaml.SafeLoader):
                def construct_mapping(self, node, deep=False):
                    # Check explicit keys before expanding valid YAML merge overrides.
                    keys = set()
                    for key_node, _ in node.value:
                        if key_node.tag == "tag:yaml.org,2002:merge":
                            continue
                        key = self.construct_object(key_node, deep=deep)
                        try:
                            if key in keys:
                                raise yaml.constructor.ConstructorError(
                                    None, None, f"duplicate parameter key {key!r}", key_node.start_mark)
                            keys.add(key)
                        except TypeError:
                            pass  # SafeLoader reports unhashable keys with a source location.
                    return super().construct_mapping(node, deep=deep)

            loader = UniqueLoader(text)
            try:
                data = loader.get_single_data()
            finally:
                loader.dispose()
            # Only an empty YAML document means an empty map. Falsy scalars and sequences are
            # malformed params files too; `or {}` silently discarded them.
            if data is None and yaml.compose(text) is None:
                data = {}
        except (yaml.YAMLError, RecursionError) as exc:
            raise NfclawError(
                ErrorCode.PARAMS_INVALID,
                f"{label} is not valid YAML: {path} ({exc})",
                fix="Fix the YAML syntax, or use a .json params file.") from exc
    # A params file is a map of parameter -> value (what Nextflow's -params-file expects). A
    # top-level list or scalar is malformed; catch it here with a clear error instead of letting
    # the later `dict.update()` blow up with a cryptic TypeError.
    if not isinstance(data, dict):
        what = " of parameters" if label == "--params-file" else ""
        raise NfclawError(
            ErrorCode.PARAMS_INVALID,
            f"{label} must contain an object{what}, got {type(data).__name__}: {path}",
            fix='Use a top-level object like {"param": value}, not a list or a bare scalar.')
    if any(not isinstance(key, str) for key in data):
        raise NfclawError(
            ErrorCode.PARAMS_INVALID, f"{label} parameter names must be strings: {path}",
            fix="Use named parameters as object keys, such as aligner: star.")
    try:
        _reject_cycles(data)
    except ValueError as exc:
        raise NfclawError(ErrorCode.PARAMS_INVALID, f"{label}: {exc}: {path}",
                          fix="Replace recursive aliases with finite JSON-compatible values.") from exc
    return data


def merge(*, cli_overrides: dict[str, Any], params_file: "Path | Mapping[str, Any] | None",
          input_path: Any, outdir: Path) -> dict[str, Any]:
    """Build the full parameter map (params-file < --input/--outdir < CLI) without touching
    disk, so the merged result can be validated before anything is written or executed.
    `params_file` is a path to load, or values already loaded with `load_params_file`.
    `input_path=False` (`--input false`) leaves `input` unset — overriding a params-file value."""
    merged: dict[str, Any] = {}
    if isinstance(params_file, Mapping):
        merged.update(params_file)
    elif params_file and params_file.exists():
        merged.update(load_params_file(params_file))
    if input_path is False:
        merged.pop("input", None)
    elif input_path is not None:
        merged["input"] = str(input_path) if isinstance(input_path, Path) else input_path
    merged["outdir"] = str(outdir)
    merged.update(cli_overrides)
    return merged


def resolve_path_params(merged: dict[str, Any], schema: ParamSchema) -> dict[str, Any]:
    """Make every path param absolute. nfclaw launches Nextflow from --outdir, so a relative path
    would otherwise resolve against the output directory, not the caller's directory."""
    refs = schema.reference_path_params()
    out = dict(merged)
    for key, val in out.items():
        # An empty value means "not set" (the pipeline tests its truthiness); resolving it would
        # silently turn it into the caller's working directory.
        if key in refs and isinstance(val, str) and val.strip() and not is_remote_url(val):
            out[key] = absolute_local_path(val).as_posix()
    return out


def _finite(value: Any) -> bool:
    """False for a NaN/Infinity anywhere in `value` (JSON has no literal for either)."""
    pending, seen = [value], set()
    while pending:
        item = pending.pop()
        if isinstance(item, float) and not math.isfinite(item):
            return False
        if isinstance(item, (Mapping, list, tuple)) and id(item) not in seen:
            seen.add(id(item))
            pending.extend(item.values() if isinstance(item, Mapping) else item)
    return True


def write_params_file(params: dict[str, Any], dest: Path) -> Path:
    # allow_nan=False: Python would otherwise write the non-standard `NaN`/`Infinity` literals, which
    # Nextflow cannot parse. Validation reports such values first; this is the backstop.
    try:
        text = json.dumps(params, indent=2, sort_keys=True, allow_nan=False)
    except ValueError as exc:
        raise NfclawError(ErrorCode.PARAMS_INVALID,
                          f"Parameters cannot be written as JSON: {exc}",
                          fix="Use finite numbers only (no NaN or Infinity).") from exc
    except TypeError as exc:
        raise NfclawError(ErrorCode.PARAMS_INVALID,
                          f"Parameters cannot be written as JSON: {exc}",
                          fix="Use JSON-compatible values; quote YAML dates as strings and use "
                              "lists rather than sets.") from exc
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text + "\n", encoding="utf-8")
    return dest
