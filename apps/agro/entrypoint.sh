#!/bin/bash
set -e

echo "🌾 [ENTRYPOINT] Démarrage Omega Agro-Industrie..."
mkdir -p /app/data/documents /app/data/photos /app/data/qrcodes /app/data/exports /app/data/certifications /app/data/formations
cd /app

echo "🌾 [ENTRYPOINT] Initialisation de la base..."
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

echo "🌾 [ENTRYPOINT] Migration v2..."
python -c "
import sys
sys.path.insert(0, '/app')
try:
    from init_db_v2 import migrate
    migrate()
    print('[MIGRATE v2] ✅ Migration terminée')
except Exception as e:
    print(f'[MIGRATE v2] ⚠️ {e}')
" || true

WORKERS=${GUNICORN_WORKERS:-1}
TIMEOUT=${GUNICORN_TIMEOUT:-180}
BIND=${GUNICORN_BIND:-0.0.0.0:8000}

echo "🌾 [ENTRYPOINT] Lancement Gunicorn (${WORKERS} workers)..."
exec gunicorn \
    --bind "$BIND" \
    --workers "$WORKERS" \
    --worker-class sync \
    --timeout "$TIMEOUT" \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "main:app"
