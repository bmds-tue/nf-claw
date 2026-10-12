# Known Issues & Troubleshooting

Configured Nextflow engine caches and temporary directories must remain outside declared input
directories. The launcher can create framework and Java-version cache entries even while probing
its version. Boundary checks cover `NXF_HOME`, `NXF_DIST`, `NXF_TEMP` and `CAPSULE_CACHE_DIR`
before metadata probes, including inherited settings and relative paths.

Most run-time failures fall into two categories: **environment** (host, network, or path issues — fixable via `nfclaw run` flags or environment adjustments) and **upstream pipeline defects** (bugs in a specific pinned nf-core release). nf-claw keeps pinned pipeline source trees **unmodified**. Upstream defects, recorded runtime corrections and their validation limits are documented here.

---

### Navigation

[Host Environment & Setup](#environment) • [Benign Nextflow Warnings](#warnings-a-run-prints-that-are-not-faults) • [Upstream Pipeline Defects](#upstream-pipeline-bugs-documented-not-patched) • [Pipeline Run Notes](#pipeline-specific-run-notes) • [Chaining Test Data Notes](#chains-what-a-demo-true-stage-hands-over)

---

> [!NOTE]
> **Parameter Syntax & Normalization:**
> `nfclaw run` normalizes dashes and underscores interchangeably (e.g. `--skip-busco` and `--skip_busco` are equivalent, whereas raw Nextflow requires the pipeline's exact spelling).
>
> **Values Starting with a Dash:** When passing parameter values that begin with a hyphen (such as tool pass-through flags like rnaseq's `--extra_star_align_args`): use the `=` syntax `--extra_star_align_args='--outFilterMismatchNmax 5'` or pass them via `--params-file`. The two-token syntax `--extra_star_align_args '--outFilterMismatchNmax 5'` is rejected fast with an `unknown parameter` error to prevent unintended flag misinterpretation.

When a run fails, nfclaw's error diagnostic quotes Nextflow's own error report (including the full `Caused by:` chain from `.nextflow.log` if hidden from the console) and references absolute paths to:
1. The unified launch log (`<outdir>/provenance/logs/run.log`), ending with the terminal outcome line.
2. Nextflow's internal engine log (`<outdir>/.nextflow.log`).
3. The failing task's `.command.err` (accompanied by `.command.log` and `.command.sh`).

---

## Environment

### `nfclaw` aborts with `ModuleNotFoundError: No module named 'runner'`
- **Symptom:** The installed `nfclaw` command fails immediately — before doing any work — with `ModuleNotFoundError: No module named 'runner'` (or `'librarian'`).
- **Why:** `nfclaw` is a console script that imports the repo's `runner` package, which relies on the `pip install -e .` editable install being active in the **same** Python the command runs under. Two things break that import:
  1. **A space in the install path:** Python's `site` module does not execute an editable install's path hook when the virtualenv/site-packages path contains a space, so `runner` never lands on `sys.path` (this repo already requires a space-free path for *runs*; the same applies to the *install*).
  2. **Python interpreter mismatch:** The editable install was performed with a **different Python** than the one in `nfclaw`'s shebang (e.g. a `--user` install whose site-packages is not on that interpreter's path). This occurs before nfclaw code executes, so it cannot be caught by runtime space checks.
- **Fix:**
  - Use a **space-free path** for both the repo and the virtualenv (on macOS also avoid iCloud paths), and run `pip install -e .` inside the virtualenv you actually use.
  - Or skip the console script and use the **no-install equivalent from the repo root**: `python3 -m runner <cmd>` (maintenance runs the same way: `make <target>`, or `python3 -m librarian.<module>` — e.g. `python3 -m librarian.write_skill --all`). It needs no install — the repo root is already on `sys.path` — and resolves the pinned pipelines correctly.

### Path contains a space — checked before the run, fails fast
- **Symptom:** A tool fails with a split path (e.g. `cannot create /vol/draft 2/...: Permission denied`, `Got unexpected extra argument(s)`, or a module building shell commands breaks).
- **Why:** Many bioinformatics tools (and Nextflow's internal work directory) build shell commands without quoting paths, causing spaces to split arguments. This affects **macOS and Linux** alike.
- **How nfclaw handles it:** `nfclaw run` checks the **repo path, the Nextflow work directory and `--outdir`** *before* launching and **fails fast**, naming exactly which path has the space — a deterministic check, no guessing.
- **Fix:**
  - Move the repository to a space-free path (strongly recommended).
  - Or set a space-free work directory: `--nxf-env NXF_WORK=/a/space-free/dir`, and use a space-free `--outdir`.
  - Or, if you know your pipeline tolerates spaces, pass `--allow-spaces` to bypass the preflight check.

### IPv6-only host — JVM can't reach GitHub
- **Symptom:** `java.net.SocketException: Network is unreachable` while Nextflow downloads `https://raw.githubusercontent.com/nf-core/configs/master/nfcore_custom.config`.
- **Why:** The host has no default IPv4 route; the JVM prefers IPv4 by default and never attempts IPv6.
- **Fix:** `--nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true`. To skip remote config fetches entirely (offline): `--nxf-env NXF_OFFLINE=true`.
- **Dual Requirement on IPv6 Hosts:** On an IPv6-only host you usually need BOTH this *and* the Docker host-network config (next section) together: the JVM flag fixes Nextflow's own GitHub download, while host-network fixes DNS *inside* containers — neither alone is sufficient:
  ```bash
  nfclaw run <name> --nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true \
                    --config host-net.config …
  ```

### No network at run time — a tool downloads a database
- **Symptom:** A step (e.g. BUSCO) hangs then fails trying to fetch a database it requires.
- **Fix:** Disable that step via parameters. Booleans work from the CLI, e.g. `--skip-busco true` (or put `{"skip_busco": true}` in a JSON file and pass it as `--params-file params.json`).

### A process requests more memory than the host has — aborts before any work
- **Symptom:** A run aborts at scheduling time because a single step requests more RAM than the machine has, e.g. `Process requirement exceeds available memory -- req: 80 GB; avail: 62.8 GB`. Seen with `detaxizer` 1.3.0 run with `--classification_bbduk`: its `BBMAP_BBDUK` step carries nf-core's `process_high` label, which `conf/base.config` sizes at `80.GB * task.attempt` — more than a typical workstation or small VM has.
- **Why:** An nf-core `base.config` sizes each process by a resource *label* (`process_low/medium/high/high_memory`) tuned for an HPC cluster; one high-memory step can exceed a small host's physical RAM, and Nextflow refuses to schedule a task it knows cannot fit.
- **Fix:** Put a ceiling on the whole run with `--limit-cpus` / `--limit-memory`, sized to the host machine:
  ```bash
  nfclaw run rnaseq --input ss.csv --outdir results -profile docker \
    --limit-cpus 4 --limit-memory 15.GB
  ```
  `--limit-time DURATION` also caps how long any one task may run: a task that needs longer is stopped, and so is every retry, so set it only as a deliberate ceiling, never as a guess at how long the analysis takes.
  nfclaw writes these as Nextflow's [`process.resourceLimits`](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources) and passes the generated config with `-c` — the mechanism nf-core prescribes, and the same one its own `test` profiles use (which is why `--demo` never hits this and a real run does). The ceiling applies to **every** process *and every retry*, so one flag covers whatever the pipeline asks for next; the generated config is kept in `<outdir>/provenance/resource_limits.config`, so `commands.sh` replays the run under the same ceiling.

  Do **not** cap by naming processes (`withName: 'STAR_GENOMEGENERATE' { memory = '15.GB' }`) unless you mean to re-size that one step: `withName` changes a single process's *initial* request, so you must name every step that might exceed the host — miss one and the run dies there instead (`STAR_GENOMEGENERATE`, then `BBMAP_BBSPLIT`, then the next). It also does not cap the retry, which asks for more. Use `withName` (via `--config`) only to tune one specific step, e.g. giving a tool *less* than its label implies:
  ```groovy
  // tune-one-step.config
  process {
      withName: 'BBMAP_BBDUK' { memory = '12.GB' }
  }
  ```
  (Size any cap to the host *and* to what the tool actually needs — too low and the step itself fails or is OOM-killed.)

### Nextflow too new for an older release
- **Symptom:** `Unexpected input: ':'`, `Unexpected token`, `Invalid include source`, or `import ...` rejected — on Nextflow **26.04+**, whose default strict parser rejects older Groovy config syntax (typed declarations, functions with params, `manifest.*`/`validation.*` accessed at parse time, `import` in `.nf`). Many older releases hit this.
- **Fix:** Pin an engine the release was written for: `--nxf-ver 25.10.2` (must still satisfy the pipeline's declared `nextflowVersion` minimum). If you hit it on most pipelines, set it once for the shell: `export NXF_VER=25.10.2` (nfclaw passes it through). See [`compatibility.md`](compatibility.md).
  Confirmed-affected releases that **do** run with `--nxf-ver 25.10.2` include `epitopeprediction`, `hgtseq`, `callingcards`, `coproid`, `denovotranscript` 1.2.1, `chipseq` 2.1.0, `atacseq` 2.1.2, `circdna` 1.1.0, `detaxizer` 1.3.0, `cutandrun` 3.2.2 and `marsseq` 1.0.3, plus the earlier, non-pinned releases `fastqrepair` 1.0.0 and `genomeassembler` 1.1.0 (`--pipeline-version`). Newer releases — including the pinned `fastqrepair` 1.1.1, `genomeassembler` 2.0.0, `fetchngs` 1.13.0, `sarek` 3.10.0 and `scrnaseq` 4.2.0 — declare `!>=25.10.4`, so use `--nxf-ver 25.10.4` to avoid Nextflow 26 strict parser failures on them.

  Examples of what NF 26 rejects:
  - chipseq's **and** marsseq's `def check_max(obj, type)` in `nextflow.config` (marsseq 1.0.3 declares only `!>=23.04.0`, so unpinned it parses under NF 26 and fails at launch with a `nextflow.cli.Launcher` error — `--nxf-ver 25.10.2` fixes it; note its `test` profile also sets `genome = 'mm10'`, which expects prebuilt local references; its configuration maps that key to GRCm39/M27, not AWS iGenomes).
  - scrnaseq 4.1.0's `Invalid include source: conf/test_multiome.config` (the `test_multiome` profile `includeConfig`s a file not committed at the tag — NF 26 validates it at parse time even though the profile is unused, while the legacy parser skips it and the `--demo` run completes).
  - cutandrun 3.2.2's `Cannot invoke method optional() on null object`, from deprecated output syntax `emit: html optional true` in `modules/local/for_patch/trimgalore/main.nf` (sibling modules already use current `emit: …, optional: true`).
- **Exception — some releases need a _newer_ engine:** `funcscan` 4.0.0 and `lsmquant` 1.0.3 declare `nextflowVersion = '!>=25.10.4'`, so `--nxf-ver 25.10.2` is rejected at the version gate (the symptom can read as a parameter/validation failure); use `--nxf-ver 25.10.4`. (`bactmap` 1.0.0 hits the parser issue *and* further bugs and can't run in demo here — see the upstream table).
- **In a chain (`nfclaw chain run`):** Pin the engine on that stage only — `"nxf_ver": "25.10.4"` in its spec entry — since other stages may need a newer one (fetchngs 1.13.0 requires `>=25.10.4`, mag 5.5.0 `>=26.04.0`). The chain parses every stage's config with its own engine (`nextflow config`) before the first stage launches, so this fails up front, not after the stages before it have run. Seen in chains on Nextflow 26.04.3: `atacseq` 2.1.2 (`def check_max`) and `viralrecon` 3.0.0 (`Invalid include source: conf/test_full_sispa.config`, a profile file missing at the pinned commit) — both parse with `"nxf_ver": "25.10.4"`.

### BUSCO finishes, then the task hangs until its time limit (IPv6-only host)
- **Symptom:** A `BUSCO_BUSCO` task (mag, and any pipeline running BUSCO 6) is killed at its time limit — Nextflow reports `process hasn't exited` — although its `.command.log` shows BUSCO's results and "Total running time: 6 seconds" hours earlier.
- **Why:** BUSCO 6 sends anonymous run statistics when it ends ("You may opt out with --opt-out-run-stats"); on a host without IPv4 that upload never completes, and the task waits on it.
- **Fix:** Opt out through a config given with `--config` (in a chain: the stage's `"config"`):
  ```groovy
  process {
      withName: 'BUSCO_BUSCO' {
          ext.args = { (params.busco_db ? '--offline ' : '') + '--opt-out-run-stats' }
      }
  }
  ```
  (mag's own `ext.args` is `--offline` when `--busco_db` is given; the closure preserves it.)

### Docker bridge network has no DNS (IPv6-only host)
- **Symptom:** Containers cannot resolve hostnames; downloads inside a container fail even though the host has connectivity. Docker's default bridge uses IPv4 DNS `8.8.8.8`, unreachable on an IPv6-only host.
- **Fix:** Give containers the host network via a config file passed with `--config`. `docker.runOptions` is a single string that a `--config` **replaces** (it does not merge with the pipeline's value), so preserve nf-core's default user mapping in the same string — otherwise the container reverts to running as root and outputs become root-owned:
  ```groovy
  // host-net.config — host network + nf-core's default user mapping
  docker { runOptions = "--network host -u $(id -u):$(id -g)" }
  ```
  Run with `nfclaw run <name> --config host-net.config …`.

### A container creates root-owned files that block publishing
- **Symptom:** A step writes a file/dir owned by root with restrictive permissions, and Nextflow — running as your user — cannot read or publish it. Examples: `CUSTOM_SRATOOLSNCBISETTINGS` and `macrel` (mode `600`), or STAR in `rnaseq` (`_STARgenome/` / `_STARpass1/` as `drwx------`, failing with `AccessDeniedException`).
- **Why:** nf-core's `docker` profile maps your host user into the container (`docker.runOptions = '-u $(id -u):$(id -g)'`). Any `--config` that sets `docker.runOptions` **replaces** this value rather than adding to it, causing containers to fall back to root.
- **Fix:** Keep the user mapping folded into the same `runOptions` string in your `--config`:
  ```groovy
  // run-as-user.config
  docker { runOptions = "-u $(id -u):$(id -g)" }
  ```
  If your shell trips over substitution (`syntax error near unexpected token ')'`), hardcode numeric ids (`id -u` / `id -g`): `docker { runOptions = "-u 1000:1000" }`.

### `--resume` resumed the wrong session
- **Status: Fixed.** `nfclaw run` launches Nextflow **from the `--outdir`**, so each run owns its own `.nextflow/` history and cache. `--resume` resumes *this* outdir's session — it can no longer pick up another pipeline's run. Always use a distinct `--outdir` per pipeline.

### Directory-consuming tasks are incorrectly cached after `--resume`
- **Status: Fixed for explicitly declared local input directories.** Nextflow keys a directory input on the directory's path, size and timestamp. Nextflow 25.10.4 and 26.04.0 reuse a cached directory-consuming task after an empty directory is renamed, or after a file in a subdirectory is edited in place (verified: the resumed task republished the old bytes), while the root size and timestamp remain unchanged. File checksums cannot detect the rename, and the namespace cannot detect the edit, so nfclaw checks both.
- **Behavior:** nfclaw records the full directory namespace and the SHA-256 of every file beneath an input directory before launch. Unchanged namespace and content preserve normal resume caching; a changed namespace, changed file content or an unavailable previous inventory preserves the previous run in a sibling `<outdir>.previous-<id>` archive, starts a fresh cache session, and recomputes all tasks. This avoids stale publications and fixed report filename conflicts; prior logs are retained and copied forward. Active engine database locks and dependencies overlapping the run directory block archiving. This also applies when the new launch disables provenance. Remote and indirectly configured directory inputs are outside this preflight's scope.
- **Validation:** Real tasks enumerated `sample_A` before the change and `sample_B` after resume on both engines, with the root timestamp restored. Unchanged resumes reused the cached task. Sample-specific output files proved that old publications stayed in the archive, while a fixed trace filename was successfully regenerated. Standalone replay refused the changed inventory before launching Nextflow. Editing a nested file to same-size content with both directory timestamps restored made the resumed run recompute and publish the new bytes on both engines, and an unchanged follow-up resume reused the cache.

### `--resume` fails with "Unable to acquire lock on session …"
- **Symptom:** After a run was interrupted (killed/timed out), re-running with `--resume` fails to acquire the session lock.
- **Why:** A hard kill leaves Nextflow's session lock behind; Nextflow refuses to resume because it cannot determine whether the lock is stale or held by a live process.
- **Fix:** Ensure no Nextflow process for that `--outdir` is active, remove the stale lock under `<outdir>/.nextflow/cache/*/LOCK` (or start fresh in a new `--outdir`), and re-run with `--resume`.

### A run in the background: is it still going, and how did it end?
- **Symptom:** A run started with `nohup nfclaw run … &` — its `run.log` has no terminal line, or you need its outcome without opening the file.
- **Fix:** `nfclaw status <outdir>` answers from the log alone: `running (nfclaw pid … on host …)` with the last output; the outcome it ended with and the recorded error; `refused before launch`; or `stopped without an outcome`. Re-run the command with `--resume`. Stop a background run cleanly with `kill <nfclaw pid>` — never `kill -9` — so logs and provenance are finalized.

### Launching several pipelines in parallel
- **Status: Fixed.** Starting 2+ pipelines simultaneously whose submodules were uninitialised previously raced on `.git/config`. `nfclaw run` serializes submodule initialization with a per-repo file lock, ensuring concurrent first-time runs initialize submodules cleanly.

### Replaying a run: `provenance/commands.sh` reproduces into a *fresh* directory
- **Status: Fixed.** The replay script reproduces the run into a **fresh** directory, defaulting to `<outdir>.replay`:
  ```bash
  ./results/provenance/commands.sh                 # → results.replay/
  ./results/provenance/commands.sh /tmp/check-it   # or name the target yourself
  ```
  It refuses a target that already holds files, launches Nextflow from the target directory, and passes `--outdir "$target"`.

  Stop it with `kill <replay pid>`. New bundles run the command in its own process
  group, allow ten seconds for shutdown, then kill surviving group members before
  closing the log and releasing the writer lock. A stopped replay returns a
  nonzero exit status even if the command handles the signal with exit zero.
  Tasks or containers detached from that group still require executor cleanup.

### `--check` never writes into `--outdir`
- **Status: Fixed.** `--check` validates parameters and prints the command without launching, staging parameters in a temporary directory and leaving `--outdir` untouched.

### A replay can change bytes and timestamped metadata filenames
Some outputs embed dates or durations: execution reports, timelines, gzip headers,
FastQC ZIP entries and MultiQC HTML can differ between runs. A changed checksum
does not identify the cause; inspect scientific results with a format-aware comparison.
Matching file inventories alone does not establish analytical agreement. Check both with:
```bash
nfclaw verify results.replay --against results
```
It hashes the replay's live files and compares them with the original recorded checksums
**by path**, reporting `identical` / `changed` / `missing` / `extra` / `renamed`. Missing or extra
files or directories fail the structural check; add `--strict` to fail on changed file bytes or recorded link identities as well. Link targets can differ when independent executions use different task work directories; inspect those differences explicitly.

nfclaw pins the schema's `trace_report_suffix` where available, but some upstream
code generates other filenames directly from the clock. For example, demo 1.2.0's
`dumpParametersToJSON()` independently names `pipeline_info/params_<timestamp>.json`.
Every faithful replay therefore has a differently named file, so comparing exact paths
failed every replay of the modern template (demo 1.2.0, ampliseq 3.0.0) and the failure
no longer distinguished a broken replay. `nfclaw verify` pairs these run-metadata names
(and the execution report/timeline/trace/DAG of releases without `trace_report_suffix`)
one to one, lists each pair under `renamed` as `original -> replay`, and compares its
bytes like any other file. The pairing is explicit, never silent; any other dated path —
possibly a scientific result — keeps its exact identity. A resumed run can retain reports
from earlier attempts: several candidates for one name are never paired by guess and stay
missing or extra for explicit classification.

**Do not diff the two `outputs.sha256` files directly.** Each line is `hash  path`, so a file whose
content merely changed has a different line in each bundle and shows up as *both* "missing" and
"extra" — one changed report is counted twice, and a run whose reports simply carry a new timestamp
reads as hundreds of missing and extra files. That is an artefact of the comparison, not a defect in
the replay; `nfclaw verify` keys on the path precisely to separate the two questions.

### Chains: `[handoff_failed]` — the next stage's input could not be prepared
- **Symptom:** `nfclaw chain run` stops after a stage succeeded, with `[handoff_failed]` and the chain log ending `failed at stage NN-<stage>: handoff`.
- **Why:** The handoff rule expected an output the upstream run did not produce (or produced multiple matching files), or the generated samplesheet failed downstream schema checks.
- **Fix:** Inspect the snapshot in `<outdir>/chain/handoffs/`; provide parameters directly in stage `params`, supply an inline handoff, and resume: `nfclaw chain run spec.json --outdir DIR --resume`.

### Concurrency: `another nfclaw run is active in …`
- **Symptom:** `nfclaw run` aborts immediately with `[environment] another nfclaw run is active in <outdir>`.
- **Why:** To prevent session corruption, `runner/locking.py` holds an exclusive non-blocking sibling flock on `.{outdir.name}.nfclaw.lock` throughout workflow execution.
- **Fix:** Wait for the active run to finish (`nfclaw status <outdir>`) or terminate it (`kill <pid>`) before launching or resuming in that directory.

### Chains: `another nfclaw chain is running in …`
- **Symptom:** `nfclaw chain` aborts indicating another chain process is running.
- **Why:** Only one chain process is permitted per `--outdir` to prevent race conditions on shared stage state (`chain/.lock`).
- **Fix:** Wait for the active chain to complete (`tail -n 1 <outdir>/chain/logs/chain.log`) or stop it with `kill <pid>`.

### Replay dependency guard failures (`provenance/replay_guard.py`)
- **Symptom:** Running `<outdir>/provenance/commands.sh` aborts with `nfclaw replay: dependency check failed: ...` before Nextflow is launched.
- **Why:** `commands.sh` executes `replay_guard.py` to ensure local input files (including paths referenced in samplesheets), external Nextflow configs (`-c`), and tracked pipeline source commits match their recorded SHA-256 manifests. New bundles also check directory namespaces, empty directories, entry types and symlink identities against `inputs.inventory.json` and `configs.inventory.json`. A checksum-only prelaunch snapshot cannot certify the original directory namespace and is refused.
- **Fix:** Restore the original input files or external configs to match the recorded checksums in `<outdir>/provenance/inputs.sha256` and `configs.sha256`. If intentional changes were made, launch a new run into a new `--outdir` instead of replaying.

### Replay refuses an unobserved engine or malformed environment names
- **Why:** New bundles pin replays to the engine version observed in the executed
  Nextflow banner, even when the original environment selected `latest` or another
  moving selector. If no version was observed and no concrete `NXF_VER` was set,
  the bundle cannot select that engine faithfully. Environment names that cannot
  be represented as shell identifiers are also refused.
- **Fix:** Start a fresh run with a valid environment and an explicit `--nxf-ver`
  from the pinned pipeline's documented engine requirement. Do not guess which
  engine an earlier unobserved run used. Private URI credentials are omitted from
  exported replay values; supply any needed credentials through your environment.

---

### An explicit remote input has an unsafe staged filename

Nextflow can retain literal shell characters in a remote basename. A task deriving a
prefix from that name can interpolate shell syntax even when its input path object is
escaped. For example, a local HTTP fixture named `reads$(id).txt` produced
`printf '%s\n' reads$(id) > name.txt` on Nextflow 25.10.4 and executed command
substitution. nfclaw now refuses explicit unsafe remote names in path parameters and
CSV/TSV or flat JSON/YAML path fields before launching. Use a safely named remote
object or download the data into a safely named local file; sample identities are
preserved.

Percent escapes remain literal in the staged name and are not decoded by this guard.
HTTP query suffixes are excluded from the filename check so signed URLs remain
usable. A standalone HTTP fragment remains in the staged name and is checked. S3
paths retain both query and fragment characters in their object keys.
The local HTTP integration oracle checks actual staged names and bytes on Nextflow
25.10.4 and 26.04.0 without interpolating their names into executable script text.
Local directory inputs and directory glob matches are inspected recursively, including
empty subdirectories and resolved symlink target names. Broken members, unreadable
subtrees and directory cycles are refused before launch. Parent names outside the
explicit directory are not staged names and retain their separate path contract.

Remote file contents, remote glob matches and values supplied only by configs/profiles
are outside this explicit-value preflight.

### A valid input symlink lost its filename and format suffix
- **Status: Fixed.** Resolving a whole input path replaced `sheet.csv` with its target
  `stored.data`. The CSV parameter constraint then rejected it; format-dependent
  samplesheet parsing and filename-derived identities could also use the target name.
  Local path parameters now resolve their parent directory while retaining the supplied
  basename. Alias and target safety checks still apply. Replay records and checks the
  alias identity, even when a retargeted link has identical bytes. Reference handoffs
  preserve the alias too; chain status can still verify older bundles that explicitly
  recorded the resolved target as their consumed parameter.

### Output or work directories contaminated a directory input
- **Status: Fixed.** A real Nextflow 25.10.4 task consuming a directory observed
  `.analysis.nfclaw.lock` and `analysis` alongside the original `index.bin` when its
  `--outdir` was a child of that input. The sibling lock was created before input
  validation, and the output tree appeared after the prelaunch snapshot.
  Dependency separation now precedes lock acquisition and all generated run files.
  Checks cover explicit directory inputs, samplesheet data paths, directory glob
  matches, nested aliases, code/configuration dependencies, generated-file redirects,
  the configured Nextflow log, work directories and chain records. A boundary refusal
  does not append to an existing run log inside the input. Refusal logging for other
  errors acquires the writer lock so it cannot forge the outcome of a live run.
  Real-engine tests on 25.10.4 and 26.04.0 verify unchanged input bytes and directory
  entries, then execute and replay a separate safe output location with literal
  filename and content oracles. Previously computed task files beneath a shared
  work tree remain legitimate downstream inputs; consuming the whole work tree is refused.

---

## Warnings a run prints that are not faults

These messages originate in upstream configurations, plugins or tools. Some have
been observed during successful runs, but a warning or an exit-zero process alone
does not establish analytical correctness. Interpret each message in the context
of its documented version and cause. A replay can reproduce the same message;
cache, network and environment changes can also change what it prints.

### `WARN: Unrecognized config option 'validation.defaultIgnoreParams'` / `'validation.monochromeLogs'`
- **Cause:** Running a Nextflow engine *newer* than the release targets. Harmless and avoidable.

  | Nextflow Version | Output / Result |
  |---|---|
  | **25.10.4** (declared minimum `!>=25.10.4`) | **No warnings emitted** |
  | **26.04.6** | `WARN: Unrecognized config option 'validation.defaultIgnoreParams'` + `'validation.monochromeLogs'` |

  Both options are set by the pipeline's own `nextflow.config` inside the `validation` scope contributed by `nf-schema`. Nextflow 26's strict parser checks config options before plugins load; because nf-schema registers no `ConfigScope` for `validation`, the parser warns. Tracked upstream in [nextflow-io/nf-schema#117](https://github.com/nextflow-io/nf-schema/issues/117).
- **Fix:** Run the engine the release was authored for:
  ```bash
  nfclaw run scrnaseq --input ss.csv --outdir results -profile docker --nxf-ver 25.10.4
  ```

### `WARN: Could not load / include the nf-core institutional config` (a host without network access)
- **Cause:** Nextflow could not fetch nf-core's optional remote institutional configuration from GitHub at parse time. sarek 3.10.0 (and 3.9.0) includes it dynamically in `nextflow.config` (line 325 at 3.10.0):
  ```groovy
  includeConfig params.custom_config_base && (!System.getenv('NXF_OFFLINE') || !params.custom_config_base.startsWith('http'))
      ? "${params.custom_config_base}/nfcore_custom.config" : "/dev/null"
  ```
  On air-gapped or IPv6-only hosts unable to reach GitHub, the remote file cannot be resolved. The configuration is purely optional tuning.
- **Fix:** Set `NXF_OFFLINE=true` to skip remote includes cleanly:
  ```bash
  nfclaw run sarek --input ss.csv --outdir results -profile docker --nxf-env NXF_OFFLINE=true
  ```

### `WARN: The following invalid input values have been detected: * --igenomes_base: …` (an institutional profile)
- **Cause:** Set by an institutional profile, not by the pipeline or nf-claw. For example, `binac2.config` sets `params.igenomes_base` for all pipelines; pipelines that do not resolve reference genomes (such as `fetchngs`) do not declare this parameter, causing nf-schema to flag it. It is benign and does not affect analysis.

### `ERROR org.pf4j.AbstractExtensionFinder - Different class loaders`
- **Cause:** A plugin-cache artifact on the host where pf4j discovers the same extension point loaded by two class loaders.
- **Fix:** Clear the plugin cache and re-pin the declared engine:
  ```bash
  rm -rf "${NXF_HOME:-$HOME/.nextflow}/plugins"
  ```

### `WARN: nf-core pipelines do not accept positional arguments. The positional argument \`nextflow\` has been detected.`
- **Cause:** A known defect in the pinned `nf-core-utils@0.4.0` plugin used by sarek 3.10.0 (and 3.9.0). The plugin's validator splits `session.commandLine` on whitespace and incorrectly inspects the launcher binary name `nextflow`. It is benign (`log.warn`, exit 0) and does not affect execution.

### `WARN: --validationSchemaIgnoreParams: genomes` is not a valid parameter (scrnaseq `--demo`)
- **Cause:** An upstream defect in `nf-core/scrnaseq` 4.2.0 test configurations referencing obsolete nf-validation 1.x parameters.
- **nf-claw Mitigation:** `nfclaw run` automatically neutralizes this warning by generating a narrow `-c` compatibility configuration:
  ```groovy
  // <outdir>/provenance/nf_schema_compat.config
  validation { ignoreParams = ['validationSchemaIgnoreParams'] }
  ```
  Pipelines declaring nf-validation 1.x correctly (e.g. `chipseq`, `atacseq`, `circdna`) are untouched.

### rnaseq `--demo`: `--gtf` with `--gff`, `--transcript_fasta`, and the `first` operator
- **Cause:** rnaseq's bundled `conf/test.config` intentionally sets `gtf`, `gff`, and `transcript_fasta` simultaneously to exercise multiple code paths, prompting Nextflow to log preference for `--gtf`. A real production run specifying custom references does not set both and emits no warning.

---

## Upstream pipeline bugs (documented, not patched)

These defects affect specific pinned releases. Workarounds and recorded runtime corrections keep upstream source trees unchanged; generated task scripts may differ when a documented correction is applied:

| Pipeline @ Version | Symptom | Underlying Defect | Recommended Workaround |
|---|---|---|---|
| `bamtofastq` (incl. 2.1.2 / 2.2.1) | `SAMTOOLS_FAIDX ([])` fails immediately | The `test` profile sets `genome = null` + `igenomes_ignore = true`, routing an empty dummy channel into `SAMTOOLS_FAIDX`. | Provide an explicit reference (`--fasta` / `--genome`); demo mode without reference fails upstream. |
| `bacass` 2.6.1 (Unicycler) | `SyntaxWarning: invalid escape sequence '\d'` then fails on Python 3.12 | The `unicycler:0.5.1` container ships legacy Python code not updated for Python 3.12. | Select Megahit assembler: `--assembler megahit`. |
| `fastqrepair` 1.1.1 | healthy reads disappear at split boundaries; singleton publication can be empty although the pipeline succeeds | Wipertools 1.1.5 splits lines or bytes rather than complete FASTQ records. The BBMap task also omits a shell continuation before `qin`, so that option and log redirection miss the real command. Its publisher maps the log onto the singleton filename; some paired wipe reports also share a publication name. | For the exact affected commit, nfclaw records a compatibility config that preserves complete records (or keeps ambiguously framed input in one chunk), passes the declared quality offset, and separates singleton reads, logs and mate reports. The embedded splitter checks that input bytes did not change between its two passes and records its source SHA-256 as its tool version. Recipe-specific internal prefixes invalidate old task caches while published sample identities stay unchanged. Inspect the generated config and actual `.command.sh` files; the pinned source tree is not edited. Independent known-input pairing and replay controls must pass before treating these corrected outputs as validated. |
| `hgtseq` 1.1.0 | `a column named input1 ... is mandatory!` | Schema requires `sample,fastq_1[,fastq_2]`, but custom parser `workflows/hgtseq.nf` expects `sample,input1[,input2]`. | An `input1`-only sheet is also refused by nfclaw because the pinned schema requires `fastq_1`. For `.fastq.gz` inputs (the custom parser rejects `.fq.gz`), both column sets must describe the same absolute inputs (`fastq_1`/`input1` and, if paired, `fastq_2`/`input2`) to satisfy the schema and custom parser. This is a source-derived compatibility option, not an established end-to-end workaround. BAM/CRAM inputs have no corresponding valid FASTQ schema contract in this release. Use a separately validated release/configuration for scientific runs; the bundled schema does not declare these data fields as path formats, so their source bytes are not automatically covered by the local samplesheet dependency manifest. |
| `funcscan` 2.1.0 – 4.0.0 (DRAMP DB only) | `TypeError` in `ampcombi_download.py` when downloading DRAMP database | DRAMP download loop regex matches NaN float values when rows contain empty sequence fields. APD database unaffected. (Requires `--nxf-ver 25.10.4`). | Pre-build DRAMP database with NaN rows removed and pass `--amp_ampcombi_db /path/to/db`. |
| `taxprofiler` 2.x (MultiQC 1.34) | `MULTIQC` fails: `AttributeError: module 'rich' has no attribute 'panel'` | MultiQC raises `IndexError` on empty MetaPhlAn profiles, followed by a secondary failure in error reporting. | Profile reads that match database content, or disable MetaPhlAn: `--run_metaphlan false`. |
| `bactmap` 1.0.0 | bundled `--demo` reference cannot be read; its default preview also cannot complete | The moving test-data branch deleted the original *Neisseria gonorrhoeae* reference and now supplies *Bacteroides fragilis* reads. The `test` profile also replaces the module-options map, dropping defaults such as MultiQC arguments. With those two faults addressed, the unconditional completion handler still waits on `multiqc_report.getVal()`, which has no value under `-preview`. | Use the complete matched historical [test-data snapshot](https://github.com/nf-core/test-datasets/tree/02195cfa96ca496173e9d63dd58e34bf02fcf55a), retain the bundled default module options and reapply the test overrides. A genuine Docker test run on Nextflow 24.10.5 completed all 47 tasks; all four trees contained the expected three samples and reference. This establishes execution and output identity, not phylogenetic accuracy. The default preview remains rejected. |
| `createpanelrefs`, `proteinfamilies` (pinned releases) | default `-preview` acceptance times out | Nextflow's workflow-output completion code waits for values that preview never produces; this was reproduced on the declared 26.04.0 engine and 26.04.6. | A preview-only config with `workflow.output.enabled=false` permits createpanelrefs graph validation. For proteinfamilies, set the bundled `params.skip_proteinfold_samplesheet=true` and `params.skip_proteinannotator_samplesheet=true` as Groovy booleans in a config. Both variants completed, but output publishing is excluded from preview validation. Keep their default previews rejected. The unchanged bundled test analyses subsequently completed on native amd64 with Nextflow 26.04.0, including publishing ([createpanelrefs execution](https://github.com/danilomonge/nf-claw/actions/runs/37922299422), [proteinfamilies execution](https://github.com/danilomonge/nf-claw/actions/runs/37922302411)). Independent controls checked createpanelrefs target coverage coordinates and finite numeric metrics for two normal samples; the antitarget BED and coverage tables were empty, so their checks establish an empty inventory rather than nonempty antitarget coverage. Proteinfamilies retained all member residues, preserved family/HMM inventory and matched representative sequences or declared source subdomains. These controls do not establish CNV calling accuracy or optimal protein family inference. |
| `multiplesequencealign` 1.1.1 | default `-preview` acceptance times out | Its own completion handler waits on `summary_reports.getVal()`; preview cannot produce the required process results. A newer engine does not resolve this dependency. | The unchanged official `test_tiny,docker` profile completed all 78 tasks on the declared Nextflow 25.04.2, using a matched immutable test-data snapshot. FAMSA, MAFFT and consensus outputs preserved all sequence IDs and ungapped amino-acid sequences; all six summary rows had finite configured metrics. This covers the tiny profile's two aligners and completion lifecycle, not every aligner or biological alignment accuracy. The default preview remains rejected. |
| `multiplesequencealign` 1.1.1 (full `test` profile) | Docker exits 125 at `LEARNMSA_ALIGN`: `manifest unknown` | The pinned module requests `felbecker/learnmsa:2.0.9`, which was unavailable in a [native full-test execution](https://github.com/danilomonge/nf-claw/actions/runs/37919738383). Other aligners' partial outputs do not make this a successful run. | The validated `test_tiny,docker` profile covers FAMSA and MAFFT, not learnMSA. Full-profile validation requires the exact unavailable image to be restored or a separately validated tool/configuration change. Do not silently substitute `latest` or a newer image: [learnMSA changed its sequence-weight defaults and removed `--sequence_weights` from 2.0.10](https://github.com/Gaius-Augustus/learnMSA#using-learnmsa), while this pinned full test uses that flag. |
| `marsseq` 1.0.3 | bundled `test` analysis preview fails with missing local references | `test.config` selects `mm10`, but analysis requires prebuilt FASTA, GTF, Bowtie2 and STAR references. `main.nf` chooses either reference building or analysis, so build and analysis are separate invocations. | Build with `--build-references true --velocity true` so both Bowtie2 and STAR indexes are generated (analysis checks the STAR path even when velocity is disabled), then supply the resulting reference base using `--genomes-base`. The complete bundled reference workflow, including real Bowtie2 and STAR indexes, completed on Nextflow 23.04.0; default and velocity-enabled analysis previews then passed with matched SB26-AB339 test inputs. These previews do not execute quantification or establish expression accuracy. **Assembly warning:** the [pinned `mm10` key](https://github.com/nf-core/marsseq/blob/b02ede773092f8a8a5999400acda6894d51b4d26/conf/genomes.config) selects **GRCm39 / GENCODE M27**, plus ERCC sequences; [GENCODE identifies M27 as GRCm39](https://www.gencodegenes.org/mouse/release_M27.html), whereas [UCSC mm10 is GRCm38](https://hgdownload.cse.ucsc.edu/gbdb/mm10/html/description.html). Record the actual assembly, annotation and reference checksums; never silently substitute GRCm38 or infer the assembly from this key. |
| `tumourevo` 1.0.0 | CNAqc parameter description links to an absent parameter | The pinned schema's `cnaqc_min_absolute_karyotype_mutations` description refers to `cnaqc_min_karyotype_size`, which is not declared in that schema or passed by its CNAqc module configuration. This upstream cross-reference has no target in the generated documentation. | Use only parameters declared by the pinned schema; nfclaw rejects the absent flag. `--cnaqc-min-absolute-karyotype-mutations` sets an absolute mutation-count threshold. The missing reference does not establish an equivalent relative threshold or a replacement flag; consult the pinned module and CNAqc tool documentation for interpretation. |

---

## Pipeline-specific run notes

- **`demo` 1.2.0 on macOS arm64 with amd64 containers** — MultiQC 1.34 can
  return exit zero and write its HTML/data while Kaleido/Chromium fails to export
  plots under QEMU. Fresh and resumed local runs both reported `0/36 completed`,
  with `qemu: unknown option 'type=utility'` and Chromium sandbox/GPU crashes.
  Check the task's `.command.err` and required plot files even when pipeline status
  is success. Validate required exports on a compatible native execution platform;
  no arm64 image or emulation workaround has been established yet.

- **`rnaseq` 3.27.0 bundled test** — A [native Docker execution](https://github.com/danilomonge/nf-claw/actions/runs/37926522041) completed all 234 tasks on Nextflow 25.10.4. Downloaded bytes matched all 1,056 recorded output checksums. Independent consistency checks covered five samples and 125 transcripts in each of the Salmon and STAR/Salmon routes: finite nonnegative estimates, normalized TPM, assigned-fragment totals and merged transcript/gene tables agreed with individual results within their published rounding. This validates the bundled test's execution and internal numerical consistency, not biological expression accuracy, differential expression or every alternative aligner.

- **`fastqrepair` 1.1.1 bundled test** — A [native Docker execution](https://github.com/danilomonge/nf-claw/actions/runs/37926532237) completed all nine tasks on Nextflow 25.10.4. Its paired sample was filtered after gzip recovery produced an empty mate; the pipeline logged that sample and the explicitly empty fixture. The surviving single-end sample produced 24 unique well-formed reads, agreeing with its repair report and independent FastQC read-count, length and GC checks. This fixture did not execute `BBMAP_REPAIR`, so it does not validate paired-read re-pairing or preservation of all original reads. Inspect discarded-sample warnings and repair reports alongside pipeline status.

- **`fetchngs`** — If accessions lack ENA FTP links, the pipeline falls back to `SRATOOLS_PREFETCH` (requiring NCBI SRA Cloud access). In network-restricted environments, run metadata-only via `--skip_fastq_download`. (Accepts `.csv`, `.tsv`, or `.txt` accession lists at pinned 1.13.0 and `dev`).
- **`coproid`** — Requires **two** samplesheets: `--input` (FASTQ sheet) and a separate required `--genome_sheet`. Each row in `--genome_sheet` requires `genome_name,taxid,genome_size` plus **exactly one** of `igenome` or `fasta` (mutually exclusive `oneOf` schema). `--kraken2_db` is mandatory and must point to a valid Kraken2 database.
- **`crisprseq`** — The samplesheet `reference` column expects a **raw DNA sequence string** (pattern `^[ACTGNactgn]+$`), not a FASTA file path.
- **`circdna`** — Two parameters are **required by schema** for non-demo runs: `--input_format` (`FASTQ` or `BAM`) and `--circle_identifier` (one or more of `circle_map_realign`, `circle_map_repeats`, `circle_finder`, `circexplorer2`, `ampliconarchitect`).
- **`metapep`** — The `--demo` profile runs `DOWNLOAD_PROTEINS`, which fetches sequences from **NCBI Entrez** (`download_proteins_entrez.py --email $NCBI_EMAIL`) reading a Nextflow secret named `NCBI_EMAIL`. Set the secret prior to execution: `nextflow secrets set NCBI_EMAIL you@example.com`.
- **`createtaxdb`** — Assign each sample a **non-numeric** `id` (e.g. `seq1`, `chr1`). Purely numeric strings (`"1"`) are coerced to integers by nf-schema, violating string constraints.
- **`genomeassembler`** — Set at least one of `--ont true` or `--hifi true` (the pipeline aborts with `At least one of params.ont, params.hifi needs to be true.`).
- **`funcscan`** — Pin `--nxf-ver 25.10.4` (declares `!>=25.10.4`). Demo profiles run all three screenings (AMP, ARG, CAZyme), which download multi-gigabyte models; pre-supply databases via `--amp_ampcombi_db` or disable heavy steps via `--run_cazyme_screening false` and `--arg_skip_deeparg true`.
- **`sarek` 3.10.0 (`sarek` 3.9.0)** — Upstream examples for cache/index-only runs show `--build_only_index --input false`. In raw Nextflow, this causes an nf-schema validation error because `input` is declared as a string path. In `nfclaw run sarek --input false`, nfclaw intercepts `--input false` and leaves `input` unset in `params.json`, allowing index-only runs (`--build_only_index true --download_cache true`) to succeed cleanly without schema errors. For raw Nextflow runs, omit `--input` instead of passing `false`.
- **`sarek` 3.10.0 (`sarek` 3.9.0)** — Do not use `--config pipelines/sarek/upstream/conf/test.config` to convert an analysis run into a test run with a custom samplesheet. Extra configs load after initial profile setup, causing validation of default S3 iGenomes paths. Run with `-profile test,docker` instead: `nfclaw run sarek --input samplesheet_sarek.csv --outdir results -profile test,docker`. For bundled test data, use `nfclaw run sarek --demo --outdir results`.
- **`ampliseq` 3.0.0** — The bundled `test` profile sets its own `process.resourceLimits` (4 CPUs, 15 GB, 1 h); the release has no `--max_memory`/`--max_cpus` parameters (nfclaw rejects them as unknown), so cap a real run with `--limit-cpus`/`--limit-memory`/`--limit-time`. Its `--demo` completed all 130 tasks without a retry on Nextflow 26.04.3 with Docker (Linux amd64); `QIIME2_EXPORT_RELTAX` peaked at 1.2 GB of RSS. This establishes execution of the bundled test, not taxonomic accuracy. 3.0.0 also removed the legacy `sampleID,forwardReads` samplesheet format (use `sample,fastq_1[,fastq_2]`) and renamed `--FW-primer`/`--RV-primer` to `--primer-fwd`/`--primer-rev`; nfclaw rejects the old names.
  - **Reproducibility:** DADA2 taxonomy ties and QIIME2 rarefaction can change results on fresh runs despite `--seed`. See [verified findings and workarounds](#ampliseq-300-taxonomy-and-rarefaction-reproducibility).

### AmpliSeq 3.0.0: taxonomy and rarefaction reproducibility

Scope: the pinned AmpliSeq commit `992e6df34065067185b5e34665b5861b6827981d`; source inspection and
a small C++ tie-breaking check, not a new end-to-end demo replay.

- **DADA2 claim confirmed, with precise wording.** The
  [1.38.0](https://bioconductor.posit.co/packages/3.22/bioc/src/contrib/dada2_1.38.0.tar.gz) and
  [1.40.0](https://bioconductor.posit.co/packages/3.23/bioc/src/contrib/dada2_1.40.0.tar.gz) release
  archives contain identical `src/taxonomy.cpp`:
  [`get_best_genus()`](https://github.com/benjjneb/dada2/blob/b61fe2e90115be08e78a01a16af89fd21402ca42/src/taxonomy.cpp#L73-L110)
  seeds `std::mt19937` from `std::random_device` and randomly chooses among equal scores. This is
  entropy-seeded randomness, without a user-controllable seed. The function is called for both the
  full query and bootstrap replicates; bootstrap subsampling separately uses R's `Rcpp::runif`.
  AmpliSeq's [taxonomy
  module](https://github.com/nf-core/ampliseq/blob/992e6df34065067185b5e34665b5861b6827981d/modules/local/dada2_taxonomy/main.nf#L29-L40)
  calls `set.seed()` using `params.seed` (default 100), but that controls only R's RNG. Neither
  changing `--seed` nor using one thread controls the C++ ties.

- **QIIME2 claim depends on version and action.** The [2024.10 rarefy
  interface](https://docs.qiime2.org/2024.10/plugins/available/feature-table/rarefy/) has no seed
  parameter; [`feature-table rarefy` in
  2025.4](https://amplicon-docs.qiime2.org/en/2025.4/references/plugins/feature-table.html) exposes
  `random_seed`. AmpliSeq 3.0.0 specifies QIIME2 2026.4, whose [core-metrics
  interface](https://amplicon-docs.qiime2.org/en/2026.4/references/plugins/diversity/) also exposes
  it and [forwards it to
  rarefy](https://github.com/qiime2/q2-diversity/blob/2026.4.0/q2_diversity/_core_metrics.py#L14-L46).
  The [AmpliSeq core
  module](https://github.com/nf-core/ampliseq/blob/992e6df34065067185b5e34665b5861b6827981d/modules/local/qiime2_diversity_core/main.nf#L35-L60)
  omits `--p-random-seed` and does not consume `params.seed` or `ext.args`: its sampling remains
  uncontrolled by AmpliSeq's `--seed`. Its separate `alpha-rarefaction` action [has no seed argument
  and repeatedly calls rarefy without
  one](https://github.com/qiime2/q2-diversity/blob/2026.4.0/q2_diversity/_alpha/_visualizer.py#L289-L333).

- **Implications and limits.** Fresh executions can change taxonomy labels, bootstrap confidence and
  assignments near `--dada-min-boot`, and rarefied counts, diversity metrics and downstream
  analyses. These mechanisms do not imply changed ASV inference, that every output must differ, or
  that GTDB ties are common: their frequency and scientific impact depend on the inputs/reference
  and were not established here. Previously reported demo measurements were 3 of 241 changed labels,
  34 changed bootstrap confidences and 4–6 label differences per pair across four isolated reruns (4
  threads and `FALSE`). ASV sequences/counts, DADA2 statistics and QIIME2 taxonomy matched; the
  filtered table retained 38 ASVs/counts with changed row order. These observations were not
  independently repeated in this audit and are not general guarantees.

- **Workarounds.** Retain original taxonomy and rarefied tables for downstream reuse (the core
  task's `diversity_core/rarefied_table.qza` stays in its work directory, outside the published
  module outputs); `--resume` can reuse valid cached tasks but does not make a fresh replay
  deterministic. Alternatively, use `--skip-dada-taxonomy true` with a suitable
  `--qiime-ref-taxonomy` classifier (the prior demo's repeatability does not establish universal
  accuracy or determinism). For controlled diversity calculations, skip pipeline diversity with
  `--skip-diversity-indices true`, retain the matching feature table, tree and metadata, and run
  QIIME2 2026.4 `core-metrics-phylogenetic` separately with `--p-random-seed 100`. Skip the independent curves with
  `--skip-alpha-rarefaction true` if needed. Seeds constrain sampling with the same inputs/software;
  they do not guarantee byte-identical QZA/QZV archives or all downstream statistics. Compare
  exported scientific values by ASV/sample; `nfclaw verify` checks structure and `--strict`
  additionally checks bytes, neither guarantees analytical accuracy.

- **nf-claw behavior.** The runner currently announces taxonomy/core-metrics variability before
  launch through `runner/reproducibility.py`; it adds no seed correction. Detection scans module
  text and explicit skip parameters, without checking tool versions or resolving config/profile
  overrides; it does not detect alpha-rarefaction separately. An advisory therefore identifies a
  potential source of variability, not proof that a particular run changed.

---

### Chains: what a `demo: true` stage hands over

When a stage specifies `demo: true`, it executes with its bundled test profile dataset:
- **`detaxizer`:** The test profile filters reads with an empty database, removing all reads and leaving empty FastQ files. For downstream chaining, provide active classification parameters: `"params": {"classification_kraken2": false, "classification_bbduk": true, "fasta_bbduk": "<host fasta>"}`.
- **`demultiplex`:** Test data consists of human amplicon reads. Downstream stages requiring reference genomes need human references (`fasta`/`gtf`), and paired-end profiles: `"profile": "test_pe,docker"`.
- **`taxprofiler`:** Test profiling on unrecognized reads fails in unhandled zero-hit modules; enable only resilient profilers (`run_kraken2`, `run_kaiju`) with `"run_profile_standardisation": false`.

### File-only inventories missed empty directories and changed aliases
- **Status: Fixed for new recorded namespaces.** Output verification previously accepted two trees with identical files but different empty-directory names. Reference handoffs could also accept changed directory shapes or retargeted aliases whose file bytes remained identical.
- **Behavior:** New bundles record `outputs.inventory.json`. Verification reports missing/extra directories and changed link identities alongside file differences. Old file-only manifests provide byte comparisons, but historical directory agreement remains unverified and cannot return a successful structural check. Live trees without historical manifests remain comparable.
- **Handoffs:** Published output namespaces and local reference namespaces are verified before the next stage starts. Chain status checks source namespaces and the downstream prelaunch snapshot. Complete run-directory handoffs retain all entries and record execution metadata at the boundary separately from historically published results.
- **Validation:** Real producer and consumer tasks exercised external references, published directories and complete run directories. Renaming an empty sample directory while retaining reference bytes blocked the consumer; restoring the original namespace allowed resume, and subsequent changes broke lineage. These execution and conservation checks do not establish biological accuracy.
