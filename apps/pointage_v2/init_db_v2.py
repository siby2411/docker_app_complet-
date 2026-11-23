"""
Omega Pointage V2 — Migration v2 : Vues SQL + données démo pointages
"""
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "/app/data/pointage_v2.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def migrate():
    print("[MIGRATE v2] Démarrage...")
    conn = get_conn()
    c = conn.cursor()

    # ==================== VUES SQL ====================

    c.execute("DROP VIEW IF EXISTS v_employes_complets")
    c.execute("""CREATE VIEW v_employes_complets AS
                 SELECT e.*,
                        p.nom AS poste_nom, p.code AS poste_code,
                        d.nom AS departement_nom, d.code AS departement_code,
                        s.nom AS site_nom, s.code AS site_code
                 FROM employes e
                 LEFT JOIN postes p ON e.poste_id = p.id
                 LEFT JOIN departements d ON e.departement_id = d.id
                 LEFT JOIN sites s ON e.site_id = s.id
                 WHERE e.actif = 1""")
    print("[MIGRATE v2] ✅ Vue v_employes_complets créée")

    c.execute("DROP VIEW IF EXISTS v_pointages_jour")
    c.execute("""CREATE VIEW v_pointages_jour AS
                 SELECT p.*,
                        e.matricule, e.nom, e.prenom,
                        d.nom AS departement_nom
                 FROM pointages p
                 LEFT JOIN employes e ON p.employe_id = e.id
                 LEFT JOIN departements d ON e.departement_id = d.id
                 ORDER BY p.date_pointage DESC, p.heure_entree DESC""")
    print("[MIGRATE v2] ✅ Vue v_pointages_jour créée")

    c.execute("DROP VIEW IF EXISTS v_stats_pointage_mois")
    c.execute("""CREATE VIEW v_stats_pointage_mois AS
                 SELECT
                    strftime('%Y-%m', date_pointage) AS mois,
                    COUNT(DISTINCT employe_id) AS nb_employes,
                    COUNT(*) AS nb_pointages,
                    SUM(CASE WHEN statut = 'Retard' THEN 1 ELSE 0 END) AS nb_retards,
                    SUM(CASE WHEN statut = 'Absent' THEN 1 ELSE 0 END) AS nb_absences,
                    COALESCE(SUM(heures_travaillees), 0) AS total_heures,
                    COALESCE(SUM(heures_sup), 0) AS total_heures_sup
                 FROM pointages
                 GROUP BY mois
                 ORDER BY mois DESC""")
    print("[MIGRATE v2] ✅ Vue v_stats_pointage_mois créée")

    c.execute("DROP VIEW IF EXISTS v_conges_en_cours")
    c.execute("""CREATE VIEW v_conges_en_cours AS
                 SELECT c.*,
                        e.matricule, e.nom, e.prenom,
                        tc.nom AS type_nom, tc.couleur AS type_couleur
                 FROM conges c
                 LEFT JOIN employes e ON c.employe_id = e.id
                 LEFT JOIN types_conges tc ON c.type_conge_id = tc.id
                 WHERE c.statut IN ('En attente', 'Approuvé')
                   AND date(c.date_fin) >= date('now')
                 ORDER BY c.date_debut""")
    print("[MIGRATE v2] ✅ Vue v_conges_en_cours créée")

    c.execute("DROP VIEW IF EXISTS v_alertes_actives")
    c.execute("""CREATE VIEW v_alertes_actives AS
                 SELECT a.*, e.matricule, e.nom, e.prenom
                 FROM alertes a
                 LEFT JOIN employes e ON a.employe_id = e.id
                 WHERE a.statut = 'Active'
                 ORDER BY a.created_at DESC""")
    print("[MIGRATE v2] ✅ Vue v_alertes_actives créée")

    conn.commit()

    # ==================== DONNEES DEMO POINTAGES ====================
    c.execute("SELECT COUNT(*) FROM pointages")
    if c.fetchone()[0] == 0:
        print("[MIGRATE v2] Insertion pointages de démonstration...")
        _seed_pointages(c)
        conn.commit()

    conn.close()
    print("[MIGRATE v2] ✅ Migration terminée")


def _seed_pointages(c):
    """Génère 30 jours de pointages pour 10 employés"""
    now = datetime.now()
    employes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    import random
    random.seed(42)  # Déterministe

    for jour_offset in range(30, 0, -1):
        d = now - timedelta(days=jour_offset)
        if d.weekday() >= 5:  # Skip weekend
            continue

        date_str = d.date().isoformat()

        for emp_id in employes:
            # 85% présence, 10% retard, 5% absence
            r = random.random()
            if r < 0.05:
                # Absence
                c.execute("""INSERT INTO pointages
                    (employe_id, date_pointage, statut, mode, notes)
                    VALUES (?, ?, 'Absent', 'Manuel', 'Absence non justifiée')""",
                    (emp_id, date_str))
                continue

            if r < 0.15:
                # Retard
                heure_entree = f"{random.randint(8, 9):02d}:{random.randint(15, 59):02d}"
                statut = 'Retard'
            else:
                heure_entree = f"08:{random.randint(0, 10):02d}"
                statut = 'Normal'

            heure_sortie = f"17:{random.randint(0, 30):02d}"

            # Calcul heures
            h_entree = int(heure_entree.split(':')[0]) * 60 + int(heure_entree.split(':')[1])
            h_sortie = int(heure_sortie.split(':')[0]) * 60 + int(heure_sortie.split(':')[1])
            duree_min = h_sortie - h_entree - 60  # -1h pause
            heures = duree_min / 60

            heures_sup = max(0, heures - 8)

            c.execute("""INSERT INTO pointages
                (employe_id, date_pointage, heure_entree, heure_sortie,
                 terminal, ip_source, mode, duree_minutes, heures_travaillees,
                 heures_sup, statut)
                VALUES (?, ?, ?, ?, 'TERM-001', '192.168.1.100', 'Biométrique',
                        ?, ?, ?, ?)""",
                (emp_id, date_str, heure_entree, heure_sortie,
                 duree_min, round(heures, 2), round(heures_sup, 2), statut))

    print("[MIGRATE v2] ✅ Pointages démo insérés (~300 enregistrements)")


if __name__ == '__main__':
    migrate()
