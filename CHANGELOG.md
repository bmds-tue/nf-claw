# Changelog

## Unreleased

- Preserve prior runs and isolate current publications when the effective analysis changes.
- Bind live container observations to actual container IDs and immutable image IDs.
- Add opt-in rejection of stubbed and reported incomplete results to CLI, chains and MCP.
- Support an explicitly configured pipeline library for installed distributions.
- Add versioned JSON reports, read-only diagnostics, bounded job listing and safe metadata retention.

## 1.0.0

- Existing pinned pipeline library, supervised runner, replay bundles, verified handoffs and MCP jobs.

## Release process

Use semantic versions: patch for compatible corrections, minor for compatible
capabilities and new opt-in policies, major for breaking CLI/protocol or bundle
contracts. Document deliberate migrations and historical bundle behavior.

Prepare a release on a reviewed branch: update the version in `pyproject.toml`,
move Unreleased changes under that version, run all applicable tests and the
package preparation workflow, and review its wheel/sdist artifacts. Only after
that review should a maintainer tag the exact commit and publish a release.
Release preparation does not publish artifacts or change server installations.
