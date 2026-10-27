from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Disciplina(models.Model):
    codigo = models.CharField("código", max_length=20, unique=True)
    nome = models.CharField(max_length=150)
    ementa = models.TextField(blank=True)
    semestre_ideal = models.PositiveSmallIntegerField(
        "semestre ideal", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Semestre da grade em que a disciplina é oferecida. Vazio = optativa/sem semestre fixo.")
    obrigatoria = models.BooleanField("obrigatória", default=True)
    creditos = models.PositiveSmallIntegerField("créditos", default=4)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["semestre_ideal", "nome"]

    def __str__(self):
        return f"{self.codigo} — {self.nome}"


class Resumo(models.Model):
    class Tipo(models.TextChoices):
        RESUMO = "resumo", "Resumo"
        DICA = "dica", "Dica"

    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name="resumos")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resumos")
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.RESUMO)
    titulo = models.CharField("título", max_length=120)
    corpo = models.TextField(max_length=8000)
    criado_em = models.DateTimeField(default=timezone.now)
    verificado = models.BooleanField("selo de verificado", default=False)
    verificado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                       on_delete=models.SET_NULL, related_name="+")
    oculto = models.BooleanField("oculto pela moderação", default=False)

    class Meta:
        ordering = ["-verificado", "-criado_em"]

    def __str__(self):
        return f"{self.titulo} ({self.disciplina.codigo})"


class AvaliacaoDificuldade(models.Model):
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name="avaliacoes")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="avaliacoes")
    nota = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    atualizacoes = models.PositiveSmallIntegerField(default=0)
    criado_em = models.DateTimeField(default=timezone.now)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["disciplina", "usuario"], name="uma_avaliacao_por_aluno")]
