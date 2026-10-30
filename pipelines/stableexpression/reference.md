---
name: stableexpression
version: 1.1.0
commit: c4cbf82471391990cae257c0212be86f6b4fb18b
---

# stableexpression — full parameter reference

nf-core/stableexpression pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/` | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## idmapping_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--gene-id-mapping` | string (file path) |  |  |  | matches `^\S+\.(csv\|dat)$` |  | Custom gene id mapping file |
| `--gene-metadata` | string (file path) |  |  |  | matches `^\S+\.(csv\|dat)$` |  | Custom gene metadata file |
| `--gprofiler-target-db` | string |  |  | `ENSG`, `ENTREZGENE`, `UNIPROTSPTREMBL`, `UNIPROTSWISSPROT` |  | `ENSG` | Experimental: target database for g:Profiler |
| `--min-occurrence-freq` | number |  |  |  | ≥ 0; ≤ 1 | `0.1` | Minimum frequency of occurrence among all datasets |
| `--min-occurrence-quantile` | number |  |  |  | ≥ 0; ≤ 1 | `0.2` | Minimum quantile for the frequency of occurrence |
| `--skip-cleaning-gene-ids` | boolean |  |  |  |  |  | Skip cleaning gene IDs step |
| `--skip-id-mapping` | boolean |  |  |  |  |  | Skip g:Profiler ID mapping step |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--accessions-only` | boolean |  |  |  |  |  | Only get accessions from Expression Atlas / GEO and exit. |
| `--datasets` | string (file path) |  |  |  | matches `^\S+\.(csv\|yaml\|yml\|dat)$` |  | Custom datasets (counts + designs) |
| `--download-only` | boolean |  |  |  |  |  | Only get accessions from Expression Atlas / GEO and download the selected datasets. |
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--keywords` | string |  |  |  | matches `(([a-zA-Z,]+))?` |  | Keywords used for selecting specific Expression Atlas / GEO accessions |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | Output directory |
| `--platform` | string |  |  | `rnaseq`, `microarray` |  |  | Only download from this platform |
| `--species` | string |  |  |  | matches `^([a-zA-Z]+)[_ ]([a-zA-Z]+)[_ a-zA-Z]*$` |  | Scientifc species name (genus and species) |
| `--target-gene-file` | string (file path) |  |  |  |  |  | File containing target genes |
| `--target-genes` | string |  |  |  |  |  | Target genes |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

## missing_value_imputation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--missing-value-imputer` | string |  |  | `knn`, `iterative`, `simple` |  | `knn` | Type of imputation method to use for missing values |

## normalisation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--gene-length` | string (file path) |  |  |  | matches `^\S+\.(csv\|tsv\|dat)$` |  | Gene length file |
| `--gff` | string (file path) |  |  |  | matches `^\S+\.(gff\|gff3\|dat)(\.gz)?$` |  | Genome annotation file (GFF format) |
| `--gff-url` | string |  |  |  |  |  | URL to genome annotation file (GFF format) |
| `--normalisation-method` | string |  |  | `tpm`, `cpm` |  | `tpm` | Count normalisation method |
| `--quantile-norm-target-distrib` | string |  |  | `uniform`, `normal` |  | `uniform` | Target distribution for quantile normalisation |

## public_data_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--accessions` | string |  |  |  | matches `([A-Z0-9-]+,?)*` |  | Expression Atlas / GEO accession(s) to include |
| `--accessions-file` | string (file path) |  |  |  |  |  | File containing Expression Atlas / GEO accession(s) to download |
| `--excluded-accessions` | string |  |  |  | matches `([A-Z0-9-]+,?)*` |  | Expression Atlas accession(s) to exclude |
| `--excluded-accessions-file` | string (file path) |  |  |  |  |  | File containing Expression Atlas accession(s) to exclude |
| `--fetch-geo-accessions` | boolean |  |  |  |  |  | Fetch GEO accessions from NCBI [Experimental] |
| `--skip-fetch-eatlas-accessions` | boolean |  |  |  |  |  | Skip fetching Expression Atlas accessions |

## sample_filtering_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--max-null-ratio` | number |  |  |  | ≥ 0; ≤ 1 | `0.9` | Maximum ratio of null values |
| `--max-null-ratio-valid-sample` | number |  |  |  | ≥ 0; ≤ 1 | `0.75` | Maximum ratio of null values in a sample for it to be considered in the computation of the null value malus |
| `--max-zero-ratio` | number |  |  |  | ≥ 0; ≤ 1 | `0.9` | Maximum ratio of zero counts to total counts |

## scalability_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--random-sampling-seed` | integer |  |  |  | ≥ 0 | `42` | Seed for dataset random sampling. |
| `--random-sampling-size` | integer |  |  |  | ≥ 1 | `5000` | Number of public dataset samples to choose randomly before downloading. |

## stability_scoring_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--nb-candidates-per-section` | integer |  |  |  | ≥ 1 | `250` | Number of candidate genes to keep for stability scoring in each section |
| `--nb-sections` | integer |  |  |  | ≥ 1 | `10` | Number of sections to divide genes into for stability scoring. |
| `--skip-genorm` | boolean |  |  |  |  |  | Run Genorm |
| `--stability-score-weights` | string |  |  |  | matches `^\d+(\.\d+)?,\d+(\.\d+)?,\d+(\.\d+)?,\d+(\.\d+)?$` | `0.25,0.25,0.25,0.25` | Weights for stability score calculation |

<!-- Generated from nf-core/stableexpression@c4cbf82471391990cae257c0212be86f6b4fb18b. Do not edit by hand. -->
