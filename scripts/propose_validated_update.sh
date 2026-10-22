#!/usr/bin/env bash
# Only call after create-pull-request failed in a maintenance workflow whose gates all passed.
# That action pushes the validated branch before it opens the pull request, and an organization
# can forbid GitHub Actions from opening pull requests at all. Confirm the pushed branch is this
# run's validated commit, then try once more to open the pull request: when that works the job
# merges it as usual; when the policy refuses it, report the branch for a maintainer to propose
# rather than failing the job. Any other failure still fails it.
set -euo pipefail

: "${BRANCH:?}" "${TITLE:?}" "${BODY:?}" "${GITHUB_REPOSITORY:?}" "${GITHUB_SHA:?}"
: "${GITHUB_SERVER_URL:?}" "${GITHUB_OUTPUT:?}" "${GITHUB_STEP_SUMMARY:?}" "${RUNNER_TEMP:?}"
if ! [[ "$BRANCH" =~ ^[A-Za-z0-9._-]+$ && "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "::error::Invalid maintenance branch identity"
  exit 1
fi

# create-pull-request leaves its local branch at the commit it pushed, or at the remote tip it found
# already holding this run's content. That commit sits directly on the one this job validated.
local_head=$(git rev-parse --verify -q "refs/heads/$BRANCH^{commit}" || true)
tip=$(gh api "repos/$GITHUB_REPOSITORY/commits/$BRANCH" \
  --jq '[.sha, .parents[0].sha, (.parents | length)] | @tsv')
IFS=$'\t' read -r head parent parents <<< "$tip"
if [[ ! "$head" =~ ^[0-9a-f]{40}$ || "$head" != "$local_head" || "$parent" != "$GITHUB_SHA" \
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

compare="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/compare/main...$BRANCH?expand=1"
echo "::warning title=Validated update awaits a pull request::GitHub Actions may not open pull" \
  "requests in this organization. $BRANCH (${head:0:12}) passed every gate of this run; open a" \
  "pull request from it: $compare"
{
  echo "### Validated update awaits a pull request"
  echo
  echo "This organization does not let GitHub Actions open pull requests, so the update was pushed"
  echo "to \`$BRANCH\` (\`$head\`) after passing every gate of this run, but not proposed."
  echo "Open a pull request from it: <$compare>. Its CI runs as for any pull request."
} >> "$GITHUB_STEP_SUMMARY"
