/**
 * Attach the problems which the api reports to the jobs they are about.
 *
 * The api reports the problems of the jobs as one message, which names the job when
 * it can (``Job 'a' depends on unknown job 'z'``). What can't be attached to a job is
 * returned as it is, to be shown for the pipeline as a whole.
 */
import type { JobNode, Level } from "./graph.ts";

export interface MappedErrors {
  byNode: Record<string, string[]>;
  unmapped: string[];
}

const allNodes = (level: Level): JobNode[] =>
  level.nodes.flatMap((node) => [
    node,
    ...Object.values(node.data.nested).flatMap(allNodes),
  ]);

const JOB_NAMED = /\bJob '([^']+)'/g;

export const mapServerErrors = (
  root: Level,
  errors: string[],
): MappedErrors => {
  const nodes = allNodes(root);
  const byNode: Record<string, string[]> = {};
  const unmapped: string[] = [];

  for (const error of errors) {
    // a message may list several problems, one per line
    for (const line of error.split("\n")) {
      const text = line.replace(/^-\s*/, "").trim();
      if (!text) continue;
      const named = [...text.matchAll(JOB_NAMED)].map((match) => match[1]);
      const matched = nodes.filter((node) =>
        named.includes(node.data.job.job_id ?? ""),
      );
      if (matched.length === 0) {
        unmapped.push(text);
      } else {
        for (const node of matched) {
          (byNode[node.id] ??= []).push(text);
        }
      }
    }
  }
  return { byNode, unmapped };
};
