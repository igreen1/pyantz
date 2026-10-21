/** Collect what is wrong with the jobs of a pipeline, level by level. */
import type { JSONSchema7 } from "json-schema";
import type { JobNode, Level, PathEntry } from "./graph.ts";
import { validateParameters } from "./validate.ts";

export type Schemas = Record<string, JSONSchema7>;

/** What is wrong with a job itself: its parameters, and its id. */
export const jobProblems = (
  node: JobNode,
  level: Level,
  schemas: Schemas,
): string[] => {
  const messages = validateParameters(
    schemas[node.data.job.function],
    node.data.job.parameters,
  ).map(
    (problem) => `${problem.path.slice(1) || "parameters"} ${problem.message}`,
  );

  const id = node.data.job.job_id;
  if (
    id !== undefined &&
    level.nodes.some((o) => o.id !== node.id && o.data.job.job_id === id)
  ) {
    messages.push(`job_id "${id}" is used by another job of this level`);
  }
  return messages;
};

/** How many problems a job has, counting the jobs inside it. */
export const countProblems = (
  node: JobNode,
  level: Level,
  schemas: Schemas,
): number =>
  jobProblems(node, level, schemas).length +
  Object.values(node.data.nested).reduce(
    (sum, inner) =>
      sum +
      inner.nodes.reduce(
        (innerSum, child) => innerSum + countProblems(child, inner, schemas),
        0,
      ),
    0,
  );

export interface ProblemEntry {
  path: PathEntry[];
  node: JobNode;
  messages: string[];
}

/** List the jobs which have problems in all levels, with the server's problems too. */
export const collectProblems = (
  root: Level,
  schemas: Schemas,
  fromServer: Record<string, string[]> = {},
): ProblemEntry[] => {
  const found: ProblemEntry[] = [];
  const visit = (level: Level, path: PathEntry[]) => {
    for (const node of level.nodes) {
      const messages = [
        ...jobProblems(node, level, schemas),
        ...(fromServer[node.id] ?? []),
      ];
      if (messages.length > 0) found.push({ path, node, messages });
      for (const [param, inner] of Object.entries(node.data.nested)) {
        visit(inner, [...path, { nodeId: node.id, param }]);
      }
    }
  };
  visit(root, []);
  return found;
};

/** A name to show for a job. */
export const jobLabel = (node: JobNode): string =>
  node.data.job.name || node.data.job.function.split(".").at(-1) || "job";
