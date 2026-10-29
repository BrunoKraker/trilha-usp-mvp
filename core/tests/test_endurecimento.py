import re
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import MensagemContato
from disciplinas.models import Disciplina

PAGINAS = ["core:home", "core:modulos", "core:sobre", "core:documentacao", "core:contato",
           "core:privacidade", "core:termos", "core:em_breve", "disciplinas:lista", "contas:entrar"]


class TerceirosECspTest(TestCase):
    def test_nenhuma_pagina_chama_google_ou_cdn(self):
        for nome in PAGINAS:
            html = self.client.get(reverse(nome)).content.decode()
            for proibido in ("googleapis", "gstatic", "jsdelivr", "cdnjs", "unpkg"):
                self.assertNotIn(proibido, html, f"{nome} referencia {proibido}")

    def test_sem_script_inline_nem_handlers_inline(self):
        for nome in PAGINAS:
            html = self.client.get(reverse(nome)).content.decode()
            self.assertEqual(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", html), [], nome)
            self.assertEqual(re.findall(r"\son(click|submit|load|error|change)\s*=", html, re.I), [], nome)

    def test_pdfjs_e_fontes_locais_existem(self):
        from django.contrib.staticfiles import finders
        for f in ("vendor/pdfjs/build/pdf.min.mjs", "vendor/pdfjs/build/pdf.worker.min.mjs",
                  "fonts/inter-latin-400-normal.woff2", "assets/fonts.css", "assets/app.js"):
            self.assertTrue(finders.find(f), f)
        with open(finders.find("assets/pdf-preview.js"), encoding="utf-8") as fh:
            self.assertNotIn("jsdelivr", fh.read().lower())

    def test_csp_e_permissions_policy(self):
        r = self.client.get(reverse("core:home"))
        csp = r["Content-Security-Policy"]
        for parte in ("default-src 'self'", "script-src 'self'", "frame-ancestors 'none'", "object-src 'none'"):
            self.assertIn(parte, csp)
        self.assertNotIn("unsafe-inline", csp.split("script-src")[1].split(";")[0])
        self.assertIn("camera=()", r["Permissions-Policy"])

    def test_admin_fica_fora_da_csp(self):
        r = self.client.get(reverse("admin:login"))
        self.assertNotIn("Content-Security-Policy", r)

    def test_gzip_no_html(self):
        r = self.client.get(reverse("core:home"), HTTP_ACCEPT_ENCODING="gzip")
        self.assertEqual(r.get("Content-Encoding"), "gzip")


class PaginasLegaisETecnicasTest(TestCase):
    def test_privacidade_e_termos(self):
        r = self.client.get(reverse("core:privacidade"))
        for t in ("Brevo", "Render", "Neon", "12 meses", "7 dias", "cookies técnicos", "formulário de contato"):
            self.assertContains(r, t)
        self.assertContains(self.client.get(reverse("core:termos")), "Moderação")

    def test_rodape_linka_privacidade_e_termos_em_todas_as_paginas(self):
        for nome in PAGINAS:
            html = self.client.get(reverse(nome)).content.decode()
            self.assertIn(reverse("core:privacidade"), html, nome)
            self.assertIn(reverse("core:termos"), html, nome)

    def test_rodape_nao_afirma_conformidade_juridica(self):
        self.assertNotIn("conforme a LGPD", self.client.get(reverse("core:home")).content.decode())

    def test_healthz_ok_e_falha(self):
        self.assertEqual(self.client.get("/healthz").json(), {"status": "ok"})
        with mock.patch("core.views.connection.cursor", side_effect=Exception("banco fora")):
            self.assertEqual(self.client.get("/healthz").status_code, 503)

    def test_robots_e_sitemap(self):
        Disciplina.objects.create(codigo="ACH1", nome="X", semestre_ideal=1)
        Disciplina.objects.create(codigo="ACH2", nome="Y", semestre_ideal=1, ativa=False)
        robots = self.client.get("/robots.txt").content.decode()
        self.assertIn("Disallow: /entrar/", robots)
        self.assertIn("/sitemap.xml", robots)
        self.assertNotIn("admin", robots)
        site = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("/disciplinas/ACH1/", site)
        self.assertNotIn("ACH2", site)

    def test_noindex_nas_telas_de_login_e_canonical_nas_publicas(self):
        self.assertContains(self.client.get(reverse("contas:entrar")), 'content="noindex, nofollow"')
        self.assertContains(self.client.get(reverse("core:home")), 'rel="canonical"')

    def test_skip_link_e_main_com_id(self):
        html = self.client.get(reverse("core:home")).content.decode()
        self.assertIn('class="skip-link"', html)
        self.assertIn('id="conteudo"', html)

    def test_documentacao_com_rotulo_correto_do_canvas(self):
        html = self.client.get(reverse("core:documentacao")).content.decode()
        self.assertNotIn("Escopo completo", html)
        self.assertIn("Project Model Canvas", html)


class ContatoLimitesTest(TestCase):
    dados = {"nome": "Ana", "email": "ana@usp.br", "assunto": "Outro", "mensagem": "Olá!", "website": ""}

    @override_settings(CONTATO_MAX_POR_HORA_IP=3, CONTATO_MAX_POR_DIA_EMAIL=100)
    def test_limite_por_ip(self):
        codigos = []
        for i in range(5):
            d = dict(self.dados, email=f"a{i}@usp.br")
            codigos.append(self.client.post(reverse("core:contato"), d).status_code)
        self.assertEqual(codigos, [302, 302, 302, 429, 429])
        self.assertEqual(MensagemContato.objects.count(), 3)

    @override_settings(CONTATO_MAX_POR_HORA_IP=100, CONTATO_MAX_POR_DIA_EMAIL=2)
    def test_limite_por_email(self):
        codigos = [self.client.post(reverse("core:contato"), self.dados).status_code for _ in range(4)]
        self.assertEqual(codigos, [302, 302, 429, 429])

    @override_settings(CONTATO_NOTIFICAR="equipe@exemplo.com")
    def test_notifica_a_equipe(self):
        self.client.post(reverse("core:contato"), self.dados)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["equipe@exemplo.com"])
        self.assertIn("Nova mensagem de contato", mail.outbox[0].subject)

    def test_sem_notificacao_por_padrao(self):
        self.client.post(reverse("core:contato"), self.dados)
        self.assertEqual(len(mail.outbox), 0)
