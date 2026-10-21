import { useEffect } from "react";
import { useAppDispatch, useAppStore } from "../store/hooks";
import { redo, selectNode, undo } from "../store/slices/graphSlice";
import { clearNotice, hideContextMenu } from "../store/slices/uiSlice";

const isTyping = (target: EventTarget | null): boolean => {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.isContentEditable ||
    ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
  );
};

/**
 * Keys for the whole page: undo and redo, and Escape to close what is open.
 * Delete is handled by the board, which knows what is selected.
 */
export const useShortcuts = (): void => {
  const dispatch = useAppDispatch();
  const store = useAppStore();

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        const { contextMenu, notice } = store.getState().uiOptions;
        if (contextMenu.showContextMenu) dispatch(hideContextMenu());
        else if (notice) dispatch(clearNotice());
        else if (!isTyping(event.target)) dispatch(selectNode(null));
        return;
      }
      if (isTyping(event.target) || !(event.ctrlKey || event.metaKey)) return;
      const key = event.key.toLowerCase();
      if (key === "z" && !event.shiftKey) {
        event.preventDefault();
        dispatch(undo());
      } else if (key === "y" || (key === "z" && event.shiftKey)) {
        event.preventDefault();
        dispatch(redo());
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [dispatch, store]);
};
