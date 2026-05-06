"""
Django settings for bitecoapp project — Sprint 3.

Cambios respecto al original (todos comentados con # >>> NUEVO o # >>> CAMBIO):
- Lectura de variables de entorno (12-factor)
- social-auth-app-django con Auth0 (ASR-01)
- AuditMiddleware activado (ASR-14)
- 3 BDs configuradas: default (accounts) + monitoring + monitoring_replica
- AUTH_USER_MODEL = usuario.Usuario
- Database router primary/replica (ASR-07)
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# >>> CAMBIO: lectura desde el entorno
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-+t@g$_$x0$h=hx%4r+@n5$qkj1q8)folzt=h!9ca3d8ylgs+$+",  # solo dev
)
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")


# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # >>> NUEVO: Auth0 OAuth2
    "social_django",

    "alerta",
    "cuentaCloud",
    "empresa",
    "factura",
    "pago",
    "planSuscripcion",
    "proyecto",
    "recursoCloud",
    "registroAuditoria",
    "registroCosto",
    "reporte",
    "usuario",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # >>> NUEVO: ASR-14 - registra cada request a endpoints auditables
    "bitecoapp.audit_middleware.AuditMiddleware",
]

ROOT_URLCONF = "bitecoapp.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # >>> NUEVO: directorio global de templates (base/, etc.)
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # >>> NUEVO: requeridos por social_django
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    },
]

WSGI_APPLICATION = "bitecoapp.wsgi.application"

# >>> CAMBIO: 3 bases de datos (accounts + monitoring primary + replica)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.environ.get("DB_NAME_DEFAULT", "accounts_db"),
        "USER": os.environ.get("DB_USER", "biteco_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "biteco_pass"),
        "HOST": os.environ.get("DB_HOST_DEFAULT", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    },
    "monitoring": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.environ.get("DB_NAME_MONITORING", "monitoring_db"),
        "USER": os.environ.get("DB_USER", "biteco_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "biteco_pass"),
        "HOST": os.environ.get("DB_HOST_MONITORING_PRIMARY", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    },
    # >>> NUEVO: lectura desde la replica (ASR-07 - Streaming Replication)
    "monitoring_replica": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.environ.get("DB_NAME_MONITORING", "monitoring_db"),
        "USER": os.environ.get("DB_USER", "biteco_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "biteco_pass"),
        "HOST": os.environ.get("DB_HOST_MONITORING_REPLICA", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    },
}

# >>> NUEVO: router primary/replica
DATABASE_ROUTERS = ["bitecoapp.db_router.MonitoringReplicaRouter"]

# >>> NUEVO: usuario.Usuario hereda de AbstractUser y agrega rol/empresa_id
AUTH_USER_MODEL = "usuario.Usuario"


# ============================================================================
# >>> NUEVO BLOQUE: Auth0 + social_django (ASR-01)
# ============================================================================
AUTHENTICATION_BACKENDS = [
    "social_core.backends.auth0.Auth0OAuth2",
    "django.contrib.auth.backends.ModelBackend",
]

SOCIAL_AUTH_TRAILING_SLASH = False
SOCIAL_AUTH_AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "")
SOCIAL_AUTH_AUTH0_KEY = os.environ.get("AUTH0_CLIENT_ID", "")
SOCIAL_AUTH_AUTH0_SECRET = os.environ.get("AUTH0_CLIENT_SECRET", "")
SOCIAL_AUTH_AUTH0_SCOPE = ["openid", "profile", "email"]

LOGIN_URL = "/login/auth0"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# Pipeline post-login: extrae rol y empresa_id del JWT y los persiste en User
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
    "usuario.pipeline.save_role_and_empresa",  # custom (ver usuario/pipeline.py)
)


# ============================================================================
# Logging
# ============================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "loggers": {
        "biteco.audit": {"handlers": ["console"], "level": "INFO"},
        "django": {"handlers": ["console"], "level": "INFO"},
    },
}


# ============================================================================
# Resto sin cambios
# ============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Detras del ALB el client IP real viene en X-Forwarded-For
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
