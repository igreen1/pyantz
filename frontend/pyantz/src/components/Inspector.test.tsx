import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { graphToConfig } from "../model/convert";
import { selectNode, selectOpenLevel } from "../store/slices/graphSlice";
import { loadedStore, renderWithStore, withConfig } from "../test/render";
import Inspector from "./Inspector";

const MKDIR = "pyantz.jobs.files.simple.mkdir";
const LOOP = "pyantz.jobs.wrappers.loops.local_for_loop";

const setup = (jobs: object[], select = "n1") => {
  const store = withConfig(loadedStore(), { jobs });
  store.dispatch(selectNode(select));
  renderWithStore(<Inspector />, store);
  const job = (index = 0) =>
    selectOpenLevel(store.getState()).nodes[index].data.job;
  return { store, job, user: userEvent.setup() };
};

describe("Inspector", () => {
  it("asks for a job to be selected", () => {
    const store = withConfig(loadedStore(), { jobs: [] });
    renderWithStore(<Inspector />, store);

    expect(screen.getByText(/Select a job on the board/)).toBeInTheDocument();
  });

  it("renames the job, and the new name is kept (T3.5)", async () => {
    const { job, user } = setup([
      { function: MKDIR, name: "first", parameters: { dir_path: "d" } },
    ]);

    await user.clear(screen.getByLabelText("Name"));
    await user.type(screen.getByLabelText("Name"), "renamed");

    expect(job().name).toBe("renamed");
  });

  it("leaves the name out when it is emptied", async () => {
    const { job, user } = setup([
      { function: MKDIR, name: "first", parameters: { dir_path: "d" } },
    ]);

    await user.clear(screen.getByLabelText("Name"));

    expect(job().name).toBeUndefined();
  });

  it("edits the job id, and says when another job has it", async () => {
    const { job, user } = setup([
      { job_id: "a", function: MKDIR, parameters: { dir_path: "d" } },
      { job_id: "b", function: MKDIR, parameters: { dir_path: "d" } },
    ]);

    await user.clear(screen.getByLabelText("Job id"));
    await user.type(screen.getByLabelText("Job id"), "b");

    expect(job().job_id).toBe("b");
    expect(
      screen.getByText("Another job of this level has this id."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Job id")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });

  it("lists what is wrong with the parameters", () => {
    setup([{ function: MKDIR, parameters: {} }]);

    expect(screen.getByRole("list", { name: "Problems" })).toHaveTextContent(
      "dir_path is required",
    );
  });

  it("shows the problems the server found", () => {
    const { store } = setup([
      { job_id: "a", function: MKDIR, parameters: { dir_path: "d" } },
    ]);
    expect(screen.queryByRole("list", { name: "Problems" })).toBeNull();

    store.dispatch({
      type: "validation/checked",
      payload: {
        valid: false,
        unmapped: [],
        byNode: { n1: ["Job 'a' is wrong"] },
      },
    });

    return screen.findByText(/Job 'a' is wrong/);
  });

  it("sets retries, timeout, how it waits, and strictness; unset ones are left out", async () => {
    const { job, user, store } = setup([
      { function: MKDIR, parameters: { dir_path: "d" } },
    ]);
    await user.click(screen.getByText("More settings"));

    await user.type(screen.getByLabelText("Retries"), "3");
    await user.type(screen.getByLabelText("Timeout (seconds)"), "45");
    await user.selectOptions(
      screen.getByLabelText("Waits for its dependencies"),
      "afterany",
    );
    await user.click(screen.getByLabelText("Strict"));

    expect(job()).toMatchObject({
      max_retries: 3,
      timeout_seconds: 45,
      dependency_type: "afterany",
      strict: true,
    });

    await user.clear(screen.getByLabelText("Retries"));
    await user.selectOptions(
      screen.getByLabelText("Waits for its dependencies"),
      "afterok",
    );
    await user.click(screen.getByLabelText("Strict"));
    const { root, pipeline } = store.getState().graph;
    expect(graphToConfig(root, pipeline).jobs[0]).toEqual({
      function: MKDIR,
      name: undefined,
      timeout_seconds: 45,
      parameters: { dir_path: "d" },
    });
  });

  it("opens the jobs inside, when it has any", async () => {
    const { store, user } = setup([
      { function: LOOP, parameters: { num_iterations: 1, jobs: [] } },
    ]);

    await user.click(screen.getByRole("button", { name: "Open jobs (0)" }));

    expect(store.getState().graph.path).toEqual([
      { nodeId: "n1", param: "jobs" },
    ]);
  });

  it("has nothing to open for a job without jobs inside", () => {
    setup([{ function: MKDIR, parameters: { dir_path: "d" } }]);

    expect(screen.queryByText("Jobs inside")).toBeNull();
  });

  it("deletes the job", async () => {
    const { store, user } = setup([
      { function: MKDIR, parameters: { dir_path: "d" } },
    ]);

    await user.click(screen.getByRole("button", { name: "Delete job" }));

    expect(selectOpenLevel(store.getState()).nodes).toEqual([]);
  });

  it("starts fresh for the next job selected", async () => {
    const { store, user } = setup([
      { function: MKDIR, name: "one", parameters: { dir_path: "1" } },
      { function: MKDIR, name: "two", parameters: { dir_path: "2" } },
    ]);
    await user.type(screen.getByLabelText("Name"), "!");

    store.dispatch(selectNode("n2"));

    expect(await screen.findByDisplayValue("two")).toBeInTheDocument();
  });
});
