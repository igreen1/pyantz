/**
 * Stores the currently selected pipeline
 * and its associated jobs.
 */

import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

export interface Job {
  job_id: string;
  depends_on: string[];
  name: string;
  parameters: Record<string, unknown>;
  function_name: string;
  num_attempted_runs: number;
  strict: boolean;
}

/**
 * At runtime, check if some arbitrary thing is a job
 * Use: This is used to determine if a parameter should be rendered
 *    as a simple field/sub-form or as another job node.
 * @param value: any javascript variable
 * @returns True if the variable appears to represent a Job
 */
export const isJob = (value: any): value is Job =>  {


  const isObj = (item: any): item is object => (
    typeof item === "object" &&
    item !== null &&
    !Array.isArray(item)
  )

  const fieldIsType = (field: string, type: string) => {
    if (!(field in value)) {
      return false;
    } else if (type === "object") {
      return isObj(value[field])
    } else if (type === "array[string]") {
      return (
        Array.isArray(value[field]) &&
        value[field].every((item: any) => typeof item === "string")
      )
    } else {
      return (
        typeof value[field] === type
      )
    }
  }

  return (
    isObj(value) && 
    fieldIsType("job_id", "string") &&
    fieldIsType("depends_on", "array[string]") &&
    fieldIsType("name", "string") &&
    fieldIsType("parameters", "object") && 
    fieldIsType("function_name", "string") &&
    fieldIsType("num_attempted_runs", "number") &&
    fieldIsType("strict", "boolean")
  )

}

export interface LocalRunnerConfig {
  type_: "local_proc";
  working_directory: string;
  poll_timeout: number;
  number_processes: number;
  timeout: number;
}

export interface InitialConfig {
  jobs: Job[];

  submitter: LocalRunnerConfig;

  variables: Record<string, unknown>;
}
