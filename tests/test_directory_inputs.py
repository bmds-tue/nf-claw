"""Explicit directory dependencies cannot hide unsafe staged child names."""
import json
import os

import pytest

from runner import parameters, replay_guard, samplesheet, schema
from runner.inputs import local_name_issues


@pytest.mark.parametrize("fmt", ["directory-path", "path", "file-path-pattern"])
@pytest.mark.parametrize("kind", ["file", "empty_directory", "directory_with_data"])
def test_directory_children_receive_literal_staged_name_checks(tmp_path, fmt, kind):
    root = tmp_path / "safe_directory"
    root.mkdir()
    unsafe = root / "reads$(id).txt"
    if kind == "file":
        unsafe.write_bytes(b"scientific data")
    else:
        unsafe.mkdir()
        if kind == "directory_with_data":
            (unsafe / "safe.txt").write_bytes(b"scientific data")
    value = str(root) if fmt != "file-path-pattern" else str(tmp_path / "safe_*")
    assert any("unsafe local input filename" in issue for issue in local_name_issues(value, fmt))


def test_directory_symlinks_do_not_hide_unsafe_target_names(tmp_path):
    root = tmp_path / "safe_directory"
    root.mkdir()
    target = tmp_path / "target$(id).txt"
    target.write_bytes(b"scientific data")
    (root / "safe.txt").symlink_to(target)
    assert any("target$(id).txt" in issue for issue in local_name_issues(str(root), "directory-path"))


def test_directory_parent_names_are_distinct_from_staged_child_names(tmp_path):
    parent = tmp_path / "parent with spaces"
    root = parent / "data_é"
    nested = root / "lane_é"
    nested.mkdir(parents=True)
    (nested / "reads_e\u0301+lane@run%=1,part:2~copy.txt").write_bytes(b"scientific data")
    (root / "empty").mkdir()
    assert local_name_issues(str(root), "directory-path") == []


def test_directory_preflight_cannot_ignore_an_unreadable_subtree(tmp_path, monkeypatch):
    root = tmp_path / "data"
    nested = root / "nested"
    nested.mkdir(parents=True)
    scandir = os.scandir

    def denied(path):
        if path == nested:
            raise PermissionError(13, "Permission denied", str(path))
        return scandir(path)

    monkeypatch.setattr(os, "scandir", denied)
    assert any("cannot inspect" in issue for issue in local_name_issues(str(root), "directory-path"))


def test_directory_cycles_fail_clearly_before_launch(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    (root / "cycle").symlink_to(root, target_is_directory=True)
    assert any("cyclic" in issue for issue in local_name_issues(str(root), "directory-path"))


def test_direct_directory_parameters_and_samplesheet_paths_have_the_same_guard(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    (root / "reads;true.txt").write_bytes(b"scientific data")
    (tmp_path / "nextflow_schema.json").write_text(json.dumps({"properties": {
        "input": {"type": "string", "format": "directory-path"}}}))
    param_schema = schema.load_param_schema(tmp_path)
    assert parameters.validate_params({"input": str(root)}, param_schema)
    sheet = tmp_path / "samples.csv"
    sheet.write_text(f"sample,data\nA,{root}\n")
    input_schema = schema.InputSchema(columns=(schema.Column("sample", "string", True, None),
        schema.Column("data", "string", True, None, "directory-path")))
    assert any("unsafe local input filename" in issue for issue in samplesheet.validate(sheet, input_schema))


def test_inventory_visitor_sees_empty_directories_without_changing_dependency_paths(tmp_path):
    root = tmp_path / "data"
    nested = root / "nested"
    empty = root / "empty"
    nested.mkdir(parents=True)
    empty.mkdir()
    read = nested / "reads.txt"
    read.write_bytes(b"scientific data")
    alias = root / "alias"
    alias.symlink_to(nested, target_is_directory=True)
    before = replay_guard.input_files([root])
    seen = []
    replay_guard.inspect_input_paths([root], seen.append)
    after = replay_guard.input_files([root])
    assert after == before == sorted([read, alias / read.name])
    assert set(seen) == {root, nested, read, empty, alias, alias / read.name}
