#!/usr/bin/env bash
# Only call after create-pull-request failed in a maintenance workflow whose gates all passed.
# That action pushes the validated branch before it opens the pull request, and an organization
# can forbid GitHub Actions from opening pull requests at all. Confirm the pushed branch is this
# run's validated commit, then try once more to open the pull request: when that works the job
# merges it as usual. When the policy refuses it, publish the commit as the merge would have:
# report the completed checks on it and fast-forward main, whose ruleset requires those checks but
# no pull request. If main has moved on or refuses the update, report the branch for a maintainer
# to propose rather than failing the job. Any other failure still fails it.
set -euo pipefail

: "${BRANCH:?}" "${TITLE:?}" "${BODY:?}" "${GITHUB_REPOSITORY:?}" "${GITHUB_SHA:?}"
: "${GITHUB_SERVER_URL:?}" "${GITHUB_RUN_ID:?}" "${GITHUB_OUTPUT:?}" "${GITHUB_STEP_SUMMARY:?}"
: "${RUNNER_TEMP:?}"
# The commit the job checked out and validated (main when it started, not when it was scheduled).
base="${BASE_SHA:-$GITHUB_SHA}"
if ! [[ "$BRANCH" =~ ^[A-Za-z0-9._-]+$ && "$base" =~ ^[0-9a-f]{40}$ ]]; then
  echo "::error::Invalid maintenance branch identity"
  exit 1
fi

# create-pull-request leaves its local branch at the commit it pushed, or at the remote tip it found
# already holding this run's content. That commit sits directly on the one this job validated.
local_head=$(git rev-parse --verify -q "refs/heads/$BRANCH^{commit}" || true)
tip=$(gh api "repos/$GITHUB_REPOSITORY/commits/$BRANCH" \
  --jq '[.sha, .parents[0].sha, (.parents | length)] | @tsv')
IFS=$'\t' read -r head parent parents <<< "$tip"
if [[ ! "$head" =~ ^[0-9a-f]{40}$ || "$head" != "$local_head" || "$parent" != "$base" \
      || "$parents" != 1 ]]; then
  echo "::error::$BRANCH does not hold this run's validated update; nothing was proposed"
  exit 1
fi

err="$RUNNER_TEMP/propose-update.err"
if url=$(gh pr create --repo "$GITHUB_REPOSITORY" --base main --head "$BRANCH" \
    --title "$TITLE" --body "$BODY" 2> "$err"); then
  echo "number=${url##*/}" >> "$GITHUB_OUTPUT"
  echo "head_sha=$head" >> "$GITHUB_OUTPUT"
  exit 0
fi
cat "$err" >&2
if ! grep -q "not permitted to create or approve pull requests" "$err"; then
  echo "::error::Could not open a pull request from $BRANCH"
  exit 1
fi

# The same check results the merge script reports, on the commit that passed them.
for check in 'pytest (ubuntu-latest, 3.11)' website nextflow-integration drift; do
  gh api --method POST "repos/$GITHUB_REPOSITORY/check-runs" --silent \
    -f "name=$check" -f "head_sha=$head" \
    -f status=completed -f conclusion=success \
    -f "details_url=$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
done

# Never forced: main only advances if it is still the commit this run validated. Allow a short
# delay for GitHub to evaluate the checks just reported.
ffwd="$RUNNER_TEMP/fast-forward.err"
for _ in {1..5}; do
  if gh api --method PATCH "repos/$GITHUB_REPOSITORY/git/refs/heads/main" --silent \
      -f "sha=$head" -F force=false 2> "$ffwd"; then
    gh api --method DELETE "repos/$GITHUB_REPOSITORY/git/refs/heads/$BRANCH" --silent || true
    # A GITHUB_TOKEN push triggers no workflow: deploy the site and run the test suite explicitly.
    gh workflow run deploy-pages.yml --repo "$GITHUB_REPOSITORY" --ref main
    gh workflow run tests.yml --repo "$GITHUB_REPOSITORY" --ref main
    echo "::notice title=Validated update published::GitHub Actions may not open pull requests in" \
      "this organization, so main was fast-forwarded to ${head:0:12} after it passed every gate"
    {
      echo "### Validated update published to main"
      echo
      echo "This organization does not let GitHub Actions open pull requests. \`$head\` passed every"
      echo "gate of this run, its check results were reported on it, and main was fast-forwarded to it."
    } >> "$GITHUB_STEP_SUMMARY"
    exit 0
  fi
  grep -qi "fast forward" "$ffwd" && break                # main moved on: a retry cannot help
  sleep 5
done
cat "$ffwd" >&2

compare="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/compare/main...$BRANCH?expand=1"
echo "::warning title=Validated update awaits a pull request::GitHub Actions may not open pull" \
  "requests in this organization, and main could not be fast-forwarded. $BRANCH (${head:0:12})" \
  "passed every gate of this run; open a pull request from it: $compare"
{
  echo "### Validated update awaits a pull request"
  echo
  echo "This organization does not let GitHub Actions open pull requests, and main could not be"
  echo "fast-forwarded to \`$head\` (it has moved on, or its rules refused the update). The update"
  echo "passed every gate of this run and is on \`$BRANCH\`."
  echo "Open a pull request from it: <$compare>. Its CI runs as for any pull request."
} >> "$GITHUB_STEP_SUMMARY"
