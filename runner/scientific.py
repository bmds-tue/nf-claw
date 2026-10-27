"""Explicit, limited scientific output contracts; never infer completeness from exit status.

Comparisons are about declared data, not biological accuracy. The original's selected bytes must
still match its recorded output checksums. SQLite keeps keyed comparisons off the Python heap.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import stat
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path

from runner import outputs
from runner.errors import ErrorCode, NfclawError
from runner.parameters import _json_equal
from runner.replay_guard import parse_checksums

VERSION = 1
_EXAMPLES = 20
_COMMON = {'path', 'format', 'min_records', 'expected_records', 'coordinates'}
_TABLE = {'delimiter', 'key', 'columns', 'numeric', 'tolerances', 'sample_columns',
          'sample_column', 'expected_samples', 'ignore_columns'}
_HTS = {'expected_samples', 'ignore_header_fields', 'field_encodings'}
_H5AD = {'matrix', 'expected_cells', 'expected_genes', 'axis_policy', 'integer', 'nonnegative'}


def _bad(message):
    return NfclawError(ErrorCode.PARAMS_INVALID, f'scientific contract: {message}')


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key {key!r}')
        result[key] = value
    return result


def _json(data):
    def constant(token):
        raise ValueError(f'non-finite JSON number {token}')
    return json.loads(data, parse_float=Decimal, object_pairs_hook=_object,
                      parse_constant=constant)


def _fields(obj, allowed, where):
    if not isinstance(obj, dict):
        raise _bad(f'{where} must be an object')
    if unknown := obj.keys() - allowed:
        raise _bad(f'unknown {where} fields: {sorted(unknown)}')


def _strings(value, where, *, empty=False, blank=False):
    if (not isinstance(value, list) or not empty and not value
            or any(not isinstance(x, str) or not blank and not x or '\x00' in x for x in value)
            or len(set(value)) != len(value)):
        raise _bad(f'{where} must be a list of unique nonempty strings')
    return value


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError('numeric values must be finite decimal numbers')
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f'not a finite decimal: {value!r}') from exc
    if not number.is_finite():
        raise ValueError(f'not a finite decimal: {value!r}')
    # An exponent such as 1e999999999 must not allocate unbounded rational integers.
    if abs(number.as_tuple().exponent) > 10000 or abs(number.adjusted()) > 10000:
        raise ValueError('decimal exponent exceeds the supported +/-10000 range')
    return Fraction(number)


def _relative(value):
    if (not isinstance(value, str) or not value or '\x00' in value or '\\' in value
            or value.startswith('/') or any(p in ('', '.', '..') for p in value.split('/'))
            or value.split('/')[0] in {'provenance', '.nextflow', 'work'}
            or value.startswith('.nextflow.log')):
        raise _bad(f'artifact path must name a relative scientific result: {value!r}')


def load_contract(path: Path):
    try:
        with Path(path).open('rb') as stream:
            data = stream.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024:
            raise ValueError('contract exceeds 1 MiB')
        spec = _json(data)
    except (OSError, ValueError) as exc:
        raise _bad(f'cannot read {path}: {exc}') from exc
    _fields(spec, {'version', 'name', 'pipeline', 'artifacts'}, 'contract')
    if type(spec.get('version')) is not int or spec['version'] != VERSION:
        raise _bad('unsupported version; expected 1')
    if not isinstance(spec.get('name'), str) or not spec['name'].strip():
        raise _bad('name is required')
    if 'pipeline' in spec:
        binding = spec['pipeline']
        _fields(binding, {'name', 'commit', 'params'}, 'pipeline binding')
        if (not isinstance(binding.get('name'), str) or not binding['name']
                or not isinstance(binding.get('commit'), str)
                or re.fullmatch('[0-9a-f]{40}', binding['commit']) is None
                or not isinstance(binding.get('params', {}), dict)):
            raise _bad('pipeline binding needs a name, exact commit and parameter object')
    artifacts = spec.get('artifacts')
    if not isinstance(artifacts, list) or not artifacts:
        raise _bad('at least one artifact is required')
    paths = set()
    for item in artifacts:
        if not isinstance(item, dict):
            raise _bad('each artifact must be an object')
        kind = item.get('format')
        if kind not in ('table', 'fasta', 'bam', 'vcf', 'h5ad_matrix'):
            raise _bad(f'unsupported artifact format {kind!r}')
        extra = (_TABLE if kind == 'table' else _HTS if kind in ('bam', 'vcf')
                 else _H5AD if kind == 'h5ad_matrix' else set())
        _fields(item, _COMMON | extra, 'artifact')
        _relative(item.get('path'))
        if item['path'] in paths:
            raise _bad(f'duplicate artifact path: {item["path"]}')
        paths.add(item['path'])
        for key in ('min_records', 'expected_records'):
            if key in item and (type(item[key]) is not int or item[key] < 0):
                raise _bad(f'{key} must be a nonnegative integer')
        if 'coordinates' in item and (not isinstance(item['coordinates'], str)
                                      or not item['coordinates'].strip()):
            raise _bad('coordinates must explicitly describe the coordinate convention')
        if kind == 'table':
            _validate_table(item)
        if kind in ('bam', 'vcf'):
            if 'field_encodings' in item and (kind != 'vcf' or item['field_encodings'] != {
                    'INFO/AS_SB_TABLE': 'gatk-strand-counts'}):
                raise _bad('unsupported explicit HTS field encoding')
            if item.get('coordinates') != ('0-based, half-open' if kind == 'bam'
                                            else '1-based, closed'):
                raise _bad(f'{kind} needs its explicit standard coordinate convention')
            if 'expected_samples' in item:
                _strings(item['expected_samples'], 'expected samples', empty=True)
            ignored = item.get('ignore_header_fields', {})
            if not isinstance(ignored, dict) or any(
                    not isinstance(k, str) or not k or not isinstance(v, str) or not v.strip()
                    for k, v in ignored.items()):
                raise _bad('ignored header fields need explicit names and reasons')
            protected = {'fileformat', 'contig', 'INFO', 'FORMAT', 'FILTER', 'reference'}
            if (kind == 'bam' and not ignored.keys() <= {'PG', 'CO'}
                    or kind == 'vcf' and ignored.keys() & protected):
                raise _bad('scientific header declarations cannot be ignored')
        if kind == 'h5ad_matrix':
            selector = item.get('matrix')
            if (not isinstance(selector, str) or selector != 'X'
                    and re.fullmatch(r'layers/[^/.][^/]*', selector) is None):
                raise _bad('H5AD matrix must explicitly select X or layers/name')
            _strings(item.get('expected_cells'), 'expected cells', empty=True)
            _strings(item.get('expected_genes'), 'expected genes', empty=True)
            if item.get('axis_policy') not in ('exact', 'subset'):
                raise _bad('H5AD axis_policy must explicitly be exact or subset')
            if any(type(item.get(key)) is not bool for key in ('integer', 'nonnegative')):
                raise _bad('H5AD integer/nonnegative requirements must be explicit booleans')
    return spec, hashlib.sha256(data).hexdigest()


def _validate_table(item):
    if item.get('delimiter') not in (',', '\t'):
        raise _bad('table delimiter must be comma or tab')
    columns = _strings(item.get('columns'), 'table columns', blank=True)
    keys = _strings(item.get('key'), 'table key')
    numeric = _strings(item.get('numeric', []), 'numeric columns', empty=True)
    if not set(keys + numeric).issubset(columns) or set(keys) & set(numeric):
        raise _bad('table keys/numeric columns must be distinct declared columns')
    if 'sample_columns' in item:
        samples = _strings(item['sample_columns'], 'sample columns')
        if not set(samples).issubset(columns):
            raise _bad('sample columns must be declared table columns')
    if 'sample_column' in item or 'expected_samples' in item:
        if item.get('sample_column') not in columns or 'sample_columns' in item:
            raise _bad('sample_column must name one column, separately from sample_columns')
        _strings(item.get('expected_samples'), 'expected samples')
    ignored = item.get('ignore_columns', {})
    _fields(ignored, set(columns) - set(keys + numeric + item.get('sample_columns', []))
            - {item.get('sample_column')}, 'ignored table columns')
    if any(not isinstance(reason, str) or not reason.strip() for reason in ignored.values()):
        raise _bad('ignored table columns need explicit reasons')
    tolerances = item.get('tolerances', {})
    _fields(tolerances, set(numeric), 'tolerance columns')
    for column, rule in tolerances.items():
        _fields(rule, {'absolute', 'relative', 'reason'}, f'tolerance for {column}')
        try:
            absolute, relative = (_number(rule.get(key, 0)) for key in ('absolute', 'relative'))
        except ValueError as exc:
            raise _bad(f'invalid tolerance: {exc}') from exc
        if absolute < 0 or relative < 0:
            raise _bad('tolerances cannot be negative')
        if (absolute or relative) and (not isinstance(rule.get('reason'), str)
                                      or not rule['reason'].strip()):
            raise _bad('nonzero tolerance needs a scientific reason')


@contextmanager
def _directory(path):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = os.open(path.anchor, flags)
    try:
        for part in path.relative_to(path.anchor).parts:
            child = os.open(part, flags, dir_fd=parent)
            os.close(parent)
            parent = child
        yield parent
    finally:
        os.close(parent)


@contextmanager
def _open(root, relative):
    """Resolve internal links, then hold every canonical ancestor while opening the data."""
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError('artifact symlinks must stay inside the run directory')
    with _directory(path.parent) as parent:
        parts = path.relative_to(path.anchor).parts
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('artifact must be a regular file')
        yield stream


def _hash(stream):
    stream.seek(0)
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(chunk)
    stream.seek(0)
    return digest.hexdigest()


def _dump(value):
    return json.dumps(value, ensure_ascii=True, separators=(',', ':'))


def _insert(db, side, key, value, length=0):
    try:
        db.execute(f'INSERT INTO {side} VALUES (?, ?, ?)', (_dump(key), _dump(value), length))
    except sqlite3.IntegrityError as exc:
        raise ValueError(f'duplicate record key: {key!r}') from exc


def _table(stream, item, db, side):
    samples, count = set(), 0
    text = io.TextIOWrapper(stream, encoding='utf-8-sig', newline='')
    try:
        reader = csv.reader(text, delimiter=item['delimiter'], strict=True)
        header = next(reader, [])
        if len(header) != len(set(header)):
            raise ValueError('duplicate table columns')
        if set(header) != set(item['columns']):
            raise ValueError(f'table columns differ: expected {item["columns"]!r}, got {header!r}')
        for line, cells in enumerate(reader, 2):
            if len(cells) != len(header):
                raise ValueError(f'row {line} has {len(cells)} columns; expected {len(header)}')
            row = dict(zip(header, cells, strict=True))
            key = [row[column] for column in item['key']]
            if any(not value for value in key):
                raise ValueError(f'empty table key at row {line}')
            for column in item.get('numeric', []):
                _number(row[column])
            if column := item.get('sample_column'):
                samples.add(row[column])
            _insert(db, side, key, [row[column] for column in item['columns']])
            count += 1
    finally:
        text.detach()
    issues = []
    if 'sample_column' in item:
        expected = set(item['expected_samples'])
        if samples != expected:
            issues.append(f'sample coverage differs: missing {sorted(expected - samples)!r}; '
                          f'unexpected {sorted(samples - expected)!r}')
    return {'records': count, 'columns': header,
            **({'samples': sorted(samples)} if 'sample_column' in item else {})}, issues


def _fasta(stream, item, db, side):
    text = io.TextIOWrapper(stream, encoding='utf-8')
    count, total, name, description, length, digest = 0, 0, None, '', 0, hashlib.sha256()

    def finish():
        if name is not None:
            if not length:
                raise ValueError('FASTA sequence record is empty')
            _insert(db, side, name, [description, length, digest.hexdigest()], length)

    try:
        for line in text:
            value = line.rstrip('\r\n')
            if not value:
                continue
            if value.startswith('>'):
                finish()
                header = value[1:].split(maxsplit=1)
                if not header:
                    raise ValueError('FASTA record has no identifier')
                name, description = header[0], header[1] if len(header) > 1 else ''
                length, digest = 0, hashlib.sha256()
                count += 1
            else:
                if name is None or re.fullmatch('[A-Za-z*.-]+', value) is None:
                    raise ValueError('invalid FASTA sequence or missing header')
                digest.update(value.encode('ascii'))
                length += len(value)
                total += len(value)
        finish()
    finally:
        text.detach()
    n50, cumulative = 0, 0
    for (size,) in db.execute(f'SELECT length FROM {side} ORDER BY length DESC'):
        cumulative += size
        if cumulative * 2 >= total:
            n50 = size
            break
    return {'records': count, 'metrics': {'sequences': count, 'total_bp': total, 'n50': n50}}, []


def _measure(root, item, db, side, baseline):
    with _open(root, item['path']) as stream:
        digest = _hash(stream)
        if baseline is not None and baseline.get(item['path']) != digest:
            raise ValueError('live original artifact does not match its recorded output checksum')
        if item['format'] in ('bam', 'vcf'):
            from runner.scientific_hts import measure as adapter
        elif item['format'] == 'h5ad_matrix':
            from runner.scientific_h5ad import measure as adapter
        else:
            adapter = _table if item['format'] == 'table' else _fasta
        result, issues = adapter(stream, item, db, side)
        if _hash(stream) != digest:
            raise ValueError('artifact changed during scientific assessment')
    result['sha256'] = digest
    if result['records'] < item.get('min_records', 0):
        issues.append(f'expected at least {item["min_records"]} records, got {result["records"]}')
    if 'expected_records' in item and result['records'] != item['expected_records']:
        issues.append(f'expected {item["expected_records"]} records, got {result["records"]}')
    return result, issues


def _equal(a, b, item):
    if item['format'] != 'table':
        return a == b
    numeric = set(item.get('numeric', []))
    for column, left, right in zip(item['columns'], a, b, strict=True):
        if column in item.get('ignore_columns', {}):
            continue
        if column not in numeric:
            if left != right:
                return False
            continue
        x, y = _number(left), _number(right)
        rule = item.get('tolerances', {}).get(column, {})
        absolute, relative = (_number(rule.get(key, 0)) for key in ('absolute', 'relative'))
        if abs(x - y) > absolute + relative * max(abs(x), abs(y)):
            return False
    return True


def _compare(db, item):
    result = {'missing_records': 0, 'extra_records': 0, 'changed_records': 0, 'examples': []}
    for key, left, right in db.execute(
            'SELECT a.key,a.value,b.value FROM original a LEFT JOIN replay b ON a.key=b.key'):
        kind = 'missing_records' if right is None else (
            'changed_records' if not _equal(json.loads(left), json.loads(right), item) else None)
        multiplicity = 1
        if item['format'] in ('bam', 'vcf'):
            x, y = int(left), int(right) if right is not None else 0
            kind = 'missing_records' if x > y else 'extra_records' if y > x else None
            multiplicity = abs(x - y)
        if kind:
            result[kind] += multiplicity
            if len(result['examples']) < _EXAMPLES:
                result['examples'].append({'kind': kind, 'key': json.loads(key)})
    for key, value in db.execute(
            'SELECT b.key,b.value FROM replay b LEFT JOIN original a '
            'ON a.key=b.key WHERE a.key IS NULL'):
        result['extra_records'] += int(value) if item['format'] in ('bam', 'vcf') else 1
        if len(result['examples']) < _EXAMPLES:
            result['examples'].append({'kind': 'extra_records', 'key': json.loads(key)})
    return result


def _binding(root, binding):
    if binding is None:
        return []
    try:
        with _open(root, 'provenance/run_manifest.json') as stream:
            manifest = _json(stream.read(1024 * 1024))
        with _open(root, 'provenance/params.json') as stream:
            data = stream.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024:
                raise ValueError('parameter binding record exceeds 1 MiB')
            params = _json(data)
        if not isinstance(manifest, dict) or not isinstance(params, dict):
            raise ValueError('binding records must be objects')
        issues = []
        with _open(root, 'provenance/configs.sha256') as stream:
            checksums = parse_checksums(stream.read().decode('utf-8'), relative=False)
        recorded_base = manifest.get('provenance_real_path', str(root / 'provenance'))
        if not isinstance(recorded_base, str) or not Path(recorded_base).is_absolute():
            raise ValueError('invalid recorded provenance directory')
        expected = checksums.get(str(Path(recorded_base) / 'params.json'))
        if expected != hashlib.sha256(data).hexdigest():
            issues.append('parameter bytes do not match their recorded configuration checksum')
        if ((manifest.get('pipeline'), manifest.get('commit'))
                != (binding['name'], binding['commit'])):
            issues.append('recorded pipeline/revision does not match the contract')
        for name, expected in binding.get('params', {}).items():
            if name not in params or not _json_equal(params[name], expected):
                issues.append(f'recorded parameter {name!r} does not match the contract')
        return issues
    except (OSError, ValueError, RuntimeError) as exc:
        return [f'cannot verify pipeline/parameter binding: {exc}']


def _unassessed(root, selected):
    count, links, examples = 0, 0, []

    def walk(fd, relative):
        nonlocal count, links
        with os.scandir(fd) as entries:
            names = sorted((entry.name, entry.is_dir(follow_symlinks=False), entry.is_symlink())
                           for entry in entries)
        for name, directory, link in names:
            path = relative / name
            if not outputs.is_result(path):
                continue
            if directory:
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    walk(child, path)
                finally:
                    os.close(child)
            elif path.as_posix() not in selected:
                count += 1
                links += int(link)
                if len(examples) < _EXAMPLES:
                    examples.append(path.as_posix())
    with _directory(root) as fd:
        walk(fd, Path())
    return {'count': count, 'examples': examples, 'unexpanded_links': links,
            'scope': 'Unselected file/link entries; directory symlinks are never traversed.'}


def assess(outdir: Path, contract: Path, *, against: Path | None = None):
    spec, digest = load_contract(contract)
    root = Path(outdir).expanduser().resolve()
    original = Path(against).expanduser().resolve() if against is not None else None
    roots = [root, *([original] if original is not None else [])]
    for directory in roots:
        if not directory.is_dir():
            raise _bad(f'not a run directory: {directory}')
    scratch = Path(tempfile.gettempdir()).resolve()
    if any(scratch.is_relative_to(directory) for directory in roots):
        raise _bad('temporary directory must be outside both run directories; set TMPDIR')
    result = {'version': VERSION, 'comparator': 'nfclaw.scientific/1',
              'assessed_at': datetime.now(UTC).isoformat(),
              'contract': spec['name'], 'contract_sha256': digest,
              'original': str(original) if original is not None else None, 'replay': str(root),
              'scope': 'Only declared artifacts, record expectations and comparisons are assessed. '
                       'Agreement does not establish biological accuracy, reference-byte '
                       'identity or continuous immutability.', 'issues': [], 'artifacts': []}
    # Source/branch conditions select the recorded reference. Candidate content can agree
    # without its software or parameters agreeing; ordinary verify checks those separately.
    bound_roots = [original] if original is not None else [root]
    result['pipeline_binding_scope'] = ('recorded original only; candidate source and parameters '
                                       'are unverified' if original is not None else 'assessed run')
    for directory in bound_roots:
        result['issues'] += [f'{directory}: {issue}' for issue in
                             _binding(directory, spec.get('pipeline'))]
    baseline = None
    if original is not None:
        try:
            with _open(original, 'provenance/outputs.sha256') as stream:
                text = stream.read().decode('utf-8')
            baseline = parse_checksums(text)
            if not text:
                raise ValueError('empty output checksum record')
        except (OSError, ValueError, RuntimeError) as exc:
            result['issues'].append(f'cannot verify recorded original outputs: {exc}')
            baseline = {}
    with tempfile.TemporaryDirectory(prefix='nfclaw-assess-', dir=scratch) as temporary:
        with sqlite3.connect(Path(temporary) / 'records.sqlite') as db:
            for item in spec['artifacts']:
                entry = {'path': item['path'], 'format': item['format'], 'issues': [],
                         'coordinates': item.get('coordinates', 'not declared'),
                         'tolerances': item.get('tolerances', {})}
                if item['format'] in ('bam', 'vcf'):
                    entry['ignored_header_fields'] = item.get('ignore_header_fields', {})
                    entry['field_encodings'] = item.get('field_encodings', {})
                if item['format'] == 'table':
                    entry['ignore_columns'] = item.get('ignore_columns', {})
                for side in ('original', 'replay'):
                    db.execute(f'DROP TABLE IF EXISTS {side}')
                    db.execute(f'CREATE TABLE {side} '
                               '(key TEXT PRIMARY KEY, value TEXT NOT NULL, length INTEGER)')
                measured = []
                for side, directory in [('original', original), ('replay', root)]:
                    if directory is None:
                        continue
                    try:
                        entry[side], issues = _measure(directory, item, db, side,
                                                       baseline if side == 'original' else None)
                        entry['issues'] += [f'{side}: {issue}' for issue in issues]
                        measured.append(side)
                    except (OSError, ValueError, RuntimeError, csv.Error, sqlite3.Error) as exc:
                        entry['issues'].append(f'{side}: {exc}')
                if original is not None and len(measured) == 2:
                    entry['comparison'] = _compare(db, item)
                    if entry['original'].get('header') != entry['replay'].get('header'):
                        entry['issues'].append('scientific headers differ')
                    if any(entry['comparison'][key] for key in (
                            'missing_records', 'extra_records', 'changed_records')):
                        entry['issues'].append('declared scientific records differ')
                entry['passed'] = not entry['issues']
                result['artifacts'].append(entry)
    selected = {item['path'] for item in spec['artifacts']}
    try:
        result['unassessed_files'] = _unassessed(root, selected)
    except OSError as exc:
        result['issues'].append(f'cannot inventory unassessed results: {exc}')
        result['unassessed_files'] = {'count': None, 'examples': [], 'unexpanded_links': None}
    result['passed'] = not result['issues'] and all(x['passed'] for x in result['artifacts'])
    return result
