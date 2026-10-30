"""Samplesheet generation from data files (runner.sheetgen): schema roles, detection, discovery,
sample and mate detection, assignments, integrity rules and the written sheet."""
import csv
import gzip
import importlib
import io
import os
import time
from pathlib import Path

import pytest

import sheetgen_schemas as S
from runner import samplesheet, sheetgen
from runner import schema as schema_mod
from runner.errors import ErrorCode, NfclawError


def fq(path: Path, *ids: str, gz: bool | None = None) -> Path:
    """A FastQ file whose records carry `ids` (gzip-compressed when the name ends in .gz)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(f"@{i}\nACGT\n+\nIIII\n" for i in ids).encode()
    if gz if gz is not None else path.name.endswith(".gz"):
        path.write_bytes(gzip.compress(text, mtime=0))
    else:
        path.write_bytes(text)
    return path


def pair(directory: Path, r1: str, r2: str,
         read: str = "M1:1:FC:1:1101:100:200") -> tuple[Path, Path]:
    """Mates: the same read name, as Illumina writes it (the read number follows a space)."""
    return (fq(directory / r1, f"{read} 1:N:0:ACGT"), fq(directory / r2, f"{read} 2:N:0:ACGT"))


def plan_of(tmp_path, spec, empty=frozenset()):
    up = S.make_pipeline(tmp_path, spec)
    sheet = schema_mod.load_input_schema(up)
    param = schema_mod.load_param_schema(up).params["input"]
    return sheetgen.plan(sheet, param, empty)


def gen(tmp_path, spec, values, assignments=None, outdir=None, pipeline="pipe"):
    up = S.make_pipeline(tmp_path, spec, pipeline)
    source = sheetgen.detect([str(v) for v in values] if len(values) > 1 else str(values[0]), up)
    assert source is not None
    return sheetgen.generate(source, up, pipeline=pipeline, assignments=assignments or {},
                             outdir=outdir or tmp_path / "results", work_dir=tmp_path / "work")


def rows(generated) -> list[dict]:
    delimiter = "\t" if generated.suffix == ".tsv" else ","
    return list(csv.DictReader(io.StringIO(generated.text), delimiter=delimiter))


def refused(tmp_path, spec, values, assignments=None, **kw) -> NfclawError:
    with pytest.raises(NfclawError) as err:
        gen(tmp_path, spec, values, assignments, **kw)
    return err.value


# --- what the schema says: column roles -------------------------------------------------------

def test_plan_reads_identity_and_other_typed_columns(tmp_path):
    p = plan_of(tmp_path, S.RNASEQ)
    assert p.problem is None
    assert p.id_column == "sample"
    assert p.reads == ("fastq_1", "fastq_2")
    assert p.data_columns == ("genome_bam",)
    assert p.lane_column is None and p.suffix == ".csv"


def test_plan_finds_a_pair_whose_partner_pattern_lives_in_anyof(tmp_path):
    p = plan_of(tmp_path, S.ATACSEQ)
    assert p.reads == ("fastq_1", "fastq_2")
    # An integer column's digits-only pattern is not a file type.
    assert "replicate" not in p.data_columns


def test_plan_lane_and_identity_preference(tmp_path):
    p = plan_of(tmp_path, S.SAREK)
    assert p.id_column == "sample" and p.lane_column == "lane"
    assert p.reads == ("fastq_1", "fastq_2")
    assert set(p.data_columns) == {"cram", "crai", "bam", "bai", "vcf"}


def test_plan_refuses_to_choose_between_read_groups(tmp_path):
    p = plan_of(tmp_path, S.MAG)
    assert p.reads == () and "--sheet-set long_reads=" in p.problem
    chosen = plan_of(tmp_path, S.MAG, frozenset({"long_reads"}))
    assert chosen.problem is None and chosen.reads == ("short_reads_1", "short_reads_2")
    long_only = plan_of(tmp_path, S.MAG, frozenset({"short_reads_1", "short_reads_2"}))
    assert long_only.reads == ("long_reads",)


def test_plan_single_read_column_and_no_reads(tmp_path):
    assert plan_of(tmp_path, S.SCNANOSEQ).reads == ("fastq",)
    p = plan_of(tmp_path, S.CREATEPANELREFS)
    assert p.problem is None and p.reads == ()
    assert p.data_columns == ("bam", "bai", "cram", "crai")


def test_plan_without_any_file_type_or_writable_format(tmp_path):
    assert "declares no file type" in plan_of(tmp_path, S.AIRRFLOW).problem
    assert plan_of(tmp_path, S.DROP).suffix == ".tsv"
    yaml_only = dict(S.RNASEQ, input=dict(S.RNASEQ["input"], pattern="^\\S+\\.ya?ml$"))
    assert "CSV or TSV" in plan_of(tmp_path, yaml_only).problem


# --- when --input names data files -------------------------------------------------------------

def test_detect_leaves_samplesheets_and_plain_values_alone(tmp_path):
    up = S.make_pipeline(tmp_path, S.RNASEQ)
    sheet = tmp_path / "sheet.csv"
    sheet.write_text("sample,fastq_1,strandedness\n")
    for value in (str(sheet), "https://x/sheet.csv", "false", "", str(tmp_path / "absent.csv"),
                  None, 3):
        assert sheetgen.detect(value, up) is None
    # A single file that matches no column is not taken for data: the samplesheet check explains
    # an .xlsx handed in by mistake better than "no file matches".
    (tmp_path / "book.xlsx").write_bytes(b"PK")
    assert sheetgen.detect(str(tmp_path / "book.xlsx"), up) is None


def test_detect_directory_glob_file_and_list(tmp_path, monkeypatch):
    up = S.make_pipeline(tmp_path, S.RNASEQ)
    data = tmp_path / "data"
    a1, a2 = pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    monkeypatch.chdir(tmp_path)
    assert sheetgen.detect("data", up).values == (str(data),)
    assert sheetgen.detect("data/*_R{1,2}.fastq.gz", up).values == (
        str(data / "*_R{1,2}.fastq.gz"),)
    assert sheetgen.detect(str(a1), up).values == (str(a1),)
    source = sheetgen.detect(["data/A_R1.fastq.gz", str(a2)], up)
    assert source.values == (str(a1), str(a2)) and source.sheet == "assets/schema_input.json"


def test_detect_keeps_the_name_of_a_linked_file(tmp_path):
    up = S.make_pipeline(tmp_path, S.RNASEQ)
    stored = fq(tmp_path / "store" / "blob123.fastq.gz", "r")
    link = tmp_path / "links" / "S1.fastq.gz"
    link.parent.mkdir()
    link.symlink_to(stored)
    assert sheetgen.detect(str(link), up).values == (str(link),)


@pytest.mark.parametrize("values, message", [
    (["{d}/A_R1.fastq.gz", "{t}/sheet.csv"], "cannot be combined"),
    (["{d}/A_R1.fastq.gz", "https://x/B_R1.fastq.gz"], "local"),
    (["{d}/A_R1.fastq.gz", "{t}/missing.fastq.gz"], "not found"),
])
def test_detect_refuses_unusable_lists(tmp_path, values, message):
    up = S.make_pipeline(tmp_path, S.RNASEQ)
    pair(tmp_path / "d", "A_R1.fastq.gz", "A_R2.fastq.gz")
    (tmp_path / "sheet.csv").write_text("x\n")
    with pytest.raises(NfclawError) as err:
        sheetgen.detect([v.format(d=tmp_path / "d", t=tmp_path) for v in values], up)
    assert message in str(err.value)


def test_detect_refuses_a_list_for_an_input_that_is_no_samplesheet(tmp_path):
    up = S.make_pipeline(tmp_path, S.NO_SHEET)
    (tmp_path / "a").mkdir()
    assert sheetgen.detect(str(tmp_path / "a"), up) is None
    with pytest.raises(NfclawError) as err:
        sheetgen.detect([str(tmp_path / "a"), str(tmp_path / "a")], up)
    assert "is not a samplesheet" in str(err.value)


# --- discovering files -------------------------------------------------------------------------

def test_directory_scan_is_recursive_skips_hidden_and_reports_unmatched(tmp_path):
    data = tmp_path / "data"
    pair(data / "run1", "A_R1.fastq.gz", "A_R2.fastq.gz")
    pair(data / "run2", "B_R1.fastq.gz", "B_R2.fastq.gz")
    fq(data / ".hidden" / "C_R1.fastq.gz", "x")
    fq(data / ".D_R1.fastq.gz", "x")
    (data / "md5sums.txt").write_text("x\n")
    g = gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"})
    assert [r["sample"] for r in rows(g)] == ["A", "B"]
    assert g.record["ignored"] == ["md5sums.txt"] and "md5sums.txt" in g.summary


def test_scan_refuses_broken_links_and_cycles(tmp_path):
    data = tmp_path / "data"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    (data / "gone.fastq.gz").symlink_to(tmp_path / "nowhere")
    assert "gone.fastq.gz" in str(refused(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))
    (data / "gone.fastq.gz").unlink()
    (data / "loop").symlink_to(data)
    assert "cycl" in str(refused(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))


def test_scan_refuses_a_directory_holding_the_output_or_work_directory(tmp_path):
    data = tmp_path / "data"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    err = refused(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"},
                  outdir=data / "results")
    assert "--outdir" in str(err) and err.code is ErrorCode.SAMPLESHEET_INVALID
    out = tmp_path / "results"
    pair(out / "fastp", "A_R1.fastq.gz", "A_R2.fastq.gz")
    err = refused(tmp_path, S.RNASEQ, [out / "fastp" / "A_R1.fastq.gz"], {"strandedness": "auto"},
                  outdir=out)
    assert "inside" in str(err)


def test_glob_with_braces_and_glob_without_match(tmp_path):
    data = tmp_path / "data"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    pair(data, "B_R1.fastq.gz", "B_R2.fastq.gz")
    g = gen(tmp_path, S.RNASEQ, [data / "A_R{1,2}.fastq.gz"], {"strandedness": "auto"})
    assert [r["sample"] for r in rows(g)] == ["A"]
    assert "matches no files" in str(refused(tmp_path, S.RNASEQ, [data / "Z*.fastq.gz"],
                                             {"strandedness": "auto"}))


# --- samples and mates -----------------------------------------------------------------------

def test_illumina_names_lanes_and_paired_rows(tmp_path):
    data = tmp_path / "data"
    pair(data, "WT_S1_L001_R1_001.fastq.gz", "WT_S1_L001_R2_001.fastq.gz", "r:1")
    pair(data, "WT_S1_L002_R1_001.fastq.gz", "WT_S1_L002_R2_001.fastq.gz", "r:2")
    pair(data, "KO_S2_L001_R1_001.fastq.gz", "KO_S2_L001_R2_001.fastq.gz", "r:3")
    g = gen(tmp_path, S.RNASEQ, [data], {"strandedness": "reverse"})
    got = rows(g)
    assert [(r["sample"], Path(r["fastq_1"]).name, Path(r["fastq_2"]).name) for r in got] == [
        ("KO", "KO_S2_L001_R1_001.fastq.gz", "KO_S2_L001_R2_001.fastq.gz"),
        ("WT", "WT_S1_L001_R1_001.fastq.gz", "WT_S1_L001_R2_001.fastq.gz"),
        ("WT", "WT_S1_L002_R1_001.fastq.gz", "WT_S1_L002_R2_001.fastq.gz")]
    assert all(Path(r["fastq_1"]).is_absolute() for r in got)
    assert g.text.splitlines()[0] == "sample,fastq_1,fastq_2,strandedness"
    assert g.record["samples"] == 2 and g.record["rows"] == 3 and g.record["paired_end"] == 3


def test_optional_columns_left_to_their_schema_defaults_are_named(tmp_path):
    # sarek's status defaults to 0: a generated sheet without it analyses every sample as normal
    # tissue, a scientific choice the caller must see before launch, not discover afterwards.
    data = tmp_path / "data"
    pair(data, "T1_S1_L001_R1_001.fastq.gz", "T1_S1_L001_R2_001.fastq.gz", "r:1")
    g = gen(tmp_path, S.SAREK, [data], {"patient": "{sample}"})
    assert "status" not in rows(g)[0] and "sex" not in rows(g)[0]
    assert g.record["implicit_defaults"] == {"sex": "NA", "status": "0"}
    assert "schema default on every row: sex = NA, status = 0" in g.summary
    up = S.make_pipeline(tmp_path / "doc", S.SAREK)
    text = sheetgen.describe(schema_mod.load_input_schema(up),
                             schema_mod.load_param_schema(up).params["input"])
    assert "Optional columns left out take their schema defaults in the pipeline: `sex` = `NA`, " \
           "`status` = `0`" in text
    # Set explicitly, the column is written and no longer implicit.
    g = gen(tmp_path / "set", S.SAREK, [data], {"patient": "{sample}", "status": "1"})
    assert rows(g)[0]["status"] == "1" and g.record["implicit_defaults"] == {"sex": "NA"}


@pytest.mark.parametrize("r1, r2, sample", [
    ("A_R1.fastq.gz", "A_R2.fastq.gz", "A"),
    ("A.R1.fq.gz", "A.R2.fq.gz", "A"),
    ("A_r1.fastq", "A_r2.fastq", "A"),
    ("A_R1_001.fastq.gz", "A_R2_001.fastq.gz", "A"),
    ("Sample_1_R1.fastq.gz", "Sample_1_R2.fastq.gz", "Sample_1"),
    ("SRR6357070_1.fastq.gz", "SRR6357070_2.fastq.gz", "SRR6357070"),
])
def test_read_tokens(tmp_path, r1, r2, sample):
    data = tmp_path / "data"
    pair(data, r1, r2)
    got = rows(gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))
    assert [(r["sample"], Path(r["fastq_1"]).name, Path(r["fastq_2"]).name) for r in got] == [
        (sample, r1, r2)]


@pytest.mark.parametrize("id1, id2", [
    ("SRR1.1 1 length=100", "SRR1.1 1 length=100"),     # fasterq-dump: both mates share the name
    ("HWI:1:1:5:7#0/1", "HWI:1:1:5:7#0/2"),              # pre-CASAVA 1.8 suffixes
    ("SRR1.1.1", "SRR1.1.2"),                            # fastq-dump --readids
])
def test_mates_are_recognised_by_read_name(tmp_path, id1, id2):
    data = tmp_path / "data"
    fq(data / "X_1.fastq.gz", id1)
    fq(data / "X_2.fastq.gz", id2)
    got = rows(gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))
    assert [r["sample"] for r in got] == ["X"] and got[0]["fastq_2"]


def test_numbered_single_end_replicates_are_not_mistaken_for_mates(tmp_path):
    # ctrl_1 and ctrl_2 are two single-end libraries: their first reads are different molecules.
    data = tmp_path / "data"
    fq(data / "ctrl_1.fastq.gz", "M1:1:FC:1:1101:100:200 1:N:0:1")
    fq(data / "ctrl_2.fastq.gz", "M1:1:FC:1:1101:900:300 1:N:0:1")
    g = gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"})
    assert [(r["sample"], r["fastq_2"]) for r in rows(g)] == [("ctrl_1", ""), ("ctrl_2", "")]
    assert g.record["single_end"] == 2


def test_explicit_mates_that_disagree_are_paired_as_named_and_said(tmp_path):
    # `_R1`/`_R2` names state the pairing. Read names that disagree are announced before launch —
    # fastqrepair exists to repair exactly such desynchronised mates — but do not undo the names.
    data = tmp_path / "data"
    fq(data / "A_R1.fastq.gz", "NS5:185:HK:1:11101:16144:1046 2:N:0:1")
    fq(data / "A_R2.fastq.gz", "NS5:185:HK:1:11101:8952:1046 2:N:0:1")
    g = gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"})
    assert rows(g)[0]["fastq_2"].endswith("A_R2.fastq.gz")
    assert any("A_R1.fastq.gz" in n and "read names differ" in n for n in g.notes)


def test_orphan_read_two_and_a_missing_mate_are_refused(tmp_path):
    data = tmp_path / "data"
    fq(data / "A_R2.fastq.gz", "r")
    assert "read 2" in str(refused(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))
    (data / "A_R2.fastq.gz").unlink()
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    fq(data / "B_R1.fastq.gz", "r")
    assert "mate" in str(refused(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))


def test_single_end_runs_and_untokened_files_mix_with_pairs(tmp_path):
    data = tmp_path / "data"
    fq(data / "A_S1_L001_R1_001.fastq.gz", "r")           # an Illumina single-end run
    fq(data / "B_S2_L001_R1_001.fastq.gz", "r")
    assert [r["sample"] for r in rows(gen(tmp_path, S.RNASEQ, [data],
                                          {"strandedness": "auto"}))] == ["A", "B"]
    other = tmp_path / "other"
    pair(other, "P_R1.fastq.gz", "P_R2.fastq.gz")
    fq(other / "SRR9.fastq.gz", "SRR9.1")                 # single-end by name: no read token
    got = rows(gen(tmp_path, S.RNASEQ, [other], {"strandedness": "auto"}))
    assert [(r["sample"], bool(r["fastq_2"])) for r in got] == [("P", True), ("SRR9", False)]


def test_index_reads_undetermined_and_read_three(tmp_path):
    data = tmp_path / "data"
    pair(data, "A_S1_L001_R1_001.fastq.gz", "A_S1_L001_R2_001.fastq.gz")
    fq(data / "A_S1_L001_I1_001.fastq.gz", "r")
    pair(data, "Undetermined_S0_L001_R1_001.fastq.gz", "Undetermined_S0_L001_R2_001.fastq.gz")
    g = gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"})
    assert [r["sample"] for r in rows(g)] == ["A"]
    assert any("index read" in n for n in g.notes) and any("Undetermined" in n for n in g.notes)
    fq(data / "A_S1_L001_R3_001.fastq.gz", "r")
    assert "read 3" in str(refused(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))


def test_empty_mates_pair_by_name_with_a_note_but_bare_numbers_need_reads(tmp_path):
    data = tmp_path / "data"
    fq(data / "A_R1.fastq.gz")
    fq(data / "A_R2.fastq.gz")
    g = gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"})
    assert rows(g)[0]["fastq_2"] and any("empty" in n for n in g.notes)
    bare = tmp_path / "bare"
    fq(bare / "X_1.fastq.gz")
    fq(bare / "X_2.fastq.gz")
    assert "empty" in str(refused(tmp_path, S.RNASEQ, [bare], {"strandedness": "auto"}))


def test_unreadable_fastq_is_refused(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "A_R1.fastq.gz").write_bytes(b"not gzip")
    (data / "A_R2.fastq.gz").write_bytes(b"not gzip")
    assert "A_R1.fastq.gz" in str(refused(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "A_R1.fastq").write_text(">fasta\nACGT\n")
    (plain / "A_R2.fastq").write_text(">fasta\nACGT\n")
    assert "not a FastQ" in str(refused(tmp_path, S.RNASEQ, [plain], {"strandedness": "auto"}))


def test_single_column_read_group_takes_no_pairs(tmp_path):
    data = tmp_path / "data"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    err = refused(tmp_path, S.SCNANOSEQ, [data], {"cell_count": "500"})
    assert "single-end" in str(err)
    single = tmp_path / "single"
    fq(single / "cells.fastq.gz", "r")
    got = rows(gen(tmp_path, S.SCNANOSEQ, [single], {"cell_count": "500"}))
    assert got == [{"sample": "cells", "fastq": str(single / "cells.fastq.gz"),
                    "cell_count": "500"}]


def test_duplicate_sample_files_are_refused(tmp_path):
    data = tmp_path / "data"
    pair(data / "a", "S_R1.fastq.gz", "S_R2.fastq.gz")
    pair(data / "b", "S_R1.fastq.gz", "S_R2.fastq.gz")
    assert "S" in str(refused(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))


# --- identities and paths are checked, never altered -------------------------------------------

def test_names_the_pipeline_cannot_take_are_refused_not_renamed(tmp_path):
    data = tmp_path / "data"
    pair(data, "-A_R1.fastq.gz", "-A_R2.fastq.gz")
    err = refused(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"})
    assert "-A_R1.fastq.gz" in str(err)
    amp = tmp_path / "amp"
    pair(amp, "1A_R1.fastq.gz", "1A_R2.fastq.gz")
    err = refused(tmp_path, S.AMPLISEQ, [amp])
    assert "1A" in str(err) and "^[a-zA-Z][a-zA-Z0-9_]+$" in str(err)


def test_a_path_holding_the_delimiter_is_refused(tmp_path):
    data = tmp_path / "da,ta"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    assert "delimiter" in str(refused(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))


# --- values nfclaw cannot take from file names -------------------------------------------------

def test_missing_required_values_are_reported_together_with_their_allowed_values(tmp_path):
    data = tmp_path / "data"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    err = refused(tmp_path, S.TAXPROFILER, [data])
    text = str(err)
    assert "'run_accession'" in text and "'instrument_platform'" in text
    assert "ILLUMINA, OXFORD_NANOPORE, PACBIO_SMRT" in text and "--sheet-set" in err.fix


def test_templates_constants_and_defaults(tmp_path):
    data = tmp_path / "data"
    pair(data, "N1_S1_L001_R1_001.fastq.gz", "N1_S1_L001_R2_001.fastq.gz", "r:1")
    pair(data, "N1_S1_L002_R1_001.fastq.gz", "N1_S1_L002_R2_001.fastq.gz", "r:2")
    g = gen(tmp_path, S.SAREK, [data], {"patient": "P_{sample}", "status": "1"})
    got = rows(g)
    assert [(r["patient"], r["sample"], r["lane"], r["status"]) for r in got] == [
        ("P_N1", "N1", "1", "1"), ("P_N1", "N1", "2", "1")]
    assert g.text.splitlines()[0] == "patient,sample,status,lane,fastq_1,fastq_2"
    assert g.record["sheet_set"] == {"patient": "P_{sample}", "status": "1"}
    drop = tmp_path / "drop"
    drop.mkdir()
    (drop / "R1.bam").write_bytes(b"x")
    (drop / "R1.bam.bai").write_bytes(b"x")
    d = gen(tmp_path, S.DROP, [drop])
    assert d.suffix == ".tsv" and rows(d) == [{"RNA_ID": "R1", "RNA_BAM_FILE": str(drop / "R1.bam"),
                                              "RNA_BAI_FILE": str(drop / "R1.bam.bai"),
                                              "STRAND": "no"}]


def test_lane_without_tokens_is_one_and_must_identify_the_row(tmp_path):
    data = tmp_path / "data"
    pair(data, "T_R1.fastq.gz", "T_R2.fastq.gz")
    got = rows(gen(tmp_path, S.SAREK, [data], {"patient": "{sample}"}))
    assert got[0]["lane"] == "1"
    split = tmp_path / "split"
    pair(split, "T_R1_001.fastq.gz", "T_R2_001.fastq.gz", "r:1")
    pair(split, "T_R1_002.fastq.gz", "T_R2_002.fastq.gz", "r:2")
    assert "lane" in str(refused(tmp_path, S.SAREK, [split], {"patient": "{sample}"}))
    # Without a lane column the split files are simply two rows of the sample.
    assert len(rows(gen(tmp_path, S.RNASEQ, [split], {"strandedness": "auto"}))) == 2


@pytest.mark.parametrize("assignments, message", [
    ({"strandednes": "auto"}, "no column 'strandednes'"),
    ({"strandedness": "sideways"}, "one of: forward, reverse, unstranded, auto"),
    ({"strandedness": "auto", "fastq_1": "/x.fastq.gz"}, "taken from the input files"),
    ({"strandedness": "auto", "sample": "S"}, "{sample}"),
    ({"strandedness": "{strand}"}, "{strand}"),
    ({"strandedness": "auto", "percent_mapped": "high"}, "number"),
    ({"strandedness": "auto", "seq_platform": "a b"}, "^\\S+$"),
])
def test_assignments_are_checked(tmp_path, assignments, message):
    data = tmp_path / "data"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    assert message in str(refused(tmp_path, S.RNASEQ, [data], assignments))


def test_empty_assignment_chooses_the_read_group_and_conditional_columns_are_named(tmp_path):
    data = tmp_path / "data"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    err = refused(tmp_path, S.MAG, [data], {"group": "0"})
    assert "--sheet-set long_reads=" in str(err)
    err = refused(tmp_path, S.MAG, [data], {"group": "0", "long_reads": ""})
    assert "'short_reads_platform'" in str(err) and "short_reads_1" in str(err)
    got = rows(gen(tmp_path, S.MAG, [data], {"group": "0", "long_reads": "",
                                            "short_reads_platform": "ILLUMINA"}))
    assert [(r["sample"], r["group"], r["short_reads_platform"]) for r in got] == [
        ("A", "0", "ILLUMINA")]


def test_unique_entries_are_enforced_with_a_way_out(tmp_path):
    data = tmp_path / "data"
    pair(data, "A_S1_L001_R1_001.fastq.gz", "A_S1_L001_R2_001.fastq.gz", "r:1")
    pair(data, "A_S1_L002_R1_001.fastq.gz", "A_S1_L002_R2_001.fastq.gz", "r:2")
    base = {"group": "0", "long_reads": "", "short_reads_platform": "ILLUMINA"}
    err = refused(tmp_path, S.MAG, [data], base)
    assert "'sample', 'run'" in str(err) and "{lane}" in err.fix
    got = rows(gen(tmp_path, S.MAG, [data], {**base, "run": "{lane}"}))
    assert [r["run"] for r in got] == ["1", "2"]
    # ampliseq takes one row per sample: several lanes are refused, never merged silently.
    lanes = tmp_path / "lanes"
    pair(lanes, "Aa_S1_L001_R1_001.fastq.gz", "Aa_S1_L001_R2_001.fastq.gz", "r:1")
    pair(lanes, "Aa_S1_L002_R1_001.fastq.gz", "Aa_S1_L002_R2_001.fastq.gz", "r:2")
    err = refused(tmp_path, S.AMPLISEQ, [lanes])
    assert "values of 'sample'" in str(err) and "one row per sample" in err.fix


def test_samples_must_bring_the_same_kinds_of_files(tmp_path):
    data = tmp_path / "data"
    pair(data, "T_R1.fastq.gz", "T_R2.fastq.gz")
    (data / "notes.vcf").write_text("##fileformat=VCFv4.2\n")
    err = refused(tmp_path, S.SAREK, [data], {"patient": "{sample}"})
    assert "notes" in str(err) and "vcf" in str(err)


def test_other_data_files_group_by_name_with_their_index(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    for name in ("n1.bam", "n1.bai", "n2.bam", "n2.bam.bai"):
        (data / name).write_bytes(b"x")
    got = rows(gen(tmp_path, S.CREATEPANELREFS, [data]))
    assert [(r["sample"], Path(r["bam"]).name, Path(r["bai"]).name) for r in got] == [
        ("n1", "n1.bam", "n1.bai"), ("n2", "n2.bam", "n2.bam.bai")]
    b = rows(gen(tmp_path, S.BAMTOFASTQ, [data], {"file_type": "bam"}))
    assert [(r["sample_id"], r["file_type"]) for r in b] == [("n1", "bam"), ("n2", "bam")]


def test_a_file_two_columns_accept_is_refused(tmp_path):
    spec = {"input": S.RNASEQ["input"], "sheet": {"items": {"properties": {
        "sample": {"type": "string", "meta": ["id"]},
        "fasta": {"type": "string", "format": "file-path", "pattern": "^\\S+\\.(fa|fasta)$"},
        "protein": {"type": "string", "format": "file-path", "pattern": "^\\S+\\.(faa|fasta)$"},
    }, "required": ["sample", "fasta"]}}}
    data = tmp_path / "data"
    data.mkdir()
    (data / "g.fasta").write_text(">x\nA\n")
    err = refused(tmp_path, spec, [data])
    assert "fasta, protein" in str(err) and "--sheet-set protein=" in err.fix
    assert rows(gen(tmp_path, spec, [data], {"protein": ""}))[0]["fasta"] == str(data / "g.fasta")


def test_no_matching_file_and_schema_without_file_types(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "README").write_text("x")
    assert "No input file" in str(refused(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    assert "declares no file type" in str(refused(tmp_path, S.AIRRFLOW, [data]))


def test_output_does_not_depend_on_discovery_order(tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    for root, names in ((first, "ABC"), (second, "CBA")):
        for n in names:
            pair(root, f"{n}_R1.fastq.gz", f"{n}_R2.fastq.gz")
    a = gen(tmp_path, S.RNASEQ, [first], {"strandedness": "auto"})
    b = gen(tmp_path, S.RNASEQ, [second], {"strandedness": "auto"})
    assert a.text.replace(str(first), "X") == b.text.replace(str(second), "X")


def test_generated_sheet_passes_the_samplesheet_check_and_lists_its_files(tmp_path):
    data = tmp_path / "data"
    a1, a2 = pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    g = gen(tmp_path, S.ATACSEQ, [data], {"replicate": "1"})
    assert g.text.splitlines()[0] == "sample,fastq_1,fastq_2,replicate"
    path = sheetgen.write(g, tmp_path / "staging")
    assert path.name == "samplesheet.csv" and path.read_text() == g.text
    assert samplesheet.validate(path, schema_mod.load_input_schema(
        tmp_path / "pipelines/pipe/upstream")) == []
    # atacseq's FastQ columns declare no path format; the files are inputs all the same.
    assert g.files == (a1, a2)


def test_resume_note_names_added_and_removed_samples(tmp_path):
    data = tmp_path / "data"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    pair(data, "B_R1.fastq.gz", "B_R2.fastq.gz")
    before = sheetgen.write(gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}),
                            tmp_path / "prev")
    assert sheetgen.resume_note(before, gen(tmp_path, S.RNASEQ, [data],
                                            {"strandedness": "auto"})) is None
    for f in data.glob("B_*"):
        f.unlink()
    pair(data, "C_R1.fastq.gz", "C_R2.fastq.gz")
    note = sheetgen.resume_note(before, gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))
    assert "added: C" in note and "removed: B" in note
    assert sheetgen.resume_note(tmp_path / "absent.csv", gen(
        tmp_path, S.RNASEQ, [data], {"strandedness": "auto"})) is None


def test_resume_note_compares_a_previous_sheet_that_is_not_utf8(tmp_path):
    # The sheet a previous launch used, damaged into bytes that are not UTF-8, ended
    # `nfclaw run --resume` (and a chain's resume check) with a UnicodeDecodeError traceback.
    data = tmp_path / "data"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    generated = gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"})
    before = sheetgen.write(generated, tmp_path / "prev")
    before.write_bytes(before.read_bytes().replace(b"A_R1", b"A_\xffR1"))
    assert "same samples, other files or values" in sheetgen.resume_note(before, generated)
    before.write_bytes(before.read_bytes().replace(b"\nA,", b"\n\xff,"))
    assert "added: A" in sheetgen.resume_note(before, generated)


@pytest.mark.parametrize("items, message", [
    (["strandedness"], "COLUMN=VALUE"),
    (["=auto"], "COLUMN=VALUE"),
    (["a=1", "a=2"], "more than once"),
])
def test_parse_assignments_refuses_malformed_items(items, message):
    with pytest.raises(NfclawError) as err:
        sheetgen.parse_assignments(items)
    assert message in str(err.value)


def test_parse_assignments_keeps_empty_values_and_strips_space():
    assert sheetgen.parse_assignments(["strandedness = auto", "long_reads="]) == {
        "strandedness": "auto", "long_reads": ""}
    assert sheetgen.assignments_from_mapping({"status": 1, "flag": True, "x": "y"}) == {
        "status": "1", "flag": "true", "x": "y"}
    with pytest.raises(NfclawError):
        sheetgen.assignments_from_mapping({"x": [1]})


def test_a_linked_directory_keeps_its_own_path(tmp_path):
    data = tmp_path / "data"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    os.symlink(data, tmp_path / "alias")
    got = rows(gen(tmp_path, S.RNASEQ, [tmp_path / "alias"], {"strandedness": "auto"}))
    assert got[0]["fastq_1"] == str(tmp_path / "alias" / "A_R1.fastq.gz")


def test_a_column_that_also_takes_fasta_is_no_read_column(tmp_path):
    # pairgenomealign's `fasta` takes genomes as FASTA or FastQ: its files are not read pairs.
    spec = {"input": S.RNASEQ["input"], "sheet": {"items": {"properties": {
        "sample": {"type": "string", "pattern": "^\\S+$", "meta": ["id"]},
        "fasta": {"type": "string", "format": "file-path", "exists": True,
                  "pattern": "^\\S+\\.f(ast|n)?(a|q)(\\.gz)?$"},
    }, "required": ["sample", "fasta"]}}}
    p = plan_of(tmp_path, spec)
    assert p.reads == () and p.data_columns == ("fasta",)
    data = tmp_path / "data"
    data.mkdir()
    (data / "genome.fa").write_text(">a\nACGT\n")
    (data / "other.fasta.gz").write_bytes(gzip.compress(b">b\nACGT\n"))
    assert [(r["sample"], Path(r["fasta"]).name) for r in rows(gen(tmp_path, spec, [data]))] == [
        ("genome", "genome.fa"), ("other", "other.fasta.gz")]


def test_a_file_column_wins_over_a_name_column_with_the_same_pattern(tmp_path):
    # nanostring: RCC_FILE is the file, RCC_FILE_NAME a name that merely ends like one.
    spec = {"input": S.RNASEQ["input"], "sheet": {"items": {"properties": {
        "SAMPLE_ID": {"type": "string", "pattern": "^\\S+$", "meta": ["id"]},
        "RCC_FILE": {"type": "string", "format": "file-path", "pattern": "^\\S+\\.RCC$"},
        "RCC_FILE_NAME": {"type": "string", "pattern": "^\\S+\\.RCC$"},
    }, "required": ["SAMPLE_ID", "RCC_FILE"]}}}
    data = tmp_path / "data"
    data.mkdir()
    (data / "s1.RCC").write_text("x")
    assert rows(gen(tmp_path, spec, [data])) == [{"SAMPLE_ID": "s1",
                                                  "RCC_FILE": str(data / "s1.RCC")}]


def test_a_number_typed_identity_does_not_take_sample_names(tmp_path):
    # mhcquant's `ID` is an integer per replicate; the sample's name belongs in `Sample`.
    spec = {"input": S.RNASEQ["input"], "sheet": {"items": {"properties": {
        "ID": {"type": "integer", "meta": ["id"]},
        "Sample": {"type": ["string", "integer"], "meta": ["sample"]},
        "ReplicateFileName": {"type": "string", "format": "path",
                              "pattern": "^\\S+\\.(raw|mzML)$"},
    }, "required": ["ID", "Sample", "ReplicateFileName"]}}}
    assert plan_of(tmp_path, spec).id_column == "Sample"


def test_columns_no_file_can_reach_are_not_offered(tmp_path):
    # Two columns with one pattern (spring_1/spring_2) cannot be told apart by a file name.
    spec = {"input": S.RNASEQ["input"], "sheet": {"items": {"properties": {
        "sample": {"type": "string", "meta": ["id"]},
        "spring_1": {"type": "string", "format": "file-path", "pattern": "^\\S+\\.spring$"},
        "spring_2": {"type": "string", "format": "file-path", "pattern": "^\\S+\\.spring$"},
        "bam": {"type": "string", "format": "file-path", "pattern": "^\\S+\\.bam$"},
    }, "required": ["sample"]}}}
    assert plan_of(tmp_path, spec).data_columns == ("bam",)


def test_results_published_into_the_shared_work_tree_are_valid_inputs(tmp_path):
    # Another run's results, published as links into the shared work tree, are inputs like any
    # other; only this run's --outdir is off-limits, and scanning the whole work tree is refused.
    work = tmp_path / "work"
    a1, a2 = pair(work / "ab" / "cdef", "A_R1.fastq.gz", "A_R2.fastq.gz")
    published = tmp_path / "earlier" / "fastq"
    published.mkdir(parents=True)
    (published / "A_R1.fastq.gz").symlink_to(a1)
    (published / "A_R2.fastq.gz").symlink_to(a2)
    got = rows(gen(tmp_path, S.RNASEQ, [published], {"strandedness": "auto"}))
    assert got[0]["fastq_1"] == str(published / "A_R1.fastq.gz")
    err = refused(tmp_path, S.RNASEQ, [tmp_path], {"strandedness": "auto"},
                  outdir=tmp_path.parent / f"{tmp_path.name}-results")
    assert "work directory" in str(err)


def test_assigned_columns_take_no_files_and_reads_take_no_constants(tmp_path):
    data = tmp_path / "data"
    pair(data, "N1_R1.fastq.gz", "N1_R2.fastq.gz")
    (data / "N1.bam").write_bytes(b"x")
    ref = tmp_path / "ref.bam"
    ref.write_bytes(b"x")
    # The constant fills the column; the directory's BAM is no longer a candidate for it.
    got = rows(gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto", "genome_bam": str(ref)}))
    assert [r["genome_bam"] for r in got] == [str(ref)]
    # A read column of a group that is not used is still a read column.
    err = refused(tmp_path, S.MAG, [data], {"group": "0", "short_reads_platform": "ILLUMINA",
                                            "long_reads": str(data / "N1_R1.fastq.gz")})
    assert "taken from the input files" in str(err)


def test_an_assigned_lane_must_still_tell_a_samples_rows_apart(tmp_path):
    data = tmp_path / "data"
    pair(data, "T_S1_L001_R1_001.fastq.gz", "T_S1_L001_R2_001.fastq.gz", "r:1")
    pair(data, "T_S1_L002_R1_001.fastq.gz", "T_S1_L002_R2_001.fastq.gz", "r:2")
    assert "lane" in str(refused(tmp_path, S.SAREK, [data], {"patient": "{sample}", "lane": "7"}))
    got = rows(gen(tmp_path, S.SAREK, [data], {"patient": "{sample}", "lane": "run7_{lane}"}))
    assert [r["lane"] for r in got] == ["run7_1", "run7_2"]


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads every directory")
def test_an_unreadable_subdirectory_is_refused_not_skipped(tmp_path):
    # Skipping it would silently drop its samples from the analysis.
    data = tmp_path / "data"
    pair(data, "A_R1.fastq.gz", "A_R2.fastq.gz")
    locked = data / "lane2"
    pair(locked, "B_R1.fastq.gz", "B_R2.fastq.gz")
    locked.chmod(0)
    try:
        err = refused(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"})
    finally:
        locked.chmod(0o755)
    assert "cannot read" in str(err) and "lane2" in str(err)


def test_an_empty_directory_and_crlf_fastq(tmp_path):
    (tmp_path / "empty").mkdir()
    assert "No input file" in str(refused(tmp_path, S.RNASEQ, [tmp_path / "empty"],
                                          {"strandedness": "auto"}))
    data = tmp_path / "data"
    data.mkdir()
    (data / "A_1.fastq").write_bytes(b"@r1/1\r\nACGT\r\n+\r\nIIII\r\n")
    (data / "A_2.fastq").write_bytes(b"@r1/2\r\nACGT\r\n+\r\nIIII\r\n")
    assert rows(gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))[0]["sample"] == "A"


def test_hyphenated_read_tokens_pair(tmp_path):
    data = tmp_path / "data"
    pair(data, "S1-R1.fastq.gz", "S1-R2.fastq.gz")
    pair(data, "S2-1.fastq.gz", "S2-2.fastq.gz", "M2:1:FC:1:1101:300:400")
    got = rows(gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))
    assert [(r["sample"], Path(r["fastq_2"]).name) for r in got] == [
        ("S1", "S1-R2.fastq.gz"), ("S2", "S2-2.fastq.gz")]


@pytest.mark.parametrize("r1, r2", [("S_read1.fq.gz", "S_read2.fq.gz"),
                                    ("S_F.fastq.gz", "S_R.fastq.gz")])
def test_mates_under_an_unknown_naming_are_refused_not_split(tmp_path, r1, r2):
    # Their names carry no read number nfclaw recognises, but their reads pair: taking them for two
    # single-end samples would analyse one library as two.
    data = tmp_path / "data"
    pair(data, r1, r2)
    err = refused(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"})
    assert r1 in str(err) and "_R1" in err.fix


def test_similar_names_of_different_libraries_stay_single_end(tmp_path):
    data = tmp_path / "data"
    fq(data / "S_read1.fq.gz", "M1:1:FC:1:1101:100:200 1:N:0:1")
    fq(data / "S_read2.fq.gz", "M1:1:FC:1:1101:555:666 1:N:0:1")
    got = rows(gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))
    assert [r["sample"] for r in got] == ["S_read1", "S_read2"]


# --- edge cases: identity templates, read names, compression, scale -----------------------------

def test_an_identity_template_can_make_a_file_derived_name_acceptable(tmp_path):
    # ampliseq's `sample` must start with a letter: `S{sample}` makes `1234` acceptable, and the
    # check judges the value written, not the raw file name.
    data = tmp_path / "data"
    pair(data, "1234_R1.fastq.gz", "1234_R2.fastq.gz")
    assert "1234" in str(refused(tmp_path, S.AMPLISEQ, [data]))
    assert rows(gen(tmp_path, S.AMPLISEQ, [data], {"sample": "S{sample}"}))[0]["sample"] == "S1234"


def test_generic_read_names_are_no_evidence(tmp_path):
    # Simulators and renumbering write `@read1` in every file: equal names prove nothing.
    bare = tmp_path / "bare"
    fq(bare / "ctrl_1.fastq.gz", "read1")
    fq(bare / "ctrl_2.fastq.gz", "read1")
    err = refused(tmp_path, S.RNASEQ, [bare], {"strandedness": "auto"})
    assert "ctrl_1.fastq.gz" in str(err) and "_R1" in err.fix
    numbered = tmp_path / "numbered"
    fq(numbered / "tumor1.fastq.gz", "read1")
    fq(numbered / "tumor2.fastq.gz", "read1")
    g = gen(tmp_path, S.RNASEQ, [numbered], {"strandedness": "auto"})
    assert [r["sample"] for r in rows(g)] == ["tumor1", "tumor2"]
    assert any("tumor1.fastq.gz" in n and "_R1" in n for n in g.notes)


@pytest.mark.parametrize("suffix, opener", [(".bz2", "bz2"), (".xz", "lzma")])
def test_other_compressed_fastq_is_read(tmp_path, suffix, opener):
    spec = {"input": S.RNASEQ["input"], "sheet": {"items": {"properties": {
        "sample": {"type": "string", "meta": ["id"]},
        "fastq_1": {"type": "string", "format": "file-path",
                    "pattern": "^\\S+\\.f(ast)?q(\\.gz|\\.bz2|\\.xz)?$"},
        "fastq_2": {"type": "string", "format": "file-path",
                    "pattern": "^\\S+\\.f(ast)?q(\\.gz|\\.bz2|\\.xz)?$"},
    }, "required": ["sample", "fastq_1"]}}}
    data = tmp_path / "data"
    data.mkdir()
    module = importlib.import_module(opener)
    for read in (1, 2):
        (data / f"S_R{read}.fastq{suffix}").write_bytes(
            module.compress(f"@M1:1:FC:1:1:1:1 {read}:N:0:1\nACGT\n+\nIIII\n".encode()))
    assert [r["sample"] for r in rows(gen(tmp_path, spec, [data]))] == ["S"]


def test_skill_paragraph_does_not_offer_a_choice_when_generation_is_impossible(tmp_path):
    spec = dict(S.MAG, input=dict(S.MAG["input"], pattern="^\\S+\\.ya?ml$"))
    up = S.make_pipeline(tmp_path, spec)
    text = sheetgen.describe(schema_mod.load_input_schema(up),
                             schema_mod.load_param_schema(up).params["input"])
    assert "cannot generate" in text and "once you choose" not in text


def test_many_samples_stay_fast(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    for n in range(3000):
        (data / f"s{n:05d}.fastq.gz").write_bytes(b"")
    started = time.monotonic()
    g = gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"})
    assert g.record["samples"] == 3000 and time.monotonic() - started < 20


# --- edge cases: zstd, lone files, template paths, the work tree ----------------------------------

def _zst_spec():
    pattern = "^\\S+\\.f(ast)?q(\\.gz|\\.zst)?$"
    return {"input": S.RNASEQ["input"], "sheet": {"items": {"properties": {
        "sample": {"type": "string", "meta": ["id"]},
        "fastq_1": {"type": "string", "format": "file-path", "pattern": pattern},
        "fastq_2": {"type": "string", "format": "file-path", "pattern": pattern},
    }, "required": ["sample", "fastq_1"]}}}


def test_zstd_mates_named_r1_r2_pair_by_name_with_a_note(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "a_R1.fastq.zst").write_bytes(b"\x28\xb5\x2f\xfd")
    (data / "a_R2.fastq.zst").write_bytes(b"\x28\xb5\x2f\xfd")
    g = gen(tmp_path, _zst_spec(), [data])
    assert rows(g)[0]["fastq_2"].endswith("a_R2.fastq.zst")
    assert any("zstd" in n and "by name" in n for n in g.notes)
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "x_1.fastq.zst").write_bytes(b"\x28\xb5\x2f\xfd")
    (bare / "x_2.fastq.zst").write_bytes(b"\x28\xb5\x2f\xfd")
    err = refused(tmp_path, _zst_spec(), [bare])
    assert "zstd" in str(err) and "_R1" in err.fix


def test_a_lone_fastq_is_data_for_a_schema_with_several_read_groups(tmp_path):
    up = S.make_pipeline(tmp_path, S.MAG)
    reads = fq(tmp_path / "s1.fastq.gz", "M1:1:FC:1:1:1:1")
    assert sheetgen.detect(str(reads), up).values == (str(reads),)


def test_paths_a_template_or_constant_writes_are_inputs(tmp_path):
    data = tmp_path / "data"
    pair(data, "N1_R1.fastq.gz", "N1_R2.fastq.gz")
    ref = tmp_path / "bams"
    ref.mkdir()
    (ref / "N1.bam").write_bytes(b"x")
    g = gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto",
                                         "genome_bam": str(ref / "{sample}.bam")})
    assert ref / "N1.bam" in g.files


def test_a_glob_does_not_reach_into_the_work_tree(tmp_path):
    pair(tmp_path / "proj" / "reads", "A_R1.fastq.gz", "A_R2.fastq.gz")
    pair(tmp_path / "proj" / "work" / "ab" / "cdef", "A_trimmed_R1.fastq.gz",
         "A_trimmed_R2.fastq.gz")
    up = S.make_pipeline(tmp_path, S.RNASEQ)
    source = sheetgen.detect(str(tmp_path / "proj" / "**" / "*.fastq.gz"), up)
    with pytest.raises(NfclawError, match="work directory"):
        sheetgen.generate(source, up, pipeline="pipe", assignments={"strandedness": "auto"},
                          outdir=tmp_path / "results", work_dir=tmp_path / "proj" / "work")


def test_read_sets_of_one_sample_must_be_told_apart(tmp_path):
    data = tmp_path / "data"
    fq(data / "ctrl.fastq.gz", "M1:1:FC:1:1:1:1")
    fq(data / "ctrl_R1.fastq.gz", "M1:1:FC:1:1:1:9")
    err = refused(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"})
    assert "ctrl.fastq.gz" in str(err) and "ctrl_R1.fastq.gz" in str(err)
