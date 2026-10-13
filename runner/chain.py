"""Pipeline chains: several pipelines run in sequence, each one's outputs handed to the next.

A chain is an ordered list of stages. Every stage is an ordinary `nfclaw run` — the same checks, run
log and provenance bundle — in its own directory `<outdir>/NN-<stage>/`, started only after the stage
before it succeeded. Between two stages a handoff rule (runner.handoff) turns the finished upstream
run into the downstream's parameters. The chain's own record lives in `<outdir>/chain/`: the spec,
each stage's state, the handoff snapshots and a log whose last line states the outcome — so a chain
can be resumed, extended, audited and reconstructed from disk. Deliberately linear: no DAG, no
scheduler, no daemon.
"""
from __future__ import annotations

import contextlib
import csv
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runner import (consumption, discovery, engine_version, execution, handoff, inputs,
                    input_safety, nextflow_command, orchestration, parameters, preflight,
                    provenance, resources, runlog, sheetgen, versions)
from runner import schema as schema_mod
from runner import outputs as output_mod
from runner import exact_json as json
from runner.errors import ErrorCode, NfclawError
from runner.probes import capture
from runner.submodule import SubmoduleStatus

try:
    import fcntl                                  # POSIX file locks (macOS/Linux)
except ImportError:                              # pragma: no cover — Windows has no fcntl
    fcntl = None

RECORD_DIRNAME = "chain"
LOG_NAME = "chain.log"
FINGERPRINT_VERSION = 2
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_OPTION_KEYS = {"profile", "nxf_ver", "nxf_env", "config", "limits"}
_CHAIN_KEYS = {"stages", "allow_spaces"} | _OPTION_KEYS
_STAGE_KEYS = {"id", "pipeline", "input", "params", "params_file", "pipeline_version",
               "retries", "demo", "handoff", "sheet_set"} | _OPTION_KEYS
_LIMIT_KEYS = {"cpus", "memory", "time"}
_PROBE_TIMEOUT = 300
# What the Nextflow launcher prints when it cannot set an engine up at all (no jars, no Java).
_ENGINE_DOWN = re.compile(r"Unable to initialize nextflow environment|CAPSULE EXCEPTION|"
                          r"Cannot download nextflow|Unable to download")


# --- the spec --------------------------------------------------------------------------------

@dataclass(frozen=True)
class Stage:
    index: int                        # 1-based position in the chain
    id: str
    pipeline: str
    input: Any                        # stage's own --input (usually only the first stage has one):
                                      # a value, or a list of data files to generate a sheet from
    params: dict                      # the stage's own pipeline parameters (as on the command line)
    params_file: Path | None
    pipeline_version: str | None
    retries: int                      # relaunches (with -resume) after a pipeline failure
    demo: bool
    handoff: dict | Path | None       # an inline rule, or a rule file, used INTO this stage
    # How this stage's Nextflow runs, where it differs from the chain's: `profile`, `nxf_ver`,
    # `nxf_env` (merged over the chain's), `configs`, `limits`. Releases of different ages can need
    # different engines — fetchngs 1.13 wants Nextflow >= 25.10.4, mag 5.5 >= 26.04, and an older
    # atacseq a parser before 26.04's strict one.
    options: dict = field(default_factory=dict)
    # Columns of the samplesheet nfclaw generates when `input` names data files (`--sheet-set`).
    sheet_set: dict = field(default_factory=dict)

    @property
    def dirname(self) -> str:
        return f"{self.index:02d}-{self.id}"


@dataclass(frozen=True)
class RunOptions:
    """How one stage's Nextflow runs — what the `nfclaw run` flags of the same names set."""
    profile: str = "docker"
    nxf_ver: str | None = None
    nxf_env: dict[str, str] = field(default_factory=dict)
    configs: tuple[str, ...] = ()
    limits: resources.ResourceLimits | None = None


@dataclass(frozen=True)
class ChainSpec:
    stages: tuple[Stage, ...]
    profile: str = "docker"
    nxf_ver: str | None = None
    nxf_env: dict[str, str] = field(default_factory=dict)
    configs: tuple[str, ...] = ()
    limits: resources.ResourceLimits | None = None
    allow_spaces: bool = False


def _bad(message: str) -> NfclawError:
    return NfclawError(ErrorCode.PARAMS_INVALID, f"chain spec: {message}",
                       fix="See docs/chaining.md for the spec format.")


def _abs(value: str) -> str:
    """A path in the spec, absolute — relative ones mean what they would on the command line."""
    return str(Path(value).expanduser().resolve())


def options(spec: ChainSpec, stage: Stage) -> RunOptions:
    """The run options of `stage`: the chain's, with the stage's own overrides on top."""
    o = stage.options
    return RunOptions(profile=o.get("profile", spec.profile),
                      nxf_ver=o.get("nxf_ver", spec.nxf_ver),
                      nxf_env=provenance.effective_nxf_env({**spec.nxf_env, **o.get("nxf_env", {})}),
                      configs=o.get("configs", spec.configs),
                      limits=o.get("limits", spec.limits))


def _parse_options(raw: dict, where: str) -> dict:
    """The run options `raw` sets (chain-wide or for one stage), validated like the `nfclaw run`
    flags of the same names; only the keys present are returned."""
    out: dict[str, Any] = {}
    if "profile" in raw:
        if not isinstance(raw["profile"], str) or not raw["profile"].strip():
            raise _bad(f"{where}: 'profile' must be a profile name such as \"docker\"")
        out["profile"] = raw["profile"]
    if "limits" in raw:
        limits = {} if raw["limits"] is None else raw["limits"]
        if not isinstance(limits, dict) or set(limits) - _LIMIT_KEYS:
            raise _bad(f"{where}: 'limits' takes only: {', '.join(sorted(_LIMIT_KEYS))}")
        cpus = limits.get("cpus")
        if cpus is not None and (not isinstance(cpus, int) or isinstance(cpus, bool)):
            raise _bad(f"{where}: 'limits.cpus' must be a whole number")
    if "config" in raw:
        configs = [] if raw["config"] is None else raw["config"]
        if not isinstance(configs, list) or not all(isinstance(c, str) for c in configs):
            raise _bad(f"{where}: 'config' must list Nextflow config file paths")
        out["configs"] = tuple(_abs(c) for c in configs)
    try:
        if "nxf_env" in raw:
            out["nxf_env"] = resources.parse_nxf_env(raw["nxf_env"] or {})
        if raw.get("nxf_ver"):
            out["nxf_ver"] = resources.check_nxf_version(raw["nxf_ver"])
        if "limits" in raw:
            lim = raw["limits"] or {}
            parsed = resources.parse(lim.get("cpus"), lim.get("memory"), lim.get("time"))
            out["limits"] = None if parsed.is_empty() else parsed
    except NfclawError as exc:
        raise _bad(f"{where}: {exc.message}") from None
    return out


def _options_json(opts: dict) -> dict:
    """Run options as a spec writes them (for chain.json)."""
    out: dict[str, Any] = {}
    for key in ("profile", "nxf_ver", "nxf_env"):
        if key in opts:
            out[key] = opts[key]
    if "configs" in opts:
        out["config"] = list(opts["configs"])
    if "limits" in opts:
        lim = opts["limits"]
        out["limits"] = ({k: v for k, v in (("cpus", lim.cpus), ("memory", lim.memory),
                                            ("time", lim.time)) if v is not None} if lim else {})
    return out


def load_spec(path: Path) -> ChainSpec:
    """Read a chain spec (JSON, or YAML when pyyaml is installed)."""
    return parse_spec(parameters.load_params_file(path, label="chain spec"))


def parse_spec(data: dict) -> ChainSpec:
    if not isinstance(data, dict):
        raise _bad("must be an object")
    if unknown := sorted(set(data) - _CHAIN_KEYS):
        raise _bad(f"unknown keys: {', '.join(unknown)}")
    raw_stages = data.get("stages")
    if not isinstance(raw_stages, list) or not raw_stages:
        raise _bad("'stages' must list at least one stage")
    stages: list[Stage] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_stages, start=1):
        if not isinstance(raw, dict) or not isinstance(raw.get("pipeline"), str):
            raise _bad(f"stage {index} must be an object with a 'pipeline'")
        if unknown := sorted(set(raw) - _STAGE_KEYS):
            raise _bad(f"stage {index}: unknown keys: {', '.join(unknown)}")
        sid = raw.get("id") or raw["pipeline"]
        if not isinstance(sid, str) or not _ID.fullmatch(sid):
            raise _bad(f"stage {index}: id {sid!r} must match {_ID.pattern}")
        if sid in seen:
            raise _bad(f"duplicate stage id '{sid}' (give one of them its own 'id')")
        seen.add(sid)
        retries = raw.get("retries", 0)
        if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0:
            raise _bad(f"stage '{sid}': 'retries' must be a whole number >= 0")
        params = raw.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise _bad(f"stage '{sid}': 'params' must be an object of pipeline parameters")
        demo = raw.get("demo", False)
        if not isinstance(demo, bool):
            raise _bad(f"stage '{sid}': 'demo' must be true or false")
        version = raw.get("pipeline_version")
        if version is not None and not isinstance(version, str):
            raise _bad(f"stage '{sid}': 'pipeline_version' must be a string such as \"3.27.0\"")
        hand = raw.get("handoff")
        if hand is not None and not isinstance(hand, (dict, str)):
            raise _bad(f"stage '{sid}': 'handoff' must be a rule object or a path to a rule file")
        params_file = raw.get("params_file")
        if params_file is not None and not isinstance(params_file, str):
            raise _bad(f"stage '{sid}': 'params_file' must be a path")
        # Keys as on the command line: `--skip-busco` and `skip_busco` name one parameter.
        params = {str(k).replace("-", "_"): v for k, v in params.items()}
        stage_input = raw.get("input")
        if "input" in params:                             # the same --input, written as a param
            if stage_input is not None:
                raise _bad(f"stage '{sid}': give its input once — 'input' or 'params.input'")
            stage_input = params.pop("input")
        if isinstance(stage_input, list) and not (
                stage_input and all(isinstance(v, str) and v.strip() for v in stage_input)):
            raise _bad(f"stage '{sid}': an 'input' list must name data files, directories or "
                       "glob patterns")
        sheet_set = raw.get("sheet_set")
        sheet_set = {} if sheet_set is None else sheet_set
        if not isinstance(sheet_set, dict):
            raise _bad(f"stage '{sid}': 'sheet_set' must map samplesheet columns to values")
        try:
            sheet_set = sheetgen.assignments_from_mapping(sheet_set)
        except NfclawError as exc:
            raise _bad(f"stage '{sid}': {exc.message}") from None
        stages.append(Stage(
            index=index, id=sid, pipeline=raw["pipeline"], input=stage_input,
            params=params,
            params_file=Path(_abs(params_file)) if params_file else None,
            pipeline_version=version or None, retries=retries,
            demo=demo,
            handoff=Path(_abs(hand)) if isinstance(hand, str) else hand,
            options=_parse_options(raw, f"stage '{sid}'"), sheet_set=sheet_set))
    chain_opts = _parse_options(data, "chain")
    allow_spaces = data.get("allow_spaces", False)
    if not isinstance(allow_spaces, bool):
        raise _bad("'allow_spaces' must be true or false")
    return ChainSpec(stages=tuple(stages), profile=chain_opts.get("profile", "docker"),
                     nxf_ver=chain_opts.get("nxf_ver"), nxf_env=chain_opts.get("nxf_env", {}),
                     configs=chain_opts.get("configs", ()), limits=chain_opts.get("limits"),
                     allow_spaces=allow_spaces)


# --- the plan: every stage and handoff resolved and checked before anything runs ------------

@dataclass(frozen=True)
class Planned:
    stage: Stage
    tree: SubmoduleStatus             # the pipeline code this stage runs
    rule: handoff.Rule | None         # the handoff INTO this stage (None for the first)
    input: Any                        # the stage's own --input, resolved (absolute when local)
    params: dict                      # its params + what the next stage's rule sets on it


def _rule_into(up: Stage, down: Stage, registry) -> handoff.Rule | None:
    if down.handoff is None:
        return registry.get((up.pipeline, down.pipeline))
    if isinstance(down.handoff, dict):
        return handoff.parse_rule(down.handoff, upstream=up.pipeline, downstream=down.pipeline,
                                  origin=f"inline handoff of stage '{down.id}'")
    return handoff.load_rule_file(down.handoff, upstream=up.pipeline, downstream=down.pipeline)


def plan(spec: ChainSpec, *, repo_root: Path) -> list[Planned]:
    """Resolve every stage's pipeline code and every handoff, and check how they fit together."""
    pdir = repo_root / "pipelines"
    for s in spec.stages:
        discovery.find(s.pipeline, pdir)                       # 404 before any git work
    registry = handoff.load_registry(repo_root)
    trees = [versions.ensure(s.pipeline, s.pipeline_version, pipelines_dir=pdir,
                             repo_root=repo_root) for s in spec.stages]
    rules: list[handoff.Rule | None] = [None]
    problems: list[str] = []
    for i in range(1, len(spec.stages)):
        up, down = spec.stages[i - 1], spec.stages[i]
        rule = _rule_into(up, down, registry)
        rules.append(rule)
        if rule is None:
            known = sorted(d for (u, d) in registry if u == up.pipeline)
            problems.append(
                f"no handoff from {up.pipeline} to {down.pipeline} (stage '{down.id}')"
                + (f"; {up.pipeline} feeds: {', '.join(known)}" if known else "")
                + f" — add handoffs/{up.pipeline}/{down.pipeline}.json, or give stage "
                  f"'{down.id}' an inline \"handoff\" (docs/chaining.md)")
            continue
        problems += handoff.check_rule(rule, trees[i - 1].path, trees[i].path)
        for key, value in rule.upstream_params.items():
            if key in up.params and up.params[key] != value:
                problems.append(f"stage '{up.id}' sets --{key}={up.params[key]}, but the handoff "
                                f"to '{down.id}' needs --{key}={value}")
    if problems:
        raise NfclawError(ErrorCode.PARAMS_INVALID, "The chain cannot run as specified.",
                          fix="Nothing was launched. Fix the stages or handoffs listed.",
                          details={"issues": problems})
    out: list[Planned] = []
    for i, s in enumerate(spec.stages):
        nxt = rules[i + 1] if i + 1 < len(rules) else None
        injected = dict(nxt.upstream_params) if nxt else {}
        ps = schema_mod.load_param_schema(trees[i].path)
        # Data files to generate the stage's samplesheet from are made absolute as given (a link
        # keeps the name its sample is called by); any other input as `nfclaw run` resolves it.
        # Whether listed files still exist matters only to a stage that runs (its own check refuses
        # them), not to one that already succeeded and is frozen.
        if isinstance(s.input, list):
            value = [sheetgen.absolute(v) for v in s.input]
        elif (source := sheetgen.detect(s.input, trees[i].path)) is not None:
            value = source.values[0]
        else:
            resolved = inputs.resolve(s.input, trees[i].path)
            value = resolved.value if resolved else None
        out.append(Planned(s, trees[i], rules[i], value,
                           parameters.resolve_path_params({**injected, **s.params}, ps)))
    return out


def _file_sha256(path: Path | None) -> str | None:
    return handoff.sha256_file(path) if path is not None and path.is_file() else None


def fingerprint(p: Planned, spec: ChainSpec | None = None) -> str:
    """What a stage would do. A stage that succeeded is frozen: resuming with a spec that changes
    its fingerprint is refused (no silent re-run, no stale results under a new definition)."""
    s = p.stage
    opts = options(spec, s) if spec is not None else options(ChainSpec(stages=(s,)), s)
    body = {"fingerprint_version": FINGERPRINT_VERSION,
            "pipeline": s.pipeline, "pipeline_version": s.pipeline_version,
            "commit": p.tree.commit, "input": p.input,
            "input_sha256": _file_sha256(Path(p.input)) if isinstance(p.input, str) else None,
            "params": p.params, "params_file": _file_sha256(s.params_file), "demo": s.demo,
            "handoff": p.rule.sha256() if p.rule else None,
            "options": _options_json({"profile": opts.profile, "nxf_ver": opts.nxf_ver,
                                      "nxf_env": opts.nxf_env, "configs": opts.configs,
                                      "limits": opts.limits}),
            "config_sha256": {c: _file_sha256(Path(c)) for c in opts.configs}}
    if s.sheet_set:                   # absent when unset: earlier chains keep their fingerprints
        body["sheet_set"] = dict(s.sheet_set)
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalized(spec: ChainSpec, planned: list[Planned]) -> dict:
    """The spec as `chain/chain.json` records it: absolute paths, so it means the same thing from any
    directory — it is what `--resume` without a spec, and a replay of the chain, re-read."""
    lim = spec.limits
    return {
        "profile": spec.profile, "nxf_ver": spec.nxf_ver, "nxf_env": dict(spec.nxf_env),
        "config": list(spec.configs), "allow_spaces": spec.allow_spaces,
        "limits": ({k: v for k, v in (("cpus", lim.cpus), ("memory", lim.memory),
                                      ("time", lim.time)) if v is not None} if lim else {}),
        "stages": [{"id": p.stage.id, "pipeline": p.stage.pipeline, "input": p.input,
                    "params": {k: v for k, v in p.params.items() if k in p.stage.params},
                    "params_file": str(p.stage.params_file) if p.stage.params_file else None,
                    "pipeline_version": p.stage.pipeline_version, "retries": p.stage.retries,
                    "demo": p.stage.demo,
                    "handoff": (str(p.stage.handoff) if isinstance(p.stage.handoff, Path)
                                else p.stage.handoff),
                    **({"sheet_set": dict(p.stage.sheet_set)} if p.stage.sheet_set else {}),
                    **_options_json(p.stage.options)}
                   for p in planned],
    }


# --- running it ----------------------------------------------------------------------------

@dataclass
class ChainResult:
    outdir: Path
    outcome: str
    stages: list[dict]
    commands: list[tuple[str, str]] = field(default_factory=list)   # --check: (stage, command)
    log_path: Path | None = None


def _write_json(path: Path, data: Any) -> Path:
    """Atomically: a reader polling state.json never sees half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


@contextlib.contextmanager
def _lock(record: Path, outdir: Path) -> Iterator[None]:
    """One chain process per --outdir: two would race on the same stages and state."""
    fd = None
    try:
        record.mkdir(parents=True, exist_ok=True)
        fd = os.open(record / ".lock", os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o644)
        if fcntl is not None:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(fd)
                fd = None
                raise NfclawError(
                    ErrorCode.ENVIRONMENT, f"another nfclaw chain is running in {outdir}",
                    fix=f"Wait for it (tail -n 1 {record / 'logs' / LOG_NAME}) or stop it with "
                        "kill <its pid>.") from None
    except OSError as exc:
        if fd is not None:
            os.close(fd)
            fd = None
        raise NfclawError(
            ErrorCode.ENVIRONMENT,
            f"chain directory could not be created or locked: {record}: {exc.strerror or exc}",
            fix="Use an output directory whose parent you can write to.") from exc
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)


def _retryable(exc: NfclawError) -> bool:
    """Only a pipeline that ran and failed is worth relaunching: a bad parameter, an invalid sheet or
    a missing tool fails the same way every time, and a timeout means the budget is spent."""
    return exc.code is ErrorCode.EXECUTION_FAILED and "timeout_seconds" not in exc.details


def _short(exc: NfclawError) -> str:
    code = exc.details.get("exit_code")
    return f"failed (exit status {code})" if code is not None else exc.code.value


def _warner(on_warning: Callable[[str], None] | None, stage: Stage):
    return None if on_warning is None else (lambda m: on_warning(f"[{stage.dirname}] {m}"))


def _say(log: runlog.RunLog, text: str) -> None:
    """A chain event: into the chain log, and onto the terminal between the stages' own output."""
    log.note(f"    {text}")
    print(f"nfclaw chain: {text}", file=sys.stderr, flush=True)


def _deferred(p: Planned) -> frozenset[str]:
    """The parameters of a stage its handoff will supply — unless the stage sets them itself."""
    if p.rule is None:
        return frozenset()
    return frozenset(t for t in p.rule.params
                     if not (t == "input" and p.input not in (None, "")) and t not in p.stage.params)


def _check(spec: ChainSpec, planned: list[Planned], *, repo_root: Path, outdir: Path,
           on_warning, keep: bool) -> list[tuple[str, str]]:
    """Validate each stage as `nfclaw run --check` would, writing nothing into --outdir. A later
    stage's handoff parameters do not exist yet; they are named as deferred, so only the stage's own
    parameters are judged (the handoff itself was checked statically by `plan`). `keep` keeps the
    files the printed commands name (for `--check`); the validation before a real run drops them."""
    commands = []
    for p in planned:
        opts = options(spec, p.stage)
        res = orchestration.run_pipeline(
            p.stage.pipeline, repo_root=repo_root, input_path=p.input,
            outdir=outdir / p.stage.dirname, profile=opts.profile,
            params_file=p.stage.params_file, cli_overrides=dict(p.params), resume=False,
            demo=p.stage.demo, check_only=True, write_provenance=False, timeout_seconds=None,
            pipeline_version=p.stage.pipeline_version, nxf_ver=opts.nxf_ver,
            nxf_env=opts.nxf_env, allow_spaces=spec.allow_spaces, configs=opts.configs,
            limits=opts.limits, on_warning=_warner(on_warning, p.stage),
            deferred_params=_deferred(p), resolved_tree=p.tree, sheet_set=p.stage.sheet_set)
        try:
            input_safety.check_write_boundaries(res.local_dependencies,
                [("chain --outdir", outdir, True),
                 ("Nextflow work directory", Path(res.env.get("NXF_WORK")
                  or os.environ.get("NXF_WORK") or repo_root / "work").expanduser().resolve(), False),
                 *input_safety.engine_write_paths(res.outdir, res.env)])
        except BaseException:
            if res.staging is not None:
                shutil.rmtree(res.staging, ignore_errors=True)
            raise
        if not keep and res.staging is not None:
            shutil.rmtree(res.staging, ignore_errors=True)
        label = p.stage.dirname
        if deferred := _deferred(p):                      # the printed command lacks them: say so
            flags = ", ".join(f"--{n.replace('_', '-')}" for n in sorted(deferred))
            label += f" — {flags} from the stage before it ({p.rule.origin})"
        commands.append((label, nextflow_command.shell_line(res.command, res.env)))
    return commands


def _probe_config(spec: ChainSpec, p: Planned, *, timeout_seconds: float | None = None) -> list[str]:
    """Whether the stage's Nextflow configuration parses with the engine it will run under.

    `nextflow config` resolves the pipeline's config and profiles without running anything (a few
    seconds). It catches the one failure no schema can predict: a release whose config the engine
    rejects outright — an older release on Nextflow 26's strict parser — which would otherwise
    surface only when that stage launches, after every stage before it has run. Run from a scratch
    directory so nothing lands in the output directory. A probe that cannot run or does not
    finish cannot establish configuration validity and blocks the chain before any launch."""
    opts = options(spec, p.stage)
    engine = f"Nextflow {opts.nxf_ver}" if opts.nxf_ver else "the installed Nextflow"
    label = f"{p.stage.dirname} ({p.stage.pipeline})"
    if shutil.which("nextflow") is None:
        return [f"{label}: configuration could not be verified — nextflow is not on PATH"]
    overlay = dict(opts.nxf_env)
    if opts.nxf_ver:
        overlay["NXF_VER"] = opts.nxf_ver
    # `-c` is the launcher's own option for `nextflow config` (`nextflow -c x.config config …`);
    # after the command it is rejected as unknown, unlike `nextflow run … -c x.config`.
    cmd = ["nextflow"]
    for cfg in opts.configs:
        cmd += ["-c", cfg]
    cmd += ["config", str(p.tree.path),
            "-profile", nextflow_command.compose_profile(opts.profile, demo=p.stage.demo)]
    probe_timeout = (min(_PROBE_TIMEOUT, timeout_seconds)
                     if timeout_seconds is not None else _PROBE_TIMEOUT)
    with tempfile.TemporaryDirectory(prefix="nfclaw-probe-") as scratch:
        try:
            r = capture(cmd, cwd=scratch, env={**os.environ, **overlay}, timeout=probe_timeout)
        except subprocess.TimeoutExpired:
            return [f"{label}: configuration could not be verified — {engine} did not finish "
                    f"its configuration probe within {probe_timeout:g} seconds"]
        except (OSError, subprocess.SubprocessError) as exc:
            return [f"{label}: configuration could not be verified — {engine}'s "
                    f"configuration probe could not run: {exc}"]
    if r.returncode == 0:
        return []
    report = (runlog.error_excerpt(r.stdout or "")
              + runlog.stderr_excerpt(r.stderr or "")) or [f"exit status {r.returncode}"]
    if _ENGINE_DOWN.search((r.stdout or "") + (r.stderr or "")):
        # The launcher could not set the engine up (a pinned version is downloaded on first use):
        # the stage could not start either, but not because of its configuration.
        return [f"{p.stage.dirname} ({p.stage.pipeline}): {engine} could not be started — "
                "Nextflow downloads a pinned engine on first use; check this host can:\n"
                + "\n".join(f"      {line}" for line in report)]
    # The engine the release was written for is the one it declares (docs/compatibility.md).
    declared = engine_version.minimum_version(
        engine_version.required_spec(p.tree.path / "nextflow.config"))
    hint = (f" — the release declares Nextflow {declared}: try \"nxf_ver\": \"{declared}\""
            if declared and declared != opts.nxf_ver else "")
    return [f"{p.stage.dirname} ({p.stage.pipeline}): {engine} cannot parse its "
            f"configuration{hint}:\n" + "\n".join(f"      {line}" for line in report)]


def _data_change(p: Planned, entry: dict, spec: ChainSpec, repo_root: Path) -> str | None:
    """For a succeeded stage whose samplesheet nfclaw generated from data files: the data files its
    --input now holds that the stage never analysed. A changed definition is caught by the
    fingerprint, which names only the data's path; this catches new data, which a resume would
    otherwise skip without a word. Data removed since is no change: a frozen stage never reads it
    again, so data that no longer yields a samplesheet at all is not refused either."""
    stage_dir = Path(entry["outdir"])
    manifest = _read_json(stage_dir / "provenance" / "run_manifest.json")
    record = manifest.get("generated_samplesheet") if isinstance(manifest, dict) else None
    if not isinstance(record, dict) or not isinstance(record.get("file"), str):
        return None
    try:
        source = sheetgen.detect(p.input, p.tree.path)
    except NfclawError:
        return None
    if source is None or not sheetgen.present(source):
        return None
    work_dir = orchestration.work_directory(options(spec, p.stage).nxf_env, repo_root)
    try:
        generated = sheetgen.generate(source, p.tree.path, pipeline=p.stage.pipeline,
                                      assignments=p.stage.sheet_set, outdir=stage_dir,
                                      work_dir=work_dir)
    except NfclawError:
        return None
    recorded = stage_dir / "provenance" / record["file"]
    used = sheetgen.named_paths(recorded)
    new = [path.name for path in generated.files if str(path) not in used]
    if not new:
        return None
    return (f"its --input data now yields a different samplesheet "
            f"({sheetgen.sheet_changes(recorded, generated)}) with files it never analysed: "
            + ", ".join(new[:5]) + (f" and {len(new) - 5} more" if len(new) > 5 else ""))


def _check_frozen(state: dict, planned: list[Planned], spec: ChainSpec,
                  repo_root: Path | None = None) -> None:
    problems = []
    if not isinstance(state.get("stages"), list) or any(
            not _valid_entry(s) for s in state["stages"]):
        raise _bad("the recorded chain stages are malformed")
    for i, old in enumerate(state.get("stages", [])):
        if old.get("status") != "success":
            continue
        if old.get("fingerprint_version") != FINGERPRINT_VERSION:
            problems.append(f"stage '{old.get('id')}' uses an older fingerprint format that did "
                            "not preserve its code and run options as immutable evidence; keep "
                            "this chain's outputs and start a new chain in a fresh --outdir")
            continue
        if i >= len(planned) or planned[i].stage.id != old.get("id"):
            problems.append(f"stage '{old.get('id')}' already succeeded as stage {i + 1}; a "
                            "resumed chain keeps its succeeded stages, in order")
        elif fingerprint(planned[i], spec) != old.get("fingerprint"):
            problems.append(f"stage '{old.get('id')}' already succeeded with a different definition "
                            "(its code, run options, input, params or handoff changed — including "
                            "what the handoff to the next stage sets on it)")
        elif repo_root is not None and (change := _data_change(planned[i], old, spec, repo_root)):
            problems.append(f"stage '{old.get('id')}' already succeeded, but {change}")
    if problems:
        raise NfclawError(ErrorCode.PARAMS_INVALID,
                          "This spec does not match the chain being resumed.",
                          fix="Edit or append only stages that have not succeeded, or run the "
                              "edited chain in a fresh --outdir.",
                          details={"issues": problems})


def run_chain(spec: ChainSpec | None, *, repo_root: Path, outdir: Path, check_only: bool = False,
              resume: bool = False, timeout_seconds: int | None = None,
              on_warning: Callable[[str], None] | None = None) -> ChainResult:
    """Run (or `check_only`: validate) a chain into `outdir`.

    Everything that can be judged before a pipeline runs is judged first — every stage's pipeline
    and version, every handoff against both schemas, every stage's own parameters, every stage's
    config parsed by its own engine — so a mistake in the last stage never surfaces after the first
    has run for hours. `resume` continues the chain
    recorded in `outdir` (with `spec`, or the recorded one when it is None)."""
    deadline = None if timeout_seconds is None else time.monotonic() + timeout_seconds
    record = outdir / RECORD_DIRNAME
    state = _read_json(record / "state.json") if resume else None
    if resume and not isinstance(state, dict):
        raise NfclawError(ErrorCode.ENVIRONMENT, f"no chain to resume in {outdir}",
                          fix="Start it without --resume, or check the --outdir.")
    if spec is None:
        if not resume:
            raise NfclawError(ErrorCode.PARAMS_INVALID, "a chain spec is required",
                              fix="Pass the spec file, or --resume an existing chain.")
        spec = parse_spec(_read_json(record / "chain.json") or {})
    if not resume and (issue := preflight._outdir_issue(outdir, resume=False,
                                                        check_only=check_only)):
        raise NfclawError(ErrorCode.ENVIRONMENT, "Preflight checks failed.",
                          details={"issues": [issue.replace("to continue that run",
                                                            "to continue that chain")]})
    planned = plan(spec, repo_root=repo_root)
    if state is not None:
        _check_frozen(state, planned, spec, repo_root)
    done = {s.get("id") for s in (state or {}).get("stages", []) if s.get("status") == "success"}
    # A real run says each stage's advisories when that stage launches; only --check says them here.
    todo = [p for p in planned if p.stage.id not in done]
    commands = _check(spec, todo, repo_root=repo_root, outdir=outdir,
                      on_warning=on_warning if check_only else None, keep=check_only)
    unparsable = []
    for p in todo:
        remaining = None if deadline is None else deadline - time.monotonic()
        if remaining is not None and remaining <= 0:
            raise NfclawError(
                ErrorCode.EXECUTION_FAILED, "The chain's --timeout ran out during validation.",
                details={"timeout_seconds": timeout_seconds})
        unparsable += _probe_config(spec, p, timeout_seconds=remaining)
    if deadline is not None and time.monotonic() >= deadline:
        raise NfclawError(
            ErrorCode.EXECUTION_FAILED, "The chain's --timeout ran out during validation.",
            details={"timeout_seconds": timeout_seconds})
    if unparsable:
        raise NfclawError(
            ErrorCode.ENVIRONMENT, "A stage could not start: its Nextflow engine cannot set it up.",
            fix=("Nothing was launched. Resolve the reported engine, configuration, network or "
                 "probe timeout issue and retry. Give each stage an engine that runs here and "
                 "parses its release — its \"nxf_ver\" in the spec entry (see 'Nextflow too new for an older "
                 f"release' in {runlog.known_issues_path()}) — and run the chain again."),
            details={"issues": unparsable})
    if check_only:
        return ChainResult(outdir=outdir, outcome="checked", stages=[], commands=commands)
    return _execute(spec, planned, state, repo_root=repo_root, outdir=outdir,
                    timeout_seconds=timeout_seconds, on_warning=on_warning, deadline=deadline)


def _new_entry(p: Planned, outdir: Path, spec: ChainSpec) -> dict:
    return {"id": p.stage.id, "pipeline": p.stage.pipeline, "index": p.stage.index,
            "outdir": str(outdir / p.stage.dirname), "status": "pending",
            "fingerprint": fingerprint(p, spec), "version": None, "commit": None, "handoff": None,
            "fingerprint_version": FINGERPRINT_VERSION,
            "attempts": []}


def _execute(spec: ChainSpec, planned: list[Planned], state: dict | None, *, repo_root: Path,
             outdir: Path, timeout_seconds: int | None, on_warning,
             deadline: float | None = None) -> ChainResult:
    record = outdir / RECORD_DIRNAME
    outdir.mkdir(parents=True, exist_ok=True)
    with _lock(record, outdir):
        current = _read_json(record / "state.json")
        if state is None:
            if (record / "state.json").exists() or any(p.name != RECORD_DIRNAME
                                                       for p in outdir.iterdir()):
                raise NfclawError(ErrorCode.ENVIRONMENT,
                                  f"{outdir} was populated by another run before launch",
                                  fix="Use --resume for its recorded chain, or a fresh --outdir.")
        else:
            if not isinstance(current, dict):
                raise NfclawError(ErrorCode.ENVIRONMENT,
                                  f"the chain record in {outdir} changed before launch",
                                  fix="Restore the recorded chain before resuming it.")
            state = current
            _check_frozen(state, planned, spec)
            if issues := _integrity_problems(state, only_succeeded=True):
                raise NfclawError(
                    ErrorCode.ENVIRONMENT, "The succeeded stages of this chain no longer verify.",
                    fix="Restore their recorded files and provenance, or use a fresh --outdir.",
                    details={"issues": issues})
        previous = {s.get("id"): s for s in (state or {}).get("stages", [])}
        stages = []
        for p in planned:
            old = previous.get(p.stage.id)
            if old and old.get("status") == "success":
                stages.append(old)                            # frozen (see _check_frozen)
            else:                                             # keep the attempt history
                stages.append({**_new_entry(p, outdir, spec),
                               "attempts": (old or {}).get("attempts", [])})
        state = {"chain_id": (state or {}).get("chain_id") or uuid.uuid4().hex,
                 "created": (state or {}).get("created") or runlog.now(),
                 "outcome": "running", "stages": stages}
        _write_json(record / "chain.json", normalized(spec, planned))
        _write_json(record / "state.json", state)
        log = runlog.RunLog(record / "logs" / LOG_NAME, label="chain")
        # The same header as a run's, so `runlog.read_state` — `nfclaw status` — tells a chain still
        # running from one whose nfclaw was killed outright (the only way it ends without a last line).
        log.note(f"==> nfclaw chain started {runlog.now()}")
        log.note(f"    launch dir: {outdir}")
        for line in runlog.host_header():
            log.note(line)
        log.note(f"    pid: {os.getpid()}")
        log.note(f"    {len(planned)} stages: " + " → ".join(p.stage.dirname for p in planned))
        print(f"nfclaw: logging this chain to {log.path}", file=sys.stderr, flush=True)
        try:
            for i, p in enumerate(planned):
                entry = state["stages"][i]
                if entry["status"] == "success":
                    manifest = _read_json(Path(entry["outdir"]) / "provenance"
                                          / "run_manifest.json")
                    if not (isinstance(manifest, dict) and manifest.get("outcome") == "success"):
                        raise NfclawError(
                            ErrorCode.ENVIRONMENT,
                            f"stage '{p.stage.id}' is recorded as succeeded, but its provenance "
                            f"bundle no longer says so ({entry['outdir']})",
                            fix="Run the chain in a fresh --outdir.")
                    _say(log, f"{p.stage.dirname}: already succeeded — skipped")
                    continue
                _run_stage(p, planned[i - 1] if i else None, entry, state, spec=spec,
                           repo_root=repo_root, outdir=outdir, deadline=deadline,
                           budget=timeout_seconds, log=log, on_warning=on_warning)
                if issues := _integrity_problems(state, only_succeeded=True):
                    raise NfclawError(
                        ErrorCode.HANDOFF_FAILED, "Completed stage lineage does not verify.",
                        fix="Keep source data unchanged throughout execution; restore verified "
                            "evidence or run the chain into a fresh output directory.",
                        details={"issues": issues})
            state["outcome"] = log.outcome = "success"
        except BaseException as exc:
            if state["outcome"] == "running":                 # not set by _run_stage: say why
                if isinstance(exc, (KeyboardInterrupt, execution.Terminated)):
                    state["outcome"] = execution.stop_outcome(exc)
                else:
                    reason = exc.message if isinstance(exc, NfclawError) else type(exc).__name__
                    state["outcome"] = f"failed ({reason})"
            log.fail(state["outcome"], str(exc) if isinstance(exc, NfclawError) else "")
            raise
        finally:
            state["updated"] = runlog.now()
            _write_json(record / "state.json", state)
            log.finish()
    return ChainResult(outdir=outdir, outcome=state["outcome"], stages=state["stages"],
                       log_path=log.path)


def _run_stage(p: Planned, prev: Planned | None, entry: dict, state: dict, *, spec: ChainSpec,
               repo_root: Path, outdir: Path, deadline: float | None, budget: int | None,
               log: runlog.RunLog, on_warning) -> None:
    stage, record = p.stage, outdir / RECORD_DIRNAME
    stage_dir = outdir / stage.dirname
    warn = _warner(on_warning, stage)
    overrides, input_path = dict(p.params), p.input
    link: dict[str, Any] = {"id": state["chain_id"], "record": str(record), "stage": stage.id,
                            "index": stage.index, "upstream": None}
    if prev is not None:
        dest = record / "handoffs" / stage.dirname
        if dest.exists():
            dest = dest / "attempts" / uuid.uuid4().hex
        _say(log, f"{stage.dirname}: preparing its input from {prev.stage.dirname} "
                  f"({p.rule.origin})")
        try:
            explicit = frozenset(name for name in p.rule.params
                                 if (p.input if name == "input" else p.stage.params.get(name))
                                 not in (None, ""))
            hand = handoff.materialize(p.rule, upstream_outdir=outdir / prev.stage.dirname,
                                       downstream_tree=p.tree.path, dest=dest,
                                       exclude_params=explicit)
        except NfclawError:
            entry["status"] = "failed"
            state["outcome"] = f"failed at stage {stage.dirname}: handoff"
            raise
        hand_path = _write_json(dest / "handoff.json",
                                {**hand.record, "from_stage": prev.stage.id, "to_stage": stage.id})
        entry["handoff"] = str(hand_path)
        if warn:
            for name in sorted(explicit):
                warn(f"--{name} is set by this stage itself; the value handed over from "
                     f"'{prev.stage.id}' is not used")
        for name, item in hand.record["params"].items():
            if dropped := item.get("dropped_rows"):
                _say(log, f"{stage.dirname}: {len(dropped)} row(s) of the {name} samplesheet "
                          f"{stage.pipeline} does not accept were dropped (recorded in "
                          f"{hand_path})")
        for name, value in hand.params.items():
            explicit = p.input if name == "input" else p.stage.params.get(name)
            if explicit not in (None, ""):
                if warn:
                    warn(f"--{name} is set by this stage itself; the value handed over from "
                         f"'{prev.stage.id}' ({value}) is not used")
            elif name == "input":
                input_path = value
            else:
                overrides[name] = value
        link["upstream"] = {"stage": prev.stage.id, "pipeline": prev.stage.pipeline,
                            "outdir": str(outdir / prev.stage.dirname), "handoff": str(hand_path),
                            "handoff_sha256": handoff.sha256_file(hand_path)}
    # A previous attempt of this stage left its run here: continue it with Nextflow's cache.
    resume = stage_dir.is_dir() and any(stage_dir.iterdir())
    attempt = 0
    while True:
        attempt += 1
        remaining = None if deadline is None else int(deadline - time.monotonic())
        if remaining is not None and remaining <= 0:
            entry["status"] = "failed"
            state["outcome"] = f"timed out after {budget} s"
            raise NfclawError(ErrorCode.EXECUTION_FAILED,
                              f"The chain's --timeout ran out before stage {stage.dirname}.",
                              fix="Resume the chain with --resume (and a larger --timeout).",
                              details={"timeout_seconds": budget})
        entry["status"] = "running"
        entry["attempts"].append({"started": runlog.now(), "resume": resume})
        _write_json(record / "state.json", state)
        _say(log, f"{stage.dirname}: {stage.pipeline} " + (f"attempt {attempt} " if attempt > 1
                                                           else "") + "started — log "
                  f"{stage_dir / 'provenance' / 'logs' / runlog.RUN_LOG_NAME}")
        opts = options(spec, stage)
        try:
            orchestration.run_pipeline(
                stage.pipeline, repo_root=repo_root, input_path=input_path, outdir=stage_dir,
                profile=opts.profile, params_file=stage.params_file, cli_overrides=overrides,
                resume=resume, demo=stage.demo, check_only=False, write_provenance=True,
                timeout_seconds=remaining, pipeline_version=stage.pipeline_version,
                nxf_ver=opts.nxf_ver, nxf_env=opts.nxf_env, allow_spaces=spec.allow_spaces,
                configs=opts.configs, limits=opts.limits, on_warning=warn, chain_link=link,
                resolved_tree=p.tree, sheet_set=p.stage.sheet_set)
        except NfclawError as exc:
            entry["attempts"][-1].update(finished=runlog.now(), outcome=_short(exc))
            if _retryable(exc) and attempt <= stage.retries:
                _say(log, f"{stage.dirname}: attempt {attempt} {_short(exc)}; retrying with "
                          f"-resume ({attempt}/{stage.retries})")
                resume = True
                continue
            entry["status"] = "failed"
            state["outcome"] = (f"timed out after {budget} s" if "timeout_seconds" in exc.details
                                else f"failed at stage {stage.dirname}: {_short(exc)}")
            raise
        except (KeyboardInterrupt, execution.Terminated) as exc:
            entry["attempts"][-1].update(finished=runlog.now(),
                                         outcome=execution.stop_outcome(exc))
            entry["status"] = "stopped"
            state["outcome"] = f"{execution.stop_outcome(exc)} (stage {stage.dirname})"
            raise
        break
    manifest = _read_json(stage_dir / "provenance" / "run_manifest.json") or {}
    entry["attempts"][-1].update(finished=runlog.now(), outcome="success")
    entry.update(status="success", version=manifest.get("version"), commit=manifest.get("commit"))
    _write_json(record / "state.json", state)
    _say(log, f"{stage.dirname}: success ({stage.pipeline} {manifest.get('version') or ''})".rstrip())


# --- lineage: reconstructing and verifying a chain from disk -----------------------------------

def _record_for(path: Path) -> Path:
    if (path / RECORD_DIRNAME / "state.json").is_file():
        return path / RECORD_DIRNAME
    manifest = _read_json(path / "provenance" / "run_manifest.json") or {}
    record = (manifest.get("chain") or {}).get("record") if isinstance(manifest, dict) else None
    if record and (Path(record) / "state.json").is_file():
        return Path(record)
    raise NfclawError(ErrorCode.ENVIRONMENT, f"no chain recorded in or for {path}",
                      fix="Pass a chain's --outdir, or the outdir of one of its stages.")


def _digests(path: Path, *, relative: bool = True) -> dict[str, str]:
    """`hash  name` lines (outputs.sha256 names are relative, inputs.sha256 absolute) as
    {name: hash}."""
    return provenance.read_checksums(path, relative=relative)


def _sha(path: Path) -> str | None:
    try:
        return handoff.sha256_file(path)
    except OSError:
        return None


def _valid_entry(entry: Any) -> bool:
    return (isinstance(entry, dict)
            and all(isinstance(entry.get(k), str) for k in ("id", "pipeline", "outdir", "status"))
            and isinstance(entry.get("index"), int) and not isinstance(entry["index"], bool)
            and entry["index"] > 0)


def _integrity_problems(state: dict, *, only_succeeded: bool = False) -> list[str]:
    """Verify recorded stage outcomes and the current bytes behind every completed link."""
    problems: list[str] = []
    entries = state.get("stages")
    if not isinstance(entries, list) or not entries:
        return ["chain state has no valid stages list"]
    manifests: dict[str, dict] = {}
    output_indices: dict[str, dict[str, str]] = {}
    current_outputs: dict[str, dict[str, str | None]] = {}
    for i, entry in enumerate(entries, start=1):
        if not _valid_entry(entry):
            problems.append("chain state contains a malformed stage record")
            continue
        if entry["index"] != i:
            problems.append(f"{entry['id']}: its recorded index does not match its chain position")
        if state.get("outcome") == "success" and entry["status"] != "success":
            problems.append(f"{entry['id']}: the chain reports success but this stage has not succeeded")
        if entry["status"] != "success":
            continue
        sid, down = entry["id"], Path(entry["outdir"])
        manifest = _read_json(down / "provenance" / "run_manifest.json")
        if not isinstance(manifest, dict) or manifest.get("outcome") != "success":
            problems.append(f"{sid}: recorded as succeeded, but its provenance bundle no longer "
                            f"says so ({down})")
            continue
        manifests[sid] = manifest
        link = manifest.get("chain")
        if (not isinstance(link, dict) or link.get("id") != state.get("chain_id")
                or link.get("stage") != sid or link.get("index") != entry["index"]):
            problems.append(f"{sid}: its stage manifest does not belong to this chain")
        for key in ("version", "commit"):
            if entry.get(key) != manifest.get(key):
                problems.append(f"{sid}: its recorded {key} does not match its stage manifest")
        try:
            outputs = _digests(down / "provenance" / "outputs.sha256")
            historical_nodes = output_mod.recorded_inventory(down, outputs)
            live, current_nodes, _ = output_mod.snapshot(down, _sha)
            if historical_nodes is not None and historical_nodes != current_nodes:
                problems.append(f"{sid}: its published output namespace changed since the recorded run; "
                                + output_mod.namespace_difference(historical_nodes, current_nodes))
        except (OSError, ValueError) as exc:
            problems.append(f"{sid}: cannot verify its output checksums: {exc}")
            continue
        output_indices[str(down)] = outputs
        current_outputs[str(down)] = live
        for rel, digest in outputs.items():
            actual = live.get(rel)
            if actual != digest:
                problems.append(f"{sid}: upstream result {rel} changed or is missing since the "
                                "recorded run")
    for i, entry in enumerate(entries):
        if not _valid_entry(entry):
            continue
        succeeded = entry["status"] == "success"
        if only_succeeded and not succeeded:
            continue
        if not entry.get("handoff"):
            if succeeded and i:
                problems.append(f"{entry['id']}: its handoff record is missing")
            continue
        sid = entry["id"]
        if not isinstance(entry["handoff"], str):
            problems.append(f"{sid}: its handoff path is malformed")
            continue
        hand_path = Path(entry["handoff"])
        rec = _read_json(hand_path)
        if not isinstance(rec, dict):
            problems.append(f"{sid}: its handoff record is missing or unreadable ({hand_path})")
            continue
        params, upstream = rec.get("params"), rec.get("upstream")
        if (not isinstance(params, dict) or not isinstance(upstream, dict)
                or not isinstance(upstream.get("outdir"), str)):
            problems.append(f"{sid}: its handoff record is malformed ({hand_path})")
            continue
        previous = entries[i - 1] if i else None
        if not isinstance(previous, dict) or upstream["outdir"] != previous.get("outdir"):
            problems.append(f"{sid}: its handoff does not name the preceding stage")
        down = Path(entry["outdir"])
        manifest = manifests.get(sid, {})
        recorded_params = _read_json(down / "provenance/params.json") or {}

        def consumed_reference_root(reference: Path, name: str) -> Path:
            root = inputs.absolute_local_path(reference)
            value = recorded_params.get(name) if isinstance(recorded_params, dict) else None
            # Older bundles passed the fully resolved target. Read their actual parameters;
            # do not rewrite the historical consumption record to today's alias behavior.
            if value is not None:
                params_path = down / "provenance/params.json"
                configs = _digests(down / "provenance/configs.sha256", relative=False)
                if configs.get(str(params_path)) != _sha(params_path):
                    raise ValueError("recorded reference parameters differ from their config checksum")
                if not isinstance(value, str) or value not in {str(root), str(reference.resolve())}:
                    raise ValueError("recorded reference parameter differs from its handoff")
                root = Path(value)
            return root
        chain_link = manifest.get("chain")
        link = chain_link.get("upstream") if isinstance(chain_link, dict) else None
        if succeeded and (not isinstance(link, dict)
                          or link.get("handoff_sha256") != _sha(hand_path)):
            problems.append(f"{sid}: the handoff record is not the one this stage ran with")
        up_dir = Path(upstream["outdir"])
        up_out = output_indices.get(str(up_dir))
        if up_out is None:
            try:
                up_out = _digests(up_dir / "provenance" / "outputs.sha256")
            except (OSError, ValueError) as exc:
                problems.append(f"{sid}: cannot verify upstream output checksums: {exc}")
                up_out = {}
        down_in: dict[str, str] = {}
        down_nodes = None
        if succeeded and params:
            try:
                down_in = _digests(down / "provenance" / "inputs.sha256", relative=False)
                strict = any(isinstance(item, dict) and ("directory_reference" in item
                             or "input_inventory" in item or "consumed_inventory" in item)
                             for item in params.values())
                down_nodes = handoff.recorded_input_inventory(down, allow_legacy=not strict)
            except (OSError, ValueError) as exc:
                problems.append(f"{sid}: cannot verify its input checksums: {exc}")
                down_nodes = {}
        for name, item in params.items():
            if not isinstance(item, dict) or not isinstance(item.get("derived_from"), dict):
                problems.append(f"{sid}: --{name} has a malformed handoff source record")
                continue
            if any(key in item for key in ("consumed_sources", "consumed_dependencies", "consumed_inventory")):
                try:
                    sources = item.get("consumed_sources")
                    if (not isinstance(sources, list) or not sources
                            or any(not isinstance(value, str) or not Path(value).is_absolute()
                                   for value in sources)):
                        raise ValueError("malformed local consumed sources")
                    evidence = handoff.consumption_evidence([Path(value) for value in sources], up_dir)
                    if any(item.get(key) != value for key, value in evidence.items()):
                        raise ValueError("local data changed since its handoff boundary")
                    scalar = item.get("consumed_scalar", False)
                    if type(scalar) is not bool:
                        raise ValueError("malformed scalar consumption mode")
                    if succeeded and not consumption.agrees(evidence, down_in, down_nodes, scalar=scalar):
                        raise ValueError("local handoff data is not the input this stage hashed")
                except (OSError, ValueError, RuntimeError, csv.Error) as exc:
                    problems.append(f"{sid}: --{name}: cannot verify consumed data: {exc}")
            elif succeeded:
                try:
                    paths = handoff.legacy_consumption_paths(item, up_dir)
                    if paths:
                        evidence = handoff.consumption_evidence(paths, up_dir)
                        if not consumption.agrees(evidence, down_in, down_nodes,
                                                  scalar=item.get("kind") in ("file", "upstream_param")):
                            raise ValueError("legacy handoff data is not the input this stage hashed")
                except (OSError, ValueError, RuntimeError, csv.Error) as exc:
                    problems.append(f"{sid}: --{name}: cannot verify consumed data: {exc}")
            if "sha256" in item:
                value = item.get("value")
                if not isinstance(value, str) or _sha(Path(value)) != item["sha256"]:
                    problems.append(f"{sid}: --{name} snapshot {value} changed since the handoff")
                if succeeded and (not isinstance(value, str)
                                  or down_in.get(value) != item["sha256"]):
                    problems.append(f"{sid}: --{name} is not the snapshot this stage hashed")
            for rel, digest in item["derived_from"].items():
                if (not isinstance(rel, str) or not handoff._relative(rel)
                        or not isinstance(digest, str) or len(digest) != 64
                        or up_out.get(rel) != digest):
                    problems.append(f"{sid}: --{name}: {rel} is not what the upstream run "
                                    "produced")
                elif (current_outputs[str(up_dir)].get(rel) if str(up_dir) in current_outputs
                      else _sha(up_dir / rel)) != digest:
                    problems.append(f"{sid}: --{name}: upstream result {rel} changed or is "
                                    "missing since the handoff")
            dependencies = item.get("input_dependencies", {})
            if not isinstance(dependencies, dict):
                problems.append(f"{sid}: --{name} has malformed input dependencies")
                continue
            if "directory_reference" in item:
                reference = item["directory_reference"]
                try:
                    if not isinstance(reference, str) or not Path(reference).is_absolute():
                        raise ValueError("directory reference is not an absolute path")
                    evidence = handoff.directory_reference_evidence(Path(reference), up_dir, boundary=item)
                    if any(item.get(key) != value for key, value in evidence.items()):
                        raise ValueError("directory handoff has no matching complete namespace record")
                    if succeeded:
                        root = consumed_reference_root(Path(reference), name)
                        normalized = handoff.normalize_reference_inventory(evidence["directory_inventory"],
                                                                           Path(reference), destination=root)
                        consumed = {path: entry for path, entry in down_nodes.items()
                                    if Path(path).is_relative_to(root)}
                        source_files = (evidence["bundle_dependencies"] if "bundle_dependencies" in evidence
                                        else evidence.get("input_dependencies") or
                                        {str(up_dir / path): digest for path, digest in
                                         evidence.get("output_dependencies", {}).items()})
                        expected = {str(root / Path(path).relative_to(reference)): digest
                                    for path, digest in source_files.items()}
                        consumed_files = {path: digest for path, digest in down_in.items()
                                          if Path(path).is_relative_to(root)}
                        if normalized != consumed or expected != consumed_files:
                            problems.append(f"{sid}: --{name}: reference directory {reference} is "
                                            "not the input inventory this stage hashed")
                except (OSError, ValueError, RuntimeError) as exc:
                    problems.append(f"{sid}: --{name}: cannot verify reference directory {reference}: {exc}")
            if dependencies and "directory_reference" not in item:
                try:
                    up_in = _digests(up_dir / "provenance/inputs.sha256", relative=False)
                    up_nodes = handoff.recorded_input_inventory(up_dir, allow_legacy=True)
                    for value, digest in dependencies.items():
                        if not isinstance(value, str) or not Path(value).is_absolute():
                            raise ValueError("external reference is not an absolute path")
                        path = Path(value)
                        if up_nodes is None:
                            if ("input_inventory" in item or up_in.get(value) != digest or _sha(path) != digest):
                                problems.append(f"{sid}: --{name}: legacy external reference {value} changed "
                                                "or has no matching upstream checksum")
                            if succeeded and down_in.get(value) != digest:
                                problems.append(f"{sid}: --{name}: legacy external reference {value} is not "
                                                "the input this stage hashed")
                            continue
                        actual, nodes = provenance.snapshot_inputs([path])
                        expected_nodes = {value: up_nodes[value]} if value in up_nodes else {}
                        if (up_in.get(value) != digest or actual != {value: digest}
                                or nodes != expected_nodes or item.get("input_inventory") != expected_nodes):
                            problems.append(f"{sid}: --{name}: external reference {value} changed "
                                            "or has no matching complete upstream input record")
                            continue
                        if succeeded:
                            root = consumed_reference_root(path, name)
                            canonical = str(root)
                            normalized = handoff.normalize_reference_inventory(expected_nodes, path, destination=root)
                            if down_in.get(canonical) != digest or down_nodes.get(canonical) != normalized[canonical]:
                                problems.append(f"{sid}: --{name}: external reference {value} is not "
                                                "the input this stage hashed")
                except (OSError, ValueError, RuntimeError) as exc:
                    problems.append(f"{sid}: --{name}: cannot verify external reference: {exc}")
    return problems


def status(path: Path) -> tuple[dict, list[str]]:
    """The chain recorded at (or for) `path`, and every broken link in it.

    A link holds when the downstream ran with exactly the recorded handoff (its manifest names the
    handoff's hash), the snapshot is unchanged and is the input the downstream hashed, and every
    upstream file the handoff drew on is what the upstream run recorded producing."""
    record = _record_for(path.expanduser().resolve())
    state = _read_json(record / "state.json")
    if not isinstance(state, dict):
        raise NfclawError(ErrorCode.ENVIRONMENT, f"chain state is missing or malformed in {record}",
                          fix="Restore the chain record before checking or resuming it.")
    live = runlog.read_state(record / "logs" / LOG_NAME)
    state["log_state"], state["log_pid"], state["log_host"] = live.state, live.pid, live.host
    problems = _integrity_problems(state)
    return state, problems


def status_exit_code(state: dict, problems: list[str]) -> int:
    """As `nfclaw status`: 0 succeeded (and every link verified), 3 still running, 1 otherwise."""
    if problems or state.get("log_state") == "dead":
        return 1
    if state.get("log_state") == "running":
        return 3
    return 0 if state.get("outcome") == "success" else 1


def format_status(state: dict, problems: list[str]) -> str:
    outcome = state.get("outcome", "?")
    if state.get("log_state") == "running":
        outcome = f"running (nfclaw pid {state.get('log_pid')} on {state.get('log_host')})"
    elif state.get("log_state") == "dead":
        outcome = (f"stopped without an outcome — nfclaw (pid {state.get('log_pid')}) is no longer "
                   "running and never recorded how the chain ended (SIGKILL, out of memory, a "
                   "restart); resume it with --resume")
    lines = [f"chain {state.get('chain_id', '?')}: {outcome}"]
    stages = state.get("stages", [])
    stages = stages if isinstance(stages, list) else []
    for i, s in enumerate(stages):
        if not _valid_entry(s):
            continue
        ver = f"{s.get('version') or '?'} ({(s.get('commit') or '')[:12]})"
        lines.append(f"  {s['index']:02d}-{s['id']:<18} {s['pipeline']} {ver}  {s['status']}  "
                     f"{s['outdir']}")
        if s.get("handoff") and i and _valid_entry(stages[i - 1]):
            prev = stages[i - 1]
            lines.append(f"      input ← {prev['index']:02d}-{prev['id']}  ({s['handoff']})")
    lines += ["", "lineage: verified" if not problems else "lineage: BROKEN"]
    lines += [f"  - {p}" for p in problems]
    return "\n".join(lines) + "\n"
