"""Migration v2 — semestres, maquette, notes, presences, emploi_temps, utilisateurs, audit"""
import sqlite3
import os
import sys
from datetime import datetime

DB_PATH = "/app/data/ecole.db"


def migrate():
    os.makedirs("/app/data", exist_ok=True)
    print("[MIGRATE v2] Démarrage migration v2...")

    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # ========== 1. SEMESTRES ==========
    c.execute("""CREATE TABLE IF NOT EXISTS semestres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL, nom TEXT NOT NULL,
        annee_academique TEXT NOT NULL,
        date_debut TEXT, date_fin TEXT)""")

    c.execute("SELECT COUNT(*) FROM semestres")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO semestres (code, nom, annee_academique) VALUES (?, ?, ?)",
            [("S1", "Semestre 1", "2025-2026"),
             ("S2", "Semestre 2", "2025-2026")])
        print("[MIGRATE v2] ✅ Semestres S1/S2 créés")

    # ========== 2. MAQUETTE ==========
    c.execute("""CREATE TABLE IF NOT EXISTS maquette (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filiere_id INTEGER NOT NULL, niveau_id INTEGER NOT NULL,
        semestre_id INTEGER NOT NULL, matiere_id INTEGER NOT NULL,
        obligatoire INTEGER DEFAULT 1,
        UNIQUE(filiere_id, niveau_id, semestre_id, matiere_id))""")

    # ========== 3. NOTES ==========
    c.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        etudiant_id INTEGER NOT NULL, matiere_id INTEGER NOT NULL,
        semestre_id INTEGER NOT NULL, classe_id INTEGER NOT NULL,
        cc1 REAL DEFAULT NULL, cc2 REAL DEFAULT NULL,
        tp REAL DEFAULT NULL, examen REAL DEFAULT NULL,
        note_finale REAL DEFAULT NULL, rang INTEGER DEFAULT NULL,
        appreciation TEXT, statut TEXT DEFAULT 'Non saisi',
        date_saisie TEXT, saisi_par INTEGER,
        UNIQUE(etudiant_id, matiere_id, semestre_id))""")

    # ========== 4. PRÉSENCES ==========
    c.execute("""CREATE TABLE IF NOT EXISTS presences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        etudiant_id INTEGER NOT NULL, classe_id INTEGER NOT NULL,
        date_presence TEXT NOT NULL,
        heure_debut TEXT, heure_fin TEXT, matiere_id INTEGER,
        statut TEXT DEFAULT 'Présent', motif TEXT,
        justificatif INTEGER DEFAULT 0)""")

    # ========== 5. EMPLOI DU TEMPS ==========
    c.execute("""CREATE TABLE IF NOT EXISTS emploi_temps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        classe_id INTEGER NOT NULL, matiere_id INTEGER NOT NULL,
        professeur_id INTEGER, semestre_id INTEGER NOT NULL,
        jour TEXT NOT NULL, heure_debut TEXT NOT NULL, heure_fin TEXT NOT NULL,
        salle TEXT, annee_academique TEXT NOT NULL)""")

    # ========== 6. UTILISATEURS ==========
    c.execute("""CREATE TABLE IF NOT EXISTS utilisateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
        role TEXT NOT NULL, etudiant_id INTEGER, professeur_id INTEGER,
        email TEXT, actif INTEGER DEFAULT 1,
        derniere_connexion TEXT,
        date_creation TEXT DEFAULT CURRENT_TIMESTAMP)""")

    # ========== 7. AUDIT LOG ==========
    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, action TEXT NOT NULL,
        table_cible TEXT, enregistrement_id INTEGER,
        details TEXT, ip TEXT,
        date_action TEXT DEFAULT CURRENT_TIMESTAMP)""")

    # ========== 8. VÉRIFICATIONS BULLETINS PDF ==========
    c.execute("""CREATE TABLE IF NOT EXISTS bulletins_verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code_verification TEXT UNIQUE NOT NULL,
        etudiant_id INTEGER NOT NULL,
        semestre_id INTEGER,
        moyenne REAL,
        mention TEXT,
        date_generation TEXT DEFAULT CURRENT_TIMESTAMP,
        hash_document TEXT)""")

    # ========== MIGRATION DES BULLETINS EXISTANTS VERS NOTES ==========
    c.execute("""INSERT OR IGNORE INTO notes 
        (etudiant_id, matiere_id, semestre_id, classe_id,
         cc1, cc2, tp, examen, note_finale, statut)
        SELECT b.etudiant_id, b.matiere_id,
               COALESCE((SELECT id FROM semestres WHERE code='S1'), 1),
               e.classe_id,
               b.note_cc, NULL, b.note_tp, b.note_examen, b.note_finale,
               CASE WHEN b.note_finale > 0 THEN 'Validé' ELSE 'Non saisi' END
        FROM bulletins b
        JOIN etudiants e ON e.id = b.etudiant_id""")

    # ========== UTILISATEURS PAR DÉFAUT (mot de passe hashé Werkzeug) ==========
    c.execute("SELECT COUNT(*) FROM utilisateurs")
    if c.fetchone()[0] == 0:
        from werkzeug.security import generate_password_hash

        users = [
            ("admin", generate_password_hash("admin123"), "admin", None, None, "admin@omega.sn"),
            ("prof001", generate_password_hash("prof123"), "professeur", None, 1, "mamadou.diop@omega.sn"),
            ("prof002", generate_password_hash("prof123"), "professeur", None, 2, "aminata.fall@omega.sn"),
            ("prof005", generate_password_hash("prof123"), "professeur", None, 5, "ibrahima.diallo@omega.sn"),
            ("etudiant001", generate_password_hash("etu123"), "etudiant", 1, None, "aliou.sarr@edu.sn"),
            ("etudiant002", generate_password_hash("etu123"), "etudiant", 2, None, "aissatou.ba@edu.sn"),
            ("etudiant004", generate_password_hash("etu123"), "etudiant", 4, None, "mariama.ndiaye@edu.sn"),
        ]
        for username, pwd_hash, role, etu_id, prof_id, email in users:
            c.execute("""INSERT INTO utilisateurs 
                (username, password_hash, role, etudiant_id, professeur_id, email)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (username, pwd_hash, role, etu_id, prof_id, email))

        print("[MIGRATE v2] ✅ Comptes utilisateurs créés :")
        print("                admin / admin123")
        print("                prof001, prof002, prof005 / prof123")
        print("                etudiant001, etudiant002, etudiant004 / etu123")

    # ========== MAQUETTE IA-L1 ==========
    c.execute("SELECT COUNT(*) FROM maquette WHERE filiere_id=(SELECT id FROM filieres WHERE code='IA') AND niveau_id=(SELECT id FROM niveaux WHERE code='L1')")
    if c.fetchone()[0] == 0:
        c.execute("SELECT id FROM filieres WHERE code='IA'")
        f_ia = c.fetchone()
        c.execute("SELECT id FROM filieres WHERE code='FC'")
        f_fc = c.fetchone()
        c.execute("SELECT id FROM niveaux WHERE code='L1'")
        n_l1 = c.fetchone()
        c.execute("SELECT id FROM semestres WHERE code='S1'")
        s1 = c.fetchone()
        c.execute("SELECT id FROM semestres WHERE code='S2'")
        s2 = c.fetchone()

        # Maquette IA-L1
        if f_ia and n_l1 and s1 and s2:
            for code_m in ["IA-L1-ALGO", "IA-L1-MATH", "IA-L1-ANG"]:
                c.execute("SELECT id FROM matieres WHERE code=?", (code_m,))
                m = c.fetchone()
                if m:
                    c.execute("""INSERT OR IGNORE INTO maquette 
                        (filiere_id, niveau_id, semestre_id, matiere_id, obligatoire)
                        VALUES (?, ?, ?, ?, 1)""",
                        (f_ia[0], n_l1[0], s1[0], m[0]))
            for code_m in ["IA-L1-PROG", "IA-L1-BD", "IA-L1-RES"]:
                c.execute("SELECT id FROM matieres WHERE code=?", (code_m,))
                m = c.fetchone()
                if m:
                    c.execute("""INSERT OR IGNORE INTO maquette 
                        (filiere_id, niveau_id, semestre_id, matiere_id, obligatoire)
                        VALUES (?, ?, ?, ?, 1)""",
                        (f_ia[0], n_l1[0], s2[0], m[0]))
            print("[MIGRATE v2] ✅ Maquette IA-L1 S1/S2 initialisée")

        # Maquette FC-L1 (Finance Comptabilité)
        if f_fc and n_l1 and s1 and s2:
            for code_m in ["FC-L1-COMPTA", "FC-L1-ECO", "FC-L1-ANG"]:
                c.execute("SELECT id FROM matieres WHERE code=?", (code_m,))
                m = c.fetchone()
                if m:
                    c.execute("""INSERT OR IGNORE INTO maquette 
                        (filiere_id, niveau_id, semestre_id, matiere_id, obligatoire)
                        VALUES (?, ?, ?, ?, 1)""",
                        (f_fc[0], n_l1[0], s1[0], m[0]))
            for code_m in ["FC-L1-MATH", "FC-L1-DROIT"]:
                c.execute("SELECT id FROM matieres WHERE code=?", (code_m,))
                m = c.fetchone()
                if m:
                    c.execute("""INSERT OR IGNORE INTO maquette 
                        (filiere_id, niveau_id, semestre_id, matiere_id, obligatoire)
                        VALUES (?, ?, ?, ?, 1)""",
                        (f_fc[0], n_l1[0], s2[0], m[0]))
            print("[MIGRATE v2] ✅ Maquette FC-L1 S1/S2 initialisée")

    conn.commit()
    conn.close()
    print("[MIGRATE v2] ✅ Migration terminée avec succès")


def generate_bulletins_for_student(etudiant_id, classe_id):
    """Génère les notes vides (bulletins encapsulés) selon la maquette de la classe"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute("PRAGMA busy_timeout=30000")
        c = conn.cursor()

        c.execute("SELECT filiere_id, niveau_id FROM classes WHERE id = ?", (classe_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return 0
        filiere_id, niveau_id = row

        c.execute("""SELECT matiere_id, semestre_id FROM maquette
            WHERE filiere_id = ? AND niveau_id = ?""", (filiere_id, niveau_id))
        maquette_rows = c.fetchall()

        count = 0
        for matiere_id, semestre_id in maquette_rows:
            c.execute("""INSERT OR IGNORE INTO notes 
                (etudiant_id, matiere_id, semestre_id, classe_id, statut)
                VALUES (?, ?, ?, ?, 'Non saisi')""",
                (etudiant_id, matiere_id, semestre_id, classe_id))
            if c.rowcount > 0:
                count += 1

        conn.commit()
        conn.close()
        return count
    except Exception as e:
        print(f"[BULLETIN] Erreur: {e}")
        return 0


if __name__ == "__main__":
    try:
        migrate()
        sys.exit(0)
    except Exception as e:
        print(f"[MIGRATE v2] ❌ ERREUR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
