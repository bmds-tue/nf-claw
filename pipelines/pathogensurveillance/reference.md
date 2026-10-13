---
name: pathogensurveillance
version: 1.1.0
commit: 13547eaa7345dab4ac97db49775ae8284af4113d
---

# pathogensurveillance — full parameter reference

nf-core/pathogensurveillance pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## analysis_parameters

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--allow-atypical-refs` | boolean |  |  |  |  | false | When selecting references automatically, allow assemblies that NCBI considers atypical. |
| `--allow-non-refseq` | boolean |  |  |  |  | false | When selecting references automatically, allow assemblies not in RefSeq. |
| `--allow-unannotated` | boolean |  |  |  |  | false | When selecting references automatically, allow assemblies that do not have annotations. The pipeline will attempt to annotate these references as needed. |
| `--cpu-scale` | number |  |  |  | ≥ 0.01 | 1.0 | A scaling factor to adjust the number of CPUs used by multithreaded processes. The number of CPUs for each process will be multiplied by this value and rounded to the nearest integer (minimum 1). |
| `--max-depth` | number |  |  |  |  | 100 | Maximum depth of reads to be used for all analyses. Samples with more reads are subsampled to this depth. |
| `--max-samples` | integer |  |  |  |  | 1000 | Maximum number of samples to analyze. The first n samples will be used. |
| `--max-variants` | number |  |  |  |  | 100000 | The maximum number of variants to use for the SNP tree and minimum spanning nextwork produced by the variant analysis. The first N variants are used when more than N are available. |
| `--min-bases-to-assemble` | number |  |  |  |  | 100000 | The minimum number of bases after quality filtering needed to attempt an genome assembly. Samples with few than this amount of bases will be excluded from further analysis. |
| `--n-ref-closest` | number |  |  |  |  | 2 | The number of references most similar to each sample based on estimated ANI to include in phyogenetic anlyses. |
| `--n-ref-closest-named` | number |  |  |  |  | 1 | Same as the 'n_ref_closest' option except that it only applies to referneces with what apppear to be standard latin binomaial names (i.e. two words with no numbers or symbols). This is intended to ensure that a refernece with an informative name is present even if it is not the most similar. |
| `--n-ref-context` | number |  |  |  |  | 5 | The number of references representing the entire range of ANI relative to each sample. These are meant to provide context for more similar references. For a group of samples, the fewest total references will be selected that satisify this count for each sample. |
| `--n-ref-genera` | integer or string |  |  |  |  | 20 | The maximum number/percentage of references representing unique genera to download from RefSeq for each family predicited to be in each sample. Samples with similar initial indentifications will usually use the same references, so the total number of references downloaded for a goup of samples will depend on the taxonomic diversity of the samples. |
| `--n-ref-species` | integer or string |  |  |  |  | 20 | The maximum number/percentage of references representing unique species to download from RefSeq for each genus predicited to be in each sample. Samples with similar initial indentifications will usually use the same references, so the total number of references downloaded for a goup of samples will depend on the taxonomic diversity of the samples. |
| `--n-ref-strains` | integer or string |  |  |  |  | 5 | The maximum number/percentage of references representing unique subspecies to download from RefSeq for each species predicited to be in each sample. Samples with similar initial indentifications will usually use the same references, so the total number of references downloaded for a goup of samples will depend on the taxonomic diversity of the samples. |
| `--only-latin-binomial-refs` | boolean |  |  |  |  | false | When selecting references automatically, only consider references with names that appear to be standard latin bionomials (i.e. no numbers or symbols in the first two words). |
| `--phylo-max-genes` | number |  |  |  |  | 500 | The maximum number of genes used to conduct a core gene phylogeny. |
| `--phylo-min-genes` | number |  |  |  |  | 10 | The minimum number of genes needed to conduct a core gene phylogeny. Samples and references will be removed (as allowed by the `min_core_samps` and `min_core_refs` options) until this minimum is met. |
| `--ref-min-ani` | number |  |  |  | ≥ 0; ≤ 1 | 0.95 | The minimum ANI between a sample and potential reference for that reference to be used for mapping reads from that sample. To force all the samples in a report group to use the same reference, set this value very low. |
| `--skip-core-phylogeny` | boolean |  |  |  |  | false | Skip the core genome phylogeny analysis. This will not affect downstream processes like MultiQC and the main report. |

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
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/refs/heads/pathogensurveillance/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | symlink | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--show-hidden-params` | boolean |  | yes |  |  |  | Show all params when using `--help` |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bakta-db` | string (directory path) |  |  |  |  |  | The path to the Bakta database folder. This or --download_bakta_db must be included. |
| `--bakta-db-type` | string |  |  |  | matches light\|full | light | Which type of the Bakta database to download. Must be 'light' (~2Gb) or 'full' (~40Gb). |
| `--data-dir` | string (directory path) |  |  |  |  | path_surveil_data | The location to save downloaded files for later use. This is seperate from the cached data (usually stored in the 'work' directory), so that the cache can be cleared without having to repeat many large downloads. |
| `--download-bakta-db` | boolean |  |  |  |  | true | Download the database required for running Bakta. This or --bakta_db must be included. For more information, see: https://github.com/oschwengers/bakta?tab=readme-ov-file#database-download |
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.[ct]sv$ |  | Path to comma/tab-separated file containing information about samples. |
| `--max-parallel-downloads` | integer |  |  |  |  |  | Maximum number of parallel downloads allowed for certain processes. This can be set to control the number of concurrent downloads to avoid overloading servers or hitting API rate limits. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage if running on Cloud infrastructure. |
| `--reference-data` | string (file path) |  |  |  | matches ^\S+\.[ct]sv$ |  | Path to comma-separated file containing information about references. |
| `--temp-dir` | string (directory path) |  |  |  |  |  | The location to save temporary files for processes. This is only used for some processes that produce large temporary files such as PICARD_SORTSAM. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

<!-- Generated from nf-core/pathogensurveillance@13547eaa7345dab4ac97db49775ae8284af4113d. Do not edit by hand. -->
