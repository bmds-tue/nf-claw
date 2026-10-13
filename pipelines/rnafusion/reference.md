---
name: rnafusion
version: 4.1.3
commit: 76ad76e7c39b2ba9edc35aa3602e3dc454d842ec
---

# rnafusion — full parameter reference

nf-core/rnafusion pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## compression_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cram` | boolean |  |  |  |  |  | Output CRAM files instead of BAM files. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--seq-center` | string |  |  |  |  |  | Sequencing center, used to fill in read group CN tag in the BAM header |
| `--seq-platform` | string |  |  |  |  |  | Sequencing platform, used to fill in read group PL tag in the BAM header |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--star-ignore-sjdbgtf` | boolean |  | yes |  |  |  | Whether to ignore the GTF in STAR alignment |
| `--star-limit-bam-sort-ram` | integer |  |  |  | ≥ 0 |  | The maximum amount of RAM to use for sorting the BAM file in STAR. Should by in bits. Setting this value to `0` will use the default amount of STAR. |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annot-filter-url` | string |  |  |  | matches ^https?://.* | https://data.broadinstitute.org/Trinity/CTAT_RESOURCE_LIB/AnnotFilterRule.pm | URL to annotation filter rule file |
| `--arriba-fusions` | string (file path) |  |  |  | matches \S+\.tsv$ |  | Path to arriba output |
| `--arriba-ref-blacklist` | string (file path) |  |  |  | matches \S+\.tsv(\.gz)?$ |  | Path to arriba reference blacklist |
| `--arriba-ref-cytobands` | string (file path) |  |  |  | matches \S+\.tsv$ |  | Path to arriba reference cytobands |
| `--arriba-ref-known-fusions` | string (file path) |  |  |  | matches \S+\.tsv(\.gz)?$ |  | Path to arriba reference known fusions |
| `--arriba-ref-protein-domains` | string (file path) |  |  |  | matches \S+\.gff3$ |  | Path to arriba reference protein domain |
| `--cosmic-passwd` | string |  |  |  |  |  | COSMIC password |
| `--cosmic-username` | string |  |  |  |  |  | COSMIC username |
| `--ctatsplicing-cancer-introns` | string (file path) |  |  |  | matches \S+\.tsv\.gz$ | https://data.broadinstitute.org/Trinity/CTAT_RESOURCE_LIB/CANCER_SPLICING_LIB_SUPPLEMENT/cancer_introns.GRCh38.Jun232020.tsv.gz | Path to the cancer introns CSV file to create the CTAT-SPLICING reference with |
| `--dfam-h3f` | string (file path) |  |  |  | matches \S+\.h3f$ |  | Path to Dfam H3F database file |
| `--dfam-h3i` | string (file path) |  |  |  | matches \S+\.h3i$ |  | Path to Dfam H3I database file |
| `--dfam-h3m` | string (file path) |  |  |  | matches \S+\.h3m$ |  | Path to Dfam H3M database file |
| `--dfam-h3p` | string (file path) |  |  |  | matches \S+\.h3p$ |  | Path to Dfam H3P database file |
| `--dfam-hmm` | string (file path) |  |  |  | matches \S+\.hmm$ |  | Path to Dfam HMM database file |
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--fusioncatcher-fusions` | string (file path) |  |  |  | matches \S+\.txt$ |  | Path to fusioncatcher output |
| `--fusioncatcher-limitSjdbInsertNsj` | integer |  |  |  | ≥ 1 | 2000000 | Use limitSjdbInsertNsj with int for fusioncatcher |
| `--fusioncatcher-ref` | string (directory path) |  |  |  |  |  | Path to fusioncatcher references |
| `--fusioninspector-fusions` | string (file path) |  |  |  | matches \S+\.tsv$ |  | Path to a fusion list file built with format GENE1--GENE2 |
| `--fusioninspector-limitSjdbInsertNsj` | integer |  |  |  | ≥ 1 | 1000000 | Use limitSjdbInsertNsj with int for fusioninspector STAR process |
| `--fusionreport-ref` | string (directory path) |  |  |  |  |  | Path to fusionreport references |
| `--genome-gencode-version` | integer |  |  |  |  |  | gencode version |
| `--genomes-base` | string | yes |  |  |  |  | Path to reference folder |
| `--genomes-ignore` | boolean |  |  |  |  |  | Don't automatically assign reference parameters to the correct references in --genomes_base |
| `--hgnc-date` | string (file path) |  |  |  | matches \S+\.txt$ |  | Path to HGNC timestamp file for database retrieval |
| `--hgnc-ref` | string (file path) |  |  |  | matches \S+\.txt$ |  | Path to HGNC database file |
| `--input` | string (file path) |  |  |  | matches ^\S+\.(csv\|yaml\|yml\|json)$ |  | Path to samplesheet file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--pfam-file` | string (file path) |  |  |  | matches \S+\.hmm(\.gz)?$ |  | Path to Pfam database file |
| `--qiagen` | boolean |  |  |  |  |  | Use QIAGEN instead of SANGER to download COSMIC database |
| `--read-length` | integer |  |  |  | ≥ 1 | 100 | The length of the reads provided to the pipeline. This is used for the '--sjdbOverhang' option of STAR as read_length - 1. Providing 1 to this option will disable overhang handling. |
| `--salmon-index` | string (directory path) |  |  |  |  |  | Path to salmon index |
| `--starfusion-fusions` | string (file path) |  |  |  | matches \S+\.tsv$ |  | Path to starfusion output |
| `--starfusion-ref` | string (directory path) |  |  |  |  |  | Path to starfusion references |
| `--starindex-ref` | string (directory path) |  |  |  |  |  | Path to starindex references |
| `--tools` | string | yes |  |  | matches ^((arriba\|ctatsplicing\|fusioncatcher\|starfusion\|stringtie\|fusionreport\|fastp\|salmon\|fusioninspector\|all)?,?)*(?<!,)$ |  | Comma-delimited list of tools to run |
| `--tools-cutoff` | integer |  |  |  | ≥ 1 | 1 | Discard fusions identified by less than INT tools |
| `--whitelist` | string (file path) |  |  |  | matches \S+\.tsv$ |  | Path to fusions to add to the input of fusioninspector |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## read_trimming_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--adapter-fasta` | string (file path) |  |  |  | matches \S+\.f(n\|ast)?a$ |  | Path to adapter fasta file: default: [] |
| `--min-trimmed-reads` | integer |  |  |  |  | 1 | FASTP: Inputs with fewer than this reads will be filtered out of the "reads" output channel |
| `--save-merged` | boolean |  |  |  |  |  | FASTP: Specify true to save merged reads |
| `--save-trimmed-fail` | boolean |  |  |  |  |  | FASTP: Specify true to save files that failed to pass trimming thresholds |
| `--trim-tail` | integer |  |  |  | ≥ 0 |  | The amount of bases to trim at the tail of each read, none will be trimmed by default |
| `--trim-tail-fusioncatcher` | integer |  |  |  | ≥ 0 |  | The amount of bases to trim at the tail of each read for fusioncatcher, none will be trimmed by default |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dfam-version` | number or null |  |  |  |  |  | Version of dfam to use |
| `--fai` | string (file path) |  |  |  | matches ^\S+\.fn?ai(\.gz)?$ |  | Path to FASTA genome index file. |
| `--fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to FASTA genome file. |
| `--fusion-annot-lib` | string (file path) |  |  |  | matches \S+\.dat\.gz$ |  | Path to Fusion Annotation Library to be used in STARFUSION_BUILD. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--gtf` | string (file path) |  |  |  | matches ^\S+\.gtf?(\.gz)?$ |  | Path to GTF genome file. |
| `--no-cosmic` | boolean |  |  |  |  |  | Avoid using Cosmic DB (for example in clinical case applications where a paid license applies. |
| `--pfam-version` | number or null |  |  |  |  |  | Version of pfam to use |
| `--references-only` | boolean |  |  |  |  |  | Skip running the analysis, only builds the references |
| `--refflat` | string (file path) |  |  |  | matches ^\S+\.refflat?$ |  | Path to GTF genome file. |
| `--rrna-intervals` | string (file path) |  |  |  | matches ^\S+\.interval_list?$ |  | Path to ribosomal interval list. |
| `--species` | string |  |  |  |  | homo_sapiens | Which species dfam should automatically download, default: homo_sapiens. |

## skip_steps

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-qc` | boolean |  |  |  |  |  | Skip QC steps |
| `--skip-vcf` | boolean |  |  |  |  |  | Skip vcf creation step |
| `--skip-vis` | boolean |  |  |  |  |  | Skip visualisation steps |

<!-- Generated from nf-core/rnafusion@76ad76e7c39b2ba9edc35aa3602e3dc454d842ec. Do not edit by hand. -->
