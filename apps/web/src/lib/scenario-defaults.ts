import {
  GENRES,
  type ForecastRequest,
  type Genre,
  type UpcomingMovie,
} from "@/types/domain";

export const defaultScenarioRequest: ForecastRequest = {
  title: "Untitled project",
  synopsis: "",
  genres: [],
  budget: 25_000_000,
  marketing_budget: 12_500_000,
  release_date: "2027-10-08",
  runtime_minutes: 110,
  audience_rating: "PG-13",
  director: null,
  cast: [],
  studio: null,
  source_material: "Original",
  franchise_strength: 0,
  premium_formats: ["Standard"],
  theater_count: 2200,
  competition_score: 50,
  social_buzz: 0,
  trailer_engagement: 0,
  international_appeal: 50,
  production_readiness: 40,
};

export function scenarioFromMovie(movie: UpcomingMovie): ForecastRequest {
  const genres = movie.genres.filter((genre): genre is Genre =>
    GENRES.includes(genre as Genre),
  );
  return {
    ...defaultScenarioRequest,
    title: movie.title,
    synopsis: movie.synopsis,
    genres: genres.slice(0, 4),
    release_date: movie.release_date,
    director: movie.director,
    cast: movie.cast,
    studio: movie.studio,
  };
}
