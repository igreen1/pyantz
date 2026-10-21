/** The jobs the pipeline compiles to, once virtual jobs are expanded. */
import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import api, { errorList } from "../../services/api";

export interface CompiledJob {
  job_id: string;
  name: string | null;
  function: string;
  depends_on: string[];
}

export interface CompileState {
  status: "idle" | "loading" | "succeeded" | "failed";
  jobs: CompiledJob[];
  edges: [string, string][];
  errors: string[];
}

const initialState: CompileState = {
  status: "idle",
  jobs: [],
  edges: [],
  errors: [],
};

export const compilePipeline = createAsyncThunk<
  { jobs: CompiledJob[]; edges: [string, string][] },
  unknown,
  { rejectValue: string[] }
>("compile/run", async (config, { rejectWithValue }) => {
  try {
    const response = await api.post("/config/compile", config);
    return response.data;
  } catch (error) {
    return rejectWithValue(errorList(error));
  }
});

export const compileSlice = createSlice({
  name: "compile",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(compilePipeline.pending, (state) => {
        state.status = "loading";
      })
      .addCase(compilePipeline.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.jobs = action.payload.jobs;
        state.edges = action.payload.edges;
        state.errors = [];
      })
      .addCase(compilePipeline.rejected, (state, action) => {
        state.status = "failed";
        state.jobs = [];
        state.edges = [];
        state.errors = action.payload ?? [
          action.error.message ?? "Unknown error",
        ];
      });
  },
});

export default compileSlice.reducer;
