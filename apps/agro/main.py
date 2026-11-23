"""
🌾 Omega Agro-Industrie — Application principale
Dashboard SM10 AGRO · Bambali, Sénégal
Projet Sadio Mané — 11,4 Milliards FCFA
"""
from flask import Flask, render_template_string, request, redirect, flash, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'omega_agro_2026_sm10_sadio_mane_secret'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

DB_PATH = "/app/data/agro.db"

try:
    from auth import (init_auth, log_action, admin_required, direction_required,
                      staff_required, role_required)
    AUTH_OK = True
except Exception as e:
    print(f"[AUTH] ⚠️ {e}")
    AUTH_OK = False
    def admin_required(f): return f
    direction_required = staff_required = admin_required
    def role_required(*r):
        def d(f): return f
        return d
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


def fmt_date(d):
    if not d:
        return "-"
    return d[:10] if len(d) >= 10 else d


# ==================== DESIGN VERT AGRO ====================
HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Omega Agro — {{ page_title or 'SM10 AGRO' }}</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}
body{background:#f0fdf4;color:#065f46;min-height:100vh}

.top-banner{background:linear-gradient(90deg,#065f46 0%,#10b981 50%,#fbbf24 100%);color:white;padding:10px 25px;font-size:0.82rem;display:flex;justify-content:space-between;align-items:center;font-weight:600;letter-spacing:0.3px;flex-wrap:wrap;gap:8px}
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
.badge-gold{background:linear-gradient(135deg,#fbbf24,#f59e0b);color:white}
.badge-role-admin{background:linear-gradient(135deg,#dc2626,#ef4444);color:white}
.badge-role-directeur{background:linear-gradient(135deg,#7c3aed,#a855f7);color:white}
.badge-role-production{background:linear-gradient(135deg,#065f46,#10b981);color:white}
.badge-role-qualite{background:linear-gradient(135deg,#0ea5e9,#06b6d4);color:white}
.badge-role-export{background:linear-gradient(135deg,#f59e0b,#fbbf24);color:white}
.badge-role-formation{background:linear-gradient(135deg,#8b5cf6,#a855f7);color:white}
.badge-role-operateur{background:linear-gradient(135deg,#64748b,#94a3b8);color:white}

.flash{padding:15px 20px;border-radius:12px;margin-bottom:18px;display:flex;align-items:center;gap:12px;font-size:0.9rem;font-weight:600}
.flash-success{background:#d1fae5;color:#065f46;border-left:5px solid #10b981}
.flash-danger{background:#fee2e2;color:#991b1b;border-left:5px solid #dc2626}
.flash-warning{background:#fef3c7;color:#92400e;border-left:5px solid #f59e0b}
.flash-info{background:#dbeafe;color:#1e40af;border-left:5px solid #3b82f6}

.footer{background:linear-gradient(135deg,#065f46,#064e3b);color:white;padding:30px;margin-top:60px;text-align:center;font-size:0.85rem;position:relative}
.footer::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#fbbf24,#dc2626,#fbbf24)}
.footer strong{color:#a7f3d0;font-weight:800}
.footer .footer-sub{opacity:0.75;font-size:0.75rem;margin-top:8px}

.empty{text-align:center;padding:60px 20px;color:#94a3b8}
.empty i{font-size:4rem;color:#d1fae5;margin-bottom:18px}

.hero{background:linear-gradient(135deg,#065f46 0%,#10b981 50%,#34d399 100%);border-radius:24px;padding:50px;color:white;margin-bottom:30px;position:relative;overflow:hidden;box-shadow:0 15px 40px rgba(16,185,129,0.25)}
.hero::before{content:'';position:absolute;top:-80px;right:-80px;width:280px;height:280px;background:rgba(254,243,199,0.15);border-radius:50%}
.hero::after{content:'';position:absolute;bottom:-100px;left:-50px;width:220px;height:220px;background:rgba(254,243,199,0.1);border-radius:50%}
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

@media(max-width:768px){
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
  <span><i class="fas fa-seedling"></i> <strong>OMEGA AGRO-INDUSTRIE</strong> — Projet SM10 AGRO · Sadio Mané</span>
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <span class="certif">HACCP</span>
    <span class="certif">ISO 22000</span>
    <span class="certif">UE Export</span>
    <span class="certif">APIX 5 ans</span>
  </div>
</div>

<header class="header">
  <div class="logo-section">
    <div class="logo-icon"><i class="fas fa-seedling"></i></div>
    <div>
      <h1>OMEGA <span>AGRO</span></h1>
      <div class="subtitle"><i class="fas fa-industry"></i> Transformation mangue & cajou · Bambali</div>
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
    <a href="/producteurs" class="{{ 'active' if active=='producteurs' else '' }}"><i class="fas fa-users"></i> Producteurs</a>
    <a href="/produits" class="{{ 'active' if active=='produits' else '' }}"><i class="fas fa-box"></i> Produits</a>
    {% if current_user.role in ['admin','directeur','production'] %}
    <a href="/production" class="{{ 'active' if active=='production' else '' }}"><i class="fas fa-industry"></i> Production</a>
    {% endif %}
    {% if current_user.role in ['admin','directeur','qualite'] %}
    <a href="/qualite" class="{{ 'active' if active=='qualite' else '' }}"><i class="fas fa-flask"></i> Qualité</a>
    {% endif %}
    {% if current_user.role in ['admin','directeur','export'] %}
    <a href="/exports" class="{{ 'active' if active=='exports' else '' }}"><i class="fas fa-ship"></i> Exports UE</a>
    {% endif %}
    <a href="/tracabilite" class="{{ 'active' if active=='tracabilite' else '' }}"><i class="fas fa-qrcode"></i> Traçabilité</a>
    {% if current_user.role in ['admin','directeur','formation'] %}
    <a href="/formations" class="{{ 'active' if active=='formations' else '' }}"><i class="fas fa-graduation-cap"></i> Formations</a>
    {% endif %}
    {% if current_user.role in ['admin','directeur'] %}
    <a href="/rapports" class="{{ 'active' if active=='rapports' else '' }}"><i class="fas fa-file-invoice"></i> Rapports</a>
    {% endif %}
    {% if current_user.role == 'admin' %}
    <a href="/utilisateurs" class="{{ 'active' if active=='utilisateurs' else '' }}"><i class="fas fa-user-shield"></i> Utilisateurs</a>
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
  <div>&copy; 2026 <strong>OMEGA AGRO-INDUSTRIE</strong> — Projet SM10 AGRO · Sadio Mané</div>
  <div class="footer-sub">
    <i class="fas fa-code"></i> Développé par <strong>OMEGA INFORMATIQUE</strong> · Dakar, Sénégal · UEMOA · APIX
  </div>
</footer>

</body>
</html>
"""


def render_page(content, active='dashboard', page_title='Omega Agro'):
    page = HTML_BASE.replace("{% block content %}{% endblock %}", content)
    return render_template_string(page, active=active, page_title=page_title,
                                  current_user=current_user)


# ==================== HEALTHCHECK ====================
@app.route('/health')
def health():
    return jsonify(status='ok', service='agro-industrie',
                   project='SM10 AGRO', version='1.0',
                   timestamp=datetime.now().isoformat())


# ==================== DASHBOARD ====================
@app.route('/')
def index():
    if not (current_user and current_user.is_authenticated):
        return redirect('/login')

    conn = get_db()
    c = conn.cursor()

    try:
        # KPI 1 : Producteurs
        c.execute("SELECT COUNT(*) FROM producteurs WHERE actif=1")
        nb_producteurs = c.fetchone()[0] or 0

        # KPI 2 : Produits finis
        c.execute("SELECT COUNT(*) FROM produits_finis WHERE actif=1")
        nb_produits = c.fetchone()[0] or 0

        # KPI 3 : Stock total
        c.execute("SELECT COALESCE(SUM(quantite_kg), 0) FROM stocks_produits")
        stock_total = c.fetchone()[0] or 0

        # KPI 4 : OF en cours
        c.execute("SELECT COUNT(*) FROM ordres_fabrication WHERE statut='En cours'")
        of_en_cours = c.fetchone()[0] or 0

        # KPI 5 : Exports en cours
        c.execute("SELECT COUNT(*) FROM exports WHERE statut IN ('En préparation', 'En transit')")
        exports_en_cours = c.fetchone()[0] or 0

        # KPI 6 : Chiffre d'affaires potentiel export
        c.execute("SELECT COALESCE(SUM(montant_total), 0) FROM exports WHERE statut='Livré'")
        ca_export = c.fetchone()[0] or 0

        # KPI 7 : Certifications actives
        c.execute("SELECT COUNT(*) FROM certifications WHERE statut='Active'")
        nb_certifs = c.fetchone()[0] or 0

        # KPI 8 : Non-conformités ouvertes
        c.execute("SELECT COUNT(*) FROM non_conformites WHERE statut='Ouverte'")
        nc_ouvertes = c.fetchone()[0] or 0

        # Production par produit
        c.execute("""SELECT p.nom, p.categorie, p.code,
                            COALESCE(SUM(s.quantite_kg), 0) AS stock,
                            (SELECT COUNT(*) FROM ordres_fabrication WHERE produit_fini_id=p.id) AS nb_of
                     FROM produits_finis p
                     LEFT JOIN stocks_produits s ON s.produit_id = p.id
                     WHERE p.actif=1
                     GROUP BY p.id
                     ORDER BY stock DESC LIMIT 8""")
        production_par_produit = c.fetchall()

        # Derniers ordres de fabrication
        c.execute("""SELECT of.*, p.nom AS produit_nom, p.code AS produit_code
                     FROM ordres_fabrication of
                     LEFT JOIN produits_finis p ON of.produit_fini_id = p.id
                     ORDER BY of.date_debut DESC LIMIT 8""")
        derniers_of = c.fetchall()

        # Derniers exports
        c.execute("""SELECT e.*, c.nom AS client_nom, c.pays AS client_pays,
                            p.nom AS produit_nom
                     FROM exports e
                     LEFT JOIN clients_b2b c ON e.client_id = c.id
                     LEFT JOIN produits_finis p ON e.produit_id = p.id
                     ORDER BY e.date_commande DESC LIMIT 5""")
        derniers_exports = c.fetchall()

        # Alertes récentes
        c.execute("""SELECT * FROM alertes WHERE statut='Active'
                     ORDER BY created_at DESC LIMIT 5""")
        alertes = c.fetchall()

        # Top producteurs
        c.execute("""SELECT p.nom, p.prenom, p.code, p.village,
                            COUNT(r.id) AS nb_recoltes,
                            COALESCE(SUM(r.quantite_kg), 0) AS total_kg
                     FROM producteurs p
                     LEFT JOIN recoltes r ON r.producteur_id = p.id
                     WHERE p.actif=1
                     GROUP BY p.id
                     ORDER BY total_kg DESC LIMIT 5""")
        top_producteurs = c.fetchall()

        # Activité récente
        c.execute("""SELECT a.*, u.nom AS user_nom, u.prenom AS user_prenom
                     FROM audit_log a
                     LEFT JOIN utilisateurs u ON a.user_id = u.id
                     ORDER BY a.created_at DESC LIMIT 6""")
        activite = c.fetchall()

        conn.close()

        content = f"""
        <div class="hero">
          <h1>Projet <span>SM10 AGRO</span> 🌾</h1>
          <p>Plateforme digitale de transformation agro-industrielle — Mangue · Noix de cajou · Fruits & légumes · Export UE</p>
          <div class="certifs">
            <span>💰 11,4 Milliards FCFA</span>
            <span>🇸🇳 Bambali, Sénégal</span>
            <span>🏭 2 usines</span>
            <span>🌍 Export UE</span>
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
              <div class="kpi-sub">Partenaires actifs</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#f59e0b">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#d97706,#fbbf24)">
              <i class="fas fa-box"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Produits finis</div>
              <div class="kpi-value">{nb_produits}</div>
              <div class="kpi-sub">Références actives</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#0ea5e9">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#0284c7,#38bdf8)">
              <i class="fas fa-warehouse"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Stock total</div>
              <div class="kpi-value">{fmt_kg(stock_total)}</div>
              <div class="kpi-sub">Tous produits</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#7c3aed">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#6d28d9,#a855f7)">
              <i class="fas fa-industry"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">OF en cours</div>
              <div class="kpi-value">{of_en_cours}</div>
              <div class="kpi-sub">Ordres fabrication</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#16a34a">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#15803d,#22c55e)">
              <i class="fas fa-ship"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Exports en cours</div>
              <div class="kpi-value">{exports_en_cours}</div>
              <div class="kpi-sub">Vers l'UE</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#fbbf24">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#d97706,#fbbf24)">
              <i class="fas fa-euro-sign"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">CA Export (livré)</div>
              <div class="kpi-value" style="font-size:1.3rem">{fmt_fcfa(ca_export)}</div>
              <div class="kpi-sub">Cumul historique</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#dc2626">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#dc2626,#ef4444)">
              <i class="fas fa-certificate"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Certifications</div>
              <div class="kpi-value">{nb_certifs}</div>
              <div class="kpi-sub">HACCP · ISO 22000</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#f97316">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#ea580c,#fb923c)">
              <i class="fas fa-triangle-exclamation"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Non-conformités</div>
              <div class="kpi-value">{nc_ouvertes}</div>
              <div class="kpi-sub">À traiter</div>
            </div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="card">
            <div class="card-header">
              <h3><i class="fas fa-flask"></i> Production par produit</h3>
              <a href="/produits" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Voir</a>
            </div>
        """
        max_stock = max([p['stock'] for p in production_par_produit], default=1)
        for p in production_par_produit:
            pct = (p['stock'] / max_stock * 100) if max_stock else 0
            content += f"""
            <div style="margin-bottom:14px">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="font-weight:700;font-size:0.85rem">{p['nom']}</span>
                <strong style="color:#065f46">{fmt_kg(p['stock'])}</strong>
              </div>
              <div style="background:#f0fdf4;border-radius:6px;height:8px;overflow:hidden">
                <div style="background:linear-gradient(90deg,#065f46,#22d3ee);height:100%;width:{pct}%"></div>
              </div>
            </div>"""
        if not production_par_produit:
            content += '<div class="empty" style="padding:20px">Aucune donnée</div>'
        content += "</div>"

        content += """
          <div class="card">
            <div class="card-header">
              <h3><i class="fas fa-trophy"></i> Top producteurs</h3>
              <a href="/producteurs" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Voir</a>
            </div>
        """
        for tp in top_producteurs:
            content += f"""
            <div style="padding:10px 0;border-bottom:1px dashed #f0fdf4;display:flex;justify-content:space-between;align-items:center">
              <div>
                <div style="font-weight:700;font-size:0.9rem">{tp['prenom'] or ''} {tp['nom']}</div>
                <div style="font-size:0.72rem;color:#94a3b8">{tp['code']} · {tp['village'] or '-'}</div>
              </div>
              <div style="text-align:right">
                <div style="font-weight:900;color:#10b981">{fmt_kg(tp['total_kg'])}</div>
                <div style="font-size:0.7rem;color:#94a3b8">{tp['nb_recoltes']} récoltes</div>
              </div>
            </div>"""
        if not top_producteurs:
            content += '<div class="empty" style="padding:20px">Aucun producteur</div>'
        content += "</div></div>"

        # Derniers OF
        content += """
        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-industry"></i> Derniers ordres de fabrication</h3>
            <a href="/production" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Voir</a>
          </div>
          <div class="table-wrap"><table>
            <thead><tr><th>Référence</th><th>Produit</th><th>Quantité</th>
                       <th>Lot</th><th>Rendement</th><th>Statut</th><th>Date</th></tr></thead>
            <tbody>"""
        for of in derniers_of:
            badge = 'badge-success' if of['statut'] == 'Terminé' else ('badge-warning' if of['statut'] == 'En cours' else 'badge-info')
            content += f"""
            <tr>
              <td><small>{of['reference']}</small></td>
              <td><strong>{of['produit_nom'] or '-'}</strong>
                  <div style="font-size:0.72rem;color:#94a3b8">{of['produit_code']}</div></td>
              <td>{fmt_kg(of['quantite_kg'])}</td>
              <td><small>{of['lot_production']}</small></td>
              <td><span class="badge badge-primary">{of['rendement_pct'] or 0:.1f}%</span></td>
              <td><span class="badge {badge}">{of['statut']}</span></td>
              <td><small>{fmt_date(of['date_debut'])}</small></td>
            </tr>"""
        if not derniers_of:
            content += '<tr><td colspan="7" class="empty">Aucun ordre</td></tr>'
        content += "</tbody></table></div></div>"

        # Derniers exports
        content += """
        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-ship"></i> Derniers exports UE</h3>
            <a href="/exports" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Voir</a>
          </div>
          <div class="table-wrap"><table>
            <thead><tr><th>Référence</th><th>Client</th><th>Pays</th>
                       <th>Produit</th><th>Quantité</th><th>Montant</th><th>Statut</th></tr></thead>
            <tbody>"""
        for e in derniers_exports:
            badge = 'badge-success' if e['statut'] == 'Livré' else ('badge-warning' if e['statut'] == 'En transit' else 'badge-info')
            content += f"""
            <tr>
              <td><small>{e['reference']}</small></td>
              <td><strong>{e['client_nom'] or '-'}</strong></td>
              <td>{e['client_pays'] or '-'}</td>
              <td>{e['produit_nom'] or '-'}</td>
              <td>{fmt_kg(e['quantite_kg'])}</td>
              <td><strong style="color:#10b981">{fmt_fcfa(e['montant_total'])}</strong></td>
              <td><span class="badge {badge}">{e['statut']}</span></td>
            </tr>"""
        if not derniers_exports:
            content += '<tr><td colspan="7" class="empty">Aucun export</td></tr>'
        content += "</tbody></table></div></div>"

        # Activité
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

        return render_page(content, active='dashboard', page_title='Dashboard SM10 AGRO')

    except Exception as e:
        import traceback
        traceback.print_exc()
        conn.close()
        flash(f"Erreur dashboard : {e}", "danger")
        return redirect('/login')


# ==================== INIT MODULES ====================
try:
    from crud import init_crud
    init_crud(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[CRUD] ✅ Module CRUD enregistré")
except Exception as e:
    print(f"[CRUD] ⚠️ {e}")

try:
    from agro_logic import init_agro
    init_agro(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[LOGIC] ✅ Module logique enregistré")
except Exception as e:
    print(f"[LOGIC] ⚠️ {e}")

try:
    from qualite import init_qualite
    init_qualite(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[QUALITE] ✅ Module qualité enregistré")
except Exception as e:
    print(f"[QUALITE] ⚠️ {e}")

try:
    from export_ue import init_export
    init_export(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[EXPORT] ✅ Module export UE enregistré")
except Exception as e:
    print(f"[EXPORT] ⚠️ {e}")

try:
    from formation import init_formation
    init_formation(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[FORMATION] ✅ Module formation enregistré")
except Exception as e:
    print(f"[FORMATION] ⚠️ {e}")

try:
    from rapports import init_rapports
    init_rapports(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[RAPPORTS] ✅ Module rapports enregistré")
except Exception as e:
    print(f"[RAPPORTS] ⚠️ {e}")

try:
    from portail import init_portail
    init_portail(app, get_db=get_db, render_page=render_page, log_action=log_action)

    # ═══════ QR ═══════
    try:
        from qr_generator import init_qr
        init_qr(app, get_db=get_db, render_page=render_page, log_action=log_action)
    except ImportError as e:
        print(f'[QR] ⚠️ {e}')

    # ═══════ PDF ═══════
    try:
        from pdf_factures import init_pdf
        init_pdf(app, get_db=get_db, render_page=render_page, log_action=log_action)
    except ImportError as e:
        print(f'[PDF] ⚠️ {e}')

    # ═══════ SMS ═══════
    try:
        from sms_notifications import init_sms
        init_sms(app, get_db=get_db, render_page=render_page, log_action=log_action)
    except ImportError as e:
        print(f'[SMS] ⚠️ {e}')

    # ═══════ V3.1 : IoT Capteurs ═══════
    try:
        from iot_sensors import init_iot
        init_iot(app, get_db=get_db, render_page=render_page, log_action=log_action)
    except ImportError as e:
        print(f'[IOT] ⚠️ {e}')

    # ═══════ V3.2 : PWA Mobile ═══════
    try:
        from pwa_mobile import init_pwa
        init_pwa(app, get_db=get_db, render_page=render_page, log_action=log_action)
    except ImportError as e:
        print(f'[PWA] ⚠️ {e}')
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
