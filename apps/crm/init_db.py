"""
💼 CRM & Ventes — Initialisation base de données
Prospects · Clients · Pipeline · Activités · Devis · Objectifs
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = '/app/data/crm.db'


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()

    # ─── Utilisateurs (commerciaux, managers) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'commercial',
            nom_complet TEXT,
            email TEXT,
            telephone TEXT,
            zone TEXT,
            objectif_mensuel REAL DEFAULT 0,
            commission_pct REAL DEFAULT 3.0,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Prospects ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prospects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            raison_sociale TEXT NOT NULL,
            secteur TEXT,
            contact_nom TEXT,
            contact_fonction TEXT,
            telephone TEXT,
            email TEXT,
            ville TEXT,
            pays TEXT DEFAULT 'Sénégal',
            source TEXT,
            statut TEXT DEFAULT 'nouveau',
            score INTEGER DEFAULT 0,
            commercial_id INTEGER,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(commercial_id) REFERENCES users(id)
        )
    """)

    # ─── Clients (converti) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            raison_sociale TEXT NOT NULL,
            secteur TEXT,
            contact_nom TEXT,
            telephone TEXT,
            email TEXT,
            ville TEXT,
            pays TEXT DEFAULT 'Sénégal',
            chiffre_affaires_total REAL DEFAULT 0,
            commercial_id INTEGER,
            date_conversion TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT,
            FOREIGN KEY(commercial_id) REFERENCES users(id)
        )
    """)

    # ─── Pipeline (opportunités) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS opportunites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titre TEXT NOT NULL,
            prospect_id INTEGER,
            client_id INTEGER,
            commercial_id INTEGER,
            montant_estime REAL DEFAULT 0,
            probabilite INTEGER DEFAULT 10,
            etape TEXT DEFAULT 'qualification',
            date_cloture_prevue TEXT,
            date_cloture_reelle TEXT,
            statut TEXT DEFAULT 'ouverte',
            source TEXT,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(prospect_id) REFERENCES prospects(id),
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(commercial_id) REFERENCES users(id)
        )
    """)

    # ─── Activités (appels, visites, emails) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS activites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            sujet TEXT,
            prospect_id INTEGER,
            client_id INTEGER,
            opportunite_id INTEGER,
            commercial_id INTEGER,
            date_activite TEXT,
            duree_min INTEGER DEFAULT 0,
            resultat TEXT,
            notes TEXT,
            prochaine_action TEXT,
            date_prochaine_action TEXT,
            created_at TEXT,
            FOREIGN KEY(prospect_id) REFERENCES prospects(id),
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(opportunite_id) REFERENCES opportunites(id),
            FOREIGN KEY(commercial_id) REFERENCES users(id)
        )
    """)

    # ─── Devis ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            client_id INTEGER,
            prospect_id INTEGER,
            commercial_id INTEGER,
            date_emission TEXT,
            date_validite TEXT,
            montant_ht REAL DEFAULT 0,
            tva REAL DEFAULT 0,
            montant_ttc REAL DEFAULT 0,
            statut TEXT DEFAULT 'brouillon',
            date_acceptation TEXT,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(prospect_id) REFERENCES prospects(id),
            FOREIGN KEY(commercial_id) REFERENCES users(id)
        )
    """)

    # ─── Lignes de devis ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devis_lignes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            devis_id INTEGER NOT NULL,
            designation TEXT,
            quantite REAL DEFAULT 1,
            prix_unitaire REAL DEFAULT 0,
            montant REAL DEFAULT 0,
            FOREIGN KEY(devis_id) REFERENCES devis(id)
        )
    """)

    # ─── Objectifs & Commissions ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS objectifs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commercial_id INTEGER,
            periode TEXT,
            objectif_ca REAL DEFAULT 0,
            ca_realise REAL DEFAULT 0,
            nb_visites_cible INTEGER DEFAULT 0,
            nb_visites_realise INTEGER DEFAULT 0,
            commission_calculee REAL DEFAULT 0,
            commission_payee INTEGER DEFAULT 0,
            statut TEXT DEFAULT 'en_cours',
            created_at TEXT,
            FOREIGN KEY(commercial_id) REFERENCES users(id)
        )
    """)

    # ─── Tournées ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tournees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commercial_id INTEGER,
            date_tournee TEXT,
            zone TEXT,
            nb_visites_prevues INTEGER DEFAULT 0,
            nb_visites_realisees INTEGER DEFAULT 0,
            statut TEXT DEFAULT 'planifiee',
            distance_km REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(commercial_id) REFERENCES users(id)
        )
    """)

    # ─── Tournées points (visites planifiées) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tournee_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournee_id INTEGER NOT NULL,
            prospect_id INTEGER,
            client_id INTEGER,
            ordre INTEGER DEFAULT 0,
            statut TEXT DEFAULT 'a_visiter',
            heure_prevue TEXT,
            heure_reelle TEXT,
            FOREIGN KEY(tournee_id) REFERENCES tournees(id),
            FOREIGN KEY(prospect_id) REFERENCES prospects(id),
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    """)

    # ─── Relances automatiques ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS relances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            prospect_id INTEGER,
            client_id INTEGER,
            opportunite_id INTEGER,
            commercial_id INTEGER,
            date_prevue TEXT,
            date_realisee TEXT,
            statut TEXT DEFAULT 'a_faire',
            message TEXT,
            created_at TEXT,
            FOREIGN KEY(prospect_id) REFERENCES prospects(id),
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(opportunite_id) REFERENCES opportunites(id),
            FOREIGN KEY(commercial_id) REFERENCES users(id)
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
        "CREATE INDEX IF NOT EXISTS idx_prospects_statut ON prospects(statut)",
        "CREATE INDEX IF NOT EXISTS idx_opp_etape ON opportunites(etape, statut)",
        "CREATE INDEX IF NOT EXISTS idx_activites_date ON activites(date_activite)",
        "CREATE INDEX IF NOT EXISTS idx_relances_date ON relances(date_prevue, statut)",
    ]:
        try:
            cur.execute(idx)
        except Exception:
            pass

    # ─── TRIGGERS ───

    # Trigger 1 : génération code prospect auto
    cur.execute("DROP TRIGGER IF EXISTS trg_prospect_code")
    cur.execute("""
        CREATE TRIGGER trg_prospect_code
        AFTER INSERT ON prospects
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE prospects SET
                code = 'PROS-' || strftime('%Y%m', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 2 : génération code client auto
    cur.execute("DROP TRIGGER IF EXISTS trg_client_code")
    cur.execute("""
        CREATE TRIGGER trg_client_code
        AFTER INSERT ON clients
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE clients SET
                code = 'CLI-' || strftime('%Y%m', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 3 : calcul automatique des montants de devis
    cur.execute("DROP TRIGGER IF EXISTS trg_devis_montants")
    cur.execute("""
        CREATE TRIGGER trg_devis_montants
        AFTER UPDATE OF montant_ht ON devis
        FOR EACH ROW
        BEGIN
            UPDATE devis SET
                tva = NEW.montant_ht * 0.18,
                montant_ttc = NEW.montant_ht * 1.18
            WHERE id = NEW.id;
        END
    """)

    # Trigger 4 : auto-conversion opportunité gagnée → client
    cur.execute("DROP TRIGGER IF EXISTS trg_opp_gagnee")
    cur.execute("""
        CREATE TRIGGER trg_opp_gagnee
        AFTER UPDATE OF statut ON opportunites
        FOR EACH ROW
        WHEN NEW.statut = 'gagnee' AND OLD.statut != 'gagnee'
        BEGIN
            UPDATE opportunites SET
                date_cloture_reelle = datetime('now'),
                probabilite = 100
            WHERE id = NEW.id;
        END
    """)

    # Trigger 5 : mise à jour CA du client après devis accepté
    cur.execute("DROP TRIGGER IF EXISTS trg_devis_accepte")
    cur.execute("""
        CREATE TRIGGER trg_devis_accepte
        AFTER UPDATE OF statut ON devis
        FOR EACH ROW
        WHEN NEW.statut = 'accepte' AND OLD.statut != 'accepte' AND NEW.client_id IS NOT NULL
        BEGIN
            UPDATE clients SET
                chiffre_affaires_total = chiffre_affaires_total + NEW.montant_ttc
            WHERE id = NEW.client_id;
        END
    """)

    conn.commit()
    conn.close()
    print("[INIT] ✅ Base CRM & Ventes prête")


def seed_demo():
    """Génère des données démo si base vide."""
    conn = get_conn()
    cur = conn.cursor()

    from werkzeug.security import generate_password_hash

    # ─── Utilisateurs ───
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        users = [
            ('admin', 'admin123', 'admin', 'Administrateur', 'admin@omega.sn', '+221 77 000 00 00', 'National', 0, 0),
            ('manager', 'manager123', 'manager', 'Fatou Sow', 'fatou@omega.sn', '+221 77 111 11 11', 'Dakar', 15000000, 2.5),
            ('commercial', 'com123', 'commercial', 'Ousmane Ba', 'ousmane@omega.sn', '+221 77 222 22 22', 'Dakar', 8000000, 3.0),
            ('commercial2', 'com123', 'commercial', 'Awa Fall', 'awa@omega.sn', '+221 77 333 33 33', 'Thiès', 7000000, 3.0),
            ('commercial3', 'com123', 'commercial', 'Cheikh Diop', 'cheikh@omega.sn', '+221 77 444 44 44', 'Saint-Louis', 6000000, 3.5),
        ]
        for u in users:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, nom_complet, email, telephone,
                                   zone, objectif_mensuel, commission_pct, actif, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,1,?)
            """, (u[0], generate_password_hash(u[1]), u[2], u[3], u[4], u[5],
                  u[6], u[7], u[8], datetime.now().isoformat()))
        print("[SEED] ✅ 5 utilisateurs créés")

    # Récupérer les commerciaux
    cur.execute("SELECT id FROM users WHERE role='commercial'")
    com_ids = [r[0] for r in cur.fetchall()]

    # ─── Prospects ───
    cur.execute("SELECT COUNT(*) FROM prospects")
    if cur.fetchone()[0] == 0:
        prospects_data = [
            ('SONACOS SA', 'Agro-industrie', 'Mamadou Diop', 'Directeur Achats', '+221 33 839 00 00', 'contact@sonacos.sn', 'Dakar'),
            ('SENELEC', 'Énergie', 'Fatou Ndiaye', 'Responsable Logistique', '+221 33 839 11 11', 'achats@senelec.sn', 'Dakar'),
            ('Ciments du Sahel', 'BTP', 'Ousmane Sall', 'Directeur Général', '+221 33 957 22 22', 'dg@cimentsdusahel.sn', 'Thiès'),
            ('SONATEL', 'Télécoms', 'Awa Diallo', 'Directeur Technique', '+221 33 839 33 33', 'tech@sonatel.sn', 'Dakar'),
            ('SM10 AGRO', 'Agro-industrie', 'Sadio Mané', 'Président', '+221 77 654 28 03', 'contact@sm10agro.sn', 'Dakar'),
            ('CSE (Ciment du Sénégal)', 'BTP', 'Ibrahima Fall', 'Directeur Commercial', '+221 33 836 44 44', 'contact@cse.sn', 'Dakar'),
            ('SEDIMA', 'Agroalimentaire', 'Moussa Traoré', 'Acheteur', '+221 33 879 55 55', 'achat@sedima.sn', 'Dakar'),
            ('SODEFITEX', 'Textile', 'Aïssatou Ba', 'Directrice', '+221 33 991 66 66', 'info@sodefitex.sn', 'Tambacounda'),
            ('SUNEOR', 'Agro-industrie', 'Cheikh Sow', 'Responsable Usine', '+221 33 991 77 77', 'usine@suneor.sn', 'Diourbel'),
            ('PORT AUTONOME DAKAR', 'Logistique', 'Amadou Sall', 'Directeur Opérations', '+221 33 849 88 88', 'contact@portdakar.sn', 'Dakar'),
            ('SONAGED', 'Environnement', 'Fatima Diallo', 'Coordinatrice', '+221 33 859 99 99', 'contact@sonaged.sn', 'Dakar'),
            ('SEN EAU', 'Eau', 'Alioune Ndiaye', 'Directeur Achats', '+221 33 839 10 10', 'achat@seneau.sn', 'Dakar'),
            ('COTONNIÈRE SN', 'Textile', 'Moussa Diop', 'Acheteur', '+221 33 939 11 11', 'achat@cotonniere.sn', 'Dakar'),
            ('SENAC SA', 'Construction', 'Pape Fall', 'Directeur', '+221 33 869 12 12', 'info@senac.sn', 'Dakar'),
            ('Transrail', 'Transport', 'Amadou Ba', 'Responsable Fret', '+221 33 839 13 13', 'fret@transrail.sn', 'Dakar'),
        ]

        statuts = ['nouveau', 'contacte', 'qualifie', 'en_negociation', 'converti', 'perdu']
        sources = ['site_web', 'salon', 'prospection', 'recommandation', 'appel_entrant', 'linkedin']

        for i, p in enumerate(prospects_data):
            statut = random.choice(statuts[:4])  # Pas converti/perdu pour l'instant
            score = random.randint(20, 95) if statut != 'nouveau' else random.randint(10, 40)
            cur.execute("""
                INSERT INTO prospects
                (code, raison_sociale, secteur, contact_nom, contact_fonction,
                 telephone, email, ville, pays, source, statut, score, commercial_id,
                 notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None, p[0], p[1], p[2], p[3], p[4], p[5], p[6], 'Sénégal',
                  random.choice(sources), statut, score,
                  random.choice(com_ids) if com_ids else None,
                  f'Prospect qualifié - {p[1]}', datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(prospects_data)} prospects créés")

    # ─── Clients ───
    cur.execute("SELECT COUNT(*) FROM clients")
    if cur.fetchone()[0] == 0:
        clients_data = [
            ('BOLLORÉ LOGISTICS', 'Logistique', 'Cheikh Ndiaye', '+221 33 839 20 20', 'contact@bollore.sn', 'Dakar', 45000000),
            ('TOTAL SÉNÉGAL', 'Pétrole', 'Amadou Sarr', '+221 33 839 21 21', 'contact@total.sn', 'Dakar', 120000000),
            ('ECOBANK', 'Banque', 'Fatou Diallo', '+221 33 839 22 22', 'contact@ecobank.sn', 'Dakar', 35000000),
            ('SONATEL BUSINESS', 'Télécoms', 'Ousmane Fall', '+221 33 839 23 23', 'business@sonatel.sn', 'Dakar', 78000000),
            ('SENELEC PME', 'Énergie', 'Awa Sy', '+221 33 839 24 24', 'pme@senelec.sn', 'Dakar', 22000000),
            ('MICROFINANCE U-IMCEC', 'Finance', 'Ibrahima Ba', '+221 33 839 25 25', 'info@uimcec.sn', 'Thiès', 18000000),
            ('KIRÈNE SÉNÉGAL', 'Distribution', 'Mariama Sow', '+221 33 839 26 26', 'contact@kirene.sn', 'Dakar', 41000000),
            ('SOBOA (Aqualma)', 'Agro-industrie', 'Amadou Diallo', '+221 33 839 27 27', 'contact@soboa.sn', 'Saint-Louis', 32000000),
        ]
        for c in clients_data:
            cur.execute("""
                INSERT INTO clients
                (code, raison_sociale, secteur, contact_nom, telephone, email,
                 ville, pays, chiffre_affaires_total, commercial_id,
                 date_conversion, actif, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,1,?)
            """, (None, c[0], c[1], c[2], c[3], c[4], c[5], 'Sénégal', c[6],
                  random.choice(com_ids) if com_ids else None,
                  (datetime.now() - timedelta(days=random.randint(30, 400))).strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(clients_data)} clients créés")

    # Récupérer IDs pour la suite
    cur.execute("SELECT id FROM prospects LIMIT 15")
    prosp_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT id FROM clients LIMIT 8")
    cli_ids = [r[0] for r in cur.fetchall()]

    # ─── Opportunités (Pipeline) ───
    cur.execute("SELECT COUNT(*) FROM opportunites")
    if cur.fetchone()[0] == 0:
        etapes = ['qualification', 'analyse', 'proposition', 'negociation', 'gagnee', 'perdue']
        titres = [
            'Fourniture équipements agricoles',
            'Contrat maintenance annuelle',
            'Déploiement ERP multi-sites',
            'Prestation conseil transformation',
            'Livraison matériels logistiques',
            'Formation équipes techniques',
            'Installation système de traçabilité',
            'Maintenance préventive industrielle',
            'Audit processus qualité',
            'Extension réseau télécom',
            'Fourniture consommables',
            'Réhabilitation entrepôt',
        ]

        for i in range(25):
            etape = random.choice(etapes)
            montant = random.randint(500000, 50000000)
            proba = {'qualification': 20, 'analyse': 40, 'proposition': 60,
                     'negociation': 80, 'gagnee': 100, 'perdue': 0}.get(etape, 10)
            statut = 'gagnee' if etape == 'gagnee' else 'perdue' if etape == 'perdue' else 'ouverte'

            date_prev = datetime.now() + timedelta(days=random.randint(-30, 90))
            date_reelle = (datetime.now() - timedelta(days=random.randint(1, 60))).strftime('%Y-%m-%d') if statut != 'ouverte' else None

            cur.execute("""
                INSERT INTO opportunites
                (titre, prospect_id, client_id, commercial_id, montant_estime, probabilite,
                 etape, date_cloture_prevue, date_cloture_reelle, statut, source, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (random.choice(titres),
                  random.choice(prosp_ids) if random.random() < 0.7 and prosp_ids else None,
                  random.choice(cli_ids) if random.random() < 0.3 and cli_ids else None,
                  random.choice(com_ids) if com_ids else None,
                  montant, proba, etape,
                  date_prev.strftime('%Y-%m-%d'),
                  date_reelle, statut,
                  random.choice(['site_web', 'salon', 'prospection', 'appel_entrant']),
                  'Opportunité créée par le commercial',
                  datetime.now().isoformat()))
        print("[SEED] ✅ 25 opportunités créées")

    # ─── Activités ───
    cur.execute("SELECT COUNT(*) FROM activites")
    if cur.fetchone()[0] == 0:
        types = ['appel', 'visite', 'email', 'reunion', 'demo']
        sujets = [
            'Présentation de la solution',
            'Suivi de la proposition commerciale',
            'Relance après devis',
            'Découverte du besoin',
            'Démonstration produit',
            'Négociation tarifaire',
            'Visite des installations',
            'Signature du contrat',
        ]
        resultats = ['positif', 'a_suivre', 'negatif', 'sans_reponse']

        for i in range(50):
            date_a = datetime.now() - timedelta(days=random.randint(0, 60))
            cur.execute("""
                INSERT INTO activites
                (type, sujet, prospect_id, client_id, commercial_id, date_activite,
                 duree_min, resultat, notes, prochaine_action, date_prochaine_action, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (random.choice(types), random.choice(sujets),
                  random.choice(prosp_ids) if prosp_ids and random.random() < 0.7 else None,
                  random.choice(cli_ids) if cli_ids and random.random() < 0.4 else None,
                  random.choice(com_ids) if com_ids else None,
                  date_a.isoformat(),
                  random.choice([15, 30, 45, 60, 90]),
                  random.choice(resultats),
                  'Compte-rendu activité',
                  random.choice(['Envoyer devis', 'Rappeler la semaine prochaine', 'Planifier démo', 'Aucune']),
                  (date_a + timedelta(days=random.randint(3, 14))).strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
        print("[SEED] ✅ 50 activités créées")

    # ─── Devis ───
    cur.execute("SELECT COUNT(*) FROM devis")
    if cur.fetchone()[0] == 0:
        statuts_devis = ['brouillon', 'envoye', 'accepte', 'refuse', 'expire']
        for i in range(15):
            statut = random.choice(statuts_devis)
            montant = random.randint(500000, 30000000)
            cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM devis")
            nid = cur.fetchone()[0]
            numero = f"DEV-{datetime.now().strftime('%Y%m')}-{nid:04d}"

            date_em = datetime.now() - timedelta(days=random.randint(0, 60))
            cur.execute("""
                INSERT INTO devis
                (numero, client_id, prospect_id, commercial_id, date_emission, date_validite,
                 montant_ht, tva, montant_ttc, statut, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (numero,
                  random.choice(cli_ids) if cli_ids and random.random() < 0.6 else None,
                  random.choice(prosp_ids) if prosp_ids and random.random() < 0.5 else None,
                  random.choice(com_ids) if com_ids else None,
                  date_em.strftime('%Y-%m-%d'),
                  (date_em + timedelta(days=30)).strftime('%Y-%m-%d'),
                  montant, montant * 0.18, montant * 1.18, statut,
                  'Devis commercial',
                  datetime.now().isoformat()))
        print("[SEED] ✅ 15 devis créés")

    # ─── Objectifs ───
    cur.execute("SELECT COUNT(*) FROM objectifs")
    if cur.fetchone()[0] == 0:
        periode = datetime.now().strftime('%Y-%m')
        for cid in com_ids:
            obj_ca = random.randint(5000000, 15000000)
            ca_real = random.randint(int(obj_ca * 0.3), int(obj_ca * 1.1))
            visites_cible = random.randint(20, 40)
            visites_real = random.randint(10, visites_cible)

            cur.execute("""
                INSERT INTO objectifs
                (commercial_id, periode, objectif_ca, ca_realise,
                 nb_visites_cible, nb_visites_realise, commission_calculee,
                 commission_payee, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (cid, periode, obj_ca, ca_real, visites_cible, visites_real,
                  ca_real * 0.03, 0, 'en_cours', datetime.now().isoformat()))
        print("[SEED] ✅ Objectifs créés")

    # ─── Relances ───
    cur.execute("SELECT COUNT(*) FROM relances")
    if cur.fetchone()[0] == 0:
        for i in range(20):
            date_prev = datetime.now() + timedelta(days=random.randint(-5, 15))
            statut = 'a_faire' if date_prev > datetime.now() else random.choice(['fait', 'retard'])

            cur.execute("""
                INSERT INTO relances
                (type, prospect_id, commercial_id, date_prevue, statut, message, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (random.choice(['appel', 'email', 'visite']),
                  random.choice(prosp_ids) if prosp_ids else None,
                  random.choice(com_ids) if com_ids else None,
                  date_prev.strftime('%Y-%m-%d'),
                  statut,
                  'Relance automatique après contact',
                  datetime.now().isoformat()))
        print("[SEED] ✅ Relances créées")

    conn.commit()
    conn.close()
    print("[SEED] ✅ Données démo CRM générées")


if __name__ == '__main__':
    init_db()
