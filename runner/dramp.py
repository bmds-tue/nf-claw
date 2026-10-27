"""Explicit, recorded DRAMP reference preparation for AMPcombi 3.0.0.

This prepares annotations and FASTA only. Build MMseqs indexes separately before analysis.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import stat
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from runner.errors import ErrorCode, NfclawError

_COLUMNS = {'DRAMP_ID', 'Sequence', 'Name', 'Family', 'Source', 'Target_Organism',
            'Gene', 'Swiss_Prot_Entry', 'PDB_ID'}
_AMINO_ACIDS = re.compile(r'[ACDEFGHIKLMNPQRSTVWY]+')
_IDENTIFIER = re.compile(r'DRAMP[0-9]+')


def _invalid(message: str) -> NfclawError:
    return NfclawError(ErrorCode.PARAMS_INVALID, message)


def _sha(stream) -> str:
    digest = hashlib.sha256()
    stream.seek(0)
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(block)
    stream.seek(0)
    return digest.hexdigest()


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _filter(stream, stage: Path) -> tuple[dict, dict]:
    reader = csv.reader(stream, delimiter='\t', strict=True)
    header = next(reader, None)
    if not header or any(not name for name in header):
        raise _invalid('DRAMP table needs a nonempty header.')
    if len(set(header)) != len(header):
        raise _invalid('DRAMP table has duplicate header columns.')
    if not _COLUMNS <= set(header):
        raise _invalid(f'DRAMP annotation columns are missing: {sorted(_COLUMNS - set(header))}')
    id_column, seq_column = header.index('DRAMP_ID'), header.index('Sequence')
    rows = {'read': 0, 'retained': 0, 'excluded': 0}
    exclusions: Counter = Counter()
    examples = []
    seen = set()
    with (stage / 'general_amps.txt').open('w', encoding='utf-8', newline='') as table, \
            (stage / 'general_amps.fasta').open('w', encoding='utf-8', newline='') as fasta:
        writer = csv.writer(table, delimiter='\t', lineterminator='\n')
        writer.writerow(header)
        for row in reader:
            rows['read'] += 1
            if len(row) != len(header):
                raise _invalid(f'DRAMP record {rows["read"]} has the wrong number of columns.')
            if any('\x00' in value for value in row):
                raise _invalid(f'DRAMP record {rows["read"]} contains NUL bytes.')
            identifier, sequence = row[id_column], row[seq_column]
            if identifier and not _IDENTIFIER.fullmatch(identifier):
                raise _invalid(f'DRAMP record {rows["read"]} has an unsafe DRAMP identifier.')
            if identifier and identifier in seen:
                raise _invalid(f'DRAMP table has a duplicate identifier: {identifier}')
            seen.add(identifier)
            reason = ('missing_identifier' if not identifier else 'missing_sequence'
                      if not sequence else 'noncanonical_sequence'
                      if not _AMINO_ACIDS.fullmatch(sequence) else None)
            if reason:
                rows['excluded'] += 1
                exclusions[reason] += 1
                if len(examples) < 10:
                    examples.append({'id': identifier, 'reason': reason})
                continue
            writer.writerow(row)
            fasta.write(f'>{identifier}\n{sequence}\n')
            rows['retained'] += 1
    if not rows['retained']:
        raise _invalid('DRAMP table has no retained canonical peptide sequences.')
    return rows, {'counts': dict(exclusions), 'examples': examples,
                  'examples_truncated': rows['excluded'] > len(examples)}


def _publish(stage: Path, outdir: Path) -> None:
    # Exclusive creation prevents replacing even an empty pre-existing database. Hard links
    # publish only our validated files, with no overwrite if an entry appears concurrently.
    outdir.mkdir(mode=0o700)
    fd = os.open(outdir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    identity = os.fstat(fd)
    linked = []
    try:
        for path in sorted(stage.iterdir()):
            path.chmod(0o600)
            os.link(path, path.name, dst_dir_fd=fd, follow_symlinks=False)
            linked.append(path)
        if not os.path.samestat(identity, outdir.lstat()):
            raise _invalid(f'DRAMP output directory changed during publication: {outdir}')
    except BaseException:
        for source in linked:
            try:
                target = os.stat(source.name, dir_fd=fd, follow_symlinks=False)
                if os.path.samestat(source.stat(), target):
                    os.unlink(source.name, dir_fd=fd)
            except FileNotFoundError:
                pass
        try:
            if os.path.samestat(identity, outdir.lstat()):
                outdir.rmdir()
        except OSError:
            pass
        raise
    finally:
        os.close(fd)


def prepare(raw: Path, outdir: Path) -> dict:
    """Filter a local DRAMP TSV into a fresh private, checksummed reference directory."""
    raw, outdir = Path(raw).expanduser(), Path(outdir).expanduser()
    try:
        if os.path.lexists(outdir):
            raise _invalid(f'DRAMP output already exists: {outdir}')
        outdir = outdir.parent.resolve(strict=True) / outdir.name
        if 'DRAMP' not in outdir.name:
            raise _invalid('The reference directory name must contain DRAMP for AMPcombi 3.')
        raw = raw.resolve(strict=True)
        fd = os.open(raw, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as binary, \
                tempfile.TemporaryDirectory(prefix='.nfclaw-dramp-', dir=outdir.parent) as temp:
            before = os.fstat(binary.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise _invalid(f'DRAMP input is not a regular file: {raw}')
            original_sha = _sha(binary)
            stage = Path(temp)
            text = io.TextIOWrapper(binary, encoding='utf-8-sig', newline='')
            try:
                rows, exclusions = _filter(text, stage)
            finally:
                text.detach()
            if (_sha(binary) != original_sha or
                    _identity(os.fstat(binary.fileno())) != _identity(before) or
                    _identity(raw.stat()) != _identity(before)):
                raise _invalid(f'DRAMP input changed during preparation: {raw}')
            outputs = {}
            for path in sorted(stage.iterdir()):
                with path.open('rb') as stream:
                    outputs[path.name] = _sha(stream)
            report = {
                'version': 1, 'created_at': datetime.now(UTC).isoformat(),
                'consumer': 'AMPcombi 3.0.0',
                'policy': {'id': 'identified-uppercase-canonical-20-v1',
                           'description': 'Retain nonempty uppercase ACDEFGHIKLMNPQRSTVWY '
                                          'sequences with a DRAMP identifier verbatim; preserve '
                                          'all retained annotations. Exclude missing identifiers. '
                                          'Other peptides may be biologically valid.'},
                'input': {'path': str(raw), 'bytes': before.st_size, 'sha256': original_sha},
                'outdir': str(outdir), 'rows': rows, 'exclusions': exclusions,
                'outputs': outputs,
                'index': {'status': 'not_built',
                          'required': 'Build mmseqs2/ref_DB before supplying this directory '
                                      'to Funcscan --amp_ampcombi_db.'}}
            (stage / 'preparation.json').write_text(json.dumps(report, indent=2) + '\n',
                                                    encoding='utf-8')
            _publish(stage, outdir)
            return report
    except (OSError, UnicodeError, csv.Error, ValueError, RuntimeError) as exc:
        raise _invalid(f'Cannot prepare DRAMP reference from {raw}: {exc}') from exc
