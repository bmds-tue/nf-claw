"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowUpRight, Menu, Search, X } from "lucide-react";
import { Github } from "@/components/ui/github-icon";
import { Logo } from "@/components/ui/logo";
import { openPalette, OPEN_PALETTE_EVENT } from "@/components/layout/command-palette";
import { ReadingProgress } from "@/components/layout/reading-progress";
import { lockScroll } from "@/lib/scroll-lock";
import { cn } from "@/lib/utils";
import { EASE } from "@/lib/motion";

const LINKS = [
  { href: "/pipelines/", label: "Pipelines", section: "pipelines", route: "/pipelines" },
  { href: "/#skills", label: "Skills", section: "skills" },
  { href: "/#activity", label: "Activity", section: "activity" },
  { href: "/#releases", label: "Releases", section: "releases" },
  { href: "/docs/", label: "Docs", section: "docs", route: "/docs" },
];

const SECTION_IDS = LINKS.map((l) => l.section);

/** The home section crossing the middle of the viewport (null above the first one). */
function useActiveSection(enabled: boolean) {
  const [active, setActive] = useState<string | null>(null);
  useEffect(() => {
    if (!enabled) {
      setActive(null);
      return;
    }
    const seen = new Map<string, boolean>();
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) seen.set(e.target.id, e.isIntersecting);
        setActive(SECTION_IDS.find((id) => seen.get(id)) ?? null);
      },
      { rootMargin: "-45% 0px -50% 0px" },
    );
    for (const id of SECTION_IDS) {
      const el = document.getElementById(id);
      if (el) io.observe(el);
    }
    return () => io.disconnect();
  }, [enabled]);
  return active;
}

export function Nav({ repo }: { repo: string | null }) {
  const pathname = usePathname() || "/";
  const isHome = pathname === "/";
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const headerRef = useRef<HTMLElement>(null);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const [mac, setMac] = useState(true);
  const reduce = useReducedMotion();
  const section = useActiveSection(isHome);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setMac(/Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent));
  }, []);

  // Close the mobile menu on navigation and on Escape. The path is compared while rendering: an
  // effect also ran once the page had hydrated, and undid a tap on the menu that landed before it.
  const [menuPath, setMenuPath] = useState(pathname);
  if (menuPath !== pathname) {
    setMenuPath(pathname);
    setOpen(false);
  }
  // Attached during commit, so that a search opened right after hydration finds it.
  useLayoutEffect(() => {
    const onSearch = () => setOpen(false);
    window.addEventListener(OPEN_PALETTE_EVENT, onSearch);
    return () => window.removeEventListener(OPEN_PALETTE_EVENT, onSearch);
  }, []);
  useEffect(() => {
    if (!open) return;
    const unlock = lockScroll();
    const header = headerRef.current;
    if (!header) return unlock;
    const background = Array.from(header.parentElement?.children ?? [])
      .filter((node): node is HTMLElement => node instanceof HTMLElement && node !== header)
      .map((node) => ({ node, inert: node.inert }));
    background.forEach(({ node }) => { node.inert = true; });
    const focusable = () => Array.from(header.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), [tabindex="0"]'))
      .filter((node) => node.getClientRects().length > 0);
    const first = header.querySelector<HTMLElement>('#mobile-menu a[href]');
    first?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); setOpen(false); }
      if (e.key !== "Tab") return;
      const nodes = focusable();
      const index = nodes.indexOf(document.activeElement as HTMLElement);
      if (index < 0 || e.shiftKey && index === 0 || !e.shiftKey && index === nodes.length - 1) {
        e.preventDefault();
        nodes[e.shiftKey ? nodes.length - 1 : 0]?.focus();
      }
    };
    const desktop = window.matchMedia('(min-width: 768px)');
    const onResize = () => { if (desktop.matches) setOpen(false); };
    desktop.addEventListener('change', onResize);
    window.addEventListener("keydown", onKey);
    return () => {
      unlock();
      background.forEach(({ node, inert }) => { node.inert = inert; });
      desktop.removeEventListener('change', onResize);
      window.removeEventListener("keydown", onKey);
      toggleRef.current?.focus();
    };
  }, [open]);

  const isActive = (l: (typeof LINKS)[number]) =>
    isHome ? section === l.section : Boolean(l.route && pathname.startsWith(l.route));

  const githubUrl = repo ? `https://github.com/${repo}` : "https://github.com";

  return (
    <header ref={headerRef} role={open ? "dialog" : undefined}
      aria-modal={open ? true : undefined} aria-label={open ? "Navigation menu" : undefined}
      className="fixed inset-x-0 top-0 z-50">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-[60] focus:rounded-lg focus:bg-claw-500 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-ink-950"
      >
        Skip to content
      </a>
      <div
        className={cn(
          "relative transition-[background-color,border-color,backdrop-filter] duration-500 ease-out",
          scrolled || open
            ? "border-b border-white/[0.06] bg-ink-950/75 backdrop-blur-xl"
            : "border-b border-transparent bg-transparent",
        )}
      >
        <nav className="container-site flex h-16 items-center justify-between gap-4" aria-label="Main">
          <Link href="/" className="group flex shrink-0 items-center rounded-xl" aria-label="nf-claw home">
            <Logo size={32} withText className="transition-transform duration-300 group-hover:scale-[1.02]" />
          </Link>

          <div className="hidden items-center gap-0.5 rounded-full border border-white/[0.06] bg-white/[0.02] p-1 md:flex">
            {LINKS.map((l) => {
              const active = isActive(l);
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  aria-current={active ? (l.route ? "page" : "location") : undefined}
                  className={cn(
                    "relative isolate rounded-full px-3.5 py-1.5 text-sm transition-colors duration-200",
                    active ? "text-fog" : "text-fog-muted hover:text-fog",
                  )}
                >
                  {active && (
                    <motion.span
                      layoutId="nav-pill"
                      className="absolute inset-0 -z-10 rounded-full border border-white/[0.08] bg-white/[0.07]"
                      transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 420, damping: 36 }}
                    />
                  )}
                  {l.label}
                </Link>
              );
            })}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={openPalette}
              className="group hidden h-9 items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] pl-3 pr-1.5 text-sm text-fog-dim transition hover:border-white/20 hover:text-fog sm:inline-flex"
              aria-keyshortcuts="Meta+K Control+K"
            >
              {/* Named by its visible text ("Search ⌘K"), so speech input can say what it shows;
                  the word stays readable to assistive technology where it is not shown. */}
              <Search className="h-3.5 w-3.5" />
              <span className="sr-only lg:not-sr-only">Search</span>
              <span className="kbd ml-1 h-6 px-2 group-hover:text-fog-muted">{mac ? "⌘K" : "Ctrl K"}</span>
            </button>
            <button
              onClick={openPalette}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] text-fog sm:hidden"
              aria-label="Search"
            >
              <Search className="h-4 w-4" />
            </button>
            <a
              href={githubUrl}
              target="_blank"
              rel="noreferrer"
              className="hidden h-9 items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-4 text-sm font-medium text-fog transition hover:border-claw-400/30 hover:bg-white/[0.06] md:inline-flex"
            >
              <Github className="h-4 w-4" />
              GitHub
            </a>
            <button
              onClick={() => setOpen((v) => !v)}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] text-fog md:hidden"
              ref={toggleRef}
              aria-label={open ? "Close menu" : "Open menu"}
              aria-expanded={open}
              aria-controls="mobile-menu"
            >
              <span className="relative h-5 w-5">
                <Menu
                  className={cn(
                    "absolute inset-0 h-5 w-5 transition-[transform,opacity] duration-200",
                    open ? "rotate-90 opacity-0" : "rotate-0 opacity-100",
                  )}
                />
                <X
                  className={cn(
                    "absolute inset-0 h-5 w-5 transition-[transform,opacity] duration-200",
                    open ? "rotate-0 opacity-100" : "-rotate-90 opacity-0",
                  )}
                />
              </span>
            </button>
          </div>
        </nav>

        {/* reading progress, chapter by chapter */}
        <ReadingProgress visible={scrolled && !open} />
      </div>

      {/* Shown/hidden with CSS rather than unmounted through an exit animation, which could leave an
          invisible layer over the page after a navigation in production builds. */}
      <div
        id="mobile-menu"
        className={cn(
          "fixed inset-x-0 bottom-0 top-16 overflow-y-auto bg-ink-950/95 backdrop-blur-xl md:hidden",
          open
            ? "visible opacity-100 [transition:opacity_200ms]"
            : "pointer-events-none invisible opacity-0 [transition:opacity_200ms,visibility_0s_linear_200ms]",
        )}
      >
        {open && (
          <motion.div
            className="container-site flex flex-col gap-1 py-6"
            initial="hidden"
            animate="show"
            variants={{ show: { transition: { staggerChildren: 0.04, delayChildren: 0.04 } } }}
          >
            {LINKS.map((l) => (
              <motion.div
                key={l.href}
                variants={{
                  hidden: reduce ? {} : { opacity: 0, x: -12 },
                  show: { opacity: 1, x: 0, transition: { duration: 0.35, ease: EASE } },
                }}
              >
                <Link
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className={cn(
                    "flex items-center justify-between rounded-2xl px-4 py-4 text-lg font-medium transition",
                    isActive(l) ? "bg-white/[0.05] text-fog" : "text-fog-muted hover:bg-white/5 hover:text-fog",
                  )}
                >
                  {l.label}
                  {isActive(l) && <span className="h-1.5 w-1.5 rounded-full bg-claw-400" />}
                </Link>
              </motion.div>
            ))}
            <motion.div
              className="mt-4 border-t border-white/[0.06] pt-4"
              variants={{ hidden: reduce ? {} : { opacity: 0 }, show: { opacity: 1 } }}
            >
              <a
                href={githubUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between rounded-2xl px-4 py-4 text-lg text-fog"
              >
                <span className="flex items-center gap-3">
                  <Github className="h-5 w-5" /> GitHub
                </span>
                <ArrowUpRight className="h-4 w-4 text-fog-dim" />
              </a>
            </motion.div>
          </motion.div>
        )}
      </div>
    </header>
  );
}
