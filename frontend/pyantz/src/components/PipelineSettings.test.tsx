import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { loadedStore, renderWithStore, withConfig } from "../test/render";
import PipelineSettings from "./PipelineSettings";

const setup = (config: object = {}) => {
  const store = withConfig(loadedStore(), { jobs: [], ...config });
  renderWithStore(<PipelineSettings />, store);
  return {
    store,
    pipeline: () => store.getState().graph.pipeline,
    user: userEvent.setup(),
  };
};

describe("PipelineSettings", () => {
  it("shows the settings of the local submitter", () => {
    setup({
      submitter: {
        type_: "local_proc",
        working_directory: "/tmp/w",
        number_processes: 4,
      },
    });

    expect(screen.getByLabelText("Working directory")).toHaveValue("/tmp/w");
    expect(screen.getByLabelText("Worker processes")).toHaveValue(4);
  });

  it("changes them", async () => {
    const { pipeline, user } = setup({
      submitter: { type_: "local_proc", working_directory: "w" },
    });

    await user.clear(screen.getByLabelText("Working directory"));
    await user.type(screen.getByLabelText("Working directory"), "/new");
    await user.type(screen.getByLabelText("Worker processes"), "3");
    await user.type(screen.getByLabelText("Timeout (seconds)"), "60");
    await user.click(screen.getByLabelText("Run in this process"));

    expect(pipeline().submitter).toEqual({
      type_: "local_proc",
      working_directory: "/new",
      number_processes: 3,
      timeout: 60,
      use_same_proc: true,
    });
  });

  it("leaves a setting out when it is emptied", async () => {
    const { pipeline, user } = setup({
      submitter: {
        type_: "local_proc",
        working_directory: "w",
        number_processes: 4,
      },
    });

    await user.clear(screen.getByLabelText("Worker processes"));

    expect(pipeline().submitter).toEqual({
      type_: "local_proc",
      working_directory: "w",
    });
  });

  it("keeps the settings it does not show", async () => {
    const { pipeline, user } = setup({
      submitter: {
        type_: "local_proc",
        working_directory: "w",
        poll_timeout: 0.5,
      },
    });

    await user.type(screen.getByLabelText("Working directory"), "x");

    expect(pipeline().submitter.poll_timeout).toBe(0.5);
  });

  it("starts the settings of another submitter when it is changed", async () => {
    const { pipeline, user } = setup();

    await user.selectOptions(
      screen.getByLabelText("Runs jobs with"),
      "slurm_sbatch",
    );

    expect(pipeline().submitter).toEqual({
      type_: "slurm_sbatch",
      working_dir: "pyantz_work",
    });
    expect(screen.queryByLabelText("Worker processes")).toBeNull();
    expect(
      screen.getByRole("group", { name: "Submitter settings" }),
    ).toBeInTheDocument();
  });

  it("sets a host, and takes it away again", async () => {
    const { pipeline, user } = setup();
    expect(pipeline().host).toBeUndefined();

    await user.selectOptions(screen.getByLabelText("Starts on"), "ssh");
    expect(pipeline().host).toEqual({ type_: "ssh", remote_host: "" });
    expect(
      screen.getByRole("group", { name: "Host settings" }),
    ).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Starts on"), "local");
    expect(pipeline().host).toBeUndefined();
    expect(screen.queryByRole("group", { name: "Host settings" })).toBeNull();
  });

  it("shows the variables", () => {
    setup({ variables: { project: "x" } });

    expect(screen.getByRole("group", { name: "Variables" })).toHaveTextContent(
      "project",
    );
  });

  it("says the working directory is not used for runs from the page", () => {
    setup();

    expect(screen.getByText(/chosen by the server/)).toBeInTheDocument();
  });
});
