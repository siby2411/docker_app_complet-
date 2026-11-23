

"""
🏠 Immobilier & Baux — Base de données
Biens · Propriétaires · Locataires · Baux · Loyers · Quittances · États des lieux
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = '/app/data/immobilier.db'


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()

    # ─── Utilisateurs (agents, gestionnaires) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'agent',
            nom_complet TEXT,
            email TEXT,
            telephone TEXT,
            agence TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Propriétaires ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS proprietaires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            prenom TEXT,
            type TEXT DEFAULT 'particulier',
            telephone TEXT,
            telephone2 TEXT,
            email TEXT,
            adresse TEXT,
            ville TEXT,
            pays TEXT DEFAULT 'Sénégal',
            num_piece TEXT,
            rib_bancaire TEXT,
            mobile_money TEXT,
            notes TEXT,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Locataires ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS locataires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            prenom TEXT,
            type TEXT DEFAULT 'particulier',
            telephone TEXT,
            telephone2 TEXT,
            email TEXT,
            adresse_actuelle TEXT,
            profession TEXT,
            employeur TEXT,
            revenu_mensuel REAL DEFAULT 0,
            num_piece TEXT,
            garant_nom TEXT,
            garant_telephone TEXT,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Biens immobiliers ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS biens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            proprietaire_id INTEGER,
            type TEXT,
            titre TEXT NOT NULL,
            description TEXT,
            adresse TEXT,
            quartier TEXT,
            ville TEXT DEFAULT 'Dakar',
            region TEXT,
            latitude REAL,
            longitude REAL,
            superficie_m2 REAL DEFAULT 0,
            nb_pieces INTEGER DEFAULT 0,
            nb_chambres INTEGER DEFAULT 0,
            nb_salles_bain INTEGER DEFAULT 0,
            etage INTEGER DEFAULT 0,
            meuble INTEGER DEFAULT 0,
            equipements TEXT,
            loyer_mensuel REAL DEFAULT 0,
            charges_mensuelles REAL DEFAULT 0,
            depot_garantie REAL DEFAULT 0,
            statut TEXT DEFAULT 'disponible',
            disponible_a_partir TEXT,
            note REAL DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(proprietaire_id) REFERENCES proprietaires(id)
        )
    """)

    # ─── Baux (contrats de location) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS baux (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            bien_id INTEGER,
            locataire_id INTEGER,
            proprietaire_id INTEGER,
            date_debut TEXT,
            date_fin TEXT,
            duree_mois INTEGER DEFAULT 12,
            loyer_mensuel REAL DEFAULT 0,
            charges_mensuelles REAL DEFAULT 0,
            depot_garantie REAL DEFAULT 0,
            jour_echeance INTEGER DEFAULT 5,
            mode_paiement TEXT,
            statut TEXT DEFAULT 'actif',
            date_signature_proprietaire TEXT,
            date_signature_locataire TEXT,
            signature_proprietaire TEXT,
            signature_locataire TEXT,
            renouvellement_auto INTEGER DEFAULT 1,
            preavis_mois INTEGER DEFAULT 3,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(bien_id) REFERENCES biens(id),
            FOREIGN KEY(locataire_id) REFERENCES locataires(id),
            FOREIGN KEY(proprietaire_id) REFERENCES proprietaires(id)
        )
    """)

    # ─── Loyers mensuels ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS loyers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bail_id INTEGER,
            periode TEXT,
            date_echeance TEXT,
            loyer_du REAL DEFAULT 0,
            charges_dues REAL DEFAULT 0,
            total_du REAL DEFAULT 0,
            montant_paye REAL DEFAULT 0,
            date_paiement TEXT,
            mode_paiement TEXT,
            statut TEXT DEFAULT 'a_payer',
            jours_retard INTEGER DEFAULT 0,
            penalite_retard REAL DEFAULT 0,
            commission_agence REAL DEFAULT 0,
            montant_proprietaire REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(bail_id) REFERENCES baux(id)
        )
    """)

    # ─── Quittances ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quittances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            loyer_id INTEGER,
            bail_id INTEGER,
            date_emission TEXT,
            montant_recu REAL DEFAULT 0,
            mode_paiement TEXT,
            qr_code TEXT,
            statut TEXT DEFAULT 'valide',
            created_at TEXT,
            FOREIGN KEY(loyer_id) REFERENCES loyers(id),
            FOREIGN KEY(bail_id) REFERENCES baux(id)
        )
    """)

    # ─── États des lieux ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS etats_lieux (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            bail_id INTEGER,
            bien_id INTEGER,
            type TEXT,
            date_etat TEXT,
            etat_general TEXT,
            observations TEXT,
            nb_photos INTEGER DEFAULT 0,
            realise_par TEXT,
            signe_proprietaire INTEGER DEFAULT 0,
            signe_locataire INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(bail_id) REFERENCES baux(id),
            FOREIGN KEY(bien_id) REFERENCES biens(id)
        )
    """)

    # ─── Photos états des lieux ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS etats_lieux_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            etat_lieux_id INTEGER,
            piece TEXT,
            chemin TEXT,
            description TEXT,
            created_at TEXT,
            FOREIGN KEY(etat_lieux_id) REFERENCES etats_lieux(id)
        )
    """)

    # ─── Impayés & recouvrement ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS impayes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loyer_id INTEGER,
            bail_id INTEGER,
            montant_impaye REAL DEFAULT 0,
            jours_retard INTEGER DEFAULT 0,
            niveau TEXT,
            action TEXT,
            statut TEXT DEFAULT 'ouvert',
            date_constat TEXT,
            date_resolution TEXT,
            created_at TEXT,
            FOREIGN KEY(loyer_id) REFERENCES loyers(id),
            FOREIGN KEY(bail_id) REFERENCES baux(id)
        )
    """)

    # ─── Commissions agence ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS commissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loyer_id INTEGER,
            bail_id INTEGER,
            bien_id INTEGER,
            mois TEXT,
            montant_loyer REAL DEFAULT 0,
            taux_commission REAL DEFAULT 0,
            montant_commission REAL DEFAULT 0,
            statut TEXT DEFAULT 'a_payer',
            date_paiement TEXT,
            created_at TEXT,
            FOREIGN KEY(loyer_id) REFERENCES loyers(id),
            FOREIGN KEY(bail_id) REFERENCES baux(id),
            FOREIGN KEY(bien_id) REFERENCES biens(id)
        )
    """)

    # ─── Réclamations / Interventions ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reclamations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bail_id INTEGER,
            bien_id INTEGER,
            type TEXT,
            titre TEXT,
            description TEXT,
            priorite TEXT DEFAULT 'normale',
            statut TEXT DEFAULT 'ouverte',
            date_declaration TEXT,
            date_resolution TEXT,
            cout_intervention REAL DEFAULT 0,
            responsable TEXT,
            created_at TEXT,
            FOREIGN KEY(bail_id) REFERENCES baux(id),
            FOREIGN KEY(bien_id) REFERENCES biens(id)
        )
    """)

    # ─── Paiements mobile money ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS paiements_mobile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loyer_id INTEGER,
            bail_id INTEGER,
            operateur TEXT,
            telephone TEXT,
            montant REAL DEFAULT 0,
            reference TEXT,
            statut TEXT DEFAULT 'en_attente',
            date_transaction TEXT,
            created_at TEXT,
            FOREIGN KEY(loyer_id) REFERENCES loyers(id),
            FOREIGN KEY(bail_id) REFERENCES baux(id)
        )
    """)

    # ─── Évaluations / Cote marché ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS evaluations_marche (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quartier TEXT,
            ville TEXT,
            type_bien TEXT,
            nb_pieces INTEGER,
            loyer_moyen REAL DEFAULT 0,
            nb_observations INTEGER DEFAULT 0,
            tendance TEXT,
            annee INTEGER,
            mois INTEGER,
            created_at TEXT
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
        "CREATE INDEX IF NOT EXISTS idx_biens_statut ON biens(statut)",
        "CREATE INDEX IF NOT EXISTS idx_baux_statut ON baux(statut)",
        "CREATE INDEX IF NOT EXISTS idx_loyers_bail ON loyers(bail_id)",
        "CREATE INDEX IF NOT EXISTS idx_loyers_statut ON loyers(statut)",
        "CREATE INDEX IF NOT EXISTS idx_impayes_statut ON impayes(statut)",
    ]:
        try:
            cur.execute(idx)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # TRIGGERS
    # ═══════════════════════════════════════════════════════

    # Trigger 1 : code bien auto
    cur.execute("DROP TRIGGER IF EXISTS trg_bien_code")
    cur.execute("""
        CREATE TRIGGER trg_bien_code
        AFTER INSERT ON biens
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE biens SET
                code = 'B-' || strftime('%Y%m', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 2 : code propriétaire auto
    cur.execute("DROP TRIGGER IF EXISTS trg_proprietaire_code")
    cur.execute("""
        CREATE TRIGGER trg_proprietaire_code
        AFTER INSERT ON proprietaires
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE proprietaires SET
                code = 'PROP-' || substr('00000' || NEW.id, -5)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 3 : code locataire auto
    cur.execute("DROP TRIGGER IF EXISTS trg_locataire_code")
    cur.execute("""
        CREATE TRIGGER trg_locataire_code
        AFTER INSERT ON locataires
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE locataires SET
                code = 'LOC-' || substr('00000' || NEW.id, -5)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 4 : numéro bail auto
    cur.execute("DROP TRIGGER IF EXISTS trg_bail_numero")
    cur.execute("""
        CREATE TRIGGER trg_bail_numero
        AFTER INSERT ON baux
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE baux SET
                numero = 'BAIL-' || strftime('%Y%m', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 5 : numéro quittance auto + QR
    cur.execute("DROP TRIGGER IF EXISTS trg_quittance_numero")
    cur.execute("""
        CREATE TRIGGER trg_quittance_numero
        AFTER INSERT ON quittances
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE quittances SET
                numero = 'QUIT-' || strftime('%Y%m', 'now') || '-' || substr('0000' || NEW.id, -4),
                qr_code = 'IMMO|QUIT|' || NEW.id
            WHERE id = NEW.id;
        END
    """)

    conn.commit()
    conn.close()
    print("[INIT] ✅ Base Immobilier & Baux prête")


def seed_demo():
    """Génère des données démo si base vide."""
    conn = get_conn()
    cur = conn.cursor()

    from werkzeug.security import generate_password_hash

    # ─── Users ───
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        users = [
            ('admin', 'admin123', 'admin', 'Administrateur', 'admin@immo.sn', '+221 77 000 00 00', 'OMEGA Immobilier'),
            ('gestionnaire', 'gestion123', 'gestionnaire', 'Fatou Diallo', 'gestion@immo.sn', '+221 77 111 11 11', 'Dakar'),
            ('agent1', 'agent123', 'agent', 'Moussa Ndiaye', 'agent1@immo.sn', '+221 77 222 22 22', 'Dakar'),
            ('agent2', 'agent123', 'agent', 'Awa Fall', 'agent2@immo.sn', '+221 77 333 33 33', 'Thiès'),
            ('agent3', 'agent123', 'agent', 'Ousmane Ba', 'agent3@immo.sn', '+221 77 444 44 44', 'Saint-Louis'),
        ]
        for u in users:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, nom_complet, email, telephone, agence, actif, created_at)
                VALUES (?,?,?,?,?,?,?,1,?)
            """, (u[0], generate_password_hash(u[1]), u[2], u[3], u[4], u[5], u[6], datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(users)} utilisateurs créés")

    # ─── Propriétaires ───
    cur.execute("SELECT COUNT(*) FROM proprietaires")
    if cur.fetchone()[0] == 0:
        noms = ['Diop', 'Ndiaye', 'Sall', 'Fall', 'Ba', 'Diallo', 'Sow', 'Sy', 'Faye', 'Gueye', 'Mbaye', 'Camara']
        prenoms_h = ['Moussa', 'Amadou', 'Ibrahima', 'Cheikh', 'Ousmane', 'Mamadou', 'Alioune', 'Babacar']
        prenoms_f = ['Fatou', 'Awa', 'Aminata', 'Mariama', 'Aïssatou', 'Ndèye', 'Khady', 'Sokhna']
        villes = [('Dakar', 'Dakar'), ('Thiès', 'Thiès'), ('Saint-Louis', 'Saint-Louis'),
                  ('Mbour', 'Thiès'), ('Diamniadio', 'Dakar'), ('Rufisque', 'Dakar')]

        n = 0
        for i in range(25):
            sexe = random.choice(['M', 'F'])
            prenom = random.choice(prenoms_h if sexe == 'M' else prenoms_f)
            nom = random.choice(noms)
            ville, region = random.choice(villes)
            type_p = random.choice(['particulier', 'particulier', 'societe'])

            cur.execute("""
                INSERT INTO proprietaires (code, nom, prenom, type, telephone, email,
                                             adresse, ville, pays, num_piece, mobile_money, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (None, nom, prenom if type_p == 'particulier' else 'SCI ' + nom,
                  type_p,
                  f'+221 77 {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}',
                  f'{prenom.lower()}.{nom.lower()}@email.sn',
                  f'Quartier {random.choice(["Médina", "Plateau", "Almadies", "Sacré-Cœur", "Yoff", "Point E"])}',
                  ville, 'Sénégal',
                  f'CNI-{random.randint(100000, 999999)}',
                  f'+221 7{random.randint(6,8)} {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}',
                  datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} propriétaires créés")

    cur.execute("SELECT id FROM proprietaires")
    prop_ids = [r[0] for r in cur.fetchall()]

    # ─── Locataires ───
    cur.execute("SELECT COUNT(*) FROM locataires")
    if cur.fetchone()[0] == 0:
        professions = ['Commerçant', 'Enseignant', 'Fonctionnaire', 'Ingénieur', 'Infirmier',
                       'Développeur', 'Commercial', 'Étudiant', 'Médecin', 'Avocat']
        noms = ['Diop', 'Ndiaye', 'Sall', 'Fall', 'Ba', 'Diallo', 'Sow', 'Sy', 'Faye', 'Gueye']
        prenoms_h = ['Moussa', 'Amadou', 'Ibrahima', 'Cheikh', 'Ousmane', 'Mamadou']
        prenoms_f = ['Fatou', 'Awa', 'Aminata', 'Mariama', 'Aïssatou', 'Ndèye']

        n = 0
        for i in range(40):
            sexe = random.choice(['M', 'F'])
            prenom = random.choice(prenoms_h if sexe == 'M' else prenoms_f)
            nom = random.choice(noms)

            cur.execute("""
                INSERT INTO locataires (code, nom, prenom, type, telephone, email,
                                          profession, employeur, revenu_mensuel,
                                          num_piece, garant_nom, garant_telephone, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (None, nom, prenom, 'particulier',
                  f'+221 77 {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}',
                  f'{prenom.lower()}.{nom.lower()}@email.sn',
                  random.choice(professions),
                  random.choice(['SONATEL', 'SENELEC', 'BOLLORÉ', 'CBAO', 'SONACOS', 'Indépendant']),
                  random.randint(150000, 900000),
                  f'CNI-{random.randint(100000, 999999)}',
                  random.choice(prenoms_h + prenoms_f) + ' ' + random.choice(noms),
                  f'+221 77 {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}',
                  datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} locataires créés")

    cur.execute("SELECT id FROM locataires")
    loc_ids = [r[0] for r in cur.fetchall()]

    # ─── Biens ───
    cur.execute("SELECT COUNT(*) FROM biens")
    if cur.fetchone()[0] == 0:
        quartiers_dakar = ['Almadies', 'Ngor', 'Mermoz', 'Point E', 'Plateau', 'Médina', 'Yoff', 'Ouakam',
                           'Sacré-Cœur', 'Grand Yoff', 'Parcelles Assainies', 'Pikine']
        types_bien = [
            ('villa', 'Villa moderne', 3500000, 5, 4, 3, 250),
            ('appartement', 'Appartement standing', 800000, 3, 2, 2, 90),
            ('studio', 'Studio meublé', 250000, 1, 1, 1, 35),
            ('chambre', 'Chambre simple', 80000, 1, 1, 1, 20),
            ('terrain', 'Terrain constructible', 150000, 0, 0, 0, 300),
            ('bureau', 'Local commercial/bureau', 500000, 3, 0, 2, 80),
        ]

        n = 0
        for i in range(50):
            t = random.choice(types_bien)
            quartier = random.choice(quartiers_dakar)
            loyer = t[2] * random.uniform(0.7, 1.4)
            charges = loyer * 0.05
            depot = loyer * 2
            statut = random.choice(['disponible', 'loue', 'loue', 'loue', 'maintenance'])

            cur.execute("""
                INSERT INTO biens (code, proprietaire_id, type, titre, description,
                                     adresse, quartier, ville, region, latitude, longitude,
                                     superficie_m2, nb_pieces, nb_chambres, nb_salles_bain,
                                     meuble, equipements, loyer_mensuel, charges_mensuelles,
                                     depot_garantie, statut, note, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None, random.choice(prop_ids), t[0],
                  t[1] + ' — ' + quartier,
                  'Beau ' + t[0] + ' situé à ' + quartier + ', Dakar',
                  f'Rue {random.randint(1, 99)}, {quartier}',
                  quartier, 'Dakar', 'Dakar',
                  14.6928 + random.uniform(-0.1, 0.1),
                  -17.4467 + random.uniform(-0.1, 0.1),
                  t[6], t[3], t[4], t[5],
                  1 if 'meublé' in t[1].lower() else 0,
                  'Eau, Électricité, Climatisation' if t[0] != 'terrain' else 'Aucun',
                  loyer, charges, depot, statut,
                  round(random.uniform(3.5, 5.0), 1),
                  datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} biens créés")

    cur.execute("SELECT id, loyer_mensuel, charges_mensuelles, proprietaire_id FROM biens WHERE statut='loue'")
    biens_loues = cur.fetchall()

    # ─── Baux ───
    cur.execute("SELECT COUNT(*) FROM baux")
    if cur.fetchone()[0] == 0:
        n = 0
        for b in biens_loues:
            date_debut = datetime.now() - timedelta(days=random.randint(30, 300))
            date_fin = date_debut + timedelta(days=365)
            depot = (b['loyer_mensuel'] or 0) * 2

            cur.execute("""
                INSERT INTO baux (numero, bien_id, locataire_id, proprietaire_id,
                                    date_debut, date_fin, duree_mois, loyer_mensuel,
                                    charges_mensuelles, depot_garantie, jour_echeance,
                                    mode_paiement, statut, date_signature_proprietaire,
                                    date_signature_locataire, renouvellement_auto, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None, b['id'], random.choice(loc_ids), b['proprietaire_id'],
                  date_debut.strftime('%Y-%m-%d'),
                  date_fin.strftime('%Y-%m-%d'),
                  12, b['loyer_mensuel'], b['charges_mensuelles'], depot,
                  random.choice([1, 5, 10]),
                  random.choice(['mobile_money', 'virement', 'especes']),
                  'actif',
                  date_debut.strftime('%Y-%m-%d'),
                  date_debut.strftime('%Y-%m-%d'),
                  1,
                  datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} baux créés")

    cur.execute("SELECT id, loyer_mensuel, charges_mensuelles FROM baux WHERE statut='actif'")
    baux_actifs = cur.fetchall()

    # ─── Loyers (12 derniers mois par bail) ───
    cur.execute("SELECT COUNT(*) FROM loyers")
    if cur.fetchone()[0] == 0:
        n = 0
        for b in baux_actifs:
            for i in range(6):
                periode = (datetime.now() - timedelta(days=i * 30)).strftime('%Y-%m')
                date_echeance = (datetime.now() - timedelta(days=i * 30)).replace(day=5).strftime('%Y-%m-%d')
                loyer_du = b['loyer_mensuel'] or 0
                charges = b['charges_mensuelles'] or 0
                total = loyer_du + charges

                statut = random.choices(['paye', 'paye', 'paye', 'a_payer', 'en_retard'],
                                          weights=[50, 20, 15, 10, 5])[0]
                montant_paye = total if statut == 'paye' else 0
                date_p = date_echeance if statut == 'paye' else None
                jours_retard = 0
                if statut == 'en_retard':
                    jours_retard = random.randint(5, 60)

                commission = loyer_du * 0.10
                mnt_prop = loyer_du - commission

                cur.execute("""
                    INSERT INTO loyers (bail_id, periode, date_echeance, loyer_du,
                                          charges_dues, total_du, montant_paye,
                                          date_paiement, mode_paiement, statut,
                                          jours_retard, commission_agence,
                                          montant_proprietaire, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (b['id'], periode, date_echeance, loyer_du, charges, total,
                      montant_paye, date_p,
                      random.choice(['mobile_money', 'virement', 'especes']) if date_p else None,
                      statut, jours_retard, commission, mnt_prop,
                      datetime.now().isoformat()))
                n += 1
        print(f"[SEED] ✅ {n} loyers créés")

    # ─── Quittances (pour loyers payés) ───
    cur.execute("SELECT COUNT(*) FROM quittances")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, bail_id, montant_paye, mode_paiement, date_paiement FROM loyers WHERE statut='paye' LIMIT 100")
        loyers_payes = cur.fetchall()
        n = 0
        for l in loyers_payes:
            cur.execute("""
                INSERT INTO quittances (numero, loyer_id, bail_id, date_emission,
                                          montant_recu, mode_paiement, statut, created_at)
                VALUES (?,?,?,?,?,?, 'valide', ?)
            """, (None, l['id'], l['bail_id'],
                  l['date_paiement'] or datetime.now().strftime('%Y-%m-%d'),
                  l['montant_paye'], l['mode_paiement'],
                  datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} quittances créées")

    # ─── Impayés ───
    cur.execute("SELECT COUNT(*) FROM impayes")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, bail_id, total_du, jours_retard FROM loyers WHERE statut='en_retard'")
        loyers_retard = cur.fetchall()
        n = 0
        for l in loyers_retard:
            niveau = 'critique' if l['jours_retard'] > 30 else 'urgent' if l['jours_retard'] > 15 else 'normal'
            cur.execute("""
                INSERT INTO impayes (loyer_id, bail_id, montant_impaye, jours_retard,
                                       niveau, action, statut, date_constat, created_at)
                VALUES (?,?,?,?,?,?, 'ouvert', ?, ?)
            """, (l['id'], l['bail_id'], l['total_du'], l['jours_retard'],
                  niveau, 'Relance SMS + appel téléphonique',
                  datetime.now().strftime('%Y-%m-%d'), datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} impayés créés")

    # ─── Commissions ───
    cur.execute("SELECT COUNT(*) FROM commissions")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, bail_id, periode, loyer_du, commission_agence FROM loyers WHERE statut='paye'")
        loyers_p = cur.fetchall()
        n = 0
        for l in loyers_p:
            cur.execute("""
                INSERT INTO commissions (loyer_id, bail_id, mois, montant_loyer,
                                           taux_commission, montant_commission, statut, created_at)
                VALUES (?,?,?,?,?,?, 'a_payer', ?)
            """, (l['id'], l['bail_id'], l['periode'], l['loyer_du'],
                  10.0, l['commission_agence'],
                  datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} commissions créées")

    # ─── Réclamations ───
    cur.execute("SELECT COUNT(*) FROM reclamations")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, bien_id FROM baux WHERE statut='actif' LIMIT 30")
        baux = cur.fetchall()
        types_recl = ['Plomberie', 'Électricité', 'Climatisation', 'Peinture', 'Serrurerie', 'Toiture']
        titres = ['Fuite d\'eau', 'Panne électrique', 'Clim en panne', 'Mur à repeindre',
                  'Serrure cassée', 'Infiltration toit']
        n = 0
        for b in baux:
            if random.random() < 0.4:
                cur.execute("""
                    INSERT INTO reclamations (bail_id, bien_id, type, titre, description,
                                                priorite, statut, date_declaration, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (b['id'], b['bien_id'],
                      random.choice(types_recl), random.choice(titres),
                      'Demande de réparation urgente',
                      random.choice(['basse', 'normale', 'haute', 'urgente']),
                      random.choice(['ouverte', 'en_cours', 'resolue']),
                      (datetime.now() - timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d'),
                      datetime.now().isoformat()))
                n += 1
        print(f"[SEED] ✅ {n} réclamations créées")

    # ─── Évaluations marché ───
    cur.execute("SELECT COUNT(*) FROM evaluations_marche")
    if cur.fetchone()[0] == 0:
        quartiers_eval = ['Almadies', 'Ngor', 'Mermoz', 'Point E', 'Plateau', 'Yoff']
        types_eval = ['villa', 'appartement', 'studio']
        n = 0
        for q in quartiers_eval:
            for t in types_eval:
                loyer_base = {'villa': 2500000, 'appartement': 600000, 'studio': 200000}[t]
                loyer_moy = loyer_base * random.uniform(0.8, 1.3)
                cur.execute("""
                    INSERT INTO evaluations_marche (quartier, ville, type_bien, nb_pieces,
                                                      loyer_moyen, nb_observations, tendance,
                                                      annee, mois, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (q, 'Dakar', t, random.choice([1, 2, 3, 4, 5]),
                      loyer_moy, random.randint(5, 30),
                      random.choice(['hausse', 'stable', 'baisse']),
                      datetime.now().year, datetime.now().month,
                      datetime.now().isoformat()))
                n += 1
        print(f"[SEED] ✅ {n} évaluations marché créées")

    conn.commit()
    conn.close()
    print("[SEED] ✅ Données démo Immobilier générées")


if __name__ == '__main__':
    init_db()
