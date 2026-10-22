---
name: bacmodel
version: 1.0.0
commit: 1abf4e28d250edf801c0f671a19f233f18128875
---

# bacmodel — full parameter reference

nf-core/bacmodel pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## analysis_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--carveme-mediadb` | string (file path) |  |  |  |  |  | Path to CarveMe media database TSV file (columns: `medium, description, compound, name`). If not provided, uses CarveMe's default media database. See [example file](../assets/medium_carveme_mediadb_example.tsv). |
| `--gapseq-db` | string |  |  |  |  |  | Directory containing a pre-downloaded gapseq reference sequence database (a `Bacteria` subdirectory, as produced by `gapseq update-sequences -D <dir>`). If present, the live Zenodo download is skipped - set this to a pre-downloaded copy if your compute nodes lack outbound internet access to Zenodo. If unset, defaults to `<outdir>/databases/gapseq`. |
| `--gapseq-doall-args` | string |  |  |  |  | -b 200 -A diamond | Custom arguments for the simplified `gapseq doall` search step. Only used in the default doall workflow - ignored if any of the `gapseq_find_args`, `gapseq_findtransport_args`, `gapseq_draft_args`, `gapseq_medium_args`, or `gapseq_fill_args` below are set, since that switches to the custom/stepwise workflow instead. |
| `--gapseq-draft-args` | string |  |  |  |  |  | Custom arguments for `gapseq draft` - draft model construction (default: none) |
| `--gapseq-fill-args` | string |  |  |  |  |  | Custom arguments for `gapseq fill` - gap-filling (default: none) |
| `--gapseq-find-args` | string |  |  |  |  |  | Custom arguments for `gapseq find` - pathway prediction (default: `-b 200 -A diamond`) |
| `--gapseq-findtransport-args` | string |  |  |  |  |  | Custom arguments for `gapseq find-transport` - transporter prediction (default: `-b 200`) |
| `--gapseq-medium-args` | string |  |  |  |  |  | Custom arguments for `gapseq medium` - add/remove specific compounds on top of the predicted medium, e.g. `-c "cpd00007:0"` to remove oxygen (default: none; ignored for samples with their own `medium_gapseq_csv` file) |
| `--macsyfinder-db` | string |  |  |  |  |  | Directory containing pre-downloaded MacSyFinder models, or ones published by a previous run of this pipeline (one subdirectory per `macsyfinder_models` value). If unset, models are downloaded automatically into `<outdir>/databases/macsyfinder` on first use and reused from there by later runs that point `--macsyfinder_db` at the same `<outdir>/databases/macsyfinder`. |
| `--macsyfinder-db-type` | string |  |  | `unordered`, `ordered_replicon`, `gembase` |  | unordered | MacSyFinder --db-type: `unordered` for MAGs/draft assemblies with unreliable gene order (default, most permissive), `ordered_replicon` for a single complete/nearly-complete genome (enables synteny-aware detection), or `gembase` for multiple complete replicons in one gembase-formatted database |
| `--macsyfinder-models` | string |  |  |  |  | TXSS | MacSyFinder models to use (TXSS for Type III/IV/VI secretion systems) |
| `--skip-carveme` | boolean |  |  |  |  | false | Skip CarveMe genome-scale metabolic reconstruction |
| `--skip-gapseq` | boolean |  |  |  |  | true | Skip Gapseq pathway analysis and metabolic modeling |
| `--skip-macsyfinder` | boolean |  |  |  |  | false | Skip MacSyFinder macromolecular systems detection |
| `--skip-memote` | boolean |  |  |  |  | true | Skip MEMOTE metabolic model quality evaluation (only runs when `skip_gapseq=false` or `skip_carveme=false`) |
| `--skip-traitar` | boolean |  |  |  |  | false | Skip TRAITAR phenotype prediction |

## annotation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annotation-tool` | string |  |  | `prokka`, `bakta` |  | prokka | Tool to use for genome annotation |
| `--bakta-db` | string |  |  |  |  |  | Directory containing a pre-downloaded Bakta database, or one published by a previous run of this pipeline (only used when `annotation_tool=bakta`). If unset, the database is downloaded automatically into `<outdir>/databases/bakta` on first use and reused from there by later runs that point `--bakta_db` at the same `<outdir>/databases/bakta`. |
| `--bakta-db-type` | string |  |  | `light`, `full` |  | light | Bakta database type to download |
| `--min-contig-length` | integer |  |  |  |  | 200 | Minimum contig length for annotation and analysis |

## database_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--pfam-db` | string |  |  |  |  |  | Directory containing a pre-downloaded Pfam database, or one published by a previous run of this pipeline (only used when `skip_traitar`=false). If unset, the database is downloaded automatically into `<outdir>/databases/pfam` on first use and reused from there by later runs that point `--pfam_db` at the same `<outdir>/databases/pfam`. |

## deprecated_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--run-carveme` | boolean |  | yes |  | deprecated |  |  |
| `--run-gapseq` | boolean |  | yes |  | deprecated |  |  |
| `--run-macsyfinder` | boolean |  | yes |  | deprecated |  |  |
| `--run-memote` | boolean |  | yes |  | deprecated |  |  |
| `--run-traitar` | boolean |  | yes |  | deprecated |  |  |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
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
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.(csv\|tsv)$ |  | Path to comma-separated or tab-separated file containing information about the samples in the experiment. |
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

<!-- Generated from nf-core/bacmodel@1abf4e28d250edf801c0f671a19f233f18128875. Do not edit by hand. -->
