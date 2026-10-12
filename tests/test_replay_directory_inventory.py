"""Directory shape is a scientific dependency even when no data bytes change."""
import subprocess

import pytest

from runner import provenance
from runner.submodule import SubmoduleStatus


@pytest.fixture(autouse=True)
def no_engine_probe(monkeypatch):
    monkeypatch.setattr(provenance, "_nextflow_version", lambda env_extra=None: "test engine")


def record(tmp_path, source):
    return provenance.write(outdir=tmp_path / "out", pipeline="fixture",
        command_str="echo REPLAY_RAN",
        submodule=SubmoduleStatus("fixture", tmp_path / "up", True, True, "1.0.0", "deadbeef", ()),
        input_paths=[source])


@pytest.mark.parametrize("change", ["add", "remove", "rename", "alias"])
def test_empty_input_directories_invalidate_the_recorded_replay(tmp_path, change):
    source = tmp_path / "data"
    source.mkdir()
    (source / "reads.txt").write_bytes(b"unchanged scientific input")
    empty = source / "empty"
    empty.mkdir()
    before = provenance.hash_inputs([source])
    bundle = record(tmp_path, source)
    if change == "add":
        (source / "new_sample").mkdir()
    elif change == "remove":
        empty.rmdir()
    elif change == "rename":
        empty.rename(source / "renamed_sample")
    else:
        (source / "sample_alias").symlink_to(empty, target_is_directory=True)
    assert provenance.hash_inputs([source]) == before  # file bytes cannot detect this change
    result = subprocess.run([str(bundle / "commands.sh"), str(tmp_path / "replay")],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "REPLAY_RAN" not in result.stdout
    assert "inventory" in result.stderr


@pytest.mark.parametrize("source_kind", ["directory", "glob", "empty"])
def test_unchanged_directory_namespace_allows_standalone_replay(tmp_path, source_kind):
    source = tmp_path / "data"
    source.mkdir()
    (source / "empty").mkdir()
    if source_kind != "empty":
        (source / "reads.txt").write_bytes(b"unchanged input")
    if source_kind == "glob":
        source = tmp_path / "data*"
    bundle = record(tmp_path, source)
    result = subprocess.run([str(bundle / "commands.sh"), str(tmp_path / "replay")],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "REPLAY_RAN" in result.stdout


def test_empty_directory_glob_members_are_recorded(tmp_path):
    source = tmp_path / "sample_1"
    source.mkdir()
    bundle = record(tmp_path, tmp_path / "sample_*")
    (tmp_path / "sample_2").mkdir()
    result = subprocess.run([str(bundle / "commands.sh"), str(tmp_path / "replay")],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0 and "REPLAY_RAN" not in result.stdout
    assert "sample_2" in result.stderr


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_symlink_retargeting_is_not_hidden_by_identical_file_bytes(tmp_path, kind):
    source = tmp_path / "data"
    source.mkdir()
    targets = []
    for name in ("first", "second"):
        target = tmp_path / name
        if kind == "file":
            target.write_bytes(b"identical data")
        else:
            target.mkdir()
        targets.append(target)
    alias = source / "alias"
    alias.symlink_to(targets[0], target_is_directory=kind == "directory")
    before = provenance.hash_inputs([source])
    bundle = record(tmp_path, source)
    alias.unlink()
    alias.symlink_to(targets[1], target_is_directory=kind == "directory")
    assert provenance.hash_inputs([source]) == before
    result = subprocess.run([str(bundle / "commands.sh"), str(tmp_path / "replay")],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0 and "REPLAY_RAN" not in result.stdout
    assert "type or link changed" in result.stderr


@pytest.mark.parametrize("damage", ["missing", "invalid_type", "duplicate", "version",
                                   "unverified_shape", "checksum_mismatch"])
def test_incomplete_or_malformed_namespace_cannot_weaken_the_replay_guard(tmp_path, damage):
    import json
    source = tmp_path / "data"
    source.mkdir()
    (source / "reads.txt").write_bytes(b"unchanged input")
    bundle = record(tmp_path, source)
    path = bundle / "inputs.inventory.json"
    inventory = json.loads(path.read_text())
    if damage == "missing":
        path.unlink()
    elif damage == "invalid_type":
        inventory[str(source)]["type"] = []
        path.write_text(json.dumps(inventory))
    elif damage == "duplicate":
        path.write_text('{"/data": {"type":"directory"}, "/data":{"type":"file"}}')
    elif damage in ("version", "unverified_shape"):
        manifest = bundle / "run_manifest.json"
        data = json.loads(manifest.read_text())
        if damage == "version":
            del data["dependency_inventory_version"]
        else:
            data["unverified_dependency_inventories"] = None
        manifest.write_text(json.dumps(data))
    else:
        inventory[str(source / "reads.txt")]["type"] = "directory"
        path.write_text(json.dumps(inventory))
    result = subprocess.run([str(bundle / "commands.sh"), str(tmp_path / "replay")],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0 and "REPLAY_RAN" not in result.stdout
    assert "dependency check failed" in result.stderr
    assert "Traceback" not in result.stderr


def test_file_only_prelaunch_checksums_cannot_invent_the_original_directory_layout(tmp_path):
    source = tmp_path / "data"
    source.mkdir()
    (source / "reads.txt").write_bytes(b"unchanged input")
    checksums = provenance.hash_inputs([source])
    (source / "later_sample").mkdir()
    bundle = provenance.write(outdir=tmp_path / "out", pipeline="fixture",
        command_str="echo REPLAY_RAN",
        submodule=SubmoduleStatus("fixture", tmp_path / "up", True, True, "1.0.0", "deadbeef", ()),
        input_paths=[source], input_checksums=checksums)
    result = subprocess.run([str(bundle / "commands.sh"), str(tmp_path / "replay")],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0 and "REPLAY_RAN" not in result.stdout
    assert "not captured" in result.stderr


def test_prelaunch_directory_shape_survives_changes_during_execution(library, tmp_path, monkeypatch):
    import json
    from runner import orchestration
    root = library("mini")
    tree = root / "pipelines/mini/upstream"
    (tree / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "directory-path"},
        "outdir": {"type": "string", "format": "directory-path"}}}))
    source = tmp_path / "data"
    source.mkdir()
    original = source / "original_sample"
    original.mkdir()
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **kwargs: [])
    monkeypatch.setattr(orchestration.engine_version, "check", lambda *args, **kwargs: [])

    def launch(*args, **kwargs):
        original.rmdir()
        (source / "later_sample").mkdir()

    monkeypatch.setattr(orchestration.execution, "run", launch)
    out = tmp_path / "out"
    orchestration.run_pipeline("mini", repo_root=root, input_path=source, outdir=out,
        profile="docker", params_file=None, cli_overrides={}, resume=False, demo=False,
        check_only=False, write_provenance=True, timeout_seconds=None, nxf_ver="25.10.4")
    bundle = out / "provenance"
    inventory = json.loads((bundle / "inputs.inventory.json").read_text())
    assert inventory == {str(source): {"type": "directory"}, str(original): {"type": "directory"}}
    result = subprocess.run([str(bundle / "commands.sh"), str(tmp_path / "replay")],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0 and "later_sample" in result.stderr


def test_replay_destination_cannot_mutate_recorded_inputs_before_dependency_validation(tmp_path):
    source = tmp_path / "data"
    source.mkdir()
    empty = source / "empty"
    empty.mkdir()
    bundle = record(tmp_path, source)
    before = provenance.snapshot_inputs([source])
    for target in (source, empty, source / "new-parent" / "replay"):
        result = subprocess.run([str(bundle / "commands.sh"), str(target)],
                                capture_output=True, text=True, timeout=15)
        assert result.returncode != 0 and "REPLAY_RAN" not in result.stdout
        assert "overlaps recorded input" in result.stderr
        assert provenance.snapshot_inputs([source]) == before


def test_parent_directory_alias_retargeting_is_recorded(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    for root in (first, second):
        root.mkdir()
        (root / "reads.txt").write_bytes(b"identical data")
    alias = tmp_path / "parent_alias"
    alias.symlink_to(first, target_is_directory=True)
    bundle = record(tmp_path, alias / "reads.txt")
    alias.unlink()
    alias.symlink_to(second, target_is_directory=True)
    result = subprocess.run([str(bundle / "commands.sh"), str(tmp_path / "replay")],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0 and "type or link changed" in result.stderr


@pytest.mark.parametrize("alias_position", ["original", "relocated"])
def test_relocated_bundle_configs_preserve_identity_across_parent_aliases(tmp_path, alias_position):
    alias = tmp_path / "parent_alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    original = (alias if alias_position == "original" else tmp_path) / "out"
    (original / "provenance").mkdir(parents=True)
    (original / "provenance/params.json").write_text('{"threshold": 0.01}\n')
    provenance.write(outdir=original, pipeline="fixture", command_str="echo REPLAY_RAN",
        submodule=SubmoduleStatus("fixture", tmp_path / "up", True, True, "1.0.0", "deadbeef", ()),
        input_paths=[])
    archive = (tmp_path if alias_position == "original" else alias) / "archive"
    original.rename(archive)
    result = subprocess.run([str(archive / "provenance/commands.sh"), str(tmp_path / "replay")],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "REPLAY_RAN" in result.stdout


@pytest.mark.parametrize("damage", ["missing", "malformed", "old_version", "boolean_version", "unverified"])
def test_resume_cannot_certify_directories_without_a_valid_previous_inventory(tmp_path, damage):
    import json
    from runner import orchestration
    source = tmp_path / "data"
    source.mkdir()
    bundle = record(tmp_path, source)
    if damage == "missing":
        (bundle / "inputs.inventory.json").unlink()
    elif damage == "malformed":
        (bundle / "inputs.inventory.json").write_text('{"/data":{"type":[]}}')
    else:
        path = bundle / "run_manifest.json"
        manifest = json.loads(path.read_text())
        if damage == "old_version":
            del manifest["dependency_inventory_version"]
        elif damage == "boolean_version":
            manifest["dependency_inventory_version"] = True
        else:
            manifest["unverified_dependency_inventories"] = ["inputs"]
        path.write_text(json.dumps(manifest))
    digests, inventory = provenance.snapshot_inputs([source])
    warning = orchestration._directory_resume_warning(tmp_path / "out", inventory, digests)
    assert warning and "fresh Nextflow cache session" in warning


def test_resume_checks_complete_file_membership_to_avoid_stale_publications(tmp_path):
    from runner import orchestration
    source = tmp_path / "data"
    source.mkdir()
    standalone = tmp_path / "table.tsv"
    standalone.write_text("old\n")
    provenance.write(outdir=tmp_path / "out", pipeline="fixture", command_str="echo REPLAY_RAN",
        submodule=SubmoduleStatus("fixture", tmp_path / "up", True, True, "1.0.0", "deadbeef", ()),
        input_paths=[source, standalone])
    standalone.rename(tmp_path / "new-table.tsv")
    _, inventory = provenance.snapshot_inputs([source, tmp_path / "new-table.tsv"])
    digests = orchestration._directory_file_digests(inventory, None)
    assert "inventory changed" in orchestration._directory_resume_warning(tmp_path / "out", inventory, digests)
    (source / "new_reads.txt").write_text("reads\n")
    _, inventory = provenance.snapshot_inputs([source])
    digests = orchestration._directory_file_digests(inventory, None)
    assert "inventory changed" in orchestration._directory_resume_warning(
        tmp_path / "out", inventory, digests)


def test_resume_detects_changed_bytes_beneath_an_input_directory(tmp_path):
    # Same names and types, different content: Nextflow's directory cache key cannot see it.
    from runner import orchestration
    source = tmp_path / "data"
    (source / "nested").mkdir(parents=True)
    reads = source / "nested" / "reads.txt"
    reads.write_text("AAAA\n")
    standalone = tmp_path / "table.tsv"
    standalone.write_text("old\n")
    provenance.write(outdir=tmp_path / "out", pipeline="fixture", command_str="echo REPLAY_RAN",
        submodule=SubmoduleStatus("fixture", tmp_path / "up", True, True, "1.0.0", "deadbeef", ()),
        input_paths=[source, standalone])
    _, inventory = provenance.snapshot_inputs([source, standalone])
    unchanged = orchestration._directory_file_digests(inventory, None)
    assert orchestration._directory_resume_warning(tmp_path / "out", inventory, unchanged) is None
    standalone.write_text("new\n")      # a standalone file's change is Nextflow's own cache key
    _, inventory = provenance.snapshot_inputs([source, standalone])
    digests = orchestration._directory_file_digests(inventory, None)
    assert orchestration._directory_resume_warning(tmp_path / "out", inventory, digests) is None
    reads.write_text("BBBB\n")
    _, inventory = provenance.snapshot_inputs([source, standalone])
    digests = orchestration._directory_file_digests(inventory, None)
    assert "content of a file inside an input directory changed" in \
        orchestration._directory_resume_warning(tmp_path / "out", inventory, digests)


def test_snapshot_reads_shared_data_bytes_once_without_collapsing_scientific_aliases(tmp_path, monkeypatch):
    from runner import replay_guard
    source = tmp_path / "data"
    source.mkdir()
    reads = source / "reads.txt"
    reads.write_bytes(b"scientific reads")
    alias = source / "alias.txt"
    alias.symlink_to(reads)
    calls = []
    original = replay_guard._sha256

    def hash_file(path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(replay_guard, "_sha256", hash_file)
    checksums, inventory = provenance.snapshot_inputs([source, reads, alias])
    assert len(calls) == 1
    assert checksums == {str(reads): original(reads), str(alias): original(reads)}
    assert inventory[str(alias)]["link_target"] == str(reads)
    assert len(inventory) == 3


def test_resume_without_provenance_still_recomputes_changed_directories(library, tmp_path, monkeypatch):
    import json
    from runner import orchestration
    root = library("mini")
    tree = root / "pipelines/mini/upstream"
    (tree / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "directory-path"},
        "outdir": {"type": "string", "format": "directory-path"},
        "optional_destination": {"type": "string", "format": "directory-path"}}}))
    source = tmp_path / "data"
    source.mkdir()
    (source / "original_sample").mkdir()
    monkeypatch.setattr(orchestration.preflight, "check_environment", lambda **kwargs: [])
    monkeypatch.setattr(orchestration.engine_version, "check", lambda *args, **kwargs: [])
    launches = []
    monkeypatch.setattr(orchestration.execution, "run", lambda cmd, **kwargs: launches.append(cmd))
    out = tmp_path / "out"
    options = dict(repo_root=root, input_path=source, outdir=out, profile="docker",
        params_file=None, cli_overrides={"optional_destination": str(tmp_path / "future")},
        demo=False, check_only=False, timeout_seconds=None, nxf_ver="25.10.4")
    orchestration.run_pipeline("mini", **options, resume=False, write_provenance=True)
    (source / "original_sample").rename(source / "changed_sample")
    before = provenance.snapshot_inputs([out])
    checked = orchestration.run_pipeline("mini", **{**options, "check_only": True},
                                         resume=True, write_provenance=False)
    assert "-resume" not in checked.command and checked.checked_only
    assert provenance.snapshot_inputs([out]) == before
    assert len(launches) == 1
    result = orchestration.run_pipeline("mini", **options, resume=True, write_provenance=False)
    assert "-resume" not in launches[-1]
    assert any("inventory changed" in warning for warning in result.warnings)


def test_replay_cannot_write_into_a_retargeted_directory_alias_before_refusing_it(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    alias = tmp_path / "input_alias"
    alias.symlink_to(first, target_is_directory=True)
    bundle = record(tmp_path, alias)
    alias.unlink()
    alias.symlink_to(second, target_is_directory=True)
    before = provenance.snapshot_inputs([second])
    result = subprocess.run([str(bundle / "commands.sh"), str(alias / "new-parent/replay")],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0 and "overlaps recorded input" in result.stderr
    assert provenance.snapshot_inputs([second]) == before
