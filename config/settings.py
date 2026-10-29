"""Configurações do Trilha USP. Tudo que varia por ambiente vem de variáveis de ambiente (.env)."""
import os
import sys
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_int(name, default):
    return int(os.environ.get(name, str(default)))


def env_list(name, default=""):
    return [x.strip() for x in os.environ.get(name, default).split(",") if x.strip()]


DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key"  # nosec B105 (só com DEBUG=true; produção exige chave própria)
    else:
        raise RuntimeError("Defina SECRET_KEY no ambiente (nunca no código).")
elif not DEBUG:
    # Recusa chaves curtas ou copiadas de exemplos (.env.example, README).
    _fraca = len(SECRET_KEY) < 32 or SECRET_KEY.lower().startswith(("troque", "dev-only", "changeme", "exemplo"))
    if _fraca:
        raise RuntimeError("SECRET_KEY fraca ou de exemplo. Gere outra: python -c \"import secrets;print(secrets.token_urlsafe(50))\"")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else "")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
# O Render informa o domínio do serviço nesta variável.
_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _render_host:
    ALLOWED_HOSTS.append(_render_host)
    CSRF_TRUSTED_ORIGINS.append(f"https://{_render_host}")

# Caminho do painel administrativo. Em produção, use um valor não óbvio (ADMIN_URL=minha-gestao-x7k2/).
ADMIN_URL = os.environ.get("ADMIN_URL", "admin/").strip().lstrip("/")
if not ADMIN_URL.endswith("/"):
    ADMIN_URL += "/"

INSTALLED_APPS = [
    "config.admin_site.TrilhaAdminConfig",
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
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.SecurityHeadersMiddleware",
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

# Sem senha para alunos (login por link). A senha só vale para quem tem acesso ao painel (staff).
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
# Cache dos estáticos no navegador (1 h). Alterações no CSS/JS aparecem em até 1 h após o deploy.
WHITENOISE_MAX_AGE = 0 if DEBUG else env_int("STATIC_MAX_AGE", 3600)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- E-mail (link de login). Em dev imprime no terminal; em produção use a API do Brevo (HTTPS). ---
# O Render grátis bloqueia SMTP (portas 25/465/587), então SMTP só serve em outros provedores.
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_TIMEOUT = 8
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_API_URL = os.environ.get("BREVO_API_URL", "https://api.brevo.com/v3/smtp/email")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "trilha-usp@localhost")
# Enviar o e-mail de login em segundo plano (não prende o servidor se o provedor estiver lento).
TESTING = "test" in sys.argv
EMAIL_ASYNC = env_bool("EMAIL_ASYNC", True) and not TESTING  # nos testes o envio é síncrono
# Opcional: avisa este e-mail quando chegar mensagem pelo formulário de contato.
CONTATO_NOTIFICAR = os.environ.get("CONTATO_NOTIFICAR", "")

# --- Regras do Trilha USP ---
ALLOWED_EMAIL_DOMAINS = [d.lower() for d in env_list("ALLOWED_EMAIL_DOMAINS", "usp.br,demo.invalid" if DEBUG else "usp.br")]
LOGIN_TOKEN_MINUTES = env_int("LOGIN_TOKEN_MINUTES", 15)
# Limites de abuso (todos gravados no banco; valem para qualquer número de processos).
LOGIN_TOKEN_MAX_PER_HOUR = env_int("LOGIN_TOKEN_MAX_PER_HOUR", 5)        # por e-mail
LOGIN_IP_MAX_PER_HOUR = env_int("LOGIN_IP_MAX_PER_HOUR", 60)             # por IP (campus pode compartilhar IP)
LOGIN_GLOBAL_MAX_PER_DAY = env_int("LOGIN_GLOBAL_MAX_PER_DAY", 250)      # protege a cota diária do Brevo (300)
ADMIN_LOGIN_MAX_FALHAS_IP = env_int("ADMIN_LOGIN_MAX_FALHAS_IP", 10)     # por IP em 15 min
ADMIN_LOGIN_MAX_FALHAS_USUARIO = env_int("ADMIN_LOGIN_MAX_FALHAS_USUARIO", 5)  # por e-mail em 15 min
PUBLICAR_MAX_POR_HORA = env_int("PUBLICAR_MAX_POR_HORA", 5)
PUBLICAR_MAX_POR_DIA = env_int("PUBLICAR_MAX_POR_DIA", 20)
DENUNCIAR_MAX_POR_DIA = env_int("DENUNCIAR_MAX_POR_DIA", 10)
CONTATO_MAX_POR_HORA_IP = env_int("CONTATO_MAX_POR_HORA_IP", 5)
CONTATO_MAX_POR_DIA_EMAIL = env_int("CONTATO_MAX_POR_DIA_EMAIL", 3)
# Quantos proxies confiáveis existem na frente do app (Render). Veja o README ("IP do cliente").
TRUSTED_PROXY_HOPS = env_int("TRUSTED_PROXY_HOPS", 1)
# Retenção (dias)
RETENCAO_TOKENS_DIAS = 7
RETENCAO_CONTATO_DIAS = env_int("RETENCAO_CONTATO_DIAS", 365)
# Visitante (sem login) pode ler o texto dos resumos? Padrão: não (só título/autor/selo).
RESUMOS_PUBLICOS = env_bool("RESUMOS_PUBLICOS", False)
MAX_ATUALIZACOES_NOTA = 3
RESUMOS_POR_PAGINA = 10

# --- Segurança em produção ---
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # HTTPS_ONLY=false só para testar produção localmente sem TLS. Em produção, deixe o padrão (true).
    HTTPS_ONLY = env_bool("HTTPS_ONLY", True)
    SECURE_SSL_REDIRECT = HTTPS_ONLY
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]  # o health check do Render chega por HTTP interno
    SESSION_COOKIE_SECURE = HTTPS_ONLY
    CSRF_COOKIE_SECURE = HTTPS_ONLY
    # Sobe aos poucos (3600 -> 86400 -> 31536000) depois de validar o HTTPS. Sem includeSubdomains:
    # o domínio onrender.com é compartilhado com outros serviços.
    SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 3600)
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

# --- Monitoramento de erros (opcional; desligado sem SENTRY_DSN) ---
_sentry_dsn = os.environ.get("SENTRY_DSN", "")
if _sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(dsn=_sentry_dsn, send_default_pii=False, traces_sample_rate=0.0,
                    environment=os.environ.get("SENTRY_ENV", "producao"))
