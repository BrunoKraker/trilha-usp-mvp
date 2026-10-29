"""Envio do e-mail de login, em segundo plano, registrando sucesso/falha no próprio token."""
import logging
import threading

from django.conf import settings
from django.core.mail import send_mail
from django.db import connections

from .models import TokenLogin

log = logging.getLogger(__name__)


def _enviar(token_pk, destino, assunto, corpo):
    status = "falhou"
    try:
        send_mail(assunto, corpo, None, [destino], fail_silently=False)
        status = "enviado"
    except Exception:  # não registra o link nem o destinatário
        log.exception("Falha ao enviar e-mail de login")
    finally:
        TokenLogin.objects.filter(pk=token_pk).update(status_envio=status)
        if settings.EMAIL_ASYNC:
            connections.close_all()


def enviar_login(token_pk, destino, assunto, corpo):
    if settings.EMAIL_ASYNC:
        threading.Thread(target=_enviar, args=(token_pk, destino, assunto, corpo), daemon=True).start()
    else:
        _enviar(token_pk, destino, assunto, corpo)
