import { API_URL } from "../playwright.config";
import {
  LOOP,
  MKDIR,
  addJob,
  addMkdir,
  connect,
  dragJob,
  expect,
  exportedConfig,
  nodes,
  open,
  runWithCli,
  tempDir,
  test,
} from "./helpers";

const RUN_PIPELINE = "pyantz.jobs.wrappers.local.run_pipeline";

test("a loop of two jobs is built, exported, validated and run (T4.3)", async ({
  page,
  request,
}) => {
  const work = tempDir();
  await open(page);
  await addJob(page, LOOP);
  await page.getByLabel("Num Iterations").fill("1");

  await page.getByRole("button", { name: /jobs: 0 jobs/ }).click();
  await expect(
    page.getByRole("navigation", { name: "Pipeline level" }),
  ).toContainText("local_for_loop › jobs");
  await addMkdir(page, { x: 150, y: 80 }, `${work}/first`);
  await addMkdir(page, { x: 150, y: 300 }, `${work}/second`);
  await connect(page, 0, 1);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Pipeline", exact: true })
    .click();

  await expect(
    page.getByRole("button", { name: /jobs: 2 jobs/ }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Pipeline" }).click();
  await page.getByLabel("Working directory").fill(`${work}/work`);
  const config = await exportedConfig(page);

  const [loop] = config.jobs;
  expect(loop.parameters.num_iterations).toBe(1);
  expect(loop.parameters.jobs).toHaveLength(2);
  expect(loop.parameters.jobs[1].depends_on).toEqual([
    loop.parameters.jobs[0].job_id,
  ]);
  const validated = await request.post(
    `${API_URL("main")}/api/v1.0/config/validate`,
    {
      data: config,
    },
  );
  expect(await validated.json()).toEqual({ valid: true, errors: [] });
  runWithCli(config);
});

test("three levels deep can be built, navigated and exported (T4.5)", async ({
  page,
}) => {
  await open(page);
  await addJob(page, RUN_PIPELINE);
  await page.getByRole("button", { name: /jobs: 0 jobs/ }).click();
  await dragJob(page, RUN_PIPELINE, { x: 200, y: 100 });
  await page.getByRole("button", { name: /jobs: 0 jobs/ }).click();
  await dragJob(page, MKDIR, { x: 200, y: 100 });
  await page.getByLabel("Dir Path").fill("/tmp/deep");

  const crumbs = page.getByRole("navigation", { name: "Pipeline level" });
  await expect(crumbs).toContainText("run_pipeline › jobs");
  await expect(crumbs.getByRole("listitem")).toHaveCount(3);
  await crumbs.getByRole("button", { name: "Pipeline", exact: true }).click();
  await expect(crumbs.getByRole("listitem")).toHaveCount(1);
  await expect(nodes(page)).toHaveCount(1);

  const config = await exportedConfig(page);
  const innermost = config.jobs[0].parameters.jobs[0].parameters.jobs[0];
  expect(innermost.function).toBe(MKDIR);
  expect(innermost.parameters).toEqual({ dir_path: "/tmp/deep" });
});

test("a job inside another is reached from the problems list", async ({
  page,
}) => {
  await open(page);
  await addJob(page, RUN_PIPELINE);
  await page.getByRole("button", { name: /jobs: 0 jobs/ }).click();
  await dragJob(page, MKDIR, { x: 200, y: 100 }); // its dir_path is still empty
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Pipeline", exact: true })
    .click();
  await expect(nodes(page).first()).toHaveAttribute("data-state", "inside");

  await page.getByRole("tab", { name: /Problems/ }).click();
  await page.getByRole("button", { name: /run_pipeline › mkdir/ }).click();

  await expect(
    page.getByRole("navigation", { name: "Pipeline level" }),
  ).toContainText("run_pipeline › jobs");
  await expect(page.getByTestId("inspector")).toContainText(
    "dir_path is required",
  );
});

test("a dependency can't be made between levels, and a level is entered from its job", async ({
  page,
}) => {
  await open(page);
  await addJob(page, RUN_PIPELINE);
  await page.getByRole("button", { name: /jobs: 0 jobs/ }).click();

  // inside, the only jobs there are in this level
  await expect(nodes(page)).toHaveCount(0);
  await addJob(page, MKDIR);
  await expect(nodes(page)).toHaveCount(1);
  await expect(
    page.getByRole("navigation", { name: "Pipeline level" }),
  ).toContainText("run_pipeline › jobs");
});

test("a parameter which holds one job does not take a second", async ({
  page,
}) => {
  await open(page);
  await addJob(page, "pyantz.jobs.branching.if_else.if_else");
  await page.getByRole("button", { name: /if_true: none/ }).click();
  await dragJob(page, MKDIR, { x: 200, y: 100 });
  await page.getByLabel("Dir Path").fill("/tmp/only");
  await expect(nodes(page)).toHaveCount(1);

  // the palette says why, and gives no job to add
  await expect(page.getByRole("status")).toContainText(
    "if_true takes a single job",
  );
  await expect(page.locator(".palette-job").first()).toBeDisabled();
  await page.locator(".react-flow__pane").click({
    button: "right",
    position: { x: 300, y: 200 },
  });
  await expect(page.getByRole("menuitem", { name: "Add Job" })).toBeDisabled();
  await page.keyboard.press("Escape");
  await dragJob(page, MKDIR, { x: 300, y: 250 });
  await expect(nodes(page)).toHaveCount(1);

  // the other branch is a parameter of its own, and takes its job
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Pipeline", exact: true })
    .click();
  await page.getByRole("button", { name: /if_false: none/ }).click();
  await expect(page.locator(".palette-job").first()).toBeEnabled();
  await dragJob(page, MKDIR, { x: 200, y: 100 });
  await page.getByLabel("Dir Path").fill("/tmp/other");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Pipeline", exact: true })
    .click();

  const [branch] = (await exportedConfig(page)).jobs;
  expect(branch.parameters.if_true.parameters).toEqual({
    dir_path: "/tmp/only",
  });
  expect(branch.parameters.if_false.parameters).toEqual({
    dir_path: "/tmp/other",
  });
});
