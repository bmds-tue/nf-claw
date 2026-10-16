"""Quick monitoring reports execution state without certifying scientific lineage."""
from pathlib import Path

from runner import chain, cli


def test_chain_status_cli_requests_quick_mode(tmp_path, monkeypatch, capsys):
    observed = []
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)

    def status(path, *, quick=False):
        observed.append((path, quick))
        return {"chain_id": "test", "outcome": "success", "stages": [],
                "lineage_verification": "not_checked" if quick else "verified"}, []

    monkeypatch.setattr(chain, "status", status)
    assert cli.main(["chain", "status", str(tmp_path), "--quick"]) == 0
    assert observed == [(Path(tmp_path), True)]
    output = capsys.readouterr().out.lower()
    assert "not checked" in output and "lineage: verified" not in output
