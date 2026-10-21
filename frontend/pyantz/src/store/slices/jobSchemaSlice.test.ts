import { beforeEach, describe, expect, it, vi } from "vitest";
import { AxiosError } from "axios";
import api from "../../services/api";
import { makeStore } from "../store";
import { fetchJobSchemas } from "./jobSchemaSlice";

vi.mock("../../services/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../services/api")>()),
  default: { get: vi.fn() },
}));

const get = vi.mocked(api.get);

const schemaFor = (title: string) => ({ data: { json_schema: { title } } });

describe("fetchJobSchemas", () => {
  beforeEach(() => {
    get.mockReset();
  });

  it("loads every schema", async () => {
    get.mockImplementation(async (url) => schemaFor(url));
    const store = makeStore();

    await store.dispatch(fetchJobSchemas(["a", "b"]));

    const state = store.getState().jobSchemas;
    expect(state.status).toBe("succeeded");
    expect(Object.keys(state.schemas)).toEqual(["a", "b"]);
    expect(state.errors).toEqual({});
  });

  it("keeps the other schemas when one fails (T1.5)", async () => {
    get.mockImplementation(async (url) => {
      if (url === "/jobs/schema/bad") {
        throw new AxiosError("Request failed with status code 500");
      }
      return schemaFor(url);
    });
    const store = makeStore();

    await store.dispatch(fetchJobSchemas(["a", "bad", "c"]));

    const state = store.getState().jobSchemas;
    expect(state.status).toBe("succeeded");
    expect(Object.keys(state.schemas)).toEqual(["a", "c"]);
    expect(state.errors).toEqual({
      bad: "Request failed with status code 500",
    });
  });

  it("fails when no schema can be loaded", async () => {
    get.mockImplementation(async () => {
      throw new AxiosError("Network Error");
    });
    const store = makeStore();

    await store.dispatch(fetchJobSchemas(["a", "b"]));

    const state = store.getState().jobSchemas;
    expect(state.status).toBe("failed");
    expect(state.error).toContain("Network Error");
  });
});
