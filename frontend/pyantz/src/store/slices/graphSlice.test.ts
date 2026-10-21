import { describe, expect, it } from "vitest";
import { makeEdge } from "../../model/connect";
import { configToGraph } from "../../model/convert";
import { nestedKinds, sequentialIds } from "../../test/fixtures";
import { makeStore } from "../store";
import {
  addNode,
  connectNodes,
  deleteElements,
  deleteJobNode,
  enterNested,
  goToDepth,
  loadPipeline,
  openNode,
  redo,
  selectAddJobBlock,
  selectNode,
  selectOpenLevel,
  selectSelectedNode,
  setSubmitter,
  undo,
  updateEdges,
  updateJob,
  updateNodes,
} from "./graphSlice";

const NOP = "pyantz.jobs.testing.nop.do_nothing";
const LOOP = "pyantz.jobs.wrappers.loops.local_for_loop";
const IF_ELSE = "pyantz.jobs.branching.if_else.if_else";

const storeWith = (jobs: unknown[]) => {
  const store = makeStore();
  const imported = configToGraph(
    { submitter: { type_: "local_proc", working_directory: "w" }, jobs },
    nestedKinds,
    sequentialIds(),
  );
  store.dispatch(loadPipeline(imported));
  return store;
};

const chain = () =>
  storeWith([
    { job_id: "a", function: NOP, parameters: {} },
    { job_id: "b", function: NOP, parameters: {}, depends_on: ["a"] },
    { job_id: "c", function: NOP, parameters: {}, depends_on: ["b"] },
  ]);

const level = (store: ReturnType<typeof makeStore>) =>
  selectOpenLevel(store.getState());
const ids = (store: ReturnType<typeof makeStore>) =>
  level(store).nodes.map((node) => node.id);

describe("deleting (T2.4)", () => {
  it("takes the dependencies of a job with it", () => {
    const store = chain();

    store.dispatch(deleteJobNode("n2"));

    expect(ids(store)).toEqual(["n1", "n3"]);
    expect(level(store).edges).toEqual([]);
  });

  it("takes the dependencies with it when react flow removes a job", () => {
    const store = chain();

    store.dispatch(updateNodes([{ id: "n2", type: "remove" }]));

    expect(level(store).edges).toEqual([]);
  });

  it("is one step of the history when jobs and dependencies go together", () => {
    const store = chain();

    store.dispatch(
      deleteElements({ nodeIds: ["n2"], edgeIds: ["en1->n2", "en2->n3"] }),
    );
    store.dispatch(undo());

    expect(ids(store)).toEqual(["n1", "n2", "n3"]);
    expect(level(store).edges).toHaveLength(2);
  });

  it("does nothing, and no history, when nothing is deleted", () => {
    const store = chain();
    store.dispatch(undo()); // back to the empty pipeline

    store.dispatch(deleteElements({ nodeIds: [], edgeIds: [] }));

    expect(store.getState().graph.past).toHaveLength(0);
  });
});

describe("connecting (T2.5)", () => {
  it("adds a dependency", () => {
    const store = storeWith([
      { job_id: "a", function: NOP, parameters: {} },
      { job_id: "b", function: NOP, parameters: {} },
    ]);

    store.dispatch(connectNodes({ source: "n1", target: "n2" }));

    expect(level(store).edges.map((e) => [e.source, e.target])).toEqual([
      ["n1", "n2"],
    ]);
  });

  it("refuses a circle, a self dependency and a repeat", () => {
    const store = chain();
    const before = level(store).edges.length;

    store.dispatch(connectNodes({ source: "n3", target: "n1" }));
    store.dispatch(connectNodes({ source: "n1", target: "n1" }));
    store.dispatch(connectNodes({ source: "n1", target: "n2" }));

    expect(level(store).edges).toHaveLength(before);
  });
});

describe("undo and redo (T3.6)", () => {
  it("steps back through adding, connecting and deleting, and forward again", () => {
    const store = storeWith([]);
    const node = (id: string) => ({
      ...configToGraph(
        { jobs: [{ function: NOP, parameters: {} }] },
        nestedKinds,
        () => id,
      ).level.nodes[0],
    });

    store.dispatch(addNode(node("x")));
    store.dispatch(addNode(node("y")));
    store.dispatch(connectNodes({ source: "x", target: "y" }));
    store.dispatch(deleteJobNode("x"));
    expect(ids(store)).toEqual(["y"]);

    store.dispatch(undo());
    expect(ids(store)).toEqual(["x", "y"]);
    expect(level(store).edges).toHaveLength(1);
    store.dispatch(undo());
    expect(level(store).edges).toHaveLength(0);
    store.dispatch(undo());
    expect(ids(store)).toEqual(["x"]);

    store.dispatch(redo());
    store.dispatch(redo());
    store.dispatch(redo());
    expect(ids(store)).toEqual(["y"]);
  });

  it("forgets what could be redone after a new change", () => {
    const store = chain();
    store.dispatch(deleteJobNode("n3"));
    store.dispatch(undo());
    expect(store.getState().graph.future).toHaveLength(1);

    store.dispatch(deleteJobNode("n1"));

    expect(store.getState().graph.future).toHaveLength(0);
  });

  it("has nothing to undo or redo at the start", () => {
    const store = makeStore();

    store.dispatch(undo());
    store.dispatch(redo());

    expect(store.getState().graph.root.nodes).toEqual([]);
  });

  it("brings back the pipeline settings which opening a config replaced", () => {
    const store = makeStore();
    store.dispatch(
      setSubmitter({ type_: "local_proc", working_directory: "mine" }),
    );
    store.dispatch(
      loadPipeline(
        configToGraph({
          submitter: { type_: "slurm_sbatch", working_dir: "x" },
          jobs: [],
        }),
      ),
    );
    expect(store.getState().graph.pipeline.submitter.type_).toBe(
      "slurm_sbatch",
    );

    store.dispatch(undo());

    expect(store.getState().graph.pipeline.submitter.working_directory).toBe(
      "mine",
    );
  });

  it("does not make a step of every keystroke in one field", () => {
    const store = chain();
    const before = store.getState().graph.past.length;

    for (const name of ["r", "re", "ren", "rena"]) {
      store.dispatch(
        updateJob({ id: "n1", changes: { name }, editKey: "n1:name" }),
      );
    }
    store.dispatch(
      updateJob({ id: "n2", changes: { name: "other" }, editKey: "n2:name" }),
    );

    expect(store.getState().graph.past.length).toBe(before + 2);
    store.dispatch(undo());
    store.dispatch(undo());
    expect(level(store).nodes[0].data.job.name).toBeUndefined();
  });

  it("keeps the history to a limit", () => {
    const store = chain();

    for (let i = 0; i < 130; i += 1) {
      store.dispatch(updateJob({ id: "n1", changes: { name: `${i}` } }));
    }

    expect(store.getState().graph.past.length).toBe(100);
  });
});

describe("updateJob", () => {
  it("replaces the parameters as a whole, so a removed one is gone", () => {
    const store = storeWith([
      { function: NOP, parameters: { keep: 1, drop: 2 } },
    ]);

    store.dispatch(
      updateJob({ id: "n1", changes: { parameters: { keep: 1 } } }),
    );

    expect(level(store).nodes[0].data.job.parameters).toEqual({ keep: 1 });
  });

  it("ignores a job which is not there", () => {
    const store = chain();
    const before = store.getState().graph.past.length;

    store.dispatch(updateJob({ id: "nope", changes: { name: "x" } }));

    expect(store.getState().graph.past.length).toBe(before);
  });
});

describe("selecting", () => {
  it("selects one job at a time", () => {
    const store = chain();

    store.dispatch(selectNode("n2"));
    store.dispatch(selectNode("n3"));

    expect(selectSelectedNode(store.getState())?.id).toBe("n3");
    store.dispatch(selectNode(null));
    expect(selectSelectedNode(store.getState())).toBeUndefined();
  });

  it("selects a job which is added", () => {
    const store = chain();
    const [added] = configToGraph(
      { jobs: [{ function: NOP, parameters: {} }] },
      nestedKinds,
      () => "new",
    ).level.nodes;

    store.dispatch(selectNode("n1"));
    store.dispatch(addNode(added));

    expect(selectSelectedNode(store.getState())?.id).toBe("new");
  });
});

describe("nested levels (T4.4, T4.5)", () => {
  const nested = () =>
    storeWith([
      {
        job_id: "loop",
        function: LOOP,
        parameters: {
          jobs: [
            { job_id: "x", function: NOP, parameters: {} },
            { job_id: "y", function: NOP, parameters: {} },
          ],
        },
      },
    ]);

  it("opens the jobs inside a job, and the way back", () => {
    const store = nested();
    const loop = level(store).nodes[0];

    store.dispatch(
      enterNested({ nodeId: loop.id, param: "jobs", kind: "list" }),
    );
    expect(level(store).nodes).toHaveLength(2);

    store.dispatch(goToDepth(0));
    expect(level(store).nodes).toHaveLength(1);
  });

  it("refuses a dependency across levels", () => {
    const store = nested();
    const loop = level(store).nodes[0];
    store.dispatch(
      enterNested({ nodeId: loop.id, param: "jobs", kind: "list" }),
    );
    const inside = level(store).nodes[0].id;

    store.dispatch(connectNodes({ source: inside, target: loop.id }));

    expect(level(store).edges).toEqual([]);
    store.dispatch(goToDepth(0));
    expect(level(store).edges).toEqual([]);
  });

  it("edits the jobs of the open level only", () => {
    const store = nested();
    const loop = level(store).nodes[0];
    store.dispatch(
      enterNested({ nodeId: loop.id, param: "jobs", kind: "list" }),
    );
    const [x, y] = level(store).nodes;

    store.dispatch(connectNodes({ source: x.id, target: y.id }));
    store.dispatch(goToDepth(0));

    expect(level(store).edges).toEqual([]);
    expect(
      store.getState().graph.root.nodes[0].data.nested.jobs.edges,
    ).toHaveLength(1);
  });

  it("makes an empty level for a parameter which has no jobs yet", () => {
    const store = storeWith([
      { function: LOOP, parameters: { num_iterations: 1 } },
    ]);
    const loop = level(store).nodes[0];

    store.dispatch(
      enterNested({ nodeId: loop.id, param: "jobs", kind: "list" }),
    );

    expect(level(store).nodes).toEqual([]);
    store.dispatch(goToDepth(0));
    expect(level(store).nodes[0].data.nested.jobs).toEqual({
      kind: "list",
      nodes: [],
      edges: [],
    });
  });

  it("opens a job at any depth and selects it", () => {
    const store = nested();
    const loop = level(store).nodes[0];

    store.dispatch(
      openNode({
        path: [{ nodeId: loop.id, param: "jobs" }],
        nodeId: level(store).nodes[0].data.nested.jobs.nodes[1].id,
      }),
    );

    expect(selectSelectedNode(store.getState())?.data.job.job_id).toBe("y");
  });

  it("closes a level which an undo has removed", () => {
    const store = storeWith([
      { function: LOOP, parameters: { num_iterations: 1 } },
    ]);
    const loop = level(store).nodes[0];
    store.dispatch(
      enterNested({ nodeId: loop.id, param: "jobs", kind: "list" }),
    );
    expect(store.getState().graph.path).toHaveLength(1);

    store.dispatch(undo());

    expect(store.getState().graph.path).toHaveLength(0);
  });
});

describe("edge changes from react flow", () => {
  it("applies them", () => {
    const store = chain();

    store.dispatch(updateEdges([{ id: "en1->n2", type: "remove" }]));

    expect(level(store).edges.map((e) => e.id)).toEqual(["en2->n3"]);
    expect(makeEdge("a", "b").id).toBe("ea->b");
  });
});

describe("a parameter which holds one job", () => {
  const branch = (parameters: object = {}) =>
    storeWith([{ job_id: "if", function: IF_ELSE, parameters }]);
  const newJob = (id: string) =>
    ({
      id,
      type: "jobNode",
      position: { x: 0, y: 0 },
      data: { job: { function: NOP, parameters: {} }, nested: {} },
    }) as const;
  const enter = (store: ReturnType<typeof makeStore>, param = "if_true") => {
    const [node] = level(store).nodes;
    store.dispatch(enterNested({ nodeId: node.id, param, kind: "single" }));
  };

  it("takes its first job", () => {
    const store = branch();
    enter(store);

    expect(selectAddJobBlock(store.getState())).toBeNull();
    store.dispatch(addNode(newJob("first")));

    expect(ids(store)).toEqual(["first"]);
  });

  it("takes no second job, and says why", () => {
    const store = branch({
      if_true: { job_id: "t", function: NOP, parameters: {} },
    });
    enter(store);

    expect(selectAddJobBlock(store.getState())).toMatch(
      /if_true takes a single job/,
    );
    store.dispatch(addNode(newJob("second")));

    expect(ids(store)).toHaveLength(1);
    expect(store.getState().graph.past).toHaveLength(1); // opening the pipeline only
  });

  it("takes another job once the one it has is deleted", () => {
    const store = branch({
      if_true: { job_id: "t", function: NOP, parameters: {} },
    });
    enter(store);
    store.dispatch(deleteJobNode(ids(store)[0]));

    expect(selectAddJobBlock(store.getState())).toBeNull();
    store.dispatch(addNode(newJob("again")));
    expect(ids(store)).toEqual(["again"]);
  });

  it("limits each parameter on its own, and not the pipeline or a list", () => {
    const store = branch({
      if_true: { job_id: "t", function: NOP, parameters: {} },
    });
    expect(selectAddJobBlock(store.getState())).toBeNull();

    enter(store, "if_false");
    expect(selectAddJobBlock(store.getState())).toBeNull();

    const loops = storeWith([
      {
        job_id: "loop",
        function: LOOP,
        parameters: { jobs: [{ job_id: "x", function: NOP, parameters: {} }] },
      },
    ]);
    const [loop] = level(loops).nodes;
    loops.dispatch(
      enterNested({ nodeId: loop.id, param: "jobs", kind: "list" }),
    );
    expect(selectAddJobBlock(loops.getState())).toBeNull();
    loops.dispatch(addNode(newJob("more")));
    expect(ids(loops)).toHaveLength(2);
  });
});
