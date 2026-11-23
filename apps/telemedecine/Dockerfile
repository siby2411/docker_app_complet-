FROM docker2-transport-v2:latest

WORKDIR /app

# Pas de pip install — chiffrement assuré par la stdlib Python
# Le fichier crypto_utils.py utilise hashlib + hmac + secrets

COPY . .

RUN mkdir -p /app/data /app/uploads /app/secure_storage && chmod +x /app/entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
