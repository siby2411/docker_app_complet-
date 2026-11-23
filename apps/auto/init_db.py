

"""
🚗 Omega Auto — Base de données Vente & Location Automobile CEDEAO
Véhicules · Clients · Ventes · Locations · Papiers · WhatsApp · Finances
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = '/app/data/auto.db'


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
            role TEXT DEFAULT 'commercial',
            nom_complet TEXT,
            email TEXT,
            telephone TEXT,
            agence TEXT,
            whatsapp TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Agences / Concessions ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            type TEXT,
            adresse TEXT,
            ville TEXT,
            region TEXT,
            pays TEXT DEFAULT 'Sénégal',
            telephone TEXT,
            whatsapp TEXT,
            email TEXT,
            responsable TEXT,
            latitude REAL,
            longitude REAL,
            horaires TEXT,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Marques ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS marques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            slug TEXT UNIQUE,
            pays_origine TEXT,
            logo_url TEXT,
            ordre INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    # ─── Modèles ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS modeles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marque_id INTEGER,
            nom TEXT NOT NULL,
            type TEXT,
            annee_debut INTEGER,
            annee_fin INTEGER,
            carburant TEXT,
            transmission TEXT,
            created_at TEXT,
            FOREIGN KEY(marque_id) REFERENCES marques(id)
        )
    """)

    # ─── Véhicules ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            agence_id INTEGER,
            marque_id INTEGER,
            modele_id INTEGER,
            immatriculation TEXT UNIQUE,
            vin_chassis TEXT,
            type TEXT,
            etat TEXT,
            annee INTEGER,
            kilometrage REAL DEFAULT 0,
            carburant TEXT,
            transmission TEXT,
            couleur TEXT,
            nb_portes INTEGER DEFAULT 4,
            nb_places INTEGER DEFAULT 5,
            puissance_ch INTEGER DEFAULT 0,
            cylindree_cm3 INTEGER DEFAULT 0,
            prix_achat REAL DEFAULT 0,
            prix_vente REAL DEFAULT 0,
            prix_location_jour REAL DEFAULT 0,
            prix_location_semaine REAL DEFAULT 0,
            prix_location_mois REAL DEFAULT 0,
            marge_estimee REAL DEFAULT 0,
            disponible_vente INTEGER DEFAULT 1,
            disponible_location INTEGER DEFAULT 1,
            photo_principale TEXT,
            description TEXT,
            equipements TEXT,
            statut TEXT DEFAULT 'disponible',
            qr_code TEXT,
            date_acquisition TEXT,
            created_at TEXT,
            FOREIGN KEY(agence_id) REFERENCES agences(id),
            FOREIGN KEY(marque_id) REFERENCES marques(id),
            FOREIGN KEY(modele_id) REFERENCES modeles(id)
        )
    """)

    # ─── Photos véhicules (galerie) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicule_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicule_id INTEGER NOT NULL,
            chemin TEXT,
            legende TEXT,
            categorie TEXT,
            ordre INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id)
        )
    """)

    # ─── Vidéos véhicules ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicule_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicule_id INTEGER NOT NULL,
            chemin TEXT,
            titre TEXT,
            duree_sec INTEGER DEFAULT 0,
            categorie TEXT,
            created_at TEXT,
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id)
        )
    """)

    # ─── Papiers véhicules (carte grise, assurance) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS papiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicule_id INTEGER NOT NULL,
            type TEXT,
            numero TEXT,
            date_emission TEXT,
            date_expiration TEXT,
            fichier_path TEXT,
            compagnie TEXT,
            montant REAL DEFAULT 0,
            statut TEXT DEFAULT 'valide',
            created_at TEXT,
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id)
        )
    """)

    # ─── Historique entretien ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entretiens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicule_id INTEGER NOT NULL,
            type TEXT,
            description TEXT,
            kilometrage REAL DEFAULT 0,
            cout REAL DEFAULT 0,
            garage TEXT,
            date_entretien TEXT,
            prochain_km REAL DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id)
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
            telephone TEXT UNIQUE,
            whatsapp TEXT,
            email TEXT,
            adresse TEXT,
            ville TEXT,
            pays TEXT DEFAULT 'Sénégal',
            piece_identite TEXT,
            permis_conduire TEXT,
            score INTEGER DEFAULT 0,
            nb_achats INTEGER DEFAULT 0,
            nb_locations INTEGER DEFAULT 0,
            total_depense REAL DEFAULT 0,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Ventes ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ventes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            vehicule_id INTEGER,
            client_id INTEGER,
            vendeur_id INTEGER,
            agence_id INTEGER,
            date_vente TEXT,
            prix_vente REAL DEFAULT 0,
            prix_achat REAL DEFAULT 0,
            marge REAL DEFAULT 0,
            remise REAL DEFAULT 0,
            montant_ttc REAL DEFAULT 0,
            acompte REAL DEFAULT 0,
            reste_a_payer REAL DEFAULT 0,
            mode_paiement TEXT,
            type_vente TEXT DEFAULT 'comptant',
            duree_credit_mois INTEGER DEFAULT 0,
            statut TEXT DEFAULT 'devis',
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id),
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(vendeur_id) REFERENCES users(id),
            FOREIGN KEY(agence_id) REFERENCES agences(id)
        )
    """)

    # ─── Locations ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            vehicule_id INTEGER,
            client_id INTEGER,
            agence_id INTEGER,
            date_debut TEXT,
            date_fin_prevue TEXT,
            date_retour_reelle TEXT,
            duree_jours INTEGER DEFAULT 0,
            km_depart REAL DEFAULT 0,
            km_retour REAL DEFAULT 0,
            km_parcourus REAL DEFAULT 0,
            tarif_journalier REAL DEFAULT 0,
            montant_ht REAL DEFAULT 0,
            caution REAL DEFAULT 0,
            frais_supplementaires REAL DEFAULT 0,
            montant_total REAL DEFAULT 0,
            statut TEXT DEFAULT 'reservee',
            carburant_depart TEXT,
            carburant_retour TEXT,
            etat_depart TEXT,
            etat_retour TEXT,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id),
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(agence_id) REFERENCES agences(id)
        )
    """)

    # ─── Paiements ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            reference_id INTEGER,
            client_id INTEGER,
            montant REAL DEFAULT 0,
            mode TEXT,
            operateur TEXT,
            telephone TEXT,
            reference_transaction TEXT,
            statut TEXT DEFAULT 'valide',
            date_paiement TEXT,
            created_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    """)

    # ─── WhatsApp messages log ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destinataire TEXT,
            type TEXT,
            vehicule_id INTEGER,
            client_id INTEGER,
            message TEXT,
            statut TEXT DEFAULT 'envoye',
            mode TEXT DEFAULT 'simulation',
            date_envoi TEXT,
            created_at TEXT
        )
    """)

    # ─── Douane / Import ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS douane (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicule_id INTEGER,
            numero_declaration TEXT,
            bureau_douane TEXT,
            pays_origine TEXT,
            date_import TEXT,
            valeur_caf REAL DEFAULT 0,
            droits_taxes REAL DEFAULT 0,
            statut TEXT DEFAULT 'en_cours',
            date_dedouanement TEXT,
            created_at TEXT,
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id)
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
        "CREATE INDEX IF NOT EXISTS idx_vehicules_statut ON vehicules(statut)",
        "CREATE INDEX IF NOT EXISTS idx_vehicules_marque ON vehicules(marque_id)",
        "CREATE INDEX IF NOT EXISTS idx_ventes_client ON ventes(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_locations_client ON locations(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_locations_statut ON locations(statut)",
    ]:
        try:
            cur.execute(idx)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # TRIGGERS
    # ═══════════════════════════════════════════════════════

    # Trigger 1 : code véhicule auto + QR
    cur.execute("DROP TRIGGER IF EXISTS trg_vehicule_code")
    cur.execute("""
        CREATE TRIGGER trg_vehicule_code
        AFTER INSERT ON vehicules
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE vehicules SET
                code = 'VEH-' || strftime('%Y%m', 'now') || '-' || substr('0000' || NEW.id, -4),
                qr_code = 'AUTO|VEH|' || NEW.id
            WHERE id = NEW.id;
        END
    """)

    # Trigger 2 : code client auto
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

    # Trigger 3 : numéro vente auto
    cur.execute("DROP TRIGGER IF EXISTS trg_vente_numero")
    cur.execute("""
        CREATE TRIGGER trg_vente_numero
        AFTER INSERT ON ventes
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE ventes SET
                numero = 'VTE-' || strftime('%Y%m%d', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 4 : numéro location auto
    cur.execute("DROP TRIGGER IF EXISTS trg_location_numero")
    cur.execute("""
        CREATE TRIGGER trg_location_numero
        AFTER INSERT ON locations
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE locations SET
                numero = 'LOC-' || strftime('%Y%m%d', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 5 : MAJ client après vente livrée
    cur.execute("DROP TRIGGER IF EXISTS trg_vente_client")
    cur.execute("""
        CREATE TRIGGER trg_vente_client
        AFTER UPDATE OF statut ON ventes
        FOR EACH ROW
        WHEN NEW.statut = 'livree' AND OLD.statut != 'livree' AND NEW.client_id IS NOT NULL
        BEGIN
            UPDATE clients SET
                nb_achats = nb_achats + 1,
                total_depense = total_depense + NEW.montant_ttc
            WHERE id = NEW.client_id;
            UPDATE vehicules SET statut = 'vendu' WHERE id = NEW.vehicule_id;
        END
    """)

    # Trigger 6 : MAJ véhicule après location terminée
    cur.execute("DROP TRIGGER IF EXISTS trg_location_vehicule")
    cur.execute("""
        CREATE TRIGGER trg_location_vehicule
        AFTER UPDATE OF statut ON locations
        FOR EACH ROW
        WHEN NEW.statut = 'terminee' AND OLD.statut != 'terminee'
        BEGIN
            UPDATE vehicules SET statut = 'disponible',
                kilometrage = kilometrage + COALESCE(NEW.km_parcourus, 0)
            WHERE id = NEW.vehicule_id;
            UPDATE clients SET
                nb_locations = nb_locations + 1,
                total_depense = total_depense + NEW.montant_total
            WHERE id = NEW.client_id;
        END
    """)

    conn.commit()
    conn.close()
    print("[INIT] ✅ Base Omega Auto prête")


def seed_demo():
    """Génère des données démo si base vide."""
    conn = get_conn()
    cur = conn.cursor()

    from werkzeug.security import generate_password_hash

    # ─── Users ───
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        users = [
            ('admin', 'admin123', 'admin', 'Administrateur', 'admin@omega-auto.sn', '+221 77 000 00 00', 'OMEGA Auto', '+221 77 000 00 00'),
            ('directeur', 'dir123', 'directeur', 'Mamadou Diop', 'dir@omega-auto.sn', '+221 77 111 11 11', 'Direction', '+221 77 111 11 11'),
            ('vendeur1', 'vendeur123', 'commercial', 'Ibrahima Sall', 'ibrahima@omega-auto.sn', '+221 77 222 22 22', 'Dakar', '+221 77 222 22 22'),
            ('vendeur2', 'vendeur123', 'commercial', 'Awa Fall', 'awa@omega-auto.sn', '+221 77 333 33 33', 'Thiès', '+221 77 333 33 33'),
            ('vendeur3', 'vendeur123', 'commercial', 'Ousmane Ba', 'ousmane@omega-auto.sn', '+221 77 444 44 44', 'Saint-Louis', '+221 77 444 44 44'),
        ]
        for u in users:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, nom_complet, email, telephone, agence, whatsapp, actif, created_at)
                VALUES (?,?,?,?,?,?,?,?,1,?)
            """, (u[0], generate_password_hash(u[1]), u[2], u[3], u[4], u[5], u[6], u[7], datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(users)} utilisateurs créés")

    # ─── Agences ───
    cur.execute("SELECT COUNT(*) FROM agences")
    if cur.fetchone()[0] == 0:
        agences = [
            ('OMEGA Auto Dakar Plateau', 'concession', 'Rue Carnot', 'Dakar', 'Dakar', '+221 33 821 00 01'),
            ('OMEGA Auto Almadies', 'concession', 'Route des Almadies', 'Dakar', 'Dakar', '+221 33 820 00 02'),
            ('OMEGA Auto Thiès', 'agence', 'Avenue LSS', 'Thiès', 'Thiès', '+221 33 951 00 03'),
            ('OMEGA Auto Saint-Louis', 'agence', 'Île Saint-Louis', 'Saint-Louis', 'Saint-Louis', '+221 33 961 00 04'),
        ]
        for a in agences:
            cur.execute("""
                INSERT INTO agences (code, nom, type, adresse, ville, region, pays, telephone, whatsapp,
                                       horaires, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (None, a[0], a[1], a[2], a[3], a[4], 'Sénégal', a[5], a[5],
                  'Lun-Sam 8h-19h', datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(agences)} agences créées")

    cur.execute("SELECT id FROM agences")
    agence_ids = [r[0] for r in cur.fetchall()]

    # ─── Marques ───
    cur.execute("SELECT COUNT(*) FROM marques")
    if cur.fetchone()[0] == 0:
        marques = [
            ('Toyota', 'toyota', 'Japon'),
            ('Peugeot', 'peugeot', 'France'),
            ('Renault', 'renault', 'France'),
            ('Hyundai', 'hyundai', 'Corée'),
            ('Kia', 'kia', 'Corée'),
            ('Mercedes-Benz', 'mercedes', 'Allemagne'),
            ('BMW', 'bmw', 'Allemagne'),
            ('Nissan', 'nissan', 'Japon'),
            ('Volkswagen', 'volkswagen', 'Allemagne'),
            ('Ford', 'ford', 'USA'),
        ]
        for i, m in enumerate(marques):
            cur.execute("""
                INSERT INTO marques (nom, slug, pays_origine, ordre, created_at)
                VALUES (?,?,?,?,?)
            """, (m[0], m[1], m[2], i + 1, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(marques)} marques créées")

    cur.execute("SELECT id, nom FROM marques")
    marques = cur.fetchall()

    # ─── Modèles ───
    cur.execute("SELECT COUNT(*) FROM modeles")
    if cur.fetchone()[0] == 0:
        modeles_data = {
            'Toyota': [('Corolla', 'berline', 2015), ('RAV4', 'SUV', 2016), ('Hilux', 'pickup', 2015), ('Yaris', 'citadine', 2016)],
            'Peugeot': [('208', 'citadine', 2017), ('308', 'berline', 2016), ('3008', 'SUV', 2017), ('Partner', 'utilitaire', 2015)],
            'Renault': [('Clio', 'citadine', 2016), ('Duster', 'SUV', 2018), ('Mégane', 'berline', 2016)],
            'Hyundai': [('Tucson', 'SUV', 2017), ('i10', 'citadine', 2018), ('Accent', 'berline', 2018)],
            'Kia': [('Sportage', 'SUV', 2017), ('Rio', 'citadine', 2017), ('Picanto', 'citadine', 2018)],
            'Mercedes-Benz': [('Classe C', 'berline', 2016), ('GLC', 'SUV', 2018), ('Classe A', 'citadine', 2018)],
            'BMW': [('Série 3', 'berline', 2017), ('X3', 'SUV', 2018)],
            'Nissan': [('Qashqai', 'SUV', 2017), ('Note', 'citadine', 2016)],
            'Volkswagen': [('Golf', 'citadine', 2017), ('Tiguan', 'SUV', 2017)],
            'Ford': [('Focus', 'berline', 2016), ('Ranger', 'pickup', 2017)],
        }
        n = 0
        for m in marques:
            for mod in modeles_data.get(m['nom'], []):
                cur.execute("""
                    INSERT INTO modeles (marque_id, nom, type, annee_debut, carburant, transmission, created_at)
                    VALUES (?,?,?,?,?,?,?)
                """, (m['id'], mod[0], mod[1], mod[2],
                      random.choice(['essence', 'diesel']),
                      random.choice(['manuelle', 'automatique']),
                      datetime.now().isoformat()))
                n += 1
        print(f"[SEED] ✅ {n} modèles créés")

    cur.execute("SELECT id, marque_id, nom, type FROM modeles")
    modeles = cur.fetchall()

    # ─── Véhicules ───
    cur.execute("SELECT COUNT(*) FROM vehicules")
    if cur.fetchone()[0] == 0:
        couleurs = ['Blanc', 'Noir', 'Gris', 'Bleu', 'Rouge', 'Argent', 'Marron']
        equipements = [
            'Climatisation, Bluetooth, Caméra recul',
            'Toit ouvrant, GPS, Sièges cuir',
            'Régulateur vitesse, ABS, Airbags',
            'Écran tactile, Apple CarPlay, Radar recul',
        ]

        n = 0
        for i in range(60):
            modele = random.choice(modeles)
            marque_id = modele['marque_id']
            annee = random.randint(2015, 2024)
            etat = random.choice(['neuf', 'occasion', 'occasion', 'occasion'])
            km = random.randint(0, 5000) if etat == 'neuf' else random.randint(10000, 180000)
            prix_achat = random.randint(3000000, 25000000)
            marge_pct = random.uniform(1.15, 1.35)
            prix_vente = int(prix_achat * marge_pct)
            prix_loc_jour = int(prix_vente * 0.002)
            dispo_v = 1 if random.random() < 0.7 else 0
            dispo_l = 1 if random.random() < 0.8 else 0

            immat = f"DK-{random.randint(1000, 9999)}-{random.choice(['A', 'B', 'AB', 'CD'])}"

            cur.execute("""
                INSERT INTO vehicules (code, agence_id, marque_id, modele_id, immatriculation,
                                         vin_chassis, type, etat, annee, kilometrage, carburant,
                                         transmission, couleur, nb_portes, nb_places,
                                         puissance_ch, cylindree_cm3, prix_achat, prix_vente,
                                         prix_location_jour, prix_location_semaine, prix_location_mois,
                                         marge_estimee, disponible_vente, disponible_location,
                                         description, equipements, statut, date_acquisition, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None,
                  random.choice(agence_ids), marque_id, modele['id'], immat,
                  f"VIN{random.randint(100000, 999999)}",
                  modele['type'], etat, annee, km,
                  random.choice(['essence', 'diesel', 'hybride']),
                  random.choice(['manuelle', 'automatique']),
                  random.choice(couleurs),
                  random.choice([3, 4, 5]),
                  random.choice([2, 5, 7]),
                  random.randint(70, 350),
                  random.randint(1000, 3000),
                  prix_achat, prix_vente,
                  prix_loc_jour, prix_loc_jour * 6, prix_loc_jour * 25,
                  prix_vente - prix_achat,
                  dispo_v, dispo_l,
                  f"Véhicule {etat} en excellent état",
                  random.choice(equipements),
                  'disponible',
                  (datetime.now() - timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} véhicules créés")

    # ─── Clients ───
    cur.execute("SELECT COUNT(*) FROM clients")
    if cur.fetchone()[0] == 0:
        prenoms_h = ['Moussa', 'Amadou', 'Ibrahima', 'Cheikh', 'Ousmane', 'Mamadou', 'Pape']
        prenoms_f = ['Fatou', 'Awa', 'Aminata', 'Mariama', 'Aïssatou', 'Ndèye']
        noms = ['Diop', 'Ndiaye', 'Sall', 'Fall', 'Ba', 'Diallo', 'Sow', 'Sy', 'Faye']
        villes = ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Mbour', 'Kaolack']

        n = 0
        for i in range(50):
            sexe = random.choice(['M', 'F', 'M', 'M'])
            prenom = random.choice(prenoms_h if sexe == 'M' else prenoms_f)
            nom = random.choice(noms)
            tel = f'+221 77 {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}'

            cur.execute("""
                INSERT INTO clients (code, nom, prenom, type, telephone, whatsapp, email,
                                       adresse, ville, pays, piece_identite, permis_conduire,
                                       score, nb_achats, nb_locations, total_depense, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0,0,0, 'actif', ?)
            """, (None, nom, prenom,
                  random.choice(['particulier', 'particulier', 'entreprise']),
                  tel, tel,
                  f'{prenom.lower()}.{nom.lower()}@email.sn',
                  f'Quartier {random.choice(["Médina", "Plateau", "Yoff", "Almadies", "Sacré-Cœur"])}',
                  random.choice(villes), 'Sénégal',
                  f'CNI-{random.randint(100000, 999999)}',
                  f'PERM-{random.randint(100000, 999999)}',
                  random.randint(60, 100),
                  datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} clients créés")

    conn.commit()
    conn.close()
    print("[SEED] ✅ Données démo Omega Auto générées")


if __name__ == '__main__':
    init_db()
