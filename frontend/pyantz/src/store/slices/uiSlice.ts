/**
 * Stores the currently selected pipeline
 * and its associated jobs.
 */

import { createSlice } from "@reduxjs/toolkit";


export interface UiOptions {
    // if true, show the available jobs retrieved from the backend
    // used for a user to add a job
    showJobOptions: boolean;
}

const initialState: UiOptions = {
    showJobOptions: false,
}

export const uiOptions = createSlice({
    name: "uiOptions",
    initialState,
    reducers: {
        showJobOptions: (state) => {
            console.log("SHOW JOB OPTS")
            state.showJobOptions = true;
        },
        hideJobOptions: (state) => {
            state.showJobOptions = false;
        }
    }
})

export const {
    showJobOptions,
    hideJobOptions,
} = uiOptions.actions

export default uiOptions.reducer;
