/**
 * Show fancier job nodes, including allowing nodes within nodes
 */

import { useCallback, useEffect, useState, type MouseEvent } from "react";
import { useAppDispatch } from "../store/hooks";
import {
  Handle,
  Position,
  NodeResizer,
  type NodeProps,
  type Node,
} from "@xyflow/react";
import { addJobToContextMenu } from "../store/slices/uiSlice";
import JobParameterEditor from "./JobParameterEditor";
import type { Job } from "../store/slices/pipelineTypes";
import { updateJobNode } from "../store/slices/graphSlice";

type IFancyJobNodeProps = NodeProps<Node<{ job: Job; label: string }>>;

export default function FancyJobNode({ id, data }: IFancyJobNodeProps) {
  const dispatch = useAppDispatch();

  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  const handleContextMenu = (right_click: MouseEvent<HTMLDivElement>) => {
    right_click.preventDefault();
    dispatch(addJobToContextMenu(id));
  };

  return (
    <div
      className={`job-node ${isExpanded ? "expanded" : "collapsed"}`}
      onContextMenu={handleContextMenu}
      style={{
        height: "100%",
        width: "100%",
        overflow: "scroll",
      }}
    >
      <NodeResizer />
      <Handle type="target" position={Position.Top} />

      <div className="job-node-header">
        <EditableLabel id={id} field_name="name" job={data.job} />
        <span
          className="job-node-toggle"
          onClick={() => setIsExpanded(!isExpanded)}
          style={{
            fontSize: "20px",
            cursor: "default",
          }}
        >
          {isExpanded ? "-" : "+"}
        </span>
      </div>
      {isExpanded ? <JobParameterEditor job={data.job} id={id} /> : <></>}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

interface IEditableLabelProps {
  id: string;
  field_name: "function_name" | "name" | "job_id";
  job: Job;
}

const EditableLabel = ({ id, field_name, job }: IEditableLabelProps) => {
  const dispatch = useAppDispatch();
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [currValue, setCurrValue] = useState(job[field_name]);

  const handleUpdate = (newValue: string) => {
    setCurrValue(newValue);
  };

  // make sure changes made elsewhere are reflected here
  // todo: how to better sync state? should we just dispatch on
  useEffect(() => {
    setCurrValue(job[field_name]);
  }, [job[field_name]]);

  const saveChanges = useCallback(() => {
    // dispatch changes to the simulation
    const newJob = {
      ...job,
      [field_name]: currValue,
    };
    dispatch(updateJobNode({ id, job: newJob }));
    setIsEditing(false);
  }, [dispatch, id, job, field_name]);

  return (
    <div className="editable-text" onDoubleClick={() => setIsEditing(true)}>
      {isEditing ? (
        <>
          <input
            type="text"
            value={currValue}
            onKeyDown={(e) => {
              if (e.key == "Escape") setIsEditing(false);
            }}
            onChange={(e) => handleUpdate(e.target.value)}
            onBlur={() => saveChanges()}
          />
        </>
      ) : (
        currValue
      )}
    </div>
  );
};
