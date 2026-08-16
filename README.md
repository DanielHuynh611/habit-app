# Habit application

Habit is a full-stack Flask and MySQL habit tracker with account authentication,
daily completion tracking, statistics, streaks, and calendar heatmaps.

Follow the setup instructions below. If you encounter an error while setting up
or running the project, copy the error message into Goat Helper for step-by-step help.

## Setup

1. Create a virtual environment: `python -m venv .venv`
2. Activate it.
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and replace the example values.
5. Apply `database/schema.sql` to a MySQL database.
6. Run tests: `python -m pytest -q`
7. Start the complete application:
   `flask --app 'fullstack:create_app()' run --debug`
8. Open `http://127.0.0.1:5000`.

The API health endpoint is `GET /health`. To run only the API, use
`flask --app 'backend:create_app()' run --debug`.
