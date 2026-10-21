/**
 * Check the parameters of a job against the schema the api serves for its function.
 *
 * The api checks parameters only for `strict` jobs, so the editor does it itself to
 * tell the user early. Values with `%{name}` placeholders are not checked: what they
 * turn into is only known when the pipeline runs.
 */
import Ajv2019, { type ValidateFunction } from "ajv/dist/2019";
import type { JSONSchema7 } from "json-schema";
import { classifyParams, simpleSchema } from "./classify.ts";
import { isTemplate, pointerKeys, valueAt } from "./templates.ts";

export interface Problem {
  // where in the parameters, e.g. `/path` (empty for the parameters as a whole)
  path: string;
  message: string;
}

const ajv = new Ajv2019({ strict: false, allErrors: true });
const compiled = new WeakMap<object, ValidateFunction | null>();

const compile = (schema: JSONSchema7): ValidateFunction | null => {
  if (!compiled.has(schema)) {
    try {
      compiled.set(schema, ajv.compile(schema));
    } catch {
      // a schema ajv can't compile is not the user's fault; their data isn't flagged
      compiled.set(schema, null);
    }
  }
  return compiled.get(schema) ?? null;
};

const simpleSchemas = new WeakMap<object, JSONSchema7>();

const simpleSchemaOf = (schema: JSONSchema7): JSONSchema7 => {
  let simple = simpleSchemas.get(schema);
  if (!simple) {
    simple = simpleSchema(schema, classifyParams(schema));
    simpleSchemas.set(schema, simple);
  }
  return simple;
};

/** List what is wrong with the parameters which aren't jobs; none if the schema is unknown. */
export const validateParameters = (
  schema: JSONSchema7 | undefined,
  parameters: Record<string, unknown>,
): Problem[] => {
  if (!schema) return [];
  const validate = compile(simpleSchemaOf(schema));
  if (!validate || validate(parameters)) return [];

  const problems: Problem[] = [];
  const seen = new Set<string>();
  const errors = validate.errors ?? [];
  // when no alternative of an anyOf fits, ajv also lists why each didn't
  const anyOfAt = new Set(
    errors.filter((e) => e.keyword === "anyOf").map((e) => e.instancePath),
  );
  for (const error of errors) {
    const missing =
      error.keyword === "required" ? `/${error.params.missingProperty}` : "";
    const path = `${error.instancePath}${missing}`;
    const value =
      error.keyword === "required"
        ? undefined
        : valueAt(parameters, pointerKeys(error.instancePath));
    if (isTemplate(value)) continue;
    if (error.keyword !== "anyOf" && anyOfAt.has(error.instancePath)) continue;
    // a required parameter which is still empty is missing, not of the wrong type
    const empty = error.keyword === "type" && (value === null || value === "");
    const message =
      error.keyword === "required" || empty
        ? "is required"
        : (error.message ?? "is not valid");
    const key = `${path}:${message}`;
    if (!seen.has(key)) {
      seen.add(key);
      problems.push({ path, message });
    }
  }
  return problems;
};
