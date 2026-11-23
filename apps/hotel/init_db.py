"""
Base de données Gestion Hôtelière Omega
25 tables : types_chambres, chambres, clients, réservations,
tarifs, restaurants, menus, commandes, housekeeping, factures
"""
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "/app/data/hotel.db"


def init_db():
    os.makedirs("/app/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    c = conn.cursor()

    # ==================== 1. ÉTAGES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS etages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero INTEGER NOT NULL,
        nom TEXT,
        description TEXT,
        actif INTEGER DEFAULT 1
    )""")

    # ==================== 2. TYPES DE CHAMBRES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS types_chambres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        capacite_adultes INTEGER DEFAULT 2,
        capacite_enfants INTEGER DEFAULT 0,
        superficie_m2 REAL DEFAULT 0,
        lit_principal TEXT,
        nb_lits INTEGER DEFAULT 1,
        equipements TEXT,
        photo_url TEXT,
        ordre INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 3. CHAMBRES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS chambres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        type_id INTEGER NOT NULL,
        etage_id INTEGER NOT NULL,
        vue TEXT,
        statut TEXT DEFAULT 'Disponible',
        etat_proprete TEXT DEFAULT 'Propre',
        derniere_maintenance TEXT,
        prochaine_maintenance TEXT,
        notes TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (type_id) REFERENCES types_chambres(id),
        FOREIGN KEY (etage_id) REFERENCES etages(id)
    )""")

    # ==================== 4. CLIENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        type_client TEXT DEFAULT 'Particulier',
        civilite TEXT,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        date_naissance TEXT,
        nationalite TEXT DEFAULT 'Sénégalaise',
        sexe TEXT,
        piece_type TEXT,
        piece_numero TEXT,
        telephone TEXT NOT NULL,
        telephone_secondaire TEXT,
        email TEXT,
        adresse TEXT,
        ville TEXT,
        pays TEXT DEFAULT 'Sénégal',
        societe TEXT,
        numero_tva TEXT,
        preferences TEXT,
        allergies TEXT,
        vip INTEGER DEFAULT 0,
        points_fidelite INTEGER DEFAULT 0,
        nb_sejours INTEGER DEFAULT 0,
        total_depense REAL DEFAULT 0,
        notes TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 5. TARIFS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS tarifs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_chambre_id INTEGER NOT NULL,
        nom TEXT NOT NULL,
        type_tarif TEXT DEFAULT 'Standard',
        date_debut TEXT,
        date_fin TEXT,
        prix_nuit REAL NOT NULL,
        prix_semaine REAL,
        prix_mois REAL,
        petit_dejeuner_inclus INTEGER DEFAULT 0,
        taxe_sejour REAL DEFAULT 0,
        min_nuits INTEGER DEFAULT 1,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (type_chambre_id) REFERENCES types_chambres(id)
    )""")

    # ==================== 6. RÉSERVATIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        client_id INTEGER NOT NULL,
        chambre_id INTEGER,
        type_chambre_id INTEGER NOT NULL,
        date_arrivee TEXT NOT NULL,
        date_depart TEXT NOT NULL,
        nb_nuits INTEGER NOT NULL,
        nb_adultes INTEGER DEFAULT 1,
        nb_enfants INTEGER DEFAULT 0,
        statut TEXT DEFAULT 'Confirmée',
        source TEXT DEFAULT 'Direct',
        numero_externe TEXT,
        tarif_nuit REAL NOT NULL,
        sous_total REAL DEFAULT 0,
        taxe_sejour REAL DEFAULT 0,
        remise REAL DEFAULT 0,
        total REAL DEFAULT 0,
        acompte REAL DEFAULT 0,
        solde REAL DEFAULT 0,
        heure_arrivee_prevue TEXT,
        demandes_speciales TEXT,
        notes_internes TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (chambre_id) REFERENCES chambres(id),
        FOREIGN KEY (type_chambre_id) REFERENCES types_chambres(id)
    )""")

    # ==================== 7. SÉJOURS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS sejours (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reservation_id INTEGER NOT NULL,
        client_id INTEGER NOT NULL,
        chambre_id INTEGER NOT NULL,
        date_checkin TEXT NOT NULL,
        date_checkout TEXT,
        nb_nuits_reelles INTEGER DEFAULT 0,
        user_checkin INTEGER,
        user_checkout INTEGER,
        statut TEXT DEFAULT 'En cours',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (reservation_id) REFERENCES reservations(id),
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (chambre_id) REFERENCES chambres(id)
    )""")

    # ==================== 8. RESTAURANTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type TEXT DEFAULT 'Restaurant',
        description TEXT,
        horaire_ouverture TEXT,
        horaire_fermeture TEXT,
        capacite INTEGER DEFAULT 0,
        responsable TEXT,
        actif INTEGER DEFAULT 1
    )""")

    # ==================== 9. CATÉGORIES MENU ====================
    c.execute("""CREATE TABLE IF NOT EXISTS categories_menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        ordre INTEGER DEFAULT 0,
        icone TEXT,
        actif INTEGER DEFAULT 1
    )""")

    # ==================== 10. MENU (Plats) ====================
    c.execute("""CREATE TABLE IF NOT EXISTS menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        categorie_id INTEGER,
        restaurant_id INTEGER,
        type_plat TEXT DEFAULT 'Plat',
        prix REAL NOT NULL,
        cout_revient REAL DEFAULT 0,
        temps_preparation_min INTEGER DEFAULT 0,
        ingredients TEXT,
        allergenes TEXT,
        disponible INTEGER DEFAULT 1,
        chef_recommande INTEGER DEFAULT 0,
        photo_url TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (categorie_id) REFERENCES categories_menu(id),
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
    )""")

    # ==================== 11. COMMANDES RESTAURANT ====================
    c.execute("""CREATE TABLE IF NOT EXISTS commandes_resto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        restaurant_id INTEGER,
        sejour_id INTEGER,
        client_id INTEGER,
        chambre_id INTEGER,
        type_service TEXT DEFAULT 'Sur place',
        date_commande TEXT NOT NULL,
        heure_commande TEXT,
        nb_couverts INTEGER DEFAULT 1,
        statut TEXT DEFAULT 'Nouvelle',
        sous_total REAL DEFAULT 0,
        tva REAL DEFAULT 0,
        service REAL DEFAULT 0,
        total REAL DEFAULT 0,
        user_id INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(id),
        FOREIGN KEY (sejour_id) REFERENCES sejours(id),
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (chambre_id) REFERENCES chambres(id)
    )""")

    # ==================== 12. LIGNES COMMANDES RESTO ====================
    c.execute("""CREATE TABLE IF NOT EXISTS commande_resto_lignes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        commande_id INTEGER NOT NULL,
        plat_id INTEGER NOT NULL,
        designation TEXT NOT NULL,
        quantite INTEGER NOT NULL,
        prix_unitaire REAL NOT NULL,
        total_ligne REAL NOT NULL,
        commentaire TEXT,
        FOREIGN KEY (commande_id) REFERENCES commandes_resto(id),
        FOREIGN KEY (plat_id) REFERENCES menu(id)
    )""")

    # ==================== 13. HOUSEKEEPING - TÂCHES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS taches_housekeeping (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        chambre_id INTEGER NOT NULL,
        type_tache TEXT NOT NULL,
        priorite TEXT DEFAULT 'Normale',
        statut TEXT DEFAULT 'À faire',
        assignee_a INTEGER,
        date_creation TEXT NOT NULL,
        date_debut TEXT,
        date_fin TEXT,
        duree_minutes INTEGER,
        checklist TEXT,
        observations TEXT,
        signale_par INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chambre_id) REFERENCES chambres(id)
    )""")

    # ==================== 14. MAINTENANCE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS maintenance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        chambre_id INTEGER,
        equipement TEXT NOT NULL,
        type_probleme TEXT NOT NULL,
        description TEXT,
        priorite TEXT DEFAULT 'Normale',
        statut TEXT DEFAULT 'Signalé',
        signale_par INTEGER,
        assigne_a TEXT,
        date_signalement TEXT NOT NULL,
        date_intervention TEXT,
        date_resolution TEXT,
        cout REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chambre_id) REFERENCES chambres(id)
    )""")

    # ==================== 15. SERVICES ANNEXES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS services_annexes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        type TEXT,
        description TEXT,
        prix REAL DEFAULT 0,
        unite TEXT,
        actif INTEGER DEFAULT 1
    )""")

    # ==================== 16. CONSOMMATIONS SERVICES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS consommation_services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sejour_id INTEGER,
        client_id INTEGER,
        service_id INTEGER,
        quantite REAL DEFAULT 1,
        prix_unitaire REAL,
        total REAL,
        date_consommation TEXT NOT NULL,
        statut TEXT DEFAULT 'À facturer',
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sejour_id) REFERENCES sejours(id),
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (service_id) REFERENCES services_annexes(id)
    )""")

    # ==================== 17. FACTURES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS factures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        sejour_id INTEGER,
        client_id INTEGER NOT NULL,
        date_facture TEXT NOT NULL,
        date_echeance TEXT,
        sous_total_hebergement REAL DEFAULT 0,
        sous_total_resto REAL DEFAULT 0,
        sous_total_services REAL DEFAULT 0,
        remise REAL DEFAULT 0,
        tva REAL DEFAULT 0,
        taxe_sejour REAL DEFAULT 0,
        total REAL NOT NULL DEFAULT 0,
        montant_paye REAL DEFAULT 0,
        solde REAL DEFAULT 0,
        mode_paiement TEXT,
        statut TEXT DEFAULT 'Impayé',
        notes TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sejour_id) REFERENCES sejours(id),
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    # ==================== 18. LIGNES FACTURES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS facture_lignes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        facture_id INTEGER NOT NULL,
        categorie TEXT,
        designation TEXT NOT NULL,
        quantite REAL DEFAULT 1,
        prix_unitaire REAL NOT NULL,
        total_ligne REAL NOT NULL,
        date_origine TEXT,
        FOREIGN KEY (facture_id) REFERENCES factures(id)
    )""")

    # ==================== 19. PAIEMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS paiements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        facture_id INTEGER,
        reservation_id INTEGER,
        client_id INTEGER,
        type_paiement TEXT DEFAULT 'Paiement',
        date_paiement TEXT NOT NULL,
        montant REAL NOT NULL,
        devise TEXT DEFAULT 'FCFA',
        mode_paiement TEXT NOT NULL,
        reference TEXT,
        statut TEXT DEFAULT 'Validé',
        user_id INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (facture_id) REFERENCES factures(id),
        FOREIGN KEY (reservation_id) REFERENCES reservations(id),
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    # ==================== 20. OTA (Sites de réservation) ====================
    c.execute("""CREATE TABLE IF NOT EXISTS ota (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        commission_pct REAL DEFAULT 15,
        contact TEXT,
        url TEXT,
        actif INTEGER DEFAULT 1
    )""")

    # ==================== 21. TARIFS SAISONNIERS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS saisons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        date_debut TEXT NOT NULL,
        date_fin TEXT NOT NULL,
        type TEXT DEFAULT 'Haute',
        coefficient REAL DEFAULT 1.0,
        description TEXT,
        actif INTEGER DEFAULT 1
    )""")

    # ==================== 22. PRESTATIONS / ÉVÉNEMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS evenements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        client_id INTEGER,
        type_evenement TEXT NOT NULL,
        nom TEXT NOT NULL,
        date_debut TEXT NOT NULL,
        date_fin TEXT,
        nb_personnes INTEGER DEFAULT 0,
        salle TEXT,
        menu_prevu TEXT,
        devis REAL DEFAULT 0,
        statut TEXT DEFAULT 'Devis',
        notes TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    # ==================== 23. AVIS CLIENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS avis_clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        sejour_id INTEGER,
        note_globale INTEGER,
        note_proprete INTEGER,
        note_service INTEGER,
        note_restaurant INTEGER,
        commentaire TEXT,
        points_positifs TEXT,
        points_ameliorer TEXT,
        recommande INTEGER DEFAULT 1,
        reponse_direction TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (sejour_id) REFERENCES sejours(id)
    )""")

    # ==================== 24. AUDIT LOG ====================
    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        ip TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 25. PARAMÈTRES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS parametres (
        cle TEXT PRIMARY KEY,
        valeur TEXT,
        description TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()

    # ==================== SEED ====================
    c.execute("SELECT COUNT(*) FROM etages")
    if c.fetchone()[0] == 0:
        print("[INIT] Insertion des données de démonstration...")

        # ÉTAGES
        c.executemany("INSERT OR IGNORE INTO etages (numero, nom, description) VALUES (?, ?, ?)", [
            (0, 'Rez-de-chaussée', 'Lobby, restaurant, salles de réunion'),
            (1, '1er Étage', 'Chambres Standard et Deluxe'),
            (2, '2ème Étage', 'Chambres Deluxe et Suites'),
            (3, '3ème Étage', 'Suites Junior et Présidentielle'),
        ])

        # TYPES DE CHAMBRES
        c.executemany("""INSERT OR IGNORE INTO types_chambres
            (code, nom, description, capacite_adultes, capacite_enfants, superficie_m2,
             lit_principal, nb_lits, equipements, ordre)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('STD', 'Standard', 'Chambre confortable avec lit double', 2, 1, 22, 'Lit double', 1,
             'Climatisation, TV LED 32", WiFi, Coffre-fort, Salle de bain privée, Mini-bar', 1),
            ('SUP', 'Supérieure', 'Chambre spacieuse avec vue sur jardin', 2, 2, 28, 'Lit Queen size', 1,
             'Climatisation, TV LED 43", WiFi, Coffre-fort, Salle de bain, Mini-bar, Balcon', 2),
            ('DLX', 'Deluxe', 'Chambre premium avec vue sur mer', 2, 2, 35, 'Lit King size', 1,
             'Climatisation, TV LED 55", WiFi, Coffre-fort, Salle de bain marbre, Mini-bar, Balcon, Peignoirs', 3),
            ('JSUITE', 'Junior Suite', 'Suite avec salon séparé', 3, 2, 50, 'Lit King size', 2,
             'Salon séparé, Cuisine équipée, Climatisation, TV LED 65", WiFi, Jacuzzi, Terrasse', 4),
            ('SUITE', 'Suite Senior', 'Suite luxueuse avec vue panoramique', 4, 2, 70, 'Lit King + Canapé-lit', 2,
             'Salon, Bureau, Cuisine, TV 65", WiFi, Jacuzzi, Terrasse privée, Service en chambre 24/7', 5),
            ('PRES', 'Suite Présidentielle', 'Notre suite la plus prestigieuse', 4, 3, 120, 'Lit King + 2 lits', 3,
             'Salon, Salle à manger, Bureau, Cuisine, TV 75", WiFi, Jacuzzi, Piscine privée, Majordome', 6),
        ])

        # CHAMBRES (50 chambres)
        chambres = []
        # Étage 1 : 15 chambres
        for i in range(1, 11):
            chambres.append((f'1{i:02d}', 1, 2, 'Jardin' if i % 2 == 0 else 'Ville', 'Disponible', 'Propre', 1))
        for i in range(11, 16):
            chambres.append((f'1{i:02d}', 2, 2, 'Mer' if i % 2 == 0 else 'Jardin', 'Disponible', 'Propre', 1))
        # Étage 2 : 18 chambres
        for i in range(1, 13):
            chambres.append((f'2{i:02d}', 2, 3, 'Mer' if i % 2 == 0 else 'Jardin', 'Disponible', 'Propre', 1))
        for i in range(13, 19):
            chambres.append((f'2{i:02d}', 3, 3, 'Mer', 'Disponible', 'Propre', 1))
        # Étage 3 : 10 chambres (Suites)
        for i in range(1, 7):
            chambres.append((f'3{i:02d}', 4, 4, 'Mer', 'Disponible', 'Propre', 1))
        for i in range(7, 10):
            chambres.append((f'3{i:02d}', 5, 4, 'Panoramique', 'Disponible', 'Propre', 1))
        chambres.append(('301', 6, 4, 'Panoramique', 'Disponible', 'Propre', 1))

        c.executemany("""INSERT OR IGNORE INTO chambres
            (numero, type_id, etage_id, vue, statut, etat_proprete, actif)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", chambres)

        # TARIFS
        c.executemany("""INSERT OR IGNORE INTO tarifs
            (type_chambre_id, nom, type_tarif, prix_nuit, prix_semaine, petit_dejeuner_inclus, taxe_sejour)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", [
            (1, 'Standard - Basse saison', 'Basse saison', 25000, 150000, 0, 1000),
            (1, 'Standard - Haute saison', 'Haute saison', 35000, 210000, 1, 1000),
            (2, 'Supérieure - Basse saison', 'Basse saison', 40000, 240000, 0, 1500),
            (2, 'Supérieure - Haute saison', 'Haute saison', 55000, 330000, 1, 1500),
            (3, 'Deluxe - Basse saison', 'Basse saison', 65000, 390000, 1, 2000),
            (3, 'Deluxe - Haute saison', 'Haute saison', 85000, 510000, 1, 2000),
            (4, 'Junior Suite - Basse saison', 'Basse saison', 95000, 570000, 1, 2500),
            (4, 'Junior Suite - Haute saison', 'Haute saison', 125000, 750000, 1, 2500),
            (5, 'Suite Senior', 'Annuel', 175000, 1050000, 1, 3000),
            (6, 'Suite Présidentielle', 'Annuel', 350000, 2100000, 1, 5000),
        ])

        # SAISONS
        today = datetime.now().date()
        c.executemany("""INSERT OR IGNORE INTO saisons
            (code, nom, date_debut, date_fin, type, coefficient, description, actif)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)""", [
            ('HAUTE-1', 'Haute saison été', '2026-06-01', '2026-09-30', 'Haute', 1.4, 'Vacances d\'été'),
            ('BASSE-1', 'Basse saison automne', '2026-10-01', '2026-11-30', 'Basse', 0.85, 'Période creuse'),
            ('HAUTE-2', 'Haute saison fin d\'année', '2026-12-01', '2027-01-05', 'Haute', 1.5, 'Fêtes de fin d\'année'),
            ('BASSE-2', 'Basse saison hiver', '2027-01-06', '2027-03-31', 'Basse', 0.9, 'Hiver'),
        ])

        # CLIENTS
        clients_data = [
            ('CLI-0001', 'Particulier', 'M.', 'Diop', 'Mamadou', '1975-05-15', 'Sénégalaise', 'M',
             'CNI', 'CNI123456', '+221 77 111 22 33', None, 'm.diop@email.sn', 'Almadies', 'Dakar', 'Sénégal',
             None, None, 'Chambre calme, étage élevé', None, 1, 250, 5, 850000, None),
            ('CLI-0002', 'Particulier', 'Mme', 'Ndiaye', 'Fatou', '1985-08-22', 'Sénégalaise', 'F',
             'CNI', 'CNI234567', '+221 77 222 33 44', None, 'f.ndiaye@email.sn', 'Médina', 'Dakar', 'Sénégal',
             None, None, 'Préférence lit King size', 'Arachides', 1, 180, 3, 420000, None),
            ('CLI-0003', 'Entreprise', None, 'Sénégal Télécom', 'Service Commercial', None, 'Sénégalaise', None,
             'NINEA', 'SN123456789', '+221 33 800 00 00', None, 'resa@telecom.sn', 'Zone Industrielle', 'Dakar', 'Sénégal',
             'Sénégal Télécom', 'SN-TVA-123456', 'Facture entreprise', None, 1, 500, 12, 3500000, 'Client corporate - facturation mensuelle'),
            ('CLI-0004', 'Particulier', 'M.', 'Dupont', 'Jean', '1968-12-10', 'Française', 'M',
             'Passeport', 'FR12345', '+33 6 12 34 56 78', None, 'jean.dupont@email.fr', 'Paris', 'Paris', 'France',
             None, None, 'Vue mer demandée', None, 1, 320, 4, 1250000, None),
            ('CLI-0005', 'Particulier', 'Mme', 'Martin', 'Sophie', '1990-03-25', 'Française', 'F',
             'Passeport', 'FR67890', '+33 6 98 76 54 32', None, 's.martin@email.fr', 'Lyon', 'Lyon', 'France',
             None, None, 'Végétarienne', 'Gluten, lactose', 0, 95, 2, 280000, None),
            ('CLI-0006', 'Entreprise', None, 'BICIS', 'Direction', None, 'Sénégalaise', None,
             'NINEA', 'SN987654321', '+221 33 800 11 11', None, 'resa@bicis.sn', 'Plateau', 'Dakar', 'Sénégal',
             'BICIS', 'SN-TVA-987654', 'Séminaires réguliers', None, 1, 800, 18, 5600000, 'Client VIP - séminaires'),
            ('CLI-0007', 'Particulier', 'M.', 'Sow', 'Ousmane', '1982-07-14', 'Sénégalaise', 'M',
             'CNI', 'CNI345678', '+221 77 333 44 55', None, 'o.sow@email.sn', 'Point E', 'Dakar', 'Sénégal',
             None, None, None, None, 0, 45, 1, 95000, None),
            ('CLI-0008', 'Particulier', 'Mlle', 'Kane', 'Aissatou', '1995-11-08', 'Sénégalaise', 'F',
             'CNI', 'CNI456789', '+221 77 444 55 66', None, 'a.kane@email.sn', 'Sacré-Cœur', 'Dakar', 'Sénégal',
             None, None, 'Lit bébé si possible', None, 0, 30, 1, 55000, None),
            ('CLI-0009', 'Particulier', 'M.', 'Traoré', 'Ibrahima', '1970-02-20', 'Malienne', 'M',
             'Passeport', 'ML12345', '+223 76 12 34 56', None, 'i.traore@email.ml', 'Bamako', 'Bamako', 'Mali',
             None, None, 'Arrivée tardive', None, 1, 210, 6, 780000, None),
            ('CLI-0010', 'Entreprise', None, 'SONATEL', 'DRH', None, 'Sénégalaise', None,
             'NINEA', 'SN555555555', '+221 33 800 22 22', None, 'resa@sonatel.sn', 'Zone Industrielle', 'Dakar', 'Sénégal',
             'SONATEL', 'SN-TVA-555555', 'Formations', None, 1, 950, 25, 7200000, 'Client corporate majeur'),
        ]

        for cl in clients_data:
            c.execute("""INSERT OR IGNORE INTO clients
                (code, type_client, civilite, nom, prenom, date_naissance, nationalite, sexe,
                 piece_type, piece_numero, telephone, telephone_secondaire, email, adresse, ville, pays,
                 societe, numero_tva, preferences, allergies, vip, points_fidelite, nb_sejours, total_depense, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", cl)

        # OTA
        c.executemany("""INSERT OR IGNORE INTO ota (code, nom, commission_pct, contact, url, actif)
            VALUES (?, ?, ?, ?, ?, 1)""", [
            ('BOOKING', 'Booking.com', 15, 'partners@booking.com', 'https://booking.com'),
            ('EXPEDIA', 'Expedia', 18, 'partners@expedia.com', 'https://expedia.com'),
            ('AIRBNB', 'Airbnb', 12, 'hosts@airbnb.com', 'https://airbnb.com'),
            ('AGODA', 'Agoda', 16, 'partners@agoda.com', 'https://agoda.com'),
            ('TRIPADVISOR', 'TripAdvisor', 0, 'partners@tripadvisor.com', 'https://tripadvisor.com'),
        ])

        # RESTAURANTS
        c.executemany("""INSERT OR IGNORE INTO restaurants (code, nom, type, description, horaire_ouverture, horaire_fermeture, capacite, responsable)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('REST-01', 'Le Baobab', 'Restaurant', 'Cuisine sénégalaise et internationale', '07:00', '23:00', 80, 'Chef Abdou Sall'),
            ('REST-02', 'La Terrasse', 'Restaurant', 'Cuisine méditerranéenne et fruits de mer', '12:00', '23:30', 50, 'Chef Marie Diouf'),
            ('BAR-01', 'Sky Bar', 'Bar', 'Cocktails et vue panoramique', '17:00', '02:00', 40, 'Barman Moussa Ndiaye'),
            ('POOL-01', 'Pool Bar', 'Bar', 'Boissons au bord de la piscine', '09:00', '20:00', 30, 'Mamadou Sow'),
        ])

        # CATÉGORIES MENU
        c.executemany("INSERT OR IGNORE INTO categories_menu (nom, ordre, icone) VALUES (?, ?, ?)", [
            ('Entrées', 1, 'fa-leaf'),
            ('Plats principaux', 2, 'fa-utensils'),
            ('Poissons & Fruits de mer', 3, 'fa-fish'),
            ('Grillades', 4, 'fa-drumstick-bite'),
            ('Pizzas & Pâtes', 5, 'fa-pizza-slice'),
            ('Desserts', 6, 'fa-ice-cream'),
            ('Boissons', 7, 'fa-glass-water'),
            ('Vins & Alcools', 8, 'fa-wine-bottle'),
        ])

        # MENU (30 plats)
        plats = [
            ('MENU-001', 'Salade Niçoise', 'Salade fraîche au thon', 1, 1, 'Entrée', 5500, 2000, 10, None, None, 1, 0),
            ('MENU-002', 'Soupe de Poisson', 'Soupe traditionnelle sénégalaise', 1, 1, 'Entrée', 4500, 1500, 15, None, 'Poisson', 1, 1),
            ('MENU-003', 'Nems aux légumes', 'Rouleaux croustillants', 1, 1, 'Entrée', 5000, 1800, 12, None, 'Gluten', 1, 0),
            ('MENU-004', 'Thieboudienne', 'Riz au poisson - Plat national', 2, 1, 'Plat', 8500, 3000, 20, None, 'Poisson', 1, 1),
            ('MENU-005', 'Yassa Poulet', 'Poulet mariné au citron et oignons', 2, 1, 'Plat', 7500, 2500, 18, None, None, 1, 1),
            ('MENU-006', 'Mafé Bœuf', 'Bœuf à la sauce arachide', 2, 1, 'Plat', 8000, 3000, 25, None, 'Arachides', 1, 0),
            ('MENU-007', 'Poulet Braisé', 'Poulet entier braisé aux épices', 4, 1, 'Plat', 9500, 3500, 30, None, None, 1, 0),
            ('MENU-008', 'Riz au Gras', 'Riz sauté aux légumes', 2, 1, 'Plat', 6500, 2000, 15, None, None, 1, 0),
            ('MENU-009', 'Côtelettes d\'Agneau', 'Grillées au romarin', 4, 1, 'Plat', 12000, 5000, 25, None, None, 1, 0),
            ('MENU-010', 'Entrecôte Grillée', 'Entrecôte 300g sauce au poivre', 4, 1, 'Plat', 15000, 6500, 25, None, None, 1, 1),
            ('MENU-011', 'Crevettes Sauteées', 'Crevettes à l\'ail et persil', 3, 2, 'Plat', 13500, 5500, 18, None, 'Crustacés', 1, 0),
            ('MENU-012', 'Filet de Capitaine', 'Filet de poisson grillé', 3, 2, 'Plat', 11000, 4500, 20, None, 'Poisson', 1, 0),
            ('MENU-013', 'Poulet à la Crème', 'Poulet sauce crème et champignons', 2, 2, 'Plat', 9500, 3500, 22, None, 'Lactose', 1, 0),
            ('MENU-014', 'Pizza Margherita', 'Tomate, mozzarella, basilic', 5, 2, 'Plat', 7000, 2500, 15, None, 'Gluten, Lactose', 1, 0),
            ('MENU-015', 'Pizza Reine', 'Jambon, champignons, fromage', 5, 2, 'Plat', 8500, 3200, 15, None, 'Gluten, Lactose', 1, 0),
            ('MENU-016', 'Pâtes Carbonara', 'Lardons, crème, parmesan', 5, 2, 'Plat', 8000, 3000, 15, None, 'Gluten, Lactose, Œufs', 1, 0),
            ('MENU-017', 'Lasagnes Bolognaise', 'Lasagnes maison', 5, 2, 'Plat', 9000, 3500, 25, None, 'Gluten, Lactose', 1, 0),
            ('MENU-018', 'Salade César', 'Poulet, parmesan, croûtons', 1, 2, 'Entrée', 6500, 2500, 12, None, 'Gluten, Lactose, Œufs', 1, 0),
            ('MENU-019', 'Tiramisu', 'Dessert italien classique', 6, 1, 'Dessert', 4000, 1200, 5, None, 'Lactose, Œufs', 1, 0),
            ('MENU-020', 'Crème Brûlée', 'Dessert français', 6, 1, 'Dessert', 4000, 1200, 5, None, 'Lactose, Œufs', 1, 1),
            ('MENU-021', 'Salade de Fruits', 'Fruits de saison frais', 6, 1, 'Dessert', 3500, 1000, 5, None, None, 1, 0),
            ('MENU-022', 'Mousse au Chocolat', 'Mousse maison chocolat noir', 6, 1, 'Dessert', 4000, 1300, 5, None, 'Lactose, Œufs', 1, 0),
            ('MENU-023', 'Eau minérale 50cl', 'Eau plate', 7, 1, 'Boisson', 1000, 300, 1, None, None, 1, 0),
            ('MENU-024', 'Eau pétillante 50cl', 'Eau gazeuse', 7, 1, 'Boisson', 1500, 500, 1, None, None, 1, 0),
            ('MENU-025', 'Jus de Bissap', 'Jus traditionnel hibiscus', 7, 1, 'Boisson', 2000, 500, 2, None, None, 1, 1),
            ('MENU-026', 'Café expresso', 'Café italien', 7, 1, 'Boisson', 1500, 400, 3, None, None, 1, 0),
            ('MENU-027', 'Thé à la menthe', 'Thé vert et menthe fraîche', 7, 1, 'Boisson', 1500, 300, 3, None, None, 1, 0),
            ('MENU-028', 'Cocktail maison', 'Cocktail signature du Sky Bar', 8, 3, 'Boisson', 5500, 1500, 5, None, 'Alcool', 1, 1),
            ('MENU-029', 'Bière locale 33cl', 'Bière pression', 8, 3, 'Boisson', 2000, 700, 1, None, 'Alcool, Gluten', 1, 0),
            ('MENU-030', 'Vin rouge (verre)', 'Vin rouge de Bordeaux', 8, 2, 'Boisson', 4500, 1500, 2, None, 'Sulfites, Alcool', 1, 0),
        ]
        c.executemany("""INSERT OR IGNORE INTO menu
            (code, nom, description, categorie_id, restaurant_id, type_plat, prix, cout_revient,
             temps_preparation_min, ingredients, allergenes, disponible, chef_recommande)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", plats)

        # SERVICES ANNEXES
        c.executemany("""INSERT OR IGNORE INTO services_annexes (code, nom, type, description, prix, unite)
            VALUES (?, ?, ?, ?, ?, ?)""", [
            ('SPA-MASSAGE', 'Massage relaxant', 'Spa', 'Massage 60 min', 25000, 'séance'),
            ('SPA-SOIN', 'Soin visage', 'Spa', 'Soin du visage premium', 20000, 'séance'),
            ('LAUNDRY', 'Blanchisserie', 'Service', 'Pressing vêtements', 5000, 'pièce'),
            ('TRANSFER', 'Transfert aéroport', 'Transport', 'Aéroport AIBD ↔ Hôtel', 25000, 'trajet'),
            ('TAXI', 'Taxi ville', 'Transport', 'Déplacements Dakar', 10000, 'trajet'),
            ('TOUR', 'Excursion Goree', 'Tourisme', 'Visite Île de Gorée', 35000, 'personne'),
            ('TOUR-2', 'Safari Bandia', 'Tourisme', 'Réserve de Bandia', 55000, 'personne'),
            ('GYM', 'Salle de sport', 'Sport', 'Accès journée', 5000, 'jour'),
            ('POOL', 'Accès piscine', 'Sport', 'Accès journée', 3000, 'jour'),
            ('ROOM-SERVICE', 'Room Service 24/7', 'Service', 'Service en chambre', 2000, 'commande'),
        ])

        # RÉSERVATIONS EXEMPLES
        today_iso = datetime.now().date().isoformat()
        tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
        next_week = (datetime.now().date() + timedelta(days=7)).isoformat()
        next_month = (datetime.now().date() + timedelta(days=30)).isoformat()

        c.executemany("""INSERT OR IGNORE INTO reservations
            (numero, client_id, chambre_id, type_chambre_id, date_arrivee, date_depart, nb_nuits,
             nb_adultes, nb_enfants, statut, source, tarif_nuit, sous_total, taxe_sejour, total, acompte, solde,
             demandes_speciales, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('RES-2026-0001', 1, 1, 1, today_iso, tomorrow, 1, 2, 0, 'Confirmée', 'Direct',
             35000, 35000, 1000, 36000, 10000, 26000, 'Arrivée tardive', 1),
            ('RES-2026-0002', 2, 16, 2, tomorrow, next_week, 6, 2, 1, 'Confirmée', 'Booking',
             55000, 330000, 9000, 339000, 100000, 239000, 'Lit bébé', 1),
            ('RES-2026-0003', 4, 35, 4, next_week, next_month, 23, 2, 0, 'Confirmée', 'Expedia',
             125000, 2875000, 57500, 2932500, 500000, 2432500, 'Vue mer impérative', 1),
            ('RES-2026-0004', 3, 40, 5, today_iso, next_week, 7, 4, 0, 'Confirmée', 'Entreprise',
             175000, 1225000, 21000, 1246000, 500000, 746000, 'Facture entreprise', 1),
            ('RES-2026-0005', 6, 41, 6, (datetime.now().date() + timedelta(days=15)).isoformat(),
             (datetime.now().date() + timedelta(days=22)).isoformat(), 7, 4, 2, 'Confirmée', 'Entreprise',
             350000, 2450000, 35000, 2485000, 1000000, 1485000, 'Séminaire BICIS', 1),
        ])

        # PARAMÈTRES
        c.executemany("INSERT OR IGNORE INTO parametres (cle, valeur, description) VALUES (?, ?, ?)", [
            ('hotel_nom', 'OMEGA HÔTEL DAKAR', 'Nom de l\'hôtel'),
            ('hotel_etoiles', '5', 'Nombre d\'étoiles'),
            ('hotel_adresse', 'Corniche Ouest, Dakar', 'Adresse'),
            ('hotel_telephone', '+221 33 800 00 00', 'Téléphone'),
            ('hotel_email', 'contact@omega-hotel.sn', 'Email'),
            ('hotel_nif', 'SN-123456789', 'NIF'),
            ('devise', 'FCFA', 'Devise'),
            ('tva', '18', 'TVA Sénégal (%)'),
            ('taxe_sejour_pct', '2', 'Taxe de séjour (%)'),
            ('checkin_heure', '14:00', 'Heure de check-in'),
            ('checkout_heure', '12:00', 'Heure de check-out'),
            ('heure_arrivee_max', '23:00', 'Arrivée max sans prévenir'),
        ])

        conn.commit()
        print("[INIT] ✅ Données de démonstration insérées")

    conn.close()
    print("[INIT] ✅ Base de données hôtel prête")


if __name__ == "__main__":
    init_db()
