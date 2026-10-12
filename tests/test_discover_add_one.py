"""Pinning a submodule to a release tag must record the gitlink AT THE TAG.

Regression test for the discovery drift bug: `git submodule add` records the default
branch HEAD, and the scaffolding then checks out the tag only in the working tree. If the
recorded gitlink is left at the default HEAD, a later `git submodule update` (run by the
Nextflow-acceptance step) resets the working tree off the tag, so `git describe --tags`
returns `<tag>-N-g<hash>` and the drift gate flags the freshly generated context as stale.
This bit pipelines whose default branch had commits after the release. `add_one` and
`bump` (auto-update) share the same pin-to-tag contract, so both are covered here."""
import subprocess
from pathlib import Path
import pytest

from librarian import discover_pipelines as dp
from librarian import update_pipelines as up_mod
from librarian import write_skill

_SCHEMA = Path(__file__).parent / "fixtures" / "mini" / "nextflow_schema.json"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(cwd), check=True,
                          capture_output=True, text=True).stdout.strip()


def _commit(origin: Path, msg: str) -> None:
    (origin / "main.nf").write_text(f"workflow {{ /* {msg} */ }}\n")
    _git(origin, "add", "-A")
    _git(origin, "commit", "-qm", msg)


def _make_origin(origin: Path) -> dict[str, str]:
    """A pipeline repo with tags 1.0.0 and 1.1.0, whose default branch HEAD is AHEAD of both."""
    origin.mkdir()
    _git(origin, "init", "-q")
    _git(origin, "config", "user.email", "t@t")
    _git(origin, "config", "user.name", "t")
    (origin / "nextflow.config").write_text("manifest { nextflowVersion = '!>=24.04.0' }\n")
    (origin / "nextflow_schema.json").write_text(_SCHEMA.read_text(encoding="utf-8"))
    commits = {}
    _commit(origin, "release 1.0.0")
    _git(origin, "tag", "1.0.0")
    commits["1.0.0"] = _git(origin, "rev-list", "-n1", "1.0.0")
    _commit(origin, "release 1.1.0")
    _git(origin, "tag", "1.1.0")
    commits["1.1.0"] = _git(origin, "rev-list", "-n1", "1.1.0")
    _commit(origin, "post-release dev")                        # default HEAD now != any tag
    return commits


def _make_superproject(repo: Path) -> None:
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "README.md").write_text("x\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")


def _allow_file_submodules(monkeypatch) -> None:
    # git blocks the file:// transport for submodules by default (CVE-2022-39253); allow it
    # for every child git process in this test via injected config.
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")


def _assert_pinned_to(repo: Path, name: str, tag: str, tag_commit: str) -> None:
    """The recorded gitlink is the tag commit, and a `git submodule update` keeps it there."""
    up = repo / "pipelines" / name / "upstream"
    assert _git(up, "describe", "--tags") == tag
    gitlink = _git(repo, "ls-files", "-s", f"pipelines/{name}/upstream").split()[1]
    assert gitlink == tag_commit
    _git(repo, "submodule", "update", "--init", f"pipelines/{name}/upstream")
    assert _git(up, "describe", "--tags") == tag               # survived the reset
    sk_disk = (repo / "pipelines" / name / "skill.md").read_text(encoding="utf-8")
    sk_ren, _ = write_skill.render(name, pipelines_dir=repo / "pipelines")
    assert sk_disk == sk_ren                                   # no drift


def test_add_one_pins_gitlink_to_tag(tmp_path, monkeypatch):
    _allow_file_submodules(monkeypatch)
    commits = _make_origin(tmp_path / "origin")
    _make_superproject(tmp_path / "repo")
    repo = tmp_path / "repo"

    assert dp.add_one("mini", (tmp_path / "origin").as_uri(), "1.0.0", repo)
    _assert_pinned_to(repo, "mini", "1.0.0", commits["1.0.0"])


@pytest.mark.parametrize("kind", ["directory", "symlink", "broken_symlink"])
def test_failed_discovery_does_not_delete_a_preexisting_pipeline_entry(tmp_path, monkeypatch, kind):
    repo = tmp_path / "repo"
    _make_superproject(repo)
    entry = repo / "pipelines/mini"
    entry.parent.mkdir()
    data = tmp_path / "scientific_data"
    data.mkdir()
    source = data / "reads.fastq"
    source.write_bytes(b"irreplaceable scientific data")
    if kind == "directory":
        entry.mkdir()
        (entry / "notes.txt").write_bytes(b"existing research notes")
    else:
        entry.symlink_to(data if kind == "symlink" else tmp_path / "missing", target_is_directory=True)
    calls = []
    def fail_add(args, **kwargs):
        calls.append(args)
        if "add" in args and "submodule" in args:
            raise subprocess.CalledProcessError(1, args)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
    monkeypatch.setattr(dp, "_run", fail_add)
    assert not dp.add_one("mini", "https://github.com/nf-core/mini", "1.0.0", repo)
    assert entry.is_symlink() if kind != "directory" else (entry / "notes.txt").read_bytes() == b"existing research notes"
    assert source.read_bytes() == b"irreplaceable scientific data"
    assert not calls, "An existing pipeline entry must be refused before Git mutations or rollback"


def test_bump_pins_gitlink_to_new_tag(tmp_path, monkeypatch):
    _allow_file_submodules(monkeypatch)
    commits = _make_origin(tmp_path / "origin")
    _make_superproject(tmp_path / "repo")
    repo = tmp_path / "repo"
    url = (tmp_path / "origin").as_uri()

    assert dp.add_one("mini", url, "1.0.0", repo)              # start pinned at the old release
    assert up_mod.bump("mini", url, repo) == "1.1.0"           # auto-update to the newest tag
    _assert_pinned_to(repo, "mini", "1.1.0", commits["1.1.0"])
