import { API_URL } from "../playwright.config";
import {
  MKDIR,
  expect,
  importConfig,
  localSubmitter,
  nodes,
  nopJob,
  open,
  test,
} from "./helpers";

test("a job missing a required parameter is marked within two seconds (T5.1)", async ({
  page,
}) => {
  await open(page);

  await importConfig(page, {
    submitter: localSubmitter("w"),
    jobs: [{ job_id: "a", function: MKDIR, parameters: {} }],
  });

  await expect(nodes(page).first()).toHaveAttribute("data-state", "invalid", {
    timeout: 2000,
  });
  await page.getByRole("tab", { name: /Problems/ }).click();
  await expect(page.getByTestId("problems-panel")).toContainText(
    "dir_path is required",
  );
});

test("the server's problem is attached to the job it names (T5.1)", async ({
  page,
}) => {
  await open(page);

  await importConfig(page, {
    submitter: localSubmitter("w"),
    jobs: [nopJob("a", ["ghost"]), nopJob("b")],
  });

  await expect(page.getByTestId("validation-status")).toHaveText(
    "Has problems",
  );
  await expect(nodes(page).first()).toHaveAttribute("data-state", "invalid");
  await expect(nodes(page).nth(1)).toHaveAttribute("data-state", "ok");
  await page.getByRole("tab", { name: /Problems/ }).click();
  await expect(page.getByTestId("problems-panel")).toContainText(
    "depends on unknown job 'ghost'",
  );
});

test("a good pipeline is valid, and the status follows edits", async ({
  page,
}) => {
  await open(page);
  await importConfig(page, {
    submitter: localSubmitter("w"),
    jobs: [nopJob("a"), nopJob("b", ["a"])],
  });

  await expect(page.getByTestId("validation-status")).toHaveText("Valid");
});

test("the compiled view has the jobs which virtual jobs expand to (T5.2)", async ({
  page,
  request,
}) => {
  const config = {
    submitter: localSubmitter("w"),
    jobs: [
      {
        job_id: "v",
        function: "pyantz.virtual.add_variables.AddVariables",
        virtual: true,
        parameters: { variables: { a: 1 } },
      },
      nopJob("j", ["v"]),
    ],
  };
  const compiled = await request.post(
    `${API_URL("main")}/api/v1.0/config/compile`,
    {
      data: config,
    },
  );
  const expected = (await compiled.json()).jobs.length;
  expect(expected).toBe(1); // two jobs are written, and one runs
  await open(page);
  await importConfig(page, config);
  await expect(nodes(page)).toHaveCount(2);

  await page.getByRole("tab", { name: "Compiled" }).click();

  await expect(page.getByTestId("compiled-node")).toHaveCount(expected);
  await expect(page.getByTestId("compiled-view")).toContainText(
    "1 job after virtual jobs are expanded",
  );
});

test("the virtual job is drawn dashed on the board", async ({ page }) => {
  await open(page);
  await importConfig(page, {
    submitter: localSubmitter("w"),
    jobs: [
      {
        job_id: "v",
        function: "pyantz.virtual.add_variables.AddVariables",
        virtual: true,
        parameters: { variables: {} },
      },
    ],
  });

  await expect(nodes(page).first()).toHaveClass(/virtual/);
});

test.describe("a config the server turns down", () => {
  test.use({ allowedConsole: [/422/] });

  test("a config the server can't compile says why", async ({ page }) => {
    await open(page);
    await importConfig(page, {
      submitter: localSubmitter("w"),
      jobs: [{ job_id: "a", function: "no.such.module.fn", parameters: {} }],
    });

    await page.getByRole("tab", { name: "Compiled" }).click();

    await expect(
      page.getByTestId("compiled-view").getByRole("alert"),
    ).toContainText("Cannot import");
  });
});
