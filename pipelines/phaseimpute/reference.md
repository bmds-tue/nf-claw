---
name: phaseimpute
version: 1.1.0
commit: 452783d960ebd2b4d337a649e9c8eb3859611916
---

# phaseimpute — full parameter reference

nf-core/phaseimpute pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

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
| `--multiqc-replace-names` | string |  |  |  |  |  | Optional two-column sample renaming file. First column a set of patterns, second column a set of corresponding replacements. Passed via MultiQC's `--replace-names` option. |
| `--multiqc-sample-names` | string |  |  |  |  |  | Optional TSV file with headers, passed to the MultiQC --sample_names argument. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/phaseimpute/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## imputation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--batch-size` | integer |  |  |  |  | 100 | Maximal number of individuals per batch for imputation. |
| `--chunks` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|yaml\|json)$ |  | Path to comma or tab-separated file, yaml or json file containing genomic chunks to be used for imputation. |
| `--posfile` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|yaml\|json)$ |  | Path to comma or tab-separated file, yaml or json file containing reference panel information converted files for imputation. |
| `--seed` | integer |  | yes |  |  | 1 | Seed for random number generation in Stitch and Quilt software |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|yaml\|json)$ |  | Path to comma or tab-separated file, yaml or json file containing information about the samples in the experiment. |
| `--input-region` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|yaml\|json)$ |  | Path to comma or tab-separated file, yaml or json file containing region of the genome to use (optional: if no file given, the whole genome will be used). |
| `--max-chr-names` | integer |  | yes |  |  | 4 | Maximum number of contigs name to print before resuming (i.e. show only subset and add '...' at the end). |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--remove-samples` | string |  |  |  | matches ^([a-zA-Z0-9]+)(,[a-zA-Z0-9]+)*$ |  | Comma-separated list of samples to remove from the reference panel. Useful for benchmarking purposes. |
| `--rename-chr` | boolean |  |  |  |  |  | Should the panel VCF files be renamed to match the reference genome (e.g. 'chr1' -> '1') |
| `--steps` | string |  |  |  | matches ^((all\|simulate\|panelprep\|impute\|validate)?,?)*(?<!,)$ |  | Step(s) to run. |
| `--tools` | string |  |  |  | matches ^((glimpse1\|glimpse2\|quilt\|stitch\|beagle5\|minimac4)?,?)*(?<!,)$ |  | Imputation tool to use. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## panelprep

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--chunk-model` | string |  | yes | `recursive`, `sequential` |  | sequential | Model type to use for GLIMPSE2_CHUNK |
| `--compute-freq` | boolean |  |  |  |  |  | Should the allele frequency for each variant (AC/AN fields necessary for Glimpse1 and the validation step) be computed using VCFFIXUP tool. This can be necessary if the fields are absent from the panel or if samples have been removed. |
| `--normalize` | boolean |  |  |  | matches true\|false |  | Should the reference panel be normalized |
| `--panel` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|yaml\|json)$ |  | Path to comma or tab-separated file, yaml or json file containing reference panel information. |
| `--phase` | boolean |  |  |  | matches true\|false |  | Should the reference panel be phased |

## quilt_parameters

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--buffer` | integer |  |  |  |  | 10000 | Buffer of region to perform imputation over. So imputation is run form regionStart-buffer to regionEnd+buffer, and reported for regionStart to regionEnd, including the bases of regionStart and regionEnd. |
| `--ngen` | integer |  |  |  |  | 100 | Number of generations since founding of the population to use for imputation. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to FASTA genome file. |
| `--fasta-fai` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?\.fai$ |  | Path to FASTA index genome file. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--igenomes-base` | string (directory path) |  | yes |  |  | s3://ngi-igenomes/igenomes/ | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--map` | string (file path) |  |  |  |  |  | Path to gmap genome file. |

## simulate

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--depth` | number |  |  |  | ≥ 0 | 1 | Depth of coverage for the simulated data |
| `--genotype` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|yaml\|json)$ |  | Genotype position to use to simulate the data |

## stitch_parameters

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--k-val` | integer |  |  |  |  | 2 | Number of ancestral haplotypes to use for imputation. Refer to the documentation for the `--K` argument of STITCH for more information. |

## validation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bins` | string |  |  |  | matches ^(\d+(\.\d+)? )+(\d+(\.\d+)?)$ | 0 0.01 0.05 0.1 0.2 0.5 | User-defined allele count bins used for rsquared computations. |
| `--input-truth` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|yaml\|json)$ |  | Path to comma or tab-separated file, yaml or json file containing samples truth files informations. |
| `--min-val-dp` | integer |  |  |  | matches ^\d+$ | 5 | Minimum coverage in validation data. If FORMAT/DP is missing and -min_val_dp > 0, the program exits with an error. Set to zero to have no filter of if using –gt-validation |
| `--min-val-gl` | number |  |  |  | matches ^\d+(\.\d+)?$; ≥ 0 | 0.9 | Minimum genotype likelihood probability P(G\|R) in validation data. Set to zero to have no filter, if using gt-validation |

<!-- Generated from nf-core/phaseimpute@452783d960ebd2b4d337a649e9c8eb3859611916. Do not edit by hand. -->
