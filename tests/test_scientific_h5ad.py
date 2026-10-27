"""H5AD selected-matrix contracts cannot treat excluded metadata or external data as validated."""
import hashlib

import pytest

from test_scientific import assess, contract, run_dir

h5py = pytest.importorskip('h5py')
np = pytest.importorskip('numpy')


def h5ad(root, *, matrix=None, cells=('cell_A', 'cell_B'), genes=('gene_A', 'gene_B'),
         sparse=None, selector='X'):
    path = root / 'cells.h5ad'
    with h5py.File(path, 'w') as f:
        f.attrs.update({'encoding-type': 'anndata', 'encoding-version': '0.1.0'})
        for axis, names in [('obs', cells), ('var', genes)]:
            group = f.create_group(axis)
            group.attrs.update({'_index': 'names', 'encoding-type': 'dataframe',
                                'encoding-version': '0.2.0', 'column-order': []})
            index = group.create_dataset('names', data=names, dtype=h5py.string_dtype())
            index.attrs.update({'encoding-type': 'string-array', 'encoding-version': '0.2.0'})
        if sparse:
            group = f.create_group(selector)
            group.attrs.update({'encoding-type': sparse, 'encoding-version': '0.1.0',
                                'shape': [len(cells), len(genes)]})
            for name, values in [('data', [1.0, 2.0]), ('indices', [0, 1]), ('indptr', [0, 1, 2])]:
                group.create_dataset(name, data=values)
        else:
            data = np.array([[1.0, 0.0], [0.0, 2.0]]) if matrix is None else matrix
            dataset = f.create_dataset(selector, data=data)
            dataset.attrs.update({'encoding-type': 'array', 'encoding-version': '0.2.0'})
    snapshot(root)
    return path


def snapshot(root):
    path = root / 'cells.h5ad'
    (root / 'provenance/outputs.sha256').write_text(
        f'{hashlib.sha256(path.read_bytes()).hexdigest()}  cells.h5ad\n')


def spec(tmp_path, **extra):
    return contract(tmp_path, [{'path': 'cells.h5ad', 'format': 'h5ad_matrix', 'matrix': 'X',
        'expected_cells': ['cell_A', 'cell_B'], 'expected_genes': ['gene_A', 'gene_B'],
        'axis_policy': 'exact', 'integer': True, 'nonnegative': True, **extra}])


@pytest.mark.parametrize('encoding', [None, 'csr_matrix', 'csc_matrix'])
def test_dense_and_sparse_selected_matrix_assessment(tmp_path, encoding):
    root = run_dir(tmp_path, 'a', {})
    h5ad(root, sparse=encoding)
    result = assess(root, spec(tmp_path))
    assert result['passed']
    measured = result['artifacts'][0]['replay']
    assert measured['metrics'] == {'cells': 2, 'genes': 2, 'nonzero': 2}
    assert 'out of scope' in measured['semantics']


def test_h5ad_matrix_comparison_maps_values_to_axis_identifiers(tmp_path):
    a, b = run_dir(tmp_path, 'a', {}), run_dir(tmp_path, 'b', {})
    h5ad(a)
    h5ad(b, cells=('cell_B', 'cell_A'), genes=('gene_B', 'gene_A'), matrix=[[2, 0], [0, 1]])
    assert assess(b, spec(tmp_path), a)['passed']
    h5ad(b, matrix=[[2, 0], [0, 1]])
    assert not assess(b, spec(tmp_path), a)['passed']


@pytest.mark.parametrize('cells,genes,matrix', [
    (('cell_A', 'cell_A'), ('gene_A', 'gene_B'), [[1, 0], [0, 2]]),
    (('cell_A',), ('gene_A', 'gene_B'), [[1, 0]]),
    (('cell_A', 'cell_B'), ('gene_A', 'gene_B'), [[1, 0]]),
    (('cell_A', 'cell_B'), ('gene_A', 'gene_B'), [[float('nan'), 0], [0, 2]]),
    (('cell_A', 'cell_B'), ('gene_A', 'gene_B'), [[-1, 0], [0, 2]]),
    (('cell_A', 'cell_B'), ('gene_A', 'gene_B'), [[1.5, 0], [0, 2]])])
def test_h5ad_rejects_missing_or_duplicate_axes_bad_shape_and_invalid_counts(
        tmp_path, cells, genes, matrix):
    root = run_dir(tmp_path, 'a', {})
    h5ad(root, cells=cells, genes=genes, matrix=matrix)
    assert not assess(root, spec(tmp_path))['passed']


@pytest.mark.parametrize('field,values', [
    ('indptr', [1, 1, 2]), ('indptr', [0, 2, 1]), ('indptr', [0, 1, 3]),
    ('indices', [0, 2]), ('indices', [0, -1]), ('indptr', [0.0, 1.0, 2.0])])
def test_h5ad_validates_sparse_pointers_and_indices(tmp_path, field, values):
    root = run_dir(tmp_path, 'a', {})
    path = h5ad(root, sparse='csr_matrix')
    with h5py.File(path, 'a') as f:
        del f['X'][field]
        f['X'].create_dataset(field, data=values)
    assert not assess(root, spec(tmp_path))['passed']


def test_h5ad_rejects_duplicate_sparse_coordinates(tmp_path):
    root = run_dir(tmp_path, 'a', {})
    path = h5ad(root, sparse='csr_matrix')
    with h5py.File(path, 'a') as f:
        f['X/indptr'][:] = [0, 2, 2]
        f['X/indices'][:] = [0, 0]
    assert not assess(root, spec(tmp_path))['passed']


@pytest.mark.parametrize('location', ['X', 'obs', 'obs/names', 'X/data'])
def test_h5ad_external_links_cannot_escape_rooted_artifact(tmp_path, location):
    root = run_dir(tmp_path, 'a', {})
    path = h5ad(root, sparse='csr_matrix' if location == 'X/data' else None)
    outside = tmp_path / 'outside.h5'
    with h5py.File(outside, 'w') as f:
        f.create_dataset('matrix', data=[[1, 0], [0, 2]])
        f.create_dataset('names', data=['cell_A', 'cell_B'], dtype=h5py.string_dtype())
    with h5py.File(path, 'a') as f:
        del f[location]
        f[location] = h5py.ExternalLink(str(outside), 'matrix' if location == 'X' else 'names')
    result = assess(root, spec(tmp_path))
    assert not result['passed']
    assert 'external' in str(result['artifacts'][0]['issues']).lower()


@pytest.mark.parametrize('backing', ['virtual', 'external'])
def test_h5ad_rejects_external_storage_and_virtual_datasets(tmp_path, backing):
    root = run_dir(tmp_path, 'a', {})
    path = h5ad(root)
    with h5py.File(path, 'a') as f:
        del f['X']
        if backing == 'virtual':
            layout = h5py.VirtualLayout(shape=(2, 2), dtype='f8')
            layout[:] = h5py.VirtualSource(str(tmp_path / 'outside.h5'), 'X', shape=(2, 2))
            dataset = f.create_virtual_dataset('X', layout)
        else:
            dataset = f.create_dataset('X', shape=(2, 2), dtype='f8',
                external=[(str(tmp_path / 'outside.bin'), 0, h5py.h5f.UNLIMITED)])
        dataset.attrs.update({'encoding-type': 'array', 'encoding-version': '0.2.0'})
    result = assess(root, spec(tmp_path))
    assert not result['passed']
    assert 'external' in str(result['artifacts'][0]['issues']).lower()


def test_normalized_layers_can_explicitly_allow_negative_noninteger_values(tmp_path):
    root = run_dir(tmp_path, 'a', {})
    h5ad(root, selector='layers/scaled', matrix=[[-1.25, 0], [0, 2.5]])
    result = assess(root, spec(tmp_path, matrix='layers/scaled', integer=False, nonnegative=False))
    assert result['passed']


@pytest.mark.parametrize('malformation', ['numeric_index', 'scalar_shape'])
def test_malformed_h5ad_metadata_returns_a_failed_assessment(tmp_path, malformation):
    root = run_dir(tmp_path, 'a', {})
    path = h5ad(root, sparse='csr_matrix')
    with h5py.File(path, 'a') as f:
        if malformation == 'numeric_index':
            del f['obs/names']
            d = f['obs'].create_dataset('names', data=[1, 2])
            d.attrs.update({'encoding-type': 'string-array', 'encoding-version': '0.2.0'})
        else:
            f['X'].attrs['shape'] = 2
    assert not assess(root, spec(tmp_path))['passed']
