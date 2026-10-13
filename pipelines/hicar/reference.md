---
name: hicar
version: 1.0.0
commit: 429087d2b13e59c3edd2e71b8005c1adc5bbb7bb
---

# hicar — full parameter reference

nf-core/hicar pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## MACS2_peak_calling_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--high-resolution-R1` | boolean |  |  |  |  |  | read peak calling for fragment (R1) reads by MACS2 |
| `--qval-thresh` | number |  |  |  |  | 0.01 | cutoff qvalue |
| `--r1-pval-thresh` | number |  |  |  |  | 0.1 | cutoff pvalue for fragment (R1) |
| `--shiftsize` | integer |  |  |  |  | -75 | shift size for MACS2 |
| `--smooth-window` | integer |  |  |  |  | 150 | extsize for MACS2 |

## MAPS_peak_calling_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cool-bin` | string |  |  |  |  | 5000_10000 | resolution bin size |
| `--feature-frag2bin-source` | string |  | yes |  |  | https://raw.githubusercontent.com/ijuric/MAPS/91c9c360092b25a217d91b9ea07eba5dd2ac72f4/bin/utils/genomic_features_generator/scripts/feature_frag2bin.py | feature_frag2bin source path |
| `--make-maps-runfile-source` | string |  | yes |  |  | https://raw.githubusercontent.com/ijuric/MAPS/18c1a337f222130d7c5735d051614e2a253d5319/bin/MAPS/make_maps_runfile.py | make_maps_runfile source path |
| `--maps-cutoff-counts` | integer |  |  |  |  | 12 | MAPS regression cutoff value |
| `--maps-cutoff-fdr` | number |  |  |  |  | 2 | MAPS regression -log10(fdr) cutoff value |
| `--maps-cutoff-fold-change` | number |  |  |  |  | 2 | MAPS regression fold change cutoff value |
| `--maps-digest-file` | string |  |  |  |  | None | output of restriction_cut_multipleenzyme.py. |
| `--maps-filter` | string |  |  |  |  | None | MAPS regression filter file name |
| `--maps-model` | string |  |  | `pospoisson`, `negbinom` |  | pospoisson | MAPS regression type |
| `--merge-map-py-source` | string |  | yes |  |  | https://raw.githubusercontent.com/ijuric/MAPS/91c9c360092b25a217d91b9ea07eba5dd2ac72f4/bin/utils/genomic_features_generator/scripts/merge_map.py | source code path for merge_map.py |
| `--peak-pair-block` | number |  | yes |  |  | 1000000000 | The block number of peak pair |
| `--remove-dup` | boolean |  | yes |  |  |  | remove duplicates for high resolution peaks or not |
| `--snow-type` | string |  |  |  |  | SOCK | Type of snow cluster to use |

## Other_options_not_expose_yet

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--enrichment-fdr` | number |  | yes |  |  |  | cutoff value for false discovery rate of enrichment analysis |
| `--skip-igv` | boolean |  | yes |  |  |  | skip creat IGV files or not |
| `--skip-peak-qc` | boolean |  | yes |  |  |  | skip peak QC or not |
| `--skip-plot-profile` | boolean |  | yes |  |  |  | skip plot profile or not |
| `--skip-trackhub` | boolean |  | yes |  |  |  | skip create trackhub files or not |

## Visualization_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--juicer-jvm-params` | string |  |  |  |  | -Xms512m -Xmx4096m | JVM heap parameters for juicer |
| `--juicer-tools-jar` | string |  |  |  |  | https://s3.amazonaws.com/hicfiles.tc4ga.com/public/juicer/juicer_tools_1.22.01.jar | The juicer_tools path |
| `--v4c-max-events` | integer |  |  |  |  | 25 | max events to plot for virtual 4c |
| `--virtual-4c` | boolean |  |  |  |  |  | create track files for virtual 4c or not |

## experiment_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--enzyme` | string |  |  |  |  | CviQI | Specifies that the cutting position has to be using. |
| `--restriction-sites` | string |  | yes |  |  | ^TAC | Specifies that the cutting sequence has to be using. |
| `--restriction-sites-cut-off` | number |  |  |  |  | 0.5 | Specifies that the cutoff value used for mappability filter. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--enable-conda` | boolean |  | yes |  |  |  | Run this workflow with Conda. You can also use '-profile conda' instead of providing this parameter. |
| `--help` | boolean |  | yes |  |  |  | Display help text. |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--show-hidden-params` | boolean |  | yes |  |  |  | Show all params when using `--help` |
| `--tracedir` | string |  | yes |  |  | ${params.outdir}/pipeline_info | Directory to keep pipeline Nextflow logs and reports. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--anchor-peaks` | string (file path) |  |  |  | matches ^\S+\.(narrowPeak\|boradPeak)$ |  | Path to anchor peaks |
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--method` | string |  |  |  |  | HiCAR | Metho for the experiment. |
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

## max_job_request_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--max-cpus` | integer |  | yes |  |  | 16 | Maximum number of CPUs that can be requested for any single job. |
| `--max-memory` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 128.GB | Maximum amount of memory that can be requested for any single job. |
| `--max-time` | string |  | yes |  | matches ^(\d+\.?\s*(s\|m\|h\|day)\s*)+$ | 240.h | Maximum amount of time that can be requested for any single job. |

## pipeline_controls

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-cutadapt` | boolean |  |  |  |  |  | skip trim 5'end TAC |
| `--skip-diff-analysis` | boolean |  |  |  |  |  | skip differential analysis or not |
| `--skip-enrichment` | boolean |  |  |  |  | true | skip enrichment or not |
| `--skip-fastqc` | boolean |  |  |  |  |  | skip fastqc or not |
| `--skip-multiqc` | boolean |  |  |  |  |  | skip multiqc or not |
| `--skip-peak-annotation` | boolean |  |  |  |  |  | skip peak annotation or not |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--blacklist` | string (file path) |  |  |  |  |  | Path to blacklist regions in BED format, used for filtering alignments. |
| `--bwa-index` | string |  |  |  |  |  | Path to bwa index file. |
| `--fasta` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Path to FASTA genome file. |
| `--gene-bed` | string (file path) |  |  |  |  |  | Path to annotation gene bed file. |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--gff` | string (file path) |  |  |  |  |  | Path to annotation gff file. |
| `--gtf` | string (file path) |  |  |  |  |  | Path to annotation gtf file. |
| `--igenomes-base` | string (directory path) |  | yes |  |  | s3://ngi-igenomes/igenomes | Directory / URL base for iGenomes references. |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--macs-gsize` | string |  |  |  |  |  | Effective genome size parameter required by MACS2. |
| `--mappability` | string (file path) |  |  |  |  |  | Path to genome mappability file. |
| `--ucscname` | string |  |  |  |  |  | UCSC assembly annotation name. |

<!-- Generated from nf-core/hicar@429087d2b13e59c3edd2e71b8005c1adc5bbb7bb. Do not edit by hand. -->
