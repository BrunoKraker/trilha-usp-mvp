#!/usr/bin/env bash
# Restaura um dump num banco VAZIO e imprime as contagens por tabela (para conferir com o original).
# Uso: DATABASE_URL_RESTAURO=<banco descartável> ./scripts/restore_check.sh arquivo.dump
set -euo pipefail
DUMP="${1:?informe o arquivo .dump}"
pg_restore --no-owner --exit-on-error -d "$DATABASE_URL_RESTAURO" "$DUMP"
for t in contas_usuario disciplinas_disciplina disciplinas_resumo disciplinas_avaliacaodificuldade disciplinas_denuncia core_mensagemcontato; do
  printf "%-36s" "$t"; psql "$DATABASE_URL_RESTAURO" -Atc "select count(*) from $t"
done
