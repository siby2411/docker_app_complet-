"""
🚛 Transport & Logistique — Initialisation base de données
Flotte · Chauffeurs · Missions · Colis · Entrepôts · Douanes
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = '/app/data/transport.db'


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
            role TEXT DEFAULT 'dispatcher',
            nom_complet TEXT,
            telephone TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Agences / Dépôts ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            nom TEXT NOT NULL,
            ville TEXT,
            pays TEXT DEFAULT 'Sénégal',
            adresse TEXT,
            telephone TEXT,
            responsable TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Flotte (camions, utilitaires, remorques) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            immatriculation TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            marque TEXT,
            modele TEXT,
            annee INTEGER,
            capacite_tonnes REAL DEFAULT 0,
            capacite_m3 REAL DEFAULT 0,
            statut TEXT DEFAULT 'disponible',
            kilometrage REAL DEFAULT 0,
            date_assurance TEXT,
            date_visite_technique TEXT,
            agence_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(agence_id) REFERENCES agences(id)
        )
    """)

    # ─── Chauffeurs ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chauffeurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_complet TEXT NOT NULL,
            telephone TEXT,
            numero_permis TEXT,
            categorie_permis TEXT,
            date_expiration_permis TEXT,
            agence_id INTEGER,
            statut TEXT DEFAULT 'disponible',
            note REAL DEFAULT 5.0,
            created_at TEXT,
            FOREIGN KEY(agence_id) REFERENCES agences(id)
        )
    """)

    # ─── Clients ───
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
            pays TEXT,
            created_at TEXT
        )
    """)

    # ─── Corridors (axes commerciaux) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS corridors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE NOT NULL,
            origine TEXT,
            destination TEXT,
            distance_km REAL DEFAULT 0,
            duree_moyenne_h INTEGER DEFAULT 0,
            tarif_base_fcfa REAL DEFAULT 0,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Missions (ordres de transport) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            client_id INTEGER,
            vehicule_id INTEGER,
            chauffeur_id INTEGER,
            corridor_id INTEGER,
            origine TEXT,
            destination TEXT,
            distance_km REAL DEFAULT 0,
            tonnage REAL DEFAULT 0,
            statut TEXT DEFAULT 'planifiee',
            date_depart TEXT,
            date_arrivee_prevue TEXT,
            date_arrivee_reelle TEXT,
            montant_fcfa REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id),
            FOREIGN KEY(chauffeur_id) REFERENCES chauffeurs(id),
            FOREIGN KEY(corridor_id) REFERENCES corridors(id)
        )
    """)

    # ─── Lots / Colis avec QR ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS colis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_suivi TEXT UNIQUE,
            mission_id INTEGER,
            client_id INTEGER,
            description TEXT,
            poids_kg REAL DEFAULT 0,
            volume_m3 REAL DEFAULT 0,
            valeur_fcfa REAL DEFAULT 0,
            qr_code TEXT,
            statut TEXT DEFAULT 'en_attente',
            date_scan_depart TEXT,
            date_scan_arrivee TEXT,
            created_at TEXT,
            FOREIGN KEY(mission_id) REFERENCES missions(id),
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    """)

    # ─── Entrepôts (cross-docking) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entrepots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT,
            ville TEXT,
            capacite_m3 REAL DEFAULT 0,
            occupe_m3 REAL DEFAULT 0,
            temperature_controlee INTEGER DEFAULT 0,
            responsable TEXT,
            telephone TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Douanes / Déclarations ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS declarations_douanes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_declaration TEXT UNIQUE,
            mission_id INTEGER,
            bureau_douane TEXT,
            pays_origine TEXT,
            pays_destination TEXT,
            valeur_marchandise REAL DEFAULT 0,
            droits_taxes REAL DEFAULT 0,
            statut TEXT DEFAULT 'en_cours',
            date_depot TEXT,
            date_liquidation TEXT,
            created_at TEXT,
            FOREIGN KEY(mission_id) REFERENCES missions(id)
        )
    """)

    # ─── Lettres de voiture (CMR) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cmr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_cmr TEXT UNIQUE,
            mission_id INTEGER,
            expediteur TEXT,
            destinataire TEXT,
            lieu_chargement TEXT,
            lieu_livraison TEXT,
            marchandise TEXT,
            poids_kg REAL DEFAULT 0,
            statut TEXT DEFAULT 'emis',
            date_emission TEXT,
            created_at TEXT,
            FOREIGN KEY(mission_id) REFERENCES missions(id)
        )
    """)

    # ─── Suivi GPS (positions temps réel) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tracking_gps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicule_id INTEGER NOT NULL,
            mission_id INTEGER,
            latitude REAL,
            longitude REAL,
            vitesse_kmh REAL DEFAULT 0,
            carburant_pct REAL DEFAULT 100,
            temperature_c REAL,
            date_position TEXT,
            created_at TEXT,
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id),
            FOREIGN KEY(mission_id) REFERENCES missions(id)
        )
    """)

    # ─── Facturation ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS factures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            mission_id INTEGER,
            client_id INTEGER,
            montant_ht REAL DEFAULT 0,
            tva REAL DEFAULT 0,
            montant_ttc REAL DEFAULT 0,
            statut TEXT DEFAULT 'emise',
            date_emission TEXT,
            date_echeance TEXT,
            date_paiement TEXT,
            created_at TEXT,
            FOREIGN KEY(mission_id) REFERENCES missions(id),
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    """)

    # ─── Alertes (retards, incidents) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alertes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            mission_id INTEGER,
            vehicule_id INTEGER,
            message TEXT,
            gravite TEXT DEFAULT 'info',
            traitee INTEGER DEFAULT 0,
            date_alerte TEXT,
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
        "CREATE INDEX IF NOT EXISTS idx_missions_statut ON missions(statut)",
        "CREATE INDEX IF NOT EXISTS idx_colis_suivi ON colis(numero_suivi)",
        "CREATE INDEX IF NOT EXISTS idx_tracking_vehicule ON tracking_gps(vehicule_id, date_position)",
        "CREATE INDEX IF NOT EXISTS idx_alertes_traitee ON alertes(traitee)",
    ]:
        try:
            cur.execute(idx)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # TRIGGERS — Code QR auto pour colis + numérotation mission
    # ═══════════════════════════════════════════════════════

    # Trigger : génération numéro suivi colis + QR
    cur.execute("DROP TRIGGER IF EXISTS trg_colis_qr_auto")
    cur.execute("""
        CREATE TRIGGER trg_colis_qr_auto
        AFTER INSERT ON colis
        FOR EACH ROW
        WHEN NEW.numero_suivi IS NULL OR NEW.numero_suivi = ''
        BEGIN
            UPDATE colis SET
                numero_suivi = 'COL-' || strftime('%Y%m%d', 'now') || '-' || substr('0000' || NEW.id, -4),
                qr_code = 'TRANSPORT|COLIS|' || NEW.id || '|' || datetime('now')
            WHERE id = NEW.id;
        END
    """)

    # Trigger : génération numéro mission
    cur.execute("DROP TRIGGER IF EXISTS trg_mission_numero_auto")
    cur.execute("""
        CREATE TRIGGER trg_mission_numero_auto
        AFTER INSERT ON missions
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE missions SET
                numero = 'MIS-' || strftime('%Y%m', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger : mise à jour statut véhicule + chauffeur quand mission démarre
    cur.execute("DROP TRIGGER IF EXISTS trg_mission_demarrage")
    cur.execute("""
        CREATE TRIGGER trg_mission_demarrage
        AFTER UPDATE OF statut ON missions
        FOR EACH ROW
        WHEN NEW.statut = 'en_cours' AND OLD.statut != 'en_cours'
        BEGIN
            UPDATE vehicules SET statut = 'en_mission' WHERE id = NEW.vehicule_id;
            UPDATE chauffeurs SET statut = 'en_mission' WHERE id = NEW.chauffeur_id;
        END
    """)

    # Trigger : libération véhicule + chauffeur quand mission terminée
    cur.execute("DROP TRIGGER IF EXISTS trg_mission_terminee")
    cur.execute("""
        CREATE TRIGGER trg_mission_terminee
        AFTER UPDATE OF statut ON missions
        FOR EACH ROW
        WHEN NEW.statut = 'terminee' AND OLD.statut != 'terminee'
        BEGIN
            UPDATE vehicules SET statut = 'disponible' WHERE id = NEW.vehicule_id;
            UPDATE chauffeurs SET statut = 'disponible' WHERE id = NEW.chauffeur_id;
        END
    """)

    conn.commit()
    conn.close()
    print("[INIT] ✅ Base Transport & Logistique prête")


def seed_demo():
    """Génère des données démo si base vide."""
    conn = get_conn()
    cur = conn.cursor()

    # Utilisateurs
    from werkzeug.security import generate_password_hash
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        for u in [
            ('admin', 'admin123', 'admin', 'Administrateur'),
            ('dispatcher', 'disp123', 'dispatcher', 'Fatou Sow'),
            ('chef_flotte', 'flotte123', 'chef_flotte', 'Ousmane Ba'),
            ('douanier', 'douane123', 'douanier', 'Moussa Diallo'),
        ]:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, nom_complet, actif, created_at)
                VALUES (?,?,?,?,1,?)
            """, (u[0], generate_password_hash(u[1]), u[2], u[3], datetime.now().isoformat()))
        print("[SEED] ✅ 4 utilisateurs créés")

    # Agences
    cur.execute("SELECT COUNT(*) FROM agences")
    if cur.fetchone()[0] == 0:
        agences = [
            ('AG-DKR', 'Agence Dakar Port', 'Dakar', 'Sénégal', 'Zone portuaire, Dakar', '+221 33 849 10 10', 'Ibrahima Sall'),
            ('AG-BKO', 'Agence Bamako', 'Bamako', 'Mali', 'Zone industrielle, Bamako', '+223 20 22 10 10', 'Moussa Traoré'),
            ('AG-ABJ', 'Agence Abidjan', 'Abidjan', "Côte d'Ivoire", 'Port d\'Abidjan', '+225 27 20 10 10', 'Konan Yao'),
            ('AG-THS', 'Dépôt Thiès', 'Thiès', 'Sénégal', 'Route nationale 2', '+221 33 951 10 10', 'Awa Fall'),
        ]
        for a in agences:
            cur.execute("""
                INSERT INTO agences (code, nom, ville, pays, adresse, telephone, responsable, actif, created_at)
                VALUES (?,?,?,?,?,?,?,1,?)
            """, (*a, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(agences)} agences créées")

    # Corridors
    cur.execute("SELECT COUNT(*) FROM corridors")
    if cur.fetchone()[0] == 0:
        corridors = [
            ('Dakar-Bamako', 'Dakar', 'Bamako', 1300, 48, 350000),
            ('Dakar-Abidjan', 'Dakar', 'Abidjan', 2200, 72, 650000),
            ('Dakar-Conakry', 'Dakar', 'Conakry', 1000, 36, 280000),
            ('Dakar-Nouakchott', 'Dakar', 'Nouakchott', 800, 24, 220000),
            ('Thiès-Ziguinchor', 'Thiès', 'Ziguinchor', 450, 18, 180000),
        ]
        for c in corridors:
            cur.execute("""
                INSERT INTO corridors (nom, origine, destination, distance_km, duree_moyenne_h, tarif_base_fcfa, actif, created_at)
                VALUES (?,?,?,?,?,?,1,?)
            """, (*c, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(corridors)} corridors créés")

    # Clients
    cur.execute("SELECT COUNT(*) FROM clients")
    if cur.fetchone()[0] == 0:
        clients = [
            ('CLI-001', 'SONACOS', 'industriel', 'Mamadou Diop', '+221 33 839 00 00', 'contact@sonacos.sn', 'Dakar, Sénégal', 'Sénégal'),
            ('CLI-002', 'SENELEC', 'industriel', 'Fatou Ndiaye', '+221 33 839 11 11', 'contact@senelec.sn', 'Dakar, Sénégal', 'Sénégal'),
            ('CLI-003', 'Ciments du Sahel', 'industriel', 'Ousmane Sall', '+221 33 957 22 22', 'info@cimentsdusahel.sn', 'Thiès, Sénégal', 'Sénégal'),
            ('CLI-004', 'SONATEL', 'telecom', 'Awa Diallo', '+221 33 839 33 33', 'contact@sonatel.sn', 'Dakar, Sénégal', 'Sénégal'),
            ('CLI-005', 'SM10 AGRO', 'agro', 'Sadio Mané', '+221 77 654 28 03', 'contact@sm10agro.sn', 'Dakar, Sénégal', 'Sénégal'),
        ]
        for c in clients:
            cur.execute("""
                INSERT INTO clients (code, nom, type, contact, telephone, email, adresse, pays, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (*c, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(clients)} clients créés")

    # Véhicules
    cur.execute("SELECT COUNT(*) FROM vehicules")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM agences LIMIT 4")
        ag_ids = [r[0] for r in cur.fetchall()]
        vehicules = [
            ('DK-1234-AB', 'camion_40t', 'Mercedes-Benz', 'Actros 1845', 2019, 40, 90),
            ('DK-5678-CD', 'camion_20t', 'Renault', 'Premium 380', 2020, 20, 60),
            ('DK-9012-EF', 'camion_30t', 'Volvo', 'FH 500', 2021, 30, 75),
            ('TH-1111-GH', 'utilitaire_3.5t', 'Peugeot', 'Boxer', 2022, 3.5, 15),
            ('TH-2222-IJ', 'camion_10t', 'Iveco', 'Eurocargo', 2018, 10, 40),
            ('DK-3333-KL', 'frigorifique', 'Mercedes-Benz', 'Atego Frigo', 2022, 12, 45),
            ('DK-4444-MN', 'porte_conteneur', 'Scania', 'R450', 2021, 35, 100),
            ('TH-5555-OP', 'camion_40t', 'MAN', 'TGX 18.500', 2020, 40, 90),
        ]
        for v in vehicules:
            cur.execute("""
                INSERT INTO vehicules
                (immatriculation, type, marque, modele, annee, capacite_tonnes, capacite_m3,
                 statut, kilometrage, date_assurance, date_visite_technique, agence_id, created_at)
                VALUES (?,?,?,?,?,?,?,'disponible',?,?,?,?,?)
            """, (v[0], v[1], v[2], v[3], v[4], v[5], v[6],
                  random.randint(50000, 500000),
                  (datetime.now() + timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d'),
                  (datetime.now() + timedelta(days=random.randint(30, 180))).strftime('%Y-%m-%d'),
                  random.choice(ag_ids) if ag_ids else None,
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(vehicules)} véhicules créés")

    # Chauffeurs
    cur.execute("SELECT COUNT(*) FROM chauffeurs")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM agences LIMIT 4")
        ag_ids = [r[0] for r in cur.fetchall()]
        chauffeurs = [
            ('Amadou Diallo', '+221 77 111 11 11', 'SN-PERM-001', 'CE'),
            ('Moussa Ndiaye', '+221 77 222 22 22', 'SN-PERM-002', 'CE'),
            ('Ibrahima Sall', '+221 77 333 33 33', 'SN-PERM-003', 'CE'),
            ('Fatou Diop', '+221 77 444 44 44', 'SN-PERM-004', 'C'),
            ('Ousmane Ba', '+221 77 555 55 55', 'SN-PERM-005', 'CE'),
            ('Awa Fall', '+221 77 666 66 66', 'SN-PERM-006', 'C'),
            ('Cheikh Sow', '+221 77 777 77 77', 'SN-PERM-007', 'CE'),
            ('Mariama Diallo', '+221 77 888 88 88', 'SN-PERM-008', 'CE'),
        ]
        for c in chauffeurs:
            cur.execute("""
                INSERT INTO chauffeurs
                (nom_complet, telephone, numero_permis, categorie_permis,
                 date_expiration_permis, agence_id, statut, note, created_at)
                VALUES (?,?,?,?,?,?,'disponible',?,?)
            """, (c[0], c[1], c[2], c[3],
                  (datetime.now() + timedelta(days=random.randint(90, 730))).strftime('%Y-%m-%d'),
                  random.choice(ag_ids) if ag_ids else None,
                  round(random.uniform(3.5, 5.0), 1),
                  datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(chauffeurs)} chauffeurs créés")

    # Missions démo
    cur.execute("SELECT COUNT(*) FROM missions")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM vehicules LIMIT 8")
        veh_ids = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT id FROM chauffeurs LIMIT 8")
        chf_ids = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT id FROM clients LIMIT 5")
        cli_ids = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT id, distance_km, tarif_base_fcfa, origine, destination FROM corridors")
        corridors = cur.fetchall()

        for i in range(15):
            cor = random.choice(corridors)
            statut = random.choice(['planifiee', 'en_cours', 'terminee', 'terminee', 'terminee'])
            date_depart = datetime.now() - timedelta(days=random.randint(-5, 30))
            duree_h = cor['distance_km'] / 50  # ~50 km/h moyenne
            date_arrivee = date_depart + timedelta(hours=duree_h)
            tonnage = random.randint(10, 40)
            montant = tonnage * cor['tarif_base_fcfa'] / 30  # tarif au tonnage

            # Générer le numéro de mission directement
            cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM missions")
            next_id = cur.fetchone()[0]
            numero = f"MIS-{datetime.now().strftime('%Y%m')}-{next_id:04d}"

            cur.execute("""
                INSERT INTO missions
                (numero, client_id, vehicule_id, chauffeur_id, corridor_id,
                 origine, destination, distance_km, tonnage, statut,
                 date_depart, date_arrivee_prevue, date_arrivee_reelle, montant_fcfa, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (numero, random.choice(cli_ids) if cli_ids else None,
                  random.choice(veh_ids) if veh_ids else None,
                  random.choice(chf_ids) if chf_ids else None,
                  cor['id'], cor['origine'], cor['destination'],
                  cor['distance_km'], tonnage, statut,
                  date_depart.isoformat(),
                  date_arrivee.isoformat(),
                  date_arrivee.isoformat() if statut == 'terminee' else None,
                  montant, datetime.now().isoformat()))
        print("[SEED] ✅ 15 missions créées")

    # Colis démo
    cur.execute("SELECT COUNT(*) FROM colis")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, client_id FROM missions LIMIT 15")
        missions = cur.fetchall()
        n_colis = 0
        for m in missions:
            for _ in range(random.randint(2, 8)):
                poids = random.randint(50, 5000)
                cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM colis")
                next_cid = cur.fetchone()[0]
                num_suivi = f"COL-{datetime.now().strftime('%Y%m%d')}-{next_cid:04d}"

                cur.execute("""
                    INSERT INTO colis
                    (numero_suivi, mission_id, client_id, description,
                     poids_kg, volume_m3, valeur_fcfa, statut, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (num_suivi, m['id'], m['client_id'],
                      random.choice(['Palettes de riz', 'Sacs de ciment', 'Cartons divers',
                                     'Mangues fraîches', 'Équipements industriels',
                                     'Produits chimiques', 'Matériel agricole']),
                      poids, round(poids / 300, 2),
                      random.randint(100000, 5000000),
                      random.choice(['en_attente', 'en_transit', 'livre']),
                      datetime.now().isoformat()))
                n_colis += 1
        print(f"[SEED] ✅ {n_colis} colis créés")

    # Entrepôts
    cur.execute("SELECT COUNT(*) FROM entrepots")
    if cur.fetchone()[0] == 0:
        entrepots = [
            ('ENT-DKR-01', 'Entrepôt Dakar Port', 'Dakar', 5000, 0, 1, 'Ibrahima Sall', '+221 33 849 10 10'),
            ('ENT-THS-01', 'Entrepôt Thiès', 'Thiès', 3000, 0, 1, 'Awa Fall', '+221 33 951 10 10'),
            ('ENT-BKO-01', 'Entrepôt Bamako', 'Bamako', 4000, 0, 0, 'Moussa Traoré', '+223 20 22 10 10'),
        ]
        for e in entrepots:
            cur.execute("""
                INSERT INTO entrepots (code, nom, ville, capacite_m3, occupe_m3,
                                       temperature_controlee, responsable, telephone, actif, created_at)
                VALUES (?,?,?,?,?,?,?,?,1,?)
            """, (*e, datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(entrepots)} entrepôts créés")

    # Alertes
    cur.execute("SELECT COUNT(*) FROM alertes")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, numero FROM missions WHERE statut='en_cours' LIMIT 3")
        missions_encours = cur.fetchall()
        for m in missions_encours:
            cur.execute("""
                INSERT INTO alertes (type, mission_id, message, gravite, traitee, date_alerte, created_at)
                VALUES (?,?,?,?,0,?,?)
            """, ('retard', m['id'], f"Mission {m['numero']} en retard de 2h", 'warning',
                  datetime.now().isoformat(), datetime.now().isoformat()))
        print("[SEED] ✅ Alertes créées")

    conn.commit()
    conn.close()
    print("[SEED] ✅ Données démo Transport générées")


if __name__ == '__main__':
    init_db()
