import { describe, expect, it } from "vitest";

import {
  defaultScenarioRequest,
  scenarioFromMovie,
} from "@/lib/scenario-defaults";
import type { UpcomingMovie } from "@/types/domain";

const movie: UpcomingMovie = {
  id: "legendary-dune-part-three",
  title: "Dune: Part Three",
  release_date: "2026-12-18",
  synopsis:
    "The next chapter in Denis Villeneuve's adaptation of Frank Herbert's Dune saga.",
  genres: ["Science Fiction", "Adventure", "Unknown Genre"],
  poster_url: "/films/dune-part-three.jpg",
  backdrop_url: "/films/dune-part-three-wide.jpg",
  director: "Denis Villeneuve",
  cast: ["Timothee Chalamet", "Zendaya"],
  studio: "Legendary Entertainment",
  data_source: "official_seed",
  forecast_ready: true,
};

describe("scenarioFromMovie", () => {
  it("transfers only known real-film metadata into the scenario lab", () => {
    const request = scenarioFromMovie(movie);

    expect(request.title).toBe(movie.title);
    expect(request.synopsis).toBe(movie.synopsis);
    expect(request.genres).toEqual(["Science Fiction", "Adventure"]);
    expect(request.director).toBe("Denis Villeneuve");
    expect(request.cast).toEqual(movie.cast);
    expect(request.studio).toBe("Legendary Entertainment");
  });

  it("keeps assumptions visibly separate from catalog metadata", () => {
    const request = scenarioFromMovie(movie);

    expect(request.budget).toBe(defaultScenarioRequest.budget);
    expect(request.marketing_budget).toBe(
      defaultScenarioRequest.marketing_budget,
    );
    expect(request.social_buzz).toBe(0);
    expect(request.trailer_engagement).toBe(0);
  });
});
