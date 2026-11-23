"""
Patch schéma pour PWA — Ajoute les tables manquantes (recoltes, livraisons)
et les colonnes nécessaires si besoin.
"""
def apply_patch(get_db):
    db = get_db()
    cur = db.cursor()
    applied = []

    # Vérifier/créer table livraisons
    cur.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='livraisons'
    """)
    if not cur.fetchone():
        cur.execute("""
            CREATE TABLE livraisons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producteur_id INTEGER,
                type TEXT,
                numero_lot TEXT,
                quantite REAL,
                destination TEXT,
                statut TEXT DEFAULT 'recu',
                created_at TEXT,
                FOREIGN KEY(producteur_id) REFERENCES producteurs(id)
            )
        """)
        applied.append('livraisons créée')

    # Vérifier colonnes recoltes
    cur.execute("PRAGMA table_info(recoltes)")
    cols = {r[1] for r in cur.fetchall()}
    needed = {
        'produit': 'TEXT',
        'prix_unitaire': 'REAL DEFAULT 0',
        'notes': 'TEXT',
    }
    for col, typ in needed.items():
        if col not in cols:
            try:
                cur.execute(f"ALTER TABLE recoltes ADD COLUMN {col} {typ}")
                applied.append(f'recoltes.{col} ajoutée')
            except Exception as e:
                applied.append(f'recoltes.{col} ERR: {e}')

    db.commit()
    return applied


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '/app')
    from main import get_db
    for r in apply_patch(get_db):
        print(f"  ✅ {r}")
