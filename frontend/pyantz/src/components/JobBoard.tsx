/**
 * This is where the user will edit their pipeline flow diagrams.
 */

import { useState, useCallback, useEffect, type MouseEvent } from "react";
import {
  ReactFlow,
  applyNodeChanges,
  applyEdgeChanges,
  MiniMap,
  Controls,
  type Node,
  type Edge,
  type Connection,
  type NodeChange,
  type EdgeChange,
  type NodeTypes,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./jobBoard.css";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import JobNode from "./JobNode";
import ContextMenu, { type ContextMenuItem } from "./ContextMenu";
import { addDependency } from "../store/slices/currentPipeline";
import { showJobOptions, showContextMenu, hideContextMenu } from "../store/slices/uiSlice";


/**
 * React component to edit the jobs dynamically.
 */
export default function JobBoard() {
  const dispatch = useAppDispatch();

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  // Handle custom right clicking context men


  const currentPipeline = useAppSelector((state) => state.currentPipeline);


  const nodeTypes: NodeTypes = {
    jobNode: JobNode,
  };

  // Callbacks used by the reactflow library
  const onNodesChange = useCallback(
    (changes: NodeChange[]) =>
      setNodes((nodesSnapshot) => applyNodeChanges(changes, nodesSnapshot)),
    []
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) =>
      setEdges((edgesSnapshot) => applyEdgeChanges(changes, edgesSnapshot)),
    []
  );
  const onConnect = useCallback(
    (params: Connection) => {
      console.log("Connecting:", params);
      dispatch(
        addDependency({ job_id: params.target!, depends_on: params.source! })
      );
    },
    [dispatch]
  );
  // End callbacks used by the flow library

  useEffect(() => {
    // Update nodes based on currentPipeline jobs
    const previousNodes = nodes.map((node) => node.id);
    const newJobs = currentPipeline.jobs.filter((job) => !previousNodes.includes(job.job_id));
    const newNodes = newJobs.map((job) => ({
      id: job.job_id,
      type: "jobNode",
      position: { x: 0, y: 0 },
      data: { label: job.name, job },

    }))
    const updatedNodes = [...nodes, ...newNodes];
    console.log(updatedNodes);
    setNodes(updatedNodes);

    // Update edges based on currentPipeline job dependencies
    const updatedEdges = currentPipeline.jobs
      .filter((job) => job.depends_on)
      .flatMap((job) =>
        job.depends_on!.map((dep) => ({
          id: `e${dep}->${job.job_id}`,
          source: dep,
          target: job.job_id,
          animated: true,
          markerEnd: {
            type: MarkerType.ArrowClosed,
          },
        }))
      );
    setEdges(updatedEdges);
  }, [currentPipeline.jobs]);

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