# Security policy

## Supported versions

| Version | Supported |
|---|---|
| `main` | Yes. Every fix lands here first. |
| The latest release (`v1.0.0`) | Yes. A security fix for it is released as a patch version (`v1.0.1`). |
| Earlier releases and other commits | No. |

## Reporting a vulnerability

Report a suspected vulnerability privately: on the repository's GitHub page open **Security →
Report a vulnerability** (GitHub private vulnerability reporting). Do not open a public issue,
pull request or discussion for it.

Include what reproduces it: the `nfclaw` command or MCP tool call, the pipeline and release, the
relevant parts of `<outdir>/provenance/` (`run.log`, `run_manifest.json`; remove credentials first)
and what happened compared with what you expected.

## Scope

nf-claw validates, launches and records pinned nf-core pipelines on the machine it runs on. Reports
that matter most here:

- input, path or write-boundary checks that let a run read or overwrite data it must not
  (`runner/input_safety.py`, `runner/replay_guard.py`);
- a provenance bundle or replay script (`commands.sh`) that can be made to run other code, or to
  skip its dependency and source checks;
- credentials or other sensitive environment values reaching provenance despite redaction;
- the MCP server (`nfclaw mcp`) or its detached jobs acting beyond what a call asked for;
- the maintenance workflows publishing changes that did not pass their gates.

A vulnerability in an nf-core pipeline, Nextflow, a container image or a scientific tool belongs
with that project. nf-claw runs pinned releases unmodified, apart from the recorded corrections in
[docs/source-corrections.md](docs/source-corrections.md).

## Fixes

Fixes are made on `main`. GitHub Actions are pinned by commit and kept current, together with the
website's npm dependencies, by Dependabot (`.github/dependabot.yml`); pipeline pins move through the
validated maintenance workflows described in [docs/updating.md](docs/updating.md).
