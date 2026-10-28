import {
  Activity,
  ArrowUpRight,
  CalendarClock,
  CircleDot,
  GitCommitHorizontal,
  PlayCircle,
  ShieldCheck,
  Workflow as WorkflowIcon,
} from "lucide-react";
import { Reveal } from "@/components/ui/reveal";
import { RelativeTime } from "@/components/ui/relative-time";
import { SectionHeading } from "@/components/ui/section-heading";
import type { Commit, Workflow } from "@/lib/types";
import type { LiveRun } from "@/lib/data/github";
import { commitTone, humanizeCron, TONE_CLASS } from "@/lib/format";
import { cleanAuthor, cn } from "@/lib/utils";

export function LiveStatus({
  commits,
  workflows,
  liveRuns,
  lastUpdate,
  repo,
}: {
  commits: Commit[];
  workflows: Workflow[];
  liveRuns: LiveRun[] | null;
  lastUpdate: string | null;
  repo: string | null;
}) {
  const capturedAt = new Date().toISOString();
  const autoUpdate = workflows.find((w) => w.schedule);
  const cron = humanizeCron(autoUpdate?.schedule ?? null);
  const gh = repo ? `https://github.com/${repo}` : null;

  return (
    <section id="activity" data-progress="Activity" className="section container-site">
      <SectionHeading
        eyebrow="Build snapshot"
        title="Repository status"
        description="Commits and automation captured from git and GitHub Actions when this site was built. Rebuild the site to refresh this view."
      />

      <p className="mt-3 text-xs text-fog-dim">Snapshot captured <time dateTime={capturedAt}>{capturedAt}</time></p>
      {/* status strip */}
      <Reveal className="mt-10">
        <div className="grid gap-3 sm:grid-cols-3">
          <StatusTile
            icon={<CalendarClock className="h-4 w-4" />}
            label="Auto-update"
            value={cron ?? "On demand"}
            sub={autoUpdate ? `${autoUpdate.name} workflow` : "scheduled workflow"}
          />
          <StatusTile
            icon={<ShieldCheck className="h-4 w-4" />}
            label="Drift gate"
            value={workflows.some((w) => /drift/i.test(w.name)) ? "Enforced on every PR" : "Configured"}
            sub="context matches the pinned submodule"
          />
          <StatusTile
            icon={<Activity className="h-4 w-4" />}
            label="Last update"
            value={lastUpdate ? <RelativeTime date={lastUpdate} /> : "—"}
            sub="most recent commit"
          />
        </div>
      </Reveal>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        {/* commit feed — the list fills exactly the height of the right column
            (absolute inset within a flex-1 area), so however much automation
            content there is, the timeline never leaves dead space below it. */}
        <Reveal className="h-full">
          <div className="glass flex h-full flex-col p-5 sm:p-6">
            <div className="mb-5 flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <GitCommitHorizontal className="h-4 w-4 text-claw-400" />
                <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-fog-dim">Update history</h3>
              </div>
              {gh && (
                <a
                  href={`${gh}/commits`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-fog-dim transition hover:text-claw-300"
                >
                  All commits <ArrowUpRight className="h-3 w-3" />
                </a>
              )}
            </div>
            <div className="relative min-h-[24rem] flex-1">
              <ol className="mask-fade-list absolute inset-0 space-y-0.5 overflow-hidden before:absolute before:left-[5px] before:top-2 before:h-[calc(100%-1rem)] before:w-px before:bg-white/[0.07]">
                {commits.map((c) => {
                  const body = (
                    <>
                      <span className="absolute left-0 top-3.5 h-2.5 w-2.5 rounded-full border-2 border-ink-900 bg-claw-500/80 transition group-hover:bg-claw-300" />
                      <div className="min-w-0 flex-1">
                        <div className="flex min-w-0 items-center gap-2">
                          {c.type && (
                            <span
                              className={cn(
                                "shrink-0 rounded-md border px-1.5 py-0.5 text-[10px] font-medium",
                                TONE_CLASS[commitTone(c.type)],
                              )}
                            >
                              {c.type}
                              {c.scope ? `(${c.scope})` : ""}
                            </span>
                          )}
                          <span className="truncate text-sm text-fog transition group-hover:text-white">
                            {c.summary}
                          </span>
                        </div>
                        <div className="mt-0.5 flex items-center gap-2 text-xs text-fog-dim">
                          <span className="font-mono">{c.hash}</span>
                          <span aria-hidden>·</span>
                          <span className="truncate">{cleanAuthor(c.author)}</span>
                          <span aria-hidden>·</span>
                          <RelativeTime date={c.date} className="shrink-0" />
                        </div>
                      </div>
                    </>
                  );
                  return (
                    <li key={c.hash}>
                      {gh ? (
                        <a
                          href={`${gh}/commit/${c.hash}`}
                          target="_blank"
                          rel="noreferrer"
                          className="group relative flex gap-4 rounded-xl py-2.5 pl-6 pr-2 transition hover:bg-white/[0.025]"
                        >
                          {body}
                        </a>
                      ) : (
                        <div className="group relative flex gap-4 py-2.5 pl-6">{body}</div>
                      )}
                    </li>
                  );
                })}
              </ol>
            </div>
          </div>
        </Reveal>

        {/* automation + runs */}
        <div className="flex flex-col gap-6">
          <Reveal delay={0.05}>
            <div className="glass p-5 sm:p-6">
              <div className="mb-5 flex items-center gap-2">
                <WorkflowIcon className="h-4 w-4 text-claw-400" />
                <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-fog-dim">CI / CD workflows</h3>
                <span className="ml-auto text-xs text-fog-dim">{workflows.length}</span>
              </div>
              <div className="space-y-2.5">
                {workflows.map((w) => {
                  const inner = (
                    <>
                      <div className="flex items-center justify-between gap-2">
                        <span className="flex min-w-0 items-center gap-2 font-mono text-sm text-fog">
                          <CircleDot className="h-3.5 w-3.5 shrink-0 text-claw-400" />
                          <span className="truncate">{w.name}</span>
                        </span>
                        <span className="flex shrink-0 items-center gap-1 text-[11px] text-fog-dim">
                          {w.jobs.length} job{w.jobs.length !== 1 ? "s" : ""}
                          {gh && <ArrowUpRight className="h-3 w-3 opacity-0 transition group-hover:opacity-100" />}
                        </span>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {w.triggers.map((t) => (
                          <span key={t} className="chip px-2.5 py-0.5 text-[10px]">
                            {t.replace(/_/g, " ")}
                          </span>
                        ))}
                        {w.schedule && (
                          <span className="chip border-cream/15 px-2.5 py-0.5 text-[10px] text-cream">{humanizeCron(w.schedule)}</span>
                        )}
                      </div>
                    </>
                  );
                  const cls = "group block rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4 transition";
                  return gh ? (
                    <a
                      key={w.file}
                      href={`${gh}/actions/workflows/${w.file}`}
                      target="_blank"
                      rel="noreferrer"
                      className={cn(cls, "hover:border-white/15 hover:bg-white/[0.035]")}
                    >
                      {inner}
                    </a>
                  ) : (
                    <div key={w.file} className={cls}>
                      {inner}
                    </div>
                  );
                })}
              </div>
            </div>
          </Reveal>

          {liveRuns && liveRuns.length > 0 && (
            <Reveal delay={0.1}>
              <div className="glass p-5 sm:p-6">
                <div className="mb-5 flex items-center gap-2">
                  <PlayCircle className="h-4 w-4 text-claw-400" />
                  <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-fog-dim">Recent runs</h3>
                </div>
                <div className="space-y-2">
                  {liveRuns.map((r, i) => (
                    <a
                      key={i}
                      href={r.url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-between gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-2.5 text-sm transition hover:border-white/15"
                    >
                      <span className="flex min-w-0 items-center gap-2 text-fog">
                        <RunDot conclusion={r.conclusion} status={r.status} />
                        <span className="truncate">{r.name}</span>
                      </span>
                      <RelativeTime date={r.date} className="shrink-0 text-xs text-fog-dim" />
                    </a>
                  ))}
                </div>
              </div>
            </Reveal>
          )}
        </div>
      </div>
    </section>
  );
}

function StatusTile({
  icon,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  sub: string;
}) {
  return (
    <div className="glass glass-hover p-5">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-fog-dim">
          {icon}
          {label}
        </span>
        <span className="relative flex h-2 w-2" aria-hidden>
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-claw-400 opacity-60" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-claw-400" />
        </span>
      </div>
      <div className="mt-3 text-lg font-semibold text-fog">{value}</div>
      <div className="mt-0.5 text-xs text-fog-dim">{sub}</div>
    </div>
  );
}

function RunDot({ conclusion, status }: { conclusion: string | null; status: string }) {
  const ok = conclusion === "success";
  const fail = conclusion === "failure" || conclusion === "cancelled";
  const running = status === "in_progress" || status === "queued";
  const color = ok ? "bg-claw-400" : fail ? "bg-red-400" : running ? "bg-cream" : "bg-fog-dim";
  const label = ok ? "succeeded" : fail ? conclusion : running ? "running" : status;
  return (
    <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", color, running && "animate-pulse")} title={label ?? undefined}>
      <span className="sr-only">{label}</span>
    </span>
  );
}
