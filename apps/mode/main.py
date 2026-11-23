"""
🎨 Mode & Couture CEDEAO — Application principale
Créations · Mesures · Commandes · Salons · Export UE
"""
from flask import Flask, render_template_string, redirect, url_for, session, request, jsonify, Response, send_file, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import sqlite3
import os
import io

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'omega-mode-secret-2026')

DB_PATH = '/app/data/mode.db'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id, username, role, nom_complet, atelier=''):
        self.id = id
        self.username = username
        self.role = role
        self.nom_complet = nom_complet
        self.atelier = atelier


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
        return User(r['id'], r['username'], r['role'], r['nom_complet'], r['atelier'] or '')
    return None


# ═══════════════════════════════════════════════════════════════
# LAYOUT — DESIGN MODE & COUTURE
# ═══════════════════════════════════════════════════════════════

LAYOUT = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — OMEGA Mode</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,-apple-system,sans-serif}}
body{{background:#fdf4ff;color:#1e293b;font-size:14px}}
.nav{{background:linear-gradient(135deg,#db2777,#9d174d);color:#fff;padding:0 22px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 3px 12px rgba(0,0,0,.15);flex-wrap:wrap;border-bottom:4px solid #f59e0b}}
.nav-brand{{font-weight:900;font-size:18px;display:flex;align-items:center;gap:12px;padding:16px 0;letter-spacing:-0.3px}}
.nav-brand-icon{{width:40px;height:40px;background:#f59e0b;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(245,158,11,.5)}}
.nav-links{{display:flex;gap:2px;flex-wrap:wrap}}
.nav-links a{{color:#fce7f3;text-decoration:none;padding:8px 13px;border-radius:8px;font-size:12.5px;font-weight:600;transition:.2s;display:flex;align-items:center;gap:6px}}
.nav-links a:hover{{background:rgba(255,255,255,.12);color:#fff}}
.nav-links a.active{{background:#f59e0b;color:#fff;box-shadow:0 4px 10px rgba(245,158,11,.4)}}
.nav-user{{font-size:12.5px;display:flex;gap:10px;align-items:center;color:#fce7f3}}
.nav-user a{{color:#fff;text-decoration:none;background:rgba(0,0,0,.25);padding:7px 14px;border-radius:8px;font-weight:600}}
.container{{max-width:1600px;margin:0 auto;padding:24px}}
h1{{color:#9d174d;margin-bottom:20px;font-size:24px;font-weight:800;letter-spacing:-0.4px}}
h2{{color:#db2777;font-size:18px;margin-bottom:14px;font-weight:700}}
.card{{background:#fff;padding:22px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:18px;border-left:4px solid #db2777}}
table{{width:100%;border-collapse:collapse}}
thead{{background:#9d174d;color:#fff}}
th{{padding:12px;text-align:left;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}}
td{{padding:11px;border-bottom:1px solid #f1f5f9;font-size:13.5px}}
tbody tr:hover{{background:#fdf2f8}}
.btn{{display:inline-block;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px;border:none;cursor:pointer;transition:.15s;letter-spacing:.2px}}
.btn:hover{{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.15)}}
.btn-primary{{background:#db2777;color:#fff}}
.btn-gold{{background:#f59e0b;color:#fff}}
.btn-success{{background:#10b981;color:#fff}}
.btn-danger{{background:#ef4444;color:#fff}}
.btn-warning{{background:#f59e0b;color:#fff}}
.btn-secondary{{background:#64748b;color:#fff}}
input,select,textarea{{width:100%;padding:11px 14px;border:2px solid #e2e8f0;border-radius:8px;font-size:13.5px;font-family:inherit;transition:.2s}}
input:focus,select:focus,textarea:focus{{outline:none;border-color:#db2777;box-shadow:0 0 0 3px rgba(219,39,119,.1)}}
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
.badge-pink{{background:#fce7f3;color:#9d174d}}
.badge-green{{background:#d1fae5;color:#047857}}
.badge-orange{{background:#fed7aa;color:#c2410c}}
.badge-red{{background:#fee2e2;color:#b91c1c}}
.badge-blue{{background:#dbeafe;color:#1e40af}}
.badge-purple{{background:#e9d5ff;color:#6b21a8}}
.badge-gray{{background:#e2e8f0;color:#475569}}
.creation-card{{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:.2s}}
.creation-card:hover{{transform:translateY(-3px);box-shadow:0 8px 20px rgba(219,39,119,.15)}}
.creation-icon{{background:linear-gradient(135deg,#db2777,#9d174d);color:#fff;height:100px;display:flex;align-items:center;justify-content:center;font-size:44px}}
.creation-body{{padding:16px}}
.creation-price{{font-size:20px;font-weight:900;color:#10b981}}
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-brand">
    <div class="nav-brand-icon">🎨</div>
    <div>OMEGA MODE<span style="display:block;font-size:10px;font-weight:500;letter-spacing:2px;color:#fce7f3">COUTURE · CEDEAO · EXPORT UE</span></div>
  </div>
  <div class="nav-links">
    <a href="/" class="{a_dash}">📊 Dashboard</a>
    <a href="/creations" class="{a_crea}">👗 Créations</a>
    <a href="/ateliers" class="{a_atl}">🏢 Ateliers</a>
    <a href="/clients" class="{a_cli}">👥 Clients</a>
    <a href="/mesures" class="{a_mes}">📏 Mesures</a>
    <a href="/commandes" class="{a_cmd}">✂️ Commandes</a>
    <a href="/tissus" class="{a_tis}">🧵 Tissus</a>
    <a href="/salons" class="{a_sal}">🎪 Salons</a>
    <a href="/billets" class="{a_bil}">🎫 Billets</a>
    <a href="/livraisons" class="{a_liv}">🚚 Livraisons</a>
    <a href="/exports" class="{a_exp}">🌍 Export UE</a>
    <a href="/finances" class="{a_fin}">💰 Finances</a>
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


def render_page(content, active='dashboard', page_title='Mode'):
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
        a_crea='active' if active == 'creations' else '',
        a_atl='active' if active == 'ateliers' else '',
        a_cli='active' if active == 'clients' else '',
        a_mes='active' if active == 'mesures' else '',
        a_cmd='active' if active == 'commandes' else '',
        a_tis='active' if active == 'tissus' else '',
        a_sal='active' if active == 'salons' else '',
        a_bil='active' if active == 'billets' else '',
        a_liv='active' if active == 'livraisons' else '',
        a_exp='active' if active == 'exports' else '',
        a_fin='active' if active == 'finances' else '',
    )


@app.route('/health')
def health():
    return {'project': 'OMEGA MODE', 'service': 'mode-couture-cedeao',
            'status': 'ok', 'timestamp': datetime.now().isoformat(), 'version': '1.0'}


LOGIN_HTML = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Connexion — OMEGA Mode</title>
<style>body{{font-family:system-ui;background:linear-gradient(135deg,#db2777,#9d174d);min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0}}
.box{{background:#fff;padding:42px;border-radius:16px;box-shadow:0 25px 70px rgba(0,0,0,.4);width:100%;max-width:420px;border-top:5px solid #f59e0b}}
.logo{{text-align:center;font-size:56px;margin-bottom:12px}}
h1{{color:#9d174d;margin:0 0 6px;text-align:center;font-size:22px;font-weight:900;letter-spacing:-0.3px}}
.subtitle{{text-align:center;color:#64748b;font-size:12px;margin-bottom:24px;letter-spacing:1.5px;text-transform:uppercase;font-weight:600}}
input{{width:100%;padding:14px;border:2px solid #e2e8f0;border-radius:10px;margin-bottom:14px;font-size:15px;box-sizing:border-box}}
input:focus{{outline:none;border-color:#db2777;box-shadow:0 0 0 3px rgba(219,39,119,.1)}}
button{{width:100%;background:#f59e0b;color:#fff;padding:15px;border:none;border-radius:10px;font-weight:800;font-size:15px;cursor:pointer;letter-spacing:.5px;text-transform:uppercase}}
button:hover{{background:#d97706}}
.err{{background:#fee2e2;color:#991b1b;padding:11px;border-radius:8px;margin-bottom:14px;font-size:13px;border-left:4px solid #ef4444}}
.hint{{margin-top:20px;padding:12px;background:#fdf2f8;border-radius:8px;font-size:12px;color:#9d174d;text-align:center;border:1px dashed #f9a8d4}}</style></head>
<body><div class="box">
<div class="logo">🎨</div>
<h1>OMEGA MODE</h1>
<div class="subtitle">Couture · CEDEAO · Export UE</div>
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
            user = User(r['id'], r['username'], r['role'], r['nom_complet'], r['atelier'] or '')
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
        'ateliers': sc("SELECT COUNT(*) FROM ateliers WHERE statut='actif'"),
        'creations': sc("SELECT COUNT(*) FROM creations WHERE disponible=1"),
        'clients': sc("SELECT COUNT(*) FROM clients WHERE statut='actif'"),
        'commandes_encours': sc("SELECT COUNT(*) FROM commandes WHERE statut IN ('devis','confirmee','en_coupe','en_couture','finition')"),
        'commandes_livrees': sc("SELECT COUNT(*) FROM commandes WHERE statut='livree'"),
        'ca_total': sc("SELECT COALESCE(SUM(montant_ttc),0) FROM commandes WHERE statut='livree'"),
        'salons': sc("SELECT COUNT(*) FROM salons WHERE statut='planifie'"),
        'billets_vendus': sc("SELECT COUNT(*) FROM billets WHERE statut='valide'"),
        'exports_ue': sc("SELECT COUNT(*) FROM exports WHERE certificat_ue=1"),
        'export_valeur': sc("SELECT COALESCE(SUM(valeur_fcfa),0) FROM exports"),
    }

    # Commandes récentes
    cur.execute("""
        SELECT c.*, cl.nom AS client_nom, cl.prenom AS client_prenom,
               a.nom AS atelier_nom, cr.nom AS creation_nom
        FROM commandes c
        LEFT JOIN clients cl ON cl.id=c.client_id
        LEFT JOIN ateliers a ON a.id=c.atelier_id
        LEFT JOIN creations cr ON cr.id=c.creation_id
        ORDER BY c.id DESC LIMIT 8
    """)
    commandes = cur.fetchall()

    cmd_html = ''
    for c in commandes:
        statut_badge = {
            'devis': 'badge-gray',
            'confirmee': 'badge-blue',
            'en_coupe': 'badge-orange',
            'en_couture': 'badge-pink',
            'finition': 'badge-purple',
            'prete': 'badge-gold',
            'livree': 'badge-green',
            'annulee': 'badge-red',
        }.get(c['statut'], 'badge-gray')
        cmd_html += (
            '<tr><td><strong style="color:#db2777">' + str(c["numero"]) + '</strong></td>'
            + '<td>' + str(c["client_prenom"] or "") + ' ' + str(c["client_nom"] or "—") + '</td>'
            + '<td>' + str(c["creation_nom"] or "—") + '<br><small style="color:#64748b">' + str(c["atelier_nom"] or "") + '</small></td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{c["montant_ttc"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></td>'
            + '<td><a href="/commandes/' + str(c["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    # Top créations
    cur.execute("""
        SELECT c.nom, c.prix_vente, COUNT(cmd.id) AS nb_commandes
        FROM creations c
        LEFT JOIN commandes cmd ON cmd.creation_id=c.id
        GROUP BY c.id
        ORDER BY nb_commandes DESC LIMIT 5
    """)
    top_creations = cur.fetchall()
    top_html = ''.join(
        '<tr><td>' + str(t["nom"]) + '</td>'
        + '<td style="text-align:center">' + str(t["nb_commandes"]) + '</td>'
        + '<td style="text-align:right">' + f'{t["prix_vente"]:,.0f}' + ' F</td></tr>'
        for t in top_creations
    )

    content = '<h1>🎨 Tableau de bord Mode & Couture</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-icon">🏢</div><div class="kpi-label">Ateliers</div><div class="kpi-value">' + str(stats["ateliers"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">👗</div><div class="kpi-label">Créations</div><div class="kpi-value">' + str(stats["creations"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">👥</div><div class="kpi-label">Clients</div><div class="kpi-value">' + str(stats["clients"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">✂️</div><div class="kpi-label">En cours</div><div class="kpi-value">' + str(stats["commandes_encours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Livrées</div><div class="kpi-value">' + str(stats["commandes_livrees"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div class="kpi-icon">💰</div><div class="kpi-label">CA total</div><div class="kpi-value" style="font-size:16px">' + f'{stats["ca_total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#14b8a6,#0d9488)"><div class="kpi-icon">🎪</div><div class="kpi-label">Salons</div><div class="kpi-value">' + str(stats["salons"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#6366f1,#4338ca)"><div class="kpi-icon">🌍</div><div class="kpi-label">Exports UE</div><div class="kpi-value">' + str(stats["exports_ue"]) + '</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:18px">'
    content += '<div class="card"><h2>✂️ Commandes récentes</h2>'
    content += '<table><thead><tr><th>N°</th><th>Client</th><th>Création</th><th style="text-align:right">Montant</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (cmd_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:30px">Aucune commande</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>🏆 Top 5 créations</h2>'
    content += '<table><thead><tr><th>Création</th><th style="text-align:center">Commandes</th><th style="text-align:right">Prix</th></tr></thead>'
    content += '<tbody>' + (top_html or '<tr><td colspan="3" style="text-align:center;color:#94a3b8;padding:30px">Aucune donnée</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    content += '<div class="card"><h2>⚡ Actions rapides</h2>'
    content += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:12px">'
    actions = [
        ('/creations/nouvelle', '👗 Nouvelle création', '#db2777'),
        ('/clients/nouveau', '👥 Nouveau client', '#8b5cf6'),
        ('/mesures/nouvelle', '📏 Nouvelle mesure', '#f59e0b'),
        ('/commandes/nouvelle', '✂️ Nouvelle commande', '#10b981'),
        ('/salons', '🎪 Salons & expositions', '#3b82f6'),
        ('/exports', '🌍 Export UE', '#ec4899'),
    ]
    for url, label, color in actions:
        content += '<a href="' + url + '" style="text-decoration:none"><div style="background:' + color + ';color:#fff;padding:20px;border-radius:10px;text-align:center;font-weight:700;font-size:13px">' + label + '</div></a>'
    content += '</div></div>'

    return render_page(content, active='dashboard', page_title='Dashboard')


# ═══════════════════════════════════════════════════════════════
# 🏢 ATELIERS / MAISONS DE COUTURE
# ═══════════════════════════════════════════════════════════════


@app.route('/ateliers')
@login_required
def ateliers_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()

    sql = """
        SELECT a.*,
               (SELECT COUNT(*) FROM creations WHERE atelier_id=a.id) AS nb_creations,
               (SELECT COUNT(*) FROM commandes WHERE atelier_id=a.id) AS nb_commandes_total
        FROM ateliers a
        WHERE 1=1
    """
    params = []
    if q:
        sql += " AND (a.nom LIKE ? OR a.specialite LIKE ? OR a.ville LIKE ?)"
        params += [f'%{q}%'] * 3
    sql += " ORDER BY a.note_moyenne DESC, a.nom"
    cur.execute(sql, params)
    ateliers = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM ateliers WHERE statut='actif'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT ville) FROM ateliers WHERE ville IS NOT NULL")
    stats['villes'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT type) FROM ateliers WHERE type IS NOT NULL")
    stats['types'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(note_moyenne),0) FROM ateliers WHERE note_moyenne > 0")
    stats['note'] = cur.fetchone()[0]

    cards = ''
    for a in ateliers:
        initiales = (str(a['nom'] or '?')[:2]).upper()
        cards += '<div class="creation-card">'
        cards += '<div class="creation-icon" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)">🏢</div>'
        cards += '<div class="creation-body">'
        cards += '<div style="font-weight:900;color:#9d174d;font-size:15px;margin-bottom:4px">' + str(a["nom"]) + '</div>'
        cards += '<div style="font-size:11.5px;color:#64748b;margin-bottom:8px">' + str(a["type"] or "—") + ' · ' + str(a["ville"] or "") + '</div>'
        cards += '<div style="font-size:12px;color:#475569;margin-bottom:10px">' + str(a["specialite"] or "") + '</div>'
        cards += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;margin-bottom:10px">'
        cards += '<div>👗 ' + str(a["nb_creations"]) + ' créations</div>'
        cards += '<div>✂️ ' + str(a["nb_commandes_total"]) + ' commandes</div>'
        cards += '<div>⭐ ' + f'{a["note_moyenne"]:.1f}' + '</div>'
        cards += '<div>📞 ' + str(a["telephone"] or "") + '</div>'
        cards += '</div>'
        cards += '<a href="/ateliers/' + str(a["id"]) + '" class="btn btn-primary" style="padding:6px 10px;font-size:11.5px;width:100%;text-align:center;display:block">👁 Voir détails</a>'
        cards += '</div></div>'

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🏢 Ateliers & Maisons de couture — ' + str(len(ateliers)) + '</h1>'
    content += '<a href="/ateliers/nouveau" class="btn btn-primary">+ Nouvel atelier</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-icon">🏢</div><div class="kpi-label">Ateliers actifs</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🗺️</div><div class="kpi-label">Villes</div><div class="kpi-value">' + str(stats["villes"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">🎯</div><div class="kpi-label">Types</div><div class="kpi-value">' + str(stats["types"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">⭐</div><div class="kpi-label">Note moyenne</div><div class="kpi-value">' + f'{stats["note"]:.1f}' + '</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher atelier, spécialité, ville..." style="max-width:500px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px">' + (cards or '<p style="grid-column:1/-1;text-align:center;color:#94a3b8;padding:40px">Aucun atelier</p>') + '</div>'

    return render_page(content, active='ateliers', page_title='Ateliers')



@app.route('/ateliers/nouveau', methods=['GET', 'POST'])
@login_required
def ateliers_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO ateliers (code, nom, type, specialite, adresse, ville, region,
                                        telephone, email, responsable, site_web, instagram,
                                        note_moyenne, nb_commandes, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,0, 'actif', ?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('type'),
                  request.form.get('specialite'),
                  request.form.get('adresse'),
                  request.form.get('ville'),
                  request.form.get('region'),
                  request.form.get('telephone'),
                  request.form.get('email'),
                  request.form.get('responsable'),
                  request.form.get('site_web'),
                  request.form.get('instagram'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Atelier créé', 'success')
            return redirect('/ateliers')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>🏢 Nouvel atelier</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom *</label><input type="text" name="nom" required autofocus></div>'
    content += '<div><label>Type</label><select name="type">'
    for t in ['Haute couture', 'Costume', 'Prêt-à-porter', 'Wax & Bogolan', 'Traditionnel', 'Mariage', 'Sportswear']:
        content += '<option value="' + t + '">' + t + '</option>'
    content += '</select></div>'
    content += '<div><label>Spécialité</label><input type="text" name="specialite" placeholder="Boubous, robes de soirée..."></div>'
    content += '<div style="grid-column:1/-1"><label>Adresse</label><input type="text" name="adresse"></div>'
    content += '<div><label>Ville</label><input type="text" name="ville" value="Dakar"></div>'
    content += '<div><label>Région</label><input type="text" name="region" value="Dakar"></div>'
    content += '<div><label>Téléphone *</label><input type="text" name="telephone" required></div>'
    content += '<div><label>Email</label><input type="email" name="email"></div>'
    content += '<div><label>Responsable</label><input type="text" name="responsable"></div>'
    content += '<div><label>Site web</label><input type="text" name="site_web"></div>'
    content += '<div><label>Instagram</label><input type="text" name="instagram" placeholder="@atelier"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/ateliers" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='ateliers', page_title='Nouvel atelier')



@app.route('/ateliers/<int:aid>')
@login_required
def ateliers_detail(aid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM ateliers WHERE id=?", (aid,))
    a = cur.fetchone()
    if not a:
        flash('❌ Atelier introuvable', 'error')
        return redirect('/ateliers')

    cur.execute("""
        SELECT c.*, cat.icone AS cat_icone, cat.nom AS cat_nom
        FROM creations c
        LEFT JOIN categories cat ON cat.id=c.categorie_id
        WHERE c.atelier_id=?
        ORDER BY c.id DESC
    """, (aid,))
    creations = cur.fetchall()
    creations_html = ''
    for c in creations:
        creations_html += (
            '<tr><td>' + str(c["cat_icone"] or "👗") + ' <strong>' + str(c["nom"]) + '</strong></td>'
            + '<td>' + str(c["cat_nom"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{c["prix_vente"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center">' + ('✅' if c["disponible"] else '❌') + '</td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🏢 ' + str(a["nom"]) + '</h1>'
    content += '<a href="/ateliers" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-label">Code</div><div class="kpi-value" style="font-size:16px">' + str(a["code"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Créations</div><div class="kpi-value">' + str(len(creations)) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Note</div><div class="kpi-value">' + f'{a["note_moyenne"]:.1f}' + ' ⭐</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Commandes</div><div class="kpi-value">' + str(a["nb_commandes"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations</h2><table>'
    content += '<tr><td><strong>Type</strong></td><td>' + str(a["type"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Spécialité</strong></td><td>' + str(a["specialite"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Adresse</strong></td><td>' + str(a["adresse"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Ville</strong></td><td>' + str(a["ville"] or "—") + ', ' + str(a["region"] or "") + '</td></tr>'
    content += '<tr><td><strong>Téléphone</strong></td><td>' + str(a["telephone"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Email</strong></td><td>' + str(a["email"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Responsable</strong></td><td>' + str(a["responsable"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Site web</strong></td><td>' + str(a["site_web"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Instagram</strong></td><td>' + str(a["instagram"] or "—") + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>👗 Créations (' + str(len(creations)) + ')</h2>'
    content += '<table><thead><tr><th>Création</th><th>Catégorie</th><th style="text-align:right">Prix</th><th style="text-align:center">Dispo</th></tr></thead>'
    content += '<tbody>' + (creations_html or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucune création</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='ateliers', page_title='Atelier')


# ═══════════════════════════════════════════════════════════════
# 👗 CRÉATIONS / MODÈLES
# ═══════════════════════════════════════════════════════════════


@app.route('/creations')
@login_required
def creations_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()
    cat_f = request.args.get('categorie_id', '')

    sql = """
        SELECT c.*, cat.nom AS cat_nom, cat.icone AS cat_icone,
               a.nom AS atelier_nom
        FROM creations c
        LEFT JOIN categories cat ON cat.id=c.categorie_id
        LEFT JOIN ateliers a ON a.id=c.atelier_id
        WHERE 1=1
    """
    params = []
    if q:
        sql += " AND (c.nom LIKE ? OR c.description LIKE ? OR c.tissu_principal LIKE ?)"
        params += [f'%{q}%'] * 3
    if cat_f:
        sql += " AND c.categorie_id=?"
        params.append(cat_f)
    sql += " ORDER BY c.note_moyenne DESC, c.nom LIMIT 200"
    cur.execute(sql, params)
    creations = cur.fetchall()

    cur.execute("SELECT * FROM categories ORDER BY ordre")
    categories = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM creations WHERE disponible=1")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT categorie_id) FROM creations")
    stats['cats'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(prix_vente),0) FROM creations")
    stats['prix_moy'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(note_moyenne),0) FROM creations WHERE note_moyenne > 0")
    stats['note'] = cur.fetchone()[0]

    cards = ''
    for c in creations:
        icon = str(c['cat_icone'] or '👗')
        dispo_badge = '' if c['disponible'] else '<span class="badge badge-red">Indisponible</span>'
        cards += '<div class="creation-card">'
        cards += '<div class="creation-icon">' + icon + '</div>'
        cards += '<div class="creation-body">'
        cards += '<div style="font-weight:800;color:#1e293b;font-size:14px;margin-bottom:4px">' + str(c["nom"]) + '</div>'
        cards += '<div style="font-size:11.5px;color:#64748b;margin-bottom:8px">' + str(c["cat_nom"] or "—") + ' · ' + str(c["atelier_nom"] or "") + '</div>'
        cards += '<div style="font-size:12px;color:#475569;margin-bottom:10px">' + str(c["description"] or "")[:60] + '</div>'
        cards += '<div style="display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap">'
        cards += '<span class="badge badge-purple">' + str(c["tissu_principal"] or "—") + '</span>'
        if not c['disponible']:
            cards += '<span class="badge badge-gray">Indisponible</span>'
        cards += '</div>'
        cards += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'
        cards += '<div class="creation-price">' + f'{c["prix_vente"]:,.0f}' + ' F</div>'
        cards += '<div style="font-size:11.5px;color:#f59e0b">⭐ ' + f'{c["note_moyenne"]:.1f}' + '</div>'
        cards += '</div>'
        cards += '<a href="/creations/' + str(c["id"]) + '" class="btn btn-primary" style="padding:6px 10px;font-size:11.5px;width:100%;text-align:center;display:block">👁 Détails</a>'
        cards += '</div></div>'

    cats_html = '<a href="/creations" class="btn ' + ('btn-primary' if not cat_f else 'btn-secondary') + '">Toutes</a> '
    for cat in categories:
        active_cls = 'btn-primary' if str(cat_f) == str(cat['id']) else 'btn-secondary'
        cats_html += '<a href="/creations?categorie_id=' + str(cat["id"]) + '" class="btn ' + active_cls + '" style="margin-left:6px">' + str(cat["icone"] or "") + ' ' + str(cat["nom"]) + '</a> '

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👗 Créations — ' + str(len(creations)) + '</h1>'
    content += '<a href="/creations/nouvelle" class="btn btn-primary">+ Nouvelle création</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-icon">👗</div><div class="kpi-label">Créations</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🏷️</div><div class="kpi-label">Catégories</div><div class="kpi-value">' + str(stats["cats"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">Prix moyen</div><div class="kpi-value" style="font-size:16px">' + f'{stats["prix_moy"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">⭐</div><div class="kpi-label">Note moyenne</div><div class="kpi-value">' + f'{stats["note"]:.1f}' + '</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher création, tissu..." style="max-width:400px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="margin-bottom:20px;display:flex;gap:6px;flex-wrap:wrap">' + cats_html + '</div>'

    content += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px">' + (cards or '<p style="grid-column:1/-1;text-align:center;color:#94a3b8;padding:40px">Aucune création</p>') + '</div>'

    return render_page(content, active='creations', page_title='Créations')



@app.route('/creations/nouvelle', methods=['GET', 'POST'])
@login_required
def creations_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO creations (code, atelier_id, categorie_id, nom, description, type,
                                         prix_base, prix_vente, tissu_principal, temps_confection,
                                         niveau, disponible, note_moyenne, nb_commandes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,0,?)
            """, (None,
                  int(request.form.get('atelier_id') or 0) or None,
                  int(request.form.get('categorie_id') or 0) or None,
                  request.form.get('nom'),
                  request.form.get('description'),
                  request.form.get('type'),
                  float(request.form.get('prix_base') or 0),
                  float(request.form.get('prix_vente') or 0),
                  request.form.get('tissu_principal'),
                  int(request.form.get('temps_confection') or 7),
                  request.form.get('niveau') or 'standard',
                  1 if request.form.get('disponible') else 0,
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Création ajoutée', 'success')
            return redirect('/creations')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom FROM ateliers WHERE statut='actif' ORDER BY nom")
    ateliers = cur.fetchall()
    cur.execute("SELECT id, nom, icone FROM categories ORDER BY ordre")
    categories = cur.fetchall()

    opts_a = ''.join('<option value="' + str(a["id"]) + '">' + str(a["nom"]) + '</option>' for a in ateliers)
    opts_c = ''.join('<option value="' + str(c["id"]) + '">' + str(c["icone"] or "") + ' ' + str(c["nom"]) + '</option>' for c in categories)

    content = '<h1>👗 Nouvelle création</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom *</label><input type="text" name="nom" required autofocus></div>'
    content += '<div><label>Atelier</label><select name="atelier_id"><option value="">— Aucun —</option>' + opts_a + '</select></div>'
    content += '<div><label>Catégorie</label><select name="categorie_id"><option value="">— Aucune —</option>' + opts_c + '</select></div>'
    content += '<div><label>Type</label><input type="text" name="type" placeholder="boubou, robe, costume..."></div>'
    content += '<div><label>Tissu principal</label><input type="text" name="tissu_principal" placeholder="Wax, bazin, bogolan..."></div>'
    content += '<div style="grid-column:1/-1"><label>Description</label><textarea name="description" rows="3"></textarea></div>'
    content += '<div><label>Prix base (FCFA)</label><input type="number" step="1000" name="prix_base" value="25000"></div>'
    content += '<div><label>Prix vente (FCFA)</label><input type="number" step="1000" name="prix_vente" value="45000"></div>'
    content += '<div><label>Temps confection (jours)</label><input type="number" name="temps_confection" value="7"></div>'
    content += '<div><label>Niveau</label><select name="niveau">'
    content += '<option value="standard">Standard</option>'
    content += '<option value="premium">Premium</option>'
    content += '<option value="luxe">Luxe</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label><input type="checkbox" name="disponible" value="1" checked style="width:auto;margin-right:8px"> Disponible à la vente</label></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/creations" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='creations', page_title='Nouvelle création')



@app.route('/creations/<int:cid>')
@login_required
def creations_detail(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, cat.nom AS cat_nom, cat.icone AS cat_icone,
               a.nom AS atelier_nom, a.telephone AS atelier_tel, a.ville AS atelier_ville
        FROM creations c
        LEFT JOIN categories cat ON cat.id=c.categorie_id
        LEFT JOIN ateliers a ON a.id=c.atelier_id
        WHERE c.id=?
    """, (cid,))
    c = cur.fetchone()
    if not c:
        flash('❌ Création introuvable', 'error')
        return redirect('/creations')

    cur.execute("""
        SELECT av.*, cl.nom, cl.prenom FROM avis av
        LEFT JOIN clients cl ON cl.id=av.client_id
        WHERE av.atelier_id=?
        ORDER BY av.id DESC LIMIT 10
    """, (c['atelier_id'],))
    avis = cur.fetchall()
    avis_html = ''
    for a in avis:
        stars = '⭐' * (a['note'] or 0)
        avis_html += (
            '<tr><td>' + str(a["prenom"] or "") + ' ' + str(a["nom"] or "Client") + '</td>'
            + '<td style="color:#f59e0b">' + stars + '</td>'
            + '<td>' + str(a["commentaire"] or "") + '</td></tr>'
        )

    qr_url = '/creations/' + str(cid) + '/qr.png'

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">' + str(c["cat_icone"] or "👗") + ' ' + str(c["nom"]) + '</h1>'
    content += '<div>'
    content += '<a href="/commandes/nouvelle?creation_id=' + str(cid) + '" class="btn btn-gold">✂️ Commander</a> '
    content += '<a href="/creations" class="btn btn-secondary" style="margin-left:6px">← Retour</a></div></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-label">Code</div><div class="kpi-value" style="font-size:16px">' + str(c["code"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Prix</div><div class="kpi-value" style="font-size:18px">' + f'{c["prix_vente"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Confection</div><div class="kpi-value">' + str(c["temps_confection"]) + ' j</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Note</div><div class="kpi-value">' + f'{c["note_moyenne"]:.1f}' + ' ⭐</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:18px">'
    content += '<div class="card"><h2>📋 Détails</h2><table>'
    content += '<tr><td><strong>Catégorie</strong></td><td>' + str(c["cat_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Atelier</strong></td><td>' + str(c["atelier_nom"] or "—") + ' · ' + str(c["atelier_ville"] or "") + '</td></tr>'
    content += '<tr><td><strong>Tissu principal</strong></td><td>' + str(c["tissu_principal"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Niveau</strong></td><td>' + str(c["niveau"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Description</strong></td><td>' + str(c["description"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Disponible</strong></td><td>' + ('✅ Oui' if c["disponible"] else '❌ Non') + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card" style="text-align:center">'
    content += '<h2>🎫 QR Code</h2>'
    content += '<img src="' + qr_url + '" alt="QR" style="width:200px;height:200px;border:3px solid #db2777;border-radius:10px">'
    content += '<div style="margin-top:14px;font-size:12px;color:#64748b">Scannez pour vérifier l\'authenticité</div>'
    content += '</div>'
    content += '</div>'

    content += '<div class="card"><h2>⭐ Avis clients (' + str(len(avis)) + ')</h2>'
    content += '<table><thead><tr><th>Client</th><th>Note</th><th>Commentaire</th></tr></thead>'
    content += '<tbody>' + (avis_html or '<tr><td colspan="3" style="text-align:center;color:#94a3b8;padding:20px">Aucun avis</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='creations', page_title='Création')



@app.route('/creations/<int:cid>/qr.png')
def creations_qr(cid):
    import qrcode
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT code FROM creations WHERE id=?", (cid,))
    c = cur.fetchone()
    if not c:
        return redirect('/')
    qr_data = 'MODE|CREA|' + str(cid) + '|' + (c['code'] or '')
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#db2777', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


# ═══════════════════════════════════════════════════════════════
# 👥 CLIENTS
# ═══════════════════════════════════════════════════════════════


@app.route('/clients')
@login_required
def clients_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()
    pays_f = request.args.get('pays', '')

    sql = "SELECT * FROM clients WHERE 1=1"
    params = []
    if q:
        sql += " AND (nom LIKE ? OR prenom LIKE ? OR telephone LIKE ? OR code LIKE ?)"
        params += [f'%{q}%'] * 4
    if pays_f:
        sql += " AND pays=?"
        params.append(pays_f)
    sql += " ORDER BY id DESC LIMIT 300"
    cur.execute(sql, params)
    clients = cur.fetchall()

    cur.execute("SELECT DISTINCT pays FROM clients WHERE pays IS NOT NULL ORDER BY pays")
    pays_list = [r[0] for r in cur.fetchall()]

    stats = {}
    cur.execute("SELECT COUNT(*) FROM clients WHERE statut='actif'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM clients WHERE pays != 'Sénégal'")
    stats['diaspora'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(total_depense),0) FROM clients")
    stats['ca'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(total_depense),0) FROM clients WHERE nb_commandes > 0")
    stats['panier'] = cur.fetchone()[0]

    rows = ''
    for c in clients:
        sexe_icon = '👨' if c['sexe'] == 'M' else '👩' if c['sexe'] == 'F' else '👤'
        rows += (
            '<tr><td><strong style="color:#db2777">' + str(c["code"] or "—") + '</strong></td>'
            + '<td>' + sexe_icon + ' <strong>' + str(c["prenom"] or "") + ' ' + str(c["nom"]) + '</strong></td>'
            + '<td>' + str(c["telephone"] or "—") + '</td>'
            + '<td>' + str(c["ville"] or "—") + '<br><small style="color:#64748b">' + str(c["pays"] or "") + '</small></td>'
            + '<td style="text-align:center">' + str(c["nb_commandes"]) + '</td>'
            + '<td style="text-align:right">' + f'{c["total_depense"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center;color:#f59e0b;font-weight:800">' + str(c["points_fidelite"]) + '</td>'
            + '<td><a href="/clients/' + str(c["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👥 Clients — ' + str(len(clients)) + '</h1>'
    content += '<a href="/clients/nouveau" class="btn btn-primary">+ Nouveau client</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-icon">👥</div><div class="kpi-label">Clients actifs</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">🌍</div><div class="kpi-label">Diaspora</div><div class="kpi-value">' + str(stats["diaspora"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">CA total</div><div class="kpi-value" style="font-size:16px">' + f'{stats["ca"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🛒</div><div class="kpi-label">Panier moyen</div><div class="kpi-value" style="font-size:16px">' + f'{stats["panier"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher client..." style="max-width:500px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/clients" class="btn ' + ('btn-primary' if not pays_f else 'btn-secondary') + '">Tous pays</a> '
    for p in pays_list[:8]:
        active_cls = 'btn-primary' if pays_f == p else 'btn-secondary'
        content += '<a href="/clients?pays=' + p + '" class="btn ' + active_cls + '" style="margin-left:6px">' + p + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Nom</th><th>Téléphone</th><th>Localisation</th><th style="text-align:center">Cmd</th><th style="text-align:right">CA</th><th style="text-align:center">Points</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun client</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='clients', page_title='Clients')



@app.route('/clients/nouveau', methods=['GET', 'POST'])
@login_required
def clients_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO clients (code, nom, prenom, telephone, email, adresse, ville, pays,
                                       date_naissance, sexe, points_fidelite, nb_commandes,
                                       total_depense, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,0,0,0, 'actif', ?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('prenom'),
                  request.form.get('telephone'),
                  request.form.get('email'),
                  request.form.get('adresse'),
                  request.form.get('ville'),
                  request.form.get('pays') or 'Sénégal',
                  request.form.get('date_naissance'),
                  request.form.get('sexe') or 'M',
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Client créé', 'success')
            return redirect('/clients')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>👥 Nouveau client</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Nom *</label><input type="text" name="nom" required autofocus></div>'
    content += '<div><label>Prénom</label><input type="text" name="prenom"></div>'
    content += '<div><label>Téléphone *</label><input type="text" name="telephone" required placeholder="+221 77 XXX XX XX"></div>'
    content += '<div><label>Email</label><input type="email" name="email"></div>'
    content += '<div style="grid-column:1/-1"><label>Adresse</label><input type="text" name="adresse"></div>'
    content += '<div><label>Ville</label><input type="text" name="ville" value="Dakar"></div>'
    content += '<div><label>Pays</label><input type="text" name="pays" value="Sénégal"></div>'
    content += '<div><label>Date naissance</label><input type="date" name="date_naissance"></div>'
    content += '<div><label>Sexe</label><select name="sexe">'
    content += '<option value="M">Masculin</option>'
    content += '<option value="F">Féminin</option>'
    content += '</select></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/clients" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='clients', page_title='Nouveau client')



@app.route('/clients/<int:cid>')
@login_required
def clients_detail(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM clients WHERE id=?", (cid,))
    c = cur.fetchone()
    if not c:
        flash('❌ Client introuvable', 'error')
        return redirect('/clients')

    cur.execute("""
        SELECT m.*, a.nom AS atelier_nom FROM mesures m
        LEFT JOIN ateliers a ON a.id=m.atelier_id
        WHERE m.client_id=? AND m.actif=1
        ORDER BY m.id DESC
    """, (cid,))
    mesures = cur.fetchall()
    mesures_html = ''
    for m in mesures:
        mesures_html += (
            '<tr><td><strong>' + str(m["nom_mesure"] or "—") + '</strong></td>'
            + '<td>' + str(m["type_tenue"] or "—") + '</td>'
            + '<td style="text-align:center">' + f'{m["tour_poitrine"]:.1f}' + ' cm</td>'
            + '<td style="text-align:center">' + f'{m["tour_taille"]:.1f}' + ' cm</td>'
            + '<td style="text-align:center">' + f'{m["longueur_totale"]:.1f}' + ' cm</td>'
            + '<td>' + str((m["created_at"] or "")[:10]) + '</td></tr>'
        )

    cur.execute("""
        SELECT cmd.*, cr.nom AS creation_nom, at.nom AS atelier_nom
        FROM commandes cmd
        LEFT JOIN creations cr ON cr.id=cmd.creation_id
        LEFT JOIN ateliers at ON at.id=cmd.atelier_id
        WHERE cmd.client_id=?
        ORDER BY cmd.id DESC
    """, (cid,))
    commandes = cur.fetchall()
    cmd_html = ''
    for cmd in commandes:
        statut_badge = {'devis': 'badge-gray', 'confirmee': 'badge-blue', 'en_coupe': 'badge-orange', 'en_couture': 'badge-pink', 'finition': 'badge-purple', 'prete': 'badge-gold', 'livree': 'badge-green'}.get(cmd['statut'], 'badge-gray')
        cmd_html += (
            '<tr><td><strong>' + str(cmd["numero"]) + '</strong></td>'
            + '<td>' + str(cmd["creation_nom"] or "—") + '</td>'
            + '<td>' + str(cmd["atelier_nom"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{cmd["montant_ttc"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(cmd["statut"]) + '</span></td></tr>'
        )

    sexe_icon = '👨' if c['sexe'] == 'M' else '👩'

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">' + sexe_icon + ' ' + str(c["prenom"] or "") + ' ' + str(c["nom"]) + '</h1>'
    content += '<a href="/clients" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-label">Code</div><div class="kpi-value" style="font-size:16px">' + str(c["code"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Total dépensé</div><div class="kpi-value" style="font-size:16px">' + f'{c["total_depense"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Commandes</div><div class="kpi-value">' + str(c["nb_commandes"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Points fidélité</div><div class="kpi-value">' + str(c["points_fidelite"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations</h2><table>'
    content += '<tr><td><strong>Téléphone</strong></td><td>' + str(c["telephone"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Email</strong></td><td>' + str(c["email"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Adresse</strong></td><td>' + str(c["adresse"] or "—") + ', ' + str(c["ville"] or "") + '</td></tr>'
    content += '<tr><td><strong>Pays</strong></td><td>' + str(c["pays"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Date naissance</strong></td><td>' + str((c["date_naissance"] or "—")[:10]) + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>📏 Mesures (' + str(len(mesures)) + ')</h2>'
    content += '<table><thead><tr><th>Nom</th><th>Type</th><th style="text-align:center">Poitrine</th><th style="text-align:center">Taille</th><th style="text-align:center">Long. totale</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (mesures_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:20px">Aucune mesure</td></tr>') + '</tbody></table>'
    content += '<div style="margin-top:14px;text-align:right"><a href="/mesures/nouvelle?client_id=' + str(cid) + '" class="btn btn-primary">+ Nouvelle mesure</a></div></div>'

    content += '<div class="card"><h2>✂️ Commandes (' + str(len(commandes)) + ')</h2>'
    content += '<table><thead><tr><th>N°</th><th>Création</th><th>Atelier</th><th style="text-align:right">Montant</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (cmd_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucune commande</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='clients', page_title='Client')


# ═══════════════════════════════════════════════════════════════
# 📏 MESURES (AUTOMATISÉES)
# ═══════════════════════════════════════════════════════════════


@app.route('/mesures')
@login_required
def mesures_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT m.*, c.nom, c.prenom, c.code AS client_code, c.telephone
        FROM mesures m
        LEFT JOIN clients c ON c.id=m.client_id
        WHERE m.actif=1
        ORDER BY m.id DESC LIMIT 200
    """)
    mesures = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM mesures WHERE actif=1")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM mesures WHERE sexe='F'")
    stats['f'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM mesures WHERE sexe='M'")
    stats['m'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT client_id) FROM mesures")
    stats['clients'] = cur.fetchone()[0]

    rows = ''
    for m in mesures:
        sexe_icon = '👩' if m['sexe'] == 'F' else '👨'
        rows += (
            '<tr><td><strong style="color:#db2777">' + str(m["client_code"] or "—") + '</strong></td>'
            + '<td>' + sexe_icon + ' ' + str(m["prenom"] or "") + ' ' + str(m["nom"] or "") + '</td>'
            + '<td>' + str(m["nom_mesure"] or "—") + '<br><small style="color:#64748b">' + str(m["type_tenue"] or "") + '</small></td>'
            + '<td style="text-align:center">' + f'{m["tour_poitrine"]:.1f}' + '</td>'
            + '<td style="text-align:center">' + f'{m["tour_taille"]:.1f}' + '</td>'
            + '<td style="text-align:center">' + f'{m["longueur_totale"]:.1f}' + '</td>'
            + '<td style="text-align:center">' + f'{m["poids"]:.1f}' + ' kg</td>'
            + '<td><a href="/mesures/' + str(m["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📏 Mesures clients — ' + str(len(mesures)) + '</h1>'
    content += '<a href="/mesures/nouvelle" class="btn btn-primary">+ Nouvelle mesure</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-icon">📏</div><div class="kpi-label">Total mesures</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div class="kpi-icon">👩</div><div class="kpi-label">Femmes</div><div class="kpi-value">' + str(stats["f"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">👨</div><div class="kpi-label">Hommes</div><div class="kpi-value">' + str(stats["m"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">👥</div><div class="kpi-label">Clients</div><div class="kpi-value">' + str(stats["clients"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Client</th><th>Nom</th><th>Type</th><th style="text-align:center">Poitrine</th><th style="text-align:center">Taille</th><th style="text-align:center">Long.</th><th style="text-align:center">Poids</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucune mesure</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='mesures', page_title='Mesures')



@app.route('/mesures/nouvelle', methods=['GET', 'POST'])
@login_required
def mesures_nouvelle():
    db = get_db()
    cur = db.cursor()
    client_id_pre = int(request.args.get('client_id') or 0)

    if request.method == 'POST':
        try:
            # Auto-calcul optionnel depuis poids/taille si mesures partielles
            poids = float(request.form.get('poids') or 0)
            taille_cm = float(request.form.get('taille_cm') or 0)

            def num(k):
                return float(request.form.get(k) or 0)

            cur.execute("""
                INSERT INTO mesures (client_id, nom_mesure, sexe, type_tenue,
                                       tour_tete, tour_cou, tour_poitrine, tour_taille,
                                       tour_hanches, longueur_bras, longueur_epaule,
                                       tour_biceps, longueur_totale, longueur_jupe,
                                       longueur_pantalon, tour_cuisse, tour_genou,
                                       tour_mollet, pointure_chaussure, poids, taille_cm,
                                       notes, actif, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)
            """, (
                int(request.form.get('client_id') or 0),
                request.form.get('nom_mesure'),
                request.form.get('sexe') or 'M',
                request.form.get('type_tenue'),
                num('tour_tete'), num('tour_cou'), num('tour_poitrine'), num('tour_taille'),
                num('tour_hanches'), num('longueur_bras'), num('longueur_epaule'),
                num('tour_biceps'), num('longueur_totale'), num('longueur_jupe'),
                num('longueur_pantalon'), num('tour_cuisse'), num('tour_genou'),
                num('tour_mollet'), int(request.form.get('pointure_chaussure') or 0),
                poids, taille_cm,
                request.form.get('notes'),
                datetime.now().isoformat()))
            db.commit()
            log_action(current_user.id, 'CREATE_MESURE', 'Nouvelle mesure', 'mesures', cur.lastrowid)
            flash('✅ Mesures enregistrées', 'success')
            return redirect('/mesures')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom, prenom, code FROM clients WHERE statut='actif' ORDER BY nom")
    clients = cur.fetchall()
    opts = ''.join('<option value="' + str(c["id"]) + '"' + (' selected' if c["id"] == client_id_pre else '') + '>' + str(c["code"] or "") + ' — ' + str(c["prenom"] or "") + ' ' + str(c["nom"]) + '</option>' for c in clients)

    content = '<h1>📏 Nouvelles mesures</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Client *</label><select name="client_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts + '</select></div>'
    content += '<div><label>Nom de la mesure</label><input type="text" name="nom_mesure" placeholder="Tenue principale"></div>'
    content += '<div><label>Sexe</label><select name="sexe">'
    content += '<option value="M">Masculin</option>'
    content += '<option value="F">Féminin</option>'
    content += '</select></div>'
    content += '<div><label>Type de tenue</label><select name="type_tenue">'
    content += '<option value="boubou">Boubou</option>'
    content += '<option value="costume">Costume</option>'
    content += '<option value="robe">Robe</option>'
    content += '<option value="jupe">Jupe</option>'
    content += '<option value="ensemble">Ensemble</option>'
    content += '<option value="accessoire">Accessoire</option>'
    content += '</select></div>'
    content += '<div><label>Poids (kg)</label><input type="number" step="0.1" name="poids" value="0"></div>'
    content += '<div><label>Taille (cm)</label><input type="number" step="0.1" name="taille_cm" value="0"></div>'
    content += '<div><label>Tour tête (cm)</label><input type="number" step="0.1" name="tour_tete" value="0"></div>'
    content += '<div><label>Tour cou (cm)</label><input type="number" step="0.1" name="tour_cou" value="0"></div>'
    content += '<div><label>Tour poitrine (cm) *</label><input type="number" step="0.1" name="tour_poitrine" required value="0"></div>'
    content += '<div><label>Tour taille (cm) *</label><input type="number" step="0.1" name="tour_taille" required value="0"></div>'
    content += '<div><label>Tour hanches (cm)</label><input type="number" step="0.1" name="tour_hanches" value="0"></div>'
    content += '<div><label>Longueur bras (cm)</label><input type="number" step="0.1" name="longueur_bras" value="0"></div>'
    content += '<div><label>Longueur épaule (cm)</label><input type="number" step="0.1" name="longueur_epaule" value="0"></div>'
    content += '<div><label>Tour biceps (cm)</label><input type="number" step="0.1" name="tour_biceps" value="0"></div>'
    content += '<div><label>Longueur totale (cm) *</label><input type="number" step="0.1" name="longueur_totale" required value="0"></div>'
    content += '<div><label>Longueur jupe (cm)</label><input type="number" step="0.1" name="longueur_jupe" value="0"></div>'
    content += '<div><label>Longueur pantalon (cm)</label><input type="number" step="0.1" name="longueur_pantalon" value="0"></div>'
    content += '<div><label>Tour cuisse (cm)</label><input type="number" step="0.1" name="tour_cuisse" value="0"></div>'
    content += '<div><label>Tour genou (cm)</label><input type="number" step="0.1" name="tour_genou" value="0"></div>'
    content += '<div><label>Tour mollet (cm)</label><input type="number" step="0.1" name="tour_mollet" value="0"></div>'
    content += '<div><label>Pointure chaussure</label><input type="number" name="pointure_chaussure" value="0"></div>'
    content += '<div style="grid-column:1/-1"><label>Notes</label><textarea name="notes" rows="3"></textarea></div>'
    content += '</div>'
    content += '<div style="background:#fdf2f8;padding:12px;border-radius:8px;margin-top:16px;font-size:12.5px;color:#9d174d">'
    content += '💡 Toutes les mesures sont en centimètres. Poids en kg.'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Enregistrer</button>'
    content += '<a href="/mesures" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='mesures', page_title='Nouvelle mesure')



@app.route('/mesures/<int:mid>')
@login_required
def mesures_detail(mid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT m.*, c.nom, c.prenom, c.code AS client_code, c.telephone
        FROM mesures m
        LEFT JOIN clients c ON c.id=m.client_id
        WHERE m.id=?
    """, (mid,))
    m = cur.fetchone()
    if not m:
        flash('❌ Mesure introuvable', 'error')
        return redirect('/mesures')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📏 ' + str(m["nom_mesure"] or "Mesure") + '</h1>'
    content += '<a href="/mesures" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-label">Client</div><div class="kpi-value" style="font-size:15px">' + str(m["prenom"] or "") + ' ' + str(m["nom"] or "") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Type tenue</div><div class="kpi-value" style="font-size:16px">' + str(m["type_tenue"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Poids</div><div class="kpi-value" style="font-size:18px">' + f'{m["poids"]:.1f}' + ' kg</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Taille</div><div class="kpi-value" style="font-size:18px">' + f'{m["taille_cm"]:.0f}' + ' cm</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📏 Détail des mesures (cm)</h2><table>'
    rows_data = [
        ('Tour tête', m["tour_tete"]),
        ('Tour cou', m["tour_cou"]),
        ('Tour poitrine', m["tour_poitrine"]),
        ('Tour taille', m["tour_taille"]),
        ('Tour hanches', m["tour_hanches"]),
        ('Longueur bras', m["longueur_bras"]),
        ('Longueur épaule', m["longueur_epaule"]),
        ('Tour biceps', m["tour_biceps"]),
        ('Longueur totale', m["longueur_totale"]),
        ('Longueur jupe', m["longueur_jupe"]),
        ('Longueur pantalon', m["longueur_pantalon"]),
        ('Tour cuisse', m["tour_cuisse"]),
        ('Tour genou', m["tour_genou"]),
        ('Tour mollet', m["tour_mollet"]),
        ('Pointure chaussure', m["pointure_chaussure"]),
    ]
    for label, val in rows_data:
        content += '<tr><td><strong>' + label + '</strong></td><td style="text-align:right">' + f'{(val or 0):.1f}' + '</td></tr>'

    if m['notes']:
        content += '<tr><td><strong>Notes</strong></td><td>' + str(m["notes"]) + '</td></tr>'

    content += '</table></div>'

    return render_page(content, active='mesures', page_title='Détail mesure')


# ═══════════════════════════════════════════════════════════════
# ✂️ COMMANDES
# ═══════════════════════════════════════════════════════════════


@app.route('/commandes')
@login_required
def commandes_liste():
    db = get_db()
    cur = db.cursor()
    statut_f = request.args.get('statut', '')

    sql = """
        SELECT c.*, cl.nom AS client_nom, cl.prenom AS client_prenom, cl.telephone AS client_tel,
               a.nom AS atelier_nom, cr.nom AS creation_nom
        FROM commandes c
        LEFT JOIN clients cl ON cl.id=c.client_id
        LEFT JOIN ateliers a ON a.id=c.atelier_id
        LEFT JOIN creations cr ON cr.id=c.creation_id
        WHERE 1=1
    """
    params = []
    if statut_f:
        sql += " AND c.statut=?"
        params.append(statut_f)
    sql += " ORDER BY c.id DESC LIMIT 200"
    cur.execute(sql, params)
    commandes = cur.fetchall()

    stats = {}
    for k, s in [
        ('total', "SELECT COUNT(*) FROM commandes"),
        ('devis', "SELECT COUNT(*) FROM commandes WHERE statut='devis'"),
        ('encours', "SELECT COUNT(*) FROM commandes WHERE statut IN ('confirmee','en_coupe','en_couture','finition')"),
        ('livree', "SELECT COUNT(*) FROM commandes WHERE statut='livree'"),
    ]:
        cur.execute(s)
        stats[k] = cur.fetchone()[0]

    rows = ''
    for c in commandes:
        statut_badge = {'devis': 'badge-gray', 'confirmee': 'badge-blue', 'en_coupe': 'badge-orange', 'en_couture': 'badge-pink', 'finition': 'badge-purple', 'prete': 'badge-gold', 'livree': 'badge-green', 'annulee': 'badge-red'}.get(c['statut'], 'badge-gray')
        urgence_badge = '<span class="badge badge-red">🔥 Urgent</span>' if c['urgence'] == 'urgente' else ''
        rows += (
            '<tr><td><strong style="color:#db2777">' + str(c["numero"]) + '</strong></td>'
            + '<td>' + str(c["client_prenom"] or "") + ' ' + str(c["client_nom"] or "—") + '<br><small style="color:#64748b">' + str(c["client_tel"] or "") + '</small></td>'
            + '<td>' + str(c["creation_nom"] or "—") + '<br><small style="color:#64748b">' + str(c["atelier_nom"] or "") + '</small></td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{c["montant_ttc"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span> ' + urgence_badge + '</td>'
            + '<td>' + str((c["date_livraison_prevue"] or "—")[:10]) + '</td>'
            + '<td><a href="/commandes/' + str(c["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">✂️ Commandes de confection — ' + str(len(commandes)) + '</h1>'
    content += '<a href="/commandes/nouvelle" class="btn btn-primary">+ Nouvelle commande</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-icon">✂️</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#64748b,#475569)"><div class="kpi-icon">📝</div><div class="kpi-label">Devis</div><div class="kpi-value">' + str(stats["devis"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">🔧</div><div class="kpi-label">En cours</div><div class="kpi-value">' + str(stats["encours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Livrées</div><div class="kpi-value">' + str(stats["livree"]) + '</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/commandes" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Toutes</a> '
    for s in ['devis', 'confirmee', 'en_coupe', 'en_couture', 'finition', 'prete', 'livree']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/commandes?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N°</th><th>Client</th><th>Création</th><th style="text-align:right">Montant</th><th>Statut</th><th>Livraison</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucune commande</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='commandes', page_title='Commandes')



@app.route('/commandes/nouvelle', methods=['GET', 'POST'])
@login_required
def commandes_nouvelle():
    db = get_db()
    cur = db.cursor()
    creation_id_pre = int(request.args.get('creation_id') or 0)

    if request.method == 'POST':
        try:
            montant_ht = float(request.form.get('montant_ht') or 0)
            tva = montant_ht * 0.18
            montant_ttc = montant_ht + tva
            avance = float(request.form.get('avance') or 0)

            cur.execute("""
                INSERT INTO commandes (numero, client_id, atelier_id, creation_id, mesure_id,
                                         type, description, quantite, montant_ht, tva, montant_ttc,
                                         avance, reste, statut, urgence, date_commande,
                                         date_livraison_prevue, mode_paiement, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (None,
                  int(request.form.get('client_id') or 0),
                  int(request.form.get('atelier_id') or 0) or None,
                  int(request.form.get('creation_id') or 0) or None,
                  int(request.form.get('mesure_id') or 0) or None,
                  request.form.get('type') or 'sur_mesure',
                  request.form.get('description'),
                  int(request.form.get('quantite') or 1),
                  montant_ht, tva, montant_ttc,
                  avance, montant_ttc - avance,
                  request.form.get('statut') or 'devis',
                  request.form.get('urgence') or 'normale',
                  datetime.now().strftime('%Y-%m-%d'),
                  request.form.get('date_livraison_prevue'),
                  request.form.get('mode_paiement') or 'mobile_money',
                  request.form.get('notes'),
                  datetime.now().isoformat()))
            db.commit()
            log_action(current_user.id, 'CREATE_COMMANDE', 'Nouvelle commande', 'commandes', cur.lastrowid)
            flash('✅ Commande créée', 'success')
            return redirect('/commandes/' + str(cur.lastrowid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom, prenom, code FROM clients WHERE statut='actif' ORDER BY nom")
    clients = cur.fetchall()
    cur.execute("SELECT id, nom FROM ateliers WHERE statut='actif' ORDER BY nom")
    ateliers = cur.fetchall()
    cur.execute("SELECT id, nom, prix_vente FROM creations WHERE disponible=1 ORDER BY nom")
    creations = cur.fetchall()
    cur.execute("SELECT m.id, c.nom, c.prenom FROM mesures m LEFT JOIN clients c ON c.id=m.client_id WHERE m.actif=1 LIMIT 200")
    mesures = cur.fetchall()

    opts_cli = ''.join('<option value="' + str(c["id"]) + '">' + str(c["code"] or "") + ' — ' + str(c["prenom"] or "") + ' ' + str(c["nom"]) + '</option>' for c in clients)
    opts_atl = ''.join('<option value="' + str(a["id"]) + '">' + str(a["nom"]) + '</option>' for a in ateliers)
    opts_crea = ''.join('<option value="' + str(c["id"]) + '"' + (' selected' if c["id"] == creation_id_pre else '') + ' data-prix="' + str(c["prix_vente"]) + '">' + str(c["nom"]) + ' (' + f'{c["prix_vente"]:,.0f}' + ' F)</option>' for c in creations)
    opts_mes = ''.join('<option value="' + str(m["id"]) + '">' + str(m["prenom"] or "") + ' ' + str(m["nom"] or "") + '</option>' for m in mesures)

    content = '<h1>✂️ Nouvelle commande</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Client *</label><select name="client_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_cli + '</select></div>'
    content += '<div><label>Atelier</label><select name="atelier_id"><option value="">— Aucun —</option>' + opts_atl + '</select></div>'
    content += '<div><label>Création</label><select name="creation_id" id="creation_select" onchange="updatePrix()"><option value="">— Aucune —</option>' + opts_crea + '</select></div>'
    content += '<div><label>Mesure existante</label><select name="mesure_id"><option value="">— Aucune —</option>' + opts_mes + '</select></div>'
    content += '<div><label>Type</label><select name="type">'
    content += '<option value="sur_mesure">Sur mesure</option>'
    content += '<option value="pret_a_porter">Prêt-à-porter</option>'
    content += '</select></div>'
    content += '<div><label>Quantité</label><input type="number" name="quantite" value="1" min="1"></div>'
    content += '<div><label>Montant HT (FCFA) *</label><input type="number" step="1000" name="montant_ht" id="montant_ht" required value="45000"></div>'
    content += '<div><label>Avance (FCFA)</label><input type="number" step="1000" name="avance" value="0"></div>'
    content += '<div><label>Statut</label><select name="statut">'
    content += '<option value="devis">📝 Devis</option>'
    content += '<option value="confirmee">✅ Confirmée</option>'
    content += '<option value="en_coupe">✂️ En coupe</option>'
    content += '<option value="en_couture">🧵 En couture</option>'
    content += '<option value="finition">✨ Finition</option>'
    content += '<option value="prete">👌 Prête</option>'
    content += '</select></div>'
    content += '<div><label>Urgence</label><select name="urgence">'
    content += '<option value="normale">Normale</option>'
    content += '<option value="urgente">🔥 Urgente</option>'
    content += '</select></div>'
    content += '<div><label>Date livraison prévue</label><input type="date" name="date_livraison_prevue" value="' + (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Mode paiement</label><select name="mode_paiement">'
    content += '<option value="mobile_money">📱 Mobile Money</option>'
    content += '<option value="especes">💵 Espèces</option>'
    content += '<option value="virement">🏦 Virement</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Description</label><textarea name="description" rows="3"></textarea></div>'
    content += '<div style="grid-column:1/-1"><label>Notes</label><textarea name="notes" rows="2"></textarea></div>'
    content += '</div>'
    content += '<script>function updatePrix(){var s=document.getElementById("creation_select");var o=s.options[s.selectedIndex];if(o.dataset.prix)document.getElementById("montant_ht").value=Math.round(o.dataset.prix);}</script>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer la commande</button>'
    content += '<a href="/commandes" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='commandes', page_title='Nouvelle commande')



@app.route('/commandes/<int:cid>', methods=['GET', 'POST'])
@login_required
def commandes_detail(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, cl.nom AS client_nom, cl.prenom AS client_prenom, cl.telephone AS client_tel,
               cl.email AS client_email, cl.adresse AS client_adresse, cl.ville AS client_ville,
               a.nom AS atelier_nom, a.telephone AS atelier_tel,
               cr.nom AS creation_nom, cr.tissu_principal
        FROM commandes c
        LEFT JOIN clients cl ON cl.id=c.client_id
        LEFT JOIN ateliers a ON a.id=c.atelier_id
        LEFT JOIN creations cr ON cr.id=c.creation_id
        WHERE c.id=?
    """, (cid,))
    c = cur.fetchone()
    if not c:
        flash('❌ Commande introuvable', 'error')
        return redirect('/commandes')

    if request.method == 'POST':
        try:
            new_statut = request.form.get('statut') or c['statut']
            notes = request.form.get('notes') or c['notes'] or ''
            date_liv = datetime.now().strftime('%Y-%m-%d') if new_statut == 'livree' else c['date_livraison_reelle']
            cur.execute("UPDATE commandes SET statut=?, notes=?, date_livraison_reelle=? WHERE id=?",
                        (new_statut, notes, date_liv, cid))
            db.commit()
            flash('✅ Statut mis à jour : ' + new_statut, 'success')
            return redirect('/commandes/' + str(cid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    statut_badge = {'devis': 'badge-gray', 'confirmee': 'badge-blue', 'en_coupe': 'badge-orange', 'en_couture': 'badge-pink', 'finition': 'badge-purple', 'prete': 'badge-gold', 'livree': 'badge-green', 'annulee': 'badge-red'}.get(c['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">✂️ ' + str(c["numero"]) + ' <span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></h1>'
    content += '<div>'
    content += '<a href="/commandes/' + str(cid) + '/pdf" class="btn btn-gold">📄 PDF</a> '
    content += '<a href="/livraisons/nouvelle?commande_id=' + str(cid) + '" class="btn btn-primary">🚚 Livraison</a> '
    content += '<a href="/commandes" class="btn btn-secondary" style="margin-left:6px">← Retour</a></div></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-label">Client</div><div class="kpi-value" style="font-size:15px">' + str(c["client_prenom"] or "") + ' ' + str(c["client_nom"] or "") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Atelier</div><div class="kpi-value" style="font-size:15px">' + str(c["atelier_nom"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Montant TTC</div><div class="kpi-value" style="font-size:16px">' + f'{c["montant_ttc"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Reste à payer</div><div class="kpi-value" style="font-size:16px">' + f'{c["reste"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>👤 Client</h2><table>'
    content += '<tr><td><strong>Téléphone</strong></td><td>' + str(c["client_tel"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Email</strong></td><td>' + str(c["client_email"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Adresse</strong></td><td>' + str(c["client_adresse"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Ville</strong></td><td>' + str(c["client_ville"] or "—") + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>✂️ Détails commande</h2><table>'
    content += '<tr><td><strong>Création</strong></td><td>' + str(c["creation_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Tissu</strong></td><td>' + str(c["tissu_principal"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Quantité</strong></td><td>' + str(c["quantite"]) + '</td></tr>'
    content += '<tr><td><strong>Montant HT</strong></td><td>' + f'{c["montant_ht"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td><strong>TVA 18%</strong></td><td>' + f'{c["tva"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td><strong>Avance</strong></td><td>' + f'{c["avance"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td><strong>Date commande</strong></td><td>' + str((c["date_commande"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Livraison prévue</strong></td><td>' + str((c["date_livraison_prevue"] or "—")[:10]) + '</td></tr>'
    if c["date_livraison_reelle"]:
        content += '<tr><td><strong>Livraison réelle</strong></td><td>' + str(c["date_livraison_reelle"][:10]) + '</td></tr>'
    content += '</table></div>'
    content += '</div>'

    if c['description'] or c['notes']:
        content += '<div class="card"><h2>📝 Notes</h2>'
        if c['description']:
            content += '<div style="margin-bottom:12px"><strong>Description :</strong><br>' + str(c['description']) + '</div>'
        if c['notes']:
            content += '<div><strong>Notes :</strong><br>' + str(c['notes']) + '</div>'
        content += '</div>'

    content += '<div class="card"><h2>✏️ Mettre à jour le statut</h2>'
    content += '<form method="post">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Statut</label><select name="statut">'
    for st in ['devis', 'confirmee', 'en_coupe', 'en_couture', 'finition', 'prete', 'livree', 'annulee']:
        sel = ' selected' if c['statut'] == st else ''
        content += '<option value="' + st + '"' + sel + '>' + st + '</option>'
    content += '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Notes</label><textarea name="notes" rows="3">' + str(c["notes"] or "") + '</textarea></div>'
    content += '</div>'
    content += '<div style="margin-top:16px"><button type="submit" class="btn btn-success">💾 Mettre à jour</button></div>'
    content += '</form></div>'

    return render_page(content, active='commandes', page_title='Commande')


# ═══════════════════════════════════════════════════════════════
# 🧵 TISSUS & MATIÈRES
# ═══════════════════════════════════════════════════════════════


@app.route('/tissus')
@login_required
def tissus_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()

    sql = "SELECT * FROM tissus WHERE 1=1"
    params = []
    if q:
        sql += " AND (nom LIKE ? OR type LIKE ? OR couleur LIKE ?)"
        params += [f'%{q}%'] * 3
    sql += " ORDER BY nom"
    cur.execute(sql, params)
    tissus = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM tissus")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM tissus WHERE quantite_metres <= seuil_alerte")
    stats['alertes'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(quantite_metres * prix_metre),0) FROM tissus")
    stats['valeur'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(quantite_metres),0) FROM tissus")
    stats['metres'] = cur.fetchone()[0]

    rows = ''
    for t in tissus:
        is_alerte = t['quantite_metres'] <= t['seuil_alerte']
        bg = '#fef2f2' if is_alerte else '#fff'
        badge = '<span class="badge badge-red">⚠ ALERTE</span>' if is_alerte else '<span class="badge badge-green">OK</span>'
        rows += (
            '<tr style="background:' + bg + '">'
            + '<td><strong>' + str(t["nom"]) + '</strong></td>'
            + '<td>' + str(t["type"] or "—") + '</td>'
            + '<td>' + str(t["couleur"] or "—") + '<br><small style="color:#64748b">' + str(t["motif"] or "") + '</small></td>'
            + '<td style="text-align:right">' + f'{t["prix_metre"]:,.0f}' + ' F/m</td>'
            + '<td style="text-align:right">' + f'{t["quantite_metres"]:.1f}' + ' m</td>'
            + '<td style="text-align:right">' + f'{t["seuil_alerte"]:.1f}' + ' m</td>'
            + '<td style="text-align:right;font-weight:800">' + f'{t["quantite_metres"] * t["prix_metre"]:,.0f}' + ' F</td>'
            + '<td>' + badge + '</td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🧵 Tissus & matières — ' + str(len(tissus)) + '</h1>'
    content += '<a href="/tissus/nouveau" class="btn btn-primary">+ Nouveau tissu</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-icon">🧵</div><div class="kpi-label">Références</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">⚠️</div><div class="kpi-label">Alertes</div><div class="kpi-value">' + str(stats["alertes"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">📏</div><div class="kpi-label">Mètres total</div><div class="kpi-value" style="font-size:18px">' + f'{stats["metres"]:,.0f}' + ' m</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">💰</div><div class="kpi-label">Valeur</div><div class="kpi-value" style="font-size:16px">' + f'{stats["valeur"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher tissu..." style="max-width:400px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Nom</th><th>Type</th><th>Couleur/Motif</th><th style="text-align:right">Prix/m</th><th style="text-align:right">Stock</th><th style="text-align:right">Seuil</th><th style="text-align:right">Valeur</th><th>État</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun tissu</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='tissus', page_title='Tissus')



@app.route('/tissus/nouveau', methods=['GET', 'POST'])
@login_required
def tissus_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO tissus (code, nom, type, couleur, motif, fournisseur,
                                      pays_origine, prix_metre, quantite_metres,
                                      seuil_alerte, qualite, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?, 'disponible', ?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('type'),
                  request.form.get('couleur'),
                  request.form.get('motif'),
                  request.form.get('fournisseur'),
                  request.form.get('pays_origine') or 'Sénégal',
                  float(request.form.get('prix_metre') or 0),
                  float(request.form.get('quantite_metres') or 0),
                  float(request.form.get('seuil_alerte') or 0),
                  request.form.get('qualite') or 'standard',
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Tissu ajouté', 'success')
            return redirect('/tissus')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>🧵 Nouveau tissu</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom *</label><input type="text" name="nom" required autofocus placeholder="Wax hollandais"></div>'
    content += '<div><label>Type</label><select name="type">'
    for t in ['wax', 'bazin', 'bogolan', 'satin', 'soie', 'dentelle', 'laine', 'coton']:
        content += '<option value="' + t + '">' + t + '</option>'
    content += '</select></div>'
    content += '<div><label>Couleur</label><input type="text" name="couleur"></div>'
    content += '<div><label>Motif</label><input type="text" name="motif" placeholder="floral, uni, géométrique"></div>'
    content += '<div><label>Fournisseur</label><input type="text" name="fournisseur"></div>'
    content += '<div><label>Pays origine</label><input type="text" name="pays_origine" value="Sénégal"></div>'
    content += '<div><label>Prix/mètre (FCFA)</label><input type="number" step="100" name="prix_metre" value="5000"></div>'
    content += '<div><label>Quantité (mètres)</label><input type="number" step="0.1" name="quantite_metres" value="0"></div>'
    content += '<div><label>Seuil alerte (m)</label><input type="number" step="0.1" name="seuil_alerte" value="5"></div>'
    content += '<div><label>Qualité</label><select name="qualite">'
    content += '<option value="standard">Standard</option>'
    content += '<option value="premium">Premium</option>'
    content += '<option value="luxe">Luxe</option>'
    content += '</select></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/tissus" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='tissus', page_title='Nouveau tissu')


# ═══════════════════════════════════════════════════════════════
# 🎪 SALONS & EXPOSITIONS
# ═══════════════════════════════════════════════════════════════


@app.route('/salons')
@login_required
def salons_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.*,
               (SELECT COUNT(*) FROM stands WHERE salon_id=s.id) AS nb_stands_reserves,
               (SELECT COUNT(*) FROM billets WHERE salon_id=s.id AND statut='valide') AS nb_billets
        FROM salons s
        ORDER BY s.date_debut DESC
    """)
    salons = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM salons")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM salons WHERE statut='planifie'")
    stats['planifie'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM stands")
    stats['stands_reserves'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM billets WHERE statut='valide'")
    stats['billets'] = cur.fetchone()[0]

    cards = ''
    for s in salons:
        statut_badge = {'planifie': 'badge-blue', 'en_cours': 'badge-orange', 'termine': 'badge-gray', 'annule': 'badge-red'}.get(s['statut'], 'badge-gray')
        cards += '<div class="card" style="border-left-color:#db2777">'
        cards += '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">'
        cards += '<div><div style="font-weight:900;color:#9d174d;font-size:18px">🎪 ' + str(s["nom"]) + '</div>'
        cards += '<div style="font-size:13px;color:#64748b;margin-top:4px">📍 ' + str(s["lieu"] or "") + ', ' + str(s["ville"] or "") + ' (' + str(s["pays"] or "") + ')</div></div>'
        cards += '<span class="badge ' + statut_badge + '">' + str(s["statut"]) + '</span></div>'
        cards += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px;color:#475569;margin-bottom:12px">'
        cards += '<div>📅 ' + str((s["date_debut"] or "—")[:10]) + '</div>'
        cards += '<div>📅 ' + str((s["date_fin"] or "—")[:10]) + '</div>'
        cards += '<div>🏪 ' + str(s["nb_stands_reserves"]) + ' / ' + str(s["nb_stands_total"]) + ' stands</div>'
        cards += '<div>🎫 ' + str(s["nb_billets"]) + ' billets vendus</div>'
        cards += '</div>'
        cards += '<div style="display:flex;gap:6px">'
        cards += '<a href="/salons/' + str(s["id"]) + '" class="btn btn-primary" style="padding:6px 10px;font-size:12px;flex:1;text-align:center">👁 Détails</a>'
        cards += '<a href="/billets/nouveau?salon_id=' + str(s["id"]) + '" class="btn btn-gold" style="padding:6px 10px;font-size:12px;flex:1;text-align:center">🎫 Billetterie</a>'
        cards += '</div></div>'

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🎪 Salons & Expositions — ' + str(len(salons)) + '</h1>'
    content += '<a href="/salons/nouveau" class="btn btn-primary">+ Nouveau salon</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-icon">🎪</div><div class="kpi-label">Total salons</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">📅</div><div class="kpi-label">Planifiés</div><div class="kpi-value">' + str(stats["planifie"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🏪</div><div class="kpi-label">Stands réservés</div><div class="kpi-value">' + str(stats["stands_reserves"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">🎫</div><div class="kpi-label">Billets vendus</div><div class="kpi-value">' + str(stats["billets"]) + '</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:16px">' + (cards or '<p style="grid-column:1/-1;text-align:center;color:#94a3b8;padding:40px">Aucun salon</p>') + '</div>'

    return render_page(content, active='salons', page_title='Salons')



@app.route('/salons/nouveau', methods=['GET', 'POST'])
@login_required
def salons_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            nb_stands = int(request.form.get('nb_stands_total') or 0)
            cur.execute("""
                INSERT INTO salons (code, nom, ville, pays, lieu, date_debut, date_fin,
                                      description, site_web, organisateur, contact,
                                      telephone, email, nb_stands_total, nb_stands_dispo,
                                      tarif_stand, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'planifie', ?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('ville'),
                  request.form.get('pays') or 'Sénégal',
                  request.form.get('lieu'),
                  request.form.get('date_debut'),
                  request.form.get('date_fin'),
                  request.form.get('description'),
                  request.form.get('site_web'),
                  request.form.get('organisateur'),
                  request.form.get('contact'),
                  request.form.get('telephone'),
                  request.form.get('email'),
                  nb_stands, nb_stands,
                  float(request.form.get('tarif_stand') or 0),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Salon créé', 'success')
            return redirect('/salons')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>🎪 Nouveau salon</h1>'
    content += '<form method="post" class="card" style="max-width:900px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom *</label><input type="text" name="nom" required autofocus placeholder="Dakar Fashion Week 2026"></div>'
    content += '<div><label>Ville *</label><input type="text" name="ville" required value="Dakar"></div>'
    content += '<div><label>Pays</label><input type="text" name="pays" value="Sénégal"></div>'
    content += '<div style="grid-column:1/-1"><label>Lieu</label><input type="text" name="lieu" placeholder="Monument Renaissance"></div>'
    content += '<div><label>Date début *</label><input type="date" name="date_debut" required value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Date fin *</label><input type="date" name="date_fin" required value="' + (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d') + '"></div>'
    content += '<div style="grid-column:1/-1"><label>Description</label><textarea name="description" rows="3"></textarea></div>'
    content += '<div><label>Site web</label><input type="text" name="site_web"></div>'
    content += '<div><label>Organisateur</label><input type="text" name="organisateur"></div>'
    content += '<div><label>Contact</label><input type="text" name="contact"></div>'
    content += '<div><label>Téléphone</label><input type="text" name="telephone"></div>'
    content += '<div><label>Email</label><input type="email" name="email"></div>'
    content += '<div><label>Nb stands total</label><input type="number" name="nb_stands_total" value="50"></div>'
    content += '<div><label>Tarif stand (FCFA)</label><input type="number" step="10000" name="tarif_stand" value="250000"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/salons" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='salons', page_title='Nouveau salon')



@app.route('/salons/<int:sid>')
@login_required
def salons_detail(sid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM salons WHERE id=?", (sid,))
    s = cur.fetchone()
    if not s:
        flash('❌ Salon introuvable', 'error')
        return redirect('/salons')

    cur.execute("""
        SELECT st.*, a.nom AS atelier_nom, a.ville
        FROM stands st
        LEFT JOIN ateliers a ON a.id=st.atelier_id
        WHERE st.salon_id=?
        ORDER BY st.numero_stand
    """, (sid,))
    stands = cur.fetchall()
    stands_html = ''
    for st in stands:
        stands_html += (
            '<tr><td><strong>' + str(st["numero_stand"]) + '</strong></td>'
            + '<td>' + str(st["atelier_nom"] or "—") + '</td>'
            + '<td>' + str(st["ville"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{st["superficie"]:.0f}' + ' m²</td>'
            + '<td style="text-align:right">' + f'{st["tarif"]:,.0f}' + ' F</td>'
            + '<td><span class="badge badge-green">' + str(st["statut"]) + '</span></td></tr>'
        )

    cur.execute("""
        SELECT b.*, c.nom AS client_nom, c.prenom AS client_prenom
        FROM billets b
        LEFT JOIN clients c ON c.id=b.client_id
        WHERE b.salon_id=?
        ORDER BY b.id DESC
    """, (sid,))
    billets = cur.fetchall()
    billets_html = ''
    for b in billets:
        billets_html += (
            '<tr><td><strong>' + str(b["numero"]) + '</strong></td>'
            + '<td>' + str(b["prenom"] or "") + ' ' + str(b["nom"] or "—") + '</td>'
            + '<td>' + str(b["type_billet"]) + '</td>'
            + '<td style="text-align:right">' + f'{b["prix"]:,.0f}' + ' F</td>'
            + '<td><span class="badge badge-green">' + str(b["statut"]) + '</span></td>'
            + '<td><a href="/billets/' + str(b["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    statut_badge = {'planifie': 'badge-blue', 'en_cours': 'badge-orange', 'termine': 'badge-gray'}.get(s['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🎪 ' + str(s["nom"]) + ' <span class="badge ' + statut_badge + '">' + str(s["statut"]) + '</span></h1>'
    content += '<a href="/salons" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-label">Dates</div><div class="kpi-value" style="font-size:14px">' + str((s["date_debut"] or "")[:10]) + ' → ' + str((s["date_fin"] or "")[:10]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Stands réservés</div><div class="kpi-value">' + str(len(stands)) + '/' + str(s["nb_stands_total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Billets vendus</div><div class="kpi-value">' + str(len(billets)) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Tarif stand</div><div class="kpi-value" style="font-size:16px">' + f'{s["tarif_stand"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations</h2><table>'
    content += '<tr><td><strong>Lieu</strong></td><td>' + str(s["lieu"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Ville</strong></td><td>' + str(s["ville"] or "—") + ', ' + str(s["pays"] or "") + '</td></tr>'
    content += '<tr><td><strong>Organisateur</strong></td><td>' + str(s["organisateur"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Contact</strong></td><td>' + str(s["contact"] or "—") + ' · ' + str(s["telephone"] or "") + '</td></tr>'
    content += '<tr><td><strong>Email</strong></td><td>' + str(s["email"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Site web</strong></td><td>' + str(s["site_web"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Description</strong></td><td>' + str(s["description"] or "—") + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>🏪 Stands réservés (' + str(len(stands)) + ')</h2>'
    content += '<table><thead><tr><th>N° Stand</th><th>Atelier</th><th>Ville</th><th style="text-align:right">Superficie</th><th style="text-align:right">Tarif</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (stands_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:20px">Aucun stand réservé</td></tr>') + '</tbody></table>'
    content += '<div style="margin-top:14px;text-align:right"><a href="/stands/nouveau?salon_id=' + str(sid) + '" class="btn btn-primary">+ Réserver un stand</a></div></div>'

    content += '<div class="card"><h2>🎫 Billets vendus (' + str(len(billets)) + ')</h2>'
    content += '<table><thead><tr><th>N°</th><th>Client</th><th>Type</th><th style="text-align:right">Prix</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (billets_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:20px">Aucun billet vendu</td></tr>') + '</tbody></table>'
    content += '<div style="margin-top:14px;text-align:right"><a href="/billets/nouveau?salon_id=' + str(sid) + '" class="btn btn-gold">🎫 Vendre un billet</a></div></div>'

    return render_page(content, active='salons', page_title='Salon')



@app.route('/stands/nouveau', methods=['GET', 'POST'])
@login_required
def stands_nouveau():
    db = get_db()
    cur = db.cursor()
    salon_id_pre = int(request.args.get('salon_id') or 0)

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO stands (salon_id, atelier_id, numero_stand, superficie, tarif,
                                      statut, date_reservation, created_at)
                VALUES (?,?,?,?,?, 'reserve', ?, ?)
            """, (int(request.form.get('salon_id') or 0),
                  int(request.form.get('atelier_id') or 0),
                  request.form.get('numero_stand'),
                  float(request.form.get('superficie') or 0),
                  float(request.form.get('tarif') or 0),
                  datetime.now().strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))

            # MAJ compteur stands dispo
            cur.execute("UPDATE salons SET nb_stands_dispo = nb_stands_dispo - 1 WHERE id=?",
                        (int(request.form.get('salon_id') or 0),))
            db.commit()
            flash('✅ Stand réservé', 'success')
            return redirect('/salons/' + request.form.get('salon_id'))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom, tarif_stand FROM salons WHERE statut='planifie' ORDER BY date_debut DESC")
    salons = cur.fetchall()
    cur.execute("SELECT id, nom FROM ateliers WHERE statut='actif' ORDER BY nom")
    ateliers = cur.fetchall()

    opts_s = ''.join('<option value="' + str(s["id"]) + '"' + (' selected' if s["id"] == salon_id_pre else '') + ' data-tarif="' + str(s["tarif_stand"]) + '">' + str(s["nom"]) + '</option>' for s in salons)
    opts_a = ''.join('<option value="' + str(a["id"]) + '">' + str(a["nom"]) + '</option>' for a in ateliers)

    content = '<h1>🏪 Réserver un stand</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="margin-bottom:16px"><label>Salon *</label><select name="salon_id" required id="salon_select" onchange="updateTarif()">'
    content += '<option value="">— Sélectionner —</option>' + opts_s + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Atelier *</label><select name="atelier_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_a + '</select></div>'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>N° Stand</label><input type="text" name="numero_stand" placeholder="A-12"></div>'
    content += '<div><label>Superficie (m²)</label><input type="number" step="0.1" name="superficie" value="12"></div>'
    content += '</div>'
    content += '<div style="margin-top:16px"><label>Tarif (FCFA)</label><input type="number" step="10000" name="tarif" id="tarif" value="250000"></div>'
    content += '<script>function updateTarif(){var s=document.getElementById("salon_select");var o=s.options[s.selectedIndex];if(o.dataset.tarif)document.getElementById("tarif").value=Math.round(o.dataset.tarif);}</script>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Réserver</button>'
    content += '<a href="/salons" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='salons', page_title='Réserver stand')


# ═══════════════════════════════════════════════════════════════
# 🎫 BILLETS SALON (QR)
# ═══════════════════════════════════════════════════════════════


@app.route('/billets')
@login_required
def billets_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT b.*, s.nom AS salon_nom, s.date_debut,
               c.nom AS client_nom, c.prenom AS client_prenom
        FROM billets b
        LEFT JOIN salons s ON s.id=b.salon_id
        LEFT JOIN clients c ON c.id=b.client_id
        ORDER BY b.id DESC LIMIT 200
    """)
    billets = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM billets WHERE statut='valide'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM billets WHERE type_billet='VIP'")
    stats['vip'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(prix),0) FROM billets WHERE statut='valide'")
    stats['ca'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT salon_id) FROM billets")
    stats['salons'] = cur.fetchone()[0]

    rows = ''
    for b in billets:
        type_badge = {'standard': 'badge-gray', 'VIP': 'badge-gold', 'presse': 'badge-blue', 'etudiant': 'badge-green'}.get(b['type_billet'], 'badge-gray')
        rows += (
            '<tr><td><strong style="color:#db2777">' + str(b["numero"]) + '</strong></td>'
            + '<td>' + str(b["salon_nom"] or "—") + '<br><small style="color:#64748b">' + str((b["date_debut"] or "")[:10]) + '</small></td>'
            + '<td>' + str(b["prenom"] or "") + ' ' + str(b["nom"] or "—") + '</td>'
            + '<td><span class="badge ' + type_badge + '">' + str(b["type_billet"]) + '</span></td>'
            + '<td style="text-align:right;font-weight:800">' + f'{b["prix"]:,.0f}' + ' F</td>'
            + '<td><span class="badge badge-green">' + str(b["statut"]) + '</span></td>'
            + '<td><a href="/billets/' + str(b["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🎫 Billets salons — ' + str(len(billets)) + '</h1>'
    content += '<a href="/billets/nouveau" class="btn btn-primary">+ Nouveau billet</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-icon">🎫</div><div class="kpi-label">Billets valides</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">👑</div><div class="kpi-label">VIP</div><div class="kpi-value">' + str(stats["vip"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">CA billetterie</div><div class="kpi-value" style="font-size:16px">' + f'{stats["ca"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🎪</div><div class="kpi-label">Salons</div><div class="kpi-value">' + str(stats["salons"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N°</th><th>Salon</th><th>Client</th><th>Type</th><th style="text-align:right">Prix</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#94a3b8">Aucun billet</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='billets', page_title='Billets')



@app.route('/billets/nouveau', methods=['GET', 'POST'])
@login_required
def billets_nouveau():
    db = get_db()
    cur = db.cursor()
    salon_id_pre = int(request.args.get('salon_id') or 0)

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO billets (numero, salon_id, client_id, type_billet, prix,
                                       date_achat, statut, created_at)
                VALUES (?,?,?,?,?,?, 'valide', ?)
            """, (None,
                  int(request.form.get('salon_id') or 0),
                  int(request.form.get('client_id') or 0) or None,
                  request.form.get('type_billet') or 'standard',
                  float(request.form.get('prix') or 0),
                  datetime.now().strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Billet émis', 'success')
            return redirect('/billets')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom FROM salons WHERE statut IN ('planifie','en_cours') ORDER BY date_debut DESC")
    salons = cur.fetchall()
    cur.execute("SELECT id, nom, prenom FROM clients WHERE statut='actif' ORDER BY nom LIMIT 500")
    clients = cur.fetchall()

    opts_s = ''.join('<option value="' + str(s["id"]) + '"' + (' selected' if s["id"] == salon_id_pre else '') + '>' + str(s["nom"]) + '</option>' for s in salons)
    opts_c = ''.join('<option value="' + str(c["id"]) + '">' + str(c["prenom"] or "") + ' ' + str(c["nom"]) + '</option>' for c in clients)

    content = '<h1>🎫 Nouveau billet</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="margin-bottom:16px"><label>Salon *</label><select name="salon_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_s + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Client</label><select name="client_id">'
    content += '<option value="">— Aucun —</option>' + opts_c + '</select></div>'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Type billet</label><select name="type_billet">'
    content += '<option value="standard">🎫 Standard</option>'
    content += '<option value="VIP">👑 VIP</option>'
    content += '<option value="presse">📰 Presse</option>'
    content += '<option value="etudiant">🎓 Étudiant</option>'
    content += '</select></div>'
    content += '<div><label>Prix (FCFA)</label><input type="number" step="1000" name="prix" value="10000"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Émettre le billet</button>'
    content += '<a href="/billets" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='billets', page_title='Nouveau billet')



@app.route('/billets/<int:bid>')
@login_required
def billets_detail(bid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT b.*, s.nom AS salon_nom, s.lieu, s.ville, s.date_debut, s.date_fin,
               c.nom AS client_nom, c.prenom AS client_prenom, c.telephone
        FROM billets b
        LEFT JOIN salons s ON s.id=b.salon_id
        LEFT JOIN clients c ON c.id=b.client_id
        WHERE b.id=?
    """, (bid,))
    b = cur.fetchone()
    if not b:
        flash('❌ Billet introuvable', 'error')
        return redirect('/billets')

    qr_url = '/billets/' + str(bid) + '/qr.png'

    content = '<div style="max-width:500px;margin:0 auto">'
    content += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">'
    content += '<a href="/billets" class="btn btn-secondary">← Retour</a>'
    content += '<a href="/billets/' + str(bid) + '/pdf" class="btn btn-gold">📄 PDF</a></div>'

    content += '<div style="background:linear-gradient(135deg,#db2777,#9d174d);color:#fff;border-radius:16px;padding:26px;box-shadow:0 10px 30px rgba(0,0,0,.15)">'
    content += '<div style="text-align:center;margin-bottom:20px">'
    content += '<div style="font-size:11px;opacity:.85;letter-spacing:3px;font-weight:600">OMEGA MODE</div>'
    content += '<div style="font-size:22px;font-weight:900;margin-top:6px">🎫 BILLET SALON</div>'
    content += '<div style="height:3px;background:#f59e0b;width:60px;margin:12px auto"></div>'
    content += '</div>'

    content += '<div style="background:rgba(255,255,255,.95);color:#1e293b;border-radius:12px;padding:18px">'
    content += '<div style="text-align:center;margin-bottom:16px">'
    content += '<img src="' + qr_url + '" alt="QR" style="width:150px;height:150px;border:3px solid #db2777;border-radius:10px">'
    content += '<div style="font-size:11px;color:#64748b;margin-top:6px;font-weight:700">SCANNER POUR VÉRIFIER</div>'
    content += '</div>'

    content += '<table style="width:100%;font-size:13px">'
    content += '<tr><td style="padding:6px 0;color:#64748b">N° billet</td><td style="text-align:right;font-weight:800;color:#db2777">' + str(b["numero"]) + '</td></tr>'
    content += '<tr><td style="padding:6px 0;color:#64748b">Salon</td><td style="text-align:right;font-weight:700">' + str(b["salon_nom"]) + '</td></tr>'
    content += '<tr><td style="padding:6px 0;color:#64748b">Lieu</td><td style="text-align:right">' + str(b["lieu"] or "") + ', ' + str(b["ville"] or "") + '</td></tr>'
    content += '<tr><td style="padding:6px 0;color:#64748b">Dates</td><td style="text-align:right">' + str((b["date_debut"] or "")[:10]) + ' → ' + str((b["date_fin"] or "")[:10]) + '</td></tr>'
    content += '<tr><td style="padding:6px 0;color:#64748b">Client</td><td style="text-align:right">' + str(b["prenom"] or "") + ' ' + str(b["nom"] or "") + '</td></tr>'
    content += '<tr><td style="padding:6px 0;color:#64748b">Type</td><td style="text-align:right"><strong>' + str(b["type_billet"]) + '</strong></td></tr>'
    content += '<tr><td style="padding:6px 0;color:#64748b">Prix</td><td style="text-align:right;font-weight:900;color:#10b981;font-size:16px">' + f'{b["prix"]:,.0f}' + ' FCFA</td></tr>'
    content += '</table>'
    content += '</div>'

    content += '<div style="text-align:center;margin-top:16px;font-size:10.5px;opacity:.85;letter-spacing:1px">'
    content += 'COUTURE · CEDEAO · EXPORT UE'
    content += '</div></div></div>'

    return render_page(content, active='billets', page_title='Billet')



@app.route('/billets/<int:bid>/qr.png')
def billets_qr(bid):
    import qrcode
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT numero FROM billets WHERE id=?", (bid,))
    b = cur.fetchone()
    if not b:
        return redirect('/')
    qr_data = 'MODE|BIL|' + str(bid) + '|' + (b['numero'] or '')
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#db2777', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')



@app.route('/billets/<int:bid>/pdf')
@login_required
def billets_pdf(bid):
    from reportlab.lib.pagesizes import A6
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    import qrcode

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT b.*, s.nom AS salon_nom, s.lieu, s.ville, s.date_debut, s.date_fin,
               c.nom AS client_nom, c.prenom AS client_prenom
        FROM billets b
        LEFT JOIN salons s ON s.id=b.salon_id
        LEFT JOIN clients c ON c.id=b.client_id
        WHERE b.id=?
    """, (bid,))
    b = cur.fetchone()
    if not b:
        flash('❌ Billet introuvable', 'error')
        return redirect('/billets')

    qr = qrcode.make('MODE|BIL|' + str(bid) + '|' + str(b['numero']))
    qr_buf = io.BytesIO()
    qr.save(qr_buf, format='PNG')
    qr_buf.seek(0)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A6)
    w, h = A6

    c.setFillColor(colors.HexColor('#db2777'))
    c.rect(0, h - 30*mm, w, 30*mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#f59e0b'))
    c.rect(0, h - 30*mm, w, 3*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(8*mm, h - 12*mm, 'OMEGA MODE')
    c.setFont('Helvetica', 8)
    c.drawString(8*mm, h - 17*mm, 'BILLET SALON')
    c.setFont('Helvetica-Bold', 10)
    c.drawRightString(w - 8*mm, h - 12*mm, str(b['numero']))

    y = h - 42*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(8*mm, y, str(b['salon_nom'] or ''))
    y -= 6*mm
    c.setFont('Helvetica', 9)
    c.drawString(8*mm, y, str(b['lieu'] or '') + ', ' + str(b['ville'] or ''))
    y -= 5*mm
    c.drawString(8*mm, y, str((b['date_debut'] or '')[:10]) + ' -> ' + str((b['date_fin'] or '')[:10]))

    y -= 10*mm
    c.setFont('Helvetica', 9)
    c.drawString(8*mm, y, 'Client : ' + str(b['prenom'] or '') + ' ' + str(b['nom'] or ''))
    y -= 5*mm
    c.drawString(8*mm, y, 'Type : ' + str(b['type_billet'] or ''))
    y -= 5*mm
    c.setFont('Helvetica-Bold', 12)
    c.setFillColor(colors.HexColor('#10b981'))
    c.drawString(8*mm, y, f"{b['prix']:,.0f} FCFA")

    qr_size = 32*mm
    c.drawImage(qr_buf, w - qr_size - 10*mm, 20*mm, qr_size, qr_size)

    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica', 7)
    c.drawString(8*mm, 12*mm, 'Scanner le QR pour vérifier · OMEGA Mode CEDEAO')

    c.showPage()
    c.save()
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf',
                     download_name='billet_' + str(b['numero']) + '.pdf')


# ═══════════════════════════════════════════════════════════════
# 🚚 LIVRAISONS
# ═══════════════════════════════════════════════════════════════


@app.route('/livraisons')
@login_required
def livraisons_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT l.*, c.numero AS commande_numero,
               cl.nom AS client_nom, cl.prenom AS client_prenom
        FROM livraisons l
        LEFT JOIN commandes c ON c.id=l.commande_id
        LEFT JOIN clients cl ON cl.id=c.client_id
        ORDER BY l.id DESC LIMIT 200
    """)
    livraisons = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM livraisons")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM livraisons WHERE statut='prepare'")
    stats['prep'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM livraisons WHERE statut='expedie'")
    stats['exp'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM livraisons WHERE statut='livre'")
    stats['liv'] = cur.fetchone()[0]

    rows = ''
    for l in livraisons:
        statut_badge = {'prepare': 'badge-gray', 'expedie': 'badge-orange', 'livre': 'badge-green', 'retour': 'badge-red'}.get(l['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong style="color:#db2777">' + str(l["numero"]) + '</strong></td>'
            + '<td>' + str(l["commande_numero"] or "—") + '</td>'
            + '<td>' + str(l["prenom"] or "") + ' ' + str(l["nom"] or "—") + '</td>'
            + '<td>' + str(l["ville"] or "—") + ', ' + str(l["pays"] or "") + '</td>'
            + '<td>' + str(l["transporteur"] or "—") + '</td>'
            + '<td>' + str((l["date_expedition"] or "—")[:10]) + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(l["statut"]) + '</span></td>'
            + '<td><a href="/livraisons/' + str(l["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🚚 Livraisons — ' + str(len(livraisons)) + '</h1>'
    content += '<a href="/livraisons/nouvelle" class="btn btn-primary">+ Nouvelle livraison</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-icon">🚚</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#64748b,#475569)"><div class="kpi-icon">📦</div><div class="kpi-label">Préparées</div><div class="kpi-value">' + str(stats["prep"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">🚛</div><div class="kpi-label">Expédiées</div><div class="kpi-value">' + str(stats["exp"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Livrées</div><div class="kpi-value">' + str(stats["liv"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N°</th><th>Commande</th><th>Client</th><th>Destination</th><th>Transporteur</th><th>Expédition</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucune livraison</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='livraisons', page_title='Livraisons')



@app.route('/livraisons/nouvelle', methods=['GET', 'POST'])
@login_required
def livraisons_nouvelle():
    db = get_db()
    cur = db.cursor()
    commande_id_pre = int(request.args.get('commande_id') or 0)

    if request.method == 'POST':
        try:
            cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM livraisons")
            nid = cur.fetchone()[0]
            numero = 'LIV-' + datetime.now().strftime('%Y%m%d') + '-' + f'{nid:04d}'

            cur.execute("""
                INSERT INTO livraisons (numero, commande_id, type, adresse_livraison, ville, pays,
                                          transporteur, numero_suivi, date_expedition,
                                          date_livraison_prevue, statut, frais_livraison,
                                          notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (numero,
                  int(request.form.get('commande_id') or 0) or None,
                  request.form.get('type') or 'domicile',
                  request.form.get('adresse_livraison'),
                  request.form.get('ville'),
                  request.form.get('pays') or 'Sénégal',
                  request.form.get('transporteur'),
                  request.form.get('numero_suivi'),
                  request.form.get('date_expedition') or datetime.now().strftime('%Y-%m-%d'),
                  request.form.get('date_livraison_prevue'),
                  request.form.get('statut') or 'prepare',
                  float(request.form.get('frais_livraison') or 0),
                  request.form.get('notes'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Livraison créée', 'success')
            return redirect('/livraisons')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("""
        SELECT c.id, c.numero FROM commandes c
        WHERE c.statut IN ('prete', 'en_couture', 'finition')
        ORDER BY c.id DESC LIMIT 100
    """)
    commandes = cur.fetchall()
    opts_c = ''.join('<option value="' + str(c["id"]) + '"' + (' selected' if c["id"] == commande_id_pre else '') + '>' + str(c["numero"]) + '</option>' for c in commandes)

    content = '<h1>🚚 Nouvelle livraison</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="margin-bottom:16px"><label>Commande *</label><select name="commande_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_c + '</select></div>'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Type</label><select name="type">'
    content += '<option value="domicile">🏠 Domicile</option>'
    content += '<option value="retrait">🏪 Retrait boutique</option>'
    content += '<option value="international">✈️ International</option>'
    content += '</select></div>'
    content += '<div><label>Transporteur</label><input type="text" name="transporteur" placeholder="DHL, SENEX..."></div>'
    content += '<div style="grid-column:1/-1"><label>Adresse livraison</label><input type="text" name="adresse_livraison"></div>'
    content += '<div><label>Ville</label><input type="text" name="ville" value="Dakar"></div>'
    content += '<div><label>Pays</label><input type="text" name="pays" value="Sénégal"></div>'
    content += '<div><label>N° suivi</label><input type="text" name="numero_suivi"></div>'
    content += '<div><label>Frais livraison (FCFA)</label><input type="number" step="500" name="frais_livraison" value="2000"></div>'
    content += '<div><label>Date expédition</label><input type="date" name="date_expedition" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Date livraison prévue</label><input type="date" name="date_livraison_prevue" value="' + (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Statut</label><select name="statut">'
    content += '<option value="prepare">📦 Préparée</option>'
    content += '<option value="expedie">🚛 Expédiée</option>'
    content += '<option value="livre">✅ Livrée</option>'
    content += '</select></div>'
    content += '</div>'
    content += '<div style="margin-top:16px"><label>Notes</label><textarea name="notes" rows="3"></textarea></div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/livraisons" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='livraisons', page_title='Nouvelle livraison')



@app.route('/livraisons/<int:lid>')
@login_required
def livraisons_detail(lid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT l.*, c.numero AS commande_numero, c.montant_ttc,
               cl.nom AS client_nom, cl.prenom AS client_prenom, cl.telephone
        FROM livraisons l
        LEFT JOIN commandes c ON c.id=l.commande_id
        LEFT JOIN clients cl ON cl.id=c.client_id
        WHERE l.id=?
    """, (lid,))
    l = cur.fetchone()
    if not l:
        flash('❌ Livraison introuvable', 'error')
        return redirect('/livraisons')

    statut_badge = {'prepare': 'badge-gray', 'expedie': 'badge-orange', 'livre': 'badge-green', 'retour': 'badge-red'}.get(l['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🚚 ' + str(l["numero"]) + ' <span class="badge ' + statut_badge + '">' + str(l["statut"]) + '</span></h1>'
    content += '<a href="/livraisons" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-label">Commande</div><div class="kpi-value" style="font-size:16px">' + str(l["commande_numero"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Client</div><div class="kpi-value" style="font-size:15px">' + str(l["prenom"] or "") + ' ' + str(l["nom"] or "") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Frais livraison</div><div class="kpi-value" style="font-size:16px">' + f'{l["frais_livraison"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Détails</h2><table>'
    content += '<tr><td><strong>Type</strong></td><td>' + str(l["type"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Adresse</strong></td><td>' + str(l["adresse_livraison"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Ville</strong></td><td>' + str(l["ville"] or "—") + ', ' + str(l["pays"] or "") + '</td></tr>'
    content += '<tr><td><strong>Transporteur</strong></td><td>' + str(l["transporteur"] or "—") + '</td></tr>'
    content += '<tr><td><strong>N° suivi</strong></td><td>' + str(l["numero_suivi"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Date expédition</strong></td><td>' + str((l["date_expedition"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Date prévue</strong></td><td>' + str((l["date_livraison_prevue"] or "—")[:10]) + '</td></tr>'
    if l["date_livraison_reelle"]:
        content += '<tr><td><strong>Livrée le</strong></td><td>' + str(l["date_livraison_reelle"][:10]) + '</td></tr>'
    if l['notes']:
        content += '<tr><td><strong>Notes</strong></td><td>' + str(l["notes"]) + '</td></tr>'
    content += '</table></div>'

    return render_page(content, active='livraisons', page_title='Livraison')


# ═══════════════════════════════════════════════════════════════
# 💳 PAIEMENTS
# ═══════════════════════════════════════════════════════════════


@app.route('/paiements')
@login_required
def paiements_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT p.*, c.numero AS commande_numero,
               cl.nom AS client_nom, cl.prenom AS client_prenom
        FROM paiements p
        LEFT JOIN commandes c ON c.id=p.commande_id
        LEFT JOIN clients cl ON cl.id=p.client_id
        ORDER BY p.id DESC LIMIT 200
    """)
    paiements = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM paiements")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant),0) FROM paiements WHERE statut='valide'")
    stats['encaisse'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(montant),0) FROM paiements WHERE statut='en_attente'")
    stats['attente'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM paiements WHERE operateur='mobile_money'")
    stats['mobile'] = cur.fetchone()[0]

    rows = ''
    for p in paiements:
        statut_badge = {'valide': 'badge-green', 'en_attente': 'badge-orange', 'echec': 'badge-red'}.get(p['statut'], 'badge-gray')
        rows += (
            '<tr><td>#' + str(p["id"]) + '</td>'
            + '<td>' + str(p["commande_numero"] or "—") + '</td>'
            + '<td>' + str(p["prenom"] or "") + ' ' + str(p["nom"] or "—") + '</td>'
            + '<td>' + str(p["operateur"] or "—") + '</td>'
            + '<td>' + str(p["telephone"] or "—") + '</td>'
            + '<td style="text-align:right;font-weight:800">' + f'{p["montant"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(p["statut"]) + '</span></td>'
            + '<td>' + str((p["date_paiement"] or p["created_at"] or "—")[:10]) + '</td></tr>'
        )

    content = '<h1>💳 Paiements — ' + str(len(paiements)) + '</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-icon">💳</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">Encaissé</div><div class="kpi-value" style="font-size:16px">' + f'{stats["encaisse"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">⏳</div><div class="kpi-label">En attente</div><div class="kpi-value" style="font-size:16px">' + f'{stats["attente"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">📱</div><div class="kpi-label">Mobile Money</div><div class="kpi-value">' + str(stats["mobile"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>#</th><th>Commande</th><th>Client</th><th>Opérateur</th><th>Téléphone</th><th style="text-align:right">Montant</th><th>Statut</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun paiement</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='paiements', page_title='Paiements')


# ═══════════════════════════════════════════════════════════════
# 🌍 EXPORT UE
# ═══════════════════════════════════════════════════════════════


@app.route('/exports')
@login_required
def exports_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT e.*, c.numero AS commande_numero,
               cl.nom AS client_nom, cl.prenom AS client_prenom
        FROM exports e
        LEFT JOIN commandes c ON c.id=e.commande_id
        LEFT JOIN clients cl ON cl.id=c.client_id
        ORDER BY e.id DESC LIMIT 200
    """)
    exports = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM exports")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM exports WHERE certificat_ue=1")
    stats['ue'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM exports WHERE certificat_usa=1")
    stats['usa'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(valeur_fcfa),0) FROM exports")
    stats['valeur'] = cur.fetchone()[0]

    rows = ''
    for e in exports:
        statut_badge = {'en_preparation': 'badge-orange', 'expedie': 'badge-blue', 'livre': 'badge-green', 'bloque': 'badge-red'}.get(e['statut'], 'badge-gray')
        ue_badge = '✅' if e['certificat_ue'] else '❌'
        usa_badge = '✅' if e['certificat_usa'] else '❌'
        rows += (
            '<tr><td><strong style="color:#db2777">' + str(e["numero"]) + '</strong></td>'
            + '<td>' + str(e["commande_numero"] or "—") + '</td>'
            + '<td>' + str(e["destination"] or "—") + '<br><small style="color:#64748b">' + str(e["pays"] or "") + '</small></td>'
            + '<td style="text-align:right">' + f'{e["valeur_fcfa"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center">' + ue_badge + '</td>'
            + '<td style="text-align:center">' + usa_badge + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(e["statut"]) + '</span></td>'
            + '<td>' + str((e["date_export"] or "—")[:10]) + '</td></tr>'
        )

    content = '<h1>🌍 Exports UE & USAID — ' + str(len(exports)) + '</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-icon">🌍</div><div class="kpi-label">Total exports</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">🇪🇺</div><div class="kpi-label">Certifiés UE</div><div class="kpi-value">' + str(stats["ue"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🇺🇸</div><div class="kpi-label">Certifiés USAID</div><div class="kpi-value">' + str(stats["usa"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">Valeur totale</div><div class="kpi-value" style="font-size:16px">' + f'{stats["valeur"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px;padding:14px;background:linear-gradient(135deg,#1e40af,#3b82f6);color:#fff;border-radius:10px;font-size:13px">'
    content += '🌍 <strong>Normes intégrées</strong> : HACCP · ISO 22000 · GlobalG.A.P. · Bio UE 2018/848 · Traçabilité QR'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N°</th><th>Commande</th><th>Destination</th><th style="text-align:right">Valeur</th><th style="text-align:center">UE</th><th style="text-align:center">USAID</th><th>Statut</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun export</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='exports', page_title='Export UE')


# ═══════════════════════════════════════════════════════════════
# 💰 FINANCES
# ═══════════════════════════════════════════════════════════════


@app.route('/finances')
@login_required
def finances_index():
    db = get_db()
    cur = db.cursor()

    def sc(sql, default=0):
        try:
            cur.execute(sql)
            r = cur.fetchone()
            return r[0] if r and r[0] is not None else default
        except Exception:
            return default

    ca_total = sc("SELECT COALESCE(SUM(montant_ttc),0) FROM commandes WHERE statut='livree'")
    ca_mois = sc("SELECT COALESCE(SUM(montant_ttc),0) FROM commandes WHERE statut='livree' AND strftime('%Y-%m',date_livraison_reelle)=strftime('%Y-%m','now')")
    nb_cmds = sc("SELECT COUNT(*) FROM commandes WHERE statut='livree'")
    panier = (ca_total / nb_cmds) if nb_cmds > 0 else 0
    billets_ca = sc("SELECT COALESCE(SUM(prix),0) FROM billets WHERE statut='valide'")
    stands_ca = sc("SELECT COALESCE(SUM(tarif),0) FROM stands")
    exports_ca = sc("SELECT COALESCE(SUM(valeur_fcfa),0) FROM exports")
    tissus_valeur = sc("SELECT COALESCE(SUM(quantite_metres * prix_metre),0) FROM tissus")

    # CA par atelier
    cur.execute("""
        SELECT a.id, a.nom, COUNT(c.id) AS nb_commandes,
               COALESCE(SUM(c.montant_ttc),0) AS ca
        FROM ateliers a
        LEFT JOIN commandes c ON c.atelier_id=a.id AND c.statut='livree'
        GROUP BY a.id
        ORDER BY ca DESC LIMIT 10
    """)
    ateliers_ca = cur.fetchall()
    ateliers_html = ''
    for a in ateliers_ca:
        ateliers_html += (
            '<tr><td><strong>' + str(a["nom"]) + '</strong></td>'
            + '<td style="text-align:center">' + str(a["nb_commandes"]) + '</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:800">' + f'{a["ca"]:,.0f}' + ' F</td></tr>'
        )

    content = '<h1>💰 États financiers</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-icon">💰</div><div class="kpi-label">CA total</div><div class="kpi-value" style="font-size:16px">' + f'{ca_total:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">📅</div><div class="kpi-label">CA du mois</div><div class="kpi-value" style="font-size:16px">' + f'{ca_mois:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">🛒</div><div class="kpi-label">Panier moyen</div><div class="kpi-value" style="font-size:16px">' + f'{panier:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🎫</div><div class="kpi-label">Billetterie</div><div class="kpi-value" style="font-size:16px">' + f'{billets_ca:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">🏪</div><div class="kpi-label">Stands salons</div><div class="kpi-value" style="font-size:16px">' + f'{stands_ca:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div class="kpi-icon">🌍</div><div class="kpi-label">Export UE</div><div class="kpi-value" style="font-size:16px">' + f'{exports_ca:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>🏢 CA par atelier</h2>'
    content += '<table><thead><tr><th>Atelier</th><th style="text-align:center">Commandes</th><th style="text-align:right">CA</th></tr></thead>'
    content += '<tbody>' + (ateliers_html or '<tr><td colspan="3" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>📊 Bilan simplifié</h2><table>'
    content += '<tr><td><strong>PRODUITS</strong></td><td style="text-align:right"><strong>' + f'{ca_total + billets_ca + stands_ca + exports_ca:,.0f}' + ' F</strong></td></tr>'
    content += '<tr><td style="padding-left:30px">Ventes commandes</td><td style="text-align:right">' + f'{ca_total:,.0f}' + ' F</td></tr>'
    content += '<tr><td style="padding-left:30px">Billetterie salons</td><td style="text-align:right">' + f'{billets_ca:,.0f}' + ' F</td></tr>'
    content += '<tr><td style="padding-left:30px">Stands salons</td><td style="text-align:right">' + f'{stands_ca:,.0f}' + ' F</td></tr>'
    content += '<tr><td style="padding-left:30px">Exports UE</td><td style="text-align:right">' + f'{exports_ca:,.0f}' + ' F</td></tr>'
    content += '<tr style="background:#fdf2f8;font-weight:900"><td>TOTAL PRODUITS</td><td style="text-align:right;color:#9d174d">' + f'{ca_total + billets_ca + stands_ca + exports_ca:,.0f}' + ' F</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>📦 Valeur stock tissus</h2>'
    content += '<div style="font-size:26px;font-weight:900;color:#db2777">' + f'{tissus_valeur:,.0f}' + ' FCFA</div></div>'

    return render_page(content, active='finances', page_title='Finances')



@app.route('/finances/export-csv')
@login_required
def finances_export_csv():
    import csv
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.numero, c.date_commande, c.montant_ttc, c.statut,
               cl.nom AS client_nom, a.nom AS atelier_nom
        FROM commandes c
        LEFT JOIN clients cl ON cl.id=c.client_id
        LEFT JOIN ateliers a ON a.id=c.atelier_id
        ORDER BY c.id DESC LIMIT 1000
    """)
    rows = cur.fetchall()

    si = io.StringIO()
    w = csv.writer(si, delimiter=';')
    w.writerow(['N°', 'Date', 'Montant', 'Statut', 'Client', 'Atelier'])
    for r in rows:
        w.writerow([r['numero'], r['date_commande'], r['montant_ttc'],
                    r['statut'], r['client_nom'], r['atelier_nom']])

    log_action(current_user.id, 'EXPORT_CSV', f'{len(rows)} lignes', 'commandes')
    return Response(si.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment;filename=mode_commandes_{datetime.now().strftime("%Y%m%d")}.csv'})


# ═══════════════════════════════════════════════════════════════
# 📱 MOBILE MODE (client + couturier)
# ═══════════════════════════════════════════════════════════════


@app.route('/mobile-mode')
@login_required
def mobile_mode():
    db = get_db()
    cur = db.cursor()

    def sc(sql, default=0):
        cur.execute(sql)
        r = cur.fetchone()
        return r[0] if r and r[0] is not None else default

    stats = {
        'creations': sc("SELECT COUNT(*) FROM creations WHERE disponible=1"),
        'ateliers': sc("SELECT COUNT(*) FROM ateliers WHERE statut='actif'"),
        'salons': sc("SELECT COUNT(*) FROM salons WHERE statut='planifie'"),
        'commandes_encours': sc("SELECT COUNT(*) FROM commandes WHERE statut NOT IN ('livree','annulee')"),
    }

    content = '<h1>📱 Mobile Mode & Couture</h1>'
    content += '<div style="background:#fdf2f8;border-left:4px solid #db2777;padding:14px;border-radius:8px;margin-bottom:20px;font-size:13px;color:#9d174d">'
    content += '💡 Application mobile pour clients et couturiers — commande, suivi, salons'
    content += '</div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#db2777,#9d174d)"><div class="kpi-label">Créations</div><div class="kpi-value">' + str(stats["creations"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Ateliers</div><div class="kpi-value">' + str(stats["ateliers"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Salons planifiés</div><div class="kpi-value">' + str(stats["salons"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Commandes en cours</div><div class="kpi-value">' + str(stats["commandes_encours"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>⚡ Actions rapides</h2>'
    content += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:12px">'
    actions = [
        ('/creations', '👗 Catalogue créations', '#db2777'),
        ('/commandes/nouvelle', '✂️ Commander', '#f59e0b'),
        ('/mesures/nouvelle', '📏 Mes mesures', '#10b981'),
        ('/salons', '🎪 Salons expositions', '#3b82f6'),
        ('/billets', '🎫 Billets', '#8b5cf6'),
        ('/exports', '🌍 Export UE', '#ec4899'),
    ]
    for url, label, color in actions:
        content += '<a href="' + url + '" style="text-decoration:none"><div style="background:' + color + ';color:#fff;padding:20px;border-radius:10px;text-align:center;font-weight:700;font-size:13px">' + label + '</div></a>'
    content += '</div></div>'

    content += '<div class="card"><h2>👗 Créations populaires</h2>'
    cur.execute("""
        SELECT c.nom, c.prix_vente, cat.icone AS cat_icone
        FROM creations c
        LEFT JOIN categories cat ON cat.id=c.categorie_id
        WHERE c.disponible=1
        ORDER BY c.nb_commandes DESC LIMIT 6
    """)
    creations = cur.fetchall()
    rows = ''
    for c in creations:
        rows += (
            '<tr><td>' + str(c["cat_icone"] or "👗") + ' ' + str(c["nom"]) + '</td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{c["prix_vente"]:,.0f}' + ' F</td></tr>'
        )
    content += '<table><tbody>' + (rows or '<tr><td colspan="2" style="text-align:center;color:#94a3b8;padding:20px">Aucune création</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='dashboard', page_title='Mobile Mode')


# ═══════════════════════════════════════════════════════════════
# 📊 API JSON
# ═══════════════════════════════════════════════════════════════


@app.route('/api/mode/stats')
@login_required
def api_mode_stats():
    db = get_db()
    cur = db.cursor()
    result = {}
    for k, sql in [
        ('ateliers', "SELECT COUNT(*) FROM ateliers WHERE statut='actif'"),
        ('creations', "SELECT COUNT(*) FROM creations WHERE disponible=1"),
        ('clients', "SELECT COUNT(*) FROM clients WHERE statut='actif'"),
        ('commandes_encours', "SELECT COUNT(*) FROM commandes WHERE statut NOT IN ('livree','annulee')"),
        ('ca_total', "SELECT COALESCE(SUM(montant_ttc),0) FROM commandes WHERE statut='livree'"),
        ('salons', "SELECT COUNT(*) FROM salons WHERE statut='planifie'"),
        ('billets', "SELECT COUNT(*) FROM billets WHERE statut='valide'"),
    ]:
        try:
            cur.execute(sql)
            r = cur.fetchone()
            result[k] = r[0] if r else 0
        except Exception:
            result[k] = 0
    return jsonify(result)



@app.route('/api/billets/verifier/<numero>')
def api_verifier_billet(numero):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT b.numero, b.type_billet, b.prix, b.statut,
               s.nom AS salon_nom, s.lieu, s.ville,
               c.nom AS client_nom, c.prenom AS client_prenom
        FROM billets b
        LEFT JOIN salons s ON s.id=b.salon_id
        LEFT JOIN clients c ON c.id=b.client_id
        WHERE b.numero=?
    """, (numero,))
    b = cur.fetchone()
    if not b:
        return jsonify({'valide': False, 'error': 'Billet introuvable'}), 404
    return jsonify({
        'valide': b['statut'] == 'valide',
        'numero': b['numero'],
        'salon': b['salon_nom'],
        'lieu': b['lieu'],
        'client': (b['prenom'] or '') + ' ' + (b['nom'] or ''),
        'type': b['type_billet'],
        'prix': b['prix'],
    })



@app.route('/api/creations/verifier/<code>')
def api_verifier_creation(code):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.code, c.nom, c.prix_vente, c.tissu_principal,
               a.nom AS atelier_nom
        FROM creations c LEFT JOIN ateliers a ON a.id=c.atelier_id
        WHERE c.code=?
    """, (code,))
    c = cur.fetchone()
    if not c:
        return jsonify({'valide': False, 'error': 'Création introuvable'}), 404
    return jsonify({
        'valide': True,
        'code': c['code'],
        'nom': c['nom'],
        'prix': c['prix_vente'],
        'tissu': c['tissu_principal'],
        'atelier': c['atelier_nom'],
    })



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
