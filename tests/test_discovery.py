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
