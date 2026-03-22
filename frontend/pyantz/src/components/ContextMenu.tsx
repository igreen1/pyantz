/** A helpful context menu that opens when the user right clicks. */

import "./ContextMenu.css"

import { useAppDispatch, useAppSelector } from "../store/hooks";
import { hideContextMenu } from "../store/slices/uiSlice";
import { removeJob } from "../store/slices/currentPipeline";

export interface ContextMenuItem {
    name: string,
    onClick: () => void
}

interface ContextMenuProps {
    items: ContextMenuItem[],
}

// ContextMenu.component.jsx
export default function ContextMenu({ items }: ContextMenuProps) {
  const dispatch = useAppDispatch();

    const visible = useAppSelector((state) => state.uiOptions.contextMenu.showContextMenu);
    const x = useAppSelector((state) => state.uiOptions.contextMenu.contextMenuPosition.x);
    const y = useAppSelector((state) => state.uiOptions.contextMenu.contextMenuPosition.y);
    const editJobId = useAppSelector((state) => state.uiOptions.contextMenu.editJobId);

    if (!visible) return null;

    let dynamicItems = []
    if (editJobId !== null) {
        dynamicItems.push({
            name: `Edit Job (${editJobId})`,
            onClick: () => {
                
            }
        });
        dynamicItems.push({
            name: `Delete Job (${editJobId})`,
            onClick: () => {
                dispatch(hideContextMenu());
                dispatch(removeJob(editJobId))
            }
        })
    }

    const finalItems = [
        ...items,
        ...dynamicItems
    ]

    return (
        <div
            className="job-board-context-menu"
            style={{ top: `${y}px`, left: `${x}px`, position: 'absolute' }}
        >
            {finalItems.map((item, idx) => (
                <div key={idx} onClick={item.onClick} className="job-board-context-menu-item">
                    {item.name}
                </div>
            ))}
        </div>
    );
};

