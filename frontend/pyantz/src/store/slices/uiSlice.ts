/**
 * Stores state that affects what shows on screen.
 */

import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

export interface ContextMenuOptions {
    showContextMenu: boolean;
    contextMenuPosition: {x: Number, y: Number};
    editJobId: null | string;
}

const initialContextMenu: () => ContextMenuOptions = () => ({
    showContextMenu: false,
    contextMenuPosition: {x: 0, y: 0},
    editJobId: null,
});

export interface UpdateContextMenuAction {
    position: {x: Number, y: Number};
}

export interface UiOptions {
    // if true, show the available jobs retrieved from the backend
    // used for a user to add a job
    showJobOptions: boolean;
    contextMenu: ContextMenuOptions;
}

const initialState: UiOptions = {
    showJobOptions: false,
    contextMenu: initialContextMenu(),

}

export const uiOptions = createSlice({
    name: "uiOptions",
    initialState,
    reducers: {
        showJobOptions: (state) => {
            state.showJobOptions = true;
        },
        hideJobOptions: (state) => {
            state.showJobOptions = false;
        },
        hideContextMenu: (state) => {
            state.contextMenu = initialContextMenu();
        },
        showContextMenu: (state, action: PayloadAction<UpdateContextMenuAction>) => {
            state.contextMenu.showContextMenu = true;
            state.contextMenu.contextMenuPosition = action.payload.position;
        },
        addJobToContextMenu: (state, action: PayloadAction<string>) => {
            state.contextMenu.editJobId = action.payload;
        }
    }
})

export const {
    showJobOptions,
    hideJobOptions,
    hideContextMenu,
    showContextMenu,
    addJobToContextMenu,
} = uiOptions.actions

export default uiOptions.reducer;
