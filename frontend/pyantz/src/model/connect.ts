/** Rules for which dependencies between the jobs of a level are allowed. */
import { MarkerType, type Edge } from "@xyflow/react";
import type { Level } from "./graph.ts";

export type ConnectionCheck = { ok: true } | { ok: false; reason: string };

/** Is there a way from `from` to `to` following the edges? */
const reaches = (edges: readonly Edge[], from: string, to: string): boolean => {
  const seen = new Set<string>();
  const pending = [from];
  while (pending.length > 0) {
    const current = pending.pop() as string;
    if (current === to) return true;
    if (seen.has(current)) continue;
    seen.add(current);
    for (const edge of edges) {
      if (edge.source === current) pending.push(edge.target);
    }
  }
  return false;
};

/** Check that `target` can be made to depend on `source` in this level. */
export const canConnect = (
  level: Level,
  source: string | null | undefined,
  target: string | null | undefined,
): ConnectionCheck => {
  const ids = new Set(level.nodes.map((node) => node.id));
  if (!source || !target || !ids.has(source) || !ids.has(target)) {
    return {
      ok: false,
      reason:
        "Jobs can only depend on jobs in the same pipeline level; open the " +
        "nested pipeline to connect its jobs.",
    };
  }
  if (source === target) {
    return { ok: false, reason: "A job can't depend on itself." };
  }
  if (level.edges.some((e) => e.source === source && e.target === target)) {
    return { ok: false, reason: "That dependency already exists." };
  }
  if (reaches(level.edges, target, source)) {
    return {
      ok: false,
      reason: "That would make the jobs depend on each other in a circle.",
    };
  }
  return { ok: true };
};

export const makeEdge = (source: string, target: string): Edge => ({
  id: `e${source}->${target}`,
  source,
  target,
  animated: true,
  markerEnd: { type: MarkerType.ArrowClosed },
});
