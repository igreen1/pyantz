import { describe, expect, it } from "vitest";
import { validateParameters } from "./validate";
import { schemaOf } from "../test/fixtures";

const MKDIR = schemaOf("pyantz.jobs.files.simple.mkdir");
const IF_ELSE = schemaOf("pyantz.jobs.branching.if_else.if_else");

describe("validateParameters", () => {
  it("accepts good parameters", () => {
    expect(validateParameters(MKDIR, { dir_path: "/tmp/x" })).toEqual([]);
  });

  it("asks for a required parameter", () => {
    expect(validateParameters(MKDIR, {})).toEqual([
      { path: "/dir_path", message: "is required" },
    ]);
  });

  it("says a required parameter which is still null is missing", () => {
    expect(validateParameters(MKDIR, { dir_path: null })).toEqual([
      { path: "/dir_path", message: "is required" },
    ]);
  });

  it("flags a value of the wrong type", () => {
    expect(validateParameters(MKDIR, { dir_path: 5 })[0].path).toBe(
      "/dir_path",
    );
  });

  it("does not check values with placeholders (T3.3)", () => {
    expect(validateParameters(MKDIR, { dir_path: "%{out_dir}/x" })).toEqual([]);
    expect(
      validateParameters(
        { type: "object", properties: { n: { type: "integer" } } },
        { n: "%{count}" },
      ),
    ).toEqual([]);
  });

  it("still flags text which is not a placeholder for a number", () => {
    expect(
      validateParameters(
        { type: "object", properties: { n: { type: "integer" } } },
        { n: "many" },
      ),
    ).toHaveLength(1);
  });

  it("does not ask for the parameters which are jobs", () => {
    const problems = validateParameters(IF_ELSE, {
      left_side: "a",
      right_side: "b",
      comparator: "==",
    });

    expect(problems).toEqual([]);
  });

  it("says one thing about a value which fits none of the alternatives", () => {
    const problems = validateParameters(IF_ELSE, {
      left_side: [],
      right_side: "b",
      comparator: "==",
    });

    expect(problems.filter((p) => p.path === "/left_side")).toHaveLength(1);
  });

  it("knows nothing wrong without a schema", () => {
    expect(validateParameters(undefined, { any: 1 })).toEqual([]);
  });

  it("does not flag anything when the schema can't be compiled", () => {
    expect(
      validateParameters(
        { type: "object", properties: { a: { $ref: "#/$defs/Missing" } } },
        { a: 1 },
      ),
    ).toEqual([]);
  });
});
