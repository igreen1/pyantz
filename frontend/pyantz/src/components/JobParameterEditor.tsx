/**
 * Handles editing the parameters of a job
 */

import { useMemo, useState, useEffect } from 'react';
import { JsonEditor } from 'json-edit-react'
import { useAppSelector, useAppDispatch } from "../store/hooks";
import {updateJobNode} from "../store/slices/graphSlice";
import Ajv2019, { _ } from "ajv/dist/2019"
import type { JSONSchema7Definition, JSONSchema7 } from 'json-schema';
import { keyword$DataError } from 'ajv/dist/compile/errors';
import FancyJobNode from './FancyJobNode';


interface IJobParameterEditorProps {
  job: Job
}

export default function JobParameterEditor({ job }: IJobParameterEditorProps) {
  console.log("JOBJOB");
  console.log(job);
  const dispatch = useAppDispatch();

  const jobParameterSchema = useAppSelector((state) => {
    const func_name = job?.function_name;
    const schemas = state?.jobSchemas?.schemas;
    return (
      func_name && schemas
    ) ? (
      schemas?.[func_name] || undefined
    ) : undefined;
  })

  const {
    simpleParameters,
    singleJobParameters,
    multiJobParameters
  } = jobParameterSchema ? splitParams(
    job.parameters,
    jobParameterSchema,
  ) : {
      simpleParameters: job.parameters,
      singleJobParameters: null,
      multiJobParameters: null,
    };

  // console.log("Splitting");
  // console.log(simpleParameters);
  // console.log(singleJobParameters);
  // console.log(multiJobParameters);
  // console.log("Done splitting");

  const updateJobParameters = (newParams: Record<string, unknown>) => {
    console.log("HELLO")
    console.log(newParams)
    const updatedParams = {
      ...job.parameters,
      ...newParams
    };
    const newJobDefinition = {
      ...job,
      parameters: updatedParams,
    }
    dispatch(
      updateJob(newJobDefinition)
    );
    dispatch (
      updateJobNode(newJobDefinition)
    );
  }

  return <div>
    {
      simpleParameters?.schema && simpleParameters?.parameters ?
        <NonJobParametersEditor
          paramsSchema={simpleParameters.schema}
          parameters={simpleParameters.parameters}
          updateJobParams={updateJobParameters}
        /> : <></>
    }
  </div>

}


interface ISchemaAndParams {
  schema: JSONSchema7,
  parameters: Record<string, unknown>
}

interface IParameterTypes {
  simpleParameters: ISchemaAndParams | null,
  singleJobParameters: ISchemaAndParams | null,
  multiJobParameters: ISchemaAndParams | null,
}


interface IInnerParameterEditorProps {
  paramsSchema: JSONSchema7 | undefined;
  parameters: Record<string, unknown>;
  updateJobParams: (arg0: Record<string, unknown>) => void;
}

const NonJobParametersEditor = ({ paramsSchema, parameters, updateJobParams }: IInnerParameterEditorProps) => {

  const ajv = useMemo(() => new Ajv2019(), []);
  const validate = useMemo(() => paramsSchema && paramsSchema?.properties ? ajv.compile(paramsSchema) : () => true, [paramsSchema, ajv]); // Re-compile only if schema changes

  const [isValid, setIsValid] = useState(validate(parameters));

  useEffect(() => {
    setIsValid(validate(parameters));
  }, [parameters, setIsValid])


  const setData = (data: unknown) => {
    // @ts-ignore
    updateJobParams(data);
  }

  const color = isValid ? "green" : "red"

  return <div
    style={{
      border: `3px solid ${color}`
    }}
  >
    <JsonEditor
      data={parameters}
      setData={setData}
    />
  </div>

}



// Parameters can be modified either directly by users
// Or they may be a set of child nodes
// or they may be a single child node
// This will mark each of those possibilities
const splitParams = (parameters: Record<string, unknown>, schema: JSONSchema7): IParameterTypes => {

  const jobRefKey = "#/$defs/JobConfig";

  const isSingleJobConfig = (property: JSONSchema7Definition) => (
    // @ts-ignore
    property?.["$ref"] === jobRefKey
  )

  const isJobConfigList = (property: JSONSchema7Definition) => (
    // @ts-ignore
    Object.hasOwn(property, "items") &&
    // @ts-ignore
    property?.items?.["$ref"] === jobRefKey
  )

  const isNotJobConfig = (property: JSONSchema7Definition): boolean => (
    !(isSingleJobConfig(property) || isJobConfigList(property))
  )

  const props = schema?.properties;
  if (!props) {
    /// idk??
    return {
      simpleParameters: null, multiJobParameters: null, singleJobParameters: null,
    }
  }

  const getFieldsMatching = (
    filterFn: (js: JSONSchema7Definition) => boolean,
  ) => (
    Object.entries(props)
      .filter(([_fieldName, fieldTypeDef]) => filterFn(fieldTypeDef))
      .map(([fieldName, _typeDef]) => fieldName)
  )

  const nonJobFields = getFieldsMatching(isNotJobConfig);
  const singleJobFields = getFieldsMatching(isSingleJobConfig);
  const multiJobFields = getFieldsMatching(isJobConfigList);


  const filterObjectFields = (o: object, fields: string[]) => {
    return Object.fromEntries(
      Object.entries(o).filter(([fieldName, _]) => fields.includes(fieldName))
    )
  }

  const parameterConstructor = (fieldList: string[]) => ({
    schema: {
      ...schema,
      "properties": filterObjectFields(props, fieldList),
      "required": schema?.required?.filter((req_field) => fieldList.includes(req_field))
    },
    parameters: filterObjectFields(parameters, fieldList)
  })

  const simpleParameters = parameterConstructor(nonJobFields);
  const singleJobParameters = parameterConstructor(singleJobFields);
  const multiJobParameters = parameterConstructor(multiJobFields);

  return {
    simpleParameters: Object.keys(simpleParameters).length > 0 ? simpleParameters : null,
    singleJobParameters: Object.keys(singleJobParameters).length > 0 ? singleJobParameters : null,
    multiJobParameters: Object.keys(multiJobParameters).length > 0 ? multiJobParameters : null,
  }


}