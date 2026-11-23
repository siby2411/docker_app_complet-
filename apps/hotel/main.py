"""
Omega Hôtel — Plateforme de gestion hôtelière premium
Design doré luxe — Développé par Omega Informatique
"""
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'omega_hotel_2026_secret_key_premium'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

DB_PATH = "/app/data/hotel.db"

# ==================== AUTH ====================
try:
    from auth import (init_auth, log_action, role_required, admin_required,
                      directeur_required, reception_required, staff_required, menage_required)
    init_auth(app)
    AUTH_OK = True
    print("[AUTH] ✅ Module auth chargé")
except Exception as e:
    print(f"[AUTH] ⚠️ {e}")
    AUTH_OK = False
    def role_required(*r):
        def d(f): return f
        return d
    def admin_required(f): return f
    def directeur_required(f): return f
    def reception_required(f): return f
    def staff_required(f): return f
    def menage_required(f): return f
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


# ==================== DESIGN DORÉ LUXE ====================
HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Omega Hôtel — {{ page_title or 'Gestion hôtelière' }}</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}
body{background:#fffbeb;color:#451a03;min-height:100vh}

/* TOP BANNER */
.top-banner{background:linear-gradient(90deg,#451a03 0%,#92400e 50%,#d97706 100%);color:white;padding:10px 25px;font-size:0.82rem;display:flex;justify-content:space-between;align-items:center;font-weight:600;letter-spacing:0.3px}
.top-banner i{color:#fbbf24}
.top-banner .brand-info{display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.top-banner strong{color:#fbbf24;font-weight:800}

/* HEADER */
.header{background:white;box-shadow:0 4px 24px rgba(146,64,14,0.08);padding:16px 30px;display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #d97706;flex-wrap:wrap;gap:15px}
.header .logo-section{display:flex;align-items:center;gap:15px}
.logo-icon{width:60px;height:60px;background:linear-gradient(135deg,#92400e,#d97706);border-radius:14px;display:flex;justify-content:center;align-items:center;color:white;font-size:1.8rem;box-shadow:0 8px 24px rgba(146,64,14,0.3)}
.header h1{font-size:1.55rem;color:#451a03;font-weight:900;line-height:1.05;letter-spacing:-0.5px}
.header h1 span{color:#d97706}
.header .subtitle{font-size:0.7rem;color:#64748b;margin-top:4px;letter-spacing:1px;text-transform:uppercase;font-weight:700}
.header .stars{color:#fbbf24;font-size:0.85rem;letter-spacing:2px;margin-top:2px}
.user-section{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.user-badge{display:flex;align-items:center;gap:10px;padding:8px 16px;background:#fffbeb;border-radius:30px;border:1.5px solid #fde68a}
.user-badge .avatar{width:38px;height:38px;background:linear-gradient(135deg,#92400e,#d97706);border-radius:50%;display:flex;justify-content:center;align-items:center;color:white;font-weight:800;font-size:0.9rem}
.user-badge .info{display:flex;flex-direction:column;line-height:1.15}
.user-badge .name{font-weight:700;font-size:0.85rem;color:#451a03}
.user-badge .role{font-size:0.68rem;color:#92400e;text-transform:uppercase;font-weight:800;letter-spacing:0.5px}
.btn-logout{background:linear-gradient(135deg,#dc2626,#ef4444);color:white;padding:9px 16px;border-radius:10px;text-decoration:none;font-size:0.82rem;font-weight:700;transition:0.3s;box-shadow:0 4px 12px rgba(220,38,38,0.25)}
.btn-logout:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(220,38,38,0.35)}

/* NAV */
.nav{background:white;padding:0 25px;display:flex;gap:2px;border-bottom:1px solid #fde68a;flex-wrap:wrap;box-shadow:0 2px 8px rgba(0,0,0,0.03)}
.nav a{padding:15px 18px;color:#475569;text-decoration:none;border-bottom:3px solid transparent;transition:0.3s;font-size:0.85rem;display:flex;align-items:center;gap:7px;font-weight:600}
.nav a:hover{color:#d97706;background:#fffbeb}
.nav a.active{color:#92400e;border-bottom-color:#d97706;background:#fffbeb}

/* CONTAINER */
.container{max-width:1500px;margin:28px auto;padding:0 25px}

/* PAGE HEADER */
.page-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:28px;flex-wrap:wrap;gap:15px}
.page-header h2{font-size:1.7rem;color:#451a03;font-weight:900;display:flex;align-items:center;gap:12px;letter-spacing:-0.5px}
.page-header h2 i{color:#d97706}
.page-header .page-subtitle{color:#64748b;font-size:0.88rem;margin-top:4px}

/* STATS */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:20px;margin-bottom:28px}
.stat-card{background:white;border-radius:18px;padding:24px;position:relative;overflow:hidden;box-shadow:0 6px 20px rgba(146,64,14,0.06);transition:0.3s;border-left:5px solid #d97706}
.stat-card:hover{transform:translateY(-5px);box-shadow:0 12px 30px rgba(146,64,14,0.15)}
.stat-card .stat-icon{position:absolute;right:18px;top:18px;font-size:2.8rem;color:#d97706;opacity:0.12}
.stat-card .stat-value{font-size:2.2rem;font-weight:900;color:#451a03;line-height:1;letter-spacing:-1px}
.stat-card .stat-label{color:#64748b;font-size:0.75rem;text-transform:uppercase;font-weight:800;letter-spacing:1px;margin-top:10px}
.stat-card.gold{border-left-color:#fbbf24}.stat-card.gold .stat-icon{color:#fbbf24}
.stat-card.green{border-left-color:#10b981}.stat-card.green .stat-icon{color:#10b981}
.stat-card.blue{border-left-color:#0891b2}.stat-card.blue .stat-icon{color:#0891b2}
.stat-card.rose{border-left-color:#dc2626}.stat-card.rose .stat-icon{color:#dc2626}
.stat-card.purple{border-left-color:#7c3aed}.stat-card.purple .stat-icon{color:#7c3aed}

/* CARDS */
.card{background:white;border-radius:18px;padding:28px;box-shadow:0 6px 20px rgba(146,64,14,0.06);margin-bottom:22px}
.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:12px;padding-bottom:18px;border-bottom:2px solid #fffbeb}
.card-header h3{font-size:1.2rem;color:#451a03;font-weight:800;display:flex;align-items:center;gap:10px}
.card-header h3 i{color:#d97706}

/* BUTTONS */
.btn{padding:11px 20px;border:none;border-radius:10px;cursor:pointer;font-weight:700;display:inline-flex;align-items:center;gap:8px;text-decoration:none;transition:0.3s;font-size:0.85rem;letter-spacing:0.3px}
.btn-primary{background:linear-gradient(135deg,#92400e,#d97706);color:white;box-shadow:0 6px 16px rgba(146,64,14,0.3)}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 10px 24px rgba(146,64,14,0.4)}
.btn-gold{background:linear-gradient(135deg,#d97706,#fbbf24);color:white;box-shadow:0 6px 16px rgba(217,119,6,0.3)}
.btn-gold:hover{transform:translateY(-2px);box-shadow:0 10px 24px rgba(217,119,6,0.4)}
.btn-success{background:linear-gradient(135deg,#16a34a,#22c55e);color:white}
.btn-warning{background:linear-gradient(135deg,#f59e0b,#fbbf24);color:white}
.btn-danger{background:linear-gradient(135deg,#dc2626,#ef4444);color:white}
.btn-info{background:linear-gradient(135deg,#0891b2,#06b6d4);color:white}
.btn-sm{padding:7px 13px;font-size:0.75rem}

/* TABLES */
.table-wrap{overflow-x:auto;border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:0.88rem}
th,td{padding:14px 16px;text-align:left;border-bottom:1px solid #fffbeb}
th{background:linear-gradient(180deg,#fffbeb,#fef3c7);color:#92400e;font-size:0.72rem;text-transform:uppercase;font-weight:800;letter-spacing:0.8px}
tbody tr{transition:0.2s}
tbody tr:hover{background:#fffbeb}

/* BADGES */
.badge{padding:5px 12px;border-radius:20px;font-size:0.7rem;font-weight:800;display:inline-flex;align-items:center;gap:5px;letter-spacing:0.3px}
.badge-success{background:#d1fae5;color:#065f46}
.badge-warning{background:#fef3c7;color:#92400e}
.badge-danger{background:#fee2e2;color:#991b1b}
.badge-info{background:#dbeafe;color:#1e40af}
.badge-gold{background:linear-gradient(135deg,#fbbf24,#f59e0b);color:white}
.badge-vip{background:linear-gradient(135deg,#fbbf24,#d97706);color:white}
.badge-role-admin{background:linear-gradient(135deg,#dc2626,#ef4444);color:white}
.badge-role-directeur{background:linear-gradient(135deg,#92400e,#d97706);color:white}
.badge-role-receptionniste{background:linear-gradient(135deg,#0891b2,#06b6d4);color:white}
.badge-role-gouvernante{background:linear-gradient(135deg,#10b981,#22c55e);color:white}
.badge-role-femme_chambre{background:linear-gradient(135deg,#64748b,#94a3b8);color:white}

/* FLASH */
.flash{padding:15px 20px;border-radius:12px;margin-bottom:18px;display:flex;align-items:center;gap:12px;font-size:0.9rem;font-weight:600}
.flash-success{background:#d1fae5;color:#065f46;border-left:5px solid #10b981}
.flash-danger{background:#fee2e2;color:#991b1b;border-left:5px solid #dc2626}
.flash-warning{background:#fef3c7;color:#92400e;border-left:5px solid #f59e0b}
.flash-info{background:#dbeafe;color:#1e40af;border-left:5px solid #3b82f6}

/* FORMS */
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.form-group{margin-bottom:16px}
.form-group label{display:block;font-weight:800;color:#92400e;margin-bottom:8px;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.5px}
.form-group input,.form-group select,.form-group textarea{width:100%;padding:12px 15px;border:2px solid #f1f5f9;border-radius:11px;font-size:0.92rem;background:#f8fafc;transition:0.3s;font-family:inherit}
.form-group input:focus,.form-group select:focus,.form-group textarea:focus{outline:none;border-color:#d97706;background:white;box-shadow:0 0 0 4px rgba(217,119,6,0.1)}
.form-full{grid-column:1/-1}

/* FOOTER */
.footer{background:linear-gradient(135deg,#451a03,#92400e);color:white;padding:30px;margin-top:60px;text-align:center;font-size:0.85rem}
.footer strong{color:#fbbf24;font-weight:800}
.footer .footer-sub{opacity:0.75;font-size:0.75rem;margin-top:8px}

/* EMPTY */
.empty{text-align:center;padding:60px 20px;color:#94a3b8}
.empty i{font-size:4rem;color:#fde68a;margin-bottom:18px}

/* HERO */
.hero{background:linear-gradient(135deg,#451a03 0%,#92400e 50%,#d97706 100%);border-radius:24px;padding:50px;color:white;margin-bottom:30px;position:relative;overflow:hidden;box-shadow:0 15px 40px rgba(146,64,14,0.3)}
.hero::before{content:'';position:absolute;top:-80px;right:-80px;width:280px;height:280px;background:rgba(255,215,0,0.15);border-radius:50%}
.hero::after{content:'';position:absolute;bottom:-100px;left:-50px;width:220px;height:220px;background:rgba(255,215,0,0.1);border-radius:50%}
.hero h1{font-size:2.4rem;font-weight:900;margin-bottom:12px;position:relative;z-index:1;letter-spacing:-1px}
.hero h1 span{color:#fbbf24}
.hero p{font-size:1.05rem;opacity:0.95;position:relative;z-index:1;max-width:600px;line-height:1.5}
.hero .stars{color:#fbbf24;font-size:1.2rem;letter-spacing:3px;margin-bottom:10px;position:relative;z-index:1}

/* KPI PREMIUM */
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px;margin-bottom:25px}
.kpi-card{background:white;border-radius:16px;padding:22px;box-shadow:0 6px 20px rgba(146,64,14,0.08);display:flex;align-items:center;gap:16px;transition:0.3s;border-top:4px solid #d97706}
.kpi-card:hover{transform:translateY(-3px);box-shadow:0 12px 30px rgba(146,64,14,0.15)}
.kpi-card .kpi-icon{width:56px;height:56px;border-radius:14px;display:flex;justify-content:center;align-items:center;font-size:1.6rem;color:white;flex-shrink:0}
.kpi-card .kpi-content{flex:1}
.kpi-card .kpi-label{font-size:0.78rem;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:0.5px}
.kpi-card .kpi-value{font-size:1.6rem;font-weight:900;color:#451a03;line-height:1.1;margin-top:4px}
.kpi-card .kpi-sub{font-size:0.75rem;color:#94a3b8;margin-top:4px}

/* CHAMBRE CARD */
.chambre-card{background:white;border-radius:14px;padding:18px;box-shadow:0 4px 15px rgba(146,64,14,0.08);transition:0.3s;border-left:5px solid #d97706}
.chambre-card:hover{transform:translateY(-3px);box-shadow:0 8px 25px rgba(146,64,14,0.15)}
.chambre-card .num{font-size:1.4rem;font-weight:900;color:#451a03}
.chambre-card .type{font-size:0.8rem;color:#92400e;font-weight:700;text-transform:uppercase;letter-spacing:0.5px}
.chambre-card .status{margin-top:10px;padding:6px 12px;border-radius:20px;font-size:0.7rem;font-weight:800;display:inline-block}

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

<!-- TOP BANNER -->
<div class="top-banner">
  <div class="brand-info">
    <span><i class="fas fa-hotel"></i> <strong>OMEGA HÔTEL</strong> — Gestion hôtelière premium</span>
  </div>
  <div class="brand-info">
    <span><i class="fas fa-star"></i> 5 étoiles</span>
    <span><i class="fas fa-crown"></i> Excellence & Luxe</span>
  </div>
</div>

<!-- HEADER -->
<header class="header">
  <div class="logo-section">
    <div class="logo-icon"><i class="fas fa-hotel"></i></div>
    <div>
      <h1>OMEGA <span>HÔTEL</span></h1>
      <div class="stars">★★★★★</div>
      <div class="subtitle"><i class="fas fa-shield-halved"></i> Service premium</div>
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

<!-- NAV -->
<nav class="nav">
  <a href="/" class="{{ 'active' if active=='dashboard' else '' }}"><i class="fas fa-chart-pie"></i> Dashboard</a>
  {% if current_user and current_user.is_authenticated %}
    {% if current_user.role in ['admin','directeur','receptionniste','gouvernante'] %}
    <a href="/chambres" class="{{ 'active' if active=='chambres' else '' }}"><i class="fas fa-bed"></i> Chambres</a>
    {% endif %}
    {% if current_user.role in ['admin','directeur','receptionniste'] %}
    <a href="/reservations" class="{{ 'active' if active=='reservations' else '' }}"><i class="fas fa-calendar-check"></i> Réservations</a>
    <a href="/clients" class="{{ 'active' if active=='clients' else '' }}"><i class="fas fa-users"></i> Clients</a>
    <a href="/sejours" class="{{ 'active' if active=='sejours' else '' }}"><i class="fas fa-user-check"></i> Séjours</a>
    {% endif %}
    {% if current_user.role in ['admin','directeur','receptionniste'] %}
    <a href="/restaurant" class="{{ 'active' if active=='restaurant' else '' }}"><i class="fas fa-utensils"></i> Restaurant</a>
    {% endif %}
    {% if current_user.role in ['admin','directeur','receptionniste','gouvernante','femme_chambre'] %}
    <a href="/housekeeping" class="{{ 'active' if active=='housekeeping' else '' }}"><i class="fas fa-broom"></i> Housekeeping</a>
    {% endif %}
    {% if current_user.role in ['admin','directeur','receptionniste'] %}
    <a href="/facturation" class="{{ 'active' if active=='facturation' else '' }}"><i class="fas fa-file-invoice-dollar"></i> Facturation</a>
    {% endif %}
    {% if current_user.role in ['admin','directeur'] %}
    <a href="/tarifs" class="{{ 'active' if active=='tarifs' else '' }}"><i class="fas fa-tags"></i> Tarifs</a>
    <a href="/rapports" class="{{ 'active' if active=='rapports' else '' }}"><i class="fas fa-chart-line"></i> Rapports</a>
    {% endif %}
    {% if current_user.role == 'admin' %}
    <a href="/directeur/accueil" class="{{ 'active' if active=='directeur' else '' }}"><i class="fas fa-chart-pie"></i> Espace Directeur</a>
    <a href="/reception/accueil" class="{{ 'active' if active=='reception' else '' }}"><i class="fas fa-concierge-bell"></i> Espace Réception</a>
    <a href="/gouvernante/accueil" class="{{ 'active' if active=='gouvernante' else '' }}"><i class="fas fa-broom"></i> Espace Gouvernante</a>
    <a href="/planning-chambres" class="{{ 'active' if active=='planning' else '' }}"><i class="fas fa-th"></i> Planning</a>
    <a href="/utilisateurs" class="{{ 'active' if active=='utilisateurs' else '' }}"><i class="fas fa-user-shield"></i> Utilisateurs</a>
    {% endif %}
  {% endif %}
</nav>

<!-- CONTAINER -->
<div class="container">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}{% for cat, msg in messages %}
      <div class="flash flash-{{ cat }}"><i class="fas fa-circle-info"></i> {{ msg }}</div>
    {% endfor %}{% endif %}
  {% endwith %}

  {% block content %}{% endblock %}
</div>

<!-- FOOTER -->
<footer class="footer">
  <div>&copy; 2026 <strong>OMEGA HÔTEL</strong> — Tous droits réservés</div>
  <div class="footer-sub">
    <i class="fas fa-code"></i> Développé par <strong>OMEGA INFORMATIQUE</strong> — Solutions hôtelières premium · Dakar, Sénégal
  </div>
</footer>

</body>
</html>
"""


def render_page(content, active='dashboard', page_title='Omega Hôtel'):
    page = HTML_BASE.replace("{% block content %}{% endblock %}", content)
    return render_template_string(page, active=active, page_title=page_title, current_user=current_user)


# ==================== HEALTHCHECK ====================
@app.route('/health')
def health():
    return jsonify(status='ok', service='hotel-omega', timestamp=datetime.now().isoformat())


# ==================== DASHBOARD ====================
@app.route('/')
def index():
    if not (current_user and current_user.is_authenticated):
        return redirect('/login')

    conn = get_db()
    c = conn.cursor()

    # Effectif chambres
    c.execute("SELECT COUNT(*) FROM chambres WHERE actif=1")
    total_chambres = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM chambres WHERE actif=1 AND statut='Occupée'")
    chambres_occupees = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM chambres WHERE actif=1 AND statut='Disponible'")
    chambres_dispo = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM chambres WHERE actif=1 AND statut='Maintenance'")
    chambres_maintenance = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM chambres WHERE actif=1 AND statut='Réservée'")
    chambres_reservees = c.fetchone()[0]

    taux_occupation = (chambres_occupees / total_chambres * 100) if total_chambres else 0

    # Arrivées aujourd'hui
    today = datetime.now().date().isoformat()
    c.execute("""SELECT COUNT(*) FROM reservations
                 WHERE date(date_arrivee) = ? AND statut='Confirmée'""", (today,))
    arrivees_jour = c.fetchone()[0]

    # Départs aujourd'hui
    c.execute("""SELECT COUNT(*) FROM reservations
                 WHERE date(date_depart) = ? AND statut='Confirmée'""", (today,))
    departs_jour = c.fetchone()[0]

    # CA du jour
    c.execute("""SELECT COALESCE(SUM(montant), 0) FROM paiements
                 WHERE date(date_paiement) = ?""", (today,))
    ca_jour = c.fetchone()[0]

    # CA du mois
    c.execute("""SELECT COALESCE(SUM(montant), 0) FROM paiements
                 WHERE strftime('%Y-%m', date_paiement) = strftime('%Y-%m', 'now')""")
    ca_mois = c.fetchone()[0]

    # Tâches housekeeping en attente
    c.execute("SELECT COUNT(*) FROM taches_housekeeping WHERE statut IN ('À faire', 'En cours')")
    taches_hk = c.fetchone()[0]

    # Réservations prochaines
    c.execute("""SELECT r.*, cl.nom, cl.prenom, ch.numero as chambre_numero,
                        tc.nom as type_nom
                 FROM reservations r
                 JOIN clients cl ON r.client_id = cl.id
                 LEFT JOIN chambres ch ON r.chambre_id = ch.id
                 JOIN types_chambres tc ON r.type_chambre_id = tc.id
                 WHERE r.date_arrivee >= date('now')
                   AND r.statut IN ('Confirmée', 'En attente')
                 ORDER BY r.date_arrivee ASC LIMIT 8""")
    prochaines = c.fetchall()

    # Chambres par statut (détail)
    c.execute("""SELECT ch.numero, ch.statut, tc.nom as type_nom, ch.etat_proprete
                 FROM chambres ch
                 JOIN types_chambres tc ON ch.type_id = tc.id
                 WHERE ch.actif=1
                 ORDER BY ch.numero LIMIT 20""")
    chambres_liste = c.fetchall()

    conn.close()

    content = f"""
    <div class="hero">
      <div class="stars">★★★★★</div>
      <h1>Bienvenue <span>{current_user.prenom}</span> 👋</h1>
      <p>Tableau de bord temps réel — Pilotez votre établissement avec excellence</p>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card" style="border-top-color:#10b981">
        <div class="kpi-icon" style="background:linear-gradient(135deg,#10b981,#22c55e)">
          <i class="fas fa-percentage"></i>
        </div>
        <div class="kpi-content">
          <div class="kpi-label">Taux d'occupation</div>
          <div class="kpi-value">{taux_occupation:.1f}%</div>
          <div class="kpi-sub">{chambres_occupees} / {total_chambres} chambres</div>
        </div>
      </div>

      <div class="kpi-card" style="border-top-color:#d97706">
        <div class="kpi-icon" style="background:linear-gradient(135deg,#92400e,#d97706)">
          <i class="fas fa-money-bill-wave"></i>
        </div>
        <div class="kpi-content">
          <div class="kpi-label">CA du jour</div>
          <div class="kpi-value">{ca_jour:,.0f}</div>
          <div class="kpi-sub">FCFA · Mois : {ca_mois:,.0f}</div>
        </div>
      </div>

      <div class="kpi-card" style="border-top-color:#0891b2">
        <div class="kpi-icon" style="background:linear-gradient(135deg,#0891b2,#06b6d4)">
          <i class="fas fa-plane-arrival"></i>
        </div>
        <div class="kpi-content">
          <div class="kpi-label">Arrivées du jour</div>
          <div class="kpi-value">{arrivees_jour}</div>
          <div class="kpi-sub">{departs_jour} départ(s) prévu(s)</div>
        </div>
      </div>

      <div class="kpi-card" style="border-top-color:#fbbf24">
        <div class="kpi-icon" style="background:linear-gradient(135deg,#d97706,#fbbf24)">
          <i class="fas fa-bed"></i>
        </div>
        <div class="kpi-content">
          <div class="kpi-label">Chambres disponibles</div>
          <div class="kpi-value">{chambres_dispo}</div>
          <div class="kpi-sub">{chambres_reservees} réservées · {chambres_maintenance} maint.</div>
        </div>
      </div>

      <div class="kpi-card" style="border-top-color:#7c3aed">
        <div class="kpi-icon" style="background:linear-gradient(135deg,#7c3aed,#a855f7)">
          <i class="fas fa-broom"></i>
        </div>
        <div class="kpi-content">
          <div class="kpi-label">Housekeeping</div>
          <div class="kpi-value">{taches_hk}</div>
          <div class="kpi-sub">Tâches en cours</div>
        </div>
      </div>

      <div class="kpi-card" style="border-top-color:#dc2626">
        <div class="kpi-icon" style="background:linear-gradient(135deg,#dc2626,#ef4444)">
          <i class="fas fa-bed"></i>
        </div>
        <div class="kpi-content">
          <div class="kpi-label">Chambres totales</div>
          <div class="kpi-value">{total_chambres}</div>
          <div class="kpi-sub">Capacité max</div>
        </div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px">
      <div>
        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-calendar-check"></i> Prochaines arrivées</h3>
            <a href="/reservations" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Voir tout</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>N°</th><th>Client</th><th>Chambre</th>
                  <th>Arrivée</th><th>Nuits</th><th>Statut</th>
                </tr>
              </thead>
              <tbody>
    """
    for r in prochaines:
        badge = 'badge-success' if r['statut'] == 'Confirmée' else 'badge-warning'
        content += f"""
        <tr>
          <td><strong>{r['numero']}</strong></td>
          <td>{r['nom']} {r['prenom']}</td>
          <td>{r['chambre_numero'] or 'À attribuer'}<br><small style="color:#94a3b8">{r['type_nom']}</small></td>
          <td>{r['date_arrivee']}</td>
          <td><strong>{r['nb_nuits']}j</strong></td>
          <td><span class="badge {badge}">{r['statut']}</span></td>
        </tr>
        """
    if not prochaines:
        content += '<tr><td colspan="6" class="empty"><i class="fas fa-calendar-check"></i><br>Aucune arrivée prévue</td></tr>'

    content += """
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div>
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-chart-pie"></i> Statut chambres</h3></div>
          <div style="display:flex;flex-direction:column;gap:12px">
    """
    statuts = [
        ('Disponible', chambres_dispo, '#10b981'),
        ('Occupée', chambres_occupees, '#dc2626'),
        ('Réservée', chambres_reservees, '#0891b2'),
        ('Maintenance', chambres_maintenance, '#f59e0b'),
    ]
    for label, nb, color in statuts:
        pct = (nb / total_chambres * 100) if total_chambres else 0
        content += f"""
        <div>
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <span style="font-weight:700;font-size:0.85rem">{label}</span>
            <strong style="color:{color}">{nb} ({pct:.0f}%)</strong>
          </div>
          <div style="background:#f3f4f6;border-radius:6px;height:10px;overflow:hidden">
            <div style="background:{color};height:100%;width:{pct}%"></div>
          </div>
        </div>
        """

    content += """
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-bell"></i> Actions rapides</h3></div>
          <div style="display:flex;flex-direction:column;gap:10px">
            <a href="/reservations/nouvelle" class="btn btn-gold" style="justify-content:center"><i class="fas fa-plus"></i> Nouvelle réservation</a>
            <a href="/sejours/checkin" class="btn btn-success" style="justify-content:center"><i class="fas fa-sign-in-alt"></i> Check-in</a>
            <a href="/sejours/checkout" class="btn btn-warning" style="justify-content:center"><i class="fas fa-sign-out-alt"></i> Check-out</a>
            <a href="/housekeeping" class="btn btn-info" style="justify-content:center"><i class="fas fa-broom"></i> Housekeeping</a>
          </div>
        </div>
      </div>
    </div>
    """
    return render_page(content, active='dashboard', page_title='Dashboard')



# ==================== ENREGISTREMENT DES ROUTES ====================
try:
    from crud import register_crud_routes
    register_crud_routes(app, render_page)
    print("[MAIN] ✅ Routes CRUD enregistrées")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"[MAIN] ⚠️ CRUD non chargé: {e}")

try:
    from hotel_logic import register_hotel_routes
    register_hotel_routes(app, render_page)
    print("[MAIN] ✅ Routes hotel_logic enregistrées")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"[MAIN] ⚠️ Hotel logic non chargé: {e}")

try:
    from portail import register_portail_routes
    register_portail_routes(app, render_page)
    print("[MAIN] ✅ Routes portail enregistrées")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"[MAIN] ⚠️ Portail non chargé: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
