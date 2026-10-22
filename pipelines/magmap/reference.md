---
name: magmap
version: 1.3.0
commit: 7cd374473c4118859b655e627ced6a80c0cf5c60
---

# magmap — full parameter reference

nf-core/magmap pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## featurecounts_option

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--featurecounts-fraction` | boolean |  |  |  |  |  | Allow featureCounts to handle multiple-mapping |
| `--features` | string |  |  |  |  | CDS,rRNA,tRNA,tmRNA | Specify which features to count |

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
| `--annotator` | string |  |  | `prokka`, `bakta_supported_only`, `bakta_all` |  | prokka | Which tool to annotate genomes lacking a GFF with: 'prokka', 'bakta_supported_only' (Bacteria to Bakta, everything else -- Archaea and unclassified genomes -- to Prokka) or 'bakta_all' (everything to Bakta, including domains Bakta wasn't designed for). |
| `--bakta-db` | string (directory path) |  |  |  |  | magmap_bakta_db | Path to a directory holding the Bakta database, used only when --annotator is bakta_supported_only or bakta_all. |
| `--bakta-store-dir` | string (directory path) |  |  |  |  | magmap_bakta | Path to a directory where Bakta annotation output is stored. |
| `--checkm-metadata` | string |  |  |  |  |  | Comma-separated list of path to tab-separated files containing the output from CheckM. For column description, see [usage docs](https://nf-co.re/magmap/usage#checkmcheckm2-metadata). |
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--genome-store-dir` | string (directory path) |  |  |  |  | magmap_genomes | Path to a directory where downloaded genome files is stored. |
| `--genomeinfo` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|yaml\|yml\|json)$ |  | Path to a file containing information about the genomes to map to, see [usage docs](https://nf-co.re/magmap/usage#genome-input). |
| `--gtdb-metadata` | string |  |  |  |  |  | Comma-separated list of paths to tab-separated files containing information from GTDB. For column description, see [usage docs](https://nf-co.re/magmap/usage#gtdb-metadata). |
| `--gtdbtk-metadata` | string |  |  |  |  |  | Comma-separated list of paths to tab-separated files containing a .tsv file which has the same columns as the output from GTDB-Tk, see [usage docs](https://nf-co.re/magmap/usage#gtdb-tk-metadata). |
| `--indexes` | string |  |  |  |  |  | Comma-separated list of paths to Sourmash .sbt/.sbt.zip files. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.(csv\|tsv\|yaml\|yml\|json)$ |  | Path to a file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--prokka-store-dir` | string (directory path) |  |  |  |  | magmap_prokka | Path to a directory where prokka output is stored. |
| `--remote-genome-sources` | string |  |  |  |  | https://ftp.ncbi.nlm.nih.gov/genomes/ASSEMBLY_REPORTS/assembly_summary_refseq.txt,https://ftp.ncbi.nlm.nih.gov/genomes/ASSEMBLY_REPORTS/assembly_summary_genbank.txt | Comma-separated list of paths to tsv files with information about genomes in NCBI 'assembly_summary' format. The default are GenBank and RefSeq summary files. |
| `--save-parquet` | boolean |  |  |  |  |  | Also write the summary tables in Parquet format, alongside the default gzipped TSV. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## mapping_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bbmap-ambiguous` | string |  |  | `best`, `all`, `random`, `toss` |  | best | Select how BBmap should treat ambiguous mapping |
| `--bbmap-minid` | number |  |  |  |  | 0.9 | Minimal identity for BBmap |
| `--bbmap-save-bam` | boolean |  |  |  |  |  | Save bam output file |
| `--bbmap-save-index` | boolean |  |  |  |  |  | Save ref folder containing the reference index |
| `--save-concatenated-genomes` | boolean |  |  |  |  |  | Save genomes concatenated file |
| `--sequence-filter` | string |  |  |  |  |  | Instructs BBduk to use a fasta file to filter away sequences before running further analysis. |

## quality_control_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip FastQC. |
| `--skip-qc` | boolean |  |  |  |  |  | Skip all QC steps except for MultiQC. |

## sourmash_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--genomeset-mode` | string |  |  | `joint`, `sample` |  | joint | Perform mapping on all genomes for all samples ('joint') or sample-specific selections of genomes ('sample'). |
| `--skip-sourmash` | boolean |  |  |  |  | true | Skip Sourmash filtering for user-provided genomes |
| `--sourmash-ksize` | integer |  |  |  |  | 21 | K-mer size used by Sourmash |
| `--sourmash-save-sourmash` | boolean |  |  |  |  |  | Save Sourmash output |
| `--species-preference` | string |  |  | `all`, `local`, `completeness`, `gtdb` |  | all | Select genomes from the same species: 'all', 'local' (prefer local genomes), 'completeness' (prefer the most complete) or 'gtdb' (use GTDB's criterion of completeness and contamination) |

## trimming_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clip-r1` | string |  |  |  |  |  | Instructs Trim Galore to remove bp from the 5' end of read 1 (or single-end reads). |
| `--clip-r2` | string |  |  |  |  |  | Instructs Trim Galore to remove bp from the 5' end of read 2 (or single-end reads). |
| `--save-trimmed` | boolean |  |  |  |  |  | Save the trimmed FastQ files in the results directory. |
| `--skip-trimming` | boolean |  |  |  |  |  | Skip the adapter trimming step. |
| `--three-prime-clip-r1` | string |  |  |  |  |  | Instructs Trim Galore to remove bp from the 3' end of read 1 AFTER adapter/quality trimming has been performed. |
| `--three-prime-clip-r2` | string |  |  |  |  |  | Instructs Trim Galore to remove bp from the 3' end of read 2 AFTER adapter/quality trimming has been performed. |
| `--trim-reads` | string |  |  |  |  |  | Instructs Trim Galore to apply the --nextseq=X option, to trim based on quality after removing poly-G tails. |

<!-- Generated from nf-core/magmap@7cd374473c4118859b655e627ced6a80c0cf5c60. Do not edit by hand. -->
