

"""
🍽️ Restauration & Livraison — Base de données
Menu · Commandes · Livraison · Stocks · POS · Caissiers · Fidélité · IA
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = '/app/data/restaurant.db'


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()

    # ─── Utilisateurs ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'caissier',
            nom_complet TEXT,
            email TEXT,
            telephone TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Restaurants (multi-sites) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            type TEXT,
            adresse TEXT,
            ville TEXT DEFAULT 'Dakar',
            region TEXT,
            telephone TEXT,
            email TEXT,
            responsable TEXT,
            latitude REAL,
            longitude REAL,
            horaires TEXT,
            frais_livraison REAL DEFAULT 1000,
            commande_min_livraison REAL DEFAULT 5000,
            statut TEXT DEFAULT 'ouvert',
            created_at TEXT
        )
    """)

    # ─── Catégories de plats ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            slug TEXT UNIQUE,
            icone TEXT,
            ordre INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    # ─── Plats (menu) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS plats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            restaurant_id INTEGER,
            categorie_id INTEGER,
            nom TEXT NOT NULL,
            description TEXT,
            prix REAL DEFAULT 0,
            temps_preparation INTEGER DEFAULT 15,
            photo_url TEXT,
            disponible INTEGER DEFAULT 1,
            vegetarien INTEGER DEFAULT 0,
            epice INTEGER DEFAULT 0,
            note_moyenne REAL DEFAULT 0,
            nb_commandes INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(restaurant_id) REFERENCES restaurants(id),
            FOREIGN KEY(categorie_id) REFERENCES categories(id)
        )
    """)

    # ─── Clients ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            prenom TEXT,
            telephone TEXT UNIQUE,
            email TEXT,
            adresse TEXT,
            ville TEXT DEFAULT 'Dakar',
            points_fidelite INTEGER DEFAULT 0,
            niveau TEXT DEFAULT 'bronze',
            nb_commandes INTEGER DEFAULT 0,
            total_depense REAL DEFAULT 0,
            derniere_commande TEXT,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Livreurs ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS livreurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            prenom TEXT,
            telephone TEXT,
            vehicule TEXT,
            immatriculation TEXT,
            zone TEXT,
            statut TEXT DEFAULT 'disponible',
            note_moyenne REAL DEFAULT 0,
            nb_livraisons INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    # ─── Commandes ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS commandes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            restaurant_id INTEGER,
            client_id INTEGER,
            caissier_id INTEGER,
            livreur_id INTEGER,
            type TEXT DEFAULT 'sur_place',
            statut TEXT DEFAULT 'nouvelle',
            montant_sous_total REAL DEFAULT 0,
            frais_livraison REAL DEFAULT 0,
            remise REAL DEFAULT 0,
            montant_total REAL DEFAULT 0,
            mode_paiement TEXT,
            adresse_livraison TEXT,
            telephone_livraison TEXT,
            latitude REAL,
            longitude REAL,
            notes TEXT,
            date_commande TEXT,
            date_preparation TEXT,
            date_pret TEXT,
            date_livraison TEXT,
            temps_preparation INTEGER DEFAULT 0,
            session_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(restaurant_id) REFERENCES restaurants(id),
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(caissier_id) REFERENCES users(id),
            FOREIGN KEY(livreur_id) REFERENCES livreurs(id)
        )
    """)

    # ─── Lignes de commande ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS commande_lignes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commande_id INTEGER NOT NULL,
            plat_id INTEGER,
            nom_plat TEXT,
            prix_unitaire REAL DEFAULT 0,
            quantite INTEGER DEFAULT 1,
            montant REAL DEFAULT 0,
            notes TEXT,
            FOREIGN KEY(commande_id) REFERENCES commandes(id),
            FOREIGN KEY(plat_id) REFERENCES plats(id)
        )
    """)

    # ─── Paiements mobile ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commande_id INTEGER,
            operateur TEXT,
            telephone TEXT,
            montant REAL DEFAULT 0,
            reference TEXT,
            statut TEXT DEFAULT 'en_attente',
            date_transaction TEXT,
            created_at TEXT,
            FOREIGN KEY(commande_id) REFERENCES commandes(id)
        )
    """)

    # ─── Suivi livraison GPS ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS livraison_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commande_id INTEGER,
            livreur_id INTEGER,
            latitude REAL,
            longitude REAL,
            statut TEXT,
            date_position TEXT,
            created_at TEXT,
            FOREIGN KEY(commande_id) REFERENCES commandes(id),
            FOREIGN KEY(livreur_id) REFERENCES livreurs(id)
        )
    """)

    # ─── Ingrédients / Stocks ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            categorie TEXT,
            unite TEXT DEFAULT 'kg',
            quantite_stock REAL DEFAULT 0,
            seuil_alerte REAL DEFAULT 0,
            prix_unitaire REAL DEFAULT 0,
            fournisseur TEXT,
            date_peremption TEXT,
            emplacement TEXT,
            created_at TEXT
        )
    """)

    # ─── Recettes (plat ↔ ingrédients) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recettes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plat_id INTEGER NOT NULL,
            ingredient_id INTEGER NOT NULL,
            quantite REAL DEFAULT 0,
            FOREIGN KEY(plat_id) REFERENCES plats(id),
            FOREIGN KEY(ingredient_id) REFERENCES ingredients(id)
        )
    """)

    # ─── Sessions caissiers ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS caissiers_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caissier_id INTEGER NOT NULL,
            restaurant_id INTEGER NOT NULL,
            date_ouverture TEXT,
            date_fermeture TEXT,
            fonds_initial REAL DEFAULT 0,
            total_especes REAL DEFAULT 0,
            total_mobile_money REAL DEFAULT 0,
            total_carte REAL DEFAULT 0,
            total_ventes REAL DEFAULT 0,
            nb_commandes INTEGER DEFAULT 0,
            montant_compte REAL DEFAULT 0,
            ecart REAL DEFAULT 0,
            statut TEXT DEFAULT 'ouverte',
            notes_ouverture TEXT,
            notes_fermeture TEXT,
            created_at TEXT,
            FOREIGN KEY(caissier_id) REFERENCES users(id),
            FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
        )
    """)

    # ─── Paiements caissiers (versement gérant) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS caissiers_paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            caissier_id INTEGER,
            montant REAL DEFAULT 0,
            mode TEXT,
            reference TEXT,
            statut TEXT DEFAULT 'valide',
            recu_par INTEGER,
            date_paiement TEXT,
            created_at TEXT,
            FOREIGN KEY(session_id) REFERENCES caissiers_sessions(id),
            FOREIGN KEY(caissier_id) REFERENCES users(id)
        )
    """)

    # ─── Avis clients ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS avis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            commande_id INTEGER,
            plat_id INTEGER,
            note INTEGER DEFAULT 5,
            commentaire TEXT,
            date_avis TEXT,
            created_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(commande_id) REFERENCES commandes(id),
            FOREIGN KEY(plat_id) REFERENCES plats(id)
        )
    """)

    # ─── Fidélité / Récompenses ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fidelite_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            commande_id INTEGER,
            type TEXT,
            points INTEGER DEFAULT 0,
            description TEXT,
            date_transaction TEXT,
            created_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(commande_id) REFERENCES commandes(id)
        )
    """)

    # ─── Recommandations IA ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ia_recommandations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            plat_id INTEGER,
            score REAL DEFAULT 0,
            raison TEXT,
            vue INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(plat_id) REFERENCES plats(id)
        )
    """)

    # ─── Audit ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            entity TEXT,
            entity_id INTEGER,
            details TEXT,
            ip TEXT,
            created_at TEXT
        )
    """)

    # ─── Index ───
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_plats_categorie ON plats(categorie_id)",
        "CREATE INDEX IF NOT EXISTS idx_commandes_statut ON commandes(statut)",
        "CREATE INDEX IF NOT EXISTS idx_commandes_session ON commandes(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_clients_tel ON clients(telephone)",
    ]:
        try:
            cur.execute(idx)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # TRIGGERS
    # ═══════════════════════════════════════════════════════

    # Trigger 1 : numéro commande auto
    cur.execute("DROP TRIGGER IF EXISTS trg_commande_numero")
    cur.execute("""
        CREATE TRIGGER trg_commande_numero
        AFTER INSERT ON commandes
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE commandes SET
                numero = 'CMD-' || strftime('%Y%m%d', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 2 : code client auto + niveau
    cur.execute("DROP TRIGGER IF EXISTS trg_client_code")
    cur.execute("""
        CREATE TRIGGER trg_client_code
        AFTER INSERT ON clients
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE clients SET
                code = 'CLI-' || substr('00000' || NEW.id, -5)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 3 : MAJ client après commande
    cur.execute("DROP TRIGGER IF EXISTS trg_commande_client")
    cur.execute("""
        CREATE TRIGGER trg_commande_client
        AFTER UPDATE OF statut ON commandes
        FOR EACH ROW
        WHEN NEW.statut = 'livree' AND OLD.statut != 'livree' AND NEW.client_id IS NOT NULL
        BEGIN
            UPDATE clients SET
                nb_commandes = nb_commandes + 1,
                total_depense = total_depense + NEW.montant_total,
                derniere_commande = datetime('now'),
                points_fidelite = points_fidelite + CAST(NEW.montant_total / 1000 AS INTEGER)
            WHERE id = NEW.client_id;
        END
    """)

    # Trigger 4 : MAJ session caissier après commande payée
    cur.execute("DROP TRIGGER IF EXISTS trg_commande_session")
    cur.execute("""
        CREATE TRIGGER trg_commande_session
        AFTER INSERT ON commandes
        FOR EACH ROW
        WHEN NEW.session_id IS NOT NULL AND NEW.montant_total > 0
        BEGIN
            UPDATE caissiers_sessions SET
                total_ventes = total_ventes + NEW.montant_total,
                nb_commandes = nb_commandes + 1,
                total_especes = CASE WHEN NEW.mode_paiement='especes' THEN total_especes + NEW.montant_total ELSE total_especes END,
                total_mobile_money = CASE WHEN NEW.mode_paiement='mobile_money' THEN total_mobile_money + NEW.montant_total ELSE total_mobile_money END,
                total_carte = CASE WHEN NEW.mode_paiement='carte' THEN total_carte + NEW.montant_total ELSE total_carte END
            WHERE id = NEW.session_id;
        END
    """)

    # Trigger 5 : MAJ stock après commande livrée
    cur.execute("DROP TRIGGER IF EXISTS trg_stock_commande")
    cur.execute("""
        CREATE TRIGGER trg_stock_commande
        AFTER INSERT ON commande_lignes
        FOR EACH ROW
        BEGIN
            UPDATE ingredients SET
                quantite_stock = quantite_stock - (
                    SELECT COALESCE(r.quantite * NEW.quantite, 0)
                    FROM recettes r WHERE r.plat_id = NEW.plat_id LIMIT 1
                )
            WHERE id IN (
                SELECT ingredient_id FROM recettes WHERE plat_id = NEW.plat_id
            );
        END
    """)

    conn.commit()
    conn.close()
    print("[INIT] ✅ Base Restauration prête")


def seed_demo():
    """Génère des données démo si base vide."""
    conn = get_conn()
    cur = conn.cursor()

    from werkzeug.security import generate_password_hash

    # ─── Users ───
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        users = [
            ('admin', 'admin123', 'admin', 'Administrateur', 'admin@resto.sn', '+221 77 000 00 00'),
            ('gerant', 'gerant123', 'gerant', 'Fatou Ndiaye', 'gerant@resto.sn', '+221 77 111 11 11'),
            ('caissier1', 'caisse123', 'caissier', 'Moussa Diop', 'caisse1@resto.sn', '+221 77 222 22 22'),
            ('caissier2', 'caisse123', 'caissier', 'Awa Fall', 'caisse2@resto.sn', '+221 77 333 33 33'),
            ('caissier3', 'caisse123', 'caissier', 'Ousmane Ba', 'caisse3@resto.sn', '+221 77 444 44 44'),
        ]
        for u in users:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, nom_complet, email, telephone, actif, created_at)
                VALUES (?,?,?,?,?,?,1,?)
            """, (u[0], generate_password_hash(u[1]), u[2], u[3], u[4], u[5], datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(users)} utilisateurs créés")

    cur.execute("SELECT id FROM users WHERE role='caissier'")
    caissier_ids = [r[0] for r in cur.fetchall()]

    # ─── Restaurants ───
    cur.execute("SELECT COUNT(*) FROM restaurants")
    if cur.fetchone()[0] == 0:
        restaurants = [
            ('OMEGA Resto Dakar Plateau', 'Restaurant', 'Rue Carnot', 'Dakar', 'Dakar', '+221 33 821 00 01'),
            ('OMEGA Resto Almadies', 'Restaurant', 'Route des Almadies', 'Dakar', 'Dakar', '+221 33 820 00 02'),
            ('OMEGA Resto Thiès', 'Restaurant', 'Avenue LSS', 'Thiès', 'Thiès', '+221 33 951 00 03'),
        ]
        for r in restaurants:
            cur.execute("""
                INSERT INTO restaurants (code, nom, type, adresse, ville, region, telephone,
                                           latitude, longitude, horaires, frais_livraison,
                                           commande_min_livraison, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'ouvert', ?)
            """, (None, r[0], r[1], r[2], r[3], r[4], r[5],
                  14.6928, -17.4467, '10h - 23h', 1000, 5000,
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(restaurants)} restaurants créés")

    cur.execute("SELECT id FROM restaurants")
    resto_ids = [r[0] for r in cur.fetchall()]

    # ─── Catégories ───
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        cats = [
            ('Entrées', 'entrees', '🥗'),
            ('Plats principaux', 'plats', '🍛'),
            ('Grillades', 'grillades', '🍖'),
            ('Poissons', 'poissons', '🐟'),
            ('Fast-food', 'fastfood', '🍔'),
            ('Desserts', 'desserts', '🍰'),
            ('Boissons', 'boissons', '🥤'),
        ]
        for i, c in enumerate(cats):
            cur.execute("""
                INSERT INTO categories (nom, slug, icone, ordre, created_at)
                VALUES (?,?,?,?,?)
            """, (c[0], c[1], c[2], i+1, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(cats)} catégories créées")

    cur.execute("SELECT id FROM categories")
    cat_ids = [r[0] for r in cur.fetchall()]

    # ─── Plats (menu) ───
    cur.execute("SELECT COUNT(*) FROM plats")
    if cur.fetchone()[0] == 0:
        plats = [
            ('Thiéboudienne', 'Riz au poisson, légumes, tomate', 3500, 25),
            ('Yassa poulet', 'Poulet mariné aux oignons', 3000, 20),
            ('Mafé bœuf', 'Bœuf à la sauce arachide', 3500, 25),
            ('Dibi haché', 'Agneau grillé aux oignons', 4000, 20),
            ('Brochettes poulet', 'Poulet mariné grillé', 2500, 15),
            ('Poisson braisé', 'Poisson entier grillé', 4500, 25),
            ('Calamars frits', 'Calamars panés', 5000, 20),
            ('Salade niçoise', 'Salade composée', 2500, 10),
            ('Hamburger OMEGA', 'Bœuf, fromage, frites', 3500, 15),
            ('Pizza Margherita', 'Tomate, mozzarella, basilic', 4000, 20),
            ('Frites', 'Portion de frites', 1500, 8),
            ('Tiramisu', 'Dessert italien', 2500, 10),
            ('Glace 2 boules', 'Glace artisanale', 1500, 5),
            ('Jus bissap', 'Jus d\'hibiscus', 1000, 5),
            ('Jus gingembre', 'Jus de gingembre frais', 1000, 5),
            ('Coca-Cola 33cl', 'Boisson gazeuse', 800, 2),
            ('Eau minérale 50cl', 'Eau en bouteille', 500, 1),
            ('Café Touba', 'Café épicé traditionnel', 500, 3),
        ]
        for p in plats:
            cur.execute("""
                INSERT INTO plats (code, restaurant_id, categorie_id, nom, description,
                                     prix, temps_preparation, disponible, vegetarien,
                                     epice, note_moyenne, created_at)
                VALUES (?,?,?,?,?,?,?,1,?,?,?,?)
            """, (None, random.choice(resto_ids), random.choice(cat_ids),
                  p[0], p[1], p[2], p[3],
                  random.choice([0, 1]), random.choice([0, 1]),
                  round(random.uniform(4.0, 5.0), 1),
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(plats)} plats créés")

    # ─── Clients ───
    cur.execute("SELECT COUNT(*) FROM clients")
    if cur.fetchone()[0] == 0:
        noms = ['Diop', 'Ndiaye', 'Sall', 'Fall', 'Ba', 'Diallo', 'Sow', 'Sy', 'Faye', 'Gueye']
        prenoms_h = ['Moussa', 'Amadou', 'Ibrahima', 'Cheikh', 'Ousmane', 'Mamadou']
        prenoms_f = ['Fatou', 'Awa', 'Aminata', 'Mariama', 'Aïssatou', 'Ndèye']

        n = 0
        for i in range(40):
            sexe = random.choice(['M', 'F'])
            prenom = random.choice(prenoms_h if sexe == 'M' else prenoms_f)
            nom = random.choice(noms)
            tel = f'+221 77 {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}'

            cur.execute("""
                INSERT INTO clients (code, nom, prenom, telephone, email, adresse,
                                       ville, points_fidelite, niveau, nb_commandes,
                                       total_depense, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (None, nom, prenom, tel,
                  f'{prenom.lower()}.{nom.lower()}@email.sn',
                  f'Quartier {random.choice(["Médina", "Plateau", "Yoff", "Almadies"])}',
                  'Dakar',
                  random.randint(0, 500),
                  random.choice(['bronze', 'argent', 'or']),
                  0, 0,
                  datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} clients créés")

    cur.execute("SELECT id FROM clients")
    client_ids = [r[0] for r in cur.fetchall()]

    # ─── Livreurs ───
    cur.execute("SELECT COUNT(*) FROM livreurs")
    if cur.fetchone()[0] == 0:
        livreurs = [
            ('Amadou Sall', '+221 77 555 55 55', 'moto', 'DK-1234-M'),
            ('Ibrahima Ba', '+221 77 666 66 66', 'moto', 'DK-5678-M'),
            ('Moussa Diallo', '+221 77 777 77 77', 'scooter', 'DK-9012-S'),
            ('Cheikh Fall', '+221 77 888 88 88', 'moto', 'DK-3456-M'),
        ]
        for l in livreurs:
            cur.execute("""
                INSERT INTO livreurs (code, nom, telephone, vehicule, immatriculation,
                                        zone, statut, note_moyenne, nb_livraisons, created_at)
                VALUES (?,?,?,?,?,?, 'disponible', ?, 0, ?)
            """, (None, l[0], l[1], l[2], l[3],
                  random.choice(['Dakar Centre', 'Almadies', 'Yoff', 'Plateau']),
                  round(random.uniform(4.0, 5.0), 1),
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(livreurs)} livreurs créés")

    # ─── Ingrédients ───
    cur.execute("SELECT COUNT(*) FROM ingredients")
    if cur.fetchone()[0] == 0:
        ingredients = [
            ('Riz', 'kg', 50, 10, 600),
            ('Poisson', 'kg', 30, 10, 2500),
            ('Poulet', 'kg', 40, 10, 2000),
            ('Bœuf', 'kg', 25, 8, 3500),
            ('Agneau', 'kg', 20, 5, 4000),
            ('Tomate', 'kg', 30, 10, 1000),
            ('Oignon', 'kg', 40, 10, 800),
            ('Pomme de terre', 'kg', 50, 15, 700),
            ('Huile', 'L', 30, 10, 1500),
            ('Farine', 'kg', 25, 10, 800),
            ('Sucre', 'kg', 20, 5, 700),
            ('Lait', 'L', 15, 5, 1000),
            ('Fromage', 'kg', 10, 3, 5000),
            ('Œufs', 'unité', 100, 30, 100),
        ]
        for ing in ingredients:
            cur.execute("""
                INSERT INTO ingredients (code, nom, unite, quantite_stock, seuil_alerte,
                                           prix_unitaire, date_peremption, created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (None, ing[0], ing[1], ing[2], ing[3], ing[4],
                  (datetime.now() + timedelta(days=random.randint(5, 60))).strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(ingredients)} ingrédients créés")

    # ─── Session caissier démo ───
    cur.execute("SELECT COUNT(*) FROM caissiers_sessions")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM users WHERE role='caissier' LIMIT 1")
        u = cur.fetchone()
        if u:
            cur.execute("""
                INSERT INTO caissiers_sessions (caissier_id, restaurant_id, date_ouverture,
                                                  fonds_initial, statut, created_at)
                VALUES (?,?,?,?,'ouverte',?)
            """, (u[0], random.choice(resto_ids), datetime.now().isoformat(),
                  50000, datetime.now().isoformat()))
            print("[SEED] ✅ Session caissier démo ouverte")

    conn.commit()
    conn.close()
    print("[SEED] ✅ Données démo Restauration générées")


if __name__ == '__main__':
    init_db()
