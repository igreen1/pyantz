/**
 * Stores the possible/available jobs
 * by grabbing it from the API.
 */

import {
  createSlice,
  createAsyncThunk,
  type PayloadAction,
} from "@reduxjs/toolkit";
import api, { errorMessage } from "../../services/api";
import { tokenForgotten, tokenSupplied } from "../actions";

interface AvailableJobsState {
  items: string[];
  descriptions: string[];
  status: "idle" | "loading" | "succeeded" | "failed";
  error: string | null;
}

const initialState: AvailableJobsState = {
  items: [],
  descriptions: [],
  status: "idle",
  error: null,
};

/**
 * Async thunk to fetch available jobs from the API
 */
export const fetchAvailableJobs = createAsyncThunk<
  { items: string[]; descriptions: string[] },
  void,
  { rejectValue: string }
>("availableJobs/fetchAvailableJobs", async (_arg, { rejectWithValue }) => {
  try {
    const response = await api.get("/jobs/get_all_jobs");
    const jobs = response.data.jobs as { name: string; description: string }[];
    return {
      items: jobs.map((job) => job.name),
      descriptions: jobs.map((job) => job.description),
    };
  } catch (error) {
    return rejectWithValue(errorMessage(error));
  }
});

export const availableJobSlice = createSlice({
  name: "availableJobs",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      // a new token may open what was closed, and the old one may have loaded
      // what the new one may not see
      .addCase(tokenSupplied, () => initialState)
      .addCase(tokenForgotten, () => initialState)
      .addCase(fetchAvailableJobs.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(
        fetchAvailableJobs.fulfilled,
        (
          state,
          action: PayloadAction<{ items: string[]; descriptions: string[] }>,
        ) => {
          state.items = action.payload.items;
          state.descriptions = action.payload.descriptions;
          state.status = "succeeded";
          state.error = null;
        },
      )
      .addCase(fetchAvailableJobs.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.payload ?? action.error.message ?? "Unknown error";
      });
  },
});

export default availableJobSlice.reducer;
