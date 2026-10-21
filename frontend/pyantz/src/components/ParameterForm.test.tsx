import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { makeStore } from "../store/store";
import { useAppSelector } from "../store/hooks";
import { selectOpenLevel } from "../store/slices/graphSlice";
import { loadedStore, renderWithStore, withConfig } from "../test/render";
import ParameterForm from "./ParameterForm";

const MKDIR = "pyantz.jobs.files.simple.mkdir";
const LOOP = "pyantz.jobs.wrappers.loops.local_for_loop";
const IF_ELSE = "pyantz.jobs.branching.if_else.if_else";

// like the inspector: the form shows what the store has
function Connected({ fn }: { fn: string }) {
  const parameters = useAppSelector(
    (state) => selectOpenLevel(state).nodes[0].data.job.parameters,
  );
  return <ParameterForm nodeId="n1" fn={fn} parameters={parameters} />;
}

const setup = (fn: string, parameters: object, store = loadedStore()) => {
  withConfig(store, { jobs: [{ function: fn, parameters }] });
  const params = () =>
    selectOpenLevel(store.getState()).nodes[0].data.job.parameters;
  renderWithStore(<Connected fn={fn} />, store);
  return { store, params, user: userEvent.setup() };
};

describe("ParameterForm", () => {
  it("makes a form from the schema, marking what is required (T3.2)", () => {
    setup(MKDIR, { dir_path: "d" });

    expect(screen.getByLabelText(/Dir Path/)).toHaveValue("d");
    expect(screen.getByText("*")).toBeInTheDocument();
  });

  it("puts what is typed in the job (T3.4)", async () => {
    const { params, user } = setup(MKDIR, { dir_path: "" });

    await user.type(screen.getByLabelText(/Dir Path/), "/tmp/x");

    expect(params()).toEqual({ dir_path: "/tmp/x" });
  });

  it("does not change the job when it is only shown", () => {
    const { store } = setup(MKDIR, { dir_path: "d" });

    expect(store.getState().graph.past).toHaveLength(1); // the config opened
    expect(
      selectOpenLevel(store.getState()).nodes[0].data.job.parameters,
    ).toEqual({ dir_path: "d" });
  });

  it("does not show the parameters which are jobs", () => {
    setup(IF_ELSE, { left_side: "a", right_side: "b", comparator: "==" });

    expect(screen.getByLabelText(/Left Side/)).toBeInTheDocument();
    expect(screen.queryByText(/If True/i)).toBeNull();
    expect(screen.queryByText(/If False/i)).toBeNull();
  });

  it("shows a parameter of several plain types as one field, with no heading", async () => {
    const { params, user } = setup(IF_ELSE, {
      left_side: 5,
      right_side: "b",
      comparator: "==",
    });

    expect(screen.getAllByLabelText(/Left Side/)).toHaveLength(1);
    expect(screen.queryByText("IfElseParams")).toBeNull();
    expect(screen.queryByText(/option 1/)).toBeNull();
    // a number which was there is not an error
    expect(screen.getByLabelText(/Left Side/)).toHaveValue("5");
    expect(screen.queryByText(/must be/)).toBeNull();

    await user.clear(screen.getByLabelText(/Left Side/));
    await user.type(screen.getByLabelText(/Left Side/), "%{{environment}");

    expect(params().left_side).toBe("%{environment}");
  });

  it("takes a number as a number, and a placeholder as it is (T3.3)", async () => {
    const { params, user } = setup(LOOP, { num_iterations: 1 });
    const field = screen.getByLabelText(/Num Iterations/);

    await user.clear(field);
    await user.type(field, "5");
    expect(params().num_iterations).toBe(5);

    await user.clear(field);
    await user.type(field, "%{{count}");
    expect(params().num_iterations).toBe("%{count}");
    expect(screen.queryByText(/must be integer/)).toBeNull();
  });

  it("can be switched to raw json and back", async () => {
    const { user } = setup(MKDIR, { dir_path: "d" });

    await user.click(screen.getByRole("button", { name: "Raw JSON" }));
    expect(screen.queryByLabelText(/Dir Path/)).toBeNull();
    expect(screen.getByRole("button", { name: "Raw JSON" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await user.click(screen.getByRole("button", { name: "Form" }));
    expect(screen.getByLabelText(/Dir Path/)).toBeInTheDocument();
  });

  it("edits raw json when the job has no schema, and says so", () => {
    const store = makeStore();
    withConfig(store, { jobs: [{ function: "x.y.z", parameters: { a: 1 } }] });
    renderWithStore(
      <ParameterForm nodeId="n1" fn="x.y.z" parameters={{ a: 1 }} />,
      store,
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "No schema for this job",
    );
  });

  it("says why when the schema could not be loaded", () => {
    const store = makeStore({
      jobSchemas: {
        schemas: {},
        errors: { "x.y.z": "status 500" },
        status: "succeeded",
        error: null,
      },
    });
    withConfig(store, { jobs: [{ function: "x.y.z", parameters: {} }] });
    renderWithStore(
      <ParameterForm nodeId="n1" fn="x.y.z" parameters={{}} />,
      store,
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "Schema unavailable (status 500)",
    );
  });

  it("falls back to raw json for a schema the form can't show", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const store = makeStore({
      jobSchemas: {
        schemas: {
          "x.y.z": {
            type: "object",
            properties: { broken: { $ref: "#/$defs/Missing" } },
          },
        },
        errors: {},
        status: "succeeded",
        error: null,
      },
    });
    withConfig(store, { jobs: [{ function: "x.y.z", parameters: {} }] });

    renderWithStore(
      <ParameterForm nodeId="n1" fn="x.y.z" parameters={{}} />,
      store,
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "This form can't be shown",
    );
  });
});
