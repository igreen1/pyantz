import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import api from "../services/api";
import { saveRunId } from "../services/session";
import { restoreRun } from "../store/slices/runSlice";
import { loadedStore, renderWithStore, withConfig } from "../test/render";
import RunPanel from "./RunPanel";

vi.mock("../services/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/api")>()),
  default: { get: vi.fn(), post: vi.fn() },
}));

const get = vi.mocked(api.get);
const post = vi.mocked(api.post);

const NOP = "pyantz.jobs.testing.nop.do_nothing";
const MKDIR = "pyantz.jobs.files.simple.mkdir";

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  saveRunId(null);
});

const setup = (
  jobs: object[] = [{ job_id: "a", function: NOP, parameters: {} }],
) => {
  const store = withConfig(loadedStore(), { jobs });
  renderWithStore(<RunPanel />, store);
  return { store, user: userEvent.setup() };
};

const run = () => screen.getByRole("button", { name: "Run" });

describe("RunPanel", () => {
  it("says the working directory is the server's", () => {
    setup();

    expect(
      screen.getByText(/in a directory the server chooses/),
    ).toBeInTheDocument();
  });

  it("can't run without a job", () => {
    setup([]);

    expect(run()).toBeDisabled();
    expect(screen.getByText("Add a job first.")).toBeInTheDocument();
  });

  it("can't run a pipeline with problems", () => {
    setup([{ function: MKDIR, parameters: {} }]);

    expect(run()).toBeDisabled();
    expect(screen.getByText("Fix the problems first.")).toBeInTheDocument();
  });

  it("sends the config, and shows the compiled view where the run is drawn", async () => {
    post.mockResolvedValue({ data: { run_id: "r1" } });
    get.mockResolvedValue({
      data: {
        run_id: "r1",
        state: "running",
        report: {
          total: 3,
          success: 1,
          error: 0,
          pending: 1,
          ready: 0,
          running: 1,
        },
        jobs: [{ job_id: "a", status: "success", details: null }],
      },
    });
    const { store, user } = setup();

    await user.click(run());

    expect(post).toHaveBeenCalledWith(
      "/runs",
      expect.objectContaining({
        jobs: [{ job_id: "a", function: NOP, parameters: {} }],
      }),
    );
    expect(store.getState().uiOptions.mainTab).toBe("compiled");
    expect(await screen.findByTestId("run-state")).toHaveTextContent("Running");
  });

  it("shows the report and each job", async () => {
    saveRunId("r1");
    const { store } = setup();
    store.dispatch(restoreRun());
    get.mockResolvedValue({
      data: {
        run_id: "r1",
        state: "failed",
        report: {
          total: 3,
          success: 1,
          error: 1,
          pending: 1,
          ready: 0,
          running: 0,
        },
        jobs: [
          { job_id: "a", status: "success", details: null },
          { job_id: "b", status: "error", details: "exit status 1" },
        ],
      },
    });
    const { fetchRun } = await import("../store/slices/runSlice");
    await store.dispatch(fetchRun("r1"));

    expect(await screen.findByTestId("run-state")).toHaveTextContent("Failed");
    expect(screen.getByTestId("run-report")).toHaveTextContent(
      "1 of 3 done · 0 running · 1 waiting · 1 failed",
    );
    expect(screen.getByRole("row", { name: /^b error/ })).toHaveTextContent(
      "exit status 1",
    );
    expect(run()).toBeEnabled();
  });

  it("shows why a run could not be started", async () => {
    post.mockRejectedValue(
      Object.assign(new Error("x"), {
        isAxiosError: true,
        response: {
          data: { detail: "Runs are disabled: set PYANTZ_ALLOWED_MODULES" },
        },
      }),
    );
    const { user } = setup();

    await user.click(run());

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "PYANTZ_ALLOWED_MODULES",
    );
    expect(screen.queryByTestId("run-state")).toBeNull();
  });

  it("reads the log, saying when only the end is shown", async () => {
    saveRunId("r1");
    const { store, user } = setup();
    store.dispatch(restoreRun());
    get.mockResolvedValueOnce({
      data: { run_id: "r1", state: "succeeded", report: null, jobs: [] },
    });
    const { fetchRun } = await import("../store/slices/runSlice");
    await store.dispatch(fetchRun("r1"));
    get.mockResolvedValue({
      data: { log: "did nothing :)\n", truncated: true },
    });

    await user.click(await screen.findByRole("button", { name: "Show log" }));

    expect(await screen.findByLabelText("Run log")).toHaveTextContent(
      "did nothing :)",
    );
    expect(
      screen.getByText("Only the end of the log is shown."),
    ).toBeInTheDocument();
  });

  it("clears a run which is over", async () => {
    saveRunId("r1");
    const { store, user } = setup();
    store.dispatch(restoreRun());
    get.mockResolvedValue({
      data: { run_id: "r1", state: "succeeded", report: null, jobs: [] },
    });
    const { fetchRun } = await import("../store/slices/runSlice");
    await store.dispatch(fetchRun("r1"));

    await user.click(await screen.findByRole("button", { name: "Clear" }));

    expect(screen.queryByTestId("run-state")).toBeNull();
  });

  it("can't be run again, or cleared, while it goes", async () => {
    saveRunId("r1");
    const { store } = setup();
    store.dispatch(restoreRun());

    expect(await screen.findByTestId("run-state")).toHaveTextContent("Running");
    expect(run()).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Clear" })).toBeNull();
  });
});
