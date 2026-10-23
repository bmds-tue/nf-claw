"""Stable host identity must distinguish machines and Linux PID namespaces."""
import hashlib
import subprocess
from types import SimpleNamespace

import pytest

from runner import replay_guard as guard


def test_linux_identity_normalizes_machine_id_and_includes_pid_namespace(monkeypatch):
    monkeypatch.setattr(guard.sys, "platform", "linux")
    monkeypatch.setattr(guard.Path, "read_text", lambda *args, **kwargs: "A" * 32 + "\n")
    monkeypatch.setattr(guard.Path, "stat", lambda *args, **kwargs: SimpleNamespace(st_ino=123))
    identity = guard.host_identity()
    assert identity == hashlib.sha256(f"nfclaw-host-v1:linux:{'a' * 32}:123".encode()).hexdigest()
    monkeypatch.setattr(guard.Path, "stat", lambda *args, **kwargs: SimpleNamespace(st_ino=456))
    assert guard.host_identity() != identity


@pytest.mark.parametrize("machine", ["", "0" * 32, "unknown", "x" * 32])
def test_invalid_machine_id_does_not_invent_a_host_identity(monkeypatch, machine):
    monkeypatch.setattr(guard.sys, "platform", "linux")
    monkeypatch.setattr(guard.Path, "read_text", lambda *args, **kwargs: machine)
    monkeypatch.setattr(guard.Path, "stat", lambda *args, **kwargs: SimpleNamespace(st_ino=123))
    assert guard.host_identity() is None


def test_macos_identity_uses_hashed_platform_uuid(monkeypatch):
    monkeypatch.setattr(guard.sys, "platform", "darwin")
    uuid = "12345678-1234-5678-9abc-123456789abc"
    monkeypatch.setattr(guard.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout=f'  "IOPlatformUUID" = "{uuid.upper()}"'))
    expected = hashlib.sha256(f"nfclaw-host-v1:darwin:{uuid}".encode()).hexdigest()
    assert guard.host_identity() == expected


def test_failed_macos_probe_falls_back_without_breaking_logging(monkeypatch):
    monkeypatch.setattr(guard.sys, "platform", "darwin")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("ioreg", 2)

    monkeypatch.setattr(guard.subprocess, "run", timeout)
    assert guard.host_identity() is None


@pytest.mark.parametrize("uuid", ["00000000-0000-0000-0000-000000000000", "-" * 36, "unknown"])
def test_macos_placeholder_or_invalid_uuid_does_not_claim_a_host_identity(monkeypatch, uuid):
    monkeypatch.setattr(guard.sys, "platform", "darwin")
    monkeypatch.setattr(guard.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout=f'"IOPlatformUUID" = "{uuid}"'))
    assert guard.host_identity() is None
