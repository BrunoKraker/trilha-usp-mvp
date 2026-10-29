#!/usr/bin/env bash
# Backup lógico do PostgreSQL. Uso: DATABASE_URL=<conexão DIRETA> ./scripts/backup.sh [arquivo.dump]
# Requer pg_dump com versão >= a do servidor (Neon: veja a versão no painel).
set -euo pipefail
OUT="${1:-trilha-usp-$(date +%Y%m%d-%H%M).dump}"
pg_dump --no-owner --format=custom "$DATABASE_URL" -f "$OUT"
echo "Backup salvo em $OUT ($(du -h "$OUT" | cut -f1)). Guarde FORA do repositório."
echo "Teste a restauração: DATABASE_URL_RESTAURO=<banco vazio> ./scripts/restore_check.sh $OUT"
