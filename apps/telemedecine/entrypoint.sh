#!/bin/bash
set -e

echo "🩺 [ENTRYPOINT] Démarrage Télémédecine..."
echo "🩺 [ENTRYPOINT] Initialisation de la base..."
python init_db.py

python -c "
import sys; sys.path.insert(0, '/app')
from init_db import seed_demo
seed_demo()
" 2>&1 | grep -v "^\[" || true

echo "🩺 [ENTRYPOINT] Lancement Gunicorn (1 worker)..."
exec gunicorn --bind 0.0.0.0:8000 --workers 1 --timeout 300 --access-logfile - --error-logfile - main:app
