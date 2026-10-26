"""The corrected bundled demo must carry its matched reference through normal parameters."""
import json
import re
from pathlib import Path

import pytest

from runner import demo_defaults, orchestration, submodule

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ('https://raw.githubusercontent.com/nf-core/test-datasets/'
             '618f1541382c4ad49eff566dadf13d5ccbd0ebb4/'
             'data/genomics/homo_sapiens/genome/genome.fasta')


@pytest.mark.parametrize('name,commit', [
    ('bamtofastq', '0' * 40), ('other', '8a295860c0c9221337dec7f2620709a47cea254d')])
def test_demo_reference_never_leaks_to_another_release_or_pipeline(name, commit):
    assert demo_defaults.parameters(name, commit) == {}


@pytest.mark.parametrize('override', [None, 'cli', 'file'])
def test_bamtofastq_bundled_demo_supplies_reference_without_overriding_user_values(
        tmp_path, monkeypatch, override):
    if not (ROOT / 'pipelines/bamtofastq/upstream/nextflow_schema.json').is_file():
        pytest.skip('requires the audited bamtofastq 2.2.1 source')
    st = submodule.resolve('bamtofastq', ROOT / 'pipelines')
    if st.commit != '8a295860c0c9221337dec7f2620709a47cea254d':
        pytest.skip('requires the audited bamtofastq 2.2.1 source')
    monkeypatch.setattr(orchestration.preflight, 'check_environment', lambda **kw: [])
    custom = 'https://example.org/custom.fasta'
    params_file = tmp_path / 'params.json' if override == 'file' else None
    if params_file:
        params_file.write_text(json.dumps({'fasta': custom}))
    result = orchestration.run_pipeline(
        'bamtofastq', repo_root=ROOT, input_path=None, outdir=tmp_path / 'out',
        profile='docker', params_file=params_file,
        cli_overrides={'fasta': custom} if override == 'cli' else {}, resume=False,
        demo=True, check_only=True, write_provenance=False, timeout_seconds=30)
    params = Path(re.search(r'-params-file (\S+)', result.command).group(1))
    assert json.loads(params.read_text())['fasta'] == (custom if override else REFERENCE)


@pytest.mark.parametrize('input_source', ['cli', 'file', 'non_demo'])
def test_demo_reference_is_never_assumed_for_user_inputs(tmp_path, monkeypatch, input_source):
    if not (ROOT / 'pipelines/bamtofastq/upstream/nextflow_schema.json').is_file():
        pytest.skip('requires the audited bamtofastq source')
    monkeypatch.setattr(orchestration.preflight, 'check_environment', lambda **kw: [])
    raw = 'https://example.org/custom.csv'
    params_file = tmp_path / 'params.json' if input_source == 'file' else None
    if params_file:
        params_file.write_text(json.dumps({'input': raw}))
    result = orchestration.run_pipeline(
        'bamtofastq', repo_root=ROOT, input_path=None if params_file else raw,
        outdir=tmp_path / 'out', profile='docker', params_file=params_file,
        cli_overrides={}, resume=False, demo=input_source != 'non_demo',
        check_only=True, write_provenance=False, timeout_seconds=30)
    params = Path(re.search(r'-params-file (\S+)', result.command).group(1))
    assert 'fasta' not in json.loads(params.read_text())
