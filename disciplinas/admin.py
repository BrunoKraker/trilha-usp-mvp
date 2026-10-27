from django.contrib import admin
from django.utils import timezone

from .models import AvaliacaoDificuldade, Disciplina, Resumo


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "semestre_ideal", "obrigatoria", "creditos", "ativa")
    list_filter = ("semestre_ideal", "obrigatoria", "ativa")
    search_fields = ("codigo", "nome")


@admin.register(Resumo)
class ResumoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "disciplina", "tipo", "autor", "criado_em", "verificado", "oculto")
    list_filter = ("verificado", "oculto", "tipo", "disciplina")
    search_fields = ("titulo", "corpo", "autor__email")
    readonly_fields = ("autor", "disciplina", "criado_em", "verificado_por")
    actions = ["marcar_verificado", "remover_verificado", "ocultar", "reexibir"]

    @admin.action(description="Dar selo de verificado")
    def marcar_verificado(self, request, qs):
        qs.update(verificado=True, verificado_por=request.user)

    @admin.action(description="Remover selo de verificado")
    def remover_verificado(self, request, qs):
        qs.update(verificado=False, verificado_por=None)

    @admin.action(description="Ocultar do site")
    def ocultar(self, request, qs):
        qs.update(oculto=True)

    @admin.action(description="Voltar a exibir no site")
    def reexibir(self, request, qs):
        qs.update(oculto=False)

    def save_model(self, request, obj, form, change):
        if change and "verificado" in form.changed_data:
            obj.verificado_por = request.user if obj.verificado else None
        super().save_model(request, obj, form, change)


@admin.register(AvaliacaoDificuldade)
class AvaliacaoAdmin(admin.ModelAdmin):
    list_display = ("disciplina", "usuario", "nota", "atualizacoes", "atualizado_em")
    list_filter = ("disciplina",)
