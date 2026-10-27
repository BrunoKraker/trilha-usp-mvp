"""Configurações do Trilha USP. Tudo que varia por ambiente vem de variáveis de ambiente (.env)."""
import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [x.strip() for x in os.environ.get(name, default).split(",") if x.strip()]


DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key"
    else:
        raise RuntimeError("Defina SECRET_KEY no ambiente (nunca no código).")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else "")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
# O Render informa o domínio do serviço nesta variável.
_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _render_host:
    ALLOWED_HOSTS.append(_render_host)
    CSRF_TRUSTED_ORIGINS.append(f"https://{_render_host}")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "core",
    "contas",
    "disciplinas",
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
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Banco: DATABASE_URL (PostgreSQL em produção). Sem ela, usa SQLite local só para desenvolvimento.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=60,
        conn_health_checks=True,
    )
}

# Compatível com a conexão "pooled" do Neon (pgbouncer em modo transação).
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

AUTH_USER_MODEL = "contas.Usuario"
LOGIN_URL = "contas:entrar"
LOGIN_REDIRECT_URL = "core:home"

# Sem senha para alunos (login por link). A senha só vale para o superusuário do /admin/.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- E-mail (link de login). Em dev imprime no terminal; em produção use SMTP (Gmail). ---
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_TIMEOUT = 10
# Envio por API (Brevo) — necessário no Render grátis, que bloqueia SMTP. Use:
#   EMAIL_BACKEND=contas.email_backends.BrevoEmailBackend  e  BREVO_API_KEY=...
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_API_URL = os.environ.get("BREVO_API_URL", "https://api.brevo.com/v3/smtp/email")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "trilha-usp@localhost")

# --- Regras do Trilha USP ---
ALLOWED_EMAIL_DOMAINS = [d.lower() for d in env_list("ALLOWED_EMAIL_DOMAINS", "usp.br")]
LOGIN_TOKEN_MINUTES = int(os.environ.get("LOGIN_TOKEN_MINUTES", "15"))
LOGIN_TOKEN_MAX_PER_HOUR = int(os.environ.get("LOGIN_TOKEN_MAX_PER_HOUR", "5"))
# Visitante (sem login) pode ler o texto dos resumos? Padrão: não (só título/autor/selo).
RESUMOS_PUBLICOS = env_bool("RESUMOS_PUBLICOS", False)
MAX_ATUALIZACOES_NOTA = 3

# --- Segurança em produção ---
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # HTTPS_ONLY=false só para testar produção localmente sem TLS. Em produção, deixe o padrão (true).
    HTTPS_ONLY = env_bool("HTTPS_ONLY", True)
    SECURE_SSL_REDIRECT = HTTPS_ONLY
    SESSION_COOKIE_SECURE = HTTPS_ONLY
    CSRF_COOKIE_SECURE = HTTPS_ONLY
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "3600"))
    SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
