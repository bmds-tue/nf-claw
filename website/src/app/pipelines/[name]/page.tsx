import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Boxes,
  Calendar,
  ChevronRight,
  GitCommitHorizontal,
  Github,
  Link2,
  Layers,
  ListChecks,
  PackageOpen,
  Puzzle,
  SlidersHorizontal,
  Table2,
  Terminal,
  Wrench,
} from "lucide-react";
import { getPipeline, getPipelines, githubRepoPath, pipelineNames } from "@/lib/data";
import { toSkill, categorize, colorForCategory } from "@/lib/derive";
import { Markdown } from "@/components/ui/markdown";
import { CodeBlock } from "@/components/ui/code-block";
import { InlineMarkdown } from "@/components/ui/inline-markdown";
import { ParameterExplorer } from "@/components/pipeline/parameter-explorer";
import { Reveal } from "@/components/ui/reveal";
import { SectionNav, type SectionLink } from "@/components/ui/section-nav";
import { RememberVisit } from "@/components/pipeline/remember-visit";
import { OG_IMAGE, siteUrl } from "@/lib/site";
import { cn, formatDate } from "@/lib/utils";

export function generateStaticParams() {
  return pipelineNames().map((name) => ({ name }));
}

export async function generateMetadata({ params }: { params: Promise<{ name: string }> }): Promise<Metadata> {
  const { name } = await params;
  const p = getPipeline(name);
  if (!p) return { title: "Pipeline not found" };
  const title = `${p.name} ${p.version}`;
  return {
    title,
    description: p.description,
    // absolute: Next does not add the base path to metadata URLs
    alternates: { canonical: siteUrl(`/pipelines/${p.name}/`) },
    openGraph: { title: `${title} · nf-claw`, description: p.description, type: "article", images: [OG_IMAGE] },
  };
}

export default async function PipelinePage({ params }: { params: Promise<{ name: string }> }) {
  const { name } = await params;
  const pipeline = getPipeline(name);
  if (!pipeline) notFound();

  const all = getPipelines();
  const index = all.findIndex((p) => p.name === pipeline.name);
  const prev = all[(index - 1 + all.length) % all.length];
  const next = all[(index + 1) % all.length];

  const skill = toSkill(pipeline);
  const category = categorize(pipeline);
  const accent = colorForCategory(category);
  const gh = githubRepoPath(pipeline.url);
  const schema = gh ? `https://github.com/${gh}/blob/${pipeline.version}/nextflow_schema.json` : null;
  const upstream = gh ? `https://github.com/${gh}/tree/${pipeline.version}` : null;

  // The header(s) exactly as skill.md gives them; the intro states the rule that goes with them.
  const headers = pipeline.samplesheetHeaders;
  const sheetFormat = (headers[0]?.format ?? "csv").toUpperCase();
  const inAHeader = new Set(
    headers.flatMap((h) => h.header.split(h.format === "tsv" ? "\t" : ",").map((c) => c.trim())),
  );
  const appendable = pipeline.samplesheet.some((c) => !inAHeader.has(c.column));
  const sheetIntro =
    headers.length > 1
      ? `A ${sheetFormat}. Each row uses exactly one of these column groups (columns from more than one fail validation) — pick the header that matches your data.`
      : headers.length === 1
        ? `A ${sheetFormat} with this header (the columns the schema requires).`
        : "The columns the samplesheet accepts.";

  const facts = [
    { icon: SlidersHorizontal, label: "Parameters", value: pipeline.parameterCount, href: "#parameters" },
    { icon: Layers, label: "Groups", value: pipeline.groups.length, href: "#parameters" },
    { icon: Puzzle, label: "nf-core modules", value: pipeline.moduleCount, href: upstream ? `${upstream}/modules/nf-core` : null },
    { icon: Table2, label: "Samplesheet cols", value: pipeline.samplesheet.length, href: pipeline.samplesheet.length ? "#samplesheet" : null },
  ];

  const sections: SectionLink[] = [
    { id: "run", label: "Run it" },
    ...(pipeline.samplesheet.length ? [{ id: "samplesheet", label: "Samplesheet", count: pipeline.samplesheet.length }] : []),
    ...(pipeline.requiredParams.length ? [{ id: "required", label: "Required", count: pipeline.requiredParams.length }] : []),
    { id: "parameters", label: "Parameters", count: pipeline.parameterCount },
    ...(pipeline.outputs ? [{ id: "outputs", label: "Outputs" }] : []),
    ...(pipeline.feeds.length || pipeline.fedBy.length
      ? [{ id: "chaining", label: "Chaining", count: pipeline.feeds.length + pipeline.fedBy.length }]
      : []),
  ];

  return (
    <div className="container-site pt-24 md:pt-28">
      <RememberVisit name={pipeline.name} />
      {/* breadcrumb */}
      <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-1.5 text-sm text-fog-dim">
        <Link href="/pipelines/" className="inline-flex items-center gap-1.5 transition hover:text-fog">
          <ArrowLeft className="h-4 w-4" /> Pipelines
        </Link>
        <ChevronRight className="h-3.5 w-3.5 text-fog-faint" />
        <Link href={`/pipelines/?domain=${encodeURIComponent(category)}`} className="inline-flex items-center gap-1.5 transition hover:text-fog">
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: accent }} />
          {category}
        </Link>
        <ChevronRight className="h-3.5 w-3.5 text-fog-faint" />
        <span className="font-mono text-fog-muted" aria-current="page">
          {pipeline.name}
        </span>
      </nav>

      {/* header */}
      <Reveal className="mt-6">
        <div className="relative overflow-hidden rounded-4xl border border-white/[0.07] bg-white/[0.015] p-6 sm:p-8 md:p-12">
          <div aria-hidden className="absolute -right-20 -top-20 h-80 w-80 rounded-full blur-[120px]" style={{ background: `${accent}2e` }} />
          <div aria-hidden className="absolute inset-0 bg-grid-faint opacity-40 [background-size:40px_40px] [mask-image:radial-gradient(ellipse_at_top_right,black,transparent_70%)]" />
          <div className="relative">
            <div className="flex flex-wrap items-center gap-2">
              <span className="chip">
                <span className="h-2 w-2 rounded-full" style={{ background: accent }} />
                {category}
              </span>
              <span className="chip">{pipeline.policy || "pinned release"}</span>
            </div>

            <h1 className="mt-5 break-words font-mono text-4xl font-semibold tracking-tight text-fog sm:text-5xl md:text-6xl">
              {pipeline.name}
            </h1>
            <p className="mt-2 text-sm text-fog-dim">{pipeline.pipeline}</p>
            <p className="mt-5 max-w-2xl text-base leading-relaxed text-fog-muted sm:text-lg">
              <InlineMarkdown text={pipeline.description} />
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-2.5">
              <span className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2 text-sm">
                <span className="text-fog-dim">version</span>
                <span className="font-mono font-semibold text-fog">{pipeline.version}</span>
              </span>
              <span className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2 text-sm" title={pipeline.commit}>
                <GitCommitHorizontal className="h-4 w-4 text-fog-dim" />
                <span className="font-mono text-fog">{pipeline.commit.slice(0, 10)}</span>
              </span>
              {pipeline.releaseDate && (
                <span className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2 text-sm">
                  <Calendar className="h-4 w-4 text-fog-dim" />
                  <span className="text-fog">{formatDate(pipeline.releaseDate)}</span>
                </span>
              )}
              {upstream && (
                <a
                  href={upstream}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2 text-sm text-fog transition hover:border-claw-400/30 hover:bg-white/[0.05]"
                >
                  <Github className="h-4 w-4" /> Upstream
                </a>
              )}
              {pipeline.usageUrl && (
                <a
                  href={pipeline.usageUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2 text-sm text-fog transition hover:border-claw-400/30 hover:bg-white/[0.05]"
                >
                  <BookOpen className="h-4 w-4" /> Usage docs
                </a>
              )}
            </div>

            {pipeline.tools.length > 0 && (
              <div className="mt-8 border-t border-white/[0.06] pt-6">
                <p className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-fog-dim">
                  <Wrench className="h-3.5 w-3.5" /> Key tools
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {pipeline.tools.map((t) => (
                    <span key={t} className="rounded-lg border border-white/[0.07] bg-white/[0.03] px-2.5 py-1 text-xs text-fog-muted">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </Reveal>

      {/* facts */}
      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        {facts.map((f) => {
          const inner = (
            <>
              <f.icon className="h-5 w-5 text-claw-400/80" />
              <div className="mt-3 text-3xl font-semibold tabular-nums text-fog">{f.value}</div>
              <div className="text-[11px] uppercase tracking-[0.14em] text-fog-dim">{f.label}</div>
            </>
          );
          return f.href ? (
            <a
              key={f.label}
              href={f.href}
              target={f.href.startsWith("http") ? "_blank" : undefined}
              rel={f.href.startsWith("http") ? "noreferrer" : undefined}
              className="glass glass-hover block p-5"
            >
              {inner}
            </a>
          ) : (
            <div key={f.label} className="glass p-5">
              {inner}
            </div>
          );
        })}
      </div>

      <SectionNav sections={sections} className="mt-8" />

      {/* run it */}
      <section id="run" data-progress="Run it" className="mt-10 scroll-mt-14">
        <SectionTitle icon={Terminal}>Run it</SectionTitle>
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <CodeBlock code={pipeline.runCommand} label="nfclaw" />
          {pipeline.rawCommand && <CodeBlock code={pipeline.rawCommand} label="raw nextflow" />}
        </div>
        {pipeline.demoCommand && (
          <div className="mt-4">
            <CodeBlock code={pipeline.demoCommand} label="demo · bundled test profile" />
          </div>
        )}
        <div className="mt-6 space-y-6">
          {pipeline.operatingGuidance.map((section) => (
            <div key={section.title} className="glass p-5">
              <h3 className="text-lg font-semibold text-fog">{section.title}</h3>
              <Markdown content={section.content} links={{
                source: `pipelines/${pipeline.name}/skill.md`, docs: {},
                repoBlobBase: "https://github.com/danilomonge/nf-claw/blob/main",
              }} />
            </div>
          ))}
        </div>
      </section>

      {/* samplesheet */}
      {pipeline.samplesheet.length > 0 && (
        <section id="samplesheet" data-progress="Samplesheet" className="mt-16 scroll-mt-14">
          <SectionTitle icon={Table2}>Samplesheet</SectionTitle>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-fog-muted">
            {sheetIntro} Fill each value per the constraints below
            {appendable ? "; optional columns from the table may be appended." : "."}
          </p>
          {headers.map((h) => (
            <div key={h.header} className="mt-5">
              <CodeBlock code={h.header} label={`samplesheet.${h.format} header`} />
            </div>
          ))}
          <div className="glass mt-4 overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b border-white/[0.07] text-left text-[11px] uppercase tracking-wider text-fog-dim">
                  <th className="px-5 py-3 font-medium">Column</th>
                  <th className="px-5 py-3 font-medium">Type</th>
                  <th className="px-5 py-3 font-medium">Required</th>
                  <th className="px-5 py-3 font-medium">Allowed / constraints</th>
                </tr>
              </thead>
              <tbody>
                {pipeline.samplesheet.map((c) => (
                  <tr key={c.column} className="border-b border-white/[0.04] transition-colors last:border-0 hover:bg-white/[0.02]">
                    <td className="px-5 py-3 align-top">
                      <code className="font-mono text-fog">{c.column}</code>
                    </td>
                    <td className="px-5 py-3 align-top text-fog-muted">{c.type}</td>
                    <td className="px-5 py-3 align-top">
                      {c.required ? (
                        <span className="rounded-md border border-claw-400/20 bg-claw-500/15 px-1.5 py-0.5 text-[11px] text-claw-300">required</span>
                      ) : (
                        <span className="text-xs text-fog-dim">optional</span>
                      )}
                    </td>
                    <td className="px-5 py-3 align-top text-fog-muted">
                      {c.allowed.length > 0 && (
                        <span className="mb-1 flex flex-wrap gap-1">
                          {c.allowed.map((a) => (
                            <code key={a} className="rounded bg-white/[0.05] px-1.5 py-0.5 font-mono text-[11px] text-fog">
                              {a}
                            </code>
                          ))}
                        </span>
                      )}
                      {c.constraints && <span className="break-all font-mono text-[11px] text-fog-dim">{c.constraints}</span>}
                      {!c.allowed.length && !c.constraints && <span className="text-fog-dim">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* required params */}
      {pipeline.requiredParams.length > 0 && (
        <section id="required" data-progress="Required" className="mt-16 scroll-mt-14">
          <SectionTitle icon={ListChecks}>Required parameters</SectionTitle>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {pipeline.requiredParams.map((r) => (
              <div key={r.name} className="glass p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <code className="font-mono text-sm font-semibold text-claw-300">{r.name}</code>
                  <span className="chip px-2 py-0.5 text-[10px]">{r.type}</span>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-fog-muted">
                  <InlineMarkdown text={r.description} />
                </p>
                {r.allowed.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {r.allowed.map((a) => (
                      <code key={a} className="rounded bg-white/[0.05] px-1.5 py-0.5 font-mono text-[11px] text-fog">
                        {a}
                      </code>
                    ))}
                  </div>
                )}
                {r.constraints && (
                  <p className="mt-2 text-xs text-fog-dim">
                    Constraint · <span className="font-mono">{r.constraints}</span>
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* parameter explorer */}
      <section id="parameters" data-progress="Parameters" className="mt-16 scroll-mt-14">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <SectionTitle icon={Boxes}>Parameter explorer</SectionTitle>
          <span className="text-sm text-fog-dim">
            {pipeline.parameterCount} parameters · {pipeline.groups.length} groups
          </span>
        </div>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-fog-muted">
          Every parameter from the pinned <code className="font-mono text-fog">nextflow_schema.json</code>.
          nfclaw checks explicit values before launch; complex rules use the pinned pipeline&apos;s runtime validation.
          Search, filter by group, and expand any parameter for its default, allowed values and constraints.
        </p>
        <div className="mt-6">
          <ParameterExplorer params={skill.params} groups={skill.groups} schemaUrl={schema} />
        </div>
      </section>

      {/* outputs */}
      {pipeline.outputs && (
        <section id="outputs" data-progress="Outputs" className="mt-16 scroll-mt-14">
          <SectionTitle icon={PackageOpen}>Outputs</SectionTitle>
          <div className="glass mt-5 p-6">
            <p className="text-pretty leading-relaxed text-fog-muted">
              <InlineMarkdown text={pipeline.outputs} />
            </p>
          </div>
        </section>
      )}

      {/* chaining */}
      {(pipeline.feeds.length > 0 || pipeline.fedBy.length > 0) && (
        <section id="chaining" data-progress="Chaining" className="mt-16 scroll-mt-14">
          <SectionTitle icon={Link2}>Chaining</SectionTitle>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-fog-muted">
            Run {pipeline.name} as one stage of a chain: <code className="font-mono text-fog">nfclaw chain run</code> starts
            each stage only after the one before it succeeded, and prepares its inputs from that stage&apos;s outputs. Every
            rule is checked against both pinned schemas.
          </p>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {(
              [
                ["Feeds into", pipeline.feeds],
                ["Fed by", pipeline.fedBy],
              ] as const
            )
              .filter(([, edges]) => edges.length > 0)
              .map(([title, edges]) => (
                <div key={title} className="glass p-5">
                  <h3 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-fog-dim">{title}</h3>
                  <ul className="mt-3 space-y-3">
                    {edges.map((e) => (
                      <li key={e.pipeline} className="text-sm leading-relaxed text-fog-muted">
                        <Link href={`/pipelines/${e.pipeline}/`} className="font-mono font-semibold text-claw-300 hover:text-claw-200">
                          {e.pipeline}
                        </Link>
                        {e.description && (
                          <>
                            {" — "}
                            <InlineMarkdown text={e.description} />
                          </>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
          </div>
          <div className="mt-4">
            <CodeBlock code={`nfclaw chain edges ${pipeline.name}`} label="nfclaw" />
          </div>
        </section>
      )}

      {/* prev / next */}
      {all.length > 1 && (
        <nav aria-label="More pipelines" className="mt-20 grid gap-3 sm:grid-cols-2">
          <PagerLink href={`/pipelines/${prev.name}/`} dir="prev" name={prev.name} sub={prev.description} color={colorForCategory(categorize(prev))} />
          <PagerLink href={`/pipelines/${next.name}/`} dir="next" name={next.name} sub={next.description} color={colorForCategory(categorize(next))} />
        </nav>
      )}
    </div>
  );
}

function SectionTitle({ icon: Icon, children }: { icon: typeof Terminal; children: React.ReactNode }) {
  return (
    <h2 className="flex items-center gap-2.5 text-2xl font-semibold tracking-tight text-fog">
      <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03]">
        <Icon className="h-4 w-4 text-claw-400" />
      </span>
      {children}
    </h2>
  );
}

function PagerLink({
  href,
  dir,
  name,
  sub,
  color,
}: {
  href: string;
  dir: "prev" | "next";
  name: string;
  sub: string;
  color: string;
}) {
  return (
    <Link href={href} className={cn("glass glass-hover group flex items-center gap-4 p-5", dir === "next" && "sm:flex-row-reverse sm:text-right")}>
      <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] text-fog-muted transition group-hover:border-claw-400/30 group-hover:text-claw-300">
        {dir === "prev" ? (
          <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
        ) : (
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        )}
      </span>
      <span className="min-w-0">
        <span className="block text-[11px] uppercase tracking-[0.16em] text-fog-dim">{dir === "prev" ? "Previous" : "Next"}</span>
        <span className={cn("mt-0.5 flex items-center gap-2 font-mono text-lg font-semibold text-fog", dir === "next" && "sm:justify-end")}>
          <span className="h-2 w-2 rounded-full" style={{ background: color }} />
          {name}
        </span>
        <span className="mt-0.5 line-clamp-1 text-xs text-fog-dim">{sub}</span>
      </span>
    </Link>
  );
}
