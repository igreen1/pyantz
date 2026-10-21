/**
 * Store slice for job schemas.
 * @module store/jobs/jobSchemaSlice
 * @author Ian Green
 */
import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import type { JSONSchema7 } from "json-schema";
import api, { errorMessage } from "../../services/api";
import { tokenForgotten, tokenSupplied } from "../actions";

interface JobSchemaFetchResult {
  schemas: Record<string, JSONSchema7>;
  // job name -> why its schema could not be loaded
  errors: Record<string, string>;
}

interface JobSchemasState extends JobSchemaFetchResult {
  status: "idle" | "loading" | "succeeded" | "failed";
  error: string | null;
}

const initialState: JobSchemasState = {
  schemas: {},
  errors: {},
  status: "idle",
  error: null,
};

/**
 * Fetch the schema of every job.
 *
 * A job whose schema fails to load is recorded in `errors` and does not stop the
 * others from loading; the thunk only fails if every request failed.
 */
export const fetchJobSchemas = createAsyncThunk<
  JobSchemaFetchResult,
  string[],
  { rejectValue: string }
>("jobSchemas/fetchAllSchemas", async (jobNames, { rejectWithValue }) => {
  const settled = await Promise.allSettled(
    jobNames.map(async (jobName) => {
      const response = await api.get(`/jobs/schema/${jobName}`);
      return response.data.json_schema as JSONSchema7;
    }),
  );

  const result: JobSchemaFetchResult = { schemas: {}, errors: {} };
  settled.forEach((outcome, index) => {
    const jobName = jobNames[index];
    if (outcome.status === "fulfilled") {
      result.schemas[jobName] = outcome.value;
    } else {
      result.errors[jobName] = errorMessage(outcome.reason);
    }
  });

  if (jobNames.length > 0 && Object.keys(result.schemas).length === 0) {
    return rejectWithValue(
      `No job schema could be loaded: ${Object.values(result.errors)[0]}`,
    );
  }
  return result;
});

export const jobSchemaSlice = createSlice({
  name: "jobSchemas",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      // a new token may open what was closed, and the old one may have loaded
      // what the new one may not see
      .addCase(tokenSupplied, () => initialState)
      .addCase(tokenForgotten, () => initialState)
      .addCase(fetchJobSchemas.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(fetchJobSchemas.fulfilled, (state, action) => {
        state.schemas = action.payload.schemas;
        state.errors = action.payload.errors;
        state.status = "succeeded";
        state.error = null;
      })
      .addCase(fetchJobSchemas.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.payload ?? action.error.message ?? "Unknown error";
      });
  },
});

export default jobSchemaSlice.reducer;
