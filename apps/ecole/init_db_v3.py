"""Migration v3 — Sprint 2 : présences, emploi_temps, délibérations, logs SMS/email"""
import sqlite3
import os
import sys

DB_PATH = "/app/data/ecole.db"


def migrate():
    os.makedirs("/app/data", exist_ok=True)
    print("[MIGRATE v3] Démarrage migration Sprint 2...")

    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # ========== 1. PRÉSENCES (remplace la v2 par une version enrichie) ==========
    c.execute("""CREATE TABLE IF NOT EXISTS presences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        etudiant_id INTEGER NOT NULL, classe_id INTEGER NOT NULL,
        matiere_id INTEGER, semestre_id INTEGER,
        date_presence TEXT NOT NULL,
        heure_debut TEXT, heure_fin TEXT,
        statut TEXT DEFAULT 'Présent',  -- Présent / Absent / Retard / Excusé
        motif TEXT, justificatif INTEGER DEFAULT 0,
        saisi_par INTEGER,
        date_saisie TEXT DEFAULT CURRENT_TIMESTAMP)""")

    # ========== 2. EMPLOI DU TEMPS (enrichi) ==========
    c.execute("""CREATE TABLE IF NOT EXISTS emploi_temps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        classe_id INTEGER NOT NULL, matiere_id INTEGER NOT NULL,
        professeur_id INTEGER, semestre_id INTEGER NOT NULL,
        jour TEXT NOT NULL,  -- Lundi/Mardi/.../Samedi
        heure_debut TEXT NOT NULL, heure_fin TEXT NOT NULL,
        salle TEXT,
        annee_academique TEXT NOT NULL,
        couleur TEXT DEFAULT '#e94560',
        saisi_par INTEGER,
        date_creation TEXT DEFAULT CURRENT_TIMESTAMP)""")

    # ========== 3. DÉLIBÉRATIONS (jury fin semestre) ==========
    c.execute("""CREATE TABLE IF NOT EXISTS deliberations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        etudiant_id INTEGER NOT NULL, classe_id INTEGER NOT NULL,
        semestre_id INTEGER NOT NULL,
        moyenne REAL, rang INTEGER,
        decision TEXT,  -- Admis / Redouble / Ajourné / Passable
        mention TEXT,
        credits_valides INTEGER DEFAULT 0,
        credits_total INTEGER DEFAULT 0,
        observations TEXT,
        valide_par INTEGER,
        date_deliberation TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(etudiant_id, semestre_id))""")

    # ========== 4. NOTIFICATIONS (SMS + Email) ==========
    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,  -- SMS / EMAIL
        destinataire TEXT NOT NULL,
        sujet TEXT, contenu TEXT NOT NULL,
        etudiant_id INTEGER,
        statut TEXT DEFAULT 'En attente',  -- En attente / Envoyé / Échec
        erreur TEXT,
        provider TEXT,  -- Wave / Orange / SMTP
        reference TEXT,
        date_creation TEXT DEFAULT CURRENT_TIMESTAMP,
        date_envoi TEXT)""")

    # ========== 5. CONFIGURATION COMMUNICATION ==========
    c.execute("""CREATE TABLE IF NOT EXISTS config_communication (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cle TEXT UNIQUE NOT NULL,
        valeur TEXT,
        description TEXT,
        date_modification TEXT DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("SELECT COUNT(*) FROM config_communication")
    if c.fetchone()[0] == 0:
        configs = [
            ("sms_provider", "simulation", "Provider SMS : simulation / orange / wave"),
            ("sms_api_key", "", "Clé API SMS"),
            ("sms_sender", "OMEGA", "Nom expéditeur SMS"),
            ("email_smtp_host", "smtp.gmail.com", "Serveur SMTP"),
            ("email_smtp_port", "587", "Port SMTP"),
            ("email_smtp_user", "", "Utilisateur SMTP"),
            ("email_smtp_pass", "", "Mot de passe SMTP"),
            ("email_from", "noreply@omega.sn", "Email expéditeur"),
            ("notif_absence", "1", "Notification absence (0/1)"),
            ("notif_paiement", "1", "Notification paiement (0/1)"),
            ("notif_notes", "1", "Notification notes publiées (0/1)"),
        ]
        for cle, valeur, desc in configs:
            c.execute("""INSERT INTO config_communication (cle, valeur, description)
                VALUES (?, ?, ?)""", (cle, valeur, desc))
        print("[MIGRATE v3] ✅ Config communication initialisée")

    # ========== 6. ATTESTATIONS ==========
    c.execute("""CREATE TABLE IF NOT EXISTS attestations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        etudiant_id INTEGER NOT NULL,
        type TEXT NOT NULL,  -- scolarite / reussite / frequence
        code_verification TEXT UNIQUE NOT NULL,
        date_emission TEXT DEFAULT CURRENT_TIMESTAMP,
        contenu_json TEXT,
        emis_par INTEGER)""")

    # ========== 7. AJOUTER COLONNES À ETUDIANTS (si absentes) ==========
    try:
        c.execute("ALTER TABLE etudiants ADD COLUMN nom_parent TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE etudiants ADD COLUMN telephone_parent TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE etudiants ADD COLUMN email_parent TEXT")
    except sqlite3.OperationalError:
        pass

    # ========== 8. EXEMPLES D'EMPLOI DU TEMPS (IA-L1) ==========
    c.execute("SELECT COUNT(*) FROM emploi_temps")
    if c.fetchone()[0] == 0:
        c.execute("SELECT id FROM classes WHERE code='IA-L1'")
        classe_ia = c.fetchone()
        c.execute("SELECT id FROM matieres WHERE code='IA-L1-ALGO'")
        m_algo = c.fetchone()
        c.execute("SELECT id FROM matieres WHERE code='IA-L1-MATH'")
        m_math = c.fetchone()
        c.execute("SELECT id FROM matieres WHERE code='IA-L1-ANG'")
        m_ang = c.fetchone()
        c.execute("SELECT id FROM professeurs WHERE code='P001'")
        p_diop = c.fetchone()
        c.execute("SELECT id FROM semestres WHERE code='S1'")
        s1 = c.fetchone()

        if classe_ia and s1:
            exemples = []
            if m_algo:
                exemples += [(classe_ia[0], m_algo[0], p_diop[0] if p_diop else None, s1[0],
                              "Lundi", "08:00", "10:00", "Salle A1", "2025-2026"),
                             (classe_ia[0], m_algo[0], p_diop[0] if p_diop else None, s1[0],
                              "Mercredi", "10:00", "12:00", "Salle A1", "2025-2026")]
            if m_math:
                exemples += [(classe_ia[0], m_math[0], None, s1[0],
                              "Mardi", "08:00", "10:00", "Salle A2", "2025-2026")]
            if m_ang:
                exemples += [(classe_ia[0], m_ang[0], None, s1[0],
                              "Jeudi", "14:00", "16:00", "Salle B1", "2025-2026")]

            for ex in exemples:
                c.execute("""INSERT INTO emploi_temps
                    (classe_id, matiere_id, professeur_id, semestre_id, jour,
                     heure_debut, heure_fin, salle, annee_academique)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", ex)

            print(f"[MIGRATE v3] ✅ {len(exemples)} créneaux d'emploi du temps insérés")

    conn.commit()
    conn.close()
    print("[MIGRATE v3] ✅ Migration Sprint 2 terminée")


if __name__ == "__main__":
    try:
        migrate()
        sys.exit(0)
    except Exception as e:
        print(f"[MIGRATE v3] ❌ ERREUR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
