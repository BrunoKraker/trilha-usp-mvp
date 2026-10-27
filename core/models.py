from django.db import models
from django.utils import timezone


class MensagemContato(models.Model):
    ASSUNTOS = ["Sugestão de conteúdo", "Reportar problema", "Proposta de parceria", "Outro"]
    nome = models.CharField(max_length=100)
    email = models.EmailField()
    assunto = models.CharField(max_length=40)
    mensagem = models.TextField(max_length=3000)
    criado_em = models.DateTimeField(default=timezone.now)
    lida = models.BooleanField(default=False)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name_plural = "mensagens de contato"

    def __str__(self):
        return f"{self.assunto} — {self.nome}"
