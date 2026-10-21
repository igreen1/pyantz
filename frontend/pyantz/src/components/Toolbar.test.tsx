import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { makeStore } from "../store/store";
import { selectOpenLevel } from "../store/slices/graphSlice";
import { copyText, downloadText } from "../services/files";
import { loadedStore, renderWithStore, withConfig } from "../test/render";
import Toolbar from "./Toolbar";

vi.mock("../services/files", () => ({
  downloadText: vi.fn(),
  copyText: vi.fn(async () => true),
  readFileText: async (file: File) => file.text(),
}));

const NOP = "pyantz.jobs.testing.nop.do_nothing";
const config = {
  submitter: { type_: "local_proc", working_directory: "w" },
  variables: { a: 1 },
  jobs: [
    { job_id: "a", function: NOP, parameters: {} },
    { job_id: "b", function: NOP, parameters: {}, depends_on: ["a"] },
  ],
};

beforeEach(() => {
  vi.mocked(downloadText).mockClear();
  vi.mocked(copyText).mockClear();
});

describe("Toolbar import", () => {
  const open = async (store = loadedStore()) => {
    const user = userEvent.setup();
    renderWithStore(<Toolbar />, store);
    await user.click(screen.getByRole("button", { name: "Import JSON" }));
    return { store, user };
  };
  const paste = (text: string) => {
    // a paste, which is much faster than typing a config key by key
    return userEvent
      .setup()
      .click(screen.getByLabelText("or paste the config"))
      .then(() => userEvent.paste(text));
  };

  it("opens a pasted config", async () => {
    const { store, user } = await open();

    await paste(JSON.stringify(config));
    await user.click(screen.getByRole("button", { name: "Open" }));

    expect(selectOpenLevel(store.getState()).nodes).toHaveLength(2);
    expect(selectOpenLevel(store.getState()).edges).toHaveLength(1);
    expect(store.getState().graph.pipeline.variables).toEqual({ a: 1 });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(store.getState().uiOptions.notice?.text).toBe("Opened 2 jobs.");
  });

  it("opens a file", async () => {
    const { store, user } = await open();

    await user.upload(
      screen.getByLabelText("Choose a file"),
      new File([JSON.stringify(config)], "pipeline.json", {
        type: "application/json",
      }),
    );
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Open" })).toBeEnabled(),
    );
    await user.click(screen.getByRole("button", { name: "Open" }));

    expect(selectOpenLevel(store.getState()).nodes).toHaveLength(2);
  });

  it("says when it is not json", async () => {
    const { user } = await open();

    await paste("{ not json");
    await user.click(screen.getByRole("button", { name: "Open" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "This is not valid JSON",
    );
  });

  it("lists everything wrong with a config which is not one", async () => {
    const { user } = await open();

    await paste(
      JSON.stringify({ jobs: [{ parameters: {} }, 3], submitter: [] }),
    );
    await user.click(screen.getByRole("button", { name: "Open" }));

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("submitter must be an object");
    expect(alert).toHaveTextContent('jobs.0 has no "function"');
    expect(alert).toHaveTextContent("jobs.1 must be an object");
  });

  it("keeps the board when the config is refused", async () => {
    const store = withConfig(loadedStore(), {
      jobs: [{ function: NOP, parameters: {} }],
    });
    const { user } = await open(store);

    await paste("[]");
    await user.click(screen.getByRole("button", { name: "Open" }));

    expect(selectOpenLevel(store.getState()).nodes).toHaveLength(1);
  });

  it("waits for the schemas, which tell the jobs inside jobs from other parameters", async () => {
    const { user } = await open(makeStore());

    await paste(JSON.stringify(config));

    expect(screen.getByRole("status")).toHaveTextContent("still loading");
    expect(screen.getByRole("button", { name: "Open" })).toBeDisabled();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("has nothing to open until something is pasted", async () => {
    await open();

    expect(screen.getByRole("button", { name: "Open" })).toBeDisabled();
  });
});

describe("Toolbar export", () => {
  const open = async () => {
    const store = withConfig(loadedStore(), config);
    const user = userEvent.setup();
    renderWithStore(<Toolbar />, store);
    await user.click(screen.getByRole("button", { name: "Export JSON" }));
    return { store, user };
  };

  it("shows the config", async () => {
    await open();

    const exported = JSON.parse(
      (screen.getByTestId("export-text") as HTMLTextAreaElement).value,
    );
    expect(exported).toEqual(config);
  });

  it("can put the layout in", async () => {
    const { user } = await open();

    await user.click(screen.getByLabelText(/Include where the jobs are/));

    const exported = JSON.parse(
      (screen.getByTestId("export-text") as HTMLTextAreaElement).value,
    );
    expect(Object.keys(exported["x-pyantz-ui"].positions)).toEqual([
      "jobs.0",
      "jobs.1",
    ]);
  });

  it("downloads a file", async () => {
    const { user } = await open();

    await user.click(screen.getByRole("button", { name: "Download" }));

    expect(downloadText).toHaveBeenCalledWith(
      "pipeline.json",
      expect.stringContaining('"job_id": "a"'),
    );
  });

  it("copies, and says whether it could", async () => {
    const { store, user } = await open();

    await user.click(screen.getByRole("button", { name: "Copy" }));
    await waitFor(() =>
      expect(store.getState().uiOptions.notice?.text).toBe(
        "Copied to the clipboard.",
      ),
    );

    vi.mocked(copyText).mockResolvedValueOnce(false);
    await user.click(screen.getByRole("button", { name: "Copy" }));
    await waitFor(() =>
      expect(store.getState().uiOptions.notice?.kind).toBe("error"),
    );
  });

  it("closes", async () => {
    const { user } = await open();

    await user.click(screen.getByRole("button", { name: "Close" }));

    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("Toolbar new, undo and redo", () => {
  it("starts a new pipeline at once when the board is empty", async () => {
    const user = userEvent.setup();
    renderWithStore(<Toolbar />, loadedStore());

    await user.click(screen.getByRole("button", { name: "New" }));

    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("asks before it discards jobs, and can be undone", async () => {
    const user = userEvent.setup();
    const store = withConfig(loadedStore(), config);
    renderWithStore(<Toolbar />, store);

    await user.click(screen.getByRole("button", { name: "New" }));
    expect(selectOpenLevel(store.getState()).nodes).toHaveLength(2);
    await user.click(
      screen.getByRole("button", { name: "Discard and start new" }),
    );
    expect(selectOpenLevel(store.getState()).nodes).toHaveLength(0);

    await user.click(screen.getByRole("button", { name: "Undo" }));
    expect(selectOpenLevel(store.getState()).nodes).toHaveLength(2);
    await user.click(screen.getByRole("button", { name: "Redo" }));
    expect(selectOpenLevel(store.getState()).nodes).toHaveLength(0);
  });

  it("can't undo or redo when there is nothing to", () => {
    renderWithStore(<Toolbar />, makeStore());

    expect(screen.getByRole("button", { name: "Undo" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Redo" })).toBeDisabled();
  });
});
