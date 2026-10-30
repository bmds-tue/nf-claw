---
name: viralrecon
version: 3.0.0
commit: 395079f1d24dce731ac22e03d7a5e71f110103fc
---

# viralrecon — full parameter reference

nf-core/viralrecon pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/test-datasets/viralrecon` | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | `copy` | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | `true` | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## illumina_de_novo_assembly_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--assemblers` | string |  |  |  |  | `spades` | Specify which assembly algorithms you would like to use. Available options are 'spades', 'unicycler' and 'minia'. |
| `--blast-db` | string (file or directory path) |  |  |  |  |  | Path to directory or tar.gz archive for pre-built BLAST database. |
| `--min-contig-length` | integer |  |  |  |  | `200` | Minimum contig length to filter from BLAST results. |
| `--min-perc-contig-aligned` | number |  |  |  |  | `0.7` | Minimum percentage of contig aligned to filter from BLAST results. |
| `--skip-abacas` | boolean |  |  |  |  |  | Skip ABACAS process for assembly contiguation. |
| `--skip-assembly` | boolean |  |  |  |  |  | Specify this parameter to skip all of the de novo assembly steps in the pipeline. |
| `--skip-assembly-quast` | boolean |  |  |  |  |  | Skip generation of QUAST aggregated report for assemblies. |
| `--skip-bandage` | boolean |  |  |  |  |  | Skip Bandage image creation for assembly visualisation. |
| `--skip-blast` | boolean |  |  |  |  |  | Skip blastn of assemblies relative to reference genome. |
| `--skip-noninternal-primers` | boolean |  |  |  |  |  | Set this parameter to false to add an X at the begining or end of the primer's fasta sequence to specify cutadapt that they are non-internal 5' or 3' adapters, respectively. |
| `--skip-plasmidid` | boolean |  |  |  |  | `true` | Skip assembly report generation by PlasmidID. |
| `--spades-hmm` | string (file path) |  |  |  |  |  | Path to profile HMMs specific for gene/organism to enhance SPAdes assembly. |
| `--spades-mode` | string |  |  | `rnaviral`, `corona`, `metaviral`, `meta`, `metaplasmid`, `plasmid`, `isolate`, `rna`, `bio` |  | `rnaviral` | Specify the SPAdes mode you would like to run (default: 'rnaviral'). |
| `--threeprime-adapters` | boolean |  |  |  |  |  | Set this parameter to true when the primer's for cutadapt are 3' adapters. Default value is false, as default primers are 5' adapters. |

## illumina_qc_read_trimming_and_filtering_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--kraken2-assembly-host-filter` | boolean |  |  |  |  | `true` | Remove host reads identified by Kraken2 before running aseembly steps in the pipeline. |
| `--kraken2-db` | string (file or directory path) |  |  |  |  | `s3://ngi-igenomes/test-data/viralrecon/kraken2_human.tar.gz` | Full path to Kraken2 database built from host genome. |
| `--kraken2-db-name` | string |  |  |  |  | `human` | Name for host genome as recognised by Kraken2 when using the 'kraken2 build' command. |
| `--kraken2-variants-host-filter` | boolean |  |  |  |  |  | Remove host reads identified by Kraken2 before running variant calling steps in the pipeline. |
| `--save-trimmed-fail` | boolean |  |  |  |  |  | Save the trimmed FastQ files in the results directory. |
| `--skip-cutadapt` | boolean |  |  |  |  |  | Skip the amplicon trimming step with Cutadapt when using --protocol amplicon. |
| `--skip-fastp` | boolean |  |  |  |  |  | Skip the initial read trimming step peformed by fastp. |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip FastQC. |
| `--skip-kraken2` | boolean |  |  |  |  |  | Skip Kraken2 process for removing host classified reads. |

## illumina_variant_calling_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--consensus-caller` | string |  |  | `ivar`, `bcftools` |  | `bcftools` | Specify which consensus calling algorithm you would like to use. Available options are 'bcftools' and 'ivar' (default: 'bcftools'). |
| `--filter-duplicates` | boolean |  |  |  |  |  | Filtered duplicates reads detected by Picard MarkDuplicates from alignments. |
| `--ivar-trim-noprimer` | boolean |  |  |  |  |  | This option unsets the '-e' parameter in 'ivar trim' to discard reads without primers. |
| `--ivar-trim-offset` | integer |  |  |  |  |  | This option sets the '-x' parameter in 'ivar trim' so that reads that occur at the specified offset positions relative to primer positions will also be trimmed. |
| `--min-mapped-reads` | integer |  |  |  |  | `1000` | Minimum number of mapped reads below which samples are removed from further processing. Some downstream steps in the pipeline will fail if this threshold is too low. |
| `--pango-database` | string (directory path) |  |  |  |  |  | Path to pangolin datadir. |
| `--save-mpileup` | boolean |  |  |  |  |  | Save mpileup files generated when calling variants with iVar variants or iVar consensus. |
| `--save-unaligned` | boolean |  |  |  |  |  | Save unaligned reads in FastQ format from Bowtie 2 to the results directory. |
| `--skip-consensus` | boolean |  |  |  |  |  | Skip genome consensus creation step and any downstream QC. |
| `--skip-consensus-plots` | boolean |  |  |  |  |  | Skip creation of consensus base density plots. |
| `--skip-ivar-trim` | boolean |  |  |  |  |  | Skip iVar primer trimming step. Not recommended for --protocol amplicon. |
| `--skip-markduplicates` | boolean |  |  |  |  | `true` | Skip picard MarkDuplicates step. |
| `--skip-picard-metrics` | boolean |  |  |  |  |  | Skip Picard CollectMultipleMetrics steps. |
| `--skip-snpeff` | boolean |  |  |  |  |  | Skip SnpEff and SnpSift annotation of variants. |
| `--skip-variants` | boolean |  |  |  |  |  | Specify this parameter to skip all of the variant calling and mapping steps in the pipeline. |
| `--variant-caller` | string |  |  | `ivar`, `bcftools` |  |  | Specify which variant calling algorithm you would like to use. Available options are 'ivar' (default for '--protocol amplicon') and 'bcftools' (default for '--protocol metagenomic'). |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) |  |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples you would like to analyse. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--platform` | string |  |  | `illumina`, `nanopore` |  |  | NGS platform used to sequence the samples. |
| `--protocol` | string |  |  | `metagenomic`, `amplicon` |  |  | Specifies the type of protocol used for sequencing. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string (directory path) |  | yes |  |  | `https://raw.githubusercontent.com/nf-core/configs/master` | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | `master` | Git commit id for Institutional configs. |

## nanopore_illumina_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--freyja-barcodes` | string (file or directory path) |  |  |  |  |  | Lineage defining barcodes, default is most recent from UShER database. |
| `--freyja-db-name` | string |  |  |  |  | `freyja_db` | Specify the name where to store UShER database (default: 'freyja_db'). |
| `--freyja-depthcutoff` | integer |  |  |  | ≥ 0 | `0` | Specify a coverage depth minimum which excludes sites with coverage less than the specified value |
| `--freyja-lineages` | string (file or directory path) |  |  |  |  |  | Metadata of lineages that match barcode, default is most recent from UShER database. |
| `--freyja-repeats` | integer |  |  |  | ≥ 1 | `100` | Specify the number of bootstrap repeats to do. |
| `--max-multiqc-email-size` | string |  | yes |  |  | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--nextclade-dataset` | string |  |  |  |  |  | Full path to Nextclade dataset required for 'nextclade run' command. |
| `--nextclade-dataset-name` | string |  |  |  |  |  | Name of Nextclade dataset to retrieve. A list of available datasets can be obtained using the 'nextclade dataset list' command. |
| `--nextclade-dataset-tag` | string |  |  |  |  |  | Version tag of the dataset to download. A list of available datasets can be obtained using the 'nextclade dataset list' command. |
| `--skip-freyja` | boolean |  |  |  |  |  | Skip freyja deep SARS-CoV-2 variant analysis using a depth weighted approach. |
| `--skip-freyja-boot` | boolean |  |  |  |  |  | Skip the bootstrapping module of Freyja |
| `--skip-mosdepth` | boolean |  |  |  |  |  | Skip genome-wide and amplicon coverage plot generation from mosdepth output. |
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip MultiQC. |
| `--skip-nextclade` | boolean |  |  |  |  |  | Skip Nextclade clade assignment, mutation calling, and sequence quality checks for genome consensus sequence. |
| `--skip-pangolin` | boolean |  |  |  |  |  | Skip Pangolin lineage analysis for genome consensus sequence. |
| `--skip-variants-long-table` | boolean |  |  |  |  |  | Skip long table generation for reporting variants. |
| `--skip-variants-quast` | boolean |  |  |  |  |  | Skip generation of QUAST aggregated report for consensus sequences. |

## nanopore_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--artic-minion-model` | string |  |  |  |  |  | Clair3 model to use. If not provided the pipeline will attempt to determine the appropriate model based on the basecall_model_version_id field in the input FASTQ header (recommended) |
| `--artic-minion-model-dir` | string |  |  |  |  |  | Path containing clair3 models. Defaults to models packaged with conda installation |
| `--artic-scheme` | string |  |  |  |  |  | Primer scheme recognised by the artic minion command. |
| `--fastq-dir` | string (directory path) |  |  |  |  |  | Path to a folder containing fastq files from the Nanopore run. |
| `--min-barcode-reads` | integer |  |  |  |  | `100` | Minimum number of raw reads required per sample/barcode in order to be considered for the downstream processing steps. |
| `--min-guppyplex-reads` | integer |  |  |  |  | `10` | Minimum number of reads required after the artic guppyplex process per sample/barcode in order to be considered for the downstream processing steps. |
| `--sequencing-summary` | string (file path) |  |  |  | matches `^\S+\.txt$` |  | Sequencing summary file generated after Nanopore run completion. |
| `--skip-nanoplot` | boolean |  |  |  |  |  | Skip NanoPlot. |
| `--skip-pycoqc` | boolean |  |  |  |  |  | Skip pycoQC. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--additional-annotation` | string (file path) |  |  |  | matches `^\S+(\.gff\|\.gtf)(\.gz)?$` |  | Full path to additional annotation file in GTF or GFF format. |
| `--bowtie2-index` | string (file or directory path) |  |  |  |  |  | Path to directory or tar.gz archive for pre-built Bowtie2 index. |
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to FASTA genome file. |
| `--genome` | string |  |  |  |  |  | Name of viral reference genome. |
| `--gff` | string (file path) |  |  |  | matches `^\S+\.gff(\.gz)?$` |  | Full path to GFF annotation file. |
| `--primer-bed` | string (file path) |  |  |  | matches `^\S+\.bed(\.gz)?$` |  | If the '--protocol amplicon' parameter is provided then iVar is used to trim primer sequences after read alignment and before variant calling. |
| `--primer-fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | If the '--protocol amplicon' parameter is provided then Cutadapt is used to trim primer sequences from FastQ files before de novo assembly. |
| `--primer-left-suffix` | string |  |  |  |  | `_LEFT` | Suffix used in name field of '--primer_bed' to indicate left primer position. |
| `--primer-right-suffix` | string |  |  |  |  | `_RIGHT` | Suffix used in name field of '--primer_bed' to indicate right primer position. |
| `--primer-set` | string |  |  |  |  |  | The primer set to be used for the data analysis. |
| `--primer-set-version` | number |  |  |  |  |  | Version of the primer set e.g. '--primer_set artic --primer_set_version 3'. |
| `--save-reference` | boolean |  |  |  |  |  | If generated by the pipeline save reference genome related files to the results folder. |

<!-- Generated from nf-core/viralrecon@395079f1d24dce731ac22e03d7a5e71f110103fc. Do not edit by hand. -->
