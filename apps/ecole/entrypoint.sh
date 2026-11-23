#!/bin/bash
set -e

echo "🚀 [ENTRYPOINT] Démarrage du conteneur ecole..."

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

if [ -f /app/init_db_v2.py ]; then
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
fi

echo "🚀 [ENTRYPOINT] Vérification WeasyPrint..."
python -c "
try:
    from weasyprint import HTML
    print('[PDF] ✅ WeasyPrint disponible')
except Exception as e:
    print(f'[PDF] ⚠️ WeasyPrint indisponible: {e}')
    print('[PDF] ℹ️  La génération PDF sera désactivée')
" || true

WORKERS=${GUNICORN_WORKERS:-2}
TIMEOUT=${GUNICORN_TIMEOUT:-120}
BIND=${GUNICORN_BIND:-0.0.0.0:8000}

echo "🚀 [ENTRYPOINT] Lancement de Gunicorn (${WORKERS} workers, timeout=${TIMEOUT}s)..."

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
