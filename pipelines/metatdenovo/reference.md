---
name: metatdenovo
version: 2.0.0
commit: e9f8311e9a24278fdaed0f8717eb819532aef55e
---

# metatdenovo — full parameter reference

nf-core/metatdenovo pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## assembler_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--assembler` | string |  |  | `megahit`, `spades` |  |  | Specify the assembler to run. Possible alternatives: megahit, spades. |
| `--megahit-k-list` | string |  | yes |  |  |  | Comma-separated list of k-mer sizes for MEGAHIT, all must be odd, in the range 15-255, increment <=28. |
| `--megahit-k-max` | integer |  | yes |  |  |  | Maximum k-mer size for MEGAHIT, must be odd and <=255. |
| `--megahit-k-min` | integer |  | yes |  |  |  | Minimum k-mer size for MEGAHIT, must be odd and <=255. |
| `--megahit-k-step` | integer |  | yes |  |  |  | Increment of k-mer size of each iteration for MEGAHIT, must be even and <=28. |
| `--megahit-min-count` | integer |  | yes |  |  |  | Minimum multiplicity for filtering k-mers in MEGAHIT. |
| `--min-contig-length` | integer |  |  |  |  | 0 | Filter out contigs shorter than this. |
| `--save-formatspades` | boolean |  |  |  |  |  | Save the formatted spades fasta file |
| `--spades-flavor` | string |  |  | `rna`, `isolate`, `sc`, `meta`, `plasmid`, `metaplasmid`, `metaviral`, `rnaviral` |  | rna | Select which type of assembly you want to make. Default: rna |
| `--user-assembly` | string (file path) |  |  |  |  |  | Path to a fasta file with a finished assembly. Assembly will be skipped by the pipeline. |
| `--user-assembly-name` | string |  |  |  |  | user_assembly | Name to give to the user-provided assembly. |

## bbduk_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--save-bbduk-fastq` | boolean |  |  |  |  |  | Save the resulting fastq files from filtering |
| `--save-bbduk-removed-fastq` | boolean |  |  |  |  |  | Save the reads that were removed (matched the sequence_filter reference) during BBDuk filtering |
| `--sequence-filter` | string |  |  |  |  |  | Fasta file with sequences to filter away before running assembly etc.. |

## consolidation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annotate-only-consolidated` | boolean |  |  |  |  | true | Only annotate the consolidated cluster representatives, not every individual ORF source as well |
| `--cluster-coverage` | number |  |  |  | ≥ 0; ≤ 1 | 0.8 | Minimum fraction of both proteins that must be covered by the alignment |
| `--cluster-min-seq-id` | number |  |  |  | ≥ 0; ≤ 1 | 0.99 | Minimum sequence identity for two proteins to be considered the same gene |
| `--skip-protein-consolidation` | boolean |  |  |  |  |  | Skip cross-contig consolidation of ORFs whose proteins cluster together |

## digital_normalization_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bbnorm` | boolean |  |  |  |  |  | Perform normalization to reduce sequencing depth. |
| `--bbnorm-min` | integer |  |  |  |  | 5 | Reads with an apparent depth of under nx will be presumed to be errors and discarded |
| `--bbnorm-target` | integer |  |  |  |  | 100 | Reduce the number of reads for assembly average coverage of this number. |
| `--save-bbnorm-fastq` | boolean |  |  |  |  |  | Save the resulting fastq files from normalization |

## functional_annotation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--dbcan-dbpath` | string |  |  |  |  | dbcan | Specify the dbCAN database path. |
| `--eggnog-db-url` | string |  | yes |  |  | http://eggnog5.embl.de/download/emapperdb-5.0.2/eggnog.db.gz | URL to download the eggNOG annotation database from. |
| `--eggnog-dbpath` | string |  |  |  |  | eggnog | Specify EGGNOG database path |
| `--eggnog-dmnd-url` | string |  | yes |  |  | http://eggnog5.embl.de/download/emapperdb-5.0.2/eggnog_proteins.dmnd.gz | URL to download the eggNOG Diamond database from. |
| `--eggnog-taxa-url` | string |  | yes |  |  | http://eggnog5.embl.de/download/emapperdb-5.0.2/eggnog.taxa.tar.gz | URL to download the eggNOG taxonomy database from. |
| `--hmmdir` | string (directory path) |  |  |  | matches ^\S+ |  | Directory with hmm files which will be searched for among ORFs |
| `--hmmfiles` | string (file path) |  |  |  | matches \S+hmm(\.gz)? |  | Comma-separated list of hmm files which will be searched for among ORFs |
| `--hmmpattern` | string |  |  |  |  | *.hmm | Specify which pattern hmm files end with |
| `--kofam-dbpath` | string |  |  |  |  | ./kofam/ | Path to a directory with KOfam files. Will be created if it doesn't exist. |
| `--kofam-dir` | string |  | yes |  |  |  | Deprecated: use `--kofam_dbpath`. If set, its value is used instead of `--kofam_dbpath`. |
| `--kofam-ko-list-url` | string |  | yes |  |  | https://www.genome.jp/ftp/db/kofam/ko_list.gz | URL to download the KOfam ko_list file from. |
| `--kofam-profiles-url` | string |  | yes |  |  | https://www.genome.jp/ftp/db/kofam/profiles.tar.gz | URL to download the KOfam HMM profiles archive from. |
| `--skip-dbcan` | boolean |  |  |  |  |  | If enabled, skips dbCAN CAZyme annotation. |
| `--skip-eggnog` | boolean |  |  |  |  |  | Skip EGGNOG functional annotation |
| `--skip-kofamscan` | boolean |  |  |  |  |  | If enabled, skips the run of KofamScan. |

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
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
| `--outdir` | string (directory path) | yes |  |  |  |  | The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure. |
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
| `--bbmap-ambiguous` | string |  |  | `best`, `all`, `random`, `toss` |  | best | How BBMap should handle reads that align equally well to more than one site |
| `--bbmap-minid` | number |  |  |  |  | 0.9 | Minimum identity needed to assign read to a contig |
| `--save-bam` | boolean |  |  |  |  |  | Save the bam files from mapping |
| `--save-idxstats` | boolean |  |  |  |  |  | Save the per-contig read counts from `samtools idxstats` |
| `--save-samtools` | boolean |  |  |  |  | true | Save the output from samtools |

## orf_caller_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--metaeuk-batchsize` | integer or string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*((K\|M\|G\|T)?B)?$ | 104857600 | Size of individual files annotated by MetaEuk in one batch. |
| `--metaeuk-db` | string |  |  |  |  |  | Path to a pre-built reference protein database for MetaEuk, either a protein fasta file or a directory containing an mmseqs2-formatted database. Optional -- when unset, `--metaeuk_db_name` is downloaded and built automatically. |
| `--metaeuk-db-name` | string |  |  | `UniRef100`, `UniRef90`, `UniRef50`, `UniProtKB`, `UniProtKB/TrEMBL`, `UniProtKB/Swiss-Prot`, `NR`, `GTDB`, `PDB` |  | UniRef50 | Name of the amino-acid reference database to download and build for MetaEuk when `--metaeuk_db` isn't set. Restricted to the amino-acid databases `metaeuk databases -h` lists (its nucleotide/profile entries aren't valid MetaEuk homology references); see the table in usage.md for which of these we've actually confirmed downloadable. |
| `--metaeuk-dbpath` | string |  |  |  |  | ./metaeuk_db/ | Path to a directory to store the downloaded MetaEuk database in. Will be created if it doesn't exist. Ignored when `--metaeuk_db` is set. |
| `--orf-caller` | string |  |  |  | matches ^(prodigal\|prokka\|transdecoder\|metaeuk)(,(prodigal\|prokka\|transdecoder\|metaeuk))*$ |  | Comma-separated list of ORF callers to run. Possible alternatives: prodigal, prokka, transdecoder, metaeuk. At least one of this, `--user_orfs`, or `--user_orfs_gff`/`--user_orfs_faa` must be set; any combination may be set together. |
| `--prodigal-trainingfile` | string |  |  |  |  |  | Specify a training file for prodigal. By default prodigal will learn from the input sequences |
| `--prokka-batchsize` | integer or string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*((K\|M\|G\|T)?B)?$ | 10485760 | Size of individual files annotated by Prokka in one batch. |
| `--transdecoder-batchsize` | integer or string |  | yes |  | matches ^\d+(\.\d+)?\.?\s*((K\|M\|G\|T)?B)?$ | 104857600 | Size of individual files annotated by TransDecoder in one batch. |
| `--user-orfs` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|json\|yaml\|yml)$ |  | Path to comma-separated file listing user-provided ORF calls to add alongside (or instead of) `--orf_caller`. |
| `--user-orfs-faa` | string (file path) |  |  |  |  |  | Path to a protein fasta file for a single set of user-provided ORFs. Additive with `--orf_caller` and `--user_orfs`; requires `--user_orfs_gff` too. |
| `--user-orfs-gff` | string (file path) |  |  |  |  |  | Path to a gff file for a single set of user-provided ORFs. Additive with `--orf_caller` and `--user_orfs`; requires `--user_orfs_faa` too. |
| `--user-orfs-name` | string |  |  |  |  | user_orfs | Name to give the ORFs supplied via `--user_orfs_gff`/`--user_orfs_faa`. Cannot collide with an active `--orf_caller` value, a `--user_orfs` row name, or the pipeline's own reserved names. |

## quality_control_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip FastQC. |

## quantification_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--featurecounts-fraction` | boolean |  |  |  |  |  | Count multi-mapped reads fractionally in featureCounts instead of at full weight per site |
| `--trim-bam-header-above` | integer |  | yes |  | ≥ 0 | 1073741824 | Header size in bytes above which contigs without reads are removed from a BAM file before featureCounts |

## taxonomy_annotation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--diamond-dbs` | string (file path) |  |  |  | matches ^\S+\.(csv\|tsv\|json\|yaml\|yml)$ |  | Path to comma-separated file containing information about Diamond database files you want to use for taxonomy assignment. |
| `--diamond-top` | integer |  |  |  |  | 10 | Argument to Diamond's `--top` that controls the percentage of hits to include in the LCA. |
| `--eukulele-db` | string |  |  | `gtdb`, `phylodb`, `marmmetsp`, `mmetsp`, `eukprot` |  |  | EUKulele database. |
| `--eukulele-dbpath` | string |  |  |  |  | ./eukulele/ | EUKulele database folder. |
| `--eukulele-method` | string |  |  | `mets`, `mags` |  | mets | Specify which method to use for EUKulele. the alternatives are: mets (metatranscriptomics) or mags (Metagenome Assembled Genomes). default: mets |
| `--save-eukulele-alignments` | boolean |  |  |  |  |  | Also publish EUKulele's raw Diamond alignment file, on top of the taxonomy estimation and counts. |
| `--skip-eukulele` | boolean |  |  |  |  |  | If enabled, skips the run of EUKulele |

## trimming_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--clip-r1` | string |  |  |  |  |  | Instructs Trim Galore to remove bp from the 5' end of read 1 (or single-end reads). |
| `--clip-r2` | string |  |  |  |  |  | Instructs Trim Galore to remove bp from the 5' end of read 2 (paired-end reads only). |
| `--save-trimmed` | boolean |  |  |  |  |  | Save the trimmed FastQ files in the results directory. |
| `--skip-trimming` | boolean |  |  |  |  |  | Skip the adapter trimming step. |
| `--three-prime-clip-r1` | string |  |  |  |  |  | Instructs Trim Galore to remove bp from the 3' end of read 1 AFTER adapter/quality trimming has been performed. |
| `--three-prime-clip-r2` | string |  |  |  |  |  | Instructs Trim Galore to remove bp from the 3' end of read 2 AFTER adapter/quality trimming has been performed. |
| `--trim-nextseq` | string |  |  |  |  |  | Instructs Trim Galore to apply the --nextseq=X option, to trim based on quality after removing poly-G tails. |

<!-- Generated from nf-core/metatdenovo@e9f8311e9a24278fdaed0f8717eb819532aef55e. Do not edit by hand. -->
