"""Independent scientific expectations must detect omissions and changed analytical content."""
import hashlib
import json

import pytest

from runner import cli


def contract(tmp_path, artifacts, **extra):
    path = tmp_path / 'contract.json'
    path.write_text(json.dumps({'version': 1, 'name': 'known answer',
                                'artifacts': artifacts, **extra}))
    return path


def table(path='counts.tsv', **extra):
    return {'path': path, 'format': 'table', 'delimiter': '\t', 'key': ['gene'],
            'columns': ['gene', 'sample_A', 'sample_B'],
            'numeric': ['sample_A', 'sample_B'],
            'sample_columns': ['sample_A', 'sample_B'], **extra}


def run_dir(tmp_path, name, files, *, snapshot=True):
    root = tmp_path / name
    root.mkdir()
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    if snapshot:
        (root / 'provenance').mkdir(exist_ok=True)
        (root / 'provenance/outputs.sha256').write_text(''.join(
            f'{hashlib.sha256(text.encode()).hexdigest()}  {name}\n'
            for name, text in files.items()))
    return root


def assess(root, spec, against=None):
    from runner import scientific
    return scientific.assess(root, spec, against=against)


def test_exact_table_comparison_uses_keys_without_rounding_numbers(tmp_path):
    a = run_dir(tmp_path, 'a', {'counts.tsv':
        'gene\tsample_A\tsample_B\ng1\t12345678901234567890.123456789\t1e-100\n'
        'g2\t2\t3\n'})
    b = run_dir(tmp_path, 'b', {'counts.tsv':
        'gene\tsample_A\tsample_B\ng2\t2.0\t3e0\n'
        'g1\t12345678901234567890.123456789\t0.1e-99\n'})
    spec = contract(tmp_path, [table(expected_records=2)])
    result = assess(b, spec, a)
    assert result['passed']
    assert result['artifacts'][0]['replay']['records'] == 2
    (b / 'counts.tsv').write_text((b / 'counts.tsv').read_text().replace(
        '12345678901234567890.123456789', '12345678901234567890.123456788'))
    result = assess(b, spec, a)
    assert not result['passed']
    assert result['artifacts'][0]['comparison']['changed_records'] == 1


def test_each_required_matrix_checks_independent_sample_coverage(tmp_path):
    root = run_dir(tmp_path, 'a', {
        'first.tsv': 'gene\tsample_A\tsample_B\ng\t1\t2\n',
        'second.tsv': 'gene\tsample_A\ng\t1\n'})
    result = assess(root, contract(tmp_path, [table('first.tsv'), table('second.tsv')]))
    assert not result['passed']
    assert result['artifacts'][0]['passed']
    assert 'sample_B' in str(result['artifacts'][1]['issues'])


@pytest.mark.parametrize('body,issue', [
    ('gene\tsample_A\tsample_A\ng\t1\t2\n', 'duplicate'),
    ('gene\tsample_A\tsample_B\ng\t1\t2\ng\t3\t4\n', 'duplicate'),
    ('gene\tsample_A\tsample_B\ng\tNaN\t2\n', 'finite'),
    ('gene\tsample_A\tsample_B\ng\t1\n', 'columns')])
def test_malformed_tables_do_not_become_success(tmp_path, body, issue):
    result = assess(run_dir(tmp_path, 'a', {'counts.tsv': body}), contract(tmp_path, [table()]))
    assert not result['passed']
    assert issue in str(result['artifacts'][0]['issues'])


def test_table_sample_column_requires_exact_membership_per_artifact(tmp_path):
    root = run_dir(tmp_path, 'a', {'summary.tsv': 'sample\tvalue\nA\t1\n'})
    spec = contract(tmp_path, [{'path': 'summary.tsv', 'format': 'table', 'delimiter': '\t',
        'key': ['sample'], 'columns': ['sample', 'value'], 'numeric': ['value'],
        'sample_column': 'sample', 'expected_samples': ['A', 'B']}])
    result = assess(root, spec)
    assert not result['passed']
    assert 'B' in str(result['artifacts'][0]['issues'])


def test_tolerance_requires_a_reason_and_applies_only_to_named_numeric_columns(tmp_path):
    a = run_dir(tmp_path, 'a', {'counts.tsv': 'gene\tsample_A\tsample_B\ng\t1\t2\n'})
    b = run_dir(tmp_path, 'b', {'counts.tsv': 'gene\tsample_A\tsample_B\ng\t1.001\t2\n'})
    allowed = table(tolerances={'sample_A': {'absolute': '0.001', 'relative': '0',
                                           'reason': 'Known precision of this test fixture'}})
    assert assess(b, contract(tmp_path, [allowed]), a)['passed']
    (b / 'counts.tsv').write_text('gene\tsample_A\tsample_B\ng\t1.001\t2.0001\n')
    assert not assess(b, contract(tmp_path, [allowed]), a)['passed']
    allowed['tolerances']['sample_A'].pop('reason')
    from runner.errors import NfclawError
    with pytest.raises(NfclawError, match='reason'):
        assess(b, contract(tmp_path, [allowed]), a)


def test_tolerances_do_not_round_at_the_default_decimal_context(tmp_path):
    value = '123456789012345678901234567890.00000000000000000001'
    a = run_dir(tmp_path, 'a', {'counts.tsv': f'gene\tsample_A\tsample_B\ng\t{value}\t2\n'})
    b = run_dir(tmp_path, 'b', {'counts.tsv':
        'gene\tsample_A\tsample_B\ng\t123456789012345678901234567890.00000000000000000003\t2\n'})
    spec = contract(tmp_path, [table(tolerances={'sample_A': {
        'absolute': '0.00000000000000000001', 'reason': 'Exact boundary regression'}})])
    assert not assess(b, spec, a)['passed']


def test_mutated_original_cannot_become_a_false_scientific_reference(tmp_path):
    body = 'gene\tsample_A\tsample_B\ng\t1\t2\n'
    a = run_dir(tmp_path, 'a', {'counts.tsv': body})
    changed = body.replace('\t1\t', '\t3\t')
    (a / 'counts.tsv').write_text(changed)
    b = run_dir(tmp_path, 'b', {'counts.tsv': changed})
    result = assess(b, contract(tmp_path, [table()]), a)
    assert not result['passed']
    assert 'recorded' in str(result['artifacts'][0]['issues'])


def test_comparative_assessment_requires_recorded_original_hashes(tmp_path):
    body = 'gene\tsample_A\tsample_B\ng\t1\t2\n'
    a = run_dir(tmp_path, 'a', {'counts.tsv': body}, snapshot=False)
    b = run_dir(tmp_path, 'b', {'counts.tsv': body})
    assert not assess(b, contract(tmp_path, [table()]), a)['passed']


def test_fasta_detects_the_reported_lost_contig_and_records_assembly_metrics(tmp_path):
    a = run_dir(tmp_path, 'a', {'assembly.fa': '>one description\nACGT\nAC\n>two\nATG\n'})
    b = run_dir(tmp_path, 'b', {'assembly.fa': '>two\nATG\n>one description\nACGTAC\n'})
    spec = contract(tmp_path, [{'path': 'assembly.fa', 'format': 'fasta', 'expected_records': 2}])
    result = assess(b, spec, a)
    assert result['passed']
    assert result['artifacts'][0]['replay']['metrics'] == {'sequences': 2, 'total_bp': 9, 'n50': 6}
    (b / 'assembly.fa').write_text('>one description\nACGTAC\n')
    result = assess(b, spec, a)
    assert not result['passed']
    assert result['artifacts'][0]['comparison']['missing_records'] == 1


def test_duplicate_fasta_identifiers_are_refused(tmp_path):
    a = run_dir(tmp_path, 'a', {'assembly.fa': '>one\nAC\n>one\nGT\n'})
    result = assess(a, contract(tmp_path, [{'path': 'assembly.fa', 'format': 'fasta'}]))
    assert not result['passed']
    assert 'duplicate' in str(result['artifacts'][0]['issues'])


@pytest.mark.parametrize('relative', ['../outside.tsv', '/outside.tsv', 'provenance/params.json'])
def test_contracts_reject_paths_outside_scientific_results(tmp_path, relative):
    root = run_dir(tmp_path, 'a', {})
    from runner.errors import NfclawError
    with pytest.raises(NfclawError, match='path'):
        assess(root, contract(tmp_path, [table(relative)]))


def test_external_symlinks_cannot_supply_an_assessed_artifact(tmp_path):
    root = run_dir(tmp_path, 'a', {})
    (tmp_path / 'outside.tsv').write_text('gene\tsample_A\tsample_B\ng\t1\t2\n')
    (root / 'counts.tsv').symlink_to(tmp_path / 'outside.tsv')
    result = assess(root, contract(tmp_path, [table()]))
    assert not result['passed']


@pytest.mark.parametrize('extra', [{'typo': True}, {'version': 2}])
def test_contract_typoes_and_unknown_versions_are_refused(tmp_path, extra):
    from runner.errors import NfclawError
    with pytest.raises(NfclawError):
        assess(run_dir(tmp_path, 'a', {}), contract(tmp_path, [table()], **extra))


def test_cli_returns_machine_readable_result_and_failed_status(tmp_path, capsys):
    root = run_dir(tmp_path, 'a', {'counts.tsv': 'gene\tsample_A\tsample_B\ng\t1\t2\n'})
    spec = contract(tmp_path, [table(expected_records=2)])
    assert cli.main(['assess', str(root), '--contract', str(spec)]) == 1
    result = json.loads(capsys.readouterr().out)
    assert not result['passed']
    assert result['contract_sha256'] == hashlib.sha256(spec.read_bytes()).hexdigest()


def test_scratch_directory_inside_a_run_is_refused_before_writes(tmp_path, monkeypatch):
    import tempfile
    root = run_dir(tmp_path, 'a', {'counts.tsv': 'gene\tsample_A\tsample_B\ng\t1\t2\n'})
    monkeypatch.setattr(tempfile, 'tempdir', str(root))
    before = sorted(root.rglob('*'))
    from runner.errors import NfclawError
    with pytest.raises(NfclawError, match='temporary'):
        assess(root, contract(tmp_path, [table()]))
    assert sorted(root.rglob('*')) == before


def test_contract_pipeline_and_parameter_conditions_are_enforced(tmp_path):
    root = run_dir(tmp_path, 'a', {'counts.tsv': 'gene\tsample_A\tsample_B\ng\t1\t2\n'})
    (root / 'provenance/run_manifest.json').write_text(json.dumps({
        'pipeline': 'demo', 'commit': '1' * 40}))
    (root / 'provenance/params.json').write_text(json.dumps({'aligner': 'bwa'}))
    params = root / 'provenance/params.json'
    (root / 'provenance/configs.sha256').write_text(
        f'{hashlib.sha256(params.read_bytes()).hexdigest()}  {params}\n')
    spec = contract(tmp_path, [table()], pipeline={
        'name': 'demo', 'commit': '1' * 40, 'params': {'aligner': 'bwa'}})
    assert assess(root, spec)['passed']
    (root / 'provenance/params.json').write_text(json.dumps({'aligner': 'bowtie2'}))
    assert not assess(root, spec)['passed']


@pytest.mark.parametrize('expected,actual', [(0, False), (1, True), (False, 0)])
def test_pipeline_conditions_keep_json_booleans_distinct_from_numbers(tmp_path, expected, actual):
    root = run_dir(tmp_path, 'a', {'counts.tsv': 'gene\tsample_A\tsample_B\ng\t1\t2\n'})
    (root / 'provenance/run_manifest.json').write_text(json.dumps({
        'pipeline': 'demo', 'commit': '1' * 40}))
    params = root / 'provenance/params.json'
    params.write_text(json.dumps({'mode': actual}))
    (root / 'provenance/configs.sha256').write_text(
        f'{hashlib.sha256(params.read_bytes()).hexdigest()}  {params}\n')
    assert not assess(root, contract(tmp_path, [table()], pipeline={
        'name': 'demo', 'commit': '1' * 40, 'params': {'mode': expected}}))['passed']


def test_edited_params_cannot_turn_another_branch_into_a_matching_contract(tmp_path):
    root = run_dir(tmp_path, 'a', {'counts.tsv': 'gene\tsample_A\tsample_B\ng\t1\t2\n'})
    (root / 'provenance/run_manifest.json').write_text(json.dumps({
        'pipeline': 'demo', 'commit': '1' * 40}))
    params = root / 'provenance/params.json'
    params.write_text(json.dumps({'aligner': 'different'}))
    (root / 'provenance/configs.sha256').write_text(
        f'{hashlib.sha256(params.read_bytes()).hexdigest()}  {params}\n')
    params.write_text(json.dumps({'aligner': 'bwa'}))
    assert not assess(root, contract(tmp_path, [table()], pipeline={
        'name': 'demo', 'commit': '1' * 40, 'params': {'aligner': 'bwa'}}))['passed']


def test_oversized_run_manifest_is_reported_instead_of_parsed_truncated(tmp_path):
    root = run_dir(tmp_path, 'a', {'counts.tsv': 'gene\tsample_A\tsample_B\ng\t1\t2\n'})
    (root / 'provenance/run_manifest.json').write_text(json.dumps({
        'pipeline': 'demo', 'commit': '1' * 40, 'padding': 'x' * (1024 * 1024)}))
    params = root / 'provenance/params.json'
    params.write_text(json.dumps({'aligner': 'bwa'}))
    (root / 'provenance/configs.sha256').write_text(
        f'{hashlib.sha256(params.read_bytes()).hexdigest()}  {params}\n')
    result = assess(root, contract(tmp_path, [table()], pipeline={
        'name': 'demo', 'commit': '1' * 40, 'params': {'aligner': 'bwa'}}))
    assert not result['passed']
    assert any('run manifest exceeds 1 MiB' in issue for issue in result['issues'])


def test_cli_can_report_exact_json_numeric_tolerances(tmp_path, capsys):
    root = run_dir(tmp_path, 'a', {'counts.tsv': 'gene\tsample_A\tsample_B\ng\t1\t2\n'})
    path = contract(tmp_path, [table(tolerances={'sample_A': {
        'absolute': 0.001, 'reason': 'Declared test precision'}})])
    assert cli.main(['assess', str(root), '--contract', str(path)]) == 0
    assert json.loads(capsys.readouterr().out)['passed']


def test_checksum_unicode_separator_is_part_of_the_filename(tmp_path):
    from runner.replay_guard import checksum_text
    path = 'counts\u2028.tsv'
    body = 'gene\tsample_A\tsample_B\ng\t1\t2\n'
    a, b = run_dir(tmp_path, 'a', {path: body}), run_dir(tmp_path, 'b', {path: body})
    (a / 'provenance/outputs.sha256').write_text(checksum_text({
        path: hashlib.sha256(body.encode()).hexdigest()}))
    assert assess(b, contract(tmp_path, [table(path)]), a)['passed']


def test_explicit_dataframe_row_index_exclusion_does_not_hide_scientific_columns(tmp_path):
    a = run_dir(tmp_path, 'a', {'counts.tsv': '\tgene\tsample_A\tsample_B\n0\tg\t1\t2\n'})
    b = run_dir(tmp_path, 'b', {'counts.tsv': '\tgene\tsample_A\tsample_B\n3\tg\t1\t2\n'})
    item = table(columns=['', 'gene', 'sample_A', 'sample_B'],
                 ignore_columns={'': 'Pandas positional row index; gene is the stable key'})
    assert assess(b, contract(tmp_path, [item]), a)['passed']
    (b / 'counts.tsv').write_text('\tgene\tsample_A\tsample_B\n3\tg\t1\t3\n')
    assert not assess(b, contract(tmp_path, [item]), a)['passed']


def test_numeric_and_key_columns_cannot_be_excluded(tmp_path):
    from runner.errors import NfclawError
    root = run_dir(tmp_path, 'a', {})
    for name in ('gene', 'sample_A'):
        with pytest.raises(NfclawError):
            assess(root, contract(tmp_path, [table(ignore_columns={name: 'Hide changed data'})]))


def test_empty_fasta_placeholder_is_not_a_sequence(tmp_path):
    root = run_dir(tmp_path, 'a', {'assembly.fa': '>contig\n'})
    assert not assess(root, contract(tmp_path, [{'path': 'assembly.fa', 'format': 'fasta',
                                               'expected_records': 1}]))['passed']


def test_unassessed_directory_links_do_not_expose_external_filenames(tmp_path):
    root = run_dir(tmp_path, 'a', {'counts.tsv': 'gene\tsample_A\tsample_B\ng\t1\t2\n'})
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'private-external-name.txt').write_text('private bytes')
    (root / 'external').symlink_to(outside, target_is_directory=True)
    result = assess(root, contract(tmp_path, [table()]))
    assert result['passed']
    assert 'private-external-name' not in json.dumps(result)
    assert result['unassessed_files']['unexpanded_links'] == 1
