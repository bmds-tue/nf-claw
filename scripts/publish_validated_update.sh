#!/usr/bin/env bash
# Trusted-base publisher: upstream code runs only in isolated read-only jobs.
# Publish precisely the candidate that passed the full matrix, drift and native-task gates.
set -euo pipefail

: "${UPDATE_KIND:?}" "${BASE_SHA:?}" "${CANDIDATE_SHA:?}" "${CANDIDATE_DIR:?}"
: "${NATIVE_EVIDENCE_DIR:?}" "${MATRIX_EVIDENCE_DIR:?}"
: "${VALIDATION_RESULT:?}" "${DRIFT_RESULT:?}" "${NATIVE_RESULT:?}"
: "${GITHUB_REPOSITORY:?}" "${GITHUB_RUN_ID:?}" "${GITHUB_SERVER_URL:?}"
: "${GITHUB_OUTPUT:?}" "${GITHUB_STEP_SUMMARY:?}" "${RUNNER_TEMP:?}"
attempt="${GITHUB_RUN_ATTEMPT:-1}"
if ! [[ "$BASE_SHA" =~ ^[0-9a-f]{40}$ && "$GITHUB_RUN_ID" =~ ^[0-9]+$ \
      && "$attempt" =~ ^[0-9]+$ ]] || [[ "$(git rev-parse HEAD)" != "$BASE_SHA" ]]; then
  echo "::error::Invalid or stale maintenance validation identity"
  exit 1
fi
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
head=$(python3 "$script_dir/maintenance_candidate.py" authorize \
  --directory "$CANDIDATE_DIR" --base "$BASE_SHA" --sha "$CANDIDATE_SHA" --kind "$UPDATE_KIND" \
  --validation-result "$VALIDATION_RESULT" --drift-result "$DRIFT_RESULT" \
  --native-result "$NATIVE_RESULT" --native-evidence "$NATIVE_EVIDENCE_DIR" \
  --matrix-evidence "$MATRIX_EVIDENCE_DIR")
scratch=$(mktemp -d "$RUNNER_TEMP/nfclaw-publish.XXXXXX")
trap 'rm -rf "$scratch"' EXIT
branch="maintenance-$UPDATE_KIND-$GITHUB_RUN_ID-$attempt"
git -c credential.helper= -c 'credential.helper=!gh auth git-credential' \
  push origin "$head:refs/heads/$branch"
tip=$(gh api "repos/$GITHUB_REPOSITORY/commits/$branch" \
  --jq '[.sha, .parents[0].sha, (.parents | length)] | @tsv')
IFS=$'\t' read -r remote_head parent parents <<< "$tip"
if [[ "$remote_head" != "$head" || "$parent" != "$BASE_SHA" || "$parents" != 1 ]]; then
  echo "::error::The publication branch no longer holds this run's validated commit"
  exit 1
fi

dispatch_followups() {
  # Token-authenticated pushes do not trigger these workflows automatically.
  local dispatch_failed=0
  for workflow in tests.yml smoke.yml codeql.yml deploy-pages.yml; do
    if ! gh workflow run "$workflow" --repo "$GITHUB_REPOSITORY" --ref main; then
      echo "::error::Could not dispatch $workflow for validated candidate $head"
      dispatch_failed=1
    fi
  done
  return "$dispatch_failed"
}

defer_publication() {
  gh api --method DELETE "repos/$GITHUB_REPOSITORY/git/refs/heads/$branch" --silent || true
  echo "published=false" >> "$GITHUB_OUTPUT"
  current=$(gh api "repos/$GITHUB_REPOSITORY/git/ref/heads/main" --jq .object.sha)
  if [[ "$current" == "$head" ]]; then
    echo "followup_retried=true" >> "$GITHUB_OUTPUT"
    echo "::notice::The validated candidate is already on main; retrying required follow-up workflows"
    dispatch_followups
    return
  fi
  echo "::notice::main moved during validation; a new candidate must be validated on its new base"
  {
    echo "### Maintenance publication deferred"
    echo
    echo "main moved during validation. Candidate \`$head\` was not published by this job."
  } >> "$GITHUB_STEP_SUMMARY"
}
current=$(gh api "repos/$GITHUB_REPOSITORY/git/ref/heads/main" --jq .object.sha)
if [[ "$current" != "$BASE_SHA" ]]; then
  defer_publication
  exit 0
fi
checks=(website nextflow-integration drift)
for os_name in ubuntu-latest macos-latest; do
  for version in 3.11 3.12 3.13 3.14 3.15; do
    checks+=("pytest ($os_name, $version)")
  done
done
if [[ "$NATIVE_RESULT" == success ]]; then checks+=(pipeline-execution); fi
for check in "${checks[@]}"; do
  gh api --method POST "repos/$GITHUB_REPOSITORY/check-runs" --silent \
    -f "name=$check" -f "head_sha=$head" -f status=completed -f conclusion=success \
    -f "details_url=$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
done

err="$scratch/fast-forward.err"
published=false
for _ in {1..5}; do
  # Explicit old OID makes this atomic. The verified candidate has exactly this parent,
  # so an accepted update is necessarily a fast-forward from the validated base.
  if git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push \
      --porcelain --force-with-lease="refs/heads/main:$BASE_SHA" origin "$head:refs/heads/main" \
      > "$scratch/push.out" 2> "$err"; then
    # Git reports success without checking the lease when the remote already equals head.
    # Require an actual fast-forward update, not an '=' (up-to-date) observation.
    if ! awk -F '\t' '$1 == " " && $2 ~ /:refs\/heads\/main$/ { updated=1 } END { exit !updated }' \
        "$scratch/push.out"; then
      defer_publication
      exit 0
    fi
    published=true
    break
  fi
  current=$(gh api "repos/$GITHUB_REPOSITORY/git/ref/heads/main" --jq .object.sha)
  if [[ "$current" != "$BASE_SHA" ]]; then
    defer_publication
    exit 0
  fi
  sleep 5
done
if [[ "$published" != true ]]; then
  cat "$err" >&2
  echo "::error::GitHub refused the validated publication; main was not changed by this job"
  exit 1
fi
echo "published=true" >> "$GITHUB_OUTPUT"
echo "head_sha=$head" >> "$GITHUB_OUTPUT"
gh api --method DELETE "repos/$GITHUB_REPOSITORY/git/refs/heads/$branch" --silent || true
for ((previous = 1; previous < attempt; previous++)); do
  gh api --method DELETE --silent \
    "repos/$GITHUB_REPOSITORY/git/refs/heads/maintenance-$UPDATE_KIND-$GITHUB_RUN_ID-$previous" \
    2> /dev/null || true
done
{
  echo "### Validated maintenance update published"
  echo
  echo "main was fast-forwarded to \`$head\` after the full Python matrix, site, integration,"
  echo "drift and required real-task gates passed on that exact candidate."
} >> "$GITHUB_STEP_SUMMARY"

dispatch_followups
