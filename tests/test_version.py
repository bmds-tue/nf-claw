"""Which nfclaw wrote a bundle, and what `nfclaw --version` says (runner.version)."""
import re

from runner import version


def test_the_package_version_is_this_checkouts_pyproject():
    text = (version.ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(rf'^version = "{re.escape(version.package_version())}"$', text, re.M)


def test_the_commit_is_the_checkouts_head_or_none_outside_one():
    head = version.commit()
    assert head is None or re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", head)   # SHA-1 or SHA-256


def test_identity_and_description_agree(monkeypatch):
    monkeypatch.setattr(version, "commit", lambda: "a" * 40)
    assert version.identity() == {"version": version.package_version(), "commit": "a" * 40}
    assert version.describe() == f"nfclaw {version.package_version()} (commit {'a' * 12})"


def test_the_citation_names_this_version_and_no_release_the_changelog_lacks():
    # CITATION.cff claimed 1.0.0 was released on 2026-06-15, a date no release or tag ever had.
    cff = (version.ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert re.search(rf"^version: {re.escape(version.package_version())}$", cff, re.M)
    released = re.search(r'^date-released: "?(\d{4}-\d{2}-\d{2})"?$', cff, re.M)
    if released:                     # a release date is the one its changelog section records
        changelog = (version.ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert re.search(rf"^## \[?{re.escape(version.package_version())}\]?\b.*{released[1]}",
                         changelog, re.M)
