import { useEffect } from "react";
import "./App.css";
import JobBoard from "./components/JobBoard";
import { useAppDispatch, useAppSelector } from "./store/hooks";
// import { JobSelection } from "./components/JobSelection";
import { fetchAvailableJobs } from "./store/slices/availableJobSlice";
import { fetchJobSchemas } from "./store/slices/jobSchemaSlice";
// import { JobList } from "./components/JobList";
import 'bootstrap/dist/css/bootstrap.min.css';
import JobOptionsMenu from "./components/JobOptionsMenu";


function App() {
  const dispatch = useAppDispatch();

  const { items: availableJobs, status: get_job_status } = useAppSelector(
    (state) => state.availableJobs
  );
  const { status: get_job_schema_status } = useAppSelector(
    (state) => state.jobSchemas
  );

  // Lazy load available jobs on mount
  useEffect(() => {
    if (get_job_status === "idle") {
      dispatch(fetchAvailableJobs());
    }
  }, [dispatch, get_job_status]);

  useEffect(() => {
    if (get_job_status === "succeeded" && get_job_schema_status === "idle") {
      dispatch(fetchJobSchemas(availableJobs));
    }
  }, [dispatch, get_job_schema_status, get_job_status, availableJobs]);

  return (
    <>
      <div className="job-board-body" style={{ display: "flex", width: "100vw " }}>
        <div className="job-board-flow">
          <JobOptionsMenu />
          <JobBoard />
        </div>
      </div>
    </>
  );
}

export default App;
