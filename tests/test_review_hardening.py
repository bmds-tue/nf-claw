"""Regressions for the October review: preserve user data and fail closed on replay."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from librarian import check_drift, update_pipelines, write_catalog, write_skill
from runner import chain, cli, orchestration, outputs, provenance, replay_guard, runlog, versions
from runner.errors import NfclawError
from runner.submodule import SubmoduleStatus


def _bundle(tmp_path, monkeypatch, *, inputs=(), env=None, command="echo REPLAY_RAN"):
    monkeypatch.setattr(provenance, "_nextflow_version", lambda *a: "nextflow version 25.10.4")
    source = tmp_path / "source"
    source.mkdir(exist_ok=True)
    (source / "main.nf").write_text("workflow {}\n")
    return provenance.write(
        outdir=tmp_path / "out",
        pipeline="mini",
        command_str=command,
        submodule=SubmoduleStatus("mini", source, True, True, "1.0.0", "", ()),
        input_paths=list(inputs),
        env_extra=env,
    )


@pytest.mark.parametrize("change", ["selection", "addition", "removal", "alias"])
def test_resume_checks_complete_standalone_namespace(tmp_path, monkeypatch, change):
    a, b = tmp_path / "a.fastq", tmp_path / "b.fastq"
    a.write_bytes(b"same reads")
    b.write_bytes(b"same reads")
    alias = tmp_path / "alias.fastq"
    alias.symlink_to(a)
    initial = [alias] if change == "alias" else [a, b] if change == "removal" else [a]
    prov = _bundle(tmp_path, monkeypatch, inputs=initial)
    current_paths = [b] if change == "selection" else [a, b] if change == "addition" else [a]
    if change == "alias":
        alias.unlink()
        alias.symlink_to(b)
        current_paths = [alias]
    hashes, nodes = provenance.snapshot_inputs(current_paths)
    assert orchestration._input_resume_warning(prov.parent, nodes, hashes)


def test_strict_cli_rejects_different_link_identity_with_identical_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    original, replay = tmp_path / "original", tmp_path / "replay"
    for root in (original, replay):
        root.mkdir()
        (root / "data").write_text("identical")
    (original / "link").symlink_to("data")
    (replay / "link").symlink_to(str(replay / "data"))
    (original / "provenance").mkdir()
    hashes, nodes, _ = outputs.snapshot(original, provenance.sha256_file)
    (original / "provenance/outputs.sha256").write_text(provenance.checksum_text(hashes))
    (original / "provenance/outputs.inventory.json").write_text(
        json.dumps({"version": 1, "entries": nodes})
    )
    assert cli.main(["verify", str(replay), "--against", str(original)]) == 0
    assert cli.main(["verify", str(replay), "--against", str(original), "--strict"]) == 1


@pytest.mark.parametrize("level", ["chain", "stage"])
def test_chain_records_secret_references_and_requires_environment_on_resume(
    tmp_path, monkeypatch, level
):
    raw = {"stages": [{"pipeline": "mini"}]}
    target = raw if level == "chain" else raw["stages"][0]
    target["nxf_env"] = {"NXF_TOWER_ACCESS_TOKEN": "private-placeholder", "NXF_OFFLINE": "true"}
    spec = chain.parse_spec(raw)
    tree = SubmoduleStatus("mini", tmp_path, True, True, "1.0.0", "", ())
    planned = [chain.Planned(spec.stages[0], tree, None, None, {})]
    record = chain.normalized(spec, planned)
    path = chain._write_json(tmp_path / "chain.json", record)
    assert "private-placeholder" not in path.read_text()
    assert path.stat().st_mode & 0o777 == 0o600
    monkeypatch.delenv("NXF_TOWER_ACCESS_TOKEN", raising=False)
    with pytest.raises(NfclawError, match="NXF_TOWER_ACCESS_TOKEN"):
        chain.parse_spec(record)
    monkeypatch.setenv("NXF_TOWER_ACCESS_TOKEN", "replacement-placeholder")
    restored = chain.parse_spec(record)
    assert (
        chain.options(restored, restored.stages[0]).nxf_env["NXF_TOWER_ACCESS_TOKEN"]
        == "replacement-placeholder"
    )


def test_null_stage_engine_keeps_existing_inheritance_semantics():
    spec = chain.parse_spec(
        {"nxf_ver": "25.10.4", "stages": [{"pipeline": "mini", "nxf_ver": None}]}
    )
    assert chain.options(spec, spec.stages[0]).nxf_ver == "25.10.4"


@pytest.mark.parametrize("equals", [False, True])
@pytest.mark.parametrize("duplicate", [False, True])
def test_refused_run_cannot_persist_or_print_a_secret(
    tmp_path, monkeypatch, capsys, equals, duplicate
):
    monkeypatch.setattr(cli, "_repo_root", lambda: tmp_path)
    out = tmp_path / "out"
    log = out / "provenance/logs/run.log"
    log.parent.mkdir(parents=True)
    log.write_text("earlier attempt\n")
    secret = "refusal-private-placeholder"

    def refuse(*a, **kw):
        raise NfclawError(cli.ErrorCode.PARAMS_INVALID, f"invalid value: {secret}")

    monkeypatch.setattr(orchestration, "run_pipeline", refuse)
    option = f"NXF_GITHUB_TOKEN={secret}"
    args = [f"--nxf-env={option}"] if equals else ["--nxf-env", option]
    overwritten = "overwritten-private-placeholder"
    if duplicate:
        args = ["--nxf-env", f"NXF_GITHUB_TOKEN={overwritten}", *args]
    assert cli.main(["run", "mini", "--outdir", str(out), *args]) == 1
    assert secret not in log.read_text()
    assert overwritten not in log.read_text()
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err
    assert "<redacted>" in log.read_text()


@pytest.mark.parametrize("level", ["chain", "stage"])
@pytest.mark.parametrize(
    "raw",
    [
        {"limits": {"memory": 16}},
        {"limits": {"time": 60}},
        {"limits": {"memory": False}},
        {"limits": {"time": []}},
        {"nxf_env": 17},
        {"nxf_env": [1]},
        {"nxf_env": []},
        {"nxf_env": False},
        {"nxf_env": None},
        {"nxf_env": {"NXF_X": 3}},
        {"nxf_ver": False},
    ],
)
@pytest.mark.parametrize("extension", ["json", "yaml"])
def test_malformed_options_through_real_cli(tmp_path, raw, level, extension):
    import sys

    data = {"stages": [{"pipeline": "demo"}]}
    (data if level == "chain" else data["stages"][0]).update(raw)
    path = tmp_path / f"spec.{extension}"
    if extension == "yaml":
        yaml = pytest.importorskip("yaml")
        path.write_text(yaml.safe_dump(data))
    else:
        path.write_text(json.dumps(data))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "runner",
            "chain",
            "run",
            str(path),
            "--outdir",
            str(tmp_path / "out"),
            "--check",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "[params_invalid]" in result.stderr and "chain" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "out").exists()


def test_replay_removes_unrecorded_nxf_environment_and_preserves_required_secret(
    tmp_path, monkeypatch
):
    for key in list(os.environ):
        if key.startswith("NXF_"):
            monkeypatch.delenv(key)
    prov = _bundle(
        tmp_path,
        monkeypatch,
        env={"NXF_GITHUB_TOKEN": "original-placeholder"},
        command='bash -c \'printf "%s|%s" "${NXF_SYNTAX_PARSER-unset}" "$NXF_GITHUB_TOKEN"\'',
    )
    env = {**os.environ, "NXF_SYNTAX_PARSER": "v2", "NXF_GITHUB_TOKEN": "external-placeholder"}
    result = subprocess.run(
        [str(prov / "commands.sh"), str(tmp_path / "replay")],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "unset|external-placeholder" in result.stdout
    assert "original-placeholder" not in (prov / "commands.sh").read_text()
    env.pop("NXF_GITHUB_TOKEN")
    refused = subprocess.run(
        [str(prov / "commands.sh"), str(tmp_path / "missing-secret")],
        env=env,
        capture_output=True,
        text=True,
    )
    assert refused.returncode != 0 and "required secret NXF_GITHUB_TOKEN" in refused.stderr


@pytest.mark.parametrize("field", ["pipeline_path", "pipeline_git_head", "pipeline"])
@pytest.mark.parametrize("archived", [False, True])
def test_missing_source_identity_cannot_disable_replay_checks(
    tmp_path, monkeypatch, field, archived
):
    prov = _bundle(tmp_path, monkeypatch)
    path = prov / "run_manifest.json"
    data = json.loads(path.read_text())
    if not archived:
        data.pop("pipeline_archive", None)
        path.write_text(json.dumps(data))
        (tmp_path / "source/main.nf").write_text("changed scientific code")
        with pytest.raises(ValueError, match="source content changed"):
            replay_guard.verify_dependencies(prov)
    else:
        replay_guard.verify_dependencies(prov)
    del data[field]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="identity is missing or incomplete"):
        replay_guard.verify_dependencies(prov)


def test_status_uses_seek_index_without_scanning_large_attempt(tmp_path, monkeypatch):
    log = runlog.RunLog.open(tmp_path, command=["nextflow"], launch_dir=tmp_path)
    for _ in range(16):
        log.write(b"x" * 1024 * 1024)
    log.outcome = "success"
    log.finish()
    read_bytes = 0
    real_open = Path.open

    class Counted:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.handle.close()

        def __getattr__(self, key):
            return getattr(self.handle, key)

        def read(self, size=-1):
            nonlocal read_bytes
            data = self.handle.read(size)
            read_bytes += len(data)
            return data

        def __iter__(self):
            raise AssertionError("status must not iterate the full log")

    def opened(path, *args, **kwargs):
        handle = real_open(path, *args, **kwargs)
        return Counted(handle) if path == log.path else handle

    monkeypatch.setattr(Path, "open", opened)
    assert runlog.read_state(log.path).state == "success"
    assert read_bytes < 1024 * 1024
    second = runlog.RunLog.open(tmp_path, command=["nextflow"], launch_dir=tmp_path)
    second.outcome = "failed"
    second.finish()
    assert runlog.read_state(log.path).outcome == "failed"


@pytest.mark.parametrize("file", ["nextflow_schema.json", "main.nf", "nextflow.config"])
def test_drift_refuses_dirty_source_even_after_regeneration(tmp_path, file):
    from test_versions import _upstream_repo_with_tag

    pdir = tmp_path / "pipelines"
    up = _upstream_repo_with_tag(pdir, "mini", "1.0.0")
    write_skill.generate("mini", pipelines_dir=pdir)
    path = up / file
    if file.endswith(".json"):
        path.write_text('{"description": "local schema edit"}\n')
    else:
        path.write_text(path.read_text() + "// local scientific change\n")
    write_skill.generate("mini", pipelines_dir=pdir)
    write_catalog.generate(
        pipelines_dir=pdir, out_md=tmp_path / "catalog.md", out_json=tmp_path / "catalog.json"
    )
    assert any("local modifications" in item for item in check_drift.check(pdir))


@pytest.mark.parametrize("kind", ["deleted_tracked", "untracked", "unrelated_repo"])
def test_version_cache_preserves_incomplete_user_work(tmp_path, monkeypatch, kind):
    from test_versions import _upstream_repo_with_tag

    pdir = tmp_path / "pipelines"
    up = _upstream_repo_with_tag(pdir, "mini", "1.0.0")
    dest = versions.cache_dir("mini", "1.0.0", pdir) / "upstream"
    if kind == "deleted_tracked":
        versions._add_worktree(up, dest, "tags/1.0.0")
        (dest / "main.nf").unlink()
    elif kind == "unrelated_repo":
        dest.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(dest)], check=True)
    else:
        dest.mkdir(parents=True)
    notes = dest / "research-notes.txt"
    notes.write_text("irreplaceable local work")
    with pytest.raises(NfclawError, match="Incomplete version cache"):
        versions.materialize("mini", "1.0.0", pipelines_dir=pdir, repo_root=tmp_path)
    assert notes.read_text() == "irreplaceable local work"


def test_failed_cache_checkout_is_preserved_before_retry(tmp_path, monkeypatch):
    from test_versions import _upstream_repo_with_tag

    pdir = tmp_path / "pipelines"
    _upstream_repo_with_tag(pdir, "mini", "1.0.0")
    dest = versions.cache_dir("mini", "1.0.0", pdir) / "upstream"
    real_capture = versions.capture

    def interrupted_checkout(command, **kwargs):
        if "worktree" in command and "add" in command:
            dest.mkdir(parents=True)
            (dest / "partial-checkout.txt").write_text("checkout evidence")
            raise subprocess.CalledProcessError(1, command, stderr="checkout interrupted")
        return real_capture(command, **kwargs)

    monkeypatch.setattr(versions, "capture", interrupted_checkout)
    with pytest.raises(NfclawError, match="Could not materialize"):
        versions.materialize("mini", "1.0.0", pipelines_dir=pdir, repo_root=tmp_path)
    notes = dest / "notes.txt"
    notes.write_text("work after the failure")
    monkeypatch.setattr(versions, "capture", real_capture)
    with pytest.raises(NfclawError, match="Incomplete version cache"):
        versions.materialize("mini", "1.0.0", pipelines_dir=pdir, repo_root=tmp_path)
    assert notes.read_text() == "work after the failure"
    assert (dest / "partial-checkout.txt").read_text() == "checkout evidence"


@pytest.mark.parametrize("cursor", [b"not JSON", b"x" * 4097])
def test_status_falls_back_when_optional_cursor_is_invalid(tmp_path, cursor):
    log = runlog.RunLog.open(tmp_path, command=["nextflow"], launch_dir=tmp_path)
    log.outcome = "success"
    log.finish()
    replay_guard.log_cursor_path(log.path).write_bytes(cursor)
    assert runlog.read_state(log.path).state == "success"


@pytest.mark.parametrize("failure", [RuntimeError, KeyboardInterrupt])
def test_updater_restores_checkout_index_and_context_on_failed_generation(
    tmp_path, monkeypatch, failure
):
    from test_discover_add_one import _allow_file_submodules, _make_origin, _make_superproject, _git

    _allow_file_submodules(monkeypatch)
    origin, root = tmp_path / "origin", tmp_path / "repo"
    commits = _make_origin(origin)
    _make_superproject(root)
    relative = "pipelines/mini/upstream"
    _git(root, "submodule", "add", origin.as_uri(), relative)
    _git(root / relative, "checkout", "--detach", "1.0.0")
    write_skill.generate("mini", pipelines_dir=root / "pipelines")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "pin")
    before = {f: (root / f"pipelines/mini/{f}").read_bytes() for f in ("skill.md", "reference.md")}

    def broken(*args, **kwargs):
        (root / "pipelines/mini/skill.md").write_text("partial generation")
        raise failure("interrupted generation")

    monkeypatch.setattr(write_skill, "generate", broken)
    with pytest.raises(failure):
        update_pipelines.bump("mini", origin.as_uri(), root)
    assert _git(root / relative, "rev-parse", "HEAD") == commits["1.0.0"]
    assert not _git(root, "status", "--porcelain")
    assert all(
        (root / f"pipelines/mini/{f}").read_bytes() == content for f, content in before.items()
    )
