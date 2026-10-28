# Known Issues & Troubleshooting

Configured Nextflow engine caches and temporary directories must remain outside declared input
directories. The launcher can create framework and Java-version cache entries even while probing
its version. Boundary checks cover `NXF_HOME`, `NXF_DIST`, `NXF_TEMP` and `CAPSULE_CACHE_DIR`
before metadata probes, including inherited settings and relative paths.

Most run-time failures fall into two categories: **environment** (host, network, or path issues — fixable via `nfclaw run` flags or environment adjustments) and **upstream pipeline defects** (bugs in a specific pinned nf-core release). nf-claw keeps pinned pipeline source trees **unmodified**. Upstream defects, recorded runtime corrections and their validation limits are documented here.

### Legacy samplesheet contracts and local data identity

Some pinned schemas omit path formats on consumed reads, references or indexes, or declare them only inside `anyOf`/`oneOf`. The runner applies declared alternative formats to the values they match. Additional file roles are documented in [`runner/input_roles.json`](../runner/input_roles.json), keyed by the original schema's SHA-256 and supported by source references. Handwritten sheets and handoffs receive the same local path checks, input hashes and namespace capture as generated sheets. Metadata such as Nanostring's `RCC_FILE_NAME`, and absence sentinels such as Bacass's `NA` and Isoseq's `none`, are preserved as literal values.

HGTseq's pinned 1.1.0 consumer reads `sample,input1` and optional `input2`, while its template lists `fastq_1`/`fastq_2`. Nanoseq 3.1.0 requires `group,replicate,barcode,input_file,fasta,gtf` in that order. The runner and generated documentation correct these stale contracts using the exact pinned consumer source, without editing upstream files. Automatic generation is refused because these formats require explicit data-role, barcode, replicate or reference assignments. Corrections apply only at the audited revision, and a changed consumer source there is refused; another release (an older one run with `--pipeline-version`, or a newer pin) keeps the contract its own schema declares until it has its own reviewed contract. The pinned consumers continue to enforce extension compatibility, replicate grouping and their other runtime constraints.

The audited roles also cover directory-valued sources (including Methylong POD5 inputs and microscopy datasets) and auxiliary reference sheets. Oncoanalyser FASTQ `filepath` values contain exactly two nonempty semicolon-delimited paths; both are validated, normalized during handoffs and hashed independently. `group_id`, `subject_id` and the `library_id`, `lane`, `flowcell` info values must be literal safe aliases. Info keys use the consumer's uppercase normalization. An apostrophe in `read_group_overrides` is unsupported by the pinned single-quoted BWA argument and is refused. Datasync `output_path` locations are destinations rather than consumed inputs. The composite interpretation and destination exclusion require the exact audited revision and source hashes.

Datasync passes complete source and destination strings into double-quoted command arguments. The runner refuses double quotes, backslashes, dollar signs, backticks and control characters anywhere in those strings, including parent folders. Destinations are not required to exist or inspected as input directories; apostrophes remain supported by that quoted argument.

Some upstream consumers infer companion files that are absent from the samplesheet (for example, Sarek's SnpSift database index defaults to `vcf.tbi`). Input hashes cover explicitly named paths; they do not comprehensively discover these inferred dependencies. Supply index paths explicitly where the consumer supports them, and preserve the complete reference dataset for reproducibility.

Runs and handoffs share the same declared and conservatively discovered local dependencies. A sheet mixing declared paths with pattern-only reads records both sets, so restoring producer bytes cannot mask different data captured by the consumer. Equal filename patterns do not establish a metadata role: an unformatted second mate remains a data path even when its first mate has a path format. Nanostring's `RCC_FILE_NAME` exclusion instead requires its exact audited revision and consumer hashes, and applies to input capture and handoff derivation. Untyped absolute existing-file values without a proven exclusion are recorded conservatively; this is dependency attribution, not proof that an analysis task read every recorded file.

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
  - Keep the repository space-free and set a space-free work directory: `--nxf-env NXF_WORK=/a/space-free/dir`, and use a space-free `--outdir`.
  - Or, if you know your pipeline tolerates spaces, pass `--allow-spaces` to bypass the preflight check.

### IPv6-only host — JVM can't reach GitHub
- **Symptom:** `java.net.SocketException: Network is unreachable` while Nextflow downloads `https://raw.githubusercontent.com/nf-core/configs/master/nfcore_custom.config`.
- **Why:** The host has no default IPv4 route; the JVM prefers IPv4 by default and never attempts IPv6.
- **Fix:** `--nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true`. To skip remote config fetches entirely (offline): `--nxf-env NXF_OFFLINE=true`.
- **Dual Requirement on IPv6 Hosts:** On an IPv6-only host you usually need BOTH this *and* the [Docker host-network config](#docker-bridge-network-has-no-dns-ipv6-only-host) together: the JVM flag fixes Nextflow's own GitHub download, while host-network fixes DNS *inside* containers — neither alone is sufficient:
  ```bash
  nfclaw run <name> --nxf-env NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true \
                    --config host-net.config …
  ```

### No network at run time — a tool downloads a database
- **Symptom:** A step (e.g. BUSCO) hangs then fails trying to fetch a database it requires.
- **Fix:** Supply the step's database locally through the pinned release's declared parameters, or deliberately skip that analysis if the release supports it. Where `reference.md` declares `skip_busco`, use `--skip-busco true` (or `{"skip_busco": true}` via `--params-file params.json`). Skipping a step changes the analysis; `NXF_OFFLINE` does not prevent tools inside containers from attempting downloads.

### A process requests more memory than the host has — aborts before any work
- **Symptom:** A run aborts at scheduling time because a single step requests more RAM than the machine has, e.g. `Process requirement exceeds available memory -- req: 80 GB; avail: 62.8 GB`. Seen with `detaxizer` 1.3.0 run with `--classification_bbduk`: its `BBMAP_BBDUK` step carries nf-core's `process_high` label, which `conf/base.config` sizes at `80.GB * task.attempt` — more than a typical workstation or small VM has.
- **Why:** An nf-core `base.config` sizes each process by a resource *label* (`process_low/medium/high/high_memory`) tuned for an HPC cluster; one high-memory step can exceed a small host's physical RAM, and Nextflow refuses to schedule a task it knows cannot fit.
- **Fix:** Put a ceiling on the whole run with `--limit-cpus` / `--limit-memory`, sized to the host machine:
  ```bash
  nfclaw run rnaseq --input ss.csv --outdir results -profile docker \
    --limit-cpus 4 --limit-memory 15.GB
  ```
  nfclaw writes these as Nextflow's [`process.resourceLimits`](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#set-max-resources), the mechanism nf-core prescribes, so one ceiling covers every process and every retry and is replayed from `<outdir>/provenance/resource_limits.config`; [AGENTS.md](../AGENTS.md) has the details, including `--limit-time`.

  A named override sizes only its own process, so it cannot stand in for that ceiling: you would need one for every step that might exceed the host (`STAR_GENOMEGENERATE`, then `BBMAP_BBSPLIT`, then the next). Use `withName` (via `--config`) only to tune one specific step, e.g. giving a tool *less* than its label implies:
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
  Confirmed-affected releases that **do** run with `--nxf-ver 25.10.2` include `hgtseq`, `callingcards`, `coproid`, `denovotranscript` 1.2.1, `chipseq` 2.1.0, `atacseq` 2.1.2, `circdna` 1.1.0, `detaxizer` 1.4.0 (and 1.3.0) and `marsseq` 1.0.3, plus the earlier, non-pinned releases `epitopeprediction` 3.1.1, `fastqrepair` 1.0.0 and `genomeassembler` 1.1.0 (`--pipeline-version`). Newer releases — including the pinned `epitopeprediction` 3.2.0, `fastqrepair` 1.1.1, `genomeassembler` 2.0.0, `fetchngs` 1.13.0, `sarek` 3.11.0 (and 3.10.0) and `scrnaseq` 4.2.0 — declare `!>=25.10.4`, so use `--nxf-ver 25.10.4` to avoid Nextflow 26 strict parser failures on them.

  Examples of what NF 26 rejects:
  - chipseq's **and** marsseq's `def check_max(obj, type)` in `nextflow.config` (marsseq 1.0.3 declares only `!>=23.04.0`, so unpinned it parses under NF 26 and fails at launch with a `nextflow.cli.Launcher` error — `--nxf-ver 25.10.2` fixes it; note its `test` profile also sets `genome = 'mm10'`, which expects prebuilt local references; its configuration maps that key to GRCm39/M27, not AWS iGenomes).
  - scrnaseq 4.1.0's `Invalid include source: conf/test_multiome.config` (the `test_multiome` profile `includeConfig`s a file not committed at the tag — NF 26 validates it at parse time even though the profile is unused, while the legacy parser skips it and the `--demo` run completes).
- **Exception — a release that needs an _older_ engine:** cutandrun 3.2.2 fails before any task with `Cannot invoke method optional() on null object` on Nextflow **25.10.0, 25.10.2 and 25.10.4** (26.04 already fails to parse its configuration, as above), from the deprecated output syntax `emit: html optional true` in `modules/local/for_patch/trimgalore/main.nf` (sibling modules already use current `emit: …, optional: true`). Nextflow 25.04.8 and older accept it: its `skill.md` names `--nxf-ver 23.04.0` (its declared minimum), with which the [validation](validation.md) run completed, and its bundled test also completed on 25.04.8 (Linux, Docker).
- **Exception — some releases need a _newer_ engine:** `funcscan` 4.0.0 and `lsmquant` 1.0.3 declare `nextflowVersion = '!>=25.10.4'`, so Nextflow rejects `--nxf-ver 25.10.2` at its version gate (`Nextflow version 25.10.2 does not match workflow required version: >=25.10.4`, on stderr); nfclaw's error names the fix: use `--nxf-ver 25.10.4`. (`bactmap` 1.0.0 also needs the test-data and module-option workarounds in the upstream table; with those, its test completed on 24.10.5).
- **In a chain (`nfclaw chain run`):** Pin the engine on that stage only — `"nxf_ver": "25.10.4"` in its spec entry — since other stages may need a newer one (fetchngs 1.13.0 requires `>=25.10.4`, mag 5.5.0 `>=26.04.0`). The chain parses every stage's config with its own engine (`nextflow config`) before the first stage launches, so this fails up front, not after the stages before it have run. Seen in chains on Nextflow 26.04.3: `atacseq` 2.1.2 (`def check_max`) and `viralrecon` 3.0.0 (`Invalid include source: conf/test_full_sispa.config`, a profile file missing at the pinned commit) — both parse with `"nxf_ver": "25.10.4"`.

### An engine older than 21.10.0 fails on Java 17: `Unsupported class file major version 61`
- **Symptom:** with an old engine pinned (bactmap 1.0.0 declares `!>=21.04.0`), Nextflow stops before reading the pipeline: `Project config file is malformed -- Cause: Compile failed …` caused by `java.lang.IllegalArgumentException: Unsupported class file major version 61`.
- **Why:** Java 17 support arrived in Nextflow 21.10.0. Verified on OpenJDK 17.0.20: `nextflow config` of a pinned pipeline fails on 21.04.0 and succeeds on 21.10.3.
- **Fix:** `nfclaw run` now refuses such a pin on Java 17+ before launching and names a later engine; the generated `skill.md` of a release whose declared minimum predates 21.10.0 recommends `--nxf-ver 24.10.5` (the engine the acceptance gate checks those releases on) instead of that minimum. To run the old engine itself, point `NXF_JAVA_HOME` at a Java 11 installation.

### BUSCO finishes, then the task hangs until its time limit
- **Symptom:** A `BUSCO_BUSCO` task (mag, and any pipeline running BUSCO 6) is killed at its time limit — Nextflow reports `process hasn't exited` — although its `.command.log` shows BUSCO's results and "Total running time: 6 seconds" hours earlier.
- **Why:** BUSCO 6 collects anonymous run statistics when it ends ("You may opt out with --opt-out-run-stats"): it looks up the host's country at `ipinfo.io` and posts the statistics to `busco-data.ezlab.org`, both without a timeout. If that HTTPS exchange cannot complete from inside the container, the task waits on it indefinitely — on the VM where this was seen, because [Docker's MTU exceeded the host's](#downloads-inside-task-containers-stall-dockers-mtu-is-larger-than-the-hosts) (the lookup answered at once from a container on a network with the host's MTU).
- **Fix:** Opt out through a config given with `--config` (in a chain: the stage's `"config"`):
  ```groovy
  process {
      withName: 'BUSCO_BUSCO' {
          ext.args = { (params.busco_db ? '--offline ' : '') + '--opt-out-run-stats' }
      }
  }
  ```
  (mag's own `ext.args` is `--offline` when `--busco_db` is given; the closure preserves it.) Pipelines that include the module under another name need that name: genomeqc 1.0.1 runs it as `BUSCO_GENOME` and `BUSCO_PROTEIN`, which set no `ext.args`, so `withName: 'BUSCO_GENOME|BUSCO_PROTEIN' { ext.args = '--opt-out-run-stats' }`. Fixing the container network instead ([MTU](#downloads-inside-task-containers-stall-dockers-mtu-is-larger-than-the-hosts)) needs no per-pipeline config.

### Docker bridge network has no DNS (IPv6-only host)
- **Symptom:** Containers cannot resolve hostnames; downloads inside a container fail even though the host has connectivity. Docker's default bridge uses IPv4 DNS `8.8.8.8`, unreachable on an IPv6-only host.
- **Fix:** Give containers the host network via a config file passed with `--config`. `docker.runOptions` is a single string that a `--config` **replaces** (it does not merge with the pipeline's value), so preserve nf-core's default user mapping in the same string — otherwise the container reverts to running as root and outputs become root-owned:
  ```groovy
  // host-net.config — host network + nf-core's default user mapping
  docker { runOptions = '--network host -u $(id -u):$(id -g)' }
  ```
  Run with `nfclaw run <name> --config host-net.config …`.
- **Also when the bridge has DNS:** a bridge configured with IPv6 and an IPv6 DNS server can still leave older runtimes resolving a name to its IPv4 address only. funcscan 4.0.0's `DEEPARG_DOWNLOADDATA` (deepARG 1.0.4, Python 2.7) resolved Zenodo to IPv4, timed out in the TLS handshake and stalled for 35 minutes, while `curl` on the host reached Zenodo over IPv6. Stopped and resumed with the host-network config above, the download completed in 23 minutes and the run succeeded with its cached tasks reused. Names with no IPv6 address at all, which the host reaches through DNS64/NAT64, cannot be resolved from the default bridge either: genomeqc 1.0.1's `REPEATMASKER_DOWNLOADDB` failed with `curl: (6) Could not resolve host: www.dfam.org`, and completed when resumed with the host-network config. A day later the host's own DNS64 resolver answered `SERVFAIL` for `www.dfam.org`, although its CNAME target `nginx.systemsbiology.net` resolved. Nextflow then could not stage rnafusion's Dfam files (`No such file or directory: https://www.dfam.org/…`). Files fetched with `curl --resolve www.dfam.org:443:[<that target's IPv6 address>]` and passed as `--dfam-hmm`, `--dfam-h3f`, `--dfam-h3i`, `--dfam-h3m` and `--dfam-h3p` matched the published sizes. genomeqc 1.0.1 hit the same failure later (`REPEATMASKER_DOWNLOADDB`, `curl: (6) Could not resolve host: www.dfam.org`). Its own offline option avoids the download: fetch `dfam39_full.0.h5.gz` and its `.md5` the same way, check the MD5, `gunzip` it, and pass the `.h5` file as `--famdb-library`.

### Java tools in containers prefer IPv4 (IPv6-only host)
- **Symptom:** a Java task that contacts a server fails with `java.net.ConnectException: Network is unreachable`, even with the host-network config — e.g. pathogensurveillance 1.1.0's `BBMAP_SENDSKETCH`, which sends a sketch to JGI's server.
- **Why:** the JVM tries a name's IPv4 address first unless told otherwise, and a host without IPv4 egress cannot reach it. (nfclaw's `NXF_JVM_ARGS=-Djava.net.preferIPv6Addresses=true` advice covers Nextflow's own JVM, not the JVMs inside task containers.)
- **Fix:** set the preference for that process's container through `--config`:
  ```groovy
  process {
      withName: 'BBMAP_SENDSKETCH' {
          containerOptions = '-e JAVA_TOOL_OPTIONS=-Djava.net.preferIPv6Addresses=true'
      }
  }
  ```
  With it, pathogensurveillance's `BBMAP_SENDSKETCH`, which had failed every attempt, completed on resume.

### Python tools cannot download `ftp://` URLs (IPv6-only host)
- **Symptom:** a Python task that fetches an `ftp://` URL fails even with the host-network config — e.g. coproid 2.0.1's `SAM2LCA_UPDATEDB`: `Download of taxonomy files failed. NCBI's server may be offline.` (taxopy downloads `ftp://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz`), while `curl` fetches the same URL on the host.
- **Why:** Python's `urllib` FTP handler resolves the server with `socket.gethostbyname`, which returns IPv4 addresses only (`OSError: [Errno 101] Network is unreachable`). `ftplib` itself works over IPv6 (EPSV); only the `urllib` route is IPv4-bound.
- **Fix:** `urllib` honours `ftp_proxy`. Run a small HTTP proxy on the host that fetches `ftp://` URLs with `curl`, and pass it to that process together with the host-network config:
  ```groovy
  process {
      withName: 'SAM2LCA_UPDATEDB' {
          containerOptions = '-e ftp_proxy=http://127.0.0.1:38128'
      }
  }
  ```
  With such a proxy, coproid's bundled test, resumed with the host-network config and this one, completed. Avoid ports already taken by a host proxy (here `tinyproxy` held 3128 and answered `403 Filtered`).

### sra-tools cannot reach NCBI (IPv6-only host)
- **Symptom:** `SRATOOLS_FASTERQDUMP` or `SRATOOLS_PREFETCH` fails with `Failed to call external services` (exit status 64) after its retries, also with the host-network config, while `curl` on the same host reaches NCBI.
- **Why:** sra-tools 3.0.8 (ncbi-vdb) connects over IPv4 only. Traced on such a host, `srapath` opened only IPv4 sockets — 244 attempts to NCBI (`130.14.29.113:443`) and its cloud-metadata probe (`169.254.169.254`), each refused with `ENETUNREACH` — and exited 3. No configuration of the container changes this.
- **Fix:** fetch the runs' FastQ files from ENA over HTTPS — the ENA portal's `filereport?accession=<run>&result=read_run&fields=fastq_ftp,fastq_md5` lists them and their MD5 sums — and give the pipeline local paths instead of accessions. This affects pathogensurveillance's bundled test (its sample `SRR18850314` is an NCBI accession) and any pipeline that falls back to sra-tools (fetchngs' `SRATOOLS_PREFETCH` route).

### Downloads inside task containers stall: Docker's MTU is larger than the host's
- **Symptom:** A step that downloads from inside its container hangs until its time limit or fails with `The handshake operation timed out` / `Read timed out`, although the same URL downloads at full speed on the host. Seen on a cloud VM (de.NBI OpenStack, link MTU 1450) for DeepARG's database from Zenodo (`funcscan`), sam2lca's NCBI taxonomy (`coproid`), and BUSCO 6's run-statistics lookup at `ipinfo.io` (the [BUSCO hang](#busco-finishes-then-the-task-hangs-until-its-time-limit)). Downloads Nextflow stages itself (remote inputs, test data) are not affected: the JVM runs on the host.
- **Why:** Docker's default bridge uses MTU 1500; on a VM whose network link is smaller (overlay networks often use 1450), full-size packets to a bridged container are dropped without the "packet too big" reply that would shrink them. Connections open, but any response larger than one packet — a TLS certificate chain, a file — never arrives. Check with `ip link show` (host interface vs `docker0`).
- **Fix:** Match Docker's MTU to the host: `"mtu": 1450` in `/etc/docker/daemon.json` (the bridge) or `--opt com.docker.network.driver.mtu=1450` on a user-defined network, then restart Docker. Without changing the daemon, give task containers the host network with the [host-net config above](#docker-bridge-network-has-no-dns-ipv6-only-host). With either, the downloads above completed on that VM; on its default 1500-MTU bridge they hung.

### A container creates root-owned files that block publishing
- **Symptom:** A step writes a file/dir owned by root with restrictive permissions, and Nextflow — running as your user — cannot read or publish it. Examples: `CUSTOM_SRATOOLSNCBISETTINGS` and `macrel` (mode `600`), or STAR in `rnaseq` (`_STARgenome/` / `_STARpass1/` as `drwx------`, failing with `AccessDeniedException`).
- **Why:** nf-core's `docker` profile maps your host user into the container (`docker.runOptions = '-u $(id -u):$(id -g)'`). Any `--config` that sets `docker.runOptions` **replaces** this value rather than adding to it, causing containers to fall back to root.
- **Fix:** Keep the user mapping folded into the same `runOptions` string in your `--config`:
  ```groovy
  // run-as-user.config
  docker { runOptions = '-u $(id -u):$(id -g)' }
  ```
  Keep `$(id ...)` inside single-quoted Groovy strings so the task shell expands it; double quotes cause a config parse error. Alternatively, hardcode numeric ids (`id -u` / `id -g`): `docker { runOptions = "-u 1000:1000" }`.

### Numeric parameters can change before Nextflow receives them
- **Status: Fixed at the wrapper boundary.** Binary-float conversion changed `9007199254740993e0` into `9007199254740992`, changed `0.1000000000000000000001` into `0.1`, and underflowed `1e-9999` to zero. Converting the float `1e23` directly to an integer also emitted `99999999999999991611392` rather than the JSON value `100000000000000000000000`.
- **Behavior:** CLI flags and JSON/YAML parameters retain their decimal value, including nested values and chain records. Precise values are emitted as JSON numbers without quoting or expansion of extreme exponents into digit strings. Plain JSON integer literals outside the signed 64-bit range also wrapped in the tested engines, so those values are emitted with a decimal point to retain their value in Nextflow. Schema enum/type/boundary checks and numeric CSV/TSV bounds compare that emitted value. Non-finite values remain refused. Pipeline engines, validation plugins and scientific tools retain their own numerical ranges and arithmetic precision.
- **Validation:** Independent decimal-text controls check serialization, enum and boundary decisions, YAML aliases, and chain records/fingerprints. Native tasks on Nextflow 25.10.4 and 26.04.0 observe the original numbers from CLI, JSON and YAML and preserve them in standalone replay. Separate nf-schema 2.5.1 and 2.7.2 controls on both engines accept the exact integer enum and exact decimal bounds without changing task-observed values.

### A successful run is missing samples
- **Symptom:** A run (or chain stage) ends `success`, but a sample has no results — e.g. no column in rnaseq's merged count tables.
- **Why:** Pipelines filter samples and tolerate task failures without failing the run. rnaseq skips a sample below its `--min_trimmed_reads` or `--min_mapped_reads` threshold (observed: a public paired-end run whose deposited read 2 was a 4 bp index read lost every pair in trimming), and nf-core's template ends "Pipeline completed successfully, but with errored process(es)" when failed tasks were ignored. Exit zero does not establish that every requested sample or task completed; nfclaw's additional dependency and provenance checks do not establish that completeness either.
- **Behavior:** nfclaw quotes the pipeline's own completion caveats and Nextflow's count of ignored task failures: as warnings after the run, in `nfclaw status` (`status: success — with caveats the pipeline reported about its results`), in `run_manifest.json` (`completion_caveats`) and per stage in the chain log and `nfclaw chain status`. The outcome stays `success`; nfclaw reports what the pipeline said and does not reinterpret it. A pipeline that drops samples without saying so is not detected: compare the samples you supplied with those in the results.

### Intermittent `No signature of method: java.util.LinkedHashMap.subMap() is applicable …`
- **Symptom:** A run fails in a channel operator rather than in a task: `.nextflow.log` shows `groovy.lang.MissingMethodException: No signature of method: java.util.LinkedHashMap.subMap() is applicable for argument types: (String, String, String)`, although the pipeline calls the ordinary varargs `meta.subMap('a', 'b', 'c')`.
- **Observed:** Once among the fastqrepair 1.1.1 native validations on Nextflow 25.10.4 (GitHub-hosted Ubuntu runner, 2026-10-13); the identical job passed in every run before and after it. The stack trace fails inside Groovy's invokedynamic call-site cache (`IndyInterface.fromCache`), not in pipeline or nfclaw code, and no input changed.
- **Fix:** Re-run the same command with `--resume`: completed tasks are reused. If it recurs, report it to Nextflow with the `.nextflow.log` stack trace.

### `--resume` resumed the wrong session
- **Status: Fixed.** `nfclaw run` launches Nextflow **from the `--outdir`**, so each run owns its own `.nextflow/` history and cache. `--resume` resumes *this* outdir's session — it can no longer pick up another pipeline's run. Always use a distinct `--outdir` per pipeline.

### `No space left on device` while writing results or run records
- **Symptom:** Nextflow, provenance recording or a chain state write fails with `No space left on device`; the final outcome may be incomplete if the log cannot be written either.
- **Fix:** Check free space on the output, work, temporary and engine-cache volumes (`df -h`). Free space or choose a larger writable work directory with `--nxf-env NXF_WORK=/path/to/work`. Preserve the existing run and work files needed for `--resume`, provenance checks and replay; moving only the output directory does not relocate recorded external dependencies.

### Existing output aliases can expose input data to execution writes
- **Status: Fixed for explicitly declared local dependencies.** Resolved root paths alone do not establish separation. A run log hard-linked to an external FASTQ shares its bytes, and an output directory can contain a symlink into an external input tree. The production log writer was reproduced appending header text to a hard-linked input fixture.
- **Behavior:** Before locks, logs or pipeline execution, nfclaw inspects existing output namespaces and compares physical file identities with consumed dependencies. It refuses hard links and symlink routes that permit writes into those inputs, including logical input slots beneath output trees whose targets are external. Declared work/cache trees retain their staged-read policy. Refusal logging leaves multiply linked logs untouched even when parameter validation fails before dependency preflight.
- **Validation:** Controlled fixtures preserve input bytes and directory timestamps on refusal. Separate controls retain normal staged file/directory aliases, unrelated hard links and cycle-safe traversal. This preflight checks the filesystem state it observes; independent concurrent changes outside nfclaw's output writer lock remain outside its guarantee.

### A sample sheet or pipeline revision changes during preflight
- **Status: Refused at preflight and launch checkpoints.** A valid sheet changed during the engine probe previously launched the replacement data while recording the original dependency selection. A pipeline checkout changed to another clean commit could similarly record its source hashes under the earlier validated commit.
- **Behavior:** Local primary and auxiliary sample sheets are fingerprinted before validation. Their bytes and namespace must still match after dependency discovery, external probes and launch preparation, including `--check`. Real runs also bind the descriptor fingerprint to the captured input baseline. Pipeline identity and tracked-file cleanliness are rechecked after probes and launch preparation; the captured source revision must equal the validated revision. A changed descriptor or source is refused rather than silently adopting a new selection without validation or write-boundary checks.
- **Validation and scope:** Controlled fixtures replace valid descriptors, retarget them to identical-byte files and switch clean revisions or edit source during preflight and command construction. These are checkpoint comparisons; transient changes restored between checks remain outside their guarantee. Keep descriptors, inputs and source stable throughout preflight and execution.

### A dependency changes while the pipeline is running
- **Status: Detected at completion checkpoints.** On Nextflow 25.10.4 and 26.04.0, a gated task consumed a changed FASTQ while the original wrapper reported success and recorded the old input SHA-256. The mutation preserved the file size and timestamp.
- **Behavior:** Every real run snapshots explicitly declared local inputs, configurations and tracked pipeline source, then compares them after execution. Changed bytes, namespaces, Git revision or unreadable dependencies prevent success. The bundle records the original hashes and a `dependency_stability` report; results remain for inspection. The original engine error is preserved when Nextflow also failed. An invalidated bundle cannot be replayed even after restoring inputs. Resume starts fresh and archives it, since cached tasks can contain results from the intervening data. `--no-provenance` still performs the comparisons. Standalone replay verifies its original bundle again before reporting success.
- **Scope:** This checks observed launch/completion states, not every byte a task read. A temporary edit restored between checks can evade it. Remote inputs and container images are not part of this check; the bundle records them after the run (`environment.json`) and a replay compares its own. Keep inputs and source stable throughout execution; this check establishes neither biological accuracy nor immutability.
- **Validation:** Native gated tasks test input mutations with restored metadata, configuration/source edits, unchanged controls and disabled provenance on both engines. Restoring original input bytes and timestamps after a tainted attempt forces a fresh task, confirmed by an execution counter and the corrected digest; the archive retains the tainted output. Separate replay gates consume changed data and fail their post-execution dependency check. Multiline post-execution errors retain a readable final status line.

### Local-input tasks can reuse stale data after `--resume`
- **Status: Fixed for explicitly declared local inputs.** Ordinary Nextflow file and directory cache keys use path, size and timestamp rather than file bytes ([Nextflow caching documentation](https://docs.seqera.io/nextflow/cache-and-resume)). On both Nextflow 25.10.4 and 26.04.0, a same-size FASTQ byte edit with its timestamp restored reused the old digest result. Directory inputs have an additional recursive namespace problem: Nextflow 25.10.4 and 26.04.0 reuse a cached directory-consuming task after an empty directory is renamed, or after a file in a subdirectory is edited in place (verified: the resumed task republished the old bytes), while the root size and timestamp remain unchanged. File checksums cannot detect the rename, and the namespace cannot detect the edit, so nfclaw checks both.
- **Behavior:** nfclaw records the full directory namespace and the SHA-256 of every declared local input file, including samplesheet data paths, before launch. Unchanged namespace and content preserve normal resume caching; a changed namespace, changed file content or an unavailable previous inventory preserves the previous run in a sibling `<outdir>.previous-<id>` archive, starts a fresh cache session, and recomputes all tasks. This avoids stale publications and fixed report filename conflicts; prior logs are retained and copied forward. Active engine database locks and dependencies overlapping the run directory block archiving. This also applies when the new launch disables provenance. Remote and indirectly configured inputs are outside this preflight's scope. Without a valid historical input snapshot, local-input resumes start fresh because unchanged bytes cannot be established. Whole-file path changes remain subject to Nextflow's own path cache keys.
- **Validation:** Real tasks enumerated `sample_A` before the change and `sample_B` after resume on both engines, with the root timestamp restored. Unchanged resumes reused the cached task. Sample-specific output files proved that old publications stayed in the archive, while a fixed trace filename was successfully regenerated. Standalone replay refused the changed inventory before launching Nextflow. Editing a nested file to same-size content with both directory timestamps restored made the resumed run recompute and publish the new bytes on both engines, and an unchanged follow-up resume reused the cache. Independent SHA-256 and execution-counter controls also verified same-size FASTQ mutations with the file timestamp restored on both engines: changed bytes recomputed, and unchanged inputs with valid snapshots reused the task. When provenance is disabled and no earlier snapshot exists, subsequent resumes recompute instead of trusting metadata. Shared physical file targets are hashed once while logical aliases remain distinct.

### `--resume` kept a removed sample's results
- **Status: Fixed.** Resuming after a sample was removed from the input selection (a hand-written or generated samplesheet) reused the session, and the removed sample's earlier publications stayed in `--outdir` beside the new results. Any change to the recorded set of local input files (added, removed, replaced or retargeted) now starts a fresh session; the previous run moves to a sibling `<outdir>.previous-<id>` archive first. Adding samples therefore recomputes all tasks instead of reusing the earlier ones.

### `--resume` after Ctrl-C or `kill` recomputed every task
- **Status: Fixed.** A run stopped with Ctrl-C or `kill <nfclaw pid>` skipped the post-execution dependency comparison and recorded it as `not_checked`; `--resume` read that as failed attribution, archived the run and recomputed every task, although a run that failed (or was killed with SIGKILL) kept its cache. A stopped run now compares its declared local inputs, configurations and pipeline source when it stops, as a failed run does: unchanged dependencies keep the cache for `--resume`, and changed ones still start a fresh session with the previous run archived. The log keeps the stop as the outcome (`terminated by SIGTERM`, `interrupted`).
- **Validation:** On Nextflow 25.10.4 with Docker, `demo` runs stopped with SIGTERM once their MultiQC task was submitted recorded `unchanged` dependencies and resumed with 7 (bundled remote test data) and 5 (local FastQ directory) cached tasks, no archive and a successful outcome. Regression tests cover both stop signals and a pipeline source edited before the stop, which is recorded as `changed` and makes the resume start fresh.

### A run aborts with `process hasn't exited`

`Caused by: process hasn't exited` (in `.nextflow.log`, `java.lang.IllegalThreadStateException`) means a task ran past its time limit on the local executor. Nextflow before 26.10.0 reads the exit status of the task it has just killed without waiting for it to exit, and the exception aborts the whole run instead of letting the task's `errorStrategy` retry it ([nextflow-io/nextflow#7569](https://github.com/nextflow-io/nextflow/issues/7569), fixed in 26.10.0). The pull of a task's container image counts toward its limit, so test profiles with minute-scale limits trip it on a cold image cache or a busy host. proteinfamilies 2.6.0's `test` profile gives most tasks 2–3 minutes: a fresh `--demo` aborted when a `CLIPKIT` task spent 1.5 of its 2 minutes pulling its image. `nfclaw status` names this cause in its `fix:` line. Re-run with `--resume`; with the image now present, the task usually completes. If it times out again, raise that process's `time` with `--config`, or run on Nextflow 26.10.0 or later, which retries the task instead. Reported to proteinfamilies as [nf-core/proteinfamilies#209](https://github.com/nf-core/proteinfamilies/issues/209).

### `--resume` fails with "Unable to acquire lock on session …"
- **Symptom:** After a run was interrupted (killed/timed out), re-running with `--resume` fails to acquire the session lock.
- **Why:** A hard kill leaves Nextflow's session lock behind; Nextflow refuses to resume because it cannot determine whether the lock is stale or held by a live process.
- **Fix:** Ensure no Nextflow process for that `--outdir` is active, remove the stale lock under `<outdir>/.nextflow/cache/*/LOCK` (or start fresh in a new `--outdir`), and re-run with `--resume`.

### A run in the background: is it still going, and how did it end?
- **Symptom:** A run started with `nohup nfclaw run … &` — its `run.log` has no terminal line, or you need its outcome without opening the file.
- **Fix:** `nfclaw status <outdir>` answers from the log alone: `running (nfclaw pid … on host …)` with the last output; the outcome it ended with and the recorded error; `refused before launch`; or `stopped without an outcome`. Re-run the command with `--resume`. Stop a background run cleanly with `kill <nfclaw pid>` — never `kill -9` — so logs and provenance are finalized.

### Launching several pipelines in parallel
- **Status: Fixed.** Starting 2+ pipelines simultaneously whose submodules were uninitialised previously raced on `.git/config`. `nfclaw run` serializes submodule initialization with a per-repo file lock, ensuring concurrent first-time runs initialize submodules cleanly.

### Replaying a run: `provenance/commands.sh` refuses a target that holds files
- **Symptom:** `commands.sh` refuses its target directory, or a replay into the original `--outdir`
  fails on `pipeline_info/execution_trace_*.txt`.
- **Fix:** Replay into a fresh directory: `commands.sh` defaults to `<outdir>.replay`, or takes a
  target (`./results/provenance/commands.sh /tmp/check-it`); [replay](architecture.md#26-replay--replay-guard)
  explains why a replay cannot publish over the original run.

  Stop it with `kill <replay pid>`. New bundles run the command in its own process
  group, allow the shutdown grace recorded at launch (10 seconds by default), then
  kill surviving group members before closing the log and releasing the writer lock.
  Set `NFCLAW_SHUTDOWN_GRACE` before the original run to record another margin;
  [timeouts](timeouts.md) explains how new and historical replay scripts use it.
  A stopped replay returns a
  nonzero exit status even if the command handles the signal with exit zero.
  Tasks or containers detached from that group still require executor cleanup.

### A replay can change bytes and timestamped metadata filenames
Some outputs embed dates or durations: execution reports, timelines, gzip headers,
FastQC ZIP entries and MultiQC HTML can differ between runs. A changed checksum
does not identify the cause; inspect scientific results with a format-aware comparison.
Matching file inventories alone does not establish analytical agreement. Compare the two with
`nfclaw verify results.replay --against results`; [the verification engine](architecture.md#27-verification-engine-nfclaw-verify)
explains its default and `--strict` checks.

nfclaw pins the schema's `trace_report_suffix` where available, but some upstream
code generates other filenames directly from the clock. For example, demo 1.2.0's
`dumpParametersToJSON()` independently names `pipeline_info/params_<timestamp>.json`.
Every faithful replay therefore has a differently named file, so comparing exact paths
failed every replay of the modern template (demo 1.2.0, ampliseq 3.0.0) and the failure
no longer distinguished a broken replay. `nfclaw verify` pairs these run-metadata names
(the execution report/timeline/trace/DAG of releases without `trace_report_suffix`,
and the nf-co2footprint plugin's launch-stamped report/summary/trace files)
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
- **Why:** `commands.sh` executes `replay_guard.py` to ensure local input files (including paths referenced in samplesheets), configs (the bundle's copies of external `-c` files where it holds them), the archived pipeline source (`pipeline-source.tar.gz`; a bundle without one checks the checkout's commit and tracked bytes) and the recorded `environment.json` / `containers.config` match their recorded SHA-256 digests. New bundles also check directory namespaces, empty directories, entry types and symlink identities against `inputs.inventory.json` and `configs.inventory.json`. A checksum-only prelaunch snapshot cannot certify the original directory namespace and is refused.
- **Fix:** Restore the dependency or bundle artifact named in the diagnostic from an intact original. Replayable config copies are checked inside `provenance/configs/`; editing or deleting their external originals does not invalidate those copies. Configs using `includeConfig` still need the original paths. New source archives allow a changed or missing checkout to fall back to extracted source; older bundles still require their recorded checkout. If input changes are intentional, launch a new run into a new `--outdir` instead of replaying.

### A replay fails after Nextflow succeeded: `execution environment differs from the recording`
- **Symptom:** A replay's run log ends with `failed after Nextflow succeeded (execution environment differs from the recording)`, and the console lists `mismatch:` lines.
- **Why:** After a replay's Nextflow succeeds, `commands.sh` records the replay's own execution environment (`<target>/provenance/environment.json`) and compares it with the original bundle's (`<target>/provenance/environment_check.json`). A process that ran another image digest (an image without a recorded digest cannot be pinned, so its tag may have moved), another set of Nextflow plugins, another container engine, or a remote input whose staged bytes changed (test data on a moving branch, an updated database URL) makes the replay a different execution, whatever its outputs.
- **Fix:** Read the `mismatch:` lines and recover the recorded data or image identity where possible; a mismatch does not establish that recovery is impossible. Keep local copies of remote data needed for future reproduction. `unverified:` lines (an image without a comparable identity, a Singularity image converted on another host) and `note:` lines (another Java runtime, a process that ran in only one of the runs) do not fail standalone replay. Inspect those gaps explicitly; a successful replay need not have an `identical` environment comparison.

### A process cannot be pinned to an image digest
- **Symptom:** `nfclaw run` ends with `provenance: N process(es) are not pinned to an image digest for replay: …` or `provenance: N container image(s) have no recorded identity: …`.
- **Why:** For named Docker/Podman profiles, nfclaw observes task-container start events and inspects image identities while the run is active. Observation is best effort, reinspecting a reused reference after 600 seconds; missing observations fall back to post-run inspection or an earlier attempt's record when available. Locally built images can lack registry digests, a process running several images or containerless tasks has no single pin, and ephemeral Wave references are excluded. Remote executors may leave no image in the local engine. Singularity/Apptainer files are hashed after execution and do not receive registry pins.
- **Fix:** Inspect `environment.json` (`images`, `pinned_containers`, `issues`) and the manifest's `container_pins` entry. `containers.config` is absent when no process qualifies. Unpinned processes retain their original container configuration, which may use tags or local image files; the replay compares the evidence it can obtain. Push locally built images to a registry and reference them by digest when registry pins are needed.

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

### Staging routes and checksum records disagreed about local data
- **Status: Fixed.** Native controls on Nextflow 25.10.4 and 26.04.0 showed that a
  newline or carriage return in a source parent becomes a separate shell line, and
  `directory_symlink/../reads.fastq` can select a different file after Nextflow's
  lexical normalization. Local input paths and resolved targets containing LF/CR
  are refused. Samplesheet routes with differing filesystem and lexical meanings
  are refused; scalar path parameters resolve their parent before staging while
  retaining the basename. Wildcard parents followed by `..` are refused before
  resolution, and glob matches receive the same route checks. LF/CR in launch,
  output or work paths cannot be enabled with `--allow-spaces`.
- Ordinary absolute parent traversal remains supported. Its logical dependency
  keys and resolved identity are retained; relative checksum keys cannot traverse
  outside a bundle. Checksum records use the [GNU escaped filename format](https://www.gnu.org/software/coreutils/manual/html_node/cksum-output-modes.html)
  for backslashes, LF and CR. Readers split records only at LF, so Unicode line
  separators remain filename characters, and reject invalid escapes and decoded
  duplicate keys. Plain legacy records and CRLF record endings remain supported.
- An absolute local parent such as `/path/data://reads.fastq` was also mistaken for a
  remote URL and omitted from input checksums. URI detection now requires a scheme
  at the start of the value. Native execution and relocated replay controls check
  supported backslash/Unicode parents and local colon parents, then confirm that
  changed input content is refused. These are execution and provenance controls,
  not proofs of biological algorithm accuracy.

### `[samplesheet_invalid]` while generating a samplesheet from `--input` data files

`nfclaw run <name> --input <directory | glob | files>` writes the samplesheet from the files and
refuses, before anything is written, whatever it cannot decide from them. Each message names the
files or columns; the fixes:

| Message | Fix |
|---|---|
| `needs values nfclaw cannot take from the files` | Set each listed column: `--sheet-set COLUMN=VALUE` (a constant or a `{sample}`/`{lane}` template). The allowed values are in the message and in skill.md. |
| `takes reads in several column groups` | Empty the groups your files do not belong in, e.g. `--sheet-set long_reads=` for short reads in mag. |
| `hold the two reads of one library …, but their names carry no read number` | Their reads pair, but the names use a convention nfclaw does not parse (`_read1`/`_read2`, `_F`/`_R`). Name or link them `<sample>_R1`/`<sample>_R2`. |
| `read 2 …, but its read 1 file is missing` / `have no mate` | A mate is missing. Restore it, or leave the file out of `--input`. Deliberately mixed single/paired layouts need a hand-written samplesheet. |
| `fit several samplesheet columns` | Empty the column you do not use (`--sheet-set protein=`), or pass only one kind of file. |
| `do not all bring the same kinds of files` | A stray file (a VCF beside FastQ files) became a sample. Narrow `--input` with a glob such as `'/data/*.fastq.gz'`. |
| `Sample names come from the file names, which these do not allow` | nfclaw never renames samples. Rename the files, or link them under names the pipeline accepts. |
| `would repeat the values of …, which the samplesheet requires to be unique` | Several lanes of a sample in a pipeline that takes one row per sample (ampliseq): merge them first. Or make the row key differ, e.g. `--sheet-set run={lane}` (mag). |
| `cannot tell whether … are the two reads of one library` | Bare `_1`/`_2` files pair only when their first read names identify one molecule (Illumina, SRA/ENA or `/1`/`/2` names). With generic names (`read1`), name mates `_R1`/`_R2`, or link separate libraries under names not ending in `_1`/`_2`. |
| `already succeeded, but its --input data now yields a different samplesheet … with files it never analysed` (chain resume) | New data arrived after the stage succeeded, and a resume would skip it. Run the chain on the new data in a fresh `--outdir`. |
| `contains the run's --outdir` / `work directory` | The scan would take the run's own results (on `--resume`) or every task's files as samples. Keep the data directory apart from both; a single result file published into the work tree remains a valid input. |

Files that match no column (checksums, reports, index reads `_I1`/`_I2`, the demultiplexer's
`Undetermined_S0` reads) are ignored and listed before launch. `_R1`/`_R2` files are paired as
named; when their first read names differ (a swapped, truncated or desynchronised mate — what
fastqrepair repairs) the pre-launch advisory says so. Two FastQ files named `x_1`/`x_2`
pair only when their first read names show they are mates; otherwise they are two single-end
samples.

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

### `WARN: Unrecognized config option 'manifest.diagram'`
- **Cause:** Running a Nextflow engine newer than the release targets. Releases built from the current nf-core template set `manifest.diagram` (the path of the pipeline's metro-map image) in `nextflow.config`; the strict config parser of Nextflow 26.04 does not know that option and warns once per launch. Nextflow 25.10.4 prints nothing (verified with rnaseq 3.27.0 on 25.10.4 and 26.04.3). The option only names a documentation image; it changes no parameter, process or result.
- **Fix:** None needed. To avoid the message, run the engine the release declares, e.g. `--nxf-ver 25.10.4`.

### `WARN: Could not load / include the nf-core institutional config` (a host without network access)
- **Cause:** Nextflow could not fetch nf-core's optional remote institutional configuration from GitHub at parse time. sarek 3.11.0 (and 3.10.0/3.9.0) includes it dynamically in `nextflow.config`:
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
- **Cause:** A known defect in the pinned `nf-core-utils@0.4.0` plugin used by sarek 3.11.0 (and 3.10.0/3.9.0). The plugin's validator splits `session.commandLine` on whitespace and incorrectly inspects the launcher binary name `nextflow`. It is benign (`log.warn`, exit 0) and does not affect execution.

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

The exact-pin wrapper corrections are recorded in generated operating notes. HGTseq's bare demo
now stages its immutable historical input/reference recipe; custom input, references, alignment
indexes, data-base selectors, profiles or configs disable that whole recipe. Tumourevo's bare demo
receives the intended `sparsesignatures_k=2:3` with explicit user values preserved; its native
66-task control passed at a 24 GiB task ceiling. These corrections leave upstream sources intact.
The table's explicit commands remain useful when using upstream directly or another revision.

These defects affect specific pinned releases. Workarounds and recorded runtime corrections keep upstream source trees unchanged; generated task scripts may differ when a documented correction is applied:

| Pipeline @ Version | Symptom | Underlying Defect | Recommended Workaround |
|---|---|---|---|
| `bamtofastq` (incl. 2.1.2 / 2.2.1) | `SAMTOOLS_FAIDX ([])` fails immediately | The `test` profile sets `genome = null` + `igenomes_ignore = true`, routing an empty dummy channel into `SAMTOOLS_FAIDX`. | For the exact pinned 2.2.1 commit, `nfclaw --demo` now supplies the matched `chr22:1-40001` FASTA from immutable test-datasets commit `618f1541382c4ad49eff566dadf13d5ccbd0ebb4`, through normal recorded parameters. Explicit reference values override it; supplying your own input disables this demo default. Other releases and direct upstream execution still require an explicit matched `--fasta` / `--genome`. Fresh corrected demo and replay each completed 32 tasks on Nextflow 25.10.4; both preserved all primary read identities, strand-corrected sequences and qualities: 2,821 and 2,718 pairs. See [audit progress](audit/2026-10-26-progress.md) for retained evidence. |
| `bacass` 2.6.1 (Unicycler) | Reported earlier: `SyntaxWarning: invalid escape sequence '\d'`, then a failure on Python 3.12 | Attributed to Python code in the `unicycler:0.5.1` container not updated for 3.12. | **Not reproduced on the pinned release:** its bundled test (`community.wave.seqera.io/library/unicycler:0.5.1--b9d21c454db1e56b`) completed both Unicycler assemblies on Nextflow 25.04.0 with Docker (Linux amd64) without that warning — 2.92 Mb in 469 segments (N50 64.6 kb) for ERR064912 — followed by Prokka and BUSCO. Should it occur in another environment, `--assembler megahit` avoids Unicycler. |
| `createtaxdb` 3.1.0 (sourmash enabled, as its `test` profile does) | a task fails with `java.util.ConcurrentModificationException` while Nextflow resolves its inputs (seen at `FIND_CONCATENATE_AA` and `METACACHE_BUILD`) | `SOURMASH_CREATE` sorts the genome list it receives with Groovy's in-place `sort()`. That list comes from `groupTuple` and is the same object `FIND_CONCATENATE_*`, `METACACHE_BUILD` and the other database builders receive, so Nextflow can be iterating it for one of them while it is reordered ([nf-core/createtaxdb#138](https://github.com/nf-core/createtaxdb/issues/138)); builders that do run can receive the genomes in either order. Fixed on `dev` by [#202](https://github.com/nf-core/createtaxdb/pull/202) (Nextflow 26.04's `groupBy`), not in a release. | For the exact pinned commit, `nfclaw run` now applies the recorded [copy-sort source correction](source-corrections.md) while preserving the original upstream tree. Corrected original/replay each completed all 31 configured builders with DNA/protein Sourmash enabled, a predecompressed MALT map and symlink publication. Full Sourmash signatures and exact-query searches agreed. Other database/report differences remain unassessed; this does not establish overall database equivalence. Direct upstream execution still has the race; disabling both Sourmash builders avoids that branch while omitting those databases. |
| `fastqrepair` 1.1.1 | healthy reads disappear at split boundaries; singleton publication can be empty although the pipeline succeeds; a single chunk fails the run (`fastqwiper -i <path component>`); gathered reports understate repaired headers | Wipertools 1.1.5 splits lines or bytes rather than complete FASTQ records. The subworkflow iterates each file's chunk list, so a single chunk (a path) is iterated by name component, which also fails `--num_splits 1`; fastqwiper fails on an empty chunk (its report divides by the line count). `reportgather` keeps only the last digit of each `of which N fixed` count (12 + 12 is reported as 4). The BBMap task also omits a shell continuation before `qin`, so that option and log redirection miss the real command. Its publisher maps the log onto the singleton filename; some paired wipe reports also share a publication name. | For the exact affected commit, nfclaw records a compatibility config. It resolves each publication mode per task, which only Nextflow's legacy config parser can express, so nfclaw runs it with `NXF_SYNTAX_PARSER=v1` (recorded and replayed; every engine through 26.10 provides that parser) and refuses an explicit `v2`. Its splitter cuts only before a clean header that follows three printable non-blank lines without `@`: under fastqwiper's line rules no record spans such a line, so the gathered chunk wipes equal one whole-file wipe, reads and report, for any `--alphabet`. Input without such a line (a single read; qualities full of `@`) is wiped whole beside a zero-byte placeholder chunk, which the patched wiper task answers with an empty output and a zero report. Reports are summed exactly; percentages in zero-count placeholder reports are marked not applicable. The config also restores the samplesheet's original mate order: the upstream gather groups mates by task arrival, which can swap streams whose read names lack mate suffixes. Paired runs skipping BBMap otherwise overwrite both mates under one sample filename; nfclaw publishes them separately. It passes the declared quality offset and separates singleton reads, logs and mate reports. Supply one row per sample, distinct staged filenames and matching compression formats. Profile/config-only input is accepted for paired repair only if every gathered record consistently identifies its mate; skipped pairing requires a local samplesheet to verify publications. The embedded splitter checks that input bytes did not change between its two passes and records its source SHA-256 as its tool version. Recipe-specific internal prefixes invalidate old task caches while published sample identities stay unchanged. Earlier nfclaw versions kept damaged input in one chunk, so such runs failed at the wiper. Inspect the generated config and actual `.command.sh` files; the pinned source tree is not edited. Independent known-input pairing, whole-file wipe and replay controls must pass before treating these corrected outputs as validated. |
| `hgtseq` 1.1.0 | the bundled schema and generated instructions named columns the consumer does not read | The unused template lists `sample,fastq_1[,fastq_2]`, while `workflows/hgtseq.nf` requires `sample,input1[,input2]`. | nfclaw's source-audited correction now validates and documents the actual pinned consumer contract. Supply absolute `input1` and optional `input2` paths in a handwritten sheet; local data are checked and hashed. The consumer accepts `.fastq`/`.fastq.gz`, `.bam` or `.cram` for `input1`; paired FASTQ inputs require matching extensions and BAM/CRAM cannot have a second mate. The correction applies only at this exact revision with unchanged consumer source; other releases keep the contract their own schema declares. This validates the input interface and dependency identity; it does not establish biological HGT inference accuracy. |
| `hgtseq` 1.1.0 (bundled `test` profile) | `--demo` stops at once: `ERROR: Please check input samplesheet -> a column named input1 with either fastq or bam/cram input is mandatory!` | The test profile reads `input_fastqs.csv` from nf-core/test-datasets' moving `hgtseq` branch, which was rewritten in November 2025 to `sample,fastq_1,fastq_2` for newer hgtseq code; the pinned 1.1.0 consumer still reads `input1`/`input2`. | Pin the test data to the last commit before that change, [`800330ec`](https://github.com/nf-core/test-datasets/tree/800330ec8f47c93caabe8157e20dd23e243de4e1): pass its `testdata/csv/input_fastqs.csv` (with the FastQ URLs rewritten to that commit) as `--input`, and `--gff` its `testdata/reference/Homo_sapiens.hg38.chr21.gff3`, alongside `--demo`. The FastQ files themselves are unchanged since 2022. With these, the bundled test completed on Nextflow 22.10.1. |
| `nanoseq` 2.0.0 – 3.0.0 (with `--pipeline-version`) | the published schema calls the scalar `--protocol` a samplesheet file | These releases' `nextflow_schema.json` declares `--protocol` (`DNA`, `cDNA` or `directRNA`) as a `file-path` carrying the input samplesheet's `schema`; their legacy validator ignores both, and the pinned source only compares the value with those literals. Taken at its word, the schema would make nfclaw resolve the value as a path and refuse it as a missing samplesheet. | nfclaw applies a source-audited value role ([`runner/param_roles.json`](../runner/param_roles.json), bound to each release's schema digest and exact commit), so `--protocol` is passed as written for exactly these releases. Another revision or an edited schema keeps the published annotations, and an edited consumer is refused by the pipeline-integrity check before launch. The pinned 3.1.0 declares a `sample-type` format, which nfclaw reads as a value. |
| `funcscan` 2.1.0 – 4.0.0 (DRAMP DB only) | `TypeError` in the AMPcombi DRAMP downloader (`amp_database.py` in 3.0.0) | The loop regex matches NaN floats when sequence cells are empty. An actual 3.0.0 container control reproduces it; the complete 2026-10-27 official data has no missing sequences. APD is unaffected. | Use the explicit [recorded DRAMP preparation and pinned-image index recipe](dramp-reference.md), then supply `--amp-ampcombi-db-id DRAMP` and `--amp-ampcombi-db /path/to/amp_DRAMP_database`. Funcscan 4.0.0 needs `--nxf-ver 25.10.4`. |
| `taxprofiler` 2.x (MultiQC 1.34) | `MULTIQC` fails: `AttributeError: module 'rich' has no attribute 'panel'` | MultiQC raises `IndexError` on empty MetaPhlAn profiles, followed by a secondary failure in error reporting. | Profile reads that match database content, or disable MetaPhlAn: `--run_metaphlan false`. |
| `bactmap` 1.0.0 | direct upstream demo cannot stage its moving reference; its test profile loses module defaults and preview waits forever for MultiQC | The moving branch removed the matched reference. The test module block replaces the default map, and completion reads a report future that preview never binds. Native controls also exposed read-order variation with multiple CPUs and unsorted pseudogenome collection. | For exact commit `834642d8ac150ca10d705833223e7bcf15efc210`, `nfclaw run` uses a recorded [source correction](source-corrections.md) preserving module defaults, sorting the alignment inputs, seeding the test's IQ-TREE/RAxML tasks and skipping the report wait only during preview. A bare demo stages all three original paired samples and the matched NCTC13799 reference from immutable [test data](https://github.com/nf-core/test-datasets/tree/02195cfa96ca496173e9d63dd58e34bf02fcf55a), defaulting to `max_cpus=1`; explicit CPU values win. Explicit input/reference, extra profiles or configs disable the fixture. Fresh native original/replay each completed 47 tasks, with identical alignment content, variant records, pseudogenome sequences and four tree files. These are fixture consistency checks, not an accuracy benchmark or a general determinism guarantee. [Assessment and failed controls](audit/2026-10-26-progress.md#u06-bactmap-matched-data-preview-and-replay). Direct upstream execution omits these corrections. |
| `createpanelrefs`, `proteinfamilies`, `stableexpression` (pinned releases) | default `-preview` acceptance times out | Nextflow's workflow-output completion code waits for values that preview never produces; this was reproduced on the declared 26.04.0 engine and 26.04.6, and for stableexpression 1.1.0 on its declared 26.04.4, where a thread dump shows `workflow.onComplete` blocked in `OutputDsl.getOutput` after "Pipeline completed successfully". | A preview-only config with `workflow.output.enabled=false` permits createpanelrefs graph validation. For proteinfamilies, set the bundled `params.skip_proteinfold_samplesheet=true` and `params.skip_proteinannotator_samplesheet=true` as Groovy booleans in a config. With `workflow.output.enabled=false`, stableexpression's preview completed in 12 seconds. These variants completed, but output publishing is excluded from preview validation. Keep their default previews rejected. The unchanged bundled test analyses subsequently completed on native amd64 with Nextflow 26.04.0, including publishing ([createpanelrefs execution](https://github.com/bmds-tue/nf-claw/actions/runs/37922299422), [proteinfamilies execution](https://github.com/bmds-tue/nf-claw/actions/runs/37922302411)); stableexpression's bundled test completed end to end on Nextflow 26.04.4 and matched its nf-test snapshot ([validation](validation.md#releases-bumped-or-added-after-the-sweep)). Independent controls checked createpanelrefs target coverage coordinates and finite numeric metrics for two normal samples; the antitarget BED and coverage tables were empty, so their checks establish an empty inventory rather than nonempty antitarget coverage. Proteinfamilies retained all member residues, preserved family/HMM inventory and matched representative sequences or declared source subdomains. These controls do not establish CNV calling accuracy or optimal protein family inference. |
| `multiplesequencealign` 1.1.1 | default `-preview` acceptance times out | Its own completion handler waits on `summary_reports.getVal()`; preview cannot produce the required process results. A newer engine does not resolve this dependency. | The unchanged official `test_tiny,docker` profile completed all 78 tasks on the declared Nextflow 25.04.2, using a matched immutable test-data snapshot. FAMSA, MAFFT and consensus outputs preserved all sequence IDs and ungapped amino-acid sequences; all six summary rows had finite configured metrics. This covers the tiny profile's two aligners and completion lifecycle, not every aligner or biological alignment accuracy. The default preview remains rejected. |
| `multiplesequencealign` 1.1.1 (full `test` profile) | Docker exits 125 at `LEARNMSA_ALIGN`: `manifest unknown` | The pinned module requests `felbecker/learnmsa:2.0.9`, which was unavailable in a [native full-test execution](https://github.com/bmds-tue/nf-claw/actions/runs/37919738383). Other aligners' partial outputs do not make this a successful run. | The validated `test_tiny,docker` profile covers FAMSA and MAFFT, not learnMSA. Full-profile validation requires the exact unavailable image to be restored or a separately validated tool/configuration change. Do not silently substitute `latest` or a newer image: [learnMSA changed its sequence-weight defaults and removed `--sequence_weights` from 2.0.10](https://github.com/Gaius-Augustus/learnMSA#using-learnmsa), while this pinned full test uses that flag. |
| `marsseq` 1.0.3 | bundled `test` analysis preview fails with missing local references | `test.config` selects `mm10`, but analysis requires prebuilt FASTA, GTF, Bowtie2 and STAR references. `main.nf` chooses either reference building or analysis, so build and analysis are separate invocations. | Build with `--build-references true --velocity true` so both Bowtie2 and STAR indexes are generated (analysis checks the STAR path even when velocity is disabled), then supply the resulting reference base using `--genomes-base`. The complete bundled reference workflow, including real Bowtie2 and STAR indexes, completed on Nextflow 23.04.0; default and velocity-enabled analysis previews then passed with matched SB26-AB339 test inputs. These previews do not execute quantification or establish expression accuracy. On a 62 GB host, `nfclaw run marsseq --demo --outdir results/marsseq-reference --build-references true --velocity true --max-memory 48.GB --max-cpus 16` built them in 9 tasks. Its first `STAR_GENOMEGENERATE` attempt was killed by the container's memory limit (exit 137). The module sets STAR's `--limitGenomeGenerateRAM` to the task memory minus 100 MB, and STAR's resident memory reached 51.4 GB against the 51.5 GB (48 GiB) limit (reported as [nf-core/modules#13226](https://github.com/nf-core/modules/issues/13226)). Nextflow's automatic retry completed. `nfclaw run marsseq --demo --outdir results/marsseq --genomes-base results/marsseq-reference/references` then ran the analysis end to end in 34 tasks: its UMI table for amplification batch AB339 holds 93,303 UMIs over 9,051 of 53,854 genes in 192 wells. A release-specific accuracy check of those counts was not available. **Assembly warning:** the [pinned `mm10` key](https://github.com/nf-core/marsseq/blob/b02ede773092f8a8a5999400acda6894d51b4d26/conf/genomes.config) selects **GRCm39 / GENCODE M27**, plus ERCC sequences; [GENCODE identifies M27 as GRCm39](https://www.gencodegenes.org/mouse/release_M27.html), whereas [UCSC mm10 is GRCm38](https://hgdownload.cse.ucsc.edu/gbdb/mm10/html/description.html). Record the actual assembly, annotation and reference checksums; never silently substitute GRCm38 or infer the assembly from this key. |
| `tumourevo` 1.0.0 | CNAqc parameter description links to an absent parameter | The pinned schema's `cnaqc_min_absolute_karyotype_mutations` description refers to `cnaqc_min_karyotype_size`, which is not declared in that schema or passed by its CNAqc module configuration. This upstream cross-reference has no target; the generated reference marks it as undeclared instead of linking to a missing heading. | Use only parameters declared by the pinned schema; nfclaw rejects the absent flag. `--cnaqc-min-absolute-karyotype-mutations` sets an absolute mutation-count threshold. The missing reference does not establish an equivalent relative threshold or a replacement flag; consult the pinned module and CNAqc tool documentation for interpretation. |
| `rnafusion` 4.1.3 (bundled `test` profile) | `--demo` cannot complete as shipped: with `tools = "all"`, `FUSIONCATCHER` fails on a placeholder reference; `FUSIONREPORT_DOWNLOAD` fails with `zipfile.BadZipFile`; the profile otherwise builds full GRCh38 references inside 4-CPU/15 GB tasks. Upstream's `test_build` profile then fails in `STARFUSION_BUILD` (`revise_gencode_annotations.pl … died with ret 512`) | The profile's `fusioncatcher_ref` is `${projectDir}/assets` ("a placeholder until a small reference can be created"), and upstream runs this profile only with `-stub`. FusionGDB2's `FusionGDB2_id.xlsx` answered 404 and then 429, so fusion-report saved an HTML page as the workbook (nf-core/rnafusion#823, Clinical-Genomics/fusion-report#98). `STARFUSION_BUILD` adds `--human_gencode_filter` whenever `species` is human, and that filter fails on the non-GENCODE tutorial minigenome that `test_build` uses (nf-core/rnafusion#724, #671; reported for 4.1.3 as [nf-core/rnafusion#832](https://github.com/nf-core/rnafusion/issues/832)). | Run the `test` analysis on upstream's hosted GRCh38 references (`--genomes-base s3://nf-core-awsmegatests/rnafusion/references`), whose prebuilt fusion-report database avoids FusionGDB2. STAR's GRCh38 index needs more than the profile's 15 GB, so add `--limit-cpus 16 --limit-memory 48.GB --limit-time 8.h`. Every tool then ran on the bundled test reads (Nextflow 25.10.4). `--tools arriba,salmon,fusionreport` completed 15 tasks. `--tools fusioncatcher,fusionreport --fusioncatcher-ref s3://nf-core-awsmegatests/rnafusion/references/GRCh38/gencode_v46/fusioncatcher/` completed 4. `--tools arriba,ctatsplicing,starfusion,stringtie,fusionreport,fastp,fusioninspector` completed 24, with `--starfusion-ref` set to a local copy of the hosted `GRCh38/gencode_v46/starfusion/ctat_genome_lib_build_dir` (62 GB). FusionInspector needs that library's `ref_genome.fa.star.idx`. Given a library without it, FusionInspector tried to build the index inside the reference directory, and nfclaw reported the run as `failed (local dependencies changed during execution)`. The test data documents no truth set, so the callers were checked against each other. All 14 gene pairs Arriba called (known oncogenic fusions such as FGFR3–TACC3, EML4–ALK and ETV6–NTRK3) were also called by FusionCatcher; 12 of them were called by STAR-Fusion too, and FusionInspector validated all 14. STAR-Fusion was also checked on its tutorial. Build the references with upstream's `-profile test_build,docker`, setting `STARFUSION_BUILD`'s `ext.args = ''` (the fix in nf-core/rnafusion#724) and `--tools arriba,starfusion,salmon,fusioninspector`. Then run the tutorial's own reads with `--tools starfusion,fusionreport,fusioninspector,salmon --skip-vcf true`, that build as `--genomes-base` and the minigenome `--fasta`/`--gtf`. That run reproduced the five fusions the [tutorial](https://github.com/STAR-Fusion/STAR-Fusion-Tutorial/wiki) lists at all seven breakpoint pairs its example output gives. On the minigenome, Arriba finds no reads on its default human contigs, and `VCF_COLLECT` expects `GENE^ENSG` gene fields, which the tutorial GTF lacks. |
| `tumourevo` 1.0.0 (bundled `test` profile) | `SPARSE_SIGNATURES (SCOUT)` fails with `Error in if (K < 2) { : missing value where TRUE/FALSE needed`, after printing a cross-validation MSE table that is all `NA` | `conf/test.config` sets `sparsesignatures_K = "2:3"`, but the release declares and reads `sparsesignatures_k` (lower case), and nf-schema does not flag the unknown name (reported as [nf-core/tumourevo#92](https://github.com/nf-core/tumourevo/issues/92)). The test therefore runs with the default `K = 3:10` on its three small samples. SparseSignatures returns no fit for any combination of K and lambda in that grid, and the script fails while picking the best K. The release's own pipeline test sets `tools` without `sparsesignatures`, so its CI never runs this step. | Pass the value the test profile intended: `nfclaw run tumourevo --demo --outdir results/tumourevo --sparsesignatures-k 2:3`. The failing task, rerun on its own inputs (seed 42), failed again with `3:10` and completed with `2:3`. Resumed with `--sparsesignatures-k 2:3`, the demo reused its 65 cached tasks and completed `SPARSE_SIGNATURES` on Nextflow 25.10.4. |

---

## Pipeline-specific run notes

- **`demo` 1.2.0 on macOS arm64 with amd64 containers** — MultiQC 1.34 can
  return exit zero and write its HTML/data while Kaleido/Chromium fails to export
  plots under QEMU. Fresh and resumed local runs both reported `0/36 completed`,
  with `qemu: unknown option 'type=utility'` and Chromium sandbox/GPU crashes.
  Check the task's `.command.err` and required plot files even when pipeline status
  is success. Validate required exports on a compatible native execution platform;
  no arm64 image or emulation workaround has been established yet.

- **`rnaseq` 3.27.0 bundled test** — A [native Docker execution](https://github.com/bmds-tue/nf-claw/actions/runs/37926522041) completed all 234 tasks on Nextflow 25.10.4. Downloaded bytes matched all 1,056 recorded output checksums. Independent consistency checks covered five samples and 125 transcripts in each of the Salmon and STAR/Salmon routes: finite nonnegative estimates, normalized TPM, assigned-fragment totals and merged transcript/gene tables agreed with individual results within their published rounding. This validates the bundled test's execution and internal numerical consistency, not biological expression accuracy, differential expression or every alternative aligner.
  - **Replay:** A `--demo` run on Nextflow 26.04.3 (Linux amd64, Docker) and its `commands.sh` replay produced the same 1,056 result files and directories (`nfclaw verify`: 0 missing, 0 extra). Salmon `quant.sf`, the merged gene count tables of both routes and featureCounts tables were byte-identical. 344 files differed in bytes: reports, logs and plots that embed timestamps or paths, and three scientific outputs whose tools are not order-stable — the deduplicated BAMs (Picard MarkDuplicates flagged a different mate as the duplicate in 6 of 38,486 duplicate pairs of `WT_REP1`, with identical totals: equal-score ties follow STAR's multithreaded output order), StringTie FPKM in the sixth decimal place, and the row order of RSeQC `inner_distance.txt`. Expect `nfclaw verify --strict` to fail on such a replay; compare the quantification tables instead.

- **`fastqrepair` 1.1.1 bundled test** — The original upstream fixture completes nine tasks but filters its damaged pair after gzip recovery produces an empty mate; its empty sample is also excluded. Its surviving single-end sample has 24 complete valid reads and two malformed records. For this exact pin, a bare `nfclaw run fastqrepair --demo` stages all three original rows from immutable test-data commit `f72c633f2547fdfaf475c7f05423437a7eac0bbf` and adds `paired_control`: 646 genuine pairs from immutable commit `800330ec8f47c93caabe8157e20dd23e243de4e1`. This makes paired repair part of the managed demo; it does not claim to recover the excluded data. The generated CSV and row roles are recorded and replayed. Explicit input/test-data selectors, extra profiles or configs disable this fixture; explicit `num_splits` values win. Inspect discarded-sample warnings, executed tasks and repair reports alongside pipeline status. Independent reordered/orphan controls are still needed to assess pairing errors beyond this matched control.

  The managed demo and fresh replay each completed 22 native Docker tasks, including BBMap,
  with matching recorded environments. Both preserved all 646 paired read identities, full
  headers, sequences and mate orientation, zero singletons, and the original 24 valid single-end
  records. BBMap 39.18's default quality validation sets ambiguous-base qualities to Phred 0:
  exactly 211 `N` positions per mate changed from Phred 2 to 0; every other quality was unchanged.
  The pre-BBMap gathered reads retained the original qualities. An independent tiny image control
  confirmed this behavior; raw paired quality identity is therefore not claimed. See the
  [run/replay assessment](audit/evidence/commit-eee40ee-fastqrepair-demo.assessed-v2.json).

- **`createpanelrefs` 1.0.0 nonempty antitarget control** — Its bundled whole-genome CNVkit
  configuration deliberately has no antitarget bins. A separate controlled hybrid fixture and
  fresh replay each completed all three native Docker tasks, including CNVkit 0.9.12. It used a
  synthetic 1 Mb reference and two normal BAMs with independently checked uniform 1× and 2×
  aligned-base coverage. Explicit access bounds and bin sizes produced two target and three
  antitarget bins; all coverage coordinates/depths and the five-bin pooled reference passed,
  and all seven scientific files matched byte-for-byte in replay. Hybrid mode alone is
  insufficient: without `--access`, this CNVkit version guesses bounds starting at 150,000,
  which excluded these short target coordinates. The tested access bytes are embedded in the
  recorded config and checked in each task. This validates synthetic bin/count mechanics,
  not CNV calling accuracy or real-cohort behavior. See the
  [assessment](audit/evidence/commit-eee40ee-createpanelrefs-antitarget-v2-assessment.json).

- **`proteinfold` 2.0.0 `--demo`** — The bundled `test` profile sets `stubRun = true`: every task runs its stub block, so the run completes in minutes with empty placeholder structures, metrics and reports. `nfclaw run` announces this before launch and `nfclaw status` reports the success with a `stub run:` caveat (also recorded in `run_manifest.json` as `stub_profiles` and carried by a replay). A `--config` that sets `stubRun = true` is reported the same way and recorded as `stub_configs`. A real prediction needs a mode's databases (see `reference.md`); the demo only checks the workflow's wiring and publication. circdna's non-default `test_AA` profile is a stub run too.
- **`pathogensurveillance` 1.1.0 `--demo` on an IPv6-only host** — Its one test sample is the NCBI accession `SRR18850314`, which [sra-tools cannot fetch there](#sra-tools-cannot-reach-ncbi-ipv6-only-host), and `BBMAP_SENDSKETCH` needs the [JVM's IPv6 preference](#java-tools-in-containers-prefer-ipv4-ipv6-only-host). Download the run's two ENA FastQ files (check their MD5 sums against the ENA portal) and pass a sheet with `sample_id,description,path,path_2,sequence_type,enabled,color_by,report_group_ids,ploidy,taxon` to `--input` alongside `--demo`; keep `taxon`, which `color_by` refers to. ENA serves this run with simplified quality scores (only `?` = Q30 and `$` = Q3), from which SPAdes cannot infer the encoding (`Failed to determine offset!`); the pipeline then ignores the assembly after four attempts and reports success with caveats. The `$` scores show Phred+33, so add `process { withName: 'SPADES' { ext.args = '--phred-offset 33' } }`. With these, the bundled test completed without caveats on Nextflow 25.04.6: a 2.07 Mb SPAdes assembly in 472 scaffolds, and sendsketch's top hit *Limosilactobacillus* at 98.4% ANI, as the test sheet expects. This establishes execution, not the accuracy of its phylogenetic placement.
- **`lsmquant` 1.0.3 `--demo` without an NVIDIA GPU** — The test profile gives `NUMORPH_3DUNET` `ext.use_gpu = true` and `accelerator = 1`, and the module calls `nvidia-smi` unconditionally, so on a host without a GPU the task fails with exit status 127 (`nvidia-smi: command not found`). Adding `--nuclei-quantification false` skips that step: intensity adjustment, alignment and stitching then completed on Nextflow 25.10.4. Nuclei quantification itself needs a GPU: on a GPU host add the release's `gpu` profile, which passes the GPU to Docker with `--gpus all` (`nfclaw run lsmquant --demo -profile docker,gpu …`; nfclaw composes `test,docker,gpu`).
- **`fetchngs`** — If accessions lack ENA FTP links, the pipeline falls back to `SRATOOLS_PREFETCH` (requiring NCBI SRA Cloud access). In network-restricted environments, run metadata-only via `--skip_fastq_download`. (Accepts `.csv`, `.tsv`, or `.txt` accession lists at pinned 1.13.0 and `dev`).
  - **Bundled test on an IPv6-only host:** three of the test accessions (`SRR12848126`, `SRR14593545`, `SRR14709033`) have no ENA FastQ files and take the sra-tools route, which [cannot connect there](#sra-tools-cannot-reach-ncbi-ipv6-only-host): `SRATOOLS_PREFETCH` fails with `cannot resolve remote location`. With `--demo` and an `--input` list of the other seven test accessions (including the GEO `GSM4907283` and `GSE214215`), the run completed on Nextflow 25.10.4. For a fetchngs → taxprofiler chain also leave out `SRR9984183`: ENA lists it as Illumina HiSeq 2500, but it holds a submitted metagenome bin (58 low-quality reads of ~34 kb), from which fastp keeps nothing, and taxprofiler's `FASTQC_PROCESSED` then fails on the empty file. Give the taxprofiler stage the restricted profilers below and `"perform_shortread_redundancyestimation": false` (its test profile turns Nonpareil on; its curve fit fails on small real samples). With these, the chain completed with verified lineage.
- **`coproid`** — Requires **two** samplesheets: `--input` (FASTQ sheet) and a separate required `--genome_sheet`. Each row in `--genome_sheet` requires `genome_name,taxid,genome_size` plus **exactly one** of `igenome` or `fasta` (mutually exclusive `oneOf` schema). `--kraken2_db` is mandatory and must point to a valid Kraken2 database.
- **`crisprseq`** — The samplesheet `reference` column expects a **raw DNA sequence string** (pattern `^[ACTGNactgn]+$`), not a FASTA file path.
- **`circdna`** — Two parameters are **required by schema** for non-demo runs: `--input_format` (`FASTQ` or `BAM`) and `--circle_identifier` (one or more of `circle_map_realign`, `circle_map_repeats`, `circle_finder`, `circexplorer2`, `ampliconarchitect`).
- **`metapep`** — The `--demo` profile runs `DOWNLOAD_PROTEINS`, which fetches sequences from **NCBI Entrez** (`download_proteins_entrez.py --email $NCBI_EMAIL`) reading a Nextflow secret named `NCBI_EMAIL`. Set the secret prior to execution: `nextflow secrets set NCBI_EMAIL you@example.com`.
- **`seqsubmit` 1.0.0 `--demo` needs an ENA Webin account** — The bundled `test` profile sets `test_upload = true`, so `genome_upload` validates the submission without uploading it, but it still queries ENA for the study's run metadata with Webin credentials. `nextflow.config` passes the Nextflow secrets `ENA_WEBIN` and `ENA_WEBIN_PASSWORD` to every task through its `env` scope, so without them Nextflow only warns that both variables evaluate to an empty value: the FASTA validation, classification and coverage tasks complete, and `CREATE_MANIFESTS` then fails with `CredentialsNotSetError: Credentials for ENA are not set` (reproduced on Nextflow 25.10.4). Set both secrets for a Webin account (`nextflow secrets set ENA_WEBIN Webin-NNNNN`, then `nextflow secrets set ENA_WEBIN_PASSWORD …`) before any run, including `--demo`. Without an account, a stub run checks the rest of the workflow: pass `--config` a file containing `stubRun = true`, and every task runs its stub block, none contacting ENA (`nfclaw status` then reports a `stub run:` caveat). It stops before the submission step, whose stub inputs match no genome.
- **`epitopeprediction` 3.1.1 queries Ensembl BioMart while it runs; the pinned 3.2.0 does not** — 3.2.0 replaced the epytope/BioMart variant path with `bcftools`, Ensembl VEP and pVACtools ([nf-core/epitopeprediction#362](https://github.com/nf-core/epitopeprediction/pull/362)). Its `test` profile annotates with a 15 MB GRCh38 VEP cache subset that it downloads with the test data. For your own VCFs, give `--vep_cache` and `--ref_fasta`, or set `--vep_download_cache`, which fetches about 20 GB from the Ensembl FTP site. In 3.1.1 (`--pipeline-version 3.1.1`), `EPYTOPE_VARIANT_PREDICTION` looks up the proteins of the variants' transcripts through epytope's `MartsAdapter`. When BioMart is overloaded it answers with its "Service unavailable" HTML page and HTTP status 200. epytope retries only error statuses, so the page reaches pandas and the task fails with `ValueError: Length mismatch: Expected axis has 1 elements, new values have 3 elements` in `MartsAdapter.get_dataset_attributes`. On 2026-10-15, 24 of 600 requests to `grch37.ensembl.org/biomart/martservice` over 50 minutes got that page, and two of the three 3.1.1 `--demo` runs that reached this step lost a task this way. Upstream tracked this as [nf-core/epitopeprediction#337](https://github.com/nf-core/epitopeprediction/issues/337). For 3.1.1, retry the task with `process { withName: 'EPYTOPE_VARIANT_PREDICTION' { errorStrategy = 'retry'; maxRetries = 3 } }` passed as `--config`, or re-run with `--resume`. A host that cannot reach Ensembl cannot run that step.
- **`oncoanalyser` 3.0.0 `--demo` needs about 130 GB for references** — The bundled test downloads about 53 GB of reference tarballs (HMF pipeline resources, GRIDSS, STAR and BWA-MEM2 indexes) plus the 3.2 GB GRCh38 FASTA and a 5.6 GB BWA image, and it extracts the tarballs inside the work directory, so a run holds both copies. Upstream's CI extracts them once instead and passes them through `tests/cached_refs.config` and five `NXF_REF_*` variables. To run it that way, download the FASTA, its `.fai`, `.dict` and `.img`, and extract each tarball into its own directory without its top-level directory (`tar -xzf … --strip-components 1`, as the pipeline's `CUSTOM_EXTRACTTARBALL` does; 77 GB in all). Then run `nfclaw run oncoanalyser --demo --outdir results/oncoanalyser --config <repo>/pipelines/oncoanalyser/upstream/tests/cached_refs.config` with `--nxf-env NXF_REF_DATA_PATH=<dir>`, plus `NXF_REF_BWAMEM2_INDEX`, `NXF_REF_GRIDSS_INDEX`, `NXF_REF_STAR_INDEX` and `NXF_REF_HMF_DATA`, each set to its extracted directory. On Nextflow 25.10.4 this ran the 42 tasks upstream's test expects with cached references. It was resumed once, after the sweep's disk guard stopped it. All 473 output paths and all 151 stable-content checksums in the release's nf-test snapshot (`tests/profile_test.nf.test.snap`) matched.
- **`createtaxdb`** — Assign each sample a **non-numeric** `id` (e.g. `seq1`, `chr1`). Purely numeric strings (`"1"`) are coerced to integers by nf-schema, violating string constraints.
- **`genomeassembler`** — Set at least one of `--ont true` or `--hifi true` (the pipeline aborts with `At least one of params.ont, params.hifi needs to be true.`).
- **`funcscan`** — Pin `--nxf-ver 25.10.4` (declares `!>=25.10.4`). Demo profiles run all three screenings (AMP, ARG, CAZyme), which download multi-gigabyte models; pre-supply databases via `--amp_ampcombi_db` or disable heavy steps via `--run_cazyme_screening false` and `--arg_skip_deeparg true`. If `DEEPARG_DOWNLOADDATA` makes no progress until its time limit, see [Docker's MTU](#downloads-inside-task-containers-stall-dockers-mtu-is-larger-than-the-hosts).
- **`sarek` 3.11.0 (`sarek` 3.10.0, 3.9.0)** — Upstream examples for cache/index-only runs show `--build_only_index --input false`. In raw Nextflow, this causes an nf-schema validation error because `input` is declared as a string path. In `nfclaw run sarek --input false`, nfclaw intercepts `--input false` and leaves `input` unset in `params.json`, allowing index-only runs (`--build_only_index true --download_cache true`) to succeed cleanly without schema errors. For raw Nextflow runs, omit `--input` instead of passing `false`.
- **`sarek` 3.11.0 (`sarek` 3.10.0, 3.9.0)** — Do not use `--config pipelines/sarek/upstream/conf/test.config` to convert an analysis run into a test run with a custom samplesheet. Extra configs load after initial profile setup, causing validation of default S3 iGenomes paths. Run with `-profile test,docker` instead: `nfclaw run sarek --input samplesheet_sarek.csv --outdir results -profile test,docker`. For bundled test data, use `nfclaw run sarek --demo --outdir results`.
- **`ampliseq` 3.0.0** — The bundled `test` profile sets its own `process.resourceLimits` (4 CPUs, 15 GB, 1 h); the release has no `--max_memory`/`--max_cpus` parameters (nfclaw rejects them as unknown), so cap a real run with `--limit-cpus`/`--limit-memory`/`--limit-time`. Its `--demo` completed all 130 tasks without a retry on Nextflow 26.04.3 with Docker (Linux amd64); `QIIME2_EXPORT_RELTAX` peaked at 1.2 GB of RSS. This establishes execution of the bundled test, not taxonomic accuracy. 3.0.0 also removed the legacy `sampleID,forwardReads` samplesheet format (use `sample,fastq_1[,fastq_2]`) and renamed `--FW-primer`/`--RV-primer` to `--primer-fwd`/`--primer-rev`; nfclaw rejects the old names.
  - **Reproducibility:** DADA2 taxonomy ties and QIIME2 rarefaction can change results on fresh runs despite `--seed`. See [verified findings and workarounds](#ampliseq-300-taxonomy-and-rarefaction-reproducibility).

- **`sopa` 1.0.1 `--demo` cannot be replayed faithfully** — Its test samplesheet (`tests/samplesheet.csv`) names `https://github.com/nf-core/sopa/blob/dev/tests/samplesheet.csv` as the sample's `data_path`: a GitHub HTML page, not a raw file. Nextflow stages that page as a task input, and the page's bytes change on every download (213,168 bytes in one run, 213,166 in its replay). A replay of `--demo` therefore fails its environment check with `remote input … changed`, as it should: the replay did consume other bytes. Pass a stable `data_path` (a local file or a `raw.githubusercontent.com` URL at a commit) for a run that replays exactly.
- **`epitopeprediction` 3.1.1 replays meet the same BioMart replies** — The [BioMart lookups](#pipeline-specific-run-notes) above happen in the replay too, so a replay can fail where its original succeeded. Pass the retry config as `--config` when the run starts: the bundle keeps a copy of it, and the replay retries the same way. A replay with it reproduced the run's environment exactly.
- **Outputs that differ between a run and its replay by design** — `nfclaw verify` compares outputs by path. Some releases name or include outputs nondeterministically, so a faithful replay (identical images, plugins, source and inputs) still reports files as missing or extra:
  - `longraredisease` 1.0.0 names its MultiQC report after the output directory (`<outdir basename>-pipeline-report_multiqc_report.html`), so a replay into `<outdir>.replay` names it differently.
  - `createtaxdb` 3.1.0: `kraken2-build` gives the files it adds to `library/added/` random names. `nfclaw verify` pairs exactly these names one to one within their directory, lists them under `renamed` and compares their bytes, so a faithful replay no longer reports them as missing and extra.
  - `hicar` 1.0.0: across runs, its MultiQC report included different samtools sections (`flagstat` once, `stats` and the alignment plots another time), and one `.hic` file under `cooler/MAPS/` was published under different names.
  - `nanoseq` 3.1.0: NanoPlot names its log by the minute it ran (`NanoPlot_<date>_<time>.log`).
  - `nanostring` 1.3.3: MultiQC exported four plots in one run and not in its replay.
  - `mag` 5.5.0: Prokka publishes temporary protein files named by its process ID (`….AMR.tmp.<pid>.faa`).
  - `rnafusion` 4.1.3: FusionInspector publishes `fi_workdir/pipeliner.<pid>.cmds`.
  - `rnasplice` 1.0.4: MISO names its batch logs by the time they were written.
  - A resumed run's outdir keeps the launch-stamped `pipeline_info` reports of its earlier attempts; its replay reproduces the last attempt only.
  Inspect such differences with a format-aware comparison; they are not reported as environment differences.

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
- **`createtaxdb`:** The test profile also builds Sourmash databases, which taxprofiler does not use. The exact pinned 3.1.0 source now receives the recorded [copy-sort correction](source-corrections.md) in nfclaw runs and chains. Supplying `"params": {"build_sourmash_dna": false, "build_sourmash_protein": false}` deliberately omits those optional builders; it is no longer required to avoid the shared-list race in corrected nfclaw execution.
- **`detaxizer`:** The test profile filters reads with an empty database, removing all reads and leaving empty FastQ files. For downstream chaining, provide active classification parameters: `"params": {"classification_kraken2": false, "classification_bbduk": true, "fasta_bbduk": "<host fasta>"}`.
- **`rnaseq` → `differentialabundance`:** rnaseq's test data leave 100 genes after differentialabundance's default abundance filter — fewer than DESeq2's default variance-stabilisation subsample (`--deseq2-vst-nsub`, 1000), so `DESEQ2_DIFFERENTIAL` fails with `less than 'nsub' rows`. Give the stage `"deseq2_vst_nsub": 50` along with its own `input` (a design sheet naming rnaseq's samples) and `contrasts`. With that, an rnaseq `demo: true` → differentialabundance chain completed (the failed stage resumed after editing the spec, rnaseq skipped as already succeeded) and `nfclaw chain status` verified the lineage; DESeq2 tested all 100 genes.
- **`bamtofastq` → `rnaseq`:** the bamtofastq stage needs its `fasta` (see the upstream table). Its test BAMs hold 2,821 and 2,718 read pairs of human `chr22:1-40001`, below rnaseq's `--min-trimmed-reads` (10,000): rnaseq then skips both samples and reports it as a caveat. Give the rnaseq stage the same chr22 test `fasta` and `gtf` (six genes), `"min_trimmed_reads": 1000`, and skip the steps that need more genes than that, `"skip_dupradar": true` and `"skip_deseq2_qc": true`. With these, the chain (the `build` handoff) completed with verified lineage and Salmon counts for both samples.
- **`demultiplex`:** Test data consists of human amplicon reads. Downstream stages requiring reference genomes need human references (`fasta`/`gtf`), and paired-end profiles: `"profile": "test_pe,docker"`.
- **`taxprofiler`:** Test profiling on unrecognized reads fails in unhandled zero-hit modules; enable only resilient profilers (`run_kraken2`, `run_kaiju`) with `"run_profile_standardisation": false`. With the detaxizer parameters above and every other `run_*` profiler switched off, a detaxizer `demo: true` → taxprofiler `demo: true` chain completed with verified lineage; all five handed-over read sets (three short-read, two long-read) were profiled with kaiju, and the short-read sets with kraken2.

### File-only inventories missed empty directories and changed aliases
- **Status: Fixed for new recorded namespaces.** Output verification previously accepted two trees with identical files but different empty-directory names. Reference handoffs could also accept changed directory shapes or retargeted aliases whose file bytes remained identical.
- **Behavior:** New bundles record `outputs.inventory.json`. Verification reports missing/extra directories and changed link identities alongside file differences. Old file-only manifests provide byte comparisons, but historical directory agreement remains unverified and cannot return a successful structural check. Live trees without historical manifests remain comparable.
- **Handoffs:** Published output namespaces and local reference namespaces are verified before the next stage starts. Chain status checks source namespaces and the downstream prelaunch snapshot. Complete run-directory handoffs retain all entries and record execution metadata at the boundary separately from historically published results.
- **Validation:** Real producer and consumer tasks exercised external references, published directories and complete run directories. Renaming an empty sample directory while retaining reference bytes blocked the consumer; restoring the original namespace allowed resume, and subsequent changes broke lineage. These execution and conservation checks do not establish biological accuracy.

### Enum preflight confused JSON types and rounded large integers
- **Status: Fixed.** Enum documentation text was also used for validation, so numeric `1` could match the string enum `"1"`, and converting enum entries to floating point could make `9007199254740992.0` match the distinct integer `9007199254740993`. A matching enum also bypassed independent type, pattern and numeric constraints.
- **Behavior:** Preflight retains typed enum values, distinguishes booleans from numbers and compares numbers without converting integer enum entries to floats. Independent constraints still apply to enum members. Whole-number CLI tokens for number parameters retain their integer precision. Enum-only schemas may contain mixed JSON types; genuinely equivalent `1` and `1.0` remain accepted, consistent with [JSON Schema enum semantics](https://json-schema.org/understanding-json-schema/reference/enum) and [numeric semantics](https://json-schema.org/understanding-json-schema/reference/numeric). Version-dependent treatment of unset values remains delegated to nf-schema.
- **Validation:** Regression controls cover scalar and nested enum types, large integers, empty enums, conflicting independent constraints and CLI conversion. An independent JSON Schema validator agreed on 840 decisions. Every enum in the pinned library was checked for conflicts with its declared independent constraints; none were found. These controls verify preflight decisions rather than biological accuracy or arbitrary-precision support throughout Nextflow.
