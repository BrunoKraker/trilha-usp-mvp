import logging
import threading

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db import connection, connections
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from contas import limites

from .forms import ContatoForm

log = logging.getLogger(__name__)


def pagina(template, nav):
    def view(request):
        return render(request, template, {"nav": nav})
    return view


def _notificar_contato(msg):
    try:
        send_mail(f"[Trilha USP] Nova mensagem de contato: {msg.assunto}",
                  f"De: {msg.nome} <{msg.email}>\n\n{msg.mensagem}\n\n(Veja e responda no painel administrativo.)",
                  None, [settings.CONTATO_NOTIFICAR], fail_silently=False)
    except Exception:
        log.exception("Falha ao notificar mensagem de contato")
    finally:
        if settings.EMAIL_ASYNC:
            connections.close_all()


def contato(request):
    form = ContatoForm(request.POST or None)
    if request.method == "POST":
        ip = limites.hash_chave(limites.ip_do_cliente(request))
        if limites.excedeu("contato_ip", ip, settings.CONTATO_MAX_POR_HORA_IP, 3600):
            messages.error(request, "Muitas mensagens em pouco tempo. Tente novamente mais tarde.")
            return render(request, "core/contato.html", {"form": form, "nav": "contato"}, status=429)
        if form.is_valid():
            chave_email = limites.hash_chave(form.cleaned_data["email"])
            if limites.excedeu("contato_email", chave_email, settings.CONTATO_MAX_POR_DIA_EMAIL, 86400):
                messages.error(request, "Você já enviou mensagens demais hoje. Tente novamente amanhã.")
                return render(request, "core/contato.html", {"form": form, "nav": "contato"}, status=429)
            msg = form.save()
            limites.registrar("contato_ip", ip)
            limites.registrar("contato_email", chave_email)
            if settings.CONTATO_NOTIFICAR:
                if settings.EMAIL_ASYNC:
                    threading.Thread(target=_notificar_contato, args=(msg,), daemon=True).start()
                else:
                    _notificar_contato(msg)
            messages.success(request, "Mensagem registrada. Retornaremos em até cinco dias úteis.")
            return redirect("core:contato")
        messages.error(request, "Revise os campos do formulário.")
    return render(request, "core/contato.html", {"form": form, "nav": "contato"})


def healthz(request):
    """Verifica app e banco. Usado pelo Render e por monitores externos."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception:
        log.exception("Health check: banco indisponível")
        return JsonResponse({"status": "erro"}, status=503)
    return JsonResponse({"status": "ok"})


def robots_txt(request):
    base = f"{request.scheme}://{request.get_host()}"
    texto = f"User-agent: *\nDisallow: /entrar/\n\nSitemap: {base}/sitemap.xml\n"
    return HttpResponse(texto, content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    from disciplinas.models import Disciplina

    base = f"{request.scheme}://{request.get_host()}"
    caminhos = [reverse(n) for n in ("core:home", "core:modulos", "core:sobre", "core:documentacao",
                                      "core:contato", "core:privacidade", "core:termos", "disciplinas:lista")]
    caminhos += [reverse("disciplinas:detalhe", args=[c]) for c in
                 Disciplina.objects.filter(ativa=True).values_list("codigo", flat=True)]
    itens = "".join(f"<url><loc>{base}{c}</loc></url>" for c in caminhos)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{itens}</urlset>'
    return HttpResponse(xml, content_type="application/xml")
