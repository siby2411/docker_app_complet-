"""
🎓 Formation Professionnelle — Application principale
Formations · Sessions · Apprenants · Évaluations · Certificats · 3FPT
"""
from flask import Flask, render_template_string, redirect, url_for, session, request, jsonify, Response, send_file, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import sqlite3
import os
import io

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'omega-formation-secret-2026')

DB_PATH = '/app/data/formation_pro.db'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id, username, role, nom_complet, specialite=''):
        self.id = id
        self.username = username
        self.role = role
        self.nom_complet = nom_complet
        self.specialite = specialite


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def log_action(user_id, action, details='', entity=None, entity_id=None):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO audit_log (user_id, action, entity, entity_id, details, ip, created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (user_id, action, entity, entity_id, details,
              request.remote_addr if request else '', datetime.now().isoformat()))
        db.commit()
    except Exception:
        pass


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    r = cur.fetchone()
    if r:
        return User(r['id'], r['username'], r['role'], r['nom_complet'], r['specialite'] or '')
    return None


# ═══════════════════════════════════════════════════════════════
# LAYOUT — DESIGN FORMATION PRO
# ═══════════════════════════════════════════════════════════════

LAYOUT = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — OMEGA Formation Pro</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,-apple-system,sans-serif}}
body{{background:#fef7f0;color:#1e293b;font-size:14px}}
.nav{{background:linear-gradient(135deg,#ea580c,#c2410c);color:#fff;padding:0 22px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 3px 12px rgba(0,0,0,.15);flex-wrap:wrap;border-bottom:4px solid #2563eb}}
.nav-brand{{font-weight:900;font-size:18px;display:flex;align-items:center;gap:12px;padding:16px 0;letter-spacing:-0.3px}}
.nav-brand-icon{{width:40px;height:40px;background:#2563eb;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(37,99,235,.4)}}
.nav-links{{display:flex;gap:2px;flex-wrap:wrap}}
.nav-links a{{color:#fed7aa;text-decoration:none;padding:8px 13px;border-radius:8px;font-size:12.5px;font-weight:600;transition:.2s;display:flex;align-items:center;gap:6px}}
.nav-links a:hover{{background:rgba(255,255,255,.15);color:#fff}}
.nav-links a.active{{background:#2563eb;color:#fff;box-shadow:0 4px 10px rgba(37,99,235,.4)}}
.nav-user{{font-size:12.5px;display:flex;gap:10px;align-items:center;color:#fed7aa}}
.nav-user a{{color:#fff;text-decoration:none;background:rgba(0,0,0,.25);padding:7px 14px;border-radius:8px;font-weight:600}}
.container{{max-width:1600px;margin:0 auto;padding:24px}}
h1{{color:#c2410c;margin-bottom:20px;font-size:24px;font-weight:800;letter-spacing:-0.4px}}
h2{{color:#ea580c;font-size:18px;margin-bottom:14px;font-weight:700}}
.card{{background:#fff;padding:22px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:18px;border-left:4px solid #ea580c}}
table{{width:100%;border-collapse:collapse}}
thead{{background:#c2410c;color:#fff}}
th{{padding:12px;text-align:left;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}}
td{{padding:11px;border-bottom:1px solid #f1f5f9;font-size:13.5px}}
tbody tr:hover{{background:#fff7ed}}
.btn{{display:inline-block;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px;border:none;cursor:pointer;transition:.15s;letter-spacing:.2px}}
.btn:hover{{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.15)}}
.btn-primary{{background:#ea580c;color:#fff}}
.btn-blue{{background:#2563eb;color:#fff}}
.btn-success{{background:#10b981;color:#fff}}
.btn-danger{{background:#ef4444;color:#fff}}
.btn-warning{{background:#f59e0b;color:#fff}}
.btn-secondary{{background:#64748b;color:#fff}}
input,select,textarea{{width:100%;padding:11px 14px;border:2px solid #e2e8f0;border-radius:8px;font-size:13.5px;font-family:inherit;transition:.2s}}
input:focus,select:focus,textarea:focus{{outline:none;border-color:#ea580c;box-shadow:0 0 0 3px rgba(234,88,12,.1)}}
label{{display:block;font-weight:700;margin-bottom:6px;font-size:12.5px;color:#334155;text-transform:uppercase;letter-spacing:.3px}}
.kpi{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:22px}}
.kpi-card{{padding:18px;border-radius:12px;color:#fff;position:relative;overflow:hidden}}
.kpi-card::after{{content:'';position:absolute;top:-20px;right:-20px;width:80px;height:80px;background:rgba(255,255,255,.1);border-radius:50%}}
.kpi-card .kpi-label{{font-size:11.5px;opacity:.9;text-transform:uppercase;letter-spacing:.5px;font-weight:600}}
.kpi-card .kpi-value{{font-size:26px;font-weight:900;margin-top:6px;letter-spacing:-0.5px}}
.kpi-card .kpi-icon{{position:absolute;top:16px;right:18px;font-size:28px;opacity:.25}}
.flash{{padding:14px 20px;border-radius:10px;margin-bottom:16px;font-size:13.5px;font-weight:600;border-left:4px solid}}
.flash-success{{background:#d1fae5;color:#065f46;border-color:#10b981}}
.flash-error{{background:#fee2e2;color:#991b1b;border-color:#ef4444}}
.badge{{display:inline-block;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.4px}}
.badge-blue{{background:#dbeafe;color:#1e40af}}
.badge-green{{background:#d1fae5;color:#047857}}
.badge-orange{{background:#fed7aa;color:#c2410c}}
.badge-red{{background:#fee2e2;color:#b91c1c}}
.badge-gray{{background:#e2e8f0;color:#475569}}
.badge-yellow{{background:#fef3c7;color:#b45309}}
.form-card{{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:.2s;border-top:4px solid #ea580c}}
.form-card:hover{{transform:translateY(-3px);box-shadow:0 8px 20px rgba(234,88,12,.15)}}
.form-icon{{background:linear-gradient(135deg,#ea580c,#c2410c);color:#fff;height:90px;display:flex;align-items:center;justify-content:center;font-size:40px}}
.form-body{{padding:16px}}
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-brand">
    <div class="nav-brand-icon">🎓</div>
    <div>OMEGA FORMATION<span style="display:block;font-size:10px;font-weight:500;letter-spacing:2px;color:#fed7aa">PRO · 3FPT · SÉNÉGAL</span></div>
  </div>
  <div class="nav-links">
    <a href="/" class="{a_dash}">📊 Dashboard</a>
    <a href="/formations" class="{a_form}">🎓 Formations</a>
    <a href="/sessions" class="{a_sess}">📅 Sessions</a>
    <a href="/apprenants" class="{a_appr}">👥 Apprenants</a>
    <a href="/formateurs" class="{a_ftr}">👨‍🏫 Formateurs</a>
    <a href="/centres" class="{a_ctr}">🏫 Centres</a>
    <a href="/certificats" class="{a_cert}">📜 Certificats</a>
    <a href="/financements" class="{a_fin}">💰 Financements</a>
    <a href="/partenariats" class="{a_part}">🔗 Partenariats</a>
    <a href="/placements" class="{a_plac}">📈 Placement</a>
    <a href="/rapports" class="{a_rap}">📊 Rapports</a>
  </div>
  <div class="nav-user">
    <span>👤 {user_name}</span>
    <a href="/logout">Déconnexion</a>
  </div>
</nav>
<div class="container">
  {flashes}
  {content}
</div>
</body>
</html>'''


def render_page(content, active='dashboard', page_title='Formation'):
    from flask import get_flashed_messages
    user_name = current_user.nom_complet if current_user.is_authenticated else ''
    msgs = get_flashed_messages(with_categories=True)
    flashes = ''
    for cat, msg in msgs:
        flashes += f'<div class="flash flash-{cat}">{msg}</div>'

    return LAYOUT.format(
        title=page_title,
        user_name=user_name,
        content=content,
        flashes=flashes,
        a_dash='active' if active == 'dashboard' else '',
        a_form='active' if active == 'formations' else '',
        a_sess='active' if active == 'sessions' else '',
        a_appr='active' if active == 'apprenants' else '',
        a_ftr='active' if active == 'formateurs' else '',
        a_ctr='active' if active == 'centres' else '',
        a_cert='active' if active == 'certificats' else '',
        a_fin='active' if active == 'financements' else '',
        a_part='active' if active == 'partenariats' else '',
        a_plac='active' if active == 'placements' else '',
        a_rap='active' if active == 'rapports' else '',
    )


@app.route('/health')
def health():
    return {'project': 'OMEGA FORMATION PRO', 'service': 'formation-professionnelle',
            'status': 'ok', 'timestamp': datetime.now().isoformat(), 'version': '1.0'}


LOGIN_HTML = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Connexion — OMEGA Formation Pro</title>
<style>body{{font-family:system-ui;background:linear-gradient(135deg,#ea580c,#c2410c);min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0}}
.box{{background:#fff;padding:42px;border-radius:16px;box-shadow:0 25px 70px rgba(0,0,0,.4);width:100%;max-width:420px;border-top:5px solid #2563eb}}
.logo{{text-align:center;font-size:56px;margin-bottom:12px}}
h1{{color:#c2410c;margin:0 0 6px;text-align:center;font-size:22px;font-weight:900;letter-spacing:-0.3px}}
.subtitle{{text-align:center;color:#64748b;font-size:12px;margin-bottom:24px;letter-spacing:1.5px;text-transform:uppercase;font-weight:600}}
input{{width:100%;padding:14px;border:2px solid #e2e8f0;border-radius:10px;margin-bottom:14px;font-size:15px;box-sizing:border-box}}
input:focus{{outline:none;border-color:#ea580c;box-shadow:0 0 0 3px rgba(234,88,12,.1)}}
button{{width:100%;background:#2563eb;color:#fff;padding:15px;border:none;border-radius:10px;font-weight:800;font-size:15px;cursor:pointer;letter-spacing:.5px;text-transform:uppercase}}
button:hover{{background:#1e40af}}
.err{{background:#fee2e2;color:#991b1b;padding:11px;border-radius:8px;margin-bottom:14px;font-size:13px;border-left:4px solid #ef4444}}
.hint{{margin-top:20px;padding:12px;background:#fff7ed;border-radius:8px;font-size:12px;color:#c2410c;text-align:center;border:1px dashed #fdba74}}</style></head>
<body><div class="box">
<div class="logo">🎓</div>
<h1>OMEGA FORMATION PRO</h1>
<div class="subtitle">3FPT · Insertion Jeunes · Sénégal</div>
{error}
<form method="post">
<input type="text" name="username" placeholder="Nom d'utilisateur" required autofocus>
<input type="password" name="password" placeholder="Mot de passe" required>
<button type="submit">Se connecter</button>
</form>
<div class="hint">admin / admin123</div></div></body></html>'''


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        from werkzeug.security import check_password_hash
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND actif=1", (username,))
        r = cur.fetchone()
        if r and check_password_hash(r['password_hash'], password):
            user = User(r['id'], r['username'], r['role'], r['nom_complet'], r['specialite'] or '')
            login_user(user)
            log_action(user.id, 'LOGIN', f'{username} connecté', 'users', user.id)
            return redirect(url_for('dashboard'))
        return LOGIN_HTML.format(error='<div class="err">Identifiants invalides</div>'), 401
    return LOGIN_HTML.format(error='')


@app.route('/logout')
@login_required
def logout():
    log_action(current_user.id, 'LOGOUT', current_user.username, 'users', current_user.id)
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    db = get_db()
    cur = db.cursor()

    def sc(sql, default=0):
        try:
            cur.execute(sql)
            r = cur.fetchone()
            return r[0] if r and r[0] is not None else default
        except Exception:
            return default

    stats = {
        'formations': sc("SELECT COUNT(*) FROM formations WHERE statut='actif'"),
        'sessions_encours': sc("SELECT COUNT(*) FROM sessions WHERE statut='en_cours'"),
        'sessions_planifiees': sc("SELECT COUNT(*) FROM sessions WHERE statut='planifiee'"),
        'sessions_terminees': sc("SELECT COUNT(*) FROM sessions WHERE statut='terminee'"),
        'apprenants': sc("SELECT COUNT(*) FROM apprenants WHERE statut='actif'"),
        'inscriptions': sc("SELECT COUNT(*) FROM inscriptions"),
        'certificats': sc("SELECT COUNT(*) FROM certificats WHERE statut='valide'"),
        'placements': sc("SELECT COUNT(*) FROM placements WHERE statut='actif'"),
        'partenariats': sc("SELECT COUNT(*) FROM partenariats WHERE statut='actif'"),
        'formations_financees': sc("SELECT COALESCE(SUM(montant_total),0) FROM financements"),
        'formations_utilisees': sc("SELECT COALESCE(SUM(montant_utilise),0) FROM financements"),
    }

    # Taux d'employabilité (placements / certificats)
    taux_emploi = (stats['placements'] / stats['certificats'] * 100) if stats['certificats'] > 0 else 0

    # Sessions en cours
    cur.execute("""
        SELECT s.*, f.nom AS formation_nom, f.domaine,
               c.nom AS centre_nom, ftr.nom_complet AS formateur_nom
        FROM sessions s
        LEFT JOIN formations f ON f.id=s.formation_id
        LEFT JOIN centres c ON c.id=s.centre_id
        LEFT JOIN formateurs ftr ON ftr.id=s.formateur_id
        WHERE s.statut IN ('en_cours', 'planifiee')
        ORDER BY s.date_debut ASC LIMIT 6
    """)
    sessions = cur.fetchall()

    sess_html = ''
    for s in sessions:
        statut_badge = {
            'planifiee': 'badge-blue',
            'en_cours': 'badge-orange',
            'terminee': 'badge-green',
        }.get(s['statut'], 'badge-gray')
        rows = ''
        sess_html += (
            '<tr><td><strong style="color:#ea580c">' + str(s["code"] or "—") + '</strong></td>'
            + '<td><strong>' + str(s["formation_nom"] or "—") + '</strong><br><small style="color:#64748b">' + str(s["domaine"] or "") + '</small></td>'
            + '<td>' + str(s["centre_nom"] or "—") + '</td>'
            + '<td>' + str(s["formateur_nom"] or "—") + '</td>'
            + '<td>' + str((s["date_debut"] or "—")[:10]) + '</td>'
            + '<td style="text-align:center">' + str(s["nb_inscrits"]) + '/' + str(s["capacite"]) + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(s["statut"]) + '</span></td></tr>'
        )

    # Top formations
    cur.execute("""
        SELECT f.nom, f.domaine, f.duree_heures, f.cout_formation,
               COUNT(i.id) AS nb_inscrits
        FROM formations f
        LEFT JOIN sessions s ON s.formation_id=f.id
        LEFT JOIN inscriptions i ON i.session_id=s.id
        GROUP BY f.id
        ORDER BY nb_inscrits DESC LIMIT 6
    """)
    top_form = cur.fetchall()
    top_html = ''.join(
        '<tr><td><strong>' + str(f["nom"]) + '</strong><br><small style="color:#64748b">' + str(f["domaine"] or "") + '</small></td>'
        + '<td style="text-align:center">' + str(f["duree_heures"]) + 'h</td>'
        + '<td style="text-align:right">' + f'{f["cout_formation"]:,.0f}' + ' F</td>'
        + '<td style="text-align:center;font-weight:800;color:#10b981">' + str(f["nb_inscrits"]) + '</td></tr>'
        for f in top_form
    )

    content = '<h1>🎓 Tableau de bord Formation Pro</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-icon">🎓</div><div class="kpi-label">Formations</div><div class="kpi-value">' + str(stats["formations"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-icon">📅</div><div class="kpi-label">Sessions en cours</div><div class="kpi-value">' + str(stats["sessions_encours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">👥</div><div class="kpi-label">Apprenants</div><div class="kpi-value">' + str(stats["apprenants"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">📜</div><div class="kpi-label">Certificats</div><div class="kpi-value">' + str(stats["certificats"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">💼</div><div class="kpi-label">Placements</div><div class="kpi-value">' + str(stats["placements"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div class="kpi-icon">📈</div><div class="kpi-label">Taux employabilité</div><div class="kpi-value">' + f'{taux_emploi:.0f}' + '%</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">🔗</div><div class="kpi-label">Partenariats</div><div class="kpi-value">' + str(stats["partenariats"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#64748b,#475569)"><div class="kpi-icon">💰</div><div class="kpi-label">Financement 3FPT</div><div class="kpi-value" style="font-size:16px">' + f'{stats["formations_financees"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:18px">'
    content += '<div class="card"><h2>📅 Sessions actives</h2>'
    content += '<table><thead><tr><th>Code</th><th>Formation</th><th>Centre</th><th>Formateur</th><th>Début</th><th style="text-align:center">Inscrits</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (sess_html or '<tr><td colspan="7" style="text-align:center;color:#94a3b8;padding:30px">Aucune session active</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>🎓 Top 6 formations</h2>'
    content += '<table><thead><tr><th>Formation</th><th style="text-align:center">Durée</th><th style="text-align:right">Coût</th><th style="text-align:center">Inscrits</th></tr></thead>'
    content += '<tbody>' + (top_html or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:30px">Aucune formation</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    # Financement 3FPT
    cur.execute("SELECT bailleur, montant_total, montant_utilise FROM financements WHERE statut='actif'")
    fins = cur.fetchall()
    fin_html = ''
    for f in fins:
        pct = (f['montant_utilise'] / f['montant_total'] * 100) if f['montant_total'] > 0 else 0
        fin_html += (
            '<div style="margin-bottom:14px">'
            + '<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px">'
            + '<strong>' + str(f["bailleur"]) + '</strong>'
            + '<span style="color:#64748b">' + f'{f["montant_utilise"]:,.0f}' + ' / ' + f'{f["montant_total"]:,.0f}' + ' F</span></div>'
            + '<div style="background:#e2e8f0;border-radius:6px;overflow:hidden;height:12px">'
            + '<div style="background:linear-gradient(90deg,#10b981,#047857);height:100%;width:' + f'{pct:.0f}' + '%"></div></div></div>'
        )

    content += '<div class="card"><h2>💰 Utilisation des financements</h2>' + fin_html + '</div>'

    return render_page(content, active='dashboard', page_title='Dashboard')


@app.route('/formations')
@login_required
def formations_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()
    domaine_f = request.args.get('domaine', '')

    sql = """
        SELECT f.*,
               (SELECT COUNT(DISTINCT s.id) FROM sessions s WHERE s.formation_id=f.id) AS nb_sessions,
               (SELECT COUNT(i.id) FROM inscriptions i JOIN sessions s ON s.id=i.session_id WHERE s.formation_id=f.id) AS nb_apprenants
        FROM formations f
        WHERE 1=1
    """
    params = []
    if q:
        sql += " AND (f.nom LIKE ? OR f.description LIKE ? OR f.domaine LIKE ?)"
        params += [f'%{q}%'] * 3
    if domaine_f:
        sql += " AND f.domaine=?"
        params.append(domaine_f)
    sql += " ORDER BY f.domaine, f.nom LIMIT 200"
    cur.execute(sql, params)
    formations = cur.fetchall()

    cur.execute("SELECT DISTINCT domaine FROM formations WHERE domaine IS NOT NULL ORDER BY domaine")
    domaines = [r[0] for r in cur.fetchall()]

    stats = {}
    cur.execute("SELECT COUNT(*) FROM formations WHERE statut='actif'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT domaine) FROM formations")
    stats['domaines'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sessions")
    stats['sessions'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(cout_formation),0) FROM formations")
    stats['cout_moy'] = cur.fetchone()[0]

    # Grille
    cards = ''
    for f in formations:
        domain_icons = {
            'BTP': '🏗️', 'Agro': '🌾', 'Numérique': '💻',
            'Commerce': '💼', 'Santé': '🏥', 'Hôtellerie': '🍽️',
        }
        icon = domain_icons.get(f['domaine'], '🎓')
        cards += '<div class="form-card">'
        cards += '<div class="form-icon">' + icon + '</div>'
        cards += '<div class="form-body">'
        cards += '<div style="font-weight:800;color:#1e293b;font-size:14px;margin-bottom:4px">' + str(f["nom"]) + '</div>'
        cards += '<div style="font-size:11.5px;color:#64748b;margin-bottom:8px"><span class="badge badge-orange">' + str(f["domaine"] or "—") + '</span></div>'
        cards += '<div style="font-size:12px;color:#475569;margin-bottom:10px">' + str(f["description"] or "")[:70] + '...</div>'
        cards += '<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:10px">'
        cards += '<span style="color:#64748b">⏱ ' + str(f["duree_heures"]) + 'h</span>'
        cards += '<span style="color:#64748b">📚 ' + str(f["nb_sessions"]) + ' sessions</span>'
        cards += '</div>'
        cards += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'
        cards += '<div style="font-size:16px;font-weight:900;color:#10b981">' + f'{f["cout_formation"]:,.0f}' + ' F</div>'
        cards += '<span style="font-size:11.5px;color:#64748b">👥 ' + str(f["nb_apprenants"]) + '</span>'
        cards += '</div>'
        cards += '<a href="/formations/' + str(f["id"]) + '" class="btn btn-primary" style="padding:6px 10px;font-size:11.5px;width:100%;text-align:center;display:block">👁 Voir détails</a>'
        cards += '</div></div>'

    cats_html = '<a href="/formations" class="btn ' + ('btn-primary' if not domaine_f else 'btn-secondary') + '">Tous</a> '
    for d in domaines:
        active_cls = 'btn-primary' if domaine_f == d else 'btn-secondary'
        cats_html += '<a href="/formations?domaine=' + d + '" class="btn ' + active_cls + '" style="margin-left:6px">' + d + '</a> '

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🎓 Catalogue Formations — ' + str(len(formations)) + '</h1>'
    content += '<a href="/formations/nouvelle" class="btn btn-primary">+ Nouvelle formation</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-icon">🎓</div><div class="kpi-label">Formations actives</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-icon">📚</div><div class="kpi-label">Domaines</div><div class="kpi-value">' + str(stats["domaines"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">📅</div><div class="kpi-label">Sessions totales</div><div class="kpi-value">' + str(stats["sessions"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">💰</div><div class="kpi-label">Coût moyen</div><div class="kpi-value" style="font-size:18px">' + f'{stats["cout_moy"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher formation..." style="max-width:500px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="margin-bottom:20px;display:flex;gap:6px;flex-wrap:wrap">' + cats_html + '</div>'

    content += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px">' + (cards or '<p style="grid-column:1/-1;text-align:center;color:#94a3b8;padding:40px">Aucune formation</p>') + '</div>'

    return render_page(content, active='formations', page_title='Formations')


@app.route('/formations/nouvelle', methods=['GET', 'POST'])
@login_required
def formations_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO formations
                (code, nom, domaine, description, niveau, duree_heures, duree_mois,
                 cout_formation, prerequis, debouches, certification, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('domaine'),
                  request.form.get('description'),
                  request.form.get('niveau'),
                  int(request.form.get('duree_heures') or 0),
                  int(request.form.get('duree_mois') or 0),
                  float(request.form.get('cout_formation') or 0),
                  request.form.get('prerequis'),
                  request.form.get('debouches'),
                  request.form.get('certification'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Formation créée', 'success')
            return redirect('/formations')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>🎓 Nouvelle formation</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom de la formation *</label>'
    content += '<input type="text" name="nom" required autofocus placeholder="Maçonnerie moderne"></div>'
    content += '<div><label>Domaine *</label><select name="domaine" required>'
    content += '<option value="BTP">🏗️ BTP</option>'
    content += '<option value="Agro">🌾 Agro</option>'
    content += '<option value="Numérique">💻 Numérique</option>'
    content += '<option value="Commerce">💼 Commerce</option>'
    content += '<option value="Santé">🏥 Santé</option>'
    content += '<option value="Hôtellerie">🍽️ Hôtellerie</option>'
    content += '<option value="Industrie">⚙️ Industrie</option>'
    content += '<option value="Autre">📚 Autre</option>'
    content += '</select></div>'
    content += '<div><label>Niveau</label><select name="niveau">'
    content += '<option value="Débutant">Débutant</option>'
    content += '<option value="Intermédiaire">Intermédiaire</option>'
    content += '<option value="Avancé">Avancé</option>'
    content += '</select></div>'
    content += '<div><label>Durée (heures)</label><input type="number" name="duree_heures" value="120"></div>'
    content += '<div><label>Durée (mois)</label><input type="number" name="duree_mois" value="3"></div>'
    content += '<div><label>Coût formation (FCFA)</label><input type="number" step="1000" name="cout_formation" value="150000"></div>'
    content += '<div><label>Certification délivrée</label>'
    content += '<input type="text" name="certification" placeholder="Certificat professionnel, Attestation..."></div>'
    content += '<div style="grid-column:1/-1"><label>Description</label>'
    content += '<textarea name="description" rows="3"></textarea></div>'
    content += '<div><label>Prérequis</label><input type="text" name="prerequis" placeholder="Aucun, BEPC, Bac..."></div>'
    content += '<div><label>Débouchés</label><input type="text" name="debouches" placeholder="Maçon, Chef d\'équipe..."></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/formations" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='formations', page_title='Nouvelle formation')


@app.route('/formations/<int:fid>')
@login_required
def formations_detail(fid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM formations WHERE id=?", (fid,))
    f = cur.fetchone()
    if not f:
        flash('❌ Formation introuvable', 'error')
        return redirect('/formations')

    cur.execute("""
        SELECT s.*, c.nom AS centre_nom, ftr.nom_complet AS formateur_nom
        FROM sessions s
        LEFT JOIN centres c ON c.id=s.centre_id
        LEFT JOIN formateurs ftr ON ftr.id=s.formateur_id
        WHERE s.formation_id=?
        ORDER BY s.date_debut DESC
    """, (fid,))
    sessions = cur.fetchall()

    sess_html = ''
    for s in sessions:
        statut_badge = {'planifiee': 'badge-blue', 'en_cours': 'badge-orange', 'terminee': 'badge-green'}.get(s['statut'], 'badge-gray')
        sess_html += (
            '<tr><td><strong>' + str(s["code"]) + '</strong></td>'
            + '<td>' + str(s["centre_nom"] or "—") + '</td>'
            + '<td>' + str(s["formateur_nom"] or "—") + '</td>'
            + '<td>' + str((s["date_debut"] or "—")[:10]) + '</td>'
            + '<td>' + str((s["date_fin"] or "—")[:10]) + '</td>'
            + '<td style="text-align:center">' + str(s["nb_inscrits"]) + '/' + str(s["capacite"]) + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(s["statut"]) + '</span></td></tr>'
        )

    domain_icons = {'BTP': '🏗️', 'Agro': '🌾', 'Numérique': '💻', 'Commerce': '💼', 'Santé': '🏥', 'Hôtellerie': '🍽️'}
    icon = domain_icons.get(f['domaine'], '🎓')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">' + icon + ' ' + str(f["nom"]) + '</h1>'
    content += '<a href="/formations" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-label">Code</div><div class="kpi-value" style="font-size:16px">' + str(f["code"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-label">Durée</div><div class="kpi-value">' + str(f["duree_heures"]) + 'h</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Coût</div><div class="kpi-value" style="font-size:18px">' + f'{f["cout_formation"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-label">Sessions</div><div class="kpi-value">' + str(len(sessions)) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations formation</h2><table>'
    content += '<tr><td><strong>Domaine</strong></td><td>' + str(f["domaine"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Niveau</strong></td><td>' + str(f["niveau"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Durée</strong></td><td>' + str(f["duree_heures"]) + 'h sur ' + str(f["duree_mois"]) + ' mois</td></tr>'
    content += '<tr><td><strong>Prérequis</strong></td><td>' + str(f["prerequis"] or "Aucun") + '</td></tr>'
    content += '<tr><td><strong>Débouchés</strong></td><td>' + str(f["debouches"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Certification</strong></td><td>' + str(f["certification"] or "—") + '</td></tr>'
    content += '</table>'
    content += '<div style="margin-top:16px;padding:14px;background:#fff7ed;border-radius:8px">'
    content += '<div style="font-size:12.5px;color:#c2410c;font-weight:700;text-transform:uppercase;margin-bottom:6px">Description</div>'
    content += '<div style="font-size:13.5px;color:#475569;line-height:1.7">' + str(f["description"] or "Aucune description") + '</div>'
    content += '</div></div>'

    content += '<div class="card"><h2>📅 Sessions de cette formation (' + str(len(sessions)) + ')</h2>'
    content += '<table><thead><tr><th>Code</th><th>Centre</th><th>Formateur</th><th>Début</th><th>Fin</th><th style="text-align:center">Inscrits</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (sess_html or '<tr><td colspan="7" style="text-align:center;color:#94a3b8;padding:20px">Aucune session planifiée</td></tr>') + '</tbody></table>'
    content += '<div style="margin-top:14px;text-align:right"><a href="/sessions/nouvelle?formation_id=' + str(fid) + '" class="btn btn-primary">+ Planifier une session</a></div></div>'

    return render_page(content, active='formations', page_title='Formation')


@app.route('/formateurs')
@login_required
def formateurs_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT f.*,
               (SELECT COUNT(*) FROM sessions WHERE formateur_id=f.id) AS nb_sessions
        FROM formateurs f
        ORDER BY f.nom_complet
    """)
    formateurs = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM formateurs WHERE statut='disponible'")
    stats['dispo'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM formateurs")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(tarif_horaire),0) FROM formateurs")
    stats['tarif'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(annees_experience),0) FROM formateurs")
    stats['exp'] = cur.fetchone()[0]

    rows = ''
    for f in formateurs:
        statut_badge = 'badge-green' if f['statut'] == 'disponible' else 'badge-orange'
        rows += (
            '<tr><td><strong style="color:#ea580c">' + str(f["code"] or "—") + '</strong></td>'
            + '<td><strong>' + str(f["nom_complet"]) + '</strong></td>'
            + '<td>' + str(f["specialite"] or "—") + '<br><small style="color:#64748b">' + str(f["diplome"] or "") + '</small></td>'
            + '<td>' + str(f["telephone"] or "—") + '</td>'
            + '<td style="text-align:center">' + str(f["annees_experience"]) + ' ans</td>'
            + '<td style="text-align:right">' + f'{f["tarif_horaire"]:,.0f}' + ' F/h</td>'
            + '<td style="text-align:center">' + str(f["nb_sessions"]) + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(f["statut"]) + '</span></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👨‍🏫 Formateurs — ' + str(len(formateurs)) + '</h1>'
    content += '<a href="/formateurs/nouveau" class="btn btn-primary">+ Nouveau formateur</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-icon">👨‍🏫</div><div class="kpi-label">Total formateurs</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Disponibles</div><div class="kpi-value">' + str(stats["dispo"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-icon">📊</div><div class="kpi-label">Exp. moyenne</div><div class="kpi-value">' + f'{stats["exp"]:.0f}' + ' ans</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">💰</div><div class="kpi-label">Tarif moyen</div><div class="kpi-value" style="font-size:18px">' + f'{stats["tarif"]:,.0f}' + ' F/h</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Nom</th><th>Spécialité</th><th>Téléphone</th>'
    content += '<th style="text-align:center">Exp.</th><th style="text-align:right">Tarif</th>'
    content += '<th style="text-align:center">Sessions</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun formateur</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='formateurs', page_title='Formateurs')


@app.route('/formateurs/nouveau', methods=['GET', 'POST'])
@login_required
def formateurs_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO formateurs
                (code, nom_complet, telephone, email, specialite, diplome,
                 annees_experience, tarif_horaire, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?, 'disponible', ?)
            """, (None,
                  request.form.get('nom_complet'),
                  request.form.get('telephone'),
                  request.form.get('email'),
                  request.form.get('specialite'),
                  request.form.get('diplome'),
                  int(request.form.get('annees_experience') or 0),
                  float(request.form.get('tarif_horaire') or 0),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Formateur créé', 'success')
            return redirect('/formateurs')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>👨‍🏫 Nouveau formateur</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom complet *</label>'
    content += '<input type="text" name="nom_complet" required autofocus></div>'
    content += '<div><label>Téléphone</label><input type="text" name="telephone"></div>'
    content += '<div><label>Email</label><input type="email" name="email"></div>'
    content += '<div><label>Spécialité</label><input type="text" name="specialite" placeholder="BTP, Numérique, Agro..."></div>'
    content += '<div><label>Diplôme</label><input type="text" name="diplome"></div>'
    content += '<div><label>Années d\'expérience</label><input type="number" name="annees_experience" value="5"></div>'
    content += '<div><label>Tarif horaire (FCFA)</label><input type="number" step="500" name="tarif_horaire" value="15000"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/formateurs" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='formateurs', page_title='Nouveau formateur')


@app.route('/centres')
@login_required
def centres_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*,
               (SELECT COUNT(*) FROM salles WHERE centre_id=c.id) AS nb_salles,
               (SELECT COUNT(*) FROM sessions WHERE centre_id=c.id) AS nb_sessions
        FROM centres c
        ORDER BY c.nom
    """)
    centres = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM centres WHERE statut='actif'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM centres WHERE type='public'")
    stats['public'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM centres WHERE type='prive'")
    stats['prive'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(capacite_totale),0) FROM centres")
    stats['capacite'] = cur.fetchone()[0]

    cards = ''
    for c in centres:
        type_icon = '🏛️' if c['type'] == 'public' else '🏢'
        cards += '<div class="form-card">'
        cards += '<div class="form-icon">' + type_icon + '</div>'
        cards += '<div class="form-body">'
        cards += '<div style="font-weight:800;color:#1e293b;font-size:14px;margin-bottom:4px">' + str(c["nom"]) + '</div>'
        cards += '<div style="font-size:11.5px;color:#64748b;margin-bottom:8px">📍 ' + str(c["ville"] or "") + ' · ' + str(c["region"] or "") + '</div>'
        cards += '<div style="font-size:12px;color:#475569;margin-bottom:10px">📞 ' + str(c["telephone"] or "—") + '</div>'
        cards += '<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:10px">'
        cards += '<span style="color:#64748b">🚪 ' + str(c["nb_salles"]) + ' salles</span>'
        cards += '<span style="color:#64748b">👥 ' + str(c["capacite_totale"]) + ' places</span>'
        cards += '</div>'
        cards += '<a href="/centres/' + str(c["id"]) + '" class="btn btn-primary" style="padding:6px 10px;font-size:11.5px;width:100%;text-align:center;display:block">👁 Voir détails</a>'
        cards += '</div></div>'

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🏫 Centres de formation — ' + str(len(centres)) + '</h1>'
    content += '<a href="/centres/nouveau" class="btn btn-primary">+ Nouveau centre</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-icon">🏫</div><div class="kpi-label">Centres actifs</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-icon">🏛️</div><div class="kpi-label">Publics</div><div class="kpi-value">' + str(stats["public"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🏢</div><div class="kpi-label">Privés</div><div class="kpi-value">' + str(stats["prive"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">👥</div><div class="kpi-label">Capacité totale</div><div class="kpi-value">' + str(stats["capacite"]) + '</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px">' + (cards or '<p style="grid-column:1/-1;text-align:center;color:#94a3b8;padding:40px">Aucun centre</p>') + '</div>'

    return render_page(content, active='centres', page_title='Centres')


@app.route('/centres/nouveau', methods=['GET', 'POST'])
@login_required
def centres_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO centres
                (code, nom, type, adresse, ville, region, telephone, email,
                 responsable, num_agrement, capacite_totale, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('type') or 'public',
                  request.form.get('adresse'),
                  request.form.get('ville'),
                  request.form.get('region'),
                  request.form.get('telephone'),
                  request.form.get('email'),
                  request.form.get('responsable'),
                  request.form.get('num_agrement'),
                  int(request.form.get('capacite_totale') or 0),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Centre créé', 'success')
            return redirect('/centres')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>🏫 Nouveau centre</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom du centre *</label><input type="text" name="nom" required autofocus></div>'
    content += '<div><label>Type</label><select name="type">'
    content += '<option value="public">🏛️ Public</option>'
    content += '<option value="prive">🏢 Privé</option>'
    content += '</select></div>'
    content += '<div><label>Numéro d\'agrément</label><input type="text" name="num_agrement"></div>'
    content += '<div style="grid-column:1/-1"><label>Adresse</label><input type="text" name="adresse"></div>'
    content += '<div><label>Ville</label><input type="text" name="ville" value="Dakar"></div>'
    content += '<div><label>Région</label><input type="text" name="region" value="Dakar"></div>'
    content += '<div><label>Téléphone</label><input type="text" name="telephone"></div>'
    content += '<div><label>Email</label><input type="email" name="email"></div>'
    content += '<div><label>Responsable</label><input type="text" name="responsable"></div>'
    content += '<div><label>Capacité totale</label><input type="number" name="capacite_totale" value="200"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/centres" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='centres', page_title='Nouveau centre')


@app.route('/centres/<int:cid>')
@login_required
def centres_detail(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM centres WHERE id=?", (cid,))
    c = cur.fetchone()
    if not c:
        flash('❌ Centre introuvable', 'error')
        return redirect('/centres')

    cur.execute("SELECT * FROM salles WHERE centre_id=? ORDER BY nom", (cid,))
    salles = cur.fetchall()
    salles_html = ''
    for s in salles:
        salles_html += (
            '<tr><td><strong>' + str(s["nom"]) + '</strong></td>'
            + '<td style="text-align:center">' + str(s["capacite"]) + '</td>'
            + '<td>' + str(s["equipements"] or "—") + '</td>'
            + '<td>' + str(s["etage"] or "—") + '</td></tr>'
        )

    cur.execute("""
        SELECT s.*, f.nom AS formation_nom, ftr.nom_complet AS formateur_nom
        FROM sessions s
        LEFT JOIN formations f ON f.id=s.formation_id
        LEFT JOIN formateurs ftr ON ftr.id=s.formateur_id
        WHERE s.centre_id=?
        ORDER BY s.date_debut DESC LIMIT 20
    """, (cid,))
    sessions = cur.fetchall()
    sess_html = ''
    for s in sessions:
        statut_badge = {'planifiee': 'badge-blue', 'en_cours': 'badge-orange', 'terminee': 'badge-green'}.get(s['statut'], 'badge-gray')
        sess_html += (
            '<tr><td><strong>' + str(s["code"]) + '</strong></td>'
            + '<td>' + str(s["formation_nom"] or "—") + '</td>'
            + '<td>' + str(s["formateur_nom"] or "—") + '</td>'
            + '<td>' + str((s["date_debut"] or "—")[:10]) + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(s["statut"]) + '</span></td></tr>'
        )

    type_icon = '🏛️' if c['type'] == 'public' else '🏢'

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">' + type_icon + ' ' + str(c["nom"]) + '</h1>'
    content += '<a href="/centres" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-label">Code</div><div class="kpi-value" style="font-size:16px">' + str(c["code"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-label">Type</div><div class="kpi-value" style="font-size:16px">' + str(c["type"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Salles</div><div class="kpi-value">' + str(len(salles)) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-label">Capacité</div><div class="kpi-value">' + str(c["capacite_totale"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations</h2><table>'
    content += '<tr><td><strong>Adresse</strong></td><td>' + str(c["adresse"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Ville / Région</strong></td><td>' + str(c["ville"] or "—") + ' / ' + str(c["region"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Téléphone</strong></td><td>' + str(c["telephone"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Email</strong></td><td>' + str(c["email"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Responsable</strong></td><td>' + str(c["responsable"] or "—") + '</td></tr>'
    content += '<tr><td><strong>N° agrément</strong></td><td>' + str(c["num_agrement"] or "—") + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>🚪 Salles (' + str(len(salles)) + ')</h2>'
    content += '<table><thead><tr><th>Nom</th><th style="text-align:center">Capacité</th><th>Équipements</th><th>Étage</th></tr></thead>'
    content += '<tbody>' + (salles_html or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucune salle</td></tr>') + '</tbody></table>'
    content += '<div style="margin-top:14px;text-align:right"><a href="/centres/' + str(cid) + '/salles/nouvelle" class="btn btn-primary">+ Ajouter une salle</a></div></div>'

    content += '<div class="card"><h2>📅 Sessions (' + str(len(sessions)) + ')</h2>'
    content += '<table><thead><tr><th>Code</th><th>Formation</th><th>Formateur</th><th>Début</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (sess_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucune session</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='centres', page_title='Centre')


@app.route('/centres/<int:cid>/salles/nouvelle', methods=['GET', 'POST'])
@login_required
def salles_nouvelle(cid):
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO salles (centre_id, nom, capacite, equipements, etage, disponible, created_at)
                VALUES (?,?,?,?,?,1,?)
            """, (cid,
                  request.form.get('nom'),
                  int(request.form.get('capacite') or 20),
                  request.form.get('equipements'),
                  request.form.get('etage'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Salle ajoutée', 'success')
            return redirect('/centres/' + str(cid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>🚪 Nouvelle salle</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="margin-bottom:16px"><label>Nom de la salle *</label>'
    content += '<input type="text" name="nom" required autofocus></div>'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Capacité</label><input type="number" name="capacite" value="20"></div>'
    content += '<div><label>Étage</label><input type="text" name="etage"></div>'
    content += '</div>'
    content += '<div style="margin-top:16px"><label>Équipements</label>'
    content += '<textarea name="equipements" rows="3"></textarea></div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/centres/' + str(cid) + '" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='centres', page_title='Nouvelle salle')


@app.route('/sessions')
@login_required
def sessions_liste():
    db = get_db()
    cur = db.cursor()
    statut_f = request.args.get('statut', '')

    sql = """
        SELECT s.*, f.nom AS formation_nom, f.domaine,
               c.nom AS centre_nom, ftr.nom_complet AS formateur_nom
        FROM sessions s
        LEFT JOIN formations f ON f.id=s.formation_id
        LEFT JOIN centres c ON c.id=s.centre_id
        LEFT JOIN formateurs ftr ON ftr.id=s.formateur_id
        WHERE 1=1
    """
    params = []
    if statut_f:
        sql += " AND s.statut=?"
        params.append(statut_f)
    sql += " ORDER BY s.date_debut DESC LIMIT 200"
    cur.execute(sql, params)
    sessions = cur.fetchall()

    stats = {}
    for k, s in [
        ('total', "SELECT COUNT(*) FROM sessions"),
        ('planifiee', "SELECT COUNT(*) FROM sessions WHERE statut='planifiee'"),
        ('en_cours', "SELECT COUNT(*) FROM sessions WHERE statut='en_cours'"),
        ('terminee', "SELECT COUNT(*) FROM sessions WHERE statut='terminee'"),
    ]:
        cur.execute(s)
        stats[k] = cur.fetchone()[0]

    rows = ''
    for s in sessions:
        statut_badge = {
            'planifiee': 'badge-blue',
            'en_cours': 'badge-orange',
            'terminee': 'badge-green',
            'annulee': 'badge-red',
        }.get(s['statut'], 'badge-gray')
        remplissage = (s['nb_inscrits'] / s['capacite'] * 100) if s['capacite'] > 0 else 0
        rows += (
            '<tr><td><strong style="color:#ea580c">' + str(s["code"]) + '</strong></td>'
            + '<td><strong>' + str(s["formation_nom"] or "—") + '</strong><br><small style="color:#64748b">' + str(s["domaine"] or "") + '</small></td>'
            + '<td>' + str(s["centre_nom"] or "—") + '</td>'
            + '<td>' + str(s["formateur_nom"] or "—") + '</td>'
            + '<td>' + str((s["date_debut"] or "—")[:10]) + '<br><small style="color:#64748b">→ ' + str((s["date_fin"] or "—")[:10]) + '</small></td>'
            + '<td style="text-align:center">' + str(s["nb_inscrits"]) + '/' + str(s["capacite"]) + '<br><small style="color:#64748b">' + f'{remplissage:.0f}' + '%</small></td>'
            + '<td>' + str(s["financement"] or "—") + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(s["statut"]) + '</span></td>'
            + '<td><a href="/sessions/' + str(s["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📅 Sessions — ' + str(len(sessions)) + '</h1>'
    content += '<a href="/sessions/nouvelle" class="btn btn-primary">+ Nouvelle session</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-icon">📅</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">📋</div><div class="kpi-label">Planifiées</div><div class="kpi-value">' + str(stats["planifiee"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">🔴</div><div class="kpi-label">En cours</div><div class="kpi-value">' + str(stats["en_cours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Terminées</div><div class="kpi-value">' + str(stats["terminee"]) + '</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/sessions" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Toutes</a> '
    for s in ['planifiee', 'en_cours', 'terminee']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/sessions?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Formation</th><th>Centre</th><th>Formateur</th>'
    content += '<th>Dates</th><th style="text-align:center">Inscrits</th><th>Financement</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="9" style="padding:40px;text-align:center;color:#94a3b8">Aucune session</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='sessions', page_title='Sessions')


@app.route('/sessions/nouvelle', methods=['GET', 'POST'])
@login_required
def sessions_nouvelle():
    db = get_db()
    cur = db.cursor()
    formation_id_pre = int(request.args.get('formation_id') or 0)

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO sessions
                (code, formation_id, centre_id, salle_id, formateur_id, date_debut, date_fin,
                 horaire, capacite, nb_inscrits, financement, cout_total, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,0,?,?,?,?)
            """, (None,
                  int(request.form.get('formation_id') or 0),
                  int(request.form.get('centre_id') or 0) or None,
                  int(request.form.get('salle_id') or 0) or None,
                  int(request.form.get('formateur_id') or 0) or None,
                  request.form.get('date_debut'),
                  request.form.get('date_fin'),
                  request.form.get('horaire'),
                  int(request.form.get('capacite') or 20),
                  request.form.get('financement') or 'autofinance',
                  float(request.form.get('cout_total') or 0),
                  request.form.get('statut') or 'planifiee',
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Session créée', 'success')
            return redirect('/sessions')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom, domaine FROM formations WHERE statut='actif' ORDER BY nom")
    formations = cur.fetchall()
    cur.execute("SELECT id, nom FROM centres ORDER BY nom")
    centres = cur.fetchall()
    cur.execute("SELECT id, nom_complet, specialite FROM formateurs WHERE statut='disponible' ORDER BY nom_complet")
    formateurs = cur.fetchall()

    opts_f = ''.join('<option value="' + str(f["id"]) + '"' + (' selected' if f["id"] == formation_id_pre else '') + '>' + str(f["nom"]) + ' (' + str(f["domaine"] or "") + ')</option>' for f in formations)
    opts_c = ''.join('<option value="' + str(c["id"]) + '">' + str(c["nom"]) + '</option>' for c in centres)
    opts_ftr = ''.join('<option value="' + str(f["id"]) + '">' + str(f["nom_complet"]) + ' — ' + str(f["specialite"] or "") + '</option>' for f in formateurs)

    content = '<h1>📅 Nouvelle session</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Formation *</label><select name="formation_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_f + '</select></div>'
    content += '<div><label>Centre</label><select name="centre_id"><option value="">— Aucun —</option>' + opts_c + '</select></div>'
    content += '<div><label>Formateur</label><select name="formateur_id"><option value="">— Aucun —</option>' + opts_ftr + '</select></div>'
    content += '<div><label>Date début *</label><input type="date" name="date_debut" required value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Date fin</label><input type="date" name="date_fin" value="' + (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Horaire</label><select name="horaire">'
    content += '<option value="8h-12h">8h-12h</option>'
    content += '<option value="14h-18h">14h-18h</option>'
    content += '<option value="8h-17h">8h-17h</option>'
    content += '</select></div>'
    content += '<div><label>Capacité</label><input type="number" name="capacite" value="20"></div>'
    content += '<div><label>Financement</label><select name="financement">'
    content += '<option value="3FPT">🏛️ 3FPT</option>'
    content += '<option value="autofinance">💰 Autofinancement</option>'
    content += '<option value="entreprise">🏢 Entreprise</option>'
    content += '<option value="cooperation">🤝 Coopération</option>'
    content += '</select></div>'
    content += '<div><label>Coût total (FCFA)</label><input type="number" step="1000" name="cout_total" value="500000"></div>'
    content += '<div><label>Statut</label><select name="statut">'
    content += '<option value="planifiee">📋 Planifiée</option>'
    content += '<option value="en_cours">🔴 En cours</option>'
    content += '</select></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer la session</button>'
    content += '<a href="/sessions" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='sessions', page_title='Nouvelle session')


@app.route('/sessions/<int:sid>')
@login_required
def sessions_detail(sid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.*, f.nom AS formation_nom, f.domaine, f.duree_heures,
               c.nom AS centre_nom, c.ville AS centre_ville,
               ftr.nom_complet AS formateur_nom, ftr.telephone AS formateur_tel,
               sa.nom AS salle_nom
        FROM sessions s
        LEFT JOIN formations f ON f.id=s.formation_id
        LEFT JOIN centres c ON c.id=s.centre_id
        LEFT JOIN formateurs ftr ON ftr.id=s.formateur_id
        LEFT JOIN salles sa ON sa.id=s.salle_id
        WHERE s.id=?
    """, (sid,))
    s = cur.fetchone()
    if not s:
        flash('❌ Session introuvable', 'error')
        return redirect('/sessions')

    cur.execute("""
        SELECT i.*, a.nom, a.prenom, a.numero_apprenant, a.telephone
        FROM inscriptions i
        LEFT JOIN apprenants a ON a.id=i.apprenant_id
        WHERE i.session_id=?
        ORDER BY a.nom
    """, (sid,))
    inscriptions = cur.fetchall()

    ins_html = ''
    for i in inscriptions:
        ins_html += (
            '<tr><td><strong>' + str(i["numero_apprenant"] or "—") + '</strong></td>'
            + '<td>' + str(i["prenom"] or "") + ' ' + str(i["nom"] or "") + '</td>'
            + '<td>' + str(i["telephone"] or "—") + '</td>'
            + '<td>' + str((i["date_inscription"] or "")[:10]) + '</td>'
            + '<td>' + str(i["financement"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{i["frais_payes"]:,.0f}' + ' F</td></tr>'
        )

    statut_badge = {'planifiee': 'badge-blue', 'en_cours': 'badge-orange', 'terminee': 'badge-green'}.get(s['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📅 Session ' + str(s["code"]) + ' <span class="badge ' + statut_badge + '">' + str(s["statut"]) + '</span></h1>'
    content += '<div>'
    content += '<a href="/sessions/' + str(sid) + '/presences" class="btn btn-blue">📋 Présences</a> '
    content += '<a href="/sessions/' + str(sid) + '/inscription" class="btn btn-success">+ Inscrire</a> '
    content += '<a href="/sessions" class="btn btn-secondary">← Retour</a></div></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-label">Formation</div><div class="kpi-value" style="font-size:14px">' + str(s["formation_nom"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-label">Centre</div><div class="kpi-value" style="font-size:16px">' + str(s["centre_nom"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Inscrits</div><div class="kpi-value">' + str(len(inscriptions)) + '/' + str(s["capacite"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-label">Financement</div><div class="kpi-value" style="font-size:16px">' + str(s["financement"] or "—") + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations</h2><table>'
    content += '<tr><td><strong>Formateur</strong></td><td>' + str(s["formateur_nom"] or "—") + ' · ' + str(s["formateur_tel"] or "") + '</td></tr>'
    content += '<tr><td><strong>Salle</strong></td><td>' + str(s["salle_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Horaire</strong></td><td>' + str(s["horaire"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Dates</strong></td><td>' + str((s["date_debut"] or "—")[:10]) + ' → ' + str((s["date_fin"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Durée formation</strong></td><td>' + str(s["duree_heures"]) + 'h</td></tr>'
    content += '<tr><td><strong>Coût total</strong></td><td>' + f'{s["cout_total"]:,.0f}' + ' FCFA</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>👥 Apprenants inscrits (' + str(len(inscriptions)) + ')</h2>'
    content += '<table><thead><tr><th>N° Apprenant</th><th>Nom</th><th>Téléphone</th><th>Inscription</th><th>Financement</th><th style="text-align:right">Frais payés</th></tr></thead>'
    content += '<tbody>' + (ins_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:20px">Aucun apprenant inscrit</td></tr>') + '</tbody></table>'
    content += '<div style="margin-top:14px;text-align:right"><a href="/sessions/' + str(sid) + '/inscription" class="btn btn-primary">+ Inscrire un apprenant</a></div></div>'

    return render_page(content, active='sessions', page_title='Session')



# ═══════════════════════════════════════════════════════════════
# 👥 APPRENANTS
# ═══════════════════════════════════════════════════════════════

@app.route('/apprenants')
@login_required
def apprenants_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()
    region_f = request.args.get('region', '')

    sql = """
        SELECT a.*,
               (SELECT COUNT(*) FROM inscriptions WHERE apprenant_id=a.id) AS nb_formations,
               (SELECT COUNT(*) FROM certificats WHERE apprenant_id=a.id) AS nb_certificats
        FROM apprenants a
        WHERE 1=1
    """
    params = []
    if q:
        sql += " AND (a.nom LIKE ? OR a.prenom LIKE ? OR a.numero_apprenant LIKE ? OR a.telephone LIKE ?)"
        params += [f'%{q}%'] * 4
    if region_f:
        sql += " AND a.region=?"
        params.append(region_f)
    sql += " ORDER BY a.id DESC LIMIT 300"
    cur.execute(sql, params)
    apprenants = cur.fetchall()

    cur.execute("SELECT DISTINCT region FROM apprenants WHERE region IS NOT NULL ORDER BY region")
    regions = [r[0] for r in cur.fetchall()]

    stats = {}
    cur.execute("SELECT COUNT(*) FROM apprenants WHERE statut='actif'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM apprenants WHERE sexe='F'")
    stats['filles'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM apprenants WHERE sexe='M'")
    stats['garcons'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM apprenants WHERE situation='Sans emploi'")
    stats['sans_emploi'] = cur.fetchone()[0]

    rows = ''
    for a in apprenants:
        sexe_icon = '👨' if a['sexe'] == 'M' else '👩' if a['sexe'] == 'F' else '👤'
        age = 0
        if a['date_naissance']:
            try:
                dn = datetime.strptime(a['date_naissance'][:10], '%Y-%m-%d')
                age = (datetime.now() - dn).days // 365
            except Exception:
                age = 0
        rows += (
            '<tr><td><strong style="color:#ea580c">' + str(a["numero_apprenant"] or "—") + '</strong></td>'
            + '<td>' + sexe_icon + ' <strong>' + str(a["prenom"] or "") + ' ' + str(a["nom"] or "") + '</strong><br><small style="color:#64748b">' + str(age) + ' ans · ' + str(a["niveau_etudes"] or "") + '</small></td>'
            + '<td>' + str(a["telephone"] or "—") + '</td>'
            + '<td>' + str(a["ville"] or "—") + '<br><small style="color:#64748b">' + str(a["region"] or "") + '</small></td>'
            + '<td>' + str(a["situation"] or "—") + '</td>'
            + '<td style="text-align:center">' + str(a["nb_formations"]) + '</td>'
            + '<td style="text-align:center;font-weight:800;color:#10b981">' + str(a["nb_certificats"]) + '</td>'
            + '<td><a href="/apprenants/' + str(a["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👥 Apprenants — ' + str(len(apprenants)) + '</h1>'
    content += '<a href="/apprenants/nouveau" class="btn btn-primary">+ Nouvel apprenant</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-icon">👥</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div class="kpi-icon">👩</div><div class="kpi-label">Filles</div><div class="kpi-value">' + str(stats["filles"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-icon">👨</div><div class="kpi-label">Garçons</div><div class="kpi-value">' + str(stats["garcons"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">🎯</div><div class="kpi-label">Sans emploi</div><div class="kpi-value">' + str(stats["sans_emploi"]) + '</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher nom, prénom, n° apprenant..." style="max-width:500px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/apprenants" class="btn ' + ('btn-primary' if not region_f else 'btn-secondary') + '">Toutes régions</a> '
    for r in regions[:8]:
        active_cls = 'btn-primary' if region_f == r else 'btn-secondary'
        content += '<a href="/apprenants?region=' + r + '" class="btn ' + active_cls + '" style="margin-left:6px">' + r + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N°</th><th>Nom</th><th>Téléphone</th><th>Localisation</th>'
    content += '<th>Situation</th><th style="text-align:center">Formations</th><th style="text-align:center">Certificats</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun apprenant</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='apprenants', page_title='Apprenants')


@app.route('/apprenants/nouveau', methods=['GET', 'POST'])
@login_required
def apprenants_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO apprenants
                (numero_apprenant, nom, prenom, date_naissance, sexe, telephone, email,
                 adresse, ville, region, niveau_etudes, situation, statut, date_inscription, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'actif', ?, ?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('prenom'),
                  request.form.get('date_naissance'),
                  request.form.get('sexe'),
                  request.form.get('telephone'),
                  request.form.get('email'),
                  request.form.get('adresse'),
                  request.form.get('ville'),
                  request.form.get('region'),
                  request.form.get('niveau_etudes'),
                  request.form.get('situation'),
                  datetime.now().strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Apprenant créé', 'success')
            return redirect('/apprenants')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>👥 Nouvel apprenant</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Nom *</label><input type="text" name="nom" required autofocus></div>'
    content += '<div><label>Prénom *</label><input type="text" name="prenom" required></div>'
    content += '<div><label>Date de naissance</label><input type="date" name="date_naissance"></div>'
    content += '<div><label>Sexe</label><select name="sexe">'
    content += '<option value="M">Masculin</option>'
    content += '<option value="F">Féminin</option>'
    content += '</select></div>'
    content += '<div><label>Téléphone *</label><input type="text" name="telephone" required placeholder="+221 77 XXX XX XX"></div>'
    content += '<div><label>Email</label><input type="email" name="email"></div>'
    content += '<div style="grid-column:1/-1"><label>Adresse</label><input type="text" name="adresse"></div>'
    content += '<div><label>Ville</label><input type="text" name="ville" value="Dakar"></div>'
    content += '<div><label>Région</label><input type="text" name="region" value="Dakar"></div>'
    content += '<div><label>Niveau d\'études</label><select name="niveau_etudes">'
    content += '<option value="Aucun">Aucun</option>'
    content += '<option value="Primaire">Primaire</option>'
    content += '<option value="BEPC">BEPC</option>'
    content += '<option value="BAC">BAC</option>'
    content += '<option value="BAC+2">BAC+2</option>'
    content += '<option value="Licence">Licence</option>'
    content += '</select></div>'
    content += '<div><label>Situation actuelle</label><select name="situation">'
    content += '<option value="Sans emploi">Sans emploi</option>'
    content += '<option value="Étudiant">Étudiant</option>'
    content += '<option value="Employé">Employé</option>'
    content += '<option value="Sous-employé">Sous-employé</option>'
    content += '<option value="Apprenti">Apprenti</option>'
    content += '</select></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/apprenants" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='apprenants', page_title='Nouvel apprenant')


@app.route('/apprenants/<int:aid>')
@login_required
def apprenants_detail(aid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM apprenants WHERE id=?", (aid,))
    a = cur.fetchone()
    if not a:
        flash('❌ Apprenant introuvable', 'error')
        return redirect('/apprenants')

    cur.execute("""
        SELECT i.*, s.code AS session_code, s.date_debut, s.date_fin, s.statut AS session_statut,
               f.nom AS formation_nom, f.domaine
        FROM inscriptions i
        LEFT JOIN sessions s ON s.id=i.session_id
        LEFT JOIN formations f ON f.id=s.formation_id
        WHERE i.apprenant_id=?
        ORDER BY i.id DESC
    """, (aid,))
    inscriptions = cur.fetchall()

    ins_html = ''
    for i in inscriptions:
        statut_badge = {'inscrit': 'badge-blue', 'en_cours': 'badge-orange', 'termine': 'badge-green', 'abandon': 'badge-red'}.get(i['statut'], 'badge-gray')
        ins_html += (
            '<tr><td><strong>' + str(i["session_code"] or "—") + '</strong></td>'
            + '<td>' + str(i["formation_nom"] or "—") + '<br><small style="color:#64748b">' + str(i["domaine"] or "") + '</small></td>'
            + '<td>' + str((i["date_debut"] or "—")[:10]) + '</td>'
            + '<td>' + str(i["financement"] or "—") + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(i["statut"]) + '</span></td></tr>'
        )

    cur.execute("""
        SELECT c.*, f.nom AS formation_nom
        FROM certificats c
        LEFT JOIN formations f ON f.id=c.formation_id
        WHERE c.apprenant_id=?
        ORDER BY c.id DESC
    """, (aid,))
    certificats = cur.fetchall()
    cert_html = ''
    for c in certificats:
        cert_html += (
            '<tr><td><strong style="color:#ea580c">' + str(c["numero_certificat"]) + '</strong></td>'
            + '<td>' + str(c["formation_nom"] or "—") + '</td>'
            + '<td style="text-align:center">' + f'{c["note_finale"]:.1f}' + '/20</td>'
            + '<td><span class="badge badge-green">' + str(c["mention"] or "") + '</span></td>'
            + '<td>' + str((c["date_emission"] or "—")[:10]) + '</td></tr>'
        )

    sexe_icon = '👨' if a['sexe'] == 'M' else '👩' if a['sexe'] == 'F' else '👤'
    age = 0
    if a['date_naissance']:
        try:
            dn = datetime.strptime(a['date_naissance'][:10], '%Y-%m-%d')
            age = (datetime.now() - dn).days // 365
        except Exception:
            age = 0

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">' + sexe_icon + ' ' + str(a["prenom"] or "") + ' ' + str(a["nom"] or "") + '</h1>'
    content += '<div><a href="/apprenants/' + str(aid) + '/carte" class="btn btn-danger">🎫 Carte</a> '
    content += '<a href="/apprenants" class="btn btn-secondary" style="margin-left:6px">← Retour</a></div></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-label">N° Apprenant</div><div class="kpi-value" style="font-size:16px">' + str(a["numero_apprenant"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-label">Âge</div><div class="kpi-value">' + str(age) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Formations</div><div class="kpi-value">' + str(len(inscriptions)) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-label">Certificats</div><div class="kpi-value">' + str(len(certificats)) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations personnelles</h2><table>'
    content += '<tr><td><strong>Sexe</strong></td><td>' + ('Masculin' if a["sexe"] == 'M' else 'Féminin') + '</td></tr>'
    content += '<tr><td><strong>Date de naissance</strong></td><td>' + str((a["date_naissance"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Téléphone</strong></td><td>' + str(a["telephone"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Email</strong></td><td>' + str(a["email"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Adresse</strong></td><td>' + str(a["adresse"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Ville / Région</strong></td><td>' + str(a["ville"] or "—") + ' / ' + str(a["region"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Niveau d\'études</strong></td><td>' + str(a["niveau_etudes"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Situation</strong></td><td>' + str(a["situation"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Inscrit le</strong></td><td>' + str((a["date_inscription"] or "—")[:10]) + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>🎓 Formations suivies (' + str(len(inscriptions)) + ')</h2>'
    content += '<table><thead><tr><th>Session</th><th>Formation</th><th>Début</th><th>Financement</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (ins_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucune inscription</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>📜 Certificats obtenus (' + str(len(certificats)) + ')</h2>'
    content += '<table><thead><tr><th>N°</th><th>Formation</th><th style="text-align:center">Note</th><th>Mention</th><th>Émis le</th></tr></thead>'
    content += '<tbody>' + (cert_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucun certificat</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='apprenants', page_title='Apprenant')


@app.route('/apprenants/<int:aid>/carte')
@login_required
def apprenants_carte(aid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM apprenants WHERE id=?", (aid,))
    a = cur.fetchone()
    if not a:
        flash('❌ Apprenant introuvable', 'error')
        return redirect('/apprenants')

    qr_url = '/apprenants/' + str(aid) + '/qr.png'

    content = '''
    <div style="max-width:480px;margin:0 auto">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
        <a href="/apprenants/''' + str(aid) + '''" class="btn btn-secondary">← Retour</a>
        <a href="/apprenants/''' + str(aid) + '''/carte.pdf" class="btn btn-primary">📄 Imprimer</a>
      </div>

      <div style="background:linear-gradient(135deg,#ea580c,#c2410c);color:#fff;border-radius:16px;padding:22px;box-shadow:0 10px 30px rgba(0,0,0,.15)">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:18px">
          <div>
            <div style="font-size:11px;opacity:.85;letter-spacing:2px;font-weight:600">OMEGA FORMATION</div>
            <div style="font-size:16px;font-weight:900">CARTE APPRENANT</div>
          </div>
          <div style="background:#2563eb;width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:22px">🎓</div>
        </div>

        <div style="background:rgba(255,255,255,.95);color:#1e293b;border-radius:12px;padding:16px">
          <div style="display:grid;grid-template-columns:1fr auto;gap:14px">
            <div>
              <div style="font-size:10px;color:#64748b;font-weight:700">N° APPRENANT</div>
              <div style="font-size:16px;font-weight:900;color:#ea580c;margin-bottom:12px">''' + str(a['numero_apprenant'] or '—') + '''</div>
              <div style="font-size:10px;color:#64748b;font-weight:700">NOM COMPLET</div>
              <div style="font-size:15px;font-weight:800;margin-bottom:12px">''' + str(a['prenom'] or '') + ' ' + str(a['nom'] or '') + '''</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:12px">
                <div><div style="font-size:9.5px;color:#64748b;font-weight:700">NAISSANCE</div><div style="font-weight:700">''' + str((a['date_naissance'] or '—')[:10]) + '''</div></div>
                <div><div style="font-size:9.5px;color:#64748b;font-weight:700">TÉLÉPHONE</div><div style="font-weight:700">''' + str(a['telephone'] or '—') + '''</div></div>
                <div><div style="font-size:9.5px;color:#64748b;font-weight:700">NIVEAU</div><div style="font-weight:700">''' + str(a['niveau_etudes'] or '—') + '''</div></div>
                <div><div style="font-size:9.5px;color:#64748b;font-weight:700">VILLE</div><div style="font-weight:700">''' + str(a['ville'] or '—') + '''</div></div>
              </div>
            </div>
            <div style="text-align:center">
              <img src="''' + qr_url + '''" alt="QR" style="width:110px;height:110px;border:3px solid #ea580c;border-radius:10px">
              <div style="font-size:9.5px;color:#64748b;margin-top:6px;font-weight:700">SCANNER</div>
            </div>
          </div>
        </div>

        <div style="text-align:center;margin-top:14px;font-size:10.5px;opacity:.85;letter-spacing:1px">
          3FPT · FORMATION PROFESSIONNELLE · SÉNÉGAL
        </div>
      </div>
    </div>
    '''
    return render_page(content, active='apprenants', page_title='Carte apprenant')


@app.route('/apprenants/<int:aid>/qr.png')
def apprenants_qr(aid):
    import qrcode
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT numero_apprenant, telephone FROM apprenants WHERE id=?", (aid,))
    a = cur.fetchone()
    if not a:
        return redirect('/')
    qr_data = 'FORM|APP|' + str(aid) + '|' + (a['numero_apprenant'] or '') + '|' + (a['telephone'] or '')
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#c2410c', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


@app.route('/apprenants/<int:aid>/carte.pdf')
@login_required
def apprenants_carte_pdf(aid):
    from reportlab.lib.pagesizes import A6
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    import qrcode

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM apprenants WHERE id=?", (aid,))
    a = cur.fetchone()
    if not a:
        flash('❌ Apprenant introuvable', 'error')
        return redirect('/apprenants')

    qr = qrcode.make('FORM|APP|' + str(aid) + '|' + (a['numero_apprenant'] or ''))
    qr_buf = io.BytesIO()
    qr.save(qr_buf, format='PNG')
    qr_buf.seek(0)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A6)
    w, h = A6

    c.setFillColor(colors.HexColor('#ea580c'))
    c.rect(0, 0, w, h, fill=1, stroke=0)

    c.setFillColor(colors.HexColor('#2563eb'))
    c.rect(0, h - 25*mm, w, 25*mm, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(8*mm, h - 10*mm, 'OMEGA FORMATION')
    c.setFont('Helvetica', 7)
    c.drawString(8*mm, h - 15*mm, 'CARTE APPRENANT')
    c.setFont('Helvetica-Bold', 18)
    c.drawRightString(w - 8*mm, h - 12*mm, '🎓')

    card_y = 30*mm
    card_h = h - 25*mm - card_y - 8*mm
    c.setFillColor(colors.white)
    c.roundRect(6*mm, card_y, w - 12*mm, card_h, 3*mm, fill=1, stroke=0)

    y = card_y + card_h - 6*mm
    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica-Bold', 6)
    c.drawString(8*mm, y, 'N° APPRENANT')
    y -= 4*mm
    c.setFillColor(colors.HexColor('#ea580c'))
    c.setFont('Helvetica-Bold', 11)
    c.drawString(8*mm, y, str(a['numero_apprenant'] or '—'))

    y -= 7*mm
    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica-Bold', 6)
    c.drawString(8*mm, y, 'NOM COMPLET')
    y -= 4*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(8*mm, y, (a['prenom'] or '') + ' ' + (a['nom'] or ''))

    y -= 7*mm
    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica-Bold', 6)
    c.drawString(8*mm, y, 'TÉLÉPHONE')
    c.drawString(40*mm, y, 'NIVEAU')
    y -= 4*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica', 9)
    c.drawString(8*mm, y, str(a['telephone'] or '—'))
    c.drawString(40*mm, y, str(a['niveau_etudes'] or '—'))

    qr_size = 22*mm
    c.drawImage(qr_buf, w - qr_size - 10*mm, card_y + 6*mm, qr_size, qr_size)

    c.setFillColor(colors.white)
    c.setFont('Helvetica', 6)
    c.drawCentredString(w / 2, 6*mm, '3FPT · FORMATION PROFESSIONNELLE · SÉNÉGAL')

    c.showPage()
    c.save()
    buf.seek(0)

    log_action(current_user.id, 'PDF_CARTE_APPRENANT', str(a['numero_apprenant']), 'apprenants', aid)
    return send_file(buf, mimetype='application/pdf',
                     download_name='carte_' + str(a['numero_apprenant'] or aid) + '.pdf')


# ═══════════════════════════════════════════════════════════════
# 📝 INSCRIPTIONS
# ═══════════════════════════════════════════════════════════════

@app.route('/sessions/<int:sid>/inscription', methods=['GET', 'POST'])
@login_required
def sessions_inscription(sid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM sessions WHERE id=?", (sid,))
    s = cur.fetchone()
    if not s:
        flash('❌ Session introuvable', 'error')
        return redirect('/sessions')

    if request.method == 'POST':
        try:
            apprenant_id = int(request.form.get('apprenant_id') or 0)
            frais = float(request.form.get('frais_payes') or 0)
            financement = request.form.get('financement') or 'autofinance'

            cur.execute("""
                INSERT INTO inscriptions (session_id, apprenant_id, date_inscription, statut,
                                            frais_payes, reste_a_payer, financement, bailleur, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (sid, apprenant_id, datetime.now().strftime('%Y-%m-%d'), 'inscrit',
                  frais, 0, financement,
                  '3FPT' if financement == '3FPT' else None,
                  datetime.now().isoformat()))

            cur.execute("UPDATE sessions SET nb_inscrits = nb_inscrits + 1 WHERE id=?", (sid,))
            db.commit()
            flash('✅ Apprenant inscrit', 'success')
            return redirect('/sessions/' + str(sid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("""
        SELECT id, nom, prenom, numero_apprenant, telephone FROM apprenants
        WHERE statut='actif'
        AND id NOT IN (SELECT apprenant_id FROM inscriptions WHERE session_id=?)
        ORDER BY nom
    """, (sid,))
    apprenants = cur.fetchall()
    opts = ''.join('<option value="' + str(a["id"]) + '">' + str(a["numero_apprenant"] or "") + ' — ' + str(a["prenom"] or "") + ' ' + str(a["nom"] or "") + '</option>' for a in apprenants)

    content = '<h1>📝 Inscrire un apprenant</h1>'
    content += '<div class="card" style="max-width:700px">'
    content += '<h2>Session ' + str(s["code"]) + '</h2>'
    content += '<p style="color:#64748b;margin-bottom:20px">Capacité : ' + str(s["nb_inscrits"]) + '/' + str(s["capacite"]) + '</p>'
    content += '<form method="post">'
    content += '<div style="margin-bottom:16px"><label>Apprenant *</label><select name="apprenant_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Financement</label><select name="financement">'
    content += '<option value="3FPT">🏛️ 3FPT</option>'
    content += '<option value="autofinance">💰 Autofinancement</option>'
    content += '<option value="entreprise">🏢 Entreprise</option>'
    content += '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Frais payés (FCFA)</label>'
    content += '<input type="number" step="1000" name="frais_payes" value="0"></div>'
    content += '<button type="submit" class="btn btn-success">💾 Inscrire</button>'
    content += '<a href="/sessions/' + str(sid) + '" class="btn btn-secondary" style="margin-left:8px">Annuler</a>'
    content += '</form></div>'
    return render_page(content, active='sessions', page_title='Inscription')


# ═══════════════════════════════════════════════════════════════
# 📋 PRÉSENCES
# ═══════════════════════════════════════════════════════════════

@app.route('/sessions/<int:sid>/presences', methods=['GET', 'POST'])
@login_required
def sessions_presences(sid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM sessions WHERE id=?", (sid,))
    s = cur.fetchone()
    if not s:
        flash('❌ Session introuvable', 'error')
        return redirect('/sessions')

    if request.method == 'POST':
        try:
            date_p = request.form.get('date_presence') or datetime.now().strftime('%Y-%m-%d')
            for key in request.form.keys():
                if key.startswith('present_'):
                    ins_id = int(key.replace('present_', ''))
                    val = 1 if request.form.get(key) == 'on' else 0
                    cur.execute("""
                        INSERT INTO presences (inscription_id, session_id, date_presence, present, heures, created_at)
                        VALUES (?,?,?,?,4,?)
                    """, (ins_id, sid, date_p, val, datetime.now().isoformat()))
            db.commit()
            flash('✅ Présences enregistrées', 'success')
            return redirect('/sessions/' + str(sid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("""
        SELECT i.id AS ins_id, a.nom, a.prenom, a.numero_apprenant
        FROM inscriptions i
        LEFT JOIN apprenants a ON a.id=i.apprenant_id
        WHERE i.session_id=?
        ORDER BY a.nom
    """, (sid,))
    inscrits = cur.fetchall()

    rows_html = ''
    for i in inscrits:
        cur.execute("""
            SELECT COUNT(*) AS total, COALESCE(SUM(present),0) AS presents
            FROM presences WHERE inscription_id=?
        """, (i['ins_id'],))
        stat = cur.fetchone()
        total = stat['total'] or 0
        pres = stat['presents'] or 0
        taux = (pres / total * 100) if total > 0 else 0
        rows_html += (
            '<tr><td><strong>' + str(i["numero_apprenant"]) + '</strong></td>'
            + '<td>' + str(i["prenom"] or "") + ' ' + str(i["nom"] or "") + '</td>'
            + '<td style="text-align:center"><input type="checkbox" name="present_' + str(i["ins_id"]) + '" checked></td>'
            + '<td style="text-align:center">' + str(pres) + '/' + str(total) + '</td>'
            + '<td style="text-align:center">' + f'{taux:.0f}' + '%</td></tr>'
        )

    content = '<h1>📋 Présences — Session ' + str(s["code"]) + '</h1>'
    content += '<div class="card">'
    content += '<form method="post">'
    content += '<div style="margin-bottom:16px;max-width:300px"><label>Date</label>'
    content += '<input type="date" name="date_presence" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<table><thead><tr><th>N°</th><th>Nom</th><th style="text-align:center">Présent</th><th style="text-align:center">Cumul</th><th style="text-align:center">Taux</th></tr></thead>'
    content += '<tbody>' + (rows_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucun inscrit</td></tr>') + '</tbody></table>'
    content += '<div style="margin-top:20px"><button type="submit" class="btn btn-success">💾 Enregistrer</button>'
    content += '<a href="/sessions/' + str(sid) + '" class="btn btn-secondary" style="margin-left:8px">Retour</a></div>'
    content += '</form></div>'

    return render_page(content, active='sessions', page_title='Présences')


# ═══════════════════════════════════════════════════════════════
# 📊 ÉVALUATIONS
# ═══════════════════════════════════════════════════════════════

@app.route('/sessions/<int:sid>/evaluations', methods=['GET', 'POST'])
@login_required
def sessions_evaluations(sid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM sessions WHERE id=?", (sid,))
    s = cur.fetchone()
    if not s:
        flash('❌ Session introuvable', 'error')
        return redirect('/sessions')

    if request.method == 'POST':
        try:
            ins_id = int(request.form.get('inscription_id') or 0)
            type_eval = request.form.get('type_eval') or 'quiz'
            libelle = request.form.get('libelle') or ''
            note = float(request.form.get('note') or 0)

            cur.execute("""
                INSERT INTO evaluations (inscription_id, session_id, type_eval, libelle,
                                           note, note_max, date_eval, commentaire, created_at)
                VALUES (?,?,?,?,?,20,?,?,?)
            """, (ins_id, sid, type_eval, libelle, note,
                  datetime.now().strftime('%Y-%m-%d'),
                  request.form.get('commentaire') or '',
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Évaluation enregistrée', 'success')
            return redirect('/sessions/' + str(sid) + '/evaluations')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("""
        SELECT i.id AS ins_id, a.nom, a.prenom, a.numero_apprenant
        FROM inscriptions i
        LEFT JOIN apprenants a ON a.id=i.apprenant_id
        WHERE i.session_id=?
        ORDER BY a.nom
    """, (sid,))
    inscrits = cur.fetchall()

    cur.execute("""
        SELECT e.*, a.nom, a.prenom
        FROM evaluations e
        LEFT JOIN inscriptions i ON i.id=e.inscription_id
        LEFT JOIN apprenants a ON a.id=i.apprenant_id
        WHERE e.session_id=?
        ORDER BY e.id DESC LIMIT 30
    """, (sid,))
    evaluations = cur.fetchall()

    eval_html = ''
    for e in evaluations:
        color = '#10b981' if (e['note'] or 0) >= 10 else '#ef4444'
        eval_html += (
            '<tr><td>' + str(e["prenom"] or "") + ' ' + str(e["nom"] or "") + '</td>'
            + '<td>' + str(e["type_eval"]) + '</td>'
            + '<td>' + str(e["libelle"] or "") + '</td>'
            + '<td style="text-align:center;font-weight:800;color:' + color + '">' + f'{e["note"]:.1f}' + '/20</td>'
            + '<td>' + str(e["date_eval"] or "") + '</td></tr>'
        )

    opts_ins = ''.join('<option value="' + str(i["ins_id"]) + '">' + str(i["prenom"] or "") + ' ' + str(i["nom"] or "") + '</option>' for i in inscrits)

    content = '<h1>📊 Évaluations — Session ' + str(s["code"]) + '</h1>'

    content += '<div class="card"><h2>➕ Nouvelle évaluation</h2>'
    content += '<form method="post">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Apprenant *</label><select name="inscription_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_ins + '</select></div>'
    content += '<div><label>Type</label><select name="type_eval">'
    content += '<option value="quiz">Quiz</option>'
    content += '<option value="projet">Projet</option>'
    content += '<option value="examen_final">Examen final</option>'
    content += '<option value="travaux_pratiques">Travaux pratiques</option>'
    content += '</select></div>'
    content += '<div><label>Libellé</label><input type="text" name="libelle" placeholder="Quiz module 1"></div>'
    content += '<div><label>Note /20</label><input type="number" step="0.1" name="note" value="10" min="0" max="20"></div>'
    content += '<div style="grid-column:1/-1"><label>Commentaire</label><textarea name="commentaire" rows="2"></textarea></div>'
    content += '</div>'
    content += '<div style="margin-top:16px"><button type="submit" class="btn btn-success">💾 Enregistrer</button></div>'
    content += '</form></div>'

    content += '<div class="card"><h2>📊 Évaluations récentes (' + str(len(evaluations)) + ')</h2>'
    content += '<table><thead><tr><th>Apprenant</th><th>Type</th><th>Libellé</th><th style="text-align:center">Note</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (eval_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucune évaluation</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='sessions', page_title='Évaluations')


# ═══════════════════════════════════════════════════════════════
# 📜 CERTIFICATS
# ═══════════════════════════════════════════════════════════════

@app.route('/certificats')
@login_required
def certificats_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, a.nom, a.prenom, a.numero_apprenant, f.nom AS formation_nom
        FROM certificats c
        LEFT JOIN apprenants a ON a.id=c.apprenant_id
        LEFT JOIN formations f ON f.id=c.formation_id
        ORDER BY c.id DESC LIMIT 200
    """)
    certificats = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM certificats WHERE statut='valide'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM certificats WHERE mention='Excellent'")
    stats['excellent'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM certificats WHERE mention='Très bien'")
    stats['tb'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(note_finale),0) FROM certificats")
    stats['moy'] = cur.fetchone()[0]

    rows = ''
    for c in certificats:
        rows += (
            '<tr><td><strong style="color:#ea580c">' + str(c["numero_certificat"]) + '</strong></td>'
            + '<td><strong>' + str(c["prenom"] or "") + ' ' + str(c["nom"] or "") + '</strong><br><small style="color:#64748b">' + str(c["numero_apprenant"] or "") + '</small></td>'
            + '<td>' + str(c["formation_nom"] or "—") + '</td>'
            + '<td style="text-align:center;font-weight:800">' + f'{c["note_finale"]:.1f}' + '/20</td>'
            + '<td><span class="badge badge-green">' + str(c["mention"] or "") + '</span></td>'
            + '<td>' + str((c["date_emission"] or "—")[:10]) + '</td>'
            + '<td><a href="/certificats/' + str(c["id"]) + '" class="btn btn-danger" style="padding:4px 10px;font-size:11px">📜</a></td></tr>'
        )

    content = '<h1>📜 Certificats — ' + str(len(certificats)) + '</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-icon">📜</div><div class="kpi-label">Certificats émis</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🏆</div><div class="kpi-label">Mentions Excellent</div><div class="kpi-value">' + str(stats["excellent"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-icon">🥈</div><div class="kpi-label">Mentions Très bien</div><div class="kpi-value">' + str(stats["tb"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">📊</div><div class="kpi-label">Note moyenne</div><div class="kpi-value">' + f'{stats["moy"]:.1f}' + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Certificat</th><th>Apprenant</th><th>Formation</th><th style="text-align:center">Note</th><th>Mention</th><th>Émis le</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucun certificat</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='certificats', page_title='Certificats')


@app.route('/certificats/<int:cid>')
@login_required
def certificats_detail(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, a.nom, a.prenom, a.numero_apprenant, a.date_naissance,
               f.nom AS formation_nom, f.duree_heures, f.domaine,
               s.date_debut, s.date_fin, s.code AS session_code
        FROM certificats c
        LEFT JOIN apprenants a ON a.id=c.apprenant_id
        LEFT JOIN formations f ON f.id=c.formation_id
        LEFT JOIN sessions s ON s.id=c.session_id
        WHERE c.id=?
    """, (cid,))
    c = cur.fetchone()
    if not c:
        flash('❌ Certificat introuvable', 'error')
        return redirect('/certificats')

    qr_url = '/certificats/' + str(cid) + '/qr.png'

    content = '''
    <div style="max-width:700px;margin:0 auto">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
        <a href="/certificats" class="btn btn-secondary">← Retour</a>
        <a href="/certificats/''' + str(cid) + '''/pdf" class="btn btn-primary">📄 Télécharger PDF</a>
      </div>

      <div style="background:linear-gradient(135deg,#fff7ed,#fed7aa);border:6px double #c2410c;border-radius:16px;padding:40px;box-shadow:0 10px 30px rgba(0,0,0,.15)">
        <div style="text-align:center;margin-bottom:24px">
          <div style="font-size:60px;margin-bottom:8px">🎓</div>
          <div style="font-size:11px;letter-spacing:3px;color:#c2410c;font-weight:700;text-transform:uppercase">République du Sénégal</div>
          <div style="font-size:20px;font-weight:900;color:#c2410c;margin-top:4px">OMEGA FORMATION PROFESSIONNELLE</div>
          <div style="height:3px;background:#c2410c;width:80px;margin:14px auto"></div>
        </div>

        <div style="text-align:center;margin-bottom:30px">
          <div style="font-size:14px;color:#64748b;letter-spacing:2px;margin-bottom:12px">CERTIFICAT DE FORMATION PROFESSIONNELLE</div>
          <div style="font-size:12px;color:#475569">Décerné à</div>
          <div style="font-size:28px;font-weight:900;color:#1e293b;margin:14px 0">''' + str(c['prenom']) + ' ' + str(c['nom']) + '''</div>
          <div style="font-size:12px;color:#475569">N° apprenant : ''' + str(c['numero_apprenant']) + '''</div>
        </div>

        <div style="background:#fff;border-radius:12px;padding:22px;margin-bottom:24px">
          <div style="font-size:13px;color:#64748b;text-align:center;margin-bottom:10px">a suivi avec succès la formation</div>
          <div style="font-size:20px;font-weight:800;color:#c2410c;text-align:center;margin-bottom:16px">''' + str(c['formation_nom']) + '''</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:13px">
            <div><strong>Domaine :</strong> ''' + str(c['domaine'] or '—') + '''</div>
            <div><strong>Durée :</strong> ''' + str(c['duree_heures']) + ''' heures</div>
            <div><strong>Période :</strong> ''' + str((c['date_debut'] or '—')[:10]) + ''' → ''' + str((c['date_fin'] or '—')[:10]) + '''</div>
            <div><strong>Note finale :</strong> ''' + f'{c["note_finale"]:.1f}' + '''/20</div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px;align-items:center">
          <div>
            <div style="font-size:12px;color:#64748b;letter-spacing:2px;margin-bottom:6px">MENTION</div>
            <div style="font-size:24px;font-weight:900;color:#ea580c">''' + str(c['mention'] or '—') + '''</div>
            <div style="margin-top:20px;padding-top:14px;border-top:2px dashed #cbd5e1;font-size:12px;color:#475569">
              <div><strong>N° certificat :</strong> <code>''' + str(c['numero_certificat']) + '''</code></div>
              <div><strong>Émis le :</strong> ''' + str((c['date_emission'] or '—')[:10]) + '''</div>
            </div>
          </div>
          <div style="text-align:center">
            <img src="''' + qr_url + '''" alt="QR" style="width:120px;height:120px;border:3px solid #c2410c;border-radius:10px;background:#fff">
            <div style="font-size:10px;color:#64748b;margin-top:6px;font-weight:700">SCANNER POUR VÉRIFIER</div>
          </div>
        </div>
      </div>
    </div>
    '''
    return render_page(content, active='certificats', page_title='Certificat')


@app.route('/certificats/<int:cid>/qr.png')
def certificats_qr(cid):
    import qrcode
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT numero_certificat FROM certificats WHERE id=?", (cid,))
    c = cur.fetchone()
    if not c:
        return redirect('/')
    qr_data = 'FORM|CERT|' + str(cid) + '|' + (c['numero_certificat'] or '')
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#c2410c', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


@app.route('/certificats/<int:cid>/pdf')
@login_required
def certificats_pdf(cid):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    import qrcode

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, a.nom, a.prenom, a.numero_apprenant, f.nom AS formation_nom,
               f.duree_heures, f.domaine, s.date_debut, s.date_fin
        FROM certificats c
        LEFT JOIN apprenants a ON a.id=c.apprenant_id
        LEFT JOIN formations f ON f.id=c.formation_id
        LEFT JOIN sessions s ON s.id=c.session_id
        WHERE c.id=?
    """, (cid,))
    c = cur.fetchone()
    if not c:
        flash('❌ Certificat introuvable', 'error')
        return redirect('/certificats')

    qr = qrcode.make('FORM|CERT|' + str(cid) + '|' + str(c['numero_certificat']))
    qr_buf = io.BytesIO()
    qr.save(qr_buf, format='PNG')
    qr_buf.seek(0)

    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=landscape(A4))
    w, h = landscape(A4)

    cv.setFillColor(colors.HexColor('#fff7ed'))
    cv.rect(0, 0, w, h, fill=1, stroke=0)

    cv.setStrokeColor(colors.HexColor('#c2410c'))
    cv.setLineWidth(6)
    cv.rect(10*mm, 10*mm, w - 20*mm, h - 20*mm, fill=0, stroke=1)
    cv.setLineWidth(2)
    cv.rect(13*mm, 13*mm, w - 26*mm, h - 26*mm, fill=0, stroke=1)

    cv.setFillColor(colors.HexColor('#c2410c'))
    cv.setFont('Helvetica-Bold', 12)
    cv.drawCentredString(w / 2, h - 30*mm, 'RÉPUBLIQUE DU SÉNÉGAL')
    cv.setFont('Helvetica-Bold', 20)
    cv.drawCentredString(w / 2, h - 40*mm, 'OMEGA FORMATION PROFESSIONNELLE')
    cv.setFont('Helvetica', 11)
    cv.drawCentredString(w / 2, h - 47*mm, 'CERTIFICAT DE FORMATION PROFESSIONNELLE')

    cv.setFillColor(colors.black)
    cv.setFont('Helvetica', 12)
    cv.drawCentredString(w / 2, h - 65*mm, 'Décerné à')
    cv.setFont('Helvetica-Bold', 26)
    cv.setFillColor(colors.HexColor('#1e293b'))
    cv.drawCentredString(w / 2, h - 78*mm, str(c['prenom']) + ' ' + str(c['nom']))
    cv.setFont('Helvetica', 10)
    cv.setFillColor(colors.HexColor('#64748b'))
    cv.drawCentredString(w / 2, h - 84*mm, 'N° apprenant : ' + str(c['numero_apprenant']))

    cv.setFillColor(colors.black)
    cv.setFont('Helvetica', 12)
    cv.drawCentredString(w / 2, h - 97*mm, 'a suivi avec succès la formation')
    cv.setFont('Helvetica-Bold', 20)
    cv.setFillColor(colors.HexColor('#c2410c'))
    cv.drawCentredString(w / 2, h - 108*mm, str(c['formation_nom']))

    cv.setFont('Helvetica', 10)
    cv.setFillColor(colors.black)
    cv.drawCentredString(w / 2, h - 118*mm, 'Domaine : ' + str(c['domaine'] or '—') + '   ·   Durée : ' + str(c['duree_heures']) + 'h   ·   Note : ' + f'{c["note_finale"]:.1f}' + '/20')
    cv.drawCentredString(w / 2, h - 125*mm, 'Période : ' + str((c['date_debut'] or '—')[:10]) + ' → ' + str((c['date_fin'] or '—')[:10]))

    cv.setFont('Helvetica-Bold', 14)
    cv.setFillColor(colors.HexColor('#ea580c'))
    cv.drawCentredString(w / 2, h - 140*mm, 'MENTION : ' + str(c['mention'] or '').upper())

    qr_size = 30*mm
    cv.drawImage(qr_buf, w - 60*mm, 25*mm, qr_size, qr_size)

    cv.setFont('Helvetica', 9)
    cv.setFillColor(colors.HexColor('#64748b'))
    cv.drawString(20*mm, 35*mm, 'N° Certificat : ' + str(c['numero_certificat']))
    cv.drawString(20*mm, 30*mm, 'Émis le : ' + str((c['date_emission'] or '')[:10]))
    cv.drawRightString(w - 20*mm, 20*mm, 'OMEGA Formation Professionnelle · Sénégal')

    cv.showPage()
    cv.save()
    buf.seek(0)

    log_action(current_user.id, 'PDF_CERTIFICAT', str(c['numero_certificat']), 'certificats', cid)
    return send_file(buf, mimetype='application/pdf',
                     download_name='certificat_' + str(c['numero_certificat']) + '.pdf')


# ═══════════════════════════════════════════════════════════════
# 💰 FINANCEMENTS (3FPT, bailleurs)
# ═══════════════════════════════════════════════════════════════

@app.route('/financements')
@login_required
def financements_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM financements ORDER BY montant_total DESC")
    financements = cur.fetchall()

    stats = {}
    cur.execute("SELECT COALESCE(SUM(montant_total),0) FROM financements WHERE statut='actif'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant_utilise),0) FROM financements WHERE statut='actif'")
    stats['utilise'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM financements WHERE statut='actif'")
    stats['nb'] = cur.fetchone()[0]
    stats['dispo'] = stats['total'] - stats['utilise']

    cards = ''
    for f in financements:
        pct = (f['montant_utilise'] / f['montant_total'] * 100) if f['montant_total'] > 0 else 0
        type_icons = {'public': '🏛️', 'cooperation': '🤝', 'prive': '🏢'}
        icon = type_icons.get(f['type_bailleur'], '💰')
        cards += '<div class="card" style="border-left-color:#10b981">'
        cards += '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">'
        cards += '<div><div style="font-size:20px;font-weight:900;color:#1e293b">' + icon + ' ' + str(f["bailleur"]) + '</div>'
        cards += '<div style="font-size:13px;color:#64748b;margin-top:4px">' + str(f["programme"] or "") + '</div></div>'
        cards += '<span class="badge badge-green">' + str(f["statut"]) + '</span></div>'
        cards += '<div style="margin:14px 0">'
        cards += '<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px">'
        cards += '<strong>Utilisation</strong><span style="color:#64748b">' + f'{f["montant_utilise"]:,.0f}' + ' / ' + f'{f["montant_total"]:,.0f}' + ' F</span></div>'
        cards += '<div style="background:#e2e8f0;border-radius:6px;overflow:hidden;height:14px">'
        cards += '<div style="background:linear-gradient(90deg,#10b981,#047857);height:100%;width:' + f'{pct:.0f}' + '%"></div></div>'
        cards += '<div style="text-align:right;margin-top:6px;font-size:12px;font-weight:700;color:#10b981">' + f'{pct:.1f}' + '%</div></div>'
        cards += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;color:#475569;margin-top:12px">'
        cards += '<div>📅 Début : ' + str((f["date_debut"] or "—")[:10]) + '</div>'
        cards += '<div>📅 Fin : ' + str((f["date_fin"] or "—")[:10]) + '</div>'
        cards += '</div>'
        cards += '<div style="margin-top:12px"><a href="/financements/' + str(f["id"]) + '/rapport" class="btn btn-blue" style="padding:6px 12px;font-size:12px;width:100%;text-align:center;display:block">📊 Rapport bailleur</a></div>'
        cards += '</div>'

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">💰 Financements — ' + str(len(financements)) + '</h1>'
    content += '<a href="/financements/nouveau" class="btn btn-primary">+ Nouveau financement</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">Total financements</div><div class="kpi-value" style="font-size:16px">' + f'{stats["total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-icon">📊</div><div class="kpi-label">Utilisé</div><div class="kpi-value" style="font-size:16px">' + f'{stats["utilise"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-icon">✅</div><div class="kpi-label">Disponible</div><div class="kpi-value" style="font-size:16px">' + f'{stats["dispo"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🏛️</div><div class="kpi-label">Bailleurs</div><div class="kpi-value">' + str(stats["nb"]) + '</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:16px">' + (cards or '<p style="grid-column:1/-1;text-align:center;color:#94a3b8;padding:40px">Aucun financement</p>') + '</div>'

    return render_page(content, active='financements', page_title='Financements')


@app.route('/financements/nouveau', methods=['GET', 'POST'])
@login_required
def financements_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO financements
                (code, bailleur, type_bailleur, programme, montant_total, montant_utilise,
                 date_debut, date_fin, contact, telephone, statut, created_at)
                VALUES (?,?,?,?,?,0,?,?,?,?, 'actif', ?)
            """, (None,
                  request.form.get('bailleur'),
                  request.form.get('type_bailleur') or 'public',
                  request.form.get('programme'),
                  float(request.form.get('montant_total') or 0),
                  request.form.get('date_debut'),
                  request.form.get('date_fin'),
                  request.form.get('contact'),
                  request.form.get('telephone'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Financement créé', 'success')
            return redirect('/financements')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>💰 Nouveau financement</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Bailleur *</label><input type="text" name="bailleur" required autofocus placeholder="3FPT, ONFP, GIZ, AFD..."></div>'
    content += '<div><label>Type</label><select name="type_bailleur">'
    content += '<option value="public">🏛️ Public (État)</option>'
    content += '<option value="cooperation">🤝 Coopération</option>'
    content += '<option value="prive">🏢 Privé</option>'
    content += '</select></div>'
    content += '<div><label>Programme</label><input type="text" name="programme"></div>'
    content += '<div><label>Montant total (FCFA)</label><input type="number" step="1000000" name="montant_total" value="100000000"></div>'
    content += '<div><label>Date début</label><input type="date" name="date_debut" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Date fin</label><input type="date" name="date_fin" value="' + (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Contact</label><input type="text" name="contact"></div>'
    content += '<div><label>Téléphone</label><input type="text" name="telephone"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/financements" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='financements', page_title='Nouveau financement')


@app.route('/financements/<int:fid>/rapport')
@login_required
def financements_rapport(fid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM financements WHERE id=?", (fid,))
    f = cur.fetchone()
    if not f:
        flash('❌ Financement introuvable', 'error')
        return redirect('/financements')

    cur.execute("""
        SELECT s.*, fo.nom AS formation_nom, c.nom AS centre_nom
        FROM sessions s
        LEFT JOIN formations fo ON fo.id=s.formation_id
        LEFT JOIN centres c ON c.id=s.centre_id
        WHERE s.financement='3FPT'
        ORDER BY s.date_debut DESC LIMIT 20
    """)
    sessions = cur.fetchall()

    sess_html = ''
    total_cout = 0
    for s in sessions:
        total_cout += s['cout_total'] or 0
        sess_html += (
            '<tr><td>' + str(s["code"]) + '</td>'
            + '<td>' + str(s["formation_nom"] or "—") + '</td>'
            + '<td>' + str(s["centre_nom"] or "—") + '</td>'
            + '<td style="text-align:center">' + str(s["nb_inscrits"]) + '</td>'
            + '<td style="text-align:right">' + f'{s["cout_total"]:,.0f}' + ' F</td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📊 Rapport ' + str(f["bailleur"]) + '</h1>'
    content += '<a href="/financements" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Montant total</div><div class="kpi-value" style="font-size:16px">' + f'{f["montant_total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-label">Utilisé</div><div class="kpi-value" style="font-size:16px">' + f'{f["montant_utilise"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-label">Sessions</div><div class="kpi-value">' + str(len(sessions)) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Coût cumulé</div><div class="kpi-value" style="font-size:16px">' + f'{total_cout:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations programme</h2><table>'
    content += '<tr><td><strong>Bailleur</strong></td><td>' + str(f["bailleur"]) + '</td></tr>'
    content += '<tr><td><strong>Programme</strong></td><td>' + str(f["programme"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Type</strong></td><td>' + str(f["type_bailleur"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Période</strong></td><td>' + str((f["date_debut"] or "—")[:10]) + ' → ' + str((f["date_fin"] or "—")[:10]) + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>📅 Sessions financées (' + str(len(sessions)) + ')</h2>'
    content += '<table><thead><tr><th>Code</th><th>Formation</th><th>Centre</th><th style="text-align:center">Inscrits</th><th style="text-align:right">Coût</th></tr></thead>'
    content += '<tbody>' + (sess_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucune session</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='financements', page_title='Rapport bailleur')


# ═══════════════════════════════════════════════════════════════
# 🔗 PARTENARIATS ENTREPRISES
# ═══════════════════════════════════════════════════════════════

@app.route('/partenariats')
@login_required
def partenariats_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM partenariats ORDER BY nb_embauches DESC")
    partenariats = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM partenariats WHERE statut='actif'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(nb_places_stage),0) FROM partenariats")
    stats['stages'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(nb_embauches),0) FROM partenariats")
    stats['embauches'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT secteur) FROM partenariats")
    stats['secteurs'] = cur.fetchone()[0]

    rows = ''
    for p in partenariats:
        rows += (
            '<tr><td><strong style="color:#ea580c">' + str(p["entreprise"]) + '</strong><br><small style="color:#64748b">' + str(p["secteur"] or "") + '</small></td>'
            + '<td>' + str(p["contact_nom"] or "—") + '<br><small style="color:#64748b">' + str(p["telephone"] or "") + '</small></td>'
            + '<td><span class="badge badge-blue">' + str(p["type_partenariat"] or "—") + '</span></td>'
            + '<td>' + str(p["formations_concernees"] or "—") + '</td>'
            + '<td style="text-align:center">' + str(p["nb_places_stage"]) + '</td>'
            + '<td style="text-align:center;font-weight:800;color:#10b981">' + str(p["nb_embauches"]) + '</td>'
            + '<td>' + str((p["date_signature"] or "—")[:10]) + '</td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🔗 Partenariats — ' + str(len(partenariats)) + '</h1>'
    content += '<a href="/partenariats/nouveau" class="btn btn-primary">+ Nouveau partenariat</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-icon">🔗</div><div class="kpi-label">Partenariats actifs</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-icon">🎓</div><div class="kpi-label">Places de stage</div><div class="kpi-value">' + str(stats["stages"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💼</div><div class="kpi-label">Embauches</div><div class="kpi-value">' + str(stats["embauches"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">🏢</div><div class="kpi-label">Secteurs</div><div class="kpi-value">' + str(stats["secteurs"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Entreprise</th><th>Contact</th><th>Type</th><th>Formations</th>'
    content += '<th style="text-align:center">Stages</th><th style="text-align:center">Embauches</th><th>Signé le</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucun partenariat</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='partenariats', page_title='Partenariats')


@app.route('/partenariats/nouveau', methods=['GET', 'POST'])
@login_required
def partenariats_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO partenariats (entreprise, secteur, contact_nom, telephone, email,
                                            type_partenariat, formations_concernees,
                                            nb_places_stage, nb_embauches, date_signature, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (request.form.get('entreprise'),
                  request.form.get('secteur'),
                  request.form.get('contact_nom'),
                  request.form.get('telephone'),
                  request.form.get('email'),
                  request.form.get('type_partenariat'),
                  request.form.get('formations_concernees'),
                  int(request.form.get('nb_places_stage') or 0),
                  int(request.form.get('nb_embauches') or 0),
                  request.form.get('date_signature') or datetime.now().strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Partenariat créé', 'success')
            return redirect('/partenariats')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>🔗 Nouveau partenariat</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Entreprise *</label><input type="text" name="entreprise" required autofocus></div>'
    content += '<div><label>Secteur</label><input type="text" name="secteur"></div>'
    content += '<div><label>Type de partenariat</label><select name="type_partenariat">'
    content += '<option value="Stages + Emploi">Stages + Emploi</option>'
    content += '<option value="Embauche directe">Embauche directe</option>'
    content += '<option value="Apprentissage">Apprentissage</option>'
    content += '<option value="Formation continue">Formation continue</option>'
    content += '</select></div>'
    content += '<div><label>Contact</label><input type="text" name="contact_nom"></div>'
    content += '<div><label>Téléphone</label><input type="text" name="telephone"></div>'
    content += '<div><label>Email</label><input type="email" name="email"></div>'
    content += '<div><label>Formations concernées</label><input type="text" name="formations_concernees"></div>'
    content += '<div><label>Date signature</label><input type="date" name="date_signature" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Nb places de stage</label><input type="number" name="nb_places_stage" value="0"></div>'
    content += '<div><label>Nb embauches</label><input type="number" name="nb_embauches" value="0"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/partenariats" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='partenariats', page_title='Nouveau partenariat')


# ═══════════════════════════════════════════════════════════════
# 📈 PLACEMENT POST-FORMATION
# ═══════════════════════════════════════════════════════════════

@app.route('/placements')
@login_required
def placements_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT p.*, a.nom, a.prenom, a.numero_apprenant, a.telephone,
               f.nom AS formation_nom
        FROM placements p
        LEFT JOIN apprenants a ON a.id=p.apprenant_id
        LEFT JOIN inscriptions i ON i.id=p.inscription_id
        LEFT JOIN sessions s ON s.id=i.session_id
        LEFT JOIN formations f ON f.id=s.formation_id
        ORDER BY p.id DESC LIMIT 200
    """)
    placements = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM placements WHERE statut='actif'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM placements WHERE type='emploi'")
    stats['emplois'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM placements WHERE type='stage'")
    stats['stages'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(salaire_mensuel),0) FROM placements WHERE salaire_mensuel > 0")
    stats['salaire'] = cur.fetchone()[0]

    rows = ''
    for p in placements:
        type_badge = {'emploi': 'badge-green', 'stage': 'badge-blue', 'apprentissage': 'badge-orange'}.get(p['type'], 'badge-gray')
        rows += (
            '<tr><td><strong>' + str(p["numero_apprenant"] or "—") + '</strong></td>'
            + '<td>' + str(p["prenom"] or "") + ' ' + str(p["nom"] or "") + '<br><small style="color:#64748b">' + str(p["telephone"] or "") + '</small></td>'
            + '<td>' + str(p["formation_nom"] or "—") + '</td>'
            + '<td>' + str(p["entreprise"] or "—") + '<br><small style="color:#64748b">' + str(p["poste"] or "") + '</small></td>'
            + '<td><span class="badge ' + type_badge + '">' + str(p["type"]) + '</span></td>'
            + '<td style="text-align:right">' + (f'{p["salaire_mensuel"]:,.0f}' + ' F' if p["salaire_mensuel"] > 0 else '—') + '</td>'
            + '<td>' + str((p["date_debut"] or "—")[:10]) + '</td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📈 Placements — ' + str(len(placements)) + '</h1>'
    content += '<a href="/placements/nouveau" class="btn btn-primary">+ Nouveau placement</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-icon">📈</div><div class="kpi-label">Total placements</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💼</div><div class="kpi-label">Emplois</div><div class="kpi-value">' + str(stats["emplois"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-icon">🎓</div><div class="kpi-label">Stages</div><div class="kpi-value">' + str(stats["stages"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">💰</div><div class="kpi-label">Salaire moyen</div><div class="kpi-value" style="font-size:16px">' + f'{stats["salaire"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N°</th><th>Apprenant</th><th>Formation</th><th>Entreprise/Poste</th>'
    content += '<th>Type</th><th style="text-align:right">Salaire</th><th>Début</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucun placement</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='placements', page_title='Placements')


@app.route('/placements/nouveau', methods=['GET', 'POST'])
@login_required
def placements_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO placements (apprenant_id, inscription_id, type, entreprise, poste,
                                         salaire_mensuel, date_debut, statut, commentaire, created_at)
                VALUES (?,?,?,?,?,?,?, 'actif', ?, ?)
            """, (int(request.form.get('apprenant_id') or 0),
                  int(request.form.get('inscription_id') or 0) or None,
                  request.form.get('type') or 'emploi',
                  request.form.get('entreprise'),
                  request.form.get('poste'),
                  float(request.form.get('salaire_mensuel') or 0),
                  request.form.get('date_debut') or datetime.now().strftime('%Y-%m-%d'),
                  request.form.get('commentaire'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Placement enregistré', 'success')
            return redirect('/placements')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom, prenom, numero_apprenant FROM apprenants WHERE statut='actif' ORDER BY nom LIMIT 500")
    apprenants = cur.fetchall()
    opts = ''.join('<option value="' + str(a["id"]) + '">' + str(a["numero_apprenant"] or "") + ' — ' + str(a["prenom"] or "") + ' ' + str(a["nom"] or "") + '</option>' for a in apprenants)

    content = '<h1>📈 Nouveau placement</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="margin-bottom:16px"><label>Apprenant *</label><select name="apprenant_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts + '</select></div>'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Type</label><select name="type">'
    content += '<option value="emploi">💼 Emploi</option>'
    content += '<option value="stage">🎓 Stage</option>'
    content += '<option value="apprentissage">🔧 Apprentissage</option>'
    content += '</select></div>'
    content += '<div><label>Date début</label><input type="date" name="date_debut" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Entreprise</label><input type="text" name="entreprise"></div>'
    content += '<div><label>Poste</label><input type="text" name="poste"></div>'
    content += '<div><label>Salaire mensuel (FCFA)</label><input type="number" step="10000" name="salaire_mensuel" value="0"></div>'
    content += '</div>'
    content += '<div style="margin-top:16px"><label>Commentaire</label><textarea name="commentaire" rows="2"></textarea></div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Enregistrer</button>'
    content += '<a href="/placements" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='placements', page_title='Nouveau placement')


# ═══════════════════════════════════════════════════════════════
# 📊 RAPPORTS & ANALYTICS
# ═══════════════════════════════════════════════════════════════

@app.route('/rapports')
@login_required
def rapports_index():
    db = get_db()
    cur = db.cursor()

    def sc(sql, default=0):
        cur.execute(sql)
        r = cur.fetchone()
        return r[0] if r and r[0] is not None else default

    total_apprenants = sc("SELECT COUNT(*) FROM apprenants")
    total_formes = sc("SELECT COUNT(DISTINCT apprenant_id) FROM certificats")
    total_certificats = sc("SELECT COUNT(*) FROM certificats WHERE statut='valide'")
    total_placements = sc("SELECT COUNT(*) FROM placements WHERE statut='actif'")
    taux_employabilite = (total_placements / total_certificats * 100) if total_certificats > 0 else 0

    # Par domaine
    cur.execute("""
        SELECT f.domaine,
               COUNT(DISTINCT f.id) AS nb_formations,
               COUNT(DISTINCT s.id) AS nb_sessions,
               COUNT(DISTINCT i.apprenant_id) AS nb_apprenants
        FROM formations f
        LEFT JOIN sessions s ON s.formation_id=f.id
        LEFT JOIN inscriptions i ON i.session_id=s.id
        WHERE f.domaine IS NOT NULL
        GROUP BY f.domaine
        ORDER BY nb_apprenants DESC
    """)
    domaines = cur.fetchall()
    dom_html = ''
    max_a = max([d['nb_apprenants'] for d in domaines], default=1)
    for d in domaines:
        pct = d['nb_apprenants'] / max_a * 100
        dom_html += (
            '<div style="margin-bottom:12px">'
            + '<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">'
            + '<strong>' + str(d["domaine"]) + '</strong>'
            + '<span>' + str(d["nb_apprenants"]) + ' apprenants · ' + str(d["nb_sessions"]) + ' sessions</span></div>'
            + '<div style="background:#e2e8f0;border-radius:6px;overflow:hidden;height:12px">'
            + '<div style="background:linear-gradient(90deg,#ea580c,#c2410c);height:100%;width:' + f'{pct:.0f}' + '%"></div></div></div>'
        )

    # Par région
    cur.execute("""
        SELECT region, COUNT(*) AS nb FROM apprenants WHERE region IS NOT NULL
        GROUP BY region ORDER BY nb DESC LIMIT 8
    """)
    regions = cur.fetchall()
    reg_html = ''
    max_r = max([r['nb'] for r in regions], default=1)
    for r in regions:
        pct = r['nb'] / max_r * 100
        reg_html += (
            '<div style="margin-bottom:10px">'
            + '<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">'
            + '<strong>' + str(r["region"]) + '</strong><span>' + str(r["nb"]) + '</span></div>'
            + '<div style="background:#e2e8f0;border-radius:6px;overflow:hidden;height:10px">'
            + '<div style="background:linear-gradient(90deg,#2563eb,#1e40af);height:100%;width:' + f'{pct:.0f}' + '%"></div></div></div>'
        )

    content = '<h1>📊 Rapports & Analytics</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-icon">👥</div><div class="kpi-label">Apprenants formés</div><div class="kpi-value">' + str(total_formes) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-icon">📜</div><div class="kpi-label">Certificats</div><div class="kpi-value">' + str(total_certificats) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💼</div><div class="kpi-label">Placements</div><div class="kpi-value">' + str(total_placements) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">📈</div><div class="kpi-label">Taux employabilité</div><div class="kpi-value">' + f'{taux_employabilite:.0f}' + '%</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>🎓 Répartition par domaine</h2>' + (dom_html or '<p style="color:#94a3b8;text-align:center;padding:20px">Aucune donnée</p>') + '</div>'
    content += '<div class="card"><h2>🗺️ Apprenants par région</h2>' + (reg_html or '<p style="color:#94a3b8;text-align:center;padding:20px">Aucune donnée</p>') + '</div>'
    content += '</div>'

    content += '<div class="card" style="border-left-color:#10b981"><h2>🎯 Objectifs 3FPT / Sénégal</h2>'
    content += '<ul style="line-height:2;color:#334155;font-size:14px">'
    content += '<li>🎓 <strong>+60% employabilité</strong> des sortants de formation</li>'
    content += '<li>🏫 <strong>500 centres 3FPT</strong> connectés au Sénégal</li>'
    content += '<li>🌍 <strong>2 000 centres CEDEAO</strong> cible</li>'
    content += '<li>📜 <strong>Certificats QR vérifiables</strong> (anti-fraude)</li>'
    content += '<li>💼 <strong>Traçabilité</strong> du placement post-formation</li>'
    content += '</ul></div>'

    return render_page(content, active='rapports', page_title='Rapports')


# ═══════════════════════════════════════════════════════════════
# 📱 MOBILE APPRENANT
# ═══════════════════════════════════════════════════════════════

@app.route('/mobile-apprenant')
@login_required
def mobile_apprenant():
    db = get_db()
    cur = db.cursor()

    def sc(sql, default=0):
        cur.execute(sql)
        r = cur.fetchone()
        return r[0] if r and r[0] is not None else default

    stats = {
        'apprenants_jour': sc("SELECT COUNT(*) FROM apprenants WHERE date_inscription=date('now')"),
        'sessions_encours': sc("SELECT COUNT(*) FROM sessions WHERE statut='en_cours'"),
        'certificats_mois': sc("SELECT COUNT(*) FROM certificats WHERE strftime('%Y-%m',date_emission)=strftime('%Y-%m','now')"),
        'placements_mois': sc("SELECT COUNT(*) FROM placements WHERE strftime('%Y-%m',date_debut)=strftime('%Y-%m','now')"),
    }

    content = '<h1>📱 Mobile Apprenant</h1>'
    content += '<div style="background:#fff7ed;border-left:4px solid #ea580c;padding:14px;border-radius:8px;margin-bottom:20px;font-size:13px;color:#c2410c">'
    content += '💡 Interface mobile pour apprenants — accès aux cours, présences, certificats'
    content += '</div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ea580c,#c2410c)"><div class="kpi-label">Inscrits aujourd\'hui</div><div class="kpi-value">' + str(stats["apprenants_jour"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-label">Sessions en cours</div><div class="kpi-value">' + str(stats["sessions_encours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Certificats ce mois</div><div class="kpi-value">' + str(stats["certificats_mois"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-label">Placements ce mois</div><div class="kpi-value">' + str(stats["placements_mois"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>⚡ Actions rapides</h2>'
    content += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:12px">'
    actions = [
        ('/apprenants/nouveau', '👤 Nouvel apprenant', '#ea580c'),
        ('/formations', '🎓 Catalogue formations', '#2563eb'),
        ('/sessions', '📅 Mes sessions', '#10b981'),
        ('/certificats', '📜 Mes certificats', '#f59e0b'),
        ('/placements', '💼 Placement', '#8b5cf6'),
        ('/financements', '💰 Financement 3FPT', '#ec4899'),
    ]
    for url, label, color in actions:
        content += '<a href="' + url + '" style="text-decoration:none"><div style="background:' + color + ';color:#fff;padding:20px;border-radius:10px;text-align:center;font-weight:700;font-size:13px">' + label + '</div></a>'
    content += '</div></div>'

    content += '<div class="card"><h2>📅 Mes prochaines sessions</h2>'
    cur.execute("""
        SELECT s.*, f.nom AS formation_nom, f.domaine, c.nom AS centre_nom
        FROM sessions s
        LEFT JOIN formations f ON f.id=s.formation_id
        LEFT JOIN centres c ON c.id=s.centre_id
        WHERE s.statut IN ('planifiee', 'en_cours')
        ORDER BY s.date_debut ASC LIMIT 6
    """)
    sessions = cur.fetchall()
    rows = ''
    for s in sessions:
        rows += (
            '<tr><td><strong>' + str(s["code"]) + '</strong></td>'
            + '<td>' + str(s["formation_nom"] or "—") + '</td>'
            + '<td>' + str(s["centre_nom"] or "—") + '</td>'
            + '<td>' + str((s["date_debut"] or "—")[:10]) + '</td></tr>'
        )
    content += '<table><thead><tr><th>Code</th><th>Formation</th><th>Centre</th><th>Début</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucune session</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='rapports', page_title='Mobile Apprenant')


# ═══════════════════════════════════════════════════════════════
# 📊 API JSON
# ═══════════════════════════════════════════════════════════════

@app.route('/api/formation/stats')
@login_required
def api_formation_stats():
    db = get_db()
    cur = db.cursor()
    result = {}
    for k, sql in [
        ('formations', "SELECT COUNT(*) FROM formations WHERE statut='actif'"),
        ('sessions', "SELECT COUNT(*) FROM sessions"),
        ('apprenants', "SELECT COUNT(*) FROM apprenants WHERE statut='actif'"),
        ('certificats', "SELECT COUNT(*) FROM certificats WHERE statut='valide'"),
        ('placements', "SELECT COUNT(*) FROM placements WHERE statut='actif'"),
        ('financements', "SELECT COALESCE(SUM(montant_total),0) FROM financements WHERE statut='actif'"),
    ]:
        try:
            cur.execute(sql)
            r = cur.fetchone()
            result[k] = r[0] if r else 0
        except Exception:
            result[k] = 0
    return jsonify(result)


@app.route('/api/certificats/verifier/<numero>')
def api_verifier_certificat(numero):
    """Endpoint public de vérification d'un certificat via QR."""
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.numero_certificat, c.date_emission, c.note_finale, c.mention, c.statut,
               a.prenom, a.nom, a.numero_apprenant,
               f.nom AS formation_nom
        FROM certificats c
        LEFT JOIN apprenants a ON a.id=c.apprenant_id
        LEFT JOIN formations f ON f.id=c.formation_id
        WHERE c.numero_certificat=?
    """, (numero,))
    c = cur.fetchone()
    if not c:
        return jsonify({'valide': False, 'error': 'Certificat introuvable'}), 404
    return jsonify({
        'valide': c['statut'] == 'valide',
        'numero': c['numero_certificat'],
        'apprenant': c['prenom'] + ' ' + c['nom'],
        'numero_apprenant': c['numero_apprenant'],
        'formation': c['formation_nom'],
        'note_finale': c['note_finale'],
        'mention': c['mention'],
        'date_emission': c['date_emission'],
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
