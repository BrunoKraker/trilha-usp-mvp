import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

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
        desde = timezone.now() - timedelta(hours=1)
        recentes = TokenLogin.objects.filter(email=email, criado_em__gte=desde).count()
        # Mesma resposta com ou sem envio: não revela limites nem se a conta existe.
        if recentes < settings.LOGIN_TOKEN_MAX_PER_HOUR:
            token = secrets.token_urlsafe(32)
            TokenLogin.objects.create(email=email, token_hash=TokenLogin.hash_token(token))
            link = request.build_absolute_uri(reverse("contas:verificar", args=[token]))
            proximo = _next_seguro(request)
            if proximo:
                link += "?next=" + proximo
            try:
                send_mail(
                    "Seu link de acesso ao Trilha USP",
                    f"Olá!\n\nClique para entrar no Trilha USP (vale por {settings.LOGIN_TOKEN_MINUTES} minutos "
                    f"e só pode ser usado uma vez):\n\n{link}\n\n"
                    "Se não foi você, ignore esta mensagem.",
                    None, [email], fail_silently=False,
                )
            except Exception:  # não loga o link nem o e-mail do destinatário
                log.exception("Falha ao enviar e-mail de login")
        else:
            log.warning("Limite de links de login atingido")
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
