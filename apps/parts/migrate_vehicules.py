#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migration : Module VÉHICULES + FICHES + HISTORIQUE SAV"""
import sqlite3

DB_PATH = '/app/data/parts.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    print("═" * 55)
    print("🚗 MIGRATION — VÉHICULES & SUIVI SAV")
    print("═" * 55)

    # 1. VEHICULES
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            client_id INTEGER,
            immatriculation TEXT UNIQUE NOT NULL,
            vin_chassis TEXT,
            marque TEXT, modele TEXT, version TEXT, annee INTEGER,
            carburant TEXT, transmission TEXT, couleur TEXT,
            kilometrage INTEGER DEFAULT 0,
            nb_portes INTEGER DEFAULT 4, nb_places INTEGER DEFAULT 5,
            puissance_ch INTEGER DEFAULT 0, cylindree_cm3 INTEGER DEFAULT 0,
            date_mise_en_circulation TEXT, date_achat TEXT,
            numero_carte_grise TEXT,
            assurance_compagnie TEXT, assurance_police TEXT, assurance_expiration TEXT,
            visite_technique_expiration TEXT,
            photo_principale TEXT, notes TEXT,
            statut TEXT DEFAULT 'actif',
            created_at TEXT, updated_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    """)
    print("  ✅ vehicules")

    # 2. VEHICULE_FICHES
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicule_fiches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicule_id INTEGER NOT NULL,
            type_fiche TEXT, titre TEXT NOT NULL,
            contenu TEXT, observations TEXT, recommandations TEXT,
            auteur_id INTEGER, priorite TEXT DEFAULT 'normale',
            date_fiche TEXT, created_at TEXT,
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id),
            FOREIGN KEY(auteur_id) REFERENCES users(id)
        )
    """)
    print("  ✅ vehicule_fiches")

    # 3. VEHICULE_HISTORIQUE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicule_historique (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicule_id INTEGER NOT NULL,
            type_evenement TEXT,
            reference_id INTEGER, reference_numero TEXT,
            intervenant_id INTEGER, kilometrage INTEGER,
            description TEXT, travaux TEXT, pieces_utilisees TEXT,
            cout_total REAL DEFAULT 0,
            date_evenement TEXT, created_at TEXT,
            FOREIGN KEY(vehicule_id) REFERENCES vehicules(id),
            FOREIGN KEY(intervenant_id) REFERENCES users(id)
        )
    """)
    print("  ✅ vehicule_historique")

    # 4. Colonnes vehicule_id sur tables existantes
    for table in ('interventions', 'lavage', 'diagnostics'):
        try:
            cur.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in cur.fetchall()]
            if 'vehicule_id' not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN vehicule_id INTEGER")
                print(f"  ✅ {table}.vehicule_id ajoutée")
            else:
                print(f"  ℹ️  {table}.vehicule_id existe déjà")
        except Exception as e:
            print(f"  ⚠️  {table}: {e}")

    # 5. Trigger code auto
    cur.execute("DROP TRIGGER IF EXISTS trg_vehicule_code")
    cur.execute("""
        CREATE TRIGGER trg_vehicule_code
        AFTER INSERT ON vehicules
        FOR EACH ROW
        WHEN NEW.code IS NULL OR NEW.code = ''
        BEGIN
            UPDATE vehicules SET code = 'VHC-' || substr('00000' || NEW.id, -5)
            WHERE id = NEW.id;
        END
    """)
    print("  ✅ Trigger trg_vehicule_code")

    # 6. Index
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_vehicules_client ON vehicules(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_vehicules_immat ON vehicules(immatriculation)",
        "CREATE INDEX IF NOT EXISTS idx_hist_vehicule ON vehicule_historique(vehicule_id)",
        "CREATE INDEX IF NOT EXISTS idx_fiches_vehicule ON vehicule_fiches(vehicule_id)",
    ]:
        cur.execute(idx)
    print("  ✅ Index créés")

    conn.commit()

    # Résumé
    print()
    print("📊 RÉSUMÉ :")
    for t in ('vehicules', 'vehicule_fiches', 'vehicule_historique'):
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t:25} : {cur.fetchone()[0]} lignes")

    conn.close()
    print("\n✅ MIGRATION TERMINÉE")

if __name__ == '__main__':
    migrate()
