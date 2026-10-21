/**
 * The pipeline as it is edited: a graph of jobs per level.
 *
 * A job with parameters which are jobs themselves (loops, branches, ...) keeps
 * those in `nested`, each a graph of its own that the user drills into. Everything
 * else in a job's `parameters` stays as it is in the config. Dependencies are the
 * edges of a level, and are the only place they are stored.
 */
import type { Edge, Node } from "@xyflow/react";
import type { DependencyType } from "./types.ts";

/** A job parameter holding one job, or a list of jobs. */
export type NestedKind = "single" | "list";

export interface NestedGraph {
  kind: NestedKind;
  nodes: JobNode[];
  edges: Edge[];
}

/** The fields of a job which the user sets; unset ones are left out of exports. */
export interface JobFields {
  job_id?: string;
  name?: string | null;
  function: string;
  parameters: Record<string, unknown>;
  strict?: boolean;
  num_attempted_runs?: number;
  timeout_seconds?: number | null;
  max_retries?: number;
  dependency_type?: DependencyType;
  virtual?: boolean;
  // keys of the job which this app does not know about, kept so nothing is lost
  extra?: Record<string, unknown>;
}

export type JobNodeData = {
  job: JobFields;
  // parameter name -> the jobs in that parameter
  nested: Record<string, NestedGraph>;
  // `depends_on` entries which name no job of the level, kept so they are reported
  dangling?: string[];
};

export type JobNode = Node<JobNodeData, "jobNode">;

/** One level of the pipeline: the jobs next to each other, and their dependencies. */
export interface Level {
  nodes: JobNode[];
  edges: Edge[];
}

/** Settings of the whole pipeline, besides its jobs. */
export interface PipelineSettings {
  submitter: Record<string, unknown>;
  host?: Record<string, unknown>;
  variables?: Record<string, unknown>;
  // other top level keys of the config, kept as they were
  extra: Record<string, unknown>;
}

/** Which nested parameter of which job a level is the content of. */
export interface PathEntry {
  nodeId: string;
  param: string;
}

export const emptyLevel = (): Level => ({ nodes: [], edges: [] });

export const defaultPipeline = (): PipelineSettings => ({
  submitter: {
    type_: "local_proc",
    working_directory: "pyantz_work",
  },
  extra: {},
});

/** Get the level at the end of a path, or undefined if the path leads nowhere. */
export const levelAt = (
  root: Level,
  path: readonly PathEntry[],
): Level | undefined => {
  let level: Level = root;
  for (const { nodeId, param } of path) {
    const nested = level.nodes.find((node) => node.id === nodeId)?.data.nested[
      param
    ];
    if (!nested) return undefined;
    level = nested;
  }
  return level;
};

/**
 * Why no job can be added to the level at the end of a path, or null if one can.
 *
 * A parameter which holds one job (`if_true` of `if_else`, ...) takes just that
 * one: the config has nowhere to put a second.
 */
export const addJobBlock = (
  root: Level,
  path: readonly PathEntry[],
): string | null => {
  const last = path.at(-1);
  if (!last) return null;
  const level = levelAt(root, path);
  if (!(level && "kind" in level && level.kind === "single")) return null;
  return level.nodes.length > 0
    ? `${last.param} takes a single job. Delete the one there to add another.`
    : null;
};
