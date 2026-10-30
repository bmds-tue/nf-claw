import Link from "next/link";
import {
  ArrowUpRight,
  Bot,
  BookOpen,
  Boxes,
  FileText,
  GitPullRequest,
  LifeBuoy,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { StaggerGroup, StaggerItem } from "@/components/ui/reveal";
import { SectionHeading } from "@/components/ui/section-heading";
import { docPreview, readingMinutes } from "@/lib/doc-meta";
import type { DocPage } from "@/lib/types";
import { cn } from "@/lib/utils";

/** An icon that says what kind of document this is, from its slug. */
function iconFor(slug: string): LucideIcon {
  if (slug === "readme") return BookOpen;
  if (/contribut/.test(slug)) return GitPullRequest;
  if (/agent/.test(slug)) return Bot;
  if (/notice|licen/.test(slug)) return Scale;
  if (/architect/.test(slug)) return Boxes;
  if (/compat/.test(slug)) return ShieldCheck;
  if (/secur/.test(slug)) return ShieldAlert;
  if (/issue|trouble/.test(slug)) return LifeBuoy;
  if (/updat/.test(slug)) return RefreshCw;
  return FileText;
}

export function DocsHub({ docs, standalone = false }: { docs: DocPage[]; standalone?: boolean }) {
  const Heading = standalone ? "h1" : "h2";
  const CardHeading = standalone ? "h2" : "h3";
  return (
    <section
      id="docs"
      data-progress={standalone ? undefined : "Docs"}
      className={cn("container-site", standalone ? "pb-12 pt-28 md:pt-32" : "section")}
    >
      <SectionHeading
        as={Heading}
        eyebrow="Single source of truth"
        title="Documentation hub"
        description="Every page here is rendered directly from the repository — README, architecture notes, contributor guides and more. Nothing is maintained by hand; update the markdown and this hub updates itself."
      />

      <StaggerGroup className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-3 lg:gap-5">
        {docs.map((doc, i) => {
          const Icon = iconFor(doc.slug);
          const featured = i === 0;
          return (
            <StaggerItem key={doc.slug} className={cn(featured && "md:col-span-2")}>
              <Link href={`/docs/${doc.slug}/`} className="group block h-full rounded-3xl">
                <article
                  className={cn(
                    "glass glass-hover flex h-full flex-col p-6",
                    featured && "bg-gradient-to-br from-claw-500/[0.06] to-transparent md:p-8",
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.03] text-claw-400 transition-colors group-hover:border-claw-400/30">
                      <Icon className="h-5 w-5" />
                    </span>
                    <ArrowUpRight className="h-5 w-5 text-fog-dim transition-all duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-claw-300" />
                  </div>
                  <CardHeading className={cn("mt-5 font-semibold text-fog", featured ? "text-xl md:text-2xl" : "text-lg")}>
                    {doc.title}
                  </CardHeading>
                  <p className={cn("mt-2 flex-1 text-sm leading-relaxed text-fog-muted", featured && "md:text-base")}>
                    {docPreview(doc.content, featured ? 260 : 150)}
                  </p>
                  <div className="mt-5 flex items-center gap-2 text-xs text-fog-dim">
                    <code className="font-mono">{doc.source}</code>
                    <span aria-hidden>·</span>
                    <span>{readingMinutes(doc.content)} min read</span>
                  </div>
                </article>
              </Link>
            </StaggerItem>
          );
        })}
      </StaggerGroup>
    </section>
  );
}
