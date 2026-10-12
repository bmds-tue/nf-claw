"""What a pipeline's `--input` value is: a samplesheet, another local path, or a plain value.

nf-core pipelines do not all take a samplesheet. Releases in this library also take a directory or
tarball (rangeland), an SDRF file or a PRIDE accession (mhcquant), and `--input false` to run without
one (sarek). The pipeline's own `nextflow_schema.json` says which, so nfclaw reads it from
there instead of assuming: a value is only resolved to a local path, and only pre-checked as a
samplesheet, when the schema (or the file system) says that is what it is.

nf-schema validates `--input` against a samplesheet schema named by the parameter's `schema` key,
possibly inside an `if`/`then` branch. Older releases name no schema on the parameter yet ship the
conventional `assets/schema_input.json` and read it themselves; that convention is honoured only
when the parameter is declared a file (rangeland ships the template file but takes a directory).
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from runner.schema import PATH_FORMATS, iter_param_groups

DEFAULT_SAMPLESHEET_SCHEMA = "assets/schema_input.json"
_FILE_URI_ISSUE = ("file: URI inputs are local dependencies; use an absolute filesystem path "
                   "so staged filenames and local data can be validated and recorded for replay")
# Keywords that describe a value without constraining it; anything else in an `if` is not decided.
_ANNOTATIONS = ("description", "errorMessage", "title", "$comment", "help_text", "fa_icon")


@dataclass(frozen=True)
class ResolvedInput:
    value: Any                           # the params-file value; False = leave `input` unset
    local_path: Path | None              # the local file/directory the value names, if any
    samplesheet_schema: str | None       # schema file (relative to the pipeline) to pre-check it with
    must_exist: bool = False             # the schema declares `exists: true` for this value


def input_param(repo: Path, name: str = "input") -> dict | None:
    """The raw schema object of parameter `name` (by default `input`), or None when the pipeline
    declares no such parameter."""
    data = json.loads((repo / "nextflow_schema.json").read_text(encoding="utf-8"))
    for _, group in iter_param_groups(data):
        props = group.get("properties")
        if isinstance(props, dict) and isinstance(props.get(name), dict):
            return props[name]
    return None


def _schema_ref(obj: dict) -> str | None:
    ref = obj.get("schema")
    return ref.lstrip("/") if isinstance(ref, str) and ref.strip("/") else None


def _branches(param: dict) -> list[dict]:
    out = [param.get(k) for k in ("then", "else")]
    for key in ("anyOf", "oneOf", "allOf"):
        if isinstance(param.get(key), list):
            out += param[key]
    return [b for b in out if isinstance(b, dict)]


def _legacy_samplesheet(repo: Path, param: dict) -> str | None:
    """The conventional samplesheet schema, for a release that names none on the parameter."""
    if any(_schema_ref(b) for b in [param, *_branches(param)]):
        return None                                      # the release says which schema applies
    if param.get("format") != "file-path":
        return None                                      # e.g. a directory or tarball, never a sheet
    return DEFAULT_SAMPLESHEET_SCHEMA if (repo / DEFAULT_SAMPLESHEET_SCHEMA).is_file() else None


def samplesheet_schema(repo: Path, param: str = "input") -> str | None:
    """The samplesheet schema parameter `param` (by default `--input`) is documented against, in any
    of its input modes.

    None when the parameter is not a samplesheet at all (or does not exist), so the generated docs
    never present a template `schema_input.json` the release does not use. The conventional
    `assets/schema_input.json` of a release that names no schema is the `--input` sheet's only."""
    obj = input_param(repo, param)
    if obj is None:
        return None
    for part in (obj, *_branches(obj)):
        ref = _schema_ref(part)
        if ref:
            return ref if (repo / ref).is_file() else None
    return _legacy_samplesheet(repo, obj) if param == "input" else None


def samplesheet_parameters(repo: Path) -> tuple[str, ...]:
    """Parameters with an explicit samplesheet schema in a supported schema branch."""
    data = json.loads((repo / "nextflow_schema.json").read_text(encoding="utf-8"))
    names = []
    for _, group in iter_param_groups(data):
        for name, obj in (group.get("properties") or {}).items():
            if isinstance(obj, dict) and any(_schema_ref(part) for part in (obj, *_branches(obj))):
                names.append(name)
    return tuple(dict.fromkeys(names))


def local_name_issues(value: str, fmt: str, *, inspect_contents: bool = True) -> list[str]:
    """Staged names passed into task shell scripts, including explicit remote basenames.

    Parent directories are not staged under their original names; this guards the basename.
    Also check directory contents and resolved symlink targets: downstream workflows can select
    children as separate inputs or derive prefixes from their names.
    Missing glob matches and remote inventories remain the runtime schema's responsibility.
    Remote basenames retain percent escapes in Nextflow; do not decode or rewrite scientific
    inputs. HTTP/FTP providers remove the query suffix, but retain a standalone fragment in the
    staged name. Object-store paths such as S3 retain both as literal key characters.
    HTTP/FTP providers stage literal names even for a schema pattern. Audited output-only
    directories can disable descendant inspection, while their own and symlink target names
    always retain the literal guard.
    """
    if value.strip().lower().startswith("file:"):
        return [_FILE_URI_ISSUE]
    from runner.replay_guard import MissingInputSource, inspect_input_paths

    def safe_name(name: str, *, pattern=False) -> bool:
        extra = "._-+@%=,:~" + ("*?[]{}" if pattern else "")
        return (not name.startswith(("-", "~"))
                and all(char.isalnum() or char in extra
                        or unicodedata.category(char).startswith("M") for char in name))

    pattern = fmt == "file-path-pattern"
    if "://" in value:
        # urlsplit silently removes tabs/newlines. Refuse those before parsing, rather than
        # checking a different URL from the one supplied to Nextflow.
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            return ["remote input URL contains control characters"]
        try:
            parsed = urlsplit(value)
            remote_path = value.split("://", 1)[1].partition("/")[2]
            literal_transport = parsed.scheme.lower() in {"http", "https", "ftp"}
            if literal_transport:
                remote_path = remote_path.split("?", 1)[0]
            name = remote_path.rstrip("/").rsplit("/", 1)[-1]
        except ValueError as exc:
            return [f"cannot inspect remote input filename: {exc}"]
        if not safe_name(name, pattern=pattern and not literal_transport):
            return [f"unsafe remote input filename {name!r}; use a safely named remote object "
                    "or download it to a safely named local file"]
        return []
    path = Path(value).expanduser()

    class UnsafeName(ValueError):
        pass

    def check_name(name: str, *, is_pattern=False):
        if not safe_name(name, pattern=is_pattern):
            raise UnsafeName(name)

    def check_path(item: Path):
        check_name(item.name)
        check_name(item.resolve().name)

    try:
        check_name(path.name, is_pattern=pattern)
        check_name(path.resolve().name, is_pattern=pattern)
        if inspect_contents and (pattern or path.is_dir()):
            try:
                inspect_input_paths([path], check_path)
            except MissingInputSource:
                pass
    except UnsafeName as exc:
        return [f"unsafe local input filename {str(exc)!r} in {value!r}; use a renamed or copied "
                "input with literal filename characters (letters, digits, combining marks, "
                "dots, underscores, hyphens, plus, @, %, =, commas, colons or interior ~)"]
    except (OSError, RuntimeError) as exc:
        return [f"cannot inspect local input filenames for {value!r}: {exc}"]
    return []


def shell_path_issues(value: str) -> list[str]:
    """Audited parameters interpolated as whole unquoted paths rather than staged basenames."""
    try:
        candidates = [value, str(Path(value).expanduser().resolve())]
    except (OSError, RuntimeError, ValueError) as exc:
        return [f"cannot inspect local input path {value!r}: {exc}"]
    allowed = "/._-+@%=,:~"
    if any(not all(char.isalnum() or char in allowed or unicodedata.category(char).startswith("M")
                   for char in path) for path in candidates):
        return [f"unsafe local input path {value!r}; the pinned task uses the complete path "
                "as an unquoted argument, so all parent folders and symlink targets must be safely named"]
    return []


def _satisfies(sub: object, value: str) -> bool | None:
    """Whether `value` satisfies an `if` subschema — True/False, or None when it cannot be decided.

    Deliberately tiny: `pattern`, `not`, `allOf`/`anyOf` and a string `type`. Anything else is left
    to nf-schema at runtime rather than guessed."""
    if not isinstance(sub, dict):
        return None
    result = True
    for key, rule in sub.items():
        if key in _ANNOTATIONS:
            continue
        if key == "pattern" and isinstance(rule, str):
            try:
                ok: bool | None = re.search(rule, value) is not None
            except re.error:
                return None
        elif key == "not":
            inner = _satisfies(rule, value)
            ok = None if inner is None else not inner
        elif key in ("allOf", "anyOf") and isinstance(rule, list):
            parts = [_satisfies(r, value) for r in rule]
            if None in parts:
                return None
            ok = all(parts) if key == "allOf" else any(parts)
        elif key == "type":
            ok = rule == "string" or (isinstance(rule, list) and "string" in rule)
        else:
            return None
        if ok is None:
            return None
        result = result and ok
    return result


def _applicable(param: dict, value: str) -> list[dict] | None:
    """The parts of the `input` schema that apply to a string `value`, or None if undecidable."""
    parts = [param]
    if "if" in param:
        cond = _satisfies(param["if"], value)
        if cond is None:
            return None
        branch = param.get("then" if cond else "else")
        if isinstance(branch, dict):
            parts.append(branch)
    for key in ("anyOf", "oneOf"):
        for branch in param.get(key) or []:
            if isinstance(branch, dict) and branch.get("type", "string") in ("string", ["string"]):
                parts.append(branch)
    for branch in param.get("allOf") or []:
        if isinstance(branch, dict):
            parts.append(branch)
    return parts


def resolve(raw: Any, repo: Path, *, param_name: str = "input") -> ResolvedInput | None:
    """Interpret an `--input` value the way the pipeline's schema declares it.

    The value is the `--input` flag or, without one, the params-file `input` — the same value means
    the same thing from either source. A params file can also hold a non-string:
    - a YAML/JSON boolean `false` is `--input false`;
    - any other non-string value is forwarded unchanged, for parameter validation to report;
    and a string is interpreted as follows:
    - an empty value is forwarded unchanged, so a required `--input` is reported missing;
    - a remote URL is forwarded unchanged (Nextflow stages it, nf-schema validates it);
      local `file:` URIs must instead use an absolute filesystem path;
    - `false` means "no input" — sarek's documented way to run without a samplesheet. It is returned
      as the value `False`, which `parameters.merge` turns into an unset `input`: a boolean false is
      rejected by nf-schema 2.7 for a string `input`, an unset one passes every version;
    - a local path is made absolute against the caller's directory (Nextflow runs from `--outdir`),
      when the schema declares a path or the value names an existing file or directory;
    - anything else (e.g. a PRIDE accession) is forwarded unchanged.
    The samplesheet pre-check applies only where the schema says the value is a samplesheet."""
    if raw is None:
        return None
    if raw is False:
        return ResolvedInput(False, None, None)
    if not isinstance(raw, (str, Path)):
        return ResolvedInput(raw, None, None)
    text = str(raw)
    if text.strip().lower().startswith("file:"):
        from runner.errors import ErrorCode, NfclawError
        raise NfclawError(ErrorCode.PARAMS_INVALID, _FILE_URI_ISSUE)
    if not text.strip():
        return ResolvedInput(text, None, None)           # "not set": never the caller's directory
    if "://" in text:
        param = input_param(repo, param_name) or {}
        parts = _applicable(param, text) or []
        fmt = next((part["format"] for part in parts if part.get("format") in PATH_FORMATS),
                   "file-path")
        if issues := local_name_issues(text, fmt):
            from runner.errors import ErrorCode, NfclawError
            raise NfclawError(ErrorCode.PARAMS_INVALID, "Input filename failed validation.",
                              details={"issues": issues})
        return ResolvedInput(text, None, None)
    if param_name == "input" and text.strip().lower() == "false":
        return ResolvedInput(False, None, None)
    param = input_param(repo, param_name) or {}
    parts = _applicable(param, text) if param else []
    sheet = None
    if parts is not None:
        sheet = next((ref for ref in map(_schema_ref, parts) if ref), None)
        if sheet is None and param and param_name == "input":
            sheet = _legacy_samplesheet(repo, param)
    declared = parts or []
    path_like = sheet is not None or any(p.get("format") in PATH_FORMATS for p in declared)
    if not (isinstance(raw, Path) or path_like or Path(text).expanduser().exists()):
        return ResolvedInput(text, None, None)
    local = Path(text).expanduser().resolve()
    return ResolvedInput(str(local), local, sheet,
                         must_exist=any(p.get("exists") is True for p in declared))
