"""
🏥 OMEGA Assurance Santé — Application principale
Membres · Cotisations · Prestataires · Prestations · Sinistres · Prévention
"""
from flask import Flask, render_template_string, redirect, url_for, session, request, jsonify, Response, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import sqlite3
import os
import io

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'omega-assurance-secret-2026')

DB_PATH = '/app/data/assurance.db'

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
# LAYOUT — DESIGN SANTÉ
# ═══════════════════════════════════════════════════════════════

LAYOUT = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — OMEGA Assurance Santé</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,-apple-system,sans-serif}}
body{{background:#f0f9ff;color:#1e293b;font-size:14px}}
.nav{{background:linear-gradient(135deg,#0891b2,#0e7490);color:#fff;padding:0 22px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 3px 12px rgba(0,0,0,.15);flex-wrap:wrap;border-bottom:4px solid #dc2626}}
.nav-brand{{font-weight:900;font-size:18px;display:flex;align-items:center;gap:12px;padding:16px 0;letter-spacing:-0.3px}}
.nav-brand-icon{{width:40px;height:40px;background:#dc2626;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(220,38,38,.4)}}
.nav-links{{display:flex;gap:2px;flex-wrap:wrap}}
.nav-links a{{color:#cffafe;text-decoration:none;padding:8px 13px;border-radius:8px;font-size:12.5px;font-weight:600;transition:.2s;display:flex;align-items:center;gap:6px}}
.nav-links a:hover{{background:rgba(255,255,255,.15);color:#fff}}
.nav-links a.active{{background:#dc2626;color:#fff;box-shadow:0 4px 10px rgba(220,38,38,.4)}}
.nav-user{{font-size:12.5px;display:flex;gap:10px;align-items:center;color:#cffafe}}
.nav-user a{{color:#fff;text-decoration:none;background:rgba(0,0,0,.25);padding:7px 14px;border-radius:8px;font-weight:600}}
.container{{max-width:1600px;margin:0 auto;padding:24px}}
h1{{color:#0e7490;margin-bottom:20px;font-size:24px;font-weight:800;letter-spacing:-0.4px}}
h1::before{{content:'🏥';margin-right:10px}}
h2{{color:#0891b2;font-size:18px;margin-bottom:14px;font-weight:700}}
.card{{background:#fff;padding:22px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:18px;border-left:4px solid #0891b2}}
table{{width:100%;border-collapse:collapse}}
thead{{background:#0e7490;color:#fff}}
th{{padding:12px;text-align:left;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}}
td{{padding:11px;border-bottom:1px solid #f1f5f9;font-size:13.5px}}
tbody tr:hover{{background:#ecfeff}}
.btn{{display:inline-block;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px;border:none;cursor:pointer;transition:.15s;letter-spacing:.2px}}
.btn:hover{{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.15)}}
.btn-primary{{background:#0891b2;color:#fff}}
.btn-success{{background:#10b981;color:#fff}}
.btn-danger{{background:#dc2626;color:#fff}}
.btn-warning{{background:#f59e0b;color:#fff}}
.btn-secondary{{background:#64748b;color:#fff}}
input,select,textarea{{width:100%;padding:11px 14px;border:2px solid #e2e8f0;border-radius:8px;font-size:13.5px;font-family:inherit;transition:.2s}}
input:focus,select:focus,textarea:focus{{outline:none;border-color:#0891b2;box-shadow:0 0 0 3px rgba(8,145,178,.1)}}
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
.badge-blue{{background:#cffafe;color:#0e7490}}
.badge-green{{background:#d1fae5;color:#047857}}
.badge-orange{{background:#fed7aa;color:#c2410c}}
.badge-red{{background:#fee2e2;color:#b91c1c}}
.badge-gray{{background:#e2e8f0;color:#475569}}
.med-cross{{display:inline-block;color:#dc2626;font-weight:900;font-size:20px;margin-right:6px}}
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-brand">
    <div class="nav-brand-icon">🏥</div>
    <div>OMEGA ASSURANCE<span style="display:block;font-size:10px;font-weight:500;letter-spacing:2px;color:#cffafe">SANTÉ · MUTUELLE · SÉNÉGAL</span></div>
  </div>
  <div class="nav-links">
    <a href="/" class="{a_dash}">📊 Dashboard</a>
    <a href="/membres" class="{a_membres}">👥 Membres</a>
    <a href="/groupes" class="{a_groupes}">🤝 Groupes</a>
    <a href="/formules" class="{a_formules}">📋 Formules</a>
    <a href="/cotisations" class="{a_cotis}">💰 Cotisations</a>
    <a href="/prestataires" class="{a_prest}">🏥 Prestataires</a>
    <a href="/prestations" class="{a_prestt}">💉 Prestations</a>
    <a href="/sinistres" class="{a_sin}">📝 Sinistres</a>
    <a href="/prevention" class="{a_prev}">🩺 Prévention</a>
    <a href="/analytics" class="{a_ana}">📈 Analytics</a>
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


def render_page(content, active='dashboard', page_title='Assurance'):
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
        a_membres='active' if active == 'membres' else '',
        a_groupes='active' if active == 'groupes' else '',
        a_formules='active' if active == 'formules' else '',
        a_cotis='active' if active == 'cotisations' else '',
        a_prest='active' if active == 'prestataires' else '',
        a_prestt='active' if active == 'prestations' else '',
        a_sin='active' if active == 'sinistres' else '',
        a_prev='active' if active == 'prevention' else '',
        a_ana='active' if active == 'analytics' else '',
    )


@app.route('/health')
def health():
    return {'project': 'OMEGA ASSURANCE SANTE', 'service': 'assurance-maladie',
            'status': 'ok', 'timestamp': datetime.now().isoformat(), 'version': '1.0'}


LOGIN_HTML = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Connexion — OMEGA Assurance Santé</title>
<style>body{{font-family:system-ui;background:linear-gradient(135deg,#0891b2,#0e7490);min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0}}
.box{{background:#fff;padding:42px;border-radius:16px;box-shadow:0 25px 70px rgba(0,0,0,.4);width:100%;max-width:420px;border-top:5px solid #dc2626}}
.logo{{text-align:center;font-size:56px;margin-bottom:12px}}
h1{{color:#0e7490;margin:0 0 6px;text-align:center;font-size:22px;font-weight:900;letter-spacing:-0.3px}}
.subtitle{{text-align:center;color:#64748b;font-size:12px;margin-bottom:24px;letter-spacing:1.5px;text-transform:uppercase;font-weight:600}}
input{{width:100%;padding:14px;border:2px solid #e2e8f0;border-radius:10px;margin-bottom:14px;font-size:15px;box-sizing:border-box}}
input:focus{{outline:none;border-color:#0891b2;box-shadow:0 0 0 3px rgba(8,145,178,.1)}}
button{{width:100%;background:#dc2626;color:#fff;padding:15px;border:none;border-radius:10px;font-weight:800;font-size:15px;cursor:pointer;letter-spacing:.5px;text-transform:uppercase}}
button:hover{{background:#b91c1c}}
.err{{background:#fee2e2;color:#991b1b;padding:11px;border-radius:8px;margin-bottom:14px;font-size:13px;border-left:4px solid #dc2626}}
.hint{{margin-top:20px;padding:12px;background:#ecfeff;border-radius:8px;font-size:12px;color:#0e7490;text-align:center;border:1px dashed #67e8f9}}</style></head>
<body><div class="box">
<div class="logo">🏥</div>
<h1>OMEGA ASSURANCE SANTÉ</h1>
<div class="subtitle">Mutuelle · Couverture Maladie Universelle</div>
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
        'membres': sc("SELECT COUNT(*) FROM membres WHERE statut='actif'"),
        'groupes': sc("SELECT COUNT(*) FROM groupes WHERE statut='actif'"),
        'cotisations': sc("SELECT COUNT(*) FROM cotisations WHERE statut='payee'"),
        'montant_cotis': sc("SELECT COALESCE(SUM(montant),0) FROM cotisations WHERE statut='payee'"),
        'sinistres': sc("SELECT COUNT(*) FROM sinistres"),
        'montant_rembourse': sc("SELECT COALESCE(SUM(montant_rembourse),0) FROM sinistres WHERE statut='rembourse'"),
        'sinistres_attente': sc("SELECT COUNT(*) FROM sinistres WHERE statut='declare'"),
        'prestataires': sc("SELECT COUNT(*) FROM prestataires WHERE statut='actif'"),
        'preventions': sc("SELECT COUNT(*) FROM actions_prevention WHERE statut='planifiee'"),
    }

    # Taux de sinistralité (remboursements / cotisations)
    taux_sinistralite = (stats['montant_rembourse'] / stats['montant_cotis'] * 100) if stats['montant_cotis'] > 0 else 0

    # Sinistres récents
    cur.execute("""
        SELECT s.*, m.nom AS membre_nom, m.prenom AS membre_prenom, m.numero_adherent,
               p.nom AS prestation_nom
        FROM sinistres s
        LEFT JOIN membres m ON m.id=s.membre_id
        LEFT JOIN prestations p ON p.id=s.prestation_id
        ORDER BY s.id DESC LIMIT 6
    """)
    sinistres = cur.fetchall()

    sin_html = ''
    for s in sinistres:
        statut_badge = {
            'declare': 'badge-orange',
            'en_cours': 'badge-blue',
            'rembourse': 'badge-green',
            'rejete': 'badge-red',
        }.get(s['statut'], 'badge-gray')
        sin_html += (
            '<tr><td><strong>' + str(s["numero_sinistre"]) + '</strong></td>'
            + '<td>' + str(s["membre_prenom"] or "") + ' ' + str(s["membre_nom"] or "") + '<br><small style="color:#64748b">' + str(s["numero_adherent"] or "") + '</small></td>'
            + '<td>' + str(s["prestation_nom"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{s["montant_facture"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:700">' + f'{s["montant_rembourse"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(s["statut"]) + '</span></td></tr>'
        )

    # Dernières cotisations
    cur.execute("""
        SELECT c.*, m.nom, m.prenom, m.numero_adherent
        FROM cotisations c
        LEFT JOIN membres m ON m.id=c.membre_id
        ORDER BY c.id DESC LIMIT 6
    """)
    cotis = cur.fetchall()

    cot_html = ''
    for c in cotis:
        cot_html += (
            '<tr><td><strong>' + str(c["numero_recu"]) + '</strong></td>'
            + '<td>' + str(c["prenom"] or "") + ' ' + str(c["nom"] or "") + '</td>'
            + '<td>' + str(c["periode"] or "—") + '</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:800">' + f'{c["montant"]:,.0f}' + ' F</td>'
            + '<td>' + str(c["mode_paiement"] or "—") + '</td>'
            + '<td>' + str((c["date_paiement"] or "")[:10]) + '</td></tr>'
        )

    # Top formules
    cur.execute("""
        SELECT f.nom, f.cotisation_mensuelle, COUNT(a.id) AS nb_adhesions
        FROM formules f
        LEFT JOIN adhesions a ON a.formule_id=f.id
        GROUP BY f.id
        ORDER BY nb_adhesions DESC
    """)
    formules = cur.fetchall()
    form_html = ''.join(
        '<tr><td>' + str(f["nom"]) + '</td>'
        + '<td style="text-align:right">' + f'{f["cotisation_mensuelle"]:,.0f}' + ' F/mois</td>'
        + '<td style="text-align:center">' + str(f["nb_adhesions"]) + '</td></tr>'
        for f in formules
    )

    content = '<h1>Tableau de bord Assurance Santé</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">👥</div><div class="kpi-label">Adhérents actifs</div><div class="kpi-value">' + str(stats["membres"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">Cotisations</div><div class="kpi-value" style="font-size:18px">' + f'{stats["montant_cotis"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">📝</div><div class="kpi-label">Sinistres</div><div class="kpi-value">' + str(stats["sinistres"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">💸</div><div class="kpi-label">Remboursements</div><div class="kpi-value" style="font-size:18px">' + f'{stats["montant_rembourse"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">⏳</div><div class="kpi-label">Sinistres à traiter</div><div class="kpi-value">' + str(stats["sinistres_attente"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🤝</div><div class="kpi-label">Groupes</div><div class="kpi-value">' + str(stats["groupes"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-icon">🏥</div><div class="kpi-label">Prestataires</div><div class="kpi-value">' + str(stats["prestataires"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div class="kpi-icon">📊</div><div class="kpi-label">Taux sinistralité</div><div class="kpi-value">' + f'{taux_sinistralite:.1f}' + '%</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:18px">'
    content += '<div class="card"><h2>📝 Sinistres récents</h2>'
    content += '<table><thead><tr><th>N°</th><th>Adhérent</th><th>Prestation</th><th style="text-align:right">Facturé</th><th style="text-align:right">Remboursé</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (sin_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:30px">Aucun sinistre</td></tr>') + '</tbody></table></div>'

    content += '<div class="card" style="border-left-color:#dc2626"><h2>🩺 Prévention</h2>'
    content += '<div style="background:#fef2f2;padding:14px;border-radius:8px;margin-bottom:12px">'
    content += '<div style="font-size:12.5px;color:#991b1b;font-weight:700">Actions planifiées</div>'
    content += '<div style="font-size:32px;font-weight:900;color:#dc2626">' + str(stats["preventions"]) + '</div>'
    content += '</div>'
    content += '<a href="/prevention" class="btn btn-danger" style="width:100%;text-align:center;display:block">Voir les actions</a>'
    content += '</div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>💰 Cotisations récentes</h2>'
    content += '<table><thead><tr><th>N° Reçu</th><th>Membre</th><th>Période</th><th style="text-align:right">Montant</th><th>Mode</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (cot_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:30px">Aucune cotisation</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>📋 Formules souscrites</h2>'
    content += '<table><thead><tr><th>Formule</th><th style="text-align:right">Cotisation</th><th style="text-align:center">Adhésions</th></tr></thead>'
    content += '<tbody>' + (form_html or '<tr><td colspan="3" style="text-align:center;color:#94a3b8;padding:30px">Aucune formule</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    return render_page(content, active='dashboard', page_title='Dashboard')


# ═══════════════════════════════════════════════════════════════
# 👥 MEMBRES / ADHÉRENTS
# ═══════════════════════════════════════════════════════════════

@app.route('/membres')
@login_required
def membres_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()
    statut_f = request.args.get('statut', '')

    sql = """
        SELECT m.*, g.nom AS groupe_nom,
               (SELECT f.nom FROM adhesions a
                LEFT JOIN formules f ON f.id=a.formule_id
                WHERE a.membre_id=m.id AND a.statut='actif'
                ORDER BY a.id DESC LIMIT 1) AS formule_nom
        FROM membres m
        LEFT JOIN groupes g ON g.id=m.groupe_id
        WHERE 1=1
    """
    params = []
    if q:
        sql += " AND (m.nom LIKE ? OR m.prenom LIKE ? OR m.numero_adherent LIKE ? OR m.telephone LIKE ?)"
        params += [f'%{q}%'] * 4
    if statut_f:
        sql += " AND m.statut=?"
        params.append(statut_f)
    sql += " ORDER BY m.id DESC LIMIT 200"
    cur.execute(sql, params)
    membres = cur.fetchall()

    stats = {}
    for k, s in [
        ('total', "SELECT COUNT(*) FROM membres"),
        ('actifs', "SELECT COUNT(*) FROM membres WHERE statut='actif'"),
        ('famille', "SELECT COUNT(*) FROM membres WHERE type_membre='familial'"),
        ('groupe', "SELECT COUNT(*) FROM membres WHERE type_membre='groupe'"),
    ]:
        cur.execute(s)
        stats[k] = cur.fetchone()[0]

    rows = ''
    for m in membres:
        statut_badge = {
            'actif': 'badge-green',
            'suspendu': 'badge-orange',
            'radie': 'badge-red',
        }.get(m['statut'], 'badge-gray')
        age = 0
        if m['date_naissance']:
            try:
                dn = datetime.strptime(m['date_naissance'][:10], '%Y-%m-%d')
                age = (datetime.now() - dn).days // 365
            except Exception:
                age = 0
        sexe_icon = '👨' if m['sexe'] == 'M' else '👩' if m['sexe'] == 'F' else '👤'
        rows += (
            '<tr><td><strong style="color:#0891b2">' + str(m["numero_adherent"] or "—") + '</strong></td>'
            + '<td>' + sexe_icon + ' <strong>' + str(m["prenom"] or "") + ' ' + str(m["nom"] or "") + '</strong><br><small style="color:#64748b">' + str(age) + ' ans · ' + str(m["profession"] or "") + '</small></td>'
            + '<td>' + str(m["telephone"] or "—") + '</td>'
            + '<td>' + str(m["ville"] or "—") + '<br><small style="color:#64748b">' + str(m["region"] or "") + '</small></td>'
            + '<td>' + str(m["formule_nom"] or "—") + '</td>'
            + '<td>' + str(m["groupe_nom"] or "Individuel") + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(m["statut"]) + '</span></td>'
            + '<td><a href="/membres/' + str(m["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a> '
            + '<a href="/membres/' + str(m["id"]) + '/carte" class="btn btn-danger" style="padding:4px 10px;font-size:11px">🎫</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👥 Adhérents — ' + str(len(membres)) + '</h1>'
    content += '<a href="/membres/nouveau" class="btn btn-primary">+ Nouvel adhérent</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">👥</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Actifs</div><div class="kpi-value">' + str(stats["actifs"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">👨‍👩‍👧</div><div class="kpi-label">Familiaux</div><div class="kpi-value">' + str(stats["famille"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🤝</div><div class="kpi-label">Via groupes</div><div class="kpi-value">' + str(stats["groupe"]) + '</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher nom, prénom, n° adhérent, téléphone..." style="max-width:500px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/membres" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Tous</a> '
    for s in ['actif', 'suspendu', 'radie']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/membres?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Adhérent</th><th>Nom complet</th><th>Téléphone</th><th>Localisation</th>'
    content += '<th>Formule</th><th>Groupe</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun adhérent</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='membres', page_title='Adhérents')


@app.route('/membres/nouveau', methods=['GET', 'POST'])
@login_required
def membres_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO membres
                (numero_adherent, nom, prenom, date_naissance, sexe, telephone, telephone_urgence,
                 email, adresse, ville, region, type_membre, groupe_id, statut,
                 date_adhesion, profession, revenu_mensuel, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('prenom'),
                  request.form.get('date_naissance'),
                  request.form.get('sexe'),
                  request.form.get('telephone'),
                  request.form.get('telephone_urgence'),
                  request.form.get('email'),
                  request.form.get('adresse'),
                  request.form.get('ville'),
                  request.form.get('region'),
                  request.form.get('type_membre') or 'individuel',
                  int(request.form.get('groupe_id') or 0) or None,
                  'actif',
                  datetime.now().strftime('%Y-%m-%d'),
                  request.form.get('profession'),
                  float(request.form.get('revenu_mensuel') or 0),
                  datetime.now().isoformat()))
            db.commit()
            log_action(current_user.id, 'CREATE_MEMBRE',
                       f'{request.form.get("prenom")} {request.form.get("nom")}',
                       'membres', cur.lastrowid)
            flash('✅ Adhérent créé — N° ' + str(cur.lastrowid), 'success')
            return redirect('/membres')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom FROM groupes WHERE statut='actif' ORDER BY nom")
    groupes = cur.fetchall()
    opts_grp = ''.join('<option value="' + str(g["id"]) + '">' + str(g["nom"]) + '</option>' for g in groupes)

    content = '<h1>👥 Nouvel adhérent</h1>'
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
    content += '<div><label>Téléphone urgence</label><input type="text" name="telephone_urgence"></div>'
    content += '<div><label>Email</label><input type="email" name="email"></div>'
    content += '<div><label>Profession</label><input type="text" name="profession"></div>'
    content += '<div style="grid-column:1/-1"><label>Adresse</label><input type="text" name="adresse"></div>'
    content += '<div><label>Ville</label><input type="text" name="ville" value="Dakar"></div>'
    content += '<div><label>Région</label><input type="text" name="region" value="Dakar"></div>'
    content += '<div><label>Type de membre</label><select name="type_membre">'
    content += '<option value="individuel">Individuel</option>'
    content += '<option value="familial">Familial</option>'
    content += '<option value="groupe">Via un groupe</option>'
    content += '</select></div>'
    content += '<div><label>Groupe (optionnel)</label><select name="groupe_id"><option value="">— Aucun —</option>' + opts_grp + '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Revenu mensuel estimé (FCFA)</label><input type="number" step="1000" name="revenu_mensuel" value="0"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer l\'adhérent</button>'
    content += '<a href="/membres" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='membres', page_title='Nouvel adhérent')


@app.route('/membres/<int:mid>')
@login_required
def membres_detail(mid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT m.*, g.nom AS groupe_nom
        FROM membres m
        LEFT JOIN groupes g ON g.id=m.groupe_id
        WHERE m.id=?
    """, (mid,))
    m = cur.fetchone()
    if not m:
        flash('❌ Adhérent introuvable', 'error')
        return redirect('/membres')

    # Adhésion active
    cur.execute("""
        SELECT a.*, f.nom AS formule_nom, f.plafond_annuel, f.taux_prise_charge,
               f.couvre_hospitalisation, f.couvre_maternite, f.couvre_pharmacie
        FROM adhesions a
        LEFT JOIN formules f ON f.id=a.formule_id
        WHERE a.membre_id=? AND a.statut='actif'
        ORDER BY a.id DESC LIMIT 1
    """, (mid,))
    adhesion = cur.fetchone()

    # Ayants droit
    cur.execute("SELECT * FROM ayants_droit WHERE membre_id=? ORDER BY id", (mid,))
    ayants = cur.fetchall()
    ayants_html = ''
    for a in ayants:
        age = 0
        if a['date_naissance']:
            try:
                dn = datetime.strptime(a['date_naissance'][:10], '%Y-%m-%d')
                age = (datetime.now() - dn).days // 365
            except Exception:
                age = 0
        ayants_html += (
            '<tr><td><strong>' + str(a["prenom"] or "") + ' ' + str(a["nom"] or "") + '</strong></td>'
            + '<td>' + str(a["lien_parente"] or "—") + '</td>'
            + '<td>' + str(a["date_naissance"] or "—") + ' (' + str(age) + ' ans)</td>'
            + '<td>' + str(a["sexe"] or "—") + '</td>'
            + '<td><span class="badge badge-green">' + str(a["statut"]) + '</span></td></tr>'
        )

    # Cotisations
    cur.execute("SELECT * FROM cotisations WHERE membre_id=? ORDER BY id DESC LIMIT 20", (mid,))
    cotis = cur.fetchall()
    cotis_html = ''
    total_paye = 0
    for c in cotis:
        total_paye += c['montant'] or 0
        cotis_html += (
            '<tr><td><strong>' + str(c["numero_recu"] or "—") + '</strong></td>'
            + '<td>' + str(c["periode"] or "—") + '</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:700">' + f'{c["montant"]:,.0f}' + ' F</td>'
            + '<td>' + str(c["mode_paiement"] or "—") + '</td>'
            + '<td>' + str((c["date_paiement"] or "")[:10]) + '</td>'
            + '<td><span class="badge badge-green">' + str(c["statut"]) + '</span></td></tr>'
        )

    # Sinistres
    cur.execute("""
        SELECT s.*, p.nom AS prestation_nom, pr.nom AS prestataire_nom
        FROM sinistres s
        LEFT JOIN prestations p ON p.id=s.prestation_id
        LEFT JOIN prestataires pr ON pr.id=s.prestataire_id
        WHERE s.membre_id=?
        ORDER BY s.id DESC LIMIT 20
    """, (mid,))
    sinistres = cur.fetchall()
    sin_html = ''
    total_rembourse = 0
    for s in sinistres:
        total_rembourse += s['montant_rembourse'] or 0
        statut_badge = {
            'declare': 'badge-orange', 'en_cours': 'badge-blue',
            'rembourse': 'badge-green', 'rejete': 'badge-red'
        }.get(s['statut'], 'badge-gray')
        sin_html += (
            '<tr><td><strong>' + str(s["numero_sinistre"]) + '</strong></td>'
            + '<td>' + str(s["prestation_nom"] or "—") + '</td>'
            + '<td>' + str(s["prestataire_nom"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{s["montant_facture"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:700">' + f'{s["montant_rembourse"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(s["statut"]) + '</span></td></tr>'
        )

    statut_badge = {'actif': 'badge-green', 'suspendu': 'badge-orange', 'radie': 'badge-red'}.get(m['statut'], 'badge-gray')
    age = 0
    if m['date_naissance']:
        try:
            dn = datetime.strptime(m['date_naissance'][:10], '%Y-%m-%d')
            age = (datetime.now() - dn).days // 365
        except Exception:
            age = 0

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👤 ' + str(m["prenom"] or "") + ' ' + str(m["nom"] or "") + ' <span class="badge ' + statut_badge + '">' + str(m["statut"]) + '</span></h1>'
    content += '<div>'
    content += '<a href="/membres/' + str(mid) + '/carte" class="btn btn-danger">🎫 Carte adhérent</a> '
    content += '<a href="/cotisations/nouvelle?membre_id=' + str(mid) + '" class="btn btn-success">💰 Cotisation</a> '
    content += '<a href="/sinistres/nouveau?membre_id=' + str(mid) + '" class="btn btn-warning">📝 Sinistre</a> '
    content += '<a href="/membres" class="btn btn-secondary">← Retour</a></div></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-label">N° Adhérent</div><div class="kpi-value" style="font-size:16px">' + str(m["numero_adherent"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Âge</div><div class="kpi-value">' + str(age) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Cotisations payées</div><div class="kpi-value" style="font-size:18px">' + f'{total_paye:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-label">Remboursements</div><div class="kpi-value" style="font-size:18px">' + f'{total_rembourse:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>📋 Informations personnelles</h2><table>'
    content += '<tr><td><strong>Sexe</strong></td><td>' + ('Masculin' if m["sexe"] == 'M' else 'Féminin' if m["sexe"] == 'F' else '—') + '</td></tr>'
    content += '<tr><td><strong>Date de naissance</strong></td><td>' + str((m["date_naissance"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Téléphone</strong></td><td>' + str(m["telephone"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Téléphone urgence</strong></td><td>' + str(m["telephone_urgence"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Email</strong></td><td>' + str(m["email"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Profession</strong></td><td>' + str(m["profession"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Adresse</strong></td><td>' + str(m["adresse"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Ville / Région</strong></td><td>' + str(m["ville"] or "—") + ' / ' + str(m["region"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Revenu mensuel</strong></td><td>' + f'{m["revenu_mensuel"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td><strong>Date adhésion</strong></td><td>' + str((m["date_adhesion"] or "—")[:10]) + '</td></tr>'
    if m['groupe_nom']:
        content += '<tr><td><strong>Groupe</strong></td><td>' + str(m["groupe_nom"]) + '</td></tr>'
    content += '</table></div>'

    # Adhésion
    content += '<div class="card" style="border-left-color:#10b981">'
    if adhesion:
        content += '<h2>✅ Formule active</h2>'
        content += '<div style="background:#f0fdf4;padding:14px;border-radius:8px;margin-bottom:14px">'
        content += '<div style="font-size:18px;font-weight:900;color:#047857">' + str(adhesion["formule_nom"]) + '</div>'
        content += '<div style="font-size:13px;color:#475569;margin-top:4px">Cotisation : ' + f'{adhesion["cotisation_mensuelle"]:,.0f}' + ' F/mois</div>'
        content += '<div style="font-size:13px;color:#475569">Plafond annuel : ' + f'{adhesion["plafond_annuel"]:,.0f}' + ' F</div>'
        content += '<div style="font-size:13px;color:#475569">Prise en charge : ' + str(adhesion["taux_prise_charge"]) + '%</div>'
        content += '</div>'
        content += '<table>'
        content += '<tr><td>Date début</td><td>' + str((adhesion["date_debut"] or "—")[:10]) + '</td></tr>'
        content += '<tr><td>Date fin</td><td>' + str((adhesion["date_fin"] or "—")[:10]) + '</td></tr>'
        content += '<tr><td>Hospitalisation</td><td>' + ('✅' if adhesion["couvre_hospitalisation"] else '❌') + '</td></tr>'
        content += '<tr><td>Maternité</td><td>' + ('✅' if adhesion["couvre_maternite"] else '❌') + '</td></tr>'
        content += '<tr><td>Pharmacie</td><td>' + ('✅' if adhesion["couvre_pharmacie"] else '❌') + '</td></tr>'
        content += '</table>'
    else:
        content += '<h2>⚠️ Aucune formule active</h2>'
        content += '<p style="color:#64748b;margin-bottom:14px">Cet adhérent n\'a pas souscrit de formule.</p>'
        content += '<a href="/adhesions/nouvelle?membre_id=' + str(mid) + '" class="btn btn-success">+ Souscrire une formule</a>'
    content += '</div>'
    content += '</div>'

    # Ayants droit
    content += '<div class="card"><h2>👨‍👩‍👧 Ayants droit (' + str(len(ayants)) + ')</h2>'
    content += '<table><thead><tr><th>Nom</th><th>Lien</th><th>Naissance</th><th>Sexe</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (ayants_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucun ayant droit</td></tr>') + '</tbody></table>'
    content += '<div style="margin-top:14px;text-align:right"><a href="/membres/' + str(mid) + '/ayant/nouveau" class="btn btn-primary">+ Ajouter un ayant droit</a></div></div>'

    # Cotisations
    content += '<div class="card"><h2>💰 Historique cotisations (' + str(len(cotis)) + ')</h2>'
    content += '<table><thead><tr><th>N° Reçu</th><th>Période</th><th style="text-align:right">Montant</th><th>Mode</th><th>Date</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (cotis_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:20px">Aucune cotisation</td></tr>') + '</tbody></table></div>'

    # Sinistres
    content += '<div class="card"><h2>📝 Historique sinistres (' + str(len(sinistres)) + ')</h2>'
    content += '<table><thead><tr><th>N°</th><th>Prestation</th><th>Prestataire</th><th style="text-align:right">Facturé</th><th style="text-align:right">Remboursé</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (sin_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:20px">Aucun sinistre</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='membres', page_title='Adhérent')


@app.route('/membres/<int:mid>/ayant/nouveau', methods=['GET', 'POST'])
@login_required
def ayants_nouveau(mid):
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO ayants_droit (membre_id, nom, prenom, date_naissance, sexe,
                                            lien_parente, statut, created_at)
                VALUES (?,?,?,?,?,?, 'actif', ?)
            """, (mid,
                  request.form.get('nom'),
                  request.form.get('prenom'),
                  request.form.get('date_naissance'),
                  request.form.get('sexe'),
                  request.form.get('lien_parente'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Ayant droit ajouté', 'success')
            return redirect('/membres/' + str(mid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>👨‍👩‍👧 Nouvel ayant droit</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Nom *</label><input type="text" name="nom" required autofocus></div>'
    content += '<div><label>Prénom *</label><input type="text" name="prenom" required></div>'
    content += '<div><label>Date de naissance</label><input type="date" name="date_naissance"></div>'
    content += '<div><label>Sexe</label><select name="sexe">'
    content += '<option value="M">Masculin</option>'
    content += '<option value="F">Féminin</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Lien de parenté *</label><select name="lien_parente" required>'
    content += '<option value="Conjoint(e)">Conjoint(e)</option>'
    content += '<option value="Enfant">Enfant</option>'
    content += '<option value="Parent">Parent</option>'
    content += '<option value="Frère/Sœur">Frère/Sœur</option>'
    content += '</select></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Ajouter</button>'
    content += '<a href="/membres/' + str(mid) + '" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='membres', page_title='Ayant droit')


# ═══════════════════════════════════════════════════════════════
# 🤝 GROUPES
# ═══════════════════════════════════════════════════════════════

@app.route('/groupes')
@login_required
def groupes_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT g.*,
               (SELECT COUNT(*) FROM membres WHERE groupe_id=g.id) AS nb_membres_reel,
               (SELECT COALESCE(SUM(montant),0) FROM cotisations c
                JOIN membres m ON m.id=c.membre_id
                WHERE m.groupe_id=g.id AND c.statut='payee') AS total_cotis
        FROM groupes g
        WHERE g.statut='actif'
        ORDER BY g.nom
    """)
    groupes = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM groupes")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(nb_membres),0) FROM groupes")
    stats['membres'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM groupes WHERE type='tontine'")
    stats['tontines'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM groupes WHERE type='cooperative'")
    stats['coop'] = cur.fetchone()[0]

    rows = ''
    for g in groupes:
        rows += (
            '<tr><td><strong style="color:#0891b2">' + str(g["code"] or "—") + '</strong></td>'
            + '<td><strong>' + str(g["nom"]) + '</strong><br><small style="color:#64748b">' + str(g["type"] or "") + '</small></td>'
            + '<td>' + str(g["responsable"] or "—") + '<br><small style="color:#64748b">' + str(g["telephone"] or "") + '</small></td>'
            + '<td>' + str(g["ville"] or "—") + '<br><small style="color:#64748b">' + str(g["region"] or "") + '</small></td>'
            + '<td style="text-align:center">' + str(g["nb_membres_reel"]) + '</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:700">' + f'{g["total_cotis"]:,.0f}' + ' F</td>'
            + '<td><span class="badge badge-green">' + str(g["statut"]) + '</span></td>'
            + '<td><a href="/groupes/' + str(g["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🤝 Groupes & Mutuelles — ' + str(len(groupes)) + '</h1>'
    content += '<a href="/groupes/nouveau" class="btn btn-primary">+ Nouveau groupe</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🤝</div><div class="kpi-label">Total groupes</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">👥</div><div class="kpi-label">Membres cumulés</div><div class="kpi-value">' + str(stats["membres"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">💰</div><div class="kpi-label">Tontines</div><div class="kpi-value">' + str(stats["tontines"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🌾</div><div class="kpi-label">Coopératives</div><div class="kpi-value">' + str(stats["coop"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Nom</th><th>Responsable</th><th>Localisation</th>'
    content += '<th style="text-align:center">Membres</th><th style="text-align:right">Cotisations</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun groupe</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='groupes', page_title='Groupes')


@app.route('/groupes/nouveau', methods=['GET', 'POST'])
@login_required
def groupes_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO groupes (code, nom, type, responsable, telephone, ville, region,
                                       nb_membres, cotisation_mensuelle, statut, created_at)
                VALUES (?,?,?,?,?,?,?,0,?, 'actif', ?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('type'),
                  request.form.get('responsable'),
                  request.form.get('telephone'),
                  request.form.get('ville'),
                  request.form.get('region'),
                  float(request.form.get('cotisation_mensuelle') or 0),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Groupe créé', 'success')
            return redirect('/groupes')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>🤝 Nouveau groupe</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom du groupe *</label>'
    content += '<input type="text" name="nom" required placeholder="Tontine Femmes Médina" autofocus></div>'
    content += '<div><label>Type</label><select name="type">'
    content += '<option value="tontine">💰 Tontine</option>'
    content += '<option value="cooperative">🌾 Coopérative</option>'
    content += '<option value="association">👥 Association</option>'
    content += '<option value="entreprise">🏢 Entreprise</option>'
    content += '<option value="mutuelle">🤝 Mutuelle</option>'
    content += '</select></div>'
    content += '<div><label>Responsable</label><input type="text" name="responsable"></div>'
    content += '<div><label>Téléphone</label><input type="text" name="telephone"></div>'
    content += '<div><label>Cotisation mensuelle (FCFA)</label><input type="number" step="500" name="cotisation_mensuelle" value="5000"></div>'
    content += '<div><label>Ville</label><input type="text" name="ville" value="Dakar"></div>'
    content += '<div><label>Région</label><input type="text" name="region" value="Dakar"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/groupes" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='groupes', page_title='Nouveau groupe')


@app.route('/groupes/<int:gid>')
@login_required
def groupes_detail(gid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM groupes WHERE id=?", (gid,))
    g = cur.fetchone()
    if not g:
        flash('❌ Groupe introuvable', 'error')
        return redirect('/groupes')

    cur.execute("SELECT * FROM membres WHERE groupe_id=? ORDER BY nom, prenom", (gid,))
    membres = cur.fetchall()

    rows = ''
    for m in membres:
        rows += (
            '<tr><td><strong>' + str(m["numero_adherent"] or "—") + '</strong></td>'
            + '<td>' + str(m["prenom"] or "") + ' ' + str(m["nom"] or "") + '</td>'
            + '<td>' + str(m["telephone"] or "—") + '</td>'
            + '<td>' + str((m["date_adhesion"] or "—")[:10]) + '</td>'
            + '<td><a href="/membres/' + str(m["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🤝 ' + str(g["nom"]) + '</h1>'
    content += '<a href="/groupes" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Code</div><div class="kpi-value" style="font-size:16px">' + str(g["code"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-label">Type</div><div class="kpi-value" style="font-size:16px">' + str(g["type"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Membres</div><div class="kpi-value">' + str(len(membres)) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-label">Cotisation</div><div class="kpi-value" style="font-size:18px">' + f'{g["cotisation_mensuelle"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations groupe</h2><table>'
    content += '<tr><td><strong>Responsable</strong></td><td>' + str(g["responsable"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Téléphone</strong></td><td>' + str(g["telephone"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Ville / Région</strong></td><td>' + str(g["ville"] or "—") + ' / ' + str(g["region"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Statut</strong></td><td><span class="badge badge-green">' + str(g["statut"]) + '</span></td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>👥 Membres du groupe (' + str(len(membres)) + ')</h2>'
    content += '<table><thead><tr><th>N° Adhérent</th><th>Nom</th><th>Téléphone</th><th>Adhésion</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucun membre</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='groupes', page_title='Groupe')


# ═══════════════════════════════════════════════════════════════
# 📋 FORMULES
# ═══════════════════════════════════════════════════════════════

@app.route('/formules')
@login_required
def formules_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT f.*,
               (SELECT COUNT(*) FROM adhesions WHERE formule_id=f.id) AS nb_adhesions
        FROM formules f
        WHERE f.statut='actif'
        ORDER BY f.cotisation_mensuelle
    """)
    formules = cur.fetchall()

    cards = ''
    for f in formules:
        cards += '<div class="card" style="border-left-color:#0891b2">'
        cards += '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">'
        cards += '<div><div style="font-size:20px;font-weight:900;color:#0891b2">' + str(f["nom"]) + '</div>'
        cards += '<div style="font-size:13px;color:#64748b;margin-top:4px">' + str(f["description"] or "") + '</div></div>'
        cards += '<div style="text-align:right"><div style="font-size:22px;font-weight:900;color:#10b981">' + f'{f["cotisation_mensuelle"]:,.0f}' + ' F</div><div style="font-size:11px;color:#64748b">par mois</div></div></div>'
        cards += '<table style="margin-top:14px">'
        cards += '<tr><td>Cotisation annuelle</td><td style="text-align:right"><strong>' + f'{f["cotisation_annuelle"]:,.0f}' + ' F</strong></td></tr>'
        cards += '<tr><td>Plafond annuel</td><td style="text-align:right"><strong>' + f'{f["plafond_annuel"]:,.0f}' + ' F</strong></td></tr>'
        cards += '<tr><td>Taux de prise en charge</td><td style="text-align:right"><strong>' + str(f["taux_prise_charge"]) + '%</strong></td></tr>'
        cards += '<tr><td>Ayants droit max</td><td style="text-align:right"><strong>' + str(f["nb_ayants_droit_max"]) + '</strong></td></tr>'
        cards += '<tr><td>Âge maximum</td><td style="text-align:right"><strong>' + str(f["age_max"]) + ' ans</strong></td></tr>'
        cards += '</table>'
        cards += '<div style="margin-top:12px;display:flex;gap:6px;flex-wrap:wrap">'
        cards += ('<span class="badge badge-green">✅ Hospitalisation</span> ' if f["couvre_hospitalisation"] else '<span class="badge badge-gray">❌ Hospitalisation</span> ')
        cards += ('<span class="badge badge-green">✅ Maternité</span> ' if f["couvre_maternite"] else '<span class="badge badge-gray">❌ Maternité</span> ')
        cards += ('<span class="badge badge-green">✅ Pharmacie</span> ' if f["couvre_pharmacie"] else '<span class="badge badge-gray">❌ Pharmacie</span> ')
        cards += ('<span class="badge badge-green">✅ Lunettes</span> ' if f["couvre_lunettes"] else '<span class="badge badge-gray">❌ Lunettes</span> ')
        cards += ('<span class="badge badge-green">✅ Dentaire</span> ' if f["couvre_dentaire"] else '<span class="badge badge-gray">❌ Dentaire</span> ')
        cards += '</div>'
        cards += '<div style="margin-top:14px;padding-top:14px;border-top:1px solid #f1f5f9;font-size:12.5px;color:#64748b">'
        cards += '📊 ' + str(f["nb_adhesions"]) + ' adhérent(s)'
        cards += '</div></div>'

    content = '<h1>📋 Formules d\'assurance — ' + str(len(formules)) + '</h1>'
    content += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:18px">' + cards + '</div>'

    return render_page(content, active='formules', page_title='Formules')


# ═══════════════════════════════════════════════════════════════
# 📝 ADHÉSIONS
# ═══════════════════════════════════════════════════════════════

@app.route('/adhesions/nouvelle', methods=['GET', 'POST'])
@login_required
def adhesions_nouvelle():
    db = get_db()
    cur = db.cursor()
    membre_id = int(request.args.get('membre_id') or 0)

    if request.method == 'POST':
        try:
            membre_id = int(request.form.get('membre_id') or 0)
            formule_id = int(request.form.get('formule_id') or 0)

            cur.execute("SELECT cotisation_mensuelle FROM formules WHERE id=?", (formule_id,))
            f = cur.fetchone()
            cotis = f['cotisation_mensuelle'] if f else 0

            date_debut = request.form.get('date_debut') or datetime.now().strftime('%Y-%m-%d')
            date_fin = request.form.get('date_fin') or (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')

            cur.execute("UPDATE adhesions SET statut='termine' WHERE membre_id=?", (membre_id,))

            cur.execute("""
                INSERT INTO adhesions (membre_id, formule_id, date_debut, date_fin,
                                        cotisation_mensuelle, statut, created_at)
                VALUES (?,?,?,?,?, 'actif', ?)
            """, (membre_id, formule_id, date_debut, date_fin, cotis,
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Adhésion enregistrée', 'success')
            return redirect('/membres/' + str(membre_id))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom, prenom, numero_adherent FROM membres WHERE statut='actif' ORDER BY nom")
    membres = cur.fetchall()
    cur.execute("SELECT id, nom, cotisation_mensuelle FROM formules WHERE statut='actif'")
    formules = cur.fetchall()

    opts_m = ''.join('<option value="' + str(m["id"]) + '"' + (' selected' if m["id"] == membre_id else '') + '>' + str(m["numero_adherent"] or "") + ' — ' + str(m["prenom"] or "") + ' ' + str(m["nom"] or "") + '</option>' for m in membres)
    opts_f = ''.join('<option value="' + str(f["id"]) + '">' + str(f["nom"]) + ' (' + f'{f["cotisation_mensuelle"]:,.0f}' + ' F/mois)</option>' for f in formules)

    content = '<h1>📝 Nouvelle adhésion</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="margin-bottom:16px"><label>Adhérent *</label><select name="membre_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_m + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Formule *</label><select name="formule_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_f + '</select></div>'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Date début</label><input type="date" name="date_debut" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Date fin</label><input type="date" name="date_fin" value="' + (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d') + '"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Enregistrer l\'adhésion</button>'
    content += '<a href="/membres" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='membres', page_title='Adhésion')


# ═══════════════════════════════════════════════════════════════
# 💰 COTISATIONS
# ═══════════════════════════════════════════════════════════════

@app.route('/cotisations')
@login_required
def cotisations_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()
    mode_f = request.args.get('mode', '')

    sql = """
        SELECT c.*, m.nom, m.prenom, m.numero_adherent, m.telephone,
               u.nom_complet AS agent_nom
        FROM cotisations c
        LEFT JOIN membres m ON m.id=c.membre_id
        LEFT JOIN users u ON u.id=c.agent_id
        WHERE 1=1
    """
    params = []
    if q:
        sql += " AND (m.nom LIKE ? OR m.prenom LIKE ? OR m.numero_adherent LIKE ? OR c.numero_recu LIKE ?)"
        params += [f'%{q}%'] * 4
    if mode_f:
        sql += " AND c.mode_paiement=?"
        params.append(mode_f)
    sql += " ORDER BY c.id DESC LIMIT 200"
    cur.execute(sql, params)
    cotis = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM cotisations WHERE statut='payee'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant),0) FROM cotisations WHERE statut='payee'")
    stats['montant'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant),0) FROM cotisations WHERE statut='payee' AND strftime('%Y-%m',date_paiement)=strftime('%Y-%m','now')")
    stats['mois'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM cotisations WHERE mode_paiement='mobile_money'")
    stats['mm'] = cur.fetchone()[0]

    rows = ''
    for c in cotis:
        statut_badge = {
            'payee': 'badge-green',
            'en_attente': 'badge-orange',
            'annulee': 'badge-red',
        }.get(c['statut'], 'badge-gray')
        mode_icon = {'mobile_money': '📱', 'especes': '💵', 'virement': '🏦'}.get(c['mode_paiement'], '💰')
        rows += (
            '<tr><td><strong style="color:#0891b2">' + str(c["numero_recu"] or "—") + '</strong></td>'
            + '<td><strong>' + str(c["prenom"] or "") + ' ' + str(c["nom"] or "") + '</strong><br><small style="color:#64748b">' + str(c["numero_adherent"] or "") + '</small></td>'
            + '<td>' + str(c["periode"] or "—") + '</td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{c["montant"]:,.0f}' + ' F</td>'
            + '<td>' + mode_icon + ' ' + str(c["mode_paiement"] or "—") + '</td>'
            + '<td>' + str((c["date_paiement"] or "")[:10]) + '</td>'
            + '<td>' + str(c["agent_nom"] or "—") + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">💰 Cotisations — ' + str(len(cotis)) + '</h1>'
    content += '<a href="/cotisations/nouvelle" class="btn btn-primary">+ Nouvelle cotisation</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">💰</div><div class="kpi-label">Total encaissé</div><div class="kpi-value" style="font-size:18px">' + f'{stats["montant"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">📅</div><div class="kpi-label">Ce mois</div><div class="kpi-value" style="font-size:18px">' + f'{stats["mois"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">🧾</div><div class="kpi-label">Nb reçus</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">📱</div><div class="kpi-label">Mobile Money</div><div class="kpi-value">' + str(stats["mm"]) + '</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher nom, n° reçu..." style="max-width:500px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/cotisations" class="btn ' + ('btn-primary' if not mode_f else 'btn-secondary') + '">Tous</a> '
    for m, l in [('mobile_money', '📱 Mobile Money'), ('especes', '💵 Espèces'), ('virement', '🏦 Virement')]:
        active_cls = 'btn-primary' if mode_f == m else 'btn-secondary'
        content += '<a href="/cotisations?mode=' + m + '" class="btn ' + active_cls + '" style="margin-left:6px">' + l + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Reçu</th><th>Membre</th><th>Période</th><th style="text-align:right">Montant</th>'
    content += '<th>Mode</th><th>Date</th><th>Agent</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucune cotisation</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='cotisations', page_title='Cotisations')


@app.route('/cotisations/nouvelle', methods=['GET', 'POST'])
@login_required
def cotisations_nouvelle():
    db = get_db()
    cur = db.cursor()
    membre_id_pre = int(request.args.get('membre_id') or 0)

    if request.method == 'POST':
        try:
            membre_id = int(request.form.get('membre_id') or 0)

            # Récupérer l'adhésion active
            cur.execute("""
                SELECT id, cotisation_mensuelle FROM adhesions
                WHERE membre_id=? AND statut='actif'
                ORDER BY id DESC LIMIT 1
            """, (membre_id,))
            ad = cur.fetchone()

            montant = float(request.form.get('montant') or (ad['cotisation_mensuelle'] if ad else 0))

            cur.execute("""
                INSERT INTO cotisations
                (numero_recu, membre_id, adhesion_id, periode, montant, mode_paiement,
                 reference, date_paiement, statut, agent_id, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?, 'payee', ?, ?, ?)
            """, (None, membre_id,
                  ad['id'] if ad else None,
                  request.form.get('periode') or datetime.now().strftime('%Y-%m'),
                  montant,
                  request.form.get('mode_paiement') or 'especes',
                  request.form.get('reference'),
                  request.form.get('date_paiement') or datetime.now().strftime('%Y-%m-%d'),
                  current_user.id,
                  request.form.get('notes'),
                  datetime.now().isoformat()))
            db.commit()
            log_action(current_user.id, 'COTISATION', f'{montant} F pour membre #{membre_id}',
                       'cotisations', cur.lastrowid)
            flash('✅ Cotisation enregistrée', 'success')
            return redirect('/cotisations')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("""
        SELECT m.id, m.nom, m.prenom, m.numero_adherent,
               (SELECT cotisation_mensuelle FROM adhesions WHERE membre_id=m.id AND statut='actif' ORDER BY id DESC LIMIT 1) AS cotis
        FROM membres m
        WHERE m.statut='actif'
        ORDER BY m.nom LIMIT 500
    """)
    membres = cur.fetchall()
    opts_m = ''.join('<option value="' + str(m["id"]) + '"' + (' selected' if m["id"] == membre_id_pre else '') + ' data-cotis="' + str(m["cotis"] or 0) + '">' + str(m["numero_adherent"] or "") + ' — ' + str(m["prenom"] or "") + ' ' + str(m["nom"] or "") + '</option>' for m in membres)

    content = '<h1>💰 Nouvelle cotisation</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="margin-bottom:16px"><label>Membre *</label>'
    content += '<select name="membre_id" id="membre_select" required onchange="updateCotis()">'
    content += '<option value="">— Sélectionner —</option>' + opts_m + '</select></div>'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Période (YYYY-MM)</label><input type="text" name="periode" value="' + datetime.now().strftime('%Y-%m') + '" pattern="[0-9]{4}-[0-9]{2}"></div>'
    content += '<div><label>Montant (FCFA) *</label><input type="number" step="500" name="montant" id="montant" required value="5000"></div>'
    content += '<div><label>Mode de paiement</label><select name="mode_paiement">'
    content += '<option value="especes">💵 Espèces</option>'
    content += '<option value="mobile_money">📱 Mobile Money</option>'
    content += '<option value="virement">🏦 Virement</option>'
    content += '</select></div>'
    content += '<div><label>Référence transaction</label><input type="text" name="reference"></div>'
    content += '<div><label>Date paiement</label><input type="date" name="date_paiement" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '</div>'
    content += '<div style="margin-top:16px"><label>Notes</label><textarea name="notes" rows="3"></textarea></div>'
    content += '<script>'
    content += 'function updateCotis() {'
    content += 'var sel = document.getElementById("membre_select");'
    content += 'var opt = sel.options[sel.selectedIndex];'
    content += 'var cotis = opt.getAttribute("data-cotis");'
    content += 'if (cotis && cotis !== "0") document.getElementById("montant").value = cotis;'
    content += '}'
    content += '</script>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Enregistrer la cotisation</button>'
    content += '<a href="/cotisations" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='cotisations', page_title='Nouvelle cotisation')


# ═══════════════════════════════════════════════════════════════
# 🏥 PRESTATAIRES DE SANTÉ
# ═══════════════════════════════════════════════════════════════

@app.route('/prestataires')
@login_required
def prestataires_liste():
    db = get_db()
    cur = db.cursor()
    type_f = request.args.get('type', '')
    q = request.args.get('q', '').strip()

    sql = "SELECT * FROM prestataires WHERE 1=1"
    params = []
    if type_f:
        sql += " AND type=?"
        params.append(type_f)
    if q:
        sql += " AND (nom LIKE ? OR ville LIKE ? OR region LIKE ?)"
        params += [f'%{q}%'] * 3
    sql += " ORDER BY nom"
    cur.execute(sql, params)
    prestataires = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM prestataires WHERE statut='actif'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM prestataires WHERE type='hopital'")
    stats['hop'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM prestataires WHERE type='clinique'")
    stats['clin'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM prestataires WHERE type='pharmacie'")
    stats['pharm'] = cur.fetchone()[0]

    rows = ''
    for p in prestataires:
        type_icon = {
            'hopital': '🏥', 'clinique': '🏨', 'poste_sante': '⛑️',
            'centre_sante': '🏪', 'pharmacie': '💊', 'laboratoire': '🔬',
        }.get(p['type'], '🏥')
        rows += (
            '<tr><td><strong style="color:#0891b2">' + str(p["code"] or "—") + '</strong></td>'
            + '<td>' + type_icon + ' <strong>' + str(p["nom"]) + '</strong><br><small style="color:#64748b">' + str(p["type"] or "") + '</small></td>'
            + '<td>' + str(p["ville"] or "—") + '<br><small style="color:#64748b">' + str(p["region"] or "") + '</small></td>'
            + '<td>' + str(p["telephone"] or "—") + '</td>'
            + '<td style="text-align:center">' + ('✅' if p["conventionne"] else '❌') + '</td>'
            + '<td style="text-align:center">' + str(p["taux_remise"]) + '%</td>'
            + '<td><span class="badge badge-green">' + str(p["statut"]) + '</span></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🏥 Prestataires — ' + str(len(prestataires)) + '</h1>'
    content += '<a href="/prestataires/nouveau" class="btn btn-primary">+ Nouveau prestataire</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">🏥</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">🏥</div><div class="kpi-label">Hôpitaux</div><div class="kpi-value">' + str(stats["hop"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">🏨</div><div class="kpi-label">Cliniques</div><div class="kpi-value">' + str(stats["clin"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💊</div><div class="kpi-label">Pharmacies</div><div class="kpi-value">' + str(stats["pharm"]) + '</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher nom, ville..." style="max-width:400px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/prestataires" class="btn ' + ('btn-primary' if not type_f else 'btn-secondary') + '">Tous</a> '
    for t, l in [('hopital', '🏥 Hôpitaux'), ('clinique', '🏨 Cliniques'), ('pharmacie', '💊 Pharmacies'), ('laboratoire', '🔬 Labos')]:
        active_cls = 'btn-primary' if type_f == t else 'btn-secondary'
        content += '<a href="/prestataires?type=' + t + '" class="btn ' + active_cls + '" style="margin-left:6px">' + l + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Nom</th><th>Localisation</th><th>Téléphone</th>'
    content += '<th style="text-align:center">Conventionné</th><th style="text-align:center">Remise</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucun prestataire</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='prestataires', page_title='Prestataires')


@app.route('/prestataires/nouveau', methods=['GET', 'POST'])
@login_required
def prestataires_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO prestataires (code, nom, type, categorie, adresse, ville, region,
                                            telephone, email, contact_nom, conventionne,
                                            taux_remise, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'actif', ?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('type'),
                  request.form.get('categorie') or 'prive',
                  request.form.get('adresse'),
                  request.form.get('ville'),
                  request.form.get('region'),
                  request.form.get('telephone'),
                  request.form.get('email'),
                  request.form.get('contact_nom'),
                  1 if request.form.get('conventionne') else 0,
                  float(request.form.get('taux_remise') or 0),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Prestataire créé', 'success')
            return redirect('/prestataires')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>🏥 Nouveau prestataire</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom du prestataire *</label>'
    content += '<input type="text" name="nom" required autofocus placeholder="Hôpital Principal de Dakar"></div>'
    content += '<div><label>Type</label><select name="type">'
    content += '<option value="hopital">🏥 Hôpital</option>'
    content += '<option value="clinique">🏨 Clinique</option>'
    content += '<option value="poste_sante">⛑️ Poste de santé</option>'
    content += '<option value="centre_sante">🏪 Centre de santé</option>'
    content += '<option value="pharmacie">💊 Pharmacie</option>'
    content += '<option value="laboratoire">🔬 Laboratoire</option>'
    content += '</select></div>'
    content += '<div><label>Catégorie</label><select name="categorie">'
    content += '<option value="public">Public</option>'
    content += '<option value="prive">Privé</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Adresse</label><input type="text" name="adresse"></div>'
    content += '<div><label>Ville</label><input type="text" name="ville" value="Dakar"></div>'
    content += '<div><label>Région</label><input type="text" name="region" value="Dakar"></div>'
    content += '<div><label>Téléphone</label><input type="text" name="telephone"></div>'
    content += '<div><label>Email</label><input type="email" name="email"></div>'
    content += '<div><label>Contact sur place</label><input type="text" name="contact_nom"></div>'
    content += '<div><label>Remise négociée (%)</label><input type="number" step="1" name="taux_remise" value="15" min="0" max="50"></div>'
    content += '<div style="grid-column:1/-1"><label><input type="checkbox" name="conventionne" value="1" checked style="width:auto;margin-right:8px"> Conventionné avec OMEGA Assurance</label></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/prestataires" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='prestataires', page_title='Nouveau prestataire')


# ═══════════════════════════════════════════════════════════════
# 💉 PRESTATIONS COUVERTES
# ═══════════════════════════════════════════════════════════════

@app.route('/prestations')
@login_required
def prestations_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT p.*,
               (SELECT COUNT(*) FROM sinistres WHERE prestation_id=p.id) AS nb_sinistres,
               (SELECT COALESCE(SUM(montant_rembourse),0) FROM sinistres WHERE prestation_id=p.id) AS total_rembourse
        FROM prestations p
        WHERE p.actif=1
        ORDER BY p.categorie, p.nom
    """)
    prestations = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM prestations WHERE actif=1")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT categorie) FROM prestations")
    stats['categories'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(taux_prise_charge),0) FROM prestations")
    stats['moy'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(plafond_annuel),0) FROM prestations")
    stats['plafond'] = cur.fetchone()[0]

    rows = ''
    for p in prestations:
        rows += (
            '<tr><td><strong style="color:#0891b2">' + str(p["code"] or "—") + '</strong></td>'
            + '<td><strong>' + str(p["nom"]) + '</strong><br><small style="color:#64748b">' + str(p["categorie"] or "") + '</small></td>'
            + '<td style="text-align:right">' + f'{p["plafond_annuel"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center">' + str(p["taux_prise_charge"]) + '%</td>'
            + '<td style="text-align:right">' + f'{p["ticket_moderateur"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center">' + str(p["delai_carence_jours"]) + ' j</td>'
            + '<td style="text-align:center">' + str(p["nb_sinistres"]) + '</td>'
            + '<td style="text-align:right;color:#dc2626;font-weight:700">' + f'{p["total_rembourse"]:,.0f}' + ' F</td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">💉 Prestations couvertes — ' + str(len(prestations)) + '</h1>'
    content += '<a href="/prestations/nouvelle" class="btn btn-primary">+ Nouvelle prestation</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">💉</div><div class="kpi-label">Total prestations</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🏷️</div><div class="kpi-label">Catégories</div><div class="kpi-value">' + str(stats["categories"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">📊</div><div class="kpi-label">Taux moyen</div><div class="kpi-value">' + f'{stats["moy"]:.0f}' + '%</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">💰</div><div class="kpi-label">Plafond cumulé</div><div class="kpi-value" style="font-size:16px">' + f'{stats["plafond"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Prestation</th><th style="text-align:right">Plafond</th>'
    content += '<th style="text-align:center">Taux</th><th style="text-align:right">Ticket mod.</th>'
    content += '<th style="text-align:center">Carence</th><th style="text-align:center">Sinistres</th>'
    content += '<th style="text-align:right">Remboursé</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucune prestation</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='prestations', page_title='Prestations')


@app.route('/prestations/nouvelle', methods=['GET', 'POST'])
@login_required
def prestations_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO prestations (code, nom, categorie, description, plafond_annuel,
                                           taux_prise_charge, ticket_moderateur, delai_carence_jours,
                                           actif, created_at)
                VALUES (?,?,?,?,?,?,?,?,1,?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('categorie'),
                  request.form.get('description'),
                  float(request.form.get('plafond_annuel') or 0),
                  float(request.form.get('taux_prise_charge') or 80),
                  float(request.form.get('ticket_moderateur') or 0),
                  int(request.form.get('delai_carence_jours') or 0),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Prestation créée', 'success')
            return redirect('/prestations')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>💉 Nouvelle prestation</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom de la prestation *</label>'
    content += '<input type="text" name="nom" required autofocus placeholder="Consultation spécialiste"></div>'
    content += '<div><label>Catégorie</label><select name="categorie">'
    content += '<option value="consultation">🩺 Consultation</option>'
    content += '<option value="hospitalisation">🏥 Hospitalisation</option>'
    content += '<option value="maternite">👶 Maternité</option>'
    content += '<option value="pharmacie">💊 Pharmacie</option>'
    content += '<option value="laboratoire">🔬 Laboratoire</option>'
    content += '<option value="imagerie">📷 Imagerie</option>'
    content += '<option value="chirurgie">🔪 Chirurgie</option>'
    content += '<option value="urgence">🚨 Urgence</option>'
    content += '<option value="optique">👁️ Optique</option>'
    content += '<option value="dentaire">🦷 Dentaire</option>'
    content += '<option value="maladie_chronique">🩸 Maladie chronique</option>'
    content += '<option value="prevention">💉 Prévention</option>'
    content += '</select></div>'
    content += '<div><label>Plafond annuel (FCFA)</label><input type="number" step="1000" name="plafond_annuel" value="100000"></div>'
    content += '<div><label>Taux de prise en charge (%)</label><input type="number" step="1" name="taux_prise_charge" value="80" min="0" max="100"></div>'
    content += '<div><label>Ticket modérateur (FCFA)</label><input type="number" step="500" name="ticket_moderateur" value="2000"></div>'
    content += '<div><label>Délai de carence (jours)</label><input type="number" name="delai_carence_jours" value="0"></div>'
    content += '<div style="grid-column:1/-1"><label>Description</label><textarea name="description" rows="3"></textarea></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/prestations" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='prestations', page_title='Nouvelle prestation')


# ═══════════════════════════════════════════════════════════════
# 📝 SINISTRES / DÉCLARATIONS
# ═══════════════════════════════════════════════════════════════

@app.route('/sinistres')
@login_required
def sinistres_liste():
    db = get_db()
    cur = db.cursor()
    statut_f = request.args.get('statut', '')
    q = request.args.get('q', '').strip()

    sql = """
        SELECT s.*, m.nom, m.prenom, m.numero_adherent,
               p.nom AS prestation_nom, pr.nom AS prestataire_nom
        FROM sinistres s
        LEFT JOIN membres m ON m.id=s.membre_id
        LEFT JOIN prestations p ON p.id=s.prestation_id
        LEFT JOIN prestataires pr ON pr.id=s.prestataire_id
        WHERE 1=1
    """
    params = []
    if statut_f:
        sql += " AND s.statut=?"
        params.append(statut_f)
    if q:
        sql += " AND (s.numero_sinistre LIKE ? OR m.nom LIKE ? OR m.prenom LIKE ? OR m.numero_adherent LIKE ?)"
        params += [f'%{q}%'] * 4
    sql += " ORDER BY s.id DESC LIMIT 200"
    cur.execute(sql, params)
    sinistres = cur.fetchall()

    stats = {}
    for k, s in [
        ('total', "SELECT COUNT(*) FROM sinistres"),
        ('declare', "SELECT COUNT(*) FROM sinistres WHERE statut='declare'"),
        ('rembourse', "SELECT COUNT(*) FROM sinistres WHERE statut='rembourse'"),
        ('montant', "SELECT COALESCE(SUM(montant_rembourse),0) FROM sinistres WHERE statut='rembourse'"),
    ]:
        cur.execute(s)
        stats[k] = cur.fetchone()[0]

    rows = ''
    for s in sinistres:
        statut_badge = {
            'declare': 'badge-orange',
            'en_cours': 'badge-blue',
            'rembourse': 'badge-green',
            'rejete': 'badge-red',
        }.get(s['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong style="color:#0891b2">' + str(s["numero_sinistre"] or "—") + '</strong></td>'
            + '<td><strong>' + str(s["prenom"] or "") + ' ' + str(s["nom"] or "") + '</strong><br><small style="color:#64748b">' + str(s["numero_adherent"] or "") + '</small></td>'
            + '<td>' + str(s["prestation_nom"] or "—") + '</td>'
            + '<td>' + str(s["prestataire_nom"] or "—") + '</td>'
            + '<td>' + str((s["date_soin"] or "—")[:10]) + '</td>'
            + '<td style="text-align:right">' + f'{s["montant_facture"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:800">' + f'{s["montant_rembourse"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(s["statut"]) + '</span></td>'
            + '<td><a href="/sinistres/' + str(s["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📝 Sinistres — ' + str(len(sinistres)) + '</h1>'
    content += '<a href="/sinistres/nouveau" class="btn btn-primary">+ Nouveau sinistre</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">📝</div><div class="kpi-label">Total sinistres</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">⏳</div><div class="kpi-label">À traiter</div><div class="kpi-value">' + str(stats["declare"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Remboursés</div><div class="kpi-value">' + str(stats["rembourse"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">💸</div><div class="kpi-label">Montant remboursé</div><div class="kpi-value" style="font-size:16px">' + f'{stats["montant"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher n° sinistre, adhérent..." style="max-width:500px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/sinistres" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Tous</a> '
    for s in ['declare', 'en_cours', 'rembourse', 'rejete']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/sinistres?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Sinistre</th><th>Adhérent</th><th>Prestation</th><th>Prestataire</th>'
    content += '<th>Date soin</th><th style="text-align:right">Facturé</th><th style="text-align:right">Remboursé</th>'
    content += '<th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="9" style="padding:40px;text-align:center;color:#94a3b8">Aucun sinistre</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='sinistres', page_title='Sinistres')


@app.route('/sinistres/nouveau', methods=['GET', 'POST'])
@login_required
def sinistres_nouveau():
    db = get_db()
    cur = db.cursor()
    membre_id_pre = int(request.args.get('membre_id') or 0)

    if request.method == 'POST':
        try:
            membre_id = int(request.form.get('membre_id') or 0)
            prestation_id = int(request.form.get('prestation_id') or 0)
            prestataire_id = int(request.form.get('prestataire_id') or 0) or None
            montant = float(request.form.get('montant_facture') or 0)

            # Récupérer la prestation pour calculer le remboursement
            cur.execute("SELECT taux_prise_charge, ticket_moderateur FROM prestations WHERE id=?", (prestation_id,))
            pr = cur.fetchone()
            taux = pr['taux_prise_charge'] if pr else 80
            ticket = pr['ticket_moderateur'] if pr else 0
            rembourse = max(0, montant * taux / 100 - ticket)

            cur.execute("""
                INSERT INTO sinistres
                (numero_sinistre, membre_id, prestation_id, prestataire_id, beneficiaire,
                 date_soin, date_declaration, description, montant_facture, montant_rembourse,
                 ticket_moderateur, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?, 'declare', ?)
            """, (None, membre_id, prestation_id, prestataire_id,
                  request.form.get('beneficiaire') or 'Adhérent',
                  request.form.get('date_soin') or datetime.now().strftime('%Y-%m-%d'),
                  datetime.now().strftime('%Y-%m-%d'),
                  request.form.get('description'),
                  montant, rembourse, ticket,
                  datetime.now().isoformat()))
            db.commit()
            log_action(current_user.id, 'SINISTRE', f'{montant} F - {rembourse} F remboursés',
                       'sinistres', cur.lastrowid)
            flash('✅ Sinistre déclaré — Remboursement prévu : ' + f'{rembourse:,.0f}' + ' F', 'success')
            return redirect('/sinistres')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom, prenom, numero_adherent FROM membres WHERE statut='actif' ORDER BY nom LIMIT 500")
    membres = cur.fetchall()
    cur.execute("SELECT id, nom FROM prestations WHERE actif=1 ORDER BY nom")
    prestations = cur.fetchall()
    cur.execute("SELECT id, nom FROM prestataires WHERE statut='actif' ORDER BY nom")
    prestataires = cur.fetchall()

    opts_m = ''.join('<option value="' + str(m["id"]) + '"' + (' selected' if m["id"] == membre_id_pre else '') + '>' + str(m["numero_adherent"] or "") + ' — ' + str(m["prenom"] or "") + ' ' + str(m["nom"] or "") + '</option>' for m in membres)
    opts_p = ''.join('<option value="' + str(p["id"]) + '">' + str(p["nom"]) + '</option>' for p in prestations)
    opts_pr = ''.join('<option value="' + str(p["id"]) + '">' + str(p["nom"]) + '</option>' for p in prestataires)

    content = '<h1>📝 Nouveau sinistre</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Adhérent *</label><select name="membre_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_m + '</select></div>'
    content += '<div><label>Prestation *</label><select name="prestation_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_p + '</select></div>'
    content += '<div><label>Prestataire</label><select name="prestataire_id">'
    content += '<option value="">— Aucun —</option>' + opts_pr + '</select></div>'
    content += '<div><label>Bénéficiaire des soins</label><input type="text" name="beneficiaire" value="Adhérent"></div>'
    content += '<div><label>Date des soins</label><input type="date" name="date_soin" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div style="grid-column:1/-1"><label>Montant facturé (FCFA) *</label>'
    content += '<input type="number" step="100" name="montant_facture" required value="15000"></div>'
    content += '<div style="grid-column:1/-1"><label>Description / Motif</label>'
    content += '<textarea name="description" rows="3"></textarea></div>'
    content += '</div>'
    content += '<div style="background:#fef2f2;padding:12px;border-radius:8px;margin-top:16px;font-size:12.5px;color:#991b1b">'
    content += '💡 Le montant remboursé sera calculé automatiquement selon le taux de prise en charge de la prestation.'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-danger">📝 Déclarer le sinistre</button>'
    content += '<a href="/sinistres" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='sinistres', page_title='Nouveau sinistre')


@app.route('/sinistres/<int:sid>', methods=['GET', 'POST'])
@login_required
def sinistres_detail(sid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.*, m.nom, m.prenom, m.numero_adherent, m.telephone,
               p.nom AS prestation_nom, p.taux_prise_charge,
               pr.nom AS prestataire_nom, pr.telephone AS prestataire_tel,
               u.nom_complet AS agent_nom
        FROM sinistres s
        LEFT JOIN membres m ON m.id=s.membre_id
        LEFT JOIN prestations p ON p.id=s.prestation_id
        LEFT JOIN prestataires pr ON pr.id=s.prestataire_id
        LEFT JOIN users u ON u.id=s.agent_id
        WHERE s.id=?
    """, (sid,))
    s = cur.fetchone()
    if not s:
        flash('❌ Sinistre introuvable', 'error')
        return redirect('/sinistres')

    # Traiter le sinistre
    if request.method == 'POST' and current_user.role in ('admin', 'gestionnaire', 'medecin_conseil'):
        try:
            new_statut = request.form.get('statut') or s['statut']
            motif_rejet = request.form.get('motif_rejet') or ''
            new_rembourse = float(request.form.get('montant_rembourse') or s['montant_rembourse'])

            date_traitement = datetime.now().strftime('%Y-%m-%d') if new_statut in ('rembourse', 'rejete') else None
            date_paiement = datetime.now().strftime('%Y-%m-%d') if new_statut == 'rembourse' else None

            cur.execute("""
                UPDATE sinistres SET
                    statut=?, montant_rembourse=?, date_traitement=?, date_paiement=?,
                    motif_rejet=?, agent_id=?
                WHERE id=?
            """, (new_statut, new_rembourse, date_traitement, date_paiement,
                  motif_rejet, current_user.id, sid))
            db.commit()
            log_action(current_user.id, 'TRAITEMENT_SINISTRE', f'SIN#{sid} → {new_statut}',
                       'sinistres', sid)
            flash('✅ Sinistre traité : ' + new_statut, 'success')
            return redirect('/sinistres/' + str(sid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    statut_badge = {
        'declare': 'badge-orange',
        'en_cours': 'badge-blue',
        'rembourse': 'badge-green',
        'rejete': 'badge-red',
    }.get(s['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📝 Sinistre ' + str(s["numero_sinistre"]) + ' <span class="badge ' + statut_badge + '">' + str(s["statut"]) + '</span></h1>'
    content += '<a href="/sinistres" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-label">Montant facturé</div><div class="kpi-value" style="font-size:18px">' + f'{s["montant_facture"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Remboursé</div><div class="kpi-value" style="font-size:18px">' + f'{s["montant_rembourse"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-label">Ticket modérateur</div><div class="kpi-value" style="font-size:18px">' + f'{s["ticket_moderateur"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Taux prise en charge</div><div class="kpi-value">' + str(s["taux_prise_charge"] or 0) + '%</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>📋 Détails sinistre</h2><table>'
    content += '<tr><td><strong>Adhérent</strong></td><td>' + str(s["prenom"] or "") + ' ' + str(s["nom"] or "") + '<br><small>' + str(s["numero_adherent"] or "") + ' · ' + str(s["telephone"] or "") + '</small></td></tr>'
    content += '<tr><td><strong>Prestation</strong></td><td>' + str(s["prestation_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Prestataire</strong></td><td>' + str(s["prestataire_nom"] or "—") + '<br><small>' + str(s["prestataire_tel"] or "") + '</small></td></tr>'
    content += '<tr><td><strong>Bénéficiaire</strong></td><td>' + str(s["beneficiaire"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Date des soins</strong></td><td>' + str((s["date_soin"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Date déclaration</strong></td><td>' + str((s["date_declaration"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Description</strong></td><td>' + str(s["description"] or "—") + '</td></tr>'
    if s['date_traitement']:
        content += '<tr><td><strong>Date traitement</strong></td><td>' + str(s["date_traitement"]) + '</td></tr>'
    if s['motif_rejet']:
        content += '<tr><td><strong>Motif rejet</strong></td><td style="color:#dc2626">' + str(s["motif_rejet"]) + '</td></tr>'
    content += '</table></div>'

    # Formulaire de traitement
    if current_user.role in ('admin', 'gestionnaire', 'medecin_conseil'):
        content += '<div class="card"><h2>✏️ Traiter le sinistre</h2>'
        content += '<form method="post">'
        content += '<div style="margin-bottom:14px"><label>Statut</label><select name="statut">'
        for st, lb in [('declare', '⏳ Déclaré'), ('en_cours', '🔵 En cours'), ('rembourse', '✅ Remboursé'), ('rejete', '❌ Rejeté')]:
            sel = ' selected' if s['statut'] == st else ''
            content += '<option value="' + st + '"' + sel + '>' + lb + '</option>'
        content += '</select></div>'
        content += '<div style="margin-bottom:14px"><label>Montant remboursé (FCFA)</label>'
        content += '<input type="number" step="100" name="montant_rembourse" value="' + f'{s["montant_rembourse"]:.0f}' + '"></div>'
        content += '<div style="margin-bottom:14px"><label>Motif de rejet (si applicable)</label>'
        content += '<textarea name="motif_rejet" rows="2">' + str(s["motif_rejet"] or "") + '</textarea></div>'
        content += '<button type="submit" class="btn btn-success">💾 Enregistrer</button>'
        content += '</form></div>'

    content += '</div>'
    return render_page(content, active='sinistres', page_title='Sinistre')


# ═══════════════════════════════════════════════════════════════
# 🩺 PRÉVENTION & SENSIBILISATION
# ═══════════════════════════════════════════════════════════════

@app.route('/prevention')
@login_required
def prevention_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT a.*, g.nom AS groupe_nom
        FROM actions_prevention a
        LEFT JOIN groupes g ON g.id=a.groupe_id
        ORDER BY a.date_action DESC LIMIT 100
    """)
    actions = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM actions_prevention")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM actions_prevention WHERE statut='planifiee'")
    stats['planifiee'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM actions_prevention WHERE statut='en_cours'")
    stats['encours'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM actions_prevention WHERE statut='terminee'")
    stats['terminee'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(nb_participants),0) FROM actions_prevention")
    stats['participants'] = cur.fetchone()[0]

    rows = ''
    for a in actions:
        statut_badge = {
            'planifiee': 'badge-blue',
            'en_cours': 'badge-orange',
            'terminee': 'badge-green',
            'annulee': 'badge-gray',
        }.get(a['statut'], 'badge-gray')
        type_icon = {
            'campagne': '📢', 'depistage': '🔬', 'formation': '🎓',
        }.get(a['type'], '🩺')
        rows += (
            '<tr><td>' + type_icon + ' <strong>' + str(a["titre"]) + '</strong></td>'
            + '<td>' + str(a["type"] or "—") + '</td>'
            + '<td>' + str(a["lieu"] or "—") + '</td>'
            + '<td>' + str((a["date_action"] or "—")[:10]) + '</td>'
            + '<td style="text-align:center">' + str(a["nb_participants"]) + '</td>'
            + '<td style="text-align:right">' + f'{a["cout"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(a["statut"]) + '</span></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🩺 Prévention & Sensibilisation</h1>'
    content += '<a href="/prevention/nouvelle" class="btn btn-primary">+ Nouvelle action</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">🩺</div><div class="kpi-label">Total actions</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">📅</div><div class="kpi-label">Planifiées</div><div class="kpi-value">' + str(stats["planifiee"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">🔴</div><div class="kpi-label">En cours</div><div class="kpi-value">' + str(stats["encours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Terminées</div><div class="kpi-value">' + str(stats["terminee"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">👥</div><div class="kpi-label">Participants</div><div class="kpi-value">' + str(stats["participants"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Action</th><th>Type</th><th>Lieu</th><th>Date</th>'
    content += '<th style="text-align:center">Participants</th><th style="text-align:right">Coût</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucune action</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='prevention', page_title='Prévention')


@app.route('/prevention/nouvelle', methods=['GET', 'POST'])
@login_required
def prevention_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO actions_prevention
                (titre, type, description, lieu, date_action, nb_participants,
                 groupe_id, cout, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (request.form.get('titre'),
                  request.form.get('type'),
                  request.form.get('description'),
                  request.form.get('lieu'),
                  request.form.get('date_action'),
                  int(request.form.get('nb_participants') or 0),
                  int(request.form.get('groupe_id') or 0) or None,
                  float(request.form.get('cout') or 0),
                  request.form.get('statut') or 'planifiee',
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Action de prévention créée', 'success')
            return redirect('/prevention')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom FROM groupes WHERE statut='actif'")
    groupes = cur.fetchall()
    opts_g = ''.join('<option value="' + str(g["id"]) + '">' + str(g["nom"]) + '</option>' for g in groupes)

    content = '<h1>🩺 Nouvelle action de prévention</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Titre de l\'action *</label>'
    content += '<input type="text" name="titre" required autofocus placeholder="Campagne de vaccination enfants"></div>'
    content += '<div><label>Type</label><select name="type">'
    content += '<option value="campagne">📢 Campagne</option>'
    content += '<option value="depistage">🔬 Dépistage</option>'
    content += '<option value="formation">🎓 Formation</option>'
    content += '<option value="sensibilisation">📣 Sensibilisation</option>'
    content += '</select></div>'
    content += '<div><label>Lieu</label><input type="text" name="lieu" value="Dakar"></div>'
    content += '<div><label>Date</label><input type="date" name="date_action" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Nb participants prévus</label><input type="number" name="nb_participants" value="50"></div>'
    content += '<div><label>Coût (FCFA)</label><input type="number" step="1000" name="cout" value="0"></div>'
    content += '<div><label>Groupe ciblé</label><select name="groupe_id"><option value="">— Aucun —</option>' + opts_g + '</select></div>'
    content += '<div><label>Statut</label><select name="statut">'
    content += '<option value="planifiee">📅 Planifiée</option>'
    content += '<option value="en_cours">🔴 En cours</option>'
    content += '<option value="terminee">✅ Terminée</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Description</label>'
    content += '<textarea name="description" rows="3"></textarea></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/prevention" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='prevention', page_title='Nouvelle action')


# ═══════════════════════════════════════════════════════════════
# 🎫 CARTE ADHÉRENT (avec QR)
# ═══════════════════════════════════════════════════════════════

@app.route('/membres/<int:mid>/carte')
@login_required
def membres_carte(mid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM membres WHERE id=?", (mid,))
    m = cur.fetchone()
    if not m:
        flash('❌ Adhérent introuvable', 'error')
        return redirect('/membres')

    # Récupérer adhésion active
    cur.execute("""
        SELECT a.*, f.nom AS formule_nom FROM adhesions a
        LEFT JOIN formules f ON f.id=a.formule_id
        WHERE a.membre_id=? AND a.statut='actif'
        ORDER BY a.id DESC LIMIT 1
    """, (mid,))
    ad = cur.fetchone()

    formule_nom = ad['formule_nom'] if ad else 'Aucune'
    date_fin = ad['date_fin'] if ad else '—'

    # QR code
    qr_data = 'ASSU|ADH|' + str(m['id']) + '|' + (m['numero_adherent'] or '') + '|' + (m['telephone'] or '')
    qr_url = '/qr/' + str(m['id']) + '.png'

    content = '''
    <div style="max-width:480px;margin:0 auto">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
        <a href="/membres/''' + str(mid) + '''" class="btn btn-secondary">← Retour</a>
        <a href="/membres/''' + str(mid) + '''/carte.pdf" class="btn btn-primary">📄 Imprimer</a>
      </div>

      <div style="background:linear-gradient(135deg,#0891b2,#0e7490);color:#fff;border-radius:16px;padding:22px;box-shadow:0 10px 30px rgba(0,0,0,.15);position:relative;overflow:hidden">
        <div style="position:absolute;top:-40px;right:-40px;width:150px;height:150px;background:rgba(220,38,38,.15);border-radius:50%"></div>

        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:18px;position:relative;z-index:1">
          <div>
            <div style="font-size:12px;opacity:.85;letter-spacing:2px;font-weight:600">OMEGA ASSURANCE</div>
            <div style="font-size:18px;font-weight:900">CARTE D'ADHÉRENT</div>
          </div>
          <div style="background:#dc2626;width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(220,38,38,.5)">🏥</div>
        </div>

        <div style="background:rgba(255,255,255,.95);color:#1e293b;border-radius:12px;padding:16px;position:relative;z-index:1">
          <div style="display:grid;grid-template-columns:1fr auto;gap:14px;align-items:start">
            <div>
              <div style="font-size:10px;color:#64748b;letter-spacing:1px;font-weight:700">N° ADHÉRENT</div>
              <div style="font-size:16px;font-weight:900;color:#0891b2;margin-bottom:12px">''' + str(m['numero_adherent'] or '—') + '''</div>

              <div style="font-size:10px;color:#64748b;letter-spacing:1px;font-weight:700">NOM COMPLET</div>
              <div style="font-size:15px;font-weight:800;margin-bottom:12px">''' + str(m['prenom'] or '') + ' ' + str(m['nom'] or '') + '''</div>

              <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:12px">
                <div>
                  <div style="font-size:9.5px;color:#64748b;font-weight:700">NAISSANCE</div>
                  <div style="font-weight:700">''' + str((m['date_naissance'] or '—')[:10]) + '''</div>
                </div>
                <div>
                  <div style="font-size:9.5px;color:#64748b;font-weight:700">TÉLÉPHONE</div>
                  <div style="font-weight:700">''' + str(m['telephone'] or '—') + '''</div>
                </div>
                <div>
                  <div style="font-size:9.5px;color:#64748b;font-weight:700">VILLE</div>
                  <div style="font-weight:700">''' + str(m['ville'] or '—') + '''</div>
                </div>
                <div>
                  <div style="font-size:9.5px;color:#64748b;font-weight:700">RÉGION</div>
                  <div style="font-weight:700">''' + str(m['region'] or '—') + '''</div>
                </div>
              </div>
            </div>

            <div style="text-align:center">
              <img src="''' + qr_url + '''" alt="QR" style="width:110px;height:110px;border:3px solid #0891b2;border-radius:10px">
              <div style="font-size:9.5px;color:#64748b;margin-top:6px;font-weight:700">SCANNER POUR VÉRIFIER</div>
            </div>
          </div>

          <div style="margin-top:14px;padding-top:12px;border-top:2px dashed #cbd5e1">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:12px">
              <div>
                <div style="font-size:9.5px;color:#64748b;font-weight:700">FORMULE</div>
                <div style="font-weight:800;color:#10b981">''' + str(formule_nom) + '''</div>
              </div>
              <div>
                <div style="font-size:9.5px;color:#64748b;font-weight:700">VALABLE JUSQU'AU</div>
                <div style="font-weight:800;color:#dc2626">''' + str((date_fin or '—')[:10]) + '''</div>
              </div>
            </div>
          </div>
        </div>

        <div style="text-align:center;margin-top:14px;font-size:10.5px;opacity:.85;letter-spacing:1px;position:relative;z-index:1">
          🏥 COUVERTURE MALADIE UNIVERSELLE · SÉNÉGAL
        </div>
      </div>

      <div style="margin-top:20px;padding:14px;background:#fef2f2;border-left:4px solid #dc2626;border-radius:8px;font-size:12.5px;color:#991b1b">
        ⚠️ <strong>Urgences</strong> : présentez cette carte dans tout établissement conventionné OMEGA Assurance
      </div>
    </div>
    '''
    return render_page(content, active='membres', page_title='Carte adhérent')


@app.route('/qr/<int:mid>.png')
def qr_membre(mid):
    """Génère le QR code d'un adhérent."""
    import qrcode
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT numero_adherent, telephone FROM membres WHERE id=?", (mid,))
    m = cur.fetchone()
    if not m:
        return redirect('/')

    qr_data = 'ASSU|ADH|' + str(mid) + '|' + (m['numero_adherent'] or '') + '|' + (m['telephone'] or '')

    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#0e7490', back_color='white')

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


@app.route('/membres/<int:mid>/carte.pdf')
@login_required
def membres_carte_pdf(mid):
    from reportlab.lib.pagesizes import A6
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    import qrcode

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM membres WHERE id=?", (mid,))
    m = cur.fetchone()
    if not m:
        flash('❌ Adhérent introuvable', 'error')
        return redirect('/membres')

    cur.execute("""
        SELECT a.*, f.nom AS formule_nom FROM adhesions a
        LEFT JOIN formules f ON f.id=a.formule_id
        WHERE a.membre_id=? AND a.statut='actif'
        ORDER BY a.id DESC LIMIT 1
    """, (mid,))
    ad = cur.fetchone()

    # Générer QR
    qr = qrcode.make('ASSU|ADH|' + str(mid) + '|' + (m['numero_adherent'] or ''))
    qr_buf = io.BytesIO()
    qr.save(qr_buf, format='PNG')
    qr_buf.seek(0)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A6)
    w, h = A6

    # Fond bleu ciel
    c.setFillColor(colors.HexColor('#0891b2'))
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Bandeau rouge
    c.setFillColor(colors.HexColor('#dc2626'))
    c.rect(0, h - 25*mm, w, 25*mm, fill=1, stroke=0)

    # Header
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(8*mm, h - 10*mm, 'OMEGA ASSURANCE')
    c.setFont('Helvetica', 7)
    c.drawString(8*mm, h - 15*mm, "CARTE D'ADHÉRENT")
    c.setFont('Helvetica-Bold', 20)
    c.drawRightString(w - 8*mm, h - 12*mm, '🏥')

    # Carte blanche
    card_y = 30*mm
    card_h = h - 25*mm - card_y - 8*mm
    c.setFillColor(colors.white)
    c.roundRect(6*mm, card_y, w - 12*mm, card_h, 3*mm, fill=1, stroke=0)

    y = card_y + card_h - 6*mm
    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica-Bold', 6)
    c.drawString(8*mm, y, 'N° ADHÉRENT')
    y -= 4*mm
    c.setFillColor(colors.HexColor('#0891b2'))
    c.setFont('Helvetica-Bold', 11)
    c.drawString(8*mm, y, str(m['numero_adherent'] or '—'))

    y -= 7*mm
    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica-Bold', 6)
    c.drawString(8*mm, y, 'NOM COMPLET')
    y -= 4*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(8*mm, y, (m['prenom'] or '') + ' ' + (m['nom'] or ''))

    y -= 7*mm
    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica-Bold', 6)
    c.drawString(8*mm, y, 'TÉLÉPHONE')
    c.drawString(40*mm, y, 'VILLE')
    y -= 4*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica', 9)
    c.drawString(8*mm, y, str(m['telephone'] or '—'))
    c.drawString(40*mm, y, str(m['ville'] or '—'))

    y -= 7*mm
    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica-Bold', 6)
    c.drawString(8*mm, y, 'FORMULE')
    c.drawString(40*mm, y, "VALABLE JUSQU'AU")
    y -= 4*mm
    c.setFillColor(colors.HexColor('#10b981'))
    c.setFont('Helvetica-Bold', 9)
    c.drawString(8*mm, y, (ad['formule_nom'] if ad else '—'))
    c.setFillColor(colors.HexColor('#dc2626'))
    c.drawString(40*mm, y, str((ad['date_fin'] if ad else '—')[:10]))

    # QR code en bas à droite
    qr_size = 22*mm
    c.drawImage(qr_buf, w - qr_size - 10*mm, card_y + 6*mm, qr_size, qr_size)

    # Footer
    c.setFillColor(colors.white)
    c.setFont('Helvetica', 6)
    c.drawCentredString(w / 2, 6*mm, 'COUVERTURE MALADIE UNIVERSELLE · SÉNÉGAL')
    c.drawCentredString(w / 2, 3*mm, 'En cas d\'urgence, présentez cette carte')

    c.showPage()
    c.save()
    buf.seek(0)

    log_action(current_user.id, 'PDF_CARTE_ADHERENT', str(m['numero_adherent']), 'membres', mid)
    return send_file(buf, mimetype='application/pdf',
                     download_name='carte_' + str(m['numero_adherent'] or mid) + '.pdf')


# ═══════════════════════════════════════════════════════════════
# 📈 ANALYTICS
# ═══════════════════════════════════════════════════════════════

@app.route('/analytics')
@login_required
def analytics():
    db = get_db()
    cur = db.cursor()

    def sc(sql, default=0):
        cur.execute(sql)
        r = cur.fetchone()
        return r[0] if r and r[0] is not None else default

    cotis_total = sc("SELECT COALESCE(SUM(montant),0) FROM cotisations WHERE statut='payee'")
    remb_total = sc("SELECT COALESCE(SUM(montant_rembourse),0) FROM sinistres WHERE statut='rembourse'")
    ratio = (remb_total / cotis_total * 100) if cotis_total > 0 else 0
    marge = cotis_total - remb_total

    # Membres par région
    cur.execute("""
        SELECT region, COUNT(*) AS nb
        FROM membres WHERE region IS NOT NULL
        GROUP BY region ORDER BY nb DESC LIMIT 10
    """)
    regions = cur.fetchall()
    max_r = max([r['nb'] for r in regions], default=1)
    regions_html = ''
    for r in regions:
        pct = r['nb'] / max_r * 100
        regions_html += (
            '<div style="margin-bottom:10px">'
            + '<div style="display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:4px">'
            + '<strong>' + str(r["region"]) + '</strong><span>' + str(r["nb"]) + ' membres</span></div>'
            + '<div style="background:#e2e8f0;border-radius:6px;overflow:hidden;height:10px">'
            + '<div style="background:linear-gradient(90deg,#0891b2,#0e7490);height:100%;width:' + f'{pct:.0f}' + '%"></div></div></div>'
        )

    # Top prestations par sinistres
    cur.execute("""
        SELECT p.nom, COUNT(s.id) AS nb, COALESCE(SUM(s.montant_rembourse),0) AS total
        FROM prestations p
        LEFT JOIN sinistres s ON s.prestation_id=p.id AND s.statut='rembourse'
        GROUP BY p.id
        ORDER BY total DESC LIMIT 8
    """)
    top_prest = cur.fetchall()
    prest_html = ''.join(
        '<tr><td>' + str(p["nom"]) + '</td>'
        + '<td style="text-align:center">' + str(p["nb"]) + '</td>'
        + '<td style="text-align:right;color:#dc2626;font-weight:700">' + f'{p["total"]:,.0f}' + ' F</td></tr>'
        for p in top_prest
    )

    # Répartition formules
    cur.execute("""
        SELECT f.nom, COUNT(a.id) AS nb
        FROM formules f
        LEFT JOIN adhesions a ON a.formule_id=f.id AND a.statut='actif'
        GROUP BY f.id ORDER BY nb DESC
    """)
    formules = cur.fetchall()
    form_html = ''.join(
        '<tr><td>' + str(f["nom"]) + '</td>'
        + '<td style="text-align:center">' + str(f["nb"]) + '</td></tr>'
        for f in formules
    )

    content = '<h1>📈 Analytics & Performance</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">Cotisations totales</div><div class="kpi-value" style="font-size:18px">' + f'{cotis_total:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">💸</div><div class="kpi-label">Remboursements</div><div class="kpi-value" style="font-size:18px">' + f'{remb_total:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div class="kpi-icon">📊</div><div class="kpi-label">Taux sinistralité</div><div class="kpi-value">' + f'{ratio:.1f}' + '%</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">📈</div><div class="kpi-label">Marge technique</div><div class="kpi-value" style="font-size:18px">' + f'{marge:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>🗺️ Adhérents par région</h2>'
    content += (regions_html or '<p style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</p>')
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>💉 Top prestations remboursées</h2>'
    content += '<table><thead><tr><th>Prestation</th><th style="text-align:center">Nb</th><th style="text-align:right">Total</th></tr></thead>'
    content += '<tbody>' + (prest_html or '<tr><td colspan="3" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>📋 Répartition formules</h2>'
    content += '<table><thead><tr><th>Formule</th><th style="text-align:center">Adhérents</th></tr></thead>'
    content += '<tbody>' + (form_html or '<tr><td colspan="2" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    content += '<div class="card" style="border-left-color:#dc2626"><h2>🎯 Objectifs CMU Sénégal</h2>'
    content += '<ul style="line-height:2;color:#334155;font-size:14px">'
    content += '<li>🎯 <strong>75% de couverture maladie</strong> d\'ici 2030 (vs 20% actuellement)</li>'
    content += '<li>👥 <strong>500 000 adhérents</strong> ciblés au Sénégal</li>'
    content += '<li>🤝 <strong>1 000 tontines et coopératives</strong> partenaires</li>'
    content += '<li>🏥 <strong>200 prestataires conventionnés</strong> dans les 14 régions</li>'
    content += '<li>📱 <strong>Paiement mobile money</strong> pour accessibilité</li>'
    content += '</ul></div>'

    return render_page(content, active='analytics', page_title='Analytics')


# ═══════════════════════════════════════════════════════════════
# 📱 MOBILE AGENT
# ═══════════════════════════════════════════════════════════════

@app.route('/mobile-agent')
@login_required
def mobile_agent():
    db = get_db()
    cur = db.cursor()

    def sc(sql, default=0):
        cur.execute(sql)
        r = cur.fetchone()
        return r[0] if r and r[0] is not None else default

    stats = {
        'cotis_jour': sc("SELECT COUNT(*) FROM cotisations WHERE date_paiement=date('now')"),
        'cotis_montant': sc("SELECT COALESCE(SUM(montant),0) FROM cotisations WHERE date_paiement=date('now')"),
        'sinistres_jour': sc("SELECT COUNT(*) FROM sinistres WHERE date_declaration=date('now')"),
        'membres_jour': sc("SELECT COUNT(*) FROM membres WHERE date_adhesion=date('now')"),
    }

    content = '<h1>📱 Mobile Agent</h1>'
    content += '<div style="background:#ecfeff;border-left:4px solid #0891b2;padding:14px;border-radius:8px;margin-bottom:20px;font-size:13px;color:#0e7490">'
    content += '💡 Interface simplifiée pour les agents de terrain'
    content += '</div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-label">Nouveaux adhérents (jour)</div><div class="kpi-value">' + str(stats["membres_jour"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Cotisations du jour</div><div class="kpi-value">' + str(stats["cotis_jour"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Encaissé (jour)</div><div class="kpi-value" style="font-size:18px">' + f'{stats["cotis_montant"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-label">Sinistres (jour)</div><div class="kpi-value">' + str(stats["sinistres_jour"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>⚡ Actions rapides</h2>'
    content += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:12px">'

    actions = [
        ('/membres/nouveau', '👤 Nouvel adhérent', '#0891b2'),
        ('/cotisations/nouvelle', '💰 Cotisation', '#10b981'),
        ('/sinistres/nouveau', '📝 Sinistre', '#dc2626'),
        ('/membres', '🔍 Rechercher adhérent', '#8b5cf6'),
        ('/prevention', '🩺 Prévention', '#f97316'),
        ('/prestataires', '🏥 Prestataires', '#2563eb'),
    ]
    for url, label, color in actions:
        content += '<a href="' + url + '" style="text-decoration:none"><div style="background:' + color + ';color:#fff;padding:20px;border-radius:10px;text-align:center;font-weight:700;font-size:13px">' + label + '</div></a>'

    content += '</div></div>'

    content += '<div class="card"><h2>💰 Dernières cotisations encaissées</h2>'
    cur.execute("""
        SELECT c.*, m.nom, m.prenom, m.numero_adherent
        FROM cotisations c
        LEFT JOIN membres m ON m.id=c.membre_id
        ORDER BY c.id DESC LIMIT 10
    """)
    cotis = cur.fetchall()
    rows = ''
    for c in cotis:
        rows += (
            '<tr><td><strong>' + str(c["numero_recu"]) + '</strong></td>'
            + '<td>' + str(c["prenom"] or "") + ' ' + str(c["nom"] or "") + '</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:800">' + f'{c["montant"]:,.0f}' + ' F</td>'
            + '<td>' + str(c["mode_paiement"] or "—") + '</td></tr>'
        )
    content += '<table><thead><tr><th>N° Reçu</th><th>Membre</th><th style="text-align:right">Montant</th><th>Mode</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucune cotisation</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='mobile', page_title='Mobile Agent')


# ═══════════════════════════════════════════════════════════════
# 📊 API JSON
# ═══════════════════════════════════════════════════════════════

@app.route('/api/assurance/stats')
@login_required
def api_assurance_stats():
    db = get_db()
    cur = db.cursor()
    result = {}
    for k, sql in [
        ('membres', "SELECT COUNT(*) FROM membres WHERE statut='actif'"),
        ('cotisations', "SELECT COALESCE(SUM(montant),0) FROM cotisations WHERE statut='payee'"),
        ('sinistres', "SELECT COUNT(*) FROM sinistres"),
        ('rembourses', "SELECT COALESCE(SUM(montant_rembourse),0) FROM sinistres WHERE statut='rembourse'"),
        ('prestataires', "SELECT COUNT(*) FROM prestataires WHERE statut='actif'"),
    ]:
        try:
            cur.execute(sql)
            r = cur.fetchone()
            result[k] = r[0] if r else 0
        except Exception:
            result[k] = 0
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
