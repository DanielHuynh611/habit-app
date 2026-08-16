"""Server-owned entry point for the assembled Zorentia application."""

from pathlib import Path

from flask import abort, redirect, send_file
from backend import create_app as create_backend_app

PROJECT_ROOT = Path(__file__).resolve().parent
SCREEN_ROUTES = {
    "/login": "frontend/features/account_creation/log_in.html",
    "/signup": "frontend/features/account_creation/sign_up.html",
    "/habits": "frontend/features/create_habits/habits_list.html",
    "/habits/new": "frontend/features/create_habits/create_habit.html",
    "/habits/today": (
        "frontend/features/daily_habit_completion_tracking/"
        "daily_habit_tracker.html"
    ),
    "/dashboard": (
        "frontend/features/completion_rate_statistics/"
        "habits_dashboard.html"
    ),
    "/streaks": (
        "frontend/features/current_streak_display/"
        "habit_list_with_streaks.html"
    ),
    "/habits/<habit_id>": (
        "frontend/features/completion_rate_statistics/"
        "habit_detail_view.html"
    ),
    "/habits/<habit_id>/streak": (
        "frontend/features/current_streak_display/"
        "habit_detail_with_streak.html"
    ),
    "/habits/<habit_id>/heatmap": (
        "frontend/features/calendar_heatmap_visualization/"
        "habit_heatmap_view.html"
    ),
}


def _project_file(relative_path):
    target = (PROJECT_ROOT / relative_path).resolve()
    if target != PROJECT_ROOT and PROJECT_ROOT not in target.parents:
        raise RuntimeError("frontend_route_path_invalid")
    return target


def create_app(testing=False):
    app = create_backend_app(testing=testing)

    @app.get("/")
    def frontend_index():
        return redirect("/login")

    @app.get("/static/css/app.css")
    def frontend_css():
        return send_file(
            _project_file("frontend/static/css/app.css"),
            mimetype="text/css",
        )

    @app.get("/static/js/app.js")
    def frontend_javascript():
        return send_file(
            _project_file("frontend/static/js/app.js"),
            mimetype="text/javascript",
        )

    @app.get("/__frontend_assets/<path:relative_path>")
    def frontend_asset(relative_path):
        normalized = str(relative_path or "").replace("\\", "/")
        if not normalized.startswith("frontend/features/") or not normalized.endswith(".js"):
            abort(404)
        return send_file(
            _project_file(normalized),
            mimetype="text/javascript",
        )

    for index, (route, relative_path) in enumerate(SCREEN_ROUTES.items()):
        target = _project_file(relative_path)

        def serve_screen(_target=target, **_route_parameters):
            return send_file(_target, mimetype="text/html")

        app.add_url_rule(
            route,
            endpoint="frontend_screen_" + str(index),
            view_func=serve_screen,
            methods=["GET"],
        )
    return app
