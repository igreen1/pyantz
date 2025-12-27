/**
 * Show all the available jobs and allow the user to select one.
 */
import { useState } from "react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import "./JobList.css";
import { addJob } from "../store/jobs/currentPipeline";

// interface IJobListProps {
// }

export const JobList = () => {
  const {
    items: availableJobs,
    status: get_job_status,
    descriptions: jobDescriptions,
  } = useAppSelector((state) => state.availableJobs);

  const dispatch = useAppDispatch();

  const [jobIdCounter, setJobIdCounter] = useState(0);

  const addJobToPipeline = (jobName: string) => {
    console.log("Adding job to pipeline:", jobName);
    const job_id = jobIdCounter.toString();
    setJobIdCounter(jobIdCounter + 1);

    const name_components = jobName.split(".");
    const defaultName = name_components[name_components.length - 1] + "_" + job_id;

    dispatch(
      addJob({
        job_id,
        depends_on: null,
        name: defaultName,
        parameters: {},
        function_name: jobName,
        num_attempted_runs: 0,
        strict: false,
      })
    )
  };

  const zip = (arr1: string[], arr2: string[]) => {
    return arr1.map((k, i) => [k, arr2[i]]);
  };

  return (
    <div style={{ border: "2px solid black", height: "100%" }}>
      <h2>Available Jobs</h2>
      {get_job_status === "loading" && <p>Loading jobs...</p>}
      {get_job_status === "failed" && <p>Error loading jobs.</p>}
      {get_job_status === "succeeded" && (
        <ul
          style={{
            listStyleType: "none",
            maxHeight: "100%",
            overflowY: "auto",
          }}
        >
          {zip(availableJobs, jobDescriptions).map(
            ([jobName, jobDescription]) => (
              <li
                key={jobName as string}
                className="job-item"
                style={{
                  minHeight: "50px",
                  marginBottom: "10px",
                  border: "1px solid grey",
                  padding: "5px",
                }}
                onClick={() => addJobToPipeline(jobName as string)}
              >
                <strong>{jobName}</strong>
                <p>{jobDescription}</p>
              </li>
            )
          )}
        </ul>
      )}
    </div>
  );
};
