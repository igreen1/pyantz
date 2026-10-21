import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test as base, type Page } from "@playwright/test";

export const NOP = "pyantz.jobs.testing.nop.do_nothing";
export const LOOP = "pyantz.jobs.wrappers.loops.local_for_loop";
export const MKDIR = "pyantz.jobs.files.simple.mkdir";
export const SET_VARIABLES = "pyantz.jobs.wrappers.variables.set_variables";

/** Every test fails on anything the browser logs as an error or a warning. */
export const test = base.extend<{
  consoleProblems: string[];
  // console messages which a test expects, e.g. the browser's note of a 403
  allowedConsole: RegExp[];
}>({
  allowedConsole: [[], { option: true }],
  consoleProblems: [
    async ({ page, allowedConsole }, use) => {
      const problems: string[] = [];
      page.on("pageerror", (error) =>
        problems.push(`pageerror: ${error.message}`),
      );
      page.on("console", (message) => {
        if (message.type() !== "error" && message.type() !== "warning") return;
        if (allowedConsole.some((pattern) => pattern.test(message.text())))
          return;
        problems.push(`${message.type()}: ${message.text()}`);
      });
      await use(problems);
      expect(problems, "browser console problems").toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };

/** Open the page and wait until the jobs and their schemas are loaded. */
export const open = async (page: Page) => {
  await page.goto("/");
  await expect(page.locator(".palette-job").first()).toBeVisible();
  // the schemas are fetched after the list; importing and adding need them
  await page.waitForFunction(() =>
    document.querySelector("[data-schemas-ready]"),
  );
};

/** Add a job by clicking it in the palette. */
export const addJob = async (page: Page, fn: string) => {
  await page.locator(".palette-job-path", { hasText: fn }).first().click();
};

export const importConfig = async (page: Page, config: unknown) => {
  await page.getByRole("button", { name: "Import JSON" }).click();
  await page.locator("#import-text").fill(JSON.stringify(config));
  await page.getByRole("button", { name: "Open", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
};

/** The config the export dialog shows. */
export const exportedConfig = async (page: Page) => {
  await page.getByRole("button", { name: "Export JSON" }).click();
  const text = await page.getByTestId("export-text").inputValue();
  await page.getByRole("button", { name: "Close" }).click();
  return JSON.parse(text);
};

export const nodes = (page: Page) => page.getByTestId("job-node");

/** Make a job depend on another by dragging from one's bottom to the other's top. */
export const connect = async (page: Page, from: number, to: number) => {
  const source = nodes(page).nth(from).locator(".react-flow__handle.source");
  const target = nodes(page).nth(to).locator(".react-flow__handle.target");
  await source.dragTo(target);
};

/** Add a job by dragging it from the palette onto the board. */
export const dragJob = async (
  page: Page,
  fn: string,
  at: { x: number; y: number },
) => {
  await page
    .locator(".palette-job-path", { hasText: fn })
    .first()
    .dragTo(page.locator(".react-flow__pane"), { targetPosition: at });
};

/** Add a mkdir job where given, with the directory filled in. */
export const addMkdir = async (
  page: Page,
  at: { x: number; y: number },
  dir: string,
) => {
  await dragJob(page, MKDIR, at);
  await page.getByLabel("Dir Path").fill(dir);
};

export const nopJob = (id: string, dependsOn: string[] = []) => ({
  job_id: id,
  function: NOP,
  parameters: {},
  ...(dependsOn.length > 0 ? { depends_on: dependsOn } : {}),
});

export const localSubmitter = (dir: string) => ({
  type_: "local_proc",
  working_directory: dir,
});

/** The root of the repository, to run `pyantz` from. */
export const REPO_ROOT = fileURLToPath(new URL("../../..", import.meta.url));

/** Run a config with the command line, as a user would; throws if it fails. */
export const runWithCli = (config: unknown): string => {
  const dir = mkdtempSync(join(tmpdir(), "pyantz-e2e-cli-"));
  const file = join(dir, "pipeline.json");
  writeFileSync(file, JSON.stringify(config));
  return execFileSync("uv", ["run", "pyantz", file], {
    cwd: REPO_ROOT,
    encoding: "utf8",
  });
};

export const tempDir = (): string =>
  mkdtempSync(join(tmpdir(), "pyantz-e2e-work-"));
