from django.contrib import admin
from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("entrar/", include("contas.urls")),
    path("disciplinas/", include("disciplinas.urls")),
    path("", include("core.urls")),
]
