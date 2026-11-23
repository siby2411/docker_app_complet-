"""
🔬 Omega Agro-Industrie — Qualité & Conformité
Contrôles · Labo virtuel · Non-conformités · Certifications
"""
from flask import Blueprint, request, redirect, flash, jsonify
from flask_login import current_user, login_required
from datetime import datetime

qualite_bp = Blueprint('qualite', __name__)
_deps = {}


def init_qualite(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(qualite_bp)
    print("[QUALITE] ✅ Module qualité enregistré")


# Alias compatibilité main.py
def init_agro_qualite(app, **kwargs):
    return init_qualite(app, **kwargs)


def _db():
    return _deps['get_db']()


def _render(content, active='qualite', title='Qualité'):
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
# 🔬 CONTRÔLES QUALITÉ
# ═══════════════════════════════════════════════════════════════

@qualite_bp.route('/qualite')
@login_required
def qualite_liste():
    db = _db()
    cur = db.cursor()
    resultat = request.args.get('resultat', '')

    sql = """
        SELECT q.*, pf.nom AS produit_nom,
               lp.nom AS ligne_nom,
               of.numero AS of_numero
        FROM controles_qualite q
        LEFT JOIN produits_finis pf ON pf.id = q.produit_fini_id
        LEFT JOIN lignes_production lp ON lp.id = q.ligne_id
        LEFT JOIN ordres_fabrication of ON of.id = q.ordre_fabrication_id
        WHERE 1=1
    """
    params = []
    if resultat:
        sql += " AND q.resultat = ?"
        params.append(resultat)
    sql += " ORDER BY q.id DESC LIMIT 200"
    cur.execute(sql, params)
    controles = _rows(cur)

    cur.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN resultat='conforme' THEN 1 ELSE 0 END) AS conformes,
               SUM(CASE WHEN resultat='non_conforme' THEN 1 ELSE 0 END) AS nc,
               AVG(CASE WHEN score IS NOT NULL THEN score END) AS score_moyen
        FROM controles_qualite
    """)
    kpi = _row(cur) or {}

    # Taux de conformité
    total = kpi.get('total') or 0
    conformes = kpi.get('conformes') or 0
    taux = (conformes / total * 100) if total > 0 else 0

    rows_html = ''
    for c in controles:
        r = c.get('resultat') or 'en_attente'
        color = {'conforme': '#10b981', 'non_conforme': '#ef4444',
                 'en_attente': '#f59e0b'}.get(r, '#6b7280')
        score = c.get('score') or 0
        rows_html += f"""
        <tr>
          <td><strong>{c.get('numero') or f'CQ-{c["id"]:04d}'}</strong></td>
          <td>{c.get('produit_nom') or '—'}</td>
          <td>{c.get('of_numero') or '—'}</td>
          <td>{c.get('type_controle') or '—'}</td>
          <td style="text-align:right">{score:.1f}/100</td>
          <td><span style="background:{color};color:#fff;padding:3px 10px;border-radius:12px;font-size:12px">{r}</span></td>
          <td>{c.get('date_controle') or '—'}</td>
          <td>
            <a href="/qualite/{c['id']}/valider" style="background:#3b82f6;color:#fff;padding:4px 10px;border-radius:6px;text-decoration:none;font-size:12px">👁 Détail</a>
          </td>
        </tr>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">🔬 Contrôles qualité — Labo virtuel</h1>
      <a href="/qualite/nouveau" style="background:#10b981;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">+ Nouveau contrôle</a>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:22px">
      <div style="background:linear-gradient(135deg,#3b82f6,#1e40af);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Total contrôles</div>
        <div style="font-size:26px;font-weight:700">{total}</div>
      </div>
      <div style="background:linear-gradient(135deg,#10b981,#047857);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Conformes</div>
        <div style="font-size:26px;font-weight:700">{conformes}</div>
      </div>
      <div style="background:linear-gradient(135deg,#ef4444,#b91c1c);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Non conformes</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('nc',0)}</div>
      </div>
      <div style="background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Taux conformité</div>
        <div style="font-size:26px;font-weight:700">{taux:.1f}%</div>
      </div>
      <div style="background:linear-gradient(135deg,#f59e0b,#b45309);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Score moyen</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('score_moyen',0) or 0:.1f}</div>
      </div>
    </div>

    <div style="margin-bottom:16px">
      <a href="/qualite" style="padding:9px 18px;border-radius:8px;text-decoration:none;background:{'#1f2937' if not resultat else '#e5e7eb'};color:{'#fff' if not resultat else '#374151'};font-weight:600">Tous</a>
      <a href="/qualite?resultat=conforme" style="padding:9px 18px;border-radius:8px;text-decoration:none;background:{'#10b981' if resultat=='conforme' else '#e5e7eb'};color:{'#fff' if resultat=='conforme' else '#374151'};font-weight:600;margin-left:8px">Conformes</a>
      <a href="/qualite?resultat=non_conforme" style="padding:9px 18px;border-radius:8px;text-decoration:none;background:{'#ef4444' if resultat=='non_conforme' else '#e5e7eb'};color:{'#fff' if resultat=='non_conforme' else '#374151'};font-weight:600;margin-left:8px">Non conformes</a>
      <a href="/non-conformites" style="padding:9px 18px;border-radius:8px;text-decoration:none;background:#fef2f2;color:#b91c1c;font-weight:600;margin-left:8px">⚠ Registre NC</a>
    </div>

    <div style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <table style="width:100%;border-collapse:collapse">
        <thead style="background:#1f2937;color:#fff">
          <tr>
            <th style="padding:12px;text-align:left">N° CQ</th>
            <th style="padding:12px;text-align:left">Produit</th>
            <th style="padding:12px;text-align:left">OF</th>
            <th style="padding:12px;text-align:left">Type</th>
            <th style="padding:12px;text-align:right">Score</th>
            <th style="padding:12px;text-align:left">Résultat</th>
            <th style="padding:12px;text-align:left">Date</th>
            <th style="padding:12px;text-align:left">Action</th>
          </tr>
        </thead>
        <tbody>{rows_html or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#9ca3af">Aucun contrôle</td></tr>'}</tbody>
      </table>
    </div>
    """
    return _render(content, active='qualite', title='Qualité')


@qualite_bp.route('/qualite/nouveau', methods=['GET', 'POST'])
@login_required
def qualite_nouveau():
    db = _db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            produit_id = int(request.form.get('produit_fini_id') or 0) or None
            of_id = int(request.form.get('ordre_fabrication_id') or 0) or None
            type_ctrl = request.form.get('type_controle') or 'physico_chimique'
            score = float(request.form.get('score') or 0)
            resultat = 'conforme' if score >= 70 else 'non_conforme'
            observations = request.form.get('observations') or ''

            cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM controles_qualite")
            nid = cur.fetchone()[0]
            numero = f"CQ-{datetime.now().strftime('%Y%m')}-{nid:04d}"

            cur.execute("""
                INSERT INTO controles_qualite
                (numero, produit_fini_id, ordre_fabrication_id, type_controle,
                 score, resultat, observations, date_controle, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (numero, produit_id, of_id, type_ctrl, score, resultat,
                  observations, datetime.now().strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
            db.commit()
            _log('CREATE_CQ', f'{numero} — score={score} → {resultat}',
                 'controles_qualite', nid)
            flash(f'✅ Contrôle {numero} — {resultat} (score {score})', 'success')
            return redirect('/qualite')
        except Exception as e:
            db.rollback()
            flash(f'❌ {e}', 'error')

    cur.execute("SELECT id, nom FROM produits_finis ORDER BY nom")
    produits = _rows(cur)
    cur.execute("SELECT id, numero FROM ordres_fabrication ORDER BY id DESC LIMIT 200")
    ofs = _rows(cur)

    opts_p = ''.join(f'<option value="{p["id"]}">{p["nom"]}</option>' for p in produits)
    opts_o = '<option value="">— Aucun —</option>' + ''.join(f'<option value="{o["id"]}">{o["numero"]}</option>' for o in ofs)

    content = f"""
    <h1 style="color:#1f2937">🔬 Nouveau contrôle qualité</h1>
    <form method="post" style="background:#fff;padding:28px;border-radius:12px;max-width:760px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
        <div>
          <label style="font-weight:600">Produit fini *</label>
          <select name="produit_fini_id" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
            <option value="">— Sélectionner —</option>{opts_p}
          </select>
        </div>
        <div>
          <label style="font-weight:600">Ordre de fabrication</label>
          <select name="ordre_fabrication_id" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">{opts_o}</select>
        </div>
        <div>
          <label style="font-weight:600">Type de contrôle *</label>
          <select name="type_controle" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
            <option value="physico_chimique">Physico-chimique</option>
            <option value="microbiologique">Microbiologique</option>
            <option value="organoleptique">Organoleptique</option>
            <option value="emballage">Emballage / Étiquetage</option>
            <option value="pesticides">Résidus pesticides</option>
            <option value="metaux_lourds">Métaux lourds</option>
          </select>
        </div>
        <div>
          <label style="font-weight:600">Score (0-100) *</label>
          <input type="number" step="0.1" min="0" max="100" name="score" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
          <small style="color:#6b7280">≥ 70 = conforme automatiquement</small>
        </div>
        <div style="grid-column:1/-1">
          <label style="font-weight:600">Observations</label>
          <textarea name="observations" rows="3" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px"></textarea>
        </div>
      </div>
      <div style="margin-top:24px">
        <button type="submit" style="background:#10b981;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-weight:600;cursor:pointer">💾 Enregistrer</button>
        <a href="/qualite" style="margin-left:12px;color:#6b7280">Annuler</a>
      </div>
    </form>
    """
    return _render(content, active='qualite', title='Nouveau contrôle')


@qualite_bp.route('/qualite/<int:cid>/valider', methods=['GET', 'POST'])
@login_required
def qualite_valider(cid):
    db = _db()
    cur = db.cursor()
    cur.execute("""
        SELECT q.*, pf.nom AS produit_nom, of.numero AS of_numero
        FROM controles_qualite q
        LEFT JOIN produits_finis pf ON pf.id=q.produit_fini_id
        LEFT JOIN ordres_fabrication of ON of.id=q.ordre_fabrication_id
        WHERE q.id=?
    """, (cid,))
    cq = _row(cur)
    if not cq:
        flash('❌ Contrôle introuvable', 'error')
        return redirect('/qualite')

    if request.method == 'POST':
        try:
            nouveau_resultat = request.form.get('resultat') or cq.get('resultat')
            observations = request.form.get('observations') or cq.get('observations') or ''
            cur.execute("""
                UPDATE controles_qualite SET resultat=?, observations=? WHERE id=?
            """, (nouveau_resultat, observations, cid))
            db.commit()
            _log('UPDATE_CQ', f'CQ#{cid} → {nouveau_resultat}', 'controles_qualite', cid)
            flash(f'✅ Contrôle mis à jour : {nouveau_resultat}', 'success')
            return redirect('/qualite')
        except Exception as e:
            db.rollback()
            flash(f'❌ {e}', 'error')

    color = {'conforme': '#10b981', 'non_conforme': '#ef4444',
             'en_attente': '#f59e0b'}.get(cq.get('resultat'), '#6b7280')

    content = f"""
    <h1 style="color:#1f2937">🔬 Contrôle {cq.get('numero') or f'CQ-{cid}'}</h1>
    <div style="background:#fff;padding:28px;border-radius:12px;max-width:760px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:20px">
        <div><strong>Produit :</strong> {cq.get('produit_nom') or '—'}</div>
        <div><strong>OF :</strong> {cq.get('of_numero') or '—'}</div>
        <div><strong>Type :</strong> {cq.get('type_controle') or '—'}</div>
        <div><strong>Score :</strong> {cq.get('score') or 0:.1f}/100</div>
        <div><strong>Date :</strong> {cq.get('date_controle') or '—'}</div>
        <div><strong>Résultat actuel :</strong> <span style="background:{color};color:#fff;padding:3px 10px;border-radius:12px;font-size:12px">{cq.get('resultat') or '—'}</span></div>
      </div>
      <form method="post">
        <div style="margin-bottom:16px">
          <label style="font-weight:600">Résultat</label>
          <select name="resultat" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
            <option value="conforme" {'selected' if cq.get('resultat')=='conforme' else ''}>✅ Conforme</option>
            <option value="non_conforme" {'selected' if cq.get('resultat')=='non_conforme' else ''}>❌ Non conforme</option>
            <option value="en_attente" {'selected' if cq.get('resultat')=='en_attente' else ''}>⏳ En attente</option>
          </select>
        </div>
        <div style="margin-bottom:16px">
          <label style="font-weight:600">Observations</label>
          <textarea name="observations" rows="4" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">{cq.get('observations') or ''}</textarea>
        </div>
        <button type="submit" style="background:#10b981;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-weight:600;cursor:pointer">💾 Enregistrer</button>
        <a href="/qualite" style="margin-left:12px;color:#6b7280">Retour</a>
      </form>
    </div>
    """
    return _render(content, active='qualite', title='Contrôle qualité')


# ═══════════════════════════════════════════════════════════════
# ⚠ NON-CONFORMITÉS — Registre
# ═══════════════════════════════════════════════════════════════

@qualite_bp.route('/non-conformites')
@login_required
def nc_liste():
    db = _db()
    cur = db.cursor()
    try:
        cur.execute("""
            SELECT nc.*, pf.nom AS produit_nom
            FROM non_conformites nc
            LEFT JOIN produits_finis pf ON pf.id = nc.produit_fini_id
            ORDER BY nc.id DESC LIMIT 200
        """)
        ncs = _rows(cur)
    except Exception:
        ncs = []

    rows_html = ''
    for n in ncs:
        grav = n.get('gravite') or 'mineure'
        color = {'critique': '#dc2626', 'majeure': '#f59e0b',
                 'mineure': '#3b82f6'}.get(grav, '#6b7280')
        rows_html += f"""
        <tr>
          <td><strong>{n.get('numero') or f'NC-{n["id"]:04d}'}</strong></td>
          <td>{n.get('produit_nom') or '—'}</td>
          <td>{n.get('description') or '—'}</td>
          <td><span style="background:{color};color:#fff;padding:3px 10px;border-radius:12px;font-size:12px">{grav}</span></td>
          <td>{n.get('action_corrective') or '—'}</td>
          <td>{n.get('statut') or 'ouverte'}</td>
          <td>{n.get('date_detection') or '—'}</td>
        </tr>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">⚠ Registre des non-conformités</h1>
      <a href="/qualite" style="background:#e5e7eb;color:#374151;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">← Contrôles</a>
    </div>

    <div style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <table style="width:100%;border-collapse:collapse">
        <thead style="background:#1f2937;color:#fff">
          <tr>
            <th style="padding:12px;text-align:left">N° NC</th>
            <th style="padding:12px;text-align:left">Produit</th>
            <th style="padding:12px;text-align:left">Description</th>
            <th style="padding:12px;text-align:left">Gravité</th>
            <th style="padding:12px;text-align:left">Action corrective</th>
            <th style="padding:12px;text-align:left">Statut</th>
            <th style="padding:12px;text-align:left">Détection</th>
          </tr>
        </thead>
        <tbody>{rows_html or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#9ca3af">Aucune non-conformité</td></tr>'}</tbody>
      </table>
    </div>
    """
    return _render(content, active='qualite', title='Non-conformités')


@qualite_bp.route('/api/qualite/kpi')
@login_required
def api_qualite_kpi():
    db = _db()
    cur = db.cursor()
    cur.execute("""
        SELECT type_controle,
               COUNT(*) AS nb,
               AVG(score) AS score_moyen,
               SUM(CASE WHEN resultat='conforme' THEN 1 ELSE 0 END) AS conformes
        FROM controles_qualite
        GROUP BY type_controle
        ORDER BY nb DESC
    """)
    return jsonify(_rows(cur))
