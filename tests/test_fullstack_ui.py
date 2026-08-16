"""Full-stack route, asset, and API journey regression tests."""

import re
import sqlite3
from datetime import date, datetime

from sqlalchemy import text

from backend.core.db import get_engine
from fullstack import create_app


SCREEN_PATHS = (
    "/login",
    "/signup",
    "/habits",
    "/habits/new",
    "/habits/today",
    "/dashboard",
    "/streaks",
    "/habits/example-id",
    "/habits/example-id/streak",
    "/habits/example-id/heatmap",
)


def test_root_and_all_screen_routes_are_available():
    client = create_app(testing=True).test_client()
    root = client.get("/")
    assert root.status_code == 302
    assert root.headers["Location"].endswith("/login")

    for path in SCREEN_PATHS:
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.content_type.startswith("text/html"), path
        assert b'/static/js/app.js' in response.data, path


def test_shared_frontend_assets_are_served():
    client = create_app(testing=True).test_client()
    javascript = client.get("/static/js/app.js")
    stylesheet = client.get("/static/css/app.css")

    assert javascript.status_code == 200
    assert javascript.content_type.startswith("text/javascript")
    assert stylesheet.status_code == 200
    assert stylesheet.content_type.startswith("text/css")
    assert b"zorentia_access_token" in javascript.data
    assert b"/api/auth/login" in javascript.data
    assert b"/api/habits" in javascript.data
    assert b"/completions" in javascript.data
    assert b"/heatmap" in javascript.data


def test_dynamic_screen_routes_use_real_path_parameters():
    app = create_app(testing=True)
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/habits/<habit_id>" in rules
    assert "/habits/<habit_id>/streak" in rules
    assert "/habits/<habit_id>/heatmap" in rules
    assert not any(re.search(r":habit_id", rule) for rule in rules)


def test_authenticated_api_journey_works_with_ui_contract(monkeypatch):
    sqlite3.register_adapter(date, lambda value: value.isoformat())
    sqlite3.register_adapter(datetime, lambda value: value.isoformat(" "))
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("JWT_SECRET", "fullstack-test-secret-with-sufficient-length")
    monkeypatch.setenv("JWT_ISSUER", "habit-fullstack-test")
    get_engine.cache_clear()
    engine = get_engine()

    try:
        with engine.begin() as connection:
            connection.execute(text("""
                CREATE TABLE users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """))
            connection.execute(text("""
                CREATE TABLE habits (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """))
            connection.execute(text("""
                CREATE TABLE habit_completions (
                    id TEXT PRIMARY KEY,
                    habit_id TEXT NOT NULL,
                    completion_date DATE NOT NULL,
                    is_completed BOOLEAN NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (habit_id, completion_date)
                )
            """))

        client = create_app(testing=True).test_client()
        signup = client.post("/api/auth/signup", json={
            "email": "ui@example.com",
            "password": "correct-horse-battery-staple",
        })
        assert signup.status_code == 201
        token = signup.get_json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        assert client.get("/api/auth/verify", headers=headers).status_code == 200
        created = client.post(
            "/api/habits",
            headers=headers,
            json={"name": "Read every day"},
        )
        assert created.status_code == 201
        habit = created.get_json()

        listed = client.get("/api/habits", headers=headers).get_json()
        assert listed["habits"][0]["name"] == "Read every day"

        completion = client.put(
            f"/api/habits/{habit['id']}/completions",
            headers=headers,
            json={
                "completion_date": date.today().isoformat(),
                "is_completed": True,
            },
        )
        assert completion.status_code == 200
        assert completion.get_json()["is_completed"] is True

        today = client.get("/api/completions/today", headers=headers).get_json()
        assert today["completions"][0]["habit_id"] == habit["id"]

        rate = client.get(
            f"/api/habits/{habit['id']}/completion-rate", headers=headers
        ).get_json()
        streak = client.get(
            f"/api/habits/{habit['id']}/streak", headers=headers
        ).get_json()
        heatmap = client.get(
            f"/api/habits/{habit['id']}/heatmap", headers=headers
        ).get_json()

        assert rate["completion_rate"] == 100.0
        assert streak["current_streak"] == 1
        assert heatmap["habit_name"] == "Read every day"
        assert heatmap["current_streak"] == 1
    finally:
        engine.dispose()
        get_engine.cache_clear()
