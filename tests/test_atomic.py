"""runner.atomic: whole-file replacement with the permissions of any new file."""
import os
import stat

import pytest

from runner import atomic


@pytest.fixture
def umask_022():
    previous = os.umask(0o022)
    yield
    os.umask(previous)


def test_a_new_file_gets_the_permissions_of_any_new_file(tmp_path, umask_022):
    path = tmp_path / "record.json"
    atomic.write_text(path, "{}\n")
    assert path.read_text() == "{}\n"
    assert stat.S_IMODE(path.stat().st_mode) == 0o644
    assert [p.name for p in tmp_path.iterdir()] == ["record.json"]


def test_a_given_mode_replaces_the_default_and_the_old_bytes(tmp_path, umask_022):
    path = tmp_path / "state.json"
    path.write_text("old")
    atomic.write_bytes(path, b"new", mode=0o600)
    assert path.read_bytes() == b"new"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    atomic.write_bytes(path, b"run", mode=0o755)
    assert stat.S_IMODE(path.stat().st_mode) == 0o755


def test_a_failed_write_keeps_the_old_file_and_leaves_no_temporary(tmp_path, monkeypatch):
    path = tmp_path / "manifest.json"
    path.write_text("previous")

    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr(atomic.os, "replace", fail)
    with pytest.raises(OSError, match="disk full"):
        atomic.write_text(path, "next")
    assert path.read_text() == "previous"
    assert [p.name for p in tmp_path.iterdir()] == ["manifest.json"]


def test_a_temporary_name_already_taken_is_never_overwritten(tmp_path, monkeypatch):
    path = tmp_path / "job.json"
    taken = tmp_path / ".job.json.00000000.tmp"
    taken.write_text("another writer's file")
    names = iter([bytes(4), b"\x01\x02\x03\x04"])
    monkeypatch.setattr(atomic.os, "urandom", lambda n: next(names))
    atomic.write_text(path, "mine")
    assert path.read_text() == "mine"
    assert taken.read_text() == "another writer's file"
