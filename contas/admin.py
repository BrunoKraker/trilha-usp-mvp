from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import TokenLogin, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("email", "nome_exibicao", "ingresso_ano", "ingresso_semestre", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active")
    search_fields = ("email", "nome_exibicao")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Perfil", {"fields": ("nome_exibicao", "ingresso_ano", "ingresso_semestre")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)


@admin.register(TokenLogin)
class TokenLoginAdmin(admin.ModelAdmin):
    """Somente leitura: serve para ver se os e-mails de login estão sendo enviados."""
    list_display = ("criado_em", "email_mascarado", "status_envio", "usado_em")
    list_filter = ("status_envio",)
    date_hierarchy = "criado_em"
    fields = ("criado_em", "email_mascarado", "status_envio", "usado_em")
    readonly_fields = fields

    @admin.display(description="e-mail")
    def email_mascarado(self, obj):
        usuario, _, dominio = obj.email.partition("@")
        return f"{usuario[:2]}***@{dominio}"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
