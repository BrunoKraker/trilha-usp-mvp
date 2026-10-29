from django.apps import AppConfig
from django.db.models.signals import post_migrate


def criar_grupo_moderadores(sender, **kwargs):
    """Grupo 'Moderadores': resumos (selo, ocultar, excluir) e denúncias. Não mexe em usuários/catálogo."""
    from django.contrib.auth.models import Group, Permission

    grupo, _ = Group.objects.get_or_create(name="Moderadores")
    nomes = ["view_resumo", "change_resumo", "delete_resumo", "view_denuncia", "change_denuncia"]
    perms = Permission.objects.filter(content_type__app_label="disciplinas", codename__in=nomes)
    if perms.count() == len(nomes):
        grupo.permissions.set(perms)


class DisciplinasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "disciplinas"

    def ready(self):
        post_migrate.connect(criar_grupo_moderadores, sender=self)
