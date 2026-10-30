---
name: bacass
version: 2.6.1
commit: 5ed7c2dd9a05d2434d8ba39ace1116368a4ba570
---

# bacass — full parameter reference

nf-core/bacass pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## annotation

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--annotation-tool` | string |  |  | `prokka`, `bakta`, `dfast`, `liftoff` |  | `prokka` | The annotation method to annotate the final assembly. |
| `--baktadb` | string |  |  |  |  |  | Path to Bakta database |
| `--baktadb-download` | boolean |  |  |  |  |  | Download Bakta database |
| `--baktadb-download-args` | string |  |  | `--type light`, `--type full` |  | `--type light` | This can be used to supply [extra options](https://github.com/oschwengers/bakta#database-download) to the Bakta download module |
| `--dfast-config` | string |  |  |  |  | `assets/test_config_dfast.py` | Specifies a configuration file for the [DFAST](https://github.com/nigyta/dfast_core) annotation method. |
| `--liftoff-ref-from-kmerfinder` | boolean |  |  |  |  |  | Use the reference files (.fasta, .gff) from kmerfinder step for LIFTOFF. |
| `--prokka-args` | string |  |  |  |  |  | Extra arguments for prokka annotation tool. |
| `--prokka-proteins` | string |  |  |  |  |  | FASTA file with protein sequences to be used as reference by PROKKA. |

## assembly_parameters

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--assembler` | string |  |  |  |  | `autocycler,canu,dragonflye,flye,megahit,miniasm,unicycler,raven` | The assembler(s) to use for assembly. |
| `--assembly-type` | string |  |  | `short`, `long`, `hybrid` |  |  | Which type of assembly to perform. |
| `--autocycler-assemblers` | string |  |  |  |  | `canu,flye,miniasm,raven` | What assemblers to use for autocycler |
| `--autocycler-cluster-args` | string |  |  |  |  |  | Arguments to autocycler cluster. |
| `--autocycler-subsample-count` | integer |  |  |  |  | `4` | Number of subsets to assemble. |
| `--autocycler-subsample-mindepth` | integer |  |  |  |  | `25` | Minimum depth for subsets to assemble. |
| `--canu-args` | string |  |  |  |  |  | This can be used to supply [extra options](https://canu.readthedocs.io/en/latest/quick-start.html) to the Canu assembler. Will be ignored when other assemblers are used. |
| `--canu-mode` | string |  |  | `-pacbio`, `-nanopore`, `-pacbio-hifi`, `null` |  |  | Allowed technologies for long read assembly with CANU. |
| `--dragonflye-args` | string |  |  |  |  |  | Extra arguments for [Dragonflye](https://github.com/rpetit3/dragonflye#usage) |
| `--flye-mode` | string |  |  | `--pacbio-raw`, `--pacbio-corr`, `--pacbio-hifi`, `--nano-raw`, `--nano-corr`, `--nano-hq` |  | `--nano-raw` | Allowed technologies for long read assembly with Flye. |
| `--megahit-args` | string |  |  |  |  |  | Extra arguments for [MEGAHIT](https://github.com/voutcn/megahit#usage) |
| `--unicycler-args` | string |  |  |  |  |  | Extra arguments for Unicycler |

## assembly_polishing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--polish-method` | string |  |  | `medaka`, `nanopolish`, `none` |  | `medaka` | Which assembly polishing method to use. |

## busco_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--busco-clean-intermediates` | boolean |  |  |  |  | `false` | Clean intermediate BUSCO files |
| `--busco-config-file` | string or null |  |  |  |  |  | Path to BUSCO config file |
| `--busco-db-path` | string or null |  |  |  |  |  | Path to BUSCO database |
| `--busco-lineage` | string |  |  |  |  | `bacteria_odb10` | BUSCO lineage to use, you can use other BUSCO lineages, these are available in: https://busco.ezlab.org/list_of_lineages.html |
| `--busco-mode` | string |  |  | `genome`, `proteins`, `transcriptome` |  | `genome` | BUSCO mode to use |

## contamination_screening

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--kmerfinderdb` | string |  |  |  |  |  | Path to the KmerFinder bacteria database (e.g. `/path_to/kmerfinder/`, `/path_to/kmerfinder/bacteria/` or `/path_to/kmerfinder/bacteria.tar.gz`). Only taxonomic group `bacteria` is supported. If a directory is provided, the pipeline auto-detects whether it already includes the `bacteria/` level. See installation guidelines: [https://bitbucket.org/genomicepidemiology/kmerfinder_db/src/master/](https://bitbucket.org/genomicepidemiology/kmerfinder_db/src/master/). Example: `--kmerfinderdb 'ftp://ftp.cbs.dtu.dk/public/CGE/databases/KmerFinder/version/latest/bacteria.tar.gz'` (FTP download is ~30GB and can be slow; prefer pre-downloading and passing a local `.tar.gz`). Older version: [https://zenodo.org/records/13447056/files/20190108_kmerfinder_stable_dirs.tar.gz](https://zenodo.org/records/13447056/files/20190108_kmerfinder_stable_dirs.tar.gz). |
| `--kraken2db` | string |  |  |  |  |  | Path to Kraken2 database. |
| `--reference-fasta` | string |  |  |  |  |  | Reference FASTA file. |
| `--reference-gff` | string |  |  |  |  |  | Reference GFF file. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary, only when pipeline fails. |
| `--help` | boolean or string |  |  |  |  |  | Display the help message. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--hook-url` | string |  | yes |  |  |  | Incoming hook URL for messaging service |
| `--max-multiqc-email-size` | string |  | yes |  | matches `^\d+(\.\d+)?\.?\s*(K\|M\|G\|T)?B$` | `25.MB` | File size limit when attaching MultiQC reports to summary emails. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--multiqc-config` | string (file path) |  | yes |  |  |  | Custom config file to supply to MultiQC. |
| `--multiqc-logo` | string |  | yes |  |  |  | Custom logo file to supply to MultiQC. File name must also be set in the MultiQC config file |
| `--multiqc-methods-description` | string |  |  |  |  |  | Custom MultiQC yaml file containing HTML including a methods description. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
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
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  |  |  | Path to tab-separated sample sheet |
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

## qc_and_trim

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--discard-trimmed-pass` | boolean |  |  |  |  | `false` | Specify true to not write any reads that pass trimming thresholds.This can be used to use fastp for the output report only. |
| `--fastp-args` | string |  |  |  |  |  | This can be used to pass arguments to [Fastp](https://github.com/OpenGene/fastp) |
| `--filtlong-args` | string |  |  |  |  |  | Arguments for running Filtlong |
| `--filtlong-minlen` | integer |  |  |  |  | `10` | Minimun length for Filtlong to work |
| `--long-reads-filtering` | string |  |  |  |  | `porechop` | Tool for ONT read filtering |
| `--rasusa` | boolean |  |  |  |  | `false` | Use Rasusa to downsample reads to a target coverage |
| `--rasusa-coverage` | integer |  |  |  |  | `100` | Target coverage for Rasusa read downsampling |
| `--save-trimmed` | boolean |  |  |  |  |  | save trimmed files |
| `--save-trimmed-fail` | boolean |  |  |  |  |  | save files that failed to pass trimming thresholds ending in `*.fail.fastq.gz` |
| `--skip-fastp` | boolean |  |  |  |  |  | Skip FastP |
| `--skip-fastqc` | boolean |  |  |  |  |  | Skip FastQC |
| `--skip-nanoplot` | boolean |  |  |  |  |  | Skip Nanoplot |
| `--skip-toulligqc` | boolean |  |  |  |  |  | Skip ToulligQC |

## skipping_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--skip-annotation` | boolean |  |  |  |  |  | Skip annotating the assembly with Prokka /DFAST. |
| `--skip-busco` | boolean |  |  |  |  |  | Skip BUSCO |
| `--skip-kmerfinder` | boolean |  |  |  |  |  | Skip contamination analysis with [Kmerfinder](https://bitbucket.org/genomicepidemiology/kmerfinder/src/master/) |
| `--skip-kraken2` | boolean |  |  |  |  |  | Skip running Kraken2 classifier on reads. |
| `--skip-multiqc` | boolean |  |  |  |  |  | Skip MultiQC |
| `--skip-polish` | boolean |  |  |  |  |  | Skip polishing the long-read assembly with fast5 input. Will not affect short/hybrid assemblies. |
| `--skip-pycoqc` | boolean |  |  |  |  |  | Skip running `PycoQC` on long read input. |

<!-- Generated from nf-core/bacass@5ed7c2dd9a05d2434d8ba39ace1116368a4ba570. Do not edit by hand. -->
