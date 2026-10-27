from django.urls import path

from . import views

app_name = "disciplinas"
urlpatterns = [
    path("", views.lista, name="lista"),
    path("<str:codigo>/", views.lista, name="detalhe"),
    path("<str:codigo>/resumos/novo/", views.publicar, name="publicar"),
    path("<str:codigo>/avaliar/", views.avaliar, name="avaliar"),
    path("<str:codigo>/resumos/<int:pk>/excluir/", views.excluir_resumo, name="excluir_resumo"),
]
