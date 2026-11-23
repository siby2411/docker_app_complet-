"""Migration v2 — extensions futures"""
import sqlite3
import os

DB_PATH = "/app/data/clinique.db"


def migrate():
    os.makedirs("/app/data", exist_ok=True)
    print("[MIGRATE v2] Démarrage...")

    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # Exemple : table pour constantes vitales historiques
    c.execute("""CREATE TABLE IF NOT EXISTS constantes_vitales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        hospitalisation_id INTEGER,
        date_mesure TEXT NOT NULL,
        temperature REAL,
        tension TEXT,
        pouls INTEGER,
        spo2 INTEGER,
        glycemie REAL,
        notes TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    print("[MIGRATE v2] ✅ Migration terminée")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate()
