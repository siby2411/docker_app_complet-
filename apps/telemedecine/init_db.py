

"""
🩺 Télémédecine — Base de données
Patients · Médecins · Consultations · Ordonnances · Pharmacies · Paiements
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = '/app/data/telemedecine.db'


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()

    # ─── Utilisateurs (médecins, admin, patients) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'patient',
            nom_complet TEXT,
            email TEXT,
            telephone TEXT,
            langue TEXT DEFAULT 'fr',
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # ─── Médecins ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS medecins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            user_id INTEGER,
            nom TEXT NOT NULL,
            prenom TEXT,
            specialite TEXT,
            numero_ordre TEXT,
            telephone TEXT,
            email TEXT,
            hopital TEXT,
            ville TEXT,
            tarif_consultation REAL DEFAULT 5000,
            disponible INTEGER DEFAULT 1,
            note_moyenne REAL DEFAULT 0,
            nb_consultations INTEGER DEFAULT 0,
            langues TEXT,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # ─── Patients (données chiffrées) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            user_id INTEGER,
            nom_encrypted TEXT,
            prenom_encrypted TEXT,
            date_naissance_encrypted TEXT,
            telephone_encrypted TEXT,
            adresse_encrypted TEXT,
            sexe TEXT,
            ville TEXT,
            groupe_sanguin TEXT,
            allergies_encrypted TEXT,
            antecedents_encrypted TEXT,
            langue TEXT DEFAULT 'fr',
            hash_id TEXT,
            statut TEXT DEFAULT 'actif',
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # ─── Dossiers médicaux ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dossiers_medicaux (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            consultation_id INTEGER,
            type TEXT,
            contenu_encrypted TEXT,
            diagnostic_encrypted TEXT,
            traitement_encrypted TEXT,
            notes_encrypted TEXT,
            medecin_id INTEGER,
            date_creation TEXT,
            created_at TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(medecin_id) REFERENCES medecins(id)
        )
    """)

    # ─── Consultations (télémédecine) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS consultations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            patient_id INTEGER,
            medecin_id INTEGER,
            date_consultation TEXT,
            heure_debut TEXT,
            heure_fin TEXT,
            duree_minutes INTEGER DEFAULT 0,
            motif TEXT,
            symptomes TEXT,
            diagnostic TEXT,
            type TEXT DEFAULT 'video',
            statut TEXT DEFAULT 'planifiee',
            salle_video TEXT,
            lien_video TEXT,
            niveau_urgence TEXT DEFAULT 'normal',
            montant REAL DEFAULT 0,
            mode_paiement TEXT,
            statut_paiement TEXT DEFAULT 'en_attente',
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(medecin_id) REFERENCES medecins(id)
        )
    """)

    # ─── Ordonnances numériques ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ordonnances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            consultation_id INTEGER,
            patient_id INTEGER,
            medecin_id INTEGER,
            date_emission TEXT,
            medicaments TEXT,
            posologie TEXT,
            duree_jours INTEGER DEFAULT 7,
            instructions TEXT,
            signature_rsa TEXT,
            qr_code TEXT,
            statut TEXT DEFAULT 'emise',
            created_at TEXT,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id),
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(medecin_id) REFERENCES medecins(id)
        )
    """)

    # ─── Pharmacies partenaires ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pharmacies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            adresse TEXT,
            ville TEXT,
            region TEXT,
            telephone TEXT,
            responsable TEXT,
            num_licence TEXT,
            latitude REAL,
            longitude REAL,
            statut TEXT DEFAULT 'actif',
            created_at TEXT
        )
    """)

    # ─── Dispensations (pharmacie) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dispensations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ordonnance_id INTEGER,
            pharmacie_id INTEGER,
            date_dispensation TEXT,
            statut TEXT DEFAULT 'delivre',
            montant REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(ordonnance_id) REFERENCES ordonnances(id),
            FOREIGN KEY(pharmacie_id) REFERENCES pharmacies(id)
        )
    """)

    # ─── Paiements mobile money ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER,
            patient_id INTEGER,
            operateur TEXT,
            telephone TEXT,
            montant REAL DEFAULT 0,
            reference TEXT,
            statut TEXT DEFAULT 'en_attente',
            date_paiement TEXT,
            created_at TEXT,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id),
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

    # ─── Suivi post-consultation ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS suivi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER,
            patient_id INTEGER,
            date_suivi TEXT,
            type TEXT,
            observations TEXT,
            tension TEXT,
            temperature REAL,
            poids REAL,
            statut TEXT DEFAULT 'normal',
            created_at TEXT,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id),
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

    # ─── Messages (chat sécurisé) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER,
            expediteur_id INTEGER,
            destinataire_id INTEGER,
            contenu_encrypted TEXT,
            lu INTEGER DEFAULT 0,
            date_message TEXT,
            created_at TEXT,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id)
        )
    """)

    # ─── Journal audit RGPD ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_rgpd (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            entity TEXT,
            entity_id INTEGER,
            details TEXT,
            ip TEXT,
            user_agent TEXT,
            created_at TEXT
        )
    """)

    # ─── Session vidéo (WebRTC signaling) ───
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions_video (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id INTEGER,
            room_id TEXT UNIQUE,
            token_patient TEXT,
            token_medecin TEXT,
            statut TEXT DEFAULT 'attente',
            debut_video TEXT,
            fin_video TEXT,
            duree_reelle INTEGER DEFAULT 0,
            qualite TEXT DEFAULT 'hd',
            created_at TEXT,
            FOREIGN KEY(consultation_id) REFERENCES consultations(id)
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
        "CREATE INDEX IF NOT EXISTS idx_patients_hash ON patients(hash_id)",
        "CREATE INDEX IF NOT EXISTS idx_consultations_statut ON consultations(statut)",
        "CREATE INDEX IF NOT EXISTS idx_consultations_patient ON consultations(patient_id)",
        "CREATE INDEX IF NOT EXISTS idx_consultations_medecin ON consultations(medecin_id)",
        "CREATE INDEX IF NOT EXISTS idx_ordonnances_patient ON ordonnances(patient_id)",
    ]:
        try:
            cur.execute(idx)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # TRIGGERS
    # ═══════════════════════════════════════════════════════

    # Trigger 1 : code patient auto
    cur.execute("DROP TRIGGER IF EXISTS trg_patient_code")
    cur.execute("""
        CREATE TRIGGER trg_patient_code
        AFTER INSERT ON patients
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE patients SET
                code = 'PAT-' || strftime('%Y%m', 'now') || '-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 2 : numéro consultation auto
    cur.execute("DROP TRIGGER IF EXISTS trg_consultation_numero")
    cur.execute("""
        CREATE TRIGGER trg_consultation_numero
        AFTER INSERT ON consultations
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE consultations SET
                numero = 'CONS-' || strftime('%Y%m%d', 'now') || '-' || substr('0000' || NEW.id, -4),
                salle_video = 'room_' || NEW.id || '_' || hex(randomblob(4))
            WHERE id = NEW.id;
        END
    """)

    # Trigger 3 : numéro ordonnance auto + QR
    cur.execute("DROP TRIGGER IF EXISTS trg_ordonnance_numero")
    cur.execute("""
        CREATE TRIGGER trg_ordonnance_numero
        AFTER INSERT ON ordonnances
        FOR EACH ROW
        WHEN NEW.numero IS NULL OR NEW.numero = ''
        BEGIN
            UPDATE ordonnances SET
                numero = 'ORD-' || strftime('%Y%m%d', 'now') || '-' || substr('0000' || NEW.id, -4),
                qr_code = 'TELEMED|ORD|' || NEW.id
            WHERE id = NEW.id;
        END
    """)

    # Trigger 4 : code médecin auto
    cur.execute("DROP TRIGGER IF EXISTS trg_medecin_code")
    cur.execute("""
        CREATE TRIGGER trg_medecin_code
        AFTER INSERT ON medecins
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE medecins SET
                code = 'MED-' || substr('0000' || NEW.id, -4)
            WHERE id = NEW.id;
        END
    """)

    # Trigger 5 : MAJ nb_consultations médecin après consultation terminée
    cur.execute("DROP TRIGGER IF EXISTS trg_consultation_terminee")
    cur.execute("""
        CREATE TRIGGER trg_consultation_terminee
        AFTER UPDATE OF statut ON consultations
        FOR EACH ROW
        WHEN NEW.statut = 'terminee' AND OLD.statut != 'terminee'
        BEGIN
            UPDATE medecins SET
                nb_consultations = nb_consultations + 1
            WHERE id = NEW.medecin_id;
        END
    """)

    conn.commit()
    conn.close()
    print("[INIT] ✅ Base Télémédecine prête")


def seed_demo():
    """Génère des données démo si base vide."""
    conn = get_conn()
    cur = conn.cursor()

    from werkzeug.security import generate_password_hash
    from crypto_utils import encrypt_data, hash_patient_id

    # ─── Users ───
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        users = [
            ('admin', 'admin123', 'admin', 'Administrateur', 'admin@telemed.sn', '+221 77 000 00 00'),
            ('dr.diop', 'medecin123', 'medecin', 'Dr. Cheikh Diop', 'cheikh@telemed.sn', '+221 77 111 11 11'),
            ('dr.sow', 'medecin123', 'medecin', 'Dr. Fatou Sow', 'fatou@telemed.sn', '+221 77 222 22 22'),
            ('dr.ba', 'medecin123', 'medecin', 'Dr. Ousmane Ba', 'ousmane@telemed.sn', '+221 77 333 33 33'),
            ('dr.fall', 'medecin123', 'medecin', 'Dr. Awa Fall', 'awa@telemed.sn', '+221 77 444 44 44'),
            ('patient1', 'patient123', 'patient', 'Moussa Ndiaye', 'moussa@email.sn', '+221 77 555 55 55'),
            ('patient2', 'patient123', 'patient', 'Awa Sy', 'awa.sy@email.sn', '+221 77 666 66 66'),
            ('patient3', 'patient123', 'patient', 'Ibrahima Ba', 'ibra@email.sn', '+221 77 777 77 77'),
        ]
        for u in users:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, nom_complet, email, telephone, actif, created_at)
                VALUES (?,?,?,?,?,?,1,?)
            """, (u[0], generate_password_hash(u[1]), u[2], u[3], u[4], u[5], datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(users)} utilisateurs créés")

    # ─── Médecins ───
    cur.execute("SELECT COUNT(*) FROM medecins")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM users WHERE role='medecin'")
        medecin_user_ids = [r[0] for r in cur.fetchall()]
        specialites = ['Généraliste', 'Pédiatre', 'Cardiologue', 'Dermatologue', 'Gynécologue']
        hopitaux = ['Hôpital Principal Dakar', 'Hôpital Fann', 'Clinique Pasteur', 'Hôpital Thiès']

        for i, uid in enumerate(medecin_user_ids):
            cur.execute("""
                INSERT INTO medecins (code, user_id, nom, prenom, specialite, telephone, email,
                                        hopital, ville, tarif_consultation, disponible,
                                        note_moyenne, nb_consultations, langues, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,1,?,0,?,?)
            """, (None, uid,
                  ['Diop', 'Sow', 'Ba', 'Fall'][i % 4],
                  ['Cheikh', 'Fatou', 'Ousmane', 'Awa'][i % 4],
                  random.choice(specialites),
                  f'+221 77 {random.randint(100,999)} 00 00',
                  f'dr{i+1}@telemed.sn',
                  random.choice(hopitaux),
                  random.choice(['Dakar', 'Thiès', 'Ziguinchor']),
                  random.randint(3000, 15000),
                  round(random.uniform(4.2, 5.0), 1),
                  'fr,wo,en',
                  datetime.now().isoformat()))
        print("[SEED] ✅ Médecins créés")

    cur.execute("SELECT id FROM medecins")
    medecin_ids = [r[0] for r in cur.fetchall()]

    # ─── Patients (chiffrés) ───
    cur.execute("SELECT COUNT(*) FROM patients")
    if cur.fetchone()[0] == 0:
        prenoms_h = ['Moussa', 'Amadou', 'Ibrahima', 'Cheikh', 'Ousmane']
        prenoms_f = ['Fatou', 'Awa', 'Aminata', 'Mariama', 'Aïssatou']
        noms = ['Diop', 'Ndiaye', 'Sall', 'Fall', 'Ba', 'Diallo']
        regions = ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Kaolack', 'Tambacounda']
        groupes_sanguins = ['O+', 'O-', 'A+', 'A-', 'B+', 'AB+']

        for i in range(30):
            sexe = random.choice(['M', 'F'])
            prenom = random.choice(prenoms_h if sexe == 'M' else prenoms_f)
            nom = random.choice(noms)
            age = random.randint(5, 85)
            date_naiss = (datetime.now() - timedelta(days=age*365)).strftime('%Y-%m-%d')
            tel = f'+221 77 {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}'

            cur.execute("""
                INSERT INTO patients (code, user_id, nom_encrypted, prenom_encrypted,
                                        date_naissance_encrypted, telephone_encrypted,
                                        adresse_encrypted, sexe, ville, groupe_sanguin,
                                        allergies_encrypted, antecedents_encrypted,
                                        langue, hash_id, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (None, None,
                  encrypt_data(nom), encrypt_data(prenom),
                  encrypt_data(date_naiss), encrypt_data(tel),
                  encrypt_data(f'Quartier {random.choice(["Médina", "Plateau", "Yoff"])}'),
                  sexe, random.choice(regions),
                  random.choice(groupes_sanguins),
                  encrypt_data(random.choice(['Aucune', 'Pénicilline', 'Arachides', 'Pollen'])),
                  encrypt_data(random.choice(['Aucun', 'Diabète type 2', 'Hypertension', 'Asthme'])),
                  random.choice(['fr', 'wo', 'fr', 'fr']),
                  hash_patient_id(i + 1),
                  datetime.now().isoformat()))
        print("[SEED] ✅ 30 patients créés (chiffrés AES-256)")

    # ─── Pharmacies ───
    cur.execute("SELECT COUNT(*) FROM pharmacies")
    if cur.fetchone()[0] == 0:
        pharmacies = [
            ('Pharmacie de la Médina', 'Dakar', 'Dakar', '+221 33 821 00 01'),
            ('Pharmacie du Plateau', 'Dakar', 'Dakar', '+221 33 823 00 02'),
            ('Pharmacie Thiès Centre', 'Thiès', 'Thiès', '+221 33 951 00 03'),
            ('Pharmacie Ziguinchor', 'Ziguinchor', 'Ziguinchor', '+221 33 991 00 04'),
            ('Pharmacie Saint-Louis', 'Saint-Louis', 'Saint-Louis', '+221 33 961 00 05'),
        ]
        for p in pharmacies:
            cur.execute("""
                INSERT INTO pharmacies (code, nom, ville, region, telephone, statut, created_at)
                VALUES (?,?,?,?,?, 'actif', ?)
            """, (None, p[0], p[1], p[2], p[3], datetime.now().isoformat()))
        print(f"[SEED] ✅ {len(pharmacies)} pharmacies créées")

    # ─── Consultations démo ───
    cur.execute("SELECT COUNT(*) FROM consultations")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id FROM patients")
        patient_ids = [r[0] for r in cur.fetchall()]
        motifs = ['Fièvre', 'Toux persistante', 'Maux de tête', 'Douleur abdominale',
                  'Éruption cutanée', 'Fatigue chronique', 'Suivi diabète', 'Suivi grossesse']

        n = 0
        for i in range(25):
            date_c = datetime.now() - timedelta(days=random.randint(0, 60))
            statut = random.choice(['planifiee', 'terminee', 'terminee', 'annulee'])
            cur.execute("""
                INSERT INTO consultations (numero, patient_id, medecin_id, date_consultation,
                                             motif, symptomes, type, statut, niveau_urgence,
                                             montant, mode_paiement, statut_paiement, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None, random.choice(patient_ids), random.choice(medecin_ids),
                  date_c.strftime('%Y-%m-%d'),
                  random.choice(motifs),
                  'Symptômes décrits par le patient',
                  random.choice(['video', 'audio', 'chat']),
                  statut,
                  random.choice(['normal', 'normal', 'urgent', 'faible']),
                  random.randint(3000, 15000),
                  random.choice(['mobile_money', 'especes', 'mutuelle']),
                  'paye' if statut == 'terminee' else 'en_attente',
                  datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} consultations créées")

    # ─── Ordonnances ───
    cur.execute("SELECT COUNT(*) FROM ordonnances")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, patient_id, medecin_id FROM consultations WHERE statut='terminee'")
        consultations = cur.fetchall()
        medicaments_list = [
            'Paracétamol 500mg, Amoxicilline 500mg',
            'Ibuprofène 400mg, Oméprazole 20mg',
            'Artéméther-Luméfantrine, Paracétamol',
            'Metformine 850mg, Amlodipine 5mg',
            'Salbutamol spray, Prednisolone 20mg',
        ]

        n = 0
        for c in consultations:
            from crypto_utils import sign_ordonnance
            meds = random.choice(medicaments_list)
            payload = f'ORD|{c["id"]}|{c["patient_id"]}|{c["medecin_id"]}|{meds}'
            signature = sign_ordonnance(payload) or 'unsigned'

            cur.execute("""
                INSERT INTO ordonnances (numero, consultation_id, patient_id, medecin_id,
                                           date_emission, medicaments, posologie, duree_jours,
                                           instructions, signature_rsa, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?, 'emise', ?)
            """, (None, c['id'], c['patient_id'], c['medecin_id'],
                  datetime.now().strftime('%Y-%m-%d'),
                  meds,
                  random.choice(['1 comprimé 2x/jour', '1 comprimé 3x/jour', '2 comprimés matin et soir']),
                  random.randint(3, 14),
                  'Prendre pendant les repas. Ne pas dépasser la dose prescrite.',
                  signature,
                  datetime.now().isoformat()))
            n += 1
        print(f"[SEED] ✅ {n} ordonnances créées (signées RSA)")


    conn.commit()
    conn.close()
    print("[SEED] ✅ Données démo Télémédecine générées")


if __name__ == '__main__':
    init_db()
