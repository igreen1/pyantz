import { describe, expect, it } from "vitest";
import { isTemplate, pointerKeys, propertyKeys, valueAt } from "./templates";

describe("templates", () => {
  it("recognises placeholders anywhere in a string", () => {
    expect(isTemplate("%{out_dir}")).toBe(true);
    expect(isTemplate("%{base}/%{name}.txt")).toBe(true);
    expect(isTemplate("plain")).toBe(false);
    expect(isTemplate("%{unclosed")).toBe(false);
    expect(isTemplate(5)).toBe(false);
  });

  it("reads values by key path", () => {
    expect(valueAt({ a: { b: [1, { c: 2 }] } }, ["a", "b", "1", "c"])).toBe(2);
    expect(valueAt({ a: 1 }, ["x", "y"])).toBeUndefined();
  });

  it("splits ajv pointers", () => {
    expect(pointerKeys("")).toEqual([]);
    expect(pointerKeys("/a/0/b~1c")).toEqual(["a", "0", "b/c"]);
  });

  it("splits rjsf property paths", () => {
    expect(propertyKeys(".a[0].b['x y']")).toEqual(["a", "0", "b", "x y"]);
    expect(propertyKeys("")).toEqual([]);
  });
});
