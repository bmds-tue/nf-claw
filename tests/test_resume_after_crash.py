"""A nfclaw that vanished (SIGKILL, out of memory, a restart, a full disk) leaves no bundle: its
launch record still lets `--resume` reuse the finished tasks."""
import json
import subprocess
from pathlib import Path

import pytest

import sheetgen_schemas as S
from runner import cli, orchestration, provenance, runlog
from runner.errors import NfclawError
from test_sheetgen import fq

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def launch(tmp_path, monkeypatch):
    """`launch(input, resume=…, crash=…, provenance=…)`: run_pipeline with the engine stubbed.
    `crash` leaves what a vanished nfclaw leaves: it launched, and wrote no bundle."""
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **k: [])
    launched = []

    def engine(cmd, **k):
        launched.append(cmd)
        k["run_log"].write(b"N E X T F L O W  ~  version 25.10.4\n")

    monkeypatch.setattr(orchestration.execution, "run", engine)
    write = provenance.write

    def go(data, *, resume=False, crash=False, keep_provenance=True):
        if not (tmp_path / "pipelines/pipe").exists():
            S.make_pipeline(tmp_path, S.ATACSEQ, "pipe")
        monkeypatch.setattr(orchestration.provenance, "write",
                            _fail_to_write if crash else write)
        def run():
            orchestration.run_pipeline(
                "pipe", repo_root=tmp_path, input_path=str(data), outdir=tmp_path / "results",
                profile="docker", params_file=None, cli_overrides={}, resume=resume, demo=False,
                check_only=False, write_provenance=keep_provenance, timeout_seconds=None,
                sheet_set={"replicate": "1"})

        if crash:
            with pytest.raises(NfclawError):
                run()
        else:
            run()
        return launched[-1]
    return go


def _fail_to_write(**_):
    raise OSError(28, "No space left on device")


def test_resume_without_a_bundle_reuses_the_cache(tmp_path, launch):
    data = tmp_path / "data"
    fq(data / "A.fastq.gz", "SRR390728.1")
    assert "-resume" not in launch(data, crash=True)
    prov = tmp_path / "results/provenance"
    assert not (prov / "run_manifest.json").exists()
    assert (prov / provenance.LAUNCH_RECORD).is_file()
    assert "-resume" in launch(data, resume=True)
    assert not list(tmp_path.glob("results.previous-*"))


def test_the_published_bundle_replaces_the_launch_record(tmp_path, launch):
    data = tmp_path / "data"
    fq(data / "A.fastq.gz", "SRR390728.1")
    launch(data)
    prov = tmp_path / "results/provenance"
    assert (prov / "run_manifest.json").is_file()
    assert not (prov / provenance.LAUNCH_RECORD).exists()


def test_changed_input_after_a_crash_starts_fresh(tmp_path, launch):
    data = tmp_path / "data"
    sample = fq(data / "A.fastq.gz", "SRR390728.1")
    launch(data, crash=True)
    fq(sample, "SRR390728.2")
    assert "-resume" not in launch(data, resume=True)
    assert len(list(tmp_path.glob("results.previous-*"))) == 1


def test_changed_source_after_a_crash_starts_fresh(tmp_path, launch):
    data = tmp_path / "data"
    fq(data / "A.fastq.gz", "SRR390728.1")
    launch(data, crash=True)
    (tmp_path / "pipelines/pipe/upstream/main.nf").write_text("// edited\n")
    assert "-resume" not in launch(data, resume=True)
    assert len(list(tmp_path.glob("results.previous-*"))) == 1


@pytest.mark.parametrize("damage", ['{"version": 1}', "[]", "{bad",
                                    '{"version": 99, "pipeline_path": "/p", "input_checksums": {}}',
                                    '{"version": 1, "pipeline_path": "/p", "input_checksums": '
                                    '{"relative/name": "00"}, "input_inventory": {}}',
                                    '{"version": 1, "pipeline_path": "/p", "input_checksums": {}, '
                                    '"input_inventory": {"/x": {"type": "socket"}}}'])
def test_a_damaged_launch_record_starts_fresh(tmp_path, launch, damage):
    data = tmp_path / "data"
    fq(data / "A.fastq.gz", "SRR390728.1")
    launch(data, crash=True)
    (tmp_path / "results/provenance" / provenance.LAUNCH_RECORD).write_text(damage)
    assert "-resume" not in launch(data, resume=True)
    assert len(list(tmp_path.glob("results.previous-*"))) == 1


def test_no_provenance_records_nothing_to_resume_from(tmp_path, launch):
    data = tmp_path / "data"
    fq(data / "A.fastq.gz", "SRR390728.1")
    launch(data, keep_provenance=False)
    assert not (tmp_path / "results/provenance" / provenance.LAUNCH_RECORD).exists()
    assert "-resume" not in launch(data, resume=True)


def test_resume_into_an_empty_outdir_archives_nothing(tmp_path, launch):
    data = tmp_path / "data"
    fq(data / "A.fastq.gz", "SRR390728.1")
    (tmp_path / "results").mkdir()
    assert "-resume" not in launch(data, resume=True)
    assert not list(tmp_path.glob("results.previous-*"))


def test_an_earlier_bundle_still_decides_when_it_exists(tmp_path, launch):
    data = tmp_path / "data"
    fq(data / "A.fastq.gz", "SRR390728.1")
    launch(data)
    prov = tmp_path / "results/provenance"
    # A later launch killed outright: its record is beside the earlier attempt's bundle.
    (prov / provenance.LAUNCH_RECORD).write_text("{bad")
    assert provenance.read_launch_record(prov) is None
    assert "-resume" in launch(data, resume=True)


def _dead_log(outdir: Path, kind: str = "run") -> Path:
    log = outdir / "provenance/logs" / runlog.RUN_LOG_NAME
    log.parent.mkdir(parents=True)
    log.write_text(f"==> nfclaw {kind} started 2026-11-05T01:00:00+00:00\n    console format: "
                   "prefixed\n    pid: 2147483646\n| some output\n")
    return log


def test_status_says_what_resume_will_do_for_a_vanished_run(tmp_path):
    out = tmp_path / "killed"
    log = _dead_log(out)
    (out / "provenance" / provenance.LAUNCH_RECORD).write_text("{}")
    report = cli._status_report(runlog.read_state(log))
    assert "stopped without an outcome" in report and "continue where it stopped" in report


def test_status_says_a_no_provenance_run_recomputes(tmp_path):
    log = _dead_log(tmp_path / "killed")
    report = cli._status_report(runlog.read_state(log))
    assert "recomputes every task" in report and "continue where it stopped" not in report


def test_status_never_offers_resume_for_a_replay(tmp_path):
    log = _dead_log(tmp_path / "replay", "replay")
    report = cli._status_report(runlog.read_state(log))
    assert "--resume" not in report and "new empty directory" in report


@pytest.mark.parametrize("name", ["results/x", "results.replay/x", "results.previous-0123abc/x",
                                  ".results.nfclaw.lock", ".results.replay.nfclaw.lock",
                                  ".other.nfclaw.lock"])
def test_a_documented_outdir_leaves_the_checkout_clean(name):
    probe = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--is-inside-work-tree"],
                           capture_output=True, text=True)
    if probe.returncode != 0:
        pytest.skip("not a git checkout")
    ignored = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "--no-index", name])
    assert ignored.returncode == 0, f"{name} would dirty the checkout"


def test_launch_record_round_trip(tmp_path):
    prov = tmp_path / "provenance"
    prov.mkdir()
    provenance.write_launch_record(
        prov, pipeline_path=tmp_path / "up", git_head=None, source_identity_record={"a": 1},
        input_checksums={"/data/a": "0" * 64}, input_inventory={"/data/a": {"type": "file"}})
    record = provenance.read_launch_record(prov)
    assert record["input_checksums"] == {"/data/a": "0" * 64}
    assert record["pipeline_path"] == str(tmp_path / "up")
    assert json.loads((prov / provenance.LAUNCH_RECORD).read_text())["version"] == 1
