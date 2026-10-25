"""Opt-in result acceptance is separate from Nextflow's exit status."""
import json

import pytest

from runner import acceptance, chain, cli, orchestration, runlog
from runner.errors import ErrorCode, NfclawError


@pytest.mark.parametrize("text,category", [
    ("test profile runs every task as a stub; placeholder files", "stub_only"),
    ("Nextflow ignored 2 failed task(s) (errorStrategy 'ignore')", "ignored_task_failures"),
    ("[nf-core/x] Pipeline completed successfully, but with errored process(es)",
     "ignored_task_failures"),
    ("[nf-core/x] with skipped sampl(es)", "skipped_samples"),
    ("[nf-core/x] Sample A failed strandedness checks", "incomplete_analysis"),
    ("upstream reported a condition we do not recognize", "unclassified"),
])
def test_categories_preserve_original_text(text, category):
    record = acceptance.evaluate([text], reject=[category])
    assert record["version"] == 1 and record["accepted"] is False
    assert {"category": category, "text": text} in record["conditions"]
    assert acceptance.evaluate([text], reject=[])["accepted"] is True


@pytest.mark.parametrize("policy", [["typo"], "stub_only", [True]])
def test_invalid_policy_is_refused(policy):
    with pytest.raises(NfclawError):
        acceptance.validate(policy)


@pytest.mark.parametrize("reject", [[], ["ignored_task_failures"], ["any"]])
def test_manifest_log_cli_and_acceptance_agree(library, monkeypatch, tmp_path, reject, capsys):
    root = library("mini")
    monkeypatch.setattr(cli, "_repo_root", lambda: root)
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **kw: [])
    caveat = "[nf-core/mini] Pipeline completed successfully, but with errored process(es)"

    def execute(*args, **kw):
        kw["run_log"].write(("-" + caveat + "-\n").encode())

    monkeypatch.setattr(orchestration.execution, "run", execute)
    out = tmp_path / "results"
    argv = ["run", "mini", "--demo", "--outdir", str(out)]
    for category in reject:
        argv.extend(["--reject-caveat", category])
    code = cli.main(argv)
    manifest = json.loads((out / "provenance/run_manifest.json").read_text())
    assert manifest["completion_caveats"] == [caveat]
    assert manifest["acceptance"]["accepted"] is (not reject)
    assert manifest["outcome"] == ("rejected" if reject else "success")
    state = runlog.read_state(out / "provenance/logs/run.log")
    assert state.state == ("ended" if reject else "success")
    assert code == (1 if reject else 0)
    assert cli.main(["status", str(out)]) == code
    if reject:
        assert "acceptance" in state.outcome
        assert "refused before launch" not in state.outcome
    capsys.readouterr()


def test_acceptance_policy_is_inherited_and_can_be_reset_per_stage():
    spec = chain.parse_spec({"reject_caveats": ["any"], "stages": [
        {"pipeline": "a"}, {"pipeline": "b", "reject_caveats": []}]})
    assert chain.options(spec, spec.stages[0]).reject_caveats == ("any",)
    assert chain.options(spec, spec.stages[1]).reject_caveats == ()


def test_no_caveats_accepts_complete_results():
    assert acceptance.evaluate([], reject=["any"])["accepted"] is True
    assert ErrorCode.ACCEPTANCE_REJECTED.value == "acceptance_rejected"
