import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, renderHook } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { Provider } from "react-redux";
import api from "../services/api";
import { tokenSupplied } from "../store/actions";
import { selectOpenLevel, addNode } from "../store/slices/graphSlice";
import { saveRunId } from "../services/session";
import { restoreRun } from "../store/slices/runSlice";
import { unauthorized } from "../store/slices/authSlice";
import { loadedStore, withConfig } from "../test/render";
import type { AppStore } from "../store/store";
import { POLL_INTERVAL_MS, useRunPolling } from "./useRunPolling";
import { VALIDATE_DELAY_MS, useConfig, useValidation } from "./useValidation";
import { useShortcuts } from "./useShortcuts";
import { configToGraph } from "../model/convert";

vi.mock("../services/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/api")>()),
  default: { get: vi.fn(), post: vi.fn() },
}));

const get = vi.mocked(api.get);
const post = vi.mocked(api.post);

const NOP = "pyantz.jobs.testing.nop.do_nothing";
const wrapper = (store: AppStore) =>
  function Wrapper({ children }: { children: ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  saveRunId(null);
});
afterEach(() => vi.useRealTimers());

describe("useValidation", () => {
  const pipeline = (jobs: object[]) => withConfig(loadedStore(), { jobs });

  const settle = async (ms: number) => {
    await act(async () => {
      await vi.advanceTimersByTimeAsync(ms);
    });
  };

  it("checks the pipeline a moment after it changed, and keeps the answer", async () => {
    vi.useFakeTimers();
    post.mockResolvedValue({ data: { valid: true, errors: [] } });
    const store = pipeline([{ function: NOP, parameters: {} }]);

    renderHook(() => useValidation(), { wrapper: wrapper(store) });
    expect(post).not.toHaveBeenCalled();
    await settle(VALIDATE_DELAY_MS + 10);

    expect(post).toHaveBeenCalledOnce();
    expect(post.mock.calls[0][0]).toBe("/config/validate");
    expect(post.mock.calls[0][1]).toMatchObject({ jobs: [{ function: NOP }] });
    expect(store.getState().validation.status).toBe("valid");
  });

  it("checks once for a burst of changes", async () => {
    vi.useFakeTimers();
    post.mockResolvedValue({ data: { valid: true, errors: [] } });
    const store = pipeline([{ function: NOP, parameters: {} }]);
    renderHook(() => useValidation(), { wrapper: wrapper(store) });

    for (let i = 0; i < 4; i += 1) {
      await settle(100);
      act(() => {
        store.dispatch(
          addNode({
            ...configToGraph(
              { jobs: [{ function: NOP, parameters: {} }] },
              undefined,
              () => `x${i}`,
            ).level.nodes[0],
          }),
        );
      });
    }
    await settle(VALIDATE_DELAY_MS + 10);

    expect(post).toHaveBeenCalledOnce();
    expect(post.mock.calls[0][1]).toMatchObject({ jobs: expect.any(Array) });
    expect((post.mock.calls[0][1] as { jobs: unknown[] }).jobs).toHaveLength(5);
  });

  it("attaches what the server says to the job it names", async () => {
    vi.useFakeTimers();
    post.mockResolvedValue({
      data: {
        valid: false,
        errors: [
          "jobs: Value error, Invalid jobs:\n- Job 'a' depends on unknown job 'z'",
        ],
      },
    });
    const store = pipeline([{ job_id: "a", function: NOP, parameters: {} }]);

    renderHook(() => useValidation(), { wrapper: wrapper(store) });
    await settle(VALIDATE_DELAY_MS + 10);

    const [node] = selectOpenLevel(store.getState()).nodes;
    expect(store.getState().validation.status).toBe("invalid");
    expect(store.getState().validation.byNode[node.id]).toEqual([
      "Job 'a' depends on unknown job 'z'",
    ]);
  });

  it("says when the check failed", async () => {
    vi.useFakeTimers();
    post.mockRejectedValue(new Error("Network Error"));
    const store = pipeline([{ function: NOP, parameters: {} }]);

    renderHook(() => useValidation(), { wrapper: wrapper(store) });
    await settle(VALIDATE_DELAY_MS + 10);

    expect(store.getState().validation).toMatchObject({
      status: "failed",
      error: "Network Error",
    });
  });

  it("does not use the answer about an older pipeline", async () => {
    vi.useFakeTimers();
    let answerFirst: (value: unknown) => void = () => undefined;
    post.mockImplementationOnce(
      () => new Promise((resolve) => (answerFirst = resolve)),
    );
    post.mockResolvedValueOnce({ data: { valid: true, errors: [] } });
    const store = pipeline([{ function: NOP, parameters: {} }]);
    renderHook(() => useValidation(), { wrapper: wrapper(store) });
    await settle(VALIDATE_DELAY_MS + 10); // the first request is out, unanswered

    act(() => {
      store.dispatch(
        addNode(
          configToGraph(
            { jobs: [{ function: NOP, parameters: {} }] },
            undefined,
            () => "x",
          ).level.nodes[0],
        ),
      );
    });
    await settle(VALIDATE_DELAY_MS + 10); // the second is answered: valid
    await act(async () =>
      answerFirst({ data: { valid: false, errors: ["old"] } }),
    );

    expect(store.getState().validation.status).toBe("valid");
  });

  it("asks nothing for an empty pipeline", async () => {
    vi.useFakeTimers();
    const store = loadedStore();

    renderHook(() => useValidation(), { wrapper: wrapper(store) });
    await settle(VALIDATE_DELAY_MS * 2);

    expect(post).not.toHaveBeenCalled();
  });

  it("waits while a token is being asked for", async () => {
    vi.useFakeTimers();
    const store = pipeline([{ function: NOP, parameters: {} }]);
    store.dispatch(unauthorized());

    renderHook(() => useValidation(), { wrapper: wrapper(store) });
    await settle(VALIDATE_DELAY_MS * 2);

    expect(post).not.toHaveBeenCalled();
    store.dispatch(tokenSupplied());
  });

  it("gives the config of the pipeline as it is", () => {
    const store = pipeline([{ job_id: "a", function: NOP, parameters: {} }]);

    const { result } = renderHook(() => useConfig(), {
      wrapper: wrapper(store),
    });

    expect(result.current.jobs).toEqual([
      { job_id: "a", function: NOP, parameters: {} },
    ]);
  });
});

describe("useRunPolling (T5.7)", () => {
  const running = (state: string) => ({
    data: { run_id: "r1", state, report: null, jobs: [] },
  });

  const startedStore = () => {
    saveRunId("r1");
    const store = loadedStore();
    store.dispatch(restoreRun());
    return store;
  };

  const settle = async (ms: number) => {
    await act(async () => {
      await vi.advanceTimersByTimeAsync(ms);
    });
  };

  it("asks at once, and then at intervals while the run goes on", async () => {
    vi.useFakeTimers();
    get.mockResolvedValue(running("running"));

    renderHook(() => useRunPolling(), { wrapper: wrapper(startedStore()) });
    await settle(1);
    expect(get).toHaveBeenCalledTimes(1);
    await settle(POLL_INTERVAL_MS);
    await settle(POLL_INTERVAL_MS);

    expect(get).toHaveBeenCalledTimes(3);
    expect(get).toHaveBeenCalledWith("/runs/r1");
  });

  it("stops asking once the run is over", async () => {
    vi.useFakeTimers();
    get
      .mockResolvedValueOnce(running("running"))
      .mockResolvedValue(running("succeeded"));
    const store = startedStore();

    renderHook(() => useRunPolling(), { wrapper: wrapper(store) });
    await settle(1);
    await settle(POLL_INTERVAL_MS);
    expect(store.getState().run.state).toBe("succeeded");
    const asked = get.mock.calls.length;
    await settle(POLL_INTERVAL_MS * 10);

    expect(get.mock.calls.length).toBe(asked);
  });

  it("stops asking when the page goes away", async () => {
    vi.useFakeTimers();
    get.mockResolvedValue(running("running"));

    const { unmount } = renderHook(() => useRunPolling(), {
      wrapper: wrapper(startedStore()),
    });
    await settle(1);
    unmount();
    const asked = get.mock.calls.length;
    await settle(POLL_INTERVAL_MS * 10);

    expect(get.mock.calls.length).toBe(asked);
  });

  it("does not ask when there is no run, or while a token is wanted", async () => {
    vi.useFakeTimers();
    const store = loadedStore();
    renderHook(() => useRunPolling(), { wrapper: wrapper(store) });
    await settle(POLL_INTERVAL_MS * 3);
    expect(get).not.toHaveBeenCalled();

    const waiting = startedStore();
    waiting.dispatch(unauthorized());
    renderHook(() => useRunPolling(), { wrapper: wrapper(waiting) });
    await settle(POLL_INTERVAL_MS * 3);

    expect(get).not.toHaveBeenCalled();
  });

  it("keeps asking when a request fails", async () => {
    vi.useFakeTimers();
    get
      .mockRejectedValueOnce(new Error("Network Error"))
      .mockResolvedValue(running("succeeded"));
    const store = startedStore();

    renderHook(() => useRunPolling(), { wrapper: wrapper(store) });
    await settle(1);
    expect(store.getState().run.error).toBe("Network Error");
    await settle(POLL_INTERVAL_MS);

    expect(store.getState().run.state).toBe("succeeded");
  });
});

describe("useShortcuts", () => {
  function Page({ store }: { store: AppStore }) {
    useShortcuts();
    return (
      <Provider store={store}>
        <input aria-label="text" />
      </Provider>
    );
  }
  const mount = (store: AppStore) =>
    render(
      <Provider store={store}>
        <Page store={store} />
      </Provider>,
    );
  const twoJobs = () =>
    withConfig(loadedStore(), { jobs: [{ function: NOP, parameters: {} }] });

  it("undoes and redoes with the keyboard", async () => {
    const user = userEvent.setup();
    const store = twoJobs();
    mount(store);

    await user.keyboard("{Control>}z{/Control}");
    expect(selectOpenLevel(store.getState()).nodes).toHaveLength(0);
    await user.keyboard("{Control>}y{/Control}");
    expect(selectOpenLevel(store.getState()).nodes).toHaveLength(1);
    await user.keyboard("{Control>}z{/Control}");
    await user.keyboard("{Control>}{Shift>}z{/Shift}{/Control}");
    expect(selectOpenLevel(store.getState()).nodes).toHaveLength(1);
  });

  it("leaves the keys to a text field", async () => {
    const user = userEvent.setup();
    const store = twoJobs();
    const { getByLabelText } = mount(store);

    await user.click(getByLabelText("text"));
    await user.keyboard("{Control>}z{/Control}");

    expect(selectOpenLevel(store.getState()).nodes).toHaveLength(1);
  });

  it("closes the context menu, then the notice, then deselects, on escape", async () => {
    const user = userEvent.setup();
    const store = twoJobs();
    store.dispatch({ type: "graph/selectNode", payload: "n1" });
    store.dispatch({
      type: "uiOptions/showContextMenu",
      payload: { position: { x: 0, y: 0 }, boardPosition: { x: 0, y: 0 } },
    });
    store.dispatch({
      type: "uiOptions/showNotice",
      payload: { kind: "info", text: "hi" },
    });
    mount(store);

    await user.keyboard("{Escape}");
    expect(store.getState().uiOptions.contextMenu.showContextMenu).toBe(false);
    expect(store.getState().uiOptions.notice).not.toBeNull();

    await user.keyboard("{Escape}");
    expect(store.getState().uiOptions.notice).toBeNull();
    expect(selectOpenLevel(store.getState()).nodes[0].selected).toBe(true);

    await user.keyboard("{Escape}");
    expect(selectOpenLevel(store.getState()).nodes[0].selected).toBe(false);
  });

  it("stops listening when it is gone", async () => {
    const user = userEvent.setup();
    const store = twoJobs();
    const { unmount } = mount(store);
    unmount();

    await user.keyboard("{Control>}z{/Control}");

    expect(selectOpenLevel(store.getState()).nodes).toHaveLength(1);
  });
});
