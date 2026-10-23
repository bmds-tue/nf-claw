"""Handoffs: how one finished pipeline run becomes the next pipeline's parameters.

A handoff rule is data, not code: `handoffs/<upstream>/<downstream>.json`. Where a pipeline publishes
a samplesheet for another one, and which columns it holds, is in no schema, so it cannot be derived
the way skill.md is — but everything a rule claims about either pipeline's *parameters and
samplesheet columns* is checked against their pinned schemas (`check_rule`, also run by the drift
gate), so a release that breaks a rule is caught the day it is pinned. The runner itself still knows
no pipeline: which parameter takes a samplesheet, and which of its columns hold paths, come from the
downstream schema.

A rule maps downstream parameters to sources:
- `samplesheet`    — a sheet the upstream already wrote for the target, copied (optionally with
                     columns renamed or set) — the direct handoff;
- `build`          — a sheet built from upstream output files matched by a `{placeholder}` pattern;
- `file`           — one upstream output file (a glob that must match exactly one);
- `upstream_param` — a value the upstream run itself used, from its `provenance/params.json`.
"""
from __future__ import annotations

import csv
import hashlib
import os
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from runner import inputs, parameters, provenance, samplesheet
from runner import outputs as output_mod
from runner import schema as schema_mod
from runner import exact_json as json
from runner.errors import ErrorCode, NfclawError
from runner.outputs import is_result

REGISTRY_DIRNAME = "handoffs"
KINDS = ("samplesheet", "build", "file", "upstream_param")
_RULE_KEYS = {"description", "upstream_params", "params"}
_EXTRA_KEYS = {"samplesheet": {"provides", "rename", "set", "add_empty", "drop_rows_not_allowed",
                               "require_values", "allowed_values"},
               "build": set(), "file": {"paired_with"}, "upstream_param": set()}
_BUILD_KEYS = {"rows", "columns", "format"}
PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass(frozen=True)
class Source:
    kind: str                         # one of KINDS
    spec: Mapping[str, Any]           # the rule's source object, as written
    optional: bool = False            # unresolvable → leave the parameter unset instead of failing


@dataclass(frozen=True)
class Rule:
    upstream: str
    downstream: str
    origin: str                       # where it came from: `handoffs/a/b.json`, a path, or inline
    description: str
    upstream_params: Mapping[str, Any]   # set on the upstream run so it writes what is handed over
    params: Mapping[str, Source]         # downstream parameter -> where its value comes from
    raw: Mapping[str, Any]               # the rule exactly as written (recorded with every handoff)

    def sha256(self) -> str:
        text = json.dumps(self.raw, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


def registry_dir(repo_root: Path) -> Path:
    return repo_root / REGISTRY_DIRNAME


def _flag(name: str) -> str:
    return f"--{name.replace('_', '-')}"


def _relative(pattern: object) -> bool:
    """A path or glob that stays inside the upstream outdir: relative, and never climbing out."""
    if not isinstance(pattern, str) or not pattern.strip():
        return False
    path = PurePosixPath(pattern.rstrip("?"))
    return not path.is_absolute() and ".." not in path.parts


def _str_map(value: object) -> bool:
    return isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str)
                                           for k, v in value.items())


def parse_rule(data: Any, *, upstream: str, downstream: str, origin: str) -> Rule:
    """Check a rule's shape (not yet its fit with any pipeline — that is `check_rule`)."""
    def bad(message: str) -> NfclawError:
        return NfclawError(ErrorCode.PARAMS_INVALID, f"handoff rule {origin}: {message}",
                           fix="See docs/chaining.md for the rule format.")

    if not isinstance(data, dict):
        raise bad("must be a JSON object")
    if unknown := sorted(set(data) - _RULE_KEYS):
        raise bad(f"unknown keys: {', '.join(unknown)}")
    up = data.get("upstream_params", {})
    if not isinstance(up, dict):
        raise bad("'upstream_params' must be an object of upstream parameters")
    params = data.get("params")
    if not isinstance(params, dict) or not params:
        raise bad("'params' must map at least one downstream parameter to a source")
    sources: dict[str, Source] = {}
    for target, src in params.items():
        if not isinstance(src, dict):
            raise bad(f"'{target}' must be an object")
        kinds = [k for k in KINDS if k in src]
        if len(kinds) != 1:
            raise bad(f"'{target}' needs exactly one of: {', '.join(KINDS)}")
        kind = kinds[0]
        if extra := sorted(set(src) - {kind, "optional"} - _EXTRA_KEYS[kind]):
            raise bad(f"'{target}': unknown keys for a {kind} source: {', '.join(extra)}")
        if "optional" in src and not isinstance(src["optional"], bool):
            raise bad(f"'{target}': 'optional' must be true or false")
        if kind == "samplesheet" and not _relative(src[kind]):
            raise bad(f"'{target}': {src[kind]!r} must be a relative path inside the upstream "
                      "outdir")
        if kind == "file" and not (_relative(src[kind]) or (
                isinstance(src[kind], list) and src[kind] and all(map(_relative, src[kind])))):
            raise bad(f"'{target}': {src[kind]!r} must be a relative path inside the upstream "
                      "outdir, or a list of them (tried in order)")
        if kind == "upstream_param" and not (isinstance(src[kind], str) and src[kind]):
            raise bad(f"'{target}': 'upstream_param' must name an upstream parameter")
        if kind == "samplesheet":
            provides = src.get("provides")
            if not (isinstance(provides, list) and provides
                    and all(isinstance(c, str) and c for c in provides)):
                raise bad(f"'{target}': a samplesheet source must list the columns it 'provides'")
            for key in ("rename", "set"):
                if key in src and not _str_map(src[key]):
                    raise bad(f"'{target}': '{key}' must map column names to strings")
            for key in ("add_empty", "drop_rows_not_allowed", "require_values"):
                cols = src.get(key, [])
                if not (isinstance(cols, list) and all(isinstance(c, str) and c for c in cols)):
                    raise bad(f"'{target}': '{key}' must list column names")
            allowed = src.get("allowed_values", {})
            if not (isinstance(allowed, dict) and all(
                    isinstance(c, str) and c and isinstance(v, list) and v
                    and all(isinstance(x, str) and x for x in v) for c, v in allowed.items())):
                raise bad(f"'{target}': 'allowed_values' must map column names to lists of values")
        if kind == "build":
            _check_build(src["build"], target, bad)
        sources[target] = Source(kind, src, bool(src.get("optional", False)))
    # `paired_with`: a file list whose candidates belong to another file list's, index by index
    # (rnaseq's gene lengths to the counts of the same quantification). The partner's choice decides.
    for target, source in sources.items():
        if "paired_with" not in source.spec:
            continue
        partner = source.spec["paired_with"]
        other = sources.get(partner) if isinstance(partner, str) else None
        if (other is None or partner == target or other.kind != "file"
                or "paired_with" in other.spec
                or not isinstance(source.spec["file"], list)
                or not isinstance(other.spec["file"], list)
                or len(source.spec["file"]) != len(other.spec["file"])):
            raise bad(f"'{target}': 'paired_with' must name another parameter whose 'file' list "
                      "is as long as this one's")
    return Rule(upstream, downstream, origin, str(data.get("description", "")), dict(up),
                sources, data)


def _check_build(build: object, target: str, bad) -> None:
    if not isinstance(build, dict) or set(build) - _BUILD_KEYS:
        raise bad(f"'{target}': 'build' takes only: {', '.join(sorted(_BUILD_KEYS))}")
    rows, columns = build.get("rows"), build.get("columns")
    if not _relative(rows) or not PLACEHOLDER.search(rows):
        raise bad(f"'{target}': 'rows' must be a relative pattern with a {{placeholder}}")
    if not _str_map(columns) or not columns:
        raise bad(f"'{target}': 'columns' must map column names to templates")
    if build.get("format", "csv") not in ("csv", "tsv"):
        raise bad(f"'{target}': 'format' must be csv or tsv")
    captured = set(PLACEHOLDER.findall(rows))
    for col, template in columns.items():
        for name in PLACEHOLDER.findall(template):
            if name not in captured:
                raise bad(f"'{target}': column '{col}' uses '{{{name}}}', which is not captured "
                          f"by rows {rows!r}")


def load_rule_file(path: Path, *, upstream: str, downstream: str,
                   origin: str | None = None) -> Rule:
    origin = origin or str(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise NfclawError(ErrorCode.PARAMS_INVALID, f"handoff rule {origin} cannot be read: {exc}",
                          fix="Pass a readable JSON rule file (see docs/chaining.md).") from exc
    return parse_rule(data, upstream=upstream, downstream=downstream, origin=origin)


def load_registry(repo_root: Path) -> dict[tuple[str, str], Rule]:
    """Every rule in `handoffs/<upstream>/<downstream>.json`, keyed (upstream, downstream)."""
    root = registry_dir(repo_root)
    if not root.is_dir():
        return {}
    return {(p.parent.name, p.stem): load_rule_file(
                p, upstream=p.parent.name, downstream=p.stem,
                origin=p.relative_to(repo_root).as_posix())
            for p in sorted(root.glob("*/*.json"))}


def provided_columns(source: Source) -> list[str]:
    """The header a samplesheet source will have, known before any row of it exists."""
    if source.kind == "build":
        return list(source.spec["build"]["columns"])
    rename = source.spec.get("rename", {})
    cols = [rename.get(c, c) for c in source.spec["provides"]]
    return list(dict.fromkeys([*cols, *source.spec.get("set", {}),
                               *source.spec.get("add_empty", [])]))


def check_rule(rule: Rule, upstream_tree: Path, downstream_tree: Path) -> list[str]:
    """Whether `rule` fits these two pipeline trees — everything that can be judged before either has
    run: the upstream parameters it sets, the downstream parameters it fills, and whether the header
    of a sheet it hands over can satisfy the downstream samplesheet schema. Runtime facts (files
    exist, rows are valid) are `materialize`'s. Each issue is prefixed with the rule's origin."""
    up = schema_mod.load_param_schema(upstream_tree)
    down = schema_mod.load_param_schema(downstream_tree)
    issues = [f"upstream {rule.upstream}: {e}"
              for e in parameters.validate_params(dict(rule.upstream_params), up)]
    for target, src in rule.params.items():
        if target not in down.params:
            issues.append(f"{rule.downstream} has no parameter '{_flag(target)}'")
            continue
        if src.kind == "upstream_param" and src.spec["upstream_param"] not in up.params:
            issues.append(f"{rule.upstream} has no parameter "
                          f"'{_flag(src.spec['upstream_param'])}'")
        if src.kind in ("samplesheet", "build"):
            ref = inputs.samplesheet_schema(downstream_tree, param=target)
            if ref is None:
                issues.append(f"'{_flag(target)}' of {rule.downstream} is not a samplesheet "
                              "(use a 'file' source)")
                continue
            sheet = schema_mod.load_input_schema(downstream_tree, ref)
            if sheet is not None:
                issues += [f"{rule.downstream} samplesheet: {i}"
                           for i in samplesheet.header_issues(provided_columns(src), sheet)]
                columns = {c.name: c for c in sheet.columns}
                for col in src.spec.get("allowed_values", {}):
                    if col not in provided_columns(src):
                        issues.append(f"'{col}' is not among the columns the handoff provides "
                                      "(allowed_values)")
                for col in src.spec.get("drop_rows_not_allowed", []):
                    if col not in columns:
                        issues.append(f"'{col}' is not a column of the {rule.downstream} "
                                      "samplesheet (drop_rows_not_allowed)")
                    elif not columns[col].enum:
                        issues.append(f"'{col}' has no allowed values to drop rows by "
                                      f"(the {rule.downstream} samplesheet does not restrict it)")
    return [f"{rule.origin}: {i}" for i in issues]


# --- producing a handoff from a finished upstream run ---------------------------------------

@dataclass(frozen=True)
class Handoff:
    params: dict[str, Any]            # downstream parameter -> value
    record: dict[str, Any]            # what handoff.json records: rule, sources, lineage


class _Unresolved(Exception):
    """A source that cannot be produced from this upstream run (the message says why)."""


class _NoMatch(_Unresolved):
    """Nothing in the upstream outdir matches a pattern (as opposed to several files matching)."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _bundle_text(outdir: Path, name: str) -> str:
    try:
        return (outdir / "provenance" / name).read_text(encoding="utf-8")
    except OSError:
        return ""


def recorded_outputs(outdir: Path) -> dict[str, str]:
    """A run's results as {path relative to its outdir: sha256}, as its bundle recorded them."""
    return provenance.read_checksums(outdir / "provenance" / "outputs.sha256")


def normalize_reference_inventory(inventory: dict[str, dict[str, str]], root: Path,
                                  *, destination: Path | None = None
                                  ) -> dict[str, dict[str, str]]:
    """Match the absolute root supplied by schema-declared downstream path parameters.

    Parent directory canonicalization retains the staged root alias. Nested aliases and their
    literal targets remain namespace entries; multiple logical paths must never be collapsed.
    """
    normalized = destination if destination is not None else inputs.absolute_local_path(root)
    resolved_root = root.resolve()
    result = {}
    for name, entry in inventory.items():
        relative = Path(name).relative_to(root)
        key = str(normalized / relative)
        node = dict(entry)
        if relative == Path(".") and normalized == resolved_root:
            node.pop("link_target", None)
        if node.get("resolved_path") == key:
            node.pop("resolved_path")
        result[key] = node
    return result


def recorded_input_inventory(outdir: Path, *, allow_legacy: bool = False) -> dict | None:
    bundle = outdir / "provenance"
    manifest = json.loads((bundle / "run_manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("invalid input manifest")
    path = bundle / "inputs.inventory.json"
    if allow_legacy and "dependency_inventory_version" not in manifest:
        return provenance.read_input_inventory(path) if path.exists() else None
    version = manifest.get("dependency_inventory_version")
    flags = manifest.get("unverified_dependency_inventories", [])
    if (type(version) is not int or version != 1 or not isinstance(flags, list)
            or any(not isinstance(kind, str) for kind in flags) or "inputs" in flags):
        raise ValueError("reference has no verified supported prelaunch input namespace")
    return provenance.read_input_inventory(path)


def directory_reference_evidence(path: Path, upstream: Path, boundary: dict | None = None) -> dict:
    """Require historical namespace and byte agreement before handing over a directory."""
    internal = _under(path, upstream)
    if internal == ".":
        historical = recorded_outputs(upstream)
        recorded_nodes = output_mod.read_inventory(upstream / "provenance/outputs.inventory.json", historical)
        current, raw_nodes = provenance.snapshot_inputs([path])
        _, nodes, raw_published = output_mod.snapshot(upstream)
        actual = {name: current.get(str(upstream / name)) for name, entry in nodes.items()
                  if entry["type"] == "file"}
        published = {name: entry for name, entry in raw_nodes.items()
                     if Path(name) != path and output_mod.is_result(Path(name).relative_to(path))}
        if (historical != actual or recorded_nodes != nodes or raw_published != published
                or any(current.get(str(upstream / name)) != digest for name, digest in historical.items())):
            raise ValueError("published results changed while recording the complete run directory")
        evidence = {"directory_reference": str(path), "directory_inventory": raw_nodes,
                    "directory_source": "bundle", "bundle_dependencies": current,
                    "output_dependencies": historical, "directory_output_inventory": recorded_nodes}
        if boundary is not None and any(boundary.get(key) != value for key, value in evidence.items()):
            raise ValueError("complete run directory changed since its recorded handoff boundary")
        return evidence
    if internal is None:
        historical = provenance.read_checksums(upstream / "provenance/inputs.sha256", relative=False)
        expected = {name: digest for name, digest in historical.items() if Path(name).is_relative_to(path)}
        nodes = recorded_input_inventory(upstream)
        expected_nodes = {name: entry for name, entry in nodes.items() if Path(name).is_relative_to(path)}
        current, current_nodes = provenance.snapshot_inputs([path])
        raw_nodes = current_nodes
        root_key = str(path)
        expected_file_nodes = expected.keys()
    else:
        historical = recorded_outputs(upstream)
        expected = {str(upstream / name): digest for name, digest in historical.items()
                    if Path(name).is_relative_to(internal)}
        nodes = output_mod.read_inventory(upstream / "provenance/outputs.inventory.json", historical)
        expected_nodes = {name: entry for name, entry in nodes.items() if Path(name).is_relative_to(internal)}
        hashes, current_nodes, raw_nodes = output_mod.snapshot(upstream, sha256_file, only=path)
        current = {str(upstream / name): digest for name, digest in hashes.items()}
        root_key = internal
        expected_file_nodes = {Path(name).relative_to(upstream).as_posix() for name in expected}
    if (expected_nodes.get(root_key, {}).get("type") != "directory"
            or current_nodes != expected_nodes or current != expected
            or {name for name, entry in expected_nodes.items() if entry["type"] == "file"}
               != expected_file_nodes):
        raise ValueError(f"reference directory {path} has no complete historical inventory or "
                         "changed since the upstream launch")
    evidence = {"directory_reference": str(path), "directory_inventory": raw_nodes,
                "directory_source": "inputs" if internal is None else "outputs"}
    if internal is None:
        evidence["input_dependencies"] = expected
    else:
        evidence["output_dependencies"] = {
            Path(name).relative_to(upstream).as_posix(): digest for name, digest in expected.items()}
        evidence["directory_output_inventory"] = expected_nodes
    return evidence


def _recorded_params(outdir: Path) -> tuple[dict[str, Any], str | None]:
    """The parameters a run used, and the result file that recorded them (None for the bundle's).

    The nf-core template dumps every *resolved* parameter — including those a profile set, such as
    a `--demo` run's references — to `pipeline_info/params_<timestamp>.json`, one per launch; the
    latest is what the finished run used. Without one (a release on an older template), nfclaw's
    own `provenance/params.json`: what the run was given, before any profile."""
    dumps = sorted((outdir / "pipeline_info").glob("params_*.json"))
    for path in reversed(dumps):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            return data, path.relative_to(outdir).as_posix()
    try:
        data = json.loads(_bundle_text(outdir, "params.json") or "{}")
    except ValueError:
        return {}, None
    return (data, None) if isinstance(data, dict) else ({}, None)


def _under(path: Path, root: Path) -> str | None:
    try:
        return Path(os.path.normpath(path)).relative_to(root).as_posix()
    except ValueError:
        return None


def _one_match(root: Path, pattern: str) -> Path:
    found = sorted(p for p in root.glob(pattern)
                   if p.is_file() and is_result(p.relative_to(root)))
    if not found:
        raise _NoMatch(f"nothing in {root} matches {pattern!r}")
    if len(found) > 1:
        shown = ", ".join(p.relative_to(root).as_posix() for p in found[:5])
        raise _Unresolved(f"{len(found)} files match {pattern!r} ({shown}); a handoff needs exactly "
                          "one — give the stage an inline handoff with a narrower pattern")
    return found[0]


def _first_match(root: Path, patterns: str | list[str]) -> tuple[Path, int]:
    """The file the first pattern that matches anything names (it must name exactly one), and that
    pattern's position. An ordered list says which output to prefer when a pipeline can write it in
    several places — rnaseq's merged counts sit under whichever quantifier ran, and its test
    profile runs two."""
    if isinstance(patterns, str):
        return _one_match(root, patterns), 0
    for index, pattern in enumerate(patterns):
        try:
            return _one_match(root, pattern), index
        except _NoMatch:
            continue                                      # several files matching is not skipped
    raise _NoMatch(f"nothing in {root} matches any of " + ", ".join(repr(p) for p in patterns))


def _fill(template: str, values: Mapping[str, str]) -> str:
    def sub(m: re.Match) -> str:
        if m.group(1) not in values:
            raise _Unresolved(f"template {template!r} needs column '{m.group(1)}', which the "
                              "upstream samplesheet does not have")
        return values[m.group(1)] or ""
    return PLACEHOLDER.sub(sub, template)


def _pattern(rows: str) -> tuple[str, re.Pattern]:
    """A `{placeholder}` row pattern as a glob (to find files) and a regex (to capture values)."""
    parts, pos, captured = [], 0, set()
    for m in PLACEHOLDER.finditer(rows):
        name = m.group(1)
        capture = f"(?P={name})" if name in captured else f"(?P<{name}>[^/]+?)"
        parts += [re.escape(rows[pos:m.start()]), capture]
        captured.add(name)
        pos = m.end()
    parts.append(re.escape(rows[pos:]))
    return PLACEHOLDER.sub("*", rows), re.compile("^" + "".join(parts) + "$")


def _schema_order(header: list[str], sheet_schema) -> list[str]:
    """`header` with the columns the downstream schema declares first, in its order, then the rest
    as they were. nf-schema reads columns by name; some releases also check the header literally
    (atacseq 2.1.2 wants `sample,fastq_1,fastq_2,replicate` first)."""
    declared = [c.name for c in sheet_schema.columns if c.name in header]
    return declared + [h for h in header if h not in declared]


def _write_sheet(dest: Path, header: list[str], rows: list[dict[str, str]]) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, delimiter=samplesheet.delimiter_for(dest),
                                extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return dest


def _absolute(value: str, root: Path) -> str:
    """A samplesheet path made absolute against the upstream outdir: Nextflow would otherwise resolve
    a relative one against the downstream's launch directory (its own --outdir)."""
    if inputs.is_remote_url(value) or Path(value).is_absolute():
        return value
    return os.path.normpath(root / value)


def consumption_evidence(paths: list[Path], upstream: Path) -> dict[str, Any]:
    """Bind local data sources to historical producer bytes and their complete namespace.

    The producer sheet is derivation evidence, but its path fields are the data the
    successor consumes. Keep the two identities separate, including directory/glob
    members and empty directories. Remote data cannot be certified by local records.
    """
    if not paths:
        return {}
    hashes, nodes = provenance.snapshot_inputs(paths)
    roots = [Path(name) for name in nodes
             if not any(str(parent) in nodes for parent in Path(name).parents)]
    published = recorded_outputs(upstream)
    for path in roots:
        if nodes[str(path)]["type"] == "directory":
            evidence = directory_reference_evidence(path, upstream)
            expected = (evidence.get("bundle_dependencies") or evidence.get("input_dependencies")
                        or {str(upstream / name): digest for name, digest in
                            evidence.get("output_dependencies", {}).items()})
            current = {name: digest for name, digest in hashes.items()
                       if Path(name).is_relative_to(path)}
            namespace = {name: entry for name, entry in nodes.items()
                         if Path(name).is_relative_to(path)}
            if current != expected or namespace != evidence["directory_inventory"]:
                raise ValueError(f"reference directory {path} changed while recording its handoff")
        elif (relative := _under(path, upstream)) is not None:
            if published.get(relative) != hashes[str(path)]:
                raise ValueError(f"upstream result {relative} changed or has no historical checksum")
        else:
            historical = provenance.read_checksums(upstream / "provenance/inputs.sha256", relative=False)
            historical_nodes = recorded_input_inventory(upstream)
            if (historical.get(str(path)) != hashes[str(path)]
                    or historical_nodes.get(str(path)) != nodes[str(path)]):
                raise ValueError(f"local upstream reference {path} changed or has no historical input record")
    return {"consumed_sources": [str(path) for path in sorted(set(paths))],
            "consumed_dependencies": hashes, "consumed_inventory": nodes}


def legacy_consumption_paths(item: dict, upstream: Path) -> list[Path]:
    """Local data named by a checksum-era handoff that predates consumed records.

    File sources explicitly name their input. For sheets, only absolute values
    naming recorded producer data are recognized; remote identities remain unverified.
    """
    value = item.get("value")
    if not isinstance(value, str) or inputs.is_remote_url(value):
        return []
    if item.get("kind") in ("file", "upstream_param"):
        if (Path(value).is_absolute() and not item.get("input_dependencies")
                and "directory_reference" not in item):
            return [Path(value)]
        return []
    if item.get("kind") not in ("samplesheet", "build"):
        return []
    published = recorded_outputs(upstream)
    paths = set()
    with Path(value).open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream, delimiter=samplesheet.delimiter_for(Path(value)), strict=True):
            for cell in row.values():
                if not isinstance(cell, str) or inputs.is_remote_url(cell):
                    continue
                path = Path(cell.strip())
                relative = _under(path, upstream)
                if path.is_absolute() and relative is not None and (
                        relative in published or path.is_dir()
                        or any(char in str(path) for char in "*?[{")):
                    paths.add(path)
    return sorted(paths)


def _direct(src: Source, root: Path, sheet_schema, dest: Path, downstream: str
            ) -> tuple[Path, list[str], dict[str, Any]]:
    sheet = _one_match(root, src.spec["samplesheet"])
    try:
        with sheet.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh, delimiter=samplesheet.delimiter_for(sheet), strict=True)
            header, rows = list(reader.fieldnames or []), list(reader)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise _Unresolved(f"cannot read {sheet}: {exc}") from exc
    duplicates = [name for name, count in Counter(header).items() if count > 1]
    if duplicates:
        raise _Unresolved(f"{sheet.name} has duplicate columns: {', '.join(duplicates)}")
    if extra := [str(i) for i, row in enumerate(rows, start=2) if None in row]:
        raise _Unresolved(f"{sheet.name} has values beyond its header on row(s) {', '.join(extra[:5])}")
    rename = src.spec.get("rename", {})
    if missing := [old for old in rename if old not in header]:
        raise _Unresolved(f"{sheet.name} has no column {', '.join(missing)} to rename")
    if clash := [new for old, new in rename.items() if new in header and new != old]:
        raise _Unresolved(f"{sheet.name} already has column {', '.join(clash)}; renaming onto it "
                          "would lose data")
    header = [rename.get(h, h) for h in header]
    if len(header) != len(set(header)):
        raise _Unresolved(f"{sheet.name}: rename maps several columns onto one column and would "
                          "lose data")
    rows = [{rename.get(k, k): v for k, v in r.items() if k is not None} for r in rows]
    for col, template in src.spec.get("set", {}).items():
        if col not in header:
            header.append(col)
        for r in rows:
            r[col] = _fill(template, r)
    for col in src.spec.get("add_empty", []):           # a column the downstream wants present
        if col not in header:
            header.append(col)
            for r in rows:
                r[col] = ""
    # Rows the downstream would reject for a value its schema does not allow (createtaxdb builds a
    # sourmash database the pinned taxprofiler cannot use) — dropped only where the rule says so.
    allowed = {c.name: set(c.enum) for c in sheet_schema.columns
               if c.enum and c.name in src.spec.get("drop_rows_not_allowed", [])}

    def rejected(row: dict) -> bool:
        return any((value := (row.get(col) or "").strip()) and value not in values
                   for col, values in allowed.items())

    kept = [r for r in rows if not rejected(r)]
    dropped = [r for r in rows if rejected(r)]
    if dropped and not kept:
        raise _Unresolved(f"no row of {sheet.name} is left once rows with values the downstream "
                          f"does not allow ({', '.join(sorted(allowed))}) are dropped")
    rows = kept
    # Rows whose data the downstream must not analyse although its schema cannot tell (a long-read
    # or colour-space run handed to a short-read aligner): refused, never dropped, naming them.
    for col, values in src.spec.get("allowed_values", {}).items():
        if col not in header:
            raise _Unresolved(f"{sheet.name} has no column '{col}' to check against the values "
                              f"{downstream} can analyse")
        if outside := [f"row {i} ({r.get('sample') or '?'}: {(r.get(col) or '').strip() or 'empty'})"
                       for i, r in enumerate(rows, start=2)
                       if (r.get(col) or "").strip() not in values]:
            raise _Unresolved(f"{downstream} takes only {col} {', '.join(values)}; "
                              f"{', '.join(outside[:5])}" + (" and more" if len(outside) > 5 else "")
                              + " — leave those runs out, or analyse them with a pipeline for "
                                "their data")
    # Rows a downstream cannot take although its schema allows them (sarek reads paired-end FastQ
    # only; its schema leaves fastq_2 optional): named here, before it launches.
    for col in src.spec.get("require_values", []):
        if missing := [f"row {i} ({r.get('sample') or '?'})" for i, r in enumerate(rows, start=2)
                       if not (r.get(col) or "").strip()]:
            raise _Unresolved(f"{downstream} needs a value in '{col}' on every row, and "
                              f"{', '.join(missing[:5])} "
                              + ("have none" if len(missing) > 1 else "has none"))
    derived = [sheet.relative_to(root).as_posix()]
    excluded = {*sheet_schema.metadata_columns, *sheet_schema.destination_columns}
    path_cols = {c.name: c for c in sheet_schema.columns if c.path_format() and c.name not in excluded}
    pattern_cols = samplesheet.pattern_file_columns(sheet_schema)
    for r in rows:
        for col in header:
            if col in excluded:
                continue
            if not (value := (r.get(col) or "").strip()):
                continue
            values = (value,)
            if col in path_cols and path_cols[col].path_format(value):
                values = tuple(_absolute(part, root) for part in path_cols[col].path_values(value, r))
                r[col] = path_cols[col].join_paths(values)
            elif col in pattern_cols and samplesheet.names_relative_file(pattern_cols[col], value):
                values = (_absolute(value, root),)
                r[col] = values[0]
            # Trace every upstream result the sheet points at — also in a column the downstream
            # schema declares no path format for (atacseq's fastq_1), so lineage misses none.
            for part in values:
                rel = _under(Path(part), root) if Path(part).is_absolute() else None
                if rel is not None and (root / rel).is_file():
                    derived.append(rel)
    suffix = sheet.suffix.lower() if sheet.suffix.lower() in (".csv", ".tsv") else ".csv"
    extra = {"dropped_rows": dropped} if dropped else {}
    return (_write_sheet(dest.with_suffix(suffix), _schema_order(header, sheet_schema), rows),
            derived, extra)


def _build(src: Source, root: Path, sheet_schema, dest: Path, downstream: str
           ) -> tuple[Path, list[str], dict[str, Any]]:
    spec = src.spec["build"]
    glob, rx = _pattern(spec["rows"])
    excluded = {*sheet_schema.metadata_columns, *sheet_schema.destination_columns}
    path_cols = {c.name: c for c in sheet_schema.columns if c.path_format() and c.name not in excluded}
    pattern_cols = samplesheet.pattern_file_columns(sheet_schema)
    rows: list[dict[str, str]] = []
    derived: list[str] = []
    for match in sorted(p for p in root.glob(glob) if p.is_file()):
        m = rx.match(match.relative_to(root).as_posix())
        if m is None:
            continue
        derived.append(match.relative_to(root).as_posix())
        row = {col: _fill(template[:-1] if template.endswith("?") else template, m.groupdict())
               for col, template in spec["columns"].items()}
        for col, template in spec["columns"].items():
            optional = template.endswith("?")
            text = row[col]
            column = path_cols.get(col)
            if text and (column and column.path_format(text) or col in pattern_cols
                         and samplesheet.names_relative_file(pattern_cols[col], text)):
                resolved = []
                values = column.path_values(text, row) if column else (text,)
                for part in values:
                    path = root / part
                    if path.is_file() or path.is_dir():
                        if path.is_file():
                            rel = _under(path, root)
                            if rel is not None:
                                derived.append(rel)
                        resolved.append(os.path.normpath(path))
                    elif optional:
                        resolved = []
                        break
                    else:
                        raise _Unresolved(f"{part} not found in {root} (column '{col}')")
                text = column.join_paths(tuple(resolved)) if column else "".join(resolved)
            row[col] = text
        rows.append(row)
    if not rows:
        raise _Unresolved(f"no file in {root} matches {spec['rows']!r}")
    return _write_sheet(dest.with_suffix("." + spec.get("format", "csv")),
                        _schema_order(list(spec["columns"]), sheet_schema), rows), derived, {}


def _resolve(rule: Rule, target: str, src: Source, *, upstream_outdir: Path,
             downstream_tree: Path, dest: Path,
             used: tuple[Mapping[str, Any], str | None],
             chosen: dict[str, int] | None = None) -> tuple[Any, list[str], dict[str, Any]]:
    """One source's value, the upstream files it was derived from, and extra record fields."""
    if src.kind in ("samplesheet", "build"):
        ref = inputs.samplesheet_schema(downstream_tree, param=target)
        sheet_schema = (schema_mod.load_input_schema(downstream_tree, ref) if ref else None)
        if sheet_schema is None:
            raise _Unresolved(f"'{_flag(target)}' of {rule.downstream} is not a samplesheet")
        make = _direct if src.kind == "samplesheet" else _build
        path, derived, extra = make(src, upstream_outdir, sheet_schema, dest / target,
                                    rule.downstream)
        if issues := samplesheet.validate(path, sheet_schema):
            raise NfclawError(
                ErrorCode.HANDOFF_FAILED,
                f"{rule.origin}: the samplesheet prepared for {rule.downstream} "
                f"{_flag(target)} would be rejected.",
                fix=(f"Inspect {path}. Fix the rule, or the {rule.upstream} stage's options, then "
                     "resume the chain."),
                details={"issues": issues, "snapshot": str(path)})
        consumption = consumption_evidence(provenance.samplesheet_dependencies(path, sheet_schema),
                                           upstream_outdir)
        return str(path), derived, {"sha256": sha256_file(path), **extra, **consumption}
    if src.kind == "file":
        chosen = {} if chosen is None else chosen
        if (partner := src.spec.get("paired_with")) is not None:
            if partner not in chosen:
                raise _Unresolved(f"it belongs to {_flag(partner)}, which this handoff did not "
                                  f"choose; supply both {_flag(partner)} and {_flag(target)}")
            index = chosen[partner]
            found = _one_match(upstream_outdir, src.spec["file"][index])
        else:
            found, index = _first_match(upstream_outdir, src.spec["file"])
        chosen[target] = index
        return (str(found), [found.relative_to(upstream_outdir).as_posix()],
                {**consumption_evidence([found], upstream_outdir), "consumed_scalar": True})
    params, recorded_in = used
    value = params.get(src.spec["upstream_param"])
    if value is None or value == "" or value is False:
        raise _Unresolved(f"the {rule.upstream} run did not set "
                          f"{_flag(src.spec['upstream_param'])}")
    extra: dict[str, Any] = {}
    if isinstance(value, str) and not inputs.is_remote_url(value):
        target_param = schema_mod.load_param_schema(downstream_tree).params.get(target)
        if target_param is not None and target_param.fmt in ("file-path", "directory-path"):
            value = _absolute(value, upstream_outdir)
        path = Path(value)
        if path.is_absolute():
            remedy = (f"Supply {_flag(target)} directly in the downstream stage to choose this "
                      "reference explicitly, or rerun the upstream with current provenance.")
            if not path.exists():
                raise NfclawError(ErrorCode.HANDOFF_FAILED,
                                  f"{rule.origin}: local upstream reference {value} is missing.",
                                  fix=remedy)
            if path.is_dir():
                try:
                    extra = directory_reference_evidence(path, upstream_outdir)
                except (OSError, ValueError) as exc:
                    raise NfclawError(ErrorCode.HANDOFF_FAILED,
                        f"{rule.origin}: cannot verify local upstream reference {value}: {exc}",
                        fix=remedy) from exc
            elif _under(path, upstream_outdir) is not None:
                extra.update(consumption_evidence([path], upstream_outdir))
                extra["consumed_scalar"] = True
            elif _under(path, upstream_outdir) is None:
                try:
                    historical = provenance.read_checksums(
                        upstream_outdir / "provenance" / "inputs.sha256", relative=False)
                    digest = historical.get(str(path))
                    nodes = recorded_input_inventory(upstream_outdir, allow_legacy=True)
                    legacy = nodes is None
                    nodes = nodes or {}
                    expected_nodes = {str(path): nodes[str(path)]} if str(path) in nodes else {}
                    actual, current_nodes = provenance.snapshot_inputs([path])
                except (OSError, ValueError) as exc:
                    raise NfclawError(
                        ErrorCode.HANDOFF_FAILED,
                        f"{rule.origin}: cannot verify local upstream reference {value}: {exc}",
                        fix=remedy) from exc
                if (digest is None or actual != {str(path): digest} or (not legacy and (
                        current_nodes != expected_nodes or expected_nodes.get(str(path), {}).get("type") != "file"))):
                    raise NfclawError(
                        ErrorCode.HANDOFF_FAILED,
                        f"{rule.origin}: local upstream reference {value} has no historical input "
                        "hash or changed since the upstream launch.", fix=remedy)
                extra["input_dependencies"] = {str(path): digest}
                if not legacy:
                    extra["input_inventory"] = expected_nodes
    rel = _under(Path(value), upstream_outdir) if isinstance(value, str) else None
    derived = [r for r in (recorded_in, rel) if r and (upstream_outdir / r).is_file()]
    derived += list(extra.get("output_dependencies", {}))
    return value, derived, extra


def materialize(rule: Rule, *, upstream_outdir: Path, downstream_tree: Path,
                dest: Path, exclude_params: frozenset[str] = frozenset()) -> Handoff:
    """Produce the downstream parameters `rule` promises from a finished upstream run.

    Samplesheets are written into `dest` (a snapshot nfclaw keeps, never the downstream's outdir),
    with absolute paths, and validated against the downstream's samplesheet schema here — so a sheet
    the next pipeline would reject fails the handoff, naming the rule and the file, before the next
    launch. Every upstream file a value points into is recorded with the digest the upstream run's
    own `outputs.sha256` gives it: that is what links the two runs."""
    try:
        outputs = recorded_outputs(upstream_outdir)
        historical_nodes = output_mod.recorded_inventory(upstream_outdir, outputs)
        current_nodes = output_mod.snapshot(upstream_outdir)[1]
        if historical_nodes is not None and historical_nodes != current_nodes:
            raise ValueError("published output namespace changed since the upstream run; "
                             + output_mod.namespace_difference(historical_nodes, current_nodes))
    except (OSError, ValueError) as exc:
        raise NfclawError(
            ErrorCode.HANDOFF_FAILED,
            f"{rule.origin}: cannot verify the {rule.upstream} output records: {exc}",
            fix="Restore the upstream provenance bundle, or run the chain in a fresh --outdir.") \
            from exc
    used = _recorded_params(upstream_outdir)
    values: dict[str, Any] = {}
    traced: dict[str, dict] = {}
    chosen: dict[str, int] = {}                 # which candidate each file list chose
    # A paired file list follows its partner's choice, so the partner is resolved first.
    order = sorted(rule.params.items(), key=lambda item: "paired_with" in item[1].spec)
    for target, src in order:
        if target in exclude_params:
            continue
        try:
            value, derived, extra = _resolve(rule, target, src, upstream_outdir=upstream_outdir,
                                             downstream_tree=downstream_tree, dest=dest, used=used,
                                             chosen=chosen)
        except (OSError, ValueError) as exc:
            raise NfclawError(
                ErrorCode.HANDOFF_FAILED,
                f"{rule.origin}: cannot verify local data consumed by {rule.downstream} "
                f"{_flag(target)}: {exc}",
                fix="Restore the producer's recorded data and provenance before resuming.") from exc
        except _Unresolved as why:
            if src.optional:
                continue
            raise NfclawError(
                ErrorCode.HANDOFF_FAILED,
                f"{rule.origin}: cannot prepare {rule.downstream} {_flag(target)}: {why}",
                fix=(f"Check the {rule.upstream} results in {upstream_outdir}; set "
                     f"{_flag(target)} in the stage's params, or give the stage an inline handoff."),
                details={"upstream_outdir": str(upstream_outdir)}) from None
        for rel in dict.fromkeys(derived):
            digest = outputs.get(rel)
            if digest is not None and extra.get("output_dependencies", {}).get(rel) == digest:
                continue  # The directory evidence already verified these bytes and namespace.
            try:
                actual = sha256_file(upstream_outdir / rel)
            except OSError as exc:
                raise NfclawError(
                    ErrorCode.HANDOFF_FAILED,
                    f"{rule.origin}: cannot verify upstream result {rel}: {exc}",
                    fix="Restore the upstream result before resuming the chain.") from exc
            if digest is None or actual != digest:
                reason = ("was not recorded as an output" if digest is None
                          else "changed since the upstream run")
                raise NfclawError(
                    ErrorCode.HANDOFF_FAILED,
                    f"{rule.origin}: upstream result {rel} {reason}.",
                    fix="Restore the recorded upstream result, or use a fresh --outdir.")
        values[target] = value
        traced[target] = {"kind": src.kind, "value": value, **extra,
                          "derived_from": {rel: outputs.get(rel)
                                           for rel in dict.fromkeys(derived)}}
    record = {"rule": {"origin": rule.origin, "sha256": rule.sha256(), "body": rule.raw},
              "upstream": {"pipeline": rule.upstream, "outdir": str(upstream_outdir)},
              "downstream": {"pipeline": rule.downstream},
              "upstream_params": dict(rule.upstream_params), "params": traced,
              "overridden_params": sorted(exclude_params & rule.params.keys())}
    return Handoff(values, record)
