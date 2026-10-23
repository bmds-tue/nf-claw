import pytest

from librarian import add_pipeline
from librarian.add_pipeline import Source


def test_read_sources_tsv(tmp_path):
    tsv = tmp_path / "sources.tsv"
    tsv.write_text("# c\nrnaseq\thttps://x/rnaseq.git\tlatest-release\n")
    srcs = add_pipeline.read_sources(tsv)
    assert srcs[0].name == "rnaseq" and srcs[0].policy == "latest-release"


def test_read_sources_rejects_path_like_pipeline_name(tmp_path):
    tsv = tmp_path / "sources.tsv"
    tsv.write_text("../bad\thttps://x/bad.git\tlatest-release\n")
    with pytest.raises(ValueError, match="invalid pipeline name"):
        add_pipeline.read_sources(tsv)


@pytest.mark.parametrize("name", [".", "..", ".hidden", "hidden.", "-bad", "bad-"])
def test_pipeline_name_rejects_special_or_hidden_path_components(name):
    # These contain no slash, but are still unsafe path components. In particular, `..` would
    # make the discovery rollback remove the repository root instead of one pipeline directory.
    assert not add_pipeline.valid_pipeline_name(name)
    with pytest.raises(ValueError, match="invalid pipeline name"):
        add_pipeline.validate_pipeline_name(name)


@pytest.mark.parametrize("name", ["a", "rnaseq", "pipe_2", "pipe.v2", "Pipe-2"])
def test_pipeline_name_accepts_safe_slugs(name):
    assert add_pipeline.validate_pipeline_name(name) == name


def test_gitmodules_text():
    text = add_pipeline.gitmodules_text([Source("sarek", "https://x/sarek.git", "latest-release")])
    assert 'path = pipelines/sarek/upstream' in text
    assert 'url = https://x/sarek.git' in text
    # matches what `git submodule add` writes (.gitmodules has no branch pin)
    assert 'branch' not in text
