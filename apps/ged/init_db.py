"""
Base de données GED Omega
Conforme ISO 15489, NF Z42-013, RGPD — UEMOA
27 tables : dossiers, documents, versions, workflows, cycles de vie, audit
"""
import sqlite3
import os
import hashlib
from datetime import datetime, timedelta

DB_PATH = "/app/data/ged.db"


def sha256_file(filepath):
    """Calcule le SHA-256 d'un fichier (pour intégrité)"""
    try:
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ''


def init_db():
    os.makedirs("/app/data", exist_ok=True)
    os.makedirs("/app/data/documents", exist_ok=True)
    os.makedirs("/app/data/archives", exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    c = conn.cursor()

    # ==================== 1. SERVICES / DÉPARTEMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        responsable_id INTEGER,
        parent_id INTEGER,
        email TEXT,
        telephone TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES services(id)
    )""")

    # ==================== 2. CATÉGORIES DE DOCUMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        icone TEXT,
        couleur TEXT,
        duree_conservation_ans INTEGER DEFAULT 5,
        destruction_auto INTEGER DEFAULT 0,
        confidentiel INTEGER DEFAULT 0,
        ordre INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 3. TYPES DE DOCUMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS types_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        categorie_id INTEGER,
        extensions TEXT,
        taille_max_mb INTEGER DEFAULT 50,
        description TEXT,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (categorie_id) REFERENCES categories(id)
    )""")

    # ==================== 4. DOSSIERS (arborescence) ====================
    c.execute("""CREATE TABLE IF NOT EXISTS dossiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        parent_id INTEGER,
        categorie_id INTEGER,
        service_id INTEGER,
        chemin TEXT,
        niveau INTEGER DEFAULT 1,
        responsable_id INTEGER,
        confidentiel INTEGER DEFAULT 0,
        ordre INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES dossiers(id),
        FOREIGN KEY (categorie_id) REFERENCES categories(id),
        FOREIGN KEY (service_id) REFERENCES services(id),
        FOREIGN KEY (responsable_id) REFERENCES utilisateurs(id),
        FOREIGN KEY (created_by) REFERENCES utilisateurs(id)
    )""")

    # ==================== 5. DOCUMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        titre TEXT NOT NULL,
        description TEXT,
        dossier_id INTEGER,
        categorie_id INTEGER,
        type_document_id INTEGER,
        service_id INTEGER,
        auteur_id INTEGER,
        proprietaire_id INTEGER,
        fichier_nom TEXT NOT NULL,
        fichier_chemin TEXT NOT NULL,
        fichier_taille_ko REAL DEFAULT 0,
        mime_type TEXT,
        extension TEXT,
        sha256 TEXT,
        version_actuelle TEXT DEFAULT '1.0',
        nb_versions INTEGER DEFAULT 1,
        statut TEXT DEFAULT 'Brouillon',
        confidentiel INTEGER DEFAULT 0,
        mots_cles TEXT,
        langue TEXT DEFAULT 'Français',
        date_document TEXT,
        date_upload TEXT NOT NULL,
        date_modification TEXT,
        date_validation TEXT,
        date_publication TEXT,
        date_archivage TEXT,
        date_destruction_prevue TEXT,
        date_destruction_effective TEXT,
        valideur_id INTEGER,
        workflow_id INTEGER,
        etape_workflow INTEGER DEFAULT 0,
        nb_telechargements INTEGER DEFAULT 0,
        nb_consultations INTEGER DEFAULT 0,
        note_moyenne REAL DEFAULT 0,
        favori INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (dossier_id) REFERENCES dossiers(id),
        FOREIGN KEY (categorie_id) REFERENCES categories(id),
        FOREIGN KEY (type_document_id) REFERENCES types_documents(id),
        FOREIGN KEY (service_id) REFERENCES services(id),
        FOREIGN KEY (auteur_id) REFERENCES utilisateurs(id),
        FOREIGN KEY (proprietaire_id) REFERENCES utilisateurs(id),
        FOREIGN KEY (valideur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 6. VERSIONS DE DOCUMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS document_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        numero_version TEXT NOT NULL,
        fichier_nom TEXT NOT NULL,
        fichier_chemin TEXT NOT NULL,
        fichier_taille_ko REAL DEFAULT 0,
        sha256 TEXT,
        commentaire TEXT,
        auteur_id INTEGER,
        statut TEXT DEFAULT 'Active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES documents(id),
        FOREIGN KEY (auteur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 7. TAGS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT UNIQUE NOT NULL,
        couleur TEXT,
        nb_utilisations INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 8. DOCUMENT_TAGS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS document_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        tag_id INTEGER NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(id),
        FOREIGN KEY (tag_id) REFERENCES tags(id),
        UNIQUE(document_id, tag_id)
    )""")

    # ==================== 9. METADONNEES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS metadonnees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        cle TEXT NOT NULL,
        valeur TEXT,
        type TEXT DEFAULT 'texte',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES documents(id)
    )""")

    # ==================== 10. WORKFLOWS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS workflows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        categorie_id INTEGER,
        service_id INTEGER,
        nb_etapes INTEGER DEFAULT 1,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (categorie_id) REFERENCES categories(id),
        FOREIGN KEY (service_id) REFERENCES services(id)
    )""")

    # ==================== 11. ETAPES WORKFLOW ====================
    c.execute("""CREATE TABLE IF NOT EXISTS workflow_etapes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workflow_id INTEGER NOT NULL,
        ordre INTEGER NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        role_requis TEXT,
        utilisateur_id INTEGER,
        delai_jours INTEGER DEFAULT 0,
        obligatoire INTEGER DEFAULT 1,
        FOREIGN KEY (workflow_id) REFERENCES workflows(id),
        FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 12. VALIDATIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS validations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        workflow_id INTEGER,
        etape_id INTEGER,
        valideur_id INTEGER NOT NULL,
        date_validation TEXT NOT NULL,
        decision TEXT NOT NULL,
        commentaire TEXT,
        signature_hash TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES documents(id),
        FOREIGN KEY (workflow_id) REFERENCES workflows(id),
        FOREIGN KEY (etape_id) REFERENCES workflow_etapes(id),
        FOREIGN KEY (valideur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 13. SIGNATURES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS signatures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        signataire_id INTEGER NOT NULL,
        type_signature TEXT DEFAULT 'Simple',
        date_signature TEXT NOT NULL,
        hash_document TEXT,
        certificat TEXT,
        position_x REAL,
        position_y REAL,
        page INTEGER,
        statut TEXT DEFAULT 'Validée',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES documents(id),
        FOREIGN KEY (signataire_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 14. PARTAGES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS partages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        dossier_id INTEGER,
        type_partage TEXT DEFAULT 'Interne',
        destinataire_id INTEGER,
        destinataire_email TEXT,
        lien_token TEXT UNIQUE,
        mot_de_passe TEXT,
        date_creation TEXT NOT NULL,
        date_expiration TEXT,
        nb_acces INTEGER DEFAULT 0,
        nb_acces_max INTEGER DEFAULT 0,
        droits TEXT DEFAULT 'lecture',
        actif INTEGER DEFAULT 1,
        created_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES documents(id),
        FOREIGN KEY (dossier_id) REFERENCES dossiers(id),
        FOREIGN KEY (destinataire_id) REFERENCES utilisateurs(id),
        FOREIGN KEY (created_by) REFERENCES utilisateurs(id)
    )""")

    # ==================== 15. PERMISSIONS / ACL ====================
    c.execute("""CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        utilisateur_id INTEGER,
        role TEXT,
        service_id INTEGER,
        dossier_id INTEGER,
        document_id INTEGER,
        droits TEXT NOT NULL,
        date_debut TEXT,
        date_fin TEXT,
        actif INTEGER DEFAULT 1,
        created_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
        FOREIGN KEY (service_id) REFERENCES services(id),
        FOREIGN KEY (dossier_id) REFERENCES dossiers(id),
        FOREIGN KEY (document_id) REFERENCES documents(id)
    )""")

    # ==================== 16. CONSULTATIONS (audit RGPD) ====================
    c.execute("""CREATE TABLE IF NOT EXISTS consultations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        utilisateur_id INTEGER,
        action TEXT NOT NULL,
        ip TEXT,
        user_agent TEXT,
        duree_secondes INTEGER DEFAULT 0,
        date_consultation TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(id),
        FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 17. TELECHARGEMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS telechargements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        utilisateur_id INTEGER,
        version TEXT,
        ip TEXT,
        date_telechargement TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(id),
        FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 18. COMMENTAIRES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS commentaires (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        utilisateur_id INTEGER NOT NULL,
        commentaire TEXT NOT NULL,
        parent_id INTEGER,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES documents(id),
        FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
        FOREIGN KEY (parent_id) REFERENCES commentaires(id)
    )""")

    # ==================== 19. FAVORIS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS favoris (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        utilisateur_id INTEGER NOT NULL,
        document_id INTEGER,
        dossier_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
        FOREIGN KEY (document_id) REFERENCES documents(id),
        FOREIGN KEY (dossier_id) REFERENCES dossiers(id)
    )""")

    # ==================== 20. OCR / EXTRACTION TEXTE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS extractions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        type_extraction TEXT DEFAULT 'PDF',
        contenu_texte TEXT,
        langue TEXT DEFAULT 'Français',
        nb_pages INTEGER DEFAULT 0,
        confiance REAL DEFAULT 0,
        statut TEXT DEFAULT 'OK',
        date_extraction TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(id)
    )""")

    # ==================== 21. INDEX FULL-TEXT ====================
    c.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS recherche_fts USING fts5(
        document_id UNINDEXED,
        titre,
        description,
        contenu,
        mots_cles,
        tokenize='unicode61 remove_diacritics 2'
    )""")

    # ==================== 22. CYCLE DE VIE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS cycle_vie (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        phase TEXT NOT NULL,
        date_debut TEXT NOT NULL,
        date_fin TEXT,
        duree_jours INTEGER DEFAULT 0,
        responsable_id INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES documents(id),
        FOREIGN KEY (responsable_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 23. DEMANDES DE DESTRUCTION ====================
    c.execute("""CREATE TABLE IF NOT EXISTS demandes_destruction (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        document_id INTEGER NOT NULL,
        motif TEXT,
        demandeur_id INTEGER,
        date_demande TEXT NOT NULL,
        statut TEXT DEFAULT 'En attente',
        valideur_id INTEGER,
        date_validation TEXT,
        commentaire_validation TEXT,
        date_destruction_effective TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES documents(id),
        FOREIGN KEY (demandeur_id) REFERENCES utilisateurs(id),
        FOREIGN KEY (valideur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 24. NOTIFICATIONS ====================
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

    # ==================== 25. AUDIT LOG ====================
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

    # ==================== 26. STATISTIQUES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS statistiques (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_stat TEXT NOT NULL,
        nb_documents INTEGER DEFAULT 0,
        nb_dossiers INTEGER DEFAULT 0,
        espace_utilise_mb REAL DEFAULT 0,
        nb_uploads INTEGER DEFAULT 0,
        nb_telechargements INTEGER DEFAULT 0,
        nb_consultations INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 27. PARAMÈTRES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS parametres (
        cle TEXT PRIMARY KEY,
        valeur TEXT,
        description TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()

    # ==================== SEED ====================
    c.execute("SELECT COUNT(*) FROM services")
    if c.fetchone()[0] == 0:
        print("[INIT] Insertion des données de démonstration...")

        # SERVICES
        c.executemany("""INSERT INTO services (code, nom, description, email, telephone)
            VALUES (?, ?, ?, ?, ?)""", [
            ('DIR', 'Direction Générale', 'Direction et stratégie', 'dg@omega-ged.sn', '+221 33 800 00 01'),
            ('RH', 'Ressources Humaines', 'Gestion du personnel', 'rh@omega-ged.sn', '+221 33 800 00 02'),
            ('FIN', 'Finance & Comptabilité', 'Gestion financière', 'fin@omega-ged.sn', '+221 33 800 00 03'),
            ('JUR', 'Service Juridique', 'Contrats et contentieux', 'jur@omega-ged.sn', '+221 33 800 00 04'),
            ('TECH', 'Technique & IT', 'Support et informatique', 'tech@omega-ged.sn', '+221 33 800 00 05'),
            ('COM', 'Commercial & Marketing', 'Ventes et marketing', 'com@omega-ged.sn', '+221 33 800 00 06'),
            ('QUAL', 'Qualité & Conformité', 'Contrôle qualité', 'qual@omega-ged.sn', '+221 33 800 00 07'),
            ('ARCH', 'Service des Archives', 'Gestion documentaire', 'arch@omega-ged.sn', '+221 33 800 00 08'),
        ])

        # CATÉGORIES
        c.executemany("""INSERT INTO categories
            (code, nom, description, icone, couleur, duree_conservation_ans, destruction_auto, confidentiel, ordre)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('ADMIN', 'Administratif', 'Documents administratifs', 'fa-folder-open', '#0e7490', 10, 0, 0, 1),
            ('JUR', 'Juridique', 'Contrats, actes, jugements', 'fa-gavel', '#1e40af', 30, 0, 1, 2),
            ('FIN', 'Finance & Comptabilité', 'Factures, bilans, paiements', 'fa-chart-line', '#059669', 10, 0, 1, 3),
            ('RH', 'Ressources Humaines', 'Contrats, fiches de paie', 'fa-users', '#7c3aed', 30, 0, 1, 4),
            ('TECH', 'Technique', 'Plans, schémas, notes', 'fa-cogs', '#0891b2', 15, 0, 0, 5),
            ('COM', 'Commercial', 'Devis, contrats clients', 'fa-handshake', '#dc2626', 5, 0, 0, 6),
            ('QUAL', 'Qualité', 'Procédures, audits', 'fa-clipboard-check', '#f59e0b', 10, 0, 0, 7),
            ('STRAT', 'Stratégie', 'Plans stratégiques', 'fa-chess', '#6b21a8', 20, 0, 1, 8),
            ('ARCH', 'Archives définitives', 'Documents à conserver', 'fa-archive', '#78350f', 100, 0, 0, 9),
            ('TEMP', 'Temporaire', 'Documents à détruire', 'fa-clock', '#64748b', 1, 1, 0, 10),
        ])

        # TYPES DE DOCUMENTS
        c.executemany("""INSERT INTO types_documents (code, nom, categorie_id, extensions, taille_max_mb)
            VALUES (?, ?, ?, ?, ?)""", [
            ('PDF', 'Document PDF', 1, 'pdf', 100),
            ('DOCX', 'Document Word', 1, 'docx,doc', 50),
            ('XLSX', 'Tableur Excel', 1, 'xlsx,xls', 50),
            ('IMG', 'Image', 1, 'jpg,jpeg,png,gif,svg', 20),
            ('VIDEO', 'Vidéo', 1, 'mp4,avi,mov', 500),
            ('AUDIO', 'Audio', 1, 'mp3,wav,ogg', 100),
            ('ZIP', 'Archive ZIP', 1, 'zip,rar,7z,tar,gz', 200),
            ('DWG', 'Plan technique', 5, 'dwg,dxf', 100),
            ('CONTRAT', 'Contrat signé', 2, 'pdf,docx', 50),
            ('FACTURE', 'Facture', 3, 'pdf,xlsx', 50),
        ])

        # WORKFLOWS
        c.executemany("""INSERT INTO workflows (code, nom, description, categorie_id, nb_etapes)
            VALUES (?, ?, ?, ?, ?)""", [
            ('WF-CONTRAT', 'Validation contrat', 'Direction → Juridique → Signature', 2, 3),
            ('WF-FACTURE', 'Validation facture', 'Comptable → DAF → Paiement', 3, 3),
            ('WF-PROC', 'Validation procédure', 'Rédaction → Qualité → Publication', 7, 3),
            ('WF-RH', 'Validation RH', 'RH → DRH → Signature DG', 4, 3),
        ])

        # DOSSIERS (arborescence)
        dossiers_data = [
            ('DOS-001', 'Direction Générale', 'Documents DG', None, 1, 1, 'DG', 1, 1, 0),
            ('DOS-001-001', 'Conseils d\'administration', 'PV CA', 1, 1, 1, 'DG', 2, 1, 0),
            ('DOS-001-002', 'Stratégie', 'Plans stratégiques', 1, 8, 1, 'DG', 2, 1, 1),
            ('DOS-002', 'Ressources Humaines', 'Documents RH', None, 4, 2, 'RH', 1, 1, 1),
            ('DOS-002-001', 'Contrats de travail', 'CDI/CDD', 4, 4, 2, 'RH', 2, 1, 1),
            ('DOS-002-002', 'Fiches de paie', 'Bulletins', 4, 4, 2, 'RH', 2, 1, 1),
            ('DOS-002-003', 'Congés', 'Demandes et validations', 4, 4, 2, 'RH', 2, 1, 0),
            ('DOS-003', 'Finance', 'Documents financiers', None, 3, 3, 'FIN', 1, 1, 1),
            ('DOS-003-001', 'Factures fournisseurs', 'Achats', 3, 3, 3, 'FIN', 2, 1, 1),
            ('DOS-003-002', 'Bilans annuels', 'Comptes', 3, 3, 3, 'FIN', 2, 1, 1),
            ('DOS-004', 'Juridique', 'Documents légaux', None, 2, 4, 'JUR', 1, 1, 1),
            ('DOS-004-001', 'Contrats clients', 'Contrats commerciaux', 2, 2, 4, 'JUR', 2, 1, 1),
            ('DOS-004-002', 'Contentieux', 'Litiges', 2, 2, 4, 'JUR', 2, 1, 1),
            ('DOS-005', 'Technique', 'Documents techniques', None, 5, 5, 'TECH', 1, 1, 0),
            ('DOS-005-001', 'Plans BTP', 'Plans architecturaux', 5, 5, 5, 'TECH', 2, 1, 0),
            ('DOS-006', 'Commercial', 'Documents commerciaux', None, 6, 6, 'COM', 1, 1, 0),
            ('DOS-007', 'Qualité', 'Documents qualité', None, 7, 7, 'QUAL', 1, 1, 0),
            ('DOS-008', 'Archives', 'Archives définitives', None, 9, 8, 'ARCH', 1, 1, 0),
        ]
        for d in dossiers_data:
            c.execute("""INSERT INTO dossiers
                (code, nom, description, parent_id, categorie_id, service_id, chemin, niveau, responsable_id, ordre, confidentiel)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", d)

        # TAGS
        c.executemany("INSERT INTO tags (nom, couleur) VALUES (?, ?)", [
            ('urgent', '#dc2626'),
            ('important', '#f59e0b'),
            ('archivé', '#64748b'),
            ('confidentiel', '#991b1b'),
            ('signé', '#10b981'),
            ('à valider', '#0891b2'),
            ('2026', '#7c3aed'),
            ('contrat', '#1e40af'),
            ('facture', '#059669'),
            ('RH', '#a855f7'),
        ])

        # PARAMÈTRES
        c.executemany("INSERT INTO parametres (cle, valeur, description) VALUES (?, ?, ?)", [
            ('organisme_nom', 'OMEGA CONSULTING', 'Nom de l\'organisme'),
            ('organisme_nif', 'SN-123456789', 'NIF'),
            ('duree_conservation_defaut', '10', 'Durée de conservation par défaut (ans)'),
            ('duree_archivage_intermediaire', '5', 'Durée d\'archivage intermédiaire (ans)'),
            ('destruction_auto_actif', '1', 'Destruction automatique activée'),
            ('confidentialite_defaut', '0', 'Confidentialité par défaut'),
            ('taille_max_upload_mb', '100', 'Taille max upload (Mo)'),
            ('extensions_autorisees', 'pdf,docx,xlsx,pptx,jpg,png,gif,zip,dwg,mp4,mp3', 'Extensions autorisées'),
            ('iso_norme', 'ISO 15489 / NF Z42-013', 'Normes appliquées'),
            ('rgpd_actif', '1', 'Conformité RGPD'),
        ])

        conn.commit()
        print("[INIT] ✅ Données de démonstration insérées")

    conn.close()
    print("[INIT] ✅ Base de données GED prête")


if __name__ == "__main__":
    init_db()
