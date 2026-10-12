from __future__ import annotations

import csv
import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from runner import (discovery, engine_version, execution, fastqrepair_compat, inputs, nextflow_command,
                    input_safety, outputs, parameters, path_roles, plugin_compat, preflight, provenance,
                    reproducibility, resources, resume_safety, runlog, samplesheet, sheetgen,
                    submodule, versions)
from runner import schema as schema_mod
from runner.replay_guard import _capture_input_inventory
from runner.errors import ErrorCode, NfclawError
from runner.locking import output_writer
from runner.submodule import SubmoduleStatus


def _resume_advisory(outdir: Path, st: SubmoduleStatus) -> list[str]:
    """Advise when `--resume` continues a run that executed different pipeline code.

    Resuming re-launches whatever the request resolves to *now*. For a release that is the code the
    earlier run used, but `dev` moves: the run being resumed may have executed an older commit.
    Nextflow's cache stays correct either way (it reuses only tasks whose code and inputs are
    unchanged), so this is advisory — it explains why some tasks re-run and that the results now
    mix two commits. The earlier commit comes from that run's provenance manifest, if it wrote one."""
    try:
        prev = json.loads((outdir / "provenance" / "run_manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    prev_commit = prev.get("commit") if isinstance(prev, dict) else None
    if not isinstance(prev_commit, str) or not prev_commit or prev_commit == st.commit:
        return []
    return [f"--resume continues a run that executed {prev.get('version') or '?'} "
            f"(commit {prev_commit[:12]}); this launch executes {st.version} (commit "
            f"{st.commit[:12]}). Nextflow reuses only tasks whose code and inputs are unchanged, "
            "so tasks touched by the change re-run and the results combine both commits."]


def _directory_nodes(inventory: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    """The input directories and every entry beneath them."""
    roots = {Path(name) for name, entry in inventory.items() if entry["type"] == "directory"}
    return {name: entry for name, entry in inventory.items()
            if Path(name) in roots or any(parent in roots for parent in Path(name).parents)}


def _input_file_digests(inventory: dict[str, dict[str, str]],
                            known: dict[str, str] | None) -> dict[str, str]:
    """SHA-256 of every local input file (from `known` when already hashed)."""
    digests = {}
    physical_digests = {}
    for name, entry in inventory.items():
        if entry["type"] == "file":
            if known is not None and name in known:
                digests[name] = known[name]
            else:
                physical = Path(entry.get("resolved_path", name))
                if physical not in physical_digests:
                    physical_digests[physical] = provenance._sha256(physical)
                digests[name] = physical_digests[physical]
    return digests


def _input_resume_warning(outdir: Path, current: dict[str, dict[str, str]],
                              current_digests: dict[str, str]) -> str | None:
    """Guard resume against metadata-preserving input changes, including directory members.

    Ordinary file and directory cache keys omit file content. A changed local input's bytes
    require a fresh session because size/mtime can be unchanged. Directory namespaces also
    need comparison because nested additions/renames can leave directory metadata unchanged.
    Unchanged inputs retain normal cache reuse. Already captured SHA-256 values are reused.
    """
    current_nodes = _directory_nodes(current)
    try:
        previous = provenance.read_input_inventory(outdir / "provenance/inputs.inventory.json")
        manifest = json.loads((outdir / "provenance/run_manifest.json").read_text())
        if (not isinstance(manifest, dict)
                or type(manifest.get("dependency_inventory_version")) is not int
                or manifest["dependency_inventory_version"] != 1
                or "inputs" in manifest.get("unverified_dependency_inventories", [])):
            raise ValueError("previous namespace was not captured")
        previous_digests = provenance.read_checksums(outdir / "provenance/inputs.sha256",
                                                     relative=False)
    except (OSError, ValueError, TypeError):
        if not current:
            return None
        reason = "the earlier local-input inventory is unavailable or invalid"
    else:
        directory_roots = [Path(name) for name, entry in current_nodes.items() if entry["type"] == "directory"]
        files = {name for name, entry in current_nodes.items() if entry["type"] == "file"}
        historical_files = {name for name in previous_digests
                            if any(Path(name).is_relative_to(root) for root in directory_roots)}
        if current_nodes != _directory_nodes(previous):
            reason = "the input-directory inventory changed"
        elif files != historical_files:
            reason = "the input-directory namespace and content records disagree"
        elif current != previous:
            reason = "the local-input inventory changed"
        elif ({name for name, entry in current.items() if entry["type"] == "file"}
              != current_digests.keys()
              or {name for name, entry in previous.items() if entry["type"] == "file"}
              != previous_digests.keys()):
            reason = "the local-input namespace and content records disagree"
        elif any(previous_digests.get(name) != current_digests[name] for name in files):
            reason = "the content of a file inside an input directory changed"
        elif any(previous_digests[name] != digest for name, digest in current_digests.items()
                 if name in previous_digests):
            reason = "the content of a local input file changed"
        else:
            return None
    return (f"--resume starts a fresh Nextflow cache session because {reason}. "
            "File and directory metadata alone cannot establish unchanged task inputs; all tasks will "
            "be recomputed to prevent stale results. An existing output directory will be "
            "preserved in a sibling archive before launching.")


def work_directory(nxf_overlay: dict[str, str], repo_root: Path) -> Path:
    """The Nextflow work directory a run uses: NXF_WORK (the run's overlay wins over the shell) or
    the repository's work directory — resolved before Nextflow changes cwd to the outdir, so a
    relative value has one meaning in preflight, execution, provenance and a chain's checks."""
    return Path(nxf_overlay.get("NXF_WORK") or os.environ.get("NXF_WORK")
                or repo_root / "work").expanduser().resolve()


@dataclass
class RunResult:
    command: str
    outdir: Path
    checked_only: bool
    outputs_report: "outputs.OutputsReport | None"
    warnings: list[str] = field(default_factory=list)
    log_path: Path | None = None            # the run log; None for --check, which launches nothing
    # The NXF_* overlay `command` runs under (--nxf-ver, --nxf-env): part of the command as shown.
    env: dict[str, str] = field(default_factory=dict)
    # --check only: the temp directory holding the files the printed command names. It outlives the
    # process so the command stays runnable; a caller that only validates (a chain) removes it.
    staging: Path | None = None
    local_dependencies: tuple[Path, ...] = ()  # check-only: chain-wide write separation
    # The samplesheet nfclaw generated from the data files --input named (runner.sheetgen).
    generated_samplesheet: Path | None = None


def run_pipeline(name: str, *, repo_root: Path, input_path: "Path | str | None",
                 outdir: Path, profile: str, params_file: Path | None,
                 cli_overrides: dict, resume: bool, demo: bool,
                 check_only: bool, write_provenance: bool,
                 timeout_seconds: int | None, pipeline_version: str | None = None,
                 nxf_ver: str | None = None,
                 nxf_env: dict[str, str] | None = None,
                 allow_spaces: bool = False,
                 configs: tuple[str, ...] | list[str] = (),
                 limits: "resources.ResourceLimits | None" = None,
                 on_warning: Callable[[str], None] | None = None,
                 chain_link: dict | None = None,
                 deferred_params: frozenset[str] = frozenset(),
                 resolved_tree: SubmoduleStatus | None = None,
                 sheet_set: dict[str, str] | None = None) -> RunResult:
    """Validate, launch and record one pipeline run.

    Two arguments exist for a chain (runner.chain) and change nothing otherwise: `chain_link` is
    recorded in the run's manifest (which chain this stage belongs to, which run fed it), and
    `deferred_params` — for `check_only` alone — names parameters a handoff will supply once the
    stage feeding this one has run, so they count as neither missing nor invalid yet.

    When the input names data files where the pipeline takes a samplesheet, the samplesheet is
    generated first (runner.sheetgen); `sheet_set` holds the column values the caller assigned."""
    outdir = outdir.expanduser().resolve()
    if deferred_params and not check_only:
        raise ValueError("deferred_params is only meaningful with check_only")
    pipelines_dir = repo_root / "pipelines"
    discovery.find(name, pipelines_dir)                       # 404 if unknown
    # Extra Nextflow config files passed straight through as `-c` (e.g. a docker host-network or
    # custom-resources config). Resolved to absolute and validated up front so a typo fails fast.
    extra_configs: list[Path] = []
    for c in configs:
        cfg = Path(c).expanduser().resolve()
        if not cfg.is_file():
            raise NfclawError(ErrorCode.ENVIRONMENT, f"--config file not found: {c}",
                              fix="Pass a path to an existing Nextflow config file.")
        extra_configs.append(cfg)
    # A --params-file the user named must exist: nfclaw reads it itself (merge, below), so a typo'd
    # path would otherwise be silently dropped and the run proceed with none of its values. Fail
    # fast, naming the path — the same fail-fast contract as --config above.
    if params_file is not None:
        params_file = params_file.expanduser()
        if not params_file.is_file():
            raise NfclawError(ErrorCode.PARAMS_INVALID, f"--params-file not found: {params_file}",
                              fix="Pass a path to an existing JSON or YAML params file.")
    # None → pinned latest (unchanged); a tag → that release, validated + materialized.
    # Everything downstream consumes `st`/`st.path`, so it all targets the chosen version.
    st = resolved_tree or versions.ensure(name, pipeline_version, pipelines_dir=pipelines_dir,
                                         repo_root=repo_root)
    if st.name != name:
        raise ValueError("resolved_tree must belong to the requested pipeline")
    # The code that runs must be the code provenance will name: the pin its docs describe (for the
    # pinned submodule) and, for any tree, without local edits.
    pinned_tree = not versions.is_cached(st)
    if tree_problems := submodule.tree_issues(
            st, pipelines_dir / name / "skill.md" if pinned_tree else None):
        rel = f"pipelines/{name}/upstream" if pinned_tree else str(st.path)
        raise NfclawError(
            ErrorCode.SUBMODULE_INCOMPLETE,
            "The pipeline code is not the unmodified release nfclaw would record.",
            fix=(f"Restore it with `git submodule update --force {rel}`" if pinned_tree else
                 f"Move {rel} aside (preserving any changes you need); nfclaw recreates it")
                + (", or pass --pipeline-version to run another release deliberately."
                   if pinned_tree else "."),
            details={"issues": tree_problems})
    # The Nextflow runtime env nfclaw applies for this run: --nxf-env vars plus --nxf-ver
    # (sugar for NXF_VER, which wins if both set it). Threaded to the engine check, the
    # subprocess and provenance so the engine actually used is consistent and recorded.
    nxf_overlay = dict(nxf_env or {})
    if nxf_ver:
        nxf_overlay["NXF_VER"] = nxf_ver
    # The Nextflow work directory for this run: NXF_WORK (overlay wins over the shell) if set,
    # else the repository work directory. Resolve it before Nextflow changes cwd to the outdir,
    # so a relative user value has one stable meaning in preflight, execution and provenance.
    work_dir = work_directory(nxf_overlay, repo_root)
    param_schema = schema_mod.load_param_schema(st.path)

    # Read the params file once; it is merged below, and it may be what supplies `input`.
    file_params = parameters.load_params_file(params_file) if params_file is not None else {}

    # What --input is comes from the pipeline's own schema, not an assumption: a samplesheet, another
    # local path (a directory, an SDRF file), or a plain value (a PRIDE accession, a URL, `false`).
    # Only a local samplesheet gets the deterministic pre-check; a remote one is staged by Nextflow and
    # validated by nf-schema at runtime, and a plain value is forwarded unchanged. The flag wins over
    # the params file's `input` (as in the merge below), and whichever supplies the value, it is
    # interpreted the same way — a params-file `input: false` or relative samplesheet means exactly
    # what `--input false` or `--input sheet.csv` does.
    # A chain's --check judges a later stage before the stage feeding it has run: an --input a
    # handoff will write does not exist yet, so it is neither resolved nor pre-checked.
    raw_input = (None if "input" in deferred_params
                 else input_path if input_path is not None else file_params.get("input"))
    # Data files where the pipeline takes a samplesheet — a directory, a glob, one or several files:
    # generate the samplesheet its schema describes (runner.sheetgen). It is validated here like a
    # hand-written one, before anything is written, and staged beside the params file below; until
    # then `input` names that staged location, which the parameter checks treat as any sheet path.
    sheet = None
    if (source := sheetgen.detect(raw_input, st.path)) is not None:
        sheet = sheetgen.generate(source, st.path, pipeline=name, assignments=sheet_set or {},
                                  outdir=outdir, work_dir=work_dir)
    elif sheet_set:
        raise NfclawError(ErrorCode.PARAMS_INVALID,
                          "--sheet-set (a chain stage's sheet_set) sets columns of a samplesheet "
                          "nfclaw generates, but --input does not name data files to generate one "
                          "from.",
                          fix="Pass the data files (a directory, glob or files) as --input, or set "
                              "the values in your own samplesheet.")
    resolved_input = (inputs.ResolvedInput(str(outdir / "provenance" / sheet.filename), None, None)
                      if sheet is not None else inputs.resolve(raw_input, st.path))
    sheet_inputs = []
    if resolved_input is not None and resolved_input.local_path is not None:
        input_schema = (schema_mod.load_input_schema(st.path, resolved_input.samplesheet_schema)
                        if resolved_input.samplesheet_schema else None)
        if input_schema is not None:
            sheet_inputs.append((resolved_input.local_path, input_schema))
            problems = samplesheet.validate(resolved_input.local_path, input_schema)
            if problems:
                raise NfclawError(ErrorCode.SAMPLESHEET_INVALID,
                                  "Samplesheet failed validation.",
                                  details={"issues": problems})
        elif resolved_input.must_exist and not resolved_input.local_path.exists():
            raise NfclawError(ErrorCode.PARAMS_INVALID,
                              f"--input not found: {resolved_input.local_path}",
                              fix="Pass an existing file or directory (see Inputs in skill.md).")

    # Merge params-file + --input/--outdir + CLI first, then validate the WHOLE map — a typo
    # or bad enum in the params-file must fail fast too, not only CLI flags.
    merged = parameters.merge(cli_overrides=cli_overrides, params_file=file_params,
                              input_path=resolved_input.value if resolved_input else None,
                              outdir=outdir)
    # Coerce CLI strings to their schema scalar type (e.g. `--skip-busco true` → real boolean)
    # before validating and writing the params-file, so nf-schema sees correctly-typed values.
    merged = parameters.coerce_to_schema(merged, param_schema)
    # Auxiliary sample/reference/database tables declare their own schemas, too. Validate only
    # the schema branch applicable to an explicitly supplied value, leaving profile/config values
    # and future chain handoffs to Nextflow instead of guessing what they will provide.
    for name_param in inputs.samplesheet_parameters(st.path):
        if name_param == "input" or name_param in deferred_params or name_param not in merged:
            continue
        auxiliary = inputs.resolve(merged[name_param], st.path, param_name=name_param)
        if auxiliary is None or auxiliary.local_path is None or auxiliary.samplesheet_schema is None:
            continue
        sheet_schema = schema_mod.load_input_schema(st.path, auxiliary.samplesheet_schema)
        if sheet_schema is None:
            continue
        problems = samplesheet.validate(auxiliary.local_path, sheet_schema)
        if problems:
            raise NfclawError(ErrorCode.SAMPLESHEET_INVALID,
                              f"Samplesheet for --{name_param.replace('_', '-')} failed validation.",
                              details={"issues": problems})
        merged[name_param] = auxiliary.value
        sheet_inputs.append((auxiliary.local_path, sheet_schema))

    # Fix the report/timeline/trace/DAG filenames for this run instead of letting the pipeline
    # re-evaluate `now()` on every launch, so replaying the bundle reproduces the run's outputs
    # rather than writing a second, differently-named set of reports beside them.
    merged = parameters.pin_report_suffix(merged, param_schema)
    output_only_dirs = path_roles.output_only_directories(st, param_schema)
    param_errors = parameters.validate_params(
        merged, param_schema, output_only_dirs=output_only_dirs,
        shell_paths=path_roles.shell_path_directories(st, param_schema))
    composed_profile = nextflow_command.compose_profile(profile, demo=demo)
    # A missing required parameter can only be judged up front when nothing but the values merged
    # above can supply one. A `test` or institutional profile, or a --config file, can assign params
    # that nf-schema then sees — nf-core's own `-profile test,docker` sets --input — so then (and for
    # --demo, which adds `test`) nf-schema judges required-ness at launch instead.
    if not extra_configs and not nextflow_command.may_set_params(composed_profile):
        supplied_later = {n: "<from handoff>" for n in deferred_params if n not in merged}
        param_errors.extend(parameters.missing_required_params(
            {**merged, **supplied_later}, param_schema,
            configured=schema_mod.config_param_defaults(st.path)))
    if param_errors:
        raise NfclawError(ErrorCode.PARAMS_INVALID,
                          "Parameters failed validation (fix before running).",
                          fix="Use parameter names and allowed values from reference.md.",
                          details={"issues": param_errors})


    # Read dependencies before creating or modifying the output directory. The sheet
    # can become unreadable or malformed after its earlier validation; do not launch
    # with a silently truncated dependency inventory or leak an unclassified error.
    sheet_dependencies = []
    for sheet_path, sheet_schema in sheet_inputs:
        try:
            sheet_dependencies.extend(provenance.samplesheet_input_paths(sheet_path, sheet_schema))
        except (csv.Error, UnicodeDecodeError) as exc:
            raise NfclawError(
                ErrorCode.SAMPLESHEET_INVALID,
                f"Cannot parse samplesheet dependencies: {sheet_path}: {exc}",
                fix="Restore a valid samplesheet before launching the pipeline.") from exc
        except OSError as exc:
            raise NfclawError(
                ErrorCode.ENVIRONMENT,
                f"Cannot read samplesheet dependencies: {sheet_path}: {exc}",
                fix="Restore the samplesheet and make it readable before launching.") from exc

    resolved = parameters.resolve_path_params(merged, param_schema)
    refs = param_schema.reference_path_params()
    prov_inputs = []
    unverified_paths = {}
    for key, value in resolved.items():
        if key not in refs or key in {"input", "outdir"} or key in output_only_dirs or not isinstance(value, str) \
                or not value or inputs.is_remote_url(value):
            continue
        path = Path(value)
        try:
            provenance.input_files([path])
        except provenance.MissingInputSource:
            if param_schema.params[key].exists is True:
                prov_inputs.append(path)  # Required input: the snapshot below reports failure.
            else:
                # Schema path formats describe both inputs and destinations. An absent path
                # without an existence assertion may be created by the workflow; leave that
                # judgment to Nextflow, and record the lack of an input snapshot explicitly.
                unverified_paths[key] = value
            continue
        except OSError as exc:
            raise NfclawError(
                ErrorCode.ENVIRONMENT, f"cannot snapshot local run dependencies: {exc}",
                fix="Make the input data and configuration files readable before launching.") from exc
        prov_inputs.append(path)
    # A local --input is an input whatever its declared format (mhcquant's carries none).
    if resolved_input is not None and resolved_input.local_path is not None:
        prov_inputs = list(dict.fromkeys([resolved_input.local_path, *prov_inputs]))
    # A generated samplesheet is a file nfclaw writes for the run (recorded with the configs, below);
    # every local path it names is an input — whether or not its column declares a path format.
    prov_inputs = list(dict.fromkeys([*prov_inputs, *(path for path, _ in sheet_inputs),
                                    *sheet_dependencies,
                                    *(sheet.files if sheet is not None else ())]))
    local_dependencies = tuple(dict.fromkeys([*prov_inputs, st.path, *extra_configs,
                                              *([params_file] if params_file else [])]))
    repair_compat = name == "fastqrepair" and st.commit == fastqrepair_compat.SUPPORTED_COMMIT
    repair_input = resolved_input.local_path if resolved_input is not None else None
    if repair_compat:
        try:
            if sheet is not None:
                fastqrepair_compat.paired_row_roles(sheet.rows)
            else:
                fastqrepair_compat.paired_input_roles(repair_input)
        except (OSError, ValueError, csv.Error) as exc:
            raise NfclawError(
                ErrorCode.SAMPLESHEET_INVALID, f"Cannot preserve paired-read identities: {exc}",
                fix="Use one row per sample, distinct staged mate names, and matching compression formats.") from exc
    writes = [("--outdir", outdir, True),
              ("output writer lock", outdir.parent / f".{outdir.name}.nfclaw.lock", True),
              ("Nextflow work directory", work_dir, False),
              ("run provenance directory", outdir / "provenance", True),
              ("Nextflow state directory", outdir / ".nextflow", True),
              ("Nextflow log", runlog.nextflow_log_path(outdir, nxf_overlay), True)]
    writes += [(f"--{key.replace('_', '-')}", Path(value), True)
               for key, value in resolved.items()
               if key in output_only_dirs and isinstance(value, str) and value
               and not inputs.is_remote_url(value)]
    generated = ["params.json", "logs", "logs/run.log", "logs/stdout.txt", "logs/stderr.txt",
                 *([sheet.filename] if sheet is not None else [])]
    if limits is not None and not limits.is_empty():
        generated.append("resource_limits.config")
    if repair_compat:
        generated.append("fastqrepair_compat.config")
    compat_params = plugin_compat.removed_params_in_use(st.path)
    if compat_params:
        generated.append("nf_schema_compat.config")
    writes += [("generated run file", outdir / "provenance" / path, True) for path in generated]
    if check_only:
        writes.append(("check staging directory", Path(tempfile.gettempdir()), False))
    writes += input_safety.engine_write_paths(outdir, nxf_overlay)
    input_safety.check_write_boundaries(local_dependencies, writes)
    # A resource ceiling only exists if the engine enforces it; say so before anything runs.
    if limits is not None and not limits.is_empty():
        engine = engine_version.effective(nxf_overlay.get("NXF_VER"))
        if engine is not None and not engine_version.supports_resource_limits(engine):
            raise NfclawError(
                ErrorCode.PARAMS_INVALID,
                f"--limit-cpus/--limit-memory/--limit-time need Nextflow 24.04.0 or newer "
                f"(process.resourceLimits); this run would use Nextflow {engine}, which ignores "
                "the setting and would apply no ceiling at all.",
                fix="Run on Nextflow 24.04.0+ (--nxf-ver), or cap resources the way this release "
                    "documents (e.g. its --max-cpus/--max-memory/--max-time parameters).")
        if engine is None:
            raise NfclawError(
                ErrorCode.PARAMS_INVALID,
                "The Nextflow version could not be determined, so the requested resource "
                "ceiling cannot be verified (process.resourceLimits needs 24.04.0+).",
                fix="Select a concrete supported engine with --nxf-ver, or restore the engine's "
                    "version probe before requesting --limit-*.")

    # First, how the tree itself was resolved: running unreleased `dev` code (and, offline, a
    # possibly stale `dev` head) is said up front, so it is never mistaken for a release run.
    warnings = list(st.notes)
    warnings += _resume_advisory(outdir, st) if resume else []
    # Advisory only: preflight has confirmed nextflow is on PATH, so compare the installed
    # engine to the pipeline's declared requirement. Non-blocking — Nextflow is the authority
    # and enforces this itself at launch; we just surface it earlier with a clear message.
    warnings += engine_version.check(st.path, nxf_ver=nxf_overlay.get("NXF_VER"))
    # Same contract: advisory, never blocking. Explains a warning the pinned release will emit for a
    # reason that is invisible in its log, so it is not mistaken for a fault in the run or in nfclaw.
    warnings += plugin_compat.check(st.path)
    # Also advisory: a pinned plugin version with a known, inert bug (e.g. nf-core-utils@0.4.0's
    # spurious "positional argument `nextflow`" logged on every sarek run). Surfaced up front so the
    # log message arrives explained rather than re-investigated as a wrapper or samplesheet fault.
    warnings += plugin_compat.known_plugin_warnings(st.path)
    # Also advisory: steps whose results are measured to vary between executions of identical
    # input, so differences between runs or replays are expected rather than investigated.
    warnings += reproducibility.advisories(st.path, merged)
    if sheet is not None:
        # What the generated samplesheet holds and where it is, before the run starts (a --check
        # stages it in a temp directory: the result and the printed command name it).
        warnings.append(sheet.summary + ("" if check_only else
                                         f" It is staged as {resolved_input.value}."))
        warnings += sheet.notes
        if resume and (note := sheetgen.resume_note(outdir / "provenance" / sheet.filename, sheet)):
            warnings.append(note)
    if repair_compat:
        warnings.append("Applying recorded corrections for fastqrepair 1.1.1: split FASTQ only "
                        "where wiping the chunks equals wiping the whole file, sum repair reports "
                        "exactly, preserve declared mate identity, pass the declared quality offset to BBMap, and keep "
                        "singleton reads, logs and mate reports in distinct publications. "
                        "Pinned source stays unchanged; generated task recipes and the complete "
                        "splitter implementation are recorded in the compatibility config.")
    # Say them now, before Nextflow starts: a run can take hours, and one that fails never returns
    # its RunResult — an advisory that only arrives with the result arrives too late, or not at all.
    if on_warning is not None:
        for w in warnings:
            on_warning(w)

    issues = preflight.check_environment(profile=composed_profile, output_dir=outdir,
                                         submodule=st, repo_root=repo_root, resume=resume,
                                         work_dir=work_dir, allow_spaces=allow_spaces,
                                         check_only=check_only)
    if issues:
        raise NfclawError(ErrorCode.ENVIRONMENT, "Preflight checks failed.",
                          details={"issues": issues})

    with output_writer(outdir, check_only=check_only):
        # A competing writer may have completed between validation and lock acquisition.
        if issue := preflight._outdir_issue(outdir, resume=resume, check_only=check_only):
            raise NfclawError(ErrorCode.ENVIRONMENT, "Preflight checks failed.",
                              details={"issues": [issue]})
        # Capture the local dependency content the launch sees, before a long analysis can change it.
        # The replay guard uses these snapshots, rather than hashing a potentially changed input only
        # after the run has finished. Remote references and runtime downloads remain upstream inputs.
        input_snapshot = config_snapshot = pipeline_snapshot = None
        input_inventory = config_inventory = None
        if write_provenance and not check_only:
            try:
                input_snapshot, input_inventory = provenance.snapshot_inputs(prov_inputs)
            except OSError as exc:
                raise NfclawError(
                    ErrorCode.ENVIRONMENT, f"cannot snapshot local run dependencies: {exc}",
                    fix="Make the input data and configuration files readable before launching.") from exc
            if unverified_paths:
                warning = ("Local path parameters absent before launch were not input-snapshotted: "
                           + ", ".join(sorted(unverified_paths))
                           + ". Their schemas do not require existing paths; Nextflow validates "
                           "their use. Provenance records these paths as unverified.")
                warnings.append(warning)
                if on_warning is not None:
                    on_warning(warning)

        effective_resume = resume
        if resume:
            try:
                resume_inventory = (input_inventory if input_inventory is not None else
                                    _capture_input_inventory(prov_inputs)[1])
            except OSError as exc:
                raise NfclawError(ErrorCode.ENVIRONMENT,
                                  f"cannot inspect local inputs before resume: {exc}") from exc
            try:
                resume_digests = _input_file_digests(resume_inventory, input_snapshot)
            except OSError as exc:
                raise NfclawError(ErrorCode.ENVIRONMENT,
                                  f"cannot read local inputs before resume: {exc}") from exc
            if warning := _input_resume_warning(outdir, resume_inventory, resume_digests):
                effective_resume = False
                warnings.append(warning)
                if on_warning is not None:
                    on_warning(warning)

                if not check_only and outdir.exists():
                    archive = resume_safety.archive_previous_run(outdir, resume_inventory,
                                                                [st.path, *extra_configs])
                    warning = f"Preserved the previous run in {archive}; this output directory starts fresh."
                    warnings.append(warning)
                    if on_warning is not None:
                        on_warning(warning)

        # Where the files nfclaw generates for the run (params file, resource-limits config) are staged.
        # A real run stages them in its own provenance bundle. `--check` must not: it validates and
        # prints the command *without launching*, so it has to leave `--outdir` exactly as it found it —
        # creating it, or dropping a provenance/ directory in it, makes the next real run fail the
        # "--outdir is not empty" guard against a directory that holds no results at all. The staged
        # files are still written (to a temp directory that outlives the process), so the command
        # `--check` prints stays runnable as printed.
        if check_only:
            staging = Path(tempfile.mkdtemp(prefix="nfclaw-check-"))
        else:
            try:
                outdir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:            # preflight judged writability; this is the authority
                raise NfclawError(ErrorCode.ENVIRONMENT,
                                  f"--outdir could not be created: {exc.strerror or exc} "
                                  f"({exc.filename or outdir})",
                                  fix="Pass an --outdir in a directory you can write to.") from exc
            staging = outdir / "provenance"
        sheet_path = None
        if sheet is not None:
            # The bytes validated above, staged beside the params file that names them.
            sheet_path = sheetgen.write(sheet, staging)
            resolved["input"] = str(sheet_path)
        params_file_out = parameters.write_params_file(resolved, staging / "params.json")

        # A resource ceiling (--limit-cpus/--limit-memory/--limit-time) becomes a generated Nextflow
        # config passed with `-c`, exactly as nf-core's configuration docs prescribe. It goes *first*
        # so an explicit `--config` the caller passed still wins, and it lives in the provenance bundle
        # so `commands.sh` — which carries the same absolute `-c` path — replays the same ceiling.
        if limits is not None and not limits.is_empty():
            extra_configs.insert(0, resources.write_config(
                limits, staging / "resource_limits.config"))

        if repair_compat:
            extra_configs.insert(0, fastqrepair_compat.write_config(
                staging / "fastqrepair_compat.config", input_path=sheet_path or repair_input))

        # If the pinned release still sets an nf-validation 1.x param that nf-schema 2.x removed (the
        # `plugin_compat` advisory above), add those names to nf-schema's `validation.ignoreParams` via a
        # generated `-c` config, so its inert "not a valid parameter" warning does not clutter the run.
        # The release tree stays byte-identical (drift-check green) and results are unaffected. Inserted
        # before any user `--config` so the caller can still override, and staged like the ceiling above
        # so `commands.sh` replays it. Harmless when the param is absent (e.g. a real run that loads no
        # test profile): ignoring a name that is never set is a no-op.
        if compat_params:
            extra_configs.insert(0, plugin_compat.write_ignore_params_config(
                compat_params, staging / "nf_schema_compat.config"))

        # Pass the work dir explicitly so it stays off the outdir (shared, content-hashed — fine),
        # and any extra `-c` configs. nfclaw launches Nextflow from the outdir (below) so each run
        # gets its own .nextflow/ state, but the work dir must not move into the results.
        cmd, cmd_str = nextflow_command.build(
            upstream=st.path, profile=composed_profile, params_file=params_file_out,
            resume=effective_resume, work_dir=work_dir, extra_configs=tuple(extra_configs),
            bundle_params={"input": sheet_path} if sheet_path else None)
        replay_configs = tuple(dict.fromkeys([*extra_configs, params_file_out,
                                              *([sheet_path] if sheet_path else [])]))
        if write_provenance and not check_only:
            try:
                config_snapshot, config_inventory = provenance.snapshot_inputs(list(replay_configs))
                pipeline_snapshot = provenance.hash_pipeline(st.path)
            except OSError as exc:
                raise NfclawError(ErrorCode.ENVIRONMENT,
                                  f"cannot snapshot local run dependencies: {exc}",
                                  fix="Make the configuration and pipeline files readable before launching.") from exc

        if check_only:
            return RunResult(command=cmd_str, outdir=outdir, checked_only=True,
                             outputs_report=None, warnings=warnings, env=nxf_overlay, staging=staging,
                             local_dependencies=local_dependencies,
                             generated_samplesheet=sheet_path)

        generation_record = None
        if sheet is not None:
            generation_record = {**sheet.record, "file": sheet.filename,
                                 "sha256": provenance._sha256(sheet_path)}

        def record(outcome: str) -> None:
            provenance.write(outdir=outdir, pipeline=name, command_str=cmd_str, submodule=st,
                             input_paths=prov_inputs, env_extra=nxf_overlay, outcome=outcome,
                             chain=chain_link, input_checksums=input_snapshot,
                             input_inventory=input_inventory,
                             config_paths=replay_configs, config_checksums=config_snapshot,
                             config_inventory=config_inventory,
                             pipeline_checksums=pipeline_snapshot,
                             unverified_local_paths=unverified_paths,
                             nextflow_version=run_log.nextflow_version or "",
                             generated_samplesheet=generation_record)

        # Launch from the outdir so each run owns its `.nextflow/` history and cache: `-resume` then
        # resumes THIS run, never another pipeline's session. Paths in the command are absolute, so
        # the cwd only decides where the engine state lands — including Nextflow's own log.
        # The run is recorded at a fixed place, `<outdir>/provenance/logs/run.log` (see runner.runlog):
        # nobody launching it, in the foreground or the background, has to redirect it or be told where.
        # Its last line states the outcome and is written last of all — after the bundle — because it
        # is what a background run is polled on.
        logs_dir = outdir / "provenance" / "logs"
        run_log = runlog.RunLog.open(logs_dir, command=cmd, launch_dir=outdir,
                                     nextflow_log=runlog.nextflow_log_path(outdir, nxf_overlay),
                                     notes=warnings, env=nxf_overlay)
        try:
            try:
                execution.run(cmd, cwd=outdir, logs_dir=logs_dir,
                              timeout_seconds=timeout_seconds, env_extra=nxf_overlay,
                              run_log=run_log)
            except BaseException:
                # A failed run is exactly when the bundle is needed most: `commands.sh` is what replays
                # the run once the cause is fixed, and the checksums record what it did manage to
                # produce. Write it, then re-raise — a provenance error must never replace the real
                # failure as the cause.
                if write_provenance:
                    try:
                        record("failed")
                    except Exception:                     # best effort; must not mask the real failure
                        pass
                raise
            run_log.outcome = "success"
            try:
                report = outputs.collect(outdir)
                if write_provenance:
                    record("success")
            except BaseException as exc:
                # Nextflow succeeded but nfclaw could not finish (a full disk while hashing outputs, an
                # interrupt): the log's last line must not claim a success the bundle does not back.
                what = (execution.stop_outcome(exc)
                        if isinstance(exc, (KeyboardInterrupt, execution.Terminated)) else "failed")
                run_log.fail(f"{what} after Nextflow succeeded ({type(exc).__name__}: {exc})",
                             f"nfclaw: {type(exc).__name__}: {exc}")
                if isinstance(exc, OSError):
                    # Summarising the outputs and writing the bundle reads every result and writes
                    # beside them: a full disk or an unreadable file is a clear error that says the
                    # results exist, not a traceback that reads like the run itself crashed.
                    raise NfclawError(
                        ErrorCode.ENVIRONMENT,
                        f"The run succeeded, but its provenance bundle could not be written: "
                        f"{exc.strerror or exc}" + (f" ({exc.filename})" if exc.filename else ""),
                        fix=f"The results are in {outdir}. Free disk space or fix the permission, then "
                            "rerun the same command with --resume: every task is reused from the cache "
                            "and the bundle is written.") from exc
                raise
        finally:
            run_log.finish()
        return RunResult(command=cmd_str, outdir=outdir, checked_only=False,
                         outputs_report=report, warnings=warnings,
                         log_path=logs_dir / runlog.RUN_LOG_NAME, env=nxf_overlay,
                         generated_samplesheet=sheet_path)
