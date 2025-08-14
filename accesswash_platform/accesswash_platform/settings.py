"""
File: accesswash_platform/accesswash_platform/settings.py
Complete fixed Django settings for AccessWash platform
"""
"""
File: accesswash_platform/accesswash_platform/settings.py
Complete Django settings for AccessWash platform, optimized for Railway deployment.
"""

from pathlib import Path
import os
from datetime import timedelta
from decouple import config
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)  # Default to False for production

# ALLOWED_HOSTS configuration for Railway and local development
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '.accesswash.org',  # Covers all subdomains
    'api.accesswash.org',
    'demo.accesswash.org',
    'app.accesswash.org',
    'health.accesswash.org',
    '*.accesswash.org',  # Explicit wildcard for subdomains
    '.railway.app',  # Railway's domain for deployment
]

# Add additional hosts from environment variable if provided
additional_hosts = config('ADDITIONAL_ALLOWED_HOSTS', default='')
if additional_hosts:
    ALLOWED_HOSTS.extend([h.strip() for h in additional_hosts.split(',') if h.strip()])

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Authentication backends for custom and default authentication
AUTHENTICATION_BACKENDS = [
    'portal.authentication.CustomerAuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Application definition
SHARED_APPS = (
    'django_tenants',  # Multi-tenancy support
    'tenants',  # Utility Tenant models
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'users',  # Custom user models
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'rest_framework',  # Django REST Framework
    'django.contrib.gis',  # GIS support for geospatial data
    'corsheaders',  # CORS support
    'drf_spectacular',  # API documentation
    'django_extensions',  # Developer tools
)

TENANT_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'users',  # Utility user models
    'core',  # Core accesswash platform
    'distro',  # Field operations
    'portal',  # Customer portal
    'support',  # Customer support
)

# Combine shared and tenant apps, ensuring no duplicates
INSTALLED_APPS = list(SHARED_APPS) + [
    'rest_framework_simplejwt',  # JWT authentication
    'rest_framework_simplejwt.token_blacklist',  # Token blacklist support
] + [app for app in TENANT_APPS if app not in SHARED_APPS]

# Middleware configuration
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # Multi-tenancy middleware
    'corsheaders.middleware.CorsMiddleware',  # CORS handling
    'django.middleware.security.SecurityMiddleware',  # Security enhancements
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static file serving
    'django.contrib.sessions.middleware.SessionMiddleware',  # Session handling
    'django.middleware.common.CommonMiddleware',  # Common utilities
    'django.middleware.csrf.CsrfViewMiddleware',  # CSRF protection
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Authentication
    'django.contrib.messages.middleware.MessageMiddleware',  # Messages framework
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Clickjacking protection
]

# URL configuration
ROOT_URLCONF = 'accesswash_platform.urls'

# Template configuration
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Custom template directory
        'APP_DIRS': True,  # Include app-specific templates
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGI application
WSGI_APPLICATION = 'accesswash_platform.wsgi.application'

# Database configuration using dj-database-url for Railway
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='postgres://accesswash_user:AccessWash2024!@localhost:5432/accesswash_db'),
        conn_max_age=60,  # Keep connections alive for 60 seconds
        engine='django_tenants.postgresql_backend',  # Compatible with django_tenants
    )
}

# Database routers for multi-tenancy
DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter',)

# Django Tenants configuration
TENANT_MODEL = "tenants.Utility"
TENANT_DOMAIN_MODEL = "tenants.Domain"
ORIGINAL_BACKEND = "django.contrib.gis.db.backends.postgis"
SHOW_PUBLIC_IF_NO_TENANT_FOUND = True
PUBLIC_SCHEMA_URLCONF = 'accesswash_platform.urls'

# Django Sites framework
SITE_ID = 1

# Email configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')

# SMTP settings if credentials are provided
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default=None)
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default=None)

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=f'AccessWash Platform <{EMAIL_HOST_USER}>')
    EMAIL_TIMEOUT = 30
else:
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@accesswash.org')

# Multi-tenant email settings
PLATFORM_URL = config('PLATFORM_URL', default='https://api.accesswash.org')
ADMIN_EMAIL = config('ADMIN_EMAIL', default=EMAIL_HOST_USER or 'admin@accesswash.org')

# JWT settings for authentication
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'portal.authentication.CustomerTokenAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# CORS settings for secure API access
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # Disabled for production security

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://api.accesswash.org",
    "https://demo.accesswash.org",
    "https://app.accesswash.org",
    "https://health.accesswash.org",
]

# Dynamically add Railway domain if provided
RAILWAY_DOMAIN = config('RAILWAY_DOMAIN', default=None)
if RAILWAY_DOMAIN:
    CORS_ALLOWED_ORIGINS.append(f"https://{RAILWAY_DOMAIN}")

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.accesswash\.org$",
    r"^https://.*\.railway\.app$",  # Support Railway's domain
    r"^http://localhost:8000$",
    r"^http://127\.0\.0\.1:8000$",
    r"^http://localhost:3000$",
    r"^http://127\.0\.0\.1:3000$",
]

# CSRF settings for secure form submissions
CSRF_TRUSTED_ORIGINS = [
    'https://api.accesswash.org',
    'https://demo.accesswash.org',
    'https://app.accesswash.org',
    'https://health.accesswash.org',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:3004',
]

if RAILWAY_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RAILWAY_DOMAIN}")

# Cache configuration using Redis (Railway's REDIS_URL)
REDIS_URL = config('REDIS_URL', default='redis://redis:6379/1')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'KEY_PREFIX': 'accesswash_v1',
        'TIMEOUT': 300,
        'OPTIONS': {
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
        },
    }
}

# Session configuration using database backend
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Database-backed sessions
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_SECURE = not DEBUG  # Use secure cookies in production
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Security settings for production
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True  # Redirect HTTP to HTTPS

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'  # WhiteNoise for static files

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Logging configuration
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

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
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'email_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'email.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],  # Stream logs to Railway dashboard
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'core.email_service': {
            'handlers': ['email_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'tenants': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# DRF Spectacular settings for API documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'AccessWASH Platform API',
    'DESCRIPTION': 'Digital Water Utility Management Platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/',
}

# Session Configuration - Use database instead of cache
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# CACHES Configuration of Redis which is used for caching things like sessions, etc
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'KEY_PREFIX': 'accesswash_v1',
        'TIMEOUT': 300,
    }
}