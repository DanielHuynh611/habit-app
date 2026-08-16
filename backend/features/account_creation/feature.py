"""Account creation, login, and session verification endpoints."""

import re
import uuid
from datetime import UTC, datetime, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.core.auth import (
    current_user_id,
    hash_password,
    issue_token,
    require_auth,
    verify_password,
)
from backend.core.db import get_engine

account_creation_bp = Blueprint("account_creation", __name__)

JWT_EXPIRATION_DAYS = 30
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)


def validate_email(email) -> bool:
    return (
        isinstance(email, str)
        and 3 <= len(email) <= 255
        and EMAIL_PATTERN.fullmatch(email) is not None
    )


def validate_password(password) -> bool:
    return isinstance(password, str) and 8 <= len(password) <= 128


def _token_for(user_id: str) -> str:
    return issue_token(
        user_id,
        expires_in_seconds=int(timedelta(days=JWT_EXPIRATION_DAYS).total_seconds()),
    )


def _database_is_unavailable(error: SQLAlchemyError) -> bool:
    """Recognize connection failures without exposing database details."""
    current = error
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if getattr(current, "errno", None) in {2002, 2003, 2005, 2006, 2013}:
            return True
        current = getattr(current, "orig", None) or getattr(
            current, "__cause__", None
        )
    return bool(getattr(error, "connection_invalidated", False))


def _database_error(error: SQLAlchemyError, fallback_message: str):
    if _database_is_unavailable(error):
        return jsonify({
            "error": "DATABASE_UNAVAILABLE",
            "message": "Database is unavailable. Start MySQL and try again.",
        }), 503
    return jsonify({
        "error": "INTERNAL_ERROR",
        "message": fallback_message,
    }), 500


@account_creation_bp.post("/api/auth/signup")
def sign_up():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "error": "INVALID_EMAIL",
            "message": "Email address is invalid",
        }), 400

    raw_email = data.get("email")
    email = raw_email.strip().lower() if isinstance(raw_email, str) else ""
    password = data.get("password")
    if not validate_email(email):
        return jsonify({
            "error": "INVALID_EMAIL",
            "message": "Email address is invalid",
        }), 400
    if not validate_password(password):
        return jsonify({
            "error": "INVALID_PASSWORD",
            "message": "Password must be between 8 and 128 characters",
        }), 400

    user_id = str(uuid.uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)
    try:
        with get_engine().begin() as connection:
            existing_user = connection.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email},
            ).first()
            if existing_user:
                return jsonify({
                    "error": "EMAIL_EXISTS",
                    "message": "An account with this email already exists",
                }), 409
            connection.execute(
                text("""
                    INSERT INTO users
                        (id, email, password_hash, created_at, updated_at)
                    VALUES
                        (:id, :email, :password_hash, :created_at, :updated_at)
                """),
                {
                    "id": user_id,
                    "email": email,
                    "password_hash": hash_password(password),
                    "created_at": now,
                    "updated_at": now,
                },
            )
    except IntegrityError:
        return jsonify({
            "error": "EMAIL_EXISTS",
            "message": "An account with this email already exists",
        }), 409
    except SQLAlchemyError as error:
        return _database_error(error, "Failed to create account")

    return jsonify({
        "user_id": user_id,
        "email": email,
        "token": _token_for(user_id),
    }), 201


@account_creation_bp.post("/api/auth/login")
def log_in():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "error": "MISSING_FIELDS",
            "message": "Email and password are required",
        }), 400

    raw_email = data.get("email")
    email = raw_email.strip().lower() if isinstance(raw_email, str) else ""
    password = data.get("password")
    if not email or not isinstance(password, str) or not password:
        return jsonify({
            "error": "MISSING_FIELDS",
            "message": "Email and password are required",
        }), 400

    try:
        with get_engine().connect() as connection:
            user = connection.execute(
                text("""
                    SELECT id, email, password_hash
                    FROM users
                    WHERE email = :email
                """),
                {"email": email},
            ).mappings().first()
    except SQLAlchemyError as error:
        return _database_error(error, "Failed to authenticate")

    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({
            "error": "INVALID_CREDENTIALS",
            "message": "Email or password is incorrect",
        }), 401

    return jsonify({
        "user_id": str(user["id"]),
        "email": user["email"],
        "token": _token_for(str(user["id"])),
    }), 200


@account_creation_bp.get("/api/auth/verify")
@require_auth
def verify_session():
    try:
        with get_engine().connect() as connection:
            user = connection.execute(
                text("SELECT id, email FROM users WHERE id = :id"),
                {"id": current_user_id()},
            ).mappings().first()
    except SQLAlchemyError as error:
        return _database_error(error, "Failed to verify session")

    if not user:
        return jsonify({
            "error": "USER_NOT_FOUND",
            "message": "User account no longer exists",
        }), 404
    return jsonify({"user_id": str(user["id"]), "email": user["email"]}), 200
