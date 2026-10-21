/**
 * Stores state that affects what shows on screen.
 */

import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

export interface Point {
  x: number;
  y: number;
}

export interface ContextMenuOptions {
  showContextMenu: boolean;
  // where on the screen the menu is drawn
  contextMenuPosition: Point;
  // where on the board the menu was opened, which is where a job is added from it
  boardPosition: Point | null;
  editJobId: null | string;
}

const initialContextMenu = (): ContextMenuOptions => ({
  showContextMenu: false,
  contextMenuPosition: { x: 0, y: 0 },
  boardPosition: null,
  editJobId: null,
});

export type SideTab = "job" | "pipeline" | "problems" | "run";
export type MainTab = "editor" | "compiled";

export interface Notice {
  // changes with each notice, so that the same text again is shown again
  id: number;
  kind: "error" | "info";
  text: string;
}

export interface UiOptions {
  contextMenu: ContextMenuOptions;
  sideTab: SideTab;
  mainTab: MainTab;
  notice: Notice | null;
  // where the next job added goes, if set by the user (e.g. dropped there)
  nextJobPosition: Point | null;
  // counts up when something asks for the palette search to get the focus
  focusSearch: number;
}

const initialState: UiOptions = {
  contextMenu: initialContextMenu(),
  sideTab: "job",
  mainTab: "editor",
  notice: null,
  nextJobPosition: null,
  focusSearch: 0,
};

let noticeCount = 0;

export const uiOptions = createSlice({
  name: "uiOptions",
  initialState,
  reducers: {
    hideContextMenu: (state) => {
      state.contextMenu = initialContextMenu();
    },
    showContextMenu: (
      state,
      action: PayloadAction<{
        position: Point;
        boardPosition: Point;
        // the job which was right clicked, if one was
        nodeId?: string;
      }>,
    ) => {
      state.contextMenu = {
        ...initialContextMenu(),
        showContextMenu: true,
        contextMenuPosition: action.payload.position,
        boardPosition: action.payload.boardPosition,
        editJobId: action.payload.nodeId ?? null,
      };
    },
    setSideTab: (state, action: PayloadAction<SideTab>) => {
      state.sideTab = action.payload;
    },
    setMainTab: (state, action: PayloadAction<MainTab>) => {
      state.mainTab = action.payload;
    },
    showNotice: (
      state,
      action: PayloadAction<{ kind: Notice["kind"]; text: string }>,
    ) => {
      noticeCount += 1;
      state.notice = { id: noticeCount, ...action.payload };
    },
    clearNotice: (state) => {
      state.notice = null;
    },
    setNextJobPosition: (state, action: PayloadAction<Point | null>) => {
      state.nextJobPosition = action.payload;
    },
    focusSearch: (state) => {
      state.focusSearch += 1;
    },
  },
});

export const {
  hideContextMenu,
  showContextMenu,
  setSideTab,
  setMainTab,
  showNotice,
  clearNotice,
  setNextJobPosition,
  focusSearch,
} = uiOptions.actions;

export default uiOptions.reducer;
