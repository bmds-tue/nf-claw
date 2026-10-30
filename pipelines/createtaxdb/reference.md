---
name: createtaxdb
version: 3.1.0
commit: b01a0f8ed96a5990d15470828dfa92a22cf08bba
---

# createtaxdb — full parameter reference

nf-core/createtaxdb pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## database_building_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bracken-build-options` | string |  |  |  |  |  | Specify parameters being given to bracken build. Parameters must be supplied in quotes: `--<tool>_build_options "--your_param"`. |
| `--build-bracken` | boolean |  |  |  |  |  | Turn on extending of Kraken2 database to include Bracken files. Requires nucleotide FASTA File input. |
| `--build-centrifuge` | boolean |  |  |  |  |  | Turn on building of Centrifuge database. Requires nucleotide FASTA file input. |
| `--build-centrifuger` | boolean |  |  |  |  |  | Turn on building of Centrifuger database. Requires nucleotide FASTA file input. |
| `--build-diamond` | boolean |  |  |  |  |  | Turn on building of DIAMOND database. Requires amino-acid FASTA file input. |
| `--build-ganon` | boolean |  |  |  |  |  | Turn on building of ganon database. Requires nucleotide FASTA file input. |
| `--build-kaiju` | boolean |  |  |  |  |  | Turn on building of Kaiju database. Requires amino-acid FASTA file input. |
| `--build-kmcp` | boolean |  |  |  |  |  | Turn on building of KMCP database. Requires nucleotide FASTA file input. |
| `--build-kraken2` | boolean |  |  |  |  |  | Turn on building of Kraken2 database. Requires nucleotide FASTA file input. |
| `--build-krakenuniq` | boolean |  |  |  |  |  | Turn on building of KrakenUniq database. Requires nucleotide FASTA file input. |
| `--build-malt` | boolean |  |  |  |  |  | Turn on building of MALT database. Requires nucleotide FASTA file input. |
| `--build-metacache` | boolean |  |  |  |  |  | Turn on building of MetaCache database. Requires nucleotide FASTA file input. |
| `--build-sourmash-dna` | boolean |  |  |  |  |  | Whether to build a sourmash reference from the provided nucleotide sequences. |
| `--build-sourmash-protein` | boolean |  |  |  |  |  | Whether to build a sourmash reference from the provided amino acid sequences. |
| `--build-sylph` | boolean |  |  |  |  |  | Turn on building of sylph database. Requires nucleotide FASTA file input. |
| `--centrifuge-build-options` | string |  |  |  |  |  | Specify parameters being given to centrifuge-build. Parameters must be supplied in quotes: `--<tool>_build_options "--your_param"`. |
| `--centrifuger-build-options` | string |  |  |  |  |  | Specify parameters being given to centrifuger-build. Parameters must be supplied in quotes: `--<tool>_build_options "--your_param"`. |
| `--diamond-build-options` | string |  |  |  |  |  | Specify parameters being given to diamond makedb. Parameters must be supplied in quotes: `--<tool>_build_options "--your_param"`. |
| `--ganon-build-options` | string |  |  |  |  |  | Specify parameters being given to ganon buildcustom. Parameters must be supplied in quotes: `--<tool>_build_options "--your_param"`. |
| `--kaiju-build-options` | string |  |  |  |  |  | Specify parameters being given to kaiju-mkbwt. Parameters must be supplied in quotes: `--<tool>_build_options "--your_param"`. |
| `--kaiju-keepintermediate` | boolean |  |  |  |  |  | Save intermediate files otherwise not required for downstream classification. |
| `--kmcp-compute-options` | string |  |  |  |  |  | Specify parameters being given to kmcp compute. Parameters must be supplied in quotes: `--<tool>_build_options "--your_param"`. |
| `--kmcp-index-options` | string |  |  |  |  |  | Specify parameters being given to kmcp index. Parameters must be supplied in quotes: `--<tool>_build_options "--your_param"`. |
| `--kraken2-build-options` | string |  |  |  |  |  | Specify parameters being given to kraken2 build. Parameters must be supplied in quotes: `--<tool>_build_options "--your_param"`. |
| `--kraken2-keepintermediate` | boolean |  |  |  |  |  | Retain intermediate Kraken2 build files for inspection. |
| `--krakenuniq-build-options` | string |  |  |  |  |  | Specify parameters being given to krakenuniq build. Parameters must be supplied in quotes: `--<tool>_build_options "--your_param"`. |
| `--krakenuniq-keepintermediate` | boolean |  |  |  |  |  | Save intermediate files otherwise not required for downstream classification. |
| `--malt-build-options` | string |  |  |  |  | `--sequenceType DNA` | Specify parameters given to malt-build. Must include --sequenceType DNA or --sequenceType Protein. Parameters must be supplied in quotes: `--malt_build_options "--sequenceType DNA --your_param". |
| `--metacache-build-options` | string |  |  |  |  |  | Specify parameters being given to metacache build. |
| `--sourmash-batch-size` | integer |  |  |  | ≥ 1 | `100` | Sourmash can perform the main build step in parallel batches. Set the size of the batches. |
| `--sourmash-build-dna-options` | string |  |  |  |  | `--param-string \'scaled=1000,k=31,noabund\` | Specify parameters given to sourmash sketch dna. Must start with sourmash sketch dna's '--param-string'. |
| `--sourmash-build-protein-options` | string |  |  |  |  | `--param-string \'scaled=200,k=10,noabund\` | Specify parameters given to sourmash sketch protein. Must start with sourmash sketch protein's '--param-string'. |
| `--sylph-build-options` | string |  |  |  |  |  | Specify parameters being given to sylph sketch. |

## generate_samplesheet_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--generate-downstream-samplesheets` | boolean |  |  |  |  |  | Turn on generation of samplesheets for downstream pipelines. |
| `--generate-pipeline-samplesheets` | string |  |  |  | matches `^(taxprofiler)(?:,(taxprofiler)){0,1}` |  | Specify a comma separated string in quotes to specify which pipeline to generate a samplesheet for. |

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
| `--unzip-batch-size` | integer | yes |  |  |  | `10000` | How many files to unzip in parallel in a single job. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_file_preprocessing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--save-concatenated-fastas` | boolean |  |  |  |  |  | Save uncompressed concatenated input FASTAs. |
| `--save-uncompressed-auxfiles` | boolean |  |  |  |  |  | Save automatically unzipped input auxiliary files. |
| `--save-uncompressed-fastas` | boolean |  |  |  |  |  | Save uncompressed input FASTAs. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--accession2taxid` | string (file path) |  |  |  |  |  | NCBI-style four-column accession to taxonomy ID map file. |
| `--dbname` | string | yes |  |  |  |  | Specify name that resulting databases will be prefixed with. |
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--genomesizes` | string |  |  |  |  |  | Path to NCBI or GTDB genome sizes file. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--malt-mapdb` | string (file path) |  |  |  |  |  | Path to MEGAN6/MALT mapping db file. |
| `--malt-mapdb-format` | string |  |  | `mdb`, `a2t`, `s2t`, `a2ec`, `s2ec`, `t4ec`, `a2eggnog`, `s2eggnog`, `t4eggnog`, `a2gtdb`, `s2gtdb`, `t4gtdb`, `a2interpro2go`, `s2interpro2go`, `t4interprotogo`, `a2kegg`, `s2kegg`, `t4kegg`, `a2pgpt`, `s2pgpt`, `t4pgpt`, `a2seed`, `s2seed`, `t4seed` |  |  | Specify the type of MALT mapdb provided, based on the corresponding MALT flag. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--namesdmp` | string (file path) |  |  |  |  |  | Path to NCBI-style taxonomy names dmp file. |
| `--nodesdmp` | string (file path) |  |  |  |  |  | Path to NCBI-style taxonomy node dmp file. |
| `--nucl2taxid` | string (file path) |  |  |  |  |  | Two column nucleotide sequence accession ID to taxonomy map file. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--prot2taxid` | string (file or directory path) |  |  |  |  |  | Two column protein sequence accession ID to taxonomy map file. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

<!-- Generated from nf-core/createtaxdb@b01a0f8ed96a5990d15470828dfa92a22cf08bba. Do not edit by hand. -->
