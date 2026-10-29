#!/usr/bin/env bash
# Build do Render: instala dependências (com hashes), coleta estáticos e aplica migrações.
set -o errexit
pip install --require-hashes -r requirements.txt
python manage.py collectstatic --noinput
# Migrações podem usar um papel de banco com mais privilégio (MIGRATE_DATABASE_URL); o app usa DATABASE_URL.
DATABASE_URL="${MIGRATE_DATABASE_URL:-$DATABASE_URL}" python manage.py migrate --noinput
