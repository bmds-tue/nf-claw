import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { BASE_PATH } from "@/lib/site";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Prefix a path to a file in `public/` with the configured base path so assets
 * resolve under project-site hosting (e.g. GitHub Pages "/<repo>"). `next/image`
 * does not add the base path to unoptimized image sources, so do it here.
 */
export function asset(path: string): string {
  return `${BASE_PATH}${path}`;
}

/**
 * Whether a link target may be rendered as a link: relative, or a web or mail URL — the protocols
 * react-markdown's default URL transform keeps.
 */
export function safeHref(href: string): boolean {
  const scheme = href.match(/^([a-z][a-z0-9+.-]*):/i);
  return !scheme || /^(https?|mailto)$/i.test(scheme[1]);
}

/** Title-case a snake_case or kebab-case identifier. */
export function humanize(id: string): string {
  return id
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bOptions\b/, "options")
    .replace(/^./, (c) => c.toUpperCase());
}

// Dates are formatted in UTC: the build machine and the reader's browser are in different zones,
// and a date rendered on both sides must read the same or hydration breaks.

/** Format an ISO date string as e.g. "Jun 2026". */
export function formatMonth(date: string | null): string {
  if (!date) return "";
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-US", { month: "long", year: "numeric", timeZone: "UTC" });
}

/** Format an ISO date string as e.g. "17 Jun 2026". */
export function formatDate(date: string | null): string {
  if (!date) return "";
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

/** Relative "time ago" string, measured from `now` (default: the current time). */
export function timeAgo(date: string | null, now: number = Date.now()): string {
  if (!date) return "";
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return "";
  const seconds = Math.floor((now - d.getTime()) / 1000);
  const units: [number, string][] = [
    [31536000, "y"],
    [2592000, "mo"],
    [604800, "w"],
    [86400, "d"],
    [3600, "h"],
    [60, "m"],
  ];
  for (const [secs, label] of units) {
    const v = Math.floor(seconds / secs);
    if (v >= 1) return `${v}${label} ago`;
  }
  return "just now";
}

/** Strip the quotes some git configs wrap a name in (user.name = "“jane”"). */
export function cleanAuthor(name: string): string {
  return name.replace(/^["'“”‘’\s]+|["'“”‘’\s]+$/g, "");
}

/** Split `text` around case-insensitive matches of `query`, for highlighting. */
export function splitMatch(text: string, query: string): { text: string; hit: boolean }[] {
  const q = query.trim();
  if (!q) return [{ text, hit: false }];
  const lower = text.toLowerCase();
  const needle = q.toLowerCase();
  const out: { text: string; hit: boolean }[] = [];
  let i = 0;
  while (i < text.length) {
    const at = lower.indexOf(needle, i);
    if (at === -1) {
      out.push({ text: text.slice(i), hit: false });
      break;
    }
    if (at > i) out.push({ text: text.slice(i, at), hit: false });
    out.push({ text: text.slice(at, at + needle.length), hit: true });
    i = at + needle.length;
  }
  return out;
}
