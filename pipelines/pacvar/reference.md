---
name: pacvar
version: 1.1.0
commit: 20364830237171928c79e59651142460379d1459
---

# pacvar — full parameter reference

nf-core/pacvar pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## annotation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--outdir-vep-cache` | string (directory path) |  |  |  |  |  | Output directory where the downloaded VEP cache will be saved. Only used when `--download_vep_cache true`. Use absolute paths on cloud infrastructure. Note: when set, the cache is published outside `--outdir`. |
| `--skip-ensemblvep` | boolean |  |  |  |  | false | Option to skip SNVs annotation with Ensembl VEP. |
| `--vep-custom-args-cnv` | string |  |  |  |  | --per_gene --buffer_size 5000 --max_sv_size 250000000 --offline --format vcf | Add extra custom arguments to VEP for CNV annotation. |
| `--vep-custom-args-snv` | string |  |  |  |  | --everything --filter_common --per_gene --total_length --offline --format vcf | Add an extra custom argument to VEP. |
| `--vep-custom-args-sv` | string |  |  |  |  | --per_gene --buffer_size 5000 --max_sv_size 250000000 --offline --format vcf | Add extra custom arguments to VEP for SV annotation. |
| `--vep-out-format` | string |  |  | `json`, `tab`, `vcf` |  | vcf | VEP output-file format. |

## general_workflow_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--workflow` | string |  |  | `wgs`, `repeat` |  | wgs | Option to choose which workflow type to run |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/refs/heads/pacvar/ | Base URL or local path to location of pipeline test dataset files |
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
| `--input` | string (file path) | yes |  |  | matches ^\S+\.(csv\|tsv\|json\|yaml\|yml)$ |  | Path to comma-separated file containing information about the samples in the experiment. |
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

## methylation_profiling

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-cpg` | boolean |  |  |  |  | false | Skip CpG site probability for 5mC methylation calling |
| `--skip-fiberseq` | boolean |  |  |  |  | true | Skip Fiber-seq nucleosome annotation with fibertools-rs |
| `--skip-m6A-predict` | boolean |  |  |  |  | true | Skip fibertools-rs m6A prediction and use existing m6A calls for Fiber-seq nucleosome annotation |

## pre_processing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--barcodes` | string (file path) |  |  |  | matches ^\S+\.fn?a(sta)?(\.gz)?$ |  | Fasta file of barcodes |
| `--intervals` | string (file path) |  |  |  | matches ^\S+\.bed$ |  | Path to BED file containing intervals for either variant calling or for repeat expansion characterization |
| `--skip-demultiplexing` | boolean |  |  |  |  |  | Option to skip demultiplexing |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dbsnp` | string (file path) |  |  |  | matches ^\S+\.vcf\.gz$ |  | Path to dbsnp VCF file |
| `--dbsnp-tbi` | string (file path) |  |  |  | matches ^\S+\.vcf\.gz\.tbi$ |  | Path to index file of the dbsnp VCF file |
| `--dict` | string (file path) |  |  |  | matches ^\S+\.dict$ |  | Path to dict for variant calling |
| `--download-vep-cache` | boolean |  |  |  |  | false | Download Ensembl VEP cache |
| `--fasta` | string (file path) |  |  |  | matches ^\S+\.(fn?a(sta)?\|mmi)(\.gz)?$ |  | Path to FASTA genome or MMI file. |
| `--fasta-fai` | string (file path) |  |  |  | matches ^\S+\.fai$ |  | Path to FASTA index |
| `--genome` | string |  |  |  |  |  | Name of iGenomes reference. |
| `--igenomes-base` | string |  | yes |  |  | s3://ngi-igenomes/igenomes/ | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |
| `--vep-cache` | string (directory path) |  |  |  |  | s3://annotation-cache/vep_cache/ | Path to VEP cache. |
| `--vep-cache-version` | string |  |  |  |  |  | VEP cache version. |
| `--vep-genome` | string |  |  |  |  |  | VEP genome. |
| `--vep-species` | string |  |  |  |  |  | VEP species. |

## repeat

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--repeat-id` | string |  |  |  |  |  | If no sample-specific repeat ID to be plotted is provided in the samplesheet, this value will be used |

## variant

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cnv-excluded-regions` | string (file path) |  |  |  | matches ^\S+\.bed(\.gz)?$ |  | BED/BED.GZ file of regions to exclude from CNV calling. |
| `--expected-cn` | string (file path) |  |  |  | matches ^\S+\.bed(\.gz)?$ |  | BED/BED.GZ file specifying expected copy-number regions (for sawfish/hificnv). |
| `--skip-hificnv` | boolean |  |  |  |  | false | Skip HiFiCNV copy number variant calling |
| `--skip-phase` | boolean |  |  |  |  | false | Option to skip phasing |
| `--skip-snp` | boolean |  |  |  |  | false | Option to skip SNP variant calling |
| `--skip-sv` | boolean |  |  |  |  | false | Option to skip SV variant calling |
| `--snv-caller` | string |  |  | `deepvariant`, `gatk4` |  | deepvariant | The tool to use for calling SNP variants |
| `--sv-caller` | string |  |  | `pbsv`, `sawfish` |  | sawfish | The tool to use for calling structural variants |

<!-- Generated from nf-core/pacvar@20364830237171928c79e59651142460379d1459. Do not edit by hand. -->
