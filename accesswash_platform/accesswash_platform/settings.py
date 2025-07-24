"""
File: accesswash_platform/accesswash_platform/settings.py
Complete fixed Django settings for AccessWash platform
"""

from pathlib import Path
import os
from datetime import timedelta
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-accesswash-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

# FIXED: Comprehensive ALLOWED_HOSTS for cloud tunneling
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1', 
    '0.0.0.0',
    '.accesswash.org',  # Covers all subdomains
    'api.accesswash.org',
    'demo.accesswash.org', 
    'app.accesswash.org',
    'health.accesswash.org',
    '*.accesswash.org',  # Explicit wildcard
]

# Add any additional hosts from environment
additional_hosts = config('ADDITIONAL_ALLOWED_HOSTS', default='')
if additional_hosts:
    ALLOWED_HOSTS.extend([h.strip() for h in additional_hosts.split(',') if h.strip()])

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Application definition
SHARED_APPS = (
    'django_tenants',
    'tenants',  # Utility Tenant models
    
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'users',
    'django.contrib.admin',
    'django.contrib.staticfiles',

    'rest_framework',
    'django.contrib.gis',
    'corsheaders',
    'drf_spectacular',
    'django_extensions',
)

TENANT_APPS = (
    # Django apps needed in tenant schemas
    'django.contrib.contenttypes',
    'django.contrib.auth', 
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',  
    'django.contrib.gis',

    'users',          # Utility user models
    'core',           # Core accesswash platform 
    'distro',         # Field operations
)

INSTALLED_APPS = list(SHARED_APPS) + [
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
] + [app for app in TENANT_APPS if app not in SHARED_APPS]

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'accesswash_platform.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'accesswash_platform.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': config('DB_NAME', default='accesswash_db'),
        'USER': config('DB_USER', default='accesswash_user'),
        'PASSWORD': config('DB_PASSWORD', default='AccessWash2024!'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 60,
        
    }
}

DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter',)

# FIXED: Django Tenants Configuration
TENANT_MODEL = "tenants.Utility"
TENANT_DOMAIN_MODEL = "tenants.Domain"
ORIGINAL_BACKEND = "django.contrib.gis.db.backends.postgis"
SHOW_PUBLIC_IF_NO_TENANT_FOUND = True
PUBLIC_SCHEMA_URLCONF = 'accesswash_platform.urls'

SITE_ID = 1

# FIXED: Email Configuration with validation
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')

# Get email settings
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
    print(f"📧 SMTP Email configured: {EMAIL_HOST_USER} via {EMAIL_HOST}:{EMAIL_PORT}")
else:
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@accesswash.org')
    print("📧 Using console email backend (no SMTP credentials)")

# Multi-tenant email settings
PLATFORM_URL = config('PLATFORM_URL', default='https://api.accesswash.org')
ADMIN_EMAIL = config('ADMIN_EMAIL', default=EMAIL_HOST_USER or 'admin@accesswash.org')

# JWT Settings
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

# FIXED: CORS Settings for cloud tunneling
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000", 
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://api.accesswash.org",
    "https://demo.accesswash.org",
    "https://app.accesswash.org",
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.accesswash\.org$",
    r"^http://localhost:8000$",
    r"^http://127\.0\.0\.1:8000$",
]

# FIXED: CSRF Settings for cloud tunneling  
CSRF_TRUSTED_ORIGINS = [
    'https://*.accesswash.org',
    'https://api.accesswash.org',
    'https://demo.accesswash.org', 
    'https://app.accesswash.org',
    'https://health.accesswash.org',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Cache Configuration (Redis with fallback)
REDIS_URL = config('REDIS_URL', default='redis://127.0.0.1:6379/1')

try:
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
    print(f"📦 Redis cache configured: {REDIS_URL}")
except Exception as e:
    print(f"⚠️  Redis cache failed, using memory cache: {e}")
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# FIXED: Security Settings for cloud tunneling
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Logging Configuration
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
        'handlers': ['console'],
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
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

# DRF Spectacular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'AccessWash Platform API',
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


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'KEY_PREFIX': 'accesswash_v1',
        'TIMEOUT': 300,
    }
}