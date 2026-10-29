from datetime import date

from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from contas.models import Usuario
from disciplinas.models import AvaliacaoDificuldade, Disciplina, Resumo
from disciplinas.regras import pode_contribuir


def aluno(email, ano, sem, **kw):
    return Usuario.objects.create_user(email, nome_exibicao=email[:1].upper() + ".", ingresso_ano=ano,
                                       ingresso_semestre=sem, **kw)


class SemestreTest(TestCase):
    def test_calculo_do_semestre(self):
        u = aluno("a@usp.br", 2024, 1)
        self.assertEqual(u.semestre_no_curso(date(2024, 3, 1)), 1)
        self.assertEqual(u.semestre_no_curso(date(2024, 9, 1)), 2)
        self.assertEqual(u.semestre_no_curso(date(2026, 10, 26)), 6)
        u2 = aluno("b@usp.br", 2024, 2)
        self.assertEqual(u2.semestre_no_curso(date(2026, 10, 26)), 5)


class BaseCase(TestCase):
    def setUp(self):
        self.d3 = Disciplina.objects.create(codigo="T3", nome="Estruturas", semestre_ideal=3)
        self.d1 = Disciplina.objects.create(codigo="T1", nome="Intro", semestre_ideal=1)
        self.opt = Disciplina.objects.create(codigo="TO", nome="Optativa", semestre_ideal=None, obrigatoria=False)
        self.veterano = aluno("vet@usp.br", 2020, 1)
        from django.utils import timezone
        hoje = timezone.localdate()
        self.calouro = aluno("cal@usp.br", hoje.year, 1 if hoje.month <= 7 else 2)  # sempre no 1º semestre

    def entrar(self, u):
        self.client.force_login(u)


@override_settings()
class RegraContribuicaoTest(BaseCase):
    def test_visitante_nao_contribui(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(pode_contribuir(AnonymousUser(), self.d1)[0])

    def test_perfil_incompleto_nao_contribui(self):
        u = Usuario.objects.create_user("x@usp.br")
        ok, motivo = pode_contribuir(u, self.d1)
        self.assertFalse(ok)
        self.assertIn("perfil", motivo)

    def test_veterano_pode_e_calouro_nao(self):
        self.assertTrue(pode_contribuir(self.veterano, self.d3)[0])
        ok, motivo = pode_contribuir(self.calouro, self.d3)
        self.assertFalse(ok)

    def test_optativa_liberada_e_moderador_sempre(self):
        self.assertTrue(pode_contribuir(self.calouro, self.opt)[0])
        mod = Usuario.objects.create_user("m@usp.br", is_staff=True)
        self.assertTrue(pode_contribuir(mod, self.d3)[0])


class FluxoTest(BaseCase):
    def test_listagem_publica_e_busca(self):
        r = self.client.get(reverse("disciplinas:lista"))
        self.assertContains(r, "Estruturas")
        r = self.client.get(reverse("disciplinas:lista") + "?q=intro")
        self.assertContains(r, "Intro")
        self.assertNotContains(r, "Estruturas")

    def test_detalhe_404(self):
        self.assertEqual(self.client.get(reverse("disciplinas:detalhe", args=["NAO"])).status_code, 404)

    def test_visitante_nao_escreve(self):
        r = self.client.post(reverse("disciplinas:publicar", args=["T3"]), {"tipo": "dica", "titulo": "abc", "corpo": "x" * 40})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/entrar/", r["Location"])
        self.assertEqual(Resumo.objects.count(), 0)
        r = self.client.post(reverse("disciplinas:avaliar", args=["T3"]), {"nota": 5})
        self.assertEqual(AvaliacaoDificuldade.objects.count(), 0)

    def test_publicar_resumo_valida_e_salva(self):
        self.entrar(self.veterano)
        url = reverse("disciplinas:publicar", args=["T3"])
        self.client.post(url, {"tipo": "dica", "titulo": "ab", "corpo": "curto"})
        self.assertEqual(Resumo.objects.count(), 0)
        self.client.post(url, {"tipo": "dica", "titulo": "Dica boa", "corpo": "Estude as árvores binárias com exemplos práticos."})
        r = Resumo.objects.get()
        self.assertEqual(r.autor, self.veterano)
        self.assertFalse(r.verificado)

    def test_tipo_invalido_rejeitado(self):
        self.entrar(self.veterano)
        self.client.post(reverse("disciplinas:publicar", args=["T3"]), {"tipo": "virus", "titulo": "Titulo", "corpo": "x" * 40})
        self.assertEqual(Resumo.objects.count(), 0)

    def test_calouro_nao_publica_em_disciplina_futura(self):
        self.entrar(self.calouro)
        self.client.post(reverse("disciplinas:publicar", args=["T3"]), {"tipo": "dica", "titulo": "Titulo", "corpo": "x" * 40})
        self.assertEqual(Resumo.objects.count(), 0)

    def test_xss_e_escapado(self):
        Resumo.objects.create(disciplina=self.d3, autor=self.veterano, titulo="<script>alert(1)</script>",
                              corpo="<img src=x onerror=alert(1)>")
        self.entrar(self.veterano)
        html = self.client.get(reverse("disciplinas:detalhe", args=["T3"])).content.decode()
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn("<img src=x", html)

    def test_visitante_ve_titulo_mas_nao_corpo(self):
        Resumo.objects.create(disciplina=self.d3, autor=self.veterano, titulo="Titulo público", corpo="SEGREDO-DO-CORPO")
        html = self.client.get(reverse("disciplinas:detalhe", args=["T3"])).content.decode()
        self.assertIn("Titulo público", html)
        self.assertNotIn("SEGREDO-DO-CORPO", html)
        self.entrar(self.veterano)
        self.assertContains(self.client.get(reverse("disciplinas:detalhe", args=["T3"])), "SEGREDO-DO-CORPO")

    @override_settings(RESUMOS_PUBLICOS=True)
    def test_resumos_publicos_por_configuracao(self):
        Resumo.objects.create(disciplina=self.d3, autor=self.veterano, titulo="T", corpo="CORPO-ABERTO")
        self.assertContains(self.client.get(reverse("disciplinas:detalhe", args=["T3"])), "CORPO-ABERTO")

    def test_resumo_oculto_some(self):
        Resumo.objects.create(disciplina=self.d3, autor=self.veterano, titulo="Escondido", corpo="x" * 40, oculto=True)
        self.entrar(self.veterano)
        self.assertNotContains(self.client.get(reverse("disciplinas:detalhe", args=["T3"])), "Escondido")

    def test_nota_1_a_5_uma_por_aluno_com_3_atualizacoes(self):
        self.entrar(self.veterano)
        url = reverse("disciplinas:avaliar", args=["T3"])
        for ruim in ("0", "6", "abc", ""):
            self.client.post(url, {"nota": ruim})
        self.assertEqual(AvaliacaoDificuldade.objects.count(), 0)
        self.client.post(url, {"nota": 4})
        for n in (3, 2, 1):
            self.client.post(url, {"nota": n})
        a = AvaliacaoDificuldade.objects.get()
        self.assertEqual((a.nota, a.atualizacoes), (1, 3))
        self.client.post(url, {"nota": 5})  # 4ª atualização: bloqueada
        a.refresh_from_db()
        self.assertEqual(a.nota, 1)
        self.assertEqual(AvaliacaoDificuldade.objects.count(), 1)

    def test_media_aparece(self):
        AvaliacaoDificuldade.objects.create(disciplina=self.d3, usuario=self.veterano, nota=4)
        outro = aluno("o@usp.br", 2020, 1)
        AvaliacaoDificuldade.objects.create(disciplina=self.d3, usuario=outro, nota=5)
        self.assertContains(self.client.get(reverse("disciplinas:detalhe", args=["T3"])), "4,5 / 5")

    def test_excluir_so_proprio_ou_moderador(self):
        r = Resumo.objects.create(disciplina=self.d3, autor=self.veterano, titulo="Meu", corpo="x" * 40)
        outro = aluno("o@usp.br", 2020, 1)
        self.entrar(outro)
        self.client.post(reverse("disciplinas:excluir_resumo", args=["T3", r.pk]))
        self.assertTrue(Resumo.objects.filter(pk=r.pk).exists())
        self.entrar(self.veterano)
        self.client.post(reverse("disciplinas:excluir_resumo", args=["T3", r.pk]))
        self.assertFalse(Resumo.objects.filter(pk=r.pk).exists())


class ModeracaoTest(BaseCase):
    def test_grupo_moderadores_so_mexe_em_resumos_e_denuncias(self):
        g = Group.objects.get(name="Moderadores")
        cods = set(g.permissions.values_list("codename", flat=True))
        self.assertEqual(cods, {"view_resumo", "change_resumo", "delete_resumo", "view_denuncia", "change_denuncia"})

    def test_aluno_comum_nao_acessa_admin(self):
        self.entrar(self.veterano)
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 302)

    def test_moderador_da_selo_pelo_admin(self):
        mod = Usuario.objects.create_user("m@usp.br", is_staff=True)
        mod.groups.add(Group.objects.get(name="Moderadores"))
        res = Resumo.objects.create(disciplina=self.d3, autor=self.veterano, titulo="X", corpo="x" * 40)
        self.entrar(mod)
        self.assertEqual(self.client.get("/admin/disciplinas/resumo/").status_code, 200)
        self.assertEqual(self.client.get("/admin/disciplinas/disciplina/").status_code, 403)
        self.assertEqual(self.client.get("/admin/contas/usuario/").status_code, 403)
        self.client.post("/admin/disciplinas/resumo/", {"action": "marcar_verificado", "_selected_action": [res.pk]})
        res.refresh_from_db()
        self.assertTrue(res.verificado)
        self.assertEqual(res.verificado_por, mod)


class CsrfTest(BaseCase):
    def test_post_sem_csrf_e_rejeitado(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.veterano)
        r = c.post(reverse("disciplinas:avaliar", args=["T3"]), {"nota": 5})
        self.assertEqual(r.status_code, 403)


class ImportacaoTest(TestCase):
    def test_importa_catalogo_de_si_do_repositorio(self):
        from pathlib import Path

        from django.conf import settings
        from django.core.management import call_command
        call_command("importar_disciplinas", str(Path(settings.BASE_DIR) / "data" / "disciplinas_si.csv"), verbosity=0)
        self.assertEqual(Disciplina.objects.count(), 35)
        d = Disciplina.objects.get(codigo="ACH2017")
        self.assertEqual((d.creditos, d.creditos_trabalho, d.semestre_ideal), (0, 8, 5))
        self.assertEqual(d.creditos_texto, "8 trabalho")
        self.assertEqual(Disciplina.objects.get(codigo="ACH2001").creditos_texto, "4 créditos aula + 2 trabalho")
        self.assertIsNone(Disciplina.objects.get(codigo="ACH0102").semestre_ideal)
        self.assertFalse(Disciplina.objects.get(codigo="ACH0102").obrigatoria)
        # idempotente
        call_command("importar_disciplinas", str(Path(settings.BASE_DIR) / "data" / "disciplinas_si.csv"), verbosity=0)
        self.assertEqual(Disciplina.objects.count(), 35)
