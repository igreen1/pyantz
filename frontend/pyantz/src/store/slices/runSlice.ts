/** The run started from this page, and how far it is. */
import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import api, { errorMessage } from "../../services/api";
import { loadRunId, saveRunId } from "../../services/session";

export interface RunJob {
  job_id: string;
  // ready, pending, running, error or success
  status: string;
  details: string | null;
}

export interface RunReport {
  total: number;
  success: number;
  error: number;
  pending: number;
  ready: number;
  running: number;
}

export interface RunState {
  runId: string | null;
  // "unknown": the server no longer knows how it went (e.g. it was restarted)
  state: "idle" | "starting" | "running" | "succeeded" | "failed" | "unknown";
  report: RunReport | null;
  jobs: RunJob[];
  error: string | null;
  log: string | null;
  logTruncated: boolean;
}

const initialState: RunState = {
  runId: null,
  state: "idle",
  report: null,
  jobs: [],
  error: null,
  log: null,
  logTruncated: false,
};

export const startRun = createAsyncThunk<
  string,
  unknown,
  { rejectValue: string }
>("run/start", async (config, { rejectWithValue }) => {
  try {
    const response = await api.post("/runs", config);
    const runId = response.data.run_id as string;
    saveRunId(runId);
    return runId;
  } catch (error) {
    return rejectWithValue(errorMessage(error));
  }
});

interface RunResponse {
  run_id: string;
  state: RunState["state"];
  report: RunReport | null;
  jobs: RunJob[];
}

export const fetchRun = createAsyncThunk<
  RunResponse,
  string,
  { rejectValue: { message: string; gone: boolean } }
>("run/fetch", async (runId, { rejectWithValue }) => {
  try {
    const response = await api.get(`/runs/${runId}`);
    return response.data;
  } catch (error) {
    const gone =
      (error as { response?: { status?: number } }).response?.status === 404;
    if (gone) saveRunId(null);
    return rejectWithValue({ message: errorMessage(error), gone });
  }
});

export const fetchLog = createAsyncThunk<
  { log: string; truncated: boolean },
  string,
  { rejectValue: string }
>("run/log", async (runId, { rejectWithValue }) => {
  try {
    const response = await api.get(`/runs/${runId}/log`);
    return { log: response.data.log, truncated: response.data.truncated };
  } catch (error) {
    return rejectWithValue(errorMessage(error));
  }
});

export const runSlice = createSlice({
  name: "run",
  initialState,
  reducers: {
    /** Pick up the run of an earlier visit to the page, if there was one. */
    restoreRun: (state) => {
      const runId = loadRunId();
      if (runId && state.runId === null) {
        state.runId = runId;
        state.state = "running";
      }
    },
    forgetRun: () => {
      saveRunId(null);
      return initialState;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(startRun.pending, () => ({ ...initialState, state: "starting" }))
      .addCase(startRun.fulfilled, (state, action) => {
        state.runId = action.payload;
        state.state = "running";
      })
      .addCase(startRun.rejected, (state, action) => {
        state.state = "idle";
        state.error = action.payload ?? action.error.message ?? "Unknown error";
      })
      .addCase(fetchRun.fulfilled, (state, action) => {
        if (action.meta.arg !== state.runId) return;
        state.state = action.payload.state;
        state.report = action.payload.report;
        state.jobs = action.payload.jobs;
        state.error = null;
      })
      .addCase(fetchRun.rejected, (state, action) => {
        if (action.meta.arg !== state.runId) return;
        if (action.payload?.gone) return initialState;
        state.error = action.payload?.message ?? "Unknown error";
      })
      .addCase(fetchLog.fulfilled, (state, action) => {
        state.log = action.payload.log;
        state.logTruncated = action.payload.truncated;
      })
      .addCase(fetchLog.rejected, (state, action) => {
        state.log = null;
        state.error = action.payload ?? "Unknown error";
      });
  },
});

export const { restoreRun, forgetRun } = runSlice.actions;
export default runSlice.reducer;
