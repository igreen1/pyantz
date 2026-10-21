/**
 * Work out from a job's parameter schema which parameters are jobs themselves.
 *
 * The api serves pydantic schemas, where a job is `#/$defs/JobConfig` (or
 * `VirtualJobConfig`), possibly in an `anyOf`, and a list of jobs is an array of
 * those, usually behind `#/$defs/JobPipeline`.
 */
import type { JSONSchema7, JSONSchema7Definition } from "json-schema";
import type { NestedKind } from "./graph.ts";

const JOB_DEFINITIONS = new Set(["JobConfig", "VirtualJobConfig"]);

type Schema = JSONSchema7 & { $defs?: Record<string, JSONSchema7Definition> };

const refName = (schema: JSONSchema7): string | undefined =>
  schema.$ref?.startsWith("#/$defs/") ? schema.$ref.slice(8) : undefined;

const asSchema = (definition: JSONSchema7Definition): JSONSchema7 =>
  typeof definition === "object" ? definition : {};

/** Follow `$ref`s to the schema they stand for. */
const resolve = (schema: JSONSchema7, root: Schema): JSONSchema7 => {
  let current = schema;
  for (let hops = 0; hops < 10; hops += 1) {
    const name = refName(current);
    if (name === undefined || JOB_DEFINITIONS.has(name)) return current;
    const target = root.$defs?.[name];
    if (target === undefined) return current;
    current = asSchema(target);
  }
  return current;
};

const alternatives = (schema: JSONSchema7): JSONSchema7[] =>
  [...(schema.anyOf ?? []), ...(schema.oneOf ?? [])]
    .map(asSchema)
    .filter((alternative) => alternative.type !== "null");

const isJob = (schema: JSONSchema7, root: Schema): boolean => {
  const resolved = resolve(schema, root);
  const name = refName(resolved);
  if (name !== undefined) return JOB_DEFINITIONS.has(name);
  const options = alternatives(resolved);
  return options.length > 0 && options.every((one) => isJob(one, root));
};

const kindOf = (schema: JSONSchema7, root: Schema): NestedKind | undefined => {
  if (isJob(schema, root)) return "single";
  const resolved = resolve(schema, root);
  if (resolved.type === "array") {
    const items = resolved.items;
    if (
      items !== undefined &&
      !Array.isArray(items) &&
      isJob(asSchema(items), root)
    ) {
      return "list";
    }
  }
  // optional parameters are `anyOf: [X, null]`
  const options = alternatives(resolved);
  if (options.length === 1) return kindOf(options[0], root);
  return undefined;
};

/** Get the kind of each parameter which holds jobs; other parameters are left out. */
export const classifyParams = (
  schema: JSONSchema7 | undefined,
): Record<string, NestedKind> => {
  const kinds: Record<string, NestedKind> = {};
  for (const [name, definition] of Object.entries(schema?.properties ?? {})) {
    const kind = kindOf(asSchema(definition), schema as Schema);
    if (kind) kinds[name] = kind;
  }
  return kinds;
};

/** The schema of the parameters which are not jobs. */
export const simpleSchema = (
  schema: JSONSchema7,
  kinds: Record<string, NestedKind>,
): JSONSchema7 => ({
  ...schema,
  properties: Object.fromEntries(
    Object.entries(schema.properties ?? {}).filter(
      ([name]) => !(name in kinds),
    ),
  ),
  required: schema.required?.filter((name) => !(name in kinds)),
});
