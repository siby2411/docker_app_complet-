"""
💊 Pharmacie Pro — Application principale
Officines · Stock · Ordonnances · POS · Anti-contrefaçon
"""
from flask import Flask, render_template_string, redirect, url_for, session, request, jsonify, Response, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
import sqlite3
import os
import io
import csv

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'omega-pharmacie-pro-secret-2026')

DB_PATH = '/app/data/pharmacie.db'

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


LAYOUT = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Pharmacie Pro</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}}
body{{background:#f3f4f6;color:#1f2937}}
.nav{{background:linear-gradient(135deg,#0891b2,#06b6d4);color:#fff;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 8px rgba(0,0,0,.1);flex-wrap:wrap;gap:10px}}
.nav-brand{{font-weight:800;font-size:17px;display:flex;align-items:center;gap:10px}}
.nav-links{{display:flex;gap:4px;flex-wrap:wrap}}
.nav-links a{{color:#fff;text-decoration:none;padding:7px 12px;border-radius:8px;font-size:12.5px;font-weight:600;transition:.2s}}
.nav-links a:hover{{background:rgba(255,255,255,.15)}}
.nav-links a.active{{background:rgba(255,255,255,.25)}}
.nav-user{{font-size:12.5px;display:flex;gap:10px;align-items:center}}
.nav-user a{{color:#fff;text-decoration:none;background:rgba(0,0,0,.2);padding:6px 12px;border-radius:6px}}
.container{{max-width:1500px;margin:0 auto;padding:20px}}
h1{{color:#0e7490;margin-bottom:18px;font-size:24px}}
.card{{background:#fff;padding:22px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:18px}}
table{{width:100%;border-collapse:collapse}}
thead{{background:#0e7490;color:#fff}}
th{{padding:11px;text-align:left;font-size:12.5px;font-weight:700}}
td{{padding:10px;border-bottom:1px solid #f3f4f6;font-size:13.5px}}
.btn{{display:inline-block;padding:9px 16px;border-radius:8px;text-decoration:none;font-weight:600;font-size:13.5px;border:none;cursor:pointer}}
.btn-primary{{background:#06b6d4;color:#fff}}
.btn-success{{background:#10b981;color:#fff}}
.btn-danger{{background:#ef4444;color:#fff}}
input,select,textarea{{width:100%;padding:10px 13px;border:2px solid #e5e7eb;border-radius:8px;font-size:13.5px;font-family:inherit}}
input:focus,select:focus,textarea:focus{{outline:none;border-color:#06b6d4}}
label{{display:block;font-weight:600;margin-bottom:6px;font-size:12.5px;color:#374151}}
.kpi{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:18px}}
.kpi-card{{padding:16px;border-radius:10px;color:#fff}}
.flash{{padding:12px 18px;border-radius:8px;margin-bottom:14px;font-size:13.5px}}
.flash-success{{background:#d1fae5;color:#065f46}}
.flash-error{{background:#fee2e2;color:#991b1b}}
.pos-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;max-height:calc(100vh - 380px);overflow-y:auto;padding:8px;background:#fff;border-radius:12px}}
.pos-product{{background:#f9fafb;border:2px solid #e5e7eb;border-radius:10px;padding:12px;cursor:pointer;transition:0.15s}}
.pos-product:hover{{border-color:#06b6d4;transform:translateY(-2px);box-shadow:0 4px 12px rgba(6,182,212,0.15)}}
.pos-product:active{{transform:scale(0.97)}}
.pos-cart{{background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.cart-line{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f3f4f6}}
.cart-line button{{background:#ef4444;color:#fff;border:none;border-radius:6px;padding:4px 8px;cursor:pointer;font-size:12px}}
.pos-search{{width:100%;padding:14px;border:3px solid #06b6d4;border-radius:10px;font-size:16px;margin-bottom:12px}}
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-brand">💊 PHARMACIE PRO</div>
  <div class="nav-links">
    <a href="/" class="{a_dash}">🏠 Dashboard</a>
    <a href="/recherche" class="{a_rech}">🔍 Recherche</a>
    <a href="/medicaments" class="{a_med}">💊 Médicaments</a>
    <a href="/stock" class="{a_stock}">📦 Stock</a>
    <a href="/ordonnances" class="{a_ord}">📋 Ordonnances</a>
    <a href="/pos" class="{a_pos}">🛒 POS</a>
    <a href="/caisse/sessions" class="{a_caisse}">🖥️ Caisse</a>
    <a href="/finances" class="{a_fin}">💰 Finances</a>
    <a href="/codes" class="{a_codes}">🎫 Codes</a>
    <a href="/alertes" class="{a_al}">🚨 Alertes</a>
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


def render_page(content, active='dashboard', page_title='Pharmacie Pro'):
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
        a_rech='active' if active == 'recherche' else '',
        a_med='active' if active == 'medicaments' else '',
        a_stock='active' if active == 'stock' else '',
        a_ord='active' if active == 'ordonnances' else '',
        a_pos='active' if active == 'pos' else '',
        a_caisse='active' if active == 'caisse' else '',
        a_fin='active' if active == 'finances' else '',
        a_codes='active' if active == 'codes' else '',
        a_al='active' if active == 'alertes' else '',
        a_rap='active' if active == 'rapports' else '',
    )


@app.route('/health')
def health():
    return {'project': 'PHARMACIE PRO', 'service': 'pharmacie',
            'status': 'ok', 'timestamp': datetime.now().isoformat(), 'version': '1.0'}


LOGIN_HTML = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Connexion — Pharmacie Pro</title>
<style>body{{font-family:system-ui;background:linear-gradient(135deg,#0891b2,#06b6d4);min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0}}
.box{{background:#fff;padding:40px;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.3);width:100%;max-width:400px}}
h1{{color:#0e7490;margin:0 0 24px;text-align:center}}
input{{width:100%;padding:14px;border:2px solid #e5e7eb;border-radius:10px;margin-bottom:14px;font-size:15px;box-sizing:border-box}}
input:focus{{outline:none;border-color:#06b6d4}}
button{{width:100%;background:#06b6d4;color:#fff;padding:14px;border:none;border-radius:10px;font-weight:700;font-size:15px;cursor:pointer}}
.err{{background:#fee2e2;color:#991b1b;padding:10px;border-radius:8px;margin-bottom:14px;font-size:13px}}
.hint{{margin-top:20px;padding:12px;background:#f0f9ff;border-radius:8px;font-size:12px;color:#0e7490;text-align:center}}</style></head>
<body><div class="box"><h1>💊 Pharmacie Pro</h1>
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
    stats = {}
    for k, sql in [
        ('medicaments', "SELECT COUNT(*) FROM medicaments"),
        ('officines', "SELECT COUNT(*) FROM officines"),
        ('lots', "SELECT COUNT(*) FROM lots WHERE statut='disponible'"),
        ('stock_total', "SELECT COALESCE(SUM(quantite),0) FROM lots WHERE statut='disponible'"),
        ('ordonnances', "SELECT COUNT(*) FROM ordonnances WHERE statut='en_attente'"),
        ('alertes', "SELECT COUNT(*) FROM alertes WHERE traitee=0"),
        ('ventes_jour', "SELECT COALESCE(SUM(montant_total),0) FROM ventes WHERE date(date_vente)=date('now')"),
        ('ventes_nb', "SELECT COUNT(*) FROM ventes WHERE date(date_vente)=date('now')"),
    ]:
        try:
            cur.execute(sql)
            stats[k] = cur.fetchone()[0]
        except Exception:
            stats[k] = 0

    cur.execute("""
        SELECT m.nom_commercial, COALESCE(SUM(vl.quantite),0) AS qte
        FROM vente_lignes vl
        JOIN medicaments m ON m.id=vl.medicament_id
        GROUP BY m.id ORDER BY qte DESC LIMIT 5
    """)
    top = cur.fetchall()
    top_html = ''.join(
        '<tr><td>' + str(t["nom_commercial"]) + '</td><td style="text-align:right">' + str(t["qte"]) + '</td></tr>'
        for t in top
    ) or '<tr><td colspan="2" style="text-align:center;color:#9ca3af">Pas encore de ventes</td></tr>'

    cur.execute("SELECT * FROM alertes WHERE traitee=0 ORDER BY id DESC LIMIT 8")
    alertes = cur.fetchall()
    alertes_html = ''.join(
        '<tr><td><span style="background:#f59e0b;color:#fff;padding:3px 10px;border-radius:12px;font-size:11px">' + str(a["type"]) + '</span></td><td>' + str(a["message"]) + '</td></tr>'
        for a in alertes
    ) or '<tr><td colspan="2" style="text-align:center;color:#10b981">✅ Aucune alerte ouverte</td></tr>'

    content = '<h1>💊 Tableau de bord Pharmacie Pro</h1>'
    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#06b6d4)"><div style="font-size:12px;opacity:.9">Médicaments référencés</div><div style="font-size:28px;font-weight:800">' + str(stats["medicaments"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div style="font-size:12px;opacity:.9">Officines actives</div><div style="font-size:28px;font-weight:800">' + str(stats["officines"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div style="font-size:12px;opacity:.9">Lots en stock</div><div style="font-size:28px;font-weight:800">' + str(stats["lots"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div style="font-size:12px;opacity:.9">Unités en stock</div><div style="font-size:28px;font-weight:800">' + f'{stats["stock_total"]:,}' + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div style="font-size:12px;opacity:.9">Alertes ouvertes</div><div style="font-size:28px;font-weight:800">' + str(stats["alertes"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div style="font-size:12px;opacity:.9">Ordonnances en attente</div><div style="font-size:28px;font-weight:800">' + str(stats["ordonnances"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#06b6d4,#0e7490)"><div style="font-size:12px;opacity:.9">CA du jour</div><div style="font-size:22px;font-weight:800">' + f'{stats["ventes_jour"]:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#7c3aed,#5b21b6)"><div style="font-size:12px;opacity:.9">Ventes du jour</div><div style="font-size:28px;font-weight:800">' + str(stats["ventes_nb"]) + '</div></div>'
    content += '</div>'
    content += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">'
    content += '<div class="card"><h3 style="margin-top:0;color:#0e7490">🏆 Top 5 médicaments vendus</h3>'
    content += '<table><thead><tr><th>Médicament</th><th style="text-align:right">Quantité</th></tr></thead>'
    content += '<tbody>' + top_html + '</tbody></table></div>'
    content += '<div class="card"><h3 style="margin-top:0;color:#0e7490">🚨 Alertes récentes</h3>'
    content += '<table><thead><tr><th>Type</th><th>Message</th></tr></thead>'
    content += '<tbody>' + alertes_html + '</tbody></table></div>'
    content += '</div>'
    return render_page(content, active='dashboard', page_title='Dashboard')


@app.route('/recherche')
@login_required
def recherche_globale():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()
    meds = []
    ords = []
    lots = []

    if q and len(q) >= 2:
        cur.execute("""
            SELECT m.*, c.code_interne, c.code_barre_ean13
            FROM medicaments m
            LEFT JOIN codes_produits c ON c.medicament_id=m.id AND c.type='medicament'
            WHERE m.nom_commercial LIKE ? OR m.dci LIKE ? OR m.code LIKE ? OR c.code_barre_ean13 LIKE ?
            LIMIT 20
        """, (f'%{q}%',) * 4)
        meds = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT * FROM ordonnances
            WHERE numero LIKE ? OR patient_nom LIKE ? OR medecin_nom LIKE ?
            LIMIT 10
        """, (f'%{q}%',) * 3)
        ords = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT l.*, m.nom_commercial, o.nom AS officine_nom
            FROM lots l
            JOIN medicaments m ON m.id=l.medicament_id
            JOIN officines o ON o.id=l.officine_id
            WHERE l.numero_lot LIKE ?
            LIMIT 10
        """, (f'%{q}%',))
        lots = [dict(r) for r in cur.fetchall()]

    total = len(meds) + len(ords) + len(lots)

    meds_html = ''.join(
        '<tr><td><strong>' + str(m["nom_commercial"]) + '</strong></td><td>' + str(m["dci"]) + '</td>'
        + '<td><code>' + str(m.get("code_interne") or "—") + '</code></td>'
        + '<td><code>' + str(m.get("code_barre_ean13") or "—") + '</code></td>'
        + '<td style="text-align:right">' + f'{m["prix_vente"]:,.0f}' + ' F</td></tr>'
        for m in meds
    )
    ords_html = ''.join(
        '<tr><td><strong>' + str(o["numero"]) + '</strong></td><td>' + str(o["patient_nom"]) + '</td>'
        + '<td>' + str(o["medecin_nom"] or "—") + '</td><td>' + str(o["statut"]) + '</td></tr>'
        for o in ords
    )
    lots_html = ''.join(
        '<tr><td><strong>' + str(l["numero_lot"]) + '</strong></td><td>' + str(l["nom_commercial"]) + '</td>'
        + '<td>' + str(l["officine_nom"]) + '</td><td style="text-align:right">' + str(l["quantite"]) + '</td></tr>'
        for l in lots
    )

    blocks = ''
    if q:
        blocks = '<div class="card" style="margin-top:20px"><h3 style="margin-top:0;color:#0e7490">💊 Médicaments (' + str(len(meds)) + ')</h3>'
        blocks += '<table><thead><tr><th>Nom</th><th>DCI</th><th>Code interne</th><th>Code-barre</th><th style="text-align:right">Prix</th></tr></thead>'
        blocks += '<tbody>' + (meds_html or '<tr><td colspan="5" style="text-align:center;color:#9ca3af;padding:20px">Aucun résultat</td></tr>') + '</tbody></table></div>'
        blocks += '<div class="card"><h3 style="margin-top:0;color:#0e7490">📋 Ordonnances (' + str(len(ords)) + ')</h3>'
        blocks += '<table><thead><tr><th>N°</th><th>Patient</th><th>Médecin</th><th>Statut</th></tr></thead>'
        blocks += '<tbody>' + (ords_html or '<tr><td colspan="4" style="text-align:center;color:#9ca3af;padding:20px">Aucun résultat</td></tr>') + '</tbody></table></div>'
        blocks += '<div class="card"><h3 style="margin-top:0;color:#0e7490">📦 Lots (' + str(len(lots)) + ')</h3>'
        blocks += '<table><thead><tr><th>N° Lot</th><th>Médicament</th><th>Officine</th><th style="text-align:right">Qté</th></tr></thead>'
        blocks += '<tbody>' + (lots_html or '<tr><td colspan="4" style="text-align:center;color:#9ca3af;padding:20px">Aucun résultat</td></tr>') + '</tbody></table></div>'

    info = ''
    if q:
        info = '<br>📊 <strong>' + str(total) + ' résultat(s)</strong> pour "' + q + '"'

    content = '<h1>🔍 Recherche globale</h1>'
    content += '<form method="get" style="margin-bottom:20px">'
    content += '<input type="text" name="q" id="search-input" value="' + q + '" placeholder="Nom médicament, DCI, code-barres, n° ordonnance, n° lot..." autofocus style="font-size:16px;padding:16px;border:3px solid #06b6d4;border-radius:12px;max-width:700px">'
    content += '<button type="submit" class="btn btn-primary" style="margin-left:10px;padding:16px 30px">🔍 Rechercher</button>'
    content += '</form>'
    content += '<script>'
    content += "document.getElementById('search-input').focus();"
    content += "document.addEventListener('keydown', function(e) {"
    content += "if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); document.getElementById('search-input').focus(); document.getElementById('search-input').select(); }"
    content += '});'
    content += '</script>'
    content += '<div style="padding:14px;background:#f0f9ff;border-left:4px solid #06b6d4;border-radius:8px;font-size:13px">'
    content += '💡 <strong>Astuce</strong> : Ctrl+K pour revenir au champ. Tapez 2 caractères minimum.' + info
    content += '</div>'
    content += blocks
    return render_page(content, active='recherche', page_title='Recherche')


@app.route('/medicaments')
@login_required
def medicaments_liste():
    db = get_db()
    cur = db.cursor()
    q = request.args.get('q', '').strip()
    sql = "SELECT * FROM medicaments WHERE 1=1"
    params = []
    if q:
        sql += " AND (nom_commercial LIKE ? OR dci LIKE ? OR code LIKE ?)"
        params = [f'%{q}%'] * 3
    sql += " ORDER BY nom_commercial LIMIT 200"
    cur.execute(sql, params)
    meds = cur.fetchall()

    rows = ''.join(
        '<tr><td><strong>' + str(m["code"] or "—") + '</strong></td><td>' + str(m["nom_commercial"]) + '</td>'
        + '<td>' + str(m["dci"]) + '</td><td>' + str(m["forme"] or "—") + '</td><td>' + str(m["dosage"] or "—") + '</td>'
        + '<td>' + str(m["categorie"] or "—") + '</td>'
        + '<td style="text-align:right">' + f'{m["prix_vente"]:,.0f}' + ' F</td>'
        + '<td style="text-align:center">' + ('⚠' if m["ordonnance_requise"] else '✓') + '</td>'
        + '<td>' + str(m["tableau"] or "—") + '</td></tr>'
        for m in meds
    )

    content = '<h1>💊 Catalogue médicaments (' + str(len(meds)) + ')</h1>'
    content += '<form method="get" style="margin-bottom:16px;display:flex;gap:10px">'
    content += '<input type="text" name="q" value="' + q + '" placeholder="Rechercher..." style="max-width:400px">'
    content += '<button type="submit" class="btn btn-primary">🔍 Rechercher</button>'
    content += '</form>'
    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code</th><th>Nom commercial</th><th>DCI</th><th>Forme</th><th>Dosage</th><th>Catégorie</th><th style="text-align:right">Prix</th><th style="text-align:center">Ordonnance</th><th>Tableau</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="9" style="padding:40px;text-align:center;color:#9ca3af">Aucun médicament</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='medicaments', page_title='Médicaments')


@app.route('/stock')
@login_required
def stock_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT l.*, m.nom_commercial, m.dci, o.nom AS officine_nom,
               CAST(julianday(l.date_peremption) - julianday('now') AS INTEGER) AS jours_restants
        FROM lots l
        JOIN medicaments m ON m.id=l.medicament_id
        JOIN officines o ON o.id=l.officine_id
        WHERE l.statut='disponible'
        ORDER BY l.date_peremption ASC LIMIT 300
    """)
    lots = cur.fetchall()

    rows = ''
    for l in lots:
        jours = l['jours_restants'] or 0
        color = '#10b981'
        if jours <= 30:
            color = '#ef4444'
        elif jours <= 90:
            color = '#f59e0b'
        rows += '<tr><td><strong>' + str(l["numero_lot"]) + '</strong></td><td>' + str(l["nom_commercial"]) + '</td>'
        rows += '<td>' + str(l["officine_nom"]) + '</td><td style="text-align:right">' + str(l["quantite"]) + '</td>'
        rows += '<td style="color:' + color + ';font-weight:700">' + str(l["date_peremption"]) + '</td>'
        rows += '<td style="color:' + color + '">' + str(jours) + ' j</td><td>' + str(l["emplacement"] or "—") + '</td></tr>'

    content = '<h1>📦 Stock des lots — ' + str(len(lots)) + '</h1>'
    content += '<div style="margin-bottom:16px;font-size:13px;color:#6b7280">🟢 DLC &gt; 90j · 🟠 DLC 30-90j · 🔴 DLC &lt; 30j</div>'
    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Lot</th><th>Médicament</th><th>Officine</th><th style="text-align:right">Quantité</th><th>DLC</th><th>Jours restants</th><th>Emplacement</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#9ca3af">Aucun lot</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='stock', page_title='Stock')


@app.route('/ordonnances')
@login_required
def ordonnances_liste():
    db = get_db()
    cur = db.cursor()
    statut = request.args.get('statut', '')
    sql = "SELECT * FROM ordonnances"
    params = []
    if statut:
        sql += " WHERE statut=?"
        params = [statut]
    sql += " ORDER BY id DESC LIMIT 200"
    cur.execute(sql, params)
    ords = cur.fetchall()

    rows = ''
    for o in ords:
        color = {'en_attente': '#f59e0b', 'delivree': '#10b981',
                 'partielle': '#3b82f6', 'annulee': '#ef4444'}.get(o['statut'], '#6b7280')
        rows += '<tr><td><strong>' + str(o["numero"]) + '</strong></td><td>' + str(o["patient_nom"] or "—") + '</td>'
        rows += '<td>' + str(o["patient_age"] or "—") + ' ans</td><td>' + str(o["medecin_nom"] or "—") + '</td>'
        rows += '<td>' + str(o["etablissement"] or "—") + '</td><td>' + str(o["date_prescription"] or "—") + '</td>'
        rows += '<td><span style="background:' + color + ';color:#fff;padding:3px 10px;border-radius:12px;font-size:11px">' + str(o["statut"]) + '</span></td></tr>'

    content = '<h1>📋 Ordonnances — ' + str(len(ords)) + '</h1>'
    content += '<div style="margin-bottom:16px">'
    content += '<a href="/ordonnances" class="btn btn-primary">Toutes</a>'
    content += '<a href="/ordonnances?statut=en_attente" class="btn btn-primary" style="margin-left:6px">En attente</a>'
    content += '<a href="/ordonnances?statut=delivree" class="btn btn-success" style="margin-left:6px">Délivrées</a>'
    content += '</div>'
    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Ordonnance</th><th>Patient</th><th>Âge</th><th>Médecin</th><th>Établissement</th><th>Date</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#9ca3af">Aucune ordonnance</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='ordonnances', page_title='Ordonnances')


@app.route('/ventes')
@login_required
def ventes_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT v.*, o.nom AS officine_nom, u.nom_complet AS caissier_nom
        FROM ventes v
        LEFT JOIN officines o ON o.id=v.officine_id
        LEFT JOIN users u ON u.id=v.caissier_id
        ORDER BY v.id DESC LIMIT 200
    """)
    ventes = cur.fetchall()

    rows = ''.join(
        '<tr><td><strong>' + str(v["numero"] or "—") + '</strong></td><td>' + str(v["officine_nom"] or "—") + '</td>'
        + '<td>' + str(v["caissier_nom"] or "—") + '</td>'
        + '<td style="text-align:right">' + f'{v["montant_total"]:,.0f}' + ' F</td>'
        + '<td>' + str(v["mode_paiement"] or "—") + '</td>'
        + '<td>' + str((v["date_vente"] or "")[:16]) + '</td><td>' + str(v["statut"] or "—") + '</td></tr>'
        for v in ventes
    )

    content = '<h1>🛒 Ventes (POS) — ' + str(len(ventes)) + '</h1>'
    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Vente</th><th>Officine</th><th>Caissier</th><th style="text-align:right">Montant</th><th>Paiement</th><th>Date</th><th>Statut</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="7" style="padding:40px;text-align:center;color:#9ca3af">Aucune vente</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='ventes', page_title='Ventes')


@app.route('/commandes')
@login_required
def commandes_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, f.nom AS fournisseur_nom, o.nom AS officine_nom
        FROM commandes c
        LEFT JOIN fournisseurs f ON f.id=c.fournisseur_id
        LEFT JOIN officines o ON o.id=c.officine_id
        ORDER BY c.id DESC LIMIT 100
    """)
    cmds = cur.fetchall()

    rows = ''.join(
        '<tr><td><strong>' + str(c["numero"] or "—") + '</strong></td><td>' + str(c["fournisseur_nom"] or "—") + '</td>'
        + '<td>' + str(c["officine_nom"] or "—") + '</td>'
        + '<td style="text-align:right">' + f'{c["montant_total"]:,.0f}' + ' F</td>'
        + '<td>' + str(c["statut"] or "—") + '</td><td>' + str(c["date_commande"] or "—") + '</td></tr>'
        for c in cmds
    )

    content = '<h1>📥 Commandes grossistes — ' + str(len(cmds)) + '</h1>'
    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>N° Commande</th><th>Fournisseur</th><th>Officine</th><th style="text-align:right">Montant</th><th>Statut</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="6" style="padding:40px;text-align:center;color:#9ca3af">Aucune commande</td></tr>') + '</tbody></table></div>'
    content += '<div class="card"><h3 style="margin-top:0;color:#0e7490">🏢 Grossistes partenaires</h3>'
    content += '<p style="color:#6b7280;font-size:13px">SONAPHARM · COPHARMED · LABOREX Sénégal</p></div>'
    return render_page(content, active='commandes', page_title='Commandes')


@app.route('/alertes')
@login_required
def alertes_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT a.*, m.nom_commercial
        FROM alertes a
        LEFT JOIN lots l ON l.id=a.lot_id
        LEFT JOIN medicaments m ON m.id=l.medicament_id
        ORDER BY a.id DESC LIMIT 200
    """)
    alertes = cur.fetchall()

    rows = ''
    for a in alertes:
        color = {'rupture': '#ef4444', 'peremption': '#f59e0b',
                 'contrefacon': '#7c3aed'}.get(a['type'], '#6b7280')
        rows += '<tr><td><span style="background:' + color + ';color:#fff;padding:3px 10px;border-radius:12px;font-size:11px">' + str(a["type"]) + '</span></td>'
        rows += '<td>' + str(a["nom_commercial"] or "—") + '</td><td>' + str(a["message"]) + '</td>'
        rows += '<td>' + ('✅' if a["traitee"] else '🔴 Ouverte') + '</td>'
        rows += '<td>' + str((a["date_alerte"] or "")[:16]) + '</td></tr>'

    content = '<h1>🚨 Alertes — ' + str(len(alertes)) + '</h1>'
    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Type</th><th>Médicament</th><th>Message</th><th>État</th><th>Date</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="5" style="padding:40px;text-align:center;color:#10b981">✅ Aucune alerte</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='alertes', page_title='Alertes')


@app.route('/rapports')
@login_required
def rapports_index():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT m.categorie,
               COUNT(DISTINCT m.id) AS nb_meds,
               COALESCE(SUM(l.quantite),0) AS stock_total
        FROM medicaments m
        LEFT JOIN lots l ON l.medicament_id=m.id AND l.statut='disponible'
        GROUP BY m.categorie
        ORDER BY stock_total DESC
    """)
    stats = cur.fetchall()
    rows = ''.join(
        '<tr><td>' + str(s["categorie"] or "Non catégorisé") + '</td>'
        + '<td style="text-align:right">' + str(s["nb_meds"]) + '</td>'
        + '<td style="text-align:right">' + f'{s["stock_total"]:,}' + '</td></tr>'
        for s in stats
    )

    content = '<h1>📈 Rapports & Statistiques</h1>'
    content += '<div class="card"><h3 style="margin-top:0;color:#0e7490">📊 Stock par catégorie thérapeutique</h3>'
    content += '<table><thead><tr><th>Catégorie</th><th style="text-align:right">Nb médicaments</th><th style="text-align:right">Stock total</th></tr></thead>'
    content += '<tbody>' + rows + '</tbody></table></div>'
    content += '<div class="card"><h3 style="margin-top:0;color:#0e7490">🎯 Indicateurs cibles SM10 AGRO</h3>'
    content += '<ul style="line-height:2;color:#374151">'
    content += '<li>📉 <strong>-50%</strong> ruptures de stock</li>'
    content += '<li>🚫 <strong>-80%</strong> contrefaçons</li>'
    content += '<li>🏥 <strong>1500</strong> officines Sénégal cible</li>'
    content += '<li>🌍 <strong>5000</strong> officines CEDEAO cible</li>'
    content += '</ul></div>'
    return render_page(content, active='rapports', page_title='Rapports')


@app.route('/caisse/sessions')
@login_required
def caisse_sessions():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.*, u.nom_complet AS caissier_nom, o.nom AS officine_nom
        FROM caissiers_sessions s
        LEFT JOIN users u ON u.id=s.caissier_id
        LEFT JOIN officines o ON o.id=s.officine_id
        ORDER BY s.id DESC LIMIT 100
    """)
    sessions = cur.fetchall()

    rows = ''
    for s in sessions:
        statut_color = '#10b981' if s['statut'] == 'ouverte' else '#6b7280'
        ecart_color = '#ef4444' if abs(s['ecart'] or 0) > 100 else '#10b981'
        btn_close = ''
        if s['statut'] == 'ouverte':
            btn_close = '<a href="/caisse/sessions/' + str(s["id"]) + '/fermer" class="btn btn-danger" style="padding:5px 12px;font-size:12px;margin-left:4px">🔒</a>'
        rows += '<tr><td>#' + str(s["id"]) + '</td>'
        rows += '<td><strong>' + str(s["caissier_nom"] or "—") + '</strong></td>'
        rows += '<td>' + str(s["officine_nom"] or "—") + '</td>'
        rows += '<td>' + str((s["date_ouverture"] or "")[:16]) + '</td>'
        ferme = (s["date_fermeture"] or "—")[:16] if s["date_fermeture"] else "—"
        rows += '<td>' + ferme + '</td>'
        rows += '<td style="text-align:right">' + str(s["nb_ventes"]) + '</td>'
        rows += '<td style="text-align:right">' + f'{s["total_ventes"]:,.0f}' + ' F</td>'
        rows += '<td style="text-align:right;color:' + ecart_color + ';font-weight:700">' + f'{s["ecart"]:,.0f}' + ' F</td>'
        rows += '<td><span style="background:' + statut_color + ';color:#fff;padding:3px 10px;border-radius:12px;font-size:11px">' + str(s["statut"]) + '</span></td>'
        rows += '<td><a href="/caisse/sessions/' + str(s["id"]) + '" class="btn btn-primary" style="padding:5px 12px;font-size:12px">👁</a>' + btn_close + '</td></tr>'

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🖥️ Sessions caissiers</h1>'
    content += '<a href="/caisse/sessions/ouvrir" class="btn btn-success">+ Ouvrir une caisse</a></div>'
    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>#</th><th>Caissier</th><th>Officine</th><th>Ouverture</th><th>Fermeture</th><th style="text-align:right">Ventes</th><th style="text-align:right">Total</th><th style="text-align:right">Écart</th><th>Statut</th><th>Actions</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="10" style="padding:40px;text-align:center;color:#9ca3af">Aucune session</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='caisse', page_title='Sessions caissiers')


@app.route('/caisse/sessions/ouvrir', methods=['GET', 'POST'])
@login_required
def caisse_session_ouvrir():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            officine_id = int(request.form.get('officine_id') or 0)
            fonds_initial = float(request.form.get('fonds_initial') or 0)
            notes = request.form.get('notes_ouverture') or ''

            cur.execute("SELECT COUNT(*) FROM caissiers_sessions WHERE caissier_id=? AND statut='ouverte'", (current_user.id,))
            if cur.fetchone()[0] > 0:
                flash('❌ Vous avez déjà une caisse ouverte', 'error')
                return redirect('/caisse/sessions')

            cur.execute("""
                INSERT INTO caissiers_sessions
                (caissier_id, officine_id, date_ouverture, fonds_initial, statut, notes_ouverture, created_at)
                VALUES (?,?,?,?,'ouverte',?,?)
            """, (current_user.id, officine_id, datetime.now().isoformat(),
                  fonds_initial, notes, datetime.now().isoformat()))
            db.commit()
            log_action(current_user.id, 'OUVERTURE_CAISSE', f'Fonds: {fonds_initial}',
                       'caissiers_sessions', cur.lastrowid)
            flash('✅ Caisse ouverte — Fonds initial : ' + f'{fonds_initial:,.0f}' + ' F', 'success')
            return redirect('/caisse/sessions')
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    cur.execute("SELECT id, nom, region FROM officines WHERE actif=1")
    offs = cur.fetchall()
    opts = ''.join('<option value="' + str(o["id"]) + '">' + str(o["nom"]) + ' (' + str(o["region"]) + ')</option>' for o in offs)

    content = '<h1>🖥️ Ouvrir une caisse</h1>'
    content += '<form method="post" class="card" style="max-width:600px">'
    content += '<div style="margin-bottom:16px"><label>Officine *</label>'
    content += '<select name="officine_id" required><option value="">— Sélectionner —</option>' + opts + '</select></div>'
    content += '<div style="margin-bottom:16px"><label>Fonds initial (FCFA) *</label>'
    content += '<input type="number" name="fonds_initial" required value="50000" min="0" step="1000" autofocus></div>'
    content += '<div style="margin-bottom:16px"><label>Notes d\'ouverture</label>'
    content += '<textarea name="notes_ouverture" rows="3"></textarea></div>'
    content += '<button type="submit" class="btn btn-success">🖥️ Ouvrir la caisse</button>'
    content += '<a href="/caisse/sessions" class="btn" style="background:#e5e7eb;color:#374151;margin-left:8px">Annuler</a>'
    content += '</form>'
    return render_page(content, active='caisse', page_title='Ouvrir caisse')


@app.route('/caisse/sessions/<int:sid>')
@login_required
def caisse_session_detail(sid):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.*, u.nom_complet AS caissier_nom, o.nom AS officine_nom
        FROM caissiers_sessions s
        LEFT JOIN users u ON u.id=s.caissier_id
        LEFT JOIN officines o ON o.id=s.officine_id
        WHERE s.id=?
    """, (sid,))
    s = cur.fetchone()
    if not s:
        flash('❌ Session introuvable', 'error')
        return redirect('/caisse/sessions')

    cur.execute("SELECT * FROM ventes WHERE caissier_id=? AND date_vente >= ? ORDER BY id DESC",
                (s['caissier_id'], s['date_ouverture']))
    ventes = cur.fetchall()
    ventes_html = ''.join(
        '<tr><td>' + str(v["numero"] or "—") + '</td><td>' + str((v["date_vente"] or "")[:16]) + '</td>'
        + '<td style="text-align:right">' + f'{v["montant_total"]:,.0f}' + ' F</td>'
        + '<td>' + str(v["mode_paiement"] or "—") + '</td></tr>'
        for v in ventes
    )

    cur.execute("SELECT * FROM caissiers_paiements WHERE session_id=? ORDER BY id DESC", (sid,))
    paiements = cur.fetchall()
    paiements_html = ''.join(
        '<tr><td>' + str((p["date_paiement"] or "")[:16]) + '</td>'
        + '<td style="text-align:right">' + f'{p["montant"]:,.0f}' + ' F</td>'
        + '<td>' + str(p["mode"]) + '</td><td>' + str(p["reference"] or "—") + '</td></tr>'
        for p in paiements
    )

    ecart_color = '#ef4444' if abs(s['ecart'] or 0) > 100 else '#10b981'

    content = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
    content += '<h1 style="margin:0">🖥️ Session #' + str(s["id"]) + '</h1>'
    content += '<div><a href="/caisse/sessions/' + str(sid) + '/verser" class="btn btn-primary">💳 Versement</a>'
    content += '<a href="/caisse/sessions" class="btn" style="background:#e5e7eb;color:#374151;margin-left:6px">← Retour</a></div></div>'

    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#06b6d4)"><div style="font-size:12px">Caissier</div><div style="font-size:18px;font-weight:800">' + str(s["caissier_nom"] or "—") + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div style="font-size:12px">Ventes</div><div style="font-size:28px;font-weight:800">' + str(s["nb_ventes"]) + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div style="font-size:12px">Total FCFA</div><div style="font-size:22px;font-weight:800">' + f'{s["total_ventes"]:,.0f}' + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div style="font-size:12px">Espèces</div><div style="font-size:22px;font-weight:800">' + f'{s["total_especes"]:,.0f}' + '</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div style="font-size:12px">Mobile Money</div><div style="font-size:22px;font-weight:800">' + f'{s["total_mobile_money"]:,.0f}' + '</div></div>'
    content += '</div>'

    content += '<div class="card"><h3 style="margin-top:0">💰 Détail</h3><table>'
    content += '<tr><td>Fonds initial</td><td style="text-align:right">' + f'{s["fonds_initial"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td>Espèces</td><td style="text-align:right">' + f'{s["total_especes"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td>Mobile Money</td><td style="text-align:right">' + f'{s["total_mobile_money"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td>Carte</td><td style="text-align:right">' + f'{s["total_carte"]:,.0f}' + ' F</td></tr>'
    content += '<tr style="background:#f0fdf4;font-weight:800"><td>Total ventes</td><td style="text-align:right">' + f'{s["total_ventes"]:,.0f}' + ' F</td></tr>'
    content += '<tr><td>Montant compté</td><td style="text-align:right">' + f'{s["montant_compte"]:,.0f}' + ' F</td></tr>'
    content += '<tr style="background:#fef2f2;font-weight:800"><td>Écart</td><td style="text-align:right;color:' + ecart_color + '">' + f'{s["ecart"]:,.0f}' + ' F</td></tr>'
    content += '</table></div>'

    content += '<div class="card"><h3 style="margin-top:0">🧾 Ventes (' + str(len(ventes)) + ')</h3>'
    content += '<table><thead><tr><th>N°</th><th>Date</th><th style="text-align:right">Montant</th><th>Paiement</th></tr></thead>'
    content += '<tbody>' + (ventes_html or '<tr><td colspan="4" style="text-align:center;color:#9ca3af;padding:20px">Aucune vente</td></tr>') + '</tbody></table></div>'

    content += '<div class="card"><h3 style="margin-top:0">💳 Versements (' + str(len(paiements)) + ')</h3>'
    content += '<table><thead><tr><th>Date</th><th style="text-align:right">Montant</th><th>Mode</th><th>Référence</th></tr></thead>'
    content += '<tbody>' + (paiements_html or '<tr><td colspan="4" style="text-align:center;color:#9ca3af;padding:20px">Aucun versement</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='caisse', page_title='Session')


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
    content += '<div style="background:#f0f9ff;padding:14px;border-radius:8px;margin-bottom:16px;font-size:13px">'
    content += '<strong>Attendu en caisse</strong> : ' + f'{attendu:,.0f}' + ' F</div>'
    content += '<div style="margin-bottom:16px"><label>Montant compté (FCFA) *</label>'
    content += '<input type="number" name="montant_compte" required step="100" autofocus style="width:100%;font-size:20px;padding:14px"></div>'
    content += '<div style="margin-bottom:16px"><label>Notes</label>'
    content += '<textarea name="notes_fermeture" rows="3"></textarea></div>'
    content += '<button type="submit" class="btn btn-danger">🔒 Fermer la caisse</button>'
    content += '<a href="/caisse/sessions/' + str(sid) + '" class="btn" style="background:#e5e7eb;color:#374151;margin-left:8px">Annuler</a>'
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
            log_action(current_user.id, 'VERSEMENT_CAISSE', f'{montant} F mode {mode}',
                       'caissiers_paiements', cur.lastrowid)
            flash('✅ Versement de ' + f'{montant:,.0f}' + ' F enregistré', 'success')
            return redirect('/caisse/sessions/' + str(sid))
        except Exception as e:
            db.rollback()
            flash('❌ ' + str(e), 'error')

    content = '<h1>💳 Enregistrer un versement — Session #' + str(sid) + '</h1>'
    content += '<form method="post" class="card" style="max-width:600px">'
    content += '<div style="margin-bottom:16px"><label>Montant (FCFA) *</label>'
    content += '<input type="number" name="montant" required step="100" min="100" autofocus style="width:100%;font-size:20px;padding:14px"></div>'
    content += '<div style="margin-bottom:16px"><label>Mode</label><select name="mode">'
    content += '<option value="especes">💵 Espèces</option><option value="mobile_money">📱 Mobile Money</option><option value="virement">🏦 Virement</option></select></div>'
    content += '<div style="margin-bottom:16px"><label>Référence</label><input type="text" name="reference"></div>'
    content += '<button type="submit" class="btn btn-success">💳 Enregistrer</button>'
    content += '<a href="/caisse/sessions/' + str(sid) + '" class="btn" style="background:#e5e7eb;color:#374151;margin-left:8px">Annuler</a>'
    content += '</form>'
    return render_page(content, active='caisse', page_title='Versement')


@app.route('/finances')
@login_required
def finances_dashboard():
    db = get_db()
    cur = db.cursor()

    def sc(sql, default=0):
        try:
            cur.execute(sql)
            r = cur.fetchone()
            return r[0] if r and r[0] is not None else default
        except Exception:
            return default

    ca_jour = sc("SELECT COALESCE(SUM(montant_total),0) FROM ventes WHERE date(date_vente)=date('now')")
    ca_mois = sc("SELECT COALESCE(SUM(montant_total),0) FROM ventes WHERE strftime('%Y-%m',date_vente)=strftime('%Y-%m','now')")
    ca_an = sc("SELECT COALESCE(SUM(montant_total),0) FROM ventes")
    nb_ventes = sc("SELECT COUNT(*) FROM ventes")
    panier_moyen = (ca_an / nb_ventes) if nb_ventes > 0 else 0

    valeur_stock_vente = sc("""
        SELECT COALESCE(SUM(l.quantite * m.prix_vente),0)
        FROM lots l JOIN medicaments m ON m.id=l.medicament_id
        WHERE l.statut='disponible'
    """)
    cout_achat = sc("SELECT COALESCE(SUM(quantite * prix_achat_unitaire),0) FROM lots WHERE statut='disponible'")
    marge_brute = valeur_stock_vente - cout_achat

    especes_caisse = sc("""
        SELECT COALESCE(SUM(total_especes - COALESCE(
            (SELECT SUM(montant) FROM caissiers_paiements WHERE session_id=caissiers_sessions.id), 0
        )), 0)
        FROM caissiers_sessions WHERE statut='ouverte'
    """)

    cur.execute("""
        SELECT COALESCE(mode_paiement,'inconnu') AS mode, COUNT(*) AS nb, COALESCE(SUM(montant_total),0) AS total
        FROM ventes GROUP BY mode_paiement
    """)
    modes = cur.fetchall()
    modes_html = ''.join(
        '<tr><td>' + str(m["mode"]) + '</td><td style="text-align:right">' + str(m["nb"]) + '</td>'
        + '<td style="text-align:right">' + f'{m["total"]:,.0f}' + ' F</td></tr>'
        for m in modes
    ) or '<tr><td colspan="3" style="text-align:center;color:#9ca3af;padding:20px">Aucune vente</td></tr>'

    content = '<h1>💰 États financiers</h1>'
    content += '<div class="kpi">'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#10b981,#047857)"><div style="font-size:12px">CA du jour</div><div style="font-size:22px;font-weight:800">' + f'{ca_jour:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#0891b2,#06b6d4)"><div style="font-size:12px">CA du mois</div><div style="font-size:22px;font-weight:800">' + f'{ca_mois:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9)"><div style="font-size:12px">CA annuel</div><div style="font-size:22px;font-weight:800">' + f'{ca_an:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#f59e0b,#b45309)"><div style="font-size:12px">Panier moyen</div><div style="font-size:22px;font-weight:800">' + f'{panier_moyen:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ec4899,#be185d)"><div style="font-size:12px">Stock valorisé</div><div style="font-size:20px;font-weight:800">' + f'{valeur_stock_vente:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#06b6d4,#0e7490)"><div style="font-size:12px">Marge brute</div><div style="font-size:22px;font-weight:800">' + f'{marge_brute:,.0f}' + ' F</div></div>'
    content += '<div class="kpi-card" style="background:linear-gradient(135deg,#ef4444,#b91c1c)"><div style="font-size:12px">Espèces en caisse</div><div style="font-size:22px;font-weight:800">' + f'{especes_caisse:,.0f}' + ' F</div></div>'
    content += '</div>'

    content += '<div class="card"><h3 style="margin-top:0;color:#0e7490">💳 Répartition par mode</h3>'
    content += '<table><thead><tr><th>Mode</th><th style="text-align:right">Nb</th><th style="text-align:right">Total</th></tr></thead>'
    content += '<tbody>' + modes_html + '</tbody></table></div>'

    content += '<div class="card"><h3 style="margin-top:0;color:#0e7490">📊 Compte de résultat</h3><table>'
    content += '<tr><td><strong>PRODUITS</strong></td><td style="text-align:right"><strong>' + f'{ca_an:,.0f}' + ' F</strong></td></tr>'
    content += '<tr><td><strong>CHARGES</strong></td><td style="text-align:right"><strong>' + f'{cout_achat:,.0f}' + ' F</strong></td></tr>'
    content += '<tr style="background:#f0fdf4;font-weight:800"><td>RÉSULTAT NET</td>'
    content += '<td style="text-align:right;color:#047857">' + f'{ca_an - cout_achat:,.0f}' + ' F</td></tr>'
    content += '</table></div>'

    content += '<div style="margin-top:20px;display:flex;gap:10px;flex-wrap:wrap">'
    content += '<a href="/finances/export-csv" class="btn btn-primary">⬇ Export CSV</a>'
    content += '<a href="/finances/rapport.pdf" class="btn btn-success">📄 Rapport PDF</a>'
    content += '<a href="/caisse/sessions" class="btn" style="background:#e5e7eb;color:#374151">🖥️ Sessions</a></div>'
    return render_page(content, active='finances', page_title='Finances')


@app.route('/finances/export-csv')
@login_required
def finances_export_csv():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT v.numero, v.date_vente, v.montant_total, v.mode_paiement,
               u.nom_complet AS caissier, o.nom AS officine
        FROM ventes v
        LEFT JOIN users u ON u.id=v.caissier_id
        LEFT JOIN officines o ON o.id=v.officine_id
        ORDER BY v.id DESC LIMIT 1000
    """)
    rows = cur.fetchall()

    si = io.StringIO()
    w = csv.writer(si, delimiter=';')
    w.writerow(['N° Vente', 'Date', 'Montant', 'Mode', 'Caissier', 'Officine'])
    for r in rows:
        w.writerow([r['numero'], r['date_vente'], r['montant_total'],
                    r['mode_paiement'], r['caissier'], r['officine']])

    log_action(current_user.id, 'EXPORT_CSV', str(len(rows)), 'ventes')
    return Response(si.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=ventes_pharmacie_' + datetime.now().strftime("%Y%m%d") + '.csv'})


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

    ca_an = sc("SELECT COALESCE(SUM(montant_total),0) FROM ventes")
    cout = sc("SELECT COALESCE(SUM(quantite * prix_achat_unitaire),0) FROM lots")
    val_stock = sc("SELECT COALESCE(SUM(l.quantite * m.prix_vente),0) FROM lots l JOIN medicaments m ON m.id=l.medicament_id WHERE l.statut='disponible'")

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    c.setFillColor(colors.HexColor('#0891b2'))
    c.rect(0, h - 30*mm, w, 30*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(15*mm, h - 15*mm, "PHARMACIE PRO")
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, h - 21*mm, "États financiers consolidés")
    c.drawRightString(w - 15*mm, h - 15*mm, datetime.now().strftime('%d/%m/%Y'))

    y = h - 45*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(15*mm, y, "COMPTE DE RESULTAT")
    y -= 10*mm
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, y, "Produits (ventes) : " + f'{ca_an:,.0f}' + " FCFA")
    y -= 6*mm
    c.drawString(15*mm, y, "Charges (achats) : " + f'{cout:,.0f}' + " FCFA")
    y -= 6*mm
    c.setFillColor(colors.HexColor('#047857'))
    c.setFont('Helvetica-Bold', 11)
    c.drawString(15*mm, y, "RESULTAT NET : " + f'{ca_an - cout:,.0f}' + " FCFA")

    y -= 15*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(15*mm, y, "BILAN SIMPLIFIE")
    y -= 10*mm
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, y, "Stock valorise : " + f'{val_stock:,.0f}' + " FCFA")

    c.setFont('Helvetica', 7)
    c.setFillColor(colors.grey)
    c.drawString(15*mm, 10*mm, "PHARMACIE PRO - Dakar, Senegal")

    c.showPage()
    c.save()
    buf.seek(0)

    log_action(current_user.id, 'RAPPORT_FINANCIER_PDF', 'Etats financiers', 'finances')
    return send_file(buf, mimetype='application/pdf',
                     download_name='finances_pharmacie_' + datetime.now().strftime("%Y%m%d") + '.pdf')


# ═══════════════════════════════════════════════════════════════
# 🛒 POS
# ═══════════════════════════════════════════════════════════════

@app.route('/pos')
@login_required
def pos_interface():
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM caissiers_sessions WHERE caissier_id=? AND statut='ouverte' ORDER BY id DESC LIMIT 1",
                (current_user.id,))
    session_row = cur.fetchone()

    if not session_row:
        flash('⚠️ Aucune caisse ouverte. Ouvrez une caisse pour utiliser le POS.', 'error')
        return redirect('/caisse/sessions/ouvrir')

    cur.execute("""
        SELECT m.id, m.nom_commercial, m.dci, m.prix_vente, m.presentation,
               c.code_interne, c.code_barre_ean13,
               COALESCE(SUM(l.quantite),0) AS stock_total
        FROM medicaments m
        LEFT JOIN codes_produits c ON c.medicament_id=m.id AND c.type='medicament'
        LEFT JOIN lots l ON l.medicament_id=m.id AND l.statut='disponible'
        GROUP BY m.id
        ORDER BY m.nom_commercial
        LIMIT 100
    """)
    produits = cur.fetchall()

    cards_html = ''
    for p in produits:
        stock_total = p['stock_total'] or 0
        if stock_total > 10:
            stock_color = '#10b981'
        elif stock_total > 0:
            stock_color = '#f59e0b'
        else:
            stock_color = '#ef4444'

        nom_html = (p['nom_commercial'] or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
        dci_html = (p['dci'] or '')[:30].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        cards_html += (
            '<div class="pos-product" data-id="' + str(p['id']) + '" '
            + 'data-nom="' + nom_html + '" '
            + 'data-prix="' + str(p['prix_vente']) + '">'
            + '<div style="font-weight:700;color:#0e7490;font-size:13px;line-height:1.2;margin-bottom:6px">' + nom_html + '</div>'
            + '<div style="font-size:11px;color:#6b7280;margin-bottom:8px">' + dci_html + '</div>'
            + '<div style="display:flex;justify-content:space-between;align-items:center">'
            + '<div style="font-weight:800;color:#10b981;font-size:16px">' + f'{p["prix_vente"]:,.0f}' + ' F</div>'
            + '<div style="font-size:10px;background:' + stock_color + ';color:#fff;padding:2px 8px;border-radius:10px">stock ' + str(stock_total) + '</div>'
            + '</div></div>'
        )

    # POS HTML — JavaScript inline pour éviter problèmes f-string
    pos_html = '''
    <div style="display:grid;grid-template-columns:1fr 380px;gap:16px">
      <div>
        <input type="text" id="pos-search" class="pos-search" placeholder="🔍 Recherche (Ctrl+K)" autofocus>
        <div class="pos-grid" id="pos-grid">
    ''' + cards_html + '''
        </div>
      </div>
      <div class="pos-cart">
        <h3 style="margin-top:0;color:#0e7490">🛒 Panier</h3>
        <div id="cart-items" style="min-height:200px;max-height:400px;overflow-y:auto"></div>
        <div style="margin-top:16px;padding-top:16px;border-top:2px solid #e5e7eb">
          <div style="display:flex;justify-content:space-between;font-size:14px">
            <span>Total</span><span id="cart-total" style="font-weight:800;font-size:20px;color:#10b981">0 F</span>
          </div>
        </div>
        <div style="margin-top:16px">
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
          🗑 Vider le panier
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
      document.querySelectorAll('.pos-product').forEach(function(el) {
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
      var mode = document.getElementById('payment-mode').value;
      var items = ids.map(function(k) {
        return { medicament_id: cart[k].id, quantite: cart[k].qte, prix_unitaire: cart[k].prix };
      });
      fetch('/api/pos/vente', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: items, mode_paiement: mode })
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.ok) {
          alert('Vente enregistree - N ' + data.numero + ' - Total : ' + data.total.toLocaleString('fr-FR') + ' F');
          clearCart();
          location.reload();
        } else {
          alert('Erreur : ' + (data.error || 'inconnue'));
        }
      })
      .catch(function(e) { alert('Erreur reseau : ' + e.message); });
    }

    document.querySelectorAll('.pos-product[data-id]').forEach(function(el) {
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


@app.route('/api/pos/vente', methods=['POST'])
@login_required
def api_pos_vente():
    db = get_db()
    cur = db.cursor()
    data = request.get_json() or {}
    items = data.get('items', [])
    mode = data.get('mode_paiement') or 'especes'

    if not items:
        return jsonify({'ok': False, 'error': 'Panier vide'}), 400

    try:
        cur.execute("SELECT * FROM caissiers_sessions WHERE caissier_id=? AND statut='ouverte' ORDER BY id DESC LIMIT 1",
                    (current_user.id,))
        session_row = cur.fetchone()
        if not session_row:
            return jsonify({'ok': False, 'error': 'Aucune caisse ouverte'}), 400

        total = sum(it['quantite'] * it['prix_unitaire'] for it in items)
        numero = "V-" + datetime.now().strftime('%Y%m%d%H%M%S')

        cur.execute("""
            INSERT INTO ventes
            (numero, officine_id, caissier_id, montant_total, mode_paiement, statut, date_vente, created_at)
            VALUES (?,?,?,?,?,'payee',?,?)
        """, (numero, session_row['officine_id'], current_user.id, total, mode,
              datetime.now().isoformat(), datetime.now().isoformat()))
        vente_id = cur.lastrowid

        for it in items:
            cur.execute("""
                INSERT INTO vente_lignes
                (vente_id, medicament_id, quantite, prix_unitaire, montant)
                VALUES (?,?,?,?,?)
            """, (vente_id, it['medicament_id'], it['quantite'],
                  it['prix_unitaire'], it['quantite'] * it['prix_unitaire']))

            reste = it['quantite']
            cur.execute("""
                SELECT id, quantite FROM lots
                WHERE medicament_id=? AND officine_id=? AND statut='disponible' AND quantite > 0
                ORDER BY date_peremption ASC
            """, (it['medicament_id'], session_row['officine_id']))
            for lot in cur.fetchall():
                if reste <= 0: break
                prend = min(reste, lot['quantite'])
                cur.execute("UPDATE lots SET quantite=quantite-? WHERE id=?", (prend, lot['id']))
                reste -= prend

        db.commit()
        log_action(current_user.id, 'VENTE_POS', numero + ' - ' + str(total) + ' F - ' + mode, 'ventes', vente_id)
        return jsonify({'ok': True, 'numero': numero, 'total': total, 'vente_id': vente_id})
    except Exception as e:
        db.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/codes')
@login_required
def codes_liste():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, m.nom_commercial, m.dci
        FROM codes_produits c
        LEFT JOIN medicaments m ON m.id=c.medicament_id
        WHERE c.type='medicament'
        ORDER BY c.id DESC LIMIT 200
    """)
    codes = cur.fetchall()

    rows = ''.join(
        '<tr><td><strong>' + str(c["code_interne"]) + '</strong></td>'
        + '<td>' + str(c["nom_commercial"] or "—") + '</td>'
        + '<td><code>' + str(c["code_barre_ean13"] or "—") + '</code></td>'
        + '<td>' + str(c["dci"] or "—") + '</td>'
        + '<td>' + str((c["date_generation"] or "")[:16]) + '</td></tr>'
        for c in codes
    )

    content = '<h1>🎫 Codes produits auto-générés (' + str(len(codes)) + ')</h1>'
    content += '<div style="margin-bottom:16px;padding:14px;background:#f0f9ff;border-left:4px solid #06b6d4;border-radius:8px;font-size:13px">'
    content += 'ℹ️ Les codes sont générés <strong>automatiquement par trigger SQL</strong>.</div>'
    content += '<div class="card" style="padding:0;overflow:hidden">'
    content += '<table><thead><tr><th>Code interne</th><th>Médicament</th><th>Code-barre</th><th>DCI</th><th>Généré</th></tr></thead>'
    content += '<tbody>' + (rows or '<tr><td colspan="5" style="padding:40px;text-align:center;color:#9ca3af">Aucun code</td></tr>') + '</tbody></table></div>'
    return render_page(content, active='codes', page_title='Codes')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
