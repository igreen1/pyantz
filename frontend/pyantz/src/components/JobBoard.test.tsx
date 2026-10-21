import { describe, expect, it } from "vitest";
import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { loadedStore, renderWithStore, withConfig } from "../test/render";
import JobBoard, { JOB_DRAG_TYPE } from "./JobBoard";
import { enterNested, selectOpenLevel } from "../store/slices/graphSlice";

const MKDIR = "pyantz.jobs.files.simple.mkdir";
const LOOP = "pyantz.jobs.wrappers.loops.local_for_loop";

const board = (jobs: object[]) =>
  renderWithStore(<JobBoard />, withConfig(loadedStore(), { jobs }));

describe("JobBoard", () => {
  it("shows the jobs of the pipeline", () => {
    board([
      {
        job_id: "a",
        name: "make",
        function: MKDIR,
        parameters: { dir_path: "d" },
      },
      {
        job_id: "b",
        function: MKDIR,
        parameters: { dir_path: "d" },
        depends_on: ["a"],
      },
    ]);

    const nodes = screen.getAllByTestId("job-node");
    expect(nodes).toHaveLength(2);
    expect(nodes[0]).toHaveTextContent("make");
    expect(nodes[1]).toHaveTextContent("mkdir");
  });

  it("marks a job which is in order, and one which is not", () => {
    board([
      { function: MKDIR, parameters: { dir_path: "d" } },
      { function: MKDIR, parameters: {} },
    ]);

    const [fine, broken] = screen.getAllByTestId("job-node");
    expect(fine).toHaveAttribute("data-state", "ok");
    expect(within(fine).getByLabelText("In order")).toBeInTheDocument();
    expect(broken).toHaveAttribute("data-state", "invalid");
    expect(within(broken).getByLabelText("1 problem")).toBeInTheDocument();
  });

  it("marks a job with problems in the jobs inside it", () => {
    board([
      {
        function: LOOP,
        parameters: {
          num_iterations: 1,
          jobs: [{ function: MKDIR, parameters: {} }],
        },
      },
    ]);

    const [loop] = screen.getAllByTestId("job-node");
    expect(loop).toHaveAttribute("data-state", "inside");
    expect(
      within(loop).getByLabelText("1 problem in the jobs inside"),
    ).toBeInTheDocument();
  });

  it("shows the jobs inside a job as a button which opens them, and a way back (T4.5)", async () => {
    const user = userEvent.setup();
    const { store } = board([
      {
        function: LOOP,
        parameters: {
          num_iterations: 1,
          jobs: [
            { name: "inner", function: MKDIR, parameters: { dir_path: "d" } },
            { function: MKDIR, parameters: { dir_path: "d" } },
          ],
        },
      },
    ]);

    await user.click(screen.getByText(/jobs: 2 jobs/));

    expect(screen.getAllByTestId("job-node")).toHaveLength(2);
    const trail = screen.getByRole("navigation", { name: "Pipeline level" });
    expect(trail).toHaveTextContent("local_for_loop › jobs");
    expect(store.getState().graph.path).toHaveLength(1);

    await user.click(within(trail).getByRole("button", { name: "Pipeline" }));
    expect(screen.getAllByTestId("job-node")).toHaveLength(1);
    expect(trail).toHaveTextContent(/^Pipeline$/);
  });

  it("says how many jobs a job holds, or that it holds none", () => {
    board([{ function: LOOP, parameters: { num_iterations: 1 } }]);

    expect(screen.getByText(/jobs: none/)).toBeInTheDocument();
  });

  it("adds a job dropped on it, where it was dropped", () => {
    const { store } = board([]);
    const canvas = document.querySelector(".job-board-canvas") as HTMLElement;

    fireEvent.drop(canvas, {
      clientX: 120,
      clientY: 80,
      dataTransfer: {
        getData: (type: string) => (type === JOB_DRAG_TYPE ? MKDIR : ""),
      },
    });

    const [node] = selectOpenLevel(store.getState()).nodes;
    expect(node.data.job.function).toBe(MKDIR);
  });

  it("takes no second job dropped into a parameter which holds one", () => {
    const store = withConfig(loadedStore(), {
      jobs: [
        {
          job_id: "if",
          function: "pyantz.jobs.branching.if_else.if_else",
          parameters: {
            if_true: { job_id: "t", function: MKDIR, parameters: {} },
          },
        },
      ],
    });
    const [node] = selectOpenLevel(store.getState()).nodes;
    store.dispatch(
      enterNested({ nodeId: node.id, param: "if_true", kind: "single" }),
    );
    renderWithStore(<JobBoard />, store);
    const canvas = document.querySelector(".job-board-canvas") as HTMLElement;
    const dataTransfer = {
      types: [JOB_DRAG_TYPE],
      getData: () => MKDIR,
      dropEffect: "none",
    };

    // not a place to drop: the drag is not accepted
    expect(fireEvent.dragOver(canvas, { dataTransfer })).toBe(true);
    expect(dataTransfer.dropEffect).toBe("none");
    fireEvent.drop(canvas, { dataTransfer });

    expect(selectOpenLevel(store.getState()).nodes).toHaveLength(1);
    expect(store.getState().uiOptions.notice?.text).toMatch(
      /takes a single job/,
    );
  });

  it("ignores a drop of something else", () => {
    const { store } = board([]);
    const canvas = document.querySelector(".job-board-canvas") as HTMLElement;

    fireEvent.drop(canvas, { dataTransfer: { getData: () => "" } });

    expect(selectOpenLevel(store.getState()).nodes).toEqual([]);
  });

  it("opens the context menu on a right click, with what can be done", async () => {
    const user = userEvent.setup();
    const { store } = board([
      { function: MKDIR, parameters: { dir_path: "d" } },
    ]);

    await user.pointer({
      keys: "[MouseRight]",
      target: screen.getByTestId("job-node"),
    });

    expect(store.getState().uiOptions.contextMenu.showContextMenu).toBe(true);
    expect(store.getState().uiOptions.contextMenu.editJobId).toBe("n1");
    expect(
      screen.getByRole("menuitem", { name: "Edit Job" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("menuitem", { name: "Delete Job" }),
    ).toBeInTheDocument();
  });
});
