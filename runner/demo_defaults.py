"""Audited fixtures/defaults for a release's bundled demo; never change upstream task code."""
from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path

_BAMTOFASTQ = ('bamtofastq', '8a295860c0c9221337dec7f2620709a47cea254d')
_TUMOUREVO = ('tumourevo', '180ae5447d0eb0214f650b6fcf7dabed0c77b5a2')
_HGTSEQ = ('hgtseq', '683daaf41bb396839445e603152b45daa141ced4')
_FASTQREPAIR = ('fastqrepair', '70a38209407b9367a9ff7ab8b26d84cb1983ea18')
_BACTMAP = ('bactmap', '834642d8ac150ca10d705833223e7bcf15efc210')
_CREATETAXDB = ('createtaxdb', 'b01a0f8ed96a5990d15470828dfa92a22cf08bba')
_FUNCSCAN = ('funcscan', 'aee3dc965eb0c77267435544dda30da858763913')
_BACTMAP_DATA = '02195cfa96ca496173e9d63dd58e34bf02fcf55a'
_BACTMAP_BASE = f'https://raw.githubusercontent.com/nf-core/test-datasets/{_BACTMAP_DATA}/'
_BACTMAP_CHECKER = '2e6b4b3e32dd0935fd4d5b4f42c359ed306f71a6be9b5676f26fdde14f228b54'
_FASTQ_DAMAGE = 'f72c633f2547fdfaf475c7f05423437a7eac0bbf'
# The moving test-data branches these demos name, pinned at the commits they held when pinned
# (every file byte-identical to the branch then). Nextflow reads a demo sheet only to validate
# it, so a remote sheet's consumed bytes are never recorded; a bundled one is.
_TEST_DATA = 'https://raw.githubusercontent.com/nf-core/test-datasets/'
_BAMTOFASTQ_DATA = 'e228f0e5412ed0bed20e7a99e1588cbf95f65102'
_CREATETAXDB_DATA = '9248a89ada220333b7bc3c7c07af5eb229c16d5b'
_FUNCSCAN_DATA = '6612875ff5d8d54fd0a7532acbfb9dda25edb9b2'
_HGT_DATA = '800330ec8f47c93caabe8157e20dd23e243de4e1'
_HGT_BASE = f'https://raw.githubusercontent.com/nf-core/test-datasets/{_HGT_DATA}/testdata/'
_MODULE_DATA = ('https://raw.githubusercontent.com/nf-core/test-datasets/'
                '56591d0269db196203af3b0cb2191da22384d24a/data/genomics/')
_REFERENCE = ('https://raw.githubusercontent.com/nf-core/test-datasets/'
              '618f1541382c4ad49eff566dadf13d5ccbd0ebb4/'
              'data/genomics/homo_sapiens/genome/genome.fasta')
_PARAMETERS = {_BAMTOFASTQ: {'fasta': _REFERENCE},
               _BACTMAP: {'reference': _BACTMAP_BASE + 'genome/NCTC13799.fna', 'max_cpus': 1},
               _TUMOUREVO: {'sparsesignatures_k': '2:3'},
               _CREATETAXDB: {key: f'{_TEST_DATA}{_CREATETAXDB_DATA}/data/taxonomy/{name}'
                              for key, name in (('accession2taxid', 'nucl_gb.accession2taxid'),
                                                ('nucl2taxid', 'nucl2tax.map'),
                                                ('prot2taxid', 'prot.accession2taxid.gz'),
                                                ('nodesdmp', 'nodes.dmp'),
                                                ('namesdmp', 'names.dmp'))},
               _FUNCSCAN: {'amp_hmmsearch_models':
                           f'{_TEST_DATA}{_FUNCSCAN_DATA}/hmms/mybacteriocin.hmm'},
               _FASTQREPAIR: {'num_splits': 2},
               _HGTSEQ: {'gff': _HGT_BASE + 'reference/Homo_sapiens.hg38.chr21.gff3',
                        'fasta': _MODULE_DATA + 'homo_sapiens/genome/chr21/sequence/genome.fasta',
                        'krakendb': _MODULE_DATA + 'sarscov2/genome/db/kraken2.tar.gz',
                        'kronadb': _MODULE_DATA + 'sarscov2/metagenome/krona_taxonomy.tab'}}
_DATA_SELECTORS = {_BAMTOFASTQ: {'input', 'genome', 'pipelines_testdata_base_path'},
                   _BACTMAP: {'input', 'reference'},
                   _TUMOUREVO: {'input', 'pipelines_testdata_base_path'},
                   _CREATETAXDB: {'input', 'pipelines_testdata_base_path', 'accession2taxid',
                                  'nucl2taxid', 'prot2taxid', 'nodesdmp', 'namesdmp',
                                  'malt_mapdb'},
                   _FUNCSCAN: {'input', 'pipelines_testdata_base_path',
                               'amp_hmmsearch_models'},
                   _FASTQREPAIR: {'input', 'pipelines_testdata_base_path'},
                   _HGTSEQ: {'input', 'genome', 'pipelines_testdata_base_path',
                             'fasta', 'gff', 'krakendb', 'kronadb', 'bwaindex', 'bwamem2index',
                             'igenomes_base'}}
_NOTES = {_BACTMAP:
    'This pinned bundled test uses missing moving data URLs. For a bare demo, nfclaw stages '
    'the three original paired samples and matched NCTC13799 reference from immutable '
    'test-datasets commit `02195cfa96ca496173e9d63dd58e34bf02fcf55a`. The generated sheet and '
    'data commit are recorded and rebased for replay. Explicit input or reference, custom '
    'profiles or `--config` disable the entire fixture. Other releases retain their defaults. '
    'Bare demos default to `max_cpus=1`: native two-CPU runs reordered identical reads and '
    'changed downstream alignments and pseudogenome masking; the single-CPU control matched. '
    'Explicit `--max-cpus` or params-file values win. Resource limits are ceilings and do not '
    'raise this default. Tree branch lengths and bootstrap support still need separate comparison. '
    'A source-bound working copy preserves module defaults, orders the pseudogenome alignment '
    'by sample name, seeds IQ-TREE and RAxML under the test profile, and skips '
    'the unbound MultiQC report wait only during preview; real runs still wait for the report.',
    _BAMTOFASTQ:
    'This pinned test profile omits its required reference. For the bundled demo input, nfclaw '
    'supplies the matched chr22:1-40001 test FASTA from immutable test-datasets commit '
    '`618f1541382c4ad49eff566dadf13d5ccbd0ebb4` and records it in params/provenance. Explicit '
    '`--fasta` or params-file values override it. Your own input, genome, test-data base, extra '
    'profiles or `--config` '
    'disable this demo default; choose a reference matched to your data. The correction applies '
    'only to the bundled test plus engine profiles. Its two-sample demo sheet is staged from '
    'immutable test-datasets commit `e228f0e5412ed0bed20e7a99e1588cbf95f65102` (the same bytes '
    'as the moving branch it names) and bundled in provenance, so a replay reads the recorded '
    'sheet. Other releases retain their own defaults.',
    _CREATETAXDB:
    'This pinned test profile reads its genome sheet and taxonomy files from a moving '
    'test-datasets branch. For a bare demo, nfclaw stages the same six-genome sheet with '
    'immutable FASTA URLs and supplies the taxonomy files from commit '
    '`9248a89ada220333b7bc3c7c07af5eb229c16d5b`, every file byte-identical to that branch. The '
    'sheet is bundled in provenance, so a replay reads the recorded sheet. Explicit input, '
    'taxonomy or MALT map selectors, the test-data base, extra profiles or `--config` disable '
    'the fixture. Other releases retain their own defaults.',
    _FUNCSCAN:
    'This pinned test profile reads its two-sample sheet and HMM model from a moving '
    'test-datasets branch. For a bare demo, nfclaw stages the same sheet with immutable FASTA '
    'URLs and supplies the HMM model from commit `6612875ff5d8d54fd0a7532acbfb9dda25edb9b2`, '
    'every file byte-identical to that branch. The sheet is bundled in provenance, so a replay '
    'reads the recorded sheet. Explicit input, HMM models, the test-data base, extra profiles '
    'or `--config` disable the fixture. Other releases retain their own defaults.',
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
    'are not mixed. Other releases retain their own defaults.',
    _FASTQREPAIR:
    'This pinned bundled test excludes its damaged pair after gzip recovery, so its original '
    'three rows never exercise BBMap paired repair. For a bare demo, nfclaw retains those damage '
    'cases at immutable test-datasets commit `f72c633f2547fdfaf475c7f05423437a7eac0bbf` and adds '
    '`paired_control`, 646 genuine pairs from `800330ec8f47c93caabe8157e20dd23e243de4e1`. The '
    'four-row CSV and row roles are bundled in provenance and rebased for replay. The damaged '
    'pair and empty sample remain excluded; the original single-end case has 24 complete valid '
    'reads. This adds paired execution coverage without claiming recovery of irreparable data. '
    'The intended `num_splits=2` default is recorded; explicit values win. User input/data-base '
    'selectors, extra profiles or `--config` disable the fixture. Other releases retain their '
    'own defaults.'}


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


def fixture_schema(name: str, commit: str | None, source: Path):
    """Validate only this paired bundled fixture where the old release has no JSON input schema.

    This is not an adapter for arbitrary user sheets or automatic sheet generation. The release's
    own Python consumer still validates the staged sheet during actual execution.
    """
    if (name, commit) != _BACTMAP:
        return None
    from runner.errors import ErrorCode, NfclawError
    from runner.schema import Column, InputSchema

    checker = source / 'bin/check_samplesheet.py'
    if (not checker.is_file() or
            hashlib.sha256(checker.read_bytes()).hexdigest() != _BACTMAP_CHECKER):
        raise NfclawError(ErrorCode.SAMPLESHEET_INVALID,
                          'The Bactmap bundled fixture consumer does not match its audited source.')
    return InputSchema(columns=(Column('sample', 'string', True, r'^\S+$'),
                                Column('fastq_1', 'string', True, r'^\S+\.(?:fastq|fq)\.gz$',
                                       fmt='file-path'),
                                Column('fastq_2', 'string', True, r'^\S+\.(?:fastq|fq)\.gz$',
                                       fmt='file-path')),
                       header_prefix=('sample', 'fastq_1', 'fastq_2'),
                       unique_entries=(('sample', 'fastq_1', 'fastq_2'),),
                       audit_note='Source-bound paired bundled Bactmap fixture only.')


def _csv(header: tuple[str, ...], rows) -> str:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=header, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def samplesheet(name: str, commit: str | None):
    """A named historical fixture, staged like generated input without a package-path dependency.

    Eligibility/override checks belong to the same caller as parameters(); this function only
    constructs immutable CSV bytes. No input-role or biological choice is inferred from filenames.
    """
    if (name, commit) == _FASTQREPAIR:
        return _fastqrepair_sheet(name, commit)
    if (name, commit) == _BACTMAP:
        return _bactmap_sheet(name, commit)
    if (name, commit) in _PINNED_SHEETS:
        return _pinned_sheet(name, commit)
    if (name, commit) != _HGTSEQ:
        return None
    from runner.sheetgen import Generated

    header = ('sample', 'group', 'input1', 'input2')
    rows = tuple({'sample': sample, 'group': 'test',
                  'input1': _HGT_BASE + f'fastq/{sample}_1.fastq.gz',
                  'input2': _HGT_BASE + f'fastq/{sample}_2.fastq.gz'}
                 for sample in ('testsample01', 'testsample02', 'testsample03'))
    return Generated(text=_csv(header, rows), suffix='.csv', header=header, rows=rows, files=(),
                     id_column='sample', summary='Prepared the immutable historical HGTseq demo '
                     'samplesheet: 3 named samples, 3 paired rows.', notes=(),
                     record={'version': 1, 'kind': 'bundled_demo_fixture', 'pipeline': name,
                             'pipeline_commit': commit, 'data_commit': _HGT_DATA,
                             'samples': 3, 'rows': 3, 'paired_end': 3, 'single_end': 0,
                             'files': 0, 'sources': ['bundled:runner.demo_defaults/hgtseq']})


def _bactmap_sheet(name: str, commit: str):
    from runner.sheetgen import Generated

    header = ('sample', 'fastq_1', 'fastq_2')
    rows = tuple({'sample': sample,
                  'fastq_1': _BACTMAP_BASE + f'illumina/{sample}_1.fastq.gz',
                  'fastq_2': _BACTMAP_BASE + f'illumina/{sample}_2.fastq.gz'}
                 for sample in ('ERR2172265', 'ERR2172266', 'ERR2172267'))
    return Generated(text=_csv(header, rows), suffix='.csv', header=header, rows=rows, files=(),
                     id_column='sample', summary='Prepared the immutable Bactmap demo '
                     'samplesheet: 3 named paired samples with the matched NCTC13799 reference.',
                     notes=(), record={
                         'version': 1, 'kind': 'bundled_demo_fixture', 'pipeline': name,
                         'pipeline_commit': commit, 'data_commit': _BACTMAP_DATA,
                         'samples': 3, 'rows': 3, 'paired_end': 3, 'single_end': 0, 'files': 0,
                         'row_roles': {row['sample']: 'matched_paired_sample' for row in rows},
                         'validation_contract': {
                             'scope': 'paired_bundled_fixture_only',
                             'source': 'bin/check_samplesheet.py', 'sha256': _BACTMAP_CHECKER},
                         'sources': ['bundled:runner.demo_defaults/bactmap']})


def _fastqrepair_sheet(name: str, commit: str):
    from runner.sheetgen import Generated

    base = f'https://raw.githubusercontent.com/nf-core/test-datasets/{_FASTQ_DAMAGE}/testdata/'
    header = ('sample', 'fastq_1', 'fastq_2')
    rows = (
        {'sample': 'test_30reads', 'fastq_1': base + 'test_30reads_R1.fastq.gz',
         'fastq_2': base + 'test_30reads_R2.fastq.gz'},
        {'sample': 'test_empty_file', 'fastq_1': base + 'empty_file.fastq', 'fastq_2': ''},
        {'sample': 'test_30reads_2', 'fastq_1': base + 'test_30reads_R2.fastq.gz', 'fastq_2': ''},
        {'sample': 'paired_control', 'fastq_1': _HGT_BASE + 'fastq/testsample01_1.fastq.gz',
         'fastq_2': _HGT_BASE + 'fastq/testsample01_2.fastq.gz'})
    return Generated(text=_csv(header, rows), suffix='.csv', header=header, rows=rows, files=(),
                     id_column='sample', summary='Prepared the immutable FastQRepair demo '
                     'samplesheet: 3 original damage cases plus a genuine paired control.',
                     notes=(), record={
                         'version': 1, 'kind': 'bundled_demo_fixture', 'pipeline': name,
                         'pipeline_commit': commit,
                         'data_commits': {'damage_cases': _FASTQ_DAMAGE,
                                          'paired_control': _HGT_DATA},
                         'samples': 4, 'rows': 4, 'paired_end': 2, 'single_end': 2, 'files': 0,
                         'row_roles': {'test_30reads': 'damaged_pair',
                                       'test_empty_file': 'empty_single_end',
                                       'test_30reads_2': 'damaged_single_end',
                                       'paired_control': 'paired_conservation_control'},
                         'sources': ['bundled:runner.demo_defaults/fastqrepair']})


def _bam(name: str) -> str:
    return (f'{_TEST_DATA}{_BAMTOFASTQ_DATA}/test-datasets/data/genomics/homo_sapiens/illumina/'
            f'bam/{name}')


def _genome(name: str) -> str:
    return f'{_TEST_DATA}{_CREATETAXDB_DATA}/data/fasta/{name}' if name else ''


# The release's own demo sheets, row for row, with each moving data URL replaced by the same file
# at an immutable commit: (data commit, header, rows, what the rows are).
_PINNED_SHEETS = {
    _BAMTOFASTQ: (_BAMTOFASTQ_DATA, ('sample_id', 'mapped', 'index', 'file_type'), tuple(
        {'sample_id': sample, 'mapped': _bam(f'{sample}.paired_end.sorted.bam'),
         'index': _bam(f'{sample}.paired_end.sorted.bam.bai'), 'file_type': 'bam'}
        for sample in ('test', 'test2')), '2 indexed paired-end BAMs'),
    _FUNCSCAN: (_FUNCSCAN_DATA, ('sample', 'fasta'), tuple(
        {'sample': sample, 'fasta': f'{_TEST_DATA}{_FUNCSCAN_DATA}/{sample}.fasta.gz'}
        for sample in ('sample_1', 'sample_2')), '2 contig FASTA samples'),
    _CREATETAXDB: (_CREATETAXDB_DATA, ('id', 'taxid', 'fasta_dna', 'fasta_aa'), tuple(
        {'id': genome, 'taxid': taxid, 'fasta_dna': _genome(dna), 'fasta_aa': _genome(aa)}
        for genome, taxid, dna, aa in (
            ('Human_Mitochondrial_genome', '9606', 'chrMT.fna', ''),
            ('SARS-CoV-2_genome', '694009', 'GCA_011545545.1_ASM1154554v1_genomic.fna.gz',
             'GCA_011545545.1_ASM1154554v1_genomic.faa.gz'),
            ('Bacteroides_fragilis_genome', '817', 'GCF_016889925.1_ASM1688992v1_genomic.fna.gz',
             'GCF_016889925.1_ASM1688992v1_genomic.faa.gz'),
            ('Candidatus_portiera_aleyrodidarum_genome', '91844',
             'GCF_000292685.1_ASM29268v1_genomic.fna', 'GCF_000292685.1_ASM29268v1_genomic.faa'),
            ('Haemophilus_influenzae_genome', '727', 'GCF_900478275.1_34211_D02_genomic.fna',
             'GCF_900478275.1_34211_D02_genomic.faa'),
            ('Streptococcus_agalactiae_genome', '1311', '',
             'GCF_002881355.1_ASM288135v1_genomic.faa'))), '6 reference genomes'),
}


def _pinned_sheet(name: str, commit: str):
    from runner.sheetgen import Generated

    data, header, rows, what = _PINNED_SHEETS[(name, commit)]
    return Generated(text=_csv(header, rows), suffix='.csv', header=header, rows=rows, files=(),
                     id_column=header[0], summary=f'Prepared the immutable {name} demo '
                     f'samplesheet: {what} from test-datasets commit {data[:12]}.',
                     notes=(), record={'version': 1, 'kind': 'bundled_demo_fixture',
                                       'pipeline': name, 'pipeline_commit': commit,
                                       'data_commit': data, 'rows': len(rows), 'files': 0,
                                       'sources': [f'bundled:runner.demo_defaults/{name}']})
