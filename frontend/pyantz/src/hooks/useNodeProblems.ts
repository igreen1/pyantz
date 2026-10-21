import { useMemo } from "react";
import { countProblems, jobProblems } from "../model/problems";
import type { JobNode, JobNodeData } from "../model/graph";
import { useAppSelector } from "../store/hooks";
import { selectOpenLevel } from "../store/slices/graphSlice";

export interface NodeProblems {
  // about the job itself
  own: string[];
  // from the api
  fromServer: string[];
  // in the jobs inside it
  inside: number;
}

/** What is wrong with a job of the open level. */
export const useNodeProblems = (
  id: string,
  data: JobNodeData,
): NodeProblems => {
  const level = useAppSelector(selectOpenLevel);
  const schemas = useAppSelector((state) => state.jobSchemas.schemas);
  const fromServer = useAppSelector((state) => state.validation.byNode[id]);

  return useMemo(() => {
    const node = { id, data } as JobNode;
    const own = jobProblems(node, level, schemas);
    return {
      own,
      fromServer: fromServer ?? [],
      inside: countProblems(node, level, schemas) - own.length,
    };
  }, [id, data, level, schemas, fromServer]);
};
