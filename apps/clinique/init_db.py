"""
Initialisation base de données Clinique Omega
14 tables conformes aux normes OMS / CIM-10
"""
import sqlite3
import os
import sys
from datetime import datetime, timedelta

DB_PATH = "/app/data/clinique.db"


def init_db():
    os.makedirs("/app/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    c = conn.cursor()

    # ==================== 1. SITES (bâtiments physiques) ====================
    c.execute("""CREATE TABLE IF NOT EXISTS sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        adresse TEXT,
        ville TEXT NOT NULL,
        region TEXT,
        telephone TEXT,
        email TEXT,
        latitude REAL,
        longitude REAL,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 2. DEPARTEMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS departements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        chef_id INTEGER,
        telephone TEXT,
        email TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 3. SALLES (localisation) ====================
    c.execute("""CREATE TABLE IF NOT EXISTS salles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        site_id INTEGER NOT NULL,
        departement_id INTEGER,
        batiment TEXT NOT NULL,
        etage INTEGER NOT NULL DEFAULT 0,
        type TEXT NOT NULL,
        capacite INTEGER DEFAULT 1,
        equipements TEXT,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (site_id) REFERENCES sites(id),
        FOREIGN KEY (departement_id) REFERENCES departements(id)
    )""")

    # ==================== 4. UTILISATEURS (RBAC) ====================
    c.execute("""CREATE TABLE IF NOT EXISTS utilisateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        email TEXT,
        telephone TEXT,
        role TEXT NOT NULL DEFAULT 'patient',
        actif INTEGER DEFAULT 1,
        dernier_login TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 5. MEDECINS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS medecins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        specialite TEXT NOT NULL,
        num_ordre TEXT,
        telephone TEXT NOT NULL,
        email TEXT,
        departement_id INTEGER,
        annees_experience INTEGER DEFAULT 0,
        tarif_consultation REAL DEFAULT 15000,
        biographie TEXT,
        langues TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (departement_id) REFERENCES departements(id)
    )""")

    # ==================== 6. PERSONNEL (infirmiers, admin, etc.) ====================
    c.execute("""CREATE TABLE IF NOT EXISTS personnel (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        fonction TEXT NOT NULL,
        telephone TEXT NOT NULL,
        email TEXT,
        departement_id INTEGER,
        date_embauche TEXT,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (departement_id) REFERENCES departements(id)
    )""")

    # ==================== 7. PATIENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_dossier TEXT UNIQUE NOT NULL,
        carte_medicale TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        date_naissance TEXT NOT NULL,
        lieu_naissance TEXT,
        sexe TEXT NOT NULL,
        groupe_sanguin TEXT,
        telephone TEXT NOT NULL,
        telephone_urgence TEXT,
        email TEXT,
        adresse TEXT,
        ville TEXT,
        region TEXT,
        profession TEXT,
        situation_matrimoniale TEXT,
        personne_contact TEXT,
        allergies TEXT,
        antecedents_medicaux TEXT,
        traitement_en_cours TEXT,
        assurance TEXT,
        numero_assurance TEXT,
        photo TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 8. CONSULTATIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS consultations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        patient_id INTEGER NOT NULL,
        medecin_id INTEGER NOT NULL,
        departement_id INTEGER,
        date_consultation TEXT NOT NULL,
        motif TEXT NOT NULL,
        temperature REAL,
        tension TEXT,
        pouls INTEGER,
        poids REAL,
        taille REAL,
        spo2 INTEGER,
        glycemie REAL,
        examen_clinique TEXT,
        diagnostic_principal TEXT,
        code_cim10 TEXT,
        diagnostic_secondaire TEXT,
        conduite_tenue TEXT,
        observations TEXT,
        cout REAL DEFAULT 0,
        statut TEXT DEFAULT 'En cours',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id),
        FOREIGN KEY (medecin_id) REFERENCES medecins(id),
        FOREIGN KEY (departement_id) REFERENCES departements(id)
    )""")

    # ==================== 9. DIAGNOSTICS CIM-10 ====================
    c.execute("""CREATE TABLE IF NOT EXISTS cim10 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        libelle TEXT NOT NULL,
        categorie TEXT,
        chapitre TEXT
    )""")

    # ==================== 10. PRESCRIPTIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS prescriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        consultation_id INTEGER NOT NULL,
        medicament TEXT NOT NULL,
        dosage TEXT,
        posologie TEXT,
        duree TEXT,
        instructions TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (consultation_id) REFERENCES consultations(id)
    )""")

    # ==================== 11. HOSPITALISATIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS hospitalisations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        patient_id INTEGER NOT NULL,
        medecin_referent_id INTEGER,
        salle_id INTEGER NOT NULL,
        lit_numero TEXT,
        date_entree TEXT NOT NULL,
        date_sortie TEXT,
        motif TEXT NOT NULL,
        diagnostic TEXT,
        cout_journalier REAL DEFAULT 0,
        statut TEXT DEFAULT 'En cours',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id),
        FOREIGN KEY (salle_id) REFERENCES salles(id)
    )""")

    # ==================== 12. FACTURES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS factures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        patient_id INTEGER NOT NULL,
        date_emission TEXT NOT NULL,
        montant_total REAL NOT NULL DEFAULT 0,
        montant_paye REAL DEFAULT 0,
        mode_paiement TEXT,
        statut TEXT DEFAULT 'Impayé',
        observations TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )""")

    # ==================== 13. LIGNES FACTURES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS lignes_facture (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        facture_id INTEGER NOT NULL,
        designation TEXT NOT NULL,
        quantite INTEGER DEFAULT 1,
        prix_unitaire REAL NOT NULL,
        montant REAL NOT NULL,
        FOREIGN KEY (facture_id) REFERENCES factures(id)
    )""")

    # ==================== 14. RENDEZ-VOUS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS rendez_vous (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        medecin_id INTEGER NOT NULL,
        date_rdv TEXT NOT NULL,
        heure_rdv TEXT NOT NULL,
        motif TEXT,
        statut TEXT DEFAULT 'Programmé',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id),
        FOREIGN KEY (medecin_id) REFERENCES medecins(id)
    )""")

    # ==================== 15. AUDIT LOG ====================
    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        ip TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()

    # ==================== SEED INITIAL ====================
    c.execute("SELECT COUNT(*) FROM sites")
    if c.fetchone()[0] == 0:
        print("[INIT] Insertion des données de démonstration...")

        # Sites
        c.executemany("""INSERT INTO sites (code, nom, adresse, ville, region, telephone, email)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", [
            ('CLN-DK', 'Clinique Omega Dakar', 'Avenue Cheikh Anta Diop, Fann', 'Dakar', 'Dakar', '+221 33 800 00 01', 'contact@omega-clinique.sn'),
            ('CLN-TH', 'Clinique Omega Thiès', 'Route de Dakar, Quartier Escale', 'Thiès', 'Thiès', '+221 33 800 00 02', 'thies@omega-clinique.sn'),
        ])

        # Départements
        c.executemany("""INSERT INTO departements (code, nom, description, telephone, email)
            VALUES (?, ?, ?, ?, ?)""", [
            ('DEP-CARD', 'Cardiologie', 'Spécialité du cœur et vaisseaux', '+221 33 800 01 01', 'cardio@omega.sn'),
            ('DEP-PED',  'Pédiatrie',   'Médecine des enfants (0-18 ans)', '+221 33 800 01 02', 'pediatrie@omega.sn'),
            ('DEP-URG',  'Urgences',    'Prise en charge urgente 24/7',    '+221 33 800 01 03', 'urgences@omega.sn'),
            ('DEP-MED',  'Médecine Générale', 'Consultations générales',    '+221 33 800 01 04', 'medecine@omega.sn'),
            ('DEP-OBS',  'Obstétrique', 'Suivi grossesse et accouchement', '+221 33 800 01 05', 'obstetrique@omega.sn'),
            ('DEP-CHIR', 'Chirurgie',   'Interventions chirurgicales',      '+221 33 800 01 06', 'chirurgie@omega.sn'),
            ('DEP-RAD',  'Radiologie',  'Imagerie médicale',                '+221 33 800 01 07', 'radio@omega.sn'),
            ('DEP-LAB',  'Laboratoire','Analyses biologiques',              '+221 33 800 01 08', 'labo@omega.sn'),
        ])

        # Salles
        c.executemany("""INSERT INTO salles (code, nom, site_id, departement_id, batiment, etage, type, capacite)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('A101', 'Consultation Cardio 1', 1, 1, 'A', 1, 'Consultation', 1),
            ('A102', 'Consultation Cardio 2', 1, 1, 'A', 1, 'Consultation', 1),
            ('B201', 'Chambre Pédiatrie 1',   1, 2, 'B', 2, 'Chambre',      2),
            ('B202', 'Chambre Pédiatrie 2',   1, 2, 'B', 2, 'Chambre',      2),
            ('C001', 'Urgences Box 1',        1, 3, 'C', 0, 'Urgence',      1),
            ('C002', 'Urgences Box 2',        1, 3, 'C', 0, 'Urgence',      1),
            ('D301', 'Bloc Opératoire 1',     1, 6, 'D', 3, 'Bloc',         1),
            ('D302', 'Bloc Opératoire 2',     1, 6, 'D', 3, 'Bloc',         1),
        ])

        # Médecins
        c.executemany("""INSERT INTO medecins (code, nom, prenom, specialite, num_ordre, telephone, email, departement_id, annees_experience, tarif_consultation, biographie, langues)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('MED-001', 'Diallo', 'Aminata', 'Cardiologie', 'ORD-SN-2015-001', '+221 77 123 45 67', 'a.diallo@omega.sn', 1, 12, 25000, 'Cardiologue, ancienne chef de clinique CHU Fann', 'Français, Wolof, Anglais'),
            ('MED-002', 'Ndiaye', 'Ibrahima', 'Pédiatrie', 'ORD-SN-2017-045', '+221 77 234 56 78', 'i.ndiaye@omega.sn', 2, 8, 20000, 'Pédiatre, spécialiste néonatalogie', 'Français, Wolof'),
            ('MED-003', 'Sow', 'Fatou', 'Médecine Générale', 'ORD-SN-2018-102', '+221 77 345 67 89', 'f.sow@omega.sn', 4, 6, 15000, 'Médecin généraliste', 'Français, Wolof, Peul'),
            ('MED-004', 'Ba', 'Moussa', 'Urgences', 'ORD-SN-2016-078', '+221 77 456 78 90', 'm.ba@omega.sn', 3, 10, 18000, 'Urgentiste, SAMU Dakar', 'Français, Wolof, Anglais'),
            ('MED-005', 'Fall', 'Khady', 'Obstétrique', 'ORD-SN-2019-201', '+221 77 567 89 01', 'k.fall@omega.sn', 5, 5, 20000, 'Gynécologue-obstétricienne', 'Français, Wolof'),
        ])

        # Personnel
        c.executemany("""INSERT INTO personnel (code, nom, prenom, fonction, telephone, email, departement_id, date_embauche)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('PER-001', 'Sarr', 'Awa', 'Infirmière Chef', '+221 78 111 22 33', 'a.sarr@omega.sn', 1, '2020-03-15'),
            ('PER-002', 'Kane', 'Modou', 'Infirmier', '+221 78 222 33 44', 'm.kane@omega.sn', 2, '2021-06-01'),
            ('PER-003', 'Diop', 'Sokhna', 'Infirmière', '+221 78 333 44 55', 's.diop@omega.sn', 3, '2022-01-10'),
            ('PER-004', 'Cisse', 'Oumar', 'Aide-soignant', '+221 78 444 55 66', 'o.cisse@omega.sn', 2, '2023-02-20'),
            ('PER-005', 'Gueye', 'Mariama', 'Secrétaire médicale', '+221 78 555 66 77', 'm.gueye@omega.sn', 4, '2021-09-05'),
        ])

        # CIM-10 (Sénégal : palu, IRA, diarrhée, tuberculose, hypertension, diabète...)
        c.executemany("""INSERT INTO cim10 (code, libelle, categorie, chapitre)
            VALUES (?, ?, ?, ?)""", [
            ('A09',  'Diarrhée et gastro-entérite', 'Infections', 'I'),
            ('B50',  'Paludisme à Plasmodium falciparum', 'Paludisme', 'I'),
            ('B54',  'Paludisme, sans précision', 'Paludisme', 'I'),
            ('A15',  'Tuberculose respiratoire', 'Tuberculose', 'I'),
            ('A16',  'Tuberculose respiratoire non confirmée', 'Tuberculose', 'I'),
            ('J06',  'Infection aiguë voies respiratoires supérieures', 'Respiratoire', 'X'),
            ('J18',  'Pneumonie, micro-organisme non précisé', 'Respiratoire', 'X'),
            ('J45',  'Asthme', 'Respiratoire', 'X'),
            ('I10',  'Hypertension essentielle (primaire)', 'Cardiovasculaire', 'IX'),
            ('I20',  'Angine de poitrine', 'Cardiovasculaire', 'IX'),
            ('I21',  'Infarctus aigu du myocarde', 'Cardiovasculaire', 'IX'),
            ('E11',  'Diabète sucré de type 2', 'Endocrinien', 'IV'),
            ('E10',  'Diabète sucré de type 1', 'Endocrinien', 'IV'),
            ('K30',  'Dyspepsie', 'Digestif', 'XI'),
            ('K29',  'Gastrite et duodénite', 'Digestif', 'XI'),
            ('N39',  'Troubles urinaires', 'Urinaire', 'XIV'),
            ('N10',  'Néphrite tubulo-interstitielle aiguë', 'Urinaire', 'XIV'),
            ('O80',  'Accouchement unique spontané', 'Obstétrique', 'XV'),
            ('Z34',  'Surveillance grossesse normale', 'Obstétrique', 'XXI'),
            ('M54',  'Dorsalgie', 'Ostéo-articulaire', 'XIII'),
            ('M79',  'Autres atteintes des tissus mous', 'Ostéo-articulaire', 'XIII'),
            ('H10',  'Conjonctivite', 'Ophtalmologie', 'VII'),
            ('H66',  'Otite moyenne suppurée', 'ORL', 'VIII'),
            ('L30',  'Autres dermatites', 'Dermatologie', 'XII'),
            ('F32',  'Épisode dépressif', 'Psychiatrique', 'V'),
            ('R50',  'Fièvre d\'origine inconnue', 'Symptôme', 'XVIII'),
            ('R05',  'Toux', 'Symptôme', 'XVIII'),
            ('R10',  'Douleur abdominale', 'Symptôme', 'XVIII'),
            ('Z00',  'Examen médical général', 'Prévention', 'XXI'),
            ('Z23',  'Vaccination', 'Prévention', 'XXI'),
        ])

        # Patients
        now = datetime.now()
        c.executemany("""INSERT INTO patients (numero_dossier, carte_medicale, nom, prenom, date_naissance, lieu_naissance, sexe, groupe_sanguin, telephone, telephone_urgence, email, adresse, ville, region, profession, situation_matrimoniale, allergies, antecedents_medicaux, assurance, numero_assurance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('PAT-2026-0001', 'CM-001', 'Sarr', 'Aliou', '1985-05-15', 'Dakar', 'M', 'O+', '+221 77 111 22 33', '+221 77 111 22 34', 'a.sarr@email.sn', 'Sacré-Cœur 3', 'Dakar', 'Dakar', 'Ingénieur', 'Marié', 'Pénicilline', 'Hypertension depuis 2019', 'IPM', 'IPM-2020-1234'),
            ('PAT-2026-0002', 'CM-002', 'Ba', 'Aissatou', '1992-03-22', 'Thiès', 'F', 'A+', '+221 77 222 33 44', '+221 77 222 33 45', 'a.ba@email.sn', 'Médina', 'Dakar', 'Dakar', 'Commerçante', 'Célibataire', 'Aucune', 'Asthme léger', 'SUNU', 'SUNU-2021-5678'),
            ('PAT-2026-0003', 'CM-003', 'Kane', 'Moussa', '1978-11-10', 'Kaolack', 'M', 'B+', '+221 77 333 44 55', '+221 77 333 44 56', 'm.kane@email.sn', 'Point E', 'Dakar', 'Dakar', 'Enseignant', 'Marié', 'Aspirine', 'Diabète type 2', 'Aucune', ''),
            ('PAT-2026-0004', 'CM-004', 'Diop', 'Fatou', '2018-07-08', 'Dakar', 'F', 'O-', '+221 77 444 55 66', '+221 77 444 55 67', 'f.diop.parent@email.sn', 'Yoff', 'Dakar', 'Dakar', 'Élève', 'Célibataire', 'Arachides', 'Aucun', 'Mutuelles', 'MUT-2024-9012'),
            ('PAT-2026-0005', 'CM-005', 'Ndiaye', 'Ousmane', '1965-12-30', 'Saint-Louis', 'M', 'AB+', '+221 77 555 66 77', '+221 77 555 66 78', 'o.ndiaye@email.sn', 'Almadies', 'Dakar', 'Dakar', 'Retraité', 'Marié', 'Aucune', 'Arthrose, cholestérol', 'IPM', 'IPM-2015-3456'),
        ])

        # Consultations
        c.executemany("""INSERT INTO consultations (numero, patient_id, medecin_id, departement_id, date_consultation, motif, temperature, tension, pouls, poids, taille, spo2, diagnostic_principal, code_cim10, conduite_tenue, cout, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('CON-2026-0001', 1, 1, 1, (now - timedelta(days=2)).isoformat(), 'Céphalées et vertiges', 37.2, '15/9', 82, 78.5, 1.78, 98, 'Hypertension artérielle', 'I10', 'Repos, régime hyposodé, traitement antihypertenseur', 25000, 'Terminé'),
            ('CON-2026-0002', 2, 3, 4, (now - timedelta(days=1)).isoformat(), 'Toux persistante', 38.1, '12/8', 88, 62.0, 1.65, 96, 'Infection respiratoire supérieure', 'J06', 'Antibiotique, repos, hydratation', 15000, 'Terminé'),
            ('CON-2026-0003', 4, 2, 2, now.isoformat(), 'Fièvre et vomissements', 39.2, '11/7', 110, 22.0, 1.15, 97, 'Paludisme', 'B50', 'Test rapide, antipaludique, hydratation', 20000, 'En cours'),
            ('CON-2026-0004', 3, 3, 4, now.isoformat(), 'Suivi diabète', 36.8, '14/9', 76, 88.0, 1.72, 99, 'Diabète type 2 - contrôle', 'E11', 'Bilan HbA1c, ajustement traitement', 15000, 'Terminé'),
        ])

        # Prescriptions
        c.executemany("""INSERT INTO prescriptions (consultation_id, medicament, dosage, posologie, duree, instructions)
            VALUES (?, ?, ?, ?, ?, ?)""", [
            (1, 'Amlodipine 5mg', '5mg', '1 comprimé/jour', '30 jours', 'Le matin à jeun'),
            (1, 'Aspirine 100mg', '100mg', '1 comprimé/jour', '30 jours', 'Le soir'),
            (2, 'Amoxicilline 500mg', '500mg', '3x/jour', '7 jours', 'Après les repas'),
            (3, 'Artéméther-Luméfantrine', '80/480mg', '2x/jour', '3 jours', 'Après les repas'),
            (3, 'Paracétamol pédiatrique', '250mg/5ml', 'Selon poids', '5 jours', 'Si fièvre > 38.5°C'),
            (4, 'Metformine 500mg', '500mg', '2x/jour', '90 jours', 'Après les repas'),
        ])

        # Hospitalisations
        c.executemany("""INSERT INTO hospitalisations (numero, patient_id, medecin_referent_id, salle_id, lit_numero, date_entree, motif, diagnostic, cout_journalier, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('HOS-2026-0001', 5, 1, 1, 'A101-1', (now - timedelta(days=3)).isoformat(), 'Douleur thoracique', 'Angine de poitrine', 50000, 'En cours'),
            ('HOS-2026-0002', 4, 2, 3, 'B201-1', now.isoformat(), 'Paludisme sévère', 'Paludisme grave', 35000, 'En cours'),
        ])

        # Factures
        c.executemany("""INSERT INTO factures (numero, patient_id, date_emission, montant_total, montant_paye, mode_paiement, statut, observations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('FAC-2026-0001', 1, (now - timedelta(days=2)).isoformat(), 25000, 25000, 'Espèces', 'Payé', 'Consultation cardio'),
            ('FAC-2026-0002', 2, (now - timedelta(days=1)).isoformat(), 15000, 15000, 'Wave', 'Payé', 'Consultation générale'),
            ('FAC-2026-0003', 4, now.isoformat(), 20000, 10000, 'Orange Money', 'Partiel', 'Paludisme enfant'),
            ('FAC-2026-0004', 3, now.isoformat(), 15000, 0, None, 'Impayé', 'Suivi diabète'),
        ])

        # Lignes facture
        c.executemany("""INSERT INTO lignes_facture (facture_id, designation, quantite, prix_unitaire, montant)
            VALUES (?, ?, ?, ?, ?)""", [
            (1, 'Consultation cardiologie', 1, 25000, 25000),
            (2, 'Consultation médecine générale', 1, 15000, 15000),
            (3, 'Consultation pédiatrie', 1, 20000, 20000),
            (4, 'Consultation médecine générale', 1, 15000, 15000),
        ])

        # Rendez-vous
        c.executemany("""INSERT INTO rendez_vous (patient_id, medecin_id, date_rdv, heure_rdv, motif, statut)
            VALUES (?, ?, ?, ?, ?, ?)""", [
            (1, 1, (now + timedelta(days=5)).date().isoformat(), '10:00', 'Contrôle tension', 'Programmé'),
            (2, 3, (now + timedelta(days=7)).date().isoformat(), '14:30', 'Suivi traitement', 'Programmé'),
            (3, 3, (now + timedelta(days=30)).date().isoformat(), '09:00', 'Bilan trimestriel', 'Programmé'),
            (5, 1, (now + timedelta(days=2)).date().isoformat(), '11:00', 'Contrôle post-hospitalisation', 'Programmé'),
        ])

        conn.commit()
        print("[INIT] ✅ Données de démonstration insérées")

    conn.close()
    print("[INIT] ✅ Base de données prête")


if __name__ == "__main__":
    init_db()
