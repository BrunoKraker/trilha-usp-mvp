"""Envio de e-mail via API HTTPS do Brevo.

Por que existe: o plano grátis do Render bloqueia as portas SMTP (25/465/587), então Gmail/SMTP não funciona lá.
A API usa HTTPS (porta 443), que não é bloqueada. Sem dependências extras (só biblioteca padrão).
"""
import json
import logging
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

log = logging.getLogger(__name__)


class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        enviadas = 0
        for msg in email_messages:
            try:
                self._enviar(msg)
                enviadas += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return enviadas

    def _enviar(self, msg):
        chave = getattr(settings, "BREVO_API_KEY", "")
        if not chave:
            raise RuntimeError("BREVO_API_KEY não configurada.")
        nome, remetente = parseaddr(msg.from_email or settings.DEFAULT_FROM_EMAIL)
        payload = {
            "sender": {"email": remetente, **({"name": nome} if nome else {})},
            "to": [{"email": a} for a in msg.to],
            "subject": msg.subject,
            "textContent": msg.body,
        }
        req = urllib.request.Request(
            getattr(settings, "BREVO_API_URL", "https://api.brevo.com/v3/smtp/email"),
            data=json.dumps(payload).encode("utf-8"),
            headers={"api-key": chave, "content-type": "application/json", "accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 300:
                    raise RuntimeError(f"Brevo respondeu {resp.status}")
        except urllib.error.HTTPError as e:
            # Registra só status e código de erro; nunca a chave nem o conteúdo da mensagem.
            try:
                detalhe = json.loads(e.read().decode("utf-8", "replace")).get("code", "")
            except Exception:
                detalhe = ""
            log.error("Brevo recusou o envio: status=%s code=%s", e.code, detalhe)
            raise
