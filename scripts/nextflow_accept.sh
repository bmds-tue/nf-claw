#!/usr/bin/env bash
# Verify that Nextflow ACCEPTS each pipeline without running the analysis.
#
# Usage: scripts/nextflow_accept.sh [pipeline ...]   (no args = every pipeline)
#
# For each pipeline this initialises the pinned submodule and runs
# `nextflow run <upstream> -profile test,docker -preview` with the Nextflow
# version the release declares (a release declaring an engine older than 22.10.0
# is checked on 24.10.5, a -preview-capable lenient-parser version). "Accepted" means Nextflow compiled the
# pipeline, resolved its config/profile and validated its parameters, and the
# preview exited successfully. Every nonzero exit fails this gate. A clearly
# identified remote-input staging failure is labelled "staging-unverified":
# it could not finish the preview, so it is never accepted for auto-merge.
#
# A failure caused by an unreachable remote file (staging, or nf-schema's existence check on a
# URL) is retried once: hosted test data is occasionally unreachable for a few seconds, and a
# second identical failure is reported as before.
#
# Documented upstream defects of an exact pinned commit are listed in
# scripts/nextflow_accept_exceptions.tsv (pipeline, commit, expected outcome, evidence pattern,
# reason). Such a preview is reported as "known-<outcome>" — never "accepted" — and does not fail
# the gate only while BOTH the outcome and the evidence pattern (an ERE searched in the console
# and the engine log) still match. A changed failure, a preview that now passes (a stale entry),
# or any other commit (every release bump) is judged as above. A documented `timeout` is given
# 300 seconds instead of 900, since its evidence is written within seconds of the launch.
#
# Env:
#   NFCLAW_RESULT_FILE      if set, write "<name>\t<verdict>" per line: accepted, staging-unverified,
#                           rejected, stale-exception, or known-(rejected|staging-unverified|timeout)
#   NFCLAW_KEEP_SUBMODULES  if "1", do not deinit submodules after checking
#   NFCLAW_LOG_DIR         if set, retain console and engine logs per pipeline
#   NFCLAW_ACCEPT_EXCEPTIONS  the exceptions file (default: beside this script)
#   NFCLAW_ACCEPT_RETRY_DELAY seconds to wait before retrying an unreachable remote file (30)
#
# Exits non-zero unless every pipeline completed its preview successfully or matched its
# documented exception exactly.
set -uo pipefail

_run_with_timeout() {
  seconds="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout --kill-after=10s "$seconds" "$@"
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout --kill-after=10s "$seconds" "$@"
  else
    echo "nfclaw acceptance: install GNU timeout (gtimeout on macOS); an unbounded preview is refused" >&2
    return 127
  fi
}

# A failure Nextflow attributes to a remote file it could not reach (an `ERROR ~` staging report,
# or nf-schema's "the file or directory '<url>' does not exist").
_remote_failure() {
  grep -qiE '^ERROR[[:space:]]*~[[:space:]]*(No such file or directory|Cannot access remote file|Unable to access (remote )?file):?[[:space:]]+(https?://|s3://|gs://)' "$1" \
    || grep -qiE "the file or directory '(https?|s3|gs)://[^']*' does not exist" "$1"
}

names=("$@")
if [ "${#names[@]}" -eq 0 ]; then
  # A failed inventory is a failed gate, even if it printed a partial list. Compatible with
  # macOS bash 3.2, which has no mapfile builtin.
  if ! inventory=$(nfclaw list); then
    echo "::error::could not list pipelines"
    exit 1
  fi
  while IFS=$'\t' read -r name _; do
    [ -z "$name" ] || names+=("$name")
  done <<< "$inventory"
  # An empty list would "accept" nothing and exit 0 — a vacuous green check.
  if [ "${#names[@]}" -eq 0 ]; then
    echo "::error::no pipelines found (nfclaw list returned nothing)"
    exit 1
  fi
fi

exceptions="${NFCLAW_ACCEPT_EXCEPTIONS:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/nextflow_accept_exceptions.tsv}"
tmp=$(mktemp -d "${RUNNER_TEMP:-/tmp}/nfclaw-accept.XXXXXXXX") || exit 1
trap 'rm -rf -- "$tmp"' EXIT
summary="${GITHUB_STEP_SUMMARY:-/dev/null}"
result="${NFCLAW_RESULT_FILE:-/dev/null}"
: > "$result" || exit 1
logs="${NFCLAW_LOG_DIR:-}"
if [ -n "$logs" ]; then
  mkdir -p -- "$logs" || exit 1
fi

cfg="$tmp/no-reports.config"
# -preview builds the DAG but produces no trace; disable the report/timeline/
# trace/dag outputs nf-core configs enable (rendering them with no data fails).
printf 'report.enabled=false\ntimeline.enabled=false\ntrace.enabled=false\ndag.enabled=false\n' > "$cfg"

{
  echo "## Nextflow acceptance ( -preview )"
  echo "| pipeline | nextflow | accepted |"
  echo "|---|---|---|"
} >> "$summary"

fail=0
for name in "${names[@]}"; do
  if [[ ! "$name" =~ ^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$ ]]; then
    echo "::error::Invalid pipeline name: $name"
    printf '%s\trejected\n' "$name" >> "$result"
    fail=1
    continue
  fi
  up="pipelines/$name/upstream"
  out="$tmp/prev-$name"
  work="$tmp/work-$name"
  if ! git submodule update --init --depth 1 "$up" >"$tmp/$name-submodule.out" 2>&1; then
    cat "$tmp/$name-submodule.out"
    if [ -n "$logs" ]; then
      cp -- "$tmp/$name-submodule.out" "$logs/$name-submodule.log" || exit 1
    fi
    echo "::error::Could not initialize $name submodule"
    echo "| \`$name\` | n/a | ❌ |" >> "$summary"
    printf '%s\trejected\n' "$name" >> "$result"
    fail=1
    continue
  fi
  ver=$(grep -hoE "nextflowVersion[[:space:]]*=[[:space:]]*'[^']+'" "$up/nextflow.config" 2>/dev/null \
        | grep -oE "[0-9]+\.[0-9]+\.[0-9]+" | head -1)
  ver="${ver:-25.10.4}"
  if [ "$(printf '%s\n22.10.0\n' "$ver" | sort -V | head -1)" = "$ver" ] && [ "$ver" != "22.10.0" ]; then
    ver="24.10.5"
  fi
  # The documented exception for exactly this commit, if any (blank and `#` lines are comments).
  commit=$(git -C "$up" rev-parse HEAD 2>/dev/null || true)
  expected=""
  evidence=""
  reason=""
  if [ -n "$commit" ] && [ -f "$exceptions" ]; then
    while IFS=$'\t' read -r e_name e_commit e_outcome e_evidence e_reason; do
      case "$e_name" in ''|'#'*) continue ;; esac
      if [ "$e_name" = "$name" ] && [ "$e_commit" = "$commit" ]; then
        expected="$e_outcome"
        evidence="$e_evidence"
        reason="$e_reason"
      fi
    done < "$exceptions"
  fi
  budget=900
  [ "$expected" = timeout ] && budget=300
  echo "::group::$name (nextflow $ver)"
  log="$tmp/$name.out"
  engine_log="$tmp/$name.nextflow.log"
  attempt=1
  while :; do
    rm -rf -- "$work" "$out" "$engine_log"
    NXF_VER="$ver" _run_with_timeout "$budget" nextflow -log "$engine_log" run "$up" -profile test,docker \
      -c "$cfg" --outdir "$out" -work-dir "$work" -preview > "$log" 2>&1 && rc=0 || rc=$?
    if [ "$rc" != 0 ] && [ "$attempt" = 1 ] && _remote_failure "$log"; then
      cat "$log"
      echo "::warning::$name: a remote file was unreachable (exit $rc); retrying the preview once"
      attempt=2
      sleep "${NFCLAW_ACCEPT_RETRY_DELAY:-30}"
      continue
    fi
    break
  done
  if [ -n "$logs" ]; then
    cp -- "$log" "$logs/$name.console.log" || exit 1
    if [ -f "$engine_log" ]; then
      cp -- "$engine_log" "$logs/$name.nextflow.log" || exit 1
    fi
  fi
  if [ "$rc" = 0 ]; then
    observed=accepted
  elif [ "$rc" = 124 ] || [ "$rc" = 137 ]; then
    observed=timeout
  elif [ "$rc" = 1 ] && _remote_failure "$log"; then
    observed=staging-unverified
  else
    observed=rejected
  fi
  if [ -n "$expected" ] && [ "$observed" = accepted ]; then
    tail -6 "$log"
    echo "::error::$name now passes its preview: remove its stale entry from $exceptions"
    echo "| \`$name\` | $ver | ❌ stale exception |" >> "$summary"
    printf '%s\tstale-exception\n' "$name" >> "$result"
    fail=1
  elif [ -n "$expected" ] && [ -n "$evidence" ] && [ "$observed" = "$expected" ] \
       && grep -sqE -- "$evidence" "$log" "$engine_log"; then
    tail -6 "$log"
    echo "::notice::$name known-$expected (documented upstream defect of commit ${commit:0:12}): $reason"
    echo "| \`$name\` | $ver | ⚠️ known-$expected (not accepted) |" >> "$summary"
    printf '%s\tknown-%s\n' "$name" "$expected" >> "$result"
  elif [ "$observed" = accepted ]; then
    tail -6 "$log"
    echo "| \`$name\` | $ver | ✅ |" >> "$summary"
    printf '%s\taccepted\n' "$name" >> "$result"
  elif [ "$observed" = staging-unverified ]; then
    cat "$log"
    echo "::warning::$name staging-unverified: remote test inputs prevented a completed preview (exit $rc)"
    echo "| \`$name\` | $ver | ⚠️ staging-unverified |" >> "$summary"
    printf '%s\tstaging-unverified\n' "$name" >> "$result"
    fail=1
  else
    cat "$log"
    if [ -n "$expected" ] && [ "$observed" = "$expected" ]; then
      echo "::error::$name failed ($observed) without its documented evidence: $evidence"
    elif [ -n "$expected" ]; then
      echo "::error::$name no longer fails as documented ($expected): observed $observed (exit $rc)"
    fi
    echo "::error::Nextflow did not accept $name (exit $rc)"
    echo "| \`$name\` | $ver | ❌ |" >> "$summary"
    printf '%s\trejected\n' "$name" >> "$result"
    fail=1
  fi
  echo "::endgroup::"
  if [ "${NFCLAW_KEEP_SUBMODULES:-}" != "1" ]; then
    git submodule deinit -f "$up" >/dev/null 2>&1 || true
  fi
  rm -rf "$work" "$out"
done

{
  echo ""
  echo "Only exit-zero previews are accepted. Staging-unverified previews fail the gate and cannot be auto-merged."
  echo "Known-* rows are documented upstream defects of that exact commit (scripts/nextflow_accept_exceptions.tsv); they are not accepted."
} >> "$summary"
exit $fail
