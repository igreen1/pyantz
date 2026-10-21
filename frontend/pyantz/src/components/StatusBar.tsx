/** What the server thinks of the pipeline, and the token if there is one. */
import { setToken } from "../services/api";
import { tokenForgotten } from "../store/actions";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { setSideTab } from "../store/slices/uiSlice";

const TEXT = {
  idle: "Not checked",
  checking: "Checking…",
  valid: "Valid",
  invalid: "Has problems",
  failed: "Check failed",
} as const;

const STYLE = {
  idle: "text-bg-secondary",
  checking: "text-bg-info",
  valid: "text-bg-success",
  invalid: "text-bg-danger",
  failed: "text-bg-warning",
} as const;

export default function StatusBar() {
  const dispatch = useAppDispatch();
  const status = useAppSelector((state) => state.validation.status);
  const hasToken = useAppSelector((state) => state.auth.hasToken);

  return (
    <div className="d-flex align-items-center gap-2 ms-auto">
      <button
        type="button"
        className={`badge border-0 ${STYLE[status]}`}
        data-testid="validation-status"
        onClick={() => dispatch(setSideTab("problems"))}
        title="Show the problems"
      >
        {TEXT[status]}
      </button>
      {hasToken && (
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary"
          onClick={() => {
            setToken(null);
            dispatch(tokenForgotten());
          }}
        >
          Forget token
        </button>
      )}
    </div>
  );
}
