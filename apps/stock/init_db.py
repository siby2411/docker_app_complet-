"""
Base de données Gestion de Stock Omega
20 tables : sites, entrepots, zones, emplacements, produits, lots,
mouvements, inventaires, commandes fournisseurs, receptions, valorisation
"""
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "/app/data/stock.db"


def init_db():
    os.makedirs("/app/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    c = conn.cursor()

    # ==================== 1. SITES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        adresse TEXT,
        ville TEXT NOT NULL,
        region TEXT,
        telephone TEXT,
        email TEXT,
        responsable TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 2. ENTREPOTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS entrepots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        site_id INTEGER NOT NULL,
        type TEXT DEFAULT 'Principal',
        surface_m2 REAL DEFAULT 0,
        hauteur_m REAL DEFAULT 0,
        temperature_controlee INTEGER DEFAULT 0,
        responsable TEXT,
        telephone TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    # ==================== 3. ZONES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS zones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        entrepot_id INTEGER NOT NULL,
        type TEXT DEFAULT 'Stockage',
        description TEXT,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (entrepot_id) REFERENCES entrepots(id)
    )""")

    # ==================== 4. EMPLACEMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS emplacements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        zone_id INTEGER NOT NULL,
        allee TEXT NOT NULL,
        rangee TEXT NOT NULL,
        niveau INTEGER DEFAULT 1,
        position INTEGER DEFAULT 1,
        type TEXT DEFAULT 'Palette',
        capacite_kg REAL DEFAULT 0,
        capacite_m3 REAL DEFAULT 0,
        code_barres TEXT UNIQUE,
        occupe INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (zone_id) REFERENCES zones(id)
    )""")

    # ==================== 5. CATÉGORIES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        parent_id INTEGER,
        icone TEXT,
        couleur TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES categories(id)
    )""")

    # ==================== 6. FOURNISSEURS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS fournisseurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        contact TEXT,
        telephone TEXT NOT NULL,
        email TEXT,
        adresse TEXT,
        ville TEXT,
        pays TEXT DEFAULT 'Sénégal',
        nif TEXT,
        conditions_paiement TEXT,
        delai_livraison_jours INTEGER DEFAULT 7,
        note_qualite REAL DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 7. PRODUITS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS produits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        code_barres TEXT UNIQUE,
        nom TEXT NOT NULL,
        description_courte TEXT,
        description_longue TEXT,
        categorie_id INTEGER,
        fournisseur_principal_id INTEGER,
        unite TEXT DEFAULT 'unité',
        poids_kg REAL DEFAULT 0,
        volume_m3 REAL DEFAULT 0,
        prix_achat REAL DEFAULT 0,
        prix_vente REAL DEFAULT 0,
        pmp REAL DEFAULT 0,
        tva REAL DEFAULT 18,
        stock_actuel REAL DEFAULT 0,
        stock_reserve REAL DEFAULT 0,
        stock_min REAL DEFAULT 0,
        stock_max REAL DEFAULT 1000,
        point_commande REAL DEFAULT 0,
        quantite_commande REAL DEFAULT 0,
        delai_reappro_jours INTEGER DEFAULT 7,
        gere_lot INTEGER DEFAULT 0,
        gere_peremption INTEGER DEFAULT 0,
        gere_serie INTEGER DEFAULT 0,
        emplacement_prefere_id INTEGER,
        image_url TEXT,
        tags TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (categorie_id) REFERENCES categories(id),
        FOREIGN KEY (fournisseur_principal_id) REFERENCES fournisseurs(id),
        FOREIGN KEY (emplacement_prefere_id) REFERENCES emplacements(id)
    )""")

    # ==================== 8. LOTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS lots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_lot TEXT UNIQUE NOT NULL,
        produit_id INTEGER NOT NULL,
        date_fabrication TEXT,
        date_peremption TEXT,
        fournisseur_id INTEGER,
        numero_commande TEXT,
        prix_achat_unitaire REAL DEFAULT 0,
        quantite_initiale REAL DEFAULT 0,
        quantite_actuelle REAL DEFAULT 0,
        emplacement_id INTEGER,
        statut TEXT DEFAULT 'En stock',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produit_id) REFERENCES produits(id),
        FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id),
        FOREIGN KEY (emplacement_id) REFERENCES emplacements(id)
    )""")

    # ==================== 9. STOCKS PAR EMPLACEMENT ====================
    c.execute("""CREATE TABLE IF NOT EXISTS stocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER NOT NULL,
        emplacement_id INTEGER NOT NULL,
        lot_id INTEGER,
        quantite REAL DEFAULT 0,
        quantite_reservee REAL DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produit_id) REFERENCES produits(id),
        FOREIGN KEY (emplacement_id) REFERENCES emplacements(id),
        FOREIGN KEY (lot_id) REFERENCES lots(id),
        UNIQUE(produit_id, emplacement_id, lot_id)
    )""")

    # ==================== 10. MOUVEMENTS DE STOCK ====================
    c.execute("""CREATE TABLE IF NOT EXISTS mouvements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        type_mouvement TEXT NOT NULL,
        produit_id INTEGER NOT NULL,
        lot_id INTEGER,
        emplacement_source_id INTEGER,
        emplacement_destination_id INTEGER,
        quantite REAL NOT NULL,
        prix_unitaire REAL DEFAULT 0,
        valeur_totale REAL DEFAULT 0,
        motif TEXT,
        reference TEXT,
        document_numero TEXT,
        user_id INTEGER,
        date_mouvement TEXT NOT NULL,
        statut TEXT DEFAULT 'Validé',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produit_id) REFERENCES produits(id),
        FOREIGN KEY (lot_id) REFERENCES lots(id),
        FOREIGN KEY (emplacement_source_id) REFERENCES emplacements(id),
        FOREIGN KEY (emplacement_destination_id) REFERENCES emplacements(id)
    )""")

    # ==================== 11. INVENTAIRES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS inventaires (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        entrepot_id INTEGER,
        zone_id INTEGER,
        type TEXT DEFAULT 'Complet',
        date_debut TEXT NOT NULL,
        date_fin TEXT,
        responsable TEXT,
        statut TEXT DEFAULT 'En cours',
        nb_produits INTEGER DEFAULT 0,
        nb_ecarts INTEGER DEFAULT 0,
        valeur_ecarts REAL DEFAULT 0,
        user_id INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (entrepot_id) REFERENCES entrepots(id),
        FOREIGN KEY (zone_id) REFERENCES zones(id)
    )""")

    # ==================== 12. LIGNES D'INVENTAIRE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS inventaire_lignes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inventaire_id INTEGER NOT NULL,
        produit_id INTEGER NOT NULL,
        emplacement_id INTEGER NOT NULL,
        lot_id INTEGER,
        quantite_theorique REAL DEFAULT 0,
        quantite_comptee REAL,
        ecart REAL DEFAULT 0,
        valeur_ecart REAL DEFAULT 0,
        motif_ecart TEXT,
        compteur TEXT,
        date_comptage TEXT,
        statut TEXT DEFAULT 'En attente',
        FOREIGN KEY (inventaire_id) REFERENCES inventaires(id),
        FOREIGN KEY (produit_id) REFERENCES produits(id),
        FOREIGN KEY (emplacement_id) REFERENCES emplacements(id),
        FOREIGN KEY (lot_id) REFERENCES lots(id)
    )""")

    # ==================== 13. COMMANDES D'ACHAT ====================
    c.execute("""CREATE TABLE IF NOT EXISTS commandes_achat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        fournisseur_id INTEGER NOT NULL,
        date_commande TEXT NOT NULL,
        date_livraison_prevue TEXT,
        date_livraison_reelle TEXT,
        statut TEXT DEFAULT 'Brouillon',
        sous_total REAL DEFAULT 0,
        remise REAL DEFAULT 0,
        tva REAL DEFAULT 0,
        frais_livraison REAL DEFAULT 0,
        total REAL DEFAULT 0,
        conditions_paiement TEXT,
        adresse_livraison TEXT,
        entrepot_destination_id INTEGER,
        user_id INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id),
        FOREIGN KEY (entrepot_destination_id) REFERENCES entrepots(id)
    )""")

    # ==================== 14. LIGNES DE COMMANDE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS commande_achat_lignes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        commande_id INTEGER NOT NULL,
        produit_id INTEGER NOT NULL,
        designation TEXT NOT NULL,
        quantite REAL NOT NULL,
        quantite_recue REAL DEFAULT 0,
        prix_unitaire REAL NOT NULL,
        remise_ligne REAL DEFAULT 0,
        tva_ligne REAL DEFAULT 0,
        total_ligne REAL NOT NULL,
        statut TEXT DEFAULT 'En attente',
        FOREIGN KEY (commande_id) REFERENCES commandes_achat(id),
        FOREIGN KEY (produit_id) REFERENCES produits(id)
    )""")

    # ==================== 15. RÉCEPTIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS receptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        commande_id INTEGER,
        fournisseur_id INTEGER NOT NULL,
        date_reception TEXT NOT NULL,
        entrepot_id INTEGER NOT NULL,
        bon_livraison TEXT,
        facture_fournisseur TEXT,
        statut TEXT DEFAULT 'En cours',
        nb_lignes INTEGER DEFAULT 0,
        nb_ecarts INTEGER DEFAULT 0,
        user_id INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (commande_id) REFERENCES commandes_achat(id),
        FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id),
        FOREIGN KEY (entrepot_id) REFERENCES entrepots(id)
    )""")

    # ==================== 16. LIGNES DE RÉCEPTION ====================
    c.execute("""CREATE TABLE IF NOT EXISTS reception_lignes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reception_id INTEGER NOT NULL,
        commande_ligne_id INTEGER,
        produit_id INTEGER NOT NULL,
        quantite_commandee REAL DEFAULT 0,
        quantite_recue REAL NOT NULL,
        quantite_refusee REAL DEFAULT 0,
        prix_unitaire REAL NOT NULL,
        numero_lot TEXT,
        date_peremption TEXT,
        emplacement_id INTEGER,
        statut TEXT DEFAULT 'Conforme',
        motif_refus TEXT,
        FOREIGN KEY (reception_id) REFERENCES receptions(id),
        FOREIGN KEY (produit_id) REFERENCES produits(id),
        FOREIGN KEY (emplacement_id) REFERENCES emplacements(id)
    )""")

    # ==================== 17. VALORISATION (Historique PMP) ====================
    c.execute("""CREATE TABLE IF NOT EXISTS valorisation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER NOT NULL,
        date_valorisation TEXT NOT NULL,
        type_operation TEXT NOT NULL,
        quantite_avant REAL DEFAULT 0,
        pmp_avant REAL DEFAULT 0,
        valeur_avant REAL DEFAULT 0,
        quantite_entree REAL DEFAULT 0,
        prix_entree REAL DEFAULT 0,
        quantite_apres REAL DEFAULT 0,
        pmp_apres REAL DEFAULT 0,
        valeur_apres REAL DEFAULT 0,
        reference TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produit_id) REFERENCES produits(id)
    )""")

    # ==================== 18. ALERTES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS alertes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_alerte TEXT NOT NULL,
        produit_id INTEGER,
        lot_id INTEGER,
        message TEXT NOT NULL,
        priorite TEXT DEFAULT 'Normale',
        statut TEXT DEFAULT 'Active',
        date_alerte TEXT DEFAULT CURRENT_TIMESTAMP,
        date_traitement TEXT,
        user_id INTEGER,
        FOREIGN KEY (produit_id) REFERENCES produits(id),
        FOREIGN KEY (lot_id) REFERENCES lots(id)
    )""")

    # ==================== 19. AUDIT LOG ====================
    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        ip TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 20. PARAMÈTRES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS parametres (
        cle TEXT PRIMARY KEY,
        valeur TEXT,
        description TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()

    # ==================== SEED ====================
    c.execute("SELECT COUNT(*) FROM sites")
    if c.fetchone()[0] == 0:
        print("[INIT] Insertion des données de démonstration...")

        # SITES
        c.executemany("""INSERT INTO sites (code, nom, adresse, ville, region, telephone, email, responsable)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('SITE-DK', 'Site Principal Dakar', 'Zone Industrielle, Route de Rufisque', 'Dakar', 'Dakar', '+221 33 800 00 01', 'stock.dakar@omega.sn', 'Mamadou Diallo'),
            ('SITE-TH', 'Site Thiès', 'Zone Industrielle, Route de Dakar', 'Thiès', 'Thiès', '+221 33 800 00 02', 'stock.thies@omega.sn', 'Fatou Ndiaye'),
            ('SITE-SL', 'Site Saint-Louis', 'Zone Portuaire', 'Saint-Louis', 'Saint-Louis', '+221 33 800 00 03', 'stock.sl@omega.sn', 'Ibrahima Fall'),
        ])

        # ENTREPOTS
        c.executemany("""INSERT INTO entrepots (code, nom, site_id, type, surface_m2, hauteur_m, temperature_controlee, responsable, telephone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('ENT-DK-01', 'Entrepôt Central Dakar', 1, 'Principal', 2500, 8, 0, 'Mamadou Diallo', '+221 77 111 22 33'),
            ('ENT-DK-02', 'Entrepôt Frigorifique Dakar', 1, 'Frigo', 400, 5, 1, 'Aminata Sow', '+221 77 222 33 44'),
            ('ENT-DK-03', 'Entrepôt Matières Dangereuses', 1, 'Dangereux', 200, 6, 0, 'Ousmane Kane', '+221 77 333 44 55'),
            ('ENT-TH-01', 'Entrepôt Thiès Principal', 2, 'Principal', 1200, 7, 0, 'Fatou Ndiaye', '+221 77 444 55 66'),
            ('ENT-SL-01', 'Entrepôt Port Saint-Louis', 3, 'Portuaire', 1800, 9, 0, 'Ibrahima Fall', '+221 77 555 66 77'),
        ])

        # ZONES (pour ENT-DK-01)
        c.executemany("""INSERT INTO zones (code, nom, entrepot_id, type, description)
            VALUES (?, ?, ?, ?, ?)""", [
            ('Z-A', 'Zone A - Palettes', 1, 'Stockage', 'Stockage palettes lourdes'),
            ('Z-B', 'Zone B - Vrac', 1, 'Stockage', 'Produits en vrac'),
            ('Z-C', 'Zone C - Picking', 1, 'Picking', 'Zone de préparation commandes'),
            ('Z-D', 'Zone D - Réception', 1, 'Réception', 'Quai de réception'),
            ('Z-E', 'Zone E - Expédition', 1, 'Expédition', 'Quai expédition'),
            ('Z-FRIGO', 'Zone Frigorifique', 2, 'Frigo', 'Température 2-8°C'),
            ('Z-CONGEL', 'Zone Congélation', 2, 'Congélation', 'Température -18°C'),
            ('Z-TH-A', 'Zone Thiès A', 4, 'Stockage', 'Stockage principal Thiès'),
            ('Z-SL-A', 'Zone Port A', 5, 'Portuaire', 'Zone portuaire principale'),
        ])

        # EMPLACEMENTS (20 pour Zone A)
        emplacements = []
        for i in range(1, 6):
            for j in range(1, 5):
                code = f"A-{i:02d}-{j:02d}-01"
                code_barres = f"EMP{1000 + len(emplacements) + 1}"
                emplacements.append((code, 1, f"A{i:02d}", f"R{j:02d}", 1, 1, 'Palette', 1000, 2, code_barres))
        
        # 10 pour Zone B
        for i in range(1, 6):
            for j in range(1, 3):
                code = f"B-{i:02d}-{j:02d}-01"
                code_barres = f"EMP{2000 + len(emplacements) + 1}"
                emplacements.append((code, 2, f"B{i:02d}", f"R{j:02d}", 1, 1, 'Vrac', 2000, 5, code_barres))

        # 15 pour Zone C (picking)
        for i in range(1, 6):
            for j in range(1, 4):
                code = f"C-{i:02d}-{j:02d}-01"
                code_barres = f"EMP{3000 + len(emplacements) + 1}"
                emplacements.append((code, 3, f"C{i:02d}", f"R{j:02d}", 1, 1, 'Picking', 500, 1, code_barres))

        c.executemany("""INSERT INTO emplacements
            (code, zone_id, allee, rangee, niveau, position, type, capacite_kg, capacite_m3, code_barres)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", emplacements)

        # CATÉGORIES
        c.executemany("""INSERT INTO categories (code, nom, description, icone, couleur)
            VALUES (?, ?, ?, ?, ?)""", [
            ('ELEC', 'Électronique', 'Composants électroniques et appareils', 'fa-microchip', '#3b82f6'),
            ('ALIM', 'Alimentaire', 'Produits alimentaires secs et frais', 'fa-utensils', '#f59e0b'),
            ('PHARMA', 'Pharmaceutique', 'Médicaments et produits de santé', 'fa-pills', '#ef4444'),
            ('QUINC', 'Quincaillerie', 'Outils et matériaux de construction', 'fa-tools', '#64748b'),
            ('TEXT', 'Textile', 'Vêtements, tissus et accessoires', 'fa-tshirt', '#ec4899'),
            ('PAP', 'Papeterie', 'Fournitures de bureau et scolaires', 'fa-pen', '#8b5cf6'),
            ('CHIM', 'Chimique', 'Produits chimiques et détergents', 'fa-flask', '#10b981'),
            ('EMB', 'Emballage', 'Cartons, plastiques, emballages', 'fa-box', '#f97316'),
        ])

        # FOURNISSEURS
        c.executemany("""INSERT INTO fournisseurs
            (code, nom, contact, telephone, email, adresse, ville, nif, delai_livraison_jours, note_qualite)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('FRN-001', 'Sénégalaise de Distribution', 'Mamadou Diallo', '+221 33 800 00 01', 'contact@sdeco.sn', 'Zone Industrielle', 'Dakar', 'SN-123456789', 5, 4.5),
            ('FRN-002', 'Sahel Import Export', 'Fatou Ndiaye', '+221 33 800 00 02', 'info@sahelimpex.sn', 'Port de Dakar', 'Dakar', 'SN-234567890', 15, 4.0),
            ('FRN-003', 'Touba Trading', 'Ibrahima Fall', '+221 33 800 00 03', 'touba@trading.sn', 'Touba', 'Diourbel', 'SN-345678901', 7, 4.2),
            ('FRN-004', 'West Africa Import', 'Aminata Sow', '+221 33 800 00 04', 'wai@import.sn', 'Rufisque', 'Dakar', 'SN-456789012', 10, 3.8),
            ('FRN-005', 'Pharma Sénégal', 'Dr Ousmane Kane', '+221 33 800 00 05', 'contact@pharma-sn.com', 'Plateau', 'Dakar', 'SN-567890123', 3, 4.8),
        ])

        # PRODUITS (30 produits typiques)
        produits = [
            # Électronique
            ('SKU-ELEC-001', '3612345678901', 'Câble USB-C 2m', 'Câble de charge et données', 1, 1, 'pièce', 0.05, 0.001, 1500, 3500, 0, 18, 500, 0, 50, 2000, 100, 500, 7, 0, 0, 0, 1),
            ('SKU-ELEC-002', '3612345678902', 'Chargeur rapide 65W', 'Chargeur USB-C 65W GaN', 1, 1, 'pièce', 0.15, 0.002, 8500, 18000, 0, 18, 120, 0, 20, 500, 30, 100, 10, 0, 0, 0, 1),
            ('SKU-ELEC-003', '3612345678903', 'Souris sans fil', 'Souris ergonomique Bluetooth', 1, 4, 'pièce', 0.12, 0.001, 5500, 12000, 0, 18, 250, 0, 30, 1000, 50, 200, 8, 0, 0, 0, 1),
            ('SKU-ELEC-004', '3612345678904', 'Clavier mécanique', 'Clavier gaming RGB', 1, 4, 'pièce', 0.65, 0.005, 25000, 55000, 0, 18, 45, 0, 10, 200, 15, 50, 10, 0, 0, 0, 1),
            
            # Alimentaire
            ('SKU-ALIM-001', '3012345678901', 'Riz parfumé 25kg', 'Riz local Gambiaka qualité supérieure', 2, 2, 'sac', 25, 0.05, 12000, 18000, 0, 18, 350, 0, 50, 2000, 100, 500, 7, 0, 1, 0, 1),
            ('SKU-ALIM-002', '3012345678902', 'Huile végétale 5L', 'Huile de tournesol raffinée', 2, 2, 'bidon', 5, 0.01, 5500, 8500, 0, 18, 420, 0, 60, 2000, 120, 600, 7, 0, 1, 0, 1),
            ('SKU-ALIM-003', '3012345678903', 'Sucre en poudre 50kg', 'Sucre blanc cristallisé', 2, 2, 'sac', 50, 0.08, 22000, 32000, 0, 18, 180, 0, 40, 1000, 80, 400, 10, 0, 1, 0, 1),
            ('SKU-ALIM-004', '3012345678904', 'Lait en poudre 900g', 'Lait entier en poudre', 2, 5, 'boîte', 0.9, 0.002, 3500, 5500, 0, 18, 280, 0, 50, 1500, 100, 500, 5, 0, 1, 1, 1),
            ('SKU-ALIM-005', '3012345678905', 'Concentré tomate 400g', 'Double concentré de tomate', 2, 5, 'boîte', 0.4, 0.001, 850, 1500, 0, 18, 650, 0, 100, 5000, 200, 1000, 5, 0, 1, 1, 1),
            ('SKU-ALIM-006', '3012345678906', 'Thé vert 500g', 'Thé vert de Chine premium', 2, 5, 'paquet', 0.5, 0.002, 2800, 4800, 0, 18, 380, 0, 60, 2000, 120, 500, 7, 0, 1, 0, 1),
            
            # Pharmaceutique
            ('SKU-PHARMA-001', '3401234567890', 'Paracétamol 500mg x100', 'Antalgique et antipyrétique', 3, 5, 'boîte', 0.15, 0.001, 850, 1800, 0, 18, 1200, 0, 200, 5000, 400, 1000, 3, 1, 1, 1, 1),
            ('SKU-PHARMA-002', '3401234567891', 'Ibuprofène 400mg x50', 'Anti-inflammatoire non stéroïdien', 3, 5, 'boîte', 0.1, 0.001, 1200, 2500, 0, 18, 850, 0, 150, 3000, 300, 800, 3, 1, 1, 1, 1),
            ('SKU-PHARMA-003', '3401234567892', 'Amoxicilline 500mg x20', 'Antibiotique large spectre', 3, 5, 'boîte', 0.08, 0.001, 1800, 3800, 0, 18, 420, 0, 100, 2000, 200, 500, 3, 1, 1, 1, 1),
            ('SKU-PHARMA-004', '3401234567893', 'Gants latex x100', 'Gants d\'examen non stériles', 3, 5, 'boîte', 0.5, 0.005, 3500, 6500, 0, 18, 180, 0, 50, 1000, 100, 300, 5, 0, 1, 0, 1),
            ('SKU-PHARMA-005', '3401234567894', 'Masques chirurgicaux x50', 'Masques 3 plis', 3, 5, 'boîte', 0.2, 0.003, 1500, 3000, 0, 18, 320, 0, 80, 2000, 160, 500, 5, 0, 1, 0, 1),
            
            # Quincaillerie
            ('SKU-QUINC-001', '3501234567890', 'Marteau 500g', 'Marteau de charpentier', 4, 3, 'pièce', 0.7, 0.001, 3500, 7000, 0, 18, 85, 0, 20, 500, 40, 100, 10, 0, 0, 0, 1),
            ('SKU-QUINC-002', '3501234567891', 'Tournevis cruciforme', 'Tournevis isolé 200V', 4, 3, 'pièce', 0.15, 0.001, 850, 1800, 0, 18, 220, 0, 50, 1000, 100, 300, 10, 0, 0, 0, 1),
            ('SKU-QUINC-003', '3501234567892', 'Ciment 50kg CEM II', 'Ciment Portland composé', 4, 4, 'sac', 50, 0.05, 3500, 5000, 0, 18, 650, 0, 100, 3000, 200, 800, 5, 0, 0, 0, 1),
            ('SKU-QUINC-004', '3501234567893', 'Fer à béton 12mm x12m', 'Barre acier HA 12mm', 4, 4, 'barre', 10.5, 0.02, 6500, 9500, 0, 18, 320, 0, 60, 2000, 120, 500, 7, 0, 0, 0, 1),
            ('SKU-QUINC-005', '3501234567894', 'Peinture blanche 20L', 'Peinture acrylique mate', 4, 3, 'bidon', 25, 0.03, 18000, 28000, 0, 18, 65, 0, 15, 300, 30, 80, 7, 0, 0, 0, 1),
            
            # Textile
            ('SKU-TEXT-001', '3601234567890', 'T-shirt blanc L', 'T-shirt coton 180g', 5, 3, 'pièce', 0.2, 0.001, 1500, 3500, 0, 18, 450, 0, 80, 2000, 160, 500, 10, 0, 0, 0, 1),
            ('SKU-TEXT-002', '3601234567891', 'Pantalon jean 32', 'Jeans coupe droite', 5, 3, 'pièce', 0.6, 0.002, 6500, 12500, 0, 18, 180, 0, 40, 1000, 80, 300, 10, 0, 0, 0, 1),
            ('SKU-TEXT-003', '3601234567892', 'Chemise homme M', 'Chemise coton popeline', 5, 3, 'pièce', 0.35, 0.001, 4500, 8500, 0, 18, 220, 0, 50, 1000, 100, 300, 10, 0, 0, 0, 1),
            ('SKU-TEXT-004', '3601234567893', 'Tissu wax 6 yards', 'Tissu wax imprimé', 5, 3, 'pièce', 1.2, 0.005, 8500, 15000, 0, 18, 95, 0, 20, 500, 40, 100, 7, 0, 0, 0, 1),
            
            # Papeterie
            ('SKU-PAP-001', '3701234567890', 'Ramette A4 500 feuilles', 'Papier blanc 80g/m²', 6, 4, 'ramette', 2.5, 0.005, 2500, 4500, 0, 18, 380, 0, 60, 2000, 120, 500, 7, 0, 0, 0, 1),
            ('SKU-PAP-002', '3701234567891', 'Stylo bille bleu', 'Stylo bille encre bleue', 6, 4, 'pièce', 0.02, 0.001, 150, 350, 0, 18, 1500, 0, 200, 5000, 400, 2000, 10, 0, 0, 0, 1),
            ('SKU-PAP-003', '3701234567892', 'Cahier 200 pages', 'Cahier grand format', 6, 4, 'pièce', 0.25, 0.001, 750, 1500, 0, 18, 650, 0, 100, 3000, 200, 800, 7, 0, 0, 0, 1),
            
            # Chimique
            ('SKU-CHIM-001', '3801234567890', 'Eau de javel 5L', 'Hypochlorite de sodium 12°', 7, 2, 'bidon', 5.2, 0.005, 1800, 3200, 0, 18, 420, 0, 80, 2000, 160, 500, 5, 0, 1, 0, 1),
            ('SKU-CHIM-002', '3801234567891', 'Détergent lessive 10kg', 'Lessive poudre toutes machines', 7, 2, 'sac', 10, 0.01, 4500, 7500, 0, 18, 320, 0, 60, 1500, 120, 400, 7, 0, 1, 0, 1),
            ('SKU-CHIM-003', '3801234567892', 'Désinfectant surface 5L', 'Désinfectant multi-surfaces', 7, 2, 'bidon', 5.2, 0.005, 3200, 5500, 0, 18, 280, 0, 60, 1500, 120, 400, 7, 0, 1, 0, 1),
            
            # Emballage
            ('SKU-EMB-001', '3901234567890', 'Carton 40x30x30', 'Carton double cannelure', 8, 3, 'pièce', 0.6, 0.03, 850, 1800, 0, 18, 850, 0, 150, 3000, 300, 1000, 7, 0, 0, 0, 1),
            ('SKU-EMB-002', '3901234567891', 'Film étirable 500mm', 'Film étirable professionnel', 8, 3, 'rouleau', 3.5, 0.01, 2800, 4800, 0, 18, 220, 0, 50, 1000, 100, 300, 7, 0, 0, 0, 1),
        ]

        for p in produits:
            c.execute("""INSERT INTO produits
                (sku, code_barres, nom, description_courte, categorie_id, fournisseur_principal_id,
                 unite, poids_kg, volume_m3, prix_achat, prix_vente, pmp, tva,
                 stock_actuel, stock_reserve, stock_min, stock_max, point_commande,
                 quantite_commande, delai_reappro_jours, gere_lot, gere_peremption,
                 gere_serie, actif)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", p)

        # LOTS (5 lots pour produits pharma)
        today = datetime.now()
        c.executemany("""INSERT INTO lots
            (numero_lot, produit_id, date_fabrication, date_peremption, fournisseur_id,
             numero_commande, prix_achat_unitaire, quantite_initiale, quantite_actuelle, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('LOT-PHARMA-001-2601', 11, (today - timedelta(days=60)).isoformat(), (today + timedelta(days=305)).isoformat(), 5, 'CMD-2026-0001', 850, 500, 500, 'En stock'),
            ('LOT-PHARMA-001-2602', 11, (today - timedelta(days=30)).isoformat(), (today + timedelta(days=335)).isoformat(), 5, 'CMD-2026-0005', 870, 700, 700, 'En stock'),
            ('LOT-PHARMA-002-2601', 12, (today - timedelta(days=90)).isoformat(), (today + timedelta(days=275)).isoformat(), 5, 'CMD-2026-0001', 1200, 400, 400, 'En stock'),
            ('LOT-PHARMA-002-2602', 12, (today - timedelta(days=15)).isoformat(), (today + timedelta(days=350)).isoformat(), 5, 'CMD-2026-0007', 1220, 450, 450, 'En stock'),
            ('LOT-PHARMA-003-2601', 13, (today - timedelta(days=45)).isoformat(), (today + timedelta(days=320)).isoformat(), 5, 'CMD-2026-0001', 1800, 420, 420, 'En stock'),
        ])

        # ALERTES EXEMPLES
        c.executemany("""INSERT INTO alertes (type_alerte, produit_id, message, priorite, statut)
            VALUES (?, ?, ?, ?, ?)""", [
            ('Stock bas', 1, 'Stock bas : Câble USB-C 2m (500 unités, seuil 50)', 'Normale', 'Active'),
            ('Stock bas', 17, 'Stock bas : Marteau 500g (85 unités, seuil 20)', 'Normale', 'Active'),
            ('Stock bas', 20, 'Stock bas : Peinture blanche 20L (65 unités, seuil 15)', 'Haute', 'Active'),
            ('Stock élevé', 11, 'Stock élevé : Paracétamol 500mg (1200 unités, max 5000)', 'Basse', 'Active'),
        ])

        # PARAMÈTRES
        c.executemany("INSERT INTO parametres (cle, valeur, description) VALUES (?, ?, ?)", [
            ('entreprise_nom', 'OMEGA STOCK', 'Nom de l\'entreprise'),
            ('entreprise_adresse', 'Zone Industrielle, Dakar', 'Adresse'),
            ('entreprise_telephone', '+221 33 800 00 00', 'Téléphone'),
            ('entreprise_email', 'stock@omega.sn', 'Email'),
            ('devise', 'FCFA', 'Devise'),
            ('tva_defaut', '18', 'TVA par défaut (%)'),
            ('methode_valorisation', 'PMP', 'Méthode de valorisation (PMP/FIFO)'),
            ('alerte_stock_bas', '1', 'Activer alertes stock bas'),
            ('alerte_peremption_jours', '30', 'Alerte péremption avant X jours'),
            ('inventaire_frequence', 'Trimestriel', 'Fréquence des inventaires'),
        ])

        conn.commit()
        print("[INIT] ✅ Données de démonstration insérées")

    conn.close()
    print("[INIT] ✅ Base de données stock prête")


if __name__ == "__main__":
    init_db()
