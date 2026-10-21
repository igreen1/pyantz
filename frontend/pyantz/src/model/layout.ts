/** Place the jobs of a level in rows by how far they are from the start. */
import type { Edge } from "@xyflow/react";

export const NODE_WIDTH = 220;
export const NODE_HEIGHT = 90;
const GAP_X = 60;
const GAP_Y = 70;

export interface Position {
  x: number;
  y: number;
}

/**
 * Get a position for each node id: a node sits one row below the lowest node it
 * depends on, and the nodes of a row are side by side in the given order.
 * Cycles don't hang this; the edge which closes a cycle is ignored.
 */
export const layoutPositions = (
  nodeIds: readonly string[],
  edges: readonly Pick<Edge, "source" | "target">[],
): Map<string, Position> => {
  const known = new Set(nodeIds);
  const dependencies = new Map<string, string[]>();
  for (const { source, target } of edges) {
    if (known.has(source) && known.has(target) && source !== target) {
      dependencies.set(target, [...(dependencies.get(target) ?? []), source]);
    }
  }

  const rows = new Map<string, number>();
  const visiting = new Set<string>();
  const rowOf = (id: string): number => {
    const known_row = rows.get(id);
    if (known_row !== undefined) return known_row;
    if (visiting.has(id)) return 0;
    visiting.add(id);
    const row = Math.max(
      -1,
      ...(dependencies.get(id) ?? []).map((dep) => rowOf(dep)),
    );
    visiting.delete(id);
    rows.set(id, row + 1);
    return row + 1;
  };

  const used = new Map<number, number>();
  const positions = new Map<string, Position>();
  for (const id of nodeIds) {
    const row = rowOf(id);
    const column = used.get(row) ?? 0;
    used.set(row, column + 1);
    positions.set(id, {
      x: column * (NODE_WIDTH + GAP_X),
      y: row * (NODE_HEIGHT + GAP_Y),
    });
  }
  return positions;
};
