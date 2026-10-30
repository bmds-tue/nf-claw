"""Runs and chains refuse a system without POSIX file locks instead of running unlocked.

Native Windows has no `fcntl`: `nfclaw run` used to skip its --outdir writer lock there (so two runs
could write one directory), while MCP jobs and source corrections already refused. Nextflow itself
runs only on POSIX systems (WSL 2 on Windows).
"""
import pytest

from runner import chain, locking
from runner.errors import ErrorCode, NfclawError


def test_a_run_without_posix_locks_is_refused_not_left_unlocked(tmp_path, monkeypatch):
    monkeypatch.setattr(locking, "fcntl", None)
    with pytest.raises(NfclawError, match="nfclaw run needs a POSIX system") as refused:
        with locking.output_writer(tmp_path / "out"):
            pytest.fail("ran without a writer lock")
    assert refused.value.code is ErrorCode.ENVIRONMENT and "WSL 2" in refused.value.fix
    assert list(tmp_path.iterdir()) == []
    with locking.output_writer(tmp_path / "out", check_only=True):     # --check takes no lock
        pass


def test_a_chain_without_posix_locks_is_refused_before_its_record(tmp_path, monkeypatch):
    monkeypatch.setattr(chain, "fcntl", None)
    with pytest.raises(NfclawError, match="nfclaw chain run needs a POSIX system"):
        with chain._lock(tmp_path / "c" / chain.RECORD_DIRNAME, tmp_path / "c"):
            pytest.fail("ran without a chain lock")
    assert not (tmp_path / "c").exists()
