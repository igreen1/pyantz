/**
 * Stores the currently selected pipeline
 * and its associated jobs.
 */

import { createSlice } from "@reduxjs/toolkit"


export interface Job {
    job_id: string | null,
    depends_on: string[] | null,
    name: string,
    parameters: Record<string, unknown>,
    function_name: string,
    num_attempted_runs: number,
    strict: boolean
}

export interface LocalRunnerConfig {
    type_: "local_proc",
    working_directory: string,
    poll_timeout: number,
    number_processes: number,
    timeout: number
}

export interface InitialConfig {
    jobs: Job[],

    submitter: LocalRunnerConfig

    variables: Record<string, unknown>
}

const initialState: InitialConfig = {
    jobs: [],
    submitter: {
        type_: "local_proc",
        working_directory: "",
        poll_timeout: 5,
        number_processes: 1,
        timeout: 3600
    },
    variables: {}
}


export const initialPipelineConfig = createSlice({
    name: "initialPipelineConfig",
    initialState,
    reducers: {
        setJobs: (state, action) => {
            state.jobs = action.payload
        },
        addJob: (state, action) => {
            state.jobs.push(action.payload)
        },
        removeJob: (state, action) => {
            state.jobs = state.jobs.filter(job => job.job_id !== action.payload)
        },
        updateJob: (state, action) => {
            const index = state.jobs.findIndex(job => job.job_id === action.payload.job_id)
            if (index !== -1) {
                state.jobs[index] = action.payload
            }
        },
        setSubmitter: (state, action) => {
            state.submitter = action.payload
        },
        setVariables: (state, action) => {
            state.variables = action.payload
        },
        updateVariable: (state, action) => {
            const { key, value } = action.payload
            state.variables[key] = value
        },
        reset: () => initialState,
    },
})

export const { setJobs, addJob, removeJob, updateJob, setSubmitter, setVariables, updateVariable, reset } = initialPipelineConfig.actions

export default initialPipelineConfig.reducer