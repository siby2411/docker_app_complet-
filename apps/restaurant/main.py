"""
🍽️ Restauration & Livraison — Application principale
Menu · Commandes · Livraison · Stocks · POS · Caissiers · Fidélité · IA
"""
from flask import Flask, render_template_string, redirect, url_for, session, request, jsonify, Response, send_file, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import sqlite3
import os
import io

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'omega-resto-secret-2026')

DB_PATH = '/app/data/restaurant.db'

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
# LAYOUT — DESIGN RESTAURATION
# ═══════════════════════════════════════════════════════════════

LAYOUT = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — OMEGA Resto</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,-apple-system,sans-serif}}
body{{background:#fef7f0;color:#1e293b;font-size:14px}}
.nav{{background:linear-gradient(135deg,#dc2626,#991b1b);color:#fff;padding:0 22px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 3px 12px rgba(0,0,0,.15);flex-wrap:wrap;border-bottom:4px solid #f59e0b}}
.nav-brand{{font-weight:900;font-size:18px;display:flex;align-items:center;gap:12px;padding:16px 0;letter-spacing:-0.3px}}
.nav-brand-icon{{width:40px;height:40px;background:#f59e0b;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(245,158,11,.5)}}
.nav-links{{display:flex;gap:2px;flex-wrap:wrap}}
.nav-links a{{color:#fecaca;text-decoration:none;padding:8px 13px;border-radius:8px;font-size:12.5px;font-weight:600;transition:.2s;display:flex;align-items:center;gap:6px}}
.nav-links a:hover{{background:rgba(255,255,255,.12);color:#fff}}
.nav-links a.active{{background:#f59e0b;color:#fff;box-shadow:0 4px 10px rgba(245,158,11,.4)}}
.nav-user{{font-size:12.5px;display:flex;gap:10px;align-items:center;color:#fecaca}}
.nav-user a{{color:#fff;text-decoration:none;background:rgba(0,0,0,.25);padding:7px 14px;border-radius:8px;font-weight:600}}
.container{{max-width:1600px;margin:0 auto;padding:24px}}
h1{{color:#dc2626;margin-bottom:20px;font-size:24px;font-weight:800;letter-spacing:-0.4px}}
h2{{color:#dc2626;font-size:18px;margin-bottom:14px;font-weight:700}}
.card{{background:#fff;padding:22px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:18px;border-left:4px solid #f59e0b}}
table{{width:100%;border-collapse:collapse}}
thead{{background:#dc2626;color:#fff}}
th{{padding:12px;text-align:left;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}}
td{{padding:11px;border-bottom:1px solid #f1f5f9;font-size:13.5px}}
tbody tr:hover{{background:#fff7ed}}
.btn{{display:inline-block;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px;border:none;cursor:pointer;transition:.15s;letter-spacing:.2px}}
.btn:hover{{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.15)}}
.btn-primary{{background:#dc2626;color:#fff}}
.btn-gold{{background:#f59e0b;color:#fff}}
.btn-success{{background:#10b981;color:#fff}}
.btn-danger{{background:#ef4444;color:#fff}}
.btn-warning{{background:#f59e0b;color:#fff}}
.btn-secondary{{background:#64748b;color:#fff}}
input,select,textarea{{width:100%;padding:11px 14px;border:2px solid #e2e8f0;border-radius:8px;font-size:13.5px;font-family:inherit;transition:.2s}}
input:focus,select:focus,textarea:focus{{outline:none;border-color:#dc2626;box-shadow:0 0 0 3px rgba(220,38,38,.1)}}
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
.plat-card{{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:.2s}}
.plat-card:hover{{transform:translateY(-3px);box-shadow:0 8px 20px rgba(220,38,38,.15)}}
.plat-icon{{background:linear-gradient(135deg,#dc2626,#991b1b);color:#fff;height:100px;display:flex;align-items:center;justify-content:center;font-size:44px}}
.plat-body{{padding:16px}}
.pos-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;max-height:calc(100vh - 380px);overflow-y:auto;padding:8px;background:#fff;border-radius:12px}}
.pos-plat{{background:#f9fafb;border:2px solid #e5e7eb;border-radius:10px;padding:12px;cursor:pointer;transition:0.15s}}
.pos-plat:hover{{border-color:#dc2626;transform:translateY(-2px);box-shadow:0 4px 12px rgba(220,38,38,0.15)}}
.pos-plat:active{{transform:scale(0.97)}}
.pos-cart{{background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.cart-line{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f3f4f6}}
.cart-line button{{background:#ef4444;color:#fff;border:none;border-radius:6px;padding:4px 8px;cursor:pointer;font-size:12px}}
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-brand">
    <div class="nav-brand-icon">🍽️</div>
    <div>OMEGA RESTO<span style="display:block;font-size:10px;font-weight:500;letter-spacing:2px;color:#fecaca">RESTAURATION · LIVRAISON · CEDEAO</span></div>
  </div>
  <div class="nav-links">
    <a href="/" class="{a_dash}">📊 Dashboard</a>
    <a href="/menu" class="{a_menu}">📋 Menu</a>
    <a href="/pos" class="{a_pos}">🖥️ POS</a>
    <a href="/commandes" class="{a_cmd}">🛒 Commandes</a>
    <a href="/livraisons" class="{a_liv}">🛵 Livraisons</a>
    <a href="/clients" class="{a_cli}">👥 Clients</a>
    <a href="/livreurs" class="{a_livr}">🛵 Livreurs</a>
    <a href="/stocks" class="{a_stk}">📦 Stocks</a>
    <a href="/caisse/sessions" class="{a_caisse}">💰 Caissiers</a>
    <a href="/finances" class="{a_fin}">💵 Finances</a>
    <a href="/avis" class="{a_avi}">⭐ Avis</a>
    <a href="/fidelite" class="{a_fid}">🎁 Fidélité</a>
    <a href="/ia" class="{a_ia}">🤖 IA</a>
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


def render_page(content, active='dashboard', page_title='Restaurant'):
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
        a_menu='active' if active == 'menu' else '',
        a_pos='active' if active == 'pos' else '',
        a_cmd='active' if active == 'commandes' else '',
        a_liv='active' if active == 'livraisons' else '',
        a_cli='active' if active == 'clients' else '',
        a_livr='active' if active == 'livreurs' else '',
        a_stk='active' if active == 'stocks' else '',
        a_caisse='active' if active == 'caisse' else '',
        a_fin='active' if active == 'finances' else '',
        a_avi='active' if active == 'avis' else '',
        a_fid='active' if active == 'fidelite' else '',
        a_ia='active' if active == 'ia' else '',
    )


@app.route('/health')
def health():
    return {'project': 'OMEGA RESTO', 'service': 'restauration-livraison',
            'status': 'ok', 'timestamp': datetime.now().isoformat(), 'version': '1.0'}


LOGIN_HTML = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Connexion — OMEGA Resto</title>
<style>body{{font-family:system-ui;background:linear-gradient(135deg,#dc2626,#991b1b);min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0}}
.box{{background:#fff;padding:42px;border-radius:16px;box-shadow:0 25px 70px rgba(0,0,0,.4);width:100%;max-width:420px;border-top:5px solid #f59e0b}}
.logo{{text-align:center;font-size:56px;margin-bottom:12px}}
h1{{color:#dc2626;margin:0 0 6px;text-align:center;font-size:22px;font-weight:900;letter-spacing:-0.3px}}
.subtitle{{text-align:center;color:#64748b;font-size:12px;margin-bottom:24px;letter-spacing:1.5px;text-transform:uppercase;font-weight:600}}
input{{width:100%;padding:14px;border:2px solid #e2e8f0;border-radius:10px;margin-bottom:14px;font-size:15px;box-sizing:border-box}}
input:focus{{outline:none;border-color:#dc2626;box-shadow:0 0 0 3px rgba(220,38,38,.1)}}
button{{width:100%;background:#f59e0b;color:#fff;padding:15px;border:none;border-radius:10px;font-weight:800;font-size:15px;cursor:pointer;letter-spacing:.5px;text-transform:uppercase}}
button:hover{{background:#d97706}}
.err{{background:#fee2e2;color:#991b1b;padding:11px;border-radius:8px;margin-bottom:14px;font-size:13px;border-left:4px solid #ef4444}}
.hint{{margin-top:20px;padding:12px;background:#fff7ed;border-radius:8px;font-size:12px;color:#c2410c;text-align:center;border:1px dashed #fdba74}}</style></head>
<body><div class="box">
<div class="logo">🍽️</div>
<h1>OMEGA RESTO</h1>
<div class="subtitle">Restauration · Livraison · CEDEAO</div>
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
        'commandes_jour': sc("SELECT COUNT(*) FROM commandes WHERE date(date_commande)=date('now')"),
        'ca_jour': sc("SELECT COALESCE(SUM(montant_total),0) FROM commandes WHERE date(date_commande)=date('now')"),
        'commandes_encours': sc("SELECT COUNT(*) FROM commandes WHERE statut IN ('nouvelle','en_preparation','prete')"),
        'livraisons_encours': sc("SELECT COUNT(*) FROM commandes WHERE statut='en_livraison'"),
        'plats_menu': sc("SELECT COUNT(*) FROM plats WHERE disponible=1"),
        'clients': sc("SELECT COUNT(*) FROM clients WHERE statut='actif'"),
        'livreurs_dispo': sc("SELECT COUNT(*) FROM livreurs WHERE statut='disponible'"),
        'stocks_alerte': sc("SELECT COUNT(*) FROM ingredients WHERE quantite_stock <= seuil_alerte"),
    }

    # Commandes récentes
    cur.execute("""
        SELECT c.*, cl.nom AS client_nom, cl.prenom AS client_prenom, cl.telephone AS client_tel,
               l.nom AS livreur_nom, r.nom AS restaurant_nom
        FROM commandes c
        LEFT JOIN clients cl ON cl.id=c.client_id
        LEFT JOIN livreurs l ON l.id=c.livreur_id
        LEFT JOIN restaurants r ON r.id=c.restaurant_id
        ORDER BY c.id DESC LIMIT 8
    """)
    commandes = cur.fetchall()

    cmd_html = ''
    for c in commandes:
        statut_badge = {
            'nouvelle': 'badge-red',
            'en_preparation': 'badge-orange',
            'prete': 'badge-gold',
            'en_livraison': 'badge-blue',
            'livree': 'badge-green',
            'annulee': 'badge-gray',
        }.get(c['statut'], 'badge-gray')
        type_icon = {'sur_place': '🍽️', 'emporter': '🥡', 'livraison': '🛵'}.get(c['type'], '🍽️')
        cmd_html += (
            '<tr><td><strong style="color:#dc2626">' + str(c["numero"]) + '</strong></td>'
            + '<td>' + type_icon + ' ' + str(c["type"]).replace('_', ' ') + '</td>'
            + '<td>' + str(c["client_prenom"] or "") + ' ' + str(c["client_nom"] or "—") + '<br><small style="color:#64748b">' + str(c["client_tel"] or "") + '</small></td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{c["montant_total"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></td>'
            + '<td><a href="/commandes/' + str(c["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    # Top plats
    cur.execute("""
        SELECT p.nom, p.prix, COUNT(cl.id) AS nb_commandes,
               COALESCE(SUM(cl.quantite),0) AS qte_vendue
        FROM plats p
        LEFT JOIN commande_lignes cl ON cl.plat_id=p.id
        GROUP BY p.id
        ORDER BY qte_vendue DESC LIMIT 5
    """)
    top_plats = cur.fetchall()
    top_html = ''.join(
        '<tr><td>' + str(p["nom"]) + '</td>'
        + '<td style="text-align:center">' + str(int(p["qte_vendue"])) + '</td>'
        + '<td style="text-align:right">' + f'{p["prix"]:,.0f}' + ' F</td></tr>'
        for p in top_plats
    )

    content = '<h1>🍽️ Tableau de bord Restaurant</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">🛒</div><div class="kpi-label">Commandes du jour</div><div class="kpi-value">' + str(stats["commandes_jour"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">CA du jour</div><div class="kpi-value" style="font-size:18px">' + f'{stats["ca_jour"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">⏳</div><div class="kpi-label">En cours</div><div class="kpi-value">' + str(stats["commandes_encours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">🛵</div><div class="kpi-label">Livraisons</div><div class="kpi-value">' + str(stats["livraisons_encours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">📋</div><div class="kpi-label">Plats au menu</div><div class="kpi-value">' + str(stats["plats_menu"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div class="kpi-icon">👥</div><div class="kpi-label">Clients</div><div class="kpi-value">' + str(stats["clients"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">🛵</div><div class="kpi-label">Livreurs dispo</div><div class="kpi-value">' + str(stats["livreurs_dispo"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">⚠️</div><div class="kpi-label">Alertes stock</div><div class="kpi-value">' + str(stats["stocks_alerte"]) + '</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:18px">'
    content += '<div class="card"><h2>🛒 Commandes récentes</h2>'
    content += '<table><thead><tr><th>N°</th><th>Type</th><th>Client</th><th style="text-align:right">Montant</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (cmd_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:30px">Aucune commande</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>🏆 Top 5 plats</h2>'
    content += '<table><thead><tr><th>Plat</th><th style="text-align:center">Vendus</th><th style="text-align:right">Prix</th></tr></thead>'
    content += '<tbody>' + (top_html or '<tr><td colspan="3" style="text-align:center;color:#94a3b8;padding:30px">Aucune donnée</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    content += '<div class="card"><h2>⚡ Actions rapides</h2>'
    content += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:12px">'
    actions = [
        ('/pos', '🖥️ Ouvrir le POS', '#dc2626'),
        ('/commandes/nouvelle', '🛒 Nouvelle commande', '#f59e0b'),
        ('/menu/nouveau', '📋 Nouveau plat', '#10b981'),
        ('/caisse/sessions/ouvrir', '💰 Ouvrir caisse', '#3b82f6'),
        ('/livraisons', '🛵 Suivi livraisons', '#8b5cf6'),
        ('/ia', '🤖 Recommandations IA', '#ec4899'),
    ]
    for url, label, color in actions:
        content += '<a href="' + url + '" style="text-decoration:none"><div style="background:' + color + ';color:#fff;padding:20px;border-radius:10px;text-align:center;font-weight:700;font-size:13px">' + label + '</div></a>'
    content += '</div></div>'

    return render_page(content, active='dashboard', page_title='Dashboard')


# ═══════════════════════════════════════════════════════════════
# 📋 MENU / PLATS
# ═══════════════════════════════════════════════════════════════

@app.route('/menu')
@login_required
def menu_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()
    cat_f = request.args.get('categorie_id', '')

    sql = """
        SELECT p.*, c.nom AS categorie_nom, c.icone AS categorie_icone
        FROM plats p
        LEFT JOIN categories c ON c.id=p.categorie_id
        WHERE 1=1
    """
    params = []
    if q:
        sql += " AND (p.nom LIKE ? OR p.description LIKE ?)"
        params += [f'%{q}%'] * 2
    if cat_f:
        sql += " AND p.categorie_id=?"
        params.append(cat_f)
    sql += " ORDER BY c.ordre, p.nom LIMIT 200"
    cur.execute(sql, params)
    plats = cur.fetchall()

    cur.execute("SELECT * FROM categories ORDER BY ordre")
    categories = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM plats WHERE disponible=1")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM categories")
    stats['cats'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(prix),0) FROM plats")
    stats['prix_moy'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(note_moyenne),0) FROM plats WHERE note_moyenne > 0")
    stats['note'] = cur.fetchone()[0]

    cards = ''
    for p in plats:
        icon = str(p['categorie_icone'] or '🍽️')
        dispo_badge = '' if p['disponible'] else '<span class="badge badge-red">Indisponible</span>'
        cards += '<div class="plat-card">'
        cards += '<div class="plat-icon">' + icon + '</div>'
        cards += '<div class="plat-body">'
        cards += '<div style="font-weight:800;color:#1e293b;font-size:14px;margin-bottom:4px">' + str(p["nom"]) + '</div>'
        cards += '<div style="font-size:11.5px;color:#64748b;margin-bottom:8px">' + str(p["categorie_nom"] or "—") + ' · ' + str(p["temps_preparation"]) + ' min</div>'
        cards += '<div style="font-size:12px;color:#475569;margin-bottom:10px">' + str(p["description"] or "")[:60] + '</div>'
        cards += '<div style="display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap">'
        if p['vegetarien']:
            cards += '<span class="badge badge-green">🥬 Végétarien</span>'
        if p['epice']:
            cards += '<span class="badge badge-red">🌶️ Épicé</span>'
        if not p['disponible']:
            cards += '<span class="badge badge-gray">Indisponible</span>'
        cards += '</div>'
        cards += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'
        cards += '<div style="font-size:18px;font-weight:900;color:#10b981">' + f'{p["prix"]:,.0f}' + ' F</div>'
        cards += '<div style="font-size:11.5px;color:#f59e0b">⭐ ' + f'{p["note_moyenne"]:.1f}' + '</div>'
        cards += '</div>'
        cards += '<a href="/menu/' + str(p["id"]) + '" class="btn btn-primary" style="padding:6px 10px;font-size:11.5px;width:100%;text-align:center;display:block">👁 Détails</a>'
        cards += '</div></div>'

    cats_html = '<a href="/menu" class="btn ' + ('btn-primary' if not cat_f else 'btn-secondary') + '">Tous</a> '
    for c in categories:
        active_cls = 'btn-primary' if str(cat_f) == str(c['id']) else 'btn-secondary'
        cats_html += '<a href="/menu?categorie_id=' + str(c["id"]) + '" class="btn ' + active_cls + '" style="margin-left:6px">' + str(c["icone"] or "") + ' ' + str(c["nom"]) + '</a> '

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📋 Menu numérique — ' + str(len(plats)) + ' plats</h1>'
    content += '<a href="/menu/nouveau" class="btn btn-primary">+ Nouveau plat</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">📋</div><div class="kpi-label">Plats disponibles</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">🏷️</div><div class="kpi-label">Catégories</div><div class="kpi-value">' + str(stats["cats"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">Prix moyen</div><div class="kpi-value" style="font-size:16px">' + f'{stats["prix_moy"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">⭐</div><div class="kpi-label">Note moyenne</div><div class="kpi-value">' + f'{stats["note"]:.1f}' + '</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher plat..." style="max-width:400px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="margin-bottom:20px;display:flex;gap:6px;flex-wrap:wrap">' + cats_html + '</div>'

    content += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px">' + (cards or '<p style="grid-column:1/-1;text-align:center;color:#94a3b8;padding:40px">Aucun plat</p>') + '</div>'

    return render_page(content, active='menu', page_title='Menu')


@app.route('/menu/nouveau', methods=['GET', 'POST'])
@login_required
def menu_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO plats
                (code, restaurant_id, categorie_id, nom, description, prix,
                 temps_preparation, disponible, vegetarien, epice, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (None,
                  int(request.form.get('restaurant_id') or 0) or None,
                  int(request.form.get('categorie_id') or 0) or None,
                  request.form.get('nom'),
                  request.form.get('description'),
                  float(request.form.get('prix') or 0),
                  int(request.form.get('temps_preparation') or 15),
                  1 if request.form.get('disponible') else 0,
                  1 if request.form.get('vegetarien') else 0,
                  1 if request.form.get('epice') else 0,
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Plat créé', 'success')
            return redirect('/menu')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom FROM restaurants WHERE statut='ouvert' ORDER BY nom")
    restaurants = cur.fetchall()
    cur.execute("SELECT id, nom, icone FROM categories ORDER BY ordre")
    categories = cur.fetchall()

    opts_r = ''.join('<option value="' + str(r["id"]) + '">' + str(r["nom"]) + '</option>' for r in restaurants)
    opts_c = ''.join('<option value="' + str(c["id"]) + '">' + str(c["icone"] or "") + ' ' + str(c["nom"]) + '</option>' for c in categories)

    content = '<h1>📋 Nouveau plat</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom du plat *</label><input type="text" name="nom" required autofocus></div>'
    content += '<div><label>Restaurant</label><select name="restaurant_id"><option value="">— Aucun —</option>' + opts_r + '</select></div>'
    content += '<div><label>Catégorie</label><select name="categorie_id"><option value="">— Aucune —</option>' + opts_c + '</select></div>'
    content += '<div style="grid-column:1/-1"><label>Description</label><textarea name="description" rows="3"></textarea></div>'
    content += '<div><label>Prix (FCFA) *</label><input type="number" step="100" name="prix" required value="2500"></div>'
    content += '<div><label>Temps préparation (min)</label><input type="number" name="temps_preparation" value="15"></div>'
    content += '<div style="grid-column:1/-1">'
    content += '<label><input type="checkbox" name="disponible" value="1" checked style="width:auto;margin-right:8px"> Disponible</label>'
    content += '<label style="margin-top:8px"><input type="checkbox" name="vegetarien" value="1" style="width:auto;margin-right:8px"> 🥬 Végétarien</label>'
    content += '<label style="margin-top:8px"><input type="checkbox" name="epice" value="1" style="width:auto;margin-right:8px"> 🌶️ Épicé</label>'
    content += '</div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/menu" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='menu', page_title='Nouveau plat')


@app.route('/menu/<int:pid>')
@login_required
def menu_detail(pid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT p.*, c.nom AS categorie_nom, c.icone AS categorie_icone
        FROM plats p
        LEFT JOIN categories c ON c.id=p.categorie_id
        WHERE p.id=?
    """, (pid,))
    p = cur.fetchone()
    if not p:
        flash('❌ Plat introuvable', 'error')
        return redirect('/menu')

    # Avis sur ce plat
    cur.execute("""
        SELECT a.*, cl.nom, cl.prenom
        FROM avis a
        LEFT JOIN clients cl ON cl.id=a.client_id
        WHERE a.plat_id=?
        ORDER BY a.id DESC LIMIT 10
    """, (pid,))
    avis = cur.fetchall()
    avis_html = ''
    for a in avis:
        stars = '⭐' * (a['note'] or 0)
        avis_html += (
            '<tr><td>' + str(a["prenom"] or "") + ' ' + str(a["nom"] or "Client") + '</td>'
            + '<td style="color:#f59e0b">' + stars + '</td>'
            + '<td>' + str(a["commentaire"] or "") + '</td>'
            + '<td>' + str((a["date_avis"] or "")[:10]) + '</td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">' + str(p["categorie_icone"] or "🍽️") + ' ' + str(p["nom"]) + '</h1>'
    content += '<a href="/menu" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Prix</div><div class="kpi-value" style="font-size:20px">' + f'{p["prix"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Préparation</div><div class="kpi-value">' + str(p["temps_preparation"]) + ' min</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Note</div><div class="kpi-value">⭐ ' + f'{p["note_moyenne"]:.1f}' + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-label">Commandes</div><div class="kpi-value">' + str(p["nb_commandes"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations</h2><table>'
    content += '<tr><td><strong>Catégorie</strong></td><td>' + str(p["categorie_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Description</strong></td><td>' + str(p["description"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Disponible</strong></td><td>' + ('✅ Oui' if p["disponible"] else '❌ Non') + '</td></tr>'
    content += '<tr><td><strong>Végétarien</strong></td><td>' + ('✅ Oui' if p["vegetarien"] else '❌ Non') + '</td></tr>'
    content += '<tr><td><strong>Épicé</strong></td><td>' + ('✅ Oui' if p["epice"] else '❌ Non') + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>⭐ Avis clients (' + str(len(avis)) + ')</h2>'
    content += '<table><thead><tr><th>Client</th><th>Note</th><th>Commentaire</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (avis_html or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucun avis</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='menu', page_title='Plat')


# ═══════════════════════════════════════════════════════════════
# 🛒 COMMANDES
# ═══════════════════════════════════════════════════════════════

@app.route('/commandes')
@login_required
def commandes_liste():
    db = get_db()
    cur = db.cursor()
    statut_f = request.args.get('statut', '')
    type_f = request.args.get('type', '')

    sql = """
        SELECT c.*, cl.nom AS client_nom, cl.prenom AS client_prenom, cl.telephone AS client_tel,
               l.nom AS livreur_nom, u.nom_complet AS caissier_nom
        FROM commandes c
        LEFT JOIN clients cl ON cl.id=c.client_id
        LEFT JOIN livreurs l ON l.id=c.livreur_id
        LEFT JOIN users u ON u.id=c.caissier_id
        WHERE 1=1
    """
    params = []
    if statut_f:
        sql += " AND c.statut=?"
        params.append(statut_f)
    if type_f:
        sql += " AND c.type=?"
        params.append(type_f)
    sql += " ORDER BY c.id DESC LIMIT 200"
    cur.execute(sql, params)
    commandes = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM commandes")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM commandes WHERE statut='nouvelle'")
    stats['nouvelles'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM commandes WHERE statut='en_preparation'")
    stats['prep'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM commandes WHERE statut='en_livraison'")
    stats['liv'] = cur.fetchone()[0]

    rows = ''
    for c in commandes:
        statut_badge = {
            'nouvelle': 'badge-red',
            'en_preparation': 'badge-orange',
            'prete': 'badge-gold',
            'en_livraison': 'badge-blue',
            'livree': 'badge-green',
            'annulee': 'badge-gray',
        }.get(c['statut'], 'badge-gray')
        type_icon = {'sur_place': '🍽️', 'emporter': '🥡', 'livraison': '🛵'}.get(c['type'], '🍽️')
        rows += (
            '<tr><td><strong style="color:#dc2626">' + str(c["numero"]) + '</strong></td>'
            + '<td>' + type_icon + '</td>'
            + '<td>' + str(c["client_prenom"] or "") + ' ' + str(c["client_nom"] or "—") + '</td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{c["montant_total"]:,.0f}' + ' F</td>'
            + '<td>' + str(c["mode_paiement"] or "—") + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></td>'
            + '<td>' + str((c["date_commande"] or "")[:16]) + '</td>'
            + '<td><a href="/commandes/' + str(c["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🛒 Commandes — ' + str(len(commandes)) + '</h1>'
    content += '<a href="/commandes/nouvelle" class="btn btn-primary">+ Nouvelle commande</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">🛒</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">🆕</div><div class="kpi-label">Nouvelles</div><div class="kpi-value">' + str(stats["nouvelles"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">👨‍🍳</div><div class="kpi-label">En préparation</div><div class="kpi-value">' + str(stats["prep"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">🛵</div><div class="kpi-label">En livraison</div><div class="kpi-value">' + str(stats["liv"]) + '</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/commandes" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Toutes</a> '
    for s in ['nouvelle', 'en_preparation', 'prete', 'en_livraison', 'livree']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/commandes?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N°</th><th>Type</th><th>Client</th><th style="text-align:right">Montant</th><th>Paiement</th><th>Statut</th><th>Date</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucune commande</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='commandes', page_title='Commandes')


@app.route('/commandes/<int:cid>', methods=['GET', 'POST'])
@login_required
def commandes_detail(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, cl.nom AS client_nom, cl.prenom AS client_prenom, cl.telephone AS client_tel,
               l.nom AS livreur_nom, l.telephone AS livreur_tel, u.nom_complet AS caissier_nom
        FROM commandes c
        LEFT JOIN clients cl ON cl.id=c.client_id
        LEFT JOIN livreurs l ON l.id=c.livreur_id
        LEFT JOIN users u ON u.id=c.caissier_id
        WHERE c.id=?
    """, (cid,))
    c = cur.fetchone()
    if not c:
        flash('❌ Commande introuvable', 'error')
        return redirect('/commandes')

    if request.method == 'POST':
        try:
            new_statut = request.form.get('statut') or c['statut']
            cur.execute("UPDATE commandes SET statut=? WHERE id=?", (new_statut, cid))
            db.commit()
            flash('✅ Statut mis à jour : ' + new_statut, 'success')
            return redirect('/commandes/' + str(cid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT * FROM commande_lignes WHERE commande_id=?", (cid,))
    lignes = cur.fetchall()
    lignes_html = ''
    for l in lignes:
        lignes_html += (
            '<tr><td>' + str(l["nom_plat"]) + '</td>'
            + '<td style="text-align:right">' + f'{l["prix_unitaire"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center">' + str(l["quantite"]) + '</td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{l["montant"]:,.0f}' + ' F</td></tr>'
        )

    statut_badge = {
        'nouvelle': 'badge-red', 'en_preparation': 'badge-orange', 'prete': 'badge-gold',
        'en_livraison': 'badge-blue', 'livree': 'badge-green', 'annulee': 'badge-gray'
    }.get(c['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🛒 ' + str(c["numero"]) + ' <span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></h1>'
    content += '<a href="/commandes" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-label">Type</div><div class="kpi-value" style="font-size:16px">' + str(c["type"]).replace('_', ' ') + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Montant</div><div class="kpi-value" style="font-size:18px">' + f'{c["montant_total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Paiement</div><div class="kpi-value" style="font-size:16px">' + str(c["mode_paiement"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Caissier</div><div class="kpi-value" style="font-size:14px">' + str(c["caissier_nom"] or "—") + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Lignes de commande</h2>'
    content += '<table><thead><tr><th>Plat</th><th style="text-align:right">Prix U.</th><th style="text-align:center">Qté</th><th style="text-align:right">Montant</th></tr></thead>'
    content += '<tbody>' + (lignes_html or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucune ligne</td></tr>') + '</tbody></table>'
    content += '<table style="margin-top:14px">'
    content += '<tr><td>Sous-total</td><td style="text-align:right">' + f'{c["montant_sous_total"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td>Frais livraison</td><td style="text-align:right">' + f'{c["frais_livraison"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td>Remise</td><td style="text-align:right">- ' + f'{c["remise"]:,.0f}' + ' F</td></tr>'
    content += '<tr style="background:#f0fdf4;font-weight:900"><td>TOTAL</td><td style="text-align:right;color:#047857">' + f'{c["montant_total"]:,.0f}' + ' F</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>👤 Client</h2>'
    content += '<div style="padding:12px;background:#f8fafc;border-radius:8px">'
    content += '<div style="font-weight:800;font-size:16px;color:#dc2626">' + str(c["client_prenom"] or "") + ' ' + str(c["client_nom"] or "—") + '</div>'
    content += '<div style="font-size:13px;color:#64748b;margin-top:6px">📞 ' + str(c["client_tel"] or "—") + '</div>'
    if c['type'] == 'livraison':
        content += '<div style="font-size:13px;color:#64748b">📍 ' + str(c["adresse_livraison"] or "—") + '</div>'
        content += '<div style="font-size:13px;color:#64748b">🛵 Livreur : ' + str(c["livreur_nom"] or "Non assigné") + '</div>'
    content += '</div></div>'

    content += '<div class="card"><h2>✏️ Changer le statut</h2>'
    content += '<form method="post">'
    content += '<div style="display:flex;gap:10px">'
    content += '<select name="statut" style="flex:1">'
    for s in ['nouvelle', 'en_preparation', 'prete', 'en_livraison', 'livree', 'annulee']:
        sel = ' selected' if c['statut'] == s else ''
        content += '<option value="' + s + '"' + sel + '>' + s + '</option>'
    content += '</select>'
    content += '<button type="submit" class="btn btn-success">💾 Mettre à jour</button>'
    content += '</div></form></div>'

    return render_page(content, active='commandes', page_title='Commande')


# ═══════════════════════════════════════════════════════════════
# 👥 CLIENTS
# ═══════════════════════════════════════════════════════════════

@app.route('/clients')
@login_required
def clients_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()

    sql = "SELECT * FROM clients WHERE 1=1"
    params = []
    if q:
        sql += " AND (nom LIKE ? OR prenom LIKE ? OR telephone LIKE ? OR code LIKE ?)"
        params += [f'%{q}%'] * 4
    sql += " ORDER BY id DESC LIMIT 300"
    cur.execute(sql, params)
    clients = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM clients WHERE statut='actif'")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM clients WHERE niveau='or'")
    stats['or'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(total_depense),0) FROM clients")
    stats['ca'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(total_depense),0) FROM clients WHERE nb_commandes > 0")
    stats['panier'] = cur.fetchone()[0]

    rows = ''
    for c in clients:
        niveau_badge = {'bronze': 'badge-orange', 'argent': 'badge-gray', 'or': 'badge-gold'}.get(c['niveau'], 'badge-gray')
        rows += (
            '<tr><td><strong style="color:#dc2626">' + str(c["code"] or "—") + '</strong></td>'
            + '<td><strong>' + str(c["prenom"] or "") + ' ' + str(c["nom"]) + '</strong></td>'
            + '<td>' + str(c["telephone"] or "—") + '</td>'
            + '<td style="text-align:center">' + str(c["nb_commandes"]) + '</td>'
            + '<td style="text-align:right">' + f'{c["total_depense"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center;color:#f59e0b;font-weight:800">' + str(c["points_fidelite"]) + '</td>'
            + '<td><span class="badge ' + niveau_badge + '">' + str(c["niveau"]) + '</span></td>'
            + '<td><a href="/clients/' + str(c["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👥 Clients — ' + str(len(clients)) + '</h1>'
    content += '<a href="/clients/nouveau" class="btn btn-primary">+ Nouveau client</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">👥</div><div class="kpi-label">Clients actifs</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">🥇</div><div class="kpi-label">Niveau Or</div><div class="kpi-value">' + str(stats["or"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">CA total</div><div class="kpi-value" style="font-size:16px">' + f'{stats["ca"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🛒</div><div class="kpi-label">Panier moyen</div><div class="kpi-value" style="font-size:16px">' + f'{stats["panier"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher client, téléphone..." style="max-width:500px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Nom</th><th>Téléphone</th><th style="text-align:center">Commandes</th>'
    content += '<th style="text-align:right">Total dépensé</th><th style="text-align:center">Points</th><th>Niveau</th><th>Actions</th></tr></thead>'
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
                INSERT INTO clients (code, nom, prenom, telephone, email, adresse, ville,
                                       points_fidelite, niveau, nb_commandes, total_depense,
                                       statut, created_at)
                VALUES (?,?,?,?,?,?,?,0,'bronze',0,0,'actif',?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('prenom'),
                  request.form.get('telephone'),
                  request.form.get('email'),
                  request.form.get('adresse'),
                  request.form.get('ville') or 'Dakar',
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Client créé', 'success')
            return redirect('/clients')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>👥 Nouveau client</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Nom *</label><input type="text" name="nom" required autofocus></div>'
    content += '<div><label>Prénom</label><input type="text" name="prenom"></div>'
    content += '<div><label>Téléphone *</label><input type="text" name="telephone" required placeholder="+221 77 XXX XX XX"></div>'
    content += '<div><label>Email</label><input type="email" name="email"></div>'
    content += '<div style="grid-column:1/-1"><label>Adresse</label><input type="text" name="adresse"></div>'
    content += '<div><label>Ville</label><input type="text" name="ville" value="Dakar"></div>'
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
        SELECT * FROM commandes WHERE client_id=?
        ORDER BY id DESC LIMIT 20
    """, (cid,))
    commandes = cur.fetchall()
    cmd_html = ''
    for cmd in commandes:
        statut_badge = {
            'nouvelle': 'badge-red', 'en_preparation': 'badge-orange', 'prete': 'badge-gold',
            'en_livraison': 'badge-blue', 'livree': 'badge-green', 'annulee': 'badge-gray'
        }.get(cmd['statut'], 'badge-gray')
        cmd_html += (
            '<tr><td><strong>' + str(cmd["numero"]) + '</strong></td>'
            + '<td>' + str(cmd["type"]).replace('_', ' ') + '</td>'
            + '<td style="text-align:right">' + f'{cmd["montant_total"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(cmd["statut"]) + '</span></td>'
            + '<td>' + str((cmd["date_commande"] or "")[:16]) + '</td></tr>'
        )

    # Fidélité
    cur.execute("SELECT * FROM fidelite_transactions WHERE client_id=? ORDER BY id DESC LIMIT 20", (cid,))
    fid = cur.fetchall()
    fid_html = ''
    for f in fid:
        type_badge = 'badge-green' if f['type'] == 'gain' else 'badge-orange'
        fid_html += (
            '<tr><td>' + str((f["date_transaction"] or "")[:10]) + '</td>'
            + '<td><span class="badge ' + type_badge + '">' + str(f["type"]) + '</span></td>'
            + '<td style="text-align:center;font-weight:800">' + ('+' if f["type"] == 'gain' else '-') + str(f["points"]) + '</td>'
            + '<td>' + str(f["description"] or "") + '</td></tr>'
        )

    niveau_badge = {'bronze': 'badge-orange', 'argent': 'badge-gray', 'or': 'badge-gold'}.get(c['niveau'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">👥 ' + str(c["prenom"] or "") + ' ' + str(c["nom"]) + ' <span class="badge ' + niveau_badge + '">' + str(c["niveau"]) + '</span></h1>'
    content += '<a href="/clients" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-label">Code</div><div class="kpi-value" style="font-size:16px">' + str(c["code"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Total dépensé</div><div class="kpi-value" style="font-size:16px">' + f'{c["total_depense"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Points fidélité</div><div class="kpi-value">' + str(c["points_fidelite"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Commandes</div><div class="kpi-value">' + str(c["nb_commandes"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📋 Informations</h2><table>'
    content += '<tr><td><strong>Téléphone</strong></td><td>' + str(c["telephone"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Email</strong></td><td>' + str(c["email"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Adresse</strong></td><td>' + str(c["adresse"] or "—") + ', ' + str(c["ville"] or "") + '</td></tr>'
    content += '<tr><td><strong>Dernière commande</strong></td><td>' + str((c["derniere_commande"] or "—")[:10]) + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>🛒 Historique commandes (' + str(len(commandes)) + ')</h2>'
    content += '<table><thead><tr><th>N°</th><th>Type</th><th style="text-align:right">Montant</th><th>Statut</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (cmd_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucune commande</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>🎁 Historique fidélité (' + str(len(fid)) + ')</h2>'
    content += '<table><thead><tr><th>Date</th><th>Type</th><th style="text-align:center">Points</th><th>Description</th></tr></thead>'
    content += '<tbody>' + (fid_html or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucune transaction</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='clients', page_title='Client')


# ═══════════════════════════════════════════════════════════════
# 🛵 LIVREURS
# ═══════════════════════════════════════════════════════════════

@app.route('/livreurs')
@login_required
def livreurs_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT l.*,
               (SELECT COUNT(*) FROM commandes WHERE livreur_id=l.id AND statut='en_livraison') AS en_cours
        FROM livreurs l
        ORDER BY l.nom
    """)
    livreurs = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM livreurs WHERE statut='disponible'")
    stats['dispo'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM livreurs")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM livreurs WHERE statut='en_livraison'")
    stats['en_liv'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(note_moyenne),0) FROM livreurs")
    stats['note'] = cur.fetchone()[0]

    rows = ''
    for l in livreurs:
        statut_badge = {
            'disponible': 'badge-green',
            'en_livraison': 'badge-orange',
            'indisponible': 'badge-gray',
            'repos': 'badge-blue',
        }.get(l['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong style="color:#dc2626">' + str(l["code"] or "—") + '</strong></td>'
            + '<td><strong>' + str(l["nom"]) + '</strong></td>'
            + '<td>' + str(l["telephone"] or "—") + '</td>'
            + '<td>' + str(l["vehicule"] or "—") + ' · ' + str(l["immatriculation"] or "") + '</td>'
            + '<td>' + str(l["zone"] or "—") + '</td>'
            + '<td style="text-align:center">⭐ ' + f'{l["note_moyenne"]:.1f}' + '</td>'
            + '<td style="text-align:center">' + str(l["nb_livraisons"]) + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(l["statut"]) + '</span></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🛵 Livreurs — ' + str(len(livreurs)) + '</h1>'
    content += '<a href="/livreurs/nouveau" class="btn btn-primary">+ Nouveau livreur</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">🛵</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Disponibles</div><div class="kpi-value">' + str(stats["dispo"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">🔵</div><div class="kpi-label">En livraison</div><div class="kpi-value">' + str(stats["en_liv"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">⭐</div><div class="kpi-label">Note moyenne</div><div class="kpi-value">' + f'{stats["note"]:.1f}' + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Nom</th><th>Téléphone</th><th>Véhicule</th><th>Zone</th><th style="text-align:center">Note</th><th style="text-align:center">Livraisons</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun livreur</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='livreurs', page_title='Livreurs')


@app.route('/livreurs/nouveau', methods=['GET', 'POST'])
@login_required
def livreurs_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO livreurs (code, nom, prenom, telephone, vehicule, immatriculation,
                                        zone, statut, note_moyenne, nb_livraisons, created_at)
                VALUES (?,?,?,?,?,?,?, 'disponible', 5.0, 0, ?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('prenom'),
                  request.form.get('telephone'),
                  request.form.get('vehicule'),
                  request.form.get('immatriculation'),
                  request.form.get('zone'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Livreur créé', 'success')
            return redirect('/livreurs')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>🛵 Nouveau livreur</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Nom *</label><input type="text" name="nom" required autofocus></div>'
    content += '<div><label>Prénom</label><input type="text" name="prenom"></div>'
    content += '<div><label>Téléphone *</label><input type="text" name="telephone" required></div>'
    content += '<div><label>Véhicule</label><select name="vehicule">'
    content += '<option value="moto">🏍️ Moto</option>'
    content += '<option value="scooter">🛵 Scooter</option>'
    content += '<option value="velo">🚲 Vélo</option>'
    content += '<option value="voiture">🚗 Voiture</option>'
    content += '</select></div>'
    content += '<div><label>Immatriculation</label><input type="text" name="immatriculation"></div>'
    content += '<div><label>Zone</label><input type="text" name="zone" placeholder="Dakar Centre"></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/livreurs" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='livreurs', page_title='Nouveau livreur')


# ═══════════════════════════════════════════════════════════════
# 🛵 LIVRAISONS & TRACKING GPS
# ═══════════════════════════════════════════════════════════════

@app.route('/livraisons')
@login_required
def livraisons_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, cl.nom AS client_nom, cl.prenom AS client_prenom, cl.telephone AS client_tel,
               l.nom AS livreur_nom, l.telephone AS livreur_tel
        FROM commandes c
        LEFT JOIN clients cl ON cl.id=c.client_id
        LEFT JOIN livreurs l ON l.id=c.livreur_id
        WHERE c.type='livraison' AND c.statut IN ('en_preparation','prete','en_livraison')
        ORDER BY c.id DESC
    """)
    livraisons = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM commandes WHERE type='livraison' AND statut='en_livraison'")
    stats['en_cours'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM commandes WHERE type='livraison' AND statut='prete'")
    stats['attente'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM commandes WHERE type='livraison' AND date(date_livraison)=date('now')")
    stats['livrees_jour'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM livreurs WHERE statut='disponible'")
    stats['dispo'] = cur.fetchone()[0]

    cards = ''
    for l in livraisons:
        statut_badge = {'en_preparation': 'badge-orange', 'prete': 'badge-gold', 'en_livraison': 'badge-blue'}.get(l['statut'], 'badge-gray')
        cards += '<div class="card" style="border-left-color:#dc2626">'
        cards += '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">'
        cards += '<div><div style="font-weight:900;color:#dc2626;font-size:16px">' + str(l["numero"]) + '</div>'
        cards += '<div style="font-size:13px;color:#64748b;margin-top:4px">' + str(l["client_prenom"] or "") + ' ' + str(l["client_nom"] or "—") + '</div></div>'
        cards += '<span class="badge ' + statut_badge + '">' + str(l["statut"]) + '</span></div>'
        cards += '<div style="background:#f8fafc;padding:12px;border-radius:8px;font-size:13px">'
        cards += '<div>📍 <strong>' + str(l["adresse_livraison"] or "—") + '</strong></div>'
        cards += '<div>📞 ' + str(l["telephone_livraison"] or l["client_tel"] or "—") + '</div>'
        cards += '<div>🛵 Livreur : ' + str(l["livreur_nom"] or "Non assigné") + '</div>'
        cards += '<div style="font-weight:800;color:#10b981;margin-top:6px">💰 ' + f'{l["montant_total"]:,.0f}' + ' F</div>'
        cards += '</div>'
        cards += '<div style="margin-top:10px;display:flex;gap:6px">'
        cards += '<a href="/commandes/' + str(l["id"]) + '" class="btn btn-primary" style="padding:6px 10px;font-size:12px;flex:1;text-align:center">👁 Détails</a>'
        if not l['livreur_id']:
            cards += '<a href="/livraisons/' + str(l["id"]) + '/assigner" class="btn btn-gold" style="padding:6px 10px;font-size:12px;flex:1;text-align:center">🛵 Assigner</a>'
        else:
            cards += '<a href="/livraisons/' + str(l["id"]) + '/tracker" class="btn btn-success" style="padding:6px 10px;font-size:12px;flex:1;text-align:center">📍 Suivi GPS</a>'
        cards += '</div></div>'

    content = '<h1>🛵 Livraisons en cours — ' + str(len(livraisons)) + '</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">🛵</div><div class="kpi-label">En livraison</div><div class="kpi-value">' + str(stats["en_cours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">⏳</div><div class="kpi-label">Prêtes à partir</div><div class="kpi-value">' + str(stats["attente"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Livrées aujourd\'hui</div><div class="kpi-value">' + str(stats["livrees_jour"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-icon">🛵</div><div class="kpi-label">Livreurs dispo</div><div class="kpi-value">' + str(stats["dispo"]) + '</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px">' + (cards or '<p style="grid-column:1/-1;text-align:center;color:#94a3b8;padding:40px">Aucune livraison en cours</p>') + '</div>'

    return render_page(content, active='livraisons', page_title='Livraisons')


@app.route('/livraisons/<int:cid>/assigner', methods=['GET', 'POST'])
@login_required
def livraisons_assigner(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM commandes WHERE id=?", (cid,))
    c = cur.fetchone()
    if not c:
        flash('❌ Commande introuvable', 'error')
        return redirect('/livraisons')

    if request.method == 'POST':
        try:
            livreur_id = int(request.form.get('livreur_id') or 0)
            cur.execute("UPDATE commandes SET livreur_id=?, statut='en_livraison', date_livraison=? WHERE id=?",
                        (livreur_id, datetime.now().isoformat(), cid))
            cur.execute("UPDATE livreurs SET statut='en_livraison' WHERE id=?", (livreur_id,))
            db.commit()
            flash('✅ Livreur assigné', 'success')
            return redirect('/livraisons/' + str(cid) + '/tracker')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT * FROM livreurs WHERE statut='disponible' ORDER BY nom")
    livreurs = cur.fetchall()
    opts = ''.join('<option value="' + str(l["id"]) + '">' + str(l["nom"]) + ' — ' + str(l["zone"] or "") + ' (' + str(l["vehicule"] or "") + ')</option>' for l in livreurs)

    content = '<h1>🛵 Assigner un livreur</h1>'
    content += '<div class="card" style="max-width:600px">'
    content += '<h2>Commande ' + str(c["numero"]) + '</h2>'
    content += '<p style="color:#64748b;margin-bottom:20px">📍 ' + str(c["adresse_livraison"] or "—") + '</p>'
    content += '<form method="post">'
    content += '<div style="margin-bottom:16px"><label>Livreur *</label><select name="livreur_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts + '</select></div>'
    content += '<button type="submit" class="btn btn-success">💾 Assigner</button>'
    content += '<a href="/livraisons" class="btn btn-secondary" style="margin-left:8px">Annuler</a>'
    content += '</form></div>'
    return render_page(content, active='livraisons', page_title='Assigner livreur')


@app.route('/livraisons/<int:cid>/tracker', methods=['GET', 'POST'])
@login_required
def livraisons_tracker(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, cl.nom AS client_nom, cl.prenom AS client_prenom,
               l.nom AS livreur_nom, l.telephone AS livreur_tel, l.vehicule, l.immatriculation
        FROM commandes c
        LEFT JOIN clients cl ON cl.id=c.client_id
        LEFT JOIN livreurs l ON l.id=c.livreur_id
        WHERE c.id=?
    """, (cid,))
    c = cur.fetchone()
    if not c:
        flash('❌ Commande introuvable', 'error')
        return redirect('/livraisons')

    if request.method == 'POST':
        try:
            lat = float(request.form.get('latitude') or 14.6928)
            lng = float(request.form.get('longitude') or -17.4467)
            statut = request.form.get('statut') or c['statut']
            cur.execute("""
                INSERT INTO livraison_tracking (commande_id, livreur_id, latitude, longitude, statut, date_position, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (cid, c['livreur_id'], lat, lng, statut,
                  datetime.now().isoformat(), datetime.now().isoformat()))
            if statut == 'livree':
                cur.execute("UPDATE commandes SET statut='livree', date_livraison=? WHERE id=?",
                            (datetime.now().isoformat(), cid))
                if c['livreur_id']:
                    cur.execute("UPDATE livreurs SET statut='disponible', nb_livraisons=nb_livraisons+1 WHERE id=?",
                                (c['livreur_id'],))
            db.commit()
            flash('✅ Position enregistrée', 'success')
            return redirect('/livraisons/' + str(cid) + '/tracker')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("""
        SELECT * FROM livraison_tracking WHERE commande_id=?
        ORDER BY id DESC LIMIT 20
    """, (cid,))
    tracking = cur.fetchall()
    tracking_html = ''
    for t in tracking:
        tracking_html += (
            '<tr><td>' + str((t["date_position"] or "")[:16]) + '</td>'
            + '<td>' + f'{t["latitude"]:.4f}, {t["longitude"]:.4f}' + '</td>'
            + '<td>' + str(t["statut"] or "") + '</td></tr>'
        )

    statut_badge = {
        'en_preparation': 'badge-orange', 'prete': 'badge-gold',
        'en_livraison': 'badge-blue', 'livree': 'badge-green'
    }.get(c['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📍 Suivi livraison ' + str(c["numero"]) + ' <span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></h1>'
    content += '<a href="/livraisons" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-label">Client</div><div class="kpi-value" style="font-size:16px">' + str(c["client_prenom"] or "") + ' ' + str(c["client_nom"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Livreur</div><div class="kpi-value" style="font-size:16px">' + str(c["livreur_nom"] or "Non assigné") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Montant</div><div class="kpi-value" style="font-size:18px">' + f'{c["montant_total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Positions</div><div class="kpi-value">' + str(len(tracking)) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>📍 Adresse de livraison</h2>'
    content += '<div style="padding:14px;background:#f8fafc;border-radius:8px">'
    content += '<div style="font-weight:700;color:#1e293b">' + str(c["adresse_livraison"] or "—") + '</div>'
    content += '<div style="font-size:13px;color:#64748b;margin-top:6px">📞 ' + str(c["telephone_livraison"] or "—") + '</div>'
    content += '</div></div>'

    content += '<div class="card"><h2>🛵 Nouvelle position</h2>'
    content += '<form method="post">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div><label>Latitude</label><input type="number" step="0.0001" name="latitude" value="14.6928"></div>'
    content += '<div><label>Longitude</label><input type="number" step="0.0001" name="longitude" value="-17.4467"></div>'
    content += '<div style="grid-column:1/-1"><label>Statut</label><select name="statut">'
    for st in ['en_livraison', 'livree']:
        sel = ' selected' if c['statut'] == st else ''
        content += '<option value="' + st + '"' + sel + '>' + st + '</option>'
    content += '</select></div></div>'
    content += '<div style="margin-top:16px"><button type="submit" class="btn btn-success">📍 Enregistrer position</button></div>'
    content += '</form></div>'

    if tracking:
        content += '<div class="card"><h2>📊 Historique positions</h2>'
        content += '<table><thead><tr><th>Date</th><th>Position GPS</th><th>Statut</th></tr></thead>'
        content += '<tbody>' + tracking_html + '</tbody></table></div>'

    return render_page(content, active='livraisons', page_title='Suivi livraison')


# ═══════════════════════════════════════════════════════════════
# 📦 STOCKS INGRÉDIENTS
# ═══════════════════════════════════════════════════════════════

@app.route('/stocks')
@login_required
def stocks_liste():
    db = get_db()
    cur = db.cursor()
    alerte_f = request.args.get('alerte') == '1'

    sql = "SELECT * FROM ingredients"
    if alerte_f:
        sql += " WHERE quantite_stock <= seuil_alerte"
    sql += " ORDER BY nom"
    cur.execute(sql)
    ingredients = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM ingredients")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ingredients WHERE quantite_stock <= seuil_alerte")
    stats['alertes'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(quantite_stock * prix_unitaire),0) FROM ingredients")
    stats['valeur'] = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(*) FROM ingredients
        WHERE date_peremption IS NOT NULL
        AND date(date_peremption) <= date('now', '+15 days')
    """)
    stats['peremption'] = cur.fetchone()[0]

    rows = ''
    for i in ingredients:
        is_alerte = i['quantite_stock'] <= i['seuil_alerte']
        bg = '#fef2f2' if is_alerte else '#fff'
        badge = '<span class="badge badge-red">⚠ ALERTE</span>' if is_alerte else '<span class="badge badge-green">OK</span>'

        jours_per = ''
        if i['date_peremption']:
            try:
                dp = datetime.strptime(i['date_peremption'][:10], '%Y-%m-%d')
                j = (dp - datetime.now()).days
                if j < 0:
                    jours_per = '<span class="badge badge-red">Périmé</span>'
                elif j < 15:
                    jours_per = '<span class="badge badge-orange">' + str(j) + 'j</span>'
            except Exception:
                pass

        rows += (
            '<tr style="background:' + bg + '">'
            + '<td><strong>' + str(i["nom"]) + '</strong></td>'
            + '<td>' + str(i["categorie"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{i["quantite_stock"]:.1f}' + ' ' + str(i["unite"] or "") + '</td>'
            + '<td style="text-align:right">' + f'{i["seuil_alerte"]:.1f}' + '</td>'
            + '<td style="text-align:right">' + f'{i["prix_unitaire"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right">' + f'{i["quantite_stock"] * i["prix_unitaire"]:,.0f}' + ' F</td>'
            + '<td>' + str((i["date_peremption"] or "—")[:10]) + ' ' + jours_per + '</td>'
            + '<td>' + badge + '</td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📦 Stocks ingrédients — ' + str(len(ingredients)) + '</h1>'
    content += '<a href="/stocks/nouveau" class="btn btn-primary">+ Nouvel ingrédient</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">📦</div><div class="kpi-label">Ingrédients</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">⚠️</div><div class="kpi-label">Alertes</div><div class="kpi-value">' + str(stats["alertes"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">💰</div><div class="kpi-label">Valeur stock</div><div class="kpi-value" style="font-size:16px">' + f'{stats["valeur"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">⏰</div><div class="kpi-label">DLC proche</div><div class="kpi-value">' + str(stats["peremption"]) + '</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/stocks" class="btn ' + ('btn-primary' if not alerte_f else 'btn-secondary') + '">Tous</a> '
    content += '<a href="/stocks?alerte=1" class="btn ' + ('btn-danger' if alerte_f else 'btn-secondary') + '" style="margin-left:6px">⚠ Alertes seulement</a>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Nom</th><th>Catégorie</th><th style="text-align:right">Stock</th><th style="text-align:right">Seuil</th>'
    content += '<th style="text-align:right">Prix U.</th><th style="text-align:right">Valeur</th><th>DLC</th><th>État</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucun ingrédient</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='stocks', page_title='Stocks')


@app.route('/stocks/nouveau', methods=['GET', 'POST'])
@login_required
def stocks_nouveau():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO ingredients (code, nom, categorie, unite, quantite_stock,
                                           seuil_alerte, prix_unitaire, fournisseur,
                                           date_peremption, emplacement, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (None,
                  request.form.get('nom'),
                  request.form.get('categorie'),
                  request.form.get('unite') or 'kg',
                  float(request.form.get('quantite_stock') or 0),
                  float(request.form.get('seuil_alerte') or 0),
                  float(request.form.get('prix_unitaire') or 0),
                  request.form.get('fournisseur'),
                  request.form.get('date_peremption'),
                  request.form.get('emplacement'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Ingrédient créé', 'success')
            return redirect('/stocks')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>📦 Nouvel ingrédient</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Nom *</label><input type="text" name="nom" required autofocus></div>'
    content += '<div><label>Catégorie</label><input type="text" name="categorie" placeholder="Viandes, légumes..."></div>'
    content += '<div><label>Unité</label><select name="unite">'
    for u in ['kg', 'g', 'L', 'cl', 'unité', 'boîte', 'sachet']:
        content += '<option value="' + u + '">' + u + '</option>'
    content += '</select></div>'
    content += '<div><label>Quantité en stock</label><input type="number" step="0.1" name="quantite_stock" value="0"></div>'
    content += '<div><label>Seuil d\'alerte</label><input type="number" step="0.1" name="seuil_alerte" value="5"></div>'
    content += '<div><label>Prix unitaire (FCFA)</label><input type="number" step="100" name="prix_unitaire" value="1000"></div>'
    content += '<div><label>Fournisseur</label><input type="text" name="fournisseur"></div>'
    content += '<div><label>Date péremption</label><input type="date" name="date_peremption"></div>'
    content += '<div><label>Emplacement</label><input type="text" name="emplacement" placeholder="Frigo A, Étagère B..."></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/stocks" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='stocks', page_title='Nouvel ingrédient')


# ═══════════════════════════════════════════════════════════════
# 🖥️ POS TACTILE (Point de Vente)
# ═══════════════════════════════════════════════════════════════

@app.route('/pos')
@login_required
def pos_interface():
    db = get_db()
    cur = db.cursor()

    # Session ouverte ?
    cur.execute("""
        SELECT s.*, r.nom AS restaurant_nom
        FROM caissiers_sessions s
        LEFT JOIN restaurants r ON r.id=s.restaurant_id
        WHERE s.caissier_id=? AND s.statut='ouverte'
        ORDER BY s.id DESC LIMIT 1
    """, (current_user.id,))
    session_row = cur.fetchone()

    if not session_row:
        flash('⚠️ Aucune caisse ouverte. Ouvrez une caisse pour utiliser le POS.', 'error')
        return redirect('/caisse/sessions/ouvrir')

    cur.execute("""
        SELECT p.id, p.nom, p.prix, p.description, p.temps_preparation,
               c.nom AS categorie_nom, c.icone AS categorie_icone
        FROM plats p
        LEFT JOIN categories c ON c.id=p.categorie_id
        WHERE p.disponible=1
        ORDER BY c.ordre, p.nom LIMIT 100
    """)
    plats = cur.fetchall()

    cards_html = ''
    for p in plats:
        icon = str(p['categorie_icone'] or '🍽️')
        nom_html = (p['nom'] or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
        cards_html += (
            '<div class="pos-plat" data-id="' + str(p['id']) + '" '
            + 'data-nom="' + nom_html + '" '
            + 'data-prix="' + str(p['prix']) + '">'
            + '<div style="text-align:center;font-size:28px;margin-bottom:6px">' + icon + '</div>'
            + '<div style="font-weight:700;color:#1e293b;font-size:12.5px;line-height:1.2;margin-bottom:6px">' + nom_html + '</div>'
            + '<div style="font-weight:900;color:#10b981;font-size:15px;text-align:center">' + f'{p["prix"]:,.0f}' + ' F</div>'
            + '</div>'
        )

    pos_html = '''
    <div style="display:grid;grid-template-columns:1fr 380px;gap:16px">
      <div>
        <input type="text" id="pos-search" placeholder="🔍 Rechercher un plat (Ctrl+K)" autofocus style="width:100%;padding:14px;border:3px solid #dc2626;border-radius:10px;font-size:16px;margin-bottom:12px">
        <div class="pos-grid" id="pos-grid">''' + cards_html + '''</div>
      </div>
      <div class="pos-cart">
        <h3 style="margin-top:0;color:#dc2626">🛒 Commande</h3>
        <div style="font-size:12px;color:#64748b;margin-bottom:10px">Session ' + str(session_row['id']) + ' — ' + str(session_row['restaurant_nom'] or '') + '</div>
        <div id="cart-items" style="min-height:200px;max-height:400px;overflow-y:auto"></div>
        <div style="margin-top:16px;padding-top:16px;border-top:2px solid #e5e7eb">
          <div style="display:flex;justify-content:space-between;font-size:14px">
            <span>Total</span><span id="cart-total" style="font-weight:800;font-size:22px;color:#10b981">0 F</span>
          </div>
        </div>
        <div style="margin-top:14px">
          <label style="font-size:12px;font-weight:600">Type commande</label>
          <select id="order-type" style="width:100%;padding:10px;border:2px solid #e5e7eb;border-radius:8px">
            <option value="sur_place">🍽️ Sur place</option>
            <option value="emporter">🥡 À emporter</option>
            <option value="livraison">🛵 Livraison</option>
          </select>
        </div>
        <div style="margin-top:10px">
          <label style="font-size:12px;font-weight:600">Mode de paiement</label>
          <select id="payment-mode" style="width:100%;padding:10px;border:2px solid #e5e7eb;border-radius:8px">
            <option value="especes">💵 Espèces</option>
            <option value="mobile_money">📱 Mobile Money</option>
            <option value="carte">💳 Carte</option>
          </select>
        </div>
        <button onclick="submitSale()" style="width:100%;margin-top:16px;padding:16px;background:#10b981;color:#fff;border:none;border-radius:10px;font-weight:800;font-size:16px;cursor:pointer">
          ✅ Encaisser <span id="btn-total">0</span> F
        </button>
        <button onclick="clearCart()" style="width:100%;margin-top:8px;padding:10px;background:#e5e7eb;color:#374151;border:none;border-radius:8px;font-weight:600;cursor:pointer">
          🗑 Vider
        </button>
      </div>
    </div>

    <script>
    var cart = {};

    function addToCart(id, nom, prix) {
      if (cart[id]) { cart[id].qte += 1; }
      else { cart[id] = { id: id, nom: nom, prix: prix, qte: 1 }; }
      renderCart();
    }

    function removeFromCart(id) {
      delete cart[id];
      renderCart();
    }

    function renderCart() {
      var cont = document.getElementById('cart-items');
      var ids = Object.keys(cart);
      if (ids.length === 0) {
        cont.innerHTML = '<div style="text-align:center;color:#9ca3af;padding:40px 0;font-size:13px">Panier vide</div>';
        document.getElementById('cart-total').textContent = '0 F';
        document.getElementById('btn-total').textContent = '0';
        return;
      }
      var html = '';
      var total = 0;
      ids.forEach(function(k) {
        var it = cart[k];
        var st = it.prix * it.qte;
        total += st;
        html += '<div class="cart-line">' +
          '<div><strong>' + it.nom + '</strong><br><small style="color:#6b7280">' + it.qte + ' x ' + it.prix.toLocaleString('fr-FR') + ' F</small></div>' +
          '<div style="display:flex;align-items:center;gap:8px"><strong>' + st.toLocaleString('fr-FR') + ' F</strong>' +
          '<button onclick="removeFromCart(' + it.id + ')">X</button></div>' +
          '</div>';
      });
      cont.innerHTML = html;
      document.getElementById('cart-total').textContent = total.toLocaleString('fr-FR') + ' F';
      document.getElementById('btn-total').textContent = total.toLocaleString('fr-FR');
    }

    function clearCart() {
      cart = {};
      renderCart();
    }

    function filterProducts() {
      var q = document.getElementById('pos-search').value.toLowerCase().trim();
      document.querySelectorAll('.pos-plat').forEach(function(el) {
        var match = el.textContent.toLowerCase().indexOf(q) !== -1;
        el.style.display = match ? 'block' : 'none';
      });
    }

    document.getElementById('pos-search').addEventListener('input', filterProducts);

    document.addEventListener('keydown', function(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('pos-search').focus();
      }
    });

    function submitSale() {
      var ids = Object.keys(cart);
      if (ids.length === 0) { alert('Panier vide'); return; }
      var type = document.getElementById('order-type').value;
      var mode = document.getElementById('payment-mode').value;
      var items = ids.map(function(k) {
        return { plat_id: cart[k].id, quantite: cart[k].qte, prix_unitaire: cart[k].prix, nom_plat: cart[k].nom };
      });
      fetch('/api/pos/commande', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: items, type: type, mode_paiement: mode })
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.ok) {
          alert('Commande ' + data.numero + ' enregistrée — Total : ' + data.total.toLocaleString('fr-FR') + ' F');
          clearCart();
          location.reload();
        } else {
          alert('Erreur : ' + (data.error || 'inconnue'));
        }
      })
      .catch(function(e) { alert('Erreur réseau : ' + e.message); });
    }

    document.querySelectorAll('.pos-plat[data-id]').forEach(function(el) {
      el.addEventListener('click', function() {
        var id = parseInt(this.dataset.id);
        var nom = this.dataset.nom;
        var prix = parseFloat(this.dataset.prix);
        addToCart(id, nom, prix);
      });
    });

    renderCart();
    </script>
    '''
    return render_page(pos_html, active='pos', page_title='POS')


@app.route('/api/pos/commande', methods=['POST'])
@login_required
def api_pos_commande():
    db = get_db()
    cur = db.cursor()
    data = request.get_json() or {}
    items = data.get('items', [])
    type_cmd = data.get('type') or 'sur_place'
    mode = data.get('mode_paiement') or 'especes'

    if not items:
        return jsonify({'ok': False, 'error': 'Panier vide'}), 400

    try:
        cur.execute("""
            SELECT * FROM caissiers_sessions
            WHERE caissier_id=? AND statut='ouverte'
            ORDER BY id DESC LIMIT 1
        """, (current_user.id,))
        session_row = cur.fetchone()
        if not session_row:
            return jsonify({'ok': False, 'error': 'Aucune caisse ouverte'}), 400

        total = sum(it['quantite'] * it['prix_unitaire'] for it in items)

        cur.execute("""
            INSERT INTO commandes
            (numero, restaurant_id, caissier_id, type, statut, montant_sous_total,
             frais_livraison, remise, montant_total, mode_paiement, date_commande,
             session_id, created_at)
            VALUES (?,?,?,?, 'nouvelle', ?,0,0,?,?,?,?,?)
        """, (None, session_row['restaurant_id'], current_user.id, type_cmd,
              total, total, mode, datetime.now().isoformat(),
              session_row['id'], datetime.now().isoformat()))
        commande_id = cur.lastrowid

        cur.execute("SELECT numero FROM commandes WHERE id=?", (commande_id,))
        numero = (cur.fetchone() or {})['numero'] or ''

        for it in items:
            cur.execute("""
                INSERT INTO commande_lignes (commande_id, plat_id, nom_plat, prix_unitaire, quantite, montant)
                VALUES (?,?,?,?,?,?)
            """, (commande_id, it['plat_id'], it.get('nom_plat', ''),
                  it['prix_unitaire'], it['quantite'],
                  it['quantite'] * it['prix_unitaire']))

        db.commit()
        log_action(current_user.id, 'COMMANDE_POS', f'{numero} — {total} F', 'commandes', commande_id)
        return jsonify({'ok': True, 'numero': numero, 'total': total, 'commande_id': commande_id})
    except Exception as e:
        db.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# 💰 SESSIONS CAISSIERS
# ═══════════════════════════════════════════════════════════════

@app.route('/caisse/sessions')
@login_required
def caisse_sessions():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.*, u.nom_complet AS caissier_nom, r.nom AS restaurant_nom
        FROM caissiers_sessions s
        LEFT JOIN users u ON u.id=s.caissier_id
        LEFT JOIN restaurants r ON r.id=s.restaurant_id
        ORDER BY s.id DESC LIMIT 100
    """)
    sessions = cur.fetchall()

    rows = ''
    for s in sessions:
        statut_color = '#10b981' if s['statut'] == 'ouverte' else '#6b7280'
        ecart_color = '#ef4444' if abs(s['ecart'] or 0) > 100 else '#10b981'
        btn_close = f'<a href="/caisse/sessions/{s["id"]}/fermer" class="btn btn-danger" style="padding:5px 12px;font-size:12px;margin-left:4px">🔒</a>' if s['statut'] == 'ouverte' else ''
        rows += (
            '<tr><td>#' + str(s["id"]) + '</td>'
            + '<td><strong>' + str(s["caissier_nom"] or "—") + '</strong></td>'
            + '<td>' + str(s["restaurant_nom"] or "—") + '</td>'
            + '<td>' + str((s["date_ouverture"] or "")[:16]) + '</td>'
            + '<td>' + ((s["date_fermeture"] or "—")[:16] if s["date_fermeture"] else "—") + '</td>'
            + '<td style="text-align:center">' + str(s["nb_commandes"]) + '</td>'
            + '<td style="text-align:right;font-weight:800">' + f'{s["total_ventes"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;color:' + ecart_color + ';font-weight:700">' + f'{s["ecart"]:,.0f}' + ' F</td>'
            + '<td><span class="badge" style="background:' + statut_color + ';color:#fff">' + str(s["statut"]) + '</span></td>'
            + '<td><a href="/caisse/sessions/' + str(s["id"]) + '" class="btn btn-primary" style="padding:5px 12px;font-size:12px">👁</a>' + btn_close + '</td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">💰 Sessions caissiers</h1>'
    content += '<a href="/caisse/sessions/ouvrir" class="btn btn-success">+ Ouvrir une caisse</a></div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>#</th><th>Caissier</th><th>Restaurant</th><th>Ouverture</th><th>Fermeture</th>'
    content += '<th style="text-align:center">Commandes</th><th style="text-align:right">Total ventes</th>'
    content += '<th style="text-align:right">Écart</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="10" style="padding:40px;text-align:center;color:#94a3b8">Aucune session</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='caisse', page_title='Sessions caissiers')


@app.route('/caisse/sessions/ouvrir', methods=['GET', 'POST'])
@login_required
def caisse_session_ouvrir():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            restaurant_id = int(request.form.get('restaurant_id') or 0)
            fonds_initial = float(request.form.get('fonds_initial') or 0)
            notes = request.form.get('notes_ouverture') or ''

            cur.execute("SELECT COUNT(*) FROM caissiers_sessions WHERE caissier_id=? AND statut='ouverte'", (current_user.id,))
            if cur.fetchone()[0] > 0:
                flash('❌ Vous avez déjà une caisse ouverte', 'error')
                return redirect('/caisse/sessions')

            cur.execute("""
                INSERT INTO caissiers_sessions
                (caissier_id, restaurant_id, date_ouverture, fonds_initial, statut, notes_ouverture, created_at)
                VALUES (?,?,?,?,'ouverte',?,?)
            """, (current_user.id, restaurant_id, datetime.now().isoformat(),
                  fonds_initial, notes, datetime.now().isoformat()))
            db.commit()
            log_action(current_user.id, 'OUVERTURE_CAISSE', f'Fonds: {fonds_initial}',
                       'caissiers_sessions', cur.lastrowid)
            flash('✅ Caisse ouverte — Fonds : ' + f'{fonds_initial:,.0f}' + ' F', 'success')
            return redirect('/caisse/sessions')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom, ville FROM restaurants WHERE statut='ouvert'")
    restos = cur.fetchall()
    opts = ''.join('<option value="' + str(r["id"]) + '">' + str(r["nom"]) + ' (' + str(r["ville"] or "") + ')</option>' for r in restos)

    content = '<h1>💰 Ouvrir une caisse</h1>'
    content += '<form method="post" class="card" style="max-width:600px">'
    content += '<div style="margin-bottom:16px"><label>Restaurant *</label>'
    content += '<select name="restaurant_id" required style="width:100%">'
    content += '<option value="">— Sélectionner —</option>' + opts + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Fonds initial (FCFA) *</label>'
    content += '<input type="number" name="fonds_initial" required value="50000" min="0" step="1000" autofocus></div>'
    content += '<div style="margin-bottom:16px"><label>Notes</label>'
    content += '<textarea name="notes_ouverture" rows="3"></textarea></div>'
    content += '<button type="submit" class="btn btn-success">💰 Ouvrir la caisse</button>'
    content += '<a href="/caisse/sessions" class="btn btn-secondary" style="margin-left:8px">Annuler</a>'
    content += '</form>'
    return render_page(content, active='caisse', page_title='Ouvrir caisse')


@app.route('/caisse/sessions/<int:sid>')
@login_required
def caisse_session_detail(sid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.*, u.nom_complet AS caissier_nom, r.nom AS restaurant_nom
        FROM caissiers_sessions s
        LEFT JOIN users u ON u.id=s.caissier_id
        LEFT JOIN restaurants r ON r.id=s.restaurant_id
        WHERE s.id=?
    """, (sid,))
    s = cur.fetchone()
    if not s:
        flash('❌ Session introuvable', 'error')
        return redirect('/caisse/sessions')

    cur.execute("""
        SELECT c.*, cl.nom AS client_nom, cl.prenom AS client_prenom
        FROM commandes c
        LEFT JOIN clients cl ON cl.id=c.client_id
        WHERE c.session_id=?
        ORDER BY c.id DESC
    """, (sid,))
    commandes = cur.fetchall()
    cmd_html = ''
    for c in commandes:
        cmd_html += (
            '<tr><td><strong>' + str(c["numero"]) + '</strong></td>'
            + '<td>' + str(c["type"]).replace('_', ' ') + '</td>'
            + '<td>' + str(c["client_prenom"] or "") + ' ' + str(c["client_nom"] or "—") + '</td>'
            + '<td style="text-align:right;font-weight:800">' + f'{c["montant_total"]:,.0f}' + ' F</td>'
            + '<td>' + str(c["mode_paiement"] or "—") + '</td></tr>'
        )

    cur.execute("SELECT * FROM caissiers_paiements WHERE session_id=? ORDER BY id DESC", (sid,))
    paiements = cur.fetchall()
    pai_html = ''
    for p in paiements:
        pai_html += (
            '<tr><td>' + str((p["date_paiement"] or "")[:16]) + '</td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{p["montant"]:,.0f}' + ' F</td>'
            + '<td>' + str(p["mode"]) + '</td>'
            + '<td>' + str(p["reference"] or "—") + '</td></tr>'
        )

    ecart_color = '#ef4444' if abs(s['ecart'] or 0) > 100 else '#10b981'

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">💰 Session #' + str(s["id"]) + '</h1>'
    content += '<div><a href="/caisse/sessions/' + str(sid) + '/verser" class="btn btn-primary">💳 Versement</a> '
    content += '<a href="/caisse/sessions" class="btn btn-secondary" style="margin-left:6px">← Retour</a></div></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-label">Caissier</div><div class="kpi-value" style="font-size:16px">' + str(s["caissier_nom"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Commandes</div><div class="kpi-value">' + str(s["nb_commandes"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Total FCFA</div><div class="kpi-value" style="font-size:18px">' + f'{s["total_ventes"]:,.0f}' + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-label">Espèces</div><div class="kpi-value" style="font-size:18px">' + f'{s["total_especes"]:,.0f}' + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div class="kpi-label">Mobile Money</div><div class="kpi-value" style="font-size:18px">' + f'{s["total_mobile_money"]:,.0f}' + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>💰 Détail</h2><table>'
    content += '<tr><td>Fonds initial</td><td style="text-align:right">' + f'{s["fonds_initial"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td>Espèces</td><td style="text-align:right">' + f'{s["total_especes"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td>Mobile Money</td><td style="text-align:right">' + f'{s["total_mobile_money"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td>Carte</td><td style="text-align:right">' + f'{s["total_carte"]:,.0f}' + ' F</td></tr>'
    content += '<tr style="background:#f0fdf4;font-weight:800"><td>Total ventes</td><td style="text-align:right">' + f'{s["total_ventes"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td>Montant compté</td><td style="text-align:right">' + f'{s["montant_compte"]:,.0f}' + ' F</td></tr>'
    content += '<tr style="background:#fef2f2;font-weight:800"><td>Écart</td><td style="text-align:right;color:' + ecart_color + '">' + f'{s["ecart"]:,.0f}' + ' F</td></tr>'
    content += '</table></div>'

    if commandes:
        content += '<div class="card"><h2>🛒 Commandes de la session (' + str(len(commandes)) + ')</h2>'
        content += '<table><thead><tr><th>N°</th><th>Type</th><th>Client</th><th style="text-align:right">Montant</th><th>Paiement</th></tr></thead>'
        content += '<tbody>' + cmd_html + '</tbody></table></div>'

    if paiements:
        content += '<div class="card"><h2>💳 Versements gérant (' + str(len(paiements)) + ')</h2>'
        content += '<table><thead><tr><th>Date</th><th style="text-align:right">Montant</th><th>Mode</th><th>Référence</th></tr></thead>'
        content += '<tbody>' + pai_html + '</tbody></table></div>'

    return render_page(content, active='caisse', page_title='Session caisse')


@app.route('/caisse/sessions/<int:sid>/fermer', methods=['GET', 'POST'])
@login_required
def caisse_session_fermer(sid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM caissiers_sessions WHERE id=?", (sid,))
    s = cur.fetchone()
    if not s:
        flash('❌ Session introuvable', 'error')
        return redirect('/caisse/sessions')

    if request.method == 'POST':
        try:
            montant_compte = float(request.form.get('montant_compte') or 0)
            notes = request.form.get('notes_fermeture') or ''

            cur.execute("SELECT COALESCE(SUM(montant),0) FROM caissiers_paiements WHERE session_id=?", (sid,))
            deja_verse = cur.fetchone()[0]
            attendu = (s['fonds_initial'] or 0) + (s['total_especes'] or 0) - deja_verse
            ecart = montant_compte - attendu

            cur.execute("""
                UPDATE caissiers_sessions SET
                    date_fermeture=?, montant_compte=?, ecart=?, statut='fermee', notes_fermeture=?
                WHERE id=?
            """, (datetime.now().isoformat(), montant_compte, ecart, notes, sid))
            db.commit()
            log_action(current_user.id, 'FERMETURE_CAISSE', f'Compté: {montant_compte}, Écart: {ecart}',
                       'caissiers_sessions', sid)
            flash('✅ Caisse fermée — Écart : ' + f'{ecart:,.0f}' + ' F', 'success')
            return redirect('/caisse/sessions/' + str(sid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT COALESCE(SUM(montant),0) FROM caissiers_paiements WHERE session_id=?", (sid,))
    deja_verse = cur.fetchone()[0]
    attendu = (s['fonds_initial'] or 0) + (s['total_especes'] or 0) - deja_verse

    content = '<h1>🔒 Fermer la caisse #' + str(sid) + '</h1>'
    content += '<form method="post" class="card" style="max-width:600px">'
    content += '<div style="background:#fff7ed;padding:14px;border-radius:8px;margin-bottom:16px;font-size:13px">'
    content += '<strong>Attendu en caisse</strong> : ' + f'{attendu:,.0f}' + ' F</div>'
    content += '<div style="margin-bottom:16px"><label>Montant compté (FCFA) *</label>'
    content += '<input type="number" name="montant_compte" required step="100" autofocus style="width:100%;font-size:20px;padding:14px"></div>'
    content += '<div style="margin-bottom:16px"><label>Notes de fermeture</label>'
    content += '<textarea name="notes_fermeture" rows="3"></textarea></div>'
    content += '<button type="submit" class="btn btn-danger">🔒 Fermer la caisse</button>'
    content += '<a href="/caisse/sessions/' + str(sid) + '" class="btn btn-secondary" style="margin-left:8px">Annuler</a>'
    content += '</form>'
    return render_page(content, active='caisse', page_title='Fermer caisse')


@app.route('/caisse/sessions/<int:sid>/verser', methods=['GET', 'POST'])
@login_required
def caisse_session_verser(sid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM caissiers_sessions WHERE id=?", (sid,))
    s = cur.fetchone()
    if not s:
        flash('❌ Session introuvable', 'error')
        return redirect('/caisse/sessions')

    if request.method == 'POST':
        try:
            montant = float(request.form.get('montant') or 0)
            mode = request.form.get('mode') or 'especes'
            reference = request.form.get('reference') or ''

            cur.execute("""
                INSERT INTO caissiers_paiements
                (session_id, caissier_id, montant, mode, reference, statut, recu_par, date_paiement, created_at)
                VALUES (?,?,?,?,?,'valide',?,?,?)
            """, (sid, s['caissier_id'], montant, mode, reference,
                  current_user.id, datetime.now().isoformat(), datetime.now().isoformat()))
            db.commit()
            flash('✅ Versement de ' + f'{montant:,.0f}' + ' F enregistré', 'success')
            return redirect('/caisse/sessions/' + str(sid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>💳 Versement gérant — Session #' + str(sid) + '</h1>'
    content += '<form method="post" class="card" style="max-width:600px">'
    content += '<div style="margin-bottom:16px"><label>Montant (FCFA) *</label>'
    content += '<input type="number" name="montant" required step="100" min="100" autofocus style="width:100%;font-size:20px;padding:14px"></div>'
    content += '<div style="margin-bottom:16px"><label>Mode</label><select name="mode">'
    content += '<option value="especes">💵 Espèces</option>'
    content += '<option value="mobile_money">📱 Mobile Money</option>'
    content += '<option value="virement">🏦 Virement</option>'
    content += '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Référence</label>'
    content += '<input type="text" name="reference"></div>'
    content += '<button type="submit" class="btn btn-success">💳 Enregistrer</button>'
    content += '<a href="/caisse/sessions/' + str(sid) + '" class="btn btn-secondary" style="margin-left:8px">Annuler</a>'
    content += '</form>'
    return render_page(content, active='caisse', page_title='Versement')


# ═══════════════════════════════════════════════════════════════
# 💵 ÉTATS FINANCIERS PAR CAISSIER
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

    ca_jour = sc("SELECT COALESCE(SUM(montant_total),0) FROM commandes WHERE date(date_commande)=date('now')")
    ca_mois = sc("SELECT COALESCE(SUM(montant_total),0) FROM commandes WHERE strftime('%Y-%m',date_commande)=strftime('%Y-%m','now')")
    ca_an = sc("SELECT COALESCE(SUM(montant_total),0) FROM commandes")
    nb_cmd = sc("SELECT COUNT(*) FROM commandes")
    panier_moy = (ca_an / nb_cmd) if nb_cmd > 0 else 0

    # CA par caissier (30 jours)
    cur.execute("""
        SELECT u.id, u.nom_complet, COUNT(c.id) AS nb_commandes,
               COALESCE(SUM(c.montant_total),0) AS ca
        FROM users u
        LEFT JOIN commandes c ON c.caissier_id=u.id
            AND c.date_commande >= date('now', '-30 days')
        WHERE u.role='caissier'
        GROUP BY u.id
        ORDER BY ca DESC
    """)
    caissiers = cur.fetchall()
    caissiers_html = ''
    for c in caissiers:
        caissiers_html += (
            '<tr><td><strong>' + str(c["nom_complet"]) + '</strong></td>'
            + '<td style="text-align:center">' + str(c["nb_commandes"]) + '</td>'
            + '<td style="text-align:right;color:#10b981;font-weight:800">' + f'{c["ca"]:,.0f}' + ' F</td></tr>'
        )

    # Répartition par mode paiement
    cur.execute("""
        SELECT COALESCE(mode_paiement,'inconnu') AS mode, COUNT(*) AS nb,
               COALESCE(SUM(montant_total),0) AS total
        FROM commandes GROUP BY mode_paiement
    """)
    modes = cur.fetchall()
    modes_html = ''.join(
        '<tr><td>' + str(m["mode"]) + '</td>'
        + '<td style="text-align:right">' + str(m["nb"]) + '</td>'
        + '<td style="text-align:right;font-weight:800">' + f'{m["total"]:,.0f}' + ' F</td></tr>'
        for m in modes
    )

    # Répartition par type commande
    cur.execute("""
        SELECT type, COUNT(*) AS nb, COALESCE(SUM(montant_total),0) AS total
        FROM commandes GROUP BY type
    """)
    types = cur.fetchall()
    types_html = ''.join(
        '<tr><td>' + str(t["type"]).replace('_', ' ') + '</td>'
        + '<td style="text-align:right">' + str(t["nb"]) + '</td>'
        + '<td style="text-align:right;font-weight:800">' + f'{t["total"]:,.0f}' + ' F</td></tr>'
        for t in types
    )

    content = '<h1>💵 États financiers</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">💰</div><div class="kpi-label">CA du jour</div><div class="kpi-value" style="font-size:18px">' + f'{ca_jour:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">📅</div><div class="kpi-label">CA du mois</div><div class="kpi-value" style="font-size:18px">' + f'{ca_mois:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">📊</div><div class="kpi-label">CA annuel</div><div class="kpi-value" style="font-size:18px">' + f'{ca_an:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🛒</div><div class="kpi-label">Panier moyen</div><div class="kpi-value" style="font-size:16px">' + f'{panier_moy:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>👤 CA par caissier (30 jours)</h2>'
    content += '<table><thead><tr><th>Caissier</th><th style="text-align:center">Commandes</th><th style="text-align:right">CA</th></tr></thead>'
    content += '<tbody>' + (caissiers_html or '<tr><td colspan="3" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>💳 Répartition par paiement</h2>'
    content += '<table><thead><tr><th>Mode</th><th style="text-align:right">Nb</th><th style="text-align:right">Total</th></tr></thead>'
    content += '<tbody>' + (modes_html or '<tr><td colspan="3" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>🛒 Répartition par type</h2>'
    content += '<table><thead><tr><th>Type</th><th style="text-align:right">Nb</th><th style="text-align:right">Total</th></tr></thead>'
    content += '<tbody>' + (types_html or '<tr><td colspan="3" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    content += '<div style="margin-top:20px;display:flex;gap:10px;flex-wrap:wrap">'
    content += '<a href="/finances/export-csv" class="btn btn-primary">⬇ Export CSV</a>'
    content += '<a href="/finances/rapport.pdf" class="btn btn-gold">📄 Rapport PDF</a>'
    content += '<a href="/caisse/sessions" class="btn btn-success">💰 Sessions caissiers</a>'
    content += '</div>'

    return render_page(content, active='finances', page_title='Finances')


@app.route('/finances/export-csv')
@login_required
def finances_export_csv():
    import csv
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.numero, c.date_commande, c.montant_total, c.mode_paiement, c.type,
               u.nom_complet AS caissier, cl.nom AS client_nom
        FROM commandes c
        LEFT JOIN users u ON u.id=c.caissier_id
        LEFT JOIN clients cl ON cl.id=c.client_id
        ORDER BY c.id DESC LIMIT 1000
    """)
    rows = cur.fetchall()

    si = io.StringIO()
    w = csv.writer(si, delimiter=';')
    w.writerow(['N°', 'Date', 'Montant', 'Mode', 'Type', 'Caissier', 'Client'])
    for r in rows:
        w.writerow([r['numero'], r['date_commande'], r['montant_total'],
                    r['mode_paiement'], r['type'], r['caissier'], r['client_nom']])

    log_action(current_user.id, 'EXPORT_CSV', f'{len(rows)} lignes', 'commandes')
    return Response(si.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment;filename=resto_ventes_{datetime.now().strftime("%Y%m%d")}.csv'})


@app.route('/finances/rapport.pdf')
@login_required
def finances_rapport_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    db = get_db()
    cur = db.cursor()

    def sc(sql, default=0):
        cur.execute(sql)
        r = cur.fetchone()
        return r[0] if r and r[0] is not None else default

    ca_an = sc("SELECT COALESCE(SUM(montant_total),0) FROM commandes")
    ca_mois = sc("SELECT COALESCE(SUM(montant_total),0) FROM commandes WHERE strftime('%Y-%m',date_commande)=strftime('%Y-%m','now')")
    nb_cmd = sc("SELECT COUNT(*) FROM commandes")

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    c.setFillColor(colors.HexColor('#dc2626'))
    c.rect(0, h - 30*mm, w, 30*mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#f59e0b'))
    c.rect(0, h - 30*mm, w, 3*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(15*mm, h - 15*mm, "OMEGA RESTO")
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, h - 21*mm, "Rapport financier")
    c.drawRightString(w - 15*mm, h - 15*mm, datetime.now().strftime('%d/%m/%Y'))

    y = h - 45*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 13)
    c.drawString(15*mm, y, "CHIFFRE D'AFFAIRES")
    y -= 10*mm
    c.setFont('Helvetica', 11)
    c.drawString(15*mm, y, "CA annuel total : " + f'{ca_an:,.0f}' + " FCFA")
    y -= 6*mm
    c.drawString(15*mm, y, "CA mois en cours : " + f'{ca_mois:,.0f}' + " FCFA")
    y -= 6*mm
    c.drawString(15*mm, y, "Nombre de commandes : " + str(nb_cmd))
    y -= 6*mm
    c.drawString(15*mm, y, "Panier moyen : " + f'{(ca_an/nb_cmd if nb_cmd else 0):,.0f}' + " FCFA")

    y -= 15*mm
    c.setFont('Helvetica-Bold', 13)
    c.drawString(15*mm, y, "CA PAR CAISSIER (30 JOURS)")
    y -= 8*mm
    c.setFont('Helvetica-Bold', 10)
    c.drawString(15*mm, y, "Caissier")
    c.drawRightString(90*mm, y, "Cmd")
    c.drawRightString(w - 15*mm, y, "CA FCFA")
    y -= 5*mm
    c.setFont('Helvetica', 10)

    cur.execute("""
        SELECT u.nom_complet, COUNT(c.id) AS nb, COALESCE(SUM(c.montant_total),0) AS ca
        FROM users u
        LEFT JOIN commandes c ON c.caissier_id=u.id AND c.date_commande >= date('now', '-30 days')
        WHERE u.role='caissier'
        GROUP BY u.id ORDER BY ca DESC
    """)
    for row in cur.fetchall():
        c.drawString(15*mm, y, str(row['nom_complet'])[:40])
        c.drawRightString(90*mm, y, str(row['nb']))
        c.drawRightString(w - 15*mm, y, f'{row["ca"]:,.0f}')
        y -= 5*mm
        if y < 40*mm:
            c.showPage()
            y = h - 20*mm

    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica', 7)
    c.drawString(15*mm, 10*mm, "OMEGA RESTO · Restauration & Livraison · Sénégal")

    c.showPage()
    c.save()
    buf.seek(0)

    log_action(current_user.id, 'RAPPORT_FINANCIER_PDF', 'Rapport finances', 'finances')
    return send_file(buf, mimetype='application/pdf',
                     download_name=f'rapport_resto_{datetime.now().strftime("%Y%m%d")}.pdf')


# ═══════════════════════════════════════════════════════════════
# ⭐ AVIS
# ═══════════════════════════════════════════════════════════════

@app.route('/avis')
@login_required
def avis_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT a.*, cl.nom, cl.prenom, p.nom AS plat_nom, c.numero AS commande_numero
        FROM avis a
        LEFT JOIN clients cl ON cl.id=a.client_id
        LEFT JOIN plats p ON p.id=a.plat_id
        LEFT JOIN commandes c ON c.id=a.commande_id
        ORDER BY a.id DESC LIMIT 200
    """)
    avis = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM avis")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(note),0) FROM avis")
    stats['moy'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM avis WHERE note >= 4")
    stats['pos'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM avis WHERE note <= 2")
    stats['neg'] = cur.fetchone()[0]

    rows = ''
    for a in avis:
        stars = '⭐' * (a['note'] or 0)
        rows += (
            '<tr><td>' + str(a["prenom"] or "") + ' ' + str(a["nom"] or "Client") + '</td>'
            + '<td>' + str(a["plat_nom"] or "—") + '</td>'
            + '<td style="color:#f59e0b;font-size:14px">' + stars + '</td>'
            + '<td>' + str(a["commentaire"] or "") + '</td>'
            + '<td>' + str((a["date_avis"] or "—")[:10]) + '</td></tr>'
        )

    content = '<h1>⭐ Avis clients — ' + str(len(avis)) + '</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">⭐</div><div class="kpi-label">Total avis</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">📊</div><div class="kpi-label">Note moyenne</div><div class="kpi-value">' + f'{stats["moy"]:.1f}' + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">👍</div><div class="kpi-label">Positifs</div><div class="kpi-value">' + str(stats["pos"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">👎</div><div class="kpi-label">Négatifs</div><div class="kpi-value">' + str(stats["neg"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Client</th><th>Plat</th><th>Note</th><th>Commentaire</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="5" style="padding:40px;text-align:center;color:#94a3b8">Aucun avis</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='avis', page_title='Avis')


# ═══════════════════════════════════════════════════════════════
# 🎁 FIDÉLITÉ
# ═══════════════════════════════════════════════════════════════

@app.route('/fidelite')
@login_required
def fidelite_index():
    db = get_db()
    cur = db.cursor()

    # Top clients fidèles
    cur.execute("""
        SELECT * FROM clients
        WHERE statut='actif' AND nb_commandes > 0
        ORDER BY points_fidelite DESC LIMIT 20
    """)
    top = cur.fetchall()
    top_html = ''
    for c in top:
        niveau_badge = {'bronze': 'badge-orange', 'argent': 'badge-gray', 'or': 'badge-gold'}.get(c['niveau'], 'badge-gray')
        top_html += (
            '<tr><td><strong>' + str(c["prenom"] or "") + ' ' + str(c["nom"]) + '</strong></td>'
            + '<td style="text-align:center">' + str(c["nb_commandes"]) + '</td>'
            + '<td style="text-align:right">' + f'{c["total_depense"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center;color:#f59e0b;font-weight:800">' + str(c["points_fidelite"]) + '</td>'
            + '<td><span class="badge ' + niveau_badge + '">' + str(c["niveau"]) + '</span></td></tr>'
        )

    # Transactions récentes
    cur.execute("""
        SELECT f.*, c.nom, c.prenom
        FROM fidelite_transactions f
        LEFT JOIN clients c ON c.id=f.client_id
        ORDER BY f.id DESC LIMIT 20
    """)
    trans = cur.fetchall()
    trans_html = ''
    for t in trans:
        type_badge = 'badge-green' if t['type'] == 'gain' else 'badge-orange'
        trans_html += (
            '<tr><td>' + str((t["date_transaction"] or "")[:16]) + '</td>'
            + '<td>' + str(t["prenom"] or "") + ' ' + str(t["nom"] or "—") + '</td>'
            + '<td><span class="badge ' + type_badge + '">' + str(t["type"]) + '</span></td>'
            + '<td style="text-align:center;font-weight:800;color:' + ('#10b981' if t['type'] == 'gain' else '#ef4444') + '">' + ('+' if t['type'] == 'gain' else '-') + str(t["points"]) + '</td>'
            + '<td>' + str(t["description"] or "") + '</td></tr>'
        )

    stats = {}
    cur.execute("SELECT COUNT(*) FROM clients WHERE niveau='or'")
    stats['or'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM clients WHERE niveau='argent'")
    stats['argent'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(points_fidelite),0) FROM clients")
    stats['points'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM fidelite_transactions")
    stats['trans'] = cur.fetchone()[0]

    content = '<h1>🎁 Programme de fidélité</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">🥇</div><div class="kpi-label">Clients Or</div><div class="kpi-value">' + str(stats["or"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#64748b,#475569)"><div class="kpi-icon">🥈</div><div class="kpi-label">Clients Argent</div><div class="kpi-value">' + str(stats["argent"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">🎁</div><div class="kpi-label">Points cumulés</div><div class="kpi-value" style="font-size:16px">' + f'{stats["points"]:,}' + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">📊</div><div class="kpi-label">Transactions</div><div class="kpi-value">' + str(stats["trans"]) + '</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>🏆 Top 20 clients fidèles</h2>'
    content += '<table><thead><tr><th>Client</th><th style="text-align:center">Commandes</th><th style="text-align:right">Total</th><th style="text-align:center">Points</th><th>Niveau</th></tr></thead>'
    content += '<tbody>' + (top_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucun client</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>📊 Transactions récentes</h2>'
    content += '<table><thead><tr><th>Date</th><th>Client</th><th>Type</th><th style="text-align:center">Points</th><th>Description</th></tr></thead>'
    content += '<tbody>' + (trans_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucune transaction</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    content += '<div class="card" style="border-left-color:#f59e0b"><h2>🎯 Programme fidélité</h2>'
    content += '<ul style="line-height:2;color:#334155;font-size:14px">'
    content += '<li>🥉 <strong>Bronze</strong> : 0 - 199 points</li>'
    content += '<li>🥈 <strong>Argent</strong> : 200 - 499 points</li>'
    content += '<li>🥇 <strong>Or</strong> : 500+ points — 10% de réduction permanente</li>'
    content += '<li>💡 <strong>1 point</strong> = 1 000 F dépensés</li>'
    content += '<li>🎁 <strong>Récompenses</strong> : plat gratuit, boisson offerte, dessert</li>'
    content += '</ul></div>'

    return render_page(content, active='fidelite', page_title='Fidélité')


# ═══════════════════════════════════════════════════════════════
# 🤖 IA RECOMMANDATION
# ═══════════════════════════════════════════════════════════════

@app.route('/ia')
@login_required
def ia_index():
    db = get_db()
    cur = db.cursor()

    # Top plats recommandés (statistiques)
    cur.execute("""
        SELECT p.id, p.nom, p.prix, p.note_moyenne, c.icone AS cat_icone,
               COUNT(cl.id) AS nb_commandes,
               COALESCE(SUM(cl.quantite),0) AS qte_vendue
        FROM plats p
        LEFT JOIN categories c ON c.id=p.categorie_id
        LEFT JOIN commande_lignes cl ON cl.plat_id=p.id
        WHERE p.disponible=1
        GROUP BY p.id
        ORDER BY qte_vendue DESC LIMIT 10
    """)
    top_plats = cur.fetchall()

    plats_html = ''
    for p in top_plats:
        score = min(100, (p['qte_vendue'] or 0) * 3 + (p['note_moyenne'] or 0) * 10)
        plats_html += (
            '<tr><td>' + str(p["cat_icone"] or "🍽️") + ' <strong>' + str(p["nom"]) + '</strong></td>'
            + '<td style="text-align:right">' + f'{p["prix"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center">' + f'{p["note_moyenne"]:.1f}' + ' ⭐</td>'
            + '<td style="text-align:center">' + str(int(p["qte_vendue"])) + '</td>'
            + '<td style="min-width:120px"><div style="background:#e2e8f0;border-radius:6px;overflow:hidden;height:12px">'
            + '<div style="background:linear-gradient(90deg,#dc2626,#f59e0b);height:100%;width:' + f'{score:.0f}' + '%"></div></div></td></tr>'
        )

    # Analyse clients - plats préférés par client
    cur.execute("""
        SELECT c.id, c.nom, c.prenom, COUNT(DISTINCT cmd.id) AS nb_cmds,
               c.total_depense, c.niveau,
               (SELECT p.nom FROM commande_lignes cl
                JOIN plats p ON p.id=cl.plat_id
                JOIN commandes cc ON cc.id=cl.commande_id
                WHERE cc.client_id=c.id
                GROUP BY cl.plat_id
                ORDER BY SUM(cl.quantite) DESC LIMIT 1) AS plat_prefere
        FROM clients c
        LEFT JOIN commandes cmd ON cmd.client_id=c.id
        WHERE c.nb_commandes > 0
        GROUP BY c.id
        ORDER BY c.total_depense DESC LIMIT 15
    """)
    clients_ia = cur.fetchall()
    clients_html = ''
    for c in clients_ia:
        niveau_badge = {'bronze': 'badge-orange', 'argent': 'badge-gray', 'or': 'badge-gold'}.get(c['niveau'], 'badge-gray')
        clients_html += (
            '<tr><td><strong>' + str(c["prenom"] or "") + ' ' + str(c["nom"]) + '</strong> <span class="badge ' + niveau_badge + '">' + str(c["niveau"]) + '</span></td>'
            + '<td style="text-align:center">' + str(c["nb_cmds"]) + '</td>'
            + '<td style="text-align:right">' + f'{c["total_depense"]:,.0f}' + ' F</td>'
            + '<td><em>' + str(c["plat_prefere"] or "—") + '</em></td></tr>'
        )

    stats = {}
    cur.execute("SELECT COUNT(*) FROM plats WHERE disponible=1")
    stats['plats'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(note_moyenne),0) FROM plats WHERE note_moyenne > 0")
    stats['note'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM clients WHERE nb_commandes > 0")
    stats['clients_actifs'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM commandes")
    stats['cmd'] = cur.fetchone()[0]

    content = '<h1>🤖 IA & Recommandations</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-icon">🍽️</div><div class="kpi-label">Plats analysés</div><div class="kpi-value">' + str(stats["plats"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-icon">⭐</div><div class="kpi-label">Note moyenne</div><div class="kpi-value">' + f'{stats["note"]:.1f}' + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">👥</div><div class="kpi-label">Clients actifs</div><div class="kpi-value">' + str(stats["clients_actifs"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">📊</div><div class="kpi-label">Commandes</div><div class="kpi-value">' + str(stats["cmd"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>🏆 Top plats recommandés (algorithme de popularité)</h2>'
    content += '<p style="color:#64748b;font-size:13px;margin-bottom:14px">Score calculé selon : ventes × 3 + note × 10</p>'
    content += '<table><thead><tr><th>Plat</th><th style="text-align:right">Prix</th><th style="text-align:center">Note</th><th style="text-align:center">Vendus</th><th>Score IA</th></tr></thead>'
    content += '<tbody>' + (plats_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>👤 Recommandations personnalisées par client</h2>'
    content += '<table><thead><tr><th>Client</th><th style="text-align:center">Commandes</th><th style="text-align:right">Total dépensé</th><th>Plat préféré</th></tr></thead>'
    content += '<tbody>' + (clients_html or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'

    content += '<div class="card" style="border-left-color:#8b5cf6"><h2>🧠 Intelligence artificielle</h2>'
    content += '<ul style="line-height:2;color:#334155;font-size:14px">'
    content += '<li>📊 <strong>Analyse historique</strong> : basé sur les ventes passées</li>'
    content += '<li>🎯 <strong>Recommandations personnalisées</strong> : chaque client voit son plat préféré</li>'
    content += '<li>💡 <strong>Suggestion panier</strong> : +30% panier moyen (accord mets-boissons)</li>'
    content += '<li>🔮 <strong>Prédiction stock</strong> : anticipe les besoins en ingrédients</li>'
    content += '<li>⭐ <strong>Filtrage collaboratif</strong> : "clients qui aiment X aiment aussi Y"</li>'
    content += '</ul></div>'

    return render_page(content, active='ia', page_title='IA')


# ═══════════════════════════════════════════════════════════════
# 📱 MOBILE CLIENT
# ═══════════════════════════════════════════════════════════════

@app.route('/mobile-client')
@login_required
def mobile_client():
    db = get_db()
    cur = db.cursor()

    def sc(sql, default=0):
        cur.execute(sql)
        r = cur.fetchone()
        return r[0] if r and r[0] is not None else default

    stats = {
        'cmd_jour': sc("SELECT COUNT(*) FROM commandes WHERE date(date_commande)=date('now')"),
        'plats_dispo': sc("SELECT COUNT(*) FROM plats WHERE disponible=1"),
        'livreurs': sc("SELECT COUNT(*) FROM livreurs WHERE statut='disponible'"),
        'clients': sc("SELECT COUNT(*) FROM clients WHERE statut='actif'"),
    }

    content = '<h1>📱 Mobile Client</h1>'
    content += '<div style="background:#fff7ed;border-left:4px solid #dc2626;padding:14px;border-radius:8px;margin-bottom:20px;font-size:13px;color:#c2410c">'
    content += '💡 Interface mobile pour clients — commande, suivi, avis, fidélité'
    content += '</div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#dc2626,#991b1b)"><div class="kpi-label">Commandes du jour</div><div class="kpi-value">' + str(stats["cmd_jour"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Plats disponibles</div><div class="kpi-value">' + str(stats["plats_dispo"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#3b82f6,#1e40af)"><div class="kpi-label">Livreurs</div><div class="kpi-value">' + str(stats["livreurs"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><div class="kpi-label">Clients</div><div class="kpi-value">' + str(stats["clients"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>⚡ Actions rapides</h2>'
    content += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:12px">'
    actions = [
        ('/menu', '📋 Voir le menu', '#dc2626'),
        ('/commandes/nouvelle', '🛒 Commander', '#f59e0b'),
        ('/fidelite', '🎁 Mes points', '#10b981'),
        ('/avis', '⭐ Mes avis', '#8b5cf6'),
    ]
    for url, label, color in actions:
        content += '<a href="' + url + '" style="text-decoration:none"><div style="background:' + color + ';color:#fff;padding:20px;border-radius:10px;text-align:center;font-weight:700;font-size:13px">' + label + '</div></a>'
    content += '</div></div>'

    content += '<div class="card"><h2>🍽️ Plats populaires</h2>'
    cur.execute("""
        SELECT p.nom, p.prix, c.icone AS cat_icone
        FROM plats p
        LEFT JOIN categories c ON c.id=p.categorie_id
        WHERE p.disponible=1
        ORDER BY p.nb_commandes DESC LIMIT 6
    """)
    plats = cur.fetchall()
    rows = ''
    for p in plats:
        rows += (
            '<tr><td>' + str(p["cat_icone"] or "🍽️") + ' ' + str(p["nom"]) + '</td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{p["prix"]:,.0f}' + ' F</td></tr>'
        )
    content += '<table><tbody>' + (rows or '<tr><td colspan="2" style="text-align:center;color:#94a3b8;padding:20px">Aucun plat</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='dashboard', page_title='Mobile Client')


# ═══════════════════════════════════════════════════════════════
# 📊 API JSON
# ═══════════════════════════════════════════════════════════════

@app.route('/api/resto/stats')
@login_required
def api_resto_stats():
    db = get_db()
    cur = db.cursor()
    result = {}
    for k, sql in [
        ('commandes_jour', "SELECT COUNT(*) FROM commandes WHERE date(date_commande)=date('now')"),
        ('ca_jour', "SELECT COALESCE(SUM(montant_total),0) FROM commandes WHERE date(date_commande)=date('now')"),
        ('plats_dispo', "SELECT COUNT(*) FROM plats WHERE disponible=1"),
        ('livreurs_dispo', "SELECT COUNT(*) FROM livreurs WHERE statut='disponible'"),
        ('stocks_alerte', "SELECT COUNT(*) FROM ingredients WHERE quantite_stock <= seuil_alerte"),
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
