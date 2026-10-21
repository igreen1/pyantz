import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  applyScheme,
  jsonEditorTheme,
  preferredScheme,
  useColorScheme,
} from "./theme";

/** A stand-in for the browser's setting, which can be changed while the page is open. */
function browserScheme(initial: "light" | "dark") {
  let dark = initial === "dark";
  const listeners = new Set<() => void>();
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      get matches() {
        return dark;
      },
      addEventListener: (_: string, listener: () => void) =>
        listeners.add(listener),
      removeEventListener: (_: string, listener: () => void) =>
        listeners.delete(listener),
    })),
  );
  const change = (next: "light" | "dark") => {
    dark = next === "dark";
    listeners.forEach((listener) => listener());
  };
  return Object.assign(change, { listening: () => listeners.size });
}

function Probe() {
  return <p>{useColorScheme()}</p>;
}

afterEach(() => {
  vi.unstubAllGlobals();
  document.documentElement.removeAttribute("data-bs-theme");
});

describe("theme", () => {
  it("is light when the browser cannot say", () => {
    vi.stubGlobal("matchMedia", undefined);
    expect(preferredScheme()).toBe("light");
  });

  it.each(["light", "dark"] as const)(
    "follows a browser set to %s",
    (scheme) => {
      browserScheme(scheme);
      expect(preferredScheme()).toBe(scheme);
    },
  );

  it("puts the scheme on the page", () => {
    applyScheme("dark");
    expect(document.documentElement).toHaveAttribute("data-bs-theme", "dark");
  });

  it("applies the browser's scheme and follows it when it changes", () => {
    const change = browserScheme("dark");
    render(<Probe />);
    expect(screen.getByText("dark")).toBeInTheDocument();
    expect(document.documentElement).toHaveAttribute("data-bs-theme", "dark");

    act(() => change("light"));
    expect(screen.getByText("light")).toBeInTheDocument();
    expect(document.documentElement).toHaveAttribute("data-bs-theme", "light");
  });

  it("stops listening when the page is closed", () => {
    const browser = browserScheme("light");
    const { unmount } = render(<Probe />);
    expect(browser.listening()).toBe(1);
    unmount();
    expect(browser.listening()).toBe(0);
  });

  it("gives the json editor a dark theme only in the dark", () => {
    expect(jsonEditorTheme("light")).toBeUndefined();
    expect(jsonEditorTheme("dark")).toBeDefined();
  });
});
