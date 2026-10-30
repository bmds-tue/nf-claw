---
name: readsimulator
version: 1.0.1
commit: 0e8805ddbcd0e0fdcdc62105d59c3f29dd985a64
---

# readsimulator — full parameter reference

nf-core/readsimulator pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## amplicon_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--amplicon-crabs-ispcr-error` | number |  |  |  |  | `4.5` | Maximum number of errors allowed in CRABS insilicoPCR primer sequences |
| `--amplicon-fw-primer` | string |  |  |  |  | `GTCGGTAAAACTCGTGCCAGC` | Forward primer to use with crabs_insilicopcr. |
| `--amplicon-read-count` | integer |  |  |  |  | `500` | Number of reads to be simulated per amplicon. |
| `--amplicon-read-length` | integer |  |  |  |  | `130` | Length of reads to be simulated. |
| `--amplicon-rv-primer` | string |  |  |  |  | `CATAGTGGGGTATCTAATCCCAGTTTG` | Reverse primer to use with crabs_insilicopcr. |
| `--amplicon-seq-system` | string |  |  | `GA1`, `GA2`, `HS10`, `HS20`, `HS25`, `HSXn`, `HSXt`, `MinS`, `MSv1`, `MSv3`, `NS50` |  | `HS25` | Sequencing system of reads to be simulated. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean |  | yes |  |  |  | Display help text. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--validationFailUnrecognisedParams` | boolean |  | yes |  |  |  | Validation of parameters fails when an unrecognised parameter is found. |
| `--validationLenientMode` | boolean |  | yes |  |  |  | Validation of parameters in lenient more. |
| `--validationShowHiddenParams` | boolean |  | yes |  |  |  | Show all params when using `--help` |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

## max_job_request_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--max-cpus` | integer |  | yes |  |  | `16` | Maximum number of CPUs that can be requested for any single job. |
| `--max-memory` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `128.GB` | Maximum amount of memory that can be requested for any single job. |
| `--max-time` | string |  | yes |  | matches `^(\d+\.?\s*(s\|m\|h\|d\|day)\s*)+$` | `240.h` | Maximum amount of time that can be requested for any single job. |

## metagenome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--metagenome-abundance` | string |  |  | `uniform`, `halfnormal`, `exponential`, `lognormal`, `zero_inflated_lognormal` |  | `lognormal` | Abundance distribution. |
| `--metagenome-abundance-file` | string (file path) |  |  |  | matches `^\S+\.tsv$` |  | Path to tab-separated file containing abundance distribution. |
| `--metagenome-coverage` | string |  |  | `uniform`, `halfnormal`, `exponential`, `lognormal`, `zero_inflated_lognormal` |  |  | Coverage distribution. |
| `--metagenome-coverage-file` | string (file path) |  |  |  | matches `^\S+\.tsv$` |  | Path to tab-separated file containing coverage information. |
| `--metagenome-gc-bias` | boolean |  |  |  |  |  | Use this option to prevent simulating reads that have abnormal GC content. |
| `--metagenome-input-format` | string |  |  | `genomes`, `draft` |  | `genomes` | Format of FASTA file used to generate reads |
| `--metagenome-mode` | string |  |  | `kde`, `basic` |  | `kde` | Can be 'kde', or 'basic'. |
| `--metagenome-model` | string |  |  | `HiSeq`, `NovaSeq`, `MiSeq` |  | `MiSeq` | Can be 'HiSeq', 'NovaSeq', or 'MiSeq'. |
| `--metagenome-n-reads` | string |  |  |  |  | `1M` | Number of reads to generate. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to reference FASTA file. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--ncbidownload-accessions` | string (file path) |  |  |  |  |  | Path to text file containing accession ids (one accession per row). |
| `--ncbidownload-group` | string |  |  |  | matches `^((all\|archaea\|bacteria\|fungi\|invertebrate\|metagenomes\|plant\|protozoa\|vertebrate_mammalian\|vertebrate_other\|viral)?,?)*(?<!,)$` | `all` | The NCBI taxonomic groups to download. Options include 'all', 'archaea', 'bacteria', 'fungi', 'invertebrate', 'metagenomes', 'plant', 'protozoa', 'vertebrate_mammalian', 'vertebrate_other', and 'viral'. A comma-separated list is also valid (e.g., 'bacteria,viral'). |
| `--ncbidownload-section` | string |  |  | `refseq`, `genbank` |  | `refseq` | The NCBI section to download. 'refseq' or 'genbank'. |
| `--ncbidownload-taxids` | string (file path) |  |  |  |  |  | Path to text file containing taxids (one taxid per row). |

## simulation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--amplicon` | boolean |  |  |  |  |  | Option to simulate amplicon sequencing reads. |
| `--metagenome` | boolean |  |  |  |  |  | Option to simulate metagenomic sequencing reads. |
| `--target-capture` | boolean |  |  |  |  |  | Option to simulate target capture sequencing reads. |
| `--wholegenome` | boolean |  |  |  |  |  | Option to simulate wholegenomic sequencing reads. |

## target_capture_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--probe-file` | string (file path) |  |  |  |  |  | Path to bait/probe file. Can be a fasta file or a bed file. |
| `--probe-ref-name` | string |  |  | `Tetrapods-UCE-2.5Kv1`, `Tetrapods-UCE-5Kv1`, `Actinopterygians-0.5Kv1`, `Acanthomorphs-1Kv1`, `Arachnida-1.1Kv1`, `Coleoptera-1.1Kv1`, `Diptera-2.7Kv1`, `Hemiptera-2.7Kv1`, `Hymenoptera-1.5Kv1`, `Hymenoptera-2.5Kv2`, `Anthozoa-1.7Kv1` |  | `Tetrapods-UCE-5Kv1` | Name of supported probe. Mandatory if not using `--probes` parameter. |
| `--target-capture-fmedian` | integer |  |  |  |  | `500` | Median of fragment size at shearing. |
| `--target-capture-fshape` | number |  |  |  |  | `6` | Shape parameter of the fragment size distribution. |
| `--target-capture-illen` | integer |  |  |  |  | `150` | Illumina: read length. |
| `--target-capture-ilmode` | string |  |  | `pe`, `mp`, `se` |  | `pe` | Illumina: Sequencing mode. |
| `--target-capture-mode` | string |  |  | `illumina`, `pacbio` |  | `illumina` | Simulate 'illumina' or 'pacbio' reads. |
| `--target-capture-num` | integer |  |  |  |  | `500000` | Number of fragments. |
| `--target-capture-pblen` | integer |  |  |  |  | `30000` | PacBio: Average (polymerase) read length. |
| `--target-capture-smedian` | integer |  |  |  |  | `1300` | Median of fragment size distribution. |
| `--target-capture-sshape` | number |  |  |  |  | `6` | Shape parameter of the fragment size distribution. |
| `--target-capture-tmedian` | integer |  |  |  |  |  | Median of target fragment size (the fragment size of the data). If specified, will override '--fmedian' and '--smedian'. Othersise will be estimated. |
| `--target-capture-tshape` | number |  |  |  |  |  | Shape parameter of the effective fragment size distribution. |

## wholegenome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--wholegenome-error-rate` | number |  |  |  |  | `0.02` | The base error rate. |
| `--wholegenome-indel-extended` | number |  |  |  |  | `0.3` | The probability that an indel is extended. |
| `--wholegenome-indel-fraction` | number |  |  |  |  | `0.15` | The fraction of indels. |
| `--wholegenome-mutation-rate` | number |  |  |  |  | `0.001` | The rate of mutations. |
| `--wholegenome-n-reads` | integer |  |  |  |  | `1000000` | The number of read pairs. |
| `--wholegenome-outer-dist` | integer |  |  |  |  | `500` | The outer distance between the two ends. |
| `--wholegenome-r1-length` | integer |  |  |  |  | `70` | The length of the first reads. |
| `--wholegenome-r2-length` | integer |  |  |  |  | `70` | The length of the second reads. |
| `--wholegenome-standard-dev` | integer |  |  |  |  | `50` | The standard deviation. |

<!-- Generated from nf-core/readsimulator@0e8805ddbcd0e0fdcdc62105d59c3f29dd985a64. Do not edit by hand. -->
