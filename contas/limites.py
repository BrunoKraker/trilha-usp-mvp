"""Limites de abuso persistidos no banco (valem para vários processos/instâncias).

Guardamos só um hash (HMAC com a SECRET_KEY) do IP ou do e-mail, nunca o valor original.
"""
import hashlib
import hmac
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import EventoLimite

log = logging.getLogger(__name__)
_ja_logou_hops = False


def hash_chave(valor: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), (valor or "").strip().lower().encode(), hashlib.sha256).hexdigest()[:40]


def ip_do_cliente(request) -> str:
    """IP do cliente. Atrás de N proxies confiáveis, o IP real é o N-ésimo a partir da direita em X-Forwarded-For."""
    global _ja_logou_hops
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    partes = [p.strip() for p in xff.split(",") if p.strip()]
    if not _ja_logou_hops and partes:
        _ja_logou_hops = True  # ajuda a calibrar TRUSTED_PROXY_HOPS (não registra IPs)
        log.info("X-Forwarded-For com %s entrada(s); TRUSTED_PROXY_HOPS=%s", len(partes), settings.TRUSTED_PROXY_HOPS)
    hops = settings.TRUSTED_PROXY_HOPS
    if partes and hops > 0:
        return partes[-hops] if len(partes) >= hops else partes[0]
    return request.META.get("REMOTE_ADDR", "")


def contar(tipo: str, chave: str, janela_segundos: int) -> int:
    desde = timezone.now() - timedelta(seconds=janela_segundos)
    return EventoLimite.objects.filter(tipo=tipo, chave=chave, criado_em__gte=desde).count()


def excedeu(tipo: str, chave: str, maximo: int, janela_segundos: int) -> bool:
    return contar(tipo, chave, janela_segundos) >= maximo


def registrar(tipo: str, chave: str) -> None:
    EventoLimite.objects.create(tipo=tipo, chave=chave)


def limpar_antigos() -> dict:
    """Remove dados vencidos: eventos de limite, tokens de login e sessões expiradas."""
    from django.contrib.sessions.models import Session

    from .models import TokenLogin

    agora = timezone.now()
    r = {}
    r["eventos"] = EventoLimite.objects.filter(criado_em__lt=agora - timedelta(days=2)).delete()[0]
    r["tokens"] = TokenLogin.objects.filter(
        criado_em__lt=agora - timedelta(days=settings.RETENCAO_TOKENS_DIAS)).delete()[0]
    r["sessoes"] = Session.objects.filter(expire_date__lt=agora).delete()[0]
    from core.models import MensagemContato

    r["contato"] = MensagemContato.objects.filter(
        criado_em__lt=agora - timedelta(days=settings.RETENCAO_CONTATO_DIAS)).delete()[0]
    return r
