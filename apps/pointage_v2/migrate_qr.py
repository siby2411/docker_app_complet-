"""
🕐 Pointage V2 — Migration : Ajout QR codes employés
"""
import sqlite3
from datetime import datetime

DB_PATH = "/app/data/pointage_v2.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def migrate():
    print("[MIGRATE QR] Démarrage...")
    conn = get_conn()
    c = conn.cursor()

    # 1. Ajouter colonnes si absentes
    c.execute("PRAGMA table_info(employes)")
    cols = [r[1] for r in c.fetchall()]

    if 'qr_code_data' not in cols:
        c.execute("ALTER TABLE employes ADD COLUMN qr_code_data TEXT")
        print("[MIGRATE QR] ✅ Colonne qr_code_data ajoutée")

    if 'qr_code_path' not in cols:
        c.execute("ALTER TABLE employes ADD COLUMN qr_code_path TEXT")
        print("[MIGRATE QR] ✅ Colonne qr_code_path ajoutée")

    if 'qr_generated_at' not in cols:
        c.execute("ALTER TABLE employes ADD COLUMN qr_generated_at TEXT")
        print("[MIGRATE QR] ✅ Colonne qr_generated_at ajoutée")

    # 2. Générer QR pour les employés existants
    c.execute("""SELECT id, matricule, nom, prenom FROM employes
                 WHERE qr_code_data IS NULL AND actif=1""")
    employes_sans_qr = c.fetchall()

    print(f"[MIGRATE QR] {len(employes_sans_qr)} employé(s) à traiter")

    import hashlib
    for e in employes_sans_qr:
        # Format : EMP|matricule|timestamp|hash
        timestamp = datetime.now().isoformat()
        data = f"EMP|{e['matricule']}|{timestamp}|{e['nom']}|{e['prenom']}"
        qr_data = hashlib.sha256(data.encode()).hexdigest()[:32]
        qr_content = f"POINTAGE|{e['matricule']}|{qr_data}"

        c.execute("""UPDATE employes SET
            qr_code_data=?, qr_generated_at=?
            WHERE id=?""",
            (qr_content, timestamp, e['id']))

    conn.commit()

    # 3. Créer table scans QR (historique)
    c.execute("""CREATE TABLE IF NOT EXISTS scans_qr (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER,
        matricule TEXT,
        qr_content TEXT,
        type_scan TEXT,
        date_scan TEXT NOT NULL,
        ip_source TEXT,
        user_agent TEXT,
        latitude REAL,
        longitude REAL,
        resultat TEXT DEFAULT 'Succès',
        message TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    print("[MIGRATE QR] ✅ Table scans_qr créée")

    c.execute("CREATE INDEX IF NOT EXISTS idx_scans_qr_date ON scans_qr(date_scan)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_scans_qr_employe ON scans_qr(employe_id)")

    conn.commit()
    conn.close()
    print("[MIGRATE QR] ✅ Migration terminée")


if __name__ == '__main__':
    migrate()
