import { useEffect, useMemo, useRef } from "react";
import { graphToConfig } from "../model/convert";
import { mapServerErrors } from "../model/errors";
import api, { errorMessage } from "../services/api";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  checkFailed,
  checked,
  checking,
} from "../store/slices/validationSlice";

export const VALIDATE_DELAY_MS = 500;

/** The config of the pipeline as it is now. */
export const useConfig = () => {
  const root = useAppSelector((state) => state.graph.root);
  const pipeline = useAppSelector((state) => state.graph.pipeline);
  return useMemo(() => graphToConfig(root, pipeline), [root, pipeline]);
};

/**
 * Have the api check the pipeline a moment after the user stopped changing it,
 * and keep what it says in the store.
 */
export const useValidation = (): void => {
  const dispatch = useAppDispatch();
  const root = useAppSelector((state) => state.graph.root);
  const config = useConfig();
  const latest = useRef(0);
  const hasToken = useAppSelector((state) => !state.auth.needsToken);

  useEffect(() => {
    if (config.jobs.length === 0 || !hasToken) return;
    const request = (latest.current += 1);
    const timer = setTimeout(async () => {
      dispatch(checking());
      try {
        const response = await api.post("/config/validate", config);
        // an answer about an older pipeline is of no use
        if (request !== latest.current) return;
        const { valid, errors } = response.data as {
          valid: boolean;
          errors: string[];
        };
        dispatch(checked({ valid, ...mapServerErrors(root, errors) }));
      } catch (error) {
        if (request === latest.current)
          dispatch(checkFailed(errorMessage(error)));
      }
    }, VALIDATE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [config, root, dispatch, hasToken]);
};
