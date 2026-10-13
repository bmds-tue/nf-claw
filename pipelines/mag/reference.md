---
name: mag
version: 5.5.0
commit: 56abab5b023ce953c9c43fe21090d156ad0e18af
---

# mag — full parameter reference

nf-core/mag pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## ancient_dna_assembly

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--ancient-dna` | boolean |  |  |  |  |  | Turn on/off the ancient DNA subworkflow |
| `--bcftools-view-high-variant-quality` | integer |  |  |  |  | 30 | minimum genotype quality for considering a variant high quality |
| `--bcftools-view-medium-variant-quality` | integer |  |  |  |  | 20 | minimum genotype quality for considering a variant medium quality |
| `--bcftools-view-minimal-allelesupport` | integer |  |  |  |  | 3 | minimum number of bases supporting the alternative allele |
| `--freebayes-min-basequality` | integer |  |  |  |  | 20 | minimum base quality required for variant calling |
| `--freebayes-minallelefreq` | number |  |  |  |  | 0.33 | minimum minor allele frequency for considering variants |
| `--freebayes-ploidy` | integer |  |  |  |  | 1 | Ploidy for variant calling |
| `--pydamage-accuracy` | number |  |  |  |  | 0.5 | PyDamage accuracy threshold |
| `--skip-ancient-damagecorrection` | boolean |  |  |  |  |  | deactivate damage correction of ancient contigs using variant and consensus calling |

## assembly_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--ale-per-base-output` | boolean |  |  |  |  |  | Enable ALE per-base output. This output can be very large (tens of GB). |
| `--coassemble-group` | boolean |  |  |  |  |  | Co-assemble samples within one group, instead of assembling each sample separately. |
| `--megahit-options` | string |  |  |  |  |  | Additional custom options for MEGAHIT. |
| `--run-pypolca` | boolean |  |  |  |  |  | Run PyPOLCA polishing on long-read assemblies before binning. |
| `--skip-ale` | boolean |  |  |  |  |  | Skip ALE |
| `--skip-flye` | boolean |  |  |  |  |  | Skip Flye assembly. |
| `--skip-megahit` | boolean |  |  |  |  |  | Skip MEGAHIT assembly. |
| `--skip-metamdbg` | boolean |  |  |  |  |  | Skip MetaDBG assembly. |
| `--skip-quast` | boolean |  |  |  |  |  | Skip metaQUAST. |
| `--skip-spades` | boolean |  |  |  |  |  | Skip Illumina-only SPAdes assembly. |
| `--skip-spadeshybrid` | boolean |  |  |  |  |  | Skip SPAdes hybrid assembly. |
| `--spades-downstreaminput` | string |  |  | `scaffolds`, `contigs` |  | scaffolds | Specify whether to use contigs or scaffolds assembled by SPAdes |
| `--spades-options` | string |  |  |  |  |  | Additional custom options for SPAdes and SPAdesHybrid. Do not specify `--meta` as this will be added for you! |

## bin_quality_check_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--busco-clean` | boolean |  |  |  |  |  | Enable clean-up of temporary files created during BUSCO runs. |
| `--busco-db` | string (file or directory path) |  |  |  |  |  | Download URL, local tar.gz archive, or local uncompressed directory for an *_odb10 or *_odb12 BUSCO lineage dataset. |
| `--busco-db-lineage` | string |  |  |  | matches (.*_odb(10\|12))\|auto(_prok\|_euk)?$ | auto | Name of the BUSCO *_odb10 or *_odb12 lineage to check against. Additionally supports 'auto', 'auto_prok' and 'auto_euk' for automatic lineage selection mode. |
| `--checkm2-db` | string (file path) |  |  |  |  |  | Path to local file of an already downloaded and uncompressed CheckM2 database file (.dmnd file). |
| `--checkm2-db-version` | integer |  |  |  |  | 14897628 | CheckM2 database version number to download (Zenodo record ID, for reference check the canonical reference https://zenodo.org/records/5571251, and pick the Zenodo ID of the database version of your choice). |
| `--checkm-db` | string (directory path) |  |  |  |  |  | Path to local folder containing already downloaded and uncompressed CheckM database. |
| `--checkm-download-url` | string (file path) |  | yes |  |  | https://zenodo.org/records/7401545/files/checkm_data_2015_01_16.tar.gz | URL pointing to checkM database for auto download, if local path not supplied. |
| `--generate-bigmag-file` | boolean |  |  |  |  |  | Make a BIgMAG input file including GUNC results. |
| `--gunc-database-type` | string |  |  | `progenomes`, `gtdb`, `test_data` |  | progenomes | Specify which database to auto-download if not supplying own |
| `--gunc-db` | string (file path) |  |  |  |  |  | Specify a path to a pre-downloaded GUNC dmnd database file |
| `--gunc-save-db` | boolean |  |  |  |  |  | Save the used GUNC reference files downloaded when not using --gunc_db parameter. |
| `--postbinning-input` | string |  |  | `raw_bins_only`, `refined_bins_only`, `both` |  | raw_bins_only | Specify which binning output is sent for downstream annotation, taxonomic classification, bin quality control etc. |
| `--refine-bins-dastool` | boolean |  |  |  |  |  | Turn on bin refinement using DAS Tool. |
| `--refine-bins-dastool-savecontig2bin` | boolean |  |  |  |  |  | Specify to save contig to bin maps used for bin refinement |
| `--refine-bins-dastool-threshold` | number |  |  |  |  | 0.5 | Specify single-copy gene score threshold for bin refinement. |
| `--run-busco` | boolean |  |  |  |  | true | Enable running BUSCO during bin QC. |
| `--run-checkm` | boolean |  |  |  |  |  | Enable running CheckM during bin QC. |
| `--run-checkm2` | boolean |  |  |  |  |  | Enable running CheckM2 during bin QC. |
| `--run-gunc` | boolean |  |  |  |  |  | Turn on GUNC genome chimerism checks |
| `--save-busco-db` | boolean |  |  |  |  |  | Save the used BUSCO lineage datasets provided via `--busco_db`. |
| `--save-checkm2-data` | boolean |  |  |  |  |  | Save the used CheckM2 reference files downloaded when not using --checkm2_db parameter. |
| `--save-checkm-data` | boolean |  |  |  |  |  | Save the used CheckM reference files downloaded when not using --checkm_db parameter. |
| `--skip-binqc` | boolean |  |  |  |  |  | Disable bin QC with BUSCO, CheckM or CheckM2. |

## binning_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bin-concoct-chunksize` | integer |  |  |  |  | 10000 | Specify length of sub-contigs cut up prior CONCOCT binning |
| `--bin-concoct-donotconcatlast` | boolean |  |  |  |  |  | Specify to not append the last contig less than sub-contig length to the last correct length contig |
| `--bin-concoct-overlap` | integer |  |  |  |  | 0 | Specify the overlap between each sub-contig prior CONCOCT binning |
| `--bin-domain-classification` | boolean |  |  |  |  |  | Enable domain-level (prokaryote or eukaryote) classification of bins using Tiara. Processes which are domain-specific will then only receive bins matching the domain requirement. |
| `--bin-domain-classification-tool` | string |  | yes |  |  | tiara | Specify which tool to use for domain classification of bins. Currently only 'tiara' is implemented. |
| `--bin-max-size` | integer |  |  |  |  |  | Specify the longest length a bin should be to retain for downstream processing (in base pairs). By default no limit. |
| `--bin-metabinner-scale` | string |  |  | `small`, `large`, `huge` |  | large | Dataset scale for MetaBinner |
| `--bin-min-size` | integer |  |  |  | ≥ 0 | 0 | Specify the shortest length a bin should be to retain for downstream processing (in base pairs) |
| `--bin-seqkit-stats-max-forks` | integer |  |  |  | ≥ 1 |  | Limit the number of concurrent SEQKIT_STATS jobs used for bin size calculation. |
| `--binning-map-mode` | string |  |  | `all`, `group`, `own` |  | group | Defines mapping strategy to compute co-abundances for binning, i.e. which samples will be mapped against the assembly. |
| `--bowtie2-mode` | string |  |  |  | matches ^[-\w]*$ |  | Specify alternative Bowtie2 settings for aligning reads back against the assembly. |
| `--exclude-unbins-from-postbinning` | boolean |  |  |  |  |  | Exclude unbinned contigs in the post-binning steps (bin QC, taxonomic classification, and annotation steps). |
| `--longread-percentidentity` | number |  |  |  |  |  | Specify a minimum percent identity filter for long reads mapping back to assembled contigs. |
| `--max-unbinned-contigs` | integer |  |  |  |  | 100 | Maximal number of contigs that are not part of any bin but treated as individual genome. |
| `--min-contig-size` | integer |  |  |  |  | 1500 | Minimum contig size to be considered for binning and for bin quality check. |
| `--min-length-unbinned-contigs` | integer |  |  |  |  | 1000000 | Minimal length of contigs that are not part of any bin but treated as individual genome. |
| `--save-assembly-mapped-reads` | boolean |  |  |  |  |  | Save the output of mapping raw reads back to assembled contigs |
| `--semibin-environment` | string |  |  | `human_gut`, `dog_gut`, `ocean`, `soil`, `cat_gut`, `human_oral`, `mouse_gut`, `pig_gut`, `built_environment`, `wastewater`, `chicken_caecum`, `global` |  | global | Pre-trained model for SemiBin2 for single sample assemblies |
| `--semibin-rng-seed` | integer |  |  |  |  | 1 | RNG seed for SemiBin2. |
| `--shortread-percentidentity` | number |  |  |  |  |  | Specify a minimum percent identity filter for short reads mapping back to assembled contigs. |
| `--skip-binning` | boolean |  |  |  |  |  | Skip metagenome binning entirely |
| `--skip-comebin` | boolean |  |  |  |  |  | Skip COMEBin Binning |
| `--skip-concoct` | boolean |  |  |  |  |  | Skip CONCOCT Binning |
| `--skip-maxbin2` | boolean |  |  |  |  |  | Skip MaxBin2 Binning |
| `--skip-metabat2` | boolean |  |  |  |  |  | Skip MetaBAT2 Binning |
| `--skip-metabinner` | boolean |  |  |  |  |  | Skip MetaBinner Binning |
| `--skip-semibin` | boolean |  |  |  |  |  | Skip SemiBin2 Binning |
| `--tiara-min-length` | integer |  |  |  |  | 3000 | Minimum contig length for Tiara to use for domain classification. For accurate classification, should be longer than 3000 bp. |

## gene_prediction_and_annotation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--metaeuk-db` | string (file or directory path) |  |  |  |  |  | Path to either a local fasta file of protein sequences, or to a directory containing an MMseqs2-formatted database, for annotation of eukaryotic genomes. |
| `--metaeuk-mmseqs-db` | string |  |  | `UniRef100`, `UniRef90`, `UniRef50`, `UniProtKB`, `UniProtKB/TrEMBL`, `UniProtKB/Swiss-Prot`, `NR`, `NT`, `GTDB`, `PDB`, `PDB70`, `Pfam-A.full`, `Pfam-A.seed`, `Pfam-B`, `CDD`, `eggNOG`, `VOGDB`, `dbCAN2`, `SILVA`, `Resfinder`, `Kalamari` |  |  | A string containing the name of one of the databases listed in the [mmseqs2 documentation](https://github.com/soedinglab/MMseqs2/wiki#downloading-databases). This database will be downloaded and formatted for eukaryotic genome annotation. Incompatible with --metaeuk_db. |
| `--prokka-compliance-centre` | string |  |  |  |  |  | Specify sequencing centre name required for Prokka's compliance mode. |
| `--prokka-fast-mode` | boolean |  |  |  |  |  | Specify to skip CDS/product searching in Prokka runs |
| `--prokka-with-compliance` | boolean |  |  |  |  |  | Turn on Prokka complicance mode for truncating contig names for NCBI/ENA compatibility. |
| `--save-mmseqs-db` | boolean |  |  |  |  |  | Save the downloaded mmseqs2 database specified in `--metaeuk_mmseqs_db`. |
| `--skip-metaeuk` | boolean |  |  |  |  |  | [DEPRECATED] This parameter no longer has any effect and will be removed in a future release. MetaEuk only runs when `--metaeuk_db` or `--metaeuk_mmseqs_db` is supplied. |
| `--skip-prodigal` | boolean |  |  |  |  |  | Skip Prodigal gene prediction |
| `--skip-prokka` | boolean |  |  |  |  |  | Skip Prokka genome annotation. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string (file path) |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string (file path) |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string (directory path) |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--assembly-input` | string (file path) |  |  |  | matches ^\S+\.csv$ |  | Additional input CSV samplesheet containing information about pre-computed assemblies. When set, assembly is skipped and the supplied assemblies are used for downstream analysis. |
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | CSV samplesheet file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--single-end` | boolean |  |  |  |  |  | Specifies that the input is single-end reads. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string (directory path) |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## quality_control_for_long_reads_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--filtlong-filtering-by-shortreads` | boolean |  |  |  |  |  | Filter long reads against short reads when using filtlong. |
| `--keep-lambda` | boolean |  |  |  |  |  | Keep reads similar to the ONT internal standard Escherichia virus Lambda genome. |
| `--lambda-reference` | string (file path) |  |  |  |  |  | Genome reference used to remove ONT Lambda contaminant reads. |
| `--longread-adaptertrimming-tool` | string |  |  | `porechop`, `porechop_abi` |  | porechop_abi | Specify which long read adapter trimming tool to use. |
| `--longread-filtering-tool` | string |  |  | `chopper`, `filtlong`, `nanoq` |  | chopper | Specify which long read filtering tool to use. |
| `--longreads-keep-percent` | integer |  |  |  |  | 90 | Keep this percent of bases. Only used by filtlong. |
| `--longreads-length-weight` | integer |  |  |  |  | 10 | The higher the more important is read length when choosing the best reads. Only used by filtlong. |
| `--longreads-min-length` | integer |  |  |  |  | 1000 | Discard any read which is shorter than this value. |
| `--longreads-min-quality` | integer |  |  |  |  |  | Discard any read which has a mean quality score lower than this value. |
| `--save-filtered-longreads` | boolean |  |  |  |  |  | Specify to save the resulting length filtered long read FASTQ files to --outdir. |
| `--save-lambdaremoved-reads` | boolean |  |  |  |  |  | Specify to save input FASTQ files with lamba reads removed to --outdir. |
| `--save-porechop-reads` | boolean |  |  |  |  |  | Specify to save the resulting clipped FASTQ files to --outdir. |
| `--skip-adapter-trimming` | boolean |  |  |  |  |  | Skip removing adapter sequences from long reads. |
| `--skip-longread-filtering` | boolean |  |  |  |  |  | Skip filtering long reads. |
| `--skip-longread-qc` | boolean |  |  |  |  |  | Skip all default QC steps for long reads (adapter trimming, filtering, removal of lambda sequences). |

## quality_control_for_short_reads_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--adapterremoval-adapter1` | string |  |  |  | matches ^[ATGCRYKMSWBDHVN]*$ | AGATCGGAAGAGCACACGTCTGAACTCCAGTCACNNNNNNATCTCGTATGCCGTCTTCTGCTTG | Forward read adapter to be trimmed by AdapterRemoval. |
| `--adapterremoval-adapter2` | string |  |  |  | matches ^[ATGCRYKMSWBDHVN]*$ | AGATCGGAAGAGCGTCGTGTAGGGAAAGAGTGTAGATCTCGGTGGTCGCCGTATCATT | Reverse read adapter to be trimmed by AdapterRemoval for paired end data. |
| `--adapterremoval-minquality` | integer |  |  |  |  | 2 | The minimum base quality for low-quality base trimming by AdapterRemoval. |
| `--adapterremoval-trim-quality-stretch` | boolean |  |  |  |  |  | Turn on quality trimming by consecutive stretch of low quality bases, rather than by window. |
| `--bbnorm` | boolean |  |  |  |  |  | Run BBnorm to normalize sequence depth. |
| `--bbnorm-min` | integer |  |  |  |  | 5 | Set BBnorm minimum depth to this number. |
| `--bbnorm-target` | integer |  |  |  |  | 100 | Set BBnorm target maximum depth to this number. |
| `--clip-tool` | string |  |  | `fastp`, `adapterremoval`, `trimmomatic` |  | fastp | Specify which adapter clipping tool to use. |
| `--fastp-cut-mean-quality` | integer |  |  |  |  | 15 | The mean quality requirement used for per read sliding window cutting by fastp. |
| `--fastp-qualified-quality` | integer |  |  |  |  | 15 | Minimum phred quality value of a base to be qualified in fastp. |
| `--fastp-save-trimmed-fail` | boolean |  |  |  |  |  | Save reads that fail fastp filtering in a separate file. Not used downstream. |
| `--fastp-trim-polyg` | boolean |  |  |  |  |  | Turn on detecting and trimming of poly-G tails |
| `--host-fasta` | string (file path) |  |  |  |  |  | Fasta reference file for host contamination removal. |
| `--host-fasta-bowtie2index` | string (directory path) |  |  |  |  |  | Bowtie2 index directory corresponding to `--host_fasta` reference file for host contamination removal. |
| `--host-genome` | string |  |  |  |  |  | Name of iGenomes reference for host contamination removal. |
| `--host-removal-save-ids` | boolean |  |  |  |  |  | Save the read IDs of removed host reads. |
| `--host-removal-verysensitive` | boolean |  |  |  |  |  | Use the `--very-sensitive` instead of the`--sensitive`setting for Bowtie 2 to map reads against the host genome. |
| `--keep-phix` | boolean |  |  |  |  |  | Keep reads similar to the Illumina internal standard PhiX genome. |
| `--phix-reference` | string (file path) |  |  |  |  |  | Genome reference used to remove Illumina PhiX contaminant reads. |
| `--reads-minlength` | integer |  |  |  |  | 15 | The minimum length of reads must have to be retained for downstream analysis. |
| `--save-bbnorm-reads` | boolean |  |  |  |  |  | Save normalized read files to output directory. |
| `--save-clipped-reads` | boolean |  |  |  |  |  | Specify to save the resulting clipped FASTQ files to --outdir. |
| `--save-hostremoved-reads` | boolean |  |  |  |  |  | Specify to save input FASTQ files with host reads removed to --outdir. |
| `--save-phixremoved-reads` | boolean |  |  |  |  |  | Specify to save input FASTQ files with phiX reads removed to --outdir. |
| `--skip-clipping` | boolean |  |  |  |  |  | Skip read preprocessing using fastp or adapterremoval. |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip running FastQC on short reads both before and after QC. |
| `--skip-shortread-qc` | boolean |  |  |  |  |  | Skip all default QC steps for short reads (adapter trimming, phiX removal). |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--igenomes-base` | string |  | yes |  |  | s3://ngi-igenomes/igenomes/ | The base path to the igenomes reference files |
| `--igenomes-ignore` | boolean |  | yes |  |  |  | Do not load the iGenomes reference config. |

## reproducibility_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--megahit-fix-cpu-1` | boolean |  |  |  |  |  | Fix number of CPUs for MEGAHIT to 1. Not increased with retries. |
| `--metabat-rng-seed` | integer |  |  |  |  | 1 | RNG seed for MetaBAT2. |
| `--spades-fix-cpus` | integer |  |  |  |  | -1 | Fix number of CPUs used by SPAdes. Not increased with retries. |
| `--spadeshybrid-fix-cpus` | integer |  |  |  |  | -1 | Fix number of CPUs used by SPAdes hybrid. Not increased with retries. |

## taxonomic_profiling_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cat-allow-unofficial-lineages` | boolean |  |  |  |  |  | Allow unofficial lineages in CAT classification. |
| `--cat-classify-unbinned` | boolean |  |  |  |  |  | Classify unbinned contigs with CAT (contig mode). |
| `--cat-db` | string (file or directory path) |  |  |  |  |  | Database for taxonomic classification of metagenome assembled genomes. Can be either a zipped file or a directory containing the extracted output of such. |
| `--cat-db-generate` | boolean |  |  |  |  |  | Generate CAT database. |
| `--cat-no-suggestive-asterisks` | boolean |  |  |  |  |  | Specify to turn off CAT marking in output files most probable hits (when multiple) with an asterix. |
| `--gtdb-db` | string (file or directory path) |  |  |  |  | https://data.gtdb.aau.ecogenomic.org/releases/release232/232.0/auxillary_files/gtdbtk_package/full_package/gtdbtk_r232_data.tar.gz | Specify the location of a GTDBTK database. Can be either an uncompressed directory or a `.tar.gz` archive. If not specified will be downloaded for you when GTDBTK or binning QC is not skipped. |
| `--gtdbtk-max-contamination` | number |  |  |  | ≥ 0; ≤ 100 | 10.0 | Max. bin contamination (in %) allowed to apply GTDB-tk classification. |
| `--gtdbtk-min-af` | number |  |  |  | ≥ 0; ≤ 1 | 0.65 | Min. alignment fraction to consider closest genome. |
| `--gtdbtk-min-completeness` | number |  |  |  | ≥ 0.01; ≤ 100 | 50.0 | Min. bin completeness (in %) required to apply GTDB-tk classification. |
| `--gtdbtk-min-perc-aa` | number |  |  |  | ≥ 0; ≤ 100 | 10.0 | Min. fraction of AA (in %) in the MSA for bins to be kept. |
| `--gtdbtk-place-species` | boolean |  |  |  |  |  | Specify to disable fast classification of genomes by ANI using skani in GTDB-Tk. |
| `--gtdbtk-pplacer-cpus` | integer |  |  |  |  | 1 | Number of CPUs used for the by GTDB-Tk run tool pplacer. |
| `--gtdbtk-pplacer-useram` | boolean |  |  |  |  |  | Speed up pplacer step of GTDB-Tk by loading to memory. |
| `--gtdbtk-single-job` | boolean |  |  |  |  |  | Run GTDB-Tk classification for all bins in a single job, rather than one job per sample/assembler/binner group. |
| `--gtdbtk-skip-aniscreen` | boolean |  | yes |  |  |  | [DEPRECATED] Use `--gtdbtk_place_species` instead. Specify to disable fast classification of genomes by ANI using skani in GTDB-Tk. |
| `--gtdbtk-use-full-tree` | boolean |  |  |  |  |  | Specify to have GTDBTk to use the full bacterial tree rather than the split tree (requires more memory!) |
| `--save-cat-db` | boolean |  |  |  |  |  | Save the CAT database generated when specified by `--cat_db_generate`. |
| `--skip-gtdbtk` | boolean |  |  |  |  |  | Skip the running of GTDB, as well as the automatic download of the database |

## virus_identification_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--genomad-db` | string (file or directory path) |  |  |  |  |  | Database for virus classification with geNomad |
| `--genomad-min-score` | number |  |  |  |  | 0.7 | Minimum geNomad score for a sequence to be considered viral |
| `--genomad-splits` | integer |  |  |  |  | 1 | Number of groups that geNomad's MMSeqs2 databse should be split into (reduced memory requirements) |
| `--run-virus-identification` | boolean |  |  |  |  |  | Run virus identification. |

<!-- Generated from nf-core/mag@56abab5b023ce953c9c43fe21090d156ad0e18af. Do not edit by hand. -->
