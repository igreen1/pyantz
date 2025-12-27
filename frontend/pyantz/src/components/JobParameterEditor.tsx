/**
 * Job parameters are JSON-like objects that can contain various data types,
 * including strings, numbers, booleans, arrays, and nested objects.
 * This component provides a user interface for editing these parameters.
 */

import { useAppSelector } from "../store/hooks";
import Form from "@rjsf/core";
import validator from "@rjsf/validator-ajv8";
import { FaCross } from "react-icons/fa6";

export interface IJobParameterEditorProps {
  job_id: string;
  toggleShowEditor: () => void;
  setValue: (value: object) => void;
}

export const FloatingJobParameterEditor = (props: IJobParameterEditorProps) => {
  return (
    <div className="floating-editor">
      <FaCross size={36} onClick={props.toggleShowEditor} />
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

  // TODO: get current parameters to populate the form with existing values

  const currentPipeline = useAppSelector((state) => state.currentPipeline);
  const job = currentPipeline?.jobs.find((j) => j.job_id === props.job_id);

  // grab the schema of the job if it is available
  const allSchemas = useAppSelector((state) => state.jobSchemas);
  const jobSchema = job?.function_name
    ? allSchemas.schemas?.[job?.function_name] || null
    : null;

  if (!job) {
    return <div>Job not found</div>;
  }

  return (
    <div>
      <Form
        schema={jobSchema || { type: "object", properties: {} }}
        validator={validator}
        onSubmit={(e) => {
                props.setValue(e.formData);
                props.toggleShowEditor();
              }
        }
      />
    </div>
  );
};
