"""
🌾 AgriSénégal V2 — Application principale
Dashboard IA · Carte interactive · KPI agricoles · Mobile Money
Design vert forêt (inspiration kente) · Sénégal 2026
"""
from flask import Flask, render_template_string, request, redirect, flash, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'omega_agri_v2_2026_premium_secret'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

DB_PATH = "/app/data/agri.db"
UPLOAD_FOLDER = "/app/data/uploads"
PHOTO_FOLDER = "/app/data/photos"

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PHOTO_FOLDER'] = PHOTO_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# ==================== AUTH ====================
try:
    from auth import (init_auth, log_action, role_required, admin_required,
                      staff_required, producer_required)
    AUTH_OK = True
except Exception as e:
    print(f"[AUTH] ⚠️ {e}")
    AUTH_OK = False
    def role_required(*r):
        def d(f): return f
        return d
    admin_required = staff_required = producer_required = role_required()
    def log_action(*a, **k): pass

try:
    from flask_login import current_user, login_required
except ImportError:
    current_user = None
    def login_required(f): return f


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def fmt_fcfa(m):
    if not m:
        return "0 F"
    return f"{int(m):,} F".replace(",", " ")


def fmt_kg(kg):
    if not kg:
        return "0 kg"
    if kg >= 1000:
        return f"{kg/1000:.1f} t"
    return f"{int(kg)} kg"


def fmt_ha(ha):
    if not ha:
        return "0 ha"
    return f"{ha:.2f} ha"


# ==================== DESIGN VERT FORÊT ====================
HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AgriSénégal — {{ page_title or 'Agriculture connectée' }}</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}
body{background:#f0fdf4;color:#065f46;min-height:100vh}

.top-banner{background:linear-gradient(90deg,#065f46 0%,#10b981 50%,#34d399 100%);color:white;padding:10px 25px;font-size:0.82rem;display:flex;justify-content:space-between;align-items:center;font-weight:600;letter-spacing:0.3px;flex-wrap:wrap;gap:8px;position:relative}
.top-banner::after{content:'';position:absolute;bottom:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#fbbf24,#dc2626,#fbbf24)}
.top-banner i{color:#fef3c7}
.top-banner strong{color:#fef3c7;font-weight:800}
.top-banner .certif{background:rgba(254,243,199,0.2);padding:3px 10px;border-radius:20px;font-size:0.7rem;letter-spacing:0.5px;font-weight:700;color:#fef3c7}

.header{background:white;box-shadow:0 4px 24px rgba(6,95,70,0.08);padding:16px 30px;display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #10b981;flex-wrap:wrap;gap:15px}
.header .logo-section{display:flex;align-items:center;gap:15px}
.logo-icon{width:56px;height:56px;background:linear-gradient(135deg,#065f46,#10b981);border-radius:14px;display:flex;justify-content:center;align-items:center;color:white;font-size:1.7rem;box-shadow:0 8px 24px rgba(16,185,129,0.3)}
.header h1{font-size:1.55rem;color:#065f46;font-weight:900;line-height:1.05;letter-spacing:-0.5px}
.header h1 span{color:#10b981}
.header .subtitle{font-size:0.72rem;color:#64748b;margin-top:4px;letter-spacing:1px;text-transform:uppercase;font-weight:700}
.user-section{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.user-badge{display:flex;align-items:center;gap:10px;padding:8px 16px;background:#f0fdf4;border-radius:30px;border:1.5px solid #a7f3d0}
.user-badge .avatar{width:38px;height:38px;background:linear-gradient(135deg,#065f46,#10b981);border-radius:50%;display:flex;justify-content:center;align-items:center;color:white;font-weight:800;font-size:0.9rem}
.user-badge .info{display:flex;flex-direction:column;line-height:1.15}
.user-badge .name{font-weight:700;font-size:0.85rem;color:#065f46}
.user-badge .role{font-size:0.68rem;color:#10b981;text-transform:uppercase;font-weight:800;letter-spacing:0.5px}
.btn-logout{background:linear-gradient(135deg,#dc2626,#ef4444);color:white;padding:9px 16px;border-radius:10px;text-decoration:none;font-size:0.82rem;font-weight:700;transition:0.3s;box-shadow:0 4px 12px rgba(220,38,38,0.25)}
.btn-logout:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(220,38,38,0.35)}

.nav{background:white;padding:0 25px;display:flex;gap:2px;border-bottom:1px solid #a7f3d0;flex-wrap:wrap;box-shadow:0 2px 8px rgba(0,0,0,0.03)}
.nav a{padding:15px 18px;color:#475569;text-decoration:none;border-bottom:3px solid transparent;transition:0.3s;font-size:0.85rem;display:flex;align-items:center;gap:7px;font-weight:600}
.nav a:hover{color:#10b981;background:#f0fdf4}
.nav a.active{color:#065f46;border-bottom-color:#10b981;background:#f0fdf4}

.container{max-width:1500px;margin:28px auto;padding:0 25px}

.page-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:28px;flex-wrap:wrap;gap:15px}
.page-header h2{font-size:1.7rem;color:#065f46;font-weight:900;display:flex;align-items:center;gap:12px;letter-spacing:-0.5px}
.page-header h2 i{color:#10b981}
.page-header .page-subtitle{color:#64748b;font-size:0.88rem;margin-top:4px}

.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:20px;margin-bottom:28px}
.stat-card{background:white;border-radius:18px;padding:24px;position:relative;overflow:hidden;box-shadow:0 6px 20px rgba(6,95,70,0.06);transition:0.3s;border-left:5px solid #10b981}
.stat-card:hover{transform:translateY(-5px);box-shadow:0 12px 30px rgba(16,185,129,0.15)}
.stat-card .stat-icon{position:absolute;right:18px;top:18px;font-size:2.8rem;color:#10b981;opacity:0.12}
.stat-card .stat-value{font-size:2.2rem;font-weight:900;color:#065f46;line-height:1;letter-spacing:-1px}
.stat-card .stat-label{color:#64748b;font-size:0.75rem;text-transform:uppercase;font-weight:800;letter-spacing:1px;margin-top:10px}
.stat-card.gold{border-left-color:#f59e0b}.stat-card.gold .stat-icon{color:#f59e0b}
.stat-card.blue{border-left-color:#0ea5e9}.stat-card.blue .stat-icon{color:#0ea5e9}
.stat-card.rose{border-left-color:#dc2626}.stat-card.rose .stat-icon{color:#dc2626}
.stat-card.purple{border-left-color:#7c3aed}.stat-card.purple .stat-icon{color:#7c3aed}

.card{background:white;border-radius:18px;padding:28px;box-shadow:0 6px 20px rgba(6,95,70,0.06);margin-bottom:22px}
.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:12px;padding-bottom:18px;border-bottom:2px solid #f0fdf4}
.card-header h3{font-size:1.2rem;color:#065f46;font-weight:800;display:flex;align-items:center;gap:10px}
.card-header h3 i{color:#10b981}

.btn{padding:11px 20px;border:none;border-radius:10px;cursor:pointer;font-weight:700;display:inline-flex;align-items:center;gap:8px;text-decoration:none;transition:0.3s;font-size:0.85rem;letter-spacing:0.3px}
.btn-primary{background:linear-gradient(135deg,#065f46,#10b981);color:white;box-shadow:0 6px 16px rgba(16,185,129,0.3)}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 10px 24px rgba(16,185,129,0.4)}
.btn-success{background:linear-gradient(135deg,#16a34a,#22c55e);color:white}
.btn-warning{background:linear-gradient(135deg,#f59e0b,#fbbf24);color:white}
.btn-danger{background:linear-gradient(135deg,#dc2626,#ef4444);color:white}
.btn-info{background:linear-gradient(135deg,#0891b2,#06b6d4);color:white}
.btn-purple{background:linear-gradient(135deg,#7c3aed,#a855f7);color:white}
.btn-sm{padding:7px 13px;font-size:0.75rem}

.table-wrap{overflow-x:auto;border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:0.88rem}
th,td{padding:14px 16px;text-align:left;border-bottom:1px solid #f0fdf4}
th{background:linear-gradient(180deg,#f0fdf4,#d1fae5);color:#065f46;font-size:0.72rem;text-transform:uppercase;font-weight:800;letter-spacing:0.8px}
tbody tr{transition:0.2s}
tbody tr:hover{background:#f0fdf4}

.badge{padding:5px 12px;border-radius:20px;font-size:0.7rem;font-weight:800;display:inline-flex;align-items:center;gap:5px;letter-spacing:0.3px}
.badge-success{background:#d1fae5;color:#065f46}
.badge-warning{background:#fef3c7;color:#92400e}
.badge-danger{background:#fee2e2;color:#991b1b}
.badge-info{background:#dbeafe;color:#1e40af}
.badge-primary{background:#ecfdf5;color:#065f46}

.flash{padding:15px 20px;border-radius:12px;margin-bottom:18px;display:flex;align-items:center;gap:12px;font-size:0.9rem;font-weight:600}
.flash-success{background:#d1fae5;color:#065f46;border-left:5px solid #10b981}
.flash-danger{background:#fee2e2;color:#991b1b;border-left:5px solid #dc2626}
.flash-warning{background:#fef3c7;color:#92400e;border-left:5px solid #f59e0b}
.flash-info{background:#dbeafe;color:#1e40af;border-left:5px solid #3b82f6}

.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.form-group{margin-bottom:16px}
.form-group label{display:block;font-weight:800;color:#065f46;margin-bottom:8px;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.5px}
.form-group input,.form-group select,.form-group textarea{width:100%;padding:12px 15px;border:2px solid #f1f5f9;border-radius:11px;font-size:0.92rem;background:#f8fafc;transition:0.3s;font-family:inherit}
.form-group input:focus,.form-group select:focus,.form-group textarea:focus{outline:none;border-color:#10b981;background:white;box-shadow:0 0 0 4px rgba(16,185,129,0.1)}
.form-full{grid-column:1/-1}

.footer{background:linear-gradient(135deg,#065f46,#064e3b);color:white;padding:30px;margin-top:60px;text-align:center;font-size:0.85rem;position:relative}
.footer::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#fbbf24,#dc2626,#fbbf24)}
.footer strong{color:#a7f3d0;font-weight:800}
.footer .footer-sub{opacity:0.75;font-size:0.75rem;margin-top:8px}

.empty{text-align:center;padding:60px 20px;color:#94a3b8}
.empty i{font-size:4rem;color:#d1fae5;margin-bottom:18px}

.hero{background:linear-gradient(135deg,#065f46 0%,#10b981 50%,#34d399 100%);border-radius:24px;padding:50px;color:white;margin-bottom:30px;position:relative;overflow:hidden;box-shadow:0 15px 40px rgba(16,185,129,0.25)}
.hero::before{content:'';position:absolute;top:-80px;right:-80px;width:280px;height:280px;background:rgba(255,255,255,0.15);border-radius:50%}
.hero::after{content:'';position:absolute;bottom:-100px;left:-50px;width:220px;height:220px;background:rgba(255,255,255,0.1);border-radius:50%}
.hero h1{font-size:2.4rem;font-weight:900;margin-bottom:12px;position:relative;z-index:1;letter-spacing:-1px}
.hero h1 span{color:#fef3c7}
.hero p{font-size:1.05rem;opacity:0.95;position:relative;z-index:1;max-width:700px;line-height:1.5}
.hero .certifs{display:flex;gap:10px;margin-top:20px;position:relative;z-index:1;flex-wrap:wrap}
.hero .certifs span{background:rgba(255,255,255,0.15);padding:6px 14px;border-radius:20px;font-size:0.75rem;font-weight:800;letter-spacing:0.5px;backdrop-filter:blur(10px)}

.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:18px;margin-bottom:25px}
.kpi-card{background:white;border-radius:16px;padding:22px;box-shadow:0 6px 20px rgba(6,95,70,0.08);display:flex;align-items:center;gap:16px;transition:0.3s;border-top:4px solid #10b981}
.kpi-card:hover{transform:translateY(-3px);box-shadow:0 12px 30px rgba(16,185,129,0.15)}
.kpi-card .kpi-icon{width:56px;height:56px;border-radius:14px;display:flex;justify-content:center;align-items:center;font-size:1.6rem;color:white;flex-shrink:0}
.kpi-card .kpi-content{flex:1}
.kpi-card .kpi-label{font-size:0.78rem;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:0.5px}
.kpi-card .kpi-value{font-size:1.6rem;font-weight:900;color:#065f46;line-height:1.1;margin-top:4px}
.kpi-card .kpi-sub{font-size:0.75rem;color:#94a3b8;margin-top:4px}

#map{height:500px;border-radius:14px;box-shadow:0 6px 20px rgba(6,95,70,0.1)}

@media(max-width:768px){
  .form-grid{grid-template-columns:1fr}
  .header{flex-direction:column;align-items:flex-start}
  .stats{grid-template-columns:1fr 1fr}
  .container{padding:0 15px}
  .hero{padding:30px 20px}
  .hero h1{font-size:1.7rem}
  .top-banner{flex-direction:column;gap:5px;text-align:center}
}
</style>
</head>
<body>

<div class="top-banner">
  <span><i class="fas fa-seedling"></i> <strong>AGRISÉNÉGAL V2</strong> — Agriculture connectée · Sénégal</span>
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <span class="certif">IA Diagnostic</span>
    <span class="certif">NDVI Satellite</span>
    <span class="certif">Mobile Money</span>
    <span class="certif">UEMOA</span>
  </div>
</div>

<header class="header">
  <div class="logo-section">
    <div class="logo-icon"><i class="fas fa-seedling"></i></div>
    <div>
      <h1>AGRI<span>SÉNÉGAL</span></h1>
      <div class="subtitle"><i class="fas fa-satellite-dish"></i> Agriculture connectée 2026</div>
    </div>
  </div>
  <div class="user-section">
    {% if current_user and current_user.is_authenticated %}
    <div class="user-badge">
      <div class="avatar">{{ current_user.prenom[0] if current_user.prenom else 'U' }}{{ current_user.nom[0] if current_user.nom else '' }}</div>
      <div class="info">
        <span class="name">{{ current_user.prenom }} {{ current_user.nom }}</span>
        <span class="role">{{ current_user.role }}</span>
      </div>
    </div>
    <a href="/logout" class="btn-logout"><i class="fas fa-right-from-bracket"></i> Déconnexion</a>
    {% endif %}
  </div>
</header>

<nav class="nav">
  <a href="/" class="{{ 'active' if active=='dashboard' else '' }}"><i class="fas fa-chart-pie"></i> Dashboard</a>
  {% if current_user and current_user.is_authenticated %}
    <a href="/carte" class="{{ 'active' if active=='carte' else '' }}"><i class="fas fa-map-marked-alt"></i> Carte</a>
    <a href="/parcelles" class="{{ 'active' if active=='parcelles' else '' }}"><i class="fas fa-draw-polygon"></i> Parcelles</a>
    <a href="/cultures" class="{{ 'active' if active=='cultures' else '' }}"><i class="fas fa-seedling"></i> Cultures</a>
    <a href="/producteurs" class="{{ 'active' if active=='producteurs' else '' }}"><i class="fas fa-users"></i> Producteurs</a>
    <a href="/cooperatives" class="{{ 'active' if active=='cooperatives' else '' }}"><i class="fas fa-handshake"></i> Coopératives</a>
    {% if current_user.role in ['admin','direction','cooperative','technicien'] %}
    <a href="/diagnostic" class="{{ 'active' if active=='diagnostic' else '' }}"><i class="fas fa-robot"></i> IA Diagnostic</a>
    <a href="/meteo" class="{{ 'active' if active=='meteo' else '' }}"><i class="fas fa-cloud-sun"></i> Météo</a>
    {% endif %}
    {% if current_user.role in ['admin','direction','cooperative','producteur','finance'] %}
    <a href="/ventes" class="{{ 'active' if active=='ventes' else '' }}"><i class="fas fa-money-bill-wave"></i> Ventes</a>
    <a href="/finance" class="{{ 'active' if active=='finance' else '' }}"><i class="fas fa-coins"></i> Finance</a>
    {% endif %}
    {% if current_user.role in ['admin','direction','cooperative','producteur'] %}
    <a href="/elevage" class="{{ 'active' if active=='elevage' else '' }}"><i class="fas fa-cow"></i> Élevage</a>
    {% endif %}
    {% if current_user.role in ['admin','direction','finance'] %}
    <a href="/rapports" class="{{ 'active' if active=='rapports' else '' }}"><i class="fas fa-file-invoice"></i> Rapports</a>
    {% endif %}
    {% if current_user.role == 'admin' %}
    <a href="/utilisateurs" class="{{ 'active' if active=='utilisateurs' else '' }}"><i class="fas fa-user-shield"></i> Utilisateurs</a>
    <a href="/audit" class="{{ 'active' if active=='audit' else '' }}"><i class="fas fa-history"></i> Audit</a>
    {% endif %}
  {% endif %}
</nav>

<div class="container">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}{% for cat, msg in messages %}
      <div class="flash flash-{{ cat }}"><i class="fas fa-circle-info"></i> {{ msg }}</div>
    {% endfor %}{% endif %}
  {% endwith %}

  {% block content %}{% endblock %}
</div>

<footer class="footer">
  <div>&copy; 2026 <strong>AGRISÉNÉGAL V2</strong> — Tous droits réservés</div>
  <div class="footer-sub">
    <i class="fas fa-code"></i> Développé par <strong>OMEGA INFORMATIQUE</strong> · Dakar, Sénégal · UEMOA
  </div>
</footer>

</body>
</html>
"""


def render_page(content, active='dashboard', page_title='AgriSénégal'):
    page = HTML_BASE.replace("{% block content %}{% endblock %}", content)
    return render_template_string(page, active=active, page_title=page_title,
                                  current_user=current_user)


# ==================== HEALTHCHECK ====================
@app.route('/health')
def health():
    return jsonify(status='ok', service='agri-v2', version='2.0',
                   timestamp=datetime.now().isoformat())


# ==================== DASHBOARD ====================
@app.route('/')
def index():
    if not (current_user and current_user.is_authenticated):
        return redirect('/login')

    conn = get_db()
    c = conn.cursor()

    try:
        # ============ KPI 1 : Producteurs actifs ============
        c.execute("SELECT COUNT(*) FROM producteurs WHERE actif=1")
        nb_producteurs = c.fetchone()[0] or 0

        # ============ KPI 2 : Parcelles ============
        c.execute("SELECT COUNT(*), COALESCE(SUM(superficie_ha), 0) FROM parcelles WHERE actif=1")
        row = c.fetchone()
        nb_parcelles = row[0] or 0
        superficie_totale = row[1] or 0

        # ============ KPI 3 : Production totale ============
        c.execute("SELECT COALESCE(SUM(quantite_kg), 0) FROM recoltes")
        production_totale = c.fetchone()[0] or 0

        # ============ KPI 4 : CA ventes mois ============
        mois = datetime.now().strftime('%Y-%m')
        c.execute("""SELECT COALESCE(SUM(montant_total), 0) FROM ventes
                     WHERE strftime('%Y-%m', date_vente)=?""", (mois,))
        ca_mois = c.fetchone()[0] or 0

        # ============ KPI 5 : Alertes actives ============
        c.execute("SELECT COUNT(*) FROM alertes_agro WHERE statut='Active'")
        nb_alertes = c.fetchone()[0] or 0

        # ============ KPI 6 : Troupeaux ============
        c.execute("SELECT COUNT(*), COALESCE(SUM(effectif_total), 0) FROM troupeaux WHERE actif=1")
        row = c.fetchone()
        nb_troupeaux = row[0] or 0
        effectif_animaux = row[1] or 0

        # ============ KPI 7 : Crédits en cours ============
        c.execute("""SELECT COUNT(*), COALESCE(SUM(montant_accorde), 0) FROM credits
                     WHERE statut IN ('Décaissé', 'En analyse')""")
        row = c.fetchone()
        nb_credits = row[0] or 0
        montant_credits = row[1] or 0

        # ============ KPI 8 : Mobile Money ============
        c.execute("""SELECT COUNT(*), COALESCE(SUM(montant), 0) FROM transactions_mobile
                     WHERE strftime('%Y-%m', date_transaction)=? AND statut='Réussi'""", (mois,))
        row = c.fetchone()
        nb_transactions = row[0] or 0
        montant_transactions = row[1] or 0

        # ============ Top 5 cultures ============
        c.execute("""SELECT c.nom, c.icone, c.nom_wolof,
                            COUNT(cp.id) AS nb_parcelles,
                            COALESCE(SUM(cp.superficie_ha), 0) AS superficie,
                            COALESCE(SUM(r.quantite_kg), 0) AS production
                     FROM cultures c
                     LEFT JOIN cultures_parcelles cp ON cp.culture_id = c.id
                     LEFT JOIN recoltes r ON r.culture_id = c.id
                     WHERE c.actif=1
                     GROUP BY c.id
                     HAVING nb_parcelles > 0
                     ORDER BY production DESC LIMIT 5""")
        top_cultures = c.fetchall()

        # ============ Dernières récoltes ============
        c.execute("""SELECT r.*, c.nom AS culture_nom, c.icone,
                            p.nom AS producteur_nom, p.prenom AS producteur_prenom
                     FROM recoltes r
                     LEFT JOIN cultures c ON r.culture_id = c.id
                     LEFT JOIN producteurs p ON r.producteur_id = p.id
                     ORDER BY r.date_recolte DESC LIMIT 8""")
        dernieres_recoltes = c.fetchall()

        # ============ Alertes récentes ============
        c.execute("""SELECT a.*, p.nom AS producteur_nom
                     FROM alertes_agro a
                     LEFT JOIN producteurs p ON a.producteur_id = p.id
                     WHERE a.statut='Active'
                     ORDER BY a.created_at DESC LIMIT 5""")
        alertes = c.fetchall()

        # ============ Dernières transactions MM ============
        c.execute("""SELECT t.*, p.nom AS producteur_nom, p.prenom AS producteur_prenom
                     FROM transactions_mobile t
                     LEFT JOIN producteurs p ON t.producteur_id = p.id
                     WHERE t.statut='Réussi'
                     ORDER BY t.date_transaction DESC LIMIT 6""")
        transactions = c.fetchall()

        # ============ Activité récente ============
        c.execute("""SELECT a.*, u.nom AS user_nom, u.prenom AS user_prenom
                     FROM audit_log a
                     LEFT JOIN utilisateurs u ON a.user_id = u.id
                     ORDER BY a.created_at DESC LIMIT 6""")
        activite = c.fetchall()

        conn.close()

        now = datetime.now()

        content = f"""
        <div class="hero">
          <h1>Bonjour <span>{current_user.prenom}</span> 🌾</h1>
          <p>Plateforme agricole connectée du Sénégal — IA diagnostic · Satellite NDVI · Mobile Money · Mobile Money · Météo hyperlocale</p>
          <div class="certifs">
            <span>🛰️ Sentinel-2</span>
            <span>🤖 IA CNN</span>
            <span>📱 Wave · OM · Free</span>
            <span>🇸🇳 14 régions</span>
          </div>
        </div>

        <div class="kpi-grid">
          <div class="kpi-card" style="border-top-color:#10b981">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#065f46,#10b981)">
              <i class="fas fa-users"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Producteurs</div>
              <div class="kpi-value">{nb_producteurs}</div>
              <div class="kpi-sub">Actifs enregistrés</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#059669">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#047857,#10b981)">
              <i class="fas fa-draw-polygon"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Parcelles</div>
              <div class="kpi-value">{nb_parcelles}</div>
              <div class="kpi-sub">{fmt_ha(superficie_totale)} cultivés</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#f59e0b">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#d97706,#fbbf24)">
              <i class="fas fa-wheat-awn"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Production totale</div>
              <div class="kpi-value">{fmt_kg(production_totale)}</div>
              <div class="kpi-sub">Toutes récoltes</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#16a34a">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#15803d,#22c55e)">
              <i class="fas fa-money-bill-wave"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">CA du mois</div>
              <div class="kpi-value" style="font-size:1.3rem">{fmt_fcfa(ca_mois)}</div>
              <div class="kpi-sub">{mois}</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#0ea5e9">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#0284c7,#38bdf8)">
              <i class="fas fa-mobile-screen"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Mobile Money</div>
              <div class="kpi-value" style="font-size:1.3rem">{fmt_fcfa(montant_transactions)}</div>
              <div class="kpi-sub">{nb_transactions} transactions</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#7c3aed">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#6d28d9,#a855f7)">
              <i class="fas fa-cow"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Élevage</div>
              <div class="kpi-value">{nb_troupeaux}</div>
              <div class="kpi-sub">{effectif_animaux} animaux</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#dc2626">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#dc2626,#ef4444)">
              <i class="fas fa-triangle-exclamation"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Alertes actives</div>
              <div class="kpi-value">{nb_alertes}</div>
              <div class="kpi-sub">À traiter</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#0891b2">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#0e7490,#06b6d4)">
              <i class="fas fa-hand-holding-dollar"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Crédits en cours</div>
              <div class="kpi-value" style="font-size:1.3rem">{fmt_fcfa(montant_credits)}</div>
              <div class="kpi-sub">{nb_credits} dossiers</div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-map-marked-alt"></i> Carte des parcelles</h3>
            <a href="/carte" class="btn btn-primary btn-sm"><i class="fas fa-expand"></i> Plein écran</a>
          </div>
          <div id="map-home" style="height:350px;border-radius:14px"></div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="card">
            <div class="card-header"><h3><i class="fas fa-fire"></i> Top 5 cultures</h3></div>
        """
        for tc in top_cultures:
            content += f"""
            <div style="padding:14px 0;border-bottom:1px dashed #f0fdf4">
              <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
                <div style="width:36px;height:36px;background:linear-gradient(135deg,#065f46,#10b981);border-radius:10px;display:flex;align-items:center;justify-content:center;color:white">
                  <i class="fas {tc['icone'] or 'fa-seedling'}"></i>
                </div>
                <div style="flex:1">
                  <div style="font-weight:800">{tc['nom']}</div>
                  <div style="font-size:0.72rem;color:#94a3b8">{tc['nb_parcelles']} parcelles · {fmt_ha(tc['superficie'])}</div>
                </div>
                <div style="text-align:right">
                  <div style="font-weight:900;color:#10b981">{fmt_kg(tc['production'])}</div>
                </div>
              </div>
            </div>"""
        if not top_cultures:
            content += '<div class="empty" style="padding:20px">Aucune donnée</div>'
        content += "</div>"

        content += """
          <div class="card">
            <div class="card-header"><h3><i class="fas fa-mobile-screen"></i> Transactions Mobile Money</h3></div>
        """
        for t in transactions:
            icon_color = '#10b981'
            if t['fournisseur'] == 'Orange Money': icon_color = '#f97316'
            elif t['fournisseur'] == 'Free Money': icon_color = '#dc2626'

            content += f"""
            <div style="padding:10px 0;border-bottom:1px dashed #f0fdf4;display:flex;justify-content:space-between;align-items:center">
              <div>
                <div style="font-weight:700;font-size:0.9rem">{t['producteur_prenom'] or ''} {t['producteur_nom'] or ''}</div>
                <div style="font-size:0.72rem;color:#94a3b8">
                  <span style="background:{icon_color}20;color:{icon_color};padding:2px 8px;border-radius:10px;font-weight:700">{t['fournisseur']}</span>
                  · {t['type_transaction']}
                </div>
              </div>
              <div style="text-align:right">
                <div style="font-weight:900;color:#10b981">+{fmt_fcfa(t['montant'])}</div>
              </div>
            </div>"""
        if not transactions:
            content += '<div class="empty" style="padding:20px">Aucune transaction</div>'
        content += "</div></div>"

        # Dernières récoltes
        content += """
        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-wheat-awn"></i> Dernières récoltes</h3>
            <a href="/parcelles" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Voir tout</a>
          </div>
          <div class="table-wrap"><table>
            <thead><tr><th>Date</th><th>Culture</th><th>Producteur</th>
                       <th>Quantité</th><th>Qualité</th><th>Destination</th></tr></thead>
            <tbody>
        """
        for r in dernieres_recoltes:
            badge_q = 'badge-success'
            if r['qualite'] == 'Moyenne': badge_q = 'badge-warning'
            content += f"""
            <tr>
              <td><strong>{r['date_recolte']}</strong></td>
              <td>
                <div style="display:flex;align-items:center;gap:8px">
                  <i class="fas {r['icone'] or 'fa-seedling'}" style="color:#10b981"></i>
                  <span>{r['culture_nom'] or '-'}</span>
                </div>
              </td>
              <td>{r['producteur_prenom'] or ''} {r['producteur_nom'] or ''}</td>
              <td><strong>{fmt_kg(r['quantite_kg'])}</strong></td>
              <td><span class="badge {badge_q}">{r['qualite']}</span></td>
              <td><small>{r['destination']}</small></td>
            </tr>"""
        if not dernieres_recoltes:
            content += '<tr><td colspan="6" class="empty">Aucune récolte</td></tr>'
        content += "</tbody></table></div></div>"

        # Alertes
        if alertes:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-triangle-exclamation" style="color:#dc2626"></i> Alertes agro actives</h3></div>"""
            for a in alertes:
                badge = 'badge-danger'
                if a['gravite'] == 'Warning': badge = 'badge-warning'
                elif a['gravite'] == 'Info': badge = 'badge-info'
                content += f"""
                <div style="padding:12px 0;border-bottom:1px dashed #f0fdf4">
                  <div style="display:flex;justify-content:space-between;margin-bottom:6px;align-items:center">
                    <strong style="font-size:0.95rem">{a['titre']}</strong>
                    <span class="badge {badge}">{a['gravite']}</span>
                  </div>
                  <div style="font-size:0.82rem;color:#64748b">{a['message'] or ''}</div>
                  {f'<div style="font-size:0.78rem;color:#10b981;margin-top:6px"><i class="fas fa-lightbulb"></i> {a["action_recommandee"]}</div>' if a['action_recommandee'] else ''}
                </div>"""
            content += "</div>"

        # Activité récente
        if activite:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-history"></i> Activité récente</h3></div>"""
            for a in activite:
                content += f"""
                <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px dashed #f0fdf4">
                  <div>
                    <strong style="font-size:0.85rem">{a['user_prenom'] or '?'} {a['user_nom'] or ''}</strong>
                    <div style="font-size:0.8rem;color:#475569">{a['action']} — {a['details'] or ''}</div>
                  </div>
                  <small style="color:#94a3b8">{a['created_at'][:16]}</small>
                </div>"""
            content += "</div>"

        # Script carte Leaflet
        content += """
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
        document.addEventListener('DOMContentLoaded', () => {
          const map = L.map('map-home').setView([14.4974, -14.4524], 7);
          L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap'
          }).addTo(map);

          // Charger les parcelles
          fetch('/api/parcelles/geojson')
            .then(r => r.json())
            .then(data => {
              if (data.features) {
                L.geoJSON(data, {
                  style: { color: '#10b981', weight: 2, opacity: 0.8, fillOpacity: 0.3 },
                  onEachFeature: (feature, layer) => {
                    const p = feature.properties;
                    layer.bindPopup(`<strong>${p.nom}</strong><br>${p.culture}<br>${p.superficie} ha<br>${p.producteur}`);
                  }
                }).addTo(map);
              }
            })
            .catch(e => console.log('Erreur carte:', e));
        });
        </script>
        """

        return render_page(content, active='dashboard', page_title='Dashboard Agri')

    except Exception as e:
        import traceback
        traceback.print_exc()
        conn.close()
        flash(f"Erreur dashboard : {e}", "danger")
        return redirect('/login')


# ==================== API GeoJSON PARCELLES ====================
@app.route('/api/parcelles/geojson')
def api_parcelles_geojson():
    if not (current_user and current_user.is_authenticated):
        return jsonify({"type": "FeatureCollection", "features": []})

    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT pa.*, cu.nom AS culture_nom, cu.icone,
                        p.nom AS producteur_nom, p.prenom AS producteur_prenom
                 FROM parcelles pa
                 LEFT JOIN cultures_parcelles cp ON cp.parcelle_id = pa.id
                 LEFT JOIN cultures cu ON cp.culture_id = cu.id
                 LEFT JOIN producteurs p ON pa.producteur_id = p.id
                 WHERE pa.actif=1 AND pa.latitude IS NOT NULL""")
    parcelles = c.fetchall()
    conn.close()

    features = []
    for p in parcelles:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [p['longitude'], p['latitude']]
            },
            "properties": {
                "id": p['id'],
                "code": p['code'],
                "nom": p['nom'] or p['code'],
                "culture": p['culture_nom'] or 'Non cultivée',
                "superficie": p['superficie_ha'],
                "producteur": f"{p['producteur_prenom'] or ''} {p['producteur_nom'] or ''}".strip(),
                "icone": p['icone'] or 'fa-seedling'
            }
        })

    return jsonify({"type": "FeatureCollection", "features": features})


# ==================== ROUTE /carte (plein écran) ====================
@app.route('/carte')
def carte():
    if not (current_user and current_user.is_authenticated):
        return redirect('/login')

    content = """
    <div class="page-header">
      <div><h2><i class="fas fa-map-marked-alt"></i> Carte des parcelles</h2>
        <div class="page-subtitle">Visualisation géographique · Sénégal</div></div>
    </div>

    <div class="card" style="padding:0;overflow:hidden">
      <div id="map-full" style="height:calc(100vh - 350px);min-height:500px"></div>
    </div>

    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
    document.addEventListener('DOMContentLoaded', () => {
      const map = L.map('map-full').setView([14.4974, -14.4524], 7);

      // Plusieurs fonds de carte
      const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap'
      }).addTo(map);

      const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: '© Esri'
      });

      L.control.layers({
        "Plan": osm,
        "Satellite": satellite
      }).addTo(map);

      // Charger les parcelles
      fetch('/api/parcelles/geojson')
        .then(r => r.json())
        .then(data => {
          if (data.features) {
            L.geoJSON(data, {
              style: (feature) => ({
                color: '#10b981',
                weight: 2,
                opacity: 0.8,
                fillOpacity: 0.3
              }),
              pointToLayer: (feature, latlng) => {
                return L.circleMarker(latlng, {
                  radius: 8,
                  fillColor: '#10b981',
                  color: '#065f46',
                  weight: 2,
                  opacity: 1,
                  fillOpacity: 0.7
                });
              },
              onEachFeature: (feature, layer) => {
                const p = feature.properties;
                layer.bindPopup(`
                  <div style="font-family:system-ui;min-width:200px">
                    <h4 style="margin:0 0 8px;color:#065f46">${p.nom}</h4>
                    <div style="font-size:0.85rem;line-height:1.6">
                      <strong>Code:</strong> ${p.code}<br>
                      <strong>Culture:</strong> ${p.culture}<br>
                      <strong>Superficie:</strong> ${p.superficie} ha<br>
                      <strong>Producteur:</strong> ${p.producteur}
                    </div>
                  </div>
                `);
              }
            }).addTo(map);
          }
        })
        .catch(e => console.error(e));
    });
    </script>
    """
    return render_page(content, active='carte', page_title='Carte interactive')


# ==================== INIT MODULES ====================
try:
    from crud import init_crud
    init_crud(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[CRUD] ✅ Module CRUD enregistré")
except Exception as e:
    print(f"[CRUD] ⚠️ {e}")

try:
    from agri_logic import init_agri
    init_agri(app, get_db=get_db, render_page=render_page,
              log_action=log_action, UPLOAD_FOLDER=UPLOAD_FOLDER)
    print("[AGRI] ✅ Module logique enregistré")
except Exception as e:
    print(f"[AGRI] ⚠️ {e}")

try:
    from agri_ia import init_agri_ia
    init_agri_ia(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[IA] ✅ Module IA enregistré")
except Exception as e:
    print(f"[IA] ⚠️ {e}")

try:
    from agri_iot import init_agri_iot
    init_agri_iot(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[IOT] ✅ Module IoT enregistré")
except Exception as e:
    print(f"[IOT] ⚠️ {e}")

try:
    from agri_finance import init_agri_finance
    init_agri_finance(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[FINANCE] ✅ Module Finance enregistré")
except Exception as e:
    print(f"[FINANCE] ⚠️ {e}")

try:
    from rapports import init_rapports
    init_rapports(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[RAPPORTS] ✅ Module rapports enregistré")
except Exception as e:
    print(f"[RAPPORTS] ⚠️ {e}")

try:
    from portail import init_portail
    init_portail(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[PORTAIL] ✅ Module portail enregistré")
except Exception as e:
    print(f"[PORTAIL] ⚠️ {e}")


# ==================== INIT AUTH (dernier) ====================
if AUTH_OK:
    try:
        init_auth(app)
    except Exception as e:
        print(f"[AUTH] ⚠️ {e}")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
