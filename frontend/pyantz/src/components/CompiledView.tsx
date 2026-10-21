/** The jobs the pipeline compiles to, read only, coloured by how the run is going. */
import { useCallback, useEffect, useMemo } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { layoutPositions } from "../model/layout";
import { shortName } from "../model/newJob";
import { useConfig } from "../hooks/useValidation";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { compilePipeline } from "../store/slices/compileSlice";
import { useColorScheme } from "../theme";

type CompiledNodeData = {
  label: string;
  fn: string;
  status?: string;
  details?: string | null;
};

function CompiledNode({ data }: NodeProps<Node<CompiledNodeData>>) {
  return (
    <div
      className="job-node"
      data-testid="compiled-node"
      data-status={data.status ?? "none"}
      title={data.details ?? data.fn}
    >
      <Handle type="target" position={Position.Top} isConnectable={false} />
      <strong className="job-node-name">{data.label}</strong>
      <div className="job-node-function">{shortName(data.fn)}</div>
      {data.status && <div className="job-node-status">{data.status}</div>}
      <Handle type="source" position={Position.Bottom} isConnectable={false} />
    </div>
  );
}

const nodeTypes = { compiledNode: CompiledNode };

function Compiled() {
  const dispatch = useAppDispatch();
  const config = useConfig();
  const compiled = useAppSelector((state) => state.compile);
  const runJobs = useAppSelector((state) => state.run.jobs);
  const colorMode = useColorScheme();

  const refresh = useCallback(
    () => void dispatch(compilePipeline(config)),
    [dispatch, config],
  );
  // compile when the view opens, and again when the pipeline changes under it
  useEffect(() => {
    if (config.jobs.length > 0) refresh();
  }, [config, refresh]);

  const { nodes, edges } = useMemo(() => {
    const byId = new Map(runJobs.map((job) => [job.job_id, job]));
    const positions = layoutPositions(
      compiled.jobs.map((job) => job.job_id),
      compiled.edges.map(([source, target]) => ({ source, target })),
    );
    const nodes: Node<CompiledNodeData>[] = compiled.jobs.map((job) => ({
      id: job.job_id,
      type: "compiledNode",
      position: positions.get(job.job_id) ?? { x: 0, y: 0 },
      draggable: false,
      data: {
        label: job.name || shortName(job.function),
        fn: job.function,
        status: byId.get(job.job_id)?.status,
        details: byId.get(job.job_id)?.details,
      },
    }));
    const edges: Edge[] = compiled.edges.map(([source, target]) => ({
      id: `e${source}->${target}`,
      source,
      target,
      markerEnd: { type: MarkerType.ArrowClosed },
    }));
    return { nodes, edges };
  }, [compiled, runJobs]);

  return (
    <div className="job-board-wrapper" data-testid="compiled-view">
      <div className="breadcrumbs d-flex justify-content-between align-items-center">
        <span className="small">
          {compiled.status === "loading"
            ? "Compiling…"
            : `${compiled.jobs.length} job${compiled.jobs.length === 1 ? "" : "s"} after virtual jobs are expanded`}
        </span>
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary"
          onClick={refresh}
        >
          Refresh
        </button>
      </div>
      {compiled.status === "failed" && (
        <ul role="alert" className="text-danger small m-2">
          {compiled.errors.map((error) => (
            <li key={error}>{error}</li>
          ))}
        </ul>
      )}
      {config.jobs.length === 0 && (
        <p className="m-3 text-secondary">
          Add a job to see what it compiles to.
        </p>
      )}
      <div className="job-board-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          colorMode={colorMode}
          nodesDraggable={false}
          nodesConnectable={false}
          fitView
          fitViewOptions={{ maxZoom: 1 }}
          key={compiled.jobs.map((job) => job.job_id).join("|")}
        >
          <Background />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  );
}

export default function CompiledView() {
  // its own react flow store: the editor's nodes are of other types, and must not
  // be seen by this board while the tabs change
  return (
    <ReactFlowProvider>
      <Compiled />
    </ReactFlowProvider>
  );
}
