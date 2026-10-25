# Accepting completed results

Nextflow can exit zero after running stubs, ignoring task failures or skipping
samples. nf-claw preserves the upstream completion text and records structured
conditions alongside it. The default remains permissive.

To refuse any reported condition:

```bash
nfclaw run rnaseq --demo --outdir /data/results --reject-caveat any
```

Alternatively repeat `--reject-caveat CATEGORY` to select conditions:

| Category | Evidence |
| --- | --- |
| `stub_only` | Selected profile/config runs every task's stub block |
| `ignored_task_failures` | Upstream errored-process summary or Nextflow ignored-task count |
| `skipped_samples` | Upstream summary explicitly reports skipped samples |
| `incomplete_analysis` | Reported missing samples, incomplete work or failed QC/strandedness |
| `unclassified` | Other upstream completion caveat; original text remains available |
| `any` | Reject every reported condition, including unclassified ones |

Classification cannot detect omissions a pipeline does not report, and absence
of caveats does not establish biological accuracy. Inspect task records and use
independent output checks appropriate to the analysis.

In a chain specification, set `"reject_caveats": ["any"]` at the top level or on
an individual stage. A stage replaces the inherited list; `[]` explicitly allows
all caveats for that stage. Rejected stages retain their results and provenance,
fail without automatic retries, and never feed downstream stages. A succeeded
stage's acceptance policy is frozen on resume along with its other settings.

MCP `run_pipeline` accepts the same `reject_caveats` list; `run_chain` uses the
same chain specification. The run manifest's `acceptance` object has `version: 1`,
the selected `reject_caveats`, `conditions` containing original `text` and category,
`rejected_categories`, and `accepted`. Rejection records `outcome: "rejected"`
and `nextflow_outcome: "success"`, gives the run log a rejected outcome, and returns
a nonzero CLI/job exit status. `completion_caveats` remains the original text.

Use a fresh directory for a different accepted analysis, or resume deliberately
with an appropriate policy. See [resume attribution](resume-policy.md).
