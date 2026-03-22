/**
 * This is where the user will edit their pipeline flow diagrams.
 */

import { useState, useCallback, useEffect, type MouseEvent } from "react";
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
import { addDependency } from "../store/slices/currentPipeline";
import { showJobOptions, showContextMenu, hideContextMenu } from "../store/slices/uiSlice";
import { setNodes, setEdges, updateNodes, updateEdges, } from "../store/slices/graphSlice";

/**
 * React component to edit the jobs dynamically.
 */
export default function JobBoard() {
  const dispatch = useAppDispatch();

  const nodes = useAppSelector((state) => state.jobGraph.nodes);
  const edges = useAppSelector((state) => state.jobGraph.edges);

  const currentPipeline = useAppSelector((state) => state.currentPipeline);

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
    const updatedNodes = currentPipeline.jobs
      .map((job) => {
        const previousElem = nodes.find((val: any) => val?.data?.job?.job_id === job.job_id);
        const x = previousElem ? previousElem.position.x : 0;
        const y = previousElem ? previousElem.position.y : 0;
        return {
          id: job.job_id,
          type: "jobNode",
          position: { x, y },
          data: {
            label: job.name,
            job
          }
        }
      })
    dispatch(setNodes(updatedNodes));
    console.log("New node states", updatedNodes)

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
    dispatch(setEdges(updatedEdges));
  }, [currentPipeline.jobs, dispatch]);

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