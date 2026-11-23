# -*- coding: utf-8 -*-
"""
🔧 OMEGA PARTS — Base de données Pièces Détachées Automobile
Catalogue · Catégories · Stock · Fournisseurs · POS · Ventes · Compatibilité
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = '/app/data/parts.db'

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
            role TEXT DEFAULT 'vendeur',
            nom_complet TEXT,
            email TEXT,
            telephone TEXT,
            point_vente TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Points de vente / Magasins ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS points_vente (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            type TEXT DEFAULT 'magasin',
            adresse TEXT,
            ville TEXT,
            pays TEXT DEFAULT 'Sénégal',
            telephone TEXT,
            responsable TEXT,
            horaires TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Catégories hiérarchiques ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            description TEXT,
            icone TEXT,
            ordre INTEGER DEFAULT 0,
            actif INTEGER DEFAULT 1,
            created_at TEXT,
            FOREIGN KEY(parent_id) REFERENCES categories(id)
        )
    """)

    # ─── Marques de véhicules (pour compatibilité) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicules_marques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE NOT NULL,
            pays_origine TEXT,
            logo_url TEXT,
            created_at TEXT
        )
    """)

    # ─── Modèles de véhicules (pour compatibilité) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicules_modeles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marque_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            annee_debut INTEGER,
            annee_fin INTEGER,
            created_at TEXT,
            FOREIGN KEY(marque_id) REFERENCES vehicules_marques(id)
        )
    """)

    # ─── Fournisseurs ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fournisseurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            type TEXT DEFAULT 'grossiste',
            pays TEXT,
            ville TEXT,
            adresse TEXT,
            telephone TEXT,
            whatsapp TEXT,
            email TEXT,
            contact_nom TEXT,
            delai_livraison_jours INTEGER DEFAULT 7,
            conditions_paiement TEXT,
            note INTEGER DEFAULT 0,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Pièces détachées (catalogue central) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pieces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE,
            code_oem TEXT,
            code_barre TEXT,
            nom TEXT NOT NULL,
            description TEXT,
            categorie_id INTEGER,
            marque_piece TEXT,
            type_piece TEXT,
            unite TEXT DEFAULT 'pièce',
            qualite TEXT DEFAULT 'standard',
            photo_principale TEXT,
            photos TEXT,
            prix_achat REAL DEFAULT 0,
            prix_vente_detail REAL DEFAULT 0,
            prix_vente_gros REAL DEFAULT 0,
            prix_vente_mecano REAL DEFAULT 0,
            marge_pct REAL DEFAULT 30,
            tva_pct REAL DEFAULT 18,
            stock_min INTEGER DEFAULT 5,
            stock_max INTEGER DEFAULT 100,
            stock_alerte INTEGER DEFAULT 10,
            emplacement TEXT,
            poids_kg REAL DEFAULT 0,
            dimensions TEXT,
            garantie_mois INTEGER DEFAULT 0,
            pays_origine TEXT,
            fournisseur_principal_id INTEGER,
            statut TEXT DEFAULT 'disponible',
            tags TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(categorie_id) REFERENCES categories(id),
            FOREIGN KEY(fournisseur_principal_id) REFERENCES fournisseurs(id)
        )
    """)

    # ─── Compatibilité pièce ↔ véhicule ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS piece_compatibilite (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            piece_id INTEGER NOT NULL,
            marque_id INTEGER NOT NULL,
            modele_id INTEGER,
            annee_debut INTEGER,
            annee_fin INTEGER,
            moteur TEXT,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(piece_id) REFERENCES pieces(id),
            FOREIGN KEY(marque_id) REFERENCES vehicules_marques(id),
            FOREIGN KEY(modele_id) REFERENCES vehicules_modeles(id)
        )
    """)

    # ─── Stock par point de vente ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            piece_id INTEGER NOT NULL,
            point_vente_id INTEGER NOT NULL,
            quantite INTEGER DEFAULT 0,
            quantite_reservee INTEGER DEFAULT 0,
            emplacement TEXT,
            dernier_inventaire TEXT,
            updated_at TEXT,
            UNIQUE(piece_id, point_vente_id),
            FOREIGN KEY(piece_id) REFERENCES pieces(id),
            FOREIGN KEY(point_vente_id) REFERENCES points_vente(id)
        )
    """)

    # ─── Mouvements de stock ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_mouvements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            piece_id INTEGER NOT NULL,
            point_vente_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            quantite INTEGER NOT NULL,
            quantite_avant INTEGER DEFAULT 0,
            quantite_apres INTEGER DEFAULT 0,
            motif TEXT,
            reference TEXT,
            user_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(piece_id) REFERENCES pieces(id),
            FOREIGN KEY(point_vente_id) REFERENCES points_vente(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # ─── Clients ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            prenom TEXT,
            type TEXT DEFAULT 'particulier',
            telephone TEXT,
            whatsapp TEXT,
            email TEXT,
            adresse TEXT,
            ville TEXT,
            pays TEXT DEFAULT 'Sénégal',
            type_client TEXT DEFAULT 'detail',
            garage_nom TEXT,
            remise_pct REAL DEFAULT 0,
            score INTEGER DEFAULT 50,
            total_achats REAL DEFAULT 0,
            nb_achats INTEGER DEFAULT 0,
            derniere_visite TEXT,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Commandes fournisseurs ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS commandes_fournisseurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            fournisseur_id INTEGER NOT NULL,
            point_vente_id INTEGER NOT NULL,
            date_commande TEXT,
            date_livraison_prevue TEXT,
            date_reception TEXT,
            statut TEXT DEFAULT 'en_attente',
            montant_total REAL DEFAULT 0,
            frais_livraison REAL DEFAULT 0,
            notes TEXT,
            user_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(fournisseur_id) REFERENCES fournisseurs(id),
            FOREIGN KEY(point_vente_id) REFERENCES points_vente(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS commandes_fournisseurs_lignes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commande_id INTEGER NOT NULL,
            piece_id INTEGER NOT NULL,
            quantite INTEGER DEFAULT 0,
            quantite_recue INTEGER DEFAULT 0,
            prix_unitaire REAL DEFAULT 0,
            montant REAL DEFAULT 0,
            FOREIGN KEY(commande_id) REFERENCES commandes_fournisseurs(id),
            FOREIGN KEY(piece_id) REFERENCES pieces(id)
        )
    """)

    # ─── Ventes (POS) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ventes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            client_id INTEGER,
            point_vente_id INTEGER,
            user_id INTEGER,
            type_vente TEXT DEFAULT 'detail',
            date_vente TEXT,
            sous_total REAL DEFAULT 0,
            remise_pct REAL DEFAULT 0,
            remise_montant REAL DEFAULT 0,
            tva REAL DEFAULT 0,
            montant_ttc REAL DEFAULT 0,
            mode_paiement TEXT DEFAULT 'especes',
            montant_paye REAL DEFAULT 0,
            monnaie REAL DEFAULT 0,
            statut TEXT DEFAULT 'complete',
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(point_vente_id) REFERENCES points_vente(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ventes_lignes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vente_id INTEGER NOT NULL,
            piece_id INTEGER NOT NULL,
            quantite INTEGER DEFAULT 1,
            prix_unitaire REAL DEFAULT 0,
            remise_pct REAL DEFAULT 0,
            montant REAL DEFAULT 0,
            FOREIGN KEY(vente_id) REFERENCES ventes(id),
            FOREIGN KEY(piece_id) REFERENCES pieces(id)
        )
    """)

    # ─── Devis ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            client_id INTEGER,
            point_vente_id INTEGER,
            date_devis TEXT,
            date_validite TEXT,
            montant_total REAL DEFAULT 0,
            statut TEXT DEFAULT 'en_attente',
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(point_vente_id) REFERENCES points_vente(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS devis_lignes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            devis_id INTEGER NOT NULL,
            piece_id INTEGER NOT NULL,
            quantite INTEGER DEFAULT 1,
            prix_unitaire REAL DEFAULT 0,
            montant REAL DEFAULT 0,
            FOREIGN KEY(devis_id) REFERENCES devis(id),
            FOREIGN KEY(piece_id) REFERENCES pieces(id)
        )
    """)

    # ─── Retours ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS retours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            vente_id INTEGER,
            client_id INTEGER,
            piece_id INTEGER,
            quantite INTEGER,
            motif TEXT,
            type_retour TEXT,
            montant_rembourse REAL DEFAULT 0,
            statut TEXT DEFAULT 'en_attente',
            created_at TEXT,
            FOREIGN KEY(vente_id) REFERENCES ventes(id),
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(piece_id) REFERENCES pieces(id)
        )
    """)

    # ─── Paiements ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vente_id INTEGER,
            client_id INTEGER,
            montant REAL DEFAULT 0,
            mode TEXT,
            operateur TEXT,
            reference TEXT,
            statut TEXT DEFAULT 'valide',
            date_paiement TEXT,
            created_at TEXT,
            FOREIGN KEY(vente_id) REFERENCES ventes(id),
            FOREIGN KEY(client_id) REFERENCES clients(id)
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

    # ─── Paramètres ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS parametres (
            cle TEXT PRIMARY KEY,
            valeur TEXT,
            description TEXT
        )
    """)

    # ═══════════════════════════════════════════════════════════
    # TRIGGERS
    # ═══════════════════════════════════════════════════════════

    # Trigger 1 : SKU auto
    cur.execute("DROP TRIGGER IF EXISTS trg_piece_sku")
    cur.execute("""
        CREATE TRIGGER trg_piece_sku
        AFTER INSERT ON pieces
        FOR EACH ROW
        WHEN NEW.sku IS NULL OR NEW.sku = ''
        BEGIN
            UPDATE pieces SET
                sku = 'PCS-' || strftime('%Y%m', 'now') || '-' || substr('00000' || NEW.id, -5),
                code_barre = 'OMG' || substr('000000000' || NEW.id, -9)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 2 : Code client auto
    cur.execute("DROP TRIGGER IF EXISTS trg_client_code")
    cur.execute("""
        CREATE TRIGGER trg_client_code
        AFTER INSERT ON clients
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE clients SET code = 'CLI-' || substr('00000' || NEW.id, -5)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 3 : Numéro vente auto
    cur.execute("DROP TRIGGER IF EXISTS trg_vente_numero")
    cur.execute("""
        CREATE TRIGGER trg_vente_numero
        AFTER INSERT ON ventes
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE ventes SET
                numero = 'VTE-' || strftime('%Y%m%d', 'now') || '-' || substr('00000' || NEW.id, -5)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 4 : Numéro devis auto
    cur.execute("DROP TRIGGER IF EXISTS trg_devis_numero")
    cur.execute("""
        CREATE TRIGGER trg_devis_numero
        AFTER INSERT ON devis
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE devis SET
                numero = 'DEV-' || strftime('%Y%m%d', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 5 : Mise à jour stock après vente
    cur.execute("DROP TRIGGER IF EXISTS trg_maj_stock_vente")
    cur.execute("""
        CREATE TRIGGER trg_maj_stock_vente
        AFTER INSERT ON ventes_lignes
        FOR EACH ROW
        BEGIN
            UPDATE stock
            SET quantite = quantite - NEW.quantite,
                updated_at = datetime('now')
            WHERE piece_id = NEW.piece_id;
        END
    """)

    # Trigger 6 : Mouvement stock automatique
    cur.execute("DROP TRIGGER IF EXISTS trg_stock_mouvement")
    cur.execute("""
        CREATE TRIGGER trg_stock_mouvement
        AFTER UPDATE OF quantite ON stock
        FOR EACH ROW
        WHEN NEW.quantite != OLD.quantite
        BEGIN
            INSERT INTO stock_mouvements
                (piece_id, point_vente_id, type, quantite, quantite_avant, quantite_apres, created_at)
            VALUES
                (NEW.piece_id, NEW.point_vente_id, 'auto', NEW.quantite - OLD.quantite,
                 OLD.quantite, NEW.quantite, datetime('now'));
        END
    """)

    # Trigger 7 : MAJ client après vente
    cur.execute("DROP TRIGGER IF EXISTS trg_maj_client_vente")
    cur.execute("""
        CREATE TRIGGER trg_maj_client_vente
        AFTER UPDATE OF statut ON ventes
        FOR EACH ROW
        WHEN NEW.statut = 'complete' AND OLD.statut != 'complete' AND NEW.client_id IS NOT NULL
        BEGIN
            UPDATE clients SET
                nb_achats = nb_achats + 1,
                total_achats = total_achats + NEW.montant_ttc,
                derniere_visite = NEW.date_vente
            WHERE id = NEW.client_id;
        END
    """)

    # ─── Index ───
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_pieces_sku ON pieces(sku)",
        "CREATE INDEX IF NOT EXISTS idx_pieces_categorie ON pieces(categorie_id)",
        "CREATE INDEX IF NOT EXISTS idx_pieces_code_oem ON pieces(code_oem)",
        "CREATE INDEX IF NOT EXISTS idx_pieces_code_barre ON pieces(code_barre)",
        "CREATE INDEX IF NOT EXISTS idx_stock_piece ON stock(piece_id)",
        "CREATE INDEX IF NOT EXISTS idx_stock_point_vente ON stock(point_vente_id)",
        "CREATE INDEX IF NOT EXISTS idx_ventes_client ON ventes(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_ventes_date ON ventes(date_vente)",
        "CREATE INDEX IF NOT EXISTS idx_compat_piece ON piece_compatibilite(piece_id)",
        "CREATE INDEX IF NOT EXISTS idx_compat_marque ON piece_compatibilite(marque_id)",
    ]:
        try:
            cur.execute(idx)
        except Exception:
            pass

    conn.commit()
    conn.close()
    print("[INIT] ✅ Base OMEGA PARTS prête")


def seed_demo():
    """Données démo complètes"""
    conn = get_conn()
    cur = conn.cursor()

    from werkzeug.security import generate_password_hash

    # ─── Users ───
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        users = [
            ('admin', 'admin123', 'admin', 'Administrateur', 'admin@omega-parts.sn', '+221 77 000 00 00', 'OMEGA PARTS'),
            ('gerant', 'gerant123', 'gerant', 'Mamadou Diop', 'gerant@omega-parts.sn', '+221 77 111 11 11', 'Magasin Dakar'),
            ('vendeur1', 'vendeur123', 'vendeur', 'Ibrahima Sall', 'ibrahima@omega-parts.sn', '+221 77 222 22 22', 'POS Dakar'),
            ('vendeur2', 'vendeur123', 'vendeur', 'Awa Fall', 'awa@omega-parts.sn', '+221 77 333 33 33', 'POS Thiès'),
            ('caissier', 'caisse123', 'caissier', 'Ousmane Ba', 'ousmane@omega-parts.sn', '+221 77 444 44 44', 'POS Dakar'),
        ]
        for u in users:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, nom_complet, email, telephone, point_vente, actif, created_at)
                VALUES (?,?,?,?,?,?,?,1,?)
            """, (u[0], generate_password_hash(u[1]), u[2], u[3], u[4], u[5], u[6], datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(users)} utilisateurs créés")

    # ─── Points de vente ───
    cur.execute("SELECT COUNT(*) FROM points_vente")
    if cur.fetchone()[0] == 0:
        pv = [
            ('OMEGA PARTS Dakar Plateau', 'magasin', 'Rue Carnot', 'Dakar', '+221 33 821 00 01'),
            ('OMEGA PARTS Almadies', 'magasin', 'Route des Almadies', 'Dakar', '+221 33 820 00 02'),
            ('OMEGA PARTS Thiès', 'magasin', 'Avenue LSS', 'Thiès', '+221 33 951 00 03'),
            ('OMEGA PARTS Saint-Louis', 'magasin', 'Île Saint-Louis', 'Saint-Louis', '+221 33 961 00 04'),
        ]
        for p in pv:
            cur.execute("""
                INSERT INTO points_vente (code, nom, type, adresse, ville, pays, telephone, actif, created_at)
                VALUES (?,?,?,?,?,?,?,1,?)
            """, (None, p[0], p[1], p[2], p[3], 'Sénégal', p[4], datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(pv)} points de vente créés")

    cur.execute("SELECT id FROM points_vente")
    pv_ids = [r[0] for r in cur.fetchall()]

    # ─── Catégories hiérarchiques ───
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        # Catégories racines
        cats_root = [
            ('MOTEUR', 'Moteur', 'Pièces moteur', '🔧'),
            ('FREINAGE', 'Freinage', 'Système de freinage', '🛑'),
            ('SUSPENSION', 'Suspension & Direction', 'Amortisseurs, rotules', '⚙️'),
            ('ELECTRICITE', 'Électricité & Électronique', 'Batteries, alternateurs', '⚡'),
            ('CARROSSERIE', 'Carrosserie', 'Pare-chocs, rétroviseurs', '🚗'),
            ('FILTRATION', 'Filtration', 'Filtres à air, huile, carburant', '💧'),
            ('TRANSMISSION', 'Transmission', 'Embrayage, boîte de vitesses', '⚙️'),
            ('CLIMATISATION', 'Climatisation', 'Compresseurs, radiateurs', '❄️'),
            ('ECLAIRAGE', 'Éclairage', 'Phares, feux, ampoules', '💡'),
            ('PNEUMATIQUE', 'Pneumatique & Roues', 'Pneus, jantes, chambres', '⭕'),
        ]
        for i, c in enumerate(cats_root):
            cur.execute("""
                INSERT INTO categories (code, nom, description, icone, ordre, actif, created_at)
                VALUES (?,?,?,?,?,1,?)
            """, (c[0], c[1], c[2], c[3], i, datetime.now().isoformat()))

        # Sous-catégories
        cur.execute("SELECT id, code FROM categories")
        cats_map = {r['code']: r['id'] for r in cur.fetchall()}

        subcats = {
            'MOTEUR': [
                ('MOT_FILT', 'Filtres moteur', '🔧'),
                ('MOT_COUR', 'Courroie distribution', '⛓️'),
                ('MOT_POMP', 'Pompes à eau', '💧'),
                ('MOT_JOINT', 'Joints moteur', '🔘'),
                ('MOT_BOUGIE', 'Bougies & allumage', '⚡'),
                ('MOT_TURBO', 'Turbos', '🌀'),
            ],
            'FREINAGE': [
                ('FRE_PLAQ', 'Plaquettes de frein', '🛑'),
                ('FRE_DISQ', 'Disques de frein', '💿'),
                ('FRE_ETRI', 'Étriers', '🔧'),
                ('FRE_LIQ', 'Liquide de frein', '💧'),
                ('FRE_ABSR', 'Capteurs ABS', '📡'),
            ],
            'SUSPENSION': [
                ('SUS_AMOR', 'Amortisseurs', '⚙️'),
                ('SUS_ROTU', 'Rotules', '🔘'),
                ('SUS_ROUE', 'Roulements', '⭕'),
                ('SUS_SILE', 'Silentblocs', '🔘'),
            ],
            'ELECTRICITE': [
                ('ELEC_BATT', 'Batteries', '🔋'),
                ('ELEC_ALTE', 'Alternateurs', '⚡'),
                ('ELEC_DEMA', 'Démarreurs', '🔑'),
                ('ELEC_CAPT', 'Capteurs', '📡'),
            ],
            'FILTRATION': [
                ('FIL_AIR', 'Filtres à air', '💨'),
                ('FIL_HUIL', 'Filtres à huile', '🛢️'),
                ('FIL_CARB', 'Filtres carburant', '⛽'),
                ('FIL_HABI', 'Filtres habitacle', '🚗'),
            ],
            'ECLAIRAGE': [
                ('ECL_PHAR', 'Phares', '💡'),
                ('ECL_AMP', 'Ampoules', '💡'),
                ('ECL_FEUX', 'Feux arrière', '🚨'),
                ('ECL_RETR', 'Rétroviseurs', '🪞'),
            ],
        }

        for parent_code, subs in subcats.items():
            parent_id = cats_map.get(parent_code)
            if not parent_id:
                continue
            for s in subs:
                cur.execute("""
                    INSERT INTO categories (parent_id, code, nom, icone, ordre, actif, created_at)
                    VALUES (?,?,?,?,?,1,?)
                """, (parent_id, s[0], s[1], s[2], 0, datetime.now().isoformat()))

        print(f"[SEED] ✅ Catégories créées (racines + sous-catégories)")

    # ─── Marques véhicules ───
    cur.execute("SELECT COUNT(*) FROM vehicules_marques")
    if cur.fetchone()[0] == 0:
        marques = ['Toyota', 'Peugeot', 'Renault', 'Hyundai', 'Kia', 'Mercedes-Benz',
                   'BMW', 'Nissan', 'Volkswagen', 'Ford', 'Suzuki', 'Mitsubishi',
                   'Citroën', 'Fiat', 'Mazda', 'Honda', 'Chevrolet', 'Audi']
        for m in marques:
            cur.execute("""
                INSERT INTO vehicules_marques (nom, created_at) VALUES (?,?)
            """, (m, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(marques)} marques véhicules créées")

    cur.execute("SELECT id, nom FROM vehicules_marques")
    marques_map = {r['nom']: r['id'] for r in cur.fetchall()}

    # ─── Modèles véhicules ───
    cur.execute("SELECT COUNT(*) FROM vehicules_modeles")
    if cur.fetchone()[0] == 0:
        modeles = {
            'Toyota': ['Corolla', 'RAV4', 'Hilux', 'Yaris', 'Camry'],
            'Peugeot': ['208', '308', '3008', 'Partner', '508'],
            'Renault': ['Clio', 'Duster', 'Mégane', 'Captur', 'Kangoo'],
            'Hyundai': ['Tucson', 'i10', 'i20', 'Accent', 'Santa Fe'],
            'Kia': ['Sportage', 'Rio', 'Picanto', 'Sorento', 'Ceed'],
            'Mercedes-Benz': ['Classe C', 'Classe A', 'GLC', 'Classe E', 'Classe S'],
            'BMW': ['Série 3', 'Série 5', 'X3', 'X5', 'Série 1'],
            'Nissan': ['Qashqai', 'Note', 'Juke', 'X-Trail', 'Micra'],
            'Volkswagen': ['Golf', 'Tiguan', 'Polo', 'Passat', 'T-Roc'],
            'Ford': ['Focus', 'Fiesta', 'Ranger', 'Kuga', 'Mondeo'],
        }
        n = 0
        for marque, mods in modeles.items():
            mid = marques_map.get(marque)
            if not mid:
                continue
            for m in mods:
                cur.execute("""
                    INSERT INTO vehicules_modeles (marque_id, nom, annee_debut, created_at)
                    VALUES (?,?,?,?)
                """, (mid, m, 2010, datetime.now().isoformat()))
                n += 1
        print(f"[SEED] ✅ {n} modèles véhicules créés")

    # ─── Fournisseurs ───
    cur.execute("SELECT COUNT(*) FROM fournisseurs")
    if cur.fetchone()[0] == 0:
        fournisseurs = [
            ('Auto Pièces Sénégal', 'grossiste', 'Sénégal', 'Dakar', '+221 33 821 10 10', 7),
            ('Sahel Auto Distribution', 'grossiste', 'Sénégal', 'Dakar', '+221 33 822 20 20', 5),
            ('CEDEAO Parts', 'importateur', 'Côte d\'Ivoire', 'Abidjan', '+225 27 21 30 40 50', 15),
            ('Euro Parts Import', 'importateur', 'France', 'Marseille', '+33 4 91 00 00 00', 30),
            ('Asia Auto Supply', 'importateur', 'Chine', 'Shanghai', '+86 21 0000 0000', 45),
            ('Nigeria Auto Hub', 'grossiste', 'Nigeria', 'Lagos', '+234 1 000 0000', 10),
            ('Maroc Pièces Pro', 'grossiste', 'Maroc', 'Casablanca', '+212 522 00 00 00', 12),
            ('Allemagne KFZ', 'importateur', 'Allemagne', 'Hamburg', '+49 40 000 000', 35),
        ]
        for f in fournisseurs:
            cur.execute("""
                INSERT INTO fournisseurs (code, nom, type, pays, ville, telephone, delai_livraison_jours, note, actif, created_at)
                VALUES (?,?,?,?,?,?,?,?,1,?)
            """, (None, f[0], f[1], f[2], f[3], f[4], f[5], random.randint(3, 5), datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(fournisseurs)} fournisseurs créés")

    # ─── Pièces détachées (60 pièces) ───
    cur.execute("SELECT COUNT(*) FROM pieces")
    if cur.fetchone()[0] == 0:
        # Récupérer les sous-catégories
        cur.execute("SELECT id, code FROM categories WHERE parent_id IS NOT NULL")
        subcats_map = {r['code']: r['id'] for r in cur.fetchall()}

        cur.execute("SELECT id, nom FROM fournisseurs")
        fourn_ids = [r['id'] for r in cur.fetchall()]

        pieces_data = [
            # (nom, code_oem, categorie_code, marque_piece, type_piece, prix_achat_base)
            ("Plaquettes frein avant Toyota Corolla", "04465-02220", "FRE_PLAQ", "Toyota", "pièce d'origine", 25000),
            ("Plaquettes frein arrière Peugeot 308", "4254.75", "FRE_PLAQ", "Bosch", "équivalent", 18000),
            ("Disque frein avant 280mm Peugeot", "4249.36", "FRE_DISQ", "Brembo", "premium", 45000),
            ("Filtre à air Toyota Hilux", "17801-0L040", "FIL_AIR", "Toyota", "pièce d'origine", 12000),
            ("Filtre à huile Renault Clio", "8200768913", "FIL_HUIL", "Mann", "équivalent", 6500),
            ("Filtre carburant Hyundai Tucson", "31922-2H900", "FIL_CARB", "Hyundai", "pièce d'origine", 15000),
            ("Batterie 12V 60Ah", "BAT-60AH", "ELEC_BATT", "Varta", "premium", 55000),
            ("Batterie 12V 70Ah", "BAT-70AH", "ELEC_BATT", "Bosch", "premium", 75000),
            ("Amortisseur avant gauche Toyota RAV4", "48510-49285", "SUS_AMOR", "KYB", "premium", 65000),
            ("Amortisseur arrière Peugeot 3008", "5206.VP", "SUS_AMOR", "Monroe", "équivalent", 45000),
            ("Rotule de direction Renault Duster", "48520-4X01A", "SUS_ROTU", "Lemförder", "premium", 22000),
            ("Roulement roue avant Nissan Qashqai", "40210-4BA0A", "SUS_ROUE", "SKF", "premium", 32000),
            ("Pompe à eau BMW Série 3", "11517586925", "MOT_POMP", "Graf", "premium", 58000),
            ("Courroie distribution Peugeot 208", "0831.V5", "MOT_COUR", "Gates", "premium", 42000),
            ("Bougie allumage Honda Civic", "12290-R1A-H01", "MOT_BOUGIE", "NGK", "premium", 4500),
            ("Alternateur Volkswagen Golf 7", "06B903016A", "ELEC_ALTE", "Valeo", "premium", 125000),
            ("Démarreur Mercedes Classe C", "A0061516001", "ELEC_DEMA", "Bosch", "premium", 145000),
            ("Ampoule H4 12V 60/55W", "H4-60-55", "ECL_AMP", "Philips", "standard", 3500),
            ("Ampoule LED H7", "LED-H7", "ECL_AMP", "Osram", "premium", 15000),
            ("Phare avant gauche Toyota Hilux", "81150-0K180", "ECL_PHAR", "TYC", "équivalent", 85000),
            ("Feu arrière Peugeot 308", "6350.P0", "ECL_FEUX", "Valeo", "premium", 55000),
            ("Rétroviseur extérieur électrique Renault", "963013291R", "ECL_RETR", "OEM", "équivalent", 68000),
            ("Filtre habitacle charbon actif BMW", "64119237555", "FIL_HABI", "Mann", "premium", 18000),
            ("Radiateur refroidissement Peugeot 308", "1330.L2", "MOT_JOINT", "Valeo", "premium", 95000),
            ("Ventilateur radiateur Toyota Corolla", "16363-0T080", "MOT_JOINT", "Denso", "premium", 72000),
            ("Compresseur climatisation Nissan", "92600-4BA0A", "MOT_JOINT", "Denso", "premium", 185000),
            ("Compresseur climatisation Hyundai", "97701-2S000", "MOT_JOINT", "Hanon", "équivalent", 145000),
            ("Capteur ABS BMW X3", "34526763342", "FRE_ABSR", "ATE", "premium", 38000),
            ("Capteur température moteur VW", "059919501A", "ELEC_CAPT", "Bosch", "premium", 15000),
            ("Capteur position vilebrequin Peugeot", "1920.EN", "ELEC_CAPT", "Valeo", "premium", 22000),
        ]

        n = 0
        for p in pieces_data:
            cat_id = subcats_map.get(p[2])
            prix_achat = p[5]
            marge = random.uniform(1.25, 1.55)
            prix_vente = int(prix_achat * marge)

            cur.execute("""
                INSERT INTO pieces (
                    sku, code_oem, nom, categorie_id, marque_piece, type_piece,
                    qualite, prix_achat, prix_vente_detail, prix_vente_gros, prix_vente_mecano,
                    marge_pct, tva_pct, stock_min, stock_max, stock_alerte,
                    poids_kg, garantie_mois, pays_origine, fournisseur_principal_id,
                    statut, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                None, p[1], p[0], cat_id, p[3], p[4],
                'premium' if 'premium' in p[4] else 'standard',
                prix_achat, prix_vente,
                int(prix_vente * 0.85),  # gros
                int(prix_vente * 0.92),  # mécano
                round((marge - 1) * 100, 1),
                18, 5, 100, 10,
                round(random.uniform(0.1, 5), 2),
                random.choice([6, 12, 24]),
                random.choice(['Allemagne', 'France', 'Japon', 'Corée', 'Chine']),
                random.choice(fourn_ids),
                'disponible', datetime.now().isoformat()
            ))
            n += 1
        print(f"[SEED] ✅ {n} pièces détachées créées")

    # ─── Stock initial ───
    cur.execute("SELECT COUNT(*) FROM stock")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM pieces")
        piece_ids = [r[0] for r in cur.fetchall()]

        n = 0
        for pid in piece_ids:
            for pvid in pv_ids:
                qte = random.randint(0, 50)
                cur.execute("""
                    INSERT INTO stock (piece_id, point_vente_id, quantite, updated_at)
                    VALUES (?,?,?,?)
                """, (pid, pvid, qte, datetime.now().isoformat()))
                n += 1
        print(f"[SEED] ✅ {n} entrées de stock créées")

    # ─── Clients ───
    cur.execute("SELECT COUNT(*) FROM clients")
    if cur.fetchone()[0] == 0:
        prenoms_h = ['Moussa', 'Amadou', 'Ibrahima', 'Cheikh', 'Ousmane', 'Mamadou', 'Pape']
        prenoms_f = ['Fatou', 'Awa', 'Aminata', 'Mariama', 'Aïssatou', 'Ndèye']
        noms = ['Diop', 'Ndiaye', 'Sall', 'Fall', 'Ba', 'Diallo', 'Sow', 'Sy', 'Faye']
        villes = ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Mbour']
        garages = ['Garage Central', 'Auto Service Plus', 'Mécanique Moderne', 'Garage Express', None]

        n = 0
        for i in range(40):
            type_client = random.choice(['particulier', 'mecano', 'garage'])
            if type_client == 'particulier':
                prenom = random.choice(prenoms_h + prenoms_f)
                nom = random.choice(noms)
                garage_nom = None
                remise = 0
            elif type_client == 'mecano':
                prenom = random.choice(prenoms_h)
                nom = random.choice(noms)
                garage_nom = None
                remise = random.uniform(3, 8)
            else:
                prenom = None
                nom = random.choice(garages)
                garage_nom = nom
                remise = random.uniform(8, 15)

            tel = f'+221 77 {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}'

            cur.execute("""
                INSERT INTO clients (code, nom, prenom, type, telephone, whatsapp, email,
                    ville, pays, type_client, garage_nom, remise_pct,
                    score, total_achats, nb_achats, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0,0,'actif',?)
            """, (None, nom, prenom, 'particulier' if type_client == 'particulier' else 'professionnel',
                  tel, tel, f'{nom.lower()}@email.sn',
                  random.choice(villes), 'Sénégal', type_client, garage_nom, round(remise, 1),
                  random.randint(50, 95), datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} clients créés")

    # ─── Paramètres ───
    cur.execute("SELECT COUNT(*) FROM parametres")
    if cur.fetchone()[0] == 0:
        params = [
            ('nom_entreprise', 'OMEGA PARTS', 'Nom affiché'),
            ('tva_defaut', '18', 'TVA par défaut en %'),
            ('devise', 'FCFA', 'Devise'),
            ('pays', 'Sénégal', 'Pays'),
            ('adresse', 'Dakar, Sénégal', 'Adresse'),
            ('telephone', '+221 33 821 00 00', 'Téléphone'),
            ('email', 'contact@omega-parts.sn', 'Email'),
            ('site_web', 'www.omega-parts.sn', 'Site web'),
            ('objectif_ca_mensuel', '50000000', 'Objectif CA mensuel'),
        ]
        for p in params:
            cur.execute("INSERT INTO parametres (cle, valeur, description) VALUES (?,?,?)", p)
        print(f"[SEED] ✅ Paramètres configurés")

    conn.commit()
    conn.close()
    print("[SEED] ✅ Données démo OMEGA PARTS générées")


if __name__ == '__main__':
    init_db()
