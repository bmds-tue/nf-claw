import shutil
from pathlib import Path

from librarian import write_skill
from runner import fastqrepair_compat, versions
from runner.schema import Param, ParamSchema
from runner.submodule import SubmoduleStatus

FIX = Path(__file__).parent / "fixtures"


def test_raw_command_preserves_upstream_parameter_spelling():
    ps = ParamSchema("p", "", {
        "input_format": Param("input_format", "string", None, None, "", None, True, "g"),
        "db_name": Param("db_name", "string", None, None, "", None, True, "g"),
    })
    wrapped, raw = write_skill._run_invocation("p", ps, None)
    assert "--input-format <input_format>" in wrapped
    assert "--db-name <db_name>" in wrapped
    assert "--input_format <input_format>" in raw
    assert "--db_name <db_name>" in raw
    assert "--input-format" not in raw and "--db-name" not in raw


def test_reference_description_distinguishes_missing_parameters_from_groups():
    ps = ParamSchema("p", "", {
        "existing_param": Param("existing_param", "string", None, None, "", None, False, "options"),
    })
    description = "See [`missing_param`](#missing_param), [`existing_param`](#existing_param) and [options](#options)."
    text = write_skill._reference_description(description, ps)
    assert "`missing_param` (not declared in this pinned schema)" in text
    assert "`existing_param`" in text and "#existing_param" not in text
    assert "[options](#options)" in text


def test_resource_example_retains_required_pipeline_arguments():
    ps = ParamSchema("p", "", {
        "input_format": Param("input_format", "string", None, None, "", None, True, "g"),
    })
    text = write_skill._resources_section("p", ps, None, "1.2.0")
    assert "--input-format <input_format>" in text
    assert "--pipeline-version 1.2.0" in text
    assert "--limit-cpus 4 --limit-memory 15.GB" in text


def test_affected_fastqrepair_docs_distinguish_corrected_runs_from_direct_source(tmp_path):
    pdir = _seed(tmp_path, "mini")
    st = SubmoduleStatus("fastqrepair", pdir / "mini" / "upstream", True, True,
                         "1.1.1", fastqrepair_compat.SUPPORTED_COMMIT, ())
    for version in (None, "1.1.1", "dev"):
        text, _ = write_skill.render_status(st, pipeline_version=version)
        assert "# raw equivalent" not in text
        assert "can lose valid reads" in text
        assert "provenance/fastqrepair_compat.config" in text
    other = SubmoduleStatus("fastqrepair", st.path, True, True, "1.2.0", "different", ())
    text, _ = write_skill.render_status(other)
    assert "**Runtime corrections.**" not in text


def _seed(tmp_path, name):
    up = tmp_path / name / "upstream"
    up.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config"):
        (up / f).write_text("x")
    shutil.copy(FIX / name / "nextflow_schema.json", up / "nextflow_schema.json")
    src_in = FIX / name / "assets" / "schema_input.json"
    if src_in.exists():
        (up / "assets").mkdir(exist_ok=True)
        shutil.copy(src_in, up / "assets" / "schema_input.json")
    return tmp_path


def test_skill_md_has_fixed_sections(tmp_path):
    pdir = _seed(tmp_path, "mini")
    skill, ref = write_skill.generate("mini", pipelines_dir=pdir)
    text = skill.read_text()
    for header in ("# mini", "## Run it", "## Inputs", "## Required parameters",
                   "## Other parameters", "## Outputs", "## Demo", "## Full reference"):
        assert header in text
    assert "Do not edit by hand" in text


def test_render_status_uses_status_path_and_version(tmp_path):
    # render_status renders from an explicit status (any version's tree), reusing the same logic.
    up = tmp_path / "anytree" / "upstream"
    up.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config"):
        (up / f).write_text("x")
    shutil.copy(FIX / "mini" / "nextflow_schema.json", up / "nextflow_schema.json")
    st = SubmoduleStatus("mini", up, True, True, "1.2.0", "deadbeef", ())
    skill, ref = write_skill.render_status(st)
    assert "version: 1.2.0" in skill and "commit: deadbeef" in skill
    assert "# mini" in skill and "mini" in ref


def test_versioned_render_threads_pipeline_version_into_commands(tmp_path):
    # A version-specific skill.md must tell the agent to run THAT version, and its raw
    # equivalent must point at the materialized version tree — not the pinned default.
    up = tmp_path / "anytree" / "upstream"
    up.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config"):
        (up / f).write_text("x")
    shutil.copy(FIX / "mini" / "nextflow_schema.json", up / "nextflow_schema.json")
    st = SubmoduleStatus("mini", up, True, True, "1.2.0", "deadbeef", ())
    versioned, _ = write_skill.render_status(st, pipeline_version="1.2.0")
    assert "--pipeline-version 1.2.0" in versioned
    assert "pipelines/mini/.versions/1.2.0/upstream" in versioned
    # the default (pinned) run/demo COMMANDS must NOT carry a version flag — keeps the default run latest
    pinned, _ = write_skill.render_status(st)
    for line in pinned.splitlines():
        if line.startswith("nfclaw run"):
            assert "--pipeline-version" not in line
    assert "pipelines/mini/upstream" in pinned


def test_skill_surfaces_other_versions_for_discovery(tmp_path):
    # The committed (pinned) skill.md nudges the agent that other releases are runnable, so it can
    # discover them without grepping a file that only knows the pin.
    pdir = _seed(tmp_path, "mini")
    skill, _ = write_skill.generate("mini", pipelines_dir=pdir)
    text = skill.read_text()
    assert "nfclaw versions mini" in text
    assert "--pipeline-version" in text                       # the discoverability nudge (prose, not the run cmd)


def test_versioned_skill_omits_discovery_note(tmp_path):
    # A version-specific doc already explains the default in its Run-it comment; no extra nudge needed.
    up = tmp_path / "anytree" / "upstream"
    up.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config"):
        (up / f).write_text("x")
    shutil.copy(FIX / "mini" / "nextflow_schema.json", up / "nextflow_schema.json")
    st = SubmoduleStatus("mini", up, True, True, "1.2.0", "deadbeef", ())
    versioned, _ = write_skill.render_status(st, pipeline_version="1.2.0")
    assert "nfclaw versions" not in versioned


def test_deterministic_idempotent(tmp_path):
    pdir = _seed(tmp_path, "mini")
    s1, r1 = write_skill.generate("mini", pipelines_dir=pdir)
    a, b = s1.read_text(), r1.read_text()
    write_skill.generate("mini", pipelines_dir=pdir)
    assert s1.read_text() == a and r1.read_text() == b


def test_reference_covers_all_params(tmp_path):
    from runner import schema
    pdir = _seed(tmp_path, "mini")
    _, ref = write_skill.generate("mini", pipelines_dir=pdir)
    ps = schema.load_param_schema(pdir / "mini" / "upstream")
    text = ref.read_text()
    for name in list(ps.known_params())[:25]:
        assert f"`{name}`" in text or f"--{name.replace('_', '-')}" in text


def test_no_samplesheet_graceful(tmp_path):
    pdir = _seed(tmp_path, "mini_no_input")
    skill, _ = write_skill.generate("mini_no_input", pipelines_dir=pdir)
    text = skill.read_text()
    assert "does not use a samplesheet" in text
    assert "has_samplesheet: false" in text
    assert "input: parameters (no samplesheet)" in text


def test_input_summary_from_schema():
    from runner.schema import Column, InputSchema
    assert write_skill._input_summary(None) == "parameters (no samplesheet)"
    cols = InputSchema(columns=(
        Column("sample", "string", True, None),
        Column("fastq_1", "string", True, None),
    ))
    assert write_skill._input_summary(cols) == "samplesheet (sample, fastq_1)"
    idlist = InputSchema(columns=(Column("", "string", True, r"^\S+$"),))
    assert write_skill._input_summary(idlist) == "id list (one value per line)"


def test_multiqc_detection_and_output_summary(tmp_path):
    up = tmp_path / "upstream"
    (up / "modules" / "nf-core" / "multiqc").mkdir(parents=True)
    assert write_skill._produces_multiqc(up) is True
    assert "MultiQC report" in write_skill._output_summary(up)
    bare = tmp_path / "bare"
    bare.mkdir()
    assert write_skill._produces_multiqc(bare) is False
    out = write_skill._output_summary(bare)
    assert "pipeline_info/" in out and "MultiQC" not in out


def test_vendored_multiqc_is_catalogued_as_conditional(tmp_path):
    # Vendoring a module does not prove a report is made: rnaseq legally skips it with skip_multiqc.
    up = tmp_path / "upstream"
    (up / "modules" / "nf-core" / "multiqc").mkdir(parents=True)
    summary = write_skill._output_summary(up)
    assert "MultiQC report (conditional)" in summary
    assert "run metadata when enabled" in summary


def test_outputs_surface_the_declared_multiqc_skip_option(tmp_path):
    pdir = _seed_with_schema(tmp_path, "qc", {"properties": {
        "skip_multiqc": {"type": "boolean", "description": "Skip MultiQC."}}})
    (pdir / "qc" / "upstream" / "modules" / "nf-core" / "multiqc").mkdir(parents=True)
    text = write_skill.generate("qc", pipelines_dir=pdir)[0].read_text()
    output = text.split("## Outputs\n", 1)[1].split("\n## ", 1)[0]
    assert "--skip-multiqc true" in output
    assert "only when" in output
    assert "one sub-directory per pipeline step/module" not in output


def test_skill_frontmatter_has_input_output(tmp_path):
    pdir = _seed(tmp_path, "mini")
    skill, _ = write_skill.generate("mini", pipelines_dir=pdir)
    fm = skill.read_text().split("---")[1]
    assert "input:" in fm and "output:" in fm


def test_required_params_only(tmp_path):
    # skill.md lists ONLY schema-required params (a fact) — no heuristic "importance" guess.
    ps = ParamSchema(title="t", description="d", params={
        "input": Param("input", "string", None, None, "samplesheet", None, True, "io"),
        "step": Param("step", "string", "mapping", ("mapping", "markduplicates"), "start step", None, True, "main"),
        "aligner": Param("aligner", "string", "star", ("star", "hisat2"), "aligner", None, False, "ref"),
        "email": Param("email", "string", None, None, "boilerplate", None, False, "generic", True),
    })
    out = write_skill._required_params(ps)
    assert "--input" in out and "--step" in out          # required → shown
    assert "`mapping`, `markduplicates`" in out          # allowed values rendered for required enum
    assert "aligner" not in out and "email" not in out   # optional → not shown


# --- tools: parsed from the software sections of the authors' own CITATIONS.md ---
def test_pipeline_tools_parses_citations(tmp_path):
    up = tmp_path / "upstream"
    up.mkdir()
    (up / "CITATIONS.md").write_text(
        "# x: Citations\n\n"
        "## [nf-core](url)\n> ref\n\n"
        "## [Nextflow](url)\n> ref\n\n"
        "## Pipeline tools\n\n"
        "- [FastQC](u1)\n\n"
        "- [STAR](u2)\n  > extra reference line\n\n"
        "- [Salmon](u3)\n\n"
        "## Software packaging/containerisation tools\n\n"
        "- [Docker](ud)\n")
    # only the curated Pipeline-tools section; packaging tools are excluded
    assert write_skill._pipeline_tools(up) == ["FastQC", "STAR", "Salmon"]


def test_pipeline_tools_handles_asterisk_bullets(tmp_path):
    # Older nf-core releases (e.g. bactmap 1.0.0) use `* [Tool]` instead of `- [Tool]`.
    up = tmp_path / "upstream"
    up.mkdir()
    (up / "CITATIONS.md").write_text(
        "# x\n\n## Pipeline tools\n\n"
        "* [bcftools](u1)\n  > ref\n\n"
        "* [BWA](u2)\n\n"
        "+ [fastp](u3)\n")
    assert write_skill._pipeline_tools(up) == ["bcftools", "BWA", "fastp"]


def test_pipeline_tools_graceful_when_absent(tmp_path):
    up = tmp_path / "upstream"
    up.mkdir()
    assert write_skill._pipeline_tools(up) == []                 # no CITATIONS.md
    (up / "CITATIONS.md").write_text("# x\n\n## Pipeline tools\n\n")
    assert write_skill._pipeline_tools(up) == []                 # section present but empty
    (up / "CITATIONS.md").write_text("# x\n\n## [SomePaper](url)\n\n- [Z](u)\n")
    assert write_skill._pipeline_tools(up) == []                 # citation-link section, not software


def test_pipeline_tools_merges_software_sections(tmp_path):
    # Some pipelines (e.g. differentialabundance, detaxizer) split their software across
    # `## Pipeline tools` plus `## R packages` / `## Python`. All are tools the pipeline runs;
    # citation-link headers, packaging/containerisation infra and test-data/archive sections are not.
    up = tmp_path / "upstream"
    up.mkdir()
    (up / "CITATIONS.md").write_text(
        "# x: Citations\n\n"
        "## [nf-core](url)\n> ref\n\n"
        "## Pipeline tools\n\n- [GSEA](u1)\n\n"
        "## R packages\n\n- [DESeq2](u2)\n- [Limma](u3)\n\n"
        "## Python\n\n- [biopython](u4)\n\n"
        "## Data\n\n- [Full-size test data](u5)\n\n"
        "## Pipeline resources\n\n- [SRA](u6)\n\n"
        "## Software packaging/containerisation tools\n\n- [Docker](u7)\n")
    assert write_skill._pipeline_tools(up) == ["GSEA", "DESeq2", "Limma", "biopython"]


def test_skill_surfaces_tools_when_citations_present(tmp_path):
    pdir = _seed(tmp_path, "mini")
    (pdir / "mini" / "upstream" / "CITATIONS.md").write_text(
        "# mini\n\n## Pipeline tools\n\n- [FastQC](u)\n- [STAR](u)\n")
    skill, _ = write_skill.generate("mini", pipelines_dir=pdir)
    text = skill.read_text()
    assert "## Tools this pipeline runs" in text
    assert "FastQC" in text and "STAR" in text
    assert 'tools: ["FastQC", "STAR"]' in text.split("---")[1]    # frontmatter (for the catalog)


# --- summary: the authors' own one-paragraph description from the README `## Introduction` ---
def test_summary_extracts_first_prose_paragraph(tmp_path):
    up = tmp_path / "upstream"
    up.mkdir()
    (up / "README.md").write_text(
        "# nf-core/x\n\n## Introduction\n\n"
        "**nf-core/x** is a bioinformatics pipeline that analyses [RNA-seq](http://u) data "
        "and produces a gene matrix.\n\n"
        "![metro map](docs/map.svg)\n\n"
        "1. Step one\n2. Step two\n")
    assert write_skill._summary(up) == (
        "nf-core/x is a bioinformatics pipeline that analyses RNA-seq data and produces a gene matrix.")


def test_summary_skips_leading_image_and_heading(tmp_path):
    # drugresponseeval leads its Introduction with an image wrapped in a heading.
    up = tmp_path / "upstream"
    up.mkdir()
    (up / "README.md").write_text(
        "## Introduction\n\n"
        "# ![summary](assets/summary.svg)\n\n"
        "**DrEval** is a bioinformatics framework that evaluates drug response prediction models.\n")
    assert write_skill._summary(up) == (
        "DrEval is a bioinformatics framework that evaluates drug response prediction models.")


def test_summary_flattens_reference_style_links(tmp_path):
    up = tmp_path / "upstream"
    up.mkdir()
    (up / "README.md").write_text(
        "## Introduction\n\n"
        "nf-core/q implements the [fgbio Best Practices Pipeline][fgbio-ref] for consensus calling.\n")
    assert write_skill._summary(up) == (
        "nf-core/q implements the fgbio Best Practices Pipeline for consensus calling.")


def test_summary_graceful_when_absent(tmp_path):
    up = tmp_path / "upstream"
    up.mkdir()
    assert write_skill._summary(up) == ""                       # no README.md
    (up / "README.md").write_text("# x\n\n## Usage\n\nrun it\n")
    assert write_skill._summary(up) == ""                       # no Introduction section
    (up / "README.md").write_text("## Introduction\n\n![only an image](i.svg)\n")
    assert write_skill._summary(up) == ""                       # no prose paragraph


def test_skill_surfaces_summary_with_fallback(tmp_path):
    pdir = _seed(tmp_path, "mini")
    (pdir / "mini" / "upstream" / "README.md").write_text(
        "## Introduction\n\nnf-core/mini is a pipeline that does a specific scientific thing well.\n")
    skill, _ = write_skill.generate("mini", pipelines_dir=pdir)
    text = skill.read_text()
    assert "summary: nf-core/mini is a pipeline that does a specific scientific thing well." in text.split("---")[1]
    assert "nf-core/mini is a pipeline that does a specific scientific thing well." in text  # body too


def test_skill_summary_falls_back_to_description(tmp_path):
    # mini fixture has no README -> summary frontmatter falls back to the terse description.
    pdir = _seed(tmp_path, "mini")
    skill, _ = write_skill.generate("mini", pipelines_dir=pdir)
    fm = skill.read_text().split("---")[1]
    assert "summary:" in fm and "description:" in fm


# --- _cell: free text is collapsed to one line and pipe-escaped so tables never break ---
def test_cell_collapses_whitespace_and_escapes_pipes():
    assert write_skill._cell("a\n\nb") == "a b"
    assert write_skill._cell("x  |  y") == "x \\| y"
    assert write_skill._cell("p\tq\nr") == "p q r"


def test_reference_row_is_single_line_and_pipe_safe():
    st = SubmoduleStatus("t", Path("/x"), True, True, "1.0.0", "abc", ())
    desc = "First sentence.\n\nSecond with a | pipe."
    ps = ParamSchema(title="t", description="d", params={
        "weird": Param("weird", "string", None, None, desc, None, False, "g"),
    })
    out = write_skill._render_reference("t", st, ps, None)
    rows = [ln for ln in out.splitlines() if ln.startswith("| `--weird`")]
    assert len(rows) == 1                                       # newlines didn't split the row
    assert "First sentence. Second with a \\| pipe." in rows[0]  # collapsed + pipe escaped


def test_samplesheet_header_carries_only_the_required_columns(tmp_path):
    # The header must be a samplesheet that is always valid. A pipeline can declare optional columns
    # that only apply to one aligner/mode, and emitting every column produces a header with fields an
    # agent then has to fill or blank out. Optional columns are named below it, so nothing is lost.
    pdir = _seed(tmp_path, "mini")
    skill, _ = write_skill.generate("mini", pipelines_dir=pdir)
    text = skill.read_text()
    header = text.split("```csv\n", 1)[1].split("\n", 1)[0]
    assert header == "sample,fastq_1"                 # fastq_2 is optional in the mini fixture
    assert "may be appended to the header" in text and "`fastq_2`" in text


def test_mandatory_group_params_are_surfaced_even_though_they_have_defaults(tmp_path):
    # nf-core marks required-ness in two places that disagree: the JSON-schema `required` list and
    # the group title. A param with a default is never in `required` (nf-schema cannot fail it), yet
    # the pipeline may still reject the default at runtime — nf-core/scrnaseq's `--protocol` aborts
    # the run on its own default for every aligner but cellranger. Reading only `required` hides it.
    import json

    up = tmp_path / "mand" / "upstream"
    up.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config"):
        (up / f).write_text("x")
    (up / "nextflow_schema.json").write_text(json.dumps({
        "title": "nf-core/mand",
        "definitions": {
            "input_output_options": {
                "title": "Input/output options",
                "properties": {"outdir": {"type": "string", "format": "directory-path"}},
                "required": ["outdir"],
            },
            "mandatory_arguments": {
                "title": "Mandatory arguments",
                "properties": {"protocol": {"type": "string", "default": "auto",
                                            "description": "The protocol used."}},
            },
        },
    }))
    skill, _ = write_skill.generate("mand", pipelines_dir=tmp_path)
    text = skill.read_text()
    assert "## Mandatory arguments" in text
    assert "`--protocol`" in text                       # the flag itself, with its default
    assert "the pipeline itself can reject the default at runtime" in text


def test_no_mandatory_section_when_the_schema_has_no_such_group(tmp_path):
    pdir = _seed(tmp_path, "mini")
    skill, _ = write_skill.generate("mini", pipelines_dir=pdir)
    assert "## Mandatory arguments" not in skill.read_text()


def test_resources_section_documents_the_nf_core_resource_ceiling(tmp_path):
    # The stock nf-core process labels are sized for a server; on a workstation a real run dies at
    # the first big step. resourceLimits is the mechanism nf-core documents for capping it.
    pdir = _seed(tmp_path, "mini")
    skill, _ = write_skill.generate("mini", pipelines_dir=pdir)
    text = skill.read_text()
    assert "## Resources" in text
    assert "--limit-cpus 4 --limit-memory 15.GB\n" in text
    # A time cap is not a machine capacity: a too-short one stops long tasks at every retry.
    assert "--limit-time 1.h" not in text and "never as a guess" in text
    assert "process.resourceLimits" in text
    assert "nf-co.re/docs/running/configuration/nextflow-for-your-system" in text


def test_group_list_uses_the_schemas_own_titles(tmp_path):
    pdir = _seed(tmp_path, "mini")
    skill, _ = write_skill.generate("mini", pipelines_dir=pdir)
    assert "**Input/output options** (`input_output_options`)" in skill.read_text()


def test_skill_names_the_engine_the_release_declares(tmp_path):
    # The engine is not a neutral detail: a newer Nextflow major changes the config parser.
    pdir = _seed(tmp_path, "mini")
    (pdir / "mini" / "upstream" / "nextflow.config").write_text(
        "manifest {\n    nextflowVersion = '!>=25.10.4'\n}\n")
    skill, _ = write_skill.generate("mini", pipelines_dir=pdir)
    text = skill.read_text()
    assert "## Nextflow engine" in text
    assert "!>=25.10.4" in text
    assert "--nxf-ver 25.10.4" in text                 # the exact flag to pin it


def test_no_engine_section_when_the_release_declares_nothing(tmp_path):
    pdir = _seed(tmp_path, "mini")                     # seeded nextflow.config has no manifest
    skill, _ = write_skill.generate("mini", pipelines_dir=pdir)
    assert "## Nextflow engine" not in skill.read_text()


def _seed_with_schema(tmp_path, name, schema):
    import json

    up = tmp_path / name / "upstream"
    up.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config"):
        (up / f).write_text("x")
    (up / "nextflow_schema.json").write_text(json.dumps(schema))
    return tmp_path


def test_warns_when_the_release_resolves_a_reference_from_s3_by_default(tmp_path):
    # sarek defaults --genome to GATK.GRCh38, resolved through AWS iGenomes at s3://ngi-igenomes/.
    # A run passing no reference of its own silently reads from S3 — it fails on a host without
    # access to that bucket. The basic recipe looked runnable when it was not.
    pdir = _seed_with_schema(tmp_path, "refs", {
        "title": "nf-core/refs",
        "definitions": {"reference_genome_options": {
            "title": "Reference genome options",
            "properties": {
                "genome": {"type": "string", "default": "GATK.GRCh38"},
                "igenomes_base": {"type": "string", "default": "s3://ngi-igenomes/igenomes/"},
                "igenomes_ignore": {"type": "boolean"},
            }}}})
    text = write_skill.generate("refs", pipelines_dir=pdir)[0].read_text()
    assert "## Reference genome" in text
    assert "resolves a reference genome remotely by default" in text
    assert "GATK.GRCh38" in text and "s3://ngi-igenomes/igenomes/" in text
    assert "--igenomes-ignore true" in text            # the documented way to switch it off


def test_states_that_no_reference_is_set_when_the_default_is_null(tmp_path):
    # rnaseq/scrnaseq: --genome has no default, so nothing is fetched behind the caller's back.
    pdir = _seed_with_schema(tmp_path, "norefs", {
        "title": "nf-core/norefs",
        "definitions": {"reference_genome_options": {
            "title": "Reference genome options",
            "properties": {
                "genome": {"type": "string"},
                "igenomes_base": {"type": "string", "default": "s3://ngi-igenomes/igenomes/"},
            }}}})
    text = write_skill.generate("norefs", pipelines_dir=pdir)[0].read_text()
    assert "No reference genome is set by default" in text
    assert "resolves a reference genome remotely by default" not in text


def test_no_reference_section_when_the_pipeline_has_no_genome_params(tmp_path):
    pdir = _seed(tmp_path, "mini")
    assert "## Reference genome" not in write_skill.generate(
        "mini", pipelines_dir=pdir)[0].read_text()



# --- the reference-genome section names only flags and groups the schema actually has ---
def test_reference_section_names_the_schemas_own_group_and_flags(tmp_path):
    # oncoanalyser / variantprioritization: --genome lives in a differently named group and there is
    # no --fasta. The section still said "the `reference_genome_options` group ... e.g. `--fasta`".
    pdir = _seed_with_schema(tmp_path, "onco", {"definitions": {"reference_data_options": {
        "properties": {"genome": {"type": "string"},
                       "ref_data_path": {"type": "string", "format": "path"}}}}})
    text = write_skill.generate("onco", pipelines_dir=pdir)[0].read_text()
    assert "## Reference genome" in text and "`reference_data_options`" in text
    assert "reference_genome_options" not in text and "--fasta" not in text


def test_reference_section_points_at_fasta_in_its_own_group(tmp_path):
    # raredisease: the reference files are in `reference_file_options`, not `reference_genome_options`.
    pdir = _seed_with_schema(tmp_path, "rare", {"definitions": {
        "input_output_options": {"properties": {"genome": {"type": "string"}}},
        "reference_file_options": {"properties": {"fasta": {"type": "string",
                                                            "format": "file-path"}}}}})
    text = write_skill.generate("rare", pipelines_dir=pdir)[0].read_text()
    assert "`--fasta`" in text and "`reference_file_options`" in text
    assert "reference_genome_options" not in text


def test_no_reference_section_without_a_genome_parameter(tmp_path):
    # mag / nanoseq / airrflow / coproid declare igenomes_base but no --genome: the section told the
    # agent to pass `--genome <id>`, a flag the runner itself rejects as unknown.
    pdir = _seed_with_schema(tmp_path, "nogenome", {"definitions": {"reference_genome_options": {
        "properties": {"igenomes_base": {"type": "string",
                                         "default": "s3://ngi-igenomes/igenomes/"},
                       "igenomes_ignore": {"type": "boolean"}}}}})
    text = write_skill.generate("nogenome", pipelines_dir=pdir)[0].read_text()
    assert "## Reference genome" not in text and "--genome" not in text


def test_reference_source_is_not_invented_from_a_genome_name(tmp_path):
    # marsseq uses a genome key for local ERCC references and GENCODE URLs; the name alone
    # cannot identify a provider, network dependency, download size or genome assembly.
    pdir = _seed_with_schema(tmp_path, "localrefs", {"properties": {
        "genome": {"type": "string", "default": "mm10"},
        "genomes_base": {"type": "string", "format": "directory-path"},
        "fasta": {"type": "string", "format": "file-path"}}})
    text = write_skill.generate("localrefs", pipelines_dir=pdir)[0].read_text()
    reference = text.split("## Reference genome\n", 1)[1].split("\n## ", 1)[0]
    assert "mm10" in reference and "upstream/nextflow.config" in reference
    assert "AWS" not in reference and "S3" not in reference
    assert "remotely by default" not in reference


def test_default_genome_key_names_the_fasta_its_configuration_selects(tmp_path):
    # marsseq's `mm10` key selects GENCODE's GRCm39 assembly, not UCSC mm10 (GRCm38): the key's name
    # is no evidence of the assembly, so the FASTA the pinned configuration assigns is quoted.
    pdir = _seed_with_schema(tmp_path, "localrefs", {"properties": {
        "genome": {"type": "string", "default": "mm10"},
        "genomes_base": {"type": "string", "format": "directory-path"},
        "fasta": {"type": "string", "format": "file-path"}}})
    conf = pdir / "localrefs" / "upstream" / "conf"
    conf.mkdir()
    (conf / "genomes.config").write_text(
        "params {\n    genomes {\n"
        "        'mm10_v32' {\n            fasta = \"${params.genomes_base}/mm10_v32/GRCm39.fa\"\n        }\n"
        "        'mm10' {   // GENCODE M27\n"
        "            bowtie2 = \"${params.genomes_base}/mm10/bowtie2/\"\n"
        "            fasta   = \"${params.genomes_base}/mm10/GRCm39.fa\"\n        }\n    }\n}\n")
    text = write_skill.generate("localrefs", pipelines_dir=pdir)[0].read_text()
    reference = text.split("## Reference genome\n", 1)[1].split("\n## ", 1)[0]
    assert "gives `--genome mm10` the FASTA `${params.genomes_base}/mm10/GRCm39.fa`" in reference
    assert "need not be the assembly it selects" in reference


def test_configured_fasta_reads_igenomes_maps_and_refuses_ambiguity(tmp_path):
    up = tmp_path / "up"
    (up / "conf").mkdir(parents=True)
    (up / "nextflow.config").write_text("params { genome = 'GRCh38' }\n")
    (up / "conf" / "igenomes.config").write_text(
        "params.genomes = [\n    'GRCh38' : [\n"
        "        fasta_fai : \"${params.igenomes_base}/x/genome.fa.fai\",\n"
        "        fasta     : \"${params.igenomes_base}/Homo_sapiens/NCBI/GRCh38/genome.fa\",\n"
        "    ],\n    'GRCh37' : [\n        fasta : \"${params.igenomes_base}/GRCh37/genome.fa\"\n    ]\n]\n")
    assert (write_skill._configured_fasta(up, "GRCh38")
            == "${params.igenomes_base}/Homo_sapiens/NCBI/GRCh38/genome.fa")
    assert write_skill._configured_fasta(up, "hg19") is None
    # Two definitions that disagree say nothing rather than pick one.
    (up / "conf" / "other.config").write_text("'GRCh38' {\n    fasta = '/elsewhere/genome.fa'\n}\n")
    assert write_skill._configured_fasta(up, "GRCh38") is None


def test_local_igenomes_base_does_not_claim_remote_downloads(tmp_path):
    pdir = _seed_with_schema(tmp_path, "localigenomes", {"properties": {
        "genome": {"type": "string", "default": "GRCh38"},
        "igenomes_base": {"type": "string", "default": "/reference/igenomes"}}})
    text = write_skill.generate("localigenomes", pipelines_dir=pdir)[0].read_text()
    reference = text.split("## Reference genome\n", 1)[1].split("\n## ", 1)[0]
    assert "/reference/igenomes" in reference
    assert "AWS" not in reference and "S3" not in reference
    assert "remotely by default" not in reference


def test_custom_remote_igenomes_base_names_the_declared_source(tmp_path):
    pdir = _seed_with_schema(tmp_path, "customrefs", {"properties": {
        "genome": {"type": "string", "default": "GRCh38"},
        "igenomes_base": {"type": "string", "default": "https://reference.example/igenomes"}}})
    text = write_skill.generate("customrefs", pipelines_dir=pdir)[0].read_text()
    reference = text.split("## Reference genome\n", 1)[1].split("\n## ", 1)[0]
    assert "https://reference.example/igenomes" in reference
    assert "AWS" not in reference and "S3" not in reference
    assert "remotely by default" in reference


def test_disabled_igenomes_lookup_does_not_claim_remote_resolution(tmp_path):
    pdir = _seed_with_schema(tmp_path, "ignoredrefs", {"properties": {
        "genome": {"type": "string", "default": "GRCh38"},
        "igenomes_base": {"type": "string", "default": "s3://ngi-igenomes/igenomes/"},
        "igenomes_ignore": {"type": "boolean", "default": True}}})
    text = write_skill.generate("ignoredrefs", pipelines_dir=pdir)[0].read_text()
    reference = text.split("## Reference genome\n", 1)[1].split("\n## ", 1)[0]
    assert "disabled by default" in reference
    assert "remotely by default" not in reference


# --- tools: names are kept whole, and only software sections count ---
def test_tools_frontmatter_is_a_json_list_that_keeps_commas(tmp_path):
    # airrflow cites "SHazaM, Change-O" as one tool; a comma-joined frontmatter split it in two.
    pdir = _seed(tmp_path, "mini")
    (pdir / "mini" / "upstream" / "CITATIONS.md").write_text(
        "# mini\n\n## Pipeline tools\n\n- [SHazaM, Change-O](u)\n- [pRESTO](u)\n")
    text = write_skill.generate("mini", pipelines_dir=pdir)[0].read_text()
    assert 'tools: ["SHazaM, Change-O", "pRESTO"]' in text.split("---")[1]


def test_data_and_framework_sections_are_not_tools(tmp_path):
    # readsimulator lists bait sets under "Reference probe/baitset databases"; raredisease lists
    # nf-core and Nextflow under "Nextflow & nf-core". Neither is software the pipeline runs.
    up = tmp_path / "upstream"
    up.mkdir()
    (up / "CITATIONS.md").write_text(
        "# x\n\n## Pipeline tools\n\n- [STAR](u)\n\n"
        "## Reference probe/baitset databases\n\n- [Tetrapods; 2,560 baits](u)\n\n"
        "## Test Data\n\n- [Full-size data](u)\n\n"
        "## Nextflow & nf-core\n\n- [nf-core](u)\n- [Nextflow](u)\n")
    assert write_skill._pipeline_tools(up) == ["STAR"]


# --- allowed values: each value is its own code span, so values containing commas stay legible ---
def test_allowed_values_are_quoted_one_by_one(tmp_path):
    # ampliseq --filter-ssu allows "bac,arc,mito,euk", "bac", ...; joined with ", " the cell read
    # "bac,arc,mito,euk, bac, arc, ..." and neither an agent nor the website could split it back.
    pdir = _seed_with_schema(tmp_path, "enums", {"definitions": {"g": {"properties": {
        "filter_ssu": {"type": "string", "enum": ["bac,arc", "bac", "vst"]}}}}})
    ref = write_skill.generate("enums", pipelines_dir=pdir)[1].read_text()
    assert "| `bac,arc`, `bac`, `vst` |" in ref


# --- an --input that is not a samplesheet is documented from its own parameter ---
def test_input_that_is_not_a_samplesheet_is_documented_from_its_parameter(tmp_path):
    # rangeland: --input is a directory or tarball of imagery, but the release still ships the
    # nf-core template schema_input.json (sample, fastq_1, fastq_2), which the skill presented as
    # the input — and the runner then rejected the real directory as "samplesheet not found".
    import json
    pdir = _seed_with_schema(tmp_path, "imagery", {"definitions": {"input_output_options": {
        "required": ["input", "outdir"],
        "properties": {
            "input": {"type": "string", "format": "path", "exists": True,
                      "description": "Root directory or tarball of all satellite imagery."},
            "outdir": {"type": "string", "format": "directory-path"}}}}})
    assets = pdir / "imagery" / "upstream" / "assets"
    assets.mkdir()
    (assets / "schema_input.json").write_text(json.dumps({"items": {
        "properties": {"sample": {"type": "string"},
                       "fastq_1": {"type": "string", "format": "file-path"}},
        "required": ["sample", "fastq_1"]}}))
    text = write_skill.generate("imagery", pipelines_dir=pdir)[0].read_text()
    front = text.split("---")[1]
    assert "has_samplesheet: false" in front and "input: --input (no samplesheet schema)" in front
    assert "fastq_1" not in text and "samplesheet.csv" not in text
    run = next(line for line in text.splitlines() if line.startswith("nfclaw run imagery"))
    assert "--input <input>" in run
    # States only what the release publishes — bactmap and seqsubmit take a samplesheet too, they
    # just ship no schema for it — and quotes the parameter's own description.
    assert "publishes no samplesheet schema for `--input`" in text
    assert "Root directory or tarball of all satellite imagery." in text
    assert "does not take a samplesheet" not in text


def test_input_summary_names_an_input_without_a_samplesheet_schema():
    ps = ParamSchema(title="t", description="d", params={
        "input": Param("input", "string", None, None, "Path to a sample sheet", None, True, "io")})
    assert write_skill._input_summary(None, ps) == "--input (no samplesheet schema)"
    assert write_skill._input_summary(None) == "parameters (no samplesheet)"


def test_cli_requires_a_pipeline_name_or_all():
    import pytest
    with pytest.raises(SystemExit) as exc:
        write_skill.main([])                          # crashed with a TypeError
    assert exc.value.code == 2


def test_outputs_section_says_where_the_run_is_logged(tmp_path):
    # The skill is what an agent reads right before running; it must not have to ask where the log is.
    pdir = _seed(tmp_path, "mini")
    skill, _ = write_skill.generate("mini", pipelines_dir=pdir)
    text = skill.read_text()
    assert "`<outdir>/provenance/logs/run.log`" in text
    assert "`<outdir>/.nextflow.log`" in text
    assert "`nfclaw status <outdir>`" in text           # how to check a run without reading logs


# --- dev: docs generated from an unreleased development commit ---------------------------------

_DEV_SHA = "f754e0a247b03f169782dbb5c688e055044a5988"


def _dev_status(tmp_path, name="mini"):
    up = tmp_path / ".versions" / f"dev-{_DEV_SHA[:12]}" / "upstream"
    up.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config"):
        (up / f).write_text("x")
    (up / "nextflow.config").write_text("manifest {\n  nextflowVersion = '!>=25.10.4'\n}\n")
    shutil.copy(FIX / name / "nextflow_schema.json", up / "nextflow_schema.json")
    (up / "docs").mkdir()
    (up / "docs" / "output.md").write_text("# outputs\n")
    return SubmoduleStatus(name, up, True, True, "dev", _DEV_SHA, ())


def test_dev_render_runs_and_links_the_exact_commit(tmp_path):
    st = _dev_status(tmp_path)
    skill, ref = write_skill.render_status(st, pipeline_version="dev")
    assert "version: dev" in skill and f"commit: {_DEV_SHA}" in skill
    # the run, resources and demo commands all ask for dev
    # (the engine section's `nfclaw run mini ... --nxf-ver X` elides the rest of the command)
    run_lines = [ln for ln in skill.splitlines()
                 if ln.startswith("nfclaw run") and " ... " not in ln]
    assert len(run_lines) == 3 and all("--pipeline-version dev" in ln for ln in run_lines)
    # the raw equivalent runs that commit's immutable tree, never a moving `dev` path
    assert f"nextflow run pipelines/mini/.versions/dev-{_DEV_SHA[:12]}/upstream" in skill
    # upstream links point at the commit the docs were generated from, not the moving branch
    assert f"blob/{_DEV_SHA}/docs/output.md" in skill
    assert f"blob/{_DEV_SHA}/docs/usage.md" in skill
    assert "blob/dev/" not in skill
    assert "This commit declares `nextflowVersion = '!>=25.10.4'`" in skill


def test_known_issues_link_resolves_from_where_each_skill_is_written(tmp_path):
    # The committed skill.md sits at pipelines/<name>/skill.md; a version's docs are written beside
    # its tree, at pipelines/<name>/.versions/<label>/skill.md — two directories deeper.
    import re

    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "known-issues.md").write_text("# known issues\n")
    pipelines = root / "pipelines"
    pdir = _seed(pipelines, "mini")
    (pdir / "mini" / "upstream" / "nextflow.config").write_text(
        "manifest {\n    nextflowVersion = '!>=25.10.4'\n}\n")
    pinned, _ = write_skill.generate("mini", pipelines_dir=pdir)
    st = _dev_status(pipelines / "mini")
    dev_skill, _ = versions.generate_docs(st, dest_dir=st.path.parent)
    assert dev_skill.parent == pipelines / "mini" / ".versions" / f"dev-{_DEV_SHA[:12]}"
    for skill in (pinned, dev_skill):
        links = re.findall(r"\[known-issues\]\(([^)]+)\)", skill.read_text())
        assert links, skill
        for link in links:
            assert (skill.parent / link).resolve() == (root / "docs" / "known-issues.md").resolve()


def test_dev_render_warns_that_the_code_is_unreleased(tmp_path):
    st = _dev_status(tmp_path)
    skill, _ = write_skill.render_status(st, pipeline_version="dev")
    assert "**Unreleased development code.**" in skill
    assert "run_manifest.json" in skill and "commands.sh" in skill
    # the release-only discovery nudge is replaced by the dev warning
    assert "This is the pinned latest release" not in skill


def test_dev_render_normalizes_the_spelling(tmp_path):
    st = _dev_status(tmp_path)
    upper, _ = write_skill.render_status(st, pipeline_version="DEV")
    lower, _ = write_skill.render_status(st, pipeline_version="dev")
    assert upper == lower


def test_pinned_skill_points_agents_at_dev(tmp_path):
    # The committed skill.md is how an agent learns that unreleased code is runnable at all.
    pdir = _seed(tmp_path, "mini")
    skill, _ = write_skill.generate("mini", pipelines_dir=pdir)
    text = skill.read_text()
    assert "--pipeline-version dev" in text
    assert "nfclaw show mini --pipeline-version dev" in text
    for line in text.splitlines():                           # the default commands stay on the pin
        if line.startswith("nfclaw run"):
            assert "--pipeline-version" not in line


def test_skill_lists_what_a_pipeline_feeds_and_is_fed_by(library):
    from runner import handoff, submodule
    root = library("mini_up", "mini", rules={("mini_up", "mini"): {
        "description": "mini_up writes a mini sheet",
        "params": {"input": {"samplesheet": "s.csv", "provides": ["sample", "fastq_1"]}}}})
    rules = handoff.load_registry(root)
    pdir = root / "pipelines"
    up_skill, _ = write_skill.render_status(submodule.resolve("mini_up", pdir), rules=rules)
    down_skill, _ = write_skill.render_status(submodule.resolve("mini", pdir), rules=rules)
    assert 'feeds: ["mini"]' in up_skill and "## Chaining" in up_skill
    assert "- `mini` — mini_up writes a mini sheet" in up_skill
    assert "Fed by:" in down_skill and "feeds:" not in down_skill
    assert "- `mini_up` — mini_up writes a mini sheet" in down_skill
    plain, _ = write_skill.render_status(submodule.resolve("mini", pdir))
    assert "## Chaining" not in plain                      # no rules → no section, docs unchanged


def test_generate_reads_the_registry_next_to_the_pipelines(library):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): {
        "description": "d", "params": {"input": {"samplesheet": "s.csv",
                                                 "provides": ["sample", "fastq_1"]}}}})
    skill, _ = write_skill.generate("mini_up", pipelines_dir=root / "pipelines")
    assert "## Chaining" in skill.read_text()


def _engine_tree(tmp_path, spec):
    from runner.submodule import SubmoduleStatus
    (tmp_path / "nextflow.config").write_text(f"manifest {{ nextflowVersion = '{spec}' }}\n")
    return SubmoduleStatus(name="p", path=tmp_path, initialized=True, complete=True,
                           version="1.0.0", commit="c" * 40, missing_files=())


def test_engine_pin_older_than_resource_limits_says_limit_flags_are_refused(tmp_path):
    from runner.schema import Param, ParamSchema

    def param(name):
        return Param(name, "string", None, None, "", None, False, "g")
    ps = ParamSchema("p", "", {n: param(n) for n in ("max_cpus", "max_memory", "input")})
    text = write_skill._engine_section("p", _engine_tree(tmp_path, "!>=23.04.0"), ps=ps)
    assert "--nxf-ver 23.04.0" in text
    assert "predates `process.resourceLimits` (24.04.0)" in text
    assert "`--max-cpus`, `--max-memory` instead" in text


def test_engine_pin_with_resource_limits_adds_no_caveat(tmp_path):
    text = write_skill._engine_section("p", _engine_tree(tmp_path, "!>=24.04.2"))
    assert "--nxf-ver 24.04.2" in text and "resourceLimits" not in text


def _rendered(tmp_path, spec):
    import sheetgen_schemas as S
    up = S.make_pipeline(tmp_path, spec)
    st = SubmoduleStatus("pipe", up, True, True, "1.0.0", "c" * 40, ())
    text, _ = write_skill.render_status(st)
    inputs = text.split("## Inputs\n", 1)[1].split("\n## ", 1)[0]
    generated = [p for p in inputs.split("\n\n") if p.startswith("**From data files.**")]
    return inputs, (generated[0] if generated else None)


def test_inputs_say_what_generating_the_samplesheet_fills_and_needs(tmp_path):
    import sheetgen_schemas as S
    inputs, paragraph = _rendered(tmp_path, S.RNASEQ)
    assert "`fastq_1`/`fastq_2` from FastQ files" in paragraph and "`sample` from file names" in paragraph
    assert "`--sheet-set COLUMN=VALUE`" in paragraph
    assert "`strandedness` (one of forward, reverse, unstranded, auto)" in paragraph
    # The website reads the first table and the csv/tsv blocks of this section: the paragraph adds
    # neither, and the header block is unchanged.
    assert "```" not in paragraph and "|" not in paragraph
    assert "```csv\nsample,fastq_1,strandedness\n```" in inputs


def test_inputs_name_the_choice_or_the_reason_generation_needs(tmp_path):
    import sheetgen_schemas as S
    _, mag = _rendered(tmp_path / "mag", S.MAG)
    assert "once you choose the read columns" in mag and "--sheet-set long_reads=" in mag
    _, airrflow = _rendered(tmp_path / "airrflow", S.AIRRFLOW)
    assert "cannot generate this samplesheet" in airrflow
    _, drop = _rendered(tmp_path / "drop", S.DROP)
    assert "Schema defaults fill `STRAND` = `no`" in drop
    _, sarek = _rendered(tmp_path / "sarek", S.SAREK)
    assert "`lane` from Illumina lane numbers" in sarek and "`patient` (matching ^\\S+$)" in sarek
    assert _rendered(tmp_path / "none", S.NO_SHEET)[1] is None


def test_demo_section_says_when_the_test_profile_runs_stubs(tmp_path):
    # proteinfold's skill.md offered `--demo` with no hint that its test profile computes nothing.
    pdir = _seed(tmp_path, "mini")
    up = pdir / "mini" / "upstream"
    (up / "nextflow.config").write_text("profiles {\n    test { includeConfig 'conf/test.config' }\n}\n")
    (up / "conf").mkdir()
    (up / "conf/test.config").write_text("params { input = 'x' }\n")
    demo = write_skill.generate("mini", pipelines_dir=pdir)[0].read_text().split("## Demo\n", 1)[1]
    assert "stubRun" not in demo.split("\n## ", 1)[0]
    (up / "conf/test.config").write_text("stubRun = true\nparams { input = 'x' }\n")
    demo = write_skill.generate("mini", pipelines_dir=pdir)[0].read_text().split("## Demo\n", 1)[1]
    assert "`stubRun = true`" in demo.split("\n## ", 1)[0]


def test_engine_section_steers_away_from_a_minimum_that_cannot_run_on_java_17(tmp_path):
    # bactmap 1.0.0 declares !>=21.04.0; that engine fails on Java 17 with "Unsupported class file
    # major version 61", so pinning it as advised made every run fail before reading the pipeline.
    text = write_skill._engine_section("p", _engine_tree(tmp_path, "!>=21.04.0"))
    assert "--nxf-ver 21.04.0" not in text
    assert "--nxf-ver 24.10.5" in text and "Java 17" in text


def test_engine_section_keeps_a_minimum_that_runs_on_java_17(tmp_path):
    text = write_skill._engine_section("p", _engine_tree(tmp_path, "!>=21.10.3"))
    assert "--nxf-ver 21.10.3" in text and "Java 17" not in text


def test_skill_md_names_the_nextflow_secrets_a_release_reads(tmp_path):
    # seqsubmit reads ENA Webin credentials from Nextflow secrets in its nextflow.config; nothing in
    # its skill.md said so, and a run without them failed only after its first tasks had started.
    pdir = _seed(tmp_path, "mini")
    up = pdir / "mini" / "upstream"
    (up / "nextflow.config").write_text(
        "env {\n    ENA_WEBIN          = secrets.ENA_WEBIN\n"
        "    ENA_WEBIN_PASSWORD = secrets.ENA_WEBIN_PASSWORD\n}\n")
    (up / "modules" / "local").mkdir(parents=True)
    (up / "modules" / "local" / "download.nf").write_text(
        "process DOWNLOAD {\n    secret 'NCBI_EMAIL'\n    script:\n    'true'\n}\n")
    text = write_skill.generate("mini", pipelines_dir=pdir)[0].read_text()
    section = text.split("## Secrets\n", 1)[1].split("\n## ", 1)[0]
    assert "`ENA_WEBIN` (in `nextflow.config`); `ENA_WEBIN_PASSWORD` (in `nextflow.config`)" in section
    assert "`NCBI_EMAIL` (in `modules/local/download.nf`)" in section
    assert "nextflow secrets set" in section


def test_skill_md_has_no_secrets_section_without_secrets(tmp_path):
    pdir = _seed(tmp_path, "mini")
    assert "## Secrets" not in write_skill.generate("mini", pipelines_dir=pdir)[0].read_text()


def test_write_all_skips_hidden_entries_beside_the_pipelines(tmp_path):
    pdir = _seed(tmp_path, "mini")
    (pdir / ".nextflow" / "plr").mkdir(parents=True)
    assert write_skill.main(["--all", "--pipelines-dir", str(pdir)]) == 0
    assert (pdir / "mini" / "skill.md").is_file() and not (pdir / ".nextflow" / "skill.md").exists()


def test_secrets_section_stays_short_when_many_modules_read_one_secret(tmp_path):
    pdir = _seed(tmp_path, "mini")
    for tool in ("bwamem", "dedup", "haplotyper", "dnascope"):
        mod = pdir / "mini" / "upstream" / "modules" / "nf-core" / "sentieon" / tool
        mod.mkdir(parents=True)
        (mod / "main.nf").write_text("process X {\n    secret 'SENTIEON_LICENSE_BASE64'\n}\n")
    text = write_skill.generate("mini", pipelines_dir=pdir)[0].read_text()
    assert text.count("SENTIEON_LICENSE_BASE64") == 1
    assert "and 2 more files" in text
