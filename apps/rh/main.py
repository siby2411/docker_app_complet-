"""
Omega RH — Plateforme de gestion des Ressources Humaines
Design violet professionnel — Développé par Omega Informatique
"""
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'omega_rh_2026_secret_key_premium'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

DB_PATH = "/app/data/rh.db"

# ==================== AUTH ====================
try:
    from auth import (init_auth, log_action, role_required, admin_required,
                      drh_required, rh_required, manager_required, staff_required)
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
    def drh_required(f): return f
    def rh_required(f): return f
    def manager_required(f): return f
    def staff_required(f): return f
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


# ==================== DESIGN ÉPOUSTOUFLANT ====================
HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Omega RH — {{ page_title or 'Ressources Humaines' }}</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}
body{background:#faf5ff;color:#4c1d95;min-height:100vh}

/* ============ TOP BANNER ============ */
.top-banner{background:linear-gradient(90deg,#4c1d95 0%,#7c3aed 50%,#a855f7 100%);color:white;padding:10px 25px;font-size:0.82rem;display:flex;justify-content:space-between;align-items:center;font-weight:600;letter-spacing:0.3px}
.top-banner i{color:#c084fc}
.top-banner .brand-info{display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.top-banner strong{color:#c084fc;font-weight:800}

/* ============ HEADER ============ */
.header{background:white;box-shadow:0 4px 24px rgba(124,58,237,0.08);padding:16px 30px;display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #7c3aed;flex-wrap:wrap;gap:15px}
.header .logo-section{display:flex;align-items:center;gap:15px}
.logo-icon{width:56px;height:56px;background:linear-gradient(135deg,#7c3aed,#a855f7);border-radius:16px;display:flex;justify-content:center;align-items:center;color:white;font-size:1.7rem;box-shadow:0 8px 24px rgba(124,58,237,0.3)}
.header h1{font-size:1.55rem;color:#4c1d95;font-weight:900;line-height:1.05;letter-spacing:-0.5px}
.header h1 span{color:#a855f7}
.header .subtitle{font-size:0.72rem;color:#64748b;margin-top:4px;letter-spacing:1px;text-transform:uppercase;font-weight:700}
.user-section{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.user-badge{display:flex;align-items:center;gap:10px;padding:8px 16px;background:#f3e8ff;border-radius:30px;border:1.5px solid #e9d5ff}
.user-badge .avatar{width:38px;height:38px;background:linear-gradient(135deg,#7c3aed,#a855f7);border-radius:50%;display:flex;justify-content:center;align-items:center;color:white;font-weight:800;font-size:0.9rem}
.user-badge .info{display:flex;flex-direction:column;line-height:1.15}
.user-badge .name{font-weight:700;font-size:0.85rem;color:#4c1d95}
.user-badge .role{font-size:0.68rem;color:#7c3aed;text-transform:uppercase;font-weight:800;letter-spacing:0.5px}
.btn-logout{background:linear-gradient(135deg,#dc2626,#ef4444);color:white;padding:9px 16px;border-radius:10px;text-decoration:none;font-size:0.82rem;font-weight:700;transition:0.3s;box-shadow:0 4px 12px rgba(220,38,38,0.25)}
.btn-logout:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(220,38,38,0.35)}

/* ============ NAV ============ */
.nav{background:white;padding:0 25px;display:flex;gap:2px;border-bottom:1px solid #e9d5ff;flex-wrap:wrap;box-shadow:0 2px 8px rgba(0,0,0,0.03)}
.nav a{padding:15px 18px;color:#475569;text-decoration:none;border-bottom:3px solid transparent;transition:0.3s;font-size:0.85rem;display:flex;align-items:center;gap:7px;font-weight:600}
.nav a:hover{color:#7c3aed;background:#faf5ff}
.nav a.active{color:#7c3aed;border-bottom-color:#7c3aed;background:#faf5ff}

/* ============ CONTAINER ============ */
.container{max-width:1500px;margin:28px auto;padding:0 25px}

/* ============ PAGE HEADER ============ */
.page-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:28px;flex-wrap:wrap;gap:15px}
.page-header h2{font-size:1.7rem;color:#4c1d95;font-weight:900;display:flex;align-items:center;gap:12px;letter-spacing:-0.5px}
.page-header h2 i{color:#a855f7}
.page-header .page-subtitle{color:#64748b;font-size:0.88rem;margin-top:4px}

/* ============ STATS ============ */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:20px;margin-bottom:28px}
.stat-card{background:white;border-radius:18px;padding:24px;position:relative;overflow:hidden;box-shadow:0 6px 20px rgba(124,58,237,0.06);transition:0.3s;border-left:5px solid #a855f7}
.stat-card:hover{transform:translateY(-5px);box-shadow:0 12px 30px rgba(124,58,237,0.15)}
.stat-card .stat-icon{position:absolute;right:18px;top:18px;font-size:2.8rem;color:#a855f7;opacity:0.12}
.stat-card .stat-value{font-size:2.2rem;font-weight:900;color:#4c1d95;line-height:1;letter-spacing:-1px}
.stat-card .stat-label{color:#64748b;font-size:0.75rem;text-transform:uppercase;font-weight:800;letter-spacing:1px;margin-top:10px}
.stat-card.rose{border-left-color:#dc2626}.stat-card.rose .stat-icon{color:#dc2626}
.stat-card.amber{border-left-color:#f59e0b}.stat-card.amber .stat-icon{color:#f59e0b}
.stat-card.blue{border-left-color:#0891b2}.stat-card.blue .stat-icon{color:#0891b2}
.stat-card.green{border-left-color:#10b981}.stat-card.green .stat-icon{color:#10b981}
.stat-card.pink{border-left-color:#ec4899}.stat-card.pink .stat-icon{color:#ec4899}

/* ============ CARDS ============ */
.card{background:white;border-radius:18px;padding:28px;box-shadow:0 6px 20px rgba(124,58,237,0.06);margin-bottom:22px}
.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:12px;padding-bottom:18px;border-bottom:2px solid #f3e8ff}
.card-header h3{font-size:1.2rem;color:#4c1d95;font-weight:800;display:flex;align-items:center;gap:10px}
.card-header h3 i{color:#a855f7}

/* ============ BUTTONS ============ */
.btn{padding:11px 20px;border:none;border-radius:10px;cursor:pointer;font-weight:700;display:inline-flex;align-items:center;gap:8px;text-decoration:none;transition:0.3s;font-size:0.85rem;letter-spacing:0.3px}
.btn-primary{background:linear-gradient(135deg,#7c3aed,#a855f7);color:white;box-shadow:0 6px 16px rgba(124,58,237,0.3)}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 10px 24px rgba(124,58,237,0.4)}
.btn-success{background:linear-gradient(135deg,#16a34a,#22c55e);color:white}
.btn-success:hover{transform:translateY(-2px)}
.btn-warning{background:linear-gradient(135deg,#f59e0b,#fbbf24);color:white}
.btn-warning:hover{transform:translateY(-2px)}
.btn-danger{background:linear-gradient(135deg,#dc2626,#ef4444);color:white}
.btn-danger:hover{transform:translateY(-2px)}
.btn-info{background:linear-gradient(135deg,#0891b2,#06b6d4);color:white}
.btn-info:hover{transform:translateY(-2px)}
.btn-pink{background:linear-gradient(135deg,#ec4899,#f472b6);color:white}
.btn-pink:hover{transform:translateY(-2px)}
.btn-sm{padding:7px 13px;font-size:0.75rem}

/* ============ TABLES ============ */
.table-wrap{overflow-x:auto;border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:0.88rem}
th,td{padding:14px 16px;text-align:left;border-bottom:1px solid #f3e8ff}
th{background:linear-gradient(180deg,#f3e8ff,#e9d5ff);color:#7c3aed;font-size:0.72rem;text-transform:uppercase;font-weight:800;letter-spacing:0.8px}
tbody tr{transition:0.2s}
tbody tr:hover{background:#faf5ff}

/* ============ BADGES ============ */
.badge{padding:5px 12px;border-radius:20px;font-size:0.7rem;font-weight:800;display:inline-flex;align-items:center;gap:5px;letter-spacing:0.3px}
.badge-success{background:#d1fae5;color:#065f46}
.badge-warning{background:#fef3c7;color:#92400e}
.badge-danger{background:#fee2e2;color:#991b1b}
.badge-info{background:#dbeafe;color:#1e40af}
.badge-primary{background:#f3e8ff;color:#6b21a8}
.badge-role-admin{background:linear-gradient(135deg,#dc2626,#ef4444);color:white}
.badge-role-drh{background:linear-gradient(135deg,#7c3aed,#a855f7);color:white}
.badge-role-rh{background:linear-gradient(135deg,#0891b2,#06b6d4);color:white}
.badge-role-manager{background:linear-gradient(135deg,#f59e0b,#fbbf24);color:white}
.badge-role-employe{background:linear-gradient(135deg,#10b981,#22c55e);color:white}

/* ============ FLASH ============ */
.flash{padding:15px 20px;border-radius:12px;margin-bottom:18px;display:flex;align-items:center;gap:12px;font-size:0.9rem;font-weight:600}
.flash-success{background:#d1fae5;color:#065f46;border-left:5px solid #10b981}
.flash-danger{background:#fee2e2;color:#991b1b;border-left:5px solid #dc2626}
.flash-warning{background:#fef3c7;color:#92400e;border-left:5px solid #f59e0b}
.flash-info{background:#dbeafe;color:#1e40af;border-left:5px solid #3b82f6}

/* ============ FORMS ============ */
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.form-group{margin-bottom:16px}
.form-group label{display:block;font-weight:800;color:#7c3aed;margin-bottom:8px;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.5px}
.form-group input,.form-group select,.form-group textarea{width:100%;padding:12px 15px;border:2px solid #f1f5f9;border-radius:11px;font-size:0.92rem;background:#f8fafc;transition:0.3s;font-family:inherit}
.form-group input:focus,.form-group select:focus,.form-group textarea:focus{outline:none;border-color:#a855f7;background:white;box-shadow:0 0 0 4px rgba(168,85,247,0.1)}
.form-full{grid-column:1/-1}

/* ============ FOOTER ============ */
.footer{background:linear-gradient(135deg,#4c1d95,#6b21a8);color:white;padding:30px;margin-top:60px;text-align:center;font-size:0.85rem}
.footer strong{color:#c084fc;font-weight:800}
.footer .footer-sub{opacity:0.7;font-size:0.75rem;margin-top:8px}

/* ============ EMPTY ============ */
.empty{text-align:center;padding:60px 20px;color:#94a3b8}
.empty i{font-size:4rem;color:#e9d5ff;margin-bottom:18px}

/* ============ HERO ============ */
.hero{background:linear-gradient(135deg,#4c1d95 0%,#7c3aed 50%,#a855f7 100%);border-radius:24px;padding:50px;color:white;margin-bottom:30px;position:relative;overflow:hidden;box-shadow:0 15px 40px rgba(124,58,237,0.25)}
.hero::before{content:'';position:absolute;top:-80px;right:-80px;width:280px;height:280px;background:rgba(255,255,255,0.1);border-radius:50%}
.hero::after{content:'';position:absolute;bottom:-100px;left:-50px;width:220px;height:220px;background:rgba(255,255,255,0.08);border-radius:50%}
.hero h1{font-size:2.4rem;font-weight:900;margin-bottom:12px;position:relative;z-index:1;letter-spacing:-1px}
.hero h1 span{color:#e9d5ff}
.hero p{font-size:1.05rem;opacity:0.95;position:relative;z-index:1;max-width:600px;line-height:1.5}

/* ============ KPI PREMIUM ============ */
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px;margin-bottom:25px}
.kpi-card{background:white;border-radius:16px;padding:22px;box-shadow:0 6px 20px rgba(124,58,237,0.08);display:flex;align-items:center;gap:16px;transition:0.3s;border-top:4px solid #a855f7}
.kpi-card:hover{transform:translateY(-3px);box-shadow:0 12px 30px rgba(124,58,237,0.15)}
.kpi-card .kpi-icon{width:56px;height:56px;border-radius:14px;display:flex;justify-content:center;align-items:center;font-size:1.6rem;color:white;flex-shrink:0}
.kpi-card .kpi-content{flex:1}
.kpi-card .kpi-label{font-size:0.78rem;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:0.5px}
.kpi-card .kpi-value{font-size:1.6rem;font-weight:900;color:#4c1d95;line-height:1.1;margin-top:4px}
.kpi-card .kpi-sub{font-size:0.75rem;color:#94a3b8;margin-top:4px}

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
    <span><i class="fas fa-users-gear"></i> <strong>OMEGA RH</strong> — Gestion des Ressources Humaines</span>
  </div>
  <div class="brand-info">
    <span><i class="fas fa-shield-halved"></i> Conforme Code du Travail Sénégal</span>
    <span><i class="fas fa-calculator"></i> IPRES · CSS · IRPP</span>
  </div>
</div>

<!-- HEADER -->
<header class="header">
  <div class="logo-section">
    <div class="logo-icon"><i class="fas fa-users-gear"></i></div>
    <div>
      <h1>OMEGA <span>RH</span></h1>
      <div class="subtitle"><i class="fas fa-user-shield"></i> Ressources Humaines</div>
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
    {% if current_user.role in ['admin','drh','rh','manager'] %}
    <a href="/employes" class="{{ 'active' if active=='employes' else '' }}"><i class="fas fa-users"></i> Employés</a>
    {% endif %}
    {% if current_user.role in ['admin','drh','rh'] %}
    <a href="/departements" class="{{ 'active' if active=='departements' else '' }}"><i class="fas fa-sitemap"></i> Départements</a>
    <a href="/postes" class="{{ 'active' if active=='postes' else '' }}"><i class="fas fa-briefcase"></i> Postes</a>
    <a href="/contrats" class="{{ 'active' if active=='contrats' else '' }}"><i class="fas fa-file-contract"></i> Contrats</a>
    {% endif %}
    {% if current_user.role in ['admin','drh','rh','manager'] %}
    <a href="/conges" class="{{ 'active' if active=='conges' else '' }}"><i class="fas fa-calendar-check"></i> Congés</a>
    <a href="/pointages" class="{{ 'active' if active=='pointages' else '' }}"><i class="fas fa-clock"></i> Pointages</a>
    {% endif %}
    {% if current_user.role in ['admin','drh','rh'] %}
    <a href="/paie" class="{{ 'active' if active=='paie' else '' }}"><i class="fas fa-money-bill-wave"></i> Paie</a>
    {% endif %}
    {% if current_user.role in ['admin','drh','rh','manager'] %}
    <a href="/formations" class="{{ 'active' if active=='formations' else '' }}"><i class="fas fa-graduation-cap"></i> Formations</a>
    <a href="/evaluations" class="{{ 'active' if active=='evaluations' else '' }}"><i class="fas fa-star"></i> Évaluations</a>
    {% endif %}
    {% if current_user.role in ['admin','drh','rh'] %}
    <a href="/recrutement" class="{{ 'active' if active=='recrutement' else '' }}"><i class="fas fa-user-plus"></i> Recrutement</a>
    <a href="/drh/accueil" class="{{ 'active' if active=='drh' else '' }}"><i class="fas fa-chart-pie"></i> Espace DRH</a>
    <a href="/manager/accueil" class="{{ 'active' if active=='manager' else '' }}"><i class="fas fa-users-viewfinder"></i> Mon Équipe</a>
    <a href="/rh/accueil" class="{{ 'active' if active=='rh' else '' }}"><i class="fas fa-bolt"></i> Opérations RH</a>
    <a href="/calendrier-equipe" class="{{ 'active' if active=='calendrier' else '' }}"><i class="fas fa-calendar-alt"></i> Calendrier</a>
    <a href="/rapports" class="{{ 'active' if active=='rapports' else '' }}"><i class="fas fa-chart-line"></i> Rapports</a>
    {% endif %}
    {% if current_user.role == 'employe' %}
    <a href="/mon-espace" class="{{ 'active' if active=='mon_espace' else '' }}"><i class="fas fa-user-circle"></i> Mon espace</a>
    <a href="/mes-conges" class="{{ 'active' if active=='mes_conges' else '' }}"><i class="fas fa-calendar-check"></i> Mes congés</a>
    <a href="/mes-bulletins" class="{{ 'active' if active=='mes_bulletins' else '' }}"><i class="fas fa-file-invoice-dollar"></i> Mes bulletins</a>
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
  <div>&copy; 2026 <strong>OMEGA RH</strong> — Tous droits réservés</div>
  <div class="footer-sub">
    <i class="fas fa-code"></i> Développé par <strong>OMEGA INFORMATIQUE</strong> — Solutions digitales RH · Dakar, Sénégal
  </div>
</footer>

</body>
</html>
"""


def render_page(content, active='dashboard', page_title='Omega RH'):
    page = HTML_BASE.replace("{% block content %}{% endblock %}", content)
    return render_template_string(page, active=active, page_title=page_title, current_user=current_user)


# ==================== HEALTHCHECK ====================
@app.route('/health')
def health():
    return jsonify(status='ok', service='rh-omega', timestamp=datetime.now().isoformat())


# ==================== DASHBOARD ====================
@app.route('/')
def index():
    if not (current_user and current_user.is_authenticated):
        return redirect('/login')

    # Redirection employé vers son espace
    if current_user.role == 'employe':
        return redirect('/mon-espace')

    conn = get_db()
    c = conn.cursor()

    # KPIs principaux
    c.execute("SELECT COUNT(*) FROM employes WHERE actif=1 AND statut='Actif'")
    effectif_total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM employes WHERE actif=1 AND sexe='F' AND statut='Actif'")
    effectif_femmes = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM departements WHERE actif=1")
    total_departements = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM postes WHERE actif=1")
    total_postes = c.fetchone()[0]

    c.execute("""SELECT COALESCE(SUM(salaire_base + prime_transport + prime_logement + prime_autre), 0)
                 FROM employes WHERE actif=1 AND statut='Actif'""")
    masse_salariale = c.fetchone()[0]

    c.execute("""SELECT AVG(salaire_base) FROM employes WHERE actif=1 AND statut='Actif'""")
    salaire_moyen = c.fetchone()[0] or 0

    # Congés en attente
    c.execute("SELECT COUNT(*) FROM conges WHERE statut='En attente'")
    conges_attente = c.fetchone()[0]

    # Congés en cours aujourd'hui
    today = datetime.now().date().isoformat()
    c.execute("""SELECT COUNT(*) FROM conges
                 WHERE statut='Approuvé' AND date_debut <= ? AND date_fin >= ?""",
              (today, today))
    conges_en_cours = c.fetchone()[0]

    # Présence aujourd'hui
    c.execute("""SELECT COUNT(DISTINCT employe_id) FROM pointages
                 WHERE date_pointage = date('now')""")
    presents_jour = c.fetchone()[0]

    # Contrats expirant dans 60 jours
    c.execute("""SELECT COUNT(*) FROM contrats
                 WHERE statut='Actif' AND date_fin IS NOT NULL
                 AND date(date_fin) <= date('now', '+60 days')
                 AND date(date_fin) >= date('now')""")
    contrats_expirant = c.fetchone()[0]

    # Répartition par département
    c.execute("""SELECT d.nom, d.id, COUNT(e.id) as nb
                 FROM departements d
                 LEFT JOIN employes e ON e.departement_id = d.id AND e.actif=1
                 WHERE d.actif=1
                 GROUP BY d.id ORDER BY nb DESC LIMIT 8""")
    par_dept = c.fetchall()

    # Répartition par type de contrat
    c.execute("""SELECT type_contrat, COUNT(*) as nb FROM employes
                 WHERE actif=1 AND statut='Actif'
                 GROUP BY type_contrat ORDER BY nb DESC""")
    par_contrat = c.fetchall()

    # Derniers employés recrutés
    c.execute("""SELECT e.*, p.intitule as poste_nom, d.nom as dept_nom
                 FROM employes e
                 LEFT JOIN postes p ON e.poste_id = p.id
                 LEFT JOIN departements d ON e.departement_id = d.id
                 WHERE e.actif=1
                 ORDER BY e.date_embauche DESC LIMIT 5""")
    derniers_employes = c.fetchall()

    # Congés en attente (5 plus récents)
    c.execute("""SELECT cg.*, e.nom as e_nom, e.prenom as e_prenom, e.matricule,
                        tc.nom as type_nom, tc.couleur as type_couleur
                 FROM conges cg
                 JOIN employes e ON cg.employe_id = e.id
                 JOIN types_conges tc ON cg.type_conge_id = tc.id
                 WHERE cg.statut = 'En attente'
                 ORDER BY cg.created_at DESC LIMIT 5""")
    conges_recent = c.fetchall()

    # Anniversaires du mois
    c.execute("""SELECT nom, prenom, matricule, date_naissance
                 FROM employes WHERE actif=1 AND statut='Actif'
                 AND strftime('%m', date_naissance) = strftime('%m', 'now')
                 ORDER BY strftime('%d', date_naissance) LIMIT 10""")
    anniversaires = c.fetchall()

    conn.close()

    role_badge = f"badge-role-{current_user.role}"

    content = f"""
    <div class="hero">
      <h1>Bienvenue <span>{current_user.prenom}</span> 👋</h1>
      <p>Tableau de bord RH temps réel — Pilotez votre capital humain</p>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card" style="border-top-color:#7c3aed">
        <div class="kpi-icon" style="background:linear-gradient(135deg,#7c3aed,#a855f7)">
          <i class="fas fa-users"></i>
        </div>
        <div class="kpi-content">
          <div class="kpi-label">Effectif actif</div>
          <div class="kpi-value">{effectif_total}</div>
          <div class="kpi-sub">{effectif_femmes} femmes ({int(effectif_femmes/effectif_total*100) if effectif_total else 0}%)</div>
        </div>
      </div>

      <div class="kpi-card" style="border-top-color:#10b981">
        <div class="kpi-icon" style="background:linear-gradient(135deg,#10b981,#22c55e)">
          <i class="fas fa-money-bill-wave"></i>
        </div>
        <div class="kpi-content">
          <div class="kpi-label">Masse salariale</div>
          <div class="kpi-value">{masse_salariale:,.0f}</div>
          <div class="kpi-sub">FCFA / mois · Moy. {salaire_moyen:,.0f}</div>
        </div>
      </div>

      <div class="kpi-card" style="border-top-color:#0891b2">
        <div class="kpi-icon" style="background:linear-gradient(135deg,#0891b2,#06b6d4)">
          <i class="fas fa-calendar-check"></i>
        </div>
        <div class="kpi-content">
          <div class="kpi-label">Congés en cours</div>
          <div class="kpi-value">{conges_en_cours}</div>
          <div class="kpi-sub">{conges_attente} en attente de validation</div>
        </div>
      </div>

      <div class="kpi-card" style="border-top-color:#f59e0b">
        <div class="kpi-icon" style="background:linear-gradient(135deg,#f59e0b,#fbbf24)">
          <i class="fas fa-user-check"></i>
        </div>
        <div class="kpi-content">
          <div class="kpi-label">Présents aujourd'hui</div>
          <div class="kpi-value">{presents_jour}</div>
          <div class="kpi-sub">{int(presents_jour/effectif_total*100) if effectif_total else 0}% de présence</div>
        </div>
      </div>

      <div class="kpi-card" style="border-top-color:#dc2626">
        <div class="kpi-icon" style="background:linear-gradient(135deg,#dc2626,#ef4444)">
          <i class="fas fa-file-contract"></i>
        </div>
        <div class="kpi-content">
          <div class="kpi-label">Contrats à renouveler</div>
          <div class="kpi-value">{contrats_expirant}</div>
          <div class="kpi-sub">Dans les 60 prochains jours</div>
        </div>
      </div>

      <div class="kpi-card" style="border-top-color:#ec4899">
        <div class="kpi-icon" style="background:linear-gradient(135deg,#ec4899,#f472b6)">
          <i class="fas fa-sitemap"></i>
        </div>
        <div class="kpi-content">
          <div class="kpi-label">Structure</div>
          <div class="kpi-value">{total_departements}</div>
          <div class="kpi-sub">{total_postes} postes définis</div>
        </div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px">
      <div>
        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-calendar-clock"></i> Congés en attente de validation</h3>
            <a href="/conges" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Voir tout</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Employé</th><th>Type</th><th>Période</th><th>Jours</th><th>Actions</th></tr></thead>
              <tbody>
    """
    for cg in conges_recent:
        content += f"""
        <tr>
          <td><strong>{cg['e_nom']} {cg['e_prenom']}</strong><br><small style="color:#94a3b8">{cg['matricule']}</small></td>
          <td><span class="badge" style="background:{cg['type_couleur']}20;color:{cg['type_couleur']}">{cg['type_nom']}</span></td>
          <td>{cg['date_debut']} → {cg['date_fin']}</td>
          <td><strong>{cg['nb_jours']}j</strong></td>
          <td>
            <a href="/conges/{cg['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
          </td>
        </tr>
        """
    if not conges_recent:
        content += '<tr><td colspan="5" class="empty"><i class="fas fa-check-circle" style="color:#10b981"></i><br>Aucun congé en attente 🎉</td></tr>'

    content += """
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-user-plus"></i> Derniers employés recrutés</h3>
            <a href="/employes" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Voir tout</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Matricule</th><th>Nom</th><th>Poste</th><th>Département</th><th>Embauche</th></tr></thead>
              <tbody>
    """
    for e in derniers_employes:
        content += f"""
        <tr>
          <td><strong>{e['matricule']}</strong></td>
          <td>{e['nom']} {e['prenom']}</td>
          <td>{e['poste_nom'] or '-'}</td>
          <td>{e['dept_nom'] or '-'}</td>
          <td>{e['date_embauche'][:10]}</td>
        </tr>
        """
    content += """
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div>
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-sitemap"></i> Effectif par département</h3></div>
    """
    max_nb = max([d['nb'] for d in par_dept], default=1)
    for d in par_dept:
        pct = int((d['nb'] / max_nb) * 100) if max_nb else 0
        content += f"""
        <div style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <span style="font-weight:700;font-size:0.85rem">{d['nom'][:25]}</span>
            <strong style="color:#7c3aed">{d['nb']}</strong>
          </div>
          <div style="background:#f3e8ff;border-radius:6px;height:8px;overflow:hidden">
            <div style="background:linear-gradient(90deg,#7c3aed,#a855f7);height:100%;width:{pct}%"></div>
          </div>
        </div>
        """

    content += """
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-file-signature"></i> Types de contrats</h3></div>
    """
    for ct in par_contrat:
        content += f"""
        <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px dashed #f3e8ff">
          <span style="font-weight:700;font-size:0.9rem">{ct['type_contrat']}</span>
          <span class="badge badge-primary">{ct['nb']} employé(s)</span>
        </div>
        """

    content += """
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-birthday-cake"></i> Anniversaires du mois</h3></div>
    """
    if anniversaires:
        for a in anniversaires:
            try:
                jour = a['date_naissance'][8:10]
                mois = a['date_naissance'][5:7]
            except Exception:
                jour = '?'
                mois = '?'

            content += f"""
            <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px dashed #f3e8ff">
              <div>
                <div style="font-weight:700;font-size:0.85rem">🎂 {a['nom']} {a['prenom']}</div>
                <small style="color:#94a3b8">{a['matricule']}</small>
              </div>
              <span class="badge badge-pink">{jour}/{mois}</span>
            </div>
            """
    else:
        content += '<div class="empty" style="padding:20px;font-size:0.85rem">Aucun anniversaire ce mois</div>'

    content += """
        </div>
      </div>
    </div>
    """
    return render_page(content, active='dashboard', page_title='Dashboard RH')



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
    from rh_logic import register_rh_routes
    register_rh_routes(app, render_page)
    print("[MAIN] ✅ Routes rh_logic enregistrées")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"[MAIN] ⚠️ RH Logic non chargé: {e}")

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
