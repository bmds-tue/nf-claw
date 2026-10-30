---
name: pangenome
version: 1.1.3
commit: 3d02bd1df79f48b4bfdb4ad95d4ca0d7f6aeb337
---

# pangenome — full parameter reference

nf-core/pangenome pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## community

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--communities` | boolean |  |  |  |  |  | Enable community detection. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/` | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--schema-ignore-params` | string |  | yes |  |  | `igenomes_base` | Do we want to display hidden parameters? |
| `--show-hidden-params` | boolean |  | yes |  |  |  | Do we want to display hidden parameters? |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to BGZIPPED input FASTA to build the pangenome graph from. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--n-haplotypes` | number | yes |  |  |  |  | The number of haplotypes in the input FASTA. |
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

## seqwish_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--seqwish-min-match-length` | integer |  |  |  |  | `23` | Ignores exact matches below this length. |
| `--seqwish-paf` | string |  |  |  |  |  | Input PAF file. The wfmash alignment step is skipped. |
| `--seqwish-sparse-factor` | number |  |  |  |  | `0` | Keep this randomly selected fraction of input matches. |
| `--seqwish-temp-dir` | string |  | yes |  |  |  | Set the directory where temporary files should be stored. Since everything runs in containers, we don't usually set this argument. |
| `--seqwish-transclose-batch` | string |  |  |  | matches `^([1-9]\d*[kKmMgGtT]?\|0)$` | `10000000` | Number of base pairs to use for transitive closure batch. |

## smoothxg_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-smoothxg` | boolean |  |  |  |  |  | Skip the graph smoothing step of the pipeline. |
| `--smoothxg-block-id-min` | string |  | yes |  |  |  | Minimum edit-based identity to cluster sequences. |
| `--smoothxg-block-ratio-min` | integer |  | yes |  |  | `0` | Minimum 'smallest / largest' sequence length ration to cluster in a block. |
| `--smoothxg-consensus-prefix` | string |  | yes |  |  | `Consensus_` | Use this prefix for consensus path names. |
| `--smoothxg-keep-intermediate-files` | boolean |  | yes |  |  |  | Keep intermediate graphs during SMOOTHXG. |
| `--smoothxg-max-edge-jump` | integer |  | yes |  |  | `0` | Maximum edge jump before a block is broken. |
| `--smoothxg-max-path-jump` | integer |  | yes |  |  | `0` | Maximum path jump to include in the block. |
| `--smoothxg-pad-max-depth` | integer |  |  |  |  | `100` | Path depth at which we don't pad the POA problem. |
| `--smoothxg-poa-cpus` | integer |  |  |  |  | `0` | Number of CPUs for the potentially very memory expensive POA phase of SMOOTHXG. Default is 'task.cpus'. |
| `--smoothxg-poa-length` | string |  |  |  |  | `700,900,1100` | Maximum sequence length to put int POA. Is a comma-separated list. For each integer, SMOOTHXG wil be executed once. |
| `--smoothxg-poa-padding` | number |  |  |  |  | `0.001` | Pad each end of each seuqence in POA with 'smoothxg_poa_padding * longest_poa_seq' base pairs. |
| `--smoothxg-poa-params` | string |  |  |  |  | `1,19,39,3,81,1` | Score parameters for POA in the form of 'match,mismatch,gap1,ext1,gap2,ext2'. It may also be given as presets: 'asm5', 'asm10', 'asm15', 'asm20'. [default: 1,19,39,3,81,1 = asm5]. |
| `--smoothxg-run-abpoa` | boolean |  |  |  |  |  | Run abPOA. [default: SPOA]. |
| `--smoothxg-run-global-poa` | boolean |  |  |  |  |  | Run the POA in global mode. [default: local mode]. |
| `--smoothxg-temp-dir` | string |  | yes |  |  |  | Set the directory where temporary files should be stored. Since everything runs in containers, we don't usually set this argument. |
| `--smoothxg-write-maf` | boolean |  |  |  |  |  | Write MAF output representing merged POA blocks. |

## vg_deconstruct_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--vcf-spec` | string |  |  |  |  |  | Specify a set of VCFs to produce with `--vcf_spec "REF[:LEN][,REF[:LEN]]*"`. |

## wfmash_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--wfmash-block-length` | string |  |  |  | matches `^([1-9]\d*[kKmMgGtT]?\|0)$` |  | Minimum block length filter for mapping. |
| `--wfmash-chunks` | integer |  |  |  |  | `1` | The number of files to generate from the approximate wfmash mappings to scale across a whole cluster. It is recommended to set this to the number of available nodes. If only one machine is available, leave it at 1. |
| `--wfmash-exclude-delim` | string |  |  |  |  |  | Skip mappings between sequences with the same name prefix before the given delimiter character. This can be helpful if several sequences originate from the same chromosome. It is recommended that the sequence names respect the https://github.com/pangenome/PanSN-spec. In future versions of the pipeline it will be required that the sequence names follow this specification. |
| `--wfmash-hg-filter-ani-diff` | integer |  |  |  |  | `30` | Filter out mappings unlikely to be this Average Nucleotide Identity (ANI) less than the best mapping. |
| `--wfmash-map-pct-id` | number |  |  |  |  | `90` | Percent identity in the wfmash mashmap step. |
| `--wfmash-mash-kmer` | integer |  |  |  |  | `19` | Kmer size for mashmap. |
| `--wfmash-mash-kmer-thres` | number |  |  |  |  | `0.001` | Ignore the top % most-frequent kmers. |
| `--wfmash-merge-segments` | boolean |  |  |  |  |  | Merge successive mappings. |
| `--wfmash-n-mappings` | integer |  |  |  |  |  | Number of mappings for each segment. [default: `n_haplotypes - 1`]. |
| `--wfmash-no-splits` | boolean |  | yes |  |  |  | Disable splitting of input sequences during mapping. |
| `--wfmash-only` | boolean |  |  |  |  |  | If this parameter is set, only the wfmash alignment step of the pipeline is executed. This option is offered for users who want to run wfmash on a cluster. |
| `--wfmash-segment-length` | string |  |  |  | matches `^([1-9]\d*[kKmMgGtT]?\|0)$` | `5000` | Segment length for mapping. |
| `--wfmash-sparse-map` | string |  |  |  | matches `(auto\|[01]\.\d+)` | `1.0` | Keep this fraction of mappings (`auto` for giant component heuristic). |
| `--wfmash-temp-dir` | string |  | yes |  |  |  | Set the directory where temporary files should be stored. Since everything runs in containers, we don't usually set this argument. |

<!-- Generated from nf-core/pangenome@3d02bd1df79f48b4bfdb4ad95d4ca0d7f6aeb337. Do not edit by hand. -->
