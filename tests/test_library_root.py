import json
from pathlib import Path

import pytest

from runner import cli, library
from runner.errors import NfclawError


def test_explicit_library_root_works_from_an_unrelated_directory(tmp_path, monkeypatch, capsys):
    content = tmp_path / "content"
    pipeline = content / "pipelines/example"
    pipeline.mkdir(parents=True)
    (pipeline / "skill.md").write_text("---\nname: example\nversion: 1.0.0\n---\nExample\n")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setenv("NFCLAW_LIBRARY_ROOT", str(content))
    assert cli._repo_root() == content
    assert cli.main(["list"]) == 0
    assert "example\t1.0.0" in capsys.readouterr().out


def test_invalid_explicit_root_does_not_silently_use_another_library(tmp_path, monkeypatch):
    monkeypatch.setenv("NFCLAW_LIBRARY_ROOT", str(tmp_path / "absent"))
    with pytest.raises(NfclawError, match="NFCLAW_LIBRARY_ROOT"):
        library.resolve()


def test_installed_package_missing_library_has_actionable_setup(tmp_path, monkeypatch):
    monkeypatch.delenv("NFCLAW_LIBRARY_ROOT", raising=False)
    monkeypatch.setattr(library, "__file__", str(tmp_path / "site-packages/runner/library.py"))
    with pytest.raises(NfclawError) as err:
        library.resolve()
    assert "git clone" in str(err.value) and "NFCLAW_LIBRARY_ROOT" in str(err.value)


def test_status_and_diagnostics_do_not_require_a_library(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NFCLAW_LIBRARY_ROOT", str(tmp_path / "absent"))
    assert cli.main(["status", str(tmp_path / "missing"), "--json"]) == 1
    status = json.loads(capsys.readouterr().out)
    assert status["schema_version"] == 1 and status["state"] == "missing"
    assert cli.main(["doctor", "--json"]) in (0, 1)
    assert json.loads(capsys.readouterr().out)["schema_version"] == 1


def test_audited_role_registries_are_package_data():
    root = Path(__file__).resolve().parents[1]
    for name in ("input_roles.json", "path_roles.json", "param_roles.json"):
        assert (root / "runner" / name).is_file()
