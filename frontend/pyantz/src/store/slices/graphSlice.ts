/**
 * The pipeline being edited: its jobs (one level at a time, with the nested levels
 * inside the jobs), its settings, and the history for undo and redo.
 */

import { createSlice, current, type PayloadAction } from "@reduxjs/toolkit";
import {
  applyEdgeChanges,
  applyNodeChanges,
  type Edge,
  type EdgeChange,
  type NodeChange,
} from "@xyflow/react";
import { canConnect, makeEdge } from "../../model/connect";
import {
  addJobBlock,
  defaultPipeline,
  emptyLevel,
  levelAt,
  type JobFields,
  type JobNode,
  type Level,
  type NestedKind,
  type PathEntry,
  type PipelineSettings,
} from "../../model/graph";

interface HistoryEntry {
  root: Level;
  // only kept for entries which replace the whole pipeline (opening a config)
  pipeline?: PipelineSettings;
}

export interface GraphState {
  root: Level;
  pipeline: PipelineSettings;
  // the nested levels which are open, outermost first; empty for the root
  path: PathEntry[];
  // counts up when a whole pipeline is loaded, so that the board starts afresh
  generation: number;
  past: HistoryEntry[];
  future: HistoryEntry[];
  // edits with the same key as the last one share a history entry
  lastEditKey: string | null;
}

const MAX_HISTORY = 100;

const initialState: GraphState = {
  root: emptyLevel(),
  pipeline: defaultPipeline(),
  path: [],
  generation: 0,
  past: [],
  future: [],
  lastEditKey: null,
};

type Draft = GraphState;

/** The level which is open. */
const openLevel = (state: Draft): Level =>
  levelAt(state.root, state.path) ?? state.root;

const remember = (state: Draft, withPipeline = false) => {
  state.past.push({
    root: current(state.root),
    pipeline: withPipeline ? current(state.pipeline) : undefined,
  });
  if (state.past.length > MAX_HISTORY) state.past.shift();
  state.future = [];
  state.lastEditKey = null;
};

const dropDanglingEdges = (level: Level) => {
  const ids = new Set(level.nodes.map((node) => node.id));
  level.edges = level.edges.filter(
    (edge) => ids.has(edge.source) && ids.has(edge.target),
  );
};

/** After undo and redo the open level may be gone. */
const closeMissingLevels = (state: Draft) => {
  while (state.path.length > 0 && !levelAt(state.root, state.path)) {
    state.path.pop();
  }
};

export const graphSlice = createSlice({
  name: "graph",
  initialState,
  reducers: {
    /** Replace the pipeline, e.g. by an opened config; `level` is the root. */
    loadPipeline: (
      state,
      action: PayloadAction<{ level: Level; pipeline: PipelineSettings }>,
    ) => {
      remember(state, true);
      state.root = action.payload.level;
      state.pipeline = action.payload.pipeline;
      state.path = [];
      state.generation += 1;
    },
    addNode: (state, action: PayloadAction<JobNode>) => {
      if (addJobBlock(state.root, state.path)) return;
      remember(state);
      const level = openLevel(state);
      level.nodes.forEach((node) => {
        node.selected = false;
      });
      level.nodes.push({ ...action.payload, selected: true });
    },
    /** Select one job of the open level, or none. */
    selectNode: (state, action: PayloadAction<string | null>) => {
      openLevel(state).nodes.forEach((node) => {
        node.selected = node.id === action.payload;
      });
    },
    /** Open the level of a job, however deep, and select the job. */
    openNode: (
      state,
      action: PayloadAction<{ path: PathEntry[]; nodeId: string }>,
    ) => {
      state.path = action.payload.path;
      openLevel(state).nodes.forEach((node) => {
        node.selected = node.id === action.payload.nodeId;
      });
    },
    /** Make `target` depend on `source`, if that is allowed. */
    connectNodes: (
      state,
      action: PayloadAction<{ source: string; target: string }>,
    ) => {
      const { source, target } = action.payload;
      const level = openLevel(state);
      if (!canConnect(current(level), source, target).ok) return;
      remember(state);
      level.edges.push(makeEdge(source, target));
    },
    /** Apply the changes which react flow reports (move, select, remove, ...). */
    updateNodes: (state, action: PayloadAction<NodeChange<JobNode>[]>) => {
      if (action.payload.some((change) => change.type === "remove")) {
        remember(state);
      }
      const level = openLevel(state);
      level.nodes = applyNodeChanges(action.payload, level.nodes);
      dropDanglingEdges(level);
    },
    updateEdges: (state, action: PayloadAction<EdgeChange<Edge>[]>) => {
      if (action.payload.some((change) => change.type === "remove")) {
        remember(state);
      }
      const level = openLevel(state);
      level.edges = applyEdgeChanges(action.payload, level.edges);
    },
    /**
     * Set fields of a job. Fields given replace the old ones as a whole, so a
     * parameter which is gone from `parameters` is gone from the job.
     */
    updateJob: (
      state,
      action: PayloadAction<{
        id: string;
        changes: Partial<JobFields>;
        // edits with the same key one after the other are one step of the history
        editKey?: string;
      }>,
    ) => {
      const { id, changes, editKey } = action.payload;
      const node = openLevel(state).nodes.find((n) => n.id === id);
      if (!node) return;
      if (editKey === undefined || editKey !== state.lastEditKey) {
        remember(state);
      }
      state.lastEditKey = editKey ?? null;
      node.data.job = { ...node.data.job, ...changes };
    },
    /** Delete jobs and dependencies together, as one step of the history. */
    deleteElements: (
      state,
      action: PayloadAction<{ nodeIds: string[]; edgeIds: string[] }>,
    ) => {
      const { nodeIds, edgeIds } = action.payload;
      if (nodeIds.length === 0 && edgeIds.length === 0) return;
      remember(state);
      const level = openLevel(state);
      level.nodes = level.nodes.filter((node) => !nodeIds.includes(node.id));
      level.edges = level.edges.filter((edge) => !edgeIds.includes(edge.id));
      dropDanglingEdges(level);
    },
    deleteJobNode: (state, action: PayloadAction<string>) => {
      remember(state);
      const level = openLevel(state);
      level.nodes = level.nodes.filter((node) => node.id !== action.payload);
      dropDanglingEdges(level);
    },
    /** Open the jobs of a parameter of a job, making them if there are none yet. */
    enterNested: (
      state,
      action: PayloadAction<{
        nodeId: string;
        param: string;
        kind: NestedKind;
      }>,
    ) => {
      const { nodeId, param, kind } = action.payload;
      const node = openLevel(state).nodes.find((n) => n.id === nodeId);
      if (!node) return;
      if (!node.data.nested[param]) {
        remember(state);
        node.data.nested[param] = { kind, nodes: [], edges: [] };
      }
      state.path.push({ nodeId, param });
    },
    /** Go back to the level at this depth: 0 is the root. */
    goToDepth: (state, action: PayloadAction<number>) => {
      state.path = state.path.slice(0, Math.max(0, action.payload));
    },
    setSubmitter: (state, action: PayloadAction<Record<string, unknown>>) => {
      state.pipeline.submitter = action.payload;
    },
    setHost: (
      state,
      action: PayloadAction<Record<string, unknown> | undefined>,
    ) => {
      state.pipeline.host = action.payload;
    },
    setVariables: (
      state,
      action: PayloadAction<Record<string, unknown> | undefined>,
    ) => {
      state.pipeline.variables = action.payload;
    },
    undo: (state) => {
      const entry = state.past.pop();
      if (!entry) return;
      state.future.push({
        root: current(state.root),
        pipeline: entry.pipeline ? current(state.pipeline) : undefined,
      });
      state.root = entry.root;
      if (entry.pipeline) state.pipeline = entry.pipeline;
      state.lastEditKey = null;
      closeMissingLevels(state);
    },
    redo: (state) => {
      const entry = state.future.pop();
      if (!entry) return;
      state.past.push({
        root: current(state.root),
        pipeline: entry.pipeline ? current(state.pipeline) : undefined,
      });
      state.root = entry.root;
      if (entry.pipeline) state.pipeline = entry.pipeline;
      state.lastEditKey = null;
      closeMissingLevels(state);
    },
  },
});

export const {
  loadPipeline,
  addNode,
  selectNode,
  openNode,
  connectNodes,
  updateNodes,
  updateEdges,
  updateJob,
  deleteElements,
  deleteJobNode,
  enterNested,
  goToDepth,
  setSubmitter,
  setHost,
  setVariables,
  undo,
  redo,
} = graphSlice.actions;

export default graphSlice.reducer;

/** Selectors, taking the whole state. */
interface WithGraph {
  graph: GraphState;
}

export const selectOpenLevel = (state: WithGraph): Level =>
  levelAt(state.graph.root, state.graph.path) ?? state.graph.root;

/** Why a job can't be added to the open level, or null if it can. */
export const selectAddJobBlock = (state: WithGraph): string | null =>
  addJobBlock(state.graph.root, state.graph.path);

export const selectSelectedNode = (state: WithGraph): JobNode | undefined =>
  selectOpenLevel(state).nodes.find((node) => node.selected);

export const selectCanUndo = (state: WithGraph): boolean =>
  state.graph.past.length > 0;

export const selectCanRedo = (state: WithGraph): boolean =>
  state.graph.future.length > 0;
