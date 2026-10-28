#!/usr/bin/env python3
"""Prepare managed release corrections for the internal, externally timed preview gate."""
from __future__ import annotations

import argparse
import os
import shlex
import sys
import tempfile
from pathlib import Path

# Also works when the shell gate runs from a separate candidate checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner import demo_defaults, execution, orchestration, source_corrections, submodule


def prepare(args):
    env = {**os.environ, 'NXF_VER': args.version}
    suffix = ['-c', str(args.config), '--outdir', str(args.outdir), '-preview']
    if not (source_corrections.recipe_identity(args.name, args.commit) or
            demo_defaults.parameters(args.name, args.commit)):
        return (['nextflow', '-log', str(args.engine_log), 'run', str(args.upstream),
                 '-profile', 'test,docker', '-c', str(args.config), '--outdir', str(args.outdir),
                 '-work-dir', str(args.work), '-preview'], env, None)

    st = submodule.resolve(args.name, args.repo_root / 'pipelines')
    if st.commit != args.commit or st.path.resolve() != args.upstream.resolve():
        raise ValueError('Managed preview source differs from the verified release commit/path.')
    args.scratch.mkdir(parents=True, exist_ok=True)
    previous_temp = tempfile.tempdir
    try:
        # --check normally retains its runnable staging directory. The gate owns this entire
        # scratch root and removes it only after the timed child and its probes have stopped.
        tempfile.tempdir = str(args.scratch)
        result = orchestration.run_pipeline(
            args.name, repo_root=args.repo_root, resolved_tree=st, input_path=None,
            outdir=args.outdir, profile='docker', params_file=None, cli_overrides={},
            resume=False, demo=True, check_only=True, write_provenance=False,
            timeout_seconds=None, nxf_ver=args.version, nxf_env={'NXF_WORK': str(args.work)})
    finally:
        tempfile.tempdir = previous_temp
    command = shlex.split(result.command)
    if command[:2] != ['nextflow', 'run']:
        raise ValueError('Managed preview preparation returned an unexpected engine command.')
    args.outdir.mkdir(parents=True, exist_ok=True)
    return ([command[0], '-log', str(args.engine_log), *command[1:], *suffix],
            {**env, **result.env}, args.outdir)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('name', 'commit', 'version'):
        parser.add_argument('--' + flag, required=True)
    for flag in ('repo-root', 'upstream', 'config', 'outdir', 'work', 'engine-log', 'scratch'):
        parser.add_argument('--' + flag, required=True, type=lambda value: Path(value).resolve())
    args = parser.parse_args(argv)
    # Metadata probes have their own sessions. Unwind their bounded capture on timeout before
    # the shell cleans scratch, then restore ordinary handlers before exec replaces this process.
    with execution.stop_on_signals():
        command, env, cwd = prepare(args)
    if cwd is not None:
        os.chdir(cwd)
    os.execvpe(command[0], command, env)


if __name__ == '__main__':
    main()
