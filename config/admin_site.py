"""Painel administrativo com bloqueio de força bruta no login (sem dependências extras)."""
from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig
from django.http import HttpResponse

JANELA = 15 * 60


class TrilhaAdminSite(AdminSite):
    site_header = "Trilha USP — administração"
    site_title = "Trilha USP"

    def login(self, request, extra_context=None):
        from contas import limites

        ip = limites.hash_chave(limites.ip_do_cliente(request))
        usuario = limites.hash_chave(request.POST.get("username", "")) if request.method == "POST" else ""
        if request.method == "POST" and (
                limites.excedeu("admin_ip", ip, settings.ADMIN_LOGIN_MAX_FALHAS_IP, JANELA)
                or (usuario and limites.excedeu("admin_user", usuario, settings.ADMIN_LOGIN_MAX_FALHAS_USUARIO, JANELA))):
            return HttpResponse("Muitas tentativas. Aguarde 15 minutos e tente de novo.", status=429,
                                content_type="text/plain; charset=utf-8")
        resposta = super().login(request, extra_context)
        if request.method == "POST" and resposta.status_code == 200:  # formulário reexibido = falha
            limites.registrar("admin_ip", ip)
            if usuario:
                limites.registrar("admin_user", usuario)
        return resposta


class TrilhaAdminConfig(AdminConfig):
    default_site = "config.admin_site.TrilhaAdminSite"
