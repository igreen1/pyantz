import { describe, expect, it } from "vitest";
import { layoutPositions, NODE_HEIGHT, NODE_WIDTH } from "./layout";

describe("layoutPositions", () => {
  it("puts a job below the ones it depends on", () => {
    const at = layoutPositions(
      ["a", "b", "c"],
      [
        { source: "a", target: "b" },
        { source: "b", target: "c" },
      ],
    );

    expect(at.get("a")?.y).toBeLessThan(at.get("b")?.y ?? -1);
    expect(at.get("b")?.y).toBeLessThan(at.get("c")?.y ?? -1);
  });

  it("puts independent jobs side by side in the order given", () => {
    const at = layoutPositions(["a", "b"], []);

    expect(at.get("a")?.y).toBe(at.get("b")?.y);
    expect((at.get("b")?.x ?? 0) - (at.get("a")?.x ?? 0)).toBeGreaterThan(
      NODE_WIDTH,
    );
    expect(NODE_HEIGHT).toBeGreaterThan(0);
  });

  it("does not hang on a circle", () => {
    const at = layoutPositions(
      ["a", "b"],
      [
        { source: "a", target: "b" },
        { source: "b", target: "a" },
      ],
    );

    expect(at.size).toBe(2);
  });

  it("ignores edges to jobs it wasn't given", () => {
    expect(layoutPositions(["a"], [{ source: "x", target: "a" }]).size).toBe(1);
  });
});
