import { describe, expect, it } from "vitest";
import { configToGraph } from "./convert";
import { mapServerErrors } from "./errors";
import { nestedKinds, sequentialIds } from "../test/fixtures";

const { level } = configToGraph(
  {
    submitter: { type_: "local_proc", working_directory: "w" },
    jobs: [
      {
        job_id: "a",
        function: "pyantz.jobs.testing.nop.do_nothing",
        parameters: {},
      },
      {
        job_id: "loop",
        function: "pyantz.jobs.wrappers.loops.local_for_loop",
        parameters: {
          jobs: [
            {
              job_id: "inner",
              function: "pyantz.jobs.testing.nop.do_nothing",
              parameters: {},
            },
          ],
        },
      },
    ],
  },
  nestedKinds,
  sequentialIds(),
);

describe("mapServerErrors", () => {
  it("attaches a problem to the job it names", () => {
    const mapped = mapServerErrors(level, [
      "jobs: Value error, Invalid jobs:\n- Job 'a' depends on unknown job 'z'",
    ]);

    expect(mapped.byNode).toEqual({
      n1: ["Job 'a' depends on unknown job 'z'"],
    });
    expect(mapped.unmapped).toEqual(["jobs: Value error, Invalid jobs:"]);
  });

  it("finds jobs in nested levels", () => {
    const mapped = mapServerErrors(level, ["Job 'inner' is wrong"]);

    expect(Object.keys(mapped.byNode)).toHaveLength(1);
    expect(mapped.unmapped).toEqual([]);
  });

  it("attaches a problem about two jobs to both", () => {
    const mapped = mapServerErrors(level, ["Job 'a' clashes with job 'loop'"]);

    expect(Object.keys(mapped.byNode)).toEqual(["n1"]);
  });

  it("keeps what names no job as unmapped", () => {
    const mapped = mapServerErrors(level, [
      "submitter.working_directory: Field required",
      "Job 'ghost' is wrong",
    ]);

    expect(mapped.byNode).toEqual({});
    expect(mapped.unmapped).toHaveLength(2);
  });
});
