import { describe, expect, it } from "vitest";
import {
  ConfigImportError,
  UI_KEY,
  configToGraph,
  graphToConfig,
  normalizeConfig,
} from "./convert";
import { exampleConfigs, nestedKinds, sequentialIds } from "../test/fixtures";

const roundTrip = (config: unknown, includeLayout = false) => {
  const { level, pipeline } = configToGraph(
    config,
    nestedKinds,
    sequentialIds(),
  );
  return graphToConfig(level, pipeline, { includeLayout });
};

const config = (jobs: unknown[], more: object = {}) => ({
  submitter: { type_: "local_proc", working_directory: "w" },
  jobs,
  ...more,
});

const NOP = "pyantz.jobs.testing.nop.do_nothing";
const LOOP = "pyantz.jobs.wrappers.loops.local_for_loop";
const PIPELINE = "pyantz.jobs.wrappers.local.run_pipeline";
const IF_ELSE = "pyantz.jobs.branching.if_else.if_else";

describe("round trip of the examples (T2.1)", () => {
  it("has the examples", () => {
    expect(exampleConfigs.length).toBeGreaterThanOrEqual(10);
  });

  it("really splits the nested jobs of the examples into levels", () => {
    const nestedCount = (
      nodes: { data: { nested: Record<string, { nodes: never[] }> } }[],
    ): number =>
      nodes.reduce(
        (sum, node) =>
          sum +
          Object.values(node.data.nested).reduce(
            (inner, level) =>
              inner + level.nodes.length + nestedCount(level.nodes),
            0,
          ),
        0,
      );
    const counts = Object.fromEntries(
      exampleConfigs.map(([name, example]) => [
        name,
        nestedCount(configToGraph(example, nestedKinds).level.nodes as never),
      ]),
    );

    expect(counts["04_conditional_branching.json"]).toBeGreaterThan(0);
    expect(counts["05_parameter_sweep.json"]).toBeGreaterThan(0);
    expect(counts["07_variables.json"]).toBeGreaterThan(0);
  });

  it.each(exampleConfigs)("keeps %s as it was", (_name, example) => {
    expect(normalizeConfig(roundTrip(example))).toEqual(
      normalizeConfig(example),
    );
  });

  it.each(exampleConfigs)("keeps %s with its layout", (_name, example) => {
    const exported = roundTrip(example, true);

    expect(exported).toHaveProperty([UI_KEY, "positions"]);
    const pure = { ...(exported as Record<string, unknown>) };
    delete pure[UI_KEY];
    expect(normalizeConfig(pure)).toEqual(normalizeConfig(example));
    // and the layout comes back as saved
    expect(roundTrip(exported, true)).toEqual(exported);
  });
});

describe("round trip of nested pipelines (T4.2)", () => {
  const cases: [string, unknown][] = [
    [
      "loop of two jobs",
      config([
        {
          job_id: "loop",
          function: LOOP,
          parameters: {
            jobs: [
              { job_id: "a", function: NOP, parameters: {} },
              { job_id: "b", function: NOP, parameters: {}, depends_on: ["a"] },
            ],
          },
        },
      ]),
    ],
    [
      "if/else with single jobs",
      config([
        {
          function: IF_ELSE,
          parameters: {
            left_side: "%{x}",
            right_side: 1,
            comparator: "==",
            if_true: { function: NOP, parameters: { a: 1 } },
            if_false: { function: NOP, parameters: { a: 2 } },
          },
        },
      ]),
    ],
    [
      "three levels deep",
      config([
        {
          job_id: "outer",
          function: PIPELINE,
          parameters: {
            jobs: [
              {
                job_id: "middle",
                function: PIPELINE,
                parameters: {
                  jobs: [
                    {
                      job_id: "inner",
                      function: LOOP,
                      parameters: {
                        jobs: [{ function: NOP, parameters: {} }],
                      },
                    },
                  ],
                },
              },
            ],
          },
        },
      ]),
    ],
    [
      "an empty pipeline",
      config([{ function: PIPELINE, parameters: { jobs: [] } }]),
    ],
  ];

  it.each(cases)("keeps %s", (_name, original) => {
    expect(normalizeConfig(roundTrip(original))).toEqual(
      normalizeConfig(original),
    );
    expect(
      normalizeConfig(roundTrip(roundTrip(original, true), false)),
    ).toEqual(normalizeConfig(original));
  });

  it("puts the nested jobs in their own levels", () => {
    const { level } = configToGraph(cases[0][1], nestedKinds, sequentialIds());

    const loop = level.nodes[0];
    expect(loop.data.job.parameters).toEqual({});
    expect(loop.data.nested.jobs.kind).toBe("list");
    expect(loop.data.nested.jobs.nodes).toHaveLength(2);
    expect(loop.data.nested.jobs.edges).toHaveLength(1);
    expect(level.edges).toHaveLength(0);
  });

  it("reads a single job as a level of one", () => {
    const { level } = configToGraph(cases[1][1], nestedKinds, sequentialIds());

    expect(level.nodes[0].data.nested.if_true.kind).toBe("single");
    expect(level.nodes[0].data.nested.if_true.nodes).toHaveLength(1);
  });
});

describe("configToGraph", () => {
  it("turns depends_on into edges, and not into job data", () => {
    const { level } = configToGraph(
      config([
        { job_id: "a", function: NOP, parameters: {} },
        { job_id: "b", function: NOP, parameters: {}, depends_on: ["a"] },
      ]),
      nestedKinds,
      sequentialIds(),
    );

    expect(level.edges.map((e) => [e.source, e.target])).toEqual([
      ["n1", "n2"],
    ]);
    expect(JSON.stringify(level.nodes[1].data)).not.toContain("depends_on");
  });

  it("lays the jobs out, with a dependency below what it depends on", () => {
    const { level } = configToGraph(
      config([
        { job_id: "a", function: NOP, parameters: {} },
        { job_id: "b", function: NOP, parameters: {}, depends_on: ["a"] },
      ]),
      nestedKinds,
    );

    expect(level.nodes[1].position.y).toBeGreaterThan(
      level.nodes[0].position.y,
    );
  });

  it("keeps what it doesn't know of", () => {
    const original = config(
      [{ function: NOP, parameters: {}, from_the_future: { x: 1 } }],
      { notes: "keep me", host: { type_: "local" }, variables: { a: 1 } },
    );

    expect(normalizeConfig(roundTrip(original))).toEqual(
      normalizeConfig(original),
    );
  });

  it("keeps dependencies on unknown jobs, for the backend to report", () => {
    const original = config([
      { job_id: "a", function: NOP, parameters: {}, depends_on: ["ghost"] },
    ]);

    expect(roundTrip(original)).toMatchObject({
      jobs: [{ depends_on: ["ghost"] }],
    });
  });

  it("names an unnamed job only when something depends on it", () => {
    const original = config([
      { function: NOP, parameters: {} },
      { function: NOP, parameters: {} },
    ]);
    const { level, pipeline } = configToGraph(
      original,
      nestedKinds,
      sequentialIds(),
    );

    expect(graphToConfig(level, pipeline).jobs[0]).not.toHaveProperty("job_id");

    level.edges.push({ id: "e", source: "n1", target: "n2" });
    const connected = graphToConfig(level, pipeline).jobs;
    expect(connected[0].job_id).toBe("n1");
    expect(connected[1].depends_on).toEqual(["n1"]);
  });

  it("leaves nested parameters raw when the job has no schema", () => {
    const original = config([
      { function: "unknown.module.fn", parameters: { jobs: [{ x: 1 }] } },
    ]);

    const { level } = configToGraph(original, nestedKinds, sequentialIds());

    expect(level.nodes[0].data.nested).toEqual({});
    expect(normalizeConfig(roundTrip(original))).toEqual(
      normalizeConfig(original),
    );
  });

  it("reports everything wrong with a config at once", () => {
    let error: unknown;
    try {
      configToGraph({ jobs: [{ parameters: {} }, 5], submitter: [] });
    } catch (caught) {
      error = caught;
    }

    expect(error).toBeInstanceOf(ConfigImportError);
    expect((error as ConfigImportError).problems).toEqual([
      "submitter must be an object",
      'jobs.0 has no "function"',
      "jobs.1 must be an object",
    ]);
  });

  it.each([[null], [[]], ["text"], [{ submitter: {} }]])(
    "refuses %j",
    (bad) => {
      expect(() => configToGraph(bad)).toThrow(ConfigImportError);
    },
  );
});

describe("graphToConfig", () => {
  it("leaves out what the user did not set", () => {
    const { level, pipeline } = configToGraph(
      config([{ function: NOP, parameters: {} }]),
      nestedKinds,
    );

    expect(graphToConfig(level, pipeline).jobs[0]).toEqual({
      function: NOP,
      parameters: {},
    });
  });

  it("writes the dependencies sorted", () => {
    const { level, pipeline } = configToGraph(
      config([
        { job_id: "b", function: NOP, parameters: {} },
        { job_id: "a", function: NOP, parameters: {} },
        { job_id: "c", function: NOP, parameters: {}, depends_on: ["b", "a"] },
      ]),
      nestedKinds,
    );

    expect(graphToConfig(level, pipeline).jobs[2].depends_on).toEqual([
      "a",
      "b",
    ]);
  });

  it("is json", () => {
    const exported = roundTrip(exampleConfigs[3][1], true);

    expect(JSON.parse(JSON.stringify(exported))).toEqual(exported);
  });
});
