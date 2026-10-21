import { describe, expect, it } from "vitest";
import { canConnect, makeEdge } from "./connect";
import type { JobNode, Level } from "./graph";

const node = (id: string): JobNode => ({
  id,
  type: "jobNode",
  position: { x: 0, y: 0 },
  data: { job: { function: "f", parameters: {} }, nested: {} },
});

const level = (ids: string[], edges: [string, string][] = []): Level => ({
  nodes: ids.map(node),
  edges: edges.map(([s, t]) => makeEdge(s, t)),
});

describe("canConnect (T2.5, T4.4)", () => {
  it("allows a dependency", () => {
    expect(canConnect(level(["a", "b"]), "a", "b")).toEqual({ ok: true });
  });

  it("refuses a job depending on itself", () => {
    expect(canConnect(level(["a"]), "a", "a")).toMatchObject({ ok: false });
  });

  it("refuses to close a circle", () => {
    const chain = level(
      ["a", "b", "c"],
      [
        ["a", "b"],
        ["b", "c"],
      ],
    );

    const check = canConnect(chain, "c", "a");

    expect(check).toMatchObject({ ok: false });
    expect(check.ok === false && check.reason).toContain("circle");
  });

  it("refuses a dependency which exists", () => {
    expect(canConnect(level(["a", "b"], [["a", "b"]]), "a", "b")).toMatchObject(
      {
        ok: false,
      },
    );
  });

  it("refuses jobs which are not in this level", () => {
    const check = canConnect(level(["a"]), "a", "elsewhere");

    expect(check.ok === false && check.reason).toContain("same pipeline level");
  });

  it("refuses missing ends", () => {
    expect(canConnect(level(["a"]), null, "a")).toMatchObject({ ok: false });
  });
});
