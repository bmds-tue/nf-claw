# librarian/write_skill.py
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from runner import (engine_version, fastqrepair_compat, handoff, inputs, nextflow_command, sheetgen,
                    versions)
from runner import schema as schema_mod
from runner import submodule as submod
from runner.schema import InputSchema, Param, ParamSchema, json_scalar
from runner.submodule import SubmoduleStatus


def _cell(text: object) -> str:
    """Collapse all whitespace (incl. newlines/tabs) and escape pipes so free text is safe inside a markdown table cell."""
    return " ".join(str(text).split()).replace("|", "\\|")


def _reference_description(text: str, ps: ParamSchema) -> str:
    """Keep upstream prose, but do not link to nonexistent parameter-table anchors."""
    def reference(match: re.Match) -> str:
        label, anchor = match.groups()
        if anchor in ps.groups() or anchor == "general":
            return match.group(0)
        name = anchor.removeprefix("--").replace("-", "_")
        missing = name not in ps.params and label.strip("`") == anchor
        return label + (" (not declared in this pinned schema)" if missing else "")
    return _cell(re.sub(r"\[([^\]]+)\]\(#([\w-]+)\)", reference, text))


def _allowed(values: tuple[str, ...] | None) -> str:
    """An allowed-values cell: each value its own code span, so a value that itself contains a comma
    (ampliseq's `bac,arc,mito,euk`) cannot be mistaken for several."""
    return _cell(", ".join(f"`{v}`" for v in values)) if values else ""


# nf-schema's path formats (runner.schema.PATH_FORMATS), as the docs name them. `path` is either a
# file or a directory; `file-path-pattern` is a glob. All four are made absolute by `nfclaw run`.
_PATH_FORMAT_LABELS = {
    "file-path": "file path",
    "directory-path": "directory path",
    "path": "file or directory path",
    "file-path-pattern": "file path glob",
}


def _type_with_fmt(type_: str, fmt: str | None) -> str:
    """Annotate a type with its path-ness — a schema fact (nf-schema's path `format`s)."""
    label = _PATH_FORMAT_LABELS.get(fmt or "")
    return f"{type_} ({label})" if label else type_


def _constraints(obj) -> str:
    """Render the value-shape constraints nf-schema enforces — a literal fact list, no heuristics.
    `enum` is intentionally excluded (it has its own 'allowed values' column). Works for both
    Param and Column since they share these attributes."""
    parts: list[str] = []
    if obj.pattern:
        parts.append(f"matches {obj.pattern}")
    if obj.minimum is not None:
        parts.append(f"≥ {obj.minimum}")
    if obj.maximum is not None:
        parts.append(f"≤ {obj.maximum}")
    if obj.min_length is not None:
        parts.append(f"length ≥ {obj.min_length}")
    if obj.max_length is not None:
        parts.append(f"length ≤ {obj.max_length}")
    if obj.deprecated:
        parts.append("deprecated")
    return _cell("; ".join(parts))


def _input_summary(insch: InputSchema | None, ps: ParamSchema | None = None) -> str:
    """One-line, schema-derived description of what the pipeline consumes (for the catalog).
    Robust: comes straight from the samplesheet schema `--input` uses, never guessed."""
    if insch is None:
        if ps is not None and "input" in ps.params:
            return "--input (no samplesheet schema)"     # a directory, a FASTA, an unschema'd sheet
        return "parameters (no samplesheet)"
    named = [c for c in insch.columns if c.name]
    if not named:
        return "id list (one value per line)"
    return "samplesheet (" + ", ".join(c.name for c in named) + ")"


def _samplesheet_format(ps: ParamSchema | None) -> tuple[str, str, str]:
    """Return (extension, display name, delimiter) for generated samplesheet examples.

    nf-schema chooses the parser from the `--input` filename extension. Some upstream schemas
    require `.tsv` while their prose still says "comma-separated", so prefer the schema pattern
    over descriptions."""
    input_param = ps.params.get("input") if ps else None
    pattern = input_param.pattern if input_param else None
    if pattern and r"\.tsv" in pattern and r"\.csv" not in pattern:
        return "tsv", "TSV", "\t"
    return "csv", "CSV", ","


def _produces_multiqc(upstream: Path) -> bool:
    """Whether the pinned tree contains MultiQC support, which may be skipped at runtime."""
    return ((upstream / "assets" / "multiqc_config.yml").exists()
            or (upstream / "modules" / "nf-core" / "multiqc").is_dir())


def _output_summary(upstream: Path) -> str:
    """Output locations and potential reports, without inferring a guarantee from vendored code.
    The selected workflow and publication settings determine the actual files."""
    parts = ["--outdir/ (configured results)", "pipeline_info/ (run metadata when enabled)"]
    if _produces_multiqc(upstream):
        parts.append("MultiQC report (conditional)")
    return "; ".join(parts)


_TOOL_BULLET = re.compile(r"^\s*[-*+]\s*\[([^\]]+)\]")  # markdown allows -, * or + bullets


def _is_tool_section(header: str) -> bool:
    """Whether a CITATIONS.md `## ` section lists software the pipeline runs. True for the
    `## Pipeline tools` section and any language-specific software section (`## R packages`,
    `## Python`, ...); False for citation-link headers (`## [Name](url)` — the pipeline's own
    paper and the nf-core/Nextflow citations), the packaging/containerisation infra section,
    and test-data/external-archive sections (`## Data`, `## Pipeline resources`)."""
    t = header.strip().lower()
    if t.startswith("["):                            # `## [Name](url)` — paper/framework citation
        return False
    if "packaging" in t or "containeri" in t:        # packaging/containerisation (incl. /testing) — infra
        return False
    if re.search(r"\bdata(bases?|sets?)?\b", t) or "resource" in t:
        return False                                 # test data, reference databases, archives
    if "nextflow" in t or "nf-core" in t:            # the framework itself, cited as plain bullets
        return False
    return True


def _pipeline_tools(upstream: Path) -> list[str]:
    """The software/methods the pipeline runs, taken from the authors' own CITATIONS.md — a
    curated fact, not our invention. Collects the `[Tool](url)` bullets under every software
    section (see `_is_tool_section`), de-duplicated in document order. Empty if the file is
    absent or lists no tools."""
    try:
        text = (upstream / "CITATIONS.md").read_text(encoding="utf-8")
    except OSError:
        return []
    tools: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = _is_tool_section(line[3:])
            continue
        if in_section and (m := _TOOL_BULLET.match(line)):
            nm = m.group(1).strip()
            if nm and nm not in tools:
                tools.append(nm)
    return tools


def _tools_section(name: str, st: SubmoduleStatus, tools: list[str],
                   ref: str | None = None) -> str:
    if not tools:
        return ""
    return (f"The tools/methods this pipeline runs, per the authors' own list: "
            f"{', '.join(tools)}.\n\nFull list with references: "
            f"https://github.com/nf-core/{name}/blob/{ref or st.version}/CITATIONS.md\n")


def _summary(upstream: Path) -> str:
    """The pipeline's own one-paragraph description, taken verbatim from the first prose
    paragraph of the README `## Introduction` section — a far richer selection signal than the
    terse manifest description. Leading non-prose blocks (images, headings, blockquotes, lists)
    are skipped; markdown links are flattened to their text. Returns "" if the section or a prose
    paragraph is absent, so callers fall back to the manifest description — this can only ever add
    signal, never break."""
    try:
        text = (upstream / "README.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(r"^##\s+Introduction\s*$(.*?)(^##\s|\Z)", text, re.M | re.S)
    if not m:
        return ""
    for block in re.split(r"\n\s*\n", m.group(1).strip()):
        s = block.strip()
        if (not s or s[0] in "#>|<" or s.startswith(("![", "- ", "* ", "+ "))
                or re.match(r"^\d+\.\s", s)):
            continue                                       # image/heading/blockquote/list lead-in
        s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)         # inline images
        s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)     # inline links -> text
        s = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", s)    # reference-style links -> text
        s = s.replace("**", "").replace("`", "")
        s = re.sub(r"\s+", " ", s).strip()
        if len(s) >= 40 and s[:1].isalpha():
            return s
    return ""


def _resources_section(name: str, ps: ParamSchema, insch: InputSchema | None,
                       pipeline_version: str | None = None) -> str:
    """How to run this pipeline on a machine smaller than its defaults assume.

    nf-core resource labels commonly assume a server and retry rules can grow their requests.
    A workstation can refuse such a task before it runs. Apply the resourceLimits ceiling
    nf-core documents to every request, rather than resizing individual processes."""
    command, _ = _run_invocation(name, ps, insch, pipeline_version)
    return (
        "Resource requests follow the pipeline's configs and selected profiles. nf-core's "
        "resource labels often assume a server — a single step can request far more memory than a "
        "workstation has, and retry rules can increase requests. If a run fails with "
        "`Process requirement exceeds available memory` (or CPUs), cap every request, and every "
        "retry, at what this machine actually has:\n\n"
        "```bash\n"
        f"{command} \\\n"
        "  --limit-cpus 4 --limit-memory 15.GB\n"
        "```\n\n"
        "nfclaw turns those into Nextflow's `process.resourceLimits` and passes them as a `-c` "
        "config — the mechanism nf-core prescribes for exactly this "
        "([docs](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources)). "
        "Set them to the machine's real capacity. `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes. The generated config is kept in "
        "`<outdir>/provenance/`, so `commands.sh` replays the run under the same ceiling.\n"
    )


_GENOME_KEY = re.compile(r"""^\s*(['"])(?P<key>[^'"]+)\1\s*(?:\{|:\s*\[)\s*$""")
_GENOME_FASTA = re.compile(r"""^\s*fasta\s*(?:=|:)\s*(['"])(?P<value>[^'"]+)\1""")


def _configured_fasta(upstream: Path, key: str) -> str | None:
    """The `fasta` the pinned configuration assigns to genome `key`, as written — only when every
    `'<key>' { … }` block (or `'<key>' : [ … ]` map) in the release's config files assigns the
    same one. A key's name need not be the assembly it selects (marsseq's `mm10` is GRCm39)."""
    values: set[str] = set()
    for path in [upstream / "nextflow.config", *sorted((upstream / "conf").glob("*.config"))]:
        try:
            lines = [schema_mod._strip_comment(line)
                     for line in path.read_text(encoding="utf-8").splitlines()]
        except (OSError, UnicodeDecodeError):
            continue
        for start, line in enumerate(lines):
            if not ((m := _GENOME_KEY.match(line)) and m["key"] == key):
                continue
            depth = 0
            for text in lines[start:]:
                depth += text.count("{") + text.count("[") - text.count("}") - text.count("]")
                if fasta := _GENOME_FASTA.match(text):
                    values.add(fasta["value"])
                if depth <= 0:
                    break
    return values.pop() if len(values) == 1 else None


def _reference_section(ps: ParamSchema, upstream: Path | None = None) -> str:
    """Name only reference sources the schema actually declares.

    A `genome` key does not identify a provider: some pipelines use local custom references
    (marsseq's ERCC references), and an iGenomes base can itself be local or use a custom host.
    When the source cannot be established here, point to the pinned configuration instead."""
    genome = ps.params.get("genome")
    if genome is None:              # no --genome: nothing is resolved through iGenomes by name
        return ""
    base = ps.params.get("igenomes_base")
    source = str(base.default) if base is not None and base.default else ""
    ignored = ps.params.get("igenomes_ignore")
    ignore = " Set `--igenomes-ignore true` to disable the lookup entirely." if ignored else ""
    # Name only flags and groups this schema has: the reference options live in different groups
    # across releases (reference_genome_options, reference_data_options, reference_file_options, …),
    # and not every release takes a --fasta.
    fasta = ps.params.get("fasta")
    group = f"`{(fasta or genome).group or 'general'}`"
    own = (f"e.g. `--fasta`; the {group} group in [reference.md](reference.md) lists every "
           "reference option" if fasta else
           f"the {group} group in [reference.md](reference.md) lists the reference options")
    selected = (f"`--genome` defaults to `{genome.default}`. " if genome.default else
                "No reference genome is set by default: supply your own reference. ")
    configured = (_configured_fasta(upstream, str(genome.default))
                  if upstream is not None and genome.default else None)
    if configured:
        selected += (f"The pinned configuration gives `--genome {genome.default}` the FASTA "
                     f"`{configured}`; a genome key's name need not be the assembly it selects, so "
                     "confirm it is the one you intend. ")
    config_note = ("Confirm the selected reference's paths and source in the pinned "
                   "`upstream/nextflow.config` and `upstream/conf/` before running.")
    if ignored is not None and ignored.default is True:
        return (f"{selected}The iGenomes lookup is disabled by default "
                "(`--igenomes-ignore true`). Configure your reference explicitly "
                f"({own}). {config_note}\n")
    if not source:
        return (f"{selected}A genome name alone does not specify where reference files come from. "
                f"{config_note} To supply your own reference, use {own}.{ignore}\n")
    remote = bool(re.match(r"^(?:https?|s3|gs|ftp)://", source, re.I))
    provider = "AWS iGenomes" if source.startswith("s3://ngi-igenomes/") else "iGenomes"
    if genome.default and remote:
        fasta_note = (f" The pinned configuration gives that key the FASTA `{configured}`."
                      if configured else "")
        return (
            f"**This release resolves a reference genome remotely by default.** `--genome` defaults "
            f"to `{genome.default}`; the schema declares {provider} at `{source}`.{fasta_note} "
            "Resolving references through that default needs access to this source. For a "
            f"self-contained run, pass your own reference instead ({own}).{ignore} {config_note}\n"
        )
    return (
        f"{selected}The schema declares {provider} at `{source}`; selecting `--genome <id>` uses "
        f"the paths in the pipeline's reference configuration. "
        + ("Access to that remote source is required. " if remote else "")
        + f"To supply your own reference, use {own}.{ignore} {config_note}\n"
    )


def _engine_section(name: str, st: SubmoduleStatus, what: str = "release",
                    repo_up: str = "../..", ps: ParamSchema | None = None) -> str:
    """The Nextflow version this release declares, and how to run exactly that one.

    The engine is not a neutral detail: a release is written against the Nextflow line it declares,
    and a newer *major* changes the config parser. Running nf-core/scrnaseq 4.2.0 (which declares
    `!>=25.10.4`) on Nextflow 26.04.6 adds `Unrecognized config option 'validation.*'` warnings that
    the same run on 25.10.4 does not produce — verified by running both. The declared version is a
    fact in the pinned manifest, so it is surfaced here with the flag that pins it. `what` names
    the tree in the prose: a `release`, or the `commit` of unreleased `dev` code. `repo_up` is the
    relative path from where the skill.md is written back to the repository root."""
    spec = engine_version.required_spec(st.path / "nextflow.config")
    if not spec:
        return ""
    pin = engine_version.minimum_version(spec)
    pin_line = ""
    if pin:
        pin_line = (f"\n\nTo pin this {what}'s declared minimum engine — useful when a newer "
                    "Nextflow has incompatible config parsing:\n```bash\n"
                    f"nfclaw run {name} ... --nxf-ver {pin}\n```\n"
                    "`--nxf-ver` is recorded in `<outdir>/provenance/`, so the replay uses the same "
                    f"engine. See [known-issues]({repo_up}/docs/known-issues.md).")
        if not engine_version.supports_resource_limits(pin):
            # The Resources section's --limit-* ceiling is process.resourceLimits, which an engine
            # this old ignores without a word; nfclaw refuses the combination.
            own = [f"`--{p.replace('_', '-')}`" for p in ("max_cpus", "max_memory", "max_time")
                   if ps is not None and p in ps.params]
            pin_line += (f"\n\nNextflow {pin} predates `process.resourceLimits` (24.04.0), so "
                         "`--limit-*` cannot be combined with this pin — nfclaw refuses it rather "
                         "than run without the ceiling"
                         + (f"; cap resources with the {what}'s own " + ", ".join(own) + " instead."
                            if own else "."))
    return f"This {what} declares `nextflowVersion = '{spec}'`.{pin_line}\n"


def _outputs_section(name: str, st: SubmoduleStatus, ref: str | None = None,
                     what: str = "release", ps: ParamSchema | None = None) -> str:
    mq = ""
    if _produces_multiqc(st.path):
        mq = (" The pinned tree includes MultiQC support; a report is produced only when its "
              "workflow step runs.")
        if ps is not None and "skip_multiqc" in ps.params:
            mq += " `--skip-multiqc true` disables that report."
    link = ""
    if (st.path / "docs" / "output.md").exists():
        link = (f"\n\nThe exact output files and directory layout for this {what} are documented "
                f"upstream: https://github.com/nf-core/{name}/blob/{ref or st.version}/docs/output.md")
    return (
        "Results land in `--outdir`; the files and directory layout depend on the selected "
        "workflow, parameters and publication settings. Run metadata is normally placed in "
        "`<outdir>/pipeline_info/` (execution report, software versions), when those outputs "
        f"are enabled.{mq} `nfclaw run` also writes `<outdir>/provenance/` with the exact params "
        "file and the run log, `<outdir>/provenance/logs/run.log` — the whole launch, whose last "
        "line states the outcome (Nextflow's own log is `<outdir>/.nextflow.log`); unless "
        "`--no-provenance` it adds a run manifest (pinned version, commit and exact command), "
        f"input/output SHA-256 checksums, and a replayable `commands.sh`.{link}\n\n"
        "Check a run — in the foreground or the background — with `nfclaw status <outdir>`: "
        "success, still running, how it ended (with the error), or stopped without an outcome; "
        "exit 0 success, 3 running, 1 otherwise.\n"
    )


def _inputs_section(insch: InputSchema | None, ps: ParamSchema | None = None) -> str:
    """The samplesheet (or other input) a run takes and, when nfclaw can write that samplesheet
    from the data files themselves, what it fills and what the caller must set (runner.sheetgen —
    the same decision `nfclaw run` takes, so the docs and the run cannot disagree)."""
    text = _sheet_section(insch, ps)
    generated = (sheetgen.describe(insch, ps.params.get("input") if ps else None)
                 if insch is not None else "")
    return text + (f"\n{generated}" if generated else "")


def _sheet_section(insch: InputSchema | None, ps: ParamSchema | None = None) -> str:
    if insch is None:
        inp = ps.params.get("input") if ps else None
        if inp is None or not inp.description.strip():
            return "This pipeline does not use a samplesheet; configure inputs via parameters.\n"
        # State only what the release publishes: rangeland's --input is a directory or tarball, but
        # bactmap's and seqsubmit's are samplesheets that simply ship without a schema.
        desc = _cell(inp.description).rstrip(".")
        return (f"This release publishes no samplesheet schema for `--input`, so nfclaw does not "
                f"pre-check its contents. The parameter reads: {desc}. Configure the other inputs "
                "via parameters (see [reference.md](reference.md)).\n")
    named = [c for c in insch.columns if c.name]
    if not named:
        # A single unnamed column (e.g. nf-core/fetchngs id list): one value per line, no header.
        c = insch.columns[0] if insch.columns else None
        constraint = f" Each value must match the pattern `{c.pattern}`." if c and c.pattern else ""
        return "Input is a plain text file with one value per line (no header)." + constraint + "\n"
    head = "| column | type | required | allowed values | constraints |\n|---|---|---|---|---|\n"
    rows = ""
    for c in named:
        typ = _type_with_fmt(c.type, c.fmt)
        rows += (f"| `{c.name}` | {typ} | {'yes' if c.required else 'no'} | "
                 f"{_allowed(c.enum)} | {_constraints(c)} |\n")
    ext, label, delimiter = _samplesheet_format(ps)
    input_note = _input_pattern_note(ps)
    tabular_intro = _tabular_intro(label, ps)
    if insch.one_of:
        # Mutually-exclusive column groups (items.oneOf): there is no single canonical header, so
        # list each allowed group and show one valid header per group (always-required columns +
        # that group). Surfacing this is exactly the signal an agent needs not to fill, say, both
        # `bam` and `cram`, or to mix ampliseq's legacy and standardized columns.
        base = [c.name for c in named if c.required]               # always-required columns
        groups = "\n".join("- " + ", ".join(f"`{col}`" for col in grp) for grp in insch.one_of)
        headers = "".join(
            f"```{ext}\n{delimiter.join(dict.fromkeys(base + list(grp)))}\n```\n"
            for grp in insch.one_of)
        return (f"{head}{rows}\n"
                f"{input_note}"
                f"The samplesheet is a {label}. Each row must include **exactly one** of these "
                "mutually-exclusive column groups (providing columns from more than one group "
                f"fails validation):\n{groups}\n\n"
                f"{_dependent_rules_section(insch)}"
                "Fill each value per the table above and `reference.md`. Valid headers — pick the "
                f"group that matches your data (optional columns from the table may be added):\n{headers}")
    # The header lists the columns the schema *requires*, not every column it allows. A pipeline can
    # declare optional columns that only apply to one aligner/mode (scrnaseq's `sample_type` and
    # `feature_type` are cellranger-arc/multi only), and emitting them all produces a header whose
    # extra fields an agent then has to fill or blank out. The required set is the one header that
    # is always valid; the optional columns are named right below it, so nothing is hidden.
    required_cols = [c.name for c in named if c.required]
    optional_cols = [c.name for c in named if not c.required]
    header_cols = list(insch.header_prefix) or required_cols or [c.name for c in named]
    optional_cols = [name for name in optional_cols if name not in header_cols]
    header_line = delimiter.join(header_cols)
    optional_note = ""
    if required_cols and optional_cols:
        cols = ", ".join(f"`{c}`" for c in optional_cols)
        optional_note = ("\nAny of the optional columns above may be appended to the header when "
                         f"your data needs them: {cols}.\n")
    required_note = (" (the required header order; optional values may be empty)" if insch.header_prefix
                     else " (the columns the schema requires)" if required_cols else "")
    return (f"{insch.audit_note}\n\n" if insch.audit_note else "") + (f"{head}{rows}\n"
            f"{input_note}"
            f"{_dependent_rules_section(insch)}"
            f"{tabular_intro}{required_note}; fill each value per the table above "
            f"and `reference.md` (no example value is invented here):\n```{ext}\n{header_line}\n```\n"
            f"{optional_note}")


def _input_pattern_note(ps: ParamSchema | None) -> str:
    input_param = ps.params.get("input") if ps else None
    if input_param and input_param.pattern:
        return f"`--input` must match `{input_param.pattern}`.\n\n"
    return ""


def _tabular_intro(label: str, ps: ParamSchema | None) -> str:
    input_param = ps.params.get("input") if ps else None
    pattern = input_param.pattern if input_param else ""
    if pattern and "csv" in pattern and "tsv" in pattern:
        return "For tabular CSV/TSV input, use this header"
    return f"The samplesheet is a {label} with this header"


def _dependent_rules_section(insch: InputSchema) -> str:
    lines: list[str] = []
    for trigger, required in insch.dependent_required:
        reqs = ", ".join(f"`{req}`" for req in required)
        lines.append(f"- When `{trigger}` is set, also provide {reqs}.")
    options: list[str] = []
    for branch in insch.any_of_dependent_required:
        parts: list[str] = []
        for trigger, required in branch:
            reqs = ", ".join(f"`{req}`" for req in required)
            parts.append(f"{reqs} when `{trigger}` is set")
        options.append(" and ".join(parts))
    if options:
        lines.append(
            "- At least one of these conditional requirements must be satisfied: "
            + "; ".join(options)
            + "."
        )
    if not lines:
        return ""
    return "Additional row validation rules from the schema:\n" + "\n".join(lines) + "\n\n"


def _param_table(params: list[Param]) -> str:
    out = ("| parameter | type | default | allowed values | constraints | description |\n"
           "|---|---|---|---|---|---|\n")
    for p in params:
        default = "" if p.default is None else json_scalar(p.default)
        out += (f"| `--{p.name.replace('_', '-')}` | {_type_with_fmt(p.type, p.fmt)} | "
                f"{_cell(default)} | {_allowed(p.enum)} | {_constraints(p)} | "
                f"{_cell(p.description)} |\n")
    return out


def _required_params(ps: ParamSchema) -> str:
    """Only the parameters the schema itself marks required — a fact, not a heuristic guess."""
    required = [p for p in ps.params.values() if p.required]
    if not required:
        return ("_The schema marks no parameter required; the pipeline runs with defaults. "
                "See reference.md to customise._\n")
    return _param_table(required)


def _is_mandatory_group(title: str) -> bool:
    """Whether a schema group is the authors' own 'these must be set' group.

    nf-core schemas mark required-ness in two independent places, and they do not always agree: the
    JSON-schema `required` list (what nf-schema enforces) and the group *title*. A parameter that
    carries a default is never in `required` — nf-schema has a value, so it cannot fail — yet the
    authors may still group it under "Mandatory arguments" because the pipeline itself rejects the
    default. nf-core/scrnaseq's `--protocol` is exactly that: it defaults to `auto`, and the
    workflow aborts on `auto` for every aligner but cellranger. Reading only `required` therefore
    understates the interface, so the group title is surfaced too."""
    t = title.strip().lower()
    return "mandator" in t or t.startswith("required")


def _mandatory_params(ps: ParamSchema) -> str:
    """Parameters the schema groups as mandatory but does not list in `required` (see above)."""
    params = [p for p in ps.params.values()
              if _is_mandatory_group(p.group_title) and not p.required]
    if not params:
        return ""
    return (
        "The schema groups these under **Mandatory arguments** — the pipeline authors' own label. "
        "They are absent from the `required` list above only because each carries a default, so "
        "nf-schema will not stop a run that omits them — but the pipeline itself can reject the "
        "default at runtime. Set them deliberately.\n\n"
        + _param_table(sorted(params, key=lambda p: p.name))
    )


def _param_groups(ps: ParamSchema) -> str:
    """The schema's own parameter groups (titles + full counts) — a deterministic map, no curation."""
    groups = sorted(ps.groups().items())
    if not groups:
        return "_No additional parameters._\n"
    lines = []
    for g, params in groups:
        title = next((p.group_title for p in params if p.group_title), "")
        label = f"**{title}** (`{g or 'general'}`)" if title else f"`{g or 'general'}`"
        lines.append(f"- {label} — {len(params)} parameter{'' if len(params) == 1 else 's'}")
    return ("Every parameter not listed above is optional as far as the schema is concerned. "
            "[reference.md](reference.md) documents them all — type, default, allowed values and "
            "constraints — organised into these groups (counts are full group sizes, so they "
            "include any parameter already listed above):\n" + "\n".join(lines) + "\n")


def _input_arg(ps: ParamSchema, insch: InputSchema | None) -> str:
    """The example commands' `--input`: a samplesheet file when the pipeline takes one, else a
    placeholder when the schema requires `--input` with no default (e.g. rangeland's imagery
    directory), else nothing."""
    if insch is not None:
        ext, _, _ = _samplesheet_format(ps)
        return f" --input samplesheet.{ext}"
    inp = ps.params.get("input")
    return " --input <input>" if inp is not None and inp.required and inp.default is None else ""


def _run_invocation(name: str, ps: ParamSchema, insch: InputSchema | None,
                    pipeline_version: str | None = None,
                    tree: str | None = None) -> tuple[str, str]:
    """The (nfclaw, raw nextflow) example commands. `--input` comes from `_input_arg`, and every
    schema-required param beyond input/outdir that has NO default
    is shown as an explicit `<placeholder>` (defaults remain subject to the pipeline's config
    and runtime validation). When rendering a non-pinned version, the nfclaw
    command carries `--pipeline-version <tag>` and the raw command targets that version's tree
    (`tree` names its cache directory when that differs from the tag, as for a `dev` commit)."""
    inp = _input_arg(ps, insch)
    required = [p for p in ps.params.values()
                if p.required and p.name not in ("input", "outdir") and p.default is None]
    extra = "".join(f" --{p.name.replace('_', '-')} <{p.name}>" for p in required)
    raw_extra = "".join(f" --{p.name} <{p.name}>" for p in required)
    ver = f" --pipeline-version {pipeline_version}" if pipeline_version else ""
    upstream = (f"pipelines/{name}/.versions/{tree or pipeline_version}/upstream"
                if pipeline_version else f"pipelines/{name}/upstream")
    nfclaw = f"nfclaw run {name}{inp} --outdir results{extra}{ver} -profile docker"
    raw = f"nextflow run {upstream} -profile docker{inp} --outdir results{raw_extra}"
    return nfclaw, raw


def _chaining_section(name: str, rules) -> str:
    """Which pipelines this one hands its outputs to, and which hand theirs to it (handoffs/)."""
    feeds = sorted(d for (u, d) in rules if u == name)
    fed_by = sorted(u for (u, d) in rules if d == name)
    if not feeds and not fed_by:
        return ""
    lines = [f"Run {name} as one stage of a chain: `nfclaw chain run spec.json --outdir DIR` starts "
             "each stage only after the one before it succeeded, and prepares its inputs from that "
             "stage's outputs. The rules live in `handoffs/` (format and spec in "
             "[docs/chaining.md](../../docs/chaining.md)); list them with "
             f"`nfclaw chain edges {name}`."]
    if feeds:
        lines += ["", "Feeds into:"] + [f"- `{d}` — {rules[(name, d)].description}" for d in feeds]
    if fed_by:
        lines += ["", "Fed by:"] + [f"- `{u}` — {rules[(u, name)].description}" for u in fed_by]
    return "\n".join(lines) + "\n"


def _render_skill(name: str, st: SubmoduleStatus, ps: ParamSchema,
                  insch: InputSchema | None, pipeline_version: str | None = None,
                  rules=None) -> str:
    desc = (ps.description.splitlines() or [name])[0]
    summary = _summary(st.path) or desc
    tools = _pipeline_tools(st.path)
    # Chaining is documented for the pinned release, the version the handoff rules are checked
    # against; a version's on-demand docs leave it out.
    rules = rules if pipeline_version is None and rules else {}
    feeds = sorted(d for (u, d) in rules if u == name)
    fm = (
        "---\n"
        f"name: {name}\n"
        f"pipeline: nf-core/{name}\n"
        f"version: {st.version}\n"
        f"commit: {st.commit}\n"
        f"description: {desc}\n"
        f"summary: {summary}\n"
        f"has_samplesheet: {str(insch is not None).lower()}\n"
        f"input: {_input_summary(insch, ps)}\n"
        f"output: {_output_summary(st.path)}\n"
        f"tools: {json.dumps(tools, ensure_ascii=False)}\n"
        + (f"feeds: {json.dumps(feeds)}\n" if feeds else "")
        + "---\n"
    )
    # Unreleased `dev` code is identified by its commit, never by the moving branch name: the docs
    # link to that commit's files and the raw command runs that commit's materialized tree.
    dev = versions.is_dev_request(pipeline_version)
    if dev:
        pipeline_version = versions.DEV_BRANCH                # one spelling in every command shown
    ref = st.commit if dev else st.version
    what = "commit" if dev else "release"
    tree = versions.dev_label(st.commit) if dev else pipeline_version
    tools_md = _tools_section(name, st, tools, ref)
    tools_block = f"## Tools this pipeline runs\n{tools_md}\n" if tools_md else ""
    # A test profile that runs every task as a stub (`stubRun = true`) computes nothing: say so where
    # --demo is offered, so a successful demo is not read as analysis results.
    demo_note = ("This release's `test` profile sets `stubRun = true`: the demo runs every task's stub "
                 "block, which writes placeholder files instead of running its tool. It checks the "
                 "workflow's wiring and publication, not its analysis, and its outputs hold no "
                 "results; `nfclaw status` reports the success with a `stub run:` caveat.\n\n"
                 if nextflow_command.stub_profiles(st.path, "test") else "")
    nfclaw_cmd, raw_cmd = _run_invocation(name, ps, insch, pipeline_version, tree)
    if dev:
        first_line = (f"# nfclaw resolves nf-core/{name}'s {pipeline_version} branch to its current head "
                      f"on every run (these docs: commit {st.commit[:12]}); the default (no "
                      "--pipeline-version) is the latest release.")
        raw_comment = (f"# raw equivalent (runs the materialized {pipeline_version} commit "
                       f"{st.commit[:12]} directly):")
        demo_line = (f"nfclaw run {name} --demo --outdir results --pipeline-version {pipeline_version}"
                     "   # adds the upstream test profile (-profile test,docker)")
        version_note = (f"**Unreleased development code.** These docs describe nf-core/{name}'s "
                        f"`{pipeline_version}` branch at commit `{st.commit}` — code that has not been "
                        "released. The branch moves: every `--pipeline-version "
                        f"{pipeline_version}` run resolves its head afresh, so two runs can execute "
                        "different code, and a parameter documented here can change or disappear. "
                        "Each run records the commit it executed in "
                        "`<outdir>/provenance/run_manifest.json`, and `commands.sh` replays exactly "
                        f"that commit. Prefer a release (`nfclaw versions {name}`) unless you need "
                        "changes that are not in one yet.\n\n")
    elif pipeline_version:
        first_line = (f"# nfclaw fetches and materializes nf-core/{name}@{pipeline_version} "
                      "on first use; the default (no --pipeline-version) is the latest release.")
        raw_comment = f"# raw equivalent (runs the materialized {pipeline_version} tree directly):"
        demo_line = (f"nfclaw run {name} --demo --outdir results --pipeline-version {pipeline_version}"
                     "   # adds the upstream test profile (-profile test,docker)")
        version_note = ""                                     # the Run-it comment already explains the default
    else:
        first_line = f"git submodule update --init pipelines/{name}/upstream   # first time only"
        raw_comment = "# raw equivalent (the submodule is already pinned to this release, so no -r is needed):"
        demo_line = (f"nfclaw run {name} --demo --outdir results"
                     "   # adds the upstream test profile (-profile test,docker)")
        version_note = (f"This is the pinned latest release. To run a different one, list the available "
                        f"releases with `nfclaw versions {name}` and add `--pipeline-version X.Y.Z` to the "
                        f"command above (`nfclaw show {name} --pipeline-version X.Y.Z` prints that release's "
                        "docs). To run unreleased development code instead, add `--pipeline-version "
                        f"{versions.DEV_BRANCH}`: nfclaw resolves nf-core's `{versions.DEV_BRANCH}` "
                        "branch to its current head commit at run time and records that commit in "
                        f"provenance (`nfclaw show {name} --pipeline-version {versions.DEV_BRANCH}` "
                        "prints the docs generated from it). Use it only for changes not yet "
                        "released.\n\n")
    if name == "fastqrepair" and st.commit == fastqrepair_compat.SUPPORTED_COMMIT:
        raw_comment = "# direct upstream execution (omits nfclaw's recorded runtime corrections):"
        version_note += (
            "**Runtime corrections.** For this exact commit, `nfclaw run` splits FASTQ only "
            "where wiping the chunks equals wiping the whole file, sums the repair reports "
            "exactly, preserves the samplesheet's mate order, passes the declared quality offset to BBMap, and publishes singleton "
            "reads, repair logs and mate reports separately. The pinned "
            "source remains unchanged; the generated task corrections and complete splitter "
            "are recorded in `provenance/fastqrepair_compat.config` and reused by replay. "
            "The direct Nextflow command above omits these corrections and can lose valid "
            "reads, swap unsuffixed mates, or overwrite output. Use `nfclaw run` for this release. "
            "Provide one row per sample, distinct staged mate filenames and matching compression "
            "formats. Without a local samplesheet, every gathered read must consistently identify "
            "its mate; ambiguous identity is refused. Paired runs that skip BBMap require a local "
            "samplesheet and publish both mates separately.\n\n"
            "**Quality encoding.** The native quality-offset control validates Phred+64 "
            "input converted to Phred+33 by BBMap. Historical Solexa log-odds quality "
            "scores require a separate score conversion before use; changing the ASCII "
            "offset alone is insufficient. See [Cock et al. (2010)]"
            "(https://doi.org/10.1093/nar/gkp1137) for the encoding and score definitions.\n\n"
        )
    reference = _reference_section(ps, st.path)
    reference_block = f"## Reference genome\n{reference}\n" if reference else ""
    # The committed skill.md is pipelines/<name>/skill.md; a version's docs are written beside its
    # tree, pipelines/<name>/.versions/<label>/skill.md, so their links climb two levels further.
    engine = _engine_section(name, st, what, "../.." if pipeline_version is None else "../../../..",
                             ps)
    engine_block = f"## Nextflow engine\n{engine}\n" if engine else ""
    chaining = _chaining_section(name, rules)
    chaining_block = f"## Chaining\n{chaining}\n" if chaining else ""
    mandatory = _mandatory_params(ps)
    mandatory_block = f"## Mandatory arguments\n{mandatory}\n" if mandatory else ""
    body = (
        f"# {name}\n\n{summary}\n\n"
        "## Run it\n```bash\n"
        f"{first_line}\n"
        f"{nfclaw_cmd}\n"
        f"{raw_comment}\n"
        f"{raw_cmd}\n```\n\n"
        f"{version_note}"
        f"## Inputs\n{_inputs_section(insch, ps)}\n"
        f"## Required parameters\n{_required_params(ps)}\n"
        f"{mandatory_block}"
        f"{reference_block}"
        f"## Other parameters\n{_param_groups(ps)}\n"
        f"## Resources\n{_resources_section(name, ps, insch, pipeline_version)}\n"
        f"{engine_block}"
        f"## Outputs\n{_outputs_section(name, st, ref, what, ps=ps)}\n"
        f"{chaining_block}"
        f"{tools_block}"
        "## Demo\n```bash\n"
        f"{demo_line}\n```\n\n"
        f"{demo_note}"
        "## Full reference\n"
        "Every parameter — name, type, required, hidden, allowed values, constraints, default and "
        "description — is in [reference.md](reference.md). Use it as the source of truth; do not guess flags. "
        "nfclaw checks explicit parameters before launch; the pinned pipeline's validation "
        "handles conditional and complex constraints at runtime. The reference uses nfclaw's "
        "hyphenated flags; raw Nextflow requires the exact schema spelling (usually underscores). "
        "Upstream usage: "
        f"https://github.com/nf-core/{name}/blob/{ref}/docs/usage.md\n\n"
        f"<!-- Generated from nf-core/{name}@{st.commit}. Do not edit by hand. -->\n"
    )
    return fm + body


def _render_reference(name: str, st: SubmoduleStatus, ps: ParamSchema,
                      insch: InputSchema | None) -> str:
    out = (f"---\nname: {name}\nversion: {st.version}\ncommit: {st.commit}\n---\n\n"
           f"# {name} — full parameter reference\n\n"
           f"{ps.title}. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's "
           "hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). "
           "`hidden` marks parameters hidden from upstream's normal help output; "
           "`constraints` lists each parameter's declared value bounds (pattern, min/max, length) — "
           "conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned "
           "pipeline's runtime validation.\n\n")
    for group, params in sorted(ps.groups().items()):
        out += f"## {group or 'general'}\n\n"
        out += ("| parameter | type | required | hidden | allowed values | constraints | "
                "default | description |\n|---|---|---|---|---|---|---|---|\n")
        for p in sorted(params, key=lambda x: x.name):
            default = "" if p.default is None else json_scalar(p.default)
            req = "yes" if p.required else ""
            hid = "yes" if p.hidden else ""
            out += (f"| `--{p.name.replace('_', '-')}` | {_type_with_fmt(p.type, p.fmt)} | "
                    f"{req} | {hid} | {_allowed(p.enum)} | {_constraints(p)} | "
                    f"{_cell(default)} | {_reference_description(p.description, ps)} |\n")
        out += "\n"
    out += f"<!-- Generated from nf-core/{name}@{st.commit}. Do not edit by hand. -->\n"
    return out


def render_status(st: SubmoduleStatus, *, pipeline_version: str | None = None,
                  rules=None) -> tuple[str, str]:
    """Return the (skill.md, reference.md) text for an already-resolved tree — works for the
    pinned submodule and for any materialized version worktree alike. Nothing is written.
    `pipeline_version` makes the skill's run commands target that specific release; leave it
    None for the pinned default so the committed docs stay byte-stable."""
    ps = schema_mod.load_param_schema(st.path)
    # The samplesheet `--input` is actually validated against — the same rule the runner applies
    # (runner/inputs.py). A release can ship assets/schema_input.json without using it: with no
    # `input` parameter at all (drugresponseeval), or with an `--input` that is a directory or
    # tarball (rangeland). Documenting that template as the input sent agents the wrong way.
    ref = inputs.samplesheet_schema(st.path)
    samplesheet = schema_mod.load_input_schema(st.path, ref) if ref else None
    return (_render_skill(st.name, st, ps, samplesheet, pipeline_version, rules),
            _render_reference(st.name, st, ps, samplesheet))


def render(name: str, *, pipelines_dir: Path) -> tuple[str, str]:
    """Return the (skill.md, reference.md) text for a pipeline WITHOUT writing anything, so the
    drift gate can compare against the committed files without mutating them."""
    return render_status(submod.resolve(name, pipelines_dir),
                         rules=handoff.load_registry(pipelines_dir.parent))


def generate(name: str, *, pipelines_dir: Path) -> tuple[Path, Path]:
    skill_text, ref_text = render(name, pipelines_dir=pipelines_dir)
    skill_path = pipelines_dir / name / "skill.md"
    ref_path = pipelines_dir / name / "reference.md"
    skill_path.write_text(skill_text, encoding="utf-8")
    ref_path.write_text(ref_text, encoding="utf-8")
    return skill_path, ref_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="librarian.write_skill")
    parser.add_argument("name", nargs="?")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--pipelines-dir", default="pipelines")
    args = parser.parse_args(argv)
    if not args.all and not args.name:
        parser.error("pass a pipeline name or --all")
    pdir = Path(args.pipelines_dir)
    names = ([d.name for d in sorted(pdir.iterdir()) if d.is_dir()]
             if args.all else [args.name])
    for n in names:
        skill, ref = generate(n, pipelines_dir=pdir)
        print(f"wrote {skill} and {ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
