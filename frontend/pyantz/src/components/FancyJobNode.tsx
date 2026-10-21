/**
 * A job on the board: its name, whether it is in order, and the jobs inside it.
 */

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { useNodeProblems } from "../hooks/useNodeProblems";
import { useSchema } from "../hooks/useSchema";
import { shortName } from "../model/newJob";
import type { JobNode } from "../model/graph";
import { useAppDispatch } from "../store/hooks";
import { enterNested } from "../store/slices/graphSlice";
import { setSideTab } from "../store/slices/uiSlice";

export default function FancyJobNode({
  id,
  data,
  selected,
}: NodeProps<JobNode>) {
  const dispatch = useAppDispatch();
  const { job, nested } = data;
  const { kinds } = useSchema(job.function);
  const problems = useNodeProblems(id, data);
  const count = problems.own.length + problems.fromServer.length;
  const state = count > 0 ? "invalid" : problems.inside > 0 ? "inside" : "ok";

  const badge = {
    ok: { text: "✓", label: "In order", className: "text-bg-success" },
    invalid: {
      text: `✗ ${count}`,
      label: `${count} problem${count === 1 ? "" : "s"}`,
      className: "text-bg-danger",
    },
    inside: {
      text: `! ${problems.inside}`,
      label: `${problems.inside} problem${problems.inside === 1 ? "" : "s"} in the jobs inside`,
      className: "text-bg-warning",
    },
  }[state];

  return (
    <div
      className={`job-node ${selected ? "selected" : ""} ${job.virtual ? "virtual" : ""}`}
      data-testid="job-node"
      data-state={state}
      onDoubleClick={() => dispatch(setSideTab("job"))}
    >
      <Handle type="target" position={Position.Top} />

      <div className="job-node-header">
        <strong className="job-node-name">
          {job.name || shortName(job.function)}
        </strong>
        <span
          className={`badge ${badge.className}`}
          role="img"
          aria-label={badge.label}
          title={[...problems.own, ...problems.fromServer].join("\n")}
        >
          {badge.text}
        </span>
      </div>
      <div className="job-node-function" title={job.function}>
        {shortName(job.function)}
      </div>

      {Object.keys(kinds).map((param) => {
        const inner = nested[param];
        const label =
          inner === undefined
            ? `${param}: none`
            : kinds[param] === "list"
              ? `${param}: ${inner.nodes.length} job${inner.nodes.length === 1 ? "" : "s"}`
              : `${param}: ${inner.nodes.length === 0 ? "none" : "1 job"}`;
        return (
          <button
            key={param}
            type="button"
            className="btn btn-sm btn-outline-secondary nested-chip nodrag"
            onClick={(event) => {
              event.stopPropagation();
              dispatch(enterNested({ nodeId: id, param, kind: kinds[param] }));
            }}
          >
            {label} ▸
          </button>
        );
      })}

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
