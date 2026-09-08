# 9jaRent.com.ng

A Nigerian property rental marketplace. Renters browse published listings and
contact agents directly; agents (once approved) list properties and manage
inspections; admins moderate agents, properties and reports. No online
payments in this release — rent is agreed and paid outside the platform,
then the listing is marked rented.

9jaRent uses **Django + Bootstrap**, with **SQLite for local development**
and **PostgreSQL for production**, and is designed for deployment on
conventional Python hosting/cPanel — no Node, no separate API layer, no
Redis/Celery/Docker.

## Features

- **Accounts**: renter and agent signup (email or phone login), agent
  approval workflow (pending/approved/rejected/suspended), email-OTP
  verification.
- **Properties**: draft → pending review → published/rejected → rented →
  archived lifecycle, image uploads, search/filter/sort.
- **Inspections**: renters request a viewing, agents accept/decline/complete.
- **Messaging**: direct renter <-> agent conversations per property.
- **Notifications**: in-app + email, triggered automatically on status
  changes (agent approval, property approval, inspection updates, new
  messages, report resolutions).
- **Reports**: renters can report a listing or agent; admins review and
  resolve.
- **Favourites**, **agent/renter portal dashboards**, **admin dashboard**
  with pending-item counts.

## Technology stack

- Backend: Python, Django, Django ORM, Django auth, Django forms/templates
- Database: SQLite (local dev) / PostgreSQL (production, required)
- Cache: Django's database-backed cache (production) / local-memory cache
  (dev) — used for dashboard metrics and OTP-resend rate limiting
- Frontend: HTML, CSS, Bootstrap, vanilla JS where needed
- Email: SMTP via `django.core.mail`
- Deployment: cPanel (Passenger/WSGI), PostgreSQL, SMTP

Deliberately **not** used: Node/React/Vue, Django REST Framework, Redis,
Celery, Docker, GraphQL, WebSockets — this stays a small, conventional
Django app that a single developer can host on cPanel. See "Background work
without Celery" below for how the handful of things that would normally
reach for Celery are done instead.

## Architecture

Modular monolith — one Django project, several apps, no service/API layer
between them:

```
nigerrents/       # project settings, urls, wsgi, rate-limit middleware
accounts/         # users, auth backends (email/phone login), agent approval, email OTP
properties/       # listings, search/filter, lifecycle
inspections/      # inspection requests
messaging/        # renter <-> agent conversations
notifications/    # in-app + email notifications, triggered by signals
favourites/
reports/
dashboard/        # admin views (dark sidebar shell)
templates/base_portal.html  # shared agent/renter portal sidebar shell
templates/, static/, media/
```

**One thing worth understanding before touching `notifications/signals.py`:**
state-transition notifications (e.g. "property approved") are detected with
`pre_save`, not `post_save`. A `post_save` handler that re-queries the DB for
"the old value" always gets the *new* value back, because the row has
already been written by the time `post_save` fires — so a naive
implementation silently never detects any transition. `pre_save` handlers
snapshot the prior state onto the instance before the write; the paired
`post_save` handler compares against that. Don't "simplify" this back to a
single `post_save` handler with a re-fetch.

## Local development

```bash
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
cp env.example .env             # edit as needed; defaults work for local dev
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

SQLite is the default for local development — no extra setup. **Production
requires PostgreSQL** (see "Database & backups" below); the app will refuse
to start with `DEBUG=False` and no `DATABASE_URL` pointing at Postgres,
rather than silently falling back to SQLite.

## Background work without Celery

A few things below would typically reach for Celery + Redis. Since this
project deliberately avoids both (simpler to run and debug on cPanel, one
less service to keep alive), here's the plain-Django equivalent for each:

| Need | How it's done here |
|---|---|
| Scheduled cleanup (expired OTPs, stale sessions) | A Django **management command**, triggered by a **cPanel cron job** on a schedule (cPanel's "Cron Jobs" panel, same place you'd schedule anything else). E.g. `python manage.py clearsessions` daily; add a similar command for expired `EmailOTP` rows if you want them purged rather than just filtered out at query time. |
| Caching expensive queries (dashboard metrics) | Django's cache framework with the **database cache backend** (`django.core.cache.backends.db.DatabaseCache`) — one extra table (`python manage.py createcachetable`), no extra service. See `dashboard/views.py`. |
| Rate limiting (OTP resend, request throttling) | Same cache framework, short-TTL keys. See `nigerrents/middleware.py` (`RateLimitMiddleware`) and `accounts/views.py` (OTP resend cooldown). |
| Sending emails | Synchronous `send_mail(..., fail_silently=True)` at the point of the triggering action (signal or view). Accepted tradeoff: a slow SMTP server adds latency to that request. If email volume ever becomes a real problem, the next step up (still no Celery) is queuing rows into a small `EmailQueue` model and flushing them with a cron-triggered management command — not async at all, just deferred to the next cron tick. |
| Video/image thumbnailing | Done synchronously with Pillow inside `PropertyImage.save()` — images are small enough that this doesn't need to be offloaded. |

## Environment variables

See `.env.example` for the full list with comments. Key ones:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key. Generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | Must be `False` in production |
| `ALLOWED_HOSTS` | Comma-separated production hostnames |
| `CSRF_TRUSTED_ORIGINS` | Origins allowed to submit forms |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | SMTP config for production email |
| `SITE_URL` | Full base URL, used to build absolute links in emails sent from background/signal code with no request object |
| `TRUST_PROXY_HEADERS` | Only `True` if you're behind a proxy that overwrites `X-Forwarded-For` — otherwise leave `False`, or the rate limiter can be bypassed with a spoofed header |
| `DATABASE_URL` | **Required in production.** `postgres://user:password@localhost:5432/dbname`. Leave unset locally to use SQLite. |
| `CONN_MAX_AGE` | Seconds to keep DB connections open between requests in production. Defaults to 600; only takes effect when `DATABASE_URL` is set. |

Never commit `.env`.

## Database & backups

**Local development**: SQLite (`db.sqlite3`) — zero setup, used automatically
when `DATABASE_URL` is unset.

**Production**: PostgreSQL is required. The app raises `ImproperlyConfigured`
at startup if `DEBUG=False` and `DATABASE_URL` is missing or points at
SQLite — this is intentional, not a bug: SQLite's single-writer file lock
causes "database is locked" errors under real concurrent traffic.

On cPanel, use the **"PostgreSQL Databases"** panel (same place/workflow as
creating a MySQL database) to create a database and user, then set:

```
DATABASE_URL=postgres://DBUSER:DBPASSWORD@localhost:5432/DBNAME
```

After deploying with a fresh `DATABASE_URL`:

```bash
python manage.py migrate
python manage.py createcachetable   # one-time: creates the DB-backed cache table
```

Back up the Postgres database with `pg_dump` (cPanel's PostgreSQL panel
usually offers a backup/export option directly; check what your host
provides). If you're still on the SQLite-only local setup:

```bash
# Local SQLite backup (dev only - production uses pg_dump instead)
cp db.sqlite3 backups/db-$(date +%Y%m%d-%H%M%S).sqlite3
```

Also back up `media/` (uploaded images) and `.env` (not the file's secrets
themselves — just make sure you have a record of them somewhere safe).
Never expose the `backups/` directory, `db.sqlite3`, or database credentials
through the web server.

## Static & media files

```bash
python manage.py collectstatic
```

Static files are served via WhiteNoise in production — no separate web
server config needed for CSS/JS. `MEDIA_ROOT`/`MEDIA_URL` serve uploaded
images normally; make sure `media/` is writable by the app but not
directly browsable/executable.

## Testing

```bash
python manage.py test
python manage.py check
python manage.py check --deploy   # run with DEBUG=False and real SECRET_KEY/ALLOWED_HOSTS set
python manage.py makemigrations --check --dry-run
```

## cPanel deployment

1. Create a Python application in cPanel, select the supported Python version.
2. cPanel creates a virtualenv automatically — activate it (path shown in
   the cPanel UI) and `pip install -r requirements.txt`.
3. Create a PostgreSQL database and user via cPanel's **"PostgreSQL
   Databases"** panel, and note the resulting `DATABASE_URL`.
4. Upload the project (excluding `venv/`, `.env`, `db.sqlite3`, and
   `__pycache__/`).
5. Set environment variables in cPanel's "Python App" environment-variables
   section (same keys as `env.example`), or create `.env` on the server.
   At minimum: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`,
   `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`.
6. `python manage.py migrate`
7. `python manage.py createcachetable` (one-time — creates the DB-backed
   cache table used for dashboard metrics and rate limiting; see
   "Background work without Celery")
8. `python manage.py collectstatic`
9. `python manage.py createsuperuser`
10. Point cPanel's Passenger config at `nigerrents/wsgi.py`.
11. Attach the domain/subdomain to the app.
12. Ensure `media/` and `logs/` are writable by the app user.
13. Optional: install `ffmpeg` on the server if you want the stricter
    video-upload codec/resolution check enforced (see "Video uploads on
    shared hosting" below) — not required for the app to run.
14. Optional but recommended: schedule `python manage.py clearsessions` as
    a periodic cron job under cPanel's "Cron Jobs" panel.
15. Test end-to-end: registration, login, property creation + image upload,
    property approval, email notifications, admin dashboard, agent/renter
    portal pages, search, messaging, inspections, mobile layout.

## Video uploads on shared hosting

Property video validation (`properties/validators.py`) uses `ffmpeg-python`,
which shells out to the `ffprobe` binary to check resolution/codec. Most
shared/cPanel hosts don't have `ffmpeg` installed and won't let you install
system packages. If it's missing, the app **degrades gracefully**: file
size and extension are still enforced, the codec/resolution check is simply
skipped (with a warning logged) rather than blocking every video upload.
Install `ffmpeg` on the server if you want that stricter check enforced —
no code changes needed, it starts working automatically once the binary is
on the `PATH`.

## Security notes

- `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS` are all environment-driven — never
  hardcoded.
- Session/CSRF cookies, HSTS, clickjacking (`X-Frame-Options`), and MIME-
  sniffing protections are configured for production and gated on
  `not DEBUG` so local development still works normally.
- The custom rate-limiting middleware (`nigerrents/middleware.py`) only
  trusts `X-Forwarded-For` when `TRUST_PROXY_HEADERS=True` — leave this off
  unless you've actually got a proxy in front that overwrites the header,
  since a client can set it to anything.
- Property search/sort/filter query params are validated: sort uses an
  explicit whitelist, numeric filters (`price`, `bedrooms`, `state`/`lga`
  IDs) are checked before hitting the database.
- File uploads are validated (type/extension/size) before being stored.
- Content-Security-Policy uses a per-request nonce for inline `<script>`
  tags rather than `'unsafe-inline'` — any inline script must carry
  `nonce="{{ csp_nonce }}"` (see `nigerrents/context_processors.py`).
- Notification redirect links are validated with
  `url_has_allowed_host_and_scheme` before following them, to prevent open
  redirects.
- Agent signup's OTP-verified-but-no-password-yet window expires after 15
  minutes (`AgentSignUpSetupView.VERIFIED_WINDOW_MINUTES`), and the session
  key is rotated at signup start — mitigates account takeover via a shared/
  public computer between the verify and password-setup steps.
- Run `python manage.py check --deploy` before every production deploy.

## Logging

Standard Python/Django logging, configured in `nigerrents/settings.py`,
writing to `logs/`. No external monitoring service required — add Sentry
later only if you actually want it (there's a commented placeholder in
`.env.example`).

## Troubleshooting

- **App won't start / `ImportError` on boot**: usually a signals module
  importing something that doesn't exist yet (e.g. `notifications/emails.py`
  missing while `notifications/signals.py` expects it). Run
  `python manage.py check` first — it'll surface import errors immediately.
- **`makemigrations --check` fails**: a model changed without a migration.
  Run `python manage.py makemigrations`, review the generated migration,
  commit it.
- **Notifications not firing on status changes**: see the `pre_save` note
  under Architecture above — this is the one signals gotcha in this
  codebase that's easy to accidentally reintroduce.
