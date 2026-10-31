import subprocess

import pytest

from librarian import update_pipelines as up


def test_select_latest_ignores_prereleases():
    tags = ["v1.0.0", "1.2.0", "v1.10.0", "2.0.0-rc1", "nightly"]
    assert up.select_latest(tags) == "v1.10.0"


def test_select_latest_none_when_no_semver():
    assert up.select_latest(["dev", "main"]) is None


def test_relative_sources_resolved_against_repo_root(monkeypatch, tmp_path):
    # A relative --sources must resolve against --repo-root, not the CWD, so the source list and
    # `bump` (which builds paths from repo-root) always target the same repo — even when the caller
    # runs from elsewhere. Regression guard for the CWD/repo-root split.
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sources.tsv").write_text("a\thttps://x/a.git\tlatest-release\n")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    seen: list[str] = []
    monkeypatch.setattr(up, "bump", lambda name, url, root: (seen.append(name), "1.0.0")[1])
    monkeypatch.chdir(elsewhere)                              # run from outside the repo
    rc = up.main(["--sources", "sources.tsv", "--repo-root", str(repo)])
    assert rc == 0
    assert seen == ["a"]  # found the repo's sources.tsv, not CWD's


def test_one_failure_does_not_block_others(monkeypatch, tmp_path, capsys):
    tsv = tmp_path / "sources.tsv"
    tsv.write_text("a\thttps://x/a.git\nb\thttps://x/b.git\n")
    calls = []

    def fake_bump(name, url, repo_root):
        calls.append(name)
        if name == "a":
            raise RuntimeError("boom")
        return "1.2.3"

    monkeypatch.setattr(up, "bump", fake_bump)
    rc = up.main(["--sources", str(tsv), "--repo-root", str(tmp_path)])
    assert rc == 1  # process every source, but fail the automation so partial errors are visible
    assert calls == ["a", "b"]  # b still processed after a raised
    out = capsys.readouterr().out
    # The fake bump moves nothing, so b is reported as checked, not bumped.
    assert "a: ERROR" in out and "b: already at 1.2.3" in out


def test_report_distinguishes_a_bump_from_an_unchanged_pin(monkeypatch, tmp_path, capsys):
    tsv = tmp_path / "sources.tsv"
    tsv.write_text("moved\thttps://x/m.git\nsame\thttps://x/s.git\n")
    heads = {"moved": iter(["a" * 40, "b" * 40]), "same": iter(["c" * 40, "c" * 40])}
    monkeypatch.setattr(up.submod, "_own_head", lambda path: next(heads[path.parent.name]))
    monkeypatch.setattr(up, "bump", lambda name, url, root: "2.0.0")
    assert up.main(["--sources", str(tsv), "--repo-root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "moved: bumped to 2.0.0" in out and "same: already at 2.0.0" in out


def test_bump_refuses_an_uninitialised_submodule(monkeypatch, tmp_path):
    # Run in an uninitialised submodule's directory, `git -C <it> fetch/checkout` acts on the
    # nf-claw repository itself; bump must stop before touching git there.
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "pipelines" / "p" / "upstream").mkdir(parents=True)
    monkeypatch.setattr(up, "remote_tags", lambda url: ["1.0.0"])
    ran = []
    real_capture = up.capture
    monkeypatch.setattr(up, "capture",
                        lambda args, **kw: (ran.append(args), real_capture(args, **kw))[1])
    with pytest.raises(RuntimeError, match="not initialised"):
        up.bump("p", "https://x/p.git", tmp_path)
    assert not any("fetch" in a or "checkout" in a for a in ran)


def test_remote_tags_keep_whole_tag_names(monkeypatch):
    # `git ls-remote --tags --refs` lists `refs/tags/<name>`, and a name may hold a slash. Taking
    # the part after the last slash made `release/9.9.9` read as the release `9.9.9`, which the
    # updater then tried (and failed) to fetch as refs/tags/9.9.9.
    listing = ("a" * 40 + "\trefs/tags/1.2.0\n" + "b" * 40 + "\trefs/tags/release/9.9.9\n"
               + "c" * 40 + "\trefs/tags/v1.3.0\n")
    monkeypatch.setattr(up, "capture", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 0, listing, ""))
    assert up.remote_tags("https://example.invalid/p.git") == ["1.2.0", "release/9.9.9",
                                                                "v1.3.0"]
    assert up.select_latest(up.remote_tags("https://example.invalid/p.git")) == "v1.3.0"
