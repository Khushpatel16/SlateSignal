import { expect, test } from "@playwright/test";

test("live local stack renders forecast data without browser errors", async ({
  page,
}, testInfo) => {
  test.skip(
    !process.env.LIVE_QA,
    "Set LIVE_QA=1 while the inference service is running.",
  );

  const browserErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(message.text());
  });
  page.on("pageerror", (error) => browserErrors.push(error.message));

  await page.addInitScript(() => {
    window.localStorage.setItem("slatesignal-cookie-consent", "essential");
  });
  await page.goto("/");
  await expect(page.getByText("Locked real-film forecast")).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("live-forecast-desk.png"),
    fullPage: true,
  });

  await page
    .getByRole("link", { name: /Dune: Part Three/ })
    .first()
    .click();
  await expect(page.getByText("Forecast time machine")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sources" })).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("live-movie-report.png"),
    fullPage: true,
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Search" }).click();
  await page
    .getByPlaceholder("Search films and workspaces")
    .fill("Spider-Man: No Way Home");
  const releasedFilm = page.getByRole("link", {
    name: /Spider-Man: No Way Home/,
  });
  await expect(releasedFilm).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("live-catalog-search.png"),
  });
  await releasedFilm.click();
  await expect(
    page.getByRole("heading", { name: "Spider-Man: No Way Home" }),
  ).toBeVisible();
  await expect(page.getByText("Final reported actual")).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("live-released-film-report.png"),
    fullPage: true,
  });

  expect(browserErrors).toEqual([]);
});

test("live decision workspaces render without browser errors", async ({
  page,
}, testInfo) => {
  test.skip(
    !process.env.LIVE_QA,
    "Set LIVE_QA=1 while the inference service is running.",
  );

  const browserErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(message.text());
  });
  page.on("pageerror", (error) => browserErrors.push(error.message));
  await page.addInitScript(() => {
    window.localStorage.setItem("slatesignal-cookie-consent", "essential");
  });

  const surfaces = [
    {
      path: "/calendar",
      heading: "Release calendar",
      ready: "Dune: Part Three",
      file: "calendar",
    },
    {
      path: "/compare",
      heading: "Compare forecasts",
      ready: "Evidence matrix",
      file: "compare",
    },
    {
      path: "/backtests",
      heading: "Backtests",
      ready: "Snow White",
      file: "backtests",
    },
    {
      path: "/research",
      heading:
        "Bias-Aware Financial Success Prediction for Film Productions Using Multi-Modal NLP",
      ready: "Model tournament",
      file: "research",
    },
    {
      path: "/lab",
      heading: "Greenlight Lab",
      ready: "Working title",
      file: "lab",
    },
  ];

  for (const surface of surfaces) {
    await page.goto(surface.path);
    await expect(
      page.getByRole("heading", { name: surface.heading }),
    ).toBeVisible();
    await expect(page.getByText(surface.ready).first()).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath(`live-${surface.file}.png`),
      fullPage: true,
    });
  }

  expect(browserErrors).toEqual([]);
});
