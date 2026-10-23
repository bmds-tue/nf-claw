import Link from "next/link";
import { ArrowUpRight, Github } from "lucide-react";
import { Logo } from "@/components/ui/logo";
import { categorize, colorForCategory, domainCounts } from "@/lib/derive";
import type { Pipeline } from "@/lib/types";

export function Footer({ repo, pipelines }: { repo: string | null; pipelines: Pipeline[] }) {
  const githubUrl = repo ? `https://github.com/${repo}` : "https://github.com";
  const year = new Date().getFullYear();

  const domains = domainCounts(pipelines.map((p) => ({ category: categorize(p) })));

  return (
    <footer className="relative mt-24 border-t border-white/[0.06]">
      <div className="container-site grid gap-12 py-16 sm:grid-cols-2 lg:grid-cols-[1.3fr_1.2fr_0.8fr_0.8fr]">
        <div>
          <Logo size={40} withText />
          <p className="mt-5 max-w-xs text-sm leading-relaxed text-fog-muted">
            A self-maintaining, token-minimal library of nf-core pipelines for AI agents. The
            repository is the single source of truth — this interface regenerates itself from it.
          </p>
          <a
            href={githubUrl}
            target="_blank"
            rel="noreferrer"
            className="mt-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-fog transition hover:border-claw-400/30 hover:bg-white/[0.05]"
          >
            <Github className="h-4 w-4" /> View on GitHub
          </a>
        </div>

        <FooterCol title="Domains">
          {domains.map((d) => (
            <li key={d.name}>
              <Link
                href={`/pipelines/?domain=${encodeURIComponent(d.name)}`}
                className="group inline-flex items-center gap-2.5 text-sm text-fog-muted transition hover:text-fog"
              >
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: colorForCategory(d.name) }} />
                {d.name}
                <span className="text-xs text-fog-dim transition group-hover:text-fog-muted">{d.count}</span>
              </Link>
            </li>
          ))}
        </FooterCol>

        <FooterCol title="Explore">
          <FooterLink href="/pipelines/">All pipelines</FooterLink>
          <FooterLink href="/#pipelines">Pipeline universe</FooterLink>
          <FooterLink href="/#skills">Skills explorer</FooterLink>
          <FooterLink href="/#activity">Live activity</FooterLink>
          <FooterLink href="/#releases">Release timeline</FooterLink>
          <FooterLink href="/docs/">Documentation</FooterLink>
        </FooterCol>

        <FooterCol title="Resources">
          <FooterLink href="/docs/readme/">README</FooterLink>
          <FooterLink href="/docs/architecture/">Architecture</FooterLink>
          <FooterLink href="/docs/known-issues/">Known issues</FooterLink>
          <FooterLink href="https://nf-co.re" external>
            nf-core
          </FooterLink>
          <FooterLink href="https://www.nextflow.io" external>
            Nextflow
          </FooterLink>
        </FooterCol>
      </div>

      <div className="border-t border-white/[0.06]">
        <div className="container-site flex flex-col items-center justify-between gap-3 py-6 text-xs text-fog-dim md:flex-row">
          <p>© {year} nf-claw · MIT licensed · Pipelines © the nf-core community.</p>
          <p className="flex items-center gap-2 font-mono">
            <span className="h-1.5 w-1.5 rounded-full bg-claw-400/80" />
            Generated from the repository · {pipelines.length} pipelines
          </p>
        </div>
      </div>
    </footer>
  );
}

function FooterCol({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-fog-dim">{title}</h2>
      <ul className="space-y-2.5">{children}</ul>
    </div>
  );
}

function FooterLink({
  href,
  children,
  external,
}: {
  href: string;
  children: React.ReactNode;
  external?: boolean;
}) {
  const cls = "group inline-flex items-center gap-1 text-sm text-fog-muted transition hover:text-claw-300";
  return (
    <li>
      {external ? (
        <a href={href} target="_blank" rel="noreferrer" className={cls}>
          {children}
          <ArrowUpRight className="h-3 w-3 opacity-50 transition group-hover:-translate-y-px group-hover:translate-x-px group-hover:opacity-100" />
        </a>
      ) : (
        <Link href={href} className={cls}>
          {children}
        </Link>
      )}
    </li>
  );
}
