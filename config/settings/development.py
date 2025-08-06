from .base import *

# Development-specific settings
DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# Use console email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Development database (can use SQLite for quick testing)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# Disable HTTPS redirects in development
SECURE_SSL_REDIRECT = False

# Development CORS settings
CORS_ALLOW_ALL_ORIGINS = True

# Disable Sentry in development
SENTRY_DSN = ''
