"""
🏦 MicroFinance 2.0 — Migration v2
Vues SQL + Données démo (clients, crédits, échéances, remboursements)
"""
import sqlite3
import random
from datetime import datetime, timedelta, date

DB_PATH = "/app/data/microfinance.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def migrate():
    print("[MIGRATE v2] Démarrage...")
    conn = get_conn()
    c = conn.cursor()

    # ==================== VUES SQL ====================

    c.execute("DROP VIEW IF EXISTS v_clients_complets")
    c.execute("""CREATE VIEW v_clients_complets AS
                 SELECT cl.*,
                        r.nom AS region_nom,
                        a.nom AS agence_nom,
                        a.code AS agence_code,
                        (SELECT COUNT(*) FROM credits WHERE client_id=cl.id AND statut='Actif') AS nb_credits_actifs,
                        (SELECT COALESCE(SUM(solde_restant), 0) FROM credits WHERE client_id=cl.id AND statut='Actif') AS encours_total,
                        (SELECT COALESCE(SUM(montant), 0) FROM operations_epargne WHERE compte_id IN
                            (SELECT id FROM comptes_epargne WHERE client_id=cl.id) AND type_operation='Dépôt') AS total_epargne
                 FROM clients cl
                 LEFT JOIN regions r ON cl.region_id = r.id
                 LEFT JOIN agences a ON cl.agence_id = a.id
                 WHERE cl.actif = 1""")
    print("[MIGRATE v2] ✅ Vue v_clients_complets créée")

    c.execute("DROP VIEW IF EXISTS v_credits_complets")
    c.execute("""CREATE VIEW v_credits_complets AS
                 SELECT cr.*,
                        cl.nom AS client_nom, cl.prenom AS client_prenom,
                        cl.telephone AS client_telephone,
                        cl.code AS client_code,
                        pr.nom AS produit_nom,
                        pr.code AS produit_code,
                        a.nom AS agence_nom
                 FROM credits cr
                 LEFT JOIN clients cl ON cr.client_id = cl.id
                 LEFT JOIN produits pr ON cr.produit_id = pr.id
                 LEFT JOIN agences a ON cr.agence_id = a.id""")
    print("[MIGRATE v2] ✅ Vue v_credits_complets créée")

    c.execute("DROP VIEW IF EXISTS v_echeances_impayees")
    c.execute("""CREATE VIEW v_echeances_impayees AS
                 SELECT ec.*,
                        cr.reference AS credit_ref,
                        cr.client_id,
                        cl.nom AS client_nom, cl.prenom AS client_prenom,
                        cl.telephone AS client_telephone,
                        a.nom AS agence_nom
                 FROM echeances_credit ec
                 INNER JOIN credits cr ON ec.credit_id = cr.id
                 INNER JOIN clients cl ON cr.client_id = cl.id
                 LEFT JOIN agences a ON cr.agence_id = a.id
                 WHERE ec.statut IN ('En retard', 'Impayé')
                   AND cr.statut = 'Actif'
                 ORDER BY ec.jours_retard DESC""")
    print("[MIGRATE v2] ✅ Vue v_echeances_impayees créée")

    c.execute("DROP VIEW IF EXISTS v_stats_agence")
    c.execute("""CREATE VIEW v_stats_agence AS
                 SELECT a.id AS agence_id, a.code, a.nom,
                        (SELECT COUNT(*) FROM clients WHERE agence_id=a.id AND actif=1) AS nb_clients,
                        (SELECT COUNT(*) FROM credits WHERE agence_id=a.id AND statut='Actif') AS nb_credits_actifs,
                        (SELECT COALESCE(SUM(montant_principal), 0) FROM credits WHERE agence_id=a.id AND statut='Actif') AS encours_total,
                        (SELECT COALESCE(SUM(montant_recu), 0) FROM remboursements r
                         INNER JOIN credits c ON r.credit_id = c.id
                         WHERE c.agence_id = a.id) AS total_rembourse,
                        (SELECT COUNT(*) FROM echeances_credit ec
                         INNER JOIN credits c ON ec.credit_id = c.id
                         WHERE c.agence_id = a.id AND ec.statut IN ('En retard', 'Impayé')) AS nb_impayes
                 FROM agences a
                 WHERE a.actif = 1""")
    print("[MIGRATE v2] ✅ Vue v_stats_agence créée")

    c.execute("DROP VIEW IF EXISTS v_dashboard_kpi")
    c.execute("""CREATE VIEW v_dashboard_kpi AS
                 SELECT
                    (SELECT COUNT(*) FROM clients WHERE actif=1) AS total_clients,
                    (SELECT COUNT(*) FROM clients WHERE statut='Actif' AND kyc_statut='Validé') AS clients_kyc_ok,
                    (SELECT COUNT(*) FROM credits WHERE statut='Actif') AS credits_actifs,
                    (SELECT COALESCE(SUM(solde_restant), 0) FROM credits WHERE statut='Actif') AS encours_total,
                    (SELECT COUNT(*) FROM echeances_credit WHERE statut='En retard') AS echeances_retard,
                    (SELECT COALESCE(SUM(montant_restant), 0) FROM echeances_credit WHERE statut='En retard') AS montant_retard,
                    (SELECT COUNT(*) FROM demandes_credit WHERE statut='En analyse') AS demandes_en_attente,
                    (SELECT COUNT(*) FROM declarations_soupcon WHERE statut='À analyser') AS declarations_lcb""")
    print("[MIGRATE v2] ✅ Vue v_dashboard_kpi créée")

    conn.commit()

    # ==================== DONNÉES DÉMO ====================
    c.execute("SELECT COUNT(*) FROM clients")
    if c.fetchone()[0] == 0:
        print("[MIGRATE v2] Génération données démo...")
        _seed_exploitation(c, conn)

    conn.close()
    print("[MIGRATE v2] ✅ Migration terminée")


def _seed_exploitation(c, conn):
    """Génère clients, crédits, échéances, remboursements"""
    random.seed(42)
    now = datetime.now()

    # ============ CLIENTS (50) ============
    noms_sen = [
        ('Diop', 'Mamadou'), ('Ndiaye', 'Fatou'), ('Fall', 'Omar'), ('Sow', 'Aminata'),
        ('Ba', 'Ibrahima'), ('Diallo', 'Awa'), ('Sarr', 'Cheikh'), ('Kane', 'Mariama'),
        ('Gueye', 'Abdoulaye'), ('Sylla', 'Kadidiatou'), ('Cisse', 'Moussa'), ('Barry', 'Alpha'),
        ('Toure', 'Ousmane'), ('Beye', 'Saliou'), ('Mbaye', 'Alioune'), ('Faye', 'Bineta'),
        ('Diagne', 'Lamine'), ('Sene', 'Fatoumata'), ('Badji', 'Moussa'), ('Diatta', 'Rokhaya'),
        ('Dieng', 'Ousmane'), ('Ka', 'Aminata'), ('Lo', 'Pape'), ('Niang', 'Awa'),
        ('Thiam', 'Moustapha'), ('Sagna', 'Coumba'), ('Mendy', 'Jean'), ('Coly', 'Aline'),
        ('Goudiaby', 'Saliou'), ('Sambou', 'Marie'), ('Diédhiou', 'Pierre'), ('Sane', 'Awa'),
        ('Camara', 'Moussa'), ('Sy', 'Fatou'), ('Sow', 'Mariama'), ('Balde', 'Amadou'),
        ('Bah', 'Aissatou'), ('Barry', 'Mamadou'), ('Diallo', 'Binta'), ('Sow', 'Ousmane'),
        ('Kouyaté', 'Seydou'), ('Camara', 'Fanta'), ('Traoré', 'Boubacar'), ('Cissé', 'Adama'),
        ('Konaté', 'Moussa'), ('Doumbia', 'Kadiatou'), ('Sanogo', 'Ibrahim'), ('Coulibaly', 'Awa'),
        ('Touré', 'Oumar'), ('Sidibé', 'Mariam')
    ]

    client_ids = []
    professions = ['Commerçant', 'Agriculteur', 'Artisan', 'Éleveur', 'Couturière',
                   'Restauratrice', 'Chauffeur', 'Mécanicien', 'Vendeur', 'Fonctionnaire']
    activites = ['Commerce', 'Agriculture', 'Artisanat', 'Élevage', 'Couture',
                 'Restauration', 'Transport', 'Mécanique', 'Vente', 'Services']

    for i, (nom, prenom) in enumerate(noms_sen, 1):
        code = f"CLI-{i:05d}"
        agence_id = random.randint(1, 5)
        region_id = random.randint(1, 14)
        age = random.randint(22, 65)
        date_naissance = (now - timedelta(days=age*365)).date().isoformat()
        revenu = random.randint(50000, 500000)
        profession = random.choice(professions)
        activite = random.choice(activites)

        # KYC statut
        kyc_statut = random.choice(['Validé', 'Validé', 'Validé', 'En attente'])

        c.execute("""INSERT INTO clients
            (code, type_client, nom, prenom, date_naissance, sexe, situation_familiale,
             telephone, email, adresse, ville, region_id, numero_cni,
             profession, revenu_mensuel, activite_principale,
             agence_id, statut, date_adhesion, kyc_statut,
             score_interne, actif)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (code, 'Particulier', nom, prenom, date_naissance,
             random.choice(['M', 'F']),
             random.choice(['Célibataire', 'Marié(e)', 'Divorcé(e)', 'Veuf(ve)']),
             f"77{random.randint(1000000, 9999999)}",
             f"{prenom.lower()}.{nom.lower()}@email.sn",
             f"Quartier {random.randint(1, 20)}",
             f"Ville {random.randint(1, 10)}",
             region_id, f"CNI{random.randint(100000000, 999999999)}",
             profession, revenu, activite,
             agence_id, 'Actif',
             (now - timedelta(days=random.randint(30, 1000))).date().isoformat(),
             kyc_statut, random.randint(400, 800), 1))
        client_ids.append(c.lastrowid)

    print(f"[MIGRATE v2] ✅ {len(client_ids)} clients créés")

    # ============ COMPTES ÉPARGNE (30) ============
    for client_id in client_ids[:30]:
        num_compte = f"EP{random.randint(100000, 999999)}"
        solde = random.randint(5000, 500000)

        c.execute("""INSERT INTO comptes_epargne
            (numero_compte, client_id, agence_id, solde, solde_disponible,
             date_ouverture, date_derniere_operation, statut)
            VALUES (?,?,?,?,?,?,?, 'Actif')""",
            (num_compte, client_id, random.randint(1, 5), solde, solde,
             (now - timedelta(days=random.randint(30, 365))).date().isoformat(),
             now.date().isoformat()))

    print(f"[MIGRATE v2] ✅ 30 comptes épargne créés")

    # ============ CRÉDITS (40) ============
    statuts_credit = ['Actif', 'Actif', 'Actif', 'Actif', 'Remboursé', 'En retard']
    credit_ids = []
    echeance_ids = []

    for i in range(40):
        client_id = random.choice(client_ids)
        produit_id = random.randint(1, 6)
        agence_id = random.randint(1, 5)

        # Paramètres produit
        c.execute("SELECT * FROM produits WHERE id=?", (produit_id,))
        prod = c.fetchone()

        montant = random.randint(prod['montant_min'], min(prod['montant_max'], 2000000))
        duree_min = max(2, prod['duree_min_mois'] or 2)
        duree_max = max(duree_min + 1, min(prod['duree_max_mois'] or 12, 24))
        duree = random.randint(duree_min, duree_max)
        taux = random.uniform(prod['taux_interet_min'], prod['taux_interet_max'])

        # Calculs
        interets = int(montant * taux / 100 * duree / 12)
        frais = int(montant * (prod['frais_dossier_pct'] or 0) / 100) + (prod['frais_dossier_fixe'] or 0)
        assurance = int(montant * (prod['assurance_pct'] or 0) / 100)
        total_du = montant + interets + frais + assurance

        date_dec = now - timedelta(days=random.randint(30, 500))
        date_prem = date_dec + timedelta(days=30)
        date_fin = date_prem + timedelta(days=30*duree)

        statut = random.choice(statuts_credit)
        classification = 'Sain' if statut == 'Actif' else ('Remboursé' if statut == 'Remboursé' else 'Sous surveillance')

        # Remboursements
        if statut == 'Remboursé':
            montant_rembourse = total_du
            solde = 0
            nb_payees = duree
        elif statut == 'En retard':
            nb_payees = random.randint(1, max(1, duree // 2))
            montant_rembourse = int(total_du * nb_payees / duree)
            solde = total_du - montant_rembourse
        else:  # Actif
            nb_payees = random.randint(1, max(1, duree - 1))
            montant_rembourse = int(total_du * nb_payees / duree)
            solde = total_du - montant_rembourse

        ref = f"CRD-{date_dec.strftime('%Y%m%d')}-{i+1:04d}"

        c.execute("""INSERT INTO credits
            (reference, client_id, produit_id, agence_id,
             montant_principal, taux_interet, duree_mois, periodicite,
             date_decaissement, date_premiere_echeance, date_fin_prevue,
             montant_interets, montant_frais, montant_assurance, montant_total_du,
             montant_rembourse, capital_restant, solde_restant,
             nb_echeances, nb_echeances_payees, statut, classification)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ref, client_id, produit_id, agence_id,
             montant, round(taux, 2), duree, 'Mensuel',
             date_dec.date().isoformat(), date_prem.date().isoformat(), date_fin.date().isoformat(),
             interets, frais, assurance, total_du,
             montant_rembourse, solde, solde,
             duree, nb_payees, statut, classification))
        credit_id = c.lastrowid
        credit_ids.append(credit_id)

        # ============ ÉCHÉANCES ============
        montant_echeance = int(total_du / duree)

        for j in range(duree):
            date_ech = date_prem + timedelta(days=30*j)
            est_payee = j < nb_payees
            est_retard = statut == 'En retard' and j >= nb_payees and date_ech < now

            if est_payee:
                statut_ech = 'Payé'
                montant_paye = montant_echeance
                date_paiement = (date_ech + timedelta(days=random.randint(-3, 5))).date().isoformat()
                jours_retard = 0
            elif est_retard:
                statut_ech = 'En retard'
                montant_paye = 0
                date_paiement = None
                jours_retard = (now.date() - date_ech.date()).days
            else:
                statut_ech = 'À venir'
                montant_paye = 0
                date_paiement = None
                jours_retard = 0

            c.execute("""INSERT INTO echeances_credit
                (credit_id, numero_echeance, date_echeance,
                 montant_capital, montant_interets, montant_total,
                 montant_paye, montant_restant, date_paiement,
                 statut, jours_retard)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (credit_id, j+1, date_ech.date().isoformat(),
                 int(montant_echeance * 0.7), int(montant_echeance * 0.3), montant_echeance,
                 montant_paye, montant_echeance - montant_paye, date_paiement,
                 statut_ech, jours_retard))

    print(f"[MIGRATE v2] ✅ {len(credit_ids)} crédits + échéances créés")

    # ============ REMBOURSEMENTS ============
    nb_remb = 0
    for credit_id in credit_ids:
        c.execute("""SELECT * FROM echeances_credit
                     WHERE credit_id=? AND statut='Payé'
                     ORDER BY numero_echeance""", (credit_id,))
        echeances = c.fetchall()

        for ec in echeances:
            ref = f"RMB-{datetime.now().strftime('%Y%m%d')}-{nb_remb+1:05d}"
            c.execute("""INSERT INTO remboursements
                (reference, credit_id, echeance_id, client_id,
                 montant_recu, montant_capital, montant_interets,
                 mode_paiement, date_paiement)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (ref, credit_id, ec['id'],
                 c.execute("SELECT client_id FROM credits WHERE id=?", (credit_id,)).fetchone()[0],
                 ec['montant_paye'], ec['montant_capital'], ec['montant_interets'],
                 random.choice(['Espèces', 'Wave', 'Orange Money', 'Free Money']),
                 ec['date_paiement']))
            nb_remb += 1

    print(f"[MIGRATE v2] ✅ {nb_remb} remboursements créés")

    # ============ DEMANDES DE CRÉDIT (15) ============
    for i in range(15):
        client_id = random.choice(client_ids)
        produit_id = random.randint(1, 6)
        montant = random.randint(50000, 2000000)
        duree = random.randint(3, 24)
        statut = random.choice(['En analyse', 'En analyse', 'Approuvé', 'Rejeté'])
        ref = f"DEM-{datetime.now().strftime('%Y%m%d')}-{i+1:04d}"

        c.execute("""INSERT INTO demandes_credit
            (reference, client_id, produit_id, agence_id,
             montant_demande, duree_mois, objet_credit, activite_financee,
             date_demande, statut, score_ia, niveau_risque)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ref, client_id, produit_id, random.randint(1, 5),
             montant, duree,
             random.choice(['Achat marchandise', 'Matériel', 'Fonds de roulement', 'Formation']),
             random.choice(['Commerce', 'Agriculture', 'Artisanat']),
             (now - timedelta(days=random.randint(1, 60))).date().isoformat(),
             statut,
             random.randint(400, 800),
             random.choice(['Faible', 'Moyen', 'Élevé'])))

    print(f"[MIGRATE v2] ✅ 15 demandes de crédit créées")

    # ============ TRANSACTIONS MOBILE MONEY (80) ============
    nb_mm = 0
    for i in range(80):
        client_id = random.choice(client_ids)
        fournisseur = random.choice(['Wave', 'Orange Money', 'Free Money'])
        montant = random.randint(1000, 500000)
        type_t = random.choice(['Dépôt', 'Remboursement', 'Paiement', 'Transfert'])
        statut = random.choice(['Réussi', 'Réussi', 'Réussi', 'En attente', 'Échoué'])

        ref = f"MM-{now.strftime('%Y%m%d')}-{i+1:05d}"
        c.execute("""INSERT INTO transactions_mobile
            (reference, client_id, fournisseur, telephone,
             type_transaction, montant, statut, date_initiation)
            VALUES (?,?,?,?,?,?,?,?)""",
            (ref, client_id, fournisseur,
             f"77{random.randint(1000000, 9999999)}",
             type_t, montant, statut,
             (now - timedelta(days=random.randint(1, 90))).isoformat()))
        nb_mm += 1

    print(f"[MIGRATE v2] ✅ {nb_mm} transactions Mobile Money créées")

    # ============ SCORES DE CRÉDIT (30) ============
    for client_id in client_ids[:30]:
        score = random.randint(300, 850)
        niveau = 'Excellent' if score >= 750 else ('Bon' if score >= 650 else ('Moyen' if score >= 500 else 'Faible'))

        c.execute("""INSERT INTO scores_credit
            (client_id, date_evaluation, score, niveau,
             probabilite_defaut, revenus_totaux, charges_totales,
             capacite_remboursement, historique_credit,
             recommandation, montant_max_recommande, modele_version)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (client_id, datetime.now().isoformat(), score, niveau,
             round((850 - score) / 850, 3),
             random.randint(100000, 500000),
             random.randint(30000, 200000),
             random.randint(50000, 300000),
             random.randint(0, 5),
             random.choice(['Accorder', 'Accorder', 'Accorder avec garanties', 'Refuser']),
             score * 1000,
             'v1.0'))

    print(f"[MIGRATE v2] ✅ 30 scores de crédit créés")

    conn.commit()


if __name__ == '__main__':
    migrate()
