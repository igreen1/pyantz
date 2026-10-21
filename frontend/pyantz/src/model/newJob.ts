/** Make the node of a job which the user adds. */
import type { JSONSchema7 } from "json-schema";
import { classifyParams } from "./classify.ts";
import { newNodeId } from "./convert.ts";
import type { Level, JobNode, NestedGraph } from "./graph.ts";
import type { Position } from "./layout.ts";

export const shortName = (fn: string): string => fn.split(".").at(-1) ?? fn;

/** A name which no other job of the level has: `mkdir`, then `mkdir_2`, ... */
export const uniqueName = (level: Level, base: string): string => {
  const taken = new Set(level.nodes.map((node) => node.data.job.name));
  if (!taken.has(base)) return base;
  let number = 2;
  while (taken.has(`${base}_${number}`)) number += 1;
  return `${base}_${number}`;
};

interface NewJobOptions {
  fn: string;
  schema?: JSONSchema7;
  position: Position;
  // the level the job is added to, to pick a name which is free in it
  level: Level;
  makeId?: () => string;
}

export const createJobNode = ({
  fn,
  schema,
  position,
  level,
  makeId = newNodeId,
}: NewJobOptions): JobNode => {
  const kinds = classifyParams(schema);
  const required = schema?.required ?? [];

  // required parameters are there to be filled in
  const parameters = Object.fromEntries(
    required.filter((name) => !(name in kinds)).map((name) => [name, null]),
  );
  const nested: Record<string, NestedGraph> = Object.fromEntries(
    required
      .filter((name) => name in kinds)
      .map((name) => [name, { kind: kinds[name], nodes: [], edges: [] }]),
  );

  return {
    id: makeId(),
    type: "jobNode",
    position,
    data: {
      job: {
        job_id: makeId(),
        name: uniqueName(level, shortName(fn)),
        function: fn,
        parameters,
      },
      nested,
    },
  };
};
