"""Current habit-streak endpoints."""

from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.core.auth import current_user_id, require_auth
from backend.core.db import get_engine

bp = Blueprint("current_streak_display", __name__)


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def calculate_streak_for_habit(habit_id, user_id, connection):
    del user_id  # Ownership is checked by each endpoint before this helper is called.
    today = date.today()
    completion_dates = [
        _as_date(value)
        for value in connection.execute(
            text("""
                SELECT DISTINCT completion_date
                FROM habit_completions
                WHERE habit_id = :habit_id
                  AND is_completed = :is_completed
                  AND completion_date <= :today
                ORDER BY completion_date DESC
            """),
            {
                "habit_id": habit_id,
                "is_completed": True,
                "today": today,
            },
        ).scalars().all()
    ]
    if not completion_dates:
        return 0, None

    expected_date = today
    current_streak = 0
    for completion_date in completion_dates:
        if completion_date == expected_date:
            current_streak += 1
            expected_date -= timedelta(days=1)
        elif completion_date < expected_date:
            break
    return current_streak, completion_dates[0]


def _streak_payload(habit_id, current_streak, last_completion_date):
    return {
        "habit_id": str(habit_id),
        "current_streak": current_streak,
        "last_completion_date": (
            last_completion_date.isoformat() if last_completion_date else None
        ),
    }


@bp.get("/api/habits/<habit_id>/streak")
@require_auth
def get_habit_current_streak(habit_id):
    user_id = current_user_id()
    try:
        with get_engine().connect() as connection:
            owner_id = connection.execute(
                text("SELECT user_id FROM habits WHERE id = :habit_id"),
                {"habit_id": habit_id},
            ).scalar_one_or_none()
            if owner_id is None:
                return jsonify({
                    "code": "HABIT_NOT_FOUND",
                    "message": "Habit does not exist",
                }), 404
            if str(owner_id) != user_id:
                return jsonify({
                    "code": "FORBIDDEN",
                    "message": "User does not have access to this habit",
                }), 403
            current_streak, last_completion_date = calculate_streak_for_habit(
                habit_id, user_id, connection
            )
    except (SQLAlchemyError, TypeError, ValueError):
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to calculate current streak",
        }), 500

    return jsonify(_streak_payload(
        habit_id, current_streak, last_completion_date
    )), 200


@bp.get("/api/habits/streaks")
@require_auth
def get_all_habits_streaks():
    user_id = current_user_id()
    try:
        with get_engine().connect() as connection:
            habit_ids = connection.execute(
                text("""
                    SELECT id
                    FROM habits
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                """),
                {"user_id": user_id},
            ).scalars().all()
            streaks = []
            for habit_id in habit_ids:
                current_streak, last_completion_date = (
                    calculate_streak_for_habit(
                        habit_id, user_id, connection
                    )
                )
                streaks.append(_streak_payload(
                    habit_id, current_streak, last_completion_date
                ))
    except (SQLAlchemyError, TypeError, ValueError):
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to calculate current streaks",
        }), 500

    return jsonify({"streaks": streaks}), 200
