# Scientific output contracts

`nfclaw assess` checks explicit expectations after a run. It returns JSON and exits nonzero if
any declared artifact, sample, format, binding or comparison fails. It does not infer completeness
from the process exit status. Existing `verify`, `verify --strict` and
`verify --require-environment` keep their separate file/namespace/environment behavior.

```bash
pip install -e '.[scientific]'
nfclaw assess results/hgtseq.replay --against results/hgtseq \
  --contract runner/output_contracts/hgtseq-1.1.0-historical-demo.json
```

Omit `--against` to check one run's requirements. With `--against`, the selected original files
must still match their recorded `provenance/outputs.sha256` before their contents can be a
reference. Candidate files are always read live. Both sides are hashed again after parsing.
These before/after observations do not establish continuous immutability.

The BAM/VCF and H5AD adapters are optional. h5py 3.16 has no Python 3.15 wheel: installation on
that interpreter needs a source build with HDF5 development headers/libraries (and pkg-config, or
explicit HDF5 include/library paths). The server's Python 3.15 adapter tests passed with a private
HDF5 1.10.10 build environment. CI prepares HDF5 on Linux 3.15; macOS 3.15 tests the runner and
BAM/VCF adapters, while its H5AD lane awaits an available wheel. Other CI Python versions install
all adapters. This describes configured CI scope, not a claim that macOS was executed on denbi.

The version-1 contract contains `name`, `version: 1`, a nonempty `artifacts` list, and an optional
`pipeline` binding with an exact `name`, 40-character `commit`, and explicit `params` conditions.
Unknown or duplicate fields are refused. Parameter conditions preserve JSON types (false is not
zero), and parameter bytes must match `configs.sha256`. Profile/config defaults absent from
the recorded params file cannot be bound through a parameter condition.

In comparative mode the binding applies **only to the recorded original**. The candidate's
software and parameters remain unverified: passing means its selected content satisfies those
expectations, not that it ran the same pipeline/environment. Use the existing environment
verification separately. Single-run assessment requires its own binding records.

Each artifact names one exact relative `path` and a supported `format`. It may declare
`min_records`, `expected_records` and a `coordinates` description. Missing, external-link,
nonregular, malformed or unsupported artifacts fail. Internal links must resolve inside the run.
Scratch SQLite files are created outside both runs; set `TMPDIR` to another writable filesystem
if necessary. Large record inventories use disk, while table rows, individual sequence lines,
headers and H5AD axis identifiers still need memory. Reports cap mismatch examples and list how
many result files were not assessed. No unmatched result is implicitly accepted as scientifically
validated. The contract SHA-256 and comparator/adapter versions identify the assessment.
Exact BAM/VCF header comparison uses canonical header digests in the report; thousands of
declarations are not repeated in its JSON. The complete header remains in the selected data file.

| Format | Required declarations and exact comparison scope |
| --- | --- |
| `table` | `delimiter` is comma or tab; `columns` lists the complete unique header; `key` lists unique row-key columns; `numeric` lists finite decimal columns. Header/row ordering may change; keys and every other cell remain exact. |
| `fasta` | Unique nonempty identifiers and nonempty sequences. Exact case-preserved sequences and descriptions per ID; line wrapping and sequence order may change. Reports sequence count, total length and N50. No sequence normalization or assembly-quality inference. |
| `bam` | `coordinates: "0-based, half-open"`. All records, including unmapped/nonprimary/duplicate-marked reads; reference names, flags, CIGAR, positions, mate fields, sequence, quality and typed tags. Record order may change, multiplicity may not. Headers are compared; reference-byte identity is unverified. CRAM and indexing/reference downloads are unsupported. |
| `vcf` | `coordinates: "1-based, closed"`. HTSlib-decoded variants, spans/END, alleles, ID, QUAL, FILTER, typed INFO/FORMAT values, sample association and genotype phase separators. Records may reorder; duplicates remain significant. No allele normalization or biological-equivalence inference. |
| `h5ad_matrix` | Explicit `matrix: "X"` or `"layers/name"`, `expected_cells`, `expected_genes`, `axis_policy: "exact"` or `"subset"`, and boolean `integer`/`nonnegative` requirements. Dense/CSR/CSC selected matrix values compare exactly by unique cell/gene identity; explicit/implicit zeros agree. All annotations, embeddings, graphs, raw, uns and unselected matrices remain out of scope. |

Tables can require sample columns with `sample_columns: ["A", "B"]`, or exact row-membership
with `sample_column: "sample_id", expected_samples: ["A", "B"]`. Every artifact is assessed
separately; samples found in one file do not fill omissions in another. Declare all matrix
columns, not just a convenient subset. BAM `expected_samples` checks sample names observed through
record read groups; records without an applicable read group cannot establish that identity.
VCF `expected_samples` checks the sample columns, not the presence of alternate calls per sample.

Table tolerances default to zero. To permit a justified difference in a named numeric column:

```json
"tolerances": {
  "abundance": {"absolute": "0.000001", "relative": "0", "reason": "Documented output precision"}
}
```

The rule is `abs(a-b) <= absolute + relative * max(abs(a), abs(b))`, using exact rational
arithmetic from finite decimals, without the ambient Decimal rounding context. Decimal exponents
outside +/-10000 are unsupported. Nonzero tolerances need a reason; no tolerances apply to BAM,
VCF, FASTA or H5AD matrices. A table may explicitly exclude a non-scientific column with
`ignore_columns: {"": "Pandas positional index; stable keys are declared separately"}`. Key,
numeric and sample-identity columns cannot be excluded, and the exclusion is reported.

BAM can explicitly exclude `PG`/`CO` header records with a reason. VCF can explicitly exclude
named metadata header records, but cannot exclude contig, INFO, FORMAT, FILTER, reference or
fileformat declarations. Every exclusion is reported. Numeric VCF values retain decoded bits,
including INFO/FORMAT values whose shorter printed strings would otherwise hide differences.
HTSlib/BCF precision applies; this is not arbitrary textual-decimal identity. Supported field
cardinalities are fixed, A, R, variable (`.`), and FORMAT G with known genotype ploidy. Unsupported
cardinalities, undeclared fields and nonfinite numeric data fail. A single missing value is allowed;
an explicitly supplied missing vector must still have the correct length.

GATK's `AS_SB_TABLE` deliberately serializes per-allele forward/reverse counts with commas and
pipes inside a `Number=1,Type=String` annotation. A VCF contract can explicitly declare
`field_encodings: {"INFO/AS_SB_TABLE": "gatk-strand-counts"}`. This validates two nonnegative
integer counts per allele and compares the full decoded annotation; it does not ignore the field
or relax any other declaration. See the
[GATK encoder/parser](https://github.com/broadinstitute/gatk/blob/master/src/main/java/org/broadinstitute/hellbender/tools/walkers/annotator/allelespecific/AS_StrandBiasTest.java)
and [VCF specification](https://samtools.github.io/hts-specs/VCFv4.5.pdf).

H5AD checks the declared AnnData/dataframe/array encodings and axis/matrix dimensions. Sparse
pointers, bounds, value arrays and duplicate coordinates are checked. Selected external links,
soft links, external-storage datasets and virtual datasets are refused before reading their data.
See the [AnnData format](https://anndata.readthedocs.io/en/stable/fileformat-prose.html).

## Shipped contracts and coverage

| Contract | Source/branch and established scope | Explicit limits |
| --- | --- | --- |
| [HGTseq historical demo](../runner/output_contracts/hgtseq-1.1.0-historical-demo.json) | Exact 1.1.0 source, immutable matched references, expected paths for testsample01/02/03, nonempty sorted BAMs and exact decoded replay comparison. | These BAMs have no read-group sample labels; identity is the explicitly required per-sample path. No HGT-inference accuracy, classifier, plot or report contract. |
| [Tumourevo tiny demo](../runner/output_contracts/tumourevo-1.0.0-demo.json) | Exact 1.0.0 source, intended `2:3` grid, three keyed PyClone input tables with both expected B/C samples and the known-answer control's 630/626/429 rows, plus six filtered VCFs. Only the declared positional dataframe index and bcftools command metadata are excluded. | The row counts are fixture regression expectations, not biological truth. Joint MS VCFs retain four cohort sample columns; SS/SS_nobam each retain the selected tumour and normal. This does not validate inferred trees, fitted signatures, CNAqc accuracy, all outputs or another input cohort. The upstream test profile's remaining implicit remote defaults are not authenticated by parameter binding. |

Other pins/branches still need their own reviewed output contracts. The generic adapters and two
selected fixture contracts do not establish scientific validation for all 95 pipelines. In
particular H5AD currently has adversarial format controls, not a newly executed biological pipeline
benchmark. Exact assembly comparison intentionally flags a lost Flye contig; changing RNG output,
reports or filenames does not become acceptable merely because it is variable.
