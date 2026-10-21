/** Everything which is wrong with the pipeline, at every depth. */
import { useMemo } from "react";
import { collectProblems, jobLabel } from "../model/problems";
import { levelAt } from "../model/graph";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { openNode } from "../store/slices/graphSlice";
import { setMainTab, setSideTab } from "../store/slices/uiSlice";

export default function ProblemsPanel() {
  const dispatch = useAppDispatch();
  const root = useAppSelector((state) => state.graph.root);
  const schemas = useAppSelector((state) => state.jobSchemas.schemas);
  const { byNode, unmapped, status, error } = useAppSelector(
    (state) => state.validation,
  );

  const entries = useMemo(
    () => collectProblems(root, schemas, byNode),
    [root, schemas, byNode],
  );

  const whereIs = (path: { nodeId: string; param: string }[]) =>
    path
      .map((step, depth) => {
        const parent = levelAt(root, path.slice(0, depth));
        const node = parent?.nodes.find((n) => n.id === step.nodeId);
        return node ? jobLabel(node) : "?";
      })
      .join(" › ");

  return (
    <div className="p-3" data-testid="problems-panel">
      {status === "failed" && (
        <p role="alert" className="text-danger small">
          The pipeline could not be checked by the server: {error}
        </p>
      )}
      {unmapped.length > 0 && (
        <>
          <h2 className="h6">The pipeline</h2>
          <ul className="small text-danger">
            {unmapped.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </>
      )}
      {entries.length > 0 && <h2 className="h6">Jobs</h2>}
      <ul className="list-unstyled">
        {entries.map(({ path, node, messages }) => (
          <li key={node.id} className="mb-2">
            <button
              type="button"
              className="btn btn-link p-0 text-start"
              onClick={() => {
                dispatch(setMainTab("editor"));
                dispatch(openNode({ path, nodeId: node.id }));
                dispatch(setSideTab("job"));
              }}
            >
              {path.length > 0 ? `${whereIs(path)} › ` : ""}
              {jobLabel(node)}
            </button>
            <ul className="small text-danger">
              {messages.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
      {entries.length === 0 && unmapped.length === 0 && status !== "failed" && (
        <p className="text-success small">No problems found.</p>
      )}
    </div>
  );
}
