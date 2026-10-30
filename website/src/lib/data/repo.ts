import fs from "node:fs";
import { execFileSync } from "node:child_process";
import { repoRoot, repoPath, readText } from "./paths";
import { getPipelines, allParameters } from "./pipelines";
import type { Commit, DocPage, RepoMeta, TimelineEntry } from "../types";

function git(args: string[]): string {
  try {
    return execFileSync("git", ["-C", repoRoot(), ...args], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return "";
  }
}

const CONVENTIONAL = /^(\w+)(?:\(([^)]+)\))?(!)?:\s*(.+)$/;

export function getCommits(limit = 20): Commit[] {
  const out = git(["log", `-${limit}`, "--pretty=format:%H%x1f%an%x1f%cI%x1f%s"]);
  if (!out) return [];
  return out.split("\n").map((line) => {
    const [hash, author, date, subject] = line.split("\x1f");
    const m = subject?.match(CONVENTIONAL);
    return {
      hash: (hash ?? "").slice(0, 7),
      author: author ?? "",
      date: date ?? "",
      subject: subject ?? "",
      summary: m ? m[4] : subject ?? "",
      type: m ? m[1] : null,
      scope: m && m[2] ? m[2] : null,
    };
  });
}

export function getTags(): { name: string; date: string | null }[] {
  // NOTE: `git tag` uses the ref-filter format language, where a byte escape is
  // `%1f` — NOT the pretty-format `%x1f` that `git log` uses. Using `%x1f` here
  // emits the literal text "%x1f", so the split below never separates name from
  // date (the tag title then swallows the raw separator and the date).
  const out = git(["tag", "--sort=-creatordate", "--format=%(refname:short)%1f%(creatordate:iso-strict)"]);
  if (!out) return [];
  return out
    .split("\n")
    .filter(Boolean)
    .map((line) => {
      const [name, date] = line.split("\x1f");
      return { name, date: date || null };
    });
}

/** "owner/repo" from a GitHub URL (https or ssh), or null for any other host. */
export function githubRepoPath(url: string): string | null {
  const m = url.match(/github\.com[:/](.+?)(?:\.git)?\/?$/);
  return m ? m[1] : null;
}

export function getRemote(): string | null {
  const url = git(["config", "--get", "remote.origin.url"]);
  return url ? githubRepoPath(url) : null;
}

/**
 * The branch GitHub serves the repository from, for links to its files: the remote's default branch
 * when the clone knows it (`origin/HEAD`), else the branch being built (CI deploys `main`), else
 * "main" — a detached checkout reports "HEAD", and a local feature branch need not exist on GitHub.
 */
export function getDefaultBranch(): string {
  const remoteHead = git(["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"]);
  if (remoteHead.startsWith("origin/")) return remoteHead.slice("origin/".length);
  const current = git(["rev-parse", "--abbrev-ref", "HEAD"]);
  return current && current !== "HEAD" ? current : "main";
}

let docsCache: DocPage[] | null = null;

/** README, the root guides (CONTRIBUTING, AGENTS, SECURITY, NOTICE) and every docs/*.md. Read once per build. */
export function getDocs(): DocPage[] {
  if (docsCache) return docsCache;
  const docs: DocPage[] = [];

  const readme = readText("README.md");
  if (readme) {
    docs.push({ slug: "readme", title: "README", source: "README.md", content: readme });
  }

  // Root-level guides, titled for a reader (their H1s repeat the project name).
  const extras: [string, string][] = [
    ["CONTRIBUTING.md", "Contributing"],
    ["AGENTS.md", "Agent guide"],
    ["SECURITY.md", "Security policy"],
    ["NOTICE", "Notice & credits"],
  ];
  for (const [f, title] of extras) {
    const content = readText(f);
    if (content) {
      docs.push({
        slug: f.toLowerCase().replace(/\.md$/, "").replace(/[^a-z0-9]+/g, "-"),
        title,
        source: f,
        content,
      });
    }
  }

  const docsDir = repoPath("docs");
  try {
    for (const f of fs.readdirSync(docsDir)) {
      // Filesystem metadata (including macOS ._ sidecars) is not documentation.
      if (f.startsWith(".") || !f.endsWith(".md")) continue;
      const content = readText("docs", f);
      if (!content) continue;
      const slug = f.replace(/\.md$/, "");
      const titleM = content.match(/^#\s+(.+)$/m);
      docs.push({
        slug,
        title: titleM ? titleM[1].trim() : slug.replace(/[-_]/g, " "),
        source: `docs/${f}`,
        content,
      });
    }
  } catch {
    /* no docs dir */
  }

  docsCache = docs;
  return docs;
}

export function getDoc(slug: string): DocPage | undefined {
  return getDocs().find((d) => d.slug === slug);
}

/** A unified timeline: each pinned pipeline release + repo tags as milestones. */
export function getTimeline(): TimelineEntry[] {
  const entries: TimelineEntry[] = [];

  for (const p of getPipelines()) {
    entries.push({
      id: `release-${p.name}`,
      kind: "release",
      title: `${p.pipeline} ${p.version}`,
      subtitle: p.description,
      date: p.releaseDate,
      pipeline: p.name,
      version: p.version,
    });
  }

  for (const tag of getTags()) {
    entries.push({
      id: `tag-${tag.name}`,
      kind: "tag",
      title: tag.name,
      subtitle: "nf-claw release tag",
      date: tag.date,
    });
  }

  return entries.sort((a, b) => {
    const da = a.date ? new Date(a.date).getTime() : 0;
    const db = b.date ? new Date(b.date).getTime() : 0;
    return db - da;
  });
}

function extractTagline(): { tagline: string; description: string } {
  const readme = readText("README.md") ?? "";
  // First non-empty paragraph after the H1.
  const afterH1 = readme.split(/^#\s+nf-claw\s*$/m)[1] ?? readme;
  const para = afterH1
    .split("\n\n")
    .map((s) => s.trim())
    .find((s) => s && !s.startsWith("#") && !s.startsWith("<") && !s.startsWith("-"));
  const clean = (para ?? "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
  // The headline tagline is the first sentence of the README's lead paragraph.
  // The description is the rest of that paragraph, so the hero does not repeat
  // the headline verbatim; single-sentence leads still fall back to the full text.
  const firstSentence = clean.match(/^.*?[.!?](?=\s|$)/)?.[0] ?? clean;
  const rest = clean.slice(firstSentence.length).trim();
  return {
    tagline:
      firstSentence ||
      "A self-maintaining library of nf-core pipelines for AI agents.",
    description: rest || clean,
  };
}

let metaCache: RepoMeta | null = null;

/** The repository's name, lead and headline numbers. Computed once per build (it runs git). */
export function getRepoMeta(): RepoMeta {
  if (metaCache) return metaCache;
  const pipelines = getPipelines();
  const { tagline, description } = extractTagline();
  metaCache = {
    tagline,
    description,
    remote: getRemote(),
    stats: {
      pipelines: pipelines.length,
      skills: pipelines.length, // each pipeline ships one agent skill (skill.md)
      parameters: allParameters().length,
      // the vendored modules of every pipeline summed (one module vendored twice counts twice)
      modules: pipelines.reduce((n, p) => n + p.moduleCount, 0),
      latestUpdate: getCommits(1)[0]?.date ?? null,
    },
  };
  return metaCache;
}
