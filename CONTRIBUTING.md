# Contributing to nf-claw

Contributions are welcome: new pipelines and handoff rules, runner features and fixes, tests and
documentation. This page covers how to report a problem, set up a development checkout, add a
pipeline or a handoff rule, test, cut a release and write documentation.

---

## Navigation

[Principles](#principles) • [Reporting bugs](#reporting-bugs) • [Proposing a feature](#proposing-a-feature) • [Drift and upstream defects](#drift-and-upstream-defects) • [Development workflow](#development-workflow) • [Code conventions](#code-conventions) • [Adding a pipeline](#adding-a-pipeline) • [Adding a handoff rule](#adding-a-handoff-rule) • [Tests](#tests) • [Cutting a release](#cutting-a-release) • [Writing documentation](#writing-documentation)

---

## Principles

- **No pipeline-specific guesses.** The runner (`runner/`) and the maintenance code (`librarian/`)
  take their behaviour from the pinned schemas and the handoff rules, not from assumptions about a
  pipeline's name or columns. The few exceptions (`runner/fastqrepair_compat.py`,
  `runner/source_corrections.py`, `runner/demo_defaults.py`, `runner/path_roles.json`,
  `runner/input_roles.json`, `runner/param_roles.json`) need evidence from the pinned source and a
  check that they apply only to the release they were written for. Runtime corrections record that
  evidence for the replay. New compatibility code must be just as explicit.
- **Reproducible generated files.** Generating the Markdown and JSON files twice from the same
  commits must give identical bytes. Generated files contain no timestamps; commit hashes identify
  versions.
- **A test for every change.** Every fix and feature comes with a regression test: write the failing
  test first, make the smallest change that fixes it, and run `make test`.
- **No drift.** The committed `skill.md`, `reference.md` and `catalog.*` must always match the pinned
  submodules. The drift gate (`python3 -m librarian.check_drift`) rejects any difference.

The [README](README.md#layout) maps the repository, and [docs/architecture.md](docs/architecture.md)
explains how its parts (`pipelines/`, `handoffs/`, `runner/`, `librarian/`) fit together.

---

## Reporting bugs

Do not report a suspected security vulnerability in a public issue; report it privately as
[SECURITY.md](SECURITY.md) describes.

### Which kind of problem is it?

| Kind | Typical symptoms | Where it goes |
|---|---|---|
| Host or environment | Spaces in a path, missing Python packages, JVM socket timeouts on IPv6-only hosts, Docker permissions, running out of memory on a workstation. | Check [`docs/known-issues.md`](docs/known-issues.md). Fix it with flags (`--nxf-env`, `--limit-*`, `--config`) or in the system configuration. |
| Upstream pipeline defect | A task fails inside an nf-core process (`.command.err`), a container image is broken, test profiles conflict. | The pinned source is not edited. Document the workaround in `docs/known-issues.md` and report the bug to the pipeline's [nf-core repository](https://github.com/nf-core). |
| nf-claw defect | Preflight rejects a valid value, a lock never releases, a provenance bundle is broken, a chain fails. | Open an issue on [GitHub](https://github.com/bmds-tue/nf-claw/issues). |

### What to include

1. A title that names the part affected, e.g. `[runner]`, `[chain]` or `[librarian]`.
2. Your environment: `uname -a`, `python3 --version`, `nextflow -version`, and
   `docker --version` or `apptainer --version`.
3. How to reproduce it: the exact command, the pipeline and version (`nfclaw versions <name>`), and
   the smallest samplesheet or parameters that show the problem.
4. Logs: `<outdir>/provenance/logs/run.log` and `<outdir>/provenance/run_manifest.json`, and the
   relevant parts of `<outdir>/.nextflow.log` and the failing task's `.command.err`.

---

## Proposing a feature

Open an issue before a large pull request: describe what the feature does, the workflow it
supports and why. A feature should:

- work for any pipeline, reading scientific inputs and parameters through the upstream schemas and
  the handoff rules rather than assumptions about a pipeline's name;
- keep what an agent has to read short;
- give the same, checkable result on every machine.

Discuss where it fits (`runner/`, `librarian/` or the CLI) before implementing it, and include
tests and documentation with it.

---

## Drift and upstream defects

If `python3 -m librarian.check_drift` reports drift:

- **Missing or stale skills or catalog:** run `make build` to regenerate them from the pinned
  submodules.
- **Registrations disagree:** `sources.tsv`, `.gitmodules` and the directories in `pipelines/` must
  list the same pipelines with the same remote URLs.
- **A handoff rule no longer fits:** if an upstream pipeline renamed an output or a downstream
  pipeline changed its samplesheet schema, update `handoffs/<upstream>/<downstream>.json` to fit
  both.

Never edit files in `pipelines/<name>/upstream/`: the submodules point at upstream release commits
and stay as published. Work around an upstream defect with a narrow runtime mechanism
([recorded corrections](docs/source-corrections.md), a `-c` config) or document it in
[`docs/known-issues.md`](docs/known-issues.md).

---

## Development workflow

### Setup

Clone into a path without spaces (e.g. `/home/user/nf-claw`); on macOS, outside iCloud folders.

```bash
git clone https://github.com/<your-username>/nf-claw.git
cd nf-claw
git submodule update --init
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,yaml]"     # nfclaw with the test, lint and YAML extras
```

### Branches and commits

Work on a branch named after the change (`feat/memory-limit-flag`, `fix/lock-release`) and write
[Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` a new feature (`feat(runner): add a memory limit flag`)
- `fix:` a bug fix (`fix(chain): release the lock after a failed stage`)
- `docs:` documentation only
- `test:` tests only
- `chore:` maintenance, dependency updates and workflow changes

### Before opening a pull request

1. `make test` passes.
2. `python3 -m librarian.check_drift` reports no drift.
3. `ruff check .` passes, as in CI.
4. If you changed documentation or data files, `pytest tests/test_agent_docs.py` checks the links and
   anchors. Then build and test the website (Node.js 24, as in CI):
   ```bash
   npm --prefix website ci
   npm --prefix website run typecheck
   npm --prefix website run build
   npx --prefix website playwright install chromium   # once
   npm --prefix website run test:browser
   ```
   The browser tests run an axe-core accessibility check on every page. Each Markdown guide directly
   in `docs/` becomes a page (the audit records and evidence do not), and a skipped heading level or
   a table without a header row fails that check.
5. Note any user-visible change (a command, flag, output, documented behaviour or fix) in
   [`CHANGELOG.md`](CHANGELOG.md) under **Unreleased**, with the pull request's number.

### Pull requests

Describe the problem and how the change solves it, and link related issues (`Fixes #…`). Every
check on the pull request must pass: `tests` (pytest on Linux and macOS, `website`,
`nextflow-integration`), `drift-check` and CodeQL, plus the real-run validations that a change to
`runner/` or to their own files triggers (`demo-validation`, `fastqrepair-validation`;
`pipeline-execution` runs when its own workflow changes).

---

## Code conventions

- Python 3.11+ typing: `from __future__ import annotations`, `str | None`, `list[str]`,
  `dict[str, Any]`.
- Use `pathlib.Path` for paths, never string concatenation.
- Never run a shell string (`shell=True`); pass `subprocess.run` or `subprocess.Popen` an argument
  list, so nothing is split or interpreted by a shell.
- Background processes must handle `SIGINT` and `SIGTERM` and stop their child tasks.
- Path checks belong in their modules: repository, output and work paths in `runner/preflight.py`
  (`--allow-spaces` lifts the space check, line breaks are always refused), input file names and
  routes in `runner/inputs.py`, and the separation of a run's writes from its inputs in
  `runner/input_safety.py`.
- Lint with Ruff, configured in `pyproject.toml`: `ruff check .`. Do not add dependencies the code
  does not need.

---

## Adding a pipeline

Only DSL2 pipelines can be added: Nextflow removed DSL1 in 22.12.

### 1. Check the name

A name may contain only ASCII letters, digits, dots, hyphens and underscores, and must start and end
with a letter or digit:

```regex
^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$
```

| Name | Valid? | Why |
|---|---|---|
| `rnaseq` | yes | Letters only. |
| `viral-recon_v2` | yes | Letters, digits, a hyphen and an underscore. |
| `../evil` | no | A path traversal. |
| `.hidden` | no | Starts with a dot. |

### 2. Register it in `sources.tsv`

Add a tab-separated row:

```tsv
<name>	https://github.com/nf-core/<name>.git	latest-release
```

The remote must be the pipeline's nf-core repository. Use the `latest-release` policy; `hold` keeps a
pipeline at its current pin ([update policy](docs/updating.md#update-policy)).

### 3. Add and pin the submodule

```bash
git submodule add https://github.com/nf-core/<name>.git pipelines/<name>/upstream
git -C pipelines/<name>/upstream fetch --tags
git -C pipelines/<name>/upstream checkout tags/<X.Y.Z>   # a published release, e.g. 1.2.0
```

> [!NOTE]
> Pin a release tag, never `main`, `master` or `dev`. A submodule left on a branch makes the
> generated files record a branch commit instead of a release.

### 4. Generate its files

```bash
make build
```

This writes `pipelines/<name>/skill.md` and `pipelines/<name>/reference.md` and rebuilds
`catalog.json` and `catalog.md`.

### 5. Check

```bash
make check
```

The drift gate and the full test suite must both pass.

---

## Adding a handoff rule

Each rule is one file, `handoffs/<upstream>/<downstream>.json`.

Find the output paths in the upstream pipeline's `docs/output.md` and in the code that publishes
them, and the columns the downstream parameter needs in its input schema. Some parameters use an
auxiliary schema; when its contract disagrees with a bundled template, read the pinned parser. The
drift gate checks parameters and column compatibility; the published files themselves are checked
when the handoff runs. The rule format (source types, `build` templates and samplesheet
transformations, with `handoffs/fetchngs/rnaseq.json` as the example) is in
[docs/chaining.md](docs/chaining.md#handoff-rules).

```bash
python3 -m librarian.check_drift                         # the rule fits both pipelines' schemas
make build                                               # rebuild the catalog
nfclaw chain run spec.json --outdir /tmp/test-chain --check
```

---

## Tests

Every bug fix needs a regression test:

1. Write a test in `tests/` that reproduces the bug or describes the new behaviour.
2. Check that it fails on the current code.
3. Make the smallest change that fixes it.
4. Check that it passes.

```bash
make test                         # the full suite, one test at a time
pytest -n auto --dist worksteal   # the same suite on every core, as CI runs it
pytest tests/test_chain.py        # one module
pytest -k "test_verify"           # tests matching an expression
```

### Make targets

| Target | Runs | What it does |
|---|---|---|
| `make add` | `librarian.add_pipeline` | Prints the `.gitmodules` entries and `git submodule add` commands for every pipeline in `sources.tsv`; changes nothing itself. |
| `make build` | `librarian.write_skill --all`, then `librarian.write_catalog` | Regenerates the skills, references and catalogs from the pinned submodules. |
| `make update` | `librarian.update_pipelines`, then `make build` | Finds the newest release tags, bumps the submodules and regenerates the files. |
| `make check` | `librarian.check_drift`, then pytest | The drift gate, then the full test suite. |
| `make test` | pytest | The full test suite. |

---

## Cutting a release

A release is an annotated tag `vX.Y.Z` on `main`. It fixes the runner and every pipeline pin at that
commit, while `main` keeps moving as the maintenance workflows bump pins. Between releases, `main`
keeps the last release's version, and `nfclaw --version` adds the commit.

1. In one pull request, rename **Unreleased** in [`CHANGELOG.md`](CHANGELOG.md) to
   `## [X.Y.Z] — YYYY-MM-DD` under a new, empty **Unreleased**, and set `version` in
   `pyproject.toml` and `version` and `date-released` in [`CITATION.cff`](CITATION.cff) to match.
   `tests/test_version.py` checks that the three agree.
2. Merge it once every check is green, the macOS pytest lanes included: the `main` ruleset requires
   only some of them.
3. Tag the merge commit (`git tag -a vX.Y.Z -m "nf-claw X.Y.Z" <commit>`) and push the tag.
4. Publish the GitHub release for that tag: what it contains, how it was validated (link the audit
   record and [`docs/validation.md`](docs/validation.md)), its known limitations, and its
   `CHANGELOG.md` section.

---

## Writing documentation

Every behaviour is documented in one place; other documents link to it instead of repeating it.

| Content | Where it goes |
|---|---|
| What an agent or user must do to find, run, follow, replay or chain a pipeline | [`AGENTS.md`](AGENTS.md), kept short because every agent session loads it. `CLAUDE.md` imports it (`@AGENTS.md`), so edit only `AGENTS.md`. |
| The guarantees behind those steps, and their limits | The guide in `docs/` that covers them. A new `docs/*.md` also needs a row in the [README's guide list](README.md#documentation-guides) and an entry in [`llms.txt`](llms.txt). |
| A symptom and its fix | [`docs/known-issues.md`](docs/known-issues.md), under the section for that symptom. |
| Generated files (`skill.md`, `reference.md`, `catalog.*`) | Never by hand: change the generator in `librarian/` and run `make build`. |
| A user-visible change | [`CHANGELOG.md`](CHANGELOG.md), under **Unreleased**, with the pull request's number. |
| What an audit found, and the evidence | A new dated record in [`docs/audit/`](docs/audit/README.md). A record describes its own date: correct the guides, not old records. |

Conventions:

- Write plainly. Say what something does and what it does not do, in short sentences. Leave out
  promotional words, bold labels standing in for sentences, and decorative diagrams; a list or a
  table is enough.
- A guide starts with an H1 and a paragraph saying what it covers, then a `Navigation` line linking
  its main sections, and never skips a heading level. The site's accessibility check fails on a
  skipped level or a table without a header row.
- Give the version and date of a measurement ("measured at ampliseq 3.0.0 on 2026-10-15"). The daily
  updater moves pins without touching the hand-written guides, so write "pinned" only for a fact that
  stays true, and point to `skill.md` for the current pin.
- Say what was run and what it does not establish; a passing check is not biological validation.
- Test a claim about the code against the code. `tests/test_agent_docs.py` checks every relative link
  and anchor, that every guide is listed, that `docs/mcp.md` lists every MCP tool, and the `CLAUDE.md`
  import. Keep such tests independent of the pins and of the number of pipelines: the maintenance
  gate runs them on every candidate that changes those.
