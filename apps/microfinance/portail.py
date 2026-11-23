"""
🌐 MicroFinance 2.0 — Portail public
Consultation anonyme : agences, produits, taux
"""
from flask import Blueprint, render_template_string, request, redirect, jsonify
import sqlite3
from datetime import datetime

portail_bp = Blueprint('portail', __name__)
_deps = {}


def init_portail(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(portail_bp)
    print("[PORTAIL] ✅ Module portail complet enregistré")


def _db():
    return _deps['get_db']()


def _fmt_fcfa(m):
    if not m:
        return "0 F"
    return f"{int(m):,} F".replace(",", " ")


@portail_bp.route('/portail')
def portail_index():
    conn = _db()
    c = conn.cursor()

    # Agences publiques
    c.execute("""SELECT a.*, r.nom AS region_nom
                 FROM agences a
                 LEFT JOIN regions r ON a.region_id = r.id
                 WHERE a.actif=1 ORDER BY a.nom""")
    agences = c.fetchall()

    # Produits crédit
    c.execute("""SELECT * FROM produits WHERE actif=1 AND categorie='Crédit' ORDER BY nom""")
    produits = c.fetchall()

    # Stats anonymes
    c.execute("SELECT COUNT(*) FROM clients WHERE actif=1")
    nb_clients = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM credits WHERE statut='Actif'")
    nb_credits = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM comptes_epargne WHERE statut='Actif'")
    nb_comptes = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(solde_restant), 0) FROM credits WHERE statut='Actif'")
    encours = c.fetchone()[0] or 0

    conn.close()

    content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MicroFinance — Portail public</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}}
body{{background:#f0fdff;color:#0e7490;min-height:100vh}}

.hero{{background:linear-gradient(135deg,#0e7490 0%,#06b6d4 50%,#22d3ee 100%);color:white;padding:80px 30px 60px;text-align:center;position:relative;overflow:hidden}}
.hero::before{{content:'';position:absolute;top:-100px;right:-100px;width:400px;height:400px;background:rgba(165,243,252,0.15);border-radius:50%}}
.hero::after{{content:'';position:absolute;bottom:-120px;left:-80px;width:320px;height:320px;background:rgba(165,243,252,0.1);border-radius:50%}}
.hero h1{{font-size:3rem;font-weight:900;letter-spacing:-1.5px;margin-bottom:15px;position:relative;z-index:1}}
.hero h1 span{{color:#a5f3fc}}
.hero p{{font-size:1.15rem;opacity:0.95;max-width:650px;margin:0 auto 30px;position:relative;z-index:1}}
.hero .badges{{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;position:relative;z-index:1}}
.hero .badges span{{background:rgba(255,255,255,0.15);padding:8px 18px;border-radius:20px;font-size:0.85rem;font-weight:800;backdrop-filter:blur(10px)}}

.container{{max-width:1300px;margin:0 auto;padding:50px 25px}}

.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin-bottom:50px}}
.stat{{background:white;border-radius:18px;padding:28px;text-align:center;box-shadow:0 6px 20px rgba(14,116,144,0.08);border-top:4px solid #06b6d4;transition:0.3s}}
.stat:hover{{transform:translateY(-4px);box-shadow:0 12px 30px rgba(14,116,144,0.15)}}
.stat .v{{font-size:2.5rem;font-weight:900;color:#0e7490;line-height:1;letter-spacing:-1px}}
.stat .l{{font-size:0.8rem;color:#64748b;text-transform:uppercase;font-weight:800;letter-spacing:1.5px;margin-top:10px}}

h2{{font-size:1.6rem;color:#0e7490;font-weight:900;margin-bottom:25px;display:flex;align-items:center;gap:12px}}
h2 i{{color:#06b6d4}}

.agences-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px;margin-bottom:50px}}
.agence-card{{background:white;border-radius:18px;padding:24px;box-shadow:0 6px 20px rgba(14,116,144,0.08);border-left:5px solid #06b6d4;transition:0.3s}}
.agence-card:hover{{transform:translateY(-4px);box-shadow:0 12px 30px rgba(14,116,144,0.15)}}
.agence-card .head{{display:flex;align-items:center;gap:12px;margin-bottom:15px}}
.agence-card .icon{{width:50px;height:50px;background:linear-gradient(135deg,#0e7490,#06b6d4);border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-size:1.4rem;flex-shrink:0}}
.agence-card .nom{{font-size:1.1rem;font-weight:900;color:#0e7490}}
.agence-card .type{{font-size:0.8rem;color:#94a3b8;text-transform:uppercase;font-weight:700;letter-spacing:1px}}
.agence-card .infos{{font-size:0.85rem;color:#475569;line-height:1.8;margin-top:15px;padding-top:15px;border-top:1px solid #f0fdff}}
.agence-card .infos i{{color:#06b6d4;width:20px}}

.produits-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}}
.produit-card{{background:white;border-radius:18px;padding:24px;box-shadow:0 6px 20px rgba(14,116,144,0.08);border-left:5px solid #10b981;transition:0.3s}}
.produit-card:hover{{transform:translateY(-4px);box-shadow:0 12px 30px rgba(16,185,129,0.15)}}
.produit-card .nom{{font-size:1.1rem;font-weight:900;color:#065f46;margin-bottom:10px}}
.produit-card .cat{{font-size:0.8rem;color:#94a3b8;text-transform:uppercase;font-weight:700;letter-spacing:1px}}
.produit-card .montant{{font-size:1.3rem;font-weight:900;color:#10b981;margin-top:15px}}
.produit-card .details{{font-size:0.8rem;color:#64748b;line-height:1.8;margin-top:10px}}
.produit-card .details strong{{color:#0e7490}}

footer{{background:linear-gradient(135deg,#0e7490,#155e75);color:white;padding:50px 20px;text-align:center;margin-top:60px;position:relative}}
footer::before{{content:'';position:absolute;top:0;left:0;right:0;height:5px;background:linear-gradient(90deg,#fbbf24,#dc2626,#fbbf24)}}
footer strong{{color:#a5f3fc}}
footer .sub{{font-size:0.8rem;opacity:0.75;margin-top:10px}}

.cta{{text-align:center;padding:50px 20px;background:white;border-radius:24px;box-shadow:0 10px 30px rgba(14,116,144,0.08)}}
.cta h3{{font-size:1.6rem;color:#0e7490;margin-bottom:15px}}
.cta p{{color:#64748b;margin-bottom:25px;max-width:600px;margin-left:auto;margin-right:auto;line-height:1.6}}
.cta .btn{{display:inline-block;padding:15px 40px;background:linear-gradient(135deg,#0e7490,#06b6d4);color:white;text-decoration:none;border-radius:12px;font-weight:800;font-size:1rem;box-shadow:0 8px 24px rgba(14,116,144,0.35);transition:0.3s}}
.cta .btn:hover{{transform:translateY(-2px);box-shadow:0 12px 32px rgba(14,116,144,0.45)}}
</style>
</head>
<body>

<div class="hero">
  <h1>MICRO<span>FINANCE</span></h1>
  <p>Institution de microfinance agréée BCEAO — Crédits, épargne et mobile money au service de l'inclusion financière</p>
  <div class="badges">
    <span>✅ Agréé BCEAO</span>
    <span>🇸🇳 Sénégal</span>
    <span>🌍 UEMOA</span>
    <span>🔒 LCB-FT</span>
  </div>
</div>

<div class="container">

  <div class="stats">
    <div class="stat">
      <div class="v">{nb_clients}</div>
      <div class="l">Clients actifs</div>
    </div>
    <div class="stat">
      <div class="v">{nb_credits}</div>
      <div class="l">Crédits en cours</div>
    </div>
    <div class="stat">
      <div class="v">{nb_comptes}</div>
      <div class="l">Comptes épargne</div>
    </div>
    <div class="stat">
      <div class="v" style="font-size:1.5rem">{_fmt_fcfa(encours)}</div>
      <div class="l">Encours crédits</div>
    </div>
  </div>

  <h2><i class="fas fa-building"></i> Nos agences</h2>
  <div class="agences-grid">
"""

    for a in agences:
        content += f"""
    <div class="agence-card">
      <div class="head">
        <div class="icon"><i class="fas fa-building-columns"></i></div>
        <div>
          <div class="nom">{a['nom']}</div>
          <div class="type">{a['type'] or 'Agence'}</div>
        </div>
      </div>
      <div class="infos">
        <div><i class="fas fa-map-marker-alt"></i> {a['adresse'] or '-'}, {a['ville'] or '-'}</div>
        <div><i class="fas fa-phone"></i> {a['telephone'] or '-'}</div>
        <div><i class="fas fa-map"></i> {a['region_nom'] or '-'}</div>
      </div>
    </div>
"""

    content += """
  </div>

  <h2><i class="fas fa-hand-holding-dollar"></i> Nos produits de crédit</h2>
  <div class="produits-grid">
"""

    for p in produits:
        content += f"""
    <div class="produit-card">
      <div class="cat">{p['categorie'] or 'Crédit'}</div>
      <div class="nom">{p['nom']}</div>
      <div class="montant">{_fmt_fcfa(p['montant_min'])} - {_fmt_fcfa(p['montant_max'])}</div>
      <div class="details">
        <div>⏱️ Durée : <strong>{p['duree_min_mois']} - {p['duree_max_mois']} mois</strong></div>
        <div>💰 Taux : <strong>{p['taux_interet_min']}% - {p['taux_interet_max']}%</strong></div>
        <div>📋 Type : <strong>{p['type_produit'] or 'Standard'}</strong></div>
      </div>
    </div>
"""

    content += """
  </div>

  <div class="cta" style="margin-top:60px">
    <h3><i class="fas fa-handshake"></i> Vous souhaitez devenir client ?</h3>
    <p>Rendez-vous dans l'une de nos agences avec votre pièce d'identité et un justificatif de revenus.
       Nos agents vous accompagneront dans votre projet.</p>
    <a href="/login" class="btn"><i class="fas fa-right-to-bracket"></i> Espace client</a>
  </div>

</div>

<footer>
  <div>&copy; 2026 <strong>MICROFINANCE 2.0</strong> — Tous droits réservés</div>
  <div class="sub">
    <i class="fas fa-code"></i> Développé par <strong>OMEGA INFORMATIQUE</strong> · Dakar, Sénégal · UEMOA · Agréé BCEAO
  </div>
</footer>

</body>
</html>
"""
    return render_template_string(content)


@portail_bp.route('/portail/api/agences')
def portail_api_agences():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT a.id, a.code, a.nom, a.type, a.adresse, a.ville,
                        a.telephone, r.nom AS region
                 FROM agences a
                 LEFT JOIN regions r ON a.region_id = r.id
                 WHERE a.actif=1 ORDER BY a.nom""")
    rows = c.fetchall()
    conn.close()
    return jsonify(agences=[dict(r) for r in rows])


@portail_bp.route('/portail/api/produits')
def portail_api_produits():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT id, code, nom, categorie, type_produit,
                        montant_min, montant_max, duree_min_mois, duree_max_mois,
                        taux_interet_min, taux_interet_max
                 FROM produits WHERE actif=1 ORDER BY nom""")
    rows = c.fetchall()
    conn.close()
    return jsonify(produits=[dict(r) for r in rows])
