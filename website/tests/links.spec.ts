import { expect, test } from "@playwright/test";
import { safeHref } from "../src/lib/utils";

// Inline Markdown renders upstream schema descriptions: only relative, web and mail targets link.
test("inline links keep relative, web and mail targets only", () => {
  for (const href of ["https://nf-co.re/rnaseq", "http://example.org", "mailto:a@example.org",
    "#usage", "/docs/preflight", "docs/usage.md", "usage.md?view=a:b"]) {
    expect(safeHref(href), href).toBe(true);
  }
  for (const href of ["javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,x",
    "vbscript:x", "file:///etc/passwd"]) {
    expect(safeHref(href), href).toBe(false);
  }
});
