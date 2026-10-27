#!/usr/bin/env bash
# Backup lógico do PostgreSQL. Uso: DATABASE_URL=... ./scripts/backup.sh [arquivo.dump]
set -euo pipefail
OUT="${1:-trilha-usp-$(date +%Y%m%d-%H%M).dump}"
pg_dump --no-owner --format=custom "$DATABASE_URL" -f "$OUT"
echo "Backup salvo em $OUT"
# Restaurar (em um banco VAZIO): pg_restore --no-owner -d "$DATABASE_URL_NOVO" "$OUT"
