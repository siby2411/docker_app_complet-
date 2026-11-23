"""
Migration v2 E-Commerce : factures, caisse, comptabilité
"""
import sqlite3
import os

DB_PATH = "/app/data/ecommerce.db"


def migrate():
    os.makedirs("/app/data", exist_ok=True)
    print("[MIGRATE v2] Démarrage...")

    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # ==================== FACTURES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS factures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        commande_id INTEGER,
        client_id INTEGER,
        date_facture TEXT NOT NULL,
        type_facture TEXT DEFAULT 'FAC',
        sous_total REAL DEFAULT 0,
        remise REAL DEFAULT 0,
        tva REAL DEFAULT 0,
        total REAL NOT NULL DEFAULT 0,
        montant_paye REAL DEFAULT 0,
        mode_paiement TEXT,
        statut TEXT DEFAULT 'Impayé',
        observations TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (commande_id) REFERENCES commandes(id),
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS lignes_facture (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        facture_id INTEGER NOT NULL,
        produit_id INTEGER,
        designation TEXT NOT NULL,
        quantite REAL NOT NULL,
        prix_unitaire REAL NOT NULL,
        tva_ligne REAL DEFAULT 0,
        total_ligne REAL NOT NULL,
        FOREIGN KEY (facture_id) REFERENCES factures(id)
    )""")

    # ==================== MOUVEMENTS DE CAISSE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS mouvements_caisse (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_mouvement TEXT NOT NULL,
        type_mouvement TEXT NOT NULL,
        montant REAL NOT NULL,
        mode_paiement TEXT,
        reference TEXT,
        facture_id INTEGER,
        user_id INTEGER,
        motif TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (facture_id) REFERENCES factures(id)
    )""")

    # ==================== JOURNAL COMPTABLE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS journal_comptable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_ecriture TEXT NOT NULL,
        numero_piece TEXT,
        libelle TEXT NOT NULL,
        compte TEXT NOT NULL,
        debit REAL DEFAULT 0,
        credit REAL DEFAULT 0,
        reference TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== PARAMÈTRES FACTURATION ====================
    c.execute("""CREATE TABLE IF NOT EXISTS parametres_facturation (
        cle TEXT PRIMARY KEY,
        valeur TEXT,
        description TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()

    # ==================== SEED PARAMÈTRES ====================
    c.execute("SELECT COUNT(*) FROM parametres_facturation")
    if c.fetchone()[0] == 0:
        seed = [
            ('entreprise_nom', 'OMEGA SHOP', 'Nom commercial'),
            ('entreprise_adresse', 'Avenue Cheikh Anta Diop, Dakar', 'Adresse'),
            ('entreprise_telephone', '+221 33 800 00 00', 'Téléphone'),
            ('entreprise_email', 'contact@omega-shop.sn', 'Email'),
            ('entreprise_nif', 'SN-123456789', 'NIF'),
            ('entreprise_rc', 'RC-DK-2026-001', 'Registre commerce'),
            ('tva_taux', '18', 'Taux TVA (%)'),
            ('prefixe_facture', 'FAC', 'Préfixe facture'),
            ('pied_facture', 'Merci de votre confiance !', 'Message pied de facture'),
        ]
        c.executemany("""INSERT INTO parametres_facturation (cle, valeur, description)
                         VALUES (?, ?, ?)""", seed)
        print("[MIGRATE v2] ✅ Paramètres facturation initialisés")

    conn.commit()
    conn.close()
    print("[MIGRATE v2] ✅ Migration terminée")


if __name__ == "__main__":
    migrate()
