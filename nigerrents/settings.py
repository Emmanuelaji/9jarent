import os
import sys
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# True when running under `manage.py test` - lets middleware (e.g. rate
# limiting) behave differently so the automated test suite isn't coupled
# to a shared process-wide cache across unrelated test methods.
TESTING = 'test' in sys.argv

# Only enable this if the app sits behind a proxy/load balancer that OVERWRITES
# (not appends to) X-Forwarded-For, so the header can't be spoofed by clients.
# On a typical shared-hosting/cPanel deployment with no such proxy, leave False.
TRUST_PROXY_HEADERS = env.bool('TRUST_PROXY_HEADERS', default=False)

if TESTING:
    # Speed up the test suite only: PBKDF2's production-strength iteration
    # count makes every create_user()/login() call needlessly slow in tests.
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# SECURITY WARNING: keep the secret key used in production secret!
# In production, this MUST be set via environment variable.
SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    
    # Custom Apps
    'properties',
    'accounts',
    'dashboard',
    'favourites',
    'messaging',
    'inspections',
    'notifications',
    'reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'nigerrents.middleware.RateLimitMiddleware',
    'nigerrents.middleware.SecurityHeadersMiddleware',
]

ROOT_URLCONF = 'nigerrents.urls'
AUTH_USER_MODEL = 'accounts.CustomUser'

# Login accepts email, phone, or username (the login page offers Email/Phone
# tabs) - ModelBackend stays as a fallback for Django admin / manage.py flows.
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrPhoneBackend',
    'django.contrib.auth.backends.ModelBackend',
]
CRISPY_TEMPLATE_PACK = 'bootstrap5'

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

from django.contrib.messages import constants as message_constants
MESSAGE_TAGS = {message_constants.ERROR: 'danger'}
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # CompressedManifestStaticFilesStorage requires collectstatic to have
        # run first (it 404s on any {% static %} reference not yet in its
        # manifest) - fine for production, but forcing every contributor to
        # run collectstatic before `manage.py test` is unnecessary friction.
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if TESTING
        else "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Used to build the pre-filled WhatsApp "Chat on Agent" link on property pages.
# {title} and {location} are filled in per-property.
WHATSAPP_DEFAULT_MESSAGE = (
    "Hello, I am interested in the {title} in {location} listed on 9jaRent.com.ng. "
    "Is it still available?"
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'messaging.context_processors.unread_messages',
                'notifications.context_processors.unread_notifications',
                'dashboard.context_processors.admin_sidebar_counts',
                'nigerrents.context_processors.csp',
],
        },
    },
]

WSGI_APPLICATION = 'nigerrents.wsgi.application'

# --------------------------------------------------------------------------
# Database: SQLite for local development (zero setup), PostgreSQL required
# in production. cPanel's "PostgreSQL Databases" panel provisions a normal
# Postgres database/user just like it does for MySQL - set DATABASE_URL to
# postgres://USER:PASSWORD@localhost:5432/DBNAME in the app's environment
# variables (or .env) and migrate as usual.
#
# We deliberately do NOT fall back to SQLite when DEBUG=False: SQLite's
# single-writer file lock causes real "database is locked" 500s under any
# concurrent traffic, so silently defaulting to it in production is worse
# than failing loudly at startup with a clear message.
# --------------------------------------------------------------------------
if not DEBUG and not TESTING:
    if not env('DATABASE_URL', default=None):
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            "DATABASE_URL is required when DEBUG=False. Set it to a PostgreSQL "
            "URL, e.g. postgres://user:password@localhost:5432/9jarent - see "
            "README.md > Database & backups. Refusing to silently fall back "
            "to SQLite in production."
        )
    DATABASES = {'default': env.db()}
    engine = DATABASES['default'].get('ENGINE', '')
    if 'sqlite' in engine:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            "DATABASE_URL points at SQLite, but SQLite is not supported in "
            "production (DEBUG=False). Use a postgres:// URL instead."
        )
    # Keep the DB connection open across requests instead of reconnecting
    # every time (cPanel/Passenger processes are long-lived, so this is a
    # meaningful win with no extra moving parts).
    DATABASES['default']['CONN_MAX_AGE'] = env.int('CONN_MAX_AGE', default=600)
else:
    DATABASES = {
        'default': env.db(default='sqlite:///db.sqlite3')
    }

# --------------------------------------------------------------------------
# Cache: Django's database-backed cache. No Redis/Celery in this stack - the
# db cache backend needs no extra service, just one table (created by
# `python manage.py createcachetable`, see README.md). Used for short-TTL
# caching of expensive aggregate queries (e.g. the admin dashboard metrics)
# and can also back rate limiting if you ever move off single-process dev
# semantics; the default LocMemCache is used for local dev/tests since it
# needs no migration.
# --------------------------------------------------------------------------
if DEBUG or TESTING:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'django_cache_table',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Additional Security Headers
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=0)  # Set to 31536000 in production
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False)
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# CSRF Trusted Origins (required for HTTPS in production)
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])


# Email: defaults to printing to the console in local development so
# password-reset works out of the box without real SMTP credentials.
# Set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend in .env for production.
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='9jaRent <noreply@9jarent.com.ng>')

# Used to build absolute links in emails (notifications, etc) sent from
# contexts with no request object to call request.build_absolute_uri() on.
SITE_URL = env('SITE_URL', default='http://localhost:8000' if DEBUG else '')
PASSWORD_RESET_TIMEOUT = 3600  # 1 hour

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': env('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'properties': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'dashboard': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
import pathlib
log_dir = pathlib.Path(BASE_DIR) / 'logs'
log_dir.mkdir(exist_ok=True)