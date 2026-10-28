"""Bactmap's test defaults and preview completion must remain independently replayable."""
import json
import shlex
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from runner import demo_defaults, orchestration, replay_guard, source_corrections, submodule
from runner.errors import NfclawError
from runner.submodule import SubmoduleStatus

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / 'fixtures/source_corrections'
COMMIT = '834642d8ac150ca10d705833223e7bcf15efc210'
DATA = '02195cfa96ca496173e9d63dd58e34bf02fcf55a'
BASE = f'https://raw.githubusercontent.com/nf-core/test-datasets/{DATA}/'
TARGETS = {'conf/test.config': 'bactmap-test.config',
           'lib/NfcoreTemplate.groovy': 'bactmap-NfcoreTemplate.groovy',
           'modules/local/alignpseudogenomes.nf': 'bactmap-alignpseudogenomes.nf'}


def original(tmp_path):
    root = tmp_path / 'original'
    for target, fixture in {**TARGETS, 'conf/modules.config': 'bactmap-modules.config'}.items():
        path = root / target
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURES / fixture, path)
    return SubmoduleStatus('bactmap', root, True, True, '1.0.0', COMMIT, ())


def test_all_corrections_are_one_atomic_recorded_source(tmp_path):
    st = original(tmp_path)
    before = replay_guard.hash_pipeline(st.path)
    planned = source_corrections.plan(st)
    assert set(planned.patched_files) == set(TARGETS)
    working = source_corrections.materialize(planned, tmp_path / 'derived')
    assert {entry['path'] for entry in working.metadata['changes']} == set(TARGETS)
    config = (working.path / 'conf/test.config').read_text()
    assert '    modules {' not in config
    assert 'params.modules.bcftools_filter.args =' in config
    assert 'params.modules.alignpseudogenomes.non_GATC_threshold = 0.8' in config
    assert "params.modules.raxmlng.args += ' --seed 23032021'" in config
    assert "params.modules.iqtree.args += ' --seed 23032021'" in config
    alignment = (working.path / 'modules/local/alignpseudogenomes.nf').read_text()
    assert '${ordered_pseudogenomes}' in alignment
    assert 'new nextflow.util.BlankSeparatedList(' in alignment
    assert '.sort(false) { it.name }' in alignment
    assert (working.path / 'conf/modules.config').read_bytes() == (
        FIXTURES / 'bactmap-modules.config').read_bytes()
    source_corrections.verify(working)
    assert replay_guard.hash_pipeline(st.path) == before
    assert source_corrections.plan(replace(st, commit='0' * 40)) is None


@pytest.mark.parametrize('target', TARGETS)
@pytest.mark.parametrize('change', ['bytes', 'missing'])
def test_either_invalid_target_refuses_the_whole_recipe(tmp_path, target, change):
    st = original(tmp_path)
    path = st.path / target
    if change == 'missing':
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b'// changed\n')
    with pytest.raises(NfclawError, match='(?i)(source|checksum)'):
        source_corrections.plan(st)
    assert not (tmp_path / 'derived').exists()


def test_additional_file_changes_bind_recipe_identity_without_rekeying_old_runs():
    expected = {'createtaxdb': 'd895ea1e9e13c28f90e36d82aee6e5f8d3fc236ee5d07bb872b7ab3ce364cc5f',
                'funcscan': '1504e0b09e4dec88b9cfa2cadbc4d972b47d09fcb0ae6d2058360587415c9800'}
    for recipe in source_corrections._RECIPES:
        if recipe.pipeline in expected:
            assert recipe.identity()['fingerprint'] == expected[recipe.pipeline]
    recipe = next(r for r in source_corrections._RECIPES if r.pipeline == 'bactmap')
    patch = recipe.additional_files[0]
    modified = replace(patch, edits=patch.edits + ((b'old', b'new'),))
    assert replace(recipe, additional_files=(modified,)).identity() != recipe.identity()


def test_duplicate_patch_paths_are_refused_before_copying(tmp_path, monkeypatch):
    st = original(tmp_path)
    recipe = next(r for r in source_corrections._RECIPES if r.pipeline == 'bactmap')
    patch = replace(recipe.additional_files[0], path=recipe.path)
    monkeypatch.setattr(source_corrections, '_RECIPES',
                        (replace(recipe, additional_files=(patch,)),))
    with pytest.raises(NfclawError, match='(?i)(duplicate|ambiguous)'):
        source_corrections.plan(st)


@pytest.mark.parametrize('target', TARGETS)
def test_second_file_is_checked_on_resume_and_cache_reuse(tmp_path, target):
    st = original(tmp_path)
    planned = source_corrections.plan(st)
    working = source_corrections.materialize(planned, tmp_path / 'derived')
    out = tmp_path / 'out'
    source_corrections.write_record(working, out / 'provenance')
    assert source_corrections.resume_source(out, planned) == working
    path = working.path / target
    path.write_bytes(path.read_bytes() + b'// changed\n')
    with pytest.raises(NfclawError):
        source_corrections.resume_source(out, planned)
    with pytest.raises(NfclawError):
        source_corrections.materialize(planned, working.path)


def test_demo_sheet_and_reference_use_the_same_immutable_dataset():
    assert demo_defaults.parameters('bactmap', COMMIT) == {
        'reference': BASE + 'genome/NCTC13799.fna', 'max_cpus': 1}
    sheet = demo_defaults.samplesheet('bactmap', COMMIT)
    assert sheet.header == ('sample', 'fastq_1', 'fastq_2')
    assert sheet.files == ()
    assert sheet.record['data_commit'] == DATA
    assert sheet.record['pipeline_commit'] == COMMIT
    assert sheet.record['rows'] == sheet.record['paired_end'] == 3
    assert [r['sample'] for r in sheet.rows] == ['ERR2172265', 'ERR2172266', 'ERR2172267']
    for row in sheet.rows:
        for mate in (1, 2):
            assert row[f'fastq_{mate}'] == BASE + f'illumina/{row["sample"]}_{mate}.fastq.gz'
    assert demo_defaults.samplesheet('bactmap', '0' * 40) is None


@pytest.mark.parametrize('selector', ['input', 'reference'])
def test_explicit_data_selectors_disable_the_entire_fixture(selector):
    assert demo_defaults.parameters('bactmap', COMMIT, provided=frozenset({selector})) == {}


@pytest.mark.parametrize('override', ['none', 'cpus', 'input', 'reference', 'null_reference',
                                     'config', 'profile', 'non_demo'])
def test_bare_demo_eligibility_and_parameter_precedence(tmp_path, monkeypatch, override):
    source = ROOT / 'pipelines/bactmap/upstream'
    if not (source / 'nextflow_schema.json').is_file():
        pytest.skip('requires audited bactmap source')
    st = submodule.resolve('bactmap', ROOT / 'pipelines')
    assert st.commit is not None, 'audited Bactmap checkout has no concrete source revision'
    if st.commit != COMMIT:
        pytest.skip('bactmap is no longer pinned at the audited commit 834642d8ac15')
    monkeypatch.setattr(orchestration.preflight, 'check_environment', lambda **kw: [])
    cli = {'fasttree': False}
    if override == 'cpus':
        cli['max_cpus'] = 2
    if override in ('reference', 'input'):
        suffix = 'fna' if override == 'reference' else 'csv'
        cli[override] = 'https://example.org/custom.' + suffix
    params_file = None
    if override == 'null_reference':
        params_file = tmp_path / 'null.json'
        params_file.write_text('{"reference":null}')
    config = tmp_path / 'custom.config'
    config.write_text('params.fasttree = false\n')
    kwargs = dict(
        repo_root=ROOT, input_path=None, outdir=tmp_path / 'out',
        profile='custom,docker' if override == 'profile' else 'docker', params_file=params_file,
        cli_overrides=cli, resume=False, demo=override != 'non_demo', check_only=True,
        write_provenance=False, timeout_seconds=60,
        configs=[str(config)] if override == 'config' else [])
    if override == 'non_demo':
        with pytest.raises(NfclawError, match='Parameters failed validation') as exc:
            orchestration.run_pipeline('bactmap', **kwargs)
        assert any('--reference' in issue for issue in exc.value.details['issues'])
        assert any('--input' in issue for issue in exc.value.details['issues'])
        return
    result = orchestration.run_pipeline('bactmap', **kwargs)
    try:
        cmd = shlex.split(result.command)
        params = json.loads(Path(cmd[cmd.index('-params-file') + 1]).read_text())
        assert params['fasttree'] is False
        assert (result.generated_samplesheet is not None) == (override in {'none', 'cpus'})
        if override in {'none', 'cpus'}:
            assert params['reference'] == BASE + 'genome/NCTC13799.fna'
            assert params['max_cpus'] == (2 if override == 'cpus' else 1)
        elif override in ('input', 'reference'):
            assert params[override] == cli[override]
        elif override == 'null_reference':
            assert params['reference'] is None
        if override not in {'none', 'cpus'}:
            assert 'max_cpus' not in params
        assert Path(cmd[cmd.index('run') + 1]) != source
        assert not result.outdir.exists()
    finally:
        if result.staging:
            shutil.rmtree(result.staging)


def test_original_source_change_in_second_file_cannot_be_adopted(tmp_path):
    st = original(tmp_path)
    planned = source_corrections.plan(st)
    (st.path / 'lib/NfcoreTemplate.groovy').write_text('// new source\n')
    with pytest.raises(NfclawError):
        source_corrections.materialize(planned, tmp_path / 'derived')
    assert not (tmp_path / 'derived').exists()


@pytest.mark.parametrize('change', ['changed', 'missing', 'other_release'])
def test_bundled_contract_requires_its_exact_legacy_consumer(tmp_path, change):
    path = tmp_path / 'bin/check_samplesheet.py'
    path.parent.mkdir()
    if change != 'missing':
        shutil.copyfile(FIXTURES / 'bactmap-check_samplesheet.py.txt', path)
    if change == 'changed':
        path.write_bytes(path.read_bytes() + b'\n')
    if change == 'other_release':
        assert demo_defaults.fixture_schema('bactmap', '0' * 40, tmp_path) is None
    else:
        with pytest.raises(NfclawError, match='consumer'):
            demo_defaults.fixture_schema('bactmap', COMMIT, tmp_path)
