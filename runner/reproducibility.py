"""Advisories for pinned tools whose results vary between executions of identical input.

nfclaw records and replays a run exactly, but a replay can only reproduce what the tools reproduce.
Two steps of the library are measured not to (docs/known-issues.md, ampliseq 3.0.0): dada2's
`assignTaxonomy` breaks ties between equally scoring genera with a generator seeded from
`std::random_device`, which no R seed controls, and QIIME2's `core-metrics` rarefies without a seed.
They are detected in the pinned task scripts, not by pipeline name, and announced before launch so
an agent comparing runs or replays knows which differences to expect. A step the run explicitly
skips is not announced. Advisory only: the pinned tree is never changed.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_ASSIGN_TAXONOMY = re.compile(r"\bassignTaxonomy\s*\(")
_RAREFIED_CORE_METRICS = re.compile(r"qiime\s+diversity\s+core-metrics[\s\S]*?--p-sampling-depth")

_TAXONOMY_SKIPS = ("skip_taxonomy", "skip_dada_taxonomy")
_RAREFACTION_SKIPS = ("skip_qiime", "skip_qiime_downstream", "skip_diversity_indices")


def _task_scripts(upstream: Path):
    modules = upstream / "modules"
    if modules.is_dir():
        for path in sorted(modules.rglob("main.nf")):
            try:
                yield path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue


def advisories(upstream: Path, params: Mapping[str, Any]) -> list[str]:
    """The run-to-run variability this pinned tree's task scripts are known to carry."""
    texts = list(_task_scripts(upstream))
    notes: list[str] = []
    if (any(_ASSIGN_TAXONOMY.search(text) for text in texts)
            and not any(params.get(name) is True for name in _TAXONOMY_SKIPS)):
        notes.append(
            "This release can run dada2 assignTaxonomy, which breaks ties between equally scoring "
            "reference genera with a generator seeded from std::random_device that no seed "
            "controls: repeated runs and commands.sh replays of identical input can give ASVs with "
            "tied references different labels and bootstrap confidences. See docs/known-issues.md "
            "(ampliseq).")
    if (any(_RAREFIED_CORE_METRICS.search(text) for text in texts)
            and not any(params.get(name) is True for name in _RAREFACTION_SKIPS)):
        notes.append(
            "This release can rarefy with QIIME2 core-metrics without a seed: rarefied diversity "
            "results differ between executions of identical input, replays included. See "
            "docs/known-issues.md (ampliseq).")
    return notes
