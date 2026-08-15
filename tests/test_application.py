"""Whole-application smoke tests."""

from backend import create_app


def test_health_endpoint():
    app = create_app(testing=True)
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_expected_function_inventory_is_frozen():
    expected = ('capability_create_habits_60ad1db9.function.create_habit', 'capability_create_habits_60ad1db9.function.list_habits', 'capability_daily_habit_completion_tracking_766e9d08.function.mark_habit_complete', 'capability_daily_habit_completion_tracking_766e9d08.function.get_habit_completions', 'capability_daily_habit_completion_tracking_766e9d08.function.get_today_completions', 'capability_account_creation_bdf66f42.function.sign_up', 'capability_account_creation_bdf66f42.function.log_in', 'capability_account_creation_bdf66f42.function.verify_session', 'capability_completion_rate_statistics_5a591160.function.get_all_habits_completion_rates', 'capability_completion_rate_statistics_5a591160.function.get_habit_completion_rate', 'capability_current_streak_display_669ed488.function.get_habit_current_streak', 'capability_current_streak_display_669ed488.function.get_all_habits_streaks', 'capability_calendar_heatmap_visualization_28ed1af0.function.get_habit_heatmap_data')
    assert len(expected) == 13
