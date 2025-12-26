/**
 * Canvas on which we work with the jobs to connect them.
 */

import { useState, useCallback, useEffect } from 'react';
import { ReactFlow, applyNodeChanges, applyEdgeChanges, addEdge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { fetchAvailableJobs } from '../store/jobs/availableJobSlice';
import { fetchJobSchemas } from '../store/jobs/jobSchemaSlice';
 
const initialNodes = [
  { id: 'n1', position: { x: 0, y: 0 }, data: { label: 'Node 1' } },
  { id: 'n2', position: { x: 0, y: 100 }, data: { label: 'Node 2' } },
];
const initialEdges = [{ id: 'n1-n2', source: 'n1', target: 'n2' }];
 
export default function JobBoard() {
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);
  const dispatch = useAppDispatch();
  const { items: availableJobs, status: get_job_status } = useAppSelector(state => state.availableJobs);
  const { schemas: jobSchemas, status: get_job_schema_status } = useAppSelector(state => state.jobSchemas);

  // Lazy load available jobs on mount
  useEffect(() => {
    if (get_job_status === "idle" ) {
      dispatch(fetchAvailableJobs());
    }
  }, [dispatch, get_job_status]);

  useEffect(() => {
    if (get_job_status === "succeeded" && get_job_schema_status === "idle") {
        dispatch(fetchJobSchemas(availableJobs));
    }
  }, [dispatch, get_job_schema_status, get_job_status, availableJobs]);


 
  const onNodesChange = useCallback(
    (changes) => setNodes((nodesSnapshot) => applyNodeChanges(changes, nodesSnapshot)),
    [],
  );
  const onEdgesChange = useCallback(
    (changes) => setEdges((edgesSnapshot) => applyEdgeChanges(changes, edgesSnapshot)),
    [],
  );
  const onConnect = useCallback(
    (params) => setEdges((edgesSnapshot) => addEdge(params, edgesSnapshot)),
    [],
  );
 
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
      />
    </div>
  );
}