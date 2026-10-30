import json
from pathlib import Path

import pytest

from runner import discovery
from runner.errors import NfclawError


def _make(tmp_path, name, frontmatter):
    d = tmp_path / name
    (d / "upstream").mkdir(parents=True)
    (d / "skill.md").write_text(f"---\n{frontmatter}\n---\n# {name}\n")
    return d


def test_discover_lists_sorted(tmp_path):
    _make(tmp_path, "sarek", "name: sarek\nversion: 3.8.1")
    _make(tmp_path, "rnaseq", "name: rnaseq\nversion: 3.14.0")
    assert [p.name for p in discovery.discover(tmp_path)] == ["rnaseq", "sarek"]


def test_find_reads_frontmatter(tmp_path):
    _make(tmp_path, "sarek", "name: sarek\nversion: 3.8.1\ndescription: variant calling")
    p = discovery.find("sarek", tmp_path)
    assert p.frontmatter["version"] == "3.8.1"
    assert p.frontmatter["description"] == "variant calling"


def test_find_missing_raises(tmp_path):
    with pytest.raises(NfclawError):
        discovery.find("nope", tmp_path)


def test_hidden_entries_beside_the_pipelines_are_not_pipelines(tmp_path):
    # A Nextflow launched with pipelines/ as its working directory leaves pipelines/.nextflow/; it
    # was listed by `nfclaw list` and crashed `make build` (write_skill --all) as a pipeline.
    _make(tmp_path, "rnaseq", "name: rnaseq\nversion: 3.14.0")
    (tmp_path / ".nextflow" / "plr").mkdir(parents=True)
    assert [p.name for p in discovery.discover(tmp_path)] == ["rnaseq"]
    assert [p.name for p in discovery.pipeline_dirs(tmp_path)] == ["rnaseq"]


@pytest.mark.parametrize("name", ["../outside", "rnaseq/../outside", ".nextflow", "", "rnaseq/"])
def test_find_only_names_a_listed_pipeline_directory(tmp_path, name):
    pipelines = tmp_path / "pipelines"
    _make(pipelines, "rnaseq", "name: rnaseq")
    _make(tmp_path, "outside", "name: outside")
    (pipelines / ".nextflow").mkdir()
    with pytest.raises(NfclawError):
        discovery.find(name, pipelines)


ROWS = [{"name": "rnaseq", "version": "3.0.0", "description": "RNA sequencing analysis",
         "tools": ["STAR", "Salmon"], "input": "FastQ", "summary": "gene expression"},
        {"name": "sarek", "version": "3.5.0", "description": "Variant calling",
         "tools": ["GATK"], "input": "FastQ or BAM", "summary": "germline and somatic"},
        {"name": "scrnaseq", "version": "2.0.0", "description": "Single-cell RNA-seq",
         "tools": ["Cellranger"], "input": "FastQ", "summary": ""}]


def test_search_ranks_an_exact_name_first_and_ignores_punctuation():
    assert [r["name"] for r in discovery.search(ROWS, "rnaseq")] == ["rnaseq", "scrnaseq"]
    assert [r["name"] for r in discovery.search(ROWS, "RNA-seq")] == ["rnaseq", "scrnaseq"]


def test_search_matches_tools_and_drops_rows_no_word_occurs_in():
    assert [r["name"] for r in discovery.search(ROWS, "gatk")] == ["sarek"]
    assert discovery.search(ROWS, "metagenome") == []


def test_an_empty_search_lists_every_row_by_name():
    assert [r["name"] for r in discovery.search(ROWS, " ,; ")] == ["rnaseq", "sarek", "scrnaseq"]


def test_search_reads_frontmatter_lists_written_as_text():
    rows = [{"name": "a", "tools": '["SHazaM, Change-O"]'}, {"name": "b", "tools": "BWA"}]
    assert [r["name"] for r in discovery.search(rows, "change-o")] == ["a"]


def test_a_row_holding_every_word_outranks_one_word_in_a_name():
    # `nfclaw list variant calling` ranked callingcards ("calling" in its name) above pipelines
    # whose descriptions name the whole query.
    rows = [{"name": "callingcards", "description": "Mammalian bulk calling cards"},
            {"name": "sarek", "description": "Germline and somatic variant calling"},
            {"name": "variantbenchmarking", "description": "Benchmarking of variant calling"}]
    assert [r["name"] for r in discovery.search(rows, "variant calling")] == [
        "variantbenchmarking", "sarek", "callingcards"]
    assert [r["name"] for r in discovery.search(rows, "calling")] == [
        "callingcards", "sarek", "variantbenchmarking"]


def test_the_library_answers_its_documented_example_with_rows_naming_both_words():
    rows = json.loads((Path(__file__).resolve().parent.parent / "catalog.json").read_text())
    top = discovery.search(rows, "variant calling")[:3]
    assert len(top) == 3
    for row in top:
        searched = (row.get(k) for k in ("name", "description", "tools", "input", "summary"))
        haystack = discovery._squash(" ".join(
            " ".join(v) if isinstance(v, list) else str(v or "") for v in searched))
        assert "variant" in haystack and "calling" in haystack, row["name"]
