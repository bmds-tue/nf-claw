---
name: taxprofiler
version: 2.0.1
commit: 70ecc15e49b4f1fcf79d876643b5d14b65c66178
---

# taxprofiler — full parameter reference

nf-core/taxprofiler pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

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

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--databases` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about databases and profiling parameters for each taxonomic profiler |
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples and libraries/runs. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--save-untarred-databases` | boolean |  |  |  |  |  | Specify to save decompressed user-supplied TAR archives of databases |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

## postprocessing_and_visualisation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--krona-taxonomy-directory` | string |  |  |  |  |  | Specify path to krona taxonomy directories (required for MALT krona plots) |
| `--run-krona` | boolean |  |  |  |  |  | Turn on generation of Krona plots for supported profilers |
| `--run-profile-standardisation` | boolean |  |  |  |  |  | Turn on standardisation of taxon tables across profilers |
| `--standardisation-motus-generatebiom` | boolean |  |  |  |  |  | Turn on generation of BIOM output (currently only applies to mOTUs) |
| `--standardisation-taxpasta-format` | string |  |  | `tsv`, `csv`, `arrow`, `parquet`, `biom` |  | `tsv` | The desired output format. |
| `--taxpasta-add-idlineage` | boolean |  |  |  |  |  | Add the taxon's entire ID lineage to the output. Requires --taxpasta_taxonomy_dir. |
| `--taxpasta-add-lineage` | boolean |  |  |  |  |  | Add the taxon's entire name lineage to the output. Requires --taxpasta_taxonomy_dir. |
| `--taxpasta-add-name` | boolean |  |  |  |  |  | Add the taxon name to the output. Requires --taxpasta_taxonomy_dir. |
| `--taxpasta-add-rank` | boolean |  |  |  |  |  | Add the taxon rank to the output. Requires --taxpasta_taxonomy_dir. |
| `--taxpasta-add-ranklineage` | boolean |  |  |  |  |  | Add the taxon's entire rank lineage to the output. Requires --taxpasta_taxonomy_dir. |
| `--taxpasta-ignore-errors` | boolean |  |  |  |  |  | Ignore individual profiles that cause errors. |
| `--taxpasta-taxonomy-dir` | string |  |  |  |  |  | The path to a directory containing taxdump files. |

## preprocessing_general_qc_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--preprocessing-qc-tool` | string |  |  | `fastqc`, `falco` |  | `fastqc` | Specify the tool used for quality control of raw sequencing reads |
| `--save-analysis-ready-fastqs` | boolean |  |  |  |  |  | Save only the final reads from all read processing steps (that are sent to classification/profiling) in results directory. |
| `--save-preprocessed-reads` | boolean |  |  |  |  |  | Save reads from samples that went through the adapter clipping, pair-merging, and length filtering steps for both short and long reads |
| `--skip-preprocessing-qc` | boolean |  |  |  |  |  | Specify to skip sequencing quality control of raw sequencing reads |

## preprocessing_host_removal_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--hostremoval-reference` | string (file path) |  |  |  |  |  | Specify path to single reference FASTA of host(s) genome(s) |
| `--longread-hostremoval-index` | string (file path) |  |  |  |  |  | Specify path to a pre-made Minimap2 index file (.mmi) of the host removal reference |
| `--perform-longread-hostremoval` | boolean |  |  |  |  |  | Turn on long-read host removal |
| `--perform-shortread-hostremoval` | boolean |  |  |  |  |  | Turn on short-read host removal |
| `--save-hostremoval-bam` | boolean |  |  |  |  |  | Saved mapped and unmapped reads in BAM format from host removal |
| `--save-hostremoval-index` | boolean |  |  |  |  |  | Save mapping index of input reference when not already supplied by user |
| `--save-hostremoval-unmapped` | boolean |  |  |  |  |  | Save reads from samples that went through the host-removal step |
| `--shortread-hostremoval-index` | string (directory path) |  |  |  |  |  | Specify path to the directory containing pre-made BowTie2 indexes of the host removal reference |

## preprocessing_long_read_qc_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--longread-adapterremoval-tool` | string |  |  | `porechop`, `porechop_abi` |  | `porechop_abi` | Specify which tool to use for adapter trimming. |
| `--longread-filter-tool` | string |  |  | `filtlong`, `nanoq` |  | `nanoq` | Specify which tool to use for long reads filtering |
| `--longread-qc-adapterlist` | string (file path) |  |  |  |  |  | Path to a custom adapter text file, if you want to manually specify a list of adapters to remove. |
| `--longread-qc-predictadapters` | boolean |  |  |  |  |  | This option allows inference of adapters directly from the reads instead of relying on a static database. |
| `--longread-qc-qualityfilter-keeppercent` | integer |  |  |  |  | `90` | Specify the percent of high-quality bases to be retained |
| `--longread-qc-qualityfilter-minlength` | integer |  |  |  |  | `1000` | Specify the minimum length of reads to be retained |
| `--longread-qc-qualityfilter-minquality` | integer |  |  |  |  | `7` | Nanoq only: specify the minimum average read quality filter (Q) |
| `--longread-qc-qualityfilter-targetbases` | integer |  |  |  |  | `500000000` | Filtlong only: specify the number of high-quality bases in the library to be retained |
| `--longread-qc-skipadaptertrim` | boolean |  |  |  |  |  | Skip long-read trimming |
| `--longread-qc-skipqualityfilter` | boolean |  |  |  |  |  | Skip long-read length and quality filtering |
| `--perform-longread-qc` | boolean |  |  |  |  |  | Turns on long read quality control steps (adapter clipping, length filtering etc.) |

## preprocessing_run_merging_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--perform-runmerging` | boolean |  |  |  |  |  | Turn on run merging |
| `--save-runmerged-reads` | boolean |  |  |  |  |  | Save reads from samples that went through the run-merging step |

## preprocessing_short_read_qc_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--perform-shortread-complexityfilter` | boolean |  |  |  |  |  | Turns on nucleotide sequence complexity filtering |
| `--perform-shortread-qc` | boolean |  |  |  |  |  | Turns on short read quality control steps (adapter clipping, complexity filtering etc.) |
| `--save-complexityfiltered-reads` | boolean |  |  |  |  |  | Save reads from samples that went through the complexity filtering step |
| `--shortread-complexityfilter-bbduk-mask` | boolean |  |  |  |  |  | Turn on masking rather than discarding of low complexity reads for BBduk |
| `--shortread-complexityfilter-bbduk-windowsize` | integer |  |  |  |  | `50` | Specify the window size for BBDuk complexity filtering |
| `--shortread-complexityfilter-entropy` | number |  |  |  |  | `0.3` | Specify the minimum sequence entropy level for complexity filtering |
| `--shortread-complexityfilter-fastp-threshold` | integer |  |  |  |  | `30` | Specify the minimum complexity filter threshold of fastp |
| `--shortread-complexityfilter-prinseqplusplus-dustscore` | number |  |  |  |  | `0.5` | Specify the minimum dust score for PRINTSEQ++ complexity filtering |
| `--shortread-complexityfilter-prinseqplusplus-mode` | string |  |  | `entropy`, `dust` |  | `entropy` | Specify the complexity filter mode for PRINSEQ++ |
| `--shortread-complexityfilter-tool` | string |  |  | `bbduk`, `prinseqplusplus`, `fastp` |  | `bbduk` | Specify which tool to use for complexity filtering |
| `--shortread-qc-adapter1` | string |  |  |  |  |  | Specify adapter 1 nucleotide sequence |
| `--shortread-qc-adapter2` | string |  |  |  |  |  | Specify adapter 2 nucleotide sequence |
| `--shortread-qc-adapterlist` | string |  |  |  |  |  | Specify a list of all possible adapters to trim. Overrides --shortread_qc_adapter1/2. Formats: .txt (AdapterRemoval) or .fasta. (fastp). |
| `--shortread-qc-dedup` | boolean |  |  |  |  |  | Perform deduplication of the input reads (fastp only) |
| `--shortread-qc-includeunmerged` | boolean |  |  |  |  |  | Include unmerged reads from paired-end merging in the downstream analysis |
| `--shortread-qc-mergepairs` | boolean |  |  |  |  |  | Turn on merging of read pairs for paired-end data |
| `--shortread-qc-minlength` | integer |  |  |  |  | `15` | Specify the minimum length of reads to be retained |
| `--shortread-qc-skipadaptertrim` | boolean |  |  |  |  |  | Skip adapter trimming |
| `--shortread-qc-tool` | string |  |  | `fastp`, `adapterremoval` |  | `fastp` | Specify which tool to use for short-read QC |

## profiling_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bracken-save-intermediatekraken2` | boolean |  |  |  |  |  | Turn on the saving of the intermediate Kraken2 files used as input to Bracken itself into Kraken2 results folder |
| `--centrifuge-save-reads` | boolean |  |  |  |  |  | Turn on saving of Centrifuge-aligned reads |
| `--diamond-output-format` | string |  |  | `blast`, `xml`, `txt`, `daa`, `sam`, `tsv`, `paf` |  | `tsv` | Specify output format from DIAMOND profiling. |
| `--diamond-save-reads` | boolean |  |  |  |  |  | Turn on saving of DIAMOND-aligned reads. Will override --diamond_output_format and no taxon tables will be generated |
| `--ganon-report-maxcount` | integer |  |  |  |  | `0` | Specify a maximum number of reads a hit must have to be retained in the ganon report. |
| `--ganon-report-mincount` | integer |  |  |  |  | `0` | Specify a minimum number of reads a hit must have to be retained in the ganon report. |
| `--ganon-report-rank` | string |  |  |  |  | `default` | Specify the taxonomic report the ganon report file should display. |
| `--ganon-report-toppercentile` | integer |  |  |  |  | `0` | Specify a percentile within which hits will be reported in ganon report output.. |
| `--ganon-report-type` | string |  |  | `abundance`, `reads`, `matches`, `dist`, `corr` |  | `reads` | Specify the type of ganon report to save. |
| `--ganon-save-readclassifications` | boolean |  |  |  |  |  | Turn on saving of ganon per-read taxonomic assignment file(s). |
| `--kaiju-expand-viruses` | boolean |  |  |  |  |  | Turn on expanding of virus hits to individual viruses rather than aggregating at a taxonomic level. |
| `--kaiju-taxon-rank` | string |  |  | `phylum`, `class`, `order`, `family`, `genus`, `species` |  | `species` | Specify taxonomic rank to be displayed in Kaiju taxon table |
| `--kmcp-save-search` | boolean |  |  |  |  |  | Turn on saving the output of KMCP search |
| `--kraken2-save-minimizers` | boolean |  |  |  |  |  | Turn on saving minimizer information in the kraken2 report thus increasing to an eight column layout. |
| `--kraken2-save-readclassifications` | boolean |  |  |  |  |  | Turn on saving of Kraken2 per-read taxonomic assignment file |
| `--kraken2-save-reads` | boolean |  |  |  |  |  | Turn on saving of Kraken2-aligned reads |
| `--krakenuniq-batch-size` | integer |  |  |  |  | `20` | Specify the number of samples for each KrakenUniq run. |
| `--krakenuniq-ram-chunk-size` | string |  |  |  |  |  | Specify a RAM chunk size for all KrakenUniq databases when loading into memory when you want to load via chunks. Specify in `--databases` for per-database values. |
| `--krakenuniq-save-readclassifications` | boolean |  |  |  |  |  | Turn on saving of KrakenUniq per-read taxonomic assignment file. |
| `--krakenuniq-save-reads` | boolean |  |  |  |  |  | Turn on saving of KrakenUniq (un-)classified reads as FASTA. |
| `--malt-generate-megansummary` | boolean |  |  |  |  |  | Turn on generation of MEGAN summary file from MALT results |
| `--malt-mode` | string |  |  | `Unknown`, `BlastN`, `BlastP`, `BlastX`, `Classifier` |  | `BlastN` | Specify which MALT alignment mode to use |
| `--malt-save-reads` | boolean |  |  |  |  |  | Turn on saving of MALT-aligned reads |
| `--melon-k2-db` | string |  |  |  |  |  | Specify kraken2 database for prefiltering of non-prokaryotic reads with melon. |
| `--metacache-abundances` | boolean |  |  |  |  |  | Print all mapping information in separate columns (rank, taxon name, taxon ids). |
| `--metaphlan-save-samfiles` | boolean |  |  |  |  |  | Turn on saving of MetaPhlAn reads aligned against marker genes in SAM format |
| `--motus-longprep-minlen` | integer |  |  |  |  | `50` | Minimum read length, shorter are discarded. |
| `--motus-longprep-splittinglength` | integer |  |  |  |  | `300` | Splitting length for the long reads. |
| `--motus-remove-ncbi-ids` | boolean |  |  |  |  |  | Turn on removing NCBI taxonomic IDs. |
| `--motus-save-mgc-read-counts` | boolean |  |  |  |  |  | Turn on saving the mgc reads count. |
| `--motus-save-split-longreads` | boolean |  |  |  |  |  | Turn on saving the output of synthetic long-reads |
| `--motus-use-relative-abundance` | boolean |  |  |  |  |  | Turn on printing relative abundance instead of counts. |
| `--run-bracken` | boolean |  |  |  |  |  | Turn on Bracken (and the required Kraken2 prerequisite step). |
| `--run-centrifuge` | boolean |  |  |  |  |  | Turn on profiling with Centrifuge. Requires database to be present CSV file passed to --databases |
| `--run-diamond` | boolean |  |  |  |  |  | Turn on profiling with DIAMOND. For unmerged paired-read libraries, only read1 will be used Requires database to be present CSV file passed to --databases |
| `--run-ganon` | boolean |  |  |  |  |  | Turn on profiling with ganon. Requires database to be present CSV file passed to --databases. |
| `--run-kaiju` | boolean |  |  |  |  |  | Turn on profiling with Kaiju. Requires database to be present CSV file passed to --databases |
| `--run-kmcp` | boolean |  |  |  |  |  | Turn on classification with KMCP. |
| `--run-kraken2` | boolean |  |  |  |  |  | Turn on profiling with Kraken2. Requires database to be present CSV file passed to --databases |
| `--run-krakenuniq` | boolean |  |  |  |  |  | Turn on profiling with KrakenUniq. Requires one or more KrakenUniq databases to be present in the CSV file passed to --databases. |
| `--run-malt` | boolean |  |  |  |  |  | Turn on profiling with MALT. Requires database to be present CSV file passed to --databases |
| `--run-melon` | boolean |  |  |  |  |  | Turn on profiling with Melon. Requires a database to be present in the CSV file passed to `--databases`. |
| `--run-metacache` | boolean |  |  |  |  |  | Turn on profiling with metacache. Requires database to be present CSV file passed to --databases |
| `--run-metaphlan` | boolean |  |  |  |  |  | Turn on profiling with MetaPhlAn. Requires database to be present CSV file passed to --databases |
| `--run-motus` | boolean |  |  |  |  |  | Turn on profiling with mOTUs. Requires database to be present CSV file passed to --databases |
| `--run-sylph` | boolean |  |  |  |  |  | Turn on profiling with sylph. Requires database to be present CSV file passed to --databases |
| `--sylph-data-type` | string |  |  | `relative_abundance`, `sequence_abundance`, `ANI` |  | `relative_abundance` | Specifies which abundance metric to use |
| `--sylph-taxonomy` | string |  |  |  |  |  | Specify path to sylph taxonomy to add taxonomic path to each hit. |

## redundancy_estimation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--perform-shortread-redundancyestimation` | boolean |  |  |  |  |  | Turn on short-read metagenome sequencing redundancy estimation with nonpareil. Warning: only use for shallow short-read sequencing datasets. |
| `--shortread-redundancyestimation-mode` | string |  |  | `kmer`, `alignment` |  | `kmer` | Specify mode for identifying redundant reads |

<!-- Generated from nf-core/taxprofiler@70ecc15e49b4f1fcf79d876643b5d14b65c66178. Do not edit by hand. -->
