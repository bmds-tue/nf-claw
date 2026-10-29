"""The shipped handoff rules (handoffs/): they parse, name library pipelines, and fit the pinned
schemas. The fit needs initialized submodules; the drift gate (CI) has them."""
import csv
import json
from pathlib import Path

import pytest

from runner import handoff, schema, submodule
from runner.errors import NfclawError

ROOT = Path(__file__).resolve().parent.parent
RULES = handoff.load_registry(ROOT)


def _tree(name):
    st = submodule.resolve(name, ROOT / "pipelines")
    if not st.complete:
        pytest.skip(f"{name} submodule not initialized")
    return st.path


def test_registry_parses_and_names_library_pipelines():
    assert ("fetchngs", "rnaseq") in RULES
    names = {d.name for d in (ROOT / "pipelines").iterdir() if d.is_dir()}
    for up, down in RULES:
        assert up in names and down in names, f"handoffs/{up}/{down}.json names an unknown pipeline"
        assert RULES[(up, down)].description, f"handoffs/{up}/{down}.json has no description"


@pytest.mark.parametrize("edge", sorted(RULES), ids=lambda e: f"{e[0]}->{e[1]}")
def test_every_rule_fits_the_pinned_schemas(edge):
    up, down = (_tree(n) for n in edge)
    assert handoff.check_rule(RULES[edge], up, down) == []


def test_fetchngs_rules_set_their_own_target_from_fetchngs_enum():
    # The direct handoffs rely on fetchngs's --nf-core-pipeline; its schema enum is the authority.
    enum = schema.load_param_schema(_tree("fetchngs")).params["nf_core_pipeline"].enum
    targets = [down for (up, down) in RULES if up == "fetchngs"]
    assert targets
    for down in targets:
        assert RULES[("fetchngs", down)].upstream_params == {"nf_core_pipeline": down}
        assert down in enum


@pytest.mark.parametrize("upstream", ["fetchngs", "detaxizer"])
def test_mag_handoff_keeps_different_samples_separate(library, finished_run, tmp_path, upstream):
    """Grouping all samples together would silently enable pooled binning in MAG."""
    root = library("mini")
    down = root / "pipelines/mini/upstream"
    schema_path = down / "assets/schema_input.json"
    sheet_schema = json.loads(schema_path.read_text())
    sheet_schema["items"]["properties"] = {
        "sample": {"type": "string"}, "group": {"type": ["string", "integer"]},
        "run": {"type": "string"},
        "short_reads_1": {"type": "string", "format": "file-path"},
        "short_reads_2": {"type": "string", "format": "file-path"},
        "short_reads_platform": {"type": "string"},
        "long_reads": {"type": "string", "format": "file-path"},
        "long_reads_platform": {"type": "string"},
    }
    sheet_schema["items"]["required"] = ["sample", "group", "short_reads_1"]
    schema_path.write_text(json.dumps(sheet_schema))
    rule = RULES[(upstream, "mag")]
    source = rule.params["input"].spec["samplesheet"]
    if upstream == "fetchngs":
        text = ("sample,fastq_1,fastq_2,group,short_reads_platform,run_accession,"
                "instrument_platform\n"
                "A,{outdir}/A_1.fastq.gz,,0,ILLUMINA,run1,ILLUMINA\n"
                "A,{outdir}/A_2.fastq.gz,,0,ILLUMINA,run2,ILLUMINA\n"
                "B,{outdir}/B_1.fastq.gz,,0,ILLUMINA,run3,ILLUMINA\n")
    else:
        text = ("sample,run,group,short_reads_1,short_reads_2,long_reads\n"
                "A,run1,,{outdir}/A_1.fastq.gz,,\n"
                "A,run2,,{outdir}/A_2.fastq.gz,,\n"
                "B,run3,,{outdir}/B_1.fastq.gz,,\n")
    up = finished_run(tmp_path / "up", {source: text, "A_1.fastq.gz": "a1",
                                       "A_2.fastq.gz": "a2", "B_1.fastq.gz": "b1"})
    result = handoff.materialize(rule, upstream_outdir=up, downstream_tree=down,
                                dest=tmp_path / "handoff")
    with Path(result.params["input"]).open() as fh:
        rows = list(csv.DictReader(fh))
    assert [(row["sample"], row["group"]) for row in rows] == [("A", "A"), ("A", "A"), ("B", "B")]


# mag 5.5.0's platform columns: the short-read enum mirrors ENA's instrument_platform names, and the
# long-read platform picks the long-read preprocessing and assembler mode.
_MAG_PLATFORMS = {
    "sample": {"type": "string"}, "group": {"type": ["string", "integer"]},
    "run": {"type": ["string", "integer"]},
    "short_reads_1": {"type": "string", "format": "file-path"},
    "short_reads_2": {"type": "string", "format": "file-path"},
    "short_reads_platform": {"type": "string", "enum": [
        "ILLUMINA", "BGISEQ", "LS454", "ION_TORRENT", "DNBSEQ", "ELEMENT", "ULTIMA",
        "VELA_DIAGNOSTICS", "GENAPSYS", "GENEMIND", "TAPESTRI"]},
    "long_reads": {"type": "string", "format": "file-path"},
    "long_reads_platform": {"type": "string", "enum": [
        "OXFORD_NANOPORE", "OXFORD_NANOPORE_HQ", "PACBIO_CLR", "PACBIO_HIFI"]},
}


def _mag_like(library):
    down = library("mini") / "pipelines/mini/upstream"
    path = down / "assets/schema_input.json"
    sheet_schema = json.loads(path.read_text())
    sheet_schema["items"]["properties"] = _MAG_PLATFORMS
    sheet_schema["items"]["required"] = ["sample", "group"]
    sheet_schema["items"]["dependentRequired"] = {"short_reads_1": ["short_reads_platform"],
                                                  "long_reads": ["long_reads_platform"]}
    path.write_text(json.dumps(sheet_schema))
    return down


def test_fetchngs_mag_platform_is_the_runs_ena_platform(library, finished_run, tmp_path):
    """fetchngs labels every run ILLUMINA; ENA's instrument_platform says what produced it."""
    down, rule = _mag_like(library), RULES[("fetchngs", "mag")]
    header = ("sample,fastq_1,fastq_2,group,short_reads_platform,long_reads_platform,run_accession,"
              "instrument_platform\n")
    up = finished_run(tmp_path / "up", {"samplesheet/samplesheet.csv": header
                      + "A,{outdir}/A_1.fastq.gz,{outdir}/A_2.fastq.gz,,ILLUMINA,,run1,ILLUMINA\n"
                      + "B,{outdir}/B_1.fastq.gz,{outdir}/B_2.fastq.gz,,ILLUMINA,,run2,BGISEQ\n",
                      "A_1.fastq.gz": "a1", "A_2.fastq.gz": "a2", "B_1.fastq.gz": "b1",
                      "B_2.fastq.gz": "b2"})
    result = handoff.materialize(rule, upstream_outdir=up, downstream_tree=down,
                                 dest=tmp_path / "handoff")
    with Path(result.params["input"]).open() as fh:
        rows = list(csv.DictReader(fh))
    assert [(r["sample"], r["short_reads_platform"]) for r in rows] == [("A", "ILLUMINA"),
                                                                        ("B", "BGISEQ")]
    # A long-read run in fetchngs's short-read columns is refused, not assembled as short reads.
    ont = finished_run(tmp_path / "ont", {"samplesheet/samplesheet.csv": header
                       + "C,{outdir}/C.fastq.gz,,,ILLUMINA,,run3,OXFORD_NANOPORE\n",
                       "C.fastq.gz": "c"})
    with pytest.raises(NfclawError, match="OXFORD_NANOPORE"):
        handoff.materialize(rule, upstream_outdir=ont, downstream_tree=down,
                            dest=tmp_path / "handoff-ont")


def test_detaxizer_mag_never_assumes_a_long_read_platform(library, finished_run, tmp_path):
    down, rule = _mag_like(library), RULES[("detaxizer", "mag")]
    header = "sample,run,group,short_reads_1,short_reads_2,long_reads\n"
    files = {"A_1.fastq.gz": "a1", "A_2.fastq.gz": "a2", "A_long.fastq.gz": "al"}
    short = finished_run(tmp_path / "short", {"downstream_samplesheets/mag-pe.csv": header
                         + "A,A,,{outdir}/A_1.fastq.gz,{outdir}/A_2.fastq.gz,\n", **files})
    result = handoff.materialize(rule, upstream_outdir=short, downstream_tree=down,
                                 dest=tmp_path / "handoff")
    with Path(result.params["input"]).open() as fh:
        (row,) = csv.DictReader(fh)
    assert (row["short_reads_platform"], row["long_reads_platform"]) == ("ILLUMINA", "")
    hybrid = finished_run(tmp_path / "hybrid", {"downstream_samplesheets/mag-pe.csv": header
                          + "A,A,,{outdir}/A_1.fastq.gz,{outdir}/A_2.fastq.gz,"
                            "{outdir}/A_long.fastq.gz\n", **files})
    with pytest.raises(NfclawError, match="'long_reads' requires 'long_reads_platform'"):
        handoff.materialize(rule, upstream_outdir=hybrid, downstream_tree=down,
                            dest=tmp_path / "handoff-hybrid")


def test_detaxizer_mag_refuses_samples_written_to_its_single_end_sheet(library, finished_run,
                                                                      tmp_path):
    """detaxizer writes samples without a second short-read file (single-end, or long reads only)
    to mag-se.csv beside mag-pe.csv, since mag cannot take both in one run. The rule hands over
    mag-pe.csv, so those samples were left out of mag without a word."""
    down, rule = _mag_like(library), RULES[("detaxizer", "mag")]
    header = "sample,run,group,short_reads_1,short_reads_2,long_reads\n"
    files = {"A_1.fastq.gz": "a1", "A_2.fastq.gz": "a2", "B_1.fastq.gz": "b1",
             "downstream_samplesheets/mag-pe.csv":
                 header + "A,A,0,{outdir}/A_1.fastq.gz,{outdir}/A_2.fastq.gz,\n"}
    paired = finished_run(tmp_path / "paired", files)
    result = handoff.materialize(rule, upstream_outdir=paired, downstream_tree=down,
                                 dest=tmp_path / "handoff")
    with Path(result.params["input"]).open() as fh:
        assert [row["sample"] for row in csv.DictReader(fh)] == ["A"]
    mixed = finished_run(tmp_path / "mixed", {**files, "downstream_samplesheets/mag-se.csv":
                                              header + "B,B,0,{outdir}/B_1.fastq.gz,,\n"})
    with pytest.raises(NfclawError, match=r"downstream_samplesheets/mag-se.csv also holds 1 "
                       r"row\(s\) \(B\)"):
        handoff.materialize(rule, upstream_outdir=mixed, downstream_tree=down,
                            dest=tmp_path / "handoff-mixed")


def test_bamtofastq_rnaseq_refuses_single_end_conversions_beside_paired_ones(finished_run,
                                                                            tmp_path):
    """bamtofastq 2.2.1's own no_bai test converts test and test2 (paired-end) with test3
    (single-end) in one run, publishing exactly these files under reads/. The rule's rows pattern
    describes the paired files only, so test3 was left out of rnaseq without a word."""
    rule, down = RULES[("bamtofastq", "rnaseq")], _tree("rnaseq")
    paired = {f"reads/{s}_{r}.merged.fastq.gz": f"{s}{r}"
              for s in ("test", "test2") for r in (1, 2)}
    up = finished_run(tmp_path / "paired", paired)
    result = handoff.materialize(rule, upstream_outdir=up, downstream_tree=down,
                                 dest=tmp_path / "handoff")
    with Path(result.params["input"]).open() as fh:
        rows = list(csv.DictReader(fh))
    assert sorted((r["sample"], Path(r["fastq_2"]).name) for r in rows) == [
        ("test", "test_2.merged.fastq.gz"), ("test2", "test2_2.merged.fastq.gz")]
    mixed = finished_run(tmp_path / "mixed", {**paired, "reads/test3_other.fq.gz": "test3"})
    with pytest.raises(NfclawError, match="reads/test3_other.fq.gz"):
        handoff.materialize(rule, upstream_outdir=mixed, downstream_tree=down,
                            dest=tmp_path / "handoff-mixed")


@pytest.mark.parametrize("down", ["rnaseq", "atacseq", "sarek", "metatdenovo", "viralrecon"])
def test_fetchngs_short_read_handoffs_refuse_other_platforms(library, finished_run, tmp_path, down):
    """fetchngs's own test accessions include ABI_SOLID (colour-space) and CAPILLARY runs."""
    rule = RULES[("fetchngs", down)]
    allowed = rule.params["input"].spec["allowed_values"]["instrument_platform"]
    assert "ILLUMINA" in allowed and not {"OXFORD_NANOPORE", "PACBIO_SMRT", "ABI_SOLID",
                                          "CAPILLARY"} & set(allowed)
    root = library("mini")
    mini = root / "pipelines/mini/upstream"
    up = finished_run(tmp_path / "up", {
        "samplesheet/samplesheet.csv": "sample,fastq_1,fastq_2,patient,run_accession,"
                                       "instrument_platform\n"
                                       "A,{outdir}/A_1.fastq.gz,,P1,SRR1,ABI_SOLID\n",
        "A_1.fastq.gz": "a"})
    with pytest.raises(NfclawError, match="row 2 \\(A: ABI_SOLID\\)"):
        handoff.materialize(rule, upstream_outdir=up, downstream_tree=mini, dest=tmp_path / "h")
