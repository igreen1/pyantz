import { useCallback } from "react";
import { useReactFlow } from "@xyflow/react";
import { createJobNode } from "../model/newJob";
import { useAppDispatch, useAppStore } from "../store/hooks";
import {
  addNode,
  selectAddJobBlock,
  selectOpenLevel,
} from "../store/slices/graphSlice";
import {
  setMainTab,
  setNextJobPosition,
  setSideTab,
  showNotice,
  type Point,
} from "../store/slices/uiSlice";

export type AddJob = (fn: string, position?: Point) => void;

/**
 * Get a function which adds a job to the open level.
 *
 * It goes where it is given, else where the user last asked for one (the context
 * menu), else the middle of the board.
 */
export const useAddJob = (): AddJob => {
  const dispatch = useAppDispatch();
  const store = useAppStore();
  const { screenToFlowPosition } = useReactFlow();

  return useCallback(
    (fn, position) => {
      const state = store.getState();
      const blocked = selectAddJobBlock(state);
      if (blocked) {
        dispatch(showNotice({ kind: "error", text: blocked }));
        return;
      }
      const level = selectOpenLevel(state);
      let at = position ?? state.uiOptions.nextJobPosition;
      if (!at) {
        const middle = screenToFlowPosition({
          x: window.innerWidth / 2,
          y: window.innerHeight / 2,
        });
        // each job a little aside of the last, so that they don't hide each other
        const shift = 24 * (level.nodes.length % 6);
        at = { x: middle.x + shift, y: middle.y + shift };
      }
      dispatch(setNextJobPosition(null));
      dispatch(
        addNode(
          createJobNode({
            fn,
            schema: state.jobSchemas.schemas[fn],
            position: at,
            level,
          }),
        ),
      );
      dispatch(setSideTab("job"));
      dispatch(setMainTab("editor"));
    },
    [dispatch, store, screenToFlowPosition],
  );
};
