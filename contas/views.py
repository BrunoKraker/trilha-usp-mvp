import json
import logging
import random
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import limites
from .envio import enviar_login
from .forms import EmailForm, PerfilForm
from .models import TokenLogin, Usuario

log = logging.getLogger(__name__)


def _next_seguro(request):
    destino = request.POST.get("next") or request.GET.get("next") or ""
    ok = url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()},
                                         require_https=request.is_secure())
    return destino if ok else ""


def entrar(request):
    if request.user.is_authenticated:
        return redirect("core:home")
    form = EmailForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        if random.random() < 0.02:  # nosec B311 (sorteio de limpeza, sem uso criptográfico)  # limpeza oportunista de dados vencidos (sem tarefa agendada)
            try:
                limites.limpar_antigos()
            except Exception:
                log.exception("Falha na limpeza de dados vencidos")
        ip = limites.hash_chave(limites.ip_do_cliente(request))
        agora = timezone.now()
        global_dia = TokenLogin.objects.filter(criado_em__gte=agora - timedelta(days=1)).count()
        if (limites.excedeu("login_ip", ip, settings.LOGIN_IP_MAX_PER_HOUR, 3600)
                or global_dia >= settings.LOGIN_GLOBAL_MAX_PER_DAY):
            log.warning("Limite de pedidos de login atingido (ip ou global)")
            resp = render(request, "contas/entrar.html", {
                "form": EmailForm(), "next": _next_seguro(request), "nav": "entrar",
                "limite": "Muitos pedidos de acesso neste momento. Tente novamente em alguns minutos."})
            resp.status_code = 429
            return resp
        limites.registrar("login_ip", ip)
        recentes = TokenLogin.objects.filter(email=email, criado_em__gte=agora - timedelta(hours=1)).count()
        # Mesma resposta com ou sem envio: não revela limites nem se a conta existe.
        if recentes < settings.LOGIN_TOKEN_MAX_PER_HOUR:
            token = secrets.token_urlsafe(32)
            registro = TokenLogin.objects.create(email=email, token_hash=TokenLogin.hash_token(token))
            link = request.build_absolute_uri(reverse("contas:verificar", args=[token]))
            proximo = _next_seguro(request)
            if proximo:
                link += "?next=" + proximo
            enviar_login(
                registro.pk, email, "Seu link de acesso ao Trilha USP",
                f"Olá!\n\nClique para entrar no Trilha USP (vale por {settings.LOGIN_TOKEN_MINUTES} minutos "
                f"e só pode ser usado uma vez):\n\n{link}\n\n"
                "Se não foi você, ignore esta mensagem.")
        else:
            log.warning("Limite de links por e-mail atingido")
        return render(request, "contas/link_enviado.html")
    return render(request, "contas/entrar.html", {"form": form, "next": _next_seguro(request), "nav": "entrar"})


def verificar(request, token):
    h = TokenLogin.hash_token(token)
    limite = timezone.now() - timedelta(minutes=settings.LOGIN_TOKEN_MINUTES)
    valido = TokenLogin.objects.filter(token_hash=h, usado_em__isnull=True, criado_em__gte=limite).exists()
    if request.method == "POST" and valido:
        # Consumo atômico: só um POST consegue marcar como usado.
        n = TokenLogin.objects.filter(token_hash=h, usado_em__isnull=True, criado_em__gte=limite)\
            .update(usado_em=timezone.now())
        if n == 1:
            email = TokenLogin.objects.get(token_hash=h).email
            usuario = Usuario.objects.filter(email=email).first() or Usuario.objects.create_user(email)
            if not usuario.is_active:
                messages.error(request, "Conta desativada.")
                return redirect("core:home")
            if usuario.is_staff or usuario.is_superuser:
                # Contas com acesso ao painel exigem senha: o link do e-mail sozinho não basta.
                messages.error(request, "Contas de moderação entram pelo painel administrativo, com senha.")
                return redirect("core:home")
            login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
            if not usuario.perfil_completo:
                messages.info(request, "Complete seu perfil para poder contribuir.")
                return redirect("contas:perfil")
            return redirect(_next_seguro(request) or "core:home")
        valido = False
    return render(request, "contas/verificar.html", {"valido": valido, "token": token, "next": _next_seguro(request)})


@login_required
def perfil(request):
    form = PerfilForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perfil atualizado.")
        return redirect("disciplinas:lista")
    return render(request, "contas/perfil.html", {"form": form, "nav": "perfil"})


@require_POST
def sair(request):
    logout(request)
    messages.info(request, "Você saiu.")
    return redirect("core:home")


@login_required
def exportar_dados(request):
    """Cópia dos dados do próprio usuário (direito de acesso), em JSON."""
    u = request.user
    dados = {
        "email": u.email, "nome_exibicao": u.nome_exibicao,
        "ingresso_ano": u.ingresso_ano, "ingresso_semestre": u.ingresso_semestre,
        "criado_em": u.date_joined.isoformat(),
        "resumos": [{"disciplina": r.disciplina.codigo, "tipo": r.tipo, "titulo": r.titulo, "texto": r.corpo,
                     "criado_em": r.criado_em.isoformat(), "verificado": r.verificado}
                    for r in u.resumos.select_related("disciplina")],
        "avaliacoes_dificuldade": [{"disciplina": a.disciplina.codigo, "nota": a.nota}
                                   for a in u.avaliacoes.select_related("disciplina")],
    }
    resp = HttpResponse(json.dumps(dados, ensure_ascii=False, indent=2), content_type="application/json; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="meus-dados-trilha-usp.json"'
    return resp


@login_required
@require_POST
def excluir_conta(request):
    """Exclusão definitiva da conta e de tudo que o usuário publicou (resumos e notas)."""
    u = request.user
    if u.is_staff or u.is_superuser:
        messages.error(request, "Contas de moderação são removidas pela administração.")
        return redirect("contas:perfil")
    if request.POST.get("confirmar") != "EXCLUIR":
        messages.error(request, "Para excluir, digite EXCLUIR no campo de confirmação.")
        return redirect("contas:perfil")
    logout(request)
    u.delete()
    messages.success(request, "Sua conta e o que você publicou foram excluídos.")
    return redirect("core:home")
