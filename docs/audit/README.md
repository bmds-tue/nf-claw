# Audit records

Dated records of the repository's audits and remediations, each with what was checked, what it found,
what changed and what it did not establish. They describe the repository **on their own date** and
are not edited afterwards, so a command, count or limitation in them can be out of date: for current
behaviour, read the guides in [`docs/`](../../README.md#documentation-guides).

| Date | Record | What it covers |
|---|---|---|
| 2026-10-26 | [Reported findings](2026-10-26-reported-findings.md) | The tracked items of the first full audit, grouped by theme. |
| 2026-10-26 | [Remediation progress](2026-10-26-progress.md) | Item-by-item progress on those findings, with native run evidence. |
| 2026-10-28 | [Merge review](2026-10-28-merge-review.md) | Independent review of the remediation branch before it merged. |
| 2026-10-28 | [Repository audit](2026-10-28-repository-audit.md) | Findings A01–A27. |
| 2026-10-29 | [Deep audit](2026-10-29-deep-audit.md) | Findings B01–B16. |
| 2026-10-30 | [Exhaustive audit](2026-10-30-exhaustive-audit.md) | Findings C01–C09. |
| 2026-10-30 | [Cleanup audit](2026-10-30-cleanup-audit.md) | Findings D01–D10. |
| 2026-10-30 | [Checklist follow-up](2026-10-30-checklist-followup.md) | A third-party checklist, item by item, against current code. |
| 2026-10-30 | [Pasted review](2026-10-30-pasted-review.md) | Follow-up of a supplied review of a local working tree. |
| 2026-10-30 | [Boundary and evidence integrity](2026-10-30-boundary-integrity-audit.md) | Validation boundaries and the integrity of recorded evidence. |
| 2026-10-31 | [Full audit](2026-10-31-full-audit.md) | Findings E01–E29. |
| 2026-10-31 | [Follow-through audit](2026-10-31-followthrough-audit.md) | Verified findings in the current product, and their limits. |
| 2026-11-01 | [Report remediation](2026-11-01-report-remediation.md) | Remediation of the 31 October repository review. |
| 2026-11-05 | [Final audit](2026-11-05-final-audit.md) | Findings G01–G16, and a sweep of every pin with its replay. |

[`evidence/`](evidence/) holds the raw records these cite: run records, assessment scripts (stored
as `.py.txt` so they are read rather than run), logs and validation summaries. Pipeline documentation
links to some of them directly, such as the
[samplesheet generation inventory](evidence/samplesheet-generation-support.json).
