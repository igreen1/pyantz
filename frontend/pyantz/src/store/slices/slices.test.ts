import { beforeEach, describe, expect, it, vi } from "vitest";
import { AxiosError } from "axios";
import api from "../../services/api";
import { loadRunId, saveRunId } from "../../services/session";
import { tokenForgotten, tokenSupplied } from "../actions";
import { makeStore } from "../store";
import { unauthorized } from "./authSlice";
import { fetchAvailableJobs } from "./availableJobSlice";
import { compilePipeline } from "./compileSlice";
import { fetchJobSchemas } from "./jobSchemaSlice";
import {
  fetchLog,
  fetchRun,
  forgetRun,
  restoreRun,
  startRun,
} from "./runSlice";
import {
  clearNotice,
  hideContextMenu,
  setMainTab,
  setNextJobPosition,
  setSideTab,
  showContextMenu,
  showNotice,
} from "./uiSlice";
import { checkFailed, checked, checking } from "./validationSlice";

vi.mock("../../services/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../services/api")>()),
  default: { get: vi.fn(), post: vi.fn() },
}));

const get = vi.mocked(api.get);
const post = vi.mocked(api.post);

const failure = (status: number, detail: unknown) => {
  const error = new AxiosError("Request failed");
  error.response = { status, data: { detail } } as AxiosError["response"];
  return error;
};

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  saveRunId(null);
});

describe("auth", () => {
  it("asks for a token when the api turns a request down, and takes the first one", () => {
    const store = makeStore();

    store.dispatch(unauthorized());
    expect(store.getState().auth).toMatchObject({
      needsToken: true,
      rejected: false,
    });

    store.dispatch(tokenSupplied());
    expect(store.getState().auth).toMatchObject({
      needsToken: false,
      hasToken: true,
    });
  });

  it("says the token was not accepted when a token had been given", () => {
    const store = makeStore();
    store.dispatch(tokenSupplied());

    store.dispatch(unauthorized());

    expect(store.getState().auth).toMatchObject({
      needsToken: true,
      rejected: true,
    });
  });

  it("forgets that there was a token", () => {
    const store = makeStore();
    store.dispatch(tokenSupplied());

    store.dispatch(tokenForgotten());

    expect(store.getState().auth).toMatchObject({
      hasToken: false,
      rejected: false,
    });
  });

  it("makes the jobs and their schemas load again with another token", async () => {
    const store = makeStore();
    get.mockRejectedValue(failure(401, "Missing or invalid token"));
    await store.dispatch(fetchAvailableJobs());
    expect(store.getState().availableJobs.status).toBe("failed");

    store.dispatch(tokenSupplied());
    expect(store.getState().availableJobs.status).toBe("idle");
    expect(store.getState().jobSchemas.status).toBe("idle");

    get.mockResolvedValue({
      data: { jobs: [{ name: "a", description: "d" }] },
    });
    await store.dispatch(fetchAvailableJobs());
    store.dispatch(tokenForgotten());
    expect(store.getState().availableJobs).toMatchObject({
      status: "idle",
      items: [],
    });
  });
});

describe("compile", () => {
  it("keeps the jobs and edges", async () => {
    const jobs = [{ job_id: "a", name: null, function: "f", depends_on: [] }];
    post.mockResolvedValue({ data: { jobs, edges: [["a", "b"]] } });
    const store = makeStore();

    await store.dispatch(compilePipeline({ jobs: [] }));

    expect(post).toHaveBeenCalledWith("/config/compile", { jobs: [] });
    expect(store.getState().compile).toMatchObject({
      status: "succeeded",
      jobs,
      edges: [["a", "b"]],
    });
  });

  it("keeps the list of problems of a config which doesn't compile", async () => {
    post.mockRejectedValue(failure(422, ["jobs: bad", "submitter: worse"]));
    const store = makeStore();

    await store.dispatch(compilePipeline({}));

    expect(store.getState().compile).toMatchObject({
      status: "failed",
      jobs: [],
      errors: ["jobs: bad", "submitter: worse"],
    });
  });
});

describe("validation", () => {
  it("goes from checking to the answer", () => {
    const store = makeStore();

    store.dispatch(checking());
    expect(store.getState().validation.status).toBe("checking");
    store.dispatch(
      checked({ valid: false, unmapped: ["u"], byNode: { n1: ["m"] } }),
    );
    expect(store.getState().validation).toMatchObject({
      status: "invalid",
      unmapped: ["u"],
      byNode: { n1: ["m"] },
    });
    store.dispatch(checked({ valid: true, unmapped: [], byNode: {} }));
    expect(store.getState().validation.status).toBe("valid");
  });

  it("drops what it knew when the check itself fails", () => {
    const store = makeStore();
    store.dispatch(
      checked({ valid: false, unmapped: ["u"], byNode: { n1: ["m"] } }),
    );

    store.dispatch(checkFailed("Network Error"));

    expect(store.getState().validation).toEqual({
      status: "failed",
      error: "Network Error",
      unmapped: [],
      byNode: {},
    });
  });
});

describe("run", () => {
  const response = (state: string) => ({
    data: {
      run_id: "r1",
      state,
      report: {
        total: 2,
        success: 1,
        error: 0,
        pending: 1,
        ready: 0,
        running: 0,
      },
      jobs: [{ job_id: "a", status: "success", details: null }],
    },
  });

  it("starts, and remembers the run for a reload", async () => {
    post.mockResolvedValue({ data: { run_id: "r1" } });
    const store = makeStore();

    await store.dispatch(startRun({ jobs: [] }));

    expect(store.getState().run).toMatchObject({
      runId: "r1",
      state: "running",
    });
    expect(loadRunId()).toBe("r1");
  });

  it("says why a run could not be started, e.g. runs are off", async () => {
    post.mockRejectedValue(
      failure(
        403,
        "Runs are disabled: set PYANTZ_ALLOWED_MODULES on the server",
      ),
    );
    const store = makeStore();

    await store.dispatch(startRun({}));

    expect(store.getState().run).toMatchObject({
      state: "idle",
      error: "Runs are disabled: set PYANTZ_ALLOWED_MODULES on the server",
    });
    expect(loadRunId()).toBeNull();
  });

  it("clears the last run when another starts", async () => {
    post.mockResolvedValueOnce({ data: { run_id: "r1" } });
    const store = makeStore();
    await store.dispatch(startRun({}));
    get.mockResolvedValue(response("succeeded"));
    await store.dispatch(fetchRun("r1"));

    post.mockResolvedValueOnce({ data: { run_id: "r2" } });
    const starting = store.dispatch(startRun({}));
    expect(store.getState().run).toMatchObject({
      state: "starting",
      jobs: [],
      report: null,
    });
    await starting;
  });

  it("keeps the progress", async () => {
    post.mockResolvedValue({ data: { run_id: "r1" } });
    const store = makeStore();
    await store.dispatch(startRun({}));
    get.mockResolvedValue(response("running"));

    await store.dispatch(fetchRun("r1"));

    expect(store.getState().run).toMatchObject({
      state: "running",
      report: { total: 2 },
      jobs: [{ job_id: "a", status: "success" }],
    });
  });

  it("ignores progress of a run which is not the current one", async () => {
    post.mockResolvedValue({ data: { run_id: "r2" } });
    const store = makeStore();
    await store.dispatch(startRun({}));
    get.mockResolvedValue(response("failed"));

    await store.dispatch(fetchRun("r1"));

    expect(store.getState().run.state).toBe("running");
  });

  it("forgets a run which the server does not know", async () => {
    saveRunId("r1");
    const store = makeStore();
    store.dispatch(restoreRun());
    expect(store.getState().run).toMatchObject({
      runId: "r1",
      state: "running",
    });
    get.mockRejectedValue(failure(404, "No such run: r1"));

    await store.dispatch(fetchRun("r1"));

    expect(store.getState().run.runId).toBeNull();
    expect(loadRunId()).toBeNull();
  });

  it("keeps the run when the request only failed", async () => {
    saveRunId("r1");
    const store = makeStore();
    store.dispatch(restoreRun());
    get.mockRejectedValue(new AxiosError("Network Error"));

    await store.dispatch(fetchRun("r1"));

    expect(store.getState().run).toMatchObject({
      runId: "r1",
      error: "Network Error",
    });
  });

  it("restores nothing when there was no run, or one is already shown", () => {
    const store = makeStore();
    store.dispatch(restoreRun());
    expect(store.getState().run.runId).toBeNull();

    saveRunId("old");
    post.mockResolvedValue({ data: { run_id: "new" } });
    return store.dispatch(startRun({})).then(() => {
      store.dispatch(restoreRun());
      expect(store.getState().run.runId).toBe("new");
    });
  });

  it("reads the end of the log", async () => {
    get.mockResolvedValue({ data: { log: "line\n", truncated: true } });
    const store = makeStore();

    await store.dispatch(fetchLog("r1"));

    expect(get).toHaveBeenCalledWith("/runs/r1/log");
    expect(store.getState().run).toMatchObject({
      log: "line\n",
      logTruncated: true,
    });
  });

  it("says why the log could not be read", async () => {
    get.mockRejectedValue(failure(404, "No log for run: r1"));
    const store = makeStore();

    await store.dispatch(fetchLog("r1"));

    expect(store.getState().run).toMatchObject({
      log: null,
      error: "No log for run: r1",
    });
  });

  it("forgets the run on request", async () => {
    post.mockResolvedValue({ data: { run_id: "r1" } });
    const store = makeStore();
    await store.dispatch(startRun({}));

    store.dispatch(forgetRun());

    expect(store.getState().run.runId).toBeNull();
    expect(loadRunId()).toBeNull();
  });
});

describe("jobs and schemas failing", () => {
  it("keeps the reason a schema could not be loaded for each job", async () => {
    get.mockImplementation(async (url) => {
      if (url.endsWith("/bad")) throw failure(500, "boom");
      return { data: { json_schema: { type: "object" } } };
    });
    const store = makeStore();

    await store.dispatch(fetchJobSchemas(["good", "bad"]));

    expect(store.getState().jobSchemas.errors).toEqual({ bad: "boom" });
  });
});

describe("ui", () => {
  it("opens and closes the context menu, remembering the job it is for", () => {
    const store = makeStore();

    store.dispatch(
      showContextMenu({
        position: { x: 1, y: 2 },
        boardPosition: { x: 3, y: 4 },
        nodeId: "n1",
      }),
    );
    expect(store.getState().uiOptions.contextMenu).toMatchObject({
      showContextMenu: true,
      contextMenuPosition: { x: 1, y: 2 },
      boardPosition: { x: 3, y: 4 },
      editJobId: "n1",
    });

    store.dispatch(hideContextMenu());
    expect(store.getState().uiOptions.contextMenu.showContextMenu).toBe(false);
  });

  it("has no job for a menu opened on the board itself", () => {
    const store = makeStore();

    store.dispatch(
      showContextMenu({
        position: { x: 0, y: 0 },
        boardPosition: { x: 0, y: 0 },
      }),
    );

    expect(store.getState().uiOptions.contextMenu.editJobId).toBeNull();
  });

  it("shows a notice again when the text is the same", () => {
    const store = makeStore();

    store.dispatch(showNotice({ kind: "error", text: "same" }));
    const first = store.getState().uiOptions.notice?.id;
    store.dispatch(showNotice({ kind: "error", text: "same" }));

    expect(store.getState().uiOptions.notice?.id).not.toBe(first);
    store.dispatch(clearNotice());
    expect(store.getState().uiOptions.notice).toBeNull();
  });

  it("changes tabs and remembers where the next job goes", () => {
    const store = makeStore();

    store.dispatch(setSideTab("run"));
    store.dispatch(setMainTab("compiled"));
    store.dispatch(setNextJobPosition({ x: 5, y: 6 }));

    expect(store.getState().uiOptions).toMatchObject({
      sideTab: "run",
      mainTab: "compiled",
      nextJobPosition: { x: 5, y: 6 },
    });
  });
});
