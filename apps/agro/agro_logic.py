"""
🌾 Omega Agro-Industrie — Logique métier complète
Production · Stocks · Contrats · Fournisseurs · Yield management
"""
from flask import Blueprint, request, redirect, flash, jsonify
from flask_login import current_user, login_required
from datetime import datetime, timedelta

logic_bp = Blueprint('agro_logic', __name__)
_deps = {}


def init_logic(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(logic_bp)
    print("[LOGIC] ✅ Module logique métier enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='dashboard', title='Omega Agro'):
    return _deps['render_page'](content, active=active, page_title=title)


def _log(action, details='', entity=None, entity_id=None):
    try:
        uid = current_user.id if (current_user and current_user.is_authenticated) else None
        _deps['log_action'](uid, action, details, entity=entity, entity_id=entity_id)
    except Exception:
        pass


def _rows(cur):
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _row(cur):
    cols = [c[0] for c in cur.description]
    r = cur.fetchone()
    return dict(zip(cols, r)) if r else None


def _num(v, default=0.0):
    try:
        return float(v) if v not in (None, '') else default
    except (TypeError, ValueError):
        return default


# ═══════════════════════════════════════════════════════════════
# 🏭 PRODUCTION — Ordres de fabrication
# ═══════════════════════════════════════════════════════════════

@logic_bp.route('/production')
@login_required
def production_liste():
    db = _db()
    cur = db.cursor()
    statut = request.args.get('statut', '')
    q = request.args.get('q', '').strip()

    sql = """
        SELECT of.*, pf.nom AS produit_nom, pf.unite,
               lp.nom AS ligne_nom
        FROM ordres_fabrication of
        LEFT JOIN produits_finis pf ON pf.id = of.produit_fini_id
        LEFT JOIN lignes_production lp ON lp.id = of.ligne_id
        WHERE 1=1
    """
    params = []
    if statut:
        sql += " AND of.statut = ?"
        params.append(statut)
    if q:
        sql += " AND (of.numero LIKE ? OR pf.nom LIKE ?)"
        params += [f'%{q}%', f'%{q}%']
    sql += " ORDER BY of.id DESC LIMIT 200"

    cur.execute(sql, params)
    ordres = _rows(cur)

    # KPIs
    cur.execute("""
        SELECT
          COUNT(*) AS total,
          SUM(CASE WHEN statut='en_cours' THEN 1 ELSE 0 END) AS en_cours,
          SUM(CASE WHEN statut='termine' THEN 1 ELSE 0 END) AS termine,
          SUM(CASE WHEN statut='planifie' THEN 1 ELSE 0 END) AS planifie,
          COALESCE(SUM(quantite_produite),0) AS qte_totale,
          COALESCE(AVG(rendement),0) AS yield_moyen
        FROM ordres_fabrication
    """)
    kpi = _row(cur) or {}

    statut_color = {
        'planifie': '#3b82f6', 'en_cours': '#f59e0b',
        'termine': '#10b981', 'annule': '#ef4444'
    }

    rows_html = ''
    for o in ordres:
        sc = statut_color.get(o.get('statut'), '#6b7280')
        rend = o.get('rendement') or 0
        rows_html += f"""
        <tr>
          <td><strong>{o.get('numero','—')}</strong></td>
          <td>{o.get('produit_nom') or '—'}</td>
          <td>{o.get('ligne_nom') or '—'}</td>
          <td style="text-align:right">{o.get('quantite_prevue') or 0} {o.get('unite') or ''}</td>
          <td style="text-align:right">{o.get('quantite_produite') or 0}</td>
          <td style="text-align:right">{rend:.1f}%</td>
          <td><span style="background:{sc};color:#fff;padding:3px 10px;border-radius:12px;font-size:12px">{o.get('statut','—')}</span></td>
          <td>{o.get('date_debut') or '—'}</td>
          <td>
            <a href="/production/{o['id']}/avancer" class="btn-sm" style="background:#10b981;color:#fff;padding:4px 10px;border-radius:6px;text-decoration:none;font-size:12px">▶ Avancer</a>
          </td>
        </tr>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">🏭 Production — Ordres de fabrication</h1>
      <a href="/production/nouveau" style="background:#10b981;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">+ Nouvel OF</a>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin-bottom:22px">
      <div style="background:linear-gradient(135deg,#3b82f6,#1e40af);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Total OF</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('total',0)}</div>
      </div>
      <div style="background:linear-gradient(135deg,#f59e0b,#b45309);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">En cours</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('en_cours',0)}</div>
      </div>
      <div style="background:linear-gradient(135deg,#10b981,#047857);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Terminés</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('termine',0)}</div>
      </div>
      <div style="background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Yield moyen</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('yield_moyen',0):.1f}%</div>
      </div>
      <div style="background:linear-gradient(135deg,#ec4899,#be185d);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Qté produite</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('qte_totale',0):,.0f}</div>
      </div>
    </div>

    <form method="get" style="margin-bottom:16px;display:flex;gap:10px;flex-wrap:wrap">
      <input type="text" name="q" value="{q}" placeholder="🔍 N° OF ou produit..." style="padding:9px 14px;border:2px solid #e5e7eb;border-radius:8px;min-width:240px">
      <select name="statut" style="padding:9px 14px;border:2px solid #e5e7eb;border-radius:8px">
        <option value="">Tous statuts</option>
        <option value="planifie" {'selected' if statut=='planifie' else ''}>Planifié</option>
        <option value="en_cours" {'selected' if statut=='en_cours' else ''}>En cours</option>
        <option value="termine" {'selected' if statut=='termine' else ''}>Terminé</option>
        <option value="annule" {'selected' if statut=='annule' else ''}>Annulé</option>
      </select>
      <button type="submit" style="background:#1f2937;color:#fff;padding:9px 20px;border:none;border-radius:8px;cursor:pointer;font-weight:600">Filtrer</button>
    </form>

    <div style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <table style="width:100%;border-collapse:collapse">
        <thead style="background:#1f2937;color:#fff">
          <tr>
            <th style="padding:12px;text-align:left">N° OF</th>
            <th style="padding:12px;text-align:left">Produit</th>
            <th style="padding:12px;text-align:left">Ligne</th>
            <th style="padding:12px;text-align:right">Prévu</th>
            <th style="padding:12px;text-align:right">Produit</th>
            <th style="padding:12px;text-align:right">Yield</th>
            <th style="padding:12px;text-align:left">Statut</th>
            <th style="padding:12px;text-align:left">Début</th>
            <th style="padding:12px;text-align:left">Action</th>
          </tr>
        </thead>
        <tbody>{rows_html or '<tr><td colspan="9" style="padding:40px;text-align:center;color:#9ca3af">Aucun ordre de fabrication</td></tr>'}</tbody>
      </table>
    </div>
    """
    return _render(content, active='production', title='Production')


@logic_bp.route('/production/nouveau', methods=['GET', 'POST'])
@login_required
def production_nouveau():
    db = _db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            produit_id = int(request.form.get('produit_fini_id') or 0)
            ligne_id = int(request.form.get('ligne_id') or 0) or None
            qte_prevue = _num(request.form.get('quantite_prevue'))
            date_debut = request.form.get('date_debut') or datetime.now().strftime('%Y-%m-%d')

            cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM ordres_fabrication")
            nid = cur.fetchone()[0]
            numero = f"OF-{datetime.now().strftime('%Y%m')}-{nid:04d}"

            cur.execute("""
                INSERT INTO ordres_fabrication
                (numero, produit_fini_id, ligne_id, quantite_prevue,
                 quantite_produite, statut, date_debut, rendement, created_at)
                VALUES (?,?,?,?,0,'planifie',?,0,?)
            """, (numero, produit_id, ligne_id, qte_prevue, date_debut,
                  datetime.now().isoformat()))
            db.commit()
            _log('CREATE_OF', f'{numero} — qte={qte_prevue}', 'ordres_fabrication', nid)
            flash(f'✅ OF {numero} créé', 'success')
            return redirect('/production')
        except Exception as e:
            db.rollback()
            flash(f'❌ Erreur : {e}', 'error')

    cur.execute("SELECT id, nom, unite FROM produits_finis ORDER BY nom")
    produits = _rows(cur)
    cur.execute("SELECT id, nom FROM lignes_production ORDER BY nom")
    lignes = _rows(cur)

    opts_p = ''.join(f'<option value="{p["id"]}">{p["nom"]} ({p.get("unite") or "u"})</option>' for p in produits)
    opts_l = '<option value="">— Aucune —</option>' + ''.join(f'<option value="{l["id"]}">{l["nom"]}</option>' for l in lignes)

    content = f"""
    <h1 style="color:#1f2937">🏭 Nouvel ordre de fabrication</h1>
    <form method="post" style="background:#fff;padding:28px;border-radius:12px;max-width:720px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
        <div style="grid-column:1/-1">
          <label style="display:block;font-weight:600;margin-bottom:6px">Produit fini *</label>
          <select name="produit_fini_id" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px">
            <option value="">— Sélectionner —</option>{opts_p}
          </select>
        </div>
        <div>
          <label style="display:block;font-weight:600;margin-bottom:6px">Ligne de production</label>
          <select name="ligne_id" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px">{opts_l}</select>
        </div>
        <div>
          <label style="display:block;font-weight:600;margin-bottom:6px">Quantité prévue *</label>
          <input type="number" step="0.1" name="quantite_prevue" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px">
        </div>
        <div>
          <label style="display:block;font-weight:600;margin-bottom:6px">Date de début</label>
          <input type="date" name="date_debut" value="{datetime.now().strftime('%Y-%m-%d')}" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px">
        </div>
      </div>
      <div style="margin-top:24px;display:flex;gap:12px">
        <button type="submit" style="background:#10b981;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-weight:600;cursor:pointer">💾 Créer l'OF</button>
        <a href="/production" style="background:#e5e7eb;color:#374151;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600">Annuler</a>
      </div>
    </form>
    """
    return _render(content, active='production', title='Nouvel OF')


@logic_bp.route('/production/<int:of_id>/avancer', methods=['GET', 'POST'])
@login_required
def production_avancer(of_id):
    db = _db()
    cur = db.cursor()
    cur.execute("SELECT * FROM ordres_fabrication WHERE id=?", (of_id,))
    of = _row(cur)
    if not of:
        flash('❌ OF introuvable', 'error')
        return redirect('/production')

    if request.method == 'POST':
        try:
            qte_prod = _num(request.form.get('quantite_produite'))
            nouveau_statut = request.form.get('statut') or of.get('statut')
            prevue = of.get('quantite_prevue') or 0
            rendement = (qte_prod / prevue * 100) if prevue > 0 else 0

            cur.execute("""
                UPDATE ordres_fabrication
                SET quantite_produite=?, statut=?, rendement=?,
                    date_fin=CASE WHEN ?='termine' THEN ? ELSE date_fin END
                WHERE id=?
            """, (qte_prod, nouveau_statut, rendement, nouveau_statut,
                  datetime.now().strftime('%Y-%m-%d'), of_id))
            db.commit()
            _log('UPDATE_OF', f'OF#{of_id} → {nouveau_statut} ({rendement:.1f}%)',
                 'ordres_fabrication', of_id)
            flash(f'✅ OF mis à jour — Yield {rendement:.1f}%', 'success')
            return redirect('/production')
        except Exception as e:
            db.rollback()
            flash(f'❌ {e}', 'error')

    return f"""
    <h1>🏭 Avancer OF #{of_id}</h1>
    <form method="post" style="background:#fff;padding:28px;border-radius:12px;max-width:600px">
      <p><strong>{of.get('numero')}</strong></p>
      <p>Prévu : {of.get('quantite_prevue')} | Produit : {of.get('quantite_produite') or 0}</p>
      <div style="margin:16px 0">
        <label style="font-weight:600">Quantité produite</label>
        <input type="number" step="0.1" name="quantite_produite" value="{of.get('quantite_produite') or 0}" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
      </div>
      <div style="margin:16px 0">
        <label style="font-weight:600">Statut</label>
        <select name="statut" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
          <option value="planifie" {'selected' if of.get('statut')=='planifie' else ''}>Planifié</option>
          <option value="en_cours" {'selected' if of.get('statut')=='en_cours' else ''}>En cours</option>
          <option value="termine" {'selected' if of.get('statut')=='termine' else ''}>Terminé</option>
          <option value="annule" {'selected' if of.get('statut')=='annule' else ''}>Annulé</option>
        </select>
      </div>
      <button type="submit" style="background:#10b981;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-weight:600;cursor:pointer">💾 Enregistrer</button>
      <a href="/production" style="margin-left:12px;color:#6b7280">Annuler</a>
    </form>
    """


# ═══════════════════════════════════════════════════════════════
# 📦 STOCKS
# ═══════════════════════════════════════════════════════════════

@logic_bp.route('/stocks')
@login_required
def stocks_liste():
    db = _db()
    cur = db.cursor()
    alerte = request.args.get('alerte') == '1'

    sql = """
        SELECT s.*, pf.nom AS produit_nom, pf.unite, pf.prix_unitaire,
               (s.quantite * COALESCE(pf.prix_unitaire,0)) AS valeur
        FROM stocks_produits s
        LEFT JOIN produits_finis pf ON pf.id = s.produit_fini_id
    """
    if alerte:
        sql += " WHERE s.quantite <= s.seuil_alerte"
    sql += " ORDER BY s.quantite ASC LIMIT 300"
    cur.execute(sql)
    stocks = _rows(cur)

    cur.execute("""
        SELECT COUNT(*) AS n,
               COALESCE(SUM(quantite),0) AS qte,
               COALESCE(SUM(CASE WHEN quantite <= seuil_alerte THEN 1 ELSE 0 END),0) AS alertes
        FROM stocks_produits
    """)
    kpi = _row(cur) or {}

    cur.execute("""
        SELECT COALESCE(SUM(s.quantite * COALESCE(pf.prix_unitaire,0)),0) AS val
        FROM stocks_produits s LEFT JOIN produits_finis pf ON pf.id=s.produit_fini_id
    """)
    valorisation = (_row(cur) or {}).get('val', 0)

    rows_html = ''
    for s in stocks:
        q = s.get('quantite') or 0
        seuil = s.get('seuil_alerte') or 0
        is_alerte = q <= seuil
        bg = '#fef2f2' if is_alerte else '#fff'
        badge = '<span style="background:#ef4444;color:#fff;padding:3px 10px;border-radius:12px;font-size:11px">⚠ ALERTE</span>' if is_alerte else '<span style="background:#10b981;color:#fff;padding:3px 10px;border-radius:12px;font-size:11px">OK</span>'
        rows_html += f"""
        <tr style="background:{bg}">
          <td><strong>{s.get('produit_nom') or '—'}</strong></td>
          <td>{s.get('lot') or s.get('numero_lot') or '—'}</td>
          <td style="text-align:right">{q:,.1f} {s.get('unite') or ''}</td>
          <td style="text-align:right">{seuil}</td>
          <td style="text-align:right">{s.get('valeur',0):,.0f} FCFA</td>
          <td>{badge}</td>
          <td>{s.get('emplacement') or '—'}</td>
        </tr>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">📦 Stocks produits finis</h1>
      <a href="/stocks/mouvement" style="background:#3b82f6;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">↔ Mouvement</a>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:22px">
      <div style="background:linear-gradient(135deg,#3b82f6,#1e40af);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Références</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('n',0)}</div>
      </div>
      <div style="background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Quantité totale</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('qte',0):,.0f}</div>
      </div>
      <div style="background:linear-gradient(135deg,#ef4444,#b91c1c);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Alertes seuil</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('alertes',0)}</div>
      </div>
      <div style="background:linear-gradient(135deg,#10b981,#047857);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Valorisation</div>
        <div style="font-size:22px;font-weight:700">{valorisation:,.0f} FCFA</div>
      </div>
    </div>

    <div style="margin-bottom:16px">
      <a href="/stocks" style="padding:9px 18px;border-radius:8px;text-decoration:none;background:{'#1f2937' if not alerte else '#e5e7eb'};color:{'#fff' if not alerte else '#374151'};font-weight:600">Tous</a>
      <a href="/stocks?alerte=1" style="padding:9px 18px;border-radius:8px;text-decoration:none;background:{'#ef4444' if alerte else '#e5e7eb'};color:{'#fff' if alerte else '#374151'};font-weight:600;margin-left:8px">⚠ Alertes seulement</a>
    </div>

    <div style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <table style="width:100%;border-collapse:collapse">
        <thead style="background:#1f2937;color:#fff">
          <tr>
            <th style="padding:12px;text-align:left">Produit</th>
            <th style="padding:12px;text-align:left">Lot</th>
            <th style="padding:12px;text-align:right">Quantité</th>
            <th style="padding:12px;text-align:right">Seuil</th>
            <th style="padding:12px;text-align:right">Valeur</th>
            <th style="padding:12px;text-align:left">État</th>
            <th style="padding:12px;text-align:left">Emplacement</th>
          </tr>
        </thead>
        <tbody>{rows_html or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#9ca3af">Aucun stock</td></tr>'}</tbody>
      </table>
    </div>
    """
    return _render(content, active='stocks', title='Stocks')


@logic_bp.route('/stocks/mouvement', methods=['GET', 'POST'])
@login_required
def stocks_mouvement():
    db = _db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            stock_id = int(request.form.get('stock_id') or 0)
            type_mvt = request.form.get('type') or 'entree'
            qte = _num(request.form.get('quantite'))
            motif = request.form.get('motif') or ''

            cur.execute("SELECT quantite FROM stocks_produits WHERE id=?", (stock_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError('Stock introuvable')
            actuel = row[0] or 0
            nouvelle = actuel + qte if type_mvt == 'entree' else actuel - qte
            if nouvelle < 0:
                raise ValueError('Stock insuffisant')

            cur.execute("UPDATE stocks_produits SET quantite=? WHERE id=?", (nouvelle, stock_id))
            db.commit()
            _log('MOUV_STOCK', f'stock#{stock_id} {type_mvt} {qte} → {nouvelle} ({motif})',
                 'stocks_produits', stock_id)
            flash(f'✅ Mouvement enregistré — nouveau stock : {nouvelle:,.1f}', 'success')
            return redirect('/stocks')
        except Exception as e:
            db.rollback()
            flash(f'❌ {e}', 'error')

    cur.execute("""
        SELECT s.id, s.quantite, pf.nom AS produit
        FROM stocks_produits s LEFT JOIN produits_finis pf ON pf.id=s.produit_fini_id
        ORDER BY pf.nom LIMIT 500
    """)
    stocks = _rows(cur)
    opts = ''.join(f'<option value="{s["id"]}">{s.get("produit") or "?"} — stock {s.get("quantite") or 0}</option>' for s in stocks)

    content = f"""
    <h1 style="color:#1f2937">↔ Mouvement de stock</h1>
    <form method="post" style="background:#fff;padding:28px;border-radius:12px;max-width:640px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <div style="margin-bottom:18px">
        <label style="font-weight:600">Produit en stock *</label>
        <select name="stock_id" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
          <option value="">— Sélectionner —</option>{opts}
        </select>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
        <div>
          <label style="font-weight:600">Type *</label>
          <select name="type" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
            <option value="entree">➕ Entrée</option>
            <option value="sortie">➖ Sortie</option>
          </select>
        </div>
        <div>
          <label style="font-weight:600">Quantité *</label>
          <input type="number" step="0.1" name="quantite" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
      </div>
      <div style="margin-top:18px">
        <label style="font-weight:600">Motif</label>
        <input type="text" name="motif" placeholder="Vente, casse, réception..." style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
      </div>
      <div style="margin-top:24px">
        <button type="submit" style="background:#3b82f6;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-weight:600;cursor:pointer">💾 Enregistrer</button>
        <a href="/stocks" style="margin-left:12px;color:#6b7280">Annuler</a>
      </div>
    </form>
    """
    return _render(content, active='stocks', title='Mouvement stock')


# ═══════════════════════════════════════════════════════════════
# 📄 CONTRATS
# ═══════════════════════════════════════════════════════════════

@logic_bp.route('/contrats')
@login_required
def contrats_liste():
    db = _db()
    cur = db.cursor()
    statut = request.args.get('statut', '')

    sql = """
        SELECT c.*, pr.nom AS producteur_nom, pr.region,
               pf.nom AS produit_nom
        FROM contrats_achat c
        LEFT JOIN producteurs pr ON pr.id = c.producteur_id
        LEFT JOIN produits_finis pf ON pf.id = c.produit_fini_id
        WHERE 1=1
    """
    params = []
    if statut:
        sql += " AND c.statut = ?"
        params.append(statut)
    sql += " ORDER BY c.id DESC LIMIT 200"
    cur.execute(sql, params)
    contrats = _rows(cur)

    cur.execute("""
        SELECT COUNT(*) AS total,
               COALESCE(SUM(montant_total),0) AS montant,
               SUM(CASE WHEN statut='signe' THEN 1 ELSE 0 END) AS signes,
               SUM(CASE WHEN statut='en_attente' THEN 1 ELSE 0 END) AS attente
        FROM contrats_achat
    """)
    kpi = _row(cur) or {}

    rows_html = ''
    for c in contrats:
        st = c.get('statut') or 'en_attente'
        color = {'signe': '#10b981', 'en_attente': '#f59e0b',
                 'annule': '#ef4444', 'livre': '#3b82f6'}.get(st, '#6b7280')
        action = ''
        if st == 'en_attente':
            action = f'<a href="/contrats/{c["id"]}/signer" style="background:#10b981;color:#fff;padding:4px 10px;border-radius:6px;text-decoration:none;font-size:12px">✍ Signer</a>'
        rows_html += f"""
        <tr>
          <td><strong>{c.get('numero') or f'CTR-{c["id"]:04d}'}</strong></td>
          <td>{c.get('producteur_nom') or '—'}<br><small style="color:#9ca3af">{c.get('region') or ''}</small></td>
          <td>{c.get('produit_nom') or '—'}</td>
          <td style="text-align:right">{c.get('quantite') or 0}</td>
          <td style="text-align:right">{c.get('prix_unitaire') or 0:,.0f} F</td>
          <td style="text-align:right"><strong>{c.get('montant_total') or 0:,.0f} F</strong></td>
          <td><span style="background:{color};color:#fff;padding:3px 10px;border-radius:12px;font-size:12px">{st}</span></td>
          <td>{action}</td>
        </tr>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">📄 Contrats d'achat producteur ↔ transformateur</h1>
      <a href="/contrats/nouveau" style="background:#10b981;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">+ Nouveau contrat</a>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:22px">
      <div style="background:linear-gradient(135deg,#3b82f6,#1e40af);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Total contrats</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('total',0)}</div>
      </div>
      <div style="background:linear-gradient(135deg,#10b981,#047857);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Signés</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('signes',0)}</div>
      </div>
      <div style="background:linear-gradient(135deg,#f59e0b,#b45309);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">En attente</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('attente',0)}</div>
      </div>
      <div style="background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Montant total</div>
        <div style="font-size:20px;font-weight:700">{kpi.get('montant',0):,.0f} F</div>
      </div>
    </div>

    <div style="margin-bottom:16px">
      <a href="/contrats" style="padding:9px 18px;border-radius:8px;text-decoration:none;background:{'#1f2937' if not statut else '#e5e7eb'};color:{'#fff' if not statut else '#374151'};font-weight:600">Tous</a>
      <a href="/contrats?statut=signe" style="padding:9px 18px;border-radius:8px;text-decoration:none;background:{'#10b981' if statut=='signe' else '#e5e7eb'};color:{'#fff' if statut=='signe' else '#374151'};font-weight:600;margin-left:8px">Signés</a>
      <a href="/contrats?statut=en_attente" style="padding:9px 18px;border-radius:8px;text-decoration:none;background:{'#f59e0b' if statut=='en_attente' else '#e5e7eb'};color:{'#fff' if statut=='en_attente' else '#374151'};font-weight:600;margin-left:8px">En attente</a>
    </div>

    <div style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <table style="width:100%;border-collapse:collapse">
        <thead style="background:#1f2937;color:#fff">
          <tr>
            <th style="padding:12px;text-align:left">N°</th>
            <th style="padding:12px;text-align:left">Producteur</th>
            <th style="padding:12px;text-align:left">Produit</th>
            <th style="padding:12px;text-align:right">Qté</th>
            <th style="padding:12px;text-align:right">Prix U.</th>
            <th style="padding:12px;text-align:right">Montant</th>
            <th style="padding:12px;text-align:left">Statut</th>
            <th style="padding:12px;text-align:left">Action</th>
          </tr>
        </thead>
        <tbody>{rows_html or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#9ca3af">Aucun contrat</td></tr>'}</tbody>
      </table>
    </div>
    """
    return _render(content, active='contrats', title='Contrats')


@logic_bp.route('/contrats/nouveau', methods=['GET', 'POST'])
@login_required
def contrats_nouveau():
    db = _db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            producteur_id = int(request.form.get('producteur_id') or 0)
            produit_id = int(request.form.get('produit_fini_id') or 0) or None
            quantite = _num(request.form.get('quantite'))
            prix_u = _num(request.form.get('prix_unitaire'))
            montant = quantite * prix_u
            date_signature = request.form.get('date_signature') or datetime.now().strftime('%Y-%m-%d')

            cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM contrats_achat")
            nid = cur.fetchone()[0]
            numero = f"CTR-{datetime.now().strftime('%Y%m')}-{nid:04d}"

            cur.execute("""
                INSERT INTO contrats_achat
                (numero, producteur_id, produit_fini_id, quantite, prix_unitaire,
                 montant_total, statut, date_signature, created_at)
                VALUES (?,?,?,?,?,?,'en_attente',?,?)
            """, (numero, producteur_id, produit_id, quantite, prix_u,
                  montant, date_signature, datetime.now().isoformat()))
            db.commit()
            _log('CREATE_CONTRAT', f'{numero} — {montant:,.0f} F', 'contrats_achat', nid)
            flash(f'✅ Contrat {numero} créé — {montant:,.0f} FCFA', 'success')
            return redirect('/contrats')
        except Exception as e:
            db.rollback()
            flash(f'❌ {e}', 'error')

    cur.execute("SELECT id, nom, region FROM producteurs ORDER BY nom LIMIT 500")
    producteurs = _rows(cur)
    cur.execute("SELECT id, nom FROM produits_finis ORDER BY nom")
    produits = _rows(cur)

    opts_pr = ''.join(f'<option value="{p["id"]}">{p["nom"]} — {p.get("region") or ""}</option>' for p in producteurs)
    opts_pf = '<option value="">— Aucun —</option>' + ''.join(f'<option value="{p["id"]}">{p["nom"]}</option>' for p in produits)

    content = f"""
    <h1 style="color:#1f2937">📄 Nouveau contrat d'achat</h1>
    <form method="post" style="background:#fff;padding:28px;border-radius:12px;max-width:760px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
        <div style="grid-column:1/-1">
          <label style="font-weight:600">Producteur *</label>
          <select name="producteur_id" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
            <option value="">— Sélectionner —</option>{opts_pr}
          </select>
        </div>
        <div>
          <label style="font-weight:600">Produit fini</label>
          <select name="produit_fini_id" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">{opts_pf}</select>
        </div>
        <div>
          <label style="font-weight:600">Quantité (kg) *</label>
          <input type="number" step="0.1" name="quantite" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Prix unitaire (FCFA/kg) *</label>
          <input type="number" step="1" name="prix_unitaire" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Date signature</label>
          <input type="date" name="date_signature" value="{datetime.now().strftime('%Y-%m-%d')}" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
      </div>
      <div style="margin-top:24px">
        <button type="submit" style="background:#10b981;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-weight:600;cursor:pointer">💾 Créer le contrat</button>
        <a href="/contrats" style="margin-left:12px;color:#6b7280">Annuler</a>
      </div>
    </form>
    """
    return _render(content, active='contrats', title='Nouveau contrat')


@logic_bp.route('/contrats/<int:cid>/signer', methods=['GET', 'POST'])
@login_required
def contrats_signer(cid):
    db = _db()
    cur = db.cursor()
    try:
        cur.execute("""
            UPDATE contrats_achat SET statut='signe', date_signature=COALESCE(date_signature,?)
            WHERE id=?
        """, (datetime.now().strftime('%Y-%m-%d'), cid))
        db.commit()
        _log('SIGN_CONTRAT', f'Contrat #{cid} signé', 'contrats_achat', cid)
        flash('✅ Contrat signé', 'success')
    except Exception as e:
        db.rollback()
        flash(f'❌ {e}', 'error')
    return redirect('/contrats')


# ═══════════════════════════════════════════════════════════════
# 🚚 FOURNISSEURS
# ═══════════════════════════════════════════════════════════════

@logic_bp.route('/fournisseurs')
@login_required
def fournisseurs_liste():
    db = _db()
    cur = db.cursor()
    try:
        cur.execute("""
            SELECT f.*,
                   (SELECT COUNT(*) FROM commandes_fournisseurs cf WHERE cf.fournisseur_id=f.id) AS nb_commandes
            FROM fournisseurs f ORDER BY f.nom LIMIT 200
        """)
        fournisseurs = _rows(cur)
    except Exception:
        fournisseurs = []

    rows_html = ''
    for f in fournisseurs:
        rows_html += f"""
        <tr>
          <td><strong>{f.get('nom') or '—'}</strong></td>
          <td>{f.get('categorie') or '—'}</td>
          <td>{f.get('contact') or '—'}</td>
          <td>{f.get('telephone') or '—'}</td>
          <td>{f.get('email') or '—'}</td>
          <td>{f.get('adresse') or '—'}</td>
          <td style="text-align:center">{f.get('nb_commandes') or 0}</td>
        </tr>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">🚚 Fournisseurs — Matériels agricoles & intrants</h1>
      <a href="/fournisseurs/nouveau" style="background:#10b981;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">+ Nouveau fournisseur</a>
    </div>

    <div style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <table style="width:100%;border-collapse:collapse">
        <thead style="background:#1f2937;color:#fff">
          <tr>
            <th style="padding:12px;text-align:left">Nom</th>
            <th style="padding:12px;text-align:left">Catégorie</th>
            <th style="padding:12px;text-align:left">Contact</th>
            <th style="padding:12px;text-align:left">Téléphone</th>
            <th style="padding:12px;text-align:left">Email</th>
            <th style="padding:12px;text-align:left">Adresse</th>
            <th style="padding:12px;text-align:center">Commandes</th>
          </tr>
        </thead>
        <tbody>{rows_html or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#9ca3af">Aucun fournisseur</td></tr>'}</tbody>
      </table>
    </div>
    """
    return _render(content, active='fournisseurs', title='Fournisseurs')


@logic_bp.route('/fournisseurs/nouveau', methods=['GET', 'POST'])
@login_required
def fournisseurs_nouveau():
    db = _db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO fournisseurs (nom, categorie, contact, telephone, email, adresse, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (
                request.form.get('nom'),
                request.form.get('categorie'),
                request.form.get('contact'),
                request.form.get('telephone'),
                request.form.get('email'),
                request.form.get('adresse'),
                datetime.now().isoformat()
            ))
            db.commit()
            _log('CREATE_FOURNISSEUR', request.form.get('nom', ''), 'fournisseurs')
            flash('✅ Fournisseur créé', 'success')
            return redirect('/fournisseurs')
        except Exception as e:
            db.rollback()
            flash(f'❌ {e}', 'error')

    content = """
    <h1 style="color:#1f2937">🚚 Nouveau fournisseur</h1>
    <form method="post" style="background:#fff;padding:28px;border-radius:12px;max-width:720px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
        <div style="grid-column:1/-1">
          <label style="font-weight:600">Nom *</label>
          <input type="text" name="nom" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Catégorie</label>
          <select name="categorie" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
            <option value="materiel_agricole">Matériel agricole</option>
            <option value="intrants">Intrants</option>
            <option value="emballage">Emballage</option>
            <option value="energie">Énergie / solaire</option>
            <option value="logistique">Logistique</option>
            <option value="autre">Autre</option>
          </select>
        </div>
        <div>
          <label style="font-weight:600">Contact</label>
          <input type="text" name="contact" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Téléphone</label>
          <input type="text" name="telephone" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Email</label>
          <input type="email" name="email" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div style="grid-column:1/-1">
          <label style="font-weight:600">Adresse</label>
          <input type="text" name="adresse" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
      </div>
      <div style="margin-top:24px">
        <button type="submit" style="background:#10b981;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-weight:600;cursor:pointer">💾 Créer</button>
        <a href="/fournisseurs" style="margin-left:12px;color:#6b7280">Annuler</a>
      </div>
    </form>
    """
    return _render(content, active='fournisseurs', title='Nouveau fournisseur')


# ═══════════════════════════════════════════════════════════════
# 📊 API JSON — KPIs & Yield management
# ═══════════════════════════════════════════════════════════════

@logic_bp.route('/api/production/yield')
@login_required
def api_yield():
    db = _db()
    cur = db.cursor()
    cur.execute("""
        SELECT pf.nom AS produit,
               COUNT(*) AS nb_of,
               AVG(of.rendement) AS yield_moyen,
               SUM(of.quantite_produite) AS qte_totale
        FROM ordres_fabrication of
        LEFT JOIN produits_finis pf ON pf.id=of.produit_fini_id
        WHERE of.statut='termine'
        GROUP BY pf.id, pf.nom
        ORDER BY yield_moyen DESC LIMIT 20
    """)
    return jsonify(_rows(cur))


@logic_bp.route('/api/stocks/alertes')
@login_required
def api_alertes():
    db = _db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.id, pf.nom AS produit, s.quantite, s.seuil_alerte
        FROM stocks_produits s LEFT JOIN produits_finis pf ON pf.id=s.produit_fini_id
        WHERE s.quantite <= s.seuil_alerte
        ORDER BY s.quantite ASC
    """)
    return jsonify(_rows(cur))


# ═══════════════════════════════════════════════════════════════
# 🔗 Alias de compatibilité — main.py appelle init_agro()
# ═══════════════════════════════════════════════════════════════
def init_agro(app, **kwargs):
    """Alias vers init_logic() pour compatibilité main.py."""
    return init_logic(app, **kwargs)
