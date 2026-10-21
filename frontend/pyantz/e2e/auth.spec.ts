import { expect, test } from "./helpers";

test.use({ allowedConsole: [/401/] });

const TOKEN = "e2e-secret";

test("the token is asked for, checked, remembered for the tab, and can be forgotten (T5.6)", async ({
  page,
}) => {
  await page.goto("/");
  const prompt = page.getByRole("dialog", { name: "API token" });
  await expect(prompt).toBeVisible();

  await prompt.getByLabel("API token").fill("wrong");
  await prompt.getByRole("button", { name: "Use token" }).click();
  await expect(prompt.getByRole("alert")).toContainText("not accepted");

  await prompt.getByLabel("API token").fill(TOKEN);
  await prompt.getByRole("button", { name: "Use token" }).click();
  await expect(page.locator(".palette-job").first()).toBeVisible();
  await expect(prompt).toHaveCount(0);

  // kept for this tab: a reload does not ask again
  await page.reload();
  await expect(page.locator(".palette-job").first()).toBeVisible();
  await expect(page.getByRole("dialog", { name: "API token" })).toHaveCount(0);

  await page.getByRole("button", { name: "Forget token" }).click();
  await page.reload();
  await expect(page.getByRole("dialog", { name: "API token" })).toBeVisible();
});

test("the token is never put in the address or in local storage", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator("#api-token").fill(TOKEN);
  await page.getByRole("button", { name: "Use token" }).click();
  await expect(page.locator(".palette-job").first()).toBeVisible();

  expect(page.url()).not.toContain(TOKEN);
  const local = await page.evaluate(() => JSON.stringify({ ...localStorage }));
  expect(local).not.toContain(TOKEN);
});
