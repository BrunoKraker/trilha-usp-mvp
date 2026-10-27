from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import NotaForm, ResumoForm
from .models import AvaliacaoDificuldade, Disciplina, Resumo
from .regras import classe_dificuldade, pode_contribuir


def _base_queryset():
    return Disciplina.objects.filter(ativa=True).annotate(
        media=Avg("avaliacoes__nota"), n_aval=Count("avaliacoes", distinct=True))


def lista(request, codigo=None):
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
        resumos = selecionada.resumos.filter(oculto=False).select_related("autor", "verificado_por")
        pode, motivo = pode_contribuir(request.user, selecionada)
        minha = None
        if request.user.is_authenticated:
            minha = AvaliacaoDificuldade.objects.filter(disciplina=selecionada, usuario=request.user).first()
        ctx.update({
            "media": round(media, 1) if media is not None else None,
            "largura": round(media / 5 * 100) if media is not None else 0,
            "classe": classe_dificuldade(media),
            "resumos": resumos,
            "ler_corpo": request.user.is_authenticated or settings.RESUMOS_PUBLICOS,
            "pode": pode, "motivo": motivo,
            "form_resumo": ResumoForm(),
            "minha": minha,
            "restantes": (settings.MAX_ATUALIZACOES_NOTA - minha.atualizacoes) if minha else None,
        })
    return render(request, "disciplinas/lista.html", ctx)


@login_required
@require_POST
def publicar(request, codigo):
    disciplina = get_object_or_404(Disciplina, codigo=codigo, ativa=True)
    pode, motivo = pode_contribuir(request.user, disciplina)
    if not pode:
        messages.error(request, motivo)
        return redirect("disciplinas:detalhe", codigo=codigo)
    form = ResumoForm(request.POST)
    if form.is_valid():
        r = form.save(commit=False)
        r.disciplina, r.autor = disciplina, request.user
        r.save()
        messages.success(request, "Publicado! A moderação pode atribuir o selo de verificado depois.")
    else:
        erros = "; ".join(e for lst in form.errors.values() for e in lst)
        messages.error(request, f"Não foi possível publicar: {erros}")
    return redirect("disciplinas:detalhe", codigo=codigo)


@login_required
@require_POST
def avaliar(request, codigo):
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
    atual = AvaliacaoDificuldade.objects.filter(disciplina=disciplina, usuario=request.user).first()
    if atual is None:
        AvaliacaoDificuldade.objects.create(disciplina=disciplina, usuario=request.user, nota=nota)
        messages.success(request, "Avaliação registrada.")
    elif atual.nota == nota:
        messages.info(request, "Sua nota já é essa.")
    elif atual.atualizacoes >= settings.MAX_ATUALIZACOES_NOTA:
        messages.error(request, "Você já usou todas as atualizações permitidas para esta nota.")
    else:
        atual.nota, atual.atualizacoes = nota, atual.atualizacoes + 1
        atual.save()
        messages.success(request, "Avaliação atualizada.")
    return redirect("disciplinas:detalhe", codigo=codigo)


@login_required
@require_POST
def excluir_resumo(request, codigo, pk):
    resumo = get_object_or_404(Resumo, pk=pk, disciplina__codigo=codigo)
    if resumo.autor_id != request.user.id and not request.user.e_moderador:
        messages.error(request, "Você só pode excluir os seus próprios resumos.")
    else:
        resumo.delete()
        messages.success(request, "Resumo excluído.")
    return redirect("disciplinas:detalhe", codigo=codigo)
