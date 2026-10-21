/**
 * Types of the configuration which `pyantz` runs, mirroring the python models in
 * `src/pyantz/infrastructure/config`.
 *
 * Each `*_FIELDS` list is built from an object typed `Record<keyof Type, true>`, so
 * it can't drift from its interface. A python test compares the lists to the python
 * models (`tests/frontend/test_model_fields.py`), which catches drift from the backend.
 */

export type DependencyType = "afterok" | "afterany" | "afternotok";

/** A job (real, or virtual when `virtual` is true), as written in a config. */
export interface JobConfig {
  job_id?: string;
  depends_on?: string[];
  parameters: Record<string, unknown>;
  strict?: boolean;
  name?: string | null;
  function: string;
  num_attempted_runs?: number;
  timeout_seconds?: number | null;
  max_retries?: number;
  dependency_type?: DependencyType;
  virtual?: boolean;
}

/** The part of a job which virtual jobs have too. */
export type VirtualJobConfig = Pick<
  JobConfig,
  | "job_id"
  | "depends_on"
  | "parameters"
  | "strict"
  | "name"
  | "function"
  | "virtual"
>;

export interface LocalRunnerConfig {
  type_: "local_proc";
  working_directory: string;
  poll_timeout?: number;
  number_processes?: number;
  timeout?: number | null;
  progress_interval?: number | null;
  use_same_proc?: boolean;
}

export interface SlurmRunnerConfig {
  type_: "slurm_sbatch";
  max_job_time_seconds?: number;
  slurm_args?: string[];
  working_dir: string;
  inherit_dependencies?: boolean;
}

export type SubmitterConfig = LocalRunnerConfig | SlurmRunnerConfig;

/** Where the controller runs; only the discriminator is typed, the rest is raw. */
export interface HostConfig {
  type_: "local" | "ssh" | "container";
  [setting: string]: unknown;
}

export interface InitialConfig {
  jobs: JobConfig[];
  submitter: SubmitterConfig;
  variables?: Record<string, unknown>;
  host?: HostConfig;
}

const fieldsOf = <T>(flags: Record<keyof T, true>): string[] =>
  Object.keys(flags).sort();

export const JOB_CONFIG_FIELDS = fieldsOf<JobConfig>({
  job_id: true,
  depends_on: true,
  parameters: true,
  strict: true,
  name: true,
  function: true,
  num_attempted_runs: true,
  timeout_seconds: true,
  max_retries: true,
  dependency_type: true,
  virtual: true,
});

export const VIRTUAL_JOB_CONFIG_FIELDS = fieldsOf<VirtualJobConfig>({
  job_id: true,
  depends_on: true,
  parameters: true,
  strict: true,
  name: true,
  function: true,
  virtual: true,
});

export const LOCAL_RUNNER_CONFIG_FIELDS = fieldsOf<LocalRunnerConfig>({
  type_: true,
  working_directory: true,
  poll_timeout: true,
  number_processes: true,
  timeout: true,
  progress_interval: true,
  use_same_proc: true,
});

export const SLURM_RUNNER_CONFIG_FIELDS = fieldsOf<SlurmRunnerConfig>({
  type_: true,
  max_job_time_seconds: true,
  slurm_args: true,
  working_dir: true,
  inherit_dependencies: true,
});

export const INITIAL_CONFIG_FIELDS = fieldsOf<InitialConfig>({
  jobs: true,
  submitter: true,
  variables: true,
  host: true,
});

export const MODEL_FIELDS = {
  JobConfig: JOB_CONFIG_FIELDS,
  VirtualJobConfig: VIRTUAL_JOB_CONFIG_FIELDS,
  LocalRunnerConfig: LOCAL_RUNNER_CONFIG_FIELDS,
  SlurmRunnerConfig: SLURM_RUNNER_CONFIG_FIELDS,
  InitialConfig: INITIAL_CONFIG_FIELDS,
};
