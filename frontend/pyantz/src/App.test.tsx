import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { Provider } from "react-redux";
import App from "./App";
import api, { setToken } from "./services/api";
import { saveRunId } from "./services/session";
import { makeStore } from "./store/store";
import { dumpedJobs } from "./test/fixtures";

vi.mock("./services/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./services/api")>()),
  default: { get: vi.fn(), post: vi.fn() },
}));

const get = vi.mocked(api.get);
const post = vi.mocked(api.post);

const MKDIR = "pyantz.jobs.files.simple.mkdir";

const answerLikeTheServer = () => {
  get.mockImplementation(async (url) => {
    if (url === "/jobs/get_all_jobs") {
      return {
        data: {
          jobs: Object.entries(dumpedJobs).map(([name, job]) => ({
            name,
            description: job.description,
          })),
        },
      };
    }
    const name = url.replace("/jobs/schema/", "");
    return {
      data: { fn_path: name, json_schema: dumpedJobs[name].json_schema },
    };
  });
  post.mockResolvedValue({ data: { valid: true, errors: [] } });
};

const mount = () => {
  const store = makeStore();
  render(
    <Provider store={store}>
      <App />
    </Provider>,
  );
  return { store, user: userEvent.setup() };
};

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  saveRunId(null);
  setToken(null);
});

describe("App", () => {
  it("loads the jobs, then their schemas, and offers the jobs", async () => {
    answerLikeTheServer();

    const { store } = mount();

    expect(await screen.findByText(MKDIR)).toBeInTheDocument();
    await waitFor(() =>
      expect(store.getState().jobSchemas.status).toBe("succeeded"),
    );
    expect(get).toHaveBeenCalledTimes(1 + Object.keys(dumpedJobs).length);
    expect(Object.keys(store.getState().jobSchemas.schemas)).toHaveLength(
      Object.keys(dumpedJobs).length,
    );
  });

  it("takes a job from the palette to the board and the inspector", async () => {
    answerLikeTheServer();
    const { user } = mount();
    await screen.findByText(MKDIR);

    await user.click(screen.getByTitle(dumpedJobs[MKDIR].description));

    expect(await screen.findByTestId("job-node")).toHaveTextContent("mkdir");
    expect(screen.getByTestId("inspector")).toBeInTheDocument();
    expect(await screen.findByLabelText(/Dir Path/)).toBeInTheDocument();
  });

  it("asks the server to check the pipeline, and shows the answer", async () => {
    answerLikeTheServer();
    const { user } = mount();
    await screen.findByText(MKDIR);
    await user.click(screen.getByTitle(dumpedJobs[MKDIR].description));

    await waitFor(() => expect(post).toHaveBeenCalled(), { timeout: 3000 });

    expect(post.mock.calls[0][0]).toBe("/config/validate");
    expect(await screen.findByTestId("validation-status")).toHaveTextContent(
      "Valid",
    );
  });

  it("counts the problems on the tab", async () => {
    answerLikeTheServer();
    const { user } = mount();
    await screen.findByText(MKDIR);

    await user.click(screen.getByTitle(dumpedJobs[MKDIR].description));

    expect(
      await screen.findByRole("tab", { name: "Problems (1)" }),
    ).toBeInTheDocument();
  });

  it("switches between the panels and the views", async () => {
    answerLikeTheServer();
    const { user } = mount();
    await screen.findByText(MKDIR);

    await user.click(screen.getByRole("tab", { name: "Pipeline" }));
    expect(screen.getByTestId("pipeline-settings")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Run" }));
    expect(screen.getByTestId("run-panel")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Problems" }));
    expect(screen.getByTestId("problems-panel")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Compiled" }));
    expect(screen.getByTestId("compiled-view")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Editor" }));
    expect(screen.queryByTestId("compiled-view")).toBeNull();
  });

  it("asks for the token when the server wants one, and loads once it has it", async () => {
    const turnedDown = new AxiosError("Unauthorized");
    turnedDown.response = { status: 401, data: {} } as AxiosError["response"];
    get.mockRejectedValue(turnedDown);
    const { store } = mount();
    // the interceptor which asks is part of the real client, which is mocked away
    store.dispatch({ type: "auth/unauthorized" });

    const prompt = await screen.findByRole("dialog", { name: "API token" });
    answerLikeTheServer();
    await userEvent
      .setup()
      .type(prompt.querySelector("input") as HTMLElement, "secret");
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Use token" }));

    expect(await screen.findByText(MKDIR)).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "API token" })).toBeNull();
  });

  it("does not load anything while the token is being asked for", async () => {
    answerLikeTheServer();
    const store = makeStore();
    store.dispatch({ type: "auth/unauthorized" });

    render(
      <Provider store={store}>
        <App />
      </Provider>,
    );
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(get).not.toHaveBeenCalled();
  });

  it("picks up the run of an earlier visit", async () => {
    answerLikeTheServer();
    saveRunId("r1");
    get.mockImplementation(async (url) => {
      if (url === "/runs/r1") {
        return {
          data: { run_id: "r1", state: "succeeded", report: null, jobs: [] },
        };
      }
      return { data: { jobs: [] } };
    });

    const { store, user } = mount();
    await waitFor(() => expect(store.getState().run.state).toBe("succeeded"));
    await user.click(screen.getByRole("tab", { name: "Run" }));

    expect(screen.getByTestId("run-state")).toHaveTextContent("Succeeded");
  });
});
