from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter
from collections.abc import Hashable, Iterable
from decimal import Decimal
from pathlib import Path

from runner import exact_json as json
from runner.inputs import is_remote_url, local_name_issues
from runner.schema import InputSchema, json_scalar


def _unique_json_keys(pairs):
    row = {}
    for key, value in pairs:
        if key in row:
            raise ValueError(f"duplicate key {key!r}")
        row[key] = value
    return row


def serialized_rows(path: Path) -> list[dict] | None:
    """Flat JSON/YAML sample records; other structures remain nf-schema's responsibility."""
    suffix = path.suffix.lower()
    if suffix not in (".json", ".yaml", ".yml"):
        return None
    text = path.read_text(encoding="utf-8-sig")
    if suffix == ".json":
        try:
            data = json.loads(text, object_pairs_hook=_unique_json_keys)
        except (ValueError, RecursionError) as exc:
            raise csv.Error(f"invalid JSON: {exc}") from exc
    else:
        try:
            import yaml
        except ImportError as exc:
            raise csv.Error("YAML preflight requires PyYAML; install nfclaw[yaml]") from exc
        try:
            class UniqueKeySafeLoader(yaml.SafeLoader):
                def construct_mapping(self, node, deep=False):
                    seen = set()
                    for key_node, _ in node.value:
                        # Explicit merge overrides are deliberate YAML semantics, not duplicate
                        # source fields. Check explicit fields before SafeLoader flattens merges.
                        if key_node.tag == "tag:yaml.org,2002:merge":
                            continue
                        key = self.construct_object(key_node, deep=deep)
                        if not isinstance(key, Hashable):
                            raise yaml.constructor.ConstructorError(
                                None, None, "unhashable mapping key", key_node.start_mark)
                        if key in seen:
                            raise yaml.constructor.ConstructorError(
                                None, None, f"duplicate key {key!r}", key_node.start_mark)
                        seen.add(key)
                    return super().construct_mapping(node, deep=deep)

            UniqueKeySafeLoader.add_constructor("tag:yaml.org,2002:float", json.yaml_float)
            loader = UniqueKeySafeLoader(text)
            try:
                data = loader.get_single_data()
            finally:
                loader.dispose()
        except (yaml.YAMLError, RecursionError, ValueError, ArithmeticError) as exc:
            raise csv.Error(f"invalid YAML: {exc}") from exc
    return data if isinstance(data, list) and all(isinstance(row, dict) for row in data) else None


def _identity_issues(row_num: int, col, raw: str) -> list[str]:
    if col.is_identifier and raw and not _safe_identifier(raw):
        return [f"row {row_num}: '{col.name}' identifier {raw!r} must start with a "
                "letter, digit or underscore and contain only letters, digits, "
                "combining marks, dots, underscores or hyphens; use an explicit "
                "safe alias (identifiers become shell arguments and filenames)"]
    return []


def pattern_file_columns(input_schema: InputSchema) -> dict:
    """File columns typed by their pattern alone, without an nf-schema path format (atacseq's and
    hic's `fastq_1`). Their values are paths all the same: the pipelines open them with `file()`,
    which resolves a relative one against Nextflow's launch directory. A column that only *names*
    a file another column stages (nanostring's `RCC_FILE_NAME` beside `RCC_FILE`) is not one."""
    from runner import sheetgen

    columns = {c.name: c for c in input_schema.columns if c.name}
    staged = {frozenset(sheetgen._patterns(c)) for c in columns.values() if c.path_format()}
    return {name: columns[name] for name in sheetgen.file_columns(input_schema)
            if not columns[name].path_format()
            and frozenset(sheetgen._patterns(columns[name])) not in staged}


def names_relative_file(col, value: str) -> bool:
    """Whether `value`, in a pattern-typed file column, is a relative path to a file the column
    takes (a plain marker such as bacass's `NA` names none)."""
    from runner import sheetgen

    return (not is_remote_url(value) and not Path(value).is_absolute()
            and sheetgen._matches(col, Path("/") / value))


def _relative_file_issues(row_num: int, col, value: str) -> list[str]:
    if not names_relative_file(col, value):
        return []
    return [f"row {row_num}: '{col.name}' is a relative path: {value} — use an absolute path "
            "(Nextflow resolves samplesheet paths against its launch directory, which nfclaw sets "
            "to --outdir)"]


def validate(path: Path, input_schema: InputSchema) -> list[str]:
    issues: list[str] = []
    if not path.is_file():
        # Covers both a missing path and one that exists but is a directory — reading either as a
        # samplesheet would otherwise raise FileNotFoundError/IsADirectoryError as a raw traceback.
        return [f"samplesheet not found or not a file: {path}"]
    named = [c for c in input_schema.columns if c.name]
    pattern_files = pattern_file_columns(input_schema)
    # nf-schema picks the parser from the file extension; mirror that exactly so a `.tsv`
    # (e.g. nf-core/airrflow, which mandates `.tsv`) is split on TAB, not read as one CSV column.
    delimiter = delimiter_for(path)
    kind = "TSV" if delimiter == "\t" else "CSV"
    # Read as utf-8-sig so a leading UTF-8 BOM (common in spreadsheet-exported CSVs) is stripped:
    # otherwise a leading BOM stays glued to the first header (it reads as `\ufeffsample`) and a
    # required column looks missing.
    # No-op when there is no BOM.
    # A non-text file (e.g. an .xlsx or other binary handed in by mistake) would raise
    # UnicodeDecodeError; report it as a clear samplesheet issue instead of a raw traceback.
    try:
        if not named:
            # Headerless, one value per line (e.g. nf-core/fetchngs accession list). csv.DictReader
            # would mistake the first value for a header; just require >=1 non-empty value. Per-value
            # pattern checks are delegated to nf-schema, exactly as for named-column samplesheets.
            values = [ln.strip() for ln in path.read_text(encoding="utf-8-sig").splitlines()
                      if ln.strip()]
            return [] if values else ["input file has no values"]
        if path.suffix.lower() not in (".csv", ".tsv"):
            # Some nf-core pipelines (notably Sarek) accept JSON/YAML inputs while also shipping a
            # tabular schema_input.json. Flat records get identity and local-path guards; full
            # format-specific and nested-structure validation stays with nf-schema.
            data = serialized_rows(path)
            if data is None:
                return []
            for i, row in enumerate(data, start=1):
                for col in named:
                    value = row.get(col.name)
                    if col.is_identifier and value is not None and not isinstance(value, (str, *json.NUMBER_TYPES, bool)):
                        issues.append(f"row {i}: '{col.name}' identifier must be a literal scalar; "
                                      "quote YAML identifiers to preserve their text")
                    else:
                        raw = "" if value is None else json_scalar(value)
                        issues.extend(_identity_issues(i, col, raw))
                    if isinstance(value, str) and value and col.path_format(value):
                        issues.extend(_path_cell_issues(i, col, value, row))
                    elif col.name in pattern_files and isinstance(value, str) and value.strip():
                        issues.extend(_relative_file_issues(i, col, value.strip()))
                    if isinstance(value, str):
                        issues.extend(_info_identifier_issues(i, col, value))
                        issues.extend(_quoted_value_issues(i, col, value))
            return issues
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh, delimiter=delimiter, strict=True)
            fields = reader.fieldnames or []
            if input_schema.header_prefix and tuple(fields[:len(input_schema.header_prefix)]) != input_schema.header_prefix:
                issues.append("samplesheet header must begin with " + ",".join(input_schema.header_prefix)
                              + " in this order, as required by the pinned consumer")
            duplicates = sorted(name for name, count in Counter(fields).items() if count > 1)
            if duplicates:
                return [f"duplicate samplesheet column '{name}'" for name in duplicates]
            header = set(fields)
            for col in named:
                if col.required and col.name not in header:
                    issues.append(f"missing required column '{col.name}'")
            rows = list(reader)
    except UnicodeDecodeError:
        return [f"samplesheet is not valid UTF-8 text: {path} "
                "(is it a text samplesheet, not a binary file such as .xlsx?)"]
    except OSError as exc:
        # It exists and is a file (checked above) but cannot be read — e.g. another user's sheet.
        return [f"samplesheet cannot be read: {exc.strerror or exc}: {path}"]
    except csv.Error as exc:
        # The parser gave up on the file's structure — in practice an unbalanced quote, which makes
        # the rest of the file one field until it exceeds the csv module's field size limit.
        kind = {".json": "JSON", ".yaml": "YAML", ".yml": "YAML"}.get(path.suffix.lower(), kind)
        hint = " (check for an unbalanced quote)" if kind in ("CSV", "TSV") else ""
        return [f"samplesheet is not parseable as {kind}: {exc}{hint}: {path}"]
    if not rows:
        issues.append("samplesheet has no data rows")
    for i, row in enumerate(rows, start=2):
        if None in row:
            issues.append(f"row {i}: extra values beyond the samplesheet header")
        for col in named:
            raw = row.get(col.name) or ""
            val = raw.strip()
            if col.required and not val:
                issues.append(f"row {i}: empty required '{col.name}'")
            issues.extend(_identity_issues(i, col, raw))
            issues.extend(_info_identifier_issues(i, col, val))
            issues.extend(_quoted_value_issues(i, col, raw))
            if val:
                issues.extend(_value_issues(i, col, val))
            if val and col.path_format(val):
                # nf-schema resolves a relative path against Nextflow's launch directory — which
                # nfclaw sets to --outdir — not against the samplesheet's folder, and it does not
                # expand `~`. A relative path cannot mean what it says, so require an absolute one.
                issues.extend(_path_cell_issues(i, col, val, row))
            elif col.name in pattern_files and val:
                issues.extend(_relative_file_issues(i, col, val))
        values = {col.name: (row.get(col.name) or "").strip() for col in named}
        for trigger, required in input_schema.dependent_required:
            if values.get(trigger):
                for req in required:
                    if not values.get(req):
                        issues.append(f"row {i}: '{trigger}' requires '{req}'")
        branches = input_schema.any_of_dependent_required
        if branches and not _any_branch_satisfied(values, branches):
            issues.append(f"row {i}: {_any_of_message(branches)}")
    return issues


def _safe_identifier(value: str) -> bool:
    # Do not normalize or rename: distinct scientific sample identities must remain distinct.
    # Unicode letters and their combining marks are literal shell-word characters, too.
    return (bool(value) and (value[0].isalnum() or value[0] == "_")
            and all(char.isalnum() or char in "._-" or unicodedata.category(char).startswith("M")
                    for char in value))


def _path_cell_issues(row_num: int, col, value: str, row: dict) -> list[str]:
    try:
        values = col.path_values(value, row)
    except ValueError as exc:
        return [f"row {row_num}: {exc}"]
    return [issue for part in values for issue in _path_issues(row_num, col, part)]


def _info_identifier_issues(row_num: int, col, value: str) -> list[str]:
    issues = []
    if col.info_identifier_keys or col.info_single_quoted_keys:
        identifiers = {key.upper() for key in col.info_identifier_keys}
        single_quoted = {key.upper() for key in col.info_single_quoted_keys}
        for entry in value.split(";"):
            key, separator, identity = entry.partition(":")
            # The pinned consumer maps keys to enum names with toUpperCase(),
            # which also recognizes dotless-i spellings; casefold() differs.
            if (separator and key.upper() in identifiers
                    and identity and not _safe_identifier(identity)):
                issues.append(f"row {row_num}: '{col.name}.{key}' identifier {identity!r} "
                              "is not a literal safe alias; use letters, digits, combining marks, "
                              "dots, underscores or hyphens")
            if separator and key.upper() in single_quoted and "'" in identity:
                issues.append(f"row {row_num}: '{col.name}.{key}' contains a single quote; "
                              "the pinned consumer cannot pass this value in its single-quoted argument")
    return issues


def _quoted_value_issues(row_num: int, col, value: str) -> list[str]:
    # Some consumers pass the complete scalar as a double-quoted shell argument
    # rather than staging its basename. Check every character in the actual value;
    # destinations need neither an existence check nor a directory inventory.
    if col.audited_double_quoted and any(char in {'"', '\\', '$', '`'}
                                         or ord(char) < 32 or ord(char) == 127 for char in value):
        return [f"row {row_num}: '{col.name}' cannot be passed literally in the pinned "
                "consumer's double-quoted argument; use a location without quotes, "
                "backslashes, dollar signs, backticks or control characters"]
    return []


def _path_issues(row_num: int, col, value: str) -> list[str]:
    fmt = col.path_format(value)
    if is_remote_url(value):
        return [f"row {row_num}: '{col.name}': {issue}"
                for issue in local_name_issues(value, fmt)]
    path = Path(value)
    if not path.is_absolute():
        return [f"row {row_num}: '{col.name}' is a relative path: {value} — use an "
                "absolute path (Nextflow resolves samplesheet paths against its "
                "launch directory, which nfclaw sets to --outdir)"]
    if issues := local_name_issues(value, fmt):
        return [f"row {row_num}: '{col.name}': {issue}" for issue in issues]
    if fmt != "file-path-pattern" and not path.exists():
        return [f"row {row_num}: file not found for '{col.name}': {value}"]
    return []


def delimiter_for(path: Path) -> str:
    """nf-schema picks the parser from the file extension: TAB for `.tsv`, comma for anything else."""
    return "\t" if path.suffix.lower() == ".tsv" else ","


def header_issues(columns: Iterable[str], input_schema: InputSchema) -> list[str]:
    """Why a samplesheet with exactly these `columns`, every one filled, could not satisfy the schema.

    The column-level half of `validate`, for judging a sheet before any row of it exists — a chain's
    handoff, checked before the pipeline that writes the sheet has run. Rows are assumed filled, so
    only what the header alone decides is reported: required columns, a `oneOf` column group,
    `dependentRequired` and its `anyOf` branches."""
    have = set(columns)
    issues = [f"missing required column '{c.name}'" for c in input_schema.columns
              if c.name and c.required and c.name not in have]
    issues += [f"missing positional header column '{name}'" for name in input_schema.header_prefix
               if name not in have and not any(f"'{name}'" in issue for issue in issues)]
    if input_schema.one_of and not any(set(group) <= have for group in input_schema.one_of):
        issues.append("needs one of these column sets: "
                      + "; ".join(", ".join(group) for group in input_schema.one_of))
    for trigger, required in input_schema.dependent_required:
        if trigger in have:
            issues += [f"'{trigger}' requires '{req}'" for req in required if req not in have]
    branches = input_schema.any_of_dependent_required
    if branches and not _any_branch_satisfied({c: "x" for c in have}, branches):
        issues.append(_any_of_message(branches))
    return issues


def _value_issues(row_num: int, col, value: str) -> list[str]:
    return [f"row {row_num}: '{col.name}' {problem}" for problem in value_problems(col, value)]


def value_problems(col, value: str) -> list[str]:
    """Why `value` cannot fill column `col` (enum, scalar type, pattern, length and bounds), each
    phrased to follow the column's name. Shared with samplesheet generation's --sheet-set check."""
    issues: list[str] = []
    if col.enum and value not in col.enum:
        issues.append(f"value {value!r} must be one of: {', '.join(col.enum)}")
    numeric: int | float | Decimal | None = None
    if col.type == "integer":
        try:
            numeric = int(value)
        except ValueError:
            issues.append(f"expects an integer, got {value!r}")
    elif col.type == "number":
        try:
            numeric = json.number(value)
        except ValueError as exc:
            kind = "a finite number" if "non-finite" in str(exc) else "a number"
            issues.append(f"expects {kind}, got {value!r}")
    if col.pattern:
        try:
            matches = re.search(col.pattern, value) is not None
        except re.error:
            matches = True
        if not matches:
            issues.append(f"value {value!r} must match {col.pattern}")
    if col.min_length is not None and len(value) < col.min_length:
        issues.append(f"length must be >= {col.min_length}")
    if col.max_length is not None and len(value) > col.max_length:
        issues.append(f"length must be <= {col.max_length}")
    if numeric is not None:
        if col.minimum is not None and json.decimal(numeric) < json.decimal(col.minimum):
            issues.append(f"must be >= {col.minimum}")
        if col.maximum is not None and json.decimal(numeric) > json.decimal(col.maximum):
            issues.append(f"must be <= {col.maximum}")
    return issues


def _branch_satisfied(values: dict[str, str], branch: tuple[str, tuple[str, ...]]) -> bool:
    trigger, required = branch
    return not values.get(trigger) or all(values.get(req) for req in required)


def _any_branch_satisfied(
    values: dict[str, str],
    branches: tuple[tuple[tuple[str, tuple[str, ...]], ...], ...],
) -> bool:
    return any(all(_branch_satisfied(values, requirement) for requirement in option)
               for option in branches)


def _any_of_message(branches: tuple[tuple[tuple[str, tuple[str, ...]], ...], ...]) -> str:
    options: list[str] = []
    triggers = sorted({trigger for option in branches for trigger, _ in option})
    if len(triggers) == 1 and all(len(option) == 1 and option[0][0] == triggers[0]
                                  for option in branches):
        reqs = [req for option in branches for req in option[0][1]]
        return (f"when '{triggers[0]}' is set, provide one of: "
                + ", ".join(f"'{req}'" for req in reqs))
    for option in branches:
        parts: list[str] = []
        for trigger, required in option:
            reqs = ", ".join(f"'{req}'" for req in required)
            parts.append(f"{reqs} when '{trigger}' is set")
        options.append(" and ".join(parts))
    if len(triggers) == 1:
        return f"when '{triggers[0]}' is set, provide one of: {', '.join(options)}"
    return f"provide one of these conditional column sets: {', '.join(options)}"
