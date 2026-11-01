"""Source identity controls exercise filesystem semantics, archive corruption and replay guards."""
from __future__ import annotations

import copy
import io
import json
import os
import stat
import subprocess
import tarfile
from pathlib import Path

import pytest

from runner import orchestration, provenance, replay_guard, source_identity
from runner.submodule import SubmoduleStatus


def tree(tmp_path):
    root = tmp_path / 'source'
    root.mkdir()
    (root / 'assets').mkdir()
    (root / 'assets/empty').mkdir()
    (root / 'main.nf').write_text('workflow {}\n')
    (root / 'assets/config').write_text('same bytes\n')
    (root / 'assets/other').write_text('same bytes\n')
    (root / 'tool').write_text('#!/bin/sh\nexit 0\n')
    (root / 'tool').chmod(0o755)
    (root / 'config-link').symlink_to('assets/config')
    (root / 'directory-link').symlink_to('assets', target_is_directory=True)
    os.link(root / 'tool', root / 'tool-alias')
    return root


def test_snapshot_includes_ignored_files_and_empty_directories_but_excludes_git_admin(tmp_path):
    root = tree(tmp_path)
    (root / '.git').mkdir()
    (root / '.git/config').write_text('administrative state')
    (root / '.gitignore').write_text('ignored-helper\n')
    (root / 'ignored-helper').write_text('runtime helper')
    record = source_identity.snapshot(root)
    assert record['entries']['ignored-helper']['type'] == 'file'
    assert record['entries']['assets/empty']['type'] == 'directory'
    (root / '.git/config').write_text('new administrative state')
    source_identity.check(root, record)


@pytest.mark.parametrize('mutation', ['mode', 'link-target', 'link-type', 'ignored-addition',
                                     'empty-directory', 'hardlink-topology'])
def test_source_identity_detects_changes_legacy_content_hashes_miss(tmp_path, mutation):
    root = tree(tmp_path)
    record = source_identity.snapshot(root)
    if mutation == 'mode':
        (root / 'main.nf').chmod(0o755)
    elif mutation == 'link-target':
        (root / 'config-link').unlink()
        (root / 'config-link').symlink_to('assets/other')  # byte-identical target
    elif mutation == 'link-type':
        (root / 'config-link').unlink()
        (root / 'config-link').write_text('same bytes\n')
    elif mutation == 'ignored-addition':
        (root / '.ignored-runtime').write_text('new code')
    elif mutation == 'empty-directory':
        (root / 'assets/empty').rmdir()
    else:
        content = (root / 'tool-alias').read_bytes()
        (root / 'tool-alias').unlink()
        (root / 'tool-alias').write_bytes(content)
        (root / 'tool-alias').chmod(0o755)
    with pytest.raises(ValueError, match='namespace, permissions or content changed'):
        source_identity.check(root, record)


def test_archive_preserves_links_modes_ignored_files_and_private_root(tmp_path):
    root = tree(tmp_path)
    (root / 'private-helper').write_text('private runtime code')
    (root / 'private-helper').chmod(0o600)
    record = source_identity.snapshot(root)
    archive = tmp_path / 'source.tar.gz'
    first = source_identity.write_archive(root, record, archive)
    assert source_identity.write_archive(root, record, archive) == first
    assert stat.S_IMODE(archive.stat().st_mode) & 0o077 == 0
    restored = tmp_path / 'restored'
    source_identity.check_archive(archive, record, restored)
    assert stat.S_IMODE(restored.stat().st_mode) == 0o700
    assert (restored / 'config-link').is_symlink()
    assert os.readlink(restored / 'config-link') == 'assets/config'
    assert os.path.samefile(restored / 'tool', restored / 'tool-alias')
    assert (restored / 'directory-link/empty').is_dir()
    source_identity.check(restored, record, private_root=True)
    (restored / 'private-helper').chmod(0o644)
    with pytest.raises(ValueError, match='permissions'):
        source_identity.check(restored, record, private_root=True)


def test_public_source_archives_keep_the_results_umask_for_group_replay(tmp_path):
    root = tree(tmp_path)
    root.chmod(0o755)
    for path in (root / 'assets', root / 'assets/empty'):
        path.chmod(0o755)
    for path in (root / 'main.nf', root / 'assets/config', root / 'assets/other'):
        path.chmod(0o644)
    archive = tmp_path / 'source.tar.gz'
    previous = os.umask(0o022)
    try:
        source_identity.write_archive(root, source_identity.snapshot(root), archive)
    finally:
        os.umask(previous)
    assert stat.S_IMODE(archive.stat().st_mode) == 0o644


@pytest.mark.parametrize('link', ['outside', 'absolute', 'cycle', 'git-admin'])
def test_unsupported_source_links_are_refused_without_reading_targets(tmp_path, link):
    root = tree(tmp_path)
    outside = tmp_path / 'private'
    outside.write_text('must not be incorporated into source')
    target = {'outside': '../private', 'absolute': str(root / 'main.nf'),
              'cycle': 'bad', 'git-admin': '.git/hooks/runtime'}[link]
    (root / 'bad').symlink_to(target)
    with pytest.raises(ValueError, match='symlink'):
        source_identity.snapshot(root)


def test_outside_hardlink_alias_is_refused(tmp_path):
    root = tree(tmp_path)
    os.link(root / 'main.nf', tmp_path / 'outside-alias')
    with pytest.raises(ValueError, match='hard-link alias outside'):
        source_identity.snapshot(root)


def test_shared_directory_modes_roundtrip_as_observed_by_the_host(tmp_path):
    root = tree(tmp_path)
    (root / 'assets').chmod(0o2775)
    expected = stat.S_IMODE((root / 'assets').stat().st_mode)
    record = source_identity.snapshot(root)
    archive = tmp_path / 'source.tar.gz'
    source_identity.write_archive(root, record, archive)
    restored = tmp_path / 'restored'
    source_identity.check_archive(archive, record, restored)
    assert stat.S_IMODE((restored / 'assets').stat().st_mode) == expected


def test_privileged_source_metadata_is_refused(tmp_path):
    root = tree(tmp_path)
    record = source_identity.snapshot(root)
    record['entries']['main.nf']['mode'] = 0o4755
    with pytest.raises(ValueError, match='privileged'):
        source_identity.inventory(record)
    (root / 'main.nf').chmod(0o4755)
    # Some hosts strip privileged bits at creation; Linux exercises the physical-file case too.
    if (root / 'main.nf').stat().st_mode & 0o6000:
        with pytest.raises(ValueError, match='privileged'):
            source_identity.snapshot(root)


def test_fifo_and_file_to_fifo_race_cannot_block_source_capture(tmp_path, monkeypatch):
    root = tree(tmp_path)
    real_open = os.open
    replaced = False

    def replace_before_open(name, flags, *args, **kwargs):
        nonlocal replaced
        if name == 'main.nf' and not replaced and kwargs.get('dir_fd') is not None:
            replaced = True
            (root / 'main.nf').unlink()
            os.mkfifo(root / 'main.nf')
        return real_open(name, flags, *args, **kwargs)

    monkeypatch.setattr(os, 'open', replace_before_open)
    with pytest.raises(ValueError, match='changed before reading'):
        source_identity.snapshot(root)
    assert replaced
    with pytest.raises(ValueError, match='special object'):
        source_identity.snapshot(root)


@pytest.mark.parametrize('attack', ['mode', 'link', 'hardlink', 'missing', 'duplicate'])
def test_archive_cannot_change_recorded_permissions_links_or_inventory(tmp_path, attack):
    root = tree(tmp_path)
    record = source_identity.snapshot(root)
    original = tmp_path / 'original.tar.gz'
    source_identity.write_archive(root, record, original)
    entries = []
    with tarfile.open(original) as tar:
        for item in tar:
            content = tar.extractfile(item).read() if item.isreg() else None
            entries.append((copy.copy(item), content))
    if attack == 'mode':
        next(item for item, _ in entries if item.name == 'tool').mode = 0o644
    elif attack == 'link':
        next(item for item, _ in entries if item.name == 'config-link').linkname = 'assets/other'
    elif attack == 'hardlink':
        next(item for item, _ in entries if item.name == 'tool-alias').linkname = 'main.nf'
    elif attack == 'missing':
        entries = [(item, data) for item, data in entries if item.name != 'assets/empty']
    else:
        entries.append(entries[0])
    changed = tmp_path / 'changed.tar.gz'
    with tarfile.open(changed, 'w:gz') as tar:
        for item, data in entries:
            tar.addfile(item, io.BytesIO(data) if data is not None else None)
    with pytest.raises(ValueError, match='archive'):
        source_identity.check_archive(changed, record, tmp_path / 'restored')


def test_existing_extraction_destination_is_never_replaced(tmp_path):
    root = tree(tmp_path)
    record = source_identity.snapshot(root)
    archive = tmp_path / 'source.tar.gz'
    source_identity.write_archive(root, record, archive)
    target = tmp_path / 'existing'
    target.mkdir()
    marker = target / 'keep'
    marker.write_text('existing evidence')
    with pytest.raises(FileExistsError):
        source_identity.check_archive(archive, record, target)
    assert marker.read_text() == 'existing evidence'


def test_malformed_archive_is_a_verification_error(tmp_path):
    root = tree(tmp_path)
    record = source_identity.snapshot(root)
    archive = tmp_path / 'not-an-archive'
    archive.write_bytes(b'not a tar archive')
    with pytest.raises(ValueError, match='archive is unreadable'):
        source_identity.check_archive(archive, record)


@pytest.mark.parametrize('name', ['../outside', 'config-link/escape', '.git/hooks/runtime'])
def test_recorded_namespace_cannot_redirect_archive_extraction(tmp_path, name):
    root = tree(tmp_path)
    record = source_identity.snapshot(root)
    archive = tmp_path / 'source.tar.gz'
    source_identity.write_archive(root, record, archive)
    record['entries'][name] = {'type': 'directory', 'mode': 0o755}
    destination = tmp_path / 'never-created'
    with pytest.raises(ValueError, match='source'):
        source_identity.check_archive(archive, record, destination)
    assert not destination.exists()


def test_new_bundle_binds_identity_and_verifies_archived_source_after_replay(tmp_path, monkeypatch):
    root = tree(tmp_path)
    monkeypatch.setattr(provenance, '_nextflow_version', lambda *_: 'nextflow version 25.10.4')
    out = tmp_path / 'out'
    out.mkdir()
    bundle = provenance.write(outdir=out, pipeline='fixture', input_paths=[],
        command_str=f'nextflow run {root} --outdir {out}',
        execution_git_head=None,  # this fixture deliberately has no Git administration tree
        submodule=SubmoduleStatus('fixture', root, True, True, '1.0.0', 'a' * 40, ()))
    manifest = json.loads((bundle / 'run_manifest.json').read_text())
    assert manifest['pipeline_identity_version'] == 2
    assert manifest['pipeline_source_selection'] is True
    intact = tmp_path / 'intact-replay'
    assert Path(replay_guard.choose_pipeline_source(bundle, intact)) == root
    replay_guard.verify_dependencies(bundle, intact)
    (root / 'config-link').unlink()
    target = tmp_path / 'replay'
    chosen = Path(replay_guard.choose_pipeline_source(bundle, target))
    assert chosen == target / 'provenance/pipeline'
    assert (chosen / 'config-link').is_symlink()
    replay_guard.verify_dependencies(bundle, target)
    (chosen / 'tool').chmod(0o644)
    with pytest.raises(ValueError, match='permissions'):
        replay_guard.verify_dependencies(bundle, target)
    (bundle / source_identity.RECORD).unlink()
    with pytest.raises(ValueError, match='incomplete'):
        replay_guard.verify_dependencies(bundle)


def test_legacy_content_only_bundle_is_not_relabelled_as_complete_identity(tmp_path, monkeypatch):
    root = tree(tmp_path)
    monkeypatch.setattr(provenance, '_nextflow_version', lambda *_: 'nextflow version 25.10.4')
    out = tmp_path / 'out'
    out.mkdir()
    legacy = provenance.hash_pipeline(root)
    bundle = provenance.write(outdir=out, pipeline='fixture', input_paths=[],
        pipeline_checksums=legacy, command_str='printf legacy',
        submodule=SubmoduleStatus('fixture', root, True, True, '1.0.0', 'a' * 40, ()))
    manifest = json.loads((bundle / 'run_manifest.json').read_text())
    assert manifest['pipeline_identity_version'] == 1
    assert manifest['pipeline_identity_scope'] == 'legacy content and revision only'
    assert 'pipeline_source_identity' not in manifest
    replay_guard.verify_dependencies(bundle)


def test_missing_bundled_helper_never_imports_an_ambient_replacement(tmp_path, monkeypatch):
    root = tree(tmp_path)
    monkeypatch.setattr(provenance, '_nextflow_version', lambda *_: 'nextflow version 25.10.4')
    out = tmp_path / 'out'
    out.mkdir()
    bundle = provenance.write(outdir=out, pipeline='fixture', input_paths=[],
        command_str='printf ANALYSIS_EXECUTED', execution_git_head=None,
        submodule=SubmoduleStatus('fixture', root, True, True, '1.0.0', 'a' * 40, ()))
    (bundle / 'source_identity.py').unlink()
    ambient = tmp_path / 'ambient'
    ambient.mkdir()
    marker = tmp_path / 'untrusted-code-executed'
    (ambient / 'source_identity.py').write_text(
        f'from pathlib import Path\nPath({str(marker)!r}).touch()\n')
    result = subprocess.run(['bash', str(bundle / 'commands.sh'), str(tmp_path / 'replay')],
                            env={**os.environ, 'PYTHONPATH': str(ambient)},
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert 'ANALYSIS_EXECUTED' not in result.stdout
    assert not marker.exists()
    assert 'bundled source_identity.py is missing or unreadable' in result.stderr


@pytest.mark.parametrize('change', ['unchanged', 'mode', 'ignored', 'legacy', 'missing', 'invalid'])
def test_resume_requires_the_same_complete_source_identity(tmp_path, monkeypatch, change):
    root = tree(tmp_path)
    monkeypatch.setattr(provenance, '_nextflow_version', lambda *_: 'nextflow version 25.10.4')
    out = tmp_path / 'out'
    out.mkdir()
    kwargs = {'pipeline_checksums': provenance.hash_pipeline(root)} if change == 'legacy' else {}
    bundle = provenance.write(outdir=out, pipeline='fixture', input_paths=[],
        command_str='printf fixture', execution_git_head=None,
        submodule=SubmoduleStatus('fixture', root, True, True, '1.0.0', 'a' * 40, ()), **kwargs)
    if change == 'mode':
        (root / 'main.nf').chmod(0o755)
    elif change == 'ignored':
        (root / '.ignored-helper').write_text('new runtime code')
    elif change == 'missing':
        (bundle / 'run_manifest.json').unlink()
    elif change == 'invalid':
        (bundle / 'run_manifest.json').write_text('[]')
    warning = orchestration._source_resume_warning(out, root, source_identity.snapshot(root))
    if change == 'unchanged':
        assert warning is None
    else:
        assert 'fresh Nextflow cache session' in warning
