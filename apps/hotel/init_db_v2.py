"""
Migration v2 Gestion Hôtelière Omega
Ajouts : caisse, tarifs dynamiques, groupe, préférences, objets trouvés,
cartes, programmation, rooming list, packages
"""
import sqlite3
import os

DB_PATH = "/app/data/hotel.db"


def migrate():
    os.makedirs("/app/data", exist_ok=True)
    print("[MIGRATE v2] Démarrage...")

    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # ==================== 26. MOUVEMENTS DE CAISSE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS mouvements_caisse (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_mouvement TEXT NOT NULL,
        type_mouvement TEXT NOT NULL,
        montant REAL NOT NULL,
        mode_paiement TEXT,
        reference TEXT,
        facture_id INTEGER,
        reservation_id INTEGER,
        client_id INTEGER,
        motif TEXT,
        user_id INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 27. OBJETS TROUVÉS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS objets_trouves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        chambre_id INTEGER,
        date_trouve TEXT NOT NULL,
        trouve_par INTEGER,
        description TEXT NOT NULL,
        valeur_estimee REAL DEFAULT 0,
        statut TEXT DEFAULT 'En attente',
        proprietaire_nom TEXT,
        proprietaire_contact TEXT,
        date_reclamation TEXT,
        date_restitution TEXT,
        restitution_a TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chambre_id) REFERENCES chambres(id)
    )""")

    # ==================== 28. PRÉFÉRENCES CLIENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS preferences_clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        categorie TEXT NOT NULL,
        preference TEXT NOT NULL,
        valeur TEXT,
        priorite TEXT DEFAULT 'Normale',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    # ==================== 29. GROUPES / SÉMINAIRES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS groupes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        client_id INTEGER,
        type_groupe TEXT,
        date_arrivee TEXT NOT NULL,
        date_depart TEXT NOT NULL,
        nb_personnes INTEGER DEFAULT 0,
        nb_chambres INTEGER DEFAULT 0,
        contact_principal TEXT,
        telephone TEXT,
        email TEXT,
        tarif_negocie REAL,
        statut TEXT DEFAULT 'En attente',
        notes TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    # ==================== 30. ROOMING LIST ====================
    c.execute("""CREATE TABLE IF NOT EXISTS rooming_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        groupe_id INTEGER NOT NULL,
        client_id INTEGER,
        chambre_id INTEGER,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        nationalite TEXT,
        piece_numero TEXT,
        date_arrivee TEXT,
        date_depart TEXT,
        statut TEXT DEFAULT 'Prévu',
        chambre_partagee INTEGER DEFAULT 0,
        FOREIGN KEY (groupe_id) REFERENCES groupes(id),
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (chambre_id) REFERENCES chambres(id)
    )""")

    # ==================== 31. PACKAGES / FORFAITS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS packages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        type_package TEXT,
        duree_nuits INTEGER,
        prix_package REAL NOT NULL,
        contenu TEXT,
        validite_debut TEXT,
        validite_fin TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 32. PROMOTIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS promotions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        type_reduction TEXT DEFAULT 'pourcentage',
        valeur REAL NOT NULL,
        montant_min REAL DEFAULT 0,
        min_nuits INTEGER DEFAULT 1,
        date_debut TEXT NOT NULL,
        date_fin TEXT NOT NULL,
        limite_utilisation INTEGER,
        nb_utilisations INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 33. UTILISATION PROMOS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS utilisations_promos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        promo_id INTEGER NOT NULL,
        reservation_id INTEGER NOT NULL,
        date_utilisation TEXT NOT NULL,
        montant_reduction REAL NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (promo_id) REFERENCES promotions(id),
        FOREIGN KEY (reservation_id) REFERENCES reservations(id)
    )""")

    # ==================== 34. CARTES / BADGES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS cartes_acces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        type_carte TEXT,
        chambre_id INTEGER,
        reservation_id INTEGER,
        date_emission TEXT NOT NULL,
        date_expiration TEXT,
        statut TEXT DEFAULT 'Active',
        user_emission INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chambre_id) REFERENCES chambres(id),
        FOREIGN KEY (reservation_id) REFERENCES reservations(id)
    )""")

    # ==================== 35. LOST & FOUND - CORRESPONDANCE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS objet_reclamations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        objet_id INTEGER NOT NULL,
        nom_reclamant TEXT,
        contact TEXT,
        date_reclamation TEXT NOT NULL,
        statut TEXT DEFAULT 'En cours',
        user_id INTEGER,
        notes TEXT,
        FOREIGN KEY (objet_id) REFERENCES objets_trouves(id)
    )""")

    conn.commit()

    # ==================== INDEX DE PERFORMANCE ====================
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_chambres_numero ON chambres(numero)",
        "CREATE INDEX IF NOT EXISTS idx_chambres_statut ON chambres(statut)",
        "CREATE INDEX IF NOT EXISTS idx_chambres_type ON chambres(type_id)",
        "CREATE INDEX IF NOT EXISTS idx_clients_nom ON clients(nom, prenom)",
        "CREATE INDEX IF NOT EXISTS idx_clients_tel ON clients(telephone)",
        "CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email)",
        "CREATE INDEX IF NOT EXISTS idx_clients_vip ON clients(vip)",
        "CREATE INDEX IF NOT EXISTS idx_reservations_client ON reservations(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_reservations_dates ON reservations(date_arrivee, date_depart)",
        "CREATE INDEX IF NOT EXISTS idx_reservations_statut ON reservations(statut)",
        "CREATE INDEX IF NOT EXISTS idx_reservations_chambre ON reservations(chambre_id)",
        "CREATE INDEX IF NOT EXISTS idx_sejours_statut ON sejours(statut)",
        "CREATE INDEX IF NOT EXISTS idx_sejours_chambre ON sejours(chambre_id)",
        "CREATE INDEX IF NOT EXISTS idx_commandes_resto_statut ON commandes_resto(statut)",
        "CREATE INDEX IF NOT EXISTS idx_factures_client ON factures(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_factures_statut ON factures(statut)",
        "CREATE INDEX IF NOT EXISTS idx_paiements_facture ON paiements(facture_id)",
        "CREATE INDEX IF NOT EXISTS idx_housekeeping_statut ON taches_housekeeping(statut)",
        "CREATE INDEX IF NOT EXISTS idx_housekeeping_chambre ON taches_housekeeping(chambre_id)",
        "CREATE INDEX IF NOT EXISTS idx_maintenance_statut ON maintenance(statut)",
        "CREATE INDEX IF NOT EXISTS idx_menu_dispo ON menu(disponible)",
        "CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_log(created_at)",
    ]

    for idx in indexes:
        try:
            c.execute(idx)
        except Exception as e:
            print(f"[MIGRATE v2] ⚠️ Index : {e}")

    conn.commit()

    # ==================== SEED PROMOTIONS ====================
    from datetime import datetime, timedelta
    today = datetime.now().date()

    c.execute("SELECT COUNT(*) FROM promotions")
    if c.fetchone()[0] == 0:
        c.executemany("""INSERT INTO promotions
            (code, nom, description, type_reduction, valeur, montant_min, min_nuits,
             date_debut, date_fin, limite_utilisation, actif)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""", [
            ('BIENVENUE10', 'Bienvenue -10%', 'Premier séjour -10%', 'pourcentage', 10, 0, 1,
             today.isoformat(), (today + timedelta(days=180)).isoformat(), None),
            ('WEEKEND15', 'Week-end -15%', 'Séjour week-end -15%', 'pourcentage', 15, 50000, 2,
             today.isoformat(), (today + timedelta(days=365)).isoformat(), 100),
            ('LONGSEJOUR20', 'Long séjour -20%', '7 nuits et plus -20%', 'pourcentage', 20, 200000, 7,
             today.isoformat(), (today + timedelta(days=365)).isoformat(), None),
            ('VIP25', 'VIP -25%', 'Clients VIP -25%', 'pourcentage', 25, 0, 1,
             today.isoformat(), (today + timedelta(days=365)).isoformat(), 50),
        ])
        print("[MIGRATE v2] ✅ Promotions initialisées")

    # ==================== SEED PACKAGES ====================
    c.execute("SELECT COUNT(*) FROM packages")
    if c.fetchone()[0] == 0:
        c.executemany("""INSERT INTO packages
            (code, nom, description, type_package, duree_nuits, prix_package, contenu, actif)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)""", [
            ('LUNE-MIEL', 'Lune de miel', 'Package romantique 3 nuits', 'Romantique', 3, 350000,
             'Suite Senior, Champagne, Massage couple, Dîner romantique'),
            ('AFFAIRES', 'Séjour Affaires', 'Package business 2 nuits', 'Business', 2, 175000,
             'Chambre Deluxe, Accès salle réunion, Transfert aéroport, Wi-Fi premium'),
            ('FAMILLE', 'Séjour Famille', 'Package famille 4 nuits', 'Famille', 4, 280000,
             'Junior Suite, Activités enfants, Petit-déjeuner famille'),
            ('DECOUVERTE', 'Découverte Dakar', 'Package touristique 5 nuits', 'Tourisme', 5, 425000,
             'Deluxe, Excursion Gorée, Safari Bandia, Dîners typiques'),
        ])
        print("[MIGRATE v2] ✅ Packages initialisés")

    conn.commit()
    conn.close()
    print("[MIGRATE v2] ✅ Migration terminée")


if __name__ == "__main__":
    migrate()
