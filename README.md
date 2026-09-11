# 9jaRent.com.ng

A Nigerian property rental marketplace. Renters browse published listings and
contact agents directly; agents (once approved) list properties and manage
inspections; admins moderate agents, properties and reports. No online
payments in this release — rent is agreed and paid outside the platform,
then the listing is marked rented.

9jaRent uses **Django + Bootstrap**, with **SQLite for local development**
and **MySQL for production**, and is designed for deployment on conventional
Python hosting/cPanel — no Node, no separate API layer, no
Redis/Celery/Docker.

## Features

- **Accounts**: renter and agent signup (email or phone login), agent
  approval workflow (pending/approved/rejected/suspended), email-OTP
  verification.
- **Properties**: draft → pending review → published/rejected → rented →
  archived lifecycle, image uploads, search/filter/sort.
- **Inspections**: renters request a viewing, agents accept/decline/complete.
- **Messaging**: direct renter ↔ agent conversations per property.
- **Notifications**: in-app + email, triggered automatically on status
  changes (agent approval, property approval, inspection updates, new
  messages, report resolutions).
- **Reports**: renters can report a listing or agent; admins review and
  resolve.
- **Favourites**, **agent/renter portal dashboards**, **admin dashboard**
  with pending-item counts.

## Technology stack

- Backend: Python, Django, Django ORM, Django auth, Django forms/templates
- Database: SQLite (local dev) / MySQL (production, required)
- Cache: Django's database-backed cache (production) / local-memory cache
  (dev) — used for dashboard metrics and OTP-resend rate limiting
- Frontend: HTML, CSS, Bootstrap, vanilla JS where needed
- Email: SMTP via `django.core.mail` — in every environment
- Deployment: cPanel (Passenger/WSGI), MySQL, SMTP

Deliberately **not** used: Node/React/Vue, Django REST Framework, Redis,
Celery, Docker, GraphQL, WebSockets — this stays a small, conventional
Django app that a single developer can host on cPanel. See "Background work
without Celery" below for how the handful of things that would normally
reach for Celery are done instead.

## Architecture

Modular monolith — one Django project, several apps, no service/API layer
between them:
