import secrets

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from contas.models import TokenLogin


class Command(BaseCommand):
    help = ("Gera um link de login manualmente (para testes ou quando o e-mail falhar). "
            "Uso: gerar_link aluno@usp.br --base-url https://seu-site.onrender.com")

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--base-url", required=True)

    def handle(self, *args, email, base_url, **opts):
        email = email.strip().lower()
        if email.rsplit("@", 1)[-1] not in settings.ALLOWED_EMAIL_DOMAINS:
            raise CommandError("Domínio de e-mail não permitido.")
        token = secrets.token_urlsafe(32)
        TokenLogin.objects.create(email=email, token_hash=TokenLogin.hash_token(token))
        self.stdout.write(f"{base_url.rstrip('/')}/entrar/verificar/{token}/")
        self.stdout.write(f"(vale {settings.LOGIN_TOKEN_MINUTES} minutos e só pode ser usado uma vez)")
