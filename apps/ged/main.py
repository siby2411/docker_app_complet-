"""
Omega GED — Plateforme de Gestion Électronique de Documents
Conforme ISO 15489, NF Z42-013, RGPD — UEMOA
Design turquoise professionnel
"""
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'omega_ged_2026_secret_key_premium'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

DB_PATH = "/app/data/ged.db"
UPLOAD_FOLDER = "/app/data/documents"
ARCHIVE_FOLDER = "/app/data/archives"

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

# ==================== AUTH ====================
try:
    from auth import (init_auth, log_action, role_required, admin_required,
                      archiviste_required, contributeur_required, staff_required, auditeur_required)
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
    def archiviste_required(f): return f
    def contributeur_required(f): return f
    def staff_required(f): return f
    def auditeur_required(f): return f
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


def format_taille(ko):
    """Formate une taille en Ko vers une unité lisible"""
    if ko < 1024:
        return f"{ko:.0f} Ko"
    elif ko < 1024 * 1024:
        return f"{ko/1024:.1f} Mo"
    else:
        return f"{ko/(1024*1024):.2f} Go"


# ==================== DESIGN TURQUOISE PROFESSIONNEL ====================
HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Omega GED — {{ page_title or 'Gestion documentaire' }}</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}
body{background:#f0fdff;color:#0e7490;min-height:100vh}

/* TOP BANNER */
.top-banner{background:linear-gradient(90deg,#0e7490 0%,#06b6d4 60%,#22d3ee 100%);color:white;padding:10px 25px;font-size:0.82rem;display:flex;justify-content:space-between;align-items:center;font-weight:600;letter-spacing:0.3px}
.top-banner i{color:#a5f3fc}
.top-banner .brand-info{display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.top-banner strong{color:#a5f3fc;font-weight:800}
.top-banner .certif{background:rgba(165,243,252,0.2);padding:3px 10px;border-radius:20px;font-size:0.7rem;letter-spacing:0.5px;font-weight:700;color:#a5f3fc}

/* HEADER */
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

/* NAV */
.nav{background:white;padding:0 25px;display:flex;gap:2px;border-bottom:1px solid #a5f3fc;flex-wrap:wrap;box-shadow:0 2px 8px rgba(0,0,0,0.03)}
.nav a{padding:15px 18px;color:#475569;text-decoration:none;border-bottom:3px solid transparent;transition:0.3s;font-size:0.85rem;display:flex;align-items:center;gap:7px;font-weight:600}
.nav a:hover{color:#06b6d4;background:#f0fdff}
.nav a.active{color:#0e7490;border-bottom-color:#06b6d4;background:#f0fdff}

/* CONTAINER */
.container{max-width:1500px;margin:28px auto;padding:0 25px}

/* PAGE HEADER */
.page-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:28px;flex-wrap:wrap;gap:15px}
.page-header h2{font-size:1.7rem;color:#0e7490;font-weight:900;display:flex;align-items:center;gap:12px;letter-spacing:-0.5px}
.page-header h2 i{color:#06b6d4}
.page-header .page-subtitle{color:#64748b;font-size:0.88rem;margin-top:4px}

/* STATS */
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

/* CARDS */
.card{background:white;border-radius:18px;padding:28px;box-shadow:0 6px 20px rgba(14,116,144,0.06);margin-bottom:22px}
.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:12px;padding-bottom:18px;border-bottom:2px solid #f0fdff}
.card-header h3{font-size:1.2rem;color:#0e7490;font-weight:800;display:flex;align-items:center;gap:10px}
.card-header h3 i{color:#06b6d4}

/* BUTTONS */
.btn{padding:11px 20px;border:none;border-radius:10px;cursor:pointer;font-weight:700;display:inline-flex;align-items:center;gap:8px;text-decoration:none;transition:0.3s;font-size:0.85rem;letter-spacing:0.3px}
.btn-primary{background:linear-gradient(135deg,#0e7490,#06b6d4);color:white;box-shadow:0 6px 16px rgba(14,116,144,0.3)}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 10px 24px rgba(14,116,144,0.4)}
.btn-success{background:linear-gradient(135deg,#16a34a,#22c55e);color:white}
.btn-warning{background:linear-gradient(135deg,#f59e0b,#fbbf24);color:white}
.btn-danger{background:linear-gradient(135deg,#dc2626,#ef4444);color:white}
.btn-info{background:linear-gradient(135deg,#0891b2,#06b6d4);color:white}
.btn-purple{background:linear-gradient(135deg,#7c3aed,#a855f7);color:white}
.btn-sm{padding:7px 13px;font-size:0.75rem}

/* TABLES */
.table-wrap{overflow-x:auto;border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:0.88rem}
th,td{padding:14px 16px;text-align:left;border-bottom:1px solid #f0fdff}
th{background:linear-gradient(180deg,#f0fdff,#cffafe);color:#0e7490;font-size:0.72rem;text-transform:uppercase;font-weight:800;letter-spacing:0.8px}
tbody tr{transition:0.2s}
tbody tr:hover{background:#f0fdff}

/* BADGES */
.badge{padding:5px 12px;border-radius:20px;font-size:0.7rem;font-weight:800;display:inline-flex;align-items:center;gap:5px;letter-spacing:0.3px}
.badge-success{background:#d1fae5;color:#065f46}
.badge-warning{background:#fef3c7;color:#92400e}
.badge-danger{background:#fee2e2;color:#991b1b}
.badge-info{background:#dbeafe;color:#1e40af}
.badge-primary{background:#cffafe;color:#155e75}
.badge-gold{background:linear-gradient(135deg,#fbbf24,#f59e0b);color:white}
.badge-role-admin{background:linear-gradient(135deg,#dc2626,#ef4444);color:white}
.badge-role-archiviste{background:linear-gradient(135deg,#0e7490,#06b6d4);color:white}
.badge-role-contributeur{background:linear-gradient(135deg,#7c3aed,#a855f7);color:white}
.badge-role-lecteur{background:linear-gradient(135deg,#10b981,#22c55e);color:white}
.badge-role-auditeur{background:linear-gradient(135deg,#f59e0b,#fbbf24);color:white}

/* FLASH */
.flash{padding:15px 20px;border-radius:12px;margin-bottom:18px;display:flex;align-items:center;gap:12px;font-size:0.9rem;font-weight:600}
.flash-success{background:#d1fae5;color:#065f46;border-left:5px solid #10b981}
.flash-danger{background:#fee2e2;color:#991b1b;border-left:5px solid #dc2626}
.flash-warning{background:#fef3c7;color:#92400e;border-left:5px solid #f59e0b}
.flash-info{background:#dbeafe;color:#1e40af;border-left:5px solid #3b82f6}

/* FORMS */
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.form-group{margin-bottom:16px}
.form-group label{display:block;font-weight:800;color:#0e7490;margin-bottom:8px;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.5px}
.form-group input,.form-group select,.form-group textarea{width:100%;padding:12px 15px;border:2px solid #f1f5f9;border-radius:11px;font-size:0.92rem;background:#f8fafc;transition:0.3s;font-family:inherit}
.form-group input:focus,.form-group select:focus,.form-group textarea:focus{outline:none;border-color:#06b6d4;background:white;box-shadow:0 0 0 4px rgba(6,182,212,0.1)}
.form-full{grid-column:1/-1}

/* FOOTER */
.footer{background:linear-gradient(135deg,#0e7490,#155e75);color:white;padding:30px;margin-top:60px;text-align:center;font-size:0.85rem}
.footer strong{color:#a5f3fc;font-weight:800}
.footer .footer-sub{opacity:0.75;font-size:0.75rem;margin-top:8px}

/* EMPTY */
.empty{text-align:center;padding:60px 20px;color:#94a3b8}
.empty i{font-size:4rem;color:#cffafe;margin-bottom:18px}

/* HERO */
.hero{background:linear-gradient(135deg,#0e7490 0%,#06b6d4 50%,#22d3ee 100%);border-radius:24px;padding:50px;color:white;margin-bottom:30px;position:relative;overflow:hidden;box-shadow:0 15px 40px rgba(14,116,144,0.25)}
.hero::before{content:'';position:absolute;top:-80px;right:-80px;width:280px;height:280px;background:rgba(165,243,252,0.15);border-radius:50%}
.hero::after{content:'';position:absolute;bottom:-100px;left:-50px;width:220px;height:220px;background:rgba(165,243,252,0.1);border-radius:50%}
.hero h1{font-size:2.4rem;font-weight:900;margin-bottom:12px;position:relative;z-index:1;letter-spacing:-1px}
.hero h1 span{color:#a5f3fc}
.hero p{font-size:1.05rem;opacity:0.95;position:relative;z-index:1;max-width:700px;line-height:1.5}
.hero .certifs{display:flex;gap:10px;margin-top:20px;position:relative;z-index:1;flex-wrap:wrap}
.hero .certifs span{background:rgba(255,255,255,0.15);padding:6px 14px;border-radius:20px;font-size:0.75rem;font-weight:800;letter-spacing:0.5px;backdrop-filter:blur(10px)}

/* KPI PREMIUM */
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:18px;margin-bottom:25px}
.kpi-card{background:white;border-radius:16px;padding:22px;box-shadow:0 6px 20px rgba(14,116,144,0.08);display:flex;align-items:center;gap:16px;transition:0.3s;border-top:4px solid #06b6d4}
.kpi-card:hover{transform:translateY(-3px);box-shadow:0 12px 30px rgba(14,116,144,0.15)}
.kpi-card .kpi-icon{width:56px;height:56px;border-radius:14px;display:flex;justify-content:center;align-items:center;font-size:1.6rem;color:white;flex-shrink:0}
.kpi-card .kpi-content{flex:1}
.kpi-card .kpi-label{font-size:0.78rem;color:#64748b;text-transform:uppercase;font-weight:700;letter-spacing:0.5px}
.kpi-card .kpi-value{font-size:1.6rem;font-weight:900;color:#0e7490;line-height:1.1;margin-top:4px}
.kpi-card .kpi-sub{font-size:0.75rem;color:#94a3b8;margin-top:4px}

/* DOSSIER */
.dossier-item{display:flex;align-items:center;gap:12px;padding:12px;border-radius:10px;transition:0.3s;text-decoration:none;color:inherit;border-bottom:1px dashed #f0fdff}
.dossier-item:hover{background:#f0fdff}
.dossier-item .dossier-icon{width:40px;height:40px;background:linear-gradient(135deg,#0e7490,#06b6d4);border-radius:10px;display:flex;justify-content:center;align-items:center;color:white;font-size:1.1rem;flex-shrink:0}
.dossier-item .dossier-info{flex:1}
.dossier-item .dossier-nom{font-weight:700;font-size:0.9rem}
.dossier-item .dossier-meta{font-size:0.75rem;color:#94a3b8;margin-top:2px}

/* DOC */
.doc-icon{width:36px;height:36px;border-radius:8px;display:flex;justify-content:center;align-items:center;color:white;font-size:1rem;flex-shrink:0}

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
    <span><i class="fas fa-folder-tree"></i> <strong>OMEGA GED</strong> — Gestion Électronique de Documents</span>
  </div>
  <div class="brand-info">
    <span class="certif">ISO 15489</span>
    <span class="certif">NF Z42-013</span>
    <span class="certif">RGPD</span>
    <span class="certif">UEMOA</span>
  </div>
</div>

<!-- HEADER -->
<header class="header">
  <div class="logo-section">
    <div class="logo-icon"><i class="fas fa-folder-tree"></i></div>
    <div>
      <h1>OMEGA <span>GED</span></h1>
      <div class="subtitle"><i class="fas fa-shield-halved"></i> Archivage conforme ISO</div>
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
    <a href="/dossiers" class="{{ 'active' if active=='dossiers' else '' }}"><i class="fas fa-folder"></i> Dossiers</a>
    <a href="/documents" class="{{ 'active' if active=='documents' else '' }}"><i class="fas fa-file-alt"></i> Documents</a>
    <a href="/recherche" class="{{ 'active' if active=='recherche' else '' }}"><i class="fas fa-search"></i> Recherche</a>
    {% if current_user.role in ['admin','archiviste','contributeur'] %}
    <a href="/upload" class="{{ 'active' if active=='upload' else '' }}"><i class="fas fa-upload"></i> Upload</a>
    {% endif %}
    {% if current_user.role in ['admin','archiviste'] %}
    <a href="/workflow" class="{{ 'active' if active=='workflow' else '' }}"><i class="fas fa-check-double"></i> Validations</a>
    <a href="/cycle-vie" class="{{ 'active' if active=='cycle' else '' }}"><i class="fas fa-recycle"></i> Cycle de vie</a>
    {% endif %}
    {% if current_user.role in ['admin','auditeur'] %}
    <a href="/audit" class="{{ 'active' if active=='audit' else '' }}"><i class="fas fa-history"></i> Audit RGPD</a>
    {% endif %}
    {% if current_user.role in ['admin','archiviste'] %}
    <a href="/statistiques" class="{{ 'active' if active=='stats' else '' }}"><i class="fas fa-chart-line"></i> Statistiques</a>
    {% endif %}
    {% if current_user.role == 'admin' %}
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
  <div>&copy; 2026 <strong>OMEGA GED</strong> — Tous droits réservés</div>
  <div class="footer-sub">
    <i class="fas fa-code"></i> Développé par <strong>OMEGA INFORMATIQUE</strong> — Archivage conforme ISO 15489 · Dakar, Sénégal · UEMOA
  </div>
</footer>

</body>
</html>
"""


def render_page(content, active='dashboard', page_title='Omega GED'):
    page = HTML_BASE.replace("{% block content %}{% endblock %}", content)
    return render_template_string(page, active=active, page_title=page_title, current_user=current_user)


# ==================== HEALTHCHECK ====================
@app.route('/health')
def health():
    return jsonify(status='ok', service='ged-omega', timestamp=datetime.now().isoformat())


# ==================== DASHBOARD ====================
@app.route('/')
def index():
    if not (current_user and current_user.is_authenticated):
        return redirect('/login')

    conn = get_db()
    c = conn.cursor()

    try:
        c.execute("SELECT COUNT(*) FROM documents WHERE actif=1")
        row = c.fetchone()
        total_docs = row[0] if row else 0

        c.execute("SELECT COUNT(*) FROM dossiers WHERE actif=1")
        row = c.fetchone()
        total_dossiers = row[0] if row else 0

        c.execute("SELECT COALESCE(SUM(fichier_taille_ko), 0) FROM documents WHERE actif=1")
        row = c.fetchone()
        taille_totale = row[0] if row else 0

        c.execute("SELECT COUNT(*) FROM documents WHERE actif=1 AND statut='Brouillon'")
        row = c.fetchone()
        brouillons = row[0] if row else 0

        c.execute("SELECT COUNT(*) FROM documents WHERE actif=1 AND statut='En validation'")
        row = c.fetchone()
        en_validation = row[0] if row else 0

        c.execute("SELECT COUNT(*) FROM documents WHERE actif=1 AND statut='Publié'")
        row = c.fetchone()
        publies = row[0] if row else 0

        c.execute("SELECT COUNT(*) FROM documents WHERE actif=1 AND confidentiel=1")
        row = c.fetchone()
        confidentiels = row[0] if row else 0

        c.execute("""SELECT d.*, cat.nom as cat_nom, cat.couleur as cat_couleur,
                            u.nom as auteur_nom, u.prenom as auteur_prenom
                     FROM documents d
                     LEFT JOIN categories cat ON d.categorie_id = cat.id
                     LEFT JOIN utilisateurs u ON d.auteur_id = u.id
                     WHERE d.actif=1
                     ORDER BY d.date_upload DESC LIMIT 8""")
        docs_recents = c.fetchall()

        c.execute("""SELECT d.*,
                     (SELECT COUNT(*) FROM documents WHERE dossier_id = d.id AND actif=1) as nb_docs,
                     (SELECT COUNT(*) FROM dossiers WHERE parent_id = d.id AND actif=1) as nb_sous
                     FROM dossiers d
                     WHERE d.parent_id IS NULL AND d.actif=1
                     ORDER BY d.ordre, d.nom LIMIT 8""")
        dossiers_racine = c.fetchall()

        c.execute("""SELECT d.*, cat.nom as cat_nom
                     FROM documents d
                     LEFT JOIN categories cat ON d.categorie_id = cat.id
                     WHERE d.actif=1 AND d.date_destruction_prevue IS NOT NULL
                       AND date(d.date_destruction_prevue) <= date('now', '+30 days')
                     ORDER BY d.date_destruction_prevue ASC LIMIT 5""")
        alertes_destruction = c.fetchall()

        c.execute("""SELECT cat.nom, cat.couleur, COUNT(d.id) as nb,
                            COALESCE(SUM(d.fichier_taille_ko), 0) as taille
                     FROM categories cat
                     LEFT JOIN documents d ON d.categorie_id = cat.id AND d.actif=1
                     WHERE cat.actif=1
                     GROUP BY cat.id HAVING nb > 0
                     ORDER BY nb DESC LIMIT 8""")
        par_categorie = c.fetchall()

        c.execute("""SELECT a.*, u.nom as user_nom, u.prenom as user_prenom
                     FROM audit_log a
                     LEFT JOIN utilisateurs u ON a.user_id = u.id
                     ORDER BY a.created_at DESC LIMIT 8""")
        activite_recente = c.fetchall()

        conn.close()

        role_badge = f"badge-role-{current_user.role}"
        taille_str = format_taille(taille_totale)

        content = f"""
        <div class="hero">
          <h1>Bienvenue <span>{current_user.prenom}</span> 👋</h1>
          <p>Plateforme GED conforme ISO 15489 et NF Z42-013 — Gestion documentaire sécurisée</p>
          <div class="certifs">
            <span>ISO 15489 Records</span>
            <span>NF Z42-013</span>
            <span>RGPD</span>
            <span>UEMOA 8 pays</span>
          </div>
        </div>

        <div class="kpi-grid">
          <div class="kpi-card" style="border-top-color:#06b6d4">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#0e7490,#06b6d4)">
              <i class="fas fa-file-alt"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Documents</div>
              <div class="kpi-value">{total_docs}</div>
              <div class="kpi-sub">{publies} publiés · {brouillons} brouillons</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#10b981">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#10b981,#22c55e)">
              <i class="fas fa-folder"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Dossiers</div>
              <div class="kpi-value">{total_dossiers}</div>
              <div class="kpi-sub">Structure arborescente</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#f59e0b">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#d97706,#f59e0b)">
              <i class="fas fa-database"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Espace utilisé</div>
              <div class="kpi-value">{taille_str}</div>
              <div class="kpi-sub">Total documents actifs</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#7c3aed">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#7c3aed,#a855f7)">
              <i class="fas fa-check-double"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">En validation</div>
              <div class="kpi-value">{en_validation}</div>
              <div class="kpi-sub">Workflow en cours</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#dc2626">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#dc2626,#ef4444)">
              <i class="fas fa-lock"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Confidentiels</div>
              <div class="kpi-value">{confidentiels}</div>
              <div class="kpi-sub">Accès restreint</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#0891b2">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#0891b2,#06b6d4)">
              <i class="fas fa-clock"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">À détruire</div>
              <div class="kpi-value">{len(alertes_destruction)}</div>
              <div class="kpi-sub">Dans 30 jours</div>
            </div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="card">
            <div class="card-header">
              <h3><i class="fas fa-folder-open"></i> Dossiers racines</h3>
              <a href="/dossiers" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Voir tout</a>
            </div>
        """
        for d in dossiers_racine:
            content += f"""
            <a href="/dossiers/{d['id']}" class="dossier-item">
              <div class="dossier-icon"><i class="fas fa-folder"></i></div>
              <div class="dossier-info">
                <div class="dossier-nom">{d['nom'][:40]}</div>
                <div class="dossier-meta">{d['nb_docs']} document(s) · {d['nb_sous']} sous-dossier(s)</div>
              </div>
              <i class="fas fa-chevron-right" style="color:#94a3b8"></i>
            </a>
            """
        if not dossiers_racine:
            content += '<div class="empty" style="padding:20px"><i class="fas fa-folder-open"></i><br>Aucun dossier</div>'

        content += """
          </div>

          <div class="card">
            <div class="card-header">
              <h3><i class="fas fa-chart-pie"></i> Documents par catégorie</h3>
            </div>
        """
        max_nb = max([c_['nb'] for c_ in par_categorie], default=1) if par_categorie else 1
        for cat in par_categorie:
            pct = (cat['nb'] / max_nb * 100) if max_nb else 0
            content += f"""
            <div style="margin-bottom:12px">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="font-weight:700;font-size:0.85rem">
                  <i class="fas fa-circle" style="color:{cat['couleur'] or '#06b6d4'};font-size:0.7rem"></i>
                  {cat['nom'][:25]}
                </span>
                <strong style="color:#0e7490">{cat['nb']} docs · {format_taille(cat['taille'])}</strong>
              </div>
              <div style="background:#f0fdff;border-radius:6px;height:8px;overflow:hidden">
                <div style="background:{cat['couleur'] or '#06b6d4'};height:100%;width:{pct}%"></div>
              </div>
            </div>
            """
        if not par_categorie:
            content += '<div class="empty" style="padding:20px">Aucune donnée</div>'

        content += """
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-clock-rotate-left"></i> Documents récents</h3>
            <a href="/documents" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Voir tout</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Type</th><th>Référence</th><th>Titre</th>
                  <th>Catégorie</th><th>Auteur</th><th>Taille</th><th>Date</th><th>Statut</th>
                </tr>
              </thead>
              <tbody>
        """
        for d in docs_recents:
            ext = (d['extension'] or '').lower()
            icon_color = '#dc2626'
            icon_name = 'fa-file-pdf'
            if ext in ['doc', 'docx']:
                icon_color = '#2563eb'
                icon_name = 'fa-file-word'
            elif ext in ['xls', 'xlsx']:
                icon_color = '#059669'
                icon_name = 'fa-file-excel'
            elif ext in ['jpg', 'jpeg', 'png', 'gif', 'svg']:
                icon_color = '#a855f7'
                icon_name = 'fa-file-image'
            elif ext in ['zip', 'rar', '7z']:
                icon_color = '#f59e0b'
                icon_name = 'fa-file-archive'
            elif ext in ['dwg', 'dxf']:
                icon_color = '#0891b2'
                icon_name = 'fa-drafting-compass'

            badge = 'badge-info'
            if d['statut'] == 'Publié': badge = 'badge-success'
            elif d['statut'] == 'En validation': badge = 'badge-warning'
            elif d['statut'] == 'Archivé': badge = 'badge-primary'
            elif d['statut'] == 'Brouillon': badge = 'badge-info'

            content += f"""
            <tr>
              <td><div class="doc-icon" style="background:{icon_color}"><i class="fas {icon_name}"></i></div></td>
              <td><strong>{d['reference']}</strong></td>
              <td>
                <div style="font-weight:700">{d['titre'][:45]}</div>
                {('🔒 Confidentiel' if d['confidentiel'] else '')}
              </td>
              <td><span class="badge" style="background:{d['cat_couleur'] or '#06b6d4'}20;color:{d['cat_couleur'] or '#0e7490'}">{d['cat_nom'] or '-'}</span></td>
              <td>{d['auteur_prenom'] or '?'} {d['auteur_nom'] or ''}</td>
              <td>{format_taille(d['fichier_taille_ko'])}</td>
              <td>{d['date_upload'][:10]}</td>
              <td><span class="badge {badge}">{d['statut']}</span></td>
            </tr>
            """
        if not docs_recents:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-file-alt"></i><br>Aucun document</td></tr>'

        content += """
              </tbody>
            </table>
          </div>
        </div>
        """

        if alertes_destruction:
            content += """
            <div class="card" style="border-left:5px solid #dc2626">
              <div class="card-header"><h3 style="color:#991b1b"><i class="fas fa-hourglass-half"></i> Documents à détruire (30 jours)</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Référence</th><th>Titre</th><th>Catégorie</th><th>Date destruction prévue</th></tr></thead>
                  <tbody>
            """
            for a in alertes_destruction:
                content += f"""
                <tr>
                  <td><strong>{a['reference']}</strong></td>
                  <td>{a['titre'][:50]}</td>
                  <td>{a['cat_nom'] or '-'}</td>
                  <td><span class="badge badge-danger">{a['date_destruction_prevue']}</span></td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        if activite_recente:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-history"></i> Activité récente</h3></div>
            """
            for a in activite_recente:
                content += f"""
                <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px dashed #f0fdff">
                  <div>
                    <strong style="font-size:0.85rem">{a['user_prenom'] or '?'} {a['user_nom'] or ''}</strong>
                    <div style="font-size:0.8rem;color:#475569">{a['action']} — {a['details'] or ''}</div>
                  </div>
                  <small style="color:#94a3b8">{a['created_at'][:16]}</small>
                </div>
                """
            content += "</div>"

        return render_page(content, active='dashboard', page_title='Dashboard GED')

    except Exception as e:
        import traceback
        traceback.print_exc()
        conn.close()
        flash(f"Erreur : {e}", "danger")
        return redirect('/login')


# ==================== INIT CRUD ====================
try:
    from crud import init_crud
    init_crud(app, get_db=get_db, render_page=render_page,
              format_taille=format_taille, log_action=log_action)
except Exception as e:
    print(f"[CRUD] ⚠️ {e}")


# ==================== INIT GED LOGIC ====================
try:
    from ged_logic import init_ged
    init_ged(app, get_db=get_db, render_page=render_page,
             format_taille=format_taille, log_action=log_action,
             UPLOAD_FOLDER=UPLOAD_FOLDER, ARCHIVE_FOLDER=ARCHIVE_FOLDER)
except Exception as e:
    print(f"[GED] ⚠️ {e}")


# ==================== INIT PORTAIL ====================
try:
    from portail import init_portail
    init_portail(app, get_db=get_db, render_page=render_page,
                 format_taille=format_taille, log_action=log_action)
except Exception as e:
    print(f"[PORTAIL] ⚠️ {e}")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
