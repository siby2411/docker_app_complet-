"""
🏦 MicroFinance 2.0 — Application principale
Dashboard SFD · Clients · Crédits · Épargne · Mobile Money
Design turquoise BCEAO
"""
from flask import Flask, render_template_string, request, redirect, flash, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'microfinance_2_2026_premium_secret_bceao'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

DB_PATH = "/app/data/microfinance.db"

try:
    from auth import (init_auth, log_action, admin_required, direction_required,
                      staff_required, audit_required, role_required)
    AUTH_OK = True
except Exception as e:
    print(f"[AUTH] ⚠️ {e}")
    AUTH_OK = False
    def admin_required(f): return f
    direction_required = staff_required = audit_required = admin_required
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


def fmt_pct(v):
    if v is None:
        return "0%"
    return f"{v:.1f}%"


def fmt_date(d):
    if not d:
        return "-"
    return d[:10] if len(d) >= 10 else d


# ==================== DESIGN TURQUOISE BCEAO ====================
HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MicroFinance — {{ page_title or 'SFD' }}</title>
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
.badge-purple{background:#ede9fe;color:#6d28d9}
.badge-role-admin{background:linear-gradient(135deg,#dc2626,#ef4444);color:white}
.badge-role-directeur{background:linear-gradient(135deg,#7c3aed,#a855f7);color:white}
.badge-role-agent{background:linear-gradient(135deg,#0e7490,#06b6d4);color:white}
.badge-role-caissier{background:linear-gradient(135deg,#10b981,#22c55e);color:white}
.badge-role-analyste{background:linear-gradient(135deg,#f59e0b,#fbbf24);color:white}
.badge-role-auditeur{background:linear-gradient(135deg,#0891b2,#06b6d4);color:white}

.flash{padding:15px 20px;border-radius:12px;margin-bottom:18px;display:flex;align-items:center;gap:12px;font-size:0.9rem;font-weight:600}
.flash-success{background:#d1fae5;color:#065f46;border-left:5px solid #10b981}
.flash-danger{background:#fee2e2;color:#991b1b;border-left:5px solid #dc2626}
.flash-warning{background:#fef3c7;color:#92400e;border-left:5px solid #f59e0b}
.flash-info{background:#dbeafe;color:#1e40af;border-left:5px solid #3b82f6}

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
  <span><i class="fas fa-building-columns"></i> <strong>MICROFINANCE 2.0</strong> — Système Financier Décentralisé</span>
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <span class="certif">BCEAO</span>
    <span class="certif">UEMOA</span>
    <span class="certif">LCB-FT</span>
    <span class="certif">RGPD</span>
  </div>
</div>

<header class="header">
  <div class="logo-section">
    <div class="logo-icon"><i class="fas fa-building-columns"></i></div>
    <div>
      <h1>MICRO<span>FINANCE</span></h1>
      <div class="subtitle"><i class="fas fa-shield-halved"></i> Conforme BCEAO</div>
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
    <a href="/clients" class="{{ 'active' if active=='clients' else '' }}"><i class="fas fa-users"></i> Clients</a>
    <a href="/credits" class="{{ 'active' if active=='credits' else '' }}"><i class="fas fa-hand-holding-dollar"></i> Crédits</a>
    <a href="/epargne" class="{{ 'active' if active=='epargne' else '' }}"><i class="fas fa-piggy-bank"></i> Épargne</a>
    {% if current_user.role in ['admin','directeur','agent','analyste'] %}
    <a href="/demandes" class="{{ 'active' if active=='demandes' else '' }}"><i class="fas fa-file-signature"></i> Demandes</a>
    {% endif %}
    {% if current_user.role in ['admin','directeur','caissier','agent'] %}
    <a href="/remboursements" class="{{ 'active' if active=='remboursements' else '' }}"><i class="fas fa-money-bill-wave"></i> Remboursements</a>
    {% endif %}
    {% if current_user.role in ['admin','directeur','agent'] %}
    <a href="/recouvrement" class="{{ 'active' if active=='recouvrement' else '' }}"><i class="fas fa-phone"></i> Recouvrement</a>
    {% endif %}
    {% if current_user.role in ['admin','directeur','analyste'] %}
    <a href="/scoring" class="{{ 'active' if active=='scoring' else '' }}"><i class="fas fa-robot"></i> Scoring IA</a>
    {% endif %}
    {% if current_user.role in ['admin','directeur','caissier'] %}
    <a href="/mobile-money" class="{{ 'active' if active=='mm' else '' }}"><i class="fas fa-mobile-screen"></i> Mobile Money</a>
    {% endif %}
    {% if current_user.role in ['admin','auditeur'] %}
    <a href="/lcb-ft" class="{{ 'active' if active=='lcb' else '' }}"><i class="fas fa-shield-halved"></i> LCB-FT</a>
    <a href="/audit" class="{{ 'active' if active=='audit' else '' }}"><i class="fas fa-history"></i> Audit</a>
    {% endif %}
    {% if current_user.role in ['admin','directeur'] %}
    <a href="/rapports" class="{{ 'active' if active=='rapports' else '' }}"><i class="fas fa-file-invoice"></i> Rapports BCEAO</a>
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
  <div>&copy; 2026 <strong>MICROFINANCE 2.0</strong> — Tous droits réservés</div>
  <div class="footer-sub">
    <i class="fas fa-code"></i> Développé par <strong>OMEGA INFORMATIQUE</strong> · Dakar, Sénégal · UEMOA
  </div>
</footer>

</body>
</html>
"""


def render_page(content, active='dashboard', page_title='MicroFinance'):
    page = HTML_BASE.replace("{% block content %}{% endblock %}", content)
    return render_template_string(page, active=active, page_title=page_title,
                                  current_user=current_user)


# ==================== HEALTHCHECK ====================
@app.route('/health')
def health():
    return jsonify(status='ok', service='microfinance-2', version='2.0',
                   timestamp=datetime.now().isoformat())


# ==================== DASHBOARD ====================
@app.route('/')
def index():
    if not (current_user and current_user.is_authenticated):
        return redirect('/login')

    conn = get_db()
    c = conn.cursor()

    try:
        # KPI 1 : Clients
        c.execute("SELECT COUNT(*) FROM clients WHERE actif=1")
        total_clients = c.fetchone()[0] or 0

        c.execute("SELECT COUNT(*) FROM clients WHERE actif=1 AND kyc_statut='Validé'")
        clients_kyc = c.fetchone()[0] or 0

        # KPI 2 : Crédits actifs
        c.execute("SELECT COUNT(*) FROM credits WHERE statut='Actif'")
        credits_actifs = c.fetchone()[0] or 0

        # KPI 3 : Encours total
        c.execute("SELECT COALESCE(SUM(solde_restant), 0) FROM credits WHERE statut='Actif'")
        encours_total = c.fetchone()[0] or 0

        # KPI 4 : Échéances en retard
        c.execute("SELECT COUNT(*) FROM echeances_credit WHERE statut IN ('En retard', 'Impayé')")
        echeances_retard = c.fetchone()[0] or 0

        c.execute("""SELECT COALESCE(SUM(montant_restant), 0) FROM echeances_credit
                     WHERE statut IN ('En retard', 'Impayé')""")
        montant_retard = c.fetchone()[0] or 0

        # KPI 5 : Demandes en attente
        c.execute("SELECT COUNT(*) FROM demandes_credit WHERE statut='En analyse'")
        demandes_attente = c.fetchone()[0] or 0

        # KPI 6 : Épargne totale
        c.execute("SELECT COALESCE(SUM(solde), 0) FROM comptes_epargne WHERE statut='Actif'")
        epargne_total = c.fetchone()[0] or 0

        # KPI 7 : Transactions Mobile Money (mois)
        mois = datetime.now().strftime('%Y-%m')
        c.execute("""SELECT COUNT(*), COALESCE(SUM(montant), 0) FROM transactions_mobile
                     WHERE strftime('%Y-%m', date_initiation)=? AND statut='Réussi'""", (mois,))
        row = c.fetchone()
        mm_count = row[0] or 0
        mm_montant = row[1] or 0

        # KPI 8 : Déclarations LCB-FT
        c.execute("SELECT COUNT(*) FROM declarations_soupcon WHERE statut='À analyser'")
        declarations_lcb = c.fetchone()[0] or 0

        # Échéances du jour
        today = datetime.now().date().isoformat()
        c.execute("""SELECT ec.*, cr.reference AS credit_ref,
                            cl.nom AS client_nom, cl.prenom AS client_prenom,
                            cl.telephone AS client_tel, a.nom AS agence_nom
                     FROM echeances_credit ec
                     INNER JOIN credits cr ON ec.credit_id = cr.id
                     INNER JOIN clients cl ON cr.client_id = cl.id
                     LEFT JOIN agences a ON cr.agence_id = a.id
                     WHERE date(ec.date_echeance) <= date(?)
                       AND ec.statut IN ('À venir', 'En retard')
                       AND cr.statut = 'Actif'
                     ORDER BY ec.date_echeance ASC LIMIT 10""", (today,))
        echeances_jour = c.fetchall()

        # Top agences
        c.execute("""SELECT a.nom, a.code,
                            (SELECT COUNT(*) FROM clients WHERE agence_id=a.id AND actif=1) AS nb_clients,
                            (SELECT COALESCE(SUM(montant_principal), 0) FROM credits WHERE agence_id=a.id AND statut='Actif') AS encours
                     FROM agences a WHERE a.actif=1 ORDER BY encours DESC LIMIT 5""")
        top_agences = c.fetchall()

        # Répartition par produit
        c.execute("""SELECT p.nom, p.code,
                            COUNT(cr.id) AS nb,
                            COALESCE(SUM(cr.montant_principal), 0) AS total
                     FROM produits p
                     LEFT JOIN credits cr ON cr.produit_id = p.id AND cr.statut='Actif'
                     WHERE p.actif=1
                     GROUP BY p.id HAVING nb > 0
                     ORDER BY total DESC""")
        par_produit = c.fetchall()

        # Activité récente
        c.execute("""SELECT a.*, u.nom AS user_nom, u.prenom AS user_prenom
                     FROM audit_log a
                     LEFT JOIN utilisateurs u ON a.user_id = u.id
                     ORDER BY a.created_at DESC LIMIT 6""")
        activite = c.fetchall()

        conn.close()

        content = f"""
        <div class="hero">
          <h1>Bonjour <span>{current_user.prenom}</span> 🏦</h1>
          <p>Plateforme SFD conforme BCEAO — Gestion clients, crédits, épargne et mobile money</p>
          <div class="certifs">
            <span>BCEAO</span>
            <span>UEMOA</span>
            <span>LCB-FT</span>
            <span>RGPD</span>
          </div>
        </div>

        <div class="kpi-grid">
          <div class="kpi-card" style="border-top-color:#06b6d4">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#0e7490,#06b6d4)">
              <i class="fas fa-users"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Clients</div>
              <div class="kpi-value">{total_clients}</div>
              <div class="kpi-sub">{clients_kyc} KYC validés</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#10b981">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#10b981,#22c55e)">
              <i class="fas fa-hand-holding-dollar"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Crédits actifs</div>
              <div class="kpi-value">{credits_actifs}</div>
              <div class="kpi-sub">{fmt_fcfa(encours_total)}</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#7c3aed">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#7c3aed,#a855f7)">
              <i class="fas fa-piggy-bank"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Épargne</div>
              <div class="kpi-value" style="font-size:1.3rem">{fmt_fcfa(epargne_total)}</div>
              <div class="kpi-sub">Total comptes</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#dc2626">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#dc2626,#ef4444)">
              <i class="fas fa-triangle-exclamation"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Impayés</div>
              <div class="kpi-value">{echeances_retard}</div>
              <div class="kpi-sub">{fmt_fcfa(montant_retard)}</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#f59e0b">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#d97706,#fbbf24)">
              <i class="fas fa-file-signature"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Demandes</div>
              <div class="kpi-value">{demandes_attente}</div>
              <div class="kpi-sub">En analyse</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#0891b2">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#0891b2,#06b6d4)">
              <i class="fas fa-mobile-screen"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Mobile Money (mois)</div>
              <div class="kpi-value" style="font-size:1.3rem">{fmt_fcfa(mm_montant)}</div>
              <div class="kpi-sub">{mm_count} transactions</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#dc2626">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#991b1b,#dc2626)">
              <i class="fas fa-shield-halved"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">LCB-FT</div>
              <div class="kpi-value">{declarations_lcb}</div>
              <div class="kpi-sub">À analyser</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#16a34a">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#16a34a,#22c55e)">
              <i class="fas fa-percent"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Taux recouvrement</div>
              <div class="kpi-value">{100 - (echeances_retard * 100 / max(credits_actifs, 1)):.1f}%</div>
              <div class="kpi-sub">Portefeuille sain</div>
            </div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="card">
            <div class="card-header">
              <h3><i class="fas fa-calendar-day"></i> Échéances à traiter</h3>
              <a href="/remboursements" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Voir</a>
            </div>
        """
        for e in echeances_jour:
            badge = 'badge-danger' if e['jours_retard'] and e['jours_retard'] > 0 else 'badge-warning'
            retard_txt = f"+{e['jours_retard']}j" if e['jours_retard'] and e['jours_retard'] > 0 else "Aujourd'hui"
            content += f"""
            <div style="padding:12px 0;border-bottom:1px dashed #f0fdff;display:flex;justify-content:space-between;align-items:center">
              <div>
                <div style="font-weight:700;font-size:0.9rem">{e['client_prenom']} {e['client_nom']}</div>
                <div style="font-size:0.72rem;color:#94a3b8">
                  {e['credit_ref']} · {e['agence_nom'] or '-'} · {e['client_tel'] or ''}
                </div>
              </div>
              <div style="text-align:right">
                <div style="font-weight:900;color:#0e7490">{fmt_fcfa(e['montant_restant'])}</div>
                <span class="badge {badge}">{retard_txt}</span>
              </div>
            </div>"""
        if not echeances_jour:
            content += '<div class="empty" style="padding:20px"><i class="fas fa-check-circle" style="color:#10b981"></i><br>Aucune échéance</div>'
        content += "</div>"

        content += """
          <div class="card">
            <div class="card-header"><h3><i class="fas fa-trophy"></i> Top agences</h3></div>
        """
        for a in top_agences:
            content += f"""
            <div style="padding:12px 0;border-bottom:1px dashed #f0fdff">
              <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                <span style="font-weight:700">{a['nom']}</span>
                <strong style="color:#0e7490">{fmt_fcfa(a['encours'])}</strong>
              </div>
              <div style="font-size:0.75rem;color:#94a3b8">
                <i class="fas fa-users"></i> {a['nb_clients']} clients
              </div>
            </div>"""
        content += "</div></div>"

        # Répartition produits
        if par_produit:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-chart-pie"></i> Portefeuille par produit</h3></div>
            """
            max_total = max([p['total'] for p in par_produit], default=1)
            for p in par_produit:
                pct = (p['total'] / max_total * 100) if max_total else 0
                content += f"""
                <div style="margin-bottom:14px">
                  <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                    <span style="font-weight:700;font-size:0.85rem">{p['nom']}</span>
                    <strong style="color:#0e7490">{p['nb']} crédits · {fmt_fcfa(p['total'])}</strong>
                  </div>
                  <div style="background:#f0fdff;border-radius:6px;height:8px;overflow:hidden">
                    <div style="background:linear-gradient(90deg,#0e7490,#22d3ee);height:100%;width:{pct}%"></div>
                  </div>
                </div>"""
            content += "</div>"

        # Activité
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

        return render_page(content, active='dashboard', page_title='Dashboard SFD')

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
    from microfinance_logic import init_microfinance
    init_microfinance(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[LOGIC] ✅ Module logique enregistré")
except Exception as e:
    print(f"[LOGIC] ⚠️ {e}")

try:
    from scoring import init_scoring
    init_scoring(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[SCORING] ✅ Module scoring IA enregistré")
except Exception as e:
    print(f"[SCORING] ⚠️ {e}")

try:
    from mobile_money import init_mobile_money
    init_mobile_money(app, get_db=get_db, render_page=render_page, log_action=log_action)
    print("[MM] ✅ Module mobile money enregistré")
except Exception as e:
    print(f"[MM] ⚠️ {e}")

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
