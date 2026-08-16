"""Habit creation and listing endpoints."""

import uuid
from datetime import UTC, datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.core.auth import current_user_id, require_auth
from backend.core.db import get_engine

bp = Blueprint("create_habits", __name__)


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


@bp.post("/api/habits")
@require_auth
def create_habit():
    data = request.get_json(silent=True)
    raw_name = data.get("name") if isinstance(data, dict) else None
    habit_name = raw_name.strip() if isinstance(raw_name, str) else ""
    if not habit_name or len(habit_name) > 255:
        return jsonify({
            "error": "INVALID_HABIT_NAME",
            "message": "Habit name must be between 1 and 255 characters",
        }), 400

    habit_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).replace(tzinfo=None)
    user_id = current_user_id()
    try:
        with get_engine().begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO habits (id, user_id, name, created_at)
                    VALUES (:id, :user_id, :name, :created_at)
                """),
                {
                    "id": habit_id,
                    "user_id": user_id,
                    "name": habit_name,
                    "created_at": created_at,
                },
            )
    except SQLAlchemyError:
        return jsonify({
            "error": "DATABASE_ERROR",
            "message": "Failed to create habit",
        }), 500

    return jsonify({
        "id": habit_id,
        "name": habit_name,
        "user_id": user_id,
        "created_at": _iso_datetime(created_at),
    }), 201


@bp.get("/api/habits")
@require_auth
def list_habits():
    try:
        with get_engine().connect() as connection:
            rows = connection.execute(
                text("""
                    SELECT id, user_id, name, created_at
                    FROM habits
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                """),
                {"user_id": current_user_id()},
            ).mappings().all()
    except SQLAlchemyError:
        return jsonify({
            "error": "DATABASE_ERROR",
            "message": "Failed to retrieve habits",
        }), 500

    return jsonify({
        "habits": [
            {
                "id": str(row["id"]),
                "user_id": str(row["user_id"]),
                "name": row["name"],
                "created_at": _iso_datetime(row["created_at"]),
            }
            for row in rows
        ]
    }), 200
