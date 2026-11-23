"""
💼 CRM & Ventes — Application principale
Prospects · Pipeline · Activités · Devis · Objectifs · Tournées
"""
from flask import Flask, render_template_string, redirect, url_for, session, request, jsonify, Response, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import sqlite3
import os
import io
import csv

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'omega-crm-secret-2026')

DB_PATH = '/app/data/crm.db'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id, username, role, nom_complet, objectif_mensuel=0, commission_pct=3.0):
        self.id = id
        self.username = username
        self.role = role
        self.nom_complet = nom_complet
        self.objectif_mensuel = objectif_mensuel
        self.commission_pct = commission_pct


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
        return User(r['id'], r['username'], r['role'], r['nom_complet'],
                    r['objectif_mensuel'] or 0, r['commission_pct'] or 3.0)
    return None


# ═══════════════════════════════════════════════════════════════
# LAYOUT — DESIGN PRO SECTEUR COMMERCIAL
# ================================================================

LAYOUT = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — OMEGA CRM</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,-apple-system,sans-serif}}
body{{background:#f8fafc;color:#1e293b;font-size:14px}}
.nav{{background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;padding:0 22px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 3px 12px rgba(0,0,0,.15);flex-wrap:wrap;border-bottom:4px solid #10b981}}
.nav-brand{{font-weight:900;font-size:18px;display:flex;align-items:center;gap:12px;padding:16px 0;letter-spacing:-0.3px}}
.nav-brand-icon{{width:40px;height:40px;background:#10b981;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(16,185,129,.4)}}
.nav-links{{display:flex;gap:2px;flex-wrap:wrap}}
.nav-links a{{color:#ede9fe;text-decoration:none;padding:8px 13px;border-radius:8px;font-size:12.5px;font-weight:600;transition:.2s;display:flex;align-items:center;gap:6px}}
.nav-links a:hover{{background:rgba(255,255,255,.12);color:#fff}}
.nav-links a.active{{background:#10b981;color:#fff;box-shadow:0 4px 10px rgba(16,185,129,.4)}}
.nav-user{{font-size:12.5px;display:flex;gap:10px;align-items:center;color:#ddd6fe}}
.nav-user a{{color:#fff;text-decoration:none;background:rgba(0,0,0,.25);padding:7px 14px;border-radius:8px;font-weight:600}}
.container{{max-width:1600px;margin:0 auto;padding:24px}}
h1{{color:#5b21b6;margin-bottom:20px;font-size:24px;font-weight:800;letter-spacing:-0.4px}}
h2{{color:#6d28d9;font-size:18px;margin-bottom:14px;font-weight:700}}
.card{{background:#fff;padding:22px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04);margin-bottom:18px;border-left:4px solid #10b981}}
table{{width:100%;border-collapse:collapse}}
thead{{background:#5b21b6;color:#fff}}
th{{padding:12px;text-align:left;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}}
td{{padding:11px;border-bottom:1px solid #f1f5f9;font-size:13.5px}}
tbody tr:hover{{background:#faf5ff}}
.btn{{display:inline-block;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px;border:none;cursor:pointer;transition:.15s;letter-spacing:.2px}}
.btn:hover{{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.15)}}
.btn-primary{{background:#7c3aed;color:#fff}}
.btn-purple{{background:#a855f7;color:#fff}}
.btn-success{{background:#10b981;color:#fff}}
.btn-danger{{background:#ef4444;color:#fff}}
.btn-warning{{background:#f59e0b;color:#fff}}
.btn-secondary{{background:#64748b;color:#fff}}
input,select,textarea{{width:100%;padding:11px 14px;border:2px solid #e2e8f0;border-radius:8px;font-size:13.5px;font-family:inherit;transition:.2s}}
input:focus,select:focus,textarea:focus{{outline:none;border-color:#7c3aed;box-shadow:0 0 0 3px rgba(124,58,237,.1)}}
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
.badge-purple{{background:#ede9fe;color:#6d28d9}}
.badge-green{{background:#d1fae5;color:#047857}}
.badge-orange{{background:#fed7aa;color:#c2410c}}
.badge-red{{background:#fee2e2;color:#b91c1c}}
.badge-blue{{background:#dbeafe;color:#1e40af}}
.badge-gray{{background:#e2e8f0;color:#475569}}
.pipeline{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;overflow-x:auto;padding-bottom:10px}}
.pipeline-col{{background:#f8fafc;border-radius:10px;padding:12px;min-height:400px;border-top:3px solid}}
.pipeline-card{{background:#fff;padding:12px;border-radius:8px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,.08);cursor:pointer;transition:.15s;border-left:3px solid #7c3aed}}
.pipeline-card:hover{{transform:translateX(2px);box-shadow:0 4px 8px rgba(0,0,0,.12)}}
.progress{{background:#e2e8f0;border-radius:8px;overflow:hidden;height:14px}}
.progress-bar{{height:100%;background:linear-gradient(90deg,#10b981,#059669);transition:.3s}}
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-brand">
    <div class="nav-brand-icon">💼</div>
    <div>OMEGA CRM<span style="display:block;font-size:10px;font-weight:500;letter-spacing:2px;color:#ddd6fe">FORCE DE VENTE · PME CEDEAO</span></div>
  </div>
  <div class="nav-links">
    <a href="/" class="{a_dash}">📊 Dashboard</a>
    <a href="/prospects" class="{a_pros}">👥 Prospects</a>
    <a href="/clients" class="{a_cli}">🏢 Clients</a>
    <a href="/pipeline" class="{a_pipe}">📊 Pipeline</a>
    <a href="/activites" class="{a_act}">📞 Activités</a>
    <a href="/devis" class="{a_dev}">💰 Devis</a>
    <a href="/objectifs" class="{a_obj}">🎯 Objectifs</a>
    <a href="/tournees" class="{a_tour}">🗺️ Tournées</a>
    <a href="/relances" class="{a_rel}">🔔 Relances</a>
    <a href="/rapports" class="{a_rap}">📈 Rapports</a>
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


def render_page(content, active='dashboard', page_title='CRM'):
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
        a_pros='active' if active == 'prospects' else '',
        a_cli='active' if active == 'clients' else '',
        a_pipe='active' if active == 'pipeline' else '',
        a_act='active' if active == 'activites' else '',
        a_dev='active' if active == 'devis' else '',
        a_obj='active' if active == 'objectifs' else '',
        a_tour='active' if active == 'tournees' else '',
        a_rel='active' if active == 'relances' else '',
        a_rap='active' if active == 'rapports' else '',
    )


@app.route('/health')
def health():
    return {'project': 'OMEGA CRM', 'service': 'crm-ventes',
            'status': 'ok', 'timestamp': datetime.now().isoformat(), 'version': '1.0'}


LOGIN_HTML = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Connexion — OMEGA CRM</title>
<style>body{{font-family:system-ui;background:linear-gradient(135deg,#5b21b6,#7c3aed);min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0}}
.box{{background:#fff;padding:42px;border-radius:16px;box-shadow:0 25px 70px rgba(0,0,0,.4);width:100%;max-width:420px;border-top:5px solid #10b981}}
.logo{{text-align:center;font-size:56px;margin-bottom:12px}}
h1{{color:#5b21b6;margin:0 0 6px;text-align:center;font-size:22px;font-weight:900;letter-spacing:-0.3px}}
.subtitle{{text-align:center;color:#64748b;font-size:12px;margin-bottom:24px;letter-spacing:1.5px;text-transform:uppercase;font-weight:600}}
input{{width:100%;padding:14px;border:2px solid #e2e8f0;border-radius:10px;margin-bottom:14px;font-size:15px;box-sizing:border-box}}
input:focus{{outline:none;border-color:#7c3aed;box-shadow:0 0 0 3px rgba(124,58,237,.1)}}
button{{width:100%;background:#10b981;color:#fff;padding:15px;border:none;border-radius:10px;font-weight:800;font-size:15px;cursor:pointer;letter-spacing:.5px;text-transform:uppercase}}
button:hover{{background:#059669}}
.err{{background:#fee2e2;color:#991b1b;padding:11px;border-radius:8px;margin-bottom:14px;font-size:13px;border-left:4px solid #ef4444}}
.hint{{margin-top:20px;padding:12px;background:#f5f3ff;border-radius:8px;font-size:12px;color:#6d28d9;text-align:center;border:1px dashed #c4b5fd}}</style></head>
<body><div class="box">
<div class="logo">💼</div>
<h1>OMEGA CRM</h1>
<div class="subtitle">Force de Vente · PME CEDEAO</div>
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
            user = User(r['id'], r['username'], r['role'], r['nom_complet'],
                        r['objectif_mensuel'] or 0, r['commission_pct'] or 3.0)
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

    def sc(sql, params=(), default=0):
        try:
            cur.execute(sql, params)
            r = cur.fetchone()
            return r[0] if r and r[0] is not None else default
        except Exception:
            return default

    is_admin = current_user.role in ('admin', 'manager')

    # Filtre : commercial voit ses données, admin voit tout
    filter_user = ''
    params = ()
    if not is_admin:
        filter_user = " AND commercial_id=?"
        params = (current_user.id,)

    stats = {
        'prospects': sc("SELECT COUNT(*) FROM prospects WHERE 1=1" + filter_user, params),
        'clients': sc("SELECT COUNT(*) FROM clients WHERE 1=1" + (filter_user.replace('commercial_id', 'commercial_id') if not is_admin else ''), params),
        'opportunites_ouvertes': sc("SELECT COUNT(*) FROM opportunites WHERE statut='ouverte'" + filter_user, params),
        'pipeline_total': sc("SELECT COALESCE(SUM(montant_estime * probabilite / 100.0),0) FROM opportunites WHERE statut='ouverte'" + filter_user, params),
        'ca_realise': sc("SELECT COALESCE(SUM(montant_ttc),0) FROM devis WHERE statut='accepte'" + filter_user, params),
        'devis_en_cours': sc("SELECT COUNT(*) FROM devis WHERE statut IN ('brouillon','envoye')" + filter_user, params),
        'relances_a_faire': sc("SELECT COUNT(*) FROM relances WHERE statut='a_faire'" + filter_user, params),
        'activites_semaine': sc("SELECT COUNT(*) FROM activites WHERE date_activite >= date('now', '-7 days')" + filter_user, params),
    }

    # Objectif en cours
    periode = datetime.now().strftime('%Y-%m')
    cur.execute("""
        SELECT objectif_ca, ca_realise FROM objectifs
        WHERE commercial_id=? AND periode=?
        ORDER BY id DESC LIMIT 1
    """, (current_user.id, periode))
    obj = cur.fetchone()
    if obj:
        obj_ca = obj['objectif_ca'] or 0
        ca_real = obj['ca_realise'] or 0
        pct_obj = (ca_real / obj_ca * 100) if obj_ca > 0 else 0
    else:
        obj_ca = 0
        ca_real = 0
        pct_obj = 0

    # Top 5 opportunités récentes
    sql_top = """
        SELECT o.*, p.raison_sociale AS prospect_nom, c.raison_sociale AS client_nom,
               u.nom_complet AS commercial_nom
        FROM opportunites o
        LEFT JOIN prospects p ON p.id=o.prospect_id
        LEFT JOIN clients c ON c.id=o.client_id
        LEFT JOIN users u ON u.id=o.commercial_id
        WHERE o.statut='ouverte'
    """
    if not is_admin:
        sql_top += " AND o.commercial_id=?"
        cur.execute(sql_top + " ORDER BY o.id DESC LIMIT 5", (current_user.id,))
    else:
        cur.execute(sql_top + " ORDER BY o.id DESC LIMIT 5")
    opps = cur.fetchall()

    opps_html = ''
    for o in opps:
        societe = o['prospect_nom'] or o['client_nom'] or '—'
        etape_badge = {
            'qualification': 'badge-blue',
            'analyse': 'badge-purple',
            'proposition': 'badge-orange',
            'negociation': 'badge-red',
        }.get(o['etape'], 'badge-gray')
        opps_html += (
            '<tr><td><strong>' + str(o["titre"]) + '</strong></td>'
            + '<td>' + str(societe) + '</td>'
            + '<td>' + str(o["commercial_nom"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{o["montant_estime"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center">' + str(o["probabilite"]) + '%</td>'
            + '<td><span class="badge ' + etape_badge + '">' + str(o["etape"]) + '</span></td></tr>'
        )

    # Relances urgentes
    sql_rel = """
        SELECT r.*, p.raison_sociale AS prospect_nom, u.nom_complet AS commercial_nom
        FROM relances r
        LEFT JOIN prospects p ON p.id=r.prospect_id
        LEFT JOIN users u ON u.id=r.commercial_id
        WHERE r.statut='a_faire'
    """
    if not is_admin:
        sql_rel += " AND r.commercial_id=?"
        cur.execute(sql_rel + " ORDER BY r.date_prevue ASC LIMIT 5", (current_user.id,))
    else:
        cur.execute(sql_rel + " ORDER BY r.date_prevue ASC LIMIT 5")
    relances = cur.fetchall()

    rel_html = ''
    for r in relances:
        type_icon = {'appel': '📞', 'email': '📧', 'visite': '🚗'}.get(r['type'], '📌')
        rel_html += (
            '<tr><td>' + type_icon + ' ' + str(r["type"]) + '</td>'
            + '<td>' + str(r["prospect_nom"] or "—") + '</td>'
            + '<td>' + str(r["date_prevue"] or "—") + '</td>'
            + '<td>' + str(r["commercial_nom"] or "—") + '</td></tr>'
        )

    content = '<h1>📊 Dashboard Commercial</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#7c3aed,#6d28d9)"><div class="kpi-icon">👥</div><div class="kpi-label">Prospects</div><div class="kpi-value">' + str(stats["prospects"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🏢</div><div class="kpi-label">Clients</div><div class="kpi-value">' + str(stats["clients"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#a855f7,#7e22ce)"><div class="kpi-icon">📊</div><div class="kpi-label">Opportunités</div><div class="kpi-value">' + str(stats["opportunites_ouvertes"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">💎</div><div class="kpi-label">Pipeline pondéré</div><div class="kpi-value" style="font-size:18px">' + f'{stats["pipeline_total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">💰</div><div class="kpi-label">CA réalisé</div><div class="kpi-value" style="font-size:18px">' + f'{stats["ca_realise"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div class="kpi-icon">📄</div><div class="kpi-label">Devis en cours</div><div class="kpi-value">' + str(stats["devis_en_cours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">🔔</div><div class="kpi-label">Relances à faire</div><div class="kpi-value">' + str(stats["relances_a_faire"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#059669,#047857)"><div class="kpi-icon">📞</div><div class="kpi-label">Activités 7j</div><div class="kpi-value">' + str(stats["activites_semaine"]) + '</div></div>'
    content += '</div>'

    # Objectif du mois
    pct_color = '#10b981' if pct_obj >= 80 else '#f59e0b' if pct_obj >= 50 else '#ef4444'
    content += '<div class="card"><h2>🎯 Objectif du mois — ' + periode + '</h2>'
    content += '<div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:13px">'
    content += '<span><strong>' + f'{ca_real:,.0f}' + ' F</strong> sur ' + f'{obj_ca:,.0f}' + ' F</span>'
    content += '<span style="color:' + pct_color + ';font-weight:800">' + f'{pct_obj:.1f}' + '%</span></div>'
    content += '<div class="progress"><div class="progress-bar" style="width:' + f'{min(pct_obj,100):.0f}' + '%;background:' + pct_color + '"></div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:18px">'
    content += '<div class="card"><h2>📊 Top 5 opportunités</h2>'
    content += '<table><thead><tr><th>Titre</th><th>Société</th><th>Commercial</th><th style="text-align:right">Montant</th><th style="text-align:center">Proba</th><th>Étape</th></tr></thead>'
    content += '<tbody>' + (opps_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:30px">Aucune opportunité</td></tr>') + '</tbody></table></div>'

    content += '<div class="card" style="border-left-color:#ef4444"><h2>🔔 Relances à faire</h2>'
    content += '<table><thead><tr><th>Type</th><th>Prospect</th><th>Prévu</th><th>Commercial</th></tr></thead>'
    content += '<tbody>' + (rel_html or '<tr><td colspan="4" style="text-align:center;color:#10b981;padding:30px">✅ Aucune relance</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    return render_page(content, active='dashboard', page_title='Dashboard')


# ═══════════════════════════════════════════════════════════════
# 👥 PROSPECTS
# ═══════════════════════════════════════════════════════════════

@app.route('/prospects')
@login_required
def prospects_liste():
    db = get_db()
    cur = db.cursor()
    statut = request.args.get('statut', '')
    q = request.args.get('q', '').strip()

    is_admin = current_user.role in ('admin', 'manager')
    sql = """
        SELECT p.*, u.nom_complet AS commercial_nom
        FROM prospects p
        LEFT JOIN users u ON u.id=p.commercial_id
        WHERE 1=1
    """
    params = []
    if not is_admin:
        sql += " AND p.commercial_id=?"
        params.append(current_user.id)
    if statut:
        sql += " AND p.statut=?"
        params.append(statut)
    if q:
        sql += " AND (p.raison_sociale LIKE ? OR p.contact_nom LIKE ? OR p.code LIKE ?)"
        params += [f'%{q}%'] * 3
    sql += " ORDER BY p.id DESC LIMIT 200"
    cur.execute(sql, params)
    prospects = cur.fetchall()

    stats = {}
    base_filter = "" if is_admin else " WHERE commercial_id=?"
    base_params = () if is_admin else (current_user.id,)
    for k, s in [
        ('total', "SELECT COUNT(*) FROM prospects" + base_filter),
        ('nouveau', "SELECT COUNT(*) FROM prospects WHERE statut='nouveau'" + (" AND commercial_id=?" if not is_admin else "")),
        ('qualifie', "SELECT COUNT(*) FROM prospects WHERE statut='qualifie'" + (" AND commercial_id=?" if not is_admin else "")),
        ('en_negociation', "SELECT COUNT(*) FROM prospects WHERE statut='en_negociation'" + (" AND commercial_id=?" if not is_admin else "")),
    ]:
        cur.execute(s, base_params)
        stats[k] = cur.fetchone()[0]

    rows = ''
    for p in prospects:
        statut_badge = {
            'nouveau': 'badge-blue',
            'contacte': 'badge-purple',
            'qualifie': 'badge-orange',
            'en_negociation': 'badge-red',
            'converti': 'badge-green',
            'perdu': 'badge-gray',
        }.get(p['statut'], 'badge-gray')
        score_color = '#10b981' if (p['score'] or 0) >= 70 else '#f59e0b' if (p['score'] or 0) >= 40 else '#ef4444'
        rows += (
            '<tr><td><strong style="color:#7c3aed">' + str(p["code"] or "—") + '</strong></td>'
            + '<td><strong>' + str(p["raison_sociale"]) + '</strong><br><small style="color:#64748b">' + str(p["secteur"] or "") + '</small></td>'
            + '<td>' + str(p["contact_nom"] or "—") + '<br><small style="color:#64748b">' + str(p["contact_fonction"] or "") + '</small></td>'
            + '<td>' + str(p["telephone"] or "—") + '</td>'
            + '<td>' + str(p["ville"] or "—") + '</td>'
            + '<td style="text-align:center;color:' + score_color + ';font-weight:800">' + str(p["score"] or 0) + '</td>'
            + '<td>' + str(p["commercial_nom"] or "—") + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(p["statut"]) + '</span></td>'
            + '<td><a href="/prospects/' + str(p["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁 Voir</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👥 Prospects — ' + str(len(prospects)) + '</h1>'
    content += '<a href="/prospects/nouveau" class="btn btn-primary">+ Nouveau prospect</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#7c3aed,#6d28d9)"><div class="kpi-icon">👥</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">🆕</div><div class="kpi-label">Nouveaux</div><div class="kpi-value">' + str(stats["nouveau"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">✅</div><div class="kpi-label">Qualifiés</div><div class="kpi-value">' + str(stats["qualifie"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">💬</div><div class="kpi-label">En négociation</div><div class="kpi-value">' + str(stats["en_negociation"]) + '</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher..." style="max-width:400px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/prospects" class="btn ' + ('btn-primary' if not statut else 'btn-secondary') + '">Tous</a> '
    for s in ['nouveau', 'contacte', 'qualifie', 'en_negociation', 'converti', 'perdu']:
        active_cls = 'btn-primary' if statut == s else 'btn-secondary'
        content += '<a href="/prospects?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>Code</th><th>Raison sociale</th><th>Contact</th><th>Téléphone</th><th>Ville</th>'
    content += '<th style="text-align:center">Score</th><th>Commercial</th><th>Statut</th><th>Actions</th>'
    content += '</tr></thead><tbody>'
    content += rows or '<tr><td colspan="9" style="padding:40px;text-align:center;color:#94a3b8">Aucun prospect</td></tr>'
    content += '</tbody></table></div>'

    return render_page(content, active='prospects', page_title='Prospects')


@app.route('/prospects/nouveau', methods=['GET', 'POST'])
@login_required
def prospects_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            commercial_id = int(request.form.get('commercial_id') or 0)
            if current_user.role not in ('admin', 'manager'):
                commercial_id = current_user.id
            if not commercial_id:
                commercial_id = current_user.id

            cur.execute("""
                INSERT INTO prospects
                (code, raison_sociale, secteur, contact_nom, contact_fonction,
                 telephone, email, ville, pays, source, statut, score, commercial_id,
                 notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None,
                  request.form.get('raison_sociale'),
                  request.form.get('secteur'),
                  request.form.get('contact_nom'),
                  request.form.get('contact_fonction'),
                  request.form.get('telephone'),
                  request.form.get('email'),
                  request.form.get('ville'),
                  request.form.get('pays') or 'Sénégal',
                  request.form.get('source'),
                  'nouveau', 20, commercial_id,
                  request.form.get('notes'),
                  datetime.now().isoformat()))
            db.commit()
            log_action(current_user.id, 'CREATE_PROSPECT',
                       request.form.get('raison_sociale'), 'prospects', cur.lastrowid)
            flash('✅ Prospect créé', 'success')
            return redirect('/prospects')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom_complet FROM users WHERE role='commercial' AND actif=1")
    coms = cur.fetchall()
    opts_com = ''.join('<option value="' + str(c["id"]) + '"' + (' selected' if c["id"] == current_user.id else '') + '>' + str(c["nom_complet"]) + '</option>' for c in coms)

    content = '<h1>👥 Nouveau prospect</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Raison sociale *</label><input type="text" name="raison_sociale" required autofocus></div>'
    content += '<div><label>Secteur</label><input type="text" name="secteur" placeholder="Agro-industrie, BTP..."></div>'
    content += '<div><label>Source</label><select name="source">'
    content += '<option value="prospection">Prospection directe</option>'
    content += '<option value="site_web">Site web</option>'
    content += '<option value="salon">Salon professionnel</option>'
    content += '<option value="recommandation">Recommandation</option>'
    content += '<option value="appel_entrant">Appel entrant</option>'
    content += '<option value="linkedin">LinkedIn</option>'
    content += '</select></div>'
    content += '<div><label>Nom du contact</label><input type="text" name="contact_nom"></div>'
    content += '<div><label>Fonction du contact</label><input type="text" name="contact_fonction"></div>'
    content += '<div><label>Téléphone</label><input type="text" name="telephone" placeholder="+221 77 XXX XX XX"></div>'
    content += '<div><label>Email</label><input type="email" name="email"></div>'
    content += '<div><label>Ville</label><input type="text" name="ville" value="Dakar"></div>'
    content += '<div><label>Pays</label><input type="text" name="pays" value="Sénégal"></div>'
    content += '<div><label>Commercial assigné</label><select name="commercial_id">' + opts_com + '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Notes</label><textarea name="notes" rows="3"></textarea></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/prospects" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='prospects', page_title='Nouveau prospect')


@app.route('/prospects/<int:pid>')
@login_required
def prospects_detail(pid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT p.*, u.nom_complet AS commercial_nom
        FROM prospects p
        LEFT JOIN users u ON u.id=p.commercial_id
        WHERE p.id=?
    """, (pid,))
    p = cur.fetchone()
    if not p:
        flash('❌ Prospect introuvable', 'error')
        return redirect('/prospects')

    # Activités
    cur.execute("""
        SELECT * FROM activites WHERE prospect_id=?
        ORDER BY date_activite DESC LIMIT 10
    """, (pid,))
    activites = cur.fetchall()

    # Opportunités
    cur.execute("SELECT * FROM opportunites WHERE prospect_id=? ORDER BY id DESC", (pid,))
    opps = cur.fetchall()

    act_html = ''
    for a in activites:
        icon = {'appel': '📞', 'visite': '🚗', 'email': '📧', 'reunion': '🤝', 'demo': '💻'}.get(a['type'], '📌')
        act_html += '<tr><td>' + icon + ' ' + str(a["type"]) + '</td><td>' + str(a["sujet"] or "—") + '</td>'
        act_html += '<td>' + str((a["date_activite"] or "")[:16]) + '</td>'
        act_html += '<td>' + str(a["resultat"] or "—") + '</td></tr>'

    opps_html = ''
    for o in opps:
        etape_badge = {'qualification': 'badge-blue', 'analyse': 'badge-purple',
                       'proposition': 'badge-orange', 'negociation': 'badge-red',
                       'gagnee': 'badge-green', 'perdue': 'badge-gray'}.get(o['etape'], 'badge-gray')
        opps_html += '<tr><td>' + str(o["titre"]) + '</td>'
        opps_html += '<td style="text-align:right">' + f'{o["montant_estime"]:,.0f}' + ' F</td>'
        opps_html += '<td><span class="badge ' + etape_badge + '">' + str(o["etape"]) + '</span></td></tr>'

    statut_badge = {'nouveau': 'badge-blue', 'contacte': 'badge-purple', 'qualifie': 'badge-orange',
                    'en_negociation': 'badge-red', 'converti': 'badge-green', 'perdu': 'badge-gray'}.get(p['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👥 ' + str(p["raison_sociale"]) + ' <span class="badge ' + statut_badge + '">' + str(p["statut"]) + '</span></h1>'
    content += '<div><a href="/activites/nouvelle?prospect_id=' + str(pid) + '" class="btn btn-primary">+ Activité</a> '
    content += '<a href="/prospects" class="btn btn-secondary" style="margin-left:6px">← Retour</a></div></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#7c3aed,#6d28d9)"><div class="kpi-label">Code</div><div class="kpi-value" style="font-size:18px">' + str(p["code"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-label">Score</div><div class="kpi-value">' + str(p["score"] or 0) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Opportunités</div><div class="kpi-value">' + str(len(opps)) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-label">Activités</div><div class="kpi-value">' + str(len(activites)) + '</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>📋 Coordonnées</h2><table>'
    content += '<tr><td><strong>Secteur</strong></td><td>' + str(p["secteur"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Contact</strong></td><td>' + str(p["contact_nom"] or "—") + ' — ' + str(p["contact_fonction"] or "") + '</td></tr>'
    content += '<tr><td><strong>Téléphone</strong></td><td>' + str(p["telephone"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Email</strong></td><td>' + str(p["email"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Ville</strong></td><td>' + str(p["ville"] or "—") + ' · ' + str(p["pays"] or "") + '</td></tr>'
    content += '<tr><td><strong>Source</strong></td><td>' + str(p["source"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Commercial</strong></td><td>' + str(p["commercial_nom"] or "—") + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>📊 Opportunités</h2>'
    content += '<table><thead><tr><th>Titre</th><th style="text-align:right">Montant</th><th>Étape</th></tr></thead>'
    content += '<tbody>' + (opps_html or '<tr><td colspan="3" style="text-align:center;color:#94a3b8;padding:20px">Aucune opportunité</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    content += '<div class="card"><h2>📞 Activités récentes</h2>'
    content += '<table><thead><tr><th>Type</th><th>Sujet</th><th>Date</th><th>Résultat</th></tr></thead>'
    content += '<tbody>' + (act_html or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucune activité</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='prospects', page_title='Prospect')


# ═══════════════════════════════════════════════════════════════
# 🏢 CLIENTS
# ═══════════════════════════════════════════════════════════════

@app.route('/clients')
@login_required
def clients_liste():
    db = get_db()
    cur = db.cursor()
    is_admin = current_user.role in ('admin', 'manager')
    sql = """
        SELECT c.*, u.nom_complet AS commercial_nom
        FROM clients c
        LEFT JOIN users u ON u.id=c.commercial_id
        WHERE 1=1
    """
    params = []
    if not is_admin:
        sql += " AND c.commercial_id=?"
        params.append(current_user.id)
    sql += " ORDER BY c.chiffre_affaires_total DESC LIMIT 200"
    cur.execute(sql, params)
    clients = cur.fetchall()

    total_ca = sum(c['chiffre_affaires_total'] or 0 for c in clients)

    rows = ''
    for c in clients:
        rows += (
            '<tr><td><strong style="color:#7c3aed">' + str(c["code"] or "—") + '</strong></td>'
            + '<td><strong>' + str(c["raison_sociale"]) + '</strong><br><small style="color:#64748b">' + str(c["secteur"] or "") + '</small></td>'
            + '<td>' + str(c["contact_nom"] or "—") + '</td>'
            + '<td>' + str(c["telephone"] or "—") + '</td>'
            + '<td>' + str(c["ville"] or "—") + '</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:800">' + f'{c["chiffre_affaires_total"]:,.0f}' + ' F</td>'
            + '<td>' + str(c["commercial_nom"] or "—") + '</td>'
            + '<td>' + str((c["date_conversion"] or "—")[:10]) + '</td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🏢 Clients — ' + str(len(clients)) + '</h1>'
    content += '<a href="/clients/nouveau" class="btn btn-primary">+ Nouveau client</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🏢</div><div class="kpi-label">Clients actifs</div><div class="kpi-value">' + str(len(clients)) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">💰</div><div class="kpi-label">CA total</div><div class="kpi-value" style="font-size:18px">' + f'{total_ca:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#7c3aed,#6d28d9)"><div class="kpi-icon">📊</div><div class="kpi-label">Panier moyen</div><div class="kpi-value" style="font-size:18px">' + f'{total_ca/len(clients) if clients else 0:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>Code</th><th>Raison sociale</th><th>Contact</th><th>Téléphone</th><th>Ville</th>'
    content += '<th style="text-align:right">CA total</th><th>Commercial</th><th>Converti le</th>'
    content += '</tr></thead><tbody>'
    content += rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun client</td></tr>'
    content += '</tbody></table></div>'

    return render_page(content, active='clients', page_title='Clients')


@app.route('/clients/nouveau', methods=['GET', 'POST'])
@login_required
def clients_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            commercial_id = int(request.form.get('commercial_id') or 0) or current_user.id
            cur.execute("""
                INSERT INTO clients
                (code, raison_sociale, secteur, contact_nom, telephone, email,
                 ville, pays, chiffre_affaires_total, commercial_id,
                 date_conversion, actif, created_at)
                VALUES (?,?,?,?,?,?,?,?,0,?,?,1,?)
            """, (None,
                  request.form.get('raison_sociale'),
                  request.form.get('secteur'),
                  request.form.get('contact_nom'),
                  request.form.get('telephone'),
                  request.form.get('email'),
                  request.form.get('ville'),
                  request.form.get('pays') or 'Sénégal',
                  commercial_id,
                  datetime.now().strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Client créé', 'success')
            return redirect('/clients')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom_complet FROM users WHERE role='commercial' AND actif=1")
    coms = cur.fetchall()
    opts_com = ''.join('<option value="' + str(c["id"]) + '"' + (' selected' if c["id"] == current_user.id else '') + '>' + str(c["nom_complet"]) + '</option>' for c in coms)

    content = '<h1>🏢 Nouveau client</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Raison sociale *</label><input type="text" name="raison_sociale" required autofocus></div>'
    content += '<div><label>Secteur</label><input type="text" name="secteur"></div>'
    content += '<div><label>Contact</label><input type="text" name="contact_nom"></div>'
    content += '<div><label>Téléphone</label><input type="text" name="telephone"></div>'
    content += '<div><label>Email</label><input type="email" name="email"></div>'
    content += '<div><label>Ville</label><input type="text" name="ville"></div>'
    content += '<div><label>Pays</label><input type="text" name="pays" value="Sénégal"></div>'
    content += '<div><label>Commercial</label><select name="commercial_id">' + opts_com + '</select></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/clients" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='clients', page_title='Nouveau client')


# ═══════════════════════════════════════════════════════════════
# 📊 PIPELINE (Kanban)
# ═══════════════════════════════════════════════════════════════

@app.route('/pipeline')
@login_required
def pipeline_kanban():
    db = get_db()
    cur = db.cursor()
    is_admin = current_user.role in ('admin', 'manager')

    sql = """
        SELECT o.*, p.raison_sociale AS prospect_nom, c.raison_sociale AS client_nom,
               u.nom_complet AS commercial_nom
        FROM opportunites o
        LEFT JOIN prospects p ON p.id=o.prospect_id
        LEFT JOIN clients c ON c.id=o.client_id
        LEFT JOIN users u ON u.id=o.commercial_id
        WHERE o.statut='ouverte'
    """
    params = []
    if not is_admin:
        sql += " AND o.commercial_id=?"
        params.append(current_user.id)
    sql += " ORDER BY o.montant_estime DESC"
    cur.execute(sql, params)
    opps = cur.fetchall()

    etapes = [
        ('qualification', '🔍 Qualification', '#3b82f6'),
        ('analyse', '📋 Analyse', '#a855f7'),
        ('proposition', '📄 Proposition', '#f59e0b'),
        ('negociation', '🤝 Négociation', '#ef4444'),
        ('gagnee', '✅ Gagnée', '#10b981'),
        ('perdue', '❌ Perdue', '#64748b'),
    ]

    columns_html = ''
    total_pipeline = 0
    for etape_key, etape_label, etape_color in etapes:
        etape_opps = [o for o in opps if o['etape'] == etape_key]
        total_etape = sum(o['montant_estime'] or 0 for o in etape_opps)

        cards = ''
        for o in etape_opps:
            societe = o['prospect_nom'] or o['client_nom'] or '—'
            cards += '<div class="pipeline-card" style="border-left-color:' + etape_color + '">'
            cards += '<div style="font-weight:700;color:#1e293b;font-size:13px;margin-bottom:4px">' + str(o["titre"]) + '</div>'
            cards += '<div style="font-size:11.5px;color:#64748b;margin-bottom:6px">' + str(societe) + '</div>'
            cards += '<div style="display:flex;justify-content:space-between;align-items:center">'
            cards += '<span style="font-weight:800;color:#10b981;font-size:13px">' + f'{o["montant_estime"]:,.0f}' + ' F</span>'
            cards += '<span style="background:#ede9fe;color:#7c3aed;padding:2px 8px;border-radius:10px;font-size:10.5px;font-weight:700">' + str(o["probabilite"]) + '%</span>'
            cards += '</div>'
            cards += '<div style="font-size:11px;color:#64748b;margin-top:6px">👤 ' + str(o["commercial_nom"] or "—") + '</div>'
            cards += '<div style="margin-top:8px"><a href="/pipeline/' + str(o["id"]) + '" class="btn btn-primary" style="padding:3px 8px;font-size:10.5px">Voir</a></div>'
            cards += '</div>'

        columns_html += '<div class="pipeline-col" style="border-top-color:' + etape_color + '">'
        columns_html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">'
        columns_html += '<strong style="color:' + etape_color + ';font-size:13px">' + etape_label + '</strong>'
        columns_html += '<span style="background:' + etape_color + '20;color:' + etape_color + ';padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">' + str(len(etape_opps)) + '</span>'
        columns_html += '</div>'
        columns_html += '<div style="font-size:11px;color:#64748b;margin-bottom:10px">' + f'{total_etape:,.0f}' + ' F</div>'
        columns_html += cards or '<div style="text-align:center;color:#94a3b8;font-size:11px;padding:20px">Aucune</div>'
        columns_html += '</div>'

        if etape_key not in ('gagnee', 'perdue'):
            total_pipeline += total_etape

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📊 Pipeline de vente</h1>'
    content += '<a href="/pipeline/nouvelle" class="btn btn-primary">+ Nouvelle opportunité</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#7c3aed,#6d28d9)"><div class="kpi-icon">📊</div><div class="kpi-label">Opportunités ouvertes</div><div class="kpi-value">' + str(len(opps)) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">Valeur pipeline</div><div class="kpi-value" style="font-size:18px">' + f'{total_pipeline:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="pipeline">' + columns_html + '</div>'
    return render_page(content, active='pipeline', page_title='Pipeline')


@app.route('/pipeline/nouvelle', methods=['GET', 'POST'])
@login_required
def pipeline_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            commercial_id = int(request.form.get('commercial_id') or 0) or current_user.id
            cur.execute("""
                INSERT INTO opportunites
                (titre, prospect_id, client_id, commercial_id, montant_estime, probabilite,
                 etape, date_cloture_prevue, statut, source, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (request.form.get('titre'),
                  int(request.form.get('prospect_id') or 0) or None,
                  int(request.form.get('client_id') or 0) or None,
                  commercial_id,
                  float(request.form.get('montant_estime') or 0),
                  int(request.form.get('probabilite') or 10),
                  request.form.get('etape') or 'qualification',
                  request.form.get('date_cloture_prevue'),
                  'ouverte',
                  request.form.get('source') or 'prospection',
                  request.form.get('notes'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Opportunité créée', 'success')
            return redirect('/pipeline')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, raison_sociale FROM prospects ORDER BY raison_sociale LIMIT 100")
    prospects = cur.fetchall()
    cur.execute("SELECT id, raison_sociale FROM clients ORDER BY raison_sociale LIMIT 100")
    clients = cur.fetchall()
    cur.execute("SELECT id, nom_complet FROM users WHERE role='commercial' AND actif=1")
    coms = cur.fetchall()

    opts_pros = ''.join('<option value="' + str(p["id"]) + '">' + str(p["raison_sociale"]) + '</option>' for p in prospects)
    opts_cli = ''.join('<option value="' + str(c["id"]) + '">' + str(c["raison_sociale"]) + '</option>' for c in clients)
    opts_com = ''.join('<option value="' + str(c["id"]) + '"' + (' selected' if c["id"] == current_user.id else '') + '>' + str(c["nom_complet"]) + '</option>' for c in coms)

    content = '<h1>📊 Nouvelle opportunité</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Titre *</label><input type="text" name="titre" required autofocus></div>'
    content += '<div><label>Prospect</label><select name="prospect_id"><option value="">— Aucun —</option>' + opts_pros + '</select></div>'
    content += '<div><label>Client existant</label><select name="client_id"><option value="">— Aucun —</option>' + opts_cli + '</select></div>'
    content += '<div><label>Montant estimé (FCFA) *</label><input type="number" step="1000" name="montant_estime" required value="1000000"></div>'
    content += '<div><label>Probabilité (%)</label><input type="number" name="probabilite" value="20" min="0" max="100"></div>'
    content += '<div><label>Étape</label><select name="etape">'
    content += '<option value="qualification">🔍 Qualification</option>'
    content += '<option value="analyse">📋 Analyse</option>'
    content += '<option value="proposition">📄 Proposition</option>'
    content += '<option value="negociation">🤝 Négociation</option>'
    content += '</select></div>'
    content += '<div><label>Date clôture prévue</label><input type="date" name="date_cloture_prevue"></div>'
    content += '<div><label>Commercial</label><select name="commercial_id">' + opts_com + '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Notes</label><textarea name="notes" rows="3"></textarea></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/pipeline" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='pipeline', page_title='Nouvelle opportunité')


@app.route('/pipeline/<int:oid>', methods=['GET', 'POST'])
@login_required
def pipeline_detail(oid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT o.*, p.raison_sociale AS prospect_nom, c.raison_sociale AS client_nom,
               u.nom_complet AS commercial_nom
        FROM opportunites o
        LEFT JOIN prospects p ON p.id=o.prospect_id
        LEFT JOIN clients c ON c.id=o.client_id
        LEFT JOIN users u ON u.id=o.commercial_id
        WHERE o.id=?
    """, (oid,))
    o = cur.fetchone()
    if not o:
        flash('❌ Opportunité introuvable', 'error')
        return redirect('/pipeline')

    if request.method == 'POST':
        try:
            new_etape = request.form.get('etape') or o['etape']
            new_proba = int(request.form.get('probabilite') or o['probabilite'])
            new_statut = o['statut']
            if new_etape == 'gagnee':
                new_statut = 'gagnee'
                new_proba = 100
            elif new_etape == 'perdue':
                new_statut = 'perdue'
                new_proba = 0

            cur.execute("""
                UPDATE opportunites SET etape=?, probabilite=?, statut=?, notes=?
                WHERE id=?
            """, (new_etape, new_proba, new_statut,
                  request.form.get('notes') or o['notes'], oid))
            db.commit()
            flash('✅ Opportunité mise à jour', 'success')
            return redirect('/pipeline/' + str(oid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    etape_badge = {'qualification': 'badge-blue', 'analyse': 'badge-purple',
                   'proposition': 'badge-orange', 'negociation': 'badge-red',
                   'gagnee': 'badge-green', 'perdue': 'badge-gray'}.get(o['etape'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📊 ' + str(o["titre"]) + ' <span class="badge ' + etape_badge + '">' + str(o["etape"]) + '</span></h1>'
    content += '<a href="/pipeline" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Montant</div><div class="kpi-value" style="font-size:18px">' + f'{o["montant_estime"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-label">Probabilité</div><div class="kpi-value">' + str(o["probabilite"]) + '%</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#7c3aed,#6d28d9)"><div class="kpi-label">Valeur pondérée</div><div class="kpi-value" style="font-size:18px">' + f'{o["montant_estime"] * o["probabilite"] / 100:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>📋 Détails</h2><table>'
    content += '<tr><td><strong>Prospect</strong></td><td>' + str(o["prospect_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Client</strong></td><td>' + str(o["client_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Commercial</strong></td><td>' + str(o["commercial_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Source</strong></td><td>' + str(o["source"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Clôture prévue</strong></td><td>' + str((o["date_cloture_prevue"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Clôture réelle</strong></td><td>' + str((o["date_cloture_reelle"] or "—")[:10]) + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>✏️ Mettre à jour</h2>'
    content += '<form method="post">'
    content += '<div style="margin-bottom:16px"><label>Étape</label><select name="etape">'
    for k, l in [('qualification', '🔍 Qualification'), ('analyse', '📋 Analyse'),
                 ('proposition', '📄 Proposition'), ('negociation', '🤝 Négociation'),
                 ('gagnee', '✅ Gagnée'), ('perdue', '❌ Perdue')]:
        sel = ' selected' if o['etape'] == k else ''
        content += '<option value="' + k + '"' + sel + '>' + l + '</option>'
    content += '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Probabilité (%)</label>'
    content += '<input type="number" name="probabilite" value="' + str(o["probabilite"]) + '" min="0" max="100"></div>'
    content += '<div style="margin-bottom:16px"><label>Notes</label>'
    content += '<textarea name="notes" rows="3">' + str(o["notes"] or "") + '</textarea></div>'
    content += '<button type="submit" class="btn btn-success">💾 Enregistrer</button>'
    content += '</form></div>'
    content += '</div>'

    return render_page(content, active='pipeline', page_title='Opportunité')


# ═══════════════════════════════════════════════════════════════
# 📞 ACTIVITÉS (appels, visites, emails)
# ═══════════════════════════════════════════════════════════════

@app.route('/activites')
@login_required
def activites_liste():
    db = get_db()
    cur = db.cursor()
    is_admin = current_user.role in ('admin', 'manager')
    type_f = request.args.get('type', '')

    sql = """
        SELECT a.*, p.raison_sociale AS prospect_nom, c.raison_sociale AS client_nom,
               u.nom_complet AS commercial_nom
        FROM activites a
        LEFT JOIN prospects p ON p.id=a.prospect_id
        LEFT JOIN clients c ON c.id=a.client_id
        LEFT JOIN users u ON u.id=a.commercial_id
        WHERE 1=1
    """
    params = []
    if not is_admin:
        sql += " AND a.commercial_id=?"
        params.append(current_user.id)
    if type_f:
        sql += " AND a.type=?"
        params.append(type_f)
    sql += " ORDER BY a.date_activite DESC LIMIT 200"
    cur.execute(sql, params)
    activites = cur.fetchall()

    stats = {}
    for k, s in [('total', "SELECT COUNT(*) FROM activites"),
                 ('appel', "SELECT COUNT(*) FROM activites WHERE type='appel'"),
                 ('visite', "SELECT COUNT(*) FROM activites WHERE type='visite'"),
                 ('email', "SELECT COUNT(*) FROM activites WHERE type='email'")]:
        if not is_admin:
            s += " AND commercial_id=?"
            cur.execute(s, (current_user.id,))
        else:
            cur.execute(s)
        stats[k] = cur.fetchone()[0]

    rows = ''
    for a in activites:
        icon = {'appel': '📞', 'visite': '🚗', 'email': '📧', 'reunion': '🤝', 'demo': '💻'}.get(a['type'], '📌')
        societe = a['prospect_nom'] or a['client_nom'] or '—'
        res_badge = {
            'positif': 'badge-green',
            'a_suivre': 'badge-orange',
            'negatif': 'badge-red',
            'sans_reponse': 'badge-gray',
        }.get(a['resultat'], 'badge-gray')
        rows += (
            '<tr><td>' + icon + ' <strong>' + str(a["type"]) + '</strong></td>'
            + '<td>' + str(a["sujet"] or "—") + '</td>'
            + '<td>' + str(societe) + '</td>'
            + '<td>' + str(a["commercial_nom"] or "—") + '</td>'
            + '<td>' + str((a["date_activite"] or "")[:16]) + '</td>'
            + '<td>' + str(a["duree_min"] or 0) + ' min</td>'
            + '<td><span class="badge ' + res_badge + '">' + str(a["resultat"] or "—") + '</span></td>'
            + '<td>' + str(a["prochaine_action"] or "—") + '</td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📞 Activités commerciales</h1>'
    content += '<a href="/activites/nouvelle" class="btn btn-primary">+ Nouvelle activité</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#7c3aed,#6d28d9)"><div class="kpi-icon">📞</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">📞</div><div class="kpi-label">Appels</div><div class="kpi-value">' + str(stats["appel"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🚗</div><div class="kpi-label">Visites</div><div class="kpi-value">' + str(stats["visite"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">📧</div><div class="kpi-label">Emails</div><div class="kpi-value">' + str(stats["email"]) + '</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/activites" class="btn ' + ('btn-primary' if not type_f else 'btn-secondary') + '">Toutes</a> '
    for t in ['appel', 'visite', 'email', 'reunion', 'demo']:
        active_cls = 'btn-primary' if type_f == t else 'btn-secondary'
        content += '<a href="/activites?type=' + t + '" class="btn ' + active_cls + '" style="margin-left:6px">' + t + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>Type</th><th>Sujet</th><th>Société</th><th>Commercial</th>'
    content += '<th>Date</th><th>Durée</th><th>Résultat</th><th>Prochaine action</th>'
    content += '</tr></thead><tbody>'
    content += rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucune activité</td></tr>'
    content += '</tbody></table></div>'

    return render_page(content, active='activites', page_title='Activités')


@app.route('/activites/nouvelle', methods=['GET', 'POST'])
@login_required
def activites_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            commercial_id = int(request.form.get('commercial_id') or 0) or current_user.id
            cur.execute("""
                INSERT INTO activites
                (type, sujet, prospect_id, client_id, commercial_id, date_activite,
                 duree_min, resultat, notes, prochaine_action, date_prochaine_action, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (request.form.get('type'),
                  request.form.get('sujet'),
                  int(request.form.get('prospect_id') or 0) or None,
                  int(request.form.get('client_id') or 0) or None,
                  commercial_id,
                  request.form.get('date_activite') or datetime.now().isoformat(),
                  int(request.form.get('duree_min') or 0),
                  request.form.get('resultat'),
                  request.form.get('notes'),
                  request.form.get('prochaine_action'),
                  request.form.get('date_prochaine_action'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Activité enregistrée', 'success')

            # Créer une relance auto si prochaine action définie
            if request.form.get('prochaine_action') and request.form.get('date_prochaine_action'):
                cur.execute("""
                    INSERT INTO relances
                    (type, prospect_id, client_id, commercial_id, date_prevue, statut, message, created_at)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (request.form.get('type'),
                      int(request.form.get('prospect_id') or 0) or None,
                      int(request.form.get('client_id') or 0) or None,
                      commercial_id,
                      request.form.get('date_prochaine_action'),
                      'a_faire',
                      request.form.get('prochaine_action'),
                      datetime.now().isoformat()))
                db.commit()
                flash('🔔 Relance automatique créée', 'success')

            return redirect('/activites')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, raison_sociale FROM prospects ORDER BY raison_sociale LIMIT 100")
    prospects = cur.fetchall()
    cur.execute("SELECT id, raison_sociale FROM clients ORDER BY raison_sociale LIMIT 100")
    clients = cur.fetchall()
    cur.execute("SELECT id, nom_complet FROM users WHERE role='commercial' AND actif=1")
    coms = cur.fetchall()

    opts_pros = ''.join('<option value="' + str(p["id"]) + '">' + str(p["raison_sociale"]) + '</option>' for p in prospects)
    opts_cli = ''.join('<option value="' + str(c["id"]) + '">' + str(c["raison_sociale"]) + '</option>' for c in clients)
    opts_com = ''.join('<option value="' + str(c["id"]) + '"' + (' selected' if c["id"] == current_user.id else '') + '>' + str(c["nom_complet"]) + '</option>' for c in coms)

    prospect_preselected = request.args.get('prospect_id', '')

    content = '<h1>📞 Nouvelle activité</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Type *</label><select name="type" required>'
    content += '<option value="appel">📞 Appel</option>'
    content += '<option value="visite">🚗 Visite</option>'
    content += '<option value="email">📧 Email</option>'
    content += '<option value="reunion">🤝 Réunion</option>'
    content += '<option value="demo">💻 Démonstration</option>'
    content += '</select></div>'
    content += '<div><label>Date activité</label><input type="datetime-local" name="date_activite" value="' + datetime.now().strftime('%Y-%m-%dT%H:%M') + '"></div>'
    content += '<div style="grid-column:1/-1"><label>Sujet</label><input type="text" name="sujet" placeholder="Présentation produit, relance devis..." autofocus></div>'
    content += '<div><label>Prospect</label><select name="prospect_id"><option value="">— Aucun —</option>' + opts_pros + '</select></div>'
    content += '<div><label>Client</label><select name="client_id"><option value="">— Aucun —</option>' + opts_cli + '</select></div>'
    content += '<div><label>Durée (min)</label><input type="number" name="duree_min" value="30"></div>'
    content += '<div><label>Résultat</label><select name="resultat">'
    content += '<option value="positif">✅ Positif</option>'
    content += '<option value="a_suivre">⏳ À suivre</option>'
    content += '<option value="negatif">❌ Négatif</option>'
    content += '<option value="sans_reponse">📵 Sans réponse</option>'
    content += '</select></div>'
    content += '<div><label>Commercial</label><select name="commercial_id">' + opts_com + '</select></div>'
    content += '<div><label>Prochaine action</label><input type="text" name="prochaine_action" placeholder="Rappeler, envoyer devis..."></div>'
    content += '<div><label>Date prochaine action</label><input type="date" name="date_prochaine_action"></div>'
    content += '<div style="grid-column:1/-1"><label>Notes</label><textarea name="notes" rows="3"></textarea></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Enregistrer</button>'
    content += '<a href="/activites" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='activites', page_title='Nouvelle activité')


# ═══════════════════════════════════════════════════════════════
# 💰 DEVIS
# ═══════════════════════════════════════════════════════════════

@app.route('/devis')
@login_required
def devis_liste():
    db = get_db()
    cur = db.cursor()
    is_admin = current_user.role in ('admin', 'manager')
    statut_f = request.args.get('statut', '')

    sql = """
        SELECT d.*, c.raison_sociale AS client_nom, p.raison_sociale AS prospect_nom,
               u.nom_complet AS commercial_nom
        FROM devis d
        LEFT JOIN clients c ON c.id=d.client_id
        LEFT JOIN prospects p ON p.id=d.prospect_id
        LEFT JOIN users u ON u.id=d.commercial_id
        WHERE 1=1
    """
    params = []
    if not is_admin:
        sql += " AND d.commercial_id=?"
        params.append(current_user.id)
    if statut_f:
        sql += " AND d.statut=?"
        params.append(statut_f)
    sql += " ORDER BY d.id DESC LIMIT 200"
    cur.execute(sql, params)
    devis = cur.fetchall()

    total_montant = sum(d['montant_ttc'] or 0 for d in devis)
    acceptes = [d for d in devis if d['statut'] == 'accepte']
    taux_conv = (len(acceptes) / len(devis) * 100) if devis else 0

    rows = ''
    for d in devis:
        statut_badge = {
            'brouillon': 'badge-gray',
            'envoye': 'badge-blue',
            'accepte': 'badge-green',
            'refuse': 'badge-red',
            'expire': 'badge-orange',
        }.get(d['statut'], 'badge-gray')
        societe = d['client_nom'] or d['prospect_nom'] or '—'
        rows += (
            '<tr><td><strong style="color:#7c3aed">' + str(d["numero"]) + '</strong></td>'
            + '<td>' + str(societe) + '</td>'
            + '<td>' + str(d["commercial_nom"] or "—") + '</td>'
            + '<td>' + str((d["date_emission"] or "")[:10]) + '</td>'
            + '<td style="text-align:right">' + f'{d["montant_ht"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{d["montant_ttc"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(d["statut"]) + '</span></td>'
            + '<td><a href="/devis/' + str(d["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">💰 Devis — ' + str(len(devis)) + '</h1>'
    content += '<a href="/devis/nouveau" class="btn btn-primary">+ Nouveau devis</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#7c3aed,#6d28d9)"><div class="kpi-icon">📄</div><div class="kpi-label">Total devis</div><div class="kpi-value">' + str(len(devis)) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">Montant TTC</div><div class="kpi-value" style="font-size:18px">' + f'{total_montant:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">✅</div><div class="kpi-label">Acceptés</div><div class="kpi-value">' + str(len(acceptes)) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">📊</div><div class="kpi-label">Taux conversion</div><div class="kpi-value">' + f'{taux_conv:.1f}' + '%</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/devis" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Tous</a> '
    for s in ['brouillon', 'envoye', 'accepte', 'refuse', 'expire']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/devis?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>N° Devis</th><th>Client/Prospect</th><th>Commercial</th><th>Date</th>'
    content += '<th style="text-align:right">HT</th><th style="text-align:right">TTC</th><th>Statut</th><th>Actions</th>'
    content += '</tr></thead><tbody>'
    content += rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun devis</td></tr>'
    content += '</tbody></table></div>'

    return render_page(content, active='devis', page_title='Devis')


@app.route('/devis/nouveau', methods=['GET', 'POST'])
@login_required
def devis_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            commercial_id = int(request.form.get('commercial_id') or 0) or current_user.id
            montant_ht = float(request.form.get('montant_ht') or 0)

            cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM devis")
            nid = cur.fetchone()[0]
            numero = 'DEV-' + datetime.now().strftime('%Y%m') + '-' + f'{nid:04d}'

            cur.execute("""
                INSERT INTO devis
                (numero, client_id, prospect_id, commercial_id, date_emission, date_validite,
                 montant_ht, tva, montant_ttc, statut, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (numero,
                  int(request.form.get('client_id') or 0) or None,
                  int(request.form.get('prospect_id') or 0) or None,
                  commercial_id,
                  request.form.get('date_emission') or datetime.now().strftime('%Y-%m-%d'),
                  request.form.get('date_validite'),
                  montant_ht, montant_ht * 0.18, montant_ht * 1.18,
                  request.form.get('statut') or 'brouillon',
                  request.form.get('notes'),
                  datetime.now().isoformat()))
            db.commit()
            log_action(current_user.id, 'CREATE_DEVIS', numero, 'devis', cur.lastrowid)
            flash('✅ Devis ' + numero + ' créé', 'success')
            return redirect('/devis')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, raison_sociale FROM clients ORDER BY raison_sociale LIMIT 100")
    clients = cur.fetchall()
    cur.execute("SELECT id, raison_sociale FROM prospects ORDER BY raison_sociale LIMIT 100")
    prospects = cur.fetchall()
    cur.execute("SELECT id, nom_complet FROM users WHERE role='commercial' AND actif=1")
    coms = cur.fetchall()

    opts_cli = ''.join('<option value="' + str(c["id"]) + '">' + str(c["raison_sociale"]) + '</option>' for c in clients)
    opts_pros = ''.join('<option value="' + str(p["id"]) + '">' + str(p["raison_sociale"]) + '</option>' for p in prospects)
    opts_com = ''.join('<option value="' + str(c["id"]) + '"' + (' selected' if c["id"] == current_user.id else '') + '>' + str(c["nom_complet"]) + '</option>' for c in coms)

    content = '<h1>💰 Nouveau devis</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Client existant</label><select name="client_id"><option value="">— Aucun —</option>' + opts_cli + '</select></div>'
    content += '<div><label>Ou prospect</label><select name="prospect_id"><option value="">— Aucun —</option>' + opts_pros + '</select></div>'
    content += '<div><label>Commercial</label><select name="commercial_id">' + opts_com + '</select></div>'
    content += '<div><label>Statut</label><select name="statut">'
    content += '<option value="brouillon">Brouillon</option>'
    content += '<option value="envoye">Envoyé</option>'
    content += '<option value="accepte">Accepté</option>'
    content += '</select></div>'
    content += '<div><label>Date émission</label><input type="date" name="date_emission" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Date validité</label><input type="date" name="date_validite" value="' + (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d') + '"></div>'
    content += '<div style="grid-column:1/-1"><label>Montant HT (FCFA) *</label><input type="number" step="1000" name="montant_ht" required value="1000000" autofocus></div>'
    content += '<div style="grid-column:1/-1;background:#f5f3ff;padding:12px;border-radius:8px;font-size:12.5px;color:#6d28d9">💡 TVA (18%) et TTC calculés automatiquement par trigger SQL</div>'
    content += '<div style="grid-column:1/-1"><label>Notes</label><textarea name="notes" rows="3"></textarea></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer le devis</button>'
    content += '<a href="/devis" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='devis', page_title='Nouveau devis')


@app.route('/devis/<int:did>', methods=['GET', 'POST'])
@login_required
def devis_detail(did):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT d.*, c.raison_sociale AS client_nom, p.raison_sociale AS prospect_nom,
               u.nom_complet AS commercial_nom
        FROM devis d
        LEFT JOIN clients c ON c.id=d.client_id
        LEFT JOIN prospects p ON p.id=d.prospect_id
        LEFT JOIN users u ON u.id=d.commercial_id
        WHERE d.id=?
    """, (did,))
    d = cur.fetchone()
    if not d:
        flash('❌ Devis introuvable', 'error')
        return redirect('/devis')

    if request.method == 'POST':
        try:
            new_statut = request.form.get('statut') or d['statut']
            cur.execute("UPDATE devis SET statut=? WHERE id=?", (new_statut, did))
            db.commit()
            flash('✅ Devis mis à jour : ' + new_statut, 'success')
            return redirect('/devis/' + str(did))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    statut_badge = {'brouillon': 'badge-gray', 'envoye': 'badge-blue',
                    'accepte': 'badge-green', 'refuse': 'badge-red',
                    'expire': 'badge-orange'}.get(d['statut'], 'badge-gray')
    societe = d['client_nom'] or d['prospect_nom'] or '—'

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">💰 Devis ' + str(d["numero"]) + ' <span class="badge ' + statut_badge + '">' + str(d["statut"]) + '</span></h1>'
    content += '<div><a href="/devis/' + str(did) + '/pdf" class="btn btn-primary">📄 PDF</a> '
    content += '<a href="/devis" class="btn btn-secondary" style="margin-left:6px">← Retour</a></div></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#7c3aed,#6d28d9)"><div class="kpi-label">Montant HT</div><div class="kpi-value" style="font-size:18px">' + f'{d["montant_ht"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-label">TVA 18%</div><div class="kpi-value" style="font-size:18px">' + f'{d["tva"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Montant TTC</div><div class="kpi-value" style="font-size:18px">' + f'{d["montant_ttc"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>📋 Informations</h2><table>'
    content += '<tr><td><strong>Client/Prospect</strong></td><td>' + str(societe) + '</td></tr>'
    content += '<tr><td><strong>Commercial</strong></td><td>' + str(d["commercial_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Date émission</strong></td><td>' + str((d["date_emission"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Date validité</strong></td><td>' + str((d["date_validite"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Accepté le</strong></td><td>' + str((d["date_acceptation"] or "—")[:10]) + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>✏️ Changer le statut</h2>'
    content += '<form method="post">'
    content += '<div style="margin-bottom:16px"><label>Statut</label><select name="statut">'
    for k, l in [('brouillon', 'Brouillon'), ('envoye', 'Envoyé'),
                 ('accepte', 'Accepté'), ('refuse', 'Refusé'), ('expire', 'Expiré')]:
        sel = ' selected' if d['statut'] == k else ''
        content += '<option value="' + k + '"' + sel + '>' + l + '</option>'
    content += '</select></div>'
    content += '<button type="submit" class="btn btn-success">💾 Mettre à jour</button>'
    content += '</form></div>'
    content += '</div>'

    return render_page(content, active='devis', page_title='Devis')


@app.route('/devis/<int:did>/pdf')
@login_required
def devis_pdf(did):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT d.*, c.raison_sociale AS client_nom, p.raison_sociale AS prospect_nom,
               u.nom_complet AS commercial_nom
        FROM devis d
        LEFT JOIN clients c ON c.id=d.client_id
        LEFT JOIN prospects p ON p.id=d.prospect_id
        LEFT JOIN users u ON u.id=d.commercial_id
        WHERE d.id=?
    """, (did,))
    d = cur.fetchone()
    if not d:
        flash('❌ Devis introuvable', 'error')
        return redirect('/devis')

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Header violet
    c.setFillColor(colors.HexColor('#7c3aed'))
    c.rect(0, h - 35*mm, w, 35*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 18)
    c.drawString(15*mm, h - 15*mm, "OMEGA CRM")
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, h - 22*mm, "Force de vente · PME CEDEAO")
    c.setFont('Helvetica-Bold', 14)
    c.drawRightString(w - 15*mm, h - 15*mm, "DEVIS " + str(d["numero"]))
    c.setFont('Helvetica', 9)
    c.drawRightString(w - 15*mm, h - 22*mm, "Date : " + str((d["date_emission"] or "")[:10]))

    # Client
    y = h - 50*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(15*mm, y, "CLIENT")
    c.setFont('Helvetica', 10)
    y -= 6*mm
    societe = d['client_nom'] or d['prospect_nom'] or '—'
    c.drawString(15*mm, y, str(societe))

    y = h - 50*mm
    c.setFont('Helvetica-Bold', 11)
    c.drawString(110*mm, y, "COMMERCIAL")
    c.setFont('Helvetica', 10)
    y -= 6*mm
    c.drawString(110*mm, y, str(d["commercial_nom"] or "—"))

    # Tableau
    y -= 25*mm
    c.setFillColor(colors.HexColor('#5b21b6'))
    c.rect(15*mm, y - 8*mm, w - 30*mm, 8*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(18*mm, y - 5*mm, "Désignation")
    c.drawRightString(w - 18*mm, y - 5*mm, "Montant")

    y -= 14*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica', 10)
    c.drawString(18*mm, y, "Prestation commerciale OMEGA")
    c.drawRightString(w - 18*mm, y, f'{d["montant_ht"]:,.0f}' + ' FCFA')

    y -= 8*mm
    c.drawString(18*mm, y, "TVA (18%)")
    c.drawRightString(w - 18*mm, y, f'{d["tva"]:,.0f}' + ' FCFA')

    # Total
    y -= 15*mm
    c.setFillColor(colors.HexColor('#d1fae5'))
    c.rect(110*mm, y - 5*mm, w - 125*mm, 14*mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#047857'))
    c.setFont('Helvetica-Bold', 12)
    c.drawString(115*mm, y, "TOTAL TTC")
    c.drawRightString(w - 18*mm, y, f'{d["montant_ttc"]:,.0f}' + ' FCFA')

    # Footer
    c.setFillColor(colors.grey)
    c.setFont('Helvetica', 7)
    c.drawString(15*mm, 10*mm, "OMEGA CRM — Dakar, Sénégal · contact@omega.sn · +221 77 654 28 03")
    c.drawRightString(w - 15*mm, 10*mm, "Devis valable jusqu'au " + str((d["date_validite"] or "")[:10]))

    c.showPage()
    c.save()
    buf.seek(0)

    log_action(current_user.id, 'PDF_DEVIS', str(d["numero"]), 'devis', did)
    return send_file(buf, mimetype='application/pdf',
                     download_name='devis_' + str(d["numero"]) + '.pdf')


# ═══════════════════════════════════════════════════════════════
# 🎯 OBJECTIFS & COMMISSIONS
# ═══════════════════════════════════════════════════════════════

@app.route('/objectifs')
@login_required
def objectifs_liste():
    db = get_db()
    cur = db.cursor()
    is_admin = current_user.role in ('admin', 'manager')

    sql = """
        SELECT o.*, u.nom_complet AS commercial_nom, u.commission_pct
        FROM objectifs o
        LEFT JOIN users u ON u.id=o.commercial_id
        WHERE 1=1
    """
    params = []
    if not is_admin:
        sql += " AND o.commercial_id=?"
        params.append(current_user.id)
    sql += " ORDER BY o.periode DESC, o.id DESC LIMIT 100"
    cur.execute(sql, params)
    objectifs = cur.fetchall()

    rows = ''
    for o in objectifs:
        pct = (o['ca_realise'] / o['objectif_ca'] * 100) if o['objectif_ca'] > 0 else 0
        color = '#10b981' if pct >= 80 else '#f59e0b' if pct >= 50 else '#ef4444'
        commission_due = o['ca_realise'] * (o['commission_pct'] or 3) / 100
        rows += (
            '<tr><td><strong>' + str(o["commercial_nom"] or "—") + '</strong></td>'
            + '<td>' + str(o["periode"]) + '</td>'
            + '<td style="text-align:right">' + f'{o["objectif_ca"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:700">' + f'{o["ca_realise"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center">' + f'{pct:.1f}' + '%<br><div class="progress" style="margin-top:4px"><div class="progress-bar" style="width:' + f'{min(pct,100):.0f}' + '%;background:' + color + '"></div></div></td>'
            + '<td style="text-align:right">' + str(o["nb_visites_realise"]) + ' / ' + str(o["nb_visites_cible"]) + '</td>'
            + '<td style="text-align:right;font-weight:800;color:#7c3aed">' + f'{commission_due:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + ('badge-green' if o['commission_payee'] else 'badge-orange') + '">' + ('Payée' if o['commission_payee'] else 'À payer') + '</span></td></tr>'
        )

    total_objectif = sum(o['objectif_ca'] for o in objectifs)
    total_realise = sum(o['ca_realise'] for o in objectifs)
    total_comm = sum(o['ca_realise'] * (o['commission_pct'] or 3) / 100 for o in objectifs)

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🎯 Objectifs & Commissions</h1>'
    content += '<a href="/objectifs/nouveau" class="btn btn-primary">+ Nouvel objectif</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#7c3aed,#6d28d9)"><div class="kpi-icon">🎯</div><div class="kpi-label">Objectif total</div><div class="kpi-value" style="font-size:18px">' + f'{total_objectif:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">CA réalisé</div><div class="kpi-value" style="font-size:18px">' + f'{total_realise:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">💵</div><div class="kpi-label">Commissions dues</div><div class="kpi-value" style="font-size:18px">' + f'{total_comm:,.0f}' + ' F</div></div>'
    pct_global = (total_realise / total_objectif * 100) if total_objectif > 0 else 0
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">📊</div><div class="kpi-label">Taux global</div><div class="kpi-value">' + f'{pct_global:.1f}' + '%</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>Commercial</th><th>Période</th>'
    content += '<th style="text-align:right">Objectif</th>'
    content += '<th style="text-align:right">Réalisé</th>'
    content += '<th style="text-align:center">Progression</th>'
    content += '<th style="text-align:right">Visites</th>'
    content += '<th style="text-align:right">Commission</th>'
    content += '<th>Statut</th></tr></thead><tbody>'
    content += rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun objectif</td></tr>'
    content += '</tbody></table></div>'

    return render_page(content, active='objectifs', page_title='Objectifs')


@app.route('/objectifs/nouveau', methods=['GET', 'POST'])
@login_required
def objectifs_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO objectifs
                (commercial_id, periode, objectif_ca, ca_realise,
                 nb_visites_cible, nb_visites_realise, commission_calculee,
                 commission_payee, statut, created_at)
                VALUES (?,?,?,?,?,?,?,0,'en_cours',?)
            """, (int(request.form.get('commercial_id') or 0),
                  request.form.get('periode') or datetime.now().strftime('%Y-%m'),
                  float(request.form.get('objectif_ca') or 0),
                  0,
                  int(request.form.get('nb_visites_cible') or 0),
                  0, 0,
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Objectif créé', 'success')
            return redirect('/objectifs')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom_complet FROM users WHERE role='commercial' AND actif=1")
    coms = cur.fetchall()
    opts_com = ''.join('<option value="' + str(c["id"]) + '">' + str(c["nom_complet"]) + '</option>' for c in coms)

    content = '<h1>🎯 Nouvel objectif</h1>'
    content += '<form method="post" class="card" style="max-width:600px">'
    content += '<div style="margin-bottom:16px"><label>Commercial *</label><select name="commercial_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_com + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Période (YYYY-MM) *</label>'
    content += '<input type="text" name="periode" required value="' + datetime.now().strftime('%Y-%m') + '" pattern="[0-9]{4}-[0-9]{2}"></div>'
    content += '<div style="margin-bottom:16px"><label>Objectif CA (FCFA) *</label>'
    content += '<input type="number" step="100000" name="objectif_ca" required value="5000000" autofocus></div>'
    content += '<div style="margin-bottom:16px"><label>Nb visites cible</label>'
    content += '<input type="number" name="nb_visites_cible" value="20"></div>'
    content += '<button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/objectifs" class="btn btn-secondary" style="margin-left:8px">Annuler</a>'
    content += '</form>'
    return render_page(content, active='objectifs', page_title='Nouvel objectif')


# ═══════════════════════════════════════════════════════════════
# 🗺️ TOURNÉES OPTIMISÉES
# ═══════════════════════════════════════════════════════════════

@app.route('/tournees')
@login_required
def tournees_liste():
    db = get_db()
    cur = db.cursor()
    is_admin = current_user.role in ('admin', 'manager')

    sql = """
        SELECT t.*, u.nom_complet AS commercial_nom
        FROM tournees t
        LEFT JOIN users u ON u.id=t.commercial_id
        WHERE 1=1
    """
    params = []
    if not is_admin:
        sql += " AND t.commercial_id=?"
        params.append(current_user.id)
    sql += " ORDER BY t.date_tournee DESC LIMIT 100"
    cur.execute(sql, params)
    tournees = cur.fetchall()

    rows = ''
    for t in tournees:
        statut_badge = {'planifiee': 'badge-blue', 'en_cours': 'badge-orange',
                        'terminee': 'badge-green', 'annulee': 'badge-gray'}.get(t['statut'], 'badge-gray')
        pct = (t['nb_visites_realisees'] / t['nb_visites_prevues'] * 100) if t['nb_visites_prevues'] > 0 else 0
        rows += (
            '<tr><td><strong>#' + str(t["id"]) + '</strong></td>'
            + '<td>' + str(t["commercial_nom"] or "—") + '</td>'
            + '<td>' + str((t["date_tournee"] or "")[:10]) + '</td>'
            + '<td>' + str(t["zone"] or "—") + '</td>'
            + '<td style="text-align:center">' + str(t["nb_visites_realisees"]) + ' / ' + str(t["nb_visites_prevues"]) + '<br><div class="progress" style="margin-top:4px"><div class="progress-bar" style="width:' + f'{min(pct,100):.0f}' + '%"></div></div></td>'
            + '<td style="text-align:right">' + f'{t["distance_km"]:.0f}' + ' km</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(t["statut"]) + '</span></td>'
            + '<td><a href="/tournees/' + str(t["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🗺️ Tournées optimisées</h1>'
    content += '<a href="/tournees/nouvelle" class="btn btn-primary">+ Nouvelle tournée</a></div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>#</th><th>Commercial</th><th>Date</th><th>Zone</th>'
    content += '<th style="text-align:center">Visites</th><th style="text-align:right">Distance</th>'
    content += '<th>Statut</th><th>Actions</th></tr></thead><tbody>'
    content += rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucune tournée</td></tr>'
    content += '</tbody></table></div>'

    return render_page(content, active='tournees', page_title='Tournées')


@app.route('/tournees/nouvelle', methods=['GET', 'POST'])
@login_required
def tournees_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            commercial_id = int(request.form.get('commercial_id') or 0) or current_user.id
            cur.execute("""
                INSERT INTO tournees
                (commercial_id, date_tournee, zone, nb_visites_prevues,
                 nb_visites_realisees, statut, distance_km, notes, created_at)
                VALUES (?,?,?,?,0,?,?,?,?)
            """, (commercial_id,
                  request.form.get('date_tournee'),
                  request.form.get('zone'),
                  int(request.form.get('nb_visites_prevues') or 0),
                  'planifiee',
                  float(request.form.get('distance_km') or 0),
                  request.form.get('notes'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Tournée créée', 'success')
            return redirect('/tournees')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom_complet FROM users WHERE role='commercial' AND actif=1")
    coms = cur.fetchall()
    opts_com = ''.join('<option value="' + str(c["id"]) + '"' + (' selected' if c["id"] == current_user.id else '') + '>' + str(c["nom_complet"]) + '</option>' for c in coms)

    content = '<h1>🗺️ Nouvelle tournée</h1>'
    content += '<form method="post" class="card" style="max-width:600px">'
    content += '<div style="margin-bottom:16px"><label>Commercial *</label><select name="commercial_id">' + opts_com + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Date *</label><input type="date" name="date_tournee" required value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div style="margin-bottom:16px"><label>Zone</label><input type="text" name="zone" placeholder="Dakar Centre, Thiès Nord..." autofocus></div>'
    content += '<div style="margin-bottom:16px"><label>Nb visites prévues</label><input type="number" name="nb_visites_prevues" value="5"></div>'
    content += '<div style="margin-bottom:16px"><label>Distance estimée (km)</label><input type="number" step="0.1" name="distance_km" value="0"></div>'
    content += '<div style="margin-bottom:16px"><label>Notes</label><textarea name="notes" rows="3"></textarea></div>'
    content += '<button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/tournees" class="btn btn-secondary" style="margin-left:8px">Annuler</a>'
    content += '</form>'
    return render_page(content, active='tournees', page_title='Nouvelle tournée')


@app.route('/tournees/<int:tid>')
@login_required
def tournees_detail(tid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT t.*, u.nom_complet AS commercial_nom
        FROM tournees t LEFT JOIN users u ON u.id=t.commercial_id
        WHERE t.id=?
    """, (tid,))
    t = cur.fetchone()
    if not t:
        flash('❌ Tournée introuvable', 'error')
        return redirect('/tournees')

    cur.execute("""
        SELECT tp.*, p.raison_sociale AS prospect_nom, p.ville, c.raison_sociale AS client_nom
        FROM tournee_points tp
        LEFT JOIN prospects p ON p.id=tp.prospect_id
        LEFT JOIN clients c ON c.id=tp.client_id
        WHERE tp.tournee_id=?
        ORDER BY tp.ordre
    """, (tid,))
    points = cur.fetchall()

    points_html = ''
    for pt in points:
        societe = pt['prospect_nom'] or pt['client_nom'] or '—'
        statut_badge = {'a_visiter': 'badge-blue', 'visite': 'badge-green', 'annule': 'badge-gray'}.get(pt['statut'], 'badge-gray')
        points_html += (
            '<tr><td>' + str(pt["ordre"]) + '</td>'
            + '<td><strong>' + str(societe) + '</strong></td>'
            + '<td>' + str(pt["ville"] or "—") + '</td>'
            + '<td>' + str(pt["heure_prevue"] or "—") + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(pt["statut"]) + '</span></td></tr>'
        )

    statut_badge = {'planifiee': 'badge-blue', 'en_cours': 'badge-orange',
                    'terminee': 'badge-green', 'annulee': 'badge-gray'}.get(t['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🗺️ Tournée #' + str(t["id"]) + ' <span class="badge ' + statut_badge + '">' + str(t["statut"]) + '</span></h1>'
    content += '<a href="/tournees" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#7c3aed,#6d28d9)"><div class="kpi-label">Zone</div><div class="kpi-value" style="font-size:18px">' + str(t["zone"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-label">Date</div><div class="kpi-value" style="font-size:18px">' + str((t["date_tournee"] or "")[:10]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Visites</div><div class="kpi-value">' + str(t["nb_visites_realisees"]) + ' / ' + str(t["nb_visites_prevues"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-label">Distance</div><div class="kpi-value" style="font-size:20px">' + f'{t["distance_km"]:.0f}' + ' km</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📍 Points de visite</h2>'
    content += '<table><thead><tr><th>Ordre</th><th>Société</th><th>Ville</th><th>Heure</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (points_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:30px">Aucun point de visite</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='tournees', page_title='Tournée')


# ═══════════════════════════════════════════════════════════════
# 🔔 RELANCES
# ═══════════════════════════════════════════════════════════════

@app.route('/relances')
@login_required
def relances_liste():
    db = get_db()
    cur = db.cursor()
    is_admin = current_user.role in ('admin', 'manager')

    sql = """
        SELECT r.*, p.raison_sociale AS prospect_nom, c.raison_sociale AS client_nom,
               u.nom_complet AS commercial_nom
        FROM relances r
        LEFT JOIN prospects p ON p.id=r.prospect_id
        LEFT JOIN clients c ON c.id=r.client_id
        LEFT JOIN users u ON u.id=r.commercial_id
        WHERE 1=1
    """
    params = []
    if not is_admin:
        sql += " AND r.commercial_id=?"
        params.append(current_user.id)
    sql += " ORDER BY r.date_prevue ASC LIMIT 200"
    cur.execute(sql, params)
    relances = cur.fetchall()

    a_faire = sum(1 for r in relances if r['statut'] == 'a_faire')
    retard = sum(1 for r in relances if r['statut'] == 'a_faire' and r['date_prevue'] < datetime.now().strftime('%Y-%m-%d'))
    faits = sum(1 for r in relances if r['statut'] == 'fait')

    rows = ''
    for r in relances:
        type_icon = {'appel': '📞', 'email': '📧', 'visite': '🚗'}.get(r['type'], '📌')
        societe = r['prospect_nom'] or r['client_nom'] or '—'
        statut_badge = {'a_faire': 'badge-blue', 'fait': 'badge-green', 'retard': 'badge-red'}.get(r['statut'], 'badge-gray')
        # Détecter retard auto
        if r['statut'] == 'a_faire' and r['date_prevue'] and r['date_prevue'] < datetime.now().strftime('%Y-%m-%d'):
            statut_badge = 'badge-red'

        rows += (
            '<tr><td>' + type_icon + ' ' + str(r["type"]) + '</td>'
            + '<td>' + str(societe) + '</td>'
            + '<td>' + str(r["message"] or "—") + '</td>'
            + '<td>' + str(r["commercial_nom"] or "—") + '</td>'
            + '<td>' + str(r["date_prevue"] or "—") + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(r["statut"]) + '</span></td>'
            + '<td><a href="/relances/' + str(r["id"]) + '/fait" class="btn btn-success" style="padding:4px 10px;font-size:11px">✅ Fait</a></td></tr>'
        )

    content = '<h1>🔔 Relances — ' + str(len(relances)) + '</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#7c3aed,#6d28d9)"><div class="kpi-icon">📋</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(len(relances)) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">⏳</div><div class="kpi-label">À faire</div><div class="kpi-value">' + str(a_faire) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">🚨</div><div class="kpi-label">En retard</div><div class="kpi-value">' + str(retard) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Faits</div><div class="kpi-value">' + str(faits) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>Type</th><th>Prospect/Client</th><th>Message</th><th>Commercial</th>'
    content += '<th>Date prévue</th><th>Statut</th><th>Action</th></tr></thead><tbody>'
    content += rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucune relance</td></tr>'
    content += '</tbody></table></div>'

    return render_page(content, active='relances', page_title='Relances')


@app.route('/relances/<int:rid>/fait')
@login_required
def relances_fait(rid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        UPDATE relances SET statut='fait', date_realisee=?
        WHERE id=?
    """, (datetime.now().strftime('%Y-%m-%d'), rid))
    db.commit()
    flash('✅ Relance marquée comme faite', 'success')
    return redirect('/relances')


# ═══════════════════════════════════════════════════════════════
# 📈 RAPPORTS
# ═══════════════════════════════════════════════════════════════

@app.route('/rapports')
@login_required
def rapports_index():
    db = get_db()
    cur = db.cursor()
    is_admin = current_user.role in ('admin', 'manager')

    filter_sql = ""
    params = ()
    if not is_admin:
        filter_sql = " AND commercial_id=?"
        params = (current_user.id,)

    def sc(sql, p=()):
        cur.execute(sql, p)
        r = cur.fetchone()
        return r[0] if r and r[0] is not None else 0

    total_prospects = sc("SELECT COUNT(*) FROM prospects WHERE 1=1" + filter_sql, params)
    total_clients = sc("SELECT COUNT(*) FROM clients WHERE 1=1" + filter_sql, params)
    total_opps = sc("SELECT COUNT(*) FROM opportunites WHERE 1=1" + filter_sql, params)
    opps_gagnees = sc("SELECT COUNT(*) FROM opportunites WHERE statut='gagnee'" + filter_sql, params)
    devis_acceptes = sc("SELECT COUNT(*) FROM devis WHERE statut='accepte'" + filter_sql, params)
    devis_total = sc("SELECT COUNT(*) FROM devis WHERE 1=1" + filter_sql, params)
    ca_total = sc("SELECT COALESCE(SUM(montant_ttc),0) FROM devis WHERE statut='accepte'" + filter_sql, params)
    activites_30j = sc("SELECT COUNT(*) FROM activites WHERE date_activite >= date('now','-30 days')" + filter_sql, params)

    taux_conv_global = (opps_gagnees / total_opps * 100) if total_opps > 0 else 0
    taux_conv_devis = (devis_acceptes / devis_total * 100) if devis_total > 0 else 0

    # CA par commercial
    cur.execute("""
        SELECT u.nom_complet, COALESCE(SUM(d.montant_ttc),0) AS ca, COUNT(d.id) AS nb
        FROM users u
        LEFT JOIN devis d ON d.commercial_id=u.id AND d.statut='accepte'
        WHERE u.role='commercial'
        GROUP BY u.id
        ORDER BY ca DESC
    """)
    ca_par_com = cur.fetchall()

    com_html = ''.join(
        '<tr><td>' + str(c["nom_complet"]) + '</td>'
        + '<td style="text-align:right">' + str(c["nb"]) + '</td>'
        + '<td style="text-align:right;color:#10b981;font-weight:800">' + f'{c["ca"]:,.0f}' + ' F</td></tr>'
        for c in ca_par_com
    )

    # CA par secteur
    cur.execute("""
        SELECT p.secteur, COUNT(DISTINCT p.id) AS nb, COALESCE(SUM(o.montant_estime),0) AS montant
        FROM prospects p
        LEFT JOIN opportunites o ON o.prospect_id=p.id
        WHERE p.secteur IS NOT NULL
        GROUP BY p.secteur
        ORDER BY montant DESC LIMIT 10
    """)
    ca_secteur = cur.fetchall()
    secteur_html = ''.join(
        '<tr><td>' + str(s["secteur"]) + '</td>'
        + '<td style="text-align:right">' + str(s["nb"]) + '</td>'
        + '<td style="text-align:right">' + f'{s["montant"]:,.0f}' + ' F</td></tr>'
        for s in secteur
    )

    content = '<h1>📈 Rapports & KPIs CRM</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#7c3aed,#6d28d9)"><div class="kpi-icon">👥</div><div class="kpi-label">Prospects</div><div class="kpi-value">' + str(total_prospects) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🏢</div><div class="kpi-label">Clients</div><div class="kpi-value">' + str(total_clients) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">💰</div><div class="kpi-label">CA signé</div><div class="kpi-value" style="font-size:18px">' + f'{ca_total:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">🎯</div><div class="kpi-label">Taux conv. opps</div><div class="kpi-value">' + f'{taux_conv_global:.1f}' + '%</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div class="kpi-icon">📄</div><div class="kpi-label">Taux conv. devis</div><div class="kpi-value">' + f'{taux_conv_devis:.1f}' + '%</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#a855f7,#7e22ce)"><div class="kpi-icon">📞</div><div class="kpi-label">Activités 30j</div><div class="kpi-value">' + str(activites_30j) + '</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>🏆 CA par commercial</h2>'
    content += '<table><thead><tr><th>Commercial</th><th style="text-align:right">Devis</th><th style="text-align:right">CA signé</th></tr></thead>'
    content += '<tbody>' + (com_html or '<tr><td colspan="3" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'
    content += '<div class="card"><h2>📊 Top secteurs</h2>'
    content += '<table><thead><tr><th>Secteur</th><th style="text-align:right">Prospects</th><th style="text-align:right">Montant</th></tr></thead>'
    content += '<tbody>' + (secteur_html or '<tr><td colspan="3" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    content += '<div class="card" style="border-left-color:#10b981"><h2>🎯 Objectifs SM10 AGRO CRM</h2>'
    content += '<ul style="line-height:2;color:#334155;font-size:14px">'
    content += '<li>🌍 <strong>10 000 PME CEDEAO</strong> connectées</li>'
    content += '<li>📊 <strong>Pipeline digitalisé</strong> 100%</li>'
    content += '<li>📈 <strong>+30% taux de conversion</strong> commerciale</li>'
    content += '<li>🎯 <strong>Objectifs & commissions</strong> automatisés</li>'
    content += '<li>🗺️ <strong>Tournées optimisées</strong> multi-villes</li>'
    content += '</ul></div>'

    return render_page(content, active='rapports', page_title='Rapports')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
