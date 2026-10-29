from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import urlencode
from django.views.decorators.http import require_POST

from contas import limites

from .forms import DenunciaForm, NotaForm, ResumoForm
from .models import AvaliacaoDificuldade, Denuncia, Disciplina, Resumo
from .regras import classe_dificuldade, pode_contribuir


def _base_queryset():
    return Disciplina.objects.filter(ativa=True).annotate(
        media=Avg("avaliacoes__nota"), n_aval=Count("avaliacoes", distinct=True))


def lista(request, codigo=None):
    if codigo and codigo != codigo.upper():  # URL canônica em maiúsculas
        return redirect("disciplinas:detalhe", codigo=codigo.upper())
    q = request.GET.get("q", "").strip()[:80]
    disciplinas = _base_queryset()
    if q:
        disciplinas = disciplinas.filter(Q(nome__icontains=q) | Q(codigo__icontains=q))
    disciplinas = list(disciplinas)
    grupos = {}
    for d in disciplinas:
        grupos.setdefault(d.semestre_ideal, []).append(d)
    grupos = sorted(grupos.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))

    selecionada = None
    if codigo:
        selecionada = get_object_or_404(_base_queryset(), codigo=codigo)
    elif disciplinas:
        selecionada = disciplinas[0]

    ctx = {"grupos": grupos, "q": q, "nav": "disciplinas", "selecionada": selecionada}
    if selecionada:
        media = selecionada.media
        resumos_qs = selecionada.resumos.filter(oculto=False).select_related("autor")
        pagina = Paginator(resumos_qs, settings.RESUMOS_POR_PAGINA).get_page(request.GET.get("pagina"))
        pode, motivo = pode_contribuir(request.user, selecionada)
        minha = None
        ja_denunciados = set()
        if request.user.is_authenticated:
            minha = AvaliacaoDificuldade.objects.filter(disciplina=selecionada, usuario=request.user).first()
            ja_denunciados = set(Denuncia.objects.filter(autor=request.user, resumo__disciplina=selecionada)
                                 .values_list("resumo_id", flat=True))
        ctx.update({
            "media": round(media, 1) if media is not None else None,
            "largura": round(media / 5 * 100) if media is not None else 0,
            "classe": classe_dificuldade(media),
            "resumos": pagina, "pagina": pagina,
            "qs_base": urlencode({"q": q}) + "&" if q else "",
            "ler_corpo": request.user.is_authenticated or settings.RESUMOS_PUBLICOS,
            "pode": pode, "motivo": motivo,
            "form_resumo": ResumoForm(),
            "form_denuncia": DenunciaForm(),
            "ja_denunciados": ja_denunciados,
            "minha": minha,
            "restantes": (settings.MAX_ATUALIZACOES_NOTA - minha.atualizacoes) if minha else None,
        })
    return render(request, "disciplinas/lista.html", ctx)


@login_required
@require_POST
def publicar(request, codigo):
    codigo = codigo.upper()
    disciplina = get_object_or_404(Disciplina, codigo=codigo, ativa=True)
    pode, motivo = pode_contribuir(request.user, disciplina)
    if not pode:
        messages.error(request, motivo)
        return redirect("disciplinas:detalhe", codigo=codigo)
    chave = limites.hash_chave(str(request.user.pk))
    if (limites.excedeu("publicar", chave, settings.PUBLICAR_MAX_POR_HORA, 3600)
            or limites.excedeu("publicar", chave, settings.PUBLICAR_MAX_POR_DIA, 86400)):
        messages.error(request, "Você publicou muita coisa em pouco tempo. Tente de novo mais tarde.")
        return redirect("disciplinas:detalhe", codigo=codigo)
    form = ResumoForm(request.POST)
    if form.is_valid():
        r = form.save(commit=False)
        r.disciplina, r.autor = disciplina, request.user
        r.save()
        limites.registrar("publicar", chave)
        messages.success(request, "Publicado! A moderação pode atribuir o selo de verificado depois.")
    else:
        erros = "; ".join(e for lst in form.errors.values() for e in lst)
        messages.error(request, f"Não foi possível publicar: {erros}")
    return redirect("disciplinas:detalhe", codigo=codigo)


@login_required
@require_POST
def avaliar(request, codigo):
    codigo = codigo.upper()
    disciplina = get_object_or_404(Disciplina, codigo=codigo, ativa=True)
    pode, motivo = pode_contribuir(request.user, disciplina)
    if not pode:
        messages.error(request, motivo)
        return redirect("disciplinas:detalhe", codigo=codigo)
    form = NotaForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Escolha uma nota de 1 a 5.")
        return redirect("disciplinas:detalhe", codigo=codigo)
    nota = form.cleaned_data["nota"]
    try:
        with transaction.atomic():
            # Trava a linha: envios simultâneos do mesmo aluno são processados um de cada vez.
            atual, criada = AvaliacaoDificuldade.objects.select_for_update().get_or_create(
                disciplina=disciplina, usuario=request.user, defaults={"nota": nota})
            if criada:
                messages.success(request, "Avaliação registrada.")
            elif atual.nota == nota:
                messages.info(request, "Sua nota já é essa.")
            elif atual.atualizacoes >= settings.MAX_ATUALIZACOES_NOTA:
                messages.error(request, "Você já usou todas as atualizações permitidas para esta nota.")
            else:
                atual.nota, atual.atualizacoes = nota, atual.atualizacoes + 1
                atual.save()
                messages.success(request, "Avaliação atualizada.")
    except IntegrityError:  # corrida na criação: outra requisição criou primeiro
        messages.info(request, "Sua avaliação já foi registrada.")
    return redirect("disciplinas:detalhe", codigo=codigo)


@login_required
@require_POST
def excluir_resumo(request, codigo, pk):
    codigo = codigo.upper()
    resumo = get_object_or_404(Resumo, pk=pk, disciplina__codigo=codigo)
    if resumo.autor_id != request.user.id and not request.user.e_moderador:
        messages.error(request, "Você só pode excluir os seus próprios resumos.")
    else:
        resumo.delete()
        messages.success(request, "Resumo excluído.")
    return redirect("disciplinas:detalhe", codigo=codigo)


@login_required
@require_POST
def denunciar(request, codigo, pk):
    codigo = codigo.upper()
    resumo = get_object_or_404(Resumo, pk=pk, disciplina__codigo=codigo, oculto=False)
    chave = limites.hash_chave(str(request.user.pk))
    if resumo.autor_id == request.user.id:
        messages.error(request, "Você não pode denunciar o seu próprio resumo.")
    elif limites.excedeu("denunciar", chave, settings.DENUNCIAR_MAX_POR_DIA, 86400):
        messages.error(request, "Limite diário de denúncias atingido.")
    else:
        form = DenunciaForm(request.POST)
        if form.is_valid():
            d = form.save(commit=False)
            d.resumo, d.autor = resumo, request.user
            try:
                with transaction.atomic():
                    d.save()
                limites.registrar("denunciar", chave)
                messages.success(request, "Denúncia enviada para a moderação. Obrigado.")
            except IntegrityError:
                messages.info(request, "Você já denunciou este resumo.")
        else:
            messages.error(request, "Escolha um motivo válido.")
    return redirect("disciplinas:detalhe", codigo=codigo)
