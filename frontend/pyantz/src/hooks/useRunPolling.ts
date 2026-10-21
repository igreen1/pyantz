import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { fetchRun } from "../store/slices/runSlice";

export const POLL_INTERVAL_MS = 1500;

/** While a run is going, ask how far it is; stop when it is over or the page closes. */
export const useRunPolling = (): void => {
  const dispatch = useAppDispatch();
  const runId = useAppSelector((state) => state.run.runId);
  const running = useAppSelector((state) => state.run.state === "running");
  const waiting = useAppSelector((state) => state.auth.needsToken);

  useEffect(() => {
    if (!runId || !running || waiting) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      await dispatch(fetchRun(runId));
      if (!stopped) timer = setTimeout(poll, POLL_INTERVAL_MS);
    };
    void poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [dispatch, runId, running, waiting]);
};
