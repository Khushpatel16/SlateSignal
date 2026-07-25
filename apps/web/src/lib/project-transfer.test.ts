import { beforeEach, describe, expect, it } from "vitest";

import {
  defaultScenarioRequest,
  scenarioFromMovie,
} from "@/lib/scenario-defaults";
import {
  consumeForecast,
  consumeMovie,
  peekForecast,
  peekMovie,
  stageForecast,
  stageMovie,
} from "@/lib/project-transfer";
import type { UpcomingMovie } from "@/types/domain";

const realMovie: UpcomingMovie = {
  id: "sony-spider-man-brand-new-day",
  title: "Spider-Man: Brand New Day",
  release_date: "2026-07-31",
  synopsis:
    "Peter Parker begins a new chapter while the consequences of his choices reshape the people and city around him.",
  genres: ["Action", "Science Fiction"],
  poster_url: "/films/spider-man-brand-new-day.jpg",
  backdrop_url: null,
  director: "Destin Daniel Cretton",
  cast: ["Tom Holland", "Zendaya"],
  studio: "Sony Pictures",
  data_source: "official_seed",
  forecast_ready: true,
};

describe("project transfer", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("stages and consumes a catalog movie exactly once", () => {
    stageMovie(realMovie);

    expect(peekMovie()).toEqual(realMovie);
    expect(consumeMovie()).toEqual(realMovie);
    expect(consumeMovie()).toBeNull();
  });

  it("stages and consumes a forecast exactly once", () => {
    const request = scenarioFromMovie(realMovie);
    stageForecast(request);

    expect(peekForecast()).toEqual(request);
    expect(consumeForecast()).toEqual(request);
    expect(consumeForecast()).toBeNull();
  });

  it("starts a blank scenario without invented film metadata", () => {
    expect(defaultScenarioRequest.title).toBe("Untitled project");
    expect(defaultScenarioRequest.synopsis).toBe("");
    expect(defaultScenarioRequest.genres).toEqual([]);
  });

  it("discards malformed transfer records", () => {
    window.localStorage.setItem("slatesignal:selected-movie", "{bad-json");

    expect(consumeMovie()).toBeNull();
    expect(
      window.localStorage.getItem("slatesignal:selected-movie"),
    ).toBeNull();
  });
});
