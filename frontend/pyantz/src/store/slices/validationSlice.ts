/** What the api says is wrong with the pipeline. */
import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

export interface ValidationState {
  status: "idle" | "checking" | "valid" | "invalid" | "failed";
  // problems named in the api's answer which are about no job in particular
  unmapped: string[];
  // problems by id of the node they are about
  byNode: Record<string, string[]>;
  // why the check itself failed (e.g. the api could not be reached)
  error: string | null;
}

const initialState: ValidationState = {
  status: "idle",
  unmapped: [],
  byNode: {},
  error: null,
};

export const validationSlice = createSlice({
  name: "validation",
  initialState,
  reducers: {
    checking: (state) => {
      state.status = "checking";
    },
    checked: (
      state,
      action: PayloadAction<{
        valid: boolean;
        unmapped: string[];
        byNode: Record<string, string[]>;
      }>,
    ) => {
      state.status = action.payload.valid ? "valid" : "invalid";
      state.unmapped = action.payload.unmapped;
      state.byNode = action.payload.byNode;
      state.error = null;
    },
    checkFailed: (state, action: PayloadAction<string>) => {
      state.status = "failed";
      state.error = action.payload;
      state.unmapped = [];
      state.byNode = {};
    },
  },
});

export const { checking, checked, checkFailed } = validationSlice.actions;
export default validationSlice.reducer;
