"""
Module CRUD complet pour Omega Stock
Produits, Catégories, Fournisseurs, Entrepôts, Zones, Emplacements,
Lots, Utilisateurs
"""
from flask import render_template_string, request, redirect, flash, jsonify
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "/app/data/stock.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def gen_code(prefix, table, field='code'):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"SELECT COUNT(*) FROM {table}")
    n = c.fetchone()[0] + 1
    conn.close()
    return f"{prefix}-{n:04d}"


try:
    from auth import (role_required, admin_required, gestionnaire_required,
                      staff_required, magasinier_required, log_action)
    from flask_login import current_user
except ImportError:
    def role_required(*r):
        def d(f): return f
        return d
    def admin_required(f): return f
    def gestionnaire_required(f): return f
    def staff_required(f): return f
    def magasinier_required(f): return f
    def log_action(*a, **k): pass
    current_user = None


def register_crud_routes(app, render_page):
    """Enregistre toutes les routes CRUD"""

    # ==================== PRODUITS ====================
    @app.route('/produits')
    @staff_required
    def produits_liste():
        conn = get_db()
        c = conn.cursor()

        search = request.args.get('q', '').strip()
        cat_filter = request.args.get('categorie', '')
        alerte_filter = request.args.get('alerte', '')

        query = """SELECT p.*, cat.nom as cat_nom, f.nom as fournisseur_nom,
                          (SELECT COUNT(*) FROM stocks WHERE produit_id = p.id AND quantite > 0) as nb_emplacements
                   FROM produits p
                   LEFT JOIN categories cat ON p.categorie_id = cat.id
                   LEFT JOIN fournisseurs f ON p.fournisseur_principal_id = f.id
                   WHERE p.actif=1"""
        params = []

        if search:
            query += " AND (p.nom LIKE ? OR p.sku LIKE ? OR p.code_barres LIKE ?)"
            params.extend([f'%{search}%'] * 3)

        if cat_filter:
            query += " AND p.categorie_id = ?"
            params.append(int(cat_filter))

        if alerte_filter == 'bas':
            query += " AND p.stock_actuel <= p.stock_min"
        elif alerte_filter == 'zero':
            query += " AND p.stock_actuel <= 0"

        query += " ORDER BY p.nom"
        c.execute(query, params)
        rows = c.fetchall()

        # Catégories pour filtre
        c.execute("SELECT id, nom FROM categories WHERE actif=1 ORDER BY nom")
        categories = c.fetchall()

        # Stats
        c.execute("SELECT COUNT(*) FROM produits WHERE actif=1")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM produits WHERE actif=1 AND stock_actuel <= stock_min")
        stock_bas = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM produits WHERE actif=1 AND stock_actuel <= 0")
        rupture = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(stock_actuel * pmp), 0) FROM produits WHERE actif=1")
        valeur = c.fetchone()[0]
        conn.close()

        cats_opts = "".join(f'<option value="{cat["id"]}" {"selected" if cat_filter == str(cat["id"]) else ""}>{cat["nom"]}</option>' for cat in categories)

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-box"></i> Produits</h2>
            <div class="page-subtitle">Catalogue complet des articles</div>
          </div>
          <a href="/produits/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau produit</a>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-box stat-icon"></i>
            <div class="stat-value">{total}</div>
            <div class="stat-label">Produits actifs</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-exclamation-triangle stat-icon"></i>
            <div class="stat-value">{stock_bas}</div>
            <div class="stat-label">Stock bas</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-times-circle stat-icon"></i>
            <div class="stat-value">{rupture}</div>
            <div class="stat-label">En rupture</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-money-bill-wave stat-icon"></i>
            <div class="stat-value">{valeur:,.0f}</div>
            <div class="stat-label">Valeur (FCFA)</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Catalogue</h3>
            <form method="GET" style="display:flex;gap:8px;flex-wrap:wrap">
              <input type="text" name="q" value="{search}" placeholder="SKU, nom, code-barres..." style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px;width:200px">
              <select name="categorie" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Toutes catégories</option>
                {cats_opts}
              </select>
              <select name="alerte" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tout stock</option>
                <option value="bas" {"selected" if alerte_filter == "bas" else ""}>Stock bas</option>
                <option value="zero" {"selected" if alerte_filter == "zero" else ""}>En rupture</option>
              </select>
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>SKU</th><th>Produit</th><th>Catégorie</th><th>Stock</th>
                  <th>Min/Max</th><th>PMP</th><th>Valeur</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
        """
        for p in rows:
            if p['stock_actuel'] <= 0:
                stock_badge = 'badge-danger'
            elif p['stock_actuel'] <= p['stock_min']:
                stock_badge = 'badge-warning'
            else:
                stock_badge = 'badge-success'

            valeur_p = p['stock_actuel'] * p['pmp']

            content += f"""
            <tr>
              <td><strong>{p['sku']}</strong><br><small style="color:#94a3b8">{p['code_barres'] or ''}</small></td>
              <td>
                <div style="font-weight:700">{p['nom'][:50]}</div>
                <small style="color:#94a3b8">{p['unite']} · {p['nb_emplacements']} emplacement(s)</small>
              </td>
              <td>{p['cat_nom'] or '-'}</td>
              <td><span class="badge {stock_badge}">{p['stock_actuel']:.0f} {p['unite']}</span></td>
              <td><small>{p['stock_min']:.0f} / {p['stock_max']:.0f}</small></td>
              <td>{p['pmp']:,.0f} FCFA</td>
              <td><strong style="color:#059669">{valeur_p:,.0f} FCFA</strong></td>
              <td>
                <a href="/produits/{p['id']}" class="btn btn-info btn-sm" title="Voir"><i class="fas fa-eye"></i></a>
                <a href="/produits/{p['id']}/modifier" class="btn btn-warning btn-sm" title="Modifier"><i class="fas fa-edit"></i></a>
                <a href="/produits/{p['id']}/supprimer" class="btn btn-danger btn-sm" title="Supprimer" onclick="return confirm('Confirmer la suppression ?')"><i class="fas fa-trash"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-box-open"></i><br>Aucun produit</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='produits', page_title='Produits')

    @app.route('/produits/nouveau', methods=['GET', 'POST'])
    @gestionnaire_required
    def produit_nouveau():
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                sku = request.form.get('sku') or gen_code('SKU', 'produits', 'sku')
                c.execute("""INSERT INTO produits
                    (sku, code_barres, nom, description_courte, description_longue,
                     categorie_id, fournisseur_principal_id, unite, poids_kg, volume_m3,
                     prix_achat, prix_vente, pmp, tva, stock_actuel, stock_min, stock_max,
                     point_commande, quantite_commande, delai_reappro_jours,
                     gere_lot, gere_peremption, gere_serie, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (sku, request.form.get('code_barres', ''),
                     request.form['nom'],
                     request.form.get('description_courte', ''),
                     request.form.get('description_longue', ''),
                     int(request.form['categorie_id']) if request.form.get('categorie_id') else None,
                     int(request.form['fournisseur_principal_id']) if request.form.get('fournisseur_principal_id') else None,
                     request.form.get('unite', 'unité'),
                     float(request.form.get('poids_kg') or 0),
                     float(request.form.get('volume_m3') or 0),
                     float(request.form.get('prix_achat') or 0),
                     float(request.form.get('prix_vente') or 0),
                     float(request.form.get('prix_achat') or 0),
                     float(request.form.get('tva') or 18),
                     float(request.form.get('stock_actuel') or 0),
                     float(request.form.get('stock_min') or 0),
                     float(request.form.get('stock_max') or 1000),
                     float(request.form.get('point_commande') or 0),
                     float(request.form.get('quantite_commande') or 0),
                     int(request.form.get('delai_reappro_jours') or 7),
                     1 if request.form.get('gere_lot') else 0,
                     1 if request.form.get('gere_peremption') else 0,
                     1 if request.form.get('gere_serie') else 0))
                conn.commit()
                conn.close()
                if current_user and current_user.is_authenticated:
                    log_action(current_user.id, 'CREATE_PRODUIT', sku)
                flash(f"✅ Produit {sku} créé", "success")
                return redirect('/produits')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom FROM categories WHERE actif=1 ORDER BY nom")
        categories = c.fetchall()
        c.execute("SELECT id, nom FROM fournisseurs WHERE actif=1 ORDER BY nom")
        fournisseurs = c.fetchall()
        conn.close()

        cats_opts = "".join(f'<option value="{x["id"]}">{x["nom"]}</option>' for x in categories)
        four_opts = "".join(f'<option value="{x["id"]}">{x["nom"]}</option>' for x in fournisseurs)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-box-open"></i> Nouveau Produit</h2>
          <a href="/produits" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <h3 style="margin-bottom:20px;color:#059669"><i class="fas fa-info-circle"></i> Identification</h3>
            <div class="form-grid">
              <div class="form-group"><label>SKU (auto si vide)</label><input type="text" name="sku" placeholder="SKU-0001"></div>
              <div class="form-group"><label>Code-barres (EAN/QR)</label><input type="text" name="code_barres" placeholder="3612345678901"></div>
              <div class="form-group form-full"><label>Nom du produit *</label><input type="text" name="nom" required></div>
              <div class="form-group form-full"><label>Description courte</label><input type="text" name="description_courte"></div>
              <div class="form-group form-full"><label>Description longue</label><textarea name="description_longue" rows="3"></textarea></div>
              <div class="form-group"><label>Catégorie</label><select name="categorie_id"><option value="">--</option>{cats_opts}</select></div>
              <div class="form-group"><label>Fournisseur principal</label><select name="fournisseur_principal_id"><option value="">--</option>{four_opts}</select></div>
              <div class="form-group"><label>Unité</label>
                <select name="unite">
                  <option value="unité">Unité</option>
                  <option value="pièce">Pièce</option>
                  <option value="kg">Kilogramme</option>
                  <option value="litre">Litre</option>
                  <option value="mètre">Mètre</option>
                  <option value="sac">Sac</option>
                  <option value="carton">Carton</option>
                  <option value="palette">Palette</option>
                  <option value="boîte">Boîte</option>
                  <option value="ramette">Ramette</option>
                </select>
              </div>
              <div class="form-group"><label>Poids (kg)</label><input type="number" name="poids_kg" step="0.001" value="0"></div>
              <div class="form-group"><label>Volume (m³)</label><input type="number" name="volume_m3" step="0.001" value="0"></div>
            </div>

            <h3 style="margin:25px 0 20px;color:#059669"><i class="fas fa-tag"></i> Prix & Valorisation</h3>
            <div class="form-grid">
              <div class="form-group"><label>Prix d'achat (FCFA)</label><input type="number" name="prix_achat" step="0.01" value="0"></div>
              <div class="form-group"><label>Prix de vente (FCFA)</label><input type="number" name="prix_vente" step="0.01" value="0"></div>
              <div class="form-group"><label>TVA (%)</label><input type="number" name="tva" step="0.01" value="18"></div>
            </div>

            <h3 style="margin:25px 0 20px;color:#059669"><i class="fas fa-boxes"></i> Stock & Seuils</h3>
            <div class="form-grid">
              <div class="form-group"><label>Stock initial</label><input type="number" name="stock_actuel" step="0.01" value="0"></div>
              <div class="form-group"><label>Stock minimum (seuil d'alerte)</label><input type="number" name="stock_min" step="0.01" value="0"></div>
              <div class="form-group"><label>Stock maximum</label><input type="number" name="stock_max" step="0.01" value="1000"></div>
              <div class="form-group"><label>Point de commande</label><input type="number" name="point_commande" step="0.01" value="0"></div>
              <div class="form-group"><label>Quantité à commander</label><input type="number" name="quantite_commande" step="0.01" value="0"></div>
              <div class="form-group"><label>Délai réappro (jours)</label><input type="number" name="delai_reappro_jours" value="7"></div>
            </div>

            <h3 style="margin:25px 0 20px;color:#059669"><i class="fas fa-cog"></i> Traçabilité</h3>
            <div class="form-grid">
              <div class="form-group" style="display:flex;align-items:center;gap:8px">
                <input type="checkbox" name="gere_lot" style="width:auto">
                <label style="margin:0">Gestion par lots</label>
              </div>
              <div class="form-group" style="display:flex;align-items:center;gap:8px">
                <input type="checkbox" name="gere_peremption" style="width:auto">
                <label style="margin:0">Gestion des dates de péremption</label>
              </div>
              <div class="form-group" style="display:flex;align-items:center;gap:8px">
                <input type="checkbox" name="gere_serie" style="width:auto">
                <label style="margin:0">Gestion par numéros de série</label>
              </div>
            </div>

            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/produits" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='produits', page_title='Nouveau produit')

    @app.route('/produits/<int:pid>')
    @staff_required
    def produit_detail(pid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT p.*, cat.nom as cat_nom, f.nom as fournisseur_nom
                     FROM produits p
                     LEFT JOIN categories cat ON p.categorie_id = cat.id
                     LEFT JOIN fournisseurs f ON p.fournisseur_principal_id = f.id
                     WHERE p.id=?""", (pid,))
        p = c.fetchone()
        if not p:
            conn.close()
            flash("Produit introuvable", "danger")
            return redirect('/produits')

        # Stocks par emplacement
        c.execute("""SELECT s.*, e.code as emp_code, e.allee, e.rangee,
                            z.nom as zone_nom, en.nom as entrepot_nom,
                            l.numero_lot, l.date_peremption
                     FROM stocks s
                     JOIN emplacements e ON s.emplacement_id = e.id
                     JOIN zones z ON e.zone_id = z.id
                     JOIN entrepots en ON z.entrepot_id = en.id
                     LEFT JOIN lots l ON s.lot_id = l.id
                     WHERE s.produit_id = ? AND s.quantite > 0
                     ORDER BY en.nom, z.nom, e.code""", (pid,))
        stocks = c.fetchall()

        # Derniers mouvements
        c.execute("""SELECT m.*, u.nom as u_nom, u.prenom as u_prenom
                     FROM mouvements m
                     LEFT JOIN utilisateurs u ON m.user_id = u.id
                     WHERE m.produit_id = ?
                     ORDER BY m.date_mouvement DESC LIMIT 15""", (pid,))
        mouvements = c.fetchall()

        # Lots actifs
        c.execute("""SELECT * FROM lots WHERE produit_id=? AND statut='En stock'
                     ORDER BY date_peremption ASC""", (pid,))
        lots = c.fetchall()

        conn.close()

        marge = p['prix_vente'] - p['pmp']
        marge_pct = (marge / p['pmp'] * 100) if p['pmp'] > 0 else 0
        valeur_stock = p['stock_actuel'] * p['pmp']

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-box"></i> {p['nom'][:60]}</h2>
          <div style="display:flex;gap:10px">
            <a href="/mouvements/nouveau?produit_id={pid}" class="btn btn-success"><i class="fas fa-plus"></i> Mouvement</a>
            <a href="/produits/{pid}/modifier" class="btn btn-warning"><i class="fas fa-edit"></i> Modifier</a>
            <a href="/produits" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-barcode stat-icon"></i>
            <div class="stat-value" style="font-size:1.1rem">{p['sku']}</div>
            <div class="stat-label">SKU</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-boxes stat-icon"></i>
            <div class="stat-value">{p['stock_actuel']:.0f}</div>
            <div class="stat-label">Stock actuel ({p['unite']})</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-coins stat-icon"></i>
            <div class="stat-value">{p['pmp']:,.0f}</div>
            <div class="stat-label">PMP (FCFA)</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-money-bill-wave stat-icon"></i>
            <div class="stat-value">{valeur_stock:,.0f}</div>
            <div class="stat-label">Valeur stock</div>
          </div>
          <div class="stat-card">
            <i class="fas fa-chart-line stat-icon"></i>
            <div class="stat-value">{marge_pct:.1f}%</div>
            <div class="stat-label">Marge</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
          <div class="form-grid">
            <div><strong>Code-barres :</strong> {p['code_barres'] or '-'}</div>
            <div><strong>Catégorie :</strong> {p['cat_nom'] or '-'}</div>
            <div><strong>Fournisseur :</strong> {p['fournisseur_nom'] or '-'}</div>
            <div><strong>Unité :</strong> {p['unite']}</div>
            <div><strong>Poids :</strong> {p['poids_kg']} kg</div>
            <div><strong>Volume :</strong> {p['volume_m3']} m³</div>
            <div><strong>Prix achat :</strong> {p['prix_achat']:,.0f} FCFA</div>
            <div><strong>Prix vente :</strong> <span style="color:#059669;font-weight:800">{p['prix_vente']:,.0f} FCFA</span></div>
            <div><strong>Stock min :</strong> {p['stock_min']:.0f}</div>
            <div><strong>Stock max :</strong> {p['stock_max']:.0f}</div>
            <div><strong>Point de commande :</strong> {p['point_commande']:.0f}</div>
            <div><strong>Délai réappro :</strong> {p['delai_reappro_jours']} jours</div>
            <div><strong>Traçabilité :</strong>
              {'Lot ' if p['gere_lot'] else ''}{'Péremption ' if p['gere_peremption'] else ''}{'Série' if p['gere_serie'] else ''}
              {'' if (p['gere_lot'] or p['gere_peremption'] or p['gere_serie']) else 'Standard'}
            </div>
          </div>
          {('<p style="margin-top:20px;padding:15px;background:#f0fdf4;border-radius:10px;border-left:4px solid #059669"><strong>Description :</strong><br>' + p['description_longue'] + '</p>') if p['description_longue'] else ''}
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-map-marker-alt"></i> Répartition par emplacement ({len(stocks)})</h3>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Entrepôt</th><th>Zone</th><th>Emplacement</th><th>Lot</th><th>Péremption</th><th>Quantité</th></tr></thead>
              <tbody>
        """
        for s in stocks:
            content += f"""
            <tr>
              <td><strong>{s['entrepot_nom']}</strong></td>
              <td>{s['zone_nom']}</td>
              <td><code>{s['emp_code']}</code> <small>(Allée {s['allee']}, Rangée {s['rangee']})</small></td>
              <td>{s['numero_lot'] or '-'}</td>
              <td>{s['date_peremption'] or '-'}</td>
              <td><strong style="color:#059669">{s['quantite']:.0f} {p['unite']}</strong></td>
            </tr>
            """
        if not stocks:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-inbox"></i><br>Aucun stock</td></tr>'

        content += """
              </tbody>
            </table>
          </div>
        </div>
        """

        if lots:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-layer-group"></i> Lots actifs</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>N° Lot</th><th>Fabrication</th><th>Péremption</th><th>Quantité</th><th>Statut</th></tr></thead>
                  <tbody>
            """
            for l in lots:
                content += f"""
                <tr>
                  <td><strong>{l['numero_lot']}</strong></td>
                  <td>{l['date_fabrication'] or '-'}</td>
                  <td>{l['date_peremption'] or '-'}</td>
                  <td><strong>{l['quantite_actuelle']:.0f}</strong></td>
                  <td><span class="badge badge-success">{l['statut']}</span></td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-clock-rotate-left"></i> Derniers mouvements</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Type</th><th>Quantité</th><th>Motif</th><th>Utilisateur</th><th>Date</th></tr></thead>
              <tbody>
        """
        for m in mouvements:
            type_badge = 'badge-success' if m['type_mouvement'] == 'Entrée' else ('badge-danger' if m['type_mouvement'] == 'Sortie' else 'badge-info')
            content += f"""
            <tr>
              <td><strong>{m['numero']}</strong></td>
              <td><span class="badge {type_badge}">{m['type_mouvement']}</span></td>
              <td><strong>{m['quantite']:.0f}</strong> {p['unite']}</td>
              <td>{m['motif'] or '-'}</td>
              <td>{m['u_nom'] or '?'} {m['u_prenom'] or ''}</td>
              <td>{m['date_mouvement'][:16]}</td>
            </tr>
            """
        if not mouvements:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-inbox"></i><br>Aucun mouvement</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='produits', page_title=f"Produit {p['sku']}")

    @app.route('/produits/<int:pid>/modifier', methods=['GET', 'POST'])
    @gestionnaire_required
    def produit_modifier(pid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE produits SET
                    code_barres=?, nom=?, description_courte=?, description_longue=?,
                    categorie_id=?, fournisseur_principal_id=?, unite=?, poids_kg=?, volume_m3=?,
                    prix_achat=?, prix_vente=?, tva=?, stock_min=?, stock_max=?,
                    point_commande=?, quantite_commande=?, delai_reappro_jours=?,
                    gere_lot=?, gere_peremption=?, gere_serie=?
                    WHERE id=?""",
                    (request.form.get('code_barres', ''), request.form['nom'],
                     request.form.get('description_courte', ''),
                     request.form.get('description_longue', ''),
                     int(request.form['categorie_id']) if request.form.get('categorie_id') else None,
                     int(request.form['fournisseur_principal_id']) if request.form.get('fournisseur_principal_id') else None,
                     request.form.get('unite', 'unité'),
                     float(request.form.get('poids_kg') or 0),
                     float(request.form.get('volume_m3') or 0),
                     float(request.form.get('prix_achat') or 0),
                     float(request.form.get('prix_vente') or 0),
                     float(request.form.get('tva') or 18),
                     float(request.form.get('stock_min') or 0),
                     float(request.form.get('stock_max') or 1000),
                     float(request.form.get('point_commande') or 0),
                     float(request.form.get('quantite_commande') or 0),
                     int(request.form.get('delai_reappro_jours') or 7),
                     1 if request.form.get('gere_lot') else 0,
                     1 if request.form.get('gere_peremption') else 0,
                     1 if request.form.get('gere_serie') else 0,
                     pid))
                conn.commit()
                conn.close()
                if current_user and current_user.is_authenticated:
                    log_action(current_user.id, 'UPDATE_PRODUIT', f'ID {pid}')
                flash("✅ Produit mis à jour", "success")
                return redirect(f'/produits/{pid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM produits WHERE id=?", (pid,))
        p = c.fetchone()
        c.execute("SELECT id, nom FROM categories WHERE actif=1 ORDER BY nom")
        categories = c.fetchall()
        c.execute("SELECT id, nom FROM fournisseurs WHERE actif=1 ORDER BY nom")
        fournisseurs = c.fetchall()
        conn.close()

        cats_opts = "".join(f'<option value="{x["id"]}" {"selected" if x["id"]==p["categorie_id"] else ""}>{x["nom"]}</option>' for x in categories)
        four_opts = "".join(f'<option value="{x["id"]}" {"selected" if x["id"]==p["fournisseur_principal_id"] else ""}>{x["nom"]}</option>' for x in fournisseurs)
        unites = ['unité', 'pièce', 'kg', 'litre', 'mètre', 'sac', 'carton', 'palette', 'boîte', 'ramette']

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-edit"></i> Modifier {p['nom'][:50]}</h2>
          <a href="/produits/{pid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>SKU (non modifiable)</label><input type="text" value="{p['sku']}" disabled></div>
              <div class="form-group"><label>Code-barres</label><input type="text" name="code_barres" value="{p['code_barres'] or ''}"></div>
              <div class="form-group form-full"><label>Nom *</label><input type="text" name="nom" value="{p['nom']}" required></div>
              <div class="form-group form-full"><label>Description courte</label><input type="text" name="description_courte" value="{p['description_courte'] or ''}"></div>
              <div class="form-group form-full"><label>Description longue</label><textarea name="description_longue" rows="3">{p['description_longue'] or ''}</textarea></div>
              <div class="form-group"><label>Catégorie</label><select name="categorie_id"><option value="">--</option>{cats_opts}</select></div>
              <div class="form-group"><label>Fournisseur</label><select name="fournisseur_principal_id"><option value="">--</option>{four_opts}</select></div>
              <div class="form-group"><label>Unité</label>
                <select name="unite">
                  {''.join(f'<option value="{u}" {"selected" if p["unite"]==u else ""}>{u}</option>' for u in unites)}
                </select>
              </div>
              <div class="form-group"><label>Poids (kg)</label><input type="number" name="poids_kg" step="0.001" value="{p['poids_kg']}"></div>
              <div class="form-group"><label>Volume (m³)</label><input type="number" name="volume_m3" step="0.001" value="{p['volume_m3']}"></div>
              <div class="form-group"><label>Prix achat (FCFA)</label><input type="number" name="prix_achat" step="0.01" value="{p['prix_achat']}"></div>
              <div class="form-group"><label>Prix vente (FCFA)</label><input type="number" name="prix_vente" step="0.01" value="{p['prix_vente']}"></div>
              <div class="form-group"><label>TVA (%)</label><input type="number" name="tva" step="0.01" value="{p['tva']}"></div>
              <div class="form-group"><label>Stock min</label><input type="number" name="stock_min" step="0.01" value="{p['stock_min']}"></div>
              <div class="form-group"><label>Stock max</label><input type="number" name="stock_max" step="0.01" value="{p['stock_max']}"></div>
              <div class="form-group"><label>Point de commande</label><input type="number" name="point_commande" step="0.01" value="{p['point_commande']}"></div>
              <div class="form-group"><label>Quantité à commander</label><input type="number" name="quantite_commande" step="0.01" value="{p['quantite_commande']}"></div>
              <div class="form-group"><label>Délai réappro (j)</label><input type="number" name="delai_reappro_jours" value="{p['delai_reappro_jours']}"></div>
              <div class="form-group" style="display:flex;align-items:center;gap:8px;margin-top:30px">
                <input type="checkbox" name="gere_lot" style="width:auto" {"checked" if p['gere_lot'] else ""}>
                <label style="margin:0">Gestion par lots</label>
              </div>
              <div class="form-group" style="display:flex;align-items:center;gap:8px;margin-top:30px">
                <input type="checkbox" name="gere_peremption" style="width:auto" {"checked" if p['gere_peremption'] else ""}>
                <label style="margin:0">Gestion péremption</label>
              </div>
              <div class="form-group" style="display:flex;align-items:center;gap:8px;margin-top:30px">
                <input type="checkbox" name="gere_serie" style="width:auto" {"checked" if p['gere_serie'] else ""}>
                <label style="margin:0">Gestion séries</label>
              </div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/produits/{pid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/produits/{pid}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer la suppression ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='produits', page_title=f"Modifier {p['sku']}")

    @app.route('/produits/<int:pid>/supprimer')
    @admin_required
    def produit_supprimer(pid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE produits SET actif=0 WHERE id=?", (pid,))
            conn.commit()
            conn.close()
            if current_user and current_user.is_authenticated:
                log_action(current_user.id, 'DELETE_PRODUIT', f'ID {pid}')
            flash("✅ Produit archivé", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/produits')

    print("[CRUD] ✅ Routes produits enregistrées")

    # ==================== CATÉGORIES ====================
    @app.route('/categories')
    @staff_required
    def categories_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT cat.*,
                     (SELECT COUNT(*) FROM produits WHERE categorie_id = cat.id AND actif=1) as nb_produits
                     FROM categories cat WHERE cat.actif=1 ORDER BY cat.nom""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-tags"></i> Catégories</h2>
            <div class="page-subtitle">Organisation du catalogue</div>
          </div>
          <a href="/categories/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle catégorie</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Icône</th><th>Catégorie</th><th>Description</th><th>Produits</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for cat in rows:
            content += f"""
            <tr>
              <td><strong>{cat['code']}</strong></td>
              <td style="font-size:1.5rem;color:{cat['couleur'] or '#059669'}">
                <i class="fas {cat['icone'] or 'fa-folder'}"></i>
              </td>
              <td><strong>{cat['nom']}</strong></td>
              <td>{cat['description'] or '-'}</td>
              <td><span class="badge badge-info">{cat['nb_produits']}</span></td>
              <td>
                <a href="/categories/{cat['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a>
                <a href="/categories/{cat['id']}/supprimer" class="btn btn-danger btn-sm" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-tags"></i><br>Aucune catégorie</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='categories', page_title='Catégories')

    @app.route('/categories/nouvelle', methods=['GET', 'POST'])
    @gestionnaire_required
    def categorie_nouvelle():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                code = request.form.get('code') or gen_code('CAT', 'categories')
                c.execute("""INSERT INTO categories (code, nom, description, icone, couleur, actif)
                    VALUES (?, ?, ?, ?, ?, 1)""",
                    (code, request.form['nom'], request.form.get('description', ''),
                     request.form.get('icone', 'fa-folder'), request.form.get('couleur', '#059669')))
                conn.commit()
                conn.close()
                flash(f"✅ Catégorie {code} créée", "success")
                return redirect('/categories')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = """
        <div class="page-header">
          <h2><i class="fas fa-tags"></i> Nouvelle Catégorie</h2>
          <a href="/categories" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code (auto si vide)</label><input type="text" name="code" placeholder="CAT-0001"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="2"></textarea></div>
              <div class="form-group"><label>Icône FontAwesome</label>
                <input type="text" name="icone" value="fa-folder" placeholder="fa-microchip, fa-utensils...">
                <small style="color:#94a3b8;font-size:0.75rem">Voir fontawesome.com/icons</small>
              </div>
              <div class="form-group"><label>Couleur</label><input type="color" name="couleur" value="#059669"></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/categories" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='categories', page_title='Nouvelle catégorie')

    @app.route('/categories/<int:cid>/modifier', methods=['GET', 'POST'])
    @gestionnaire_required
    def categorie_modifier(cid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE categories SET code=?, nom=?, description=?, icone=?, couleur=? WHERE id=?""",
                    (request.form['code'], request.form['nom'], request.form.get('description', ''),
                     request.form.get('icone', 'fa-folder'), request.form.get('couleur', '#059669'), cid))
                conn.commit()
                conn.close()
                flash("✅ Catégorie mise à jour", "success")
                return redirect('/categories')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM categories WHERE id=?", (cid,))
        cat = c.fetchone()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-edit"></i> Modifier {cat['nom']}</h2>
          <a href="/categories" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code *</label><input type="text" name="code" value="{cat['code']}" required></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{cat['nom']}" required></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="2">{cat['description'] or ''}</textarea></div>
              <div class="form-group"><label>Icône</label><input type="text" name="icone" value="{cat['icone'] or 'fa-folder'}"></div>
              <div class="form-group"><label>Couleur</label><input type="color" name="couleur" value="{cat['couleur'] or '#059669'}"></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/categories" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/categories/{cid}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='categories', page_title='Modifier catégorie')

    @app.route('/categories/<int:cid>/supprimer')
    @admin_required
    def categorie_supprimer(cid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE categories SET actif=0 WHERE id=?", (cid,))
            conn.commit()
            conn.close()
            flash("✅ Catégorie archivée", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/categories')

    print("[CRUD] ✅ Routes catégories enregistrées")

    # ==================== FOURNISSEURS ====================
    @app.route('/fournisseurs')
    @gestionnaire_required
    def fournisseurs_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT f.*,
                     (SELECT COUNT(*) FROM produits WHERE fournisseur_principal_id = f.id AND actif=1) as nb_produits
                     FROM fournisseurs f WHERE f.actif=1 ORDER BY f.nom""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-truck"></i> Fournisseurs</h2>
            <div class="page-subtitle">Partenaires d'approvisionnement</div>
          </div>
          <a href="/fournisseurs/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau fournisseur</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Nom</th><th>Contact</th><th>Téléphone</th><th>Ville</th><th>Délai</th><th>Produits</th><th>Note</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for f in rows:
            note = '⭐' * int(f['note_qualite'] or 0)
            content += f"""
            <tr>
              <td><strong>{f['code']}</strong></td>
              <td><strong>{f['nom']}</strong></td>
              <td>{f['contact'] or '-'}</td>
              <td>{f['telephone']}</td>
              <td>{f['ville'] or '-'}</td>
              <td><span class="badge badge-info">{f['delai_livraison_jours']}j</span></td>
              <td><span class="badge badge-success">{f['nb_produits']}</span></td>
              <td>{note if note else '-'}</td>
              <td>
                <a href="/fournisseurs/{f['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a>
                <a href="/fournisseurs/{f['id']}/supprimer" class="btn btn-danger btn-sm" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="9" class="empty"><i class="fas fa-truck"></i><br>Aucun fournisseur</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='fournisseurs', page_title='Fournisseurs')

    @app.route('/fournisseurs/nouveau', methods=['GET', 'POST'])
    @gestionnaire_required
    def fournisseur_nouveau():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                code = request.form.get('code') or gen_code('FRN', 'fournisseurs')
                c.execute("""INSERT INTO fournisseurs
                    (code, nom, contact, telephone, email, adresse, ville, pays, nif,
                     conditions_paiement, delai_livraison_jours, note_qualite, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (code, request.form['nom'], request.form.get('contact', ''),
                     request.form['telephone'], request.form.get('email', ''),
                     request.form.get('adresse', ''), request.form.get('ville', ''),
                     request.form.get('pays', 'Sénégal'), request.form.get('nif', ''),
                     request.form.get('conditions_paiement', ''),
                     int(request.form.get('delai_livraison_jours') or 7),
                     float(request.form.get('note_qualite') or 0)))
                conn.commit()
                conn.close()
                flash(f"✅ Fournisseur {code} créé", "success")
                return redirect('/fournisseurs')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = """
        <div class="page-header">
          <h2><i class="fas fa-truck"></i> Nouveau Fournisseur</h2>
          <a href="/fournisseurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code (auto si vide)</label><input type="text" name="code" placeholder="FRN-0001"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group"><label>Personne à contacter</label><input type="text" name="contact"></div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email"></div>
              <div class="form-group"><label>Adresse</label><input type="text" name="adresse"></div>
              <div class="form-group"><label>Ville</label><input type="text" name="ville" value="Dakar"></div>
              <div class="form-group"><label>Pays</label><input type="text" name="pays" value="Sénégal"></div>
              <div class="form-group"><label>NIF</label><input type="text" name="nif"></div>
              <div class="form-group"><label>Délai livraison (jours)</label><input type="number" name="delai_livraison_jours" value="7"></div>
              <div class="form-group"><label>Note qualité (0-5)</label><input type="number" name="note_qualite" step="0.1" min="0" max="5" value="0"></div>
              <div class="form-group form-full"><label>Conditions de paiement</label><textarea name="conditions_paiement" rows="2"></textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/fournisseurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='fournisseurs', page_title='Nouveau fournisseur')

    @app.route('/fournisseurs/<int:fid>/modifier', methods=['GET', 'POST'])
    @gestionnaire_required
    def fournisseur_modifier(fid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE fournisseurs SET
                    code=?, nom=?, contact=?, telephone=?, email=?, adresse=?,
                    ville=?, pays=?, nif=?, conditions_paiement=?,
                    delai_livraison_jours=?, note_qualite=? WHERE id=?""",
                    (request.form['code'], request.form['nom'], request.form.get('contact', ''),
                     request.form['telephone'], request.form.get('email', ''),
                     request.form.get('adresse', ''), request.form.get('ville', ''),
                     request.form.get('pays', 'Sénégal'), request.form.get('nif', ''),
                     request.form.get('conditions_paiement', ''),
                     int(request.form.get('delai_livraison_jours') or 7),
                     float(request.form.get('note_qualite') or 0),
                     fid))
                conn.commit()
                conn.close()
                flash("✅ Fournisseur mis à jour", "success")
                return redirect('/fournisseurs')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM fournisseurs WHERE id=?", (fid,))
        f = c.fetchone()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-edit"></i> Modifier {f['nom']}</h2>
          <a href="/fournisseurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code *</label><input type="text" name="code" value="{f['code']}" required></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{f['nom']}" required></div>
              <div class="form-group"><label>Contact</label><input type="text" name="contact" value="{f['contact'] or ''}"></div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" value="{f['telephone']}" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email" value="{f['email'] or ''}"></div>
              <div class="form-group"><label>Adresse</label><input type="text" name="adresse" value="{f['adresse'] or ''}"></div>
              <div class="form-group"><label>Ville</label><input type="text" name="ville" value="{f['ville'] or ''}"></div>
              <div class="form-group"><label>Pays</label><input type="text" name="pays" value="{f['pays'] or 'Sénégal'}"></div>
              <div class="form-group"><label>NIF</label><input type="text" name="nif" value="{f['nif'] or ''}"></div>
              <div class="form-group"><label>Délai (jours)</label><input type="number" name="delai_livraison_jours" value="{f['delai_livraison_jours']}"></div>
              <div class="form-group"><label>Note qualité</label><input type="number" name="note_qualite" step="0.1" min="0" max="5" value="{f['note_qualite']}"></div>
              <div class="form-group form-full"><label>Conditions de paiement</label><textarea name="conditions_paiement" rows="2">{f['conditions_paiement'] or ''}</textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/fournisseurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/fournisseurs/{fid}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='fournisseurs', page_title='Modifier fournisseur')

    @app.route('/fournisseurs/<int:fid>/supprimer')
    @admin_required
    def fournisseur_supprimer(fid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE fournisseurs SET actif=0 WHERE id=?", (fid,))
            conn.commit()
            conn.close()
            flash("✅ Fournisseur archivé", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/fournisseurs')

    print("[CRUD] ✅ Routes fournisseurs enregistrées")

    # ==================== ENTREPÔTS ====================
    @app.route('/entrepots')
    @staff_required
    def entrepots_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT e.*, s.nom as site_nom,
                     (SELECT COUNT(*) FROM zones WHERE entrepot_id = e.id AND actif=1) as nb_zones,
                     (SELECT COUNT(*) FROM emplacements emp JOIN zones z ON emp.zone_id = z.id
                      WHERE z.entrepot_id = e.id AND emp.actif=1) as nb_emplacements
                     FROM entrepots e
                     LEFT JOIN sites s ON e.site_id = s.id
                     WHERE e.actif=1 ORDER BY s.nom, e.nom""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-warehouse"></i> Entrepôts</h2>
            <div class="page-subtitle">Vue multi-sites de vos installations</div>
          </div>
          <a href="/entrepots/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvel entrepôt</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Entrepôt</th><th>Site</th><th>Type</th><th>Surface</th><th>Zones</th><th>Emplacements</th><th>Responsable</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for e in rows:
            type_badge = 'badge-info'
            if e['type'] == 'Frigo':
                type_badge = 'badge-primary'
            elif e['type'] == 'Dangereux':
                type_badge = 'badge-danger'

            content += f"""
            <tr>
              <td><strong>{e['code']}</strong></td>
              <td>
                <strong>{e['nom']}</strong>
                {('<br><small style="color:#dc2626"><i class="fas fa-snowflake"></i> Température contrôlée</small>') if e['temperature_controlee'] else ''}
              </td>
              <td>{e['site_nom'] or '-'}</td>
              <td><span class="badge {type_badge}">{e['type']}</span></td>
              <td>{e['surface_m2']:,.0f} m² ({e['hauteur_m']:.1f} m h)</td>
              <td><span class="badge badge-info">{e['nb_zones']}</span></td>
              <td><span class="badge badge-success">{e['nb_emplacements']}</span></td>
              <td>{e['responsable'] or '-'}<br><small>{e['telephone'] or ''}</small></td>
              <td>
                <a href="/entrepots/{e['id']}" class="btn btn-info btn-sm" title="Détail"><i class="fas fa-eye"></i></a>
                <a href="/entrepots/{e['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="9" class="empty"><i class="fas fa-warehouse"></i><br>Aucun entrepôt</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='entrepots', page_title='Entrepôts')

    @app.route('/entrepots/nouveau', methods=['GET', 'POST'])
    @admin_required
    def entrepot_nouveau():
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                code = request.form.get('code') or gen_code('ENT', 'entrepots')
                c.execute("""INSERT INTO entrepots
                    (code, nom, site_id, type, surface_m2, hauteur_m, temperature_controlee,
                     responsable, telephone, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (code, request.form['nom'], int(request.form['site_id']),
                     request.form.get('type', 'Principal'),
                     float(request.form.get('surface_m2') or 0),
                     float(request.form.get('hauteur_m') or 0),
                     1 if request.form.get('temperature_controlee') else 0,
                     request.form.get('responsable', ''),
                     request.form.get('telephone', '')))
                conn.commit()
                conn.close()
                flash(f"✅ Entrepôt {code} créé", "success")
                return redirect('/entrepots')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom FROM sites WHERE actif=1 ORDER BY nom")
        sites = c.fetchall()
        conn.close()
        sites_opts = "".join(f'<option value="{s["id"]}">{s["nom"]}</option>' for s in sites)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-warehouse"></i> Nouvel Entrepôt</h2>
          <a href="/entrepots" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code (auto si vide)</label><input type="text" name="code" placeholder="ENT-0001"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group"><label>Site *</label><select name="site_id" required><option value="">--</option>{sites_opts}</select></div>
              <div class="form-group"><label>Type</label>
                <select name="type">
                  <option value="Principal">Principal</option>
                  <option value="Frigo">Frigorifique</option>
                  <option value="Congélation">Congélation</option>
                  <option value="Dangereux">Matières dangereuses</option>
                  <option value="Portuaire">Portuaire</option>
                  <option value="Transit">Zone de transit</option>
                </select>
              </div>
              <div class="form-group"><label>Surface (m²)</label><input type="number" name="surface_m2" step="0.01" value="0"></div>
              <div class="form-group"><label>Hauteur (m)</label><input type="number" name="hauteur_m" step="0.1" value="0"></div>
              <div class="form-group"><label>Responsable</label><input type="text" name="responsable"></div>
              <div class="form-group"><label>Téléphone</label><input type="tel" name="telephone"></div>
              <div class="form-group" style="display:flex;align-items:center;gap:8px;margin-top:30px">
                <input type="checkbox" name="temperature_controlee" style="width:auto">
                <label style="margin:0">Température contrôlée</label>
              </div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/entrepots" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='entrepots', page_title='Nouvel entrepôt')

    @app.route('/entrepots/<int:eid>')
    @staff_required
    def entrepot_detail(eid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT e.*, s.nom as site_nom, s.adresse as site_adresse, s.ville as site_ville
                     FROM entrepots e LEFT JOIN sites s ON e.site_id = s.id
                     WHERE e.id=?""", (eid,))
        e = c.fetchone()
        if not e:
            conn.close()
            flash("Entrepôt introuvable", "danger")
            return redirect('/entrepots')

        c.execute("""SELECT z.*,
                     (SELECT COUNT(*) FROM emplacements WHERE zone_id = z.id AND actif=1) as nb_emplacements,
                     (SELECT COALESCE(SUM(s.quantite), 0) FROM stocks s
                      JOIN emplacements emp ON s.emplacement_id = emp.id
                      WHERE emp.zone_id = z.id) as qte_stockee
                     FROM zones z WHERE z.entrepot_id = ? AND z.actif=1
                     ORDER BY z.nom""", (eid,))
        zones = c.fetchall()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-warehouse"></i> {e['nom']}</h2>
          <div style="display:flex;gap:10px">
            <a href="/zones/nouvelle?entrepot_id={eid}" class="btn btn-success"><i class="fas fa-plus"></i> Nouvelle zone</a>
            <a href="/entrepots/{eid}/modifier" class="btn btn-warning"><i class="fas fa-edit"></i> Modifier</a>
            <a href="/entrepots" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-warehouse stat-icon"></i>
            <div class="stat-value">{e['surface_m2']:,.0f}</div>
            <div class="stat-label">Surface (m²)</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-ruler-vertical stat-icon"></i>
            <div class="stat-value">{e['hauteur_m']:.1f} m</div>
            <div class="stat-label">Hauteur</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-layer-group stat-icon"></i>
            <div class="stat-value">{len(zones)}</div>
            <div class="stat-label">Zones</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-temperature-low stat-icon"></i>
            <div class="stat-value">{'❄️ Oui' if e['temperature_controlee'] else 'Non'}</div>
            <div class="stat-label">Temp. contrôlée</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
          <div class="form-grid">
            <div><strong>Code :</strong> {e['code']}</div>
            <div><strong>Type :</strong> {e['type']}</div>
            <div><strong>Site :</strong> {e['site_nom'] or '-'}</div>
            <div><strong>Ville :</strong> {e['site_ville'] or '-'}</div>
            <div><strong>Responsable :</strong> {e['responsable'] or '-'}</div>
            <div><strong>Téléphone :</strong> {e['telephone'] or '-'}</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-layer-group"></i> Zones ({len(zones)})</h3>
            <a href="/zones/nouvelle?entrepot_id={eid}" class="btn btn-primary btn-sm"><i class="fas fa-plus"></i> Ajouter</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Zone</th><th>Type</th><th>Description</th><th>Emplacements</th><th>Qté stockée</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for z in zones:
            content += f"""
            <tr>
              <td><strong>{z['code']}</strong></td>
              <td><strong>{z['nom']}</strong></td>
              <td><span class="badge badge-info">{z['type']}</span></td>
              <td>{z['description'] or '-'}</td>
              <td><span class="badge badge-success">{z['nb_emplacements']}</span></td>
              <td>{z['qte_stockee']:.0f}</td>
              <td>
                <a href="/zones/{z['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
                <a href="/zones/{z['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a>
              </td>
            </tr>
            """
        if not zones:
            content += '<tr><td colspan="7" class="empty"><i class="fas fa-layer-group"></i><br>Aucune zone</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='entrepots', page_title=f"Entrepôt {e['nom']}")

    @app.route('/entrepots/<int:eid>/modifier', methods=['GET', 'POST'])
    @admin_required
    def entrepot_modifier(eid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE entrepots SET
                    code=?, nom=?, site_id=?, type=?, surface_m2=?, hauteur_m=?,
                    temperature_controlee=?, responsable=?, telephone=? WHERE id=?""",
                    (request.form['code'], request.form['nom'], int(request.form['site_id']),
                     request.form.get('type', 'Principal'),
                     float(request.form.get('surface_m2') or 0),
                     float(request.form.get('hauteur_m') or 0),
                     1 if request.form.get('temperature_controlee') else 0,
                     request.form.get('responsable', ''),
                     request.form.get('telephone', ''), eid))
                conn.commit()
                conn.close()
                flash("✅ Entrepôt mis à jour", "success")
                return redirect(f'/entrepots/{eid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM entrepots WHERE id=?", (eid,))
        e = c.fetchone()
        c.execute("SELECT id, nom FROM sites WHERE actif=1 ORDER BY nom")
        sites = c.fetchall()
        conn.close()
        sites_opts = "".join(f'<option value="{s["id"]}" {"selected" if s["id"]==e["site_id"] else ""}>{s["nom"]}</option>' for s in sites)
        types = ['Principal', 'Frigo', 'Congélation', 'Dangereux', 'Portuaire', 'Transit']

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-edit"></i> Modifier {e['nom']}</h2>
          <a href="/entrepots/{eid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code *</label><input type="text" name="code" value="{e['code']}" required></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{e['nom']}" required></div>
              <div class="form-group"><label>Site *</label><select name="site_id" required>{sites_opts}</select></div>
              <div class="form-group"><label>Type</label>
                <select name="type">
                  {''.join(f'<option value="{t}" {"selected" if e["type"]==t else ""}>{t}</option>' for t in types)}
                </select>
              </div>
              <div class="form-group"><label>Surface (m²)</label><input type="number" name="surface_m2" step="0.01" value="{e['surface_m2']}"></div>
              <div class="form-group"><label>Hauteur (m)</label><input type="number" name="hauteur_m" step="0.1" value="{e['hauteur_m']}"></div>
              <div class="form-group"><label>Responsable</label><input type="text" name="responsable" value="{e['responsable'] or ''}"></div>
              <div class="form-group"><label>Téléphone</label><input type="tel" name="telephone" value="{e['telephone'] or ''}"></div>
              <div class="form-group" style="display:flex;align-items:center;gap:8px;margin-top:30px">
                <input type="checkbox" name="temperature_controlee" style="width:auto" {"checked" if e['temperature_controlee'] else ""}>
                <label style="margin:0">Température contrôlée</label>
              </div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/entrepots/{eid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='entrepots', page_title='Modifier entrepôt')

    print("[CRUD] ✅ Routes entrepôts enregistrées")

    # ==================== ZONES ====================
    @app.route('/zones/nouvelle', methods=['GET', 'POST'])
    @admin_required
    def zone_nouvelle():
        conn = get_db()
        c = conn.cursor()
        entrepot_id_pre = request.args.get('entrepot_id', '')

        if request.method == 'POST':
            try:
                code = request.form.get('code') or gen_code('Z', 'zones')
                c.execute("""INSERT INTO zones (code, nom, entrepot_id, type, description, actif)
                    VALUES (?, ?, ?, ?, ?, 1)""",
                    (code, request.form['nom'], int(request.form['entrepot_id']),
                     request.form.get('type', 'Stockage'),
                     request.form.get('description', '')))
                conn.commit()
                conn.close()
                flash(f"✅ Zone {code} créée", "success")
                return redirect(f"/entrepots/{request.form['entrepot_id']}")
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom FROM entrepots WHERE actif=1 ORDER BY nom")
        entrepots = c.fetchall()
        conn.close()
        entrepots_opts = "".join(f'<option value="{e["id"]}" {"selected" if str(e["id"])==entrepot_id_pre else ""}>{e["nom"]}</option>' for e in entrepots)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-layer-group"></i> Nouvelle Zone</h2>
          <a href="/entrepots" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code (auto si vide)</label><input type="text" name="code" placeholder="Z-A"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group"><label>Entrepôt *</label><select name="entrepot_id" required>{entrepots_opts}</select></div>
              <div class="form-group"><label>Type</label>
                <select name="type">
                  <option value="Stockage">Stockage</option>
                  <option value="Picking">Picking</option>
                  <option value="Réception">Réception</option>
                  <option value="Expédition">Expédition</option>
                  <option value="Frigo">Frigo</option>
                  <option value="Congélation">Congélation</option>
                  <option value="Dangereux">Dangereux</option>
                  <option value="Quarantaine">Quarantaine</option>
                </select>
              </div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="2"></textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/entrepots" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='zones', page_title='Nouvelle zone')

    @app.route('/zones/<int:zid>')
    @staff_required
    def zone_detail(zid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT z.*, e.nom as entrepot_nom, e.id as entrepot_id FROM zones z
                     LEFT JOIN entrepots e ON z.entrepot_id = e.id WHERE z.id=?""", (zid,))
        z = c.fetchone()
        if not z:
            conn.close()
            flash("Zone introuvable", "danger")
            return redirect('/entrepots')

        c.execute("""SELECT emp.*,
                     (SELECT COUNT(*) FROM stocks WHERE emplacement_id = emp.id AND quantite > 0) as nb_produits,
                     (SELECT COALESCE(SUM(quantite), 0) FROM stocks WHERE emplacement_id = emp.id) as qte_stockee
                     FROM emplacements emp WHERE emp.zone_id = ? AND emp.actif=1
                     ORDER BY emp.code""", (zid,))
        emplacements = c.fetchall()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-layer-group"></i> {z['nom']}</h2>
          <div style="display:flex;gap:10px">
            <a href="/emplacements/nouveau?zone_id={zid}" class="btn btn-success"><i class="fas fa-plus"></i> Nouvel emplacement</a>
            <a href="/entrepots/{z['entrepot_id']}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-layer-group stat-icon"></i>
            <div class="stat-value" style="font-size:1.3rem">{z['code']}</div>
            <div class="stat-label">Code zone</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-tag stat-icon"></i>
            <div class="stat-value" style="font-size:1.3rem">{z['type']}</div>
            <div class="stat-label">Type</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-cubes stat-icon"></i>
            <div class="stat-value">{len(emplacements)}</div>
            <div class="stat-label">Emplacements</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
          <div class="form-grid">
            <div><strong>Entrepôt :</strong> {z['entrepot_nom']}</div>
            <div><strong>Type :</strong> {z['type']}</div>
            <div class="form-full"><strong>Description :</strong> {z['description'] or '-'}</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-cubes"></i> Emplacements ({len(emplacements)})</h3>
            <a href="/emplacements/nouveau?zone_id={zid}" class="btn btn-primary btn-sm"><i class="fas fa-plus"></i> Ajouter</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Allée</th><th>Rangée</th><th>Niveau</th><th>Type</th><th>Capacité</th><th>Produits</th><th>Qté</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for emp in emplacements:
            content += f"""
            <tr>
              <td><strong>{emp['code']}</strong><br><small style="color:#94a3b8">{emp['code_barres'] or ''}</small></td>
              <td>{emp['allee']}</td>
              <td>{emp['rangee']}</td>
              <td>{emp['niveau']}</td>
              <td><span class="badge badge-info">{emp['type']}</span></td>
              <td>{emp['capacite_kg']:,.0f} kg</td>
              <td><span class="badge badge-success">{emp['nb_produits']}</span></td>
              <td>{emp['qte_stockee']:.0f}</td>
              <td>
                <a href="/emplacements/{emp['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a>
              </td>
            </tr>
            """
        if not emplacements:
            content += '<tr><td colspan="9" class="empty"><i class="fas fa-cubes"></i><br>Aucun emplacement</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='zones', page_title=f"Zone {z['nom']}")

    # ==================== EMPLACEMENTS ====================
    @app.route('/emplacements/nouveau', methods=['GET', 'POST'])
    @admin_required
    def emplacement_nouveau():
        conn = get_db()
        c = conn.cursor()
        zone_id_pre = request.args.get('zone_id', '')

        if request.method == 'POST':
            try:
                code = request.form.get('code') or f"EMP-{datetime.now().strftime('%H%M%S')}"
                c.execute("""INSERT INTO emplacements
                    (code, zone_id, allee, rangee, niveau, position, type,
                     capacite_kg, capacite_m3, code_barres, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (code, int(request.form['zone_id']),
                     request.form['allee'], request.form['rangee'],
                     int(request.form.get('niveau') or 1),
                     int(request.form.get('position') or 1),
                     request.form.get('type', 'Palette'),
                     float(request.form.get('capacite_kg') or 0),
                     float(request.form.get('capacite_m3') or 0),
                     request.form.get('code_barres', '')))
                conn.commit()
                conn.close()
                flash(f"✅ Emplacement {code} créé", "success")
                return redirect(f"/zones/{request.form['zone_id']}")
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom FROM zones WHERE actif=1 ORDER BY nom")
        zones = c.fetchall()
        conn.close()
        zones_opts = "".join(f'<option value="{z["id"]}" {"selected" if str(z["id"])==zone_id_pre else ""}>{z["nom"]}</option>' for z in zones)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-cube"></i> Nouvel Emplacement</h2>
          <a href="/entrepots" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code *</label><input type="text" name="code" required placeholder="A-01-01-01"></div>
              <div class="form-group"><label>Zone *</label><select name="zone_id" required><option value="">--</option>{zones_opts}</select></div>
              <div class="form-group"><label>Allée *</label><input type="text" name="allee" required placeholder="A01"></div>
              <div class="form-group"><label>Rangée *</label><input type="text" name="rangee" required placeholder="R01"></div>
              <div class="form-group"><label>Niveau</label><input type="number" name="niveau" value="1"></div>
              <div class="form-group"><label>Position</label><input type="number" name="position" value="1"></div>
              <div class="form-group"><label>Type</label>
                <select name="type">
                  <option value="Palette">Palette</option>
                  <option value="Vrac">Vrac</option>
                  <option value="Picking">Picking</option>
                  <option value="Casier">Casier</option>
                  <option value="Frigo">Frigo</option>
                  <option value="Congélation">Congélation</option>
                </select>
              </div>
              <div class="form-group"><label>Capacité (kg)</label><input type="number" name="capacite_kg" step="0.01" value="0"></div>
              <div class="form-group"><label>Capacité (m³)</label><input type="number" name="capacite_m3" step="0.01" value="0"></div>
              <div class="form-group"><label>Code-barres</label><input type="text" name="code_barres"></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/entrepots" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='emplacements', page_title='Nouvel emplacement')

    @app.route('/emplacements/<int:eid>/modifier', methods=['GET', 'POST'])
    @admin_required
    def emplacement_modifier(eid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE emplacements SET
                    code=?, zone_id=?, allee=?, rangee=?, niveau=?, position=?,
                    type=?, capacite_kg=?, capacite_m3=?, code_barres=? WHERE id=?""",
                    (request.form['code'], int(request.form['zone_id']),
                     request.form['allee'], request.form['rangee'],
                     int(request.form.get('niveau') or 1),
                     int(request.form.get('position') or 1),
                     request.form.get('type', 'Palette'),
                     float(request.form.get('capacite_kg') or 0),
                     float(request.form.get('capacite_m3') or 0),
                     request.form.get('code_barres', ''), eid))
                conn.commit()
                conn.close()
                flash("✅ Emplacement mis à jour", "success")
                return redirect(f"/zones/{request.form['zone_id']}")
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM emplacements WHERE id=?", (eid,))
        emp = c.fetchone()
        c.execute("SELECT id, nom FROM zones WHERE actif=1 ORDER BY nom")
        zones = c.fetchall()
        conn.close()
        zones_opts = "".join(f'<option value="{z["id"]}" {"selected" if z["id"]==emp["zone_id"] else ""}>{z["nom"]}</option>' for z in zones)
        types = ['Palette', 'Vrac', 'Picking', 'Casier', 'Frigo', 'Congélation']

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-edit"></i> Modifier {emp['code']}</h2>
          <a href="/zones/{emp['zone_id']}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code *</label><input type="text" name="code" value="{emp['code']}" required></div>
              <div class="form-group"><label>Zone *</label><select name="zone_id" required>{zones_opts}</select></div>
              <div class="form-group"><label>Allée</label><input type="text" name="allee" value="{emp['allee']}"></div>
              <div class="form-group"><label>Rangée</label><input type="text" name="rangee" value="{emp['rangee']}"></div>
              <div class="form-group"><label>Niveau</label><input type="number" name="niveau" value="{emp['niveau']}"></div>
              <div class="form-group"><label>Position</label><input type="number" name="position" value="{emp['position']}"></div>
              <div class="form-group"><label>Type</label>
                <select name="type">
                  {''.join(f'<option value="{t}" {"selected" if emp["type"]==t else ""}>{t}</option>' for t in types)}
                </select>
              </div>
              <div class="form-group"><label>Capacité (kg)</label><input type="number" name="capacite_kg" step="0.01" value="{emp['capacite_kg']}"></div>
              <div class="form-group"><label>Capacité (m³)</label><input type="number" name="capacite_m3" step="0.01" value="{emp['capacite_m3']}"></div>
              <div class="form-group"><label>Code-barres</label><input type="text" name="code_barres" value="{emp['code_barres'] or ''}"></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/zones/{emp['zone_id']}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='emplacements', page_title=f"Modifier {emp['code']}")

    print("[CRUD] ✅ Routes zones + emplacements enregistrées")

    # ==================== LOTS ====================
    @app.route('/lots')
    @staff_required
    def lots_liste():
        conn = get_db()
        c = conn.cursor()
        alerte = request.args.get('alerte', '')
        query = """SELECT l.*, p.nom as produit_nom, p.sku, p.unite, f.nom as fournisseur_nom
                   FROM lots l
                   JOIN produits p ON l.produit_id = p.id
                   LEFT JOIN fournisseurs f ON l.fournisseur_id = f.id
                   WHERE l.statut = 'En stock'"""
        params = []

        if alerte == 'peremption':
            query += " AND date(l.date_peremption) <= date('now', '+30 days') AND l.date_peremption IS NOT NULL"

        query += " ORDER BY l.date_peremption ASC, l.numero_lot"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()

        today = datetime.now().date()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-layer-group"></i> Lots & Traçabilité</h2>
            <div class="page-subtitle">Suivi des lots avec dates de péremption</div>
          </div>
          <div style="display:flex;gap:10px">
            <a href="/lots?alerte=peremption" class="btn btn-warning"><i class="fas fa-hourglass-half"></i> Péremption proche</a>
            <a href="/lots" class="btn btn-info"><i class="fas fa-list"></i> Tous</a>
          </div>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>N° Lot</th><th>Produit</th><th>Fournisseur</th><th>Fabrication</th><th>Péremption</th><th>Quantité</th><th>Valeur</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for l in rows:
            jours = '?'
            jours_color = '#059669'
            if l['date_peremption']:
                try:
                    peremption = datetime.fromisoformat(l['date_peremption']).date()
                    jours = (peremption - today).days
                    jours_color = '#dc2626' if jours <= 7 else ('#f59e0b' if jours <= 30 else '#059669')
                except Exception:
                    pass

            valeur = l['quantite_actuelle'] * l['prix_achat_unitaire']

            content += f"""
            <tr>
              <td><strong>{l['numero_lot']}</strong></td>
              <td>{l['produit_nom'][:40]}<br><small style="color:#94a3b8">{l['sku']}</small></td>
              <td>{l['fournisseur_nom'] or '-'}</td>
              <td>{l['date_fabrication'] or '-'}</td>
              <td>
                {l['date_peremption'] or '-'}
                {f'<br><span class="badge" style="background:{jours_color}20;color:{jours_color}">{jours} jours</span>' if jours != '?' else ''}
              </td>
              <td><strong>{l['quantite_actuelle']:.0f} {l['unite']}</strong></td>
              <td>{valeur:,.0f} FCFA</td>
              <td><span class="badge badge-success">{l['statut']}</span></td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-inbox"></i><br>Aucun lot</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='lots', page_title='Lots')

    print("[CRUD] ✅ Routes lots enregistrées")

    # ==================== UTILISATEURS ====================
    @app.route('/utilisateurs')
    @admin_required
    def utilisateurs_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM utilisateurs ORDER BY role, nom")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-users"></i> Utilisateurs</h2>
            <div class="page-subtitle">Gestion des accès et rôles</div>
          </div>
          <a href="/utilisateurs/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvel utilisateur</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Username</th><th>Nom</th><th>Contact</th><th>Rôle</th><th>Dernière connexion</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for u in rows:
            role_badge = f'badge-role-{u["role"]}'
            statut_badge = 'badge-success' if u['actif'] else 'badge-danger'
            content += f"""
            <tr>
              <td><strong>{u['username']}</strong></td>
              <td>{u['nom']} {u['prenom']}</td>
              <td>{u['email'] or '-'}<br><small>{u['telephone'] or ''}</small></td>
              <td><span class="badge {role_badge}">{u['role']}</span></td>
              <td>{u['dernier_login'][:16] if u['dernier_login'] else 'Jamais'}</td>
              <td><span class="badge {statut_badge}">{'Actif' if u['actif'] else 'Inactif'}</span></td>
              <td>
                <a href="/utilisateurs/{u['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="7" class="empty"><i class="fas fa-users"></i><br>Aucun utilisateur</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='utilisateurs', page_title='Utilisateurs')

    @app.route('/utilisateurs/nouveau', methods=['GET', 'POST'])
    @admin_required
    def utilisateur_nouveau():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                from auth import hash_password
                h = hash_password(request.form['password'])
                c.execute("""INSERT INTO utilisateurs
                    (username, password_hash, nom, prenom, email, telephone, role, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                    (request.form['username'], h, request.form['nom'],
                     request.form['prenom'], request.form.get('email', ''),
                     request.form.get('telephone', ''), request.form['role']))
                conn.commit()
                conn.close()
                flash(f"✅ Utilisateur {request.form['username']} créé", "success")
                return redirect('/utilisateurs')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = """
        <div class="page-header">
          <h2><i class="fas fa-user-plus"></i> Nouvel Utilisateur</h2>
          <a href="/utilisateurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Username *</label><input type="text" name="username" required></div>
              <div class="form-group"><label>Mot de passe *</label><input type="password" name="password" required minlength="6"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email"></div>
              <div class="form-group"><label>Téléphone</label><input type="tel" name="telephone"></div>
              <div class="form-group"><label>Rôle *</label>
                <select name="role" required>
                  <option value="consultation">Consultation</option>
                  <option value="magasinier">Magasinier</option>
                  <option value="gestionnaire">Gestionnaire</option>
                  <option value="admin">Administrateur</option>
                </select>
              </div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/utilisateurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='utilisateurs', page_title='Nouvel utilisateur')

    print("[CRUD] ✅ Routes utilisateurs enregistrées")
