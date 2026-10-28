"""Selected H5AD matrix/axis assessment, not a claim about an entire AnnData object."""
from __future__ import annotations

import math
import hashlib
import json
from fractions import Fraction


def _text(value):
    return value.decode('utf-8') if isinstance(value, bytes) else value


def _child(parent, name, h5py):
    # Inspect a link before dereferencing it. Even internal soft links are unsupported here.
    link = parent.get(name, getlink=True)
    if not isinstance(link, h5py.HardLink):
        raise ValueError('missing, soft or external HDF5 links are unsupported')
    value = parent[name]
    if isinstance(value, h5py.Dataset) and (value.is_virtual or value.external):
        raise ValueError('external storage and virtual HDF5 datasets are unsupported')
    return value


def _index(source, axis, h5py):
    group = _child(source, axis, h5py)
    if (not isinstance(group, h5py.Group)
            or _text(group.attrs.get('encoding-type')) != 'dataframe'
            or _text(group.attrs.get('encoding-version')) != '0.2.0'):
        raise ValueError('unsupported H5AD axis dataframe encoding')
    name = _text(group.attrs.get('_index'))
    if not isinstance(name, str) or not name or '/' in name or name in ('.', '..'):
        raise ValueError('invalid H5AD declared index name')
    dataset = _child(group, name, h5py)
    if (not isinstance(dataset, h5py.Dataset) or dataset.ndim != 1
            or _text(dataset.attrs.get('encoding-type')) != 'string-array'
            or _text(dataset.attrs.get('encoding-version')) != '0.2.0'
            or h5py.check_string_dtype(dataset.dtype) is None):
        raise ValueError('unsupported H5AD index string-array encoding')
    names = list(dataset.asstr()[:])
    if any(not name or '\x00' in name for name in names) or len(names) != len(set(names)):
        raise ValueError('empty or duplicate H5AD axis identifiers')
    return names


def _numeric(dataset, h5py):
    if (not isinstance(dataset, h5py.Dataset) or dataset.dtype.kind not in 'iuf'
            or dataset.dtype.itemsize > 8):
        raise ValueError('selected H5AD data must be supported real numeric values')


def _value(value, item):
    number = value.item() if hasattr(value, 'item') else value
    if isinstance(number, float) and not math.isfinite(number):
        raise ValueError('selected H5AD matrix contains non-finite values')
    rational = Fraction(number)
    if item['integer'] and rational.denominator != 1:
        raise ValueError('selected H5AD matrix requires integer values')
    if item['nonnegative'] and rational < 0:
        raise ValueError('selected H5AD matrix requires nonnegative values')
    return str(rational)


def measure(stream, item, db, side):
    try:
        import h5py
    except ImportError as exc:
        raise ValueError('H5AD assessment needs pip install "nfclaw[scientific]"') from exc
    from runner.scientific import _insert

    count = 0
    with h5py.File(stream, 'r') as source:
        if (_text(source.attrs.get('encoding-type')) != 'anndata'
                or _text(source.attrs.get('encoding-version')) != '0.1.0'):
            raise ValueError('unsupported H5AD AnnData encoding')
        cells, genes = _index(source, 'obs', h5py), _index(source, 'var', h5py)
        issues = []
        for label, observed in [('cells', cells), ('genes', genes)]:
            expected = set(item[f'expected_{label}'])
            missing, extra = expected - set(observed), set(observed) - expected
            if missing or item['axis_policy'] == 'exact' and extra:
                issues.append(f'H5AD {label} coverage differs: {len(missing)} missing '
                              f'(examples {sorted(missing)[:20]!r}); {len(extra)} unexpected '
                              f'(examples {sorted(extra)[:20]!r})')
        matrix = source
        for part in item['matrix'].split('/'):
            if not isinstance(matrix, h5py.Group):
                raise ValueError('invalid selected H5AD matrix path')
            matrix = _child(matrix, part, h5py)
        encoding = _text(matrix.attrs.get('encoding-type'))
        version = _text(matrix.attrs.get('encoding-version'))
        shape = (len(cells), len(genes))
        if isinstance(matrix, h5py.Dataset):
            _numeric(matrix, h5py)
            if encoding != 'array' or version != '0.2.0' or matrix.shape != shape:
                raise ValueError('unsupported H5AD dense encoding or matrix/axis shape mismatch')
            for i, cell in enumerate(cells):
                for start in range(0, len(genes), 4096):
                    for offset, number in enumerate(matrix[i, start:start + 4096]):
                        value = _value(number, item)
                        if value != '0':
                            _insert(db, side, [cell, genes[start + offset]], value)
                            count += 1
        elif encoding in ('csr_matrix', 'csc_matrix') and version == '0.1.0':
            declared_shape = matrix.attrs.get('shape')
            if (getattr(declared_shape, 'shape', None) != (2,)
                    or declared_shape.dtype.kind not in 'iu' or tuple(declared_shape) != shape):
                raise ValueError('H5AD sparse matrix/axis shape mismatch')
            data, indices, pointers = [_child(matrix, name, h5py)
                                       for name in ('data', 'indices', 'indptr')]
            _numeric(data, h5py)
            if (not isinstance(indices, h5py.Dataset) or not isinstance(pointers, h5py.Dataset)
                    or any(x.ndim != 1 for x in (data, indices, pointers))
                    or any(x.dtype.kind not in 'iu' for x in (indices, pointers))
                    or len(indices) != len(data)):
                raise ValueError('invalid H5AD sparse data/index arrays')
            major, minor = shape if encoding == 'csr_matrix' else shape[::-1]
            if len(pointers) != major + 1 or int(pointers[0]) != 0:
                raise ValueError('invalid H5AD sparse pointers')
            previous = 0
            for axis in range(major):
                end = int(pointers[axis + 1])
                if end < previous or end > len(data):
                    raise ValueError('invalid H5AD sparse pointers')
                for start in range(previous, end, 4096):
                    stop = min(end, start + 4096)
                    for index, number in zip(indices[start:stop], data[start:stop], strict=True):
                        index = int(index)
                        if index < 0 or index >= minor:
                            raise ValueError('invalid H5AD sparse index bounds')
                        i, j = (axis, index) if encoding == 'csr_matrix' else (index, axis)
                        value = _value(number, item)
                        # Keep explicit zeros until all duplicate coordinates have been checked.
                        _insert(db, side, [cells[i], genes[j]], value)
                        count += value != '0'
                previous = end
            if previous != len(data):
                raise ValueError('H5AD sparse pointers do not cover every stored value')
            db.execute(f'DELETE FROM {side} WHERE value=?', ('"0"',))
        else:
            raise ValueError('unsupported selected H5AD matrix encoding')
    return {'records': count,
            'metrics': {'cells': len(cells), 'genes': len(genes), 'nonzero': count},
            'header': {'cells': _axis_digest(cells), 'genes': _axis_digest(genes)},
            'adapter': f'h5py/{h5py.__version__}',
            'semantics': 'Only the selected matrix and declared cell/gene indexes are assessed. '
                         'Finite numeric values compare exactly by cell/gene identity; implicit '
                         'and explicit zero are equivalent. All other AnnData content is out of '
                         'scope, including obs/var annotations, embeddings, graphs, raw, uns '
                         'and unselected matrices.'}, issues


def _axis_digest(names):
    return {'count': len(names), 'sha256': hashlib.sha256(json.dumps(
        sorted(names), ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()}
