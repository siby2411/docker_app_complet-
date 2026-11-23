"""
🎓 Omega Agro-Industrie — Centre de formation
Sessions · Inscriptions · Formateurs · Certifications
"""
from flask import Blueprint, request, redirect, flash, jsonify
from flask_login import current_user, login_required
from datetime import datetime

formation_bp = Blueprint('formation', __name__)
_deps = {}


def init_formation(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(formation_bp)
    print("[FORMATION] ✅ Module formation enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='formation', title='Formation'):
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
# 🎓 SESSIONS DE FORMATION
# ═══════════════════════════════════════════════════════════════

@formation_bp.route('/formation')
@login_required
def formation_liste():
    db = _db()
    cur = db.cursor()

    try:
        cur.execute("""
            SELECT f.*,
                   (SELECT COUNT(*) FROM inscriptions_formation i WHERE i.session_id=f.id) AS nb_inscrits
            FROM sessions_formation f
            ORDER BY f.date_debut DESC LIMIT 100
        """)
        sessions = _rows(cur)
    except Exception:
        sessions = []

    cur.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN statut='planifiee' THEN 1 ELSE 0 END) AS planifiees,
               SUM(CASE WHEN statut='en_cours' THEN 1 ELSE 0 END) AS en_cours,
               SUM(CASE WHEN statut='terminee' THEN 1 ELSE 0 END) AS terminees
        FROM sessions_formation
    """) if sessions else None
    try:
        kpi = _row(cur) or {}
    except Exception:
        kpi = {}

    rows_html = ''
    for s in sessions:
        st = s.get('statut') or 'planifiee'
        color = {'planifiee': '#3b82f6', 'en_cours': '#f59e0b',
                 'terminee': '#10b981', 'annulee': '#ef4444'}.get(st, '#6b7280')
        rows_html += f"""
        <tr>
          <td><strong>{s.get('titre') or f'SESSION-{s["id"]}'}</strong></td>
          <td>{s.get('theme') or '—'}</td>
          <td>{s.get('formateur') or '—'}</td>
          <td>{s.get('lieu') or '—'}</td>
          <td>{s.get('date_debut') or '—'}</td>
          <td>{s.get('date_fin') or '—'}</td>
          <td style="text-align:center">{s.get('nb_inscrits') or 0} / {s.get('capacite') or '?'}</td>
          <td><span style="background:{color};color:#fff;padding:3px 10px;border-radius:12px;font-size:12px">{st}</span></td>
          <td>
            <a href="/formation/{s['id']}/inscrire" style="background:#10b981;color:#fff;padding:4px 10px;border-radius:6px;text-decoration:none;font-size:12px">➕ Inscrire</a>
          </td>
        </tr>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">🎓 Centre de formation agricole</h1>
      <a href="/formation/nouvelle" style="background:#10b981;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">+ Nouvelle session</a>
    </div>

    <div style="background:linear-gradient(135deg,#7c3aed,#5b21b6);color:#fff;padding:18px;border-radius:12px;margin-bottom:22px">
      <div style="font-size:13px;opacity:.9">🌾 Former les producteurs aux bonnes pratiques agricoles, à la transformation et à l'export UE</div>
      <div style="font-size:13px;opacity:.9;margin-top:6px">Thèmes : mangue · noix de cajou · HACCP · GlobalG.A.P. · énergie solaire</div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:22px">
      <div style="background:linear-gradient(135deg,#3b82f6,#1e40af);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Total sessions</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('total',len(sessions))}</div>
      </div>
      <div style="background:linear-gradient(135deg,#f59e0b,#b45309);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">En cours</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('en_cours',0)}</div>
      </div>
      <div style="background:linear-gradient(135deg,#10b981,#047857);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Terminées</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('terminees',0)}</div>
      </div>
      <div style="background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Planifiées</div>
        <div style="font-size:26px;font-weight:700">{kpi.get('planifiees',0)}</div>
      </div>
    </div>

    <div style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <table style="width:100%;border-collapse:collapse">
        <thead style="background:#1f2937;color:#fff">
          <tr>
            <th style="padding:12px;text-align:left">Titre</th>
            <th style="padding:12px;text-align:left">Thème</th>
            <th style="padding:12px;text-align:left">Formateur</th>
            <th style="padding:12px;text-align:left">Lieu</th>
            <th style="padding:12px;text-align:left">Début</th>
            <th style="padding:12px;text-align:left">Fin</th>
            <th style="padding:12px;text-align:center">Inscrits</th>
            <th style="padding:12px;text-align:left">Statut</th>
            <th style="padding:12px;text-align:left">Action</th>
          </tr>
        </thead>
        <tbody>{rows_html or '<tr><td colspan="9" style="padding:40px;text-align:center;color:#9ca3af">Aucune session</td></tr>'}</tbody>
      </table>
    </div>
    """
    return _render(content, active='formation', title='Formation')


@formation_bp.route('/formation/nouvelle', methods=['GET', 'POST'])
@login_required
def formation_nouvelle():
    db = _db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO sessions_formation
                (titre, theme, formateur, lieu, date_debut, date_fin,
                 capacite, statut, description, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                request.form.get('titre'),
                request.form.get('theme'),
                request.form.get('formateur'),
                request.form.get('lieu'),
                request.form.get('date_debut'),
                request.form.get('date_fin'),
                int(request.form.get('capacite') or 30),
                'planifiee',
                request.form.get('description') or '',
                datetime.now().isoformat()
            ))
            db.commit()
            _log('CREATE_SESSION', request.form.get('titre', ''), 'sessions_formation')
            flash('✅ Session de formation créée', 'success')
            return redirect('/formation')
        except Exception as e:
            db.rollback()
            flash(f'❌ {e}', 'error')

    content = f"""
    <h1 style="color:#1f2937">🎓 Nouvelle session de formation</h1>
    <form method="post" style="background:#fff;padding:28px;border-radius:12px;max-width:820px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
        <div style="grid-column:1/-1">
          <label style="font-weight:600">Titre *</label>
          <input type="text" name="titre" required placeholder="Ex: Bonnes pratiques transformation mangue" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Thème</label>
          <select name="theme" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
            <option value="mangue">🥭 Mangue</option>
            <option value="noix_cajou">🥜 Noix de cajou</option>
            <option value="fruits_legumes">🥬 Fruits & légumes</option>
            <option value="haccp">🔬 HACCP / ISO 22000</option>
            <option value="globalgap">🌍 GlobalG.A.P.</option>
            <option value="solaire">☀️ Énergie solaire</option>
            <option value="materiel">🚜 Matériel agricole</option>
            <option value="export">📦 Export UE</option>
          </select>
        </div>
        <div>
          <label style="font-weight:600">Formateur</label>
          <input type="text" name="formateur" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Lieu</label>
          <input type="text" name="lieu" placeholder="Ex: Centre de formation Bambey" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Capacité</label>
          <input type="number" name="capacite" value="30" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Date début</label>
          <input type="date" name="date_debut" value="{datetime.now().strftime('%Y-%m-%d')}" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Date fin</label>
          <input type="date" name="date_fin" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div style="grid-column:1/-1">
          <label style="font-weight:600">Description</label>
          <textarea name="description" rows="3" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px"></textarea>
        </div>
      </div>
      <div style="margin-top:24px">
        <button type="submit" style="background:#10b981;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-weight:600;cursor:pointer">💾 Créer</button>
        <a href="/formation" style="margin-left:12px;color:#6b7280">Annuler</a>
      </div>
    </form>
    """
    return _render(content, active='formation', title='Nouvelle session')


@formation_bp.route('/formation/<int:sid>/inscrire', methods=['GET', 'POST'])
@login_required
def formation_inscrire(sid):
    db = _db()
    cur = db.cursor()
    cur.execute("SELECT * FROM sessions_formation WHERE id=?", (sid,))
    s = _row(cur)
    if not s:
        flash('❌ Session introuvable', 'error')
        return redirect('/formation')

    if request.method == 'POST':
        try:
            producteur_id = int(request.form.get('producteur_id') or 0)
            cur.execute("""
                INSERT INTO inscriptions_formation
                (session_id, producteur_id, statut, date_inscription, created_at)
                VALUES (?,?,'inscrit',?,?)
            """, (sid, producteur_id, datetime.now().strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
            db.commit()
            _log('INSCRIPTION', f'Session#{sid} — producteur#{producteur_id}',
                 'inscriptions_formation')
            flash('✅ Producteur inscrit', 'success')
            return redirect('/formation')
        except Exception as e:
            db.rollback()
            flash(f'❌ {e}', 'error')

    cur.execute("SELECT id, nom, region FROM producteurs ORDER BY nom LIMIT 500")
    producteurs = _rows(cur)
    opts = ''.join(f'<option value="{p["id"]}">{p["nom"]} ({p.get("region") or ""})</option>' for p in producteurs)

    content = f"""
    <h1 style="color:#1f2937">🎓 Inscrire à : {s.get('titre')}</h1>
    <div style="background:#f0f9ff;border-left:4px solid #3b82f6;padding:14px;border-radius:8px;margin-bottom:20px;max-width:600px">
      <strong>Formateur :</strong> {s.get('formateur') or '—'}<br>
      <strong>Lieu :</strong> {s.get('lieu') or '—'}<br>
      <strong>Dates :</strong> {s.get('date_debut')} → {s.get('date_fin') or '—'}
    </div>
    <form method="post" style="background:#fff;padding:28px;border-radius:12px;max-width:600px">
      <label style="font-weight:600">Producteur *</label>
      <select name="producteur_id" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        <option value="">— Sélectionner —</option>{opts}
      </select>
      <div style="margin-top:24px">
        <button type="submit" style="background:#10b981;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-weight:600;cursor:pointer">💾 Inscrire</button>
        <a href="/formation" style="margin-left:12px;color:#6b7280">Annuler</a>
      </div>
    </form>
    """
    return _render(content, active='formation', title='Inscription')


@formation_bp.route('/api/formation/kpi')
@login_required
def api_formation_kpi():
    db = _db()
    cur = db.cursor()
    cur.execute("""
        SELECT theme, COUNT(*) AS nb_sessions, SUM(capacite) AS capacite_totale
        FROM sessions_formation GROUP BY theme ORDER BY nb_sessions DESC
    """)
    return jsonify(_rows(cur))
