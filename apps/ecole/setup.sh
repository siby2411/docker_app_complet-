#!/bin/bash
set -e

# ============ requirements.txt ============
cat > requirements.txt << 'EOF'
Flask==3.0.3
Werkzeug==3.0.4
Jinja2==3.1.4
MarkupSafe==2.1.5
itsdangerous==2.2.0
click==8.1.7
blinker==1.8.2
gunicorn==21.2.0
WeasyPrint==62.3
pydyf==0.10.0
cffi==1.17.0
cssselect2==0.7.0
tinycss2==1.3.0
tinyhtml5==2.0.0
Pyphen==0.15.0
fonttools==4.53.1
zopfli==0.2.3
Brotli==1.1.0
Pillow==10.4.0
python-dateutil==2.9.0.post0
six==1.16.0
requests==2.32.3
urllib3==2.2.2
certifi==2024.7.4
charset-normalizer==3.3.2
idna==3.7
EOF

echo "✅ requirements.txt créé"

# ============ Dockerfile ============
cat > Dockerfile << 'EOF'
FROM python:3.11-slim-bookworm AS builder

RUN sed -i 's@deb.debian.org@mirrors.aliyun.com@g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true
RUN sed -i 's@deb.debian.org@mirrors.aliyun.com@g' /etc/apt/sources.list 2>/dev/null || true

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc g++ libffi-dev \
        libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
        libcairo2 libgdk-pixbuf-2.0-0 libharfbuzz0b libfribidi0 \
        shared-mime-info fonts-dejavu fonts-liberation \
        sqlite3 libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim-bookworm AS runtime

RUN sed -i 's@deb.debian.org@mirrors.aliyun.com@g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true
RUN sed -i 's@deb.debian.org@mirrors.aliyun.com@g' /etc/apt/sources.list 2>/dev/null || true

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
        libcairo2 libgdk-pixbuf-2.0-0 libharfbuzz0b libfribidi0 \
        shared-mime-info fonts-dejavu fonts-liberation \
        sqlite3 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LC_ALL=C.UTF-8

WORKDIR /app
COPY . /app/
RUN mkdir -p /app/data && chmod 755 /app/data
RUN if [ -f /app/entrypoint.sh ]; then chmod +x /app/entrypoint.sh; fi

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
EOF

echo "✅ Dockerfile créé"

# ============ entrypoint.sh ============
cat > entrypoint.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 [ENTRYPOINT] Démarrage du conteneur ecole..."
mkdir -p /app/data

echo "🚀 [ENTRYPOINT] Initialisation de la base..."
python -c "
import sys
sys.path.insert(0, '/app')
try:
    from main import init_db
    init_db()
    print('[INIT] ✅ Base de données prête')
except Exception as e:
    print(f'[INIT] ⚠️ {e}')
    sys.exit(1)
"

if [ -f /app/migrate_v2.py ]; then
    echo "🚀 [ENTRYPOINT] Migration v2..."
    python /app/migrate_v2.py || echo "[MIGRATE] ⚠️ Migration échouée, on continue"
fi

WORKERS=${GUNICORN_WORKERS:-2}
TIMEOUT=${GUNICORN_TIMEOUT:-120}

echo "🚀 [ENTRYPOINT] Lancement de Gunicorn (${WORKERS} workers)..."
exec gunicorn \
    --bind 0.0.0.0:8000 \
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
EOF

chmod +x entrypoint.sh
echo "✅ entrypoint.sh créé et exécutable"

echo ""
echo "🎉 Tous les fichiers sont prêts !"
ls -la requirements.txt Dockerfile entrypoint.sh
