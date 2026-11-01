# Brighton Properties — Browser-Based Foundation

A deployable **starter application**, not yet a production-ready construction ERP. It runs in Chrome and Samsung Internet via an HTTPS URL after hosting.

## Included
- Individual username/password login with salted password hashes
- CSRF protection, secure cookie settings, login rate limit (single-process memory), basic security headers
- Admin-managed users and baseline role assignments
- Project registration, core validation, draft/pending/approved/returned/active status transitions
- Shared SQL database (PostgreSQL recommended; SQLite development fallback)
- Append-only application audit event records
- Brighton branding, tablet-responsive layout, light/dark toggle

## Local development (developer / server setup, not on Galaxy Tab)
1. Install Python 3.11+ and PostgreSQL (or use SQLite for local tests).
2. `python -m venv .venv` and activate it.
3. `pip install -r requirements.txt`
4. Set `SECRET_KEY` to a cryptographically random 64+ character string.
5. Set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL, e.g. `postgresql+psycopg://...`.
6. For **HTTP local testing only**, set `SESSION_COOKIE_SECURE=0`; for production leave it `1`.
7. `flask --app app init-db`
8. `flask --app app create-admin`
9. Local test: `flask --app app run --debug` (never expose debug mode publicly).
10. Production behind HTTPS reverse proxy: `gunicorn -w 3 -b 127.0.0.1:8000 app:app` and configure TLS, trusted proxy headers, persistent PostgreSQL, backups and monitoring.

## Important limitations / work before real company deployment
- No website has been hosted or publicly deployed; a domain, server and TLS are still required.
- First registration form currently requires core fields even for Save Draft. Partial drafts, seven-step wizard, project structure, document uploads and detailed organizational reporting lines are **not yet implemented**.
- Approval is role-based but not a complete segregation-of-duties workflow; add self-approval restrictions and configurable approval policy before production.
- Add persistent/shared rate-limiting storage (Redis), MFA, password reset, user disable/change-password, session revocation, detailed account lockout policy, audit immutability/retention, migrations, automated tests and operational security review.
- PostgreSQL deployment requires dedicated DB credentials and least-privilege access. Database writes and backups require recovery testing.
- Role assignments in this starter are global. Project-specific assignment and delegated approval administration are future work; the data model includes a project_id for this purpose.
- Financial ledger, photo/video evidence, and full document management are future modules.
- Company data should **not** be entered until deployment security and backup procedures are verified.


## Render
See `DEPLOY_RENDER.md` and `render.yaml`. These are **preparations only**; no paid services have been created.
