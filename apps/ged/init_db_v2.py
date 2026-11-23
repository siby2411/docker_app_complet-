"""
Migration v2 GED
Tables additionnelles + Index + Triggers
"""
import sqlite3
import os

DB_PATH = "/app/data/ged.db"


def migrate():
    os.makedirs("/app/data", exist_ok=True)
    print("[MIGRATE v2] Démarrage...")

    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # ==================== 28. LOGS SYSTÈME ====================
    c.execute("""CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        niveau TEXT NOT NULL,
        composant TEXT,
        message TEXT NOT NULL,
        details TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 29. GROUPES UTILISATEURS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS groupes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS groupes_utilisateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        groupe_id INTEGER NOT NULL,
        utilisateur_id INTEGER NOT NULL,
        role_groupe TEXT DEFAULT 'membre',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (groupe_id) REFERENCES groupes(id),
        FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
        UNIQUE(groupe_id, utilisateur_id)
    )""")

    # ==================== 30. RECHERCHES SAUVEGARDÉES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS recherches_sauvegardees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        utilisateur_id INTEGER NOT NULL,
        nom TEXT NOT NULL,
        criteres TEXT NOT NULL,
        nb_resultats INTEGER DEFAULT 0,
        date_derniere_utilisation TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 31. RAPPORTS GÉNÉRÉS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS rapports_generes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        type_rapport TEXT NOT NULL,
        titre TEXT NOT NULL,
        parametres TEXT,
        fichier_chemin TEXT,
        format TEXT DEFAULT 'PDF',
        genere_par INTEGER,
        date_generation TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (genere_par) REFERENCES utilisateurs(id)
    )""")

    # ==================== 32. IMPORT EN MASSE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS imports_masse (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        type_import TEXT,
        nb_fichiers INTEGER DEFAULT 0,
        nb_succes INTEGER DEFAULT 0,
        nb_echecs INTEGER DEFAULT 0,
        statut TEXT DEFAULT 'En cours',
        fichier_log TEXT,
        user_id INTEGER,
        date_debut TEXT NOT NULL,
        date_fin TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES utilisateurs(id)
    )""")

    conn.commit()

    # ==================== INDEX PERFORMANCE ====================
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_dossiers_parent ON dossiers(parent_id)",
        "CREATE INDEX IF NOT EXISTS idx_dossiers_service ON dossiers(service_id)",
        "CREATE INDEX IF NOT EXISTS idx_dossiers_code ON dossiers(code)",
        "CREATE INDEX IF NOT EXISTS idx_documents_dossier ON documents(dossier_id)",
        "CREATE INDEX IF NOT EXISTS idx_documents_categorie ON documents(categorie_id)",
        "CREATE INDEX IF NOT EXISTS idx_documents_service ON documents(service_id)",
        "CREATE INDEX IF NOT EXISTS idx_documents_statut ON documents(statut)",
        "CREATE INDEX IF NOT EXISTS idx_documents_auteur ON documents(auteur_id)",
        "CREATE INDEX IF NOT EXISTS idx_documents_date ON documents(date_upload)",
        "CREATE INDEX IF NOT EXISTS idx_documents_confidentiel ON documents(confidentiel)",
        "CREATE INDEX IF NOT EXISTS idx_documents_destruction ON documents(date_destruction_prevue)",
        "CREATE INDEX IF NOT EXISTS idx_versions_document ON document_versions(document_id)",
        "CREATE INDEX IF NOT EXISTS idx_tags_nom ON tags(nom)",
        "CREATE INDEX IF NOT EXISTS idx_document_tags_doc ON document_tags(document_id)",
        "CREATE INDEX IF NOT EXISTS idx_metadonnees_doc ON metadonnees(document_id)",
        "CREATE INDEX IF NOT EXISTS idx_validations_doc ON validations(document_id)",
        "CREATE INDEX IF NOT EXISTS idx_validations_valideur ON validations(valideur_id)",
        "CREATE INDEX IF NOT EXISTS idx_consultations_doc ON consultations(document_id)",
        "CREATE INDEX IF NOT EXISTS idx_consultations_user ON consultations(utilisateur_id)",
        "CREATE INDEX IF NOT EXISTS idx_consultations_date ON consultations(date_consultation)",
        "CREATE INDEX IF NOT EXISTS idx_telechargements_doc ON telechargements(document_id)",
        "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_log(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity, entity_id)",
        "CREATE INDEX IF NOT EXISTS idx_cycle_vie_doc ON cycle_vie(document_id)",
        "CREATE INDEX IF NOT EXISTS idx_partages_token ON partages(lien_token)",
        "CREATE INDEX IF NOT EXISTS idx_permissions_user ON permissions(utilisateur_id)",
        "CREATE INDEX IF NOT EXISTS idx_permissions_doc ON permissions(document_id)",
    ]

    for idx in indexes:
        try:
            c.execute(idx)
        except Exception as e:
            print(f"[MIGRATE v2] ⚠️ Index : {e}")

    # ==================== VUES ====================
    # Vue : documents avec infos joints
    try:
        c.execute("""CREATE VIEW IF NOT EXISTS v_documents_complets AS
            SELECT d.*,
                   cat.nom as categorie_nom, cat.couleur as categorie_couleur,
                   dos.nom as dossier_nom, dos.chemin as dossier_chemin,
                   u.nom as auteur_nom, u.prenom as auteur_prenom,
                   s.nom as service_nom
            FROM documents d
            LEFT JOIN categories cat ON d.categorie_id = cat.id
            LEFT JOIN dossiers dos ON d.dossier_id = dos.id
            LEFT JOIN utilisateurs u ON d.auteur_id = u.id
            LEFT JOIN services s ON d.service_id = s.id
            WHERE d.actif = 1""")
        print("[MIGRATE v2] ✅ Vue v_documents_complets créée")
    except Exception as e:
        print(f"[MIGRATE v2] ⚠️ Vue documents : {e}")

    # Vue : statistiques par catégorie
    try:
        c.execute("""CREATE VIEW IF NOT EXISTS v_stats_categories AS
            SELECT cat.id, cat.nom, cat.couleur,
                   COUNT(d.id) as nb_documents,
                   COALESCE(SUM(d.fichier_taille_ko), 0) as taille_totale_ko
            FROM categories cat
            LEFT JOIN documents d ON d.categorie_id = cat.id AND d.actif = 1
            WHERE cat.actif = 1
            GROUP BY cat.id""")
        print("[MIGRATE v2] ✅ Vue v_stats_categories créée")
    except Exception as e:
        print(f"[MIGRATE v2] ⚠️ Vue stats : {e}")

    conn.commit()
    conn.close()
    print("[MIGRATE v2] ✅ Migration terminée")


if __name__ == "__main__":
    migrate()
