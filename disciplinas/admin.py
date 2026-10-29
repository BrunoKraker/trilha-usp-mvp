from django.contrib import admin
from django.db.models import Count, Q

from .models import AvaliacaoDificuldade, Denuncia, Disciplina, Resumo


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "semestre_ideal", "obrigatoria", "creditos", "creditos_trabalho", "ativa")
    list_filter = ("semestre_ideal", "obrigatoria", "ativa")
    search_fields = ("codigo", "nome")


@admin.register(Resumo)
class ResumoAdmin(admin.ModelAdmin):
    """Moderação: o moderador vê só o nome de exibição (nunca o e-mail) e só pode dar selo/ocultar."""

    list_display = ("titulo", "disciplina", "tipo", "autor_nome", "criado_em", "verificado", "oculto", "n_denuncias")
    list_filter = ("verificado", "oculto", "tipo", "disciplina")
    search_fields = ("titulo", "corpo", "autor__nome_exibicao")
    actions = ["marcar_verificado", "remover_verificado", "ocultar", "reexibir"]
    campos_do_moderador = ("verificado", "oculto")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("autor", "disciplina").annotate(
            _den=Count("denuncias", filter=Q(denuncias__resolvida=False)))

    @admin.display(description="autor")
    def autor_nome(self, obj):
        return obj.autor.nome_exibicao or "(sem nome)"

    @admin.display(description="denúncias abertas", ordering="_den")
    def n_denuncias(self, obj):
        return obj._den

    def get_fields(self, request, obj=None):
        return ("disciplina", "autor_nome", "tipo", "titulo", "corpo", "criado_em", "verificado", "oculto", "verificado_por")

    def get_readonly_fields(self, request, obj=None):
        base = ("disciplina", "autor_nome", "criado_em", "verificado_por")
        if request.user.is_superuser:
            return base
        return base + ("tipo", "titulo", "corpo")  # moderador não reescreve o texto dos alunos

    def _aplicar(self, request, qs, acao, **campos):
        for obj in qs:
            for k, v in campos.items():
                setattr(obj, k, v)
            if "verificado" in campos:
                obj.verificado_por = request.user if campos["verificado"] else None
            obj.save()
            self.log_change(request, obj, acao)  # trilha de auditoria (quem fez o quê)

    @admin.action(description="Dar selo de verificado")
    def marcar_verificado(self, request, qs):
        self._aplicar(request, qs, "Selo de verificado concedido", verificado=True)

    @admin.action(description="Remover selo de verificado")
    def remover_verificado(self, request, qs):
        self._aplicar(request, qs, "Selo de verificado removido", verificado=False)

    @admin.action(description="Ocultar do site")
    def ocultar(self, request, qs):
        self._aplicar(request, qs, "Resumo ocultado", oculto=True)

    @admin.action(description="Voltar a exibir no site")
    def reexibir(self, request, qs):
        self._aplicar(request, qs, "Resumo reexibido", oculto=False)

    def save_model(self, request, obj, form, change):
        if change and "verificado" in form.changed_data:
            obj.verificado_por = request.user if obj.verificado else None
        super().save_model(request, obj, form, change)


@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    list_display = ("resumo", "motivo", "denunciante", "criado_em", "resolvida")
    list_filter = ("resolvida", "motivo")
    actions = ["marcar_resolvida"]
    fields = ("resumo", "denunciante", "motivo", "comentario", "criado_em", "resolvida")
    readonly_fields = ("resumo", "denunciante", "motivo", "comentario", "criado_em")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("autor", "resumo")

    @admin.display(description="denunciante")
    def denunciante(self, obj):
        return obj.autor.nome_exibicao or "(sem nome)"

    @admin.action(description="Marcar como resolvida")
    def marcar_resolvida(self, request, qs):
        for d in qs:
            d.resolvida = True
            d.save(update_fields=["resolvida"])
            self.log_change(request, d, "Denúncia resolvida")

    def has_add_permission(self, request):
        return False


@admin.register(AvaliacaoDificuldade)
class AvaliacaoAdmin(admin.ModelAdmin):
    list_display = ("disciplina", "nota", "atualizacoes", "atualizado_em")
    list_filter = ("disciplina",)
    fields = ("disciplina", "nota", "atualizacoes", "atualizado_em")
    readonly_fields = ("disciplina", "atualizado_em")
