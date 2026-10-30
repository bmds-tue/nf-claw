# Changelog

User-visible changes to nf-claw, newest first. nf-claw has no tagged release yet; the draft release
notes for 1.0.0 (2026-10-22) describe the library as it stood then, and this file starts there.
Pipeline releases the maintenance workflows pin, bump or add are recorded in `sources.tsv`, the
generated `skill.md` files and the git history, not here. Audit records, with the evidence behind
each change, are in [`docs/audit/`](docs/audit/).

## Unreleased

### Added

- `nfclaw status --json` and `nfclaw chain status --json` print one machine-readable object (state,
  outcome, times, pids, logs, caveats, recorded error, last output, and the human report) with the
  same exit codes; the MCP `run_status` tool returns it as `run`.
- [`docs/replay.md`](docs/replay.md): what a provenance bundle carries, the replay guard, dependency
  stability, resume of changed local inputs, and what `nfclaw verify` and `nfclaw assess`
  establish.
- The website's search palette finds documentation sections by their headings, not only documents
  by title, and opens the page at the section; below the widest layout, a document opens with a
  folded table of contents.
- `nfclaw --version`, `nfclaw list <keywords>`, run manifests that record which nfclaw ran them, and
  a security policy (`SECURITY.md`) (#218).
- An accessibility check of every website page in the browser tests (#219).

### Changed

- `AGENTS.md`, which every agent session loads, is half its size (45 KB → 24 KB): it keeps every
  operating instruction and links the guarantees behind them to focused guides.
- Inputs and outputs are hashed several files at once (up to eight threads): one core hashed
  314 MB/s on the validation server, eight threads 7.7× faster on cached data.
- `nfclaw run` and `nfclaw chain run` refuse a Python without POSIX file locks (native Windows)
  instead of running without their writer locks; use WSL 2 there.
- Generated parameter tables write patterns, defaults and allowed values as code spans, so they
  render as the values nf-schema enforces (#219).

### Fixed

- A stopped run (Ctrl-C, `kill`, `--timeout`, MCP `cancel_job`) and a stopped replay remove the
  Docker/Podman task containers their processes started. Task wrappers killed while `docker stop`
  waited on a container's PID 1 had left every container behind, exited, and with a shorter shutdown
  grace still running.
- Handoffs no longer drop samples silently (bamtofastq → rnaseq single-end files, detaxizer → mag
  single-end sheets), and resuming a chain stage keeps its unchanged handoff and Nextflow cache
  (#218, #219).
- `nfclaw mcp` answers a message nested too deeply to parse instead of stopping (#219).
- Robustness of `nfclaw status` with unreadable logs and damaged records, the job supervisor and
  the container watcher (#218).

### Since the 1.0.0 draft notes

- #217 Post-merge fixes: palette race, kraken2 verify pairing, sarek 3.11.0 re-audit, docker probe
  limit.
- #216 Audit remediation: verified defect fixes, scientific output contracts (`nfclaw assess`),
  `verify --require-environment`, structured MCP parameters, `replay_run` and `read_artifact`,
  gated maintenance publication.
- #215 Stop repeating checks that Nextflow and nf-core already make.
- #213 fastqrepair: run the recorded corrections under the legacy config parser.
- #212 Remove duplicated files, code and documentation.
- #209, #211 MCP verified end to end in Claude Code, Codex and Antigravity; Antigravity loads every
  tool up front.
- #205 Report runs stubbed by a `--config`; stub-run seqsubmit's test without ENA.
- #203 Review of the whole codebase: three bug fixes, dead code removed, 100-column lint.
- #202 Next.js 15.5.28 for the website (GHSA-2464-fhr4-w9xw, GHSA-p3m5-59mp-jv5r).
- #200, #206, #207 Maintenance publication without organization PR permissions.
- #195 Name the release a failed chain stage ran; correct engine and network notes.
- Pipelines added or validated since: bacmodel, plasmodiumdrugres, provenancereport,
  stableexpression, magmap 1.3.1, rnasplice 2.0.0, rnastructurome 1.1.0, genomeassembler 2.0.1
  (#197, #198, #204, #208, #214).
