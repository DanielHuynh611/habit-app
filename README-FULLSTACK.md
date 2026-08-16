# habit full-stack application

This package combines the Flask API with responsive browser pages and a shared
interaction controller. It does not require a frontend CDN at runtime.

## Run locally

1. Create and activate a Python virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and replace its example values.
4. Apply `database/schema.sql` to MySQL.
5. Run `pytest -q`.
6. Start the complete application:
   `flask --app 'fullstack:create_app()' run --debug`
7. Open `http://127.0.0.1:5000`.

## Route setup note

The main routes are `/habits`, `/habits/today`, `/dashboard`, and `/streaks`.
Habit-specific statistics, streak, and heatmap screens use
`/habits/<habit_id>`, `/habits/<habit_id>/streak`, and
`/habits/<habit_id>/heatmap`.

