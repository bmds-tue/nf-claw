import fs from "node:fs";
import path from "node:path";

/**
 * Locate the nf-claw repository root by walking up from the website directory
 * until we find the catalog (the repository's pipeline index). This keeps the
 * data layer pointed at the real source of truth regardless of CWD.
 */
let cached: string | null = null;

export function repoRoot(): string {
  if (cached) return cached;
  const override = process.env.NFCLAW_REPO_ROOT;
  if (override && fs.existsSync(path.join(override, "catalog.json"))) {
    cached = override;
    return cached;
  }
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (fs.existsSync(path.join(dir, "catalog.json"))) {
      cached = dir;
      return cached;
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  // Fallback: assume the website lives one level below the repo root.
  cached = path.resolve(process.cwd(), "..");
  return cached;
}

export function repoPath(...segments: string[]): string {
  return path.join(repoRoot(), ...segments);
}

export function readText(...segments: string[]): string | null {
  try {
    return fs.readFileSync(repoPath(...segments), "utf8");
  } catch {
    return null;
  }
}
