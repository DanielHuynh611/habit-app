# habit backend

This backend was assembled from your completed feature implementations by
Zorentia Backend Generator.

Follow the setup instructions below. If you encounter an error while setting up
or running the project, copy the error message into Goat Helper for step-by-step help.

## Setup

1. Create a virtual environment: `python -m venv .venv`
2. Activate it.
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and replace the example values.
5. Apply `database/schema.sql` to a MySQL database.
6. Run tests: `pytest -q`
7. Start the application:
   `flask --app 'backend:create_app()' run --debug`

The generated API health endpoint is `GET /health`.
