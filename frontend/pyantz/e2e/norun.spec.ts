import {
  expect,
  importConfig,
  localSubmitter,
  nopJob,
  open,
  test,
} from "./helpers";

test.use({ allowedConsole: [/403/] });

test("running when the server has runs switched off says how to switch them on (T5.5)", async ({
  page,
}) => {
  await open(page);
  await importConfig(page, {
    submitter: localSubmitter("w"),
    jobs: [nopJob("a")],
  });
  await page.getByRole("tab", { name: "Run" }).click();

  await page.getByRole("button", { name: "Run", exact: true }).click();

  await expect(page.getByTestId("run-panel").getByRole("alert")).toContainText(
    "PYANTZ_ALLOWED_MODULES",
  );
  await expect(page.getByTestId("run-state")).toHaveCount(0);
});

test("there is nothing to run without a job, or with problems", async ({
  page,
}) => {
  await open(page);
  await page.getByRole("tab", { name: "Run" }).click();

  await expect(
    page.getByRole("button", { name: "Run", exact: true }),
  ).toBeDisabled();
  await expect(page.getByTestId("run-panel")).toContainText("Add a job first");
});
