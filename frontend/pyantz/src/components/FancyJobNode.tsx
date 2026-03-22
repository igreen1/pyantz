/**
 * Show fancier job nodes, including allowing nodes within nodes
 */

import { useState, type MouseEvent } from "react";
import { useAppDispatch } from "../store/hooks";
import { updateJob } from "../store/slices/currentPipeline";
import { type Job } from "../store/slices/currentPipeline";
import { Handle, Position, NodeResizer } from '@xyflow/react';
import { addJobToContextMenu } from "../store/slices/uiSlice";
import JobParameterEditor from "./JobParameterEditor";

export interface IFancyJobNodeProps {
  data: {
    label: string;
    job: Job
  }
}



export default function FancyJobNode({ data }: IFancyJobNodeProps) {
  const dispatch = useAppDispatch();

  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  const handleContextMenu = (right_click: MouseEvent<HTMLDivElement>) => {
    right_click.preventDefault();
    const jobId = data.job.job_id;
    dispatch(
      addJobToContextMenu(jobId)
    )
  }

  return (
    <div
      className={`job-node ${isExpanded ? "expanded" : "collapsed"}`}
      onContextMenu={handleContextMenu}
      style={{
        height: "100%",
        width: "100%",
        overflow: "scroll"
      }}
    >
      <NodeResizer />
      <Handle type="target" position={Position.Top} />

      <div
        className="job-node-header"
      >
        <EditableLabel
          field_name="name"
          job={data.job}
        />
        <span
          className="job-node-toggle"
          onClick={() => setIsExpanded(!isExpanded)}
          style={{
            fontSize: "20px",
            cursor: "default"
          }}
        >
          {isExpanded ? "-" : "+"}
        </span>
      </div>
      {
        isExpanded ? <JobParameterEditor job={data.job} /> : <></>
      }
      <Handle type="source" position={Position.Bottom} />
    </div>
  )

}


const EditableLabel = (props: { field_name: "function_name" | "name" | "job_id", job: Job }) => {

  const dispatch = useAppDispatch();
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [currValue, setCurrValue] = useState(props.job[props.field_name]);

  const handleUpdate = (newValue: string) => {
    setCurrValue(newValue)
  }

  const saveChanges = () => {
    // note: this will trigger a re-render of this entire component
    // which isn't strictly necessary but not a big expense
    console.log("dispatching save event")
    const newJob = {
      ...props.job,
      [props.field_name]: currValue
    };
    dispatch(
      updateJob(
        newJob
      )
    );
    setIsEditing(false);
  }

  return (
    <div className="editable-text" onDoubleClick={() => setIsEditing(true)}>
      {
        isEditing ? (
          <>
            <input
              type="text"
              value={currValue}
              onKeyDown={(e) => {
                if (e.key == "Escape") setIsEditing(false)
              }}
              onChange={(e) => handleUpdate(e.target.value)}
              onBlur={() => saveChanges()}
            />
          </>
        ) : (currValue)
      }

    </div>
  )

}