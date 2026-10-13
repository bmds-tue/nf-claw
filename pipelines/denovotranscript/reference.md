---
name: denovotranscript
version: 1.2.1
commit: 9ab0f57785c37f77e05a03c8c327e35c63c8432b
---

# denovotranscript — full parameter reference

nf-core/denovotranscript pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## assembly_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--assemblers` | string |  |  |  | matches ^(trinity\|trinity_no_norm\|rnaspades)(,(trinity\|trinity_no_norm\|rnaspades))*$ | trinity,rnaspades | Assemblers to use. Possible options include `trinity`, `trinity_no_norm` (trinity without normalized reads), and `rnaspades`. |
| `--extra-tr2aacds-args` | string |  |  |  |  |  | Extra arguments for tr2aacds.pl. For example, '-MINAA=20' |
| `--extra-trinity-args` | string |  |  |  |  |  | Extra arguments to pass to Trinity command in addition to defaults. Applies to both trinity and trinity_no_norm. |
| `--hard-filtered-transcripts` | boolean |  |  |  |  |  | Include soft filtered transcripts (in addition to the medium filtered transcripts) from rnaSPAdes in the input to EvidentialGene tr2aacds. |
| `--soft-filtered-transcripts` | boolean |  |  |  |  |  | Include hard filtered transcripts (in addition to medium filtered transcripts) from rnaSPAdes in the input to EvidentialGene tr2aacds. |
| `--ss` | string |  |  | `rf`, `fr` |  |  | Set strand-specific type for rnaSPAdes. Use `rf` when first read in pair corresponds to reverse gene strand (antisense data, e.g. obtained via dUTP protocol) and `fr` otherwise (forward). |

## busco_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--busco-config` | string |  |  |  |  |  | Path to BUSCO config file. |
| `--busco-lineage` | string |  |  |  |  | auto | The BUSCO lineage to use, or `auto` to automatically select lineage |
| `--busco-lineages-path` | string |  |  |  |  |  | Path to local BUSCO lineages directory. |
| `--busco-mode` | string |  |  | `genome`, `proteins`, `transcriptome` |  | transcriptome | The mode to run BUSCO in. One of genome, proteins, or transcriptome |

## fastqc_fastp_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--adapter-fasta` | string |  |  |  |  |  | File in FASTA format containing possible adapters to remove. Accepted formats: *.{fasta,fna,fas,fa} |
| `--extra-fastp-args` | string |  |  |  |  |  | Extra arguements for fastp. For example, `--trim_front1 15 --trim_front2 15 --trim_tail1 5 --trim_tail2 5{:bash}` |
| `--save-merged` | boolean |  |  |  |  |  | Specify true to save all merged reads to the a file ending in *.merged.fastq.gz |
| `--save-trimmed-fail` | boolean |  |  |  |  |  | Specify `true` to save files that failed to pass trimming thresholds ending in *.fail.fastq.gz |
| `--skip-fastp` | boolean |  |  |  |  |  | Skip the fastp process if `true` |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip FastQC processes if `true` |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--transcript-fasta` | string |  |  |  |  |  | Path to fasta file (not compressed) containing a transcriptome assembly. Only needed if `--skip_assembly` is `True`. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--genome` | string |  | yes |  |  |  | Name of iGenomes reference. |
| `--igenomes-base` | string |  | yes |  |  | s3://ngi-igenomes/igenomes/ | Directory / URL base for iGenomes references. |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |

## rnaquast_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to FASTA genome file. |
| `--gtf` | string |  |  |  |  |  | File with gene coordinates in GTF/GFF format (needs information about parent relations). rnaQUAST authors recommend to use files downloaded from GENCODE or Ensembl. |

## salmon_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--lib-type` | string |  |  |  |  | A | Override library type inferred based on strandedness defined in meta object. `A` for auto. |

## sortmerna_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--remove-ribo-rna` | boolean |  |  |  |  |  | Enable the removal of reads derived from ribosomal RNA using SortMeRNA. |
| `--ribo-database-manifest` | string |  |  |  |  | ${projectDir}/assets/rrna-db-defaults.txt | Text file containing paths to fasta files (one per line) that will be used to create the database for SortMeRNA. |
| `--save-non-ribo-reads` | boolean |  |  |  |  |  | If this option is specified, intermediate FastQ files containing non-rRNA reads will be saved in the results directory. |

## transrate_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--transrate-reference` | string |  |  |  |  |  | Path to FASTA file of reference set of proteins or transcripts from a related species |

## workflow_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--qc-only` | boolean |  |  |  |  |  | Whether the pipeline should only perform quality control, and skip assembly and quantification. |
| `--skip-assembly` | boolean |  |  |  |  |  | Whether the pipeline should skip assembly steps, and only perform quality control of reads and quantification. --transcript_fasta must be provided if True. |

<!-- Generated from nf-core/denovotranscript@9ab0f57785c37f77e05a03c8c327e35c63c8432b. Do not edit by hand. -->
