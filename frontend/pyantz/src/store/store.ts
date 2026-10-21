import availableJobsReducer from "./slices/availableJobSlice";
import jobSchemaReducer from "./slices/jobSchemaSlice";
import UiOptionsReducer from "./slices/uiSlice";
import GraphSliceReducer from "./slices/graphSlice";
import validationReducer from "./slices/validationSlice";
import authReducer from "./slices/authSlice";
import compileReducer from "./slices/compileSlice";
import runReducer from "./slices/runSlice";
import {
  type Action,
  type ThunkAction,
  combineReducers,
  configureStore,
} from "@reduxjs/toolkit";

const rootReducer = combineReducers({
  availableJobs: availableJobsReducer,
  jobSchemas: jobSchemaReducer,
  uiOptions: UiOptionsReducer,
  graph: GraphSliceReducer,
  validation: validationReducer,
  auth: authReducer,
  compile: compileReducer,
  run: runReducer,
});

// Infer the `RootState` and `AppDispatch` types from the reducers
export type RootState = ReturnType<typeof rootReducer>;

/** Make a store; tests make their own so state does not leak between them. */
export const makeStore = (preloadedState?: Partial<RootState>) =>
  configureStore({ reducer: rootReducer, preloadedState });

export type AppStore = ReturnType<typeof makeStore>;
export type AppDispatch = AppStore["dispatch"];
export type AppThunk = ThunkAction<void, RootState, unknown, Action>;

export const store = makeStore();
