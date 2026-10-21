/**
 * Light or dark, following the browser's setting.
 *
 * Bootstrap colours everything from `data-bs-theme` on the page, so that is what
 * is set; the few things which are not Bootstrap (the board, the json editor)
 * are told by `useColorScheme`.
 */
import { useEffect, useSyncExternalStore } from "react";
import { githubDarkTheme, type ThemeInput } from "json-edit-react";

export type ColorScheme = "light" | "dark";

const DARK_QUERY = "(prefers-color-scheme: dark)";

const query = (): MediaQueryList | undefined =>
  typeof window.matchMedia === "function"
    ? window.matchMedia(DARK_QUERY)
    : undefined;

export function preferredScheme(): ColorScheme {
  return query()?.matches ? "dark" : "light";
}

/** Show the page in this scheme. */
export function applyScheme(scheme: ColorScheme) {
  document.documentElement.setAttribute("data-bs-theme", scheme);
}

function subscribe(onChange: () => void) {
  const list = query();
  list?.addEventListener("change", onChange);
  return () => list?.removeEventListener("change", onChange);
}

/** The scheme the browser asks for, kept up to date and applied to the page. */
export function useColorScheme(): ColorScheme {
  const scheme = useSyncExternalStore<ColorScheme>(
    subscribe,
    preferredScheme,
    () => "light",
  );
  useEffect(() => applyScheme(scheme), [scheme]);
  return scheme;
}

/** The theme of the json editor: its default is already the light one. */
export function jsonEditorTheme(scheme: ColorScheme): ThemeInput | undefined {
  return scheme === "dark" ? githubDarkTheme : undefined;
}
