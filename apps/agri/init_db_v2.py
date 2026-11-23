"""
🌾 AgriSénégal V2 — Migration v2 : Vues SQL + données exploitation
Génère parcelles, cultures, récoltes, ventes, météo, NDVI, troupeaux
"""
import sqlite3
import random
import hashlib
from datetime import datetime, timedelta

DB_PATH = "/app/data/agri.db"


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

    c.execute("DROP VIEW IF EXISTS v_producteurs_complets")
    c.execute("""CREATE VIEW v_producteurs_complets AS
                 SELECT p.*,
                        v.nom AS village_nom,
                        d.nom AS departement_nom,
                        r.nom AS region_nom,
                        co.nom AS cooperative_nom
                 FROM producteurs p
                 LEFT JOIN villages v ON p.village_id = v.id
                 LEFT JOIN departements d ON v.departement_id = d.id
                 LEFT JOIN regions r ON d.region_id = r.id
                 LEFT JOIN cooperatives co ON p.cooperative_id = co.id
                 WHERE p.actif = 1""")
    print("[MIGRATE v2] ✅ Vue v_producteurs_complets créée")

    c.execute("DROP VIEW IF EXISTS v_parcelles_cultures")
    c.execute("""CREATE VIEW v_parcelles_cultures AS
                 SELECT pa.*,
                        cu.nom AS culture_nom, cu.code AS culture_code, cu.icone,
                        cp.id AS culture_parcelle_id,
                        cp.date_semis, cp.etat AS culture_etat,
                        cp.superficie_ha AS superficie_cultivee,
                        cp.rendement_obtenu_t_ha,
                        pr.nom AS producteur_nom, pr.prenom AS producteur_prenom
                 FROM parcelles pa
                 LEFT JOIN cultures_parcelles cp ON cp.parcelle_id = pa.id
                 LEFT JOIN cultures cu ON cp.culture_id = cu.id
                 LEFT JOIN producteurs pr ON pa.producteur_id = pr.id
                 WHERE pa.actif = 1""")
    print("[MIGRATE v2] ✅ Vue v_parcelles_cultures créée")

    c.execute("DROP VIEW IF EXISTS v_stats_producteur")
    c.execute("""CREATE VIEW v_stats_producteur AS
                 SELECT p.id AS producteur_id,
                        p.code, p.nom, p.prenom,
                        COUNT(DISTINCT pa.id) AS nb_parcelles,
                        COALESCE(SUM(pa.superficie_ha), 0) AS superficie_totale,
                        (SELECT COALESCE(SUM(quantite_kg), 0) FROM recoltes WHERE producteur_id=p.id) AS recolte_totale_kg,
                        (SELECT COALESCE(SUM(montant_total), 0) FROM ventes WHERE producteur_id=p.id AND statut_paiement='Payé') AS ca_realise,
                        (SELECT COUNT(*) FROM credits WHERE producteur_id=p.id AND statut='Décaissé') AS nb_credits_actifs
                 FROM producteurs p
                 LEFT JOIN parcelles pa ON pa.producteur_id = p.id AND pa.actif = 1
                 WHERE p.actif = 1
                 GROUP BY p.id""")
    print("[MIGRATE v2] ✅ Vue v_stats_producteur créée")

    c.execute("DROP VIEW IF EXISTS v_stock_produits_dispo")
    c.execute("""CREATE VIEW v_stock_produits_dispo AS
                 SELECT sp.*,
                        c.nom AS culture_nom, c.icone,
                        p.nom AS producteur_nom, p.prenom AS producteur_prenom,
                        (sp.quantite_kg - sp.quantite_reservee_kg) AS quantite_disponible
                 FROM stocks_produits sp
                 LEFT JOIN cultures c ON sp.culture_id = c.id
                 LEFT JOIN producteurs p ON sp.producteur_id = p.id
                 WHERE sp.quantite_kg > 0""")
    print("[MIGRATE v2] ✅ Vue v_stock_produits_dispo créée")

    c.execute("DROP VIEW IF EXISTS v_troupeaux_complets")
    c.execute("""CREATE VIEW v_troupeaux_complets AS
                 SELECT t.*,
                        e.nom AS espece_nom, e.icone,
                        p.nom AS producteur_nom, p.prenom AS producteur_prenom,
                        (SELECT COALESCE(SUM(quantite_litres), 0) FROM production_lait
                         WHERE troupeau_id=t.id AND date_production >= date('now', '-30 days')) AS lait_30j
                 FROM troupeaux t
                 LEFT JOIN especes_animales e ON t.espece_id = e.id
                 LEFT JOIN producteurs p ON t.producteur_id = p.id
                 WHERE t.actif = 1""")
    print("[MIGRATE v2] ✅ Vue v_troupeaux_complets créée")

    c.execute("DROP VIEW IF EXISTS v_credits_complets")
    c.execute("""CREATE VIEW v_credits_complets AS
                 SELECT cr.*,
                        p.nom AS producteur_nom, p.prenom AS producteur_prenom,
                        i.nom AS institution_nom,
                        (SELECT COUNT(*) FROM echeances_credit WHERE credit_id=cr.id) AS nb_echeances,
                        (SELECT COUNT(*) FROM echeances_credit WHERE credit_id=cr.id AND statut='Payé') AS nb_payees
                 FROM credits cr
                 LEFT JOIN producteurs p ON cr.producteur_id = p.id
                 LEFT JOIN institutions_financement i ON cr.institution_id = i.id""")
    print("[MIGRATE v2] ✅ Vue v_credits_complets créée")

    c.execute("DROP VIEW IF EXISTS v_alertes_producteur")
    c.execute("""CREATE VIEW v_alertes_producteur AS
                 SELECT a.*, p.nom AS producteur_nom, p.prenom AS producteur_prenom,
                        p.telephone
                 FROM alertes_agro a
                 LEFT JOIN producteurs p ON a.producteur_id = p.id
                 WHERE a.statut = 'Active'
                 ORDER BY a.created_at DESC""")
    print("[MIGRATE v2] ✅ Vue v_alertes_producteur créée")

    conn.commit()

    # ==================== DONNÉES EXPLOITATION ====================
    c.execute("SELECT COUNT(*) FROM parcelles")
    if c.fetchone()[0] == 0:
        print("[MIGRATE v2] Génération parcelles, cultures, récoltes...")
        _seed_exploitation(c, conn)

    conn.close()
    print("[MIGRATE v2] ✅ Migration terminée")


def _seed_exploitation(c, conn):
    """Génère données exploitation réalistes"""
    random.seed(42)
    now = datetime.now()
    year = now.year

    # ============ CAMPAGNES ============
    campagnes = [
        (f'CAMP-{year-1}-HIV', f'Hivernage {year-1}', f'{year-1}-06-01', f'{year-1}-11-30', 'Hivernage'),
        (f'CAMP-{year}-HIV', f'Hivernage {year}', f'{year}-06-01', f'{year}-11-30', 'Hivernage'),
        (f'CAMP-{year}-CS', f'Contre-saison {year}', f'{year}-11-01', f'{year+1}-03-31', 'Contre-saison'),
    ]
    for code, nom, dd, df, saison in campagnes:
        statut_camp = 'Terminée' if 'CS' in code or str(year-1) in code else 'En cours'
        c.execute("""INSERT INTO campagnes (code, nom, date_debut, date_fin, saison, region_id, statut)
                     VALUES (?,?,?,?,?,?,?)""", (code, nom, dd, df, saison, 1, statut_camp))

    # ============ PARCELLES ============
    # Villages avec coordonnées connues pour placer parcelles proches
    villages_gps = {
        1: (14.7833, -17.3167),  # Keur Massar
        2: (14.7500, -16.9333),  # Notto
        3: (14.4500, -17.0000),  # Saly
        4: (14.8833, -16.5500),  # Baba Garage
        5: (14.1000, -15.5500),  # Kaffrine
        6: (16.2667, -16.2333),  # Ross Béthio
        7: (15.6000, -13.3167),  # Ourossogui
        8: (13.7833, -13.6667),  # Tambacounda
        9: (12.5667, -16.2667),  # Ziguinchor
    }

    parcelles_ids = []
    for prod_id in range(1, 9):
        c.execute("SELECT village_id FROM producteurs WHERE id=?", (prod_id,))
        row = c.fetchone()
        village_id = row['village_id'] if row else 1
        base_lat, base_lon = villages_gps.get(village_id, (14.7, -17.0))

        nb_parcelles = random.randint(1, 3)
        for p_idx in range(nb_parcelles):
            # Décalage aléatoire ~500m autour du village
            lat = base_lat + random.uniform(-0.005, 0.005)
            lon = base_lon + random.uniform(-0.005, 0.005)
            sup = round(random.uniform(0.5, 5.0), 2)
            code = f"PAR-{prod_id:03d}-{p_idx+1:02d}"

            c.execute("""INSERT INTO parcelles
                (code, producteur_id, nom, superficie_ha, latitude, longitude, altitude,
                 type_sol, ph_sol, matiere_organique, pente_pct, irrigation_disponible,
                 source_eau, statut_juridique, actif)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                (code, prod_id, f"Parcelle {p_idx+1}",
                 sup, round(lat, 6), round(lon, 6),
                 random.randint(5, 50),
                 random.choice(['Sablo-limoneux', 'Argileux', 'Limono-argileux', 'Sableux']),
                 round(random.uniform(5.5, 7.5), 2),
                 round(random.uniform(0.5, 3.0), 2),
                 round(random.uniform(0, 5), 2),
                 1 if random.random() < 0.4 else 0,
                 random.choice(['Puits', 'Forage', 'Fleuve', 'Aucune']),
                 random.choice(['Propriété', 'Location', 'Mise à disposition'])))
            parcelles_ids.append(c.lastrowid)

    print(f"[MIGRATE v2] ✅ {len(parcelles_ids)} parcelles créées")

    # ============ CULTURES PAR PARCELLE ============
    cultures_parcelles_ids = []
    for parcelle_id in parcelles_ids:
        # 1-2 cultures par parcelle
        nb_cultures = random.randint(1, 2)
        for _ in range(nb_cultures):
            culture_id = random.randint(1, 16)
            campagne_id = random.choice([1, 2, 3])
            date_semis = now - timedelta(days=random.randint(30, 180))

            c.execute("SELECT cycle_jours_min, cycle_jours_max FROM cultures WHERE id=?", (culture_id,))
            cyc = c.fetchone()
            cycle = random.randint(cyc['cycle_jours_min'] or 90, cyc['cycle_jours_max'] or 120)

            date_recolte_prevue = date_semis + timedelta(days=cycle)
            est_recolte = date_recolte_prevue < now

            etat = 'Récolté' if est_recolte else random.choice(['Semé', 'En croissance', 'Maturité'])

            rendement = round(random.uniform(0.8, 3.0), 2) if est_recolte else None

            c.execute("""INSERT INTO cultures_parcelles
                (parcelle_id, culture_id, campagne_id, date_semis, date_prevue_recolte,
                 date_reelle_recolte, superficie_ha, quantite_semence_kg, type_semence,
                 etat, rendement_obtenu_t_ha)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (parcelle_id, culture_id, campagne_id,
                 date_semis.date().isoformat(),
                 date_recolte_prevue.date().isoformat(),
                 date_recolte_prevue.date().isoformat() if est_recolte else None,
                 round(random.uniform(0.5, 3.0), 2),
                 round(random.uniform(10, 50), 2),
                 random.choice(['Certifiée', 'Améliorée', 'Locale']),
                 etat, rendement))
            cultures_parcelles_ids.append((c.lastrowid, parcelle_id, culture_id))

    print(f"[MIGRATE v2] ✅ {len(cultures_parcelles_ids)} cultures créées")

    # ============ RÉCOLTES ============
    nb_recoltes = 0
    for cp_id, parcelle_id, culture_id in cultures_parcelles_ids:
        c.execute("SELECT etat, date_reelle_recolte, superficie_ha FROM cultures_parcelles WHERE id=?", (cp_id,))
        row = c.fetchone()
        if row and row['etat'] == 'Récolté' and row['date_reelle_recolte']:
            c.execute("SELECT producteur_id FROM parcelles WHERE id=?", (parcelle_id,))
            prod = c.fetchone()
            sup = row['superficie_ha'] or 1.0
            quantite = round(sup * random.uniform(800, 2500), 0)  # kg

            ref = f"REC-{year}-{nb_recoltes+1:05d}"
            c.execute("""INSERT INTO recoltes
                (code, culture_parcelle_id, producteur_id, parcelle_id, culture_id,
                 date_recolte, quantite_kg, qualite, humidite_pct, destination)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (ref, cp_id, prod['producteur_id'] if prod else 1,
                 parcelle_id, culture_id,
                 row['date_reelle_recolte'],
                 quantite,
                 random.choice(['Excellente', 'Bonne', 'Moyenne']),
                 round(random.uniform(8, 15), 1),
                 random.choice(['Stock', 'Vente directe', 'Coopérative'])))
            nb_recoltes += 1

    print(f"[MIGRATE v2] ✅ {nb_recoltes} récoltes créées")

    # ============ STOCK PRODUITS ============
    c.execute("""INSERT INTO stocks_produits
                 (producteur_id, culture_id, qualite, quantite_kg, prix_revient_kg, emplacement)
                 SELECT
                    r.producteur_id,
                    r.culture_id,
                    'Bonne',
                    COALESCE(SUM(r.quantite_kg), 0) * 0.6,
                    150,
                    'Magasin'
                 FROM recoltes r
                 GROUP BY r.producteur_id, r.culture_id""")
    print(f"[MIGRATE v2] ✅ Stocks produits créés")

    # ============ VENTES ============
    nb_ventes = 0
    for _ in range(40):
        prod_id = random.randint(1, 8)
        culture_id = random.randint(1, 16)
        acheteur_id = random.randint(1, 3)
        qte = round(random.uniform(100, 2000), 0)

        c.execute("SELECT prix_moyen_kg, nom FROM cultures WHERE id=?", (culture_id,))
        cul = c.fetchone()
        prix = cul['prix_moyen_kg'] or 200

        montant = int(qte * prix)
        date_v = now - timedelta(days=random.randint(1, 180))

        statut_p = random.choice(['Payé', 'Payé', 'Payé', 'En attente'])

        ref = f"VTE-{date_v.strftime('%Y%m%d')}-{nb_ventes+1:04d}"

        c.execute("""INSERT INTO ventes
            (reference, producteur_id, acheteur_id, date_vente, culture_id,
             quantite_kg, prix_unitaire_kg, montant_total, mode_paiement,
             statut_paiement, date_paiement)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (ref, prod_id, acheteur_id, date_v.date().isoformat(), culture_id,
             qte, prix, montant,
             random.choice(['Wave', 'Orange Money', 'Espèces', 'Virement']),
             statut_p,
             date_v.date().isoformat() if statut_p == 'Payé' else None))
        nb_ventes += 1

    print(f"[MIGRATE v2] ✅ {nb_ventes} ventes créées")

    # ============ TRANSACTIONS MOBILE MONEY ============
    nb_trans = 0
    for _ in range(80):
        prod_id = random.randint(1, 8)
        c.execute("SELECT telephone, mobile_money_type FROM producteurs WHERE id=?", (prod_id,))
        prod = c.fetchone()
        fournisseur = prod['mobile_money_type'] or 'Wave'

        montant = random.randint(1000, 200000)
        type_t = random.choice(['Encaissement', 'Paiement', 'Transfert', 'Paiement crédit'])
        statut = random.choice(['Réussi', 'Réussi', 'Réussi', 'En attente', 'Échoué'])

        ref = f"MM-{now.strftime('%Y%m%d')}-{nb_trans+1:05d}"

        c.execute("""INSERT INTO transactions_mobile
            (reference, producteur_id, fournisseur, telephone, type_transaction,
             montant, statut, objet, date_transaction)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (ref, prod_id, fournisseur, prod['telephone'],
             type_t, montant, statut,
             random.choice(['Achat intrants', 'Vente récolte', 'Prime assurance',
                            'Remboursement crédit', 'Cotisation coopérative']),
             (now - timedelta(days=random.randint(1, 90))).isoformat()))
        nb_trans += 1

    print(f"[MIGRATE v2] ✅ {nb_trans} transactions mobile money créées")

    # ============ TROUPEAUX ============
    nb_troupeaux = 0
    for prod_id in range(1, 6):  # 5 producteurs avec élevage
        espece_id = random.randint(1, 6)
        effectif = random.randint(5, 100)

        code = f"TRP-{prod_id:03d}-{nb_troupeaux+1:02d}"
        c.execute("""INSERT INTO troupeaux
            (code, producteur_id, espece_id, nom, race, effectif_total, mode_elevage, objectif)
            VALUES (?,?,?,?,?,?,?,?)""",
            (code, prod_id, espece_id,
             f"Troupeau {prod_id}", 'Locale',
             effectif,
             random.choice(['Extensif', 'Semi-intensif']),
             random.choice(['Lait', 'Viande', 'Mixte'])))
        troupeau_id = c.lastrowid
        nb_troupeaux += 1

        # Animaux individuels (max 20 par troupeau)
        for a_idx in range(min(effectif, 20)):
            num_boucle = f"SEN-{troupeau_id:03d}-{a_idx+1:04d}"
            sexe = random.choice(['M', 'F'])
            naissance = now - timedelta(days=random.randint(90, 2000))
            poids = random.uniform(15, 400) if espece_id == 1 else random.uniform(10, 80)

            c.execute("""INSERT INTO animaux
                (numero_boucle, troupeau_id, sexe, date_naissance, poids_kg,
                 race, etat_sante, stade_physiologique, actif)
                VALUES (?,?,?,?,?,?,?,?,1)""",
                (num_boucle, troupeau_id, sexe, naissance.date().isoformat(),
                 round(poids, 1), 'Locale',
                 random.choice(['Bon', 'Bon', 'Bon', 'À surveiller']),
                 random.choice(['Croissance', 'Gestante', 'Lactation', 'Repos'])))

    print(f"[MIGRATE v2] ✅ {nb_troupeaux} troupeaux + animaux créés")

    # ============ DONNÉES MÉTÉO ============
    nb_meteo = 0
    for jour in range(180, 0, -1):
        d = now - timedelta(days=jour)
        for village_id in [1, 3, 5, 7, 9]:
            temp_min = round(random.uniform(15, 25), 1)
            temp_max = round(random.uniform(28, 42), 1)
            pluvio = round(random.uniform(0, 30), 1) if 6 <= d.month <= 10 else 0

            c.execute("""INSERT INTO donnees_meteo
                (village_id, date_mesure, temperature_min, temperature_max, temperature_moy,
                 humidite_pct, pluviometrie_mm, vent_vitesse_kmh, vent_direction, source)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (village_id, d.date().isoformat(), temp_min, temp_max,
                 round((temp_min + temp_max) / 2, 1),
                 random.randint(30, 90), pluvio,
                 round(random.uniform(5, 25), 1),
                 random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']),
                 'Manuel'))
            nb_meteo += 1

    print(f"[MIGRATE v2] ✅ {nb_meteo} relevés météo créés")

    # ============ IMAGES SATELLITE NDVI ============
    nb_ndvi = 0
    for parcelle_id in parcelles_ids[:20]:
        for semaine in range(8, 0, -1):
            d = now - timedelta(days=semaine * 7)
            ndvi = round(random.uniform(0.2, 0.85), 3)
            stress_h = 1 if ndvi < 0.35 else 0

            c.execute("""INSERT INTO images_satellite
                (parcelle_id, date_image, satellite, ndvi_moyen, ndvi_min, ndvi_max,
                 ndwi, stress_hydrique, stress_azote, source)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (parcelle_id, d.date().isoformat(), 'Sentinel-2',
                 ndvi,
                 round(ndvi - random.uniform(0.05, 0.15), 3),
                 round(ndvi + random.uniform(0.05, 0.15), 3),
                 round(random.uniform(-0.3, 0.4), 3),
                 stress_h,
                 1 if random.random() < 0.15 else 0,
                 'Sentinel-2'))
            nb_ndvi += 1

    print(f"[MIGRATE v2] ✅ {nb_ndvi} images NDVI créées")

    # ============ CRÉDITS & ÉCHÉANCES ============
    nb_credits = 0
    for _ in range(8):
        prod_id = random.randint(1, 8)
        inst_id = random.randint(1, 4)
        montant = random.choice([100000, 250000, 500000, 1000000, 2000000])
        taux = random.uniform(7.0, 18.0)
        duree = random.choice([6, 12, 18, 24])

        date_demande = now - timedelta(days=random.randint(60, 400))
        statut = random.choice(['Décaissé', 'Décaissé', 'Décaissé', 'En analyse', 'Remboursé'])

        ref = f"CRD-{date_demande.strftime('%Y%m%d')}-{nb_credits+1:04d}"

        c.execute("""INSERT INTO credits
            (reference, producteur_id, institution_id, type_credit,
             montant_demande, montant_accorde, taux_interet, duree_mois,
             date_demande, date_accord, date_decaissement, statut,
             objet, score_credit)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ref, prod_id, inst_id,
             random.choice(['Campagne agricole', 'Équipement', 'Intrants']),
             montant, montant if statut in ('Décaissé', 'Remboursé') else None,
             taux, duree,
             date_demande.date().isoformat(),
             (date_demande + timedelta(days=15)).date().isoformat() if statut != 'En analyse' else None,
             (date_demande + timedelta(days=30)).date().isoformat() if statut in ('Décaissé', 'Remboursé') else None,
             statut,
             random.choice(['Achat semences', 'Achat engrais', 'Irrigation', 'Matériel agricole']),
             random.randint(450, 800)))
        credit_id = c.lastrowid
        nb_credits += 1

        # Échéances
        if statut in ('Décaissé', 'Remboursé'):
            date_deb = date_demande + timedelta(days=30)
            montant_mensuel = montant // duree
            for i in range(duree):
                d_ech = date_deb + timedelta(days=30 * i)
                paye = d_ech < now and (statut == 'Remboursé' or random.random() < 0.85)
                c.execute("""INSERT INTO echeances_credit
                    (credit_id, numero_echeance, date_echeance,
                     montant_capital, montant_interet, montant_total,
                     montant_paye, date_paiement, statut)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (credit_id, i + 1, d_ech.date().isoformat(),
                     montant_mensuel, int(montant_mensuel * taux / 100 / 12),
                     int(montant_mensuel * (1 + taux / 100 / 12)),
                     int(montant_mensuel * (1 + taux / 100 / 12)) if paye else 0,
                     d_ech.date().isoformat() if paye else None,
                     'Payé' if paye else ('En retard' if d_ech < now else 'À venir')))

    print(f"[MIGRATE v2] ✅ {nb_credits} crédits + échéances créés")

    # ============ MISE À JOUR NB MEMBRES COOPÉRATIVES ============
    c.execute("""UPDATE cooperatives SET nb_membres =
                 (SELECT COUNT(*) FROM producteurs WHERE cooperative_id = cooperatives.id AND actif=1)""")

    conn.commit()
    print("[MIGRATE v2] ✅ Toutes les données générées")


if __name__ == '__main__':
    migrate()
