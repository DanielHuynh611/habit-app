"""Habit completion-rate statistics endpoints."""

import uuid
from datetime import date, datetime

from flask import Blueprint, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.core.auth import current_user_id, require_auth
from backend.core.db import get_engine

bp = Blueprint("completion_rate_statistics", __name__)


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()


def calculate_completion_rate_for_habit(connection, habit_id, user_id):
    habit = connection.execute(
        text("""
            SELECT id, created_at
            FROM habits
            WHERE id = :habit_id AND user_id = :user_id
        """),
        {"habit_id": habit_id, "user_id": user_id},
    ).mappings().first()
    if not habit:
        return None

    today = date.today()
    creation_date = _as_date(habit["created_at"])
    total_days = max((today - creation_date).days + 1, 1)
    completed_days = connection.execute(
        text("""
            SELECT COUNT(DISTINCT completion_date)
            FROM habit_completions
            WHERE habit_id = :habit_id
              AND is_completed = :is_completed
              AND completion_date BETWEEN :creation_date AND :today
        """),
        {
            "habit_id": habit_id,
            "is_completed": True,
            "creation_date": creation_date,
            "today": today,
        },
    ).scalar_one()
    completed_days = int(completed_days or 0)
    completion_rate = min((completed_days / total_days) * 100, 100.0)
    return {
        "habit_id": str(habit_id),
        "completion_rate": round(completion_rate, 2),
        "completed_days": completed_days,
        "total_days": total_days,
    }


@bp.get("/api/habits/completion-rates")
@require_auth
def get_all_habits_completion_rates():
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
            completion_rates = [
                calculate_completion_rate_for_habit(
                    connection, habit_id, user_id
                )
                for habit_id in habit_ids
            ]
    except (SQLAlchemyError, TypeError, ValueError):
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to calculate completion rates",
        }), 500

    return jsonify({"completion_rates": completion_rates}), 200


@bp.get("/api/habits/<habit_id>/completion-rate")
@require_auth
def get_habit_completion_rate(habit_id):
    try:
        uuid.UUID(habit_id)
    except (ValueError, AttributeError):
        return jsonify({
            "code": "HABIT_NOT_FOUND",
            "message": "Habit not found or does not belong to user",
        }), 404

    try:
        with get_engine().connect() as connection:
            result = calculate_completion_rate_for_habit(
                connection, habit_id, current_user_id()
            )
    except (SQLAlchemyError, TypeError, ValueError):
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": "Failed to calculate completion rate",
        }), 500

    if result is None:
        return jsonify({
            "code": "HABIT_NOT_FOUND",
            "message": "Habit not found or does not belong to user",
        }), 404
    return jsonify(result), 200
