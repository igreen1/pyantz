import { API_URL } from "../playwright.config";
import {
  MKDIR,
  SET_VARIABLES,
  addJob,
  expect,
  nodes,
  open,
  test,
} from "./helpers";

test("lists every job the api has, with descriptions", async ({
  page,
  request,
}) => {
  const response = await request.get(
    `${API_URL("main")}/api/v1.0/jobs/get_all_jobs`,
  );
  const { jobs } = (await response.json()) as {
    jobs: { name: string; description: string }[];
  };
  expect(jobs.length).toBeGreaterThan(30);

  await open(page);

  await expect(page.locator(".palette-job")).toHaveCount(jobs.length);
  await expect(page.getByText(jobs[0].description).first()).toBeVisible();
});

test("a job whose schema used to fail gets a parameter form", async ({
  page,
}) => {
  await open(page);

  await addJob(page, SET_VARIABLES);

  await expect(page.getByTestId("inspector")).toBeVisible();
  await expect(
    page.getByRole("status").filter({ hasText: "Schema unavailable" }),
  ).toHaveCount(0);
  await expect(page.getByLabel("Setter Job")).toBeVisible();
});

test("renaming a job in the inspector shows on the board", async ({ page }) => {
  await open(page);
  await addJob(page, MKDIR);

  await page.getByLabel("Name", { exact: true }).fill("make the folder");

  await expect(nodes(page).first()).toContainText("make the folder");
});

test("a new job with required parameters is marked as not in order", async ({
  page,
}) => {
  await open(page);

  await addJob(page, MKDIR);

  await expect(nodes(page).first()).toHaveAttribute("data-state", "invalid");
  await page.getByLabel("Dir Path").fill("/tmp/somewhere");
  await expect(nodes(page).first()).toHaveAttribute("data-state", "ok");
});

test("the page fills the window", async ({ page }) => {
  await open(page);

  const sizes = await page.evaluate(() => ({
    body: document.documentElement.scrollWidth - window.innerWidth,
    board:
      document.querySelector(".react-flow")?.getBoundingClientRect().height ??
      0,
    window: window.innerHeight,
  }));

  expect(sizes.body).toBeLessThanOrEqual(0);
  expect(sizes.board).toBeGreaterThan(sizes.window * 0.6);
});
