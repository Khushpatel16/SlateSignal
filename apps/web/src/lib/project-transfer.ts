import type { ForecastRequest, UpcomingMovie } from "@/types/domain";

const SELECTED_MOVIE_KEY = "slatesignal:selected-movie";
const SELECTED_FORECAST_KEY = "slatesignal:selected-forecast";

function readStored<T>(key: string): T | null {
  try {
    const value = window.localStorage.getItem(key);
    if (!value) return null;
    window.localStorage.removeItem(key);
    return JSON.parse(value) as T;
  } catch {
    window.localStorage.removeItem(key);
    return null;
  }
}

function peekStored<T>(key: string): T | null {
  try {
    const value = window.localStorage.getItem(key);
    return value ? (JSON.parse(value) as T) : null;
  } catch {
    window.localStorage.removeItem(key);
    return null;
  }
}

export function stageMovie(movie: UpcomingMovie) {
  window.localStorage.setItem(SELECTED_MOVIE_KEY, JSON.stringify(movie));
}

export function consumeMovie() {
  return readStored<UpcomingMovie>(SELECTED_MOVIE_KEY);
}

export function peekMovie() {
  return peekStored<UpcomingMovie>(SELECTED_MOVIE_KEY);
}

export function clearMovie() {
  window.localStorage.removeItem(SELECTED_MOVIE_KEY);
}

export function stageForecast(request: ForecastRequest) {
  window.localStorage.setItem(SELECTED_FORECAST_KEY, JSON.stringify(request));
}

export function consumeForecast() {
  return readStored<ForecastRequest>(SELECTED_FORECAST_KEY);
}

export function peekForecast() {
  return peekStored<ForecastRequest>(SELECTED_FORECAST_KEY);
}

export function clearForecast() {
  window.localStorage.removeItem(SELECTED_FORECAST_KEY);
}
