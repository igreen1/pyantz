/** The id of the last run, kept for this tab so that a reload can pick it up again. */
const RUN_KEY = "pyantz-run-id";

export const loadRunId = (): string | null => {
  try {
    return sessionStorage.getItem(RUN_KEY);
  } catch {
    return null;
  }
};

export const saveRunId = (runId: string | null): void => {
  try {
    if (runId === null) sessionStorage.removeItem(RUN_KEY);
    else sessionStorage.setItem(RUN_KEY, runId);
  } catch {
    // a run is then not remembered over a reload
  }
};
