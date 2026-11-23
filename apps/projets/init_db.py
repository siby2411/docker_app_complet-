"""
Base de données Gestion de Projets Omega
Conforme PMI / PRINCE2 / ISO 21500 — UEMOA
32 tables : portefeuille, programmes, projets, WBS, tâches, ressources,
risques, achats, qualité, EVM, devises
"""
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "/app/data/projets.db"


def init_db():
    os.makedirs("/app/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    c = conn.cursor()

    # ==================== 1. DEVISES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS devises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        symbole TEXT,
        taux_fcfa REAL DEFAULT 1,
        reference INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1
    )""")

    # ==================== 2. SITES (Zones UEMOA) ====================
    c.execute("""CREATE TABLE IF NOT EXISTS sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        pays TEXT NOT NULL,
        ville TEXT,
        zone_uemoa TEXT,
        adresse TEXT,
        telephone TEXT,
        responsable TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 3. CLIENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        type_client TEXT DEFAULT 'Entreprise',
        nom TEXT NOT NULL,
        contact_nom TEXT,
        telephone TEXT NOT NULL,
        email TEXT,
        adresse TEXT,
        ville TEXT,
        pays TEXT DEFAULT 'Sénégal',
        nif TEXT,
        rccm TEXT,
        secteur TEXT,
        conditions_paiement TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 4. FOURNISSEURS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS fournisseurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        contact TEXT,
        telephone TEXT NOT NULL,
        email TEXT,
        adresse TEXT,
        pays TEXT DEFAULT 'Sénégal',
        nif TEXT,
        specialite TEXT,
        note_qualite REAL DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 5. PORTEFEUILLE ====================
    c.execute("""CREATE TABLE IF NOT EXISTS portefeuilles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        responsable_id INTEGER,
        budget_total REAL DEFAULT 0,
        devise TEXT DEFAULT 'FCFA',
        date_debut TEXT,
        date_fin TEXT,
        statut TEXT DEFAULT 'Actif',
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 6. PROGRAMMES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS programmes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        portefeuille_id INTEGER,
        responsable_id INTEGER,
        budget_total REAL DEFAULT 0,
        devise TEXT DEFAULT 'FCFA',
        date_debut TEXT,
        date_fin TEXT,
        objectif_strategique TEXT,
        statut TEXT DEFAULT 'Actif',
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (portefeuille_id) REFERENCES portefeuilles(id)
    )""")

    # ==================== 7. PROJETS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS projets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        programme_id INTEGER,
        client_id INTEGER,
        chef_projet_id INTEGER,
        site_id INTEGER,
        type_projet TEXT DEFAULT 'Construction',
        methodologie TEXT DEFAULT 'Hybride',
        priorite TEXT DEFAULT 'Normale',
        complexite TEXT DEFAULT 'Moyenne',
        date_debut_prevue TEXT,
        date_fin_prevue TEXT,
        date_debut_reelle TEXT,
        date_fin_reelle TEXT,
        duree_jours INTEGER DEFAULT 0,
        budget_prevu REAL DEFAULT 0,
        budget_engage REAL DEFAULT 0,
        budget_consomme REAL DEFAULT 0,
        devise TEXT DEFAULT 'FCFA',
        marge_cible REAL DEFAULT 0,
        avancement_pct REAL DEFAULT 0,
        statut TEXT DEFAULT 'En préparation',
        sante_projet TEXT DEFAULT 'Vert',
        objectifs TEXT,
        perimetre TEXT,
        exclusions TEXT,
        hypotheses TEXT,
        contraintes TEXT,
        notes TEXT,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (programme_id) REFERENCES programmes(id),
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (chef_projet_id) REFERENCES utilisateurs(id),
        FOREIGN KEY (site_id) REFERENCES sites(id)
    )""")

    # ==================== 8. MEMBRES DU PROJET ====================
    c.execute("""CREATE TABLE IF NOT EXISTS projet_equipe (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projet_id INTEGER NOT NULL,
        utilisateur_id INTEGER NOT NULL,
        role_projet TEXT NOT NULL,
        date_affectation TEXT NOT NULL,
        date_fin TEXT,
        taux_horaire REAL DEFAULT 0,
        actif INTEGER DEFAULT 1,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 9. PHASES / LOT DE TRAVAIL ====================
    c.execute("""CREATE TABLE IF NOT EXISTS phases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projet_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        ordre INTEGER DEFAULT 0,
        date_debut TEXT,
        date_fin TEXT,
        avancement_pct REAL DEFAULT 0,
        budget_alloue REAL DEFAULT 0,
        statut TEXT DEFAULT 'À venir',
        FOREIGN KEY (projet_id) REFERENCES projets(id)
    )""")

    # ==================== 10. WBS / TÂCHES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS taches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        projet_id INTEGER NOT NULL,
        phase_id INTEGER,
        wbs_code TEXT,
        wbs_niveau INTEGER DEFAULT 1,
        parent_id INTEGER,
        nom TEXT NOT NULL,
        description TEXT,
        type_tache TEXT DEFAULT 'Tâche',
        responsable_id INTEGER,
        priorite TEXT DEFAULT 'Normale',
        complexite INTEGER DEFAULT 1,
        date_debut_prevue TEXT,
        date_fin_prevue TEXT,
        date_debut_reelle TEXT,
        date_fin_reelle TEXT,
        duree_prevue_heures REAL DEFAULT 0,
        duree_reelle_heures REAL DEFAULT 0,
        effort_estime REAL DEFAULT 0,
        effort_consomme REAL DEFAULT 0,
        avancement_pct REAL DEFAULT 0,
        cout_prevu REAL DEFAULT 0,
        cout_reel REAL DEFAULT 0,
        statut TEXT DEFAULT 'À faire',
        jalon INTEGER DEFAULT 0,
        chemin_critique INTEGER DEFAULT 0,
        methode_agile TEXT,
        story_points INTEGER DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (phase_id) REFERENCES phases(id),
        FOREIGN KEY (parent_id) REFERENCES taches(id),
        FOREIGN KEY (responsable_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 11. DÉPENDANCES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS dependances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projet_id INTEGER NOT NULL,
        tache_source_id INTEGER NOT NULL,
        tache_cible_id INTEGER NOT NULL,
        type_dependance TEXT DEFAULT 'FS',
        decalage_jours INTEGER DEFAULT 0,
        obligatoire INTEGER DEFAULT 1,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (tache_source_id) REFERENCES taches(id),
        FOREIGN KEY (tache_cible_id) REFERENCES taches(id)
    )""")

    # ==================== 12. AFFECTATIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS affectations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projet_id INTEGER NOT NULL,
        tache_id INTEGER,
        utilisateur_id INTEGER NOT NULL,
        date_debut TEXT,
        date_fin TEXT,
        charge_heures REAL DEFAULT 0,
        taux_allocation REAL DEFAULT 100,
        taux_horaire REAL DEFAULT 0,
        cout_prevu REAL DEFAULT 0,
        cout_reel REAL DEFAULT 0,
        statut TEXT DEFAULT 'Prévu',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (tache_id) REFERENCES taches(id),
        FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 13. JALONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS jalons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projet_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        nom TEXT NOT NULL,
        description TEXT,
        date_prevue TEXT NOT NULL,
        date_reelle TEXT,
        statut TEXT DEFAULT 'À venir',
        obligatoire INTEGER DEFAULT 1,
        FOREIGN KEY (projet_id) REFERENCES projets(id)
    )""")

    # ==================== 14. RISQUES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS risques (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        projet_id INTEGER NOT NULL,
        tache_id INTEGER,
        titre TEXT NOT NULL,
        description TEXT,
        categorie TEXT,
        type_risque TEXT DEFAULT 'Menace',
        probabilite INTEGER DEFAULT 1,
        impact INTEGER DEFAULT 1,
        criticite INTEGER DEFAULT 1,
        niveau_risque TEXT DEFAULT 'Faible',
        date_identification TEXT NOT NULL,
        identifie_par INTEGER,
        responsable_id INTEGER,
        strategie TEXT DEFAULT 'Réduire',
        plan_mitigation TEXT,
        plan_contigence TEXT,
        cout_mitigation REAL DEFAULT 0,
        date_echeance TEXT,
        statut TEXT DEFAULT 'Ouvert',
        date_cloture TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (tache_id) REFERENCES taches(id),
        FOREIGN KEY (identifie_par) REFERENCES utilisateurs(id),
        FOREIGN KEY (responsable_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 15. ACTIONS (issues de risques) ====================
    c.execute("""CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        projet_id INTEGER NOT NULL,
        risque_id INTEGER,
        titre TEXT NOT NULL,
        description TEXT,
        responsable_id INTEGER,
        date_echeance TEXT,
        priorite TEXT DEFAULT 'Normale',
        statut TEXT DEFAULT 'À faire',
        avancement_pct REAL DEFAULT 0,
        date_creation TEXT NOT NULL,
        date_cloture TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (risque_id) REFERENCES risques(id),
        FOREIGN KEY (responsable_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 16. BUDGET LIGNES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS budget_lignes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projet_id INTEGER NOT NULL,
        phase_id INTEGER,
        code TEXT NOT NULL,
        designation TEXT NOT NULL,
        categorie TEXT,
        quantite REAL DEFAULT 1,
        unite TEXT,
        prix_unitaire REAL DEFAULT 0,
        montant_prevu REAL DEFAULT 0,
        montant_engage REAL DEFAULT 0,
        montant_consomme REAL DEFAULT 0,
        devise TEXT DEFAULT 'FCFA',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (phase_id) REFERENCES phases(id)
    )""")

    # ==================== 17. ENGAGEMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS engagements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        projet_id INTEGER NOT NULL,
        fournisseur_id INTEGER,
        type_engagement TEXT DEFAULT 'Commande',
        date_engagement TEXT NOT NULL,
        date_livraison_prevue TEXT,
        montant REAL NOT NULL,
        devise TEXT DEFAULT 'FCFA',
        description TEXT,
        statut TEXT DEFAULT 'En cours',
        reference TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id)
    )""")

    # ==================== 18. FACTURES CLIENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS factures_client (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        projet_id INTEGER NOT NULL,
        client_id INTEGER NOT NULL,
        date_facture TEXT NOT NULL,
        date_echeance TEXT,
        type_facture TEXT DEFAULT 'Situation',
        montant_ht REAL DEFAULT 0,
        taux_tva REAL DEFAULT 18,
        montant_tva REAL DEFAULT 0,
        montant_ttc REAL DEFAULT 0,
        montant_paye REAL DEFAULT 0,
        solde REAL DEFAULT 0,
        devise TEXT DEFAULT 'FCFA',
        statut TEXT DEFAULT 'Impayé',
        notes TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")

    # ==================== 19. PAIEMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS paiements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        facture_id INTEGER,
        projet_id INTEGER,
        type_paiement TEXT DEFAULT 'Encaissement',
        date_paiement TEXT NOT NULL,
        montant REAL NOT NULL,
        devise TEXT DEFAULT 'FCFA',
        mode_paiement TEXT,
        reference TEXT,
        statut TEXT DEFAULT 'Validé',
        user_id INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (facture_id) REFERENCES factures_client(id),
        FOREIGN KEY (projet_id) REFERENCES projets(id)
    )""")

    # ==================== 20. EVM (Valeur Acquise) ====================
    c.execute("""CREATE TABLE IF NOT EXISTS evm (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projet_id INTEGER NOT NULL,
        date_mesure TEXT NOT NULL,
        pv REAL DEFAULT 0,
        ev REAL DEFAULT 0,
        ac REAL DEFAULT 0,
        bac REAL DEFAULT 0,
        sv REAL DEFAULT 0,
        cv REAL DEFAULT 0,
        spi REAL DEFAULT 0,
        cpi REAL DEFAULT 0,
        eac REAL DEFAULT 0,
        etc REAL DEFAULT 0,
        vac REAL DEFAULT 0,
        tcpi REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id)
    )""")

    # ==================== 21. LIVRABLES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS livrables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        projet_id INTEGER NOT NULL,
        phase_id INTEGER,
        nom TEXT NOT NULL,
        description TEXT,
        type_livrable TEXT,
        responsable_id INTEGER,
        date_prevue TEXT,
        date_livraison TEXT,
        statut TEXT DEFAULT 'En attente',
        version TEXT DEFAULT '1.0',
        chemin_fichier TEXT,
        valide_par INTEGER,
        date_validation TEXT,
        commentaires TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (phase_id) REFERENCES phases(id),
        FOREIGN KEY (responsable_id) REFERENCES utilisateurs(id),
        FOREIGN KEY (valide_par) REFERENCES utilisateurs(id)
    )""")

    # ==================== 22. DOCUMENTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projet_id INTEGER,
        tache_id INTEGER,
        livrable_id INTEGER,
        categorie TEXT,
        titre TEXT NOT NULL,
        description TEXT,
        reference TEXT,
        version TEXT DEFAULT '1.0',
        chemin_fichier TEXT,
        taille_ko REAL DEFAULT 0,
        mime_type TEXT,
        auteur_id INTEGER,
        statut TEXT DEFAULT 'Brouillon',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (tache_id) REFERENCES taches(id),
        FOREIGN KEY (livrable_id) REFERENCES livrables(id),
        FOREIGN KEY (auteur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 23. RÉUNIONS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS reunions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        projet_id INTEGER NOT NULL,
        type_reunion TEXT DEFAULT 'Avancement',
        titre TEXT NOT NULL,
        date_reunion TEXT NOT NULL,
        duree_minutes INTEGER DEFAULT 60,
        lieu TEXT,
        ordre_du_jour TEXT,
        participants TEXT,
        animateur_id INTEGER,
        statut TEXT DEFAULT 'Planifiée',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (animateur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 24. COMPTES-RENDUS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS comptes_rendus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reunion_id INTEGER NOT NULL,
        contenu TEXT,
        decisions TEXT,
        actions_suivi TEXT,
        redacteur_id INTEGER,
        date_redaction TEXT NOT NULL,
        statut TEXT DEFAULT 'Brouillon',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (reunion_id) REFERENCES reunions(id),
        FOREIGN KEY (redacteur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 25. ACHATS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS achats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        projet_id INTEGER NOT NULL,
        fournisseur_id INTEGER,
        type_achat TEXT DEFAULT 'Matériel',
        description TEXT NOT NULL,
        quantite REAL DEFAULT 1,
        unite TEXT,
        prix_unitaire REAL DEFAULT 0,
        montant_ht REAL DEFAULT 0,
        taux_tva REAL DEFAULT 18,
        montant_ttc REAL DEFAULT 0,
        date_commande TEXT,
        date_livraison_prevue TEXT,
        date_livraison_reelle TEXT,
        statut TEXT DEFAULT 'En attente',
        user_id INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id)
    )""")

    # ==================== 26. SOUS-TRAITANTS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS sous_traitants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        projet_id INTEGER NOT NULL,
        fournisseur_id INTEGER,
        nom TEXT NOT NULL,
        specialite TEXT,
        contact TEXT,
        telephone TEXT,
        date_debut TEXT,
        date_fin TEXT,
        montant_contrat REAL DEFAULT 0,
        montant_paye REAL DEFAULT 0,
        statut TEXT DEFAULT 'En cours',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id)
    )""")

    # ==================== 27. QUALITÉ ====================
    c.execute("""CREATE TABLE IF NOT EXISTS qualite (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        projet_id INTEGER NOT NULL,
        tache_id INTEGER,
        type_controle TEXT,
        reference TEXT,
        description TEXT,
        critere TEXT,
        date_controle TEXT,
        controleur_id INTEGER,
        resultat TEXT DEFAULT 'Conforme',
        non_conformites TEXT,
        actions_correctives TEXT,
        statut TEXT DEFAULT 'Ouvert',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (tache_id) REFERENCES taches(id),
        FOREIGN KEY (controleur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 28. CHANGEMENTS (Change Management) ====================
    c.execute("""CREATE TABLE IF NOT EXISTS changements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        projet_id INTEGER NOT NULL,
        type_changement TEXT DEFAULT 'Périmètre',
        titre TEXT NOT NULL,
        description TEXT,
        justification TEXT,
        impact_delai_jours INTEGER DEFAULT 0,
        impact_cout REAL DEFAULT 0,
        impact_qualite TEXT,
        impact_risques TEXT,
        demandeur_id INTEGER,
        date_demande TEXT NOT NULL,
        decision TEXT DEFAULT 'En attente',
        decide_par INTEGER,
        date_decision TEXT,
        statut TEXT DEFAULT 'En attente',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (demandeur_id) REFERENCES utilisateurs(id),
        FOREIGN KEY (decide_par) REFERENCES utilisateurs(id)
    )""")

    # ==================== 29. LEÇONS APPRISES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS lecons_apprises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projet_id INTEGER,
        phase_id INTEGER,
        categorie TEXT,
        titre TEXT NOT NULL,
        contexte TEXT,
        probleme TEXT,
        solution TEXT,
        recommandation TEXT,
        impact TEXT,
        auteur_id INTEGER,
        date_lecon TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (phase_id) REFERENCES phases(id),
        FOREIGN KEY (auteur_id) REFERENCES utilisateurs(id)
    )""")

    # ==================== 30. FEUILLE DE TEMPS ====================
    c.execute("""CREATE TABLE IF NOT EXISTS feuilles_temps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        utilisateur_id INTEGER NOT NULL,
        projet_id INTEGER NOT NULL,
        tache_id INTEGER,
        date_jour TEXT NOT NULL,
        heures REAL NOT NULL,
        description TEXT,
        statut TEXT DEFAULT 'En attente',
        valide_par INTEGER,
        date_validation TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id),
        FOREIGN KEY (projet_id) REFERENCES projets(id),
        FOREIGN KEY (tache_id) REFERENCES taches(id),
        FOREIGN KEY (valide_par) REFERENCES utilisateurs(id)
    )""")

    # ==================== 31. AUDIT LOG ====================
    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        ip TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ==================== 32. PARAMÈTRES ====================
    c.execute("""CREATE TABLE IF NOT EXISTS parametres (
        cle TEXT PRIMARY KEY,
        valeur TEXT,
        description TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()

    # ==================== SEED ====================
    c.execute("SELECT COUNT(*) FROM devises")
    if c.fetchone()[0] == 0:
        print("[INIT] Insertion des données de démonstration...")

        # DEVISES
        c.executemany("""INSERT INTO devises (code, nom, symbole, taux_fcfa, reference)
            VALUES (?, ?, ?, ?, ?)""", [
            ('FCFA', 'Franc CFA', 'FCFA', 1.0, 1),
            ('EUR', 'Euro', '€', 655.957, 0),
            ('USD', 'Dollar US', '$', 605.50, 0),
            ('GBP', 'Livre Sterling', '£', 765.00, 0),
            ('XOF', 'Franc CFA BCEAO', 'FCFA', 1.0, 0),
        ])

        # SITES (Zones UEMOA)
        c.executemany("""INSERT INTO sites (code, nom, pays, ville, zone_uemoa, telephone, responsable)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", [
            ('SITE-DK', 'Bureau Dakar', 'Sénégal', 'Dakar', 'Zone UEMOA', '+221 33 800 00 01', 'Mamadou Diallo'),
            ('SITE-AB', 'Bureau Abidjan', 'Côte d\'Ivoire', 'Abidjan', 'Zone UEMOA', '+225 27 20 00 00 02', 'Fatou Ndiaye'),
            ('SITE-BM', 'Bureau Bamako', 'Mali', 'Bamako', 'Zone UEMOA', '+223 20 00 00 03', 'Ibrahima Fall'),
            ('SITE-OU', 'Bureau Ouagadougou', 'Burkina Faso', 'Ouagadougou', 'Zone UEMOA', '+226 25 00 00 04', 'Aminata Sow'),
            ('SITE-CO', 'Bureau Cotonou', 'Bénin', 'Cotonou', 'Zone UEMOA', '+229 21 00 00 05', 'Ousmane Kane'),
            ('SITE-LO', 'Bureau Lomé', 'Togo', 'Lomé', 'Zone UEMOA', '+228 22 00 00 06', 'Aissatou Ba'),
            ('SITE-NI', 'Bureau Niamey', 'Niger', 'Niamey', 'Zone UEMOA', '+227 20 00 00 07', 'Moussa Traoré'),
        ])

        # CLIENTS
        c.executemany("""INSERT INTO clients
            (code, type_client, nom, contact_nom, telephone, email, ville, pays, nif, secteur, conditions_paiement)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('CLI-001', 'Entreprise', 'Sonatel SA', 'M. Diop', '+221 33 839 00 00', 'contact@sonatel.sn', 'Dakar', 'Sénégal', 'SN-001234567', 'Télécoms', '30% acompte + 60j'),
            ('CLI-002', 'Entreprise', 'Sénégalaise des Eaux', 'Mme Fall', '+221 33 839 11 11', 'contact@sde.sn', 'Dakar', 'Sénégal', 'SN-002345678', 'Eau/Assainissement', '30j'),
            ('CLI-003', 'Ministère', 'Ministère Infrastructures Sénégal', 'M. Ndiaye', '+221 33 839 22 22', 'contact@infra.gouv.sn', 'Dakar', 'Sénégal', 'SN-003456789', 'Public', '45j'),
            ('CLI-004', 'Entreprise', 'Côte d\'Ivoire Énergie', 'M. Kouassi', '+225 27 20 30 40 50', 'contact@ci-energie.ci', 'Abidjan', 'Côte d\'Ivoire', 'CI-100234567', 'Énergie', '60j'),
            ('CLI-005', 'Banque', 'BOAD', 'M. Togo', '+228 22 23 24 25', 'contact@boad.org', 'Lomé', 'Togo', 'TG-500345678', 'Finance', '30j'),
            ('CLI-006', 'Entreprise', 'Orange Mali', 'Mme Traoré', '+223 20 70 00 00', 'contact@orange.ml', 'Bamako', 'Mali', 'ML-200456789', 'Télécoms', '45j'),
            ('CLI-007', 'ONG', 'USAID Sénégal', 'M. Smith', '+221 33 869 00 00', 'contact@usaid.gov', 'Dakar', 'Sénégal', 'SN-007567890', 'Développement', '15j'),
            ('CLI-008', 'Entreprise', 'Société Nationale d\'Électricité', 'M. Sow', '+226 25 30 00 00', 'contact@sonabel.bf', 'Ouagadougou', 'Burkina Faso', 'BF-300567890', 'Énergie', '60j'),
        ])

        # FOURNISSEURS
        c.executemany("""INSERT INTO fournisseurs
            (code, nom, contact, telephone, email, pays, specialite, note_qualite)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('FRN-001', 'Sénégal Matériaux BTP', 'M. Ba', '+221 33 800 11 11', 'contact@sm-btp.sn', 'Sénégal', 'Matériaux construction', 4.5),
            ('FRN-002', 'Ivoirienne Équipements', 'M. Kouadio', '+225 27 21 22 23 24', 'contact@iv-equip.ci', 'Côte d\'Ivoire', 'Équipements industriels', 4.2),
            ('FRN-003', 'Sahel Informatique', 'M. Touré', '+223 20 22 23 24', 'contact@sahel-info.ml', 'Mali', 'IT & réseaux', 4.0),
            ('FRN-004', 'Burkina Logistique', 'M. Sawadogo', '+226 25 36 37 38', 'contact@bf-log.bf', 'Burkina Faso', 'Transport & logistique', 3.8),
            ('FRN-005', 'Togolaise Énergie Solaire', 'Mme Adjovi', '+228 22 30 31 32', 'contact@te-solar.tg', 'Togo', 'Solaire & énergie', 4.7),
            ('FRN-006', 'Bénin Câblage Pro', 'M. Houngbédji', '+229 21 30 31 32', 'contact@bcp.bj', 'Bénin', 'Câblage électrique', 4.3),
        ])

        # PORTEFEUILLE
        c.executemany("""INSERT INTO portefeuilles (code, nom, description, budget_total, devise, date_debut, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", [
            ('PORT-INFRA', 'Portefeuille Infrastructures', 'Projets BTP et infrastructures UEMOA', 25000000000, 'FCFA', '2024-01-01', 'Actif'),
            ('PORT-DIG', 'Portefeuille Digital & IT', 'Projets transformation digitale', 8500000000, 'FCFA', '2024-01-01', 'Actif'),
            ('PORT-ENER', 'Portefeuille Énergie', 'Projets énergie & solaire', 12000000000, 'FCFA', '2024-06-01', 'Actif'),
        ])

        # PROGRAMMES
        c.executemany("""INSERT INTO programmes
            (code, nom, description, portefeuille_id, budget_total, devise, date_debut, date_fin, objectif_strategique)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('PROG-ROUTES', 'Programme Routes UEMOA', 'Modernisation réseaux routiers', 1, 8000000000, 'FCFA', '2024-01-01', '2027-12-31', 'Connexion inter-états'),
            ('PROG-EAU', 'Programme Eau Potable', 'Accès eau potable zones rurales', 1, 5000000000, 'FCFA', '2024-03-01', '2027-06-30', 'ODD 6 - Eau'),
            ('PROG-FIBRE', 'Programme Fibre Optique UEMOA', 'Déploiement backbone fibre', 2, 6000000000, 'FCFA', '2024-01-01', '2026-12-31', 'Souveraineté numérique'),
            ('PROG-SOLAIRE', 'Programme Solaire UEMOA', 'Centrales solaires 500MW', 3, 10000000000, 'FCFA', '2024-06-01', '2028-12-31', 'Transition énergétique'),
        ])

        # PROJETS (8 projets multi-pays)
        projets = [
            # Programmes Infra
            ('PRJ-001', 'Autoroute Dakar-Thiès', 'Élargissement et modernisation', 1, 3, 1, 1,
             'Construction', 'Waterfall', 'Critique', 'Élevée',
             '2024-03-01', '2026-06-30', 850, 3500000000, 'FCFA', 25, 35, 'En cours', 'Vert'),
            ('PRJ-002', 'Station traitement eau Saint-Louis', 'Construction STEP 50 000 m³/j', 2, 2, 2, 1,
             'Construction', 'Waterfall', 'Haute', 'Élevée',
             '2024-05-01', '2026-03-31', 700, 1800000000, 'FCFA', 22, 28, 'En cours', 'Vert'),
            ('PRJ-003', 'Pont Abidjan-Bassam', 'Pont 2 voies + voies ferrées', 1, 4, 1, 2,
             'Construction', 'Hybride', 'Critique', 'Très élevée',
             '2024-09-01', '2027-12-31', 1200, 5500000000, 'FCFA', 20, 15, 'En cours', 'Jaune'),

            # Programmes Digital
            ('PRJ-004', 'Backbone fibre Abidjan-Ouaga', 'Déploiement 1500 km fibre', 3, 4, 3, 2,
             'IT/Télécoms', 'Agile', 'Haute', 'Élevée',
             '2024-06-01', '2026-09-30', 850, 2800000000, 'FCFA', 30, 45, 'En cours', 'Vert'),
            ('PRJ-005', 'Cloud souverain UEMOA', 'Datacenter Tier III Dakar', 3, 1, 3, 1,
             'IT/Digital', 'Hybride', 'Haute', 'Moyenne',
             '2025-01-01', '2026-06-30', 550, 1500000000, 'FCFA', 35, 20, 'En cours', 'Vert'),
            ('PRJ-006', 'ERP Santé Mali', 'Système information hospitalier', 3, 6, 3, 3,
             'IT/Digital', 'Agile', 'Normale', 'Moyenne',
             '2025-02-01', '2026-01-31', 365, 480000000, 'FCFA', 40, 30, 'En cours', 'Vert'),

            # Programmes Énergie
            ('PRJ-007', 'Centrale solaire Touba', '50 MW solaire + stockage', 4, 2, 3, 1,
             'Énergie', 'Waterfall', 'Critique', 'Élevée',
             '2024-08-01', '2026-12-31', 880, 2200000000, 'FCFA', 28, 40, 'En cours', 'Vert'),
            ('PRJ-008', 'Réseau solaire rural Niger', '500 mini-centrales solaires', 4, 7, 3, 7,
             'Énergie', 'Hybride', 'Haute', 'Moyenne',
             '2025-03-01', '2027-06-30', 850, 1200000000, 'FCFA', 25, 10, 'En cours', 'Vert'),
        ]
        c.executemany("""INSERT INTO projets
            (code, nom, description, programme_id, client_id, chef_projet_id, site_id,
             type_projet, methodologie, priorite, complexite,
             date_debut_prevue, date_fin_prevue, duree_jours, budget_prevu,
             devise, marge_cible, avancement_pct, statut, sante_projet)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", projets)

        # ÉQUIPES PROJETS
        c.executemany("""INSERT INTO projet_equipe
            (projet_id, utilisateur_id, role_projet, date_affectation, taux_horaire)
            VALUES (?, ?, ?, ?, ?)""", [
            (1, 3, 'Chef de projet', '2024-03-01', 18000),
            (1, 4, 'Chef de chantier', '2024-03-15', 15000),
            (1, 5, 'Ingénieur travaux', '2024-03-15', 12000),
            (2, 3, 'Chef de projet', '2024-05-01', 18000),
            (3, 3, 'Chef de projet', '2024-09-01', 20000),
            (4, 3, 'Chef de projet', '2024-06-01', 20000),
            (4, 5, 'Ingénieur DevOps', '2024-06-15', 18000),
            (5, 3, 'Chef de projet', '2025-01-01', 20000),
            (6, 3, 'Chef de projet', '2025-02-01', 18000),
            (7, 3, 'Chef de projet', '2024-08-01', 20000),
            (7, 4, 'Chef de chantier', '2024-08-15', 15000),
            (8, 3, 'Chef de projet', '2025-03-01', 18000),
        ])

        # PHASES PROJET 1 (Autoroute)
        c.executemany("""INSERT INTO phases
            (projet_id, code, nom, ordre, date_debut, date_fin, budget_alloue, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [
            (1, 'PH-01', 'Études préliminaires', 1, '2024-03-01', '2024-08-31', 250000000, 'Terminée'),
            (1, 'PH-02', 'Terrassement', 2, '2024-09-01', '2025-06-30', 800000000, 'En cours'),
            (1, 'PH-03', 'Chaussée & revêtement', 3, '2025-07-01', '2026-02-28', 1500000000, 'À venir'),
            (1, 'PH-04', 'Signalisation & finitions', 4, '2026-03-01', '2026-06-30', 600000000, 'À venir'),
            (1, 'PH-05', 'Réception & livraison', 5, '2026-05-01', '2026-06-30', 100000000, 'À venir'),
        ])

        # TÂCHES PROJET 1 (WBS)
        taches = [
            ('T-001-01', 1, 1, '1', 1, None, 'Étude géotechnique', 'Tâche', 3, '2024-03-01', '2024-04-15', 320, 0, 'Terminée', 0),
            ('T-001-02', 1, 1, '2', 1, None, 'Étude hydraulique', 'Tâche', 3, '2024-04-01', '2024-05-31', 280, 0, 'Terminée', 0),
            ('T-001-03', 1, 1, '3', 1, None, 'Étude d\'impact environnemental', 'Tâche', 3, '2024-05-01', '2024-07-31', 400, 0, 'Terminée', 1),
            ('T-001-04', 1, 1, '4', 1, None, 'Conception détaillée', 'Tâche', 3, '2024-06-01', '2024-08-31', 500, 0, 'Terminée', 1),
            ('T-001-05', 1, 2, '1.1', 2, None, 'Défrichage', 'Tâche', 4, '2024-09-01', '2024-10-31', 400, 0, 'Terminée', 0),
            ('T-001-06', 1, 2, '1.2', 2, None, 'Terrassement général', 'Tâche', 4, '2024-10-15', '2025-03-31', 1200, 0, 'En cours', 1),
            ('T-001-07', 1, 2, '1.3', 2, None, 'Ouvrages d\'art', 'Tâche', 4, '2025-01-01', '2025-06-30', 800, 0, 'En cours', 1),
            ('T-001-08', 1, 3, '2.1', 2, None, 'Couche de base', 'Tâche', 4, '2025-07-01', '2025-11-30', 600, 0, 'À faire', 0),
            ('T-001-09', 1, 3, '2.2', 2, None, 'Revêtement bitumineux', 'Tâche', 4, '2025-10-01', '2026-02-28', 800, 0, 'À faire', 1),
        ]
        for t in taches:
            c.execute("""INSERT INTO taches
                (code, projet_id, phase_id, wbs_code, wbs_niveau, parent_id, nom, type_tache,
                 responsable_id, date_debut_prevue, date_fin_prevue, effort_estime,
                 effort_consomme, statut, chemin_critique)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", t)

        # JALONS PROJET 1
        c.executemany("""INSERT INTO jalons (projet_id, code, nom, date_prevue, statut)
            VALUES (?, ?, ?, ?, ?)""", [
            (1, 'JAL-01', 'Études approuvées', '2024-08-31', 'Atteint'),
            (1, 'JAL-02', 'Fin terrassement', '2025-06-30', 'En cours'),
            (1, 'JAL-03', 'Fin chaussée', '2026-02-28', 'À venir'),
            (1, 'JAL-04', 'Réception provisoire', '2026-06-30', 'À venir'),
        ])

        # RISQUES
        c.executemany("""INSERT INTO risques
            (code, projet_id, titre, description, categorie, type_risque,
             probabilite, impact, criticite, niveau_risque,
             date_identification, strategie, plan_mitigation, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('RSK-001', 1, 'Retard livraison matériaux', 'Approvisionnement bitume retardé', 'Approvisionnement', 'Menace',
             4, 4, 16, 'Critique', datetime.now().isoformat(), 'Réduire',
             'Diversifier fournisseurs + stock tampon 15 jours', 'Ouvert'),
            ('RSK-002', 1, 'Intempéries saison pluies', 'Arrêt chantier juillet-septembre', 'Naturel', 'Menace',
             5, 3, 15, 'Élevé', datetime.now().isoformat(), 'Réduire',
             'Planification travaux hors saison + bâches', 'Ouvert'),
            ('RSK-003', 1, 'Conflit riverains', 'Opposition expropriation', 'Social', 'Menace',
             3, 4, 12, 'Élevé', datetime.now().isoformat(), 'Réduire',
             'Dialogue communautaire + indemnisations', 'Ouvert'),
            ('RSK-004', 4, 'Pénurie fibre optique', 'Fournisseur principal en rupture', 'Approvisionnement', 'Menace',
             3, 5, 15, 'Élevé', datetime.now().isoformat(), 'Transférer',
             'Contrats multi-fournisseurs + import', 'Ouvert'),
            ('RSK-005', 7, 'Retard autorisation', 'Permis environnemental', 'Réglementaire', 'Menace',
             4, 4, 16, 'Critique', datetime.now().isoformat(), 'Réduire',
             'Dossier complet + suivi hebdomadaire', 'Ouvert'),
        ])

        # ACTIONS
        c.executemany("""INSERT INTO actions
            (code, projet_id, risque_id, titre, description, responsable_id, date_echeance, priorite, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('ACT-001', 1, 1, 'Identifier 3 fournisseurs bitume', 'Contacter fournisseurs EU + Afrique', 3, '2024-04-30', 'Haute', 'En cours'),
            ('ACT-002', 1, 2, 'Établir plan saison pluies', 'Replanifier travaux critiques', 3, '2024-05-15', 'Haute', 'À faire'),
            ('ACT-003', 1, 3, 'Réunion riverains', 'Organiser consultation', 4, '2024-04-15', 'Normale', 'Terminée'),
        ])

        # BUDGET LIGNES
        c.executemany("""INSERT INTO budget_lignes
            (projet_id, phase_id, code, designation, categorie, quantite, unite, prix_unitaire, montant_prevu)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            (1, 2, 'BL-001', 'Terrassement (m³)', 'Travaux', 500000, 'm³', 1500, 750000000),
            (1, 2, 'BL-002', 'Ouvrages d\'art', 'Travaux', 1, 'forfait', 50000000, 50000000),
            (1, 3, 'BL-003', 'Bitume (tonnes)', 'Matériaux', 15000, 't', 80000, 1200000000),
            (1, 3, 'BL-004', 'Granulats (m³)', 'Matériaux', 100000, 'm³', 3000, 300000000),
        ])

        # ENGAGEMENTS
        c.executemany("""INSERT INTO engagements
            (numero, projet_id, fournisseur_id, type_engagement, date_engagement, montant, statut, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('ENG-2026-0001', 1, 1, 'Commande', '2024-09-01', 450000000, 'En cours', 'Fourniture granulats phase 2'),
            ('ENG-2026-0002', 1, 5, 'Contrat', '2024-10-15', 85000000, 'En cours', 'Maintenance équipements'),
            ('ENG-2026-0003', 4, 3, 'Commande', '2024-06-15', 680000000, 'Livré', 'Câble fibre optique 1500km'),
        ])

        # FACTURES CLIENTS
        c.executemany("""INSERT INTO factures_client
            (numero, projet_id, client_id, date_facture, date_echeance, type_facture,
             montant_ht, montant_tva, montant_ttc, montant_paye, solde, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('FAC-2026-0001', 1, 3, '2024-09-30', '2024-11-14', 'Situation',
             350000000, 63000000, 413000000, 413000000, 0, 'Payé'),
            ('FAC-2026-0002', 1, 3, '2025-01-15', '2025-03-01', 'Situation',
             280000000, 50400000, 330400000, 165200000, 165200000, 'Partiel'),
            ('FAC-2026-0003', 4, 1, '2024-10-31', '2024-11-30', 'Situation',
             420000000, 75600000, 495600000, 0, 495600000, 'Impayé'),
            ('FAC-2026-0004', 2, 2, '2024-12-15', '2025-01-14', 'Situation',
             180000000, 32400000, 212400000, 212400000, 0, 'Payé'),
        ])

        # PAIEMENTS
        c.executemany("""INSERT INTO paiements
            (numero, facture_id, projet_id, type_paiement, date_paiement, montant, mode_paiement, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('PAY-2026-0001', 1, 1, 'Encaissement', '2024-10-15', 413000000, 'Virement', 'Validé'),
            ('PAY-2026-0002', 2, 1, 'Encaissement', '2025-02-01', 165200000, 'Virement', 'Validé'),
            ('PAY-2026-0003', 4, 2, 'Encaissement', '2024-12-20', 212400000, 'Chèque', 'Validé'),
        ])

        # EVM (mesure pour projet 1)
        c.executemany("""INSERT INTO evm
            (projet_id, date_mesure, pv, ev, ac, bac, sv, cv, spi, cpi, eac, etc, vac, tcpi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            (1, '2024-12-31', 850000000, 780000000, 920000000, 3500000000,
             -70000000, -140000000, 0.92, 0.85, 4127000000, 3207000000, -627000000, 1.18),
            (1, '2025-03-31', 1450000000, 1320000000, 1580000000, 3500000000,
             -130000000, -260000000, 0.91, 0.84, 4193000000, 2613000000, -693000000, 1.20),
        ])

        # PARAMÈTRES
        c.executemany("INSERT INTO parametres (cle, valeur, description) VALUES (?, ?, ?)", [
            ('entreprise_nom', 'OMEGA PROJETS', 'Nom de l\'entreprise'),
            ('entreprise_nif', 'SN-123456789', 'NIF'),
            ('devise_defaut', 'FCFA', 'Devise par défaut'),
            ('tva_defaut', '18', 'TVA UEMOA (%)'),
            ('norme', 'ISO 21500 / PMI / PRINCE2', 'Normes appliquées'),
            ('seuil_alerte_delai', '10', 'Alerte retard en %'),
            ('seuil_alerte_budget', '5', 'Alerte dépassement budget en %'),
        ])

        conn.commit()
        print("[INIT] ✅ Données de démonstration insérées")

    conn.close()
    print("[INIT] ✅ Base de données Projets prête")


if __name__ == "__main__":
    init_db()
