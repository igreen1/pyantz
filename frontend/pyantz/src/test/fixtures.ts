/** Fixtures shared by the tests: the example configs, and the schemas of all jobs. */
import type { JSONSchema7 } from "json-schema";
import { classifyParams } from "../model/classify";
import type { NestedKindsFn } from "../model/convert";
import jobSchemaDump from "../__fixtures__/job-schemas.json";

interface DumpedJob {
  description: string;
  json_schema: JSONSchema7;
}

export const dumpedJobs = jobSchemaDump as unknown as Record<string, DumpedJob>;

export const schemaOf = (fn: string): JSONSchema7 | undefined =>
  dumpedJobs[fn]?.json_schema;

/** What the app does at import: look the schema of the job up. */
export const nestedKinds: NestedKindsFn = (fn) => classifyParams(schemaOf(fn));

const exampleModules = import.meta.glob("../__fixtures__/examples/*.json", {
  eager: true,
  import: "default",
}) as Record<string, unknown>;

/** The configs of the `examples/` directory, by file name. */
export const exampleConfigs: [string, unknown][] = Object.entries(
  exampleModules,
)
  .map(([path, config]): [string, unknown] => [
    path.split("/").pop() as string,
    config,
  ])
  .sort(([a], [b]) => a.localeCompare(b));

let nextId = 0;
/** Ids which are the same on each run, for readable failures. */
export const sequentialIds = () => {
  nextId = 0;
  return () => `n${(nextId += 1)}`;
};
