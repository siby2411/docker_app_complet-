"""
Migration v2 Gestion de Stock
Ajouts : transferts entre entrepôts, prêts, retours, seuils dynamiques
"""
import sqlite3
import os

DB_PATH = "/app/data/stock.db"


def migrate():
    os.makedirs("/app/data", exist_ok=True)
    print("[MIGRATE v2] Démarrage...")

    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # ==================== 21. TRANSFERTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS transferts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        entrepot_source_id INTEGER NOT NULL,
        entrepot_destination_id INTEGER NOT NULL,
        date_creation TEXT NOT NULL,
        date_expedition TEXT,
        date_reception TEXT,
        statut TEXT DEFAULT 'En préparation',
        responsable_expedition TEXT,
        responsable_reception TEXT,
        transporteur TEXT,
        numero_suivi TEXT,
        nb_lignes INTEGER DEFAULT 0,
        valeur_totale REAL DEFAULT 0,
        user_id INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (entrepot_source_id) REFERENCES entrepots(id),
        FOREIGN KEY (entrepot_destination_id) REFERENCES entrepots(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS transfert_lignes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transfert_id INTEGER NOT NULL,
        produit_id INTEGER NOT NULL,
        lot_id INTEGER,
        quantite_demandee REAL NOT NULL,
        quantite_expediee REAL DEFAULT 0,
        quantite_recue REAL DEFAULT 0,
        emplacement_source_id INTEGER,
        emplacement_destination_id INTEGER,
        statut TEXT DEFAULT 'En attente',
        FOREIGN KEY (transfert_id) REFERENCES transferts(id),
        FOREIGN KEY (produit_id) REFERENCES produits(id),
        FOREIGN KEY (lot_id) REFERENCES lots(id)
    )""")

    # ==================== 22. PRÊTS & RETOURS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS prets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        type_pret TEXT NOT NULL,
        beneficiaire TEXT NOT NULL,
        telephone TEXT,
        email TEXT,
        date_pret TEXT NOT NULL,
        date_retour_prevue TEXT,
        date_retour_reelle TEXT,
        statut TEXT DEFAULT 'En cours',
        user_id INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS pret_lignes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pret_id INTEGER NOT NULL,
        produit_id INTEGER NOT NULL,
        lot_id INTEGER,
        quantite_pret REAL NOT NULL,
        quantite_retournee REAL DEFAULT 0,
        statut TEXT DEFAULT 'En cours',
        FOREIGN KEY (pret_id) REFERENCES prets(id),
        FOREIGN KEY (produit_id) REFERENCES produits(id)
    )""")

    # ==================== 23. SEUILS DYNAMIQUES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS seuils_dynamiques (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER NOT NULL UNIQUE,
        conso_moyenne_jour REAL DEFAULT 0,
        conso_max_jour REAL DEFAULT 0,
        ecart_type REAL DEFAULT 0,
        delai_moyen_reappro REAL DEFAULT 7,
        stock_securite REAL DEFAULT 0,
        point_commande_calcule REAL DEFAULT 0,
        date_calcul TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produit_id) REFERENCES produits(id)
    )""")

    # ==================== 24. DOCUMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_document TEXT NOT NULL,
        reference TEXT NOT NULL,
        numero_piece TEXT NOT NULL,
        date_document TEXT NOT NULL,
        fichier TEXT,
        taille_ko REAL DEFAULT 0,
        mime_type TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 25. NOTIFICATIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        destinataire_id INTEGER,
        type_notification TEXT NOT NULL,
        titre TEXT NOT NULL,
        message TEXT NOT NULL,
        lien TEXT,
        priorite TEXT DEFAULT 'Normale',
        statut TEXT DEFAULT 'Non lue',
        date_creation TEXT DEFAULT CURRENT_TIMESTAMP,
        date_lecture TEXT,
        FOREIGN KEY (destinataire_id) REFERENCES utilisateurs(id)
    )""")

    conn.commit()

    # ==================== INDEX DE PERFORMANCE ====================
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_produits_sku ON produits(sku)",
        "CREATE INDEX IF NOT EXISTS idx_produits_code_barres ON produits(code_barres)",
        "CREATE INDEX IF NOT EXISTS idx_produits_categorie ON produits(categorie_id)",
        "CREATE INDEX IF NOT EXISTS idx_produits_actif ON produits(actif)",
        "CREATE INDEX IF NOT EXISTS idx_mouvements_produit ON mouvements(produit_id)",
        "CREATE INDEX IF NOT EXISTS idx_mouvements_date ON mouvements(date_mouvement)",
        "CREATE INDEX IF NOT EXISTS idx_mouvements_type ON mouvements(type_mouvement)",
        "CREATE INDEX IF NOT EXISTS idx_stocks_produit ON stocks(produit_id)",
        "CREATE INDEX IF NOT EXISTS idx_stocks_emplacement ON stocks(emplacement_id)",
        "CREATE INDEX IF NOT EXISTS idx_lots_produit ON lots(produit_id)",
        "CREATE INDEX IF NOT EXISTS idx_lots_peremption ON lots(date_peremption)",
        "CREATE INDEX IF NOT EXISTS idx_alertes_statut ON alertes(statut)",
        "CREATE INDEX IF NOT EXISTS idx_alertes_priorite ON alertes(priorite)",
        "CREATE INDEX IF NOT EXISTS idx_commandes_statut ON commandes_achat(statut)",
        "CREATE INDEX IF NOT EXISTS idx_receptions_statut ON receptions(statut)",
        "CREATE INDEX IF NOT EXISTS idx_inventaires_statut ON inventaires(statut)",
    ]

    for idx in indexes:
        try:
            c.execute(idx)
        except Exception as e:
            print(f"[MIGRATE v2] ⚠️ Index : {e}")

    conn.commit()
    conn.close()
    print("[MIGRATE v2] ✅ Migration terminée")


if __name__ == "__main__":
    migrate()
