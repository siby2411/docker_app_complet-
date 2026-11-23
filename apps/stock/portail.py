"""
Portail Magasinier + Portail Gestionnaire
Vues personnalisées par rôle pour Omega Stock
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


def register_portail_routes(app, render_page):
    """Portails par rôle"""

    # ==================== PORTAIL MAGASINIER ====================
    @app.route('/magasinier/accueil')
    @magasinier_required
    def magasinier_accueil():
        conn = get_db()
        c = conn.cursor()

        # Mes mouvements du jour
        c.execute("""SELECT COUNT(*) FROM mouvements
                     WHERE user_id = ? AND date(date_mouvement) = date('now')""",
                  (current_user.id if current_user else 0,))
        mes_mvts_jour = c.fetchone()[0]

        # Mouvements total du jour
        c.execute("""SELECT COUNT(*) FROM mouvements
                     WHERE date(date_mouvement) = date('now')""")
        mvts_jour = c.fetchone()[0]

        # Mes mouvements de la semaine
        c.execute("""SELECT COUNT(*) FROM mouvements
                     WHERE user_id = ? AND date(date_mouvement) >= date('now', '-7 days')""",
                  (current_user.id if current_user else 0,))
        mes_mvts_semaine = c.fetchone()[0]

        # Produits en alerte
        c.execute("""SELECT COUNT(*) FROM produits
                     WHERE actif=1 AND stock_actuel <= stock_min""")
        alertes = c.fetchone()[0]

        # Mes derniers mouvements
        c.execute("""SELECT m.*, p.nom as produit_nom, p.sku, p.unite
                     FROM mouvements m
                     LEFT JOIN produits p ON m.produit_id = p.id
                     WHERE m.user_id = ?
                     ORDER BY m.date_mouvement DESC LIMIT 10""",
                  (current_user.id if current_user else 0,))
        mes_mvts = c.fetchall()

        # Tâches en attente
        c.execute("""SELECT COUNT(*) FROM inventaires WHERE statut='En cours'""")
        inventaires_en_cours = c.fetchone()[0]

        c.execute("""SELECT COUNT(*) FROM commandes_achat WHERE statut IN ('Validée', 'En cours')""")
        commandes_a_receptionner = c.fetchone()[0]

        conn.close()

        content = f"""
        <div class="hero" style="background:linear-gradient(135deg,#0891b2,#06b6d4)">
          <h1>Bonjour <span>{current_user.prenom}</span> 👋</h1>
          <p>Espace magasinier — Vos mouvements et tâches du jour</p>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-arrows-rotate stat-icon"></i>
            <div class="stat-value">{mes_mvts_jour}</div>
            <div class="stat-label">Mes mouvements (jour)</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-chart-line stat-icon"></i>
            <div class="stat-value">{mes_mvts_semaine}</div>
            <div class="stat-label">Mes mouvements (7j)</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-users stat-icon"></i>
            <div class="stat-value">{mvts_jour}</div>
            <div class="stat-label">Mouvements équipe (jour)</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-clipboard-check stat-icon"></i>
            <div class="stat-value">{inventaires_en_cours}</div>
            <div class="stat-label">Inventaires en cours</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-exclamation-triangle stat-icon"></i>
            <div class="stat-value">{alertes}</div>
            <div class="stat-label">Alertes stock</div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-bottom:25px">
          <a href="/mouvements/nouveau?type=Entrée" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:30px;border-left:5px solid #10b981;cursor:pointer;transition:0.3s" onmouseover="this.style.transform='translateY(-5px)'" onmouseout="this.style.transform=''">
              <i class="fas fa-arrow-down" style="font-size:2.5rem;color:#10b981;margin-bottom:15px"></i>
              <div style="font-size:1.2rem;font-weight:900;color:#064e3b">Enregistrer une entrée</div>
              <div style="color:#64748b;font-size:0.85rem;margin-top:5px">Réception, retour</div>
            </div>
          </a>
          <a href="/mouvements/nouveau?type=Sortie" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:30px;border-left:5px solid #dc2626;cursor:pointer;transition:0.3s" onmouseover="this.style.transform='translateY(-5px)'" onmouseout="this.style.transform=''">
              <i class="fas fa-arrow-up" style="font-size:2.5rem;color:#dc2626;margin-bottom:15px"></i>
              <div style="font-size:1.2rem;font-weight:900;color:#064e3b">Enregistrer une sortie</div>
              <div style="color:#64748b;font-size:0.85rem;margin-top:5px">Vente, consommation</div>
            </div>
          </a>
          <a href="/inventaires" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:30px;border-left:5px solid #f59e0b;cursor:pointer;transition:0.3s" onmouseover="this.style.transform='translateY(-5px)'" onmouseout="this.style.transform=''">
              <i class="fas fa-clipboard-check" style="font-size:2.5rem;color:#f59e0b;margin-bottom:15px"></i>
              <div style="font-size:1.2rem;font-weight:900;color:#064e3b">Inventaires</div>
              <div style="color:#64748b;font-size:0.85rem;margin-top:5px">{inventaires_en_cours} en cours</div>
            </div>
          </a>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-clock-rotate-left"></i> Mes derniers mouvements</h3>
            <a href="/mouvements" class="btn btn-primary btn-sm"><i class="fas fa-list"></i> Voir tout</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Type</th><th>Produit</th><th>Quantité</th><th>Motif</th><th>Date</th></tr></thead>
              <tbody>
        """
        for m in mes_mvts:
            type_badge = 'badge-success' if m['type_mouvement'] == 'Entrée' else ('badge-danger' if m['type_mouvement'] == 'Sortie' else 'badge-info')
            signe = '+' if m['type_mouvement'] == 'Entrée' else ('-' if m['type_mouvement'] == 'Sortie' else '↔')

            content += f"""
            <tr>
              <td><strong>{m['numero']}</strong></td>
              <td><span class="badge {type_badge}">{m['type_mouvement']}</span></td>
              <td>{m['produit_nom'][:40] if m['produit_nom'] else '-'}<br><small style="color:#94a3b8">{m['sku'] or ''}</small></td>
              <td><strong>{signe}{m['quantite']:.0f} {m['unite'] or ''}</strong></td>
              <td>{m['motif'][:30] if m['motif'] else '-'}</td>
              <td>{m['date_mouvement'][:16]}</td>
            </tr>
            """
        if not mes_mvts:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-inbox"></i><br>Aucun mouvement</td></tr>'

        content += """
              </tbody>
            </table>
          </div>
        </div>
        """
        return render_page(content, active='dashboard', page_title='Accueil magasinier')

    # ==================== MOUVEMENT RAPIDE (magasinier) ====================
    @app.route('/magasinier/mouvement-rapide', methods=['GET', 'POST'])
    @magasinier_required
    def magasinier_mouvement_rapide():
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                from stock_logic import gen_numero, maj_alertes_produit

                type_mvt = request.form['type_mouvement']
                produit_id = int(request.form['produit_id'])
                quantite = float(request.form['quantite'])
                emplacement_id = int(request.form['emplacement_id']) if request.form.get('emplacement_id') else None
                prix_unitaire = float(request.form.get('prix_unitaire') or 0)

                numero = gen_numero('MVT', 'mouvements')

                c.execute("SELECT * FROM produits WHERE id=?", (produit_id,))
                p = c.fetchone()

                valeur_totale = quantite * (prix_unitaire if prix_unitaire > 0 else p['pmp'])

                c.execute("""INSERT INTO mouvements
                    (numero, type_mouvement, produit_id, emplacement_destination_id,
                     quantite, prix_unitaire, valeur_totale, motif, user_id,
                     date_mouvement, statut)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Validé')""",
                    (numero, type_mvt, produit_id,
                     emplacement_id if type_mvt == 'Entrée' else None,
                     quantite, prix_unitaire, valeur_totale,
                     request.form.get('motif', f'{type_mvt} rapide'),
                     current_user.id if current_user else None,
                     datetime.now().isoformat()))

                # Stock
                stock_avant = p['stock_actuel']
                if type_mvt == 'Entrée':
                    nouveau_stock = stock_avant + quantite
                    if prix_unitaire > 0:
                        val_av = stock_avant * p['pmp']
                        val_ent = quantite * prix_unitaire
                        nv_pmp = (val_av + val_ent) / (stock_avant + quantite) if (stock_avant + quantite) > 0 else prix_unitaire
                        c.execute("UPDATE produits SET pmp=? WHERE id=?", (nv_pmp, produit_id))
                else:
                    nouveau_stock = max(0, stock_avant - quantite)

                c.execute("UPDATE produits SET stock_actuel=? WHERE id=?", (nouveau_stock, produit_id))

                # Emplacement
                if emplacement_id and type_mvt == 'Entrée':
                    c.execute("SELECT id FROM stocks WHERE produit_id=? AND emplacement_id=?",
                              (produit_id, emplacement_id))
                    s = c.fetchone()
                    if s:
                        c.execute("UPDATE stocks SET quantite = quantite + ? WHERE id=?", (quantite, s['id']))
                    else:
                        c.execute("INSERT INTO stocks (produit_id, emplacement_id, quantite) VALUES (?, ?, ?)",
                                  (produit_id, emplacement_id, quantite))

                maj_alertes_produit(produit_id, conn)

                conn.commit()
                conn.close()

                flash(f"✅ Mouvement {numero} enregistré. Nouveau stock : {nouveau_stock:.0f}", "success")
                return redirect('/magasinier/accueil')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        # GET
        c.execute("SELECT id, sku, nom, unite, stock_actuel FROM produits WHERE actif=1 ORDER BY nom LIMIT 200")
        produits = c.fetchall()
        c.execute("""SELECT e.id, e.code, z.nom as zone_nom, en.nom as entrepot_nom
                     FROM emplacements e
                     JOIN zones z ON e.zone_id = z.id
                     JOIN entrepots en ON z.entrepot_id = en.id
                     WHERE e.actif=1 ORDER BY en.nom, z.nom, e.code LIMIT 100""")
        emplacements = c.fetchall()
        conn.close()

        produits_opts = "".join(f'<option value="{p["id"]}">{p["sku"]} - {p["nom"][:40]} (Stock: {p["stock_actuel"]:.0f} {p["unite"]})</option>' for p in produits)
        emp_opts = "".join(f'<option value="{e["id"]}">{e["entrepot_nom"]} / {e["zone_nom"]} / {e["code"]}</option>' for e in emplacements)

        type_pre = request.args.get('type', 'Entrée')

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-bolt"></i> Mouvement rapide</h2>
          <a href="/magasinier/accueil" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Type *</label>
                <select name="type_mouvement" required style="font-size:1.1rem;padding:15px">
                  <option value="Entrée" {"selected" if type_pre == "Entrée" else ""}>⬇️ Entrée</option>
                  <option value="Sortie" {"selected" if type_pre == "Sortie" else ""}>⬆️ Sortie</option>
                </select>
              </div>
              <div class="form-group"><label>Quantité *</label>
                <input type="number" name="quantite" step="0.01" required min="0.01" style="font-size:1.2rem;padding:15px;text-align:center;font-weight:700">
              </div>
              <div class="form-group form-full"><label>Produit * (tapez pour rechercher)</label>
                <input type="text" id="produitSearch" placeholder="Tapez SKU ou nom..." style="padding:15px;font-size:1rem;margin-bottom:5px">
                <select name="produit_id" id="produitSelect" required style="font-size:1rem;padding:12px">
                  <option value="">-- Sélectionner --</option>
                  {produits_opts}
                </select>
              </div>
              <div class="form-group"><label>Emplacement destination</label>
                <select name="emplacement_id">
                  <option value="">-- Aucun --</option>
                  {emp_opts}
                </select>
              </div>
              <div class="form-group"><label>Prix unitaire (FCFA)</label>
                <input type="number" name="prix_unitaire" step="0.01" value="0" placeholder="Pour entrée">
              </div>
              <div class="form-group form-full"><label>Motif</label>
                <input type="text" name="motif" placeholder="Raison du mouvement">
              </div>
            </div>
            <div style="margin-top:25px">
              <button type="submit" class="btn btn-success" style="width:100%;justify-content:center;padding:18px;font-size:1.1rem">
                <i class="fas fa-check-circle"></i> Valider le mouvement
              </button>
            </div>
          </form>
        </div>
        <script>
          document.getElementById('produitSearch').addEventListener('keyup', function() {{
            const filter = this.value.toUpperCase();
            const select = document.getElementById('produitSelect');
            for (let i = 0; i < select.options.length; i++) {{
              const txt = select.options[i].text.toUpperCase();
              select.options[i].style.display = txt.indexOf(filter) > -1 ? '' : 'none';
            }}
          }});
        </script>
        """
        return render_page(content, active='dashboard', page_title='Mouvement rapide')

    print("[PORTAIL] ✅ Routes magasinier enregistrées")

    # ==================== PORTAIL GESTIONNAIRE ====================
    @app.route('/gestionnaire/accueil')
    @gestionnaire_required
    def gestionnaire_accueil():
        conn = get_db()
        c = conn.cursor()

        # KPIs gestionnaire
        c.execute("""SELECT COALESCE(SUM(stock_actuel * pmp), 0) FROM produits WHERE actif=1""")
        valeur_stock = c.fetchone()[0]

        c.execute("""SELECT COUNT(*) FROM produits WHERE actif=1 AND stock_actuel <= stock_min""")
        alertes = c.fetchone()[0]

        c.execute("""SELECT COUNT(*) FROM commandes_achat WHERE statut IN ('Brouillon', 'Validée')""")
        commandes_a_valider = c.fetchone()[0]

        c.execute("""SELECT COUNT(*) FROM inventaires WHERE statut='En cours'""")
        inventaires_en_cours = c.fetchone()[0]

        # Mouvements 7 jours par type
        c.execute("""SELECT type_mouvement, COUNT(*) as nb
                     FROM mouvements
                     WHERE date(date_mouvement) >= date('now', '-7 days')
                     GROUP BY type_mouvement""")
        mvts = {r['type_mouvement']: r['nb'] for r in c.fetchall()}

        # Top mouvements
        c.execute("""SELECT m.*, p.nom as produit_nom, p.sku, u.nom as u_nom, u.prenom as u_prenom
                     FROM mouvements m
                     LEFT JOIN produits p ON m.produit_id = p.id
                     LEFT JOIN utilisateurs u ON m.user_id = u.id
                     ORDER BY m.date_mouvement DESC LIMIT 15""")
        derniers_mvts = c.fetchall()

        # Top produits actifs
        c.execute("""SELECT p.sku, p.nom, p.stock_actuel, p.unite, p.pmp,
                            (SELECT COUNT(*) FROM mouvements WHERE produit_id = p.id
                             AND date(date_mouvement) >= date('now', '-30 days')) as mvts_30j
                     FROM produits p WHERE p.actif=1
                     ORDER BY mvts_30j DESC LIMIT 10""")
        top_produits = c.fetchall()

        # Commandes à valider
        c.execute("""SELECT ca.*, f.nom as fournisseur_nom
                     FROM commandes_achat ca
                     LEFT JOIN fournisseurs f ON ca.fournisseur_id = f.id
                     WHERE ca.statut IN ('Brouillon', 'Validée')
                     ORDER BY ca.date_commande DESC LIMIT 5""")
        commandes = c.fetchall()

        conn.close()

        content = f"""
        <div class="hero" style="background:linear-gradient(135deg,#059669,#10b981)">
          <h1>Bonjour <span>{current_user.prenom}</span> 👋</h1>
          <p>Espace gestionnaire — Pilotage et validation</p>
        </div>

        <div class="stats">
          <div class="stat-card green">
            <i class="fas fa-coins stat-icon"></i>
            <div class="stat-value">{valeur_stock:,.0f}</div>
            <div class="stat-label">Valeur stock (FCFA)</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-exclamation-triangle stat-icon"></i>
            <div class="stat-value">{alertes}</div>
            <div class="stat-label">Alertes stock</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-shopping-cart stat-icon"></i>
            <div class="stat-value">{commandes_a_valider}</div>
            <div class="stat-label">Commandes à valider</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-clipboard-check stat-icon"></i>
            <div class="stat-value">{inventaires_en_cours}</div>
            <div class="stat-label">Inventaires</div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:15px;margin-bottom:25px">
          <a href="/commandes" style="text-decoration:none">
            <div class="card" style="padding:25px;border-left:5px solid #059669;cursor:pointer">
              <div style="display:flex;align-items:center;gap:15px">
                <i class="fas fa-shopping-cart" style="font-size:2rem;color:#059669"></i>
                <div>
                  <div style="font-weight:900;color:#064e3b;font-size:1.1rem">Commandes</div>
                  <div style="color:#64748b;font-size:0.85rem">{commandes_a_valider} à traiter</div>
                </div>
              </div>
            </div>
          </a>
          <a href="/rapports" style="text-decoration:none">
            <div class="card" style="padding:25px;border-left:5px solid #0891b2;cursor:pointer">
              <div style="display:flex;align-items:center;gap:15px">
                <i class="fas fa-chart-line" style="font-size:2rem;color:#0891b2"></i>
                <div>
                  <div style="font-weight:900;color:#064e3b;font-size:1.1rem">Rapports</div>
                  <div style="color:#64748b;font-size:0.85rem">Valorisation & analyses</div>
                </div>
              </div>
            </div>
          </a>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="card">
            <div class="card-header"><h3><i class="fas fa-arrows-rotate"></i> Derniers mouvements</h3></div>
        """
        for m in derniers_mvts[:8]:
            type_badge = 'badge-success' if m['type_mouvement'] == 'Entrée' else ('badge-danger' if m['type_mouvement'] == 'Sortie' else 'badge-info')
            signe = '+' if m['type_mouvement'] == 'Entrée' else ('-' if m['type_mouvement'] == 'Sortie' else '↔')
            content += f"""
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px dashed #ecfdf5">
              <div style="flex:1">
                <div style="font-weight:700;font-size:0.85rem">{m['produit_nom'][:35] if m['produit_nom'] else '-'}</div>
                <small style="color:#94a3b8">{m['numero']} · {m['u_prenom'] or '?'} {m['u_nom'] or ''}</small>
              </div>
              <div style="text-align:right">
                <span class="badge {type_badge}">{signe}{m['quantite']:.0f}</span>
                <div style="font-size:0.7rem;color:#94a3b8;margin-top:3px">{m['date_mouvement'][11:16]}</div>
              </div>
            </div>
            """
        if not derniers_mvts:
            content += '<div class="empty" style="padding:20px">Aucun mouvement</div>'

        content += """
          </div>

          <div class="card">
            <div class="card-header"><h3><i class="fas fa-fire"></i> Top produits actifs (30j)</h3></div>
        """
        for i, p in enumerate(top_produits, 1):
            medal = '🥇' if i == 1 else ('🥈' if i == 2 else ('🥉' if i == 3 else ''))
            content += f"""
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px dashed #ecfdf5">
              <div style="flex:1">
                <div style="font-weight:700;font-size:0.85rem">{medal} {p['nom'][:35]}</div>
                <small style="color:#94a3b8">{p['sku']} · Stock: {p['stock_actuel']:.0f} {p['unite']}</small>
              </div>
              <div style="text-align:right">
                <span class="badge badge-info">{p['mvts_30j']} mvt</span>
              </div>
            </div>
            """
        if not top_produits:
            content += '<div class="empty" style="padding:20px">Aucun produit actif</div>'

        content += """
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-shopping-cart"></i> Commandes en attente</h3>
            <a href="/commandes" class="btn btn-primary btn-sm"><i class="fas fa-list"></i> Voir tout</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Fournisseur</th><th>Date</th><th>Total</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for cmd in commandes:
            badge = 'badge-info' if cmd['statut'] == 'Brouillon' else 'badge-warning'
            content += f"""
            <tr>
              <td><strong>{cmd['numero']}</strong></td>
              <td>{cmd['fournisseur_nom'] or '-'}</td>
              <td>{cmd['date_commande'][:10]}</td>
              <td><strong>{cmd['total']:,.0f}</strong> FCFA</td>
              <td><span class="badge {badge}">{cmd['statut']}</span></td>
              <td>
                <a href="/commandes/{cmd['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
                <a href="/receptions/nouvelle?commande_id={cmd['id']}" class="btn btn-success btn-sm" title="Réceptionner"><i class="fas fa-truck-ramp-box"></i></a>
              </td>
            </tr>
            """
        if not commandes:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-inbox"></i><br>Aucune commande</td></tr>'

        content += """
              </tbody>
            </table>
          </div>
        </div>
        """
        return render_page(content, active='dashboard', page_title='Accueil gestionnaire')

    print("[PORTAIL] ✅ Routes gestionnaire enregistrées")

    # ==================== VALIDATION INVENTAIRE (raccourci) ====================
    @app.route('/gestionnaire/inventaires-a-valider')
    @gestionnaire_required
    def gestionnaire_inventaires_a_valider():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT i.*, e.nom as entrepot_nom
                     FROM inventaires i
                     LEFT JOIN entrepots e ON i.entrepot_id = e.id
                     WHERE i.statut = 'En cours'
                     ORDER BY i.date_debut DESC""")
        inventaires = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <h2><i class="fas fa-clipboard-check"></i> Inventaires à valider</h2>
          <a href="/gestionnaire/accueil" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Nom</th><th>Entrepôt</th><th>Début</th><th>Lignes</th><th>Écarts</th><th>Valeur écarts</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for i in inventaires:
            content += f"""
            <tr>
              <td><strong>{i['numero']}</strong></td>
              <td>{i['nom']}</td>
              <td>{i['entrepot_nom'] or '-'}</td>
              <td>{i['date_debut'][:10]}</td>
              <td><span class="badge badge-info">{i['nb_produits']}</span></td>
              <td><span class="badge {'badge-danger' if i['nb_ecarts'] > 0 else 'badge-success'}">{i['nb_ecarts']}</span></td>
              <td><strong>{i['valeur_ecarts']:,.0f}</strong> FCFA</td>
              <td>
                <a href="/inventaires/{i['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i> Voir</a>
                <a href="/inventaires/{i['id']}/valider" class="btn btn-success btn-sm" onclick="return confirm('Valider et appliquer les écarts ?')"><i class="fas fa-check"></i> Valider</a>
              </td>
            </tr>
            """
        if not inventaires:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-check-circle" style="color:#10b981"></i><br>Aucun inventaire à valider 🎉</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='dashboard', page_title='Inventaires à valider')

    print("[PORTAIL] ✅ Routes validation enregistrées")
