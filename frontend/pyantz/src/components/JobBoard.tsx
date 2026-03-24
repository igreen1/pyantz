/**
 * This is where the user will edit their pipeline flow diagrams.
 */

import { useCallback, type MouseEvent } from "react";
import {
  ReactFlow,
  MiniMap,
  Controls,
  type Connection,
  type NodeChange,
  type EdgeChange,
  type NodeTypes,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./jobBoard.css";
import { useAppDispatch, useAppSelector } from "../store/hooks";
// import JobNode from "./JobNode";
import FancyJobNode from "./FancyJobNode";
import ContextMenu, { type ContextMenuItem } from "./ContextMenu";
import { showJobOptions, showContextMenu, hideContextMenu } from "../store/slices/uiSlice";
import { updateNodes, updateEdges, addEdge, } from "../store/slices/graphSlice";

/**
 * React component to edit the jobs dynamically.
 */
export default function JobBoard() {
  const dispatch = useAppDispatch();

  const nodes = useAppSelector((state) => state.jobGraph.nodes);
  const edges = useAppSelector((state) => state.jobGraph.edges);

  const nodeTypes: NodeTypes = {
    jobNode: FancyJobNode,
  };

  // Callbacks used by the reactflow library
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      dispatch(updateNodes(changes));
    },
    [dispatch]
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      dispatch(updateEdges(changes))
    },
    [dispatch]
  );
  const onConnect = useCallback(
    (params: Connection) => {
      let dep_id = params.source!;
      let job_id = params.target!;
      let con = {
        id: `e${dep_id}->${job_id}`,
        source: dep_id,
        target: job_id,
        animated: true,
        markerEnd: {
          type: MarkerType.ArrowClosed
        }
      }
      dispatch(
        addEdge(con)
      )
    },
    [dispatch]
  );
  // End callbacks used by the flow library

  const handleContextMenu = (right_click: MouseEvent<HTMLDivElement>) => {
    right_click.preventDefault();
    const position = { x: right_click.clientX, y: right_click.clientY };
    dispatch(
      showContextMenu(
        {
          position,
        }
      )
    )
  }

  const closeContextMenu = () => {
    dispatch(hideContextMenu())
  }

  const contextMenuItems: ContextMenuItem[] = [
    {
      "name": "Add Job",
      "onClick": () => {
        dispatch(
          showJobOptions()
        )
        closeContextMenu()
      }
    }
  ]

  return (
    <div className="job-board-wrapper" style={{ width: "100%", height: "100%", border: "2px solid black" }}>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        onContextMenu={handleContextMenu}
        onClick={closeContextMenu}
      >
        <MiniMap />
        <Controls />
      </ReactFlow>
      <ContextMenu
        items={contextMenuItems}
      />
    </div>
  )

}