import os
import sys
import dj_database_url
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# Set SECRET_KEY in the environment in production; the built-in value keeps
# local/dev working exactly as before.
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-pxx@ku-$dv53%w)cx0)$odp(bh^hhf225(8yz2i73k0bjtzp5@",
)

# SECURITY WARNING: don't run with debug turned on in production!
# Defaults to on for local development — set DEBUG=False on the server.
DEBUG = os.getenv("DEBUG", "true").strip().lower() in ("1", "true", "yes", "on")

ALLOWED_HOSTS = ["*"]

AUTH_USER_MODEL = "accounts.User" 
# Application definition

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "channels",
    "apps.accounts",
    "apps.MeetSoc",
    "apps.MeetChat",
    "apps.Media",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.MeetSoc.core.middleware.PageAccountMiddleware",
]

ROOT_URLCONF = "DevazBackend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "DevazBackend.wsgi.application"
ASGI_APPLICATION = "DevazBackend.asgi.application"

# ---------------------------------------------------------------------------
# Channels (WebSocket)
# ---------------------------------------------------------------------------
# Redis is optional: with a single ASGI process (daphne) the in-memory layer
# is enough for chat/notification/call fan-out. Set REDIS_URL (redis://…) when
# running more than one worker or more than one instance.
REDIS_URL = os.getenv("REDIS_URL", "").strip()

if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }

# ---------------------------------------------------------------------------
# Django REST Framework + JWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "apps.MeetSoc.core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",
        "otp": "5/min",
    },
}

from datetime import timedelta

SIMPLE_JWT = {
    # Keep the user signed in: the app auto-renews the session on every launch,
    # so a stored account stays valid for 90 days of not being opened.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=365),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "UPDATE_LAST_LOGIN": True,
}

# CORS (dev — allow all; tighten for production)
CORS_ALLOW_ALL_ORIGINS = True

# ---------------------------------------------------------------------------
# App runtime settings
# ---------------------------------------------------------------------------
RATELIMIT_POSTS_PER_HOUR = 30
FCM_SERVER_KEY = ""

# TURN relay for WebRTC calls — only included in /meetchat/calls/ice-servers/
# responses when TURN_SERVER_URL is set; STUN is always returned.
# TURN_SERVER_URL = "turn:turn.example.com:3478"
# TURN_USERNAME = "meetsoc"
# TURN_CREDENTIAL = "change-me"

# HTML sanitization (bleach)
BLEACH_ALLOWED_TAGS = [
    "a", "b", "i", "u", "strong", "em", "p", "br", "ul", "ol", "li",
    "blockquote", "code", "pre", "span",
]
BLEACH_ALLOWED_ATTRIBUTES = {"a": ["href", "title", "target"], "span": ["class"]}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
# CELERY_ENABLED=False -> notification/feed tasks run inline (synchronously) in
# the request, so rows are always created. Flip to True only when a Celery
# worker + broker are actually running.
CELERY_ENABLED = False
CELERY_BROKER_URL = "redis://127.0.0.1:6379/1"
CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/1"
CELERY_TASK_ALWAYS_EAGER = False
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases


DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://devazdb_user:EBMYT5YqvOoIiv9nGxTqQG48afOdy10K@dpg-dar5b0c9v7es739i1vng-a.singapore-postgres.render.com/devazdb'
)

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        ssl_require=True  # Supabase-এর জন্য SSL Connection বাধ্যতামূলক
    )
}


PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",   # pip install argon2-cffi
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"

# Uploaded media (avatars, covers, post photos/videos...)
# Uploaded files are stored under BASE_DIR/media and served at /media/...
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"