"""Calendar heatmap data endpoint."""

from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.core.auth import current_user_id, require_auth
from backend.core.db import get_engine

calendar_heatmap_bp = Blueprint("calendar_heatmap_visualization", __name__)


def _parse_date(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("invalid_date")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("invalid_date")
    return parsed


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _current_streak(connection, habit_id, today):
    completion_dates = {
        _as_date(value)
        for value in connection.execute(
            text("""
                SELECT DISTINCT completion_date
                FROM habit_completions
                WHERE habit_id = :habit_id
                  AND is_completed = :is_completed
                  AND completion_date <= :today
            """),
            {
                "habit_id": habit_id,
                "is_completed": True,
                "today": today,
            },
        ).scalars().all()
    }
    streak = 0
    check_date = today
    while check_date in completion_dates:
        streak += 1
        check_date -= timedelta(days=1)
    return streak


@calendar_heatmap_bp.get("/api/habits/<habit_id>/heatmap")
@require_auth
def get_habit_heatmap_data(habit_id):
    today = date.today()
    try:
        end_date = _parse_date(request.args.get("end_date")) or today
        start_date = (
            _parse_date(request.args.get("start_date"))
            or end_date - timedelta(weeks=12)
        )
    except ValueError:
        return jsonify({
            "error": "INVALID_DATE_RANGE",
            "message": "Dates must use ISO 8601 format (YYYY-MM-DD)",
        }), 400
    if start_date > end_date:
        return jsonify({
            "error": "INVALID_DATE_RANGE",
            "message": "Start date must be before or equal to end date",
        }), 400
    if (end_date - start_date).days > 3660:
        return jsonify({
            "error": "INVALID_DATE_RANGE",
            "message": "Date range cannot exceed 3660 days",
        }), 400

    user_id = current_user_id()
    try:
        with get_engine().connect() as connection:
            habit = connection.execute(
                text("""
                    SELECT id, name, user_id
                    FROM habits
                    WHERE id = :habit_id
                """),
                {"habit_id": habit_id},
            ).mappings().first()
            if not habit:
                return jsonify({
                    "error": "HABIT_NOT_FOUND",
                    "message": "The specified habit does not exist",
                }), 404
            if str(habit["user_id"]) != user_id:
                return jsonify({
                    "error": "FORBIDDEN",
                    "message": "User does not have permission to view this habit",
                }), 403

            completed_dates = {
                _as_date(value)
                for value in connection.execute(
                    text("""
                        SELECT DISTINCT completion_date
                        FROM habit_completions
                        WHERE habit_id = :habit_id
                          AND is_completed = :is_completed
                          AND completion_date BETWEEN :start_date AND :end_date
                    """),
                    {
                        "habit_id": habit_id,
                        "is_completed": True,
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                ).scalars().all()
            }
            current_streak = _current_streak(connection, habit_id, today)
    except (SQLAlchemyError, TypeError, ValueError):
        return jsonify({
            "error": "DATABASE_ERROR",
            "message": "An error occurred while retrieving heatmap data",
        }), 500

    days = []
    current_date = start_date
    while current_date <= end_date:
        days.append({
            "date": current_date.isoformat(),
            "completed": current_date in completed_dates,
            "is_future": current_date > today,
        })
        current_date += timedelta(days=1)

    tracked_days = [day for day in days if not day["is_future"]]
    completed_days = sum(1 for day in tracked_days if day["completed"])
    completion_rate = (
        completed_days / len(tracked_days) * 100 if tracked_days else 0.0
    )
    return jsonify({
        "habit_id": habit_id,
        "habit_name": habit["name"],
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "days": days,
        "current_streak": current_streak,
        "completion_rate": round(completion_rate, 2),
    }), 200


__all__ = ["calendar_heatmap_bp", "get_habit_heatmap_data"]
