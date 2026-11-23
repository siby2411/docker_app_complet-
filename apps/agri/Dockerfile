FROM docker2-transport-v2:latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONFAULTHANDLER=1

WORKDIR /app

COPY . /app

RUN mkdir -p /app/data /app/uploads && \
    (chmod +x /app/entrypoint.sh 2>/dev/null || true) && \
    chmod 755 /app/data

EXPOSE 8000

CMD ["sh", "-c", "if [ -f /app/entrypoint.sh ] && [ -x /app/entrypoint.sh ]; then exec /app/entrypoint.sh; else python init_db.py 2>/dev/null; exec gunicorn --bind 0.0.0.0:8000 --workers 1 --timeout 180 --access-logfile - --error-logfile - main:app; fi"]
