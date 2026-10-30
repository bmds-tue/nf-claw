---
name: plasmodiumdrugres
version: 1.0.0
commit: a333327a245ccb3c0f1a37167a7afe670c35894e
---

# plasmodiumdrugres — full parameter reference

nf-core/plasmodiumdrugres pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/refs/heads/plasmodiumdrugres/` | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--allele-table` | string (file path) |  |  |  | matches `^\S+\.[ct]sv$` |  | Path to tab separated file containing microhaplotypes for specimens. |
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | null (file path) |  | yes |  |  |  | Path to input samplesheet (unused; kept for nf-core template lint compatibility). |
| `--loci-groups` | string or null (file path) |  |  |  | matches `^\S+\.[ct]sv$` |  | Path to tab separated file containing groups of loci of interest. Multi-locus allele frequency estimation is skipped when this parameter is not provided. |
| `--loci-of-interest-bed` | string (file path) | yes |  |  | matches `^\S+\.bed$` |  | Path to BED file containing individual loci of interest. |
| `--outdir` | string (directory path) |  |  |  |  | `output` | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--panel-info-bed` | string (file path) |  |  |  | matches `^\S+\.bed$` |  | Path to BED file containing panel location information. |
| `--pmo` | string (file path) |  |  |  | matches `^\S+\.json(\.gz)?$` |  | Path to json file containing metadata and microhaplotypes according to pmo format. |
| `--pmo-population-fields` | string or null |  |  |  |  |  | Comma-separated list of PMO specimen metadata field names to combine into the population label (e.g. "collection_country, collection_date"). Whitespace is ignored. |
| `--pmo-population-separator` | string or null |  |  |  |  | `_` | String used to join the selected `pmo_population_fields` when building the population label. |
| `--pmo-replicate-libraries` | string |  |  | `combine`, `max_reads` |  | `combine` | How to handle specimens with more than one library sample in the PMO. |
| `--population-assignment` | string (file path) |  |  |  | matches `^\S+\.[ct]sv$` |  | Path to tab separated file containing population assignment for each specimen_name. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

## method_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--collapse-calls-by-summing` | boolean |  |  |  |  | `true` | Sum amino acid calls across all targets covering a locus instead of using only the target with the highest read count. |
| `--dcifer-slaf-wrapper-coi-lrank` | integer or null |  | yes |  |  |  | COI lrank for dcifer slaf wrapper. |
| `--dcifer-slaf-wrapper-qstart` | number or null |  | yes |  |  |  | qstart for dcifer slaf wrapper. |
| `--dcifer-slaf-wrapper-tol` | number or null |  | yes |  |  |  | tolerance for dcifer slaf wrapper. |
| `--fem-coi` | number |  |  |  | ≥ 1 | `3` | Average complexity of infection (COI) assumed for every specimen when --mlaf_method is FEM. |
| `--mlaf-method` | string |  |  | `MLBM`, `FEM`, `naive` |  | `naive` | Method for multi-locus allele frequency estimates. |
| `--mlbm-wrapper-aa-specimen-occurence-cut-off` | integer or null |  | yes |  |  |  | when running MLBM, a cut off value for filtering amino acid calls. |
| `--naive-mlaf-method` | string |  |  | `wsaf_prop`, `presence_absence` |  | `wsaf_prop` | Naive MLAF method when --mlaf_method is naive. |
| `--naive-multilocus-wsaf-cut-off` | number or null |  | yes |  |  |  | wsaf cut off for naive multilocus estimates. |
| `--naive-slaf-method` | string |  |  | `read_count_prop`, `presence_absence` |  | `read_count_prop` | Naive SLAF method when --slaf_method is naive. |
| `--population-label` | string |  |  |  |  | `pop1` | label for population/ this individual pipeline run. |
| `--slaf-method` | string |  |  | `IDM`, `naive`, `mhaps_freq` |  | `naive` | Method for single-locus allele frequency estimates. |
| `--slaf-method-mhaps-freq-method` | string |  |  | `dcifer` |  | `dcifer` | Tool used for --slaf_method mhaps_freq. |
| `--translate-loci-extra-args` | string |  |  |  |  |  | Extra arguments supplied when translating loci of interest |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--genome-reference` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA file containing the full genome. |
| `--targeted-reference` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA file containing the reference for only the targets. |

<!-- Generated from nf-core/plasmodiumdrugres@a333327a245ccb3c0f1a37167a7afe670c35894e. Do not edit by hand. -->
