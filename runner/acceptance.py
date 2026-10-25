"""Versioned, opt-in acceptance of pipeline-reported completion conditions.

Classification organizes the existing evidence; it never establishes biological
completeness when an upstream workflow reports no caveat.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

from runner.errors import ErrorCode, NfclawError

CATEGORIES = ("stub_only", "ignored_task_failures", "skipped_samples", "incomplete_analysis",
              "unclassified")
POLICIES = (*CATEGORIES, "any")


def validate(reject: Sequence[str] | None) -> tuple[str, ...]:
    if reject is None:
        return ()
    if (not isinstance(reject, (list, tuple))
            or any(not isinstance(value, str) or value not in POLICIES for value in reject)):
        raise NfclawError(ErrorCode.PARAMS_INVALID,
                          "reject_caveats must list supported completion categories.",
                          fix="Use one or more of: " + ", ".join(POLICIES))
    return tuple(sorted(set(reject)))


def classify(text: str) -> tuple[str, ...]:
    lower = text.lower()
    found = []
    if "stub" in lower and ("placeholder" in lower or "every task" in lower):
        found.append("stub_only")
    if (re.search(r"ignored? \d+ failed task|errored process|errorstrategy ['\"]ignore", lower)):
        found.append("ignored_task_failures")
    if re.search(r"skipped sampl|sampl\S*.*(?:were|was|are|is) skipped", lower):
        found.append("skipped_samples")
    if re.search(r"failed.*(?:strandedness|qc|quality)|incomplete|missing sampl", lower):
        found.append("incomplete_analysis")
    return tuple(found or ["unclassified"])


def evaluate(caveats: list[str], *, reject: Sequence[str] | None = None) -> dict:
    policy = validate(reject)
    conditions = [{"category": category, "text": text}
                  for text in caveats for category in classify(text)]
    rejected = sorted({item["category"] for item in conditions
                       if "any" in policy or item["category"] in policy})
    return {"version": 1, "reject_caveats": list(policy), "conditions": conditions,
            "rejected_categories": rejected, "accepted": not rejected}


def require_accepted(record: dict) -> None:
    if not record["accepted"]:
        raise NfclawError(ErrorCode.ACCEPTANCE_REJECTED,
                          "Nextflow completed, but the results were rejected by acceptance policy.",
                          details={"rejected_categories": record["rejected_categories"]},
                          fix="Inspect the original completion caveats and retained results. "
                              "Resolve the incomplete analysis or explicitly select a "
                              "permissive policy if those conditions are acceptable.")
