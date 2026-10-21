/** Render components with a store which has what the app loads from the api. */
import type { ReactElement } from "react";
import { render } from "@testing-library/react";
import { ReactFlowProvider } from "@xyflow/react";
import { Provider } from "react-redux";
import { configToGraph } from "../model/convert";
import { loadPipeline } from "../store/slices/graphSlice";
import { makeStore, type AppStore, type RootState } from "../store/store";
import { dumpedJobs, nestedKinds, sequentialIds } from "./fixtures";

/** A store as it is once the jobs and their schemas have been fetched. */
export const loadedStore = (preloaded: Partial<RootState> = {}): AppStore => {
  const names = Object.keys(dumpedJobs);
  return makeStore({
    availableJobs: {
      items: names,
      descriptions: names.map((name) => dumpedJobs[name].description),
      status: "succeeded",
      error: null,
    },
    jobSchemas: {
      schemas: Object.fromEntries(
        names.map((name) => [name, dumpedJobs[name].json_schema]),
      ),
      errors: {},
      status: "succeeded",
      error: null,
    },
    ...preloaded,
  });
};

/** Put the jobs of a config on the board of the store; ids are n1, n2, ... */
export const withConfig = (store: AppStore, config: object): AppStore => {
  store.dispatch(
    loadPipeline(
      configToGraph(
        {
          submitter: { type_: "local_proc", working_directory: "w" },
          ...config,
        },
        nestedKinds,
        sequentialIds(),
      ),
    ),
  );
  return store;
};

export const renderWithStore = (
  ui: ReactElement,
  store: AppStore = loadedStore(),
) => ({
  store,
  ...render(
    <Provider store={store}>
      <ReactFlowProvider>{ui}</ReactFlowProvider>
    </Provider>,
  ),
});
