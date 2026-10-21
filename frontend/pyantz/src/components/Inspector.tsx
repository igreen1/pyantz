/** Edit the job which is selected: its settings, its parameters, its problems. */
import { useNodeProblems } from "../hooks/useNodeProblems";
import { useSchema } from "../hooks/useSchema";
import type { DependencyType } from "../model/types";
import type { JobFields, JobNode } from "../model/graph";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  deleteJobNode,
  enterNested,
  selectOpenLevel,
  selectSelectedNode,
  updateJob,
} from "../store/slices/graphSlice";
import { CheckField, NumberField, SelectField, TextField } from "./fields";
import ParameterForm from "./ParameterForm";

const DEPENDENCY_TYPES: readonly DependencyType[] = [
  "afterok",
  "afterany",
  "afternotok",
];

export default function Inspector() {
  const node = useAppSelector(selectSelectedNode);
  if (!node) {
    return (
      <p className="p-3 text-secondary">
        Select a job on the board to edit it, or add one from the list on the
        left.
      </p>
    );
  }
  // a new component per job, so that nothing typed leaks into the next job
  return <JobInspector key={node.id} node={node} />;
}

function JobInspector({ node }: { node: JobNode }) {
  const dispatch = useAppDispatch();
  const { job, nested } = node.data;
  const { kinds } = useSchema(job.function);
  const problems = useNodeProblems(node.id, node.data);
  const level = useAppSelector(selectOpenLevel);

  const set = (changes: Partial<JobFields>, field: string) =>
    dispatch(
      updateJob({ id: node.id, changes, editKey: `${node.id}:${field}` }),
    );

  const idTaken =
    job.job_id !== undefined &&
    level.nodes.some(
      (o) => o.id !== node.id && o.data.job.job_id === job.job_id,
    );

  const messages = [...problems.own, ...problems.fromServer];

  return (
    <div className="p-3" data-testid="inspector">
      <h2 className="h6 mb-0">{job.name || job.function}</h2>
      <p className="small text-secondary text-break">{job.function}</p>

      {messages.length > 0 && (
        <ul className="list-unstyled small text-danger" aria-label="Problems">
          {messages.map((message) => (
            <li key={message}>✗ {message}</li>
          ))}
        </ul>
      )}

      <TextField
        label="Name"
        value={job.name}
        onChange={(name) => set({ name: name || undefined }, "name")}
      />
      <TextField
        label="Job id"
        value={job.job_id}
        placeholder="(none)"
        error={idTaken ? "Another job of this level has this id." : null}
        onChange={(jobId) => set({ job_id: jobId || undefined }, "job_id")}
        help="Other jobs name this one by its id."
      />

      <h3 className="h6 mt-3">Parameters</h3>
      <ParameterForm
        nodeId={node.id}
        fn={job.function}
        parameters={job.parameters}
      />

      {Object.keys(kinds).length > 0 && (
        <>
          <h3 className="h6 mt-3">Jobs inside</h3>
          <ul className="list-unstyled">
            {Object.entries(kinds).map(([param, kind]) => (
              <li key={param}>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-primary mb-1"
                  onClick={() =>
                    dispatch(enterNested({ nodeId: node.id, param, kind }))
                  }
                >
                  Open {param} ({nested[param]?.nodes.length ?? 0})
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      <details className="mt-3">
        <summary className="small fw-semibold">More settings</summary>
        <div className="mt-2">
          <NumberField
            label="Retries"
            min={0}
            value={job.max_retries}
            onChange={(value) => set({ max_retries: value }, "max_retries")}
            help="How often a failed job is run again."
          />
          <NumberField
            label="Timeout (seconds)"
            min={0}
            value={job.timeout_seconds}
            onChange={(value) =>
              set({ timeout_seconds: value }, "timeout_seconds")
            }
          />
          <SelectField
            label="Waits for its dependencies"
            value={job.dependency_type ?? "afterok"}
            options={DEPENDENCY_TYPES}
            onChange={(value) =>
              set(
                { dependency_type: value === "afterok" ? undefined : value },
                "dependency_type",
              )
            }
            help="Only SLURM honours this; the local runner always waits for success."
          />
          <CheckField
            label="Strict"
            checked={job.strict ?? false}
            onChange={(strict) =>
              set({ strict: strict || undefined }, "strict")
            }
            help="No %{variables}; parameters are checked when the pipeline starts."
          />
        </div>
      </details>

      <button
        type="button"
        className="btn btn-sm btn-outline-danger mt-3"
        onClick={() => dispatch(deleteJobNode(node.id))}
      >
        Delete job
      </button>
    </div>
  );
}
