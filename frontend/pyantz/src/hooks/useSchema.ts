import { useMemo } from "react";
import type { JSONSchema7 } from "json-schema";
import { classifyParams } from "../model/classify";
import type { NestedKind } from "../model/graph";
import { useAppSelector } from "../store/hooks";

/** The parameter schema of a job's function, and which parameters are jobs. */
export const useSchema = (
  fn: string,
): {
  schema: JSONSchema7 | undefined;
  loadError: string | undefined;
  kinds: Record<string, NestedKind>;
} => {
  const schema = useAppSelector((state) => state.jobSchemas.schemas[fn]);
  const loadError = useAppSelector((state) => state.jobSchemas.errors[fn]);
  const kinds = useMemo(() => classifyParams(schema), [schema]);
  return { schema, loadError, kinds };
};
