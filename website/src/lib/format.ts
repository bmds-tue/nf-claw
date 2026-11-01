import { formatMonth } from "@/lib/utils";

/**
 * Humanize a 5-field cron expression for the common cases the repo uses. Only single values and
 * wildcards are worded; a field with a step, range or list (every 30 minutes, `1-5`, `1,3`) is
 * shown as written rather than as a wrong sentence.
 */
export function humanizeCron(cron: string | null): string | null {
  if (!cron) return null;
  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5 || !parts.every((f) => f === "*" || /^\d+$/.test(f))) return cron;
  const [min, hour, dom, mon, dow] = parts;
  if (min === "*") return parts.every((f) => f === "*") ? "Every minute" : cron;
  const minute = min.padStart(2, "0");
  const time = hour === "*" ? null : `${hour.padStart(2, "0")}:${minute} UTC`;
  if (dom === "*" && mon === "*" && dow === "*") {
    return time ? `Daily at ${time}` : `Hourly at :${minute}`;
  }
  if (dom === "*" && mon === "*" && time) {
    const day = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][Number(dow)];
    if (day) return `Weekly · ${day} ${time}`;
  }
  return time ? `Scheduled · ${time}` : cron;
}

export type CommitTone = "feat" | "fix" | "chore" | "docs" | "refactor" | "test" | "other";

export function commitTone(type: string | null): CommitTone {
  switch (type) {
    case "feat":
      return "feat";
    case "fix":
      return "fix";
    case "refactor":
    case "perf":
      return "refactor";
    case "docs":
      return "docs";
    case "test":
      return "test";
    case "chore":
    case "build":
    case "ci":
    case "style":
      return "chore";
    default:
      return "other";
  }
}

export const TONE_CLASS: Record<CommitTone, string> = {
  feat: "bg-claw-500/15 text-claw-300 border-claw-400/20",
  fix: "bg-cream/10 text-cream border-cream/20",
  refactor: "bg-white/[0.05] text-fog-muted border-white/10",
  docs: "bg-white/[0.04] text-fog-dim border-white/10",
  test: "bg-white/[0.04] text-fog-dim border-white/10",
  chore: "bg-white/[0.03] text-fog-dim border-white/10",
  other: "bg-white/[0.03] text-fog-dim border-white/10",
};

/**
 * Consecutive entries grouped by calendar month, in UTC as the labels are: a git date keeps its
 * committer's offset, so `2026-03-31T23:30:00-05:00` belongs to April 2026.
 */
export function groupByMonth<T extends { date: string | null }>(
  items: T[],
): { key: string; label: string; items: T[] }[] {
  const groups: { key: string; label: string; items: T[] }[] = [];
  for (const item of items) {
    const at = item.date ? new Date(item.date) : null;
    const key = at && !Number.isNaN(at.getTime()) ? at.toISOString().slice(0, 7) : "undated";
    const label = key === "undated" ? "Undated" : formatMonth(item.date);
    const last = groups[groups.length - 1];
    if (last && last.key === key) last.items.push(item);
    else groups.push({ key, label, items: [item] });
  }
  return groups;
}
