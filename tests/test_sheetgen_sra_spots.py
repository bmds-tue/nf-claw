"""SRA spot numbers name molecules: consecutive spots are never mates."""
import pytest

import sheetgen_schemas as S
from test_sheetgen import fq, gen, rows


@pytest.mark.parametrize("id1, id2", [
    ("SRR390728.1", "SRR390728.2"),                       # fastq-dump: spots 1 and 2
    ("ERR123.1 length=50", "ERR123.2 length=50"),
    ("DRR9.11", "DRR9.12"),
])
def test_consecutive_sra_spots_in_numbered_files_stay_two_single_end_samples(tmp_path, id1, id2):
    data = tmp_path / "data"
    fq(data / "run_1.fastq.gz", id1)
    fq(data / "run_2.fastq.gz", id2)
    g = gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"})
    assert [(r["sample"], r["fastq_2"]) for r in rows(g)] == [("run_1", ""), ("run_2", "")]


@pytest.mark.parametrize("id1, id2", [
    ("SRR390728.1", "SRR390728.1"),                       # fastq-dump --split-files: one spot
    ("SRR390728.1.1", "SRR390728.1.2"),                   # fastq-dump --readids
    ("SRR390728.1/1", "SRR390728.1/2"),
])
def test_mates_of_one_sra_spot_still_pair(tmp_path, id1, id2):
    data = tmp_path / "data"
    fq(data / "run_1.fastq.gz", id1)
    fq(data / "run_2.fastq.gz", id2)
    got = rows(gen(tmp_path, S.RNASEQ, [data], {"strandedness": "auto"}))
    assert [r["sample"] for r in got] == ["run"] and got[0]["fastq_2"].endswith("run_2.fastq.gz")
