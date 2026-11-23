"""
🏠 Immobilier & Baux — Application principale
Biens · Propriétaires · Locataires · Baux · Loyers · Quittances · Impayés
"""
from flask import Flask, render_template_string, redirect, url_for, session, request, jsonify, Response, send_file, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import sqlite3
import os
import io

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'omega-immo-secret-2026')

DB_PATH = '/app/data/immobilier.db'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id, username, role, nom_complet, agence=''):
        self.id = id
        self.username = username
        self.role = role
        self.nom_complet = nom_complet
        self.agence = agence


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
        return User(r['id'], r['username'], r['role'], r['nom_complet'], r['agence'] or '')
    return None


# ═══════════════════════════════════════════════════════════════
# LAYOUT — DESIGN IMMOBILIER
# ═══════════════════════════════════════════════════════════════

LAYOUT = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — OMEGA Immobilier</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,-apple-system,sans-serif}}
body{{background:#f0f4f8;color:#1e293b;font-size:14px}}
.nav{{background:linear-gradient(135deg,#1e40af,#1e3a8a);color:#fff;padding:0 22px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 3px 12px rgba(0,0,0,.15);flex-wrap:wrap;border-bottom:4px solid #f59e0b}}
.nav-brand{{font-weight:900;font-size:18px;display:flex;align-items:center;gap:12px;padding:16px 0;letter-spacing:-0.3px}}
.nav-brand-icon{{width:40px;height:40px;background:#f59e0b;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(245,158,11,.4)}}
.nav-links{{display:flex;gap:2px;flex-wrap:wrap}}
.nav-links a{{color:#dbeafe;text-decoration:none;padding:8px 13px;border-radius:8px;font-size:12.5px;font-weight:600;transition:.2s;display:flex;align-items:center;gap:6px}}
.nav-links a:hover{{background:rgba(255,255,255,.12);color:#fff}}
.nav-links a.active{{background:#f59e0b;color:#fff;box-shadow:0 4px 10px rgba(245,158,11,.4)}}
.nav-user{{font-size:12.5px;display:flex;gap:10px;align-items:center;color:#dbeafe}}
.nav-user a{{color:#fff;text-decoration:none;background:rgba(0,0,0,.25);padding:7px 14px;border-radius:8px;font-weight:600}}
.container{{max-width:1600px;margin:0 auto;padding:24px}}
h1{{color:#1e40af;margin-bottom:20px;font-size:24px;font-weight:800;letter-spacing:-0.4px}}
h2{{color:#1e40af;font-size:18px;margin-bottom:14px;font-weight:700}}
.card{{background:#fff;padding:22px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:18px;border-left:4px solid #f59e0b}}
table{{width:100%;border-collapse:collapse}}
thead{{background:#1e40af;color:#fff}}
th{{padding:12px;text-align:left;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}}
td{{padding:11px;border-bottom:1px solid #f1f5f9;font-size:13.5px}}
tbody tr:hover{{background:#eff6ff}}
.btn{{display:inline-block;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px;border:none;cursor:pointer;transition:.15s;letter-spacing:.2px}}
.btn:hover{{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.15)}}
.btn-primary{{background:#1e40af;color:#fff}}
.btn-gold{{background:#f59e0b;color:#fff}}
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
.badge-gold{{background:#fef3c7;color:#b45309}}
.bien-card{{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:.2s}}
.bien-card:hover{{transform:translateY(-3px);box-shadow:0 8px 20px rgba(30,64,175,.15)}}
.bien-icon{{background:linear-gradient(135deg,#1e40af,#1e3a8a);color:#fff;height:100px;display:flex;align-items:center;justify-content:center;font-size:44px}}
.bien-body{{padding:16px}}
.bien-price{{font-size:20px;font-weight:900;color:#10b981}}
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-brand">
    <div class="nav-brand-icon">🏠</div>
    <div>OMEGA IMMOBILIER<span style="display:block;font-size:10px;font-weight:500;letter-spacing:2px;color:#dbeafe">BAUX · GESTION LOCATIVE · SÉNÉGAL</span></div>
  </div>
  <div class="nav-links">
    <a href="/" class="{a_dash}">📊 Dashboard</a>
    <a href="/biens" class="{a_biens}">🏠 Biens</a>
    <a href="/proprietaires" class="{a_prop}">👤 Propriétaires</a>
    <a href="/locataires" class="{a_loc}">👥 Locataires</a>
    <a href="/baux" class="{a_baux}">📋 Baux</a>
    <a href="/loyers" class="{a_loyers}">💰 Loyers</a>
    <a href="/quittances" class="{a_quit}">📜 Quittances</a>
    <a href="/impayes" class="{a_imp}">⚠️ Impayés</a>
    <a href="/etats-lieux" class="{a_etat}">📸 États lieux</a>
    <a href="/commissions" class="{a_com}">📊 Commissions</a>
    <a href="/reclamations" class="{a_recl}">🔧 Réclamations</a>
    <a href="/marche" class="{a_mar}">📈 Marché</a>
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


def render_page(content, active='dashboard', page_title='Immobilier'):
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
        a_biens='active' if active == 'biens' else '',
        a_prop='active' if active == 'proprietaires' else '',
        a_loc='active' if active == 'locataires' else '',
        a_baux='active' if active == 'baux' else '',
        a_loyers='active' if active == 'loyers' else '',
        a_quit='active' if active == 'quittances' else '',
        a_imp='active' if active == 'impayes' else '',
        a_etat='active' if active == 'etats_lieux' else '',
        a_com='active' if active == 'commissions' else '',
        a_recl='active' if active == 'reclamations' else '',
        a_mar='active' if active == 'marche' else '',
    )


@app.route('/health')
def health():
    return {'project': 'OMEGA IMMOBILIER', 'service': 'immobilier-baux',
            'status': 'ok', 'timestamp': datetime.now().isoformat(), 'version': '1.0'}


LOGIN_HTML = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Connexion — OMEGA Immobilier</title>
<style>body{{font-family:system-ui;background:linear-gradient(135deg,#1e40af,#1e3a8a);min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0}}
.box{{background:#fff;padding:42px;border-radius:16px;box-shadow:0 25px 70px rgba(0,0,0,.4);width:100%;max-width:420px;border-top:5px solid #f59e0b}}
.logo{{text-align:center;font-size:56px;margin-bottom:12px}}
h1{{color:#1e40af;margin:0 0 6px;text-align:center;font-size:22px;font-weight:900;letter-spacing:-0.3px}}
.subtitle{{text-align:center;color:#64748b;font-size:12px;margin-bottom:24px;letter-spacing:1.5px;text-transform:uppercase;font-weight:600}}
input{{width:100%;padding:14px;border:2px solid #e2e8f0;border-radius:10px;margin-bottom:14px;font-size:15px;box-sizing:border-box}}
input:focus{{outline:none;border-color:#1e40af;box-shadow:0 0 0 3px rgba(30,64,175,.1)}}
button{{width:100%;background:#f59e0b;color:#fff;padding:15px;border:none;border-radius:10px;font-weight:800;font-size:15px;cursor:pointer;letter-spacing:.5px;text-transform:uppercase}}
button:hover{{background:#d97706}}
.err{{background:#fee2e2;color:#991b1b;padding:11px;border-radius:8px;margin-bottom:14px;font-size:13px;border-left:4px solid #ef4444}}
.hint{{margin-top:20px;padding:12px;background:#eff6ff;border-radius:8px;font-size:12px;color:#1e40af;text-align:center;border:1px dashed #93c5fd}}</style></head>
<body><div class="box">
<div class="logo">🏠</div>
<h1>OMEGA IMMOBILIER</h1>
<div class="subtitle">Baux · Gestion locative · Sénégal</div>
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
            user = User(r['id'], r['username'], r['role'], r['nom_complet'], r['agence'] or '')
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
        'biens_total': sc("SELECT COUNT(*) FROM biens"),
        'biens_dispo': sc("SELECT COUNT(*) FROM biens WHERE statut='disponible'"),
        'biens_loues': sc("SELECT COUNT(*) FROM biens WHERE statut='loue'"),
        'proprietaires': sc("SELECT COUNT(*) FROM proprietaires WHERE statut='actif'"),
        'locataires': sc("SELECT COUNT(*) FROM locataires WHERE statut='actif'"),
        'baux_actifs': sc("SELECT COUNT(*) FROM baux WHERE statut='actif'"),
        'loyers_mois': sc("SELECT COALESCE(SUM(total_du),0) FROM loyers WHERE periode=strftime('%Y-%m','now')"),
        'impayes_total': sc("SELECT COUNT(*) FROM impayes WHERE statut='ouvert'"),
        'impayes_montant': sc("SELECT COALESCE(SUM(montant_impaye),0) FROM impayes WHERE statut='ouvert'"),
        'commissions_a_payer': sc("SELECT COALESCE(SUM(montant_commission),0) FROM commissions WHERE statut='a_payer'"),
        'reclamations_ouvertes': sc("SELECT COUNT(*) FROM reclamations WHERE statut='ouverte'"),
    }

    # Biens par type
    cur.execute("""
        SELECT type, COUNT(*) AS nb FROM biens
        GROUP BY type ORDER BY nb DESC
    """)
    types_biens = cur.fetchall()
    type_html = ''
    for t in types_biens:
        icon = {'villa': '🏡', 'appartement': '🏢', 'studio': '🏠', 'chambre': '🚪',
                'terrain': '🌍', 'bureau': '🏢'}.get(t['type'], '🏠')
        type_html += (
            '<tr><td>' + icon + ' ' + str(t["type"]).capitalize() + '</td>'
            + '<td style="text-align:center;font-weight:800">' + str(t["nb"]) + '</td></tr>'
        )

    # Loyers du mois
    cur.execute("""
        SELECT l.*, b.numero AS bail_numero, lo.nom AS locataire_nom, lo.prenom AS locataire_prenom
        FROM loyers l
        LEFT JOIN baux b ON b.id=l.bail_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        WHERE l.periode = strftime('%Y-%m','now')
        ORDER BY l.id DESC LIMIT 8
    """)
    loyers_mois = cur.fetchall()
    loyer_html = ''
    for l in loyers_mois:
        statut_badge = {'paye': 'badge-green', 'a_payer': 'badge-orange', 'en_retard': 'badge-red'}.get(l['statut'], 'badge-gray')
        loyer_html += (
            '<tr><td><strong>' + str(l["bail_numero"] or "—") + '</strong></td>'
            + '<td>' + str(l["locataire_prenom"] or "") + ' ' + str(l["locataire_nom"] or "") + '</td>'
            + '<td style="text-align:right;font-weight:800">' + f'{l["total_du"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right">' + f'{l["montant_paye"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(l["statut"]) + '</span></td></tr>'
        )

    content = '<h1>📊 Tableau de bord Immobilier</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-icon">🏠</div><div class="kpi-label">Total biens</div><div class="kpi-value">' + str(stats["biens_total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🏡</div><div class="kpi-label">Loués</div><div class="kpi-value">' + str(stats["biens_loues"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">✅</div><div class="kpi-label">Disponibles</div><div class="kpi-value">' + str(stats["biens_dispo"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">📋</div><div class="kpi-label">Baux actifs</div><div class="kpi-value">' + str(stats["baux_actifs"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">👥</div><div class="kpi-label">Locataires</div><div class="kpi-value">' + str(stats["locataires"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">⚠️</div><div class="kpi-label">Impayés ouverts</div><div class="kpi-value">' + str(stats["impayes_total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div class="kpi-icon">💰</div><div class="kpi-label">Loyers du mois</div><div class="kpi-value" style="font-size:18px">' + f'{stats["loyers_mois"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">📊</div><div class="kpi-label">Commissions</div><div class="kpi-value" style="font-size:18px">' + f'{stats["commissions_a_payer"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:18px">'
    content += '<div class="card"><h2>💰 Loyers du mois en cours</h2>'
    content += '<table><thead><tr><th>Bail</th><th>Locataire</th><th style="text-align:right">Montant dû</th><th style="text-align:right">Payé</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (loyer_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:30px">Aucun loyer ce mois</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>🏠 Biens par type</h2>'
    content += '<table><thead><tr><th>Type</th><th style="text-align:center">Nombre</th></tr></thead>'
    content += '<tbody>' + (type_html or '<tr><td colspan="2" style="text-align:center;color:#94a3b8;padding:30px">Aucun bien</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    content += '<div class="card"><h2>⚡ Actions rapides</h2>'
    content += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:12px">'
    actions = [
        ('/biens/nouveau', '🏠 Nouveau bien', '#1e40af'),
        ('/baux/nouveau', '📋 Nouveau bail', '#f59e0b'),
        ('/loyers/nouveau', '💰 Enregistrer loyer', '#10b981'),
        ('/impayes', '⚠️ Voir impayés', '#ef4444'),
        ('/reclamations/nouvelle', '🔧 Réclamation', '#8b5cf6'),
        ('/marche', '📈 Cote marché', '#ec4899'),
    ]
    for url, label, color in actions:
        content += '<a href="' + url + '" style="text-decoration:none"><div style="background:' + color + ';color:#fff;padding:20px;border-radius:10px;text-align:center;font-weight:700;font-size:13px">' + label + '</div></a>'
    content += '</div></div>'

    return render_page(content, active='dashboard', page_title='Dashboard')


# ═══════════════════════════════════════════════════════════════
# 🏠 BIENS IMMOBILIERS
# ═══════════════════════════════════════════════════════════════

@app.route('/biens')
@login_required
def biens_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()
    type_f = request.args.get('type', '')
    statut_f = request.args.get('statut', '')

    sql = """
        SELECT b.*, p.nom AS proprietaire_nom, p.prenom AS proprietaire_prenom,
               (SELECT numero FROM baux WHERE bien_id=b.id AND statut='actif' LIMIT 1) AS bail_actif
        FROM biens b
        LEFT JOIN proprietaires p ON p.id=b.proprietaire_id
        WHERE 1=1
    """
    params = []
    if q:
        sql += " AND (b.titre LIKE ? OR b.quartier LIKE ? OR b.code LIKE ? OR b.adresse LIKE ?)"
        params += [f'%{q}%'] * 4
    if type_f:
        sql += " AND b.type=?"
        params.append(type_f)
    if statut_f:
        sql += " AND b.statut=?"
        params.append(statut_f)
    sql += " ORDER BY b.id DESC LIMIT 200"
    cur.execute(sql, params)
    biens = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM biens")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM biens WHERE statut='disponible'")
    stats['dispo'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM biens WHERE statut='loue'")
    stats['loue'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(loyer_mensuel),0) FROM biens WHERE statut='loue'")
    stats['loyer_moy'] = cur.fetchone()[0]

    cards = ''
    for b in biens:
        type_icons = {'villa': '🏡', 'appartement': '🏢', 'studio': '🏠', 'chambre': '🚪',
                      'terrain': '🌍', 'bureau': '🏢'}
        icon = type_icons.get(b['type'], '🏠')
        statut_badge = {
            'disponible': 'badge-green',
            'loue': 'badge-blue',
            'maintenance': 'badge-orange',
            'indisponible': 'badge-red',
        }.get(b['statut'], 'badge-gray')
        cards += '<div class="bien-card">'
        cards += '<div class="bien-icon">' + icon + '</div>'
        cards += '<div class="bien-body">'
        cards += '<div style="font-weight:800;color:#1e293b;font-size:14px;margin-bottom:4px">' + str(b["titre"]) + '</div>'
        cards += '<div style="font-size:11.5px;color:#64748b;margin-bottom:8px">📍 ' + str(b["quartier"] or "") + ' · ' + str(b["ville"] or "") + '</div>'
        cards += '<div style="font-size:12px;color:#475569;margin-bottom:10px">'
        if b['type'] != 'terrain':
            cards += '🛏 ' + str(b["nb_chambres"]) + ' ch · 🚿 ' + str(b["nb_salles_bain"]) + ' sdb · 📐 ' + f'{b["superficie_m2"]:.0f}' + 'm²'
        else:
            cards += '📐 ' + f'{b["superficie_m2"]:.0f}' + 'm²'
        cards += '</div>'
        cards += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'
        cards += '<div class="bien-price">' + f'{b["loyer_mensuel"]:,.0f}' + ' F<span style="font-size:12px;color:#64748b;font-weight:400">/mois</span></div>'
        cards += '<span class="badge ' + statut_badge + '">' + str(b["statut"]) + '</span>'
        cards += '</div>'
        cards += '<a href="/biens/' + str(b["id"]) + '" class="btn btn-primary" style="padding:6px 10px;font-size:11.5px;width:100%;text-align:center;display:block">👁 Voir détails</a>'
        cards += '</div></div>'

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🏠 Biens immobiliers — ' + str(len(biens)) + '</h1>'
    content += '<a href="/biens/nouveau" class="btn btn-primary">+ Nouveau bien</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-icon">🏠</div><div class="kpi-label">Total biens</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Disponibles</div><div class="kpi-value">' + str(stats["dispo"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">🏡</div><div class="kpi-label">Loués</div><div class="kpi-value">' + str(stats["loue"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">💰</div><div class="kpi-label">Loyer moyen</div><div class="kpi-value" style="font-size:16px">' + f'{stats["loyer_moy"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher bien, quartier..." style="max-width:400px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/biens" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Tous</a> '
    for s in ['disponible', 'loue', 'maintenance', 'indisponible']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/biens?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px">' + (cards or '<p style="grid-column:1/-1;text-align:center;color:#94a3b8;padding:40px">Aucun bien</p>') + '</div>'

    return render_page(content, active='biens', page_title='Biens')


@app.route('/biens/nouveau', methods=['GET', 'POST'])
@login_required
def biens_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO biens
                (code, proprietaire_id, type, titre, description, adresse, quartier,
                 ville, region, latitude, longitude, superficie_m2, nb_pieces,
                 nb_chambres, nb_salles_bain, etage, meuble, equipements,
                 loyer_mensuel, charges_mensuelles, depot_garantie, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None,
                  int(request.form.get('proprietaire_id') or 0) or None,
                  request.form.get('type'),
                  request.form.get('titre'),
                  request.form.get('description'),
                  request.form.get('adresse'),
                  request.form.get('quartier'),
                  request.form.get('ville') or 'Dakar',
                  request.form.get('region'),
                  float(request.form.get('latitude') or 0),
                  float(request.form.get('longitude') or 0),
                  float(request.form.get('superficie_m2') or 0),
                  int(request.form.get('nb_pieces') or 0),
                  int(request.form.get('nb_chambres') or 0),
                  int(request.form.get('nb_salles_bain') or 0),
                  int(request.form.get('etage') or 0),
                  1 if request.form.get('meuble') else 0,
                  request.form.get('equipements'),
                  float(request.form.get('loyer_mensuel') or 0),
                  float(request.form.get('charges_mensuelles') or 0),
                  float(request.form.get('depot_garantie') or 0),
                  request.form.get('statut') or 'disponible',
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Bien créé', 'success')
            return redirect('/biens')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, code, nom, prenom FROM proprietaires WHERE statut='actif' ORDER BY nom")
    proprietaires = cur.fetchall()
    opts_p = ''.join('<option value="' + str(p["id"]) + '">' + str(p["code"] or "") + ' — ' + str(p["nom"] or "") + ' ' + str(p["prenom"] or "") + '</option>' for p in proprietaires)

    content = '<h1>🏠 Nouveau bien immobilier</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Titre du bien *</label><input type="text" name="titre" required autofocus placeholder="Villa moderne à Almadies"></div>'
    content += '<div><label>Propriétaire *</label><select name="proprietaire_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_p + '</select></div>'
    content += '<div><label>Type *</label><select name="type" required>'
    content += '<option value="villa">🏡 Villa</option>'
    content += '<option value="appartement">🏢 Appartement</option>'
    content += '<option value="studio">🏠 Studio</option>'
    content += '<option value="chambre">🚪 Chambre</option>'
    content += '<option value="terrain">🌍 Terrain</option>'
    content += '<option value="bureau">🏢 Bureau / Local commercial</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Description</label><textarea name="description" rows="3"></textarea></div>'
    content += '<div style="grid-column:1/-1"><label>Adresse</label><input type="text" name="adresse"></div>'
    content += '<div><label>Quartier</label><input type="text" name="quartier" placeholder="Almadies, Médina..."></div>'
    content += '<div><label>Ville</label><input type="text" name="ville" value="Dakar"></div>'
    content += '<div><label>Région</label><input type="text" name="region" value="Dakar"></div>'
    content += '<div><label>Latitude GPS</label><input type="number" step="0.0001" name="latitude" value="14.6928"></div>'
    content += '<div><label>Longitude GPS</label><input type="number" step="0.0001" name="longitude" value="-17.4467"></div>'
    content += '<div><label>Superficie (m²)</label><input type="number" step="1" name="superficie_m2" value="0"></div>'
    content += '<div><label>Nb pièces</label><input type="number" name="nb_pieces" value="0"></div>'
    content += '<div><label>Nb chambres</label><input type="number" name="nb_chambres" value="0"></div>'
    content += '<div><label>Nb salles de bain</label><input type="number" name="nb_salles_bain" value="0"></div>'
    content += '<div><label>Étage</label><input type="number" name="etage" value="0"></div>'
    content += '<div><label>Équipements</label><input type="text" name="equipements" placeholder="Eau, électricité, climatisation"></div>'
    content += '<div><label>Loyer mensuel (FCFA) *</label><input type="number" step="1000" name="loyer_mensuel" required value="200000"></div>'
    content += '<div><label>Charges mensuelles</label><input type="number" step="1000" name="charges_mensuelles" value="0"></div>'
    content += '<div><label>Dépôt de garantie</label><input type="number" step="1000" name="depot_garantie" value="0"></div>'
    content += '<div><label>Statut</label><select name="statut">'
    content += '<option value="disponible">✅ Disponible</option>'
    content += '<option value="loue">🔑 Loué</option>'
    content += '<option value="maintenance">🔧 Maintenance</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label><input type="checkbox" name="meuble" value="1" style="width:auto;margin-right:8px"> Bien meublé</label></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/biens" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='biens', page_title='Nouveau bien')


@app.route('/biens/<int:bid>')
@login_required
def biens_detail(bid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT b.*, p.nom AS proprietaire_nom, p.prenom AS proprietaire_prenom,
               p.telephone AS proprietaire_tel, p.email AS proprietaire_email
        FROM biens b
        LEFT JOIN proprietaires p ON p.id=b.proprietaire_id
        WHERE b.id=?
    """, (bid,))
    b = cur.fetchone()
    if not b:
        flash('❌ Bien introuvable', 'error')
        return redirect('/biens')

    # Bail actif
    cur.execute("""
        SELECT b2.*, l.nom AS locataire_nom, l.prenom AS locataire_prenom,
               l.telephone AS locataire_tel
        FROM baux b2
        LEFT JOIN locataires l ON l.id=b2.locataire_id
        WHERE b2.bien_id=? AND b2.statut='actif'
        LIMIT 1
    """, (bid,))
    bail_actif = cur.fetchone()

    # Historique baux
    cur.execute("""
        SELECT b2.*, l.nom AS locataire_nom, l.prenom AS locataire_prenom
        FROM baux b2
        LEFT JOIN locataires l ON l.id=b2.locataire_id
        WHERE b2.bien_id=?
        ORDER BY b2.id DESC LIMIT 10
    """, (bid,))
    historique = cur.fetchall()

    hist_html = ''
    for h in historique:
        statut_badge = 'badge-green' if h['statut'] == 'actif' else 'badge-gray'
        hist_html += (
            '<tr><td><strong>' + str(h["numero"]) + '</strong></td>'
            + '<td>' + str(h["locataire_prenom"] or "") + ' ' + str(h["locataire_nom"] or "") + '</td>'
            + '<td>' + str((h["date_debut"] or "—")[:10]) + ' → ' + str((h["date_fin"] or "—")[:10]) + '</td>'
            + '<td style="text-align:right">' + f'{h["loyer_mensuel"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(h["statut"]) + '</span></td></tr>'
        )

    type_icons = {'villa': '🏡', 'appartement': '🏢', 'studio': '🏠', 'chambre': '🚪',
                  'terrain': '🌍', 'bureau': '🏢'}
    icon = type_icons.get(b['type'], '🏠')
    statut_badge = {
        'disponible': 'badge-green', 'loue': 'badge-blue',
        'maintenance': 'badge-orange', 'indisponible': 'badge-red',
    }.get(b['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">' + icon + ' ' + str(b["titre"]) + ' <span class="badge ' + statut_badge + '">' + str(b["statut"]) + '</span></h1>'
    content += '<a href="/biens" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-label">Code</div><div class="kpi-value" style="font-size:16px">' + str(b["code"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Loyer</div><div class="kpi-value" style="font-size:18px">' + f'{b["loyer_mensuel"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Charges</div><div class="kpi-value" style="font-size:18px">' + f'{b["charges_mensuelles"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Dépôt garantie</div><div class="kpi-value" style="font-size:18px">' + f'{b["depot_garantie"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>📋 Caractéristiques</h2><table>'
    content += '<tr><td><strong>Type</strong></td><td>' + str(b["type"] or "—").capitalize() + '</td></tr>'
    content += '<tr><td><strong>Superficie</strong></td><td>' + f'{b["superficie_m2"]:.0f}' + ' m²</td></tr>'
    content += '<tr><td><strong>Pièces</strong></td><td>' + str(b["nb_pieces"]) + '</td></tr>'
    content += '<tr><td><strong>Chambres</strong></td><td>' + str(b["nb_chambres"]) + '</td></tr>'
    content += '<tr><td><strong>Salles de bain</strong></td><td>' + str(b["nb_salles_bain"]) + '</td></tr>'
    content += '<tr><td><strong>Étage</strong></td><td>' + str(b["etage"]) + '</td></tr>'
    content += '<tr><td><strong>Meublé</strong></td><td>' + ('✅ Oui' if b["meuble"] else '❌ Non') + '</td></tr>'
    content += '<tr><td><strong>Équipements</strong></td><td>' + str(b["equipements"] or "—") + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>👤 Propriétaire</h2>'
    if b['proprietaire_nom']:
        content += '<div style="padding:12px;background:#f8fafc;border-radius:8px;margin-bottom:12px">'
        content += '<div style="font-weight:800;font-size:16px;color:#1e40af">' + str(b["proprietaire_prenom"] or "") + ' ' + str(b["proprietaire_nom"]) + '</div>'
        content += '<div style="font-size:13px;color:#64748b;margin-top:6px">📞 ' + str(b["proprietaire_tel"] or "—") + '</div>'
        content += '<div style="font-size:13px;color:#64748b">✉️ ' + str(b["proprietaire_email"] or "—") + '</div>'
        content += '</div>'
        content += '<a href="/proprietaires/' + str(b["proprietaire_id"]) + '" class="btn btn-primary" style="width:100%;text-align:center;display:block">Voir le profil</a>'
    else:
        content += '<p style="color:#94a3b8">Aucun propriétaire assigné</p>'
    content += '</div>'
    content += '</div>'

    # Localisation
    content += '<div class="card"><h2>📍 Localisation</h2>'
    content += '<table><tr><td><strong>Adresse</strong></td><td>' + str(b["adresse"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Quartier</strong></td><td>' + str(b["quartier"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Ville</strong></td><td>' + str(b["ville"] or "—") + '</td></tr>'
    if b['latitude'] and b['longitude']:
        content += '<tr><td><strong>GPS</strong></td><td>' + f'{b["latitude"]:.4f}, {b["longitude"]:.4f}' + '</td></tr>'
    content += '</table></div>'

    if bail_actif:
        content += '<div class="card" style="border-left-color:#10b981"><h2>🔑 Bail actif</h2>'
        content += '<div style="padding:14px;background:#f0fdf4;border-radius:8px;margin-bottom:12px">'
        content += '<div style="font-weight:800;color:#047857">' + str(bail_actif["numero"]) + '</div>'
        content += '<div style="font-size:13px;color:#475569;margin-top:4px">Locataire : ' + str(bail_actif["locataire_prenom"] or "") + ' ' + str(bail_actif["locataire_nom"] or "") + '</div>'
        content += '<div style="font-size:13px;color:#475569">📞 ' + str(bail_actif["locataire_tel"] or "") + '</div>'
        content += '<div style="font-size:13px;color:#475569">📅 ' + str((bail_actif["date_debut"] or "")[:10]) + ' → ' + str((bail_actif["date_fin"] or "")[:10]) + '</div>'
        content += '</div>'
        content += '<a href="/baux/' + str(bail_actif["id"]) + '" class="btn btn-primary" style="width:100%;text-align:center;display:block">Voir le bail</a>'
        content += '</div>'

    content += '<div class="card"><h2>📋 Historique des baux (' + str(len(historique)) + ')</h2>'
    content += '<table><thead><tr><th>N° Bail</th><th>Locataire</th><th>Période</th><th style="text-align:right">Loyer</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (hist_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucun bail enregistré</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='biens', page_title='Bien')


# ═══════════════════════════════════════════════════════════════
# 👤 PROPRIÉTAIRES
# ═══════════════════════════════════════════════════════════════

@app.route('/proprietaires')
@login_required
def proprietaires_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()

    sql = """
        SELECT p.*,
               (SELECT COUNT(*) FROM biens WHERE proprietaire_id=p.id) AS nb_biens,
               (SELECT COUNT(*) FROM biens WHERE proprietaire_id=p.id AND statut='loue') AS nb_loues
        FROM proprietaires p
        WHERE 1=1
    """
    params = []
    if q:
        sql += " AND (p.nom LIKE ? OR p.prenom LIKE ? OR p.code LIKE ? OR p.telephone LIKE ?)"
        params += [f'%{q}%'] * 4
    sql += " ORDER BY p.nom, p.prenom LIMIT 200"
    cur.execute(sql, params)
    proprietaires = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM proprietaires WHERE statut='actif'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM proprietaires WHERE type='particulier'")
    stats['part'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM proprietaires WHERE type='societe'")
    stats['soc'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT ville) FROM proprietaires WHERE ville IS NOT NULL")
    stats['villes'] = cur.fetchone()[0]

    rows = ''
    for p in proprietaires:
        type_badge = 'badge-blue' if p['type'] == 'particulier' else 'badge-gold'
        rows += (
            '<tr><td><strong style="color:#1e40af">' + str(p["code"] or "—") + '</strong></td>'
            + '<td><strong>' + str(p["prenom"] or "") + ' ' + str(p["nom"] or "") + '</strong></td>'
            + '<td><span class="badge ' + type_badge + '">' + str(p["type"]) + '</span></td>'
            + '<td>' + str(p["telephone"] or "—") + '</td>'
            + '<td>' + str(p["ville"] or "—") + '</td>'
            + '<td style="text-align:center;font-weight:800">' + str(p["nb_biens"]) + '</td>'
            + '<td style="text-align:center;color:#10b981;font-weight:800">' + str(p["nb_loues"]) + '</td>'
            + '<td><a href="/proprietaires/' + str(p["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👤 Propriétaires — ' + str(len(proprietaires)) + '</h1>'
    content += '<a href="/proprietaires/nouveau" class="btn btn-primary">+ Nouveau propriétaire</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-icon">👤</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🏡</div><div class="kpi-label">Particuliers</div><div class="kpi-value">' + str(stats["part"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">🏢</div><div class="kpi-label">Sociétés</div><div class="kpi-value">' + str(stats["soc"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🗺️</div><div class="kpi-label">Villes</div><div class="kpi-value">' + str(stats["villes"]) + '</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher propriétaire, téléphone..." style="max-width:500px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Nom</th><th>Type</th><th>Téléphone</th><th>Ville</th>'
    content += '<th style="text-align:center">Biens</th><th style="text-align:center">Loués</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun propriétaire</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='proprietaires', page_title='Propriétaires')


@app.route('/proprietaires/nouveau', methods=['GET', 'POST'])
@login_required
def proprietaires_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO proprietaires
                (code, nom, prenom, type, telephone, telephone2, email, adresse,
                 ville, pays, num_piece, rib_bancaire, mobile_money, notes, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('prenom'),
                  request.form.get('type') or 'particulier',
                  request.form.get('telephone'),
                  request.form.get('telephone2'),
                  request.form.get('email'),
                  request.form.get('adresse'),
                  request.form.get('ville'),
                  request.form.get('pays') or 'Sénégal',
                  request.form.get('num_piece'),
                  request.form.get('rib_bancaire'),
                  request.form.get('mobile_money'),
                  request.form.get('notes'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Propriétaire créé', 'success')
            return redirect('/proprietaires')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>👤 Nouveau propriétaire</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Nom *</label><input type="text" name="nom" required autofocus></div>'
    content += '<div><label>Prénom</label><input type="text" name="prenom"></div>'
    content += '<div><label>Type</label><select name="type">'
    content += '<option value="particulier">👤 Particulier</option>'
    content += '<option value="societe">🏢 Société</option>'
    content += '</select></div>'
    content += '<div><label>Téléphone *</label><input type="text" name="telephone" required></div>'
    content += '<div><label>Téléphone 2</label><input type="text" name="telephone2"></div>'
    content += '<div><label>Email</label><input type="email" name="email"></div>'
    content += '<div style="grid-column:1/-1"><label>Adresse</label><input type="text" name="adresse"></div>'
    content += '<div><label>Ville</label><input type="text" name="ville" value="Dakar"></div>'
    content += '<div><label>Pays</label><input type="text" name="pays" value="Sénégal"></div>'
    content += '<div><label>N° pièce (CNI/Passeport)</label><input type="text" name="num_piece"></div>'
    content += '<div><label>RIB bancaire</label><input type="text" name="rib_bancaire"></div>'
    content += '<div><label>Mobile Money</label><input type="text" name="mobile_money" placeholder="+221 77 XXX XX XX"></div>'
    content += '<div style="grid-column:1/-1"><label>Notes</label><textarea name="notes" rows="2"></textarea></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/proprietaires" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='proprietaires', page_title='Nouveau propriétaire')


@app.route('/proprietaires/<int:pid>')
@login_required
def proprietaires_detail(pid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM proprietaires WHERE id=?", (pid,))
    p = cur.fetchone()
    if not p:
        flash('❌ Propriétaire introuvable', 'error')
        return redirect('/proprietaires')

    cur.execute("""
        SELECT b.*, (SELECT numero FROM baux WHERE bien_id=b.id AND statut='actif' LIMIT 1) AS bail_actif
        FROM biens b WHERE b.proprietaire_id=?
        ORDER BY b.id DESC
    """, (pid,))
    biens = cur.fetchall()
    biens_html = ''
    total_loyers = 0
    for b in biens:
        statut_badge = {'disponible': 'badge-green', 'loue': 'badge-blue', 'maintenance': 'badge-orange'}.get(b['statut'], 'badge-gray')
        total_loyers += b['loyer_mensuel'] if b['statut'] == 'loue' else 0
        biens_html += (
            '<tr><td><strong>' + str(b["code"]) + '</strong></td>'
            + '<td>' + str(b["titre"]) + '<br><small style="color:#64748b">' + str(b["quartier"] or "") + '</small></td>'
            + '<td>' + str(b["type"]).capitalize() + '</td>'
            + '<td style="text-align:right">' + f'{b["loyer_mensuel"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(b["statut"]) + '</span></td>'
            + '<td><a href="/biens/' + str(b["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👤 ' + str(p["prenom"] or "") + ' ' + str(p["nom"]) + '</h1>'
    content += '<a href="/proprietaires" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-label">Code</div><div class="kpi-value" style="font-size:16px">' + str(p["code"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Biens</div><div class="kpi-value">' + str(len(biens)) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Loyers/mois</div><div class="kpi-value" style="font-size:16px">' + f'{total_loyers:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Type</div><div class="kpi-value" style="font-size:16px">' + str(p["type"]).capitalize() + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations personnelles</h2><table>'
    content += '<tr><td><strong>Téléphone</strong></td><td>' + str(p["telephone"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Téléphone 2</strong></td><td>' + str(p["telephone2"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Email</strong></td><td>' + str(p["email"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Adresse</strong></td><td>' + str(p["adresse"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Ville</strong></td><td>' + str(p["ville"] or "—") + ', ' + str(p["pays"] or "") + '</td></tr>'
    content += '<tr><td><strong>N° pièce</strong></td><td>' + str(p["num_piece"] or "—") + '</td></tr>'
    content += '<tr><td><strong>RIB</strong></td><td>' + str(p["rib_bancaire"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Mobile Money</strong></td><td>' + str(p["mobile_money"] or "—") + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>🏠 Biens de ce propriétaire (' + str(len(biens)) + ')</h2>'
    content += '<table><thead><tr><th>Code</th><th>Bien</th><th>Type</th><th style="text-align:right">Loyer</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (biens_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:20px">Aucun bien</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='proprietaires', page_title='Propriétaire')


# ═══════════════════════════════════════════════════════════════
# 👥 LOCATAIRES
# ═══════════════════════════════════════════════════════════════

@app.route('/locataires')
@login_required
def locataires_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()

    sql = """
        SELECT l.*,
               (SELECT COUNT(*) FROM baux WHERE locataire_id=l.id) AS nb_baux,
               (SELECT COUNT(*) FROM baux WHERE locataire_id=l.id AND statut='actif') AS nb_actifs
        FROM locataires l
        WHERE 1=1
    """
    params = []
    if q:
        sql += " AND (l.nom LIKE ? OR l.prenom LIKE ? OR l.code LIKE ? OR l.telephone LIKE ?)"
        params += [f'%{q}%'] * 4
    sql += " ORDER BY l.nom, l.prenom LIMIT 300"
    cur.execute(sql, params)
    locataires = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM locataires WHERE statut='actif'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(revenu_mensuel),0) FROM locataires")
    stats['revenu'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM locataires WHERE statut='actif'")
    stats['actifs'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT profession) FROM locataires WHERE profession IS NOT NULL")
    stats['professions'] = cur.fetchone()[0]

    rows = ''
    for l in locataires:
        rows += (
            '<tr><td><strong style="color:#1e40af">' + str(l["code"] or "—") + '</strong></td>'
            + '<td><strong>' + str(l["prenom"] or "") + ' ' + str(l["nom"] or "") + '</strong><br><small style="color:#64748b">' + str(l["profession"] or "") + '</small></td>'
            + '<td>' + str(l["telephone"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{l["revenu_mensuel"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center">' + str(l["nb_baux"]) + '</td>'
            + '<td style="text-align:center;color:#10b981;font-weight:800">' + str(l["nb_actifs"]) + '</td>'
            + '<td><a href="/locataires/' + str(l["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👥 Locataires — ' + str(len(locataires)) + '</h1>'
    content += '<a href="/locataires/nouveau" class="btn btn-primary">+ Nouveau locataire</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-icon">👥</div><div class="kpi-label">Total actifs</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">Revenu moyen</div><div class="kpi-value" style="font-size:16px">' + f'{stats["revenu"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">👨‍💼</div><div class="kpi-label">Professions</div><div class="kpi-value">' + str(stats["professions"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">📋</div><div class="kpi-label">Baux actifs</div><div class="kpi-value">' + str(sum(l["nb_actifs"] for l in locataires)) + '</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher locataire, téléphone..." style="max-width:500px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Nom</th><th>Téléphone</th><th style="text-align:right">Revenu</th>'
    content += '<th style="text-align:center">Baux</th><th style="text-align:center">Actifs</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucun locataire</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='locataires', page_title='Locataires')


@app.route('/locataires/nouveau', methods=['GET', 'POST'])
@login_required
def locataires_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO locataires
                (code, nom, prenom, type, telephone, telephone2, email, adresse_actuelle,
                 profession, employeur, revenu_mensuel, num_piece,
                 garant_nom, garant_telephone, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('prenom'),
                  request.form.get('type') or 'particulier',
                  request.form.get('telephone'),
                  request.form.get('telephone2'),
                  request.form.get('email'),
                  request.form.get('adresse_actuelle'),
                  request.form.get('profession'),
                  request.form.get('employeur'),
                  float(request.form.get('revenu_mensuel') or 0),
                  request.form.get('num_piece'),
                  request.form.get('garant_nom'),
                  request.form.get('garant_telephone'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Locataire créé', 'success')
            return redirect('/locataires')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>👥 Nouveau locataire</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Nom *</label><input type="text" name="nom" required autofocus></div>'
    content += '<div><label>Prénom</label><input type="text" name="prenom"></div>'
    content += '<div><label>Type</label><select name="type">'
    content += '<option value="particulier">👤 Particulier</option>'
    content += '<option value="societe">🏢 Société</option>'
    content += '</select></div>'
    content += '<div><label>Téléphone *</label><input type="text" name="telephone" required></div>'
    content += '<div><label>Téléphone 2</label><input type="text" name="telephone2"></div>'
    content += '<div><label>Email</label><input type="email" name="email"></div>'
    content += '<div style="grid-column:1/-1"><label>Adresse actuelle</label><input type="text" name="adresse_actuelle"></div>'
    content += '<div><label>Profession</label><input type="text" name="profession"></div>'
    content += '<div><label>Employeur</label><input type="text" name="employeur"></div>'
    content += '<div><label>Revenu mensuel (FCFA)</label><input type="number" step="10000" name="revenu_mensuel" value="0"></div>'
    content += '<div><label>N° pièce</label><input type="text" name="num_piece"></div>'
    content += '<div><label>Garant (nom)</label><input type="text" name="garant_nom"></div>'
    content += '<div><label>Garant (téléphone)</label><input type="text" name="garant_telephone"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/locataires" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='locataires', page_title='Nouveau locataire')


@app.route('/locataires/<int:lid>')
@login_required
def locataires_detail(lid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM locataires WHERE id=?", (lid,))
    l = cur.fetchone()
    if not l:
        flash('❌ Locataire introuvable', 'error')
        return redirect('/locataires')

    cur.execute("""
        SELECT b.*, bi.titre AS bien_titre, bi.quartier, bi.loyer_mensuel
        FROM baux b
        LEFT JOIN biens bi ON bi.id=b.bien_id
        WHERE b.locataire_id=?
        ORDER BY b.id DESC
    """, (lid,))
    baux = cur.fetchall()

    baux_html = ''
    total_impaye = 0
    for b in baux:
        statut_badge = 'badge-green' if b['statut'] == 'actif' else 'badge-gray'
        cur.execute("SELECT COALESCE(SUM(total_du - montant_paye),0) AS du FROM loyers WHERE bail_id=? AND statut != 'paye'", (b['id'],))
        du = (cur.fetchone() or {})['du'] or 0
        total_impaye += du
        baux_html += (
            '<tr><td><strong>' + str(b["numero"]) + '</strong></td>'
            + '<td>' + str(b["bien_titre"] or "—") + '</td>'
            + '<td>' + str((b["date_debut"] or "—")[:10]) + ' → ' + str((b["date_fin"] or "—")[:10]) + '</td>'
            + '<td style="text-align:right">' + f'{b["loyer_mensuel"]:,.0f}' + ' F</td>'
            + ('<td style="text-align:right;color:#ef4444;font-weight:800">' + f'{du:,.0f}' + ' F</td>' if du > 0 else '<td style="text-align:right;color:#10b981">✅ OK</td>')
            + '<td><span class="badge ' + statut_badge + '">' + str(b["statut"]) + '</span></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👥 ' + str(l["prenom"] or "") + ' ' + str(l["nom"]) + '</h1>'
    content += '<a href="/locataires" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-label">Code</div><div class="kpi-value" style="font-size:16px">' + str(l["code"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Revenu</div><div class="kpi-value" style="font-size:16px">' + f'{l["revenu_mensuel"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Baux</div><div class="kpi-value">' + str(len(baux)) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-label">Impayé total</div><div class="kpi-value" style="font-size:16px">' + f'{total_impaye:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations personnelles</h2><table>'
    content += '<tr><td><strong>Téléphone</strong></td><td>' + str(l["telephone"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Téléphone 2</strong></td><td>' + str(l["telephone2"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Email</strong></td><td>' + str(l["email"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Adresse actuelle</strong></td><td>' + str(l["adresse_actuelle"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Profession</strong></td><td>' + str(l["profession"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Employeur</strong></td><td>' + str(l["employeur"] or "—") + '</td></tr>'
    content += '<tr><td><strong>N° pièce</strong></td><td>' + str(l["num_piece"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Garant</strong></td><td>' + str(l["garant_nom"] or "—") + ' — ' + str(l["garant_telephone"] or "") + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>📋 Baux (' + str(len(baux)) + ')</h2>'
    content += '<table><thead><tr><th>N° Bail</th><th>Bien</th><th>Période</th><th style="text-align:right">Loyer</th><th style="text-align:right">Impayé</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (baux_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:20px">Aucun bail</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='locataires', page_title='Locataire')


# ═══════════════════════════════════════════════════════════════
# 📋 BAUX
# ═══════════════════════════════════════════════════════════════

@app.route('/baux')
@login_required
def baux_liste():
    db = get_db()
    cur = db.cursor()
    statut_f = request.args.get('statut', '')
    q = request.args.get('q', '').strip()

    sql = """
        SELECT b.*, bi.titre AS bien_titre, bi.quartier, bi.type AS bien_type,
               lo.nom AS locataire_nom, lo.prenom AS locataire_prenom,
               pr.nom AS proprietaire_nom, pr.prenom AS proprietaire_prenom
        FROM baux b
        LEFT JOIN biens bi ON bi.id=b.bien_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        LEFT JOIN proprietaires pr ON pr.id=b.proprietaire_id
        WHERE 1=1
    """
    params = []
    if statut_f:
        sql += " AND b.statut=?"
        params.append(statut_f)
    if q:
        sql += " AND (b.numero LIKE ? OR lo.nom LIKE ? OR bi.titre LIKE ?)"
        params += [f'%{q}%'] * 3
    sql += " ORDER BY b.id DESC LIMIT 200"
    cur.execute(sql, params)
    baux = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM baux")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM baux WHERE statut='actif'")
    stats['actifs'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM baux WHERE statut='termine'")
    stats['termines'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(loyer_mensuel),0) FROM baux WHERE statut='actif'")
    stats['loyers_total'] = cur.fetchone()[0]

    rows = ''
    for b in baux:
        statut_badge = {
            'actif': 'badge-green',
            'termine': 'badge-gray',
            'en_attente': 'badge-orange',
            'resilie': 'badge-red',
        }.get(b['statut'], 'badge-gray')
        date_fin = b['date_fin'] or ''
        jours_restants = ''
        if date_fin and b['statut'] == 'actif':
            try:
                df = datetime.strptime(date_fin[:10], '%Y-%m-%d')
                j = (df - datetime.now()).days
                if j < 0:
                    jours_restants = '<br><small style="color:#ef4444">⚠ Expiré</small>'
                elif j < 60:
                    jours_restants = '<br><small style="color:#f59e0b">Expire dans ' + str(j) + 'j</small>'
            except Exception:
                pass

        rows += (
            '<tr><td><strong style="color:#1e40af">' + str(b["numero"] or "—") + '</strong></td>'
            + '<td>' + str(b["bien_titre"] or "—") + '<br><small style="color:#64748b">' + str(b["quartier"] or "") + '</small></td>'
            + '<td>' + str(b["locataire_prenom"] or "") + ' ' + str(b["locataire_nom"] or "") + '</td>'
            + '<td>' + str((b["date_debut"] or "—")[:10]) + '<br><small style="color:#64748b">→ ' + str((b["date_fin"] or "—")[:10]) + jours_restants + '</small></td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{b["loyer_mensuel"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(b["statut"]) + '</span></td>'
            + '<td><a href="/baux/' + str(b["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📋 Baux — ' + str(len(baux)) + '</h1>'
    content += '<a href="/baux/nouveau" class="btn btn-primary">+ Nouveau bail</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-icon">📋</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🔑</div><div class="kpi-label">Actifs</div><div class="kpi-value">' + str(stats["actifs"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#64748b,#475569)"><div class="kpi-icon">✅</div><div class="kpi-label">Terminés</div><div class="kpi-value">' + str(stats["termines"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">💰</div><div class="kpi-label">Loyers mensuels</div><div class="kpi-value" style="font-size:16px">' + f'{stats["loyers_total"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher n° bail, locataire, bien..." style="max-width:500px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/baux" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Tous</a> '
    for s in ['actif', 'en_attente', 'termine', 'resilie']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/baux?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Bail</th><th>Bien</th><th>Locataire</th><th>Période</th><th style="text-align:right">Loyer</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucun bail</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='baux', page_title='Baux')


@app.route('/baux/nouveau', methods=['GET', 'POST'])
@login_required
def baux_nouveau():
    db = get_db()
    cur = db.cursor()
    bien_id_pre = int(request.args.get('bien_id') or 0)
    locataire_id_pre = int(request.args.get('locataire_id') or 0)

    if request.method == 'POST':
        try:
            bien_id = int(request.form.get('bien_id') or 0)
            locataire_id = int(request.form.get('locataire_id') or 0)

            cur.execute("SELECT proprietaire_id, loyer_mensuel, charges_mensuelles, depot_garantie FROM biens WHERE id=?", (bien_id,))
            b = cur.fetchone()
            proprietaire_id = b['proprietaire_id'] if b else None

            cur.execute("""
                INSERT INTO baux (numero, bien_id, locataire_id, proprietaire_id,
                                    date_debut, date_fin, duree_mois, loyer_mensuel,
                                    charges_mensuelles, depot_garantie, jour_echeance,
                                    mode_paiement, statut, date_signature_proprietaire,
                                    date_signature_locataire, renouvellement_auto,
                                    preavis_mois, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None, bien_id, locataire_id, proprietaire_id,
                  request.form.get('date_debut'),
                  request.form.get('date_fin'),
                  int(request.form.get('duree_mois') or 12),
                  float(request.form.get('loyer_mensuel') or (b['loyer_mensuel'] if b else 0)),
                  float(request.form.get('charges_mensuelles') or (b['charges_mensuelles'] if b else 0)),
                  float(request.form.get('depot_garantie') or (b['depot_garantie'] if b else 0)),
                  int(request.form.get('jour_echeance') or 5),
                  request.form.get('mode_paiement') or 'mobile_money',
                  request.form.get('statut') or 'actif',
                  datetime.now().strftime('%Y-%m-%d') if request.form.get('statut') == 'actif' else None,
                  datetime.now().strftime('%Y-%m-%d') if request.form.get('statut') == 'actif' else None,
                  1 if request.form.get('renouvellement_auto') else 0,
                  int(request.form.get('preavis_mois') or 3),
                  request.form.get('notes'),
                  datetime.now().isoformat()))

            # Si bail actif → bien passe en "loué"
            if request.form.get('statut') == 'actif':
                cur.execute("UPDATE biens SET statut='loue' WHERE id=?", (bien_id,))

            db.commit()
            flash('✅ Bail créé', 'success')
            return redirect('/baux')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, code, titre, loyer_mensuel, charges_mensuelles, depot_garantie FROM biens WHERE statut='disponible' ORDER BY titre")
    biens = cur.fetchall()
    cur.execute("SELECT id, code, nom, prenom FROM locataires WHERE statut='actif' ORDER BY nom")
    locataires = cur.fetchall()

    opts_b = ''.join('<option value="' + str(b["id"]) + '"' + (' selected' if b["id"] == bien_id_pre else '') + ' data-loyer="' + str(b["loyer_mensuel"]) + '" data-charges="' + str(b["charges_mensuelles"] or 0) + '" data-depot="' + str(b["depot_garantie"] or 0) + '">' + str(b["code"]) + ' — ' + str(b["titre"]) + ' (' + f'{b["loyer_mensuel"]:,.0f}' + ' F)</option>' for b in biens)
    opts_l = ''.join('<option value="' + str(l["id"]) + '"' + (' selected' if l["id"] == locataire_id_pre else '') + '>' + str(l["code"]) + ' — ' + str(l["prenom"] or "") + ' ' + str(l["nom"]) + '</option>' for l in locataires)

    today = datetime.now().strftime('%Y-%m-%d')
    one_year = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')

    content = '<h1>📋 Nouveau bail</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Bien *</label><select name="bien_id" id="bien_select" required onchange="updateBien()">'
    content += '<option value="">— Sélectionner —</option>' + opts_b + '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Locataire *</label><select name="locataire_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_l + '</select></div>'
    content += '<div><label>Date début *</label><input type="date" name="date_debut" required value="' + today + '"></div>'
    content += '<div><label>Date fin *</label><input type="date" name="date_fin" required value="' + one_year + '"></div>'
    content += '<div><label>Durée (mois)</label><input type="number" name="duree_mois" value="12"></div>'
    content += '<div><label>Loyer mensuel (FCFA) *</label><input type="number" step="1000" name="loyer_mensuel" id="loyer" required value="0"></div>'
    content += '<div><label>Charges mensuelles (FCFA)</label><input type="number" step="1000" name="charges_mensuelles" id="charges" value="0"></div>'
    content += '<div><label>Dépôt de garantie (FCFA)</label><input type="number" step="1000" name="depot_garantie" id="depot" value="0"></div>'
    content += '<div><label>Jour échéance (1-28)</label><input type="number" name="jour_echeance" value="5" min="1" max="28"></div>'
    content += '<div><label>Mode de paiement</label><select name="mode_paiement">'
    content += '<option value="mobile_money">📱 Mobile Money</option>'
    content += '<option value="virement">🏦 Virement</option>'
    content += '<option value="especes">💵 Espèces</option>'
    content += '<option value="cheque">📝 Chèque</option>'
    content += '</select></div>'
    content += '<div><label>Préavis (mois)</label><input type="number" name="preavis_mois" value="3"></div>'
    content += '<div><label>Statut</label><select name="statut">'
    content += '<option value="actif">✅ Actif</option>'
    content += '<option value="en_attente">⏳ En attente signature</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label><input type="checkbox" name="renouvellement_auto" value="1" checked style="width:auto;margin-right:8px"> Renouvellement automatique</label></div>'
    content += '<div style="grid-column:1/-1"><label>Notes</label><textarea name="notes" rows="3"></textarea></div>'
    content += '</div>'
    content += '<script>'
    content += 'function updateBien() {'
    content += 'var sel = document.getElementById("bien_select");'
    content += 'var opt = sel.options[sel.selectedIndex];'
    content += 'if (opt.dataset.loyer) document.getElementById("loyer").value = Math.round(opt.dataset.loyer);'
    content += 'if (opt.dataset.charges) document.getElementById("charges").value = Math.round(opt.dataset.charges);'
    content += 'if (opt.dataset.depot) document.getElementById("depot").value = Math.round(opt.dataset.depot);'
    content += '}'
    content += '</script>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer le bail</button>'
    content += '<a href="/baux" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='baux', page_title='Nouveau bail')


@app.route('/baux/<int:bid>', methods=['GET', 'POST'])
@login_required
def baux_detail(bid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT b.*, bi.titre AS bien_titre, bi.quartier, bi.adresse AS bien_adresse,
               bi.ville, bi.type AS bien_type, bi.superficie_m2,
               lo.nom AS locataire_nom, lo.prenom AS locataire_prenom,
               lo.telephone AS locataire_tel, lo.email AS locataire_email,
               pr.nom AS proprietaire_nom, pr.prenom AS proprietaire_prenom,
               pr.telephone AS proprietaire_tel
        FROM baux b
        LEFT JOIN biens bi ON bi.id=b.bien_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        LEFT JOIN proprietaires pr ON pr.id=b.proprietaire_id
        WHERE b.id=?
    """, (bid,))
    b = cur.fetchone()
    if not b:
        flash('❌ Bail introuvable', 'error')
        return redirect('/baux')

    # Signer le bail
    if request.method == 'POST':
        try:
            action = request.form.get('action') or 'signer'
            if action == 'signer':
                partie = request.form.get('partie') or 'locataire'
                if partie == 'locataire':
                    cur.execute("UPDATE baux SET date_signature_locataire=? WHERE id=?", (datetime.now().strftime('%Y-%m-%d'), bid))
                elif partie == 'proprietaire':
                    cur.execute("UPDATE baux SET date_signature_proprietaire=? WHERE id=?", (datetime.now().strftime('%Y-%m-%d'), bid))
                flash('✅ Bail signé par ' + partie, 'success')
            elif action == 'resilier':
                cur.execute("UPDATE baux SET statut='resilie' WHERE id=?", (bid,))
                cur.execute("UPDATE biens SET statut='disponible' WHERE id=?", (b['bien_id'],))
                flash('✅ Bail résilié', 'success')
            db.commit()
            return redirect('/baux/' + str(bid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    # Loyers du bail
    cur.execute("SELECT * FROM loyers WHERE bail_id=? ORDER BY periode DESC LIMIT 12", (bid,))
    loyers = cur.fetchall()
    loyers_html = ''
    for l in loyers:
        statut_badge = {'paye': 'badge-green', 'a_payer': 'badge-orange', 'en_retard': 'badge-red'}.get(l['statut'], 'badge-gray')
        loyers_html += (
            '<tr><td>' + str(l["periode"]) + '</td>'
            + '<td>' + str((l["date_echeance"] or "—")[:10]) + '</td>'
            + '<td style="text-align:right">' + f'{l["total_du"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right">' + f'{l["montant_paye"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(l["statut"]) + '</span></td>'
            + '<td><a href="/loyers/' + str(l["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    statut_badge = {'actif': 'badge-green', 'en_attente': 'badge-orange', 'termine': 'badge-gray', 'resilie': 'badge-red'}.get(b['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📋 ' + str(b["numero"]) + ' <span class="badge ' + statut_badge + '">' + str(b["statut"]) + '</span></h1>'
    content += '<div>'
    content += '<a href="/baux/' + str(bid) + '/pdf" class="btn btn-gold">📄 Contrat PDF</a> '
    content += '<a href="/baux" class="btn btn-secondary" style="margin-left:6px">← Retour</a></div></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-label">Loyer</div><div class="kpi-value" style="font-size:18px">' + f'{b["loyer_mensuel"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Charges</div><div class="kpi-value" style="font-size:18px">' + f'{b["charges_mensuelles"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Dépôt garantie</div><div class="kpi-value" style="font-size:18px">' + f'{b["depot_garantie"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Durée</div><div class="kpi-value">' + str(b["duree_mois"]) + ' mois</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>🏠 Bien loué</h2><table>'
    content += '<tr><td><strong>Titre</strong></td><td>' + str(b["bien_titre"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Type</strong></td><td>' + str(b["bien_type"] or "—").capitalize() + '</td></tr>'
    content += '<tr><td><strong>Adresse</strong></td><td>' + str(b["bien_adresse"] or "—") + ', ' + str(b["quartier"] or "") + '</td></tr>'
    content += '<tr><td><strong>Ville</strong></td><td>' + str(b["ville"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Superficie</strong></td><td>' + f'{b["superficie_m2"]:.0f}' + ' m²</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>📅 Période</h2><table>'
    content += '<tr><td><strong>Début</strong></td><td>' + str((b["date_debut"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Fin</strong></td><td>' + str((b["date_fin"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Jour échéance</strong></td><td>' + str(b["jour_echeance"]) + '</td></tr>'
    content += '<tr><td><strong>Mode paiement</strong></td><td>' + str(b["mode_paiement"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Renouvellement auto</strong></td><td>' + ('✅ Oui' if b["renouvellement_auto"] else '❌ Non') + '</td></tr>'
    content += '</table></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>👥 Locataire</h2>'
    content += '<div style="padding:12px;background:#f8fafc;border-radius:8px">'
    content += '<div style="font-weight:800;font-size:16px;color:#1e40af">' + str(b["locataire_prenom"] or "") + ' ' + str(b["locataire_nom"] or "") + '</div>'
    content += '<div style="font-size:13px;color:#64748b;margin-top:6px">📞 ' + str(b["locataire_tel"] or "—") + '</div>'
    content += '<div style="font-size:13px;color:#64748b">✉️ ' + str(b["locataire_email"] or "—") + '</div>'
    content += '<div style="font-size:12px;color:#64748b;margin-top:8px">Signature : ' + ('✅ ' + str((b["date_signature_locataire"] or "")[:10]) if b["date_signature_locataire"] else '⏳ En attente') + '</div>'
    content += '</div>'
    if not b['date_signature_locataire']:
        content += '<form method="post" style="margin-top:12px"><input type="hidden" name="action" value="signer"><input type="hidden" name="partie" value="locataire"><button type="submit" class="btn btn-success" style="width:100%">✍ Faire signer le locataire</button></form>'
    content += '</div>'

    content += '<div class="card"><h2>👤 Propriétaire</h2>'
    content += '<div style="padding:12px;background:#f8fafc;border-radius:8px">'
    content += '<div style="font-weight:800;font-size:16px;color:#1e40af">' + str(b["proprietaire_prenom"] or "") + ' ' + str(b["proprietaire_nom"] or "") + '</div>'
    content += '<div style="font-size:13px;color:#64748b;margin-top:6px">📞 ' + str(b["proprietaire_tel"] or "—") + '</div>'
    content += '<div style="font-size:12px;color:#64748b;margin-top:8px">Signature : ' + ('✅ ' + str((b["date_signature_proprietaire"] or "")[:10]) if b["date_signature_proprietaire"] else '⏳ En attente') + '</div>'
    content += '</div>'
    if not b['date_signature_proprietaire']:
        content += '<form method="post" style="margin-top:12px"><input type="hidden" name="action" value="signer"><input type="hidden" name="partie" value="proprietaire"><button type="submit" class="btn btn-success" style="width:100%">✍ Faire signer le propriétaire</button></form>'
    content += '</div>'
    content += '</div>'

    content += '<div class="card"><h2>💰 Historique des loyers</h2>'
    content += '<table><thead><tr><th>Période</th><th>Échéance</th><th style="text-align:right">Montant dû</th><th style="text-align:right">Payé</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (loyers_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:20px">Aucun loyer enregistré</td></tr>') + '</tbody></table>'
    content += '<div style="margin-top:14px;display:flex;gap:8px;justify-content:flex-end">'
    content += '<a href="/loyers/generer?bail_id=' + str(bid) + '" class="btn btn-primary">📅 Générer loyers du mois</a> '
    if b['statut'] == 'actif':
        content += '<form method="post" onsubmit="return confirm(\'Confirmer la résiliation du bail ?\')"><input type="hidden" name="action" value="resilier"><button type="submit" class="btn btn-danger">❌ Résilier le bail</button></form>'
    content += '</div></div>'

    return render_page(content, active='baux', page_title='Bail')


@app.route('/baux/<int:bid>/pdf')
@login_required
def baux_pdf(bid):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT b.*, bi.titre AS bien_titre, bi.adresse AS bien_adresse, bi.quartier, bi.ville,
               bi.type AS bien_type, bi.superficie_m2, bi.nb_chambres, bi.nb_salles_bain,
               lo.nom AS locataire_nom, lo.prenom AS locataire_prenom, lo.telephone AS locataire_tel,
               lo.num_piece AS locataire_piece,
               pr.nom AS proprietaire_nom, pr.prenom AS proprietaire_prenom,
               pr.telephone AS proprietaire_tel, pr.num_piece AS proprietaire_piece
        FROM baux b
        LEFT JOIN biens bi ON bi.id=b.bien_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        LEFT JOIN proprietaires pr ON pr.id=b.proprietaire_id
        WHERE b.id=?
    """, (bid,))
    b = cur.fetchone()
    if not b:
        flash('❌ Bail introuvable', 'error')
        return redirect('/baux')

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Header
    c.setFillColor(colors.HexColor('#1e40af'))
    c.rect(0, h - 35*mm, w, 35*mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#f59e0b'))
    c.rect(0, h - 35*mm, w, 3*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 18)
    c.drawString(15*mm, h - 15*mm, "OMEGA IMMOBILIER")
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, h - 22*mm, "CONTRAT DE BAIL D'HABITATION")
    c.setFont('Helvetica-Bold', 12)
    c.drawRightString(w - 15*mm, h - 15*mm, str(b["numero"] or ""))
    c.setFont('Helvetica', 9)
    c.drawRightString(w - 15*mm, h - 22*mm, "Émis le " + datetime.now().strftime('%d/%m/%Y'))

    # Titre
    y = h - 45*mm
    c.setFillColor(colors.HexColor('#1e40af'))
    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(w / 2, y, "CONTRAT DE BAIL")
    y -= 8*mm

    # Parties
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(15*mm, y, "ENTRE :")
    y -= 6*mm
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, y, "Le Propriétaire : " + str(b["proprietaire_prenom"] or "") + " " + str(b["proprietaire_nom"] or ""))
    y -= 5*mm
    c.drawString(15*mm, y, "Téléphone : " + str(b["proprietaire_tel"] or "—"))
    y -= 5*mm
    c.drawString(15*mm, y, "N° pièce : " + str(b["proprietaire_piece"] or "—"))

    y -= 8*mm
    c.setFont('Helvetica-Bold', 11)
    c.drawString(15*mm, y, "ET :")
    y -= 6*mm
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, y, "Le Locataire : " + str(b["locataire_prenom"] or "") + " " + str(b["locataire_nom"] or ""))
    y -= 5*mm
    c.drawString(15*mm, y, "Téléphone : " + str(b["locataire_tel"] or "—"))
    y -= 5*mm
    c.drawString(15*mm, y, "N° pièce : " + str(b["locataire_piece"] or "—"))

    # Article 1 - Bien
    y -= 12*mm
    c.setFillColor(colors.HexColor('#1e40af'))
    c.setFont('Helvetica-Bold', 11)
    c.drawString(15*mm, y, "ARTICLE 1 — BIEN LOUÉ")
    y -= 6*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, y, str(b["bien_titre"] or ""))
    y -= 5*mm
    c.drawString(15*mm, y, str(b["bien_adresse"] or "") + ", " + str(b["quartier"] or "") + ", " + str(b["ville"] or ""))
    y -= 5*mm
    if b['bien_type'] != 'terrain':
        c.drawString(15*mm, y, "Type : " + str(b["bien_type"] or "").capitalize() + " · " + f'{b["superficie_m2"]:.0f}' + " m² · " + str(b["nb_chambres"] or 0) + " ch · " + str(b["nb_salles_bain"] or 0) + " sdb")

    # Article 2 - Durée
    y -= 10*mm
    c.setFillColor(colors.HexColor('#1e40af'))
    c.setFont('Helvetica-Bold', 11)
    c.drawString(15*mm, y, "ARTICLE 2 — DURÉE DU BAIL")
    y -= 6*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, y, "Du " + str((b["date_debut"] or "—")[:10]) + " au " + str((b["date_fin"] or "—")[:10]) + " (" + str(b["duree_mois"]) + " mois)")

    # Article 3 - Loyer
    y -= 10*mm
    c.setFillColor(colors.HexColor('#1e40af'))
    c.setFont('Helvetica-Bold', 11)
    c.drawString(15*mm, y, "ARTICLE 3 — LOYER ET CHARGES")
    y -= 6*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, y, f"Loyer mensuel : {b['loyer_mensuel']:,.0f} FCFA")
    y -= 5*mm
    c.drawString(15*mm, y, f"Charges mensuelles : {b['charges_mensuelles']:,.0f} FCFA")
    y -= 5*mm
    c.drawString(15*mm, y, f"Dépôt de garantie : {b['depot_garantie']:,.0f} FCFA")
    y -= 5*mm
    c.drawString(15*mm, y, "Paiement avant le " + str(b["jour_echeance"]) + " de chaque mois par " + str(b["mode_paiement"] or ""))

    # Signatures
    y -= 20*mm
    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, y, "Signé le :")
    y -= 6*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, y, "Propriétaire : " + (str((b["date_signature_proprietaire"] or "")[:10]) if b["date_signature_proprietaire"] else "________________"))
    c.drawString(110*mm, y, "Locataire : " + (str((b["date_signature_locataire"] or "")[:10]) if b["date_signature_locataire"] else "________________"))

    # Footer
    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica', 7)
    c.drawString(15*mm, 10*mm, "OMEGA Immobilier · Dakar, Sénégal · Ce contrat est régi par la loi sénégalaise")
    c.drawRightString(w - 15*mm, 10*mm, "Bail n° " + str(b["numero"]))

    c.showPage()
    c.save()
    buf.seek(0)

    log_action(current_user.id, 'PDF_BAIL', str(b["numero"]), 'baux', bid)
    return send_file(buf, mimetype='application/pdf',
                     download_name='bail_' + str(b["numero"]) + '.pdf')


# ═══════════════════════════════════════════════════════════════
# 💰 LOYERS
# ═══════════════════════════════════════════════════════════════

@app.route('/loyers')
@login_required
def loyers_liste():
    db = get_db()
    cur = db.cursor()
    statut_f = request.args.get('statut', '')
    periode_f = request.args.get('periode', '')

    sql = """
        SELECT l.*, b.numero AS bail_numero, bi.titre AS bien_titre, bi.quartier,
               lo.nom AS locataire_nom, lo.prenom AS locataire_prenom, lo.telephone AS locataire_tel
        FROM loyers l
        LEFT JOIN baux b ON b.id=l.bail_id
        LEFT JOIN biens bi ON bi.id=b.bien_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        WHERE 1=1
    """
    params = []
    if statut_f:
        sql += " AND l.statut=?"
        params.append(statut_f)
    if periode_f:
        sql += " AND l.periode=?"
        params.append(periode_f)
    sql += " ORDER BY l.id DESC LIMIT 200"
    cur.execute(sql, params)
    loyers = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM loyers")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant_paye),0) FROM loyers WHERE statut='paye'")
    stats['paye'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(total_du - montant_paye),0) FROM loyers WHERE statut != 'paye'")
    stats['impaye'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM loyers WHERE statut='en_retard'")
    stats['retard'] = cur.fetchone()[0]

    rows = ''
    for l in loyers:
        statut_badge = {'paye': 'badge-green', 'a_payer': 'badge-orange', 'en_retard': 'badge-red'}.get(l['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong>' + str(l["periode"]) + '</strong></td>'
            + '<td>' + str(l["bail_numero"] or "—") + '<br><small style="color:#64748b">' + str(l["bien_titre"] or "") + '</small></td>'
            + '<td>' + str(l["locataire_prenom"] or "") + ' ' + str(l["locataire_nom"] or "") + '</td>'
            + '<td style="text-align:right">' + f'{l["total_du"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:800">' + f'{l["montant_paye"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(l["statut"]) + '</span></td>'
            + '<td>' + str((l["date_echeance"] or "—")[:10]) + '</td>'
            + '<td><a href="/loyers/' + str(l["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">💰 Loyers — ' + str(len(loyers)) + '</h1>'
    content += '<div>'
    content += '<a href="/loyers/generer" class="btn btn-gold">📅 Générer loyers du mois</a> '
    content += '<a href="/loyers/nouveau" class="btn btn-primary" style="margin-left:6px">+ Enregistrer paiement</a></div></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-icon">💰</div><div class="kpi-label">Total loyers</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Encaissé</div><div class="kpi-value" style="font-size:16px">' + f'{stats["paye"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">⚠️</div><div class="kpi-label">Impayé</div><div class="kpi-value" style="font-size:16px">' + f'{stats["impaye"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">🚨</div><div class="kpi-label">En retard</div><div class="kpi-value">' + str(stats["retard"]) + '</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/loyers" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Tous</a> '
    for s in ['paye', 'a_payer', 'en_retard']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/loyers?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Période</th><th>Bail/Bien</th><th>Locataire</th><th style="text-align:right">Dû</th><th style="text-align:right">Payé</th><th>Statut</th><th>Échéance</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun loyer</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='loyers', page_title='Loyers')


@app.route('/loyers/generer')
@login_required
def loyers_generer():
    db = get_db()
    cur = db.cursor()
    bail_id = int(request.args.get('bail_id') or 0)
    periode = request.args.get('periode') or datetime.now().strftime('%Y-%m')

    if bail_id:
        cur.execute("SELECT * FROM baux WHERE id=? AND statut='actif'", (bail_id,))
        baux = cur.fetchall()
    else:
        cur.execute("SELECT * FROM baux WHERE statut='actif'")
        baux = cur.fetchall()

    generes = 0
    for b in baux:
        cur.execute("SELECT COUNT(*) FROM loyers WHERE bail_id=? AND periode=?", (b['id'], periode))
        if cur.fetchone()[0] > 0:
            continue

        jour = b['jour_echeance'] or 5
        annee, mois = periode.split('-')
        date_echeance = f"{annee}-{mois}-{jour:02d}"

        loyer = b['loyer_mensuel'] or 0
        charges = b['charges_mensuelles'] or 0
        total = loyer + charges

        commission = loyer * 0.10
        montant_prop = loyer - commission

        cur.execute("""
            INSERT INTO loyers (bail_id, periode, date_echeance, loyer_du, charges_dues,
                                  total_du, montant_paye, statut, commission_agence,
                                  montant_proprietaire, created_at)
            VALUES (?,?,?,?,?,?,0,'a_payer',?,?,?)
        """, (b['id'], periode, date_echeance, loyer, charges, total,
              commission, montant_prop, datetime.now().isoformat()))
        generes += 1

    db.commit()
    log_action(current_user.id, 'GENERER_LOYERS', str(generes) + ' loyers pour ' + periode, 'loyers')
    flash('✅ ' + str(generes) + ' loyer(s) généré(s) pour ' + periode, 'success')
    return redirect('/loyers')


@app.route('/loyers/nouveau', methods=['GET', 'POST'])
@login_required
def loyers_nouveau():
    db = get_db()
    cur = db.cursor()
    loyer_id_pre = int(request.args.get('loyer_id') or 0)

    if request.method == 'POST':
        try:
            loyer_id = int(request.form.get('loyer_id') or 0)
            montant = float(request.form.get('montant_paye') or 0)
            mode = request.form.get('mode_paiement') or 'mobile_money'
            reference = request.form.get('reference') or ''

            cur.execute("SELECT * FROM loyers WHERE id=?", (loyer_id,))
            l = cur.fetchone()
            if not l:
                raise ValueError('Loyer introuvable')

            nouveau_paye = (l['montant_paye'] or 0) + montant
            nouveau_statut = 'paye' if nouveau_paye >= (l['total_du'] or 0) else 'a_payer'

            cur.execute("""
                UPDATE loyers SET montant_paye=?, date_paiement=?, mode_paiement=?, statut=?
                WHERE id=?
            """, (nouveau_paye, datetime.now().strftime('%Y-%m-%d'), mode, nouveau_statut, loyer_id))

            if nouveau_statut == 'paye':
                # Générer quittance automatique
                cur.execute("""
                    INSERT INTO quittances (numero, loyer_id, bail_id, date_emission,
                                              montant_recu, mode_paiement, statut, created_at)
                    VALUES (?,?,?,?,?,?, 'valide', ?)
                """, (None, loyer_id, l['bail_id'],
                      datetime.now().strftime('%Y-%m-%d'),
                      nouveau_paye, mode, datetime.now().isoformat()))

            db.commit()
            log_action(current_user.id, 'PAIEMENT_LOYER', f'{montant} F mode {mode}', 'loyers', loyer_id)
            flash('✅ Paiement enregistré : ' + f'{montant:,.0f}' + ' F', 'success')
            return redirect('/loyers/' + str(loyer_id))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("""
        SELECT l.id, l.periode, l.total_du, l.montant_paye,
               b.numero AS bail_numero, lo.nom AS locataire_nom, lo.prenom AS locataire_prenom
        FROM loyers l
        LEFT JOIN baux b ON b.id=l.bail_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        WHERE l.statut != 'paye'
        ORDER BY l.date_echeance DESC LIMIT 200
    """)
    loyers = cur.fetchall()
    opts = ''.join('<option value="' + str(l["id"]) + '"' + (' selected' if l["id"] == loyer_id_pre else '') + ' data-reste="' + str((l["total_du"] or 0) - (l["montant_paye"] or 0)) + '">' + str(l["bail_numero"]) + ' — ' + str(l["periode"]) + ' — ' + str(l["locataire_prenom"] or "") + ' ' + str(l["locataire_nom"] or "") + ' (reste ' + f'{(l["total_du"] or 0) - (l["montant_paye"] or 0):,.0f}' + ' F)</option>' for l in loyers)

    content = '<h1>💰 Enregistrer un paiement de loyer</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="margin-bottom:16px"><label>Loyer à payer *</label><select name="loyer_id" id="loyer_select" required onchange="updateReste()">'
    content += '<option value="">— Sélectionner —</option>' + opts + '</select></div>'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Montant payé (FCFA) *</label><input type="number" step="1000" name="montant_paye" id="montant" required value="0"></div>'
    content += '<div><label>Mode de paiement</label><select name="mode_paiement">'
    content += '<option value="mobile_money">📱 Mobile Money</option>'
    content += '<option value="especes">💵 Espèces</option>'
    content += '<option value="virement">🏦 Virement</option>'
    content += '<option value="cheque">📝 Chèque</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Référence transaction</label><input type="text" name="reference"></div>'
    content += '</div>'
    content += '<script>'
    content += 'function updateReste() {'
    content += 'var sel = document.getElementById("loyer_select");'
    content += 'var opt = sel.options[sel.selectedIndex];'
    content += 'if (opt.dataset.reste) document.getElementById("montant").value = Math.round(opt.dataset.reste);'
    content += '}'
    content += '</script>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Enregistrer le paiement</button>'
    content += '<a href="/loyers" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='loyers', page_title='Paiement loyer')


@app.route('/loyers/<int:lid>', methods=['GET', 'POST'])
@login_required
def loyers_detail(lid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT l.*, b.numero AS bail_numero, b.loyer_mensuel, b.id AS bail_id,
               bi.titre AS bien_titre, bi.quartier,
               lo.nom AS locataire_nom, lo.prenom AS locataire_prenom, lo.telephone AS locataire_tel
        FROM loyers l
        LEFT JOIN baux b ON b.id=l.bail_id
        LEFT JOIN biens bi ON bi.id=b.bien_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        WHERE l.id=?
    """, (lid,))
    l = cur.fetchone()
    if not l:
        flash('❌ Loyer introuvable', 'error')
        return redirect('/loyers')

    # Quittance associée
    cur.execute("SELECT * FROM quittances WHERE loyer_id=?", (lid,))
    quittance = cur.fetchone()

    # Paiements mobile
    cur.execute("SELECT * FROM paiements_mobile WHERE loyer_id=? ORDER BY id DESC", (lid,))
    paiements = cur.fetchall()
    pai_html = ''
    for p in paiements:
        statut_badge = {'en_attente': 'badge-orange', 'reussi': 'badge-green', 'echoue': 'badge-red'}.get(p['statut'], 'badge-gray')
        pai_html += (
            '<tr><td>' + str((p["date_transaction"] or "")[:16]) + '</td>'
            + '<td>' + str(p["operateur"]) + '</td>'
            + '<td>' + str(p["telephone"] or "") + '</td>'
            + '<td style="text-align:right">' + f'{p["montant"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(p["statut"]) + '</span></td></tr>'
        )

    statut_badge = {'paye': 'badge-green', 'a_payer': 'badge-orange', 'en_retard': 'badge-red'}.get(l['statut'], 'badge-gray')
    reste = (l['total_du'] or 0) - (l['montant_paye'] or 0)

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">💰 Loyer ' + str(l["periode"]) + ' <span class="badge ' + statut_badge + '">' + str(l["statut"]) + '</span></h1>'
    content += '<div>'
    if quittance:
        content += '<a href="/quittances/' + str(quittance["id"]) + '" class="btn btn-gold">📜 Quittance</a> '
    content += '<a href="/loyers" class="btn btn-secondary" style="margin-left:6px">← Retour</a></div></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-label">Loyer dû</div><div class="kpi-value" style="font-size:18px">' + f'{l["loyer_du"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Charges</div><div class="kpi-value" style="font-size:18px">' + f'{l["charges_dues"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Payé</div><div class="kpi-value" style="font-size:18px">' + f'{l["montant_paye"]:,.0f}' + ' F</div></div>'
    if reste > 0:
        content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-label">Reste à payer</div><div class="kpi-value" style="font-size:18px">' + f'{reste:,.0f}' + ' F</div></div>'
    else:
        content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Statut</div><div class="kpi-value">✅ PAYÉ</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Détails</h2><table>'
    content += '<tr><td><strong>Bail</strong></td><td>' + str(l["bail_numero"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Bien</strong></td><td>' + str(l["bien_titre"] or "—") + ' — ' + str(l["quartier"] or "") + '</td></tr>'
    content += '<tr><td><strong>Locataire</strong></td><td>' + str(l["locataire_prenom"] or "") + ' ' + str(l["locataire_nom"] or "") + ' — ' + str(l["locataire_tel"] or "") + '</td></tr>'
    content += '<tr><td><strong>Période</strong></td><td>' + str(l["periode"]) + '</td></tr>'
    content += '<tr><td><strong>Échéance</strong></td><td>' + str((l["date_echeance"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Date paiement</strong></td><td>' + str((l["date_paiement"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Mode</strong></td><td>' + str(l["mode_paiement"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Commission agence</strong></td><td>' + f'{l["commission_agence"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td><strong>Part propriétaire</strong></td><td>' + f'{l["montant_proprietaire"]:,.0f}' + ' F</td></tr>'
    content += '</table></div>'

    if reste > 0:
        content += '<div class="card"><h2>💰 Enregistrer un paiement</h2>'
        content += '<form method="post" action="/loyers/nouveau">'
        content += '<input type="hidden" name="loyer_id" value="' + str(lid) + '">'
        content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
        content += '<div><label>Montant (FCFA)</label><input type="number" step="1000" name="montant_paye" value="' + f'{reste:.0f}' + '"></div>'
        content += '<div><label>Mode</label><select name="mode_paiement">'
        content += '<option value="mobile_money">📱 Mobile Money</option>'
        content += '<option value="especes">💵 Espèces</option>'
        content += '<option value="virement">🏦 Virement</option>'
        content += '</select></div>'
        content += '</div>'
        content += '<div style="margin-top:16px"><button type="submit" class="btn btn-success">💾 Enregistrer</button></div>'
        content += '</form></div>'

    if paiements:
        content += '<div class="card"><h2>📱 Paiements mobile</h2>'
        content += '<table><thead><tr><th>Date</th><th>Opérateur</th><th>Téléphone</th><th style="text-align:right">Montant</th><th>Statut</th></tr></thead>'
        content += '<tbody>' + pai_html + '</tbody></table></div>'

    return render_page(content, active='loyers', page_title='Loyer')


# ═══════════════════════════════════════════════════════════════
# 📜 QUITTANCES
# ═══════════════════════════════════════════════════════════════

@app.route('/quittances')
@login_required
def quittances_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT q.*, b.numero AS bail_numero, bi.titre AS bien_titre,
               lo.nom AS locataire_nom, lo.prenom AS locataire_prenom
        FROM quittances q
        LEFT JOIN baux b ON b.id=q.bail_id
        LEFT JOIN biens bi ON bi.id=b.bien_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        ORDER BY q.id DESC LIMIT 200
    """)
    quittances = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM quittances WHERE statut='valide'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant_recu),0) FROM quittances WHERE statut='valide'")
    stats['montant'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM quittances WHERE strftime('%Y-%m',date_emission)=strftime('%Y-%m','now')")
    stats['mois'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant_recu),0) FROM quittances WHERE strftime('%Y-%m',date_emission)=strftime('%Y-%m','now')")
    stats['montant_mois'] = cur.fetchone()[0]

    rows = ''
    for q in quittances:
        rows += (
            '<tr><td><strong style="color:#1e40af">' + str(q["numero"]) + '</strong></td>'
            + '<td>' + str(q["bail_numero"] or "—") + '<br><small style="color:#64748b">' + str(q["bien_titre"] or "") + '</small></td>'
            + '<td>' + str(q["locataire_prenom"] or "") + ' ' + str(q["locataire_nom"] or "") + '</td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{q["montant_recu"]:,.0f}' + ' F</td>'
            + '<td>' + str(q["mode_paiement"] or "—") + '</td>'
            + '<td>' + str((q["date_emission"] or "—")[:10]) + '</td>'
            + '<td><a href="/quittances/' + str(q["id"]) + '" class="btn btn-gold" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<h1>📜 Quittances — ' + str(len(quittances)) + '</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-icon">📜</div><div class="kpi-label">Total quittances</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">Total encaissé</div><div class="kpi-value" style="font-size:16px">' + f'{stats["montant"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">📅</div><div class="kpi-label">Ce mois</div><div class="kpi-value">' + str(stats["mois"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">💵</div><div class="kpi-label">Montant du mois</div><div class="kpi-value" style="font-size:16px">' + f'{stats["montant_mois"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Quittance</th><th>Bail/Bien</th><th>Locataire</th><th style="text-align:right">Montant</th><th>Mode</th><th>Date</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucune quittance</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='quittances', page_title='Quittances')


@app.route('/quittances/<int:qid>')
@login_required
def quittances_detail(qid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT q.*, b.numero AS bail_numero, b.loyer_mensuel, b.charges_mensuelles,
               bi.titre AS bien_titre, bi.adresse AS bien_adresse, bi.quartier,
               lo.nom AS locataire_nom, lo.prenom AS locataire_prenom, lo.telephone AS locataire_tel,
               pr.nom AS proprietaire_nom, pr.prenom AS proprietaire_prenom,
               l.periode, l.date_echeance
        FROM quittances q
        LEFT JOIN baux b ON b.id=q.bail_id
        LEFT JOIN biens bi ON bi.id=b.bien_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        LEFT JOIN proprietaires pr ON pr.id=b.proprietaire_id
        LEFT JOIN loyers l ON l.id=q.loyer_id
        WHERE q.id=?
    """, (qid,))
    q = cur.fetchone()
    if not q:
        flash('❌ Quittance introuvable', 'error')
        return redirect('/quittances')

    qr_url = '/quittances/' + str(qid) + '/qr.png'

    content = '''
    <div style="max-width:600px;margin:0 auto">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
        <a href="/quittances" class="btn btn-secondary">← Retour</a>
        <a href="/quittances/''' + str(qid) + '''/pdf" class="btn btn-gold">📄 Télécharger PDF</a>
      </div>

      <div style="background:linear-gradient(135deg,#fff,#eff6ff);border:4px solid #1e40af;border-radius:16px;padding:32px;box-shadow:0 10px 30px rgba(0,0,0,.15)">
        <div style="text-align:center;margin-bottom:24px">
          <div style="font-size:48px;margin-bottom:8px">📜</div>
          <div style="font-size:11px;letter-spacing:3px;color:#1e40af;font-weight:700">OMEGA IMMOBILIER</div>
          <div style="font-size:22px;font-weight:900;color:#1e40af;margin-top:4px">QUITTANCE DE LOYER</div>
          <div style="height:3px;background:#f59e0b;width:80px;margin:14px auto"></div>
        </div>

        <div style="background:#eff6ff;padding:14px;border-radius:10px;margin-bottom:20px">
          <div style="text-align:center">
            <div style="font-size:11px;color:#64748b;letter-spacing:2px">N° QUITTANCE</div>
            <div style="font-size:16px;font-weight:900;color:#1e40af">''' + str(q['numero']) + '''</div>
            <div style="font-size:11px;color:#64748b;margin-top:6px">Période : ''' + str(q['periode'] or '—') + '''</div>
          </div>
        </div>

        <table style="width:100%;font-size:14px">
          <tr><td style="padding:8px 0;color:#64748b">Locataire</td><td style="padding:8px 0;text-align:right;font-weight:700">''' + str(q['locataire_prenom'] or '') + ' ' + str(q['locataire_nom'] or '') + '''</td></tr>
          <tr><td style="padding:8px 0;color:#64748b">Téléphone</td><td style="padding:8px 0;text-align:right">''' + str(q['locataire_tel'] or '—') + '''</td></tr>
          <tr><td style="padding:8px 0;color:#64748b">Bien loué</td><td style="padding:8px 0;text-align:right;font-weight:700">''' + str(q['bien_titre'] or '') + '''</td></tr>
          <tr><td style="padding:8px 0;color:#64748b">Adresse</td><td style="padding:8px 0;text-align:right">''' + str(q['bien_adresse'] or '') + ', ''' + str(q['quartier'] or '') + '''</td></tr>
          <tr><td style="padding:8px 0;color:#64748b">Bail N°</td><td style="padding:8px 0;text-align:right">''' + str(q['bail_numero'] or '') + '''</td></tr>
          <tr><td style="padding:8px 0;color:#64748b">Propriétaire</td><td style="padding:8px 0;text-align:right">''' + str(q['proprietaire_prenom'] or '') + ' ' + str(q['proprietaire_nom'] or '') + '''</td></tr>
        </table>

        <div style="background:#f0fdf4;padding:16px;border-radius:10px;margin-top:20px;text-align:center">
          <div style="font-size:12px;color:#047857;font-weight:700;letter-spacing:2px">MONTANT REÇU</div>
          <div style="font-size:32px;font-weight:900;color:#047857;margin:6px 0">''' + f'{q["montant_recu"]:,.0f}' + ''' FCFA</div>
          <div style="font-size:12px;color:#64748b">Mode : ''' + str(q['mode_paiement'] or '—') + '''</div>
        </div>

        <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px;align-items:center;margin-top:24px;padding-top:20px;border-top:2px dashed #cbd5e1">
          <div style="font-size:12px;color:#475569">
            <div><strong>Émise le :</strong> ''' + str((q['date_emission'] or '—')[:10]) + '''</div>
            <div style="margin-top:6px"><strong>Statut :</strong> <span class="badge badge-green">''' + str(q['statut']) + '''</span></div>
            <div style="margin-top:10px;color:#64748b;font-style:italic">Quittance valable comme preuve de paiement</div>
          </div>
          <div style="text-align:center">
            <img src="''' + qr_url + '''" alt="QR" style="width:100px;height:100px;border:2px solid #1e40af;border-radius:8px">
            <div style="font-size:9px;color:#64748b;margin-top:4px;font-weight:700">SCANNER POUR VÉRIFIER</div>
          </div>
        </div>
      </div>
    </div>
    '''
    return render_page(content, active='quittances', page_title='Quittance')


@app.route('/quittances/<int:qid>/qr.png')
def quittances_qr(qid):
    import qrcode
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT numero FROM quittances WHERE id=?", (qid,))
    q = cur.fetchone()
    if not q:
        return redirect('/')
    qr_data = 'IMMO|QUIT|' + str(qid) + '|' + (q['numero'] or '')
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#1e40af', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


@app.route('/quittances/<int:qid>/pdf')
@login_required
def quittances_pdf(qid):
    from reportlab.lib.pagesizes import A5
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    import qrcode

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT q.*, b.numero AS bail_numero, bi.titre AS bien_titre, bi.adresse AS bien_adresse, bi.quartier,
               lo.nom AS locataire_nom, lo.prenom AS locataire_prenom, lo.telephone AS locataire_tel,
               pr.nom AS proprietaire_nom, pr.prenom AS proprietaire_prenom, l.periode
        FROM quittances q
        LEFT JOIN baux b ON b.id=q.bail_id
        LEFT JOIN biens bi ON bi.id=b.bien_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        LEFT JOIN proprietaires pr ON pr.id=b.proprietaire_id
        LEFT JOIN loyers l ON l.id=q.loyer_id
        WHERE q.id=?
    """, (qid,))
    q = cur.fetchone()
    if not q:
        flash('❌ Quittance introuvable', 'error')
        return redirect('/quittances')

    qr = qrcode.make('IMMO|QUIT|' + str(qid) + '|' + str(q['numero']))
    qr_buf = io.BytesIO()
    qr.save(qr_buf, format='PNG')
    qr_buf.seek(0)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A5)
    w, h = A5

    # Header bleu marine
    c.setFillColor(colors.HexColor('#1e40af'))
    c.rect(0, h - 25*mm, w, 25*mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#f59e0b'))
    c.rect(0, h - 25*mm, w, 2*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(8*mm, h - 10*mm, 'OMEGA IMMOBILIER')
    c.setFont('Helvetica', 8)
    c.drawString(8*mm, h - 15*mm, 'QUITTANCE DE LOYER')
    c.setFont('Helvetica-Bold', 10)
    c.drawRightString(w - 8*mm, h - 12*mm, str(q['numero'] or ''))

    # Infos
    y = h - 32*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica', 9)
    infos = [
        ('Période', str(q['periode'] or '—')),
        ('Locataire', str(q['locataire_prenom'] or '') + ' ' + str(q['locataire_nom'] or '')),
        ('Bien loué', str(q['bien_titre'] or '')),
        ('Adresse', str(q['bien_adresse'] or '') + ', ' + str(q['quartier'] or '')),
        ('Bail N°', str(q['bail_numero'] or '')),
        ('Propriétaire', str(q['proprietaire_prenom'] or '') + ' ' + str(q['proprietaire_nom'] or '')),
    ]
    for label, val in infos:
        c.setFont('Helvetica-Bold', 8)
        c.setFillColor(colors.HexColor('#64748b'))
        c.drawString(8*mm, y, label.upper())
        c.setFont('Helvetica', 9)
        c.setFillColor(colors.black)
        c.drawString(40*mm, y, val[:50])
        y -= 5*mm

    # Montant
    y -= 6*mm
    c.setFillColor(colors.HexColor('#f0fdf4'))
    c.rect(8*mm, y - 15*mm, w - 16*mm, 18*mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#047857'))
    c.setFont('Helvetica-Bold', 10)
    c.drawString(12*mm, y - 4*mm, 'MONTANT REÇU')
    c.setFont('Helvetica-Bold', 18)
    c.drawString(12*mm, y - 12*mm, f'{q["montant_recu"]:,.0f} FCFA')
    c.setFont('Helvetica', 8)
    c.setFillColor(colors.HexColor('#64748b'))
    c.drawString(12*mm, y - 17*mm, 'Mode : ' + str(q['mode_paiement'] or ''))

    # QR code
    qr_size = 25*mm
    c.drawImage(qr_buf, w - qr_size - 10*mm, y - 25*mm, qr_size, qr_size)

    # Footer
    y -= 35*mm
    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica', 7)
    c.drawString(8*mm, y, 'Émise le : ' + str((q['date_emission'] or '')[:10]))
    y -= 4*mm
    c.drawString(8*mm, y, 'Quittance valable comme preuve de paiement · OMEGA Immobilier · Dakar, Sénégal')

    c.showPage()
    c.save()
    buf.seek(0)

    log_action(current_user.id, 'PDF_QUITTANCE', str(q['numero']), 'quittances', qid)
    return send_file(buf, mimetype='application/pdf',
                     download_name='quittance_' + str(q['numero']) + '.pdf')


# ═══════════════════════════════════════════════════════════════
# ⚠️ IMPAYÉS
# ═══════════════════════════════════════════════════════════════

@app.route('/impayes')
@login_required
def impayes_liste():
    db = get_db()
    cur = db.cursor()
    statut_f = request.args.get('statut', '')

    sql = """
        SELECT i.*, l.periode, l.total_du, l.montant_paye,
               b.numero AS bail_numero,
               lo.nom AS locataire_nom, lo.prenom AS locataire_prenom, lo.telephone AS locataire_tel,
               bi.titre AS bien_titre
        FROM impayes i
        LEFT JOIN loyers l ON l.id=i.loyer_id
        LEFT JOIN baux b ON b.id=i.bail_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        LEFT JOIN biens bi ON bi.id=b.bien_id
        WHERE 1=1
    """
    params = []
    if statut_f:
        sql += " AND i.statut=?"
        params.append(statut_f)
    sql += " ORDER BY i.jours_retard DESC, i.id DESC LIMIT 200"
    cur.execute(sql, params)
    impayes = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM impayes WHERE statut='ouvert'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant_impaye),0) FROM impayes WHERE statut='ouvert'")
    stats['montant'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM impayes WHERE niveau='critique' AND statut='ouvert'")
    stats['critiques'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(jours_retard),0) FROM impayes WHERE statut='ouvert'")
    stats['retard_moyen'] = cur.fetchone()[0]

    rows = ''
    for i in impayes:
        niveau_badge = {'normal': 'badge-blue', 'urgent': 'badge-orange', 'critique': 'badge-red'}.get(i['niveau'], 'badge-gray')
        statut_badge = 'badge-red' if i['statut'] == 'ouvert' else 'badge-green'
        rows += (
            '<tr><td>' + str(i["periode"] or "—") + '</td>'
            + '<td>' + str(i["bail_numero"] or "—") + '<br><small style="color:#64748b">' + str(i["bien_titre"] or "") + '</small></td>'
            + '<td>' + str(i["locataire_prenom"] or "") + ' ' + str(i["locataire_nom"] or "") + '<br><small style="color:#64748b">' + str(i["locataire_tel"] or "") + '</small></td>'
            + '<td style="text-align:right;color:#ef4444;font-weight:800">' + f'{i["montant_impaye"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center;color:#ef4444;font-weight:800">' + str(i["jours_retard"]) + ' j</td>'
            + '<td><span class="badge ' + niveau_badge + '">' + str(i["niveau"]) + '</span></td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(i["statut"]) + '</span></td></tr>'
        )

    content = '<h1>⚠️ Impayés & Recouvrement — ' + str(len(impayes)) + '</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">⚠️</div><div class="kpi-label">Impayés ouverts</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">💰</div><div class="kpi-label">Montant total</div><div class="kpi-value" style="font-size:16px">' + f'{stats["montant"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🚨</div><div class="kpi-label">Critiques</div><div class="kpi-value">' + str(stats["critiques"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">📅</div><div class="kpi-label">Retard moyen</div><div class="kpi-value">' + f'{stats["retard_moyen"]:.0f}' + ' j</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/impayes" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Tous</a> '
    for s in ['ouvert', 'resolu']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/impayes?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '<a href="/impayes/relancer" class="btn btn-danger" style="margin-left:12px">📲 Relancer tous les impayés</a>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Période</th><th>Bail</th><th>Locataire</th><th style="text-align:right">Montant</th><th style="text-align:center">Retard</th><th>Niveau</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#10b981">✅ Aucun impayé</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='impayes', page_title='Impayés')


@app.route('/impayes/relancer')
@login_required
def impayes_relancer():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT i.*, lo.telephone AS locataire_tel, lo.prenom, lo.nom
        FROM impayes i
        LEFT JOIN baux b ON b.id=i.bail_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        WHERE i.statut='ouvert'
    """)
    impayes = cur.fetchall()

    n = 0
    for i in impayes:
        if i['locataire_tel']:
            n += 1
            log_action(current_user.id, 'RELANCE_IMPAYE',
                       f'SMS à {i["locataire_tel"]} pour {i["montant_impaye"]} F',
                       'impayes', i['id'])

    flash('📲 ' + str(n) + ' relances envoyées (mode simulation)', 'success')
    return redirect('/impayes')


# ═══════════════════════════════════════════════════════════════
# 📸 ÉTATS DES LIEUX
# ═══════════════════════════════════════════════════════════════

@app.route('/etats-lieux')
@login_required
def etats_lieux_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT e.*, b.numero AS bail_numero, bi.titre AS bien_titre,
               lo.nom AS locataire_nom, lo.prenom AS locataire_prenom
        FROM etats_lieux e
        LEFT JOIN baux b ON b.id=e.bail_id
        LEFT JOIN biens bi ON bi.id=e.bien_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        ORDER BY e.id DESC LIMIT 200
    """)
    etats = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM etats_lieux")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM etats_lieux WHERE type='entree'")
    stats['entrees'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM etats_lieux WHERE type='sortie'")
    stats['sorties'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM etats_lieux WHERE signe_proprietaire=1 AND signe_locataire=1")
    stats['signes'] = cur.fetchone()[0]

    rows = ''
    for e in etats:
        type_badge = 'badge-green' if e['type'] == 'entree' else 'badge-orange'
        rows += (
            '<tr><td><strong style="color:#1e40af">' + str(e["numero"]) + '</strong></td>'
            + '<td><span class="badge ' + type_badge + '">' + str(e["type"]) + '</span></td>'
            + '<td>' + str(e["bail_numero"] or "—") + '<br><small style="color:#64748b">' + str(e["bien_titre"] or "") + '</small></td>'
            + '<td>' + str(e["locataire_prenom"] or "") + ' ' + str(e["locataire_nom"] or "") + '</td>'
            + '<td>' + str((e["date_etat"] or "—")[:10]) + '</td>'
            + '<td style="text-align:center">' + str(e["nb_photos"]) + '</td>'
            + '<td>' + ('✅✅ Signé' if e["signe_proprietaire"] and e["signe_locataire"] else '⏳ ' + str(e["signe_proprietaire"] + e["signe_locataire"]) + '/2') + '</td>'
            + '<td><a href="/etats-lieux/' + str(e["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📸 États des lieux — ' + str(len(etats)) + '</h1>'
    content += '<a href="/etats-lieux/nouveau" class="btn btn-primary">+ Nouvel état des lieux</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-icon">📸</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🔑</div><div class="kpi-label">Entrées</div><div class="kpi-value">' + str(stats["entrees"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">🚪</div><div class="kpi-label">Sorties</div><div class="kpi-value">' + str(stats["sorties"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">✍</div><div class="kpi-label">Signés</div><div class="kpi-value">' + str(stats["signes"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N°</th><th>Type</th><th>Bail/Bien</th><th>Locataire</th><th>Date</th><th style="text-align:center">Photos</th><th>Signatures</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun état des lieux</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='etats_lieux', page_title='États des lieux')


@app.route('/etats-lieux/nouveau', methods=['GET', 'POST'])
@login_required
def etats_lieux_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            bail_id = int(request.form.get('bail_id') or 0)
            cur.execute("SELECT bien_id FROM baux WHERE id=?", (bail_id,))
            b = cur.fetchone()
            bien_id = b['bien_id'] if b else None

            cur.execute("""
                INSERT INTO etats_lieux (numero, bail_id, bien_id, type, date_etat,
                                           etat_general, observations, realise_par, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (None, bail_id, bien_id,
                  request.form.get('type') or 'entree',
                  request.form.get('date_etat') or datetime.now().strftime('%Y-%m-%d'),
                  request.form.get('etat_general') or 'bon',
                  request.form.get('observations'),
                  current_user.nom_complet,
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ État des lieux créé', 'success')
            return redirect('/etats-lieux')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("""
        SELECT b.id, b.numero, bi.titre AS bien_titre,
               lo.nom AS locataire_nom, lo.prenom AS locataire_prenom
        FROM baux b
        LEFT JOIN biens bi ON bi.id=b.bien_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        WHERE b.statut='actif'
        ORDER BY b.id DESC
    """)
    baux = cur.fetchall()
    opts = ''.join('<option value="' + str(b["id"]) + '">' + str(b["numero"]) + ' — ' + str(b["bien_titre"] or "") + ' — ' + str(b["locataire_prenom"] or "") + ' ' + str(b["locataire_nom"] or "") + '</option>' for b in baux)

    content = '<h1>📸 Nouvel état des lieux</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="margin-bottom:16px"><label>Bail *</label><select name="bail_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts + '</select></div>'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Type *</label><select name="type" required>'
    content += '<option value="entree">🔑 Entrée</option>'
    content += '<option value="sortie">🚪 Sortie</option>'
    content += '</select></div>'
    content += '<div><label>Date</label><input type="date" name="date_etat" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>État général</label><select name="etat_general">'
    content += '<option value="excellent">⭐ Excellent</option>'
    content += '<option value="bon" selected>✅ Bon</option>'
    content += '<option value="moyen">⚠️ Moyen</option>'
    content += '<option value="mauvais">❌ Mauvais</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Observations</label><textarea name="observations" rows="4" placeholder="Détails pièce par pièce..."></textarea></div>'
    content += '</div>'
    content += '<div style="background:#eff6ff;padding:12px;border-radius:8px;margin-top:16px;font-size:12.5px;color:#1e40af">'
    content += '💡 Photos : à ajouter après création (interface dédiée)'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/etats-lieux" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='etats_lieux', page_title='Nouvel état des lieux')


@app.route('/etats-lieux/<int:eid>')
@login_required
def etats_lieux_detail(eid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT e.*, b.numero AS bail_numero, bi.titre AS bien_titre, bi.adresse AS bien_adresse,
               bi.quartier, lo.nom AS locataire_nom, lo.prenom AS locataire_prenom,
               pr.nom AS proprietaire_nom, pr.prenom AS proprietaire_prenom
        FROM etats_lieux e
        LEFT JOIN baux b ON b.id=e.bail_id
        LEFT JOIN biens bi ON bi.id=e.bien_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        LEFT JOIN proprietaires pr ON pr.id=b.proprietaire_id
        WHERE e.id=?
    """, (eid,))
    e = cur.fetchone()
    if not e:
        flash('❌ État des lieux introuvable', 'error')
        return redirect('/etats-lieux')

    type_badge = 'badge-green' if e['type'] == 'entree' else 'badge-orange'

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📸 ' + str(e["numero"]) + ' <span class="badge ' + type_badge + '">' + str(e["type"]) + '</span></h1>'
    content += '<div><a href="/etats-lieux/' + str(eid) + '/pdf" class="btn btn-gold">📄 PDF</a> '
    content += '<a href="/etats-lieux" class="btn btn-secondary" style="margin-left:6px">← Retour</a></div></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-label">Type</div><div class="kpi-value" style="font-size:16px">' + str(e["type"]).capitalize() + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">État général</div><div class="kpi-value" style="font-size:16px">' + str(e["etat_general"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Date</div><div class="kpi-value" style="font-size:16px">' + str((e["date_etat"] or "—")[:10]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Photos</div><div class="kpi-value">' + str(e["nb_photos"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations</h2><table>'
    content += '<tr><td><strong>Bail</strong></td><td>' + str(e["bail_numero"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Bien</strong></td><td>' + str(e["bien_titre"] or "—") + ' — ' + str(e["quartier"] or "") + '</td></tr>'
    content += '<tr><td><strong>Adresse</strong></td><td>' + str(e["bien_adresse"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Locataire</strong></td><td>' + str(e["locataire_prenom"] or "") + ' ' + str(e["locataire_nom"] or "") + '</td></tr>'
    content += '<tr><td><strong>Propriétaire</strong></td><td>' + str(e["proprietaire_prenom"] or "") + ' ' + str(e["proprietaire_nom"] or "") + '</td></tr>'
    content += '<tr><td><strong>Réalisé par</strong></td><td>' + str(e["realise_par"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Signatures</strong></td><td>Propriétaire : ' + ('✅' if e["signe_proprietaire"] else '⏳') + ' · Locataire : ' + ('✅' if e["signe_locataire"] else '⏳') + '</td></tr>'
    content += '</table></div>'

    if e['observations']:
        content += '<div class="card"><h2>📝 Observations</h2>'
        content += '<p style="line-height:1.7;color:#475569">' + str(e["observations"]) + '</p></div>'

    return render_page(content, active='etats_lieux', page_title='État des lieux')


@app.route('/etats-lieux/<int:eid>/pdf')
@login_required
def etats_lieux_pdf(eid):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT e.*, b.numero AS bail_numero, bi.titre AS bien_titre, bi.adresse AS bien_adresse,
               bi.quartier, lo.nom AS locataire_nom, lo.prenom AS locataire_prenom,
               pr.nom AS proprietaire_nom, pr.prenom AS proprietaire_prenom
        FROM etats_lieux e
        LEFT JOIN baux b ON b.id=e.bail_id
        LEFT JOIN biens bi ON bi.id=e.bien_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        LEFT JOIN proprietaires pr ON pr.id=b.proprietaire_id
        WHERE e.id=?
    """, (eid,))
    e = cur.fetchone()
    if not e:
        flash('❌ État des lieux introuvable', 'error')
        return redirect('/etats-lieux')

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    c.setFillColor(colors.HexColor('#1e40af'))
    c.rect(0, h - 30*mm, w, 30*mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#f59e0b'))
    c.rect(0, h - 30*mm, w, 3*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(15*mm, h - 15*mm, "ÉTAT DES LIEUX")
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, h - 22*mm, "OMEGA Immobilier · " + str(e["type"] or "").capitalize())
    c.setFont('Helvetica-Bold', 12)
    c.drawRightString(w - 15*mm, h - 15*mm, str(e["numero"] or ""))

    y = h - 45*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(15*mm, y, "INFORMATIONS")
    y -= 8*mm
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, y, "Bail : " + str(e["bail_numero"] or "—"))
    y -= 5*mm
    c.drawString(15*mm, y, "Bien : " + str(e["bien_titre"] or "—"))
    y -= 5*mm
    c.drawString(15*mm, y, "Adresse : " + str(e["bien_adresse"] or "—") + ", " + str(e["quartier"] or ""))
    y -= 5*mm
    c.drawString(15*mm, y, "Locataire : " + str(e["locataire_prenom"] or "") + " " + str(e["locataire_nom"] or ""))
    y -= 5*mm
    c.drawString(15*mm, y, "Propriétaire : " + str(e["proprietaire_prenom"] or "") + " " + str(e["proprietaire_nom"] or ""))
    y -= 5*mm
    c.drawString(15*mm, y, "Date : " + str((e["date_etat"] or "")[:10]))
    y -= 5*mm
    c.drawString(15*mm, y, "État général : " + str(e["etat_general"] or ""))

    if e['observations']:
        y -= 10*mm
        c.setFont('Helvetica-Bold', 11)
        c.drawString(15*mm, y, "OBSERVATIONS")
        y -= 6*mm
        c.setFont('Helvetica', 9)
        txt = e['observations']
        for i in range(0, len(txt), 90):
            c.drawString(15*mm, y, txt[i:i+90])
            y -= 4.5*mm

    y -= 15*mm
    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica', 9)
    c.drawString(15*mm, y, "Signatures :")
    y -= 6*mm
    c.setFillColor(colors.black)
    c.drawString(15*mm, y, "Propriétaire : " + ("✅ Signé" if e["signe_proprietaire"] else "____________"))
    c.drawString(110*mm, y, "Locataire : " + ("✅ Signé" if e["signe_locataire"] else "____________"))

    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica', 7)
    c.drawString(15*mm, 10*mm, "OMEGA Immobilier · Dakar, Sénégal")

    c.showPage()
    c.save()
    buf.seek(0)

    log_action(current_user.id, 'PDF_ETAT_LIEUX', str(e["numero"]), 'etats_lieux', eid)
    return send_file(buf, mimetype='application/pdf',
                     download_name='etat_lieux_' + str(e["numero"]) + '.pdf')


# ═══════════════════════════════════════════════════════════════
# 📊 COMMISSIONS
# ═══════════════════════════════════════════════════════════════

@app.route('/commissions')
@login_required
def commissions_liste():
    db = get_db()
    cur = db.cursor()
    statut_f = request.args.get('statut', '')

    sql = """
        SELECT c.*, bi.titre AS bien_titre, b.numero AS bail_numero
        FROM commissions c
        LEFT JOIN baux b ON b.id=c.bail_id
        LEFT JOIN biens bi ON bi.id=c.bien_id
        WHERE 1=1
    """
    params = []
    if statut_f:
        sql += " AND c.statut=?"
        params.append(statut_f)
    sql += " ORDER BY c.id DESC LIMIT 200"
    cur.execute(sql, params)
    commissions = cur.fetchall()

    stats = {}
    cur.execute("SELECT COALESCE(SUM(montant_commission),0) FROM commissions")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant_commission),0) FROM commissions WHERE statut='a_payer'")
    stats['a_payer'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant_commission),0) FROM commissions WHERE statut='payee'")
    stats['payees'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM commissions WHERE statut='a_payer'")
    stats['nb'] = cur.fetchone()[0]

    rows = ''
    for c in commissions:
        statut_badge = 'badge-orange' if c['statut'] == 'a_payer' else 'badge-green'
        rows += (
            '<tr><td>' + str(c["mois"]) + '</td>'
            + '<td>' + str(c["bail_numero"] or "—") + '<br><small style="color:#64748b">' + str(c["bien_titre"] or "") + '</small></td>'
            + '<td style="text-align:right">' + f'{c["montant_loyer"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center">' + f'{c["taux_commission"]:.1f}' + '%</td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{c["montant_commission"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></td>'
            + ('<td><a href="/commissions/' + str(c["id"]) + '/payer" class="btn btn-success" style="padding:4px 10px;font-size:11px">✅ Payer</a></td>' if c['statut'] == 'a_payer' else '<td>—</td>')
            + '</tr>'
        )

    content = '<h1>📊 Commissions agence — ' + str(len(commissions)) + '</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-icon">📊</div><div class="kpi-label">Total commissions</div><div class="kpi-value" style="font-size:16px">' + f'{stats["total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">⏳</div><div class="kpi-label">À payer</div><div class="kpi-value" style="font-size:16px">' + f'{stats["a_payer"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Payées</div><div class="kpi-value" style="font-size:16px">' + f'{stats["payees"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">📋</div><div class="kpi-label">Nb à payer</div><div class="kpi-value">' + str(stats["nb"]) + '</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/commissions" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Toutes</a> '
    for s in ['a_payer', 'payee']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/commissions?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Mois</th><th>Bail/Bien</th><th style="text-align:right">Loyer</th><th style="text-align:center">Taux</th><th style="text-align:right">Commission</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucune commission</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='commissions', page_title='Commissions')


@app.route('/commissions/<int:cid>/payer')
@login_required
def commissions_payer(cid):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("UPDATE commissions SET statut='payee', date_paiement=? WHERE id=?",
                    (datetime.now().strftime('%Y-%m-%d'), cid))
        db.commit()
        flash('✅ Commission marquée payée', 'success')
    except Exception as e:
        db.rollback()
        flash('❌ ' + str(e), 'error')
    return redirect('/commissions')


# ═══════════════════════════════════════════════════════════════
# 🔧 RÉCLAMATIONS
# ═══════════════════════════════════════════════════════════════

@app.route('/reclamations')
@login_required
def reclamations_liste():
    db = get_db()
    cur = db.cursor()
    statut_f = request.args.get('statut', '')

    sql = """
        SELECT r.*, b.numero AS bail_numero, bi.titre AS bien_titre, bi.quartier
        FROM reclamations r
        LEFT JOIN baux b ON b.id=r.bail_id
        LEFT JOIN biens bi ON bi.id=r.bien_id
        WHERE 1=1
    """
    params = []
    if statut_f:
        sql += " AND r.statut=?"
        params.append(statut_f)
    sql += " ORDER BY r.id DESC LIMIT 200"
    cur.execute(sql, params)
    reclamations = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM reclamations WHERE statut='ouverte'")
    stats['ouvertes'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM reclamations WHERE statut='en_cours'")
    stats['en_cours'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM reclamations WHERE statut='resolue'")
    stats['resolues'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(cout_intervention),0) FROM reclamations WHERE statut='resolue'")
    stats['cout'] = cur.fetchone()[0]

    rows = ''
    for r in reclamations:
        priorite_badge = {'basse': 'badge-gray', 'normale': 'badge-blue', 'haute': 'badge-orange', 'urgente': 'badge-red'}.get(r['priorite'], 'badge-gray')
        statut_badge = {'ouverte': 'badge-red', 'en_cours': 'badge-orange', 'resolue': 'badge-green'}.get(r['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong>' + str(r["type"] or "—") + '</strong></td>'
            + '<td>' + str(r["titre"] or "—") + '<br><small style="color:#64748b">' + str(r["bien_titre"] or "") + '</small></td>'
            + '<td><span class="badge ' + priorite_badge + '">' + str(r["priorite"]) + '</span></td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(r["statut"]) + '</span></td>'
            + '<td>' + str((r["date_declaration"] or "—")[:10]) + '</td>'
            + '<td><a href="/reclamations/' + str(r["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🔧 Réclamations — ' + str(len(reclamations)) + '</h1>'
    content += '<a href="/reclamations/nouvelle" class="btn btn-primary">+ Nouvelle réclamation</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">🔧</div><div class="kpi-label">Ouvertes</div><div class="kpi-value">' + str(stats["ouvertes"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">⚙️</div><div class="kpi-label">En cours</div><div class="kpi-value">' + str(stats["en_cours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Résolues</div><div class="kpi-value">' + str(stats["resolues"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">💰</div><div class="kpi-label">Coût interventions</div><div class="kpi-value" style="font-size:16px">' + f'{stats["cout"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/reclamations" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Toutes</a> '
    for s in ['ouverte', 'en_cours', 'resolue']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/reclamations?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Type</th><th>Titre / Bien</th><th>Priorité</th><th>Statut</th><th>Date</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="6" style="padding:40px;text-align:center;color:#10b981">✅ Aucune réclamation</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='reclamations', page_title='Réclamations')


@app.route('/reclamations/nouvelle', methods=['GET', 'POST'])
@login_required
def reclamations_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            bail_id = int(request.form.get('bail_id') or 0)
            cur.execute("SELECT bien_id FROM baux WHERE id=?", (bail_id,))
            b = cur.fetchone()
            bien_id = b['bien_id'] if b else None

            cur.execute("""
                INSERT INTO reclamations (bail_id, bien_id, type, titre, description,
                                            priorite, statut, date_declaration, created_at)
                VALUES (?,?,?,?,?,?, 'ouverte', ?, ?)
            """, (bail_id, bien_id,
                  request.form.get('type'),
                  request.form.get('titre'),
                  request.form.get('description'),
                  request.form.get('priorite') or 'normale',
                  datetime.now().strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Réclamation créée', 'success')
            return redirect('/reclamations')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("""
        SELECT b.id, b.numero, bi.titre AS bien_titre
        FROM baux b
        LEFT JOIN biens bi ON bi.id=b.bien_id
        WHERE b.statut='actif'
        ORDER BY b.id DESC
    """)
    baux = cur.fetchall()
    opts = ''.join('<option value="' + str(b["id"]) + '">' + str(b["numero"]) + ' — ' + str(b["bien_titre"] or "") + '</option>' for b in baux)

    content = '<h1>🔧 Nouvelle réclamation</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="margin-bottom:16px"><label>Bail *</label><select name="bail_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts + '</select></div>'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Type *</label><select name="type" required>'
    content += '<option value="Plomberie">🚿 Plomberie</option>'
    content += '<option value="Électricité">⚡ Électricité</option>'
    content += '<option value="Climatisation">❄️ Climatisation</option>'
    content += '<option value="Peinture">🎨 Peinture</option>'
    content += '<option value="Serrurerie">🔑 Serrurerie</option>'
    content += '<option value="Toiture">🏠 Toiture</option>'
    content += '<option value="Autre">📋 Autre</option>'
    content += '</select></div>'
    content += '<div><label>Priorité</label><select name="priorite">'
    content += '<option value="basse">🟢 Basse</option>'
    content += '<option value="normale" selected>🔵 Normale</option>'
    content += '<option value="haute">🟠 Haute</option>'
    content += '<option value="urgente">🔴 Urgente</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Titre *</label><input type="text" name="titre" required placeholder="Fuite d\'eau cuisine"></div>'
    content += '<div style="grid-column:1/-1"><label>Description</label><textarea name="description" rows="4"></textarea></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/reclamations" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='reclamations', page_title='Nouvelle réclamation')


@app.route('/reclamations/<int:rid>', methods=['GET', 'POST'])
@login_required
def reclamations_detail(rid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT r.*, b.numero AS bail_numero, bi.titre AS bien_titre, bi.quartier,
               lo.nom AS locataire_nom, lo.prenom AS locataire_prenom, lo.telephone AS locataire_tel
        FROM reclamations r
        LEFT JOIN baux b ON b.id=r.bail_id
        LEFT JOIN biens bi ON bi.id=r.bien_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        WHERE r.id=?
    """, (rid,))
    r = cur.fetchone()
    if not r:
        flash('❌ Réclamation introuvable', 'error')
        return redirect('/reclamations')

    if request.method == 'POST':
        try:
            new_statut = request.form.get('statut') or r['statut']
            cout = float(request.form.get('cout_intervention') or 0)
            date_resolution = datetime.now().strftime('%Y-%m-%d') if new_statut == 'resolue' else r['date_resolution']

            cur.execute("""
                UPDATE reclamations SET statut=?, cout_intervention=?, date_resolution=?, responsable=?
                WHERE id=?
            """, (new_statut, cout, date_resolution, current_user.nom_complet, rid))
            db.commit()
            flash('✅ Réclamation mise à jour', 'success')
            return redirect('/reclamations/' + str(rid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    priorite_badge = {'basse': 'badge-gray', 'normale': 'badge-blue', 'haute': 'badge-orange', 'urgente': 'badge-red'}.get(r['priorite'], 'badge-gray')
    statut_badge = {'ouverte': 'badge-red', 'en_cours': 'badge-orange', 'resolue': 'badge-green'}.get(r['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🔧 Réclamation <span class="badge ' + statut_badge + '">' + str(r["statut"]) + '</span></h1>'
    content += '<a href="/reclamations" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-label">Type</div><div class="kpi-value" style="font-size:16px">' + str(r["type"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Priorité</div><div class="kpi-value" style="font-size:16px">' + str(r["priorite"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Coût</div><div class="kpi-value" style="font-size:16px">' + f'{r["cout_intervention"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations</h2><table>'
    content += '<tr><td><strong>Titre</strong></td><td>' + str(r["titre"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Bien</strong></td><td>' + str(r["bien_titre"] or "—") + ' — ' + str(r["quartier"] or "") + '</td></tr>'
    content += '<tr><td><strong>Locataire</strong></td><td>' + str(r["locataire_prenom"] or "") + ' ' + str(r["locataire_nom"] or "") + ' — ' + str(r["locataire_tel"] or "") + '</td></tr>'
    content += '<tr><td><strong>Description</strong></td><td>' + str(r["description"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Date déclaration</strong></td><td>' + str((r["date_declaration"] or "—")[:10]) + '</td></tr>'
    if r['date_resolution']:
        content += '<tr><td><strong>Date résolution</strong></td><td>' + str(r["date_resolution"][:10]) + '</td></tr>'
    if r['responsable']:
        content += '<tr><td><strong>Responsable</strong></td><td>' + str(r["responsable"]) + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>✏️ Mettre à jour</h2>'
    content += '<form method="post">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Statut</label><select name="statut">'
    for st, lb in [('ouverte', '🔴 Ouverte'), ('en_cours', '🟠 En cours'), ('resolue', '✅ Résolue')]:
        sel = ' selected' if r['statut'] == st else ''
        content += '<option value="' + st + '"' + sel + '>' + lb + '</option>'
    content += '</select></div>'
    content += '<div><label>Coût intervention (FCFA)</label><input type="number" step="1000" name="cout_intervention" value="' + f'{r["cout_intervention"]:.0f}' + '"></div>'
    content += '</div>'
    content += '<div style="margin-top:16px"><button type="submit" class="btn btn-success">💾 Enregistrer</button></div>'
    content += '</form></div>'

    return render_page(content, active='reclamations', page_title='Réclamation')


# ═══════════════════════════════════════════════════════════════
# 📈 MARCHÉ / ÉVALUATION
# ═══════════════════════════════════════════════════════════════

@app.route('/marche')
@login_required
def marche_index():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT * FROM evaluations_marche
        ORDER BY ville, quartier, type_bien
    """)
    evaluations = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM evaluations_marche")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT quartier) FROM evaluations_marche")
    stats['quartiers'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(loyer_moyen),0) FROM evaluations_marche")
    stats['moyenne'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM evaluations_marche WHERE tendance='hausse'")
    stats['hausse'] = cur.fetchone()[0]

    rows = ''
    for e in evaluations:
        icon = {'villa': '🏡', 'appartement': '🏢', 'studio': '🏠', 'chambre': '🚪', 'bureau': '🏢'}.get(e['type_bien'], '🏠')
        tendance_badge = {'hausse': 'badge-red', 'stable': 'badge-blue', 'baisse': 'badge-green'}.get(e['tendance'], 'badge-gray')
        tendance_arrow = {'hausse': '📈', 'stable': '➡️', 'baisse': '📉'}.get(e['tendance'], '—')
        rows += (
            '<tr><td>' + str(e["quartier"]) + '</td>'
            + '<td>' + str(e["ville"]) + '</td>'
            + '<td>' + icon + ' ' + str(e["type_bien"]).capitalize() + ' · ' + str(e["nb_pieces"]) + 'p</td>'
            + '<td style="text-align:right;font-weight:800;color:#1e40af">' + f'{e["loyer_moyen"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center">' + str(e["nb_observations"]) + '</td>'
            + '<td><span class="badge ' + tendance_badge + '">' + tendance_arrow + ' ' + str(e["tendance"]) + '</span></td></tr>'
        )

    content = '<h1>📈 Marché immobilier — Cote & tendances</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-icon">📈</div><div class="kpi-label">Références</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🗺️</div><div class="kpi-label">Quartiers</div><div class="kpi-value">' + str(stats["quartiers"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">💰</div><div class="kpi-label">Loyer moyen</div><div class="kpi-value" style="font-size:16px">' + f'{stats["moyenne"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">📈</div><div class="kpi-label">En hausse</div><div class="kpi-value">' + str(stats["hausse"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Quartier</th><th>Ville</th><th>Type</th><th style="text-align:right">Loyer moyen</th><th style="text-align:center">Observations</th><th>Tendance</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="6" style="padding:40px;text-align:center;color:#94a3b8">Aucune donnée</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='marche', page_title='Marché')


# ═══════════════════════════════════════════════════════════════
# 📱 MOBILE LOCATAIRE
# ═══════════════════════════════════════════════════════════════

@app.route('/mobile-locataire')
@login_required
def mobile_locataire():
    db = get_db()
    cur = db.cursor()

    def sc(sql, default=0):
        cur.execute(sql)
        r = cur.fetchone()
        return r[0] if r and r[0] is not None else default

    stats = {
        'loyers_mois': sc("SELECT COUNT(*) FROM loyers WHERE periode=strftime('%Y-%m','now')"),
        'impayes': sc("SELECT COALESCE(SUM(total_du - montant_paye),0) FROM loyers WHERE statut != 'paye'"),
        'reclamations': sc("SELECT COUNT(*) FROM reclamations WHERE statut='ouverte'"),
        'quittances': sc("SELECT COUNT(*) FROM quittances WHERE strftime('%Y-%m',date_emission)=strftime('%Y-%m','now')"),
    }

    content = '<h1>📱 Mobile Locataire</h1>'
    content += '<div style="background:#eff6ff;border-left:4px solid #1e40af;padding:14px;border-radius:8px;margin-bottom:20px;font-size:13px;color:#1e40af">'
    content += '💡 Interface mobile pour locataires — paiement, quittances, réclamations'
    content += '</div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)"><div class="kpi-label">Loyers du mois</div><div class="kpi-value">' + str(stats["loyers_mois"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-label">Impayés total</div><div class="kpi-value" style="font-size:16px">' + f'{stats["impayes"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Réclamations</div><div class="kpi-value">' + str(stats["reclamations"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Quittances mois</div><div class="kpi-value">' + str(stats["quittances"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>⚡ Actions rapides</h2>'
    content += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:12px">'
    actions = [
        ('/loyers', '💰 Payer mon loyer', '#1e40af'),
        ('/quittances', '📜 Mes quittances', '#10b981'),
        ('/reclamations/nouvelle', '🔧 Déclarer un problème', '#ef4444'),
        ('/marche', '📈 Prix du marché', '#8b5cf6'),
    ]
    for url, label, color in actions:
        content += '<a href="' + url + '" style="text-decoration:none"><div style="background:' + color + ';color:#fff;padding:20px;border-radius:10px;text-align:center;font-weight:700;font-size:13px">' + label + '</div></a>'
    content += '</div></div>'

    content += '<div class="card"><h2>💰 Mes prochains loyers</h2>'
    cur.execute("""
        SELECT l.*, bi.titre AS bien_titre, bi.quartier
        FROM loyers l
        LEFT JOIN baux b ON b.id=l.bail_id
        LEFT JOIN biens bi ON bi.id=b.bien_id
        WHERE l.statut != 'paye'
        ORDER BY l.date_echeance ASC LIMIT 6
    """)
    loyers = cur.fetchall()
    rows = ''
    for l in loyers:
        reste = (l['total_du'] or 0) - (l['montant_paye'] or 0)
        rows += (
            '<tr><td><strong>' + str(l["periode"]) + '</strong></td>'
            + '<td>' + str(l["bien_titre"] or "—") + '</td>'
            + '<td style="text-align:right;color:#ef4444;font-weight:800">' + f'{reste:,.0f}' + ' F</td>'
            + '<td>' + str((l["date_echeance"] or "—")[:10]) + '</td></tr>'
        )
    content += '<table><thead><tr><th>Période</th><th>Bien</th><th style="text-align:right">Reste à payer</th><th>Échéance</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="4" style="text-align:center;color:#10b981;padding:20px">✅ Aucun loyer impayé</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='dashboard', page_title='Mobile Locataire')


# ═══════════════════════════════════════════════════════════════
# 📊 API JSON
# ═══════════════════════════════════════════════════════════════

@app.route('/api/immobilier/stats')
@login_required
def api_immobilier_stats():
    db = get_db()
    cur = db.cursor()
    result = {}
    for k, sql in [
        ('biens_total', "SELECT COUNT(*) FROM biens"),
        ('biens_dispo', "SELECT COUNT(*) FROM biens WHERE statut='disponible'"),
        ('biens_loues', "SELECT COUNT(*) FROM biens WHERE statut='loue'"),
        ('baux_actifs', "SELECT COUNT(*) FROM baux WHERE statut='actif'"),
        ('locataires', "SELECT COUNT(*) FROM locataires WHERE statut='actif'"),
        ('loyers_mois', "SELECT COALESCE(SUM(total_du),0) FROM loyers WHERE periode=strftime('%Y-%m','now')"),
        ('impayes', "SELECT COALESCE(SUM(montant_impaye),0) FROM impayes WHERE statut='ouvert'"),
    ]:
        try:
            cur.execute(sql)
            r = cur.fetchone()
            result[k] = r[0] if r else 0
        except Exception:
            result[k] = 0
    return jsonify(result)


@app.route('/api/quittances/verifier/<numero>')
def api_verifier_quittance(numero):
    """Endpoint public de vérification d'une quittance via QR."""
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT q.numero, q.date_emission, q.montant_recu, q.mode_paiement, q.statut,
               b.numero AS bail_numero, l.periode,
               lo.prenom, lo.nom, bi.titre AS bien_titre
        FROM quittances q
        LEFT JOIN baux b ON b.id=q.bail_id
        LEFT JOIN loyers l ON l.id=q.loyer_id
        LEFT JOIN locataires lo ON lo.id=b.locataire_id
        LEFT JOIN biens bi ON bi.id=b.bien_id
        WHERE q.numero=?
    """, (numero,))
    q = cur.fetchone()
    if not q:
        return jsonify({'valide': False, 'error': 'Quittance introuvable'}), 404
    return jsonify({
        'valide': q['statut'] == 'valide',
        'numero': q['numero'],
        'locataire': (q['prenom'] or '') + ' ' + (q['nom'] or ''),
        'bien': q['bien_titre'],
        'periode': q['periode'],
        'montant_recu': q['montant_recu'],
        'mode_paiement': q['mode_paiement'],
        'date_emission': q['date_emission'],
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
