# Final pre-release audit, 2026-11-05

Audited: `8f0f6de` (`main` after #256). Findings are numbered G01–G16, after the A–F series of the
earlier records. Server: `denbi_instance`, Python 3.12.3, Nextflow 26.04.3 (build 12259), OpenJDK
17.0.20.1, Docker 29.1.3, every pipeline submodule initialised. Local: macOS, Python 3.13 (and the
system Python 3.9.6 for G09 and the bundled scripts).

The earlier audits read every module and fuzzed the parsers. This one read the runner again with
the static gates beside it, and then went after what those audits had no reason to try:

- **A new user's path.** A fresh clone without submodules, a fresh virtualenv, and the README's
  commands as written, followed by `git status` (G04).
- **Ways a run ends without a goodbye.** SIGKILL of a real run, of a real chain and of a run on
  `--no-provenance`, then what `nfclaw status` advises and what `--resume` really does (G01, G02,
  G05).
- **Stops at the worst moment.** A stop as the first tasks start, while the daemon is still creating
  their containers (G03).
- **Odd arguments and environments.** 115 argument and environment cases against the CLI:
  unknown users, over-long names, invalid UTF-8, empty values, special files, deleted working
  directory, invalid `NFCLAW_*` values, a POSIX locale. A Python traceback or a timeout counts as a
  finding (G06, G08).
- **Pins moved since their last on-host validation.** Each one's demo, replay and verification,
  and what each bump did to the audited input roles (G07). Then a [sweep of every pin](#the-pin-sweep).
- **Every documented command.** All 304 `nfclaw` command lines in the guides, the README and the
  website, parsed against the real argument parser; every internal link and anchor; every
  `NFCLAW_*` variable against its documentation. No mismatch then. #258 reorganized the guides
  afterwards, so all of it ran again on 329 command forms: one mismatch, `nfclaw --demo` with no
  command, now corrected. This shows that commands parse and links resolve, not that the prose is true.

Each finding was reproduced before it was fixed; each fix has a test that fails without it.

## Checklist

| ID | Severity | Location | Finding | Disposition |
|---|---|---|---|---|
| G01 | High | `runner/orchestration.py` (`_input_resume_warning`, `_source_resume_warning`), `runner/provenance.py`, `runner/cli.py` | The bundle is written when a run ends. A nfclaw killed outright (SIGKILL, out of memory, a host restart) or unable to finish it (a full disk) left `--resume` nothing to compare sources and inputs against, so it archived the run and recomputed every task of what may be a days-long analysis. `nfclaw status` meanwhile said "re-run the same command with --resume to continue where it stopped", and the full-disk error "every task is reused from the cache". Reproduced: a real `demo` run, SIGKILL after 4 finished tasks, `--resume`: `-resume` absent from the command, the run moved to `.previous-<id>`, nothing cached. | A launch writes `provenance/launch-record.json` before Nextflow starts: the source identity and the input bytes and namespace it launched with. With no manifest, the resume guards compare against it; a changed source or input still starts fresh, and a damaged record counts as none. The published manifest replaces it, so a finished bundle is unchanged. The same run resumes with its finished tasks cached, no archive; its replay succeeds and verifies with an identical environment. |
| G02 | High | `runner/chain.py` (`_unchanged_handoff`) | The same for a chain: a stage whose nfclaw was killed prepared its handoff again at a new path, and a new input path alone recomputes every task. | The launch record carries the stage's chain link, so the attempt's handoff is found and kept. |
| G03 | Medium | `runner/replay_guard.py` (`remove_task_containers`), `runner/execution.py` (`_terminate`) | A stop while the daemon is still creating a task container: its wrapper's `docker stop` and nfclaw's `docker rm -f` both find `No such container`, the daemon then finishes creating it, and a container that never started is removed by nothing. Six of them stayed behind after one SIGTERM on the loaded server, contradicting "removes the task containers". | The stopping group is looked through every 0.25 s until it ends, because a client can outlive the signal or start after it. A container the engine does not list yet is looked for until it appears, within one 30 s wait however many there are; one already listed is not waited for, so an ordinary stop takes no longer. One that still has not appeared is reported with the command of the engine that started it, and a removal the engine says is already in progress is no longer reported as a failure. This narrows the problem and does not close it: see [Not changed](#not-changed-and-why). |
| G04 | Medium | `.gitignore` | The documented `--outdir results` left the checkout dirty: its writer lock `.results.nfclaw.lock`, the default replay target `results.replay/` and the archive `results.previous-<id>/` are not `results/`. | All three are ignored. A test asks Git itself. |
| G05 | Medium | `runner/cli.py` (`_status_report`) | `nfclaw status` told a killed *replay* to re-run with `--resume`, which `commands.sh` does not have. | A replay is told to run `commands.sh` into a new empty directory; a run launched with `--no-provenance` is told that `--resume` will recompute. |
| G06 | Medium | `runner/replay_guard.py` (`check_write_boundaries`), `runner/input_safety.py` | `nfclaw run … --check --outdir /` never returned, and any large existing directory given as `--outdir` took minutes, as did one given to `commands.sh`: the boundary check walked every entry under it looking for links into the inputs, although a real run refuses a non-empty directory without `--resume` (and a replay refuses any that holds files). `--check` deliberately does not refuse one, so it now exits without walking it. | A destination that will be refused is not walked. An input inside it is still refused as an overlap, by path. |
| G07 | Medium | `runner/input_roles.json` | Audited roles are keyed by schema digest, and the bump to bacass 2.7.0 changed its schema. `R1`, `R2` and `LongFastQ` fell back safely to pattern-based file columns, but a Fast5 directory silently left the run's input identity, so a changed one was invisible to `--resume` and the replay guard. Ampliseq 3.1.0 and rnasplice 2.0.0 keep or now declare their roles; pixelator 6.0.0 kept its digest. | An audit of 2.7.0's consumer (`resolveFilePath`, `subworkflows/local/utils_nfcore_bacass_pipeline/main.nf`) with the same roles. |
| G08 | Low | `runner/cli.py` (`main`), `runner/probes.py` | A `~` naming no user (`nfclaw status ~nosuchuser/x`) ended in a `RuntimeError` traceback, in 13 of the fuzzed commands. `nfclaw show` and `status`, whose reports hold `—` and `≥`, crashed with `UnicodeEncodeError` on a stdout that cannot show them (a Latin-1 terminal, `PYTHONIOENCODING=ascii`). | One refusal, naming the path rule. It answers only pathlib's own two messages: a peer review pointed out that catching every `RuntimeError` would have hidden real bugs behind the same line. Such characters print escaped, and a probe's undecodable output is replaced rather than fatal. |
| G09 | Low | `runner/__main__.py` | The documented no-install form on macOS's `python3` (3.9) ended in `ImportError: cannot import name 'UTC'`. | It names the Python it needs. |
| G10 | Low | `runner/config_probe.py` | `--check -profile nosuchprofile` said the engine "cannot parse its configuration" and suggested another engine and parser. | It says the release defines no such profile. |
| G11 | Low | `runner/parameters.py`, `runner/cli.py` | A params file's `multiqc-title` was reported as an unknown parameter `--multiqc-title`, a flag the command line accepts. A value starting with `-c` was told to pass pipeline parameters as `--param value`, which is what the caller had done. | The first names its spelling in a file; the second names `--param='-c 3'`. |
| G12 | Low | `runner/orchestration.py` | `--resume` into an empty `--outdir` archived the empty directory and reported preserving a previous run. | Nothing to preserve, nothing archived. |
| G13 | Low | `tests/test_runtime_followthrough.py`, `README.md`, `docs/mcp.md`, `runner/replay_guard.py`, `runner/source_corrections.py` | The socket test behind a red macOS lane on `main` (run 41939826353) caught only `EPIPE`/`ECONNRESET`, while macOS can report a closing peer as `EPROTOTYPE`, and allowed the handler 1 s on a loaded runner. A garbled README sentence. The job store's growth was undocumented. Four reads relied on the locale's encoding (harmless today: those records are ASCII). | Any closed-peer error, within 10 s. Fixed, documented, and explicit. |
| G14 | Low | `runner/config_probe.py`, `runner/input_safety.py` | On a host whose JVM cannot reach GitHub, `--check` said the engine "cannot parse its configuration" and suggested another engine and parser. Nextflow 26.04 prints only `Unable to parse config file` there, and the documented IPv6 flag alone fixes it. Separately, a chain `--outdir` holding only the chain's own record counted as refused, so its links were not looked for, although a chain still writes there. | A failed probe is repeated with remote includes skipped: if that parses, the report names the network and its remedies, or, when Nextflow names no include, says the release could not use a remote configuration it includes (it parses without them) rather than claim a fetch failed. A chain's record no longer makes its `--outdir` non-empty. |
| G15 | Medium | `runner/orchestration.py`, `runner/runlog.py`, `runner/cli.py`, `runner/chain.py`, `runner/environment_record.py` | A gap in what a successful run recorded for its replay (an image without a digest, no task records) reached only stderr and `environment.json`, and a task with no container was not recorded as a gap at all. `run.log`, `nfclaw status` and `nfclaw chain status` said nothing, so a background run or a later session could not see it. A peer session's repeat on a real engine found this. | The gap is a line in `run.log`, which console text cannot forge. `nfclaw status` lists it under `provenance gaps` (`provenance_gaps` with `--json`) and `nfclaw chain status` beside the stage. `status: success` and the exit code do not change, because the results stand. |
| G16 | Medium | `runner/environment_record.py`, `docs/known-issues.md` | A run with no task records (`cleanup = true`, as genomeqc's test profile sets) recorded no gap, so its bundle read as 0 processes, 0 images and nothing wrong. | `environment.json`'s `issues` says that no image was identified or pinned and why. The replay's check reports `unverified`. The guide gives the remedy, a config holding `cleanup = false`. |

## Evidence

Runs, stops, chains, MCP and the CLI cases ran on the server on the fixed tree, and the last round of them on
`366c203`. Only `environment_record.py` changed after that, in `feba432`, the last code change, which has its own
suite and its own real run. The static gates, the website and part of the packaging ran locally. The per-pin records are
[`evidence/2026-11-05-pin-runs.json`](evidence/2026-11-05-pin-runs.json), for the pins that had moved, and
[`evidence/2026-11-05-pin-sweep.json`](evidence/2026-11-05-pin-sweep.json), for the sweep.

- **Suites.** On `feba432`: 4,196 tests, 0 failures, 4 skips; `ruff` and the drift check clean. `main`
  before the fixes: 4,129 tests, 0 failures, 4 skips. The 4 skips are audited-commit fixtures that a
  depth-1 clone lacks. GitHub CI on `feba432`: all 10 pytest lanes (Ubuntu and macOS, Python
  3.11–3.15), website, Nextflow integration, drift, native and Apptainer demos, CodeQL. One macOS lane got
  no runner and was rerun.
- **Static gates and the repository.** `zizmor` (only the notes below), `actionlint`, `shellcheck`,
  an extended `ruff` selection read rule by rule, `pip-audit` with no known vulnerability. The
  ruleset is active; private vulnerability reporting, secret scanning and push protection are on;
  no Dependabot or code-scanning alert is open.
- **Website.** `npm audit`, `tsc`, the build and the `llms` comparison pass. Playwright: 166 of 166,
  one after a rerun of an `ERR_NETWORK_CHANGED` flake.
- **Packaging.** Wheel and sdist build; a non-editable install explains itself; a fresh clone
  initialises the submodule it needs. Startup takes 0.2 s. A 10,000-file input scales linearly:
  validation 2 s, write boundaries 3 s, sheet generation 6 s. The bundled replay scripts import on
  Python 3.9.6.
- **A run, and how it ends.** A demo with limits, its replay and `nfclaw verify` (42 identical, 34
  changed, 0 missing, 0 extra, environment identical); a generated samplesheet, also under
  `--require-environment`. SIGKILL on `main` recomputed every task (G01); with the fix finished tasks
  came from the cache, nothing was archived, and the replay's environment was identical. `--timeout`
  left no containers; a timed-out run, a failed task and a SIGTERM each resumed. A second run into
  the same `--outdir` was refused. A killed `--no-provenance` run's status says `--resume` recomputes
  every task.
- **Versions and engines.** Release 1.1.0 with replay and verify; a `dev` run, and its bundle replayed
  after moving it; Nextflow 26.10.4 and 26.10.5 with replay and verify. A stub run through `--config`
  and proteinfold's `--demo` both report their caveats.
- **Chains.** `demultiplex` → `seqinspector`: SIGTERM then `--resume`; SIGKILL in stage 2 after 56
  tasks, then `--resume`: exit 0, stage 2 cached, no archive, lineage verified by SHA-256.
  `chain --check`: 15 of 19 edges pass on Nextflow 26.04.3 unpinned, and the other 4 are refused
  with the remedy named. All of this ran again on `366c203`, where the SIGKILL came after 5 of stage 2's
  tasks and those 5 were cached. An MCP chain ran there too, with its lineage verified.
- **Stops at the worst moment (G03).** Under load, with no wait, 6, 4 and 6 containers stayed `created`.
  With a wait of 15 s, 0, 6 and 0 did: containers appeared 2 to 15 s after the SIGTERM, and the slowest stop
  took 79.6 s, with `rm -f` at its 60 s bound. Hence one wait of 30 s, and a report of what still has not
  appeared. An ordinary stop, whose containers already run, listed nothing to wait for, and the 5 false
  "could not be removed" lines are gone. Then a real chain's SIGTERM on `85313d4` left one exited container,
  whose client had started after nfclaw last looked. Stops timed as tasks start reproduced it: on that code, 2 of
  12 trials left containers, 2 each. With the group looked through until it ends (`366c203`), the same 12 trials
  and the battery's 3 more left none, in 5.0–37.9 s, and the same chain's stop left none. Four stops took
  35–38 s, the wait for a container that never appeared. 12 trials are too few to show the rate by themselves;
  the tests that fail without the fix show the mechanism.
- **Odd input (G06, G08).** `--outdir /` is refused in 0.6 s, `/mnt/volume` (771 GB in use) in 0.9 s,
  the same in a chain in 2.1 s, and `commands.sh /mnt/volume` in 0.2 s. Of the 115 cases on `366c203`,
  114 end cleanly at once, with no traceback. The other, `NXF_HOME='~nosuchuser/h'`, is Nextflow
  downloading itself into a new home, which stalls on this IPv6-only host; `NFCLAW_CONFIG_TIMEOUT`
  bounds it, and with a 20 s bound it was refused with that cause and left no process behind.
- **MCP, through the official SDK.** On `366c203`: 14 tools; a refused job reports its cause; a real job
  succeeds and `nfclaw jobs` agrees; path traversal is refused; replay and verify pass; `cancel_job` took 5
  task containers to 0. A job whose supervisor got SIGKILL reads `lost`, and `resume=true` succeeded with its 2
  finished tasks cached and no archive.
- **Provenance gaps on a real engine (G15, G16).** A demo with `cleanup = true` through MCP on `366c203`:
  `get_job`, `run_status` and `nfclaw jobs status` each report the gap, and the run stays `success` with exit
  code 0. `get_job` and `nfclaw jobs status --json` carry it in the status report's text, and `run_status`
  also as `provenance_gaps`. A real chain with the same config: `nfclaw chain status` names it beside each
  stage, with the lineage verified. mcmicro's demo on `feba432`: its `exec:` task `OMEVALIDATION` is named by
  the run's warning, `nfclaw status`, `provenance_gaps` and `environment.json`. Its replay reports `unverified`,
  and `nfclaw verify` exits 0 (18 identical, 13 changed, 0 missing, 0 extra), or 1 with `--require-environment`.
- **Every pin.** The maintenance smoke step exits 0 on `366c203`: all 95 pins pass on the engine their
  `skill.md` names. On Nextflow 26.04.3, 25 of them are refused without `--nxf-ver` or
  `NXF_SYNTAX_PARSER=v1`, as documented.

Pins moved since their last on-host validation, each on the engine its `skill.md` names. Sarek, sopa,
bacass and variantbenchmarking first ran short of disk, so these rows are from the sweep below:

| Pin | Nextflow | Run | Replay | `nfclaw verify` |
|---|---|---|---|---|
| ampliseq 3.1.0 | 26.04.0 | success, 130 tasks | success, environment identical | 1,288 identical, 322 changed |
| bacmodel 1.0.1 | 25.10.4 | success, 2 tasks | success, environment identical | 15 identical, 5 changed |
| detaxizer 1.4.0 | 26.04.0 | success, 54 tasks (on `8f0f6de`) | success, environment identical | 80 identical, 42 changed |
| pixelator 6.0.0 | 25.10.4 | success, 27 tasks | success, environment identical | 21 identical, 97 changed |
| sarek 3.11.0 | 25.10.4 | success, 22 tasks | success, environment identical | 86 identical, 97 changed |
| sopa 1.0.2 | 25.10.4 | success, 9 tasks | refused by the environment check, as documented | — |
| bacass 2.7.0 | 25.10.4 | success, 17 tasks | success, environment identical | 130 identical, 114 changed |
| variantbenchmarking 1.6.0 | 25.10.4 | success, 68 tasks | success, environment identical | 47 identical, 47 changed |
| variantbenchmarking 1.6.1 | 25.10.4 | success, 68 tasks, twice (on `aea5fa4`) | success, environment identical | 46 identical, 48 changed; 45 and 49 |

Every verified replay has 0 missing and 0 extra files. Ampliseq's changed files are mostly QIIME2
results and MultiQC reports (257 and 40 of the 322), and pixelator's are its per-stage outputs and
logs. They were not compared one by one.

## The pin sweep

90 pins ran their bundled test, replay and `nfclaw verify` from 2026-11-05 to 2026-11-06, at `a23a092`, on the
engine each `skill.md` names; the last reruns of coproid and marsseq ran on `85313d4`.
[`docs/validation.md`](../validation.md#final-pin-sweep) has the method, the per-job table and what did not come out
clean. In short:

- **Runs.** 88 of the 91 jobs succeeded. seqsubmit needs credentials, and marsseq's two jobs have no result.
- **Replays.** 86 succeeded. sopa's was refused, and reportho's failed twice before a third passed, which the counts
  here leave out. The environment was identical in 82, differs in 1 (sopa) and is `unverified` in 4: mcmicro, circdna and raredisease run tasks with no container, and genomeqc leaves
  no task records.
- **`nfclaw verify`.** It exited 0 for 79 replays and 1 for 7.
- **First attempts.** 69 jobs ended with success, an identical environment and `nfclaw verify` 0 at the first attempt.
  3 of those carry caveats: proteinfold is a stub run, and cutandrun and hicar ignore a failure. So do not read 69
  as free of caveats.
- **Containers.** One job left one behind (drop's first attempt).
- **Output contracts.** tumourevo's and hgtseq's demos passed theirs.

The commits of all 91 jobs match the final pins, except variantbenchmarking, which the updater moved to 1.6.1 once the
sweep had begun; 1.6.1 ran twice on `aea5fa4`, once in each session. No bundle recorded an issue at `a23a092`, although
genomeqc's should have (G16), and so should those of mcmicro, circdna and raredisease (G15). What else it found was
recorded rather than fixed, because these are the pipelines' behaviour and the network's:

- **Files on one side only.** rnafusion, nanostring, longraredisease, mag, spatialaxe, nanoseq and rnasplice have
  known causes, and [the guide lists them](../known-issues.md#pipeline-specific-run-notes). rnasplice's were
  not read this time. coproid's replay lost 25 plot exports under load. That fits MultiQC's 30-second limit on exporting
  them, which fails silently, as a test in that image showed. Rerun on an idle host on `85313d4`, it kept them all and
  `nfclaw verify` exited 0, with no timeout in its log and the whole task taking 27.4 s. That the limit caused the loss
  is strongly supported and still inferred: the logs of the replay that lost them were not kept, and the rerun also differs
  by 16 commits of the runner, none of which mentions MultiQC or its exports. nanostring's four rest only on the same mechanism.
- **Remote files reported as missing.** seqinspector, metatdenovo and drop, in two windows (08:56–09:00 and 15:36–15:42
  UTC). Their reruns were clean. A probe of six such URLs on 2026-11-06, 1,488 requests over 4 hours, got the redirect
  every time, so no window recurred to catch. The cause is not established, and
  [the guide now describes it](../known-issues.md#a-samplesheets-remote-file-is-reported-as-missing-but-it-exists).
- **funcscan's test limit.** A slow download reached the one-hour limit of its `test` profile while still
  progressing, and `--resume` took 11 minutes to finish it.
- **reportho's live databases.** 3 of its 7 launches failed on Ensembl's answers, and two replays failed before a third
  passed. Two `DIAMOND_CLUSTER` tasks stopped exactly 3 minutes after submission, upstream's limit, as another pipeline's
  first tasks spent over four minutes outside their scripts. That an image download slowed the shared volume is unproven:
  one 1.22 GB pull on an idle host slowed a small container by about 1 s at the median and 18 s at worst, and host writes
  barely moved. That was not several pipelines pulling at once, so it does not rule the link out either.
- **The failures cutandrun, hicar and mag ignore.** The [remediation record](2026-11-01-report-remediation.md) asks to
  reproduce and resolve them. All three reproduced, in separate demos that kept the failed tasks' files, on `aea5fa4`
  with the later status changes. `PRESEQ_LCEXTRAP`, `CIRCOS_PREPARE` and `MAXBIN2` each stopped with a message saying
  it had too little to work with, and the pipeline's own configuration tolerates the failure, so nfclaw reports a
  caveat. [The guide quotes them](../known-issues.md#a-successful-run-is-missing-samples). That the demo data is the
  reason is a reading of those messages: the data was not varied to prove it. So this is reproduced and explained,
  not fixed: upstream still tolerates them, and those tasks' results are still missing.

## What this audit did not establish

- **The sweep did not run on the final code.** After `a23a092`, the runner changed in `replay_guard` and `execution`
  (G03), `config_probe` (G14), `environment_record` (G15, G16), `input_safety` (G14), and `orchestration`, `runlog`, `cli`
  and `chain` (G15). Only the [later runs](#evidence) cover those changes, and no second sweep did.
- **marsseq has no result.** The sweep's memory guard stopped its reference build at 2.6 GB available, with STAR and
  Bowtie2 building side by side. Rerun on `85313d4`, one task at a time, it started with 56 GB free and a disk guard
  stopped it at 2.8 GB, 64 minutes and 7 tasks in, in `STAR_GENOMEGENERATE`. Its analysis failed on the missing references
  both times. None of that says anything about the pipeline. What fills the rest of the volume is other work and the
  shared image cache, so this was not forced further. Its [earlier run and replay](../validation.md#provenance-bundles),
  at this same pin, succeeded with an identical environment; the runner has changed since.
- **oncoanalyser did not run.** Its references were deleted on 2026-10-16 and no longer fit. Its last on-host run,
  in [`docs/validation.md`](../validation.md), is at the same commit.
- **A demo is small.** These are bundled test profiles under Docker on one host. Real-scale data,
  schedulers such as SLURM, and analyses that need a GPU were not run. seqsubmit needs ENA Webin credentials.
  Apptainer and macOS ran only in CI's lanes.

## Not changed, and why

- **25 pins are refused by Nextflow 26.04's strict parser** unless a run names `--nxf-ver` or
  `NXF_SYNTAX_PARSER=v1`, and so are 4 of the 19 chain edges. Each refusal names both remedies, and
  each `skill.md` names the engine; choosing an engine silently is what nfclaw refuses to do.
- **A vanished nfclaw cannot remove its task containers.** On Linux Nextflow still gets SIGTERM and
  the wrappers clean up what they can; some can stay behind exited
  (`docker ps -a --filter name=nxf-`), as one did after the chain's SIGKILL on `366c203`. They hold no
  process, as `AGENTS.md` and [`docs/mcp.md`](../mcp.md) say.
- **A configuration probe outlives a nfclaw killed outright.** The fuzz harness killed nfclaw during
  the stalled download above, and that probe's `nextflow config` and `curl` stayed running until
  stopped by hand. A probe normally ends in seconds, and a nfclaw still alive stops it at its bound
  and on a stop, so this needs both SIGKILL and a stalled network.
- **A stop can still leave a container, more rarely.** A client that starts and ends between two looks at the group is
  never seen. So is one whose look is held up by a busy engine, for up to 5 s. Telling a run's containers from another's
  without racing would need matching each container's work directory against the run's own submitted tasks, because a
  name alone does not say whose it is and `NXF_WORK` is shared by default. That is a larger change than this
  audit should make. The price of looking is that a client that never created anything can cost a stop the 30 s wait.
- **A run that fails by itself can leave a container.** One sweep job did (drop's first attempt, 1
  of 91 jobs). On a stop, nfclaw reads the names of the task containers from the commands of the
  run's process group while it is alive. A run that ended by itself has no group left to read, and
  work directories are shared between runs, so nothing tells its container from another run's.
- **Nothing prunes the MCP job store.** It holds what a later session reads; deleting a finished
  job's directory is safe, and the guide now says so.
- **Static-gate notes left alone:** zizmor's pedantic `self-repository` notes; `ruff`'s `S608` on the
  scientific scratch tables (the table name is an internal constant), `S314` on the JUnit reports
  the publisher parses (Python's expat bounds entity expansion), and `S324` on nf-test's own MD5
  snapshots.

## Review before the merge

Two sessions worked on this branch and checked each other. One ran the sweep and repeated the other's real runs; the
other fixed what they found and reran them. That found G15, G16, the second round of G03 and the wording of G14, and
the known issues above. The repeats agreed with the originals: variantbenchmarking 1.6.1 and the `cleanup = true` gap.
An adversarial read of the run log's gap lines tried to forge one through `\n`, `\r`, CRLF, split chunks, VT, FF, NEL
and LS, through a resume and through multi-line output, and found no fault.

## For the release

These are decisions for the maintainer rather than defects: publishing the draft `v1.0.0` release
(its notes date from 2026-10-22 and should gain the bumps and this audit), turning `CHANGELOG.md`'s
**Unreleased** into `1.0.0`, and adding a `date-released` to `CITATION.cff`.
