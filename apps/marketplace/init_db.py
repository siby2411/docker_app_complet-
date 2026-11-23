

"""
🛒 Marketplace B2B — Initialisation base de données
Vendeurs · Produits · Commandes · Devis · Paiements · Avis
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = '/app/data/marketplace.db'


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()

    # ─── Users (acheteurs + vendeurs) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'acheteur',
            nom_complet TEXT,
            email TEXT,
            telephone TEXT,
            entreprise TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Vendeurs (entreprises) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendeurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            raison_sociale TEXT NOT NULL,
            secteur TEXT,
            description TEXT,
            contact_nom TEXT,
            telephone TEXT,
            email TEXT,
            adresse TEXT,
            ville TEXT,
            pays TEXT DEFAULT 'Sénégal',
            num_registre TEXT,
            note_moyenne REAL DEFAULT 0,
            nb_avis INTEGER DEFAULT 0,
            nb_ventes INTEGER DEFAULT 0,
            statut TEXT DEFAULT 'actif',
            user_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # ─── Catégories ───
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

    # ─── Produits ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS produits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            vendeur_id INTEGER NOT NULL,
            categorie_id INTEGER,
            nom TEXT NOT NULL,
            description TEXT,
            unite TEXT DEFAULT 'unité',
            prix_unitaire REAL DEFAULT 0,
            prix_min_commande INTEGER DEFAULT 1,
            stock INTEGER DEFAULT 0,
            photo_url TEXT,
            qr_code TEXT,
            statut TEXT DEFAULT 'actif',
            note_moyenne REAL DEFAULT 0,
            nb_ventes INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(vendeur_id) REFERENCES vendeurs(id),
            FOREIGN KEY(categorie_id) REFERENCES categories(id)
        )
    """)

    # ─── Demandes de devis (RFQ) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rfq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            acheteur_id INTEGER,
            categorie_id INTEGER,
            titre TEXT,
            description TEXT,
            quantite REAL DEFAULT 0,
            unite TEXT,
            date_limite TEXT,
            statut TEXT DEFAULT 'ouvert',
            created_at TEXT,
            FOREIGN KEY(acheteur_id) REFERENCES users(id),
            FOREIGN KEY(categorie_id) REFERENCES categories(id)
        )
    """)

    # ─── Offres sur RFQ ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rfq_offres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfq_id INTEGER NOT NULL,
            vendeur_id INTEGER NOT NULL,
            prix_unitaire REAL DEFAULT 0,
            montant_total REAL DEFAULT 0,
            delai_jours INTEGER DEFAULT 7,
            message TEXT,
            statut TEXT DEFAULT 'soumise',
            created_at TEXT,
            FOREIGN KEY(rfq_id) REFERENCES rfq(id),
            FOREIGN KEY(vendeur_id) REFERENCES vendeurs(id)
        )
    """)

    # ─── Commandes ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS commandes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            acheteur_id INTEGER,
            vendeur_id INTEGER,
            date_commande TEXT,
            montant_ht REAL DEFAULT 0,
            tva REAL DEFAULT 0,
            montant_ttc REAL DEFAULT 0,
            frais_livraison REAL DEFAULT 0,
            montant_total REAL DEFAULT 0,
            mode_paiement TEXT,
            adresse_livraison TEXT,
            ville_livraison TEXT,
            statut TEXT DEFAULT 'en_attente',
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(acheteur_id) REFERENCES users(id),
            FOREIGN KEY(vendeur_id) REFERENCES vendeurs(id)
        )
    """)

    # ─── Lignes de commande ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS commande_lignes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commande_id INTEGER NOT NULL,
            produit_id INTEGER,
            nom_produit TEXT,
            quantite REAL DEFAULT 0,
            prix_unitaire REAL DEFAULT 0,
            montant REAL DEFAULT 0,
            FOREIGN KEY(commande_id) REFERENCES commandes(id),
            FOREIGN KEY(produit_id) REFERENCES produits(id)
        )
    """)

    # ─── Paiements ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commande_id INTEGER,
            montant REAL DEFAULT 0,
            mode TEXT,
            reference TEXT,
            statut TEXT DEFAULT 'en_attente',
            date_paiement TEXT,
            created_at TEXT,
            FOREIGN KEY(commande_id) REFERENCES commandes(id)
        )
    """)

    # ─── Livraisons ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS livraisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commande_id INTEGER,
            numero_suivi TEXT UNIQUE,
            transporteur TEXT,
            date_expedition TEXT,
            date_livraison_prevue TEXT,
            date_livraison_reelle TEXT,
            statut TEXT DEFAULT 'prepare',
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(commande_id) REFERENCES commandes(id)
        )
    """)

    # ─── Avis / Évaluations ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS avis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendeur_id INTEGER,
            produit_id INTEGER,
            acheteur_id INTEGER,
            commande_id INTEGER,
            note INTEGER DEFAULT 5,
            commentaire TEXT,
            date_avis TEXT,
            created_at TEXT,
            FOREIGN KEY(vendeur_id) REFERENCES vendeurs(id),
            FOREIGN KEY(produit_id) REFERENCES produits(id),
            FOREIGN KEY(acheteur_id) REFERENCES users(id),
            FOREIGN KEY(commande_id) REFERENCES commandes(id)
        )
    """)

    # ─── Panier (temporaire) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS panier (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            produit_id INTEGER,
            quantite REAL DEFAULT 1,
            prix_unitaire REAL DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(produit_id) REFERENCES produits(id)
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
        "CREATE INDEX IF NOT EXISTS idx_produits_categorie ON produits(categorie_id)",
        "CREATE INDEX IF NOT EXISTS idx_produits_vendeur ON produits(vendeur_id)",
        "CREATE INDEX IF NOT EXISTS idx_commandes_acheteur ON commandes(acheteur_id)",
        "CREATE INDEX IF NOT EXISTS idx_commandes_vendeur ON commandes(vendeur_id)",
        "CREATE INDEX IF NOT EXISTS idx_avis_vendeur ON avis(vendeur_id)",
    ]:
        try:
            cur.execute(idx)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # TRIGGERS
    # ═══════════════════════════════════════════════════════

    # Trigger 1 : génération code vendeur
    cur.execute("DROP TRIGGER IF EXISTS trg_vendeur_code")
    cur.execute("""
        CREATE TRIGGER trg_vendeur_code
        AFTER INSERT ON vendeurs
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE vendeurs SET
                code = 'VND-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 2 : génération code produit + QR
    cur.execute("DROP TRIGGER IF EXISTS trg_produit_code")
    cur.execute("""
        CREATE TRIGGER trg_produit_code
        AFTER INSERT ON produits
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE produits SET
                code = 'PRD-' || substr('00000' || NEW.id, -5),
                qr_code = 'MKT|PRD|' || NEW.id
            WHERE id = NEW.id;
        END
    """)

    # Trigger 3 : génération numéro commande
    cur.execute("DROP TRIGGER IF EXISTS trg_commande_numero")
    cur.execute("""
        CREATE TRIGGER trg_commande_numero
        AFTER INSERT ON commandes
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE commandes SET
                numero = 'CMD-' || strftime('%Y%m', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 4 : MAJ note moyenne après avis
    cur.execute("DROP TRIGGER IF EXISTS trg_avis_maj_note")
    cur.execute("""
        CREATE TRIGGER trg_avis_maj_note
        AFTER INSERT ON avis
        FOR EACH ROW
        BEGIN
            UPDATE vendeurs SET
                note_moyenne = (
                    SELECT AVG(note) FROM avis WHERE vendeur_id = NEW.vendeur_id
                ),
                nb_avis = (
                    SELECT COUNT(*) FROM avis WHERE vendeur_id = NEW.vendeur_id
                )
            WHERE id = NEW.vendeur_id;
        END
    """)

    # Trigger 5 : MAJ nb_ventes vendeur après commande livrée
    cur.execute("DROP TRIGGER IF EXISTS trg_commande_livree")
    cur.execute("""
        CREATE TRIGGER trg_commande_livree
        AFTER UPDATE OF statut ON commandes
        FOR EACH ROW
        WHEN NEW.statut = 'livree' AND OLD.statut != 'livree'
        BEGIN
            UPDATE vendeurs SET
                nb_ventes = nb_ventes + 1
            WHERE id = NEW.vendeur_id;
        END
    """)

    conn.commit()
    conn.close()
    print("[INIT] ✅ Base Marketplace B2B prête")


def seed_demo():
    """Génère des données démo si base vide."""
    conn = get_conn()
    cur = conn.cursor()

    from werkzeug.security import generate_password_hash

    # ─── Users ───
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        users = [
            ('admin', 'admin123', 'admin', 'Administrateur', 'admin@marketplace.sn', '+221 77 000 00 00', 'OMEGA MARKETPLACE'),
            ('acheteur1', 'ach123', 'acheteur', 'Moussa Ndiaye', 'moussa@entreprise.sn', '+221 77 111 11 11', 'SONACOS SA'),
            ('acheteur2', 'ach123', 'acheteur', 'Fatou Sow', 'fatou@entreprise.sn', '+221 77 222 22 22', 'SENELEC'),
            ('vendeur1', 'vnd123', 'vendeur', 'Ibrahima Sall', 'ibrahima@fournisseur.sn', '+221 77 333 33 33', 'SENFER'),
            ('vendeur2', 'vnd123', 'vendeur', 'Awa Fall', 'awa@fournisseur.sn', '+221 77 444 44 44', 'SOCOCIM'),
            ('vendeur3', 'vnd123', 'vendeur', 'Ousmane Ba', 'ousmane@fournisseur.sn', '+221 77 555 55 55', 'SONATEL Business'),
        ]
        for u in users:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, nom_complet, email, telephone, entreprise, actif, created_at)
                VALUES (?,?,?,?,?,?,?,1,?)
            """, (u[0], generate_password_hash(u[1]), u[2], u[3], u[4], u[5], u[6], datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(users)} utilisateurs créés")

    # ─── Vendeurs ───
    cur.execute("SELECT COUNT(*) FROM vendeurs")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM users WHERE role='vendeur'")
        vendeur_user_ids = [r[0] for r in cur.fetchall()]

        vendeurs = [
            ('SENFER SA', 'Métallurgie', 'Ferraille et produits sidérurgiques', 'Ibrahima Sall', '+221 33 839 11 11', 'contact@senfer.sn', 'Zone industrielle', 'Dakar'),
            ('SOCOCIM Industries', 'Ciment', 'Production de ciment et matériaux', 'Awa Fall', '+221 33 957 00 00', 'contact@sococim.sn', 'Rufisque', 'Rufisque'),
            ('SONATEL Business', 'Télécoms', 'Solutions télécoms entreprises', 'Ousmane Ba', '+221 33 839 22 22', 'business@sonatel.sn', 'Route de Ouakam', 'Dakar'),
            ('SEDIMA Group', 'Agroalimentaire', 'Transformation agro-alimentaire', 'Moussa Diop', '+221 33 839 33 33', 'info@sedima.sn', 'Zone industrielle', 'Dakar'),
            ('SOSACO', 'Agrégats BTP', 'Sable, gravier, granulats', 'Cheikh Sow', '+221 33 839 44 44', 'contact@sosaco.sn', 'Route de Rufisque', 'Dakar'),
        ]
        for i, v in enumerate(vendeurs):
            uid = vendeur_user_ids[i] if i < len(vendeur_user_ids) else None
            cur.execute("""
                INSERT INTO vendeurs (code, raison_sociale, secteur, description, contact_nom,
                                       telephone, email, adresse, ville, pays, num_registre,
                                       note_moyenne, statut, user_id, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'actif', ?, ?)
            """, (None, v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], 'Sénégal',
                  f'RCCM-{i+1:05d}', round(random.uniform(3.5, 5.0), 1),
                  uid, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(vendeurs)} vendeurs créés")

    # ─── Catégories ───
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        categories = [
            ('Matériaux BTP', 'materiaux-btp', '🏗️', 'Ciment, fer, agrégats'),
            ('Agroalimentaire', 'agroalimentaire', '🌾', 'Produits agricoles et transformés'),
            ('Équipements', 'equipements', '⚙️', 'Machines et outillages'),
            ('Électronique', 'electronique', '💻', 'Informatique et télécoms'),
            ('Textile', 'textile', '👕', 'Vêtements et tissus'),
            ('Chimie', 'chimie', '🧪', 'Produits chimiques et industriels'),
        ]
        for i, cat in enumerate(categories):
            cur.execute("""
                INSERT INTO categories (nom, slug, icone, description, ordre, created_at)
                VALUES (?,?,?,?,?,?)
            """, (cat[0], cat[1], cat[2], cat[3], i+1, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(categories)} catégories créées")

    # ─── Produits ───
    cur.execute("SELECT COUNT(*) FROM produits")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM vendeurs")
        v_ids = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT id FROM categories")
        c_ids = [r[0] for r in cur.fetchall()]

        produits = [
            ('Ciment CPJ 42.5 - Sac 50kg', 'Ciment Portland', 'sac', 5500, 10),
            ('Fer à béton Ø12mm', 'Ferraille haute résistance', 'barre', 4500, 20),
            ('Fer à béton Ø16mm', 'Ferraille haute résistance', 'barre', 7000, 20),
            ('Gravier 15/25 - Camion 10T', 'Granulat calibré', 'camion', 220000, 1),
            ('Sable de rivière - Camion 10T', 'Sable lavé', 'camion', 180000, 1),
            ('Tôle bac acier 0.5mm', 'Couverture métallique', 'm2', 8500, 50),
            ('Huile d\'arachide 5L', 'Huile alimentaire', 'bidon', 6500, 10),
            ('Riz parfumé 50kg', 'Riz local', 'sac', 22000, 10),
            ('Laptop HP ProBook 450', 'Ordinateur portable', 'unité', 450000, 1),
            ('Switch réseau 24 ports', 'Switch Ethernet managed', 'unité', 180000, 1),
            ('Peinture acrylique 20L', 'Peinture intérieure', 'seau', 45000, 5),
            ('Câble électrique 2.5mm²', 'Câble cuivre', 'mètre', 850, 100),
        ]
        for p in produits:
            cur.execute("""
                INSERT INTO produits (code, vendeur_id, categorie_id, nom, description,
                                       unite, prix_unitaire, prix_min_commande, stock,
                                       statut, note_moyenne, created_at)
                VALUES (?,?,?,?,?,?,?,?,?, 'actif', ?, ?)
            """, (None, random.choice(v_ids), random.choice(c_ids),
                  p[0], p[1], p[2], p[3], p[4],
                  random.randint(50, 1000),
                  round(random.uniform(3.5, 5.0), 1),
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(produits)} produits créés")

    # ─── Commandes démo ───
    cur.execute("SELECT COUNT(*) FROM commandes")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM users WHERE role='acheteur'")
        acheteurs = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT id FROM vendeurs")
        vendeurs = [r[0] for r in cur.fetchall()]

        for i in range(15):
            montant_ht = random.randint(500000, 15000000)
            tva = montant_ht * 0.18
            frais = random.randint(0, 50000)
            total = montant_ht + tva + frais

            cur.execute("""
                INSERT INTO commandes
                (numero, acheteur_id, vendeur_id, date_commande, montant_ht, tva,
                 montant_ttc, frais_livraison, montant_total, mode_paiement,
                 adresse_livraison, ville_livraison, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None,
                  random.choice(acheteurs), random.choice(vendeurs),
                  (datetime.now() - timedelta(days=random.randint(0, 90))).strftime('%Y-%m-%d'),
                  montant_ht, tva, montant_ht + tva, frais, total,
                  random.choice(['mobile_money', 'virement', 'especes', 'sequestre']),
                  'Zone industrielle', 'Dakar',
                  random.choice(['en_attente', 'confirmee', 'expediee', 'livree', 'livree']),
                  datetime.now().isoformat()))
        print("[SEED] ✅ 15 commandes créées")

    # ─── RFQ ───
    cur.execute("SELECT COUNT(*) FROM rfq")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM users WHERE role='acheteur'")
        acheteurs = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT id FROM categories")
        c_ids = [r[0] for r in cur.fetchall()]

        rfq_titres = [
            'Recherche fournisseur ciment 500 sacs',
            'Achat fer à béton Ø12 - 1000 barres',
            'Fourniture gravier 50 camions',
            'Achat 20 laptops HP pour équipe',
            'Commande 100 m² tôle bac acier',
        ]
        for i, titre in enumerate(rfq_titres):
            cur.execute("""
                INSERT INTO rfq (numero, acheteur_id, categorie_id, titre, description,
                                  quantite, unite, date_limite, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?, 'ouvert', ?)
            """, (None, random.choice(acheteurs), random.choice(c_ids),
                  titre, 'Demande de prix détaillée',
                  random.randint(100, 1000), 'unité',
                  (datetime.now() + timedelta(days=random.randint(3, 15))).strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(rfq_titres)} RFQ créées")

    # ─── Avis ───
    cur.execute("SELECT COUNT(*) FROM avis")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM vendeurs")
        v_ids = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT id FROM users WHERE role='acheteur'")
        acheteurs = [r[0] for r in cur.fetchall()]

        for i in range(20):
            cur.execute("""
                INSERT INTO avis (vendeur_id, acheteur_id, note, commentaire, date_avis, created_at)
                VALUES (?,?,?,?,?,?)
            """, (random.choice(v_ids), random.choice(acheteurs),
                  random.randint(3, 5),
                  random.choice(['Livraison rapide, produits conformes',
                                  'Bon rapport qualité-prix',
                                  'Excellent service client',
                                  'Délai un peu long mais produits OK',
                                  'Je recommande ce fournisseur']),
                  (datetime.now() - timedelta(days=random.randint(0, 180))).strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
        print("[SEED] ✅ 20 avis créés")

    conn.commit()
    conn.close()
    print("[SEED] ✅ Données démo Marketplace générées")


if __name__ == '__main__':
    init_db()
