"""Current publications must belong to the current analysis configuration."""
import json
from datetime import datetime
from pathlib import Path

import pytest

from runner import orchestration, resources


@pytest.fixture
def analysis(library, monkeypatch, tmp_path):
    root = library("mini")
    tree = root / "pipelines/mini/upstream"
    (tree / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "outdir": {"type": "string"}, "label": {"type": "string"},
        "publish_optional": {"type": "boolean"}, "trace_report_suffix": {"type": "string"}}}))
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **kw: [])
    monkeypatch.setattr(orchestration.engine_version, "effective", lambda *a: "25.10.4")
    launches = []

    def execute(command, **kw):
        params = json.loads(Path(command[command.index("-params-file") + 1]).read_text())
        out = Path(params["outdir"])
        (out / (params.get("label", "first") + ".txt")).write_text("result\n")
        if params.get("publish_optional", True):
            (out / "optional.txt").write_text("optional result\n")
        launches.append(command)

    monkeypatch.setattr(orchestration.execution, "run", execute)

    def run(**kw):
        options = dict(repo_root=root, input_path=None, outdir=tmp_path / "results",
            profile="docker", params_file=None, cli_overrides={}, resume=False, demo=False,
            check_only=False, write_provenance=True, timeout_seconds=None, nxf_ver="25.10.4")
        options.update(kw)
        return orchestration.run_pipeline("mini", **options)

    return run, tree, launches


@pytest.mark.parametrize("change", ["parameters", "disabled-output", "profile", "config",
                                    "source", "engine", "environment", "limits"])
def test_changed_analysis_preserves_previous_run_in_isolated_archive(analysis, tmp_path, change):
    run, tree, launches = analysis
    config = tmp_path / "settings.config"
    config.write_text("params.label = 'first'\n")
    run(configs=[str(config)])
    old_params = (tmp_path / "results/provenance/params.json").read_bytes()
    (tmp_path / "results/important-user-notes.txt").write_text("retain me\n")
    options = dict(resume=True, configs=[str(config)])
    if change == "parameters":
        options["cli_overrides"] = {"label": "second"}
    elif change == "disabled-output":
        options["cli_overrides"] = {"publish_optional": False}
    elif change == "profile":
        options["profile"] = "podman"
    elif change == "config":
        config.write_text("params.label = 'other'\n")
    elif change == "source":
        (tree / "main.nf").write_text("// changed pipeline source\n")
    elif change == "engine":
        options["nxf_ver"] = "26.04.3"
    elif change == "environment":
        options["nxf_env"] = {"NXF_OFFLINE": "true"}
    elif change == "limits":
        options["limits"] = resources.parse(1, "1.GB", None)
    result = run(**options)
    archives = list(tmp_path.glob("results.previous-*"))
    assert len(archives) == 1
    assert (archives[0] / "first.txt").read_text() == "result\n"
    assert (archives[0] / "provenance/params.json").read_bytes() == old_params
    assert (archives[0] / "important-user-notes.txt").read_text() == "retain me\n"
    assert not (tmp_path / "results/important-user-notes.txt").exists()
    assert "-resume" not in launches[-1]
    assert any("analysis configuration" in warning for warning in result.warnings)
    if change == "parameters":
        assert not (tmp_path / "results/first.txt").exists()
        assert (tmp_path / "results/second.txt").is_file()
    if change == "disabled-output":
        assert not (tmp_path / "results/optional.txt").exists()


@pytest.mark.parametrize("provenance", [True, False])
def test_unchanged_analysis_reuses_cache_and_report_suffix(
        analysis, tmp_path, provenance, monkeypatch):
    run, _, launches = analysis
    original = orchestration.parameters.pin_report_suffix
    dates = iter([datetime(2026, 1, 1), datetime(2026, 1, 2)])
    monkeypatch.setattr(orchestration.parameters, "pin_report_suffix",
                        lambda merged, schema: original(merged, schema, now=next(dates)))
    run(write_provenance=provenance)
    params = (tmp_path / "results/provenance/params.json").read_bytes()
    # Report suffix generation must not turn an unchanged resume into another analysis.
    run(resume=True, write_provenance=provenance)
    assert "-resume" in launches[-1]
    assert (tmp_path / "results/provenance/params.json").read_bytes() == params
    assert not list(tmp_path.glob("results.previous-*"))


def test_empty_resource_options_mean_the_same_analysis_as_no_options(analysis):
    run, _, launches = analysis
    run(limits=resources.parse(None, None, None))
    run(resume=True, limits=None)
    assert "-resume" in launches[-1]


def test_check_reports_configuration_change_without_writing(analysis, tmp_path):
    run, _, launches = analysis
    run()
    old = (tmp_path / "results/provenance/params.json").read_bytes()
    checked = run(resume=True, check_only=True, cli_overrides={"label": "second"})
    assert "-resume" not in checked.command
    assert len(launches) == 1
    assert (tmp_path / "results/first.txt").is_file()
    assert (tmp_path / "results/provenance/params.json").read_bytes() == old
    assert not list(tmp_path.glob("results.previous-*"))
