

"""
🏥 OMEGA Assurance Santé — Base de données
Membres · Cotisations · Prestataires · Prestations · Sinistres · Prévention
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = '/app/data/assurance.db'


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()

    # ─── Utilisateurs (agents + gestionnaires) ───
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

    # ─── Membres / Adhérents ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS membres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_adherent TEXT UNIQUE,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            date_naissance TEXT,
            sexe TEXT,
            telephone TEXT,
            telephone_urgence TEXT,
            email TEXT,
            adresse TEXT,
            ville TEXT,
            region TEXT,
            type_membre TEXT DEFAULT 'individuel',
            groupe_id INTEGER,
            statut TEXT DEFAULT 'actif',
            qr_code TEXT,
            date_adhesion TEXT,
            profession TEXT,
            revenu_mensuel REAL DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(groupe_id) REFERENCES groupes(id)
        )
    """)

    # ─── Groupes (famille, tontine, coopérative, entreprise) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS groupes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            type TEXT,
            responsable TEXT,
            telephone TEXT,
            ville TEXT,
            region TEXT,
            nb_membres INTEGER DEFAULT 0,
            cotisation_mensuelle REAL DEFAULT 0,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Personnes à charge (famille du membre) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ayants_droit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            membre_id INTEGER NOT NULL,
            nom TEXT,
            prenom TEXT,
            date_naissance TEXT,
            sexe TEXT,
            lien_parente TEXT,
            statut TEXT DEFAULT 'actif',
            created_at TEXT,
            FOREIGN KEY(membre_id) REFERENCES membres(id)
        )
    """)

    # ─── Formules d'assurance ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS formules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            description TEXT,
            cotisation_mensuelle REAL DEFAULT 0,
            cotisation_annuelle REAL DEFAULT 0,
            plafond_annuel REAL DEFAULT 0,
            taux_prise_charge REAL DEFAULT 80,
            couvre_hospitalisation INTEGER DEFAULT 1,
            couvre_maternite INTEGER DEFAULT 1,
            couvre_pharmacie INTEGER DEFAULT 1,
            couvre_consultations INTEGER DEFAULT 1,
            couvre_lunettes INTEGER DEFAULT 0,
            couvre_dentaire INTEGER DEFAULT 0,
            nb_ayants_droit_max INTEGER DEFAULT 0,
            age_max INTEGER DEFAULT 75,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Adhésions (membre ↔ formule) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS adhesions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            membre_id INTEGER NOT NULL,
            formule_id INTEGER NOT NULL,
            date_debut TEXT,
            date_fin TEXT,
            cotisation_mensuelle REAL DEFAULT 0,
            statut TEXT DEFAULT 'actif',
            created_at TEXT,
            FOREIGN KEY(membre_id) REFERENCES membres(id),
            FOREIGN KEY(formule_id) REFERENCES formules(id)
        )
    """)

    # ─── Cotisations / Paiements ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cotisations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_recu TEXT UNIQUE,
            membre_id INTEGER NOT NULL,
            adhesion_id INTEGER,
            periode TEXT,
            montant REAL DEFAULT 0,
            mode_paiement TEXT,
            reference TEXT,
            date_paiement TEXT,
            statut TEXT DEFAULT 'payee',
            agent_id INTEGER,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(membre_id) REFERENCES membres(id),
            FOREIGN KEY(adhesion_id) REFERENCES adhesions(id),
            FOREIGN KEY(agent_id) REFERENCES users(id)
        )
    """)

    # ─── Prestataires de santé ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prestataires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            type TEXT,
            categorie TEXT,
            adresse TEXT,
            ville TEXT,
            region TEXT,
            telephone TEXT,
            email TEXT,
            contact_nom TEXT,
            conventionne INTEGER DEFAULT 1,
            taux_remise REAL DEFAULT 0,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Prestations (types de soins couverts) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prestations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            categorie TEXT,
            description TEXT,
            plafond_annuel REAL DEFAULT 0,
            taux_prise_charge REAL DEFAULT 80,
            ticket_moderateur REAL DEFAULT 0,
            delai_carence_jours INTEGER DEFAULT 0,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Sinistres / Déclarations ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sinistres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_sinistre TEXT UNIQUE,
            membre_id INTEGER NOT NULL,
            prestation_id INTEGER,
            prestataire_id INTEGER,
            beneficiaire TEXT,
            date_soin TEXT,
            date_declaration TEXT,
            description TEXT,
            montant_facture REAL DEFAULT 0,
            montant_rembourse REAL DEFAULT 0,
            ticket_moderateur REAL DEFAULT 0,
            statut TEXT DEFAULT 'declare',
            date_traitement TEXT,
            date_paiement TEXT,
            motif_rejet TEXT,
            agent_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(membre_id) REFERENCES membres(id),
            FOREIGN KEY(prestation_id) REFERENCES prestations(id),
            FOREIGN KEY(prestataire_id) REFERENCES prestataires(id),
            FOREIGN KEY(agent_id) REFERENCES users(id)
        )
    """)

    # ─── Prévention / Sensibilisation ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS actions_prevention (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titre TEXT NOT NULL,
            type TEXT,
            description TEXT,
            lieu TEXT,
            date_action TEXT,
            nb_participants INTEGER DEFAULT 0,
            groupe_id INTEGER,
            cout REAL DEFAULT 0,
            statut TEXT DEFAULT 'planifiee',
            created_at TEXT,
            FOREIGN KEY(groupe_id) REFERENCES groupes(id)
        )
    """)

    # ─── Dépistages ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS depistages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            membre_id INTEGER,
            type_depistage TEXT,
            date_depistage TEXT,
            resultat TEXT,
            suivi TEXT,
            created_at TEXT,
            FOREIGN KEY(membre_id) REFERENCES membres(id)
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
        "CREATE INDEX IF NOT EXISTS idx_membres_statut ON membres(statut)",
        "CREATE INDEX IF NOT EXISTS idx_membres_tel ON membres(telephone)",
        "CREATE INDEX IF NOT EXISTS idx_cotisations_membre ON cotisations(membre_id)",
        "CREATE INDEX IF NOT EXISTS idx_sinistres_membre ON sinistres(membre_id)",
        "CREATE INDEX IF NOT EXISTS idx_sinistres_statut ON sinistres(statut)",
    ]:
        try:
            cur.execute(idx)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # TRIGGERS
    # ═══════════════════════════════════════════════════════

    # Trigger 1 : numéro adhérent auto + QR
    cur.execute("DROP TRIGGER IF EXISTS trg_membre_numero")
    cur.execute("""
        CREATE TRIGGER trg_membre_numero
        AFTER INSERT ON membres
        FOR EACH ROW
        WHEN NEW.numero_adherent IS NULL OR NEW.numero_adherent = ''
        BEGIN
            UPDATE membres SET
                numero_adherent = 'ADH-' || strftime('%Y', 'now') || '-' || substr('000000' || NEW.id, -6),
                qr_code = 'ASSU|ADH|' || NEW.id || '|' || NEW.telephone
            WHERE id = NEW.id;
        END
    """)

    # Trigger 2 : numéro reçu cotisation auto
    cur.execute("DROP TRIGGER IF EXISTS trg_cotisation_recu")
    cur.execute("""
        CREATE TRIGGER trg_cotisation_recu
        AFTER INSERT ON cotisations
        FOR EACH ROW
        WHEN NEW.numero_recu IS NULL OR NEW.numero_recu = ''
        BEGIN
            UPDATE cotisations SET
                numero_recu = 'REC-' || strftime('%Y%m%d', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 3 : numéro sinistre auto
    cur.execute("DROP TRIGGER IF EXISTS trg_sinistre_numero")
    cur.execute("""
        CREATE TRIGGER trg_sinistre_numero
        AFTER INSERT ON sinistres
        FOR EACH ROW
        WHEN NEW.numero_sinistre IS NULL OR NEW.numero_sinistre = ''
        BEGIN
            UPDATE sinistres SET
                numero_sinistre = 'SIN-' || strftime('%Y%m', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 4 : code groupe auto
    cur.execute("DROP TRIGGER IF EXISTS trg_groupe_code")
    cur.execute("""
        CREATE TRIGGER trg_groupe_code
        AFTER INSERT ON groupes
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE groupes SET
                code = 'GRP-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 5 : MAJ nb_membres groupe
    cur.execute("DROP TRIGGER IF EXISTS trg_groupe_nb_membres")
    cur.execute("""
        CREATE TRIGGER trg_groupe_nb_membres
        AFTER INSERT ON membres
        FOR EACH ROW
        WHEN NEW.groupe_id IS NOT NULL
        BEGIN
            UPDATE groupes SET
                nb_membres = (SELECT COUNT(*) FROM membres WHERE groupe_id = NEW.groupe_id)
            WHERE id = NEW.groupe_id;
        END
    """)

    conn.commit()
    conn.close()
    print("[INIT] ✅ Base Assurance Santé prête")


def seed_demo():
    """Génère des données démo si base vide."""
    conn = get_conn()
    cur = conn.cursor()

    from werkzeug.security import generate_password_hash

    # ─── Users ───
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        users = [
            ('admin', 'admin123', 'admin', 'Administrateur', 'admin@assurance.sn', '+221 77 000 00 00', 'Siège Dakar'),
            ('gestionnaire', 'gestion123', 'gestionnaire', 'Fatou Diallo', 'gestion@assurance.sn', '+221 77 111 11 11', 'Siège Dakar'),
            ('agent', 'agent123', 'agent', 'Moussa Ndiaye', 'agent@assurance.sn', '+221 77 222 22 22', 'Agence Thiès'),
            ('agent2', 'agent123', 'agent', 'Awa Fall', 'agent2@assurance.sn', '+221 77 333 33 33', 'Agence Ziguinchor'),
            ('medecin', 'medecin123', 'medecin_conseil', 'Dr. Ibrahima Ba', 'medecin@assurance.sn', '+221 77 444 44 44', 'Siège Dakar'),
        ]
        for u in users:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, nom_complet, email, telephone, agence, actif, created_at)
                VALUES (?,?,?,?,?,?,?,1,?)
            """, (u[0], generate_password_hash(u[1]), u[2], u[3], u[4], u[5], u[6], datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(users)} utilisateurs créés")

    # ─── Formules ───
    cur.execute("SELECT COUNT(*) FROM formules")
    if cur.fetchone()[0] == 0:
        formules = [
            ('FORM-BAS', 'Formule BASIQUE', 'Soins de base, consultations', 3500, 40000, 250000, 70, 0, 0, 1, 1, 0, 0, 0, 75),
            ('FORM-FAM', 'Formule FAMILLE', 'Individuel + 4 ayants droit', 8500, 100000, 750000, 80, 1, 1, 1, 1, 0, 0, 4, 75),
            ('FORM-MAT', 'Formule MATERNITÉ', 'Suivi grossesse + accouchement', 5000, 60000, 500000, 85, 1, 1, 1, 1, 0, 0, 2, 50),
            ('FORM-PREMIUM', 'Formule PREMIUM', 'Couverture complète famille', 15000, 180000, 2000000, 90, 1, 1, 1, 1, 1, 1, 6, 75),
            ('FORM-SENIOR', 'Formule SENIOR', 'Personnes âgées 60-75 ans', 12000, 144000, 1200000, 85, 1, 0, 1, 1, 1, 1, 0, 75),
        ]
        for f in formules:
            cur.execute("""
                INSERT INTO formules (code, nom, description, cotisation_mensuelle, cotisation_annuelle,
                                       plafond_annuel, taux_prise_charge, couvre_hospitalisation,
                                       couvre_maternite, couvre_pharmacie, couvre_consultations,
                                       couvre_lunettes, couvre_dentaire, nb_ayants_droit_max,
                                       age_max, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (*f, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(formules)} formules créées")

    # ─── Groupes ───
    cur.execute("SELECT COUNT(*) FROM groupes")
    if cur.fetchone()[0] == 0:
        groupes = [
            ('Tontine Femmes Médina', 'tontine', 'Aïssatou Sow', '+221 77 555 55 55', 'Dakar', 'Dakar', 35),
            ('Coopérative Agricole Thiès', 'cooperative', 'Moussa Traoré', '+221 77 666 66 66', 'Thiès', 'Thiès', 120),
            ('Groupement Pêcheurs Saint-Louis', 'cooperative', 'Cheikh Sall', '+221 77 777 77 77', 'Saint-Louis', 'Saint-Louis', 85),
            ('Tontine Ziguinchor', 'tontine', 'Fatou Mané', '+221 77 888 88 88', 'Ziguinchor', 'Ziguinchor', 45),
            ('Association Marchands Kaolack', 'association', 'Ibrahima Diop', '+221 77 999 99 99', 'Kaolack', 'Kaolack', 200),
        ]
        for g in groupes:
            cur.execute("""
                INSERT INTO groupes (code, nom, type, responsable, telephone, ville, region,
                                       nb_membres, cotisation_mensuelle, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (None, g[0], g[1], g[2], g[3], g[4], g[5], g[6], 0, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(groupes)} groupes créés")

    cur.execute("SELECT id FROM groupes")
    grp_ids = [r[0] for r in cur.fetchall()]

    # ─── Membres ───
    cur.execute("SELECT COUNT(*) FROM membres")
    if cur.fetchone()[0] == 0:
        prenoms_h = ['Moussa', 'Amadou', 'Ibrahima', 'Cheikh', 'Ousmane', 'Mamadou', 'Alioune', 'Babacar']
        prenoms_f = ['Fatou', 'Awa', 'Aminata', 'Mariama', 'Aïssatou', 'Marième', 'Ndèye', 'Khady']
        noms = ['Diop', 'Ndiaye', 'Sall', 'Fall', 'Ba', 'Diallo', 'Sow', 'Sy', 'Faye', 'Gueye']
        regions = [('Dakar', 'Dakar'), ('Thiès', 'Thiès'), ('Saint-Louis', 'Saint-Louis'),
                   ('Ziguinchor', 'Ziguinchor'), ('Kaolack', 'Kaolack'), ('Touba', 'Diourbel'),
                   ('Tambacounda', 'Tambacounda')]
        professions = ['Commerçant', 'Agriculteur', 'Pêcheur', 'Enseignant', 'Fonctionnaire',
                       'Artisan', 'Couturière', 'Chauffeur', 'Infirmier', 'Menuisier']

        for i in range(45):
            sexe = random.choice(['M', 'F'])
            prenom = random.choice(prenoms_h if sexe == 'M' else prenoms_f)
            nom = random.choice(noms)
            age = random.randint(18, 75)
            date_naiss = (datetime.now() - timedelta(days=age*365)).strftime('%Y-%m-%d')
            ville, region = random.choice(regions)
            tel = f'+221 77 {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}'
            type_m = random.choice(['individuel', 'individuel', 'familial', 'groupe'])
            groupe_id = random.choice(grp_ids) if type_m == 'groupe' else None

            cur.execute("""
                INSERT INTO membres
                (numero_adherent, nom, prenom, date_naissance, sexe, telephone, telephone_urgence,
                 email, adresse, ville, region, type_membre, groupe_id, statut,
                 date_adhesion, profession, revenu_mensuel, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None, nom, prenom, date_naiss, sexe, tel,
                  f'+221 77 {random.randint(100,999)} 00 00',
                  f'{prenom.lower()}.{nom.lower()}@email.sn',
                  f'Quartier {random.choice(["Médina", "Plateau", "Grand Dakar", "Yoff"])}',
                  ville, region, type_m, groupe_id, 'actif',
                  (datetime.now() - timedelta(days=random.randint(30, 500))).strftime('%Y-%m-%d'),
                  random.choice(professions),
                  random.randint(50000, 500000),
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ 45 membres créés")

    cur.execute("SELECT id FROM membres")
    membre_ids = [r[0] for r in cur.fetchall()]

    # ─── Adhésions ───
    cur.execute("SELECT COUNT(*) FROM adhesions")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, cotisation_mensuelle FROM formules")
        formules_rows = cur.fetchall()

        for mid in membre_ids:
            f = random.choice(formules_rows)
            date_debut = datetime.now() - timedelta(days=random.randint(30, 400))
            date_fin = date_debut + timedelta(days=365)
            cur.execute("""
                INSERT INTO adhesions (membre_id, formule_id, date_debut, date_fin,
                                        cotisation_mensuelle, statut, created_at)
                VALUES (?,?,?,?,?, 'actif', ?)
            """, (mid, f['id'], date_debut.strftime('%Y-%m-%d'),
                  date_fin.strftime('%Y-%m-%d'), f['cotisation_mensuelle'],
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ Adhésions créées")

    # ─── Cotisations ───
    cur.execute("SELECT COUNT(*) FROM cotisations")
    if cur.fetchone()[0] == 0:
        n_cot = 0
        for mid in membre_ids[:40]:
            for m in range(random.randint(1, 8)):
                date_p = datetime.now() - timedelta(days=random.randint(0, 300))
                cur.execute("""
                    INSERT INTO cotisations
                    (numero_recu, membre_id, periode, montant, mode_paiement, reference,
                     date_paiement, statut, created_at)
                    VALUES (?,?,?,?,?,?,?, 'payee', ?)
                """, (None, mid, date_p.strftime('%Y-%m'), random.choice([3500, 5000, 8500, 12000, 15000]),
                      random.choice(['mobile_money', 'especes', 'virement']),
                      f'REF-{random.randint(1000,9999)}',
                      date_p.strftime('%Y-%m-%d'),
                      datetime.now().isoformat()))
                n_cot += 1
        print(f"[SEED] ✅ {n_cot} cotisations créées")

    # ─── Prestataires ───
    cur.execute("SELECT COUNT(*) FROM prestataires")
    if cur.fetchone()[0] == 0:
        prestataires = [
            ('Hôpital Principal de Dakar', 'hopital', 'public', 'Avenue Nelson Mandela', 'Dakar', 'Dakar', '+221 33 839 50 50'),
            ('Hôpital Fann', 'hopital', 'public', 'Avenue Cheikh Anta Diop', 'Dakar', 'Dakar', '+221 33 869 18 18'),
            ('Clinique Pasteur', 'clinique', 'prive', 'Rue Docteur Theze', 'Dakar', 'Dakar', '+221 33 839 11 11'),
            ('Hôpital Régional de Thiès', 'hopital', 'public', 'Route de Dakar', 'Thiès', 'Thiès', '+221 33 951 12 12'),
            ('Poste de Santé Médina', 'poste_sante', 'public', 'Médina', 'Dakar', 'Dakar', '+221 33 821 33 33'),
            ('Pharmacie de la Médina', 'pharmacie', 'prive', 'Avenue Blaise Diagne', 'Dakar', 'Dakar', '+221 33 821 44 44'),
            ('Centre de Santé Ziguinchor', 'centre_sante', 'public', 'Centre-ville', 'Ziguinchor', 'Ziguinchor', '+221 33 991 55 55'),
            ('Laboratoire Bio 24', 'laboratoire', 'prive', 'Plateau', 'Dakar', 'Dakar', '+221 33 823 66 66'),
            ('Clinique de la Madeleine', 'clinique', 'prive', 'Rue Carnot', 'Dakar', 'Dakar', '+221 33 889 77 77'),
        ]
        for i, p in enumerate(prestataires):
            cur.execute("""
                INSERT INTO prestataires (code, nom, type, categorie, adresse, ville, region,
                                            telephone, conventionne, taux_remise, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,1,?, 'actif', ?)
            """, (f'PREST-{i+1:03d}', p[0], p[1], p[2], p[3], p[4], p[5], p[6],
                  random.choice([10, 15, 20]), datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(prestataires)} prestataires créés")

    # ─── Prestations ───
    cur.execute("SELECT COUNT(*) FROM prestations")
    if cur.fetchone()[0] == 0:
        prestations = [
            ('Consultation généraliste', 'consultation', 15000, 80, 2000, 0),
            ('Consultation spécialiste', 'consultation', 30000, 80, 5000, 0),
            ('Hospitalisation', 'hospitalisation', 500000, 85, 0, 0),
            ('Maternité - Accouchement', 'maternite', 250000, 90, 0, 270),
            ('Césarienne', 'maternite', 800000, 90, 0, 270),
            ('Médicaments génériques', 'pharmacie', 100000, 70, 1000, 0),
            ('Analyses laboratoire', 'laboratoire', 80000, 80, 2000, 0),
            ('Radiologie', 'imagerie', 150000, 80, 3000, 0),
            ('Chirurgie', 'chirurgie', 1500000, 85, 0, 30),
            ('Urgences', 'urgence', 200000, 90, 0, 0),
            ('Lunettes', 'optique', 50000, 70, 5000, 180),
            ('Soins dentaires', 'dentaire', 100000, 70, 3000, 30),
            ('Vaccination', 'prevention', 25000, 100, 0, 0),
            ('Dialyse', 'maladie_chronique', 2000000, 90, 0, 90),
            ('Traitement diabète', 'maladie_chronique', 300000, 80, 5000, 90),
        ]
        for i, p in enumerate(prestations):
            cur.execute("""
                INSERT INTO prestations (code, nom, categorie, description, plafond_annuel,
                                           taux_prise_charge, ticket_moderateur, delai_carence_jours,
                                           actif, created_at)
                VALUES (?,?,?,?,?,?,?,?,1,?)
            """, (f'PREST-{i+1:03d}', p[0], p[1], f'Couverture {p[0]}', p[2], p[3], p[4], p[5],
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(prestations)} prestations créées")

    # ─── Sinistres ───
    cur.execute("SELECT COUNT(*) FROM sinistres")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM prestations")
        presta_ids = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT id FROM prestataires")
        prest_ids = [r[0] for r in cur.fetchall()]

        n_sin = 0
        for mid in membre_ids[:30]:
            for _ in range(random.randint(1, 4)):
                facture = random.randint(15000, 500000)
                taux = random.choice([70, 80, 85, 90])
                rembourse = facture * taux / 100
                date_soin = datetime.now() - timedelta(days=random.randint(0, 180))

                cur.execute("""
                    INSERT INTO sinistres
                    (numero_sinistre, membre_id, prestation_id, prestataire_id, beneficiaire,
                     date_soin, date_declaration, description, montant_facture, montant_rembourse,
                     ticket_moderateur, statut, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (None, mid,
                      random.choice(presta_ids), random.choice(prest_ids),
                      'Adhérent',
                      date_soin.strftime('%Y-%m-%d'),
                      (date_soin + timedelta(days=random.randint(0, 15))).strftime('%Y-%m-%d'),
                      'Soins médicaux',
                      facture, rembourse, facture - rembourse,
                      random.choice(['declare', 'en_cours', 'rembourse', 'rembourse', 'rejete']),
                      datetime.now().isoformat()))
                n_sin += 1
        print(f"[SEED] ✅ {n_sin} sinistres créés")

    # ─── Actions prévention ───
    cur.execute("SELECT COUNT(*) FROM actions_prevention")
    if cur.fetchone()[0] == 0:
        actions = [
            'Campagne de vaccination enfants',
            'Dépistage diabète gratuit',
            'Sensibilisation paludisme',
            'Dépistage cancer du sein',
            'Formation premiers secours',
            'Journée santé maternelle',
        ]
        for a in actions:
            cur.execute("""
                INSERT INTO actions_prevention (titre, type, description, lieu, date_action,
                                                  nb_participants, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (a, random.choice(['campagne', 'depistage', 'formation']),
                  f'Action de prévention : {a}',
                  random.choice(['Dakar', 'Thiès', 'Ziguinchor', 'Saint-Louis']),
                  (datetime.now() + timedelta(days=random.randint(-30, 60))).strftime('%Y-%m-%d'),
                  random.randint(20, 200),
                  random.choice(['planifiee', 'en_cours', 'terminee']),
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(actions)} actions prévention créées")

    conn.commit()
    conn.close()
    print("[SEED] ✅ Données démo Assurance Santé générées")


if __name__ == '__main__':
    init_db()
