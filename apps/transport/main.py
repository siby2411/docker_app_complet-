"""
🚛 Transport & Logistique — Application principale
Flotte · Chauffeurs · Missions · Colis · GPS · Douanes · Facturation
"""
from flask import Flask, render_template_string, redirect, url_for, session, request, jsonify, Response, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import sqlite3
import os
import io
import csv
import math
import random

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'omega-transport-secret-2026')

DB_PATH = '/app/data/transport.db'

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
# LAYOUT — DESIGN PRO SECTEUR TRANSPORT
# ═══════════════════════════════════════════════════════════════

LAYOUT = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — OMEGA Transport</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,-apple-system,sans-serif}}
body{{background:#f1f5f9;color:#1e293b;font-size:14px}}
.nav{{background:linear-gradient(135deg,#1e3a8a,#1e40af);color:#fff;padding:0 22px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 3px 12px rgba(0,0,0,.15);flex-wrap:wrap;border-bottom:4px solid #f97316}}
.nav-brand{{font-weight:900;font-size:18px;display:flex;align-items:center;gap:12px;padding:16px 0;letter-spacing:-0.3px}}
.nav-brand-icon{{width:40px;height:40px;background:#f97316;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(249,115,22,.4)}}
.nav-links{{display:flex;gap:2px;flex-wrap:wrap}}
.nav-links a{{color:#e0e7ff;text-decoration:none;padding:8px 14px;border-radius:8px;font-size:12.5px;font-weight:600;transition:.2s;display:flex;align-items:center;gap:6px}}
.nav-links a:hover{{background:rgba(255,255,255,.12);color:#fff}}
.nav-links a.active{{background:#f97316;color:#fff;box-shadow:0 4px 10px rgba(249,115,22,.4)}}
.nav-user{{font-size:12.5px;display:flex;gap:10px;align-items:center;color:#c7d2fe}}
.nav-user a{{color:#fff;text-decoration:none;background:rgba(0,0,0,.25);padding:7px 14px;border-radius:8px;font-weight:600}}
.container{{max-width:1600px;margin:0 auto;padding:24px}}
h1{{color:#1e3a8a;margin-bottom:20px;font-size:24px;font-weight:800;letter-spacing:-0.4px}}
h2{{color:#1e40af;font-size:18px;margin-bottom:14px;font-weight:700}}
.card{{background:#fff;padding:22px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04);margin-bottom:18px;border-left:4px solid #f97316}}
table{{width:100%;border-collapse:collapse}}
thead{{background:#1e3a8a;color:#fff}}
th{{padding:12px;text-align:left;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}}
td{{padding:11px;border-bottom:1px solid #f1f5f9;font-size:13.5px}}
tbody tr:hover{{background:#f8fafc}}
.btn{{display:inline-block;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px;border:none;cursor:pointer;transition:.15s;letter-spacing:.2px}}
.btn:hover{{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.15)}}
.btn-primary{{background:#1e40af;color:#fff}}
.btn-orange{{background:#f97316;color:#fff}}
.btn-success{{background:#10b981;color:#fff}}
.btn-danger{{background:#ef4444;color:#fff}}
.btn-warning{{background:#f59e0b;color:#fff}}
.btn-secondary{{background:#64748b;color:#fff}}
input,select,textarea{{width:100%;padding:11px 14px;border:2px solid #e2e8f0;border-radius:8px;font-size:13.5px;font-family:inherit;transition:.2s}}
input:focus,select:focus,textarea:focus{{outline:none;border-color:#1e40af;box-shadow:0 0 0 3px rgba(30,64,175,.1)}}
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
.route-timeline{{display:flex;align-items:center;gap:12px;padding:16px;background:#f8fafc;border-radius:10px;margin:14px 0}}
.route-dot{{width:14px;height:14px;border-radius:50%;flex-shrink:0}}
.route-dot-start{{background:#10b981}}
.route-dot-end{{background:#f97316}}
.route-line{{flex:1;height:3px;background:repeating-linear-gradient(90deg,#cbd5e1 0 8px,transparent 8px 14px)}}
.truck-card{{background:linear-gradient(135deg,#1e3a8a,#1e40af);color:#fff;padding:16px;border-radius:10px;cursor:pointer;transition:.2s;border-bottom:3px solid #f97316}}
.truck-card:hover{{transform:translateY(-3px);box-shadow:0 8px 20px rgba(30,58,138,.3)}}
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-brand">
    <div class="nav-brand-icon">🚛</div>
    <div>OMEGA TRANSPORT<span style="display:block;font-size:10px;font-weight:500;letter-spacing:2px;color:#c7d2fe">LOGISTIQUE & FRET CEDEAO</span></div>
  </div>
  <div class="nav-links">
    <a href="/" class="{a_dash}">📊 Dashboard</a>
    <a href="/flotte" class="{a_flotte}">🚛 Flotte</a>
    <a href="/chauffeurs" class="{a_chf}">👨‍✈️ Chauffeurs</a>
    <a href="/missions" class="{a_mis}">📦 Missions</a>
    <a href="/colis" class="{a_colis}">📮 Colis</a>
    <a href="/tracking" class="{a_track}">🗺️ Tracking</a>
    <a href="/entrepots" class="{a_ent}">🏭 Entrepôts</a>
    <a href="/douanes" class="{a_dou}">🛃 Douanes</a>
    <a href="/factures" class="{a_fac}">💰 Facturation</a>
    <a href="/alertes" class="{a_al}">🚨 Alertes</a>
    <a href="/rapports" class="{a_rap}">📈 KPI</a>
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


def render_page(content, active='dashboard', page_title='Transport'):
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
        a_flotte='active' if active == 'flotte' else '',
        a_chf='active' if active == 'chauffeurs' else '',
        a_mis='active' if active == 'missions' else '',
        a_colis='active' if active == 'colis' else '',
        a_track='active' if active == 'tracking' else '',
        a_ent='active' if active == 'entrepots' else '',
        a_dou='active' if active == 'douanes' else '',
        a_fac='active' if active == 'factures' else '',
        a_al='active' if active == 'alertes' else '',
        a_rap='active' if active == 'rapports' else '',
    )


@app.route('/health')
def health():
    return {'project': 'OMEGA TRANSPORT', 'service': 'transport-logistique',
            'status': 'ok', 'timestamp': datetime.now().isoformat(), 'version': '1.0'}


LOGIN_HTML = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Connexion — OMEGA Transport</title>
<style>body{{font-family:system-ui;background:linear-gradient(135deg,#1e3a8a,#1e40af);min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0}}
.box{{background:#fff;padding:42px;border-radius:16px;box-shadow:0 25px 70px rgba(0,0,0,.4);width:100%;max-width:420px;border-top:5px solid #f97316}}
.logo{{text-align:center;font-size:56px;margin-bottom:12px}}
h1{{color:#1e3a8a;margin:0 0 6px;text-align:center;font-size:22px;font-weight:900;letter-spacing:-0.3px}}
.subtitle{{text-align:center;color:#64748b;font-size:12px;margin-bottom:24px;letter-spacing:1.5px;text-transform:uppercase;font-weight:600}}
input{{width:100%;padding:14px;border:2px solid #e2e8f0;border-radius:10px;margin-bottom:14px;font-size:15px;box-sizing:border-box}}
input:focus{{outline:none;border-color:#1e40af;box-shadow:0 0 0 3px rgba(30,64,175,.1)}}
button{{width:100%;background:#f97316;color:#fff;padding:15px;border:none;border-radius:10px;font-weight:800;font-size:15px;cursor:pointer;letter-spacing:.5px;text-transform:uppercase}}
button:hover{{background:#ea580c}}
.err{{background:#fee2e2;color:#991b1b;padding:11px;border-radius:8px;margin-bottom:14px;font-size:13px;border-left:4px solid #ef4444}}
.hint{{margin-top:20px;padding:12px;background:#eff6ff;border-radius:8px;font-size:12px;color:#1e40af;text-align:center;border:1px dashed #93c5fd}}</style></head>
<body><div class="box">
<div class="logo">🚛</div>
<h1>OMEGA TRANSPORT</h1>
<div class="subtitle">Logistique & Fret CEDEAO</div>
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
        'vehicules_dispo': sc("SELECT COUNT(*) FROM vehicules WHERE statut='disponible'"),
        'vehicules_mission': sc("SELECT COUNT(*) FROM vehicules WHERE statut='en_mission'"),
        'chauffeurs_dispo': sc("SELECT COUNT(*) FROM chauffeurs WHERE statut='disponible'"),
        'missions_encours': sc("SELECT COUNT(*) FROM missions WHERE statut='en_cours'"),
        'missions_planifiees': sc("SELECT COUNT(*) FROM missions WHERE statut='planifiee'"),
        'missions_terminees': sc("SELECT COUNT(*) FROM missions WHERE statut='terminee'"),
        'colis_transit': sc("SELECT COUNT(*) FROM colis WHERE statut='en_transit'"),
        'alertes': sc("SELECT COUNT(*) FROM alertes WHERE traitee=0"),
        'ca_mois': sc("SELECT COALESCE(SUM(montant_fcfa),0) FROM missions WHERE statut='terminee' AND strftime('%Y-%m',date_arrivee_reelle)=strftime('%Y-%m','now')"),
        'tonnage_mois': sc("SELECT COALESCE(SUM(tonnage),0) FROM missions WHERE statut='terminee' AND strftime('%Y-%m',date_arrivee_reelle)=strftime('%Y-%m','now')"),
    }

    # Missions en cours avec infos
    cur.execute("""
        SELECT m.*, v.immatriculation, ch.nom_complet AS chauffeur_nom, c.nom AS client_nom
        FROM missions m
        LEFT JOIN vehicules v ON v.id=m.vehicule_id
        LEFT JOIN chauffeurs ch ON ch.id=m.chauffeur_id
        LEFT JOIN clients c ON c.id=m.client_id
        WHERE m.statut='en_cours'
        ORDER BY m.id DESC LIMIT 5
    """)
    missions_cours = cur.fetchall()

    missions_html = ''
    for m in missions_cours:
        missions_html += (
            '<tr><td><strong style="color:#1e40af">' + str(m["numero"]) + '</strong></td>'
            + '<td>' + str(m["client_nom"] or "—") + '</td>'
            + '<td>' + str(m["immatriculation"] or "—") + '</td>'
            + '<td>' + str(m["chauffeur_nom"] or "—") + '</td>'
            + '<td><span style="color:#10b981">●</span> ' + str(m["origine"] or "—") + ' → <span style="color:#f97316">●</span> ' + str(m["destination"] or "—") + '</td>'
            + '<td>' + f'{m["tonnage"]:.1f}' + ' T</td></tr>'
        )

    # Alertes
    cur.execute("SELECT * FROM alertes WHERE traitee=0 ORDER BY id DESC LIMIT 5")
    alertes = cur.fetchall()
    alertes_html = ''
    for a in alertes:
        color = {'critique': 'badge-red', 'warning': 'badge-orange', 'info': 'badge-blue'}.get(a['gravite'], 'badge-gray')
        alertes_html += (
            '<tr><td><span class="badge ' + color + '">' + str(a["type"]) + '</span></td>'
            + '<td>' + str(a["message"]) + '</td>'
            + '<td>' + str((a["date_alerte"] or "")[:16]) + '</td></tr>'
        )

    content = '<h1>📊 Tableau de bord Logistique</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-icon">🚛</div><div class="kpi-label">Flotte disponible</div><div class="kpi-value">' + str(stats["vehicules_dispo"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">🛣️</div><div class="kpi-label">En mission</div><div class="kpi-value">' + str(stats["vehicules_mission"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0ea5e9,#0284c7)"><div class="kpi-icon">📦</div><div class="kpi-label">Missions en cours</div><div class="kpi-value">' + str(stats["missions_encours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">📮</div><div class="kpi-label">Colis en transit</div><div class="kpi-value">' + str(stats["colis_transit"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Missions terminées</div><div class="kpi-value">' + str(stats["missions_terminees"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">🚨</div><div class="kpi-label">Alertes</div><div class="kpi-value">' + str(stats["alertes"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">💰</div><div class="kpi-label">CA mois (FCFA)</div><div class="kpi-value" style="font-size:18px">' + f'{stats["ca_mois"]:,.0f}' + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#64748b,#334155)"><div class="kpi-icon">⚖️</div><div class="kpi-label">Tonnage mois</div><div class="kpi-value">' + f'{stats["tonnage_mois"]:,.0f}' + ' T</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:18px">'

    # Missions en cours
    content += '<div class="card"><h2>🚚 Missions en cours</h2>'
    content += '<table><thead><tr><th>N° Mission</th><th>Client</th><th>Véhicule</th><th>Chauffeur</th><th>Trajet</th><th>Tonnage</th></tr></thead>'
    content += '<tbody>' + (missions_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:30px">Aucune mission en cours</td></tr>') + '</tbody></table></div>'

    # Alertes
    content += '<div class="card" style="border-left-color:#ef4444"><h2>🚨 Alertes récentes</h2>'
    content += '<table><thead><tr><th>Type</th><th>Message</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (alertes_html or '<tr><td colspan="3" style="text-align:center;color:#10b981;padding:30px">✅ Aucune alerte</td></tr>') + '</tbody></table></div>'

    content += '</div>'

    # Corridors
    content += '<div class="card"><h2>🛣️ Corridors CEDEAO actifs</h2>'
    cur.execute("SELECT * FROM corridors WHERE actif=1 ORDER BY distance_km")
    corridors = cur.fetchall()
    for c in corridors:
        content += '<div style="padding:12px;background:#f8fafc;border-radius:10px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">'
        content += '<div style="display:flex;align-items:center;gap:12px">'
        content += '<span class="badge badge-blue">' + str(c["nom"]) + '</span>'
        content += '<span style="color:#64748b;font-size:12px">' + f'{c["distance_km"]:.0f}' + ' km · ' + f'{c["duree_moyenne_h"]:.0f}' + 'h</span>'
        content += '</div>'
        content += '<span style="font-weight:700;color:#1e40af">' + f'{c["tarif_base_fcfa"]:,.0f}' + ' FCFA</span>'
        content += '</div>'

    content += '</div>'

    return render_page(content, active='dashboard', page_title='Dashboard')


# ═══════════════════════════════════════════════════════════════
# 🚛 FLOTTE — Véhicules
# ═══════════════════════════════════════════════════════════════

@app.route('/flotte')
@login_required
def flotte_liste():
    db = get_db()
    cur = db.cursor()
    statut = request.args.get('statut', '')
    sql = """
        SELECT v.*, a.nom AS agence_nom
        FROM vehicules v
        LEFT JOIN agences a ON a.id=v.agence_id
        WHERE 1=1
    """
    params = []
    if statut:
        sql += " AND v.statut=?"
        params = [statut]
    sql += " ORDER BY v.immatriculation"
    cur.execute(sql, params)
    veh = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM vehicules")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM vehicules WHERE statut='disponible'")
    stats['dispo'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM vehicules WHERE statut='en_mission'")
    stats['mission'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM vehicules WHERE statut='maintenance'")
    stats['maint'] = cur.fetchone()[0]

    rows = ''
    for v in veh:
        statut_badge = {
            'disponible': 'badge-green',
            'en_mission': 'badge-orange',
            'maintenance': 'badge-red',
        }.get(v['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong style="color:#1e40af">' + str(v["immatriculation"]) + '</strong></td>'
            + '<td>' + str(v["type"] or "—") + '</td>'
            + '<td>' + str(v["marque"] or "—") + ' ' + str(v["modele"] or "") + '</td>'
            + '<td>' + str(v["annee"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{v["capacite_tonnes"]:.1f}' + ' T</td>'
            + '<td style="text-align:right">' + f'{v["kilometrage"]:,.0f}' + ' km</td>'
            + '<td>' + str(v["agence_nom"] or "—") + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(v["statut"]) + '</span></td>'
            + '<td>' + str((v["date_visite_technique"] or "—")[:10]) + '</td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🚛 Flotte de véhicules</h1>'
    content += '<a href="/flotte/nouveau" class="btn btn-orange">+ Nouveau véhicule</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-icon">🚛</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Disponibles</div><div class="kpi-value">' + str(stats["dispo"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">🛣️</div><div class="kpi-label">En mission</div><div class="kpi-value">' + str(stats["mission"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">🔧</div><div class="kpi-label">Maintenance</div><div class="kpi-value">' + str(stats["maint"]) + '</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/flotte" class="btn ' + ('btn-primary' if not statut else 'btn-secondary') + '">Tous</a> '
    content += '<a href="/flotte?statut=disponible" class="btn ' + ('btn-success' if statut == 'disponible' else 'btn-secondary') + '" style="margin-left:6px">Disponibles</a> '
    content += '<a href="/flotte?statut=en_mission" class="btn ' + ('btn-warning' if statut == 'en_mission' else 'btn-secondary') + '" style="margin-left:6px">En mission</a> '
    content += '<a href="/flotte?statut=maintenance" class="btn ' + ('btn-danger' if statut == 'maintenance' else 'btn-secondary') + '" style="margin-left:6px">Maintenance</a>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>Immatriculation</th><th>Type</th><th>Marque/Modèle</th><th>Année</th>'
    content += '<th style="text-align:right">Capacité</th><th style="text-align:right">Km</th>'
    content += '<th>Agence</th><th>Statut</th><th>Visite tech.</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="9" style="padding:40px;text-align:center;color:#94a3b8">Aucun véhicule</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='flotte', page_title='Flotte')


@app.route('/flotte/nouveau', methods=['GET', 'POST'])
@login_required
def flotte_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO vehicules
                (immatriculation, type, marque, modele, annee, capacite_tonnes, capacite_m3,
                 statut, kilometrage, date_assurance, date_visite_technique, agence_id, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                request.form.get('immatriculation'),
                request.form.get('type'),
                request.form.get('marque'),
                request.form.get('modele'),
                int(request.form.get('annee') or 0),
                float(request.form.get('capacite_tonnes') or 0),
                float(request.form.get('capacite_m3') or 0),
                request.form.get('statut') or 'disponible',
                float(request.form.get('kilometrage') or 0),
                request.form.get('date_assurance'),
                request.form.get('date_visite_technique'),
                int(request.form.get('agence_id') or 0) or None,
                datetime.now().isoformat()))
            db.commit()
            log_action(current_user.id, 'CREATE_VEHICULE',
                       request.form.get('immatriculation'), 'vehicules')
            flash('✅ Véhicule créé', 'success')
            return redirect('/flotte')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom FROM agences WHERE actif=1")
    ags = cur.fetchall()
    opts = ''.join('<option value="' + str(a["id"]) + '">' + str(a["nom"]) + '</option>' for a in ags)

    content = '<h1>🚛 Nouveau véhicule</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Immatriculation *</label><input type="text" name="immatriculation" required placeholder="DK-1234-AB"></div>'
    content += '<div><label>Type *</label><select name="type" required>'
    content += '<option value="camion_40t">Camion 40T</option>'
    content += '<option value="camion_30t">Camion 30T</option>'
    content += '<option value="camion_20t">Camion 20T</option>'
    content += '<option value="camion_10t">Camion 10T</option>'
    content += '<option value="utilitaire_3.5t">Utilitaire 3.5T</option>'
    content += '<option value="frigorifique">Frigorifique</option>'
    content += '<option value="porte_conteneur">Porte-conteneur</option>'
    content += '</select></div>'
    content += '<div><label>Marque</label><input type="text" name="marque"></div>'
    content += '<div><label>Modèle</label><input type="text" name="modele"></div>'
    content += '<div><label>Année</label><input type="number" name="annee" value="2024"></div>'
    content += '<div><label>Capacité (tonnes)</label><input type="number" step="0.1" name="capacite_tonnes" value="0"></div>'
    content += '<div><label>Capacité (m³)</label><input type="number" step="0.1" name="capacite_m3" value="0"></div>'
    content += '<div><label>Kilométrage</label><input type="number" name="kilometrage" value="0"></div>'
    content += '<div><label>Date assurance</label><input type="date" name="date_assurance"></div>'
    content += '<div><label>Date visite technique</label><input type="date" name="date_visite_technique"></div>'
    content += '<div><label>Agence</label><select name="agence_id"><option value="">— Aucune —</option>' + opts + '</select></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Enregistrer</button>'
    content += '<a href="/flotte" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='flotte', page_title='Nouveau véhicule')


# ═══════════════════════════════════════════════════════════════
# 👨‍✈️ CHAUFFEURS
# ═══════════════════════════════════════════════════════════════

@app.route('/chauffeurs')
@login_required
def chauffeurs_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, a.nom AS agence_nom
        FROM chauffeurs c
        LEFT JOIN agences a ON a.id=c.agence_id
        ORDER BY c.nom_complet
    """)
    chfs = cur.fetchall()

    rows = ''
    for c in chfs:
        statut_badge = 'badge-green' if c['statut'] == 'disponible' else 'badge-orange'
        note_color = '#10b981' if (c['note'] or 0) >= 4.5 else '#f59e0b' if (c['note'] or 0) >= 3.5 else '#ef4444'
        rows += (
            '<tr><td><strong>' + str(c["nom_complet"]) + '</strong></td>'
            + '<td>' + str(c["telephone"] or "—") + '</td>'
            + '<td>' + str(c["numero_permis"] or "—") + '</td>'
            + '<td><span class="badge badge-blue">' + str(c["categorie_permis"] or "—") + '</span></td>'
            + '<td>' + str((c["date_expiration_permis"] or "—")[:10]) + '</td>'
            + '<td>' + str(c["agence_nom"] or "—") + '</td>'
            + '<td><strong style="color:' + note_color + '">⭐ ' + f'{c["note"]:.1f}' + '</strong></td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👨‍✈️ Chauffeurs — ' + str(len(chfs)) + '</h1>'
    content += '<a href="/chauffeurs/nouveau" class="btn btn-orange">+ Nouveau chauffeur</a></div>'
    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>Nom</th><th>Téléphone</th><th>N° Permis</th><th>Catégorie</th>'
    content += '<th>Expiration</th><th>Agence</th><th>Note</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun chauffeur</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='chauffeurs', page_title='Chauffeurs')


@app.route('/chauffeurs/nouveau', methods=['GET', 'POST'])
@login_required
def chauffeurs_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO chauffeurs
                (nom_complet, telephone, numero_permis, categorie_permis,
                 date_expiration_permis, agence_id, statut, note, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                request.form.get('nom_complet'),
                request.form.get('telephone'),
                request.form.get('numero_permis'),
                request.form.get('categorie_permis'),
                request.form.get('date_expiration_permis'),
                int(request.form.get('agence_id') or 0) or None,
                'disponible', 5.0,
                datetime.now().isoformat()))
            db.commit()
            log_action(current_user.id, 'CREATE_CHAUFFEUR',
                       request.form.get('nom_complet'), 'chauffeurs')
            flash('✅ Chauffeur créé', 'success')
            return redirect('/chauffeurs')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom FROM agences WHERE actif=1")
    ags = cur.fetchall()
    opts = ''.join('<option value="' + str(a["id"]) + '">' + str(a["nom"]) + '</option>' for a in ags)

    content = '<h1>👨‍✈️ Nouveau chauffeur</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom complet *</label><input type="text" name="nom_complet" required autofocus></div>'
    content += '<div><label>Téléphone</label><input type="text" name="telephone" placeholder="+221 77 XXX XX XX"></div>'
    content += '<div><label>N° Permis</label><input type="text" name="numero_permis"></div>'
    content += '<div><label>Catégorie permis</label><select name="categorie_permis">'
    content += '<option value="C">C - Poids lourd</option>'
    content += '<option value="CE">CE - Poids lourd + remorque</option>'
    content += '<option value="D">D - Transport en commun</option>'
    content += '</select></div>'
    content += '<div><label>Date expiration permis</label><input type="date" name="date_expiration_permis"></div>'
    content += '<div style="grid-column:1/-1"><label>Agence</label><select name="agence_id"><option value="">— Aucune —</option>' + opts + '</select></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Enregistrer</button>'
    content += '<a href="/chauffeurs" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='chauffeurs', page_title='Nouveau chauffeur')


# ═══════════════════════════════════════════════════════════════
# 📦 MISSIONS
# ═══════════════════════════════════════════════════════════════

@app.route('/missions')
@login_required
def missions_liste():
    db = get_db()
    cur = db.cursor()
    statut = request.args.get('statut', '')
    sql = """
        SELECT m.*, v.immatriculation, ch.nom_complet AS chauffeur_nom,
               c.nom AS client_nom, co.nom AS corridor_nom
        FROM missions m
        LEFT JOIN vehicules v ON v.id=m.vehicule_id
        LEFT JOIN chauffeurs ch ON ch.id=m.chauffeur_id
        LEFT JOIN clients c ON c.id=m.client_id
        LEFT JOIN corridors co ON co.id=m.corridor_id
        WHERE 1=1
    """
    params = []
    if statut:
        sql += " AND m.statut=?"
        params = [statut]
    sql += " ORDER BY m.id DESC LIMIT 200"
    cur.execute(sql, params)
    missions = cur.fetchall()

    stats = {}
    for k, s in [
        ('total', "SELECT COUNT(*) FROM missions"),
        ('encours', "SELECT COUNT(*) FROM missions WHERE statut='en_cours'"),
        ('terminees', "SELECT COUNT(*) FROM missions WHERE statut='terminee'"),
        ('planifiees', "SELECT COUNT(*) FROM missions WHERE statut='planifiee'"),
    ]:
        cur.execute(s)
        stats[k] = cur.fetchone()[0]

    rows = ''
    for m in missions:
        statut_badge = {
            'planifiee': 'badge-blue',
            'en_cours': 'badge-orange',
            'terminee': 'badge-green',
            'annulee': 'badge-red',
        }.get(m['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong style="color:#1e40af">' + str(m["numero"] or "—") + '</strong></td>'
            + '<td>' + str(m["client_nom"] or "—") + '</td>'
            + '<td>' + str(m["immatriculation"] or "—") + '</td>'
            + '<td>' + str(m["chauffeur_nom"] or "—") + '</td>'
            + '<td>' + str(m["origine"] or "—") + ' → ' + str(m["destination"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{m["distance_km"]:.0f}' + ' km</td>'
            + '<td style="text-align:right">' + f'{m["tonnage"]:.1f}' + ' T</td>'
            + '<td style="text-align:right">' + f'{m["montant_fcfa"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(m["statut"]) + '</span></td>'
            + '<td><a href="/missions/' + str(m["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁 Détail</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📦 Missions de transport</h1>'
    content += '<a href="/missions/nouvelle" class="btn btn-orange">+ Nouvelle mission</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-icon">📦</div><div class="kpi-label">Total missions</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">🛣️</div><div class="kpi-label">En cours</div><div class="kpi-value">' + str(stats["encours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0ea5e9,#0284c7)"><div class="kpi-icon">📅</div><div class="kpi-label">Planifiées</div><div class="kpi-value">' + str(stats["planifiees"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Terminées</div><div class="kpi-value">' + str(stats["terminees"]) + '</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/missions" class="btn ' + ('btn-primary' if not statut else 'btn-secondary') + '">Toutes</a> '
    content += '<a href="/missions?statut=planifiee" class="btn ' + ('btn-primary' if statut == 'planifiee' else 'btn-secondary') + '" style="margin-left:6px">Planifiées</a> '
    content += '<a href="/missions?statut=en_cours" class="btn ' + ('btn-warning' if statut == 'en_cours' else 'btn-secondary') + '" style="margin-left:6px">En cours</a> '
    content += '<a href="/missions?statut=terminee" class="btn ' + ('btn-success' if statut == 'terminee' else 'btn-secondary') + '" style="margin-left:6px">Terminées</a>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>N° Mission</th><th>Client</th><th>Véhicule</th><th>Chauffeur</th><th>Trajet</th>'
    content += '<th style="text-align:right">Distance</th><th style="text-align:right">Tonnage</th>'
    content += '<th style="text-align:right">Montant</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="10" style="padding:40px;text-align:center;color:#94a3b8">Aucune mission</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='missions', page_title='Missions')


@app.route('/missions/nouvelle', methods=['GET', 'POST'])
@login_required
def missions_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            corridor_id = int(request.form.get('corridor_id') or 0) or None
            # Récupérer distance et orig/dest du corridor
            distance = 0
            origine = request.form.get('origine') or ''
            destination = request.form.get('destination') or ''
            if corridor_id:
                cur.execute("SELECT distance_km, origine, destination FROM corridors WHERE id=?", (corridor_id,))
                r = cur.fetchone()
                if r:
                    distance = r['distance_km']
                    origine = r['origine']
                    destination = r['destination']

            tonnage = float(request.form.get('tonnage') or 0)
            tarif_tonne_km = float(request.form.get('tarif_tonne_km') or 25)
            montant = tonnage * distance * tarif_tonne_km / 1000

            cur.execute("""
                INSERT INTO missions
                (numero, client_id, vehicule_id, chauffeur_id, corridor_id,
                 origine, destination, distance_km, tonnage, statut,
                 date_depart, date_arrivee_prevue, montant_fcfa, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None,
                  int(request.form.get('client_id') or 0) or None,
                  int(request.form.get('vehicule_id') or 0) or None,
                  int(request.form.get('chauffeur_id') or 0) or None,
                  corridor_id, origine, destination, distance, tonnage,
                  request.form.get('statut') or 'planifiee',
                  request.form.get('date_depart'),
                  request.form.get('date_arrivee_prevue'),
                  montant,
                  request.form.get('notes'),
                  datetime.now().isoformat()))
            db.commit()
            log_action(current_user.id, 'CREATE_MISSION', f'Tonnage: {tonnage}',
                       'missions', cur.lastrowid)
            flash('✅ Mission créée', 'success')
            return redirect('/missions')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom FROM clients ORDER BY nom")
    clients = cur.fetchall()
    cur.execute("SELECT id, immatriculation FROM vehicules WHERE statut='disponible'")
    vehicules = cur.fetchall()
    cur.execute("SELECT id, nom_complet FROM chauffeurs WHERE statut='disponible'")
    chauffeurs = cur.fetchall()
    cur.execute("SELECT id, nom, distance_km, tarif_base_fcfa FROM corridors WHERE actif=1")
    corridors = cur.fetchall()

    opts_cli = ''.join('<option value="' + str(c["id"]) + '">' + str(c["nom"]) + '</option>' for c in clients)
    opts_veh = ''.join('<option value="' + str(v["id"]) + '">' + str(v["immatriculation"]) + '</option>' for v in vehicules)
    opts_chf = ''.join('<option value="' + str(c["id"]) + '">' + str(c["nom_complet"]) + '</option>' for c in chauffeurs)
    opts_cor = ''.join('<option value="' + str(c["id"]) + '">' + str(c["nom"]) + ' (' + f'{c["distance_km"]:.0f}' + ' km)</option>' for c in corridors)

    content = '<h1>📦 Nouvelle mission</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Client *</label><select name="client_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_cli + '</select></div>'
    content += '<div><label>Véhicule *</label><select name="vehicule_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_veh + '</select></div>'
    content += '<div><label>Chauffeur *</label><select name="chauffeur_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_chf + '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Corridor *</label><select name="corridor_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_cor + '</select></div>'
    content += '<div><label>Tonnage *</label><input type="number" step="0.1" name="tonnage" required value="20"></div>'
    content += '<div><label>Tarif tonne/km (FCFA)</label><input type="number" step="0.1" name="tarif_tonne_km" value="25"></div>'
    content += '<div><label>Date départ</label><input type="date" name="date_depart" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Date arrivée prévue</label><input type="date" name="date_arrivee_prevue"></div>'
    content += '<div><label>Statut</label><select name="statut">'
    content += '<option value="planifiee">Planifiée</option>'
    content += '<option value="en_cours">En cours</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Notes</label><textarea name="notes" rows="3"></textarea></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer la mission</button>'
    content += '<a href="/missions" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='missions', page_title='Nouvelle mission')


@app.route('/missions/<int:mid>')
@login_required
def missions_detail(mid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT m.*, v.immatriculation, v.type AS vehicule_type,
               ch.nom_complet AS chauffeur_nom, ch.telephone AS chauffeur_tel,
               c.nom AS client_nom, co.nom AS corridor_nom
        FROM missions m
        LEFT JOIN vehicules v ON v.id=m.vehicule_id
        LEFT JOIN chauffeurs ch ON ch.id=m.chauffeur_id
        LEFT JOIN clients c ON c.id=m.client_id
        LEFT JOIN corridors co ON co.id=m.corridor_id
        WHERE m.id=?
    """, (mid,))
    m = cur.fetchone()
    if not m:
        flash('❌ Mission introuvable', 'error')
        return redirect('/missions')

    # Colis de la mission
    cur.execute("SELECT * FROM colis WHERE mission_id=?", (mid,))
    colis = cur.fetchall()

    colis_html = ''
    for c in colis:
        colis_html += (
            '<tr><td><code style="color:#1e40af;font-weight:700">' + str(c["numero_suivi"]) + '</code></td>'
            + '<td>' + str(c["description"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{c["poids_kg"]:.0f}' + ' kg</td>'
            + '<td style="text-align:right">' + f'{c["valeur_fcfa"]:,.0f}' + ' F</td>'
            + '<td>' + str(c["statut"]) + '</td></tr>'
        )

    statut_badge = {
        'planifiee': 'badge-blue',
        'en_cours': 'badge-orange',
        'terminee': 'badge-green',
        'annulee': 'badge-red',
    }.get(m['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📦 Mission ' + str(m["numero"]) + ' <span class="badge ' + statut_badge + '">' + str(m["statut"]) + '</span></h1>'
    content += '<div><a href="/missions/' + str(mid) + '/statut/en_cours" class="btn btn-warning">▶ Démarrer</a> '
    content += '<a href="/missions/' + str(mid) + '/statut/terminee" class="btn btn-success">✅ Terminer</a> '
    content += '<a href="/missions" class="btn btn-secondary">← Retour</a></div></div>'

    # Trajet visuel
    content += '<div class="card">'
    content += '<h2>🗺️ Itinéraire</h2>'
    content += '<div class="route-timeline">'
    content += '<div class="route-dot route-dot-start"></div>'
    content += '<div><strong>' + str(m["origine"] or "—") + '</strong><br><small style="color:#64748b">Origine</small></div>'
    content += '<div class="route-line"></div>'
    content += '<div style="text-align:center"><strong style="color:#1e40af">' + f'{m["distance_km"]:.0f}' + ' km</strong><br><small style="color:#64748b">Distance</small></div>'
    content += '<div class="route-line"></div>'
    content += '<div class="route-dot route-dot-end"></div>'
    content += '<div><strong>' + str(m["destination"] or "—") + '</strong><br><small style="color:#64748b">Destination</small></div>'
    content += '</div></div>'

    # Détails
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>📋 Détails mission</h2><table>'
    content += '<tr><td><strong>Client</strong></td><td>' + str(m["client_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Véhicule</strong></td><td>' + str(m["immatriculation"] or "—") + ' (' + str(m["vehicule_type"] or "") + ')</td></tr>'
    content += '<tr><td><strong>Chauffeur</strong></td><td>' + str(m["chauffeur_nom"] or "—") + ' · ' + str(m["chauffeur_tel"] or "") + '</td></tr>'
    content += '<tr><td><strong>Corridor</strong></td><td>' + str(m["corridor_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Tonnage</strong></td><td>' + f'{m["tonnage"]:.1f}' + ' T</td></tr>'
    content += '<tr><td><strong>Montant</strong></td><td style="color:#10b981;font-weight:700">' + f'{m["montant_fcfa"]:,.0f}' + ' FCFA</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>📅 Planning</h2><table>'
    content += '<tr><td><strong>Départ</strong></td><td>' + str((m["date_depart"] or "—")[:16]) + '</td></tr>'
    content += '<tr><td><strong>Arrivée prévue</strong></td><td>' + str((m["date_arrivee_prevue"] or "—")[:16]) + '</td></tr>'
    content += '<tr><td><strong>Arrivée réelle</strong></td><td>' + str((m["date_arrivee_reelle"] or "—")[:16]) + '</td></tr>'
    content += '</table></div>'
    content += '</div>'

    # Colis
    content += '<div class="card"><h2>📮 Colis transportés (' + str(len(colis)) + ')</h2>'
    content += '<table><thead><tr><th>N° Suivi</th><th>Description</th><th style="text-align:right">Poids</th><th style="text-align:right">Valeur</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (colis_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:30px">Aucun colis</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='missions', page_title='Mission')


@app.route('/missions/<int:mid>/statut/<statut>')
@login_required
def missions_statut(mid, statut):
    db = get_db()
    cur = db.cursor()
    try:
        date_fin = datetime.now().isoformat() if statut == 'terminee' else None
        cur.execute("""
            UPDATE missions SET statut=?, date_arrivee_reelle=COALESCE(?, date_arrivee_reelle)
            WHERE id=?
        """, (statut, date_fin, mid))
        db.commit()
        log_action(current_user.id, 'MISSION_STATUT', statut, 'missions', mid)
        flash('✅ Statut : ' + statut, 'success')
    except Exception as e:
        db.rollback()
        flash('❌ ' + str(e), 'error')
    return redirect('/missions/' + str(mid))


# ═══════════════════════════════════════════════════════════════
# 📮 COLIS
# ═══════════════════════════════════════════════════════════════

@app.route('/colis')
@login_required
def colis_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, m.numero AS mission_numero, cl.nom AS client_nom
        FROM colis c
        LEFT JOIN missions m ON m.id=c.mission_id
        LEFT JOIN clients cl ON cl.id=c.client_id
        ORDER BY c.id DESC LIMIT 200
    """)
    colis = cur.fetchall()

    rows = ''
    for c in colis:
        statut_badge = {
            'en_attente': 'badge-gray',
            'en_transit': 'badge-orange',
            'livre': 'badge-green',
            'retourne': 'badge-red',
        }.get(c['statut'], 'badge-gray')
        rows += (
            '<tr><td><code style="color:#1e40af;font-weight:700;font-size:12px">' + str(c["numero_suivi"]) + '</code></td>'
            + '<td>' + str(c["description"] or "—") + '</td>'
            + '<td>' + str(c["client_nom"] or "—") + '</td>'
            + '<td>' + str(c["mission_numero"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{c["poids_kg"]:.0f}' + ' kg</td>'
            + '<td style="text-align:right">' + f'{c["valeur_fcfa"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📮 Colis & Lots — ' + str(len(colis)) + '</h1>'
    content += '<a href="/colis/nouveau" class="btn btn-orange">+ Nouveau colis</a></div>'
    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>N° Suivi</th><th>Description</th><th>Client</th><th>Mission</th>'
    content += '<th style="text-align:right">Poids</th><th style="text-align:right">Valeur</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucun colis</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='colis', page_title='Colis')


@app.route('/colis/nouveau', methods=['GET', 'POST'])
@login_required
def colis_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO colis
                (numero_suivi, mission_id, client_id, description,
                 poids_kg, volume_m3, valeur_fcfa, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (None,
                  int(request.form.get('mission_id') or 0) or None,
                  int(request.form.get('client_id') or 0) or None,
                  request.form.get('description'),
                  float(request.form.get('poids_kg') or 0),
                  float(request.form.get('volume_m3') or 0),
                  float(request.form.get('valeur_fcfa') or 0),
                  'en_attente',
                  datetime.now().isoformat()))
            db.commit()
            log_action(current_user.id, 'CREATE_COLIS', 'Nouveau colis', 'colis', cur.lastrowid)
            flash('✅ Colis créé — N° suivi auto-généré', 'success')
            return redirect('/colis')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, numero FROM missions WHERE statut IN ('planifiee','en_cours') ORDER BY id DESC LIMIT 50")
    missions = cur.fetchall()
    cur.execute("SELECT id, nom FROM clients ORDER BY nom")
    clients = cur.fetchall()

    opts_m = ''.join('<option value="' + str(m["id"]) + '">' + str(m["numero"]) + '</option>' for m in missions)
    opts_c = ''.join('<option value="' + str(c["id"]) + '">' + str(c["nom"]) + '</option>' for c in clients)

    content = '<h1>📮 Nouveau colis</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Description *</label><input type="text" name="description" required autofocus placeholder="Palettes de riz, cartons divers..."></div>'
    content += '<div><label>Mission</label><select name="mission_id"><option value="">— Aucune —</option>' + opts_m + '</select></div>'
    content += '<div><label>Client</label><select name="client_id"><option value="">— Aucun —</option>' + opts_c + '</select></div>'
    content += '<div><label>Poids (kg)</label><input type="number" step="1" name="poids_kg" value="0"></div>'
    content += '<div><label>Volume (m³)</label><input type="number" step="0.1" name="volume_m3" value="0"></div>'
    content += '<div style="grid-column:1/-1"><label>Valeur (FCFA)</label><input type="number" step="1000" name="valeur_fcfa" value="0"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer le colis</button>'
    content += '<a href="/colis" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='colis', page_title='Nouveau colis')


# ═══════════════════════════════════════════════════════════════
# 🗺️ TRACKING GPS
# ═══════════════════════════════════════════════════════════════

@app.route('/tracking')
@login_required
def tracking_dashboard():
    db = get_db()
    cur = db.cursor()

    # Véhicules en mission + dernière position
    cur.execute("""
        SELECT v.id, v.immatriculation, v.type, m.numero AS mission_numero,
               m.origine, m.destination, m.id AS mission_id,
               (SELECT latitude FROM tracking_gps WHERE vehicule_id=v.id ORDER BY id DESC LIMIT 1) AS lat,
               (SELECT longitude FROM tracking_gps WHERE vehicule_id=v.id ORDER BY id DESC LIMIT 1) AS lng,
               (SELECT vitesse_kmh FROM tracking_gps WHERE vehicule_id=v.id ORDER BY id DESC LIMIT 1) AS vitesse,
               (SELECT carburant_pct FROM tracking_gps WHERE vehicule_id=v.id ORDER BY id DESC LIMIT 1) AS carburant,
               (SELECT date_position FROM tracking_gps WHERE vehicule_id=v.id ORDER BY id DESC LIMIT 1) AS derniere_pos
        FROM vehicules v
        LEFT JOIN missions m ON m.vehicule_id=v.id AND m.statut='en_cours'
        WHERE v.statut='en_mission'
    """)
    tracking = cur.fetchall()

    cards = ''
    for t in tracking:
        vitesse = t['vitesse'] or 0
        carburant = t['carburant'] or 0
        carb_color = '#10b981' if carburant > 50 else '#f59e0b' if carburant > 20 else '#ef4444'
        cards += '<div class="truck-card">'
        cards += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'
        cards += '<strong style="font-size:16px">🚛 ' + str(t["immatriculation"]) + '</strong>'
        cards += '<span class="badge" style="background:rgba(255,255,255,.2)">' + str(t["mission_numero"] or "—") + '</span></div>'
        cards += '<div style="font-size:13px;opacity:.9;margin-bottom:10px">' + str(t["origine"] or "—") + ' → ' + str(t["destination"] or "—") + '</div>'
        cards += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px">'
        cards += '<div>📍 Vitesse : <strong>' + f'{vitesse:.0f}' + ' km/h</strong></div>'
        cards += '<div>⛽ Carburant : <strong style="color:' + carb_color + '">' + f'{carburant:.0f}' + '%</strong></div>'
        cards += '<div>🌐 Lat : ' + f'{t["lat"] or 0:.4f}' + '</div>'
        cards += '<div>🌐 Lng : ' + f'{t["lng"] or 0:.4f}' + '</div>'
        cards += '</div>'
        cards += '<div style="margin-top:10px;font-size:11px;opacity:.7">Dernière position : ' + str((t["derniere_pos"] or "—")[:16]) + '</div>'
        cards += '</div>'

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🗺️ Tracking GPS temps réel</h1>'
    content += '<a href="/tracking/simuler" class="btn btn-orange">📡 Simuler positions</a></div>'

    content += '<div style="margin-bottom:16px;padding:14px;background:#eff6ff;border-left:4px solid #1e40af;border-radius:8px;font-size:13px">'
    content += '📍 <strong>Suivi GPS</strong> des véhicules en mission — mises à jour toutes les 2 minutes. Cliquez sur <strong>Simuler</strong> pour tester.</div>'

    content += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px">'
    content += cards or '<div style="grid-column:1/-1;padding:60px;text-align:center;color:#94a3b8">Aucun véhicule en mission</div>'
    content += '</div>'
    return render_page(content, active='tracking', page_title='Tracking GPS')


@app.route('/tracking/simuler')
@login_required
def tracking_simuler():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT v.id, m.id AS mission_id, m.distance_km
        FROM vehicules v
        LEFT JOIN missions m ON m.vehicule_id=v.id AND m.statut='en_cours'
        WHERE v.statut='en_mission'
    """)
    veh = cur.fetchall()

    n = 0
    for v in veh:
        # Position autour de Dakar (14.6928, -17.4467)
        lat = 14.6928 + random.uniform(-5, 5)
        lng = -17.4467 + random.uniform(-5, 5)
        vitesse = random.uniform(40, 90)
        carburant = random.uniform(20, 100)

        cur.execute("""
            INSERT INTO tracking_gps
            (vehicule_id, mission_id, latitude, longitude, vitesse_kmh, carburant_pct, date_position, created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (v['id'], v['mission_id'], lat, lng, vitesse, carburant,
              datetime.now().isoformat(), datetime.now().isoformat()))
        n += 1

    db.commit()
    log_action(current_user.id, 'TRACKING_SIM', str(n) + ' positions', 'tracking_gps')
    flash('📡 ' + str(n) + ' positions GPS simulées', 'success')
    return redirect('/tracking')


# ═══════════════════════════════════════════════════════════════
# 🏭 ENTREPÔTS
# ═══════════════════════════════════════════════════════════════

@app.route('/entrepots')
@login_required
def entrepots_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM entrepots ORDER BY nom")
    entrepots = cur.fetchall()

    cards = ''
    for e in entrepots:
        cap = e['capacite_m3'] or 0
        occ = e['occupe_m3'] or 0
        pct = (occ / cap * 100) if cap > 0 else 0
        color = '#10b981' if pct < 70 else '#f59e0b' if pct < 90 else '#ef4444'
        temp_badge = '<span class="badge badge-blue">❄ Temp. contrôlée</span>' if e['temperature_controlee'] else '<span class="badge badge-gray">Standard</span>'

        cards += '<div class="card" style="border-left-color:' + color + '">'
        cards += '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">'
        cards += '<div><h2 style="margin:0;color:#1e3a8a">🏭 ' + str(e["nom"]) + '</h2>'
        cards += '<small style="color:#64748b">' + str(e["code"]) + ' · ' + str(e["ville"]) + '</small></div>'
        cards += temp_badge + '</div>'
        cards += '<div style="margin-bottom:8px;font-size:13px"><strong>Occupation :</strong> ' + f'{occ:,.0f}' + ' / ' + f'{cap:,.0f}' + ' m³ (' + f'{pct:.0f}' + '%)</div>'
        cards += '<div style="background:#e2e8f0;border-radius:8px;overflow:hidden;height:14px"><div style="background:' + color + ';height:100%;width:' + f'{min(pct,100):.0f}' + '%"></div></div>'
        cards += '<div style="margin-top:12px;font-size:12px;color:#64748b">👤 ' + str(e["responsable"] or "—") + ' · 📞 ' + str(e["telephone"] or "—") + '</div>'
        cards += '</div>'

    content = '<h1>🏭 Entrepôts & Cross-docking — ' + str(len(entrepots)) + '</h1>'
    content += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px">'
    content += cards
    content += '</div>'
    return render_page(content, active='entrepots', page_title='Entrepôts')


# ═══════════════════════════════════════════════════════════════
# 🛃 DOUANES
# ═══════════════════════════════════════════════════════════════

@app.route('/douanes')
@login_required
def douanes_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT d.*, m.numero AS mission_numero
        FROM declarations_douanes d
        LEFT JOIN missions m ON m.id=d.mission_id
        ORDER BY d.id DESC LIMIT 200
    """)
    decls = cur.fetchall()

    rows = ''
    for d in decls:
        statut_badge = {
            'en_cours': 'badge-orange',
            'liquidee': 'badge-green',
            'bloquee': 'badge-red',
        }.get(d['statut'], 'badge-gray')
        rows += (
            '<tr><td><code style="color:#1e40af;font-weight:700">' + str(d["numero_declaration"] or "—") + '</code></td>'
            + '<td>' + str(d["mission_numero"] or "—") + '</td>'
            + '<td>' + str(d["bureau_douane"] or "—") + '</td>'
            + '<td>' + str(d["pays_origine"] or "—") + ' → ' + str(d["pays_destination"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{d["valeur_marchandise"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right">' + f'{d["droits_taxes"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(d["statut"]) + '</span></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🛃 Déclarations douanières — ' + str(len(decls)) + '</h1>'
    content += '<a href="/douanes/nouvelle" class="btn btn-orange">+ Nouvelle déclaration</a></div>'
    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>N° Déclaration</th><th>Mission</th><th>Bureau</th><th>Trajet</th>'
    content += '<th style="text-align:right">Valeur</th><th style="text-align:right">Droits/Taxes</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucune déclaration</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='douanes', page_title='Douanes')


@app.route('/douanes/nouvelle', methods=['GET', 'POST'])
@login_required
def douanes_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            val = float(request.form.get('valeur_marchandise') or 0)
            droits = val * 0.20  # 20% simplifié
            cur.execute("""
                INSERT INTO declarations_douanes
                (numero_declaration, mission_id, bureau_douane, pays_origine, pays_destination,
                 valeur_marchandise, droits_taxes, statut, date_depot, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (request.form.get('numero_declaration'),
                  int(request.form.get('mission_id') or 0) or None,
                  request.form.get('bureau_douane'),
                  request.form.get('pays_origine'),
                  request.form.get('pays_destination'),
                  val, droits, 'en_cours',
                  datetime.now().strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Déclaration créée', 'success')
            return redirect('/douanes')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, numero FROM missions ORDER BY id DESC LIMIT 50")
    missions = cur.fetchall()
    opts = ''.join('<option value="' + str(m["id"]) + '">' + str(m["numero"]) + '</option>' for m in missions)

    content = '<h1>🛃 Nouvelle déclaration douanière</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>N° Déclaration *</label><input type="text" name="numero_declaration" required placeholder="DOU-2026-XXXX"></div>'
    content += '<div><label>Mission</label><select name="mission_id"><option value="">— Aucune —</option>' + opts + '</select></div>'
    content += '<div><label>Bureau de douane</label><input type="text" name="bureau_douane" value="Dakar Port"></div>'
    content += '<div><label>Pays origine</label><input type="text" name="pays_origine" value="Sénégal"></div>'
    content += '<div><label>Pays destination</label><input type="text" name="pays_destination" value="Mali"></div>'
    content += '<div style="grid-column:1/-1"><label>Valeur marchandise (FCFA)</label><input type="number" step="1000" name="valeur_marchandise" value="0"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/douanes" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='douanes', page_title='Nouvelle déclaration')


# ═══════════════════════════════════════════════════════════════
# 💰 FACTURATION
# ═══════════════════════════════════════════════════════════════

@app.route('/factures')
@login_required
def factures_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT f.*, c.nom AS client_nom, m.numero AS mission_numero
        FROM factures f
        LEFT JOIN clients c ON c.id=f.client_id
        LEFT JOIN missions m ON m.id=f.mission_id
        ORDER BY f.id DESC LIMIT 200
    """)
    factures = cur.fetchall()

    rows = ''
    for f in factures:
        statut_badge = {
            'emise': 'badge-blue',
            'payee': 'badge-green',
            'impayee': 'badge-red',
            'annulee': 'badge-gray',
        }.get(f['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong style="color:#1e40af">' + str(f["numero"] or "—") + '</strong></td>'
            + '<td>' + str(f["client_nom"] or "—") + '</td>'
            + '<td>' + str(f["mission_numero"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{f["montant_ht"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right">' + f'{f["montant_ttc"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(f["statut"]) + '</span></td>'
            + '<td>' + str((f["date_emission"] or "—")[:10]) + '</td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">💰 Facturation — ' + str(len(factures)) + '</h1>'
    content += '<a href="/factures/nouvelle" class="btn btn-orange">+ Nouvelle facture</a></div>'
    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>N° Facture</th><th>Client</th><th>Mission</th>'
    content += '<th style="text-align:right">Montant HT</th><th style="text-align:right">Montant TTC</th>'
    content += '<th>Statut</th><th>Émise le</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucune facture</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='factures', page_title='Facturation')


@app.route('/factures/nouvelle', methods=['GET', 'POST'])
@login_required
def factures_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            mission_id = int(request.form.get('mission_id') or 0) or None
            montant_ht = float(request.form.get('montant_ht') or 0)
            tva = montant_ht * 0.18
            montant_ttc = montant_ht + tva

            cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM factures")
            nid = cur.fetchone()[0]
            numero = 'FAC-' + datetime.now().strftime('%Y%m') + '-' + f'{nid:04d}'

            # Client auto depuis mission
            client_id = int(request.form.get('client_id') or 0) or None
            if not client_id and mission_id:
                cur.execute("SELECT client_id FROM missions WHERE id=?", (mission_id,))
                r = cur.fetchone()
                if r:
                    client_id = r['client_id']

            cur.execute("""
                INSERT INTO factures
                (numero, mission_id, client_id, montant_ht, tva, montant_ttc,
                 statut, date_emission, date_echeance, created_at)
                VALUES (?,?,?,?,?,?,'emise',?,?,?)
            """, (numero, mission_id, client_id, montant_ht, tva, montant_ttc,
                  datetime.now().strftime('%Y-%m-%d'),
                  (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Facture créée — N° ' + numero, 'success')
            return redirect('/factures')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("""
        SELECT m.id, m.numero, m.montant_fcfa, c.nom AS client_nom
        FROM missions m LEFT JOIN clients c ON c.id=m.client_id
        WHERE m.statut='terminee'
        ORDER BY m.id DESC LIMIT 50
    """)
    missions = cur.fetchall()

    opts = ''
    for m in missions:
        opts += '<option value="' + str(m["id"]) + '" data-montant="' + str(m["montant_fcfa"]) + '">' + str(m["numero"]) + ' — ' + str(m["client_nom"] or "") + ' (' + f'{m["montant_fcfa"]:,.0f}' + ' F)</option>'

    content = '<h1>💰 Nouvelle facture</h1>'
    content += '<form method="post" class="card" style="max-width:600px">'
    content += '<div style="margin-bottom:16px"><label>Mission *</label>'
    content += '<select name="mission_id" required onchange="var opt=this.options[this.selectedIndex];document.querySelector(\'input[name=montant_ht]\').value=opt.dataset.montant||0">'
    content += '<option value="">— Sélectionner —</option>' + opts + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Montant HT (FCFA) *</label>'
    content += '<input type="number" step="1000" name="montant_ht" required value="0"></div>'
    content += '<div style="background:#eff6ff;padding:12px;border-radius:8px;margin-bottom:16px;font-size:12px;color:#1e40af">'
    content += 'La TVA de 18% sera automatiquement ajoutée au montant TTC.</div>'
    content += '<button type="submit" class="btn btn-success">💾 Créer la facture</button>'
    content += '<a href="/factures" class="btn btn-secondary" style="margin-left:8px">Annuler</a>'
    content += '</form>'
    return render_page(content, active='factures', page_title='Nouvelle facture')


# ═══════════════════════════════════════════════════════════════
# 🚨 ALERTES
# ═══════════════════════════════════════════════════════════════

@app.route('/alertes')
@login_required
def alertes_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT a.*, m.numero AS mission_numero, v.immatriculation
        FROM alertes a
        LEFT JOIN missions m ON m.id=a.mission_id
        LEFT JOIN vehicules v ON v.id=a.vehicule_id
        ORDER BY a.id DESC LIMIT 200
    """)
    alertes = cur.fetchall()

    rows = ''
    for a in alertes:
        grav_badge = {
            'critique': 'badge-red',
            'warning': 'badge-orange',
            'info': 'badge-blue',
        }.get(a['gravite'], 'badge-gray')
        rows += (
            '<tr><td><span class="badge ' + grav_badge + '">' + str(a["type"]) + '</span></td>'
            + '<td>' + str(a["message"]) + '</td>'
            + '<td>' + str(a["mission_numero"] or "—") + '</td>'
            + '<td>' + str(a["immatriculation"] or "—") + '</td>'
            + '<td>' + ('✅' if a["traitee"] else '🔴 Ouverte') + '</td>'
            + '<td>' + str((a["date_alerte"] or "")[:16]) + '</td>'
            + '<td><a href="/alertes/' + str(a["id"]) + '/traiter" class="btn btn-primary" style="padding:4px 10px;font-size:11px">Traiter</a></td></tr>'
        )

    content = '<h1>🚨 Alertes & Incidents — ' + str(len(alertes)) + '</h1>'
    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr>'
    content += '<th>Type</th><th>Message</th><th>Mission</th><th>Véhicule</th>'
    content += '<th>État</th><th>Date</th><th>Action</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#10b981">✅ Aucune alerte</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='alertes', page_title='Alertes')


@app.route('/alertes/<int:aid>/traiter')
@login_required
def alertes_traiter(aid):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE alertes SET traitee=1 WHERE id=?", (aid,))
    db.commit()
    flash('✅ Alerte traitée', 'success')
    return redirect('/alertes')


# ═══════════════════════════════════════════════════════════════
# 📈 KPI & RAPPORTS
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

    ca_total = sc("SELECT COALESCE(SUM(montant_fcfa),0) FROM missions WHERE statut='terminee'")
    km_total = sc("SELECT COALESCE(SUM(distance_km),0) FROM missions WHERE statut='terminee'")
    tonnage_total = sc("SELECT COALESCE(SUM(tonnage),0) FROM missions WHERE statut='terminee'")
    taux_remplissage = sc("""
        SELECT AVG(tonnage * 100.0 / (SELECT AVG(capacite_tonnes) FROM vehicules WHERE statut != 'maintenance'))
        FROM missions WHERE statut='terminee'
    """) or 0

    # CO2 économisé vs camions individuels
    co2_economise = km_total * 0.15  # 150g CO2/km économisé par mutualisation

    # Top clients par CA
    cur.execute("""
        SELECT c.nom, COUNT(m.id) AS nb_missions, COALESCE(SUM(m.montant_fcfa),0) AS ca
        FROM clients c
        LEFT JOIN missions m ON m.client_id=c.id AND m.statut='terminee'
        GROUP BY c.id ORDER BY ca DESC LIMIT 5
    """)
    top_clients = cur.fetchall()
    clients_html = ''.join(
        '<tr><td>' + str(c["nom"]) + '</td>'
        + '<td style="text-align:right">' + str(c["nb_missions"]) + '</td>'
        + '<td style="text-align:right">' + f'{c["ca"]:,.0f}' + ' F</td></tr>'
        for c in top_clients
    )

    # Par corridor
    cur.execute("""
        SELECT co.nom, COUNT(m.id) AS nb, COALESCE(SUM(m.distance_km),0) AS km,
               COALESCE(SUM(m.montant_fcfa),0) AS ca
        FROM corridors co
        LEFT JOIN missions m ON m.corridor_id=co.id AND m.statut='terminee'
        GROUP BY co.id ORDER BY ca DESC
    """)
    corridors = cur.fetchall()
    corridors_html = ''.join(
        '<tr><td>' + str(c["nom"]) + '</td>'
        + '<td style="text-align:right">' + str(c["nb"]) + '</td>'
        + '<td style="text-align:right">' + f'{c["km"]:,.0f}' + ' km</td>'
        + '<td style="text-align:right">' + f'{c["ca"]:,.0f}' + ' F</td></tr>'
        for c in corridors
    )

    content = '<h1>📈 KPI & Rapports Transport</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">CA Total</div><div class="kpi-value" style="font-size:18px">' + f'{ca_total:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-icon">🛣️</div><div class="kpi-label">Km parcourus</div><div class="kpi-value">' + f'{km_total:,.0f}' + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">⚖️</div><div class="kpi-label">Tonnage</div><div class="kpi-value">' + f'{tonnage_total:,.0f}' + ' T</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">📊</div><div class="kpi-label">Taux remplissage</div><div class="kpi-value">' + f'{taux_remplissage:.1f}' + '%</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#059669,#047857)"><div class="kpi-icon">🌱</div><div class="kpi-label">CO₂ économisé</div><div class="kpi-value">' + f'{co2_economise:,.0f}' + ' kg</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>🏆 Top 5 clients</h2>'
    content += '<table><thead><tr><th>Client</th><th style="text-align:right">Missions</th><th style="text-align:right">CA</th></tr></thead>'
    content += '<tbody>' + (clients_html or '<tr><td colspan="3" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>🛣️ Performance corridors</h2>'
    content += '<table><thead><tr><th>Corridor</th><th style="text-align:right">Missions</th><th style="text-align:right">Km</th><th style="text-align:right">CA</th></tr></thead>'
    content += '<tbody>' + (corridors_html or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    content += '<div class="card" style="border-left-color:#10b981"><h2>🎯 Objectifs SM10 AGRO Transport</h2>'
    content += '<ul style="line-height:2;color:#334155;font-size:14px">'
    content += '<li>📉 <strong>-30%</strong> coûts logistiques via mutualisation</li>'
    content += '<li>🌍 <strong>2 000</strong> transporteurs CEDEAO connectés</li>'
    content += '<li>📊 <strong>Traçabilité totale</strong> colis par QR code</li>'
    content += '<li>🛃 <strong>Douanes digitalisées</strong> pour corridors Dakar-Bamako, Dakar-Abidjan</li>'
    content += '<li>🌱 <strong>-20% émissions CO₂</strong> via optimisation taux de remplissage</li>'
    content += '</ul></div>'

    return render_page(content, active='rapports', page_title='KPI')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
