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

const initialState: InitialConfig = {
  jobs: [],
  submitter: {
    type_: "local_proc",
    working_directory: "",
    poll_timeout: 5,
    number_processes: 1,
    timeout: 3600,
  },
  variables: {},
};

export const initialPipelineConfig = createSlice({
  name: "initialPipelineConfig",
  initialState,
  reducers: {
    setJobs: (state, action) => {
      state.jobs = action.payload;
    },
    addJob: (state, action) => {
      state.jobs.push(action.payload);
    },
    removeJob: (state, action) => {
      state.jobs = state.jobs.filter((job) => job.job_id !== action.payload);
    },
    updateJob: (state, action) => {
      const index = state.jobs.findIndex(
        (job) => job.job_id === action.payload.job_id
      );
      if (index !== -1) {
        console.log("Job update redux called", action.payload)
        state.jobs[index] = action.payload;
      }
    },
    addDependency: (
      state,
      action: PayloadAction<{ job_id: string; depends_on: string }>
    ) => {
      const { job_id, depends_on } = action.payload;
      const job = state.jobs.find((job) => job.job_id === job_id);
      if (job) {
        if (job.depends_on) {
          job.depends_on.push(depends_on);
        } else {
          job.depends_on = [depends_on];
        }
        job.depends_on = [... new Set(job.depends_on)]; // Ensure uniqueness
      }
    },
    setSubmitter: (state, action) => {
      state.submitter = action.payload;
    },
    setVariables: (state, action) => {
      state.variables = action.payload;
    },
    updateVariable: (state, action) => {
      const { key, value } = action.payload;
      state.variables[key] = value;
    },
    reset: () => initialState,
  },
});

export const {
  setJobs,
  addJob,
  addDependency,
  removeJob,
  updateJob,
  setSubmitter,
  setVariables,
  updateVariable,
  reset,
} = initialPipelineConfig.actions;

export default initialPipelineConfig.reducer;
