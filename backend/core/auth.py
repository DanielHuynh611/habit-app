"""HS256 bearer tokens and PBKDF2 password utilities."""

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from functools import wraps

from flask import g, jsonify, request
from werkzeug.security import check_password_hash

from backend.core.config import get_settings


def _decode_segment(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _encode_segment(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    rounds = 310000
    digest = hashlib.pbkdf2_hmac(
        "sha256", str(password).encode("utf-8"), salt, rounds
    )
    return (
        f"pbkdf2_sha256${rounds}$"
        f"{_encode_segment(salt)}${_encode_segment(digest)}"
    )


def verify_password(password: str, encoded: str) -> bool:
    encoded = str(encoded)
    if not encoded.startswith("pbkdf2_sha256$"):
        # Accounts created by the original Flask implementation used
        # Werkzeug's versioned scrypt/pbkdf2 hashes. Keep those accounts
        # usable while new passwords use the format produced above.
        try:
            return check_password_hash(encoded, str(password))
        except (TypeError, ValueError):
            return False

    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            str(password).encode("utf-8"),
            _decode_segment(salt),
            int(rounds),
        )
        return hmac.compare_digest(actual, _decode_segment(expected))
    except (TypeError, ValueError, binascii.Error):
        return False


def issue_token(subject: str, *, expires_in_seconds: int = 86400) -> str:
    settings = get_settings()
    now = int(time.time())
    header = _encode_segment(
        json.dumps(
            {"alg": "HS256", "typ": "JWT"},
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    payload = _encode_segment(
        json.dumps(
            {
                "sub": str(subject),
                "iss": settings.jwt_issuer,
                "iat": now,
                "exp": now + int(expires_in_seconds),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    signing_input = f"{header}.{payload}"
    signature = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_encode_segment(signature)}"


def _verify_token(token: str) -> dict:
    try:
        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}".encode("ascii")
        header = json.loads(_decode_segment(header_part))
        payload = json.loads(_decode_segment(payload_part))
        signature = _decode_segment(signature_part)
    except Exception as exc:
        raise ValueError("invalid_token") from exc
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise ValueError("invalid_token")
    if header.get("alg") != "HS256":
        raise ValueError("invalid_token_algorithm")
    settings = get_settings()
    expected = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("invalid_token_signature")
    if payload.get("iss") != settings.jwt_issuer:
        raise ValueError("invalid_token_issuer")
    if not payload.get("sub"):
        raise ValueError("token_subject_required")
    if int(payload.get("exp") or 0) <= int(time.time()):
        raise ValueError("token_expired")
    return payload


def current_user_id() -> str:
    """Return the authenticated user identifier for the current request."""
    identity = getattr(g, "identity", None) or {}
    subject = identity.get("sub")
    if not subject:
        raise RuntimeError("authenticated_user_required")
    return str(subject)


def require_auth(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        authorization = request.headers.get("Authorization", "")
        scheme, separator, token = authorization.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            return jsonify({
                "error": "UNAUTHORIZED",
                "message": "Authentication required",
            }), 401
        try:
            g.identity = _verify_token(token.strip())
        except ValueError:
            return jsonify({
                "error": "INVALID_TOKEN",
                "message": "Authentication token is invalid or expired",
            }), 401
        return handler(*args, **kwargs)

    return wrapped


def load_optional_auth(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        authorization = request.headers.get("Authorization", "")
        if not authorization:
            g.identity = None
            return handler(*args, **kwargs)
        scheme, separator, token = authorization.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            return jsonify({"error": "invalid_authorization"}), 401
        try:
            g.identity = _verify_token(token.strip())
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 401
        return handler(*args, **kwargs)

    return wrapped
