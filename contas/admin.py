from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


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
