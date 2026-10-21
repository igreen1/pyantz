import { describe, expect, it } from "vitest";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { loadedStore, renderWithStore } from "../test/render";
import { dumpedJobs } from "../test/fixtures";
import { withConfig } from "../test/render";
import { makeStore } from "../store/store";
import { enterNested, selectOpenLevel } from "../store/slices/graphSlice";
import { focusSearch } from "../store/slices/uiSlice";
import Palette from "./Palette";
import { JOB_DRAG_TYPE } from "./JobBoard";

const MKDIR = "pyantz.jobs.files.simple.mkdir";
const IF_ELSE = "pyantz.jobs.branching.if_else.if_else";

describe("Palette", () => {
  it("lists the jobs in groups, with a description", () => {
    renderWithStore(<Palette />);

    const files = screen.getByRole("region", { name: "files" });
    expect(within(files).getByText(MKDIR)).toBeInTheDocument();
    expect(screen.getAllByRole("button").length).toBe(
      Object.keys(dumpedJobs).length,
    );
    expect(
      screen.getByRole("region", { name: "branching" }),
    ).toBeInTheDocument();
  });

  it("shows only the jobs which match the search, in name or description (T3.1)", async () => {
    const user = userEvent.setup();
    renderWithStore(<Palette />);

    await user.type(screen.getByLabelText("Search jobs"), "mkdir");

    const shown = screen.getAllByRole("button");
    expect(shown.length).toBeGreaterThan(0);
    expect(shown.length).toBeLessThan(5);
    for (const job of shown) {
      const name = job.querySelector(".palette-job-path")?.textContent ?? "";
      const description = dumpedJobs[name].description;
      expect(`${name} ${description}`.toLowerCase()).toContain("mkdir");
    }
  });

  it("matches every word, in any order", async () => {
    const user = userEvent.setup();
    renderWithStore(<Palette />);

    await user.type(screen.getByLabelText("Search jobs"), "simple FILES");

    const names = screen
      .getAllByRole("button")
      .map((job) => job.querySelector(".palette-job-path")?.textContent);
    expect(names).toContain(MKDIR);
    expect(names.every((name) => name?.includes("files.simple"))).toBe(true);
  });

  it("says when nothing matches", async () => {
    const user = userEvent.setup();
    renderWithStore(<Palette />);

    await user.type(screen.getByLabelText("Search jobs"), "zzzzzz");

    expect(screen.getByText("No job matches.")).toBeInTheDocument();
  });

  it("adds a job with its required parameters filled in as empty, on a click", async () => {
    const user = userEvent.setup();
    const { store } = renderWithStore(<Palette />);

    await user.click(screen.getByTitle(dumpedJobs[MKDIR].description));

    const [node] = selectOpenLevel(store.getState()).nodes;
    expect(node.data.job).toMatchObject({
      function: MKDIR,
      name: "mkdir",
      parameters: { dir_path: null },
    });
    expect(node.selected).toBe(true);
    expect(store.getState().uiOptions.sideTab).toBe("job");
  });

  it("gives jobs of the same kind different names and ids", async () => {
    const user = userEvent.setup();
    const { store } = renderWithStore(<Palette />);
    const mkdir = screen.getByTitle(dumpedJobs[MKDIR].description);

    await user.click(mkdir);
    await user.click(mkdir);

    const jobs = selectOpenLevel(store.getState()).nodes.map((n) => n.data.job);
    expect(jobs.map((job) => job.name)).toEqual(["mkdir", "mkdir_2"]);
    expect(new Set(jobs.map((job) => job.job_id)).size).toBe(2);
  });

  it("makes nested parameters which are required, empty (T4.1)", async () => {
    const user = userEvent.setup();
    const { store } = renderWithStore(<Palette />);
    await user.type(screen.getByLabelText("Search jobs"), "local_for_loop");

    await user.click(screen.getByRole("button", { name: /local_for_loop/ }));

    const [node] = selectOpenLevel(store.getState()).nodes;
    expect(node.data.nested.jobs).toEqual({
      kind: "list",
      nodes: [],
      edges: [],
    });
    expect(node.data.job.parameters).toEqual({ num_iterations: null });
  });

  it("puts the next job where the user asked for one", async () => {
    const user = userEvent.setup();
    const store = loadedStore();
    store.dispatch({
      type: "uiOptions/setNextJobPosition",
      payload: { x: 7, y: 9 },
    });
    renderWithStore(<Palette />, store);

    await user.click(screen.getByTitle(dumpedJobs[MKDIR].description));

    expect(selectOpenLevel(store.getState()).nodes[0].position).toEqual({
      x: 7,
      y: 9,
    });
    expect(store.getState().uiOptions.nextJobPosition).toBeNull();
  });

  it("can be dragged, carrying the name of the job", () => {
    renderWithStore(<Palette />);
    const data: Record<string, string> = {};

    fireEvent.dragStart(screen.getByTitle(dumpedJobs[MKDIR].description), {
      dataTransfer: {
        setData: (type: string, value: string) => (data[type] = value),
      },
    });

    expect(data[JOB_DRAG_TYPE]).toBe(MKDIR);
  });

  it("takes the focus when asked for it", () => {
    const { store } = renderWithStore(<Palette />);

    store.dispatch(focusSearch());

    return waitFor(() =>
      expect(screen.getByLabelText("Search jobs")).toHaveFocus(),
    );
  });

  it("says it is loading, and why it failed", () => {
    const { rerender } = renderWithStore(<Palette />, makeStore());
    expect(screen.getByRole("status")).toHaveTextContent("Loading jobs");
    rerender(<></>);

    renderWithStore(
      <Palette />,
      makeStore({
        availableJobs: {
          items: [],
          descriptions: [],
          status: "failed",
          error: "Network Error",
        },
      }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Network Error");
  });

  describe("inside a parameter which holds one job", () => {
    const full = (parameters: object) => {
      const store = withConfig(loadedStore(), {
        jobs: [{ job_id: "if", function: IF_ELSE, parameters }],
      });
      const [node] = selectOpenLevel(store.getState()).nodes;
      store.dispatch(
        enterNested({ nodeId: node.id, param: "if_true", kind: "single" }),
      );
      return store;
    };

    it("offers the jobs while it is empty", async () => {
      const user = userEvent.setup();
      const { store } = renderWithStore(<Palette />, full({}));

      expect(screen.queryByText(/takes a single job/)).toBeNull();
      await user.click(screen.getByTitle(dumpedJobs[MKDIR].description));

      expect(selectOpenLevel(store.getState()).nodes).toHaveLength(1);
    });

    it("turns the jobs off once it has its job, and says why", async () => {
      const user = userEvent.setup();
      const store = full({
        if_true: { job_id: "t", function: MKDIR, parameters: {} },
      });
      renderWithStore(<Palette />, store);

      expect(screen.getByRole("status")).toHaveTextContent(
        "if_true takes a single job",
      );
      const job = screen.getByTitle(dumpedJobs[MKDIR].description);
      expect(job).toBeDisabled();
      expect(job).toHaveAttribute("draggable", "false");
      await user.click(job);

      expect(selectOpenLevel(store.getState()).nodes).toHaveLength(1);
    });
  });
});
