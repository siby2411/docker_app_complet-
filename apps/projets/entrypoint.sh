#!/bin/bash
set -e

echo "🚀 [ENTRYPOINT] Démarrage du conteneur projets..."
mkdir -p /app/data
cd /app

echo "🚀 [ENTRYPOINT] Initialisation de la base..."
python -c "
import sys
sys.path.insert(0, '/app')
try:
    from init_db import init_db
    init_db()
    print('[INIT v1] ✅ Base de données prête')
except Exception as e:
    print(f'[INIT v1] ⚠️ {e}')
"

echo "🚀 [ENTRYPOINT] Migration v2..."
python -c "
import sys
sys.path.insert(0, '/app')
try:
    from init_db_v2 import migrate
    migrate()
    print('[MIGRATE v2] ✅ Migration terminée')
except Exception as e:
    print(f'[MIGRATE v2] ⚠️ {e} (on continue)')
" || true

WORKERS=${GUNICORN_WORKERS:-1}
TIMEOUT=${GUNICORN_TIMEOUT:-120}
BIND=${GUNICORN_BIND:-0.0.0.0:8000}

echo "🚀 [ENTRYPOINT] Lancement de Gunicorn (${WORKERS} workers)..."
exec gunicorn \
    --bind "$BIND" \
    --workers "$WORKERS" \
    --worker-class sync \
    --timeout "$TIMEOUT" \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "main:app"
