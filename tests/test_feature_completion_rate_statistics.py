"""Deterministic contract checks for Completion Rate Statistics."""

from backend import create_app


def test_feature_routes_are_registered():
    app = create_app(testing=True)
    actual = {
        (rule.rule, method)
        for rule in app.url_map.iter_rules()
        for method in (rule.methods or set())
    }
    expected = (('/api/habits/completion-rates', 'GET'), ('/api/habits/<habit_id>/completion-rate', 'GET'))
    assert all(route in actual for route in expected)


def test_protected_routes_reject_missing_authentication():
    client = create_app(testing=True).test_client()
    response = client.get('/api/habits/completion-rates')
    assert response.status_code == 401
    response = client.get('/api/habits/test-id/completion-rate')
    assert response.status_code == 401
