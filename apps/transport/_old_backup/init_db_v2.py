"""
Omega Transport V2 — Migration v2 : Vues SQL + données démo
Génère : voyages du mois, billets, carburant, maintenance
"""
import sqlite3
import hashlib
# import qrcode  # désactivé
import io
import os
import random
from datetime import datetime, timedelta

DB_PATH = "/app/data/transport.db"
QR_DIR = "/app/data/qrcodes"


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _hash(txt):
    return hashlib.sha256(txt.encode()).hexdigest()


def migrate():
    print("[MIGRATE v2] Démarrage...")
    pass  # QR dir désactivé
    conn = get_conn()
    c = conn.cursor()

    # ==================== VUES SQL ====================

    c.execute("DROP VIEW IF EXISTS v_vehicules_complets")
    c.execute("""CREATE VIEW v_vehicules_complets AS
                 SELECT v.*,
                        m.nom AS marque_nom,
                        t.nom AS type_nom, t.categorie,
                        s.nom AS site_nom,
                        (SELECT nom || ' ' || prenom FROM chauffeurs WHERE id=v.chauffeur_principal_id) AS chauffeur_nom,
                        (SELECT date_expiration FROM documents_vehicules
                         WHERE vehicule_id=v.id AND type_document='Assurance'
                         ORDER BY date_expiration DESC LIMIT 1) AS assurance_exp,
                        (SELECT date_expiration FROM documents_vehicules
                         WHERE vehicule_id=v.id AND type_document='Visite technique'
                         ORDER BY date_expiration DESC LIMIT 1) AS visite_tech_exp
                 FROM vehicules v
                 LEFT JOIN marques m ON v.marque_id = m.id
                 LEFT JOIN types_vehicules t ON v.type_id = t.id
                 LEFT JOIN sites s ON v.site_id = s.id""")
    print("[MIGRATE v2] ✅ Vue v_vehicules_complets créée")

    c.execute("DROP VIEW IF EXISTS v_voyages_complets")
    c.execute("""CREATE VIEW v_voyages_complets AS
                 SELECT vo.*,
                        l.code AS ligne_code, l.nom AS ligne_nom,
                        l.ville_depart, l.ville_arrivee, l.distance_km,
                        v.immatriculation, v.modele,
                        ch.nom AS chauffeur_nom, ch.prenom AS chauffeur_prenom,
                        ch.telephone AS chauffeur_telephone,
                        s.nom AS site_nom
                 FROM voyages vo
                 LEFT JOIN lignes l ON vo.ligne_id = l.id
                 LEFT JOIN vehicules v ON vo.vehicule_id = v.id
                 LEFT JOIN chauffeurs ch ON vo.chauffeur_id = ch.id
                 LEFT JOIN sites s ON vo.site_id = s.id""")
    print("[MIGRATE v2] ✅ Vue v_voyages_complets créée")

    c.execute("DROP VIEW IF EXISTS v_billets_complets")
    c.execute("""CREATE VIEW v_billets_complets AS
                 SELECT b.*,
                        vo.numero AS voyage_numero, vo.date_voyage, vo.heure_depart_prevue,
                        l.code AS ligne_code, l.nom AS ligne_nom,
                        l.ville_depart, l.ville_arrivee,
                        v.immatriculation,
                        ch.nom AS chauffeur_nom
                 FROM billets b
                 LEFT JOIN voyages vo ON b.voyage_id = vo.id
                 LEFT JOIN lignes l ON vo.ligne_id = l.id
                 LEFT JOIN vehicules v ON vo.vehicule_id = v.id
                 LEFT JOIN chauffeurs ch ON vo.chauffeur_id = ch.id""")
    print("[MIGRATE v2] ✅ Vue v_billets_complets créée")

    c.execute("DROP VIEW IF EXISTS v_stats_vehicule_mois")
    c.execute("""CREATE VIEW v_stats_vehicule_mois AS
                 SELECT v.id AS vehicule_id, v.immatriculation,
                        strftime('%Y-%m', vo.date_voyage) AS mois,
                        COUNT(DISTINCT vo.id) AS nb_voyages,
                        COALESCE(SUM(vo.recette_reelle), 0) AS ca,
                        COALESCE(SUM(vo.places_vendues), 0) AS passagers,
                        (SELECT COALESCE(SUM(montant_total), 0) FROM carburant
                         WHERE vehicule_id=v.id AND strftime('%Y-%m', date_bon)=strftime('%Y-%m', vo.date_voyage)) AS cout_carburant,
                        (SELECT COALESCE(SUM(cout_total), 0) FROM maintenance
                         WHERE vehicule_id=v.id AND strftime('%Y-%m', date_debut)=strftime('%Y-%m', vo.date_voyage)) AS cout_maintenance
                 FROM vehicules v
                 LEFT JOIN voyages vo ON vo.vehicule_id = v.id
                 GROUP BY v.id, mois""")
    print("[MIGRATE v2] ✅ Vue v_stats_vehicule_mois créée")

    c.execute("DROP VIEW IF EXISTS v_alertes_documents")
    c.execute("""CREATE VIEW v_alertes_documents AS
                 SELECT dv.id, dv.vehicule_id, dv.type_document, dv.date_expiration,
                        v.immatriculation,
                        CAST(julianday(dv.date_expiration) - julianday('now') AS INTEGER) AS jours_restants
                 FROM documents_vehicules dv
                 INNER JOIN vehicules v ON dv.vehicule_id = v.id
                 WHERE dv.date_expiration IS NOT NULL
                   AND date(dv.date_expiration) <= date('now', '+60 days')""")
    print("[MIGRATE v2] ✅ Vue v_alertes_documents créée")

    conn.commit()

    # ==================== DONNEES DEMO ====================
    c.execute("SELECT COUNT(*) FROM voyages")
    if c.fetchone()[0] == 0:
        print("[MIGRATE v2] Insertion voyages/billets/carburant démo...")
        _seed_exploitation(c, conn)

    conn.close()
    print("[MIGRATE v2] ✅ Migration terminée")


def _seed_exploitation(c, conn):
    """Génère 60 jours de voyages avec billets, carburant, maintenances"""
    random.seed(42)

    # ---- Documents véhicules ----
    now = datetime.now()
    for v_id in range(1, 11):
        # Assurance
        exp_assurance = (now + timedelta(days=random.randint(-30, 300))).date().isoformat()
        c.execute("""INSERT INTO documents_vehicules
            (vehicule_id, type_document, numero, date_emission, date_expiration)
            VALUES (?, 'Assurance', ?, ?, ?)""",
            (v_id, f"ASS-{v_id:04d}", (now - timedelta(days=365)).date().isoformat(),
             exp_assurance))

        # Visite technique
        exp_visite = (now + timedelta(days=random.randint(-15, 180))).date().isoformat()
        c.execute("""INSERT INTO documents_vehicules
            (vehicule_id, type_document, numero, date_emission, date_expiration)
            VALUES (?, 'Visite technique', ?, ?, ?)""",
            (v_id, f"VT-{v_id:04d}", (now - timedelta(days=180)).date().isoformat(),
             exp_visite))

        # Carte grise
        c.execute("""INSERT INTO documents_vehicules
            (vehicule_id, type_document, numero, date_emission)
            VALUES (?, 'Carte grise', ?, ?)""",
            (v_id, f"CG-{v_id:04d}", (now - timedelta(days=500)).date().isoformat()))

    # ---- Voyages sur 60 jours ----
    voyage_count = 0
    billet_count = 0
    carburant_count = 0
    maintenance_count = 0

    for jour_offset in range(60, 0, -1):
        d = now - timedelta(days=jour_offset)
        date_str = d.date().isoformat()

        # 3-8 voyages par jour
        nb_voyages = random.randint(2, 4)
        for _ in range(nb_voyages):
            ligne_id = random.randint(1, 7)
            vehicule_id = random.randint(1, 10)
            chauffeur_id = random.randint(1, 15)

            c.execute("SELECT tarif_base, distance_km, duree_minutes FROM lignes WHERE id=?",
                      (ligne_id,))
            ligne = c.fetchone()
            tarif = ligne['tarif_base']

            c.execute("SELECT capacite_places FROM vehicules WHERE id=?", (vehicule_id,))
            capa = c.fetchone()['capacite_places']

            heure_depart = f"{random.randint(5, 20):02d}:{random.choice(['00','15','30','45'])}"
            h_dep = int(heure_depart.split(':')[0])
            duree_h = ligne['duree_minutes'] // 60
            heure_arrivee = f"{(h_dep + duree_h) % 24:02d}:{heure_depart.split(':')[1]}"

            # Taux de remplissage
            taux = random.uniform(0.55, 0.98)
            places_vendues = int(capa * taux)
            places_dispo = capa - places_vendues
            recette_attendue = places_vendues * tarif

            # Écart recette (0-8%)
            ecart_pct = random.uniform(-3, 8)
            recette_reelle = int(recette_attendue * (1 + ecart_pct / 100))

            # Statut selon date
            if jour_offset > 1:
                statut = 'Terminé'
            elif jour_offset == 1:
                statut = 'Terminé' if h_dep < 12 else 'En cours'
            else:
                statut = 'En cours' if h_dep <= now.hour else 'Programmé'

            c.execute("""INSERT INTO voyages
                (numero, ligne_id, vehicule_id, chauffeur_id, date_voyage,
                 heure_depart_prevue, heure_arrivee_prevue,
                 heure_depart_reelle, heure_arrivee_reelle,
                 places_totales, places_vendues, places_disponibles,
                 recette_attendue, recette_reelle,
                 kilometrage_depart, kilometrage_arrivee,
                 statut, site_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (f"VOY-{d.strftime('%Y%m%d')}-{voyage_count + 1:04d}",
                 ligne_id, vehicule_id, chauffeur_id, date_str,
                 heure_depart, heure_arrivee,
                 heure_depart if statut == 'Terminé' else None,
                 heure_arrivee if statut == 'Terminé' else None,
                 capa, places_vendues, places_dispo,
                 recette_attendue, recette_reelle if statut == 'Terminé' else 0,
                 150000 + voyage_count * 50, 150000 + voyage_count * 50 + int(ligne['distance_km']),
                 statut))

            voyage_id = c.lastrowid
            voyage_count += 1

            # ---- Billets pour les voyages terminés ----
            if statut == 'Terminé' and places_vendues > 0:
                nb_billets = min(places_vendues, random.randint(1, 3))
                noms_sen = [
                    ('Diop', 'Mamadou'), ('Ndiaye', 'Fatou'), ('Fall', 'Omar'),
                    ('Sow', 'Aminata'), ('Ba', 'Ibrahima'), ('Diallo', 'Awa'),
                    ('Sarr', 'Cheikh'), ('Kane', 'Mariama'), ('Gueye', 'Abdoulaye'),
                    ('Sylla', 'Kadidiatou'), ('Cisse', 'Moussa'), ('Barry', 'Alpha')
                ]
                for _ in range(nb_billets):
                    nom_p, prenom_p = random.choice(noms_sen)
                    num_place = random.randint(1, capa)
                    classe = random.choice(['1ère', '2ème', '2ème', '2ème'])
                    prix = int(tarif * (1.5 if classe == '1ère' else 1))

                    num_billet = f"BIL-{d.strftime('%Y%m%d')}-{billet_count + 1:05d}"
                    qr_data = f"{num_billet}|{voyage_id}|{num_place}|{prix}"
                    qr_hash = _hash(qr_data)

                    c.execute("""INSERT INTO billets
                        (numero, voyage_id, passager_nom, passager_telephone,
                         numero_place, classe, prix, statut, mode_paiement,
                         vendeur_id, qr_code, checksum, date_emission)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'Vendu', ?, 4, ?, ?, ?)""",
                        (num_billet, voyage_id, f"{prenom_p} {nom_p}",
                         f"77{random.randint(1000000, 9999999)}",
                         num_place, classe, prix,
                         random.choice(['Espèces', 'Wave', 'Orange Money']),
                         qr_hash[:32], qr_hash,
                         d.replace(hour=random.randint(5, 14)).isoformat()))

                    # Générer le QR code image (désactivé pour perf)
                    pass

                    billet_count += 1

            # ---- Carburant (1 bon / 3 voyages) ----
            if voyage_count % 3 == 0:
                litres = random.uniform(60, 150)
                prix_l = 990
                km_parcourus = ligne['distance_km'] * 2
                conso_theorique = (km_parcourus * 22.0) / 100
                conso_reelle = litres
                ecart = ((conso_reelle - conso_theorique) / conso_theorique * 100) if conso_theorique > 0 else 0

                c.execute("""INSERT INTO carburant
                    (numero_bon, vehicule_id, chauffeur_id, date_bon,
                     litres, prix_litre, montant_total, kilometrage,
                     station, consommation_calculee, consommation_theorique,
                     ecart_pct, statut)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (f"BON-{d.strftime('%Y%m%d')}-{carburant_count + 1:04d}",
                     vehicule_id, chauffeur_id, date_str,
                     round(litres, 2), prix_l, int(litres * prix_l),
                     150000 + carburant_count * 100,
                     random.choice(['Total Dakar', 'Shell Thiès', 'Petro Sen']),
                     round(conso_reelle, 2), round(conso_theorique, 2),
                     round(ecart, 2),
                     'Anomalie' if abs(ecart) > 15 else 'Normal'))
                carburant_count += 1

    # ---- Maintenances ----
    for v_id in range(1, 11):
        nb_inter = random.randint(1, 3)
        for _ in range(nb_inter):
            d = now - timedelta(days=random.randint(5, 120))
            cout_pieces = random.randint(30000, 250000)
            cout_mo = random.randint(15000, 80000)
            type_m = random.choice(['Préventive', 'Curative', 'Révision'])
            c.execute("""INSERT INTO maintenance
                (vehicule_id, type_maintenance, date_debut, date_fin,
                 kilometrage, description, garage,
                 cout_pieces, cout_main_oeuvre, cout_total,
                 statut, prochaine_echeance_km, prochaine_echeance_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Terminée', ?, ?)""",
                (v_id, type_m, d.date().isoformat(),
                 (d + timedelta(days=random.randint(1, 5))).date().isoformat(),
                 150000 + random.randint(0, 50000),
                 f"{type_m} - vérification et remplacement pièces",
                 random.choice(['Garage Omega', 'Garage Central', 'Garage Dakar Auto']),
                 cout_pieces, cout_mo, cout_pieces + cout_mo,
                 150000 + random.randint(5000, 20000),
                 (now + timedelta(days=random.randint(30, 180))).date().isoformat()))
            maintenance_count += 1

    # ---- Amendes ----
    motifs = [
        ('Excès de vitesse', 25000, 'Radar Dakar'),
        ('Non-port ceinture', 15000, 'Police Thiès'),
        ('Feu rouge grillé', 20000, 'Police Dakar'),
        ('Stationnement interdit', 10000, 'Municipalité'),
    ]
    for _ in range(8):
        motif, montant, autorite = random.choice(motifs)
        d = now - timedelta(days=random.randint(5, 90))
        c.execute("""INSERT INTO amendes
            (vehicule_id, chauffeur_id, date_amende, motif, montant,
             lieu, autorite, statut)
            VALUES (?, ?, ?, ?, ?, 'Dakar', ?, ?)""",
            (random.randint(1, 10), random.randint(1, 15),
             d.date().isoformat(), motif, montant, autorite,
             random.choice(['Payée', 'À payer', 'À payer'])))

    conn.commit()
    print(f"[MIGRATE v2] ✅ {voyage_count} voyages, {billet_count} billets, "
          f"{carburant_count} bons carburant, {maintenance_count} maintenances")


if __name__ == '__main__':
    migrate()
