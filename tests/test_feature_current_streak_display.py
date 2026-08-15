"""Deterministic contract checks for Current Streak Display."""

from backend import create_app


def test_feature_routes_are_registered():
    app = create_app(testing=True)
    actual = {
        (rule.rule, method)
        for rule in app.url_map.iter_rules()
        for method in (rule.methods or set())
    }
    expected = (('/api/habits/<habit_id>/streak', 'GET'), ('/api/habits/streaks', 'GET'))
    assert all(route in actual for route in expected)


def test_protected_routes_reject_missing_authentication():
    client = create_app(testing=True).test_client()
    response = client.get('/api/habits/:habit_id/streak')
    assert response.status_code == 401
    response = client.get('/api/habits/streaks')
    assert response.status_code == 401
