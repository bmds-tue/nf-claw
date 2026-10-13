---
name: viralmetagenome
version: 1.2.0
commit: 74064a43f4b00c163c22bcfc9cf1d84a2a69e988
---

# viralmetagenome — full parameter reference

nf-core/viralmetagenome pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## assembly

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--arguments-bbnorm` | string |  |  |  |  |  | Extra arguments passed to BBNorm |
| `--arguments-megahit` | string |  | yes |  |  |  | Arguments for MEGAHIT tool |
| `--arguments-prinseq-contig` | string |  |  |  |  | -out_format 1 -lc_dust .20 | Arguments for Prinseq tool for contigs |
| `--arguments-quast` | string |  | yes |  |  | --min-contig 0 | Arguments for QUAST tool |
| `--arguments-spades` | string |  | yes |  |  | --rnaviral | Arguments for SPAdes tool |
| `--arguments-sspace-basic` | string |  | yes |  |  | -x 1 -o 15 -r 0.75 | Arguments for SSPACE Basic tool |
| `--arguments-trinity` | string |  | yes |  |  | --max_reads_per_graph 100000 | Arguments for Trinity tool |
| `--assemblers` | string |  |  |  | matches ^(trinity\|spades\|megahit)(?:,(trinity\|spades\|megahit)){0,2}$ | spades,megahit | The specified tools for de novo assembly, multiple options are possible |
| `--normalise-reads` | boolean |  |  |  |  |  | Digitally normalise reads with BBNorm before de novo assembly |
| `--read-distance` | integer |  |  |  | ≥ 1 | 350 | Specify the mean distance between the paired reads |
| `--read-distance-sd` | number |  |  |  | ≥ 0.01; ≤ 1 | 0.75 | Specify the deviation of the mean distance that is allowed. |
| `--read-orientation` | string |  | yes |  |  | FR | Specify the read orientation. |
| `--skip-assembly` | boolean |  |  |  |  |  | Skip de novo assembly of reads |
| `--skip-contig-prinseq` | boolean |  |  |  |  |  | Skip the filtering of low complexity contigs with prinseq |
| `--skip-sspace-basic` | boolean |  |  |  |  | true | Skip the contig extension with sspace_basic |
| `--spades-hmm` | string |  |  |  |  |  | File or directory with amino acid HMMs for Spades HMM-guided mode. |
| `--spades-mode` | string |  |  | `rnaviral`, `corona`, `metaviral`, `meta`, `metaplasmid`, `plasmid`, `isolate`, `rna`, `bio` |  | rnaviral | Specific SPAdes mode to run |
| `--spades-yml` | string |  | yes |  |  |  | Path to yml file containing read information. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--custom-table-headers` | string |  | yes |  |  |  | Custom yaml file containing the table column names selection and new names. |
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--global-prefix` | string |  | yes |  |  |  | Prefix for all output files and directories, including logs and intermediate files. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--max-multiqc-email-size` | string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$ | 25.MB | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--prefix` | string |  | yes |  |  |  | Prefix that will be used to generate a global prefix, date and runname will be added for all output files and directories. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--trace-report-suffix` | string |  | yes |  |  |  | Suffix to add to the trace report filename. Default is the date and time in the format yyyy-MM-dd_HH-mm-ss. |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## genome_qc

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annotation-db` | string |  |  |  |  | ftp://ftp.expasy.org/databases/viralzone/2020_4/virosaurus90_vertebrate-20200330.fas.gz | Database used for annotation of the consensus constructs |
| `--annotation-metadata` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|txt)(\.gz)?$ |  | Metadata table describing the sequences of the annotation database |
| `--arguments-blastn-qc` | string |  | yes |  |  | -max_target_seqs 5 | Arguments for BLASTN QC |
| `--arguments-checkv` | string |  | yes |  |  | --remove_tmp | Arguments for CheckV tool |
| `--arguments-mafft-iterations` | string |  | yes |  |  | --auto --adjustdirection | Arguments for MAFFT iterations |
| `--arguments-mafft-qc` | string |  | yes |  |  | --auto --adjustdirection | Arguments for MAFFT QC |
| `--arguments-mmseqs-search` | string |  | yes |  |  | --search-type 4 --rescore-mode 3 | Arguments for MMseqs2 search |
| `--arguments-prokka` | string |  | yes |  |  | --centre X --compliant --force --kingdom Viruses | Arguments for Prokka tool |
| `--arguments-quast-qc` | string |  |  |  |  |  | Arguments for QUAST quality control |
| `--checkv-db` | string (file or directory path) |  |  |  |  |  | Reference database used by checkv for consensus quality control |
| `--mmseqs-searchtype` | integer |  | yes |  |  | 4 | Specify the search algorithm to use for mmseqs. 0: auto 1: amino acid, 2: translated, 3: nucleotide, 4: translated nucleotide alignment |
| `--prokka-db` | string |  |  |  |  |  | Define a prokka `--protein` database for protein annotation |
| `--skip-alignment-qc` | boolean |  |  |  |  | true | Skip creating an alignment of each the collapsed clusters and each iterative step |
| `--skip-blast-qc` | boolean |  |  |  |  |  | Skip the blast search of contigs to the provided reference DB |
| `--skip-checkv` | boolean |  |  |  |  |  | Skip the use of checkv for quality check |
| `--skip-consensus-annotation` | boolean |  |  |  |  |  | Skip the annotation of the consensus constructs |
| `--skip-consensus-qc` | boolean |  |  |  |  |  | Skip the quality measurements on consensus genomes |
| `--skip-prokka` | boolean |  |  |  |  |  | Skip gene estimation & annotation with prokka |
| `--skip-quast` | boolean |  |  |  |  |  | Skip the use of QUAST for quality check |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--metadata` | string |  |  |  | matches ^\S+\.[tc]sv$ |  | Sample metadata that is included in the multiqc report |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
| `--transpose-overview-tables` | boolean |  |  |  |  |  | Transpose the samples overview table so samples become columns and result fields become rows. |

## institutional_config_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--config-profile-contact` | string |  | yes |  |  |  | Institutional config contact information. |
| `--config-profile-description` | string |  | yes |  |  |  | Institutional config description. |
| `--config-profile-name` | string |  | yes |  |  |  | Institutional config name. |
| `--config-profile-url` | string |  | yes |  |  |  | Institutional config URL link. |
| `--custom-config-base` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/configs/master | Base directory for Institutional configs. |
| `--custom-config-version` | string |  | yes |  |  | master | Git commit id for Institutional configs. |

## iterative_consensus_refinement

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--call-intermediate-variants` | boolean |  |  |  |  |  | Call variants during the iterations |
| `--intermediate-consensus-caller` | string |  |  |  |  | bcftools | Consensus tool used for calling new consensus during iterations |
| `--intermediate-mapper` | string |  |  | `bwamem2`, `bowtie2` |  | bwamem2 | Mapping tool used during iterations |
| `--intermediate-mapping-stats` | boolean |  |  |  |  | true | Calculate summary statistics during iterations |
| `--intermediate-variant-caller` | string |  |  | `ivar`, `bcftools` |  | ivar | Variant caller used during iterations |
| `--iterative-refinement-cycles` | integer |  |  |  |  | 2 | Number of iterations |
| `--skip-iterative-refinement` | boolean |  |  |  |  |  | Don't realign reads to consensus sequences and redefine the consensus through (multiple) iterations |

## metagenomic_diversity

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--arguments-bracken` | string |  | yes |  |  |  | Arguments for Bracken tool |
| `--arguments-kaiju` | string |  | yes |  |  | -v | Arguments for Kaiju tool |
| `--arguments-kaiju2krona` | string |  | yes |  |  | -v -u | Arguments for Kaiju2Krona tool |
| `--arguments-kaiju2table` | string |  | yes |  |  | -e -l species | Arguments for Kaiju2Table tool |
| `--arguments-kraken2` | string |  | yes |  |  | --report-minimizer-data | Arguments for Kraken2 tool |
| `--arguments-kreport2krona` | string |  |  |  |  |  | Arguments for Kreport2Krona tool |
| `--arguments-krona` | string |  | yes |  |  |  | Arguments for Krona tool |
| `--bracken-db` | string (file or directory path) |  |  |  |  | https://genome-idx.s3.amazonaws.com/kraken/k2_viral_20230314.tar.gz | Location of bracken database |
| `--kaiju-db` | string (file or directory path) |  |  |  |  | https://kaiju-idx.s3.eu-central-1.amazonaws.com/2023/kaiju_db_rvdb_2023-05-26.tgz | Location of Kaiju database |
| `--kaiju-taxon-rank` | string |  | yes | `superkingdom`, `phylum`, `class`, `order`, `family`, `genus`, `species` |  | species | Level of taxa rank that needs to be determined |
| `--kraken2-db` | string (file or directory path) |  |  |  |  | https://genome-idx.s3.amazonaws.com/kraken/k2_viral_20230314.tar.gz | Location of the Kraken2 database |
| `--kraken2-save-minimizers` | boolean |  |  |  |  |  | Save kraken2's used minimizers |
| `--kraken2-save-readclassification` | boolean |  |  |  |  |  | Save summary overview of read classifications in a txt file |
| `--kraken2-save-reads` | boolean |  |  |  |  |  | Save classified and unclassified reads as fastq files |
| `--read-classifiers` | string |  |  |  | matches ^(kaiju\|kraken2\|bracken)(?:,(kaiju\|kraken2\|bracken)){0,2}$ | kraken2,kaiju | Specify the taxonomic read classifiers, choices are 'kaiju,kraken2' |
| `--save-databases` | boolean |  |  |  |  |  | Save the used databases |
| `--skip-read-classification` | boolean |  |  |  |  |  | Skip determining the metagenomic diversity of the sample |

## polishing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--arguments-blast-filter` | string |  | yes |  |  | --escore 0.01 --bitscore 50 --percent-alignment 0.80 | Arguments for BLAST filter tool |
| `--arguments-blast-makeblastdb` | string |  | yes |  |  | -dbtype nucl | Arguments for BLAST makeblastdb tool |
| `--arguments-blastn` | string |  | yes |  |  | -max_target_seqs 5 | Arguments for BLASTN tool |
| `--arguments-cdhit` | string |  | yes |  |  | -c 0.85 -mask rRyYkKsSwWmMbBdDhHvVnN | Arguments for CD-HIT tool |
| `--arguments-extract-cluster` | string |  | yes |  |  | --perc_reads_contig 5 | Arguments for cluster extraction |
| `--arguments-extract-precluster` | string |  | yes |  |  | --keep-unclassified true --merge-strategy lca | Arguments for precluster extraction |
| `--arguments-kaiju-contig` | string |  | yes |  |  | -v | Arguments for Kaiju tool for contigs |
| `--arguments-kraken2-contig` | string |  | yes |  |  |  | Arguments for Kraken2 tool for contigs |
| `--arguments-mash-dist` | string |  | yes |  |  | -s 4000 -k 15 | Arguments for Mash distance tool |
| `--arguments-mash-screen` | string |  | yes |  |  |  | Arguments for Mash screen tool |
| `--arguments-mash-sketch` | string |  | yes |  |  | -i | Arguments for Mash sketch tool |
| `--arguments-minimap2-align` | string |  | yes |  |  |  | Arguments for Minimap2 alignment |
| `--arguments-minimap2-index` | string |  | yes |  |  |  | Arguments for Minimap2 index |
| `--arguments-mmseqs-cluster` | string |  | yes |  |  | --min-seq-id 0.85 -c 0.700 --cov-mode 2 --cluster-mode 0 | Arguments for MMseqs2 cluster tool |
| `--arguments-mmseqs-linclust` | string |  | yes |  |  | --min-seq-id 0.85 -c 0.700 --cov-mode 2 --cluster-mode 0 | Arguments for MMseqs2 linclust tool |
| `--arguments-network-cluster` | string |  | yes |  |  | --max distance 0.15 --out-representatives --algo single | Arguments for network clustering, done with clusty |
| `--arguments-select-reference` | string |  |  |  |  |  | Arguments for selecting reference |
| `--arguments-vrhyme` | string |  | yes |  |  | --mems 50 | Arguments for VRhyme tool |
| `--arguments-vsearch` | string |  | yes |  |  | --maxseqlength 10000000 --id 0.85 --strand both --iddef 0 --no_progress --qmask none | Arguments for VSEARCH tool |
| `--blacklist` | string |  |  |  |  |  | File containing identifiers to exclude from the scaffolding reference pool |
| `--cluster-method` | string |  |  | `cdhitest`, `vsearch`, `mmseqs-linclust`, `mmseqs-cluster`, `vrhyme`, `mash` |  | cdhitest | Cluster algorithm used for contigs |
| `--cluster-with-reference-pool` | boolean |  |  |  |  | true | Include BLAST-hit reference sequences in the contig clustering input |
| `--identity-threshold` | number |  |  |  |  | 0.85 | Identity threshold value used in clustering algorithms |
| `--keep-unclassified` | boolean |  |  |  |  | true | Keep the contigs that could not be classified with the taxonomic databases (`kaiju_db` & `kraken2_db`) |
| `--max-contig-size` | integer |  |  |  |  | 10000000 | Maximum allowed contig size |
| `--max-n-perc` | integer |  |  |  | ≥ 0; ≤ 100 | 50 | Define the maximum percentage of ambiguous bases in a contig |
| `--min-contig-size` | integer |  |  |  |  | 500 | Minimum allowed contig size |
| `--network-clustering` | string |  |  | `single`, `complete`, `uclust`, `set-cover`, `cd-hit`, `leiden` |  | single | (only with mash) Algorithm to partition the network. |
| `--perc-reads-contig` | integer |  |  |  | ≥ 0; ≤ 99 | 5 | Minimum cumulated sum of mapped read percentages of each member from a cluster group, set to 0 to disable |
| `--precluster-classifiers` | string |  |  |  | matches ^(kaiju\|kraken2)(,(kaiju\|kraken2))?$ | kraken2,kaiju | Specify the metagenomic classifiers to use for contig taxonomy classification: 'kraken2,kaiju' |
| `--reference-pool` | string |  |  |  | matches ^.*\.(fasta\|fa\|fas\|fna\|fn)(\.gz)?$ | https://rvdb.dbi.udel.edu/download/C-RVDBv31.0.fasta.gz | Set of fasta sequences used as potential references for the contigs |
| `--save-intermediate-polishing` | boolean |  |  |  |  |  | Save intermediate polishing files |
| `--skip-polishing` | boolean |  |  |  |  |  | Skip the refinement/polishing of contigs through reference based scaffolding and read mapping |
| `--skip-precluster` | boolean |  |  |  |  |  | Skip the preclustering of assemblies to facilitate downstream processing of assemblies |
| `--skip-singleton-filtering` | boolean |  | yes |  |  |  | Skip the filtering of contigs that did not cluster together with other contigs |

## preprocessing_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--adapter-fasta` | string |  |  |  |  |  | Fasta file of adapters |
| `--arguments-bbduk` | string |  | yes |  |  | entropy=0.3 entropywindow=50 entropymask=f | Arguments for BBDuk tool |
| `--arguments-fastp` | string |  | yes |  |  | --cut_front --cut_tail --trim_poly_x --cut_mean_quality 30 --qualified_quality_phred 30 --unqualified_percent_limit 10 --length_required 50 | Arguments for Fastp tool |
| `--arguments-fastqc` | string |  | yes |  |  | --quiet | Arguments for FastQC tool |
| `--arguments-humid` | string |  | yes |  |  | -a -m 1 | Arguments for Humid tool |
| `--arguments-kraken2-host` | string |  |  |  |  |  | Arguments for Kraken2 tool for host removal |
| `--arguments-prinseq-reads` | string |  | yes |  |  |  | Arguments for Prinseq tool for reads |
| `--arguments-trimmomatic` | string |  | yes |  |  | ILLUMINACLIP:null:2:30:10 | Arguments for Trimmomatic tool |
| `--arguments-umitools-extract` | string |  | yes |  |  | --umi-separator ":" | Arguments for UMI-tools extract |
| `--contaminants` | string |  |  |  |  |  | Reference files containing adapter and/or contaminant sequences for sequence kmer matching (used by bbduk) |
| `--decomplexifier` | string |  |  | `bbduk`, `prinseq` |  | prinseq | Specify the decomplexifier to use, bbduk or prinseq |
| `--host-k2-db` | string |  |  |  |  | s3://ngi-igenomes/test-data/viralrecon/kraken2_human.tar.gz | Kraken2 database used to remove host and contamination |
| `--merge-reads` | boolean |  |  |  |  |  | Specify if reads coming from the same group or original sample should be merged for the downstream analyses |
| `--min-trimmed-reads` | integer |  |  |  |  | 1 | Input files with fewer than these reads will be filtered out of the "reads" output channel |
| `--save-final-reads` | boolean |  |  |  |  | true | Save reads after the final preprocessing step |
| `--save-intermediate-reads` | boolean |  |  |  |  |  | Save reads after every preprocessing step |
| `--save-merged` | boolean |  |  |  |  |  | Specify true to save all merged reads to a file ending in `*.merged.fastq.gz` |
| `--save-trimmed-fail` | boolean |  |  |  |  |  | Specify true to save files that failed to pass trimming thresholds ending in `*.fail.fastq.gz` |
| `--skip-complexity-filtering` | boolean |  |  |  |  | true | Skip filtering of low complexity regions in reads |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip read quality statistics summary tool 'fastqc' |
| `--skip-host-fastqc` | boolean |  | yes |  |  |  | Skip the fastqc step after host & contaminants were removed |
| `--skip-hostremoval` | boolean |  |  |  |  |  | Skip the removal of host read sequences |
| `--skip-preprocessing` | boolean |  |  |  |  |  | Skip read preprocessing and use input reads for downstream analysis |
| `--skip-trimming` | boolean |  |  |  |  |  | Skip read trimming |
| `--skip-umi-extract` | boolean |  |  |  |  | true | With or without UMI extraction |
| `--trim-tool` | string |  |  | `fastp`, `trimmomatic` |  | fastp | The used trimming tool |
| `--umi-deduplicate` | string |  |  | `read`, `mapping`, `both` |  | read | Specify at what level UMI deduplication should occur. |
| `--umi-discard-read` | integer |  |  |  |  | 0 | Discard R1 / R2 if required 0, meaning not to discard |
| `--use-host-filtered-reads` | boolean |  |  |  |  |  | Prefer host-filtered reads for downstream mapping & polishing steps once host removal has completed successfully |
| `--with-umi` | boolean |  |  |  |  |  | With or without UMI detection |

## variant_analysis

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--allele-frequency` | number |  |  |  | ≥ 0.01; ≤ 1 | 0.75 | Minimum allele frequency threshold for calling consensus |
| `--arguments-bcftools-consensus` | string |  | yes |  |  |  | Arguments for BCFtools consensus |
| `--arguments-bcftools-mpileup1` | string |  | yes |  |  | --ignore-overlaps --count-orphans --max-depth 800000 --min-BQ 20 --annotate FORMAT/AD,FORMAT/ADF,FORMAT/ADR,FORMAT/DP,FORMAT/SP,INFO/AD,INFO/ADF,INFO/ADR | Arguments for BCFtools mpileup step 1 |
| `--arguments-bcftools-mpileup2` | string |  | yes |  |  | --ploidy 2 --keep-alts --keep-masked-ref --multiallelic-caller --variants-only | Arguments for BCFtools mpileup step 2 |
| `--arguments-bcftools-mpileup3` | string |  | yes |  |  | --include 'INFO/DP>=5' | Arguments for BCFtools mpileup step 3 |
| `--arguments-bcftools-norm` | string |  | yes |  |  | --do-not-normalize --output-type z --multiallelics -any --write-index=tbi | Arguments for BCFtools norm, `--write-index=tbi` is required for downstream steps |
| `--arguments-bcftools-stats` | string |  | yes |  |  |  | Arguments for BCFtools stats |
| `--arguments-bedtools-maskfasta` | string |  | yes |  |  |  | Arguments for Bedtools maskfasta |
| `--arguments-bedtools-merge` | string |  | yes |  |  |  | Arguments for Bedtools merge |
| `--arguments-bowtie2-align` | string |  | yes |  |  | --local --very-sensitive-local --seed 1 | Arguments for Bowtie2 alignment |
| `--arguments-bowtie2-build` | string |  | yes |  |  |  | Arguments for Bowtie2 build |
| `--arguments-bwamem2-index` | string |  | yes |  |  |  | Arguments for BWA-MEM2 index |
| `--arguments-custom-mpileup` | string |  | yes |  |  | --max-depth 800000 | Arguments for custom mpileup |
| `--arguments-ivar-consensus1` | string |  | yes |  |  | -t 0 -q 20 -m 5 -n N | Arguments for iVar consensus step 1 |
| `--arguments-ivar-consensus2` | string |  | yes |  |  | --count-orphans --max-depth 0 --min-BQ 20 --no-BAQ -aa | Arguments for iVar consensus step 2 |
| `--arguments-ivar-variants1` | string |  | yes |  |  | -q 20 -m 5 | Arguments for iVar variants step 1 |
| `--arguments-ivar-variants2` | string |  | yes |  |  | --ignore-overlaps --count-orphans --max-depth 0 --no-BAQ --min-BQ 0 | Arguments for iVar variants step 2 |
| `--arguments-make-bed-mask` | string |  | yes |  |  | -a --ignore-overlaps --count-orphans --max-depth 0 --no-BAQ --min-BQ 0 | Arguments for making BED mask |
| `--arguments-mosdepth` | string |  | yes |  |  |  | Arguments for Mosdepth tool |
| `--arguments-picard-collectmultiplemetrics` | string |  | yes |  |  | --ASSUME_SORTED true --VALIDATION_STRINGENCY LENIENT --TMP_DIR tmp | Arguments for Picard CollectMultipleMetrics |
| `--arguments-picard-markduplicates` | string |  | yes |  |  | --ASSUME_SORTED true --VALIDATION_STRINGENCY LENIENT --TMP_DIR tmp --REMOVE_DUPLICATES true | Arguments for Picard MarkDuplicates |
| `--arguments-samtools-flagstat` | string |  | yes |  |  |  | Arguments for Samtools flagstat command |
| `--arguments-samtools-idxstats` | string |  | yes |  |  |  | Arguments for Samtools idxstats command |
| `--arguments-samtools-stats` | string |  | yes |  |  |  | Arguments for Samtools stats command |
| `--arguments-snpeff` | string |  | yes |  |  |  | Arguments for SnpEff tool for variant annotation |
| `--arguments-snpsift-extractfields` | string |  |  |  |  | -s "," -e "." | Arguments for SnpSift ExtractFields tool |
| `--arguments-tabix` | string |  | yes |  |  | -p vcf -f | Arguments for Tabix tool |
| `--arguments-umitools-dedup` | string |  | yes |  |  | --umi-separator=':' --method cluster --unmapped-reads use | Arguments for UMI-tools deduplication |
| `--consensus-caller` | string |  |  | `ivar`, `bcftools` |  | ivar | Consensus tool used for calling new consensus in final iteration |
| `--deduplicate` | boolean |  |  |  |  | true | Deduplicate the reads |
| `--ivar-header` | string |  | yes |  |  |  |  |
| `--keep-unmapped` | boolean |  |  |  |  |  | Keep unmapped reads in the alignments used for contig coverage, polishing and consensus refinement |
| `--mapper` | string |  |  | `bwamem2`, `bowtie2` |  | bwamem2 | Define which mapping tool needs to be used when mapping reads to reference |
| `--mapping-constraints` | string |  |  |  |  |  | Sequence(s) to use as a reference for mapping instead of the de novo contigs or scaffolds |
| `--mapping-stats` | boolean |  |  |  |  | true | Calculate summary statistics in final iteration |
| `--min-consensus-depth` | integer |  |  |  | ≥ 1 | 5 | Define the minimum consensus depth |
| `--min-mapped-reads` | integer |  |  |  | ≥ 1 | 200 | Define the minimum number of mapped reads in order to continue the variant and consensus calling |
| `--skip-variant-calling` | boolean |  |  |  |  |  | Skip the analysis of variants for the external reference or contigs |
| `--skip-vcf-annotation` | boolean |  |  |  |  |  | Skip the annotation of the VCF file |
| `--variant-caller` | string |  |  | `ivar`, `bcftools` |  | ivar | Define the variant caller to use: 'ivar' or 'bcftools' |

<!-- Generated from nf-core/viralmetagenome@74064a43f4b00c163c22bcfc9cf1d84a2a69e988. Do not edit by hand. -->
