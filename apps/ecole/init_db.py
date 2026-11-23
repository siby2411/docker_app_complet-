"""Init DB v1 — tables de base + données de démonstration"""
import sqlite3
import os
import sys
from datetime import datetime

DB_PATH = "/app/data/ecole.db"


def init_db():
    os.makedirs("/app/data", exist_ok=True)
    print(f"[INIT v1] Connexion à {DB_PATH}")

    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    c = conn.cursor()

    # ========== TABLES ==========
    c.execute("""CREATE TABLE IF NOT EXISTS cycles (
        id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL, description TEXT, duree_ans INTEGER DEFAULT 3)""")

    c.execute("""CREATE TABLE IF NOT EXISTS filieres (
        id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL, cycle_id INTEGER NOT NULL, description TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS niveaux (
        id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL, cycle_id INTEGER NOT NULL, ordre INTEGER DEFAULT 1)""")

    c.execute("""CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL, niveau_id INTEGER NOT NULL, filiere_id INTEGER NOT NULL,
        annee_academique TEXT NOT NULL, capacite INTEGER DEFAULT 30, effectif INTEGER DEFAULT 0)""")

    c.execute("""CREATE TABLE IF NOT EXISTS matieres (
        id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL, niveau_id INTEGER NOT NULL, coefficient INTEGER DEFAULT 1,
        credit INTEGER DEFAULT 3, heures_cours INTEGER DEFAULT 0,
        heures_td INTEGER DEFAULT 0, heures_tp INTEGER DEFAULT 0)""")

    c.execute("""CREATE TABLE IF NOT EXISTS etudiants (
        id INTEGER PRIMARY KEY AUTOINCREMENT, matricule TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL, prenom TEXT NOT NULL, date_naissance TEXT NOT NULL,
        lieu_naissance TEXT, sexe TEXT NOT NULL, telephone TEXT NOT NULL,
        email TEXT NOT NULL, adresse TEXT, classe_id INTEGER NOT NULL,
        date_inscription TEXT NOT NULL, statut TEXT DEFAULT 'Actif')""")

    c.execute("""CREATE TABLE IF NOT EXISTS bulletins (
        id INTEGER PRIMARY KEY AUTOINCREMENT, etudiant_id INTEGER NOT NULL,
        matiere_id INTEGER NOT NULL, note_cc REAL DEFAULT 0, note_tp REAL DEFAULT 0,
        note_examen REAL DEFAULT 0, note_finale REAL DEFAULT 0,
        moyenne REAL DEFAULT 0, appreciation TEXT, statut TEXT DEFAULT 'En cours')""")

    c.execute("""CREATE TABLE IF NOT EXISTS professeurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL, prenom TEXT NOT NULL, telephone TEXT NOT NULL,
        email TEXT NOT NULL, specialite TEXT, date_embauche TEXT NOT NULL,
        statut TEXT DEFAULT 'Actif')""")

    c.execute("""CREATE TABLE IF NOT EXISTS affectations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, professeur_id INTEGER NOT NULL,
        matiere_id INTEGER NOT NULL, classe_id INTEGER NOT NULL,
        annee_academique TEXT NOT NULL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS scolarite (
        id INTEGER PRIMARY KEY AUTOINCREMENT, etudiant_id INTEGER NOT NULL,
        montant REAL NOT NULL, mois TEXT NOT NULL, date_paiement TEXT NOT NULL,
        mode_paiement TEXT, reference TEXT, statut TEXT DEFAULT 'En attente')""")

    # ========== DONNÉES DE DÉMO ==========
    c.execute("SELECT COUNT(*) FROM cycles")
    if c.fetchone()[0] == 0:
        print("[INIT v1] Insertion des données initiales...")

        c.executemany("INSERT INTO cycles (code, nom, description, duree_ans) VALUES (?, ?, ?, ?)",
            [("LIC", "Licence", "Cycle Licence - 3 ans", 3),
             ("MAS", "Master", "Cycle Master - 2 ans", 2),
             ("DOC", "Doctorat", "Cycle Doctorat - 3 ans", 3)])

        c.executemany("INSERT INTO niveaux (code, nom, cycle_id, ordre) VALUES (?, ?, ?, ?)",
            [("L1", "Licence 1", 1, 1), ("L2", "Licence 2", 1, 2), ("L3", "Licence 3", 1, 3),
             ("M1", "Master 1", 2, 1), ("M2", "Master 2", 2, 2),
             ("D1", "Doctorat 1", 3, 1), ("D2", "Doctorat 2", 3, 2), ("D3", "Doctorat 3", 3, 3)])

        c.executemany("INSERT INTO filieres (code, nom, cycle_id, description) VALUES (?, ?, ?, ?)",
            [("IA", "Informatique Appliquée", 1, "Informatique appliquée"),
             ("SE", "Systèmes Embarqués", 1, "Systèmes embarqués et IoT"),
             ("RS", "Réseaux et Sécurité", 1, "Réseaux et cybersécurité"),
             ("FC", "Finance Comptabilité", 1, "Finance et comptabilité"),
             ("GL", "Génie Logiciel", 1, "Ingénierie logicielle")])

        c.executemany("""INSERT INTO classes (code, nom, niveau_id, filiere_id, annee_academique, capacite)
            VALUES (?, ?, ?, ?, ?, ?)""",
            [("IA-L1", "IA - Licence 1", 1, 1, "2025-2026", 40),
             ("IA-L2", "IA - Licence 2", 2, 1, "2025-2026", 35),
             ("IA-L3", "IA - Licence 3", 3, 1, "2025-2026", 30),
             ("FC-L1", "FC - Licence 1", 1, 4, "2025-2026", 40),
             ("FC-L2", "FC - Licence 2", 2, 4, "2025-2026", 35),
             ("SE-L1", "SE - Licence 1", 1, 2, "2025-2026", 35),
             ("RS-L1", "RS - Licence 1", 1, 3, "2025-2026", 35)])

        c.executemany("""INSERT INTO matieres (code, nom, niveau_id, coefficient, credit, heures_cours, heures_td, heures_tp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [("IA-L1-ALGO", "Algorithmique", 1, 3, 4, 60, 30, 0),
             ("IA-L1-PROG", "Programmation", 1, 4, 5, 60, 30, 15),
             ("IA-L1-BD", "Bases de Données", 1, 3, 4, 45, 30, 15),
             ("IA-L1-RES", "Réseaux", 1, 2, 3, 45, 15, 0),
             ("IA-L1-MATH", "Mathématiques", 1, 3, 3, 60, 0, 0),
             ("IA-L1-ANG", "Anglais Technique", 1, 1, 2, 30, 0, 0),
             ("FC-L1-COMPTA", "Comptabilité Générale", 1, 4, 5, 60, 30, 0),
             ("FC-L1-ECO", "Économie", 1, 3, 4, 45, 15, 0),
             ("FC-L1-MATH", "Mathématiques Financières", 1, 3, 4, 45, 30, 0),
             ("FC-L1-DROIT", "Droit des Affaires", 1, 2, 3, 30, 15, 0),
             ("FC-L1-ANG", "Anglais des Affaires", 1, 2, 2, 30, 0, 0)])

        c.executemany("""INSERT INTO professeurs (code, nom, prenom, telephone, email, specialite, date_embauche)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [("P001", "Diop", "Mamadou", "771234567", "mamadou.diop@omega.sn", "Algorithmique", "2020-01-15"),
             ("P002", "Fall", "Aminata", "772345678", "aminata.fall@omega.sn", "Bases de Données", "2020-09-01"),
             ("P003", "Ndiaye", "Ousmane", "773456789", "ousmane.ndiaye@omega.sn", "Programmation", "2021-01-10"),
             ("P004", "Sow", "Fatou", "774567890", "fatou.sow@omega.sn", "Réseaux", "2021-09-15"),
             ("P005", "Diallo", "Ibrahima", "775678901", "ibrahima.diallo@omega.sn", "Comptabilité", "2019-09-01")])

        now = datetime.now().isoformat()
        c.executemany("""INSERT INTO etudiants (matricule, nom, prenom, date_naissance, lieu_naissance,
            sexe, telephone, email, adresse, classe_id, date_inscription, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Actif')""",
            [("E001", "Sarr", "Aliou", "2000-05-15", "Dakar", "M", "771234568", "aliou.sarr@edu.sn", "Dakar", 1, now),
             ("E002", "Ba", "Aissatou", "2001-03-22", "Thiès", "F", "772345679", "aissatou.ba@edu.sn", "Thiès", 1, now),
             ("E003", "Kane", "Moussa", "2000-11-10", "Kaolack", "M", "773456780", "moussa.kane@edu.sn", "Kaolack", 1, now),
             ("E004", "Ndiaye", "Mariama", "2000-08-05", "Saint-Louis", "F", "774567891", "mariama.ndiaye@edu.sn", "Saint-Louis", 4, now),
             ("E005", "Sow", "Cheikh", "2001-01-20", "Ziguinchor", "M", "775678902", "cheikh.sow@edu.sn", "Ziguinchor", 4, now)])

        c.execute("""INSERT INTO bulletins (etudiant_id, matiere_id, note_cc, note_tp, note_examen, note_finale, moyenne, statut)
            SELECT e.id, m.id, 0, 0, 0, 0, 0, 'En cours' FROM etudiants e
            JOIN classes c ON e.classe_id = c.id JOIN matieres m ON m.niveau_id = c.niveau_id""")

        c.executemany("""INSERT INTO scolarite (etudiant_id, montant, mois, date_paiement, mode_paiement, reference, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(1, 150000, "Septembre", now, "Wave", "WAVE001", "Payé"),
             (2, 150000, "Septembre", now, "Espèces", "ES001", "Payé"),
             (3, 150000, "Septembre", now, "Orange Money", "OM001", "En attente"),
             (4, 175000, "Septembre", now, "Virement", "VIR001", "Payé"),
             (5, 175000, "Septembre", now, "Wave", "WAVE002", "En attente")])

        print("[INIT v1] Données initiales insérées.")
    else:
        print("[INIT v1] DB déjà initialisée, skip.")

    conn.commit()
    conn.close()
    print("[INIT v1] ✅ Terminé avec succès")


if __name__ == "__main__":
    try:
        init_db()
        sys.exit(0)
    except Exception as e:
        print(f"[INIT v1] ❌ ERREUR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
