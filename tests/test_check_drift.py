import shutil
import subprocess
from pathlib import Path

import pytest

from librarian import check_drift, write_catalog, write_skill

FIX = Path(__file__).parent / "fixtures"


def _seed(tmp_path, name):
    up = tmp_path / "pipelines" / name / "upstream"
    up.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config"):
        (up / f).write_text("x")
    shutil.copy(FIX / name / "nextflow_schema.json", up / "nextflow_schema.json")
    return tmp_path / "pipelines"


def test_no_drift_when_freshly_generated(tmp_path):
    pdir = _seed(tmp_path, "mini")
    write_skill.generate("mini", pipelines_dir=pdir)
    write_catalog.generate(pipelines_dir=pdir,
                           out_md=tmp_path / "catalog.md", out_json=tmp_path / "catalog.json")
    assert check_drift.check(pdir) == []


def test_drift_when_skill_edited(tmp_path):
    pdir = _seed(tmp_path, "mini")
    write_skill.generate("mini", pipelines_dir=pdir)
    (pdir / "mini" / "skill.md").write_text("hand-edited\n")
    assert any("stale" in d for d in check_drift.check(pdir))


def test_drift_reports_incomplete_submodule_without_traceback(tmp_path):
    pdir = tmp_path / "pipelines"
    (pdir / "empty" / "upstream").mkdir(parents=True)
    drift = check_drift.check(pdir)
    assert (
        "empty/upstream is incomplete (missing main.nf, nextflow.config, nextflow_schema.json; "
        "run `git submodule update --init pipelines/empty/upstream`)"
    ) in drift


def test_check_drift_never_writes(tmp_path, monkeypatch):
    # The gate compares in memory via render(); it must never call the writing path.
    pdir = _seed(tmp_path, "mini")
    write_skill.generate("mini", pipelines_dir=pdir)
    write_catalog.generate(pipelines_dir=pdir,
                           out_md=tmp_path / "catalog.md", out_json=tmp_path / "catalog.json")

    def _boom(*a, **k):
        raise AssertionError("check_drift must not write files")
    monkeypatch.setattr(write_skill, "generate", _boom)
    assert check_drift.check(pdir) == []


def test_drift_reports_manifest_set_and_remote_mismatches(tmp_path):
    pdir = _seed(tmp_path, "mini")
    write_skill.generate("mini", pipelines_dir=pdir)
    write_catalog.generate(pipelines_dir=pdir,
                           out_md=tmp_path / "catalog.md", out_json=tmp_path / "catalog.json")
    (tmp_path / "sources.tsv").write_text(
        "mini\thttps://github.com/nf-core/wrong.git\tlatest-release\n"
        "extra\thttps://github.com/nf-core/extra.git\tlatest-release\n"
    )
    (tmp_path / ".gitmodules").write_text(
        '[submodule "pipelines/mini/upstream"]\n'
        "\tpath = pipelines/mini/upstream\n"
        "\turl = https://github.com/nf-core/mini.git\n"
    )
    drift = check_drift.check(pdir)
    assert "sources.tsv has unknown pipelines: extra" in drift
    assert any(item.startswith("mini remote differs:") for item in drift)


@pytest.mark.parametrize("extra", [
    "url = https://example.invalid/other.git\n",
    "URL = https://example.invalid/other.git\n",
    "path = pipelines/other/upstream\n",
    '[submodule "pipelines/mini/upstream"]\nurl = https://example.invalid/other.git\n',
    '[submodule "other"]\npath = pipelines/other/upstream\nurl = https://example.invalid/x\n',
    '[unrelated]\nsetting = ignored\n',
    '[submodule "broken"\n',
])
def test_drift_refuses_ambiguous_or_malformed_gitmodule_registration(tmp_path, extra):
    (tmp_path / 'sources.tsv').write_text(
        'mini\thttps://github.com/nf-core/mini.git\tlatest-release\n')
    (tmp_path / '.gitmodules').write_text(
        '[submodule "pipelines/mini/upstream"]\n'
        'path = pipelines/mini/upstream\nurl = https://github.com/nf-core/mini.git\n' + extra)
    assert check_drift._structure_drift(tmp_path, ['mini'])


def test_drift_reads_git_quoted_values_and_comments_as_git_does(tmp_path):
    (tmp_path / 'sources.tsv').write_text(
        'mini\thttps://github.com/nf-core/mini.git\tlatest-release\n')
    (tmp_path / '.gitmodules').write_text(
        '# canonical registration, using valid Git quoting\n'
        '[submodule "pipelines/mini/upstream"]\n'
        'path = "pipelines/mini/upstream" # location\n'
        'url = "https://github.com/nf-core/mini.git" ; source\n')
    assert check_drift._structure_drift(tmp_path, ['mini']) == []


def test_drift_gate_reports_an_incompatible_handoff(library):
    root = library("mini_up", "mini", rules={("mini_up", "mini"): {
        "params": {"input": {"samplesheet": "s.csv", "provides": ["sample"]}}}})
    assert check_drift._handoff_drift(root, root / "pipelines") == [
        "handoffs/mini_up/mini.json: mini samplesheet: missing required column 'fastq_1'"]


def test_drift_gate_reports_a_handoff_naming_an_unknown_pipeline(library):
    root = library("mini_up", rules={("mini_up", "gone"): {
        "params": {"x": {"file": "a.tsv"}}}})
    assert check_drift._handoff_drift(root, root / "pipelines") == [
        "handoffs/mini_up/gone.json: unknown pipeline(s): gone"]


def test_drift_gate_reports_an_unreadable_handoff(library):
    root = library("mini_up")
    (root / "handoffs" / "mini_up").mkdir(parents=True)
    (root / "handoffs" / "mini_up" / "mini.json").write_text("{nope")
    [drift] = check_drift._handoff_drift(root, root / "pipelines")
    assert "handoffs/mini_up/mini.json cannot be read" in drift


def test_drift_when_a_checkout_is_not_the_recorded_gitlink(tmp_path):
    # Docs are generated from the checked-out tree. CI checks out the gitlinks, but a local
    # `make check` with a submodule at another commit used to pass while the committed docs
    # described a commit the repository does not pin.
    def git(path, *args):
        return subprocess.run(["git", "-C", str(path), "-c", "user.name=t", "-c", "user.email=t@t",
                               *args], check=True, capture_output=True, text=True).stdout.strip()

    pdir = _seed(tmp_path, "mini")
    up = pdir / "mini" / "upstream"
    git(up, "init", "-q")
    git(up, "add", "-A")
    git(up, "commit", "-qm", "one")
    pinned = git(up, "rev-parse", "HEAD")
    (up / "main.nf").write_text("y")
    git(up, "commit", "-qam", "two")
    git(tmp_path, "init", "-q")
    git(tmp_path, "update-index", "--add", "--cacheinfo",
        f"160000,{pinned},pipelines/mini/upstream")
    write_skill.generate("mini", pipelines_dir=pdir)               # docs of the checked-out "two"
    write_catalog.generate(pipelines_dir=pdir,
                           out_md=tmp_path / "catalog.md", out_json=tmp_path / "catalog.json")
    drift = check_drift.check(pdir)
    assert any("checked out at" in d and pinned[:12] in d for d in drift)
    git(up, "checkout", "-q", pinned)
    write_skill.generate("mini", pipelines_dir=pdir)
    write_catalog.generate(pipelines_dir=pdir,
                           out_md=tmp_path / "catalog.md", out_json=tmp_path / "catalog.json")
    assert not any("checked out at" in d for d in check_drift.check(pdir))
