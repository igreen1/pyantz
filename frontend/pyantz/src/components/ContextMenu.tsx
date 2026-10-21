/** A helpful context menu that opens when the user right clicks. */

import "./ContextMenu.css";

import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  deleteJobNode,
  selectAddJobBlock,
  selectNode,
} from "../store/slices/graphSlice";
import {
  focusSearch,
  hideContextMenu,
  setNextJobPosition,
  setSideTab,
} from "../store/slices/uiSlice";

export default function ContextMenu() {
  const dispatch = useAppDispatch();
  const menu = useAppSelector((state) => state.uiOptions.contextMenu);
  const blocked = useAppSelector(selectAddJobBlock);

  if (!menu.showContextMenu) return null;
  const { editJobId, boardPosition } = menu;

  const items: { name: string; onClick: () => void; disabled?: string }[] = [
    {
      name: "Add Job",
      disabled: blocked ?? undefined,
      onClick: () => {
        // the next job from the palette goes where the menu was opened
        dispatch(setNextJobPosition(boardPosition));
        dispatch(focusSearch());
      },
    },
  ];
  if (editJobId !== null) {
    items.push(
      {
        name: "Edit Job",
        onClick: () => {
          dispatch(selectNode(editJobId));
          dispatch(setSideTab("job"));
        },
      },
      { name: "Delete Job", onClick: () => dispatch(deleteJobNode(editJobId)) },
    );
  }

  return (
    <div
      className="job-board-context-menu"
      role="menu"
      style={{
        top: `${menu.contextMenuPosition.y}px`,
        left: `${menu.contextMenuPosition.x}px`,
        position: "fixed",
      }}
    >
      {items.map((item) => (
        <button
          key={item.name}
          type="button"
          role="menuitem"
          disabled={item.disabled !== undefined}
          title={item.disabled}
          onClick={() => {
            item.onClick();
            dispatch(hideContextMenu());
          }}
          className="job-board-context-menu-item"
        >
          {item.name}
        </button>
      ))}
    </div>
  );
}
