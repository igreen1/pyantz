import { describe, expect, it, vi } from "vitest";
import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { getToken, setToken } from "../services/api";
import { makeStore } from "../store/store";
import { tokenSupplied } from "../store/actions";
import { unauthorized } from "../store/slices/authSlice";
import { enterNested, selectOpenLevel } from "../store/slices/graphSlice";
import {
  checked,
  checkFailed,
  checking,
} from "../store/slices/validationSlice";
import { loadedStore, renderWithStore, withConfig } from "../test/render";
import Breadcrumbs from "./Breadcrumbs";
import ContextMenu from "./ContextMenu";
import Notice from "./Notice";
import ProblemsPanel from "./ProblemsPanel";
import StatusBar from "./StatusBar";
import TokenPrompt from "./TokenPrompt";

const MKDIR = "pyantz.jobs.files.simple.mkdir";
const LOOP = "pyantz.jobs.wrappers.loops.local_for_loop";

describe("TokenPrompt", () => {
  it("shows nothing until the api wants a token", () => {
    renderWithStore(<TokenPrompt />, makeStore());

    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("takes the token, keeps it for the tab, and goes away", async () => {
    const user = userEvent.setup();
    const store = makeStore();
    store.dispatch(unauthorized());
    renderWithStore(<TokenPrompt />, store);
    const useButton = screen.getByRole("button", { name: "Use token" });
    expect(useButton).toBeDisabled();

    await user.type(
      screen.getByLabelText("API token", { selector: "input" }),
      " secret ",
    );
    await user.click(useButton);

    expect(getToken()).toBe("secret");
    expect(store.getState().auth).toMatchObject({
      needsToken: false,
      hasToken: true,
    });
    expect(screen.queryByRole("dialog")).toBeNull();
    setToken(null);
  });

  it("says when the token which was given is not accepted", () => {
    const store = makeStore();
    store.dispatch(tokenSupplied());
    store.dispatch(unauthorized());

    renderWithStore(<TokenPrompt />, store);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "That token was not accepted.",
    );
  });

  it("hides what is typed", () => {
    const store = makeStore();
    store.dispatch(unauthorized());
    renderWithStore(<TokenPrompt />, store);

    expect(
      screen.getByLabelText("API token", { selector: "input" }),
    ).toHaveAttribute("type", "password");
  });
});

describe("StatusBar", () => {
  it.each([
    ["idle", "Not checked"],
    ["checking", "Checking…"],
    ["valid", "Valid"],
    ["invalid", "Has problems"],
    ["failed", "Check failed"],
  ])("says %s as %s", (status, text) => {
    const store = makeStore();
    if (status === "checking") store.dispatch(checking());
    if (status === "valid")
      store.dispatch(checked({ valid: true, unmapped: [], byNode: {} }));
    if (status === "invalid")
      store.dispatch(checked({ valid: false, unmapped: [], byNode: {} }));
    if (status === "failed") store.dispatch(checkFailed("x"));

    renderWithStore(<StatusBar />, store);

    expect(screen.getByTestId("validation-status")).toHaveTextContent(text);
  });

  it("opens the problems when clicked", async () => {
    const user = userEvent.setup();
    const { store } = renderWithStore(<StatusBar />, makeStore());

    await user.click(screen.getByTestId("validation-status"));

    expect(store.getState().uiOptions.sideTab).toBe("problems");
  });

  it("offers to forget the token only when there is one", async () => {
    const user = userEvent.setup();
    const store = makeStore();
    const { rerender } = renderWithStore(<StatusBar />, store);
    expect(screen.queryByRole("button", { name: "Forget token" })).toBeNull();
    rerender(<></>);

    const withToken = makeStore();
    withToken.dispatch(tokenSupplied());
    setToken("secret");
    renderWithStore(<StatusBar />, withToken);
    await user.click(screen.getByRole("button", { name: "Forget token" }));

    expect(getToken()).toBeNull();
    expect(withToken.getState().auth.hasToken).toBe(false);
  });
});

describe("Notice", () => {
  it("shows an error as an alert, and goes away by itself", () => {
    vi.useFakeTimers();
    const store = makeStore();
    renderWithStore(<Notice />, store);
    expect(screen.queryByRole("alert")).toBeNull();

    act(() => {
      store.dispatch({
        type: "uiOptions/showNotice",
        payload: { kind: "error", text: "no" },
      });
    });
    expect(screen.getByRole("alert")).toHaveTextContent("no");
    act(() => {
      vi.advanceTimersByTime(8001);
    });

    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows information as a status, and can be dismissed", async () => {
    const store = makeStore();
    renderWithStore(<Notice />, store);
    act(() => {
      store.dispatch({
        type: "uiOptions/showNotice",
        payload: { kind: "info", text: "ok" },
      });
    });
    expect(screen.getByRole("status")).toHaveTextContent("ok");

    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Dismiss" }));

    expect(screen.queryByRole("status")).toBeNull();
  });
});

describe("ContextMenu", () => {
  const open = (nodeId?: string) => {
    const store = withConfig(loadedStore(), {
      jobs: [{ function: MKDIR, parameters: { dir_path: "d" } }],
    });
    store.dispatch({
      type: "uiOptions/showContextMenu",
      payload: {
        position: { x: 10, y: 20 },
        boardPosition: { x: 3, y: 4 },
        nodeId,
      },
    });
    renderWithStore(<ContextMenu />, store);
    return { store, user: userEvent.setup() };
  };

  it("is not there until opened", () => {
    renderWithStore(<ContextMenu />, loadedStore());

    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("is where the user clicked", () => {
    open();

    expect(screen.getByRole("menu")).toHaveStyle({ top: "20px", left: "10px" });
  });

  it("offers only adding a job on the board itself", () => {
    open();

    expect(
      screen.getAllByRole("menuitem").map((item) => item.textContent),
    ).toEqual(["Add Job"]);
  });

  it("sends the next job to where it was opened, and closes", async () => {
    const { store, user } = open();

    await user.click(screen.getByRole("menuitem", { name: "Add Job" }));

    expect(store.getState().uiOptions.nextJobPosition).toEqual({ x: 3, y: 4 });
    expect(store.getState().uiOptions.focusSearch).toBe(1);
    expect(store.getState().uiOptions.contextMenu.showContextMenu).toBe(false);
  });

  it("does not offer a job where only one fits, and it is there", () => {
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
    store.dispatch({
      type: "uiOptions/showContextMenu",
      payload: { position: { x: 1, y: 1 }, boardPosition: { x: 1, y: 1 } },
    });
    renderWithStore(<ContextMenu />, store);

    expect(screen.getByRole("menuitem", { name: "Add Job" })).toBeDisabled();
  });

  it("edits a job: selects it and shows its details", async () => {
    const { store, user } = open("n1");
    store.dispatch({ type: "uiOptions/setSideTab", payload: "run" });

    await user.click(screen.getByRole("menuitem", { name: "Edit Job" }));

    expect(selectOpenLevel(store.getState()).nodes[0].selected).toBe(true);
    expect(store.getState().uiOptions.sideTab).toBe("job");
  });

  it("deletes a job", async () => {
    const { store, user } = open("n1");

    await user.click(screen.getByRole("menuitem", { name: "Delete Job" }));

    expect(selectOpenLevel(store.getState()).nodes).toEqual([]);
  });
});

describe("Breadcrumbs", () => {
  it("shows only the pipeline at the top", () => {
    renderWithStore(<Breadcrumbs />, loadedStore());

    expect(
      screen.getByRole("navigation", { name: "Pipeline level" }),
    ).toHaveTextContent(/^Pipeline$/);
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("shows the way in, and goes back to any level", async () => {
    const user = userEvent.setup();
    const store = withConfig(loadedStore(), {
      jobs: [
        {
          name: "outer",
          function: LOOP,
          parameters: {
            num_iterations: 1,
            jobs: [
              {
                name: "inner",
                function: LOOP,
                parameters: { num_iterations: 1, jobs: [] },
              },
            ],
          },
        },
      ],
    });
    store.dispatch({
      type: "graph/enterNested",
      payload: { nodeId: "n2", param: "jobs", kind: "list" },
    });
    store.dispatch({
      type: "graph/enterNested",
      payload: { nodeId: "n1", param: "jobs", kind: "list" },
    });
    renderWithStore(<Breadcrumbs />, store);
    expect(store.getState().graph.path).toHaveLength(2);

    const nav = screen.getByRole("navigation", { name: "Pipeline level" });
    expect(nav).toHaveTextContent("Pipeline");
    expect(nav).toHaveTextContent("outer › jobs");
    expect(nav).toHaveTextContent("inner › jobs");

    await user.click(screen.getByRole("button", { name: "outer › jobs" }));
    expect(store.getState().graph.path).toHaveLength(1);
  });
});

describe("ProblemsPanel", () => {
  const setup = (jobs: object[]) => {
    const store = withConfig(loadedStore(), { jobs });
    renderWithStore(<ProblemsPanel />, store);
    return { store, user: userEvent.setup() };
  };

  it("says when there are none", () => {
    setup([{ function: MKDIR, parameters: { dir_path: "d" } }]);

    expect(screen.getByText("No problems found.")).toBeInTheDocument();
  });

  it("lists the jobs with problems and goes to one", async () => {
    const { store, user } = setup([
      { function: MKDIR, parameters: { dir_path: "d" } },
      { function: MKDIR, name: "empty", parameters: {} },
    ]);

    expect(screen.getByText("dir_path is required")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "empty" }));

    expect(selectOpenLevel(store.getState()).nodes[1].selected).toBe(true);
    expect(store.getState().uiOptions.sideTab).toBe("job");
    expect(store.getState().uiOptions.mainTab).toBe("editor");
  });

  it("shows where a job inside another is, and opens that level", async () => {
    const { store, user } = setup([
      {
        name: "wrapper",
        function: LOOP,
        parameters: {
          num_iterations: 1,
          jobs: [{ name: "inside", function: MKDIR, parameters: {} }],
        },
      },
    ]);

    await user.click(screen.getByRole("button", { name: "wrapper › inside" }));

    expect(store.getState().graph.path).toHaveLength(1);
  });

  it("lists what the server says about the pipeline as a whole", () => {
    const { store } = setup([
      { function: MKDIR, parameters: { dir_path: "d" } },
    ]);

    act(() => {
      store.dispatch(
        checked({
          valid: false,
          unmapped: ["submitter: Field required"],
          byNode: {},
        }),
      );
    });

    expect(screen.getByText("submitter: Field required")).toBeInTheDocument();
    expect(screen.queryByText("No problems found.")).toBeNull();
  });

  it("says when the server could not be asked", () => {
    const { store } = setup([
      { function: MKDIR, parameters: { dir_path: "d" } },
    ]);

    act(() => {
      store.dispatch(checkFailed("Network Error"));
    });

    expect(screen.getByRole("alert")).toHaveTextContent("Network Error");
    expect(screen.queryByText("No problems found.")).toBeNull();
  });
});
