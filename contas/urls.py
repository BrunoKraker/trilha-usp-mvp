from django.urls import path

from . import views

app_name = "contas"
urlpatterns = [
    path("", views.entrar, name="entrar"),
    path("verificar/<str:token>/", views.verificar, name="verificar"),
    path("perfil/", views.perfil, name="perfil"),
    path("perfil/exportar/", views.exportar_dados, name="exportar"),
    path("perfil/excluir/", views.excluir_conta, name="excluir"),
    path("sair/", views.sair, name="sair"),
]
