"""Demo sheets from moving test-data branches are staged from immutable commits instead.

Nextflow reads such a sheet only to validate it, so its consumed bytes were never recorded and a
strict replay check could not establish them. A bundled, recorded sheet can be.
"""
import csv
import json
import re
from pathlib import Path

import pytest

from runner import demo_defaults, orchestration, submodule

ROOT = Path(__file__).resolve().parent.parent
CASES = {
    'bamtofastq': ('8a295860c0c9221337dec7f2620709a47cea254d', '2.2.1',
                   'e228f0e5412ed0bed20e7a99e1588cbf95f65102', 'sample_id', ['test', 'test2'],
                   {'fasta'}),
    'funcscan': ('aee3dc965eb0c77267435544dda30da858763913', '4.0.0',
                 '6612875ff5d8d54fd0a7532acbfb9dda25edb9b2', 'sample', ['sample_1', 'sample_2'],
                 {'amp_hmmsearch_models'}),
    'createtaxdb': ('b01a0f8ed96a5990d15470828dfa92a22cf08bba', '3.1.0',
                    '9248a89ada220333b7bc3c7c07af5eb229c16d5b', 'id',
                    ['Human_Mitochondrial_genome', 'SARS-CoV-2_genome',
                     'Bacteroides_fragilis_genome', 'Candidatus_portiera_aleyrodidarum_genome',
                     'Haemophilus_influenzae_genome', 'Streptococcus_agalactiae_genome'],
                    {'accession2taxid', 'nucl2taxid', 'prot2taxid', 'nodesdmp', 'namesdmp'}),
}
MOVING = ('/bamtofastq/', '/funcscan/', '/createtaxdb/', 'refs/heads', 'github.com/')


def _urls(rows):
    return [value for row in rows for value in row.values() if value.startswith('http')]


@pytest.mark.parametrize('name', sorted(CASES))
def test_fixture_sheets_name_only_immutable_data(name):
    pin, _, data, id_column, samples, _ = CASES[name]
    sheet = demo_defaults.samplesheet(name, pin)
    assert sheet.id_column == id_column
    assert [row[id_column] for row in sheet.rows] == samples
    assert sheet.record['data_commit'] == data
    sheet_urls = _urls(sheet.rows)
    assert sheet_urls and all(f'/{data}/' in url for url in sheet_urls)
    # Parameter defaults may come from another immutable commit (bamtofastq's reference).
    urls = sheet_urls + list(demo_defaults.parameters(name, pin).values())
    assert all(re.search(r'/[0-9a-f]{40}/', url) and not any(m in url for m in MOVING)
               for url in urls)
    assert demo_defaults.samplesheet(name, '0' * 40) is None   # other releases keep their own


@pytest.fixture
def prepare(tmp_path, monkeypatch):
    def check(name, **kwargs):
        pin, version = CASES[name][:2]
        if (not (ROOT / f'pipelines/{name}/upstream/nextflow_schema.json').is_file()
                or submodule.resolve(name, ROOT / 'pipelines').commit != pin):
            pytest.skip(f'requires the audited {name} {version} source')
        monkeypatch.setattr(orchestration.preflight, 'check_environment', lambda **kw: [])
        options = dict(repo_root=ROOT, input_path=None, outdir=tmp_path / 'out', profile='docker',
                       params_file=None, cli_overrides={}, resume=False, demo=True,
                       check_only=True, write_provenance=False, timeout_seconds=30)
        options.update(kwargs)
        result = orchestration.run_pipeline(name, **options)
        return result, json.loads((result.staging / 'params.json').read_text())
    return check


@pytest.mark.parametrize('name', sorted(CASES))
def test_bare_demo_stages_the_validated_immutable_sheet(prepare, name):
    _, _, data, id_column, samples, pinned = CASES[name]
    result, params = prepare(name)
    path = result.generated_samplesheet
    assert path is not None and params['input'] == str(path)
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    assert [row[id_column] for row in rows] == samples
    assert all(f'/{data}/' in url for url in _urls(rows))
    assert pinned <= params.keys()
    assert result.validation_scope['local_samplesheets'] == 1
    assert not result.outdir.exists()


@pytest.mark.parametrize('name,override', [
    ('bamtofastq', 'input'), ('funcscan', 'input'), ('funcscan', 'amp_hmmsearch_models'),
    ('createtaxdb', 'input'), ('createtaxdb', 'nodesdmp'), ('createtaxdb', 'malt_mapdb'),
])
def test_explicit_data_selectors_disable_the_fixture(prepare, name, override):
    value = f'https://example.org/user-{override}.csv'
    if override == 'input':
        result, params = prepare(name, input_path=value)
        assert params['input'] == value
    else:
        result, params = prepare(name, cli_overrides={override: value})
        assert params[override] == value and 'input' not in params
    assert result.generated_samplesheet is None
    assert not (CASES[name][5] - {override}) & params.keys()


@pytest.mark.parametrize('name', sorted(CASES))
def test_extra_profiles_keep_the_release_demo(prepare, name):
    result, params = prepare(name, profile='docker,arm')
    assert result.generated_samplesheet is None and 'input' not in params


def test_explicit_bamtofastq_reference_still_gets_the_immutable_sheet(prepare):
    # A user reference replaces only the reference default (the chain specs pass one).
    result, params = prepare('bamtofastq', cli_overrides={'fasta': 'https://example.org/ref.fa'})
    assert params['fasta'] == 'https://example.org/ref.fa'
    assert result.generated_samplesheet is not None
