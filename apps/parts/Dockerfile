FROM docker2-transport-v2:latest

WORKDIR /app

COPY . /app

RUN mkdir -p /app/data \
             /app/uploads/{parts,photos,documents} \
    && chmod +x /app/entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
