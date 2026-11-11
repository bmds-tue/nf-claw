<p align="center">
  <img src="docs/images/nf-claw-logo-with-text.png" alt="nf-claw" width="240">
</p>

<p align="center">
  <a href="https://github.com/bmds-tue/nf-claw/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/bmds-tue/nf-claw/tests.yml?branch=main&amp;label=tests" alt="Tests status"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"></a>
  <a href="https://bmds-tue.github.io/nf-claw/"><img src="https://img.shields.io/badge/website-bmds--tue.github.io-00ffff.svg" alt="Website"></a>
</p>

# nf-claw

A self-maintaining library of [nf-core](https://nf-co.re) pipelines for AI agents and bioinformaticians. Each pipeline is an unmodified git submodule pinned to a release, with a generated `skill.md` that says how to run it and a `reference.md` that lists every parameter. The `nfclaw` command checks a run before it starts, records what a replay needs, chains pipelines and serves all of this to agents over MCP. Scheduled workflows move the pins to new releases once the tests and each changed pipeline's own test run pass.

The website, [bmds-tue.github.io/nf-claw](https://bmds-tue.github.io/nf-claw/), shows the same
content: the pipelines, their parameters, the documentation and the state of the automation when the
site was last built.

## What it does

| Step | Command | Result |
|---|---|---|
| Find | `nfclaw list <keywords>` | The pipelines that match a request, ranked, without reading the whole catalog. |
| Read | `nfclaw show <name>` | The pinned release's inputs, required parameters and run command. |
| Run | `nfclaw run <name> …` | A real run, checked first. `--check` validates and prints the command without starting it. |
| Follow | `nfclaw status <outdir>` | Whether the run is still going, how it ended, and any caveats the pipeline reported about its results. |
| Replay | `<outdir>/provenance/commands.sh`, `nfclaw verify` | A guarded re-run into a fresh directory, compared with the original by path, bytes and environment. |
| Assess | `nfclaw assess` | The declared scientific outputs and sample coverage, checked against an explicit contract. |
| Chain | `nfclaw chain run` | Pipelines in sequence, each fed by the checksummed outputs of the one before. |
| Serve | `nfclaw mcp` | All of the above as MCP tools. Long runs become detached jobs. |

nfclaw checks a run before it starts and again before it reports success. It refuses unknown flags,
invalid values, unsafe file names or sample identifiers, and output directories that overlap the
inputs, instead of correcting them silently. It fails a run whose inputs, configs or pipeline source
changed while it ran. [AGENTS.md](AGENTS.md) states these rules briefly and
[docs/preflight.md](docs/preflight.md#inputs-refused-before-launch) in full;
[docs/architecture.md](docs/architecture.md) explains how they are enforced, and
[docs/known-issues.md](docs/known-issues.md) where the checks stop.

The pipeline source trees are never edited. A few exact releases need corrections at run time, and
each correction is recorded with the run and replayed with it: configs for fastqrepair 1.1.1, and
patched working copies of Bactmap, Createtaxdb and Funcscan
([source corrections](docs/source-corrections.md)).

## Layout

| Path | Contents |
|---|---|
| `pipelines/<name>/` | `upstream/`, the pipeline pinned to a release (a git submodule), and the generated `skill.md` (how to run it) and `reference.md` (every parameter). |
| `runner/` | The `nfclaw` command: preflight, launch, logs, provenance, replay, verification, chaining and the MCP server. |
| `librarian/` | Maintenance code. It generates the skills and catalogs, checks for drift, bumps releases and finds new pipelines. |
| `handoffs/` | Chaining rules, one file per pipeline pair (`handoffs/<upstream>/<downstream>.json`), checked by the drift gate. |
| `catalog.md`, `catalog.json` | The generated index of all pipelines: pinned version, input, outputs and description, plus tools and downstream pipelines in the JSON. Search it rather than reading it whole. |
| `sources.tsv` | Each pipeline's upstream repository and update policy: `latest-release`, or `hold` to keep the current pin. |
| `docs/` | The guides listed below, and dated audit records with their evidence (`docs/audit/`). |
| `website/` | The static website, rebuilt from the repository on every push to `main`. |

## Documentation guides

### Running pipelines

| Document | What it covers |
|---|---|
| [`AGENTS.md`](AGENTS.md) | How to find, run, follow, replay and chain a pipeline. Written for agents and useful to people. [`CLAUDE.md`](CLAUDE.md) imports it for Claude Code. |
| [`docs/preflight.md`](docs/preflight.md) | Which checks run before launch, which are left to the pipeline, the samplesheet generator and the pipelines it supports, and the inputs refused before launch. |
| [`docs/chaining.md`](docs/chaining.md) | Chain specs, handoff rules, resuming a chain and verifying which outputs became which inputs. |
| [`docs/mcp.md`](docs/mcp.md) | Setting up `nfclaw mcp` in Claude Code, Codex, Antigravity, Hermes and other clients, its tools, and detached jobs. |
| [`docs/timeouts.md`](docs/timeouts.md) | Optional deadlines, background runs and cheap progress checks. |
| [`docs/compatibility.md`](docs/compatibility.md) | Matching the Nextflow version to a release, `--nxf-ver` and `--nxf-env`, the CI workflows and host requirements. |
| [`docs/dramp-reference.md`](docs/dramp-reference.md) | Preparing a DRAMP antimicrobial peptide reference for Funcscan. |
| [`docs/known-issues.md`](docs/known-issues.md) | Symptoms and fixes: host setup, runs and resume, replay, chains, harmless warnings and upstream bugs. |

### Trusting results

| Document | What it covers |
|---|---|
| [`docs/replay.md`](docs/replay.md) | What a provenance bundle holds, what the replay checks, resuming with changed inputs, and what `nfclaw verify` and `nfclaw assess` can and cannot show. |
| [`docs/scientific-output-contracts.md`](docs/scientific-output-contracts.md) | Writing a contract for `nfclaw assess`: formats compared (BAM, VCF, FASTA, TSV, H5AD), sample coverage and tolerances. |
| [`docs/source-corrections.md`](docs/source-corrections.md) | The recorded corrections for Createtaxdb, Funcscan, Bactmap and fastqrepair. |
| [`docs/validation.md`](docs/validation.md) | End-to-end runs of every pinned pipeline and of nfclaw's features, the settings each needed, and what that evidence does not show. |

### Maintaining nf-claw

| Document | What it covers |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | How the repository and the runner are put together: modules, preflight, locking, provenance, verification and assessment. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Reporting bugs, the development workflow, adding a pipeline or handoff rule, tests, releases and documentation conventions. |
| [`docs/updating.md`](docs/updating.md) | The daily update and weekly discovery workflows, update policies and the drift gate. |
| [`docs/maintenance.md`](docs/maintenance.md) | What the maintenance workflows must show before they publish a change to `main`. |
| [`docs/audit/`](docs/audit/README.md) | Dated audit records and the evidence behind each change. |
| [`CHANGELOG.md`](CHANGELOG.md) | User-visible changes, newest first, by pull request. |
| [`SECURITY.md`](SECURITY.md) | How to report a vulnerability privately, and what is in scope. |
| [`llms.txt`](llms.txt) | An index of this documentation for AI agents ([llms.txt](https://llmstxt.org) format). |

## Quickstart

Clone into a path without spaces (on macOS, outside iCloud folders). You need Python 3.11+, Git,
Nextflow with Java 17+, and Docker or Singularity/Apptainer.

```bash
# main moves as pins are bumped; add --branch v1.0.0 for the 1.0.0 release
git clone --recurse-submodules https://github.com/bmds-tue/nf-claw.git
cd nf-claw
python3 -m venv .venv
source .venv/bin/activate
pip install -e .           # puts nfclaw on PATH
```

Install it editable: `nfclaw` reads the pinned submodules and generated files from the checkout,
from whichever directory you call it. Without installing, `python3 -m runner <command>` from the
repository root does the same.

```bash
nfclaw list variant calling     # pipelines that match, ranked
nfclaw show rnaseq              # the pinned release's inputs, required parameters and run command

# validate and print the command without running it
nfclaw run rnaseq --input samplesheet.csv --outdir results -profile docker \
  --fasta /data/genome.fa --gtf /data/genes.gtf --igenomes-ignore true --check

# the same without --check runs it; then follow it
nfclaw status results           # success, running, or how it ended
```

Use your own matched FASTA and GTF. The parameters a schema marks as required do not cover every
reference an analysis needs; each `skill.md` has a section on references. `--check` leaves
`--outdir` untouched but needs the run's tools on the host, including a running Docker daemon for
the Docker profile.

Other common tasks:

| To | Use | Details |
|---|---|---|
| Build the samplesheet from data files | `nfclaw run rnaseq --input /data/fastq --sheet-set strandedness=auto …` | [AGENTS.md](AGENTS.md#inputs) |
| Replay a run and compare it | `results/provenance/commands.sh`, then `nfclaw verify results.replay --against results` | [replay](docs/replay.md) |
| Check scientific outputs | `nfclaw assess results --contract FILE` | [output contracts](docs/scientific-output-contracts.md) |
| Run another release, or `dev` | `nfclaw versions rnaseq`, then `--pipeline-version 3.14.0` | [AGENTS.md](AGENTS.md#to-run-a-specific-non-latest-version) |
| Choose the Nextflow version | `--nxf-ver 25.10.4`, `--nxf-env NXF_OFFLINE=true` | [compatibility](docs/compatibility.md) |
| Fit a small machine | `--limit-cpus 4 --limit-memory 15.GB` | [AGENTS.md](AGENTS.md#running-on-a-machine-smaller-than-the-pipeline-assumes) |
| Set a deadline | `--timeout SECONDS` (whole run), `--limit-time` (each task) | [timeouts](docs/timeouts.md) |
| Chain pipelines | `nfclaw chain run spec.json --outdir /abs/chain` | [chaining](docs/chaining.md) |
| Use it from an MCP client | `claude mcp add nfclaw -- "$PWD/.venv/bin/nfclaw" mcp` | [MCP](docs/mcp.md) |

## Provenance and replay

Unless told otherwise, `nfclaw run` writes a provenance bundle to `<outdir>/provenance/`: the run log,
a replay script with its dependency guard, an archive of the pipeline source, copies of the configs,
records of the parameters, checksums and files, and as much of the execution environment as could
be recorded. [docs/architecture.md](docs/architecture.md#25-provenance-bundles) lists every file. The
bundle does not contain the input data, container images or plugins, so those must still be
available for a replay. [docs/replay.md](docs/replay.md) covers replaying, resuming and verifying,
and their limits.

## Maintenance

Generated files are never edited by hand. `make build` regenerates every `skill.md`, `reference.md`
and `catalog.*` from the pinned submodules, `make update` bumps the pins to the newest releases, and
`make check` runs the drift gate and the tests. [CONTRIBUTING.md](CONTRIBUTING.md) explains each
target and how to add a pipeline or a handoff rule.

## How it stays current

| Workflow | Runs | What it does |
|---|---|---|
| `auto-update.yml` | daily | Bumps pins to new releases. A candidate reaches `main` only after the test matrix, the drift gate and real runs of each changed pipeline's bundled test pass ([publication policy](docs/maintenance.md)). |
| `discover-pipelines.yml` | weekly | Adds new nf-core DSL2 pipelines through the same gate. |
| `tests.yml` | push to `main`, pull requests | pytest on Ubuntu and macOS with Python 3.11–3.15, integration tests against a real Nextflow, and the website build and browser tests. |
| `drift-check.yml` | pull requests, daily | Regenerates every skill, reference and catalog, and fails on any difference. |
| `smoke.yml` | runner or pipeline changes on `main`, weekly | `nfclaw run --check --demo` for every pipeline, on the Nextflow version its `skill.md` advises. |
| `nextflow-validate.yml` | pin changes on `main`, weekly | `nextflow run -preview` of every pipeline's test profile. |
| `demo-validation.yml`, `fastqrepair-validation.yml` | pull requests that change the runner | A real run in Docker, a replay, and checks of the results and the recorded environment. |
| `pipeline-execution.yml` | manual | A real run of any one pipeline's test profile in Docker. |
| `deploy-pages.yml` | push to `main` | Rebuilds and publishes the website. |
| `codeql.yml` | push, pull requests, weekly | Code scanning of the Python, JavaScript/TypeScript and workflow files. |

[docs/compatibility.md](docs/compatibility.md#continuous-validation) gives each workflow's exact
scope and what fails it.

## Scientific limits

nfclaw validates inputs and parameters, assembles the command, isolates the run and records its
provenance. None of that shows that the results are biologically correct: a run can pass every check,
exit 0 and still be wrong for the question asked. Before you rely on results:

1. Validate the pipeline, parameters and reference against benchmark data suited to your question.
2. Read the caveats `nfclaw status` reports for a successful run. A pipeline can exit 0 after
   skipping samples or ignoring failed tasks (`completion_caveats` in the run manifest).
3. Compare a replay with `nfclaw verify --strict`, and inspect files that differ with tools that
   understand their format.
4. Check [docs/known-issues.md](docs/known-issues.md) for the release you run.

`nfclaw assess` checks declared outputs and sample coverage against a contract
([guide](docs/scientific-output-contracts.md)). Two demo contracts are supplied; other pipelines
need their own.

## Citation and attribution

The pipelines are the work of the [nf-core](https://nf-co.re) community. nf-claw includes them
unmodified as pinned submodules, and each keeps its own authors, licence and citations. The few
corrections nf-claw applies at run time are documented separately.

nf-claw was created by Danilo Monge (Eberhard Karls Universität Tübingen). It adapts ideas and
repository structure from [ClawBio](https://clawbio.ai), created by Manuel Corpas (MIT licence;
copyright notice in [`LICENSE`](LICENSE), details in [`NOTICE`](NOTICE)).

If you use nf-claw in research, cite it with [`CITATION.cff`](CITATION.cff), together with:

- **Nextflow:** Di Tommaso P, *et al.* Nextflow enables reproducible computational workflows. *Nat Biotechnol* **35**, 316–319 (2017). [doi:10.1038/nbt.3820](https://doi.org/10.1038/nbt.3820)
- **nf-core:** Ewels PA, *et al.* The nf-core framework for community-curated bioinformatics pipelines. *Nat Biotechnol* **38**, 276–278 (2020). [doi:10.1038/s41587-020-0439-x](https://doi.org/10.1038/s41587-020-0439-x)
- **The pipeline you ran:** see `pipelines/<name>/upstream/CITATIONS.md`.
- **ClawBio:** Corpas M. ClawBio: Bioinformatics-Native AI Agent Skill Library. Zenodo (2026). [doi:10.5281/zenodo.19420648](https://doi.org/10.5281/zenodo.19420648)

nf-claw is MIT-licensed (© Danilo Monge). The nf-core pipelines are MIT-licensed, and Nextflow is
Apache-2.0.
