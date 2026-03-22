/** A helpful context menu that opens when the user right clicks. */

import "./ContextMenu.css"

interface ContextMenuItem {
    name: string,
    onClick: () => {}
}

interface ContextMenuProps {
    visible: boolean,
    x: Number,
    y: Number,
    items: ContextMenuItem[],
}

// ContextMenu.component.jsx
export default function ContextMenu({ visible, x, y, items }: ContextMenuProps) {
    if (!visible) return null;

    return (
        <div
            className="job-board-context-menu"
            style={{ top: `${y}px`, left: `${x}px`, position: 'absolute' }}
        >
            {items.map((item, idx) => (
                <div key={idx} onClick={item.onClick} className="job-board-context-menu-item">
                    {item.name}
                </div>
            ))}
        </div>
    );
};

