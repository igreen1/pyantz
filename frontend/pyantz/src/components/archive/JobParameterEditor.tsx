/**
 * Job parameters are JSON-like objects that can contain various data types,
 * including strings, numbers, booleans, arrays, and nested objects.
 * This component provides a user interface for editing these parameters.
 */

import { useAppSelector } from "../store/hooks";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import "./JobParameterEditor.css";
import { useState } from "react";

export interface IJobParameterEditorProps {
  job_id: string;
  toggleShowEditor: () => void;
  setValue: (value: object) => void;
}

export const FloatingJobParameterEditor = (props: IJobParameterEditorProps) => {
  return (
    <div
      className="floating-editor"
      style={{
        // position: "absolute",
        // top: "20%",
        // left: "30%",
        // zIndex: 1000,
        // backgroundColor: "#283F3B",
      }}
    >
      <JobParameterEditorForm
        job_id={props.job_id}
        toggleShowEditor={props.toggleShowEditor}
        setValue={props.setValue}
      />
    </div>
  );
};

export const JobParameterEditorForm = (props: IJobParameterEditorProps) => {
  // grab the job

  // get current parameters to populate the form with existing values
  const currentPipeline = useAppSelector((state) => state.currentPipeline);
  const job = currentPipeline?.jobs.find((j) => j.job_id === props.job_id);
  const initialParameters = job?.parameters || {};

  const [currentInputNoSchema, setCurrentInputNoSchema] = useState(JSON.stringify(initialParameters));

  // grab the schema of the job if it is available
  const allSchemas = useAppSelector((state) => state.jobSchemas);
  const jobSchema = job?.function_name
    ? allSchemas.schemas?.[job?.function_name] || null
    : null;

  if (!job) {
    return <div>Job not found</div>;
  }

  let validJson;
  try {
    JSON.parse(currentInputNoSchema);
    validJson = true;
  } catch {
    validJson = false;
  }

  return (
    <div className="no-border-form">
      {
        jobSchema ?
          (
            <Form
              schema={jobSchema || { type: "object", properties: {} }}
              formData={initialParameters}
              validator={validator}
              onSubmit={(e) => {
                props.setValue(e.formData);
                props.toggleShowEditor();
              }}
              // className="no-border-form"
            />

          )
          : (
            <>
              <textarea
                style={{
                  border: validJson ? '2px solid green' : '2px solid red',
                  boxShadow: "none"
                }}
                value={
                  currentInputNoSchema
                }
                onChange={(e) => setCurrentInputNoSchema(e.target.value)}
              />
              <br />
              <button onClick={() => {
                // todo: handle errors
                const userParams = JSON.parse(currentInputNoSchema);
                props.setValue(userParams);

                props.toggleShowEditor();
              }
              }>Submit</button>
            </>

          )

      }

    </div>
  );
};
