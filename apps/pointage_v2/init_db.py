"""
Omega Pointage V2 — Initialisation base de données
Conforme SYSCOHADA UEMOA — Calcul heures, congés, paie
"""
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "/app/data/pointage_v2.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    print(f"[INIT] Base : {DB_PATH}")
    conn = get_conn()
    c = conn.cursor()

    # ==================== SITES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        adresse TEXT,
        ville TEXT,
        pays TEXT DEFAULT 'Sénégal',
        telephone TEXT,
        email TEXT,
        responsable_id INTEGER,
        fuseau_horaire TEXT DEFAULT 'Africa/Dakar',
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== DEPARTEMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS departements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        responsable_id INTEGER,
        site_id INTEGER,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    # ==================== POSTES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS postes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        departement_id INTEGER,
        categorie TEXT,
        salaire_base INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (departement_id) REFERENCES departements(id)
    )""")

    # ==================== EMPLOYES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS employes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        matricule TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        date_naissance TEXT,
        sexe TEXT,
        telephone TEXT,
        email TEXT,
        adresse TEXT,
        photo_path TEXT,
        empreinte_id TEXT,
        numero_cni TEXT,
        numero_cnss TEXT,
        situation_familiale TEXT,
        nombre_enfants INTEGER DEFAULT 0,
        poste_id INTEGER,
        departement_id INTEGER,
        site_id INTEGER,
        date_embauche TEXT,
        date_fin TEXT,
        type_contrat TEXT,
        salaire_base INTEGER DEFAULT 0,
        mode_paiement TEXT,
        rib TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (poste_id) REFERENCES postes(id),
        FOREIGN KEY (departement_id) REFERENCES departements(id),
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    # ==================== SHIFT TYPES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS shift_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        heure_debut TEXT,
        heure_fin TEXT,
        duree_heures REAL,
        couleur TEXT DEFAULT '#06b6d4',
        pause_minutes INTEGER DEFAULT 0,
        majoration REAL DEFAULT 1.0,
        actif INTEGER DEFAULT 1
    )""")

    # ==================== PLANNINGS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS plannings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER NOT NULL,
        date_planning TEXT NOT NULL,
        shift_type_id INTEGER,
        heure_debut_prevue TEXT,
        heure_fin_prevue TEXT,
        site_id INTEGER,
        statut TEXT DEFAULT 'Prévu',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id),
        FOREIGN KEY (shift_type_id) REFERENCES shift_types(id)
    )""")

    # ==================== POINTAGES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS pointages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER NOT NULL,
        date_pointage TEXT NOT NULL,
        heure_entree TEXT,
        heure_sortie TEXT,
        type_pointage TEXT DEFAULT 'Normal',
        terminal TEXT,
        ip_source TEXT,
        latitude REAL,
        longitude REAL,
        photo_path TEXT,
        mode TEXT DEFAULT 'Manuel',
        duree_minutes INTEGER,
        heures_travaillees REAL,
        heures_sup REAL DEFAULT 0,
        statut TEXT DEFAULT 'Normal',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    c.execute("CREATE INDEX IF NOT EXISTS idx_pointage_emp_date ON pointages(employe_id, date_pointage)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pointage_date ON pointages(date_pointage)")

    # ==================== ANOMALIES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS anomalies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER NOT NULL,
        type_anomalie TEXT NOT NULL,
        date_anomalie TEXT NOT NULL,
        gravite TEXT DEFAULT 'Normale',
        details TEXT,
        statut TEXT DEFAULT 'Ouverte',
        justificatif_id INTEGER,
        traitee_par INTEGER,
        date_traitement TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== TYPES DE CONGES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS types_conges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        jours_par_an INTEGER DEFAULT 0,
        paye INTEGER DEFAULT 1,
        couleur TEXT DEFAULT '#10b981',
        actif INTEGER DEFAULT 1
    )""")

    # ==================== CONGES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS conges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER NOT NULL,
        type_conge_id INTEGER,
        date_debut TEXT NOT NULL,
        date_fin TEXT NOT NULL,
        nb_jours REAL,
        motif TEXT,
        statut TEXT DEFAULT 'En attente',
        valide_par INTEGER,
        date_validation TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id),
        FOREIGN KEY (type_conge_id) REFERENCES types_conges(id)
    )""")

    # ==================== ABSENCES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS absences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER NOT NULL,
        date_absence TEXT NOT NULL,
        type_absence TEXT,
        duree_heures REAL,
        motif TEXT,
        justifie INTEGER DEFAULT 0,
        justificatif_path TEXT,
        statut TEXT DEFAULT 'Non justifiée',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== HEURES SUPPLEMENTAIRES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS heures_sup (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER NOT NULL,
        date_hs TEXT NOT NULL,
        nb_heures REAL NOT NULL,
        taux_majoration REAL DEFAULT 1.25,
        motif TEXT,
        statut TEXT DEFAULT 'En attente',
        valide_par INTEGER,
        date_validation TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== JOURS FERIES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS jours_feries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_ferie TEXT NOT NULL UNIQUE,
        nom TEXT NOT NULL,
        pays TEXT DEFAULT 'Sénégal',
        recurrent INTEGER DEFAULT 1,
        actif INTEGER DEFAULT 1
    )""")

    # ==================== TERMINAUX ====================
    c.execute("""CREATE TABLE IF NOT EXISTS terminaux (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type TEXT DEFAULT 'Biométrique',
        site_id INTEGER,
        adresse_ip TEXT,
        numero_serie TEXT,
        statut TEXT DEFAULT 'Actif',
        derniere_synchro TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    # ==================== PERIODES DE PAIE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS periodes_paie (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        date_debut TEXT NOT NULL,
        date_fin TEXT NOT NULL,
        statut TEXT DEFAULT 'Ouverte',
        date_cloture TEXT,
        cloture_par INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== RECAP HEURES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS recap_heures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER NOT NULL,
        periode_id INTEGER,
        heures_normales REAL DEFAULT 0,
        heures_sup_25 REAL DEFAULT 0,
        heures_sup_50 REAL DEFAULT 0,
        heures_nuit REAL DEFAULT 0,
        heures_ferie REAL DEFAULT 0,
        jours_travailles INTEGER DEFAULT 0,
        jours_absences INTEGER DEFAULT 0,
        retards_minutes INTEGER DEFAULT 0,
        montant_estime INTEGER DEFAULT 0,
        statut TEXT DEFAULT 'Brouillon',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id),
        FOREIGN KEY (periode_id) REFERENCES periodes_paie(id)
    )""")

    # ==================== PARAMETRES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS parametres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cle TEXT UNIQUE NOT NULL,
        valeur TEXT,
        type TEXT,
        description TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== UTILISATEURS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS utilisateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nom TEXT,
        prenom TEXT,
        email TEXT,
        telephone TEXT,
        role TEXT DEFAULT 'lecteur',
        employe_id INTEGER,
        actif INTEGER DEFAULT 1,
        dernier_login TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== AUDIT LOG ====================
    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        entity TEXT,
        entity_id INTEGER,
        details TEXT,
        ancienne_valeur TEXT,
        nouvelle_valeur TEXT,
        ip TEXT,
        user_agent TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)")

    # ==================== ALERTES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS alertes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_alerte TEXT NOT NULL,
        gravite TEXT DEFAULT 'Info',
        titre TEXT NOT NULL,
        message TEXT,
        employe_id INTEGER,
        statut TEXT DEFAULT 'Active',
        traitee_par INTEGER,
        date_traitement TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== NOTIFICATIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        destinataire_id INTEGER,
        type TEXT,
        titre TEXT,
        message TEXT,
        lu INTEGER DEFAULT 0,
        date_lecture TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== JUSTIFICATIFS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS justificatifs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER,
        type_justificatif TEXT,
        date_debut TEXT,
        date_fin TEXT,
        motif TEXT,
        fichier_path TEXT,
        statut TEXT DEFAULT 'En attente',
        valide_par INTEGER,
        date_validation TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()

    # ==================== DONNEES DE DEMO ====================
    c.execute("SELECT COUNT(*) FROM sites")
    if c.fetchone()[0] == 0:
        print("[INIT] Insertion des données de démonstration...")
        _seed_data(c)
        conn.commit()

    conn.close()
    print(f"[INIT] ✅ Base prête : {DB_PATH}")


def _seed_data(c):
    """Insère les données de démonstration"""
    now = datetime.now().isoformat()
    year = datetime.now().year

    # ---- Sites ----
    c.execute("""INSERT INTO sites (code, nom, adresse, ville, telephone, email)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              ('SDK', 'Siège Dakar', 'Plateau, Avenue Léopold Sédar Senghor',
               'Dakar', '338210000', 'contact@omega-software.sn'))
    c.execute("""INSERT INTO sites (code, nom, adresse, ville, telephone, email)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              ('THS', 'Succursale Thiès', 'Quartier Escale',
               'Thiès', '339510000', 'thies@omega-software.sn'))
    c.execute("""INSERT INTO sites (code, nom, adresse, ville, telephone, email)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              ('SLO', 'Entrepôt Saint-Louis', 'Zone industrielle Nord',
               'Saint-Louis', '339610000', 'sl@omega-software.sn'))

    # ---- Départements ----
    deps = [
        ('DIR', 'Direction Générale', 'Direction et stratégie', 1),
        ('RH', 'Ressources Humaines', 'Gestion du personnel', 1),
        ('FIN', 'Finance & Comptabilité', 'Comptabilité, trésorerie', 1),
        ('TECH', 'Technique & IT', 'Support informatique', 1),
        ('COM', 'Commercial & Ventes', 'Force de vente', 1),
        ('LOG', 'Logistique', 'Entrepôt et livraisons', 3),
    ]
    for code, nom, desc, site_id in deps:
        c.execute("""INSERT INTO departements (code, nom, description, site_id)
                     VALUES (?, ?, ?, ?)""", (code, nom, desc, site_id))

    # ---- Postes ----
    postes = [
        ('DG', 'Directeur Général', 1, 'Cadre supérieur', 1500000),
        ('DRH', 'Directeur RH', 2, 'Cadre', 900000),
        ('CPT', 'Comptable', 3, 'Employé qualifié', 450000),
        ('DEV', 'Développeur', 4, 'Cadre', 600000),
        ('TECH', 'Technicien', 4, 'Employé', 350000),
        ('COM', 'Commercial', 5, 'Employé', 300000),
        ('MAG', 'Magasinier', 6, 'Employé', 250000),
        ('SEC', 'Secrétaire', 2, 'Employé', 250000),
        ('GAR', 'Agent de sécurité', 1, 'Ouvrier', 180000),
        ('CHF', 'Chauffeur', 6, 'Ouvrier', 200000),
    ]
    for code, nom, dep_id, cat, sal in postes:
        c.execute("""INSERT INTO postes (code, nom, departement_id, categorie, salaire_base)
                     VALUES (?, ?, ?, ?, ?)""", (code, nom, dep_id, cat, sal))

    # ---- Types de shift ----
    shifts = [
        ('MATIN', 'Matin', '08:00', '16:00', 8.0, '#f59e0b', 60, 1.0),
        ('SOIR', 'Soir', '16:00', '00:00', 8.0, '#3b82f6', 60, 1.0),
        ('NUIT', 'Nuit', '00:00', '08:00', 8.0, '#6366f1', 60, 1.15),
        ('JOUR', 'Journée normale', '08:30', '17:30', 8.0, '#10b981', 60, 1.0),
        ('WEEK', 'Weekend', '09:00', '17:00', 8.0, '#ef4444', 60, 1.5),
    ]
    for code, nom, hd, hf, dur, col, pause, maj in shifts:
        c.execute("""INSERT INTO shift_types (code, nom, heure_debut, heure_fin, duree_heures, couleur, pause_minutes, majoration)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (code, nom, hd, hf, dur, col, pause, maj))

    # ---- Employés (30 employés) ----
    employes_data = [
        # (mat, nom, prenom, sexe, poste, dep, site, salaire)
        ('EMP0001', 'Diop', 'Mamadou', 'M', 1, 1, 1, 1500000),
        ('EMP0002', 'Ndiaye', 'Fatou', 'F', 2, 2, 1, 900000),
        ('EMP0003', 'Fall', 'Omar', 'M', 3, 3, 1, 450000),
        ('EMP0004', 'Sow', 'Aminata', 'F', 3, 3, 1, 450000),
        ('EMP0005', 'Ba', 'Ibrahima', 'M', 4, 4, 1, 600000),
        ('EMP0006', 'Diallo', 'Awa', 'F', 4, 4, 1, 600000),
        ('EMP0007', 'Sarr', 'Cheikh', 'M', 5, 4, 1, 350000),
        ('EMP0008', 'Kane', 'Mariama', 'F', 6, 5, 1, 300000),
        ('EMP0009', 'Gueye', 'Abdoulaye', 'M', 6, 5, 1, 300000),
        ('EMP0010', 'Camara', 'Kadidiatou', 'F', 7, 6, 3, 250000),
        ('EMP0011', 'Sylla', 'Moussa', 'M', 7, 6, 3, 250000),
        ('EMP0012', 'Cisse', 'Aissatou', 'F', 8, 2, 1, 250000),
        ('EMP0013', 'Barry', 'Alpha', 'M', 8, 2, 1, 250000),
        ('EMP0014', 'Toure', 'Marieme', 'F', 9, 1, 1, 180000),
        ('EMP0015', 'Beye', 'Saliou', 'M', 9, 1, 1, 180000),
        ('EMP0016', 'Mbaye', 'Cheikh', 'M', 10, 6, 3, 200000),
        ('EMP0017', 'Faye', 'Bineta', 'F', 3, 3, 2, 450000),
        ('EMP0018', 'Diagne', 'Lamine', 'M', 5, 4, 2, 350000),
        ('EMP0019', 'Sene', 'Fatoumata', 'F', 8, 2, 2, 250000),
        ('EMP0020', 'Badji', 'Moussa', 'M', 7, 6, 2, 250000),
        ('EMP0021', 'Diatta', 'Rokhaya', 'F', 3, 3, 2, 450000),
        ('EMP0022', 'Dieng', 'Ousmane', 'M', 6, 5, 2, 300000),
        ('EMP0023', 'Ka', 'Aminata', 'F', 8, 2, 1, 250000),
        ('EMP0024', 'Lo', 'Pape', 'M', 10, 6, 1, 200000),
        ('EMP0025', 'Niang', 'Awa', 'F', 9, 1, 1, 180000),
        ('EMP0026', 'Thiam', 'Moustapha', 'M', 4, 4, 1, 600000),
        ('EMP0027', 'Sagna', 'Coumba', 'F', 8, 2, 1, 250000),
        ('EMP0028', 'Mendy', 'Jean', 'M', 6, 5, 1, 300000),
        ('EMP0029', 'Coly', 'Aline', 'F', 7, 6, 3, 250000),
        ('EMP0030', 'Goudiaby', 'Saliou', 'M', 5, 4, 2, 350000),
    ]
    base_date = datetime(year - 2, 1, 15).isoformat()
    for i, (mat, nom, prenom, sexe, poste_id, dep_id, site_id, sal) in enumerate(employes_data, 1):
        c.execute("""INSERT INTO employes
            (matricule, nom, prenom, sexe, telephone, email, poste_id, departement_id, site_id,
             date_embauche, type_contrat, salaire_base, mode_paiement, actif)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (mat, nom, prenom, sexe,
             f"77{1000000 + i}", f"{prenom.lower()}.{nom.lower()}@omega-software.sn",
             poste_id, dep_id, site_id,
             base_date, 'CDI', sal, 'Virement'))

    # ---- Types de congés ----
    conges_types = [
        ('ANNUEL', 'Congé annuel', 30, 1, '#10b981'),
        ('MALADIE', 'Congé maladie', 15, 1, '#ef4444'),
        ('MATERNITE', 'Congé maternité', 98, 1, '#ec4899'),
        ('PATERNITE', 'Congé paternité', 3, 1, '#3b82f6'),
        ('EXCEPTION', 'Congé exceptionnel', 5, 1, '#f59e0b'),
        ('SANS_SOLDE', 'Congé sans solde', 0, 0, '#64748b'),
        ('FORMATION', 'Congé formation', 10, 1, '#8b5cf6'),
    ]
    for code, nom, jours, paye, col in conges_types:
        c.execute("""INSERT INTO types_conges (code, nom, jours_par_an, paye, couleur)
                     VALUES (?, ?, ?, ?, ?)""",
                  (code, nom, jours, paye, col))

    # ---- Jours fériés Sénégal ----
    feries = [
        (f'{year}-01-01', 'Jour de l\'An'),
        (f'{year}-04-04', 'Fête de l\'Indépendance'),
        (f'{year}-05-01', 'Fête du Travail'),
        (f'{year}-08-15', 'Assomption'),
        (f'{year}-11-01', 'Toussaint'),
        (f'{year}-12-25', 'Noël'),
        (f'{year}-04-10', 'Korité (approx.)'),
        (f'{year}-06-17', 'Tabaski (approx.)'),
        (f'{year}-09-16', 'Maouloud (approx.)'),
    ]
    for date_ferie, nom in feries:
        try:
            c.execute("""INSERT INTO jours_feries (date_ferie, nom, pays, recurrent)
                         VALUES (?, ?, 'Sénégal', 1)""", (date_ferie, nom))
        except sqlite3.IntegrityError:
            pass

    # ---- Terminaux ----
    terminaux = [
        ('TERM-001', 'Terminal entrée principale', 'Biométrique', 1, '192.168.1.100', 'BIO-001'),
        ('TERM-002', 'Terminal sortie principale', 'Biométrique', 1, '192.168.1.101', 'BIO-002'),
        ('TERM-003', 'Terminal entrepôt', 'Badge', 3, '192.168.1.102', 'BADGE-001'),
        ('TERM-004', 'Terminal mobile', 'Mobile', 1, '192.168.1.103', 'MOB-001'),
    ]
    for code, nom, typ, site_id, ip, sn in terminaux:
        c.execute("""INSERT INTO terminaux (code, nom, type, site_id, adresse_ip, numero_serie)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (code, nom, typ, site_id, ip, sn))

    # ---- Période de paie courante ----
    mois_courant = datetime.now().replace(day=1)
    fin_mois = (mois_courant + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    c.execute("""INSERT INTO periodes_paie (code, date_debut, date_fin, statut)
                 VALUES (?, ?, ?, 'Ouverte')""",
              (f'{year}-{mois_courant.month:02d}',
               mois_courant.date().isoformat(),
               fin_mois.date().isoformat()))

    # ---- Paramètres ----
    params = [
        ('tolerance_retard_min', '10', 'int', 'Tolérance retard en minutes'),
        ('retard_gravite_min', '60', 'int', 'Retard considéré grave au-delà (minutes)'),
        ('majoration_hs_25', '1.25', 'float', 'Majoration heures sup normales'),
        ('majoration_hs_50', '1.50', 'float', 'Majoration heures sup nuit/weekend'),
        ('majoration_nuit', '1.15', 'float', 'Majoration heures de nuit'),
        ('duree_journee_legale', '8', 'float', 'Durée légale journée (heures)'),
        ('duree_hebdo_legale', '40', 'float', 'Durée légale hebdomadaire (heures)'),
        ('jours_conges_annuel', '30', 'int', 'Jours de congés annuels'),
        ('pointage_auto_ferie', '1', 'int', 'Pointage auto les jours fériés'),
        ('heure_debut_nuit', '22:00', 'text', 'Heure début nuit'),
        ('heure_fin_nuit', '06:00', 'text', 'Heure fin nuit'),
    ]
    for cle, val, typ, desc in params:
        c.execute("""INSERT INTO parametres (cle, valeur, type, description)
                     VALUES (?, ?, ?, ?)""", (cle, val, typ, desc))

    # ---- Utilisateurs ----
    import hashlib
    def h(pwd):
        return hashlib.sha256(pwd.encode()).hexdigest()

    users = [
        ('admin', h('admin123'), 'Admin', 'Omega', 'admin@pointage.sn', 'admin', None),
        ('rh', h('rh123'), 'Diop', 'Fatou', 'rh@pointage.sn', 'rh', 2),
        ('chef', h('chef123'), 'Ndiaye', 'Omar', 'chef@pointage.sn', 'chef', 5),
        ('pointage', h('pointage123'), 'Fall', 'Awa', 'pointage@pointage.sn', 'pointage', 12),
        ('employe', h('employe123'), 'Sow', 'Moussa', 'employe@pointage.sn', 'employe', 6),
    ]
    for username, pwd, nom, prenom, email, role, emp_id in users:
        c.execute("""INSERT INTO utilisateurs (username, password_hash, nom, prenom, email, role, employe_id, actif)
                     VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                  (username, pwd, nom, prenom, email, role, emp_id))

    print("[INIT] ✅ Données de démo insérées (30 employés, 10 postes, 3 sites)")


if __name__ == '__main__':
    init_db()
