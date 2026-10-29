import re
from datetime import timedelta

from django.contrib.sessions.models import Session
from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from contas import limites
from contas.models import EventoLimite, TokenLogin, Usuario


class BackendQuebrado(BaseEmailBackend):
    def send_messages(self, msgs):
        raise ConnectionError("provedor fora do ar")


def pedir(client, email):
    return client.post(reverse("contas:entrar"), {"email": email})


class LimitesDeLoginTest(TestCase):
    @override_settings(LOGIN_IP_MAX_PER_HOUR=3)
    def test_limite_por_ip_com_enderecos_diferentes(self):
        codigos = [pedir(self.client, f"a{i}@usp.br").status_code for i in range(5)]
        self.assertEqual(codigos, [200, 200, 200, 429, 429])
        self.assertEqual(len(mail.outbox), 3)

    @override_settings(LOGIN_IP_MAX_PER_HOUR=2)
    def test_ips_diferentes_nao_se_misturam(self):
        for i in range(2):
            self.client.post(reverse("contas:entrar"), {"email": f"a{i}@usp.br"}, REMOTE_ADDR="10.0.0.1")
        r = self.client.post(reverse("contas:entrar"), {"email": "x@usp.br"}, REMOTE_ADDR="10.0.0.2")
        self.assertEqual(r.status_code, 200)

    @override_settings(LOGIN_GLOBAL_MAX_PER_DAY=2, LOGIN_IP_MAX_PER_HOUR=100)
    def test_teto_global_diario(self):
        codigos = [self.client.post(reverse("contas:entrar"), {"email": f"g{i}@usp.br"},
                                    REMOTE_ADDR=f"10.0.1.{i}").status_code for i in range(4)]
        self.assertEqual(codigos, [200, 200, 429, 429])
        self.assertEqual(len(mail.outbox), 2)

    def test_mensagem_de_limite_nao_revela_existencia_de_conta(self):
        with override_settings(LOGIN_IP_MAX_PER_HOUR=1):
            pedir(self.client, "a@usp.br")
            r = pedir(self.client, "b@usp.br")
        self.assertContains(r, "Muitos pedidos", status_code=429)

    def test_status_de_envio_registrado(self):
        pedir(self.client, "ok@usp.br")
        self.assertEqual(TokenLogin.objects.get(email="ok@usp.br").status_envio, "enviado")

    @override_settings(EMAIL_BACKEND="contas.tests.test_limites.BackendQuebrado")
    def test_falha_de_envio_fica_registrada_e_usuario_ve_resposta_generica(self):
        r = pedir(self.client, "falha@usp.br")
        self.assertContains(r, "Confira seu e-mail")
        self.assertEqual(TokenLogin.objects.get(email="falha@usp.br").status_envio, "falhou")


class ContasPrivilegiadasTest(TestCase):
    def _link(self, email):
        pedir(self.client, email)
        return re.search(r"http\S+/entrar/verificar/\S+/", mail.outbox[-1].body).group(0)

    def test_staff_nao_entra_so_com_link(self):
        Usuario.objects.create_user("mod@usp.br", is_staff=True, nome_exibicao="M", ingresso_ano=2020, ingresso_semestre=1)
        link = self._link("mod@usp.br")
        r = self.client.post(link)
        self.assertRedirects(r, reverse("core:home"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_superusuario_nao_entra_so_com_link(self):
        Usuario.objects.create_superuser("root@usp.br", "SenhaMuitoForte-123456")
        link = self._link("root@usp.br")
        self.client.post(link)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_staff_entra_no_admin_com_senha(self):
        Usuario.objects.create_superuser("root@usp.br", "SenhaMuitoForte-123456")
        ok = self.client.post(reverse("admin:login"), {"username": "root@usp.br", "password": "SenhaMuitoForte-123456",
                                                       "next": "/admin/"})
        self.assertEqual(ok.status_code, 302)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    @override_settings(ADMIN_LOGIN_MAX_FALHAS_USUARIO=3, ADMIN_LOGIN_MAX_FALHAS_IP=100)
    def test_admin_bloqueia_apos_falhas_por_usuario(self):
        Usuario.objects.create_superuser("root@usp.br", "SenhaMuitoForte-123456")
        for _ in range(3):
            r = self.client.post(reverse("admin:login"), {"username": "root@usp.br", "password": "errada", "next": "/admin/"})
            self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse("admin:login"), {"username": "root@usp.br", "password": "SenhaMuitoForte-123456",
                                                      "next": "/admin/"})
        self.assertEqual(r.status_code, 429)  # bloqueado mesmo com a senha certa

    @override_settings(ADMIN_LOGIN_MAX_FALHAS_IP=3, ADMIN_LOGIN_MAX_FALHAS_USUARIO=100)
    def test_admin_bloqueia_apos_falhas_por_ip(self):
        for i in range(3):
            self.client.post(reverse("admin:login"), {"username": f"x{i}@usp.br", "password": "errada", "next": "/admin/"})
        r = self.client.post(reverse("admin:login"), {"username": "outro@usp.br", "password": "errada", "next": "/admin/"})
        self.assertEqual(r.status_code, 429)

    def test_login_normal_do_admin_nao_conta_como_falha(self):
        Usuario.objects.create_superuser("root@usp.br", "SenhaMuitoForte-123456")
        self.client.post(reverse("admin:login"), {"username": "root@usp.br", "password": "SenhaMuitoForte-123456", "next": "/admin/"})
        self.assertEqual(EventoLimite.objects.filter(tipo__startswith="admin").count(), 0)


class PerfilTest(TestCase):
    def setUp(self):
        self.u = Usuario.objects.create_user("a@usp.br", nome_exibicao="Ana A.", ingresso_ano=2022, ingresso_semestre=1)
        self.client.force_login(self.u)

    def test_ingresso_nao_pode_ser_alterado_pelo_aluno(self):
        self.client.post(reverse("contas:perfil"), {"nome_exibicao": "Ana B.", "ingresso_ano": 2000, "ingresso_semestre": 2})
        self.u.refresh_from_db()
        self.assertEqual((self.u.nome_exibicao, self.u.ingresso_ano, self.u.ingresso_semestre), ("Ana B.", 2022, 1))

    def test_primeiro_preenchimento_permitido(self):
        novo = Usuario.objects.create_user("n@usp.br")
        self.client.force_login(novo)
        self.client.post(reverse("contas:perfil"), {"nome_exibicao": "Novo N.", "ingresso_ano": 2025, "ingresso_semestre": 2})
        novo.refresh_from_db()
        self.assertEqual((novo.ingresso_ano, novo.ingresso_semestre), (2025, 2))

    def test_exportar_dados_so_do_proprio_usuario(self):
        outro = Usuario.objects.create_user("o@usp.br", nome_exibicao="Outro O.", ingresso_ano=2020, ingresso_semestre=1)
        from disciplinas.models import Disciplina, Resumo
        d = Disciplina.objects.create(codigo="X1", nome="X", semestre_ideal=1)
        Resumo.objects.create(disciplina=d, autor=self.u, titulo="Meu resumo", corpo="x" * 40)
        Resumo.objects.create(disciplina=d, autor=outro, titulo="Do outro", corpo="y" * 40)
        r = self.client.get(reverse("contas:exportar"))
        self.assertIn("attachment", r["Content-Disposition"])
        txt = r.content.decode()
        self.assertIn("Meu resumo", txt)
        self.assertNotIn("Do outro", txt)
        self.assertNotIn("o@usp.br", txt)

    def test_exportar_exige_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("contas:exportar")).status_code, 302)

    def test_excluir_conta_exige_confirmacao(self):
        self.client.post(reverse("contas:excluir"), {"confirmar": "sim"})
        self.assertTrue(Usuario.objects.filter(pk=self.u.pk).exists())

    def test_excluir_conta_remove_tudo_e_desloga(self):
        from disciplinas.models import AvaliacaoDificuldade, Disciplina, Resumo
        d = Disciplina.objects.create(codigo="X1", nome="X", semestre_ideal=1)
        Resumo.objects.create(disciplina=d, autor=self.u, titulo="R", corpo="x" * 40)
        AvaliacaoDificuldade.objects.create(disciplina=d, usuario=self.u, nota=3)
        self.client.post(reverse("contas:excluir"), {"confirmar": "EXCLUIR"})
        self.assertFalse(Usuario.objects.filter(pk=self.u.pk).exists())
        self.assertEqual(Resumo.objects.count() + AvaliacaoDificuldade.objects.count(), 0)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_excluir_conta_so_por_post_e_staff_nao_exclui(self):
        self.assertEqual(self.client.get(reverse("contas:excluir")).status_code, 405)
        staff = Usuario.objects.create_user("s@usp.br", is_staff=True)
        self.client.force_login(staff)
        self.client.post(reverse("contas:excluir"), {"confirmar": "EXCLUIR"})
        self.assertTrue(Usuario.objects.filter(pk=staff.pk).exists())


class IpETetoTest(TestCase):
    def _req(self, xff=None, remote="9.9.9.9"):
        extra = {"HTTP_X_FORWARDED_FOR": xff} if xff else {}
        return RequestFactory().get("/", REMOTE_ADDR=remote, **extra)

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_ip_ignora_entradas_forjadas_a_esquerda(self):
        self.assertEqual(limites.ip_do_cliente(self._req("6.6.6.6, 1.2.3.4")), "1.2.3.4")

    @override_settings(TRUSTED_PROXY_HOPS=2)
    def test_ip_com_dois_proxies(self):
        self.assertEqual(limites.ip_do_cliente(self._req("6.6.6.6, 1.2.3.4, 10.0.0.1")), "1.2.3.4")

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_sem_xff_usa_remote_addr(self):
        self.assertEqual(limites.ip_do_cliente(self._req()), "9.9.9.9")

    def test_hash_nao_expoe_o_valor(self):
        h = limites.hash_chave("1.2.3.4")
        self.assertNotIn("1.2.3.4", h)
        self.assertEqual(h, limites.hash_chave(" 1.2.3.4 "))

    def test_limpeza_remove_somente_vencidos(self):
        from core.models import MensagemContato
        velho = timezone.now() - timedelta(days=400)
        TokenLogin.objects.create(email="v@usp.br", token_hash="a" * 64, criado_em=velho)
        TokenLogin.objects.create(email="n@usp.br", token_hash="b" * 64)
        EventoLimite.objects.create(tipo="t", chave="k", criado_em=velho)
        EventoLimite.objects.create(tipo="t", chave="k")
        MensagemContato.objects.create(nome="A", email="a@x.com", assunto="Outro", mensagem="m", criado_em=velho)
        MensagemContato.objects.create(nome="B", email="b@x.com", assunto="Outro", mensagem="m")
        s = self.client.session; s["x"] = 1; s.save()
        Session.objects.filter(pk=s.session_key).update(expire_date=velho)
        limites.limpar_antigos()
        self.assertEqual(list(TokenLogin.objects.values_list("email", flat=True)), ["n@usp.br"])
        self.assertEqual(EventoLimite.objects.count(), 1)
        self.assertEqual(MensagemContato.objects.count(), 1)
        self.assertEqual(Session.objects.count(), 0)


class BackendHttpsTest(TestCase):
    @override_settings(EMAIL_BACKEND="contas.email_backends.BrevoEmailBackend", BREVO_API_KEY="k",
                       BREVO_API_URL="http://evil.example/v3", DEFAULT_FROM_EMAIL="T <t@x.com>")
    def test_recusa_url_http_externa(self):
        from django.core.mail import send_mail
        with self.assertRaises(RuntimeError):
            send_mail("a", "b", None, ["x@usp.br"])
