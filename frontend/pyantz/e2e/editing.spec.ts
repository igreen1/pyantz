import AxeBuilder from "@axe-core/playwright";
import { API_URL } from "../playwright.config";
import {
  MKDIR,
  addJob,
  addMkdir,
  connect,
  expect,
  exportedConfig,
  importConfig,
  localSubmitter,
  nodes,
  nopJob,
  open,
  test,
} from "./helpers";

test("a chain built on the board exports as a valid config (T2.2)", async ({
  page,
  request,
}) => {
  await open(page);
  await addMkdir(page, { x: 150, y: 80 }, "/tmp/pyantz-e2e/a");
  await addMkdir(page, { x: 150, y: 240 }, "/tmp/pyantz-e2e/b");
  await addMkdir(page, { x: 150, y: 400 }, "/tmp/pyantz-e2e/c");
  await expect(nodes(page)).toHaveCount(3);

  await connect(page, 0, 1);
  await connect(page, 1, 2);

  const config = await exportedConfig(page);
  expect(config.jobs).toHaveLength(3);
  const [first, second, third] = config.jobs;
  expect(first.depends_on).toBeUndefined();
  expect(second.depends_on).toEqual([first.job_id]);
  expect(third.depends_on).toEqual([second.job_id]);
  expect(third.parameters).toEqual({ dir_path: "/tmp/pyantz-e2e/c" });

  const response = await request.post(
    `${API_URL("main")}/api/v1.0/config/validate`,
    {
      data: config,
    },
  );
  expect(await response.json()).toEqual({ valid: true, errors: [] });
});

test("a circle is refused, with the reason", async ({ page }) => {
  await open(page);
  await addMkdir(page, { x: 150, y: 80 }, "/tmp/a");
  await addMkdir(page, { x: 150, y: 300 }, "/tmp/b");
  await connect(page, 0, 1);

  await connect(page, 1, 0);

  await expect(page.getByRole("alert")).toContainText("circle");
  const config = await exportedConfig(page);
  expect(config.jobs[0].depends_on).toBeUndefined();
});

test("delete removes the selected job and its dependencies; undo brings them back (T2.4, T3.6)", async ({
  page,
}) => {
  await open(page);
  await addMkdir(page, { x: 150, y: 80 }, "/tmp/a");
  await addMkdir(page, { x: 150, y: 300 }, "/tmp/b");
  await connect(page, 0, 1);

  await nodes(page).first().click();
  await page.keyboard.press("Delete");

  await expect(nodes(page)).toHaveCount(1);
  expect((await exportedConfig(page)).jobs[0].depends_on).toBeUndefined();

  await page.keyboard.press("Control+z");
  await expect(nodes(page)).toHaveCount(2);
  expect((await exportedConfig(page)).jobs[1].depends_on).toHaveLength(1);

  await page.keyboard.press("Control+y");
  await expect(nodes(page)).toHaveCount(1);
});

test("the right click menu adds a job where it was opened and edits a job", async ({
  page,
}) => {
  await open(page);

  await page
    .locator(".react-flow__pane")
    .click({ button: "right", position: { x: 300, y: 200 } });
  await page.getByRole("menuitem", { name: "Add Job" }).click();
  await expect(page.getByLabel("Search jobs")).toBeFocused();
  await addJob(page, MKDIR);
  await expect(nodes(page)).toHaveCount(1);

  await nodes(page).first().click({ button: "right" });
  await page.getByRole("menuitem", { name: "Edit Job" }).click();
  await expect(page.getByTestId("inspector")).toBeVisible();
});

test("the pipeline settings are in the export", async ({ page }) => {
  await open(page);
  await page.getByRole("tab", { name: "Pipeline" }).click();

  await page.getByLabel("Working directory").fill("/tmp/work");
  await page.getByLabel("Worker processes").fill("3");

  const config = await exportedConfig(page);
  expect(config.submitter).toMatchObject({
    type_: "local_proc",
    working_directory: "/tmp/work",
    number_processes: 3,
  });
});

test("an imported config is exported as it was written", async ({ page }) => {
  const original = {
    submitter: localSubmitter("/tmp/w"),
    variables: { who: "world" },
    jobs: [nopJob("a"), nopJob("b", ["a"]), nopJob("c", ["a", "b"])],
  };
  await open(page);

  await importConfig(page, original);

  expect(await exportedConfig(page)).toEqual(original);
  await expect(nodes(page)).toHaveCount(3);
});

test("a config which isn't one says what is wrong", async ({ page }) => {
  await open(page);
  await page.getByRole("button", { name: "Import JSON" }).click();

  await page.locator("#import-text").fill("{ not json");
  await page.getByRole("button", { name: "Open", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("not valid JSON");

  await page
    .locator("#import-text")
    .fill(JSON.stringify({ jobs: [{ parameters: {} }] }));
  await page.getByRole("button", { name: "Open", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    'jobs.0 has no "function"',
  );
});

test("placeholders are accepted where a number is wanted (T3.3)", async ({
  page,
}) => {
  await open(page);
  await addJob(page, "pyantz.jobs.wrappers.loops.local_for_loop");

  await page.getByLabel("Num Iterations").pressSequentially("%{count}");

  await expect(nodes(page).first()).toHaveAttribute("data-state", "ok");
});

test("the main screen has no serious accessibility problems (T3.7)", async ({
  page,
}) => {
  await open(page);
  await addMkdir(page, { x: 150, y: 120 }, "/tmp/a");
  await expect(page.getByTestId("inspector")).toBeVisible();

  const results = await new AxeBuilder({ page }).analyze();

  const serious = results.violations.filter((violation) =>
    ["serious", "critical"].includes(violation.impact ?? ""),
  );
  expect(
    serious.map(
      (violation) =>
        `${violation.id}: ${violation.nodes.map((n) => n.target).join(" ")}`,
    ),
  ).toEqual([]);
});
