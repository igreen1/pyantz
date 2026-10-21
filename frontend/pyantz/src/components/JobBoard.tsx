/**
 * This is where the user will edit their pipeline flow diagrams.
 */

import { useCallback, useState, type DragEvent, type MouseEvent } from "react";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useReactFlow,
  type Connection,
  type EdgeChange,
  type NodeChange,
  type NodeTypes,
  type OnConnectEnd,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./jobBoard.css";
import { useAddJob } from "../hooks/useAddJob";
import { canConnect } from "../model/connect";
import type { JobNode } from "../model/graph";
import { useAppDispatch, useAppSelector, useAppStore } from "../store/hooks";
import {
  connectNodes,
  deleteElements,
  selectAddJobBlock,
  selectOpenLevel,
  updateEdges,
  updateNodes,
} from "../store/slices/graphSlice";
import {
  hideContextMenu,
  showContextMenu,
  showNotice,
} from "../store/slices/uiSlice";
import { useColorScheme } from "../theme";
import Breadcrumbs from "./Breadcrumbs";
import ContextMenu from "./ContextMenu";
import FancyJobNode from "./FancyJobNode";

// defined outside the component so react flow sees the same object every render
const nodeTypes: NodeTypes = {
  jobNode: FancyJobNode,
};

/** What a job dragged from the palette carries. */
export const JOB_DRAG_TYPE = "application/x-pyantz-job";

/**
 * React component to edit the jobs dynamically.
 */
function Board() {
  const dispatch = useAppDispatch();
  const store = useAppStore();
  const addJob = useAddJob();
  const { screenToFlowPosition } = useReactFlow();
  const colorMode = useColorScheme();

  const level = useAppSelector(selectOpenLevel);
  // Fit the view when the board is opened with jobs on it. This is decided once:
  // react flow fits again when the prop turns on, so a job added to an empty board
  // would move the view, and the next one would land somewhere else.
  const [fitOnOpen] = useState(level.nodes.length > 0);

  // Callbacks used by the reactflow library
  const onNodesChange = useCallback(
    (changes: NodeChange<JobNode>[]) => dispatch(updateNodes(changes)),
    [dispatch],
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => dispatch(updateEdges(changes)),
    [dispatch],
  );
  const isValidConnection = useCallback(
    (connection: Connection | { source: string; target: string }) =>
      canConnect(
        selectOpenLevel(store.getState()),
        connection.source,
        connection.target,
      ).ok,
    [store],
  );
  const onConnect = useCallback(
    (params: Connection) => {
      const check = canConnect(
        selectOpenLevel(store.getState()),
        params.source,
        params.target,
      );
      if (check.ok) {
        dispatch(
          connectNodes({ source: params.source, target: params.target }),
        );
      } else {
        dispatch(showNotice({ kind: "error", text: check.reason }));
      }
    },
    [dispatch, store],
  );
  // react flow does not call onConnect for a connection which is not valid, so
  // the user would not be told why nothing happened
  const onConnectEnd = useCallback<OnConnectEnd>(
    (_event, state) => {
      const { fromNode, toNode, isValid } = state;
      if (isValid !== false || !fromNode || !toNode) return;
      const check = canConnect(
        selectOpenLevel(store.getState()),
        fromNode.id,
        toNode.id,
      );
      if (!check.ok)
        dispatch(showNotice({ kind: "error", text: check.reason }));
    },
    [dispatch, store],
  );
  // deleting is one step of the history: jobs and their dependencies together
  const onBeforeDelete = useCallback(
    async ({
      nodes,
      edges,
    }: {
      nodes: { id: string }[];
      edges: { id: string }[];
    }) => {
      dispatch(
        deleteElements({
          nodeIds: nodes.map((node) => node.id),
          edgeIds: edges.map((edge) => edge.id),
        }),
      );
      return false;
    },
    [dispatch],
  );
  // End callbacks used by the flow library

  const handleContextMenu = (
    right_click: MouseEvent | globalThis.MouseEvent,
  ) => {
    right_click.preventDefault();
    dispatch(
      showContextMenu({
        position: { x: right_click.clientX, y: right_click.clientY },
        boardPosition: screenToFlowPosition({
          x: right_click.clientX,
          y: right_click.clientY,
        }),
        nodeId:
          (right_click.target as HTMLElement)
            .closest(".react-flow__node")
            ?.getAttribute("data-id") ?? undefined,
      }),
    );
  };

  const onDragOver = (event: DragEvent) => {
    if (
      event.dataTransfer.types.includes(JOB_DRAG_TYPE) &&
      !selectAddJobBlock(store.getState())
    ) {
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
    }
  };
  const onDrop = (event: DragEvent) => {
    const fn = event.dataTransfer.getData(JOB_DRAG_TYPE);
    if (!fn) return;
    event.preventDefault();
    addJob(fn, screenToFlowPosition({ x: event.clientX, y: event.clientY }));
  };

  return (
    <div className="job-board-canvas" onDragOver={onDragOver} onDrop={onDrop}>
      <ReactFlow
        nodes={level.nodes}
        edges={level.edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onConnectEnd={onConnectEnd}
        onBeforeDelete={onBeforeDelete}
        isValidConnection={isValidConnection}
        nodeTypes={nodeTypes}
        colorMode={colorMode}
        deleteKeyCode={["Backspace", "Delete"]}
        fitView={fitOnOpen}
        fitViewOptions={{ maxZoom: 1 }}
        onContextMenu={handleContextMenu}
        onNodeContextMenu={(event) => handleContextMenu(event)}
        onPaneClick={() => dispatch(hideContextMenu())}
        onMoveStart={() => dispatch(hideContextMenu())}
      >
        <Background />
        <MiniMap pannable zoomable />
        <Controls />
      </ReactFlow>
      <ContextMenu />
    </div>
  );
}

export default function JobBoard() {
  // a fresh board for each level and each loaded pipeline, so that it fits its jobs
  const boardKey = useAppSelector(
    (state) =>
      `${state.graph.generation}:` +
      state.graph.path
        .map((entry) => `${entry.nodeId}/${entry.param}`)
        .join(">"),
  );
  return (
    <div className="job-board-wrapper">
      <Breadcrumbs />
      <Board key={boardKey} />
    </div>
  );
}
