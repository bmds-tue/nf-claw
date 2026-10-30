---
name: genomeqc
version: 1.0.1
commit: bce44e5b558e21b38d4dd2b6521302246b4dae6d
---

# genomeqc — full parameter reference

nf-core/genomeqc pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## annotation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--val-tool` | string |  |  | `agat`, `gffread` |  | `agat` | Tool for gxf validation. |

## busco_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--busco-clean` | boolean |  |  |  |  |  | Remove intermediate files |
| `--busco-config` | string |  |  |  |  |  | A path to a BUSCO config file (optional) |
| `--busco-lineage` | string |  |  |  |  | `hymenoptera_odb10` | A flag to set the busco lineage. |
| `--busco-lineages-path` | string |  |  |  |  |  | A flag to set the BUSCO lineages directory (optional) |
| `--groups` | string |  |  |  | matches `^(all\|archaea\|bacteria\|fungi\|invertebrate\|metagenomes\|plant\|protozoa\|vertebrate_mammalian\|vertebrate_other\|viral)(,(all\|archaea\|bacteria\|fungi\|invertebrate\|metagenomes\|plant\|protozoa\|vertebrate_mammalian\|vertebrate_other\|viral))*$` | `all` | A string with NCBI taxonomic groups of the assemblies. Can be a comma-separated list. |
| `--min-buscos` | integer |  |  |  |  |  | Minimum number of Complete BUSCOs a sequence must have to be counted as significant ortholog-containing sequences. |
| `--skip-busco` | boolean |  |  |  |  | `false` | Skip BUSCO. If run on genome only, it will also skip orthofinder. |

## decontamination_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--gxdb` | string |  |  |  |  |  | Path to FCS-GX contamination screening database. |
| `--gxdb-manifest` | string |  |  |  |  |  | Path to FCS GX contamination screening database |
| `--ramdisk` | string (directory path) |  |  |  |  |  | Path to RAM-backed tmpfs or ramfs location to store FCS-GX database |
| `--save-cleaned-adaptor` | boolean |  |  |  |  |  | Save cleaned genome after adaptor removal with FCS-GX |
| `--save-cleaned-genome` | boolean |  |  |  |  |  | Save cleaned genome after decontamination with FCS-GX |

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
| `--email` | string |  |  |  | matches `^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$` |  | Email address for completion summary. |
| `--input` | string (file path) | yes |  |  | matches `^\S+\.csv$` |  | Path to comma-separated file containing information about the samples in the experiment. |
| `--multiqc-title` | string |  |  |  |  |  | MultiQC report title. Printed as page header, used for filename if not otherwise specified. |
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

## orthology_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--ortho-version` | string |  |  | `v2`, `v3` |  | `v3` | OrthoFinder major version to run. |
| `--save-longest-isoform` | boolean |  |  |  |  |  | Publish longest protein isoform fasta files. |
| `--save-orthofinder-results` | boolean |  |  |  |  | `true` | Publish orthofinder results. |

## pipeline_mode_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--container-engine` | string |  |  | `docker`, `podman` |  | `docker` | Container engine used to launch the interactive Shiny app. Only 'docker' and 'podman' are supported - Singularity/Apptainer does not work. |
| `--genome-only` | boolean |  | yes |  |  |  | Run genomeqc on genomes only. |
| `--kvalue` | integer |  |  |  |  | `21` | k-mer size for meryl (merqury). |

## save_intermediate_files_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--save-assembly` | boolean |  |  |  |  |  | Publish genomes and/or annotations of user-supplied RefSeq IDs. |
| `--save-extracted-seqs` | boolean |  |  |  |  |  | Publish extracted protein fasta files by GFFREAD. |
| `--save-filtered-seqs` | boolean |  |  |  |  |  | Publish filtered fasta genome files from seqkit. |
| `--save-sorted-seqs` | boolean |  |  |  |  |  | Publish sorted fasta genome files from seqkit. |
| `--save-validated-annotation` | boolean |  |  |  |  |  | Publish gff files validated by AGAT. |

## te_annotation_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--RM-db` | array |  |  |  |  |  | List of URLs to DFAM h5 partition files to download. |
| `--RM-download-db` | boolean |  |  |  |  | `false` | Download h5 partition files from the URLs specified in RM_db. |
| `--curated-lib` | string (file path) |  |  |  |  |  | Path to a curated repeat library for HiTE. |
| `--famdb-library` | string (file path glob) |  |  |  |  |  | Path to pre-staged famdb h5 partition file(s). Accepts a single file path or a glob pattern (e.g. '/path/FamDB*'). Alternative to downloading via RM_db. |
| `--famdb-lineage` | string |  |  |  |  |  | Taxonomic lineage to filter repeat families from famdb (e.g. 'hymenoptera'). Omit to export all families. |
| `--is-plant` | boolean |  |  |  |  |  | Set to true for plant genomes (passed to HiTE). |
| `--repeatmasker-speed` | string |  |  | `default`, `q`, `qq` |  | `qq` | RepeatMasker sensitivity/speed mode. 'default' is most sensitive; 'q' (quick) is ~5x faster; 'qq' (rush) is fastest with lowest sensitivity. |
| `--run-repeatmodeler` | boolean |  |  |  |  |  | Run de novo repeat discovery with RepeatModeler before masking. Disabled by default — RepeatModeler typically requires 24 CPUs and 24–48 h per genome. When false, only the curated famdb library is used. |
| `--te` | string |  |  | `hite`, `repeatmasker` |  |  | TE annotation method to run. Use 'hite' for HiTE or 'repeatmasker' for the full RepeatMasker pipeline. Omit to skip TE annotation. 'hite' does not support -profile conda/mamba - use `-profile docker`, `-profile singularity`, or `-profile podman` instead. |
| `--te-cluster-coverage` | number |  |  |  | ≥ 0; ≤ 1 | `0.8` | Minimum alignment coverage threshold (0.0–1.0) for repeat library clustering. Passed as -aS to CD-HIT-EST and -c (with --cov-mode 1) to MMseqs2. |
| `--te-cluster-identity` | number |  |  |  | ≥ 0; ≤ 1 | `0.8` | Minimum sequence identity threshold (0.0–1.0) for repeat library clustering. Passed as -c to CD-HIT-EST and --min-seq-id to MMseqs2. |
| `--te-clusterer` | string |  |  | `mmseqs`, `linclust`, `cdhit` |  | `linclust` | Clustering tool used to dereplicate the repeat library before RepeatMasker. 'mmseqs' uses MMseqs2 easy-cluster; 'linclust' (default) uses MMseqs2 easy-linclust (linear time, less sensitive); 'cdhit' uses CD-HIT-EST. |

## tidk_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--repeat` | string |  |  |  |  |  | DNA string for tidk motif search |
| `--skip-tidk` | boolean |  |  |  |  | `false` | Do not run TIDK. |

## tree_summary_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--circular-rings` | string |  |  |  |  |  | Circular layout only: which summary stats to draw as rings. |
| `--quality-preset` | string |  |  | `generic`, `vertebrate`, `insect`, `plant`, `fungi`, `bacteria` |  |  | Circular layout only: phylogenetic-group thresholds used to score the quality (traffic-light) rings. |
| `--quality-thresholds` | string |  |  |  |  |  | Circular layout only: override individual --quality_preset cut-offs. |
| `--show-ring-values` | boolean |  |  |  |  | `false` | Circular layout only: print each value on its ring. |
| `--skip-plots-genome-anno` | string |  |  |  | matches `^(ch_plot\|nseqs_plot\|ortho_plot\|len_plot\|gene_plot\|n50_plot\|busco_gen_plot\|busco_prot_plot\|te_plot\|fcs_plot)(,(ch_plot\|nseqs_plot\|ortho_plot\|len_plot\|gene_plot\|n50_plot\|busco_gen_plot\|busco_prot_plot\|te_plot\|fcs_plot))*$` | `nseqs_plot` | Skip these stat plots in the genome and annotation tree plot. |
| `--skip-plots-genome-only` | string |  |  |  | matches `^(ch_plot\|nseqs_plot\|ortho_plot\|len_plot\|n50_plot\|busco_gen_plot\|te_plot\|fcs_plot)(,(ch_plot\|nseqs_plot\|ortho_plot\|len_plot\|n50_plot\|busco_gen_plot\|te_plot\|fcs_plot))*$` | `nseqs_plot` | Skip these stat plots in the genome only tree plot. |
| `--tree-margin` | string |  | yes |  |  |  | Tree's right margin size for the non-circular layouts. |
| `--tree-scale` | integer |  |  |  |  |  | Modifies scale of the tree plot in the tree summary, default value is '0.0005'. Useful if tree tips overlap with the concatenated plots. Very sensitive, increase/decrease by two-fold. |
| `--tree-style` | string |  |  | `roundrect`, `ellipse`, `rectangular`, `circular` |  | `roundrect` | Tree layout style for the tree summary plot. |

<!-- Generated from nf-core/genomeqc@bce44e5b558e21b38d4dd2b6521302246b4dae6d. Do not edit by hand. -->
