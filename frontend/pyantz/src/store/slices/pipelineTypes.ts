/**
 * Types of the pipeline being edited.
 */

export interface Job {
  job_id: string;
  depends_on: string[];
  name: string;
  parameters: Record<string, unknown>;
  function_name: string;
  num_attempted_runs: number;
  strict: boolean;
}

const isObj = (item: unknown): item is Record<string, unknown> =>
  typeof item === "object" && item !== null && !Array.isArray(item);

/**
 * At runtime, check if some arbitrary thing is a job
 * Use: This is used to determine if a parameter should be rendered
 *    as a simple field/sub-form or as another job node.
 * @param value: any javascript variable
 * @returns True if the variable appears to represent a Job
 */
export const isJob = (value: unknown): value is Job =>
  isObj(value) &&
  typeof value.job_id === "string" &&
  Array.isArray(value.depends_on) &&
  value.depends_on.every((item) => typeof item === "string") &&
  typeof value.name === "string" &&
  isObj(value.parameters) &&
  typeof value.function_name === "string" &&
  typeof value.num_attempted_runs === "number" &&
  typeof value.strict === "boolean";

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
