import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import api from "../services/api";
import { fetchRun } from "../store/slices/runSlice";
import { loadedStore, renderWithStore, withConfig } from "../test/render";
import CompiledView from "./CompiledView";

vi.mock("../services/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/api")>()),
  default: { get: vi.fn(), post: vi.fn() },
}));

const get = vi.mocked(api.get);
const post = vi.mocked(api.post);
const NOP = "pyantz.jobs.testing.nop.do_nothing";

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

const compiled = {
  jobs: [
    { job_id: "a", name: null, function: NOP, depends_on: [] },
    { job_id: "b", name: "second", function: NOP, depends_on: ["a"] },
  ],
  edges: [["a", "b"]],
};

const setup = (
  jobs: object[] = [{ job_id: "a", function: NOP, parameters: {} }],
) => {
  const store = withConfig(loadedStore(), { jobs });
  renderWithStore(<CompiledView />, store);
  return { store, user: userEvent.setup() };
};

describe("CompiledView", () => {
  it("compiles the pipeline when it opens, and shows the jobs it gets", async () => {
    post.mockResolvedValue({ data: compiled });

    setup();

    expect(await screen.findAllByTestId("compiled-node")).toHaveLength(2);
    expect(post).toHaveBeenCalledWith(
      "/config/compile",
      expect.objectContaining({ jobs: expect.any(Array) }),
    );
    expect(screen.getByTestId("compiled-view")).toHaveTextContent(
      "2 jobs after virtual jobs are expanded",
    );
    expect(screen.getByText("second")).toBeInTheDocument();
  });

  it("compiles again on request", async () => {
    post.mockResolvedValue({ data: compiled });
    const { user } = setup();
    await screen.findAllByTestId("compiled-node");

    await user.click(screen.getByRole("button", { name: "Refresh" }));

    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
  });

  it("shows how the run is going, in words as well as colour", async () => {
    post.mockResolvedValue({ data: compiled });
    const { store } = setup();
    await screen.findAllByTestId("compiled-node");
    get.mockResolvedValue({
      data: {
        run_id: "r1",
        state: "failed",
        report: null,
        jobs: [
          { job_id: "a", status: "success", details: null },
          { job_id: "b", status: "error", details: "exit status 1" },
        ],
      },
    });
    store.dispatch({ type: "run/start/fulfilled", payload: "r1" });

    await store.dispatch(fetchRun("r1"));

    const [a, b] = await screen.findAllByTestId("compiled-node");
    await waitFor(() => expect(a).toHaveAttribute("data-status", "success"));
    expect(b).toHaveAttribute("data-status", "error");
    expect(b).toHaveTextContent("error");
    expect(b).toHaveAttribute("title", "exit status 1");
  });

  it("says why the pipeline does not compile", async () => {
    post.mockRejectedValue(
      Object.assign(new Error("x"), {
        isAxiosError: true,
        response: { data: { detail: ["jobs: Cannot import 'x.y'"] } },
      }),
    );

    setup();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Cannot import 'x.y'",
    );
  });

  it("has nothing to compile without a job", () => {
    setup([]);

    expect(
      screen.getByText("Add a job to see what it compiles to."),
    ).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });
});
