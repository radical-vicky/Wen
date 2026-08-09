"""
Django settings for the Radilox project.
Cloudinary-backed media hosting, Vercel-inspired dark theme.
"""
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production-please')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
# Vercel assigns a new *.vercel.app domain per project (and another one per
# preview deployment) — rather than needing ALLOWED_HOSTS updated by hand
# every time a project gets renamed or redeployed, a leading-dot entry
# tells Django to trust any subdomain of vercel.app automatically. This is
# safe: it doesn't open up arbitrary hosts, only Vercel's own domain space.
ALLOWED_HOSTS.append('.vercel.app')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Cloudinary
    'cloudinary_storage',
    'cloudinary',

    # Auth (allauth + Google social login)
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # Local apps
    'accounts',
    'media_hub',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

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
                'media_hub.context_processors.cloudinary_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Serverless hosts (Vercel, and most others) run on a read-only filesystem
# outside of /tmp, so SQLite — which needs to write journal/WAL files even
# to read — cannot work there. Locally (no DATABASE_URL set), we fall back
# to SQLite for zero-setup dev; in production, set DATABASE_URL to a real
# Postgres connection string (e.g. from Vercel Postgres, Neon, or Supabase).
DATABASE_URL = config('DATABASE_URL', default='')
if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=True)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static & media
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---- Cloudinary configuration ----
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# django-cloudinary-storage's CLOUDINARY_STORAGE setting configures the
# *storage backend* (saving new files). It does NOT reliably propagate to
# the underlying `cloudinary` SDK's own global config object, which is what
# CloudinaryResource.url / cloudinary.utils.cloudinary_url() read from when
# rendering an existing file's URL (used all over our templates and in
# media_hub.views.download). Relying on implicit bridging between the two
# packages is what causes "Must supply cloud_name in tag or in
# configuration" even when CLOUDINARY_STORAGE above is correct — so we
# configure the SDK explicitly and unconditionally here instead.
import cloudinary as _cloudinary_sdk
_cloudinary_sdk.config(
    cloud_name=CLOUDINARY_STORAGE['CLOUD_NAME'],
    api_key=CLOUDINARY_STORAGE['API_KEY'],
    api_secret=CLOUDINARY_STORAGE['API_SECRET'],
    secure=True,
)

# Unsigned upload preset used for fast, direct browser-to-Cloudinary uploads
# (bypasses the Django server entirely for file bytes -> much faster than
# proxying uploads through our own backend). Create this in your Cloudinary
# dashboard under Settings > Upload > Upload presets, with Signing Mode set
# to "Unsigned". See README for the exact steps.
CLOUDINARY_UPLOAD_PRESET = config('CLOUDINARY_UPLOAD_PRESET', default='radilox_unsigned')

# ---- Auth redirects ----
LOGIN_URL = 'account_login'
LOGIN_REDIRECT_URL = 'media_hub:feed'
LOGOUT_REDIRECT_URL = 'media_hub:feed'

# ---- django-allauth ----
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = config('ACCOUNT_EMAIL_VERIFICATION', default='none')  # 'none' for easy local dev; use 'mandatory' in production with a real email backend
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_SESSION_REMEMBER = True

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APPS': [
            {
                'client_id': config('GOOGLE_CLIENT_ID', default=''),
                'secret': config('GOOGLE_CLIENT_SECRET', default=''),
                'key': '',
            },
        ],
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
    }
}
SOCIALACCOUNT_LOGIN_ON_GET = True  # skip the "continue?" confirmation page for Google

# Upload size guardrails (Cloudinary free tier friendly)
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024
