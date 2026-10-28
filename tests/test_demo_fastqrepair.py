"""A paired demo must preserve the damage cases and respect user-selected data."""
import csv
import io
import json
from pathlib import Path

import pytest

from runner import demo_defaults, fastqrepair_compat, orchestration, submodule

ROOT = Path(__file__).resolve().parents[1]
PIN = '70a38209407b9367a9ff7ab8b26d84cb1983ea18'
DAMAGE = 'f72c633f2547fdfaf475c7f05423437a7eac0bbf'
PAIRED = '800330ec8f47c93caabe8157e20dd23e243de4e1'
BASE = 'https://raw.githubusercontent.com/nf-core/test-datasets/'


@pytest.fixture
def prepare(tmp_path, monkeypatch):
    status = submodule.resolve('fastqrepair', ROOT / 'pipelines')
    if status.commit and status.commit != PIN:
        pytest.skip('requires the audited fastqrepair 1.1.1 source')
    if status.commit != PIN or not (status.path / 'nextflow_schema.json').is_file():
        pytest.skip('requires initialized pinned pipeline source')
    monkeypatch.setattr(orchestration.preflight, 'check_environment', lambda **kw: [])

    def check(**kwargs):
        options = dict(repo_root=ROOT, input_path=None, outdir=tmp_path / 'out', profile='docker',
                       params_file=None, cli_overrides={}, resume=False, demo=True,
                       check_only=True, write_provenance=False, timeout_seconds=30)
        options.update(kwargs)
        result = orchestration.run_pipeline('fastqrepair', **options)
        return result, json.loads((result.staging / 'params.json').read_text())
    return check


def test_fixture_keeps_original_damage_cases_and_adds_immutable_paired_control():
    sheet = demo_defaults.samplesheet('fastqrepair', PIN)
    assert sheet is not None
    assert list(csv.DictReader(io.StringIO(sheet.text))) == [
        {'sample': 'test_30reads',
         'fastq_1': BASE + DAMAGE + '/testdata/test_30reads_R1.fastq.gz',
         'fastq_2': BASE + DAMAGE + '/testdata/test_30reads_R2.fastq.gz'},
        {'sample': 'test_empty_file',
         'fastq_1': BASE + DAMAGE + '/testdata/empty_file.fastq', 'fastq_2': ''},
        {'sample': 'test_30reads_2',
         'fastq_1': BASE + DAMAGE + '/testdata/test_30reads_R2.fastq.gz', 'fastq_2': ''},
        {'sample': 'paired_control',
         'fastq_1': BASE + PAIRED + '/testdata/fastq/testsample01_1.fastq.gz',
         'fastq_2': BASE + PAIRED + '/testdata/fastq/testsample01_2.fastq.gz'}]
    assert sheet.files == ()
    assert sheet.record['kind'] == 'bundled_demo_fixture'
    assert sheet.record['data_commits'] == {'damage_cases': DAMAGE, 'paired_control': PAIRED}
    assert sheet.record['samples'] == sheet.record['rows'] == 4
    assert sheet.record['paired_end'] == sheet.record['single_end'] == 2
    assert sheet.record['row_roles'] == {
        'test_30reads': 'damaged_pair', 'test_empty_file': 'empty_single_end',
        'test_30reads_2': 'damaged_single_end', 'paired_control': 'paired_conservation_control'}
    assert fastqrepair_compat.paired_row_roles(sheet.rows) == {
        'test_30reads': ['test_30reads_recovered_1', 'test_30reads_recovered_2'],
        'paired_control': ['paired_control_recovered_1', 'paired_control_recovered_2']}


def test_bare_demo_stages_valid_sheet_and_retains_mate_roles(prepare):
    result, params = prepare()
    sheet = result.generated_samplesheet
    assert sheet is not None
    assert params['input'] == str(sheet)
    assert params['num_splits'] == 2
    assert result.validation_scope['local_samplesheets'] == 1
    assert fastqrepair_compat.paired_input_roles(sheet)['paired_control'] == [
        'paired_control_recovered_1', 'paired_control_recovered_2']
    assert not result.outdir.exists()


@pytest.mark.parametrize('source', ['cli', 'file'])
@pytest.mark.parametrize('selector,value', [
    ('input', 'https://example.org/user.csv'),
    ('pipelines_testdata_base_path', 'https://example.org/test-data/')])
def test_explicit_data_selectors_disable_entire_recipe(prepare, tmp_path, source, selector, value):
    params_file = tmp_path / 'user.json'
    params_file.write_text(json.dumps({selector: value}))
    result, params = prepare(cli_overrides={selector: value} if source == 'cli' else {},
                             params_file=params_file if source == 'file' else None)
    assert params[selector] == value
    assert result.generated_samplesheet is None
    assert 'num_splits' not in params


@pytest.mark.parametrize('source', ['cli', 'file'])
def test_explicit_split_count_wins_without_losing_demo_control(prepare, tmp_path, source):
    params_file = tmp_path / 'user.json'
    params_file.write_text(json.dumps({'num_splits': 1}))
    result, params = prepare(cli_overrides={'num_splits': 1} if source == 'cli' else {},
                             params_file=params_file if source == 'file' else None)
    assert params['num_splits'] == 1
    assert result.generated_samplesheet is not None


@pytest.mark.parametrize('kind', ['profile', 'config', 'non_demo'])
def test_custom_configuration_and_non_demo_runs_keep_ordinary_input(prepare, tmp_path, kind):
    config = tmp_path / 'user.config'
    config.write_text("params.input = 'https://example.org/user.csv'\n")
    result, params = prepare(profile='test_full,docker' if kind == 'profile' else 'docker',
                             configs=[str(config)] if kind == 'config' else [],
                             demo=kind != 'non_demo',
                             input_path='https://example.org/user.csv' if kind == 'non_demo'
                             else None)
    assert result.generated_samplesheet is None
    assert 'num_splits' not in params


@pytest.mark.parametrize('name,commit', [('fastqrepair', '0' * 40), ('another', PIN)])
def test_fixture_and_default_never_leak_to_other_revisions(name, commit):
    assert demo_defaults.parameters(name, commit) == {}
    assert demo_defaults.samplesheet(name, commit) is None
