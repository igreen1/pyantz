import { beforeEach, describe, expect, it, vi } from "vitest";
import { AxiosError } from "axios";
import api from "../../services/api";
import { makeStore } from "../store";
import { fetchAvailableJobs } from "./availableJobSlice";

vi.mock("../../services/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../services/api")>()),
  default: { get: vi.fn() },
}));

const get = vi.mocked(api.get);

describe("fetchAvailableJobs", () => {
  beforeEach(() => {
    get.mockReset();
  });

  it("stores the names and descriptions", async () => {
    get.mockResolvedValue({
      data: { jobs: [{ name: "a.b", description: "does b" }] },
    });
    const store = makeStore();

    await store.dispatch(fetchAvailableJobs());

    expect(get).toHaveBeenCalledWith("/jobs/get_all_jobs");
    expect(store.getState().availableJobs).toMatchObject({
      status: "succeeded",
      items: ["a.b"],
      descriptions: ["does b"],
    });
  });

  it("stores a readable message when the request fails (T1.6)", async () => {
    get.mockImplementation(async () => {
      throw new AxiosError("Network Error");
    });
    const store = makeStore();

    await store.dispatch(fetchAvailableJobs());

    expect(store.getState().availableJobs).toMatchObject({
      status: "failed",
      error: "Network Error",
    });
  });
});
