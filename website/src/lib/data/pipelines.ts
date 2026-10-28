import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { repoPath, readText } from "./paths";
import {
  splitFrontmatter,
  sectionLines,
  tableUnder,
  parseTableAt,
  codeBlockUnder,
  codeBlocksUnder,
  proseUnder,
  splitAllowed,
  isYes,
  unticked,
} from "./markdown";
import { humanize } from "../utils";
import type {
  Pipeline,
  Parameter,
  ParameterGroup,
  SamplesheetColumn,
  SamplesheetHeader,
  RequiredParam,
} from "../types";

interface CatalogEntry {
  name: string;
  version: string;
  description: string;
  tools?: string[];
}

/** Catalog tool names come from upstream READMEs and can carry markup ("CADD<sup>1</sup>"). */
function cleanTools(tools: string[] | undefined): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of tools ?? []) {
    let t = raw.replace(/<sup>.*?<\/sup>/gi, "");
    // Until stable: removing one tag must not leave another assembled from its neighbours.
    for (let previous = ""; previous !== t; ) {
      previous = t;
      t = t.replace(/<[^>]+>/g, "");
    }
    t = t.replace(/\s+/g, " ").trim();
    if (t && !seen.has(t.toLowerCase())) {
      seen.add(t.toLowerCase());
      out.push(t);
    }
  }
  return out;
}

function readCatalog(): CatalogEntry[] {
  const raw = readText("catalog.json");
  if (!raw) return [];
  try {
    return JSON.parse(raw) as CatalogEntry[];
  } catch {
    return [];
  }
}

/** Parse sources.tsv into name -> { url, policy }. */
function readSources(): Record<string, { url: string; policy: string }> {
  const raw = readText("sources.tsv");
  const out: Record<string, { url: string; policy: string }> = {};
  if (!raw) return out;
  for (const line of raw.split("\n")) {
    if (!line.trim() || line.trim().startsWith("#")) continue;
    const [name, url, policy] = line.split("\t").map((s) => s.trim());
    if (name) out[name] = { url: url || "", policy: policy || "" };
  }
  return out;
}

/** Parse .gitmodules into pipeline-name -> url (fallback for sources.tsv). */
function readSubmoduleUrls(): Record<string, string> {
  const raw = readText(".gitmodules");
  const out: Record<string, string> = {};
  if (!raw) return out;
  const blocks = raw.split(/\[submodule/).slice(1);
  for (const block of blocks) {
    const pathM = block.match(/path\s*=\s*pipelines\/([^/]+)\/upstream/);
    const urlM = block.match(/url\s*=\s*(\S+)/);
    if (pathM && urlM) out[pathM[1]] = urlM[1];
  }
  return out;
}

/** Date of the pinned release commit inside an upstream submodule. */
function releaseDate(name: string, commit: string): string | null {
  if (!commit) return null;
  try {
    const out = execFileSync(
      "git",
      ["-C", repoPath("pipelines", name, "upstream"), "show", "-s", "--format=%cI", commit],
      { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] },
    ).trim();
    return out || null;
  } catch {
    return null;
  }
}

/** Count distinct nf-core modules vendored inside an upstream submodule. */
function moduleCount(name: string): number {
  const base = repoPath("pipelines", name, "upstream", "modules", "nf-core");
  if (!fs.existsSync(base)) return 0;
  let count = 0;
  const walk = (dir: string, depth: number) => {
    if (depth > 4) return;
    let entries: fs.Dirent[] = [];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    const hasMain = entries.some((e) => e.isFile() && e.name === "main.nf");
    if (hasMain) {
      count++;
      return;
    }
    for (const e of entries) {
      if (e.isDirectory()) walk(path.join(dir, e.name), depth + 1);
    }
  };
  walk(base, 0);
  return count;
}

function parseSamplesheet(skill: string): SamplesheetColumn[] {
  const table = tableUnder(skill, "Inputs");
  if (!table) return [];
  return table.rows.map((r) => ({
    column: unticked(r[0] ?? ""),
    type: r[1] ?? "",
    required: isYes(r[2] ?? ""),
    allowed: splitAllowed(r[3] ?? ""),
    constraints: r[4] ?? "",
  }));
}

/**
 * The samplesheet header(s) skill.md gives — its own fenced `csv`/`tsv` blocks under "Inputs", never
 * rebuilt here. The librarian decides what a valid header is (the required columns; one header per
 * mutually-exclusive column group; TAB-separated for a TSV), so joining every column with commas
 * produced a header that is wrong for TSV pipelines and invalid where column groups exclude each other.
 */
function parseSamplesheetHeaders(skill: string): SamplesheetHeader[] {
  return codeBlocksUnder(skill, "Inputs")
    .filter((b) => (b.lang === "csv" || b.lang === "tsv") && b.code.trim())
    .map((b) => ({ format: b.lang as SamplesheetHeader["format"], header: b.code.trim() }));
}

function parseRequired(skill: string): RequiredParam[] {
  const table = tableUnder(skill, "Required parameters");
  if (!table) return [];
  // The librarian emits six columns: parameter, type, default, allowed values,
  // constraints, description. This view intentionally omits `default` (column 2),
  // so the remaining fields start at column 3 — not column 2.
  return table.rows.map((r) => ({
    name: unticked(r[0] ?? ""),
    type: r[1] ?? "",
    allowed: splitAllowed(r[3] ?? ""),
    constraints: r[4] ?? "",
    description: r[5] ?? "",
  }));
}

/** Parse reference.md into parameter groups. Each "## group" holds one table. */
function parseReference(reference: string): ParameterGroup[] {
  const lines = reference.split("\n");
  const groups: ParameterGroup[] = [];
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(/^##\s+([a-z0-9_]+)\s*$/i);
    if (!m) continue;
    const groupName = m[1];
    const table = parseTableAt(lines, i + 1);
    if (!table) continue;
    const parameters: Parameter[] = table.rows.map((r) => ({
      name: unticked(r[0] ?? ""),
      type: r[1] ?? "",
      required: isYes(r[2] ?? ""),
      hidden: isYes(r[3] ?? ""),
      allowed: splitAllowed(r[4] ?? ""),
      constraints: r[5] ?? "",
      default: r[6] ?? "",
      description: r[7] ?? "",
      group: groupName,
    }));
    if (parameters.length) {
      groups.push({ name: groupName, title: humanize(groupName), parameters });
    }
  }
  return groups;
}

function extractUsageUrl(skill: string): string | null {
  const m = skill.match(/https?:\/\/\S+usage\.md/);
  return m ? m[0] : null;
}

/**
 * The commands skill.md's "Run it" block gives. They are generated per pipeline (its `--input`, its
 * required parameters), so none is invented here: a missing raw command is shown as absent, and the
 * nfclaw fallback names no input it cannot know.
 */
function runCommands(skill: string, name: string): { run: string; raw: string | null } {
  const block = codeBlockUnder(skill, "Run it") ?? "";
  const lines = block.split("\n").map((l) => l.trim());
  const run =
    lines.find((l) => l.startsWith("nfclaw run")) ?? `nfclaw run ${name} --outdir results -profile docker`;
  const raw = lines.find((l) => l.startsWith("nextflow run")) ?? null;
  return { run, raw };
}

function demoCommand(skill: string): string | null {
  const block = codeBlockUnder(skill, "Demo");
  if (!block) return null;
  const line = block.split("\n").find((l) => l.trim().startsWith("nfclaw"));
  return line ? line.trim() : null;
}

interface Handoff {
  from: string;
  to: string;
  description: string;
}

/** The chaining rules, `handoffs/<upstream>/<downstream>.json` — which pipeline can follow which. */
function readHandoffs(): Handoff[] {
  const root = repoPath("handoffs");
  if (!fs.existsSync(root)) return [];
  const out: Handoff[] = [];
  for (const up of fs.readdirSync(root).sort()) {
    const dir = path.join(root, up);
    if (!fs.statSync(dir).isDirectory()) continue;
    for (const file of fs.readdirSync(dir).sort()) {
      if (!file.endsWith(".json")) continue;
      try {
        const rule = JSON.parse(fs.readFileSync(path.join(dir, file), "utf8"));
        out.push({ from: up, to: file.slice(0, -".json".length), description: String(rule.description ?? "") });
      } catch {
        // a malformed rule is the drift gate's to report, not the website's
      }
    }
  }
  return out;
}

let cache: Pipeline[] | null = null;

export function getPipelines(): Pipeline[] {
  if (cache) return cache;
  const catalog = readCatalog();
  const sources = readSources();
  const submodules = readSubmoduleUrls();
  const handoffs = readHandoffs();

  const pipelines = catalog
    .map((entry): Pipeline | null => {
      const name = entry.name;
      const skillRaw = readText("pipelines", name, "skill.md");
      const referenceRaw = readText("pipelines", name, "reference.md");
      if (!skillRaw) return null;

      const { data: fm, content: skillBody } = splitFrontmatter(skillRaw);
      const reference = referenceRaw ? splitFrontmatter(referenceRaw).content : "";

      // Schema descriptions use links relative to upstream docs/usage.md.
      const sourceBase = `https://github.com/nf-core/${name}/blob/${String(fm.commit)}/docs/usage.md`;
      const linkedReference = reference.replace(/(\[[^\]]+\]\()([^\s)]+)(\))/g,
        (whole, prefix, href, suffix) => /^[a-z][a-z0-9+.-]*:|^[#/]/i.test(href)
          ? whole : `${prefix}${new URL(href, sourceBase).href}${suffix}`);
      const groups = parseReference(linkedReference);
      const parameterCount = groups.reduce((n, g) => n + g.parameters.length, 0);
      const commit = String(fm.commit ?? "");
      const { run, raw } = runCommands(skillBody, name);

      return {
        name,
        pipeline: String(fm.pipeline ?? `nf-core/${name}`),
        version: String(fm.version ?? entry.version ?? ""),
        commit,
        description: String(fm.description ?? entry.description ?? ""),
        tools: cleanTools(entry.tools),
        hasSamplesheet: Boolean(fm.has_samplesheet),
        url: sources[name]?.url || submodules[name] || `https://github.com/nf-core/${name}`,
        policy: sources[name]?.policy || "",
        runCommand: run,
        rawCommand: raw,
        demoCommand: demoCommand(skillBody),
        operatingGuidance: ["Runtime corrections", "Inputs", "Reference genome", "Reference database", "Secrets",
          "Resources", "Nextflow engine", "Demo"]
          .map((title) => ({ title, content: sectionLines(skillBody, title).join("\n").trim() }))
          .filter((section) => section.content),
        samplesheet: parseSamplesheet(skillBody),
        samplesheetHeaders: parseSamplesheetHeaders(skillBody),
        requiredParams: parseRequired(skillBody),
        groups,
        parameterCount,
        outputs: proseUnder(skillBody, "Outputs"),
        usageUrl: extractUsageUrl(skillBody),
        releaseDate: releaseDate(name, commit),
        moduleCount: moduleCount(name),
        feeds: handoffs
          .filter((h) => h.from === name)
          .map((h) => ({ pipeline: h.to, description: h.description })),
        fedBy: handoffs
          .filter((h) => h.to === name)
          .map((h) => ({ pipeline: h.from, description: h.description })),
      };
    })
    .filter((p): p is Pipeline => p !== null)
    .sort((a, b) => a.name.localeCompare(b.name));

  cache = pipelines;
  return pipelines;
}

export function getPipeline(name: string): Pipeline | undefined {
  return getPipelines().find((p) => p.name === name);
}

export function pipelineNames(): string[] {
  return getPipelines().map((p) => p.name);
}

/** All parameters across every pipeline, flattened for the global explorer. */
export function allParameters(): (Parameter & { pipeline: string })[] {
  const out: (Parameter & { pipeline: string })[] = [];
  for (const p of getPipelines()) {
    for (const g of p.groups) {
      for (const param of g.parameters) {
        out.push({ ...param, pipeline: p.name });
      }
    }
  }
  return out;
}
