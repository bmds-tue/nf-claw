"""Format-aware comparisons must retain all alignments, VCF fields and multiplicities."""
import hashlib
import json

import pytest

from test_scientific import assess, contract, run_dir

pysam = pytest.importorskip('pysam')


def bam(root, lines, *, header=None):
    path = root / 'reads.bam'
    header = header or {'HD': {'VN': '1.6'}, 'SQ': [{'SN': 'chr1', 'LN': 1000}],
                        'RG': [{'ID': 'rg1', 'SM': 'sample_A'}]}
    with pysam.AlignmentFile(path, 'wb', header=header) as out:
        for line in lines:
            out.write(pysam.AlignedSegment.fromstring(line, out.header))
    (root / 'provenance/outputs.sha256').write_text(
        f'{hashlib.sha256(path.read_bytes()).hexdigest()}  reads.bam\n')
    return path


MAPPED = 'mapped\t0\tchr1\t10\t60\t4M\t*\t0\t0\tACGT\tIIII\tRG:Z:rg1\tNM:i:0'
UNMAPPED = 'unmapped\t4\t*\t0\t0\t*\t*\t0\t0\tTGCA\t####\tRG:Z:rg1'


def bam_contract(tmp_path, **extra):
    return contract(tmp_path, [{'path': 'reads.bam', 'format': 'bam',
        'coordinates': '0-based, half-open', 'expected_samples': ['sample_A'], **extra}])


def test_bam_includes_unmapped_reads_and_preserves_duplicate_multiplicity(tmp_path):
    a, b = run_dir(tmp_path, 'a', {}), run_dir(tmp_path, 'b', {})
    bam(a, [MAPPED, UNMAPPED, MAPPED])
    bam(b, [UNMAPPED, MAPPED, MAPPED])
    spec = bam_contract(tmp_path)
    assert assess(b, spec, a)['passed']
    bam(b, [MAPPED, MAPPED])
    assert not assess(b, spec, a)['passed']
    bam(b, [MAPPED, UNMAPPED])
    assert not assess(b, spec, a)['passed']


@pytest.mark.parametrize('replacement', [
    MAPPED.replace('\t10\t', '\t11\t'), MAPPED.replace('NM:i:0', 'NM:i:1'),
    MAPPED.replace('IIII', 'IIIH'), MAPPED.replace('ACGT', 'ACGA'),
    MAPPED.replace('mapped\t0', 'mapped\t256')])
def test_bam_preserves_coordinates_tags_qualities_sequences_and_flags(tmp_path, replacement):
    a, b = run_dir(tmp_path, 'a', {}), run_dir(tmp_path, 'b', {})
    bam(a, [MAPPED])
    bam(b, [replacement])
    assert not assess(b, bam_contract(tmp_path), a)['passed']


def test_bam_resolves_reference_names_independently_of_header_numeric_ids(tmp_path):
    a, b = run_dir(tmp_path, 'a', {}), run_dir(tmp_path, 'b', {})
    header = {'HD': {'VN': '1.6'}, 'SQ': [{'SN': 'chr1', 'LN': 1000}, {'SN': 'chr2', 'LN': 1000}],
              'RG': [{'ID': 'rg1', 'SM': 'sample_A'}]}
    bam(a, [MAPPED], header=header)
    header['SQ'].reverse()
    bam(b, [MAPPED], header=header)
    assert assess(b, bam_contract(tmp_path), a)['passed']


def test_bam_sample_and_reference_headers_are_not_ignored(tmp_path):
    a, b = run_dir(tmp_path, 'a', {}), run_dir(tmp_path, 'b', {})
    bam(a, [MAPPED])
    bam(b, [MAPPED], header={'HD': {'VN': '1.6'}, 'SQ': [{'SN': 'chr1', 'LN': 999}],
                            'RG': [{'ID': 'rg1', 'SM': 'sample_A'}]})
    assert not assess(b, bam_contract(tmp_path), a)['passed']


VCF_HEADER = '''##fileformat=VCFv4.3
##contig=<ID=chr1,length=1000>
##FILTER=<ID=PASS,Description="All filters passed">
##INFO=<ID=END,Number=1,Type=Integer,Description="End position">
##INFO=<ID=DP,Number=1,Type=Integer,Description="Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tA\tB
'''
VARIANT = 'chr1\t11\tv1\tA\t<DEL>\t30\tPASS\tEND=20;DP=10\tGT:DP\t0|1:5\t1/1:5\n'


def vcf_spec(tmp_path, **extra):
    return contract(tmp_path, [{'path': 'variants.vcf', 'format': 'vcf',
        'coordinates': '1-based, closed', 'expected_samples': ['A', 'B'], **extra}])


def test_vcf_field_order_is_independent_but_genotypes_stay_associated_with_samples(tmp_path):
    a = run_dir(tmp_path, 'a', {'variants.vcf': VCF_HEADER + VARIANT})
    b = run_dir(tmp_path, 'b', {'variants.vcf': VCF_HEADER.replace('\tA\tB', '\tB\tA') +
        VARIANT.replace('END=20;DP=10', 'DP=10;END=20').replace('0|1:5\t1/1:5', '1/1:5\t0|1:5')})
    assert assess(b, vcf_spec(tmp_path), a)['passed']
    (b / 'variants.vcf').write_text(VCF_HEADER + VARIANT.replace('0|1:5\t1/1:5', '1/1:5\t0|1:5'))
    assert not assess(b, vcf_spec(tmp_path), a)['passed']


@pytest.mark.parametrize('replacement', [
    VARIANT.replace('END=20', 'END=21'), VARIANT.replace('\tPASS\t', '\t.\t'),
    VARIANT.replace('0|1', '0/1'), VARIANT.replace('DP=10', 'DP=11'),
    VARIANT.replace('\t30\t', '\t31\t'), VARIANT + VARIANT])
def test_vcf_preserves_span_filter_phasing_info_qual_and_duplicates(tmp_path, replacement):
    a = run_dir(tmp_path, 'a', {'variants.vcf': VCF_HEADER + VARIANT})
    b = run_dir(tmp_path, 'b', {'variants.vcf': VCF_HEADER + replacement})
    assert not assess(b, vcf_spec(tmp_path), a)['passed']


def test_vcf_mixed_polyploid_phasing_is_preserved(tmp_path):
    original = VARIANT.replace('0|1:5', '0|1/1:5')
    a = run_dir(tmp_path, 'a', {'variants.vcf': VCF_HEADER + original})
    b = run_dir(tmp_path, 'b', {'variants.vcf': VCF_HEADER + original.replace('0|1/1', '0/1|1')})
    assert not assess(b, vcf_spec(tmp_path), a)['passed']


@pytest.mark.parametrize('quality,valid', [('30', True), ('.', True), ('nan', False),
                                          ('inf', False), ('-inf', False)])
@pytest.mark.parametrize('comparative', [False, True])
def test_vcf_quality_requires_a_finite_value_or_missing_marker(tmp_path, quality, valid,
                                                              comparative):
    body = VCF_HEADER + VARIANT.replace('\t30\t', f'\t{quality}\t')
    candidate = run_dir(tmp_path, 'candidate', {'variants.vcf': body})
    original = run_dir(tmp_path, 'original', {'variants.vcf': body}) if comparative else None
    result = assess(candidate, vcf_spec(tmp_path), original)
    assert result['passed'] is valid
    if not valid:
        assert 'QUAL' in str(result['artifacts'][0]['issues'])
        assert 'finite' in str(result['artifacts'][0]['issues'])


def test_header_ignores_are_explicit_reasoned_and_cannot_hide_scientific_declarations(tmp_path):
    from runner.errors import NfclawError
    a = run_dir(tmp_path, 'a', {'variants.vcf': VCF_HEADER + VARIANT})
    b = run_dir(tmp_path, 'b', {'variants.vcf': VCF_HEADER.replace(
        '##fileformat=VCFv4.3', '##fileformat=VCFv4.3\n##fileDate=20261027') + VARIANT})
    assert not assess(b, vcf_spec(tmp_path), a)['passed']
    result = assess(b, vcf_spec(tmp_path, ignore_header_fields={
        'fileDate': 'Recorded launch date, not a scientific field'}), a)
    assert result['passed']
    assert result['artifacts'][0]['ignored_header_fields'] == {
        'fileDate': 'Recorded launch date, not a scientific field'}
    with pytest.raises(NfclawError):
        assess(b, vcf_spec(tmp_path, ignore_header_fields={'INFO': 'Hide changed depth'}), a)


def test_bam_contract_does_not_accept_sam_renamed_as_bam(tmp_path):
    a = run_dir(tmp_path, 'a', {'reads.bam': '@HD\tVN:1.6\n@SQ\tSN:chr1\tLN:1000\n' +
                                          MAPPED + '\n'})
    assert not assess(a, bam_contract(tmp_path))['passed']


def test_missing_optional_adapter_is_unverified_not_passing(tmp_path, monkeypatch):
    import builtins
    a = run_dir(tmp_path, 'a', {})
    bam(a, [MAPPED])
    original_import = builtins.__import__

    def unavailable(name, *args, **kwargs):
        if name == 'pysam':
            raise ImportError('test missing optional adapter')
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', unavailable)
    result = assess(a, bam_contract(tmp_path))
    assert not result['passed']
    assert 'scientific' in json.dumps(result['artifacts'][0]['issues'])


@pytest.mark.parametrize('field', ['INFO', 'FORMAT'])
def test_vcf_compares_decoded_float_bits_beyond_rendered_precision(tmp_path, field):
    header = VCF_HEADER.replace('#CHROM',
        f'##{field}=<ID=AF,Number=1,Type=Float,Description="Allele fraction">\n#CHROM')
    left = VARIANT.replace('DP=10', 'DP=10;AF=0.12345671') if field == 'INFO' else (
        VARIANT.replace('GT:DP', 'GT:DP:AF').replace('0|1:5', '0|1:5:0.12345671')
        .replace('1/1:5', '1/1:5:0.12345671'))
    right = left.replace('0.12345671', '0.12345672')
    a = run_dir(tmp_path, 'a', {'variants.vcf': header + left})
    b = run_dir(tmp_path, 'b', {'variants.vcf': header + right})
    with pysam.VariantFile(a / 'variants.vcf') as f, pysam.VariantFile(b / 'variants.vcf') as g:
        x, y = next(f), next(g)
        assert (x.info['AF'] != y.info['AF'] if field == 'INFO'
                else x.samples['A']['AF'] != y.samples['A']['AF'])
    assert not assess(b, vcf_spec(tmp_path), a)['passed']


@pytest.mark.parametrize('field', ['INFO', 'FORMAT'])
def test_vcf_declared_cardinality_must_match_values(tmp_path, field):
    body = VARIANT.replace('DP=10', 'DP=10,11') if field == 'INFO' else (
        VARIANT.replace('0|1:5', '0|1:5,6'))
    root = run_dir(tmp_path, 'a', {'variants.vcf': VCF_HEADER + body})
    assert not assess(root, vcf_spec(tmp_path))['passed']


@pytest.mark.parametrize('field', ['INFO', 'FORMAT'])
def test_vcf_missing_vectors_still_have_declared_cardinality(tmp_path, field):
    body = VARIANT.replace('DP=10', 'DP=.,.') if field == 'INFO' else (
        VARIANT.replace('0|1:5', '0|1:.,.'))
    root = run_dir(tmp_path, 'a', {'variants.vcf': VCF_HEADER + body})
    assert not assess(root, vcf_spec(tmp_path))['passed']


@pytest.mark.parametrize('counts,valid', [('30,26|6,9', True), ('30,26|6', False),
                                       ('30,26|-6,9', False), ('30,26', False)])
def test_explicit_gatk_strand_table_encoding_validates_each_allele(tmp_path, counts, valid):
    header = VCF_HEADER.replace('#CHROM',
        '##INFO=<ID=AS_SB_TABLE,Number=1,Type=String,Description="GATK strand counts">\n#CHROM')
    root = run_dir(tmp_path, 'a', {'variants.vcf': header + VARIANT.replace(
        'DP=10', f'DP=10;AS_SB_TABLE={counts}')})
    result = assess(root, vcf_spec(tmp_path, field_encodings={
        'INFO/AS_SB_TABLE': 'gatk-strand-counts'}))
    assert result['passed'] is valid


def test_large_vcf_headers_compare_exactly_without_expanding_the_report(tmp_path):
    declarations = ''.join(f'##INFO=<ID=EXTRA_{n},Number=1,Type=Integer,Description="Extra {n}">\n'
                           for n in range(1000))
    header = VCF_HEADER.replace('#CHROM', declarations + '#CHROM')
    a = run_dir(tmp_path, 'a', {'variants.vcf': header + VARIANT})
    b = run_dir(tmp_path, 'b', {'variants.vcf': header + VARIANT})
    result = assess(b, vcf_spec(tmp_path), a)
    assert result['passed']
    assert len(json.dumps(result)) < 25000
    measured = result['artifacts'][0]['replay']['header']
    assert len(measured['sha256']) == 64
    (b / 'variants.vcf').write_text(header.replace('Description="Extra 999"',
                                                  'Description="Changed meaning"') + VARIANT)
    assert not assess(b, vcf_spec(tmp_path), a)['passed']
