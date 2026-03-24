// /**
//  * Job parameters are the heart of configuration
//  * But they are very complicated, this component makes it easier to edit them.
// */

// import { useMemo, useState } from 'react';
// import { JsonEditor } from 'json-edit-react'
// import { useAppSelector, useAppDispatch } from "../store/hooks";
// import { updateJob, type Job } from "../store/slices/currentPipeline";
// import Ajv2019, { _ } from "ajv/dist/2019"
// import type { JSONSchema7Definition, JSONSchema7 } from 'json-schema';
// import { keyword$DataError } from 'ajv/dist/compile/errors';
// import FancyJobNode from './FancyJobNode';

// export interface IJobParameterEditorProps {
//   job: Job
// }


// export default function JobParameterEditor({ job }: IJobParameterEditorProps) {
//   const dispatch = useAppDispatch();

//   const jobParameterSchema = useAppSelector((state) => {
//     const func_name = job?.function_name;
//     const schemas = state?.jobSchemas?.schemas;
//     return (
//       func_name && schemas
//     ) ? (
//       schemas?.[func_name] || undefined
//     ) : undefined;
//   })

//   const job_ref = "#/$defs/JobConfig";
//   const isSingleJobConfigSchemaElem = (prop: object) => (
//     // @ts-ignore
//     prop?.["$ref"] === job_ref
//   );
//   const isMultiJobConfigSchemaElem = (prop: object) => (
//       Object.hasOwn(prop, "items") &&
//       // @ts-ignore
//       prop?.items?.["$ref"] === job_ref
//   )

//   const isJobConfigSchemaElem = (prop: object) => (
//     isSingleJobConfigSchemaElem(prop) || isMultiJobConfigSchemaElem(prop)
//   )

//   const filterPropsFromSchema = (properties: JSONSchema7Definition, predicate: (arg0: object) => boolean) => {
//     return Object.fromEntries(
//       Object.entries(properties).filter(([_, value]) => predicate(value))
//     )
//   }

//   const singleJobSchemas = {
//     ...jobParameterSchema,
//     properties: jobParameterSchema?.properties ? filterPropsFromSchema(jobParameterSchema.properties, isSingleJobConfigSchemaElem) : undefined
//   };
//   const multiJobSchemas = {
//     ...jobParameterSchema,
//     properties: jobParameterSchema?.properties ? filterPropsFromSchema(jobParameterSchema.properties, isMultiJobConfigSchemaElem) : undefined
//   }
//   const nonJobSchema = {
//     ...jobParameterSchema,
//     properties: jobParameterSchema?.properties ? filterPropsFromSchema(jobParameterSchema.properties, (prop: object) => !isJobConfigSchemaElem(prop),) : undefined
//   }

//   const updateJobParameters = (newParams: Record<string, unknown>) => {
//     console.log("Updating job parameters", newParams);
//     const params = {
//       ...job.parameters,
//       ...newParams,
//     };
//     const newJobDefinition = {
//       ...job,
//       "parameters": params
//     };
//     dispatch(
//       updateJob(newJobDefinition)
//     )
//   }
//   if ((!job.parameters || Object.keys(job.parameters).length === 0) && jobParameterSchema?.properties) {
//     // Create a default params
//     const empty_default = Object.fromEntries(
//       Object.entries(jobParameterSchema.properties).map(([key, _]) => [key, null])
//     )
//     updateJobParameters(empty_default)
//   }


//   return (<div>
//     <NonJobParametersEditor
//       schema={nonJobSchema}
//       jobParams={job.parameters}
//       updateJobParams={updateJobParameters}
//     />
//   </div>)

// }
// interface ISubParametersEditorProps {
//   schema: JSONSchema7;
//   jobParams: Record<string, unknown>;
//   updateJobParams: (arg0: Record<string, unknown>) => void;
// }


// /**
//  * Edit child pipelines
//  */
// const SubPipelineEditor = ({ schema, jobParams, updateJobParams }: ISubParametersEditorProps) => {
// }

// /**
//  * Edit child jobs, where the job is a single job for the parameter
//  */
// const SubjobParametersEditor = ({ schema, jobParams, updateJobParams }: ISubParametersEditorProps) => {

//   // these jobs are NOT in the pipeline because they are part of the parameters
//   const parameters = Object.fromEntries(
//     Object.entries(jobParams).filter(([field, _]) => schema?.properties && Object.hasOwn(schema.properties, field))
//   );

//   // for the jobs which are a "simple" single job
  

// }

// const NonJobParametersEditor = ({ schema, jobParams, updateJobParams }: ISubParametersEditorProps) => {

//   const parameters = Object.fromEntries(
//     Object.entries(jobParams).filter(([field, _]) => schema?.properties && Object.hasOwn(schema.properties, field))
//   );

//   // validate our user input
//   const ajv = useMemo(() => new Ajv2019(), []);
//   const validate = useMemo(() => schema && schema?.properties ? ajv.compile(schema) : () => true, [schema, ajv]); // Re-compile only if schema changes

//   const [isValid, setIsValid] = useState(validate(parameters));

//   const updateData = (data: unknown) => {
//     const valid = validate(data);
//     setIsValid(valid)
//     updateJobParams(data)
//   }

//   const color = isValid ? "green" : "red"

//   return <div
//     style={{
//       border: `3px solid ${color}`
//     }}
//   >
//     <JsonEditor
//       data={parameters}
//       setData={updateData}
//     />
//   </div>

// }

