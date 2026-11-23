"""
🌾 Omega Agro-Industrie — Base de données
55 tables — Projet SM10 AGRO · Sadio Mané
Conforme HACCP, ISO 22000, normes UE, APIX
"""
import sqlite3
import hashlib
from datetime import datetime, timedelta

DB_PATH = "/app/data/agro.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=MEMORY")
    return conn


def init_db():
    print(f"[INIT] Base : {DB_PATH}")
    conn = get_conn()
    c = conn.cursor()

    # ================================================================
    # RÉFÉRENTIEL (8 tables)
    # ================================================================
    c.execute("""CREATE TABLE IF NOT EXISTS pays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        continent TEXT,
        actif INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS regions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pays_id INTEGER,
        code TEXT NOT NULL,
        nom TEXT NOT NULL,
        FOREIGN KEY (pays_id) REFERENCES pays(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type TEXT DEFAULT 'Usine',
        adresse TEXT,
        ville TEXT,
        region_id INTEGER,
        superficie_m2 REAL,
        capacite_t_jour REAL,
        responsable_id INTEGER,
        telephone TEXT,
        email TEXT,
        gps_latitude REAL,
        gps_longitude REAL,
        date_ouverture TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (region_id) REFERENCES regions(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS departements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        site_id INTEGER,
        responsable_id INTEGER,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS postes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        departement_id INTEGER,
        salaire_base INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (departement_id) REFERENCES departements(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS employes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        matricule TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        sexe TEXT,
        date_naissance TEXT,
        telephone TEXT,
        email TEXT,
        adresse TEXT,
        poste_id INTEGER,
        departement_id INTEGER,
        site_id INTEGER,
        date_embauche TEXT,
        type_contrat TEXT DEFAULT 'CDI',
        salaire_base INTEGER DEFAULT 0,
        numero_cnss TEXT,
        numero_cni TEXT,
        photo_path TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (poste_id) REFERENCES postes(id),
        FOREIGN KEY (departement_id) REFERENCES departements(id),
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS fournisseurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type TEXT,
        contact_nom TEXT,
        telephone TEXT,
        email TEXT,
        adresse TEXT,
        ville TEXT,
        pays TEXT DEFAULT 'Sénégal',
        produits_fournis TEXT,
        numero_ninea TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS clients_b2b (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type TEXT,
        pays TEXT,
        contact_nom TEXT,
        telephone TEXT,
        email TEXT,
        adresse TEXT,
        produits_recherches TEXT,
        volume_annuel_t REAL,
        certifications_requises TEXT,
        mode_paiement TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ================================================================
    # PRODUCTEURS & APPROVISIONNEMENT (6 tables)
    # ================================================================
    c.execute("""CREATE TABLE IF NOT EXISTS producteurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT,
        sexe TEXT,
        telephone TEXT,
        email TEXT,
        adresse TEXT,
        village TEXT,
        region_id INTEGER,
        gps_latitude REAL,
        gps_longitude REAL,
        superficie_ha REAL DEFAULT 0,
        type_exploitation TEXT DEFAULT 'Familiale',
        produits_agricoles TEXT,
        numero_cnss TEXT,
        numero_cni TEXT,
        cooperative_id INTEGER,
        mobile_money_type TEXT,
        mobile_money_numero TEXT,
        certifications TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (region_id) REFERENCES regions(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS parcelles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        producteur_id INTEGER,
        nom TEXT,
        superficie_ha REAL,
        gps_latitude REAL,
        gps_longitude REAL,
        type_sol TEXT,
        cultures_principales TEXT,
        irrigation_disponible INTEGER DEFAULT 0,
        certification_bio INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS recoltes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        producteur_id INTEGER,
        parcelle_id INTEGER,
        produit TEXT NOT NULL,
        variete TEXT,
        date_recolte TEXT,
        quantite_kg REAL,
        qualite TEXT,
        taux_humidite REAL,
        prix_kg INTEGER,
        destination TEXT,
        statut TEXT DEFAULT 'Disponible',
        photo_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id),
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS contrats_achat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        producteur_id INTEGER,
        produit TEXT,
        quantite_kg REAL,
        prix_kg INTEGER,
        montant_total INTEGER,
        date_signature TEXT,
        date_livraison_prevue TEXT,
        date_livraison_reelle TEXT,
        statut TEXT DEFAULT 'Actif',
        conditions TEXT,
        document_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS livraisons_producteurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        contrat_id INTEGER,
        producteur_id INTEGER,
        produit TEXT,
        quantite_kg REAL,
        qualite TEXT,
        date_livraison TEXT,
        poids_brut_kg REAL,
        poids_net_kg REAL,
        prix_kg INTEGER,
        montant_total INTEGER,
        mode_paiement TEXT,
        statut_paiement TEXT DEFAULT 'En attente',
        date_paiement TEXT,
        receptionnaire_id INTEGER,
        site_id INTEGER,
        observations TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (contrat_id) REFERENCES contrats_achat(id),
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id),
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cooperatives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type TEXT,
        village TEXT,
        region_id INTEGER,
        responsable_nom TEXT,
        telephone TEXT,
        nb_membres INTEGER DEFAULT 0,
        produits TEXT,
        numero_agrement TEXT,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (region_id) REFERENCES regions(id)
    )""")

    # ================================================================
    # PRODUITS FINIS (4 tables)
    # ================================================================
    c.execute("""CREATE TABLE IF NOT EXISTS produits_finis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        categorie TEXT,
        sous_categorie TEXT,
        description TEXT,
        matiere_premiere TEXT,
        unite TEXT DEFAULT 'kg',
        poids_unitaire_g REAL,
        conditionnement TEXT,
        duree_conservation_mois INTEGER,
        temperature_conservation TEXT,
        certifications TEXT,
        prix_revient INTEGER,
        prix_vente INTEGER,
        marge_pct REAL,
        code_sh TEXT,
        photo_path TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS stocks_produits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER NOT NULL,
        site_id INTEGER,
        lot TEXT,
        date_fabrication TEXT,
        date_peremption TEXT,
        quantite_kg REAL DEFAULT 0,
        quantite_reservee REAL DEFAULT 0,
        emplacement TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produit_id) REFERENCES produits_finis(id),
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS prix_marche (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit TEXT,
        marche TEXT,
        pays TEXT,
        date_releve TEXT,
        prix_min INTEGER,
        prix_moyen INTEGER,
        prix_max INTEGER,
        unite TEXT DEFAULT 'kg',
        devise TEXT DEFAULT 'FCFA',
        tendance TEXT,
        source TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS concurrents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        pays TEXT,
        produits TEXT,
        marches TEXT,
        prix_moyen INTEGER,
        certifications TEXT,
        notes TEXT,
        actif INTEGER DEFAULT 1
    )""")

    # ================================================================
    # PRODUCTION / TRANSFORMATION (10 tables)
    # ================================================================
    c.execute("""CREATE TABLE IF NOT EXISTS lignes_production (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        site_id INTEGER,
        produit_fini_id INTEGER,
        capacite_kg_heure REAL,
        statut TEXT DEFAULT 'Active',
        date_mise_service TEXT,
        FOREIGN KEY (site_id) REFERENCES sites(id),
        FOREIGN KEY (produit_fini_id) REFERENCES produits_finis(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ordres_fabrication (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        ligne_id INTEGER,
        produit_fini_id INTEGER,
        quantite_kg REAL NOT NULL,
        matiere_premiere_kg REAL,
        date_debut TEXT,
        date_fin_prevue TEXT,
        date_fin_reelle TEXT,
        lot_production TEXT,
        statut TEXT DEFAULT 'Planifié',
        responsable_id INTEGER,
        cout_matiere INTEGER DEFAULT 0,
        cout_main_oeuvre INTEGER DEFAULT 0,
        cout_energie INTEGER DEFAULT 0,
        cout_emballage INTEGER DEFAULT 0,
        cout_total INTEGER DEFAULT 0,
        rendement_pct REAL,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ligne_id) REFERENCES lignes_production(id),
        FOREIGN KEY (produit_fini_id) REFERENCES produits_finis(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS etapes_production (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ordre_id INTEGER,
        numero_etape INTEGER,
        nom_etape TEXT,
        description TEXT,
        duree_minutes INTEGER,
        temperature_c REAL,
        humidite_pct REAL,
        operateur_id INTEGER,
        date_debut TEXT,
        date_fin TEXT,
        statut TEXT DEFAULT 'En attente',
        FOREIGN KEY (ordre_id) REFERENCES ordres_fabrication(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS matieres_premieres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        categorie TEXT,
        type TEXT,
        unite TEXT DEFAULT 'kg',
        prix_unitaire INTEGER,
        fournisseur_id INTEGER,
        stock_kg REAL DEFAULT 0,
        seuil_alerte_kg REAL DEFAULT 100,
        date_peremption TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS consommations_mp (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ordre_id INTEGER,
        matiere_id INTEGER,
        quantite_kg REAL,
        date_consommation TEXT,
        cout INTEGER,
        FOREIGN KEY (ordre_id) REFERENCES ordres_fabrication(id),
        FOREIGN KEY (matiere_id) REFERENCES matieres_premieres(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS equipements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type TEXT,
        site_id INTEGER,
        marque TEXT,
        modele TEXT,
        numero_serie TEXT,
        date_installation TEXT,
        duree_vie_ans INTEGER,
        capacite TEXT,
        consommation_kw REAL,
        cout_acquisition INTEGER,
        statut TEXT DEFAULT 'Opérationnel',
        prochaine_maintenance TEXT,
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS maintenances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipement_id INTEGER,
        type TEXT,
        date_debut TEXT,
        date_fin TEXT,
        description TEXT,
        technicien TEXT,
        cout_pieces INTEGER DEFAULT 0,
        cout_main_oeuvre INTEGER DEFAULT 0,
        cout_total INTEGER DEFAULT 0,
        statut TEXT DEFAULT 'Terminée',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (equipement_id) REFERENCES equipements(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS energetique (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        site_id INTEGER,
        date_releve TEXT,
        electricite_kwh REAL,
        eau_m3 REAL,
        gasoil_l REAL,
        solaire_kwh REAL,
        cout_total INTEGER DEFAULT 0,
        production_kg REAL,
        cout_par_kg REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS panneaux_solaires (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        site_id INTEGER,
        marque TEXT,
        puissance_kwc REAL,
        nb_panneaux INTEGER,
        onduleur TEXT,
        capacite_batterie_kwh REAL,
        date_installation TEXT,
        production_jour_kwh REAL,
        statut TEXT DEFAULT 'Opérationnel',
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS dechets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        site_id INTEGER,
        date_releve TEXT,
        type_dechet TEXT,
        quantite_kg REAL,
        destination TEXT,
        valorisation TEXT,
        cout_traitement INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    # ================================================================
    # QUALITÉ / HACCP / ISO 22000 (7 tables)
    # ================================================================
    c.execute("""CREATE TABLE IF NOT EXISTS controles_qualite (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        ordre_id INTEGER,
        produit_fini_id INTEGER,
        lot TEXT,
        date_controle TEXT,
        controleur_id INTEGER,
        type_controle TEXT,
        parametre TEXT,
        valeur_mesuree REAL,
        valeur_cible REAL,
        tolerance REAL,
        resultat TEXT DEFAULT 'Conforme',
        observations TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ordre_id) REFERENCES ordres_fabrication(id),
        FOREIGN KEY (produit_fini_id) REFERENCES produits_finis(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS analyses_labo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        produit_id INTEGER,
        lot TEXT,
        date_analyse TEXT,
        laboratoire TEXT,
        type_analyse TEXT,
        parametres_json TEXT,
        resultat TEXT,
        conformite TEXT DEFAULT 'Conforme',
        fichier_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produit_id) REFERENCES produits_finis(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS non_conformites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        produit_id INTEGER,
        lot TEXT,
        date_detection TEXT,
        type_nc TEXT,
        gravite TEXT,
        description TEXT,
        cause_racine TEXT,
        action_corrective TEXT,
        responsable_id INTEGER,
        date_cloture TEXT,
        statut TEXT DEFAULT 'Ouverte',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produit_id) REFERENCES produits_finis(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS certifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        organisme TEXT,
        type TEXT,
        date_obtention TEXT,
        date_expiration TEXT,
        portee TEXT,
        fichier_path TEXT,
        statut TEXT DEFAULT 'Active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS audits_qualite (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        type_audit TEXT,
        norme TEXT,
        date_audit TEXT,
        auditeur TEXT,
        organisme TEXT,
        perimetre TEXT,
        conclusion TEXT,
        score INTEGER,
        fichier_path TEXT,
        statut TEXT DEFAULT 'Réalisé',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS tracabilite (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code_qr TEXT UNIQUE NOT NULL,
        produit_fini_id INTEGER,
        lot TEXT,
        producteur_id INTEGER,
        parcelle_id INTEGER,
        date_recolte TEXT,
        date_reception TEXT,
        date_transformation TEXT,
        date_conditionnement TEXT,
        date_expedition TEXT,
        destination TEXT,
        temperature_chaine TEXT,
        donnees_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produit_fini_id) REFERENCES produits_finis(id),
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS scans_qr (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracabilite_id INTEGER,
        date_scan TEXT,
        type_scan TEXT,
        lieu TEXT,
        latitude REAL,
        longitude REAL,
        ip_source TEXT,
        user_agent TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tracabilite_id) REFERENCES tracabilite(id)
    )""")

    # ================================================================
    # EXPORT / DOUANES (6 tables)
    # ================================================================
    c.execute("""CREATE TABLE IF NOT EXISTS exports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        client_id INTEGER,
        pays_destination TEXT,
        port_embarquement TEXT,
        produit_id INTEGER,
        quantite_kg REAL,
        prix_unitaire INTEGER,
        montant_total INTEGER,
        devise TEXT DEFAULT 'EUR',
        incoterm TEXT,
        date_commande TEXT,
        date_expedition TEXT,
        date_arrivee_prevue TEXT,
        transporteur TEXT,
        numero_conteneur TEXT,
        statut TEXT DEFAULT 'En préparation',
        documents_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients_b2b(id),
        FOREIGN KEY (produit_id) REFERENCES produits_finis(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS documents_export (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        export_id INTEGER,
        type_document TEXT,
        numero TEXT,
        date_emission TEXT,
        fichier_path TEXT,
        statut TEXT DEFAULT 'Émis',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (export_id) REFERENCES exports(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS douanes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        export_id INTEGER,
        type_declaration TEXT,
        bureau_douane TEXT,
        numero_declaration TEXT,
        date_declaration TEXT,
        droits_douane INTEGER DEFAULT 0,
        tva INTEGER DEFAULT 0,
        taxes_autres INTEGER DEFAULT 0,
        exoneration INTEGER DEFAULT 0,
        motif_exoneration TEXT,
        reference_apix TEXT,
        statut TEXT DEFAULT 'En cours',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (export_id) REFERENCES exports(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS transports_internationaux (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        export_id INTEGER,
        type_transport TEXT,
        compagnie TEXT,
        numero_vol_navire TEXT,
        date_depart TEXT,
        date_arrivee TEXT,
        cout_transport INTEGER,
        numero_connaissement TEXT,
        statut TEXT DEFAULT 'Réservé',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (export_id) REFERENCES exports(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS reglementations_ue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        produit TEXT,
        pays TEXT,
        norme TEXT,
        description TEXT,
        limites_json TEXT,
        methode_analyse TEXT,
        actif INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS certificats_sanitaires (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        export_id INTEGER,
        type_certificat TEXT,
        organisme TEXT,
        date_emission TEXT,
        date_expiration TEXT,
        numero_certificat TEXT,
        fichier_path TEXT,
        statut TEXT DEFAULT 'Valide',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (export_id) REFERENCES exports(id)
    )""")

    # ================================================================
    # FORMATION (4 tables)
    # ================================================================
    c.execute("""CREATE TABLE IF NOT EXISTS formations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        categorie TEXT,
        description TEXT,
        duree_jours INTEGER,
        niveau TEXT,
        pre_requis TEXT,
        objectifs TEXT,
        formateur_id INTEGER,
        cout_participant INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sessions_formation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        formation_id INTEGER,
        date_debut TEXT,
        date_fin TEXT,
        lieu TEXT,
        site_id INTEGER,
        formateur_id INTEGER,
        capacite_max INTEGER DEFAULT 20,
        nb_inscrits INTEGER DEFAULT 0,
        statut TEXT DEFAULT 'Planifiée',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (formation_id) REFERENCES formations(id),
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS participants_formation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        participant_type TEXT,
        employe_id INTEGER,
        producteur_id INTEGER,
        nom_externe TEXT,
        telephone TEXT,
        date_inscription TEXT,
        presence INTEGER DEFAULT 0,
        note_finale REAL,
        attestation INTEGER DEFAULT 0,
        statut TEXT DEFAULT 'Inscrit',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions_formation(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS attestations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_attestation TEXT UNIQUE NOT NULL,
        participant_id INTEGER,
        formation_id INTEGER,
        date_emission TEXT,
        date_expiration TEXT,
        score REAL,
        fichier_path TEXT,
        code_qr TEXT UNIQUE,
        statut TEXT DEFAULT 'Valide',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (participant_id) REFERENCES participants_formation(id),
        FOREIGN KEY (formation_id) REFERENCES formations(id)
    )""")

    # ================================================================
    # FINANCE (5 tables)
    # ================================================================
    c.execute("""CREATE TABLE IF NOT EXISTS financements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        source TEXT,
        type_financement TEXT,
        montant INTEGER,
        devise TEXT DEFAULT 'FCFA',
        objet TEXT,
        date_accord TEXT,
        date_decaissement TEXT,
        duree_mois INTEGER,
        taux REAL DEFAULT 0,
        montant_rembourse INTEGER DEFAULT 0,
        solde_restant INTEGER,
        statut TEXT DEFAULT 'Actif',
        document_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS echeances_financement (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        financement_id INTEGER,
        numero_echeance INTEGER,
        date_echeance TEXT,
        montant_capital INTEGER,
        montant_interets INTEGER,
        montant_total INTEGER,
        montant_paye INTEGER DEFAULT 0,
        date_paiement TEXT,
        statut TEXT DEFAULT 'À venir',
        FOREIGN KEY (financement_id) REFERENCES financements(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS exoneration_apix (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        type_exoneration TEXT,
        materiel_concerne TEXT,
        montant_materiel INTEGER,
        montant_exonere INTEGER,
        date_debut TEXT,
        date_fin TEXT,
        duree_ans INTEGER DEFAULT 5,
        statut TEXT DEFAULT 'En cours',
        numero_agrement TEXT,
        fichier_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS subventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        programme TEXT,
        bailleur TEXT,
        montant INTEGER,
        objet TEXT,
        date_attribution TEXT,
        date_decaissement TEXT,
        statut TEXT DEFAULT 'En cours',
        conditions TEXT,
        document_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS factures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        type_facture TEXT,
        tiers_type TEXT,
        tiers_id INTEGER,
        tiers_nom TEXT,
        date_facture TEXT,
        date_echeance TEXT,
        montant_ht INTEGER,
        tva_pct REAL DEFAULT 18,
        montant_tva INTEGER,
        montant_ttc INTEGER,
        mode_paiement TEXT,
        statut TEXT DEFAULT 'Émise',
        date_paiement TEXT,
        document_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ================================================================
    # SYSTÈME (5 tables)
    # ================================================================
    c.execute("""CREATE TABLE IF NOT EXISTS utilisateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nom TEXT,
        prenom TEXT,
        email TEXT,
        telephone TEXT,
        role TEXT DEFAULT 'operateur',
        site_id INTEGER,
        employe_id INTEGER,
        actif INTEGER DEFAULT 1,
        dernier_login TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

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

    c.execute("""CREATE TABLE IF NOT EXISTS parametres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cle TEXT UNIQUE NOT NULL,
        valeur TEXT,
        type TEXT,
        description TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        destinataire_id INTEGER,
        type TEXT,
        canal TEXT DEFAULT 'app',
        titre TEXT,
        message TEXT,
        lu INTEGER DEFAULT 0,
        date_lecture TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS alertes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_alerte TEXT,
        gravite TEXT DEFAULT 'Info',
        titre TEXT NOT NULL,
        message TEXT,
        entity TEXT,
        entity_id INTEGER,
        statut TEXT DEFAULT 'Active',
        traitee_par INTEGER,
        date_traitement TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Index
    c.execute("CREATE INDEX IF NOT EXISTS idx_recoltes_producteur ON recoltes(producteur_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_livraisons_producteur ON livraisons_producteurs(producteur_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_of_statut ON ordres_fabrication(statut)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_exports_statut ON exports(statut)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tracabilite_lot ON tracabilite(lot)")

    conn.commit()

    # ==================== DONNÉES DÉMO ====================
    c.execute("SELECT COUNT(*) FROM sites")
    if c.fetchone()[0] == 0:
        print("[INIT] Insertion données démo SM10 AGRO...")
        _seed_data(c)
        conn.commit()

    conn.close()
    print(f"[INIT] ✅ Base prête : {DB_PATH}")


def _seed_data(c):
    """Données de démonstration basées sur SM10 AGRO"""
    year = datetime.now().year

    # ============ PAYS ============
    pays_list = [
        ('SN', 'Sénégal', 'Afrique'),
        ('FR', 'France', 'Europe'),
        ('DE', 'Allemagne', 'Europe'),
        ('BE', 'Belgique', 'Europe'),
        ('NL', 'Pays-Bas', 'Europe'),
        ('ES', 'Espagne', 'Europe'),
        ('IT', 'Italie', 'Europe'),
        ('MA', 'Maroc', 'Afrique'),
        ('US', 'États-Unis', 'Amérique'),
    ]
    for code, nom, cont in pays_list:
        c.execute("INSERT INTO pays (code, nom, continent) VALUES (?,?,?)", (code, nom, cont))

    # ============ RÉGIONS SÉNÉGAL ============
    regions_list = [
        (1, 'DKR', 'Dakar'), (1, 'THS', 'Thiès'), (1, 'DBL', 'Diourbel'),
        (1, 'FTK', 'Fatick'), (1, 'KLC', 'Kaolack'), (1, 'KFL', 'Kaffrine'),
        (1, 'SLS', 'Saint-Louis'), (1, 'LOU', 'Louga'), (1, 'MTM', 'Matam'),
        (1, 'TMB', 'Tambacounda'), (1, 'KDG', 'Kédougou'), (1, 'KOL', 'Kolda'),
        (1, 'ZIG', 'Ziguinchor'), (1, 'SED', 'Sédhiou'),
    ]
    for pays_id, code, nom in regions_list:
        c.execute("INSERT INTO regions (pays_id, code, nom) VALUES (?,?,?)", (pays_id, code, nom))

    # ============ SITES / USINES ============
    sites = [
        ('USN-001', 'Usine SM10 Bambali', 'Usine principale', 'Bambali', 'Bambali', 14, 12000, 50.0),
        ('USN-002', 'Usine Ziguinchor', 'Usine régionale', 'Zone industrielle', 'Ziguinchor', 13, 8000, 30.0),
        ('USN-003', 'Centre Formation Bambali', 'Centre formation', 'Bambali', 'Bambali', 14, 2000, 0),
        ('USN-004', 'Entrepôt Dakar Port', 'Entrepôt export', 'Port de Dakar', 'Dakar', 1, 3000, 0),
    ]
    for code, nom, typ, adr, ville, reg_id, sup, cap in sites:
        c.execute("""INSERT INTO sites (code, nom, type, adresse, ville, region_id, superficie_m2, capacite_t_jour, date_ouverture)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (code, nom, typ, adr, ville, reg_id, sup, cap, f'{year}-01-15'))

    # ============ DÉPARTEMENTS ============
    deps = [
        ('DIR', 'Direction', 1), ('PROD', 'Production', 1), ('QUAL', 'Qualité', 1),
        ('LOG', 'Logistique', 1), ('EXP', 'Export', 1), ('FORM', 'Formation', 3),
        ('MAINT', 'Maintenance', 1), ('ADMIN', 'Administration', 1),
    ]
    for code, nom, site_id in deps:
        c.execute("INSERT INTO departements (code, nom, site_id) VALUES (?,?,?)", (code, nom, site_id))

    # ============ POSTES ============
    postes = [
        ('DG', 'Directeur Général', 1, 2000000),
        ('DPROD', 'Directeur Production', 2, 1200000),
        ('DQUAL', 'Directeur Qualité', 3, 1000000),
        ('CHEF_LIGNE', 'Chef de ligne', 2, 500000),
        ('OPERATEUR', 'Opérateur production', 2, 200000),
        ('CONTROLEUR', 'Contrôleur qualité', 3, 350000),
        ('MAGASINIER', 'Magasinier', 4, 250000),
        ('TECH', 'Technicien maintenance', 7, 400000),
        ('FORMATEUR', 'Formateur', 6, 500000),
        ('COMMERCIAL', 'Commercial export', 5, 600000),
    ]
    for code, nom, dep_id, sal in postes:
        c.execute("INSERT INTO postes (code, nom, departement_id, salaire_base) VALUES (?,?,?,?)",
                  (code, nom, dep_id, sal))

    # ============ EMPLOYÉS ============
    employes = [
        ('EMP0001', 'Diop', 'Mamadou', 'M', 1, 1, 1, 2000000),
        ('EMP0002', 'Ndiaye', 'Fatou', 'F', 2, 2, 1, 1200000),
        ('EMP0003', 'Fall', 'Omar', 'M', 3, 3, 1, 1000000),
        ('EMP0004', 'Sow', 'Aminata', 'F', 4, 2, 1, 500000),
        ('EMP0005', 'Ba', 'Ibrahima', 'M', 5, 2, 1, 200000),
        ('EMP0006', 'Diallo', 'Awa', 'F', 5, 2, 1, 200000),
        ('EMP0007', 'Sarr', 'Cheikh', 'M', 6, 3, 1, 350000),
        ('EMP0008', 'Kane', 'Mariama', 'F', 7, 4, 1, 250000),
        ('EMP0009', 'Gueye', 'Abdoulaye', 'M', 8, 7, 1, 400000),
        ('EMP0010', 'Sylla', 'Kadidiatou', 'F', 9, 6, 3, 500000),
        ('EMP0011', 'Cisse', 'Moussa', 'M', 10, 5, 1, 600000),
        ('EMP0012', 'Barry', 'Alpha', 'M', 5, 2, 1, 200000),
        ('EMP0013', 'Toure', 'Ousmane', 'M', 5, 2, 1, 200000),
        ('EMP0014', 'Beye', 'Saliou', 'M', 5, 2, 2, 200000),
        ('EMP0015', 'Mbaye', 'Alioune', 'M', 5, 2, 2, 200000),
    ]
    for mat, nom, prenom, sexe, poste, dep, site, sal in employes:
        c.execute("""INSERT INTO employes
            (matricule, nom, prenom, sexe, poste_id, departement_id, site_id,
             date_embauche, type_contrat, salaire_base, actif)
            VALUES (?,?,?,?,?,?,?,?,?,?,1)""",
            (mat, nom, prenom, sexe, poste, dep, site, f'{year-2}-01-15', 'CDI', sal))

    # ============ FOURNISSEURS ============
    fournisseurs = [
        ('F001', 'SEMENCES SAHEL', 'Semences', 'M. Diop', '33 821 00 00', 'Dakar'),
        ('F002', 'MPEMBA INDUSTRIES', 'Emballage', 'Mme Sy', '33 855 00 00', 'Dakar'),
        ('F003', 'ETIQUETTES SENEGAL', 'Étiquetage', 'M. Sall', '33 957 00 00', 'Thiès'),
        ('F004', 'SUCRERIE SENEGALAISE', 'Sucre', 'M. Faye', '33 991 00 00', 'Richard-Toll'),
        ('F005', 'SOLAR AFRICA', 'Panneaux solaires', 'M. Diouf', '33 860 00 00', 'Dakar'),
    ]
    for code, nom, typ, contact, tel, ville in fournisseurs:
        c.execute("""INSERT INTO fournisseurs (code, nom, type, contact_nom, telephone, ville)
                     VALUES (?,?,?,?,?,?)""", (code, nom, typ, contact, tel, ville))

    # ============ CLIENTS B2B EXPORT ============
    clients_b2b = [
        ('CL001', 'CARREFOUR FRANCE', 'Grande distribution', 'France', 'EUR', 'bio, IFS'),
        ('CL002', 'METRO AG', 'Cash & Carry', 'Allemagne', 'EUR', 'IFS, HACCP'),
        ('CL003', 'DELHAIZE', 'Grande distribution', 'Belgique', 'EUR', 'BRC, IFS'),
        ('CL004', 'AHOLD DELHAIZE', 'Grande distribution', 'Pays-Bas', 'EUR', 'IFS'),
        ('CL005', 'WHOLE FOODS', 'Bio premium', 'US', 'USD', 'USDA Organic'),
    ]
    for code, nom, typ, pays, devise, certifs in clients_b2b:
        c.execute("""INSERT INTO clients_b2b
            (code, nom, type, pays, certifications_requises, actif)
            VALUES (?,?,?,?,?,1)""",
            (code, nom, typ, pays, certifs))

    # ============ PRODUITS FINIS (SM10 AGRO) ============
    produits = [
        # Mangue
        ('PF-MNG-001', 'Mangue séchée premium', 'Mangue', 'Séchée', 'Mangue', 'kg', 'sachet 200g', 12, '#0e7490', 8000, 15000, '0810.10'),
        ('PF-MNG-002', 'Mangue séchée bio', 'Mangue', 'Séchée Bio', 'Mangue', 'kg', 'sachet 200g', 12, '#0e7490', 10000, 18000, '0810.10'),
        ('PF-MNG-003', 'Pulpe de mangue', 'Mangue', 'Pulpe', 'Mangue', 'kg', 'bidon 5kg', 12, '#0e7490', 3000, 6000, '2007.99'),
        ('PF-MNG-004', 'Confiture de mangue', 'Mangue', 'Confiture', 'Mangue', 'kg', 'pot 250g', 24, '#0e7490', 4000, 8000, '2007.99'),
        ('PF-MNG-005', 'Jus de mangue', 'Mangue', 'Jus', 'Mangue', 'L', 'bouteille 1L', 12, '#0e7490', 1500, 3000, '2009.89'),

        # Noix de cajou
        ('PF-CAJ-001', 'Noix de cajou grillées', 'Cajou', 'Grillée', 'Noix cajou', 'kg', 'sachet 500g', 12, '#f59e0b', 5000, 10000, '0801.31'),
        ('PF-CAJ-002', 'Noix de cajou salées', 'Cajou', 'Salée', 'Noix cajou', 'kg', 'sachet 500g', 12, '#f59e0b', 5500, 11000, '0801.31'),
        ('PF-CAJ-003', 'Beurre de cajou', 'Cajou', 'Beurre', 'Noix cajou', 'kg', 'pot 500g', 24, '#f59e0b', 8000, 16000, '2008.19'),
        ('PF-CAJ-004', 'Noix de cajou bio', 'Cajou', 'Bio', 'Noix cajou', 'kg', 'sachet 500g', 12, '#f59e0b', 6500, 13000, '0801.31'),

        # Autres fruits/légumes
        ('PF-BIS-001', 'Bissap séché', 'Autres', 'Infusion', 'Hibiscus', 'kg', 'sachet 100g', 24, '#dc2626', 4000, 8000, '1211.90'),
        ('PF-BOU-001', 'Bouye séché', 'Autres', 'Infusion', 'Baobab', 'kg', 'sachet 100g', 24, '#dc2626', 6000, 12000, '1211.90'),
        ('PF-GNG-001', 'Gingembre en poudre', 'Autres', 'Poudre', 'Gingembre', 'kg', 'sachet 200g', 24, '#dc2626', 5000, 10000, '0910.11'),
        ('PF-TAM-001', 'Tamarin séché', 'Autres', 'Séchée', 'Tamarin', 'kg', 'sachet 200g', 24, '#dc2626', 3500, 7000, '0813.40'),

        # Légumes
        ('PF-OIG-001', 'Oignon déshydraté', 'Légumes', 'Déshydraté', 'Oignon', 'kg', 'sachet 500g', 24, '#10b981', 3500, 7000, '0712.20'),
        ('PF-TOM-001', 'Tomate séchée', 'Légumes', 'Séchée', 'Tomate', 'kg', 'sachet 250g', 12, '#10b981', 4500, 9000, '0712.90'),
    ]

    for code, nom, cat, sous_cat, mp, unite, cond, duree, color, prix_rev, prix_vente, sh in produits:
        c.execute("""INSERT INTO produits_finis
            (code, nom, categorie, sous_categorie, matiere_premiere, unite,
             conditionnement, duree_conservation_mois, prix_revient, prix_vente,
             code_sh, certifications, actif)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)""",
            (code, nom, cat, sous_cat, mp, unite, cond, duree,
             prix_rev, prix_vente, sh, 'HACCP, ISO 22000'))

    # ============ CATÉGORIES MARCHÉ ============
    prix_marches = [
        ('Mangue séchée', 'Dakar', 'Sénégal', 15000, 18000, 22000, 'kg', 'XOF'),
        ('Mangue séchée', 'Paris', 'France', 25000, 30000, 35000, 'kg', 'EUR'),
        ('Noix cajou', 'Dakar', 'Sénégal', 10000, 12000, 15000, 'kg', 'XOF'),
        ('Noix cajou', 'Amsterdam', 'Pays-Bas', 20000, 25000, 30000, 'kg', 'EUR'),
        ('Bissap', 'Dakar', 'Sénégal', 8000, 10000, 12000, 'kg', 'XOF'),
    ]
    for prod, marche, pays, pmin, pmoy, pmax, unite, devise in prix_marches:
        c.execute("""INSERT INTO prix_marche
            (produit, marche, pays, date_releve, prix_min, prix_moyen, prix_max, unite, devise)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (prod, marche, pays, datetime.now().date().isoformat(), pmin, pmoy, pmax, unite, devise))

    # ============ CONCURRENTS ============
    concurrents = [
        ('Mangue du Sénégal', 'Sénégal', 'Mangue séchée', 'Local + Export', 12000, 'HACCP'),
        ('Olam International', 'Singapour', 'Cajou, mangue', 'International', 25000, 'BRC, ISO'),
        ('Cajou du Bénin', 'Bénin', 'Noix cajou', 'Local', 9000, 'Bio UE'),
    ]
    for nom, pays, produits, marches, prix, certifs in concurrents:
        c.execute("""INSERT INTO concurrents (nom, pays, produits, marches, prix_moyen, certifications)
                     VALUES (?,?,?,?,?,?)""", (nom, pays, produits, marches, prix, certifs))

    # ============ UTILISATEURS ============
    def h(pwd):
        return hashlib.sha256(pwd.encode()).hexdigest()

    users = [
        ('admin', h('admin123'), 'Admin', 'Omega', 'admin@omega-agro.sn', 'admin', None),
        ('directeur', h('dir123'), 'Diop', 'Mamadou', 'dir@omega-agro.sn', 'directeur', 1),
        ('production', h('prod123'), 'Ndiaye', 'Fatou', 'prod@omega-agro.sn', 'production', 1),
        ('qualite', h('qual123'), 'Fall', 'Omar', 'qual@omega-agro.sn', 'qualite', 1),
        ('export', h('exp123'), 'Sow', 'Aminata', 'export@omega-agro.sn', 'export', 1),
        ('formation', h('form123'), 'Ba', 'Ibrahima', 'formation@omega-agro.sn', 'formation', 3),
    ]
    for username, pwd, nom, prenom, email, role, site_id in users:
        c.execute("""INSERT INTO utilisateurs
            (username, password_hash, nom, prenom, email, role, site_id, actif)
            VALUES (?,?,?,?,?,?,?,1)""",
            (username, pwd, nom, prenom, email, role, site_id))

    # ============ CERTIFICATIONS ============
    certifs = [
        ('CERT-HACCP', 'HACCP', 'Ecocert', 'Sécurité alimentaire', 5),
        ('CERT-ISO22000', 'ISO 22000', 'AFNOR', 'Management sécurité alimentaire', 3),
        ('CERT-BRC', 'BRC Global Standard', 'BRCGS', 'Standard distributeurs UE', 3),
        ('CERT-IFS', 'IFS Food', 'IFS', 'Standard distributeurs UE', 3),
        ('CERT-ORGANIC', 'Bio UE', 'Ecocert', 'Agriculture biologique UE', 3),
        ('CERT-FAIRTRADE', 'Fairtrade', 'Fairtrade International', 'Commerce équitable', 3),
        ('CERT-EXPORT', 'Certificat export UE', 'UE', 'Autorisation export UE', 5),
    ]
    for code, nom, orga, portee, duree in certifs:
        c.execute("""INSERT INTO certifications
            (code, nom, organisme, portee, date_obtention, date_expiration, statut)
            VALUES (?,?,?,?,?,?,?)""",
            (code, nom, orga, portee,
             datetime.now().date().isoformat(),
             (datetime.now() + timedelta(days=duree*365)).date().isoformat(),
             'Active'))

    # ============ FORMATIONS ============
    formations = [
        ('FORM-HACCP', 'HACCP niveau 1', 'Qualité', 2, 'Débutant'),
        ('FORM-ISO22000', 'ISO 22000 internal auditor', 'Qualité', 5, 'Intermédiaire'),
        ('FORM-TRANSFO', 'Techniques de transformation mangue', 'Production', 10, 'Intermédiaire'),
        ('FORM-CAJOU', 'Transformation noix de cajou', 'Production', 7, 'Intermédiaire'),
        ('FORM-EXPORT', 'Export vers l\'UE', 'Export', 3, 'Avancé'),
        ('FORM-AGRICULTURE', 'Bonnes pratiques agricoles', 'Agriculture', 5, 'Débutant'),
        ('FORM-ENTREPRENEUR', 'Entrepreneuriat agricole', 'Management', 14, 'Intermédiaire'),
        ('FORM-BIO', 'Agriculture biologique', 'Agriculture', 5, 'Intermédiaire'),
    ]
    for code, nom, cat, duree, niveau in formations:
        c.execute("""INSERT INTO formations
            (code, nom, categorie, duree_jours, niveau, actif)
            VALUES (?,?,?,?,?,1)""",
            (code, nom, cat, duree, niveau))

    # ============ PARAMÈTRES ============
    params = [
        ('devise', 'FCFA', 'text', 'Devise principale'),
        ('tva_pct', '18', 'int', 'TVA Sénégal'),
        ('investissement_sm10', '11400000000', 'int', 'Investissement SM10 AGRO en FCFA'),
        ('capacite_mangue_t_an', '5000', 'int', 'Capacité transformation mangue (t/an)'),
        ('capacite_cajou_t_an', '3000', 'int', 'Capacité transformation cajou (t/an)'),
        ('nb_producteurs_cible', '2000', 'int', 'Nombre de producteurs partenaires'),
        ('exoneration_apix_ans', '5', 'int', 'Durée exonération APIX'),
        ('seuil_export_ue_t', '100', 'float', 'Seuil minimal export UE (tonnes)'),
        ('temp_sechage_c', '60', 'int', 'Température de séchage (°C)'),
        ('temp_conservation_c', '20', 'int', 'Température de conservation (°C)'),
        ('duree_conservation_mois', '12', 'int', 'Durée de conservation par défaut'),
        ('objectif_export_ue_pct', '70', 'int', 'Objectif % chiffre d\'affaires UE'),
        ('filiere_mangue', '1', 'int', 'Filière mangue active'),
        ('filiere_cajou', '1', 'int', 'Filière cajou active'),
        ('filiere_autres', '1', 'int', 'Filière autres fruits active'),
        ('formation_active', '1', 'int', 'Centre de formation actif'),
    ]
    for cle, val, typ, desc in params:
        c.execute("""INSERT INTO parametres (cle, valeur, type, description)
                     VALUES (?,?,?,?)""", (cle, val, typ, desc))

    print("[INIT] ✅ Données démo SM10 AGRO insérées")
    print("      - 4 sites (usines + formation)")
    print("      - 15 produits finis (mangue, cajou, autres)")
    print("      - 5 clients B2B européens")
    print("      - 7 certifications (HACCP, ISO 22000, BRC...)")
    print("      - 8 formations disponibles")


if __name__ == '__main__':
    init_db()
