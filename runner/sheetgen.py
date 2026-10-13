"""Samplesheets generated from data files: `nfclaw run <name> --input <directory | glob | files>`.

When a pipeline's `--input` is a samplesheet and the value names data files instead — a directory,
a glob, one data file or several — `nfclaw run` writes the samplesheet itself, as one stage of the
run: before the samplesheet check, the parameter checks and launch, which then treat it exactly
like a hand-written sheet.

The pinned release's own samplesheet schema decides everything; nothing here knows a pipeline:
- which columns take files: those whose declared pattern names a file type (`^\\S+\\.bam$`), FastQ
  read columns among them, paired by their names (`fastq_1`/`fastq_2`, `short_reads_1`/`_2`);
- which column names the sample (its identity metadata), and whether there is a `lane` column;
- which columns are required, what they may hold, and which rules tie them together.

Values come only from the files (sample names, read files, mates, lanes), from the schema's own
defaults, or from the caller: `--sheet-set COLUMN=VALUE`, a constant or a template using
`{sample}`/`{lane}`. Nothing scientific is inferred (strandedness, patient, condition, replicate):
a required value nothing supplies is refused, naming the column and its allowed values. Sample
names are taken from file names and never altered: a name the pipeline cannot take is refused,
naming the file. Mates are paired by name and confirmed by their first read names, so numbered
single-end replicates (`ctrl_1`, `ctrl_2`) are never taken for the two reads of one library.

The result is validated by the same samplesheet check a hand-written sheet gets, written beside
the run's params file and recorded in its provenance bundle, so the replay reuses the decision
instead of re-scanning a directory whose contents may have changed.
"""
from __future__ import annotations

import bz2
import csv
import glob
import gzip
import io
import lzma
import os
import re
import tempfile
import zlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runner import inputs, samplesheet
from runner import schema as schema_mod
from runner.errors import ErrorCode, NfclawError
from runner.replay_guard import _glob_patterns
from runner.schema import Column, InputSchema, Param, json_scalar

# Values that name a samplesheet (nf-schema reads CSV, TSV, JSON and YAML; fetchngs takes `.txt`).
SHEET_SUFFIXES = (".csv", ".tsv", ".txt", ".json", ".yaml", ".yml")
GENERATED_STEM = "samplesheet"
# A column "names a file type" when its pattern requires an extension that no plain name has.
_PROBE = "nfclaw_probe"
_FASTQ_PROBES = ("nfclaw_probe.fastq.gz", "nfclaw_probe.fq.gz", "nfclaw_probe.fastq", "nfclaw_probe.fq")
# A read column takes FastQ only: pairgenomealign's `fasta` takes FastQ or FASTA genomes, and
# longraredisease's `file_path` FastQ or BAM — one file per sample, not read pairs.
_NOT_READS_PROBES = ("nfclaw_probe.bam", "nfclaw_probe.fa", "nfclaw_probe.fasta")
_EXTENSION = re.compile(r"\.(?:[A-Za-z]|\()")
_IDENTITY_NAMES = ("id", "sampleid", "samplename")
_PLACEHOLDER = re.compile(r"\{([^{}]*)\}")
_TEMPLATE_KEYS = ("sample", "lane")

_FASTQ_SUFFIX = re.compile(r"\.f(?:ast)?q(?:\.(?:gz|bz2|xz|zst))?$", re.IGNORECASE)
# Read names that identify a molecule: Illumina's instrument:run:flowcell:lane:tile:x:y and the
# SRA/ENA spot names. Generic names (`read1`, written by simulators or renumbering) prove nothing.
_ACCESSION = re.compile(r"^[SED]RR\d+\.\d+")
# bcl2fastq / BCL Convert: <sample>_S<n>[_L<lane>]_<R|I><read>_<chunk>
_ILLUMINA = re.compile(r"^(?P<sample>.+)_S(?P<number>\d+)(?:_L(?P<lane>\d{3}))?_(?P<kind>[RI])"
                       r"(?P<read>\d)_(?P<chunk>\d{3})$")
# An explicit read token: <sample>[_L<lane>]{_|.|-}R<read>[_<chunk>]. Index reads are recognised
# only in the demultiplexer's full form above: `Patient_I1` may well be a sample.
_TOKEN = re.compile(r"^(?P<sample>.+?)(?:_L(?P<lane>\d{3}))?[._-](?P<kind>[Rr])(?P<read>\d)"
                    r"(?:_(?P<chunk>\d{3}))?$")
# A bare read number: <sample>{_|.|-}<1|2> — mates only when their reads say so.
_BARE = re.compile(r"^(?P<sample>.+)[._-](?P<read>[12])$")
# Characters that mark read 1/read 2 in naming conventions nfclaw does not parse (`_read1`, `_F`).
_READ_MARKS = {"1": "2", "F": "R", "f": "r"}
_COMPRESSION = (".gz", ".bz2", ".xz", ".zst", ".zip")
_INDEXES = (".bai", ".crai", ".csi", ".tbi", ".pbi", ".fai")
_SHOWN = 5                      # file names quoted in one message


def _bad(message: str, *, fix: str = "", issues: list[str] | None = None) -> NfclawError:
    return NfclawError(ErrorCode.SAMPLESHEET_INVALID, message, fix=fix,
                       details={"issues": issues} if issues else {})


def _shown(names: list[str]) -> str:
    more = len(names) - _SHOWN
    return ", ".join(names[:_SHOWN]) + (f" and {more} more" if more > 0 else "")


# --- the schema: which column takes what ------------------------------------------------------

def _patterns(col: Column) -> tuple[str, ...]:
    return ((col.pattern,) if col.pattern else ()) + tuple(col.alternatives)


def _search(pattern: str, text: str) -> bool:
    try:
        return re.search(pattern, text) is not None
    except re.error:
        return False


def _typed(col: Column) -> bool:
    """Whether the column declares a file type: a string column whose patterns all compile, none of
    which a plain name satisfies, and at least one of which requires an extension."""
    pats = _patterns(col)
    if not pats or col.is_identifier or not ("string" in col.type or not col.type):
        return False
    for p in pats:
        try:
            re.compile(p)
        except re.error:
            return False
    return (not any(_search(p, _PROBE) or _search(p, f"/{_PROBE}/{_PROBE}") for p in pats)
            and any(_EXTENSION.search(p) for p in pats))


def file_columns(sheet: InputSchema) -> tuple[str, ...]:
    """The columns whose patterns name a file type: data files, whatever format the schema declares."""
    return tuple(c.name for c in sheet.columns if c.name and _typed(c))


def _matches(col: Column, path: Path) -> bool:
    """A file fits a column when one of its patterns accepts both the absolute path (the value
    nf-schema checks) and the bare file name — so a pattern matching a directory name is no match."""
    return any(_search(p, str(path)) and _search(p, path.name) for p in _patterns(col))


def _is_reads(col: Column) -> bool:
    return (any(_matches(col, Path("/nfclaw") / probe) for probe in _FASTQ_PROBES)
            and not any(_matches(col, Path("/nfclaw") / probe) for probe in _NOT_READS_PROBES))


def _read_groups(names: list[str]) -> list[tuple[str, ...]]:
    """Read columns as groups: `<base>1`+`<base>2` or `<base>`+`<base>_2` are one pair."""
    pairs: dict[str, str] = {}
    for name in names:
        partner = (name[:-1] + "2") if name.endswith("1") else f"{name}_2"
        if partner in names and partner != name:
            pairs[name] = partner
    taken = set(pairs) | set(pairs.values())
    groups: list[tuple[str, ...]] = []
    for name in names:
        if name in pairs:
            groups.append((name, pairs[name]))
        elif name not in taken:
            groups.append((name,))
    return groups


@dataclass(frozen=True)
class Plan:
    """What generation can fill for one samplesheet schema (shared with the generated skill.md)."""
    id_column: str | None
    reads: tuple[str, ...]                     # the read group filled: (read 1,) or (read 1, read 2)
    read_groups: tuple[tuple[str, ...], ...]   # every read group the schema declares
    data_columns: tuple[str, ...]              # other columns filled from files, by their patterns
    lane_column: str | None
    suffix: str | None                         # ".csv" / ".tsv": a file name --input accepts
    problem: str | None                        # why no samplesheet can be generated (None: it can)
    columns: Mapping[str, Column] = field(default_factory=dict)
    choice: bool = False                       # the only problem: which read group to fill


def _reachable(names: list[str], columns: Mapping[str, Column]) -> tuple[str, ...]:
    """The data columns a file can be given to by its name alone. Columns declaring the same
    patterns as another cannot (sarek's `spring_1`/`spring_2`, rnaseq's genome and transcriptome
    BAM), unless exactly one of them is a file column nf-schema stages — nanostring's `RCC_FILE`
    — while the other merely holds a name (`RCC_FILE_NAME`)."""
    same: dict[frozenset[str], list[str]] = {}
    for name in names:
        same.setdefault(frozenset(_patterns(columns[name])), []).append(name)
    out = set()
    for group in same.values():
        files = [n for n in group if columns[n].fmt in schema_mod.PATH_FORMATS]
        if len(group) == 1:
            out.update(group)
        elif len(files) == 1:
            out.update(files)
    return tuple(n for n in names if n in out)


def _id_column(sheet: InputSchema, skip: set[str]) -> str | None:
    best: tuple[int, int, str] | None = None
    for order, col in enumerate(sheet.columns):
        # A sample name is text: mhcquant's integer `ID` numbers replicates instead.
        if (not col.name or col.name in skip or not col.is_identifier
                or not ("string" in col.type or not col.type)):
            continue
        key = col.name.casefold().replace("_", "")
        rank = (0 if "id" in col.meta else 1 if key == "sample"
                else 2 if key in _IDENTITY_NAMES else None)
        if rank is not None and (best is None or (rank, order) < best[:2]):
            best = (rank, order, col.name)
    return best[2] if best else None


def _suffix(input_param: Param | None) -> str | None:
    pattern = input_param.pattern if input_param else None
    for suffix in (".csv", ".tsv"):
        if not pattern or _search(pattern, f"/x/{GENERATED_STEM}{suffix}"):
            return suffix
    return None


def plan(sheet: InputSchema, input_param: Param | None,
         empty: frozenset[str] = frozenset()) -> Plan:
    """The roles of the schema's columns. `empty` holds the columns the caller left empty
    (`--sheet-set COLUMN=`): they take no files, which is how a read group is chosen."""
    columns = {c.name: c for c in sheet.columns if c.name}
    typed = [c.name for c in columns.values() if _typed(c)]
    read_cols = [n for n in typed if _is_reads(columns[n])]
    # An emptied read column leaves its group: emptying `fastq_2` makes the pair single-end.
    groups = [g for g in (tuple(n for n in grp if n not in empty)
                          for grp in _read_groups(read_cols)) if g]
    data = _reachable([n for n in typed if n not in read_cols and n not in empty], columns)
    lane = next((n for n in columns if n.casefold() == "lane" and n not in empty), None)
    suffix = _suffix(input_param)
    with_required = [g for g in groups if any(columns[n].required for n in g)]
    reads: tuple[str, ...] = ()
    choice = None
    if len(with_required) == 1:
        reads = with_required[0]
    elif len(groups) == 1:
        reads = groups[0]
    elif groups:
        shown = "; ".join(" + ".join(g) for g in groups)
        choice = (f"the samplesheet takes reads in several column groups ({shown}) and file names "
                  "cannot tell which yours belong in; leave the groups you do not use empty, e.g. "
                  + " ".join(f"--sheet-set {n}=" for g in groups[1:] for n in g))
    # What makes generation impossible outright comes before the choice of a read group.
    problem = None
    if sheet.generation_problem:
        problem = sheet.generation_problem
    elif not columns:
        problem = "the samplesheet takes one value per line, not data files"
    elif not groups and not data:
        problem = ("the samplesheet declares no file type nfclaw could match files against (no "
                   "column's pattern names a file extension)")
    elif suffix is None:
        problem = (f"--input must match {input_param.pattern}, which accepts no CSV or TSV "
                   "samplesheet")
    return Plan(id_column=_id_column(sheet, set(read_cols) | set(data)), reads=reads,
                read_groups=tuple(groups), data_columns=data, lane_column=lane, suffix=suffix,
                problem=problem or choice, columns=columns, choice=problem is None and bool(choice))


def _allowed(col: Column) -> str:
    if col.enum:
        return "one of: " + ", ".join(col.enum)
    if col.pattern:
        return f"matching {col.pattern}"
    return col.type


def describe(sheet: InputSchema, input_param: Param | None) -> str:
    """The skill.md paragraph: what generating this samplesheet fills, and what it needs."""
    p = plan(sheet, input_param)
    if not p.columns:
        return ""
    lead = ("**From data files.** `--input` may also be the data files — a directory (searched "
            "recursively), a quoted glob, or files (`--input` once per file) — from which nfclaw "
            "writes this samplesheet")
    tail = (" Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.\n")
    if p.choice:
        return (f"{lead} once you choose the read columns: {p.problem}. Set the required columns "
                f"no file determines with `--sheet-set COLUMN=VALUE`.{tail}")
    if p.problem:
        return f"**From data files.** nfclaw cannot generate this samplesheet: {p.problem}.\n"
    fills = []
    if p.id_column:
        fills.append(f"`{p.id_column}` from file names")
    if len(p.reads) == 2:
        fills.append(f"`{p.reads[0]}`/`{p.reads[1]}` from FastQ files (mates paired by "
                     "`_R1`/`_R2`, or by `_1`/`_2` when their read names show they are mates)")
    elif p.reads:
        fills.append(f"`{p.reads[0]}` from FastQ files (single-end)")
    if p.lane_column and p.reads:
        fills.append(f"`{p.lane_column}` from Illumina lane numbers (`_L002` → 2, else 1)")
    if p.data_columns:
        fills.append(", ".join(f"`{n}`" for n in p.data_columns)
                     + " from files matching their patterns, by sample name")
    filled = {p.id_column, *p.reads, *p.data_columns} | ({p.lane_column} if p.reads else set())
    needs, defaults = [], []
    for col in sheet.columns:
        if col.name and col.required and col.name not in filled:
            if col.default not in (None, ""):
                defaults.append(f"`{col.name}` = `{json_scalar(col.default)}`")
            else:
                needs.append(f"`{col.name}` ({_allowed(col).replace('one of: ', 'one of ')})")
    named = {col.name for col in sheet.columns if col.name and col.required}
    for trigger, required in sheet.dependent_required:
        if trigger in p.reads[:1]:                      # filled on every generated row
            needs += [f"`{r}` (with `{trigger}`)" for r in required
                      if r not in filled and r not in named]
    text = f"{lead}: " + "; ".join(fills) + "."
    if defaults:
        text += " Schema defaults fill " + ", ".join(defaults) + "."
    if needs:
        text += (" Set the required columns no file determines with `--sheet-set COLUMN=VALUE` (a "
                 "constant or a `{sample}`/`{lane}` template): " + "; ".join(needs) + ".")
    else:
        text += " Set other columns with `--sheet-set COLUMN=VALUE`."
    return text + tail


# --- detecting data files in --input ------------------------------------------------------------

@dataclass(frozen=True)
class Source:
    values: tuple[str, ...]        # absolute, as given: a link keeps its own (sample) name
    sheet: str                     # the samplesheet schema, relative to the pipeline tree


def _absolute(value: str) -> Path:
    # As every local path parameter: the parent resolved, the supplied (sample) name kept.
    return inputs.absolute_local_path(value)


def _has_magic(value: str) -> bool:
    return glob.has_magic(value) or ("{" in value and "}" in value)


def _kind(path: Path, text: str) -> str:
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "samplesheet" if path.suffix.lower() in SHEET_SUFFIXES else "file"
    return "glob" if _has_magic(text) else "missing"


def detect(raw: Any, repo: Path) -> Source | None:
    """The data files `--input` names for a samplesheet, or None when the value is something else
    (a samplesheet, a remote value, `false`, or an input that is no samplesheet at all)."""
    many = isinstance(raw, (list, tuple))
    items = list(raw) if many else [raw]
    if not items or not all(isinstance(v, (str, Path)) for v in items):
        return None
    texts = [str(v) for v in items]
    if not many:
        text = texts[0].strip()
        if not text or "://" in text or text.lower() == "false" or text.lower().startswith("file:"):
            return None
        resolved = inputs.resolve(text, repo)
        if resolved is None or resolved.local_path is None or resolved.samplesheet_schema is None:
            return None
        path = _absolute(text)
        kind = _kind(path, text)
        if kind in ("samplesheet", "missing"):
            return None
        if kind == "file":
            # One file is taken for data only when a column accepts it; anything else keeps the
            # samplesheet check, which explains e.g. an .xlsx handed in by mistake.
            sheet = schema_mod.load_input_schema(repo, resolved.samplesheet_schema)
            p = plan(sheet, schema_mod.load_param_schema(repo).params.get("input")) if sheet else None
            accepting = [n for group in p.read_groups for n in group] if p else []
            if p is None or not any(_matches(p.columns[n], path)
                                    for n in (*accepting, *p.data_columns)):
                return None
        return Source((str(path),), resolved.samplesheet_schema)
    for text in texts:
        if not text.strip():
            raise NfclawError(ErrorCode.PARAMS_INVALID, "an empty --input value was given",
                              fix="Pass each data file, directory or glob once.")
        if "://" in text or text.strip().lower().startswith("file:"):
            raise NfclawError(ErrorCode.PARAMS_INVALID,
                              f"--input {text!r}: a samplesheet can only be generated from local "
                              "files",
                              fix="Download the files, or write the samplesheet yourself.")
    resolved = inputs.resolve(texts[0], repo)
    if resolved is None or resolved.samplesheet_schema is None:
        raise NfclawError(ErrorCode.PARAMS_INVALID,
                          "several --input values were given, but this pipeline's --input is not a "
                          "samplesheet",
                          fix="Pass one --input value (see Inputs in skill.md).")
    values = []
    for text in texts:
        path = _absolute(text)
        kind = _kind(path, text)
        if kind == "samplesheet":
            raise NfclawError(ErrorCode.PARAMS_INVALID,
                              f"--input {path}: a samplesheet cannot be combined with other "
                              "--input values",
                              fix="Pass the samplesheet alone, or only data files.")
        if kind == "missing":
            raise NfclawError(ErrorCode.PARAMS_INVALID, f"--input not found: {path}",
                              fix="Pass existing data files, directories or glob patterns.")
        values.append(str(path))
    return Source(tuple(dict.fromkeys(values)), resolved.samplesheet_schema)


# --- discovering the files ------------------------------------------------------------------------

def _outside(path: Path, outdir: Path) -> None:
    """A file (or what it links to) inside this run's --outdir is one of its own results."""
    if path.resolve().is_relative_to(outdir.resolve()):
        raise _bad(f"input file {path} is inside the run's --outdir ({outdir}); its results are "
                   "not its inputs",
                   fix="Pass the data files themselves, kept outside --outdir.")


def _walk(root: Path, found: dict[str, tuple[Path, Path]], outdir: Path, work_dir: Path) -> None:
    # Scanning a directory that holds the run's --outdir would read its own results as samples on
    # --resume; one that holds the shared work tree would take every task's files as samples. A
    # single task file, or a result published into the work tree, remains a valid input.
    real_root = root.resolve()
    for place, label in ((outdir, "--outdir"), (work_dir, "work directory")):
        if place.resolve().is_relative_to(real_root):
            raise _bad(f"--input {root} contains the run's {label} ({place}): its files are the "
                       "pipeline's results and task files, not data to analyse",
                       fix="Point --input at the directory that holds only the data, or keep "
                           "--outdir and the work directory outside it.")

    def walk(directory: Path, ancestors: frozenset[Path]) -> None:
        real = directory.resolve()
        if real in ancestors:
            raise _bad(f"--input {root}: {directory} links back to a directory above it (a cyclic "
                       "link)", fix="Remove the link, or pass the files with a glob.")
        try:
            with os.scandir(directory) as it:
                entries = sorted(it, key=lambda e: e.name)
        except OSError as exc:
            raise _bad(f"--input {root}: cannot read {directory}: {exc.strerror or exc}",
                       fix="Make the directory readable.") from exc
        for entry in entries:
            if entry.name.startswith("."):
                continue                                  # hidden: not data by convention
            path = directory / entry.name
            try:
                is_dir, is_file = entry.is_dir(), entry.is_file()
            except OSError:
                is_dir = is_file = False
            if is_dir:
                walk(path, ancestors | {real})
            elif is_file:
                found.setdefault(str(path), (path, root))
            else:
                raise _bad(f"--input {root}: {path} is not a readable file or directory (a broken "
                           "link?)", fix="Remove or repair it, or pass the files with a glob.")

    walk(root, frozenset())


def discover(source: Source, *, outdir: Path, work_dir: Path) -> list[tuple[Path, Path]]:
    """Every file the source names, as (file, the directory or value it was found under)."""
    found: dict[str, tuple[Path, Path]] = {}
    for text in source.values:
        path = Path(text)
        if path.is_dir():
            _walk(path, found, outdir, work_dir)
            continue
        if path.is_file():
            found.setdefault(str(path), (path, path.parent))
            continue
        matches = sorted({m for pattern in _glob_patterns(text)
                          for m in glob.glob(pattern, recursive=True)})
        if not matches:
            raise _bad(f"--input {text} matches no files",
                       fix="Check the pattern (quote it so the shell does not expand it).")
        for match in map(Path, matches):
            where = (match if match.is_dir() else match.parent).resolve()
            if where.is_relative_to(work_dir.resolve()):
                raise _bad(f"--input {text} matches {match}, inside the run's work directory "
                           f"({work_dir}): task files are not data to analyse",
                           fix="Narrow the glob to the data, or keep the work directory outside "
                               "the tree it searches.")
            if match.is_dir():
                _walk(match, found, outdir, work_dir)
            elif match.is_file():
                found.setdefault(str(match), (match, match.parent))
            else:
                raise _bad(f"--input {text}: {match} is not a readable file (a broken link?)",
                           fix="Remove or repair it.")
    for path, _ in found.values():
        _outside(path, outdir)
    return list(found.values())


# --- FastQ: samples, lanes and mates ---------------------------------------------------------------

@dataclass(frozen=True)
class _Read:
    path: Path
    sample: str
    lane: int | None
    chunk: int | None
    kind: str          # "R" read, "I" index read, "bare" bare number, "" no token
    read: int | None
    number: str | None  # the Illumina sample number (S<n>)


def _read_stem(name: str) -> str:
    return _FASTQ_SUFFIX.sub("", name) if _FASTQ_SUFFIX.search(name) else _stem(name)


def _parse_read(path: Path) -> _Read:
    stem = _read_stem(path.name)
    for rx in (_ILLUMINA, _TOKEN):
        if m := rx.match(stem):
            lane, chunk = m.group("lane"), m.group("chunk")
            return _Read(path, m.group("sample"), int(lane) if lane else None,
                         int(chunk) if chunk else None, m.group("kind").upper(),
                         int(m.group("read")), m.groupdict().get("number"))
    if m := _BARE.match(stem):
        return _Read(path, m.group("sample"), None, None, "bare", int(m.group("read")), None)
    return _Read(path, stem, None, None, "", None, None)


def _names_readable(path: Path) -> bool:
    """Whether the standard library can read the file's read names (it has no zstd reader)."""
    return path.suffix.lower() != ".zst"


def _first_read_identity(path: Path) -> tuple[str | None, int | None]:
    """The first read's molecule name and explicit mate role, retaining contradictions."""
    suffix = path.suffix.lower()
    opener = {".gz": gzip.open, ".bz2": bz2.open, ".xz": lzma.open}.get(suffix, open)
    if not _names_readable(path):
        raise _bad(f"cannot read the read names of zstd-compressed {path.name} (the Python standard "
                   "library has no zstd reader)",
                   fix="Name mates _R1/_R2 (their names alone then pair them, with a note), or "
                       "write the samplesheet yourself.")
    try:
        with opener(path, "rb") as fh:
            line = fh.readline(1 << 16)
    except (OSError, EOFError, zlib.error, lzma.LZMAError) as exc:
        raise _bad(f"cannot read FastQ file {path}: {exc}",
                   fix="Restore a valid FastQ file (compressed as its name says).") from exc
    if not line:
        return None, None
    text = line.decode("utf-8", "replace").rstrip("\r\n")
    if not text.startswith("@"):
        raise _bad(f"{path} is not a FastQ file: its first line does not start with '@'",
                   fix="Pass FastQ files (or leave this one out of --input).")
    words = text[1:].split()
    name = words[0] if words else ""
    roles = set()
    if match := re.search(r"[/._]([12])$", name):
        # The terminal SRA spot number is a molecule identity, not a mate label.
        if not _ACCESSION.fullmatch(name):
            roles.add(int(match[1]))
    if len(words) > 1 and re.match(r"^[12]:", words[1]):
        roles.add(int(words[1][0]))
    return name, next(iter(roles)) if len(roles) == 1 else -1 if roles else None


def _first_read_name(path: Path) -> str | None:
    return _first_read_identity(path)[0]


def _compatible_roles(first: int | None, second: int | None) -> bool:
    return first in (None, 1) and second in (None, 2)


def _mates(first: str, second: str) -> bool:
    """Illumina and SRA mates share their read name; older tools suffix it /1 and /2 (or .1/.2)."""
    # SRA accession.spot-id names a molecule, not its read number. Distinct spots
    # ending in .1 and .2 are different molecules. An additional suffix on the
    # same spot (e.g. SRR390728.123/1 or SRR390728.123.1) may identify its mate.
    if first != second and (_ACCESSION.fullmatch(first) or _ACCESSION.fullmatch(second)):
        return False
    return first == second or (len(first) == len(second) > 2 and first[:-1] == second[:-1]
                               and first[-2] in "/._" and first[-1] == "1" and second[-1] == "2")


def _strong(first: str, second: str) -> bool:
    """Whether two read names that pair also identify one molecule: suffixed mates, an Illumina
    name (instrument:run:flowcell:lane:tile:x:y) or an SRA/ENA spot. Equal generic names (`read1`
    in every file a simulator or a renumbering wrote) are no evidence either way."""
    return first != second or first.count(":") >= 4 or bool(_ACCESSION.match(first))


@dataclass
class _Unit:
    sample: str
    lane: int | None
    chunk: int | None
    reads: list[Path]
    flag: str = ""           # "lone": a read-1 file whose mate the name promises but is missing


def _read_units(files: list[Path], notes: list[str], paired_ok: bool) -> list[_Unit]:
    reads = [_parse_read(p) for p in files]
    index = [r for r in reads if r.kind == "I"]
    if index:
        notes.append(f"Ignored {len(index)} index read file(s) (`_I1`/`_I2`), which no read column "
                     f"takes: {_shown([r.path.name for r in index])}.")
    undetermined = [r for r in reads if r.sample == "Undetermined" and r.number == "0"]
    if undetermined:
        notes.append("Ignored the demultiplexer's unassigned reads "
                     f"({_shown([r.path.name for r in undetermined])}): `Undetermined` is no sample.")
    reads = [r for r in reads if r.kind != "I" and r not in undetermined]
    if beyond := [r for r in reads if r.kind == "R" and r.read not in (1, 2)]:
        raise _bad(f"read {beyond[0].read} files are not taken by any read column: "
                   f"{_shown([r.path.name for r in beyond])}",
                   fix="Leave them out of --input, or write the samplesheet yourself.")
    slots: dict[tuple, dict[int, Path]] = {}
    for r in reads:
        key = ((r.sample, r.lane, r.chunk, "R") if r.kind == "R"
               else (r.sample, None, None, "bare") if r.kind == "bare"
               else (r.sample, None, None, ""))
        slot = slots.setdefault(key, {})
        number = r.read or 1
        if number in slot:
            raise _bad(f"two files are read {number} of sample {r.sample!r}: {slot[number]} and "
                       f"{r.path}", fix="Pass each read file once (check for copies in "
                                        "subdirectories).")
        slot[number] = r.path
    units: list[_Unit] = []
    for key, slot in slots.items():
        sample, lane, chunk, kind = key[:4]
        if kind == "R":
            if 1 not in slot:
                raise _bad(f"{slot[2].name} is read 2 of sample {sample!r}, but its read 1 file is "
                           "missing", fix="Restore the read 1 file, or leave read 2 out.")
            if 2 in slot:
                _confirm(slot[1], slot[2], notes)
                units.append(_Unit(sample, lane, chunk, [slot[1], slot[2]]))
            else:
                units.append(_Unit(sample, lane, chunk, [slot[1]], "lone"))
        elif kind == "bare":
            if len(slot) == 2:
                if not (_names_readable(slot[1]) and _names_readable(slot[2])):
                    raise _bad(f"cannot tell whether {slot[1].name} and {slot[2].name} are the two "
                               "reads of one library: zstd-compressed read names cannot be read "
                               "to compare", fix="Name mates _R1/_R2, or write the samplesheet "
                                                 "yourself.")
                (first, first_role), (second, second_role) = (
                    _first_read_identity(slot[1]), _first_read_identity(slot[2]))
                if first is None or second is None:
                    raise _bad(f"cannot tell whether {slot[1].name} and {slot[2].name} are the two "
                               "reads of one library: an empty file has no read names to compare",
                               fix="Name them _R1/_R2, or write the samplesheet yourself.")
                if _mates(first, second) and not _compatible_roles(first_role, second_role):
                    raise _bad(f"cannot infer mate orientation for {slot[1].name} and {slot[2].name}: "
                               "their explicit read-header mate labels contradict the proposed pairing",
                               fix="Check the original data and write an explicit samplesheet.")
                if _mates(first, second) and not _strong(first, second):
                    raise _bad(f"cannot tell whether {slot[1].name} and {slot[2].name} are the two "
                               f"reads of one library: both start with the generic read name "
                               f"{first!r}, which identifies no molecule",
                               fix="Name mates _R1/_R2, or link separate libraries under names "
                                   "that do not end in _1/_2.")
                if _mates(first, second):
                    units.append(_Unit(sample, None, None, [slot[1], slot[2]]))
                    continue
                for path in (slot[1], slot[2]):
                    units.append(_Unit(_read_stem(path.name), None, None, [path],
                                       "unpaired"))
            else:
                (path,) = slot.values()
                units.append(_Unit(_read_stem(path.name), None, None, [path], "lone"))
        else:
            (path,) = slot.values()
            units.append(_Unit(_read_stem(path.name), None, None, [path]))
    _refuse_unnamed_mates(units, notes)
    seen: dict[tuple, _Unit] = {}
    for unit in units:
        key = (unit.sample, unit.lane, unit.chunk)
        if key in seen:
            raise _bad(f"{seen[key].reads[0].name} and {unit.reads[0].name} both give sample "
                       f"{unit.sample!r} a read set, with no lane or chunk number to tell them apart "
                       "(a copy, or a concatenated file?)",
                       fix="Pass each library once; name several runs of one sample with Illumina "
                           "lane numbers, or write the samplesheet yourself.")
        seen[key] = unit
    if any(len(u.reads) == 2 for u in units):
        if not paired_ok:
            raise _bad("the samplesheet takes single-end reads in one column, but the files hold "
                       "read pairs: " + _shown([u.reads[0].name for u in units
                                                if len(u.reads) == 2]),
                       fix="Pass single-end read files, or write the samplesheet yourself.")
        if odd := [u for u in units if u.flag]:
            raise _bad("the other samples are paired-end, but these files have no mate: "
                       + _shown([u.reads[0].name for u in odd]),
                       fix="Restore the missing mates, or leave these files out of --input. A "
                           "deliberately single-end library can be linked under a name without "
                           "a read number (x.fastq.gz); otherwise write the samplesheet yourself.")
    return units


def _refuse_unnamed_mates(units: list[_Unit], notes: list[str]) -> None:
    """Two would-be single-end files whose names differ only by a read mark (`_read1`/`_read2`,
    `_F`/`_R`) and whose first reads are mates are one library under a naming nfclaw does not
    parse: taking them for two samples would analyse it twice, as single-end."""
    singles = [u.reads[0] for u in units if len(u.reads) == 1]
    partners: dict[tuple[Path, str], dict[str, Path]] = {}
    for path in singles:
        stem = _read_stem(path.name)
        for i, char in enumerate(stem):
            if char in _READ_MARKS or char in _READ_MARKS.values():
                key = (path.parent, f"{stem[:i]}\0{stem[i + 1:]}")
                partners.setdefault(key, {})[char] = path
    names: dict[Path, tuple[str | None, int | None]] = {}

    def read_name(path: Path) -> tuple[str | None, int | None]:
        if path not in names:
            names[path] = _first_read_identity(path) if _names_readable(path) else (None, None)
        return names[path]

    for marks in partners.values():
        for first, second in _READ_MARKS.items():
            if first in marks and second in marks:
                (a, a_role), (b, b_role) = read_name(marks[first]), read_name(marks[second])
                if a and b and _mates(a, b) and not _compatible_roles(a_role, b_role):
                    raise _bad(f"cannot infer mate orientation for {marks[first].name} and "
                               f"{marks[second].name}: their explicit read-header mate labels "
                               "contradict the proposed pairing",
                               fix="Check the original data and write an explicit samplesheet.")
                if a and b and _mates(a, b) and not _strong(a, b):
                    notes.append(f"{marks[first].name} and {marks[second].name} start with the same "
                                 f"generic read name ({a!r}); they are taken for two single-end "
                                 "samples. If they are the two reads of one library, name them "
                                 "<sample>_R1 / <sample>_R2.")
                elif a and b and _mates(a, b):
                    raise _bad(f"{marks[first].name} and {marks[second].name} hold the two reads of "
                               "one library (their read names pair), but their names carry no read "
                               "number nfclaw recognises",
                               fix="Name (or link) them <sample>_R1 / <sample>_R2 so they are "
                                   "analysed as one paired-end library.")


def _confirm(first: Path, second: Path, notes: list[str]) -> None:
    if not (_names_readable(first) and _names_readable(second)):
        notes.append(f"Paired {first.name} with {second.name} by name only: zstd-compressed read "
                     "names cannot be read to compare.")
        return
    (a, a_role), (b, b_role) = _first_read_identity(first), _first_read_identity(second)
    if a is None or b is None:
        notes.append(f"Paired {first.name} with {second.name} by name only: an empty file has no "
                     "read names to compare.")
    elif not _mates(a, b):
        # The names state the pairing; desynchronised mates are what some pipelines repair
        # (fastqrepair). Said before launch, never silently, and never undone by guessing.
        notes.append(f"{first.name} and {second.name} are paired as their names say, but their first "
                     f"read names differ ({a!r}, {b!r}): check that they belong together (a "
                     "swapped, truncated or desynchronised mate).")
    elif not _compatible_roles(a_role, b_role):
        notes.append(f"Paired {first.name} with {second.name} as their filenames declare, but "
                     "their explicit read-header mate labels disagree with that orientation; "
                     "check the original data and the generated samplesheet before analysis.")


# --- other data files ---------------------------------------------------------------------------

def _stem(name: str) -> str:
    """A data file's sample name: without compression, its extension and an indexed extension
    (`n1.bam.bai`, `n1.bai`, `x.vcf.gz.tbi` and `x.vcf.gz` all name `n1`/`x`)."""
    def strip(text: str) -> tuple[str, str]:
        for c in _COMPRESSION:
            if text.lower().endswith(c) and len(text) > len(c):
                text = text[:-len(c)]
                break
        root, ext = os.path.splitext(text)
        return (root or text), ext.lower()

    root, ext = strip(name)
    if ext in _INDEXES:
        root, _ = strip(root)
    return root


# --- assignments ------------------------------------------------------------------------------------

def parse_assignments(items: list[str]) -> dict[str, str]:
    """`--sheet-set COLUMN=VALUE` (repeatable) as {column: value}; an empty value is kept."""
    out: dict[str, str] = {}
    for item in items:
        column, sep, value = item.partition("=")
        column = column.strip()
        if not sep or not column:
            raise NfclawError(ErrorCode.PARAMS_INVALID,
                              f"--sheet-set expects COLUMN=VALUE, got {item!r}",
                              fix="e.g. --sheet-set strandedness=auto")
        if column in out:
            raise NfclawError(ErrorCode.PARAMS_INVALID,
                              f"--sheet-set sets column '{column}' more than once",
                              fix="Set each samplesheet column once.")
        out[column] = value.strip()
    return out


def assignments_from_mapping(values: Mapping[str, Any]) -> dict[str, str]:
    """A chain stage's `sheet_set` object, with scalars written as JSON writes them."""
    out: dict[str, str] = {}
    for column, value in values.items():
        if not isinstance(column, str) or not column or isinstance(value, (dict, list)) \
                or value is None:
            raise NfclawError(ErrorCode.PARAMS_INVALID,
                              f"sheet_set: {column!r} must map a column name to a text or number "
                              "value", fix='e.g. "sheet_set": {"strandedness": "auto"}')
        out[column] = json_scalar(value).strip() if not isinstance(value, str) else value.strip()
    return out


def _check_assignments(assignments: Mapping[str, str], p: Plan) -> None:
    issues = []
    for column, value in assignments.items():
        col = p.columns.get(column)
        if col is None:
            issues.append(f"the samplesheet has no column '{column}' (columns: "
                          f"{', '.join(p.columns)})")
            continue
        keys = _PLACEHOLDER.findall(value)
        if unknown := [k for k in keys if k not in _TEMPLATE_KEYS]:
            issues.append(f"'{column}': unknown placeholder "
                          + ", ".join("{" + k + "}" for k in unknown)
                          + " (templates may use {sample} and {lane})")
            continue
        if _PLACEHOLDER.sub("", value).count("{") or _PLACEHOLDER.sub("", value).count("}"):
            issues.append(f"'{column}': unbalanced braces in {value!r}")
            continue
        if value and any(column in group for group in p.read_groups):
            issues.append(f"'{column}' is taken from the input files; leave it out (or empty it "
                          "to use another read column)")
        elif column == p.id_column and value and "{sample}" not in value:
            issues.append(f"'{column}' names each sample from its files; a value must contain "
                          "{sample} (e.g. P1_{sample})")
        elif value and not keys:
            issues += [f"'{column}': {i}" for i in _value_issues(col, value)]
    if issues:
        raise NfclawError(ErrorCode.PARAMS_INVALID, "--sheet-set cannot be applied.",
                          fix="Use the samplesheet columns and values listed in skill.md (Inputs).",
                          details={"issues": issues})


def _value_issues(col: Column, value: str) -> list[str]:
    return samplesheet.value_problems(col, value)


# --- building the sheet -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Generated:
    text: str
    suffix: str
    header: tuple[str, ...]
    rows: tuple[dict[str, str], ...]
    files: tuple[Path, ...]               # every data file the sheet names: the run's inputs
    id_column: str | None
    summary: str
    notes: tuple[str, ...]
    record: dict

    @property
    def filename(self) -> str:
        return GENERATED_STEM + self.suffix


def generate(source: Source, repo: Path, *, pipeline: str, assignments: Mapping[str, str],
             outdir: Path, work_dir: Path) -> Generated:
    """Write the samplesheet `pipeline` expects from the files `source` names (see the module
    docstring). Raises NfclawError, naming what to change, instead of writing a doubtful sheet."""
    sheet = schema_mod.load_input_schema(repo, source.sheet)
    if sheet is None:
        raise _bad(f"{pipeline} declares no samplesheet columns to generate")
    input_param = schema_mod.load_param_schema(repo).params.get("input")
    _check_assignments(assignments, plan(sheet, input_param))
    # An assigned column takes no files: an empty one leaves its read group (how a group is
    # chosen), a constant one fills the column on every row instead.
    p = plan(sheet, input_param, frozenset(assignments))
    if p.problem:
        raise _bad(f"nfclaw cannot generate the {pipeline} samplesheet: {p.problem}",
                   fix="Follow the hint above, or write the samplesheet yourself (Inputs in "
                       "skill.md).")
    found = discover(source, outdir=outdir, work_dir=work_dir)
    # Which column(s) each file fits: the read group as one target, every other typed column alone.
    reads: list[Path] = []
    data: dict[tuple[str, str], Path] = {}
    ignored: list[str] = []
    ambiguous: list[str] = []
    optional: set[str] = set()
    for path, base in sorted(found, key=lambda item: str(item[0])):
        fits = [n for n in (*p.reads, *p.data_columns) if _matches(p.columns[n], path)]
        # A column nf-schema treats as a file wins over one that only names a file (nanostring's
        # RCC_FILE over RCC_FILE_NAME, both ending in .RCC).
        if any(p.columns[n].fmt in schema_mod.PATH_FORMATS for n in fits):
            fits = [n for n in fits if p.columns[n].fmt in schema_mod.PATH_FORMATS
                    or n in p.reads]
        targets = list(dict.fromkeys("reads" if n in p.reads else n for n in fits))
        if not targets:
            ignored.append(os.path.relpath(path, base) if path.is_relative_to(base) else str(path))
        elif len(targets) > 1:
            names = [n for n in fits if n not in p.reads[1:]]
            ambiguous.append(f"{path.name} fits columns {', '.join(names)}")
            optional |= {n for n in names if not p.columns[n].required}
        elif targets[0] == "reads":
            reads.append(path)
        else:
            key = (_stem(path.name), targets[0])
            if key in data:
                raise _bad(f"two files fit column '{targets[0]}' of sample {key[0]!r}: {data[key]} "
                           f"and {path}", fix="Pass each file once.")
            data[key] = path
    if ambiguous:
        raise _bad("these files fit several samplesheet columns: " + _shown(ambiguous),
                   fix="Leave the column you do not use empty"
                       + (", e.g. " + " ".join(f"--sheet-set {n}=" for n in sorted(optional))
                          if optional else " with --sheet-set COLUMN=")
                       + ", or pass only the files of one kind.")
    if not reads and not data:
        kinds = ", ".join(f"{n} ({_patterns(p.columns[n])[0]})" for n in (*p.reads, *p.data_columns))
        raise _bad(f"No input file fits a column of the {pipeline} samplesheet (it takes {kinds}).",
                   fix="Check --input, and the file names and extensions the columns accept.")
    notes: list[str] = []
    units = _read_units(reads, notes, paired_ok=len(p.reads) == 2) if reads else []
    # Each sample's read sets and other files, grouped once (a plate can hold thousands).
    sample_units: dict[str, list[_Unit]] = {}
    for unit in units:
        sample_units.setdefault(unit.sample, []).append(unit)
    sample_data: dict[str, dict[str, str]] = {}
    for (sample, col), path in sorted(data.items()):
        sample_data.setdefault(sample, {})[col] = str(path)
    samples = sorted(set(sample_units) | set(sample_data))
    _check_paths([path for u in units for path in u.reads] + list(data.values()))
    _check_shapes(samples, sample_units, sample_data)
    rows: list[dict[str, str]] = []
    row_sample: list[tuple[str, int]] = []
    for sample in samples:
        attached = sample_data.get(sample, {})
        mine = sorted(sample_units.get(sample, []),
                      key=lambda u: (u.lane or 0, u.chunk or 0, str(u.reads[0])))
        for unit in mine or [None]:
            row: dict[str, str] = {}
            if p.id_column:
                row[p.id_column] = sample
            if unit is not None:
                row[p.reads[0]] = str(unit.reads[0])
                if len(p.reads) == 2:
                    row[p.reads[1]] = str(unit.reads[1]) if len(unit.reads) == 2 else ""
                if p.lane_column:
                    row[p.lane_column] = str(unit.lane or 1)
            row.update(attached)
            rows.append(row)
            row_sample.append((sample, (unit.lane or 1) if unit is not None else 1))
    for column, value in assignments.items():
        for row, (sample, lane) in zip(rows, row_sample):
            row[column] = value.replace("{sample}", sample).replace("{lane}", str(lane))
    # Whatever filled it — the files or an assignment — the lane column must still tell apart the
    # read sets of one sample.
    lane_column = next((n for n in p.columns if n.casefold() == "lane"), None)
    if lane_column and units:
        _check_lanes(rows, row_sample, lane_column)
    _check_identities(rows, p, pipeline)
    defaults = {}
    for col in sheet.columns:
        if (col.name and col.required and col.name not in assignments
                and all(not r.get(col.name) for r in rows) and col.default not in (None, "")):
            defaults[col.name] = json_scalar(col.default)
            for row in rows:
                row[col.name] = defaults[col.name]
    _check_complete(rows, sheet, p, pipeline)
    _check_unique(rows, sheet, p)
    filled = {k for r in rows for k, v in r.items() if v}
    keep = filled | {c.name for c in sheet.columns if c.name and c.required} | set(p.reads)
    header = [c.name for c in sheet.columns if c.name in keep]
    delimiter = samplesheet.delimiter_for(Path(GENERATED_STEM + p.suffix))
    _check_cells(rows, delimiter)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
    writer.writerow(header)
    writer.writerows([[row.get(h, "") for h in header] for row in rows])
    text = buffer.getvalue()
    _validate(text, p.suffix, sheet, pipeline)
    # Every local path the sheet names is an input: the files it was generated from, and paths a
    # --sheet-set constant, template or schema default wrote into a path column.
    path_columns = {*p.reads, *p.data_columns} | {
        c.name for c in sheet.columns if c.name and c.path_format()}
    files = tuple(dict.fromkeys(Path(row[c]) for row in rows for c in header
                                if c in path_columns and row.get(c) and "://" not in row[c]
                                and (p.columns[c].path_format(row[c])
                                     or not p.columns[c].path_format()
                                     and c in {*p.reads, *p.data_columns})))
    paired = sum(1 for u in units if len(u.reads) == 2)
    record = {"version": 1, "sources": list(source.values), "schema": source.sheet,
              "files": len(files), "samples": len(samples), "rows": len(rows),
              "paired_end": paired, "single_end": len(units) - paired,
              "from_files": [c for c in header if c in {p.id_column, *p.reads, *p.data_columns}
                             or (c == p.lane_column and units)],
              "sheet_set": dict(assignments), "defaults": defaults, "ignored": ignored[:50],
              "ignored_count": len(ignored)}
    where = source.values[0] if len(source.values) == 1 else f"{len(source.values)} --input values"
    layout = (f" ({paired} paired-end, {len(units) - paired} single-end read sets)" if units else "")
    summary = (f"Generated the {pipeline} samplesheet from {len(files)} files in {where}: "
               f"{len(samples)} sample(s){layout}, {len(rows)} row(s); columns from the files: "
               f"{', '.join(record['from_files'])}"
               + (f"; from --sheet-set: {', '.join(c for c in header if c in assignments)}"
                  if any(c in assignments for c in header) else "")
               + (f"; schema defaults: {', '.join(defaults)}" if defaults else "")
               + (f". Ignored {len(ignored)} file(s) no column takes: {_shown(ignored)}"
                  if ignored else "") + ".")
    return Generated(text=text, suffix=p.suffix, header=tuple(header), rows=tuple(rows),
                     files=files, id_column=p.id_column, summary=summary, notes=tuple(notes),
                     record=record)


def _check_paths(paths: list[Path]) -> None:
    issues = [f"{path}: {issue}" for path in paths
              for issue in inputs.local_name_issues(str(path), "file-path")]
    if issues:
        raise _bad("These input files have names the pipelines' tasks cannot stage safely.",
                   fix="Rename them or link them under plain names (letters, digits, dots, "
                       "underscores, hyphens).", issues=issues)


def _check_identities(rows: list[dict[str, str]], p: Plan, pipeline: str) -> None:
    """The sample names written — from file names, or a --sheet-set template around them — must be
    safe identifiers that the identity column's pattern accepts. Never altered: refused, naming the
    file they came from."""
    if not p.id_column:
        return
    column = p.columns[p.id_column]
    issues: dict[str, str] = {}
    for row in rows:
        value = row.get(p.id_column, "")
        origin = next((Path(v).name for c, v in row.items()
                       if c in (*p.reads, *p.data_columns) and v), "?")
        if value in issues:
            continue
        if not samplesheet._safe_identifier(value):
            issues[value] = (f"sample name {value!r} (from {origin}) must start with a letter, "
                             "digit or underscore and contain only letters, digits, dots, "
                             "underscores or hyphens")
        elif column.pattern and not _search(column.pattern, value):
            issues[value] = (f"sample name {value!r} (from {origin}) does not match the {pipeline} "
                             f"'{column.name}' pattern {column.pattern}")
    if issues:
        raise _bad("Sample names come from the file names, which these do not allow.",
                   fix=f"Give the files (or links to them) names that fit, or wrap them in a "
                       f"template that does (--sheet-set {p.id_column}=S{{sample}}); nfclaw never "
                       "renames samples.", issues=list(issues.values()))


def _check_shapes(samples: list[str], sample_units: dict[str, list[_Unit]],
                  sample_data: dict[str, dict[str, str]]) -> None:
    shapes: dict[tuple[str, ...], list[str]] = {}
    for sample in samples:
        kinds = (("FastQ reads",) if sample in sample_units else ()) + tuple(
            sorted(sample_data.get(sample, {})))
        shapes.setdefault(kinds, []).append(sample)
    if len(shapes) > 1:
        raise _bad("The samples do not all bring the same kinds of files, which suggests stray "
                   "or missing files.",
                   fix="Pass only the files of the samples to analyse (a narrower directory or a "
                       "glob), or write the samplesheet yourself for mixed inputs.",
                   issues=[f"{', '.join(kinds)}: {_shown(names)}"
                           for kinds, names in shapes.items()])


def _check_lanes(rows: list[dict[str, str]], row_sample: list[tuple[str, int]],
                 lane_column: str) -> None:
    """The lane column tells the read sets of one sample apart (sarek names read groups by it)."""
    seen: dict[tuple[str, str], dict[str, str]] = {}
    for row, (sample, _) in zip(rows, row_sample):
        key = (sample, row.get(lane_column, ""))
        if key in seen:
            reads = [Path(r[c]).name for r in (seen[key], row) for c in r
                     if c != lane_column and Path(r[c]).is_absolute()][:4]
            raise _bad(f"sample {sample!r} would have two read sets with '{lane_column}' "
                       f"{key[1]!r} ({_shown(reads)}): the column could no longer tell them apart",
                       fix="Merge the split files of each lane, keep {lane} in a --sheet-set "
                           f"{lane_column} value, or write the samplesheet yourself.")
        seen[key] = row


def _check_complete(rows: list[dict[str, str]], sheet: InputSchema, p: Plan,
                    pipeline: str) -> None:
    issues: list[str] = []
    for col in sheet.columns:
        if col.name and col.required and any(not r.get(col.name) for r in rows):
            if col.name in p.reads[1:]:
                issues.append(f"'{col.name}' (required): {pipeline} takes paired-end reads only, "
                              "and some read sets are single-end")
            elif col.name in p.reads[:1]:
                issues.append(f"'{col.name}' (required): some samples have no FastQ read files")
            else:
                issues.append(f"'{col.name}' (required; {_allowed(col)})")
    for trigger, required in sheet.dependent_required:
        for req in required:
            if any(r.get(trigger) and not r.get(req) for r in rows):
                text = f"'{req}' (required with '{trigger}'; {_allowed(p.columns[req])})" \
                    if req in p.columns else f"'{req}' (required with '{trigger}')"
                if text not in issues:
                    issues.append(text)
    if sheet.any_of_required and any(
            not any(all(r.get(c) for c in group) for group in sheet.any_of_required) for r in rows):
        issues.append("each row needs one of: "
                      + "; ".join(" + ".join(g) for g in sheet.any_of_required))
    if issues:
        raise _bad(f"The {pipeline} samplesheet needs values nfclaw cannot take from the files.",
                   fix="Set them with --sheet-set COLUMN=VALUE (a constant, or a template using "
                       "{sample} or {lane}) and run again.", issues=issues)


def _check_unique(rows: list[dict[str, str]], sheet: InputSchema, p: Plan) -> None:
    """nf-schema's uniqueEntries: no two rows may share the values of these columns (cells left
    empty are left out of the comparison; a row with all of them empty is not compared)."""
    for combo in sheet.unique_entries:
        seen: dict[tuple, int] = {}
        for number, row in enumerate(rows, start=2):
            key = tuple((c, row[c]) for c in combo if row.get(c))
            if not key:
                continue
            if key in seen:
                cols = ", ".join(f"'{c}'" for c in combo)
                other = [c for c in combo if c != p.id_column]
                raise _bad(f"rows {seen[key]} and {number} would repeat the values of {cols}, "
                           "which the samplesheet requires to be unique",
                           fix=(f"Make them differ, e.g. --sheet-set {other[0]}={{sample}}_{{lane}} "
                                f"or {other[0]}={{lane}}" if other else
                                "This pipeline takes one row per sample: merge each sample's "
                                "read files first, or write the samplesheet yourself."))
            seen[key] = number


def _check_cells(rows: list[dict[str, str]], delimiter: str) -> None:
    label = "tab" if delimiter == "\t" else "comma"
    bad = sorted({v for r in rows for v in r.values()
                  if delimiter in v or '"' in v or "\n" in v or "\r" in v})
    if bad:
        raise _bad(f"these values hold the samplesheet's delimiter ({label}), a quote or a line "
                   "break, which some pipelines' own samplesheet readers split: " + _shown(bad),
                   fix="Rename the files or directories, or link them under plain names.")


def _validate(text: str, suffix: str, sheet: InputSchema, pipeline: str) -> None:
    with tempfile.TemporaryDirectory(prefix="nfclaw-samplesheet-") as scratch:
        path = Path(scratch) / (GENERATED_STEM + suffix)
        path.write_text(text, encoding="utf-8")
        issues = samplesheet.validate(path, sheet)
    if issues:
        raise _bad(f"The samplesheet generated for {pipeline} fails its samplesheet check.",
                   fix="Adjust --input or --sheet-set, or write the samplesheet yourself.",
                   issues=issues)


def write(generated: Generated, directory: Path) -> Path:
    """Stage the sheet (beside the run's params file); the bytes are those that were validated."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / generated.filename
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(generated.text, encoding="utf-8")
    os.replace(tmp, path)
    return path


def sheet_changes(previous: Path, generated: Generated) -> str | None:
    """How `generated` differs from the samplesheet at `previous` (None when identical or when
    there is none): the samples added and removed, or that only files or values changed."""
    try:
        before = previous.read_text(encoding="utf-8")
    except OSError:
        return None
    if before == generated.text:
        return None
    if not generated.id_column:
        return "other samples, files or values"
    try:
        old = {r.get(generated.id_column) or "" for r in
               csv.DictReader(io.StringIO(before), delimiter=samplesheet.delimiter_for(previous))}
    except csv.Error:
        old = set()
    new = {r[generated.id_column] for r in generated.rows}
    changes = [f"{label}: {_shown(sorted(names))}"
               for label, names in (("added", new - old), ("removed", old - new)) if names]
    return "; ".join(changes) or "same samples, other files or values"


def resume_note(previous: Path, generated: Generated) -> str | None:
    """On --resume: say how the regenerated sheet differs from the one the previous launch used."""
    changes = sheet_changes(previous, generated)
    if changes is None:
        return None
    return ("--resume regenerated the samplesheet from --input, and it differs from the one the "
            f"previous launch used ({changes}). Nextflow reuses only the tasks whose inputs are "
            "unchanged.")


def named_paths(sheet: Path) -> set[str]:
    """The absolute paths a samplesheet names (empty when it cannot be read)."""
    try:
        with sheet.open(newline="", encoding="utf-8") as fh:
            return {value for row in csv.reader(fh, delimiter=samplesheet.delimiter_for(sheet))
                    for value in row if value.startswith("/")}
    except (OSError, csv.Error, UnicodeDecodeError):
        return set()


def absolute(value: str) -> str:
    """A local --input value made absolute as given (a link keeps its name); a remote one as is."""
    return value if "://" in value else str(_absolute(value))


def present(source: Source) -> bool:
    """Whether any data the source names still exists (a directory, a file, a glob match)."""
    return any(Path(v).exists() or (_has_magic(v) and any(
        glob.glob(p, recursive=True) for p in _glob_patterns(v))) for v in source.values)
