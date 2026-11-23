"""
🌍 Omega Agro-Industrie — Export UE & USAID
Certifications · Traçabilité QR · Conformité normes européennes
"""
from flask import Blueprint, request, redirect, flash, jsonify
from flask_login import current_user, login_required
from datetime import datetime
import json

export_bp = Blueprint('export_ue', __name__)
_deps = {}


def init_export(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(export_bp)
    print("[EXPORT] ✅ Module export UE enregistré")


# Alias compatibilité main.py
def init_agro_export(app, **kwargs):
    return init_export(app, **kwargs)


def _db():
    return _deps['get_db']()


def _render(content, active='export', title='Export'):
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


# ═══════════════════════════════════════════════════════════════
# 🌍 EXPORTS
# ═══════════════════════════════════════════════════════════════

@export_bp.route('/exports')
@login_required
def exports_liste():
    db = _db()
    cur = db.cursor()
    statut = request.args.get('statut', '')
    destination = request.args.get('destination', '')

    sql = """
        SELECT e.*, pf.nom AS produit_nom, pf.unite
        FROM exports e
        LEFT JOIN produits_finis pf ON pf.id = e.produit_fini_id
        WHERE 1=1
    """
    params = []
    if statut:
        sql += " AND e.statut = ?"
        params.append(statut)
    if destination:
        sql += " AND e.destination = ?"
        params.append(destination)
    sql += " ORDER BY e.id DESC LIMIT 200"
    cur.execute(sql, params)
    exports = _rows(cur)

    cur.execute("""
        SELECT COUNT(*) AS total,
               COALESCE(SUM(quantite),0) AS qte,
               COALESCE(SUM(valeur_fcfa),0) AS valeur,
               SUM(CASE WHEN certification_ue=1 THEN 1 ELSE 0 END) AS cert_ue
        FROM exports
    """)
    kpi = _row(cur) or {}

    rows_html = ''
    for e in exports:
        st = e.get('statut') or 'en_preparation'
        color = {'en_preparation': '#f59e0b', 'expedie': '#3b82f6',
                 'livre': '#10b981', 'bloque': '#ef4444'}.get(st, '#6b7280')
        cert_ue = '✅' if e.get('certification_ue') else '❌'
        cert_usaid = '✅' if e.get('certification_usaid') else '❌'
        rows_html += f"""
        <tr>
          <td><strong>{e.get('numero') or f'EXP-{e["id"]:04d}'}</strong></td>
          <td>{e.get('produit_nom') or '—'}</td>
          <td>{e.get('destination') or '—'}</td>
          <td style="text-align:right">{e.get('quantite') or 0:,.1f}</td>
          <td style="text-align:right">{e.get('valeur_fcfa') or 0:,.0f} F</td>
          <td style="text-align:center">{cert_ue}</td>
          <td style="text-align:center">{cert_usaid}</td>
          <td><span style="background:{color};color:#fff;padding:3px 10px;border-radius:12px;font-size:12px">{st}</span></td>
          <td>
            <a href="/exports/{e['id']}/certifier" style="background:#3b82f6;color:#fff;padding:4px 10px;border-radius:6px;text-decoration:none;font-size:12px">🌍 Certifier</a>
          </td>
        </tr>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">🌍 Exports — Union Européenne & USAID</h1>
      <a href="/exports/nouveau" style="background:#10b981;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">+ Nouvel export</a>
    </div>

    <div style="background:linear-gradient(135deg,#1e40af,#3b82f6);color:#fff;padding:18px;border-radius:12px;margin-bottom:22px">
      <div style="font-size:13px;opacity:.9;margin-bottom:8px">🇪🇺 Normes intégrées dans les processus de fabrication</div>
      <div style="display:flex;gap:20px;flex-wrap:wrap;font-size:13px">
        <span>✅ HACCP</span><span>✅ ISO 22000</span><span>✅ GlobalG.A.P.</span>
        <span>✅ Bio UE 2018/848</span><span>✅ Traçabilité QR</span><span>✅ Résidus pesticides</span>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:22px">
      <div style="background:linear-gradient(135deg,#3b82f6,#1e40af);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Total exports</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('total',0)}</div>
      </div>
      <div style="background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Quantité</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('qte',0):,.0f}</div>
      </div>
      <div style="background:linear-gradient(135deg,#10b981,#047857);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Valeur</div>
        <div style="font-size:20px;font-weight:700">{kpi.get('valeur',0):,.0f} F</div>
      </div>
      <div style="background:linear-gradient(135deg,#f59e0b,#b45309);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Certifiés UE</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('cert_ue',0)}</div>
      </div>
    </div>

    <div style="margin-bottom:16px">
      <a href="/exports" style="padding:9px 18px;border-radius:8px;text-decoration:none;background:{'#1f2937' if not statut else '#e5e7eb'};color:{'#fff' if not statut else '#374151'};font-weight:600">Tous</a>
      <a href="/exports?statut=en_preparation" style="padding:9px 18px;border-radius:8px;text-decoration:none;background:{'#f59e0b' if statut=='en_preparation' else '#e5e7eb'};color:{'#fff' if statut=='en_preparation' else '#374151'};font-weight:600;margin-left:8px">En préparation</a>
      <a href="/exports?statut=expedie" style="padding:9px 18px;border-radius:8px;text-decoration:none;background:{'#3b82f6' if statut=='expedie' else '#e5e7eb'};color:{'#fff' if statut=='expedie' else '#374151'};font-weight:600;margin-left:8px">Expédiés</a>
      <a href="/exports?statut=livre" style="padding:9px 18px;border-radius:8px;text-decoration:none;background:{'#10b981' if statut=='livre' else '#e5e7eb'};color:{'#fff' if statut=='livre' else '#374151'};font-weight:600;margin-left:8px">Livrés</a>
    </div>

    <div style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <table style="width:100%;border-collapse:collapse">
        <thead style="background:#1f2937;color:#fff">
          <tr>
            <th style="padding:12px;text-align:left">N°</th>
            <th style="padding:12px;text-align:left">Produit</th>
            <th style="padding:12px;text-align:left">Destination</th>
            <th style="padding:12px;text-align:right">Quantité</th>
            <th style="padding:12px;text-align:right">Valeur</th>
            <th style="padding:12px;text-align:center">UE</th>
            <th style="padding:12px;text-align:center">USAID</th>
            <th style="padding:12px;text-align:left">Statut</th>
            <th style="padding:12px;text-align:left">Action</th>
          </tr>
        </thead>
        <tbody>{rows_html or '<tr><td colspan="9" style="padding:40px;text-align:center;color:#9ca3af">Aucun export</td></tr>'}</tbody>
      </table>
    </div>
    """
    return _render(content, active='export', title='Exports')


@export_bp.route('/exports/nouveau', methods=['GET', 'POST'])
@login_required
def exports_nouveau():
    db = _db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            produit_id = int(request.form.get('produit_fini_id') or 0) or None
            destination = request.form.get('destination') or 'UE'
            quantite = float(request.form.get('quantite') or 0)
            valeur = float(request.form.get('valeur_fcfa') or 0)

            cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM exports")
            nid = cur.fetchone()[0]
            numero = f"EXP-{datetime.now().strftime('%Y%m')}-{nid:04d}"

            cur.execute("""
                INSERT INTO exports
                (numero, produit_fini_id, destination, quantite, valeur_fcfa,
                 certification_ue, certification_usaid, statut, date_export, created_at)
                VALUES (?,?,?,?,?,0,0,'en_preparation',?,?)
            """, (numero, produit_id, destination, quantite, valeur,
                  datetime.now().strftime('%Y-%m-%d'), datetime.now().isoformat()))
            db.commit()
            _log('CREATE_EXPORT', f'{numero} → {destination} ({quantite} u)',
                 'exports', nid)
            flash(f'✅ Export {numero} créé', 'success')
            return redirect('/exports')
        except Exception as e:
            db.rollback()
            flash(f'❌ {e}', 'error')

    cur.execute("SELECT id, nom FROM produits_finis ORDER BY nom")
    produits = _rows(cur)
    opts_p = ''.join(f'<option value="{p["id"]}">{p["nom"]}</option>' for p in produits)

    content = f"""
    <h1 style="color:#1f2937">🌍 Nouvel export</h1>
    <form method="post" style="background:#fff;padding:28px;border-radius:12px;max-width:760px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
        <div style="grid-column:1/-1">
          <label style="font-weight:600">Produit fini *</label>
          <select name="produit_fini_id" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
            <option value="">— Sélectionner —</option>{opts_p}
          </select>
        </div>
        <div>
          <label style="font-weight:600">Destination *</label>
          <select name="destination" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
            <option value="UE - France">🇫🇷 France</option>
            <option value="UE - Belgique">🇧🇪 Belgique</option>
            <option value="UE - Allemagne">🇩🇪 Allemagne</option>
            <option value="UE - Espagne">🇪🇸 Espagne</option>
            <option value="UE - Italie">🇮🇹 Italie</option>
            <option value="UE - Pays-Bas">🇳🇱 Pays-Bas</option>
            <option value="USAID - USA">🇺🇸 USA (USAID)</option>
            <option value="Maroc">🇲🇦 Maroc</option>
            <option value="Côte d'Ivoire">🇨🇮 Côte d'Ivoire</option>
          </select>
        </div>
        <div>
          <label style="font-weight:600">Quantité (kg) *</label>
          <input type="number" step="0.1" name="quantite" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Valeur FCFA *</label>
          <input type="number" step="1000" name="valeur_fcfa" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
      </div>
      <div style="margin-top:24px">
        <button type="submit" style="background:#10b981;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-weight:600;cursor:pointer">💾 Créer l'export</button>
        <a href="/exports" style="margin-left:12px;color:#6b7280">Annuler</a>
      </div>
    </form>
    """
    return _render(content, active='export', title='Nouvel export')


@export_bp.route('/exports/<int:eid>/certifier', methods=['GET', 'POST'])
@login_required
def exports_certifier(eid):
    db = _db()
    cur = db.cursor()
    cur.execute("""
        SELECT e.*, pf.nom AS produit_nom FROM exports e
        LEFT JOIN produits_finis pf ON pf.id=e.produit_fini_id WHERE e.id=?
    """, (eid,))
    e = _row(cur)
    if not e:
        flash('❌ Export introuvable', 'error')
        return redirect('/exports')

    if request.method == 'POST':
        try:
            cert_ue = 1 if request.form.get('certification_ue') else 0
            cert_usaid = 1 if request.form.get('certification_usaid') else 0
            nouveau_statut = request.form.get('statut') or e.get('statut')
            cur.execute("""
                UPDATE exports SET certification_ue=?, certification_usaid=?, statut=?
                WHERE id=?
            """, (cert_ue, cert_usaid, nouveau_statut, eid))
            db.commit()
            _log('CERTIF_EXPORT', f'EXP#{eid} UE={cert_ue} USAID={cert_usaid}',
                 'exports', eid)
            flash('✅ Certifications mises à jour', 'success')
            return redirect('/exports')
        except Exception as e2:
            db.rollback()
            flash(f'❌ {e2}', 'error')

    content = f"""
    <h1 style="color:#1f2937">🌍 Certifications export — {e.get('numero') or f'EXP-{eid}'}</h1>
    <div style="background:#fff;padding:28px;border-radius:12px;max-width:720px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <div style="background:#f0f9ff;border-left:4px solid #3b82f6;padding:14px;border-radius:8px;margin-bottom:20px">
        <strong>Produit :</strong> {e.get('produit_nom') or '—'}<br>
        <strong>Destination :</strong> {e.get('destination') or '—'}<br>
        <strong>Quantité :</strong> {e.get('quantite') or 0:,.1f} kg<br>
        <strong>Valeur :</strong> {e.get('valeur_fcfa') or 0:,.0f} FCFA
      </div>
      <form method="post">
        <div style="margin-bottom:18px;padding:14px;background:#f9fafb;border-radius:8px">
          <label style="font-weight:600;display:flex;align-items:center;gap:10px;cursor:pointer">
            <input type="checkbox" name="certification_ue" value="1" {'checked' if e.get('certification_ue') else ''}>
            🇪🇺 Certification UE (HACCP + ISO 22000 + GlobalG.A.P.)
          </label>
        </div>
        <div style="margin-bottom:18px;padding:14px;background:#f9fafb;border-radius:8px">
          <label style="font-weight:600;display:flex;align-items:center;gap:10px;cursor:pointer">
            <input type="checkbox" name="certification_usaid" value="1" {'checked' if e.get('certification_usaid') else ''}>
            🇺🇸 Certification USAID (FDA + FSMA)
          </label>
        </div>
        <div style="margin-bottom:18px">
          <label style="font-weight:600">Statut export</label>
          <select name="statut" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
            <option value="en_preparation" {'selected' if e.get('statut')=='en_preparation' else ''}>En préparation</option>
            <option value="expedie" {'selected' if e.get('statut')=='expedie' else ''}>Expédié</option>
            <option value="livre" {'selected' if e.get('statut')=='livre' else ''}>Livré</option>
            <option value="bloque" {'selected' if e.get('statut')=='bloque' else ''}>Bloqué (douane)</option>
          </select>
        </div>
        <button type="submit" style="background:#10b981;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-weight:600;cursor:pointer">💾 Enregistrer</button>
        <a href="/exports" style="margin-left:12px;color:#6b7280">Retour</a>
      </form>
    </div>
    """
    return _render(content, active='export', title='Certifier export')


# ═══════════════════════════════════════════════════════════════
# 🔍 TRAÇABILITÉ QR — Champ à l'assiette
# ═══════════════════════════════════════════════════════════════

@export_bp.route('/exports/tracabilite/<lot>')
@login_required
def tracabilite_lot(lot):
    db = _db()
    cur = db.cursor()
    try:
        cur.execute("""
            SELECT t.*, pf.nom AS produit_nom,
                   pr.nom AS producteur_nom, pr.region,
                   r.date_recolte
            FROM tracabilite t
            LEFT JOIN produits_finis pf ON pf.id = t.produit_fini_id
            LEFT JOIN producteurs pr ON pr.id = t.producteur_id
            LEFT JOIN recoltes r ON r.id = t.recolte_id
            WHERE t.numero_lot = ? OR t.qr_code = ?
            LIMIT 1
        """, (lot, lot))
        t = _row(cur)
    except Exception:
        t = None

    if not t:
        flash(f'❌ Lot {lot} introuvable', 'error')
        return redirect('/exports')

    content = f"""
    <h1 style="color:#1f2937">🔍 Traçabilité — Lot {lot}</h1>
    <div style="background:linear-gradient(135deg,#10b981,#047857);color:#fff;padding:20px;border-radius:12px;margin-bottom:20px">
      <div style="font-size:13px;opacity:.9">Chaîne de traçabilité</div>
      <div style="font-size:22px;font-weight:700">{t.get('produit_nom') or '—'}</div>
      <div style="font-size:13px;opacity:.9;margin-top:6px">Du champ à l'assiette — Conforme UE</div>
    </div>

    <div style="background:#fff;padding:28px;border-radius:12px;max-width:820px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <h3 style="margin-top:0;color:#1f2937">📋 Fiche lot</h3>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:10px;background:#f9fafb;font-weight:600;width:200px">N° lot</td><td style="padding:10px">{t.get('numero_lot') or '—'}</td></tr>
        <tr><td style="padding:10px;background:#f9fafb;font-weight:600">Produit fini</td><td style="padding:10px">{t.get('produit_nom') or '—'}</td></tr>
        <tr><td style="padding:10px;background:#f9fafb;font-weight:600">Producteur</td><td style="padding:10px">{t.get('producteur_nom') or '—'} ({t.get('region') or '—'})</td></tr>
        <tr><td style="padding:10px;background:#f9fafb;font-weight:600">Date récolte</td><td style="padding:10px">{t.get('date_recolte') or '—'}</td></tr>
        <tr><td style="padding:10px;background:#f9fafb;font-weight:600">QR Code</td><td style="padding:10px"><code>{t.get('qr_code') or '—'}</code></td></tr>
        <tr><td style="padding:10px;background:#f9fafb;font-weight:600">Statut</td><td style="padding:10px">{t.get('statut') or '—'}</td></tr>
      </table>
    </div>
    """
    return _render(content, active='export', title=f'Traçabilité {lot}')


@export_bp.route('/api/exports/kpi')
@login_required
def api_exports_kpi():
    db = _db()
    cur = db.cursor()
    cur.execute("""
        SELECT destination,
               COUNT(*) AS nb,
               SUM(quantite) AS qte,
               SUM(valeur_fcfa) AS valeur
        FROM exports
        GROUP BY destination
        ORDER BY valeur DESC
    """)
    return jsonify(_rows(cur))


@export_bp.route('/api/tracabilite/qr/<lot>')
@login_required
def api_qr_lot(lot):
    db = _db()
    cur = db.cursor()
    cur.execute("SELECT * FROM tracabilite WHERE numero_lot=? OR qr_code=? LIMIT 1",
                (lot, lot))
    return jsonify(_row(cur) or {'error': 'lot introuvable'})
