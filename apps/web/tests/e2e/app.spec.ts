import { expect, test, type Page } from "@playwright/test";

const observedAt = "2026-07-24T12:00:00Z";

function movie(
  id: string,
  slug: string,
  title: string,
  releaseDate: string,
  director: string,
  p50: number,
  poster: string | null = null,
  backdrop: string | null = null,
) {
  return {
    id,
    slug,
    title,
    original_title: null,
    synopsis: `${title} continues its officially announced theatrical story with a source-backed release record.`,
    release_status: "confirmed",
    release_date: releaseDate,
    release_year: Number(releaseDate.slice(0, 4)),
    date_precision: "day",
    countdown_days: 147,
    genres: ["Science Fiction", "Adventure"],
    runtime_minutes: null,
    certification: null,
    original_language: "en",
    origin_country: "US",
    poster_url: poster,
    backdrop_url: backdrop,
    trailer_url: null,
    director,
    top_cast: ["Zendaya", "Timothee Chalamet"],
    studio: "Legendary Entertainment",
    forecast: {
      availability: "locked",
      p10: p50 * 0.36,
      p50,
      p90: p50 * 2.6,
      horizon_days: 147,
      data_cutoff: observedAt,
      model_version: "bert-xgb-v1",
      ledger_hash: "a".repeat(64),
    },
    worldwide_actual: null,
    buzz_momentum: 0.18,
    data_updated_at: observedAt,
    primary_source: "legendary",
    source_confidence: 0.98,
  };
}

const dune = movie(
  "dune-id",
  "dune-part-three-2026",
  "Dune: Part Three",
  "2026-12-18",
  "Denis Villeneuve",
  120_000_000,
  "/films/dune-part-three.jpg",
  "/films/dune-part-three-wide.jpg",
);
const avengers = movie(
  "avengers-id",
  "avengers-doomsday-2026",
  "Avengers: Doomsday",
  "2026-12-18",
  "Anthony Russo, Joe Russo",
  640_000_000,
);
const spider = movie(
  "spider-id",
  "spider-man-brand-new-day-2026",
  "Spider-Man: Brand New Day",
  "2026-07-31",
  "Destin Daniel Cretton",
  410_000_000,
  "/films/spider-man-brand-new-day.jpg",
);
const upcoming = [dune, avengers, spider];

const evidence = {
  source: "legendary",
  observation_type: "catalog_snapshot",
  observed_at: observedAt,
  source_url: "https://www.legendary.com/film/dune-part-three/",
  confidence: 0.98,
  raw_checksum: "b".repeat(64),
  forecast_eligible: true,
};

function officialForecast(film = dune) {
  const p50 = film.forecast.p50;
  return {
    film,
    forecast_type: "official",
    data_cutoff: observedAt,
    horizon_days: film.forecast.horizon_days,
    model_version: "bert-xgb-v1",
    model_kind: "bert_mean_pool_xgboost",
    targets: {
      worldwide_total: {
        p10: p50 * 0.36,
        p50,
        p90: p50 * 2.6,
        currency: "USD",
      },
      domestic_total: null,
      domestic_opening: null,
      international_total: null,
    },
    actuals: {
      worldwide_total: null,
      domestic_total: null,
      domestic_opening: null,
      international_total: null,
    },
    errors: {
      worldwide_total: null,
      domestic_total: null,
      domestic_opening: null,
      international_total: null,
    },
    grouped_factors: [
      {
        key: "synopsis_embedding",
        label: "Synopsis embedding",
        group: "Story",
        value: "mean-pooled BERT, 768 dimensions",
        impact: 14_000_000,
        direction: "positive",
        evidence: "Modeled directly by bert-xgb-v1.",
        source_count: 1,
      },
      {
        key: "budget",
        label: "Production budget",
        group: "Package",
        value: "$120,000,000 model imputed",
        impact: 22_000_000,
        direction: "positive",
        evidence: "Log budget is an original structured feature.",
        source_count: 1,
      },
      {
        key: "director_history",
        label: "Director history",
        group: "People",
        value: film.director,
        impact: 9_000_000,
        direction: "positive",
        evidence: "Pre-cutoff track record.",
        source_count: 1,
      },
      {
        key: "nearby_competition",
        label: "Nearby competition",
        group: "Release",
        value: "1 confirmed film within 7 days",
        impact: null,
        direction: "unknown",
        evidence: "Context only in this baseline.",
        source_count: 1,
      },
    ],
    buzz: [],
    comparables: [],
    fairness: {
      protected_attributes_used: false,
      audit_status: "watch",
      evaluation_only_attributes: ["Wikidata demographic annotations"],
      cohort_definition: "Matched budget, genre, and release year cohorts.",
      notes: ["Protected attributes are excluded from model inputs."],
    },
    evidence: [evidence],
    confidence_score: 0.61,
    feature_manifest_hash: "c".repeat(64),
    ledger_hash: film.forecast.ledger_hash,
    ledger_sequence: film.id === "dune-id" ? 2 : 3,
    generated_at: observedAt,
    limitations: [
      "Secondary revenue targets are unavailable for this baseline.",
    ],
  };
}

const scenarioForecast = {
  model_version: "scenario-engine-1.0",
  generated_at: observedAt,
  input: {},
  financials: {
    worldwide_gross: {
      low: 146_000_000,
      expected: 238_000_000,
      high: 368_000_000,
    },
    domestic_gross: {
      low: 58_000_000,
      expected: 95_000_000,
      high: 147_000_000,
    },
    international_gross: {
      low: 88_000_000,
      expected: 143_000_000,
      high: 221_000_000,
    },
    opening_weekend: {
      low: 28_000_000,
      expected: 43_000_000,
      high: 61_000_000,
    },
    break_even_gross: 205_000_000,
    expected_profit: 33_000_000,
    expected_roi: 0.26,
    break_even_probability: 0.64,
    hit_probability: 0.31,
  },
  factors: [
    {
      key: "release",
      label: "Release window",
      value: "May",
      impact: 18_000_000,
      direction: "positive",
      evidence: "Historically favorable corridor.",
      mutable: true,
    },
  ],
  synopsis_signals: [
    {
      label: "Concept clarity",
      score: 78,
      detail: "The protagonist and stakes are legible.",
    },
  ],
  robustness: {
    score: 73,
    label: "Resilient",
    profitable_scenarios: 0.68,
    downside_gross: 138_000_000,
    upside_gross: 388_000_000,
    key_risk: "Marketing efficiency",
  },
  confidence: {
    score: 76,
    level: "High",
    data_completeness: 0.91,
    calibration_segment: "high",
    caveats: ["Scenario forecasts carry structural uncertainty."],
  },
  fairness: {
    protected_attributes_used: false,
    audit_status: "watch",
    notes: ["Protected attributes are excluded."],
  },
  methodology_note: "Scenario estimate with an uncertainty interval.",
};

async function mockApi(page: Page) {
  const user = {
    id: "user-1",
    email: "maker@example.com",
    display_name: "Film Maker",
    role: "user",
    created_at: observedAt,
  };
  let sessionUser: typeof user | null = null;
  const projects: Array<Record<string, unknown>> = [];

  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();
    const identifier = decodeURIComponent(path.split("/").at(-2) ?? "");
    const selected =
      upcoming.find(
        (item) => item.id === identifier || item.slug === identifier,
      ) ?? dune;

    if (path.endsWith("/health")) {
      await route.fulfill({
        json: {
          status: "ok",
          version: "0.2",
          model_mode: "artifact",
          database: "postgresql",
          knowledge_base_loaded: true,
          tmdb_configured: true,
        },
      });
    } else if (path.endsWith("/auth/session")) {
      await route.fulfill({ json: sessionUser });
    } else if (
      path.endsWith("/auth/register") ||
      path.endsWith("/auth/login")
    ) {
      sessionUser = user;
      await route.fulfill({
        status: path.endsWith("/auth/register") ? 201 : 200,
        json: user,
      });
    } else if (path.endsWith("/auth/logout")) {
      sessionUser = null;
      await route.fulfill({ status: 204 });
    } else if (path.endsWith("/auth/me")) {
      await route.fulfill({
        status: sessionUser ? 200 : 401,
        json: sessionUser ?? { detail: "Sign in" },
      });
    } else if (path.endsWith("/projects") && method === "GET") {
      await route.fulfill({
        status: sessionUser ? 200 : 401,
        json: sessionUser ? projects : { detail: "Sign in" },
      });
    } else if (path.endsWith("/projects") && method === "POST") {
      const payload = route.request().postDataJSON();
      const saved = {
        id: `project-${projects.length + 1}`,
        ...payload,
        created_at: observedAt,
        updated_at: observedAt,
      };
      projects.unshift(saved);
      await route.fulfill({ status: 201, json: saved });
    } else if (path.endsWith("/forecast-history")) {
      await route.fulfill({
        json: [
          {
            forecast_id: `${selected.id}-forecast`,
            forecast_type: "official",
            data_cutoff: observedAt,
            horizon_days: selected.forecast.horizon_days,
            worldwide: officialForecast(selected).targets.worldwide_total,
            actual_worldwide: null,
            model_version: "bert-xgb-v1",
            ledger_hash: selected.forecast.ledger_hash,
            generated_at: observedAt,
          },
        ],
      });
    } else if (path.endsWith("/buzz")) {
      await route.fulfill({
        json: [
          {
            source: "wikimedia",
            metric: "pageviews_7d",
            value: 184_000,
            normalized_value: 71,
            momentum: 0.18,
            observed_at: observedAt,
            source_url: "https://en.wikipedia.org/",
            confidence: 0.88,
          },
        ],
      });
    } else if (/\/movies\/[^/]+\/forecast$/.test(path)) {
      await route.fulfill({ json: officialForecast(selected) });
    } else if (/\/movies\/[^/]+$/.test(path)) {
      await route.fulfill({
        json: {
          ...selected,
          budget: null,
          budget_status: "model_imputed",
          homepage_url: evidence.source_url,
          external_ids: [],
          credits: [],
          companies: [],
          releases: [
            {
              country_code: "US",
              release_type: "wide",
              release_date: selected.release_date,
              certification: null,
              note: null,
              is_confirmed: true,
            },
          ],
          actuals: [],
          evidence: [evidence],
        },
      });
    } else if (path.endsWith("/movies")) {
      await route.fulfill({
        json: {
          items: upcoming,
          total: upcoming.length,
          limit: 100,
          offset: 0,
          data_freshness: observedAt,
          attribution:
            "This product uses the TMDB API but is not endorsed or certified by TMDB.",
        },
      });
    } else if (path.endsWith("/backtests")) {
      const released = {
        ...spider,
        id: "snow-white-id",
        slug: "snow-white-2025",
        title: "Snow White",
        release_status: "gross_closed",
        release_date: "2025-03-21",
        release_year: 2025,
      };
      const actual = {
        target: "worldwide_total",
        amount: 92_629_251,
        currency: "USD",
        amount_status: "final",
        source: "research_corpus",
        source_url: "https://www.imdb.com/title/tt6208148/",
        observed_at: "2025-11-27T00:00:00Z",
        confidence: 0.72,
        conflicts: [],
      };
      await route.fulfill({
        json: {
          items: [
            {
              movie: released,
              forecast: {
                forecast_id: "snow-white-eval",
                forecast_type: "evaluation",
                data_cutoff: observedAt,
                horizon_days: null,
                worldwide: {
                  p10: 26_000_000,
                  p50: 211_000_000,
                  p90: 690_000_000,
                  currency: "USD",
                },
                actual_worldwide: actual.amount,
                model_version: "bert-xgb-v1",
                ledger_hash: "d".repeat(64),
                generated_at: observedAt,
              },
              actual_worldwide: actual,
              absolute_error: 118_370_749,
              absolute_percentage_error: 1.277,
            },
          ],
          metrics: {
            count: 24,
            mae: 115_030_680,
            median_absolute_error: 16_578_079,
            log_mae: 1.6216,
            interval_coverage: 0.75,
            interval_target: 0.8,
          },
          cutoff: null,
          model_version: null,
          methodology_note:
            "Retrospective evaluation forecasts are labeled separately.",
        },
      });
    } else if (path.endsWith("/scenarios/forecast")) {
      await route.fulfill({ json: scenarioForecast });
    } else {
      await route.fulfill({ status: 404, json: { detail: "Not found" } });
    }
  });
}

test.beforeEach(async ({ page }) => {
  await mockApi(page);
  await page.addInitScript(() => {
    window.localStorage.setItem("slatesignal-cookie-consent", "essential");
  });
});

test("real-film search opens a source-backed evidence report", async ({
  page,
}) => {
  await page.goto("/");

  await expect(page.locator("h1")).toHaveText("Dune: Part Three");
  await expect(page.getByText("Locked real-film forecast")).toBeVisible();
  await page.getByPlaceholder("Title, director, studio, genre").fill("Spider");
  await page.getByRole("link", { name: /Spider-Man: Brand New Day/ }).click();

  await expect(
    page.getByRole("heading", { name: "Spider-Man: Brand New Day" }),
  ).toBeVisible();
  await expect(page.getByText("Forecast time machine")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sources" })).toBeVisible();
  await expect(page.getByText("Ledger locked")).toBeVisible();
});

test("calendar and compare expose the December release collision", async ({
  page,
}) => {
  await page.goto("/calendar");
  await expect(
    page.getByRole("heading", { name: "Release calendar" }),
  ).toBeVisible();
  await expect(page.getByText("Dune: Part Three").first()).toBeVisible();
  await expect(page.getByText("Avengers: Doomsday").first()).toBeVisible();

  await page.goto("/compare");
  await expect(
    page.getByRole("heading", { name: "Compare forecasts" }),
  ).toBeVisible();
  await expect(page.getByText("0 days")).toBeVisible();
  await expect(page.getByText("Direct same-day collision")).toBeVisible();
});

test("backtests distinguish evaluation from official locks", async ({
  page,
}) => {
  await page.goto("/backtests");

  await expect(page.getByText("24", { exact: true })).toBeVisible();
  await expect(page.getByText("Snow White")).toBeVisible();
  await expect(
    page.getByRole("table").getByText("evaluation", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(/never presents a retrospective model run/i),
  ).toBeVisible();

  await page.goto("/research");
  await expect(
    page.getByRole("heading", {
      name: /Bias-Aware Financial Success Prediction/,
    }),
  ).toBeVisible();
  await expect(page.getByText("Promotion gates")).toBeVisible();
});

test("authenticated users can save an original scenario", async ({ page }) => {
  await page.goto("/signup");
  await page.getByLabel("Display name").fill("Film Maker");
  await page.getByLabel("Email").fill("maker@example.com");
  await page.getByLabel("Password").fill("correct-horse-battery-staple");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(
    page.getByRole("button", { name: "Open account menu" }),
  ).toBeVisible();

  await page.goto("/lab");
  await page.getByLabel("Working title").fill("Untitled orbital thriller");
  await page
    .getByLabel("Synopsis")
    .fill(
      "A flight engineer must repair a failing orbital archive before its final transmission erases the only proof of a global conspiracy.",
    );
  await page.getByRole("button", { name: "Science Fiction" }).click();
  await expect(page.getByText("$238M", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Save analysis" }).click();
  await expect(page.getByText("Forecast saved")).toBeVisible();
  await page.goto("/saved");
  await expect(
    page.getByText(/Untitled orbital thriller - 2027-10-08/).first(),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Open in lab" })).toBeVisible();
});
