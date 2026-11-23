

"""
🎓 Formation Professionnelle — Base de données
Formations · Sessions · Apprenants · Évaluations · Certificats · Financement 3FPT
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = '/app/data/formation_pro.db'


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()

    # ─── Utilisateurs (formateurs + admin + bailleurs) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'formateur',
            nom_complet TEXT,
            email TEXT,
            telephone TEXT,
            specialite TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Centres de formation ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS centres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            type TEXT,
            adresse TEXT,
            ville TEXT,
            region TEXT,
            telephone TEXT,
            email TEXT,
            responsable TEXT,
            num_agrement TEXT,
            capacite_totale INTEGER DEFAULT 0,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Salles de formation ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS salles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            centre_id INTEGER,
            nom TEXT NOT NULL,
            capacite INTEGER DEFAULT 20,
            equipements TEXT,
            etage TEXT,
            disponible INTEGER DEFAULT 1,
            created_at TEXT,
            FOREIGN KEY(centre_id) REFERENCES centres(id)
        )
    """)

    # ─── Formations (catalogue) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS formations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            domaine TEXT,
            description TEXT,
            niveau TEXT,
            duree_heures INTEGER DEFAULT 0,
            duree_mois INTEGER DEFAULT 0,
            cout_formation REAL DEFAULT 0,
            prerequis TEXT,
            debouches TEXT,
            certification TEXT,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Formateurs ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS formateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom_complet TEXT NOT NULL,
            telephone TEXT,
            email TEXT,
            specialite TEXT,
            diplome TEXT,
            annees_experience INTEGER DEFAULT 0,
            tarif_horaire REAL DEFAULT 0,
            statut TEXT DEFAULT 'disponible',
            created_at TEXT
        )
    """)

    # ─── Sessions de formation ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            formation_id INTEGER,
            centre_id INTEGER,
            salle_id INTEGER,
            formateur_id INTEGER,
            date_debut TEXT,
            date_fin TEXT,
            horaire TEXT,
            capacite INTEGER DEFAULT 20,
            nb_inscrits INTEGER DEFAULT 0,
            financement TEXT,
            cout_total REAL DEFAULT 0,
            statut TEXT DEFAULT 'planifiee',
            created_at TEXT,
            FOREIGN KEY(formation_id) REFERENCES formations(id),
            FOREIGN KEY(centre_id) REFERENCES centres(id),
            FOREIGN KEY(salle_id) REFERENCES salles(id),
            FOREIGN KEY(formateur_id) REFERENCES formateurs(id)
        )
    """)

    # ─── Apprenants ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS apprenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_apprenant TEXT UNIQUE,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            date_naissance TEXT,
            sexe TEXT,
            telephone TEXT,
            email TEXT,
            adresse TEXT,
            ville TEXT,
            region TEXT,
            niveau_etudes TEXT,
            situation TEXT,
            qr_code TEXT,
            statut TEXT DEFAULT 'actif',
            date_inscription TEXT,
            created_at TEXT
        )
    """)

    # ─── Inscriptions ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            apprenant_id INTEGER,
            date_inscription TEXT,
            statut TEXT DEFAULT 'inscrit',
            frais_payes REAL DEFAULT 0,
            reste_a_payer REAL DEFAULT 0,
            financement TEXT,
            bailleur TEXT,
            created_at TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id),
            FOREIGN KEY(apprenant_id) REFERENCES apprenants(id)
        )
    """)

    # ─── Présences ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS presences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inscription_id INTEGER,
            session_id INTEGER,
            date_presence TEXT,
            present INTEGER DEFAULT 1,
            heures INTEGER DEFAULT 4,
            observation TEXT,
            created_at TEXT,
            FOREIGN KEY(inscription_id) REFERENCES inscriptions(id),
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
    """)

    # ─── Évaluations ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inscription_id INTEGER,
            session_id INTEGER,
            type_eval TEXT,
            libelle TEXT,
            note REAL DEFAULT 0,
            note_max REAL DEFAULT 20,
            date_eval TEXT,
            commentaire TEXT,
            created_at TEXT,
            FOREIGN KEY(inscription_id) REFERENCES inscriptions(id),
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
    """)

    # ─── Certificats ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS certificats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_certificat TEXT UNIQUE,
            inscription_id INTEGER,
            apprenant_id INTEGER,
            formation_id INTEGER,
            session_id INTEGER,
            date_emission TEXT,
            note_finale REAL DEFAULT 0,
            mention TEXT,
            qr_code TEXT,
            statut TEXT DEFAULT 'valide',
            created_at TEXT,
            FOREIGN KEY(inscription_id) REFERENCES inscriptions(id),
            FOREIGN KEY(apprenant_id) REFERENCES apprenants(id),
            FOREIGN KEY(formation_id) REFERENCES formations(id),
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
    """)

    # ─── Financements (3FPT, entreprises) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS financements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            bailleur TEXT NOT NULL,
            type_bailleur TEXT,
            programme TEXT,
            montant_total REAL DEFAULT 0,
            montant_utilise REAL DEFAULT 0,
            date_debut TEXT,
            date_fin TEXT,
            contact TEXT,
            telephone TEXT,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Partenariats entreprises ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS partenariats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entreprise TEXT NOT NULL,
            secteur TEXT,
            contact_nom TEXT,
            telephone TEXT,
            email TEXT,
            type_partenariat TEXT,
            formations_concernees TEXT,
            nb_places_stage INTEGER DEFAULT 0,
            nb_embauches INTEGER DEFAULT 0,
            date_signature TEXT,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Placement post-formation ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS placements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apprenant_id INTEGER,
            inscription_id INTEGER,
            type TEXT,
            entreprise TEXT,
            poste TEXT,
            salaire_mensuel REAL DEFAULT 0,
            date_debut TEXT,
            statut TEXT DEFAULT 'actif',
            commentaire TEXT,
            created_at TEXT,
            FOREIGN KEY(apprenant_id) REFERENCES apprenants(id),
            FOREIGN KEY(inscription_id) REFERENCES inscriptions(id)
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
        "CREATE INDEX IF NOT EXISTS idx_sessions_formation ON sessions(formation_id)",
        "CREATE INDEX IF NOT EXISTS idx_inscriptions_session ON inscriptions(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_inscriptions_apprenant ON inscriptions(apprenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_presences_inscription ON presences(inscription_id)",
        "CREATE INDEX IF NOT EXISTS idx_evaluations_inscription ON evaluations(inscription_id)",
    ]:
        try:
            cur.execute(idx)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # TRIGGERS
    # ═══════════════════════════════════════════════════════

    # Trigger 1 : code centre auto
    cur.execute("DROP TRIGGER IF EXISTS trg_centre_code")
    cur.execute("""
        CREATE TRIGGER trg_centre_code
        AFTER INSERT ON centres
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE centres SET
                code = 'CTR-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 2 : code formation auto
    cur.execute("DROP TRIGGER IF EXISTS trg_formation_code")
    cur.execute("""
        CREATE TRIGGER trg_formation_code
        AFTER INSERT ON formations
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE formations SET
                code = 'FOR-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 3 : code session auto + MAJ nb_inscrits
    cur.execute("DROP TRIGGER IF EXISTS trg_session_code")
    cur.execute("""
        CREATE TRIGGER trg_session_code
        AFTER INSERT ON sessions
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE sessions SET
                code = 'SES-' || strftime('%Y%m', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 4 : numéro apprenant auto + QR
    cur.execute("DROP TRIGGER IF EXISTS trg_apprenant_numero")
    cur.execute("""
        CREATE TRIGGER trg_apprenant_numero
        AFTER INSERT ON apprenants
        FOR EACH ROW
        WHEN NEW.numero_apprenant IS NULL OR NEW.numero_apprenant = ''
        BEGIN
            UPDATE apprenants SET
                numero_apprenant = 'APP-' || strftime('%Y', 'now') || '-' || substr('000000' || NEW.id, -6),
                qr_code = 'FORM|APP|' || NEW.id || '|' || NEW.telephone
            WHERE id = NEW.id;
        END
    """)

    # Trigger 5 : numéro certificat auto + QR
    cur.execute("DROP TRIGGER IF EXISTS trg_certificat_numero")
    cur.execute("""
        CREATE TRIGGER trg_certificat_numero
        AFTER INSERT ON certificats
        FOR EACH ROW
        WHEN NEW.numero_certificat IS NULL OR NEW.numero_certificat = ''
        BEGIN
            UPDATE certificats SET
                numero_certificat = 'CERT-' || strftime('%Y', 'now') || '-' || substr('00000' || NEW.id, -5),
                qr_code = 'FORM|CERT|' || NEW.id
            WHERE id = NEW.id;
        END
    """)

    conn.commit()
    conn.close()
    print("[INIT] ✅ Base Formation Professionnelle prête")


def seed_demo():
    """Génère des données démo si base vide."""
    conn = get_conn()
    cur = conn.cursor()

    from werkzeug.security import generate_password_hash

    # ─── Users ───
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        users = [
            ('admin', 'admin123', 'admin', 'Administrateur', 'admin@formation.sn', '+221 77 000 00 00', 'Direction'),
            ('directeur', 'dir123', 'directeur', 'Mamadou Diop', 'dir@formation.sn', '+221 77 111 11 11', 'Direction'),
            ('formateur1', 'form123', 'formateur', 'Ibrahima Sall', 'ibrahima@formation.sn', '+221 77 222 22 22', 'BTP'),
            ('formateur2', 'form123', 'formateur', 'Awa Fall', 'awa@formation.sn', '+221 77 333 33 33', 'Numérique'),
            ('formateur3', 'form123', 'formateur', 'Ousmane Ba', 'ousmane@formation.sn', '+221 77 444 44 44', 'Agro'),
        ]
        for u in users:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, nom_complet, email, telephone, specialite, actif, created_at)
                VALUES (?,?,?,?,?,?,?,1,?)
            """, (u[0], generate_password_hash(u[1]), u[2], u[3], u[4], u[5], u[6], datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(users)} utilisateurs créés")

    # ─── Centres ───
    cur.execute("SELECT COUNT(*) FROM centres")
    if cur.fetchone()[0] == 0:
        centres = [
            ('Centre 3FPT Dakar', 'public', 'Zone industrielle', 'Dakar', 'Dakar', '+221 33 839 10 10', '3FPT-DKR-001', 500),
            ('CFP Thiès', 'public', 'Route de Dakar', 'Thiès', 'Thiès', '+221 33 951 10 10', '3FPT-THS-002', 300),
            ('Centre Formation Ziguinchor', 'public', 'Centre-ville', 'Ziguinchor', 'Ziguinchor', '+221 33 991 10 10', '3FPT-ZIG-003', 250),
            ('Institut Formation Saint-Louis', 'prive', 'Quartier Nord', 'Saint-Louis', 'Saint-Louis', '+221 33 961 10 10', 'ONFP-SL-004', 200),
            ('CFP Kaolack', 'public', 'Route Kaolack', 'Kaolack', 'Kaolack', '+221 33 941 10 10', '3FPT-KLK-005', 180),
        ]
        for c in centres:
            cur.execute("""
                INSERT INTO centres (code, nom, type, adresse, ville, region, telephone, num_agrement, capacite_totale, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (None, c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7], datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(centres)} centres créés")

    cur.execute("SELECT id FROM centres")
    centre_ids = [r[0] for r in cur.fetchall()]

    # ─── Salles ───
    cur.execute("SELECT COUNT(*) FROM salles")
    if cur.fetchone()[0] == 0:
        n = 0
        for cid in centre_ids:
            for i in range(random.randint(3, 6)):
                cur.execute("""
                    INSERT INTO salles (centre_id, nom, capacite, equipements, etage, disponible, created_at)
                    VALUES (?,?,?,?,?,1,?)
                """, (cid, f'Salle {i+1}', random.choice([15, 20, 25, 30, 40]),
                      random.choice(['Vidéoprojecteur, Tableau blanc', 'Ordinateurs, Wi-Fi', 'Atelier pratique', 'Tableau interactif']),
                      random.choice(['RDC', '1er étage', '2ème étage']),
                      datetime.now().isoformat()))
                n += 1
        print(f"[SEED] ✅ {n} salles créées")

    # ─── Formations (adapté Sénégal) ───
    cur.execute("SELECT COUNT(*) FROM formations")
    if cur.fetchone()[0] == 0:
        formations = [
            # BTP
            ('Maçonnerie moderne', 'BTP', 'Techniques de maçonnerie, lecture de plans', 'Débutant', 240, 3, 150000, 'Aucun', 'Maçon, Chef d\'équipe', 'Certificat professionnel'),
            ('Électricité bâtiment', 'BTP', 'Installation électrique, normes de sécurité', 'Débutant', 300, 4, 180000, 'Niveau BEPC', 'Électricien qualifié', 'Certificat professionnel'),
            ('Soudure à l\'arc', 'BTP', 'Techniques de soudure, sécurité', 'Débutant', 180, 2, 120000, 'Aucun', 'Soudeur', 'Attestation'),
            # Agro
            ('Transformation mangue', 'Agro', 'Séchage, pasteurisation, conditionnement', 'Intermédiaire', 120, 2, 100000, 'Aucun', 'Transformateur agro', 'Certificat'),
            ('Aviculture moderne', 'Agro', 'Élevage poulets de chair, pondeuses', 'Débutant', 90, 1, 80000, 'Aucun', 'Aviculteur', 'Attestation'),
            ('Maraîchage intensif', 'Agro', 'Cultures maraîchères, irrigation', 'Débutant', 120, 2, 90000, 'Aucun', 'Maraîcher', 'Certificat'),
            # Numérique
            ('Développement web', 'Numérique', 'HTML, CSS, JavaScript, Python', 'Débutant', 480, 6, 350000, 'Niveau Bac', 'Développeur web', 'Certificat professionnel'),
            ('Bureautique avancée', 'Numérique', 'Word, Excel, PowerPoint', 'Débutant', 120, 2, 80000, 'Aucun', 'Assistant administratif', 'Attestation'),
            ('Maintenance informatique', 'Numérique', 'Réparation ordinateurs, réseaux', 'Intermédiaire', 240, 3, 180000, 'Niveau Bac', 'Technicien IT', 'Certificat'),
            # Commerce
            ('Gestion commerciale', 'Commerce', 'Techniques de vente, comptabilité', 'Débutant', 180, 3, 150000, 'Niveau BEPC', 'Commercial, Vendeur', 'Certificat'),
            ('E-commerce & digital', 'Commerce', 'Vente en ligne, réseaux sociaux', 'Débutant', 90, 1, 70000, 'Aucun', 'E-commerçant', 'Attestation'),
            # Santé
            ('Aide-soignant', 'Santé', 'Soins de base, hygiène, premiers secours', 'Débutant', 360, 6, 250000, 'Niveau BEPC', 'Aide-soignant', 'Certificat professionnel'),
            ('Secourisme', 'Santé', 'Gestes qui sauvent, RCP', 'Débutant', 30, 1, 30000, 'Aucun', 'Secouriste', 'Attestation'),
            # Hôtellerie
            ('Cuisine professionnelle', 'Hôtellerie', 'Techniques culinaires, hygiène HACCP', 'Débutant', 300, 4, 200000, 'Aucun', 'Commis, Cuisinier', 'Certificat'),
            ('Service en salle', 'Hôtellerie', 'Service, accueil, gestion restaurant', 'Débutant', 120, 2, 100000, 'Aucun', 'Serveur', 'Attestation'),
        ]
        for f in formations:
            cur.execute("""
                INSERT INTO formations (code, nom, domaine, description, niveau, duree_heures, duree_mois,
                                          cout_formation, prerequis, debouches, certification, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (None, f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7], f[8], f[9], datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(formations)} formations créées")

    # ─── Formateurs ───
    cur.execute("SELECT COUNT(*) FROM formateurs")
    if cur.fetchone()[0] == 0:
        formateurs = [
            ('Ibrahima Sall', '+221 77 222 22 22', 'ibrahima@formation.sn', 'BTP / Maçonnerie', 'Ingénieur Génie Civil', 12, 15000),
            ('Awa Fall', '+221 77 333 33 33', 'awa@formation.sn', 'Numérique / Web', 'Master Informatique', 8, 18000),
            ('Ousmane Ba', '+221 77 444 44 44', 'ousmane@formation.sn', 'Agro / Transformation', 'Ingénieur Agro', 10, 12000),
            ('Fatou Diallo', '+221 77 555 55 55', 'fatou@formation.sn', 'Commerce / Vente', 'MBA Management', 15, 20000),
            ('Cheikh Sow', '+221 77 666 66 66', 'cheikh@formation.sn', 'Santé / Soins', 'Infirmier diplômé', 20, 22000),
            ('Mariama Ba', '+221 77 777 77 77', 'mariama@formation.sn', 'Cuisine / Hôtellerie', 'Chef cuisinier', 18, 16000),
            ('Pape Diop', '+221 77 888 88 88', 'pape@formation.sn', 'Électricité', 'Technicien supérieur', 14, 14000),
            ('Ndèye Sy', '+221 77 999 99 99', 'ndeye@formation.sn', 'Bureautique', 'Formatrice professionnelle', 6, 10000),
        ]
        for f in formateurs:
            cur.execute("""
                INSERT INTO formateurs (code, nom_complet, telephone, email, specialite, diplome,
                                         annees_experience, tarif_horaire, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?, 'disponible', ?)
            """, (None, f[0], f[1], f[2], f[3], f[4], f[5], f[6], datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(formateurs)} formateurs créés")

    # ─── Sessions ───
    cur.execute("SELECT COUNT(*) FROM sessions")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, duree_mois FROM formations")
        form_rows = cur.fetchall()
        cur.execute("SELECT id FROM centres")
        c_ids = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT id, centre_id FROM salles")
        salle_rows = cur.fetchall()
        cur.execute("SELECT id FROM formateurs")
        formateur_ids = [r[0] for r in cur.fetchall()]

        n = 0
        for i in range(25):
            f = random.choice(form_rows)
            date_debut = datetime.now() + timedelta(days=random.randint(-60, 90))
            duree_j = (f['duree_mois'] or 1) * 30
            date_fin = date_debut + timedelta(days=duree_j)
            capacite = random.choice([15, 20, 25, 30])

            if date_fin < datetime.now():
                statut = 'terminee'
                nb_inscrits = random.randint(10, capacite)
            elif date_debut < datetime.now():
                statut = 'en_cours'
                nb_inscrits = random.randint(5, capacite)
            else:
                statut = 'planifiee'
                nb_inscrits = random.randint(0, capacite // 2)

            cid = random.choice(c_ids)
            salles_centre = [s for s in salle_rows if s['centre_id'] == cid]
            sid = random.choice(salles_centre)['id'] if salles_centre else None

            cur.execute("""
                INSERT INTO sessions (code, formation_id, centre_id, salle_id, formateur_id,
                                       date_debut, date_fin, horaire, capacite, nb_inscrits,
                                       financement, cout_total, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None, f['id'], cid, sid, random.choice(formateur_ids),
                  date_debut.strftime('%Y-%m-%d'), date_fin.strftime('%Y-%m-%d'),
                  random.choice(['8h-12h', '14h-18h', '8h-17h']),
                  capacite, nb_inscrits,
                  random.choice(['3FPT', 'autofinance', 'entreprise', '3FPT', '3FPT']),
                  random.randint(500000, 3000000),
                  statut, datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} sessions créées")

    # ─── Apprenants ───
    cur.execute("SELECT COUNT(*) FROM apprenants")
    if cur.fetchone()[0] == 0:
        prenoms_h = ['Moussa', 'Amadou', 'Ibrahima', 'Cheikh', 'Ousmane', 'Mamadou', 'Alioune', 'Babacar', 'Modou', 'Pape']
        prenoms_f = ['Fatou', 'Awa', 'Aminata', 'Mariama', 'Aïssatou', 'Marième', 'Ndèye', 'Khady', 'Aïda', 'Sokhna']
        noms = ['Diop', 'Ndiaye', 'Sall', 'Fall', 'Ba', 'Diallo', 'Sow', 'Sy', 'Faye', 'Gueye', 'Mbaye', 'Camara']
        regions = [('Dakar', 'Dakar'), ('Thiès', 'Thiès'), ('Saint-Louis', 'Saint-Louis'),
                   ('Ziguinchor', 'Ziguinchor'), ('Kaolack', 'Kaolack'), ('Touba', 'Diourbel')]
        niveaux = ['Aucun', 'Primaire', 'BEPC', 'BAC', 'BAC+2']
        situations = ['Sans emploi', 'Étudiant', 'Employé', 'Sous-employé', 'Apprenti']

        n = 0
        for i in range(80):
            sexe = random.choice(['M', 'F'])
            prenom = random.choice(prenoms_h if sexe == 'M' else prenoms_f)
            nom = random.choice(noms)
            age = random.randint(18, 35)
            date_naiss = (datetime.now() - timedelta(days=age*365)).strftime('%Y-%m-%d')
            ville, region = random.choice(regions)

            cur.execute("""
                INSERT INTO apprenants (numero_apprenant, nom, prenom, date_naissance, sexe,
                                          telephone, email, adresse, ville, region, niveau_etudes,
                                          situation, statut, date_inscription, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'actif', ?, ?)
            """, (None, nom, prenom, date_naiss, sexe,
                  f'+221 77 {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}',
                  f'{prenom.lower()}.{nom.lower()}@email.sn',
                  f'Quartier {random.choice(["Médina", "Plateau", "Grand Dakar", "Yoff", "Parcelles"])}',
                  ville, region,
                  random.choice(niveaux),
                  random.choice(situations),
                  (datetime.now() - timedelta(days=random.randint(0, 180))).strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} apprenants créés")

    # ─── Inscriptions ───
    cur.execute("SELECT COUNT(*) FROM inscriptions")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, capacite FROM sessions")
        sessions = cur.fetchall()
        cur.execute("SELECT id FROM apprenants")
        appr_ids = [r[0] for r in cur.fetchall()]

        n = 0
        for s in sessions:
            nb = random.randint(3, min(s['capacite'], 15))
            selected = random.sample(appr_ids, min(nb, len(appr_ids)))
            for aid in selected:
                financement = random.choice(['3FPT', 'autofinance', 'entreprise'])
                frais = random.randint(0, 150000)
                cur.execute("""
                    INSERT INTO inscriptions (session_id, apprenant_id, date_inscription, statut,
                                                frais_payes, reste_a_payer, financement, bailleur, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (s['id'], aid,
                      (datetime.now() - timedelta(days=random.randint(0, 60))).strftime('%Y-%m-%d'),
                      'inscrit',
                      frais, max(0, 150000 - frais),
                      financement,
                      '3FPT' if financement == '3FPT' else None,
                      datetime.now().isoformat()))
                n += 1
        print(f"[SEED] ✅ {n} inscriptions créées")

    # ─── Présences ───
    cur.execute("SELECT COUNT(*) FROM presences")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, session_id FROM inscriptions LIMIT 100")
        inscriptions = cur.fetchall()
        n = 0
        for ins in inscriptions:
            for _ in range(random.randint(2, 8)):
                date_p = datetime.now() - timedelta(days=random.randint(0, 30))
                cur.execute("""
                    INSERT INTO presences (inscription_id, session_id, date_presence,
                                             present, heures, created_at)
                    VALUES (?,?,?,?,?,?)
                """, (ins['id'], ins['session_id'], date_p.strftime('%Y-%m-%d'),
                      random.choice([1, 1, 1, 0]),
                      random.choice([4, 6, 8]),
                      datetime.now().isoformat()))
                n += 1
        print(f"[SEED] ✅ {n} présences enregistrées")

    # ─── Évaluations ───
    cur.execute("SELECT COUNT(*) FROM evaluations")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, session_id FROM inscriptions LIMIT 80")
        inscriptions = cur.fetchall()
        n = 0
        for ins in inscriptions:
            for _ in range(random.randint(1, 3)):
                note = random.uniform(8, 18)
                cur.execute("""
                    INSERT INTO evaluations (inscription_id, session_id, type_eval, libelle,
                                               note, note_max, date_eval, commentaire, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (ins['id'], ins['session_id'],
                      random.choice(['quiz', 'projet', 'examen_final', 'travaux_pratiques']),
                      random.choice(['Quiz module 1', 'Projet pratique', 'Examen final', 'TP atelier']),
                      round(note, 1), 20,
                      (datetime.now() - timedelta(days=random.randint(0, 60))).strftime('%Y-%m-%d'),
                      random.choice(['Très bon travail', 'Peut mieux faire', 'Excellent', 'À revoir']),
                      datetime.now().isoformat()))
                n += 1
        print(f"[SEED] ✅ {n} évaluations créées")

    # ─── Certificats (pour sessions terminées) ───
    cur.execute("SELECT COUNT(*) FROM certificats")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            SELECT i.id AS ins_id, i.apprenant_id, s.formation_id, s.id AS session_id
            FROM inscriptions i
            JOIN sessions s ON s.id=i.session_id
            WHERE s.statut='terminee'
            LIMIT 30
        """)
        termines = cur.fetchall()
        n = 0
        for t in termines:
            note_finale = random.uniform(10, 18)
            mention = 'Excellent' if note_finale >= 16 else 'Très bien' if note_finale >= 14 else 'Bien' if note_finale >= 12 else 'Passable'
            cur.execute("""
                INSERT INTO certificats (numero_certificat, inscription_id, apprenant_id, formation_id,
                                           session_id, date_emission, note_finale, mention, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?, 'valide', ?)
            """, (None, t['ins_id'], t['apprenant_id'], t['formation_id'], t['session_id'],
                  (datetime.now() - timedelta(days=random.randint(0, 60))).strftime('%Y-%m-%d'),
                  round(note_finale, 1), mention,
                  datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} certificats émis")

    # ─── Financements ───
    cur.execute("SELECT COUNT(*) FROM financements")
    if cur.fetchone()[0] == 0:
        financements = [
            ('3FPT', 'public', 'Formation professionnelle 2026', 500000000, 280000000),
            ('ONFP', 'public', 'Appui centres privés', 150000000, 75000000),
            ('GIZ', 'cooperation', 'Projet ProAgri', 200000000, 120000000),
            ('AFD', 'cooperation', 'Insertion jeunes', 300000000, 180000000),
            ('USAID', 'cooperation', 'Youth Employability', 250000000, 90000000),
        ]
        for f in financements:
            cur.execute("""
                INSERT INTO financements (code, bailleur, type_bailleur, programme, montant_total,
                                            montant_utilise, date_debut, date_fin, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?, 'actif', ?)
            """, (None, f[0], f[1], f[2], f[3], f[4],
                  '2026-01-01', '2026-12-31',
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(financements)} financements créés")

    # ─── Partenariats ───
    cur.execute("SELECT COUNT(*) FROM partenariats")
    if cur.fetchone()[0] == 0:
        partenariats = [
            ('SENELEC', 'Énergie', 'Amadou Sarr', '+221 33 839 11 11', 'Stages + Emploi', 'Électricité bâtiment', 10, 5),
            ('SONATEL', 'Télécoms', 'Awa Diallo', '+221 33 839 22 22', 'Embauche directe', 'Développement web, Maintenance', 5, 8),
            ('SONACOS', 'Agro-industrie', 'Moussa Diop', '+221 33 839 33 33', 'Stages + Apprentissage', 'Transformation agro', 15, 3),
            ('BTP Sénégal SA', 'BTP', 'Ousmane Ba', '+221 33 839 44 44', 'Emploi + Formation continue', 'Maçonnerie, Soudure', 20, 12),
            ('Groupe CBAO', 'Banque', 'Fatou Sow', '+221 33 839 55 55', 'Stages + Emploi', 'Commerce, Bureautique', 8, 4),
        ]
        for p in partenariats:
            cur.execute("""
                INSERT INTO partenariats (entreprise, secteur, contact_nom, telephone,
                                            type_partenariat, formations_concernees,
                                            nb_places_stage, nb_embauches, date_signature, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (*p, (datetime.now() - timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(partenariats)} partenariats créés")

    # ─── Placements ───
    cur.execute("SELECT COUNT(*) FROM placements")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, apprenant_id FROM inscriptions LIMIT 40")
        inscriptions = cur.fetchall()
        n = 0
        for ins in inscriptions:
            if random.random() < 0.5:
                cur.execute("""
                    INSERT INTO placements (apprenant_id, inscription_id, type, entreprise,
                                             poste, salaire_mensuel, date_debut, statut, created_at)
                    VALUES (?,?,?,?,?,?,?, 'actif', ?)
                """, (ins['apprenant_id'], ins['id'],
                      random.choice(['emploi', 'stage', 'apprentissage']),
                      random.choice(['SENELEC', 'SONATEL', 'BTP Sénégal', 'SONACOS', 'CBAO', 'Autre entreprise']),
                      random.choice(['Technicien', 'Ouvrier qualifié', 'Assistant', 'Commercial', 'Apprenti']),
                      random.randint(80000, 250000),
                      (datetime.now() - timedelta(days=random.randint(15, 120))).strftime('%Y-%m-%d'),
                      datetime.now().isoformat()))
                n += 1
        print(f"[SEED] ✅ {n} placements enregistrés")

    conn.commit()
    conn.close()
    print("[SEED] ✅ Données démo Formation Pro générées")


if __name__ == '__main__':
    init_db()
