"""Exact candidate bundles and conservative native-task publication evidence."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/maintenance_candidate.py'


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True,
                          check=True).stdout.strip()


@pytest.fixture
def candidate(tmp_path):
    root = tmp_path / 'repo'
    root.mkdir()
    git(root, 'init', '-q', '-b', 'main')
    git(root, 'config', 'user.name', 'test')
    git(root, 'config', 'user.email', 'test@example.com')
    (root / 'catalog.json').write_text('{}\n')
    (root / 'catalog.md').write_text('original\n')
    (root / '.gitmodules').write_text('[submodule "pipelines/mini/upstream"]\n'
        'path = pipelines/mini/upstream\nurl = https://github.com/nf-core/mini.git\n')
    (root / 'sources.tsv').write_text('mini\thttps://github.com/nf-core/mini.git\tlatest-release\n')
    (root / 'README.md').write_text('original\n')
    upstream = root / 'pipelines/mini/upstream'
    upstream.mkdir(parents=True)
    git(upstream, 'init', '-q')
    git(upstream, 'config', 'user.name', 'test')
    git(upstream, 'config', 'user.email', 'test@example.com')
    (upstream / 'nextflow.config').write_text("manifest { nextflowVersion = '!>=25.10.4' }\n")
    git(upstream, 'add', '.')
    git(upstream, 'commit', '-qm', 'old release')
    old_pin = git(upstream, 'rev-parse', 'HEAD')
    git(root, 'add', '.')
    git(root, 'commit', '-qm', 'base')
    base = git(root, 'rev-parse', 'HEAD')
    (upstream / 'main.nf').write_text('workflow {}\n')
    git(upstream, 'add', '.')
    git(upstream, 'commit', '-qm', 'new release')
    pin = git(upstream, 'rev-parse', 'HEAD')
    git(root, 'add', 'pipelines/mini/upstream')
    (root / 'catalog.md').write_text('regenerated\n')
    artifact = tmp_path / 'candidate'

    def run(command='prepare', **kwargs):
        argv = [sys.executable, str(SCRIPT), command, '--directory', str(artifact),
                '--base', base]
        if command == 'prepare':
            argv.extend(['--kind', 'update'])
        else:
            argv.extend(['--sha', json.loads((artifact / 'candidate.json').read_text())['sha']])
        for key, value in kwargs.items():
            argv.extend(['--' + key.replace('_', '-'), str(value)])
        return subprocess.run(argv, cwd=root, text=True, capture_output=True)

    run.expected_pin = pin
    run.old_pin = old_pin
    return root, base, artifact, run


def prepare(candidate):
    root, base, artifact, run = candidate
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads((artifact / 'candidate.json').read_text())


def test_candidate_preserves_checkout_and_restores_exact_generated_commit(candidate, tmp_path):
    root, base, artifact, run = candidate
    staged = git(root, 'diff', '--cached', '--raw')
    metadata = prepare(candidate)
    assert metadata['base'] == base and metadata['sha'] != base
    assert metadata['pipelines'] == {'mini': run.expected_pin}
    assert git(root, 'rev-parse', 'HEAD') == base
    assert git(root, 'diff', '--cached', '--raw') == staged
    clone = tmp_path / 'clone'
    git(tmp_path, 'clone', '-q', '--no-checkout', str(root), str(clone))
    git(clone, 'checkout', '-q', base)
    result = subprocess.run([sys.executable, str(SCRIPT), 'restore', '--directory', str(artifact),
                             '--base', base, '--sha', metadata['sha']], cwd=clone,
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert git(clone, 'rev-parse', 'HEAD') == metadata['sha']
    assert (clone / 'catalog.md').read_text() == 'regenerated\n'
    assert git(clone, 'ls-tree', 'HEAD', 'pipelines/mini/upstream').startswith(
        f'160000 commit {run.expected_pin}')


@pytest.mark.parametrize('field,value', [('sha', 'f' * 40), ('base', 'e' * 40),
                                        ('pipelines', {}), ('kind', 'discover')])
def test_candidate_substitution_is_refused_before_checkout(candidate, field, value):
    root, base, artifact, run = candidate
    metadata = prepare(candidate)
    # Expected values are supplied independently of the corrupted artifact.
    sha = metadata['sha']
    metadata[field] = value
    (artifact / 'candidate.json').write_text(json.dumps(metadata))
    result = subprocess.run([sys.executable, str(SCRIPT), 'restore', '--directory', str(artifact),
                             '--base', base, '--sha', sha], cwd=root,
                            text=True, capture_output=True)
    assert result.returncode != 0
    assert git(root, 'rev-parse', 'HEAD') == base


def test_candidate_rejects_changes_outside_generated_paths(candidate):
    root, base, artifact, run = candidate
    (root / 'README.md').write_text('unexpected source change\n')
    result = run()
    assert result.returncode != 0
    assert not artifact.exists() and git(root, 'rev-parse', 'HEAD') == base


def test_metadata_only_candidate_has_no_fabricated_native_inventory(candidate):
    root, base, _, run = candidate
    git(root / 'pipelines/mini/upstream', 'checkout', '-q', run.old_pin)
    assert prepare(candidate)['pipelines'] == {}


def test_no_change_writes_no_bundle(candidate):
    root, _, artifact, run = candidate
    git(root / 'pipelines/mini/upstream', 'checkout', '-q', run.old_pin)
    (root / 'catalog.md').write_text('original\n')
    result = run()
    assert result.returncode == 0, result.stderr
    assert not artifact.exists()
    assert 'changed=false' in result.stdout


@pytest.fixture
def native(candidate, tmp_path):
    root, _, artifact, run = candidate
    metadata = prepare(candidate)
    git(root, 'reset', '--hard', metadata['sha'])
    analysis = tmp_path / 'analysis'
    (analysis / 'provenance').mkdir(parents=True)
    (analysis / 'pipeline_info').mkdir()
    manifest = analysis / 'provenance/run_manifest.json'
    manifest.write_text(json.dumps({'pipeline': 'mini', 'commit': run.expected_pin,
        'outcome': 'success', 'nextflow': 'nextflow version 25.10.4 build 1',
        'dependency_stability': {'status': 'unchanged'}}))
    trace = analysis / 'pipeline_info/execution_trace.txt'
    trace.write_text('task_id\tname\tstatus\texit\n1\tMINI:COUNT (sample1)\tCOMPLETED\t0\n')
    output = tmp_path / 'native.json'
    return run, analysis, manifest, trace, output


def test_native_evidence_binds_real_completed_tasks_to_candidate_and_pin(native):
    run, analysis, _, _, output = native
    result = run('native', pipeline='mini', analysis=analysis, output=output)
    assert result.returncode == 0, result.stderr
    record = json.loads(output.read_text())
    assert record['pipeline'] == 'mini' and record['pin'] == run.expected_pin
    assert record['tasks'] == [{'task_id': '1', 'name': 'MINI:COUNT (sample1)',
                                'status': 'COMPLETED', 'exit': '0'}]
    assert len(record['trace_sha256']) == 64 and len(record['manifest_sha256']) == 64


@pytest.mark.parametrize('change', ['empty', 'missing', 'cached', 'ignored', 'exit', 'duplicate',
                                    'stub_profile', 'stub_config', 'caveat', 'failed', 'wrong_pin',
                                    'changed_inputs', 'no_stability', 'two_traces'])
def test_native_publication_rejects_success_without_complete_real_task_evidence(native, change):
    run, analysis, manifest, trace, output = native
    value = json.loads(manifest.read_text())
    if change == 'empty':
        trace.write_text('task_id\tname\tstatus\texit\n')
    elif change == 'missing':
        trace.unlink()
    elif change in ('cached', 'ignored'):
        trace.write_text(trace.read_text().replace('COMPLETED',
                                                  'CACHED' if change == 'cached' else 'FAILED'))
    elif change == 'exit':
        trace.write_text(trace.read_text().replace('\t0\n', '\t1\n'))
    elif change == 'duplicate':
        with trace.open('a') as stream:
            stream.write('1\tMINI:COUNT (sample1)\tCOMPLETED\t0\n')
    elif change == 'two_traces':
        (trace.parent / 'execution_trace_other.txt').write_text(trace.read_text())
    elif change == 'stub_profile':
        value['stub_profiles'] = ['test']
    elif change == 'stub_config':
        value['stub_configs'] = ['all-stubs.config']
    elif change == 'caveat':
        value['completion_caveats'] = ['one sample was skipped']
    elif change == 'failed':
        value['outcome'] = 'failed'
    elif change == 'wrong_pin':
        value['commit'] = '3' * 40
    elif change == 'changed_inputs':
        value['dependency_stability'] = {'status': 'changed'}
    else:
        del value['dependency_stability']
    manifest.write_text(json.dumps(value))
    result = run('native', pipeline='mini', analysis=analysis, output=output)
    assert result.returncode != 0
    assert not output.exists()


@pytest.mark.parametrize('mutation', ['symlink', 'executable', 'delete', 'file_for_gitlink',
                                      'unapproved_url', 'extra_config', 'missing_registration'])
def test_unsafe_candidate_modes_or_registrations_never_produce_a_bundle(candidate, mutation):
    root, _, artifact, run = candidate
    if mutation == 'symlink':
        (root / 'catalog.md').unlink()
        (root / 'catalog.md').symlink_to('README.md')
    elif mutation == 'executable':
        (root / 'catalog.md').chmod(0o755)
    elif mutation == 'delete':
        (root / 'catalog.json').unlink()
    elif mutation == 'file_for_gitlink':
        import shutil
        shutil.rmtree(root / 'pipelines/mini/upstream')
        (root / 'pipelines/mini/upstream').write_text('replacement source file\n')
    elif mutation == 'unapproved_url':
        path = root / '.gitmodules'
        path.write_text(path.read_text().replace('https://github.com/nf-core/mini.git',
                                                'file:///private/other-repo'))
    elif mutation == 'extra_config':
        with (root / '.gitmodules').open('a') as stream:
            stream.write('update = !unapproved-command\n')
    else:
        (root / 'sources.tsv').write_text('')
    result = run()
    assert result.returncode != 0
    assert not artifact.exists()


def test_existing_nonautomatic_source_policy_survives_metadata_refresh(candidate):
    root, _, artifact, run = candidate
    (root / 'sources.tsv').write_text('mini\thttps://github.com/nf-core/mini.git\tmanual\n')
    git(root, 'add', 'sources.tsv')
    git(root, 'commit', '--only', 'sources.tsv', '-qm', 'keep this source manual')
    base = git(root, 'rev-parse', 'HEAD')
    git(root / 'pipelines/mini/upstream', 'checkout', '-q', run.old_pin)
    result = subprocess.run([sys.executable, str(SCRIPT), 'prepare', '--directory', str(artifact),
                             '--base', base, '--kind', 'update'], cwd=root,
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads((artifact / 'candidate.json').read_text())['base'] == base
