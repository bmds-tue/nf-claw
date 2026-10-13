---
name: raredisease
version: 3.1.2
commit: 83f2699d28bc957e1d3b875da3d96004a818c2c3
---

# raredisease — full parameter reference

nf-core/raredisease pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## alignment_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--aligner` | string |  |  | `bwa`, `bwafastalign`, `bwamem2`, `bwameme`, `sentieon` |  | bwamem2 | Specifies the alignment algorithm to use - available options are 'bwamem2', 'bwa', 'bwameme' and 'sentieon'. |
| `--mbuffer-mem` | integer |  |  |  |  | 8192 | Memory allocated for mbuffer in megabytes (MB) (used by bwameme and bwafastalign) |
| `--min-trimmed-length` | integer |  |  |  |  | 40 | Discard trimmed reads shorter than the given value |
| `--mt-aligner` | string |  |  | `bwa`, `bwamem2`, `sentieon` |  | bwamem2 | Specifies the alignment algorithm to use - available options are 'bwamem2', 'bwa' and 'sentieon'. |
| `--mt-subsample-approach` | string |  |  | `fraction`, `reads` |  | reads | Subsample mitochondria based on fraction of reads or number of reads |
| `--mt-subsample-rd` | integer |  |  |  |  | 150 | Expected coverage to subsample mt alignment to, when mt_subsample_approach is set to fraction |
| `--mt-subsample-reads` | integer |  |  |  |  | 18000 | Expected number of reads to subsample mitochondria to, when mt_subsample_approach is set to reads |
| `--mt-subsample-seed` | integer |  |  |  |  | 30 | Subsampling seed used to influence which subset of mitochondrial reads is kept. Used when mt_subsample_approach is set to fraction |
| `--rmdup` | boolean |  |  |  |  |  | Specifies whether duplicates reads should be removed prior to variant calling. |
| `--samtools-sort-threads` | integer |  |  |  |  | 4 | Number of threads allocated for sorting alignment files (used by bwameme and bwafastalign) |

## analysis_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--analysis-type` | string |  |  | `wgs`, `wes`, `mito` |  | wgs | Specifies which analysis type for the pipeline- either 'wgs', 'wes' or 'mito'. This changes resources consumed and tools used. |
| `--concatenate-snv-calls` | boolean |  |  |  |  |  | Specifies whether to generate a concatenated VCF file containing both nuclear & mitochondrial snv calls |
| `--exclude-alt` | boolean |  |  |  |  |  | After aligning the reads to a reference, remove alignments to alt contigs using samtools view, retaining only primary chromosomes (GRCh37: 1-22,X,Y,MT / GRCh38: chr1-chr22,chrX,chrY,chrM). |
| `--extract-alignments` | boolean |  |  |  |  |  | After aligning the reads to a reference, extract alignments from specific regions/contigs and restrict the analysis to those regions/contigs. |
| `--homoplasmy-af-threshold` | number |  |  |  |  | 1.0 | Allele frequency threshold for mitochondrial variants. Variants with an AF above this threshold will be treated as homoplasmic and assigned a 1/1 genotype. Range 0-1.0. |
| `--ngsbits-samplegender-method` | string |  |  | `xy`, `hetx`, `sry` |  | xy | Method selection for ngs-bits samplegender |
| `--platform` | string |  |  |  |  | illumina | Specifies the platform on which the reads were sequenced. |
| `--restrict-to-contigs` | string |  |  |  |  |  | Can be specified as RNAME[:STARTPOS[-ENDPOS]]. Multiple regions should be seperated by space |
| `--run-mt-for-wes` | boolean |  |  |  |  |  | Specifies whether to run mitochondrial analysis for wes samples |
| `--run-rtgvcfeval` | boolean |  |  |  |  |  | Specifies whether to run rtgtools' vcfeval |
| `--run-vcfanno-db-sanity-check` | boolean |  |  |  |  |  | Specifies whether to check vcfanno database files for zero records and remove the corresponding annotation blocks from the TOML config before running vcfanno |
| `--save-all-mapped-as-cram` | boolean |  |  |  |  |  | Specifies whether to generate and publish all (unfiltered) alignment files as cram instead of bam |
| `--save-noalt-mapped-as-cram` | boolean |  |  |  |  |  | Specifies whether to generate and publish alt-filtered alignment files as cram instead of bam. Requires exclude_alt to be set to true. |
| `--scatter-count` | integer |  |  |  |  | 20 | Number of intervals to split your genome into (used to parallelize annotations) |
| `--skip-split-multiallelics` | boolean |  |  |  |  |  | Skip the split multiallelics step in SNV calling. |
| `--skip-subworkflows` | string |  |  |  | matches ^((me_calling\|me_annotation\|mt_annotation\|mt_subsample\|repeat_annotation\|repeat_calling\|snv_annotation\|snv_calling\|sv_annotation\|sv_calling\|generate_clinical_set)?,?)*(?<!,)$ |  | Disable specified subworkflows. |
| `--skip-tools` | string |  |  |  | matches ^((fastp\|gens\|germlinecnvcaller\|peddy\|smncopynumbercaller\|vcf2cytosure\|fastqc\|ngsbits\|mitosalt)?,?)*(?<!,)$ |  | Disable specified tools. |

## annotation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--variant-consequences-snv` | string |  |  |  |  |  | File containing list of SO terms listed in the order of severity from most severe to lease severe for annotating genomic and mitochondrial SNVs. |
| `--variant-consequences-sv` | string |  |  |  |  |  | File containing list of SO terms listed in the order of severity from most severe to lease severe for annotating genomic SVs. |
| `--vep-cache-version` | integer |  |  |  |  | 112 | Specify the version of the VEP cache provided to the `--vep_cache` option. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string (file path) |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string (file path) |  | yes |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--multiqc-samples` | string (file path) |  |  |  | matches ^\S+\.tsv$ |  | Path to a file containing internal ids and alternative ids in tab separated format. Will replace the internal id with the alternative id in the report. For more info check, https://docs.seqera.io/multiqc/reports/customisation#sample-name-replacement |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|json\|yaml\|yml)$ |  | Path to the samplesheet file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  | yes |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## mitosalt_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--heavy-strand-origin-end` | integer |  |  |  |  | 407 | end of heavy strand origin |
| `--heavy-strand-origin-start` | integer |  |  |  |  | 16081 | start of heavy strand origin |
| `--hisat2` | string |  |  |  |  |  |  |
| `--hisat2-build-memory` | string |  |  |  |  |  | Minimum memory required to build HISAT2 index with splice sites and exons. If available memory is below this threshold, a simpler index is built without splice sites. |
| `--light-strand-origin-end` | integer |  |  |  |  | 5763 | end of light strand origin |
| `--light-strand-origin-start` | integer |  |  |  |  | 5730 | start of light strand origin |
| `--mito-length` | integer |  |  |  |  | 16569 | length of mitochondrial genome |
| `--mitosalt-breakspan` | integer |  |  |  |  | 15 | minimum number of bases a non-split read must span either side of a breakpoint to be considered in the heteroplasmy count |
| `--mitosalt-breakthreshold` | integer |  |  |  |  | 2 | the maximum deviation a given set of split read breakpoints can have to be considered within the same cluster |
| `--mitosalt-cluster-threshold` | integer |  |  |  |  | 5 | minimum number of reads supporting a cluster |
| `--mitosalt-deletion-threshold-max` | integer |  |  |  |  | 30000 | the maximum size of the gap between fragments of a split read for the split read to be considered as potentially spanning a deletion |
| `--mitosalt-deletion-threshold-min` | integer |  |  |  |  | 30 | the minimum size of the gap between fragments of a split read for the split read to be considered as potentially spanning a deletion |
| `--mitosalt-depth` | integer |  |  |  |  | 10000000 | depth to subsample fastq files to before running mitosalt |
| `--mitosalt-evalue-threshold` | number |  |  |  |  | 1e-05 | alignment e-value cutoff |
| `--mitosalt-exclude` | integer |  |  |  |  | 5 | filter split reads if both fragments fall within the regions at the start and end to avoid pseudo-gapped alignments due to a circular genome |
| `--mitosalt-flank` | integer |  |  |  |  | 15 | basepairs flanking a deletion |
| `--mitosalt-heteroplasmy-limit` | number |  |  |  |  | 0.01 | detected heteroplasmy threshold |
| `--mitosalt-paired-distance` | integer |  |  |  |  | 1000 | the maximum distance of a paired read from its split counterpart for paired support to be considered positive |
| `--mitosalt-score-threshold` | integer |  |  |  |  | 80 | alignment score cutoff |
| `--mitosalt-sizelimit` | integer |  |  |  |  | 10000 | maximum size of deletions tolerated, beyond which they are reclassified as potential duplications in the reverse orientation |
| `--mitosalt-split-distance-threshold` | integer |  |  |  |  | 5 | the maximum length of unmapped distance between two fragments of a split read |
| `--mitosalt-split-length` | integer |  |  |  |  | 15 | minimum number of bases in a split read fragment for the read to be considered as potentially spanning a deletion |
| `--saltshaker-dominant-fraction` | number |  |  |  |  | 0.5 | fraction for dominant fraction for saltshaker classification |
| `--saltshaker-group-radius` | integer |  |  |  |  | 600 | spatial clustering radius for saltshaker grouping |
| `--saltshaker-high-heteroplasmy` | integer |  |  |  |  | 10 | high heteroplasmy threshold for saltshaker classification |
| `--saltshaker-multiple-threshold` | integer |  |  |  |  | 5 | threshold for multiple saltshaker classification |
| `--saltshaker-noise-threshold` | number |  |  |  |  | 0.3 | heteroplasmy threshold for background noise |

## reference_file_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bait-padding` | integer |  |  |  | matches ^\S+\.bed(\.gz)?$ | 100 | The amount to pad each end of the target intervals to create bait intervals. |
| `--bwa` | string (directory path) |  |  |  |  |  | Directory for pre-built bwa index. |
| `--bwafastalign` | string (directory path) |  |  |  |  |  | Directory for pre-built bwa-fastalign index. |
| `--bwamem2` | string (directory path) |  |  |  |  |  | Directory for pre-built bwamem2 index. |
| `--bwameme` | string (directory path) |  |  |  |  |  | Directory for pre-built bwameme's learned index. |
| `--cadd-prescored` | string (directory path) |  |  |  |  |  | Path to the directory containing pre-scored CADD indel annotations. |
| `--cadd-resources` | string (directory path) |  |  |  |  |  | Path to the directory containing cadd annotations. |
| `--fai` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?\.fai$ |  | Path to FASTA genome index file. |
| `--fasta` | string (file path) | yes |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to FASTA genome file. |
| `--gcnvcaller-model` | string (file path) |  |  |  |  |  | A file containing the path to models produced by GATK4 GermlineCNVCaller cohort. |
| `--genome` | string |  |  | `GRCh37`, `GRCh38` |  | GRCh38 | Name of iGenomes reference. |
| `--gens-gnomad-pos` | string (file path) |  | yes |  |  |  | Path to a list of common SNP locations for Gens. |
| `--gens-interval-list` | string (file path) |  | yes |  |  |  | Path to interval list for Gens. |
| `--gens-pon-female` | string (file path) |  | yes |  |  |  | Path to female panel of normals for Gens. |
| `--gens-pon-male` | string (file path) |  | yes |  |  |  | Path to male panel of normals for Gens. |
| `--gnomad-af` | string (file or directory path) |  |  |  | matches ^\S+\.tab(\.gz)?$ |  | Path to the gnomad tab file with allele frequencies. |
| `--gnomad-af-idx` | string (file or directory path) |  |  |  | matches ^\S+\.tab(\.gz)?\.tbi$ |  | Path to the index file for the gnomad tab file with allele frequencies. |
| `--igenomes-base` | string (directory path) |  | yes |  |  | s3://ngi-igenomes/igenomes/ | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  |  |  |  |  | Do not load the iGenomes reference config. |
| `--intervals-wgs` | string (file or directory path) | yes |  |  | matches ^\S+\.intervals?(_list)?$ |  | Path to the interval list of the genome (autosomes, sex chromosomes, and mitochondria). |
| `--intervals-y` | string (file or directory path) | yes |  |  | matches ^\S+\.intervals?(_list)?$ |  | Path to the interval list of the Y chromosome. |
| `--known-dbsnp` | string (file or directory path) |  |  |  | matches ^\S+\.vcf(\.gz)?$ |  | Path to known dbSNP file. |
| `--known-dbsnp-tbi` | string (file or directory path) |  |  |  | matches ^\S+\.vcf(\.gz)?\.tbi$ |  | Path to known dbSNP file index. |
| `--local-genomes` | string (directory path) |  |  |  |  |  | Local directory base for genome references that map to the config. |
| `--manta-call-regions` | string (file path) |  |  |  | matches ^\S+\.bed\.gz$ |  | Path to a bgzipped BED file restricting Manta SV calling to specific regions (e.g. primary chromosomes). Only applied for WGS; for WES, Manta always uses target_bed instead. |
| `--manta-call-regions-tbi` | string (file path) |  |  |  | matches ^\S+\.bed\.gz\.tbi$ |  | Tabix index for the file supplied via --manta_call_regions. |
| `--mito-name` | string |  |  |  |  | chrM | Name of the mitochondrial contig in the reference fasta file |
| `--ml-model` | string (file or directory path) |  |  |  |  |  | Path to sentieon machine learning model file. |
| `--mobile-element-references` | string (file path) |  |  |  | matches ^\S+\.tsv$ |  | File with mobile element references |
| `--mobile-element-svdb-annotations` | string |  |  |  | matches ^\S+\.csv$ |  | File with mobile element allele frequency references |
| `--modules-testdata-base-path` | string |  | yes |  |  |  | Base path / URL for data used in the modules |
| `--mt-fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to mitochondrial FASTA genome file. |
| `--par-bed` | string (file or directory path) |  |  |  | matches ^\S+\.bed(\.gz)?$ |  | Path to a BED file containing PAR regions (used by deepvariant). |
| `--ploidy-model` | string (directory path) |  |  |  |  |  | Directory containing the ploidy model files |
| `--readcount-intervals` | string (file path) |  |  |  |  |  | Interval list file containing the intervals over which read counts are tabulated for CNV calling |
| `--reduced-penetrance` | string (file or directory path) |  |  |  |  |  | File with gene ids that have reduced penetrance. For use with genmod |
| `--rtg-truthvcfs` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|json\|yaml\|yml)$ |  | Vcf used for evaluating variant calls. |
| `--sambamba-regions` | string (file path) |  |  |  | matches ^\S+\.bed$ |  | A BED file with regions of interest used in sambamba depth. |
| `--sample-id-map` | string (file path) |  |  |  | matches ^\S+\.csv$ |  | Path to a file containing internal ids and customer ids in csv format. |
| `--save-reference` | boolean |  |  |  |  |  | If generated by the pipeline save the required indices/references in the results directory. |
| `--score-config-mt` | string (file or directory path) |  |  |  |  |  | MT rank model config file for genmod. |
| `--score-config-snv` | string (file or directory path) |  |  |  |  |  | SNV rank model config file for genmod. |
| `--score-config-sv` | string (file or directory path) |  |  |  |  |  | SV rank model config file for genmod. |
| `--sdf` | string (directory path) |  |  |  |  |  | Directory for pre-built sdf index. Used by rtg/vcfeval |
| `--sequence-dictionary` | string (file or directory path) |  |  |  | matches ^\S+\.dict$ |  | Path to the genome dictionary file |
| `--svdb-query-bedpedbs` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|json\|yaml\|yml)$ |  | Databases used for structural variant annotation in chrA-posA-chrB-posB-type-count-frequency format. |
| `--svdb-query-dbs` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|json\|yaml\|yml)$ |  | Databases used for structural variant annotation in vcf format. |
| `--target-bed` | string (file or directory path) |  |  |  | matches ^\S+\.bed$ |  | Path to directory for target bed file. |
| `--variant-catalog` | string (file path) |  |  |  |  |  | Path to variant catalog file |
| `--vcf2cytosure-blacklist` | string (file path) |  |  |  | matches ^\S+\.bed$ |  | Path to vcf2cytosure blacklist file |
| `--vcfanno-extra-resources` | string (file path) |  |  |  |  |  | Path to a VCF file containing annotations. |
| `--vcfanno-lua` | string |  |  |  | matches ^\S+\.lua$ |  | Path to the vcfanno lua file. |
| `--vcfanno-resources` | string |  |  |  |  |  | Path to a file containing the absolute paths to resources defined within the vcfanno toml file. One line per resource. |
| `--vcfanno-toml` | string |  |  |  | matches ^\S+\.toml$ |  | Path to the vcfanno toml file. |
| `--vep-cache` | string |  |  |  |  |  | Path to vep's cache directory. |
| `--vep-filters` | string (file or directory path) |  |  |  |  |  | Path to the file containing HGNC_IDs of interest on separate lines. |
| `--vep-filters-scout-fmt` | string (file or directory path) |  |  |  |  |  | Path to a bed-like file exported by scout, which contains HGNC_IDs to be used in filter_vep. |
| `--vep-plugin-files` | string (file path) |  |  |  | matches ^\S+\.csv$ |  | Databases used by both named and custom plugins to annotate variants. |
| `--verifybamid-svd-bed` | string (file path) |  |  |  |  |  | Path to a BED file containing markers used by verifybamid2. |
| `--verifybamid-svd-mu` | string (file path) |  |  |  |  |  | Path to mean matrix file of genotype matrix. Used by verifybamid2. |
| `--verifybamid-svd-ud` | string (file path) |  |  |  |  |  | Path to UD matrix file from SVD result of genotype matrix. Used by verifybamid2. |

## variant_calling_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--call-interval` | string (file or directory path) |  |  |  |  |  | Interval in the reference that will be used in the software. Used only by sentieon. |
| `--cnvnator-binsize` | integer |  |  |  |  | 1000 | Bin size for CNVnator |
| `--sentieon-dnascope-pcr-indel-model` | string |  |  | `NONE`, `HOSTILE`, `AGGRESSIVE`, `CONSERVATIVE` |  | CONSERVATIVE | Option for selecting the PCR indel model used by Sentieon Dnascope. |
| `--variant-caller` | string |  |  | `deepvariant`, `sentieon` |  | deepvariant | Specifies the variant caller to use - available options are 'deepvariant' and 'sentieon'. |
| `--variant-type` | string |  |  | `snp`, `indel`, `snp,indel` |  | snp,indel | Specifies the variant types for sentieon variant caller. |

<!-- Generated from nf-core/raredisease@83f2699d28bc957e1d3b875da3d96004a818c2c3. Do not edit by hand. -->
