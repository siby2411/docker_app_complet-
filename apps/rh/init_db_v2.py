"""
Migration v2 Gestion RH
Ajouts : notes de frais, prêts employés, avances, mouvements carrière,
sanctions, objectifs, absences exceptionnelles
"""
import sqlite3
import os

DB_PATH = "/app/data/rh.db"


def migrate():
    os.makedirs("/app/data", exist_ok=True)
    print("[MIGRATE v2] Démarrage...")

    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # ==================== 23. NOTES DE FRAIS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS notes_frais (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        employe_id INTEGER NOT NULL,
        date_depense TEXT NOT NULL,
        date_soumission TEXT NOT NULL,
        categorie TEXT NOT NULL,
        description TEXT NOT NULL,
        montant REAL NOT NULL,
        justificatif_fichier TEXT,
        statut TEXT DEFAULT 'En attente',
        valideur_id INTEGER,
        date_validation TEXT,
        motif_refus TEXT,
        date_remboursement TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== 24. PRÊTS EMPLOYÉS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS prets_employes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        employe_id INTEGER NOT NULL,
        montant REAL NOT NULL,
        motif TEXT,
        date_pret TEXT NOT NULL,
        duree_mois INTEGER NOT NULL,
        mensualite REAL NOT NULL,
        montant_restant REAL NOT NULL,
        taux_interet REAL DEFAULT 0,
        statut TEXT DEFAULT 'En cours',
        valideur_id INTEGER,
        date_validation TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== 25. REMBOURSEMENTS PRÊTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS prets_remboursements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pret_id INTEGER NOT NULL,
        date_remboursement TEXT NOT NULL,
        montant REAL NOT NULL,
        bulletin_id INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pret_id) REFERENCES prets_employes(id)
    )""")

    # ==================== 26. MOUVEMENTS CARRIÈRE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS mouvements_carriere (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER NOT NULL,
        type_mouvement TEXT NOT NULL,
        date_effet TEXT NOT NULL,
        ancien_poste_id INTEGER,
        nouveau_poste_id INTEGER,
        ancien_salaire REAL,
        nouveau_salaire REAL,
        motif TEXT,
        document_fichier TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== 27. SANCTIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS sanctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        employe_id INTEGER NOT NULL,
        type_sanction TEXT NOT NULL,
        motif TEXT NOT NULL,
        description TEXT,
        date_sanction TEXT NOT NULL,
        date_effet TEXT,
        duree_jours INTEGER,
        impact_salaire REAL DEFAULT 0,
        statut TEXT DEFAULT 'Active',
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== 28. OBJECTIFS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS objectifs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER NOT NULL,
        titre TEXT NOT NULL,
        description TEXT,
        periode TEXT NOT NULL,
        annee INTEGER NOT NULL,
        type_objectif TEXT,
        indicateur TEXT,
        cible TEXT,
        poids REAL DEFAULT 1,
        progression REAL DEFAULT 0,
        note REAL DEFAULT 0,
        statut TEXT DEFAULT 'En cours',
        date_echeance TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== 29. AVANCES SALAIRE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS avances_salaire (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        employe_id INTEGER NOT NULL,
        montant REAL NOT NULL,
        motif TEXT,
        date_demande TEXT NOT NULL,
        date_validation TEXT,
        mois_deduction INTEGER,
        annee_deduction INTEGER,
        statut TEXT DEFAULT 'En attente',
        valideur_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== 30. VISITES MÉDICALES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS visites_medicales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employe_id INTEGER NOT NULL,
        type_visite TEXT NOT NULL,
        date_visite TEXT NOT NULL,
        medecin TEXT,
        etablissement TEXT,
        resultat TEXT,
        apte INTEGER DEFAULT 1,
        restrictions TEXT,
        prochaine_visite TEXT,
        cout REAL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employe_id) REFERENCES employes(id)
    )""")

    # ==================== 31. ANNONCES INTERNES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS annonces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titre TEXT NOT NULL,
        contenu TEXT NOT NULL,
        categorie TEXT,
        priorite TEXT DEFAULT 'Normale',
        date_publication TEXT NOT NULL,
        date_expiration TEXT,
        auteur_id INTEGER,
        destinataires TEXT,
        statut TEXT DEFAULT 'Publiée',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 32. NOTIFICATIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        destinataire_id INTEGER,
        type_notification TEXT NOT NULL,
        titre TEXT NOT NULL,
        message TEXT NOT NULL,
        lien TEXT,
        priorite TEXT DEFAULT 'Normale',
        statut TEXT DEFAULT 'Non lue',
        date_creation TEXT DEFAULT CURRENT_TIMESTAMP,
        date_lecture TEXT
    )""")

    conn.commit()

    # ==================== INDEX DE PERFORMANCE ====================
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_employes_matricule ON employes(matricule)",
        "CREATE INDEX IF NOT EXISTS idx_employes_nom ON employes(nom, prenom)",
        "CREATE INDEX IF NOT EXISTS idx_employes_departement ON employes(departement_id)",
        "CREATE INDEX IF NOT EXISTS idx_employes_statut ON employes(statut)",
        "CREATE INDEX IF NOT EXISTS idx_employes_actif ON employes(actif)",
        "CREATE INDEX IF NOT EXISTS idx_contrats_employe ON contrats(employe_id)",
        "CREATE INDEX IF NOT EXISTS idx_conges_employe ON conges(employe_id)",
        "CREATE INDEX IF NOT EXISTS idx_conges_statut ON conges(statut)",
        "CREATE INDEX IF NOT EXISTS idx_conges_dates ON conges(date_debut, date_fin)",
        "CREATE INDEX IF NOT EXISTS idx_bulletins_employe ON bulletins_paie(employe_id)",
        "CREATE INDEX IF NOT EXISTS idx_bulletins_periode ON bulletins_paie(annee, mois)",
        "CREATE INDEX IF NOT EXISTS idx_pointages_employe ON pointages(employe_id)",
        "CREATE INDEX IF NOT EXISTS idx_pointages_date ON pointages(date_pointage)",
        "CREATE INDEX IF NOT EXISTS idx_evaluations_employe ON evaluations(employe_id)",
        "CREATE INDEX IF NOT EXISTS idx_formations_employes_emp ON formations_employes(employe_id)",
        "CREATE INDEX IF NOT EXISTS idx_candidats_offre ON candidats(offre_id)",
        "CREATE INDEX IF NOT EXISTS idx_documents_employe ON documents_rh(employe_id)",
        "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_log(created_at)",
    ]

    for idx in indexes:
        try:
            c.execute(idx)
        except Exception as e:
            print(f"[MIGRATE v2] ⚠️ Index : {e}")

    conn.commit()
    conn.close()
    print("[MIGRATE v2] ✅ Migration terminée")


if __name__ == "__main__":
    migrate()
