import type { Pipeline } from "./types";

/**
 * The research domains a pipeline is grouped under, in a fixed order. Each is matched against the
 * pipeline's name + description (first match wins), so a new pipeline lands in a domain without any
 * per-pipeline hardcoding; one that matches nothing is "Other".
 *
 * The colors are a categorical palette validated for the site's dark surface (#0A0B0E): every
 * hue sits in the OKLCH lightness band 0.48–0.67, clears 3:1 contrast, and — in this order, wrapping
 * around as the constellation's wedges do — keeps adjacent pairs ≥ 13.9 ΔE apart under simulated
 * protan/deutan vision. Reordering the list re-pairs the neighbours; re-validate before changing it.
 */
export const CATEGORIES: { name: string; color: string; test: RegExp }[] = [
  {
    name: "Transcriptomics",
    color: "#3fac4a",
    test: /\brna|transcript|isoform|expression|splic|ribosom|isoseq|nanostring|differential abundance/,
  },
  {
    name: "Single-cell & spatial",
    color: "#2784d5",
    test: /single.?cell|scrna|\b10x\b|spatial|xenium|cartography|proximity network|mars-?seq|microscop|imag(e|ing)|light-?sheet|satellite/,
  },
  {
    name: "Variant calling",
    color: "#da534f",
    test: /variant|germline|somatic|mutation|rare disease|tumou?r|cancer|onco|phasing|imputation|panel of normals/,
  },
  {
    name: "Epigenomics",
    color: "#7d5cc7",
    test: /methyl|epigen|chip-?seq|atac|cut&run|cut&tag|chromosome conformation|\bhi-?c\b|hicar|run-on|calling cards/,
  },
  {
    name: "Proteomics & immunology",
    color: "#c38300",
    test: /\b(hla|mhc)|epitope|b and t cell|repertoire|immun|protein|peptide|amino acid|mass spectromet|metabolom/,
  },
  {
    name: "Microbial & metagenomics",
    color: "#04a19b",
    test: /metagenom|metatranscriptom|microbi|taxon|amplicon|\b16s\b|bacteri|viral|virus|pathogen|horizontal gene|coprolite/,
  },
  {
    name: "Genomes & evolution",
    color: "#979828",
    test: /assembl|genome|ortholog|phylogen|sequence align|crispr|circular dna|contig/,
  },
  {
    name: "Data & utilities",
    color: "#b94c90",
    test: /download|public database|synchroni|archive|demultiplex|\bbam|fastq|simulat|submit|\bdemo\b|\bqc\b|consensus|nanopore/,
  },
];

export const OTHER_CATEGORY = { name: "Other", color: "#6b7280" };

/** Every domain name in palette order, "Other" last. */
export const DOMAIN_ORDER = [...CATEGORIES.map((c) => c.name), OTHER_CATEGORY.name];

/** The domains `items` fall into, in palette order, with how many items each holds. */
export function domainCounts(items: { category: string }[]): { name: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const item of items) counts.set(item.category, (counts.get(item.category) ?? 0) + 1);
  return DOMAIN_ORDER.filter((name) => counts.has(name)).map((name) => ({ name, count: counts.get(name)! }));
}

/**
 * Matching order. A description often names more than one domain ("RNA and DNA … somatic mutation",
 * "metagenomes to peptides"), so the more specific domains are tried before the broad ones:
 * single-cell/microbial/variants before transcriptomics, data utilities ("submit sequences, assemblies")
 * before genomes.
 */
const RULES = [
  "Single-cell & spatial",
  "Microbial & metagenomics",
  "Variant calling",
  "Epigenomics",
  "Proteomics & immunology",
  "Transcriptomics",
  "Data & utilities",
  "Genomes & evolution",
].map((name) => CATEGORIES.find((c) => c.name === name)!);

const COLOR = new Map<string, string>([
  ...CATEGORIES.map((c) => [c.name, c.color] as [string, string]),
  [OTHER_CATEGORY.name, OTHER_CATEGORY.color],
]);

export function colorForCategory(cat: string): string {
  return COLOR.get(cat) ?? OTHER_CATEGORY.color;
}

/** Position of a domain in the fixed palette order ("Other" last). */
export function categoryRank(cat: string): number {
  const i = CATEGORIES.findIndex((c) => c.name === cat);
  return i === -1 ? CATEGORIES.length : i;
}

/** Derive a pipeline's research domain from its name + description. */
export function categorize(p: { name: string; description: string }): string {
  const t = `${p.name} ${p.description}`.toLowerCase();
  return RULES.find((c) => c.test.test(t))?.name ?? OTHER_CATEGORY.name;
}

/** A serialisable, lightweight summary passed to client components. */
export interface PipelineSummary {
  name: string;
  pipeline: string;
  version: string;
  description: string;
  category: string;
  tools: string[];
  parameterCount: number;
  groupCount: number;
  moduleCount: number;
  requiredCount: number;
  samplesheetCount: number;
  hasSamplesheet: boolean;
  releaseDate: string | null;
  policy: string;
  runCommand: string;
}

/** Compact parameter shape for the client-side skills/parameter explorer. */
export interface ParamLite {
  name: string;
  type: string;
  group: string;
  required: boolean;
  hidden: boolean;
  allowed: string[];
  constraints: string;
  default: string;
  description: string;
}

export interface SkillGroupLite {
  name: string;
  title: string;
  count: number;
}

/** A "skill" == one pipeline's generated skill.md (what an agent reads). */
export interface SkillSummary {
  name: string;
  pipeline: string;
  version: string;
  commit: string;
  description: string;
  category: string;
  runCommand: string;
  demoCommand: string | null;
  usageUrl: string | null;
  outputs: string;
  releaseDate: string | null;
  policy: string;
  parameterCount: number;
  moduleCount: number;
  samplesheetCount: number;
  hasSamplesheet: boolean;
  groups: SkillGroupLite[];
  required: { name: string; type: string; description: string }[];
  params: ParamLite[];
}

/**
 * A skill as the home page ships it: no parameters (they load on demand from /search/params.json),
 * group titles left to the client (humanize(name)) and a short commit.
 */
export type SkillCard = Omit<SkillSummary, "params" | "groups"> & { groups: { name: string; count: number }[] };

/** One parameter as the skills search shows it. */
export interface ParamHit {
  name: string;
  group: string;
  description: string;
}

/** pipeline name → [parameter, group, description] for every parameter (served as /search/params.json). */
export type ParamIndex = Record<string, [string, string, string][]>;

export function toSkillCard(p: Pipeline): SkillCard {
  const { params: _params, groups, commit, ...card } = toSkill(p);
  void _params;
  return { ...card, commit: commit.slice(0, 7), groups: groups.map(({ name, count }) => ({ name, count })) };
}

export function toSkill(p: Pipeline): SkillSummary {
  return {
    name: p.name,
    pipeline: p.pipeline,
    version: p.version,
    commit: p.commit,
    description: p.description,
    category: categorize(p),
    runCommand: p.runCommand,
    demoCommand: p.demoCommand,
    usageUrl: p.usageUrl,
    outputs: p.outputs,
    releaseDate: p.releaseDate,
    policy: p.policy,
    parameterCount: p.parameterCount,
    moduleCount: p.moduleCount,
    samplesheetCount: p.samplesheet.length,
    hasSamplesheet: p.hasSamplesheet,
    groups: p.groups.map((g) => ({
      name: g.name,
      title: g.title,
      count: g.parameters.length,
    })),
    required: p.requiredParams.map((r) => ({
      name: r.name,
      type: r.type,
      description: r.description,
    })),
    params: p.groups.flatMap((g) =>
      g.parameters.map((param) => ({
        name: param.name,
        type: param.type,
        group: g.name,
        required: param.required,
        hidden: param.hidden,
        allowed: param.allowed,
        constraints: param.constraints,
        default: param.default,
        description: param.description,
      })),
    ),
  };
}

export function toSummary(p: Pipeline): PipelineSummary {
  return {
    name: p.name,
    pipeline: p.pipeline,
    version: p.version,
    description: p.description,
    category: categorize(p),
    tools: p.tools,
    parameterCount: p.parameterCount,
    groupCount: p.groups.length,
    moduleCount: p.moduleCount,
    requiredCount: p.requiredParams.length,
    samplesheetCount: p.samplesheet.length,
    hasSamplesheet: p.hasSamplesheet,
    releaseDate: p.releaseDate,
    policy: p.policy,
    runCommand: p.runCommand,
  };
}
