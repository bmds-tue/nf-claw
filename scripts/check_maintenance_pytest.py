#!/usr/bin/env python3
"""Reject incomplete full-suite evidence and undeclared coverage skips."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def allowed_skip(module: str, name: str, reason: str, os_name: str, python: str) -> bool:
    if (module == 'tests.test_bactmap_corrections'
            and reason == 'bactmap is no longer pinned at the audited commit 834642d8ac15'):
        return True
    if module in {'tests.test_legacy_sheet_paths', 'tests.test_path_roles'} and re.fullmatch(
            r'[a-z0-9_-]+ is no longer pinned at the audited commit [0-9a-f]{12}', reason):
        return True
    if module == 'tests.test_demo_defaults' and re.fullmatch(
            r'requires the audited (bamtofastq(?: 2\.2\.1)?|tumourevo(?: 1\.0\.0)?) source',
            reason):
        return True
    if module == 'tests.test_demo_hgtseq' and reason == 'requires the audited hgtseq 1.1.0 source':
        return True
    if (module == 'tests.test_demo_fastqrepair'
            and reason == 'requires the audited fastqrepair 1.1.1 source'):
        return True
    if os_name == 'macos-latest' and module == 'tests.test_execution':
        if (name == 'test_teardown_kills_a_task_that_outlives_sigterm'
                and reason == 'reads process state from /proc'):
            return True
        if (name == 'test_nextflow_does_not_outlive_an_nfclaw_killed_with_sigkill'
                and reason == 'PR_SET_PDEATHSIG is Linux-only'):
            return True
    return (os_name == 'macos-latest' and python == '3.15'
            and module == 'tests.test_scientific_h5ad'
            and reason == "could not import 'h5py': No module named 'h5py'")


def check_report(path: Path, os_name: str, python: str) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('Missing, redirected or oversized pytest report')
    root = ET.parse(path).getroot()
    if root.tag != 'testsuites' or root.findall('.//error') or root.findall('.//failure'):
        raise ValueError('The pytest report is malformed or unsuccessful')
    cases = root.findall('.//testcase')
    seen, skipped, passed = set(), [], 0
    for case in cases:
        module, name = case.get('classname', ''), case.get('name', '')
        identity = (module, name)
        if identity in seen:
            raise ValueError('Duplicate pytest case identity')
        seen.add(identity)
        omissions = case.findall('skipped')
        if omissions:
            reason = omissions[0].get('message', '')
            if len(omissions) != 1 or not allowed_skip(module, name, reason, os_name, python):
                raise ValueError(f'Undeclared skipped coverage: {module}.{name}: {reason}')
            skipped.append({'module': module, 'name': name, 'reason': reason})
        else:
            passed += 1
    # The repository already has over 3,000 cases. This rejects partial/empty reports;
    # the trusted workflow's unfiltered pytest command establishes collection scope.
    if passed < 3000:
        raise ValueError('The full-suite report contains fewer than 3000 executed cases')
    return {'passed': passed, 'skipped': skipped,
            'report_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--os', choices=['ubuntu-latest', 'macos-latest'], required=True)
    parser.add_argument('--python', choices=['3.11', '3.12', '3.13', '3.14', '3.15'], required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        expected_python = tuple(map(int, args.python.split('.')))
        expected_system = {'ubuntu-latest': 'Linux', 'macos-latest': 'Darwin'}[args.os]
        if (actual != args.candidate or sys.version_info[:2] != expected_python
                or platform.system() != expected_system):
            raise ValueError('Pytest lane identity differs from its candidate/platform/Python')
        sources = subprocess.check_output(['git', 'submodule', 'status', '--recursive'], text=True)
        if not sources.strip() or any(line[0] != ' ' for line in sources.splitlines()):
            raise ValueError('Full-suite source trees are missing or at different pins')
        # Submodule status reports HEAD even when a tracked schema was deleted. A skipped
        # fixture must not turn a damaged candidate/source checkout into full-suite evidence.
        subprocess.run(['git', 'diff', '--quiet', '--ignore-submodules=none', 'HEAD'], check=True)
        value = {'version': 1, 'candidate': args.candidate, 'os': args.os, 'python': args.python,
                 **check_report(args.report, args.os, args.python)}
        args.output.write_text(json.dumps(value, indent=2) + '\n')
    except (OSError, ValueError, ET.ParseError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Full-matrix evidence refused: {exc}\n')


if __name__ == '__main__':
    main()
