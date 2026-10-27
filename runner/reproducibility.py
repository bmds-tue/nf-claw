"""Advisories for pinned tools whose results vary between executions of identical input.

nfclaw records and replays a run exactly, but a replay can only reproduce what the tools reproduce.
Two steps of the library are measured not to (docs/known-issues.md, ampliseq 3.0.0): dada2's
`assignTaxonomy` breaks ties between equally scoring genera with a generator seeded from
`std::random_device`, which no R seed controls, and QIIME2's `core-metrics` rarefies without a seed.
They are detected in the pinned task scripts, not by pipeline name, and announced before launch so
an agent comparing runs or replays knows which differences to expect. A step the run explicitly
skips is not announced. Advisory only: the pinned tree is never changed.

A pinned workflow that reorders, in place, a list Nextflow hands to several processes at once is
announced the same way: it can fail a task with a ConcurrentModificationException, and the
processes that do run can receive that list in either order.
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

# createtaxdb 3.1.0's sourmash subworkflow sorts the genome list it receives with Groovy's in-place
# `sort()`. That list comes from `groupTuple` and is the same object every other database builder
# receives, so Nextflow can be iterating it for one of them while it is reordered
# (nf-core/createtaxdb#138; fixed on dev by switching to `groupBy`, nf-core/createtaxdb#202).
_SOURMASH_SUBWORKFLOW = Path("subworkflows/local/sourmash_create/main.nf")
_IN_PLACE_GENOME_SORT = re.compile(r"\{\s*\w+\s*,\s*genomes\s*->\s*genomes\s*\.sort\(\)")
_GROUPED_GENOMES = Path("subworkflows/local/preprocessing/main.nf")
_SOURMASH_SWITCHES = ("build_sourmash_dna", "build_sourmash_protein")


def _task_scripts(upstream: Path):
    modules = upstream / "modules"
    if modules.is_dir():
        for path in sorted(modules.rglob("main.nf")):
            try:
                yield path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _sourmash_runs(upstream: Path, params: Mapping[str, Any], demo: bool) -> bool:
    """Whether a sourmash database is built: an explicit switch, else the `--demo`
    test profile's."""
    test_profile = _read(upstream / "conf" / "test.config") if demo else ""
    return any(params.get(name) is True
               or (params.get(name) is None
                   and re.search(rf"\b{name}\s*=\s*true\b", test_profile) is not None)
               for name in _SOURMASH_SWITCHES)


def advisories(upstream: Path, params: Mapping[str, Any], demo: bool = False, *,
               source_overrides: Mapping[str, bytes] | None = None) -> list[str]:
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
    sourmash_source = ((source_overrides or {}).get(_SOURMASH_SUBWORKFLOW.as_posix()))
    sourmash_text = (sourmash_source.decode() if sourmash_source is not None else
                     _read(upstream / _SOURMASH_SUBWORKFLOW))
    if (_IN_PLACE_GENOME_SORT.search(sourmash_text)
            and ".groupTuple(" in _read(upstream / _GROUPED_GENOMES)
            and _sourmash_runs(upstream, params, demo)):
        notes.append(
            "This release's sourmash step sorts, in place, the genome list its other database "
            "builders receive at the same time: Nextflow can fail one of their tasks with "
            "java.util.ConcurrentModificationException (nf-core/createtaxdb#138), and builders "
            "that do run can receive the genomes in either order. Add `--build-sourmash-dna false "
            "--build-sourmash-protein false` to avoid it (no sourmash databases are then built), "
            "or re-run with --resume after such a failure. See docs/known-issues.md (createtaxdb).")
    return notes
