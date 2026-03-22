/**
 * Select jobs to be added to the workflow
 */
import { useAppSelector } from "../store/hooks";
import { FaCirclePlus } from "react-icons/fa6";

// Props for the JobSelection component
interface IJobSelectionProps {
  // Whether to display the job selection popup
  // this plus button controls whether that is shown
  displayPopup: boolean;
  // Function to set the displayPopup state
  // Used to toggle display popup on click when enabled
  setDisplayPopup: (display: boolean) => void;
}

export const JobSelection = (prop: IJobSelectionProps) => {
  const { status: get_job_status } = useAppSelector(
    (state) => state.availableJobs
  );
  const { status: get_job_schema_status } = useAppSelector(
    (state) => state.jobSchemas
  );

  const succeeded =
    get_job_status === "succeeded" && get_job_schema_status === "succeeded";

  const togglePopup = () => {
    prop.setDisplayPopup(!prop.displayPopup);
  };

  return (
    <>
      <FaCirclePlus
        size={36}
        color={succeeded ? "green" : "grey"}
        onClick={succeeded || prop.displayPopup ? togglePopup : undefined}
        style={{ float: "left", marginTop: "5px", marginLeft: "5px", cursor: succeeded ? "pointer" : "not-allowed" }}
      />
    </>
  );
};
