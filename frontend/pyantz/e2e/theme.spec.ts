import type { Page } from "@playwright/test";
import { MKDIR, addJob, expect, open, test } from "./helpers";

/**
 * How light (0 black, 255 white) what the selector finds looks: the first
 * background colour found on it or on what it is drawn over.
 */
const brightness = (page: Page, selector: string) =>
  page
    .locator(selector)
    .first()
    .evaluate((element) => {
      for (let el: Element | null = element; el; el = el.parentElement) {
        const [red, green, blue, alpha = 1] = getComputedStyle(el)
          .backgroundColor.match(/[\d.]+/g)!
          .map(Number);
        if (alpha > 0) return (red + green + blue) / 3;
      }
      return -1;
    });

for (const [scheme, dark] of [
  ["dark", true],
  ["light", false],
] as const) {
  test.describe(`browser in ${scheme} mode`, () => {
    test.use({ colorScheme: scheme });

    test(`the page, the board and the panels are ${scheme}`, async ({
      page,
    }, info) => {
      await open(page);
      await addJob(page, MKDIR);
      await expect(page.locator("html")).toHaveAttribute(
        "data-bs-theme",
        scheme,
      );
      await expect(page.locator(".react-flow")).toHaveClass(
        dark ? /\bdark\b/ : /\blight\b/,
      );

      for (const selector of [
        "body",
        ".app-header",
        ".palette",
        ".app-side",
        ".react-flow__renderer",
        ".job-node",
      ]) {
        const level = await brightness(page, selector);
        if (dark) expect(level, selector).toBeLessThan(90);
        else expect(level, selector).toBeGreaterThan(200);
      }
      await page.screenshot({
        path: info.outputPath(`${scheme}.png`),
        fullPage: true,
      });
    });

    test(`the compiled view is ${scheme}`, async ({ page }) => {
      await open(page);
      await addJob(page, MKDIR);
      await page.getByRole("tab", { name: "Compiled" }).click();
      await expect(page.getByTestId("compiled-node")).toBeVisible();
      await expect(page.locator(".react-flow")).toHaveClass(
        dark ? /\bdark\b/ : /\blight\b/,
      );
    });
  });
}

test("the page follows the browser when it changes", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await open(page);
  await expect(page.locator("html")).toHaveAttribute("data-bs-theme", "light");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveAttribute("data-bs-theme", "dark");
});
