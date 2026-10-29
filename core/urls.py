from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.pagina("core/index.html", "home"), name="home"),
    path("modulos/", views.pagina("core/modulos.html", "modulos"), name="modulos"),
    #path("entidades/", views.pagina("core/entidades.html", "modulos"), name="entidades"),
    path("em-breve/", views.pagina("core/em_breve.html", "modulos"), name="em_breve"),
    path("sobre/", views.pagina("core/sobre.html", "sobre"), name="sobre"),
    path("documentacao/", views.pagina("core/documentacao.html", "documentacao"), name="documentacao"),
    path("contato/", views.contato, name="contato"),
    path("privacidade/", views.pagina("core/privacidade.html", "privacidade"), name="privacidade"),
    path("termos/", views.pagina("core/termos.html", "termos"), name="termos"),
    path("healthz", views.healthz, name="healthz"),
    path("robots.txt", views.robots_txt, name="robots"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap"),
]
