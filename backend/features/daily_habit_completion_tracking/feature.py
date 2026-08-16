"""Daily habit completion tracking endpoints."""

import uuid
from datetime import date, datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.core.auth import current_user_id, require_auth
from backend.core.db import get_engine

bp = Blueprint("daily_habit_completion_tracking", __name__)


def _parse_date(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _iso_date(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _iso_datetime(value) -> str:
    if isinstance(value, datetime):
        return value.isoformat() + ("Z" if value.tzinfo is None else "")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.isoformat() + ("Z" if parsed.tzinfo is None else "")
        except ValueError:
            return value
    return str(value)


def _completion_response(row, *, include_habit_id=True):
    result = {
        "id": str(row["id"]),
        "completion_date": _iso_date(row["completion_date"]),
        "is_completed": bool(row["is_completed"]),
        "created_at": _iso_datetime(row["created_at"]),
        "updated_at": _iso_datetime(row["updated_at"]),
    }
    if include_habit_id:
        result["habit_id"] = str(row["habit_id"])
    return result


def _habit_owner(connection, habit_id):
    return connection.execute(
        text("SELECT user_id FROM habits WHERE id = :habit_id"),
        {"habit_id": habit_id},
    ).scalar_one_or_none()


def _access_error(owner_id, user_id):
    if owner_id is None:
        return jsonify({
            "error": "HABIT_NOT_FOUND",
            "message": "Habit with the specified ID does not exist",
        }), 404
    if str(owner_id) != str(user_id):
        return jsonify({
            "error": "FORBIDDEN",
            "message": "User does not have access to this habit",
        }), 403
    return None


@bp.put("/api/habits/<habit_id>/completions")
@require_auth
def mark_habit_complete(habit_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "error": "INVALID_REQUEST",
            "message": "Request body is required",
        }), 400

    completion_date = _parse_date(data.get("completion_date"))
    is_completed = data.get("is_completed")
    if completion_date is None:
        return jsonify({
            "error": "INVALID_DATE",
            "message": "completion_date must be a valid date in YYYY-MM-DD format",
        }), 400
    if not isinstance(is_completed, bool):
        return jsonify({
            "error": "INVALID_REQUEST",
            "message": "is_completed must be a boolean",
        }), 400

    user_id = current_user_id()
    try:
        with get_engine().begin() as connection:
            access_error = _access_error(
                _habit_owner(connection, habit_id), user_id
            )
            if access_error:
                return access_error

            completion_id = connection.execute(
                text("""
                    SELECT id
                    FROM habit_completions
                    WHERE habit_id = :habit_id
                      AND completion_date = :completion_date
                """),
                {
                    "habit_id": habit_id,
                    "completion_date": completion_date,
                },
            ).scalar_one_or_none()
            if completion_id:
                connection.execute(
                    text("""
                        UPDATE habit_completions
                        SET is_completed = :is_completed,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """),
                    {"id": completion_id, "is_completed": is_completed},
                )
            else:
                completion_id = str(uuid.uuid4())
                connection.execute(
                    text("""
                        INSERT INTO habit_completions
                            (id, habit_id, completion_date, is_completed,
                             created_at, updated_at)
                        VALUES
                            (:id, :habit_id, :completion_date, :is_completed,
                             CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """),
                    {
                        "id": completion_id,
                        "habit_id": habit_id,
                        "completion_date": completion_date,
                        "is_completed": is_completed,
                    },
                )
            row = connection.execute(
                text("""
                    SELECT id, habit_id, completion_date, is_completed,
                           created_at, updated_at
                    FROM habit_completions
                    WHERE id = :id
                """),
                {"id": completion_id},
            ).mappings().one()
    except SQLAlchemyError:
        return jsonify({
            "error": "DATABASE_ERROR",
            "message": "Failed to save habit completion",
        }), 500

    return jsonify(_completion_response(row)), 200


@bp.get("/api/habits/<habit_id>/completions")
@require_auth
def get_habit_completions(habit_id):
    start_date = _parse_date(request.args.get("start_date"))
    end_date = _parse_date(request.args.get("end_date"))
    if start_date is None or end_date is None or start_date > end_date:
        return jsonify({
            "error": "INVALID_DATE_RANGE",
            "message": (
                "start_date and end_date must be valid dates, and "
                "start_date must not be after end_date"
            ),
        }), 400

    user_id = current_user_id()
    try:
        with get_engine().connect() as connection:
            access_error = _access_error(
                _habit_owner(connection, habit_id), user_id
            )
            if access_error:
                return access_error
            rows = connection.execute(
                text("""
                    SELECT id, habit_id, completion_date, is_completed,
                           created_at, updated_at
                    FROM habit_completions
                    WHERE habit_id = :habit_id
                      AND completion_date BETWEEN :start_date AND :end_date
                    ORDER BY completion_date ASC
                """),
                {
                    "habit_id": habit_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ).mappings().all()
    except SQLAlchemyError:
        return jsonify({
            "error": "DATABASE_ERROR",
            "message": "Failed to retrieve habit completions",
        }), 500

    return jsonify({
        "habit_id": habit_id,
        "completions": [
            _completion_response(row, include_habit_id=False) for row in rows
        ],
    }), 200


@bp.get("/api/completions/today")
@require_auth
def get_today_completions():
    today = date.today()
    try:
        with get_engine().connect() as connection:
            rows = connection.execute(
                text("""
                    SELECT hc.id, hc.habit_id, hc.completion_date,
                           hc.is_completed, hc.created_at, hc.updated_at
                    FROM habit_completions AS hc
                    INNER JOIN habits AS h ON h.id = hc.habit_id
                    WHERE h.user_id = :user_id
                      AND hc.completion_date = :today
                    ORDER BY hc.created_at ASC
                """),
                {"user_id": current_user_id(), "today": today},
            ).mappings().all()
    except SQLAlchemyError:
        return jsonify({
            "error": "DATABASE_ERROR",
            "message": "Failed to retrieve today's completions",
        }), 500

    return jsonify({
        "date": today.isoformat(),
        "completions": [_completion_response(row) for row in rows],
    }), 200
