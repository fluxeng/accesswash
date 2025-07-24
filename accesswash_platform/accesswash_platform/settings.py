"""
Django settings for accesswash_platform project.
AccessWash - Water Utility Portal Platform
"""

from pathlib import Path
import os
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-accesswash-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = ['*']

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

    'users',          # Utility custer models
    'core',           # Core accesswash platform 
    'distro',         # Field operations
    #'huduma',         # Customer support (future)
    #'analytics',      # Analytics (future)
)

INSTALLED_APPS = list(SHARED_APPS) + [
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
] + [app for app in TENANT_APPS if app not in SHARED_APPS]

# Add this to ensure admin works properly
TENANT_ADMIN_PREFIX = ''

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add whitenoise for static files
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

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '.accesswash.org',  # This allows ALL subdomains: *.accesswash.org
    'api.accesswash.org',
    'demo.accesswash.org', 
    'app.accesswash.org',
]


DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': os.getenv('DB_NAME', 'accesswash_db'),
        'USER': os.getenv('DB_USER', 'accesswash_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'AccessWash2024!'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter',)

DATABASES['default']['CONN_MAX_AGE'] = 60


# Django Tenants Configuration
TENANT_MODEL = "tenants.Utility"
TENANT_DOMAIN_MODEL = "tenants.Domain"
ORIGINAL_BACKEND = "django.contrib.gis.db.backends.postgis"
STATICFILES_STORAGE = "django_tenants.staticfiles.storage.TenantStaticFilesStorage"
DEFAULT_FILE_STORAGE = "django_tenants.files.storage.TenantFileSystemStorage"
SHOW_PUBLIC_IF_NO_TENANT_FOUND = True

SITE_ID = 1

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
        'tenants': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'users': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'infrastructure': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

LOGGING['loggers']['django_tenants'] = {
    'handlers': ['file', 'console'],
    'level': 'INFO',
    'propagate': True,
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    
    'JTI_CLAIM': 'jti',
    
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
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

# API Documentation Settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'AccessWASH V 1.00',
    'DESCRIPTION': 'Digital Twin Platform for Water Utilities with Integrated Customer Support',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,
    'SCHEMA_PATH_PREFIX': '/api/',
    'SERVERS': [
        {
            'url': 'http://localhost:8000',
            'description': 'Public Tenant (Master Control)'
        },
        {
            'url': 'http://demo.localhost:8000',
            'description': 'Demo Tenant (Water Utility Operations)'
        }
    ],
    'CONTACT': {
        'name': 'Distro V1 Support',
        'email': 'support@distro.app'
    },
    'LICENSE': {
        'name': 'Proprietary'
    }
}

# CORS Settings for Frontend
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://demo.localhost:3000",
    "https://api.accesswash.org",
    "https://demo.accesswash.org",
    "https://app.accesswash.org",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only in development

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.accesswash\.org$",  # All subdomains
    r"^http://localhost:8000$",
    r"^http://127\.0\.0\.1:8000$",
]

# CSRF Settings
CSRF_TRUSTED_ORIGINS = [
    'https://*.accesswash.org',  # Wildcard for all subdomains
    'https://api.accesswash.org',
    'https://demo.accesswash.org',
    'https://app.accesswash.org',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

CSRF_COOKIE_SECURE = not DEBUG  # Set to True in production with HTTPS
CSRF_COOKIE_SAMESITE = 'Lax'

SHOW_PUBLIC_IF_NO_TENANT_FOUND = True


# Content Security Policy for subdomains
CSP_DEFAULT_SRC = ("'self'", "*.accesswash.org")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "*.accesswash.org")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "*.accesswash.org")

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Cache Configuration (Redis) - Optional for Railway
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'KEY_PREFIX': 'accesswash_v1',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400  # 24 hours


# Email Configuration
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')

# Force SMTP backend if credentials are provided (for development testing)
if os.getenv('EMAIL_HOST_USER') and os.getenv('EMAIL_HOST_PASSWORD'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', f'AccessWash Platform <{os.getenv("EMAIL_HOST_USER")}>')
    
    # Email timeout and security settings
    EMAIL_TIMEOUT = 30
    EMAIL_USE_LOCALTIME = False
    
    print(f"📧 Email configured: {EMAIL_HOST_USER} via {EMAIL_HOST}:{EMAIL_PORT}")
else:
    print("📧 Email using console backend (no SMTP credentials)")

# Multi-tenant email settings
PLATFORM_URL = os.getenv('PLATFORM_URL', 'https://api.accesswash.org')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', EMAIL_HOST_USER if 'EMAIL_HOST_USER' in os.environ else 'admin@accesswash.org')

# Email rate limiting (emails per hour)
EMAIL_RATE_LIMIT = 100

# Security Settings for Production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Database optimization for production
    DATABASES['default']['CONN_MAX_AGE'] = 60


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

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