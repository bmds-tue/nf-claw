"""Inputs and outputs are hashed several files at once, with the same digests and errors.

SHA-256 ran at 314 MB/s on one core of the validation server, well below its storage, and every run
hashes its inputs twice and its outputs once: eight threads hashed 3.2 GB of cached data in 1.3 s
instead of 10.2 s.
"""
import hashlib
import threading
import time

import pytest

from runner import outputs, provenance, replay_guard


def _tree(root, count=24):
    for index in range(count):
        path = root / f"d{index % 3}" / f"f{index:02d}.bin"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes([index]) * (1000 + index))
    return sorted(root.rglob("*.bin"))


def test_digests_are_those_of_hashing_one_file_at_a_time(tmp_path):
    files = _tree(tmp_path)
    expected = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    assert replay_guard.hash_files(files + files[:5]) == expected        # duplicates hashed once
    checksums, _ = replay_guard.snapshot_inputs([tmp_path])
    assert checksums == {str(path): digest for path, digest in expected.items()}
    assert replay_guard.hash_inputs([tmp_path]) == checksums
    hashes, _, _ = outputs.snapshot(tmp_path, provenance.sha256_file)
    assert hashes == {path.relative_to(tmp_path).as_posix(): digest
                      for path, digest in expected.items()}


def test_files_are_hashed_concurrently(tmp_path, monkeypatch):
    monkeypatch.setattr(replay_guard, "_HASH_WORKERS", 4)
    active, peak, lock = 0, 0, threading.Lock()

    def slow(path):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return provenance.sha256_file(path)

    replay_guard.hash_files(_tree(tmp_path, 8), slow)
    assert peak > 1


def test_the_error_is_the_first_one_in_order(tmp_path, monkeypatch):
    monkeypatch.setattr(replay_guard, "_HASH_WORKERS", 4)
    files = _tree(tmp_path, 8)

    def failing(path):
        if path in (files[2], files[5]):
            raise PermissionError(13, "Permission denied", str(path))
        return provenance.sha256_file(path)

    with pytest.raises(PermissionError) as raised:
        replay_guard.hash_files(files, failing)
    assert raised.value.filename == str(files[2])
