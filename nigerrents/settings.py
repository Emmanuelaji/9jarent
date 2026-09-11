"""
Django settings for 9jaRent.com.ng.

- MySQL in production (DEBUG=False), SQLite locally (DEBUG=True).
- Email always via SMTP — no console fallback.
- Fails fast on missing required env vars.
"""

import os
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# --- Core -------------------------------------------------------------------

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)

if DEBUG:
    ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
else:
    ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# Only enable behind a proxy that OVERWRITES (not appends) X-Forwarded-For.
TRUST_PROXY_HEADERS = env.bool("TRUST_PROXY_HEADERS", default=False)

# --- Applications -----------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "crispy_forms",
    "crispy_bootstrap5",
    "django_filters",
    "properties",
    "accounts",
    "dashboard",
    "favourites",
    "messaging",
    "inspections",
    "notifications",
    "reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "nigerrents.middleware.RateLimitMiddleware",
    "nigerrents.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "nigerrents.urls"
WSGI_APPLICATION = "nigerrents.wsgi.application"

AUTH_USER_MODEL = "accounts.CustomUser"

# Email, phone, or username login; ModelBackend fallback for admin/CLI.
AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailOrPhoneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

CRISPY_TEMPLATE_PACK = "bootstrap5"

# --- Templates --------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "messaging.context_processors.unread_messages",
                "notifications.context_processors.unread_notifications",
                "dashboard.context_processors.admin_sidebar_counts",
                "nigerrents.context_processors.csp",
                "nigerrents.context_processors.site_url",
            ],
        },
    },
]

# --- Static & media ---------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

from django.contrib.messages import constants as message_constants
MESSAGE_TAGS = {message_constants.ERROR: "danger"}

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # CompressedManifest needs collectstatic first; production only.
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

WHATSAPP_DEFAULT_MESSAGE = env(
    "WHATSAPP_DEFAULT_MESSAGE",
    default=(
        "Hello, I am interested in the {title} in {location} listed on "
        "9jaRent.com.ng. Is it still available?"
    ),
)

# --- Database ---------------------------------------------------------------
# DEBUG=True  -> SQLite unless DATABASE_URL is set.
# DEBUG=False -> MySQL required.
#
# OPTIONS pin correctness: utf8mb4 for 4-byte UTF-8 (emoji),
# STRICT_TRANS_TABLES so over-length strings raise instead of truncating.

if DEBUG and not env("DATABASE_URL", default=None):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    if not env("DATABASE_URL", default=None):
        raise ImproperlyConfigured(
            "DATABASE_URL is required when DEBUG=False. Set it to a MySQL "
            "URL, e.g. mysql://user:password@localhost:3306/9jarent."
        )

    DATABASES = {"default": env.db()}

    engine = DATABASES["default"].get("ENGINE", "")
    if "sqlite" in engine:
        raise ImproperlyConfigured(
            "DATABASE_URL points at SQLite, unsupported in production. "
            "Use a mysql:// URL."
        )
    if "mysql" not in engine:
        raise ImproperlyConfigured(
            f"DATABASE_URL engine is {engine!r}, but this project is MySQL-only."
        )

    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"].setdefault("charset", "utf8mb4")
    DATABASES["default"]["OPTIONS"].setdefault(
        "init_command", "SET sql_mode='STRICT_TRANS_TABLES'"
    )
    # Long-lived Passenger processes benefit from persistent connections;
    # CONN_HEALTH_CHECKS reopens dropped ones instead of erroring.
    DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=600)
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# --- Cache ------------------------------------------------------------------
# LocMem locally; DB-backed in production (requires createcachetable).

if DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "django_cache_table",
        }
    }

# --- Auth & i18n ------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Security ---------------------------------------------------------------

SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# HSTS is opt-in — a misconfigured deploy with this on can lock users out
# for a year. Enable after verifying HTTPS end-to-end.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

if DEBUG:
    CSRF_TRUSTED_ORIGINS = env.list(
        "CSRF_TRUSTED_ORIGINS", default=["http://localhost:8000"]
    )
else:
    CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# --- Email (always SMTP) ----------------------------------------------------

EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=not EMAIL_USE_SSL)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL", default="9jaRent <noreply@9jarent.com.ng>"
)

if EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
    if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
        raise ImproperlyConfigured(
            "EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are required — this "
            "project always uses SMTP. See env.example."
        )

SITE_URL = env("SITE_URL", default="http://localhost:8000" if DEBUG else None)
if not SITE_URL:
    raise ImproperlyConfigured(
        "SITE_URL is required when DEBUG=False (used to build absolute links "
        "in emails). Set it to e.g. https://www.9jarent.com.ng."
    )

PASSWORD_RESET_TIMEOUT = 3600

# --- Logging ----------------------------------------------------------------
# Split by concern: django.log (everything), errors.log (ERROR+ only),
# security.log (rate limiting, CSRF, permission denials), auth.log
# (login/signup/OTP/password). All rotate with 5-10 backups.

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "verbose": {
            "format": (
                "{levelname} {asctime} {module}:{lineno} "
                "[pid:{process:d} tid:{thread:d}] {message}"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file_general": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "django.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "file_errors": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "errors.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
            "level": "ERROR",
        },
        "file_security": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "security.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "file_auth": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "auth.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
            "filters": ["require_debug_false"],
            "level": "ERROR",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "file_security", "file_errors"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.contrib.auth": {
            "handlers": ["console", "file_auth", "file_general"],
            "level": "INFO",
            "propagate": False,
        },
        "accounts": {
            "handlers": ["console", "file_auth", "file_general", "file_errors"],
            "level": "INFO",
            "propagate": False,
        },
        "properties": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": "INFO",
            "propagate": False,
        },
        "messaging": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": "INFO",
            "propagate": False,
        },
        "inspections": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": "INFO",
            "propagate": False,
        },
        "notifications": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": "INFO",
            "propagate": False,
        },
        "dashboard": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": "INFO",
            "propagate": False,
        },
        "reports": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": "INFO",
            "propagate": False,
        },
        "nigerrents.middleware": {
            "handlers": ["console", "file_security", "file_general"],
            "level": "INFO",
            "propagate": False,
        },
        "nigerrents": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

ADMINS = [
    tuple(entry.split(" <"))
    for entry in env.list("ADMINS", default=[])
]
ADMINS = [(name.strip(), email.rstrip(">").strip()) for name, email in ADMINS]