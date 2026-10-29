import threading

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.db import connection
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from contas.models import Usuario
from disciplinas.models import AvaliacaoDificuldade, Denuncia, Disciplina, Resumo


def aluno(email, ano=2020, sem=1, **kw):
    return Usuario.objects.create_user(email, nome_exibicao=email[:3].upper() + ".", ingresso_ano=ano,
                                       ingresso_semestre=sem, **kw)


class Base(TestCase):
    def setUp(self):
        self.d = Disciplina.objects.create(codigo="ACH2001", nome="Intro", semestre_ideal=1)
        self.a = aluno("ana@usp.br")
        self.b = aluno("bia@usp.br")
        self.client.force_login(self.a)


class LimitesDePublicacaoTest(Base):
    @override_settings(PUBLICAR_MAX_POR_HORA=2)
    def test_limite_por_hora(self):
        url = reverse("disciplinas:publicar", args=["ACH2001"])
        for i in range(4):
            self.client.post(url, {"tipo": "dica", "titulo": f"Dica {i}", "corpo": "texto " * 10})
        self.assertEqual(Resumo.objects.count(), 2)

    @override_settings(PUBLICAR_MAX_POR_HORA=100, PUBLICAR_MAX_POR_DIA=3)
    def test_limite_por_dia(self):
        url = reverse("disciplinas:publicar", args=["ACH2001"])
        for i in range(6):
            self.client.post(url, {"tipo": "dica", "titulo": f"Dica {i}", "corpo": "texto " * 10})
        self.assertEqual(Resumo.objects.count(), 3)

    def test_limite_e_por_usuario(self):
        url = reverse("disciplinas:publicar", args=["ACH2001"])
        with override_settings(PUBLICAR_MAX_POR_HORA=1):
            self.client.post(url, {"tipo": "dica", "titulo": "Da Ana", "corpo": "texto " * 10})
            self.client.force_login(self.b)
            self.client.post(url, {"tipo": "dica", "titulo": "Da Bia", "corpo": "texto " * 10})
        self.assertEqual(Resumo.objects.count(), 2)


class UrlsETextoTest(Base):
    def test_codigo_em_minusculas_redireciona_para_maiusculas(self):
        r = self.client.get("/disciplinas/ach2001/")
        self.assertRedirects(r, "/disciplinas/ACH2001/", fetch_redirect_response=False)

    def test_post_com_codigo_minusculo_funciona(self):
        self.client.post("/disciplinas/ach2001/avaliar/", {"nota": 4})
        self.assertEqual(AvaliacaoDificuldade.objects.count(), 1)

    def test_paginacao_de_resumos(self):
        for i in range(25):
            Resumo.objects.create(disciplina=self.d, autor=self.a, titulo=f"Resumo numero {i:02d}", corpo="x" * 40)
        p1 = self.client.get("/disciplinas/ACH2001/").content.decode()
        p3 = self.client.get("/disciplinas/ACH2001/?pagina=3").content.decode()
        self.assertEqual(p1.count('class="material-card"'), 10)
        self.assertEqual(p3.count('class="material-card"'), 5)
        self.assertIn("Página 1 de 3", p1)
        self.assertEqual(self.client.get("/disciplinas/ACH2001/?pagina=abc").status_code, 200)
        self.assertEqual(self.client.get("/disciplinas/ACH2001/?pagina=999").status_code, 200)


class DenunciaTest(Base):
    def setUp(self):
        super().setUp()
        self.r = Resumo.objects.create(disciplina=self.d, autor=self.b, titulo="Da Bia", corpo="x" * 40)

    def url(self, pk=None):
        return reverse("disciplinas:denunciar", args=["ACH2001", pk or self.r.pk])

    def test_denuncia_valida(self):
        self.client.post(self.url(), {"motivo": "spam", "comentario": "propaganda"})
        d = Denuncia.objects.get()
        self.assertEqual((d.autor, d.resumo, d.motivo), (self.a, self.r, "spam"))

    def test_nao_duplica_e_nao_denuncia_o_proprio(self):
        self.client.post(self.url(), {"motivo": "spam"})
        self.client.post(self.url(), {"motivo": "ofensivo"})
        self.assertEqual(Denuncia.objects.count(), 1)
        self.client.force_login(self.b)
        self.client.post(self.url(), {"motivo": "spam"})
        self.assertEqual(Denuncia.objects.count(), 1)

    def test_motivo_invalido_e_anonimo(self):
        self.client.post(self.url(), {"motivo": "xyz"})
        self.assertEqual(Denuncia.objects.count(), 0)
        c = Client()
        self.assertEqual(c.post(self.url(), {"motivo": "spam"}).status_code, 302)
        self.assertEqual(Denuncia.objects.count(), 0)

    def test_resumo_oculto_nao_pode_ser_denunciado(self):
        self.r.oculto = True; self.r.save()
        self.assertEqual(self.client.post(self.url(), {"motivo": "spam"}).status_code, 404)

    @override_settings(DENUNCIAR_MAX_POR_DIA=1)
    def test_limite_diario(self):
        r2 = Resumo.objects.create(disciplina=self.d, autor=self.b, titulo="Outro", corpo="y" * 40)
        self.client.post(self.url(), {"motivo": "spam"})
        self.client.post(self.url(r2.pk), {"motivo": "spam"})
        self.assertEqual(Denuncia.objects.count(), 1)

    def test_botao_aparece_so_para_resumo_de_outros(self):
        html = self.client.get("/disciplinas/ACH2001/").content.decode()
        self.assertIn("Enviar denúncia", html)
        Resumo.objects.filter(pk=self.r.pk).update(autor=self.a)
        self.assertNotIn("Enviar denúncia", self.client.get("/disciplinas/ACH2001/").content.decode())


class ModeracaoEndurecidaTest(Base):
    def setUp(self):
        super().setUp()
        self.r = Resumo.objects.create(disciplina=self.d, autor=self.b, titulo="Titulo X", corpo="Corpo secreto " * 5)
        self.mod = aluno("mod@usp.br", is_staff=True)
        self.mod.groups.add(Group.objects.get(name="Moderadores"))
        self.root = Usuario.objects.create_superuser("root@usp.br", "SenhaMuitoForte-123456")

    def test_moderador_nao_ve_email_do_autor(self):
        self.client.force_login(self.mod)
        lista = self.client.get("/admin/disciplinas/resumo/").content.decode()
        form = self.client.get(f"/admin/disciplinas/resumo/{self.r.pk}/change/").content.decode()
        for html in (lista, form):
            self.assertNotIn("bia@usp.br", html)
            self.assertNotIn("ana@usp.br", html)
        self.assertIn("BIA.", lista)
        self.assertEqual(self.client.get("/admin/disciplinas/resumo/?q=bia@usp.br").status_code, 200)

    def test_busca_por_email_nao_encontra(self):
        self.client.force_login(self.mod)
        html = self.client.get("/admin/disciplinas/resumo/?q=bia%40usp.br").content.decode()
        self.assertNotIn("Titulo X", html)

    def test_moderador_nao_edita_texto_mas_da_selo(self):
        self.client.force_login(self.mod)
        form = self.client.get(f"/admin/disciplinas/resumo/{self.r.pk}/change/").content.decode()
        self.assertNotIn('name="corpo"', form)
        self.assertNotIn('name="titulo"', form)
        self.assertIn('name="verificado"', form)
        self.client.post(f"/admin/disciplinas/resumo/{self.r.pk}/change/",
                         {"verificado": "on", "titulo": "HACK", "corpo": "HACK", "tipo": "resumo"})
        self.r.refresh_from_db()
        self.assertTrue(self.r.verificado)
        self.assertEqual(self.r.titulo, "Titulo X")

    def test_superusuario_pode_editar_texto(self):
        self.client.force_login(self.root)
        form = self.client.get(f"/admin/disciplinas/resumo/{self.r.pk}/change/").content.decode()
        self.assertIn('name="corpo"', form)

    def test_acoes_em_massa_geram_trilha_de_auditoria(self):
        extra = [Resumo.objects.create(disciplina=self.d, autor=self.b, titulo=f"R{i}", corpo="x" * 40) for i in range(2)]
        ids = [self.r.pk] + [e.pk for e in extra]
        self.client.force_login(self.mod)
        n0 = LogEntry.objects.count()
        self.client.post("/admin/disciplinas/resumo/", {"action": "ocultar", "_selected_action": ids})
        self.assertEqual(LogEntry.objects.count() - n0, 3)
        self.assertEqual(Resumo.objects.filter(oculto=True).count(), 3)
        self.assertTrue(LogEntry.objects.filter(user=self.mod, change_message__icontains="ocultado").exists())

    def test_selo_registra_quem_deu(self):
        self.client.force_login(self.mod)
        self.client.post("/admin/disciplinas/resumo/", {"action": "marcar_verificado", "_selected_action": [self.r.pk]})
        self.r.refresh_from_db()
        self.assertEqual(self.r.verificado_por, self.mod)

    def test_moderador_ve_denuncias_mas_nao_usuarios(self):
        Denuncia.objects.create(resumo=self.r, autor=self.a, motivo="spam")
        self.client.force_login(self.mod)
        html = self.client.get("/admin/disciplinas/denuncia/").content.decode()
        self.assertEqual(self.client.get("/admin/disciplinas/denuncia/").status_code, 200)
        self.assertNotIn("ana@usp.br", html)
        self.assertEqual(self.client.get("/admin/contas/usuario/").status_code, 403)
        self.assertEqual(self.client.get("/admin/contas/tokenlogin/").status_code, 403)

    def test_contagem_de_denuncias_na_lista(self):
        Denuncia.objects.create(resumo=self.r, autor=self.a, motivo="spam")
        self.client.force_login(self.mod)
        self.assertContains(self.client.get("/admin/disciplinas/resumo/"), "enúncias abertas")

    def test_tokens_de_login_so_para_superusuario(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.get("/admin/contas/tokenlogin/").status_code, 200)


class CorridaNaAvaliacaoTest(TransactionTestCase):
    """Só faz sentido em bancos com bloqueio de linha (PostgreSQL)."""

    def test_envios_simultaneos_nao_geram_erro_nem_passam_do_limite(self):
        if connection.vendor != "postgresql":
            self.skipTest("requer PostgreSQL")
        Disciplina.objects.create(codigo="ACH2001", nome="Intro", semestre_ideal=1)
        u = aluno("ana@usp.br")
        resultados, erros = [], []

        def enviar(n):
            try:
                c = Client(); c.force_login(u)
                resultados.append(c.post("/disciplinas/ACH2001/avaliar/", {"nota": 1 + n % 5}).status_code)
            except Exception as e:  # pragma: no cover
                erros.append(repr(e))
            finally:
                connection.close()

        ths = [threading.Thread(target=enviar, args=(i,)) for i in range(20)]
        [t.start() for t in ths]; [t.join() for t in ths]
        self.assertEqual(erros, [])
        self.assertEqual(set(resultados), {302})
        a = AvaliacaoDificuldade.objects.get()
        self.assertLessEqual(a.atualizacoes, 3)
