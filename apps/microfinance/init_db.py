"""
🏦 MicroFinance 2.0 — Base de données
45 tables — Conforme BCEAO, UEMOA, LCB-FT, RGPD
"""
import sqlite3
import hashlib
from datetime import datetime, timedelta

DB_PATH = "/app/data/microfinance.db"


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

    # ==================== RÉFÉRENTIEL ====================
    c.execute("""CREATE TABLE IF NOT EXISTS pays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        devise TEXT DEFAULT 'XOF',
        actif INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS regions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pays_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        nom TEXT NOT NULL,
        FOREIGN KEY (pays_id) REFERENCES pays(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS agences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type TEXT DEFAULT 'Agence',
        adresse TEXT,
        ville TEXT,
        telephone TEXT,
        email TEXT,
        responsable_id INTEGER,
        region_id INTEGER,
        gps_latitude REAL,
        gps_longitude REAL,
        ouverture TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (region_id) REFERENCES regions(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS guichets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        agence_id INTEGER NOT NULL,
        caissier_id INTEGER,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (agence_id) REFERENCES agences(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS employes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        matricule TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        poste TEXT,
        telephone TEXT,
        email TEXT,
        agence_id INTEGER,
        date_embauche TEXT,
        salaire_base INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (agence_id) REFERENCES agences(id)
    )""")

    # ==================== CLIENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        type_client TEXT DEFAULT 'Particulier',
        nom TEXT NOT NULL,
        prenom TEXT,
        date_naissance TEXT,
        sexe TEXT,
        situation_familiale TEXT,
        telephone TEXT,
        telephone_secondaire TEXT,
        email TEXT,
        adresse TEXT,
        ville TEXT,
        region_id INTEGER,
        numero_cni TEXT,
        date_cni TEXT,
        numero_cnss TEXT,
        photo_path TEXT,
        gps_latitude REAL,
        gps_longitude REAL,
        profession TEXT,
        revenu_mensuel INTEGER DEFAULT 0,
        activite_principale TEXT,
        agence_id INTEGER,
        agent_id INTEGER,
        statut TEXT DEFAULT 'Actif',
        date_adhesion TEXT,
        kyc_statut TEXT DEFAULT 'En attente',
        kyc_date TEXT,
        kyc_valide_par INTEGER,
        score_interne INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (region_id) REFERENCES regions(id),
        FOREIGN KEY (agence_id) REFERENCES agences(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS documents_kyc (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        type_document TEXT NOT NULL,
        numero TEXT,
        fichier_path TEXT,
        date_emission TEXT,
        date_expiration TEXT,
        verifie INTEGER DEFAULT 0,
        verifie_par INTEGER,
        date_verification TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS benefficiaires (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT,
        lien_parente TEXT,
        telephone TEXT,
        pourcentage INTEGER DEFAULT 100,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS groupes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type_groupe TEXT DEFAULT 'Solidarité',
        agence_id INTEGER,
        responsable_id INTEGER,
        date_creation TEXT,
        nb_membres INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (agence_id) REFERENCES agences(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS groupe_membres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        groupe_id INTEGER NOT NULL,
        client_id INTEGER NOT NULL,
        date_adhesion TEXT,
        role TEXT DEFAULT 'Membre',
        FOREIGN KEY (groupe_id) REFERENCES groupes(id),
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    # ==================== PRODUITS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS produits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        categorie TEXT,
        type_produit TEXT,
        description TEXT,
        montant_min INTEGER DEFAULT 0,
        montant_max INTEGER DEFAULT 0,
        duree_min_mois INTEGER DEFAULT 0,
        duree_max_mois INTEGER DEFAULT 0,
        taux_interet_min REAL DEFAULT 0,
        taux_interet_max REAL DEFAULT 0,
        frais_dossier_pct REAL DEFAULT 0,
        frais_dossier_fixe INTEGER DEFAULT 0,
        assurance_pct REAL DEFAULT 0,
        epargne_obligatoire_pct REAL DEFAULT 0,
        periodicite TEXT DEFAULT 'Mensuel',
        garanties_requises TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS conditions_produit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER NOT NULL,
        condition TEXT NOT NULL,
        valeur TEXT,
        obligatoire INTEGER DEFAULT 1,
        FOREIGN KEY (produit_id) REFERENCES produits(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS grille_tarifaire (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER NOT NULL,
        tranche_min INTEGER NOT NULL,
        tranche_max INTEGER NOT NULL,
        taux_interet REAL NOT NULL,
        duree_max_mois INTEGER,
        FOREIGN KEY (produit_id) REFERENCES produits(id) ON DELETE CASCADE
    )""")

    # ==================== DEMANDES DE CRÉDIT ====================
    c.execute("""CREATE TABLE IF NOT EXISTS demandes_credit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        client_id INTEGER NOT NULL,
        produit_id INTEGER,
        agence_id INTEGER,
        agent_id INTEGER,
        montant_demande INTEGER NOT NULL,
        duree_mois INTEGER NOT NULL,
        objet_credit TEXT,
        activite_financee TEXT,
        date_demande TEXT,
        date_analyse TEXT,
        date_decision TEXT,
        statut TEXT DEFAULT 'En analyse',
        score_client INTEGER,
        score_ia INTEGER,
        recommandation_ia TEXT,
        niveau_risque TEXT,
        montant_approuve INTEGER,
        taux_approuve REAL,
        duree_approuvee INTEGER,
        motif_rejet TEXT,
        valide_par INTEGER,
        date_validation TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (produit_id) REFERENCES produits(id),
        FOREIGN KEY (agence_id) REFERENCES agences(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS documents_demande (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        demande_id INTEGER NOT NULL,
        type_document TEXT NOT NULL,
        fichier_path TEXT,
        uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (demande_id) REFERENCES demandes_credit(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS analyses_credit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        demande_id INTEGER NOT NULL,
        analyste_id INTEGER,
        date_analyse TEXT,
        revenus_client INTEGER,
        charges_client INTEGER,
        capacite_remboursement INTEGER,
        ratio_endettement REAL,
        garanties_offertes TEXT,
        valeur_garanties INTEGER,
        observations TEXT,
        recommandation TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (demande_id) REFERENCES demandes_credit(id)
    )""")

    # ==================== CRÉDITS ACTIFS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS credits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        demande_id INTEGER,
        client_id INTEGER NOT NULL,
        produit_id INTEGER,
        agence_id INTEGER,
        agent_id INTEGER,
        montant_principal INTEGER NOT NULL,
        taux_interet REAL NOT NULL,
        duree_mois INTEGER NOT NULL,
        periodicite TEXT DEFAULT 'Mensuel',
        date_decaissement TEXT,
        date_premiere_echeance TEXT,
        date_fin_prevue TEXT,
        montant_interets INTEGER DEFAULT 0,
        montant_frais INTEGER DEFAULT 0,
        montant_assurance INTEGER DEFAULT 0,
        montant_total_du INTEGER DEFAULT 0,
        montant_rembourse INTEGER DEFAULT 0,
        capital_restant INTEGER DEFAULT 0,
        interets_restants INTEGER DEFAULT 0,
        solde_restant INTEGER DEFAULT 0,
        nb_echeances INTEGER DEFAULT 0,
        nb_echeances_payees INTEGER DEFAULT 0,
        nb_echeances_retard INTEGER DEFAULT 0,
        jours_retard INTEGER DEFAULT 0,
        statut TEXT DEFAULT 'Actif',
        classification TEXT DEFAULT 'Sain',
        provision_risque INTEGER DEFAULT 0,
        garanties TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (produit_id) REFERENCES produits(id),
        FOREIGN KEY (agence_id) REFERENCES agences(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS echeances_credit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        credit_id INTEGER NOT NULL,
        numero_echeance INTEGER NOT NULL,
        date_echeance TEXT NOT NULL,
        montant_capital INTEGER,
        montant_interets INTEGER,
        montant_frais INTEGER DEFAULT 0,
        montant_assurance INTEGER DEFAULT 0,
        montant_total INTEGER,
        montant_paye INTEGER DEFAULT 0,
        montant_restant INTEGER,
        date_paiement TEXT,
        statut TEXT DEFAULT 'À venir',
        jours_retard INTEGER DEFAULT 0,
        penalite_retard INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (credit_id) REFERENCES credits(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS remboursements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        credit_id INTEGER NOT NULL,
        echeance_id INTEGER,
        client_id INTEGER NOT NULL,
        montant_recu INTEGER NOT NULL,
        montant_capital INTEGER DEFAULT 0,
        montant_interets INTEGER DEFAULT 0,
        montant_penalites INTEGER DEFAULT 0,
        montant_frais INTEGER DEFAULT 0,
        mode_paiement TEXT DEFAULT 'Espèces',
        reference_paiement TEXT,
        numero_recu TEXT,
        caissier_id INTEGER,
        guichet_id INTEGER,
        date_paiement TEXT,
        observation TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (credit_id) REFERENCES credits(id),
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS garanties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        credit_id INTEGER NOT NULL,
        type_garantie TEXT,
        description TEXT,
        valeur_estimee INTEGER,
        fichier_path TEXT,
        statut TEXT DEFAULT 'Active',
        date_restitution TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (credit_id) REFERENCES credits(id)
    )""")

    # ==================== ÉPARGNE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS comptes_epargne (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_compte TEXT UNIQUE NOT NULL,
        client_id INTEGER NOT NULL,
        produit_epargne_id INTEGER,
        agence_id INTEGER,
        solde INTEGER DEFAULT 0,
        solde_disponible INTEGER DEFAULT 0,
        solde_bloque INTEGER DEFAULT 0,
        date_ouverture TEXT,
        date_derniere_operation TEXT,
        taux_interet REAL DEFAULT 0,
        statut TEXT DEFAULT 'Actif',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS operations_epargne (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        compte_id INTEGER NOT NULL,
        type_operation TEXT NOT NULL,
        montant INTEGER NOT NULL,
        solde_avant INTEGER,
        solde_apres INTEGER,
        mode_paiement TEXT,
        reference_externe TEXT,
        caissier_id INTEGER,
        guichet_id INTEGER,
        date_operation TEXT,
        observation TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (compte_id) REFERENCES comptes_epargne(id)
    )""")

    # ==================== MOBILE MONEY ====================
    c.execute("""CREATE TABLE IF NOT EXISTS transactions_mobile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        client_id INTEGER,
        credit_id INTEGER,
        compte_epargne_id INTEGER,
        fournisseur TEXT NOT NULL,
        telephone TEXT,
        type_transaction TEXT,
        montant INTEGER NOT NULL,
        frais INTEGER DEFAULT 0,
        statut TEXT DEFAULT 'En attente',
        reference_externe TEXT,
        callback_data TEXT,
        date_initiation TEXT,
        date_completion TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS configurations_mm (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fournisseur TEXT UNIQUE NOT NULL,
        api_key TEXT,
        api_secret TEXT,
        endpoint TEXT,
        merchant_id TEXT,
        actif INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== RECOUVREMENT ====================
    c.execute("""CREATE TABLE IF NOT EXISTS actions_recouvrement (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        credit_id INTEGER NOT NULL,
        client_id INTEGER NOT NULL,
        agent_id INTEGER,
        type_action TEXT,
        date_action TEXT,
        description TEXT,
        resultat TEXT,
        prochaine_action TEXT,
        date_prochaine_action TEXT,
        montant_promis INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (credit_id) REFERENCES credits(id),
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS mises_en_demeure (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        credit_id INTEGER NOT NULL,
        client_id INTEGER NOT NULL,
        date_emission TEXT,
        date_echeance TEXT,
        motif TEXT,
        montant_reclame INTEGER,
        statut TEXT DEFAULT 'Envoyée',
        fichier_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (credit_id) REFERENCES credits(id)
    )""")

    # ==================== COMPTABILITÉ ====================
    c.execute("""CREATE TABLE IF NOT EXISTS journal_comptable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_ecriture TEXT UNIQUE NOT NULL,
        date_ecriture TEXT NOT NULL,
        journal TEXT,
        compte_debit TEXT,
        compte_credit TEXT,
        libelle TEXT,
        montant INTEGER,
        reference_document TEXT,
        utilisateur_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS caisse (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        agence_id INTEGER,
        guichet_id INTEGER,
        caissier_id INTEGER,
        solde_ouverture INTEGER DEFAULT 0,
        solde_actuel INTEGER DEFAULT 0,
        date_ouverture TEXT,
        date_fermeture TEXT,
        statut TEXT DEFAULT 'Ouverte',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (agence_id) REFERENCES agences(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS mouvements_caisse (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        caisse_id INTEGER NOT NULL,
        type_mouvement TEXT,
        montant INTEGER,
        solde_avant INTEGER,
        solde_apres INTEGER,
        libelle TEXT,
        reference TEXT,
        utilisateur_id INTEGER,
        date_mouvement TEXT,
        FOREIGN KEY (caisse_id) REFERENCES caisse(id)
    )""")

    # ==================== SCORING & IA ====================
    c.execute("""CREATE TABLE IF NOT EXISTS scores_credit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        date_evaluation TEXT,
        score INTEGER NOT NULL,
        niveau TEXT,
        probabilite_defaut REAL,
        revenus_totaux INTEGER,
        charges_totales INTEGER,
        capacite_remboursement INTEGER,
        historique_credit INTEGER,
        anciennete_client INTEGER,
        regularite_paiement REAL,
        garanties_valeur INTEGER,
        zone_geographique TEXT,
        activite TEXT,
        recommandation TEXT,
        montant_max_recommande INTEGER,
        modele_version TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS modeles_ia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type_modele TEXT,
        version TEXT,
        precision_pct REAL,
        dataset_taille INTEGER,
        date_entrainement TEXT,
        statut TEXT DEFAULT 'Actif',
        description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS predictions_ia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        modele_id INTEGER,
        client_id INTEGER,
        credit_id INTEGER,
        date_prediction TEXT,
        type_prediction TEXT,
        valeur_predite REAL,
        unite TEXT,
        confiance_pct REAL,
        donnees_entree_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== LCB-FT (Anti-blanchiment) ====================
    c.execute("""CREATE TABLE IF NOT EXISTS declarations_soupcon (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        client_id INTEGER,
        transaction_id INTEGER,
        date_detection TEXT,
        type_alerte TEXT,
        niveau_risque TEXT,
        montant_implique INTEGER,
        description TEXT,
        statut TEXT DEFAULT 'À analyser',
        analyste_id INTEGER,
        date_analyse TEXT,
        decision TEXT,
        transmission_centif INTEGER DEFAULT 0,
        date_transmission TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS listes_surveillance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        type_liste TEXT,
        nom TEXT,
        prenom TEXT,
        date_naissance TEXT,
        nationalite TEXT,
        numero_piece TEXT,
        motif TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS alertes_lcb (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        type_alerte TEXT,
        gravite TEXT,
        description TEXT,
        montant_implique INTEGER,
        seuil_depasse INTEGER DEFAULT 0,
        statut TEXT DEFAULT 'Active',
        traitee_par INTEGER,
        date_traitement TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== REPORTING BCEAO ====================
    c.execute("""CREATE TABLE IF NOT EXISTS rapports_reglementaires (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type_rapport TEXT,
        periodicite TEXT,
        organisme TEXT DEFAULT 'BCEAO',
        format TEXT,
        derniere_generation TEXT,
        prochaine_echeance TEXT,
        statut TEXT DEFAULT 'À jour',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS generations_rapports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rapport_id INTEGER,
        date_generation TEXT,
        periode TEXT,
        fichier_path TEXT,
        statut TEXT DEFAULT 'Généré',
        genere_par INTEGER,
        transmis INTEGER DEFAULT 0,
        date_transmission TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (rapport_id) REFERENCES rapports_reglementaires(id)
    )""")

    # ==================== UTILISATEURS & AUDIT ====================
    c.execute("""CREATE TABLE IF NOT EXISTS utilisateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nom TEXT,
        prenom TEXT,
        email TEXT,
        telephone TEXT,
        role TEXT DEFAULT 'agent',
        agence_id INTEGER,
        employe_id INTEGER,
        actif INTEGER DEFAULT 1,
        dernier_login TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        module TEXT NOT NULL,
        action TEXT NOT NULL,
        autorise INTEGER DEFAULT 1
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

    # Index pour performance
    c.execute("CREATE INDEX IF NOT EXISTS idx_clients_agence ON clients(agence_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_clients_statut ON clients(statut)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_credits_client ON credits(client_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_credits_statut ON credits(statut)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_echeances_credit ON echeances_credit(credit_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_echeances_statut ON echeances_credit(statut)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_remboursements_credit ON remboursements(credit_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_transactions_client ON transactions_mobile(client_id)")

    conn.commit()

    # ==================== DONNÉES DÉMO ====================
    c.execute("SELECT COUNT(*) FROM pays")
    if c.fetchone()[0] == 0:
        print("[INIT] Insertion données démo...")
        _seed_data(c)
        conn.commit()

    conn.close()
    print(f"[INIT] ✅ Base prête : {DB_PATH}")


def _seed_data(c):
    """Insère les données de démonstration"""
    year = datetime.now().year

    # ============ PAYS CEDEAO ============
    pays = [
        ('SN', 'Sénégal', 'XOF'),
        ('CI', 'Côte d\'Ivoire', 'XOF'),
        ('ML', 'Mali', 'XOF'),
        ('BF', 'Burkina Faso', 'XOF'),
        ('BJ', 'Bénin', 'XOF'),
        ('TG', 'Togo', 'XOF'),
        ('NE', 'Niger', 'XOF'),
        ('GW', 'Guinée-Bissau', 'XOF'),
        ('NG', 'Nigeria', 'NGN'),
        ('GH', 'Ghana', 'GHS'),
    ]
    for code, nom, devise in pays:
        c.execute("INSERT INTO pays (code, nom, devise) VALUES (?,?,?)", (code, nom, devise))

    # ============ RÉGIONS SÉNÉGAL ============
    regions = [
        (1, 'DKR', 'Dakar'), (1, 'THS', 'Thiès'), (1, 'DBL', 'Diourbel'),
        (1, 'FTK', 'Fatick'), (1, 'KLC', 'Kaolack'), (1, 'KFL', 'Kaffrine'),
        (1, 'SLS', 'Saint-Louis'), (1, 'LOU', 'Louga'), (1, 'MTM', 'Matam'),
        (1, 'TMB', 'Tambacounda'), (1, 'KDG', 'Kédougou'), (1, 'KOL', 'Kolda'),
        (1, 'ZIG', 'Ziguinchor'), (1, 'SED', 'Sédhiou'),
    ]
    for pays_id, code, nom in regions:
        c.execute("INSERT INTO regions (pays_id, code, nom) VALUES (?,?,?)", (pays_id, code, nom))

    # ============ AGENCES ============
    agences = [
        ('AG-DKR-001', 'Agence Dakar Centre', 'Agence', 'Plateau', 'Dakar', '33 821 00 00', 1),
        ('AG-DKR-002', 'Agence Pikine', 'Agence', 'Pikine', 'Dakar', '33 855 00 00', 1),
        ('AG-THS-001', 'Agence Thiès', 'Agence', 'Centre', 'Thiès', '33 951 00 00', 2),
        ('AG-KLC-001', 'Agence Kaolack', 'Agence', 'Médina', 'Kaolack', '33 941 00 00', 5),
        ('AG-ZIG-001', 'Agence Ziguinchor', 'Agence', 'Centre', 'Ziguinchor', '33 991 00 00', 13),
    ]
    for code, nom, typ, adr, ville, tel, region_id in agences:
        c.execute("""INSERT INTO agences (code, nom, type, adresse, ville, telephone, region_id)
                     VALUES (?,?,?,?,?,?,?)""", (code, nom, typ, adr, ville, tel, region_id))

    # ============ PRODUITS ============
    produits = [
        ('CRD-MICRO', 'Micro-crédit solidaire', 'Crédit', 'Groupe', 50000, 500000, 3, 12, 12.0, 18.0, 2.0, 5000, 1.0, 10.0),
        ('CRD-INDIV', 'Crédit individuel', 'Crédit', 'Individuel', 100000, 5000000, 6, 36, 10.0, 15.0, 1.5, 10000, 1.5, 5.0),
        ('CRD-AGR', 'Crédit agricole', 'Crédit', 'Saisonnier', 100000, 2000000, 6, 18, 8.0, 12.0, 1.0, 5000, 1.0, 5.0),
        ('CRD-COM', 'Crédit commercial', 'Crédit', 'Court terme', 200000, 10000000, 3, 24, 10.0, 14.0, 2.0, 15000, 2.0, 5.0),
        ('CRD-IMMO', 'Crédit immobilier', 'Crédit', 'Long terme', 1000000, 30000000, 24, 120, 8.0, 12.0, 1.5, 50000, 1.0, 5.0),
        ('CRD-URG', 'Crédit urgence', 'Crédit', 'Court terme', 25000, 200000, 1, 6, 15.0, 20.0, 3.0, 2500, 1.0, 5.0),
    ]
    for code, nom, cat, typ, mmin, mmax, dmin, dmax, tmin, tmax, frais_pct, frais_fixe, assur, ep in produits:
        c.execute("""INSERT INTO produits
            (code, nom, categorie, type_produit, montant_min, montant_max,
             duree_min_mois, duree_max_mois, taux_interet_min, taux_interet_max,
             frais_dossier_pct, frais_dossier_fixe, assurance_pct, epargne_obligatoire_pct)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (code, nom, cat, typ, mmin, mmax, dmin, dmax, tmin, tmax, frais_pct, frais_fixe, assur, ep))

    # ============ UTILISATEURS ============
    def h(pwd):
        return hashlib.sha256(pwd.encode()).hexdigest()

    users = [
        ('admin', h('admin123'), 'Admin', 'Omega', 'admin@microfinance.sn', 'admin', None),
        ('directeur', h('dir123'), 'Diop', 'Mamadou', 'dir@microfinance.sn', 'directeur', 1),
        ('agent1', h('agent123'), 'Fall', 'Omar', 'agent1@microfinance.sn', 'agent', 1),
        ('caissier1', h('caisse123'), 'Ndiaye', 'Fatou', 'caissier1@microfinance.sn', 'caissier', 1),
        ('analyste1', h('analyse123'), 'Ba', 'Ibrahima', 'analyste@microfinance.sn', 'analyste', 1),
        ('auditeur1', h('audit123'), 'Sow', 'Aminata', 'auditeur@microfinance.sn', 'auditeur', None),
    ]
    for username, pwd, nom, prenom, email, role, agence_id in users:
        c.execute("""INSERT INTO utilisateurs
            (username, password_hash, nom, prenom, email, role, agence_id, actif)
            VALUES (?,?,?,?,?,?,?,1)""",
            (username, pwd, nom, prenom, email, role, agence_id))

    # ============ PARAMÈTRES ============
    params = [
        ('devise', 'FCFA', 'text', 'Devise'),
        ('taux_tva', '18', 'int', 'TVA Sénégal'),
        ('taux_usure', '27', 'float', 'Taux d\'usure BCEAO'),
        ('seuil_declaration', '5000000', 'int', 'Seuil déclaration LCB-FT'),
        ('age_minimum', '18', 'int', 'Âge minimum emprunteur'),
        ('age_maximum', '70', 'int', 'Âge maximum emprunteur'),
        ('ratio_endettement_max', '40', 'float', 'Ratio endettement max (%)'),
        ('provision_sain', '0', 'float', 'Provision crédit sain (%)'),
        ('provision_sous_surveillance', '5', 'float', 'Provision sous surveillance (%)'),
        ('provision_douteux', '50', 'float', 'Provision douteux (%)'),
        ('provision_compromis', '100', 'float', 'Provision compromis (%)'),
        ('periode_grace_jours', '30', 'int', 'Période de grâce avant impayé'),
        ('penalite_retard_pct', '1', 'float', 'Pénalité de retard mensuelle (%)'),
        ('mm_wave_actif', '1', 'int', 'Wave activé'),
        ('mm_om_actif', '1', 'int', 'Orange Money activé'),
        ('mm_free_actif', '1', 'int', 'Free Money activé'),
    ]
    for cle, val, typ, desc in params:
        c.execute("""INSERT INTO parametres (cle, valeur, type, description)
                     VALUES (?,?,?,?)""", (cle, val, typ, desc))

    print("[INIT] ✅ Données démo insérées (10 pays, 14 régions, 5 agences, 6 produits)")


if __name__ == '__main__':
    init_db()
