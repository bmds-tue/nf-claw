"""Execution, resume and standalone replay must all use the recorded derived source."""
import hashlib
import json
import shlex
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from runner import chain, orchestration, replay_guard, source_corrections, submodule
from runner.errors import NfclawError


@pytest.fixture
def corrected_run(tmp_path, monkeypatch):
    root = tmp_path / 'repo'
    upstream = root / 'pipelines/mini/upstream'
    upstream.mkdir(parents=True)
    fixtures = Path(__file__).parent / 'fixtures'
    shutil.copy(fixtures / 'mini/nextflow_schema.json', upstream)
    (upstream / 'main.nf').write_text('// original entry point\n')
    (upstream / 'nextflow.config').write_text('// original configuration\n')
    target = upstream / 'subworkflows/local/sourmash_create/main.nf'
    target.parent.mkdir(parents=True)
    shutil.copy(fixtures / 'source_corrections/createtaxdb-sourmash-create.nf', target)
    subprocess.run(['git', 'init', '-q', str(upstream)], check=True)
    subprocess.run(['git', '-C', str(upstream), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(upstream), '-c', 'user.name=Test',
                    '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture'],
                   check=True)
    st = submodule.resolve_at('mini', upstream)
    (upstream.parent / 'skill.md').write_text('---\nname: mini\n---\n')
    recipe = replace(source_corrections._RECIPES[0], pipeline='mini', commit=st.commit)
    monkeypatch.setattr(source_corrections, '_RECIPES', (recipe,))
    monkeypatch.setenv('NFCLAW_SOURCE_CACHE', str(tmp_path / 'private-cache'))
    monkeypatch.setattr(orchestration.preflight, 'check_environment', lambda **kw: [])
    monkeypatch.setattr(orchestration.provenance, '_nextflow_version', lambda *a: '25.10.4')
    launched = []

    def execute(cmd, **kwargs):
        actual_source = Path(cmd[cmd.index('run') + 1])
        launched.append(actual_source)
        assert actual_source != upstream
        assert b'.sort(false)' in (actual_source / target.relative_to(upstream)).read_bytes()
        (kwargs['cwd'] / 'scientific-result.txt').write_text('verified result\n')
        kwargs['run_log'].write(b'N E X T F L O W  ~  version 25.10.4\n')

    monkeypatch.setattr(orchestration.execution, 'run', execute)
    kwargs = dict(repo_root=root, input_path=None, outdir=tmp_path / 'out', profile='docker',
                  params_file=None, cli_overrides={}, resume=False, demo=True, check_only=False,
                  write_provenance=True, timeout_seconds=30, resolved_tree=st)
    return st, target, kwargs, launched


def test_run_records_and_archives_the_actual_corrected_source(corrected_run):
    st, original, kwargs, launched = corrected_run
    original_bytes = original.read_bytes()
    result = orchestration.run_pipeline('mini', **kwargs)
    manifest = json.loads((result.outdir / 'provenance/run_manifest.json').read_text())
    assert manifest['commit'] == st.commit
    assert manifest['pipeline_git_head'] is None
    assert Path(manifest['pipeline_path']) == launched[0]
    correction = manifest['source_corrections']
    record_path = result.outdir / 'provenance' / correction['file']
    assert hashlib.sha256(record_path.read_bytes()).hexdigest() == correction['sha256']
    record = json.loads(record_path.read_text())
    assert record['upstream_commit'] == st.commit
    snapshot = replay_guard.read_checksums(result.outdir / 'provenance/pipeline.sha256')
    assert record['files'] == snapshot
    replay_guard.check_pipeline_archive(result.outdir / 'provenance', manifest)
    replay_guard.check_pipeline_checkout(result.outdir / 'provenance', manifest)
    assert original.read_bytes() == original_bytes


def test_check_prints_a_corrected_runnable_copy_without_creating_outdir(corrected_run):
    st, original, kwargs, launched = corrected_run
    result = orchestration.run_pipeline('mini', **{**kwargs, 'check_only': True})
    cmd = shlex.split(result.command)
    actual = Path(cmd[cmd.index('run') + 1])
    assert actual.resolve().is_relative_to(result.staging.resolve())
    assert actual in result.local_dependencies
    assert b'.sort(false)' in (actual / original.relative_to(st.path)).read_bytes()
    assert not launched
    assert not result.outdir.exists()


def test_no_provenance_still_binds_source_and_unchanged_resume(corrected_run):
    st, _, kwargs, launched = corrected_run
    kwargs['write_provenance'] = False
    result = orchestration.run_pipeline('mini', **kwargs)
    minimal_record = result.outdir / 'provenance/working-source.json'
    assert json.loads(minimal_record.read_text())['upstream_commit'] == st.commit
    assert not (result.outdir / 'provenance/run_manifest.json').exists()
    orchestration.run_pipeline('mini', **{**kwargs, 'resume': True})
    assert launched == [launched[0], launched[0]]


@pytest.mark.parametrize('change', ['missing_record', 'recipe', 'copy_bytes', 'copy_mode'])
def test_resume_refuses_missing_or_changed_source_identity(corrected_run, monkeypatch, change):
    _, _, kwargs, launched = corrected_run
    orchestration.run_pipeline('mini', **kwargs)
    if change == 'missing_record':
        (kwargs['outdir'] / 'provenance/working-source.json').unlink()
    elif change == 'recipe':
        recipe = source_corrections._RECIPES[0]
        monkeypatch.setattr(source_corrections, '_RECIPES', (replace(recipe, identifier='new'),))
    elif change == 'copy_bytes':
        (launched[0] / 'main.nf').write_text('// user modification\n')
    else:
        (launched[0] / 'main.nf').chmod(0o755)
    with pytest.raises(NfclawError, match='(?i)(source|recipe|correction)'):
        orchestration.run_pipeline('mini', **{**kwargs, 'resume': True})
    assert len(launched) == 1


def test_cache_publication_is_checked_against_inputs_and_original_before_writing(
        corrected_run, monkeypatch):
    st, _, kwargs, launched = corrected_run
    monkeypatch.setenv('NFCLAW_SOURCE_CACHE', str(st.path / 'must-not-be-created'))
    with pytest.raises(NfclawError):
        orchestration.run_pipeline('mini', **kwargs)
    assert not launched
    assert not (st.path / 'must-not-be-created').exists()


def test_execution_may_not_write_inside_an_existing_corrected_source(corrected_run, monkeypatch):
    _, _, kwargs, launched = corrected_run
    orchestration.run_pipeline('mini', **kwargs)
    work = launched[0] / 'engine-work'
    with pytest.raises(NfclawError):
        orchestration.run_pipeline('mini', **{**kwargs, 'resume': True,
                                              'nxf_env': {'NXF_WORK': str(work)}})
    assert len(launched) == 1
    assert not work.exists()


def test_derived_source_modes_are_checked_after_execution(corrected_run, monkeypatch):
    _, _, kwargs, launched = corrected_run
    original_execute = orchestration.execution.run

    def mutate(cmd, **options):
        original_execute(cmd, **options)
        (launched[-1] / 'main.nf').chmod(0o755)

    monkeypatch.setattr(orchestration.execution, 'run', mutate)
    with pytest.raises(NfclawError, match='(?i)(source|dependencies)'):
        orchestration.run_pipeline('mini', **kwargs)
    bundle = kwargs['outdir'] / 'provenance'
    manifest = json.loads((bundle / 'run_manifest.json').read_text())
    assert manifest['outcome'] == 'failed'
    assert manifest['dependency_stability']['status'] == 'changed'
    assert 'pipeline_archive_error' in manifest
    record = json.loads((bundle / manifest['source_corrections']['file']).read_text())
    assert replay_guard.read_checksums(bundle / 'pipeline.sha256') == record['files']
    assert (bundle / 'inputs.sha256').exists() and (bundle / 'configs.sha256').exists()


def test_snapshot_cannot_adopt_changed_bytes_as_a_new_corrected_baseline(
        corrected_run, monkeypatch):
    _, _, kwargs, launched = corrected_run
    original_verify = source_corrections.verify

    def change_after_verifying(working):
        original_verify(working)
        if (kwargs['outdir'] / 'provenance/working-source.json').exists():
            (working.path / 'main.nf').write_text('// changed after source verification\n')

    monkeypatch.setattr(source_corrections, 'verify', change_after_verifying)
    with pytest.raises(NfclawError):
        orchestration.run_pipeline('mini', **kwargs)
    assert not launched


def test_minimum_source_identity_cannot_change_during_a_no_provenance_run(
        corrected_run, monkeypatch):
    _, _, kwargs, _ = corrected_run
    original_execute = orchestration.execution.run

    def mutate(cmd, **options):
        original_execute(cmd, **options)
        (options['cwd'] / 'provenance/working-source.json').write_text('{}\n')

    monkeypatch.setattr(orchestration.execution, 'run', mutate)
    with pytest.raises(NfclawError, match='(?i)(dependencies|source)'):
        orchestration.run_pipeline('mini', **{**kwargs, 'write_provenance': False})


def test_chain_fingerprint_binds_applicable_recipe_only(corrected_run, monkeypatch):
    st, _, _, _ = corrected_run
    stage = chain.parse_spec({'stages': [{'pipeline': 'mini', 'demo': True}]}).stages[0]
    planned = chain.Planned(stage, st, None, None, {})
    original = chain.fingerprint(planned)
    recipe = source_corrections._RECIPES[0]
    monkeypatch.setattr(source_corrections, '_RECIPES', (replace(recipe, identifier='new'),))
    assert chain.fingerprint(planned) != original
    unrelated = replace(planned, tree=replace(st, commit='f' * 40))
    ordinary = chain.fingerprint(unrelated)
    monkeypatch.setattr(source_corrections, '_RECIPES', ())
    assert chain.fingerprint(unrelated) == ordinary


@pytest.mark.parametrize('ignored', [False, True])
def test_corrected_source_does_not_silently_drop_untracked_runtime_files(corrected_run, ignored):
    st, _, kwargs, launched = corrected_run
    if ignored:
        (st.path / '.git/info/exclude').write_text('local-helper.nf\n')
    extra = st.path / 'local-helper.nf'
    extra.write_text('// user runtime helper\n')
    with pytest.raises(NfclawError, match='(?i)(untracked|source|inventory)'):
        orchestration.run_pipeline('mini', **kwargs)
    assert extra.read_text() == '// user runtime helper\n'
    assert not launched


def test_archive_fallback_checks_corrected_source_modes_without_either_original(
        corrected_run):
    st, _, kwargs, launched = corrected_run
    orchestration.run_pipeline('mini', **kwargs)
    bundle = kwargs['outdir'] / 'provenance'
    manifest = json.loads((bundle / 'run_manifest.json').read_text())
    st.path.rename(st.path.with_name('preserved-original'))
    launched[0].rename(launched[0].with_name('preserved-corrected'))
    target = kwargs['outdir'].with_name('replay')
    actual = Path(replay_guard.choose_pipeline_source(bundle, target))
    assert actual == target / 'provenance/pipeline'
    record = json.loads((bundle / manifest['source_corrections']['file']).read_text())
    replay_guard.check_corrected_source(actual, record)
    replay_guard.verify_dependencies(bundle, target)
    (actual / 'main.nf').chmod(0o755)
    with pytest.raises(ValueError, match='(?i)(mode|source)'):
        replay_guard.verify_dependencies(bundle, target)


def test_a_corrected_checkout_replaced_by_a_symlink_uses_the_archive(corrected_run):
    _, _, kwargs, launched = corrected_run
    orchestration.run_pipeline('mini', **kwargs)
    bundle = kwargs['outdir'] / 'provenance'
    path = launched[0]
    preserved = path.with_name('preserved-source')
    path.rename(preserved)
    path.symlink_to(preserved, target_is_directory=True)
    replay = kwargs['outdir'].with_name('replay')
    actual = Path(replay_guard.choose_pipeline_source(bundle, replay))
    assert actual == replay / 'provenance/pipeline'


def test_corrected_replay_requires_the_record_of_which_source_actually_ran(corrected_run):
    _, _, kwargs, _ = corrected_run
    orchestration.run_pipeline('mini', **kwargs)
    bundle = kwargs['outdir'] / 'provenance'
    replay = kwargs['outdir'].with_name('replay')
    replay_guard.choose_pipeline_source(bundle, replay)
    (replay / 'provenance' / replay_guard.PIPELINE_SOURCE_RECORD).unlink()
    with pytest.raises(ValueError, match='(?i)(source|record)'):
        replay_guard.verify_dependencies(bundle, replay)
