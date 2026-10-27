"""Audited missing defaults for a release's bundled demo; never change upstream task code."""
from __future__ import annotations

_BAMTOFASTQ = ('bamtofastq', '8a295860c0c9221337dec7f2620709a47cea254d')
_TUMOUREVO = ('tumourevo', '180ae5447d0eb0214f650b6fcf7dabed0c77b5a2')
_REFERENCE = ('https://raw.githubusercontent.com/nf-core/test-datasets/'
              '618f1541382c4ad49eff566dadf13d5ccbd0ebb4/'
              'data/genomics/homo_sapiens/genome/genome.fasta')
_PARAMETERS = {_BAMTOFASTQ: {'fasta': _REFERENCE},
               _TUMOUREVO: {'sparsesignatures_k': '2:3'}}
_DATA_SELECTORS = {_BAMTOFASTQ: {'input', 'genome', 'pipelines_testdata_base_path'},
                   _TUMOUREVO: {'input', 'pipelines_testdata_base_path'}}
_NOTES = {_BAMTOFASTQ:
    'This pinned test profile omits its required reference. For the bundled demo input, nfclaw '
    'supplies the matched chr22:1-40001 test FASTA from immutable test-datasets commit '
    '`618f1541382c4ad49eff566dadf13d5ccbd0ebb4` and records it in params/provenance. Explicit '
    '`--fasta` or params-file values override it. Your own input, genome, test-data base, extra '
    'profiles or `--config` '
    'disable this demo default; choose a reference matched to your data. The correction applies '
    'only to the bundled test plus engine profiles. Other releases retain their own defaults.',
    _TUMOUREVO:
    'This pinned test profile misspells `sparsesignatures_K`; the declared parameter is '
    '`sparsesignatures_k`. For its bundled tiny input, nfclaw supplies the intended `2:3` grid '
    'and records it in params/provenance. Explicit CLI or params-file values win. Your own input, '
    'test-data base, extra profiles or `--config` disable this demo default. A native original '
    'and fresh replay completed with a 24 GiB task ceiling; an 8 GiB task was killed. Allocate '
    'sufficient memory for SparseSignatures. Other releases retain their own defaults.'}


def bundled_profile(profile: str) -> bool:
    """Extra profiles can replace the demo's input/reference, so never override them."""
    engines = {'test', 'docker', 'podman', 'singularity', 'apptainer', 'conda', 'mamba',
               'charliecloud', 'shifter'}
    return {part.strip() for part in profile.split(',') if part.strip()}.issubset(engines)


def parameters(name: str, commit: str | None, *, provided: frozenset[str] = frozenset()) -> dict:
    key = (name, commit)
    return {} if provided & _DATA_SELECTORS.get(key, set()) else dict(_PARAMETERS.get(key, {}))


def note(name: str, commit: str | None) -> str:
    return _NOTES.get((name, commit), '')
