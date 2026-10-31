"""Damaged or empty observations must never establish environment identity."""
import copy

import pytest

from runner import environment_record


def _legacy_record():
    return {"processes": {"A": {"containers": ["quay.io/a:1"]}},
            "images": {"quay.io/a:1": {"kind": "registry", "digest": "sha256:" + "a" * 64}},
            "nextflow_plugins": [], "container_engine": {"name": "docker"}}


@pytest.mark.parametrize("record", [{}, {"version": 999}, None, [], "record"])
def test_absent_or_invalid_observations_cannot_compare_identical(record):
    result = environment_record.compare(record, record)
    assert result["status"] == "unverified"
    assert result["unverified"]


@pytest.mark.parametrize("field,value", [
    ("version", 999), ("version", True), ("version", "1"),
    ("processes", {}), ("processes", []), ("processes", {"A": None}),
    ("processes", {"A": {"containers": "quay.io/a:1"}}),
    ("processes", {"A": {"containers": []}}),
    ("processes", {"A": {"containers": [None]}}),
    ("processes", {"A": {"containers": ["quay.io/a:1"], "without_container": 1}}),
    ("images", []), ("images", {"quay.io/a:1": "image"}),
    ("images", {"quay.io/a:1": {"kind": "registry", "digest": "invalid"}}),
    ("images", {"quay.io/a:1": {"kind": "file", "path": "/image"}}),
    ("images", {"quay.io/a:1": {}}),
    ("container_engine", "docker"), ("container_engine", {}),
    ("nextflow_plugins", "nf-schema@1"), ("nextflow_plugins", [None]),
    ("remote_inputs", []), ("remote_inputs", {"https://data/a": None}),
    ("remote_inputs", {"https://data/a": {"sha256": "invalid"}}),
    ("issues", "could not capture tasks"),
])
def test_malformed_or_unusable_evidence_is_unverified_without_a_traceback(field, value):
    record = _legacy_record()
    record[field] = value
    result = environment_record.compare(record, copy.deepcopy(record))
    assert result["status"] == "unverified"
    assert result["unverified"]


def test_legacy_minimal_container_evidence_still_compares_identical():
    record = _legacy_record()
    assert environment_record.compare(record, copy.deepcopy(record))["status"] == "identical"


@pytest.mark.parametrize('damage', ['json', 'encoding', 'directory'])
def test_standalone_replay_reports_corrupt_record_as_unverified(
        tmp_path, monkeypatch, capsys, damage):
    bundle = tmp_path / 'bundle'
    bundle.mkdir()
    path = bundle / 'environment.json'
    if damage == 'json':
        path.write_text('{broken')
    elif damage == 'encoding':
        path.write_bytes(b'\xff')
    else:
        path.mkdir()
    monkeypatch.setattr(environment_record, 'capture', lambda *args, **kwargs: _legacy_record())
    target = tmp_path / 'replay'
    assert environment_record.verify_replay(bundle, target) == 0
    assert 'execution environment unverified' in capsys.readouterr().out
    assert (target / 'provenance/environment_check.json').is_file()


@pytest.mark.parametrize('reverse', [False, True])
def test_image_aliases_cannot_hide_another_image_used_by_the_replay(reverse):
    original = _legacy_record()
    original['processes']['A']['containers'].append('quay.io/alias:1')
    original['images']['quay.io/alias:1'] = {
        'kind': 'registry', 'digest': 'sha256:' + 'a' * 64}
    replay = copy.deepcopy(original)
    replay['images']['quay.io/alias:1']['digest'] = 'sha256:' + 'b' * 64
    before, after = (replay, original) if reverse else (original, replay)
    result = environment_record.compare(before, after)
    assert result['status'] == 'differs'
    assert result['mismatches']


@pytest.mark.parametrize('reverse', [False, True])
def test_missing_inventories_are_unknown_rather_than_confirmed_environment_changes(reverse):
    record = _legacy_record()
    record['nextflow_plugins'] = ['nf-schema@2.5.1']
    before, after = ({'version': 1}, record) if reverse else (record, {'version': 1})
    result = environment_record.compare(before, after)
    assert result['status'] == 'unverified'
    assert result['mismatches'] == []


def test_known_mismatches_are_preserved_alongside_missing_evidence():
    original = _legacy_record()
    replay = copy.deepcopy(original)
    original.pop('container_engine')
    replay['nextflow_plugins'] = ['nf-schema@2.5.1']
    result = environment_record.compare(original, replay)
    assert result['status'] == 'differs'
    assert result['unverified']
    assert any('Nextflow plugins differ' in item for item in result['mismatches'])


@pytest.mark.parametrize('field,value', [
    ('tasks', 0), ('tasks', False), ('tasks', -1), ('tasks', '1'),
    ('without_container', False), ('without_container', []),
    ('without_container', -1), ('without_container', '0'),
])
def test_malformed_supplied_task_counters_cannot_compare_identical(field, value):
    record = _legacy_record()
    record['processes']['A'][field] = value
    result = environment_record.compare(record, copy.deepcopy(record))
    assert result['status'] == 'unverified'
    assert result['unverified']
