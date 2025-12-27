/**
 * Canvas on which we work with the jobs to connect them.
 */

import { useState, useCallback, useEffect } from "react";
import {
  ReactFlow,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  type NodeTypes,
  type Connection,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import JobNode from "./JobNode";
import { addDependency } from "../store/jobs/currentPipeline";

export default function JobBoard() {
  const dispatch = useAppDispatch();

  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);

  const nodeTypes: NodeTypes = {
    jobNode: JobNode,
  };

  const onNodesChange = useCallback(
    (changes) =>
      setNodes((nodesSnapshot) => applyNodeChanges(changes, nodesSnapshot)),
    []
  );
  const onEdgesChange = useCallback(
    (changes) =>
      setEdges((edgesSnapshot) => applyEdgeChanges(changes, edgesSnapshot)),
    []
  );
  const onConnect = useCallback(
    (params: Connection) => {
      console.log("Connecting:", params);
      // setEdges((edgesSnapshot) => addEdge(params, edgesSnapshot));
      dispatch(
        addDependency({ job_id: params.target!, depends_on: params.source! })
      );
    },
    [dispatch]
  );

  const currentPipeline = useAppSelector((state) => state.currentPipeline);

  useEffect(() => {
    console.log(currentPipeline);
  }, [currentPipeline]);

  useEffect(() => {
    // Update nodes based on currentPipeline jobs
    const updatedNodes = currentPipeline.jobs.map((job, index) => ({
      id: job.job_id,
      type: "jobNode",
      position: { x: 0, y: index * 100 },
      data: { label: job.name, job },
    }));
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

  return (
    <div style={{ width: "100%", height: "100%", border: "2px solid black" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
      />
    </div>
  );
}
