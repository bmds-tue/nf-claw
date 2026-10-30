import shutil
import subprocess
from pathlib import Path

import pytest

from runner import submodule as submod
from runner import versions
from runner.errors import ErrorCode, NfclawError
from runner.submodule import SubmoduleStatus


@pytest.fixture(autouse=True)
def _make_tmp_removable(tmp_path):
    """Git pack objects under a worktree are written read-only. Make the whole tree
    writable on teardown so pytest's tmp-retention cleanup never trips over them and
    floods later runs with `rm_rf` warnings."""
    yield
    for p in sorted(tmp_path.rglob("*"), reverse=True):
        try:
            p.chmod(0o700)
        except OSError:
            pass


# --- _url_for: read the submodule URL straight from .gitmodules (offline, no git) ---
def test_url_for_reads_gitmodules(tmp_path):
    (tmp_path / ".gitmodules").write_text(
        '[submodule "pipelines/sarek/upstream"]\n'
        "\tpath = pipelines/sarek/upstream\n"
        "\turl = https://github.com/nf-core/sarek.git\n"
        '[submodule "pipelines/rnaseq/upstream"]\n'
        "\tpath = pipelines/rnaseq/upstream\n"
        "\turl = https://github.com/nf-core/rnaseq.git\n")
    assert versions._url_for("rnaseq", tmp_path) == "https://github.com/nf-core/rnaseq.git"
    assert versions._url_for("sarek", tmp_path) == "https://github.com/nf-core/sarek.git"


def test_url_for_none_when_absent(tmp_path):
    assert versions._url_for("nope", tmp_path) is None          # no .gitmodules at all
    (tmp_path / ".gitmodules").write_text(
        '[submodule "pipelines/sarek/upstream"]\n\turl = x\n')
    assert versions._url_for("rnaseq", tmp_path) is None        # name not present


# --- release_tags: semver only, newest first, union of remote + local, deduped ---
def test_release_tags_semver_only_newest_first(tmp_path, monkeypatch):
    monkeypatch.setattr(versions, "_url_for", lambda *a, **k: "url")
    monkeypatch.setattr(versions, "remote_tags",
                        lambda url: ["1.2.0", "2.0.0", "dev", "2.0.0-rc1", "v1.10.0"])
    monkeypatch.setattr(versions, "_local_tags", lambda up: ["1.1.0"])
    assert versions.release_tags("p", pipelines_dir=tmp_path, repo_root=tmp_path) == [
        "2.0.0", "v1.10.0", "1.2.0", "1.1.0"]


def test_release_tags_include_two_part_nfcore_releases(tmp_path, monkeypatch):
    # nf-core released as `X.Y` before settling on `X.Y.Z` — fetchngs 1.0–1.9, sarek 2.5–2.7,
    # rnaseq 1.0–3.9 and others. They are real releases, so they are listed and runnable.
    monkeypatch.setattr(versions, "_url_for", lambda *a, **k: "url")
    monkeypatch.setattr(versions, "remote_tags",
                        lambda url: ["1.9", "1.10.0", "1.0", "2.0", "dev", "1.4.2", "1.2-rc"])
    monkeypatch.setattr(versions, "_local_tags", lambda up: [])
    tags = versions.release_tags("p", pipelines_dir=tmp_path, repo_root=tmp_path)
    assert tags == ["2.0", "1.10.0", "1.9", "1.4.2", "1.0"]
    monkeypatch.setattr(versions, "release_tags", lambda *a, **k: tags)
    assert versions.resolve("p", "1.9", pipelines_dir=tmp_path, repo_root=tmp_path) == "1.9"
    assert versions.resolve("p", "v1.9", pipelines_dir=tmp_path, repo_root=tmp_path) == "1.9"


def test_release_tags_offline_falls_back_to_local(tmp_path, monkeypatch):
    monkeypatch.setattr(versions, "_url_for", lambda *a, **k: "url")
    monkeypatch.setattr(versions, "remote_tags", lambda url: [])   # network down
    monkeypatch.setattr(versions, "_local_tags", lambda up: ["1.0.0", "1.1.0"])
    assert versions.release_tags("p", pipelines_dir=tmp_path, repo_root=tmp_path) == [
        "1.1.0", "1.0.0"]


# --- _match_tag: tolerate the optional leading 'v' on either side ---
def test_match_tag_normalizes_v_prefix():
    assert versions._match_tag("2.0.0", ["2.0.0", "1.0.0"]) == "2.0.0"
    assert versions._match_tag("v2.0.0", ["2.0.0"]) == "2.0.0"
    assert versions._match_tag("2.0.0", ["v2.0.0"]) == "v2.0.0"
    assert versions._match_tag("9.9.9", ["2.0.0"]) is None


# --- resolve: validate against real tags; raise VERSION_NOT_FOUND with the list ---
def test_resolve_returns_canonical_tag(tmp_path, monkeypatch):
    monkeypatch.setattr(versions, "release_tags", lambda *a, **k: ["2.0.0", "1.2.0"])
    assert versions.resolve("p", "v1.2.0", pipelines_dir=tmp_path, repo_root=tmp_path) == "1.2.0"


def test_resolve_unknown_version_raises_with_available(tmp_path, monkeypatch):
    monkeypatch.setattr(versions, "release_tags", lambda *a, **k: ["2.0.0", "1.2.0"])
    with pytest.raises(NfclawError) as exc:
        versions.resolve("p", "9.9.9", pipelines_dir=tmp_path, repo_root=tmp_path)
    assert exc.value.code == ErrorCode.VERSION_NOT_FOUND
    assert exc.value.details["available"] == ["2.0.0", "1.2.0"]


# --- ensure: the orchestrator that downstream code consumes ---
def test_ensure_none_uses_pinned_submodule(tmp_path, monkeypatch):
    sentinel = object()
    monkeypatch.setattr(versions.submod, "ensure_initialized",
                        lambda name, pdir, root: sentinel)
    assert versions.ensure("p", None, pipelines_dir=tmp_path, repo_root=tmp_path) is sentinel


def test_ensure_requested_equals_pin_skips_cache(tmp_path, monkeypatch):
    pin = SubmoduleStatus("p", tmp_path / "up", True, True, "2.0.0", "abc", ())
    monkeypatch.setattr(versions.submod, "ensure_initialized", lambda *a, **k: pin)
    monkeypatch.setattr(versions, "resolve", lambda *a, **k: "2.0.0")
    materialized = {}
    monkeypatch.setattr(versions, "materialize",
                        lambda *a, **k: materialized.setdefault("called", True))
    assert versions.ensure("p", "v2.0.0", pipelines_dir=tmp_path, repo_root=tmp_path) is pin
    assert "called" not in materialized                         # no needless worktree


def test_ensure_other_version_materializes(tmp_path, monkeypatch):
    pin = SubmoduleStatus("p", tmp_path / "up", True, True, "2.0.0", "abc", ())
    cached = SubmoduleStatus("p", tmp_path / "cache", True, True, "1.2.0", "def", ())
    monkeypatch.setattr(versions.submod, "ensure_initialized", lambda *a, **k: pin)
    monkeypatch.setattr(versions, "resolve", lambda *a, **k: "1.2.0")
    monkeypatch.setattr(versions, "materialize", lambda name, tag, **k: cached)
    assert versions.ensure("p", "1.2.0", pipelines_dir=tmp_path, repo_root=tmp_path) is cached


# --- available: every release tag, the committed pin flagged ---
def test_available_flags_the_pin(tmp_path, monkeypatch):
    d = tmp_path / "pipelines" / "p"
    (d / "upstream").mkdir(parents=True)
    d.joinpath("skill.md").write_text("---\nname: p\nversion: 2.0.0\n---\n# p\n")
    monkeypatch.setattr(versions, "release_tags", lambda *a, **k: ["2.0.0", "1.2.0"])
    assert versions.available("p", pipelines_dir=tmp_path / "pipelines", repo_root=tmp_path) == [
        ("2.0.0", True), ("1.2.0", False)]


# --- materialize: a real git worktree pinned to the tag (the robustness core) ---
_GIT_ID = ("-c", "user.email=t@t", "-c", "user.name=t")


def _git(path, *args, **kw):
    subprocess.run(["git", "-C", str(path), *args], check=True,
                   capture_output=True, text=True, **kw)


def _upstream_repo_with_tag(pipelines_dir, name, tag):
    up = pipelines_dir / name / "upstream"
    up.mkdir(parents=True)
    (up / "main.nf").write_text("workflow {}\n")
    (up / "nextflow.config").write_text("manifest {}\n")
    (up / "nextflow_schema.json").write_text("{}\n")
    _git(up, "init", "-q", "-b", "main")
    _git(up, *_GIT_ID, "add", ".")
    _git(up, *_GIT_ID, "commit", "-q", "-m", "init")
    _git(up, "tag", tag)
    return up


def test_materialize_checks_out_tag_into_cache(tmp_path):
    pdir = tmp_path / "pipelines"
    _upstream_repo_with_tag(pdir, "p", "1.2.0")
    st = versions.materialize("p", "1.2.0", pipelines_dir=pdir, repo_root=tmp_path)
    assert st.version == "1.2.0"
    assert st.complete is True
    assert st.path == pdir / "p" / versions.CACHE_DIRNAME / "1.2.0" / "upstream"
    assert (st.path / "main.nf").read_text() == "workflow {}\n"
    assert versions.is_cached(st) is True


def test_materialize_is_idempotent(tmp_path):
    pdir = tmp_path / "pipelines"
    _upstream_repo_with_tag(pdir, "p", "1.2.0")
    first = versions.materialize("p", "1.2.0", pipelines_dir=pdir, repo_root=tmp_path)
    second = versions.materialize("p", "1.2.0", pipelines_dir=pdir, repo_root=tmp_path)
    assert first.path == second.path and second.complete is True


def test_materialize_refuses_a_complete_cache_at_the_wrong_release(tmp_path):
    pdir = tmp_path / "pipelines"
    up = _upstream_repo_with_tag(pdir, "p", "1.2.0")
    first = versions.materialize("p", "1.2.0", pipelines_dir=pdir, repo_root=tmp_path)
    other = _commit_tree(up, "other release", {"main.nf": "workflow { /* different */ }\n"})
    _git(up, "tag", "2.0.0")
    _git(first.path, "checkout", "--detach", other)
    marker = first.path / "user-notes.txt"
    marker.write_text("preserve my changes")
    with pytest.raises(NfclawError) as exc:
        versions.materialize("p", "1.2.0", pipelines_dir=pdir, repo_root=tmp_path)
    assert exc.value.code == ErrorCode.SUBMODULE_INCOMPLETE
    assert "does not match" in str(exc.value)
    assert marker.read_text() == "preserve my changes"
    assert submod.resolve_at("p", first.path).commit == other


def test_materialize_refuses_complete_copied_files_without_cache_git_metadata(tmp_path):
    pdir = tmp_path / "pipelines"
    _upstream_repo_with_tag(pdir, "p", "1.2.0")
    dest = versions.cache_dir("p", "1.2.0", pdir) / "upstream"
    dest.mkdir(parents=True)
    for filename in submod.REQUIRED_FILES:
        (dest / filename).write_text("copied user file")
    with pytest.raises(NfclawError) as exc:
        versions.materialize("p", "1.2.0", pipelines_dir=pdir, repo_root=tmp_path)
    assert exc.value.code == ErrorCode.SUBMODULE_INCOMPLETE
    assert "does not match" in str(exc.value)
    assert (dest / "main.nf").read_text() == "copied user file"


def test_materialize_preserves_a_partial_cache(tmp_path):
    pdir = tmp_path / "pipelines"
    _upstream_repo_with_tag(pdir, "p", "1.2.0")
    dest = versions.cache_dir("p", "1.2.0", pdir) / "upstream"
    dest.mkdir(parents=True)
    (dest / "main.nf").write_text("partial\n")               # old check mistook this for complete
    with pytest.raises(NfclawError, match="Incomplete version cache already exists"):
        versions.materialize("p", "1.2.0", pipelines_dir=pdir, repo_root=tmp_path)
    assert (dest / "main.nf").read_text() == "partial\n"


def test_materialize_failure_is_a_structured_error(tmp_path, monkeypatch):
    upstream = tmp_path / "pipelines" / "p" / "upstream"
    upstream.mkdir(parents=True)
    incomplete = SubmoduleStatus("p", upstream, False, False, "", "", ("main.nf",))
    monkeypatch.setattr(versions.submod, "resolve_at", lambda *a, **k: incomplete)
    monkeypatch.setattr(versions.submod, "is_git_tree", lambda *a, **k: True)
    monkeypatch.setattr(versions, "_has_tag", lambda *a, **k: False)
    monkeypatch.setattr(
        versions, "_fetch_tag",
        lambda *a, **k: (_ for _ in ()).throw(
            subprocess.CalledProcessError(1, ["git", "fetch"], stderr="offline")))
    with pytest.raises(NfclawError) as exc:
        versions.materialize("p", "1.2.0", pipelines_dir=tmp_path / "pipelines",
                             repo_root=tmp_path)
    assert exc.value.code == ErrorCode.SUBMODULE_INCOMPLETE
    assert "offline" in str(exc.value)


# --- generate_docs: reuse the librarian renderer for an arbitrary version's tree ---
def test_generate_docs_writes_version_markdowns(tmp_path):
    fix = Path(__file__).parent / "fixtures" / "mini"
    dest = tmp_path / ".versions" / "1.2.0" / "upstream"
    dest.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config"):
        (dest / f).write_text("x")
    shutil.copy(fix / "nextflow_schema.json", dest / "nextflow_schema.json")
    st = SubmoduleStatus("mini", dest, True, True, "1.2.0", "abc123", ())
    skill_path, ref_path = versions.generate_docs(st, dest_dir=dest.parent)
    assert skill_path == dest.parent / "skill.md"
    assert "# mini" in skill_path.read_text()
    assert "version: 1.2.0" in skill_path.read_text()
    assert "mini" in ref_path.read_text()


# --- dev: the unreleased development branch, resolved to an immutable per-commit tree ---------
# A real nf-core-like remote (release on `main`, development on `dev`) and a shallow clone of the
# release as the "submodule", exactly as `git submodule update --init --depth 1` leaves it.

def _commit_tree(repo, msg, files):
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    _git(repo, *_GIT_ID, "add", ".")
    _git(repo, *_GIT_ID, "commit", "-q", "-m", msg)
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()


_PIPELINE_FILES = {"main.nf": "workflow {}\n", "nextflow.config": "manifest {}\n",
                   "nextflow_schema.json": "{}\n"}


def _nfcore_remote(tmp_path, *, with_dev=True):
    """`remote/` with release 1.0.0 on main and (optionally) one commit ahead on `dev`.
    Returns (remote_url, release_sha, dev_sha_or_None)."""
    remote = tmp_path / "remote"
    remote.mkdir()
    _git(remote, "init", "-q", "-b", "main")
    release = _commit_tree(remote, "release", _PIPELINE_FILES)
    _git(remote, "tag", "1.0.0")
    dev = None
    if with_dev:
        _git(remote, "checkout", "-q", "-b", "dev")
        dev = _commit_tree(remote, "dev work", {"main.nf": "workflow { /* dev */ }\n"})
        _git(remote, "checkout", "-q", "main")
    return f"file://{remote}", release, dev


def _library(tmp_path, url, name="p"):
    """An nf-claw-shaped repo root: `.gitmodules` naming the remote, and the pipeline's
    `upstream/` as a shallow, single-branch clone of the release (no `dev` objects locally)."""
    root = tmp_path / "lib"
    pdir = root / "pipelines"
    (pdir / name).mkdir(parents=True)
    (root / ".gitmodules").write_text(
        f'[submodule "pipelines/{name}/upstream"]\n'
        f"\tpath = pipelines/{name}/upstream\n\turl = {url}\n")
    subprocess.run(["git", "clone", "-q", "--depth", "1", "--single-branch", "--branch", "main",
                    url, str(pdir / name / "upstream")], check=True, capture_output=True)
    return root, pdir


def _advance_dev(tmp_path, text):
    remote = tmp_path / "remote"
    _git(remote, "checkout", "-q", "dev")
    sha = _commit_tree(remote, "more dev work", {"main.nf": text})
    _git(remote, "checkout", "-q", "main")
    return sha


@pytest.mark.parametrize("raw,expected", [
    ("dev", True), (" dev ", True), ("DEV", True), ("Dev", True),
    ("1.0.0", False), ("v1.0.0", False), ("develop", False), ("dev1", False), ("", False),
    (None, False)])
def test_is_dev_request(raw, expected):
    assert versions.is_dev_request(raw) is expected


def test_dev_label_is_commit_keyed():
    assert versions.dev_label("f754e0a247b03f169782dbb5c688e055044a5988") == "dev-f754e0a247b0"


def test_remote_branch_head_found_missing_and_unreachable(tmp_path):
    url, _, dev = _nfcore_remote(tmp_path)
    assert versions.remote_branch_head(url, "dev") == dev
    assert versions.remote_branch_head(url, "no-such-branch") is None     # reachable, no branch
    with pytest.raises(versions.RemoteUnavailable):                       # never "no branch"
        versions.remote_branch_head(f"file://{tmp_path}/does-not-exist", "dev")


def test_materialize_dev_checks_out_the_dev_head(tmp_path):
    url, release, dev = _nfcore_remote(tmp_path)
    root, pdir = _library(tmp_path, url)
    st = versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)
    assert st.version == "dev" and st.commit == dev and st.complete
    assert st.path == pdir / "p" / versions.CACHE_DIRNAME / versions.dev_label(dev) / "upstream"
    assert (st.path / "main.nf").read_text() == "workflow { /* dev */ }\n"
    assert versions.is_cached(st)
    # it is announced as unreleased code, naming the exact commit
    assert any("unreleased" in n and dev in n for n in st.notes)
    # the pinned release tree is untouched
    assert (pdir / "p" / "upstream" / "main.nf").read_text() == "workflow {}\n"
    # and the head is remembered for the offline fallback
    assert versions._local_dev_head(pdir / "p" / "upstream") == dev


def test_materialize_dev_follows_the_branch_and_keeps_earlier_commits_intact(tmp_path):
    url, _, first = _nfcore_remote(tmp_path)
    root, pdir = _library(tmp_path, url)
    a = versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)
    second = _advance_dev(tmp_path, "workflow { /* dev v2 */ }\n")
    b = versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)
    assert (a.commit, b.commit) == (first, second)
    assert a.path != b.path                                     # a new head never replaces a tree
    assert (a.path / "main.nf").read_text() == "workflow { /* dev */ }\n"   # replays stay faithful
    assert (b.path / "main.nf").read_text() == "workflow { /* dev v2 */ }\n"


def test_materialize_dev_reuses_a_complete_tree_without_fetching(tmp_path, monkeypatch):
    url, _, dev = _nfcore_remote(tmp_path)
    root, pdir = _library(tmp_path, url)
    first = versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)
    monkeypatch.setattr(versions, "_fetch_dev",
                        lambda *a, **k: pytest.fail("an unchanged dev head must not be refetched"))
    again = versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)
    assert again.path == first.path and again.commit == dev


def test_materialize_dev_runs_the_newer_head_when_dev_moves_mid_resolution(tmp_path, monkeypatch):
    # ls-remote saw one head, but by the time it is fetched dev has moved on: run what was fetched
    # (the newer development code) rather than failing on a commit that is no longer the head.
    url, _, stale = _nfcore_remote(tmp_path)
    root, pdir = _library(tmp_path, url)
    newer = _advance_dev(tmp_path, "workflow { /* moved */ }\n")
    monkeypatch.setattr(versions, "remote_branch_head", lambda *a, **k: stale)
    st = versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)
    assert st.commit == newer
    assert (st.path / "main.nf").read_text() == "workflow { /* moved */ }\n"


def test_materialize_dev_offline_falls_back_to_last_fetched_head(tmp_path, monkeypatch):
    url, _, dev = _nfcore_remote(tmp_path)
    root, pdir = _library(tmp_path, url)
    online = versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)

    def unreachable(*a, **k):
        raise versions.RemoteUnavailable("network down")

    monkeypatch.setattr(versions, "remote_branch_head", unreachable)
    offline = versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)
    assert offline.path == online.path and offline.commit == dev
    # the stale-head risk is said first, then the unreleased-code advisory
    assert "could not reach" in offline.notes[0] and dev[:12] in offline.notes[0]
    assert any("unreleased" in n for n in offline.notes)


def test_materialize_dev_refuses_a_cache_at_a_different_commit(tmp_path):
    url, release, dev = _nfcore_remote(tmp_path)
    root, pdir = _library(tmp_path, url)
    first = versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)
    _git(first.path, "checkout", "--detach", release)
    marker = first.path / "user-notes.txt"
    marker.write_text("keep this file")
    with pytest.raises(NfclawError) as exc:
        versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)
    assert exc.value.code == ErrorCode.SUBMODULE_INCOMPLETE
    assert "does not match" in str(exc.value) and dev in str(exc.value)
    assert submod.resolve_at("p", first.path).commit == release
    assert marker.read_text() == "keep this file"


def test_materialize_dev_offline_with_nothing_fetched_is_a_clear_error(tmp_path, monkeypatch):
    url, _, _ = _nfcore_remote(tmp_path)
    root, pdir = _library(tmp_path, url)

    def unreachable(*a, **k):
        raise versions.RemoteUnavailable("network down")

    monkeypatch.setattr(versions, "remote_branch_head", unreachable)
    with pytest.raises(NfclawError) as exc:
        versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)
    assert exc.value.code == ErrorCode.SUBMODULE_INCOMPLETE
    assert "network" in str(exc.value)


def test_materialize_dev_without_a_dev_branch_is_version_not_found(tmp_path):
    url, _, _ = _nfcore_remote(tmp_path, with_dev=False)
    root, pdir = _library(tmp_path, url)
    with pytest.raises(NfclawError) as exc:
        versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)
    assert exc.value.code == ErrorCode.VERSION_NOT_FOUND
    assert "no 'dev' branch" in str(exc.value)
    assert not (pdir / "p" / versions.CACHE_DIRNAME).exists()             # nothing half-made


def test_materialize_dev_rejects_an_incomplete_dev_tree(tmp_path):
    url, _, _ = _nfcore_remote(tmp_path)
    remote = tmp_path / "remote"
    _git(remote, "checkout", "-q", "dev")
    _git(remote, "rm", "-q", "nextflow_schema.json")
    _git(remote, *_GIT_ID, "commit", "-q", "-m", "restructure")
    _git(remote, "checkout", "-q", "main")
    root, pdir = _library(tmp_path, url)
    with pytest.raises(NfclawError) as exc:
        versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)
    assert exc.value.code == ErrorCode.SUBMODULE_INCOMPLETE
    assert "nextflow_schema.json" in str(exc.value)


def test_materialize_dev_git_failure_is_a_structured_error(tmp_path, monkeypatch):
    url, _, _ = _nfcore_remote(tmp_path)
    root, pdir = _library(tmp_path, url)
    monkeypatch.setattr(
        versions, "_fetch_dev",
        lambda *a, **k: (_ for _ in ()).throw(
            subprocess.CalledProcessError(1, ["git", "fetch"], stderr="connection reset")))
    with pytest.raises(NfclawError) as exc:
        versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)
    assert exc.value.code == ErrorCode.SUBMODULE_INCOMPLETE
    assert "connection reset" in str(exc.value)


def test_local_dev_head_ignores_the_enclosing_repository(tmp_path):
    # An uninitialized submodule is an empty directory inside the nf-claw repo; git run there would
    # answer for nf-claw itself. Its own `origin/dev` must never be mistaken for the pipeline's.
    outer = tmp_path / "outer"
    outer.mkdir()
    _git(outer, "init", "-q", "-b", "main")
    sha = _commit_tree(outer, "outer", {"README": "x\n"})
    _git(outer, "update-ref", "refs/remotes/origin/dev", sha)
    empty = outer / "pipelines" / "p" / "upstream"
    empty.mkdir(parents=True)
    assert versions._local_dev_head(empty) == ""


def test_dev_head_reports_freshness(tmp_path):
    url, _, dev = _nfcore_remote(tmp_path)
    root, pdir = _library(tmp_path, url)
    assert versions.dev_head("p", pipelines_dir=pdir, repo_root=root) == (dev, True)
    (root / ".gitmodules").write_text("")                        # no remote known → local only
    assert versions.dev_head("p", pipelines_dir=pdir, repo_root=root) == (None, False)
    (root / ".gitmodules").write_text(
        f'[submodule "pipelines/p/upstream"]\n\turl = {url}\n')
    versions.materialize_dev("p", pipelines_dir=pdir, repo_root=root)
    (root / ".gitmodules").write_text("")                        # offline again: last fetched head
    assert versions.dev_head("p", pipelines_dir=pdir, repo_root=root) == (dev, False)


def test_ensure_dev_routes_to_materialize_dev(tmp_path, monkeypatch):
    pin = SubmoduleStatus("p", tmp_path / "up", True, True, "2.0.0", "abc", ())
    dev = SubmoduleStatus("p", tmp_path / ".versions" / "dev-x" / "upstream", True, True,
                          "dev", "f" * 40, ())
    monkeypatch.setattr(versions.submod, "ensure_initialized", lambda *a, **k: pin)
    monkeypatch.setattr(versions, "resolve",
                        lambda *a, **k: pytest.fail("dev is a branch, not a release tag"))
    monkeypatch.setattr(versions, "materialize_dev", lambda name, **k: dev)
    assert versions.ensure("p", "dev", pipelines_dir=tmp_path, repo_root=tmp_path) is dev
    assert versions.ensure("p", "DEV", pipelines_dir=tmp_path, repo_root=tmp_path) is dev


def test_ensure_dev_end_to_end_with_real_git(tmp_path):
    url, release, dev = _nfcore_remote(tmp_path)
    root, pdir = _library(tmp_path, url)
    # the pinned skill.md lets submodule.resolve report the release, as in the real library
    (pdir / "p" / "skill.md").write_text(f"---\nname: p\nversion: 1.0.0\ncommit: {release}\n---\n")
    st = versions.ensure("p", "dev", pipelines_dir=pdir, repo_root=root)
    assert st.version == "dev" and st.commit == dev and versions.is_cached(st)


def test_unknown_version_error_mentions_dev(tmp_path, monkeypatch):
    monkeypatch.setattr(versions, "release_tags", lambda *a, **k: ["2.0.0"])
    with pytest.raises(NfclawError) as exc:
        versions.resolve("p", "9.9.9", pipelines_dir=tmp_path, repo_root=tmp_path)
    assert "`dev`" in exc.value.fix


def test_generate_docs_for_dev_commit(tmp_path):
    fix = Path(__file__).parent / "fixtures" / "mini"
    sha = "f754e0a247b03f169782dbb5c688e055044a5988"
    dest = tmp_path / ".versions" / versions.dev_label(sha) / "upstream"
    dest.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config"):
        (dest / f).write_text("x")
    shutil.copy(fix / "nextflow_schema.json", dest / "nextflow_schema.json")
    st = SubmoduleStatus("mini", dest, True, True, "dev", sha, ())
    skill_path, _ = versions.generate_docs(st, dest_dir=dest.parent)
    text = skill_path.read_text()
    assert "version: dev" in text and f"commit: {sha}" in text
    assert "--pipeline-version dev" in text
    assert f"pipelines/mini/.versions/dev-{sha[:12]}/upstream" in text


def _outer_repo_with_tag(root, tag):
    """The nf-claw checkout itself, carrying a semver tag of its own."""
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, *_GIT_ID, "commit", "-q", "--allow-empty", "-m", "init")
    _git(root, "tag", tag)


def test_uninitialised_submodule_never_lists_nf_claws_own_tags(tmp_path):
    # `git tag --list` in an uninitialised submodule's (empty) directory lists the enclosing nf-claw
    # repository's tags, which `nfclaw versions` then offered as releases of the pipeline.
    _outer_repo_with_tag(tmp_path, "v9.9.9")
    up = tmp_path / "pipelines" / "p" / "upstream"
    up.mkdir(parents=True)
    assert versions._local_tags(up) == []
    assert versions.release_tags("p", pipelines_dir=tmp_path / "pipelines",
                                 repo_root=tmp_path) == []


def test_materialize_refuses_a_tree_that_is_not_its_own_clone(tmp_path):
    # Copied files inside the nf-claw checkout: fetching/adding a worktree "there" would act on
    # nf-claw itself (fetch the tag into it, shallow it, register a worktree of it).
    _outer_repo_with_tag(tmp_path, "1.2.0")
    up = tmp_path / "pipelines" / "p" / "upstream"
    up.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config", "nextflow_schema.json"):
        (up / f).write_text("x")
    with pytest.raises(NfclawError) as exc:
        versions.materialize("p", "1.2.0", pipelines_dir=tmp_path / "pipelines", repo_root=tmp_path)
    assert exc.value.code == ErrorCode.SUBMODULE_INCOMPLETE
    assert "not a git checkout" in str(exc.value)
    out = subprocess.run(["git", "-C", str(tmp_path), "worktree", "list"], capture_output=True,
                         text=True, check=True).stdout
    assert len(out.splitlines()) == 1  # no worktree registered against nf-claw


def test_materialize_dev_refuses_a_tree_that_is_not_its_own_clone(tmp_path):
    # The `dev` path needs the same guard as a release: with copied files in place of the clone,
    # `git -C upstream fetch origin dev` and `worktree add` act on the nf-claw checkout itself. Here
    # nf-claw's own `origin` even has a `dev` branch, so the fetch would succeed — shallowing
    # nf-claw, writing its `origin/dev`, and registering the cache as a worktree of nf-claw.
    url, _, _ = _nfcore_remote(tmp_path)
    root = tmp_path / "lib"
    _outer_repo_with_tag(root, "v0.1.0")
    _git(root, "remote", "add", "origin", url)
    (root / ".gitmodules").write_text(f'[submodule "pipelines/p/upstream"]\n\turl = {url}\n')
    up = root / "pipelines" / "p" / "upstream"
    up.mkdir(parents=True)
    for f in ("main.nf", "nextflow.config", "nextflow_schema.json"):
        (up / f).write_text("x")
    with pytest.raises(NfclawError) as exc:
        versions.materialize_dev("p", pipelines_dir=root / "pipelines", repo_root=root)
    assert exc.value.code == ErrorCode.SUBMODULE_INCOMPLETE
    assert "not a git checkout" in str(exc.value)
    assert "git submodule update --init pipelines/p/upstream" in exc.value.fix
    worktrees = subprocess.run(["git", "-C", str(root), "worktree", "list"], capture_output=True,
                               text=True, check=True).stdout
    assert len(worktrees.splitlines()) == 1
    refs = subprocess.run(["git", "-C", str(root), "for-each-ref", "refs/remotes"],
                          capture_output=True, text=True, check=True).stdout
    assert refs == ""                                        # nothing fetched into nf-claw
    assert not (root / ".git" / "shallow").exists()


def test_release_git_calls_never_wait_on_a_credential_prompt(tmp_path, monkeypatch):
    # A wrong or renamed remote makes git ask for a username on the terminal; `nfclaw versions` and
    # a release fetch must fail instead of hanging until their timeout — as the `dev` calls
    # already do.
    seen = []

    def fake_run(cmd, **kw):
        seen.append((cmd, kw.get("env") or {}))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(versions, "capture", fake_run)
    versions.remote_tags("https://example.invalid/x")
    versions._fetch_tag(tmp_path, "1.0.0")
    assert [c[1] for c, _ in seen] == ["ls-remote", "-C"]
    assert all(env.get("GIT_TERMINAL_PROMPT") == "0" for _, env in seen)


def test_explicit_verified_local_pin_does_not_need_remote_tag_inventory(tmp_path, monkeypatch):
    pin = SubmoduleStatus('p', tmp_path / 'up', True, True, '2.0.0', 'abc', ())
    monkeypatch.setattr(versions.submod, 'ensure_initialized', lambda *a, **k: pin)
    monkeypatch.setattr(versions, 'release_tags',
                        lambda *a, **k: pytest.fail('verified local pin requested tags'))
    assert versions.ensure('p', 'v2.0.0', pipelines_dir=tmp_path, repo_root=tmp_path) is pin
