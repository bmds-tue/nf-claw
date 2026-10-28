"""Explicit reference preparation must conserve valid DRAMP records and refuse ambiguity."""
import csv
import hashlib
import json
import os

import pytest

from runner import cli
from runner.errors import NfclawError


COLUMNS = ['DRAMP_ID', 'Sequence', 'Name', 'Family', 'Source', 'Target_Organism',
           'Gene', 'Swiss_Prot_Entry', 'PDB_ID', 'Comments']


def raw_table(tmp_path, rows):
    path = tmp_path / 'raw.tsv'
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream, delimiter='\t')
        writer.writerow(COLUMNS)
        for identifier, sequence, note in rows:
            writer.writerow([identifier, sequence, 'name', 'family', 'source', 'target',
                             'gene', '', '', note])
    return path


def prepare(raw, out):
    from runner import dramp
    return dramp.prepare(raw, out)


def test_valid_sequences_and_all_annotations_are_conserved(tmp_path):
    raw = raw_table(tmp_path, [('DRAMP00001', 'ACDEFG', 'quoted\tannotation\nsecond line'),
                               ('DRAMP00002', '', 'missing'),
                               ('DRAMP00003', 'AX', 'noncanonical'),
                               ('DRAMP00004', 'NA', 'literal NA is a valid sequence'),
                               ('DRAMP00005', 'acde', 'case is never changed')])
    original = raw.read_bytes()
    out = tmp_path / 'amp_DRAMP_database'
    report = prepare(raw, out)
    assert raw.read_bytes() == original
    assert (out / 'general_amps.fasta').read_text() == '>DRAMP00001\nACDEFG\n>DRAMP00004\nNA\n'
    with (out / 'general_amps.txt').open(newline='') as stream:
        rows = list(csv.reader(stream, delimiter='\t'))
    assert rows[0] == COLUMNS
    assert [row[0] for row in rows[1:]] == ['DRAMP00001', 'DRAMP00004']
    assert rows[1][-1] == 'quoted\tannotation\nsecond line'
    assert rows[2][-1] == 'literal NA is a valid sequence'
    assert report['rows'] == {'read': 5, 'retained': 2, 'excluded': 3}
    assert report['exclusions']['counts'] == {'missing_sequence': 1, 'noncanonical_sequence': 2}
    assert report['input']['sha256'] == hashlib.sha256(original).hexdigest()
    assert json.loads((out / 'preparation.json').read_text()) == report
    for name, digest in report['outputs'].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
    assert out.stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in out.iterdir())


@pytest.mark.parametrize('rows,issue', [
    ([('DRAMP1', 'AC', ''), ('DRAMP1', 'DE', '')], 'duplicate'),
    ([('DRAMP1', '', ''), ('DRAMP2', 'AX', '')], 'retained'),
    ([('unsafe id', 'AC', '')], 'identifier'),
    ([('DRAMP1', 'AC', 'nul\x00byte')], 'NUL')])
def test_invalid_reference_never_leaves_a_database(tmp_path, rows, issue):
    raw = raw_table(tmp_path, rows)
    out = tmp_path / 'amp_DRAMP_database'
    with pytest.raises(NfclawError, match=issue):
        prepare(raw, out)
    assert not out.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ['raw.tsv']


@pytest.mark.parametrize('body,issue', [
    ('DRAMP_ID\tSequence\nDRAMP1\tAC\n', 'columns'),
    ('DRAMP_ID\tSequence\tSequence\nDRAMP1\tAC\tDE\n', 'duplicate'),
    ('\n', 'header')])
def test_missing_or_duplicate_headers_are_refused(tmp_path, body, issue):
    raw = tmp_path / 'raw.tsv'
    raw.write_text(body)
    with pytest.raises(NfclawError, match=issue):
        prepare(raw, tmp_path / 'amp_DRAMP_database')


def test_existing_database_and_symlink_are_untouched(tmp_path):
    raw = raw_table(tmp_path, [('DRAMP1', 'AC', '')])
    out = tmp_path / 'amp_DRAMP_database'
    out.mkdir()
    sentinel = out / 'sentinel'
    sentinel.write_text('keep')
    with pytest.raises(NfclawError, match='exists'):
        prepare(raw, out)
    alias = tmp_path / 'alias_DRAMP'
    alias.symlink_to(out, target_is_directory=True)
    with pytest.raises(NfclawError, match='exists'):
        prepare(raw, alias)
    assert sentinel.read_text() == 'keep'
    assert sorted(p.name for p in out.iterdir()) == ['sentinel']


def test_consumer_requires_dramp_in_directory_name(tmp_path):
    raw = raw_table(tmp_path, [('DRAMP1', 'AC', '')])
    with pytest.raises(NfclawError, match='DRAMP'):
        prepare(raw, tmp_path / 'reference')


def test_cli_prepares_reference_without_repository_lookup(tmp_path, monkeypatch, capsys):
    raw = raw_table(tmp_path, [('DRAMP1', 'AC', '')])
    monkeypatch.setattr(cli, '_repo_root', lambda: pytest.fail('preparation is standalone'))
    out = tmp_path / 'amp_DRAMP_database'
    assert cli.main(['prepare-dramp', str(raw), '--outdir', str(out)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['rows']['retained'] == 1
    assert (out / 'general_amps.fasta').is_file()


def test_cli_reference_error_is_actionable_without_traceback(tmp_path, capsys):
    assert cli.main(['prepare-dramp', str(tmp_path / 'missing.tsv'), '--outdir',
                     str(tmp_path / 'amp_DRAMP_database')]) == 1
    result = capsys.readouterr()
    assert 'missing.tsv' in result.err
    assert 'Traceback' not in result.err


def test_malformed_row_cannot_be_silently_dropped(tmp_path):
    raw = raw_table(tmp_path, [('DRAMP1', 'AC', '')])
    with raw.open('a') as stream:
        stream.write('DRAMP2\tDE\n')
    with pytest.raises(NfclawError, match='columns'):
        prepare(raw, tmp_path / 'amp_DRAMP_database')


def test_changed_source_is_refused_before_publication(tmp_path, monkeypatch):
    raw = raw_table(tmp_path, [('DRAMP1', 'AC', '')])
    original_reader = csv.reader

    def changing_reader(*args, **kwargs):
        for number, row in enumerate(original_reader(*args, **kwargs)):
            if number == 1:
                with raw.open('a') as stream:
                    stream.write('DRAMP2\tDE\tname\tfamily\tsource\ttarget\tgene\t\t\tnew\n')
            yield row

    monkeypatch.setattr(csv, 'reader', changing_reader)
    with pytest.raises(NfclawError, match='changed'):
        prepare(raw, tmp_path / 'amp_DRAMP_database')
    assert not (tmp_path / 'amp_DRAMP_database').exists()


def test_replaced_destination_cannot_receive_reference_files(tmp_path, monkeypatch):
    raw = raw_table(tmp_path, [('DRAMP1', 'AC', '')])
    out = tmp_path / 'amp_DRAMP_database'
    displaced = tmp_path / 'displaced_DRAMP_database'
    victim = tmp_path / 'existing'
    victim.mkdir()
    (victim / 'sentinel').write_text('keep')
    original_link = os.link
    replaced = False

    def replace_then_link(*args, **kwargs):
        nonlocal replaced
        if not replaced:
            replaced = True
            out.rename(displaced)
            out.symlink_to(victim, target_is_directory=True)
        return original_link(*args, **kwargs)

    monkeypatch.setattr(os, 'link', replace_then_link)
    with pytest.raises(NfclawError, match='changed'):
        prepare(raw, out)
    assert sorted(path.name for path in victim.iterdir()) == ['sentinel']
    assert (victim / 'sentinel').read_text() == 'keep'
    assert list(displaced.iterdir()) == []


def test_missing_identifier_is_excluded_and_never_invented(tmp_path):
    raw = raw_table(tmp_path, [('', 'AC', 'unknown identity'), ('DRAMP2', 'DE', 'known')])
    out = tmp_path / 'amp_DRAMP_database'
    report = prepare(raw, out)
    assert (out / 'general_amps.fasta').read_text() == '>DRAMP2\nDE\n'
    assert report['rows'] == {'read': 2, 'retained': 1, 'excluded': 1}
    assert report['exclusions']['counts'] == {'missing_identifier': 1}
