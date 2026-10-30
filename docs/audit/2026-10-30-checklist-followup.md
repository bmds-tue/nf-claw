# Pasted audit checklist follow-up, 2026-10-30

A third-party checklist (items 1.1–3.10) was written against a local checkout at `58e8e15`, 31
commits behind GitHub `main`. It was checked here against `main` at `4d09382`, which includes the
[2026-10-28 audit](2026-10-28-repository-audit.md) (#218, A01–A27), the
[2026-10-29 deep audit](2026-10-29-deep-audit.md) (#219, B01–B16) and the
[2026-10-30 exhaustive audit](2026-10-30-exhaustive-audit.md) (#227). Each item was checked in the
code on `main`, not taken from the checklist's own "fixed by merging" note. Three were still real
and are fixed here. One more was partly real and is fixed in the parallel runner follow-up branch
(`claude/runner-followups-2026-10-30`).

## Checklist

| Item | Finding | Disposition on `main` |
|---|---|---|
| 1.1 | Handoffs dropped single-end samples (bamtofastq → rnaseq, detaxizer → mag) | Already fixed (`3367a5f`, #218): `exhaustive` and `refuse_rows_in` refuse such a run. |
| 1.2 | Container watcher left a zombie; `_terminate` sent SIGKILL to a group number it had already reaped | Watcher already fixed (`3367a5f`). `_terminate`'s final SIGKILL still runs unconditionally after the leader is reaped. Once the group is gone, POSIX no longer reserves that number, so the call could hit a reused group; the chance is negligible. The runner follow-up branch guards it and `replay_guard._stop_replay_group`: they only signal while the leader is unreaped or the group is alive. |
| 1.3 | `_tree_digest` followed symlink cycles and skipped unreadable directories | Already fixed (`3367a5f`): ancestor tracking raises `ELOOP`, `onerror` raises. |
| 1.4 | Job supervisor died before recording an exit code | Already fixed (`0323b1f`): any exception becomes `status_error`; `exit_code` and `finished_at` are always written. |
| 1.5 | Local checkout behind `origin/main` | Operational, not a code defect: the local `main` is fast-forwarded. |
| 2.1 | Scripts call a bare `python3` | **Real; fixed here.** Where `python3` is older than 3.11 (macOS ships 3.9), every preview failed with an `ImportError` that the gate reported as a rejected pipeline. 26 tests in `test_maintenance_publish.py` and `test_nextflow_accept.py` failed on such a host. Both scripts now use `$PYTHON` (default `python3`, as the Makefile does) and refuse an older interpreter with a message that names it. |
| 2.2 | The gate needs GNU `timeout` | **Real; fixed here.** On `main`, `gtimeout` was already accepted, but a host with neither (macOS without coreutils) refused every preview. The gate now falls back to `scripts/run_with_timeout.py`, which has GNU timeout's contract: its own process group, SIGTERM at the deadline, SIGKILL after the grace period, forwarded INT/TERM/HUP, and statuses 124/137/125/126/127. GNU `timeout`/`gtimeout` are still used where present. The test shims the checklist asked for already existed (B14). |
| 2.3 | Deeply nested MCP message ended the session | Already fixed (`6576243`, #219): `RecursionError` gives `-32700`; any handler exception gives `-32603`. |
| 2.4 | Chain resume moved handoff paths, invalidating the cache | Already fixed (`6576243`): `_unchanged_handoff` keeps the previous paths. |
| 2.5 | Snapshot check read whole files into memory and included engine state | Already fixed (`3367a5f`): 1 MiB chunks, streamed gzip, `.nextflow*` excluded. |
| 2.6 | `nfclaw status` crashed on an unreadable log | Already fixed (`3367a5f`): state `unreadable`, `status: unknown`, exit 1. |
| 2.7 | Checkouts persisted the workflow token | Already fixed (#219, B06), and enforced by `test_workflows.py`. Every `actions/checkout` step sets `persist-credentials: false`. |
| 2.8 | No security policy | Already fixed (`3367a5f`): `SECURITY.md`. |
| 2.9 | No Dependabot configuration | Already fixed (`6576243`): Actions and npm, weekly, 7-day cooldown. |
| 3.1 | `parameters.merge` silently ignored a missing params file path | **Real; fixed here.** `nfclaw run` loads the file itself and was not affected; a direct caller with a mistyped path ran on defaults. Any given path is now loaded, and an unreadable one is `PARAMS_INVALID`. |
| 3.2 | Generated docs lost backslashes, asterisks and brackets | Already fixed (`6576243`): `_code` fences them. |
| 3.3 | Relative links in generated reference pages were dead | Already fixed (`6576243`): `_source_links` pins them to the commit. |
| 3.4 | Non-UTF-8 previous samplesheet crashed `--resume` | Already fixed (`6576243`): `errors="replace"`. |
| 3.5 | No `--version`, no nfclaw identity in manifests | Already fixed (`3367a5f`): `runner/version.py`, `nfclaw --version`, `run_manifest.json`. |
| 3.6 | No keyword search in `nfclaw list` | Already fixed (`3367a5f`): `discovery.search`, ranked by matched words. |
| 3.7 | Website accessibility violations | Already fixed (#219): labels, heading order, reduced motion, axe checks of every page. |
| 3.8 | Search shortcut state race | Already fixed: the shortcut listener is registered once and reads the open state from a ref. |
| 3.9 | Copy button failed silently | Already fixed: falls back to a hidden selection and shows the failure. |
| 3.10 | `bamtofastq → rnaseq` demo recipe missed `skip_pseudo_alignment` | Already fixed (`6576243`): `known-issues.md` and `validation.md` include it. |

## Evidence

- Before: on macOS (python3 3.9.6, no `timeout`/`gtimeout`), `pytest tests/test_maintenance_publish.py
  tests/test_nextflow_accept.py` on `main` failed 26 tests with
  `ImportError: cannot import name 'UTC' from 'datetime'`.
- After, same host: those files plus `test_parameters.py` and the new `test_run_with_timeout.py`,
  153 tests, all pass.
- The real gate on that Mac, `PYTHON=<3.13 venv> scripts/nextflow_accept.sh demo`, ran
  Nextflow 25.10.4 under the bundled supervisor: `demo	accepted`.
- A real `nextflow run … -preview` under `run_with_timeout.py --kill-after 10 4` received SIGTERM
  at 4 s and SIGKILL at 14 s (exit 137, as GNU timeout reports it). No process from the run was
  left afterwards.
