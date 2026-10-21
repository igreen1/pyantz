/** Asks for the api token when the server wants one. */
import { useState, type FormEvent } from "react";
import { setToken } from "../services/api";
import { tokenSupplied } from "../store/actions";
import { useAppDispatch, useAppSelector } from "../store/hooks";

export default function TokenPrompt() {
  const dispatch = useAppDispatch();
  const { needsToken, rejected } = useAppSelector((state) => state.auth);
  const [token, setText] = useState("");

  if (!needsToken) return null;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setToken(token.trim());
    setText("");
    dispatch(tokenSupplied());
  };

  return (
    <div className="dialog-backdrop">
      <form
        className="dialog card"
        role="dialog"
        aria-modal="true"
        aria-label="API token"
        onSubmit={submit}
      >
        <div className="card-body">
          <h2 className="h6">This server asks for a token</h2>
          <p className="small text-secondary">
            Set by <code>PYANTZ_API_TOKEN</code> where the server runs. It is
            kept for this tab only.
          </p>
          {rejected && (
            <p role="alert" className="text-danger small">
              That token was not accepted.
            </p>
          )}
          <label htmlFor="api-token" className="form-label small">
            API token
          </label>
          <input
            id="api-token"
            type="password"
            autoComplete="off"
            className="form-control form-control-sm"
            value={token}
            onChange={(event) => setText(event.target.value)}
            autoFocus
          />
          <button
            type="submit"
            className="btn btn-primary btn-sm mt-2"
            disabled={!token.trim()}
          >
            Use token
          </button>
        </div>
      </form>
    </div>
  );
}
