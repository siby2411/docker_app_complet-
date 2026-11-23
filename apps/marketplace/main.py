"""
🛒 Marketplace B2B — Application principale
Vendeurs · Produits · Commandes · RFQ · Paiements · Avis
"""
from flask import Flask, render_template_string, redirect, url_for, session, request, jsonify, Response, send_file, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import sqlite3
import os
import io

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'omega-marketplace-secret-2026')

DB_PATH = '/app/data/marketplace.db'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id, username, role, nom_complet, entreprise=''):
        self.id = id
        self.username = username
        self.role = role
        self.nom_complet = nom_complet
        self.entreprise = entreprise


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
        return User(r['id'], r['username'], r['role'], r['nom_complet'], r['entreprise'] or '')
    return None


# ═══════════════════════════════════════════════════════════════
# LAYOUT — DESIGN MARKETPLACE B2B
# ═══════════════════════════════════════════════════════════════

LAYOUT = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — OMEGA MARKETPLACE</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,-apple-system,sans-serif}}
body{{background:#f8fafc;color:#1e293b;font-size:14px}}
.nav{{background:linear-gradient(135deg,#1e40af,#2563eb);color:#fff;padding:0 22px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 3px 12px rgba(0,0,0,.15);flex-wrap:wrap;border-bottom:4px solid #10b981}}
.nav-brand{{font-weight:900;font-size:18px;display:flex;align-items:center;gap:12px;padding:16px 0;letter-spacing:-0.3px}}
.nav-brand-icon{{width:40px;height:40px;background:#10b981;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 4px 12px rgba(16,185,129,.4)}}
.nav-links{{display:flex;gap:2px;flex-wrap:wrap}}
.nav-links a{{color:#dbeafe;text-decoration:none;padding:8px 13px;border-radius:8px;font-size:12.5px;font-weight:600;transition:.2s;display:flex;align-items:center;gap:6px}}
.nav-links a:hover{{background:rgba(255,255,255,.12);color:#fff}}
.nav-links a.active{{background:#10b981;color:#fff;box-shadow:0 4px 10px rgba(16,185,129,.4)}}
.nav-user{{font-size:12.5px;display:flex;gap:10px;align-items:center;color:#dbeafe}}
.nav-user a{{color:#fff;text-decoration:none;background:rgba(0,0,0,.25);padding:7px 14px;border-radius:8px;font-weight:600}}
.nav-cart{{background:#facc15;color:#1e293b;padding:7px 14px;border-radius:8px;font-weight:800;font-size:12.5px;display:flex;align-items:center;gap:6px;text-decoration:none}}
.container{{max-width:1600px;margin:0 auto;padding:24px}}
h1{{color:#1e40af;margin-bottom:20px;font-size:24px;font-weight:800;letter-spacing:-0.4px}}
h2{{color:#2563eb;font-size:18px;margin-bottom:14px;font-weight:700}}
.card{{background:#fff;padding:22px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:18px;border-left:4px solid #10b981}}
table{{width:100%;border-collapse:collapse}}
thead{{background:#1e40af;color:#fff}}
th{{padding:12px;text-align:left;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}}
td{{padding:11px;border-bottom:1px solid #f1f5f9;font-size:13.5px}}
tbody tr:hover{{background:#eff6ff}}
.btn{{display:inline-block;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px;border:none;cursor:pointer;transition:.15s;letter-spacing:.2px}}
.btn:hover{{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.15)}}
.btn-primary{{background:#2563eb;color:#fff}}
.btn-success{{background:#10b981;color:#fff}}
.btn-warning{{background:#facc15;color:#1e293b}}
.btn-danger{{background:#ef4444;color:#fff}}
.btn-secondary{{background:#64748b;color:#fff}}
input,select,textarea{{width:100%;padding:11px 14px;border:2px solid #e2e8f0;border-radius:8px;font-size:13.5px;font-family:inherit;transition:.2s}}
input:focus,select:focus,textarea:focus{{outline:none;border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1)}}
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
.badge-yellow{{background:#fef3c7;color:#b45309}}
.badge-gray{{background:#e2e8f0;color:#475569}}
.product-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}}
.product-card{{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,.08);transition:.2s;display:flex;flex-direction:column}}
.product-card:hover{{transform:translateY(-3px);box-shadow:0 8px 24px rgba(37,99,235,.15)}}
.product-icon{{background:linear-gradient(135deg,#2563eb,#1e40af);color:#fff;height:100px;display:flex;align-items:center;justify-content:center;font-size:44px}}
.product-body{{padding:14px;flex:1;display:flex;flex-direction:column}}
.product-title{{font-weight:700;color:#1e293b;font-size:14px;margin-bottom:4px;line-height:1.3}}
.product-vendeur{{font-size:11.5px;color:#64748b;margin-bottom:10px}}
.product-price{{font-size:18px;font-weight:800;color:#10b981;margin-top:auto}}
.rating{{color:#facc15;font-size:14px}}
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-brand">
    <div class="nav-brand-icon">🛒</div>
    <div>OMEGA MARKET<span style="display:block;font-size:10px;font-weight:500;letter-spacing:2px;color:#dbeafe">B2B · PME CEDEAO</span></div>
  </div>
  <div class="nav-links">
    <a href="/" class="{a_dash}">📊 Dashboard</a>
    <a href="/catalogue" class="{a_cat}">🛍️ Catalogue</a>
    <a href="/vendeurs" class="{a_vnd}">🏪 Vendeurs</a>
    <a href="/rfq" class="{a_rfq}">📋 Devis (RFQ)</a>
    <a href="/commandes" class="{a_cmd}">📦 Commandes</a>
    <a href="/livraisons" class="{a_liv}">🚚 Livraisons</a>
    <a href="/avis" class="{a_avi}">⭐ Avis</a>
    <a href="/analytics" class="{a_ana}">📈 Analytics</a>
  </div>
  <div class="nav-user">
    <a href="/panier" class="nav-cart">🛒 Panier <span id="cart-count">0</span></a>
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


def render_page(content, active='dashboard', page_title='Marketplace'):
    from flask import get_flashed_messages
    user_name = current_user.nom_complet if current_user.is_authenticated else ''
    msgs = get_flashed_messages(with_categories=True)
    flashes = ''
    for cat, msg in msgs:
        flashes += f'<div class="flash flash-{cat}">{msg}</div>'

    # Compter panier
    cart_count = 0
    if current_user.is_authenticated:
        try:
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT COALESCE(SUM(quantite),0) FROM panier WHERE user_id=?", (current_user.id,))
            r = cur.fetchone()
            cart_count = int(r[0]) if r else 0
        except Exception:
            pass

    return LAYOUT.format(
        title=page_title,
        user_name=user_name,
        content=content,
        flashes=flashes,
        a_dash='active' if active == 'dashboard' else '',
        a_cat='active' if active == 'catalogue' else '',
        a_vnd='active' if active == 'vendeurs' else '',
        a_rfq='active' if active == 'rfq' else '',
        a_cmd='active' if active == 'commandes' else '',
        a_liv='active' if active == 'livraisons' else '',
        a_avi='active' if active == 'avis' else '',
        a_ana='active' if active == 'analytics' else '',
    ).replace('<span id="cart-count">0</span>', f'<span id="cart-count">{cart_count}</span>')


@app.route('/health')
def health():
    return {'project': 'OMEGA MARKETPLACE', 'service': 'marketplace-b2b',
            'status': 'ok', 'timestamp': datetime.now().isoformat(), 'version': '1.0'}


LOGIN_HTML = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Connexion — OMEGA Marketplace</title>
<style>body{{font-family:system-ui;background:linear-gradient(135deg,#1e40af,#2563eb);min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0}}
.box{{background:#fff;padding:42px;border-radius:16px;box-shadow:0 25px 70px rgba(0,0,0,.4);width:100%;max-width:420px;border-top:5px solid #10b981}}
.logo{{text-align:center;font-size:56px;margin-bottom:12px}}
h1{{color:#1e40af;margin:0 0 6px;text-align:center;font-size:22px;font-weight:900;letter-spacing:-0.3px}}
.subtitle{{text-align:center;color:#64748b;font-size:12px;margin-bottom:24px;letter-spacing:1.5px;text-transform:uppercase;font-weight:600}}
input{{width:100%;padding:14px;border:2px solid #e2e8f0;border-radius:10px;margin-bottom:14px;font-size:15px;box-sizing:border-box}}
input:focus{{outline:none;border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1)}}
button{{width:100%;background:#10b981;color:#fff;padding:15px;border:none;border-radius:10px;font-weight:800;font-size:15px;cursor:pointer;letter-spacing:.5px;text-transform:uppercase}}
button:hover{{background:#059669}}
.err{{background:#fee2e2;color:#991b1b;padding:11px;border-radius:8px;margin-bottom:14px;font-size:13px;border-left:4px solid #ef4444}}
.hint{{margin-top:20px;padding:12px;background:#eff6ff;border-radius:8px;font-size:12px;color:#1e40af;text-align:center;border:1px dashed #93c5fd}}</style></head>
<body><div class="box">
<div class="logo">🛒</div>
<h1>OMEGA MARKETPLACE</h1>
<div class="subtitle">B2B · PME CEDEAO</div>
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
            user = User(r['id'], r['username'], r['role'], r['nom_complet'], r['entreprise'] or '')
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

    is_vendeur = current_user.role == 'vendeur'

    stats = {
        'vendeurs': sc("SELECT COUNT(*) FROM vendeurs WHERE statut='actif'"),
        'produits': sc("SELECT COUNT(*) FROM produits WHERE statut='actif'"),
        'commandes': sc("SELECT COUNT(*) FROM commandes"),
        'ca_total': sc("SELECT COALESCE(SUM(montant_total),0) FROM commandes"),
        'rfq_ouvertes': sc("SELECT COUNT(*) FROM rfq WHERE statut='ouvert'"),
        'livraisons_encours': sc("SELECT COUNT(*) FROM livraisons WHERE statut IN ('prepare','expedie')"),
        'avis_total': sc("SELECT COUNT(*) FROM avis"),
    }

    # Top vendeurs
    cur.execute("""
        SELECT v.*, (SELECT COUNT(*) FROM produits WHERE vendeur_id=v.id) AS nb_produits
        FROM vendeurs v
        WHERE v.statut='actif'
        ORDER BY v.note_moyenne DESC, v.nb_ventes DESC
        LIMIT 5
    """)
    vendeurs = cur.fetchall()

    vnd_html = ''
    for v in vendeurs:
        stars = '⭐' * int(round(v['note_moyenne'] or 0))
        vnd_html += (
            '<tr><td><strong>' + str(v["code"] or "") + '</strong></td>'
            + '<td><strong>' + str(v["raison_sociale"]) + '</strong><br><small style="color:#64748b">' + str(v["secteur"] or "") + '</small></td>'
            + '<td>' + str(v["ville"] or "—") + '</td>'
            + '<td style="text-align:center">' + str(v["nb_produits"]) + '</td>'
            + '<td><span class="rating">' + (stars or "—") + '</span> ' + f'{v["note_moyenne"]:.1f}' + '</td>'
            + '<td style="text-align:center">' + str(v["nb_ventes"]) + '</td></tr>'
        )

    # Commandes récentes
    cur.execute("""
        SELECT c.*, v.raison_sociale AS vendeur_nom, u.nom_complet AS acheteur_nom
        FROM commandes c
        LEFT JOIN vendeurs v ON v.id=c.vendeur_id
        LEFT JOIN users u ON u.id=c.acheteur_id
        ORDER BY c.id DESC LIMIT 6
    """)
    commandes = cur.fetchall()

    cmd_html = ''
    for c in commandes:
        statut_badge = {
            'en_attente': 'badge-orange',
            'confirmee': 'badge-blue',
            'expediee': 'badge-yellow',
            'livree': 'badge-green',
            'annulee': 'badge-red',
        }.get(c['statut'], 'badge-gray')
        cmd_html += (
            '<tr><td><strong style="color:#2563eb">' + str(c["numero"]) + '</strong></td>'
            + '<td>' + str(c["acheteur_nom"] or "—") + '</td>'
            + '<td>' + str(c["vendeur_nom"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{c["montant_total"]:,.0f}' + ' F</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></td>'
            + '<td>' + str((c["date_commande"] or "—")[:10]) + '</td></tr>'
        )

    content = '<h1>📊 Tableau de bord Marketplace B2B</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#2563eb)"><div class="kpi-icon">🏪</div><div class="kpi-label">Vendeurs actifs</div><div class="kpi-value">' + str(stats["vendeurs"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-icon">📦</div><div class="kpi-label">Produits</div><div class="kpi-value">' + str(stats["produits"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🛒</div><div class="kpi-label">Commandes</div><div class="kpi-value">' + str(stats["commandes"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#facc15,#eab308);color:#1e293b"><div class="kpi-icon">💰</div><div class="kpi-label">Volume total</div><div class="kpi-value" style="font-size:18px">' + f'{stats["ca_total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">📋</div><div class="kpi-label">RFQ ouvertes</div><div class="kpi-value">' + str(stats["rfq_ouvertes"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">🚚</div><div class="kpi-label">Livraisons</div><div class="kpi-value">' + str(stats["livraisons_encours"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div class="kpi-icon">⭐</div><div class="kpi-label">Avis</div><div class="kpi-value">' + str(stats["avis_total"]) + '</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>🏆 Top 5 vendeurs</h2>'
    content += '<table><thead><tr><th>Code</th><th>Vendeur</th><th>Ville</th><th style="text-align:center">Produits</th><th>Note</th><th style="text-align:center">Ventes</th></tr></thead>'
    content += '<tbody>' + (vnd_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:30px">Aucun vendeur</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>🛒 Commandes récentes</h2>'
    content += '<table><thead><tr><th>N°</th><th>Acheteur</th><th>Vendeur</th><th style="text-align:right">Montant</th><th>Statut</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (cmd_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:30px">Aucune commande</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    # Catégories
    cur.execute("SELECT * FROM categories ORDER BY ordre LIMIT 6")
    cats = cur.fetchall()
    content += '<div class="card"><h2>🏷️ Catégories principales</h2>'
    content += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px">'
    for cat in cats:
        content += '<a href="/catalogue?categorie_id=' + str(cat["id"]) + '" style="text-decoration:none">'
        content += '<div style="background:#eff6ff;padding:20px;border-radius:10px;text-align:center;transition:.2s" onmouseover="this.style.background=\'#dbeafe\'" onmouseout="this.style.background=\'#eff6ff\'">'
        content += '<div style="font-size:36px;margin-bottom:8px">' + str(cat["icone"] or "📦") + '</div>'
        content += '<div style="font-weight:700;color:#1e40af;font-size:13px">' + str(cat["nom"]) + '</div>'
        content += '</div></a>'
    content += '</div></div>'

    return render_page(content, active='dashboard', page_title='Dashboard')


# ═══════════════════════════════════════════════════════════════
# 🛍️ CATALOGUE
# ═══════════════════════════════════════════════════════════════

@app.route('/catalogue')
@login_required
def catalogue():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()
    cat_id = request.args.get('categorie_id', '')

    sql = """
        SELECT p.*, v.raison_sociale AS vendeur_nom, v.ville AS vendeur_ville,
               c.nom AS categorie_nom, c.icone AS categorie_icone
        FROM produits p
        LEFT JOIN vendeurs v ON v.id=p.vendeur_id
        LEFT JOIN categories c ON c.id=p.categorie_id
        WHERE p.statut='actif'
    """
    params = []
    if q:
        sql += " AND (p.nom LIKE ? OR p.description LIKE ? OR p.code LIKE ?)"
        params += [f'%{q}%'] * 3
    if cat_id:
        sql += " AND p.categorie_id=?"
        params.append(cat_id)
    sql += " ORDER BY p.nb_ventes DESC, p.id DESC LIMIT 100"
    cur.execute(sql, params)
    produits = cur.fetchall()

    cur.execute("SELECT * FROM categories ORDER BY ordre")
    categories = cur.fetchall()

    cards = ''
    for p in produits:
        stars_count = int(round(p['note_moyenne'] or 0))
        stars = '⭐' * stars_count
        cards += '<div class="product-card">'
        cards += '<div class="product-icon">' + str(p["categorie_icone"] or "📦") + '</div>'
        cards += '<div class="product-body">'
        cards += '<div class="product-title">' + str(p["nom"]) + '</div>'
        cards += '<div class="product-vendeur">🏪 ' + str(p["vendeur_nom"] or "—") + ' · ' + str(p["vendeur_ville"] or "") + '</div>'
        cards += '<div style="font-size:11.5px;color:#64748b;margin-bottom:8px">' + str(p["description"] or "")[:60] + '...</div>'
        cards += '<div class="rating">' + (stars or "—") + ' ' + f'{p["note_moyenne"]:.1f}' + '</div>'
        cards += '<div style="display:flex;justify-content:space-between;align-items:flex-end;margin-top:10px">'
        cards += '<div class="product-price">' + f'{p["prix_unitaire"]:,.0f}' + ' F<span style="font-size:12px;color:#64748b;font-weight:400">/' + str(p["unite"]) + '</span></div>'
        cards += '</div>'
        cards += '<div style="margin-top:10px;display:flex;gap:6px">'
        cards += '<a href="/produit/' + str(p["id"]) + '" class="btn btn-secondary" style="padding:6px 10px;font-size:11.5px;flex:1;text-align:center">👁 Voir</a>'
        cards += '<a href="/panier/ajouter/' + str(p["id"]) + '" class="btn btn-success" style="padding:6px 10px;font-size:11.5px;flex:1;text-align:center">+ Panier</a>'
        cards += '</div></div></div>'

    cats_html = '<a href="/catalogue" class="btn ' + ('btn-primary' if not cat_id else 'btn-secondary') + '">Toutes</a> '
    for c in categories:
        active_cls = 'btn-primary' if str(cat_id) == str(c['id']) else 'btn-secondary'
        cats_html += '<a href="/catalogue?categorie_id=' + str(c["id"]) + '" class="btn ' + active_cls + '" style="margin-left:6px">' + str(c["icone"] or "") + ' ' + str(c["nom"]) + '</a> '

    content = '<h1>🛍️ Catalogue produits — ' + str(len(produits)) + '</h1>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher produit, vendeur, code..." style="max-width:500px" autofocus>'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div style="margin-bottom:20px;display:flex;gap:6px;flex-wrap:wrap">' + cats_html + '</div>'

    content += '<div class="product-grid">' + (cards or '<p style="text-align:center;color:#94a3b8;padding:40px;grid-column:1/-1">Aucun produit trouvé</p>') + '</div>'

    return render_page(content, active='catalogue', page_title='Catalogue')


@app.route('/produit/<int:pid>')
@login_required
def produit_detail(pid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT p.*, v.raison_sociale AS vendeur_nom, v.ville AS vendeur_ville,
               v.telephone AS vendeur_tel, v.email AS vendeur_email,
               v.note_moyenne AS vendeur_note, v.nb_ventes AS vendeur_ventes,
               c.nom AS categorie_nom, c.icone AS categorie_icone
        FROM produits p
        LEFT JOIN vendeurs v ON v.id=p.vendeur_id
        LEFT JOIN categories c ON c.id=p.categorie_id
        WHERE p.id=?
    """, (pid,))
    p = cur.fetchone()
    if not p:
        flash('❌ Produit introuvable', 'error')
        return redirect('/catalogue')

    # Avis sur ce produit
    cur.execute("""
        SELECT a.*, u.nom_complet AS acheteur_nom
        FROM avis a
        LEFT JOIN users u ON u.id=a.acheteur_id
        WHERE a.produit_id=?
        ORDER BY a.id DESC LIMIT 5
    """, (pid,))
    avis = cur.fetchall()

    avis_html = ''
    for a in avis:
        stars = '⭐' * (a['note'] or 0)
        avis_html += (
            '<tr><td>' + str(a["acheteur_nom"] or "Client") + '</td>'
            + '<td><span class="rating">' + stars + '</span></td>'
            + '<td>' + str(a["commentaire"] or "") + '</td>'
            + '<td>' + str((a["date_avis"] or "—")[:10]) + '</td></tr>'
        )

    stars_vendeur = '⭐' * int(round(p['vendeur_note'] or 0))

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">' + str(p["categorie_icone"] or "📦") + ' ' + str(p["nom"]) + '</h1>'
    content += '<a href="/catalogue" class="btn btn-secondary">← Catalogue</a></div>'

    content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:18px">'

    content += '<div>'
    content += '<div class="card">'
    content += '<div style="background:linear-gradient(135deg,#2563eb,#1e40af);color:#fff;height:200px;display:flex;align-items:center;justify-content:center;font-size:80px;border-radius:8px;margin-bottom:16px">' + str(p["categorie_icone"] or "📦") + '</div>'
    content += '<h2 style="margin-top:0">Description</h2>'
    content += '<p style="color:#475569;line-height:1.7">' + str(p["description"] or "Aucune description") + '</p>'
    content += '<table style="margin-top:16px">'
    content += '<tr><td><strong>Code produit</strong></td><td>' + str(p["code"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Unité</strong></td><td>' + str(p["unite"] or "unité") + '</td></tr>'
    content += '<tr><td><strong>Stock disponible</strong></td><td>' + str(p["stock"]) + ' ' + str(p["unite"] or "") + '</td></tr>'
    content += '<tr><td><strong>Commande minimum</strong></td><td>' + str(p["prix_min_commande"]) + ' ' + str(p["unite"] or "") + '</td></tr>'
    content += '<tr><td><strong>Nombre de ventes</strong></td><td>' + str(p["nb_ventes"]) + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>⭐ Avis clients (' + str(len(avis)) + ')</h2>'
    content += '<table><thead><tr><th>Client</th><th>Note</th><th>Commentaire</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (avis_html or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucun avis</td></tr>') + '</tbody></table></div>'

    content += '</div>'

    # Colonne droite - achat
    content += '<div>'
    content += '<div class="card" style="border-left-color:#10b981">'
    content += '<div style="text-align:center;padding:16px 0">'
    content += '<div style="font-size:14px;color:#64748b;text-transform:uppercase;letter-spacing:1px;font-weight:600">Prix unitaire</div>'
    content += '<div style="font-size:38px;font-weight:900;color:#10b981;letter-spacing:-1px">' + f'{p["prix_unitaire"]:,.0f}' + '</div>'
    content += '<div style="font-size:14px;color:#64748b">FCFA / ' + str(p["unite"] or "unité") + '</div>'
    content += '<div style="margin-top:8px" class="rating">' + (stars_vendeur or "—") + ' ' + f'{p["note_moyenne"]:.1f}' + '</div>'
    content += '</div>'

    content += '<form method="post" action="/panier/ajouter/' + str(pid) + '" style="margin-top:16px">'
    content += '<label>Quantité</label>'
    content += '<input type="number" name="quantite" value="' + str(p["prix_min_commande"]) + '" min="' + str(p["prix_min_commande"]) + '" step="1" style="margin-bottom:12px;font-size:18px;text-align:center;font-weight:800">'
    content += '<button type="submit" class="btn btn-success" style="width:100%;padding:14px;font-size:15px">🛒 Ajouter au panier</button>'
    content += '</form>'
    content += '</div>'

    content += '<div class="card"><h2>🏪 Vendeur</h2>'
    content += '<div style="font-weight:800;color:#1e40af;font-size:16px;margin-bottom:6px">' + str(p["vendeur_nom"] or "—") + '</div>'
    content += '<div style="color:#64748b;font-size:13px">📍 ' + str(p["vendeur_ville"] or "—") + '</div>'
    content += '<div style="color:#64748b;font-size:13px">📞 ' + str(p["vendeur_tel"] or "—") + '</div>'
    content += '<div style="color:#64748b;font-size:13px">✉️ ' + str(p["vendeur_email"] or "—") + '</div>'
    content += '<div style="margin-top:10px;padding-top:10px;border-top:1px solid #f1f5f9">'
    content += '<div style="font-size:12px;color:#64748b">' + str(p["vendeur_ventes"]) + ' ventes · ' + (stars_vendeur or "—") + '</div>'
    content += '</div></div>'
    content += '</div>'

    content += '</div>'
    return render_page(content, active='catalogue', page_title='Produit')


# ═══════════════════════════════════════════════════════════════
# 🏪 VENDEURS
# ═══════════════════════════════════════════════════════════════

@app.route('/vendeurs')
@login_required
def vendeurs_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()

    sql = """
        SELECT v.*, (SELECT COUNT(*) FROM produits WHERE vendeur_id=v.id AND statut='actif') AS nb_produits
        FROM vendeurs v
        WHERE v.statut='actif'
    """
    params = []
    if q:
        sql += " AND (v.raison_sociale LIKE ? OR v.secteur LIKE ? OR v.ville LIKE ?)"
        params += [f'%{q}%'] * 3
    sql += " ORDER BY v.note_moyenne DESC, v.nb_ventes DESC"
    cur.execute(sql, params)
    vendeurs = cur.fetchall()

    cards = ''
    for v in vendeurs:
        stars = '⭐' * int(round(v['note_moyenne'] or 0))
        cards += '<div class="product-card">'
        cards += '<div class="product-icon" style="background:linear-gradient(135deg,#10b981,#047857)">🏪</div>'
        cards += '<div class="product-body">'
        cards += '<div class="product-title">' + str(v["raison_sociale"]) + '</div>'
        cards += '<div class="product-vendeur">' + str(v["secteur"] or "") + ' · 📍 ' + str(v["ville"] or "") + '</div>'
        cards += '<div style="font-size:11.5px;color:#64748b;margin-bottom:8px">' + str(v["description"] or "")[:60] + '...</div>'
        cards += '<div class="rating">' + (stars or "—") + ' ' + f'{v["note_moyenne"]:.1f}' + ' (' + str(v["nb_avis"]) + ' avis)</div>'
        cards += '<div style="margin-top:10px;display:flex;gap:6px">'
        cards += '<a href="/vendeur/' + str(v["id"]) + '" class="btn btn-primary" style="padding:6px 10px;font-size:11.5px;flex:1;text-align:center">👁 ' + str(v["nb_produits"]) + ' produits</a>'
        cards += '</div></div></div>'

    content = '<h1>🏪 Vendeurs B2B — ' + str(len(vendeurs)) + '</h1>'

    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher vendeur, secteur, ville..." style="max-width:500px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button></form>'

    content += '<div class="product-grid">' + (cards or '<p style="text-align:center;color:#94a3b8;padding:40px;grid-column:1/-1">Aucun vendeur</p>') + '</div>'

    return render_page(content, active='vendeurs', page_title='Vendeurs')


@app.route('/vendeur/<int:vid>')
@login_required
def vendeur_detail(vid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM vendeurs WHERE id=?", (vid,))
    v = cur.fetchone()
    if not v:
        flash('❌ Vendeur introuvable', 'error')
        return redirect('/vendeurs')

    cur.execute("""
        SELECT p.*, c.nom AS categorie_nom, c.icone AS categorie_icone
        FROM produits p
        LEFT JOIN categories c ON c.id=p.categorie_id
        WHERE p.vendeur_id=? AND p.statut='actif'
        ORDER BY p.nb_ventes DESC LIMIT 30
    """, (vid,))
    produits = cur.fetchall()

    # Avis vendeur
    cur.execute("""
        SELECT a.*, u.nom_complet AS acheteur_nom
        FROM avis a
        LEFT JOIN users u ON u.id=a.acheteur_id
        WHERE a.vendeur_id=?
        ORDER BY a.id DESC LIMIT 10
    """, (vid,))
    avis = cur.fetchall()

    avis_html = ''
    for a in avis:
        stars = '⭐' * (a['note'] or 0)
        avis_html += (
            '<tr><td>' + str(a["acheteur_nom"] or "Client") + '</td>'
            + '<td><span class="rating">' + stars + '</span></td>'
            + '<td>' + str(a["commentaire"] or "") + '</td>'
            + '<td>' + str((a["date_avis"] or "—")[:10]) + '</td></tr>'
        )

    cards = ''
    for p in produits:
        stars = '⭐' * int(round(p['note_moyenne'] or 0))
        cards += '<div class="product-card">'
        cards += '<div class="product-icon">' + str(p["categorie_icone"] or "📦") + '</div>'
        cards += '<div class="product-body">'
        cards += '<div class="product-title">' + str(p["nom"]) + '</div>'
        cards += '<div class="rating">' + (stars or "—") + '</div>'
        cards += '<div class="product-price">' + f'{p["prix_unitaire"]:,.0f}' + ' F</div>'
        cards += '<div style="margin-top:8px"><a href="/produit/' + str(p["id"]) + '" class="btn btn-primary" style="padding:6px 10px;font-size:11.5px;width:100%;text-align:center;display:block">Voir</a></div>'
        cards += '</div></div>'

    stars_v = '⭐' * int(round(v['note_moyenne'] or 0))

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🏪 ' + str(v["raison_sociale"]) + '</h1>'
    content += '<a href="/vendeurs" class="btn btn-secondary">← Vendeurs</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Note</div><div class="kpi-value" style="font-size:20px">' + (stars_v or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#2563eb,#1e40af)"><div class="kpi-label">Avis</div><div class="kpi-value">' + str(v["nb_avis"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#facc15,#eab308);color:#1e293b"><div class="kpi-label">Ventes</div><div class="kpi-value">' + str(v["nb_ventes"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-label">Produits</div><div class="kpi-value">' + str(len(produits)) + '</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:1fr 2fr;gap:18px;margin-bottom:18px">'
    content += '<div class="card"><h2>📋 Coordonnées</h2><table>'
    content += '<tr><td><strong>Secteur</strong></td><td>' + str(v["secteur"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Contact</strong></td><td>' + str(v["contact_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Téléphone</strong></td><td>' + str(v["telephone"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Email</strong></td><td>' + str(v["email"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Adresse</strong></td><td>' + str(v["adresse"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Ville</strong></td><td>' + str(v["ville"] or "—") + ', ' + str(v["pays"] or "") + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>📝 Description</h2><p style="line-height:1.7;color:#475569">' + str(v["description"] or "Aucune description") + '</p></div>'
    content += '</div>'

    content += '<div class="card"><h2>📦 Produits de ce vendeur (' + str(len(produits)) + ')</h2>'
    content += '<div class="product-grid" style="margin-top:14px">' + (cards or '<p style="color:#94a3b8">Aucun produit</p>') + '</div></div>'

    content += '<div class="card"><h2>⭐ Avis clients (' + str(len(avis)) + ')</h2>'
    content += '<table><thead><tr><th>Client</th><th>Note</th><th>Commentaire</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (avis_html or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucun avis</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='vendeurs', page_title='Vendeur')


# ═══════════════════════════════════════════════════════════════
# 🛒 PANIER
# ═══════════════════════════════════════════════════════════════

@app.route('/panier')
@login_required
def panier_view():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT p.*, pr.nom AS produit_nom, pr.unite, pr.stock,
               v.raison_sociale AS vendeur_nom, v.id AS vendeur_id
        FROM panier p
        LEFT JOIN produits pr ON pr.id=p.produit_id
        LEFT JOIN vendeurs v ON v.id=pr.vendeur_id
        WHERE p.user_id=?
        ORDER BY p.id DESC
    """, (current_user.id,))
    items = cur.fetchall()

    rows = ''
    total = 0
    vendeurs_set = set()
    for it in items:
        montant = (it['quantite'] or 0) * (it['prix_unitaire'] or 0)
        total += montant
        vendeurs_set.add(it['vendeur_id'])
        rows += (
            '<tr><td><strong>' + str(it["produit_nom"]) + '</strong></td>'
            + '<td>' + str(it["vendeur_nom"] or "—") + '</td>'
            + '<td style="text-align:right">' + f'{it["prix_unitaire"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center">' + f'{it["quantite"]:.0f}' + '</td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{montant:,.0f}' + ' F</td>'
            + '<td><a href="/panier/retirer/' + str(it["id"]) + '" class="btn btn-danger" style="padding:4px 10px;font-size:11px">✕</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🛒 Mon panier — ' + str(len(items)) + ' article(s)</h1>'
    content += '<a href="/catalogue" class="btn btn-secondary">← Continuer achats</a></div>'

    if not items:
        content += '<div class="card" style="text-align:center;padding:60px">'
        content += '<div style="font-size:80px;margin-bottom:20px">🛒</div>'
        content += '<h2>Votre panier est vide</h2>'
        content += '<p style="color:#64748b;margin:14px 0">Découvrez notre catalogue de produits B2B</p>'
        content += '<a href="/catalogue" class="btn btn-primary">Parcourir le catalogue</a></div>'
        return render_page(content, active='panier', page_title='Panier')

    content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:18px">'
    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Produit</th><th>Vendeur</th><th style="text-align:right">Prix U.</th>'
    content += '<th style="text-align:center">Qté</th><th style="text-align:right">Sous-total</th><th></th></tr></thead>'
    content += '<tbody>' + rows + '</tbody></table></div>'

    content += '<div>'
    content += '<div class="card" style="border-left-color:#10b981">'
    content += '<h2 style="margin-top:0">📊 Récapitulatif</h2>'
    content += '<table>'
    content += '<tr><td>Nombre d\'articles</td><td style="text-align:right;font-weight:800">' + str(len(items)) + '</td></tr>'
    content += '<tr><td>Vendeurs</td><td style="text-align:right;font-weight:800">' + str(len(vendeurs_set)) + '</td></tr>'
    content += '<tr><td>Total HT</td><td style="text-align:right;font-weight:800">' + f'{total:,.0f}' + ' F</td></tr>'
    content += '<tr><td>TVA 18%</td><td style="text-align:right;font-weight:800">' + f'{total*0.18:,.0f}' + ' F</td></tr>'
    content += '<tr style="background:#f0fdf4;font-weight:900;font-size:16px"><td>TOTAL TTC</td><td style="text-align:right;color:#047857">' + f'{total*1.18:,.0f}' + ' F</td></tr>'
    content += '</table>'
    content += '<div style="margin-top:20px">'
    content += '<a href="/commande/checkout" class="btn btn-success" style="width:100%;padding:16px;font-size:15px;text-align:center;display:block">✅ Passer commande</a>'
    content += '<a href="/panier/vider" class="btn btn-secondary" style="width:100%;padding:10px;margin-top:8px;text-align:center;display:block">🗑 Vider le panier</a>'
    content += '</div></div>'
    content += '</div>'
    content += '</div>'

    return render_page(content, active='panier', page_title='Panier')


@app.route('/panier/ajouter/<int:pid>', methods=['GET', 'POST'])
@login_required
def panier_ajouter(pid):
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            quantite = float(request.form.get('quantite') or 1)
        except Exception:
            quantite = 1
    else:
        try:
            quantite = float(request.args.get('quantite') or 1)
        except Exception:
            quantite = 1

    cur.execute("SELECT prix_unitaire, nom FROM produits WHERE id=?", (pid,))
    p = cur.fetchone()
    if not p:
        flash('❌ Produit introuvable', 'error')
        return redirect('/catalogue')

    # Vérifier si déjà dans le panier
    cur.execute("SELECT id, quantite FROM panier WHERE user_id=? AND produit_id=?",
                (current_user.id, pid))
    existing = cur.fetchone()
    if existing:
        cur.execute("UPDATE panier SET quantite = quantite + ? WHERE id=?",
                    (quantite, existing['id']))
    else:
        cur.execute("""
            INSERT INTO panier (user_id, produit_id, quantite, prix_unitaire, created_at)
            VALUES (?,?,?,?,?)
        """, (current_user.id, pid, quantite, p['prix_unitaire'], datetime.now().isoformat()))

    db.commit()
    flash('✅ ' + str(p['nom']) + ' ajouté au panier', 'success')
    return redirect('/panier')


@app.route('/panier/retirer/<int:item_id>')
@login_required
def panier_retirer(item_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM panier WHERE id=? AND user_id=?", (item_id, current_user.id))
    db.commit()
    flash('✅ Article retiré', 'success')
    return redirect('/panier')


@app.route('/panier/vider')
@login_required
def panier_vider():
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM panier WHERE user_id=?", (current_user.id,))
    db.commit()
    flash('✅ Panier vidé', 'success')
    return redirect('/panier')


# ═══════════════════════════════════════════════════════════════
# 📦 COMMANDES
# ═══════════════════════════════════════════════════════════════

@app.route('/commande/checkout', methods=['GET', 'POST'])
@login_required
def commande_checkout():
    db = get_db()
    cur = db.cursor()

    # Récupérer le panier
    cur.execute("""
        SELECT p.*, pr.nom AS produit_nom, pr.vendeur_id
        FROM panier p
        LEFT JOIN produits pr ON pr.id=p.produit_id
        WHERE p.user_id=?
    """, (current_user.id,))
    items = cur.fetchall()

    if not items:
        flash('⚠️ Panier vide', 'error')
        return redirect('/catalogue')

    # Grouper par vendeur → 1 commande par vendeur
    vendeurs_items = {}
    for it in items:
        vid = it['vendeur_id']
        if vid not in vendeurs_items:
            vendeurs_items[vid] = []
        vendeurs_items[vid].append(it)

    if request.method == 'POST':
        try:
            adresse = request.form.get('adresse_livraison') or ''
            ville = request.form.get('ville_livraison') or 'Dakar'
            mode_paiement = request.form.get('mode_paiement') or 'virement'

            # Créer une commande par vendeur
            for vid, lignes in vendeurs_items.items():
                montant_ht = sum((l['quantite'] or 0) * (l['prix_unitaire'] or 0) for l in lignes)
                tva = montant_ht * 0.18
                frais = 0
                total = montant_ht + tva + frais

                cur.execute("""
                    INSERT INTO commandes
                    (numero, acheteur_id, vendeur_id, date_commande, montant_ht, tva,
                     montant_ttc, frais_livraison, montant_total, mode_paiement,
                     adresse_livraison, ville_livraison, statut, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'en_attente',?)
                """, (None, current_user.id, vid,
                      datetime.now().strftime('%Y-%m-%d'),
                      montant_ht, tva, montant_ht + tva, frais, total,
                      mode_paiement, adresse, ville,
                      datetime.now().isoformat()))
                cmd_id = cur.lastrowid

                # Lignes
                for l in lignes:
                    cur.execute("""
                        INSERT INTO commande_lignes
                        (commande_id, produit_id, nom_produit, quantite, prix_unitaire, montant)
                        VALUES (?,?,?,?,?,?)
                    """, (cmd_id, l['produit_id'], l['produit_nom'],
                          l['quantite'], l['prix_unitaire'],
                          (l['quantite'] or 0) * (l['prix_unitaire'] or 0)))

                    # Décrémenter stock
                    cur.execute("UPDATE produits SET stock = stock - ? WHERE id=?",
                                (l['quantite'], l['produit_id']))

                # Créer paiement en attente
                cur.execute("""
                    INSERT INTO paiements (commande_id, montant, mode, statut, created_at)
                    VALUES (?,?,?,'en_attente',?)
                """, (cmd_id, total, mode_paiement, datetime.now().isoformat()))

            # Vider le panier
            cur.execute("DELETE FROM panier WHERE user_id=?", (current_user.id,))
            db.commit()

            log_action(current_user.id, 'CHECKOUT', f'{len(vendeurs_items)} commandes créées', 'commandes')
            flash('✅ ' + str(len(vendeurs_items)) + ' commande(s) créée(s) !', 'success')
            return redirect('/commandes')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    # Calcul total
    total = sum((it['quantite'] or 0) * (it['prix_unitaire'] or 0) for it in items)

    content = '<h1>✅ Finaliser la commande</h1>'

    content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:18px">'

    content += '<form method="post">'
    content += '<div class="card">'
    content += '<h2 style="margin-top:0">📍 Adresse de livraison</h2>'
    content += '<div style="margin-bottom:16px"><label>Adresse *</label>'
    content += '<input type="text" name="adresse_livraison" required placeholder="Zone industrielle, Rue X" autofocus></div>'
    content += '<div style="margin-bottom:16px"><label>Ville *</label>'
    content += '<input type="text" name="ville_livraison" required value="Dakar"></div>'
    content += '</div>'

    content += '<div class="card">'
    content += '<h2 style="margin-top:0">💳 Mode de paiement</h2>'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">'
    content += '<label style="padding:16px;border:2px solid #e2e8f0;border-radius:10px;text-align:center;cursor:pointer;font-weight:600">'
    content += '<input type="radio" name="mode_paiement" value="virement" checked style="width:auto;margin-right:6px"> 🏦 Virement'
    content += '</label>'
    content += '<label style="padding:16px;border:2px solid #e2e8f0;border-radius:10px;text-align:center;cursor:pointer;font-weight:600">'
    content += '<input type="radio" name="mode_paiement" value="mobile_money" style="width:auto;margin-right:6px"> 📱 Mobile Money'
    content += '</label>'
    content += '<label style="padding:16px;border:2px solid #e2e8f0;border-radius:10px;text-align:center;cursor:pointer;font-weight:600">'
    content += '<input type="radio" name="mode_paiement" value="sequestre" style="width:auto;margin-right:6px"> 🔒 Séquestre'
    content += '</label>'
    content += '<label style="padding:16px;border:2px solid #e2e8f0;border-radius:10px;text-align:center;cursor:pointer;font-weight:600">'
    content += '<input type="radio" name="mode_paiement" value="especes" style="width:auto;margin-right:6px"> 💵 Espèces'
    content += '</label>'
    content += '</div></div>'

    content += '<button type="submit" class="btn btn-success" style="width:100%;padding:16px;font-size:16px">✅ Valider la commande</button>'
    content += '</form>'

    content += '<div>'
    content += '<div class="card" style="border-left-color:#2563eb">'
    content += '<h2 style="margin-top:0">🛒 Votre commande</h2>'
    content += '<p style="font-size:12.5px;color:#64748b;margin-bottom:12px">' + str(len(items)) + ' article(s) · ' + str(len(vendeurs_items)) + ' vendeur(s)</p>'
    for vid, lignes in vendeurs_items.items():
        content += '<div style="margin-bottom:12px;padding:10px;background:#f8fafc;border-radius:8px">'
        content += '<div style="font-size:12px;color:#64748b;margin-bottom:6px">Vendeur #' + str(vid) + '</div>'
        for l in lignes:
            content += '<div style="font-size:12.5px;display:flex;justify-content:space-between;margin-bottom:4px">'
            content += '<span>' + str(l["produit_nom"])[:30] + ' × ' + f'{l["quantite"]:.0f}' + '</span>'
            content += '<span style="font-weight:700">' + f'{(l["quantite"] or 0) * (l["prix_unitaire"] or 0):,.0f}' + ' F</span>'
            content += '</div>'
        content += '</div>'
    content += '<table>'
    content += '<tr><td>Total HT</td><td style="text-align:right;font-weight:800">' + f'{total:,.0f}' + ' F</td></tr>'
    content += '<tr><td>TVA 18%</td><td style="text-align:right;font-weight:800">' + f'{total*0.18:,.0f}' + ' F</td></tr>'
    content += '<tr><td>Livraison</td><td style="text-align:right;font-weight:800">Gratuit</td></tr>'
    content += '<tr style="background:#f0fdf4;font-weight:900;font-size:16px"><td>TOTAL TTC</td><td style="text-align:right;color:#047857">' + f'{total*1.18:,.0f}' + ' F</td></tr>'
    content += '</table></div></div>'

    content += '</div>'
    return render_page(content, active='panier', page_title='Checkout')


@app.route('/commandes')
@login_required
def commandes_liste():
    db = get_db()
    cur = db.cursor()
    statut_f = request.args.get('statut', '')

    is_vendeur = current_user.role == 'vendeur'

    if is_vendeur:
        # Voir les commandes liées à mes produits
        cur.execute("SELECT id FROM vendeurs WHERE user_id=?", (current_user.id,))
        r = cur.fetchone()
        vid = r['id'] if r else 0

        sql = """
            SELECT c.*, v.raison_sociale AS vendeur_nom, u.nom_complet AS acheteur_nom
            FROM commandes c
            LEFT JOIN vendeurs v ON v.id=c.vendeur_id
            LEFT JOIN users u ON u.id=c.acheteur_id
            WHERE c.vendeur_id=?
        """
        params = [vid]
    else:
        sql = """
            SELECT c.*, v.raison_sociale AS vendeur_nom, u.nom_complet AS acheteur_nom
            FROM commandes c
            LEFT JOIN vendeurs v ON v.id=c.vendeur_id
            LEFT JOIN users u ON u.id=c.acheteur_id
            WHERE 1=1
        """
        params = []
        if current_user.role == 'acheteur':
            sql += " AND c.acheteur_id=?"
            params.append(current_user.id)

    if statut_f:
        sql += " AND c.statut=?"
        params.append(statut_f)
    sql += " ORDER BY c.id DESC LIMIT 200"
    cur.execute(sql, params)
    commandes = cur.fetchall()

    rows = ''
    for c in commandes:
        statut_badge = {
            'en_attente': 'badge-orange',
            'confirmee': 'badge-blue',
            'expediee': 'badge-yellow',
            'livree': 'badge-green',
            'annulee': 'badge-red',
        }.get(c['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong style="color:#2563eb">' + str(c["numero"]) + '</strong></td>'
            + '<td>' + str(c["acheteur_nom"] or "—") + '</td>'
            + '<td>' + str(c["vendeur_nom"] or "—") + '</td>'
            + '<td>' + str((c["date_commande"] or "—")[:10]) + '</td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{c["montant_total"]:,.0f}' + ' F</td>'
            + '<td>' + str(c["mode_paiement"] or "—") + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></td>'
            + '<td><a href="/commande/' + str(c["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    stats = {}
    base = " WHERE vendeur_id=" + str(vid) if is_vendeur else ("" if current_user.role != 'acheteur' else f" WHERE acheteur_id={current_user.id}")
    for k, s in [
        ('total', "SELECT COUNT(*) FROM commandes" + base),
        ('attente', "SELECT COUNT(*) FROM commandes" + (base + " AND " if base else " WHERE ") + "statut='en_attente'"),
        ('livrees', "SELECT COUNT(*) FROM commandes" + (base + " AND " if base else " WHERE ") + "statut='livree'"),
        ('ca', "SELECT COALESCE(SUM(montant_total),0) FROM commandes" + base),
    ]:
        try:
            cur.execute(s)
            stats[k] = cur.fetchone()[0]
        except Exception:
            stats[k] = 0

    content = '<h1>📦 Commandes — ' + str(len(commandes)) + '</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#2563eb)"><div class="kpi-icon">📦</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f97316,#ea580c)"><div class="kpi-icon">⏳</div><div class="kpi-label">En attente</div><div class="kpi-value">' + str(stats["attente"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Livrées</div><div class="kpi-value">' + str(stats["livrees"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#facc15,#eab308);color:#1e293b"><div class="kpi-icon">💰</div><div class="kpi-label">CA total</div><div class="kpi-value" style="font-size:18px">' + f'{stats["ca"]:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/commandes" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Toutes</a> '
    for s in ['en_attente', 'confirmee', 'expediee', 'livree']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/commandes?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Commande</th><th>Acheteur</th><th>Vendeur</th><th>Date</th>'
    content += '<th style="text-align:right">Montant</th><th>Paiement</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucune commande</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='commandes', page_title='Commandes')


@app.route('/commande/<int:cid>', methods=['GET', 'POST'])
@login_required
def commande_detail(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, v.raison_sociale AS vendeur_nom, v.telephone AS vendeur_tel,
               u.nom_complet AS acheteur_nom, u.telephone AS acheteur_tel
        FROM commandes c
        LEFT JOIN vendeurs v ON v.id=c.vendeur_id
        LEFT JOIN users u ON u.id=c.acheteur_id
        WHERE c.id=?
    """, (cid,))
    c = cur.fetchone()
    if not c:
        flash('❌ Commande introuvable', 'error')
        return redirect('/commandes')

    # Changer statut (si vendeur ou admin)
    if request.method == 'POST' and current_user.role in ('admin', 'vendeur'):
        try:
            new_statut = request.form.get('statut') or c['statut']
            cur.execute("UPDATE commandes SET statut=? WHERE id=?", (new_statut, cid))
            db.commit()
            log_action(current_user.id, 'CMD_STATUT', f'CMD#{cid} → {new_statut}', 'commandes', cid)
            flash('✅ Statut : ' + new_statut, 'success')
            return redirect('/commande/' + str(cid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    # Lignes
    cur.execute("SELECT * FROM commande_lignes WHERE commande_id=?", (cid,))
    lignes = cur.fetchall()

    lignes_html = ''
    for l in lignes:
        lignes_html += (
            '<tr><td><strong>' + str(l["nom_produit"]) + '</strong></td>'
            + '<td style="text-align:right">' + f'{l["prix_unitaire"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center">' + f'{l["quantite"]:.0f}' + '</td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{l["montant"]:,.0f}' + ' F</td></tr>'
        )

    # Paiements
    cur.execute("SELECT * FROM paiements WHERE commande_id=?", (cid,))
    paiements = cur.fetchall()
    pai_html = ''
    for p in paiements:
        statut_badge = {'en_attente': 'badge-orange', 'paye': 'badge-green', 'annule': 'badge-red'}.get(p['statut'], 'badge-gray')
        pai_html += (
            '<tr><td>' + str((p["date_paiement"] or "—")[:10]) + '</td>'
            + '<td style="text-align:right">' + f'{p["montant"]:,.0f}' + ' F</td>'
            + '<td>' + str(p["mode"]) + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(p["statut"]) + '</span></td></tr>'
        )

    statut_badge = {
        'en_attente': 'badge-orange',
        'confirmee': 'badge-blue',
        'expediee': 'badge-yellow',
        'livree': 'badge-green',
        'annulee': 'badge-red',
    }.get(c['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📦 ' + str(c["numero"]) + ' <span class="badge ' + statut_badge + '">' + str(c["statut"]) + '</span></h1>'
    content += '<a href="/commandes" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#2563eb)"><div class="kpi-label">Acheteur</div><div class="kpi-value" style="font-size:15px">' + str(c["acheteur_nom"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-label">Vendeur</div><div class="kpi-value" style="font-size:15px">' + str(c["vendeur_nom"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#facc15,#eab308);color:#1e293b"><div class="kpi-label">Montant TTC</div><div class="kpi-value" style="font-size:18px">' + f'{c["montant_total"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#0e7490)"><div class="kpi-label">Mode paiement</div><div class="kpi-value" style="font-size:15px">' + str(c["mode_paiement"] or "—") + '</div></div>'
    content += '</div>'

    content += '<div style="display:grid;grid-template-columns:2fr 1fr;gap:18px">'

    content += '<div>'
    content += '<div class="card"><h2>📋 Lignes de commande</h2>'
    content += '<table><thead><tr><th>Produit</th><th style="text-align:right">Prix U.</th>'
    content += '<th style="text-align:center">Qté</th><th style="text-align:right">Montant</th></tr></thead>'
    content += '<tbody>' + (lignes_html or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucune ligne</td></tr>') + '</tbody></table>'

    content += '<table style="margin-top:14px">'
    content += '<tr><td>Montant HT</td><td style="text-align:right">' + f'{c["montant_ht"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td>TVA 18%</td><td style="text-align:right">' + f'{c["tva"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td>Frais livraison</td><td style="text-align:right">' + f'{c["frais_livraison"]:,.0f}' + ' F</td></tr>'
    content += '<tr style="background:#f0fdf4;font-weight:900"><td>TOTAL TTC</td><td style="text-align:right;color:#047857">' + f'{c["montant_total"]:,.0f}' + ' F</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>💳 Paiements</h2>'
    content += '<table><thead><tr><th>Date</th><th style="text-align:right">Montant</th><th>Mode</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (pai_html or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucun paiement</td></tr>') + '</tbody></table></div>'

    content += '</div>'

    # Actions
    content += '<div>'
    content += '<div class="card"><h2>📍 Livraison</h2>'
    content += '<div style="font-weight:600;color:#475569">' + str(c["adresse_livraison"] or "—") + '</div>'
    content += '<div style="color:#64748b;font-size:13px">' + str(c["ville_livraison"] or "") + '</div>'
    content += '</div>'

    if current_user.role in ('admin', 'vendeur'):
        content += '<div class="card"><h2>✏️ Changer le statut</h2>'
        content += '<form method="post">'
        content += '<div style="margin-bottom:14px"><select name="statut" style="padding:12px">'
        for s in ['en_attente', 'confirmee', 'expediee', 'livree', 'annulee']:
            sel = ' selected' if c['statut'] == s else ''
            content += '<option value="' + s + '"' + sel + '>' + s + '</option>'
        content += '</select></div>'
        content += '<button type="submit" class="btn btn-success" style="width:100%">💾 Mettre à jour</button>'
        content += '</form></div>'

    content += '<div class="card"><h2>👤 Contact</h2>'
    content += '<div style="font-size:13px;margin-bottom:8px"><strong>Acheteur</strong><br>' + str(c["acheteur_nom"] or "—") + '<br>📞 ' + str(c["acheteur_tel"] or "—") + '</div>'
    content += '<div style="font-size:13px"><strong>Vendeur</strong><br>' + str(c["vendeur_nom"] or "—") + '<br>📞 ' + str(c["vendeur_tel"] or "—") + '</div>'
    content += '</div>'
    content += '</div>'

    content += '</div>'
    return render_page(content, active='commandes', page_title='Commande')


# ═══════════════════════════════════════════════════════════════
# 📋 DEMANDES DE DEVIS (RFQ)
# ═══════════════════════════════════════════════════════════════

@app.route('/rfq')
@login_required
def rfq_liste():
    db = get_db()
    cur = db.cursor()
    statut_f = request.args.get('statut', '')

    sql = """
        SELECT r.*, u.nom_complet AS acheteur_nom, c.nom AS categorie_nom, c.icone AS categorie_icone,
               (SELECT COUNT(*) FROM rfq_offres WHERE rfq_id=r.id) AS nb_offres
        FROM rfq r
        LEFT JOIN users u ON u.id=r.acheteur_id
        LEFT JOIN categories c ON c.id=r.categorie_id
        WHERE 1=1
    """
    params = []
    if statut_f:
        sql += " AND r.statut=?"
        params.append(statut_f)
    sql += " ORDER BY r.id DESC LIMIT 100"
    cur.execute(sql, params)
    rfqs = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM rfq")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM rfq WHERE statut='ouvert'")
    stats['ouverts'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM rfq_offres")
    stats['offres'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT rfq_id) FROM rfq_offres")
    stats['avec_offres'] = cur.fetchone()[0]

    rows = ''
    for r in rfqs:
        statut_badge = {
            'ouvert': 'badge-blue',
            'cloture': 'badge-gray',
            'attribue': 'badge-green',
        }.get(r['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong style="color:#2563eb">' + str(r["numero"] or "—") + '</strong></td>'
            + '<td><strong>' + str(r["titre"]) + '</strong><br><small style="color:#64748b">' + str(r["acheteur_nom"] or "") + '</small></td>'
            + '<td>' + str(r["categorie_icone"] or "") + ' ' + str(r["categorie_nom"] or "—") + '</td>'
            + '<td style="text-align:center">' + f'{r["quantite"]:.0f}' + ' ' + str(r["unite"] or "") + '</td>'
            + '<td style="text-align:center">' + str(r["nb_offres"]) + '</td>'
            + '<td>' + str((r["date_limite"] or "—")[:10]) + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(r["statut"]) + '</span></td>'
            + '<td><a href="/rfq/' + str(r["id"]) + '" class="btn btn-primary" style="padding:4px 10px;font-size:11px">👁</a></td></tr>'
        )

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📋 Demandes de devis (RFQ) — ' + str(len(rfqs)) + '</h1>'
    content += '<a href="/rfq/nouvelle" class="btn btn-primary">+ Nouvelle RFQ</a></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#2563eb)"><div class="kpi-icon">📋</div><div class="kpi-label">Total RFQ</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🟢</div><div class="kpi-label">Ouvertes</div><div class="kpi-value">' + str(stats["ouverts"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#facc15,#eab308);color:#1e293b"><div class="kpi-icon">💬</div><div class="kpi-label">Offres reçues</div><div class="kpi-value">' + str(stats["offres"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">✅</div><div class="kpi-label">Avec offres</div><div class="kpi-value">' + str(stats["avec_offres"]) + '</div></div>'
    content += '</div>'

    content += '<div style="margin-bottom:16px">'
    content += '<a href="/rfq" class="btn ' + ('btn-primary' if not statut_f else 'btn-secondary') + '">Toutes</a> '
    for s in ['ouvert', 'cloture', 'attribue']:
        active_cls = 'btn-primary' if statut_f == s else 'btn-secondary'
        content += '<a href="/rfq?statut=' + s + '" class="btn ' + active_cls + '" style="margin-left:6px">' + s + '</a> '
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° RFQ</th><th>Titre</th><th>Catégorie</th><th style="text-align:center">Quantité</th>'
    content += '<th style="text-align:center">Offres</th><th>Date limite</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucune RFQ</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='rfq', page_title='RFQ')


@app.route('/rfq/nouvelle', methods=['GET', 'POST'])
@login_required
def rfq_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            cur.execute("""
                INSERT INTO rfq
                (numero, acheteur_id, categorie_id, titre, description,
                 quantite, unite, date_limite, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?, 'ouvert', ?)
            """, (None, current_user.id,
                  int(request.form.get('categorie_id') or 0) or None,
                  request.form.get('titre'),
                  request.form.get('description'),
                  float(request.form.get('quantite') or 0),
                  request.form.get('unite') or 'unité',
                  request.form.get('date_limite'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ RFQ créée', 'success')
            return redirect('/rfq')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom, icone FROM categories ORDER BY ordre")
    cats = cur.fetchall()
    opts_c = ''.join('<option value="' + str(c["id"]) + '">' + str(c["icone"] or "") + ' ' + str(c["nom"]) + '</option>' for c in cats)

    content = '<h1>📋 Nouvelle demande de devis</h1>'
    content += '<form method="post" class="card" style="max-width:800px">'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
    content += '<div style="grid-column:1/-1"><label>Titre de la demande *</label>'
    content += '<input type="text" name="titre" required placeholder="Recherche fournisseur ciment 500 sacs" autofocus></div>'
    content += '<div><label>Catégorie</label><select name="categorie_id"><option value="">— Aucune —</option>' + opts_c + '</select></div>'
    content += '<div><label>Date limite</label>'
    content += '<input type="date" name="date_limite" value="' + (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d') + '"></div>'
    content += '<div><label>Quantité</label><input type="number" step="0.1" name="quantite" value="100"></div>'
    content += '<div><label>Unité</label><input type="text" name="unite" value="unité"></div>'
    content += '<div style="grid-column:1/-1"><label>Description détaillée</label>'
    content += '<textarea name="description" rows="4" placeholder="Détails, spécifications, conditions..."></textarea></div>'
    content += '</div>'
    content += '<div style="margin-top:24px"><button type="submit" class="btn btn-success">💾 Publier la RFQ</button>'
    content += '<a href="/rfq" class="btn btn-secondary" style="margin-left:8px">Annuler</a></div>'
    content += '</form>'
    return render_page(content, active='rfq', page_title='Nouvelle RFQ')


@app.route('/rfq/<int:rid>', methods=['GET', 'POST'])
@login_required
def rfq_detail(rid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT r.*, u.nom_complet AS acheteur_nom, c.nom AS categorie_nom, c.icone AS categorie_icone
        FROM rfq r
        LEFT JOIN users u ON u.id=r.acheteur_id
        LEFT JOIN categories c ON c.id=r.categorie_id
        WHERE r.id=?
    """, (rid,))
    r = cur.fetchone()
    if not r:
        flash('❌ RFQ introuvable', 'error')
        return redirect('/rfq')

    # Ajouter une offre (si vendeur)
    if request.method == 'POST' and current_user.role in ('vendeur', 'admin'):
        try:
            cur.execute("SELECT id FROM vendeurs WHERE user_id=?", (current_user.id,))
            v = cur.fetchone()
            vid = v['id'] if v else int(request.form.get('vendeur_id') or 0)

            prix_u = float(request.form.get('prix_unitaire') or 0)
            delai = int(request.form.get('delai_jours') or 7)
            montant_total = prix_u * (r['quantite'] or 0)

            cur.execute("""
                INSERT INTO rfq_offres
                (rfq_id, vendeur_id, prix_unitaire, montant_total, delai_jours, message, statut, created_at)
                VALUES (?,?,?,?,?,?, 'soumise', ?)
            """, (rid, vid, prix_u, montant_total, delai,
                  request.form.get('message'), datetime.now().isoformat()))
            db.commit()
            flash('✅ Offre soumise', 'success')
            return redirect('/rfq/' + str(rid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    # Offres
    cur.execute("""
        SELECT o.*, v.raison_sociale AS vendeur_nom, v.ville AS vendeur_ville,
               v.note_moyenne AS vendeur_note, v.telephone AS vendeur_tel
        FROM rfq_offres o
        LEFT JOIN vendeurs v ON v.id=o.vendeur_id
        WHERE o.rfq_id=?
        ORDER BY o.prix_unitaire ASC
    """, (rid,))
    offres = cur.fetchall()

    offres_html = ''
    for o in offres:
        statut_badge = {
            'soumise': 'badge-blue',
            'retenue': 'badge-green',
            'refusee': 'badge-red',
        }.get(o['statut'], 'badge-gray')
        stars = '⭐' * int(round(o['vendeur_note'] or 0))
        offres_html += (
            '<tr><td><strong>' + str(o["vendeur_nom"] or "—") + '</strong><br><small style="color:#64748b">📍 ' + str(o["vendeur_ville"] or "") + '</small></td>'
            + '<td><span class="rating">' + (stars or "—") + '</span> ' + f'{o["vendeur_note"] or 0:.1f}' + '</td>'
            + '<td style="text-align:right">' + f'{o["prix_unitaire"]:,.0f}' + ' F</td>'
            + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{o["montant_total"]:,.0f}' + ' F</td>'
            + '<td style="text-align:center">' + str(o["delai_jours"]) + ' j</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(o["statut"]) + '</span></td></tr>'
        )

    statut_badge = {'ouvert': 'badge-blue', 'cloture': 'badge-gray', 'attribue': 'badge-green'}.get(r['statut'], 'badge-gray')

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">📋 ' + str(r["numero"]) + ' <span class="badge ' + statut_badge + '">' + str(r["statut"]) + '</span></h1>'
    content += '<a href="/rfq" class="btn btn-secondary">← Retour</a></div>'

    content += '<div class="card">'
    content += '<h2>' + str(r["categorie_icone"] or "📋") + ' ' + str(r["titre"]) + '</h2>'
    content += '<table style="margin-top:14px">'
    content += '<tr><td><strong>Acheteur</strong></td><td>' + str(r["acheteur_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Catégorie</strong></td><td>' + str(r["categorie_nom"] or "—") + '</td></tr>'
    content += '<tr><td><strong>Quantité</strong></td><td>' + f'{r["quantite"]:.0f}' + ' ' + str(r["unite"] or "") + '</td></tr>'
    content += '<tr><td><strong>Date limite</strong></td><td>' + str((r["date_limite"] or "—")[:10]) + '</td></tr>'
    content += '<tr><td><strong>Description</strong></td><td>' + str(r["description"] or "—") + '</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h2>💬 Offres reçues (' + str(len(offres)) + ')</h2>'
    content += '<table><thead><tr><th>Vendeur</th><th>Note</th><th style="text-align:right">Prix U.</th>'
    content += '<th style="text-align:right">Total</th><th style="text-align:center">Délai</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (offres_html or '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:20px">Aucune offre pour l\'instant</td></tr>') + '</tbody></table></div>'

    # Formulaire d'offre pour les vendeurs
    if current_user.role in ('vendeur', 'admin') and r['statut'] == 'ouvert':
        content += '<div class="card"><h2>✏️ Soumettre votre offre</h2>'
        content += '<form method="post">'
        content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
        content += '<div><label>Prix unitaire (FCFA) *</label>'
        content += '<input type="number" step="100" name="prix_unitaire" required autofocus></div>'
        content += '<div><label>Délai (jours) *</label>'
        content += '<input type="number" name="delai_jours" required value="7"></div>'
        content += '<div style="grid-column:1/-1"><label>Message / conditions</label>'
        content += '<textarea name="message" rows="3" placeholder="Conditions, garanties, modalités..."></textarea></div>'
        content += '</div>'
        content += '<div style="margin-top:16px"><button type="submit" class="btn btn-success">📤 Soumettre l\'offre</button></div>'
        content += '</form></div>'

    return render_page(content, active='rfq', page_title='RFQ')


# ═══════════════════════════════════════════════════════════════
# 🚚 LIVRAISONS
# ═══════════════════════════════════════════════════════════════

@app.route('/livraisons')
@login_required
def livraisons_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT l.*, c.numero AS commande_numero, v.raison_sociale AS vendeur_nom,
               u.nom_complet AS acheteur_nom
        FROM livraisons l
        LEFT JOIN commandes c ON c.id=l.commande_id
        LEFT JOIN vendeurs v ON v.id=c.vendeur_id
        LEFT JOIN users u ON u.id=c.acheteur_id
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
        statut_badge = {
            'prepare': 'badge-gray',
            'expedie': 'badge-yellow',
            'livre': 'badge-green',
            'retour': 'badge-red',
        }.get(l['statut'], 'badge-gray')
        rows += (
            '<tr><td><strong style="color:#2563eb">' + str(l["numero_suivi"] or "—") + '</strong></td>'
            + '<td>' + str(l["commande_numero"] or "—") + '</td>'
            + '<td>' + str(l["vendeur_nom"] or "—") + '</td>'
            + '<td>' + str(l["acheteur_nom"] or "—") + '</td>'
            + '<td>' + str(l["transporteur"] or "—") + '</td>'
            + '<td>' + str((l["date_expedition"] or "—")[:10]) + '</td>'
            + '<td>' + str((l["date_livraison_prevue"] or "—")[:10]) + '</td>'
            + '<td><span class="badge ' + statut_badge + '">' + str(l["statut"]) + '</span></td></tr>'
        )

    content = '<h1>🚚 Livraisons — ' + str(len(livraisons)) + '</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#2563eb)"><div class="kpi-icon">🚚</div><div class="kpi-label">Total</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#64748b,#475569)"><div class="kpi-icon">📦</div><div class="kpi-label">Préparées</div><div class="kpi-value">' + str(stats["prep"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#facc15,#eab308);color:#1e293b"><div class="kpi-icon">🚛</div><div class="kpi-label">Expédiées</div><div class="kpi-value">' + str(stats["exp"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">✅</div><div class="kpi-label">Livrées</div><div class="kpi-value">' + str(stats["liv"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Suivi</th><th>Commande</th><th>Vendeur</th><th>Acheteur</th>'
    content += '<th>Transporteur</th><th>Expédition</th><th>Livraison prévue</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="8" style="padding:40px;text-align:center;color:#94a3b8">Aucune livraison</td></tr>') + '</tbody></table></div>'

    content += '<div style="margin-top:16px;text-align:right"><a href="/livraisons/nouvelle" class="btn btn-primary">+ Nouvelle livraison</a></div>'

    return render_page(content, active='livraisons', page_title='Livraisons')


@app.route('/livraisons/nouvelle', methods=['GET', 'POST'])
@login_required
def livraisons_nouvelle():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            commande_id = int(request.form.get('commande_id') or 0)

            cur.execute("SELECT COALESCE(MAX(id),0)+1 FROM livraisons")
            nid = cur.fetchone()[0]
            numero = 'LIV-' + datetime.now().strftime('%Y%m%d') + '-' + f'{nid:04d}'

            cur.execute("""
                INSERT INTO livraisons
                (commande_id, numero_suivi, transporteur, date_expedition,
                 date_livraison_prevue, statut, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (commande_id, numero,
                  request.form.get('transporteur'),
                  request.form.get('date_expedition') or datetime.now().strftime('%Y-%m-%d'),
                  request.form.get('date_livraison_prevue'),
                  request.form.get('statut') or 'prepare',
                  request.form.get('notes'),
                  datetime.now().isoformat()))
            db.commit()
            flash('✅ Livraison créée — N° ' + numero, 'success')
            return redirect('/livraisons')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("""
        SELECT c.id, c.numero, v.raison_sociale AS vendeur_nom
        FROM commandes c
        LEFT JOIN vendeurs v ON v.id=c.vendeur_id
        WHERE c.statut IN ('confirmee', 'expediee', 'en_attente')
        ORDER BY c.id DESC LIMIT 100
    """)
    commandes = cur.fetchall()
    opts_cmd = ''.join('<option value="' + str(c["id"]) + '">' + str(c["numero"]) + ' — ' + str(c["vendeur_nom"] or "") + '</option>' for c in commandes)

    content = '<h1>🚚 Nouvelle livraison</h1>'
    content += '<form method="post" class="card" style="max-width:700px">'
    content += '<div style="margin-bottom:16px"><label>Commande *</label><select name="commande_id" required>'
    content += '<option value="">— Sélectionner —</option>' + opts_cmd + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Transporteur</label>'
    content += '<input type="text" name="transporteur" placeholder="DHL, SENEX, Transrail..." autofocus></div>'
    content += '<div style="margin-bottom:16px"><label>Date expédition</label>'
    content += '<input type="date" name="date_expedition" value="' + datetime.now().strftime('%Y-%m-%d') + '"></div>'
    content += '<div style="margin-bottom:16px"><label>Date livraison prévue</label>'
    content += '<input type="date" name="date_livraison_prevue" value="' + (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d') + '"></div>'
    content += '<div style="margin-bottom:16px"><label>Statut</label><select name="statut">'
    content += '<option value="prepare">📦 Préparée</option>'
    content += '<option value="expedie">🚛 Expédiée</option>'
    content += '<option value="livre">✅ Livrée</option>'
    content += '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Notes</label>'
    content += '<textarea name="notes" rows="3"></textarea></div>'
    content += '<button type="submit" class="btn btn-success">💾 Créer</button>'
    content += '<a href="/livraisons" class="btn btn-secondary" style="margin-left:8px">Annuler</a>'
    content += '</form>'
    return render_page(content, active='livraisons', page_title='Nouvelle livraison')


# ═══════════════════════════════════════════════════════════════
# ⭐ AVIS
# ═══════════════════════════════════════════════════════════════

@app.route('/avis')
@login_required
def avis_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT a.*, v.raison_sociale AS vendeur_nom, p.nom AS produit_nom,
               u.nom_complet AS acheteur_nom
        FROM avis a
        LEFT JOIN vendeurs v ON v.id=a.vendeur_id
        LEFT JOIN produits p ON p.id=a.produit_id
        LEFT JOIN users u ON u.id=a.acheteur_id
        ORDER BY a.id DESC LIMIT 200
    """)
    avis = cur.fetchall()

    stats = {}
    cur.execute("SELECT COUNT(*) FROM avis")
    stats['total'] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(AVG(note),0) FROM avis")
    stats['moyenne'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM avis WHERE note >= 4")
    stats['positifs'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM avis WHERE note <= 2")
    stats['negatifs'] = cur.fetchone()[0]

    rows = ''
    for a in avis:
        stars = '⭐' * (a['note'] or 0)
        rows += (
            '<tr><td><strong>' + str(a["vendeur_nom"] or "—") + '</strong></td>'
            + '<td>' + str(a["produit_nom"] or "—") + '</td>'
            + '<td>' + str(a["acheteur_nom"] or "Client") + '</td>'
            + '<td><span class="rating">' + stars + '</span></td>'
            + '<td>' + str(a["commentaire"] or "") + '</td>'
            + '<td>' + str((a["date_avis"] or "—")[:10]) + '</td></tr>'
        )

    content = '<h1>⭐ Avis & Évaluations — ' + str(len(avis)) + '</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#2563eb)"><div class="kpi-icon">⭐</div><div class="kpi-label">Total avis</div><div class="kpi-value">' + str(stats["total"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#facc15,#eab308);color:#1e293b"><div class="kpi-icon">📊</div><div class="kpi-label">Note moyenne</div><div class="kpi-value">' + f'{stats["moyenne"]:.1f}' + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">👍</div><div class="kpi-label">Positifs (4-5★)</div><div class="kpi-value">' + str(stats["positifs"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div class="kpi-icon">👎</div><div class="kpi-label">Négatifs (1-2★)</div><div class="kpi-value">' + str(stats["negatifs"]) + '</div></div>'
    content += '</div>'

    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Vendeur</th><th>Produit</th><th>Client</th><th>Note</th><th>Commentaire</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="6" style="padding:40px;text-align:center;color:#94a3b8">Aucun avis</td></tr>') + '</tbody></table></div>'

    return render_page(content, active='avis', page_title='Avis')


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

    ca_total = sc("SELECT COALESCE(SUM(montant_total),0) FROM commandes")
    nb_cmd = sc("SELECT COUNT(*) FROM commandes")
    panier_moyen = (ca_total / nb_cmd) if nb_cmd > 0 else 0
    ca_mois = sc("SELECT COALESCE(SUM(montant_total),0) FROM commandes WHERE strftime('%Y-%m',date_commande)=strftime('%Y-%m','now')")

    # Top 10 produits
    cur.execute("""
        SELECT p.nom, p.prix_unitaire, COUNT(cl.id) AS nb_commandes,
               COALESCE(SUM(cl.quantite),0) AS qte_vendue,
               COALESCE(SUM(cl.montant),0) AS ca
        FROM produits p
        LEFT JOIN commande_lignes cl ON cl.produit_id=p.id
        GROUP BY p.id
        ORDER BY ca DESC
        LIMIT 10
    """)
    top_produits = cur.fetchall()
    prod_html = ''.join(
        '<tr><td>' + str(p["nom"]) + '</td>'
        + '<td style="text-align:right">' + f'{p["prix_unitaire"]:,.0f}' + ' F</td>'
        + '<td style="text-align:center">' + str(p["nb_commandes"]) + '</td>'
        + '<td style="text-align:right">' + f'{p["qte_vendue"]:.0f}' + '</td>'
        + '<td style="text-align:right;color:#10b981;font-weight:800">' + f'{p["ca"]:,.0f}' + ' F</td></tr>'
        for p in top_produits
    )

    # Top 10 vendeurs
    cur.execute("""
        SELECT v.raison_sociale, v.note_moyenne, v.nb_ventes,
               COALESCE(SUM(c.montant_total),0) AS ca
        FROM vendeurs v
        LEFT JOIN commandes c ON c.vendeur_id=v.id
        GROUP BY v.id
        ORDER BY ca DESC
        LIMIT 10
    """)
    top_vendeurs = cur.fetchall()
    vnd_html = ''.join(
        '<tr><td>' + str(v["raison_sociale"]) + '</td>'
        + '<td style="text-align:center">⭐ ' + f'{v["note_moyenne"]:.1f}' + '</td>'
        + '<td style="text-align:center">' + str(v["nb_ventes"]) + '</td>'
        + '<td style="text-align:right;color:#10b981;font-weight:800">' + f'{v["ca"]:,.0f}' + ' F</td></tr>'
        for v in top_vendeurs
    )

    # CA par catégorie
    cur.execute("""
        SELECT c.nom, c.icone, COALESCE(SUM(cl.montant),0) AS ca
        FROM categories c
        LEFT JOIN produits p ON p.categorie_id=c.id
        LEFT JOIN commande_lignes cl ON cl.produit_id=p.id
        GROUP BY c.id
        ORDER BY ca DESC
    """)
    cat_ca = cur.fetchall()
    cat_html = ''.join(
        '<tr><td>' + str(c["icone"] or "") + ' ' + str(c["nom"]) + '</td>'
        + '<td style="text-align:right;font-weight:800;color:#10b981">' + f'{c["ca"]:,.0f}' + ' F</td></tr>'
        for c in cat_ca
    )

    content = '<h1>📈 Analytics Marketplace</h1>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#1e40af,#2563eb)"><div class="kpi-icon">💰</div><div class="kpi-label">Volume total</div><div class="kpi-value" style="font-size:18px">' + f'{ca_total:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div class="kpi-icon">🛒</div><div class="kpi-label">Commandes</div><div class="kpi-value">' + str(nb_cmd) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#facc15,#eab308);color:#1e293b"><div class="kpi-icon">📊</div><div class="kpi-label">Panier moyen</div><div class="kpi-value" style="font-size:18px">' + f'{panier_moyen:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div class="kpi-icon">📅</div><div class="kpi-label">CA du mois</div><div class="kpi-value" style="font-size:18px">' + f'{ca_mois:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card"><h2>🏆 Top 10 produits</h2>'
    content += '<table><thead><tr><th>Produit</th><th style="text-align:right">Prix U.</th>'
    content += '<th style="text-align:center">Commandes</th><th style="text-align:right">Qté vendue</th>'
    content += '<th style="text-align:right">CA</th></tr></thead>'
    content += '<tbody>' + (prod_html or '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'

    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h2>🏪 Top vendeurs</h2>'
    content += '<table><thead><tr><th>Vendeur</th><th style="text-align:center">Note</th>'
    content += '<th style="text-align:center">Ventes</th><th style="text-align:right">CA</th></tr></thead>'
    content += '<tbody>' + (vnd_html or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h2>🏷️ CA par catégorie</h2>'
    content += '<table><thead><tr><th>Catégorie</th><th style="text-align:right">CA</th></tr></thead>'
    content += '<tbody>' + (cat_html or '<tr><td colspan="2" style="text-align:center;color:#94a3b8;padding:20px">Aucune donnée</td></tr>') + '</tbody></table></div>'
    content += '</div>'

    content += '<div class="card" style="border-left-color:#10b981"><h2>🎯 Objectifs OMEGA Marketplace</h2>'
    content += '<ul style="line-height:2;color:#334155;font-size:14px">'
    content += '<li>🌍 <strong>10 000 PME CEDEAO</strong> connectées</li>'
    content += '<li>🏪 <strong>500 vendeurs</strong> vérifiés</li>'
    content += '<li>📦 <strong>5 000 produits</strong> référencés</li>'
    content += '<li>💳 <strong>Paiement sécurisé</strong> (mobile money + séquestre)</li>'
    content += '<li>⭐ <strong>Avis transparents</strong> pour la confiance B2B</li>'
    content += '</ul></div>'

    return render_page(content, active='analytics', page_title='Analytics')


# ═══════════════════════════════════════════════════════════════
# 📊 API JSON
# ═══════════════════════════════════════════════════════════════

@app.route('/api/marketplace/stats')
@login_required
def api_marketplace_stats():
    db = get_db()
    cur = db.cursor()
    result = {}
    for k, sql in [
        ('vendeurs', "SELECT COUNT(*) FROM vendeurs WHERE statut='actif'"),
        ('produits', "SELECT COUNT(*) FROM produits WHERE statut='actif'"),
        ('commandes', "SELECT COUNT(*) FROM commandes"),
        ('ca_total', "SELECT COALESCE(SUM(montant_total),0) FROM commandes"),
        ('rfq_ouverts', "SELECT COUNT(*) FROM rfq WHERE statut='ouvert'"),
        ('avis_total', "SELECT COUNT(*) FROM avis"),
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


# ═══════════════════════════════════════════════════════════════
# 🛒 AMÉLIORATIONS — Commandes & Avis
# ═══════════════════════════════════════════════════════════════

@app.route('/commande/<int:cid>/annuler')
@login_required
def commande_annuler(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM commandes WHERE id=?", (cid,))
    c = cur.fetchone()
    if not c:
        flash('❌ Commande introuvable', 'error')
        return redirect('/commandes')

    if current_user.role not in ('admin', 'vendeur') and c['acheteur_id'] != current_user.id:
        flash('❌ Non autorisé', 'error')
        return redirect('/commandes')

    try:
        cur.execute("UPDATE commandes SET statut='annulee' WHERE id=?", (cid,))
        db.commit()
        flash('✅ Commande annulée', 'success')
    except Exception as e:
        db.rollback()
        flash('❌ ' + str(e), 'error')
    return redirect('/commande/' + str(cid))


@app.route('/commande/<int:cid>/livrer')
@login_required
def commande_livrer(cid):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("UPDATE commandes SET statut='livree' WHERE id=?", (cid,))
        db.commit()
        flash('✅ Commande marquée livrée', 'success')
    except Exception as e:
        db.rollback()
        flash('❌ ' + str(e), 'error')
    return redirect('/commande/' + str(cid))


@app.route('/commande/<int:cid>/avis', methods=['GET', 'POST'])
@login_required
def commande_avis(cid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, v.raison_sociale AS vendeur_nom
        FROM commandes c
        LEFT JOIN vendeurs v ON v.id=c.vendeur_id
        WHERE c.id=?
    """, (cid,))
    c = cur.fetchone()
    if not c:
        flash('❌ Commande introuvable', 'error')
        return redirect('/commandes')

    if request.method == 'POST':
        try:
            note = int(request.form.get('note') or 5)
            commentaire = request.form.get('commentaire') or ''

            cur.execute("""
                INSERT INTO avis (vendeur_id, acheteur_id, commande_id, note, commentaire, date_avis, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (c['vendeur_id'], current_user.id, cid, note, commentaire,
                  datetime.now().strftime('%Y-%m-%d'), datetime.now().isoformat()))
            db.commit()
            flash('✅ Merci pour votre avis !', 'success')
            return redirect('/commande/' + str(cid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>⭐ Laisser un avis</h1>'
    content += '<div class="card" style="max-width:600px">'
    content += '<h2>Commande ' + str(c['numero']) + '</h2>'
    content += '<p style="color:#64748b;margin-bottom:20px">Vendeur : <strong>' + str(c['vendeur_nom'] or '—') + '</strong></p>'
    content += '<form method="post">'
    content += '<div style="margin-bottom:16px"><label>Note globale</label>'
    content += '<select name="note" required>'
    content += '<option value="5">⭐⭐⭐⭐⭐ Excellent</option>'
    content += '<option value="4">⭐⭐⭐⭐ Très bien</option>'
    content += '<option value="3">⭐⭐⭐ Bien</option>'
    content += '<option value="2">⭐⭐ Moyen</option>'
    content += '<option value="1">⭐ Mauvais</option>'
    content += '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Commentaire</label>'
    content += '<textarea name="commentaire" rows="4" placeholder="Décrivez votre expérience..."></textarea></div>'
    content += '<button type="submit" class="btn btn-success">📤 Publier l\'avis</button>'
    content += '<a href="/commande/' + str(cid) + '" class="btn btn-secondary" style="margin-left:8px">Annuler</a>'
    content += '</form></div>'
    return render_page(content, active='commandes', page_title='Avis')


@app.route('/vendeur/<int:vid>/avis', methods=['GET', 'POST'])
@login_required
def vendeur_avis(vid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM vendeurs WHERE id=?", (vid,))
    v = cur.fetchone()
    if not v:
        flash('❌ Vendeur introuvable', 'error')
        return redirect('/vendeurs')

    if request.method == 'POST':
        try:
            note = int(request.form.get('note') or 5)
            commentaire = request.form.get('commentaire') or ''
            cur.execute("""
                INSERT INTO avis (vendeur_id, acheteur_id, note, commentaire, date_avis, created_at)
                VALUES (?,?,?,?,?,?)
            """, (vid, current_user.id, note, commentaire,
                  datetime.now().strftime('%Y-%m-%d'), datetime.now().isoformat()))
            db.commit()
            flash('✅ Avis publié', 'success')
            return redirect('/vendeur/' + str(vid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>⭐ Avis sur ' + str(v['raison_sociale']) + '</h1>'
    content += '<form method="post" class="card" style="max-width:600px">'
    content += '<div style="margin-bottom:16px"><label>Note</label><select name="note" required>'
    content += '<option value="5">⭐⭐⭐⭐⭐</option>'
    content += '<option value="4">⭐⭐⭐⭐</option>'
    content += '<option value="3">⭐⭐⭐</option>'
    content += '<option value="2">⭐⭐</option>'
    content += '<option value="1">⭐</option>'
    content += '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Commentaire</label>'
    content += '<textarea name="commentaire" rows="4" required></textarea></div>'
    content += '<button type="submit" class="btn btn-success">📤 Publier</button>'
    content += '<a href="/vendeur/' + str(vid) + '" class="btn btn-secondary" style="margin-left:8px">Annuler</a>'
    content += '</form>'
    return render_page(content, active='vendeurs', page_title='Avis')


# Alias pour supporter /ajouter/<pid> directement
@app.route('/ajouter/<int:pid>', methods=['GET', 'POST'])
@login_required
def ajouter_alias(pid):
    return panier_ajouter(pid)
