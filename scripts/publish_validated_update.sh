#!/usr/bin/env bash
# Called only after a maintenance job's complete unit, website, drift and Nextflow gates pass.
# The organization forbids Actions PRs, but main permits checked fast-forwards. Publish through
# that permitted path, with no personal token, PR creation, approval or ruleset bypass.
set -euo pipefail

: "${UPDATE_KIND:?}" "${BASE_SHA:?}" "${GITHUB_REPOSITORY:?}" "${GITHUB_RUN_ID:?}"
: "${GITHUB_SERVER_URL:?}" "${GITHUB_OUTPUT:?}" "${GITHUB_STEP_SUMMARY:?}" "${RUNNER_TEMP:?}"
attempt="${GITHUB_RUN_ATTEMPT:-1}"
if ! [[ "$BASE_SHA" =~ ^[0-9a-f]{40}$ && "$GITHUB_RUN_ID" =~ ^[0-9]+$ \
      && "$attempt" =~ ^[0-9]+$ ]] || [[ "$(git rev-parse HEAD)" != "$BASE_SHA" ]]; then
  echo "::error::Invalid or stale maintenance validation identity"
  exit 1
fi

paths=(pipelines catalog.json catalog.md .gitmodules)
case "$UPDATE_KIND" in
  update) title="chore: bump pipelines + regenerate context" ;;
  discover)
    title="feat: add discovered nf-core pipelines + generated context"
    paths+=(sources.tsv)
    ;;
  *) echo "::error::Unknown maintenance update kind"; exit 1 ;;
esac

# The validation gates ran against this working tree. A tracked change outside the generated
# paths would mean the published commit does not contain the code/configuration they checked.
exclude=()
for path in "${paths[@]}"; do exclude+=(":(exclude)$path"); done
if ! git diff --quiet "$BASE_SHA" -- . "${exclude[@]}"; then
  echo "::error::Unexpected tracked changes outside this maintenance job's generated paths"
  exit 1
fi

# A separate index includes exactly the generated paths, including new gitlinks and discovery's
# source registration. It preserves the checkout's staging and cannot sweep in stray build files.
scratch=$(mktemp -d "$RUNNER_TEMP/nfclaw-publish.XXXXXX")
trap 'rm -rf "$scratch"' EXIT
export GIT_INDEX_FILE="$scratch/index"
git read-tree "$BASE_SHA"
git add -- "${paths[@]}"
tree=$(git write-tree)
if [[ "$tree" == "$(git rev-parse "$BASE_SHA^{tree}")" ]]; then
  echo "No validated maintenance changes to publish."
  echo "published=false" >> "$GITHUB_OUTPUT"
  exit 0
fi
head=$(git -c user.name='github-actions[bot]' \
  -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
  commit-tree "$tree" -p "$BASE_SHA" -m "$title")
branch="maintenance-$UPDATE_KIND-$GITHUB_RUN_ID-$attempt"
# Authenticate only this push; no credential is stored in .git/config or sent to upstream code.
git -c credential.helper= -c 'credential.helper=!gh auth git-credential' \
  push origin "$head:refs/heads/$branch"

# Confirm the remote branch is still precisely the single commit validated by this job.
tip=$(gh api "repos/$GITHUB_REPOSITORY/commits/$branch" \
  --jq '[.sha, .parents[0].sha, (.parents | length)] | @tsv')
IFS=$'\t' read -r remote_head parent parents <<< "$tip"
if [[ "$remote_head" != "$head" || "$parent" != "$BASE_SHA" || "$parents" != 1 ]]; then
  echo "::error::The publication branch no longer holds this run's validated commit"
  exit 1
fi

for check in 'pytest (ubuntu-latest, 3.11)' website nextflow-integration drift; do
  gh api --method POST "repos/$GITHUB_REPOSITORY/check-runs" --silent \
    -f "name=$check" -f "head_sha=$head" -f status=completed -f conclusion=success \
    -f "details_url=$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
done

err="$scratch/fast-forward.err"
published=false
for _ in {1..5}; do
  if gh api --method PATCH "repos/$GITHUB_REPOSITORY/git/refs/heads/main" --silent \
      -f "sha=$head" -F force=false 2> "$err"; then
    published=true
    break
  fi
  if grep -qi 'fast forward' "$err"; then
    # A human changed main during validation. Preserve it; the next scheduled run regenerates
    # and validates on that new base. Never rebase or force-push an unchecked combination.
    echo "published=false" >> "$GITHUB_OUTPUT"
    echo "::notice::main moved during validation; the next maintenance run will revalidate the update"
    {
      echo "### Maintenance publication deferred"
      echo
      echo "main moved during validation. The next scheduled run will regenerate and validate"
      echo "against the new main. This run's candidate remains on \`$branch\` (\`$head\`)."
    } >> "$GITHUB_STEP_SUMMARY"
    exit 0
  fi
  sleep 5                                    # allow GitHub to evaluate the just-reported checks
done
if [[ "$published" != true ]]; then
  cat "$err" >&2
  echo "::error::GitHub refused the validated publication; main was not changed"
  exit 1
fi
echo "published=true" >> "$GITHUB_OUTPUT"
echo "head_sha=$head" >> "$GITHUB_OUTPUT"
gh api --method DELETE "repos/$GITHUB_REPOSITORY/git/refs/heads/$branch" --silent || true
{
  echo "### Validated maintenance update published"
  echo
  echo "main was fast-forwarded to \`$head\` after this run's validation gates passed."
  echo "Required checks were reported on that exact commit; no pull request or bypass was needed."
} >> "$GITHUB_STEP_SUMMARY"

# GITHUB_TOKEN pushes do not trigger push workflows. Start every post-publication workflow
# explicitly; attempt all four even if one dispatch fails, and expose any failure in the job.
dispatch_failed=0
for workflow in tests.yml smoke.yml codeql.yml deploy-pages.yml; do
  if ! gh workflow run "$workflow" --repo "$GITHUB_REPOSITORY" --ref main; then
    echo "::error::Could not dispatch $workflow after publication of $head"
    dispatch_failed=1
  fi
done
exit "$dispatch_failed"
