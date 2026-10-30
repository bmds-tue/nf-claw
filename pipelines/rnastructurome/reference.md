---
name: rnastructurome
version: 1.1.0
commit: 633ab1d0d12103f9002fe6e781ae1251df2d2656
---

# rnastructurome — full parameter reference

nf-core/rnastructurome pipeline parameters. Every parameter from the pinned `nextflow_schema.json`. Flags use nfclaw's hyphenated spelling; raw Nextflow requires the exact schema spelling (usually underscores). `hidden` marks parameters hidden from upstream's normal help output; `constraints` lists each parameter's declared value bounds (pattern, min/max, length) — conditional or composed rules (e.g. anyOf/oneOf) remain subject to the pinned pipeline's runtime validation.

## alignment_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--bowtie2-dovetail` | boolean |  |  |  |  | `true` | Allow dovetailing mates (`--dovetail`). |
| `--bowtie2-dpad` | integer |  |  |  | ≥ 0 | `15` | Bowtie2 `--dpad` padding around DP table. |
| `--bowtie2-ma` | integer |  |  |  |  | `2` | Bowtie2 `--ma` match bonus used with `--local`. |
| `--bowtie2-mp` | string |  |  |  | matches `^\d+,\d+$` | `6,2` | Bowtie2 `--mp` mismatch penalties as `max,min`. |
| `--bowtie2-preset` | string |  |  |  |  | `--very-sensitive-local` | Bowtie2 alignment preset. Default is equivalent to `--local -N 0 -D 20 -R 3 -L 20 -i S,1,0.50`. |
| `--bowtie2-rdg` | string |  |  |  | matches `^\d+,\d+$` | `5,3` | Bowtie2 `--rdg` read gap penalties as `open,extend`. |
| `--bowtie2-rfg` | string |  |  |  | matches `^\d+,\d+$` | `5,3` | Bowtie2 `--rfg` reference gap penalties as `open,extend`. |
| `--bowtie2-softclip` | boolean |  |  |  |  |  | Enable Bowtie2 local alignment mode (`--local`). |
| `--bowtie-all` | boolean or string |  |  |  |  | `true` | Report all valid alignments (`-a`). |
| `--bowtie-chunkmbs` | integer |  |  |  | ≥ 1 | `512` | Bowtie v1 `--chunkmbs` memory chunk size. |
| `--bowtie-index` | string |  |  |  |  |  | Optional path to a prebuilt Bowtie index (currently not consumed by workflow logic). |
| `--bowtie-k` | integer |  |  |  | ≥ 1 | `1` | Report up to this number of alignments per read (`-k`). |
| `--bowtie-max` | integer |  |  |  | ≥ 1 | `1` | Bowtie v1 `-m` maximum reportable alignments per read before suppression. |
| `--bowtie-n` | integer |  |  |  | ≥ 0; ≤ 3 | `2` | Bowtie v1 `-n` seed mismatch mode value. |
| `--bowtie-trim3` | integer |  |  |  | ≥ 0 | `0` | Trim this many bases from 3' read end (`--trim3`). |
| `--bowtie-trim5` | integer |  |  |  | ≥ 0 | `0` | Trim this many bases from 5' read end (`--trim5`). |
| `--bowtie-v` | integer |  |  |  | ≥ 0; ≤ 3 |  | Bowtie v1 `-v` mismatch mode value. |
| `--count-genome` | boolean |  |  |  |  | `false` | Genome route (STAR) quantification method. Default (false) uses STAR --quantMode TranscriptomeSAM projected onto transcripts, tag-corrected with samtools calmd, counted with rf-count. Set true for the legacy rf-count-genome + rf-rctools extract path. |
| `--markdup` | boolean |  |  |  |  |  | Run SAMtools markdup deduplication on non-UMI libraries. Off by default: position-based duplicate removal is not valid for chemical-probing libraries without UMIs, where reads sharing a 5' start are independent RT events rather than PCR duplicates. UMI libraries are always deduplicated via UMI-tools. |
| `--skip-markdup` | boolean |  | yes |  |  |  | Deprecated: use `--markdup` (inverted). |
| `--star-map-sjdb-overhang` | integer |  |  |  | ≥ 1 | `200` | STAR `--sjdbOverhang` for MaP alignment. Ideally `readLength - 1`; default 200 suits 201 bp reads. |
| `--star-multimap-nmax` | integer |  |  |  | ≥ 1 | `10` | Maximum number of loci a read is allowed to map to in STAR (`--outFilterMultimapNmax`). Reads mapping to more loci than this are discarded. Increase when studying repetitive non-coding RNAs. |
| `--transcriptome` | boolean |  |  |  |  | `false` | Align against a transcript-level FASTA using Bowtie (RT-stop) / Bowtie2 (MaP). Default (false) downloads a genome FASTA and aligns with STAR. |

## executor_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--slurm-account` | string |  |  |  |  |  | SLURM account / allocation passed via `--account`. |
| `--slurm-clusterOptions` | string |  |  |  |  |  | Extra sbatch flags appended verbatim to `process.clusterOptions`. |
| `--slurm-queue` | string |  |  |  |  |  | SLURM partition / queue name passed via `--partition`. |

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

## read_trimming_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--cutadapt-3quality` | integer |  |  |  |  | `20` | Base quality threshold for 3' trimming. |
| `--cutadapt-5quality` | integer |  |  |  |  | `20` | Base quality threshold for 5' trimming (used for MaP; RT-stop is forced to 0). |
| `--cutadapt-adapter-3p` | string |  |  |  |  | `AGATCGGAAGAGC` | Global fallback 3' adapter sequence(s), comma-separated. If omitted and no per-sample adapter is provided, the pipeline defaults to AGATCGGAAGAGC. |
| `--cutadapt-adapter-5p` | string |  |  |  |  | `AGATCGGAAGAGC` | Global fallback 5' adapter sequence(s), comma-separated. If omitted and no per-sample adapter is provided, the pipeline defaults to AGATCGGAAGAGC. |
| `--cutadapt-discard-untrimmed` | boolean |  |  |  |  | `false` | Discard reads in which no adapter was found. For short-insert libraries (e.g. tRNA, miRNA) where every genuine read runs into the adapter. |
| `--cutadapt-len` | integer |  |  |  |  | `25` | Minimum read length retained after trimming. |
| `--cutadapt-min-align` | integer |  |  |  |  | `3` | Minimum adapter overlap required for trimming. |
| `--cutadapt-nextseq-trim` | integer |  |  |  |  |  | Enable cutadapt `--nextseq-trim` with this 3' quality cutoff, trimming high-quality poly-G tails left by 2-colour (NextSeq/NovaSeq) chemistry. Off by default. |
| `--cutadapt-quality-only` | boolean |  |  |  |  | `false` | If true, skip adapter trimming and apply quality/length trimming only. |
| `--cutadapt-trim-n` | boolean |  |  |  |  | `true` | Trim terminal N bases. |

## reference_genome_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--ensembl-base-url` | string |  |  |  |  | `https://ftp.ensembl.org/pub` | Ensembl FTP base URL used when auto-resolving transcript FASTA. |
| `--ensembl-release` | string |  |  |  |  | `current` | Ensembl release for transcript FASTA auto-resolution (`current`, `latest`, or release number like `114`). |
| `--ensembl-species-map` | object |  | yes |  |  |  | Optional map from organism keys to Ensembl species names used for transcript FASTA auto-resolution. |
| `--fasta` | string (file path) |  |  |  | matches `^\S+\.fn?a(sta)?(\.gz)?$` |  | Path to transcript FASTA file. |
| `--genomes` | object |  | yes |  |  |  | Optional custom reference map keyed by organism/reference name. |
| `--gtf` | string (file path) |  |  |  | matches `^\S+\.gtf(\.gz)?$` |  | Path to transcript annotation GTF file. |
| `--ncbi-accessions-map` | object |  | yes |  |  |  | Internal map from normalized viral organism keys to NCBI accession lists. |

## rnaframework_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--correlate-ignore-sequence` | boolean |  |  |  |  | `false` | rf-correlate ignores sequence differences (e.g. SNVs) between compared transcripts (`-I`). |
| `--correlate-img` | boolean |  |  |  |  | `false` | Generate the rf-correlate correlation heatmap PDF (`-g`; requires R). |
| `--correlate-min-values` | number |  |  |  | ≥ 0 |  | rf-correlate minimum number of values to calculate a correlation (`-m`); a value between 0 and 1 is interpreted as a fraction of transcript length. Unset uses the tool default (off). |
| `--correlate-replicates` | boolean |  |  |  |  | `true` | Run rf-correlate to compute pairwise reactivity-profile correlations between replicates of each sample group (a replicate-reproducibility QC surfaced in MultiQC). Only runs for sample groups with more than one replicate; a no-op otherwise. |
| `--four-base-dms` | boolean |  |  |  |  | `true` | Four-base DMS analysis (Mitchell et al., 2023) for DMS-MaP samples at pH >= 8: rf-count keeps only G->C/G->T mutations on G and drops indels (`-om H2N,G2Y -ncl`), and rf-norm normalises each base separately over the whole transcript (`-4d`). |
| `--jackknife-reference` | string (file path) |  |  |  |  |  | Path to a reference `.db` structure file for rf-jackknife normalisation assessment. When provided, rf-jackknife runs between rf-norm and rf-fold and the output CSV reports optimal slope/intercept values. When omitted, rf-fold runs directly using whatever slope/intercept params are set. |
| `--r2dt` | boolean |  |  |  |  | `true` | Generate template-based 2D RNA structure diagrams using R2DT, coloured by normalised SHAPE/chemical-probing reactivity. |
| `--r2dt-templatable-biotypes` | string |  |  |  |  | `rRNA,Mt_rRNA,tRNA,Mt_tRNA,snoRNA,scaRNA,snRNA,SRP_RNA,RNase_P_RNA,RNase_MRP_RNA,tmRNA` | Comma-separated GTF biotypes sent to R2DT. R2DT only has templates for structured ncRNA classes; transcripts of other biotypes (mRNA, lncRNA, ...) are excluded so R2DT never force-fits them to the wrong template, and are drawn by ViennaRNA instead. Matched case-insensitively against transcript/gene biotype. |
| `--rfcorrelate-cap-react` | number |  |  |  | ≥ 0 | `1.5` | Cap reactivities to this value before Pearson correlation in rf-correlate (`--cap-react`). Not applied to the Spearman run, which is rank-based. |
| `--rfcount-discard-clipped-reads` | boolean |  |  |  |  | `false` | Discard reads with excessive 5' or 3' end clipping in rf-count / rf-count-genome (`--discard-clipped-reads`). |
| `--rfcount-genome-block-size` | integer |  |  |  | ≥ 1 | `100000` | Block size for per-chromosome memory allocation in rf-count-genome (`-bs`); increase for large genomes. |
| `--rfcount-genome-map-quality` | integer |  |  |  | ≥ 0 | `0` | Minimum MAPQ score for rf-count-genome (`--map-quality`). Useful for filtering multi-mappers; 0 keeps all alignments. |
| `--rfcount-genome-samtools-threads` | integer |  |  |  | ≥ 1 | `1` | SAMtools working threads per processor instance in rf-count-genome (`-wt`); total threads = `-p` × `-wt`. |
| `--rfcount-img` | boolean |  |  |  |  | `false` | Deprecated: rf-count plot generation (`-g`) is always enabled. |
| `--rfcount-map-collapse-consecutive` | boolean |  |  |  |  |  | In mutation mode (`-m`), collapse consecutive mutations/indels (`--collapse-consecutive`). Auto: on unless `RT_enzyme` is a Group II Intron RT (e.g. TGIRT); leave unset to use the auto default. |
| `--rfcount-map-discard-consecutive` | integer |  |  |  |  |  | MaP only: discard mutations within N nt of each other (`-dc N`). Auto: 3 when `RT_enzyme` is a Group II Intron RT (e.g. TGIRT), off for M-MLV; leave unset to use the auto default. |
| `--rfcount-map-discard-shorter` | integer |  |  |  | ≥ 1 | `1` | In mutation mode (`-m`), discard reads shorter than this value (`--discard-shorter`). |
| `--rfcount-map-eval-surrounding` | boolean |  |  |  |  | `true` | MaP only: also evaluate quality of ±1 nt surrounding each mutation (`-es`). |
| `--rfcount-map-max-collapse-distance` | integer |  |  |  | ≥ 0 | `2` | In mutation mode with collapsing enabled, max distance to collapse (`--max-collapse-distance`). |
| `--rfcount-map-max-coverage` | integer |  |  |  | ≥ 1000 |  | In mutation mode (`-m`), downsample each transcript above this coverage in rf-count (`--max-coverage`). Unset means off. Ignored with `--count_genome true`. |
| `--rfcount-map-median-quality` | integer |  |  |  | ≥ 0 | `20` | MaP only: discard reads with median Phred+33 base quality below this value (`-eq`). |
| `--rfcount-map-min-quality` | integer |  |  |  | ≥ 0 | `20` | In mutation mode (`-m`), minimum Phred+33 base quality for mutations (`--min-quality`). |
| `--rfcount-map-no-ambiguous` | boolean |  |  |  |  |  | MaP only: ignore ambiguously aligned deletion events (`-na`). Auto: off for M-MLV, on for Group II Intron (e.g. TGIRT); leave unset to use the auto default. |
| `--rfcount-map-no-deletions` | boolean |  |  |  |  | `false` | MaP only: ignore all deletion events during mutation counting (`-nd`). |
| `--rfcount-map-no-insertions` | boolean |  |  |  |  |  | MaP only: ignore insertion events during mutation counting (`-ni`). Auto: off for M-MLV, on for Group II Intron (e.g. TGIRT); leave unset to use the auto default. |
| `--rfcount-map-right-deletion` | boolean |  |  |  |  |  | MaP only: mark only the right-most base of a deletion as mutated (`--right-deletion`). Auto: on for M-MLV, off for Group II Intron (e.g. TGIRT); leave unset to use the auto default. |
| `--rfcount-map-sort-by-read-name` | boolean |  |  |  |  | `true` | In mutation mode (`-m`), pre-sort paired-end reads by read name (`--sort-by-read-name`). No effect on single-end data. |
| `--rfcount-mask-file` | string (file path) |  |  |  |  |  | Path to rf-count mask file (`--mask-file`). |
| `--rfcount-paired-only` | boolean |  |  |  |  | `false` | For paired-end samples, use only reads with both mates mapped (`--paired-only`). |
| `--rfcount-primary-only` | boolean |  |  |  |  | `false` | Use only primary alignments in rf-count (`--primary-only`). |
| `--rfcount-properly-paired` | boolean |  |  |  |  | `false` | For paired-end samples, use only properly paired reads (`--properly-paired`). |
| `--rfcount-strandedness` | string |  |  | `unstranded`, `first`, `second` |  | `unstranded` | Library strandedness fallback for rf-count-genome when RSeQC inference is unavailable (e.g. viral/bacterial references without a usable BED annotation). |
| `--rfcount-trim-5prime` | integer |  |  |  | ≥ 0 | `0` | Trim this many bases from the 5' read end for rf-count (`-t5`). |
| `--rfeval-ignore-terminal` | boolean |  |  |  |  | `true` | Exclude terminal base-pairs from rf-eval calculations (`-it`). |
| `--rfeval-img` | boolean |  |  |  |  | `false` | Generate R metric plots in rf-eval (`-g`). |
| `--rfeval-keep-lonelypairs` | boolean |  |  |  |  | `true` | Retain lonely/isolated base-pairs in rf-eval (`-kl`). |
| `--rfeval-keep-pseudoknots` | boolean |  |  |  |  | `true` | Retain pseudoknotted base-pairs in rf-eval (`-kp`). |
| `--rfeval-reactivity-cutoff` | number |  |  |  | ≥ 0; ≤ 1 | `0.7` | Cutoff for classifying a base as highly-reactive in rf-eval unpaired-coefficient calculation (`-c`). |
| `--rfeval-reference` | string (file path) |  |  |  | matches `^\S+\.db$` |  | Path to a `.db` file of known RNA secondary structures. Enables rf-eval when provided. |
| `--rfeval-terminal-as-unpaired` | boolean |  |  |  |  | `false` | Treat terminal base-pairs as unpaired in rf-eval (`-tu`). |
| `--rfeval-windows` | string (file path) |  |  |  |  |  | Optional manifest of sub-region references, one per line: `ref_seq_id start end structure_id [strand]` (1-based inclusive, in the XML's own coordinate space). When set, rf-norm reactivities are sliced to each window before rf-eval, so a sub-region structure (e.g. an Rfam element on a whole chromosome) is scored against a matching windowed XML instead of the diluted full transcript. `structure_id` must match an entry in `--rfeval_reference`. |
| `--rffold-ct` | boolean |  |  |  |  | `false` | Write CT format structures with rf-fold (`-ct`). Disabled by default to keep dot-bracket output. |
| `--rffold-dotplot` | boolean |  |  |  |  | `true` | Generate dot plots from rf-fold (`-dp`). |
| `--rffold-fold-constraint-file` | string (file path) |  |  |  |  |  | Constraint file for allowed base-pairing positions (`-c`). |
| `--rffold-img` | boolean |  |  |  |  | `false` | Generate ViennaRNA RNAplot structure diagrams via rf-fold (`-g`). Disabled by default; slow on large transcriptomes. Use `--r2dt` for template-based diagrams instead. |
| `--rffold-intercept` | number |  |  |  |  |  | Intercept for reactivity-to-folding-constraint conversion in rf-fold (`-in`). Auto by `chemical`: DMS -2, NAI -0.8, 2A3 -0.4, other/unset -0.6. Overridden by jackknife calibration when available. |
| `--rffold-only-common` | integer |  |  |  | ≥ 1 |  | Only fold transcripts covered in at least this number of XML experiments (`-oc`). |
| `--rffold-partition-window` | integer |  |  |  | ≥ 50 | `1000` | Partition-function window size in rf-fold (`-pw N`). |
| `--rffold-shannon-entropy` | boolean |  |  |  |  | `true` | Compute and report Shannon entropy in rf-fold (`-sh`). |
| `--rffold-slope` | number |  |  |  |  |  | Slope for reactivity-to-folding-constraint conversion in rf-fold (`-sl`). Auto by `chemical`: DMS 4.6, NAI 2.2, 2A3 1, other/unset 1.8. Overridden by jackknife calibration when available. |
| `--rffold-unconstrained` | boolean |  |  |  |  | `false` | Fold without reactivity constraints in rf-fold (`-i`). |
| `--rffold-use-alifold` | boolean |  |  |  |  | `true` | Fold a group's replicates together with RNAalifold, constrained by all their reactivity profiles at once, instead of folding each with RNAfold and aggregating base pairs (`-ua`). Applies only to groups with more than one replicate. |
| `--rffold-vienna-constrained` | boolean |  |  |  |  | `false` | Use ViennaRNA hard constraints with rf-fold (`-hc`). |
| `--rffold-vienna-max-bp-span` | integer |  |  |  | ≥ 1 | `600` | Maximal base-pair span for ViennaRNA in rf-fold (`-md`). |
| `--rffold-vienna-no-lonely-pairs` | boolean |  |  |  |  | `false` | Pass ViennaRNA no-lonely-pairs mode to rf-fold (`-nlp`). |
| `--rffold-vienna-rnaplot` | string |  |  |  |  | `RNAplot` | Path to ViennaRNA `RNAplot` binary for the ViennaRNA and rf-structextract SVG structure plots. |
| `--rffold-window` | integer |  |  |  | ≥ 50 | `1000` | Enable windowed MFE folding in rf-fold with this window size (`-w -fw N`). Set null/unset to fold the whole transcript instead. |
| `--rfjackknife-img` | boolean |  |  |  |  |  | Generate R heatmap of grid-search results in rf-jackknife (`-g`). |
| `--rfjackknife-intercept` | string |  |  |  | matches `^-?\d+(\.\d+)?,-?\d+(\.\d+)?$` | `-3,0` | Comma-separated intercept range to search in rf-jackknife (`-in`), e.g. `-3,0`. |
| `--rfjackknife-intercept-step` | number |  |  |  |  | `0.2` | Step size for intercept grid search in rf-jackknife (`-is`). |
| `--rfjackknife-keep-lonelypairs` | boolean |  |  |  |  | `true` | Retain lonely base-pairs (1 bp helices) in the reference structure before comparison (`-kl`). |
| `--rfjackknife-keep-pseudoknots` | boolean |  |  |  |  |  | Retain pseudoknotted base-pairs in the reference structure during FMI comparison (`-kp`). Disabled by default because rf-fold cannot predict pseudoknots, so including them systematically lowers FMI. |
| `--rfjackknife-mfmi` | boolean |  |  |  |  | `true` | Use modified FMI (Lan et al. 2022) instead of standard FMI in rf-jackknife (`-m`). |
| `--rfjackknife-only-common` | boolean |  |  |  |  |  | Only use transcripts present across all replicates in rf-jackknife (`-oc`). |
| `--rfjackknife-pool-all` | boolean |  |  |  |  | `true` | Pool XMLs from all sample groups into a single rf-jackknife run (output: `jackknife/all_groups/`) instead of running one jackknife per group. Default: true. |
| `--rfjackknife-relaxed` | boolean |  |  |  |  | `true` | Use relaxed FMI criteria (Deigan et al. 2009) in rf-jackknife (`-x`). |
| `--rfjackknife-rf-fold-params` | string |  |  |  |  | `-md 600` | Additional rf-fold parameters passed inside rf-jackknife (`-rp`), e.g. `-md 500`. |
| `--rfjackknife-slope` | string |  |  |  | matches `^-?\d+(\.\d+)?,-?\d+(\.\d+)?$` | `0,5` | Comma-separated slope range to search in rf-jackknife (`-sl`), e.g. `0,5`. |
| `--rfjackknife-slope-step` | number |  |  |  |  | `0.2` | Step size for slope grid search in rf-jackknife (`-ss`). |
| `--rfnorm-dynamic-window` | integer or boolean |  |  |  | ≥ 0 |  | Enable dynamic normalization window (`--dynamic-window`). Set to a positive integer to enable (value is passed to `--norm-window`); set to `false` or `0` to explicitly disable even for DMS (which enables it by default). Leave unset to use the per-method default. |
| `--rfnorm-ignore-lower-than-untreated` | boolean |  |  |  |  | `false` | Set reactivities lower than untreated to zero for Ding or Siegfried scoring (`--ignore-lower-than-untreated`). |
| `--rfnorm-img` | boolean |  |  |  |  | `false` | Deprecated: rf-norm plot generation (`--img`) is always enabled. |
| `--rfnorm-mean-coverage` | number |  |  |  | ≥ 0 | `0` | Discard transcripts with mean coverage below this threshold (`--mean-coverage`). |
| `--rfnorm-median-coverage` | number |  |  |  | ≥ 0 | `0` | Discard transcripts with median coverage below this threshold (`--median-coverage`). |
| `--rfnorm-nan` | string |  |  |  |  |  | Positions with read coverage below this threshold are reported as NaN (`--nan`). Auto: 1000 for MaP, 50 for RT-stop. Set to 0 to disable NaN masking. |
| `--rfnorm-norm-independent` | boolean |  |  |  |  | `false` | Normalize each reactive base independently (`--norm-independent`). |
| `--rfnorm-norm-method` | integer |  |  | `1`, `2`, `3`, `4` |  |  | Override rf-norm normalization method (`-nm`). 1=2-8%, 2=90% Winsorizing, 3=Box-plot, 4=Mitchell (MaP only). |
| `--rfnorm-norm-window` | integer |  |  |  | ≥ 1 |  | Normalization window size (`--norm-window`). Auto: 50 for DMS or RT-stop, unset otherwise; leave unset to use the auto default. |
| `--rfnorm-normfactor-min-coverage` | integer |  |  |  | ≥ 1 |  | rf-normfactor minimum coverage (`-mc`): bases below this coverage are excluded from the normalization factor calculation. Auto: 1000 for MaP, 50 for RT-stop; leave unset to use the auto default. |
| `--rfnorm-prefilter-min-coverage` | integer |  |  |  | ≥ 0 | `1` | `--count_genome true` only: after rf-rctools extract, keep transcripts with at least one position at this coverage or higher before rf-norm. Set to 0 to keep the full annotation RC. |
| `--rfnorm-pseudocount` | number |  |  |  | ≥ 0 |  | Pseudocount used by Ding scoring (`--pseudocount`). |
| `--rfnorm-raw` | boolean |  |  |  |  | `false` | Score raw reactivities without applying normalization (`--raw`). |
| `--rfnorm-reactive-bases` | string |  |  |  | matches `^[A-Za-z]+$` |  | Reactive bases used for normalization window selection (`--reactive-bases`), e.g. `AC` for DMS. |
| `--rfnorm-remap-reactivities` | boolean |  |  |  |  | `false` | Remap normalized reactivities to the 0-1 range according to Zarringhalam et al. (`--remap-reactivities`). |
| `--rfnorm-score-method` | integer |  |  | `1`, `2`, `3`, `4` |  |  | Override rf-norm scoring method (`-sm`). 1=Ding, 2=Rouskin, 3=Siegfried, 4=Zubradt. |
| `--rfnorm-use-normfactor` | boolean |  |  |  |  |  | Cross-experiment normalization via rf-normfactor (one factor set per reference, fed to rf-norm via `-nf`), putting reactivities on a common scale. Leave unset for auto (enabled only for a reference with more than one treated sample to cross-normalise); set `true` to force on, `false` to force off (per-sample box-plot). |
| `--rfnorm-window-offset` | integer |  |  |  | ≥ 0 |  | Normalization window offset (`--window-offset`). |
| `--rfrctools-gtf-attribute` | string |  |  |  |  | `transcript_id` | GTF attribute used as the output RC entry ID by rf-rctools (`-b`). |
| `--rfrctools-gtf-feature` | string |  |  |  |  | `exon` | GTF feature type to extract with rf-rctools (`-f`); override for non-standard annotations. |
| `--rfwiggle-keep-bases` | string |  |  |  |  |  | Restrict WIG output to specific bases using an IUPAC code or combination (e.g. `AC` for DMS probing) (`-kb`). Default: all bases (`N`). |
| `--rfwiggle-report-zeroes` | boolean |  |  |  |  | `true` | Report positions with zero reactivity in the WIG/BigWig output (`-z`). Enabled by default so genome browsers receive complete tracks without gaps. |
| `--rnaframework-r-path` | string |  |  |  |  | `/usr/bin/R` | Path to R executable used by rf-count, rf-norm, and rf-fold plotting. |
| `--stop-after-jackknife` | boolean |  |  |  |  | `false` | Stop the pipeline after rf-jackknife completes, skipping rf-fold, structure visualisation, browser track generation, and RDAT output. Useful for calibration runs where you only want jackknife statistics. |
| `--structextract` | boolean |  |  |  |  | `false` | Run rf-structextract after rf-fold to extract high-confidence, low-reactivity / low-Shannon structural motifs from the folded structures. |
| `--structextract-dinucl-shuffle` | boolean |  |  |  |  | `false` | rf-structextract preserves dinucleotide frequencies when shuffling for energy evaluation (`-ds`). |
| `--structextract-eval-energy` | boolean |  |  |  |  | `false` | rf-structextract only reports elements with a free energy significantly lower than expected by chance (`-ee`). |
| `--structextract-ignore-react` | boolean |  |  |  |  | `false` | rf-structextract skips low-reactivity evaluation (`-ir`). When false (default), reactivity is evaluated so only regions with probing support are extracted. |
| `--structextract-ignore-shannon` | boolean |  |  |  |  | `false` | rf-structextract skips low-Shannon evaluation (`-is`). When `false`, the Shannon-entropy test is applied so only high-confidence regions are extracted. |
| `--structextract-max-loop-size` | integer |  |  |  | ≥ 1 |  | rf-structextract discards elements with a loop larger than this (`-xl`). Unset for no limit. |
| `--structextract-max-motif-len` | integer |  |  |  | ≥ 1 |  | rf-structextract discards structure elements longer than this (`-xm`). Unset for no limit. |
| `--structextract-min-below-median` | number |  |  |  | ≥ 0; ≤ 1 | `0.7` | rf-structextract minimum fraction of bases whose Shannon and reactivity are below the transcript median (`-mb`). |
| `--structextract-min-motif-len` | integer |  |  |  | ≥ 1 | `50` | rf-structextract discards structure elements shorter than this (`-mm`). |
| `--structextract-min-paired-frac` | number |  |  |  | ≥ 0; ≤ 1 | `0.45` | rf-structextract discards elements with less than this fraction of paired bases (`-mp`). |
| `--structextract-min-transcript-len` | integer |  |  |  | ≥ 1 | `500` | rf-structextract skips low-reactivity/low-Shannon evaluation for transcripts below this length (`-ml`). |
| `--structextract-min-value-frac` | number |  |  |  | ≥ 0; ≤ 1 | `0.4` | rf-structextract windows with less than this fraction of bases covered are set to NaN (`-mv`). |
| `--structextract-multiway-only` | boolean |  |  |  |  | `false` | rf-structextract only reports elements encompassing multiway junctions (`-mo`). |
| `--structextract-n-shufflings` | integer |  |  |  | ≥ 1 | `100` | rf-structextract number of sequence shufflings for energy evaluation (`-ns`). |
| `--structextract-one-per-file` | boolean |  |  |  |  | `false` | rf-structextract reports each extracted element in a separate file (`-opf`). |
| `--structextract-plot` | boolean |  |  |  |  | `true` | Render an SVG diagram per extracted rf-structextract motif via ViennaRNA RNAplot. |
| `--structextract-pvalue` | number |  |  |  | ≥ 0; ≤ 1 | `0.05` | rf-structextract p-value threshold for energy significance (`-v`); requires `--structextract_eval_energy`. |
| `--structextract-win-size` | integer |  |  |  | ≥ 1 | `50` | rf-structextract window size in nt for median reactivity/Shannon calculations (`-w`). |

## sample_metadata_options

| parameter | type | required | hidden | allowed values | constraints | default | description |
|---|---|---|---|---|---|---|---|
| `--RT-enzyme` | string |  |  |  |  |  | Fallback reverse transcriptase enzyme for rows missing `RT_enzyme` (e.g. `M-MLV`). |
| `--chemical` | string |  |  |  |  |  | Fallback chemical probing reagent for rows missing `chemical` (e.g. `1M7`). |
| `--exact-untreated-pairing` | boolean |  |  |  |  |  | Require an exact `sample_group`+`replicate` match when pairing treated samples with untreated/denatured controls. By default, a treated group with no exact match falls back to the control whose `sample_group` shares the longest leading substring with it (see the usage docs). With this set, unmatched treated groups proceed without an untreated control (scoring method 2 or 4). |
| `--fuzzy-untreated-pairing` | boolean |  | yes |  |  |  | Deprecated: use `--exact_untreated_pairing` (inverted). |
| `--method` | string |  |  |  |  |  | Fallback probing method for rows missing `method`. |
| `--organism` | string |  |  |  |  |  | Fallback organism for rows missing `organism`, typically a Latin binomial such as `Homo sapiens`. |
| `--pH` | number |  |  |  |  |  | Fallback DMS reaction pH for rows missing `pH`. |
| `--principle` | string |  |  | `RT-stop`, `MaP`, `rt-stop`, `map` |  |  | Fallback probing principle for rows missing `principle`. |
| `--sample-id` | string |  |  |  | matches `^\S+$` |  | Fallback sample ID for rows missing `sample_id`. |
| `--umi-pattern` | string |  |  |  |  |  | Fallback UMI pattern for rows missing `umi_pattern`. Supplying a pattern enables umi_tools extract before cutadapt. |

<!-- Generated from nf-core/rnastructurome@633ab1d0d12103f9002fe6e781ae1251df2d2656. Do not edit by hand. -->
