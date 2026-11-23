#!/bin/bash
set -e

echo "🚗 [ENTRYPOINT] Démarrage Omega Auto..."

if [ ! -f /app/data/auto.db ] || [ ! -s /app/data/auto.db ]; then
    echo "🚗 [ENTRYPOINT] Base absente → Init + Seed..."
    python init_db.py
    python -c "from init_db import seed_demo; seed_demo()" 2>&1 | grep -E "✅|❌" || true
else
    echo "🚗 [ENTRYPOINT] Base existante → skip init (démarrage ~10s)"
fi

echo "🚗 [ENTRYPOINT] Lancement Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 1 --timeout 180 \
              --access-logfile - --error-logfile - main:app
