#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Migration OMEGA PARTS — Module Services Automobiles
Ajoute les tables : services, interventions, diagnostic, formation, suivi
"""
import sqlite3
from datetime import datetime

DB_PATH = '/app/data/parts.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("═" * 50)
    print("🔧 MIGRATION SERVICES OMEGA PARTS")
    print("═" * 50)
    print()

    # ═══════════════════════════════════════════════════════════
    # 1. SERVICES (types de prestations)
    # ═══════════════════════════════════════════════════════════
    cur.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            categorie TEXT,
            description TEXT,
            duree_min INTEGER DEFAULT 30,
            prix_min REAL DEFAULT 0,
            prix_max REAL DEFAULT 0,
            icone TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)
    print("  ✅ Table services")

    # ═══════════════════════════════════════════════════════════
    # 2. INTERVENTIONS (ordres de réparation)
    # ═══════════════════════════════════════════════════════════
    cur.execute("""
        CREATE TABLE IF NOT EXISTS interventions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            vehicule_id INTEGER,
            client_id INTEGER,
            service_id INTEGER,
            mecanicien_id INTEGER,
            date_debut TEXT,
            date_fin_prevue TEXT,
            date_fin_reelle TEXT,
            kilometrage INTEGER,
            description TEXT,
            diagnostic TEXT,
            travaux_realises TEXT,
            statut TEXT DEFAULT 'en_attente',
            priorite TEXT DEFAULT 'normale',
            prix_main_oeuvre REAL DEFAULT 0,
            prix_pieces REAL DEFAULT 0,
            prix_total REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id),
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(service_id) REFERENCES services(id),
            FOREIGN KEY(mecanicien_id) REFERENCES users(id)
        )
    """)
    print("  ✅ Table interventions")

    # ═══════════════════════════════════════════════════════════
    # 3. INTERVENTION PIÈCES (pièces utilisées)
    # ═══════════════════════════════════════════════════════════
    cur.execute("""
        CREATE TABLE IF NOT EXISTS intervention_pieces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intervention_id INTEGER NOT NULL,
            piece_id INTEGER NOT NULL,
            quantite INTEGER DEFAULT 1,
            prix_unitaire REAL DEFAULT 0,
            montant REAL DEFAULT 0,
            FOREIGN KEY(intervention_id) REFERENCES interventions(id),
            FOREIGN KEY(piece_id) REFERENCES pieces(id)
        )
    """)
    print("  ✅ Table intervention_pieces")

    # ═══════════════════════════════════════════════════════════
    # 4. LAVAGE (formules et prestations)
    # ═══════════════════════════════════════════════════════════
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lavage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            vehicule_id INTEGER,
            client_id INTEGER,
            formule TEXT,
            description TEXT,
            prix REAL DEFAULT 0,
            date_debut TEXT,
            date_fin TEXT,
            statut TEXT DEFAULT 'en_attente',
            agent_id INTEGER,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id),
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(agent_id) REFERENCES users(id)
        )
    """)
    print("  ✅ Table lavage")

    # ═══════════════════════════════════════════════════════════
    # 5. DIAGNOSTIC (rapports)
    # ═══════════════════════════════════════════════════════════
    cur.execute("""
        CREATE TABLE IF NOT EXISTS diagnostics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            vehicule_id INTEGER,
            client_id INTEGER,
            technicien_id INTEGER,
            type_diag TEXT,
            date_diag TEXT,
            kilometrage INTEGER,
            symptomes TEXT,
            code_erreur TEXT,
            resultat TEXT,
            recommandations TEXT,
            cout REAL DEFAULT 0,
            rapport_path TEXT,
            created_at TEXT,
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id),
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(technicien_id) REFERENCES users(id)
        )
    """)
    print("  ✅ Table diagnostics")

    # ═══════════════════════════════════════════════════════════
    # 6. FICHES TECHNIQUES
    # ═══════════════════════════════════════════════════════════
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fiches_techniques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marque_id INTEGER,
            modele_id INTEGER,
            annee INTEGER,
            titre TEXT NOT NULL,
            type_fiche TEXT,
            contenu TEXT,
            fichier_path TEXT,
            auteur TEXT,
            version TEXT,
            created_at TEXT,
            FOREIGN KEY(marque_id) REFERENCES vehicules_marques(id),
            FOREIGN KEY(modele_id) REFERENCES vehicules_modeles(id)
        )
    """)
    print("  ✅ Table fiches_techniques")

    # ═══════════════════════════════════════════════════════════
    # 7. PROCÉDURES DE DÉPANNAGE
    # ═══════════════════════════════════════════════════════════
    cur.execute("""
        CREATE TABLE IF NOT EXISTS procedures_depannage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            titre TEXT NOT NULL,
            categorie TEXT,
            niveau TEXT,
            symptomes TEXT,
            etapes TEXT,
            outils_requis TEXT,
            duree_estimee INTEGER,
            difficulte INTEGER DEFAULT 3,
            created_at TEXT
        )
    """)
    print("  ✅ Table procedures_depannage")

    # ═══════════════════════════════════════════════════════════
    # 8. FORMATION APPRENTIS
    # ═══════════════════════════════════════════════════════════
    cur.execute("""
        CREATE TABLE IF NOT EXISTS formation_modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            titre TEXT NOT NULL,
            niveau TEXT,
            categorie TEXT,
            description TEXT,
            duree_heures INTEGER,
            contenu TEXT,
            prerequis TEXT,
            ordre INTEGER DEFAULT 0,
            actif INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)
    print("  ✅ Table formation_modules")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS formation_apprentis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            prenom TEXT,
            telephone TEXT,
            email TEXT,
            age INTEGER,
            niveau_etude TEXT,
            date_inscription TEXT,
            statut TEXT DEFAULT 'en_cours',
            progression INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT
        )
    """)
    print("  ✅ Table formation_apprentis")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS formation_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apprenti_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            date_evaluation TEXT,
            note REAL DEFAULT 0,
            observation TEXT,
            evaluateur_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(apprenti_id) REFERENCES formation_apprentis(id),
            FOREIGN KEY(module_id) REFERENCES formation_modules(id),
            FOREIGN KEY(evaluateur_id) REFERENCES users(id)
        )
    """)
    print("  ✅ Table formation_evaluations")

    # ═══════════════════════════════════════════════════════════
    # 9. SUIVI VÉHICULE (carnet numérique)
    # ═══════════════════════════════════════════════════════════
    cur.execute("""
        CREATE TABLE IF NOT EXISTS suivi_vehicule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicule_id INTEGER NOT NULL,
            type_evenement TEXT,
            reference_id INTEGER,
            date_evenement TEXT,
            kilometrage INTEGER,
            description TEXT,
            cout REAL DEFAULT 0,
            garage TEXT,
            created_at TEXT,
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id)
        )
    """)
    print("  ✅ Table suivi_vehicule")

    # ═══════════════════════════════════════════════════════════
    # 10. DÉPENSES / RECETTES PAR SERVICE
    # ═══════════════════════════════════════════════════════════
    cur.execute("""
        CREATE TABLE IF NOT EXISTS service_finances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id INTEGER,
            type_operation TEXT,
            categorie TEXT,
            libelle TEXT,
            montant REAL DEFAULT 0,
            reference TEXT,
            date_operation TEXT,
            user_id INTEGER,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(service_id) REFERENCES services(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    print("  ✅ Table service_finances")

    # ═══════════════════════════════════════════════════════════
    # 11. BACKUP PARTS
    # ═══════════════════════════════════════════════════════════
    cur.execute("""
        CREATE TABLE IF NOT EXISTS backup_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            fichier TEXT,
            taille_mb REAL,
            description TEXT,
            user_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    print("  ✅ Table backup_history")

    # ─── Peupler avec services par défaut ───
    cur.execute("SELECT COUNT(*) FROM services")
    if cur.fetchone()[0] == 0:
        services = [
            ('VIDANGE', 'Vidange moteur', 'entretien', 'Vidange huile + filtre', 45, 15000, 45000, '🛢️'),
            ('REVISION', 'Révision complète', 'entretien', 'Révision périodique', 120, 50000, 150000, '🔧'),
            ('FREIN', 'Réparation freinage', 'reparation', 'Plaquettes, disques, étriers', 90, 30000, 200000, '🛑'),
            ('EMBRAYAGE', 'Réparation embrayage', 'reparation', 'Remplacement embrayage', 300, 200000, 500000, '⚙️'),
            ('DIAG_ELEC', 'Diagnostic électronique', 'diagnostic', 'Diagnostic OBD + codes', 30, 10000, 30000, '🔍'),
            ('DIAG_MECA', 'Diagnostic mécanique', 'diagnostic', 'Contrôle mécanique complet', 60, 20000, 50000, '🔧'),
            ('CLIM', 'Réparation climatisation', 'reparation', 'Recharge + réparation clim', 90, 35000, 250000, '❄️'),
            ('DISTRIBUTION', 'Courroie de distribution', 'reparation', 'Remplacement kit distribution', 240, 150000, 400000, '⛓️'),
            ('LAVAGE_BASIC', 'Lavage Basic', 'lavage', 'Extérieur + intérieur simple', 30, 3000, 5000, '🚿'),
            ('LAVAGE_PREMIUM', 'Lavage Premium', 'lavage', 'Extérieur + intérieur détaillé', 60, 7000, 12000, '✨'),
            ('LAVAGE_VIP', 'Lavage VIP', 'lavage', 'Lavage + polish + cire', 120, 15000, 25000, '💎'),
            ('PNEU', 'Montage pneumatiques', 'entretien', 'Montage/équilibrage pneus', 45, 5000, 15000, '⭕'),
            ('BATTERIE', 'Remplacement batterie', 'entretien', 'Test + remplacement', 30, 8000, 20000, '🔋'),
            ('CARROSSERIE', 'Réparation carrosserie', 'reparation', 'Débosselage + peinture', 480, 100000, 800000, '🎨'),
            ('PEINTURE', 'Peinture complète', 'reparation', 'Peinture véhicule complet', 720, 300000, 1500000, '🎨'),
        ]
        for s in services:
            cur.execute("""
                INSERT INTO services (code, nom, categorie, description, duree_min,
                    prix_min, prix_max, icone, actif, created_at)
                VALUES (?,?,?,?,?,?,?,?,1,?)
            """, (*s, datetime.now().isoformat()))
        print(f"  ✅ {len(services)} services créés")

    # ─── Peupler procédures de dépannage ───
    cur.execute("SELECT COUNT(*) FROM procedures_depannage")
    if cur.fetchone()[0] == 0:
        procedures = [
            ('PROC001', 'Moteur ne démarre pas', 'moteur', 'debutant',
             'Le moteur tourne mais ne démarre pas',
             '1. Vérifier la batterie\n2. Vérifier le carburant\n3. Vérifier les fusibles\n4. Tester la pompe à carburant\n5. Vérifier l\'allumage',
             'Multimètre, tournevis, clé à bougie', 60, 2),
            ('PROC002', 'Surchauffe moteur', 'moteur', 'intermediaire',
             'Température élevée, fumée blanche',
             '1. Arrêter immédiatement le moteur\n2. Vérifier niveau liquide refroidissement\n3. Vérifier durites et radiateur\n4. Tester thermostat\n5. Vérifier la pompe à eau',
             'Gants, clé à pipe, tournevis', 90, 3),
            ('PROC003', 'Freins qui grincent', 'freinage', 'debutant',
             'Bruit métallique au freinage',
             '1. Vérifier plaquettes\n2. Vérifier disques\n3. Nettoyer étriers\n4. Remplacer si nécessaire\n5. Tester sur route',
             'Cric, clé à chocs, plaquettes neuves', 60, 1),
            ('PROC004', 'Batterie déchargée', 'electricite', 'debutant',
             'Véhicule ne démarre pas, phares faibles',
             '1. Tester la tension (12.6V)\n2. Vérifier les cosses\n3. Tester l\'alternateur\n4. Vérifier les fusibles\n5. Remplacer si nécessaire',
             'Multimètre, clé à cosse', 30, 1),
            ('PROC005', 'Climatisation ne refroidit pas', 'clim', 'intermediaire',
             'Air tiède au lieu de froid',
             '1. Vérifier le gaz\n2. Tester le compresseur\n3. Vérifier le condensateur\n4. Détecter les fuites\n5. Recharger',
             'Manomètres clim, détecteur de fuite', 90, 3),
            ('PROC006', 'Vibration au volant', 'suspension', 'intermediaire',
             'Vibrations à vitesse élevée',
             '1. Vérifier équilibrage pneus\n2. Contrôler rotules\n3. Vérifier amortisseurs\n4. Contrôler cardan\n5. Tester sur route',
             'Pont élévateur, équilibreuse', 120, 3),
        ]
        for p in procedures:
            cur.execute("""
                INSERT INTO procedures_depannage (code, titre, categorie, niveau,
                    symptomes, etapes, outils_requis, duree_estimee, difficulte, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (*p, datetime.now().isoformat()))
        print(f"  ✅ {len(procedures)} procédures créées")

    # ─── Peupler modules formation ───
    cur.execute("SELECT COUNT(*) FROM formation_modules")
    if cur.fetchone()[0] == 0:
        modules = [
            ('MOD01', 'Introduction à la mécanique', 'debutant', 'bases',
             'Découverte du métier de mécanicien automobile',
             20, 'Sécurité, outils, vocabulaire technique', None, 1),
            ('MOD02', 'Moteur thermique', 'debutant', 'moteur',
             'Comprendre le fonctionnement du moteur',
             40, 'Cycles, composants, entretien de base', 'MOD01', 2),
            ('MOD03', 'Système de freinage', 'intermediaire', 'freinage',
             'Diagnostic et réparation du freinage',
             30, 'Plaquettes, disques, étriers, purge', 'MOD01', 3),
            ('MOD04', 'Électricité automobile', 'intermediaire', 'electricite',
             'Bases de l\'électricité auto et diagnostic',
             40, 'Batterie, alternateur, démarreur, fusibles', 'MOD01', 4),
            ('MOD05', 'Diagnostic électronique', 'avance', 'diagnostic',
             'Utilisation des outils de diagnostic OBD',
             30, 'Lecture codes, interprétation, effacement', 'MOD04', 5),
            ('MOD06', 'Climatisation automobile', 'avance', 'clim',
             'Entretien et réparation de la clim',
             25, 'Recharge, détection fuites, compresseur', 'MOD04', 6),
            ('MOD07', 'Transmission et embrayage', 'avance', 'transmission',
             'Intervention sur transmission',
             35, 'Embrayage, boîte, cardans', 'MOD02', 7),
            ('MOD08', 'Diagnostic pannes complexes', 'expert', 'diagnostic',
             'Méthodologie de diagnostic avancé',
             40, 'Arbres de diagnostic, cas pratiques', 'MOD05', 8),
        ]
        for m in modules:
            cur.execute("""
                INSERT INTO formation_modules (code, titre, niveau, categorie,
                    description, duree_heures, contenu, prerequis, ordre, actif, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,1,?)
            """, (*m, datetime.now().isoformat()))
        print(f"  ✅ {len(modules)} modules de formation créés")

    conn.commit()
    conn.close()

    print()
    print("═" * 50)
    print("✅ MIGRATION TERMINÉE")
    print("═" * 50)

if __name__ == '__main__':
    migrate()
