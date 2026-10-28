"""The unformatted reference directory is a source-audited input, including its indexes."""
import hashlib
import json
import subprocess

import pytest

from runner import orchestration, parameters, replay_guard, schema
from runner.errors import NfclawError


@pytest.fixture
def directory_reference(library, tmp_path, monkeypatch, no_engine_probe):
    root = library('mini')
    up = root / 'pipelines/mini/upstream'
    path = up / 'nextflow_schema.json'
    data = json.loads(path.read_text())
    properties = data['definitions']['input_output_options']['properties']
    properties['amp_ampcombi_db'] = {'type': 'string'}
    path.write_text(json.dumps(data))
    git = ['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', '-C', str(up)]
    subprocess.run(['git', 'init', '-q', str(up)], check=True)
    subprocess.run([*git, 'add', '-A'], check=True)
    subprocess.run([*git, 'commit', '-q', '-m', 'release'], check=True)
    head = subprocess.check_output([*git, 'rev-parse', 'HEAD'], text=True).strip()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    registry = tmp_path / 'roles.json'
    registry.write_text(json.dumps({digest: {
        'pipeline': 'mini', 'releases': {'1.0.0': head}, 'values': {},
        'paths': {'amp_ampcombi_db': {'format': 'directory-path', 'exists': True,
                                    'source': ['main.nf:1'],
                                    'use': 'consumed reference directory'}}}}))
    monkeypatch.setattr(schema, '_PARAM_ROLES', registry)
    monkeypatch.setattr(orchestration.preflight, 'check_environment', lambda **kwargs: [])
    monkeypatch.setattr(orchestration.execution, 'run', lambda *args, **kwargs: None)
    monkeypatch.chdir(tmp_path)
    reference = tmp_path / 'amp_DRAMP_database'
    (reference / 'mmseqs2').mkdir(parents=True)
    (reference / 'general_amps.fasta').write_text('>DRAMP1\nACDE\n')
    (reference / 'general_amps.txt').write_text('DRAMP_ID\tSequence\nDRAMP1\tACDE\n')
    (reference / 'mmseqs2/ref_DB').write_bytes(b'known index')
    return root, up, reference


def run(root, outdir, reference):
    return orchestration.run_pipeline(
        'mini', repo_root=root, outdir=outdir, profile='docker',
        input_path=None, cli_overrides={'amp_ampcombi_db': str(reference)},
        demo=True, check_only=False, write_provenance=True, timeout_seconds=30,
        params_file=None, resume=False, nxf_ver='25.10.4')


def test_audited_directory_format_resolves_relative_reference(directory_reference):
    root, up, reference = directory_reference
    spec = schema.load_param_schema(up)
    assert spec.params['amp_ampcombi_db'].fmt == 'directory-path'
    assert spec.params['amp_ampcombi_db'].exists is True
    resolved = parameters.resolve_path_params({'amp_ampcombi_db': reference.name}, spec)
    assert resolved['amp_ampcombi_db'] == str(reference)


def test_directory_role_never_extends_to_another_revision(directory_reference):
    _, up, _ = directory_reference
    subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                    '-C', str(up), 'commit', '-q', '--allow-empty', '-m', 'other'], check=True)
    assert schema.load_param_schema(up).params['amp_ampcombi_db'].fmt is None


def test_reference_indexes_are_snapshotted(directory_reference, tmp_path):
    root, _, reference = directory_reference
    out = tmp_path / 'out'
    run(root, out, reference)
    checksums = replay_guard.read_checksums(out / 'provenance/inputs.sha256', relative=False)
    assert str(reference / 'mmseqs2/ref_DB') in checksums
    assert str(reference / 'general_amps.fasta') in checksums
    sources = json.loads((out / 'provenance/inputs.sources.json').read_text())
    assert str(reference) in sources


def test_changed_index_refuses_guarded_replay(directory_reference, tmp_path):
    root, _, reference = directory_reference
    out = tmp_path / 'out'
    run(root, out, reference)
    replay_guard.verify_dependencies(out / 'provenance')
    (reference / 'mmseqs2/ref_DB').write_bytes(b'changed index')
    with pytest.raises(ValueError, match='ref_DB'):
        replay_guard.verify_dependencies(out / 'provenance')


def test_output_inside_reference_is_refused_before_writes(directory_reference):
    root, _, reference = directory_reference
    out = reference / 'results'
    with pytest.raises(NfclawError, match='(?i)(overlap|write|input|dependency)'):
        run(root, out, reference)
    assert not out.exists()
    assert not (reference / '.results.nfclaw.lock').exists()
    assert (reference / 'mmseqs2/ref_DB').read_bytes() == b'known index'
