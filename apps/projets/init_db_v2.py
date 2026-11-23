"""
Migration v2 Gestion de Projets
Tables additionnelles + index + vues
"""
import sqlite3
import os

DB_PATH = "/app/data/projets.db"


def migrate():
    os.makedirs("/app/data", exist_ok=True)
    print("[MIGRATE v2] Démarrage...")

    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # ==================== 33. HISTORIQUE PROJET ====================
    c.execute("""CREATE TABLE IF NOT EXISTS historique_projet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projet_id INTEGER NOT NULL,
        date_evenement TEXT NOT NULL,
        type_evenement TEXT NOT NULL,
        titre TEXT NOT NULL,
        description TEXT,
        ancienne_valeur TEXT,
        nouvelle_valeur TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id)
    )""")

    # ==================== 34. KPIs ====================
    c.execute("""CREATE TABLE IF NOT EXISTS kpis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        categorie TEXT,
        unite TEXT,
        formule TEXT,
        valeur_cible REAL,
        seuil_alerte REAL,
        frequence TEXT DEFAULT 'Mensuel',
        actif INTEGER DEFAULT 1
    )""")

    # ==================== 35. KPI MESURES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS kpi_mesures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kpi_id INTEGER NOT NULL,
        projet_id INTEGER,
        date_mesure TEXT NOT NULL,
        valeur REAL NOT NULL,
        objectif REAL,
        statut TEXT,
        commentaire TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (kpi_id) REFERENCES kpis(id),
        FOREIGN KEY (projet_id) REFERENCES projets(id)
    )""")

    # ==================== 36. NOTIFICATIONS ====================
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

    # ==================== 37. PARTIES PRENANTES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS parties_prenantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projet_id INTEGER NOT NULL,
        nom TEXT NOT NULL,
        organisation TEXT,
        role TEXT,
        type TEXT,
        influence INTEGER DEFAULT 1,
        interet INTEGER DEFAULT 1,
        strategie TEXT,
        contact TEXT,
        telephone TEXT,
        email TEXT,
        attentes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id)
    )""")

    # ==================== 38. BUGS / INCIDENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        projet_id INTEGER NOT NULL,
        tache_id INTEGER,
        titre TEXT NOT NULL,
        description TEXT,
        severite TEXT DEFAULT 'Majeure',
        priorite TEXT DEFAULT 'Normale',
        statut TEXT DEFAULT 'Ouvert',
        signale_par INTEGER,
        assigne_a INTEGER,
        date_signalement TEXT NOT NULL,
        date_resolution TEXT,
        solution TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (tache_id) REFERENCES taches(id)
    )""")

    conn.commit()

    # ==================== INDEX ====================
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_projets_code ON projets(code)",
        "CREATE INDEX IF NOT EXISTS idx_projets_statut ON projets(statut)",
        "CREATE INDEX IF NOT EXISTS idx_projets_chef ON projets(chef_projet_id)",
        "CREATE INDEX IF NOT EXISTS idx_projets_client ON projets(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_taches_projet ON taches(projet_id)",
        "CREATE INDEX IF NOT EXISTS idx_taches_statut ON taches(statut)",
        "CREATE INDEX IF NOT EXISTS idx_taches_responsable ON taches(responsable_id)",
        "CREATE INDEX IF NOT EXISTS idx_taches_dates ON taches(date_debut_prevue, date_fin_prevue)",
        "CREATE INDEX IF NOT EXISTS idx_dependances_projet ON dependances(projet_id)",
        "CREATE INDEX IF NOT EXISTS idx_affectations_projet ON affectations(projet_id)",
        "CREATE INDEX IF NOT EXISTS idx_affectations_user ON affectations(utilisateur_id)",
        "CREATE INDEX IF NOT EXISTS idx_risques_projet ON risques(projet_id)",
        "CREATE INDEX IF NOT EXISTS idx_risques_statut ON risques(statut)",
        "CREATE INDEX IF NOT EXISTS idx_engagements_projet ON engagements(projet_id)",
        "CREATE INDEX IF NOT EXISTS idx_factures_projet ON factures_client(projet_id)",
        "CREATE INDEX IF NOT EXISTS idx_factures_statut ON factures_client(statut)",
        "CREATE INDEX IF NOT EXISTS idx_paiements_projet ON paiements(projet_id)",
        "CREATE INDEX IF NOT EXISTS idx_evm_projet ON evm(projet_id)",
        "CREATE INDEX IF NOT EXISTS idx_livrables_projet ON livrables(projet_id)",
        "CREATE INDEX IF NOT EXISTS idx_reunions_projet ON reunions(projet_id)",
        "CREATE INDEX IF NOT EXISTS idx_achats_projet ON achats(projet_id)",
        "CREATE INDEX IF NOT EXISTS idx_qualite_projet ON qualite(projet_id)",
        "CREATE INDEX IF NOT EXISTS idx_feuilles_user ON feuilles_temps(utilisateur_id)",
        "CREATE INDEX IF NOT EXISTS idx_feuilles_date ON feuilles_temps(date_jour)",
        "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_log(created_at)",
    ]

    for idx in indexes:
        try:
            c.execute(idx)
        except Exception as e:
            print(f"[MIGRATE v2] ⚠️ Index : {e}")

    conn.commit()

    # ==================== SEED KPI ====================
    c.execute("SELECT COUNT(*) FROM kpis")
    if c.fetchone()[0] == 0:
        c.executemany("""INSERT INTO kpis
            (code, nom, description, categorie, unite, formule, valeur_cible, seuil_alerte, frequence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('KPI-SPI', 'Schedule Performance Index', 'Performance délais', 'EVM', 'Ratio', 'EV / PV', 1.0, 0.9, 'Mensuel'),
            ('KPI-CPI', 'Cost Performance Index', 'Performance coûts', 'EVM', 'Ratio', 'EV / AC', 1.0, 0.9, 'Mensuel'),
            ('KPI-AVANC', 'Avancement global', 'Avancement physique', 'Délai', '%', 'EV / BAC * 100', 100, 90, 'Hebdomadaire'),
            ('KPI-MARGE', 'Marge projet', 'Marge financière', 'Finance', '%', '(CA - Coûts) / CA * 100', 20, 15, 'Mensuel'),
            ('KPI-QUAL', 'Taux de conformité', 'Non-conformités', 'Qualité', '%', 'Conformes / Total * 100', 98, 95, 'Hebdomadaire'),
            ('KPI-RISQ', 'Risques ouverts', 'Risques actifs', 'Risques', 'Nombre', 'COUNT(risques ouverts)', 0, 5, 'Hebdomadaire'),
            ('KPI-RENTAB', 'Rentabilité', 'ROI projet', 'Finance', '%', 'Bénéfice / Investissement * 100', 25, 15, 'Mensuel'),
        ])
        print("[MIGRATE v2] ✅ KPIs initialisés")

    conn.commit()
    conn.close()
    print("[MIGRATE v2] ✅ Migration terminée")


if __name__ == "__main__":
    migrate()
