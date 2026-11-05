#!/usr/bin/env python3
"""Copy the JVM crash reports a failed test run left behind into a directory CI uploads.

    keep_jvm_crash_reports.py DEST

A JVM that dies on a fatal signal writes `hs_err_pid<pid>.log` (the crashing thread, its native
frames, the loaded libraries) into its working directory, plus `replay_pid<pid>.log` when a JIT
compiler thread crashed. In the test suite that is a Nextflow launch directory inside pytest's
temporary tree (`<tmp>/pytest-of-<user>/`), which is gone with the CI runner, so a crash such as a
SIGSEGV in `ld-linux-x86-64.so.2` left nothing to read. When the working directory is not
writable, the JVM writes into the temporary directory itself, so reports lying there directly are
kept too (on an ephemeral runner only this job's JVMs can have left them). Each report is copied to
DEST under its path below the temporary directory, so reports from different tests never collide.
Symlinks (pytest's `pytest-current`) are not followed, so each report is kept once; core files are
never copied. Prints one line per report; finding none is not an error.
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import tempfile
from pathlib import Path

REPORTS = ('hs_err_pid*.log', 'replay_pid*.log')


def keep(dest: Path, tmp: Path) -> list[Path]:
    """Copy every JVM crash report directly in `tmp` or under its pytest trees to `dest`; the
    copies, in order."""
    found = sorted(tmp.iterdir())
    for root in sorted(tmp.glob('pytest-of-*')):
        if root.is_symlink() or not root.is_dir():
            continue
        for directory, subdirectories, files in os.walk(root):
            subdirectories.sort()
            found += (Path(directory, name) for name in sorted(files))
    kept = []
    for report in found:
        if (not any(fnmatch.fnmatchcase(report.name, p) for p in REPORTS)
                or report.is_symlink() or not report.is_file()):
            continue
        target = dest / report.relative_to(tmp)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(report, target)
        kept.append(target)
    return kept


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('dest', type=Path)
    args = parser.parse_args()
    for target in keep(args.dest, Path(tempfile.gettempdir())):
        print(f'kept JVM crash report {target}')


if __name__ == '__main__':
    main()
