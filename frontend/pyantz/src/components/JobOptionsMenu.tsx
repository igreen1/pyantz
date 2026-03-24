/** This menu pops up and allows a user to add jobs to the scene */

import { useState, type Dispatch, type SetStateAction } from "react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { addNode } from "../store/slices/graphSlice";
import "./JobOptionsMenu.css"
import { addJob } from "../store/slices/currentPipeline";
import { Oval } from 'react-loader-spinner'; // Import a specific spinner type
import { BsXLg } from "react-icons/bs";
import { hideJobOptions } from "../store/slices/uiSlice";
import type { JSONSchema7 } from "json-schema";

export default function JobOptionsMenu() {
  const dispatch = useAppDispatch();

  const showOptions = useAppSelector(
    (state) => state.uiOptions.showJobOptions
  )

  const [jobDefaultIdCounter, setJobDefaultIdCounter] = useState(0);

  const createJob = jobAdderFactory(
    jobDefaultIdCounter,
    setJobDefaultIdCounter,
  );

  if (!showOptions) {
    return null;
  }

  const closeMenu = () => {
    dispatch(hideJobOptions())
  }

  return (<>
    <div className="job-options-menu">
      <BsXLg className="job-options-menu-close-button" onClick={closeMenu} />
      <h2>Jobs</h2>
      <JobList
        createJob={createJob}
      ></JobList>
    </div>
  </>)

}

const jobAdderFactory = (
  jobIdCounter: number,
  setJobIdCounter: Dispatch<SetStateAction<number>>,
): (arg0: string, arg1: JSONSchema7 | undefined) => void => {

  const dispatch = useAppDispatch();

  const addJobToPipeline = (jobName: string, jobSchema: JSONSchema7 | undefined) => {
    console.log("Adding job to pipeline:", jobName);
    const job_id = jobIdCounter.toString();
    setJobIdCounter(jobIdCounter + 1);

    const name_components = jobName.split(".");
    const defaultName = name_components[name_components.length - 1] + "_" + job_id;

    // add default parameters if a schema is available
    console.log("Got schema for job: ", jobSchema)
    const entries = jobSchema?.required?.map((req_field) => [req_field, null]);

    const parameters = jobSchema && entries ? (
      Object.fromEntries(entries)
    ) : {};

    const job = {
      job_id,
      depends_on: null,
      name: defaultName,
      parameters: parameters,
      function_name: jobName,
      num_attempted_runs: 0,
      strict: false,
    }


    dispatch(
      addJob(job)
    )

    // add the node directly
    const newGraphNode = {
      id: job.job_id,
      type: "jobNode",
      position: { x: 0, y: 0 },
      data: {
        label: job.name,
        job
      },
    };

    dispatch(
      addNode(newGraphNode)
    );


  };

  return addJobToPipeline;

}

interface JobListProps {
  createJob: (jobName: string, jobSchema: JSONSchema7 | undefined) => void;
};

const JobList = (
  { createJob }: JobListProps
) => {

  const {
    items: availableJobs,
    status: get_job_status,
    descriptions: jobDescriptions,
  } = useAppSelector((state) => state.availableJobs);

  const loading_animation = (
    <div className="loading-animation">
      <Oval
        color="purple"
        secondaryColor="purple"
        wrapperClass="loading-animation"
      />
    </div>
  )

  const loading_response = (
    <div style={{ padding: "20px" }}>
      {loading_animation}
      <p style={{ paddingTop: "10px" }}>Loading Jobs</p>
    </div>
  )

  return (
    <div className="job-options-menu-list">
      {(get_job_status === "loading" || get_job_status === "idle") && loading_response}
      {get_job_status === "failed" && <p>Error loading jobs.</p>}
      {
        get_job_status === "succeeded" &&
        <InnerJobList names={availableJobs} descriptions={jobDescriptions} createJob={createJob} />
      }
    </div>
  )
}


interface InnerJobListProps {
  names: string[];
  descriptions: string[];
  createJob: (jobName: string, jobSchema: JSONSchema7 | undefined) => void;
}

const InnerJobList = ({ names, descriptions, createJob }: InnerJobListProps) => {

  const zip = (arr1: string[], arr2: string[]) => {
    return arr1.map((k, i) => [k, arr2[i]]);
  };

  const makeListItem = (jobName: string, jobDesc: string) => {
    const schema =  useAppSelector((state) => state?.jobSchemas?.schemas?.[jobName]);
    return (
      <li
        key={jobName}
        className="job-options-menu-inner-list-item"
        onClick={() => createJob(jobName, schema)}
      >
        <strong>{jobName}</strong>
        <p>{jobDesc}</p>
      </li>
    )
  }

  return (
    <ul className="job-options-menu-inner-list">
      {
        zip(names, descriptions).map(
          ([jobName, jobDesc]) => (
            makeListItem(jobName, jobDesc)
          )
        )
      }
    </ul>
  )

}