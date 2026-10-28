"""Regression tests for the library's maintenance gates and generated docs, and for the
schema-surfacing pass.

The surfacing pass guarantees every fact the loader captures is rendered downstream:
`hidden`, column `pattern`, the path-format marker and the schema `title`. It also makes
`Column.fmt` symmetric with `Param.fmt` (both carry file-path/directory-path), so a
samplesheet directory column is no longer silently flattened to a plain string.
"""
import inspect
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from librarian import check_drift, update_pipelines, write_catalog, write_skill
from runner import inputs, preflight, schema
from runner.schema import Column, InputSchema, Param, ParamSchema
from runner.submodule import SubmoduleStatus

FIX = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[1]


def test_nextflow_accept_rejects_invalid_pipeline_name(tmp_path):
    result = tmp_path / "accept.tsv"
    env = {
        **os.environ,
        "NFCLAW_RESULT_FILE": str(result),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
        "RUNNER_TEMP": str(tmp_path),
    }
    proc = subprocess.run(
        ["bash", str(REPO / "scripts" / "nextflow_accept.sh"), "../bad"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "Invalid pipeline name" in proc.stdout
    assert "../bad\trejected" in result.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", [".", ".."])
def test_nextflow_accept_rejects_special_path_components(tmp_path, name):
    env = {**os.environ, "NFCLAW_RESULT_FILE": str(tmp_path / "result.tsv")}
    proc = subprocess.run(
        ["bash", "scripts/nextflow_accept.sh", name],
        cwd=Path(__file__).parent.parent, env=env, capture_output=True, text=True,
    )
    assert proc.returncode != 0
    assert "Invalid pipeline name" in proc.stdout


def test_setup_nextflow_action_verifies_the_checksum_and_stays_out_of_the_repo():
    # The launcher is fetched from the network on every job, so the install must stay pinned and
    # checksum-verified — and must never land in the working tree: a workflow that commits its tree
    # (auto-update, discover-pipelines) would otherwise sweep the downloaded file into a PR.
    text = (REPO / ".github" / "actions" / "setup-nextflow" / "action.yml").read_text(
        encoding="utf-8")
    assert "sha256sum --check --strict" in text
    assert 'launcher="$RUNNER_TEMP/nextflow"' in text
    assert "--output nextflow" not in text                     # i.e. never into the repo root


def test_the_launcher_is_not_tracked_in_the_repo():
    assert not (REPO / "nextflow").exists()


def test_every_workflow_installs_nextflow_through_the_pinned_action():
    # One pinned, checksum-verified install for the whole repo — no workflow may hand-roll its own.
    for wf in sorted((REPO / ".github" / "workflows").glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        if "nextflow" not in text.lower():
            continue
        assert "raw.githubusercontent.com/nextflow-io/nextflow" not in text, (
            f"{wf.name} downloads the launcher itself; use ./.github/actions/setup-nextflow")


def test_every_pipeline_is_registered_in_sources_tsv():
    # The invariant the narrow allowlist broke, asserted on the artefact itself so it holds no
    # matter which mechanism breaks it next: pipelines/, .gitmodules and sources.tsv describe one
    # and the same set of pipelines. (check_drift enforces this too, but it only runs in the
    # workflows a bot merge does not trigger — this runs on every PR.)
    sources = (REPO / "sources.tsv").read_text(encoding="utf-8")
    registered = {line.split("\t")[0] for line in sources.splitlines()
                  if line.strip() and not line.startswith("#")}
    submodules = set(re.findall(r"path = pipelines/([^/\n]+)/upstream",
                                (REPO / ".gitmodules").read_text(encoding="utf-8")))
    assert submodules - registered == set(), "pipelines missing a sources.tsv row"
    assert registered - submodules == set(), "sources.tsv rows with no pipeline"


# --- skill.md is deterministic: ONLY schema-required params + a group map. For scientific use
#     an agent must not rely on a guessed "importance" subset of the parameters. ---
def test_required_params_lists_only_required_in_schema_order():
    ps = ParamSchema(title="t", description="d", params={
        "input": Param("input", "string", None, None, "ss", None, True, "io"),
        "outdir": Param("outdir", "string", None, None, "out", None, True, "io"),
        "aligner": Param("aligner", "string", "star", None, "no default but optional",
                         None, False, "ref"),
    })
    out = write_skill._required_params(ps)
    assert "--input" in out and "--outdir" in out          # required → shown
    assert "aligner" not in out                            # optional (even no-default) → not shown
    assert out.index("--input") < out.index("--outdir")    # schema order preserved
    assert "| parameter | type | default | allowed values | constraints | description |" in out


def test_required_params_show_defaults_for_required_defaulted_params():
    # Sarek's `--step` is schema-required but defaults to `mapping`; surfacing that default keeps
    # agents from pausing to choose a value that the pinned pipeline already defines.
    ps = ParamSchema(title="t", description="d", params={
        "step": Param("step", "string", "mapping", ("mapping", "annotate"),
                      "Starting step", None, True, "io"),
    })
    out = write_skill._required_params(ps)
    row = next(line for line in out.splitlines() if line.startswith("| `--step`"))
    assert "| mapping |" in row


def test_param_groups_maps_every_group_with_counts():
    ps = ParamSchema(title="t", description="d", params={
        "a": Param("a", "string", None, None, "x", None, True, "input_output"),
        "b": Param("b", "string", "d", None, "y", None, False, "advanced"),
        "c": Param("c", "string", "d", None, "z", None, False, "advanced"),
    })
    out = write_skill._param_groups(ps)
    assert "`input_output` — 1 parameter" in out          # full group size, singular grammar
    assert "`advanced` — 2 parameters" in out
    # The counts are full group sizes; the prose must not claim every counted param is optional.
    assert "All other parameters are optional" not in out
    assert "include any parameter already listed above" in out


# --- catalog.md escapes pipes in the description cell ---
def test_catalog_md_escapes_pipes(tmp_path):
    d = tmp_path / "pX"
    (d / "upstream").mkdir(parents=True)
    (d / "skill.md").write_text("---\nname: pX\nversion: 1.0.0\n"
                                "description: does A | B things\n---\n")
    out_md, out_json = tmp_path / "catalog.md", tmp_path / "catalog.json"
    write_catalog.generate(pipelines_dir=tmp_path, out_md=out_md, out_json=out_json)
    md = out_md.read_text()
    assert "A \\| B" in md
    row = next(line for line in md.splitlines() if line.startswith("| `pX`"))
    # 6 unescaped pipes = exactly 5 columns (pipeline|version|input|output|description);
    # the literal pipe in the description stays escaped, not counted as a separator
    assert row.count("|") - row.count("\\|") == 6


# --- the drift gate covers catalog.{md,json} ---
def test_check_drift_detects_stale_catalog(tmp_path):
    repo = tmp_path
    pdir = repo / "pipelines"
    up = pdir / "pY" / "upstream"
    up.mkdir(parents=True)
    shutil.copy(FIX / "mini" / "nextflow_schema.json", up / "nextflow_schema.json")
    write_skill.generate("pY", pipelines_dir=pdir)          # correct skill.md + reference.md
    (repo / "catalog.md").write_text("STALE\n")
    (repo / "catalog.json").write_text("[]\n")
    drift = check_drift.check(pdir)
    assert any("catalog.md" in d for d in drift)
    assert not any("pY/skill.md" in d for d in drift)        # skill.md itself is in sync


# --- an unnamed-column input schema (e.g. fetchngs id list) renders cleanly ---
def test_inputs_section_handles_unnamed_single_column():
    insch = InputSchema(columns=(Column("", "string", False, "^SRR", None),))
    out = write_skill._inputs_section(insch)
    assert "one value per line" in out
    assert "| `` |" not in out          # no broken empty-named table cell


def test_inputs_section_named_columns_still_render_table():
    insch = InputSchema(columns=(
        Column("sample", "string", True, None, None),
        Column("fastq_1", "string", True, None, "file-path"),
    ))
    out = write_skill._inputs_section(insch)
    assert "| `sample` |" in out and "| `fastq_1` |" in out


# --- update_pipelines honours the sources.tsv policy column ---
def test_update_pipelines_respects_policy(tmp_path, monkeypatch):
    src = tmp_path / "sources.tsv"
    src.write_text("a\thttps://x/a.git\tlatest-release\nb\thttps://x/b.git\tpinned\n")
    bumped: list[str] = []
    monkeypatch.setattr(update_pipelines, "bump",
                        lambda name, url, root: (bumped.append(name), "1.0.0")[1])
    update_pipelines.main(["--sources", str(src), "--repo-root", str(tmp_path)])
    assert bumped == ["a"]   # only the latest-release pipeline is bumped; pinned 'b' is skipped


# --- samplesheet inputs are schema-faithful — allowed values shown, NO fabricated values ---
def test_inputs_section_shows_enum_and_no_fabricated_values():
    insch = InputSchema(columns=(
        Column("sample", "string", True, None, None),
        Column("sex", "string", False, None, None, enum=("XX", "XY", "NA")),
        Column("fastq_1", "string", False, None, "file-path"),
    ))
    out = write_skill._inputs_section(insch)
    assert "`XX`, `XY`, `NA`" in out                             # enum → allowed values (a fact)
    assert "string (file path)" in out                          # file-path columns marked
    assert "data/sample1_" not in out and "sample1" not in out  # no invented values
    csv = out.split("```csv\n")[1].split("```")[0].strip()
    assert csv == "sample"          # the header is the required columns — never a fabricated row
    assert "\n" not in csv          # header only: no invented data lines
    # The optional columns are not dropped, just not forced into the header.
    assert "`sex`" in out and "`fastq_1`" in out


def test_samplesheet_docs_follow_schema_input_extension():
    # nf-core/airrflow requires a .tsv input even though its prose description says
    # comma-separated. The generated skill must follow the schema constraint, not prose.
    insch = InputSchema(columns=(
        Column("sample_id", "string", True, None, None),
        Column("filename_R1", "string", True, None, "file-path"),
    ))
    ps = ParamSchema(title="t", description="d", params={
        "input": Param("input", "string", None, None, "Path to comma-separated file",
                       "file-path", True, "io", pattern=r"^\S+\.tsv$"),
        "outdir": Param("outdir", "string", None, None, "out", "directory-path", True, "io"),
    })
    nf, raw = write_skill._run_invocation("airrflow", ps, insch)
    assert "--input samplesheet.tsv" in nf and "--input samplesheet.tsv" in raw
    out = write_skill._inputs_section(insch, ps)
    assert "TSV" in out and "CSV" not in out
    assert "```tsv\nsample_id\tfilename_R1\n```" in out


def test_user_facing_commands_do_not_assume_bare_python():
    # Some macOS/Linux environments have python3 but no python. User-facing commands and Make
    # targets must not require a bare `python` executable to exist.
    for rel in ("README.md", "AGENTS.md", "Makefile"):
        text = (REPO / rel).read_text(encoding="utf-8")
        assert "python -m " not in text


def test_load_input_schema_captures_column_enum(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "schema_input.json").write_text(
        '{"items": {"properties": {"status": {"type": "integer", "enum": [0, 1]}}, '
        '"required": ["status"]}}')
    insch = schema.load_input_schema(tmp_path)
    col = insch.columns[0]
    assert col.name == "status" and col.enum == ("0", "1")      # ints rendered as strings


# --- Surfacing pass: every fact the loader captures is rendered; Param.fmt and Column.fmt
#     are symmetric (both file-path AND directory-path); hidden/pattern/title all reach docs. ---
def test_type_with_fmt_marks_only_path_formats():
    assert write_skill._type_with_fmt("string", "file-path") == "string (file path)"
    assert write_skill._type_with_fmt("string", "directory-path") == "string (directory path)"
    # nf-schema's other path formats are paths too (the runner makes them absolute), so they are
    # documented as such — mag's --busco-db (`path`), sarek's --known-indels (`file-path-pattern`).
    assert write_skill._type_with_fmt("string", "path") == "string (file or directory path)"
    assert write_skill._type_with_fmt("string", "file-path-pattern") == "string (file path glob)"
    assert write_skill._type_with_fmt("integer", None) == "integer"
    assert write_skill._type_with_fmt("string", "email") == "string"   # non-path format → unchanged


def test_column_fmt_is_symmetric_with_param_and_drives_is_path(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "schema_input.json").write_text(
        '{"items": {"properties": {'
        '"reads": {"type": "string", "format": "file-path"}, '
        '"refdir": {"type": "string", "format": "directory-path"}, '
        '"name": {"type": "string"}}}}')
    cols = {c.name: c for c in schema.load_input_schema(tmp_path).columns}
    assert cols["reads"].fmt == "file-path" and cols["reads"].is_path is True
    # not flattened
    assert cols["refdir"].fmt == "directory-path" and cols["refdir"].is_path is True
    assert cols["name"].fmt is None and cols["name"].is_path is False


def test_inputs_section_surfaces_constraints_and_directory_path():
    insch = InputSchema(columns=(
        Column("sample", "string", True, r"^\S+$", None),
        Column("reads", "string", False, r"^\S+\.fq\.gz$", "file-path"),
        Column("refdir", "string", False, None, "directory-path"),
    ))
    out = write_skill._inputs_section(insch)
    assert "| constraints |" in out                    # unified constraints column header
    assert r"matches ^\S+\.fq\.gz$" in out             # a real column pattern rendered (a fact)
    assert "string (file path)" in out                 # file-path marker
    assert "string (directory path)" in out            # directory-path marker (was lost before)


def test_load_param_schema_captures_hidden(tmp_path):
    (tmp_path / "nextflow_schema.json").write_text(
        '{"title": "t", "definitions": {"g": {"properties": {'
        '"email": {"type": "string", "hidden": true}, '
        '"input": {"type": "string"}}}}}')
    ps = schema.load_param_schema(tmp_path)
    assert ps.params["email"].hidden is True
    assert ps.params["input"].hidden is False


def test_reference_surfaces_hidden_fmt_and_title():
    st = SubmoduleStatus(name="pZ", path=Path("/x"), initialized=True, complete=True,
                         version="1.0.0", commit="abc1234", missing_files=())
    ps = ParamSchema(title="nf-core/pZ parameters", description="d", params={
        "input": Param("input", "string", None, None, "samplesheet", "file-path", True, "io"),
        "outdir": Param("outdir", "string", None, None, "results", "directory-path", True, "io"),
        "email": Param("email", "string", None, None, "notify", None, False,
                       "generic", hidden=True),
    })
    out = write_skill._render_reference("pZ", st, ps, None)
    assert "nf-core/pZ parameters" in out               # schema title surfaced in the intro
    assert "| hidden |" in out                           # hidden column present
    assert "string (file path)" in out                   # Param.fmt surfaced
    assert "string (directory path)" in out              # directory-path Param.fmt surfaced
    email_row = next(line for line in out.splitlines() if line.startswith("| `--email`"))
    assert email_row.split("|")[4].strip() == "yes"      # hidden cell = yes for hidden param
    input_row = next(line for line in out.splitlines() if line.startswith("| `--input`"))
    assert input_row.split("|")[4].strip() == ""         # non-hidden → blank hidden cell


def test_required_params_marks_path_formats():
    ps = ParamSchema(title="t", description="d", params={
        "input": Param("input", "string", None, None, "ss", "file-path", True, "io"),
        "outdir": Param("outdir", "string", None, None, "out", "directory-path", True, "io"),
    })
    out = write_skill._required_params(ps)
    assert "string (file path)" in out
    assert "string (directory path)" in out


def test_required_params_shows_constraints_column():
    # skill.md's two tables (Inputs, Required params) must agree: both carry constraints.
    # A required --input with a `.csv` pattern is exactly the fact an agent must not miss.
    ps = ParamSchema(title="t", description="d", params={
        "input": Param("input", "string", None, None, "ss", "file-path", True, "io",
                       pattern=r"^\S+\.csv$"),
    })
    out = write_skill._required_params(ps)
    assert "| constraints |" in out
    assert r"matches ^\S+\.csv$" in out


def test_run_invocation_omits_input_without_samplesheet():
    ps = ParamSchema(title="t", description="d", params={
        "outdir": Param("outdir", "string", None, None, "o", "directory-path", True, "io"),
    })
    nf, raw = write_skill._run_invocation("p", ps, None)
    assert "--input" not in nf and "--input" not in raw       # no samplesheet → no --input
    assert "--outdir results" in nf and nf.endswith("-profile docker")


def test_run_invocation_shows_required_without_default_only():
    ps = ParamSchema(title="t", description="d", params={
        "outdir": Param("outdir", "string", None, None, "o", "directory-path", True, "io"),
        # required, no default
        "genome": Param("genome", "string", None, None, "g", None, True, "ref"),
        # required, has default
        "step": Param("step", "string", "mapping", ("mapping", "x"), "s", None, True, "main"),
    })
    nf, raw = write_skill._run_invocation("p", ps, InputSchema(columns=()))
    assert "--genome <genome>" in nf and "--genome <genome>" in raw  # must-pass → placeholder shown
    assert "--step" not in nf  # default filled by nf-schema → omitted
    assert "--input samplesheet.csv" in nf  # samplesheet present → --input shown


def test_reference_renders_boolean_default_as_json_literal():
    # JSON booleans must render as true/false (schema-faithful), never Python True/False.
    st = SubmoduleStatus(name="p", path=Path("/x"), initialized=True, complete=True,
                         version="1.0.0", commit="abc", missing_files=())
    ps = ParamSchema(title="t", description="d", params={
        "validate_params": Param("validate_params", "boolean", True, None, "d", None, False, "g"),
    })
    out = write_skill._render_reference("p", st, ps, None)
    row = next(line for line in out.splitlines() if line.startswith("| `--validate-params`"))
    assert "| true |" in row and "True" not in row


# --- Value constraints: pattern/min/max/length/deprecated are captured on BOTH Param and Column
#     and rendered by ONE helper (so the two never drift apart), excluding enum (own column). ---
def test_constraints_helper_renders_all_and_excludes_enum():
    p = Param("x", "integer", None, ("a", "b"), "d", None, False, "g",
              pattern=r"^(a|b)$", minimum=1, maximum=10, min_length=2, max_length=8,
              deprecated=True)
    out = write_skill._constraints(p)
    assert r"matches ^(a\|b)$" in out  # pattern rendered, pipe escaped for the table
    assert "≥ 1" in out and "≤ 10" in out               # numeric bounds
    assert "length ≥ 2" in out and "length ≤ 8" in out  # length bounds
    assert "deprecated" in out
    assert "a, b" not in out                              # enum is NOT folded in here (own column)


def test_constraints_helper_blank_when_unconstrained():
    p = Param("x", "string", None, None, "d", None, False, "g")
    assert write_skill._constraints(p) == ""
    c = Column("x", "string", False, None, None)
    assert write_skill._constraints(c) == ""             # same helper works on Column


def test_constraints_minimum_zero_is_rendered():
    # `0` is a real bound — must use `is not None`, not truthiness, or it vanishes.
    p = Param("x", "integer", None, None, "d", None, False, "g", minimum=0)
    assert "≥ 0" in write_skill._constraints(p)


def test_load_param_schema_captures_value_constraints(tmp_path):
    (tmp_path / "nextflow_schema.json").write_text(
        '{"title": "t", "definitions": {"g": {"properties": {'
        '"reads": {"type": "string", "pattern": "^\\\\S+\\\\.csv$"}, '
        '"n": {"type": "integer", "minimum": 1, "maximum": 9}, '
        '"s": {"type": "string", "minLength": 2, "maxLength": 4}, '
        '"old": {"type": "string", "deprecated": true}}}}}')
    ps = schema.load_param_schema(tmp_path)
    assert ps.params["reads"].pattern == r"^\S+\.csv$"
    assert ps.params["n"].minimum == 1 and ps.params["n"].maximum == 9
    assert ps.params["s"].min_length == 2 and ps.params["s"].max_length == 4
    assert ps.params["old"].deprecated is True


def test_load_input_schema_captures_column_constraints(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "schema_input.json").write_text(
        '{"items": {"properties": {'
        '"cells": {"type": "integer", "minimum": 1}, '
        '"name": {"type": "string", "minLength": 1}}}}')
    cols = {c.name: c for c in schema.load_input_schema(tmp_path).columns}
    assert cols["cells"].minimum == 1  # numeric column bound captured, not dropped
    assert cols["name"].min_length == 1


def test_reference_has_constraints_column_with_real_pattern():
    st = SubmoduleStatus(name="pZ", path=Path("/x"), initialized=True, complete=True,
                         version="1.0.0", commit="abc1234", missing_files=())
    ps = ParamSchema(title="t", description="d", params={
        "input": Param("input", "string", None, None, "ss", "file-path", True, "io",
                       pattern=r"^\S+\.(csv|tsv)$"),
        "n": Param("n", "integer", None, None, "count", None, False, "io", minimum=1),
    })
    out = write_skill._render_reference("pZ", st, ps, None)
    assert "| constraints |" in out                                  # column present
    input_row = next(line for line in out.splitlines() if line.startswith("| `--input`"))
    assert r"matches ^\S+\.(csv\|tsv)$" in input_row  # pattern in the right cell, pipe escaped
    n_row = next(line for line in out.splitlines() if line.startswith("| `--n`"))
    assert "≥ 1" in n_row


# --- Two gaps verified against the pinned releases when running pipelines — detaxizer's
#     high-memory BBMAP_BBDUK step (80 GB) and circdna's schema-required run parameters. The
#     symptom→fix map must document both, the run command must not be mistaken for a preview,
#     and each documented fact must agree with its source of truth. ---
KNOWN_ISSUES = (REPO / "docs" / "known-issues.md").read_text(encoding="utf-8")


def test_known_issues_documents_detaxizer_bbduk_memory_workaround():
    # The 80 GB process_high request aborts on a small host; the documented fix is a per-process
    # memory cap passed through --config (the mechanism nfclaw already supports).
    assert "BBMAP_BBDUK" in KNOWN_ISSUES and "detaxizer" in KNOWN_ISSUES
    assert "exceeds available memory" in KNOWN_ISSUES        # the recognisable Nextflow symptom
    assert "--config" in KNOWN_ISSUES                        # the supported knob
    assert "withName: 'BBMAP_BBDUK'" in KNOWN_ISSUES         # a concrete, targeted cap


def test_known_issues_documents_circdna_required_run_params():
    assert "`circdna`" in KNOWN_ISSUES
    assert "--input_format" in KNOWN_ISSUES and "--circle_identifier" in KNOWN_ISSUES


def test_agent_guide_states_run_is_real_with_check_for_dry_run():
    # Pre-empt the "runner defaults to -preview" confusion: nfclaw run is a real run; --check is
    # the dry run. Both facts must be stated where an agent decides how to run a pipeline.
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    assert "no preview/dry-run default" in text
    assert "--check" in text


def test_circdna_required_params_match_committed_reference():
    # Scientific rigor: the run note must agree with the schema-derived reference.md, not memory.
    # reference.md is committed (not a submodule), so this always runs.
    ref = (REPO / "pipelines" / "circdna" / "reference.md").read_text(encoding="utf-8")

    def required(flag: str) -> str:
        row = next(line for line in ref.splitlines() if line.startswith(f"| `{flag}`"))
        return row.split("|")[3].strip()                     # parameter|type|required|... → cell 3

    assert required("--input-format") == "yes"
    assert required("--circle-identifier") == "yes"


# --- Input-schema faithfulness. Two generator gaps surfaced when running
#     pipelines: (a) a samplesheet's mutually-exclusive column groups (items.oneOf — bam/cram,
#     ampliseq legacy/standardized, drop's RNA inputs) were flattened into one table with the
#     choice hidden; (b) a parameter-driven pipeline that ships schema_input.json but declares no
#     `input` param (drugresponseeval) was told to pass `--input`, which the runner rejects. ---
def test_load_input_schema_captures_oneof_groups(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "schema_input.json").write_text(
        '{"items": {"properties": {"sample": {"type": "string"}, '
        '"bam": {"type": "string"}, "cram": {"type": "string"}}, '
        '"required": ["sample"], '
        '"oneOf": [{"required": ["bam"]}, {"required": ["cram"]}]}}')
    insch = schema.load_input_schema(tmp_path)
    assert insch.one_of == (("bam",), ("cram",))


def test_load_input_schema_oneof_empty_when_absent(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "schema_input.json").write_text(
        '{"items": {"properties": {"sample": {"type": "string"}}, "required": ["sample"]}}')
    assert schema.load_input_schema(tmp_path).one_of == ()


def test_inputs_section_surfaces_oneof_mutually_exclusive_groups():
    # createpanelrefs-style: one always-required column + a bam-xor-cram choice.
    insch = InputSchema(columns=(
        Column("sample", "string", True, None, None),
        Column("bam", "string", False, r"^\S+\.bam$", "file-path"),
        Column("cram", "string", False, r"^\S+\.cram$", "file-path"),
    ), one_of=(("bam",), ("cram",)))
    out = write_skill._inputs_section(insch)
    assert "exactly one" in out.lower() and "mutually-exclusive" in out
    assert "`bam`" in out and "`cram`" in out          # the exclusive columns are listed as groups
    assert "sample,bam" in out and "sample,cram" in out  # one valid header per group, with `sample`
    assert "sample,bam,cram" not in out                  # never a single all-columns header


def test_inputs_section_oneof_combines_base_required_with_each_group():
    # ampliseq-style: no always-required column, two multi-column groups, no single header.
    insch = InputSchema(columns=(
        Column("sampleID", "string", False, None, None),
        Column("forwardReads", "string", False, None, "file-path"),
        Column("sample", "string", False, None, None),
        Column("fastq_1", "string", False, None, "file-path"),
    ), one_of=(("sampleID", "forwardReads"), ("sample", "fastq_1")))
    out = write_skill._inputs_section(insch)
    assert "sampleID,forwardReads" in out and "sample,fastq_1" in out
    assert "sampleID,forwardReads,sample,fastq_1" not in out   # never mixes the two formats


def test_inputs_section_without_oneof_keeps_single_exact_header():
    insch = InputSchema(columns=(
        Column("sample", "string", True, None, None),
        Column("fastq_1", "string", True, None, "file-path"),
    ))
    out = write_skill._inputs_section(insch)
    assert "sample,fastq_1" in out
    assert "exactly one" not in out.lower() and "mutually-exclusive" not in out


def test_inputs_section_surfaces_input_pattern_for_multi_format_samplesheets():
    # Sarek accepts csv/tsv/yaml/yml/json at the `--input` parameter level, so the generated skill
    # must not leave agents with a CSV-only mental model.
    insch = InputSchema(columns=(
        Column("patient", "string", True, None, None),
        Column("sample", "string", True, None, None),
    ))
    ps = ParamSchema(title="t", description="d", params={
        "input": Param("input", "string", None, None, "ss", "file-path", False, "io",
                       pattern=r"^\S+\.(csv|tsv|yaml|yml|json)$"),
    })
    out = write_skill._inputs_section(insch, ps)
    assert r"`--input` must match `^\S+\.(csv|tsv|yaml|yml|json)$`." in out
    assert "For tabular CSV/TSV input" in out


def test_inputs_section_surfaces_dependent_required_rules():
    insch = InputSchema(
        columns=(
            Column("patient", "string", True, None, None),
            Column("sample", "string", True, None, None),
            Column("lane", "integer or string", False, r"^\S+$", None),
            Column("fastq_1", "string", False, None, "file-path"),
            Column("fastq_2", "string", False, None, "file-path"),
            Column("bam", "string", False, None, "file-path"),
        ),
        dependent_required=(("fastq_2", ("fastq_1",)),),
        any_of_dependent_required=(
            (("lane", ("fastq_1",)),),
            (("lane", ("bam",)),),
        ),
    )
    out = write_skill._inputs_section(insch)
    assert "Additional row validation rules" in out
    assert "When `fastq_2` is set, also provide `fastq_1`." in out
    assert "At least one of these conditional requirements must be satisfied" in out
    assert "`fastq_1` when `lane` is set" in out and "`bam` when `lane` is set" in out


def test_render_skips_input_when_pipeline_has_no_input_param(tmp_path):
    # A parameter-driven pipeline (e.g. drugresponseeval) ships assets/schema_input.json but
    # declares no `input` param. The skill must NOT tell the agent to pass --input, and must show
    # the schema-required parameters instead.
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "schema_input.json").write_text(
        '{"items": {"properties": {"col": {"type": "string"}}, "required": ["col"]}}')
    (tmp_path / "nextflow_schema.json").write_text(
        '{"title": "t", "definitions": {"io": {"properties": {'
        '"outdir": {"type": "string", "format": "directory-path"}, '
        '"dataset_name": {"type": "string"}}, "required": ["outdir", "dataset_name"]}}}')
    st = SubmoduleStatus(name="p", path=tmp_path, initialized=True, complete=True,
                         version="1.0.0", commit="abc", missing_files=())
    skill, _ = write_skill.render_status(st)
    assert "--input" not in skill                       # no samplesheet flag for a param-driven run
    assert "does not use a samplesheet" in skill
    assert "has_samplesheet: false" in skill
    assert "--dataset-name <dataset_name>" in skill     # required-without-default → placeholder


def test_render_shows_input_when_pipeline_has_input_param(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "schema_input.json").write_text(
        '{"items": {"properties": {"sample": {"type": "string"}}, "required": ["sample"]}}')
    (tmp_path / "nextflow_schema.json").write_text(
        '{"title": "t", "definitions": {"io": {"properties": {'
        '"input": {"type": "string", "format": "file-path"}, '
        '"outdir": {"type": "string", "format": "directory-path"}}, '
        '"required": ["input", "outdir"]}}}')
    st = SubmoduleStatus(name="p", path=tmp_path, initialized=True, complete=True,
                         version="1.0.0", commit="abc", missing_files=())
    skill, _ = write_skill.render_status(st)
    assert "--input samplesheet.csv" in skill
    assert "has_samplesheet: true" in skill


def test_detaxizer_bbduk_memory_note_matches_pinned_upstream():
    # Source-of-truth check, skipped when the submodule isn't initialised (the pytest CI job checks
    # out without submodules): the documented 80 GB + process_high label come from the pinned
    # detaxizer release, so confirm the doc matches upstream whenever upstream is present.
    up = REPO / "pipelines" / "detaxizer" / "upstream"
    bbduk = up / "modules" / "nf-core" / "bbmap" / "bbduk" / "main.nf"
    base = up / "conf" / "base.config"
    if not (bbduk.exists() and base.exists()):
        pytest.skip("detaxizer submodule not initialised")
    assert "label 'process_high'" in bbduk.read_text(encoding="utf-8")
    # the process_high tier (not process_high_memory) sizes memory at 80.GB
    assert re.search(r"withLabel:process_high\b.*?80\.GB",
                     base.read_text(encoding="utf-8"), re.S)


def test_known_issues_documents_coproid_genome_sheet_and_required_dbs():
    # coproid's mutual exclusivity lives in a SECONDARY samplesheet (--genome_sheet /
    # schema_genomes.json) the generator doesn't render, so the symptom→fix map must cover it.
    assert "`coproid`" in KNOWN_ISSUES and "--genome_sheet" in KNOWN_ISSUES
    assert "igenome" in KNOWN_ISSUES and "fasta" in KNOWN_ISSUES
    assert "--kraken2_db" in KNOWN_ISSUES


def _assert_input_choices_documented(name, tree, skill):
    # Read the selected release's raw schema independently of the column-group loader.
    # A release may add or remove groups (ampliseq 3.0.0 removed its legacy input format).
    ref = inputs.samplesheet_schema(tree)
    data = json.loads((tree / ref).read_text()) if ref else {}
    groups = [branch["required"] for branch in data.get("items", {}).get("oneOf", [])
              if isinstance(branch, dict) and branch.get("required")]
    section = skill.split("## Inputs\n", 1)[1].split("\n## ", 1)[0]
    assert ("mutually-exclusive column groups" in section) == bool(groups), name
    if groups:
        block = section.split("mutually-exclusive column groups", 1)[1].split("\n", 1)[1]
        lines = block.split("\n\n", 1)[0].splitlines()
        documented = [tuple(re.findall(r"`([^`]+)`", line)) for line in lines
                      if line.startswith("- ")]
        assert sorted(documented) == sorted(tuple(group) for group in groups), name


def test_generated_skills_surface_input_oneof_exclusivity():
    checked = 0
    for pipeline in sorted((REPO / "pipelines").iterdir()):
        tree = pipeline / "upstream"
        if not (tree / "nextflow_schema.json").is_file():
            continue
        _assert_input_choices_documented(pipeline.name, tree,
                                        (pipeline / "skill.md").read_text())
        checked += 1
    if not checked:
        pytest.skip("requires initialized pipeline schemas; the drift job initializes all of them")


def test_committed_skills_show_the_pinned_column_groups():
    # Runs without submodules: the committed skill.md for every pipeline whose --input schema has
    # mutually-exclusive column groups must surface the choice (not flatten it into one table).
    # (ampliseq had such groups until 3.0.0 removed its legacy sampleID/forwardReads format.)
    for name in ("createpanelrefs", "drop"):
        skill = (REPO / "pipelines" / name / "skill.md").read_text(encoding="utf-8")
        assert "mutually-exclusive column groups" in skill, name
    cpr = (REPO / "pipelines" / "createpanelrefs" / "skill.md").read_text(encoding="utf-8")
    assert "sample,bam" in cpr and "sample,cram" in cpr                  # one header per group


def test_generated_input_choice_gate_tracks_a_release_schema_change(tmp_path):
    tree = tmp_path / "pipelines" / "fixture" / "upstream"
    tree.mkdir(parents=True)
    (tree / "assets").mkdir()
    (tree / "main.nf").write_text("workflow {}\n")
    (tree / "nextflow.config").write_text("manifest.name = 'nf-core/fixture'\n")
    (tree / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "file-path", "schema": "assets/schema_input.json"}}}))
    path = tree / "assets/schema_input.json"
    props = {name: {"type": "string"} for name in ("sampleID", "forwardReads", "sample", "fastq_1")}
    path.write_text(json.dumps({"items": {"properties": props, "oneOf": [
        {"required": ["sampleID", "forwardReads"]}, {"required": ["sample", "fastq_1"]}]}}))
    skill_path, _ = write_skill.generate("fixture", pipelines_dir=tree.parents[1])
    legacy = skill_path.read_text()
    _assert_input_choices_documented("fixture", tree, legacy)
    with pytest.raises(AssertionError):
        _assert_input_choices_documented("fixture", tree, legacy.replace(
            "- `sampleID`, `forwardReads`", "- `sampleID`"))
    # Removing one alternative must reject its obsolete documentation even while another
    # mutually exclusive group remains in the selected schema.
    path.write_text(json.dumps({"items": {"properties": props, "oneOf": [
        {"required": ["sample", "fastq_1"]}]}}))
    with pytest.raises(AssertionError):
        _assert_input_choices_documented("fixture", tree, legacy)
    write_skill.generate("fixture", pipelines_dir=tree.parents[1])
    _assert_input_choices_documented("fixture", tree, skill_path.read_text())
    # The next release removes the legacy fields and makes the standard ones required.
    path.write_text(json.dumps({"items": {"properties": {name: props[name]
        for name in ("sample", "fastq_1")}, "required": ["sample", "fastq_1"]}}))
    with pytest.raises(AssertionError):
        _assert_input_choices_documented("fixture", tree, legacy)
    write_skill.generate("fixture", pipelines_dir=tree.parents[1])
    _assert_input_choices_documented("fixture", tree, skill_path.read_text())


def test_drugresponseeval_skill_has_no_input_flag():
    # drugresponseeval declares no `input` param; its committed skill must not tell the agent to
    # pass --input (the runner rejects unknown flags and would fail fast).
    skill = (REPO / "pipelines" / "drugresponseeval" / "skill.md").read_text(encoding="utf-8")
    assert "--input" not in skill
    assert "does not use a samplesheet" in skill


def test_coproid_genome_sheet_oneof_matches_pinned_upstream():
    # Source-of-truth check (skips without the submodule): the documented igenome-xor-fasta choice
    # is the real schema_genomes.json oneOf.
    sg = REPO / "pipelines" / "coproid" / "upstream" / "assets" / "schema_genomes.json"
    if not sg.exists():
        pytest.skip("coproid submodule not initialised")
    groups = [tuple(b.get("required", []))
              for b in json.loads(sg.read_text(encoding="utf-8"))["items"]["oneOf"]]
    assert ("igenome",) in groups and ("fasta",) in groups


# --- Demo-run failures: three verified additions to the symptom→fix map —
#     marsseq (NF 26 parser → --nxf-ver 25.10.2), lsmquant (declares !>=25.10.4 → --nxf-ver
#     25.10.4) and metapep (demo's DOWNLOAD_PROTEINS fetches from NCBI Entrez via a secret). Each
#     is checked against the doc and the pinned upstream (source-of-truth tests skip
#     without it). ---
def test_known_issues_documents_marsseq_lsmquant_metapep():
    assert "`marsseq`" in KNOWN_ISSUES and "`lsmquant`" in KNOWN_ISSUES
    assert "`metapep`" in KNOWN_ISSUES
    assert "--nxf-ver 25.10.4" in KNOWN_ISSUES          # lsmquant/funcscan newer-engine pin
    assert "NCBI_EMAIL" in KNOWN_ISSUES                 # metapep secret


def test_known_issues_documents_sarek_input_false_schema_conflict():
    assert "`sarek` 3.9.0" in KNOWN_ISSUES
    assert "--input false" in KNOWN_ISSUES
    assert "--build_only_index" in KNOWN_ISSUES
    assert "omit `--input`" in KNOWN_ISSUES


def test_known_issues_documents_sarek_test_profile_not_extra_config():
    assert "`sarek` 3.9.0" in KNOWN_ISSUES
    assert "--config pipelines/sarek/upstream/conf/test.config" in KNOWN_ISSUES
    assert "-profile test,docker" in KNOWN_ISSUES
    assert "S3 iGenomes" in KNOWN_ISSUES
    assert "custom samplesheet" in KNOWN_ISSUES


def test_marsseq_has_nf26_blocking_check_max_in_pinned_config():
    cfg = REPO / "pipelines" / "marsseq" / "upstream" / "nextflow.config"
    if not cfg.exists():
        pytest.skip("marsseq submodule not initialised")
    text = cfg.read_text(encoding="utf-8")
    assert "def check_max(obj, type)" in text           # the NF 26 strict-parser blocker
    assert "!>=23.04.0" in text                          # old engine req → 25.10.2 satisfies it


def test_lsmquant_requires_newer_engine_in_pinned_schema():
    cfg = REPO / "pipelines" / "lsmquant" / "upstream" / "nextflow.config"
    if not cfg.exists():
        pytest.skip("lsmquant submodule not initialised")
    assert "!>=25.10.4" in cfg.read_text(encoding="utf-8")


# --- Setup and flow. (1) The `nfclaw` console script fails with
#     ModuleNotFoundError when the editable install can't be found (a space in the install path
#     breaks site's path hook, or a wrong-Python install) — documented with the `python -m runner`
#     fallback. (2) `--check` must not be blocked by a non-empty outdir (a real-run-only guard). ---
def test_known_issues_documents_module_not_found_and_python_m_fallback():
    assert "ModuleNotFoundError" in KNOWN_ISSUES and "No module named 'runner'" in KNOWN_ISSUES
    assert "python3 -m runner" in KNOWN_ISSUES          # the no-install fallback that always works
    assert "space-free path" in KNOWN_ISSUES


def test_preflight_check_only_signature_skips_empty_outdir_guard(tmp_path, monkeypatch):
    # The guard is threaded through check_only, not hard-coded, so --check can validate over an
    # existing results dir. (Behaviour is covered end-to-end in tests/test_orchestration.py.)
    assert "check_only" in inspect.signature(preflight.check_environment).parameters
    monkeypatch.setattr(preflight.shutil, "which", lambda x: "/usr/bin/" + x)
    out = tmp_path / "out"
    out.mkdir()
    (out / "previous_result.txt").write_text("x")
    st = SubmoduleStatus("p", tmp_path / "up", True, True, "1.0.0", "abc", ())

    def issues(check_only):
        return preflight.check_environment(profile="singularity", output_dir=out, submodule=st,
                                           repo_root=tmp_path / "repo", resume=False,
                                           check_only=check_only)
    assert any("is not empty" in i for i in issues(check_only=False))
    assert not any("is not empty" in i for i in issues(check_only=True))


def test_metapep_demo_downloads_from_ncbi_via_secret_in_pinned_upstream():
    mod = (REPO / "pipelines" / "metapep" / "upstream" / "modules" / "local"
           / "download_proteins.nf")
    if not mod.exists():
        pytest.skip("metapep submodule not initialised")
    text = mod.read_text(encoding="utf-8")
    assert 'secret "NCBI_EMAIL"' in text and "download_proteins_entrez.py" in text
