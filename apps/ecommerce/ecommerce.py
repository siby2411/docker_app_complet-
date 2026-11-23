"""
Module E-Commerce : Boutique, Panier, Commandes, Paiement, Livraison
Cœur métier de la plateforme Omega Shop
"""
from flask import render_template_string, request, redirect, flash, jsonify, session
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "/app/data/ecommerce.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def gen_numero(prefix, table):
    conn = get_db()
    c = conn.cursor()
    year = datetime.now().year
    c.execute(f"SELECT COUNT(*) FROM {table}")
    n = c.fetchone()[0] + 1
    conn.close()
    return f"{prefix}-{year}-{n:04d}"


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


def _get_client_for_user(user):
    """Récupère la fiche client liée à l'utilisateur connecté"""
    if not user:
        return None
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM clients WHERE user_id=? LIMIT 1", (user.id,))
    cl = c.fetchone()
    if cl:
        conn.close()
        return cl
    # Fallback par email
    if hasattr(user, 'email') and user.email:
        c.execute("SELECT * FROM clients WHERE email=? LIMIT 1", (user.email,))
        cl = c.fetchone()
        if cl:
            conn.close()
            return cl
    # Fallback par username client1 -> id 1
    if user.username.startswith('client'):
        try:
            cid = int(user.username.replace('client', ''))
            c.execute("SELECT * FROM clients WHERE id=?", (cid,))
            cl = c.fetchone()
            if cl:
                conn.close()
                return cl
        except Exception:
            pass
    conn.close()
    return None


def register_ecommerce_routes(app, render_page):
    """Enregistre les routes e-commerce"""

    # ==================== BOUTIQUE (catalogue client) ====================
    @app.route('/boutique')
    @client_required
    def boutique():
        conn = get_db()
        c = conn.cursor()

        search = request.args.get('q', '').strip()
        cat_id = request.args.get('cat', '')
        sort = request.args.get('sort', 'recent')

        query = """SELECT p.*, cat.nom as cat_nom, m.nom as marque_nom
                   FROM produits p
                   LEFT JOIN categories cat ON p.categorie_id = cat.id
                   LEFT JOIN marques m ON p.marque_id = m.id
                   WHERE p.actif=1 AND p.stock > 0"""
        params = []
        if search:
            query += " AND (p.nom LIKE ? OR p.description_courte LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])
        if cat_id:
            query += " AND p.categorie_id = ?"
            params.append(int(cat_id))

        if sort == 'prix_asc':
            query += " ORDER BY COALESCE(p.prix_promo, p.prix_vente) ASC"
        elif sort == 'prix_desc':
            query += " ORDER BY COALESCE(p.prix_promo, p.prix_vente) DESC"
        elif sort == 'populaire':
            query += " ORDER BY p.nb_ventes DESC"
        else:
            query += " ORDER BY p.created_at DESC"

        c.execute(query, params)
        produits = c.fetchall()

        c.execute("SELECT * FROM categories WHERE actif=1 ORDER BY nom")
        categories = c.fetchall()

        # Compter panier
        client = _get_client_for_user(current_user)
        nb_panier = 0
        if client:
            c.execute("SELECT COALESCE(SUM(quantite), 0) FROM paniers WHERE client_id=?", (client['id'],))
            nb_panier = c.fetchone()[0]
        conn.close()

        cats_html = "".join(f'<a href="/boutique?cat={cat["id"]}" class="cat-chip {"active" if cat_id == str(cat["id"]) else ""}"><i class="fas {cat["icone"] or "fa-folder"}"></i> {cat["nom"]}</a>' for cat in categories)

        content = f"""
        <div class="hero" style="padding:35px 40px">
          <h1>Découvrez nos <span>meilleures offres</span> 🛍️</h1>
          <p>Livraison rapide à Dakar et dans tout le Sénégal · Paiement sécurisé · Satisfait ou remboursé</p>
        </div>

        <div style="display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap;align-items:center">
          <a href="/boutique" class="cat-chip {"active" if not cat_id else ""}"><i class="fas fa-th"></i> Toutes</a>
          {cats_html}
        </div>

        <div class="card" style="padding:20px">
          <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:center">
            <input type="hidden" name="cat" value="{cat_id}">
            <input type="text" name="q" value="{search}" placeholder="Rechercher un produit..." style="flex:1;min-width:200px;padding:12px 16px;border:2px solid #f1f5f9;border-radius:10px;font-size:0.95rem">
            <select name="sort" style="padding:12px 16px;border:2px solid #f1f5f9;border-radius:10px;font-weight:600">
              <option value="recent" {"selected" if sort == "recent" else ""}>Plus récents</option>
              <option value="prix_asc" {"selected" if sort == "prix_asc" else ""}>Prix croissant</option>
              <option value="prix_desc" {"selected" if sort == "prix_desc" else ""}>Prix décroissant</option>
              <option value="populaire" {"selected" if sort == "populaire" else ""}>Populaires</option>
            </select>
            <button type="submit" class="btn btn-primary"><i class="fas fa-search"></i> Rechercher</button>
          </form>
        </div>

        <div style="display:flex;justify-content:space-between;align-items:center;margin:20px 0 15px">
          <div style="font-weight:800;font-size:1.1rem;color:#1a1a2e">{len(produits)} produit{'s' if len(produits) > 1 else ''} trouvé{'s' if len(produits) > 1 else ''}</div>
          <a href="/mon-panier" class="btn btn-gold"><i class="fas fa-shopping-basket"></i> Panier ({nb_panier})</a>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:22px">
        """

        for p in produits:
            prix = p['prix_promo'] if p['prix_promo'] else p['prix_vente']
            has_promo = p['prix_promo'] and p['prix_promo'] < p['prix_vente']
            remise_pct = int((1 - p['prix_promo'] / p['prix_vente']) * 100) if has_promo else 0
            promo_badge = f'<div class="prod-promo">-{remise_pct}%</div>' if has_promo else ''
            new_badge = '<div class="prod-new">NOUVEAU</div>' if p['nouveau'] else ''
            stock_badge = ''
            if p['stock'] <= 3:
                stock_badge = f'<div style="position:absolute;bottom:10px;left:10px;background:#fef3c7;color:#92400e;padding:4px 10px;border-radius:6px;font-size:0.7rem;font-weight:800">Plus que {p["stock"]} !</div>'

            content += f"""
            <div class="product-card">
              <div class="prod-image">
                <i class="fas fa-image" style="font-size:3rem;color:#fed7aa"></i>
                {promo_badge}
                {new_badge}
                {stock_badge}
              </div>
              <div class="prod-body">
                <div class="prod-cat">{p['cat_nom'] or 'Général'}</div>
                <div class="prod-name">{p['nom'][:60]}</div>
                <div class="prod-desc">{p['description_courte'][:70] if p['description_courte'] else ''}</div>
                <div class="prod-price">
                  <span class="price-current">{prix:,.0f} FCFA</span>
                  {f'<span class="price-old">{p["prix_vente"]:,.0f}</span>' if has_promo else ''}
                </div>
                <a href="/produit/{p['id']}" class="btn btn-primary" style="width:100%;justify-content:center;margin-top:12px">
                  <i class="fas fa-eye"></i> Voir le produit
                </a>
              </div>
            </div>
            """

        if not produits:
            content += """
            <div class="empty" style="grid-column:1/-1">
              <i class="fas fa-search"></i>
              <h3>Aucun produit trouvé</h3>
              <p>Essayez de modifier vos filtres de recherche</p>
            </div>
            """

        content += """
        </div>
        <style>
        .cat-chip{padding:9px 16px;background:white;border-radius:30px;text-decoration:none;color:#475569;font-weight:700;font-size:0.82rem;box-shadow:0 3px 10px rgba(0,0,0,0.05);transition:0.3s;display:inline-flex;align-items:center;gap:7px;border:2px solid transparent}
        .cat-chip:hover{background:#fff4e6;color:#ff6b35}
        .cat-chip.active{background:linear-gradient(135deg,#ff6b35,#f7931e);color:white;box-shadow:0 5px 15px rgba(255,107,53,0.35)}
        .product-card{background:white;border-radius:18px;overflow:hidden;box-shadow:0 6px 20px rgba(255,107,53,0.06);transition:0.3s;display:flex;flex-direction:column}
        .product-card:hover{transform:translateY(-6px);box-shadow:0 15px 35px rgba(255,107,53,0.18)}
        .prod-image{position:relative;height:180px;background:linear-gradient(135deg,#fff4e6,#ffe9d1);display:flex;justify-content:center;align-items:center}
        .prod-promo{position:absolute;top:12px;right:12px;background:linear-gradient(135deg,#dc2626,#ef4444);color:white;padding:5px 12px;border-radius:20px;font-size:0.72rem;font-weight:900}
        .prod-new{position:absolute;top:12px;left:12px;background:linear-gradient(135deg,#10b981,#059669);color:white;padding:5px 10px;border-radius:20px;font-size:0.7rem;font-weight:900}
        .prod-body{padding:16px}
        .prod-cat{font-size:0.7rem;color:#ff6b35;font-weight:800;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px}
        .prod-name{font-size:0.95rem;font-weight:800;color:#1a1a2e;margin-bottom:6px;min-height:38px;line-height:1.3}
        .prod-desc{font-size:0.78rem;color:#64748b;margin-bottom:10px;min-height:32px}
        .prod-price{margin-top:8px}
        .price-current{font-size:1.15rem;font-weight:900;color:#ff6b35}
        .price-old{font-size:0.82rem;color:#94a3b8;text-decoration:line-through;margin-left:8px}
        </style>
        """
        return render_page(content, active='boutique', page_title='Boutique')

    # ==================== DÉTAIL PRODUIT (vue client) ====================
    @app.route('/produit/<int:pid>')
    @client_required
    def produit_public(pid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT p.*, cat.nom as cat_nom, m.nom as marque_nom
                     FROM produits p
                     LEFT JOIN categories cat ON p.categorie_id = cat.id
                     LEFT JOIN marques m ON p.marque_id = m.id
                     WHERE p.id=? AND p.actif=1""", (pid,))
        p = c.fetchone()
        if not p:
            conn.close()
            flash("Produit introuvable", "danger")
            return redirect('/boutique')

        # Produits similaires
        c.execute("""SELECT * FROM produits WHERE categorie_id=? AND id!=? AND actif=1
                     AND stock > 0 LIMIT 4""", (p['categorie_id'], pid))
        similaires = c.fetchall()

        # Avis
        c.execute("""SELECT a.*, cl.nom, cl.prenom FROM avis a
                     JOIN clients cl ON a.client_id = cl.id
                     WHERE a.produit_id=? AND a.approuve=1
                     ORDER BY a.created_at DESC LIMIT 5""", (pid,))
        avis = c.fetchall()
        conn.close()

        prix = p['prix_promo'] if p['prix_promo'] else p['prix_vente']
        has_promo = p['prix_promo'] and p['prix_promo'] < p['prix_vente']

        content = f"""
        <div style="margin-bottom:15px;font-size:0.85rem;color:#64748b">
          <a href="/boutique" style="color:#ff6b35;text-decoration:none">Boutique</a>
          <i class="fas fa-chevron-right" style="margin:0 8px;font-size:0.7rem"></i>
          <a href="/boutique?cat={p['categorie_id']}" style="color:#ff6b35;text-decoration:none">{p['cat_nom'] or 'Général'}</a>
          <i class="fas fa-chevron-right" style="margin:0 8px;font-size:0.7rem"></i>
          <span>{p['nom'][:40]}</span>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:30px;margin-bottom:30px">
          <div class="card" style="display:flex;justify-content:center;align-items:center;min-height:400px;background:linear-gradient(135deg,#fff4e6,#ffe9d1)">
            <i class="fas fa-image" style="font-size:8rem;color:#fed7aa"></i>
          </div>
          <div>
            <div style="font-size:0.75rem;color:#ff6b35;font-weight:800;text-transform:uppercase;letter-spacing:1px">{p['marque_nom'] or 'Sans marque'}</div>
            <h1 style="font-size:1.8rem;margin:10px 0;color:#1a1a2e;font-weight:900">{p['nom']}</h1>
            <div style="display:flex;gap:8px;align-items:center;margin-bottom:15px">
              <div style="color:#ffb800;font-size:1.1rem">{'★' * int(p['note_moyenne'] or 4)}{'☆' * (5 - int(p['note_moyenne'] or 4))}</div>
              <span style="color:#64748b;font-size:0.85rem">({p['nb_avis']} avis)</span>
            </div>
            <p style="color:#64748b;line-height:1.7;margin-bottom:20px">{p['description_courte'] or ''}</p>

            <div style="background:#fff4e6;padding:20px;border-radius:14px;margin-bottom:20px">
              <div style="display:flex;align-items:baseline;gap:15px">
                <span style="font-size:2.2rem;font-weight:900;color:#ff6b35">{prix:,.0f} FCFA</span>
                {f'<span style="font-size:1.2rem;color:#94a3b8;text-decoration:line-through">{p["prix_vente"]:,.0f}</span>' if has_promo else ''}
                {f'<span class="badge badge-danger">-{int((1 - p["prix_promo"]/p["prix_vente"])*100)}%</span>' if has_promo else ''}
              </div>
              <div style="margin-top:10px;font-size:0.85rem">
                {f'<span style="color:#10b981;font-weight:700"><i class="fas fa-check-circle"></i> En stock ({p["stock"]} disponibles)</span>' if p['stock'] > 3 else f'<span style="color:#f59e0b;font-weight:700"><i class="fas fa-exclamation-triangle"></i> Plus que {p["stock"]} en stock !</span>'}
              </div>
            </div>

            <form method="POST" action="/panier/ajouter/{p['id']}" style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
              <div style="display:flex;align-items:center;border:2px solid #f1f5f9;border-radius:12px;overflow:hidden">
                <button type="button" onclick="this.nextElementSibling.stepDown()" style="padding:12px 16px;background:#f8fafc;border:none;font-size:1.1rem;cursor:pointer">−</button>
                <input type="number" name="quantite" value="1" min="1" max="{p['stock']}" style="width:70px;padding:12px;text-align:center;border:none;font-weight:800;font-size:1rem">
                <button type="button" onclick="this.previousElementSibling.stepUp()" style="padding:12px 16px;background:#f8fafc;border:none;font-size:1.1rem;cursor:pointer">+</button>
              </div>
              <button type="submit" class="btn btn-primary" style="padding:14px 30px;font-size:1rem">
                <i class="fas fa-cart-plus"></i> Ajouter au panier
              </button>
            </form>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Description détaillée</h3></div>
          <p style="color:#475569;line-height:1.8">{p['description_longue'] or 'Aucune description détaillée disponible.'}</p>
        </div>
        """

        if similaires:
            content += '<div class="card"><div class="card-header"><h3><i class="fas fa-fire"></i> Produits similaires</h3></div><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:18px">'
            for s in similaires:
                sp = s['prix_promo'] if s['prix_promo'] else s['prix_vente']
                content += f"""
                <a href="/produit/{s['id']}" style="text-decoration:none;color:inherit;background:#fff9f3;border-radius:12px;padding:15px;transition:0.3s;display:block">
                  <div style="height:100px;background:linear-gradient(135deg,#fff4e6,#ffe9d1);border-radius:8px;display:flex;justify-content:center;align-items:center;margin-bottom:10px">
                    <i class="fas fa-image" style="font-size:2rem;color:#fed7aa"></i>
                  </div>
                  <div style="font-weight:700;font-size:0.85rem;margin-bottom:6px">{s['nom'][:40]}</div>
                  <div style="color:#ff6b35;font-weight:900">{sp:,.0f} FCFA</div>
                </a>
                """
            content += '</div></div>'

        return render_page(content, active='boutique', page_title=p['nom'][:50])

    # ==================== AJOUTER AU PANIER ====================
    @app.route('/panier/ajouter/<int:pid>', methods=['POST'])
    @client_required
    def panier_ajouter(pid):
        client = _get_client_for_user(current_user)
        if not client:
            flash("Profil client introuvable. Contactez le support.", "danger")
            return redirect('/boutique')

        quantite = int(request.form.get('quantite') or 1)

        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT * FROM produits WHERE id=? AND actif=1", (pid,))
        p = c.fetchone()
        if not p:
            conn.close()
            flash("Produit introuvable", "danger")
            return redirect('/boutique')

        if quantite > p['stock']:
            conn.close()
            flash(f"Stock insuffisant ({p['stock']} disponibles)", "warning")
            return redirect(f'/produit/{pid}')

        prix = p['prix_promo'] if p['prix_promo'] else p['prix_vente']

        # Vérifier si déjà dans panier
        c.execute("SELECT * FROM paniers WHERE client_id=? AND produit_id=?", (client['id'], pid))
        existing = c.fetchone()

        if existing:
            nouvelle_qte = existing['quantite'] + quantite
            if nouvelle_qte > p['stock']:
                nouvelle_qte = p['stock']
            c.execute("UPDATE paniers SET quantite=? WHERE id=?", (nouvelle_qte, existing['id']))
        else:
            c.execute("""INSERT INTO paniers (client_id, produit_id, quantite, prix_unitaire)
                         VALUES (?, ?, ?, ?)""", (client['id'], pid, quantite, prix))

        conn.commit()
        conn.close()
        flash(f"✅ {p['nom'][:40]} ajouté au panier", "success")
        return redirect(request.referrer or '/boutique')

    # ==================== MON PANIER ====================
    @app.route('/mon-panier')
    @client_required
    def mon_panier():
        client = _get_client_for_user(current_user)
        if not client:
            flash("Profil client introuvable", "danger")
            return redirect('/boutique')

        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT pa.*, p.nom, p.sku, p.stock, p.image_url
                     FROM paniers pa
                     JOIN produits p ON pa.produit_id = p.id
                     WHERE pa.client_id = ?
                     ORDER BY pa.created_at DESC""", (client['id'],))
        items = c.fetchall()

        # Charger les catégories pour suggestions
        c.execute("SELECT * FROM produits WHERE actif=1 AND stock > 0 ORDER BY nb_ventes DESC LIMIT 4")
        suggestions = c.fetchall()
        conn.close()

        sous_total = sum(item['quantite'] * item['prix_unitaire'] for item in items)
        frais_livraison = 2000 if sous_total < 50000 else 0
        total = sous_total + frais_livraison

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-shopping-basket"></i> Mon Panier</h2>
            <div class="page-subtitle">{len(items)} article{'s' if len(items) > 1 else ''} dans votre panier</div>
          </div>
          <a href="/boutique" class="btn btn-info"><i class="fas fa-store"></i> Continuer les achats</a>
        </div>
        """

        if not items:
            content += """
            <div class="card">
              <div class="empty">
                <i class="fas fa-shopping-basket"></i>
                <h3>Votre panier est vide</h3>
                <p>Découvrez nos produits et faites vos premiers achats</p>
                <a href="/boutique" class="btn btn-primary" style="margin-top:20px"><i class="fas fa-store"></i> Aller à la boutique</a>
              </div>
            </div>
            """
        else:
            content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:25px;align-items:start">'
            content += '<div class="card"><div class="table-wrap"><table><thead><tr><th>Produit</th><th>Prix unitaire</th><th>Quantité</th><th>Total</th><th></th></tr></thead><tbody>'

            for item in items:
                content += f"""
                <tr>
                  <td>
                    <div style="font-weight:700">{item['nom'][:50]}</div>
                    <small style="color:#94a3b8">SKU: {item['sku']}</small>
                  </td>
                  <td><strong>{item['prix_unitaire']:,.0f} FCFA</strong></td>
                  <td>
                    <form method="POST" action="/panier/modifier/{item['id']}" style="display:flex;align-items:center;gap:5px">
                      <input type="number" name="quantite" value="{item['quantite']}" min="1" max="{item['stock']}" style="width:70px;padding:6px;border:2px solid #f1f5f9;border-radius:6px;text-align:center;font-weight:700">
                      <button type="submit" class="btn btn-info btn-sm" title="Mettre à jour"><i class="fas fa-sync"></i></button>
                    </form>
                  </td>
                  <td><strong style="color:#ff6b35;font-size:1rem">{item['quantite'] * item['prix_unitaire']:,.0f} FCFA</strong></td>
                  <td>
                    <a href="/panier/supprimer/{item['id']}" class="btn btn-danger btn-sm" onclick="return confirm('Retirer cet article ?')"><i class="fas fa-trash"></i></a>
                  </td>
                </tr>
                """

            content += '</tbody></table></div></div>'

            content += f"""
            <div class="card" style="position:sticky;top:20px">
              <div class="card-header"><h3><i class="fas fa-receipt"></i> Récapitulatif</h3></div>
              <div style="display:flex;flex-direction:column;gap:12px">
                <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px dashed #fed7aa">
                  <span>Sous-total</span>
                  <strong>{sous_total:,.0f} FCFA</strong>
                </div>
                <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px dashed #fed7aa">
                  <span>Livraison</span>
                  <strong style="color:{'#10b981' if frais_livraison == 0 else '#ff6b35'}">{'GRATUITE' if frais_livraison == 0 else f'{frais_livraison:,.0f} FCFA'}</strong>
                </div>
                {('<div style="padding:8px 12px;background:#dcfce7;border-radius:8px;font-size:0.8rem;color:#065f46"><i class="fas fa-gift"></i> Plus que 50 000 FCFA pour la livraison gratuite !</div>') if sous_total < 50000 else ''}
                <div style="display:flex;justify-content:space-between;padding:15px 0;font-size:1.2rem">
                  <span style="font-weight:800">TOTAL</span>
                  <strong style="color:#ff6b35;font-size:1.4rem">{total:,.0f} FCFA</strong>
                </div>
                <a href="/commande/passer" class="btn btn-success" style="width:100%;justify-content:center;padding:14px">
                  <i class="fas fa-credit-card"></i> Passer la commande
                </a>
              </div>
            </div>
            """
            content += '</div>'

        if suggestions:
            content += '<div class="card"><div class="card-header"><h3><i class="fas fa-star"></i> Suggestions pour vous</h3></div><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:18px">'
            for s in suggestions:
                sp = s['prix_promo'] if s['prix_promo'] else s['prix_vente']
                content += f"""
                <a href="/produit/{s['id']}" style="text-decoration:none;color:inherit;background:#fff9f3;border-radius:12px;padding:15px;transition:0.3s;display:block">
                  <div style="height:100px;background:linear-gradient(135deg,#fff4e6,#ffe9d1);border-radius:8px;display:flex;justify-content:center;align-items:center;margin-bottom:10px">
                    <i class="fas fa-image" style="font-size:2rem;color:#fed7aa"></i>
                  </div>
                  <div style="font-weight:700;font-size:0.85rem;margin-bottom:6px">{s['nom'][:40]}</div>
                  <div style="color:#ff6b35;font-weight:900">{sp:,.0f} FCFA</div>
                </a>
                """
            content += '</div></div>'

        return render_page(content, active='panier', page_title='Mon panier')

    @app.route('/panier/modifier/<int:item_id>', methods=['POST'])
    @client_required
    def panier_modifier(item_id):
        client = _get_client_for_user(current_user)
        if not client:
            return redirect('/boutique')

        quantite = int(request.form.get('quantite') or 1)

        conn = get_db()
        c = conn.cursor()
        c.execute("""UPDATE paniers SET quantite=?
                     WHERE id=? AND client_id=?""", (quantite, item_id, client['id']))
        conn.commit()
        conn.close()
        flash("✅ Panier mis à jour", "success")
        return redirect('/mon-panier')

    @app.route('/panier/supprimer/<int:item_id>')
    @client_required
    def panier_supprimer(item_id):
        client = _get_client_for_user(current_user)
        if not client:
            return redirect('/boutique')

        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM paniers WHERE id=? AND client_id=?", (item_id, client['id']))
        conn.commit()
        conn.close()
        flash("✅ Article retiré du panier", "success")
        return redirect('/mon-panier')

    # ==================== PASSER COMMANDE ====================
    @app.route('/commande/passer', methods=['GET', 'POST'])
    @client_required
    def commande_passer():
        client = _get_client_for_user(current_user)
        if not client:
            flash("Profil client introuvable", "danger")
            return redirect('/boutique')

        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT pa.*, p.nom, p.stock FROM paniers pa
                     JOIN produits p ON pa.produit_id = p.id
                     WHERE pa.client_id = ?""", (client['id'],))
        items = c.fetchall()

        if not items:
            conn.close()
            flash("Votre panier est vide", "warning")
            return redirect('/boutique')

        sous_total = sum(item['quantite'] * item['prix_unitaire'] for item in items)
        frais_livraison = 2000 if sous_total < 50000 else 0

        if request.method == 'POST':
            try:
                numero = gen_numero('CMD', 'commandes')

                # Récupérer les infos livraison
                adresse = request.form.get('adresse_livraison') or client['adresse'] or ''
                ville = request.form.get('ville_livraison') or client['ville'] or ''
                tel = request.form.get('telephone_livraison') or client['telephone'] or ''
                mode_paiement = request.form.get('mode_paiement', 'Espèces')
                code_promo = request.form.get('code_promo', '').strip().upper()
                notes = request.form.get('notes', '')

                remise = 0
                if code_promo:
                    c.execute("""SELECT * FROM promotions
                                 WHERE code=? AND actif=1
                                   AND date_debut <= date('now') AND date_fin >= date('now')""", (code_promo,))
                    promo = c.fetchone()
                    if promo and sous_total >= promo['montant_min']:
                        if promo['type'] == 'pourcentage':
                            remise = sous_total * promo['valeur'] / 100
                        elif promo['type'] == 'montant':
                            remise = promo['valeur']
                        elif promo['type'] == 'livraison':
                            frais_livraison = 0
                        c.execute("UPDATE promotions SET nb_utilisations = nb_utilisations + 1 WHERE id=?", (promo['id'],))

                total = sous_total - remise + frais_livraison
                tva_calc = total * 18 / 118

                c.execute("""INSERT INTO commandes
                    (numero, client_id, date_commande, sous_total, remise, code_promo,
                     tva, frais_livraison, total, mode_paiement, statut, statut_paiement,
                     adresse_livraison, ville_livraison, telephone_livraison, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'En attente', 'Impayé', ?, ?, ?, ?)""",
                    (numero, client['id'], datetime.now().isoformat(),
                     sous_total, remise, code_promo or None, tva_calc, frais_livraison, total,
                     mode_paiement, adresse, ville, tel, notes))
                commande_id = c.lastrowid

                # Lignes de commande + mise à jour stock
                for item in items:
                    c.execute("""INSERT INTO lignes_commande
                        (commande_id, produit_id, nom_produit, quantite, prix_unitaire, total_ligne)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                        (commande_id, item['produit_id'], item['nom'],
                         item['quantite'], item['prix_unitaire'],
                         item['quantite'] * item['prix_unitaire']))

                    # Décrémenter stock
                    c.execute("""UPDATE produits SET stock = stock - ?, nb_ventes = nb_ventes + ?
                                 WHERE id=?""", (item['quantite'], item['quantite'], item['produit_id']))

                # Vider panier
                c.execute("DELETE FROM paniers WHERE client_id=?", (client['id'],))

                # Créer livraison
                numero_suivi = f"TRK-{numero}"
                c.execute("""INSERT INTO livraisons
                    (commande_id, numero_suivi, statut, adresse, destinataire, telephone)
                    VALUES (?, ?, 'En préparation', ?, ?, ?)""",
                    (commande_id, numero_suivi, adresse, f"{client['prenom']} {client['nom']}", tel))

                # Mettre à jour stats client
                c.execute("""UPDATE clients SET
                    nb_commandes = nb_commandes + 1,
                    total_achats = total_achats + ?,
                    points_fidelite = points_fidelite + ?
                    WHERE id=?""", (total, int(total / 1000), client['id']))

                conn.commit()
                conn.close()

                if current_user:
                    log_action(current_user.id, 'CREATE_COMMANDE', numero)

                flash(f"✅ Commande {numero} passée avec succès !", "success")
                return redirect(f'/commande/{commande_id}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-credit-card"></i> Finaliser la commande</h2>
          <a href="/mon-panier" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour au panier</a>
        </div>

        <form method="POST">
        <div style="display:grid;grid-template-columns:2fr 1fr;gap:25px;align-items:start">
          <div>
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-map-marker-alt"></i> Adresse de livraison</h3></div>
              <div class="form-grid">
                <div class="form-group form-full"><label>Adresse complète *</label>
                  <input type="text" name="adresse_livraison" value="{client['adresse'] or ''}" required placeholder="Ex: Sacré-Cœur 3, Villa N°123">
                </div>
                <div class="form-group"><label>Ville *</label>
                  <input type="text" name="ville_livraison" value="{client['ville'] or 'Dakar'}" required>
                </div>
                <div class="form-group"><label>Téléphone *</label>
                  <input type="tel" name="telephone_livraison" value="{client['telephone'] or ''}" required>
                </div>
                <div class="form-group form-full"><label>Notes (instructions pour le livreur)</label>
                  <textarea name="notes" rows="2" placeholder="Ex: Appeler avant d'arriver"></textarea>
                </div>
              </div>
            </div>

            <div class="card">
              <div class="card-header"><h3><i class="fas fa-credit-card"></i> Mode de paiement</h3></div>
              <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px">
                <label style="display:flex;align-items:center;gap:10px;padding:15px;border:2px solid #f1f5f9;border-radius:12px;cursor:pointer;transition:0.3s">
                  <input type="radio" name="mode_paiement" value="Wave" checked>
                  <div><strong>Wave</strong><br><small style="color:#94a3b8">Paiement mobile</small></div>
                </label>
                <label style="display:flex;align-items:center;gap:10px;padding:15px;border:2px solid #f1f5f9;border-radius:12px;cursor:pointer;transition:0.3s">
                  <input type="radio" name="mode_paiement" value="Orange Money">
                  <div><strong>Orange Money</strong><br><small style="color:#94a3b8">Paiement mobile</small></div>
                </label>
                <label style="display:flex;align-items:center;gap:10px;padding:15px;border:2px solid #f1f5f9;border-radius:12px;cursor:pointer;transition:0.3s">
                  <input type="radio" name="mode_paiement" value="Espèces">
                  <div><strong>Espèces</strong><br><small style="color:#94a3b8">À la livraison</small></div>
                </label>
                <label style="display:flex;align-items:center;gap:10px;padding:15px;border:2px solid #f1f5f9;border-radius:12px;cursor:pointer;transition:0.3s">
                  <input type="radio" name="mode_paiement" value="Carte">
                  <div><strong>Carte bancaire</strong><br><small style="color:#94a3b8">Visa/MasterCard</small></div>
                </label>
              </div>
            </div>

            <div class="card">
              <div class="card-header"><h3><i class="fas fa-tag"></i> Code promo</h3></div>
              <div style="display:flex;gap:10px">
                <input type="text" name="code_promo" placeholder="Ex: BIENVENUE10" style="flex:1;padding:12px 16px;border:2px solid #f1f5f9;border-radius:10px;text-transform:uppercase;font-weight:700">
                <button type="button" class="btn btn-gold"><i class="fas fa-check"></i> Appliquer</button>
              </div>
            </div>
          </div>

          <div class="card" style="position:sticky;top:20px">
            <div class="card-header"><h3><i class="fas fa-receipt"></i> Récapitulatif</h3></div>
            <div style="display:flex;flex-direction:column;gap:10px;margin-bottom:20px">
              {''.join(f'<div style="display:flex;justify-content:space-between;font-size:0.85rem"><span>{item["nom"][:30]} × {item["quantite"]}</span><strong>{item["quantite"]*item["prix_unitaire"]:,.0f}</strong></div>' for item in items)}
            </div>
            <div style="padding-top:15px;border-top:1px dashed #fed7aa;display:flex;flex-direction:column;gap:10px">
              <div style="display:flex;justify-content:space-between"><span>Sous-total</span><strong>{sous_total:,.0f} FCFA</strong></div>
              <div style="display:flex;justify-content:space-between"><span>Livraison</span><strong style="color:{'#10b981' if frais_livraison == 0 else '#ff6b35'}">{'GRATUITE' if frais_livraison == 0 else f'{frais_livraison:,.0f} FCFA'}</strong></div>
            </div>
            <div style="margin-top:20px;padding-top:20px;border-top:2px solid #ff6b35;display:flex;justify-content:space-between;align-items:center">
              <span style="font-weight:800;font-size:1.1rem">TOTAL</span>
              <strong style="color:#ff6b35;font-size:1.5rem">{sous_total + frais_livraison:,.0f} FCFA</strong>
            </div>
            <button type="submit" class="btn btn-success" style="width:100%;justify-content:center;margin-top:20px;padding:16px;font-size:1rem">
              <i class="fas fa-check-circle"></i> Confirmer la commande
            </button>
          </div>
        </div>
        </form>
        """
        return render_page(content, active='panier', page_title='Passer commande')

    # ==================== MES COMMANDES (client) ====================
    @app.route('/mes-commandes')
    @client_required
    def mes_commandes():
        client = _get_client_for_user(current_user)
        if not client:
            return redirect('/boutique')

        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT * FROM commandes WHERE client_id = ?
                     ORDER BY date_commande DESC""", (client['id'],))
        commandes = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <h2><i class="fas fa-receipt"></i> Mes commandes</h2>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Date</th><th>Total</th><th>Paiement</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for cmd in commandes:
            badge = 'badge-info'
            if cmd['statut'] == 'Livrée': badge = 'badge-success'
            elif cmd['statut'] == 'En cours': badge = 'badge-warning'
            elif cmd['statut'] == 'Annulée': badge = 'badge-danger'

            content += f"""
            <tr>
              <td><strong>{cmd['numero']}</strong></td>
              <td>{cmd['date_commande'][:10]}</td>
              <td><strong style="color:#ff6b35">{cmd['total']:,.0f}</strong> FCFA</td>
              <td>{cmd['mode_paiement'] or '-'}</td>
              <td><span class="badge {badge}">{cmd['statut']}</span></td>
              <td><a href="/commande/{cmd['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i> Voir</a></td>
            </tr>
            """
        if not commandes:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-receipt"></i><br>Aucune commande passée</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='mes_commandes', page_title='Mes commandes')

    print("[ECOMMERCE] ✅ Routes boutique + panier + commandes enregistrées")
