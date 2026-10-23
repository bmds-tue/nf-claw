---
name: genomeassembler
version: 2.0.1
commit: c608622876dc627020e6627a5ea8cffd0d2e3f3d
---

# genomeassembler — full parameter reference

nf-core/genomeassembler pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## annotations_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--lift-annotations` | boolean |  |  |  |  | false | Lift-over annotations (requires `ref_gff`). |

## assembly_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--assembler` | string |  |  | `flye`, `hifiasm`, `flye_hifiasm`, `hifiasm_hifiasm`, `flye_flye`, `hifiasm_flye` |  | hifiasm | Assembler to use. Valid choices depend on strategy; for single either `'flye'` or `'hifiasm'`, hybrid can be done with `'hifiasm'` and for scaffolded assembly provide the names of the assemblers separated with an underscore. The first assembler will be used for ONT reads, the second for HiFi reads see below: `asembler_ont` and `assembler_hifi`. |
| `--assembler-hifi` | string |  |  |  |  |  | `assembler_hifi` assembles HiFi reads. This option is mainly useful when building more complex samplesheets. |
| `--assembler-hifi-args` | string |  |  |  |  |  | Arguments to be passed to `assembler_hifi` (HiFi). |
| `--assembler-ont` | string |  |  |  |  |  | `assembler_ont` assembles ONT reads. This option is mainly useful when building more complex samplesheets. |
| `--assembler-ont-args` | string |  |  |  |  |  | Arguments to be passed to `assembler_ont` (ONT) |
| `--assembly-scaffolding-order` | string |  |  | `ont_on_hifi`, `hifi_on_ont` |  | ont_on_hifi | When `strategy` is 'scaffold', which assembly should be scaffolded onto which? |
| `--flye-args` | string |  |  |  |  |  | Additional args for `flye`. |
| `--flye-mode` | string |  |  | `--pacbio-raw`, `--pacbio-corr`, `--pacbio-hifi`, `--nano-raw`, `--nano-corr`, `--nano-hq` |  | --nano-hq | Flye assembly mode. |
| `--genome-size` | string |  |  |  |  |  | Expected genome size, optional. |
| `--hifiasm-args` | string |  |  |  |  |  | Extra arguments passed to `hifiasm` |
| `--strategy` | string |  |  |  |  | single | Assembly strategy to use. Valid choices are `'single'`, `'hybrid'` and `'scaffold'`. |

## generic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email-on-fail` | string |  | yes |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary, only when pipeline fails. |
| `--help-full` | boolean |  |  |  |  |  | Display the full detailed help message. |
| `--monochrome-logs` | boolean |  | yes |  |  |  | Do not use coloured log outputs. |
| `--pipelines-testdata-base-path` | string |  | yes |  |  | https://raw.githubusercontent.com/nf-core/test-datasets/refs/heads/genomeassembler/ | Base URL or local path to location of pipeline test dataset files |
| `--plaintext-email` | boolean |  | yes |  |  |  | Send plain-text email instead of HTML. |
| `--publish-dir-mode` | string |  | yes | `symlink`, `rellink`, `link`, `copy`, `copyNoFollow`, `move` |  | copy | Method used to save pipeline results to output directory. |
| `--show-hidden` | boolean |  |  |  |  |  | Display hidden parameters in the help message (only works when --help or --help_full are provided). |
| `--validate-params` | boolean |  | yes |  |  | true | Boolean whether to validate parameters against the schema at runtime |
| `--version` | boolean |  | yes |  |  |  | Display version and exit. |

## hic_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--hic-F` | string |  |  |  |  |  | Path to forward HiC short reads. |
| `--hic-R` | string |  |  |  |  |  | Path to reverse HiC short reads. |
| `--hic-trim` | boolean |  |  |  |  | false | Trim HiC short reads. |

## input_output_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--email` | string |  |  |  | matches ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$ |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches ^\S+\.csv$ |  | Path to comma-separated file containing information about the samples in the experiment. |
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

## long_read_preprocessing

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--hifi-adapters` | string |  |  |  |  |  | Adapters for HiFi read-trimming. |
| `--hifi-fastplong-args` | string |  |  |  |  |  | Additional args to be passed to fastplong for HiFi reads. |
| `--hifireads` | string |  |  |  |  |  | Path to HiFi reads. |
| `--jellyfish` | boolean |  |  |  |  |  | Run jellyfish and genomescope (recommended). |
| `--jellyfish-k` | integer |  |  |  |  | 21 | Value of k used during k-mer analysis with `jellyfish`. |
| `--jellyfish-size` | string |  |  |  |  | 200M | Initial hash size used by `jellyfish count`. |
| `--ont-adapters` | string |  |  |  |  |  | Adapters for ONT read-trimming. |
| `--ont-collect` | boolean |  |  |  |  |  | Collect ONT reads from several files. |
| `--ont-fastplong-args` | string |  |  |  |  |  | Additional args to be passed to fastplong for ONT reads. |
| `--ontreads` | string |  |  |  |  |  | Path to ONT reads. |

## polishing_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--medaka-model` | string |  |  |  |  |  | Model to use with `medaka`. |
| `--polish` | string |  |  | `pilon`, `dorado`, `medaka`, `dorado+pilon`, `medaka+pilon` |  |  | String describing the polishing strategy. Takes priority over boolean selectors. If missing will be created from boolean selectors. |
| `--polish-dorado` | boolean |  |  |  |  |  | Polish assembly with `dorado` (ONT only). |
| `--polish-medaka` | boolean |  |  |  |  |  | Polish assembly with `medaka` (ONT only). |
| `--polish-pilon` | boolean |  |  |  |  |  | Polish assembly with `pilon`. Requires short reads. |

## qc_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--assembly` | string |  |  |  |  |  | Can be used to provide existing assembly will skip assembly and perform downstream steps including QC. |
| `--assembly-map-bam` | string |  |  |  |  |  | A mapping (bam) of reads mapped to the provided assembly can be specified for QC. If provided, alignment to the provided assembly fasta will not run, |
| `--busco` | boolean |  |  |  |  |  | Run `BUSCO`. |
| `--busco-db` | string (directory path) |  |  |  |  |  | Path to `BUSCO` data-base (optional). |
| `--busco-lineage` | string |  |  |  |  | auto_euk | `BUSCO` lineage to use. |
| `--csi-index-size` | integer |  |  |  |  | 14 | Index size to use for csi index (default: 14), creating and index of size 2^csi_index_size. See [samtools index documentation](https://www.htslib.org/doc/samtools-index.html) for details. |
| `--merqury` | boolean |  |  |  |  | false | Run `merqury` if short reads are provided. |
| `--qc-reads` | string |  |  | `ont`, `hifi` |  | ont | Long reads that should be used for QC when both ONT and HiFi reads are provided. Options are `'ont'` or `'hifi'`. |
| `--quast` | boolean |  |  |  |  |  | Run `QUAST`. |
| `--ref-map-bam` | string |  |  |  |  |  | A mapping (bam) of reads mapped to the reference can be provided for QC. If provided, alignment to reference fasta will not run. |

## reference_parameters

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--ref-fasta` | string |  |  |  |  |  | Path to reference genome seqeunce (fasta) |
| `--ref-gff` | string |  |  |  |  |  | Path to reference genome annotations (gff) |
| `--use-ref` | boolean |  | yes |  |  |  | Use reference genome. |

## scaffolding_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--hic-aligner` | string |  |  | `bwa-mem2`, `minimap2` |  | bwa-mem2 | Aligner to use for HiC reads; default: `'bwa-mem2'`. |
| `--scaffold-hic` | boolean |  |  |  |  |  | Scaffold using HiC reads using `yahs` (requires reads). |
| `--scaffold-links` | boolean |  |  |  |  |  | Scaffolding with `links`. |
| `--scaffold-longstitch` | boolean |  |  |  |  |  | Scaffold with `longstitch`. |
| `--scaffold-ragtag` | boolean |  |  |  |  |  | Scaffold with `ragtag` (requires reference). |

## short_read_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--meryl-k` | integer |  |  |  | ≥ 1 | 21 | kmer length for `meryl` / `merqury`. |
| `--paired` | boolean |  |  |  |  | false | Are shortreads paired. |
| `--shortread-F` | string |  |  |  |  |  | Path to forward short reads. |
| `--shortread-R` | string |  |  |  |  |  | Path to reverse short reads. |
| `--shortread-trim` | boolean |  |  |  |  |  | Trim short reads. |
| `--use-short-reads` | boolean |  |  |  |  |  | Use short reads. |

<!-- Generated from nf-core/genomeassembler@c608622876dc627020e6627a5ea8cffd0d2e3f3d. Do not edit by hand. -->
