from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Trilha USP — administração"
admin.site.site_title = "Trilha USP"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("entrar/", include("contas.urls")),
    path("disciplinas/", include("disciplinas.urls")),
    path("", include("core.urls")),
]
