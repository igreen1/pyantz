/**
 * Convert between a config (what `pyantz` runs) and the graph which is edited.
 *
 * Both directions are lossless: keys this app does not know about are kept, and
 * `graphToConfig(configToGraph(config))` gives the config back (the order of
 * `depends_on` aside, which is not kept). Only imports of types from libraries are
 * allowed here, so that node can run this file directly.
 */
import type { Edge } from "@xyflow/react";
import type {
  JobFields,
  JobNode,
  JobNodeData,
  Level,
  NestedGraph,
  NestedKind,
  PipelineSettings,
} from "./graph.ts";
import { layoutPositions, type Position } from "./layout.ts";
import type { InitialConfig, JobConfig } from "./types.ts";

/** Key of the config where the positions of the jobs are saved. */
export const UI_KEY = "x-pyantz-ui";

type Raw = Record<string, unknown>;

/** Which parameters of a job are jobs, given its function; see `classifyParams`. */
export type NestedKindsFn = (fn: string) => Record<string, NestedKind>;

export class ConfigImportError extends Error {
  readonly problems: string[];

  constructor(problems: string[]) {
    super(`Can't open this config: ${problems.join("; ")}`);
    this.name = "ConfigImportError";
    this.problems = problems;
  }
}

const isRaw = (value: unknown): value is Raw =>
  typeof value === "object" && value !== null && !Array.isArray(value);

let counter = 0;
export const newNodeId = (): string =>
  globalThis.crypto?.randomUUID?.() ?? `node-${(counter += 1)}`;

const KNOWN_JOB_KEYS = new Set([
  "job_id",
  "depends_on",
  "parameters",
  "strict",
  "name",
  "function",
  "num_attempted_runs",
  "timeout_seconds",
  "max_retries",
  "dependency_type",
  "virtual",
]);

const KNOWN_FIELDS_WITH_VALUES = [
  "job_id",
  "name",
  "strict",
  "num_attempted_runs",
  "timeout_seconds",
  "max_retries",
  "dependency_type",
  "virtual",
] as const;

const edgeBetween = (source: string, target: string): Edge => ({
  id: `e${source}->${target}`,
  source,
  target,
  animated: true,
  markerEnd: { type: "arrowclosed" } as Edge["markerEnd"],
});

interface ImportContext {
  nestedKinds: NestedKindsFn;
  makeId: () => string;
  positions: Record<string, Position>;
  problems: string[];
}

const toJobs = (value: unknown, where: string, ctx: ImportContext): Raw[] => {
  if (!Array.isArray(value)) {
    ctx.problems.push(`${where} must be a list of jobs`);
    return [];
  }
  const jobs: Raw[] = [];
  value.forEach((item, index) => {
    if (!isRaw(item)) {
      ctx.problems.push(`${where}.${index} must be an object`);
    } else if (typeof item.function !== "string") {
      ctx.problems.push(`${where}.${index} has no "function"`);
    } else if (item.parameters !== undefined && !isRaw(item.parameters)) {
      ctx.problems.push(`${where}.${index}.parameters must be an object`);
    } else {
      jobs.push(item);
    }
  });
  return jobs;
};

/** Make the nodes and edges of a list of jobs; `where` is its path in the config. */
const jobsToLevel = (
  rawJobs: Raw[],
  where: string,
  ctx: ImportContext,
): Level => {
  const nodes: JobNode[] = rawJobs.map((raw, index) =>
    toNode(raw, `${where}.${index}`, ctx),
  );

  const idToNode = new Map<string, JobNode>();
  nodes.forEach((node) => {
    const jobId = node.data.job.job_id;
    if (jobId !== undefined && !idToNode.has(jobId)) idToNode.set(jobId, node);
  });

  const edges: Edge[] = [];
  rawJobs.forEach((raw, index) => {
    const target = nodes[index];
    const dependsOn = Array.isArray(raw.depends_on) ? raw.depends_on : [];
    for (const dependency of dependsOn) {
      const source = idToNode.get(String(dependency));
      if (source === undefined) {
        target.data.dangling = [
          ...(target.data.dangling ?? []),
          String(dependency),
        ];
      } else {
        edges.push(edgeBetween(source.id, target.id));
      }
    }
  });

  const auto = layoutPositions(
    nodes.map((node) => node.id),
    edges,
  );
  nodes.forEach((node, index) => {
    node.position = ctx.positions[`${where}.${index}`] ??
      auto.get(node.id) ?? { x: 0, y: 0 };
  });
  return { nodes, edges };
};

const toNode = (raw: Raw, where: string, ctx: ImportContext): JobNode => {
  const fn = raw.function as string;
  const kinds = ctx.nestedKinds(fn);
  const parameters: Raw = {};
  const nested: Record<string, NestedGraph> = {};

  for (const [param, value] of Object.entries((raw.parameters as Raw) ?? {})) {
    const kind = kinds[param];
    if (kind === "list" && Array.isArray(value)) {
      nested[param] = {
        kind,
        ...jobsToLevel(
          toJobs(value, `${where}.parameters.${param}`, ctx),
          `${where}.parameters.${param}`,
          ctx,
        ),
      };
    } else if (kind === "single" && isRaw(value)) {
      const jobs = toJobs([value], `${where}.parameters.${param}`, ctx);
      nested[param] = {
        kind,
        ...jobsToLevel(jobs, `${where}.parameters.${param}`, ctx),
      };
    } else {
      // not a job in the shape expected: left as it is, to be checked by the backend
      parameters[param] = value;
    }
  }

  const job: JobFields = { function: fn, parameters };
  for (const key of KNOWN_FIELDS_WITH_VALUES) {
    if (key in raw) (job as unknown as Raw)[key] = raw[key];
  }
  const extra = Object.fromEntries(
    Object.entries(raw).filter(([key]) => !KNOWN_JOB_KEYS.has(key)),
  );
  if (Object.keys(extra).length > 0) job.extra = extra;

  return {
    id: ctx.makeId(),
    type: "jobNode",
    position: { x: 0, y: 0 },
    data: { job, nested },
  };
};

export interface ImportedPipeline {
  level: Level;
  pipeline: PipelineSettings;
}

/**
 * Make the graph of a config.
 *
 * @throws ConfigImportError if it isn't shaped like a config
 */
export const configToGraph = (
  config: unknown,
  nestedKinds: NestedKindsFn = () => ({}),
  makeId: () => string = newNodeId,
): ImportedPipeline => {
  if (!isRaw(config)) {
    throw new ConfigImportError(["the config must be a json object"]);
  }
  const problems: string[] = [];
  if (config.submitter !== undefined && !isRaw(config.submitter)) {
    problems.push("submitter must be an object");
  }
  if (config.variables !== undefined && !isRaw(config.variables)) {
    problems.push("variables must be an object");
  }
  if (config.host !== undefined && !isRaw(config.host)) {
    problems.push("host must be an object");
  }
  const ui = config[UI_KEY];
  const positions =
    isRaw(ui) && isRaw(ui.positions)
      ? (ui.positions as Record<string, Position>)
      : {};

  const ctx: ImportContext = { nestedKinds, makeId, positions, problems };
  const level = jobsToLevel(toJobs(config.jobs, "jobs", ctx), "jobs", ctx);
  if (problems.length > 0) throw new ConfigImportError(problems);

  const known = new Set(["jobs", "submitter", "variables", "host", UI_KEY]);
  const pipeline: PipelineSettings = {
    submitter: (config.submitter as Raw | undefined) ?? {},
    extra: Object.fromEntries(
      Object.entries(config).filter(([key]) => !known.has(key)),
    ),
  };
  if (config.host !== undefined) pipeline.host = config.host as Raw;
  if (config.variables !== undefined)
    pipeline.variables = config.variables as Raw;
  return { level, pipeline };
};

export interface ExportOptions {
  // also write where the jobs are on the board, under `UI_KEY`
  includeLayout?: boolean;
}

/** Make the config of a graph. */
export const graphToConfig = (
  level: Level,
  pipeline: PipelineSettings,
  options: ExportOptions = {},
): InitialConfig & Raw => {
  const positions: Record<string, Position> = {};
  const track = options.includeLayout
    ? (path: string, node: JobNode) => {
        positions[path] = {
          x: Math.round(node.position.x),
          y: Math.round(node.position.y),
        };
      }
    : () => undefined;

  const jobs = levelToJobs(level, "jobs", track);
  const config: Raw = {
    ...pipeline.extra,
    jobs,
    submitter: pipeline.submitter,
  };
  if (pipeline.variables !== undefined) config.variables = pipeline.variables;
  if (pipeline.host !== undefined) config.host = pipeline.host;
  if (options.includeLayout) config[UI_KEY] = { positions };
  return config as unknown as InitialConfig & Raw;
};

type Track = (path: string, node: JobNode) => void;

const levelToJobs = (
  level: Level,
  where: string,
  track: Track,
): JobConfig[] => {
  // jobs which others depend on need an id to be named by
  const idOf = (node: JobNode): string | undefined => {
    if (node.data.job.job_id !== undefined) return node.data.job.job_id;
    return level.edges.some((e) => e.source === node.id || e.target === node.id)
      ? node.id
      : undefined;
  };
  const ids = new Map(level.nodes.map((node) => [node.id, idOf(node)]));

  return level.nodes.map((node, index) => {
    const path = `${where}.${index}`;
    track(path, node);
    const dependsOn = level.edges
      .filter((edge) => edge.target === node.id)
      .map((edge) => ids.get(edge.source))
      .filter((id): id is string => id !== undefined);
    dependsOn.push(...(node.data.dangling ?? []));
    return nodeToJob(node, ids.get(node.id), dependsOn.sort(), path, track);
  });
};

const nodeToJob = (
  node: JobNode,
  jobId: string | undefined,
  dependsOn: string[],
  path: string,
  track: Track,
): JobConfig => {
  const { job, nested } = node.data;
  const parameters: Raw = { ...job.parameters };

  for (const [param, graph] of Object.entries(nested)) {
    const nestedPath = `${path}.parameters.${param}`;
    if (graph.kind === "list") {
      parameters[param] = levelToJobs(graph, nestedPath, track);
    } else if (graph.nodes.length > 0) {
      parameters[param] = levelToJobs(graph, nestedPath, track)[0];
    }
  }

  const out: Raw = { ...job.extra };
  for (const key of KNOWN_FIELDS_WITH_VALUES) {
    if (job[key] !== undefined) out[key] = job[key];
  }
  if (jobId !== undefined) out.job_id = jobId;
  out.function = job.function;
  out.parameters = parameters;
  if (dependsOn.length > 0) out.depends_on = dependsOn;
  return out as unknown as JobConfig;
};

/** Bring configs to a form which can be compared: `depends_on` sorted, none if empty. */
export const normalizeConfig = (config: unknown): unknown => {
  if (Array.isArray(config)) return config.map(normalizeConfig);
  if (!isRaw(config)) return config;
  const out: Raw = {};
  for (const [key, value] of Object.entries(config)) {
    if (key === "depends_on" && Array.isArray(value)) {
      if (value.length > 0) out[key] = [...(value as string[])].sort();
    } else {
      out[key] = normalizeConfig(value);
    }
  }
  return out;
};

export type { JobNodeData };
