"""
Module CRUD complet pour Omega Shop
Produits, Catégories, Marques, Fournisseurs, Clients, Promotions
"""
from flask import render_template_string, request, redirect, flash, jsonify
import sqlite3
from datetime import datetime

DB_PATH = "/app/data/ecommerce.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def gen_sku():
    """Génère un SKU unique"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM produits")
    n = c.fetchone()[0] + 1
    conn.close()
    return f"SKU-{n:04d}"


def gen_code(prefix, table):
    """Génère un code séquentiel"""
    conn = get_db()
    c = conn.cursor()
    c.execute(f"SELECT COUNT(*) FROM {table}")
    n = c.fetchone()[0] + 1
    conn.close()
    return f"{prefix}-{n:04d}"


try:
    from auth import (role_required, admin_required, vendeur_required,
                      staff_required, client_required, log_action)
    from flask_login import current_user
except ImportError:
    def role_required(*r):
        def d(f): return f
        return d
    def admin_required(f): return f
    def vendeur_required(f): return f
    def staff_required(f): return f
    def client_required(f): return f
    def log_action(*a, **k): pass
    current_user = None


def register_crud_routes(app, render_page):
    """Enregistre toutes les routes CRUD"""

    # ==================== PRODUITS ====================
    @app.route('/produits')
    @vendeur_required
    def produits_liste():
        conn = get_db()
        c = conn.cursor()

        search = request.args.get('q', '').strip()
        cat_filter = request.args.get('categorie', '')

        query = """SELECT p.*, cat.nom as cat_nom, m.nom as marque_nom,
                          f.nom as fournisseur_nom
                   FROM produits p
                   LEFT JOIN categories cat ON p.categorie_id = cat.id
                   LEFT JOIN marques m ON p.marque_id = m.id
                   LEFT JOIN fournisseurs f ON p.fournisseur_id = f.id
                   WHERE p.actif=1"""
        params = []

        if search:
            query += " AND (p.nom LIKE ? OR p.sku LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])

        if cat_filter:
            query += " AND p.categorie_id = ?"
            params.append(int(cat_filter))

        query += " ORDER BY p.nom"
        c.execute(query, params)
        rows = c.fetchall()

        # Récupérer les catégories pour le filtre
        c.execute("SELECT id, nom FROM categories WHERE actif=1 ORDER BY nom")
        categories = c.fetchall()

        # Stats
        c.execute("SELECT COUNT(*) FROM produits WHERE actif=1")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM produits WHERE actif=1 AND stock <= stock_alerte")
        alertes = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(stock * prix_vente), 0) FROM produits WHERE actif=1")
        valeur = c.fetchone()[0]
        conn.close()

        cats_opts = "".join(f'<option value="{cat["id"]}" {"selected" if cat_filter == str(cat["id"]) else ""}>{cat["nom"]}</option>' for cat in categories)

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-box"></i> Produits</h2>
            <div class="page-subtitle">Gestion du catalogue</div>
          </div>
          <a href="/produits/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau produit</a>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-box stat-icon"></i>
            <div class="stat-value">{total}</div>
            <div class="stat-label">Produits</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-exclamation-triangle stat-icon"></i>
            <div class="stat-value">{alertes}</div>
            <div class="stat-label">Alertes stock</div>
          </div>
          <div class="stat-card gold">
            <i class="fas fa-coins stat-icon"></i>
            <div class="stat-value">{valeur:,.0f}</div>
            <div class="stat-label">Valeur stock (FCFA)</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Catalogue</h3>
            <form method="GET" style="display:flex;gap:8px;flex-wrap:wrap">
              <input type="text" name="q" value="{search}" placeholder="Rechercher..." style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px;width:200px">
              <select name="categorie" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Toutes catégories</option>
                {cats_opts}
              </select>
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>SKU</th><th>Produit</th><th>Catégorie</th><th>Marque</th>
                  <th>Prix</th><th>Stock</th><th>Vendus</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
        """
        for p in rows:
            stock_badge = 'badge-success'
            if p['stock'] <= 0:
                stock_badge = 'badge-danger'
            elif p['stock'] <= p['stock_alerte']:
                stock_badge = 'badge-warning'

            prix_display = f"{p['prix_promo']:,.0f}" if p['prix_promo'] else f"{p['prix_vente']:,.0f}"
            prix_style = "color:#dc2626;text-decoration:line-through;font-size:0.75rem" if p['prix_promo'] else ""

            content += f"""
            <tr>
              <td><strong>{p['sku']}</strong></td>
              <td>
                <div style="font-weight:700">{p['nom'][:55]}</div>
                <small style="color:#94a3b8">{p['description_courte'][:60] if p['description_courte'] else ''}</small>
              </td>
              <td>{p['cat_nom'] or '-'}</td>
              <td>{p['marque_nom'] or '-'}</td>
              <td><strong style="color:#ff6b35">{prix_display} FCFA</strong>{f'<br><span style="{prix_style}">{p["prix_vente"]:,.0f}</span>' if p['prix_promo'] else ''}</td>
              <td><span class="badge {stock_badge}">{p['stock']}</span></td>
              <td>{p['nb_ventes']}</td>
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
    @vendeur_required
    def produit_nouveau():
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                sku = request.form.get('sku') or gen_sku()
                c.execute("""INSERT INTO produits
                    (sku, nom, description_courte, description_longue,
                     categorie_id, marque_id, fournisseur_id,
                     prix_achat, prix_vente, prix_promo, tva, stock, stock_alerte,
                     unite, poids_kg, image_url, caracteristiques, tags, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (sku, request.form['nom'], request.form.get('description_courte', ''),
                     request.form.get('description_longue', ''),
                     int(request.form['categorie_id']) if request.form.get('categorie_id') else None,
                     int(request.form['marque_id']) if request.form.get('marque_id') else None,
                     int(request.form['fournisseur_id']) if request.form.get('fournisseur_id') else None,
                     float(request.form.get('prix_achat') or 0),
                     float(request.form.get('prix_vente') or 0),
                     float(request.form['prix_promo']) if request.form.get('prix_promo') else None,
                     float(request.form.get('tva') or 18),
                     int(request.form.get('stock') or 0),
                     int(request.form.get('stock_alerte') or 5),
                     request.form.get('unite', 'unité'),
                     float(request.form.get('poids_kg') or 0),
                     request.form.get('image_url', ''),
                     request.form.get('caracteristiques', ''),
                     request.form.get('tags', '')))
                conn.commit()
                conn.close()
                if current_user and current_user.is_authenticated:
                    log_action(current_user.id, 'CREATE_PRODUIT', sku)
                flash(f"✅ Produit {sku} créé avec succès", "success")
                return redirect('/produits')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom FROM categories WHERE actif=1 ORDER BY nom")
        categories = c.fetchall()
        c.execute("SELECT id, nom FROM marques WHERE actif=1 ORDER BY nom")
        marques = c.fetchall()
        c.execute("SELECT id, nom FROM fournisseurs WHERE actif=1 ORDER BY nom")
        fournisseurs = c.fetchall()
        conn.close()

        cats_opts = "".join(f'<option value="{x["id"]}">{x["nom"]}</option>' for x in categories)
        marques_opts = "".join(f'<option value="{x["id"]}">{x["nom"]}</option>' for x in marques)
        four_opts = "".join(f'<option value="{x["id"]}">{x["nom"]}</option>' for x in fournisseurs)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-box-open"></i> Nouveau Produit</h2>
          <a href="/produits" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <h3 style="margin-bottom:20px;color:#ff6b35"><i class="fas fa-info-circle"></i> Informations générales</h3>
            <div class="form-grid">
              <div class="form-group"><label>SKU (laisser vide = auto)</label><input type="text" name="sku" placeholder="SKU-0001"></div>
              <div class="form-group"><label>Nom du produit *</label><input type="text" name="nom" required></div>
              <div class="form-group form-full"><label>Description courte</label><input type="text" name="description_courte" placeholder="Résumé accrocheur..."></div>
              <div class="form-group form-full"><label>Description longue</label><textarea name="description_longue" rows="4"></textarea></div>
              <div class="form-group"><label>Catégorie</label><select name="categorie_id"><option value="">--</option>{cats_opts}</select></div>
              <div class="form-group"><label>Marque</label><select name="marque_id"><option value="">--</option>{marques_opts}</select></div>
              <div class="form-group"><label>Fournisseur</label><select name="fournisseur_id"><option value="">--</option>{four_opts}</select></div>
              <div class="form-group"><label>Unité</label><input type="text" name="unite" value="unité"></div>
            </div>

            <h3 style="margin:25px 0 20px;color:#ff6b35"><i class="fas fa-tag"></i> Prix & Stock</h3>
            <div class="form-grid">
              <div class="form-group"><label>Prix d'achat (FCFA)</label><input type="number" name="prix_achat" value="0" step="0.01"></div>
              <div class="form-group"><label>Prix de vente (FCFA) *</label><input type="number" name="prix_vente" required step="0.01" value="0"></div>
              <div class="form-group"><label>Prix promo (FCFA)</label><input type="number" name="prix_promo" step="0.01" placeholder="Laisser vide"></div>
              <div class="form-group"><label>TVA (%)</label><input type="number" name="tva" value="18" step="0.01"></div>
              <div class="form-group"><label>Stock initial</label><input type="number" name="stock" value="0"></div>
              <div class="form-group"><label>Seuil d'alerte</label><input type="number" name="stock_alerte" value="5"></div>
              <div class="form-group"><label>Poids (kg)</label><input type="number" name="poids_kg" step="0.01" value="0"></div>
            </div>

            <h3 style="margin:25px 0 20px;color:#ff6b35"><i class="fas fa-image"></i> Médias & Détails</h3>
            <div class="form-grid">
              <div class="form-group form-full"><label>URL Image principale</label><input type="url" name="image_url" placeholder="https://..."></div>
              <div class="form-group form-full"><label>Caractéristiques (JSON ou texte)</label><textarea name="caracteristiques" rows="3"></textarea></div>
              <div class="form-group form-full"><label>Tags (séparés par virgule)</label><input type="text" name="tags" placeholder="nouveau, promo, premium"></div>
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
    @vendeur_required
    def produit_detail(pid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT p.*, cat.nom as cat_nom, m.nom as marque_nom,
                            f.nom as fournisseur_nom
                     FROM produits p
                     LEFT JOIN categories cat ON p.categorie_id = cat.id
                     LEFT JOIN marques m ON p.marque_id = m.id
                     LEFT JOIN fournisseurs f ON p.fournisseur_id = f.id
                     WHERE p.id=?""", (pid,))
        p = c.fetchone()
        if not p:
            conn.close()
            flash("Produit introuvable", "danger")
            return redirect('/produits')

        # Dernières ventes
        c.execute("""SELECT lc.*, c.numero, c.date_commande, c.statut
                     FROM lignes_commande lc
                     JOIN commandes c ON lc.commande_id = c.id
                     WHERE lc.produit_id = ?
                     ORDER BY c.date_commande DESC LIMIT 10""", (pid,))
        ventes = c.fetchall()
        conn.close()

        marge = p['prix_vente'] - p['prix_achat'] if p['prix_achat'] else 0
        marge_pct = (marge / p['prix_achat'] * 100) if p['prix_achat'] else 0

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-box"></i> {p['nom'][:60]}</h2>
          <div style="display:flex;gap:10px">
            <a href="/produits/{pid}/modifier" class="btn btn-warning"><i class="fas fa-edit"></i> Modifier</a>
            <a href="/produits" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-tag stat-icon"></i>
            <div class="stat-value" style="font-size:1.3rem">{p['sku']}</div>
            <div class="stat-label">SKU</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-money-bill stat-icon"></i>
            <div class="stat-value">{p['prix_vente']:,.0f}</div>
            <div class="stat-label">Prix (FCFA)</div>
          </div>
          <div class="stat-card gold">
            <i class="fas fa-chart-line stat-icon"></i>
            <div class="stat-value">{marge_pct:.1f}%</div>
            <div class="stat-label">Marge</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-boxes stat-icon"></i>
            <div class="stat-value">{p['stock']}</div>
            <div class="stat-label">Stock</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-shopping-cart stat-icon"></i>
            <div class="stat-value">{p['nb_ventes']}</div>
            <div class="stat-label">Ventes</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Fiche produit</h3></div>
          <div class="form-grid">
            <div><strong>Catégorie :</strong> {p['cat_nom'] or '-'}</div>
            <div><strong>Marque :</strong> {p['marque_nom'] or '-'}</div>
            <div><strong>Fournisseur :</strong> {p['fournisseur_nom'] or '-'}</div>
            <div><strong>Unité :</strong> {p['unite'] or 'unité'}</div>
            <div><strong>Prix d'achat :</strong> {p['prix_achat']:,.0f} FCFA</div>
            <div><strong>Prix de vente :</strong> <span style="color:#ff6b35;font-weight:800">{p['prix_vente']:,.0f} FCFA</span></div>
            <div><strong>TVA :</strong> {p['tva']}%</div>
            <div><strong>Poids :</strong> {p['poids_kg']} kg</div>
          </div>
          {('<p style="margin-top:20px;padding:15px;background:#fff9f3;border-radius:10px;border-left:4px solid #ff6b35"><strong>Description :</strong><br>' + p['description_longue'] + '</p>') if p['description_longue'] else ''}
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-history"></i> Dernières ventes</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Commande</th><th>Date</th><th>Quantité</th><th>Prix unitaire</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for v in ventes:
            badge = 'badge-success' if v['statut'] == 'Livrée' else 'badge-warning'
            content += f"""<tr>
              <td><strong>{v['numero']}</strong></td>
              <td>{v['date_commande'][:10]}</td>
              <td>{v['quantite']}</td>
              <td>{v['prix_unitaire']:,.0f} FCFA</td>
              <td><span class="badge {badge}">{v['statut']}</span></td>
            </tr>"""
        if not ventes:
            content += '<tr><td colspan="5" class="empty"><i class="fas fa-inbox"></i><br>Aucune vente</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='produits', page_title=f"Produit {p['sku']}")

    @app.route('/produits/<int:pid>/modifier', methods=['GET', 'POST'])
    @vendeur_required
    def produit_modifier(pid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE produits SET
                    nom=?, description_courte=?, description_longue=?,
                    categorie_id=?, marque_id=?, fournisseur_id=?,
                    prix_achat=?, prix_vente=?, prix_promo=?, tva=?,
                    stock=?, stock_alerte=?, unite=?, poids_kg=?,
                    image_url=?, caracteristiques=?, tags=?
                    WHERE id=?""",
                    (request.form['nom'], request.form.get('description_courte', ''),
                     request.form.get('description_longue', ''),
                     int(request.form['categorie_id']) if request.form.get('categorie_id') else None,
                     int(request.form['marque_id']) if request.form.get('marque_id') else None,
                     int(request.form['fournisseur_id']) if request.form.get('fournisseur_id') else None,
                     float(request.form.get('prix_achat') or 0),
                     float(request.form.get('prix_vente') or 0),
                     float(request.form['prix_promo']) if request.form.get('prix_promo') else None,
                     float(request.form.get('tva') or 18),
                     int(request.form.get('stock') or 0),
                     int(request.form.get('stock_alerte') or 5),
                     request.form.get('unite', 'unité'),
                     float(request.form.get('poids_kg') or 0),
                     request.form.get('image_url', ''),
                     request.form.get('caracteristiques', ''),
                     request.form.get('tags', ''),
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
        c.execute("SELECT id, nom FROM marques WHERE actif=1 ORDER BY nom")
        marques = c.fetchall()
        c.execute("SELECT id, nom FROM fournisseurs WHERE actif=1 ORDER BY nom")
        fournisseurs = c.fetchall()
        conn.close()

        cats_opts = "".join(f'<option value="{x["id"]}" {"selected" if x["id"]==p["categorie_id"] else ""}>{x["nom"]}</option>' for x in categories)
        marques_opts = "".join(f'<option value="{x["id"]}" {"selected" if x["id"]==p["marque_id"] else ""}>{x["nom"]}</option>' for x in marques)
        four_opts = "".join(f'<option value="{x["id"]}" {"selected" if x["id"]==p["fournisseur_id"] else ""}>{x["nom"]}</option>' for x in fournisseurs)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-edit"></i> Modifier {p['nom'][:50]}</h2>
          <a href="/produits/{pid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{p['nom']}" required></div>
              <div class="form-group"><label>SKU (non modifiable)</label><input type="text" value="{p['sku']}" disabled></div>
              <div class="form-group form-full"><label>Description courte</label><input type="text" name="description_courte" value="{p['description_courte'] or ''}"></div>
              <div class="form-group form-full"><label>Description longue</label><textarea name="description_longue" rows="3">{p['description_longue'] or ''}</textarea></div>
              <div class="form-group"><label>Catégorie</label><select name="categorie_id"><option value="">--</option>{cats_opts}</select></div>
              <div class="form-group"><label>Marque</label><select name="marque_id"><option value="">--</option>{marques_opts}</select></div>
              <div class="form-group"><label>Fournisseur</label><select name="fournisseur_id"><option value="">--</option>{four_opts}</select></div>
              <div class="form-group"><label>Unité</label><input type="text" name="unite" value="{p['unite'] or 'unité'}"></div>
              <div class="form-group"><label>Prix d'achat</label><input type="number" name="prix_achat" step="0.01" value="{p['prix_achat']}"></div>
              <div class="form-group"><label>Prix de vente *</label><input type="number" name="prix_vente" step="0.01" value="{p['prix_vente']}" required></div>
              <div class="form-group"><label>Prix promo</label><input type="number" name="prix_promo" step="0.01" value="{p['prix_promo'] or ''}"></div>
              <div class="form-group"><label>TVA (%)</label><input type="number" name="tva" step="0.01" value="{p['tva']}"></div>
              <div class="form-group"><label>Stock</label><input type="number" name="stock" value="{p['stock']}"></div>
              <div class="form-group"><label>Seuil alerte</label><input type="number" name="stock_alerte" value="{p['stock_alerte']}"></div>
              <div class="form-group"><label>Poids (kg)</label><input type="number" name="poids_kg" step="0.01" value="{p['poids_kg']}"></div>
              <div class="form-group form-full"><label>Image URL</label><input type="url" name="image_url" value="{p['image_url'] or ''}"></div>
              <div class="form-group form-full"><label>Caractéristiques</label><textarea name="caracteristiques" rows="2">{p['caracteristiques'] or ''}</textarea></div>
              <div class="form-group form-full"><label>Tags</label><input type="text" name="tags" value="{p['tags'] or ''}"></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/produits/{pid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/produits/{pid}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer la suppression ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='produits', page_title=f"Modifier produit")

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
    @vendeur_required
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
              <td style="font-size:1.5rem;color:{cat['couleur'] or '#ff6b35'}">
                <i class="fas {cat['icone'] or 'fa-folder'}"></i>
              </td>
              <td><strong>{cat['nom']}</strong></td>
              <td>{cat['description'] or '-'}</td>
              <td><span class="badge badge-info">{cat['nb_produits']}</span></td>
              <td>
                <a href="/categories/{cat['id']}/modifier" class="btn btn-warning btn-sm" title="Modifier"><i class="fas fa-edit"></i></a>
                <a href="/categories/{cat['id']}/supprimer" class="btn btn-danger btn-sm" title="Supprimer" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-tags"></i><br>Aucune catégorie</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='categories', page_title='Catégories')

    @app.route('/categories/nouvelle', methods=['GET', 'POST'])
    @vendeur_required
    def categorie_nouvelle():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                code = request.form.get('code') or gen_code('CAT', 'categories')
                c.execute("""INSERT INTO categories (code, nom, description, icone, couleur, actif)
                    VALUES (?, ?, ?, ?, ?, 1)""",
                    (code, request.form['nom'], request.form.get('description', ''),
                     request.form.get('icone', 'fa-folder'), request.form.get('couleur', '#ff6b35')))
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
                <input type="text" name="icone" value="fa-folder" placeholder="fa-mobile-screen, fa-shirt...">
                <small style="color:#94a3b8;font-size:0.75rem">Voir fontawesome.com/icons</small>
              </div>
              <div class="form-group"><label>Couleur</label><input type="color" name="couleur" value="#ff6b35"></div>
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
    @vendeur_required
    def categorie_modifier(cid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE categories SET code=?, nom=?, description=?, icone=?, couleur=? WHERE id=?""",
                    (request.form['code'], request.form['nom'], request.form.get('description', ''),
                     request.form.get('icone', 'fa-folder'), request.form.get('couleur', '#ff6b35'), cid))
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
              <div class="form-group"><label>Icône FontAwesome</label><input type="text" name="icone" value="{cat['icone'] or 'fa-folder'}"></div>
              <div class="form-group"><label>Couleur</label><input type="color" name="couleur" value="{cat['couleur'] or '#ff6b35'}"></div>
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


    # ==================== MARQUES ====================
    @app.route('/marques')
    @vendeur_required
    def marques_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT m.*,
                     (SELECT COUNT(*) FROM produits WHERE marque_id = m.id AND actif=1) as nb_produits
                     FROM marques m WHERE m.actif=1 ORDER BY m.nom""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-award"></i> Marques</h2>
            <div class="page-subtitle">Marques partenaires</div>
          </div>
          <a href="/marques/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle marque</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Nom</th><th>Pays d'origine</th><th>Site web</th><th>Description</th><th>Produits</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for m in rows:
            content += f"""
            <tr>
              <td><strong>{m['nom']}</strong></td>
              <td><i class="fas fa-flag"></i> {m['pays_origine'] or '-'}</td>
              <td>{f'<a href="{m["site_web"]}" target="_blank" style="color:#ff6b35">{m["site_web"]}</a>' if m['site_web'] else '-'}</td>
              <td>{m['description'] or '-'}</td>
              <td><span class="badge badge-info">{m['nb_produits']}</span></td>
              <td>
                <a href="/marques/{m['id']}/modifier" class="btn btn-warning btn-sm" title="Modifier"><i class="fas fa-edit"></i></a>
                <a href="/marques/{m['id']}/supprimer" class="btn btn-danger btn-sm" title="Supprimer" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-award"></i><br>Aucune marque</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='marques', page_title='Marques')

    @app.route('/marques/nouvelle', methods=['GET', 'POST'])
    @vendeur_required
    def marque_nouvelle():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute("""INSERT INTO marques (nom, description, pays_origine, site_web, actif)
                    VALUES (?, ?, ?, ?, 1)""",
                    (request.form['nom'], request.form.get('description', ''),
                     request.form.get('pays_origine', ''), request.form.get('site_web', '')))
                conn.commit()
                conn.close()
                flash(f"✅ Marque {request.form['nom']} créée", "success")
                return redirect('/marques')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = """
        <div class="page-header">
          <h2><i class="fas fa-award"></i> Nouvelle Marque</h2>
          <a href="/marques" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required placeholder="Samsung, Nike..."></div>
              <div class="form-group"><label>Pays d'origine</label><input type="text" name="pays_origine" placeholder="Corée du Sud"></div>
              <div class="form-group form-full"><label>Site web</label><input type="url" name="site_web" placeholder="https://..."></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="3"></textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/marques" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='marques', page_title='Nouvelle marque')

    @app.route('/marques/<int:mid>/modifier', methods=['GET', 'POST'])
    @vendeur_required
    def marque_modifier(mid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE marques SET nom=?, description=?, pays_origine=?, site_web=? WHERE id=?""",
                    (request.form['nom'], request.form.get('description', ''),
                     request.form.get('pays_origine', ''), request.form.get('site_web', ''), mid))
                conn.commit()
                conn.close()
                flash("✅ Marque mise à jour", "success")
                return redirect('/marques')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM marques WHERE id=?", (mid,))
        m = c.fetchone()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-edit"></i> Modifier {m['nom']}</h2>
          <a href="/marques" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{m['nom']}" required></div>
              <div class="form-group"><label>Pays d'origine</label><input type="text" name="pays_origine" value="{m['pays_origine'] or ''}"></div>
              <div class="form-group form-full"><label>Site web</label><input type="url" name="site_web" value="{m['site_web'] or ''}"></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="3">{m['description'] or ''}</textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/marques" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/marques/{mid}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='marques', page_title='Modifier marque')

    @app.route('/marques/<int:mid>/supprimer')
    @admin_required
    def marque_supprimer(mid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE marques SET actif=0 WHERE id=?", (mid,))
            conn.commit()
            conn.close()
            flash("✅ Marque archivée", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/marques')


    # ==================== FOURNISSEURS ====================
    @app.route('/fournisseurs')
    @vendeur_required
    def fournisseurs_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT f.*,
                     (SELECT COUNT(*) FROM produits WHERE fournisseur_id = f.id AND actif=1) as nb_produits
                     FROM fournisseurs f WHERE f.actif=1 ORDER BY f.nom""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-truck-loading"></i> Fournisseurs</h2>
            <div class="page-subtitle">Partenaires d'approvisionnement</div>
          </div>
          <a href="/fournisseurs/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau fournisseur</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Nom</th><th>Contact</th><th>Téléphone</th><th>Ville</th><th>Délai</th><th>Produits</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for f in rows:
            content += f"""
            <tr>
              <td><strong>{f['code']}</strong></td>
              <td><strong>{f['nom']}</strong></td>
              <td>{f['contact'] or '-'}</td>
              <td><i class="fas fa-phone" style="color:#ff6b35"></i> {f['telephone']}</td>
              <td>{f['ville'] or '-'}</td>
              <td><span class="badge badge-info">{f['delai_livraison_jours']}j</span></td>
              <td><span class="badge badge-success">{f['nb_produits']}</span></td>
              <td>
                <a href="/fournisseurs/{f['id']}/modifier" class="btn btn-warning btn-sm" title="Modifier"><i class="fas fa-edit"></i></a>
                <a href="/fournisseurs/{f['id']}/supprimer" class="btn btn-danger btn-sm" title="Supprimer" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-truck"></i><br>Aucun fournisseur</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='fournisseurs', page_title='Fournisseurs')

    @app.route('/fournisseurs/nouveau', methods=['GET', 'POST'])
    @vendeur_required
    def fournisseur_nouveau():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                code = request.form.get('code') or gen_code('F', 'fournisseurs')
                c.execute("""INSERT INTO fournisseurs
                    (code, nom, contact, telephone, email, adresse, ville, pays, nif,
                     delai_livraison_jours, conditions_paiement, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (code, request.form['nom'], request.form.get('contact', ''),
                     request.form['telephone'], request.form.get('email', ''),
                     request.form.get('adresse', ''), request.form.get('ville', ''),
                     request.form.get('pays', 'Sénégal'), request.form.get('nif', ''),
                     int(request.form.get('delai_livraison_jours') or 7),
                     request.form.get('conditions_paiement', '')))
                conn.commit()
                conn.close()
                flash(f"✅ Fournisseur {code} créé", "success")
                return redirect('/fournisseurs')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = """
        <div class="page-header">
          <h2><i class="fas fa-truck-loading"></i> Nouveau Fournisseur</h2>
          <a href="/fournisseurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code (auto si vide)</label><input type="text" name="code" placeholder="F-0001"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group"><label>Personne à contacter</label><input type="text" name="contact"></div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email"></div>
              <div class="form-group"><label>Adresse</label><input type="text" name="adresse"></div>
              <div class="form-group"><label>Ville</label><input type="text" name="ville" value="Dakar"></div>
              <div class="form-group"><label>Pays</label><input type="text" name="pays" value="Sénégal"></div>
              <div class="form-group"><label>NIF</label><input type="text" name="nif" placeholder="Numéro d'identification fiscale"></div>
              <div class="form-group"><label>Délai livraison (jours)</label><input type="number" name="delai_livraison_jours" value="7"></div>
              <div class="form-group form-full"><label>Conditions de paiement</label><textarea name="conditions_paiement" rows="2" placeholder="Ex : 30% à la commande, 70% à la livraison"></textarea></div>
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
    @vendeur_required
    def fournisseur_modifier(fid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE fournisseurs SET
                    code=?, nom=?, contact=?, telephone=?, email=?, adresse=?,
                    ville=?, pays=?, nif=?, delai_livraison_jours=?, conditions_paiement=?
                    WHERE id=?""",
                    (request.form['code'], request.form['nom'], request.form.get('contact', ''),
                     request.form['telephone'], request.form.get('email', ''),
                     request.form.get('adresse', ''), request.form.get('ville', ''),
                     request.form.get('pays', 'Sénégal'), request.form.get('nif', ''),
                     int(request.form.get('delai_livraison_jours') or 7),
                     request.form.get('conditions_paiement', ''), fid))
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
              <div class="form-group"><label>Délai livraison (j)</label><input type="number" name="delai_livraison_jours" value="{f['delai_livraison_jours']}"></div>
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

    print("[CRUD] ✅ Routes catégories + marques + fournisseurs enregistrées")

    # ==================== CLIENTS ====================
    @app.route('/clients')
    @vendeur_required
    def clients_liste():
        conn = get_db()
        c = conn.cursor()

        search = request.args.get('q', '').strip()
        query = """SELECT cl.*,
                   (SELECT COUNT(*) FROM commandes WHERE client_id = cl.id AND statut != 'Annulée') as nb_commandes_calc
                   FROM clients cl WHERE cl.actif=1"""
        params = []
        if search:
            query += " AND (cl.nom LIKE ? OR cl.prenom LIKE ? OR cl.telephone LIKE ? OR cl.email LIKE ?)"
            params.extend([f'%{search}%'] * 4)
        query += " ORDER BY cl.nom"
        c.execute(query, params)
        rows = c.fetchall()

        c.execute("SELECT COUNT(*) FROM clients WHERE actif=1")
        total = c.fetchone()[0]

        c.execute("SELECT COALESCE(SUM(total_achats), 0) FROM clients WHERE actif=1")
        total_achats = c.fetchone()[0]

        c.execute("SELECT COALESCE(AVG(total_achats), 0) FROM clients WHERE actif=1 AND nb_commandes > 0")
        panier_moyen = c.fetchone()[0]
        conn.close()

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-users"></i> Clients</h2>
            <div class="page-subtitle">Base clients de la boutique</div>
          </div>
          <a href="/clients/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau client</a>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-users stat-icon"></i>
            <div class="stat-value">{total}</div>
            <div class="stat-label">Clients actifs</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-shopping-bag stat-icon"></i>
            <div class="stat-value">{total_achats:,.0f}</div>
            <div class="stat-label">CA total (FCFA)</div>
          </div>
          <div class="stat-card gold">
            <i class="fas fa-chart-line stat-icon"></i>
            <div class="stat-value">{panier_moyen:,.0f}</div>
            <div class="stat-label">Panier moyen</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Liste des clients</h3>
            <form method="GET" style="display:flex;gap:8px">
              <input type="text" name="q" value="{search}" placeholder="Rechercher..." style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px;width:250px">
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Nom</th><th>Contact</th><th>Ville</th><th>Points</th><th>Achats</th><th>Commandes</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for cl in rows:
            points_badge = 'badge-gold' if cl['points_fidelite'] > 300 else 'badge-info'
            content += f"""
            <tr>
              <td><strong>{cl['code']}</strong></td>
              <td>
                <div style="font-weight:700">{cl['nom']} {cl['prenom']}</div>
                <small style="color:#94a3b8">{cl['email'] or '-'}</small>
              </td>
              <td><i class="fas fa-phone" style="color:#ff6b35"></i> {cl['telephone']}</td>
              <td>{cl['ville'] or '-'}</td>
              <td><span class="badge {points_badge}">{cl['points_fidelite']} pts</span></td>
              <td><strong style="color:#10b981">{cl['total_achats']:,.0f}</strong> FCFA</td>
              <td><span class="badge badge-info">{cl['nb_commandes_calc']}</span></td>
              <td>
                <a href="/clients/{cl['id']}" class="btn btn-info btn-sm" title="Voir"><i class="fas fa-eye"></i></a>
                <a href="/clients/{cl['id']}/modifier" class="btn btn-warning btn-sm" title="Modifier"><i class="fas fa-edit"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-users"></i><br>Aucun client</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='clients', page_title='Clients')

    @app.route('/clients/nouveau', methods=['GET', 'POST'])
    @vendeur_required
    def client_nouveau():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                code = request.form.get('code') or gen_code('CLI', 'clients')
                c.execute("""INSERT INTO clients
                    (code, nom, prenom, email, telephone, adresse, ville, region,
                     pays, date_naissance, genre, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (code, request.form['nom'], request.form['prenom'],
                     request.form.get('email', ''), request.form['telephone'],
                     request.form.get('adresse', ''), request.form.get('ville', ''),
                     request.form.get('region', ''), request.form.get('pays', 'Sénégal'),
                     request.form.get('date_naissance', ''), request.form.get('genre', '')))
                conn.commit()
                conn.close()
                flash(f"✅ Client {code} créé", "success")
                return redirect('/clients')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = """
        <div class="page-header">
          <h2><i class="fas fa-user-plus"></i> Nouveau Client</h2>
          <a href="/clients" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code (auto si vide)</label><input type="text" name="code" placeholder="CLI-0001"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" required></div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email"></div>
              <div class="form-group"><label>Date de naissance</label><input type="date" name="date_naissance"></div>
              <div class="form-group"><label>Genre</label>
                <select name="genre"><option value="">--</option><option value="M">Masculin</option><option value="F">Féminin</option></select>
              </div>
              <div class="form-group"><label>Adresse</label><input type="text" name="adresse"></div>
              <div class="form-group"><label>Ville</label><input type="text" name="ville" value="Dakar"></div>
              <div class="form-group"><label>Région</label><input type="text" name="region" value="Dakar"></div>
              <div class="form-group"><label>Pays</label><input type="text" name="pays" value="Sénégal"></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/clients" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='clients', page_title='Nouveau client')

    @app.route('/clients/<int:cid>')
    @vendeur_required
    def client_detail(cid):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM clients WHERE id=?", (cid,))
        cl = c.fetchone()
        if not cl:
            conn.close()
            flash("Client introuvable", "danger")
            return redirect('/clients')

        c.execute("""SELECT * FROM commandes WHERE client_id = ?
                     ORDER BY date_commande DESC LIMIT 20""", (cid,))
        commandes = c.fetchall()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user"></i> {cl['nom']} {cl['prenom']}</h2>
          <div style="display:flex;gap:10px">
            <a href="/clients/{cid}/modifier" class="btn btn-warning"><i class="fas fa-edit"></i> Modifier</a>
            <a href="/clients" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-id-card stat-icon"></i>
            <div class="stat-value" style="font-size:1.2rem">{cl['code']}</div>
            <div class="stat-label">Code client</div>
          </div>
          <div class="stat-card gold">
            <i class="fas fa-star stat-icon"></i>
            <div class="stat-value">{cl['points_fidelite']}</div>
            <div class="stat-label">Points fidélité</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-coins stat-icon"></i>
            <div class="stat-value">{cl['total_achats']:,.0f}</div>
            <div class="stat-label">CA total (FCFA)</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-shopping-cart stat-icon"></i>
            <div class="stat-value">{cl['nb_commandes']}</div>
            <div class="stat-label">Commandes</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
          <div class="form-grid">
            <div><strong>Téléphone :</strong> {cl['telephone']}</div>
            <div><strong>Email :</strong> {cl['email'] or '-'}</div>
            <div><strong>Adresse :</strong> {cl['adresse'] or '-'}</div>
            <div><strong>Ville :</strong> {cl['ville'] or '-'}, {cl['region'] or ''}</div>
            <div><strong>Genre :</strong> {'Masculin' if cl['genre'] == 'M' else ('Féminin' if cl['genre'] == 'F' else '-')}</div>
            <div><strong>Naissance :</strong> {cl['date_naissance'] or '-'}</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-history"></i> Commandes récentes</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Date</th><th>Total</th><th>Paiement</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for cmd in commandes:
            badge = 'badge-success' if cmd['statut'] == 'Livrée' else 'badge-warning'
            content += f"""<tr>
              <td><strong>{cmd['numero']}</strong></td>
              <td>{cmd['date_commande'][:10]}</td>
              <td><strong>{cmd['total']:,.0f}</strong> FCFA</td>
              <td>{cmd['mode_paiement'] or '-'}</td>
              <td><span class="badge {badge}">{cmd['statut']}</span></td>
            </tr>"""
        if not commandes:
            content += '<tr><td colspan="5" class="empty"><i class="fas fa-inbox"></i><br>Aucune commande</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='clients', page_title=f"Client {cl['code']}")

    @app.route('/clients/<int:cid>/modifier', methods=['GET', 'POST'])
    @vendeur_required
    def client_modifier(cid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE clients SET
                    nom=?, prenom=?, email=?, telephone=?, adresse=?, ville=?, region=?,
                    pays=?, date_naissance=?, genre=? WHERE id=?""",
                    (request.form['nom'], request.form['prenom'], request.form.get('email', ''),
                     request.form['telephone'], request.form.get('adresse', ''),
                     request.form.get('ville', ''), request.form.get('region', ''),
                     request.form.get('pays', 'Sénégal'), request.form.get('date_naissance', ''),
                     request.form.get('genre', ''), cid))
                conn.commit()
                conn.close()
                flash("✅ Client mis à jour", "success")
                return redirect(f'/clients/{cid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM clients WHERE id=?", (cid,))
        cl = c.fetchone()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user-edit"></i> Modifier {cl['nom']} {cl['prenom']}</h2>
          <a href="/clients/{cid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code (non modifiable)</label><input type="text" value="{cl['code']}" disabled></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{cl['nom']}" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" value="{cl['prenom']}" required></div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" value="{cl['telephone']}" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email" value="{cl['email'] or ''}"></div>
              <div class="form-group"><label>Date naissance</label><input type="date" name="date_naissance" value="{cl['date_naissance'] or ''}"></div>
              <div class="form-group"><label>Genre</label>
                <select name="genre">
                  <option value="">--</option>
                  <option value="M" {"selected" if cl['genre'] == 'M' else ""}>Masculin</option>
                  <option value="F" {"selected" if cl['genre'] == 'F' else ""}>Féminin</option>
                </select>
              </div>
              <div class="form-group"><label>Adresse</label><input type="text" name="adresse" value="{cl['adresse'] or ''}"></div>
              <div class="form-group"><label>Ville</label><input type="text" name="ville" value="{cl['ville'] or ''}"></div>
              <div class="form-group"><label>Région</label><input type="text" name="region" value="{cl['region'] or ''}"></div>
              <div class="form-group"><label>Pays</label><input type="text" name="pays" value="{cl['pays'] or 'Sénégal'}"></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/clients/{cid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='clients', page_title='Modifier client')


    # ==================== PROMOTIONS ====================
    @app.route('/promotions')
    @vendeur_required
    def promotions_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM promotions WHERE actif=1 ORDER BY date_fin DESC")
        rows = c.fetchall()
        conn.close()

        today = datetime.now().date().isoformat()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-percent"></i> Promotions</h2>
            <div class="page-subtitle">Codes promo & réductions</div>
          </div>
          <a href="/promotions/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle promo</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Nom</th><th>Type</th><th>Valeur</th><th>Min. commande</th><th>Validité</th><th>Utilisations</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for p in rows:
            is_active = p['date_fin'] >= today and p['date_debut'] <= today
            status_badge = 'badge-success' if is_active else 'badge-danger'
            status_text = 'Active' if is_active else 'Expirée'

            if p['type'] == 'pourcentage':
                valeur_display = f"{p['valeur']}%"
            elif p['type'] == 'montant':
                valeur_display = f"{p['valeur']:,.0f} FCFA"
            else:
                valeur_display = "Livraison gratuite"

            content += f"""
            <tr>
              <td><strong style="color:#ff6b35;font-family:monospace">{p['code']}</strong></td>
              <td>{p['nom']}</td>
              <td><span class="badge badge-info">{p['type']}</span></td>
              <td><strong>{valeur_display}</strong></td>
              <td>{p['montant_min']:,.0f} FCFA</td>
              <td>
                <small>{p['date_debut']} → {p['date_fin']}</small><br>
                <span class="badge {status_badge}">{status_text}</span>
              </td>
              <td>{p['nb_utilisations']}{f' / {p["limite_utilisation"]}' if p['limite_utilisation'] else ''}</td>
              <td>
                <a href="/promotions/{p['id']}/modifier" class="btn btn-warning btn-sm" title="Modifier"><i class="fas fa-edit"></i></a>
                <a href="/promotions/{p['id']}/supprimer" class="btn btn-danger btn-sm" title="Supprimer" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-percent"></i><br>Aucune promotion</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='promotions', page_title='Promotions')

    @app.route('/promotions/nouvelle', methods=['GET', 'POST'])
    @vendeur_required
    def promotion_nouvelle():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute("""INSERT INTO promotions
                    (code, nom, description, type, valeur, montant_min,
                     date_debut, date_fin, limite_utilisation, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (request.form['code'].upper(), request.form['nom'],
                     request.form.get('description', ''),
                     request.form['type'],
                     float(request.form.get('valeur') or 0),
                     float(request.form.get('montant_min') or 0),
                     request.form['date_debut'], request.form['date_fin'],
                     int(request.form['limite_utilisation']) if request.form.get('limite_utilisation') else None))
                conn.commit()
                conn.close()
                flash(f"✅ Promotion {request.form['code'].upper()} créée", "success")
                return redirect('/promotions')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        today = datetime.now().date().isoformat()
        future = (datetime.now().date() + timedelta(days=30)).isoformat()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-percent"></i> Nouvelle Promotion</h2>
          <a href="/promotions" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code promo * (majuscules)</label><input type="text" name="code" required placeholder="PROMO2026" style="text-transform:uppercase"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required placeholder="Promo d'été"></div>
              <div class="form-group form-full"><label>Description</label><input type="text" name="description"></div>
              <div class="form-group"><label>Type *</label>
                <select name="type" required>
                  <option value="pourcentage">Pourcentage (%)</option>
                  <option value="montant">Montant fixe (FCFA)</option>
                  <option value="livraison">Livraison gratuite</option>
                </select>
              </div>
              <div class="form-group"><label>Valeur *</label><input type="number" name="valeur" step="0.01" value="0" required></div>
              <div class="form-group"><label>Montant minimum commande</label><input type="number" name="montant_min" step="0.01" value="0"></div>
              <div class="form-group"><label>Limite d'utilisation</label><input type="number" name="limite_utilisation" placeholder="Illimité si vide"></div>
              <div class="form-group"><label>Date début *</label><input type="date" name="date_debut" value="{today}" required></div>
              <div class="form-group"><label>Date fin *</label><input type="date" name="date_fin" value="{future}" required></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/promotions" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='promotions', page_title='Nouvelle promotion')

    @app.route('/promotions/<int:pid>/modifier', methods=['GET', 'POST'])
    @vendeur_required
    def promotion_modifier(pid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE promotions SET
                    code=?, nom=?, description=?, type=?, valeur=?, montant_min=?,
                    date_debut=?, date_fin=?, limite_utilisation=? WHERE id=?""",
                    (request.form['code'].upper(), request.form['nom'],
                     request.form.get('description', ''),
                     request.form['type'],
                     float(request.form.get('valeur') or 0),
                     float(request.form.get('montant_min') or 0),
                     request.form['date_debut'], request.form['date_fin'],
                     int(request.form['limite_utilisation']) if request.form.get('limite_utilisation') else None,
                     pid))
                conn.commit()
                conn.close()
                flash("✅ Promotion mise à jour", "success")
                return redirect('/promotions')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM promotions WHERE id=?", (pid,))
        p = c.fetchone()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-edit"></i> Modifier {p['code']}</h2>
          <a href="/promotions" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code *</label><input type="text" name="code" value="{p['code']}" required style="text-transform:uppercase"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{p['nom']}" required></div>
              <div class="form-group form-full"><label>Description</label><input type="text" name="description" value="{p['description'] or ''}"></div>
              <div class="form-group"><label>Type *</label>
                <select name="type" required>
                  <option value="pourcentage" {"selected" if p['type'] == 'pourcentage' else ""}>Pourcentage (%)</option>
                  <option value="montant" {"selected" if p['type'] == 'montant' else ""}>Montant fixe (FCFA)</option>
                  <option value="livraison" {"selected" if p['type'] == 'livraison' else ""}>Livraison gratuite</option>
                </select>
              </div>
              <div class="form-group"><label>Valeur *</label><input type="number" name="valeur" step="0.01" value="{p['valeur']}" required></div>
              <div class="form-group"><label>Montant minimum</label><input type="number" name="montant_min" step="0.01" value="{p['montant_min']}"></div>
              <div class="form-group"><label>Limite d'utilisation</label><input type="number" name="limite_utilisation" value="{p['limite_utilisation'] or ''}"></div>
              <div class="form-group"><label>Date début *</label><input type="date" name="date_debut" value="{p['date_debut']}" required></div>
              <div class="form-group"><label>Date fin *</label><input type="date" name="date_fin" value="{p['date_fin']}" required></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/promotions" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/promotions/{pid}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='promotions', page_title='Modifier promotion')

    @app.route('/promotions/<int:pid>/supprimer')
    @admin_required
    def promotion_supprimer(pid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE promotions SET actif=0 WHERE id=?", (pid,))
            conn.commit()
            conn.close()
            flash("✅ Promotion archivée", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/promotions')

    print("[CRUD] ✅ Routes clients + promotions enregistrées")
