import {
  expect,
  importConfig,
  localSubmitter,
  nopJob,
  open,
  test,
} from "./helpers";

const DISPATCH = "pyantz.jobs.subproc.dispatch.dispatch";

const startRun = async (page: Parameters<typeof importConfig>[0]) => {
  await page.getByRole("tab", { name: "Run" }).click();
  await page.getByRole("button", { name: "Run", exact: true }).click();
};

test("a run of three jobs finishes and every job shows as done (T5.3)", async ({
  page,
}) => {
  await open(page);
  await importConfig(page, {
    submitter: localSubmitter("ignored"),
    jobs: [nopJob("a"), nopJob("b", ["a"]), nopJob("c", ["b"])],
  });

  await startRun(page);

  await expect(page.getByTestId("run-state")).toHaveText("Succeeded", {
    timeout: 30_000,
  });
  await expect(page.getByTestId("run-report")).toContainText("3 of 3 done");
  const compiled = page.getByTestId("compiled-node");
  await expect(compiled).toHaveCount(3);
  for (const status of await compiled.evaluateAll((els) =>
    els.map((el) => el.getAttribute("data-status")),
  )) {
    expect(status).toBe("success");
  }
});

test("a failed run shows which job failed, and why (T5.4)", async ({
  page,
}) => {
  await open(page);
  await importConfig(page, {
    submitter: localSubmitter("ignored"),
    jobs: [
      nopJob("fine"),
      {
        job_id: "bad",
        function: DISPATCH,
        parameters: { cmd: ["false"] },
        depends_on: ["fine"],
      },
    ],
  });

  await startRun(page);

  await expect(page.getByTestId("run-state")).toHaveText("Failed", {
    timeout: 30_000,
  });
  await expect(
    page.getByTestId("compiled-node").filter({ hasText: "dispatch" }),
  ).toHaveAttribute("data-status", "error");
  await expect(
    page.getByTestId("run-panel").getByRole("row", { name: /bad/ }),
  ).toContainText("error");
});

test("the run is picked up again when the page is reloaded", async ({
  page,
}) => {
  await open(page);
  await importConfig(page, {
    submitter: localSubmitter("x"),
    jobs: [nopJob("a")],
  });
  await startRun(page);
  await expect(page.getByTestId("run-state")).toHaveText("Succeeded", {
    timeout: 30_000,
  });

  await page.reload();
  await page.getByRole("tab", { name: "Run" }).click();

  await expect(page.getByTestId("run-state")).toHaveText("Succeeded", {
    timeout: 15_000,
  });
});

test("the log of a run can be read", async ({ page }) => {
  await open(page);
  await importConfig(page, {
    submitter: localSubmitter("x"),
    jobs: [nopJob("a")],
  });
  await startRun(page);
  await expect(page.getByTestId("run-state")).toHaveText("Succeeded", {
    timeout: 30_000,
  });

  await page.getByRole("button", { name: "Show log" }).click();

  await expect(page.getByLabel("Run log")).not.toBeEmpty();
});

test("the run can be cleared once it is over", async ({ page }) => {
  await open(page);
  await importConfig(page, {
    submitter: localSubmitter("x"),
    jobs: [nopJob("a")],
  });
  await startRun(page);
  await expect(page.getByTestId("run-state")).toHaveText("Succeeded", {
    timeout: 30_000,
  });

  await page.getByRole("button", { name: "Clear" }).click();

  await expect(page.getByTestId("run-state")).toHaveCount(0);
});
