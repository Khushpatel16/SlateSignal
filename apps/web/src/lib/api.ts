import type {
  ForecastRequest,
  ForecastResponse,
  OptimizeRequest,
  OptimizeResponse,
  AdminOverview,
  BacktestResponse,
  BuzzPoint,
  ForecastHistoryPoint,
  MovieDetail,
  MovieForecast,
  MovieListResponse,
  SavedProject,
  UpcomingMovie,
  User,
} from "@/types/domain";

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new ApiError(
      payload?.detail ?? "The request could not be completed.",
      response.status,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () =>
    request<{
      status: "ok" | "degraded";
      version: string;
      model_mode: "decision_engine" | "artifact";
      database: string;
      knowledge_base_loaded: boolean;
      tmdb_configured: boolean;
    }>("/health"),
  forecast: (payload: ForecastRequest) =>
    request<ForecastResponse>("/scenarios/forecast", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  optimize: (payload: OptimizeRequest) =>
    request<OptimizeResponse>("/scenarios/optimize", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  upcoming: () => request<UpcomingMovie[]>("/catalog/upcoming"),
  movies: (query = "") =>
    request<MovieListResponse>(`/movies${query ? `?${query}` : ""}`),
  movie: (identifier: string) =>
    request<MovieDetail>(`/movies/${encodeURIComponent(identifier)}`),
  movieForecast: (identifier: string, query = "") =>
    request<MovieForecast>(
      `/movies/${encodeURIComponent(identifier)}/forecast${
        query ? `?${query}` : ""
      }`,
    ),
  forecastHistory: (identifier: string) =>
    request<ForecastHistoryPoint[]>(
      `/movies/${encodeURIComponent(identifier)}/forecast-history`,
    ),
  buzz: (identifier: string) =>
    request<BuzzPoint[]>(`/movies/${encodeURIComponent(identifier)}/buzz`),
  backtests: (query = "") =>
    request<BacktestResponse>(`/backtests${query ? `?${query}` : ""}`),
  me: () => request<User>("/auth/me"),
  session: () => request<User | null>("/auth/session"),
  login: (payload: { email: string; password: string }) =>
    request<User>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  register: (payload: {
    email: string;
    display_name: string;
    password: string;
  }) =>
    request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  projects: () => request<SavedProject[]>("/projects"),
  saveProject: (payload: {
    title: string;
    project_type: "scenario" | "forecast" | "optimization";
    payload: Record<string, unknown>;
  }) =>
    request<SavedProject>("/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteProject: (id: string) =>
    request<void>(`/projects/${id}`, { method: "DELETE" }),
  adminOverview: () => request<AdminOverview>("/admin/overview"),
};

export { ApiError };
