// Optional live-data adapter. The site is local-first: it is fully driven by repository files
// and local git. When the checkout has a GitHub remote AND a token is present (GITHUB_TOKEN /
// GH_TOKEN), the build adds the repository's latest Actions runs from the REST API. Without a
// token it no-ops, and the UI shows the local equivalents (workflow definitions, git log).

import { getRemote } from "./repo";

export interface LiveRun {
  name: string;
  status: string;
  conclusion: string | null;
  branch: string;
  url: string;
  date: string;
}

function liveEnabled(): boolean {
  return Boolean(getRemote() && (process.env.GITHUB_TOKEN || process.env.GH_TOKEN));
}

async function gh<T>(repo: string, endpoint: string): Promise<T | null> {
  const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
  if (!token) return null;
  try {
    const res = await fetch(`https://api.github.com/repos/${repo}/${endpoint}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
      },
      // A static export fetches only while it builds; repeated local builds reuse the
      // response for up to an hour instead of calling the API again.
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function getLiveRuns(limit = 6): Promise<LiveRun[] | null> {
  const repo = getRemote();
  if (!repo || !liveEnabled()) return null;
  const data = await gh<{ workflow_runs: Record<string, unknown>[] }>(
    repo,
    `actions/runs?per_page=${limit}`,
  );
  if (!data?.workflow_runs) return null;
  return data.workflow_runs.map((r) => ({
    name: String(r.name ?? r.display_title ?? "run"),
    status: String(r.status ?? ""),
    conclusion: r.conclusion ? String(r.conclusion) : null,
    branch: String(r.head_branch ?? ""),
    url: String(r.html_url ?? ""),
    date: String(r.created_at ?? ""),
  }));
}
