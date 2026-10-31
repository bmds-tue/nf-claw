"""Frozen stages need private effective-value identity independently of public redaction."""
# ruff: noqa: F811
import hashlib
import json
import os
import stat

import pytest

from runner import chain
from runner.errors import NfclawError
from test_chain import _boom, fake_runs  # noqa: F401


def _spec(env=None, *, stage=False):
    data = {'stages': [{'pipeline': 'mini_up'}]}
    if env is not None:
        (data['stages'][0] if stage else data)['nxf_env'] = env
    return chain.parse_spec(data)


def _snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('stage', [False, True])
@pytest.mark.parametrize('before,after', [
    ({'NXF_TOKEN': 'synthetic-first'}, {'NXF_TOKEN': 'synthetic-second'}),
    ({'NXF_JVM_ARGS': '-Dpassword=synthetic -Xmx1g'},
     {'NXF_JVM_ARGS': '-Dpassword=synthetic -Xmx8g'})])
def test_changed_private_effective_environment_refuses_frozen_stage(
        library, fake_runs, tmp_path, stage, before, after):
    root, out = library('mini_up'), tmp_path / 'chain'
    chain.run_chain(_spec(before, stage=stage), repo_root=root, outdir=out)
    previous = _snapshot(out)
    with pytest.raises(NfclawError, match='different definition'):
        chain.run_chain(_spec(after, stage=stage), repo_root=root, outdir=out, resume=True)
    assert _snapshot(out) == previous
    assert len(fake_runs.calls) == 1


def test_inherited_private_settings_are_frozen(library, fake_runs, tmp_path, monkeypatch):
    root, out = library('mini_up'), tmp_path / 'chain'
    monkeypatch.setenv('NXF_TOKEN', 'synthetic-first')
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    monkeypatch.setenv('NXF_TOKEN', 'synthetic-second')
    with pytest.raises(NfclawError, match='different definition'):
        chain.run_chain(_spec(), repo_root=root, outdir=out, resume=True)
    assert len(fake_runs.calls) == 1


def test_private_identity_key_and_values_stay_out_of_recorded_artifacts(
        library, fake_runs, tmp_path):
    root, out = library('mini_up'), tmp_path / 'chain'
    spec = _spec({'NXF_TOKEN': 'synthetic-private-value'})
    chain.run_chain(spec, repo_root=root, outdir=out)
    key_path = out / 'chain/.environment-key'
    assert key_path.is_file()
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(key_path.parent.stat().st_mode) == 0o700
    key = key_path.read_bytes()
    assert len(key) == 32
    for path in out.rglob('*'):
        if path.is_file() and path != key_path:
            content = path.read_bytes()
            assert b'synthetic-private-value' not in content
            assert key not in content and key.hex().encode() not in content
    assert chain.run_chain(spec, repo_root=root, outdir=out, resume=True).outcome == 'success'
    assert len(fake_runs.calls) == 1


@pytest.mark.parametrize('damage', ['missing', 'wrong', 'public_mode', 'symlink'])
def test_private_identity_key_damage_refuses_resume_without_changing_recorded_data(
        library, fake_runs, tmp_path, damage):
    root, out = library('mini_up'), tmp_path / 'chain'
    spec = _spec({'NXF_TOKEN': 'synthetic-private-value'})
    chain.run_chain(spec, repo_root=root, outdir=out)
    key = out / 'chain/.environment-key'
    assert key.is_file()
    if damage == 'missing':
        key.unlink()
    elif damage == 'wrong':
        key.write_bytes(b'x' * 32)
    elif damage == 'public_mode':
        key.chmod(0o644)
    else:
        saved = tmp_path / 'saved-key'
        key.rename(saved)
        key.symlink_to(saved)
    previous = _snapshot(out)
    with pytest.raises(NfclawError, match='key|different definition'):
        chain.run_chain(spec, repo_root=root, outdir=out, resume=True)
    assert _snapshot(out) == previous
    assert len(fake_runs.calls) == 1


@pytest.mark.parametrize('retain_current_env', [False, True])
def test_legacy_sensitive_identity_is_not_recovered_from_newly_supplied_values(
        library, fake_runs, tmp_path, retain_current_env):
    root, out = library('mini_up'), tmp_path / 'chain'
    spec = _spec({'NXF_TOKEN': 'synthetic-private-value'})
    chain.run_chain(spec, repo_root=root, outdir=out)
    # Independent version-2 control: the old format hashed redacted serialization only.
    body = {'fingerprint_version': 2, 'pipeline': 'mini_up', 'pipeline_version': None,
            'commit': '', 'input': None, 'input_sha256': None, 'params': {},
            'params_file': None, 'demo': False, 'handoff': None,
            'options': {'profile': 'docker', 'nxf_ver': None,
                        'nxf_env': {'NXF_TOKEN': '<redacted>'}, 'config': [], 'limits': {}},
            'config_sha256': {}}
    state_path = out / 'chain/state.json'
    state = json.loads(state_path.read_text())
    state.pop('environment_key_sha256', None)
    state['stages'][0].pop('environment_identity_version', None)
    state['stages'][0]['fingerprint'] = hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    state_path.write_text(json.dumps(state))
    (out / 'chain/.environment-key').unlink(missing_ok=True)
    previous = _snapshot(out)
    with pytest.raises(NfclawError, match='legacy.*sensitive|sensitive.*legacy'):
        chain.run_chain(spec if retain_current_env else _spec(), repo_root=root,
                        outdir=out, resume=True)
    assert _snapshot(out) == previous


def test_nonsensitive_version_two_chain_remains_resumable_without_a_key(
        library, fake_runs, tmp_path):
    root, out = library('mini_up'), tmp_path / 'chain'
    spec = _spec({'NXF_OFFLINE': 'true'})
    chain.run_chain(spec, repo_root=root, outdir=out)
    assert not (out / 'chain/.environment-key').exists()
    assert chain.run_chain(None, repo_root=root, outdir=out, resume=True).outcome == 'success'
    assert len(fake_runs.calls) == 1


def test_sensitive_check_does_not_create_a_key_or_output_directory(library, fake_runs, tmp_path):
    root, out = library('mini_up'), tmp_path / 'chain'
    result = chain.run_chain(_spec({'NXF_TOKEN': 'synthetic-private-value'}),
                             repo_root=root, outdir=out, check_only=True)
    assert result.outcome == 'checked'
    assert not out.exists()
    assert fake_runs.calls == []


def test_wrong_private_key_cannot_replace_identity_after_a_failed_stage(
        library, fake_runs, tmp_path):
    root, out = library('mini_up'), tmp_path / 'chain'
    spec = _spec({'NXF_TOKEN': 'synthetic-private-value'})
    fake_runs.failures['mini_up'] = [_boom()]
    with pytest.raises(NfclawError, match='execution failed'):
        chain.run_chain(spec, repo_root=root, outdir=out)
    (out / 'chain/.environment-key').write_bytes(b'x' * 32)
    previous = _snapshot(out)
    with pytest.raises(NfclawError, match='key'):
        chain.run_chain(spec, repo_root=root, outdir=out, resume=True)
    assert _snapshot(out) == previous
    assert len(fake_runs.calls) == 1


@pytest.mark.parametrize('malformed', ['not-a-digest', '\u00e9' * 64, [], None])
def test_malformed_private_key_verifier_is_a_resume_refusal(library, fake_runs, tmp_path,
                                                           malformed):
    root, out = library('mini_up'), tmp_path / 'chain'
    spec = _spec({'NXF_TOKEN': 'synthetic-private-value'})
    chain.run_chain(spec, repo_root=root, outdir=out)
    state_path = out / 'chain/state.json'
    state = json.loads(state_path.read_text())
    state['environment_key_sha256'] = malformed
    state_path.write_text(json.dumps(state))
    previous = _snapshot(out)
    with pytest.raises(NfclawError, match='key'):
        chain.run_chain(spec, repo_root=root, outdir=out, resume=True)
    assert _snapshot(out) == previous


def test_appending_sensitive_stage_adds_private_identity_under_writer_lock(
        library, fake_runs, tmp_path, monkeypatch):
    import fcntl

    root, out = library('mini_up'), tmp_path / 'chain'
    chain.run_chain(_spec(), repo_root=root, outdir=out)
    assert not (out / 'chain/.environment-key').exists()
    write = chain._write_json

    def check_private_creation(path, data):
        if path.name == 'state.json' and len(data.get('stages', [])) == 2:
            assert (out / 'chain/.environment-key').is_file()
            fd = os.open(out / 'chain/.lock', os.O_RDWR)
            try:
                with pytest.raises(BlockingIOError):
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                os.close(fd)
        return write(path, data)

    monkeypatch.setattr(chain, '_write_json', check_private_creation)
    extended = chain.parse_spec({'stages': [{'pipeline': 'mini_up'}, {
        'pipeline': 'mini_up', 'id': 'again', 'nxf_env': {'NXF_TOKEN': 'synthetic-value'},
        'handoff': {'params': {'gtf': {'file': 'fastq/A_1.fastq.gz'}}}}]})
    assert chain.run_chain(extended, repo_root=root, outdir=out, resume=True).outcome == 'success'
    assert len(fake_runs.calls) == 2
