"""Deterministic contract checks for Account Creation."""

from sqlalchemy.exc import OperationalError
from werkzeug.security import generate_password_hash

from backend import create_app
from backend.core.auth import verify_password
from backend.features.account_creation import feature as account_creation_feature


def test_feature_routes_are_registered():
    app = create_app(testing=True)
    actual = {
        (rule.rule, method)
        for rule in app.url_map.iter_rules()
        for method in (rule.methods or set())
    }
    expected = (('/api/auth/signup', 'POST'), ('/api/auth/login', 'POST'), ('/api/auth/verify', 'GET'))
    assert all(route in actual for route in expected)


def test_protected_routes_reject_missing_authentication():
    client = create_app(testing=True).test_client()
    response = client.get('/api/auth/verify')
    assert response.status_code == 401


def test_verify_password_accepts_legacy_werkzeug_hash():
    password = "correct horse battery staple"
    legacy_hash = generate_password_hash(password, method="scrypt")

    assert legacy_hash.startswith("scrypt:")
    assert verify_password(password, legacy_hash) is True
    assert verify_password("incorrect password", legacy_hash) is False


def test_login_reports_database_unavailable(monkeypatch):
    class UnavailableEngine:
        def connect(self):
            raise OperationalError(
                "connect",
                {},
                OSError(2003, "database connection refused"),
            )

    monkeypatch.setattr(
        account_creation_feature,
        "get_engine",
        lambda: UnavailableEngine(),
    )

    response = create_app(testing=True).test_client().post(
        "/api/auth/login",
        json={"email": "person@example.com", "password": "password123"},
    )

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["error"] == "DATABASE_UNAVAILABLE"
    assert "database" in payload["message"].lower()
