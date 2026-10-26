"""Audited missing defaults for a release's bundled demo; never change upstream task code."""
from __future__ import annotations

_BAMTOFASTQ = ('bamtofastq', '8a295860c0c9221337dec7f2620709a47cea254d')
_REFERENCE = ('https://raw.githubusercontent.com/nf-core/test-datasets/'
              '618f1541382c4ad49eff566dadf13d5ccbd0ebb4/'
              'data/genomics/homo_sapiens/genome/genome.fasta')
_PARAMETERS = {_BAMTOFASTQ: {'fasta': _REFERENCE}}
_NOTES = {_BAMTOFASTQ:
    'This pinned test profile omits its required reference. For the bundled demo input, nfclaw '
    'supplies the matched chr22:1-40001 test FASTA from immutable test-datasets commit '
    '`618f1541382c4ad49eff566dadf13d5ccbd0ebb4` and records it in params/provenance. Explicit '
    '`--fasta` or params-file values override it. Supplying your own input disables this demo '
    'default; choose a reference matched to your data. Other releases retain their own defaults.'}


def parameters(name: str, commit: str | None) -> dict:
    return dict(_PARAMETERS.get((name, commit), {}))


def note(name: str, commit: str | None) -> str:
    return _NOTES.get((name, commit), '')
