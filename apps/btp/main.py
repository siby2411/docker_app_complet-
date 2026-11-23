"""
🏗️ BTP & Chantiers — Application principale
Chantiers · Ressources · Matériaux · Sécurité · Budget · Situations · Mobile
"""
from flask import Flask, render_template_string, redirect, url_for, session, request, jsonify, Response, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import sqlite3
import os
import io
import csv

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'omega-btp-secret-2026')

DB_PATH = '/app/data/btp.db'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id, username, role, nom_complet):
        self.id = id
        self.username = username
        self.role = role
        self.nom_complet = nom_complet


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
        return User(r['id'], r['username'], r['role'], r['nom_complet'])
    return None


# ═══════════════════════════════════════════════════════════════
# LAYOUT BTP — DESIGN PRO CHANTIER
# ═══════════════════════════════════════════════════════════════

LAYOUT = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — OMEGA BTP</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,-apple-system,sans-serif}}
body{{background:#f1f5f9;color:#1e293b;font-size:14px}}
.nav{{background:linear-gradient(135deg,#1e293b,#334155);color:#fff;padding:0 22px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 3px 12px rgba(0,0,0,.2);flex-wrap:wrap;border-bottom:4px solid #f97316}}
.nav-brand{{font-weight:900;font-size:18px;display:flex;align-items:center;gap:12px;padding:16px 0;letter-spacing:-0.3px}}
.nav-brand-icon{{width:40px;height:40px;background:#f97316;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(249,115,22,.5)}}
.nav-links{{display:flex;gap:2px;flex-wrap:wrap}}
.nav-links a{{color:#cbd5e1;text-decoration:none;padding:8px 13px;border-radius:8px;font-size:12.5px;font-weight:600;transition:.2s;display:flex;align-items:center;gap:6px}}
.nav-links a:hover{{background:rgba(255,255,255,.1);color:#fff}}
.nav-links a.active{{background:#f97316;color:#fff;box-shadow:0 4px 10px rgba(249,115,22,.5)}}
.nav-user{{font-size:12.5px;display:flex;gap:10px;align-items:center;color:#cbd5e1}}
.nav-user a{{color:#fff;text-decoration:none;background:rgba(0,0,0,.3);padding:7px 14px;border-radius:8px;font-weight:600}}
.container{{max-width:1600px;margin:0 auto;padding:24px}}
h1{{color:#1e293b;margin-bottom:20px;font-size:24px;font-weight:800;letter-spacing:-0.4px}}
h1::before{{content:'';display:inline-block;width:6px;height:26px;background:#f97316;margin-right:12px;vertical-align:middle;border-radius:3px}}
h2{{color:#334155;font-size:18px;margin-bottom:14px;font-weight:700}}
.card{{background:#fff;padding:22px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:18px;border-left:4px solid #f97316}}
table{{width:100%;border-collapse:collapse}}
thead{{background:#1e293b;color:#fff}}
th{{padding:12px;text-align:left;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}}
td{{padding:11px;border-bottom:1px solid #f1f5f9;font-size:13.5px}}
tbody tr:hover{{background:#fff7ed}}
.btn{{display:inline-block;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px;border:none;cursor:pointer;transition:.15s;letter-spacing:.2px}}
.btn:hover{{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.15)}}
.btn-primary{{background:#f97316;color:#fff}}
.btn-dark{{background:#1e293b;color:#fff}}
.btn-success{{background:#10b981;color:#fff}}
.btn-danger{{background:#ef4444;color:#fff}}
.btn-warning{{background:#facc15;color:#1e293b}}
.btn-secondary{{background:#64748b;color:#fff}}
input,select,textarea{{width:100%;padding:11px 14px;border:2px solid #e2e8f0;border-radius:8px;font-size:13.5px;font-family:inherit;transition:.2s}}
input:focus,select:focus,textarea:focus{{outline:none;border-color:#f97316;box-shadow:0 0 0 3px rgba(249,115,22,.15)}}
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
.badge-orange{{background:#fed7aa;color:#c2410c}}
.badge-green{{background:#d1fae5;color:#047857}}
.badge-red{{background:#fee2e2;color:#b91c1c}}
.badge-blue{{background:#dbeafe;color:#1e40af}}
.badge-gray{{background:#e2e8f0;color:#475569}}
.badge-yellow{{background:#fef3c7;color:#b45309}}
.progress{{background:#e2e8f0;border-radius:8px;overflow:hidden;height:14px}}
.progress-bar{{height:100%;background:linear-gradient(90deg,#f97316,#ea580c);transition:.3s}}
.gantt{{display:flex;flex-direction:column;gap:8px}}
.gantt-row{{display:flex;align-items:center;gap:12px;padding:8px;background:#f8fafc;border-radius:8px}}
.gantt-label{{min-width:180px;font-weight:700;font-size:13px;color:#334155}}
.gantt-bar-container{{flex:1;position:relative;height:24px;background:#e2e8f0;border-radius:6px;overflow:hidden}}
.gantt-bar{{position:absolute;height:100%;background:linear-gradient(90deg,#f97316,#fb923c);border-radius:6px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:11px;font-weight:700}}
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-brand">
    <div class="nav-brand-icon">🏗️</div>
    <div>OMEGA BTP<span style="display:block;font-size:10px;font-weight:500;letter-spacing:2px;color:#cbd5e1">CHANTIERS · PME SÉNÉGAL</span></div>
  </div>
  <div class="nav-links">
    <a href="/" class="{a_dash}">📊 Dashboard</a>
    <a href="/chantiers" class="{a_ch}">🏗️ Chantiers</a>
    <a href="/ressources" class="{a_res}">👷 Ressources</a>
    <a href="/materiaux" class="{a_mat}">📦 Matériaux</a>
    <a href="/bons-commande" class="{a_bc}">📄 Bons Cde</a>
    <a href="/securite" class="{a_sec}">🦺 Sécurité</a>
    <a href="/budget" class="{a_bud}">💰 Budget</a>
    <a href="/situations" class="{a_sit}">📊 Situations</a>
    <a href="/factures" class="{a_fac}">🧾 Factures</a>
    <a href="/rentabilite" class="{a_ren}">📈 Rentabilité</a>
    <a href="/mobile-chef" class="{a_mob}">📱 Mobile</a>
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


def render_page(content, active='dashboard', page_title='BTP'):
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
        a_ch='active' if active == 'chantiers' else '',
        a_res='active' if active == 'ressources' else '',
        a_mat='active' if active == 'materiaux' else '',
        a_bc='active' if active == 'bons_commande' else '',
        a_sec='active' if active == 'securite' else '',
        a_bud='active' if active == 'budget' else '',
        a_sit='active' if active == 'situations' else '',
        a_fac='active' if active == 'factures' else '',
        a_ren='active' if active == 'rentabilite' else '',
        a_mob='active' if active == 'mobile' else '',
    )


@app.route('/health')
def health():
    return {'project': 'OMEGA BTP', 'service': 'btp-chantiers',
            'status': 'ok', 'timestamp': datetime.now().isoformat(), 'version': '1.0'}


LOGIN_HTML = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Connexion — OMEGA BTP</title>
<style>body{{font-family:system-ui;background:linear-gradient(135deg,#1e293b,#334155);min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0}}
.box{{background:#fff;padding:42px;border-radius:16px;box-shadow:0 25px 70px rgba(0,0,0,.4);width:100%;max-width:420px;border-top:5px solid #f97316}}
.logo{{text-align:center;font-size:56px;margin-bottom:12px}}
h1{{color:#1e293b;margin:0 0 6px;text-align:center;font-size:22px;font-weight:900;letter-spacing:-0.3px}}
.subtitle{{text-align:center;color:#64748b;font-size:12px;margin-bottom:24px;letter-spacing:1.5px;text-transform:uppercase;font-weight:600}}
input{{width:100%;padding:14px;border:2px solid #e2e8f0;border-radius:10px;margin-bottom:14px;font-size:15px;box-sizing:border-box}}
input:focus{{outline:none;border-color:#f97316;box-shadow:0 0 0 3px rgba(249,115,22,.15)}}
button{{width:100%;background:#f97316;color:#fff;padding:15px;border:none;border-radius:10px;font-weight:800;font-size:15px;cursor:pointer;letter-spacing:.5px;text-transform:uppercase}}
button:hover{{background:#ea580c}}
.err{{background:#fee2e2;color:#991b1b;padding:11px;border-radius:8px;margin-bottom:14px;font-size:13px;border-left:4px solid #ef4444}}
.hint{{margin-top:20px;padding:12px;background:#fff7ed;border-radius:8px;font-size:12px;color:#c2410c;text-align:center;border:1px dashed #fdba74}}</style></head>
<body><div class="box">
<div class="logo">🏗️</div>
<h1>OMEGA BTP</h1>
<div class="subtitle">Chantiers · PME Sénégal</div>
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
            user = User(r['id'], r['username'], r['role'], r['nom_complet'])
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
        'chantiers_actifs': sc("SELECT COUNT(*) FROM chantiers WHERE statut='en_cours'"),
        'chantiers_total': sc("SELECT COUNT(*) FROM chantiers"),
        'budget_total': sc("SELECT COALESCE(SUM(budget_initial),0) FROM chantiers WHERE statut='en_cours'"),
        'engage_total': sc("SELECT COALESCE(SUM(montant_engage),0) FROM budget_lignes"),
        'paye_total': sc("SELECT COALESCE(SUM(montant_paye),0) FROM budget_lignes"),
        'bc_en_cours': sc("SELECT COUNT(*) FROM bons_commande WHERE statut IN ('envoye','livre')"),
        'incidents_ouverts': sc("SELECT COUNT(*) FROM incidents WHERE statut='ouvert'"),
        'situations_brouillon': sc("SELECT COUNT(*) FROM situations WHERE statut='brouillon'"),
        'ressources_dispo': sc("SELECT COUNT(*) FROM ressources WHERE statut='disponible'"),
    }

    # Chantiers en cours
    cur.execute("""
        SELECT c.*, cl.nom AS client_nom, u.nom_complet AS chef_nom
        FROM chantiers c
        LEFT JOIN clients cl ON cl.id=c.client_id
        LEFT JOIN users u ON u.id=c.chef_chantier_id
        WHERE c.statut='en_cours'
        ORDER BY c.avancement_pct DESC
        LIMIT 6
    """)
    chantiers = cur.fetchall()

    ch_html = ''
    for c in chantiers:
        av = c['avancement_pct'] or 0
        av_color = '#10b981' if av >= 70 else '#f97316' if av >= 40 else '#ef4444'
        retard_jours = 0
        if c['date_fin_prevue']:
            try:
                df = datetime.strptime(c['date_fin_prevue'][:10], '%Y-%m-%d')
                if df < datetime.now() and av < 100:
                    retard_jours = (datetime.now() - df).days
            except Exception:
                pass

        ch_html += (
            '<tr><td><strong style="color:#f97316">' + str(c["code"]) + '</strong></td>'
            + '<td>' + str(c["nom"]) + '</td>'
            + '<td>' + str(c["client_nom"] or "—") + '</td>'
            + '<td>' + str(c["chef_nom"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{c["budget_initial"]:,.0f}' + ' F</td>'
            + '<td style="min-width:120px"><div class="progress"><div class="progress-bar" style="width:' + f'{av:.0f}' + '%;background:' + av_color + '"></div></div><small>' + f'{av:.0f}' + '%</small></td>'
            + ('<td><span class="badge badge-red">+' + str(retard_jours) + 'j retard</span></td>' if retard_jours > 0 else '<td><span class="badge badge-green">Dans les délais</span></td>')
            + '<td><a href="/chantiers/' + str(c["id"]) + '" class="btn btn-dark" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    # Alertes sécurité
    cur.execute("""
        SELECT i.*, c.nom AS chantier_nom
        FROM incidents i LEFT JOIN chantiers c ON c.id=i.chantier_id
        WHERE i.statut='ouvert' ORDER BY i.id DESC LIMIT 5
    """)
    incidents = cur.fetchall()
    inc_html = ''
    for i in incidents:
        grav_badge = {'mineure': 'badge-blue', 'majeure': 'badge-orange', 'critique': 'badge-red'}.get(i['gravite'], 'badge-gray')
        inc_html += (
            '<tr><td><span class="badge ' + grav_badge + '">' + str(i["gravite"]) + '</span></td>'
            + '<td>' + str(i["chantier_nom"] or "—") + '</td>'
            + '<td>' + str(i["description"]) + '</td>'
            + '<td>' + str(i["date_incident"] or "—") + '</td></tr>'
        )

    content = '<h1>🏗️ Tableau de bord BTP</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">🏗️</div><div class="kpi-label">Chantiers actifs</div><div class="kpi-value">' + str(stats["chantiers_actifs"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e293b,#334155)"><div class="kpi-icon">📋</div><div class="kpi-label">Total chantiers</div><div class="kpi-value">' + str(stats["chantiers_total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">💰</div><div class="kpi-label">Budget actif</div><div class="kpi-value" style="font-size:18px">' + f'{stats["budget_total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#facc15,#eab308);color:#1e293b"><div class="kpi-icon">📊</div><div class="kpi-label">Engagé</div><div class="kpi-value" style="font-size:18px">' + f'{stats["engage_total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Payé</div><div class="kpi-value" style="font-size:18px">' + f'{stats["paye_total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">📄</div><div class="kpi-label">BC en cours</div><div class="kpi-value">' + str(stats["bc_en_cours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">🦺</div><div class="kpi-label">Incidents</div><div class="kpi-value">' + str(stats["incidents_ouverts"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#64748b,#475569)"><div class="kpi-icon">👷</div><div class="kpi-label">Ressources dispo</div><div class="kpi-value">' + str(stats["ressources_dispo"]) + '</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:18px">'
    content += '<div class="card"><h2>🏗️ Chantiers en cours</h2>'
    content += '<table><thead><tr><th>Code</th><th>Chantier</th><th>Client</th><th>Chef</th><th style="text-align:right">Budget</th><th>Avancement</th><th>Délai</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (ch_html or '<tr><td colspan="8" style="text-align:center;color:#94a3b8;padding:30px">Aucun chantier en cours</td></tr>') + '</tbody></table></div>'

    content += '<div class="card" style="border-left-color:#ef4444"><h2>🦺 Incidents sécurité</h2>'
    content += '<table><thead><tr><th>Gravité</th><th>Chantier</th><th>Description</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (inc_html or '<tr><td colspan="4" style="text-align:center;color:#10b981;padding:30px">✅ Aucun incident</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    return render_page(content, active='dashboard', page_title='Dashboard')


# ═══════════════════════════════════════════════════════════════
# 🏗️ CHANTIERS
# ═══════════════════════════════════════════════════════════════

@app.route('/chantiers')
@login_required
def chantiers_liste():
    db = get_db()
    cur = db.cursor()
    statut_f = request.args.get('statut', '')
    q = request.args.get('q', '').strip()

    sql = """
        SELECT c.*, cl.nom AS client_nom, u.nom_complet AS chef_nom
        FROM chantiers c
        LEFT JOIN clients cl ON cl.id=c.client_id
        LEFT JOIN users u ON u.id=c.chef_chantier_id
        WHERE 1=1
    """
    params = []
    if statut_f:
        sql += " AND c.statut=?"
        params.append(statut_f)
    if q:
        sql += " AND (c.nom LIKE ? OR c.code LIKE ? OR c.ville LIKE ?)"
        params += [f'%{q}%'] * 3
    sql += " ORDER BY c.id DESC LIMIT 200"
    cur.execute(sql, params)
    chantiers = cur.fetchall()

    stats = {}
    for k, s in [
        ('total', "SELECT COUNT(*) FROM chantiers"),
        ('en_cours', "SELECT COUNT(*) FROM chantiers WHERE statut='en_cours'"),
        ('prepa', "SELECT COUNT(*) FROM chantiers WHERE statut='en_preparation'"),
        ('termine', "SELECT COUNT(*) FROM chantiers WHERE statut='termine'"),
    ]:
        cur.execute(s)
        stats[k] = cur.fetchone()[0]

    rows = ''
    for c in chantiers:
        statut_badge = {
            'en_preparation': 'badge-blue',
            'en_cours': 'badge-orange',
            'termine': 'badge-green',
            'suspendu': 'badge-red',
        }.get(c['statut'], 'badge-gray')
        av = c['avancement_pct'] or 0
        av_color = '#10b981' if av >= 70 else '#f97316' if av >= 40 else '#ef4444'
        rows += (
            '<tr><td><strong style="color:#f97316">' + str(c["code"] or "—") + '</strong></td>'
            + '<td><strong>' + str(c["nom"]) + '</strong><br><small style="color:#64748b">' + str(c["ville"] or "") + ' · ' + str(c["type"] or "") + '</small></td>'
            + '<td>' + str(c["client_nom"] or "—") + '</td>'
            + '<td>' + str(c["chef_nom"] or "—") + '</td>'
            + '<td>' + str((c["date_debut"] or "—")[:10]) + '</td>'
            + '<td>' + str((c["date_fin_prevue"] or "—")[:10]) + '</td>'
            + '<td style="text-align:right">' + f'{c["budget_initial"]:,.0f}' + ' F</td>'
            + '<td style="min-width:120px"><div class="progress"><div class="progress-bar" style="width:' + f'{av:.0f}' + '%;background:' + av_color + '"></div></div><small>' + f'{av:.0f}' + '%</small></td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></td>'
            + '<td><a href="/chantiers/' + str(c["id"]) + '" class="btn btn-dark" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🏗️ Chantiers — ' + str(len(chantiers)) + '</h1>'
    content += '<a href="/chantiers/nouveau" class="btn btn-primary">+ Nouveau chantier</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e293b,#334155)"><div class="kpi-icon">🏗️</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">🔨</div><div class="kpi-label">En cours</div><div class="kpi-value">' + str(stats["en_cours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">📋</div><div class="kpi-label">En préparation</div><div class="kpi-value">' + str(stats["prepa"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Terminés</div><div class="kpi-value">' + str(stats["termine"]) + '</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher chantier, ville..." style="max-width:400px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/chantiers" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Tous</a> '
    for s in ['en_preparation', 'en_cours', 'termine', 'suspendu']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/chantiers?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>Code</th><th>Chantier</th><th>Client</th><th>Chef</th><th>Début</th><th>Fin prévue</th>'
    content += '<th style="text-align:right">Budget</th><th>Avancement</th><th>Statut</th><th>Actions</th>'
    content += '</tr></thead><tbody>'
    content += rows or '<tr><td colspan="10" style="padding:40px;text-align:center;color:#94a3b8">Aucun chantier</td></tr>'
    content += '</tbody></table></div>'

    return render_page(content, active='chantiers', page_title='Chantiers')


@app.route('/chantiers/nouveau', methods=['GET', 'POST'])
@login_required
def chantiers_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO chantiers
                (code, nom, client_id, type, adresse, ville, latitude, longitude,
                 date_debut, date_fin_prevue, budget_initial, budget_revise,
                 statut, avancement_pct, chef_chantier_id, description, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,?,?)
            """, (None,
                  request.form.get('nom'),
                  int(request.form.get('client_id') or 0) or None,
                  request.form.get('type'),
                  request.form.get('adresse'),
                  request.form.get('ville'),
                  float(request.form.get('latitude') or 0),
                  float(request.form.get('longitude') or 0),
                  request.form.get('date_debut'),
                  request.form.get('date_fin_prevue'),
                  float(request.form.get('budget_initial') or 0),
                  float(request.form.get('budget_initial') or 0),
                  request.form.get('statut') or 'en_preparation',
                  int(request.form.get('chef_chantier_id') or 0) or None,
                  request.form.get('description'),
                  datetime.now().isoformat()))
            db.commit()
            log_action(current_user.id, 'CREATE_CHANTIER', request.form.get('nom'),
                       'chantiers', cur.lastrowid)
            flash('✅ Chantier créé', 'success')
            return redirect('/chantiers')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom FROM clients ORDER BY nom")
    clients = cur.fetchall()
    cur.execute("SELECT id, nom_complet FROM users WHERE role='chef_chantier' AND actif=1")
    chefs = cur.fetchall()

    opts_cli = ''.join('<option value="' + str(c["id"]) + '">' + str(c["nom"]) + '</option>' for c in clients)
    opts_chef = ''.join('<option value="' + str(c["id"]) + '">' + str(c["nom_complet"]) + '</option>' for c in chefs)

    content = '<h1>🏗️ Nouveau chantier</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom du chantier *</label><input type="text" name="nom" required autofocus></div>'
    content += '<div><label>Client (maitre d\'ouvrage) *</label><select name="client_id" required><option value="">— Sélectionner —</option>' + opts_cli + '</select></div>'
    content += '<div><label>Type</label><select name="type">'
    content += '<option value="batiment">Bâtiment</option>'
    content += '<option value="route">Route</option>'
    content += '<option value="logement">Logement</option>'
    content += '<option value="infrastructure">Infrastructure</option>'
    content += '<option value="ouvrage_art">Ouvrage d\'art</option>'
    content += '</select></div>'
    content += '<div><label>Ville</label><input type="text" name="ville" value="Dakar"></div>'
    content += '<div><label>Adresse</label><input type="text" name="adresse"></div>'
    content += '<div><label>Latitude GPS</label><input type="number" step="0.0001" name="latitude" value="14.6928"></div>'
    content += '<div><label>Longitude GPS</label><input type="number" step="0.0001" name="longitude" value="-17.4467"></div>'
    content += '<div><label>Date début</label><input type="date" name="date_debut" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Date fin prévue</label><input type="date" name="date_fin_prevue"></div>'
    content += '<div><label>Budget initial (FCFA) *</label><input type="number" step="100000" name="budget_initial" required value="100000000"></div>'
    content += '<div><label>Statut</label><select name="statut">'
    content += '<option value="en_preparation">En préparation</option>'
    content += '<option value="en_cours">En cours</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Chef de chantier</label><select name="chef_chantier_id"><option value="">— Aucun —</option>' + opts_chef + '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Description</label><textarea name="description" rows="3"></textarea></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer le chantier</button>'
    content += '<a href="/chantiers" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='chantiers', page_title='Nouveau chantier')


@app.route('/chantiers/<int:cid>')
@login_required
def chantiers_detail(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, cl.nom AS client_nom, cl.telephone AS client_tel, cl.email AS client_email,
               u.nom_complet AS chef_nom
        FROM chantiers c
        LEFT JOIN clients cl ON cl.id=c.client_id
        LEFT JOIN users u ON u.id=c.chef_chantier_id
        WHERE c.id=?
    """, (cid,))
    c = cur.fetchone()
    if not c:
        flash('❌ Chantier introuvable', 'error')
        return redirect('/chantiers')

    cur.execute("SELECT * FROM taches WHERE chantier_id=? ORDER BY ordre, date_debut", (cid,))
    taches = cur.fetchall()

    dates_debut = [t['date_debut'] for t in taches if t['date_debut']]
    dates_fin = [t['date_fin'] for t in taches if t['date_fin']]
    if dates_debut and dates_fin:
        try:
            min_date = datetime.strptime(min(dates_debut)[:10], '%Y-%m-%d')
            max_date = datetime.strptime(max(dates_fin)[:10], '%Y-%m-%d')
            total_jours = max(1, (max_date - min_date).days)
        except Exception:
            min_date = datetime.now()
            max_date = datetime.now() + timedelta(days=180)
            total_jours = 180
    else:
        min_date = datetime.now()
        max_date = datetime.now() + timedelta(days=180)
        total_jours = 180

    gantt_html = ''
    for t in taches:
        if not (t['date_debut'] and t['date_fin']):
            continue
        try:
            d1 = datetime.strptime(t['date_debut'][:10], '%Y-%m-%d')
            d2 = datetime.strptime(t['date_fin'][:10], '%Y-%m-%d')
            start_pct = max(0, (d1 - min_date).days / total_jours * 100)
            width_pct = max(1, min(100 - start_pct, (d2 - d1).days / total_jours * 100))
        except Exception:
            continue

        statut_color = '#10b981' if t['statut'] == 'termine' else '#f97316' if t['statut'] == 'en_cours' else '#94a3b8'

        gantt_html += '<div class="gantt-row">'
        gantt_html += '<div class="gantt-label">' + str(t["phase"] or t["nom"]) + '</div>'
        gantt_html += '<div class="gantt-bar-container">'
        gantt_html += '<div class="gantt-bar" style="left:' + f'{start_pct:.1f}' + '%;width:' + f'{width_pct:.1f}' + '%;background:' + statut_color + '">'
        gantt_html += f'{t["avancement_pct"]:.0f}' + '%'
        gantt_html += '</div></div>'
        gantt_html += '<div style="min-width:80px;font-size:12px;color:#64748b;text-align:right">' + str(t["duree_jours"]) + ' j</div>'
        gantt_html += '</div>'

    cur.execute("""
        SELECT a.*, r.nom AS ressource_nom, r.type AS ressource_type, r.cout_journalier
        FROM affectations a
        LEFT JOIN ressources r ON r.id=a.ressource_id
        WHERE a.chantier_id=? AND a.statut='active'
    """, (cid,))
    affectations = cur.fetchall()
    aff_html = ''
    for a in affectations:
        aff_html += (
            '<tr><td>' + str(a["ressource_nom"]) + '</td>'
            + '<td>' + str(a["ressource_type"]) + '</td>'
            + '<td>' + str((a["date_debut"] or "—")[:10]) + '</td>'
            + '<td>' + str((a["date_fin"] or "—")[:10]) + '</td>'
            + '<td style="text-align:right">' + f'{a["cout_total"]:,.0f}' + ' F</td></tr>'
        )

    cur.execute("SELECT * FROM budget_lignes WHERE chantier_id=? ORDER BY categorie", (cid,))
    budget = cur.fetchall()
    bud_html = ''
    total_prevu = total_engage = total_paye = 0
    for b in budget:
        total_prevu += b['montant_prevu'] or 0
        total_engage += b['montant_engage'] or 0
        total_paye += b['montant_paye'] or 0
        pct_engage = (b['montant_engage'] / b['montant_prevu'] * 100) if b['montant_prevu'] > 0 else 0
        bud_html += (
            '<tr><td>' + str(b["libelle"]) + '</td>'
            + '<td style="text-align:right">' + f'{b["montant_prevu"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;color:#f59e0b;font-weight:700">' + f'{b["montant_engage"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:700">' + f'{b["montant_paye"]:,.0f}' + ' F</td>'
            + '<td style="min-width:100px"><div class="progress"><div class="progress-bar" style="width:' + f'{min(pct_engage,100):.0f}' + '%"></div></div></td></tr>'
        )

    statut_badge = {'en_preparation': 'badge-blue', 'en_cours': 'badge-orange',
                    'termine': 'badge-green', 'suspendu': 'badge-red'}.get(c['statut'], 'badge-gray')
    av = c['avancement_pct'] or 0

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🏗️ ' + str(c["nom"]) + ' <span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></h1>'
    content += '<div><a href="/chantiers" class="btn btn-secondary">← Retour</a></div></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e293b,#334155)"><div class="kpi-label">Code</div><div class="kpi-value" style="font-size:18px">' + str(c["code"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-label">Avancement</div><div class="kpi-value">' + f'{av:.0f}' + '%</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-label">Budget</div><div class="kpi-value" style="font-size:18px">' + f'{c["budget_initial"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#facc15,#eab308);color:#1e293b"><div class="kpi-label">Engagé</div><div class="kpi-value" style="font-size:18px">' + f'{total_engage:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Payé</div><div class="kpi-value" style="font-size:18px">' + f'{total_paye:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>📋 Informations</h2><table>'
    content += '<tr><td><strong>Client</strong></td><td>' + str(c["client_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Contact</strong></td><td>' + str(c["client_tel"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Chef chantier</strong></td><td>' + str(c["chef_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Type</strong></td><td>' + str(c["type"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Adresse</strong></td><td>' + str(c["adresse"] or "—") + ', ' + str(c["ville"] or "") + '</td></tr>'
    content += '<tr><td><strong>Date début</strong></td><td>' + str((c["date_debut"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Date fin prévue</strong></td><td>' + str((c["date_fin_prevue"] or "—")[:10]) + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>💰 Budget par catégorie</h2>'
    content += '<table><thead><tr><th>Catégorie</th><th style="text-align:right">Prévu</th><th style="text-align:right">Engagé</th><th style="text-align:right">Payé</th><th>%</th></tr></thead>'
    content += '<tbody>' + (bud_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucune ligne budget</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    content += '<div class="card"><h2>📊 Planning Gantt</h2>'
    content += '<div class="gantt">' + (gantt_html or '<p style="text-align:center;color:#94a3b8;padding:20px">Aucune tâche planifiée</p>') + '</div>'
    content += '<div style="margin-top:14px;text-align:right"><a href="/chantiers/' + str(cid) + '/taches/nouvelle" class="btn btn-primary">+ Ajouter une tâche</a></div>'
    content += '</div>'

    content += '<div class="card"><h2>👷 Ressources affectées (' + str(len(affectations)) + ')</h2>'
    content += '<table><thead><tr><th>Ressource</th><th>Type</th><th>Début</th><th>Fin</th><th style="text-align:right">Coût</th></tr></thead>'
    content += '<tbody>' + (aff_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucune ressource affectée</td></tr>') + '</tbody></table>'
    content += '<div style="margin-top:14px;text-align:right"><a href="/chantiers/' + str(cid) + '/affecter" class="btn btn-primary">+ Affecter ressource</a></div>'
    content += '</div>'

    return render_page(content, active='chantiers', page_title='Chantier')


@app.route('/chantiers/<int:cid>/taches/nouvelle', methods=['GET', 'POST'])
@login_required
def taches_nouvelle(cid):
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            d1 = request.form.get('date_debut')
            d2 = request.form.get('date_fin')
            duree = 0
            if d1 and d2:
                try:
                    duree = (datetime.strptime(d2[:10], '%Y-%m-%d') - datetime.strptime(d1[:10], '%Y-%m-%d')).days
                except Exception:
                    duree = 0

            cur.execute("SELECT COALESCE(MAX(ordre),0)+1 FROM taches WHERE chantier_id=?", (cid,))
            ordre = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO taches
                (chantier_id, nom, phase, date_debut, date_fin, duree_jours,
                 avancement_pct, responsable, statut, ordre, created_at)
                VALUES (?,?,?,?,?,?,0,?,?,?,?)
            """, (cid,
                  request.form.get('nom'),
                  request.form.get('phase'),
                  d1, d2, duree,
                  request.form.get('responsable'),
                  'a_faire', ordre,
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Tâche ajoutée', 'success')
            return redirect('/chantiers/' + str(cid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>📋 Nouvelle tâche Gantt</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom de la tâche *</label><input type="text" name="nom" required autofocus></div>'
    content += '<div><label>Phase</label><input type="text" name="phase" placeholder="Fondations, Structure..."></div>'
    content += '<div><label>Responsable</label><input type="text" name="responsable"></div>'
    content += '<div><label>Date début</label><input type="date" name="date_debut" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Date fin</label><input type="date" name="date_fin"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Ajouter</button>'
    content += '<a href="/chantiers/' + str(cid) + '" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='chantiers', page_title='Nouvelle tâche')


@app.route('/chantiers/<int:cid>/affecter', methods=['GET', 'POST'])
@login_required
def chantiers_affecter(cid):
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            ressource_id = int(request.form.get('ressource_id') or 0)
            date_debut = request.form.get('date_debut')
            date_fin = request.form.get('date_fin')

            cur.execute("SELECT cout_journalier FROM ressources WHERE id=?", (ressource_id,))
            r = cur.fetchone()
            cout_j = r['cout_journalier'] if r else 0

            duree = 0
            if date_debut and date_fin:
                try:
                    duree = (datetime.strptime(date_fin[:10], '%Y-%m-%d') - datetime.strptime(date_debut[:10], '%Y-%m-%d')).days
                except Exception:
                    duree = 0
            cout_total = cout_j * max(0, duree)

            cur.execute("""
                INSERT INTO affectations
                (chantier_id, ressource_id, date_debut, date_fin, cout_total, statut, created_at)
                VALUES (?,?,?,?,?,'active',?)
            """, (cid, ressource_id, date_debut, date_fin, cout_total,
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Ressource affectée', 'success')
            return redirect('/chantiers/' + str(cid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, code, nom, type, cout_journalier FROM ressources WHERE statut='disponible'")
    ressources = cur.fetchall()
    opts = ''.join('<option value="' + str(r["id"]) + '">' + str(r["code"]) + ' — ' + str(r["nom"]) + ' (' + f'{r["cout_journalier"]:,.0f}' + ' F/jour)</option>' for r in ressources)

    content = '<h1>👷 Affecter une ressource</h1>'
    content += '<form method="post" class="card" style="max-width:600px">'
    content += '<div style="margin-bottom:16px"><label>Ressource *</label><select name="ressource_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Date début *</label><input type="date" name="date_debut" required value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div style="margin-bottom:16px"><label>Date fin *</label><input type="date" name="date_fin" required></div>'
    content += '<button type="submit" class="btn btn-success">💾 Affecter</button>'
    content += '<a href="/chantiers/' + str(cid) + '" class="btn btn-secondary" style="margin-left:8px">Annuler</a>'
    content += '</form>'
    return render_page(content, active='chantiers', page_title='Affecter ressource')


# ═══════════════════════════════════════════════════════════════
# 👷 RESSOURCES
# ═══════════════════════════════════════════════════════════════

@app.route('/ressources')
@login_required
def ressources_liste():
    db = get_db()
    cur = db.cursor()
    type_f = request.args.get('type', '')
    sql = "SELECT * FROM ressources WHERE 1=1"
    params = []
    if type_f:
        sql += " AND type=?"
        params.append(type_f)
    sql += " ORDER BY type, nom"
    cur.execute(sql, params)
    ressources = cur.fetchall()

    stats = {}
    for k, s in [
        ('total', "SELECT COUNT(*) FROM ressources"),
        ('personnel', "SELECT COUNT(*) FROM ressources WHERE type='personnel'"),
        ('engin', "SELECT COUNT(*) FROM ressources WHERE type='engin'"),
        ('dispo', "SELECT COUNT(*) FROM ressources WHERE statut='disponible'"),
    ]:
        cur.execute(s)
        stats[k] = cur.fetchone()[0]

    rows = ''
    for r in ressources:
        statut_badge = 'badge-green' if r['statut'] == 'disponible' else 'badge-orange'
        icon = '👷' if r['type'] == 'personnel' else '🚜'
        rows += (
            '<tr><td><strong>' + str(r["code"]) + '</strong></td>'
            + '<td>' + icon + ' ' + str(r["nom"]) + '</td>'
            + '<td><span class="badge badge-blue">' + str(r["type"]) + '</span></td>'
            + '<td>' + str(r["categorie"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{r["cout_journalier"]:,.0f}' + ' F/j</td>'
            + '<td style="text-align:right">' + f'{r["cout_horaire"]:,.0f}' + ' F/h</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(r["statut"]) + '</span></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👷 Ressources</h1>'
    content += '<a href="/ressources/nouvelle" class="btn btn-primary">+ Nouvelle ressource</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e293b,#334155)"><div class="kpi-icon">📊</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">👷</div><div class="kpi-label">Personnel</div><div class="kpi-value">' + str(stats["personnel"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">🚜</div><div class="kpi-label">Engins</div><div class="kpi-value">' + str(stats["engin"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Disponibles</div><div class="kpi-value">' + str(stats["dispo"]) + '</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/ressources" class="btn ' + ('btn-primary' if not type_f else 'btn-secondary') + '">Toutes</a> '
    content += '<a href="/ressources?type=personnel" class="btn ' + ('btn-primary' if type_f == 'personnel' else 'btn-secondary') + '" style="margin-left:6px">Personnel</a> '
    content += '<a href="/ressources?type=engin" class="btn ' + ('btn-primary' if type_f == 'engin' else 'btn-secondary') + '" style="margin-left:6px">Engins</a>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Nom</th><th>Type</th><th>Catégorie</th>'
    content += '<th style="text-align:right">Coût/jour</th><th style="text-align:right">Coût/heure</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucune ressource</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='ressources', page_title='Ressources')


@app.route('/ressources/nouvelle', methods=['GET', 'POST'])
@login_required
def ressources_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO ressources
                (code, nom, type, categorie, cout_journalier, cout_horaire, unite, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (request.form.get('code') or None,
                  request.form.get('nom'),
                  request.form.get('type'),
                  request.form.get('categorie'),
                  float(request.form.get('cout_journalier') or 0),
                  float(request.form.get('cout_horaire') or 0),
                  request.form.get('unite') or 'jour',
                  'disponible',
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Ressource créée', 'success')
            return redirect('/ressources')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>👷 Nouvelle ressource</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Code</label><input type="text" name="code" placeholder="PERS-001, ENG-001..." autofocus></div>'
    content += '<div><label>Type *</label><select name="type" required>'
    content += '<option value="personnel">Personnel</option>'
    content += '<option value="engin">Engin</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Nom *</label><input type="text" name="nom" required></div>'
    content += '<div><label>Catégorie</label><input type="text" name="categorie" placeholder="main_oeuvre, terrassement..."></div>'
    content += '<div><label>Unité</label><input type="text" name="unite" value="jour"></div>'
    content += '<div><label>Coût journalier (FCFA)</label><input type="number" step="100" name="cout_journalier" value="15000"></div>'
    content += '<div><label>Coût horaire (FCFA)</label><input type="number" step="100" name="cout_horaire" value="0"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/ressources" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='ressources', page_title='Nouvelle ressource')


# ═══════════════════════════════════════════════════════════════
# 📦 MATÉRIAUX
# ═══════════════════════════════════════════════════════════════

@app.route('/materiaux')
@login_required
def materiaux_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT m.*, f.nom AS fournisseur_nom
        FROM materiaux m
        LEFT JOIN fournisseurs f ON f.id=m.fournisseur_id
        ORDER BY m.categorie, m.nom
    """)
    materiaux = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM materiaux")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT categorie) FROM materiaux")
    stats['categories'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(prix_unitaire),0) FROM materiaux")
    stats['prix_moyen'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM fournisseurs")
    stats['fournisseurs'] = cur.fetchone()[0]

    rows = ''
    for m in materiaux:
        rows += (
            '<tr><td><strong>' + str(m["code"] or "—") + '</strong></td>'
            + '<td><strong>' + str(m["nom"]) + '</strong></td>'
            + '<td><span class="badge badge-blue">' + str(m["categorie"] or "—") + '</span></td>'
            + '<td>' + str(m["unite"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{m["prix_unitaire"]:,.0f}' + ' F</td>'
            + '<td>' + str(m["fournisseur_nom"] or "—") + '</td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📦 Matériaux — ' + str(len(materiaux)) + '</h1>'
    content += '<a href="/materiaux/nouveau" class="btn btn-primary">+ Nouveau matériau</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e293b,#334155)"><div class="kpi-icon">📦</div><div class="kpi-label">Total références</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">🏷️</div><div class="kpi-label">Catégories</div><div class="kpi-value">' + str(stats["categories"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">💰</div><div class="kpi-label">Prix moyen</div><div class="kpi-value" style="font-size:18px">' + f'{stats["prix_moyen"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🏢</div><div class="kpi-label">Fournisseurs</div><div class="kpi-value">' + str(stats["fournisseurs"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Matériau</th><th>Catégorie</th><th>Unité</th>'
    content += '<th style="text-align:right">Prix unitaire</th><th>Fournisseur</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="6" style="padding:40px;text-align:center;color:#94a3b8">Aucun matériau</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='materiaux', page_title='Matériaux')


@app.route('/materiaux/nouveau', methods=['GET', 'POST'])
@login_required
def materiaux_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO materiaux
                (code, nom, categorie, unite, prix_unitaire, fournisseur_id, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (request.form.get('code') or None,
                  request.form.get('nom'),
                  request.form.get('categorie'),
                  request.form.get('unite') or 'unité',
                  float(request.form.get('prix_unitaire') or 0),
                  int(request.form.get('fournisseur_id') or 0) or None,
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Matériau créé', 'success')
            return redirect('/materiaux')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom FROM fournisseurs ORDER BY nom")
    fournisseurs = cur.fetchall()
    opts_f = ''.join('<option value="' + str(f["id"]) + '">' + str(f["nom"]) + '</option>' for f in fournisseurs)

    content = '<h1>📦 Nouveau matériau</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Code</label><input type="text" name="code" placeholder="MAT-CIM-50" autofocus></div>'
    content += '<div><label>Catégorie</label><input type="text" name="categorie" placeholder="Ciment, Ferraille..."></div>'
    content += '<div style="grid-column:1/-1"><label>Nom du matériau *</label><input type="text" name="nom" required></div>'
    content += '<div><label>Unité</label><input type="text" name="unite" value="unité"></div>'
    content += '<div><label>Prix unitaire (FCFA) *</label><input type="number" step="100" name="prix_unitaire" required value="5000"></div>'
    content += '<div style="grid-column:1/-1"><label>Fournisseur</label><select name="fournisseur_id"><option value="">— Aucun —</option>' + opts_f + '</select></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/materiaux" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='materiaux', page_title='Nouveau matériau')


# ═══════════════════════════════════════════════════════════════
# 📄 BONS DE COMMANDE
# ═══════════════════════════════════════════════════════════════

@app.route('/bons-commande')
@login_required
def bons_commande_liste():
    db = get_db()
    cur = db.cursor()
    statut_f = request.args.get('statut', '')

    sql = """
        SELECT bc.*, c.nom AS chantier_nom, f.nom AS fournisseur_nom
        FROM bons_commande bc
        LEFT JOIN chantiers c ON c.id=bc.chantier_id
        LEFT JOIN fournisseurs f ON f.id=bc.fournisseur_id
        WHERE 1=1
    """
    params = []
    if statut_f:
        sql += " AND bc.statut=?"
        params.append(statut_f)
    sql += " ORDER BY bc.id DESC LIMIT 200"
    cur.execute(sql, params)
    bcs = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM bons_commande")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant_ttc),0) FROM bons_commande")
    stats['montant'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM bons_commande WHERE statut='livre'")
    stats['livres'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM bons_commande WHERE statut='envoye'")
    stats['attente'] = cur.fetchone()[0]

    rows = ''
    for b in bcs:
        statut_badge = {
            'brouillon': 'badge-gray',
            'envoye': 'badge-blue',
            'livre': 'badge-green',
            'annule': 'badge-red',
        }.get(b['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong style="color:#f97316">' + str(b["numero"] or "—") + '</strong></td>'
            + '<td>' + str(b["chantier_nom"] or "—") + '</td>'
            + '<td>' + str(b["fournisseur_nom"] or "—") + '</td>'
            + '<td>' + str((b["date_commande"] or "—")[:10]) + '</td>'
            + '<td style="text-align:right">' + f'{b["montant_ttc"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(b["statut"]) + '</span></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📄 Bons de commande — ' + str(len(bcs)) + '</h1>'
    content += '<a href="/bons-commande/nouveau" class="btn btn-primary">+ Nouveau BC</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e293b,#334155)"><div class="kpi-icon">📄</div><div class="kpi-label">Total BC</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">💰</div><div class="kpi-label">Montant total</div><div class="kpi-value" style="font-size:18px">' + f'{stats["montant"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Livrés</div><div class="kpi-value">' + str(stats["livres"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">📮</div><div class="kpi-label">En attente</div><div class="kpi-value">' + str(stats["attente"]) + '</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/bons-commande" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Tous</a> '
    for s in ['brouillon', 'envoye', 'livre', 'annule']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/bons-commande?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° BC</th><th>Chantier</th><th>Fournisseur</th><th>Date</th>'
    content += '<th style="text-align:right">Montant TTC</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="6" style="padding:40px;text-align:center;color:#94a3b8">Aucun bon de commande</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='bons_commande', page_title='Bons de commande')


@app.route('/bons-commande/nouveau', methods=['GET', 'POST'])
@login_required
def bons_commande_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            montant_ht = float(request.form.get('montant_ht') or 0)
            tva = montant_ht * 0.18
            cur.execute("""
                INSERT INTO bons_commande
                (numero, chantier_id, fournisseur_id, date_commande, date_livraison_prevue,
                 montant_ht, tva, montant_ttc, statut, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (None,
                  int(request.form.get('chantier_id') or 0),
                  int(request.form.get('fournisseur_id') or 0),
                  request.form.get('date_commande') or datetime.now().strftime('%Y-%m-%d'),
                  request.form.get('date_livraison_prevue'),
                  montant_ht, tva, montant_ht + tva,
                  request.form.get('statut') or 'brouillon',
                  request.form.get('notes'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Bon de commande créé', 'success')
            return redirect('/bons-commande')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom, code FROM chantiers WHERE statut IN ('en_preparation','en_cours')")
    chantiers = cur.fetchall()
    cur.execute("SELECT id, nom FROM fournisseurs ORDER BY nom")
    fournisseurs = cur.fetchall()

    opts_ch = ''.join('<option value="' + str(c["id"]) + '">' + str(c["code"] or "") + ' — ' + str(c["nom"]) + '</option>' for c in chantiers)
    opts_f = ''.join('<option value="' + str(f["id"]) + '">' + str(f["nom"]) + '</option>' for f in fournisseurs)

    content = '<h1>📄 Nouveau bon de commande</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Chantier *</label><select name="chantier_id" required><option value="">— Sélectionner —</option>' + opts_ch + '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Fournisseur *</label><select name="fournisseur_id" required><option value="">— Sélectionner —</option>' + opts_f + '</select></div>'
    content += '<div><label>Date commande</label><input type="date" name="date_commande" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Date livraison prévue</label><input type="date" name="date_livraison_prevue"></div>'
    content += '<div><label>Montant HT (FCFA) *</label><input type="number" step="1000" name="montant_ht" required value="1000000"></div>'
    content += '<div><label>Statut</label><select name="statut">'
    content += '<option value="brouillon">Brouillon</option>'
    content += '<option value="envoye">Envoyé</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Notes</label><textarea name="notes" rows="3"></textarea></div>'
    content += '</div>'
    content += '<div style="background:#fff7ed;padding:12px;border-radius:8px;margin-top:16px;font-size:12.5px;color:#c2410c">💡 TVA 18% et montant TTC calculés automatiquement</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/bons-commande" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='bons_commande', page_title='Nouveau BC')


# ═══════════════════════════════════════════════════════════════
# 🦺 SÉCURITÉ
# ═══════════════════════════════════════════════════════════════

@app.route('/securite')
@login_required
def securite_dashboard():
    db = get_db()
    cur = db.cursor()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM incidents")
    stats['incidents'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM incidents WHERE statut='ouvert'")
    stats['ouverts'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM epi_dotations")
    stats['epi'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM formations_securite")
    stats['formations'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM incidents WHERE gravite='critique'")
    stats['critiques'] = cur.fetchone()[0]

    # Incidents récents
    cur.execute("""
        SELECT i.*, c.nom AS chantier_nom
        FROM incidents i LEFT JOIN chantiers c ON c.id=i.chantier_id
        ORDER BY i.id DESC LIMIT 10
    """)
    incidents = cur.fetchall()
    inc_html = ''
    for i in incidents:
        grav_badge = {'mineure': 'badge-blue', 'majeure': 'badge-orange', 'critique': 'badge-red'}.get(i['gravite'], 'badge-gray')
        statut_badge = 'badge-red' if i['statut'] == 'ouvert' else 'badge-green'
        inc_html += (
            '<tr><td><span class="badge ' + grav_badge + '">' + str(i["gravite"]) + '</span></td>'
            + '<td>' + str(i["chantier_nom"] or "—") + '</td>'
            + '<td>' + str(i["description"]) + '</td>'
            + '<td>' + str(i["date_incident"] or "—") + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(i["statut"]) + '</span></td></tr>'
        )

    # Formations
    cur.execute("""
        SELECT f.*, c.nom AS chantier_nom
        FROM formations_securite f LEFT JOIN chantiers c ON c.id=f.chantier_id
        ORDER BY f.id DESC LIMIT 5
    """)
    formations = cur.fetchall()
    form_html = ''
    for f in formations:
        form_html += (
            '<tr><td>' + str(f["theme"]) + '</td>'
            + '<td>' + str(f["chantier_nom"] or "—") + '</td>'
            + '<td>' + str(f["date_formation"] or "—") + '</td>'
            + '<td style="text-align:center">' + str(f["nb_participants"]) + '</td>'
            + '<td style="text-align:center">' + str(f["duree_heures"]) + 'h</td></tr>'
        )

    content = '<h1>🦺 Sécurité & Prévention</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e293b,#334155)"><div class="kpi-icon">🦺</div><div class="kpi-label">Total incidents</div><div class="kpi-value">' + str(stats["incidents"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">🚨</div><div class="kpi-label">Ouverts</div><div class="kpi-value">' + str(stats["ouverts"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">⚠️</div><div class="kpi-label">Critiques</div><div class="kpi-value">' + str(stats["critiques"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">👷</div><div class="kpi-label">EPI distribués</div><div class="kpi-value">' + str(stats["epi"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🎓</div><div class="kpi-label">Formations</div><div class="kpi-value">' + str(stats["formations"]) + '</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:18px">'
    content += '<div class="card"><h2>🚨 Incidents récents</h2>'
    content += '<table><thead><tr><th>Gravité</th><th>Chantier</th><th>Description</th><th>Date</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (inc_html or '<tr><td colspan="5" style="text-align:center;color:#10b981;padding:30px">✅ Aucun incident</td></tr>') + '</tbody></table>'
    content += '<div style="margin-top:14px;text-align:right"><a href="/securite/incidents/nouveau" class="btn btn-danger">+ Déclarer un incident</a></div></div>'

    content += '<div class="card"><h2>🎓 Formations</h2>'
    content += '<table><thead><tr><th>Thème</th><th>Chantier</th><th>Date</th><th>Nb</th><th>Durée</th></tr></thead>'
    content += '<tbody>' + (form_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucune formation</td></tr>') + '</tbody></table>'
    content += '<div style="margin-top:14px;text-align:right"><a href="/securite/formations/nouvelle" class="btn btn-primary">+ Nouvelle formation</a></div></div>'
    content += '</div>'

    return render_page(content, active='securite', page_title='Sécurité')


@app.route('/securite/incidents/nouveau', methods=['GET', 'POST'])
@login_required
def incidents_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO incidents
                (chantier_id, date_incident, gravite, description, personne_impliquee,
                 action_corrective, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (int(request.form.get('chantier_id') or 0),
                  request.form.get('date_incident') or datetime.now().strftime('%Y-%m-%d'),
                  request.form.get('gravite'),
                  request.form.get('description'),
                  request.form.get('personne_impliquee'),
                  request.form.get('action_corrective'),
                  'ouvert',
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Incident déclaré', 'success')
            return redirect('/securite')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom FROM chantiers ORDER BY nom")
    chantiers = cur.fetchall()
    opts_ch = ''.join('<option value="' + str(c["id"]) + '">' + str(c["nom"]) + '</option>' for c in chantiers)

    content = '<h1>🚨 Déclarer un incident</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="margin-bottom:16px"><label>Chantier *</label><select name="chantier_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_ch + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Date incident</label>'
    content += '<input type="date" name="date_incident" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div style="margin-bottom:16px"><label>Gravité *</label><select name="gravite" required>'
    content += '<option value="mineure">🟦 Mineure</option>'
    content += '<option value="majeure">🟧 Majeure</option>'
    content += '<option value="critique">🟥 Critique</option>'
    content += '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Description *</label>'
    content += '<textarea name="description" rows="3" required autofocus></textarea></div>'
    content += '<div style="margin-bottom:16px"><label>Personne impliquée</label>'
    content += '<input type="text" name="personne_impliquee"></div>'
    content += '<div style="margin-bottom:16px"><label>Action corrective</label>'
    content += '<textarea name="action_corrective" rows="3"></textarea></div>'
    content += '<button type="submit" class="btn btn-danger">🚨 Déclarer</button>'
    content += '<a href="/securite" class="btn btn-secondary" style="margin-left:8px">Annuler</a>'
    content += '</form>'
    return render_page(content, active='securite', page_title='Incident')


@app.route('/securite/formations/nouvelle', methods=['GET', 'POST'])
@login_required
def formations_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO formations_securite
                (chantier_id, theme, formateur, date_formation, nb_participants, duree_heures, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (int(request.form.get('chantier_id') or 0) or None,
                  request.form.get('theme'),
                  request.form.get('formateur'),
                  request.form.get('date_formation'),
                  int(request.form.get('nb_participants') or 0),
                  float(request.form.get('duree_heures') or 0),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Formation enregistrée', 'success')
            return redirect('/securite')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom FROM chantiers ORDER BY nom")
    chantiers = cur.fetchall()
    opts_ch = ''.join('<option value="' + str(c["id"]) + '">' + str(c["nom"]) + '</option>' for c in chantiers)

    content = '<h1>🎓 Nouvelle formation sécurité</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="margin-bottom:16px"><label>Chantier</label><select name="chantier_id">'
    content += '<option value="">— Aucun —</option>' + opts_ch + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Thème *</label>'
    content += '<input type="text" name="theme" required placeholder="Port des EPI, Travail en hauteur..." autofocus></div>'
    content += '<div style="margin-bottom:16px"><label>Formateur</label>'
    content += '<input type="text" name="formateur"></div>'
    content += '<div style="margin-bottom:16px"><label>Date formation</label>'
    content += '<input type="date" name="date_formation" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Nb participants</label><input type="number" name="nb_participants" value="10"></div>'
    content += '<div><label>Durée (heures)</label><input type="number" step="0.5" name="duree_heures" value="4"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Enregistrer</button>'
    content += '<a href="/securite" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='securite', page_title='Formation sécurité')


# ═══════════════════════════════════════════════════════════════
# 📮 LIVRAISONS
# ═══════════════════════════════════════════════════════════════

@app.route('/livraisons')
@login_required
def livraisons_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT l.*, bc.numero AS bc_numero, c.nom AS chantier_nom, f.nom AS fournisseur_nom
        FROM livraisons l
        LEFT JOIN bons_commande bc ON bc.id=l.bc_id
        LEFT JOIN chantiers c ON c.id=l.chantier_id
        LEFT JOIN fournisseurs f ON f.id=l.fournisseur_id
        ORDER BY l.id DESC LIMIT 200
    """)
    livraisons = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM livraisons")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM livraisons WHERE statut='recu'")
    stats['recues'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM livraisons WHERE statut='attente'")
    stats['attente'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM livraisons WHERE statut='refuse'")
    stats['refusees'] = cur.fetchone()[0]

    rows = ''
    for l in livraisons:
        statut_badge = {
            'recu': 'badge-green',
            'attente': 'badge-blue',
            'refuse': 'badge-red',
            'partiel': 'badge-orange',
        }.get(l['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong>' + str(l["numero"] or "—") + '</strong></td>'
            + '<td>' + str(l["bc_numero"] or "—") + '</td>'
            + '<td>' + str(l["chantier_nom"] or "—") + '</td>'
            + '<td>' + str(l["fournisseur_nom"] or "—") + '</td>'
            + '<td>' + str((l["date_livraison"] or "—")[:10]) + '</td>'
            + '<td>' + str(l["numero_bon"] or "—") + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(l["statut"]) + '</span></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📮 Livraisons — ' + str(len(livraisons)) + '</h1>'
    content += '<a href="/livraisons/nouvelle" class="btn btn-primary">+ Nouvelle livraison</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e293b,#334155)"><div class="kpi-icon">📮</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Reçues</div><div class="kpi-value">' + str(stats["recues"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">⏳</div><div class="kpi-label">En attente</div><div class="kpi-value">' + str(stats["attente"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">❌</div><div class="kpi-label">Refusées</div><div class="kpi-value">' + str(stats["refusees"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Livraison</th><th>N° BC</th><th>Chantier</th><th>Fournisseur</th>'
    content += '<th>Date livraison</th><th>N° bon</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucune livraison</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='livraisons', page_title='Livraisons')


@app.route('/livraisons/nouvelle', methods=['GET', 'POST'])
@login_required
def livraisons_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            bc_id = int(request.form.get('bc_id') or 0)
            chantier_id = None
            fournisseur_id = None
            if bc_id:
                cur.execute("SELECT chantier_id, fournisseur_id FROM bons_commande WHERE id=?", (bc_id,))
                r = cur.fetchone()
                if r:
                    chantier_id = r['chantier_id']
                    fournisseur_id = r['fournisseur_id']

            cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM livraisons")
            nid = cur.fetchone()[0]
            numero = 'LIV-' + datetime.now().strftime('%Y%m') + '-' + f'{nid:04d}'

            cur.execute("""
                INSERT INTO livraisons
                (numero, bc_id, chantier_id, fournisseur_id, date_livraison,
                 numero_bon, statut, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (numero, bc_id or None, chantier_id, fournisseur_id,
                  request.form.get('date_livraison') or datetime.now().strftime('%Y-%m-%d'),
                  request.form.get('numero_bon'),
                  request.form.get('statut') or 'recu',
                  request.form.get('notes'),
                  datetime.now().isoformat()))
            db.commit()

            # Si livré, marquer le BC comme livré
            if bc_id and request.form.get('statut') == 'recu':
                cur.execute("UPDATE bons_commande SET statut='livre', date_livraison_reelle=? WHERE id=?",
                            (datetime.now().strftime('%Y-%m-%d'), bc_id))
                db.commit()

            flash('✅ Livraison enregistrée — N° ' + numero, 'success')
            return redirect('/livraisons')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("""
        SELECT bc.id, bc.numero, c.nom AS chantier_nom, f.nom AS fournisseur_nom
        FROM bons_commande bc
        LEFT JOIN chantiers c ON c.id=bc.chantier_id
        LEFT JOIN fournisseurs f ON f.id=bc.fournisseur_id
        WHERE bc.statut IN ('envoye', 'brouillon')
        ORDER BY bc.id DESC LIMIT 100
    """)
    bcs = cur.fetchall()
    opts_bc = ''.join('<option value="' + str(b["id"]) + '">' + str(b["numero"]) + ' — ' + str(b["chantier_nom"] or "") + ' (' + str(b["fournisseur_nom"] or "") + ')</option>' for b in bcs)

    content = '<h1>📮 Nouvelle livraison</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="margin-bottom:16px"><label>Bon de commande *</label><select name="bc_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_bc + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Date livraison</label>'
    content += '<input type="date" name="date_livraison" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div style="margin-bottom:16px"><label>N° bon de livraison</label>'
    content += '<input type="text" name="numero_bon" placeholder="BL-2026-XXXX" autofocus></div>'
    content += '<div style="margin-bottom:16px"><label>Statut</label><select name="statut">'
    content += '<option value="recu">✅ Reçu</option>'
    content += '<option value="partiel">🟧 Partiel</option>'
    content += '<option value="attente">⏳ En attente</option>'
    content += '<option value="refuse">❌ Refusé</option>'
    content += '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Notes</label>'
    content += '<textarea name="notes" rows="3"></textarea></div>'
    content += '<button type="submit" class="btn btn-success">💾 Enregistrer</button>'
    content += '<a href="/livraisons" class="btn btn-secondary" style="margin-left:8px">Annuler</a>'
    content += '</form>'
    return render_page(content, active='livraisons', page_title='Nouvelle livraison')


# ═══════════════════════════════════════════════════════════════
# 💰 BUDGET
# ═══════════════════════════════════════════════════════════════

@app.route('/budget')
@login_required
def budget_dashboard():
    db = get_db()
    cur = db.cursor()

    def sc(sql, default=0):
        cur.execute(sql)
        r = cur.fetchone()
        return r[0] if r and r[0] is not None else default

    stats = {
        'budget_total': sc("SELECT COALESCE(SUM(budget_initial),0) FROM chantiers WHERE statut IN ('en_preparation','en_cours')"),
        'prevu_total': sc("SELECT COALESCE(SUM(montant_prevu),0) FROM budget_lignes"),
        'engage_total': sc("SELECT COALESCE(SUM(montant_engage),0) FROM budget_lignes"),
        'paye_total': sc("SELECT COALESCE(SUM(montant_paye),0) FROM budget_lignes"),
        'nb_chantiers': sc("SELECT COUNT(*) FROM chantiers"),
    }

    pct_engage = (stats['engage_total'] / stats['prevu_total'] * 100) if stats['prevu_total'] > 0 else 0
    pct_paye = (stats['paye_total'] / stats['prevu_total'] * 100) if stats['prevu_total'] > 0 else 0

    # Budget par chantier
    cur.execute("""
        SELECT c.id, c.code, c.nom, c.budget_initial, c.avancement_pct,
               COALESCE(SUM(b.montant_prevu),0) AS prevu,
               COALESCE(SUM(b.montant_engage),0) AS engage,
               COALESCE(SUM(b.montant_paye),0) AS paye
        FROM chantiers c
        LEFT JOIN budget_lignes b ON b.chantier_id=c.id
        WHERE c.statut IN ('en_preparation','en_cours')
        GROUP BY c.id
        ORDER BY c.budget_initial DESC
    """)
    chantiers = cur.fetchall()

    rows = ''
    for c in chantiers:
        engage = c['engage'] or 0
        prevu = c['prevu'] or 0
        pct = (engage / prevu * 100) if prevu > 0 else 0
        color = '#ef4444' if pct > 100 else '#f97316' if pct > 80 else '#10b981'
        rows += (
            '<tr><td><strong style="color:#f97316">' + str(c["code"] or "—") + '</strong></td>'
            + '<td>' + str(c["nom"]) + '</td>'
            + '<td style="text-align:right">' + f'{c["prevu"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;color:#f59e0b;font-weight:700">' + f'{c["engage"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:700">' + f'{c["paye"]:,.0f}' + ' F</td>'
            + '<td style="min-width:120px"><div class="progress"><div class="progress-bar" style="width:' + f'{min(pct,100):.0f}' + '%;background:' + color + '"></div></div><small>' + f'{pct:.0f}' + '%</small></td>'
            + '<td><a href="/chantiers/' + str(c["id"]) + '" class="btn btn-dark" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<h1>💰 Suivi budgétaire</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e293b,#334155)"><div class="kpi-icon">💰</div><div class="kpi-label">Budget total</div><div class="kpi-value" style="font-size:18px">' + f'{stats["budget_total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">📊</div><div class="kpi-label">Prévu lignes</div><div class="kpi-value" style="font-size:18px">' + f'{stats["prevu_total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">📈</div><div class="kpi-label">Engagé (' + f'{pct_engage:.0f}' + '%)</div><div class="kpi-value" style="font-size:18px">' + f'{stats["engage_total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Payé (' + f'{pct_paye:.0f}' + '%)</div><div class="kpi-value" style="font-size:18px">' + f'{stats["paye_total"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Chantier</th>'
    content += '<th style="text-align:right">Prévu</th><th style="text-align:right">Engagé</th><th style="text-align:right">Payé</th>'
    content += '<th>Consommation</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucun chantier actif</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='budget', page_title='Budget')


# ═══════════════════════════════════════════════════════════════
# 📊 SITUATIONS DE TRAVAUX
# ═══════════════════════════════════════════════════════════════

@app.route('/situations')
@login_required
def situations_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.*, c.nom AS chantier_nom, c.code AS chantier_code
        FROM situations s
        LEFT JOIN chantiers c ON c.id=s.chantier_id
        ORDER BY s.id DESC LIMIT 200
    """)
    situations = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM situations")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant_net),0) FROM situations")
    stats['montant'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM situations WHERE statut='validee'")
    stats['validees'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM situations WHERE statut='brouillon'")
    stats['brouillon'] = cur.fetchone()[0]

    rows = ''
    for s in situations:
        statut_badge = {
            'brouillon': 'badge-gray',
            'validee': 'badge-blue',
            'facturee': 'badge-green',
        }.get(s['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong style="color:#f97316">' + str(s["numero"] or "—") + '</strong></td>'
            + '<td>' + str(s["chantier_code"] or "") + ' — ' + str(s["chantier_nom"] or "") + '</td>'
            + '<td style="text-align:center">N° ' + str(s["numero_situation"]) + '</td>'
            + '<td>' + str((s["date_situation"] or "—")[:10]) + '</td>'
            + '<td style="text-align:center">' + f'{s["avancement_pct"]:.0f}' + '%</td>'
            + '<td style="text-align:right">' + f'{s["montant_cette_situation"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:700">' + f'{s["montant_net"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(s["statut"]) + '</span></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📊 Situations de travaux — ' + str(len(situations)) + '</h1>'
    content += '<a href="/situations/nouvelle" class="btn btn-primary">+ Nouvelle situation</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e293b,#334155)"><div class="kpi-icon">📊</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">💰</div><div class="kpi-label">Montant cumulé</div><div class="kpi-value" style="font-size:18px">' + f'{stats["montant"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">✅</div><div class="kpi-label">Validées</div><div class="kpi-value">' + str(stats["validees"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#64748b,#475569)"><div class="kpi-icon">✏️</div><div class="kpi-label">Brouillon</div><div class="kpi-value">' + str(stats["brouillon"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Situation</th><th>Chantier</th><th style="text-align:center">N°</th>'
    content += '<th>Date</th><th style="text-align:center">Avancement</th>'
    content += '<th style="text-align:right">Montant situation</th><th style="text-align:right">Net à payer</th>'
    content += '<th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucune situation</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='situations', page_title='Situations')


@app.route('/situations/nouvelle', methods=['GET', 'POST'])
@login_required
def situations_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            chantier_id = int(request.form.get('chantier_id') or 0)
            avancement = float(request.form.get('avancement_pct') or 0)

            cur.execute("SELECT budget_initial FROM chantiers WHERE id=?", (chantier_id,))
            r = cur.fetchone()
            budget = r['budget_initial'] if r else 0

            # Numéro de situation (max + 1 pour ce chantier)
            cur.execute("SELECT COALESCE(MAX(numero_situation),0)+1 FROM situations WHERE chantier_id=?", (chantier_id,))
            num_sit = cur.fetchone()[0]

            # Montant travaux cumulé
            montant_travaux = budget * avancement / 100

            # Montant précédent (max cumulé)
            cur.execute("SELECT COALESCE(MAX(montant_travaux),0) FROM situations WHERE chantier_id=?", (chantier_id,))
            montant_prec = cur.fetchone()[0]

            montant_sit = montant_travaux - montant_prec
            retenue = montant_sit * 0.05  # 5% retenue de garantie
            montant_net = montant_sit - retenue

            cur.execute("""
                INSERT INTO situations
                (numero, chantier_id, numero_situation, date_situation, avancement_pct,
                 montant_travaux, montant_precedent, montant_cette_situation,
                 retenue_garantie, montant_net, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None, chantier_id, num_sit,
                  request.form.get('date_situation') or datetime.now().strftime('%Y-%m-%d'),
                  avancement, montant_travaux, montant_prec, montant_sit,
                  retenue, montant_net,
                  request.form.get('statut') or 'brouillon',
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Situation créée — N° ' + str(num_sit), 'success')
            return redirect('/situations')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, code, nom, budget_initial FROM chantiers WHERE statut IN ('en_cours','en_preparation')")
    chantiers = cur.fetchall()
    opts_ch = ''.join('<option value="' + str(c["id"]) + '">' + str(c["code"] or "") + ' — ' + str(c["nom"]) + ' (' + f'{c["budget_initial"]:,.0f}' + ' F)</option>' for c in chantiers)

    content = '<h1>📊 Nouvelle situation de travaux</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="margin-bottom:16px"><label>Chantier *</label><select name="chantier_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_ch + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Date situation</label>'
    content += '<input type="date" name="date_situation" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div style="margin-bottom:16px"><label>Avancement cumulé (%) *</label>'
    content += '<input type="number" step="0.1" name="avancement_pct" required value="20" min="0" max="100" autofocus></div>'
    content += '<div style="margin-bottom:16px"><label>Statut</label><select name="statut">'
    content += '<option value="brouillon">Brouillon</option>'
    content += '<option value="validee">Validée</option>'
    content += '</select></div>'
    content += '<div style="background:#fff7ed;padding:12px;border-radius:8px;font-size:12.5px;color:#c2410c">💡 Montant travaux, retenue garantie (5%) et net à payer sont calculés automatiquement</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/situations" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='situations', page_title='Nouvelle situation')


# ═══════════════════════════════════════════════════════════════
# 🧾 FACTURES
# ═══════════════════════════════════════════════════════════════

@app.route('/factures')
@login_required
def factures_liste():
    db = get_db()
    cur = db.cursor()
    statut_f = request.args.get('statut', '')

    sql = """
        SELECT f.*, c.nom AS chantier_nom, cl.nom AS client_nom
        FROM factures f
        LEFT JOIN chantiers c ON c.id=f.chantier_id
        LEFT JOIN clients cl ON cl.id=f.client_id
        WHERE 1=1
    """
    params = []
    if statut_f:
        sql += " AND f.statut=?"
        params.append(statut_f)
    sql += " ORDER BY f.id DESC LIMIT 200"
    cur.execute(sql, params)
    factures = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM factures")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant_ttc),0) FROM factures")
    stats['montant'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant_paye),0) FROM factures")
    stats['paye'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant_ttc - montant_paye),0) FROM factures WHERE statut != 'payee'")
    stats['solde'] = cur.fetchone()[0]

    rows = ''
    for f in factures:
        statut_badge = {
            'emise': 'badge-blue',
            'payee': 'badge-green',
            'impayee': 'badge-red',
            'partiel': 'badge-orange',
        }.get(f['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong style="color:#f97316">' + str(f["numero"] or "—") + '</strong></td>'
            + '<td>' + str(f["chantier_nom"] or "—") + '</td>'
            + '<td>' + str(f["client_nom"] or "—") + '</td>'
            + '<td>' + str((f["date_facture"] or "—")[:10]) + '</td>'
            + '<td style="text-align:right">' + f'{f["montant_ttc"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:700">' + f'{f["montant_paye"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;color:#ef4444;font-weight:700">' + f'{f["montant_ttc"] - f["montant_paye"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(f["statut"]) + '</span></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🧾 Factures — ' + str(len(factures)) + '</h1>'
    content += '<a href="/factures/nouvelle" class="btn btn-primary">+ Nouvelle facture</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e293b,#334155)"><div class="kpi-icon">🧾</div><div class="kpi-label">Total factures</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">💰</div><div class="kpi-label">Montant facturé</div><div class="kpi-value" style="font-size:18px">' + f'{stats["montant"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Encaissé</div><div class="kpi-value" style="font-size:18px">' + f'{stats["paye"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">⚠️</div><div class="kpi-label">Solde dû</div><div class="kpi-value" style="font-size:18px">' + f'{stats["solde"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/factures" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Toutes</a> '
    for s in ['emise', 'payee', 'impayee', 'partiel']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/factures?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Facture</th><th>Chantier</th><th>Client</th><th>Date</th>'
    content += '<th style="text-align:right">TTC</th><th style="text-align:right">Payé</th><th style="text-align:right">Solde</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucune facture</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='factures', page_title='Factures')


@app.route('/factures/nouvelle', methods=['GET', 'POST'])
@login_required
def factures_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            chantier_id = int(request.form.get('chantier_id') or 0)
            situation_id = int(request.form.get('situation_id') or 0) or None

            # Client auto depuis chantier
            cur.execute("SELECT client_id FROM chantiers WHERE id=?", (chantier_id,))
            r = cur.fetchone()
            client_id = r['client_id'] if r else None

            montant_ht = float(request.form.get('montant_ht') or 0)
            tva = montant_ht * 0.18

            cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM factures")
            nid = cur.fetchone()[0]
            numero = 'FAC-' + datetime.now().strftime('%Y%m') + '-' + f'{nid:04d}'

            cur.execute("""
                INSERT INTO factures
                (numero, chantier_id, client_id, situation_id, date_facture, date_echeance,
                 montant_ht, tva, montant_ttc, montant_paye, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,0,?,?)
            """, (numero, chantier_id, client_id, situation_id,
                  request.form.get('date_facture') or datetime.now().strftime('%Y-%m-%d'),
                  request.form.get('date_echeance'),
                  montant_ht, tva, montant_ht + tva,
                  request.form.get('statut') or 'emise',
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Facture créée — ' + numero, 'success')
            return redirect('/factures')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, code, nom FROM chantiers WHERE statut IN ('en_cours','en_preparation')")
    chantiers = cur.fetchall()
    cur.execute("SELECT id, numero, montant_net FROM situations WHERE statut IN ('validee','brouillon') LIMIT 100")
    situations = cur.fetchall()

    opts_ch = ''.join('<option value="' + str(c["id"]) + '">' + str(c["code"] or "") + ' — ' + str(c["nom"]) + '</option>' for c in chantiers)
    opts_sit = '<option value="">— Aucune —</option>' + ''.join('<option value="' + str(s["id"]) + '">' + str(s["numero"]) + ' — ' + f'{s["montant_net"]:,.0f}' + ' F</option>' for s in situations)

    content = '<h1>🧾 Nouvelle facture</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="margin-bottom:16px"><label>Chantier *</label><select name="chantier_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_ch + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Situation liée</label><select name="situation_id">' + opts_sit + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Date facture</label>'
    content += '<input type="date" name="date_facture" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div style="margin-bottom:16px"><label>Date échéance</label>'
    content += '<input type="date" name="date_echeance" value="' + (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d') + '"></div>'
    content += '<div style="margin-bottom:16px"><label>Montant HT (FCFA) *</label>'
    content += '<input type="number" step="1000" name="montant_ht" required value="10000000" autofocus></div>'
    content += '<div style="margin-bottom:16px"><label>Statut</label><select name="statut">'
    content += '<option value="emise">Émise</option>'
    content += '<option value="payee">Payée</option>'
    content += '</select></div>'
    content += '<div style="background:#fff7ed;padding:12px;border-radius:8px;font-size:12.5px;color:#c2410c">💡 TVA 18% et TTC calculés automatiquement</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer la facture</button>'
    content += '<a href="/factures" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='factures', page_title='Nouvelle facture')


# ═══════════════════════════════════════════════════════════════
# 📈 RENTABILITÉ
# ═══════════════════════════════════════════════════════════════

@app.route('/rentabilite')
@login_required
def rentabilite_index():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT c.id, c.code, c.nom, c.budget_initial, c.avancement_pct, c.statut,
               COALESCE((SELECT SUM(montant_engage) FROM budget_lignes WHERE chantier_id=c.id), 0) AS cout_engage,
               COALESCE((SELECT SUM(montant_paye) FROM budget_lignes WHERE chantier_id=c.id), 0) AS cout_paye,
               COALESCE((SELECT SUM(montant_travaux) FROM situations WHERE chantier_id=c.id), 0) AS travaux_realises,
               COALESCE((SELECT SUM(montant_ttc) FROM factures WHERE chantier_id=c.id), 0) AS facture_client,
               COALESCE((SELECT SUM(montant_paye) FROM factures WHERE chantier_id=c.id), 0) AS encaisse
        FROM chantiers c
        ORDER BY c.budget_initial DESC
    """)
    chantiers = cur.fetchall()

    total_budget = total_cout = total_fact = total_marge = 0

    rows = ''
    for c in chantiers:
        cout = c['cout_engage'] or 0
        fact = c['facture_client'] or 0
        marge = fact - cout
        pct_marge = (marge / fact * 100) if fact > 0 else 0
        color = '#10b981' if pct_marge >= 15 else '#f59e0b' if pct_marge >= 0 else '#ef4444'

        total_budget += c['budget_initial'] or 0
        total_cout += cout
        total_fact += fact
        total_marge += marge

        rows += (
            '<tr><td><strong style="color:#f97316">' + str(c["code"] or "—") + '</strong></td>'
            + '<td>' + str(c["nom"]) + '</td>'
            + '<td style="text-align:right">' + f'{c["budget_initial"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right">' + f'{cout:,.0f}' + ' F</td>'
            + '<td style="text-align:right">' + f'{fact:,.0f}' + ' F</td>'
            + '<td style="text-align:right;color:' + color + ';font-weight:800">' + f'{marge:,.0f}' + ' F</td>'
            + '<td style="text-align:center;color:' + color + ';font-weight:800">' + f'{pct_marge:.1f}' + '%</td></tr>'
        )

    pct_global = (total_marge / total_fact * 100) if total_fact > 0 else 0

    content = '<h1>📈 Rentabilité par chantier</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e293b,#334155)"><div class="kpi-icon">💰</div><div class="kpi-label">Budget total</div><div class="kpi-value" style="font-size:18px">' + f'{total_budget:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">📊</div><div class="kpi-label">Coûts engagés</div><div class="kpi-value" style="font-size:18px">' + f'{total_cout:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">🧾</div><div class="kpi-label">Facturé clients</div><div class="kpi-value" style="font-size:18px">' + f'{total_fact:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">📈</div><div class="kpi-label">Marge (' + f'{pct_global:.1f}' + '%)</div><div class="kpi-value" style="font-size:18px">' + f'{total_marge:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Chantier</th>'
    content += '<th style="text-align:right">Budget</th><th style="text-align:right">Coût engagé</th>'
    content += '<th style="text-align:right">Facturé</th><th style="text-align:right">Marge</th>'
    content += '<th style="text-align:center">% Marge</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucun chantier</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='rentabilite', page_title='Rentabilité')


# ═══════════════════════════════════════════════════════════════
# 📱 MOBILE CHEF DE CHANTIER
# ═══════════════════════════════════════════════════════════════

@app.route('/mobile-chef')
@login_required
def mobile_chef():
    db = get_db()
    cur = db.cursor()

    # Chantiers du chef connecté
    cur.execute("""
        SELECT c.*, cl.nom AS client_nom
        FROM chantiers c
        LEFT JOIN clients cl ON cl.id=c.client_id
        WHERE c.chef_chantier_id=? AND c.statut='en_cours'
        ORDER BY c.id DESC
        LIMIT 10
    """, (current_user.id,))
    chantiers = cur.fetchall()

    # Si admin sans chef assigné, montrer tous les en cours
    if not chantiers and current_user.role in ('admin', 'directeur'):
        cur.execute("""
            SELECT c.*, cl.nom AS client_nom
            FROM chantiers c
            LEFT JOIN clients cl ON cl.id=c.client_id
            WHERE c.statut='en_cours'
            ORDER BY c.id DESC LIMIT 10
        """)
        chantiers = cur.fetchall()

    cards = ''
    for c in chantiers:
        av = c['avancement_pct'] or 0
        cards += '<div class="card" style="border-left-color:#f97316">'
        cards += '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">'
        cards += '<div><h2 style="margin:0;color:#1e293b">' + str(c["nom"]) + '</h2>'
        cards += '<small style="color:#64748b">' + str(c["code"]) + ' · ' + str(c["ville"] or "") + '</small></div>'
        cards += '<span class="badge badge-orange">' + f'{av:.0f}' + '%</span></div>'
        cards += '<div class="progress" style="margin-bottom:10px"><div class="progress-bar" style="width:' + f'{av:.0f}' + '%"></div></div>'
        cards += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12.5px;color:#475569">'
        cards += '<div>👤 ' + str(c["client_nom"] or "—") + '</div>'
        cards += '<div>📅 ' + str((c["date_fin_prevue"] or "—")[:10]) + '</div>'
        cards += '</div>'
        cards += '<div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">'
        cards += '<a href="/chantiers/' + str(c["id"]) + '" class="btn btn-dark" style="padding:6px 12px;font-size:12px">📋 Détail</a>'
        cards += '<a href="/chantiers/' + str(c["id"]) + '/taches/nouvelle" class="btn btn-primary" style="padding:6px 12px;font-size:12px">+ Tâche</a>'
        cards += '<a href="/securite/incidents/nouveau" class="btn btn-danger" style="padding:6px 12px;font-size:12px">🚨 Incident</a>'
        cards += '</div></div>'

    content = '<h1>📱 Mobile chef de chantier</h1>'
    content += '<div style="background:#fff7ed;border-left:4px solid #f97316;padding:14px;border-radius:8px;margin-bottom:20px;font-size:13px;color:#c2410c">'
    content += '📱 Interface simplifiée pour utilisation sur le terrain — accès direct aux actions clés'
    content += '</div>'

    if not chantiers:
        content += '<div class="card"><p style="text-align:center;color:#94a3b8;padding:40px">Aucun chantier actif assigné</p></div>'
    else:
        content += cards

    return render_page(content, active='mobile', page_title='Mobile Chef')


# ═══════════════════════════════════════════════════════════════
# 📄 PDF CHANTIER
# ═══════════════════════════════════════════════════════════════

@app.route('/chantiers/<int:cid>/pdf')
@login_required
def chantiers_pdf(cid):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, cl.nom AS client_nom, u.nom_complet AS chef_nom
        FROM chantiers c
        LEFT JOIN clients cl ON cl.id=c.client_id
        LEFT JOIN users u ON u.id=c.chef_chantier_id
        WHERE c.id=?
    """, (cid,))
    c = cur.fetchone()
    if not c:
        flash('❌ Chantier introuvable', 'error')
        return redirect('/chantiers')

    cur.execute("SELECT * FROM budget_lignes WHERE chantier_id=?", (cid,))
    budget = cur.fetchall()

    cur.execute("SELECT * FROM taches WHERE chantier_id=? ORDER BY ordre", (cid,))
    taches = cur.fetchall()

    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Header orange/anthracite
    cv.setFillColor(colors.HexColor('#1e293b'))
    cv.rect(0, h - 35*mm, w, 35*mm, fill=1, stroke=0)
    cv.setFillColor(colors.HexColor('#f97316'))
    cv.rect(0, h - 35*mm, w, 4*mm, fill=1, stroke=0)
    cv.setFillColor(colors.white)
    cv.setFont('Helvetica-Bold', 20)
    cv.drawString(15*mm, h - 18*mm, "OMEGA BTP")
    cv.setFont('Helvetica', 10)
    cv.drawString(15*mm, h - 25*mm, "Fiche chantier")
    cv.setFont('Helvetica-Bold', 14)
    cv.drawRightString(w - 15*mm, h - 18*mm, str(c["code"] or ""))
    cv.setFont('Helvetica', 9)
    cv.drawRightString(w - 15*mm, h - 25*mm, datetime.now().strftime('%d/%m/%Y'))

    # Titre chantier
    y = h - 45*mm
    cv.setFillColor(colors.HexColor('#1e293b'))
    cv.setFont('Helvetica-Bold', 16)
    cv.drawString(15*mm, y, str(c["nom"]))
    y -= 6*mm
    cv.setFont('Helvetica', 10)
    cv.setFillColor(colors.HexColor('#64748b'))
    cv.drawString(15*mm, y, str(c["type"] or "") + ' · ' + str(c["ville"] or ""))

    # Informations
    y -= 15*mm
    cv.setFillColor(colors.HexColor('#f97316'))
    cv.rect(15*mm, y - 7*mm, w - 30*mm, 8*mm, fill=1, stroke=0)
    cv.setFillColor(colors.white)
    cv.setFont('Helvetica-Bold', 11)
    cv.drawString(17*mm, y - 4.5*mm, "INFORMATIONS GÉNÉRALES")

    y -= 14*mm
    cv.setFillColor(colors.HexColor('#1e293b'))
    cv.setFont('Helvetica', 10)
    infos = [
        ('Client', str(c["client_nom"] or "—")),
        ('Chef chantier', str(c["chef_nom"] or "—")),
        ('Date début', str((c["date_debut"] or "—")[:10])),
        ('Date fin prévue', str((c["date_fin_prevue"] or "—")[:10])),
        ('Budget initial', f'{c["budget_initial"]:,.0f} FCFA'),
        ('Avancement', f'{c["avancement_pct"]:.0f}%'),
        ('Statut', str(c["statut"])),
    ]
    for label, val in infos:
        cv.setFont('Helvetica-Bold', 10)
        cv.drawString(17*mm, y, label + ' :')
        cv.setFont('Helvetica', 10)
        cv.drawString(60*mm, y, val)
        y -= 5.5*mm

    # Budget
    y -= 8*mm
    cv.setFillColor(colors.HexColor('#f97316'))
    cv.rect(15*mm, y - 7*mm, w - 30*mm, 8*mm, fill=1, stroke=0)
    cv.setFillColor(colors.white)
    cv.setFont('Helvetica-Bold', 11)
    cv.drawString(17*mm, y - 4.5*mm, "BUDGET PAR CATÉGORIE")
    y -= 14*mm

    cv.setFillColor(colors.HexColor('#1e293b'))
    cv.setFont('Helvetica-Bold', 9)
    cv.drawString(17*mm, y, "Catégorie")
    cv.drawRightString(100*mm, y, "Prévu")
    cv.drawRightString(140*mm, y, "Engagé")
    cv.drawRightString(w - 17*mm, y, "Payé")
    y -= 5*mm

    cv.setFont('Helvetica', 9)
    total_p = total_e = total_pa = 0
    for b in budget:
        total_p += b['montant_prevu'] or 0
        total_e += b['montant_engage'] or 0
        total_pa += b['montant_paye'] or 0
        cv.drawString(17*mm, y, str(b["libelle"])[:40])
        cv.drawRightString(100*mm, y, f'{b["montant_prevu"]:,.0f}')
        cv.drawRightString(140*mm, y, f'{b["montant_engage"]:,.0f}')
        cv.drawRightString(w - 17*mm, y, f'{b["montant_paye"]:,.0f}')
        y -= 5*mm
        if y < 40*mm:
            cv.showPage()
            y = h - 20*mm

    y -= 3*mm
    cv.setFont('Helvetica-Bold', 10)
    cv.setFillColor(colors.HexColor('#f97316'))
    cv.drawString(17*mm, y, "TOTAL")
    cv.drawRightString(100*mm, y, f'{total_p:,.0f}')
    cv.drawRightString(140*mm, y, f'{total_e:,.0f}')
    cv.drawRightString(w - 17*mm, y, f'{total_pa:,.0f}')

    # Tâches
    y -= 15*mm
    if y > 60*mm:
        cv.setFillColor(colors.HexColor('#f97316'))
        cv.rect(15*mm, y - 7*mm, w - 30*mm, 8*mm, fill=1, stroke=0)
        cv.setFillColor(colors.white)
        cv.setFont('Helvetica-Bold', 11)
        cv.drawString(17*mm, y - 4.5*mm, "PLANNING DES TÂCHES")
        y -= 14*mm

        cv.setFillColor(colors.HexColor('#1e293b'))
        cv.setFont('Helvetica-Bold', 9)
        cv.drawString(17*mm, y, "Phase")
        cv.drawString(70*mm, y, "Début")
        cv.drawString(110*mm, y, "Fin")
        cv.drawRightString(150*mm, y, "Durée")
        cv.drawRightString(w - 17*mm, y, "Avanc.")
        y -= 5*mm

        cv.setFont('Helvetica', 9)
        for t in taches[:15]:
            cv.drawString(17*mm, y, str(t["phase"] or t["nom"])[:30])
            cv.drawString(70*mm, y, str((t["date_debut"] or "—")[:10]))
            cv.drawString(110*mm, y, str((t["date_fin"] or "—")[:10]))
            cv.drawRightString(150*mm, y, str(t["duree_jours"]) + ' j')
            cv.drawRightString(w - 17*mm, y, f'{t["avancement_pct"]:.0f}%')
            y -= 5*mm

    # Footer
    cv.setFillColor(colors.HexColor('#64748b'))
    cv.setFont('Helvetica', 7)
    cv.drawString(15*mm, 10*mm, "OMEGA BTP — Chantiers · PME Sénégal · Dakar")
    cv.drawRightString(w - 15*mm, 10*mm, "Généré le " + datetime.now().strftime('%d/%m/%Y à %H:%M'))

    cv.showPage()
    cv.save()
    buf.seek(0)

    log_action(current_user.id, 'PDF_CHANTIER', str(c["code"]), 'chantiers', cid)
    return send_file(buf, mimetype='application/pdf',
                     download_name='chantier_' + str(c["code"] or cid) + '.pdf')


# ═══════════════════════════════════════════════════════════════
# 📊 API JSON
# ═══════════════════════════════════════════════════════════════

@app.route('/api/chantiers/stats')
@login_required
def api_chantiers_stats():
    db = get_db()
    cur = db.cursor()
    result = {}
    for k, sql in [
        ('chantiers_total', "SELECT COUNT(*) FROM chantiers"),
        ('chantiers_en_cours', "SELECT COUNT(*) FROM chantiers WHERE statut='en_cours'"),
        ('budget_total', "SELECT COALESCE(SUM(budget_initial),0) FROM chantiers WHERE statut='en_cours'"),
        ('engage_total', "SELECT COALESCE(SUM(montant_engage),0) FROM budget_lignes"),
        ('paye_total', "SELECT COALESCE(SUM(montant_paye),0) FROM budget_lignes"),
        ('incidents_ouverts', "SELECT COUNT(*) FROM incidents WHERE statut='ouvert'"),
    ]:
        try:
            cur.execute(sql)
            r = cur.fetchone()
            result[k] = r[0] if r else 0
        except Exception:
            result[k] = 0
    return jsonify(result)


@app.route('/api/chantiers/gps')
@login_required
def api_chantiers_gps():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT code, nom, ville, latitude, longitude, statut, avancement_pct
        FROM chantiers
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """)
    r = cur.fetchall()
    return jsonify([dict(row) for row in r])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
