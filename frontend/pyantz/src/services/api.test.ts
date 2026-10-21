import { afterEach, describe, expect, it, vi } from "vitest";
import { AxiosError, type InternalAxiosRequestConfig } from "axios";
import api, {
  errorList,
  errorMessage,
  getToken,
  setToken,
  setUnauthorizedHandler,
} from "./api";

afterEach(() => {
  setToken(null);
  setUnauthorizedHandler(undefined);
});

describe("api", () => {
  it("requests the versioned api under /api (T1.7)", () => {
    // no doubled /api, which only worked through the dev proxy
    expect(api.getUri({ url: "/jobs/get_all_jobs" })).toBe(
      "/api/v1.0/jobs/get_all_jobs",
    );
  });
});

describe("the token", () => {
  // run a request through the interceptors with an adapter which answers
  const request = (status = 200) =>
    api.get("/x", {
      adapter: async (config: InternalAxiosRequestConfig) => {
        const response = {
          data: {},
          status,
          statusText: "",
          headers: {},
          config,
        };
        if (status >= 400) {
          throw new AxiosError(
            "failed",
            String(status),
            config,
            null,
            response as never,
          );
        }
        return response;
      },
    });

  it("is sent as a bearer token once there is one", async () => {
    setToken("secret");

    const response = await request();

    expect(response.config.headers.get("Authorization")).toBe("Bearer secret");
  });

  it("is not sent when there is none", async () => {
    const response = await request();

    expect(response.config.headers.get("Authorization")).toBeUndefined();
  });

  it("is forgotten when set to null", () => {
    setToken("secret");
    expect(getToken()).toBe("secret");

    setToken(null);

    expect(getToken()).toBeNull();
  });

  it("is kept for the tab only, never in local storage", () => {
    setToken("secret");

    expect(sessionStorage.getItem("pyantz-api-token")).toBe("secret");
    expect(JSON.stringify({ ...localStorage })).not.toContain("secret");
  });

  it("calls the handler when the api turns a request down, and still fails it", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);

    await expect(request(401)).rejects.toBeInstanceOf(AxiosError);

    expect(handler).toHaveBeenCalledOnce();
  });

  it("does not call the handler for other failures", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);

    await expect(request(500)).rejects.toBeInstanceOf(AxiosError);

    expect(handler).not.toHaveBeenCalled();
  });

  it("copes with storage which can't be used", () => {
    const broken = vi
      .spyOn(Storage.prototype, "getItem")
      .mockImplementation(() => {
        throw new Error("blocked");
      });
    const brokenSet = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new Error("blocked");
      });

    expect(getToken()).toBeNull();
    expect(() => setToken("x")).not.toThrow();

    broken.mockRestore();
    brokenSet.mockRestore();
  });
});

describe("errorMessage and errorList", () => {
  const failure = (data: unknown, message = "Request failed") => {
    const error = new AxiosError(message);
    error.response = { data } as AxiosError["response"];
    return error;
  };

  it("prefers the detail sent by the server", () => {
    expect(errorMessage(failure({ detail: "No such job: x" }))).toBe(
      "No such job: x",
    );
  });

  it("joins a list of problems, or lists them", () => {
    const error = failure({ detail: ["a: bad", "b: worse"] });

    expect(errorMessage(error)).toBe("a: bad; b: worse");
    expect(errorList(error)).toEqual(["a: bad", "b: worse"]);
  });

  it("falls back to the axios message", () => {
    expect(errorMessage(new AxiosError("Network Error"))).toBe("Network Error");
    expect(errorList(new AxiosError("Network Error"))).toEqual([
      "Network Error",
    ]);
  });

  it("handles things which are not axios errors", () => {
    expect(errorMessage(new Error("boom"))).toBe("boom");
    expect(errorMessage("text")).toBe("text");
  });
});
