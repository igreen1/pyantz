/**
 * AI SLOP to create
 */
import { useState } from "react";
import { Handle, Position } from "@xyflow/react";
import { useAppDispatch } from "../store/hooks";
import { updateJob } from "../store/jobs/currentPipeline";
import { type Job } from "../store/jobs/currentPipeline";
import "./JobNode.css";
import { FloatingJobParameterEditor } from "./JobParameterEditor";

interface JobNodeProps {
  data: {
    label: string;
    job: Job;
  };
}

export default function JobNode({ data }: JobNodeProps) {
  const dispatch = useAppDispatch();
  const [isExpanded, setIsExpanded] = useState(false);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const handleFieldChange = (field: string, value: unknown) => {
    const updatedJob = { ...data.job, [field]: value };
    dispatch(updateJob(updatedJob));
  };

  const startEditing = (field: string, value: unknown) => {
    setEditingField(field);
    setEditValue(String(value));
  };

  const saveEdit = (field: string) => {
    try {
      let value: unknown = editValue;
      if (field === "num_attempted_runs") {
        value = parseInt(editValue, 10);
      } else if (field === "strict") {
        value = editValue === "true";
      } else if (field === "depends_on") {
        value = editValue.trim()
          ? editValue.split(",").map((s) => s.trim())
          : null;
      } else if (field === "parameters") {
        value = JSON.parse(editValue);
      }
      handleFieldChange(field, value);
    } catch (e) {
      console.error("Invalid value:", e);
    }
    setEditingField(null);
    setEditValue("");
  };

  const renderParameterField = (
    label: string,
    field: string,
    value: unknown
  ) => {
    const isEditing = editingField === field;
    const displayValue = Array.isArray(value)
      ? value.join(", ")
      : typeof value === "object"
      ? JSON.stringify(value)
      : String(value);

    return (
      <div key={field} className="job-field">
        <span className="job-field-label">{label}:</span>
        {isEditing ? (
          <FloatingJobParameterEditor
            job_id={data.job.job_id ?? "unknown"}
            toggleShowEditor={() => {
              setEditingField(null);
            }}
            setValue={(newValue: object) => {
              console.log("Form submission:", newValue);
              handleFieldChange(field, newValue);
              setEditingField(null);
              setEditValue("");
            }}
          />
        ) : (
          <span
            className="job-field-value"
            onDoubleClick={() => startEditing(field, value)}
            title={displayValue}
          >
            {displayValue}
          </span>
        )}
      </div>
    );
  };

  const renderField = (label: string, field: string, value: unknown) => {
    const isEditing = editingField === field;
    const displayValue =
      value !== null && value != undefined
        ? Array.isArray(value)
          ? value.join(", ")
          : typeof value === "object"
          ? JSON.stringify(value)
          : String(value)
        : "";

    return (
      <div key={field} className="job-field">
        <span className="job-field-label">{label}:</span>
        {isEditing ? (
          <input
            type={typeof value === "boolean" ? "checkbox" : "text"}
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") saveEdit(field);
              if (e.key === "Escape") setEditingField(null);
            }}
            onBlur={() => saveEdit(field)}
            autoFocus
            className="job-field-input"
          />
        ) : (
          <span
            className="job-field-value"
            onDoubleClick={() => startEditing(field, value)}
            title={displayValue}
          >
            {displayValue}
          </span>
        )}
      </div>
    );
  };


  return (
    <div className={`job-node ${isExpanded ? "expanded" : "collapsed"}`}>
      <Handle type="target" position={Position.Top} />

      <div
        className="job-node-header"
      >
        <div className="job-node-title" onDoubleClick={() => setEditingField("name")}>
          {
            editingField === "name" 
            ? (<>
              <input
              type="text"
              value={data.job.name}
              onChange={(e) => handleFieldChange("name", e.target.value)}
              onKeyDown={(e) => {
                if (e.key == "Escape") setEditingField(null)
              }}
              onBlur={() => setEditingField(null)}
              autoFocus
              />
            </>)
            : `${data.job.name} (ID: ${data.job.job_id})`
          }
          
        </div>
        <span className="job-node-toggle"  onClick={() => setIsExpanded(!isExpanded)}>{isExpanded ? "−" : "+"}</span>
      </div>

      {isExpanded && (
        <div className="job-node-details">

          {renderField("Function", "function_name", data.job.function_name)}
          {renderField("Depends On", "depends_on", data.job.depends_on)}
          {renderParameterField(
            "Parameters",

            "parameters",
            data.job.parameters
          )}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
