"""Audited missing defaults for a release's bundled demo; never change upstream task code."""
from __future__ import annotations

import csv
import io

_BAMTOFASTQ = ('bamtofastq', '8a295860c0c9221337dec7f2620709a47cea254d')
_TUMOUREVO = ('tumourevo', '180ae5447d0eb0214f650b6fcf7dabed0c77b5a2')
_HGTSEQ = ('hgtseq', '683daaf41bb396839445e603152b45daa141ced4')
_HGT_DATA = '800330ec8f47c93caabe8157e20dd23e243de4e1'
_HGT_BASE = f'https://raw.githubusercontent.com/nf-core/test-datasets/{_HGT_DATA}/testdata/'
_MODULE_DATA = ('https://raw.githubusercontent.com/nf-core/test-datasets/'
                '56591d0269db196203af3b0cb2191da22384d24a/data/genomics/')
_REFERENCE = ('https://raw.githubusercontent.com/nf-core/test-datasets/'
              '618f1541382c4ad49eff566dadf13d5ccbd0ebb4/'
              'data/genomics/homo_sapiens/genome/genome.fasta')
_PARAMETERS = {_BAMTOFASTQ: {'fasta': _REFERENCE},
               _TUMOUREVO: {'sparsesignatures_k': '2:3'},
               _HGTSEQ: {'gff': _HGT_BASE + 'reference/Homo_sapiens.hg38.chr21.gff3',
                        'fasta': _MODULE_DATA + 'homo_sapiens/genome/chr21/sequence/genome.fasta',
                        'krakendb': _MODULE_DATA + 'sarscov2/genome/db/kraken2.tar.gz',
                        'kronadb': _MODULE_DATA + 'sarscov2/metagenome/krona_taxonomy.tab'}}
_DATA_SELECTORS = {_BAMTOFASTQ: {'input', 'genome', 'pipelines_testdata_base_path'},
                   _TUMOUREVO: {'input', 'pipelines_testdata_base_path'},
                   _HGTSEQ: {'input', 'genome', 'pipelines_testdata_base_path',
                             'fasta', 'gff', 'krakendb', 'kronadb', 'bwaindex', 'bwamem2index',
                             'igenomes_base'}}
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
    'sufficient memory for SparseSignatures. Other releases retain their own defaults.',
    _HGTSEQ:
    'This pinned consumer requires `input1`/`input2`, but its moving demo sheet now uses newer '
    'columns. For a bare bundled demo, nfclaw stages a three-sample historical CSV with immutable '
    'read/GFF URLs from test-datasets commit `800330ec8f47c93caabe8157e20dd23e243de4e1` and '
    'matched immutable FASTA/Kraken/Krona inputs from '
    '`56591d0269db196203af3b0cb2191da22384d24a`. The CSV is bundled in provenance and rebased '
    'for replay; no remote sheet is rescanned. Explicit input, reference/database/data-base '
    'selectors, extra profiles or `--config` disable this entire recipe so reference choices '
    'are not mixed. Other releases retain their own defaults.'}


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


def samplesheet(name: str, commit: str | None):
    """A named historical fixture, staged like generated input without a package-path dependency.

    Eligibility/override checks belong to the same caller as parameters(); this function only
    constructs immutable CSV bytes. No input-role or biological choice is inferred from filenames.
    """
    if (name, commit) != _HGTSEQ:
        return None
    from runner.sheetgen import Generated

    header = ('sample', 'group', 'input1', 'input2')
    rows = tuple({'sample': sample, 'group': 'test',
                  'input1': _HGT_BASE + f'fastq/{sample}_1.fastq.gz',
                  'input2': _HGT_BASE + f'fastq/{sample}_2.fastq.gz'}
                 for sample in ('testsample01', 'testsample02', 'testsample03'))
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=header, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return Generated(text=stream.getvalue(), suffix='.csv', header=header, rows=rows, files=(),
                     id_column='sample', summary='Prepared the immutable historical HGTseq demo '
                     'samplesheet: 3 named samples, 3 paired rows.', notes=(),
                     record={'version': 1, 'kind': 'bundled_demo_fixture', 'pipeline': name,
                             'pipeline_commit': commit, 'data_commit': _HGT_DATA,
                             'samples': 3, 'rows': 3, 'paired_end': 3, 'single_end': 0,
                             'files': 0, 'sources': ['bundled:runner.demo_defaults/hgtseq']})
