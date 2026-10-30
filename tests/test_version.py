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
