from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator
from runner.errors import ErrorCode, NfclawError

from runner import exact_json as json

# nf-schema's path formats: `path` is a file or a directory, `file-path-pattern` a glob.
PATH_FORMATS = ("file-path", "directory-path", "path", "file-path-pattern")
_INPUT_ROLES = Path(__file__).with_name("input_roles.json")


@dataclass(frozen=True)
class Param:
    name: str
    type: str
    default: Any
    enum: tuple[str, ...] | None
    description: str
    fmt: str | None          # "file-path" | "directory-path" | None
    required: bool
    group: str
    # The group's human title from the schema (e.g. "Mandatory arguments" for the `mandatory_arguments`
    # group). The authors' own labelling of what a group means — surfaced in the generated docs.
    group_title: str = ""
    hidden: bool = False      # nf-core marks generic/boilerplate params (email, validation*, …) hidden
    # Value-shape constraints nf-schema enforces at runtime (enum has its own field above).
    pattern: str | None = None
    minimum: int | float | Decimal | None = None
    maximum: int | float | Decimal | None = None
    min_length: int | None = None
    max_length: int | None = None
    deprecated: bool = False
    # A path format alone does not require an existing input: output/cache directories use it too.
    exists: bool | None = None
    # Keep JSON values separately from their documentation text: "1", 1 and true differ.
    enum_values: tuple[Any, ...] | None = None
    type_declared: bool = True


@dataclass(frozen=True)
class ParamSchema:
    title: str
    description: str
    params: dict[str, Param]

    def known_params(self) -> set[str]:
        return set(self.params)

    def reference_path_params(self) -> set[str]:
        """Every parameter whose value names something on a file system — nf-schema's `file-path`,
        `directory-path`, `path` (either) and `file-path-pattern` (a glob)."""
        return {n for n, p in self.params.items() if p.fmt in PATH_FORMATS}

    def groups(self) -> dict[str, list[Param]]:
        out: dict[str, list[Param]] = {}
        for p in self.params.values():
            out.setdefault(p.group, []).append(p)
        return out


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    required: bool
    pattern: str | None
    fmt: str | None = None          # "file-path" | "directory-path" | None — mirrors Param.fmt
    enum: tuple[str, ...] | None = None
    # Same value-shape constraints as Param, so one renderer serves both (no asymmetry).
    minimum: int | float | Decimal | None = None
    maximum: int | float | Decimal | None = None
    min_length: int | None = None
    max_length: int | None = None
    deprecated: bool = False
    meta: tuple[str, ...] = ()
    # What samplesheet generation (runner.sheetgen) reads beyond validation: the schema's default,
    # and the patterns of the column's anyOf/oneOf branches — atacseq declares fastq_2's FastQ
    # pattern only inside `anyOf` (beside an empty-string branch, which is left out here).
    default: Any = None
    alternatives: tuple[str, ...] = ()
    # Older schemas sometimes put formats only on alternatives or omit them entirely.
    # Preserve branch-specific rules; exact-schema source audits fill omissions without
    # treating arbitrary filename-like metadata as data or sentinel values as paths.
    path_branches: tuple[tuple[str | None, str], ...] = ()
    audited_path_format: str | None = None
    path_sentinels: tuple[str, ...] = ()
    path_separator: str | None = None
    path_selector: tuple[str, str] | None = None
    path_count: int | None = None
    audited_identifier: bool = False
    info_identifier_keys: tuple[str, ...] = ()
    info_single_quoted_keys: tuple[str, ...] = ()
    audited_double_quoted: bool = False

    def path_values(self, value: str, row: dict) -> tuple[str, ...]:
        if not self.path_format(value):
            return ()
        if self.path_separator and self.path_selector:
            key, expected = self.path_selector
            if str(row.get(key, "")).upper() == expected.upper():
                values = tuple(part for part in value.split(self.path_separator) if part)
                if self.path_count is not None and len(values) != self.path_count:
                    raise ValueError(f"'{self.name}' requires exactly {self.path_count} paths "
                                     f"delimited by {self.path_separator!r}")
                return values
        return (value,)

    def join_paths(self, paths: tuple[str, ...]) -> str:
        return (self.path_separator or "").join(paths)

    def path_format(self, value: str | None = None) -> str | None:
        if self.fmt in PATH_FORMATS:
            return self.fmt
        if value is not None:
            if value in self.path_sentinels:
                return None
            for pattern, fmt in self.path_branches:
                try:
                    if pattern is None or re.search(pattern, value):
                        return fmt
                except re.error:
                    continue
        elif self.path_branches:
            formats = {fmt for _, fmt in self.path_branches}
            return next(iter(formats)) if len(formats) == 1 else "path"
        return self.audited_path_format

    @property
    def is_path(self) -> bool:
        """Any filesystem path (a file, a directory, or nf-schema's `path` for either) — these values
        must be absolute and get an existence check. A glob (`file-path-pattern`) cannot be checked
        for literal existence; glob matching is left to nf-schema, but the runner still requires
        an absolute local pattern."""
        return self.path_format() in ("file-path", "directory-path", "path")

    @property
    def is_identifier(self) -> bool:
        """Schema-declared identity metadata, plus legacy sample/patient column names.

        Paths and descriptive annotations keep their own contracts; identity values are often
        interpolated into upstream shell scripts and output filenames without escaping.
        """
        if self.path_format() in PATH_FORMATS:
            return False
        name = self.name.casefold().replace("_", "").replace(" ", "")
        return (self.audited_identifier or self.type not in {"object", "array"}
                and name in {"id", "sample", "sampleid", "samplename", "patient", "patientid"}
                or any(key in {"id", "sample", "patient", "sample_name", "sample_alias",
                               "tumour_sample", "normal_sample", "paternal", "maternal",
                               "genome_name", "db_name"}
                       or key.endswith("_id") for key in self.meta))


@dataclass(frozen=True)
class InputSchema:
    columns: tuple[Column, ...]
    # Mutually-exclusive required column groups from the samplesheet's `items.oneOf`: each inner
    # tuple is one allowed set of columns, and a row must satisfy EXACTLY ONE group (e.g.
    # (("bam",), ("cram",)) for createpanelrefs, or (("sampleID","forwardReads"),
    # ("sample","fastq_1")) for ampliseq's legacy-vs-standardized formats). Empty when the schema
    # declares no such choice. nf-schema enforces the full rule (including any `not`/`anyOf`
    # exclusions) at runtime; this captures the choice so the generated docs can surface it.
    one_of: tuple[tuple[str, ...], ...] = ()
    # Conditional row rules from `items.dependentRequired`, plus `items.anyOf` branches that are
    # themselves dependentRequired maps. These are deterministic column-presence constraints, so
    # the runner can fail malformed tabular inputs before launching Nextflow.
    dependent_required: tuple[tuple[str, tuple[str, ...]], ...] = ()
    any_of_dependent_required: tuple[tuple[tuple[str, tuple[str, ...]], ...], ...] = ()
    # `items.anyOf` branches that require columns (mag: short_reads_1 or long_reads), and nf-schema's
    # `uniqueEntries` column combinations (top level or inside a top-level `allOf`). Read by
    # samplesheet generation, which must not write a sheet nf-schema would then reject.
    any_of_required: tuple[tuple[str, ...], ...] = ()
    unique_entries: tuple[tuple[str, ...], ...] = ()
    header_prefix: tuple[str, ...] = ()
    generation_problem: str | None = None
    audit_note: str = ""
    destination_columns: tuple[str, ...] = ()


def json_scalar(value: Any) -> str:
    """A JSON scalar in its JSON literal form — `true`/`false`, not Python's `True`/`False`.
    Used for enum documentation and default rendering. Validation retains typed enum values."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None or isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _type_of(obj: dict) -> str:
    """Render a JSON-schema type, unioning list/anyOf/oneOf variants (e.g. 'integer or string')."""
    t = obj.get("type")
    if isinstance(t, list):                       # JSON Schema allows a type array, e.g. ["boolean","string"]
        types = [str(x) for x in t if x]
        if types:
            return " or ".join(dict.fromkeys(types))
    if t:
        return str(t)
    for key in ("anyOf", "oneOf"):
        variants = obj.get(key)
        if isinstance(variants, list):
            types = [str(v["type"]) for v in variants
                     if isinstance(v, dict) and v.get("type")]
            if types:
                return " or ".join(dict.fromkeys(types))
    return "string"


def iter_param_groups(data: dict) -> Iterator[tuple[str, dict]]:
    """Yield (group_name, group_object) for every parameter group.

    nf-core schemas place groups under "definitions" (older) or "$defs" (newer),
    and may also carry ungrouped top-level "properties". All are tolerated.
    """
    for key in ("definitions", "$defs"):
        defs = data.get(key)
        if isinstance(defs, dict):
            for gname, gobj in defs.items():
                if isinstance(gobj, dict):
                    yield str(gname), gobj
    if isinstance(data.get("properties"), dict):
        yield "", {"properties": data["properties"], "required": data.get("required", [])}


def load_param_schema(repo: Path) -> ParamSchema:
    data = json.loads((repo / "nextflow_schema.json").read_text(encoding="utf-8"))
    params: dict[str, Param] = {}
    for gname, gobj in iter_param_groups(data):
        props = gobj.get("properties")
        if not isinstance(props, dict):
            continue
        required = set(gobj.get("required") or [])
        for pname, pobj in props.items():
            if not isinstance(pobj, dict):
                continue
            enum = pobj.get("enum")
            params[pname] = Param(
                name=pname,
                type=_type_of(pobj),
                default=pobj.get("default"),
                enum=tuple(json_scalar(e) for e in enum) if isinstance(enum, list) else None,
                description=str(pobj.get("description", "")),
                fmt=pobj.get("format"),
                required=pname in required,
                group=gname,
                group_title=str(gobj.get("title") or ""),
                hidden=bool(pobj.get("hidden", False)),
                pattern=pobj.get("pattern"),
                minimum=pobj.get("minimum"),
                maximum=pobj.get("maximum"),
                min_length=pobj.get("minLength"),
                max_length=pobj.get("maxLength"),
                deprecated=bool(pobj.get("deprecated", False)),
                exists=pobj.get("exists") if isinstance(pobj.get("exists"), bool) else None,
                enum_values=tuple(enum) if isinstance(enum, list) else None,
                type_declared=bool(pobj.get("type") or any(
                    isinstance(v, dict) and v.get("type")
                    for variants in (pobj.get("anyOf"), pobj.get("oneOf"))
                    if isinstance(variants, list) for v in variants)),
            )
    return ParamSchema(
        title=str(data.get("title") or repo.name),
        description=str(data.get("description") or ""),
        params=params,
    )


def load_input_schema(repo: Path, rel: str = "assets/schema_input.json") -> InputSchema | None:
    """The samplesheet schema at `rel` inside the pipeline (by default the nf-core convention), or
    None when the file is absent."""
    path = repo / rel
    if not path.exists():
        return None
    content = path.read_bytes()
    data = json.loads(content)
    audited = _audited_input_contract(content, repo)
    audited_roles = audited.get("columns", {})
    data = audited.get("replacement", data)
    items = data.get("items", {})
    props = items.get("properties", {})
    required = set(items.get("required") or [])
    # Mutually-exclusive required column groups: each `items.oneOf` branch that lists `required`
    # columns is one allowed group (a row must satisfy exactly one). Branches without a `required`
    # list carry no column choice and are skipped.
    one_of: list[tuple[str, ...]] = []
    for branch in items.get("oneOf") or []:
        if isinstance(branch, dict):
            req = branch.get("required")
            if isinstance(req, list) and req:
                one_of.append(tuple(str(r) for r in req))
    dependent_required = _dependent_required(items.get("dependentRequired"))
    any_of_dependent_required: list[tuple[tuple[str, tuple[str, ...]], ...]] = []
    any_of_required: list[tuple[str, ...]] = []
    for branch in items.get("anyOf") or []:
        if isinstance(branch, dict):
            deps = _dependent_required(branch.get("dependentRequired"))
            if deps:
                any_of_dependent_required.append(deps)
            req = branch.get("required")
            if isinstance(req, list) and req:
                any_of_required.append(tuple(str(r) for r in req))
    unique_entries = [entry for entry in (
        [data.get("uniqueEntries")]
        + [part.get("uniqueEntries") for part in data.get("allOf") or [] if isinstance(part, dict)])
        if isinstance(entry, list) and entry and all(isinstance(c, str) for c in entry)]
    cols: list[Column] = []
    if isinstance(props, dict):
        for cname, cobj in props.items():
            if not isinstance(cobj, dict):
                continue
            enum = cobj.get("enum")
            meta = cobj.get("meta", [])
            if isinstance(meta, str):
                meta = [meta]
            cols.append(Column(
                name=str(cname),
                type=_type_of(cobj),
                required=cname in required,
                pattern=cobj.get("pattern"),
                fmt=cobj.get("format"),
                enum=tuple(json_scalar(e) for e in enum) if isinstance(enum, list) else None,
                minimum=cobj.get("minimum"),
                maximum=cobj.get("maximum"),
                min_length=cobj.get("minLength"),
                max_length=cobj.get("maxLength"),
                deprecated=bool(cobj.get("deprecated", False)),
                meta=tuple(key for key in meta if isinstance(key, str)) if isinstance(meta, list) else (),
                default=cobj.get("default"),
                alternatives=_branch_patterns(cobj),
                path_branches=_path_branches(cobj),
                audited_path_format=audited_roles.get(cname, {}).get("format"),
                path_sentinels=tuple(audited_roles.get(cname, {}).get("sentinels", [])),
                path_separator=audited_roles.get(cname, {}).get("separator"),
                path_selector=tuple(audited_roles[cname]["selector"]) if audited_roles.get(cname, {}).get("selector") else None,
                path_count=audited_roles.get(cname, {}).get("count"),
                audited_identifier=cname in audited.get("identifiers", []),
                info_identifier_keys=tuple(audited.get("info_identifiers", {}).get(cname, [])),
                info_single_quoted_keys=tuple(audited.get("info_single_quoted", {}).get(cname, [])),
                audited_double_quoted=cname in audited.get("double_quoted_columns", []),
            ))
    header_prefix = tuple(audited.get("header_prefix", []))
    if header_prefix:
        ordered = {name: index for index, name in enumerate(header_prefix)}
        cols.sort(key=lambda column: ordered.get(column.name, len(ordered)))
    return InputSchema(
        columns=tuple(cols),
        one_of=tuple(one_of),
        dependent_required=dependent_required,
        any_of_dependent_required=tuple(any_of_dependent_required),
        any_of_required=tuple(any_of_required),
        unique_entries=tuple(tuple(entry) for entry in unique_entries),
        header_prefix=header_prefix,
        generation_problem=audited.get("generation_problem"),
        audit_note=audited.get("note", ""),
        destination_columns=tuple(audited.get("destination_columns", [])),
    )


def _audited_input_contract(content: bytes, repo: Path) -> dict:
    """Additional consumed-file roles established from the pinned source, by schema digest.

    Added roles fill omitted path annotations. Consumer corrections and destination
    exclusions also require the exact revision and unchanged audited source. Unknown
    schemas retain their explicit path annotations, including annotated alternatives.
    """
    registry = json.loads(_INPUT_ROLES.read_text(encoding="utf-8"))
    audited = registry.get(hashlib.sha256(content).hexdigest(), {})
    if ("replacement" in audited or audited.get("destination_columns") or audited.get("double_quoted_columns")
            or any(role.get("separator") for role in audited.get("columns", {}).values())):
        from runner.submodule import _own_head
        if _own_head(repo) != audited["commit"]:
            raise NfclawError(ErrorCode.SAMPLESHEET_INVALID,
                             "audited samplesheet correction requires its exact pinned pipeline revision",
                             fix="Use the supported pinned release; other stale contracts require a source audit.")
        for name, digest in audited["source_sha256"].items():
            path = repo / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise NfclawError(ErrorCode.SAMPLESHEET_INVALID,
                                 f"audited samplesheet consumer source changed: {path}",
                                 fix="Restore the pinned consumer source before using its corrected input contract.")
    return audited


def _path_branches(obj: dict) -> tuple[tuple[str | None, str], ...]:
    out = []
    for key in ("anyOf", "oneOf"):
        for branch in obj.get(key) or []:
            if not isinstance(branch, dict):
                continue
            if branch.get("format") in PATH_FORMATS:
                out.append((branch.get("pattern"), branch["format"]))
            out.extend(_path_branches(branch))
    return tuple(dict.fromkeys(out))


def _branch_patterns(obj: dict) -> tuple[str, ...]:
    """The string patterns of a column's anyOf/oneOf branches, in schema order."""
    out: list[str] = []
    for key in ("anyOf", "oneOf"):
        for branch in obj.get(key) or []:
            if isinstance(branch, dict) and isinstance(branch.get("pattern"), str):
                out.append(branch["pattern"])
    return tuple(dict.fromkeys(out))


def _dependent_required(obj: Any) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if not isinstance(obj, dict):
        return ()
    out: list[tuple[str, tuple[str, ...]]] = []
    for key, values in obj.items():
        if isinstance(values, list):
            reqs = tuple(str(v) for v in values if v)
            if reqs:
                out.append((str(key), reqs))
    return tuple(out)


_ASSIGNMENT = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def _strip_comment(text: str) -> str:
    """`text` without a trailing `//` comment — one outside quotes (a URL's `//` is not a comment)."""
    quote = None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote and text[i - 1] != "\\":
                quote = None
        elif ch in "'\"":
            quote = ch
        elif text.startswith("//", i):
            return text[:i].rstrip()
    return text.rstrip()


def config_param_defaults(repo: Path) -> dict[str, str]:
    """The defaults the pipeline's own `nextflow.config` assigns in its top-level `params { }` block,
    as {name: value as written}. nf-schema validates the value a parameter ends up with, so a required
    parameter this config sets is supplied even though the schema gives it no default
    (differentialabundance's `filtering_min_abundance = 1`). Only direct assignments at the block's
    first level are read — the block nf-core's template declares every default in."""
    try:
        text = (repo / "nextflow.config").read_text(encoding="utf-8")
    except OSError:
        return {}
    out: dict[str, str] = {}
    depth = 0
    inside = False
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not inside:
            if depth == 0 and re.match(r"^\s*params\s*\{\s*$", line):
                inside, depth = True, 1
                continue
            depth += line.count("{") - line.count("}")
            continue
        if depth == 1 and (m := _ASSIGNMENT.match(line)) and "{" not in m.group(2):
            out.setdefault(m.group(1), m.group(2).strip())
        depth += line.count("{") - line.count("}")
        if depth <= 0:
            break
    return out
