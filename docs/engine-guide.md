# Pipeline versions, engine configuration and resources

## To run a specific (non-latest) version

The default is the repository's pinned release. Updates are checked before adoption, so a newer upstream release may not yet be pinned. To run another published release instead:

1. **List releases:** `nfclaw versions <name>` (the pinned latest is flagged).
2. **Read that version's docs:** `nfclaw show <name> --pipeline-version X.Y.Z` — it fetches the tag, materializes it under `pipelines/<name>/.versions/X.Y.Z/` (git-ignored), and prints the `skill.md` generated from *that* release's schema (a `reference.md` is written alongside it). The params, flags and validation all come from X.Y.Z, not from latest.
3. **Run it:**
   ```bash
   nfclaw run <name> --pipeline-version X.Y.Z --input samplesheet.csv --outdir results -profile docker
   ```

Only real release tags are accepted (`X.Y.Z`, or the `X.Y` of older nf-core releases such as fetchngs `1.9`; with or without a leading `v`) — plus `dev`, below; an unknown version fails fast and lists what is available. Provenance records the exact version that ran.

---

## To run unreleased development code (`dev`)

Every nf-core pipeline develops on a `dev` branch and releases from it, so `dev` holds the changes that are not in any release yet. To run it (the `nextflow run nf-core/<name> -r dev` equivalent):
```bash
nfclaw run <name> --pipeline-version dev --input samplesheet.csv --outdir results -profile docker
```
Every other flag works as for a release, e.g.:
```bash
nfclaw run fetchngs --pipeline-version dev --input ids.csv --outdir /path/to/out -profile binac2 --nxf-ver 25.10.4
```

- **Commit anchoring:** `dev` moves, so each run resolves it to the branch's **current head commit** and materializes that commit under `pipelines/<name>/.versions/dev-<commit12>/` (git-ignored, one immutable tree per commit, so a replay or a concurrent run never sees the code change). The run prints a warning naming the commit; provenance records `version: dev` plus that exact commit, and `commands.sh` replays it.
- **Documentation:** Read its docs first — params can differ from the release: `nfclaw show <name> --pipeline-version dev` prints the `skill.md` generated from that commit (`reference.md` is written beside it).
- **Listing:** `nfclaw versions <name>` lists `dev` (with its head commit) after the releases.
- **Offline behavior:** Offline, nfclaw falls back to the last `dev` head it fetched and says so; a pipeline with no `dev` branch fails fast. `--resume` warns when `dev` moved; the [analysis identity guard](resume-policy.md) preserves the previous run and starts a fresh cache session for the new revision.

Prefer a release for results you need to reproduce from a version number; use `dev` for fixes or features that are not released yet.

---

## Tuning the Nextflow engine / environment

`nfclaw run` inherits your shell environment and passes it through to Nextflow. Two run flags make the engine and its runtime explicit and reproducible (both are recorded in `<outdir>/provenance/`):

- **`--nxf-ver X.Y.Z`** — pin the Nextflow engine for this run (sets `NXF_VER`). Use it when a newer Nextflow breaks an older pipeline release (e.g. a config-parser change in a new Nextflow major), or to reproduce a prior run exactly. nfclaw judges the version requirement against this pin.
- **`--nxf-env KEY=VALUE`** — set an `NXF_*` variable for this run (repeatable). Common fixes:
  - IPv6-only host where the JVM can't reach GitHub for remote configs:
    `--nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true`
  - skip remote config fetches entirely:
    `--nxf-env NXF_OFFLINE=true`
- **`--config PATH` (or `-c`, repeatable)** — pass an extra Nextflow config straight through (`-c`), e.g. a docker host-network config (`docker { runOptions = "--network host" }`) or custom resources.

---

## Running on a machine smaller than the pipeline assumes

nf-core commonly sizes processes from labels in the pipeline's `conf/base.config`, tuned for a server: one step can request far more memory than a workstation has (`Process requirement exceeds available memory`), and retry rules can increase requests. Many bundled `test` profiles set small ceilings; real runs often need an explicit one. Set one:
```bash
nfclaw run <name> ... --limit-cpus 4 --limit-memory 15.GB
```
`--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes.

These become Nextflow's `process.resourceLimits` — the ceiling nf-core documents — applied to every process and every retry, so one flag covers whatever the pipeline asks for next. `resourceLimits` needs Nextflow 24.04.0 or newer: older engines accept it silently and apply no ceiling, so `nfclaw run` refuses `--limit-*` when the run would use one or its engine version cannot be identified (pin a supported concrete engine with `--nxf-ver`, or use the release's own `--max-*` parameters where it declares them). Do not chase this with `withName:` overrides: those size only selected processes. A constant override also applies to that process's retries, but expressions using `task.attempt` can grow and every other process still needs coverage. The generated config is written to `<outdir>/provenance/resource_limits.config` and replayed by `commands.sh`.

Any other environment (proxies, `JAVA_HOME`, …) is inherited from your shell unchanged. Each run launches Nextflow from its `--outdir`, so its `.nextflow/` history is isolated and `--resume` resumes that run (use a distinct `--outdir` per pipeline).

Task work files default to the shared `<repo>/work/` directory. Set
`--nxf-env NXF_WORK=/path/to/work` to choose another location; relative values resolve
against the caller's working directory. Preserve the work files needed for resume
and any result symlinks that point into them.

If a pipeline's `upstream/` is empty, initialise it first:
```bash
git submodule update --init pipelines/<name>/upstream
```
`nfclaw run` refuses a pinned `upstream/` that is not at the commit its `skill.md` documents (e.g. after a `git pull` without a submodule update, which would otherwise run the old release under the new release's docs) or that has local edits to tracked files: restore it with `git submodule update --force pipelines/<name>/upstream`, or pass `--pipeline-version` to run another release deliberately.

---

