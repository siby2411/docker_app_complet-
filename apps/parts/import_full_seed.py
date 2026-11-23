#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌱 Import complet pour OMEGA PARTS — Base vide
Peuple TOUTES les tables : catégories, marques, modèles, fournisseurs, PV, pièces, stock, clients
"""
import sqlite3
from datetime import datetime
import random

DB_PATH = '/app/data/parts.db'

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def main():
    conn = get_conn()
    cur = conn.cursor()

    print("═" * 50)
    print("🌱 IMPORT COMPLET OMEGA PARTS")
    print("═" * 50)
    print()

    # ═══════════════════════════════════════════════════════
    # 1. CATÉGORIES (9 racines + 17 sous-catégories)
    # ═══════════════════════════════════════════════════════
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        print("📂 Création des catégories...")

        roots = [
            ('MOTEUR', 'Moteur', '🔧', 1),
            ('FREINAGE', 'Freinage', '🛑', 2),
            ('SUSPENSION', 'Suspension & Direction', '⚙️', 3),
            ('ELECTRICITE', 'Électricité & Électronique', '⚡', 4),
            ('CARROSSERIE', 'Carrosserie', '🚗', 5),
            ('FILTRATION', 'Filtration', '💧', 6),
            ('TRANSMISSION', 'Transmission', '⛓️', 7),
            ('ECLAIRAGE', 'Éclairage', '💡', 8),
            ('PNEUMATIQUE', 'Pneumatique & Roues', '⭕', 9),
        ]

        for code, nom, icone, ordre in roots:
            cur.execute("""
                INSERT INTO categories (code, nom, icone, ordre, actif, created_at)
                VALUES (?,?,?,?,1,?)
            """, (code, nom, icone, ordre, datetime.now().isoformat()))

        # Récupérer les IDs
        cur.execute("SELECT id, code FROM categories WHERE parent_id IS NULL")
        roots_map = {r['code']: r['id'] for r in cur.fetchall()}

        subs = [
            ('MOT_POMP', 'MOTEUR', 'Pompes à eau', '💧'),
            ('MOT_COUR', 'MOTEUR', 'Courroies distribution', '⛓️'),
            ('MOT_BOUGIE', 'MOTEUR', 'Bougies & allumage', '⚡'),
            ('MOT_JOINT', 'MOTEUR', 'Joints moteur', '🔘'),
            ('FRE_PLAQ', 'FREINAGE', 'Plaquettes de frein', '🛑'),
            ('FRE_DISQ', 'FREINAGE', 'Disques de frein', '💿'),
            ('FRE_ETRI', 'FREINAGE', 'Étriers', '🔧'),
            ('FRE_LIQ', 'FREINAGE', 'Liquide de frein', '💧'),
            ('FRE_ABSR', 'FREINAGE', 'Capteurs ABS', '📡'),
            ('SUS_AMOR', 'SUSPENSION', 'Amortisseurs', '⚙️'),
            ('SUS_ROTU', 'SUSPENSION', 'Rotules', '🔘'),
            ('SUS_ROUE', 'SUSPENSION', 'Roulements', '⭕'),
            ('ELEC_BATT', 'ELECTRICITE', 'Batteries', '🔋'),
            ('ELEC_ALTE', 'ELECTRICITE', 'Alternateurs', '⚡'),
            ('ELEC_DEMA', 'ELECTRICITE', 'Démarreurs', '🔑'),
            ('ELEC_CAPT', 'ELECTRICITE', 'Capteurs', '📡'),
            ('FIL_HUIL', 'FILTRATION', 'Filtres à huile', '🛢️'),
            ('FIL_AIR', 'FILTRATION', 'Filtres à air', '💨'),
            ('FIL_CARB', 'FILTRATION', 'Filtres carburant', '⛽'),
            ('FIL_HABI', 'FILTRATION', 'Filtres habitacle', '🚗'),
            ('ECL_PHAR', 'ECLAIRAGE', 'Phares', '💡'),
            ('ECL_AMP', 'ECLAIRAGE', 'Ampoules', '💡'),
            ('ECL_FEUX', 'ECLAIRAGE', 'Feux arrière', '🚨'),
            ('ECL_RETR', 'ECLAIRAGE', 'Rétroviseurs', '🪞'),
        ]

        for code, parent_code, nom, icone in subs:
            parent_id = roots_map.get(parent_code)
            if parent_id:
                cur.execute("""
                    INSERT INTO categories (parent_id, code, nom, icone, ordre, actif, created_at)
                    VALUES (?,?,?,?,0,1,?)
                """, (parent_id, code, nom, icone, datetime.now().isoformat()))

        conn.commit()
        cur.execute("SELECT COUNT(*) FROM categories")
        print(f"  ✅ {cur.fetchone()[0]} catégories créées")
    else:
        print(f"📂 Catégories : déjà présentes")

    # ═══════════════════════════════════════════════════════
    # 2. MARQUES VÉHICULES
    # ═══════════════════════════════════════════════════════
    cur.execute("SELECT COUNT(*) FROM vehicules_marques")
    if cur.fetchone()[0] == 0:
        print("🚗 Création des marques véhicules...")
        marques = ['Toyota', 'Peugeot', 'Renault', 'Hyundai', 'Kia', 'Mercedes-Benz',
                   'BMW', 'Nissan', 'Volkswagen', 'Ford', 'Suzuki', 'Mitsubishi',
                   'Citroën', 'Fiat', 'Mazda', 'Honda', 'Chevrolet', 'Audi']
        for m in marques:
            cur.execute("INSERT INTO vehicules_marques (nom, created_at) VALUES (?,?)",
                        (m, datetime.now().isoformat()))
        conn.commit()
        print(f"  ✅ {len(marques)} marques créées")
    else:
        print("🚗 Marques : déjà présentes")

    # ═══════════════════════════════════════════════════════
    # 3. MODÈLES VÉHICULES
    # ═══════════════════════════════════════════════════════
    cur.execute("SELECT COUNT(*) FROM vehicules_modeles")
    if cur.fetchone()[0] == 0:
        print("🚗 Création des modèles véhicules...")
        cur.execute("SELECT id, nom FROM vehicules_marques")
        marques_map = {r['nom']: r['id'] for r in cur.fetchall()}

        modeles_data = {
            'Toyota': ['Corolla', 'RAV4', 'Hilux', 'Yaris', 'Camry'],
            'Peugeot': ['208', '308', '3008', 'Partner', '508'],
            'Renault': ['Clio', 'Duster', 'Mégane', 'Captur', 'Kangoo'],
            'Hyundai': ['Tucson', 'i10', 'i20', 'Accent', 'Santa Fe'],
            'Kia': ['Sportage', 'Rio', 'Picanto', 'Sorento', 'Ceed'],
            'Mercedes-Benz': ['Classe C', 'Classe A', 'GLC', 'Classe E', 'Classe S'],
            'BMW': ['Série 3', 'Série 5', 'X3', 'X5', 'Série 1'],
            'Nissan': ['Qashqai', 'Note', 'Juke', 'X-Trail', 'Micra'],
            'Volkswagen': ['Golf', 'Tiguan', 'Polo', 'Passat', 'T-Roc'],
            'Ford': ['Focus', 'Fiesta', 'Ranger', 'Kuga', 'Mondeo'],
        }
        n = 0
        for marque, mods in modeles_data.items():
            marque_id = marques_map.get(marque)
            if marque_id:
                for m in mods:
                    cur.execute("""
                        INSERT INTO vehicules_modeles (marque_id, nom, annee_debut, created_at)
                        VALUES (?,?,?,?)
                    """, (marque_id, m, 2010, datetime.now().isoformat()))
                    n += 1
        conn.commit()
        print(f"  ✅ {n} modèles créés")
    else:
        print("🚗 Modèles : déjà présents")

    # ═══════════════════════════════════════════════════════
    # 4. FOURNISSEURS
    # ═══════════════════════════════════════════════════════
    cur.execute("SELECT COUNT(*) FROM fournisseurs")
    if cur.fetchone()[0] == 0:
        print("🏭 Création des fournisseurs...")
        fournisseurs = [
            ('Auto Pièces Sénégal', 'grossiste', 'Sénégal', 'Dakar', '+221 33 821 10 10', 7),
            ('Sahel Auto Distribution', 'grossiste', 'Sénégal', 'Dakar', '+221 33 822 20 20', 5),
            ('CEDEAO Parts', 'importateur', "Côte d'Ivoire", 'Abidjan', '+225 27 21 30 40 50', 15),
            ('Euro Parts Import', 'importateur', 'France', 'Marseille', '+33 4 91 00 00 00', 30),
            ('Asia Auto Supply', 'importateur', 'Chine', 'Shanghai', '+86 21 0000 0000', 45),
            ('Nigeria Auto Hub', 'grossiste', 'Nigeria', 'Lagos', '+234 1 000 0000', 10),
            ('Maroc Pièces Pro', 'grossiste', 'Maroc', 'Casablanca', '+212 522 00 00 00', 12),
            ('Allemagne KFZ', 'importateur', 'Allemagne', 'Hamburg', '+49 40 000 000', 35),
        ]
        for nom, type_f, pays, ville, tel, delai in fournisseurs:
            cur.execute("""
                INSERT INTO fournisseurs (code, nom, type, pays, ville, telephone,
                    delai_livraison_jours, note, actif, created_at)
                VALUES (?,?,?,?,?,?,?,4,1,?)
            """, (None, nom, type_f, pays, ville, tel, delai, datetime.now().isoformat()))
        conn.commit()
        print(f"  ✅ {len(fournisseurs)} fournisseurs créés")
    else:
        print("🏭 Fournisseurs : déjà présents")

    # ═══════════════════════════════════════════════════════
    # 5. POINTS DE VENTE
    # ═══════════════════════════════════════════════════════
    cur.execute("SELECT COUNT(*) FROM points_vente")
    if cur.fetchone()[0] == 0:
        print("🏢 Création des points de vente...")
        pvs = [
            ('OMEGA PARTS Dakar Plateau', 'Rue Carnot', 'Dakar', '+221 33 821 00 01'),
            ('OMEGA PARTS Almadies', 'Route des Almadies', 'Dakar', '+221 33 820 00 02'),
            ('OMEGA PARTS Thiès', 'Avenue LSS', 'Thiès', '+221 33 951 00 03'),
            ('OMEGA PARTS Saint-Louis', 'Île Saint-Louis', 'Saint-Louis', '+221 33 961 00 04'),
        ]
        for nom, adresse, ville, tel in pvs:
            cur.execute("""
                INSERT INTO points_vente (code, nom, type, adresse, ville, pays,
                    telephone, actif, created_at)
                VALUES (?,?,?,?,?,?,?,1,?)
            """, (None, nom, 'magasin', adresse, ville, 'Sénégal', tel, datetime.now().isoformat()))
        conn.commit()
        print(f"  ✅ {len(pvs)} points de vente créés")
    else:
        print("🏢 Points de vente : déjà présents")

    # ═══════════════════════════════════════════════════════
    # 6. PIÈCES DÉTACHÉES — TOP 60 SN
    # ═══════════════════════════════════════════════════════
    cur.execute("SELECT COUNT(*) FROM pieces")
    if cur.fetchone()[0] == 0:
        print("🔧 Création des pièces détachées (Top 60 SN)...")

        # Récupérer les références
        cur.execute("SELECT id, code FROM categories WHERE parent_id IS NOT NULL")
        cats = {r['code']: r['id'] for r in cur.fetchall()}

        cur.execute("SELECT id FROM points_vente WHERE actif=1")
        pdv_ids = [r['id'] for r in cur.fetchall()]

        cur.execute("SELECT id FROM fournisseurs WHERE actif=1")
        fourn_ids = [r['id'] for r in cur.fetchall()]

        # TOP 60 pièces Sénégal
        pieces = [
            # 🔋 BATTERIES (7)
            ("Batterie Varta 12V 60Ah Blue Dynamic", "BAT-VARTA-60", "ELEC_BATT", "Varta", "premium", 55000, 1.4),
            ("Batterie Varta 12V 70Ah Blue Dynamic", "BAT-VARTA-70", "ELEC_BATT", "Varta", "premium", 75000, 1.4),
            ("Batterie Bosch 12V 45Ah S4", "BAT-BOSCH-45", "ELEC_BATT", "Bosch", "premium", 42000, 1.35),
            ("Batterie Bosch 12V 90Ah S5", "BAT-BOSCH-90", "ELEC_BATT", "Bosch", "premium", 95000, 1.4),
            ("Batterie Yuasa 12V 55Ah", "BAT-YUASA-55", "ELEC_BATT", "Yuasa", "équivalent", 45000, 1.35),
            ("Batterie Hankook 12V 60Ah", "BAT-HANKOOK-60", "ELEC_BATT", "Hankook", "équivalent", 48000, 1.4),
            ("Batterie ACDelco 12V 65Ah", "BAT-ACDELCO-65", "ELEC_BATT", "ACDelco", "standard", 52000, 1.35),

            # 🛑 FREINAGE (12)
            ("Plaquettes frein avant Toyota Corolla 2014-2019", "04465-02220", "FRE_PLAQ", "Toyota", "premium", 28000, 1.45),
            ("Plaquettes frein avant Toyota Hilux 2015+", "04465-0K290", "FRE_PLAQ", "Toyota", "premium", 35000, 1.45),
            ("Plaquettes frein avant Peugeot 208 2012-2019", "1611839880", "FRE_PLAQ", "Bosch", "équivalent", 22000, 1.4),
            ("Plaquettes frein avant Peugeot 308 2013+", "1619791080", "FRE_PLAQ", "Valeo", "premium", 26000, 1.45),
            ("Plaquettes frein arrière Renault Clio IV", "440605713R", "FRE_PLAQ", "Renault", "premium", 24000, 1.4),
            ("Plaquettes frein avant Hyundai Tucson", "58101-D3A00", "FRE_PLAQ", "Hyundai", "premium", 32000, 1.45),
            ("Disque frein avant 280mm Peugeot 308", "4249.36", "FRE_DISQ", "Brembo", "premium", 48000, 1.4),
            ("Disque frein avant 256mm Toyota Corolla", "43512-02210", "FRE_DISQ", "Toyota", "premium", 42000, 1.4),
            ("Disque frein avant 300mm Toyota Hilux", "43512-0K090", "FRE_DISQ", "Brembo", "premium", 58000, 1.4),
            ("Disque frein avant 283mm BMW Série 3", "34116792219", "FRE_DISQ", "ATE", "premium", 65000, 1.4),
            ("Liquide de frein DOT4 500ml", "DOT4-500", "FRE_LIQ", "Bosch", "standard", 4500, 1.6),
            ("Capteur ABS avant droit BMW X3", "34526763342", "FRE_ABSR", "ATE", "premium", 42000, 1.35),

            # 💧 FILTRATION (9)
            ("Filtre à huile Toyota Corolla", "90915-YZZE1", "FIL_HUIL", "Toyota", "premium", 8000, 1.5),
            ("Filtre à huile Peugeot 208/308", "1109.CK", "FIL_HUIL", "Mann", "premium", 7500, 1.5),
            ("Filtre à huile Renault Clio/Duster", "8200768913", "FIL_HUIL", "Mann", "équivalent", 6500, 1.5),
            ("Filtre à huile BMW Série 3", "11427508969", "FIL_HUIL", "Mahle", "premium", 15000, 1.45),
            ("Filtre à air Toyota Hilux", "17801-0L040", "FIL_AIR", "Toyota", "premium", 15000, 1.5),
            ("Filtre à air Peugeot 208", "1444.R3", "FIL_AIR", "Mann", "premium", 12000, 1.5),
            ("Filtre à air Hyundai Tucson", "28113-2S100", "FIL_AIR", "Hyundai", "premium", 18000, 1.5),
            ("Filtre carburant Toyota Hilux Diesel", "23390-0L041", "FIL_CARB", "Toyota", "premium", 22000, 1.5),
            ("Filtre carburant Peugeot 308 Diesel", "1901.E1", "FIL_CARB", "Purflux", "premium", 18000, 1.5),

            # ⚙️ SUSPENSION (8)
            ("Amortisseur avant gauche Toyota RAV4", "48510-49285", "SUS_AMOR", "KYB", "premium", 68000, 1.4),
            ("Amortisseur avant droit Toyota RAV4", "48510-49285", "SUS_AMOR", "KYB", "premium", 68000, 1.4),
            ("Amortisseur arrière Peugeot 3008", "5206.VP", "SUS_AMOR", "Monroe", "équivalent", 48000, 1.4),
            ("Amortisseur avant Renault Duster", "543029854R", "SUS_AMOR", "Renault", "premium", 55000, 1.4),
            ("Rotule de direction Renault Duster", "48520-4X01A", "SUS_ROTU", "Lemförder", "premium", 25000, 1.45),
            ("Rotule de suspension Peugeot 308", "3640.69", "SUS_ROTU", "Febi", "premium", 22000, 1.45),
            ("Roulement roue avant Nissan Qashqai", "40210-4BA0A", "SUS_ROUE", "SKF", "premium", 35000, 1.4),
            ("Roulement roue arrière Peugeot 208", "3748.44", "SUS_ROUE", "SKF", "premium", 32000, 1.4),

            # ⚡ ÉLECTRICITÉ (8)
            ("Alternateur Volkswagen Golf 7", "06B903016A", "ELEC_ALTE", "Valeo", "premium", 135000, 1.35),
            ("Alternateur Peugeot 308", "5705.KR", "ELEC_ALTE", "Valeo", "premium", 125000, 1.35),
            ("Démarreur Mercedes Classe C", "A0061516001", "ELEC_DEMA", "Bosch", "premium", 155000, 1.35),
            ("Bougie d'allumage NGK Honda Civic", "12290-R1A-H01", "MOT_BOUGIE", "NGK", "premium", 5500, 1.6),
            ("Bougie d'allumage Bosch Peugeot 208", "0242229704", "MOT_BOUGIE", "Bosch", "premium", 4800, 1.6),
            ("Capteur température moteur VW Golf", "059919501A", "ELEC_CAPT", "Bosch", "premium", 18000, 1.45),
            ("Capteur position vilebrequin Peugeot", "1920.EN", "ELEC_CAPT", "Valeo", "premium", 25000, 1.45),
            ("Capteur pression turbo BMW 320d", "13627805152", "ELEC_CAPT", "Bosch", "premium", 55000, 1.4),

            # 🔧 MOTEUR (6)
            ("Pompe à eau BMW Série 3", "11517586925", "MOT_POMP", "Graf", "premium", 62000, 1.4),
            ("Pompe à eau Peugeot 208/308", "1201.H9", "MOT_POMP", "SKF", "premium", 48000, 1.4),
            ("Courroie de distribution Peugeot 208", "0831.V5", "MOT_COUR", "Gates", "premium", 45000, 1.45),
            ("Courroie de distribution Renault Clio", "7701477028", "MOT_COUR", "Gates", "premium", 42000, 1.45),
            ("Radiateur refroidissement Peugeot 308", "1330.L2", "MOT_JOINT", "Valeo", "premium", 98000, 1.4),
            ("Ventilateur radiateur Toyota Corolla", "16363-0T080", "MOT_JOINT", "Denso", "premium", 78000, 1.4),

            # 💡 ÉCLAIRAGE (4)
            ("Phare avant gauche Toyota Hilux", "81150-0K180", "ECL_PHAR", "TYC", "équivalent", 95000, 1.35),
            ("Phare avant droit Peugeot 308", "6208.A3", "ECL_PHAR", "Valeo", "premium", 125000, 1.35),
            ("Ampoule H4 12V 60/55W", "H4-60-55", "ECL_AMP", "Philips", "standard", 3500, 1.6),
            ("Ampoule LED H7 Premium", "LED-H7-6000K", "ECL_AMP", "Osram", "premium", 18000, 1.5),

            # ⭕ PNEUMATIQUE (6)
            ("Pneu 195/65 R15 Michelin", "P195-65-15-MIC", "PNEUMATIQUE", "Michelin", "premium", 55000, 1.35),
            ("Pneu 205/55 R16 Michelin", "P205-55-16-MIC", "PNEUMATIQUE", "Michelin", "premium", 75000, 1.35),
            ("Pneu 215/65 R16 Goodyear", "P215-65-16-GY", "PNEUMATIQUE", "Goodyear", "premium", 85000, 1.35),
            ("Pneu 195/60 R15 Bridgestone", "P195-60-15-BRI", "PNEUMATIQUE", "Bridgestone", "premium", 60000, 1.35),
            ("Pneu 205/60 R16 Continental", "P205-60-16-CON", "PNEUMATIQUE", "Continental", "premium", 82000, 1.35),
            ("Pneu 175/70 R14 Michelin", "P175-70-14-MIC", "PNEUMATIQUE", "Michelin", "premium", 42000, 1.35),
        ]

        inserted = 0
        for p in pieces:
            nom, code_oem, cat_code, marque, qualite, prix_achat, marge = p
            cat_id = cats.get(cat_code)
            if not cat_id:
                print(f"  ⚠️  Catégorie {cat_code} non trouvée pour {nom[:40]}")
                continue

            prix_vente_detail = int(prix_achat * marge)
            prix_vente_gros = int(prix_vente_detail * 0.85)
            prix_vente_mecano = int(prix_vente_detail * 0.92)
            marge_pct = round((marge - 1) * 100, 1)

            # SKU auto
            today = datetime.now().strftime('%Y%m')
            cur.execute("SELECT sku FROM pieces WHERE sku LIKE ? ORDER BY id DESC LIMIT 1",
                        (f'PCS-{today}-%',))
            row = cur.fetchone()
            n = int(row['sku'].split('-')[-1]) + 1 if row else 1
            sku = f"PCS-{today}-{n:05d}"

            fourn_id = random.choice(fourn_ids) if fourn_ids else None

            cur.execute("""
                INSERT INTO pieces (
                    sku, code_oem, nom, categorie_id, marque_piece, qualite,
                    prix_achat, prix_vente_detail, prix_vente_gros, prix_vente_mecano,
                    marge_pct, tva_pct, stock_min, stock_max, stock_alerte,
                    garantie_mois, fournisseur_principal_id, statut, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                sku, code_oem, nom, cat_id, marque, qualite,
                prix_achat, prix_vente_detail, prix_vente_gros, prix_vente_mecano,
                marge_pct, 18, 5, 100, 10,
                12, fourn_id, 'disponible',
                datetime.now().isoformat(), datetime.now().isoformat()
            ))

            piece_id = cur.lastrowid
            inserted += 1

            # Stock par PDV
            for pdv_id in pdv_ids:
                qte = random.randint(15, 60)
                cur.execute("""
                    INSERT INTO stock (piece_id, point_vente_id, quantite, updated_at)
                    VALUES (?,?,?,?)
                """, (piece_id, pdv_id, qte, datetime.now().isoformat()))

        conn.commit()
        print(f"  ✅ {inserted} pièces créées")
        print(f"  ✅ Stock initialisé dans {len(pdv_ids)} PDV ({inserted * len(pdv_ids)} entrées)")
    else:
        print("🔧 Pièces : déjà présentes")

    # ═══════════════════════════════════════════════════════
    # 7. CLIENTS
    # ═══════════════════════════════════════════════════════
    cur.execute("SELECT COUNT(*) FROM clients")
    if cur.fetchone()[0] == 0:
        print("👥 Création des clients...")
        prenoms_h = ['Moussa', 'Amadou', 'Ibrahima', 'Cheikh', 'Ousmane', 'Mamadou', 'Pape']
        prenoms_f = ['Fatou', 'Awa', 'Aminata', 'Mariama', 'Aïssatou', 'Ndèye']
        noms = ['Diop', 'Ndiaye', 'Sall', 'Fall', 'Ba', 'Diallo', 'Sow', 'Sy', 'Faye']
        villes = ['Dakar', 'Thiès', 'Saint-Louis', 'Ziguinchor', 'Mbour']
        garages = ['Garage Central', 'Auto Service Plus', 'Mécanique Moderne', 'Garage Express']

        n = 0
        for i in range(40):
            type_client = random.choice(['particulier', 'particulier', 'mecano', 'garage'])

            if type_client == 'particulier':
                prenom = random.choice(prenoms_h + prenoms_f)
                nom = random.choice(noms)
                garage_nom = None
                remise = 0
            elif type_client == 'mecano':
                prenom = random.choice(prenoms_h)
                nom = random.choice(noms)
                garage_nom = None
                remise = round(random.uniform(3, 8), 1)
            else:
                prenom = None
                nom = random.choice(garages)
                garage_nom = nom
                remise = round(random.uniform(8, 15), 1)

            tel = f'+221 77 {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}'

            cur.execute("""
                INSERT INTO clients (code, nom, prenom, type, telephone, whatsapp, email,
                    ville, pays, type_client, garage_nom, remise_pct,
                    score, total_achats, nb_achats, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0,0,'actif',?)
            """, (None, nom, prenom,
                  'particulier' if type_client == 'particulier' else 'professionnel',
                  tel, tel, f'{nom.lower()}@email.sn',
                  random.choice(villes), 'Sénégal', type_client, garage_nom, remise,
                  random.randint(50, 95), datetime.now().isoformat()))
            n += 1

        conn.commit()
        print(f"  ✅ {n} clients créés")
    else:
        print("👥 Clients : déjà présents")

    # ═══════════════════════════════════════════════════════
    # 8. PARAMÈTRES
    # ═══════════════════════════════════════════════════════
    cur.execute("SELECT COUNT(*) FROM parametres")
    if cur.fetchone()[0] == 0:
        print("⚙️  Création des paramètres...")
        params = [
            ('nom_entreprise', 'OMEGA PARTS', 'Nom affiché'),
            ('tva_defaut', '18', 'TVA par défaut (%)'),
            ('devise', 'FCFA', 'Devise'),
            ('pays', 'Sénégal', 'Pays'),
            ('adresse', 'Dakar, Sénégal', 'Adresse'),
            ('telephone', '+221 33 821 00 00', 'Téléphone'),
            ('email', 'contact@omega-parts.sn', 'Email'),
            ('site_web', 'www.omega-parts.sn', 'Site web'),
        ]
        for cle, valeur, desc in params:
            cur.execute("INSERT INTO parametres (cle, valeur, description) VALUES (?,?,?)",
                        (cle, valeur, desc))
        conn.commit()
        print(f"  ✅ {len(params)} paramètres créés")
    else:
        print("⚙️  Paramètres : déjà présents")

    # ═══════════════════════════════════════════════════════
    # RÉSUMÉ FINAL
    # ═══════════════════════════════════════════════════════
    print()
    print("═" * 50)
    print("📊 RÉSUMÉ FINAL")
    print("═" * 50)

    tables = ['users', 'categories', 'vehicules_marques', 'vehicules_modeles',
              'fournisseurs', 'points_vente', 'pieces', 'stock', 'clients', 'parametres']
    for t in tables:
        cur.execute(f'SELECT COUNT(*) FROM {t}')
        count = cur.fetchone()[0]
        status = '✅' if count > 0 else '❌'
        print(f"  {status} {t:25} : {count}")

    conn.close()
    print()
    print("═" * 50)
    print("✅ IMPORT TERMINÉ")
    print("═" * 50)

if __name__ == '__main__':
    main()
