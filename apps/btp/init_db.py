"""
🏗️ BTP & Chantiers — Initialisation base de données
Chantiers · Ressources · Matériaux · Sécurité · Budgétaire · Situations
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = '/app/data/btp.db'


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
            role TEXT DEFAULT 'chef_chantier',
            nom_complet TEXT,
            email TEXT,
            telephone TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Clients (maîtres d'ouvrage) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            type TEXT,
            contact TEXT,
            telephone TEXT,
            email TEXT,
            adresse TEXT,
            ville TEXT,
            created_at TEXT
        )
    """)

    # ─── Chantiers ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chantiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            client_id INTEGER,
            type TEXT,
            adresse TEXT,
            ville TEXT,
            latitude REAL,
            longitude REAL,
            date_debut TEXT,
            date_fin_prevue TEXT,
            date_fin_reelle TEXT,
            budget_initial REAL DEFAULT 0,
            budget_revise REAL DEFAULT 0,
            statut TEXT DEFAULT 'en_preparation',
            avancement_pct REAL DEFAULT 0,
            chef_chantier_id INTEGER,
            description TEXT,
            created_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(chef_chantier_id) REFERENCES users(id)
        )
    """)

    # ─── Phases / Tâches Gantt ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS taches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chantier_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            phase TEXT,
            date_debut TEXT,
            date_fin TEXT,
            duree_jours INTEGER DEFAULT 0,
            avancement_pct REAL DEFAULT 0,
            responsable TEXT,
            statut TEXT DEFAULT 'a_faire',
            ordre INTEGER DEFAULT 0,
            dependance_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(chantier_id) REFERENCES chantiers(id),
            FOREIGN KEY(dependance_id) REFERENCES taches(id)
        )
    """)

    # ─── Ressources (personnel + engins) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ressources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            type TEXT,
            categorie TEXT,
            cout_journalier REAL DEFAULT 0,
            cout_horaire REAL DEFAULT 0,
            unite TEXT DEFAULT 'jour',
            statut TEXT DEFAULT 'disponible',
            created_at TEXT
        )
    """)

    # ─── Affectations ressources aux chantiers ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS affectations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chantier_id INTEGER NOT NULL,
            ressource_id INTEGER NOT NULL,
            date_debut TEXT,
            date_fin TEXT,
            cout_total REAL DEFAULT 0,
            statut TEXT DEFAULT 'active',
            created_at TEXT,
            FOREIGN KEY(chantier_id) REFERENCES chantiers(id),
            FOREIGN KEY(ressource_id) REFERENCES ressources(id)
        )
    """)

    # ─── Pointage journalier ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pointages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chantier_id INTEGER NOT NULL,
            ressource_id INTEGER NOT NULL,
            date_pointage TEXT,
            heures REAL DEFAULT 8,
            cout_jour REAL DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(chantier_id) REFERENCES chantiers(id),
            FOREIGN KEY(ressource_id) REFERENCES ressources(id)
        )
    """)

    # ─── Fournisseurs ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fournisseurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            categorie TEXT,
            contact TEXT,
            telephone TEXT,
            email TEXT,
            adresse TEXT,
            created_at TEXT
        )
    """)

    # ─── Matériaux (catalogue) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS materiaux (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            categorie TEXT,
            unite TEXT DEFAULT 'unité',
            prix_unitaire REAL DEFAULT 0,
            fournisseur_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(fournisseur_id) REFERENCES fournisseurs(id)
        )
    """)

    # ─── Bons de commande ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bons_commande (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            chantier_id INTEGER,
            fournisseur_id INTEGER,
            date_commande TEXT,
            date_livraison_prevue TEXT,
            date_livraison_reelle TEXT,
            montant_ht REAL DEFAULT 0,
            tva REAL DEFAULT 0,
            montant_ttc REAL DEFAULT 0,
            statut TEXT DEFAULT 'brouillon',
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(chantier_id) REFERENCES chantiers(id),
            FOREIGN KEY(fournisseur_id) REFERENCES fournisseurs(id)
        )
    """)

    # ─── Lignes de commande ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bc_lignes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bc_id INTEGER NOT NULL,
            materiau_id INTEGER,
            designation TEXT,
            quantite REAL DEFAULT 0,
            prix_unitaire REAL DEFAULT 0,
            montant REAL DEFAULT 0,
            FOREIGN KEY(bc_id) REFERENCES bons_commande(id),
            FOREIGN KEY(materiau_id) REFERENCES materiaux(id)
        )
    """)

    # ─── Livraisons ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS livraisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            bc_id INTEGER,
            chantier_id INTEGER,
            fournisseur_id INTEGER,
            date_livraison TEXT,
            numero_bon TEXT,
            statut TEXT DEFAULT 'recu',
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(bc_id) REFERENCES bons_commande(id),
            FOREIGN KEY(chantier_id) REFERENCES chantiers(id)
        )
    """)

    # ─── Sécurité / EPI ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS epi_dotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chantier_id INTEGER,
            beneficiaire TEXT,
            type_epi TEXT,
            quantite INTEGER DEFAULT 1,
            date_remise TEXT,
            created_at TEXT,
            FOREIGN KEY(chantier_id) REFERENCES chantiers(id)
        )
    """)

    # ─── Incidents sécurité ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chantier_id INTEGER,
            date_incident TEXT,
            gravite TEXT,
            description TEXT,
            personne_impliquee TEXT,
            action_corrective TEXT,
            statut TEXT DEFAULT 'ouvert',
            created_at TEXT,
            FOREIGN KEY(chantier_id) REFERENCES chantiers(id)
        )
    """)

    # ─── Formations sécurité ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS formations_securite (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chantier_id INTEGER,
            theme TEXT,
            formateur TEXT,
            date_formation TEXT,
            nb_participants INTEGER DEFAULT 0,
            duree_heures REAL DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(chantier_id) REFERENCES chantiers(id)
        )
    """)

    # ─── Budget / Engagements / Paiements ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS budget_lignes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chantier_id INTEGER NOT NULL,
            categorie TEXT,
            libelle TEXT,
            montant_prevu REAL DEFAULT 0,
            montant_engage REAL DEFAULT 0,
            montant_paye REAL DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(chantier_id) REFERENCES chantiers(id)
        )
    """)

    # ─── Photos chantier ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chantier_id INTEGER,
            type TEXT,
            titre TEXT,
            chemin TEXT,
            description TEXT,
            date_photo TEXT,
            created_at TEXT,
            FOREIGN KEY(chantier_id) REFERENCES chantiers(id)
        )
    """)

    # ─── Situations de travaux ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS situations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            chantier_id INTEGER,
            numero_situation INTEGER,
            date_situation TEXT,
            avancement_pct REAL DEFAULT 0,
            montant_travaux REAL DEFAULT 0,
            montant_precedent REAL DEFAULT 0,
            montant_cette_situation REAL DEFAULT 0,
            retenue_garantie REAL DEFAULT 0,
            montant_net REAL DEFAULT 0,
            statut TEXT DEFAULT 'brouillon',
            created_at TEXT,
            FOREIGN KEY(chantier_id) REFERENCES chantiers(id)
        )
    """)

    # ─── Factures ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS factures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            chantier_id INTEGER,
            client_id INTEGER,
            situation_id INTEGER,
            date_facture TEXT,
            date_echeance TEXT,
            montant_ht REAL DEFAULT 0,
            tva REAL DEFAULT 0,
            montant_ttc REAL DEFAULT 0,
            montant_paye REAL DEFAULT 0,
            statut TEXT DEFAULT 'emise',
            created_at TEXT,
            FOREIGN KEY(chantier_id) REFERENCES chantiers(id),
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(situation_id) REFERENCES situations(id)
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
        "CREATE INDEX IF NOT EXISTS idx_chantiers_statut ON chantiers(statut)",
        "CREATE INDEX IF NOT EXISTS idx_taches_chantier ON taches(chantier_id)",
        "CREATE INDEX IF NOT EXISTS idx_bc_chantier ON bons_commande(chantier_id)",
        "CREATE INDEX IF NOT EXISTS idx_situations_chantier ON situations(chantier_id)",
        "CREATE INDEX IF NOT EXISTS idx_factures_chantier ON factures(chantier_id)",
    ]:
        try:
            cur.execute(idx)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # TRIGGERS
    # ═══════════════════════════════════════════════════════

    # Trigger 1 : génération code chantier
    cur.execute("DROP TRIGGER IF EXISTS trg_chantier_code")
    cur.execute("""
        CREATE TRIGGER trg_chantier_code
        AFTER INSERT ON chantiers
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE chantiers SET
                code = 'CH-' || strftime('%Y%m', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 2 : numéro BC auto
    cur.execute("DROP TRIGGER IF EXISTS trg_bc_numero")
    cur.execute("""
        CREATE TRIGGER trg_bc_numero
        AFTER INSERT ON bons_commande
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE bons_commande SET
                numero = 'BC-' || strftime('%Y%m', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 3 : numéro situation auto
    cur.execute("DROP TRIGGER IF EXISTS trg_situation_numero")
    cur.execute("""
        CREATE TRIGGER trg_situation_numero
        AFTER INSERT ON situations
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE situations SET
                numero = 'SIT-' || strftime('%Y%m', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 4 : mise à jour budget engagé après BC (sans LIMIT pour compatibilité SQLite)
    cur.execute("DROP TRIGGER IF EXISTS trg_bc_maj_engage")
    cur.execute("""
        CREATE TRIGGER trg_bc_maj_engage
        AFTER INSERT ON bons_commande
        FOR EACH ROW
        WHEN NEW.montant_ttc > 0
        BEGIN
            UPDATE budget_lignes
            SET montant_engage = montant_engage + NEW.montant_ttc
            WHERE chantier_id = NEW.chantier_id
              AND id = (
                  SELECT MIN(id) FROM budget_lignes
                  WHERE chantier_id = NEW.chantier_id
                    AND categorie = 'materiaux'
              );
        END
    """)

    # Trigger 5 : calcul montant_net situation
    cur.execute("DROP TRIGGER IF EXISTS trg_situation_net")
    cur.execute("""
        CREATE TRIGGER trg_situation_net
        AFTER UPDATE OF montant_cette_situation ON situations
        FOR EACH ROW
        BEGIN
            UPDATE situations SET
                montant_net = NEW.montant_cette_situation - COALESCE(NEW.retenue_garantie, 0)
            WHERE id = NEW.id;
        END
    """)

    conn.commit()
    conn.close()
    print("[INIT] ✅ Base BTP & Chantiers prête")


def seed_demo():
    """Génère des données démo si base vide."""
    conn = get_conn()
    cur = conn.cursor()

    from werkzeug.security import generate_password_hash

    # ─── Users ───
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        users = [
            ('admin', 'admin123', 'admin', 'Administrateur', 'admin@btp.sn', '+221 77 000 00 00'),
            ('directeur', 'dir123', 'directeur', 'Mamadou Diop', 'dir@btp.sn', '+221 77 111 11 11'),
            ('chef1', 'chef123', 'chef_chantier', 'Ibrahima Sall', 'chef1@btp.sn', '+221 77 222 22 22'),
            ('chef2', 'chef123', 'chef_chantier', 'Fatou Ndiaye', 'chef2@btp.sn', '+221 77 333 33 33'),
            ('chef3', 'chef123', 'chef_chantier', 'Ousmane Ba', 'chef3@btp.sn', '+221 77 444 44 44'),
        ]
        for u in users:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, nom_complet, email, telephone, actif, created_at)
                VALUES (?,?,?,?,?,?,1,?)
            """, (u[0], generate_password_hash(u[1]), u[2], u[3], u[4], u[5], datetime.now().isoformat()))
        print("[SEED] ✅ 5 utilisateurs créés")

    cur.execute("SELECT id FROM users WHERE role='chef_chantier'")
    chef_ids = [r[0] for r in cur.fetchall()]

    # ─── Clients ───
    cur.execute("SELECT COUNT(*) FROM clients")
    if cur.fetchone()[0] == 0:
        clients = [
            ('CLI-BTP-001', 'Ministère des Infrastructures', 'public', 'Amadou Diallo', '+221 33 839 00 00', 'contact@infra.gouv.sn', 'Dakar'),
            ('CLI-BTP-002', 'SONATEL Immobilier', 'prive', 'Fatou Sow', '+221 33 839 11 11', 'immo@sonatel.sn', 'Dakar'),
            ('CLI-BTP-003', 'Cité Keur Gorgui', 'prive', 'Moussa Ndiaye', '+221 33 839 22 22', 'contact@kg.sn', 'Dakar'),
            ('CLI-BTP-004', 'Port Autonome Dakar', 'public', 'Ibrahima Fall', '+221 33 849 33 33', 'travaux@portdakar.sn', 'Dakar'),
            ('CLI-BTP-005', 'Groupe CBAO', 'prive', 'Aïssatou Ba', '+221 33 839 44 44', 'immo@cbao.sn', 'Dakar'),
        ]
        for c in clients:
            cur.execute("""
                INSERT INTO clients (code, nom, type, contact, telephone, email, ville, created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (*c, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(clients)} clients créés")

    cur.execute("SELECT id FROM clients LIMIT 5")
    cli_ids = [r[0] for r in cur.fetchall()]

    # ─── Chantiers ───
    cur.execute("SELECT COUNT(*) FROM chantiers")
    if cur.fetchone()[0] == 0:
        chantiers = [
            ('Immeuble R+5 Dakar Plateau', 'batiment', 'Dakar', 800_000_000, 'en_cours'),
            ('Route nationale Thiès-Kayar', 'route', 'Thiès', 1_500_000_000, 'en_cours'),
            ('Cité 50 logements Diamniadio', 'logement', 'Diamniadio', 600_000_000, 'en_cours'),
            ('Extension Port Dakar', 'infrastructure', 'Dakar', 2_200_000_000, 'en_cours'),
            ('Réhabilitation École Kaolack', 'batiment', 'Kaolack', 150_000_000, 'termine'),
            ('Pont Faidherbe rénovation', 'ouvrage_art', 'Saint-Louis', 900_000_000, 'en_preparation'),
            ('Zone industrielle Diamniadio', 'infrastructure', 'Diamniadio', 1_800_000_000, 'en_cours'),
            ('Hôpital régional Thiès', 'batiment', 'Thiès', 750_000_000, 'en_cours'),
        ]
        for c in chantiers:
            date_debut = datetime.now() - timedelta(days=random.randint(30, 300))
            date_fin = date_debut + timedelta(days=random.randint(180, 720))
            budget = c[3]
            budget_revise = budget * random.uniform(0.95, 1.15)
            avancement = random.randint(10, 95) if c[4] == 'en_cours' else 100 if c[4] == 'termine' else 0

            cur.execute("""
                INSERT INTO chantiers
                (code, nom, client_id, type, ville, latitude, longitude,
                 date_debut, date_fin_prevue, budget_initial, budget_revise,
                 statut, avancement_pct, chef_chantier_id, description, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None, c[0], random.choice(cli_ids), c[1], c[2],
                  random.uniform(14.5, 16.0), random.uniform(-17.5, -16.0),
                  date_debut.strftime('%Y-%m-%d'),
                  date_fin.strftime('%Y-%m-%d'),
                  budget, budget_revise,
                  c[4], avancement,
                  random.choice(chef_ids) if chef_ids else None,
                  f"Projet {c[0]} - {c[1]}",
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(chantiers)} chantiers créés")

    cur.execute("SELECT id, budget_initial FROM chantiers")
    chantier_rows = cur.fetchall()

    # ─── Tâches (Gantt) ───
    cur.execute("SELECT COUNT(*) FROM taches")
    if cur.fetchone()[0] == 0:
        phases = ['Installation chantier', 'Terrassement', 'Fondations', 'Structure', 'Second œuvre', 'Finitions']
        n_taches = 0
        for ch in chantier_rows:
            for i, phase in enumerate(phases):
                duree = random.randint(15, 60)
                debut = datetime.now() - timedelta(days=random.randint(0, 200))
                fin = debut + timedelta(days=duree)
                avancement = random.randint(0, 100)
                statut = 'termine' if avancement == 100 else 'en_cours' if avancement > 0 else 'a_faire'
                cur.execute("""
                    INSERT INTO taches
                    (chantier_id, nom, phase, date_debut, date_fin, duree_jours,
                     avancement_pct, responsable, statut, ordre, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (ch['id'], phase, phase,
                      debut.strftime('%Y-%m-%d'),
                      fin.strftime('%Y-%m-%d'), duree,
                      avancement,
                      random.choice(['Chef A', 'Chef B', 'Chef C']),
                      statut, i+1, datetime.now().isoformat()))
                n_taches += 1
        print(f"[SEED] ✅ {n_taches} tâches créées")

    # ─── Ressources ───
    cur.execute("SELECT COUNT(*) FROM ressources")
    if cur.fetchone()[0] == 0:
        ressources = [
            # Personnel
            ('PERS-001', 'Maçon qualifié', 'personnel', 'main_oeuvre', 15000, 0),
            ('PERS-002', 'Ferrailleur', 'personnel', 'main_oeuvre', 18000, 0),
            ('PERS-003', 'Coffreur', 'personnel', 'main_oeuvre', 16000, 0),
            ('PERS-004', 'Électricien', 'personnel', 'main_oeuvre', 22000, 0),
            ('PERS-005', 'Plombier', 'personnel', 'main_oeuvre', 20000, 0),
            ('PERS-006', 'Chef d\'équipe', 'personnel', 'encadrement', 35000, 0),
            # Engins
            ('ENG-001', 'Pelle hydraulique 20T', 'engin', 'terrassement', 250000, 45000),
            ('ENG-002', 'Bulldozer D6', 'engin', 'terrassement', 300000, 55000),
            ('ENG-003', 'Compacteur vibrant', 'engin', 'voirie', 180000, 35000),
            ('ENG-004', 'Grue à tour 40m', 'engin', 'levage', 400000, 75000),
            ('ENG-005', 'Bétonnière 350L', 'engin', 'beton', 80000, 15000),
            ('ENG-006', 'Camion benne 20T', 'engin', 'transport', 150000, 28000),
            ('ENG-007', 'Nacelle élévatrice', 'engin', 'levage', 120000, 22000),
            ('ENG-008', 'Groupe électrogène 100kVA', 'engin', 'energie', 90000, 17000),
        ]
        for r in ressources:
            cur.execute("""
                INSERT INTO ressources (code, nom, type, categorie, cout_journalier, cout_horaire, unite, statut, created_at)
                VALUES (?,?,?,?,?,?,?, 'disponible', ?)
            """, (r[0], r[1], r[2], r[3], r[4], r[5], 'jour' if r[2] == 'personnel' else 'jour', datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(ressources)} ressources créées")

    # ─── Fournisseurs ───
    cur.execute("SELECT COUNT(*) FROM fournisseurs")
    if cur.fetchone()[0] == 0:
        fournisseurs = [
            ('SOCOCIM Industries', 'Ciment', 'Moussa Diop', '+221 33 957 00 00', 'contact@sococim.sn', 'Rufisque'),
            ('SENFER', 'Ferraille', 'Amadou Sall', '+221 33 839 11 11', 'vente@senfer.sn', 'Dakar'),
            ('Ciments du Sahel', 'Ciment', 'Fatou Ba', '+221 33 957 22 22', 'info@cimentsdusahel.sn', 'Thiès'),
            ('SOSACO', 'Agrégats', 'Ibrahima Fall', '+221 33 839 33 33', 'contact@sosaco.sn', 'Dakar'),
            ('WIRTGEN Sénégal', 'Engins BTP', 'Pape Sow', '+221 33 869 44 44', 'info@wirtgen.sn', 'Dakar'),
        ]
        for f in fournisseurs:
            cur.execute("""
                INSERT INTO fournisseurs (nom, categorie, contact, telephone, email, adresse, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (*f, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(fournisseurs)} fournisseurs créés")

    # ─── Matériaux ───
    cur.execute("SELECT COUNT(*) FROM materiaux")
    if cur.fetchone()[0] == 0:
        materiaux = [
            ('MAT-CIM-50', 'Ciment CPJ 42.5 - Sac 50kg', 'Ciment', 'sac', 5500),
            ('MAT-BET-350', 'Béton prêt à l\'emploi 350kg/m³', 'Béton', 'm3', 85000),
            ('MAT-FER-12', 'Fer à béton Ø12mm', 'Ferraille', 'barre', 4500),
            ('MAT-FER-16', 'Fer à béton Ø16mm', 'Ferraille', 'barre', 7000),
            ('MAT-GRAV-15', 'Gravier 15/25', 'Agrégats', 'm3', 22000),
            ('MAT-SAB-01', 'Sable de rivière', 'Agrégats', 'm3', 18000),
            ('MAT-BRI-20', 'Brique creuse 20x20x40', 'Maçonnerie', 'unité', 350),
            ('MAT-TUI-01', 'Tôle bac acier', 'Couverture', 'm2', 8500),
        ]
        cur.execute("SELECT id FROM fournisseurs LIMIT 5")
        four_ids = [r[0] for r in cur.fetchall()]
        for m in materiaux:
            cur.execute("""
                INSERT INTO materiaux (code, nom, categorie, unite, prix_unitaire, fournisseur_id, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (*m, random.choice(four_ids) if four_ids else None, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(materiaux)} matériaux créés")

    # ─── Bons de commande ───
    cur.execute("SELECT COUNT(*) FROM bons_commande")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM fournisseurs LIMIT 5")
        four_ids = [r[0] for r in cur.fetchall()]
        n_bc = 0
        for ch in chantier_rows:
            for _ in range(random.randint(1, 3)):
                montant = random.randint(500000, 25000000)
                tva = montant * 0.18
                cur.execute("""
                    INSERT INTO bons_commande
                    (numero, chantier_id, fournisseur_id, date_commande, date_livraison_prevue,
                     montant_ht, tva, montant_ttc, statut, notes, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (None, ch['id'], random.choice(four_ids),
                      (datetime.now() - timedelta(days=random.randint(0, 90))).strftime('%Y-%m-%d'),
                      (datetime.now() + timedelta(days=random.randint(-15, 30))).strftime('%Y-%m-%d'),
                      montant, tva, montant + tva,
                      random.choice(['brouillon', 'envoye', 'livre', 'livre', 'livre']),
                      'Commande matériaux chantier',
                      datetime.now().isoformat()))
                n_bc += 1
        print(f"[SEED] ✅ {n_bc} bons de commande créés")

    # ─── Budget lignes ───
    cur.execute("SELECT COUNT(*) FROM budget_lignes")
    if cur.fetchone()[0] == 0:
        categories = [
            ('materiaux', 'Matériaux de construction', 0.40),
            ('main_oeuvre', 'Main d\'œuvre', 0.25),
            ('engins', 'Location engins', 0.15),
            ('sous_traitance', 'Sous-traitance', 0.10),
            ('divers', 'Divers & imprévus', 0.10),
        ]
        n_lignes = 0
        for ch in chantier_rows:
            budget = ch['budget_initial']
            for cat, lib, pct in categories:
                prevu = budget * pct
                engage = prevu * random.uniform(0.2, 1.1)
                paye = engage * random.uniform(0.3, 1.0)
                cur.execute("""
                    INSERT INTO budget_lignes
                    (chantier_id, categorie, libelle, montant_prevu, montant_engage, montant_paye, created_at)
                    VALUES (?,?,?,?,?,?,?)
                """, (ch['id'], cat, lib, prevu, engage, paye, datetime.now().isoformat()))
                n_lignes += 1
        print(f"[SEED] ✅ {n_lignes} lignes budgétaires créées")

    # ─── Situations ───
    cur.execute("SELECT COUNT(*) FROM situations")
    if cur.fetchone()[0] == 0:
        n_sit = 0
        for ch in chantier_rows:
            if random.random() < 0.7:
                nb_sit = random.randint(1, 3)
                montant_prec = 0
                for i in range(nb_sit):
                    avancement = random.randint(10, 35)
                    montant_travaux = ch['budget_initial'] * avancement / 100
                    montant_sit = montant_travaux - montant_prec
                    retenue = montant_sit * 0.05
                    cur.execute("""
                        INSERT INTO situations
                        (numero, chantier_id, numero_situation, date_situation, avancement_pct,
                         montant_travaux, montant_precedent, montant_cette_situation,
                         retenue_garantie, montant_net, statut, created_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (None, ch['id'], i+1,
                          (datetime.now() - timedelta(days=random.randint(0, 90))).strftime('%Y-%m-%d'),
                          avancement, montant_travaux, montant_prec, montant_sit,
                          retenue, montant_sit - retenue,
                          random.choice(['brouillon', 'validee', 'facturee']),
                          datetime.now().isoformat()))
                    montant_prec = montant_travaux
                    n_sit += 1
        print(f"[SEED] ✅ {n_sit} situations de travaux créées")

    # ─── Incidents sécurité ───
    cur.execute("SELECT COUNT(*) FROM incidents")
    if cur.fetchone()[0] == 0:
        n_inc = 0
        for ch in chantier_rows:
            if random.random() < 0.5:
                for _ in range(random.randint(1, 2)):
                    cur.execute("""
                        INSERT INTO incidents
                        (chantier_id, date_incident, gravite, description, personne_impliquee,
                         action_corrective, statut, created_at)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (ch['id'],
                          (datetime.now() - timedelta(days=random.randint(0, 60))).strftime('%Y-%m-%d'),
                          random.choice(['mineure', 'majeure', 'critique']),
                          random.choice(['Chute sans gravité', 'Coupure main', 'Glissade',
                                          'Chute d\'échafaudage', 'Projection oculaire']),
                          random.choice(['Ouvrier A', 'Ouvrier B', 'Ouvrier C']),
                          'Rappel consignes + EPI renforcés',
                          random.choice(['ouvert', 'clos']),
                          datetime.now().isoformat()))
                    n_inc += 1
        print(f"[SEED] ✅ {n_inc} incidents sécurité créés")

    # ─── EPI dotations ───
    cur.execute("SELECT COUNT(*) FROM epi_dotations")
    if cur.fetchone()[0] == 0:
        for ch in chantier_rows:
            for _ in range(random.randint(3, 8)):
                cur.execute("""
                    INSERT INTO epi_dotations (chantier_id, beneficiaire, type_epi, quantite, date_remise, created_at)
                    VALUES (?,?,?,?,?,?)
                """, (ch['id'],
                      random.choice(['Ouvrier A', 'Ouvrier B', 'Ouvrier C', 'Chef équipe']),
                      random.choice(['Casque', 'Gilet réfléchissant', 'Chaussures sécurité',
                                      'Gants', 'Lunettes', 'Harnais']),
                      random.randint(1, 3),
                      (datetime.now() - timedelta(days=random.randint(0, 120))).strftime('%Y-%m-%d'),
                      datetime.now().isoformat()))
        print("[SEED] ✅ Dotations EPI créées")

    # ─── Formations sécurité ───
    cur.execute("SELECT COUNT(*) FROM formations_securite")
    if cur.fetchone()[0] == 0:
        for ch in chantier_rows:
            if random.random() < 0.4:
                cur.execute("""
                    INSERT INTO formations_securite
                    (chantier_id, theme, formateur, date_formation, nb_participants, duree_heures, created_at)
                    VALUES (?,?,?,?,?,?,?)
                """, (ch['id'],
                      random.choice(['Port des EPI', 'Travail en hauteur', 'Premiers secours',
                                      'Manutention manuelle', 'Conduite engins']),
                      random.choice(['Formateur certifié A', 'Formateur certifié B']),
                      (datetime.now() - timedelta(days=random.randint(0, 180))).strftime('%Y-%m-%d'),
                      random.randint(5, 30),
                      random.choice([2, 4, 8, 16]),
                      datetime.now().isoformat()))
        print("[SEED] ✅ Formations sécurité créées")

    conn.commit()
    conn.close()
    print("[SEED] ✅ Données démo BTP & Chantiers générées")


if __name__ == '__main__':
    init_db()
