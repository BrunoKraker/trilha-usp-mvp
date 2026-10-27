from django.apps import AppConfig
from django.db.models.signals import post_migrate


def criar_grupo_moderadores(sender, **kwargs):
    """Grupo 'Moderadores': só pode ver/alterar/excluir resumos (selo, ocultar). Não mexe em usuários/catálogo."""
    from django.contrib.auth.models import Group, Permission

    grupo, _ = Group.objects.get_or_create(name="Moderadores")
    perms = Permission.objects.filter(content_type__app_label="disciplinas", content_type__model="resumo",
                                      codename__in=["view_resumo", "change_resumo", "delete_resumo"])
    if perms.count() == 3:
        grupo.permissions.set(perms)


class DisciplinasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "disciplinas"

    def ready(self):
        post_migrate.connect(criar_grupo_moderadores, sender=self)
