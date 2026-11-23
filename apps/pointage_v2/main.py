"""
Omega Pointage V2 — Application principale
Dashboard turquoise · Gestion temps & présence
Design conforme ISO 15489, RGPD, UEMOA
"""
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'omega_pointage_v2_2026_premium_secret'

# ⚠️ Config cookies adaptée aux réseaux locaux HTTP
app.config['SESSION_COOKIE_SECURE'] = False  # HTTP autorisé (LAN)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Compatible mobile
app.config['REMEMBER_COOKIE_SECURE'] = False
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24h

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

DB_PATH = "/app/data/pointage_v2.db"
UPLOAD_FOLDER = "/app/data/justificatifs"

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 MB

# ==================== AUTH ====================
try:
    from auth import (init_auth, log_action, User, role_required, admin_required,
                      rh_required, chef_required, staff_required)
    AUTH_OK = True
except Exception as e:
    print(f"[AUTH] ⚠️ {e}")
    AUTH_OK = False
    def role_required(*r):
        def d(f): return f
        return d
    admin_required = rh_required = chef_required = staff_required = role_required()
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


def format_duree(minutes):
    """Formate minutes en hh:mm"""
    if not minutes:
        return "0h00"
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}h{m:02d}"


def format_fcfa(montant):
    """Formate un montant en FCFA"""
    if not montant:
        return "0 F"
    return f"{int(montant):,} F".replace(",", " ")


# ==================== DESIGN TURQUOISE ====================
HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Omega Pointage — {{ page_title or 'Gestion du temps' }}</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}
body{background:#f0fdff;color:#0e7490;min-height:100vh}

.top-banner{background:linear-gradient(90deg,#0e7490 0%,#06b6d4 60%,#22d3ee 100%);color:white;padding:10px 25px;font-size:0.82rem;display:flex;justify-content:space-between;align-items:center;font-weight:600;letter-spacing:0.3px;flex-wrap:wrap;gap:8px}
.top-banner i{color:#a5f3fc}
.top-banner strong{color:#a5f3fc;font-weight:800}
.top-banner .certif{background:rgba(165,243,252,0.2);padding:3px 10px;border-radius:20px;font-size:0.7rem;letter-spacing:0.5px;font-weight:700;color:#a5f3fc}

.header{background:white;box-shadow:0 4px 24px rgba(14,116,144,0.08);padding:16px 30px;display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #06b6d4;flex-wrap:wrap;gap:15px}
.header .logo-section{display:flex;align-items:center;gap:15px}
.logo-icon{width:56px;height:56px;background:linear-gradient(135deg,#0e7490,#06b6d4);border-radius:14px;display:flex;justify-content:center;align-items:center;color:white;font-size:1.7rem;box-shadow:0 8px 24px rgba(14,116,144,0.3)}
.header h1{font-size:1.55rem;color:#0e7490;font-weight:900;line-height:1.05;letter-spacing:-0.5px}
.header h1 span{color:#06b6d4}
.header .subtitle{font-size:0.72rem;color:#64748b;margin-top:4px;letter-spacing:1px;text-transform:uppercase;font-weight:700}
.user-section{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.user-badge{display:flex;align-items:center;gap:10px;padding:8px 16px;background:#f0fdff;border-radius:30px;border:1.5px solid #a5f3fc}
.user-badge .avatar{width:38px;height:38px;background:linear-gradient(135deg,#0e7490,#06b6d4);border-radius:50%;display:flex;justify-content:center;align-items:center;color:white;font-weight:800;font-size:0.9rem}
.user-badge .info{display:flex;flex-direction:column;line-height:1.15}
.user-badge .name{font-weight:700;font-size:0.85rem;color:#0e7490}
.user-badge .role{font-size:0.68rem;color:#06b6d4;text-transform:uppercase;font-weight:800;letter-spacing:0.5px}
.btn-logout{background:linear-gradient(135deg,#dc2626,#ef4444);color:white;padding:9px 16px;border-radius:10px;text-decoration:none;font-size:0.82rem;font-weight:700;transition:0.3s;box-shadow:0 4px 12px rgba(220,38,38,0.25)}
.btn-logout:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(220,38,38,0.35)}

.nav{background:white;padding:0 25px;display:flex;gap:2px;border-bottom:1px solid #a5f3fc;flex-wrap:wrap;box-shadow:0 2px 8px rgba(0,0,0,0.03)}
.nav a{padding:15px 18px;color:#475569;text-decoration:none;border-bottom:3px solid transparent;transition:0.3s;font-size:0.85rem;display:flex;align-items:center;gap:7px;font-weight:600}
.nav a:hover{color:#06b6d4;background:#f0fdff}
.nav a.active{color:#0e7490;border-bottom-color:#06b6d4;background:#f0fdff}

.container{max-width:1500px;margin:28px auto;padding:0 25px}

.page-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:28px;flex-wrap:wrap;gap:15px}
.page-header h2{font-size:1.7rem;color:#0e7490;font-weight:900;display:flex;align-items:center;gap:12px;letter-spacing:-0.5px}
.page-header h2 i{color:#06b6d4}
.page-header .page-subtitle{color:#64748b;font-size:0.88rem;margin-top:4px}

.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:20px;margin-bottom:28px}
.stat-card{background:white;border-radius:18px;padding:24px;position:relative;overflow:hidden;box-shadow:0 6px 20px rgba(14,116,144,0.06);transition:0.3s;border-left:5px solid #06b6d4}
.stat-card:hover{transform:translateY(-5px);box-shadow:0 12px 30px rgba(14,116,144,0.15)}
.stat-card .stat-icon{position:absolute;right:18px;top:18px;font-size:2.8rem;color:#06b6d4;opacity:0.12}
.stat-card .stat-value{font-size:2.2rem;font-weight:900;color:#0e7490;line-height:1;letter-spacing:-1px}
.stat-card .stat-label{color:#64748b;font-size:0.75rem;text-transform:uppercase;font-weight:800;letter-spacing:1px;margin-top:10px}
.stat-card.gold{border-left-color:#f59e0b}.stat-card.gold .stat-icon{color:#f59e0b}
.stat-card.green{border-left-color:#10b981}.stat-card.green .stat-icon{color:#10b981}
.stat-card.rose{border-left-color:#dc2626}.stat-card.rose .stat-icon{color:#dc2626}
.stat-card.purple{border-left-color:#7c3aed}.stat-card.purple .stat-icon{color:#7c3aed}

.card{background:white;border-radius:18px;padding:28px;box-shadow:0 6px 20px rgba(14,116,144,0.06);margin-bottom:22px}
.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:12px;padding-bottom:18px;border-bottom:2px solid #f0fdff}
.card-header h3{font-size:1.2rem;color:#0e7490;font-weight:800;display:flex;align-items:center;gap:10px}
.card-header h3 i{color:#06b6d4}

.btn{padding:11px 20px;border:none;border-radius:10px;cursor:pointer;font-weight:700;display:inline-flex;align-items:center;gap:8px;text-decoration:none;transition:0.3s;font-size:0.85rem;letter-spacing:0.3px}
.btn-primary{background:linear-gradient(135deg,#0e7490,#06b6d4);color:white;box-shadow:0 6px 16px rgba(14,116,144,0.3)}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 10px 24px rgba(14,116,144,0.4)}
.btn-success{background:linear-gradient(135deg,#16a34a,#22c55e);color:white}
.btn-warning{background:linear-gradient(135deg,#f59e0b,#fbbf24);color:white}
.btn-danger{background:linear-gradient(135deg,#dc2626,#ef4444);color:white}
.btn-info{background:linear-gradient(135deg,#0891b2,#06b6d4);color:white}
.btn-purple{background:linear-gradient(135deg,#7c3aed,#a855f7);color:white}
.btn-sm{padding:7px 13px;font-size:0.75rem}

.table-wrap{overflow-x:auto;border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:0.88rem}
th,td{padding:14px 16px;text-align:left;border-bottom:1px solid #f0fdff}
th{background:linear-gradient(180deg,#f0fdff,#cffafe);color:#0e7490;font-size:0.72rem;text-transform:uppercase;font-weight:800;letter-spacing:0.8px}
tbody tr{transition:0.2s}
tbody tr:hover{background:#f0fdff}

.badge{padding:5px 12px;border-radius:20px;font-size:0.7rem;font-weight:800;display:inline-flex;align-items:center;gap:5px;letter-spacing:0.3px}
.badge-success{background:#d1fae5;color:#065f46}
.badge-warning{background:#fef3c7;color:#92400e}
.badge-danger{background:#fee2e2;color:#991b1b}
.badge-info{background:#dbeafe;color:#1e40af}
.badge-primary{background:#cffafe;color:#155e75}
.badge-role-admin{background:linear-gradient(135deg,#dc2626,#ef4444);color:white}
.badge-role-rh{background:linear-gradient(135deg,#0e7490,#06b6d4);color:white}
.badge-role-chef{background:linear-gradient(135deg,#7c3aed,#a855f7);color:white}
.badge-role-pointage{background:linear-gradient(135deg,#f59e0b,#fbbf24);color:white}
.badge-role-employe{background:linear-gradient(135deg,#10b981,#22c55e);color:white}
.badge-role-lecteur{background:linear-gradient(135deg,#64748b,#94a3b8);color:white}

.flash{padding:15px 20px;border-radius:12px;margin-bottom:18px;display:flex;align-items:center;gap:12px;font-size:0.9rem;font-weight:600}
.flash-success{background:#d1fae5;color:#065f46;border-left:5px solid #10b981}
.flash-danger{background:#fee2e2;color:#991b1b;border-left:5px solid #dc2626}
.flash-warning{background:#fef3c7;color:#92400e;border-left:5px solid #f59e0b}
.flash-info{background:#dbeafe;color:#1e40af;border-left:5px solid #3b82f6}

.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.form-group{margin-bottom:16px}
.form-group label{display:block;font-weight:800;color:#0e7490;margin-bottom:8px;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.5px}
.form-group input,.form-group select,.form-group textarea{width:100%;padding:12px 15px;border:2px solid #f1f5f9;border-radius:11px;font-size:0.92rem;background:#f8fafc;transition:0.3s;font-family:inherit}
.form-group input:focus,.form-group select:focus,.form-group textarea:focus{outline:none;border-color:#06b6d4;background:white;box-shadow:0 0 0 4px rgba(6,182,212,0.1)}
.form-full{grid-column:1/-1}

.footer{background:linear-gradient(135deg,#0e7490,#155e75);color:white;padding:30px;margin-top:60px;text-align:center;font-size:0.85rem}
.footer strong{color:#a5f3fc;font-weight:800}
.footer .footer-sub{opacity:0.75;font-size:0.75rem;margin-top:8px}

.empty{text-align:center;padding:60px 20px;color:#94a3b8}
.empty i{font-size:4rem;color:#cffafe;margin-bottom:18px}

.hero{background:linear-gradient(135deg,#0e7490 0%,#06b6d4 50%,#22d3ee 100%);border-radius:24px;padding:50px;color:white;margin-bottom:30px;position:relative;overflow:hidden;box-shadow:0 15px 40px rgba(14,116,144,0.25)}
.hero::before{content:'';position:absolute;top:-80px;right:-80px;width:280px;height:280px;background:rgba(165,243,252,0.15);border-radius:50%}
.hero::after{content:'';position:absolute;bottom:-100px;left:-50px;width:220px;height:220px;background:rgba(165,243,252,0.1);border-radius:50%}
.hero h1{font-size:2.4rem;font-weight:900;margin-bottom:12px;position:relative;z-index:1;letter-spacing:-1px}
.hero h1 span{color:#a5f3fc}
.hero p{font-size:1.05rem;opacity:0.95;position:relative;z-index:1;max-width:700px;line-height:1.5}
.hero .certifs{display:flex;gap:10px;margin-top:20px;position:relative;z-index:1;flex-wrap:wrap}
.hero .certifs span{background:rgba(255,255,255,0.15);padding:6px 14px;border-radius:20px;font-size:0.75rem;font-weight:800;letter-spacing:0.5px;backdrop-filter:blur(10px)}

.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:18px;margin-bottom:25px}
.kpi-card{background:white;border-radius:16px;padding:22px;box-shadow:0 6px 20px rgba(14,116,144,0.08);display:flex;align-items:center;gap:16px;transition:0.3s;border-top:4px solid #06b6d4}
.kpi-card:hover{transform:translateY(-3px);box-shadow:0 12px 30px rgba(14,116,144,0.15)}
.kpi-card .kpi-icon{width:56px;height:56px;border-radius:14px;display:flex;justify-content:center;align-items:center;font-size:1.6rem;color:white;flex-shrink:0}
.kpi-card .kpi-content{flex:1}
.kpi-card .kpi-label{font-size:0.78rem;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:0.5px}
.kpi-card .kpi-value{font-size:1.6rem;font-weight:900;color:#0e7490;line-height:1.1;margin-top:4px}
.kpi-card .kpi-sub{font-size:0.75rem;color:#94a3b8;margin-top:4px}

.punch-hero{background:linear-gradient(135deg,#0e7490 0%,#06b6d4 100%);border-radius:20px;padding:30px;color:white;margin-bottom:25px;text-align:center;box-shadow:0 15px 40px rgba(14,116,144,0.3)}
.punch-hero .time{font-size:3.5rem;font-weight:900;letter-spacing:-2px;line-height:1}
.punch-hero .date{font-size:0.95rem;opacity:0.9;margin-top:8px}
.punch-hero .actions{margin-top:24px;display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
.punch-btn{padding:16px 32px;border-radius:14px;font-weight:800;font-size:1.05rem;border:none;cursor:pointer;transition:0.3s;display:inline-flex;align-items:center;gap:10px;letter-spacing:0.5px}
.punch-in{background:#10b981;color:white;box-shadow:0 8px 24px rgba(16,185,129,0.4)}
.punch-in:hover{transform:translateY(-3px);box-shadow:0 12px 32px rgba(16,185,129,0.5)}
.punch-out{background:#f59e0b;color:white;box-shadow:0 8px 24px rgba(245,158,11,0.4)}
.punch-out:hover{transform:translateY(-3px);box-shadow:0 12px 32px rgba(245,158,11,0.5)}

@media(max-width:768px){
  .form-grid{grid-template-columns:1fr}
  .header{flex-direction:column;align-items:flex-start}
  .stats{grid-template-columns:1fr 1fr}
  .container{padding:0 15px}
  .hero{padding:30px 20px}
  .hero h1{font-size:1.7rem}
  .top-banner{flex-direction:column;gap:5px;text-align:center}
  .punch-hero .time{font-size:2.5rem}
}
</style>
</head>
<body>

<div class="top-banner">
  <span><i class="fas fa-clock"></i> <strong>OMEGA POINTAGE V2</strong> — Gestion du temps & présence</span>
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <span class="certif">ISO 15489</span>
    <span class="certif">RGPD</span>
    <span class="certif">UEMOA</span>
    <span class="certif">SYSCOHADA</span>
  </div>
</div>

<header class="header">
  <div class="logo-section">
    <div class="logo-icon"><i class="fas fa-clock"></i></div>
    <div>
      <h1>OMEGA <span>POINTAGE</span></h1>
      <div class="subtitle"><i class="fas fa-fingerprint"></i> Gestion du temps & présence</div>
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
    {% if current_user.role in ['admin','rh','chef','pointage'] %}
    <a href="/pointages" class="{{ 'active' if active=='pointages' else '' }}"><i class="fas fa-fingerprint"></i> Pointages</a>
    <a href="/pointages/nouveau" class="{{ 'active' if active=='pointage_new' else '' }}"><i class="fas fa-plus-circle"></i> Saisir</a>
    <a href="/pointage/scan" class="{{ 'active' if active=='scan' else '' }}" style="background:linear-gradient(135deg,#10b981,#22c55e);color:white;margin:5px;border-radius:8px"><i class="fas fa-qrcode"></i> 📱 Scanner QR</a>
    {% endif %}
    <a href="/employes" class="{{ 'active' if active=='employes' else '' }}"><i class="fas fa-users"></i> Employés</a>
    {% if current_user.role in ['admin','rh','chef','pointage'] %}
    <a href="/plannings" class="{{ 'active' if active=='plannings' else '' }}"><i class="fas fa-calendar-days"></i> Plannings</a>
    <a href="/conges" class="{{ 'active' if active=='conges' else '' }}"><i class="fas fa-plane-departure"></i> Congés</a>
    <a href="/heures-sup" class="{{ 'active' if active=='hs' else '' }}"><i class="fas fa-plus"></i> Heures sup</a>
    {% endif %}
    {% if current_user.role in ['admin','rh'] %}
    <a href="/rapports" class="{{ 'active' if active=='rapports' else '' }}"><i class="fas fa-file-invoice"></i> Rapports</a>
    <a href="/recap-mensuel" class="{{ 'active' if active=='recap' else '' }}"><i class="fas fa-chart-line"></i> Récap mensuel</a>
    <a href="/absences" class="{{ 'active' if active=='absences' else '' }}"><i class="fas fa-user-xmark"></i> Absences</a>
    <a href="/terminaux" class="{{ 'active' if active=='terminaux' else '' }}"><i class="fas fa-microchip"></i> Terminaux</a>
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
  <div>&copy; 2026 <strong>OMEGA POINTAGE V2</strong> — Tous droits réservés</div>
  <div class="footer-sub">
    <i class="fas fa-code"></i> Développé par <strong>OMEGA INFORMATIQUE</strong> · Dakar, Sénégal · UEMOA
  </div>
</footer>

</body>
</html>
"""


def render_page(content, active='dashboard', page_title='Omega Pointage'):
    page = HTML_BASE.replace("{% block content %}{% endblock %}", content)
    return render_template_string(page, active=active, page_title=page_title,
                                  current_user=current_user)


# ==================== HEALTHCHECK ====================
@app.route('/health')
def health():
    return jsonify(status='ok', service='pointage-v2', timestamp=datetime.now().isoformat())


# ==================== DASHBOARD ====================
@app.route('/')
def index():
    if not (current_user and current_user.is_authenticated):
        return redirect('/login')

    conn = get_db()
    c = conn.cursor()

    try:
        today = datetime.now().date().isoformat()
        mois_courant = datetime.now().strftime('%Y-%m')

        # KPI 1 : Employés actifs
        c.execute("SELECT COUNT(*) FROM employes WHERE actif=1")
        nb_employes = c.fetchone()[0] or 0

        # KPI 2 : Présents aujourd'hui
        c.execute("""SELECT COUNT(DISTINCT employe_id) FROM pointages
                     WHERE date_pointage=? AND heure_entree IS NOT NULL
                     AND statut NOT IN ('Absent')""", (today,))
        presents_jour = c.fetchone()[0] or 0

        # KPI 3 : Retards aujourd'hui
        c.execute("""SELECT COUNT(*) FROM pointages
                     WHERE date_pointage=? AND statut='Retard'""", (today,))
        retards_jour = c.fetchone()[0] or 0

        # KPI 4 : Absents aujourd'hui
        c.execute("""SELECT COUNT(*) FROM pointages
                     WHERE date_pointage=? AND statut='Absent'""", (today,))
        absents_jour = c.fetchone()[0] or 0

        # KPI 5 : Congés en attente
        c.execute("""SELECT COUNT(*) FROM conges WHERE statut='En attente'""")
        conges_attente = c.fetchone()[0] or 0

        # KPI 6 : Heures sup en attente
        c.execute("""SELECT COALESCE(SUM(nb_heures), 0) FROM heures_sup
                     WHERE statut='En attente'""")
        hs_attente = c.fetchone()[0] or 0

        # KPI 7 : Heures totales mois
        c.execute("""SELECT COALESCE(SUM(heures_travaillees), 0) FROM pointages
                     WHERE strftime('%Y-%m', date_pointage)=?""", (mois_courant,))
        heures_mois = c.fetchone()[0] or 0

        # KPI 8 : Taux de présence
        c.execute("""SELECT COUNT(*) FROM pointages
                     WHERE strftime('%Y-%m', date_pointage)=?""", (mois_courant,))
        total_pointages_mois = c.fetchone()[0] or 0
        c.execute("""SELECT COUNT(*) FROM pointages
                     WHERE strftime('%Y-%m', date_pointage)=?
                     AND statut NOT IN ('Absent')""", (mois_courant,))
        presents_mois = c.fetchone()[0] or 0
        taux_presence = round((presents_mois / total_pointages_mois * 100) if total_pointages_mois else 0, 1)

        # Derniers pointages du jour
        c.execute("""SELECT p.*, e.matricule, e.nom, e.prenom,
                            d.nom AS departement_nom
                     FROM pointages p
                     LEFT JOIN employes e ON p.employe_id = e.id
                     LEFT JOIN departements d ON e.departement_id = d.id
                     WHERE p.date_pointage=?
                     ORDER BY p.heure_entree DESC LIMIT 15""", (today,))
        dernieres_entrees = c.fetchall()

        # Congés à venir
        c.execute("""SELECT c.*, e.matricule, e.nom, e.prenom, tc.nom AS type_nom
                     FROM conges c
                     LEFT JOIN employes e ON c.employe_id = e.id
                     LEFT JOIN types_conges tc ON c.type_conge_id = tc.id
                     WHERE c.statut IN ('En attente','Approuvé')
                       AND date(c.date_debut) >= date('now')
                     ORDER BY c.date_debut LIMIT 5""")
        conges_a_venir = c.fetchall()

        # Activité récente
        c.execute("""SELECT a.*, u.nom AS user_nom, u.prenom AS user_prenom
                     FROM audit_log a
                     LEFT JOIN utilisateurs u ON a.user_id = u.id
                     ORDER BY a.created_at DESC LIMIT 6""")
        activite = c.fetchall()

        # Employés par département (top)
        c.execute("""SELECT d.nom, d.code, COUNT(e.id) AS nb
                     FROM departements d
                     LEFT JOIN employes e ON e.departement_id = d.id AND e.actif=1
                     WHERE d.actif=1
                     GROUP BY d.id HAVING nb > 0
                     ORDER BY nb DESC LIMIT 8""")
        par_departement = c.fetchall()

        conn.close()

        now = datetime.now()

        content = f"""
        <div class="hero">
          <h1>Bonjour <span>{current_user.prenom}</span> 👋</h1>
          <p>Système de gestion du temps et de présence — Pointage, plannings, congés, heures sup</p>
          <div class="certifs">
            <span>ISO 15489</span>
            <span>RGPD</span>
            <span>UEMOA</span>
            <span>SYSCOHADA</span>
          </div>
        </div>

        <div class="punch-hero">
          <div class="time" id="live-clock">{now.strftime('%H:%M:%S')}</div>
          <div class="date"><i class="fas fa-calendar"></i> {now.strftime('%A %d %B %Y')}</div>
          <div class="actions">
            <a href="/pointages/nouveau?type=entree" class="punch-btn punch-in">
              <i class="fas fa-right-to-bracket"></i> Pointer ENTRÉE
            </a>
            <a href="/pointages/nouveau?type=sortie" class="punch-btn punch-out">
              <i class="fas fa-right-from-bracket"></i> Pointer SORTIE
            </a>
          </div>
        </div>

        <div class="kpi-grid">
          <div class="kpi-card" style="border-top-color:#06b6d4">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#0e7490,#06b6d4)">
              <i class="fas fa-users"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Employés actifs</div>
              <div class="kpi-value">{nb_employes}</div>
              <div class="kpi-sub">Effectif total</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#10b981">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#10b981,#22c55e)">
              <i class="fas fa-user-check"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Présents aujourd'hui</div>
              <div class="kpi-value">{presents_jour}</div>
              <div class="kpi-sub">Taux : {taux_presence}%</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#f59e0b">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#d97706,#f59e0b)">
              <i class="fas fa-clock"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Retards aujourd'hui</div>
              <div class="kpi-value">{retards_jour}</div>
              <div class="kpi-sub">À surveiller</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#dc2626">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#dc2626,#ef4444)">
              <i class="fas fa-user-xmark"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Absents aujourd'hui</div>
              <div class="kpi-value">{absents_jour}</div>
              <div class="kpi-sub">Non pointés</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#7c3aed">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#7c3aed,#a855f7)">
              <i class="fas fa-plane-departure"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Congés en attente</div>
              <div class="kpi-value">{conges_attente}</div>
              <div class="kpi-sub">À valider</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#0891b2">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#0891b2,#06b6d4)">
              <i class="fas fa-plus-circle"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Heures sup</div>
              <div class="kpi-value">{hs_attente:.1f}h</div>
              <div class="kpi-sub">En attente validation</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#14b8a6">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#14b8a6,#2dd4bf)">
              <i class="fas fa-hourglass-half"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Heures du mois</div>
              <div class="kpi-value">{heures_mois:.0f}h</div>
              <div class="kpi-sub">Cumul équipe</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#ec4899">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#ec4899,#f472b6)">
              <i class="fas fa-chart-line"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Taux présence</div>
              <div class="kpi-value">{taux_presence}%</div>
              <div class="kpi-sub">{presents_mois} / {total_pointages_mois} pointages</div>
            </div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="card">
            <div class="card-header">
              <h3><i class="fas fa-fingerprint"></i> Derniers pointages du jour</h3>
              <a href="/pointages" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Voir tout</a>
            </div>
            <div class="table-wrap">
              <table>
                <thead><tr><th>Employé</th><th>Entrée</th><th>Sortie</th><th>Statut</th></tr></thead>
                <tbody>
        """
        for p in dernieres_entrees:
            badge = 'badge-success'
            if p['statut'] == 'Retard': badge = 'badge-warning'
            elif p['statut'] == 'Absent': badge = 'badge-danger'
            content += f"""
            <tr>
              <td><strong>{p['prenom']} {p['nom']}</strong>
                  <div style="font-size:0.72rem;color:#94a3b8">{p['matricule']} · {p['departement_nom'] or '-'}</div></td>
              <td>{p['heure_entree'] or '-'}</td>
              <td>{p['heure_sortie'] or '-'}</td>
              <td><span class="badge {badge}">{p['statut']}</span></td>
            </tr>"""
        if not dernieres_entrees:
            content += '<tr><td colspan="4" class="empty"><i class="fas fa-fingerprint"></i><br>Aucun pointage aujourd\'hui</td></tr>'
        content += """
                </tbody>
              </table>
            </div>
          </div>

          <div class="card">
            <div class="card-header">
              <h3><i class="fas fa-users"></i> Effectif par département</h3>
            </div>
        """
        max_dep = max([d['nb'] for d in par_departement], default=1) if par_departement else 1
        for d in par_departement:
            pct = (d['nb'] / max_dep * 100) if max_dep else 0
            content += f"""
            <div style="margin-bottom:12px">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="font-weight:700;font-size:0.85rem">
                  <i class="fas fa-building" style="color:#06b6d4;font-size:0.75rem"></i>
                  {d['nom']}
                </span>
                <strong style="color:#0e7490">{d['nb']} pers.</strong>
              </div>
              <div style="background:#f0fdff;border-radius:6px;height:8px;overflow:hidden">
                <div style="background:linear-gradient(90deg,#0e7490,#22d3ee);height:100%;width:{pct}%"></div>
              </div>
            </div>
            """
        if not par_departement:
            content += '<div class="empty" style="padding:20px">Aucun département</div>'
        content += "</div></div>"

        # Congés à venir
        if conges_a_venir:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-plane-departure"></i> Congés à venir</h3></div>
              <div class="table-wrap"><table>
                <thead><tr><th>Employé</th><th>Type</th><th>Du</th><th>Au</th><th>Jours</th><th>Statut</th></tr></thead>
                <tbody>"""
            for c_ in conges_a_venir:
                badge = 'badge-success' if c_['statut'] == 'Approuvé' else 'badge-warning'
                content += f"""
                <tr>
                  <td><strong>{c_['prenom']} {c_['nom']}</strong></td>
                  <td>{c_['type_nom'] or '-'}</td>
                  <td>{c_['date_debut']}</td>
                  <td>{c_['date_fin']}</td>
                  <td><span class="badge badge-primary">{c_['nb_jours']} j</span></td>
                  <td><span class="badge {badge}">{c_['statut']}</span></td>
                </tr>"""
            content += "</tbody></table></div></div>"

        # Activité récente
        if activite:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-history"></i> Activité récente</h3></div>"""
            for a in activite:
                content += f"""
                <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px dashed #f0fdff">
                  <div>
                    <strong style="font-size:0.85rem">{a['user_prenom'] or '?'} {a['user_nom'] or ''}</strong>
                    <div style="font-size:0.8rem;color:#475569">{a['action']} — {a['details'] or ''}</div>
                  </div>
                  <small style="color:#94a3b8">{a['created_at'][:16]}</small>
                </div>"""
            content += "</div>"

        # Script horloge live
        content += """
        <script>
        function updateClock() {
          const now = new Date();
          const h = String(now.getHours()).padStart(2, '0');
          const m = String(now.getMinutes()).padStart(2, '0');
          const s = String(now.getSeconds()).padStart(2, '0');
          document.getElementById('live-clock').textContent = `${h}:${m}:${s}`;
        }
        setInterval(updateClock, 1000);
        </script>
        """

        return render_page(content, active='dashboard', page_title='Dashboard Pointage')

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
    from pointage_logic import init_pointage
    init_pointage(app, get_db=get_db, render_page=render_page,
                  log_action=log_action, UPLOAD_FOLDER=UPLOAD_FOLDER)
    print("[POINTAGE] ✅ Module logique enregistré")
except Exception as e:
    print(f"[POINTAGE] ⚠️ {e}")

try:
    from pointage_qr import init_qr
    init_qr(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[QR] ✅ Module QR scan enregistré")
except Exception as e:
    print(f"[QR] ⚠️ {e}")

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


# ==================== INIT DEBUG ====================
try:
    from debug_cookies import init_debug
    init_debug(app, get_db=get_db)
    print("[DEBUG] ✅ Module debug cookies enregistré")
except Exception as e:
    print(f"[DEBUG] ⚠️ {e}")


# ==================== INIT STATS ====================
try:
    from pointage_stats import init_stats
    init_stats(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[STATS] ✅ Module statistiques enregistré")
except Exception as e:
    print(f"[STATS] ⚠️ {e}")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
