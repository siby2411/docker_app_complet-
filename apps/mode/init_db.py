

"""
🎨 Mode & Couture CEDEAO — Base de données
Créations · Clients · Mesures · Commandes · Tissus · Salons · Export UE
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = '/app/data/mode.db'


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
            role TEXT DEFAULT 'couturier',
            nom_complet TEXT,
            email TEXT,
            telephone TEXT,
            atelier TEXT,
            ville TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Ateliers / Maisons de couture ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ateliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            type TEXT,
            specialite TEXT,
            adresse TEXT,
            ville TEXT,
            region TEXT,
            telephone TEXT,
            email TEXT,
            responsable TEXT,
            site_web TEXT,
            instagram TEXT,
            note_moyenne REAL DEFAULT 0,
            nb_commandes INTEGER DEFAULT 0,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Catégories de créations ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            slug TEXT UNIQUE,
            icone TEXT,
            description TEXT,
            ordre INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    # ─── Créations / Modèles ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS creations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            atelier_id INTEGER,
            categorie_id INTEGER,
            nom TEXT NOT NULL,
            description TEXT,
            type TEXT,
            photo_url TEXT,
            prix_base REAL DEFAULT 0,
            prix_vente REAL DEFAULT 0,
            tissu_principal TEXT,
            temps_confection INTEGER DEFAULT 7,
            niveau TEXT,
            disponible INTEGER DEFAULT 1,
            note_moyenne REAL DEFAULT 0,
            nb_commandes INTEGER DEFAULT 0,
            qr_code TEXT,
            created_at TEXT,
            FOREIGN KEY(atelier_id) REFERENCES ateliers(id),
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
            ville TEXT,
            pays TEXT DEFAULT 'Sénégal',
            date_naissance TEXT,
            sexe TEXT,
            points_fidelite INTEGER DEFAULT 0,
            nb_commandes INTEGER DEFAULT 0,
            total_depense REAL DEFAULT 0,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Mesures clients (confection) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mesures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            nom_mesure TEXT,
            sexe TEXT,
            type_tenue TEXT,
            tour_tete REAL DEFAULT 0,
            tour_cou REAL DEFAULT 0,
            tour_poitrine REAL DEFAULT 0,
            tour_taille REAL DEFAULT 0,
            tour_hanches REAL DEFAULT 0,
            longueur_bras REAL DEFAULT 0,
            longueur_epaule REAL DEFAULT 0,
            tour_biceps REAL DEFAULT 0,
            longueur_totale REAL DEFAULT 0,
            longueur_jupe REAL DEFAULT 0,
            longueur_pantalon REAL DEFAULT 0,
            tour_cuisse REAL DEFAULT 0,
            tour_genou REAL DEFAULT 0,
            tour_mollet REAL DEFAULT 0,
            pointure_chaussure INTEGER DEFAULT 0,
            poids REAL DEFAULT 0,
            taille_cm REAL DEFAULT 0,
            notes TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    """)

    # ─── Commandes de confection ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS commandes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            client_id INTEGER,
            atelier_id INTEGER,
            creation_id INTEGER,
            mesure_id INTEGER,
            type TEXT DEFAULT 'sur_mesure',
            description TEXT,
            quantite INTEGER DEFAULT 1,
            montant_ht REAL DEFAULT 0,
            tva REAL DEFAULT 0,
            montant_ttc REAL DEFAULT 0,
            avance REAL DEFAULT 0,
            reste REAL DEFAULT 0,
            statut TEXT DEFAULT 'devis',
            urgence TEXT DEFAULT 'normale',
            date_commande TEXT,
            date_livraison_prevue TEXT,
            date_livraison_reelle TEXT,
            mode_paiement TEXT,
            notes TEXT,
            qr_code TEXT,
            created_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(atelier_id) REFERENCES ateliers(id),
            FOREIGN KEY(creation_id) REFERENCES creations(id),
            FOREIGN KEY(mesure_id) REFERENCES mesures(id)
        )
    """)

    # ─── Tissus & matières ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tissus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            type TEXT,
            couleur TEXT,
            motif TEXT,
            fournisseur TEXT,
            pays_origine TEXT,
            prix_metre REAL DEFAULT 0,
            quantite_metres REAL DEFAULT 0,
            seuil_alerte REAL DEFAULT 0,
            qualite TEXT,
            photo_url TEXT,
            statut TEXT DEFAULT 'disponible',
            created_at TEXT
        )
    """)

    # ─── Salons & Expositions ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS salons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            ville TEXT,
            pays TEXT,
            lieu TEXT,
            date_debut TEXT,
            date_fin TEXT,
            description TEXT,
            site_web TEXT,
            organisateur TEXT,
            contact TEXT,
            telephone TEXT,
            email TEXT,
            nb_stands_total INTEGER DEFAULT 0,
            nb_stands_dispo INTEGER DEFAULT 0,
            tarif_stand REAL DEFAULT 0,
            statut TEXT DEFAULT 'planifie',
            created_at TEXT
        )
    """)

    # ─── Stands réservés ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salon_id INTEGER,
            atelier_id INTEGER,
            numero_stand TEXT,
            superficie REAL DEFAULT 0,
            tarif REAL DEFAULT 0,
            statut TEXT DEFAULT 'reserve',
            date_reservation TEXT,
            created_at TEXT,
            FOREIGN KEY(salon_id) REFERENCES salons(id),
            FOREIGN KEY(atelier_id) REFERENCES ateliers(id)
        )
    """)

    # ─── Billets salon ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS billets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            salon_id INTEGER,
            client_id INTEGER,
            type_billet TEXT,
            prix REAL DEFAULT 0,
            date_achat TEXT,
            qr_code TEXT,
            statut TEXT DEFAULT 'valide',
            created_at TEXT,
            FOREIGN KEY(salon_id) REFERENCES salons(id),
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    """)

    # ─── Livraisons ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS livraisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            commande_id INTEGER,
            type TEXT,
            adresse_livraison TEXT,
            ville TEXT,
            pays TEXT DEFAULT 'Sénégal',
            transporteur TEXT,
            numero_suivi TEXT,
            date_expedition TEXT,
            date_livraison_prevue TEXT,
            date_livraison_reelle TEXT,
            statut TEXT DEFAULT 'prepare',
            frais_livraison REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(commande_id) REFERENCES commandes(id)
        )
    """)

    # ─── Paiements mobile ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commande_id INTEGER,
            client_id INTEGER,
            operateur TEXT,
            telephone TEXT,
            montant REAL DEFAULT 0,
            reference TEXT,
            type TEXT DEFAULT 'acompte',
            statut TEXT DEFAULT 'en_attente',
            date_paiement TEXT,
            created_at TEXT,
            FOREIGN KEY(commande_id) REFERENCES commandes(id),
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    """)

    # ─── Export UE ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            commande_id INTEGER,
            destination TEXT,
            pays TEXT,
            valeur_fcfa REAL DEFAULT 0,
            devise TEXT DEFAULT 'EUR',
            valeur_devise REAL DEFAULT 0,
            certificat_origine INTEGER DEFAULT 0,
            certificat_ue INTEGER DEFAULT 0,
            certificat_usa INTEGER DEFAULT 0,
            num_douane TEXT,
            statut TEXT DEFAULT 'en_preparation',
            date_export TEXT,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(commande_id) REFERENCES commandes(id)
        )
    """)

    # ─── Avis clients ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS avis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            atelier_id INTEGER,
            commande_id INTEGER,
            note INTEGER DEFAULT 5,
            commentaire TEXT,
            date_avis TEXT,
            created_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(atelier_id) REFERENCES ateliers(id)
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
        "CREATE INDEX IF NOT EXISTS idx_creations_atelier ON creations(atelier_id)",
        "CREATE INDEX IF NOT EXISTS idx_creations_categorie ON creations(categorie_id)",
        "CREATE INDEX IF NOT EXISTS idx_commandes_statut ON commandes(statut)",
        "CREATE INDEX IF NOT EXISTS idx_commandes_client ON commandes(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_mesures_client ON mesures(client_id)",
    ]:
        try:
            cur.execute(idx)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # TRIGGERS
    # ═══════════════════════════════════════════════════════

    # Trigger 1 : code atelier auto
    cur.execute("DROP TRIGGER IF EXISTS trg_atelier_code")
    cur.execute("""
        CREATE TRIGGER trg_atelier_code
        AFTER INSERT ON ateliers
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE ateliers SET
                code = 'ATL-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 2 : code création auto + QR
    cur.execute("DROP TRIGGER IF EXISTS trg_creation_code")
    cur.execute("""
        CREATE TRIGGER trg_creation_code
        AFTER INSERT ON creations
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE creations SET
                code = 'CREA-' || substr('00000' || NEW.id, -5),
                qr_code = 'MODE|CREA|' || NEW.id
            WHERE id = NEW.id;
        END
    """)

    # Trigger 3 : numéro commande auto + QR
    cur.execute("DROP TRIGGER IF EXISTS trg_commande_numero")
    cur.execute("""
        CREATE TRIGGER trg_commande_numero
        AFTER INSERT ON commandes
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE commandes SET
                numero = 'CMD-' || strftime('%Y%m%d', 'now') || '-' || substr('0000' || NEW.id, -4),
                qr_code = 'MODE|CMD|' || NEW.id
            WHERE id = NEW.id;
        END
    """)

    # Trigger 4 : numéro billet auto + QR
    cur.execute("DROP TRIGGER IF EXISTS trg_billet_numero")
    cur.execute("""
        CREATE TRIGGER trg_billet_numero
        AFTER INSERT ON billets
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE billets SET
                numero = 'BIL-' || strftime('%Y%m%d', 'now') || '-' || substr('0000' || NEW.id, -4),
                qr_code = 'MODE|BIL|' || NEW.id
            WHERE id = NEW.id;
        END
    """)

    # Trigger 5 : MAJ client après commande livrée
    cur.execute("DROP TRIGGER IF EXISTS trg_commande_client")
    cur.execute("""
        CREATE TRIGGER trg_commande_client
        AFTER UPDATE OF statut ON commandes
        FOR EACH ROW
        WHEN NEW.statut = 'livree' AND OLD.statut != 'livree' AND NEW.client_id IS NOT NULL
        BEGIN
            UPDATE clients SET
                nb_commandes = nb_commandes + 1,
                total_depense = total_depense + NEW.montant_ttc,
                points_fidelite = points_fidelite + CAST(NEW.montant_ttc / 1000 AS INTEGER)
            WHERE id = NEW.client_id;
        END
    """)

    conn.commit()
    conn.close()
    print("[INIT] ✅ Base Mode & Couture prête")


def seed_demo():
    """Génère des données démo si base vide."""
    conn = get_conn()
    cur = conn.cursor()

    from werkzeug.security import generate_password_hash

    # ─── Users ───
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        users = [
            ('admin', 'admin123', 'admin', 'Administrateur', 'admin@mode.sn', '+221 77 000 00 00', 'OMEGA Mode'),
            ('atelier1', 'mode123', 'couturier', 'Aïssatou Diop', 'aissatou@mode.sn', '+221 77 111 11 11', 'Atelier Aïssatou'),
            ('atelier2', 'mode123', 'couturier', 'Moussa Ndiaye', 'moussa@mode.sn', '+221 77 222 22 22', 'Maison Moussa'),
            ('atelier3', 'mode123', 'couturier', 'Fatou Sow', 'fatou@mode.sn', '+221 77 333 33 33', 'Créations Fatou'),
            ('organisateur', 'org123', 'organisateur', 'Salon Dakar Fashion', 'contact@dfw.sn', '+221 77 444 44 44', 'DFW'),
        ]
        for u in users:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, nom_complet, email, telephone, atelier, actif, created_at)
                VALUES (?,?,?,?,?,?,?,1,?)
            """, (u[0], generate_password_hash(u[1]), u[2], u[3], u[4], u[5], u[6], datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(users)} utilisateurs créés")

    # ─── Ateliers ───
    cur.execute("SELECT COUNT(*) FROM ateliers")
    if cur.fetchone()[0] == 0:
        ateliers = [
            ('Atelier Aïssatou', 'Haute couture', 'Boubous, robes de soirée', 'Médina', 'Dakar', 'Dakar', '+221 77 111 11 11'),
            ('Maison Moussa', 'Costume', 'Costumes homme, smokings', 'Plateau', 'Dakar', 'Dakar', '+221 77 222 22 22'),
            ('Créations Fatou', 'Prêt-à-porter', 'Robes, jupes, tops', 'Yoff', 'Dakar', 'Dakar', '+221 77 333 33 33'),
            ('Atelier Wax Design', 'Wax & Bogolan', 'Tenues traditionnelles', 'Thiès Centre', 'Thiès', 'Thiès', '+221 77 444 44 44'),
            ('Ziguinchor Couture', 'Traditionnel', 'Boubous brodés', 'Ziguinchor', 'Ziguinchor', 'Ziguinchor', '+221 77 555 55 55'),
            ('Saint-Louis Elegance', 'Mariage', 'Robes de mariée, tenues', 'Île Saint-Louis', 'Saint-Louis', 'Saint-Louis', '+221 77 666 66 66'),
        ]
        for a in ateliers:
            cur.execute("""
                INSERT INTO ateliers (code, nom, type, specialite, adresse, ville, region, telephone,
                                        note_moyenne, nb_commandes, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,0, 'actif', ?)
            """, (None, a[0], a[1], a[2], a[3], a[4], a[5], a[6],
                  round(random.uniform(4.0, 5.0), 1),
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(ateliers)} ateliers créés")

    cur.execute("SELECT id FROM ateliers")
    atelier_ids = [r[0] for r in cur.fetchall()]

    # ─── Catégories ───
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        cats = [
            ('Boubous', 'boubous', '👘', 'Tenues traditionnelles sénégalaises'),
            ('Costumes', 'costumes', '🤵', 'Costumes homme, smokings'),
            ('Robes', 'robes', '👗', 'Robes de soirée, cocktail'),
            ('Jupes', 'jupes', '👚', 'Jupes, ensembles'),
            ('Tenues Wax', 'wax', '🧵', 'Tenues en tissu wax'),
            ('Bogolan', 'bogolan', '🎨', 'Créations en bogolan malien'),
            ('Mariage', 'mariage', '💍', 'Robes de mariée, tenues de cérémonie'),
            ('Accessoires', 'accessoires', '👒', 'Sacs, chapeaux, bijoux'),
        ]
        for i, c in enumerate(cats):
            cur.execute("""
                INSERT INTO categories (nom, slug, icone, description, ordre, created_at)
                VALUES (?,?,?,?,?,?)
            """, (c[0], c[1], c[2], c[3], i + 1, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(cats)} catégories créées")

    cur.execute("SELECT id FROM categories")
    cat_ids = [r[0] for r in cur.fetchall()]

    # ─── Créations ───
    cur.execute("SELECT COUNT(*) FROM creations")
    if cur.fetchone()[0] == 0:
        creations = [
            ('Boubou brodé homme', 'Boubou traditionnel en bazin riche', 'boubou', 45000, 75000, 'Bazin riche', 'fr,wo'),
            ('Boubou femme wax', 'Boubou moderne en wax hollandais', 'boubou', 35000, 60000, 'Wax hollandais', 'fr,wo'),
            ('Costume 3 pièces', 'Costume classique homme', 'costume', 85000, 150000, 'Laine', 'fr,en'),
            ('Robe de soirée', 'Robe longue pour cérémonie', 'robe', 55000, 95000, 'Satin', 'fr'),
            ('Robe cocktail', 'Robe courte élégante', 'robe', 40000, 70000, 'Soie', 'fr'),
            ('Jupe wax', 'Jupe portefeuille en wax', 'jupe', 25000, 45000, 'Wax', 'fr'),
            ('Robe de mariée', 'Robe de mariée sur mesure', 'robe_mariage', 150000, 350000, 'Dentelle, satin', 'fr,en'),
            ('Ensemble bogolan', 'Robe + foulard en bogolan', 'bogolan', 45000, 80000, 'Bogolan', 'fr,wo'),
            ('Sac en wax', 'Sac à main artisanal', 'accessoire', 15000, 25000, 'Wax', 'fr'),
            ('Chapeau bogolan', 'Chapeau traditionnel', 'accessoire', 8000, 15000, 'Bogolan', 'fr'),
            ('Smoking homme', 'Smoking classique noir', 'costume', 120000, 220000, 'Laine', 'fr,en'),
            ('Robe longue wax', 'Robe longue moderne wax', 'robe', 45000, 75000, 'Wax', 'fr,wo'),
        ]
        for c in creations:
            cur.execute("""
                INSERT INTO creations (code, atelier_id, categorie_id, nom, description, type,
                                         prix_base, prix_vente, tissu_principal, temps_confection,
                                         disponible, note_moyenne, nb_commandes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,1,?,0,?)
            """, (None, random.choice(atelier_ids), random.choice(cat_ids),
                  c[0], c[1], c[2], c[3], c[4], c[5],
                  random.randint(5, 21),
                  round(random.uniform(4.2, 5.0), 1),
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(creations)} créations créées")

    cur.execute("SELECT id FROM creations")
    creation_ids = [r[0] for r in cur.fetchall()]

    # ─── Clients ───
    cur.execute("SELECT COUNT(*) FROM clients")
    if cur.fetchone()[0] == 0:
        prenoms_h = ['Moussa', 'Amadou', 'Ibrahima', 'Cheikh', 'Ousmane']
        prenoms_f = ['Fatou', 'Awa', 'Aminata', 'Mariama', 'Aïssatou']
        noms = ['Diop', 'Ndiaye', 'Sall', 'Fall', 'Ba', 'Diallo', 'Sow']
        villes = ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Mbour']
        pays_list = ['Sénégal', 'Sénégal', 'Sénégal', 'France', 'Belgique', 'USA', 'Italie']

        for i in range(40):
            sexe = random.choice(['M', 'F'])
            prenom = random.choice(prenoms_h if sexe == 'M' else prenoms_f)
            nom = random.choice(noms)
            tel = f'+221 77 {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}'

            cur.execute("""
                INSERT INTO clients (code, nom, prenom, telephone, email, adresse, ville,
                                       pays, sexe, points_fidelite, nb_commandes, total_depense,
                                       statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,0,0, 'actif', ?)
            """, (None, nom, prenom, tel,
                  f'{prenom.lower()}.{nom.lower()}@email.sn',
                  f'Quartier {random.choice(["Médina", "Plateau", "Yoff", "Almadies"])}',
                  random.choice(villes),
                  random.choice(pays_list),
                  sexe,
                  random.randint(0, 300),
                  datetime.now().isoformat()))
        print("[SEED] ✅ 40 clients créés")

    cur.execute("SELECT id FROM clients")
    client_ids = [r[0] for r in cur.fetchall()]

    # ─── Mesures ───
    cur.execute("SELECT COUNT(*) FROM mesures")
    if cur.fetchone()[0] == 0:
        n = 0
        for cid in random.sample(client_ids, 25):
            cur.execute("SELECT sexe FROM clients WHERE id=?", (cid,))
            r = cur.fetchone()
            sexe = r['sexe'] if r else 'M'

            if sexe == 'F':
                cur.execute("""
                    INSERT INTO mesures (client_id, nom_mesure, sexe, type_tenue,
                                           tour_tete, tour_cou, tour_poitrine, tour_taille,
                                           tour_hanches, longueur_bras, longueur_epaule,
                                           longueur_totale, tour_cuisse, poids, taille_cm,
                                           actif, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)
                """, (cid, 'Tenue femme principale', 'F', 'boubou',
                      round(random.uniform(54, 60), 1), round(random.uniform(32, 38), 1),
                      round(random.uniform(85, 110), 1), round(random.uniform(70, 95), 1),
                      round(random.uniform(90, 115), 1), round(random.uniform(55, 65), 1),
                      round(random.uniform(35, 42), 1), round(random.uniform(140, 175), 1),
                      round(random.uniform(50, 65), 1), round(random.uniform(50, 85), 1),
                      round(random.uniform(155, 175), 1),
                      datetime.now().isoformat()))
            else:
                cur.execute("""
                    INSERT INTO mesures (client_id, nom_mesure, sexe, type_tenue,
                                           tour_tete, tour_cou, tour_poitrine, tour_taille,
                                           longueur_bras, longueur_epaule, longueur_totale,
                                           longueur_pantalon, tour_cuisse, tour_genou,
                                           poids, taille_cm, actif, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)
                """, (cid, 'Costume homme', 'M', 'costume',
                      round(random.uniform(56, 62), 1), round(random.uniform(38, 44), 1),
                      round(random.uniform(95, 115), 1), round(random.uniform(78, 95), 1),
                      round(random.uniform(60, 68), 1), round(random.uniform(42, 48), 1),
                      round(random.uniform(165, 185), 1), round(random.uniform(95, 110), 1),
                      round(random.uniform(55, 68), 1), round(random.uniform(38, 45), 1),
                      round(random.uniform(65, 95), 1), round(random.uniform(165, 190), 1),
                      datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} mesures clients créées")

    # ─── Tissus ───
    cur.execute("SELECT COUNT(*) FROM tissus")
    if cur.fetchone()[0] == 0:
        tissus = [
            ('Wax hollandais', 'wax', 'multicolore', 'motif floral', 8500),
            ('Bazin riche', 'bazin', 'bleu', 'uni', 15000),
            ('Bogolan', 'bogolan', 'marron', 'traditionnel', 6500),
            ('Satin duchesse', 'satin', 'blanc', 'uni', 12000),
            ('Soie naturelle', 'soie', 'rouge', 'uni', 20000),
            ('Dentelle française', 'dentelle', 'ivoire', 'floral', 35000),
            ('Laine vierge', 'laine', 'noir', 'uni', 18000),
            ('Coton bio', 'coton', 'écru', 'uni', 5500),
        ]
        for t in tissus:
            cur.execute("""
                INSERT INTO tissus (code, nom, type, couleur, motif, prix_metre,
                                      quantite_metres, seuil_alerte, qualite, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?, 'disponible', ?)
            """, (None, t[0], t[1], t[2], t[3], t[4],
                  random.randint(20, 200),
                  random.randint(5, 20),
                  random.choice(['Premium', 'Standard', 'Luxe']),
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(tissus)} tissus créés")

    # ─── Commandes ───
    cur.execute("SELECT COUNT(*) FROM commandes")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM mesures")
        mesure_rows = cur.fetchall()
        mesure_ids = [r[0] for r in mesure_rows]

        statuts = ['devis', 'confirmee', 'en_coupe', 'en_couture', 'finition', 'prete', 'livree', 'livree']

        n = 0
        for i in range(30):
            montant_ht = random.randint(25000, 350000)
            tva = montant_ht * 0.18
            montant_ttc = montant_ht + tva
            avance = montant_ttc * random.choice([0, 0.3, 0.5, 0.7])
            date_cmd = datetime.now() - timedelta(days=random.randint(0, 60))
            date_liv = date_cmd + timedelta(days=random.randint(7, 30))

            cur.execute("""
                INSERT INTO commandes (numero, client_id, atelier_id, creation_id, mesure_id,
                                         type, description, quantite, montant_ht, tva, montant_ttc,
                                         avance, reste, statut, urgence, date_commande,
                                         date_livraison_prevue, mode_paiement, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None,
                  random.choice(client_ids),
                  random.choice(atelier_ids),
                  random.choice(creation_ids),
                  random.choice(mesure_ids) if mesure_ids else None,
                  random.choice(['sur_mesure', 'pret_a_porter']),
                  'Commande de confection',
                  random.randint(1, 3),
                  montant_ht, tva, montant_ttc,
                  avance, montant_ttc - avance,
                  random.choice(statuts),
                  random.choice(['normale', 'normale', 'urgente']),
                  date_cmd.strftime('%Y-%m-%d'),
                  date_liv.strftime('%Y-%m-%d'),
                  random.choice(['mobile_money', 'especes', 'virement']),
                  datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} commandes créées")

    # ─── Salons ───
    cur.execute("SELECT COUNT(*) FROM salons")
    if cur.fetchone()[0] == 0:
        salons = [
            ('Dakar Fashion Week 2026', 'Dakar', 'Sénégal', 'Monument Renaissance',
             '2026-06-15', '2026-06-20', 50),
            ('Salon Mode Abidjan', 'Abidjan', "Côte d'Ivoire", 'Sofitel Hôtel Ivoire',
             '2026-07-10', '2026-07-14', 40),
            ('Lagos Fashion Week', 'Lagos', 'Nigeria', 'Federal Palace Hotel',
             '2026-10-20', '2026-10-25', 80),
            ('FESMAN Mode', 'Dakar', 'Sénégal', 'CICES',
             '2026-12-01', '2026-12-07', 60),
            ('Bamako Fashion Days', 'Bamako', 'Mali', 'Palais de la Culture',
             '2026-11-05', '2026-11-09', 35),
        ]
        for s in salons:
            cur.execute("""
                INSERT INTO salons (code, nom, ville, pays, lieu, date_debut, date_fin,
                                      description, site_web, nb_stands_total, nb_stands_dispo,
                                      tarif_stand, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'planifie', ?)
            """, (None, s[0], s[1], s[2], s[3], s[4], s[5],
                  'Salon international de mode et couture',
                  'https://www.' + s[0].lower().replace(' ', '') + '.sn',
                  s[6], s[6], 250000,
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(salons)} salons créés")

    conn.commit()
    conn.close()
    print("[SEED] ✅ Données démo Mode & Couture générées")


if __name__ == '__main__':
    init_db()
