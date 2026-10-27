from django.test import TestCase
from django.urls import reverse

from core.models import MensagemContato


class PaginasTest(TestCase):
    def test_paginas_publicas_abrem(self):
        for nome in ["core:home", "core:modulos", "core:entidades", "core:em_breve", "core:sobre",
                     "core:documentacao", "core:contato", "disciplinas:lista", "contas:entrar"]:
            r = self.client.get(reverse(nome))
            self.assertEqual(r.status_code, 200, nome)

    def test_sem_mencao_a_ej_nos_textos_do_trilha(self):
        for nome in ["core:sobre", "core:contato", "core:entidades"]:
            html = self.client.get(reverse(nome)).content.decode()
            self.assertNotIn("apoio operacional da empresa júnior", html)
            self.assertNotIn("e-mail institucional da EJ", html)
            self.assertNotIn("mantém o Trilha USP", html)

    def test_contato_salva_mensagem(self):
        r = self.client.post(reverse("core:contato"), {
            "nome": "Ana", "email": "ana@usp.br", "assunto": "Outro", "mensagem": "Olá, equipe!", "website": ""})
        self.assertRedirects(r, reverse("core:contato"))
        self.assertEqual(MensagemContato.objects.count(), 1)

    def test_contato_honeypot_bloqueia_robo(self):
        self.client.post(reverse("core:contato"), {
            "nome": "Bot", "email": "b@x.com", "assunto": "Outro", "mensagem": "spam", "website": "http://spam"})
        self.assertEqual(MensagemContato.objects.count(), 0)

    def test_contato_assunto_invalido(self):
        self.client.post(reverse("core:contato"), {
            "nome": "A", "email": "a@usp.br", "assunto": "<script>", "mensagem": "x"})
        self.assertEqual(MensagemContato.objects.count(), 0)

    def test_estaticos_e_pdfs_servidos(self):
        from django.contrib.staticfiles import finders
        for f in ["assets/styles.css", "assets/app.css", "docs/TAP_Trilha_USP.pdf", "img/equipe/Bruno.jpg"]:
            self.assertTrue(finders.find(f), f)
