import re
from datetime import timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from contas.models import TokenLogin, Usuario


def pedir_link(client, email):
    client.post(reverse("contas:entrar"), {"email": email})
    if not mail.outbox:
        return None
    return re.search(r"http\S+/entrar/verificar/\S+/", mail.outbox[-1].body).group(0)


class LoginTest(TestCase):
    def test_dominio_nao_usp_e_recusado_sem_enviar_email(self):
        r = self.client.post(reverse("contas:entrar"), {"email": "x@gmail.com"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "e-mail institucional")
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(TokenLogin.objects.count(), 0)

    def test_subdominio_enganoso_recusado(self):
        self.client.post(reverse("contas:entrar"), {"email": "x@usp.br.evil.com"})
        self.client.post(reverse("contas:entrar"), {"email": "x@evilusp.br"})
        self.assertEqual(len(mail.outbox), 0)

    def test_fluxo_completo_cria_usuario_e_loga(self):
        link = pedir_link(self.client, "Aluno@USP.br")
        self.assertIsNotNone(link)
        # GET não consome o token (scanners de e-mail fazem GET)
        self.assertEqual(self.client.get(link).status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        r = self.client.post(link)
        self.assertRedirects(r, reverse("contas:perfil"))
        self.assertTrue(Usuario.objects.filter(email="aluno@usp.br").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_token_e_de_uso_unico(self):
        link = pedir_link(self.client, "a@usp.br")
        self.client.post(link)
        self.client.post(reverse("contas:sair"))
        r = self.client.post(link)
        self.assertContains(r, "inválido ou expirado")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_token_expirado(self):
        link = pedir_link(self.client, "a@usp.br")
        TokenLogin.objects.update(criado_em=timezone.now() - timedelta(minutes=16))
        r = self.client.post(link)
        self.assertContains(r, "inválido ou expirado")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_token_aleatorio_invalido(self):
        r = self.client.post(reverse("contas:verificar", args=["naoexiste"]))
        self.assertContains(r, "inválido ou expirado")

    def test_token_nao_fica_em_texto_puro_no_banco(self):
        link = pedir_link(self.client, "a@usp.br")
        token = link.rstrip("/").rsplit("/", 1)[-1]
        self.assertFalse(TokenLogin.objects.filter(token_hash=token).exists())

    @override_settings(LOGIN_TOKEN_MAX_PER_HOUR=2)
    def test_limite_de_links_por_hora(self):
        for _ in range(4):
            self.client.post(reverse("contas:entrar"), {"email": "a@usp.br"})
        self.assertEqual(len(mail.outbox), 2)

    def test_open_redirect_bloqueado(self):
        link = pedir_link(self.client, "b@usp.br")
        Usuario.objects.create_user("b@usp.br", nome_exibicao="B", ingresso_ano=2024, ingresso_semestre=1)
        r = self.client.post(link, {"next": "https://evil.com/"})
        self.assertRedirects(r, reverse("core:home"))

    def test_perfil_exige_login_e_valida(self):
        self.assertEqual(self.client.get(reverse("contas:perfil")).status_code, 302)
        u = Usuario.objects.create_user("c@usp.br")
        self.client.force_login(u)
        r = self.client.post(reverse("contas:perfil"), {"nome_exibicao": "C", "ingresso_ano": 1990})
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse("contas:perfil"), {"nome_exibicao": "Caio C.", "ingresso_ano": 2024, "ingresso_semestre": 1})
        self.assertEqual(r.status_code, 302)
        u.refresh_from_db()
        self.assertTrue(u.perfil_completo)

    def test_logout_so_por_post(self):
        u = Usuario.objects.create_user("d@usp.br")
        self.client.force_login(u)
        self.assertEqual(self.client.get(reverse("contas:sair")).status_code, 405)
        self.client.post(reverse("contas:sair"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logs_nao_vazam_link(self):
        with self.assertNoLogs("contas.views", level="INFO"):
            pedir_link(self.client, "e@usp.br")


class GerarLinkTest(TestCase):
    def test_comando_gera_link_valido(self):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command("gerar_link", "Aluno@usp.br", "--base-url", "https://site.exemplo", stdout=out)
        link = out.getvalue().splitlines()[0]
        self.assertTrue(link.startswith("https://site.exemplo/entrar/verificar/"))
        self.client.post(link.replace("https://site.exemplo", ""))
        self.assertIn("_auth_user_id", self.client.session)

    def test_comando_recusa_dominio_externo(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command("gerar_link", "x@gmail.com", "--base-url", "https://site.exemplo")
