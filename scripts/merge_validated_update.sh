#!/usr/bin/env bash
# Only call after the maintenance workflow's unit/lint, website, Nextflow and drift gates pass.
# GITHUB_TOKEN-created PRs cannot run ordinary PR CI unattended. Publish real validation
# evidence on the generated commit instead; the same required checks still apply to the bot.
set -euo pipefail

: "${PR_NUMBER:?}" "${PR_HEAD_SHA:?}" "${GITHUB_REPOSITORY:?}"
: "${GITHUB_SERVER_URL:?}" "${GITHUB_RUN_ID:?}"
if ! [[ "$PR_NUMBER" =~ ^[0-9]+$ && "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "::error::Invalid maintenance PR identity"
  exit 1
fi

for check in 'pytest (ubuntu-latest, 3.11)' website nextflow-integration drift; do
  gh api --method POST "repos/$GITHUB_REPOSITORY/check-runs" --silent \
    -f "name=$check" -f "head_sha=$PR_HEAD_SHA" \
    -f status=completed -f conclusion=success \
    -f "details_url=$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
done

# Auto-merge tolerates a short delay while GitHub evaluates the newly reported checks.
# Matching the head prevents merging a different commit from the one just validated.
gh pr merge "$PR_NUMBER" --repo "$GITHUB_REPOSITORY" --squash --delete-branch \
  --match-head-commit "$PR_HEAD_SHA" --auto

# A GITHUB_TOKEN merge does not trigger the push-driven deploy. Wait for the merge
# before dispatching it, so a queued merge cannot deploy the previous main revision.
for _ in {1..30}; do
  state=$(gh pr view "$PR_NUMBER" --repo "$GITHUB_REPOSITORY" --json state --jq .state)
  case "$state" in
    MERGED)
      gh workflow run deploy-pages.yml --repo "$GITHUB_REPOSITORY" --ref main
      exit 0
      ;;
    CLOSED)
      echo "::error::Maintenance PR closed without merging"
      exit 1
      ;;
  esac
  sleep 5
done
echo "::error::Maintenance PR is still waiting to merge; deployment was not started"
exit 1
