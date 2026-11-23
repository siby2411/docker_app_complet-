"""
📈 Omega Agro-Industrie — Rapports & Analytics
KPIs · Yield management · Export CSV · Dashboards
"""
from flask import Blueprint, request, redirect, flash, jsonify, Response
from flask_login import current_user, login_required
from datetime import datetime, timedelta
import csv
import io

rapports_bp = Blueprint('rapports', __name__)
_deps = {}


def init_rapports(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(rapports_bp)
    print("[RAPPORTS] ✅ Module rapports enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='rapports', title='Rapports'):
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


def _scalar(cur, sql, default=0):
    try:
        cur.execute(sql)
        r = cur.fetchone()
        return r[0] if r and r[0] is not None else default
    except Exception:
        return default


# ═══════════════════════════════════════════════════════════════
# 📈 RAPPORTS PRINCIPAUX
# ═══════════════════════════════════════════════════════════════

@rapports_bp.route('/rapports')
@login_required
def rapports_index():
    db = _db()
    cur = db.cursor()

    kpis = {
        'producteurs': _scalar(cur, "SELECT COUNT(*) FROM producteurs"),
        'recoltes': _scalar(cur, "SELECT COUNT(*) FROM recoltes"),
        'of_total': _scalar(cur, "SELECT COUNT(*) FROM ordres_fabrication"),
        'of_termines': _scalar(cur, "SELECT COUNT(*) FROM ordres_fabrication WHERE statut='termine'"),
        'yield_moyen': _scalar(cur, "SELECT AVG(rendement) FROM ordres_fabrication WHERE rendement IS NOT NULL"),
        'stocks_valeur': _scalar(cur, """
            SELECT COALESCE(SUM(s.quantite * COALESCE(pf.prix_unitaire,0)),0)
            FROM stocks_produits s LEFT JOIN produits_finis pf ON pf.id=s.produit_fini_id
        """),
        'contrats_montant': _scalar(cur, "SELECT COALESCE(SUM(montant_total),0) FROM contrats_achat"),
        'exports_valeur': _scalar(cur, "SELECT COALESCE(SUM(valeur_fcfa),0) FROM exports"),
        'taux_conformite': 0,
        'nc_total': _scalar(cur, "SELECT COUNT(*) FROM non_conformites"),
        'lots_traces': _scalar(cur, "SELECT COUNT(*) FROM tracabilite"),
        'sessions_formation': _scalar(cur, "SELECT COUNT(*) FROM sessions_formation"),
    }

    total_cq = _scalar(cur, "SELECT COUNT(*) FROM controles_qualite")
    conformes = _scalar(cur, "SELECT COUNT(*) FROM controles_qualite WHERE resultat='conforme'")
    kpis['taux_conformite'] = (conformes / total_cq * 100) if total_cq > 0 else 0

    # Top 5 produits par yield
    try:
        cur.execute("""
            SELECT pf.nom, AVG(of.rendement) AS yield, COUNT(*) AS nb
            FROM ordres_fabrication of
            LEFT JOIN produits_finis pf ON pf.id=of.produit_fini_id
            WHERE of.rendement IS NOT NULL
            GROUP BY pf.id, pf.nom
            ORDER BY yield DESC LIMIT 5
        """)
        top_yield = _rows(cur)
    except Exception:
        top_yield = []

    top_html = ''
    for t in top_yield:
        y = t.get('yield') or 0
        top_html += f"""
        <tr>
          <td>{t.get('nom') or '—'}</td>
          <td style="text-align:right">{y:.1f}%</td>
          <td style="text-align:right">{t.get('nb') or 0} OF</td>
          <td><div style="background:#e5e7eb;border-radius:6px;overflow:hidden"><div style="background:linear-gradient(90deg,#10b981,#047857);height:18px;width:{min(y,100):.0f}%"></div></div></td>
        </tr>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">📈 Rapports & Analytics</h1>
      <div style="display:flex;gap:10px">
        <a href="/rapports/dashboard" style="background:#3b82f6;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">📊 Dashboard</a>
        <a href="/rapports/export-csv" style="background:#10b981;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">⬇ Export CSV</a>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:22px">
      <div style="background:linear-gradient(135deg,#3b82f6,#1e40af);color:#fff;padding:18px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">👨‍🌾 Producteurs</div>
        <div style="font-size:30px;font-weight:700">{kpis['producteurs']}</div>
      </div>
      <div style="background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:#fff;padding:18px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">🌾 Récoltes</div>
        <div style="font-size:30px;font-weight:700">{kpis['recoltes']}</div>
      </div>
      <div style="background:linear-gradient(135deg,#10b981,#047857);color:#fff;padding:18px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">🏭 OF terminés</div>
        <div style="font-size:30px;font-weight:700">{kpis['of_termines']} / {kpis['of_total']}</div>
      </div>
      <div style="background:linear-gradient(135deg,#f59e0b,#b45309);color:#fff;padding:18px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">⚙️ Yield moyen</div>
        <div style="font-size:30px;font-weight:700">{kpis['yield_moyen']:.1f}%</div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:22px">
      <div style="background:#fff;padding:18px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.1);border-left:4px solid #3b82f6">
        <div style="font-size:12px;color:#6b7280">📦 Valeur stocks</div>
        <div style="font-size:22px;font-weight:700;color:#1f2937">{kpis['stocks_valeur']:,.0f} F</div>
      </div>
      <div style="background:#fff;padding:18px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.1);border-left:4px solid #10b981">
        <div style="font-size:12px;color:#6b7280">📄 Montant contrats</div>
        <div style="font-size:22px;font-weight:700;color:#1f2937">{kpis['contrats_montant']:,.0f} F</div>
      </div>
      <div style="background:#fff;padding:18px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.1);border-left:4px solid #f59e0b">
        <div style="font-size:12px;color:#6b7280">🌍 Valeur exports</div>
        <div style="font-size:22px;font-weight:700;color:#1f2937">{kpis['exports_valeur']:,.0f} F</div>
      </div>
      <div style="background:#fff;padding:18px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.1);border-left:4px solid #8b5cf6">
        <div style="font-size:12px;color:#6b7280">🔬 Taux conformité</div>
        <div style="font-size:22px;font-weight:700;color:#1f2937">{kpis['taux_conformite']:.1f}%</div>
      </div>
      <div style="background:#fff;padding:18px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.1);border-left:4px solid #ef4444">
        <div style="font-size:12px;color:#6b7280">⚠ Non-conformités</div>
        <div style="font-size:22px;font-weight:700;color:#1f2937">{kpis['nc_total']}</div>
      </div>
      <div style="background:#fff;padding:18px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.1);border-left:4px solid #ec4899">
        <div style="font-size:12px;color:#6b7280">🔍 Lots tracés</div>
        <div style="font-size:22px;font-weight:700;color:#1f2937">{kpis['lots_traces']}</div>
      </div>
      <div style="background:#fff;padding:18px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.1);border-left:4px solid #7c3aed">
        <div style="font-size:12px;color:#6b7280">🎓 Sessions formation</div>
        <div style="font-size:22px;font-weight:700;color:#1f2937">{kpis['sessions_formation']}</div>
      </div>
    </div>

    <div style="background:#fff;padding:22px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <h2 style="margin-top:0;color:#1f2937;font-size:18px">🏆 Top 5 produits par yield</h2>
      <table style="width:100%;border-collapse:collapse">
        <thead>
          <tr style="background:#f9fafb">
            <th style="padding:10px;text-align:left">Produit</th>
            <th style="padding:10px;text-align:right">Yield</th>
            <th style="padding:10px;text-align:right">OF</th>
            <th style="padding:10px;text-align:left">Performance</th>
          </tr>
        </thead>
        <tbody>{top_html or '<tr><td colspan="4" style="padding:30px;text-align:center;color:#9ca3af">Pas de données</td></tr>'}</tbody>
      </table>
    </div>
    """
    return _render(content, active='rapports', title='Rapports')


@rapports_bp.route('/rapports/dashboard')
@login_required
def rapports_dashboard():
    db = _db()
    cur = db.cursor()

    # Répartition par région
    try:
        cur.execute("""
            SELECT region, COUNT(*) AS nb
            FROM producteurs WHERE region IS NOT NULL
            GROUP BY region ORDER BY nb DESC
        """)
        regions = _rows(cur)
    except Exception:
        regions = []

    # Répartition exports par destination
    try:
        cur.execute("""
            SELECT destination, COUNT(*) AS nb, SUM(valeur_fcfa) AS valeur
            FROM exports GROUP BY destination ORDER BY valeur DESC LIMIT 10
        """)
        dests = _rows(cur)
    except Exception:
        dests = []

    max_region = max([r.get('nb', 0) for r in regions], default=1)
    max_dest = max([d.get('valeur', 0) for d in dests], default=1)

    regions_html = ''
    for r in regions:
        pct = (r.get('nb', 0) / max_region * 100) if max_region else 0
        regions_html += f"""
        <div style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
            <strong>{r.get('region')}</strong><span>{r.get('nb')} producteurs</span>
          </div>
          <div style="background:#e5e7eb;border-radius:6px;overflow:hidden;height:10px">
            <div style="background:linear-gradient(90deg,#3b82f6,#1e40af);height:100%;width:{pct:.0f}%"></div>
          </div>
        </div>"""

    dests_html = ''
    for d in dests:
        pct = (d.get('valeur', 0) / max_dest * 100) if max_dest else 0
        dests_html += f"""
        <div style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
            <strong>{d.get('destination')}</strong><span>{d.get('valeur',0):,.0f} F ({d.get('nb',0)} exp.)</span>
          </div>
          <div style="background:#e5e7eb;border-radius:6px;overflow:hidden;height:10px">
            <div style="background:linear-gradient(90deg,#10b981,#047857);height:100%;width:{pct:.0f}%"></div>
          </div>
        </div>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">📊 Dashboard analytique</h1>
      <a href="/rapports" style="background:#e5e7eb;color:#374151;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">← Rapports</a>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div style="background:#fff;padding:22px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
        <h3 style="margin-top:0;color:#1f2937">🗺 Producteurs par région</h3>
        {regions_html or '<p style="color:#9ca3af">Aucune donnée</p>'}
      </div>
      <div style="background:#fff;padding:22px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
        <h3 style="margin-top:0;color:#1f2937">🌍 Exports par destination</h3>
        {dests_html or '<p style="color:#9ca3af">Aucune donnée</p>'}
      </div>
    </div>
    """
    return _render(content, active='rapports', title='Dashboard')


@rapports_bp.route('/rapports/export-csv')
@login_required
def rapports_export_csv():
    db = _db()
    cur = db.cursor()
    cur.execute("""
        SELECT of.numero, pf.nom AS produit, of.quantite_prevue,
               of.quantite_produite, of.rendement, of.statut,
               of.date_debut, of.date_fin
        FROM ordres_fabrication of
        LEFT JOIN produits_finis pf ON pf.id=of.produit_fini_id
        ORDER BY of.id DESC LIMIT 500
    """)
    rows = _rows(cur)

    si = io.StringIO()
    writer = csv.writer(si, delimiter=';')
    writer.writerow(['N° OF', 'Produit', 'Qté prévue', 'Qté produite',
                     'Yield %', 'Statut', 'Début', 'Fin'])
    for r in rows:
        writer.writerow([
            r.get('numero'), r.get('produit'), r.get('quantite_prevue'),
            r.get('quantite_produite'),
            f"{r.get('rendement') or 0:.1f}",
            r.get('statut'), r.get('date_debut'), r.get('date_fin')
        ])

    _log('EXPORT_CSV', f'{len(rows)} lignes', 'rapports')
    output = si.getvalue()
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=omega_agro_of_{datetime.now().strftime("%Y%m%d")}.csv'}
    )


@rapports_bp.route('/api/rapports/kpi')
@login_required
def api_rapports_kpi():
    db = _db()
    cur = db.cursor()
    result = {}
    for key, sql in [
        ('producteurs', "SELECT COUNT(*) FROM producteurs"),
        ('recoltes', "SELECT COUNT(*) FROM recoltes"),
        ('of_termines', "SELECT COUNT(*) FROM ordres_fabrication WHERE statut='termine'"),
        ('exports_valeur', "SELECT COALESCE(SUM(valeur_fcfa),0) FROM exports"),
        ('stocks_valeur', """
            SELECT COALESCE(SUM(s.quantite * COALESCE(pf.prix_unitaire,0)),0)
            FROM stocks_produits s LEFT JOIN produits_finis pf ON pf.id=s.produit_fini_id
        """),
    ]:
        result[key] = _scalar(cur, sql)
    return jsonify(result)
