# Brighton Properties — Render deployment plan (NOT EXECUTED)

## Current status
Source repository files are prepared locally only. No remote GitHub repository, Render web service, or paid PostgreSQL instance has been created.

## Before deploying
1. Create a **private GitHub repository** under a Brighton-controlled account. Upload these files to its root; never upload `.env`, database files, or credentials.
2. Confirm pricing and authorize paid resources. Select a paid PostgreSQL instance and Starter web service in **Frankfurt** (same region).
3. Add the private GitHub repository to Render and connect the web service, using `render.yaml` as a reference or deploy manually.
4. Configure the `DATABASE_URL` environment variable with the **internal** Render PostgreSQL connection string (secret). Do not paste it in chat or commit it to GitHub.
5. Set `APP_ENV=production`, `SESSION_COOKIE_SECURE=1`, and a long random `SECRET_KEY`. Render can generate the secret.
6. Initialize the database once using `flask --app app init-db` through an authorized Render shell/job. Create the first admin securely using `flask --app app create-admin` in an interactive secure shell. Never put admin passwords in repository, build commands, or chat.
7. Verify `/health`, login, access control, project creation, project workflow and persistence from two browsers.
8. Keep the test site restricted to dummy data. Before using real data: persistent rate limits, migrations, robust RBAC, independent approval chain, MFA, password reset, recovery and backup testing, and external security review.

## Render service settings
Runtime: Python
Build: `pip install -r requirements.txt`
Start: `gunicorn --bind 0.0.0.0:$PORT --workers 2 app:app`
Health check: `/health`
Plan: Starter
Region: Frankfurt
Database: PostgreSQL, paid, same region; confirm plan and price in dashboard.

## Important
- The initial app uses in-memory rate limits, which are not shared across Gunicorn workers.
- The Admin role is global. The current approval workflow is only a pilot.
- `render.yaml` is a **proposal**, not an authorization to deploy or incur charges.
