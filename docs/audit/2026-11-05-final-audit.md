# Final pre-release audit, 2026-11-05

Audited: `8f0f6de` (`main` after #256). Findings are numbered G01–G14, after the A–F series of the
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
  and what each bump did to the audited input roles (G07).
- **Every documented command.** All 304 `nfclaw` command lines in the guides, the README and the
  website, parsed against the real argument parser; every internal link and anchor; every
  `NFCLAW_*` variable against its documentation. No mismatch.

Each finding was reproduced before it was fixed; each fix has a test that fails without it.

## Checklist

| ID | Severity | Location | Finding | Disposition |
|---|---|---|---|---|
| G01 | High | `runner/orchestration.py` (`_input_resume_warning`, `_source_resume_warning`), `runner/provenance.py`, `runner/cli.py` | The bundle is written when a run ends. A nfclaw killed outright (SIGKILL, out of memory, a host restart) or unable to finish it (a full disk) left `--resume` nothing to compare sources and inputs against, so it archived the run and recomputed every task of what may be a days-long analysis. `nfclaw status` meanwhile said "re-run the same command with --resume to continue where it stopped", and the full-disk error "every task is reused from the cache". Reproduced: a real `demo` run, SIGKILL after 4 finished tasks, `--resume`: `-resume` absent from the command, the run moved to `.previous-<id>`, nothing cached. | A launch writes `provenance/launch-record.json` before Nextflow starts: the source identity and the input bytes and namespace it launched with. With no manifest, the resume guards compare against it; a changed source or input still starts fresh, and a damaged record counts as none. The published manifest replaces it, so a finished bundle is unchanged. The same run resumes with its finished tasks cached, no archive; its replay succeeds and verifies with an identical environment. |
| G02 | High | `runner/chain.py` (`_unchanged_handoff`) | The same for a chain: a stage whose nfclaw was killed prepared its handoff again at a new path, and a new input path alone recomputes every task. | The launch record carries the stage's chain link, so the attempt's handoff is found and kept. |
| G03 | Medium | `runner/replay_guard.py` (`remove_task_containers`), `runner/execution.py` (`_terminate`) | A stop while the daemon is still creating a task container: its wrapper's `docker stop` and nfclaw's `docker rm -f` both find `No such container`, the daemon then finishes creating it, and a container that never started is removed by nothing. Six of them stayed behind after one SIGTERM on the loaded server, contradicting "removes the task containers". | The containers the engine does not yet list when the stop begins are looked for until they appear (up to 15 s). Containers already listed are not waited for, so an ordinary stop takes no longer. |
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
| G14 | Low | `runner/config_probe.py`, `runner/input_safety.py` | On a host whose JVM cannot reach GitHub, `--check` said the engine "cannot parse its configuration" and suggested another engine and parser. Nextflow 26.04 prints only `Unable to parse config file` there, and the documented IPv6 flag alone fixes it. Separately, a chain `--outdir` holding only the chain's own record counted as refused, so its links were not looked for, although a chain still writes there. | A failed probe is repeated with remote includes skipped: if that parses, the report names the network and its remedies. A chain's record no longer makes its `--outdir` non-empty. |

## Evidence

Runs, stops, chains, MCP and the CLI cases ran on the server on the fixed tree. The static gates, the
website and part of the packaging ran locally. The per-pin record is
[`evidence/2026-11-05-pin-runs.json`](evidence/2026-11-05-pin-runs.json).

- **Suites.** 4,175 tests, 0 failures, 4 skips, in two runs; `ruff` and the drift check clean. `main`
  before the fixes: 4,129 tests, 0 failures, 4 skips. The 4 skips are audited-commit fixtures that a
  depth-1 clone lacks. GitHub CI on `4821d22`: all 10 pytest lanes (Ubuntu and macOS, Python
  3.11–3.15), website, Nextflow integration, drift, native and Apptainer demos, CodeQL.
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
  with the remedy named.
- **Stops at the worst moment (G03).** Before the fix, 6 containers stayed `created` under load. After
  it, in 4 trials, no container was left and the stops took 8.3–20.0 s.
- **Odd input (G06, G08).** `--outdir /` is refused in 0.6 s, `/mnt/volume` (771 GB in use) in 0.9 s,
  the same in a chain in 2.1 s, and `commands.sh /mnt/volume` in 0.2 s. Of the 115 cases on the final
  tree, 114 end cleanly at once, with no traceback. The other, `NXF_HOME='~nosuchuser/h'`, is Nextflow
  downloading itself into a new home, which stalls on this IPv6-only host; `NFCLAW_CONFIG_TIMEOUT`
  bounds it, and with a 20 s bound it was refused with that cause and left no process behind.
- **MCP, through the official SDK.** 14 tools; a refused job reports its cause; a real job succeeds and
  `nfclaw jobs` agrees; path traversal is refused; replay and verify pass; `cancel_job` took 3 task
  containers to 0.
- **Every pin.** The maintenance smoke step exits 0: all 95 pins pass on the engine their `skill.md`
  names. On Nextflow 26.04.3, 25 of them are refused without `--nxf-ver` or `NXF_SYNTAX_PARSER=v1`,
  as documented.

Pins moved since their last on-host validation, each on the engine its `skill.md` names:

| Pin | Nextflow | Run | Replay | `nfclaw verify` |
|---|---|---|---|---|
| ampliseq 3.1.0 | 26.04.0 | success, 130 tasks | success, environment identical | 1,288 identical, 322 changed |
| bacmodel 1.0.1 | 25.10.4 | success, 2 tasks | success, environment identical | 15 identical, 5 changed |
| detaxizer 1.4.0 | 26.04.0 | success, 54 tasks (on `8f0f6de`) | success, environment identical | 80 identical, 42 changed |
| pixelator 6.0.0 | 25.10.4 | success, 27 tasks | success, environment identical | 21 identical, 97 changed |
| sarek 3.11.0 | 25.10.4 | success, 22 tasks | not run: disk | — |
| sopa 1.0.2 | 25.10.4 | success, 9 tasks | not run: disk | — |
| bacass 2.7.0 | 25.10.4 | stopped by the disk watchdog after 9 tasks | — | — |
| variantbenchmarking 1.6.0 | 25.10.4 | stopped by the disk watchdog after 53 tasks | — | — |

Every verified replay has 0 missing and 0 extra files. Ampliseq's changed files are mostly QIIME2
results and MultiQC reports (257 and 40 of the 322), and pixelator's are its per-stage outputs and
logs. They were not compared one by one.

## What this audit did not establish

- **bacass 2.7.0 and variantbenchmarking 1.6.0 have no complete on-host run at their current
  version.** The server's shared volume ran short: 8 GB free, and each needs more for its images.
  A watchdog stopped both at 3 GB, so neither result says anything about the pipeline. The updater's
  gate ran each bundled test at the pinned commit on a hosted runner, successfully
  (bacass: [run 41837654947](https://github.com/bmds-tue/nf-claw/actions/runs/41837654947),
  variantbenchmarking: [run 41176597064](https://github.com/bmds-tue/nf-claw/actions/runs/41176597064)).
  The same shortage left sarek and sopa without a replay at their current version.
- **Most pipelines did not run again.** The 87 pins that did not move keep the on-host evidence of
  [`docs/validation.md`](../validation.md) at the same commits; the smoke step above checks only that
  each one parses and validates.
- **A demo is small.** These are bundled test profiles under Docker on one host. Real-scale data,
  schedulers such as SLURM, and analyses that need a GPU were not run. Apptainer and macOS ran only
  in CI's lanes.

## Not changed, and why

- **25 pins are refused by Nextflow 26.04's strict parser** unless a run names `--nxf-ver` or
  `NXF_SYNTAX_PARSER=v1`, and so are 4 of the 19 chain edges. Each refusal names both remedies, and
  each `skill.md` names the engine; choosing an engine silently is what nfclaw refuses to do.
- **A vanished nfclaw cannot remove its task containers.** On Linux Nextflow still gets SIGTERM and
  the wrappers clean up what they can; some can stay behind exited
  (`docker ps -a --filter name=nxf-`). They hold no process, as `AGENTS.md` and
  [`docs/mcp.md`](../mcp.md) say.
- **A configuration probe outlives a nfclaw killed outright.** The fuzz harness killed nfclaw during
  the stalled download above, and that probe's `nextflow config` and `curl` stayed running until
  stopped by hand. A probe normally ends in seconds, and a nfclaw still alive stops it at its bound
  and on a stop, so this needs both SIGKILL and a stalled network.
- **Nothing prunes the MCP job store.** It holds what a later session reads; deleting a finished
  job's directory is safe, and the guide now says so.
- **Static-gate notes left alone:** zizmor's pedantic `self-repository` notes; `ruff`'s `S608` on the
  scientific scratch tables (the table name is an internal constant), `S314` on the JUnit reports
  the publisher parses (Python's expat bounds entity expansion), and `S324` on nf-test's own MD5
  snapshots.

## For the release

These are decisions for the maintainer rather than defects: publishing the draft `v1.0.0` release
(its notes date from 2026-10-22 and should gain the bumps and this audit), turning `CHANGELOG.md`'s
**Unreleased** into `1.0.0`, and adding a `date-released` to `CITATION.cff`.
