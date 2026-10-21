/** Whether the api wants a token, and whether we have one. */
import { createAction, createSlice } from "@reduxjs/toolkit";
import { getToken } from "../../services/api";
import { tokenForgotten, tokenSupplied } from "../actions";

export interface AuthState {
  // the api turned a request down: ask for a token
  needsToken: boolean;
  hasToken: boolean;
  // the last token given was turned down
  rejected: boolean;
}

export const unauthorized = createAction("auth/unauthorized");

const initialState = (): AuthState => ({
  needsToken: false,
  hasToken: getToken() !== null,
  rejected: false,
});

export const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(unauthorized, (state) => {
        // a token was already given, so it must be wrong
        state.rejected = state.hasToken;
        state.needsToken = true;
      })
      .addCase(tokenSupplied, (state) => {
        state.needsToken = false;
        state.hasToken = true;
      })
      .addCase(tokenForgotten, (state) => {
        state.hasToken = false;
        state.rejected = false;
      });
  },
});

export default authSlice.reducer;
