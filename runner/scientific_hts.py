"""Exact HTSlib-decoded BAM/VCF records, with explicitly scoped header exclusions.

No normalization, reference fetching, indexing, read filtering or variant equivalence inference.
Record hashes are SHA-256 multisets: order may vary, duplicate multiplicity may not.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import struct


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'))


def _typed(value):
    if isinstance(value, float):
        return {'float64_bits': struct.pack('>d', value).hex()}
    if isinstance(value, dict):
        return {key: _typed(item) for key, item in value.items()}
    if value is not None and not isinstance(value, (str, int)):
        return [_typed(item) for item in value]
    return value


def _header(value):
    data = _json(value).encode()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'canonical_bytes': len(data)}


def _record(db, side, value):
    key = _json(hashlib.sha256(_json(value).encode()).hexdigest())
    db.execute(f'INSERT INTO {side} VALUES (?, ?, 0) '
               'ON CONFLICT(key) DO UPDATE SET value=CAST(CAST(value AS INTEGER)+1 AS TEXT)',
               (key, '1'))


def _coverage(expected, observed, source):
    if expected is None or set(expected) == set(observed):
        return []
    missing, extra = set(expected) - set(observed), set(observed) - set(expected)
    return [f'{source} sample coverage differs: {len(missing)} missing '
            f'(examples {sorted(missing)[:20]}); {len(extra)} unexpected '
            f'(examples {sorted(extra)[:20]})']


def _cardinality(value, declaration, alleles, ploidy=None):
    values = value if isinstance(value, tuple) else (value,)
    if values == (None,):
        return
    number, kind = declaration.number, declaration.type
    if kind == 'Flag':
        if number != 0 or type(value) is not bool:
            raise ValueError('VCF Flag field has invalid cardinality/type')
        return
    if number == 'A':
        expected = alleles - 1
    elif number == 'R':
        expected = alleles
    elif number == 'G':
        if ploidy is None or ploidy < 1:
            raise ValueError('VCF Number=G needs a known sample genotype ploidy')
        expected = math.comb(alleles + ploidy - 1, ploidy)
    elif number == '.':
        expected = len(values)
    elif isinstance(number, int) and number >= 1:
        expected = number
    else:
        raise ValueError('unsupported VCF field cardinality')
    if len(values) != expected:
        raise ValueError('VCF values violate declared field cardinality')
    for item in values:
        if item is None:
            continue
        if kind == 'Integer' and type(item) is not int:
            raise ValueError('VCF Integer field has invalid type')
        if kind == 'Float' and (not isinstance(item, (int, float)) or not math.isfinite(item)):
            raise ValueError('VCF Float field must contain finite numeric values')
        if kind in ('String', 'Character') and not isinstance(item, str):
            raise ValueError('VCF text field has invalid type')
        if kind == 'Character' and len(item) != 1:
            raise ValueError('VCF Character field must contain single characters')


def _bam(stream, item, db, side, pysam):
    count, observed = 0, set()
    with pysam.AlignmentFile(stream, 'rb', duplicate_filehandle=True) as source:
        if not source.is_bam:
            raise ValueError('bam contract requires detected BAM data, not SAM/CRAM')
        header = source.header.to_dict()
        groups = {}
        for record in header.get('RG', []):
            if not record.get('ID') or record['ID'] in groups:
                raise ValueError('missing or duplicate BAM read-group ID')
            groups[record['ID']] = record.get('SM')
        references = [record.get('SN') for record in header.get('SQ', [])]
        if None in references or len(references) != len(set(references)):
            raise ValueError('missing or duplicate BAM reference name')
        for field in item.get('ignore_header_fields', {}):
            header.pop(field, None)
        header = {key: sorted(value, key=_json) if isinstance(value, list) else value
                  for key, value in header.items()}
        for read in source.fetch(until_eof=True):
            tags = read.get_tags(with_value_type=True)
            if len({tag[0] for tag in tags}) != len(tags):
                raise ValueError('duplicate BAM auxiliary tag')
            if read.has_tag('RG'):
                group = read.get_tag('RG')
                if group not in groups:
                    raise ValueError('BAM record references an undeclared read group')
                if groups[group] is not None:
                    observed.add(groups[group])
            elif item.get('expected_samples'):
                raise ValueError('BAM record has no read group to establish sample identity')
            value = [read.query_name, read.flag, read.reference_name, read.reference_start,
                     read.mapping_quality, read.cigartuples, read.next_reference_name,
                     read.next_reference_start, read.template_length, read.query_sequence,
                     list(read.query_qualities) if read.query_qualities is not None else None,
                     sorted([[tag, kind, _typed(value)] for tag, value, kind in tags], key=_json)]
            _record(db, side, value)
            count += 1
    issues = _coverage(item.get('expected_samples'), observed, 'observed BAM read-group')
    return {'records': count, 'samples': sorted(observed), 'header': _header(header),
            'adapter': f'pysam/{pysam.__version__}',
            'semantics': 'Every decoded alignment, including unmapped and nonprimary records; '
                         'reference names, all flags/fields and typed tags; SHA-256 multiset. '
                         'Reference bytes are not established by the BAM header.'}, issues


def _vcf(stream, item, db, side, pysam):
    count = 0
    with pysam.VariantFile(stream, duplicate_filehandle=True) as source:
        samples = list(source.header.samples)
        ignored = item.get('ignore_header_fields', {})
        header = sorted(str(record).strip() for record in source.header.records
                        if record.key not in ignored)
        header.append(_json({'samples': sorted(samples)}))
        declared_info = set(source.header.info)
        declared_formats = set(source.header.formats)
        declared_filters = set(source.header.filters)
        declared_contigs = set(source.header.contigs)
        for record in source:
            # HTSlib renders decoded values. Keeping each rendered GT string also preserves
            # mixed polyploid phase separators that a tuple plus one phased boolean would lose.
            columns = str(record).rstrip('\r\n').split('\t')
            if len(columns) < 8 or len(columns) != (9 + len(samples) if samples else 8):
                raise ValueError('malformed decoded VCF record columns')
            if record.contig not in declared_contigs:
                raise ValueError('VCF record has an undeclared contig')
            info = columns[7].split(';') if columns[7] != '.' else []
            if len({field.split('=', 1)[0] for field in info}) != len(info):
                raise ValueError('duplicate VCF INFO field')
            if any(field.split('=', 1)[0] not in declared_info for field in info):
                raise ValueError('VCF INFO field lacks a declaration')
            filters = list(record.filter)
            if set(filters) - declared_filters:
                raise ValueError('VCF FILTER field lacks a declaration')
            formats = columns[8].split(':') if samples else []
            if len(formats) != len(set(formats)):
                raise ValueError('duplicate VCF FORMAT field')
            if set(formats) - declared_formats:
                raise ValueError('VCF FORMAT field lacks a declaration')
            associations = {}
            for sample, text in zip(samples, columns[9:], strict=True):
                fields = text.split(':')
                if len(fields) != len(formats):
                    raise ValueError('VCF sample fields do not match FORMAT')
                genotype = record.samples[sample].get('GT')
                for key in formats:
                    if key == 'GT':
                        if any(allele is not None and (allele < 0 or allele >= len(record.alleles))
                               for allele in genotype):
                            raise ValueError('VCF genotype allele index is invalid')
                    else:
                        _cardinality(record.samples[sample][key], source.header.formats[key],
                                     len(record.alleles), len(genotype) if genotype else None)
                associations[sample] = {
                    'values': {key: _typed(record.samples[sample][key]) for key in formats},
                    'GT_phase': dict(zip(formats, fields, strict=True)).get('GT')}
            typed_info = {key: _typed(record.info[key]) for key in record.info}
            for key in record.info:
                declaration = source.header.info[key]
                if key == 'AS_SB_TABLE' and item.get('field_encodings', {}).get(
                        'INFO/AS_SB_TABLE') == 'gatk-strand-counts':
                    raw = record.info[key]
                    if declaration.number != 1 or declaration.type != 'String':
                        raise ValueError('GATK strand-table encoding needs Number=1 Type=String')
                    value = ','.join(raw) if isinstance(raw, tuple) else raw
                    if (not isinstance(value, str) or len(value.split('|')) != len(record.alleles)
                            or any(re.fullmatch(r'[0-9]+,[0-9]+', pair) is None
                                   for pair in value.split('|'))):
                        raise ValueError('GATK strand table needs two nonnegative counts '
                                         'per allele')
                else:
                    try:
                        _cardinality(record.info[key], declaration, len(record.alleles))
                    except ValueError as exc:
                        raise ValueError(f'INFO/{key} at {record.contig}:{record.pos}: {exc}') \
                            from exc
            if any(field.startswith('END=') for field in info):
                typed_info['END'] = record.stop
            _record(db, side, [record.contig, record.start, record.stop, record.id,
                              record.alleles, _typed(record.qual), sorted(filters), typed_info,
                              associations])
            count += 1
    return {'records': count, 'samples': sorted(samples), 'header': _header(header),
            'adapter': f'pysam/{pysam.__version__}',
            'semantics': 'Exact HTSlib-decoded variant records and spans, all INFO/FORMAT values, '
                         'sample associations and phase separators; SHA-256 multiset. '
                         'BCF numeric precision applies; arbitrary textual-decimal identity, '
                         'normalization and biological equivalence are not established.'}, \
        _coverage(item.get('expected_samples'), samples, 'VCF header')


def measure(stream, item, db, side):
    try:
        import pysam
    except ImportError as exc:
        raise ValueError('BAM/VCF assessment needs pip install "nfclaw[scientific]"') from exc
    return (_bam if item['format'] == 'bam' else _vcf)(stream, item, db, side, pysam)
