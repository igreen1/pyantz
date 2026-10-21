import { describe, expect, it } from "vitest";
import { groupOf } from "./groups";

describe("groupOf", () => {
  it("groups the jobs of pyantz by their area", () => {
    expect(groupOf("pyantz.jobs.files.simple.mkdir")).toBe("files");
    expect(groupOf("pyantz.jobs.branching.if_else.if_else")).toBe("branching");
  });

  it("groups other jobs by their module", () => {
    expect(groupOf("my_pkg.tasks.clean")).toBe("my_pkg.tasks");
  });

  it("has a group for a bare name", () => {
    expect(groupOf("clean")).toBe("other");
  });
});
