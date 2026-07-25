from fastapi.testclient import TestClient

from slatesignal.core.database import SessionLocal
from slatesignal.main import app
from slatesignal.services.bootstrap import bootstrap_historical_evaluations


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json()["knowledge_base_loaded"] is True
    assert response.headers["x-request-id"]
    assert response.headers["server-timing"].startswith("app;dur=")


def test_session_status_is_nullable_for_signed_out_visitors() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/auth/session")

    assert response.status_code == 200
    assert response.json() is None


def test_account_session_and_saved_project_flow() -> None:
    with TestClient(app) as client:
        register = client.post(
            "/v1/auth/register",
            json={
                "email": "maker@example.com",
                "display_name": "Film Maker",
                "password": "correct-horse-battery-staple",
            },
        )
        assert register.status_code == 201
        assert register.json()["role"] == "user"
        assert "slatesignal_session" in client.cookies

        me = client.get("/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == "maker@example.com"
        assert client.get("/v1/auth/session").json()["email"] == "maker@example.com"

        saved = client.post(
            "/v1/projects",
            json={
                "title": "Glass Horizon - May scenario",
                "project_type": "scenario",
                "payload": {"budget": 85_000_000, "release_date": "2027-05-21"},
            },
        )
        assert saved.status_code == 201

        projects = client.get("/v1/projects")
        assert projects.status_code == 200
        assert len(projects.json()) == 1

        deleted = client.delete(f"/v1/projects/{saved.json()['id']}")
        assert deleted.status_code == 204
        assert client.get("/v1/projects").json() == []

        logout = client.post("/v1/auth/logout")
        assert logout.status_code == 204
        assert client.get("/v1/projects").status_code == 401


def test_duplicate_email_is_rejected() -> None:
    payload = {
        "email": "duplicate@example.com",
        "display_name": "First User",
        "password": "a-secure-password-123",
    }
    with TestClient(app) as client:
        assert client.post("/v1/auth/register", json=payload).status_code == 201
        client.post("/v1/auth/logout")
        duplicate = client.post("/v1/auth/register", json=payload)

    assert duplicate.status_code == 409


def test_admin_role_and_overview() -> None:
    with TestClient(app) as client:
        register = client.post(
            "/v1/auth/register",
            headers={"X-Admin-Bootstrap-Token": "test-admin-bootstrap-token"},
            json={
                "email": "admin@slatesignal.dev",
                "display_name": "SlateSignal Admin",
                "password": "admin-password-is-long",
            },
        )
        assert register.json()["role"] == "admin"

        client.post(
            "/v1/projects",
            json={
                "title": "Admin forecast",
                "project_type": "forecast",
                "payload": {"budget": 42_000_000},
            },
        )
        overview = client.get("/v1/admin/overview")

    assert overview.status_code == 200
    assert overview.json()["users"] == 1
    assert overview.json()["active_sessions"] == 1
    assert overview.json()["forecast_projects"] == 1
    assert overview.json()["recent_projects"][0]["owner_name"] == "SlateSignal Admin"


def test_admin_email_without_bootstrap_token_remains_a_regular_user() -> None:
    with TestClient(app) as client:
        register = client.post(
            "/v1/auth/register",
            json={
                "email": "admin@slatesignal.dev",
                "display_name": "Unverified Admin",
                "password": "admin-password-is-long",
            },
        )

    assert register.status_code == 201
    assert register.json()["role"] == "user"


def test_regular_user_cannot_access_admin_overview() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "email": "viewer@example.com",
                "display_name": "Viewer",
                "password": "a-secure-viewer-password",
            },
        )
        response = client.get("/v1/admin/overview")

    assert response.status_code == 403


def test_upcoming_catalog_contains_only_source_backed_real_films() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/catalog/upcoming")

    assert response.status_code == 200
    titles = {movie["title"] for movie in response.json()}
    assert {
        "Spider-Man: Brand New Day",
        "Avengers: Doomsday",
        "Dune: Part Three",
    }.issubset(titles)
    assert {movie["data_source"] for movie in response.json()} == {"official_seed"}
    assert all(movie["forecast_ready"] for movie in response.json())


def test_real_movie_report_exposes_sources_and_sealed_forecast() -> None:
    with TestClient(app) as client:
        search = client.get("/v1/movies", params={"q": "Dune: Part Three"})
        assert search.status_code == 200
        movie = search.json()["items"][0]

        detail = client.get(f"/v1/movies/{movie['slug']}")
        forecast = client.get(f"/v1/movies/{movie['slug']}/forecast")

    assert detail.status_code == 200
    assert detail.json()["primary_source"] == "legendary"
    assert detail.json()["evidence"]
    assert forecast.status_code == 200
    assert forecast.json()["forecast_type"] == "official"
    assert len(forecast.json()["ledger_hash"]) == 64
    assert len(forecast.json()["grouped_factors"]) == 20
    assert forecast.headers["etag"].strip('"') == forecast.json()["ledger_hash"]
    assert forecast.headers["x-ledger-hash"] == forecast.json()["ledger_hash"]


def test_closed_holdout_is_labeled_as_retrospective_evaluation() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/backtests", params={"limit": 100})

    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]["count"] == 24
    assert payload["metrics"]["interval_coverage"] == 0.75
    assert {item["forecast"]["forecast_type"] for item in payload["items"]} == {"evaluation"}
    assert "retrospective" in payload["methodology_note"].casefold()


def test_released_2021_movie_has_sealed_predicted_vs_actual_evaluation() -> None:
    with TestClient(app) as client:
        with SessionLocal() as db:
            assert bootstrap_historical_evaluations(db) == 480

        search = client.get(
            "/v1/movies",
            params={"q": "Spider-Man: No Way Home"},
        )
        movie = search.json()["items"][0]
        forecast = client.get(f"/v1/movies/{movie['slug']}/forecast")

    assert forecast.status_code == 200
    payload = forecast.json()
    assert payload["forecast_type"] == "evaluation"
    assert payload["model_version"] == "bert-xgb-temporal-2021"
    assert payload["actuals"]["worldwide_total"]["amount"] == 1_952_732_181
    assert payload["targets"]["worldwide_total"]["p50"] == 139_157_600
    assert len(payload["ledger_hash"]) == 64
    assert any("retrospectively" in item for item in payload["limitations"])
