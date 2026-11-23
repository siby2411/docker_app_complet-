"""
Module Logique Métier Stock
Mouvements, Inventaires, Commandes, Réceptions, Valorisation PMP, Alertes
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


def gen_numero(prefix, table):
    conn = get_db()
    c = conn.cursor()
    year = datetime.now().year
    c.execute(f"SELECT COUNT(*) FROM {table}")
    n = c.fetchone()[0] + 1
    conn.close()
    return f"{prefix}-{year}-{n:04d}"


def calculer_pmp(produit_id, conn=None):
    """Recalcule le PMP d'un produit"""
    close_after = False
    if conn is None:
        conn = get_db()
        close_after = True

    c = conn.cursor()

    # Stock actuel
    c.execute("SELECT stock_actuel FROM produits WHERE id=?", (produit_id,))
    row = c.fetchone()
    stock_actuel = row['stock_actuel'] if row else 0

    # Quantité totale entrée × prix
    c.execute("""SELECT COALESCE(SUM(quantite), 0) as qte,
                        COALESCE(SUM(quantite * prix_unitaire), 0) as val
                 FROM mouvements
                 WHERE produit_id = ? AND type_mouvement = 'Entrée' AND statut = 'Validé'""",
              (produit_id,))
    row = c.fetchone()
    qte_entrees = row['qte']
    val_entrees = row['val']

    pmp = (val_entrees / qte_entrees) if qte_entrees > 0 else 0

    c.execute("UPDATE produits SET pmp=? WHERE id=?", (pmp, produit_id))

    if close_after:
        conn.commit()
        conn.close()

    return pmp


def generer_alerte(conn, type_alerte, produit_id, message, priorite='Normale'):
    """Crée une alerte si elle n'existe pas déjà"""
    c = conn.cursor()
    c.execute("""SELECT id FROM alertes WHERE type_alerte=? AND produit_id=?
                 AND statut='Active'""", (type_alerte, produit_id))
    if not c.fetchone():
        c.execute("""INSERT INTO alertes (type_alerte, produit_id, message, priorite, statut)
                     VALUES (?, ?, ?, ?, 'Active')""",
                  (type_alerte, produit_id, message, priorite))


def maj_alertes_produit(produit_id, conn=None):
    """Met à jour les alertes pour un produit"""
    close_after = False
    if conn is None:
        conn = get_db()
        close_after = True

    c = conn.cursor()
    c.execute("SELECT * FROM produits WHERE id=?", (produit_id,))
    p = c.fetchone()
    if not p:
        if close_after: conn.close()
        return

    # Alerte stock bas
    if p['stock_actuel'] <= p['stock_min'] and p['stock_min'] > 0:
        generer_alerte(conn, 'Stock bas', produit_id,
                       f"Stock bas : {p['nom']} ({p['stock_actuel']:.0f}, seuil {p['stock_min']:.0f})",
                       'Haute' if p['stock_actuel'] <= 0 else 'Normale')
    else:
        # Résoudre l'alerte si elle existe
        c.execute("""UPDATE alertes SET statut='Résolue', date_traitement=?
                     WHERE type_alerte='Stock bas' AND produit_id=? AND statut='Active'""",
                  (datetime.now().isoformat(), produit_id))

    # Alerte rupture
    if p['stock_actuel'] <= 0:
        generer_alerte(conn, 'Rupture', produit_id,
                       f"RUPTURE : {p['nom']} est épuisé", 'Critique')

    # Alerte surstock
    if p['stock_actuel'] > p['stock_max'] and p['stock_max'] > 0:
        generer_alerte(conn, 'Stock élevé', produit_id,
                       f"Stock élevé : {p['nom']} ({p['stock_actuel']:.0f} > {p['stock_max']:.0f})",
                       'Basse')

    if close_after:
        conn.commit()
        conn.close()


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


def register_stock_routes(app, render_page):
    """Enregistre toutes les routes logique métier"""

    # ==================== MOUVEMENTS ====================
    @app.route('/mouvements')
    @staff_required
    def mouvements_liste():
        conn = get_db()
        c = conn.cursor()

        type_filter = request.args.get('type', '')
        search = request.args.get('q', '').strip()
        date_debut = request.args.get('debut', '')
        date_fin = request.args.get('fin', '')

        query = """SELECT m.*, p.nom as produit_nom, p.sku, p.unite,
                          u.nom as u_nom, u.prenom as u_prenom,
                          es.code as src_code, ed.code as dest_code
                   FROM mouvements m
                   LEFT JOIN produits p ON m.produit_id = p.id
                   LEFT JOIN utilisateurs u ON m.user_id = u.id
                   LEFT JOIN emplacements es ON m.emplacement_source_id = es.id
                   LEFT JOIN emplacements ed ON m.emplacement_destination_id = ed.id
                   WHERE 1=1"""
        params = []

        if type_filter:
            query += " AND m.type_mouvement = ?"
            params.append(type_filter)

        if search:
            query += " AND (p.nom LIKE ? OR p.sku LIKE ? OR m.numero LIKE ?)"
            params.extend([f'%{search}%'] * 3)

        if date_debut:
            query += " AND date(m.date_mouvement) >= ?"
            params.append(date_debut)
        if date_fin:
            query += " AND date(m.date_mouvement) <= ?"
            params.append(date_fin)

        query += " ORDER BY m.date_mouvement DESC LIMIT 300"
        c.execute(query, params)
        rows = c.fetchall()

        # Stats
        c.execute("""SELECT type_mouvement, COUNT(*) as nb FROM mouvements
                     WHERE date(date_mouvement) >= date('now', '-30 days')
                     GROUP BY type_mouvement""")
        stats = {r['type_mouvement']: r['nb'] for r in c.fetchall()}
        conn.close()

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-arrows-rotate"></i> Mouvements de stock</h2>
            <div class="page-subtitle">Historique complet des entrées/sorties</div>
          </div>
          <a href="/mouvements/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau mouvement</a>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-arrow-down stat-icon"></i>
            <div class="stat-value">{stats.get('Entrée', 0)}</div>
            <div class="stat-label">Entrées (30j)</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-arrow-up stat-icon"></i>
            <div class="stat-value">{stats.get('Sortie', 0)}</div>
            <div class="stat-label">Sorties (30j)</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-arrows-left-right stat-icon"></i>
            <div class="stat-value">{stats.get('Transfert', 0)}</div>
            <div class="stat-label">Transferts (30j)</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-balance-scale stat-icon"></i>
            <div class="stat-value">{stats.get('Ajustement', 0)}</div>
            <div class="stat-label">Ajustements (30j)</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Historique</h3>
            <form method="GET" style="display:flex;gap:8px;flex-wrap:wrap">
              <input type="text" name="q" value="{search}" placeholder="N°, SKU, produit..." style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px;width:180px">
              <select name="type" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous types</option>
                <option value="Entrée" {"selected" if type_filter == "Entrée" else ""}>Entrée</option>
                <option value="Sortie" {"selected" if type_filter == "Sortie" else ""}>Sortie</option>
                <option value="Transfert" {"selected" if type_filter == "Transfert" else ""}>Transfert</option>
                <option value="Ajustement" {"selected" if type_filter == "Ajustement" else ""}>Ajustement</option>
              </select>
              <input type="date" name="debut" value="{date_debut}" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
              <input type="date" name="fin" value="{date_fin}" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>N°</th><th>Type</th><th>Produit</th><th>Quantité</th>
                  <th>Valeur</th><th>Motif</th><th>Utilisateur</th><th>Date</th>
                </tr>
              </thead>
              <tbody>
        """
        for m in rows:
            type_badge = 'badge-success' if m['type_mouvement'] == 'Entrée' else ('badge-danger' if m['type_mouvement'] == 'Sortie' else 'badge-info')
            signe = '+' if m['type_mouvement'] == 'Entrée' else ('-' if m['type_mouvement'] == 'Sortie' else '↔')

            content += f"""
            <tr>
              <td><strong>{m['numero']}</strong></td>
              <td><span class="badge {type_badge}">{m['type_mouvement']}</span></td>
              <td>
                <div style="font-weight:700">{m['produit_nom'][:45] if m['produit_nom'] else '-'}</div>
                <small style="color:#94a3b8">{m['sku'] or ''}</small>
              </td>
              <td><strong>{signe}{m['quantite']:.0f} {m['unite'] or ''}</strong></td>
              <td>{m['valeur_totale']:,.0f} FCFA</td>
              <td>{m['motif'][:30] if m['motif'] else '-'}</td>
              <td><small>{m['u_nom'] or '?'} {m['u_prenom'] or ''}</small></td>
              <td>{m['date_mouvement'][:16]}</td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-inbox"></i><br>Aucun mouvement</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='mouvements', page_title='Mouvements')

    @app.route('/mouvements/nouveau', methods=['GET', 'POST'])
    @magasinier_required
    def mouvement_nouveau():
        conn = get_db()
        c = conn.cursor()
        produit_id_pre = request.args.get('produit_id', '')

        if request.method == 'POST':
            try:
                type_mvt = request.form['type_mouvement']
                produit_id = int(request.form['produit_id'])
                quantite = float(request.form['quantite'])
                emplacement_id = int(request.form['emplacement_id']) if request.form.get('emplacement_id') else None
                emplacement_dest = int(request.form['emplacement_destination_id']) if request.form.get('emplacement_destination_id') else None
                prix_unitaire = float(request.form.get('prix_unitaire') or 0)

                # Générer numéro
                numero = gen_numero('MVT', 'mouvements')

                # Récupérer infos produit
                c.execute("SELECT * FROM produits WHERE id=?", (produit_id,))
                p = c.fetchone()

                valeur_totale = quantite * prix_unitaire if prix_unitaire > 0 else quantite * p['pmp']

                # Insérer mouvement
                c.execute("""INSERT INTO mouvements
                    (numero, type_mouvement, produit_id, emplacement_source_id,
                     emplacement_destination_id, quantite, prix_unitaire, valeur_totale,
                     motif, reference, user_id, date_mouvement, statut, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Validé', ?)""",
                    (numero, type_mvt, produit_id,
                     emplacement_id if type_mvt in ('Sortie', 'Transfert') else None,
                     emplacement_dest if type_mvt in ('Entrée', 'Transfert') else emplacement_id,
                     quantite, prix_unitaire, valeur_totale,
                     request.form.get('motif', ''),
                     request.form.get('reference', ''),
                     current_user.id if current_user else None,
                     datetime.now().isoformat(),
                     request.form.get('notes', '')))

                # Mettre à jour le stock du produit
                stock_avant = p['stock_actuel']
                if type_mvt == 'Entrée':
                    nouveau_stock = stock_avant + quantite
                    # Mise à jour PMP
                    if prix_unitaire > 0:
                        valeur_avant = stock_avant * p['pmp']
                        valeur_entree = quantite * prix_unitaire
                        nouveau_pmp = (valeur_avant + valeur_entree) / (stock_avant + quantite) if (stock_avant + quantite) > 0 else prix_unitaire
                        c.execute("UPDATE produits SET pmp=? WHERE id=?", (nouveau_pmp, produit_id))
                elif type_mvt == 'Sortie':
                    nouveau_stock = stock_avant - quantite
                elif type_mvt == 'Ajustement':
                    nouveau_stock = quantite
                else:
                    nouveau_stock = stock_avant

                c.execute("UPDATE produits SET stock_actuel=? WHERE id=?", (nouveau_stock, produit_id))

                # Mise à jour stocks par emplacement
                if emplacement_id and type_mvt in ('Entrée', 'Ajustement'):
                    c.execute("""SELECT * FROM stocks WHERE produit_id=? AND emplacement_id=?""",
                              (produit_id, emplacement_id))
                    existing = c.fetchone()
                    if existing:
                        if type_mvt == 'Entrée':
                            c.execute("UPDATE stocks SET quantite = quantite + ? WHERE id=?",
                                      (quantite, existing['id']))
                        else:
                            c.execute("UPDATE stocks SET quantite = ? WHERE id=?",
                                      (quantite, existing['id']))
                    else:
                        c.execute("""INSERT INTO stocks (produit_id, emplacement_id, quantite)
                                     VALUES (?, ?, ?)""",
                                  (produit_id, emplacement_id, quantite))

                if emplacement_id and type_mvt == 'Sortie':
                    c.execute("""SELECT id FROM stocks WHERE produit_id=? AND emplacement_id=?""",
                              (produit_id, emplacement_id))
                    s = c.fetchone()
                    if s:
                        c.execute("UPDATE stocks SET quantite = MAX(0, quantite - ?) WHERE id=?",
                                  (quantite, s['id']))

                # Mettre à jour alertes
                maj_alertes_produit(produit_id, conn)

                conn.commit()
                conn.close()

                if current_user and current_user.is_authenticated:
                    log_action(current_user.id, f'MOUVEMENT_{type_mvt.upper()}', f'{numero} - Qté {quantite}')

                flash(f"✅ Mouvement {numero} enregistré. Nouveau stock : {nouveau_stock:.0f}", "success")
                return redirect('/mouvements')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        # GET
        c.execute("SELECT id, sku, nom, unite, stock_actuel, pmp FROM produits WHERE actif=1 ORDER BY nom")
        produits = c.fetchall()
        c.execute("""SELECT e.id, e.code, e.nom, z.nom as zone_nom, en.nom as entrepot_nom
                     FROM emplacements e
                     JOIN zones z ON e.zone_id = z.id
                     JOIN entrepots en ON z.entrepot_id = en.id
                     WHERE e.actif=1 ORDER BY en.nom, z.nom, e.code""")
        emplacements = c.fetchall()
        conn.close()

        produits_opts = "".join(f'<option value="{p["id"]}" {"selected" if str(p["id"])==produit_id_pre else ""}>{p["sku"]} - {p["nom"][:40]} (Stock: {p["stock_actuel"]:.0f} {p["unite"]})</option>' for p in produits)
        emplacements_opts = "".join(f'<option value="{e["id"]}">{e["entrepot_nom"]} / {e["zone_nom"]} / {e["code"]}</option>' for e in emplacements)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-plus"></i> Nouveau Mouvement</h2>
          <a href="/mouvements" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Type de mouvement *</label>
                <select name="type_mouvement" required>
                  <option value="Entrée">Entrée (réception, retour)</option>
                  <option value="Sortie">Sortie (vente, consommation)</option>
                  <option value="Ajustement">Ajustement (inventaire, correction)</option>
                </select>
              </div>
              <div class="form-group"><label>Produit *</label>
                <select name="produit_id" required>
                  <option value="">-- Sélectionner --</option>
                  {produits_opts}
                </select>
              </div>
              <div class="form-group"><label>Quantité *</label><input type="number" name="quantite" step="0.01" required min="0.01"></div>
              <div class="form-group"><label>Prix unitaire (FCFA)</label><input type="number" name="prix_unitaire" step="0.01" value="0" placeholder="Pour entrée uniquement"></div>
              <div class="form-group"><label>Emplacement source</label>
                <select name="emplacement_id">
                  <option value="">-- Aucun --</option>
                  {emplacements_opts}
                </select>
              </div>
              <div class="form-group"><label>Emplacement destination</label>
                <select name="emplacement_destination_id">
                  <option value="">-- Aucun --</option>
                  {emplacements_opts}
                </select>
              </div>
              <div class="form-group form-full"><label>Motif</label><input type="text" name="motif" placeholder="Ex : Réception commande CMD-2026-0001"></div>
              <div class="form-group form-full"><label>Référence</label><input type="text" name="reference" placeholder="N° BL, facture..."></div>
              <div class="form-group form-full"><label>Notes</label><textarea name="notes" rows="2"></textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer le mouvement</button>
              <a href="/mouvements" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='mouvements', page_title='Nouveau mouvement')

    print("[STOCK_LOGIC] ✅ Routes mouvements enregistrées")

    # ==================== STOCKS CONSOLIDÉS ====================
    @app.route('/stocks')
    @staff_required
    def stocks_liste():
        conn = get_db()
        c = conn.cursor()

        entrepot_filter = request.args.get('entrepot', '')
        search = request.args.get('q', '').strip()

        query = """SELECT s.*, p.sku, p.nom as produit_nom, p.unite, p.pmp,
                          e.code as emp_code, e.type as emp_type,
                          z.nom as zone_nom, en.nom as entrepot_nom,
                          l.numero_lot, l.date_peremption
                   FROM stocks s
                   JOIN produits p ON s.produit_id = p.id
                   JOIN emplacements e ON s.emplacement_id = e.id
                   JOIN zones z ON e.zone_id = z.id
                   JOIN entrepots en ON z.entrepot_id = en.id
                   LEFT JOIN lots l ON s.lot_id = l.id
                   WHERE s.quantite > 0"""
        params = []

        if entrepot_filter:
            query += " AND en.id = ?"
            params.append(int(entrepot_filter))

        if search:
            query += " AND (p.nom LIKE ? OR p.sku LIKE ? OR e.code LIKE ?)"
            params.extend([f'%{search}%'] * 3)

        query += " ORDER BY en.nom, z.nom, e.code, p.nom LIMIT 500"
        c.execute(query, params)
        rows = c.fetchall()

        c.execute("SELECT id, nom FROM entrepots WHERE actif=1 ORDER BY nom")
        entrepots = c.fetchall()

        # Statistiques
        c.execute("""SELECT COUNT(DISTINCT produit_id) as nb_produits,
                            COUNT(*) as nb_emplacements,
                            COALESCE(SUM(quantite * p.pmp), 0) as valeur
                     FROM stocks s JOIN produits p ON s.produit_id = p.id
                     WHERE s.quantite > 0""")
        stats = c.fetchone()
        conn.close()

        ents_opts = "".join(f'<option value="{e["id"]}" {"selected" if entrepot_filter == str(e["id"]) else ""}>{e["nom"]}</option>' for e in entrepots)

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-cubes"></i> Stocks par emplacement</h2>
            <div class="page-subtitle">Vue détaillée du stock physique</div>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-box stat-icon"></i>
            <div class="stat-value">{stats['nb_produits']}</div>
            <div class="stat-label">Produits stockés</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-cubes stat-icon"></i>
            <div class="stat-value">{stats['nb_emplacements']}</div>
            <div class="stat-label">Emplacements actifs</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-coins stat-icon"></i>
            <div class="stat-value">{stats['valeur']:,.0f}</div>
            <div class="stat-label">Valeur (FCFA)</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Stock par emplacement</h3>
            <form method="GET" style="display:flex;gap:8px;flex-wrap:wrap">
              <input type="text" name="q" value="{search}" placeholder="SKU, produit, emplacement..." style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px;width:200px">
              <select name="entrepot" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous entrepôts</option>
                {ents_opts}
              </select>
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Entrepôt</th><th>Zone</th><th>Emplacement</th>
                  <th>Produit</th><th>Lot</th><th>Péremption</th><th>Quantité</th><th>Valeur</th>
                </tr>
              </thead>
              <tbody>
        """
        for s in rows:
            valeur = s['quantite'] * s['pmp']
            content += f"""
            <tr>
              <td><strong>{s['entrepot_nom']}</strong></td>
              <td>{s['zone_nom']}</td>
              <td><code>{s['emp_code']}</code><br><small style="color:#94a3b8">{s['emp_type']}</small></td>
              <td>
                <div style="font-weight:700">{s['produit_nom'][:40]}</div>
                <small style="color:#94a3b8">{s['sku']}</small>
              </td>
              <td>{s['numero_lot'] or '-'}</td>
              <td>{s['date_peremption'] or '-'}</td>
              <td><strong style="color:#059669">{s['quantite']:.0f} {s['unite']}</strong></td>
              <td>{valeur:,.0f} FCFA</td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-inbox"></i><br>Aucun stock</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='stocks', page_title='Stocks')

    print("[STOCK_LOGIC] ✅ Routes stocks enregistrées")

    # ==================== INVENTAIRES ====================
    @app.route('/inventaires')
    @gestionnaire_required
    def inventaires_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT i.*, e.nom as entrepot_nom, z.nom as zone_nom
                     FROM inventaires i
                     LEFT JOIN entrepots e ON i.entrepot_id = e.id
                     LEFT JOIN zones z ON i.zone_id = z.id
                     ORDER BY i.date_debut DESC LIMIT 50""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-clipboard-check"></i> Inventaires</h2>
            <div class="page-subtitle">Sessions d'inventaire physique</div>
          </div>
          <a href="/inventaires/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvel inventaire</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Nom</th><th>Entrepôt</th><th>Zone</th><th>Type</th><th>Début</th><th>Fin</th><th>Produits</th><th>Écarts</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for i in rows:
            badge = 'badge-success' if i['statut'] == 'Validé' else ('badge-info' if i['statut'] == 'En cours' else 'badge-warning')
            content += f"""
            <tr>
              <td><strong>{i['numero']}</strong></td>
              <td>{i['nom']}</td>
              <td>{i['entrepot_nom'] or 'Tous'}</td>
              <td>{i['zone_nom'] or '-'}</td>
              <td><span class="badge badge-info">{i['type']}</span></td>
              <td>{i['date_debut'][:10]}</td>
              <td>{i['date_fin'][:10] if i['date_fin'] else '-'}</td>
              <td><span class="badge badge-primary">{i['nb_produits']}</span></td>
              <td><span class="badge {'badge-danger' if i['nb_ecarts'] > 0 else 'badge-success'}">{i['nb_ecarts']}</span></td>
              <td><span class="badge {badge}">{i['statut']}</span></td>
              <td>
                <a href="/inventaires/{i['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="11" class="empty"><i class="fas fa-clipboard-check"></i><br>Aucun inventaire</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='inventaires', page_title='Inventaires')

    @app.route('/inventaires/nouveau', methods=['GET', 'POST'])
    @gestionnaire_required
    def inventaire_nouveau():
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                numero = gen_numero('INV', 'inventaires')
                entrepot_id = int(request.form['entrepot_id']) if request.form.get('entrepot_id') else None
                zone_id = int(request.form['zone_id']) if request.form.get('zone_id') else None

                c.execute("""INSERT INTO inventaires
                    (numero, nom, entrepot_id, zone_id, type, date_debut, responsable, statut, user_id, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'En cours', ?, ?)""",
                    (numero, request.form['nom'], entrepot_id, zone_id,
                     request.form.get('type', 'Complet'),
                     datetime.now().isoformat(),
                     request.form.get('responsable', ''),
                     current_user.id if current_user else None,
                     request.form.get('notes', '')))
                inventaire_id = c.lastrowid

                # Générer les lignes d'inventaire depuis les stocks existants
                query = """SELECT s.produit_id, s.emplacement_id, s.lot_id,
                                  p.nom, p.unite, s.quantite
                           FROM stocks s
                           JOIN produits p ON s.produit_id = p.id
                           JOIN emplacements emp ON s.emplacement_id = emp.id
                           JOIN zones z ON emp.zone_id = z.id
                           WHERE s.quantite > 0"""
                params = []
                if zone_id:
                    query += " AND z.id = ?"
                    params.append(zone_id)
                elif entrepot_id:
                    query += " AND z.entrepot_id = ?"
                    params.append(entrepot_id)

                c.execute(query, params)
                stocks = c.fetchall()

                for s in stocks:
                    c.execute("""INSERT INTO inventaire_lignes
                        (inventaire_id, produit_id, emplacement_id, lot_id,
                         quantite_theorique, statut)
                        VALUES (?, ?, ?, ?, ?, 'En attente')""",
                        (inventaire_id, s['produit_id'], s['emplacement_id'],
                         s['lot_id'], s['quantite']))

                c.execute("UPDATE inventaires SET nb_produits=? WHERE id=?",
                          (len(stocks), inventaire_id))
                conn.commit()
                conn.close()

                if current_user:
                    log_action(current_user.id, 'CREATE_INVENTAIRE', numero)

                flash(f"✅ Inventaire {numero} créé avec {len(stocks)} lignes", "success")
                return redirect(f'/inventaires/{inventaire_id}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom FROM entrepots WHERE actif=1 ORDER BY nom")
        entrepots = c.fetchall()
        conn.close()
        ents_opts = "".join(f'<option value="{e["id"]}">{e["nom"]}</option>' for e in entrepots)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-clipboard-check"></i> Nouvel Inventaire</h2>
          <a href="/inventaires" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Nom de la session *</label><input type="text" name="nom" required placeholder="Ex : Inventaire annuel 2026"></div>
              <div class="form-group"><label>Type</label>
                <select name="type">
                  <option value="Complet">Complet</option>
                  <option value="Tournant">Tournant</option>
                  <option value="Ciblé">Ciblé</option>
                  <option value="Annuel">Annuel</option>
                </select>
              </div>
              <div class="form-group"><label>Entrepôt</label>
                <select name="entrepot_id">
                  <option value="">Tous les entrepôts</option>
                  {ents_opts}
                </select>
              </div>
              <div class="form-group"><label>Responsable</label><input type="text" name="responsable"></div>
              <div class="form-group form-full"><label>Notes</label><textarea name="notes" rows="2"></textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-play"></i> Démarrer l'inventaire</button>
              <a href="/inventaires" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='inventaires', page_title='Nouvel inventaire')

    @app.route('/inventaires/<int:iid>', methods=['GET', 'POST'])
    @gestionnaire_required
    def inventaire_detail(iid):
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            # Enregistrer les comptages
            try:
                for key, val in request.form.items():
                    if key.startswith('qte_'):
                        ligne_id = int(key.replace('qte_', ''))
                        if val:
                            quantite_comptee = float(val)
                            c.execute("SELECT quantite_theorique FROM inventaire_lignes WHERE id=?", (ligne_id,))
                            row = c.fetchone()
                            if row:
                                ecart = quantite_comptee - row['quantite_theorique']
                                c.execute("""UPDATE inventaire_lignes SET
                                    quantite_comptee=?, ecart=?, date_comptage=?,
                                    statut='Compté' WHERE id=?""",
                                    (quantite_comptee, ecart, datetime.now().isoformat(), ligne_id))

                # Recalculer nb_ecarts
                c.execute("""SELECT COUNT(*) FROM inventaire_lignes
                             WHERE inventaire_id=? AND ABS(ecart) > 0.01""", (iid,))
                nb_ecarts = c.fetchone()[0]
                c.execute("UPDATE inventaires SET nb_ecarts=? WHERE id=?", (nb_ecarts, iid))

                conn.commit()
                conn.close()
                flash("✅ Comptages enregistrés", "success")
                return redirect(f'/inventaires/{iid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("""SELECT i.*, e.nom as entrepot_nom FROM inventaires i
                     LEFT JOIN entrepots e ON i.entrepot_id = e.id WHERE i.id=?""", (iid,))
        inv = c.fetchone()
        if not inv:
            conn.close()
            flash("Inventaire introuvable", "danger")
            return redirect('/inventaires')

        c.execute("""SELECT il.*, p.sku, p.nom as produit_nom, p.unite, p.pmp,
                            e.code as emp_code, l.numero_lot
                     FROM inventaire_lignes il
                     JOIN produits p ON il.produit_id = p.id
                     JOIN emplacements e ON il.emplacement_id = e.id
                     LEFT JOIN lots l ON il.lot_id = l.id
                     WHERE il.inventaire_id = ?
                     ORDER BY e.code, p.nom""", (iid,))
        lignes = c.fetchall()
        conn.close()

        # Stats
        nb_ecarts = sum(1 for l in lignes if l['quantite_comptee'] is not None and abs(l['ecart'] or 0) > 0.01)
        valeur_ecarts = sum((l['ecart'] or 0) * l['pmp'] for l in lignes if l['quantite_comptee'] is not None)
        nb_comptes = sum(1 for l in lignes if l['quantite_comptee'] is not None)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-clipboard-check"></i> {inv['nom']}</h2>
          <div style="display:flex;gap:10px">
            <a href="/inventaires" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-list stat-icon"></i>
            <div class="stat-value">{len(lignes)}</div>
            <div class="stat-label">Lignes</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-check-circle stat-icon"></i>
            <div class="stat-value">{nb_comptes}</div>
            <div class="stat-label">Comptées</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-exclamation-triangle stat-icon"></i>
            <div class="stat-value">{nb_ecarts}</div>
            <div class="stat-label">Écarts</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-money-bill-wave stat-icon"></i>
            <div class="stat-value">{valeur_ecarts:,.0f}</div>
            <div class="stat-label">Valeur écarts (FCFA)</div>
          </div>
        </div>

        <div class="card">
          <form method="POST">
            <div class="card-header">
              <h3><i class="fas fa-edit"></i> Saisie des comptages</h3>
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
            </div>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Emplacement</th><th>Produit</th><th>Lot</th>
                    <th>Théorique</th><th>Compté</th><th>Écart</th><th>Valeur écart</th>
                  </tr>
                </thead>
                <tbody>
        """
        for l in lignes:
            ecart_display = ''
            if l['quantite_comptee'] is not None:
                ecart = l['ecart'] or 0
                if abs(ecart) < 0.01:
                    ecart_display = '<span class="badge badge-success">OK</span>'
                elif ecart > 0:
                    ecart_display = f'<span class="badge badge-warning">+{ecart:.0f}</span>'
                else:
                    ecart_display = f'<span class="badge badge-danger">{ecart:.0f}</span>'

            valeur_ecart = (l['ecart'] or 0) * l['pmp'] if l['quantite_comptee'] is not None else 0

            content += f"""
            <tr>
              <td><code>{l['emp_code']}</code></td>
              <td>
                <div style="font-weight:700">{l['produit_nom'][:40]}</div>
                <small style="color:#94a3b8">{l['sku']}</small>
              </td>
              <td>{l['numero_lot'] or '-'}</td>
              <td><strong>{l['quantite_theorique']:.0f} {l['unite']}</strong></td>
              <td>
                <input type="number" name="qte_{l['id']}" step="0.01"
                       value="{l['quantite_comptee'] if l['quantite_comptee'] is not None else ''}"
                       placeholder="0" style="width:100px;padding:6px;border:2px solid #f1f5f9;border-radius:6px">
              </td>
              <td>{ecart_display}</td>
              <td>{valeur_ecart:,.0f} FCFA</td>
            </tr>
            """
        if not lignes:
            content += '<tr><td colspan="7" class="empty"><i class="fas fa-inbox"></i><br>Aucune ligne</td></tr>'

        content += """
                </tbody>
              </table>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='inventaires', page_title=f"Inventaire {inv['numero']}")

    @app.route('/inventaires/<int:iid>/valider')
    @gestionnaire_required
    def inventaire_valider(iid):
        conn = get_db()
        c = conn.cursor()
        try:
            # Appliquer les écarts aux stocks
            c.execute("""SELECT il.*, p.pmp FROM inventaire_lignes il
                         JOIN produits p ON il.produit_id = p.id
                         WHERE il.inventaire_id = ? AND il.quantite_comptee IS NOT NULL
                         AND ABS(il.ecart) > 0.01""", (iid,))
            lignes = c.fetchall()

            for l in lignes:
                # Ajuster stock produit
                c.execute("""UPDATE produits SET stock_actuel = stock_actuel + ?
                             WHERE id=?""", (l['ecart'], l['produit_id']))

                # Ajuster stock emplacement
                if l['quantite_comptee'] is not None:
                    c.execute("""UPDATE stocks SET quantite = ?
                                 WHERE produit_id=? AND emplacement_id=?
                                 AND (lot_id=? OR (lot_id IS NULL AND ? IS NULL))""",
                              (l['quantite_comptee'], l['produit_id'],
                               l['emplacement_id'], l['lot_id'], l['lot_id']))

            # Marquer inventaire comme validé
            c.execute("""UPDATE inventaires SET statut='Validé', date_fin=?
                         WHERE id=?""", (datetime.now().isoformat(), iid))

            conn.commit()
            conn.close()

            if current_user:
                log_action(current_user.id, 'VALIDATE_INVENTAIRE', f'ID {iid}')

            flash(f"✅ Inventaire validé. {len(lignes)} écarts appliqués.", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect(f'/inventaires/{iid}')

    print("[STOCK_LOGIC] ✅ Routes inventaires enregistrées")

    # ==================== COMMANDES D'ACHAT ====================
    @app.route('/commandes')
    @gestionnaire_required
    def commandes_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT ca.*, f.nom as fournisseur_nom
                     FROM commandes_achat ca
                     LEFT JOIN fournisseurs f ON ca.fournisseur_id = f.id
                     ORDER BY ca.date_commande DESC LIMIT 100""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-shopping-cart"></i> Commandes d'achat</h2>
            <div class="page-subtitle">Commandes fournisseurs</div>
          </div>
          <a href="/commandes/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle commande</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Fournisseur</th><th>Date</th><th>Livraison prévue</th><th>Total</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for cmd in rows:
            badge = 'badge-info'
            if cmd['statut'] == 'Reçue': badge = 'badge-success'
            elif cmd['statut'] == 'Validée': badge = 'badge-primary'
            elif cmd['statut'] == 'Annulée': badge = 'badge-danger'
            elif cmd['statut'] == 'En cours': badge = 'badge-warning'

            content += f"""
            <tr>
              <td><strong>{cmd['numero']}</strong></td>
              <td>{cmd['fournisseur_nom'] or '-'}</td>
              <td>{cmd['date_commande'][:10]}</td>
              <td>{cmd['date_livraison_prevue'] or '-'}</td>
              <td><strong style="color:#059669">{cmd['total']:,.0f}</strong> FCFA</td>
              <td><span class="badge {badge}">{cmd['statut']}</span></td>
              <td>
                <a href="/commandes/{cmd['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="7" class="empty"><i class="fas fa-shopping-cart"></i><br>Aucune commande</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='commandes', page_title='Commandes')

    @app.route('/commandes/nouvelle', methods=['GET', 'POST'])
    @gestionnaire_required
    def commande_nouvelle():
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                numero = gen_numero('CMD', 'commandes_achat')
                fournisseur_id = int(request.form['fournisseur_id'])
                date_livraison = request.form.get('date_livraison_prevue', '')

                c.execute("""INSERT INTO commandes_achat
                    (numero, fournisseur_id, date_commande, date_livraison_prevue,
                     statut, entrepot_destination_id, user_id, notes)
                    VALUES (?, ?, ?, ?, 'Brouillon', ?, ?, ?)""",
                    (numero, fournisseur_id,
                     datetime.now().isoformat(), date_livraison,
                     int(request.form['entrepot_destination_id']) if request.form.get('entrepot_destination_id') else None,
                     current_user.id if current_user else None,
                     request.form.get('notes', '')))
                commande_id = c.lastrowid

                # Lignes
                produits = request.form.getlist('produit_id[]')
                quantites = request.form.getlist('quantite[]')
                prix = request.form.getlist('prix_unitaire[]')

                sous_total = 0
                for pid, q, pu in zip(produits, quantites, prix):
                    if pid and q and pu:
                        c.execute("SELECT nom FROM produits WHERE id=?", (int(pid),))
                        p = c.fetchone()
                        total_ligne = float(q) * float(pu)
                        sous_total += total_ligne

                        c.execute("""INSERT INTO commande_achat_lignes
                            (commande_id, produit_id, designation, quantite, prix_unitaire, total_ligne)
                            VALUES (?, ?, ?, ?, ?, ?)""",
                            (commande_id, int(pid), p['nom'], float(q), float(pu), total_ligne))

                tva = sous_total * 18 / 100
                total = sous_total + tva

                c.execute("""UPDATE commandes_achat SET sous_total=?, tva=?, total=?
                             WHERE id=?""", (sous_total, tva, total, commande_id))

                conn.commit()
                conn.close()

                if current_user:
                    log_action(current_user.id, 'CREATE_COMMANDE', numero)

                flash(f"✅ Commande {numero} créée", "success")
                return redirect(f'/commandes/{commande_id}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom, delai_livraison_jours FROM fournisseurs WHERE actif=1 ORDER BY nom")
        fournisseurs = c.fetchall()
        c.execute("SELECT id, nom FROM entrepots WHERE actif=1 ORDER BY nom")
        entrepots = c.fetchall()
        c.execute("SELECT id, sku, nom, unite, prix_achat, stock_actuel, stock_min FROM produits WHERE actif=1 ORDER BY nom")
        produits = c.fetchall()
        conn.close()

        four_opts = "".join(f'<option value="{f["id"]}">{f["nom"]}</option>' for f in fournisseurs)
        ents_opts = "".join(f'<option value="{e["id"]}">{e["nom"]}</option>' for e in entrepots)

        produits_json = []
        for p in produits:
            produits_json.append({
                'id': p['id'],
                'label': f"{p['sku']} - {p['nom'][:40]} ({p['unite']})",
                'prix': p['prix_achat'],
                'stock': p['stock_actuel'],
                'min': p['stock_min']
            })

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-shopping-cart"></i> Nouvelle Commande d'achat</h2>
          <a href="/commandes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Fournisseur *</label><select name="fournisseur_id" required><option value="">--</option>{four_opts}</select></div>
              <div class="form-group"><label>Livraison prévue</label><input type="date" name="date_livraison_prevue"></div>
              <div class="form-group"><label>Entrepôt destination</label><select name="entrepot_destination_id"><option value="">--</option>{ents_opts}</select></div>
            </div>

            <h3 style="margin:25px 0 15px;color:#059669"><i class="fas fa-list"></i> Lignes de commande</h3>
            <div id="lignes">
              <div class="ligne form-grid" style="margin-bottom:10px;align-items:end">
                <div class="form-group" style="margin:0"><label>Produit</label>
                  <select name="produit_id[]" onchange="majPrix(this)">
                    <option value="">--</option>
                    {''.join(f'<option value="{p["id"]}" data-prix="{p["prix_achat"]}">{p["sku"]} - {p["nom"][:40]}</option>' for p in produits)}
                  </select>
                </div>
                <div class="form-group" style="margin:0"><label>Quantité</label><input type="number" name="quantite[]" step="0.01" value="1"></div>
                <div class="form-group" style="margin:0"><label>Prix unitaire</label><input type="number" name="prix_unitaire[]" step="0.01" value="0"></div>
              </div>
            </div>
            <button type="button" class="btn btn-info btn-sm" onclick="ajouterLigne()"><i class="fas fa-plus"></i> Ajouter une ligne</button>

            <div class="form-group" style="margin-top:20px"><label>Notes</label><textarea name="notes" rows="2"></textarea></div>

            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Créer la commande</button>
              <a href="/commandes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        <script>
          function ajouterLigne() {{
            const container = document.getElementById('lignes');
            const newLigne = document.createElement('div');
            newLigne.className = 'ligne form-grid';
            newLigne.style.marginBottom = '10px';
            newLigne.style.alignItems = 'end';
            newLigne.innerHTML = `
              <div class="form-group" style="margin:0"><label>Produit</label>
                <select name="produit_id[]" onchange="majPrix(this)">
                  <option value="">--</option>
                  {''.join(f'<option value="{p["id"]}" data-prix="{p["prix_achat"]}">{p["sku"]} - {p["nom"][:40]}</option>' for p in produits)}
                </select>
              </div>
              <div class="form-group" style="margin:0"><label>Quantité</label><input type="number" name="quantite[]" step="0.01" value="1"></div>
              <div class="form-group" style="margin:0"><label>Prix unitaire</label><input type="number" name="prix_unitaire[]" step="0.01" value="0"></div>
            `;
            container.appendChild(newLigne);
          }}
          function majPrix(select) {{
            const prix = select.options[select.selectedIndex].dataset.prix;
            if (prix) {{
              select.closest('.ligne').querySelector('input[name="prix_unitaire[]"]').value = prix;
            }}
          }}
        </script>
        """
        return render_page(content, active='commandes', page_title='Nouvelle commande')

    @app.route('/commandes/<int:cid>')
    @gestionnaire_required
    def commande_detail(cid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT ca.*, f.nom as fournisseur_nom, f.telephone as fournisseur_tel,
                            e.nom as entrepot_nom
                     FROM commandes_achat ca
                     LEFT JOIN fournisseurs f ON ca.fournisseur_id = f.id
                     LEFT JOIN entrepots e ON ca.entrepot_destination_id = e.id
                     WHERE ca.id=?""", (cid,))
        cmd = c.fetchone()
        if not cmd:
            conn.close()
            flash("Commande introuvable", "danger")
            return redirect('/commandes')

        c.execute("""SELECT cal.*, p.sku, p.unite FROM commande_achat_lignes cal
                     JOIN produits p ON cal.produit_id = p.id
                     WHERE cal.commande_id=?""", (cid,))
        lignes = c.fetchall()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-shopping-cart"></i> Commande {cmd['numero']}</h2>
          <div style="display:flex;gap:10px">
            {f'<a href="/receptions/nouvelle?commande_id={cid}" class="btn btn-success"><i class="fas fa-truck-ramp-box"></i> Réceptionner</a>' if cmd['statut'] in ['Validée', 'En cours', 'Brouillon'] else ''}
            <a href="/commandes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-info-circle stat-icon"></i>
            <div class="stat-value" style="font-size:1.3rem">{cmd['statut']}</div>
            <div class="stat-label">Statut</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-coins stat-icon"></i>
            <div class="stat-value">{cmd['total']:,.0f}</div>
            <div class="stat-label">Total (FCFA)</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-calendar stat-icon"></i>
            <div class="stat-value" style="font-size:1.1rem">{cmd['date_commande'][:10]}</div>
            <div class="stat-label">Date commande</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
          <div class="form-grid">
            <div><strong>Fournisseur :</strong> {cmd['fournisseur_nom'] or '-'}</div>
            <div><strong>Téléphone :</strong> {cmd['fournisseur_tel'] or '-'}</div>
            <div><strong>Entrepôt :</strong> {cmd['entrepot_nom'] or '-'}</div>
            <div><strong>Livraison prévue :</strong> {cmd['date_livraison_prevue'] or '-'}</div>
          </div>
          {('<p style="margin-top:15px"><strong>Notes :</strong> ' + cmd['notes'] + '</p>') if cmd['notes'] else ''}
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-list"></i> Lignes de commande</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Produit</th><th>Qté commandée</th><th>Qté reçue</th><th>Prix unitaire</th><th>Total ligne</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for l in lignes:
            badge = 'badge-success' if l['statut'] == 'Reçue' else 'badge-warning'
            content += f"""
            <tr>
              <td><strong>{l['designation'][:50]}</strong><br><small style="color:#94a3b8">{l['sku']}</small></td>
              <td><strong>{l['quantite']:.0f} {l['unite']}</strong></td>
              <td>{l['quantite_recue']:.0f} {l['unite']}</td>
              <td>{l['prix_unitaire']:,.0f} FCFA</td>
              <td><strong>{l['total_ligne']:,.0f} FCFA</strong></td>
              <td><span class="badge {badge}">{l['statut']}</span></td>
            </tr>
            """
        content += f"""
              </tbody>
              <tfoot>
                <tr style="background:#ecfdf5"><td colspan="4" style="text-align:right"><strong>Sous-total</strong></td><td><strong>{cmd['sous_total']:,.0f} FCFA</strong></td><td></td></tr>
                <tr><td colspan="4" style="text-align:right"><strong>TVA</strong></td><td><strong>{cmd['tva']:,.0f} FCFA</strong></td><td></td></tr>
                <tr style="background:#d1fae5"><td colspan="4" style="text-align:right"><strong style="font-size:1.1rem">TOTAL</strong></td><td><strong style="color:#059669;font-size:1.2rem">{cmd['total']:,.0f} FCFA</strong></td><td></td></tr>
              </tfoot>
            </table>
          </div>
        </div>
        """
        return render_page(content, active='commandes', page_title=f"Commande {cmd['numero']}")

    print("[STOCK_LOGIC] ✅ Routes commandes enregistrées")

    # ==================== RÉCEPTIONS ====================
    @app.route('/receptions')
    @gestionnaire_required
    def receptions_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT r.*, f.nom as fournisseur_nom, e.nom as entrepot_nom
                     FROM receptions r
                     LEFT JOIN fournisseurs f ON r.fournisseur_id = f.id
                     LEFT JOIN entrepots e ON r.entrepot_id = e.id
                     ORDER BY r.date_reception DESC LIMIT 100""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-truck-ramp-box"></i> Réceptions</h2>
            <div class="page-subtitle">Réceptions de marchandises</div>
          </div>
          <a href="/receptions/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle réception</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Fournisseur</th><th>Entrepôt</th><th>Date</th><th>BL</th><th>Lignes</th><th>Écarts</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for r in rows:
            badge = 'badge-success' if r['statut'] == 'Validée' else 'badge-warning'
            content += f"""
            <tr>
              <td><strong>{r['numero']}</strong></td>
              <td>{r['fournisseur_nom'] or '-'}</td>
              <td>{r['entrepot_nom'] or '-'}</td>
              <td>{r['date_reception'][:10]}</td>
              <td>{r['bon_livraison'] or '-'}</td>
              <td><span class="badge badge-info">{r['nb_lignes']}</span></td>
              <td><span class="badge {'badge-danger' if r['nb_ecarts'] > 0 else 'badge-success'}">{r['nb_ecarts']}</span></td>
              <td><span class="badge {badge}">{r['statut']}</span></td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-truck-ramp-box"></i><br>Aucune réception</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='receptions', page_title='Réceptions')

    print("[STOCK_LOGIC] ✅ Routes réceptions enregistrées")

    # ==================== ALERTES ====================
    @app.route('/alertes')
    @staff_required
    def alertes_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT a.*, p.nom as produit_nom, p.sku
                     FROM alertes a
                     LEFT JOIN produits p ON a.produit_id = p.id
                     WHERE a.statut = 'Active'
                     ORDER BY CASE a.priorite WHEN 'Critique' THEN 1 WHEN 'Haute' THEN 2 WHEN 'Normale' THEN 3 ELSE 4 END,
                     a.date_alerte DESC""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-bell"></i> Alertes actives</h2>
            <div class="page-subtitle">Notifications automatiques du système</div>
          </div>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Priorité</th><th>Type</th><th>Produit</th><th>Message</th><th>Date</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for a in rows:
            prio_badge = 'badge-danger' if a['priorite'] == 'Critique' else ('badge-warning' if a['priorite'] == 'Haute' else 'badge-info')
            content += f"""
            <tr>
              <td><span class="badge {prio_badge}">{a['priorite']}</span></td>
              <td><strong>{a['type_alerte']}</strong></td>
              <td>{a['produit_nom'][:40] if a['produit_nom'] else '-'}<br><small>{a['sku'] or ''}</small></td>
              <td>{a['message']}</td>
              <td>{a['date_alerte'][:16]}</td>
              <td>
                <a href="/alertes/{a['id']}/resoudre" class="btn btn-success btn-sm" onclick="return confirm('Marquer comme résolue ?')"><i class="fas fa-check"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-check-circle" style="color:#10b981"></i><br>Aucune alerte active 🎉</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='alertes', page_title='Alertes')

    @app.route('/alertes/<int:aid>/resoudre')
    @staff_required
    def alerte_resoudre(aid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("""UPDATE alertes SET statut='Résolue', date_traitement=?,
                         user_id=? WHERE id=?""",
                      (datetime.now().isoformat(),
                       current_user.id if current_user else None, aid))
            conn.commit()
            conn.close()
            flash("✅ Alerte résolue", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/alertes')

    print("[STOCK_LOGIC] ✅ Routes alertes enregistrées")

    # ==================== RAPPORTS ====================
    @app.route('/rapports')
    @staff_required
    def rapports():
        conn = get_db()
        c = conn.cursor()

        # Valorisation globale
        c.execute("""SELECT
                        COUNT(*) as nb_produits,
                        COALESCE(SUM(stock_actuel * pmp), 0) as valeur_totale,
                        COALESCE(SUM(stock_actuel), 0) as qte_totale
                     FROM produits WHERE actif=1""")
        valo = c.fetchone()

        # Stock par catégorie
        c.execute("""SELECT cat.nom as cat_nom, cat.couleur,
                            COUNT(p.id) as nb_produits,
                            COALESCE(SUM(p.stock_actuel * p.pmp), 0) as valeur
                     FROM categories cat
                     LEFT JOIN produits p ON p.categorie_id = cat.id AND p.actif=1
                     WHERE cat.actif=1
                     GROUP BY cat.id ORDER BY valeur DESC""")
        par_cat = c.fetchall()

        # Stock par entrepôt
        c.execute("""SELECT en.nom as entrepot_nom,
                            COUNT(DISTINCT s.produit_id) as nb_produits,
                            COALESCE(SUM(s.quantite), 0) as qte,
                            COALESCE(SUM(s.quantite * p.pmp), 0) as valeur
                     FROM stocks s
                     JOIN produits p ON s.produit_id = p.id
                     JOIN emplacements emp ON s.emplacement_id = emp.id
                     JOIN zones z ON emp.zone_id = z.id
                     JOIN entrepots en ON z.entrepot_id = en.id
                     WHERE s.quantite > 0
                     GROUP BY en.id ORDER BY valeur DESC""")
        par_entrepot = c.fetchall()

        # Top 10 produits par valeur
        c.execute("""SELECT sku, nom, stock_actuel, unite, pmp,
                            (stock_actuel * pmp) as valeur
                     FROM produits WHERE actif=1
                     ORDER BY valeur DESC LIMIT 10""")
        top_produits = c.fetchall()

        # Mouvements récents (30 jours)
        c.execute("""SELECT type_mouvement, COUNT(*) as nb,
                            COALESCE(SUM(valeur_totale), 0) as valeur
                     FROM mouvements
                     WHERE date(date_mouvement) >= date('now', '-30 days')
                     GROUP BY type_mouvement""")
        mouvements = c.fetchall()

        conn.close()

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-chart-line"></i> Rapports & Analyses</h2>
            <div class="page-subtitle">Valorisation, répartition et tendances</div>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-box stat-icon"></i>
            <div class="stat-value">{valo['nb_produits']}</div>
            <div class="stat-label">Produits actifs</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-cubes stat-icon"></i>
            <div class="stat-value">{valo['qte_totale']:,.0f}</div>
            <div class="stat-label">Quantité totale</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-coins stat-icon"></i>
            <div class="stat-value">{valo['valeur_totale']:,.0f}</div>
            <div class="stat-label">Valeur totale (FCFA)</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-tags"></i> Valorisation par catégorie</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Catégorie</th><th>Produits</th><th>Valeur (FCFA)</th><th>%</th></tr></thead>
              <tbody>
        """
        for cat in par_cat:
            pct = (cat['valeur'] / valo['valeur_totale'] * 100) if valo['valeur_totale'] > 0 else 0
            content += f"""
            <tr>
              <td>
                <i class="fas fa-circle" style="color:{cat['couleur'] or '#059669'};font-size:0.7rem"></i>
                <strong>{cat['cat_nom']}</strong>
              </td>
              <td>{cat['nb_produits']}</td>
              <td><strong>{cat['valeur']:,.0f}</strong></td>
              <td>{pct:.1f}%</td>
            </tr>
            """
        content += "</tbody></table></div></div>"

        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-warehouse"></i> Valorisation par entrepôt</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Entrepôt</th><th>Produits</th><th>Quantité</th><th>Valeur (FCFA)</th></tr></thead>
              <tbody>
        """
        for e in par_entrepot:
            content += f"""
            <tr>
              <td><strong>{e['entrepot_nom']}</strong></td>
              <td>{e['nb_produits']}</td>
              <td>{e['qte']:,.0f}</td>
              <td><strong>{e['valeur']:,.0f}</strong></td>
            </tr>
            """
        content += "</tbody></table></div></div>"

        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-fire"></i> Top 10 produits par valeur</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>#</th><th>SKU</th><th>Produit</th><th>Stock</th><th>PMP</th><th>Valeur</th></tr></thead>
              <tbody>
        """
        for i, p in enumerate(top_produits, 1):
            medal = '🥇' if i == 1 else ('🥈' if i == 2 else ('🥉' if i == 3 else ''))
            content += f"""
            <tr>
              <td><strong>{medal} {i}</strong></td>
              <td>{p['sku']}</td>
              <td>{p['nom'][:45]}</td>
              <td>{p['stock_actuel']:.0f} {p['unite']}</td>
              <td>{p['pmp']:,.0f}</td>
              <td><strong style="color:#059669">{p['valeur']:,.0f} FCFA</strong></td>
            </tr>
            """
        content += "</tbody></table></div></div>"

        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-arrows-rotate"></i> Mouvements 30 derniers jours</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Type</th><th>Nombre</th><th>Valeur totale (FCFA)</th></tr></thead>
              <tbody>
        """
        for m in mouvements:
            content += f"""
            <tr>
              <td><strong>{m['type_mouvement']}</strong></td>
              <td>{m['nb']}</td>
              <td>{m['valeur']:,.0f}</td>
            </tr>
            """
        if not mouvements:
            content += '<tr><td colspan="3" class="empty">Aucun mouvement</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='rapports', page_title='Rapports')

    print("[STOCK_LOGIC] ✅ Routes rapports enregistrées")
