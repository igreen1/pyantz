import { useEffect } from "react";
import { ReactFlowProvider } from "@xyflow/react";
import "bootstrap/dist/css/bootstrap.min.css";
import "./App.css";
import CompiledView from "./components/CompiledView";
import Inspector from "./components/Inspector";
import JobBoard from "./components/JobBoard";
import Notice from "./components/Notice";
import Palette from "./components/Palette";
import PipelineSettings from "./components/PipelineSettings";
import ProblemsPanel from "./components/ProblemsPanel";
import RunPanel from "./components/RunPanel";
import StatusBar from "./components/StatusBar";
import TokenPrompt from "./components/TokenPrompt";
import Toolbar from "./components/Toolbar";
import { useRunPolling } from "./hooks/useRunPolling";
import { useColorScheme } from "./theme";
import { useShortcuts } from "./hooks/useShortcuts";
import { useValidation } from "./hooks/useValidation";
import { collectProblems } from "./model/problems";
import { useAppDispatch, useAppSelector } from "./store/hooks";
import { fetchAvailableJobs } from "./store/slices/availableJobSlice";
import { fetchJobSchemas } from "./store/slices/jobSchemaSlice";
import { restoreRun } from "./store/slices/runSlice";
import {
  setMainTab,
  setSideTab,
  type MainTab,
  type SideTab,
} from "./store/slices/uiSlice";

const SIDE_TABS: { id: SideTab; label: string }[] = [
  { id: "job", label: "Job" },
  { id: "pipeline", label: "Pipeline" },
  { id: "problems", label: "Problems" },
  { id: "run", label: "Run" },
];

const MAIN_TABS: { id: MainTab; label: string }[] = [
  { id: "editor", label: "Editor" },
  { id: "compiled", label: "Compiled" },
];

function Tabs<T extends string>({
  label,
  tabs,
  active,
  onSelect,
}: {
  label: string;
  tabs: { id: T; label: string }[];
  active: T;
  onSelect: (id: T) => void;
}) {
  return (
    <div className="nav nav-tabs" role="tablist" aria-label={label}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={active === tab.id}
          className={`nav-link ${active === tab.id ? "active" : ""}`}
          onClick={() => onSelect(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function App() {
  const dispatch = useAppDispatch();

  const { items: availableJobs, status: get_job_status } = useAppSelector(
    (state) => state.availableJobs,
  );
  const { status: get_job_schema_status } = useAppSelector(
    (state) => state.jobSchemas,
  );
  const { mainTab, sideTab } = useAppSelector((state) => state.uiOptions);
  const needsToken = useAppSelector((state) => state.auth.needsToken);
  const root = useAppSelector((state) => state.graph.root);
  const schemas = useAppSelector((state) => state.jobSchemas.schemas);
  const serverProblems = useAppSelector((state) => state.validation.byNode);
  const unmapped = useAppSelector((state) => state.validation.unmapped);

  useColorScheme();
  useShortcuts();
  useValidation();
  useRunPolling();

  // Lazy load available jobs on mount
  useEffect(() => {
    if (get_job_status === "idle" && !needsToken) {
      dispatch(fetchAvailableJobs());
    }
  }, [dispatch, get_job_status, needsToken]);

  useEffect(() => {
    if (
      get_job_status === "succeeded" &&
      get_job_schema_status === "idle" &&
      !needsToken
    ) {
      dispatch(fetchJobSchemas(availableJobs));
    }
  }, [
    dispatch,
    get_job_schema_status,
    get_job_status,
    availableJobs,
    needsToken,
  ]);

  // a run which was going when the page was closed is picked up again
  useEffect(() => {
    dispatch(restoreRun());
  }, [dispatch]);

  const problemCount =
    collectProblems(root, schemas, serverProblems).length + unmapped.length;

  return (
    <ReactFlowProvider>
      <div
        className="app"
        data-schemas-ready={
          get_job_schema_status === "succeeded" ||
          get_job_schema_status === "failed"
            ? ""
            : undefined
        }
      >
        <header className="app-header">
          <img src="/pyantz_logo.png" alt="" className="app-logo" />
          <h1 className="h6 mb-0">PyAntz</h1>
          <Toolbar />
          <StatusBar />
        </header>
        <div className="app-palette">
          <Palette />
        </div>
        <main className="app-main">
          <Tabs
            label="View"
            tabs={MAIN_TABS}
            active={mainTab}
            onSelect={(id) => dispatch(setMainTab(id))}
          />
          <div className="app-main-view">
            {mainTab === "editor" ? <JobBoard /> : <CompiledView />}
          </div>
        </main>
        <aside className="app-side" aria-label="Details">
          <Tabs
            label="Details"
            tabs={SIDE_TABS.map((tab) =>
              tab.id === "problems" && problemCount > 0
                ? { ...tab, label: `Problems (${problemCount})` }
                : tab,
            )}
            active={sideTab}
            onSelect={(id) => dispatch(setSideTab(id))}
          />
          <div className="app-side-view">
            {sideTab === "job" && <Inspector />}
            {sideTab === "pipeline" && <PipelineSettings />}
            {sideTab === "problems" && <ProblemsPanel />}
            {sideTab === "run" && <RunPanel />}
          </div>
        </aside>
        <Notice />
        <TokenPrompt />
      </div>
    </ReactFlowProvider>
  );
}

export default App;
