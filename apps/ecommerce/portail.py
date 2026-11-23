"""
Portail Vendeur + Portail Livreur + Portail Client
Vues personnalisées par rôle pour Omega Shop
"""
from flask import render_template_string, request, redirect, flash, jsonify
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "/app/data/ecommerce.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


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
    if hasattr(user, 'email') and user.email:
        c.execute("SELECT * FROM clients WHERE email=? LIMIT 1", (user.email,))
        cl = c.fetchone()
        if cl:
            conn.close()
            return cl
    if user.username and user.username.startswith('client'):
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


def register_portail_routes(app, render_page):
    """Portails par rôle"""

    # ==================== PORTAIL VENDEUR : MES VENTES ====================
    @app.route('/vendeur/mes-ventes')
    @vendeur_required
    def vendeur_mes_ventes():
        conn = get_db()
        c = conn.cursor()

        # Ventes du jour
        c.execute("""SELECT COUNT(*) as nb, COALESCE(SUM(total), 0) as total
                     FROM commandes
                     WHERE date(date_commande) = date('now') AND statut != 'Annulée'""")
        v_jour = c.fetchone()

        # Ventes semaine
        c.execute("""SELECT COUNT(*) as nb, COALESCE(SUM(total), 0) as total
                     FROM commandes
                     WHERE date_commande >= date('now', '-7 days') AND statut != 'Annulée'""")
        v_semaine = c.fetchone()

        # Ventes mois
        c.execute("""SELECT COUNT(*) as nb, COALESCE(SUM(total), 0) as total
                     FROM commandes
                     WHERE strftime('%Y-%m', date_commande) = strftime('%Y-%m', 'now') AND statut != 'Annulée'""")
        v_mois = c.fetchone()

        # Commandes en attente de traitement
        c.execute("""SELECT c.*, cl.nom, cl.prenom FROM commandes c
                     JOIN clients cl ON c.client_id = cl.id
                     WHERE c.statut = 'En attente'
                     ORDER BY c.date_commande DESC LIMIT 15""")
        en_attente = c.fetchall()

        # Top produits vendus
        c.execute("""SELECT p.nom, p.sku, SUM(lc.quantite) as total_vendu,
                     SUM(lc.total_ligne) as ca_genere
                     FROM produits p
                     JOIN lignes_commande lc ON lc.produit_id = p.id
                     GROUP BY p.id
                     ORDER BY total_vendu DESC LIMIT 5""")
        top_produits = c.fetchall()

        conn.close()

        content = f"""
        <div class="hero" style="padding:30px 35px;background:linear-gradient(135deg,#ff6b35,#f7931e)">
          <h1 style="font-size:1.8rem">Bonjour <span>{current_user.prenom}</span> 👋</h1>
          <p>Voici votre tableau de bord vendeur — Suivi temps réel des ventes</p>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-calendar-day stat-icon"></i>
            <div class="stat-value">{v_jour['nb']}</div>
            <div class="stat-label">Ventes du jour</div>
          </div>
          <div class="stat-card gold">
            <i class="fas fa-coins stat-icon"></i>
            <div class="stat-value">{v_jour['total']:,.0f}</div>
            <div class="stat-label">CA du jour (FCFA)</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-chart-line stat-icon"></i>
            <div class="stat-value">{v_semaine['nb']}</div>
            <div class="stat-label">Ventes 7 jours</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-calendar-month stat-icon"></i>
            <div class="stat-value">{v_mois['nb']}</div>
            <div class="stat-label">Ventes ce mois</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-money-bill-wave stat-icon"></i>
            <div class="stat-value">{v_mois['total']:,.0f}</div>
            <div class="stat-label">CA du mois (FCFA)</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-clock"></i> Commandes en attente de traitement ({len(en_attente)})</h3>
            <a href="/commandes" class="btn btn-primary btn-sm"><i class="fas fa-list"></i> Toutes les commandes</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Client</th><th>Montant</th><th>Date</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for cmd in en_attente:
            content += f"""
            <tr>
              <td><strong>{cmd['numero']}</strong></td>
              <td>{cmd['nom']} {cmd['prenom']}</td>
              <td><strong style="color:#ff6b35">{cmd['total']:,.0f}</strong> FCFA</td>
              <td>{cmd['date_commande'][:16]}</td>
              <td>
                <a href="/commandes/{cmd['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i> Traiter</a>
              </td>
            </tr>
            """
        if not en_attente:
            content += '<tr><td colspan="5" class="empty"><i class="fas fa-check-circle"></i><br>Aucune commande en attente 🎉</td></tr>'

        content += """
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-fire"></i> Top 5 produits vendus</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>SKU</th><th>Produit</th><th>Quantité vendue</th><th>CA généré</th></tr></thead>
              <tbody>
        """
        for p in top_produits:
            content += f"""
            <tr>
              <td><strong>{p['sku']}</strong></td>
              <td>{p['nom'][:50]}</td>
              <td><strong style="color:#10b981">{p['total_vendu']}</strong></td>
              <td><strong>{p['ca_genere']:,.0f}</strong> FCFA</td>
            </tr>
            """
        if not top_produits:
            content += '<tr><td colspan="4" class="empty"><i class="fas fa-inbox"></i><br>Aucune vente</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='dashboard', page_title='Portail vendeur')


    # ==================== LISTE COMMANDES (vendeur) ====================
    @app.route('/commandes')
    @staff_required
    def commandes_liste():
        conn = get_db()
        c = conn.cursor()

        statut_filter = request.args.get('statut', '')
        search = request.args.get('q', '').strip()

        query = """SELECT c.*, cl.nom as cl_nom, cl.prenom as cl_prenom, cl.telephone as cl_tel
                   FROM commandes c
                   JOIN clients cl ON c.client_id = cl.id
                   WHERE 1=1"""
        params = []

        if statut_filter:
            query += " AND c.statut = ?"
            params.append(statut_filter)
        if search:
            query += " AND (c.numero LIKE ? OR cl.nom LIKE ? OR cl.prenom LIKE ?)"
            params.extend([f'%{search}%'] * 3)

        query += " ORDER BY c.date_commande DESC LIMIT 200"
        c.execute(query, params)
        rows = c.fetchall()

        # Stats
        c.execute("""SELECT statut, COUNT(*) as nb FROM commandes GROUP BY statut""")
        stats_par_statut = {r['statut']: r['nb'] for r in c.fetchall()}
        conn.close()

        total = sum(stats_par_statut.values())

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-shopping-cart"></i> Commandes</h2>
            <div class="page-subtitle">{total} commande(s) au total</div>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card"><i class="fas fa-clock stat-icon"></i><div class="stat-value">{stats_par_statut.get('En attente', 0)}</div><div class="stat-label">En attente</div></div>
          <div class="stat-card gold"><i class="fas fa-cog stat-icon"></i><div class="stat-value">{stats_par_statut.get('En cours', 0)}</div><div class="stat-label">En cours</div></div>
          <div class="stat-card blue"><i class="fas fa-truck stat-icon"></i><div class="stat-value">{stats_par_statut.get('Expédiée', 0)}</div><div class="stat-label">Expédiées</div></div>
          <div class="stat-card green"><i class="fas fa-check-circle stat-icon"></i><div class="stat-value">{stats_par_statut.get('Livrée', 0)}</div><div class="stat-label">Livrées</div></div>
          <div class="stat-card rose"><i class="fas fa-times-circle stat-icon"></i><div class="stat-value">{stats_par_statut.get('Annulée', 0)}</div><div class="stat-label">Annulées</div></div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Liste des commandes</h3>
            <form method="GET" style="display:flex;gap:8px;flex-wrap:wrap">
              <input type="text" name="q" value="{search}" placeholder="Rechercher..." style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px;width:180px">
              <select name="statut" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous statuts</option>
                <option value="En attente" {"selected" if statut_filter == "En attente" else ""}>En attente</option>
                <option value="En cours" {"selected" if statut_filter == "En cours" else ""}>En cours</option>
                <option value="Expédiée" {"selected" if statut_filter == "Expédiée" else ""}>Expédiée</option>
                <option value="Livrée" {"selected" if statut_filter == "Livrée" else ""}>Livrée</option>
                <option value="Annulée" {"selected" if statut_filter == "Annulée" else ""}>Annulée</option>
              </select>
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>N°</th><th>Client</th><th>Contact</th><th>Montant</th>
                  <th>Paiement</th><th>Date</th><th>Statut</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
        """
        for cmd in rows:
            badge = 'badge-info'
            if cmd['statut'] == 'Livrée': badge = 'badge-success'
            elif cmd['statut'] == 'En cours': badge = 'badge-warning'
            elif cmd['statut'] == 'Expédiée': badge = 'badge-primary'
            elif cmd['statut'] == 'Annulée': badge = 'badge-danger'

            content += f"""
            <tr>
              <td><strong>{cmd['numero']}</strong></td>
              <td>{cmd['cl_nom']} {cmd['cl_prenom']}</td>
              <td><small><i class="fas fa-phone"></i> {cmd['cl_tel'] or '-'}</small></td>
              <td><strong style="color:#ff6b35">{cmd['total']:,.0f}</strong> FCFA</td>
              <td>{cmd['mode_paiement'] or '-'}</td>
              <td>{cmd['date_commande'][:16]}</td>
              <td><span class="badge {badge}">{cmd['statut']}</span></td>
              <td>
                <a href="/commandes/{cmd['id']}" class="btn btn-info btn-sm" title="Voir"><i class="fas fa-eye"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-inbox"></i><br>Aucune commande</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='commandes', page_title='Commandes')


    # ==================== DÉTAIL COMMANDE (vendeur) ====================
    @app.route('/commandes/<int:cid>')
    @staff_required
    def commande_detail(cid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT c.*, cl.nom as cl_nom, cl.prenom as cl_prenom,
                            cl.telephone as cl_tel, cl.email as cl_email, cl.code as cl_code
                     FROM commandes c
                     JOIN clients cl ON c.client_id = cl.id
                     WHERE c.id=?""", (cid,))
        cmd = c.fetchone()
        if not cmd:
            conn.close()
            flash("Commande introuvable", "danger")
            return redirect('/commandes')

        c.execute("SELECT * FROM lignes_commande WHERE commande_id=?", (cid,))
        lignes = c.fetchall()

        c.execute("SELECT * FROM livraisons WHERE commande_id=?", (cid,))
        livraison = c.fetchone()

        c.execute("SELECT * FROM paiements WHERE commande_id=? ORDER BY date_paiement DESC", (cid,))
        paiements = c.fetchall()

        c.execute("""SELECT l.*, u.nom as u_nom, u.prenom as u_prenom
                     FROM livraisons l
                     LEFT JOIN utilisateurs u ON l.livreur_id = u.id
                     WHERE l.commande_id=?""", (cid,))
        conn.close()

        # Statuts possibles
        statuts = ['En attente', 'En cours', 'Expédiée', 'Livrée', 'Annulée']

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-receipt"></i> Commande {cmd['numero']}</h2>
          <a href="/commandes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-money-bill-wave stat-icon"></i>
            <div class="stat-value">{cmd['total']:,.0f}</div>
            <div class="stat-label">Total (FCFA)</div>
          </div>
          <div class="stat-card gold">
            <i class="fas fa-credit-card stat-icon"></i>
            <div class="stat-value" style="font-size:1.2rem">{cmd['mode_paiement'] or '-'}</div>
            <div class="stat-label">Mode paiement</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-check-circle stat-icon"></i>
            <div class="stat-value" style="font-size:1.2rem">{cmd['statut_paiement'] or '-'}</div>
            <div class="stat-label">Statut paiement</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-info-circle stat-icon"></i>
            <div class="stat-value" style="font-size:1.2rem">{cmd['statut']}</div>
            <div class="stat-label">Statut commande</div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:2fr 1fr;gap:25px">
          <div>
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-user"></i> Informations client</h3></div>
              <div class="form-grid">
                <div><strong>Client :</strong> {cmd['cl_nom']} {cmd['cl_prenom']}</div>
                <div><strong>Code :</strong> {cmd['cl_code']}</div>
                <div><strong>Téléphone :</strong> {cmd['cl_tel'] or '-'}</div>
                <div><strong>Email :</strong> {cmd['cl_email'] or '-'}</div>
                <div><strong>Adresse livraison :</strong> {cmd['adresse_livraison'] or '-'}</div>
                <div><strong>Ville :</strong> {cmd['ville_livraison'] or '-'}</div>
                <div><strong>Tél. livraison :</strong> {cmd['telephone_livraison'] or '-'}</div>
                <div><strong>Date commande :</strong> {cmd['date_commande'][:19]}</div>
              </div>
              {('<div style="margin-top:15px;padding:12px;background:#fff4e6;border-radius:8px"><strong>Notes client :</strong> ' + cmd['notes'] + '</div>') if cmd['notes'] else ''}
            </div>

            <div class="card">
              <div class="card-header"><h3><i class="fas fa-list"></i> Articles commandés</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Produit</th><th>Qté</th><th>Prix unitaire</th><th>Total ligne</th></tr></thead>
                  <tbody>
        """
        for l in lignes:
            content += f"""
            <tr>
              <td>{l['nom_produit']}</td>
              <td><strong>{l['quantite']}</strong></td>
              <td>{l['prix_unitaire']:,.0f} FCFA</td>
              <td><strong style="color:#ff6b35">{l['total_ligne']:,.0f} FCFA</strong></td>
            </tr>
            """
        content += f"""
                  </tbody>
                  <tfoot>
                    <tr style="background:#fff9f3"><td colspan="3" style="text-align:right"><strong>Sous-total</strong></td><td><strong>{cmd['sous_total']:,.0f} FCFA</strong></td></tr>
                    {f'<tr><td colspan="3" style="text-align:right"><strong>Remise ({cmd["code_promo"]})</strong></td><td style="color:#10b981"><strong>-{cmd["remise"]:,.0f} FCFA</strong></td></tr>' if cmd['remise'] and cmd['remise'] > 0 else ''}
                    <tr><td colspan="3" style="text-align:right"><strong>Frais livraison</strong></td><td><strong>{cmd['frais_livraison']:,.0f} FCFA</strong></td></tr>
                    <tr style="background:#fff4e6"><td colspan="3" style="text-align:right"><strong style="font-size:1.1rem">TOTAL</strong></td><td><strong style="color:#ff6b35;font-size:1.2rem">{cmd['total']:,.0f} FCFA</strong></td></tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </div>

          <div>
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-cog"></i> Changer le statut</h3></div>
              <form method="POST" action="/commandes/{cid}/statut">
                <div class="form-group">
                  <label>Nouveau statut</label>
                  <select name="statut" required>
                    {''.join(f'<option value="{s}" {"selected" if cmd["statut"]==s else ""}>{s}</option>' for s in statuts)}
                  </select>
                </div>
                <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center">
                  <i class="fas fa-sync"></i> Mettre à jour
                </button>
              </form>
            </div>

            {f'''
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-truck"></i> Livraison</h3></div>
              <div style="display:flex;flex-direction:column;gap:10px;font-size:0.9rem">
                <div><strong>N° suivi :</strong> <code>{livraison["numero_suivi"]}</code></div>
                <div><strong>Statut :</strong> <span class="badge badge-info">{livraison["statut"]}</span></div>
                {f'<div><strong>Livreur :</strong> {livraison["u_nom"] or "?"} {livraison["u_prenom"] or ""}</div>' if livraison and "u_nom" in livraison.keys() else ""}
                <div><strong>Destinataire :</strong> {livraison["destinataire"] or "-"}</div>
                <div><strong>Adresse :</strong> {livraison["adresse"] or "-"}</div>
              </div>
            </div>
            ''' if livraison else ''}

            {f'''
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-money-bill"></i> Paiements ({len(paiements)})</h3></div>
              <div style="display:flex;flex-direction:column;gap:10px">
                {''.join(f'<div style="padding:10px;background:#f8fafc;border-radius:8px"><strong>{p["montant"]:,.0f} FCFA</strong> — {p["mode"]}<br><small style="color:#94a3b8">{p["date_paiement"][:16]}</small></div>' for p in paiements)}
              </div>
            </div>
            ''' if paiements else ''}
          </div>
        </div>
        """
        return render_page(content, active='commandes', page_title=f'Commande {cmd["numero"]}')


    # ==================== CHANGER STATUT COMMANDE ====================
    @app.route('/commandes/<int:cid>/statut', methods=['POST'])
    @vendeur_required
    def commande_changer_statut(cid):
        nouveau_statut = request.form.get('statut', '').strip()
        if not nouveau_statut:
            flash("Statut invalide", "danger")
            return redirect(f'/commandes/{cid}')

        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE commandes SET statut=? WHERE id=?", (nouveau_statut, cid))

            # Si livrée, mettre à jour le paiement
            if nouveau_statut == 'Livrée':
                c.execute("""UPDATE commandes SET statut_paiement='Payé',
                             montant_paye=total WHERE id=?""", (cid,))

            # Mettre à jour livraison
            c.execute("""UPDATE livraisons SET statut=?
                         WHERE commande_id=?""",
                      ('Livrée' if nouveau_statut == 'Livrée' else ('En cours' if nouveau_statut == 'Expédiée' else 'En préparation'), cid))

            conn.commit()
            conn.close()

            if current_user:
                log_action(current_user.id, 'UPDATE_COMMANDE_STATUT',
                          f'Commande {cid} → {nouveau_statut}')

            flash(f"✅ Statut mis à jour : {nouveau_statut}", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")

        return redirect(f'/commandes/{cid}')


    # ==================== PORTAIL LIVREUR : MES LIVRAISONS ====================
    @app.route('/livreur/mes-livraisons')
    @staff_required
    def livreur_mes_livraisons():
        conn = get_db()
        c = conn.cursor()

        # Récupérer toutes les livraisons en cours (non livrées, non annulées)
        c.execute("""SELECT l.*, c.numero as cmd_numero, c.total, c.ville_livraison,
                            cl.nom as cl_nom, cl.prenom as cl_prenom, cl.telephone as cl_tel
                     FROM livraisons l
                     JOIN commandes c ON l.commande_id = c.id
                     JOIN clients cl ON c.client_id = cl.id
                     WHERE l.statut IN ('En préparation', 'En cours')
                     ORDER BY l.created_at DESC""")
        livraisons = c.fetchall()

        # Livraisons du jour (livrées aujourd'hui)
        c.execute("""SELECT COUNT(*) FROM livraisons
                     WHERE statut='Livrée' AND date(date_arrivee) = date('now')""")
        livrees_jour = c.fetchone()[0]

        # Stats
        c.execute("""SELECT statut, COUNT(*) as nb FROM livraisons GROUP BY statut""")
        stats_par_statut = {r['statut']: r['nb'] for r in c.fetchall()}

        conn.close()

        content = f"""
        <div class="hero" style="padding:30px 35px;background:linear-gradient(135deg,#0891b2,#06b6d4)">
          <h1 style="font-size:1.8rem">Bonjour <span>{current_user.prenom}</span> 🚚</h1>
          <p>Tableau de bord livreur — Vos tournées et livraisons</p>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-clock stat-icon"></i>
            <div class="stat-value">{stats_par_statut.get('En préparation', 0)}</div>
            <div class="stat-label">À préparer</div>
          </div>
          <div class="stat-card gold">
            <i class="fas fa-truck stat-icon"></i>
            <div class="stat-value">{stats_par_statut.get('En cours', 0)}</div>
            <div class="stat-label">En cours de livraison</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-check-circle stat-icon"></i>
            <div class="stat-value">{livrees_jour}</div>
            <div class="stat-label">Livrées aujourd'hui</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-truck-fast"></i> Livraisons à effectuer ({len(livraisons)})</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>N° suivi</th><th>Commande</th><th>Client</th><th>Adresse</th><th>Montant</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for l in livraisons:
            badge = 'badge-info' if l['statut'] == 'En préparation' else 'badge-warning'
            content += f"""
            <tr>
              <td><strong>{l['numero_suivi']}</strong></td>
              <td>{l['cmd_numero']}</td>
              <td>
                <div>{l['cl_nom']} {l['cl_prenom']}</div>
                <small style="color:#94a3b8"><i class="fas fa-phone"></i> {l['cl_tel']}</small>
              </td>
              <td>
                <div>{l['adresse'] or '-'}</div>
                <small style="color:#64748b">{l['ville_livraison'] or ''}</small>
              </td>
              <td><strong style="color:#ff6b35">{l['total']:,.0f}</strong> FCFA</td>
              <td><span class="badge {badge}">{l['statut']}</span></td>
              <td>
                <a href="/livreur/livraison/{l['id']}/demarrer" class="btn btn-warning btn-sm" title="Démarrer" onclick="return confirm('Démarrer cette livraison ?')"><i class="fas fa-play"></i></a>
                <a href="/livreur/livraison/{l['id']}/terminer" class="btn btn-success btn-sm" title="Terminer" onclick="return confirm('Marquer comme livrée ?')"><i class="fas fa-check"></i></a>
              </td>
            </tr>
            """
        if not livraisons:
            content += '<tr><td colspan="7" class="empty"><i class="fas fa-check-circle"></i><br>Aucune livraison en attente 🎉</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='dashboard', page_title='Mes livraisons')


    @app.route('/livreur/livraison/<int:lid>/demarrer')
    @staff_required
    def livraison_demarrer(lid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("""UPDATE livraisons SET statut='En cours',
                         date_depart=?, livreur_id=? WHERE id=?""",
                      (datetime.now().isoformat(), current_user.id, lid))

            # Récupérer commande
            c.execute("SELECT commande_id FROM livraisons WHERE id=?", (lid,))
            row = c.fetchone()
            if row:
                c.execute("UPDATE commandes SET statut='Expédiée' WHERE id=?", (row['commande_id'],))

            conn.commit()
            conn.close()
            if current_user:
                log_action(current_user.id, 'LIVRAISON_DEMARREE', f'ID {lid}')
            flash("✅ Livraison démarrée", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/livreur/mes-livraisons')


    @app.route('/livreur/livraison/<int:lid>/terminer')
    @staff_required
    def livraison_terminer(lid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("""UPDATE livraisons SET statut='Livrée',
                         date_arrivee=? WHERE id=?""",
                      (datetime.now().isoformat(), lid))

            c.execute("SELECT commande_id FROM livraisons WHERE id=?", (lid,))
            row = c.fetchone()
            if row:
                c.execute("""UPDATE commandes SET statut='Livrée',
                             statut_paiement='Payé', montant_paye=total
                             WHERE id=?""", (row['commande_id'],))

            conn.commit()
            conn.close()
            if current_user:
                log_action(current_user.id, 'LIVRAISON_TERMINEE', f'ID {lid}')
            flash("✅ Livraison terminée", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/livreur/mes-livraisons')


    # ==================== PORTAIL CLIENT : MON PROFIL ====================
    @app.route('/mon-profil', methods=['GET', 'POST'])
    @client_required
    def mon_profil():
        client = _get_client_for_user(current_user)
        if not client:
            flash("Profil introuvable", "danger")
            return redirect('/boutique')

        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                c.execute("""UPDATE clients SET
                    nom=?, prenom=?, email=?, telephone=?, adresse=?, ville=?, region=?,
                    date_naissance=?, genre=? WHERE id=?""",
                    (request.form['nom'], request.form['prenom'], request.form.get('email', ''),
                     request.form['telephone'], request.form.get('adresse', ''),
                     request.form.get('ville', ''), request.form.get('region', ''),
                     request.form.get('date_naissance', ''), request.form.get('genre', ''),
                     client['id']))
                conn.commit()
                conn.close()
                flash("✅ Profil mis à jour", "success")
                return redirect('/mon-profil')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        # Stats client
        c.execute("""SELECT COUNT(*) as nb, COALESCE(SUM(total), 0) as total
                     FROM commandes WHERE client_id=?""", (client['id'],))
        stats = c.fetchone()

        c.execute("""SELECT COUNT(*) FROM paniers WHERE client_id=?""", (client['id'],))
        nb_panier = c.fetchone()[0]

        c.execute("""SELECT COUNT(*) FROM wishlist WHERE client_id=?""", (client['id'],))
        nb_wishlist = c.fetchone()[0]

        conn.close()

        content = f"""
        <div class="hero" style="padding:30px 35px;background:linear-gradient(135deg,#10b981,#059669)">
          <h1 style="font-size:1.8rem">Bonjour <span>{client['prenom']}</span> 👋</h1>
          <p>Membre fidèle Omega Shop depuis {client['created_at'][:10]}</p>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-shopping-bag stat-icon"></i>
            <div class="stat-value">{stats['nb']}</div>
            <div class="stat-label">Commandes</div>
          </div>
          <div class="stat-card gold">
            <i class="fas fa-star stat-icon"></i>
            <div class="stat-value">{client['points_fidelite']}</div>
            <div class="stat-label">Points fidélité</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-coins stat-icon"></i>
            <div class="stat-value">{stats['total']:,.0f}</div>
            <div class="stat-label">CA total (FCFA)</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-shopping-basket stat-icon"></i>
            <div class="stat-value">{nb_panier}</div>
            <div class="stat-label">Panier</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-heart stat-icon"></i>
            <div class="stat-value">{nb_wishlist}</div>
            <div class="stat-label">Wishlist</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-user-edit"></i> Modifier mon profil</h3></div>
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code client</label><input type="text" value="{client['code']}" disabled></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{client['nom']}" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" value="{client['prenom']}" required></div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" value="{client['telephone']}" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email" value="{client['email'] or ''}"></div>
              <div class="form-group"><label>Date naissance</label><input type="date" name="date_naissance" value="{client['date_naissance'] or ''}"></div>
              <div class="form-group"><label>Genre</label>
                <select name="genre">
                  <option value="">--</option>
                  <option value="M" {"selected" if client['genre'] == 'M' else ""}>Masculin</option>
                  <option value="F" {"selected" if client['genre'] == 'F' else ""}>Féminin</option>
                </select>
              </div>
              <div class="form-group form-full"><label>Adresse</label><input type="text" name="adresse" value="{client['adresse'] or ''}"></div>
              <div class="form-group"><label>Ville</label><input type="text" name="ville" value="{client['ville'] or ''}"></div>
              <div class="form-group"><label>Région</label><input type="text" name="region" value="{client['region'] or ''}"></div>
            </div>
            <div style="margin-top:25px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='dashboard', page_title='Mon profil')


    # ==================== PORTAIL CLIENT : MA WISHLIST ====================
    @app.route('/ma-wishlist')
    @client_required
    def ma_wishlist():
        client = _get_client_for_user(current_user)
        if not client:
            return redirect('/boutique')

        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT w.*, p.nom, p.sku, p.prix_vente, p.prix_promo,
                            p.stock, p.description_courte
                     FROM wishlist w
                     JOIN produits p ON w.produit_id = p.id
                     WHERE w.client_id = ?
                     ORDER BY w.created_at DESC""", (client['id'],))
        items = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <h2><i class="fas fa-heart" style="color:#ec4899"></i> Ma Wishlist</h2>
          <a href="/boutique" class="btn btn-info"><i class="fas fa-store"></i> Continuer les achats</a>
        </div>
        """

        if not items:
            content += """
            <div class="card">
              <div class="empty">
                <i class="fas fa-heart" style="color:#fce7f3"></i>
                <h3>Votre wishlist est vide</h3>
                <p>Ajoutez vos produits préférés pour les retrouver ici</p>
              </div>
            </div>
            """
        else:
            content += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:22px">'
            for w in items:
                prix = w['prix_promo'] if w['prix_promo'] else w['prix_vente']
                content += f"""
                <div class="product-card" style="background:white;border-radius:18px;overflow:hidden;box-shadow:0 6px 20px rgba(255,107,53,0.06)">
                  <div style="position:relative;height:150px;background:linear-gradient(135deg,#fff4e6,#ffe9d1);display:flex;justify-content:center;align-items:center">
                    <i class="fas fa-image" style="font-size:3rem;color:#fed7aa"></i>
                    <a href="/wishlist/supprimer/{w['id']}" style="position:absolute;top:10px;right:10px;background:#dc2626;color:white;width:34px;height:34px;border-radius:50%;display:flex;justify-content:center;align-items:center;text-decoration:none" title="Retirer" onclick="return confirm('Retirer de la wishlist ?')">
                      <i class="fas fa-times"></i>
                    </a>
                  </div>
                  <div style="padding:16px">
                    <div style="font-weight:700;font-size:0.9rem;margin-bottom:8px">{w['nom'][:50]}</div>
                    <div style="color:#ff6b35;font-weight:900;font-size:1.1rem;margin-bottom:12px">{prix:,.0f} FCFA</div>
                    <div style="display:flex;gap:8px">
                      <a href="/produit/{w['produit_id']}" class="btn btn-primary btn-sm" style="flex:1;justify-content:center"><i class="fas fa-eye"></i> Voir</a>
                      <form method="POST" action="/panier/ajouter/{w['produit_id']}" style="flex:1">
                        <input type="hidden" name="quantite" value="1">
                        <button type="submit" class="btn btn-success btn-sm" style="width:100%;justify-content:center"><i class="fas fa-cart-plus"></i></button>
                      </form>
                    </div>
                  </div>
                </div>
                """
            content += '</div>'
        return render_page(content, active='wishlist', page_title='Ma wishlist')


    @app.route('/wishlist/ajouter/<int:pid>')
    @client_required
    def wishlist_ajouter(pid):
        client = _get_client_for_user(current_user)
        if not client:
            return redirect('/boutique')
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM wishlist WHERE client_id=? AND produit_id=?",
                  (client['id'], pid))
        if not c.fetchone():
            c.execute("INSERT INTO wishlist (client_id, produit_id) VALUES (?, ?)",
                      (client['id'], pid))
            conn.commit()
            flash("✅ Ajouté à la wishlist", "success")
        else:
            flash("Déjà dans la wishlist", "info")
        conn.close()
        return redirect(request.referrer or '/boutique')


    @app.route('/wishlist/supprimer/<int:wid>')
    @client_required
    def wishlist_supprimer(wid):
        client = _get_client_for_user(current_user)
        if not client:
            return redirect('/boutique')
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM wishlist WHERE id=? AND client_id=?", (wid, client['id']))
        conn.commit()
        conn.close()
        flash("✅ Retiré de la wishlist", "success")
        return redirect('/ma-wishlist')


    print("[PORTAIL] ✅ Routes portail vendeur + livreur + client enregistrées")
