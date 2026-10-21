import { describe, expect, it } from "vitest";
import { configToGraph } from "./convert";
import {
  collectProblems,
  countProblems,
  jobProblems,
  jobLabel,
} from "./problems";
import { dumpedJobs, nestedKinds, sequentialIds } from "../test/fixtures";

const schemas = Object.fromEntries(
  Object.entries(dumpedJobs).map(([name, job]) => [name, job.json_schema]),
);

const MKDIR = "pyantz.jobs.files.simple.mkdir";
const LOOP = "pyantz.jobs.wrappers.loops.local_for_loop";

const { level } = configToGraph(
  {
    submitter: { type_: "local_proc", working_directory: "w" },
    jobs: [
      { job_id: "same", function: MKDIR, parameters: { dir_path: "ok" } },
      { job_id: "same", function: MKDIR, parameters: {} },
      {
        job_id: "loop",
        function: LOOP,
        parameters: {
          num_iterations: 2,
          jobs: [{ function: MKDIR, parameters: { dir_path: 3 } }],
        },
      },
    ],
  },
  nestedKinds,
  sequentialIds(),
);

describe("jobProblems", () => {
  it("lists parameter problems and duplicate ids", () => {
    expect(jobProblems(level.nodes[0], level, schemas)).toEqual([
      'job_id "same" is used by another job of this level',
    ]);
    expect(jobProblems(level.nodes[1], level, schemas)).toEqual([
      "dir_path is required",
      'job_id "same" is used by another job of this level',
    ]);
  });
});

describe("countProblems", () => {
  it("counts the jobs inside a job", () => {
    expect(countProblems(level.nodes[2], level, schemas)).toBe(1);
  });
});

describe("collectProblems", () => {
  it("finds problems at every depth, with the way to them", () => {
    const found = collectProblems(level, schemas, { n4: ["from the server"] });

    expect(found.map((entry) => entry.path.length)).toEqual([0, 0, 0, 1]);
    expect(found[2].messages).toEqual(["from the server"]);
    expect(found[3].path).toEqual([{ nodeId: "n4", param: "jobs" }]);
  });
});

describe("jobLabel", () => {
  it("uses the name, or else the short function name", () => {
    expect(jobLabel(level.nodes[0])).toBe("mkdir");
    level.nodes[0].data.job.name = "Make it";
    expect(jobLabel(level.nodes[0])).toBe("Make it");
  });
});
