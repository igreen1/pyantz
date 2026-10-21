import { describe, expect, it } from "vitest";
import { classifyParams, simpleSchema } from "./classify";
import { dumpedJobs } from "../test/fixtures";

describe("classifyParams (T4.1)", () => {
  it("finds the jobs among the parameters of every registered job", () => {
    const found = Object.fromEntries(
      Object.entries(dumpedJobs)
        .map(([name, job]) => [name, classifyParams(job.json_schema)] as const)
        .filter(([, kinds]) => Object.keys(kinds).length > 0),
    );

    // a new job holding jobs fails this until it is listed here, on purpose
    expect(found).toEqual({
      "pyantz.jobs.branching.case_matrix.pipeline_expansion": {
        pipeline_template: "list",
      },
      "pyantz.jobs.branching.case_matrix.pipeline_expansion_with_output_dir": {
        pipeline_template: "list",
      },
      "pyantz.jobs.branching.if_else.conditionally_execute": {
        if_true: "single",
      },
      "pyantz.jobs.branching.if_else.if_else": {
        if_true: "single",
        if_false: "single",
      },
      "pyantz.jobs.wrappers.local.run_pipeline": { jobs: "list" },
      "pyantz.jobs.wrappers.loops.local_for_loop": { jobs: "list" },
      "pyantz.jobs.wrappers.submit.new_host": { jobs: "list" },
      "pyantz.jobs.wrappers.submit.submit": { jobs: "list" },
      "pyantz.jobs.wrappers.variables.run_jobs_in_context": { jobs: "list" },
      "pyantz.jobs.wrappers.variables.run_jobs_with_temp_dir": { jobs: "list" },
      "pyantz.jobs.wrappers.variables.set_variables": { jobs: "list" },
    });
  });

  it("treats an optional job as a job", () => {
    expect(
      classifyParams({
        type: "object",
        properties: {
          maybe: { anyOf: [{ $ref: "#/$defs/JobConfig" }, { type: "null" }] },
        },
      }),
    ).toEqual({ maybe: "single" });
  });

  it("does not take other objects or lists for jobs", () => {
    expect(
      classifyParams({
        type: "object",
        properties: {
          a: { type: "array", items: { type: "string" } },
          b: { $ref: "#/$defs/Other" },
          c: { anyOf: [{ type: "string" }, { type: "number" }] },
        },
        $defs: { Other: { type: "object" } },
      } as never),
    ).toEqual({});
  });

  it("knows no jobs without a schema", () => {
    expect(classifyParams(undefined)).toEqual({});
  });
});

describe("simpleSchema", () => {
  it("leaves out the job parameters and their requirement", () => {
    const schema =
      dumpedJobs["pyantz.jobs.branching.if_else.if_else"].json_schema;

    const simple = simpleSchema(schema, classifyParams(schema));

    expect(Object.keys(simple.properties ?? {})).not.toContain("if_true");
    expect(simple.required).not.toContain("if_true");
    expect(simple.required).toContain("left_side");
  });
});
