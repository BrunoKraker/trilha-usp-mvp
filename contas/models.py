import hashlib
from datetime import date

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("E-mail obrigatório.")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Dados mínimos (LGPD): e-mail, nome de exibição e semestre de ingresso."""

    email = models.EmailField(unique=True)
    nome_exibicao = models.CharField("nome de exibição", max_length=40, blank=True,
                                     help_text="Ex.: Ana T. Aparece nos resumos que você publicar.")
    ingresso_ano = models.PositiveSmallIntegerField(
        "ano de ingresso", null=True, blank=True,
        validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    ingresso_semestre = models.PositiveSmallIntegerField(
        "semestre de ingresso", null=True, blank=True, choices=[(1, "1º semestre"), (2, "2º semestre")])
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField("moderador/admin (acessa /admin/)", default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UsuarioManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    def __str__(self):
        return self.email

    @property
    def perfil_completo(self):
        return bool(self.nome_exibicao and self.ingresso_ano and self.ingresso_semestre)

    @property
    def e_moderador(self):
        return self.is_active and self.is_staff

    def semestre_no_curso(self, hoje: date | None = None):
        """Qual semestre do curso o aluno está cursando agora (1 = primeiro). None se perfil incompleto."""
        if not (self.ingresso_ano and self.ingresso_semestre):
            return None
        hoje = hoje or timezone.localdate()
        sem_atual = 1 if hoje.month <= 7 else 2
        return (hoje.year - self.ingresso_ano) * 2 + (sem_atual - self.ingresso_semestre) + 1


class TokenLogin(models.Model):
    """Link de login de uso único. Guardamos só o hash do token, nunca o token."""

    email = models.EmailField()
    token_hash = models.CharField(max_length=64, unique=True)
    criado_em = models.DateTimeField(default=timezone.now, db_index=True)
    usado_em = models.DateTimeField(null=True, blank=True)
    status_envio = models.CharField(max_length=10, default="pendente",
                                    choices=[("pendente", "pendente"), ("enviado", "enviado"), ("falhou", "falhou")])

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()


class EventoLimite(models.Model):
    """Registro de eventos (pedido de login, falha de admin etc.) para aplicar limites de taxa."""

    tipo = models.CharField(max_length=30)
    chave = models.CharField(max_length=64)
    criado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["tipo", "chave", "criado_em"])]
