import { expect, open, test } from "./helpers";

// served by `pyantz-prod` alone: the page and the api are on the same address

test("the built page is served next to the api, and works (T6.1)", async ({
  page,
  request,
}) => {
  await open(page);

  expect(await page.locator(".palette-job").count()).toBeGreaterThan(30);
  const answer = await request.get("/api/v1.0/jobs/get_all_jobs");
  expect(answer.ok()).toBe(true);
  expect(answer.headers()["content-type"]).toContain("application/json");
});

test("a pipeline can be built and checked on the built page", async ({
  page,
}) => {
  await open(page);

  await page
    .locator(".palette-job-path", { hasText: "pyantz.jobs.files.simple.mkdir" })
    .click();
  await page.getByLabel("Dir Path").fill("/tmp/x");

  await expect(page.getByTestId("validation-status")).toHaveText("Valid");
});
