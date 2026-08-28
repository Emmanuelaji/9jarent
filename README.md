# 9jaRent.com.ng

A Nigerian property rental marketplace. Renters browse published listings and
contact agents directly; agents (once approved) list properties and manage
inspections; admins moderate agents, properties and reports. No online
payments in this release — rent is agreed and paid outside the platform,
then the listing is marked rented.

9jaRent uses **Django + Bootstrap + SQLite** and is designed for deployment
on conventional Python hosting/cPanel — no Node, no separate API layer, no
Redis/Celery/Postgres/Docker.

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
- Database: SQLite
- Frontend: HTML, CSS, Bootstrap, vanilla JS where needed
- Email: SMTP via `django.core.mail`
- Deployment: cPanel (Passenger/WSGI), SQLite, SMTP

Deliberately **not** used: Node/React/Vue, Django REST Framework, Redis,
Celery, PostgreSQL/MySQL, Docker, GraphQL, WebSockets — this stays a small,
conventional Django app that a single developer can host on cPanel.

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
cp .env.example .env            # edit as needed; defaults work for local dev
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

SQLite is the default in both dev and production — no extra setup.

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

Never commit `.env`.

## Database & backups

Production database is SQLite (`db.sqlite3`). Back up regularly:

```bash
# Backup
cp db.sqlite3 backups/db-$(date +%Y%m%d-%H%M%S).sqlite3

# Restore
cp backups/db-<timestamp>.sqlite3 db.sqlite3
```

Also back up `media/` (uploaded images) and `.env` (not the file's secrets
themselves — just make sure you have a record of them somewhere safe).
Never expose the `backups/` directory or `db.sqlite3` through the web server.

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
3. Upload the project (excluding `venv/`, `.env`, `db.sqlite3` if you want a
   fresh DB, and `__pycache__/`).
4. Set environment variables in cPanel's "Python App" environment-variables
   section (same keys as `.env.example`), or create `.env` on the server.
5. `python manage.py migrate`
6. `python manage.py collectstatic`
7. `python manage.py createsuperuser`
8. Point cPanel's Passenger config at `nigerrents/wsgi.py`.
9. Attach the domain/subdomain to the app.
10. Ensure `media/`, `logs/`, and the directory holding `db.sqlite3` are
    writable by the app user.
11. Test end-to-end: registration, login, property creation + image upload,
    property approval, email notifications, admin dashboard, agent/renter
    portal pages, search, messaging, inspections, mobile layout.

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
