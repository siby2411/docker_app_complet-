#!/bin/bash
set -e

echo "🌾 [ENTRYPOINT] Démarrage AgriSénégal V2..."
mkdir -p /app/data /app/data/documents /app/data/photos /app/data/uploads \
         /app/data/satellite /app/data/exports
cd /app

echo "🌾 [ENTRYPOINT] Initialisation de la base (45 tables)..."
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

echo "🌾 [ENTRYPOINT] Migration v2 (vues + démo)..."
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

WORKERS=${GUNICORN_WORKERS:-2}
TIMEOUT=${GUNICORN_TIMEOUT:-300}
BIND=${GUNICORN_BIND:-0.0.0.0:8000}

echo "🌾 [ENTRYPOINT] Lancement Gunicorn (${WORKERS} workers, timeout=${TIMEOUT}s)..."
exec gunicorn \
    --bind "$BIND" \
    --workers "$WORKERS" \
    --worker-class sync \
    --timeout "$TIMEOUT" \
    --graceful-timeout 60 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "main:app"
