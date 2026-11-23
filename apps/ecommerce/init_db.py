"""
Base de données E-Commerce Omega
16 tables : utilisateurs, catégories, marques, fournisseurs, produits,
clients, paniers, commandes, lignes, paiements, livraisons,
promotions, avis, wishlist, stock, audit
"""
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "/app/data/ecommerce.db"


def init_db():
    os.makedirs("/app/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    c = conn.cursor()

    # ==================== 1. CATÉGORIES ====================
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

    # ==================== 2. MARQUES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS marques (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT UNIQUE NOT NULL,
        description TEXT,
        pays_origine TEXT,
        site_web TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 3. FOURNISSEURS ====================
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
        delai_livraison_jours INTEGER DEFAULT 7,
        conditions_paiement TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 4. PRODUITS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS produits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description_courte TEXT,
        description_longue TEXT,
        categorie_id INTEGER,
        marque_id INTEGER,
        fournisseur_id INTEGER,
        prix_achat REAL DEFAULT 0,
        prix_vente REAL NOT NULL DEFAULT 0,
        prix_promo REAL,
        tva REAL DEFAULT 18,
        stock INTEGER DEFAULT 0,
        stock_alerte INTEGER DEFAULT 5,
        unite TEXT DEFAULT 'unité',
        poids_kg REAL DEFAULT 0,
        image_url TEXT,
        galerie TEXT,
        caracteristiques TEXT,
        tags TEXT,
        note_moyenne REAL DEFAULT 0,
        nb_avis INTEGER DEFAULT 0,
        nb_ventes INTEGER DEFAULT 0,
        vedette INTEGER DEFAULT 0,
        nouveau INTEGER DEFAULT 1,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (categorie_id) REFERENCES categories(id),
        FOREIGN KEY (marque_id) REFERENCES marques(id),
        FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id)
    )""")

    # ==================== 5. CLIENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        email TEXT,
        telephone TEXT NOT NULL,
        adresse TEXT,
        ville TEXT,
        region TEXT,
        pays TEXT DEFAULT 'Sénégal',
        date_naissance TEXT,
        genre TEXT,
        points_fidelite INTEGER DEFAULT 0,
        total_achats REAL DEFAULT 0,
        nb_commandes INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 6. PANIERS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS paniers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        produit_id INTEGER NOT NULL,
        quantite INTEGER NOT NULL DEFAULT 1,
        prix_unitaire REAL NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (produit_id) REFERENCES produits(id)
    )""")

    # ==================== 7. COMMANDES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS commandes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        client_id INTEGER NOT NULL,
        date_commande TEXT NOT NULL,
        sous_total REAL DEFAULT 0,
        remise REAL DEFAULT 0,
        code_promo TEXT,
        tva REAL DEFAULT 0,
        frais_livraison REAL DEFAULT 0,
        total REAL NOT NULL DEFAULT 0,
        montant_paye REAL DEFAULT 0,
        mode_paiement TEXT,
        statut TEXT DEFAULT 'En attente',
        statut_paiement TEXT DEFAULT 'Impayé',
        adresse_livraison TEXT,
        ville_livraison TEXT,
        telephone_livraison TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    # ==================== 8. LIGNES COMMANDE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS lignes_commande (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        commande_id INTEGER NOT NULL,
        produit_id INTEGER NOT NULL,
        nom_produit TEXT NOT NULL,
        quantite INTEGER NOT NULL,
        prix_unitaire REAL NOT NULL,
        total_ligne REAL NOT NULL,
        FOREIGN KEY (commande_id) REFERENCES commandes(id),
        FOREIGN KEY (produit_id) REFERENCES produits(id)
    )""")

    # ==================== 9. PAIEMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS paiements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        commande_id INTEGER NOT NULL,
        date_paiement TEXT NOT NULL,
        montant REAL NOT NULL,
        mode TEXT NOT NULL,
        reference TEXT,
        statut TEXT DEFAULT 'Validé',
        notes TEXT,
        FOREIGN KEY (commande_id) REFERENCES commandes(id)
    )""")

    # ==================== 10. LIVRAISONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS livraisons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        commande_id INTEGER NOT NULL,
        livreur_id INTEGER,
        numero_suivi TEXT UNIQUE,
        date_depart TEXT,
        date_arrivee TEXT,
        statut TEXT DEFAULT 'En préparation',
        adresse TEXT,
        destinataire TEXT,
        telephone TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (commande_id) REFERENCES commandes(id),
        FOREIGN KEY (livreur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 11. PROMOTIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS promotions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        type TEXT DEFAULT 'pourcentage',
        valeur REAL NOT NULL,
        montant_min REAL DEFAULT 0,
        date_debut TEXT NOT NULL,
        date_fin TEXT NOT NULL,
        limite_utilisation INTEGER,
        nb_utilisations INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 12. AVIS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS avis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER NOT NULL,
        client_id INTEGER NOT NULL,
        note INTEGER NOT NULL,
        titre TEXT,
        commentaire TEXT,
        approuve INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produit_id) REFERENCES produits(id),
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    # ==================== 13. WISHLIST ====================
    c.execute("""CREATE TABLE IF NOT EXISTS wishlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        produit_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (produit_id) REFERENCES produits(id)
    )""")

    # ==================== 14. MOUVEMENTS STOCK ====================
    c.execute("""CREATE TABLE IF NOT EXISTS mouvements_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER NOT NULL,
        type_mouvement TEXT NOT NULL,
        quantite INTEGER NOT NULL,
        stock_avant INTEGER,
        stock_apres INTEGER,
        motif TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produit_id) REFERENCES produits(id)
    )""")

    # ==================== 15. AUDIT LOG ====================
    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        ip TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 16. PARAMÈTRES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS parametres (
        cle TEXT PRIMARY KEY,
        valeur TEXT,
        description TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()

    # ==================== SEED ====================
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        print("[INIT] Insertion des données de démonstration...")

        # Catégories
        categories = [
            ('ELEC', 'Électronique', 'Smartphones, ordinateurs, accessoires', 'fa-mobile-screen', '#3b82f6'),
            ('MODE', 'Mode & Habillement', 'Vêtements hommes, femmes, enfants', 'fa-shirt', '#ec4899'),
            ('MAISON', 'Maison & Déco', 'Meubles, ustensiles, décoration', 'fa-couch', '#8b5cf6'),
            ('BEAUTE', 'Beauté & Santé', 'Cosmétiques, parfums, soins', 'fa-spa', '#f59e0b'),
            ('ALIM', 'Alimentation', 'Épicerie, boissons, produits locaux', 'fa-utensils', '#10b981'),
            ('SPORT', 'Sport & Loisirs', 'Équipements, vêtements sport', 'fa-futbol', '#ef4444'),
            ('BEBE', 'Bébé & Enfant', 'Puériculture, jouets, vêtements', 'fa-baby', '#06b6d4'),
            ('AUTO', 'Auto & Moto', 'Pièces, accessoires, entretien', 'fa-car', '#64748b'),
        ]
        c.executemany("""INSERT INTO categories (code, nom, description, icone, couleur)
            VALUES (?, ?, ?, ?, ?)""", categories)

        # Marques
        marques = [
            ('Samsung', 'Géant coréen électronique', 'Corée du Sud', 'samsung.com'),
            ('Apple', 'Innovation premium', 'USA', 'apple.com'),
            ('Xiaomi', 'Rapport qualité/prix', 'Chine', 'mi.com'),
            ('Adidas', 'Sportswear mondial', 'Allemagne', 'adidas.com'),
            ('Nike', 'Just Do It', 'USA', 'nike.com'),
            ('Dior', 'Luxe français', 'France', 'dior.com'),
            ('Nestlé', 'Alimentaire mondial', 'Suisse', 'nestle.com'),
            ('Sénéléc', 'Électronique local', 'Sénégal', 'senelec.sn'),
        ]
        c.executemany("INSERT INTO marques (nom, description, pays_origine, site_web) VALUES (?, ?, ?, ?)", marques)

        # Fournisseurs
        c.executemany("""INSERT INTO fournisseurs
            (code, nom, contact, telephone, email, adresse, ville, delai_livraison_jours)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('F001', 'Sénégalaise de Distribution', 'Mamadou Diallo', '+221 33 800 00 01', 'contact@sdeco.sn', 'Zone Industrielle', 'Dakar', 5),
            ('F002', 'Sahel Import Export', 'Fatou Ndiaye', '+221 33 800 00 02', 'info@sahelimpex.sn', 'Port de Dakar', 'Dakar', 15),
            ('F003', 'Touba Trading', 'Ibrahima Fall', '+221 33 800 00 03', 'touba@trading.sn', 'Touba', 'Diourbel', 7),
            ('F004', 'West Africa Import', 'Aminata Sow', '+221 33 800 00 04', 'wai@import.sn', 'Rufisque', 'Dakar', 10),
        ])

        # Produits
        produits = [
            ('SKU-001', 'Smartphone Samsung Galaxy A15 128Go', 'Écran 6.5", 4Go RAM, 128Go stockage, batterie 5000mAh', 1, 1, 1, 95000, 125000, 115000, 18, 45, 5, 1, 'Samsung A15'),
            ('SKU-002', 'iPhone 15 Pro 256Go', 'Puce A17 Pro, écran ProMotion 120Hz, appareil photo 48MP', 1, 2, 2, 650000, 850000, None, 18, 12, 3, 1, 'iPhone 15 Pro'),
            ('SKU-003', 'Xiaomi Redmi Note 13 128Go', 'Écran AMOLED 6.67", 8Go RAM, 128Go, 5000mAh', 1, 3, 1, 105000, 145000, 135000, 18, 38, 5, 1, 'Redmi Note 13'),
            ('SKU-004', 'T-shirt Nike Dri-FIT Homme', 'Coton respirant, séchage rapide, coupe sport', 2, 5, 3, 8500, 18000, 15000, 18, 120, 20, 0, ''),
            ('SKU-005', 'Baskets Adidas Ultraboost 22', 'Amorti Boost, tige Primeknit, semelle Continental', 2, 4, 3, 55000, 95000, None, 18, 25, 5, 0, ''),
            ('SKU-006', 'Robe Wax Africaine Premium', 'Tissu wax authentique, coupe moderne, fait main', 2, 8, 3, 12000, 28000, 24000, 18, 60, 10, 0, ''),
            ('SKU-007', 'Parfum Dior Sauvage 100ml', 'Fragrance boisée aromatique, tenue 8h', 4, 6, 2, 45000, 75000, None, 18, 20, 5, 0, ''),
            ('SKU-008', 'Huile de Baobab Bio 250ml', '100% naturelle, pressée à froid, riche en vitamines', 4, 8, 3, 3500, 8000, 6500, 18, 150, 20, 0, ''),
            ('SKU-009', 'Riz parfumé Gambiaka 25kg', 'Riz local parfumé, qualité supérieure', 5, 8, 4, 12000, 18000, None, 18, 200, 30, 0, ''),
            ('SKU-010', 'Huile végétale 5L', 'Huile de tournesol raffinée, bouteille 5L', 5, 7, 4, 5500, 8500, None, 18, 180, 30, 0, ''),
            ('SKU-011', 'Ballon de football Nike', 'Taille 5, cuir synthétique, homologué', 6, 5, 3, 12000, 25000, 22000, 18, 40, 10, 0, ''),
            ('SKU-012', 'Poussette bébé 3-en-1', 'Poussette + siège auto + nacelle, pliage compact', 7, 8, 2, 85000, 145000, None, 18, 15, 3, 0, ''),
        ]
        c.executemany("""INSERT INTO produits
            (sku, nom, description_courte, categorie_id, marque_id, fournisseur_id,
             prix_achat, prix_vente, prix_promo, tva, stock, stock_alerte, vedette, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", produits)

        # Clients
        clients = [
            (4, 'CLI-001', 'Diop', 'Aissatou', 'a.diop@email.sn', '+221 77 111 22 33', 'Médina', 'Dakar', 'Dakar', 'F', 150),
            (None, 'CLI-002', 'Sarr', 'Aliou', 'a.sarr@email.sn', '+221 77 222 33 44', 'Sacré-Cœur 3', 'Dakar', 'Dakar', 'M', 320),
            (None, 'CLI-003', 'Ba', 'Fatou', 'f.ba@email.sn', '+221 77 333 44 55', 'Thiès Escale', 'Thiès', 'Thiès', 'F', 85),
            (None, 'CLI-004', 'Ndiaye', 'Moussa', 'm.ndiaye@email.sn', '+221 77 444 55 66', 'Almadies', 'Dakar', 'Dakar', 'M', 540),
            (None, 'CLI-005', 'Sow', 'Khady', 'k.sow@email.sn', '+221 77 555 66 77', 'Point E', 'Dakar', 'Dakar', 'F', 210),
        ]
        c.executemany("""INSERT INTO clients
            (user_id, code, nom, prenom, email, telephone, adresse, ville, region, genre, points_fidelite)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", clients)

        # Promotions
        today = datetime.now().date()
        c.executemany("""INSERT INTO promotions
            (code, nom, description, type, valeur, montant_min, date_debut, date_fin, actif)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""", [
            ('BIENVENUE10', 'Bienvenue -10%', 'Première commande -10%', 'pourcentage', 10, 10000, today.isoformat(), (today + timedelta(days=90)).isoformat()),
            ('LIVRAISON0', 'Livraison gratuite', 'Livraison offerte dès 50 000 FCFA', 'livraison', 0, 50000, today.isoformat(), (today + timedelta(days=60)).isoformat()),
            ('PROMO2026', 'Promo 2026', 'Remise 15% sur tout', 'pourcentage', 15, 25000, today.isoformat(), (today + timedelta(days=30)).isoformat()),
        ])

        # Paramètres
        c.executemany("INSERT INTO parametres (cle, valeur, description) VALUES (?, ?, ?)", [
            ('site_nom', 'Omega Shop', 'Nom du site'),
            ('site_email', 'contact@omega-shop.sn', 'Email de contact'),
            ('site_telephone', '+221 33 800 00 00', 'Téléphone'),
            ('devise', 'FCFA', 'Devise'),
            ('tva_defaut', '18', 'TVA par défaut (%)'),
            ('frais_livraison_dakar', '2000', 'Frais livraison Dakar'),
            ('frais_livraison_region', '5000', 'Frais livraison régions'),
            ('seuil_livraison_gratuite', '50000', 'Seuil livraison gratuite'),
        ])

        conn.commit()
        print("[INIT] ✅ Données de démonstration insérées")

    conn.close()
    print("[INIT] ✅ Base de données e-commerce prête")


if __name__ == "__main__":
    init_db()
