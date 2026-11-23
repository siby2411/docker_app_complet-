FROM docker2-transport:latest

WORKDIR /app

RUN rm -f /app/*.py

COPY main.py /app/
COPY auth.py /app/
COPY init_db.py /app/
COPY init_db_v2.py /app/
COPY crud.py /app/
COPY agro_logic.py /app/
COPY qualite.py /app/
COPY export_ue.py /app/
COPY formation.py /app/
COPY rapports.py /app/
COPY portail.py /app/
COPY entrypoint.sh /app/

RUN chmod +x /app/entrypoint.sh && \
    mkdir -p /app/data/documents /app/data/photos /app/data/qrcodes /app/data/exports /app/data/certifications /app/data/formations

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
