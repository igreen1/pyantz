import type { RJSFValidationError } from "@rjsf/utils";
import { describe, expect, it } from "vitest";
import { customizeValidator } from "@rjsf/validator-ajv8";
import {
  buildUiSchema,
  ignoreTemplates,
  ignoringTemplates,
  simplifyForForm,
} from "./rjsf";

const error = (property: string): RJSFValidationError => ({
  name: "type",
  property,
  message: "must be integer",
  stack: `${property} must be integer`,
});

describe("ignoreTemplates (T3.3)", () => {
  const transform = (data: unknown, errors: RJSFValidationError[]) =>
    ignoreTemplates(data)(errors, {} as never);

  it("drops errors about placeholders", () => {
    expect(transform({ n: "%{count}" }, [error(".n")])).toEqual([]);
  });

  it("keeps errors about other values", () => {
    expect(transform({ n: "many" }, [error(".n")])).toHaveLength(1);
  });

  it("finds nested values", () => {
    const data = { a: [{ b: "%{x}" }, { b: "no" }] };

    expect(transform(data, [error(".a[0].b"), error(".a[1].b")])).toEqual([
      error(".a[1].b"),
    ]);
  });

  it("keeps errors about no property", () => {
    expect(
      transform({}, [{ name: "required", message: "m", stack: "s" }]),
    ).toHaveLength(1);
  });
});

describe("buildUiSchema", () => {
  it("shows numbers as text, and nothing else", () => {
    expect(
      buildUiSchema({
        type: "object",
        properties: {
          count: { type: "integer" },
          ratio: { type: "number" },
          maybe: { anyOf: [{ type: "integer" }, { type: "null" }] },
          path: { type: "string" },
        },
      }),
    ).toEqual({
      "ui:submitButtonOptions": { norender: true },
      count: { "ui:options": { inputType: "text" } },
      ratio: { "ui:options": { inputType: "text" } },
      maybe: { "ui:options": { inputType: "text" } },
    });
  });
});

describe("ignoringTemplates", () => {
  const validator = ignoringTemplates(customizeValidator());
  const schema = {
    type: "object" as const,
    properties: {
      n: { type: "integer" as const },
      s: { type: "string" as const },
    },
  };

  it("accepts a placeholder where a number is wanted", () => {
    expect(
      validator.validateFormData({ n: "%{count}" }, schema).errors,
    ).toEqual([]);
  });

  it("still reports a value which is wrong", () => {
    const { errors } = validator.validateFormData({ n: "many" }, schema);

    expect(errors).toHaveLength(1);
    expect(errors[0].property).toBe(".n");
  });

  it("judges the data it is given, not data from an earlier call", () => {
    validator.validateFormData({ n: "%{count" }, schema);

    expect(
      validator.validateFormData({ n: "%{count}" }, schema).errors,
    ).toEqual([]);
  });

  it("keeps the other methods of the validator", () => {
    expect(validator.isValid(schema, { n: 1 }, schema)).toBe(true);
    expect(validator.isValid(schema, { n: "x" }, schema)).toBe(false);
  });

  it("applies the transform it is given too", () => {
    const { errors } = validator.validateFormData(
      { n: "many" },
      schema,
      undefined,
      () => [],
    );

    expect(errors).toEqual([]);
  });
});

describe("simplifyForForm", () => {
  it("leaves out the heading and text of the whole schema", () => {
    const simple = simplifyForForm({
      type: "object",
      title: "IfElseParams",
      description: "Parameters for the if/else job.",
      properties: { a: { type: "string" } },
    });

    expect(simple).toEqual({
      type: "object",
      properties: { a: { type: "string" } },
    });
  });

  it("makes one field of a parameter which may be of several plain types", () => {
    const simple = simplifyForForm({
      type: "object",
      properties: {
        side: {
          title: "Left Side",
          anyOf: [{ type: "number" }, { type: "string" }],
          default: 1,
        },
        maybe: { anyOf: [{ type: "integer" }, { type: "null" }] },
      },
    });

    expect(simple.properties).toEqual({
      // text first, so that the field is shown as one
      side: { title: "Left Side", type: ["string", "number"], default: 1 },
      maybe: { type: ["integer", "null"] },
    });
  });

  it("leaves other alternatives, such as choices and objects, as they are", () => {
    const properties = {
      choice: {
        anyOf: [{ type: "string", enum: ["a", "b"] }, { type: "null" }],
      },
      shape: { anyOf: [{ type: "object" }, { type: "string" }] },
      ref: { $ref: "#/$defs/X" },
    };

    expect(
      simplifyForForm({ type: "object", properties } as never).properties,
    ).toEqual(properties);
  });

  it("accepts a value of any of the types", () => {
    const schema = simplifyForForm({
      type: "object",
      properties: { side: { anyOf: [{ type: "string" }, { type: "number" }] } },
    });
    const validator = customizeValidator();

    expect(validator.validateFormData({ side: 5 }, schema).errors).toEqual([]);
    expect(validator.validateFormData({ side: "five" }, schema).errors).toEqual(
      [],
    );
    expect(
      validator.validateFormData({ side: [] }, schema).errors,
    ).toHaveLength(1);
  });
});
