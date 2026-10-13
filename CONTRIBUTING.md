# Contributing to nf-claw

Welcome! nf-claw provides AI agents and bioinformaticians with a token-minimal, deterministic, and drift-free interface to nf-core workflows. Contributions are welcome across pipeline curation, chaining rules, runtime features, testing, and documentation.

---

### Navigation

[Core Tenets](#core-development-tenets) • [Repository Structure](#repository-structure) • [Reporting Bugs](#reporting-bugs) • [Proposing New Features](#proposing-new-features) • [Fixing Inconsistencies](#fixing-inconsistencies--schema-drift) • [Contribution Workflow](#contribution-workflow) • [Coding Standards](#coding-standards--implementation-guidelines) • [Adding Pipelines](#adding-a-new-pipeline) • [Chaining Handoff Rules](#adding-a-chaining-handoff-rule) • [Testing & Quality](#testing-requirements--quality-assurance) • [Agent Guidance Sync](#agent-guidance-sync)

---

## Core Development Tenets

All contributions must uphold four architectural invariants:

| Tenet | Rule & Invariant |
|---|---|
| **1. Pipeline-Agnostic Design** | General behavior in `runner/` (execution runtime) and `librarian/` (maintenance) comes from pinned schemas and declarative handoff rules, rather than biological assumptions about names or columns. Narrow, audited exceptions in `runner/fastqrepair_compat.py`, `runner/path_roles.json` and `runner/input_roles.json` require explicit source evidence and appropriate identity guards. Runtime corrections record their evidence for replay. Keep new compatibility logic equally explicit and guarded. |
| **2. Deterministic Outputs** | Generated markdown and JSON documents must remain bit-identical across repeated runs on the same commits. Timestamps are forbidden in generated context; git commit hashes serve as immutable version anchors. |
| **3. Test-Driven Development (TDD)** | Every bugfix or new feature must be paired with regression tests. Write the failing test first, implement the minimal fix, and verify with `make test`. |
| **4. Zero-Drift Invariant** | Committed context (`skill.md`, `reference.md`, `catalog.*`) must always match pinned submodule code. Any discrepancy between context files and pinned submodules is rejected by the drift gate (`python3 -m librarian.check_drift`). |

---

## Repository Structure

The repository is structured into four distinct, decoupled functional zones:

```
                          ┌────────────────────────────────────────┐
                          │             nf-claw Core               │
                          └────────────────────────────────────────┘
                                              │
             ┌──────────────────┬─────────────┴────────────┬──────────────────┐
             ▼                  ▼                          ▼                  ▼
       ┌──────────────┐   ┌──────────────┐          ┌──────────────┐   ┌────────────────┐
       │  pipelines/  │   │   handoffs/  │          │   runner/    │   │   librarian/   │
       │ (Submodules  │   │  (Chaining   │          │ (CLI, Engine │   │ (Drift Gate,   │
       │  & Skills)   │   │    Rules)    │          │  & Runtime)  │   │  Generators)   │
       └──────────────┘   └──────────────┘          └──────────────┘   └────────────────┘
```

| Path | Zone | Function & Responsibility |
|---|---|---|
| `pipelines/<name>/` | **Library Content** | Contains `upstream/` (pinned git submodule pointing to an official release tag) plus generated `skill.md` (agent instructions) and `reference.md` (schema parameter reference). |
| `runner/` | **Execution Engine** | Python runtime (`nfclaw` CLI) providing preflight schema validation, schema-driven samplesheet generation from data files, execution locking, signal trapping, provenance capture, and multi-stage chaining. |
| `librarian/` | **Maintenance Automation** | Tools for building context files (`write_skill.py`, `write_catalog.py`), checking schema drift (`check_drift.py`), and tracking upstream releases. |
| `handoffs/` | **Chaining Rules** | Declarative JSON specifications (`handoffs/<upstream>/<downstream>.json`) defining output-to-input mappings between sequential stages. |
| `sources.tsv` | **Manifest Registry** | Tab-separated manifest mapping pipeline names to upstream git remotes and version tracking policies (`latest-release`). |
| `catalog.md` / `.json` | **Pipeline Catalog** | Auto-compiled catalog detailing inputs, conditional outputs, upstream descriptions, and tool citations. |
| `docs/` | **Documentation** | Deep architectural guides, chaining manuals, engine compatibility matrices, known issues, and update automation docs. |
| `website/` | **Live Portal** | Next.js 15 static digital interface and documentation hub rebuilt continuously from repository data. |

---

## Reporting Bugs

Before opening a bug report, determine which category the issue falls into:

### 1. Categorizing the Issue

| Category | Typical Symptoms | Resolution Path |
|---|---|---|
| **Host / Environment Issue** | Spaces in directory path, missing Python packages, IPv6 JVM socket timeouts, Docker permissions, workstation OOMs. | Consult [`docs/known-issues.md`](docs/known-issues.md). Fix via flags (`--nxf-env`, `--limit-*`, `--config`) or system configuration. |
| **Upstream Pipeline Defect** | A task failure inside an nf-core process (`.command.err`), container image bugs, or conflicting test profiles. | Pinned releases are wrapped **unmodified**. Document the workaround in `docs/known-issues.md` and report the bug upstream to the respective [nf-core repository](https://github.com/nf-core). |
| **nf-claw Runtime Defect** | Preflight parameter validation falsely rejecting valid values, locking deadlocks, broken provenance bundles, or chaining errors. | File a bug report on [GitHub Issues](https://github.com/bmds-tue/nf-claw/issues). |

### 2. How to File an Issue

When filing a bug report on GitHub:
1. **Title:** Clear, concise summary including component (e.g. `[runner]`, `[chain]`, `[librarian]`).
2. **Context:**
   - Operating system and architecture (`uname -a`).
   - Python version (`python3 --version`).
   - Nextflow version (`nextflow -version`).
   - Container runtime (`docker --version` or `apptainer --version`).
3. **Reproduction Steps:**
   - Exact command line executed.
   - Pinned pipeline name and version (`nfclaw versions <name>`).
   - Minimal samplesheet or parameters required to reproduce the behavior.
4. **Logs & Diagnostics:**
   - Attach `<outdir>/provenance/logs/run.log` and `<outdir>/provenance/run_manifest.json`.
   - Relevant excerpts from Nextflow's log (`<outdir>/.nextflow.log`) and task `.command.err`.

---

## Proposing New Features

We welcome ideas that enhance nf-claw's reliability, ergonomics, and scientific rigor.

### Feature Alignment Guidelines
- **Schema-Driven Behavior:** Features must remain pipeline-agnostic. Interpret scientific inputs and parameters through upstream schemas and declarative handoff rules, rather than assumptions about a pipeline's name.
- **Token Efficiency:** Context and outputs must remain concise and token-minimal for AI agents.
- **Deterministic Execution:** Features must produce predictable, verifiable results across environments.

### Process
1. **Open an Issue / Discussion:** Describe the proposed feature, user workflow, and technical rationale before submitting large PRs.
2. **Design Review:** Discuss integration points (`runner/`, `librarian/`, or CLI).
3. **Implementation:** Pair the feature with comprehensive unit tests and documentation updates.

---

## Fixing Inconsistencies & Schema Drift

nf-claw maintains strict bidirectional synchronization between pinned code and documentation.

### 1. Schema Drift (`librarian/check_drift.py`)
If `python3 -m librarian.check_drift` reports drift:
- **Missing or stale skills/catalog:** Run `make build` to regenerate context files from pinned submodules.
- **Manifest mismatch:** Ensure `sources.tsv`, `.gitmodules`, and filesystem directories in `pipelines/` define the exact same pipeline set and remote URLs.
- **Handoff rule incompatibility:** If an upstream pipeline renamed an output file or a downstream pipeline modified its samplesheet schema, update the mapping in `handoffs/<upstream>/<downstream>.json` to fit both schemas.

### 2. Upstream Defects vs. Local Workarounds
- **Never edit files inside `pipelines/<name>/upstream/` directly.** Git submodules point to upstream release commits and must remain vendor-clean.
- Workarounds for upstream defects are implemented via narrow runtime mechanisms (such as `-c` compatibility configs or documentation in `docs/known-issues.md`).

---

## Contribution Workflow

### 1. Fork, Clone, and Setup

> [!IMPORTANT]
> **Use a Space-Free Path:**
> Clone the repository into a filesystem path **without spaces** (e.g. `/home/user/nf-claw`). Many bioinformatics tools and Nextflow work directories fail when spaces are present. On macOS, avoid iCloud-synced folders.

```bash
# 1. Clone your fork
git clone https://github.com/<your-username>/nf-claw.git
cd nf-claw

# 2. Initialize submodules
git submodule update --init

# 3. Create virtual environment (Python 3.11+)
python3 -m venv .venv
source .venv/bin/activate

# 4. Install in editable mode with test dependencies and lint tooling
pip install -e ".[dev,yaml]"
pip install ruff
```

### 2. Branching & Commit Conventions
Create a descriptive branch for your work:
```bash
git checkout -b feat/my-new-feature
# or
git checkout -b fix/resolve-locking-issue
```

We follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New features or capabilities (e.g. `feat(runner): add strict memory limit flag`).
- `fix:` Bugfixes and error corrections (e.g. `fix(chain): resolve POSIX flock race condition`).
- `docs:` Documentation improvements and guide refinements (e.g. `docs: polish contribution guide`).
- `test:` Test additions or regression test enhancements (e.g. `test: add preflight samplesheet test`).
- `chore:` Maintenance, dependency updates, and workflow changes.

### 3. Submitting Pull Requests
Before opening a PR:
1. Ensure all tests pass: `make test`.
2. Verify zero schema drift: `python3 -m librarian.check_drift`.
3. Check linting as CI does: `ruff check .`.
4. If documentation or data files were modified, verify the static site build:
   ```bash
   # Use Node.js 24 LTS, matching CI
   npm --prefix website ci
   npm --prefix website run typecheck
   npm --prefix website run build
   ```

When submitting the PR on GitHub:
- Provide a clear description of the problem solved and the implementation approach.
- Reference any relevant GitHub issues (`Fixes #...`).
- Verify that automated CI checks (`tests/pytest`, `drift-check/drift`) pass.

---

## Coding Standards & Implementation Guidelines

### Python Standards (3.11+)
- **Modern Typing:** Use Python 3.11+ type annotations (`from __future__ import annotations`, `str | None`, `list[str]`, `dict[str, Any]`).
- **Path Handling:** Always use `pathlib.Path` for filesystem operations. Do not concatenate strings for paths.
- **Subprocess Execution:** Never invoke bare shell strings (`shell=True`). Use `subprocess.Popen` or `subprocess.run` with discrete argument lists (`list[str]`) to prevent word splitting and shell injection vulnerabilities.
- **Process Signals:** Ensure background processes cleanly trap `SIGINT` and `SIGTERM` and shut down child tasks.
- **Space-Free Path Invariant:** Use `runner/preflight.py` checks for repository, output and work paths. `--allow-spaces` bypasses the space check; LF/CR remain forbidden. Input filename and route checks live in `runner/input_safety.py`.

### Code Style & Linting
We enforce Ruff configuration defined in `pyproject.toml`:
```bash
ruff check .
```
Keep code clean, readable, and free of extraneous dependencies.

---

## Adding a New Pipeline

All pipelines in nf-claw must be **DSL2** (DSL1 was removed in Nextflow 22.12 and cannot run).

### Step 1: Validate the Pipeline Name
Pipeline names must consist solely of ASCII letters, digits, dots, hyphens, and underscores, beginning and ending with an alphanumeric character:
```regex
^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$
```

| Candidate Name | Status | Rationale |
|---|---|---|
| `rnaseq` | Valid | Pure alphanumeric string. |
| `viral-recon_v2` | Valid | Alphanumeric with hyphens and underscores. |
| `../evil` | Invalid | Directory traversal attempt; rejected by sanitization. |
| `.hidden` | Invalid | Begins with a dot; special path component. |

### Step 2: Register in `sources.tsv`
Add a tab-separated entry to `sources.tsv`:
```tsv
<name>	https://github.com/nf-core/<name>.git	latest-release
```
The repository remote must point to official nf-core infrastructure (`https://github.com/nf-core/<name>.git`). The version tracking policy is `latest-release`.

### Step 3: Add and Pin the Git Submodule
```bash
git submodule add https://github.com/nf-core/<name>.git pipelines/<name>/upstream
git -C pipelines/<name>/upstream fetch --tags
git -C pipelines/<name>/upstream checkout tags/<X.Y.Z>   # Pin to a published release tag (e.g. 1.2.0)
```

> [!NOTE]
> Never leave the submodule pointing to `main`, `master`, or `dev`. An unpinned submodule causes context generation to record a branch commit rather than an immutable release tag.

### Step 4: Build Context Files
```bash
make build
```
This generates `pipelines/<name>/skill.md` and `pipelines/<name>/reference.md`, and recompiles `catalog.json` and `catalog.md`.

### Step 5: Verify Schema Drift and Tests
```bash
make check
```
Both `librarian.check_drift` and the full pytest suite must pass with 0 errors.

---

## Adding a Chaining Handoff Rule

Handoff rules describe how outputs published by an upstream pipeline are adapted into inputs for a downstream pipeline. Rules reside in `handoffs/<upstream>/<downstream>.json`.

### 1. Author the Rule File
Inspect the upstream pipeline's `docs/output.md` and publication code to identify output paths, and the downstream parameter's declared input schema to identify required columns. Some parameters use an auxiliary schema; inspect the pinned parser when its contract disagrees with a bundled template. Static checks validate parameters and column compatibility; actual published files are verified at handoff time.

Example: `handoffs/fetchngs/rnaseq.json`:
```json
{
  "description": "Feed fetched FASTQ samplesheet into rnaseq",
  "upstream_params": {
    "nf_core_pipeline": "rnaseq"
  },
  "params": {
    "input": {
      "samplesheet": "samplesheet/samplesheet.csv",
      "provides": ["sample", "fastq_1", "fastq_2", "strandedness"]
    }
  }
}
```

### 2. Supported Source Mappings

| Source Type | Mapping Key | Description | Example |
|---|---|---|---|
| **Samplesheet** | `"samplesheet"` | Direct copy and transformation of an upstream samplesheet. `"provides"` asserts required columns. | `fetchngs` → `rnaseq` |
| **File** | `"file"` | Maps a single published output file to a downstream parameter. Globs must match exactly 1 file. | `rnaseq` → `differentialabundance` |
| **Build** | `"build"` | Synthesizes a new samplesheet from matching output files using `{placeholders}` for grouping. | `bamtofastq` → `rnaseq` |
| **Upstream Param** | `"upstream_param"` | Propagates a parameter value used in the upstream run to the downstream stage. | `rnaseq` `--gtf` → downstream `--gtf` |

### 3. Samplesheet Transformations
When mapping via `"samplesheet"`, transformations apply in strict sequential order:
- `"rename"`: `{"old_col": "new_col"}` — renames existing column headers.
- `"set"`: `{"column": "literal or {template}"}` — sets fixed values or templates per row.
- `"add_empty"`: `["column"]` — inserts missing columns with empty values.
- `"drop_rows_not_allowed"`: `["column"]` — filters out rows containing invalid enum values.
- `"require_values"`: `["column"]` — asserts that specified columns must not be empty.

### 4. Verify and Test Handoffs
```bash
# Verify static schema compatibility across both participating pipelines
python3 -m librarian.check_drift

# Rebuild catalog and test chaining specification in check-only mode
make build
nfclaw chain run spec.json --outdir /tmp/test-chain --check
```

---

## Testing Requirements & Quality Assurance

### Test-Driven Development (TDD)
We require regression tests for every bugfix:
1. Write a test in `tests/` that reproduces the bug or asserts the new behavior.
2. Verify that the test fails on existing code.
3. Implement the minimal necessary change to fix the issue.
4. Verify that the test passes.

### Running Test Commands
```bash
make test                      # Run full pytest test suite
pytest tests/test_chain.py     # Run focused test module
pytest -k "test_verify"        # Run tests matching an expression
```

### Makefile Targets Summary

| Target | Command | Description |
|---|---|---|
| `make add`   | `add_pipeline` | Print the `.gitmodules` entries and `git submodule add` commands for every pipeline in `sources.tsv` (it changes nothing itself). |
| `make build` | `write_skill --all && write_catalog` | Regenerate skills, references, and catalog files from pinned submodules. |
| `make update`| `update_pipelines && make build` | Discover newest release tags, bump submodules, and rebuild context. |
| `make check` | `check_drift && pytest` | Run schema drift verification followed by the complete pytest suite. |
| `make test`  | `pytest` | Execute all unit, regression, and integration tests. |

---

## Agent Guidance Sync

> [!IMPORTANT]
> **100% Byte-for-Byte Parity Required:**
> `AGENTS.md` and `CLAUDE.md` provide agent guidelines for Claude Code and other agentic runtimes. **They must remain 100% byte-identical.** The test `tests/test_agent_docs.py` enforces this equality. Whenever updating agent instructions, always mirror changes across both files.
