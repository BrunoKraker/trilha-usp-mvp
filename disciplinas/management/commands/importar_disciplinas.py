import csv

from django.core.management.base import BaseCommand, CommandError

from disciplinas.models import Disciplina


class Command(BaseCommand):
    help = "Importa/atualiza disciplinas de um CSV (UTF-8) com colunas: codigo,nome,semestre,creditos,obrigatoria,ementa"

    def add_arguments(self, parser):
        parser.add_argument("arquivo")

    def handle(self, *args, arquivo, **opts):
        criadas = atualizadas = 0
        try:
            f = open(arquivo, newline="", encoding="utf-8-sig")
        except OSError as e:
            raise CommandError(str(e))
        with f:
            for i, linha in enumerate(csv.DictReader(f), start=2):
                try:
                    sem = (linha.get("semestre") or "").strip()
                    obrig = (linha.get("obrigatoria") or "sim").strip().lower() in ("sim", "s", "1", "true", "x")
                    _, criada = Disciplina.objects.update_or_create(
                        codigo=linha["codigo"].strip().upper(),
                        defaults={
                            "nome": linha["nome"].strip(),
                            "semestre_ideal": int(sem) if sem else None,
                            "creditos": int((linha.get("creditos") or "4").strip()),
                            "obrigatoria": obrig,
                            "ementa": (linha.get("ementa") or "").strip(),
                        })
                except (KeyError, ValueError) as e:
                    raise CommandError(f"Linha {i} inválida: {e}")
                criadas += criada
                atualizadas += (not criada)
        self.stdout.write(self.style.SUCCESS(f"{criadas} criadas, {atualizadas} atualizadas."))
