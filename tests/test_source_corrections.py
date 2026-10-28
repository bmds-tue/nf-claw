"""Corrected working source must be explicit, independently copied and integrity checked."""
import hashlib
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from runner import replay_guard
from runner.errors import NfclawError
from runner.submodule import SubmoduleStatus


FIXTURES = Path(__file__).parent / 'fixtures/source_corrections'
CASES = [
    ('createtaxdb', 'b01a0f8ed96a5990d15470828dfa92a22cf08bba',
     'subworkflows/local/sourmash_create/main.nf', 'createtaxdb-sourmash-create.nf'),
    ('funcscan', 'aee3dc965eb0c77267435544dda30da858763913',
     'subworkflows/local/amp.nf', 'funcscan-amp.nf')]


def correction_api():
    from runner import source_corrections
    return source_corrections


def source(tmp_path, case):
    name, commit, target, fixture = case
    root = tmp_path / 'original'
    path = root / target
    path.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURES / fixture, path)
    (root / 'main.nf').write_text('// unchanged workflow\n')
    binary = root / 'bin/tool'
    binary.parent.mkdir()
    binary.write_text('#!/bin/sh\nprintf "known behavior\\n"\n')
    binary.chmod(0o755)
    return SubmoduleStatus(name, root, True, True, 'fixture', commit, ()), path


@pytest.mark.parametrize('case', CASES)
def test_plan_is_deterministic_and_changes_only_the_bound_workflow(tmp_path, case):
    api = correction_api()
    st, path = source(tmp_path, case)
    before = replay_guard.hash_pipeline(st.path)
    plan = api.plan(st)
    assert plan is not None
    assert len(plan.fingerprint) == 64
    assert api.plan(st).fingerprint == plan.fingerprint
    assert plan.upstream_commit == st.commit
    assert set(plan.patched_files) == {case[2]}
    assert plan.expected_files[case[2]] != before[case[2]]
    assert {name: digest for name, digest in plan.expected_files.items() if name != case[2]} == {
        name: digest for name, digest in before.items() if name != case[2]}
    assert hashlib.sha256(plan.patched_files[case[2]]).hexdigest() == plan.expected_files[case[2]]
    assert replay_guard.hash_pipeline(st.path) == before
    assert path.read_bytes() == (FIXTURES / case[3]).read_bytes()


def test_other_releases_have_no_implicit_correction(tmp_path):
    api = correction_api()
    st, _ = source(tmp_path, CASES[0])
    assert api.plan(replace(st, commit='f' * 40)) is None
    assert api.plan(replace(st, name='unrelated')) is None


@pytest.mark.parametrize('case', CASES)
def test_target_bytes_must_match_the_audited_source(tmp_path, case):
    api = correction_api()
    st, path = source(tmp_path, case)
    path.write_bytes(path.read_bytes() + b'\n// changed\n')
    with pytest.raises(NfclawError, match='(?i)(source|checksum|hash)'):
        api.plan(st)


def test_materialized_source_is_independent_and_preserves_executable_modes(tmp_path):
    api = correction_api()
    st, original_target = source(tmp_path, CASES[0])
    plan = api.plan(st)
    before = replay_guard.hash_pipeline(st.path)
    destination = tmp_path / 'cache/pipeline'
    working = api.materialize(plan, destination)
    assert working.path == destination
    assert working.metadata['upstream_commit'] == st.commit
    assert working.metadata['fingerprint'] == plan.fingerprint
    assert working.git_head is None
    assert replay_guard.hash_pipeline(destination) == plan.expected_files
    assert (destination / 'bin/tool').stat().st_mode & 0o111 == 0o111
    assert (destination / 'main.nf').stat().st_mode & 0o111 == 0
    assert original_target.stat().st_ino != (destination / CASES[0][2]).stat().st_ino
    assert replay_guard.hash_pipeline(st.path) == before
    api.verify(working)
    again = api.materialize(plan, destination)
    assert again.path == destination
    assert replay_guard.hash_pipeline(destination) == plan.expected_files


@pytest.mark.parametrize('mutation', ['bytes', 'extra', 'executable_mode'])
def test_changed_cached_source_is_refused_without_overwriting_it(tmp_path, mutation):
    api = correction_api()
    st, _ = source(tmp_path, CASES[0])
    plan = api.plan(st)
    destination = tmp_path / 'cache/pipeline'
    working = api.materialize(plan, destination)
    if mutation == 'bytes':
        (destination / 'main.nf').write_text('// user changed this\n')
    elif mutation == 'extra':
        (destination / 'extra.nf').write_text('// additional runtime source\n')
    else:
        (destination / 'bin/tool').chmod(0o644)
    altered = replay_guard.hash_pipeline(destination)
    with pytest.raises(NfclawError, match='(?i)(changed|mode|inventory|source)'):
        api.verify(working)
    with pytest.raises(NfclawError):
        api.materialize(plan, destination)
    assert replay_guard.hash_pipeline(destination) == altered


def test_changed_original_after_planning_never_publishes_a_copy(tmp_path):
    api = correction_api()
    st, target = source(tmp_path, CASES[0])
    plan = api.plan(st)
    target.write_bytes(target.read_bytes() + b'\n// changed after plan\n')
    destination = tmp_path / 'cache/pipeline'
    with pytest.raises(NfclawError, match='(?i)(changed|source)'):
        api.materialize(plan, destination)
    assert not destination.exists()


def test_materialization_cannot_write_inside_the_original_source(tmp_path):
    api = correction_api()
    st, _ = source(tmp_path, CASES[0])
    plan = api.plan(st)
    before = replay_guard.hash_pipeline(st.path)
    with pytest.raises(NfclawError):
        api.materialize(plan, st.path / 'generated-copy')
    assert replay_guard.hash_pipeline(st.path) == before


def test_a_destination_symlink_is_never_treated_as_an_owned_source_copy(tmp_path):
    api = correction_api()
    st, _ = source(tmp_path, CASES[0])
    plan = api.plan(st)
    destination = tmp_path / 'pipeline'
    victim = tmp_path / 'other'
    victim.mkdir()
    (victim / 'sentinel').write_text('keep')
    destination.symlink_to(victim, target_is_directory=True)
    with pytest.raises(NfclawError):
        api.materialize(plan, destination)
    assert [path.name for path in victim.iterdir()] == ['sentinel']


def test_added_empty_directory_invalidates_the_corrected_namespace(tmp_path):
    api = correction_api()
    st, _ = source(tmp_path, CASES[0])
    working = api.materialize(api.plan(st), tmp_path / 'cache/pipeline')
    (working.path / 'unexpected-empty-directory').mkdir()
    with pytest.raises(NfclawError, match='(?i)(inventory|namespace|directory|source)'):
        api.verify(working)


def test_external_directory_link_is_refused_before_reading_its_files(tmp_path, monkeypatch):
    api = correction_api()
    st, _ = source(tmp_path, CASES[0])
    working = api.materialize(api.plan(st), tmp_path / 'cache/pipeline')
    outside = tmp_path / 'external'
    outside.mkdir()
    (outside / 'private-source.txt').write_text('unselected external bytes')
    (working.path / 'foreign').symlink_to(outside, target_is_directory=True)
    original_sha = replay_guard._sha256

    def bounded_sha(path):
        assert path.name != 'private-source.txt', 'external source bytes were read'
        return original_sha(path)

    monkeypatch.setattr(replay_guard, '_sha256', bounded_sha)
    with pytest.raises(NfclawError):
        api.verify(working)


def test_exact_bytes_used_for_patching_must_match_the_audit_hash(tmp_path, monkeypatch):
    api = correction_api()
    st, target = source(tmp_path, CASES[0])
    original_bytes = target.read_bytes()
    original_snapshot = replay_guard.hash_pipeline

    def capture_then_mutate(path):
        result = original_snapshot(path)
        if path == st.path:
            target.write_bytes(original_bytes + b'\nprintln("unreviewed code")\n')
        return result

    monkeypatch.setattr(replay_guard, 'hash_pipeline', capture_then_mutate)
    try:
        with pytest.raises(NfclawError, match='(?i)(source|checksum|hash|changed)'):
            api.plan(st)
    finally:
        target.write_bytes(original_bytes)


@pytest.mark.parametrize('failed_directory', ['pipeline', 'bin'])
def test_failed_directory_open_removes_only_the_new_owned_copy(tmp_path, monkeypatch,
                                                              failed_directory):
    api = correction_api()
    st, _ = source(tmp_path, CASES[0])
    plan = api.plan(st)
    destination = tmp_path / 'cache/pipeline'
    real_open = api.os.open

    def fail_directory(path, flags, *args, **kwargs):
        if Path(path).name == failed_directory and flags & api.os.O_DIRECTORY:
            raise OSError('injected directory-open failure')
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(api.os, 'open', fail_directory)
    with pytest.raises(NfclawError):
        api.materialize(plan, destination)
    assert not destination.exists()
    assert replay_guard.hash_pipeline(st.path) == plan.original_files


def test_replaced_cache_parent_never_redirects_writes_into_the_original(tmp_path, monkeypatch):
    api = correction_api()
    st, _ = source(tmp_path, CASES[0])
    plan = api.plan(st)
    parent = tmp_path / 'cache'
    parent.mkdir()
    before = sorted(str(path.relative_to(st.path)) for path in st.path.rglob('*'))
    original_check = api._original_unchanged
    swapped = False

    def replace_parent(checked_plan):
        nonlocal swapped
        original_check(checked_plan)
        if not swapped:
            parent.rename(tmp_path / 'renamed-cache')
            parent.symlink_to(st.path, target_is_directory=True)
            swapped = True

    monkeypatch.setattr(api, '_original_unchanged', replace_parent)
    with pytest.raises(NfclawError):
        api.materialize(plan, parent / 'pipeline')
    assert sorted(str(path.relative_to(st.path)) for path in st.path.rglob('*')) == before


@pytest.mark.parametrize('relative', ['.', 'bin'])
def test_namespace_addition_during_verification_is_detected(tmp_path, monkeypatch, relative):
    api = correction_api()
    st, _ = source(tmp_path, CASES[0])
    working = api.materialize(api.plan(st), tmp_path / 'cache/pipeline')
    target = working.path / relative
    target_info = target.stat()
    real_listdir = api.os.listdir
    changed = False

    def list_then_add(fd):
        nonlocal changed
        entries = real_listdir(fd)
        if not changed and api.os.path.samestat(target_info, api.os.fstat(fd)):
            (target / 'unexpected-after-listing').mkdir()
            changed = True
        return entries

    monkeypatch.setattr(api.os, 'listdir', list_then_add)
    with pytest.raises(NfclawError):
        api.verify(working)
