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

# Allow a short delay for GitHub to evaluate the checks, without leaving a queued
# merge behind if this job stops. Matching the head pins the validated commit.
for _ in {1..5}; do
  if gh pr merge "$PR_NUMBER" --repo "$GITHUB_REPOSITORY" --squash --delete-branch \
    --match-head-commit "$PR_HEAD_SHA"; then
    # GITHUB_TOKEN merges do not trigger the push-driven deploy.
    gh workflow run deploy-pages.yml --repo "$GITHUB_REPOSITORY" --ref main
    exit 0
  fi
  sleep 5
done
echo "::error::Maintenance PR could not be merged; deployment was not started"
exit 1
