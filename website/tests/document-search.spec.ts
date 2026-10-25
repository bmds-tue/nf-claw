import { expect, test } from "@playwright/test";
import { buildDocSearch, searchDocs } from "../src/lib/doc-search";

test("section links share renderer IDs, preserve identifiers and match body remedies", () => {
  const index = buildDocSearch([{ slug: "fixes", title: "Troubleshooting", content:
    "# Troubleshooting\n\n## Remedy\nNetwork is unreachable: set `NFCLAW_LIBRARY_ROOT`.\n\n## Remedy\nSecond remedy.\n" }]);
  const match = searchDocs(index, "Network is unreachable");
  expect(match).toHaveLength(1);
  expect(match[0].href).toBe("/docs/fixes/#remedy");
  expect(match[0].snippet).toContain("NFCLAW_LIBRARY_ROOT");
  expect(searchDocs(index, "NFCLAW_LIBRARY_ROOT")).toHaveLength(1);
  expect(searchDocs(index, "Second remedy")[0].href).toBe("/docs/fixes/#remedy-1");
  expect(searchDocs(index, ".*")).toEqual([]);
});

test("fenced headings do not create incorrect anchors and query markup stays literal", () => {
  const index = buildDocSearch([{ slug: "safe", title: "Safe", content:
    "# Safe\n\n## Actual section\n```\n## A code example\nConnection refused\n```\n<script>alert(1)</script>\n" }]);
  expect(searchDocs(index, "Connection refused")[0].href).toBe("/docs/safe/#actual-section");
  expect(searchDocs(index, "<script>")).toEqual([]);
});
