// Geometry for the pipeline constellation: every domain gets a wedge of the disc sized to its
// pipeline count, and its pipelines fill that wedge in rings from the rim inward. The layout always
// fits the view box — however many pipelines there are, the ring spacing shrinks to fit — and it is
// fully deterministic (no randomness, rounded coordinates), so server and client render the same SVG.

export interface Node {
  name: string;
  category: string;
  x: number;
  y: number;
  r: number;
  angle: number;
}

/**
 * A wedge's tag, outside the rim: a dot on the wedge's bisector, a short leader from the rim to it,
 * and the domain name with its pipeline count beside the dot (to the side for wedges on the left or
 * right, above or below for wedges at the top or bottom).
 */
export interface WedgeLabel {
  name: string;
  sub: string;
  dot: { x: number; y: number };
  leader: { x1: number; y1: number; x2: number; y2: number };
  anchor: "start" | "middle" | "end";
  nameAt: { x: number; y: number };
  subAt: { x: number; y: number };
}

export interface Wedge {
  category: string;
  start: number;
  end: number;
  count: number;
  label: WedgeLabel;
  path: string;
}

export interface Constellation {
  width: number;
  height: number;
  cx: number;
  cy: number;
  rInner: number;
  rOuter: number;
  /** Horizontal stretch of the disc (1: a true circle). */
  sx: number;
  nodes: Node[];
  wedges: Wedge[];
}

const round = (v: number) => Math.round(v * 100) / 100;

/** A tiny stable hash → [0, 1), used for gentle per-node jitter that is identical on every render. */
function unit(seed: string): number {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 10000) / 10000;
}

/** Node radius from the parameter count: area grows with the count, within a legible range. */
function nodeRadius(parameterCount: number): number {
  return round(Math.min(10, Math.max(4.5, 3 + Math.sqrt(Math.max(0, parameterCount)) * 0.5)));
}

// Radial distances beyond the outermost ring (rOuter). Outer nodes reach rOuter + 13 at most
// (radius ≤ 10, jitter ≤ 3), the wedge's tint ends at RIM, and the tag sits clear of it.
const RIM = 16;
const LEADER_FROM = RIM + 4;
const LEADER_TO = 32;
const DOT = 38;
const TEXT_GAP = 10;
// Rough advance widths of the tag text (13.5 px name, 11.5 px count) — enough to keep tags in view.
const NAME_CHAR = 7.4;
const SUB_CHAR = 6.3;
const TAG_HEIGHT = 42; // a stacked tag: name, count and the gap to the dot

export function layoutConstellation(
  items: { name: string; category: string; parameterCount: number }[],
  categoryOrder: string[],
  { width = 760, height = 640, labelName = (category: string) => category } = {},
): Constellation {
  const cx = width / 2;
  const cy = height / 2;
  const rInner = 64;
  const sx = 1;

  const groups = categoryOrder
    .map((category) => ({
      category,
      items: items.filter((i) => i.category === category).sort((a, b) => a.name.localeCompare(b.name)),
    }))
    .filter((g) => g.items.length);
  const total = groups.reduce((n, g) => n + g.items.length, 0) || 1;

  // Wedge angles depend only on the counts.
  const gap = groups.length > 1 ? 0.07 : 0;
  const usable = Math.PI * 2 - gap * groups.length;
  let angle = -Math.PI / 2 + gap / 2;
  const spans = groups.map((g) => {
    const start = angle;
    const end = angle + (usable * g.items.length) / total;
    angle = end + gap;
    const name = labelName(g.category);
    const sub = `${g.items.length} pipeline${g.items.length === 1 ? "" : "s"}`;
    return { g, start, end, mid: (start + end) / 2, name, sub };
  });

  // The largest disc whose every tag still fits in the view box.
  let rOuter = cy - 60;
  for (const { mid, name, sub } of spans) {
    const cos = Math.abs(Math.cos(mid));
    const sin = Math.abs(Math.sin(mid));
    if (isSide(mid)) {
      const w = Math.max(name.length * NAME_CHAR, sub.length * SUB_CHAR);
      rOuter = Math.min(rOuter, (cx - 8 - TEXT_GAP - w) / cos - DOT);
    } else {
      rOuter = Math.min(rOuter, (cy - 8 - TAG_HEIGHT) / sin - DOT);
    }
  }
  rOuter = Math.max(150, Math.floor(rOuter));

  const nodes: Node[] = [];
  const wedges: Wedge[] = [];
  // Closest two node centres may sit along a ring (arc length) and between rings (radius).
  const minArc = 26;
  const rMin = rInner + 34;

  for (const { g, start, end, mid, name, sub } of spans) {
    const span = end - start;

    // The fewest rings that hold the wedge's pipelines, then spread across the radius (up to 54
    // apart) instead of packed at the rim, so the disc fills evenly instead of leaving a void
    // around the hub. Each ring takes a share of the nodes proportional to its circumference.
    const n = g.items.length;
    const capacity = (r: number) => Math.max(1, Math.floor((span * r) / minArc));
    let rings: { r: number; count: number }[] = [];
    for (let count = 1; count <= 12; count++) {
      const step = count === 1 ? 0 : Math.min(54, (rOuter - rMin) / (count - 1));
      const radii = Array.from({ length: count }, (_, i) => rOuter - i * step);
      const caps = radii.map(capacity);
      if (caps.reduce((a, b) => a + b, 0) < n && count < 12) continue;
      const weight = radii.reduce((a, b) => a + b, 0);
      const counts = radii.map((r, i) => Math.min(caps[i], Math.floor((n * r) / weight)));
      // hand out what rounding left over, outer rings first
      for (let left = n - counts.reduce((a, b) => a + b, 0), i = 0; left > 0; i = (i + 1) % count) {
        if (counts[i] < caps[i] || i === count - 1) {
          counts[i] += 1;
          left -= 1;
        }
      }
      rings = radii.map((r, i) => ({ r, count: counts[i] })).filter((ring) => ring.count > 0);
      break;
    }

    let k = 0;
    for (const ring of rings) {
      for (let j = 0; j < ring.count; j++) {
        const item = g.items[k++];
        const jitterA = (unit(item.name) - 0.5) * Math.min(0.06, span / (ring.count + 1) / 3);
        const jitterR = (unit(item.name + "r") - 0.5) * 6;
        const a = start + ((j + 0.5) / ring.count) * span + jitterA;
        const r = ring.r + jitterR;
        nodes.push({
          name: item.name,
          category: g.category,
          x: round(cx + r * Math.cos(a)),
          y: round(cy + r * Math.sin(a)),
          r: nodeRadius(item.parameterCount),
          angle: round(a),
        });
      }
    }

    wedges.push({
      category: g.category,
      start: round(start),
      end: round(end),
      count: n,
      label: tag(cx, cy, rOuter, mid, name, sub),
      path: wedgePath(cx, cy, rInner, rOuter + RIM, start, end, sx),
    });
  }

  return { width, height, cx, cy, rInner, rOuter, sx, nodes, wedges };
}

/** Tags of wedges facing left or right sit beside their dot; the rest above or below it. */
function isSide(mid: number): boolean {
  return Math.abs(Math.cos(mid)) >= 0.4;
}

function tag(cx: number, cy: number, rOuter: number, mid: number, name: string, sub: string): WedgeLabel {
  const cos = Math.cos(mid);
  const sin = Math.sin(mid);
  const at = (d: number) => ({ x: round(cx + (rOuter + d) * cos), y: round(cy + (rOuter + d) * sin) });
  const dot = at(DOT);
  const from = at(LEADER_FROM);
  const to = at(LEADER_TO);
  const leader = { x1: from.x, y1: from.y, x2: to.x, y2: to.y };
  if (isSide(mid)) {
    const right = cos > 0;
    const x = round(dot.x + (right ? TEXT_GAP : -TEXT_GAP));
    return {
      name,
      sub,
      dot,
      leader,
      anchor: right ? "start" : "end",
      nameAt: { x, y: round(dot.y + 4.5) },
      subAt: { x, y: round(dot.y + 20) },
    };
  }
  const below = sin > 0;
  return {
    name,
    sub,
    dot,
    leader,
    anchor: "middle",
    nameAt: { x: dot.x, y: round(below ? dot.y + 23 : dot.y - 27) },
    subAt: { x: dot.x, y: round(below ? dot.y + 38 : dot.y - 12) },
  };
}

/** An annular sector, stretched by `sx` horizontally (drawn as polylines so the stretch stays exact). */
function wedgePath(cx: number, cy: number, r0: number, r1: number, a0: number, a1: number, sx: number): string {
  const steps = Math.max(4, Math.ceil(((a1 - a0) / (Math.PI * 2)) * 72));
  const pt = (r: number, a: number) => `${round(cx + r * Math.cos(a) * sx)} ${round(cy + r * Math.sin(a))}`;
  const outer: string[] = [];
  const inner: string[] = [];
  for (let i = 0; i <= steps; i++) {
    const a = a0 + ((a1 - a0) * i) / steps;
    outer.push(pt(r1, a));
    inner.push(pt(r0, a1 - ((a1 - a0) * i) / steps));
  }
  return `M ${outer.join(" L ")} L ${inner.join(" L ")} Z`;
}
