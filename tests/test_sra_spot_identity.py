"""SRA spot identifiers identify molecules; their terminal digits are not mate numbers."""
import pytest

import sheetgen_schemas as S
from runner import sheetgen
from runner.errors import NfclawError
from test_sheetgen import fq, gen, rows


@pytest.mark.parametrize("accession", ["SRR390728", "ERR390728", "DRR390728"])
def test_different_sra_spots_never_pair_numbered_single_end_libraries(tmp_path, accession):
    first = fq(tmp_path / "data/replicate_1.fastq.gz", accession + ".1")
    second = fq(tmp_path / "data/replicate_2.fastq.gz", accession + ".2")
    generated = gen(tmp_path, S.ATACSEQ, [first, second], {"replicate": "1"})
    result = rows(generated)
    assert {row["sample"] for row in result} == {"replicate_1", "replicate_2"}
    assert all(not row["fastq_2"] for row in result)
    assert generated.record["paired_end"] == 0


@pytest.mark.parametrize("suffixes", [("/1", "/2"), (".1", ".2"), ("", "")])
def test_same_sra_spot_can_carry_explicit_mate_suffixes_or_a_shared_name(suffixes):
    assert sheetgen._mates("SRR390728.123" + suffixes[0], "SRR390728.123" + suffixes[1])


def test_explicitly_named_sra_mates_with_different_spots_raise_a_note(tmp_path):
    first = fq(tmp_path / "data/A_R1.fastq.gz", "SRR390728.1")
    second = fq(tmp_path / "data/A_R2.fastq.gz", "SRR390728.2")
    generated = gen(tmp_path, S.ATACSEQ, [first, second], {"replicate": "1"})
    assert len(rows(generated)) == 1
    assert any("read names differ" in note for note in generated.notes)


@pytest.mark.parametrize("roles", [(1, 1), (2, 2), (2, 1)])
def test_bare_numbers_cannot_override_explicit_illumina_mate_orientation(tmp_path, roles):
    paths = [fq(tmp_path / f"data/technical_{index}.fastq.gz",
                f"M1:1:FC:1:1101:100:200 {role}:N:0:ACGT")
             for index, role in zip((1, 2), roles, strict=True)]
    with pytest.raises(NfclawError, match="mate|orientation"):
        gen(tmp_path, S.ATACSEQ, paths, {"replicate": "1"})


def test_conflicting_suffix_and_illumina_role_is_not_pairing_evidence(tmp_path):
    paths = [fq(tmp_path / f"data/technical_{index}.fastq.gz",
                f"M1:1:FC:1:1101:100:200/{index} {3 - index}:N:0:ACGT")
             for index in (1, 2)]
    with pytest.raises(NfclawError, match="mate|orientation"):
        gen(tmp_path, S.ATACSEQ, paths, {"replicate": "1"})
