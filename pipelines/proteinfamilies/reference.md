---
name: proteinfamilies
version: 2.6.0
commit: 318acd54eb9c679553338b2db46313bb469d03d1
---

# proteinfamilies — full parameter reference

nf-core/proteinfamilies pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## alignment_params

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--alignment-tool` | string |  |  | `famsa`, `mafft` |  | famsa | Choose alignment tool. FAMSA is recommended as best time-memory-accuracy combination option. |
| `--clipkit-out-format` | string |  |  |  |  | clipkit | Choose the output format of the clipped alignment. |
| `--gap-threshold` | number |  |  |  | ≥ 0.0; ≤ 1.0 | 0.5 | Multiple Sequence Alignment (MSA) positions with gappiness greater than this threshold will be trimmed |
| `--hmmsearch-evalue-cutoff` | number |  |  |  |  | 0.001 | hmmsearch e-value cutoff threshold for reported results |
| `--hmmsearch-query-length-threshold` | number |  |  |  | ≥ 0.0; ≤ 1.0 | 0.9 | hmmsearch minimum length percentage filter of hit env vs query length |
| `--hmmsearch-write-domain` | boolean |  | yes |  |  | true | Boolean whether to generate domain results file of hmmsearch |
| `--hmmsearch-write-target` | boolean |  | yes |  |  |  | Boolean whether to generate target results file of hmmsearch |
| `--save-hmmsearch-filtered-fasta` | boolean |  |  |  |  |  | Save family fasta files after recruiting sequences with hmmsearch |
| `--save-hmmsearch-results` | boolean |  |  |  |  |  | Save the output of hmmsearch (.domtbl.gz and .tbl.gz) |
| `--skip-additional-sequence-recruiting` | boolean |  | yes |  |  |  | Skip recruitment of additional sequences from the input FASTA file using the family Hidden Markov Models (HMMs) into the full alignment |
| `--skip-msa-trimming` | boolean |  | yes |  |  |  | Boolean whether to skip the trimming process of gappy positions from Multiple Sequence Alignments (MSAs) |
| `--trim-ends-only` | boolean |  |  |  |  | true | Choose if ClipKIT should only clip gaps at the ends of the MSAs. |

## clustering_params

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cluster-cov-mode` | integer |  |  |  |  | 0 | mmseqs parameter for coverage mode: 0 for both, 1 for target and 2 for query sequence |
| `--cluster-coverage` | number |  |  |  | ≥ 0.0; ≤ 1.0 | 0.5 | mmseqs parameter for minimum sequence coverage ratio |
| `--cluster-seq-identity` | number |  |  |  | ≥ 0.0; ≤ 1.0 | 0.3 | mmseqs parameter for minimum sequence identity |
| `--cluster-size-threshold` | integer |  |  |  |  | 25 | Minimum clustering chunk size threshold to create seed Multiple Sequence Alignments upon. |
| `--clustering-tool` | string |  |  | `linclust`, `cluster` |  | cluster | Choose clustering algorithm. Either simple 'cluster' for medium size inputs, or 'linclust' for less sensitive clustering of larger datasets. |
| `--save-mmseqs-chunked-fasta` | boolean |  |  |  |  |  | Save membership-filtered initial mmseqs clusters in fasta format |
| `--save-mmseqs-clustering` | boolean |  |  |  |  |  | Save the clustering output folder of mmseqs cluster or linclust |
| `--save-mmseqs-db` | boolean |  |  |  |  |  | Save the db output folder of mmseqs createdb |

## downstream_params

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-proteinannotator-samplesheet` | boolean |  | yes |  |  | true | Skip the generation of the proteinannotator samplesheet. |
| `--skip-proteinfold-samplesheet` | boolean |  | yes |  |  | true | Skip the generation of the proteinfold samplesheet. |

## family_generation_params

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clusters-per-chunk` | integer |  |  |  |  | 1000 | Number of clusters handed to each family generation task by the 'iterative' algorithm. |
| `--family-generation-algorithm` | string |  |  | `standard`, `iterative` |  | standard | Choose the algorithm that turns clusters into family models. Either 'standard', aligning each cluster and building one HMM per task, or 'iterative', letting mgnifam loop HMM building, recruitment and realignment per cluster. |
| `--save-iterative-family-metadata` | boolean |  |  |  |  |  | Save the family rosters and diagnostics reported by the 'iterative' algorithm |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. Example: name.surname@example.com |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. Example: name.surname@example.com |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/proteinfamilies/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. Example: name.surname@example.com |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file '.csv' containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
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
| `--modules-testdata-base-path` | string |  | yes |  |  |  | Base path / URL for data used in the modules |

## phylogeny_params

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-phylogenetic-inference` | boolean |  | yes |  |  | true | Skip the phylogenetic inference with the cmaple tool. |

## quality_check_params

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--max-seq-length` | integer |  |  |  |  | 5000 | The maximum allowed sequence length |
| `--min-seq-length` | integer |  |  |  |  | 30 | The minimum allowed sequence length |
| `--remove-duplicates-on-sequence` | boolean |  |  |  |  |  | Remove duplicate input amino acid sequences, based on the sequence. |
| `--skip-preprocessing` | boolean |  |  |  |  |  | Skip all default QC steps for sequences (gap trimming, length filtering, validation, duplicate removal). |

## redundancy_params

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cluster-cov-mode-for-redundancy` | integer |  |  |  |  | 0 | mmseqs parameter for coverage mode: 0 for both, 1 for target and 2 for query sequence |
| `--cluster-coverage-for-redundancy` | number |  |  |  | ≥ 0.0; ≤ 1.0 | 0.9 | mmseqs parameter for minimum sequence coverage ratio |
| `--cluster-seq-identity-for-redundancy` | number |  |  |  | ≥ 0.0; ≤ 1.0 | 0.9 | mmseqs parameter for minimum sequence identity |
| `--hmmsearch-family-redundancy-length-threshold` | number |  |  |  | ≥ 0.0; ≤ 1.0 | 1.0 | hmmsearch minimum length percentage filter of hit env vs query length, for redundant family removal |
| `--hmmsearch-family-similarity-length-threshold` | number |  |  |  | ≥ 0.0; ≤ 1.0 | 0.9 | hmmsearch minimum length percentage of hit env vs query length, to flag and report similar families (and to optionally merge) |
| `--save-non-redundant-fams-fasta` | boolean |  |  |  |  |  | Save only the fasta files of non-redundant families (might still contain redundant sequences) |
| `--save-non-redundant-seqs-fasta` | boolean |  |  |  |  | true | Save the final family fasta files with sequence redundancy removed |
| `--skip-family-merging` | boolean |  | yes |  |  |  | Flag to skip merging of similar families. |
| `--skip-family-redundancy-removal` | boolean |  | yes |  |  |  | Skip removal of between-family redundancy via hmmsearch sequence to family model matching. |
| `--skip-sequence-redundancy-removal` | boolean |  | yes |  |  |  | Skip removal of inside-family redundancy of sequences via mmseqs clustering. |

## update_params

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--save-update-families-clipped-fasta` | boolean |  |  |  |  | true | Save FASTA files derived from updated family MSAs (after re-alignment and clipping) |
| `--save-update-families-pre-clipped-fasta` | boolean |  |  |  |  |  | Save intermediate FASTA files before clipping gappy ends (non-redundant --if `skip_sequence_redundancy_removal` is false-- or all --if `skip_sequence_redundancy_removal` is true--) in the update_families subworkflow |

<!-- Generated from nf-core/proteinfamilies@318acd54eb9c679553338b2db46313bb469d03d1. Do not edit by hand. -->
