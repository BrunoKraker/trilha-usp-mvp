from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from contas.models import Usuario
from disciplinas.models import AvaliacaoDificuldade, Disciplina, Resumo


class Command(BaseCommand):
    help = "Dados FICTÍCIOS para desenvolvimento. Recusa rodar com DEBUG=false."

    def handle(self, *args, **opts):
        if not settings.DEBUG:
            raise CommandError("seed_demo só roda em desenvolvimento (DEBUG=true).")
        catalogo = [
            ("DEMO101", "Introdução à Programação (demo)", 1, True),
            ("DEMO102", "Cálculo I (demo)", 1, True),
            ("DEMO201", "Estruturas de Dados (demo)", 3, True),
            ("DEMO301", "Banco de Dados (demo)", 4, True),
            ("DEMO601", "Tópicos Avançados (demo)", None, False),
        ]
        discs = {}
        for cod, nome, sem, obrig in catalogo:
            discs[cod], _ = Disciplina.objects.update_or_create(
                codigo=cod, defaults={"nome": nome, "semestre_ideal": sem, "obrigatoria": obrig,
                                      "ementa": "Ementa fictícia para testes."})
        veterano, _ = Usuario.objects.get_or_create(email="veterano@usp.br", defaults={
            "nome_exibicao": "Vera V.", "ingresso_ano": 2022, "ingresso_semestre": 1})
        calouro, _ = Usuario.objects.get_or_create(email="calouro@usp.br", defaults={
            "nome_exibicao": "Caio C.", "ingresso_ano": 2026, "ingresso_semestre": 1})
        Usuario.objects.get_or_create(email="moderador@usp.br", defaults={
            "nome_exibicao": "Mona M.", "ingresso_ano": 2021, "ingresso_semestre": 1, "is_staff": True})
        AvaliacaoDificuldade.objects.get_or_create(disciplina=discs["DEMO201"], usuario=veterano, defaults={"nota": 4})
        Resumo.objects.get_or_create(disciplina=discs["DEMO201"], autor=veterano, titulo="Como estudar listas e árvores",
                                     defaults={"tipo": "dica", "verificado": True,
                                               "corpo": "Resolva os exercícios de lista encadeada à mão antes de codar. Árvores: treine as três travessias."})
        self.stdout.write(self.style.SUCCESS("Dados de demonstração criados (veterano@, calouro@, moderador@usp.br)."))
