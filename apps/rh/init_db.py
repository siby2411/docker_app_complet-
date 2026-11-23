"""
Base de données Gestion RH Omega
22 tables : départements, postes, employés, contrats, congés, absences,
paie, bulletins, pointages, formations, évaluations, recrutement, etc.
"""
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "/app/data/rh.db"


def init_db():
    os.makedirs("/app/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    c = conn.cursor()

    # ==================== 1. ENTREPRISES / SITES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        adresse TEXT,
        ville TEXT NOT NULL,
        region TEXT,
        telephone TEXT,
        email TEXT,
        responsable TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 2. DÉPARTEMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS departements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        parent_id INTEGER,
        responsable_id INTEGER,
        site_id INTEGER,
        budget_annuel REAL DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES departements(id),
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    # ==================== 3. POSTES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS postes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        intitule TEXT NOT NULL,
        description TEXT,
        departement_id INTEGER,
        categorie TEXT,
        niveau TEXT,
        salaire_min REAL DEFAULT 0,
        salaire_max REAL DEFAULT 0,
        competences TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (departement_id) REFERENCES departements(id)
    )""")

    # ==================== 4. EMPLOYÉS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS employes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        matricule TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        date_naissance TEXT NOT NULL,
        lieu_naissance TEXT,
        sexe TEXT NOT NULL,
        situation_matrimoniale TEXT,
        nombre_enfants INTEGER DEFAULT 0,
        nationalite TEXT DEFAULT 'Sénégalaise',
        cni TEXT UNIQUE,
        numero_css TEXT UNIQUE,
        numero_ipres TEXT UNIQUE,
        telephone TEXT NOT NULL,
        telephone_urgence TEXT,
        email TEXT,
        adresse TEXT,
        ville TEXT,
        region TEXT,
        poste_id INTEGER,
        departement_id INTEGER,
        site_id INTEGER,
        manager_id INTEGER,
        date_embauche TEXT NOT NULL,
        date_fin_contrat TEXT,
        type_contrat TEXT DEFAULT 'CDI',
        statut TEXT DEFAULT 'Actif',
        salaire_base REAL DEFAULT 0,
        prime_transport REAL DEFAULT 0,
        prime_logement REAL DEFAULT 0,
        prime_autre REAL DEFAULT 0,
        banque TEXT,
        rib TEXT,
        mode_paiement TEXT DEFAULT 'Virement',
        photo TEXT,
        cv_fichier TEXT,
        notes TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (poste_id) REFERENCES postes(id),
        FOREIGN KEY (departement_id) REFERENCES departements(id),
        FOREIGN KEY (site_id) REFERENCES sites(id),
        FOREIGN KEY (manager_id) REFERENCES employes(id)
    )""")

    # ==================== 5. CONTRATS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS contrats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        employe_id INTEGER NOT NULL,
        type_contrat TEXT NOT NULL,
        date_debut TEXT NOT NULL,
        date_fin TEXT,
        duree_mois INTEGER,
        salaire_mensuel REAL NOT NULL,
        periode_essai_mois INTEGER DEFAULT 0,
        statut TEXT DEFAULT 'Actif',
        document_fichier TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== 6. TYPES DE CONGÉS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS types_conges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        jours_par_an INTEGER DEFAULT 0,
        paye INTEGER DEFAULT 1,
        justificatif_requis INTEGER DEFAULT 0,
        couleur TEXT,
        actif INTEGER DEFAULT 1
    )""")

    # ==================== 7. CONGÉS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS conges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        employe_id INTEGER NOT NULL,
        type_conge_id INTEGER NOT NULL,
        date_debut TEXT NOT NULL,
        date_fin TEXT NOT NULL,
        nb_jours REAL NOT NULL,
        motif TEXT,
        statut TEXT DEFAULT 'En attente',
        valideur_id INTEGER,
        date_validation TEXT,
        commentaire_validation TEXT,
        justificatif_fichier TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id),
        FOREIGN KEY (type_conge_id) REFERENCES types_conges(id),
        FOREIGN KEY (valideur_id) REFERENCES employes(id)
    )""")

    # ==================== 8. ABSENCES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS absences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER NOT NULL,
        date_absence TEXT NOT NULL,
        type_absence TEXT NOT NULL,
        duree_heures REAL,
        motif TEXT,
        justifie INTEGER DEFAULT 0,
        justificatif_fichier TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== 9. POINTAGES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS pointages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER NOT NULL,
        date_pointage TEXT NOT NULL,
        heure_arrivee TEXT,
        heure_depart TEXT,
        heures_travaillees REAL DEFAULT 0,
        heures_sup REAL DEFAULT 0,
        retard_minutes INTEGER DEFAULT 0,
        mode_pointage TEXT DEFAULT 'QR',
        localisation TEXT,
        ip TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== 10. RUBRIQUES PAIE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS rubriques_paie (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        libelle TEXT NOT NULL,
        type TEXT NOT NULL,
        mode_calcul TEXT,
        taux REAL DEFAULT 0,
        plafond REAL DEFAULT 0,
        base_legale TEXT,
        ordre INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1
    )""")

    # ==================== 11. BULLETINS PAIE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS bulletins_paie (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        employe_id INTEGER NOT NULL,
        mois INTEGER NOT NULL,
        annee INTEGER NOT NULL,
        date_emission TEXT NOT NULL,
        salaire_brut REAL DEFAULT 0,
        primes_total REAL DEFAULT 0,
        heures_sup_total REAL DEFAULT 0,
        cotisations_salariales REAL DEFAULT 0,
        cotisations_patronales REAL DEFAULT 0,
        irpp REAL DEFAULT 0,
        cfce REAL DEFAULT 0,
        total_retenues REAL DEFAULT 0,
        salaire_net REAL DEFAULT 0,
        cout_employeur REAL DEFAULT 0,
        jours_travailles INTEGER DEFAULT 0,
        jours_conges INTEGER DEFAULT 0,
        statut TEXT DEFAULT 'Brouillon',
        mode_paiement TEXT,
        date_paiement TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== 12. LIGNES BULLETINS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS bulletins_lignes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bulletin_id INTEGER NOT NULL,
        rubrique_id INTEGER,
        libelle TEXT NOT NULL,
        type TEXT NOT NULL,
        base REAL DEFAULT 0,
        taux REAL DEFAULT 0,
        montant REAL NOT NULL,
        ordre INTEGER DEFAULT 0,
        FOREIGN KEY (bulletin_id) REFERENCES bulletins_paie(id),
        FOREIGN KEY (rubrique_id) REFERENCES rubriques_paie(id)
    )""")

    # ==================== 13. FORMATIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS formations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        titre TEXT NOT NULL,
        description TEXT,
        categorie TEXT,
        organisme TEXT,
        formateur TEXT,
        date_debut TEXT,
        date_fin TEXT,
        duree_heures INTEGER,
        cout_total REAL DEFAULT 0,
        lieu TEXT,
        nb_places INTEGER,
        statut TEXT DEFAULT 'Planifiée',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 14. INSCRIPTIONS FORMATIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS formations_employes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        formation_id INTEGER NOT NULL,
        employe_id INTEGER NOT NULL,
        statut TEXT DEFAULT 'Inscrit',
        note REAL,
        appreciation TEXT,
        certificat_fichier TEXT,
        cout_individuel REAL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (formation_id) REFERENCES formations(id),
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== 15. ÉVALUATIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        employe_id INTEGER NOT NULL,
        evaluateur_id INTEGER,
        periode TEXT NOT NULL,
        annee INTEGER NOT NULL,
        date_evaluation TEXT NOT NULL,
        note_globale REAL DEFAULT 0,
        note_objectifs REAL DEFAULT 0,
        note_competences REAL DEFAULT 0,
        note_comportement REAL DEFAULT 0,
        points_forts TEXT,
        points_ameliorer TEXT,
        objectifs_prochaine_periode TEXT,
        commentaire_employe TEXT,
        statut TEXT DEFAULT 'Brouillon',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id),
        FOREIGN KEY (evaluateur_id) REFERENCES employes(id)
    )""")

    # ==================== 16. CRITÈRES ÉVALUATION ====================
    c.execute("""CREATE TABLE IF NOT EXISTS evaluation_criteres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        evaluation_id INTEGER NOT NULL,
        critere TEXT NOT NULL,
        categorie TEXT,
        note REAL DEFAULT 0,
        poids REAL DEFAULT 1,
        commentaire TEXT,
        FOREIGN KEY (evaluation_id) REFERENCES evaluations(id)
    )""")

    # ==================== 17. RECRUTEMENT OFFRES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS offres_emploi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        titre TEXT NOT NULL,
        description TEXT,
        poste_id INTEGER,
        departement_id INTEGER,
        type_contrat TEXT,
        lieu TEXT,
        salaire_min REAL,
        salaire_max REAL,
        date_publication TEXT NOT NULL,
        date_cloture TEXT,
        nb_postes INTEGER DEFAULT 1,
        statut TEXT DEFAULT 'Ouverte',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (poste_id) REFERENCES postes(id),
        FOREIGN KEY (departement_id) REFERENCES departements(id)
    )""")

    # ==================== 18. CANDIDATS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS candidats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offre_id INTEGER NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        email TEXT,
        telephone TEXT NOT NULL,
        date_naissance TEXT,
        adresse TEXT,
        cv_fichier TEXT,
        lettre_fichier TEXT,
        diplome TEXT,
        experience_annees INTEGER DEFAULT 0,
        pretentions_salariales REAL,
        statut TEXT DEFAULT 'Nouveau',
        source TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (offre_id) REFERENCES offres_emploi(id)
    )""")

    # ==================== 19. ENTRETIENS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS entretiens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidat_id INTEGER NOT NULL,
        type_entretien TEXT,
        date_entretien TEXT NOT NULL,
        duree_minutes INTEGER DEFAULT 60,
        interviewers TEXT,
        lieu TEXT,
        note REAL,
        appreciation TEXT,
        decision TEXT DEFAULT 'En attente',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidat_id) REFERENCES candidats(id)
    )""")

    # ==================== 20. DOCUMENTS RH ====================
    c.execute("""CREATE TABLE IF NOT EXISTS documents_rh (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER,
        type_document TEXT NOT NULL,
        titre TEXT NOT NULL,
        reference TEXT,
        date_document TEXT,
        date_expiration TEXT,
        fichier TEXT,
        taille_ko REAL DEFAULT 0,
        mime_type TEXT,
        statut TEXT DEFAULT 'Valide',
        notes TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== 21. AUDIT LOG ====================
    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        ip TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 22. PARAMÈTRES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS parametres (
        cle TEXT PRIMARY KEY,
        valeur TEXT,
        description TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()

    # ==================== SEED ====================
    c.execute("SELECT COUNT(*) FROM sites")
    if c.fetchone()[0] == 0:
        print("[INIT] Insertion des données de démonstration...")

        # SITES
        c.executemany("""INSERT INTO sites (code, nom, adresse, ville, region, telephone, email, responsable)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('SITE-DK', 'Siège Dakar', 'Avenue Cheikh Anta Diop, Fann', 'Dakar', 'Dakar', '+221 33 800 00 01', 'rh.dakar@omega.sn', 'Direction Générale'),
            ('SITE-TH', 'Agence Thiès', 'Route de Dakar, Quartier Escale', 'Thiès', 'Thiès', '+221 33 800 00 02', 'rh.thies@omega.sn', 'Direction Régionale'),
        ])

        # DÉPARTEMENTS
        c.executemany("""INSERT INTO departements (code, nom, description, site_id, budget_annuel)
            VALUES (?, ?, ?, ?, ?)""", [
            ('DG',    'Direction Générale', 'Direction et stratégie', 1, 50000000),
            ('FIN',   'Finance & Comptabilité', 'Gestion financière', 1, 35000000),
            ('RH',    'Ressources Humaines', 'Gestion du personnel', 1, 25000000),
            ('COM',   'Commercial & Marketing', 'Ventes et marketing', 1, 45000000),
            ('TECH',  'Technique & IT', 'Support technique et informatique', 1, 60000000),
            ('LOG',   'Logistique', 'Approvisionnement et livraison', 2, 30000000),
            ('PROD',  'Production', 'Production et fabrication', 2, 80000000),
            ('QUA',   'Qualité & HSE', 'Contrôle qualité et sécurité', 2, 20000000),
        ])

        # POSTES
        c.executemany("""INSERT INTO postes (code, intitule, description, departement_id, categorie, niveau, salaire_min, salaire_max)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('P001', 'Directeur Général', 'Direction de l\'entreprise', 1, 'Direction', 'A', 1500000, 3000000),
            ('P002', 'Directeur Financier', 'Direction financière', 2, 'Direction', 'A', 1000000, 2000000),
            ('P003', 'Comptable', 'Comptabilité générale', 2, 'Cadre', 'B', 400000, 700000),
            ('P004', 'Responsable RH', 'Gestion RH', 3, 'Cadre', 'B', 500000, 900000),
            ('P005', 'Chargé RH', 'Administration du personnel', 3, 'Agent', 'C', 250000, 400000),
            ('P006', 'Directeur Commercial', 'Direction commerciale', 4, 'Direction', 'A', 900000, 1800000),
            ('P007', 'Commercial', 'Vente et prospection', 4, 'Agent', 'C', 200000, 350000),
            ('P008', 'Directeur Technique', 'Direction technique', 5, 'Direction', 'A', 900000, 1800000),
            ('P009', 'Développeur', 'Développement logiciel', 5, 'Cadre', 'B', 400000, 900000),
            ('P010', 'Technicien Support', 'Support informatique', 5, 'Agent', 'C', 200000, 350000),
            ('P011', 'Magasinier', 'Gestion entrepôt', 6, 'Agent', 'C', 150000, 250000),
            ('P012', 'Chauffeur', 'Livraison', 6, 'Agent', 'D', 130000, 200000),
            ('P013', 'Chef Production', 'Encadrement production', 7, 'Cadre', 'B', 500000, 900000),
            ('P014', 'Ouvrier', 'Production', 7, 'Agent', 'D', 130000, 200000),
            ('P015', 'Responsable Qualité', 'Contrôle qualité', 8, 'Cadre', 'B', 400000, 700000),
        ])

        # TYPES CONGÉS
        c.executemany("""INSERT INTO types_conges (code, nom, description, jours_par_an, paye, justificatif_requis, couleur)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", [
            ('CA',       'Congé annuel', 'Congé payé annuel', 30, 1, 0, '#10b981'),
            ('MAL',      'Maladie', 'Arrêt maladie', 15, 1, 1, '#dc2626'),
            ('MAT',      'Maternité', 'Congé maternité', 98, 1, 1, '#ec4899'),
            ('PAT',      'Paternité', 'Congé paternité', 3, 1, 1, '#3b82f6'),
            ('MARIAGE',  'Mariage', 'Mariage employé', 3, 1, 1, '#a855f7'),
            ('DECES',    'Décès', 'Décès proche', 3, 1, 1, '#64748b'),
            ('NAISS',    'Naissance', 'Naissance enfant', 1, 1, 1, '#f59e0b'),
            ('SANS_SOLDE', 'Sans solde', 'Congé non payé', 0, 0, 0, '#94a3b8'),
            ('EXCEPT',   'Exceptionnel', 'Événement exceptionnel', 3, 1, 1, '#f97316'),
        ])

        # RUBRIQUES PAIE (Conformes Sénégal)
        c.executemany("""INSERT INTO rubriques_paie (code, libelle, type, mode_calcul, taux, plafond, base_legale, ordre)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [
            # Gains
            ('SAL_BASE',  'Salaire de base',          'Gain',           'Fixe',          0,    0,        '', 1),
            ('PR_TRANS',  'Prime de transport',        'Gain',           'Fixe',          0,    0,        '', 2),
            ('PR_LOGE',   'Prime de logement',         'Gain',           'Fixe',          0,    0,        '', 3),
            ('PR_ANCIEN', 'Prime d\'ancienneté',      'Gain',           'Pourcentage',   2,    0,        '', 4),
            ('PR_AUTRE',  'Autres primes',             'Gain',           'Fixe',          0,    0,        '', 5),
            ('H_SUP',     'Heures supplémentaires',   'Gain',           'Fixe',          0,    0,        '', 6),
            # Cotisations salariales
            ('IPRES_SAL', 'IPRES salariale',          'Cotisation Sal', 'Pourcentage',   5.6,  432000,   'Loi 75-50', 10),
            ('CSS_SAL',   'CSS salariale',            'Cotisation Sal', 'Pourcentage',   3.0,  63000,    'Loi 75-50', 11),
            ('IRPP',      'IRPP',                     'Cotisation Sal', 'Bareme',        0,    0,        'CGI Sénégal', 12),
            ('CFCE_SAL',  'CFCE salariale',           'Cotisation Sal', 'Fixe',          0,    0,        'CGI Sénégal', 13),
            # Cotisations patronales
            ('IPRES_PAT', 'IPRES patronale',          'Cotisation Pat', 'Pourcentage',   8.4,  432000,   'Loi 75-50', 20),
            ('CSS_PAT',   'CSS patronale',            'Cotisation Pat', 'Pourcentage',   9.0,  63000,    'Loi 75-50', 21),
            ('CFCE_PAT',  'CFCE patronale',           'Cotisation Pat', 'Pourcentage',   3.0,  0,        'CGI Sénégal', 22),
            ('FNP',       'Fonds National de Prévoyance', 'Cotisation Pat', 'Pourcentage', 2.0, 0,       'Loi 75-50', 23),
            # Retenues
            ('AVANCE',    'Avance sur salaire',       'Retenue',        'Fixe',          0,    0,        '', 30),
            ('PRET',      'Remboursement prêt',       'Retenue',        'Fixe',          0,    0,        '', 31),
            ('AUTRE_RET', 'Autres retenues',          'Retenue',        'Fixe',          0,    0,        '', 32),
        ])

        # EMPLOYÉS (30 employés)
        employes = []
        noms_prenoms = [
            ('Diallo', 'Mamadou', 'M'), ('Ndiaye', 'Fatou', 'F'), ('Fall', 'Ibrahima', 'M'),
            ('Sow', 'Aminata', 'F'), ('Ba', 'Ousmane', 'M'), ('Kane', 'Khady', 'F'),
            ('Sarr', 'Aliou', 'M'), ('Diop', 'Aissatou', 'F'), ('Gueye', 'Moussa', 'M'),
            ('Cisse', 'Mariama', 'F'), ('Sy', 'Modou', 'M'), ('Toure', 'Rokhaya', 'F'),
            ('Camara', 'Souleymane', 'M'), ('Barry', 'Binta', 'F'), ('Mendy', 'Lamine', 'M'),
            ('Faye', 'Adama', 'F'), ('Thiam', 'Abdoulaye', 'M'), ('Ndour', 'Ndèye', 'F'),
            ('Samb', 'Cheikh', 'M'), ('Dieng', 'Maimouna', 'F'), ('Ka', 'Saliou', 'M'),
            ('Diallo', 'Bintou', 'F'), ('Sane', 'Lassana', 'M'), ('Sagna', 'Awa', 'F'),
            ('Badji', 'Malick', 'M'), ('Manga', 'Coumba', 'F'), ('Mané', 'Alioune', 'M'),
            ('Coly', 'Aissatou', 'F'), ('Tine', 'Serigne', 'M'), ('Gomis', 'Marie', 'F'),
        ]

        for i, (nom, prenom, sexe) in enumerate(noms_prenoms, 1):
            matricule = f"EMP-2026-{i:04d}"
            date_naissance = (datetime.now() - timedelta(days=365 * (25 + i % 20))).date().isoformat()
            date_embauche = (datetime.now() - timedelta(days=365 * (i % 10))).date().isoformat()

            # Attribution poste/département
            poste_map = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10}
            poste_id = poste_map.get(i, (i % 15) + 1)
            dept_map = {1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 4, 7: 4, 8: 5, 9: 5, 10: 5}
            dept_id = dept_map.get(i, (i % 8) + 1)

            salaire = 200000 + (i * 25000) % 800000

            employes.append((
                matricule, nom, prenom, date_naissance, 'Dakar', sexe,
                'Marié(e)' if i % 3 == 0 else 'Célibataire', i % 4,
                'Sénégalaise', f"CNI{i:010d}", f"CSS{i:08d}", f"IPRES{i:08d}",
                f"+221 77 {i:03d} {i*2:02d} {i*3:02d}", f"+221 78 {i:03d} {i:02d} {i:02d}",
                f"{prenom.lower()}.{nom.lower()}@omega.sn",
                f"Villa N°{i}, Cité Keur Gorgui", 'Dakar', 'Dakar',
                poste_id, dept_id, 1, None,
                date_embauche, None, 'CDI' if i % 5 != 0 else 'CDD', 'Actif',
                salaire, 25000, 50000, 0,
                'CBAO', f"SN08CB0100{i:010d}", 'Virement',
                None, None, None, 1
            ))

        c.executemany("""INSERT INTO employes
            (matricule, nom, prenom, date_naissance, lieu_naissance, sexe,
             situation_matrimoniale, nombre_enfants, nationalite,
             cni, numero_css, numero_ipres,
             telephone, telephone_urgence, email, adresse, ville, region,
             poste_id, departement_id, site_id, manager_id,
             date_embauche, date_fin_contrat, type_contrat, statut,
             salaire_base, prime_transport, prime_logement, prime_autre,
             banque, rib, mode_paiement, photo, cv_fichier, notes, actif)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", employes)

        # CONTRATS pour les employés
        contrats = []
        for i in range(1, 31):
            contrats.append((
                f"CTR-2026-{i:04d}", i,
                'CDI' if i % 5 != 0 else 'CDD',
                (datetime.now() - timedelta(days=365 * (i % 10))).date().isoformat(),
                None if i % 5 != 0 else (datetime.now() + timedelta(days=180)).date().isoformat(),
                None if i % 5 != 0 else 12,
                200000 + (i * 25000) % 800000,
                3, 'Actif', None, None
            ))
        c.executemany("""INSERT INTO contrats
            (numero, employe_id, type_contrat, date_debut, date_fin, duree_mois,
             salaire_mensuel, periode_essai_mois, statut, document_fichier, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", contrats)

        # PARAMÈTRES
        c.executemany("INSERT INTO parametres (cle, valeur, description) VALUES (?, ?, ?)", [
            ('entreprise_nom', 'OMEGA INFORMATIQUE', 'Nom de l\'entreprise'),
            ('entreprise_nif', 'SN-123456789', 'NIF'),
            ('taux_ipres_sal', '5.6', 'Taux IPRES salarial (%)'),
            ('taux_ipres_pat', '8.4', 'Taux IPRES patronal (%)'),
            ('taux_css_sal', '3.0', 'Taux CSS salarial (%)'),
            ('taux_css_pat', '9.0', 'Taux CSS patronal (%)'),
            ('taux_cfce', '3.0', 'Taux CFCE (%)'),
            ('plafond_css', '63000', 'Plafond CSS (FCFA/mois)'),
            ('plafond_ipres', '432000', 'Plafond IPRES (FCFA/mois)'),
            ('smig', '64325', 'SMIG Sénégal (FCFA)'),
            ('devise', 'FCFA', 'Devise'),
            ('jours_conges_annuels', '30', 'Jours de congés annuels'),
        ])

        conn.commit()
        print("[INIT] ✅ Données de démonstration insérées")

    conn.close()
    print("[INIT] ✅ Base de données RH prête")


if __name__ == "__main__":
    init_db()
