# Validation scope and samplesheet generation

`nfclaw run --check` prepares a command; it does not execute scientific tasks. Its three
`preflight` lines list checks completed by the wrapper, deferred to workflow launch, and unsupported
by preparation. A real run retains the detailed versioned report as `validation_scope` in
`provenance/run_manifest.json`. Failed preparation reports the failing check through its error;
it does not claim that later checks ran. The report adds no network or engine probes.
Generated tables count as validated local sheets too. A check-only preparation inspects local data
paths but does not read every data file's bytes; `local_data_bytes` stays deferred until a real run
has taken its input snapshots. A successful check can therefore still encounter unreadable data at
launch, and is not a byte-readability guarantee.

---

## Navigation

[Schema Subset](#wrapper-schema-subset) • [Replay Integrity Limits](#replay-integrity-limits) • [Generation Boundaries](#generation-boundaries) • [Support Matrix](#support-matrix-for-the-95-audited-pins) • [Inputs Refused Before Launch](#inputs-refused-before-launch)

---

## Wrapper schema subset

| Input or rule | What the wrapper checks | What remains for the pinned pipeline/plugin |
|---|---|---|
| Explicit parameters | Known names; declared string, boolean, integer and number types; enums with exact JSON numeric identity; string patterns/lengths and numeric bounds. Required values without defaults are checked when not deferred to a profile/handoff. | Effective profile/config values, nested object/array constraints, general composition and conditional validation. |
| Local CSV/TSV | Parsing, duplicate headers, required columns/nonempty values, extra fields, supported scalar/pattern/range constraints, literal safe identifiers and declared local paths. | Unimplemented schema keywords and analysis-specific consistency. |
| Handwritten CSV/TSV relationships | Supported `dependentRequired` rules, extracted `anyOf` dependency groups, necessary required-column sets and scalar `uniqueEntries` tuples, using nonempty-cell semantics. | Full branch evaluation/exclusivity, arbitrary predicates, `if`/`then`/`else` and nested rules. |
| Generated sheets and handoff headers | Generation and supplied rows share supported relationships and uniqueness checks; handoff headers check which declared groups can be supplied. | These checks are not equivalent to full row-level JSON Schema evaluation. |
| Local JSON/YAML samplesheets | Flat arrays of objects receive required-field, supported scalar/pattern/range, relationship, scalar uniqueness, identifier and local-file checks; empty arrays and duplicate mapping keys are rejected. YAML needs the optional `yaml` dependency. | Nested structures, nested equality and the complete format schema require runtime validation. Checking necessary column sets does not establish general branch exclusivity. |
| Headerless accession lists | At least one nonempty value. | Per-accession pattern and service validation. |
| Remote sheets/data; config/profile expressions | Explicit path syntax and declared write separation where values are available. | URL availability, remote inventory/content and resolved profile/config values. A successful check does not establish these. |
| Scientific results | Preparation establishes no result completeness or biological accuracy. | Expected/processed samples, required scientific artifacts, formats and analysis-specific assessments. Exit zero alone does not establish these. |

The supported path formats and exact-source annotations are shared by handwritten tables, generated
tables and handoffs. The [architecture](architecture.md#21-schema-preflight--fast-fail-parameter-validation)
describes their boundaries. Before/after local hashes can detect a lasting change but cannot prove
continuous immutability or establish every byte a task consumed. Implicit indexes, transitive config
includes, Conda environments and task-managed downloads are not comprehensively discovered.

## Replay integrity limits

Source replay integrity currently means the recorded revision and tracked file contents. The
source archive retains executable/nonexecutable permissions when created, but `pipeline.sha256`
does not independently authenticate those mode bits or symlink identities. Tracked symlinks are
archived as their resolved contents; untracked/ignored source files are not archived or comprehensively
judged for runtime significance. These are explicit limits, so a tracked-byte match is not a claim
that every possible filesystem dependency or continuous source state was reproduced.

The three exact-pin [recorded source corrections](source-corrections.md) (Createtaxdb, Funcscan, and Bactmap) use independent regular-file
copies with a separately bound inventory, executable modes and complete directory namespace.
They reject original untracked/ignored files and source symlinks, and verify the actual corrected
copy or extracted archive before/after execution. These stronger checks apply to those corrected
copies; they do not retroactively strengthen ordinary historical bundles or establish continuous
filesystem immutability.

## Generation boundaries

Generation consumes local directories, quoted local globs or explicit local files. Remote dataset
inventories require an explicit samplesheet. File patterns select typed columns; sample names remain
unchanged. Values that files cannot determine still require schema defaults or `--sheet-set`.
A "direct" classification does not promise that every arbitrary filename or mixed layout can be
inferred; orphan mates, duplicate/ambiguous roles and missing assignments are refused.

`_R1`/`_R2` filenames pair directly, with an advisory if the first read names disagree. `_1`/`_2`
pair only when their first read identities establish mates. This inspection examines the first read,
not every record, so it does not establish complete read pairing or FASTQ validity. Zstd read-name
inspection is unavailable: use unambiguous `_R1`/`_R2` names (with an advisory) or a manual sheet.
Unfamiliar naming and mixed layouts may need manual assignment. Unmatched unrelated files may be
ignored with a warning and recorded inventory; inspect the warnings before running.

## Support matrix for the 95 audited pins

This is a fresh classification using the same `sheetgen.plan` as runtime and generated pipeline
skills: **71 direct, 3 requiring column selection, 12 manual, 9 without a consumed samplesheet
schema**. It classifies schemas rather than executing analyses. Each pipeline's generated Inputs
section remains authoritative for assignments and required values. The
[machine-readable inventory](audit/evidence/samplesheet-generation-support.json) records all source
commits, classification time and classifier digest. Regenerate it when pins or generation rules
change; another release may have another contract.

| Pipeline | Generation support | Selection or limitation |
|---|---|---|
| [airrflow](../pipelines/airrflow/skill.md) | Manual sheet | the samplesheet declares no file type nfclaw could match files against (no column's pattern names a file extension) |
| [ampliseq](../pipelines/ampliseq/skill.md) | Direct | fastq_1 + fastq_2 |
| [atacseq](../pipelines/atacseq/skill.md) | Direct | fastq_1 + fastq_2 |
| [bacass](../pipelines/bacass/skill.md) | Choose columns | the samplesheet takes reads in several column groups (R1 + R2; LongFastQ) and file names cannot tell which yours belong in; leave the groups you do not use empty, e.g. --sheet-set LongFastQ= |
| [bacmodel](../pipelines/bacmodel/skill.md) | Direct | fasta, medium_gapseq_csv, medium_carveme_tsv |
| [bactmap](../pipelines/bactmap/skill.md) | No samplesheet schema | No samplesheet schema consumed by this input. |
| [bamtofastq](../pipelines/bamtofastq/skill.md) | Direct | mapped, index |
| [callingcards](../pipelines/callingcards/skill.md) | Direct | fastq_1 + fastq_2 |
| [chipseq](../pipelines/chipseq/skill.md) | Direct | fastq_1 + fastq_2 |
| [circdna](../pipelines/circdna/skill.md) | Direct | fastq_1 + fastq_2 |
| [coproid](../pipelines/coproid/skill.md) | Direct | fastq_1 + fastq_2 |
| [createpanelrefs](../pipelines/createpanelrefs/skill.md) | Direct | bam, bai, cram, crai |
| [createtaxdb](../pipelines/createtaxdb/skill.md) | Direct | fasta_dna, fasta_aa |
| [crisprseq](../pipelines/crisprseq/skill.md) | Direct | fastq_1 + fastq_2 |
| [cutandrun](../pipelines/cutandrun/skill.md) | Direct | fastq_1 + fastq_2 |
| [datasync](../pipelines/datasync/skill.md) | Direct | checksum_md5, checksum_sha |
| [demo](../pipelines/demo/skill.md) | Direct | fastq_1 + fastq_2 |
| [demultiplex](../pipelines/demultiplex/skill.md) | Direct | samplesheet |
| [denovotranscript](../pipelines/denovotranscript/skill.md) | Direct | fastq_1 + fastq_2 |
| [detaxizer](../pipelines/detaxizer/skill.md) | Choose columns | the samplesheet takes reads in several column groups (short_reads_fastq_1 + short_reads_fastq_2; long_reads_fastq_1) and file names cannot tell which yours belong in; leave the groups you do not use empty, e.g. --sheet-set long_reads_fastq_1= |
| [differentialabundance](../pipelines/differentialabundance/skill.md) | Manual sheet | the samplesheet declares no file type nfclaw could match files against (no column's pattern names a file extension) |
| [drop](../pipelines/drop/skill.md) | Direct | RNA_BAM_FILE, RNA_BAI_FILE, DNA_VCF_FILE, DNA_TBI_FILE, GENE_COUNTS_FILE |
| [drugresponseeval](../pipelines/drugresponseeval/skill.md) | No samplesheet schema | No samplesheet schema consumed by this input. |
| [epitopeprediction](../pipelines/epitopeprediction/skill.md) | Direct | filename, germline_vcf |
| [fastqrepair](../pipelines/fastqrepair/skill.md) | Direct | fastq_1 + fastq_2 |
| [fastquorum](../pipelines/fastquorum/skill.md) | Direct | fastq_1 + fastq_2; fastq_3; fastq_4 |
| [fetchngs](../pipelines/fetchngs/skill.md) | Manual sheet | the samplesheet takes one value per line, not data files |
| [funcprofiler](../pipelines/funcprofiler/skill.md) | Direct | fastq_1 + fastq_2 |
| [funcscan](../pipelines/funcscan/skill.md) | Direct | fasta, protein, gbk, gff |
| [genomeassembler](../pipelines/genomeassembler/skill.md) | Manual sheet | the samplesheet declares no file type nfclaw could match files against (no column's pattern names a file extension) |
| [genomeqc](../pipelines/genomeqc/skill.md) | Direct | fastq |
| [hadge](../pipelines/hadge/skill.md) | Direct | bam, barcodes, vcf |
| [hgtseq](../pipelines/hgtseq/skill.md) | Manual sheet | the pinned consumer accepts mixed FASTQ/alignment roles that require an explicit samplesheet |
| [hic](../pipelines/hic/skill.md) | Direct | fastq_1 + fastq_2 |
| [hicar](../pipelines/hicar/skill.md) | Direct | fastq_1 + fastq_2 |
| [hlatyping](../pipelines/hlatyping/skill.md) | Direct | fastq_1 + fastq_2 |
| [isoseq](../pipelines/isoseq/skill.md) | Direct | seq_data, pbi |
| [longraredisease](../pipelines/longraredisease/skill.md) | Direct | file_path |
| [lsmquant](../pipelines/lsmquant/skill.md) | Direct | img_directory, parameter_file |
| [mag](../pipelines/mag/skill.md) | Choose columns | the samplesheet takes reads in several column groups (short_reads_1 + short_reads_2; long_reads) and file names cannot tell which yours belong in; leave the groups you do not use empty, e.g. --sheet-set long_reads= |
| [magmap](../pipelines/magmap/skill.md) | Direct | fastq_1 + fastq_2 |
| [marsseq](../pipelines/marsseq/skill.md) | Direct | fastq_1 + fastq_2 |
| [mcmicro](../pipelines/mcmicro/skill.md) | No samplesheet schema | No samplesheet schema consumed by this input. |
| [metaboigniter](../pipelines/metaboigniter/skill.md) | Direct | msfile |
| [metapep](../pipelines/metapep/skill.md) | Manual sheet | the samplesheet declares no file type nfclaw could match files against (no column's pattern names a file extension) |
| [metatdenovo](../pipelines/metatdenovo/skill.md) | Direct | fastq_1 + fastq_2 |
| [methylong](../pipelines/methylong/skill.md) | Direct | ref |
| [methylseq](../pipelines/methylseq/skill.md) | Direct | fastq_1 + fastq_2 |
| [mhcquant](../pipelines/mhcquant/skill.md) | Direct | ReplicateFileName, Fasta |
| [molkart](../pipelines/molkart/skill.md) | Direct | nuclear_image, spot_table |
| [multiplesequencealign](../pipelines/multiplesequencealign/skill.md) | Direct | fasta, reference, optional_data, template |
| [nanoseq](../pipelines/nanoseq/skill.md) | Manual sheet | group, replicate, barcode, data layout and reference assignments require an explicit samplesheet |
| [nanostring](../pipelines/nanostring/skill.md) | Direct | RCC_FILE |
| [nascent](../pipelines/nascent/skill.md) | Direct | fastq_1 + fastq_2 |
| [oncoanalyser](../pipelines/oncoanalyser/skill.md) | Manual sheet | the samplesheet declares no file type nfclaw could match files against (no column's pattern names a file extension) |
| [pacvar](../pipelines/pacvar/skill.md) | Direct | pbi |
| [pairgenomealign](../pipelines/pairgenomealign/skill.md) | Direct | fasta |
| [pangenome](../pipelines/pangenome/skill.md) | No samplesheet schema | No samplesheet schema consumed by this input. |
| [pathogensurveillance](../pipelines/pathogensurveillance/skill.md) | Direct | path + path_2 |
| [phaseimpute](../pipelines/phaseimpute/skill.md) | Direct | index |
| [phyloplace](../pipelines/phyloplace/skill.md) | No samplesheet schema | No samplesheet schema consumed by this input. |
| [pixelator](../pipelines/pixelator/skill.md) | Direct | fastq_1 + fastq_2 |
| [plasmodiumdrugres](../pipelines/plasmodiumdrugres/skill.md) | No samplesheet schema | No samplesheet schema consumed by this input. |
| [proteinannotator](../pipelines/proteinannotator/skill.md) | Direct | fasta |
| [proteinfamilies](../pipelines/proteinfamilies/skill.md) | Direct | fasta |
| [proteinfold](../pipelines/proteinfold/skill.md) | Direct | fasta |
| [provenancereport](../pipelines/provenancereport/skill.md) | Manual sheet | the samplesheet declares no file type nfclaw could match files against (no column's pattern names a file extension) |
| [rangeland](../pipelines/rangeland/skill.md) | No samplesheet schema | No samplesheet schema consumed by this input. |
| [raredisease](../pipelines/raredisease/skill.md) | Direct | fastq_1 + fastq_2 |
| [readsimulator](../pipelines/readsimulator/skill.md) | Manual sheet | the samplesheet declares no file type nfclaw could match files against (no column's pattern names a file extension) |
| [reportho](../pipelines/reportho/skill.md) | Direct | fasta |
| [ribomsqc](../pipelines/ribomsqc/skill.md) | Direct | raw_file |
| [riboseq](../pipelines/riboseq/skill.md) | Direct | fastq_1 + fastq_2 |
| [rnadnavar](../pipelines/rnadnavar/skill.md) | Direct | fastq_1 + fastq_2 |
| [rnafusion](../pipelines/rnafusion/skill.md) | Direct | fastq_1 + fastq_2 |
| [rnaseq](../pipelines/rnaseq/skill.md) | Direct | fastq_1 + fastq_2 |
| [rnasplice](../pipelines/rnasplice/skill.md) | Direct | fastq_1 + fastq_2 |
| [rnastructurome](../pipelines/rnastructurome/skill.md) | Direct | fastq_1 + fastq_2 |
| [rnavar](../pipelines/rnavar/skill.md) | Direct | fastq_1 + fastq_2 |
| [sarek](../pipelines/sarek/skill.md) | Direct | fastq_1 + fastq_2 |
| [scnanoseq](../pipelines/scnanoseq/skill.md) | Direct | fastq |
| [scrnaseq](../pipelines/scrnaseq/skill.md) | Direct | fastq_1 + fastq_2 |
| [seqinspector](../pipelines/seqinspector/skill.md) | Direct | fastq_1 + fastq_2 |
| [seqsubmit](../pipelines/seqsubmit/skill.md) | No samplesheet schema | No samplesheet schema consumed by this input. |
| [smrnaseq](../pipelines/smrnaseq/skill.md) | Direct | fastq_1 + fastq_2 |
| [sopa](../pipelines/sopa/skill.md) | Manual sheet | the samplesheet declares no file type nfclaw could match files against (no column's pattern names a file extension) |
| [spatialaxe](../pipelines/spatialaxe/skill.md) | Manual sheet | the samplesheet declares no file type nfclaw could match files against (no column's pattern names a file extension) |
| [stableexpression](../pipelines/stableexpression/skill.md) | No samplesheet schema | No samplesheet schema consumed by this input. |
| [taxprofiler](../pipelines/taxprofiler/skill.md) | Direct | fastq_1 + fastq_2 |
| [tumourevo](../pipelines/tumourevo/skill.md) | Direct | vcf, tbi, tumour_alignment, tumour_alignment_index |
| [variantbenchmarking](../pipelines/variantbenchmarking/skill.md) | Direct | test_vcf, test_regions |
| [variantprioritization](../pipelines/variantprioritization/skill.md) | Direct | vcf, cna |
| [viralintegration](../pipelines/viralintegration/skill.md) | Direct | fastq_1 + fastq_2 |
| [viralmetagenome](../pipelines/viralmetagenome/skill.md) | Direct | fastq_1 + fastq_2 |
| [viralrecon](../pipelines/viralrecon/skill.md) | Direct | fastq_1 + fastq_2 |

## Inputs refused before launch

`nfclaw run` refuses these before it creates a lock or writes anything into `--outdir`; the agent
guide gives the one-line rules.

### Output directories and locking

On POSIX systems, `nfclaw run` holds an exclusive non-blocking sibling lock (`.{outdir.name}.nfclaw.lock`) around the run. Overlapping or concurrent runs into the same `--outdir` fail fast with an environment error, preventing race conditions or output corruption. Before creating that lock or any run files, explicit local dependencies and samplesheet data paths are checked against output, work, engine-state and log destinations. Keep execution writes outside consumed directories, including nested aliases and directory glob matches; keep data, pipeline code and configuration outside the output tree. Chain preflight also checks its whole output tree before writing its record. Existing output aliases and hard-linked files are inspected too: a different pathname does not establish different data. Declared work/cache trees retain their staged-read policy; input slots within output trees remain protected even when their symlinks point outside. Boundary refusals preserve input files, directory entries and existing logs.

### Input filenames

Explicit local and remote input path fields and schema-declared path parameters are checked for filenames that pinned tasks could interpret as shell syntax. Unsafe staged basenames (including literal wildcards, whitespace, shell operators and leading `-` or `~`) are refused; choose a safely named copy rather than renaming a scientific sample. Local directories and directory glob matches are inspected recursively, including empty subdirectories; unreadable entries, broken links and cycles are refused. Symlink targets and local glob matches receive the same name check. Unicode letters, digits and combining marks and literal `._-+@%=,:~` characters remain supported (with `~` only internally). Nextflow preserves percent escapes in remote basenames; nfclaw preserves them too. HTTP/FTP query suffixes are excluded from the staged name; standalone fragments remain literal filename characters. Object-store keys such as S3 retain query and fragment characters and receive the literal-name check. Parent directory names are not staged as the input basename, but LF/CR in local input paths or resolved targets are refused because Nextflow can turn them into shell lines. Samplesheet paths crossing a directory symlink with `..` must use an explicit absolute parent: Nextflow's lexical normalization may select different data. Ordinary parent traversal is supported; wildcard parents followed by `..` are refused before resolution. URI schemes must start the value, so a local colon parent remains a checksummed local dependency. The separate run-directory space check still applies, and `--allow-spaces` cannot permit LF/CR in launch, output or work paths. Local `file:` URI inputs must be written as absolute filesystem paths so the same filename and replay-dependency checks apply. Values supplied indirectly through configs/profiles, remote glob inventories and remote file contents remain subject to upstream validation.

Audited output-only directory parameters retain basename checks while excluding unrelated
existing children from input snapshots. These roles are declared in `runner/path_roles.json`
for exact clean source revisions, never inferred from names or descriptions. Whole-path
arguments in audited task scripts also validate parent folders and resolved symlink paths.
HTTP/HTTPS/FTP basenames remain literal even in schema-declared file patterns; object-store
patterns retain their upstream expansion semantics.

### Sample identities

Metadata identifiers (`meta.id`, patient/sample IDs, genome/database names and legacy sample/patient columns) must start with a letter, digit or underscore and contain only letters, digits, combining marks, dots, underscores or hyphens. Upstream tasks use these values in shell commands and filenames. Choose explicit safe aliases for other identifiers; nfclaw never silently renames scientific samples. This preflight applies to CSV/TSV and flat JSON/YAML records; YAML requires `pip install -e ".[yaml]"`. Local path fields in these records must be absolute, including glob patterns, and their content is included in replay dependency checks. Explicitly supplied auxiliary tables such as `--genome-sheet` and `--databases` receive their own schema validation and local-data dependency checks too. Values supplied by profiles/configs and future chain handoffs are validated by Nextflow when available. Nested input structures remain subject to the pinned nf-schema validation.

### Numeric parameter values

Numeric values supplied through CLI flags, JSON/YAML parameter files and chain specs retain their decimal value when nfclaw writes the parameters Nextflow reads. Decimal notation and scientific notation do not round large integers or underflow small nonzero values to zero. Schema enum/boundary comparisons and numeric CSV/TSV column checks use the emitted decimal value. JSON/YAML nested numeric parameters and recorded chain specs retain it too. Integer values beyond Nextflow's signed 64-bit JSON parser range use decimal notation to prevent wraparound. NaN and infinity remain refused. Nextflow, nf-schema and each scientific tool still determine their own supported ranges and arithmetic precision.
