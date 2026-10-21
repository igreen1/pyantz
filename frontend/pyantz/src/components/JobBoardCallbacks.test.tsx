import { beforeEach, describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import type { ReactFlowProps } from "@xyflow/react";
import { Provider } from "react-redux";
import { selectOpenLevel } from "../store/slices/graphSlice";
import { loadedStore, withConfig } from "../test/render";
import type { AppStore } from "../store/store";
import JobBoard from "./JobBoard";

// jsdom can't drag, so the board is given a stand in for react flow which keeps the
// props it is given; calling them is what a drag, a delete key or a click would do
let flow: ReactFlowProps;
vi.mock("@xyflow/react", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@xyflow/react")>()),
  ReactFlow: (props: ReactFlowProps) => {
    flow = props;
    return <div data-testid="flow" />;
  },
  useReactFlow: () => ({
    screenToFlowPosition: (p: { x: number; y: number }) => p,
  }),
}));

const NOP = "pyantz.jobs.testing.nop.do_nothing";

let store: AppStore;
beforeEach(() => {
  store = withConfig(loadedStore(), {
    jobs: [
      { job_id: "a", function: NOP, parameters: {} },
      { job_id: "b", function: NOP, parameters: {} },
      { job_id: "c", function: NOP, parameters: {}, depends_on: ["b"] },
    ],
  });
  render(
    <Provider store={store}>
      <JobBoard />
    </Provider>,
  );
});

const edges = () =>
  selectOpenLevel(store.getState()).edges.map((e) => `${e.source}>${e.target}`);
const connection = (source: string, target: string) => ({
  source,
  target,
  sourceHandle: null,
  targetHandle: null,
});

describe("JobBoard callbacks", () => {
  it("draws the open level", () => {
    expect(flow.nodes).toHaveLength(3);
    expect(flow.edges).toHaveLength(1);
  });

  it("adds a dependency which is made", () => {
    flow.onConnect?.(connection("n1", "n2"));

    expect(edges()).toContain("n1>n2");
  });

  it("says why a dependency which is refused is refused", () => {
    flow.onConnect?.(connection("n3", "n2")); // c depends on b: this is a circle

    expect(edges()).toEqual(["n2>n3"]);
    expect(store.getState().uiOptions.notice).toMatchObject({
      kind: "error",
      text: expect.stringContaining("circle"),
    });
  });

  it("tells react flow which connections are valid", () => {
    expect(flow.isValidConnection?.(connection("n1", "n2") as never)).toBe(
      true,
    );
    expect(flow.isValidConnection?.(connection("n3", "n2") as never)).toBe(
      false,
    );
    expect(flow.isValidConnection?.(connection("n1", "n1") as never)).toBe(
      false,
    );
  });

  it("explains a connection which was let go on a job which can't be connected to", () => {
    const fromNode = { id: "n3" };
    const toNode = { id: "n2" };

    flow.onConnectEnd?.(new MouseEvent("mouseup"), {
      isValid: false,
      fromNode,
      toNode,
    } as never);

    expect(store.getState().uiOptions.notice?.text).toContain("circle");
  });

  it("is quiet when a connection was let go on nothing, or was fine", () => {
    flow.onConnectEnd?.(new MouseEvent("mouseup"), {
      isValid: null,
      fromNode: { id: "n1" },
      toNode: null,
    } as never);
    flow.onConnectEnd?.(new MouseEvent("mouseup"), {
      isValid: true,
      fromNode: { id: "n1" },
      toNode: { id: "n2" },
    } as never);

    expect(store.getState().uiOptions.notice).toBeNull();
  });

  it("deletes jobs and their dependencies as one step, and keeps react flow from doing it too", async () => {
    const answer = await flow.onBeforeDelete?.({
      nodes: [{ id: "n2" }],
      edges: [{ id: "en2->n3" }],
    } as never);

    expect(answer).toBe(false);
    expect(selectOpenLevel(store.getState()).nodes.map((n) => n.id)).toEqual([
      "n1",
      "n3",
    ]);
    expect(edges()).toEqual([]);
    store.dispatch({ type: "graph/undo" });
    expect(edges()).toEqual(["n2>n3"]);
  });

  it("passes on what react flow reports about jobs and dependencies", () => {
    flow.onNodesChange?.([
      { id: "n1", type: "position", position: { x: 5, y: 6 } },
    ]);
    flow.onEdgesChange?.([{ id: "en2->n3", type: "remove" }]);

    expect(selectOpenLevel(store.getState()).nodes[0].position).toEqual({
      x: 5,
      y: 6,
    });
    expect(edges()).toEqual([]);
  });

  it("closes the menu when the board is clicked or moved", () => {
    flow.onContextMenu?.({
      preventDefault: () => undefined,
      clientX: 1,
      clientY: 2,
      target: document.body,
    } as never);
    expect(store.getState().uiOptions.contextMenu.showContextMenu).toBe(true);

    flow.onPaneClick?.({} as never);
    expect(store.getState().uiOptions.contextMenu.showContextMenu).toBe(false);

    flow.onContextMenu?.({
      preventDefault: () => undefined,
      clientX: 1,
      clientY: 2,
      target: document.body,
    } as never);
    flow.onMoveStart?.(null as never, { x: 0, y: 0, zoom: 1 });
    expect(store.getState().uiOptions.contextMenu.showContextMenu).toBe(false);
  });

  it("does not fit the view for an empty board, which would move it under the next job", () => {
    expect(flow.fitView).toBe(true); // opened with jobs

    const empty = withConfig(loadedStore(), { jobs: [] });
    render(
      <Provider store={empty}>
        <JobBoard />
      </Provider>,
    );

    expect(flow.fitView).toBe(false);
  });
});
