from django.contrib import admin

from .models import MensagemContato


@admin.register(MensagemContato)
class MensagemContatoAdmin(admin.ModelAdmin):
    list_display = ("assunto", "nome", "email", "criado_em", "lida")
    list_filter = ("lida", "assunto")
    readonly_fields = ("nome", "email", "assunto", "mensagem", "criado_em")
