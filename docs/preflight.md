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

## Wrapper schema subset

| Input or rule | What the wrapper checks | What remains for the pinned pipeline/plugin |
|---|---|---|
| Explicit parameters | Known names; declared string, boolean, integer and number types; enums with exact JSON numeric identity; string patterns/lengths and numeric bounds. Required values without defaults are checked when not deferred to a profile/handoff. | Effective profile/config values, nested object/array constraints, general composition and conditional validation. |
| Local CSV/TSV | Parsing, duplicate headers, required columns/nonempty values, extra fields, supported scalar/pattern/range constraints, literal safe identifiers and declared local paths. | Unimplemented schema keywords and analysis-specific consistency. |
| Handwritten CSV/TSV relationships | Supported `dependentRequired` rules and extracted `anyOf` dependency groups, using nonempty-cell semantics. | General branch evaluation, `oneOf`/`anyOf` required-group exclusivity, cross-row `uniqueEntries`, arbitrary predicates, `if`/`then`/`else` and nested rules. |
| Generated sheets and handoff headers | Generation additionally applies its extracted required column groups and `uniqueEntries` tuples; handoff headers check which declared groups can be supplied. | These checks are not equivalent to full row-level JSON Schema evaluation. A supplied handwritten table does not receive every generation-only check. |
| Local JSON/YAML samplesheets | Flat arrays of objects receive declared identifier and local-file safety checks; duplicate mapping keys are rejected. YAML needs the optional `yaml` dependency. | CSV/TSV required-field, scalar, relationship and uniqueness validation is not equivalently implemented for serialized rows. Nested structures and the complete format schema require runtime validation. |
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
