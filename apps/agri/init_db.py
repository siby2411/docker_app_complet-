"""
🌾 AgriSénégal V2 — Base de données
45 tables — Agriculture connectée 2026
Inspiration : Kenya (M-Pesa, iCow, UjuziKilimo, FarmDrive)
"""
import sqlite3
import hashlib
from datetime import datetime, timedelta, date

DB_PATH = "/app/data/agri.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # NOTE: FK + WAL désactivés temporairement (perf WSL)
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=MEMORY")
    return conn


def init_db():
    print(f"[INIT] Base : {DB_PATH}")
    conn = get_conn()
    c = conn.cursor()

    # ================================================================
    # RÉFÉRENTIEL
    # ================================================================

    c.execute("""CREATE TABLE IF NOT EXISTS regions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        chef_lieu TEXT,
        superficie_km2 REAL,
        population INTEGER,
        zone_agro TEXT,
        pluviometrie_mm REAL,
        actif INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS departements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        region_id INTEGER NOT NULL,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        chef_lieu TEXT,
        FOREIGN KEY (region_id) REFERENCES regions(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS villages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        departement_id INTEGER NOT NULL,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        population INTEGER,
        nb_menages INTEGER,
        acces_eau TEXT,
        couverture_reseau TEXT,
        FOREIGN KEY (departement_id) REFERENCES departements(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cooperatives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type TEXT DEFAULT 'Agricole',
        village_id INTEGER,
        date_creation TEXT,
        nb_membres INTEGER DEFAULT 0,
        president_id INTEGER,
        telephone TEXT,
        email TEXT,
        numero_agrement TEXT,
        banque TEXT,
        rib TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (village_id) REFERENCES villages(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS producteurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT,
        sexe TEXT,
        date_naissance TEXT,
        telephone TEXT,
        telephone_secondaire TEXT,
        email TEXT,
        photo_path TEXT,
        numero_cni TEXT,
        village_id INTEGER,
        cooperative_id INTEGER,
        exploitation_nom TEXT,
        superficie_totale REAL DEFAULT 0,
        type_exploitation TEXT DEFAULT 'Familiale',
        experience_annees INTEGER DEFAULT 0,
        niveau_education TEXT,
        langue_principale TEXT DEFAULT 'Wolof',
        mobile_money_type TEXT,
        mobile_money_numero TEXT,
        gps_latitude REAL,
        gps_longitude REAL,
        certification_bio INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (village_id) REFERENCES villages(id),
        FOREIGN KEY (cooperative_id) REFERENCES cooperatives(id)
    )""")

    # ================================================================
    # PARCELLES & CULTURES
    # ================================================================

    c.execute("""CREATE TABLE IF NOT EXISTS parcelles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        producteur_id INTEGER NOT NULL,
        nom TEXT,
        superficie_ha REAL NOT NULL,
        latitude REAL,
        longitude REAL,
        altitude REAL,
        polygone_geojson TEXT,
        type_sol TEXT,
        ph_sol REAL,
        matiere_organique REAL,
        pente_pct REAL,
        irrigation_disponible INTEGER DEFAULT 0,
        source_eau TEXT,
        statut_juridique TEXT,
        annee_acquisition INTEGER,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cultures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        nom_scientifique TEXT,
        nom_wolof TEXT,
        categorie TEXT,
        cycle_jours_min INTEGER,
        cycle_jours_max INTEGER,
        saison_recommandee TEXT,
        zone_agro TEXT,
        besoin_eau_mm REAL,
        rendement_theorique_t_ha REAL,
        prix_moyen_kg INTEGER,
        icone TEXT,
        actif INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS varietes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        culture_id INTEGER NOT NULL,
        nom TEXT NOT NULL,
        obtenteur TEXT,
        cycle_jours INTEGER,
        potentiel_rendement REAL,
        resistance_maladies TEXT,
        adapte_zone TEXT,
        annee_certification INTEGER,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (culture_id) REFERENCES cultures(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS campagnes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT,
        date_debut TEXT NOT NULL,
        date_fin TEXT,
        saison TEXT,
        region_id INTEGER,
        statut TEXT DEFAULT 'En cours',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (region_id) REFERENCES regions(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cultures_parcelles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parcelle_id INTEGER NOT NULL,
        culture_id INTEGER NOT NULL,
        variete_id INTEGER,
        campagne_id INTEGER,
        date_semis TEXT,
        date_prevue_recolte TEXT,
        date_reelle_recolte TEXT,
        superficie_ha REAL,
        quantite_semence_kg REAL,
        type_semence TEXT,
        densite_plants_ha INTEGER,
        etat TEXT DEFAULT 'Semé',
        rendement_obtenu_t_ha REAL,
        qualite TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id),
        FOREIGN KEY (culture_id) REFERENCES cultures(id),
        FOREIGN KEY (variete_id) REFERENCES varietes(id),
        FOREIGN KEY (campagne_id) REFERENCES campagnes(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS itineraire_technique (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        culture_parcelle_id INTEGER NOT NULL,
        type_operation TEXT NOT NULL,
        date_operation TEXT NOT NULL,
        description TEXT,
        produit_utilise TEXT,
        quantite REAL,
        unite TEXT,
        cout INTEGER DEFAULT 0,
        operateur TEXT,
        statut TEXT DEFAULT 'Planifié',
        photo_path TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (culture_parcelle_id) REFERENCES cultures_parcelles(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS intrants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        categorie TEXT,
        type TEXT,
        composition TEXT,
        unite TEXT,
        prix_unitaire INTEGER DEFAULT 0,
        fournisseur TEXT,
        stock_disponible REAL DEFAULT 0,
        stock_alerte REAL DEFAULT 0,
        homologation TEXT,
        date_peremption TEXT,
        actif INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS stock_intrants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producteur_id INTEGER NOT NULL,
        intrant_id INTEGER NOT NULL,
        quantite_actuelle REAL DEFAULT 0,
        quantite_reservee REAL DEFAULT 0,
        date_derniere_entree TEXT,
        date_derniere_sortie TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id),
        FOREIGN KEY (intrant_id) REFERENCES intrants(id)
    )""")

    # ================================================================
    # AGRO-CLIMAT & SATELLITE
    # ================================================================

    c.execute("""CREATE TABLE IF NOT EXISTS stations_meteo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type TEXT,
        latitude REAL,
        longitude REAL,
        altitude REAL,
        region_id INTEGER,
        statut TEXT DEFAULT 'Active',
        api_source TEXT,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (region_id) REFERENCES regions(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS donnees_meteo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        station_id INTEGER,
        village_id INTEGER,
        date_mesure TEXT NOT NULL,
        temperature_min REAL,
        temperature_max REAL,
        temperature_moy REAL,
        humidite_pct REAL,
        pluviometrie_mm REAL,
        vent_vitesse_kmh REAL,
        vent_direction TEXT,
        pression_hpa REAL,
        rayonnement_solaire REAL,
        evapotranspiration_mm REAL,
        source TEXT DEFAULT 'Manuel',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (station_id) REFERENCES stations_meteo(id),
        FOREIGN KEY (village_id) REFERENCES villages(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS previsions_meteo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        village_id INTEGER,
        date_prevision TEXT NOT NULL,
        temperature_min REAL,
        temperature_max REAL,
        pluviometrie_probable_pct REAL,
        pluviometrie_mm REAL,
        humidite_pct REAL,
        vent_kmh REAL,
        conseil_agricole TEXT,
        confiance_pct REAL,
        source TEXT DEFAULT 'API',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (village_id) REFERENCES villages(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS images_satellite (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parcelle_id INTEGER NOT NULL,
        date_image TEXT NOT NULL,
        satellite TEXT,
        ndvi_moyen REAL,
        ndvi_min REAL,
        ndvi_max REAL,
        ndwi REAL,
        ndre REAL,
        stress_hydrique INTEGER DEFAULT 0,
        stress_azote INTEGER DEFAULT 0,
        anomalie_detectee TEXT,
        image_path TEXT,
        source TEXT DEFAULT 'Sentinel-2',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS alertes_agro (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_alerte TEXT NOT NULL,
        gravite TEXT DEFAULT 'Info',
        titre TEXT NOT NULL,
        message TEXT,
        region_id INTEGER,
        village_id INTEGER,
        parcelle_id INTEGER,
        producteur_id INTEGER,
        date_debut TEXT,
        date_fin TEXT,
        action_recommandee TEXT,
        statut TEXT DEFAULT 'Active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ================================================================
    # ÉLEVAGE
    # ================================================================

    c.execute("""CREATE TABLE IF NOT EXISTS especes_animales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        nom_scientifique TEXT,
        categorie TEXT,
        cycle_reproduction_jours INTEGER,
        duree_gestation_jours INTEGER,
        age_maturite_mois INTEGER,
        production_lait_l_jour REAL,
        poids_adulte_kg REAL,
        icone TEXT,
        actif INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS troupeaux (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        producteur_id INTEGER NOT NULL,
        espece_id INTEGER NOT NULL,
        nom TEXT,
        race TEXT,
        effectif_total INTEGER DEFAULT 0,
        effectif_femelles INTEGER DEFAULT 0,
        effectif_males INTEGER DEFAULT 0,
        effectif_jeunes INTEGER DEFAULT 0,
        mode_elevage TEXT,
        lieu_garde TEXT,
        gps_latitude REAL,
        gps_longitude REAL,
        objectif TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id),
        FOREIGN KEY (espece_id) REFERENCES especes_animales(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS animaux (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_boucle TEXT UNIQUE NOT NULL,
        troupeau_id INTEGER NOT NULL,
        nom TEXT,
        sexe TEXT,
        date_naissance TEXT,
        poids_kg REAL,
        race TEXT,
        pere_id INTEGER,
        mere_id INTEGER,
        etat_sante TEXT DEFAULT 'Bon',
        stade_physiologique TEXT,
        derniere_gestation TEXT,
        date_derniere_insemination TEXT,
        production_lait_moyenne_l REAL,
        statut TEXT DEFAULT 'Actif',
        photo_path TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (troupeau_id) REFERENCES troupeaux(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sante_animale (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal_id INTEGER,
        troupeau_id INTEGER,
        date_intervention TEXT NOT NULL,
        type_intervention TEXT,
        maladie_suspectee TEXT,
        diagnostic TEXT,
        medicament TEXT,
        dose TEXT,
        veterinaire TEXT,
        cout INTEGER DEFAULT 0,
        statut TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (animal_id) REFERENCES animaux(id),
        FOREIGN KEY (troupeau_id) REFERENCES troupeaux(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS production_lait (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal_id INTEGER,
        troupeau_id INTEGER,
        date_production TEXT NOT NULL,
        quantite_litres REAL NOT NULL,
        moment TEXT,
        qualite TEXT,
        taux_matiere_grasse REAL,
        destination TEXT,
        prix_litre INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (animal_id) REFERENCES animaux(id),
        FOREIGN KEY (troupeau_id) REFERENCES troupeaux(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS alimentation_animale (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        troupeau_id INTEGER NOT NULL,
        date_alimentation TEXT NOT NULL,
        type_aliment TEXT,
        quantite_kg REAL,
        cout INTEGER DEFAULT 0,
        notes TEXT,
        FOREIGN KEY (troupeau_id) REFERENCES troupeaux(id)
    )""")

    # ================================================================
    # MOBILE MONEY & IA
    # ================================================================

    c.execute("""CREATE TABLE IF NOT EXISTS transactions_mobile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        producteur_id INTEGER,
        fournisseur TEXT NOT NULL,
        telephone TEXT,
        type_transaction TEXT,
        montant INTEGER NOT NULL,
        frais INTEGER DEFAULT 0,
        statut TEXT DEFAULT 'En attente',
        objet TEXT,
        reference_externe TEXT,
        solde_avant INTEGER,
        solde_apres INTEGER,
        date_transaction TEXT DEFAULT CURRENT_TIMESTAMP,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS diagnostics_ia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producteur_id INTEGER,
        parcelle_id INTEGER,
        culture_parcelle_id INTEGER,
        date_diagnostic TEXT NOT NULL,
        photo_path TEXT,
        type_diagnostic TEXT,
        maladie_detectee TEXT,
        confiance_pct REAL,
        severite TEXT,
        recommandation TEXT,
        traitement_propose TEXT,
        statut TEXT DEFAULT 'Nouveau',
        retour_producteur TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id),
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS scores_credit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producteur_id INTEGER NOT NULL,
        date_evaluation TEXT NOT NULL,
        score INTEGER NOT NULL,
        niveau TEXT,
        production_totale REAL,
        regularite_production REAL,
        superficie_cultivee REAL,
        historique_ventes INTEGER,
        remboursements_precedents INTEGER,
        recommandation_credit INTEGER,
        partenaire_financier TEXT,
        details_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id)
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
        producteur_id INTEGER,
        parcelle_id INTEGER,
        date_prediction TEXT NOT NULL,
        type_prediction TEXT,
        valeur_predite REAL,
        unite TEXT,
        intervalle_confiance TEXT,
        confiance_pct REAL,
        donnees_entree_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (modele_id) REFERENCES modeles_ia(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS messages_vocaux (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producteur_id INTEGER,
        date_message TEXT NOT NULL,
        langue TEXT DEFAULT 'Wolof',
        audio_path TEXT,
        transcription TEXT,
        type_demande TEXT,
        reponse_texte TEXT,
        reponse_audio_path TEXT,
        statut TEXT DEFAULT 'Traité',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id)
    )""")

    # ================================================================
    # COMMERCIALISATION
    # ================================================================

    c.execute("""CREATE TABLE IF NOT EXISTS recoltes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        culture_parcelle_id INTEGER,
        producteur_id INTEGER NOT NULL,
        parcelle_id INTEGER,
        culture_id INTEGER,
        date_recolte TEXT NOT NULL,
        quantite_kg REAL NOT NULL,
        qualite TEXT,
        humidite_pct REAL,
        destination TEXT DEFAULT 'Stock',
        prix_vente_kg INTEGER,
        acheteur TEXT,
        photo_path TEXT,
        gps_latitude REAL,
        gps_longitude REAL,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id),
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id),
        FOREIGN KEY (culture_id) REFERENCES cultures(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS stocks_produits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producteur_id INTEGER NOT NULL,
        culture_id INTEGER NOT NULL,
        qualite TEXT,
        quantite_kg REAL DEFAULT 0,
        quantite_reservee_kg REAL DEFAULT 0,
        prix_revient_kg INTEGER,
        date_derniere_entree TEXT,
        date_derniere_sortie TEXT,
        emplacement TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id),
        FOREIGN KEY (culture_id) REFERENCES cultures(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS acheteurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type TEXT,
        contact_nom TEXT,
        telephone TEXT,
        email TEXT,
        adresse TEXT,
        ville TEXT,
        produits_recherches TEXT,
        volume_annuel_t REAL,
        mode_paiement TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS offres_achat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        acheteur_id INTEGER NOT NULL,
        culture_id INTEGER NOT NULL,
        quantite_kg REAL NOT NULL,
        prix_propose_kg INTEGER NOT NULL,
        qualite_requise TEXT,
        date_limite TEXT,
        conditions TEXT,
        statut TEXT DEFAULT 'Active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (acheteur_id) REFERENCES acheteurs(id),
        FOREIGN KEY (culture_id) REFERENCES cultures(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ventes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        producteur_id INTEGER NOT NULL,
        acheteur_id INTEGER,
        acheteur_nom TEXT,
        date_vente TEXT NOT NULL,
        culture_id INTEGER,
        quantite_kg REAL NOT NULL,
        prix_unitaire_kg INTEGER NOT NULL,
        montant_total INTEGER NOT NULL,
        frais_transport INTEGER DEFAULT 0,
        frais_autres INTEGER DEFAULT 0,
        montant_net INTEGER,
        mode_paiement TEXT,
        statut_paiement TEXT DEFAULT 'En attente',
        date_paiement TEXT,
        reference_mobile_money TEXT,
        livraison_statut TEXT DEFAULT 'À livrer',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id),
        FOREIGN KEY (acheteur_id) REFERENCES acheteurs(id),
        FOREIGN KEY (culture_id) REFERENCES cultures(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS prix_marche (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        culture_id INTEGER NOT NULL,
        marche TEXT,
        region_id INTEGER,
        date_releve TEXT NOT NULL,
        prix_min INTEGER,
        prix_moyen INTEGER,
        prix_max INTEGER,
        unite TEXT DEFAULT 'kg',
        tendance TEXT,
        source TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (culture_id) REFERENCES cultures(id),
        FOREIGN KEY (region_id) REFERENCES regions(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS contrats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        type_contrat TEXT,
        producteur_id INTEGER,
        acheteur_id INTEGER,
        cooperative_id INTEGER,
        culture_id INTEGER,
        quantite_kg REAL,
        prix_unitaire_kg INTEGER,
        montant_total INTEGER,
        date_signature TEXT,
        date_debut TEXT,
        date_fin TEXT,
        conditions TEXT,
        statut TEXT DEFAULT 'Actif',
        document_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id),
        FOREIGN KEY (acheteur_id) REFERENCES acheteurs(id),
        FOREIGN KEY (culture_id) REFERENCES cultures(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS transport_livraisons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        vente_id INTEGER,
        type_transport TEXT,
        transporteur TEXT,
        telephone_transporteur TEXT,
        vehicule_immat TEXT,
        chauffeur_nom TEXT,
        lieu_enlevement TEXT,
        lieu_livraison TEXT,
        distance_km REAL,
        cout_transport INTEGER,
        date_enlevement TEXT,
        date_livraison_prevue TEXT,
        date_livraison_reelle TEXT,
        statut TEXT DEFAULT 'Planifié',
        bons_livraison TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ================================================================
    # FINANCE
    # ================================================================

    c.execute("""CREATE TABLE IF NOT EXISTS institutions_financement (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type TEXT,
        telephone TEXT,
        email TEXT,
        contact_nom TEXT,
        produits_disponibles TEXT,
        taux_min_pct REAL,
        taux_max_pct REAL,
        montant_min INTEGER,
        montant_max INTEGER,
        actif INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS credits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        producteur_id INTEGER NOT NULL,
        institution_id INTEGER,
        type_credit TEXT,
        montant_demande INTEGER,
        montant_accorde INTEGER,
        taux_interet REAL,
        duree_mois INTEGER,
        date_demande TEXT,
        date_accord TEXT,
        date_decaissement TEXT,
        date_premiere_echeance TEXT,
        montant_rembourse INTEGER DEFAULT 0,
        solde_restant INTEGER,
        statut TEXT DEFAULT 'Demandé',
        objet TEXT,
        garanties TEXT,
        score_credit INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id),
        FOREIGN KEY (institution_id) REFERENCES institutions_financement(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS echeances_credit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        credit_id INTEGER NOT NULL,
        numero_echeance INTEGER,
        date_echeance TEXT NOT NULL,
        montant_capital INTEGER,
        montant_interet INTEGER,
        montant_total INTEGER,
        montant_paye INTEGER DEFAULT 0,
        date_paiement TEXT,
        statut TEXT DEFAULT 'À venir',
        reference_paiement TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (credit_id) REFERENCES credits(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS subventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        producteur_id INTEGER,
        cooperative_id INTEGER,
        programme TEXT,
        bailleur TEXT,
        type_subvention TEXT,
        montant INTEGER,
        objet TEXT,
        date_attribution TEXT,
        date_decaissement TEXT,
        statut TEXT DEFAULT 'En attente',
        conditions TEXT,
        document_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS assurances_agricoles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        producteur_id INTEGER NOT NULL,
        parcelle_id INTEGER,
        type_assurance TEXT,
        compagnie TEXT,
        culture_id INTEGER,
        superficie_assuree REAL,
        capital_assure INTEGER,
        prime INTEGER,
        date_souscription TEXT,
        date_debut TEXT,
        date_fin TEXT,
        statut TEXT DEFAULT 'Active',
        sinistres_declares INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id),
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sinistres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        assurance_id INTEGER,
        producteur_id INTEGER,
        date_sinistre TEXT NOT NULL,
        type_sinistre TEXT,
        description TEXT,
        superficie_affectee REAL,
        pertes_estimees INTEGER,
        montant_indemnisation INTEGER,
        statut TEXT DEFAULT 'Déclaré',
        date_indemnisation TEXT,
        photos TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assurance_id) REFERENCES assurances_agricoles(id)
    )""")

    # ================================================================
    # COOPÉRATIVES
    # ================================================================

    c.execute("""CREATE TABLE IF NOT EXISTS membres_cooperative (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cooperative_id INTEGER NOT NULL,
        producteur_id INTEGER NOT NULL,
        date_adhesion TEXT,
        role TEXT DEFAULT 'Membre',
        cotisation_annuelle INTEGER DEFAULT 0,
        statut TEXT DEFAULT 'Actif',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cooperative_id) REFERENCES cooperatives(id),
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cotisations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cooperative_id INTEGER NOT NULL,
        producteur_id INTEGER NOT NULL,
        annee INTEGER,
        montant INTEGER,
        date_paiement TEXT,
        mode_paiement TEXT,
        reference TEXT,
        statut TEXT DEFAULT 'Payé',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cooperative_id) REFERENCES cooperatives(id),
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ventes_groupees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        cooperative_id INTEGER NOT NULL,
        acheteur_id INTEGER,
        acheteur_nom TEXT,
        culture_id INTEGER,
        quantite_totale_kg REAL,
        prix_unitaire_kg INTEGER,
        montant_total INTEGER,
        nb_producteurs INTEGER,
        date_vente TEXT,
        date_livraison TEXT,
        statut TEXT DEFAULT 'En cours',
        repartition_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cooperative_id) REFERENCES cooperatives(id),
        FOREIGN KEY (culture_id) REFERENCES cultures(id)
    )""")

    # ================================================================
    # SYSTÈME
    # ================================================================

    c.execute("""CREATE TABLE IF NOT EXISTS utilisateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nom TEXT,
        prenom TEXT,
        email TEXT,
        telephone TEXT,
        role TEXT DEFAULT 'producteur',
        producteur_id INTEGER,
        cooperative_id INTEGER,
        village_id INTEGER,
        region_id INTEGER,
        langue TEXT DEFAULT 'fr',
        actif INTEGER DEFAULT 1,
        dernier_login TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producteur_id) REFERENCES producteurs(id)
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
        gps_latitude REAL,
        gps_longitude REAL,
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

    # Index performance
    c.execute("CREATE INDEX IF NOT EXISTS idx_parcelles_prod ON parcelles(producteur_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cultures_parc ON cultures_parcelles(parcelle_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_recoltes_prod ON recoltes(producteur_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ventes_prod ON ventes(producteur_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ventes_date ON ventes(date_vente)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_meteo_date ON donnees_meteo(date_mesure)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_transactions_prod ON transactions_mobile(producteur_id)")

    conn.commit()

    # Données démo
    c.execute("SELECT COUNT(*) FROM regions")
    if c.fetchone()[0] == 0:
        print("[INIT] Insertion données démo Sénégal...")
        _seed_data(c)
        conn.commit()

    conn.close()
    print(f"[INIT] ✅ Base prête : {DB_PATH}")


def _seed_data(c):
    """Insère les données de démonstration"""

    # ============ RÉGIONS DU SÉNÉGAL ============
    regions = [
        ('DKR', 'Dakar', 'Dakar', 550, 4000000, 'Niayes', 500),
        ('THS', 'Thiès', 'Thiès', 6670, 2000000, 'Bassin arachidier', 600),
        ('DBL', 'Diourbel', 'Diourbel', 4824, 1700000, 'Bassin arachidier', 550),
        ('FTK', 'Fatick', 'Fatick', 6849, 800000, 'Bassin arachidier', 700),
        ('KLC', 'Kaolack', 'Kaolack', 5357, 1200000, 'Bassin arachidier', 700),
        ('KFL', 'Kaffrine', 'Kaffrine', 11262, 700000, 'Bassin arachidier', 650),
        ('SLS', 'Saint-Louis', 'Saint-Louis', 19241, 1000000, 'Vallée fleuve', 300),
        ('LOU', 'Louga', 'Louga', 24847, 1000000, 'Sylvopastorale', 400),
        ('MTM', 'Matam', 'Matam', 29445, 700000, 'Vallée fleuve', 400),
        ('TMB', 'Tambacounda', 'Tambacounda', 42564, 800000, 'Soudanienne', 800),
        ('KDG', 'Kédougou', 'Kédougou', 16800, 200000, 'Soudanienne', 1000),
        ('KOL', 'Kolda', 'Kolda', 21011, 700000, 'Casamance', 1000),
        ('ZIG', 'Ziguinchor', 'Ziguinchor', 7352, 600000, 'Casamance', 1200),
        ('SED', 'Sédhiou', 'Sédhiou', 7341, 500000, 'Casamance', 1100),
    ]
    for code, nom, chef, sup, pop, zone, pluv in regions:
        c.execute("""INSERT INTO regions (code, nom, chef_lieu, superficie_km2, population, zone_agro, pluviometrie_mm)
                     VALUES (?,?,?,?,?,?,?)""", (code, nom, chef, sup, pop, zone, pluv))

    # ============ DÉPARTEMENTS (exemples) ============
    deps = [
        (1, 'DKR-PIK', 'Pikine', 'Pikine'),
        (1, 'DKR-GUE', 'Guédiawaye', 'Guédiawaye'),
        (2, 'THS-THS', 'Thiès', 'Thiès'),
        (2, 'THS-MBR', 'Mbour', 'Mbour'),
        (2, 'THS-TBA', 'Tivaouane', 'Tivaouane'),
        (3, 'DBL-BMB', 'Bambey', 'Bambey'),
        (3, 'DBL-MBR', 'Mbacké', 'Mbacké'),
        (6, 'KFL-KFL', 'Kaffrine', 'Kaffrine'),
        (7, 'SLS-SLS', 'Saint-Louis', 'Saint-Louis'),
        (9, 'MTM-MTM', 'Matam', 'Matam'),
        (10, 'TMB-TMB', 'Tambacounda', 'Tambacounda'),
        (13, 'ZIG-ZIG', 'Ziguinchor', 'Ziguinchor'),
    ]
    for reg_id, code, nom, chef in deps:
        c.execute("""INSERT INTO departements (region_id, code, nom, chef_lieu)
                     VALUES (?,?,?,?)""", (reg_id, code, nom, chef))

    # ============ VILLAGES (exemples) ============
    # Villages — avec lookup par code département (sécurisé)
    villages_data = [
        ('DKR-PIK', 'VIL-001', 'Keur Massar', 14.7833, -17.3167, 15000, 2000, 'Forage', '4G'),
        ('DKR-GUE', 'VIL-002', 'Guédiawaye Centre', 14.7667, -17.4000, 25000, 3000, 'Réseau', '4G'),
        ('THS-THS', 'VIL-003', 'Notto Gouye Diama', 14.7500, -16.9333, 3000, 400, 'Forage', '3G'),
        ('THS-MBR', 'VIL-004', 'Saly Portudal', 14.4500, -17.0000, 5000, 800, 'Réseau', '4G'),
        ('DBL-BMB', 'VIL-005', 'Baba Garage', 14.8833, -16.5500, 4000, 500, 'Puits', '3G'),
        ('KFL-KFL', 'VIL-006', 'Kaffrine Centre', 14.1000, -15.5500, 8000, 1000, 'Forage', '4G'),
        ('SLS-SLS', 'VIL-007', 'Ross Béthio', 16.2667, -16.2333, 6000, 700, 'Fleuve', '3G'),
        ('MTM-MTM', 'VIL-008', 'Ourossogui', 15.6000, -13.3167, 10000, 1200, 'Fleuve', '4G'),
        ('TMB-TMB', 'VIL-009', 'Tambacounda Centre', 13.7833, -13.6667, 20000, 2500, 'Forage', '4G'),
        ('ZIG-ZIG', 'VIL-010', 'Ziguinchor Centre', 12.5667, -16.2667, 25000, 3000, 'Réseau', '4G'),
    ]
    for dep_code, code, nom, lat, lon, pop, men, eau, res in villages_data:
        c.execute("SELECT id FROM departements WHERE code=?", (dep_code,))
        row = c.fetchone()
        if not row:
            continue
        c.execute("""INSERT INTO villages (departement_id, code, nom, latitude, longitude, population, nb_menages, acces_eau, couverture_reseau)
                     VALUES (?,?,?,?,?,?,?,?,?)""", (row['id'], code, nom, lat, lon, pop, men, eau, res))

    # ============ CULTURES PRINCIPALES DU SÉNÉGAL ============
    cultures = [
        # (code, nom, nom_sc, nom_wolof, cat, cycle_min, cycle_max, saison, zone, eau, rendement, prix, icone)
        ('MIL', 'Mil', 'Pennisetum glaucum', 'Duum', 'Céréale', 75, 100, 'Hivernage', 'Bassin arachidier', 400, 1.2, 200, 'fa-seedling'),
        ('SORGHO', 'Sorgho', 'Sorghum bicolor', 'Mbind', 'Céréale', 90, 130, 'Hivernage', 'Bassin arachidier', 500, 1.5, 180, 'fa-seedling'),
        ('MAIS', 'Maïs', 'Zea mays', 'Mboq', 'Céréale', 90, 120, 'Hivernage', 'Toutes zones', 600, 2.5, 175, 'fa-seedling'),
        ('RIZ', 'Riz', 'Oryza sativa', 'Ceeb', 'Céréale', 110, 150, 'Saison sèche', 'Vallée fleuve', 1200, 4.0, 250, 'fa-seedling'),
        ('ARACHIDE', 'Arachide', 'Arachis hypogaea', 'Tiga', 'Légumineuse', 90, 120, 'Hivernage', 'Bassin arachidier', 550, 1.5, 300, 'fa-seedling'),
        ('NIEBE', 'Niébé', 'Vigna unguiculata', 'Ñebbe', 'Légumineuse', 60, 90, 'Hivernage', 'Toutes zones', 400, 1.0, 350, 'fa-seedling'),
        ('COTON', 'Coton', 'Gossypium hirsutum', 'Koton', 'Fibre', 150, 180, 'Hivernage', 'Sénégal oriental', 700, 1.2, 250, 'fa-seedling'),
        ('SESAME', 'Sésame', 'Sesamum indicum', 'Sesam', 'Oléagineux', 90, 120, 'Hivernage', 'Casamance', 500, 0.8, 800, 'fa-seedling'),
        ('TOMATE', 'Tomate', 'Solanum lycopersicum', 'Tamaate', 'Maraîchage', 90, 120, 'Contre-saison', 'Niayes', 600, 25.0, 400, 'fa-apple-alt'),
        ('OIGNON', 'Oignon', 'Allium cepa', 'Soble', 'Maraîchage', 100, 140, 'Contre-saison', 'Niayes', 700, 20.0, 350, 'fa-apple-alt'),
        ('POMME_TERRE', 'Pomme de terre', 'Solanum tuberosum', 'Pomme de terre', 'Maraîchage', 80, 100, 'Contre-saison', 'Niayes', 600, 15.0, 300, 'fa-apple-alt'),
        ('CAROTTE', 'Carotte', 'Daucus carota', 'Carotte', 'Maraîchage', 90, 110, 'Contre-saison', 'Niayes', 500, 20.0, 350, 'fa-apple-alt'),
        ('CHOU', 'Chou', 'Brassica oleracea', 'Chou', 'Maraîchage', 80, 110, 'Contre-saison', 'Niayes', 500, 25.0, 250, 'fa-apple-alt'),
        ('PASTEQUE', 'Pastèque', 'Citrullus lanatus', 'Pastèque', 'Maraîchage', 80, 100, 'Contre-saison', 'Niayes', 500, 20.0, 200, 'fa-apple-alt'),
        ('MANGUE', 'Mangue', 'Mangifera indica', 'Mango', 'Fruit', 1095, 1825, 'Pérenne', 'Casamance', 800, 15.0, 500, 'fa-tree'),
        ('ANACARDE', 'Anacarde', 'Anacardium occidentale', 'Anacardier', 'Fruit sec', 1095, 1460, 'Pérenne', 'Casamance', 900, 2.0, 600, 'fa-tree'),
    ]
    for code, nom, nom_sc, wolof, cat, cmin, cmax, saison, zone, eau, rend, prix, ico in cultures:
        c.execute("""INSERT INTO cultures
                     (code, nom, nom_scientifique, nom_wolof, categorie, cycle_jours_min, cycle_jours_max,
                      saison_recommandee, zone_agro, besoin_eau_mm, rendement_theorique_t_ha, prix_moyen_kg, icone)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (code, nom, nom_sc, wolof, cat, cmin, cmax, saison, zone, eau, rend, prix, ico))

    # ============ ESPÈCES ANIMALES ============
    especes = [
        ('BOVIN', 'Bovin', 'Bos taurus', 'Bétail', 365, 280, 24, 5.0, 350, 'fa-cow'),
        ('OVIN', 'Ovin', 'Ovis aries', 'Mouton', 240, 150, 12, 1.5, 50, 'fa-sheep'),
        ('CAPRIN', 'Caprin', 'Capra hircus', 'Chèvre', 240, 150, 12, 2.0, 40, 'fa-goat'),
        ('VOLAILLE', 'Volaille', 'Gallus gallus', 'Poule', 365, 21, 6, 0, 2, 'fa-dove'),
        ('EQUIN', 'Équin', 'Equus caballus', 'Cheval', 365, 340, 36, 0, 400, 'fa-horse'),
        ('CAMELIN', 'Camélin', 'Camelus dromedarius', 'Chameau', 730, 380, 48, 15.0, 500, 'fa-horse'),
    ]
    for code, nom, nom_sc, cat, cycle, gest, mat, lait, poids, ico in especes:
        c.execute("""INSERT INTO especes_animales
                     (code, nom, nom_scientifique, categorie, cycle_reproduction_jours, duree_gestation_jours,
                      age_maturite_mois, production_lait_l_jour, poids_adulte_kg, icone)
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (code, nom, nom_sc, cat, cycle, gest, mat, lait, poids, ico))

    # ============ INTRANTS ============
    intrants = [
        ('SEM-MIL-001', 'Semence Mil IBV 8004', 'Semence', 'Certifiée', 'Variété améliorée', 'kg', 1500, 'ISRA', 500, 100, 'ISRA-2019', None),
        ('SEM-AR-001', 'Semence Arachide 55-437', 'Semence', 'Certifiée', 'Variété précoce', 'kg', 2500, 'ISRA', 800, 150, 'ISRA-2020', None),
        ('ENG-NPK-15', 'Engrais NPK 15-15-15', 'Engrais', 'Minéral', 'NPK 15-15-15', 'kg', 350, 'SENCHIM', 2000, 500, 'HOM-2023', None),
        ('ENG-UREE-46', 'Urée 46% N', 'Engrais', 'Minéral', 'Urée 46%', 'kg', 320, 'SENCHIM', 1500, 400, 'HOM-2023', None),
        ('PEST-NEEM', 'Insecticide Neem', 'Pesticide', 'Bio', 'Azadirachtine', 'L', 5000, 'Bio Sénégal', 200, 50, 'BIO-2024', '2027-12-31'),
        ('HERB-GLY', 'Herbicide Glyphosate', 'Herbicide', 'Chimique', 'Glyphosate 48%', 'L', 4500, 'Agro Sen', 300, 80, 'HOM-2023', '2026-06-30'),
    ]
    for code, nom, cat, typ, comp, unite, prix, four, stock, alerte, hom, perem in intrants:
        c.execute("""INSERT INTO intrants
                     (code, nom, categorie, type, composition, unite, prix_unitaire, fournisseur,
                      stock_disponible, stock_alerte, homologation, date_peremption)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (code, nom, cat, typ, comp, unite, prix, four, stock, alerte, hom, perem))

    # ============ PARAMÈTRES ============
    params = [
        ('devise', 'FCFA', 'text', 'Devise principale'),
        ('superficie_max_ha', '1000', 'float', 'Superficie max parcelle'),
        ('alerte_stock_jours', '30', 'int', 'Alerte stock bas avant jours'),
        ('gps_precision_m', '10', 'int', 'Précision GPS requise (m)'),
        ('ndvi_stress_seuil', '0.3', 'float', 'Seuil NDVI stress hydrique'),
        ('score_credit_min', '400', 'int', 'Score crédit minimum'),
        ('score_credit_max', '850', 'int', 'Score crédit maximum'),
        ('tva_pct', '18', 'int', 'TVA Sénégal'),
        ('api_meteo_key', '', 'text', 'Clé API météo (OpenWeather)'),
        ('api_satellite_url', 'https://api.sentinel-hub.com', 'text', 'API satellite'),
        ('mobile_money_wave', '1', 'int', 'Wave activé'),
        ('mobile_money_om', '1', 'int', 'Orange Money activé'),
        ('mobile_money_free', '1', 'int', 'Free Money activé'),
        ('langue_defaut', 'fr', 'text', 'Langue par défaut'),
        ('langues_supportees', 'fr,wo,en', 'text', 'Langues supportées'),
        ('ia_diagnostic_actif', '1', 'int', 'IA diagnostic maladies'),
        ('assistant_vocal_actif', '1', 'int', 'Assistant vocal Wolof'),
    ]
    for cle, val, typ, desc in params:
        c.execute("""INSERT INTO parametres (cle, valeur, type, description)
                     VALUES (?,?,?,?)""", (cle, val, typ, desc))

    # ============ UTILISATEURS ============
    def h(pwd):
        return hashlib.sha256(pwd.encode()).hexdigest()

    users = [
        ('admin', h('admin123'), 'Admin', 'Omega', 'admin@agri.sn', 'admin'),
        ('direction', h('dir123'), 'Diop', 'Mamadou', 'dir@agri.sn', 'direction'),
        ('coop1', h('coop123'), 'Fall', 'Omar', 'coop1@agri.sn', 'cooperative'),
        ('prod1', h('prod123'), 'Ndiaye', 'Ibrahima', 'prod1@agri.sn', 'producteur'),
        ('tech1', h('tech123'), 'Ba', 'Fatou', 'tech1@agri.sn', 'technicien'),
        ('fin1', h('fin123'), 'Sow', 'Aminata', 'fin1@agri.sn', 'finance'),
        ('acheteur1', h('ach123'), 'Sarr', 'Cheikh', 'ach1@agri.sn', 'acheteur'),
    ]
    for username, pwd, nom, prenom, email, role in users:
        c.execute("""INSERT INTO utilisateurs (username, password_hash, nom, prenom, email, role, actif)
                     VALUES (?,?,?,?,?,?,1)""", (username, pwd, nom, prenom, email, role))

    # ============ COOPÉRATIVES ============
    coops = [
        ('COOP-001', 'Coopérative Keur Massar', 'Agricole', 'VIL-001'),
        ('COOP-002', 'Coopérative Notto', 'Agricole', 'VIL-003'),
        ('COOP-003', 'Coopérative Ross Béthio', 'Rizicole', 'VIL-007'),
        ('COOP-004', 'Coopérative Ourossogui', 'Agro-pastorale', 'VIL-008'),
    ]
    for code, nom, typ, village_code in coops:
        c.execute("SELECT id FROM villages WHERE code=?", (village_code,))
        row = c.fetchone()
        vid = row['id'] if row else None
        c.execute("""INSERT INTO cooperatives (code, nom, type, village_id, nb_membres, actif)
                     VALUES (?,?,?,?,0,1)""", (code, nom, typ, vid))

    # ============ PRODUCTEURS (démo) ============
    producteurs = [
        ('PRD-0001', 'Ndiaye', 'Ibrahima', 'M', '77 111 11 11', 'VIL-001', 'COOP-001'),
        ('PRD-0002', 'Diop', 'Fatou', 'F', '77 222 22 22', 'VIL-001', 'COOP-001'),
        ('PRD-0003', 'Fall', 'Omar', 'M', '77 333 33 33', 'VIL-003', 'COOP-002'),
        ('PRD-0004', 'Sow', 'Aminata', 'F', '77 444 44 44', 'VIL-003', 'COOP-002'),
        ('PRD-0005', 'Sarr', 'Cheikh', 'M', '77 555 55 55', 'VIL-007', 'COOP-003'),
        ('PRD-0006', 'Ba', 'Awa', 'F', '77 666 66 66', 'VIL-008', 'COOP-004'),
        ('PRD-0007', 'Diallo', 'Moussa', 'M', '77 777 77 77', 'VIL-004', 'COOP-002'),
        ('PRD-0008', 'Kane', 'Mariama', 'F', '77 888 88 88', 'VIL-009', None),
    ]
    for i, (code, nom, prenom, sexe, tel, village_code, coop_code) in enumerate(producteurs, 1):
        # Lookup village
        c.execute("SELECT id FROM villages WHERE code=?", (village_code,))
        row = c.fetchone()
        village_id = row['id'] if row else None

        # Lookup coop
        coop_id = None
        if coop_code:
            c.execute("SELECT id FROM cooperatives WHERE code=?", (coop_code,))
            row = c.fetchone()
            coop_id = row['id'] if row else None

        c.execute("""INSERT INTO producteurs
            (code, nom, prenom, sexe, telephone, village_id, cooperative_id,
             exploitation_nom, superficie_totale, type_exploitation, experience_annees,
             langue_principale, mobile_money_type, mobile_money_numero, actif)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
            (code, nom, prenom, sexe, tel, village_id, coop_id,
             f"Ferme {nom}", 5.0 + i, 'Familiale', 5 + i,
             'Wolof', 'Wave', tel.replace(' ', '')))

    # ============ MARCHÉS ============
    # Acheteurs
    acheteurs = [
        ('ACH-001', 'SONACOS', 'Industriel', 'M. Diagne', '33 839 00 00', 'sonacos@sn'),
        ('ACH-002', 'Grands Moulins', 'Industriel', 'Mme Sy', '33 859 00 00', 'gm@sn'),
        ('ACH-003', 'Exportateur Anacarde', 'Exportateur', 'M. Coly', '33 991 00 00', 'expa@sn'),
    ]
    for code, nom, typ, contact, tel, email in acheteurs:
        c.execute("""INSERT INTO acheteurs (code, nom, type, contact_nom, telephone, email, actif)
                     VALUES (?,?,?,?,?,?,1)""", (code, nom, typ, contact, tel, email))

    # Institutions de financement
    institutions = [
        ('CNCAS', 'CNCAS', 'Banque agricole', '33 839 00 00', 7.0, 12.0, 100000, 50000000),
        ('BNDE', 'BNDE', 'Banque', '33 839 11 11', 8.0, 14.0, 500000, 100000000),
        ('PAMECAS', 'PAMECAS', 'SFD', '33 859 22 22', 10.0, 18.0, 50000, 10000000),
        ('BAOBAB', 'Baobab', 'SFD', '33 839 33 33', 12.0, 20.0, 25000, 5000000),
    ]
    for code, nom, typ, tel, tmin, tmax, mmin, mmax in institutions:
        c.execute("""INSERT INTO institutions_financement
                     (code, nom, type, telephone, taux_min_pct, taux_max_pct, montant_min, montant_max, actif)
                     VALUES (?,?,?,?,?,?,?,?,1)""", (code, nom, typ, tel, tmin, tmax, mmin, mmax))

    # Modèles IA
    modeles = [
        ('DIAG-PLANT', 'Diagnostic maladies plantes', 'CNN', 'v1.0', 92.5, 50000),
        ('PRED-REND', 'Prédiction rendement', 'RandomForest', 'v1.0', 85.3, 30000),
        ('SCORE-CRED', 'Scoring crédit agricole', 'GradientBoosting', 'v1.0', 88.7, 15000),
        ('ALERT-MAL', 'Alerte maladies épidémiques', 'LSTM', 'v1.0', 79.2, 20000),
    ]
    for code, nom, typ, ver, prec, taille in modeles:
        c.execute("""INSERT INTO modeles_ia (code, nom, type_modele, version, precision_pct, dataset_taille, statut)
                     VALUES (?,?,?,?,?,?,'Actif')""", (code, nom, typ, ver, prec, taille))

    print("[INIT] ✅ Données démo insérées (14 régions, 16 cultures, 6 espèces, 8 producteurs)")


if __name__ == '__main__':
    init_db()
