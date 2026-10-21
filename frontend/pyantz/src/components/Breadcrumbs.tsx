/** Where in the nested pipelines the board is, with a way back out. */
import { jobLabel } from "../model/problems";
import { levelAt } from "../model/graph";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { goToDepth } from "../store/slices/graphSlice";

export default function Breadcrumbs() {
  const dispatch = useAppDispatch();
  const root = useAppSelector((state) => state.graph.root);
  const path = useAppSelector((state) => state.graph.path);

  const crumbs = path.map((entry, index) => {
    const parent = levelAt(root, path.slice(0, index));
    const node = parent?.nodes.find((n) => n.id === entry.nodeId);
    return `${node ? jobLabel(node) : "?"} › ${entry.param}`;
  });
  const names = ["Pipeline", ...crumbs];

  return (
    <nav aria-label="Pipeline level" className="breadcrumbs">
      <ol className="breadcrumb mb-0">
        {names.map((name, depth) => (
          <li
            key={depth}
            className={`breadcrumb-item ${depth === names.length - 1 ? "active" : ""}`}
            aria-current={depth === names.length - 1 ? "page" : undefined}
          >
            {depth === names.length - 1 ? (
              name
            ) : (
              <button
                type="button"
                className="btn btn-link p-0"
                onClick={() => dispatch(goToDepth(depth))}
              >
                {name}
              </button>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
