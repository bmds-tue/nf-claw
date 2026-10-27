"""The pinned demo input must be immutable and conditional on bundled demo selection."""
import csv
import io
import json
from pathlib import Path

import pytest

from runner import demo_defaults, orchestration, submodule

ROOT = Path(__file__).resolve().parent.parent
PIN = '683daaf41bb396839445e603152b45daa141ced4'
DATA = '800330ec8f47c93caabe8157e20dd23e243de4e1'


@pytest.fixture
def prepare(tmp_path, monkeypatch):
    if not (ROOT / 'pipelines/hgtseq/upstream/nextflow_schema.json').is_file():
        pytest.skip('requires the audited hgtseq 1.1.0 source')
    if submodule.resolve('hgtseq', ROOT / 'pipelines').commit != PIN:
        pytest.skip('requires the audited hgtseq 1.1.0 source')
    monkeypatch.setattr(orchestration.preflight, 'check_environment', lambda **kw: [])

    def check(**kwargs):
        options = dict(repo_root=ROOT, input_path=None, outdir=tmp_path / 'out', profile='docker',
                       params_file=None, cli_overrides={}, resume=False, demo=True,
                       check_only=True, write_provenance=False, timeout_seconds=30)
        options.update(kwargs)
        result = orchestration.run_pipeline('hgtseq', **options)
        return result, json.loads((result.staging / 'params.json').read_text())
    return check


def test_bare_hgtseq_demo_stages_historical_columns_and_immutable_matched_data(prepare):
    result, params = prepare()
    path = result.generated_samplesheet
    assert path is not None
    assert params['input'] == str(path)
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    assert [r['sample'] for r in rows] == ['testsample01', 'testsample02', 'testsample03']
    assert all(set(row) == {'sample', 'group', 'input1', 'input2'} for row in rows)
    assert all(f'/{DATA}/testdata/fastq/' in row[key]
               for row in rows for key in ('input1', 'input2'))
    assert f'/{DATA}/testdata/reference/' in params['gff']
    assert '/56591d0269db196203af3b0cb2191da22384d24a/' in params['fasta']
    assert result.validation_scope['local_samplesheets'] == 1
    assert not result.outdir.exists()


@pytest.mark.parametrize('source', ['cli', 'file'])
def test_user_input_disables_hgtseq_managed_demo(prepare, tmp_path, source):
    url = 'https://example.org/my-samples.csv'
    file = tmp_path / 'params.json'
    file.write_text(json.dumps({'input': url}))
    result, params = prepare(input_path=url if source == 'cli' else None,
                             params_file=file if source == 'file' else None)
    assert params['input'] == url
    assert result.generated_samplesheet is None
    assert not {'fasta', 'gff', 'krakendb', 'kronadb'} & params.keys()


@pytest.mark.parametrize('kind', ['profile', 'config'])
def test_hgtseq_custom_configuration_disables_the_managed_fixture(prepare, tmp_path, kind):
    config = tmp_path / 'user.config'
    config.write_text("params.input = 'https://example.org/custom.csv'\n")
    result, params = prepare(profile='test_full,docker' if kind == 'profile' else 'docker',
                             configs=[str(config)] if kind == 'config' else [])
    assert result.generated_samplesheet is None
    assert not {'fasta', 'gff', 'krakendb', 'kronadb'} & params.keys()


@pytest.mark.parametrize('parameter', ['fasta', 'gff', 'krakendb', 'kronadb', 'igenomes_base'])
@pytest.mark.parametrize('source', ['cli', 'file'])
def test_explicit_reference_selector_prevents_mixing_demo_references(
        prepare, tmp_path, parameter, source):
    value = 'https://example.org/custom.fasta'
    params_file = tmp_path / 'params.json'
    params_file.write_text(json.dumps({parameter: value}))
    result, params = prepare(cli_overrides={parameter: value} if source == 'cli' else {},
                             params_file=params_file if source == 'file' else None)
    assert params[parameter] == value
    assert result.generated_samplesheet is None
    assert not ({'fasta', 'gff', 'krakendb', 'kronadb'} - {parameter}) & params.keys()


def test_undeclared_testdata_selector_keeps_ordinary_parameter_refusal(prepare):
    from runner.errors import NfclawError
    with pytest.raises(NfclawError, match='unknown parameter'):
        prepare(cli_overrides={'pipelines_testdata_base_path': 'https://example.org/custom'})


@pytest.mark.parametrize('parameter,aligner', [('bwaindex', 'bwa-mem'),
                                             ('bwamem2index', 'bwa-mem2')])
@pytest.mark.parametrize('source', ['cli', 'file'])
def test_explicit_alignment_index_never_mixes_with_the_managed_chr21_reference(
        prepare, tmp_path, parameter, aligner, source):
    values = {parameter: 'https://example.org/custom-index.tar.gz', 'aligner': aligner}
    params_file = tmp_path / 'params.json'
    params_file.write_text(json.dumps(values))
    result, params = prepare(cli_overrides=values if source == 'cli' else {},
                             params_file=params_file if source == 'file' else None)
    assert params[parameter] == values[parameter]
    assert result.generated_samplesheet is None
    assert not {'fasta', 'gff', 'krakendb', 'kronadb'} & params.keys()


def test_managed_hgtseq_sheet_is_an_explicit_fixture_not_a_remote_rescan():
    sheet = demo_defaults.samplesheet('hgtseq', PIN)
    assert sheet.files == ()
    assert sheet.record['kind'] == 'bundled_demo_fixture'
    assert sheet.record['data_commit'] == DATA
    assert sheet.record['samples'] == 3
    assert len(list(csv.DictReader(io.StringIO(sheet.text)))) == 3
    assert demo_defaults.samplesheet('hgtseq', '0' * 40) is None
    assert demo_defaults.samplesheet('another', PIN) is None
