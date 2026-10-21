/** Run the pipeline on the server and watch how it goes. */
import { useMemo } from "react";
import { collectProblems } from "../model/problems";
import { useConfig } from "../hooks/useValidation";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { fetchLog, forgetRun, startRun } from "../store/slices/runSlice";
import { setMainTab } from "../store/slices/uiSlice";

const STATE_TEXT = {
  idle: "Not started",
  starting: "Starting…",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
  unknown: "Unknown (the server no longer knows how it went)",
} as const;

const STATE_STYLE = {
  idle: "text-bg-secondary",
  starting: "text-bg-info",
  running: "text-bg-primary",
  succeeded: "text-bg-success",
  failed: "text-bg-danger",
  unknown: "text-bg-warning",
} as const;

export default function RunPanel() {
  const dispatch = useAppDispatch();
  const config = useConfig();
  const root = useAppSelector((state) => state.graph.root);
  const schemas = useAppSelector((state) => state.jobSchemas.schemas);
  const run = useAppSelector((state) => state.run);

  const hasProblems = useMemo(
    () => collectProblems(root, schemas).length > 0,
    [root, schemas],
  );
  const empty = config.jobs.length === 0;
  const busy = run.state === "starting" || run.state === "running";

  return (
    <div className="p-3" data-testid="run-panel">
      <p className="small text-secondary">
        Runs the pipeline on the server, in a directory the server chooses. The
        working directory in the pipeline settings is not used.
      </p>
      <button
        type="button"
        className="btn btn-primary btn-sm"
        disabled={busy || empty || hasProblems}
        onClick={() => {
          dispatch(setMainTab("compiled"));
          void dispatch(startRun(config));
        }}
      >
        Run
      </button>
      {(empty || hasProblems) && (
        <span className="small text-secondary ms-2">
          {empty ? "Add a job first." : "Fix the problems first."}
        </span>
      )}

      {run.error && (
        <p role="alert" className="text-danger small mt-3">
          {run.error}
        </p>
      )}

      {run.state !== "idle" && (
        <div className="mt-3" aria-live="polite">
          <span
            className={`badge ${STATE_STYLE[run.state]}`}
            data-testid="run-state"
          >
            {STATE_TEXT[run.state]}
          </span>
          {run.report && (
            <p className="small mt-2 mb-1" data-testid="run-report">
              {run.report.success} of {run.report.total} done ·{" "}
              {run.report.running} running ·{" "}
              {run.report.pending + run.report.ready} waiting ·{" "}
              {run.report.error} failed
            </p>
          )}
          {run.jobs.length > 0 && (
            <table className="table table-sm small">
              <thead>
                <tr>
                  <th scope="col">Job</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {run.jobs.map((job) => (
                  <tr key={job.job_id}>
                    <td className="text-break">{job.job_id}</td>
                    <td>
                      {job.status}
                      {job.details ? (
                        <div className="text-danger text-break">
                          {job.details}
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="d-flex gap-2">
            <button
              type="button"
              className="btn btn-outline-secondary btn-sm"
              disabled={!run.runId}
              onClick={() => run.runId && void dispatch(fetchLog(run.runId))}
            >
              Show log
            </button>
            {!busy && (
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                onClick={() => dispatch(forgetRun())}
              >
                Clear
              </button>
            )}
          </div>
          {run.log !== null && (
            <>
              {run.logTruncated && (
                <p className="small text-secondary mt-2 mb-0">
                  Only the end of the log is shown.
                </p>
              )}
              <pre className="run-log" aria-label="Run log">
                {run.log || "(nothing was printed)"}
              </pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}
