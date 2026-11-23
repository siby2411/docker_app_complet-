"""
Module Stock Pharmacie — Clinique Omega
Gestion des médicaments, entrées/sorties, alertes de seuil
"""
from flask import render_template_string, request, redirect, flash
import sqlite3
from datetime import datetime

DB_PATH = "/app/data/clinique.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


try:
    from auth import role_required, admin_required, staff_required, log_action
    from flask_login import current_user
except ImportError:
    def role_required(*r):
        def deco(f):
            return f
        return deco
    def admin_required(f):
        return f
    def staff_required(f):
        return f
    def log_action(*a, **k):
        pass
    current_user = None


def _init_stock_tables():
    """Crée les tables du stock si elles n'existent pas"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS medicaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        forme TEXT,
        dosage TEXT,
        categorie TEXT,
        fabricant TEXT,
        prix_achat REAL DEFAULT 0,
        prix_vente REAL DEFAULT 0,
        stock_actuel INTEGER DEFAULT 0,
        stock_min INTEGER DEFAULT 10,
        stock_max INTEGER DEFAULT 1000,
        emplacement TEXT,
        ordonnance_requise INTEGER DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS mouvements_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicament_id INTEGER NOT NULL,
        type_mouvement TEXT NOT NULL,
        quantite INTEGER NOT NULL,
        prix_unitaire REAL DEFAULT 0,
        motif TEXT,
        user_id INTEGER,
        date_mouvement TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (medicament_id) REFERENCES medicaments(id)
    )""")
    conn.commit()
    conn.close()


def register_stock_routes(app, render_page):
    """Routes du module stock pharmacie"""
    _init_stock_tables()

    # ==================== LISTE ====================
    @app.route('/stock')
    @staff_required
    def stock_liste():
        conn = get_db()
        c = conn.cursor()

        search = request.args.get('q', '').strip()
        if search:
            c.execute("""SELECT * FROM medicaments WHERE actif=1
                         AND (nom LIKE ? OR code LIKE ? OR categorie LIKE ?)
                         ORDER BY nom""",
                      (f'%{search}%', f'%{search}%', f'%{search}%'))
        else:
            c.execute("SELECT * FROM medicaments WHERE actif=1 ORDER BY nom")
        rows = c.fetchall()

        # Stats
        c.execute("SELECT COUNT(*) FROM medicaments WHERE actif=1")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM medicaments WHERE actif=1 AND stock_actuel <= stock_min")
        alertes = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(stock_actuel * prix_achat), 0) FROM medicaments WHERE actif=1")
        valeur = c.fetchone()[0]
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-pills"></i> Stock Pharmacie</h2>
          <a href="/stock/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau médicament</a>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-boxes stat-icon"></i>
            <div class="stat-value">{total}</div>
            <div class="stat-label">Médicaments</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-exclamation-triangle stat-icon"></i>
            <div class="stat-value">{alertes}</div>
            <div class="stat-label">Alertes stock bas</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-money-bill-wave stat-icon"></i>
            <div class="stat-value">{valeur:,.0f}</div>
            <div class="stat-label">Valeur du stock (FCFA)</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Inventaire</h3>
            <form method="GET" style="display:flex;gap:8px">
              <input type="text" name="q" value="{search}" placeholder="Rechercher..." style="padding:8px 12px;border:2px solid #e2e8f0;border-radius:6px;width:250px">
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Nom</th><th>Forme</th><th>Catégorie</th><th>Stock</th><th>Seuil</th><th>Prix vente</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for m in rows:
            if m['stock_actuel'] <= 0:
                stock_badge = '<span class="badge badge-danger">RUPTURE</span>'
            elif m['stock_actuel'] <= m['stock_min']:
                stock_badge = f'<span class="badge badge-warning">{m["stock_actuel"]}</span>'
            else:
                stock_badge = f'<span class="badge badge-success">{m["stock_actuel"]}</span>'

            content += f"""<tr>
              <td><strong>{m['code']}</strong></td>
              <td>{m['nom']}</td>
              <td>{m['forme'] or '-'}</td>
              <td>{m['categorie'] or '-'}</td>
              <td>{stock_badge}</td>
              <td>{m['stock_min']}</td>
              <td><strong>{m['prix_vente']:,.0f}</strong> FCFA</td>
              <td>
                <a href="/stock/{m['id']}/mouvement" class="btn btn-success btn-sm" title="Mouvement"><i class="fas fa-arrow-right-arrow-left"></i></a>
                <a href="/stock/{m['id']}/modifier" class="btn btn-warning btn-sm" title="Modifier"><i class="fas fa-edit"></i></a>
              </td>
            </tr>"""
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-box-open"></i><br>Aucun médicament</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='stock', page_title='Stock pharmacie')

    # ==================== NOUVEAU MÉDICAMENT ====================
    @app.route('/stock/nouveau', methods=['GET', 'POST'])
    @admin_required
    def stock_nouveau():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                code = request.form.get('code') or f"MED-{datetime.now().strftime('%y%m%d%H%M%S')}"
                c.execute("""INSERT INTO medicaments
                    (code, nom, forme, dosage, categorie, fabricant,
                     prix_achat, prix_vente, stock_actuel, stock_min, stock_max,
                     emplacement, ordonnance_requise, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (code, request.form['nom'], request.form.get('forme', ''),
                     request.form.get('dosage', ''), request.form.get('categorie', ''),
                     request.form.get('fabricant', ''),
                     float(request.form.get('prix_achat') or 0),
                     float(request.form.get('prix_vente') or 0),
                     int(request.form.get('stock_actuel') or 0),
                     int(request.form.get('stock_min') or 10),
                     int(request.form.get('stock_max') or 1000),
                     request.form.get('emplacement', ''),
                     1 if request.form.get('ordonnance_requise') else 0))
                conn.commit()
                conn.close()
                flash(f"✅ Médicament {code} créé", "success")
                return redirect('/stock')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = """
        <div class="page-header"><h2><i class="fas fa-pills"></i> Nouveau Médicament</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code *</label><input type="text" name="code" placeholder="Auto si vide"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required placeholder="Ex : Paracétamol"></div>
              <div class="form-group"><label>Forme</label>
                <select name="forme">
                  <option value="">--</option>
                  <option>Comprimé</option><option>Gélule</option>
                  <option>Sirop</option><option>Injection</option>
                  <option>Pommade</option><option>Suppositoire</option>
                  <option>Gouttes</option><option>Sachet</option>
                </select>
              </div>
              <div class="form-group"><label>Dosage</label><input type="text" name="dosage" placeholder="Ex : 500mg"></div>
              <div class="form-group"><label>Catégorie</label>
                <select name="categorie">
                  <option value="">--</option>
                  <option>Antalgique</option><option>Antibiotique</option>
                  <option>Antipaludique</option><option>Anti-inflammatoire</option>
                  <option>Antihypertenseur</option><option>Antidiabétique</option>
                  <option>Vitamines</option><option>Autre</option>
                </select>
              </div>
              <div class="form-group"><label>Fabricant</label><input type="text" name="fabricant"></div>
              <div class="form-group"><label>Prix achat (FCFA)</label><input type="number" name="prix_achat" value="0"></div>
              <div class="form-group"><label>Prix vente (FCFA)</label><input type="number" name="prix_vente" value="0"></div>
              <div class="form-group"><label>Stock initial</label><input type="number" name="stock_actuel" value="0"></div>
              <div class="form-group"><label>Seuil alerte</label><input type="number" name="stock_min" value="10"></div>
              <div class="form-group"><label>Stock max</label><input type="number" name="stock_max" value="1000"></div>
              <div class="form-group"><label>Emplacement</label><input type="text" name="emplacement" placeholder="Ex : Étagère A1"></div>
              <div class="form-group" style="display:flex;align-items:center;gap:8px;margin-top:30px">
                <input type="checkbox" name="ordonnance_requise" style="width:auto">
                <label style="margin:0">Ordonnance requise</label>
              </div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/stock" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='stock', page_title='Nouveau médicament')

    # ==================== MOUVEMENT DE STOCK ====================
    @app.route('/stock/<int:mid>/mouvement', methods=['GET', 'POST'])
    @staff_required
    def stock_mouvement(mid):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM medicaments WHERE id=?", (mid,))
        med = c.fetchone()
        if not med:
            conn.close()
            flash("Médicament introuvable", "danger")
            return redirect('/stock')

        if request.method == 'POST':
            try:
                type_mvt = request.form['type_mouvement']
                quantite = int(request.form['quantite'])
                prix = float(request.form.get('prix_unitaire') or 0)

                # Mise à jour du stock
                if type_mvt == 'entree':
                    nouveau_stock = med['stock_actuel'] + quantite
                elif type_mvt == 'sortie':
                    if quantite > med['stock_actuel']:
                        raise ValueError(f"Stock insuffisant ({med['stock_actuel']} disponible)")
                    nouveau_stock = med['stock_actuel'] - quantite
                else:
                    nouveau_stock = quantite

                c.execute("UPDATE medicaments SET stock_actuel=? WHERE id=?", (nouveau_stock, mid))
                c.execute("""INSERT INTO mouvements_stock
                    (medicament_id, type_mouvement, quantite, prix_unitaire, motif, user_id)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (mid, type_mvt, quantite, prix,
                     request.form.get('motif', ''),
                     current_user.id if current_user else None))

                # Historique
                c.execute("""SELECT * FROM mouvements_stock WHERE medicament_id=?
                             ORDER BY date_mouvement DESC LIMIT 20""", (mid,))
                mouvements = c.fetchall()

                conn.commit()
                conn.close()
                flash(f"✅ Mouvement enregistré. Nouveau stock : {nouveau_stock}", "success")
                return redirect(f'/stock/{mid}/mouvement')
            except Exception as e:
                flash(f"❌ Erreur : {e}", "danger")

        # Historique
        c.execute("""SELECT m.*, u.nom as u_nom, u.prenom as u_prenom
                     FROM mouvements_stock m
                     LEFT JOIN utilisateurs u ON m.user_id = u.id
                     WHERE m.medicament_id = ?
                     ORDER BY m.date_mouvement DESC LIMIT 30""", (mid,))
        mouvements = c.fetchall()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-arrows-rotate"></i> {med['nom']} {med['dosage'] or ''}</h2>
          <a href="/stock" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-boxes stat-icon"></i>
            <div class="stat-value">{med['stock_actuel']}</div>
            <div class="stat-label">Stock actuel</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-exclamation-circle stat-icon"></i>
            <div class="stat-value">{med['stock_min']}</div>
            <div class="stat-label">Seuil alerte</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-tag stat-icon"></i>
            <div class="stat-value">{med['prix_vente']:,.0f}</div>
            <div class="stat-label">Prix vente FCFA</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-plus-minus"></i> Nouveau mouvement</h3></div>
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Type *</label>
                <select name="type_mouvement" required>
                  <option value="entree">Entrée (réception)</option>
                  <option value="sortie">Sortie (dispensation)</option>
                  <option value="ajustement">Ajustement (inventaire)</option>
                </select>
              </div>
              <div class="form-group"><label>Quantité *</label><input type="number" name="quantite" required min="1" value="1"></div>
              <div class="form-group"><label>Prix unitaire (FCFA)</label><input type="number" name="prix_unitaire" value="0"></div>
              <div class="form-group"><label>Motif</label><input type="text" name="motif" placeholder="Ex : Vente, Réappro..."></div>
            </div>
            <div style="margin-top:15px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
            </div>
          </form>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-clock-rotate-left"></i> Historique des mouvements</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Type</th><th>Quantité</th><th>Motif</th><th>Par</th></tr></thead>
              <tbody>
        """
        for mvt in mouvements:
            badge = 'badge-success' if mvt['type_mouvement'] == 'entree' else ('badge-danger' if mvt['type_mouvement'] == 'sortie' else 'badge-warning')
            signe = '+' if mvt['type_mouvement'] == 'entree' else ('-' if mvt['type_mouvement'] == 'sortie' else '=')
            content += f"""<tr>
              <td>{mvt['date_mouvement'][:16]}</td>
              <td><span class="badge {badge}">{mvt['type_mouvement']}</span></td>
              <td><strong>{signe}{mvt['quantite']}</strong></td>
              <td>{mvt['motif'] or '-'}</td>
              <td>{mvt['u_nom'] or '?'} {mvt['u_prenom'] or ''}</td>
            </tr>"""
        if not mouvements:
            content += '<tr><td colspan="5" class="empty">Aucun mouvement</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='stock', page_title=f"Stock {med['nom']}")

    # ==================== MODIFIER ====================
    @app.route('/stock/<int:mid>/modifier', methods=['GET', 'POST'])
    @admin_required
    def stock_modifier(mid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE medicaments SET
                    nom=?, forme=?, dosage=?, categorie=?, fabricant=?,
                    prix_achat=?, prix_vente=?, stock_min=?, stock_max=?,
                    emplacement=?, ordonnance_requise=? WHERE id=?""",
                    (request.form['nom'], request.form.get('forme', ''),
                     request.form.get('dosage', ''), request.form.get('categorie', ''),
                     request.form.get('fabricant', ''),
                     float(request.form.get('prix_achat') or 0),
                     float(request.form.get('prix_vente') or 0),
                     int(request.form.get('stock_min') or 10),
                     int(request.form.get('stock_max') or 1000),
                     request.form.get('emplacement', ''),
                     1 if request.form.get('ordonnance_requise') else 0,
                     mid))
                conn.commit()
                conn.close()
                flash("✅ Médicament mis à jour", "success")
                return redirect('/stock')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM medicaments WHERE id=?", (mid,))
        m = c.fetchone()
        conn.close()
        formes = ['', 'Comprimé', 'Gélule', 'Sirop', 'Injection', 'Pommade', 'Suppositoire', 'Gouttes', 'Sachet']
        cats = ['', 'Antalgique', 'Antibiotique', 'Antipaludique', 'Anti-inflammatoire', 'Antihypertenseur', 'Antidiabétique', 'Vitamines', 'Autre']

        content = f"""
        <div class="page-header"><h2><i class="fas fa-edit"></i> Modifier {m['nom']}</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{m['nom']}" required></div>
              <div class="form-group"><label>Forme</label>
                <select name="forme">
                  {''.join(f'<option value="{f}" {"selected" if m["forme"]==f else ""}>{f or "--"}</option>' for f in formes)}
                </select>
              </div>
              <div class="form-group"><label>Dosage</label><input type="text" name="dosage" value="{m['dosage'] or ''}"></div>
              <div class="form-group"><label>Catégorie</label>
                <select name="categorie">
                  {''.join(f'<option value="{c}" {"selected" if m["categorie"]==c else ""}>{c or "--"}</option>' for c in cats)}
                </select>
              </div>
              <div class="form-group"><label>Fabricant</label><input type="text" name="fabricant" value="{m['fabricant'] or ''}"></div>
              <div class="form-group"><label>Prix achat</label><input type="number" name="prix_achat" value="{m['prix_achat']}"></div>
              <div class="form-group"><label>Prix vente</label><input type="number" name="prix_vente" value="{m['prix_vente']}"></div>
              <div class="form-group"><label>Seuil alerte</label><input type="number" name="stock_min" value="{m['stock_min']}"></div>
              <div class="form-group"><label>Stock max</label><input type="number" name="stock_max" value="{m['stock_max']}"></div>
              <div class="form-group"><label>Emplacement</label><input type="text" name="emplacement" value="{m['emplacement'] or ''}"></div>
              <div class="form-group" style="display:flex;align-items:center;gap:8px;margin-top:30px">
                <input type="checkbox" name="ordonnance_requise" style="width:auto" {"checked" if m['ordonnance_requise'] else ""}>
                <label style="margin:0">Ordonnance requise</label>
              </div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/stock" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='stock', page_title=f"Modifier {m['nom']}")

    print("[STOCK] ✅ Routes stock pharmacie enregistrées")
