# Recorded workflow-source corrections

Three pinned releases need source changes that a process configuration cannot supply:

| Release and exact commit | Recorded correction | Effect |
| --- | --- | --- |
| Createtaxdb 3.1.0, `b01a0f8ed96a5990d15470828dfa92a22cf08bba` | `createtaxdb-sourmash-copy-sort-v1` | Sort a copy of each shared genome list before Sourmash batching. Other database builders keep their original list. |
| Funcscan 4.0.0, `aee3dc965eb0c77267435544dda30da858763913` | `funcscan-hmm-metadata-v1` | Preserve original sample metadata through HMM search, removing only the temporary model identifier before joining the result files with FAA/GBK/InterPro inputs. |
| Bactmap 1.0.0, `834642d8ac150ca10d705833223e7bcf15efc210` | `bactmap-demo-order-preview-v2` | Preserve the default module map and apply the original test overrides and explicit IQ-TREE/RAxML seeds as individual leaves. Align pseudogenomes in sample-name order. Skip the unbound MultiQC report wait only during preview; real execution retains the wait. |

`nfclaw run` applies only these exact-name, exact-commit recipes, after checking the original
target-file SHA-256. Multi-file recipes validate every target before copying, record every changed
file and bind all edits in one fingerprint. Earlier single-file fingerprints remain unchanged.
Each bounded replacement must occur exactly once. Other releases retain
their original behavior. No upstream checkout or pin is edited. The changed files, original and
corrected hashes, recipe fingerprint and complete working-source inventory are recorded.

Real runs use an independently copied source under
`${XDG_CACHE_HOME:-$HOME/.cache}/nfclaw/working-sources/`. Set `NFCLAW_SOURCE_CACHE` to choose
another writable location. The repository itself need not be writable. The runner never
overwrites an existing changed copy. Keep that copy for inspection and choose a fresh cache
location and output directory when necessary. Untracked or ignored files in an affected
original checkout are refused rather than silently omitted; preserve them outside that checkout.

Copies contain regular files with their executable bits preserved using modes 0644/0755 and
private directories (0700). Publication uses exclusive creation, a cooperating writer lock and
held directory descriptors. Checks reject added or removed files/directories, symlinks, changed
bytes and changed modes. Execution output, work, log and cache destinations are checked against
the original and actual working source before launch. These are launch/completion observations,
not a continuously read-only filesystem or a guarantee against edits restored between checks.

`--check` stages its runnable corrected source beside its other temporary command files and
leaves `--outdir` untouched. A real run keeps `provenance/working-source.json` as minimum resume
identity, including with `--no-provenance`. Resume requires the same recipe, complete inventory,
modes and recorded copy; missing or changed identity is refused. Changing a recipe changes the
affected chain stage fingerprint, preventing silent reuse of a previously frozen defective stage.
Unrelated chain fingerprints are unchanged.

With provenance enabled, `source-corrections.json` independently retains the launch identity,
and its hash is bound into `run_manifest.json`. `commit` names the upstream release;
`pipeline_path`, `pipeline.sha256` and `pipeline-source.tar.gz` describe the actual corrected
working source. `pipeline_git_head` is explicitly null because the copy is not a Git checkout.
Replay verifies both bytes and modes. If the recorded copy is unavailable or changed, replay
extracts and verifies the archived corrected source without requiring either original directory.
A source change during execution fails attribution; the failed bundle retains launch checksums
and records an archive error instead of claiming the changed source is valid.

Server regression controls cover planning, independent copies, failure cleanup, namespace races,
input/write separation, check-only staging, no-provenance resume, source changes, failed-bundle
retention, chain fingerprints and archive fallback. Native Sourmash-enabled and HMM-only/mixed
scientific runs are tracked separately in the [audit progress](audit/2026-10-26-progress.md);
unit or replay-guard tests alone do not establish scientific task coverage or database accuracy.

For Bactmap's bare bundled demo, nfclaw stages all three historical paired samples and the matched
NCTC13799 reference from test-datasets commit `02195cfa96ca496173e9d63dd58e34bf02fcf55a`.
Every read URL names that immutable commit. Explicit input/reference values (including null),
custom configs or extra profiles disable this fixture. The legacy release has no JSON input
schema: a contract limited to this paired fixture checks the exact Python samplesheet consumer
checksum, header, required values, read extensions and duplicate rows before staging. The real
task still runs the release's checker. This does not provide arbitrary legacy sheet generation.

The bare fixture also defaults to `max_cpus=1`. Two-CPU original/replay controls retained the same
complete trimmed read content but emitted different read orders and changed alignments, variant
coverage and pseudogenome masks. The single-CPU control preserved read order and pseudogenome
bytes. Explicit `--max-cpus` and params-file values remain authoritative; a resource ceiling
does not increase this default. This control does not establish phylogenetic accuracy or promise
identical branch lengths or bootstrap support. No output differences are ignored by verification.
At runtime commit `8db1cbb`, a fresh native original and replay each completed all 47 tasks;
the independent fixture assessment matched each sample's alignment content, variant records and
pseudogenome bases. The combined alignment and all four tree files were byte-identical in that
pair. Full output byte identity is not claimed. The [audit evidence](audit/2026-10-26-progress.md#u06-bactmap-matched-data-preview-and-replay)
also retains the earlier failed comparisons and their read-order controls.

The internal acceptance stager prepares the same managed source and demo, then appends its
preview-only reporting config. Ordinary releases retain direct previews. Preparation installs
signal cleanup for probes with separate process groups, restores handlers before replacing
itself with Nextflow, and keeps all staged files under the gate's private temporary directory.
