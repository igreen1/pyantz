import { useEffect, useState } from "react";
import "./App.css";
import JobBoard from "./components/JobBoard";
import { useAppDispatch, useAppSelector } from "./store/hooks";
import { JobSelection } from "./components/JobSelection";
import { fetchAvailableJobs } from "./store/jobs/availableJobSlice";
import { fetchJobSchemas } from "./store/jobs/jobSchemaSlice";
import { JobList } from "./components/JobList";

function App() {
  const dispatch = useAppDispatch();

  const [displayPopup, setDisplayPopup] = useState(false);

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
    console.log(get_job_status);
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
          <JobSelection
            displayPopup={displayPopup}
            setDisplayPopup={setDisplayPopup}
          />
          <JobBoard />
        </div>
        {
          displayPopup ? 
          <div className="job-board-popup">
            <JobList />
          </div> 
          : null
        }
      </div>
    </>
  );
}

export default App;
