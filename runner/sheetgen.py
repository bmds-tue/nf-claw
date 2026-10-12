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

import csv
import glob
import gzip
import io
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

_FASTQ_SUFFIX = re.compile(r"\.f(?:ast)?q(?:\.gz)?$", re.IGNORECASE)
# bcl2fastq / BCL Convert: <sample>_S<n>[_L<lane>]_<R|I><read>_<chunk>
_ILLUMINA = re.compile(r"^(?P<sample>.+)_S(?P<number>\d+)(?:_L(?P<lane>\d{3}))?_(?P<kind>[RI])"
                       r"(?P<read>\d)_(?P<chunk>\d{3})$")
# An explicit read token: <sample>[_L<lane>]{_|.}R<read>[_<chunk>]. Index reads are recognised only
# in the demultiplexer's full form above: `Patient_I1` may well be a sample.
_TOKEN = re.compile(r"^(?P<sample>.+?)(?:_L(?P<lane>\d{3}))?[._](?P<kind>[Rr])(?P<read>\d)"
                    r"(?:_(?P<chunk>\d{3}))?$")
# A bare read number: <sample>{_|.}<1|2> — mates only when their reads say so.
_BARE = re.compile(r"^(?P<sample>.+)[._](?P<read>[12])$")
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
    problem = None
    with_required = [g for g in groups if any(columns[n].required for n in g)]
    reads: tuple[str, ...] = ()
    if len(with_required) == 1:
        reads = with_required[0]
    elif len(groups) == 1:
        reads = groups[0]
    elif groups:
        shown = "; ".join(" + ".join(g) for g in groups)
        problem = (f"the samplesheet takes reads in several column groups ({shown}) and file names "
                   "cannot tell which yours belong in; leave the groups you do not use empty, e.g. "
                   + " ".join(f"--sheet-set {n}=" for g in groups[1:] for n in g))
    if not columns:
        problem = "the samplesheet takes one value per line, not data files"
    elif not reads and not data and problem is None:
        problem = ("the samplesheet declares no file type nfclaw could match files against (no "
                   "column's pattern names a file extension)")
    elif suffix is None and problem is None:
        problem = (f"--input must match {input_param.pattern}, which accepts no CSV or TSV "
                   "samplesheet")
    return Plan(id_column=_id_column(sheet, set(read_cols) | set(data)), reads=reads,
                read_groups=tuple(groups), data_columns=data, lane_column=lane, suffix=suffix,
                problem=problem, columns=columns)


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
            "recursively), a glob or several files — from which nfclaw writes this samplesheet")
    tail = (" Preview it with `--check`; a run records it in `<outdir>/provenance/` for replay.\n")
    if p.problem and len(p.read_groups) > 1:
        return (f"{lead} once you choose the read columns: {p.problem}. Set the required columns "
                f"no file determines with `--sheet-set COLUMN=VALUE`.{tail}")
    if p.problem:
        return f"**From data files.** nfclaw cannot generate this samplesheet: {p.problem}.\n"
    fills = []
    if p.id_column:
        fills.append(f"`{p.id_column}` from file names")
    if len(p.reads) == 2:
        fills.append(f"`{p.reads[0]}`/`{p.reads[1]}` from FastQ files (mates paired by "
                     "`_R1`/`_R2` or `_1`/`_2` and confirmed by read name)")
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
    return Path(os.path.abspath(os.path.expanduser(value)))


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
            if p is None or not any(_matches(p.columns[n], path) for n in (*p.reads, *p.data_columns)):
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

def _outside(path: Path, avoid: tuple[Path, ...]) -> None:
    real = path.resolve()
    for place in avoid:
        if real.is_relative_to(place.resolve()):
            raise _bad(f"input file {path} is inside the run's {_avoid_label(place, avoid)} "
                       f"({place}); results and task files are not inputs",
                       fix="Pass the data files themselves, kept outside --outdir and the work "
                           "directory.")


def _avoid_label(place: Path, avoid: tuple[Path, ...]) -> str:
    return "--outdir" if place == avoid[0] else "work directory"


def _walk(root: Path, found: dict[str, tuple[Path, Path]], avoid: tuple[Path, ...]) -> None:
    real_root = root.resolve()
    for place in avoid:
        if place.resolve().is_relative_to(real_root):
            raise _bad(f"--input {root} contains the run's {_avoid_label(place, avoid)} ({place}): "
                       "a resumed run would read its own results as samples",
                       fix="Point --input at the directory that holds only the data, or use an "
                           "--outdir outside it.")

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


def discover(source: Source, *, avoid: tuple[Path, ...]) -> list[tuple[Path, Path]]:
    """Every file the source names, as (file, the directory or value it was found under)."""
    found: dict[str, tuple[Path, Path]] = {}
    for text in source.values:
        path = Path(text)
        if path.is_dir():
            _walk(path, found, avoid)
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
            if match.is_dir():
                _walk(match, found, avoid)
            elif match.is_file():
                found.setdefault(str(match), (match, match.parent))
            else:
                raise _bad(f"--input {text}: {match} is not a readable file (a broken link?)",
                           fix="Remove or repair it.")
    for path, _ in found.values():
        _outside(path, avoid)
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


def _first_read_name(path: Path) -> str | None:
    """The name of a FastQ file's first read (None for an empty file)."""
    try:
        opener = gzip.open if path.name.lower().endswith(".gz") else open
        with opener(path, "rb") as fh:
            line = fh.readline(1 << 16)
    except (OSError, EOFError, zlib.error) as exc:
        raise _bad(f"cannot read FastQ file {path}: {exc}",
                   fix="Restore a valid (gzip-compressed if named .gz) FastQ file.") from exc
    if not line:
        return None
    text = line.decode("utf-8", "replace").rstrip("\r\n")
    if not text.startswith("@"):
        raise _bad(f"{path} is not a FastQ file: its first line does not start with '@'",
                   fix="Pass FastQ files (or leave this one out of --input).")
    words = text[1:].split()
    return words[0] if words else ""


def _mates(first: str, second: str) -> bool:
    """Illumina and SRA mates share their read name; older tools suffix it /1 and /2 (or .1/.2)."""
    return first == second or (len(first) == len(second) > 2 and first[:-1] == second[:-1]
                               and first[-2] in "/._" and first[-1] == "1" and second[-1] == "2")


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
                first, second = _first_read_name(slot[1]), _first_read_name(slot[2])
                if first is None or second is None:
                    raise _bad(f"cannot tell whether {slot[1].name} and {slot[2].name} are the two "
                               "reads of one library: an empty file has no read names to compare",
                               fix="Name them _R1/_R2, or write the samplesheet yourself.")
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


def _confirm(first: Path, second: Path, notes: list[str]) -> None:
    a, b = _first_read_name(first), _first_read_name(second)
    if a is None or b is None:
        notes.append(f"Paired {first.name} with {second.name} by name only: an empty file has no "
                     "read names to compare.")
    elif not _mates(a, b):
        raise _bad(f"{first.name} and {second.name} are named as mates, but their first read names "
                   f"differ ({a!r}, {b!r})",
                   fix="Check that the files belong together (a swapped or truncated mate?).")


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
        if column in p.reads and value:
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
    issues = samplesheet._value_issues(0, col, value)
    return [i.split(": ", 1)[1].replace(f"'{col.name}' ", "", 1) if ": " in i else i
            for i in issues]


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
    empty = frozenset(c for c, v in assignments.items() if v == "")
    p = plan(sheet, input_param, empty)
    _check_assignments(assignments, p)
    if p.problem:
        raise _bad(f"nfclaw cannot generate the {pipeline} samplesheet: {p.problem}",
                   fix="Follow the hint above, or write the samplesheet yourself (Inputs in "
                       "skill.md).")
    found = discover(source, avoid=(outdir, work_dir))
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
    samples = sorted({u.sample for u in units} | {s for s, _ in data})
    _check_names(samples, units, data, p, pipeline)
    _check_shapes(samples, units, data)
    rows: list[dict[str, str]] = []
    row_sample: list[tuple[str, int]] = []
    for sample in samples:
        attached = {col: str(path) for (s, col), path in sorted(data.items()) if s == sample}
        mine = sorted((u for u in units if u.sample == sample),
                      key=lambda u: (u.lane or 0, u.chunk or 0, str(u.reads[0])))
        if p.lane_column and mine:
            lanes = [u.lane or 1 for u in mine]
            if len(set(lanes)) != len(lanes):
                raise _bad(f"sample {sample!r} has several read sets for one lane "
                           f"({_shown([u.reads[0].name for u in mine])}); its '{p.lane_column}' "
                           "column could no longer tell them apart",
                           fix="Merge the split files of each lane, or write the samplesheet "
                               "yourself.")
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
    delimiter = "\t" if p.suffix == ".tsv" else ","
    _check_cells(rows, delimiter)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
    writer.writerow(header)
    writer.writerows([[row.get(h, "") for h in header] for row in rows])
    text = buffer.getvalue()
    _validate(text, p.suffix, sheet, pipeline)
    files = tuple(dict.fromkeys(Path(row[c]) for row in rows
                                for c in (*p.reads, *p.data_columns) if row.get(c)))
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


def _check_names(samples: list[str], units: list[_Unit], data: dict, p: Plan,
                 pipeline: str) -> None:
    def origin(sample: str) -> str:
        paths = [str(u.reads[0]) for u in units if u.sample == sample]
        paths += [str(path) for (s, _), path in data.items() if s == sample]
        return Path(paths[0]).name if paths else sample

    issues = []
    for path in [path for u in units for path in u.reads] + list(data.values()):
        issues += [f"{path}: {i}" for i in inputs.local_name_issues(str(path), "file-path")]
    id_col = p.columns.get(p.id_column) if p.id_column else None
    for sample in samples:
        if not samplesheet._safe_identifier(sample):
            issues.append(f"sample name {sample!r} (from {origin(sample)}) must start with a "
                          "letter, digit or underscore and contain only letters, digits, dots, "
                          "underscores or hyphens")
        elif id_col is not None and id_col.pattern and not _search(id_col.pattern, sample):
            issues.append(f"sample name {sample!r} (from {origin(sample)}) does not match the "
                          f"{pipeline} '{id_col.name}' pattern {id_col.pattern}")
    if issues:
        raise _bad("Sample names come from the file names, which these do not allow.",
                   fix="Give the files (or links to them) names that fit; nfclaw never renames "
                       "samples.", issues=issues)


def _check_shapes(samples: list[str], units: list[_Unit], data: dict) -> None:
    shapes: dict[tuple[str, ...], list[str]] = {}
    for sample in samples:
        kinds = (("FastQ reads",) if any(u.sample == sample for u in units) else ()) + tuple(
            sorted(col for (s, col) in data if s == sample))
        shapes.setdefault(kinds, []).append(sample)
    if len(shapes) > 1:
        raise _bad("The samples do not all bring the same kinds of files, which suggests stray "
                   "or missing files.",
                   fix="Pass only the files of the samples to analyse (a narrower directory or a "
                       "glob), or write the samplesheet yourself for mixed inputs.",
                   issues=[f"{', '.join(kinds)}: {_shown(names)}"
                           for kinds, names in shapes.items()])


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


def resume_note(previous: Path, generated: Generated) -> str | None:
    """On --resume: say how the regenerated sheet differs from the one the previous launch used."""
    try:
        before = previous.read_text(encoding="utf-8")
    except OSError:
        return None
    if before == generated.text:
        return None
    note = ("--resume regenerated the samplesheet from --input, and it differs from the one the "
            "previous launch used")
    if generated.id_column:
        delimiter = "\t" if generated.suffix == ".tsv" else ","
        try:
            old = {r.get(generated.id_column) or "" for r in
                   csv.DictReader(io.StringIO(before), delimiter=delimiter)}
        except csv.Error:
            old = set()
        new = {r[generated.id_column] for r in generated.rows}
        changes = [f"{label}: {_shown(sorted(names))}"
                   for label, names in (("added", new - old), ("removed", old - new)) if names]
        note += " (" + ("; ".join(changes) if changes else "same samples, other files or values") + ")"
    return note + ". Nextflow reuses only the tasks whose inputs are unchanged."
