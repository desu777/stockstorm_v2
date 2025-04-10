"""
Django settings for stockstorm_project project.

Generated by 'django-admin startproject' using Django 5.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os

# Dodajemy obsługę zmiennych środowiskowych z pliku .env
from dotenv import load_dotenv

# Ładujemy zmienne z pliku .env (znajdującego się w głównym katalogu projektu)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '../.env'))

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-br7*sac60)7rpbb=78iwl60%!v#h4*t*+yd^hs@6&wn1_x*z!#')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '94.131.97.54,stockstorm.online,127.0.0.1,stockstorm.xyz,www.stockstorm.xyz').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # Dodane dla filtrów humanize
    'home',
    'hpcrypto',
    'gt',  # Giełda Tradycyjna
    'rest_framework',
    'rest_framework.authtoken',
    'ai_agent',
    'livechat',  # Nowa aplikacja live chat
    'channels',  # Channels dla WebSockets
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'home.middleware.LiveStatusMiddleware',
    'home.sync_bot_middleware.SyncBotMiddleware',
]

if not DEBUG:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'stockstorm_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / "home/templates",
            BASE_DIR / "ai_agent",  # Dodane dla ai_agent/template
            BASE_DIR / "hpcrypto/templates",  # Dodane dla hpcrypto/templates
            BASE_DIR / "gt/templates",  # Dodane dla gt/templates
            BASE_DIR / "livechat/templates",  # Dodane dla livechat/templates
        ],  
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


WSGI_APPLICATION = 'stockstorm_project.wsgi.application'
ASGI_APPLICATION = 'stockstorm_project.asgi.application'  # Dodane dla Channels

# Channels configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer' if not DEBUG else 'channels.layers.InMemoryChannelLayer',
        'CONFIG': {
            "hosts": [(os.getenv('REDIS_HOST', '127.0.0.1'), int(os.getenv('REDIS_PORT', 6379)))],
        } if not DEBUG else {},
    },
}

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.mysql'),
        'NAME': os.getenv('DB_NAME', 'server'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'Polskikaktus9036.'),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '3306'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'home/static'),
    os.path.join(BASE_DIR, 'livechat/static'),
]

if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (User Uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = '/dashboard/'  # Przekierowanie po udanym logowaniu
LOGOUT_REDIRECT_URL = '/'  # Przekierowanie po wylogowaniu


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    )
}


# URLs mikrousług botów
BNB_MICROSERVICE_URL="http://127.0.0.1:8006"  # 51015rei (z reinwestycją)
BNB_MICROSERVICE_URL_2="http://127.0.0.1:8007"  # 51015 (bez reinwestycji)


# Session settings
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
SESSION_SAVE_EVERY_REQUEST = True

# To ensure cookies work properly
CSRF_COOKIE_SECURE = not DEBUG  # True w produkcji z HTTPS
SESSION_COOKIE_SECURE = not DEBUG  # True w produkcji z HTTPS
SECURE_SSL_REDIRECT = not DEBUG  # Przekierowanie na HTTPS w produkcji

# Ustawienia bezpieczeństwa dla produkcji
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1 rok
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# API tokens
MICROSERVICE_API_TOKEN = os.getenv('MICROSERVICE_API_TOKEN', '')
MICROSERVICE_API_TOKEN2 = os.getenv('MICROSERVICE_API_TOKEN2', '')
REGISTER_KEY = os.getenv('REGISTER_KEY', '')

# OpenAI and Pinecone Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY', '')
PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME', 'finalboss')
# Host for Pinecone index
PINECONE_HOST = os.getenv('PINECONE_HOST', '')
# Dodatkowe informacje o konfiguracji Pinecone
PINECONE_DIMENSION = os.getenv('PINECONE_DIMENSION', 1536)
PINECONE_METRIC = os.getenv('PINECONE_METRIC', "cosine")
PINECONE_CLOUD = os.getenv('PINECONE_CLOUD', "aws")
PINECONE_REGION = os.getenv('PINECONE_REGION', "us-east-1")
PINECONE_NAMESPACE = os.getenv('PINECONE_NAMESPACE', "trading_analysis")  # Dodane z pliku popo.py