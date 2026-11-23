"""
🌐 AgriSénégal V2 — Portail public
Consultation anonyme · Lignes · Prix marché · Statistiques
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

    # Stats publiques
    c.execute("SELECT COUNT(*) FROM producteurs WHERE actif=1")
    nb_producteurs = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM parcelles WHERE actif=1")
    nb_parcelles = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM cultures WHERE actif=1")
    nb_cultures = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(quantite_kg), 0) FROM recoltes")
    prod_totale = c.fetchone()[0]

    # Prix du marché (derniers relevés)
    c.execute("""SELECT pm.*, c.nom AS culture_nom, c.icone, c.nom_wolof
                 FROM prix_marche pm
                 LEFT JOIN cultures c ON pm.culture_id = c.id
                 ORDER BY pm.date_releve DESC LIMIT 12""")
    prix = c.fetchall()

    # Cultures populaires
    c.execute("""SELECT c.nom, c.nom_wolof, c.icone, c.prix_moyen_kg,
                        c.rendement_theorique_t_ha,
                        (SELECT COUNT(*) FROM cultures_parcelles WHERE culture_id=c.id) AS nb_cultivateurs
                 FROM cultures c
                 WHERE c.actif=1
                 ORDER BY nb_cultivateurs DESC LIMIT 12""")
    cultures = c.fetchall()

    conn.close()

    content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AgriSénégal — Portail public</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}}
body{{background:#f0fdf4;color:#065f46;min-height:100vh}}

.hero{{background:linear-gradient(135deg,#065f46 0%,#10b981 50%,#34d399 100%);color:white;padding:80px 30px 60px;text-align:center;position:relative;overflow:hidden}}
.hero::before{{content:'';position:absolute;top:-100px;right:-100px;width:400px;height:400px;background:rgba(255,255,255,0.1);border-radius:50%}}
.hero::after{{content:'';position:absolute;bottom:-120px;left:-80px;width:320px;height:320px;background:rgba(255,255,255,0.08);border-radius:50%}}
.hero h1{{font-size:3rem;font-weight:900;letter-spacing:-1.5px;margin-bottom:15px;position:relative;z-index:1}}
.hero h1 span{{color:#fef3c7}}
.hero p{{font-size:1.15rem;opacity:0.95;max-width:650px;margin:0 auto 30px;position:relative;z-index:1}}
.hero .badges{{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;position:relative;z-index:1}}
.hero .badges span{{background:rgba(255,255,255,0.15);padding:8px 18px;border-radius:20px;font-size:0.85rem;font-weight:800;backdrop-filter:blur(10px)}}

.container{{max-width:1300px;margin:0 auto;padding:50px 25px}}

.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin-bottom:50px}}
.stat{{background:white;border-radius:18px;padding:28px;text-align:center;box-shadow:0 6px 20px rgba(6,95,70,0.08);border-top:4px solid #10b981;transition:0.3s}}
.stat:hover{{transform:translateY(-4px);box-shadow:0 12px 30px rgba(16,185,129,0.15)}}
.stat .v{{font-size:2.8rem;font-weight:900;color:#065f46;line-height:1;letter-spacing:-1px}}
.stat .l{{font-size:0.8rem;color:#64748b;text-transform:uppercase;font-weight:800;letter-spacing:1.5px;margin-top:10px}}

h2{{font-size:1.6rem;color:#065f46;font-weight:900;margin-bottom:25px;display:flex;align-items:center;gap:12px}}
h2 i{{color:#10b981}}

.prix-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:15px;margin-bottom:50px}}
.prix-card{{background:white;border-radius:14px;padding:18px;box-shadow:0 4px 12px rgba(6,95,70,0.08);text-align:center;transition:0.3s}}
.prix-card:hover{{transform:translateY(-3px);box-shadow:0 8px 20px rgba(16,185,129,0.15)}}
.prix-card .nom{{font-weight:800;color:#065f46;margin-bottom:5px}}
.prix-card .wolof{{font-size:0.75rem;color:#94a3b8;font-style:italic}}
.prix-card .prix{{font-size:1.5rem;font-weight:900;color:#10b981;margin-top:10px}}
.prix-card .tendance{{font-size:0.75rem;color:#64748b;margin-top:5px}}

.cultures-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:20px}}
.culture-card{{background:white;border-radius:18px;padding:24px;box-shadow:0 6px 20px rgba(6,95,70,0.08);border-left:5px solid #10b981;transition:0.3s}}
.culture-card:hover{{transform:translateY(-4px);box-shadow:0 12px 30px rgba(16,185,129,0.15)}}
.culture-card .head{{display:flex;align-items:center;gap:12px;margin-bottom:15px}}
.culture-card .icon{{width:50px;height:50px;background:linear-gradient(135deg,#065f46,#10b981);border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-size:1.4rem}}
.culture-card .nom{{font-size:1.15rem;font-weight:900;color:#065f46}}
.culture-card .wolof{{font-size:0.85rem;color:#94a3b8;font-style:italic}}
.culture-card .info{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:15px;padding-top:15px;border-top:1px solid #f0fdf4}}
.culture-card .info .lbl{{font-size:0.7rem;color:#64748b;text-transform:uppercase;font-weight:800}}
.culture-card .info .val{{font-size:1rem;font-weight:800;color:#10b981}}

footer{{background:linear-gradient(135deg,#065f46,#064e3b);color:white;padding:50px 20px;text-align:center;margin-top:60px;position:relative}}
footer::before{{content:'';position:absolute;top:0;left:0;right:0;height:5px;background:linear-gradient(90deg,#fbbf24,#dc2626,#fbbf24)}}
footer strong{{color:#a7f3d0}}
footer .sub{{font-size:0.8rem;opacity:0.75;margin-top:10px}}

.cta{{text-align:center;padding:50px 20px;background:white;border-radius:24px;box-shadow:0 10px 30px rgba(6,95,70,0.08)}}
.cta h3{{font-size:1.6rem;color:#065f46;margin-bottom:15px}}
.cta p{{color:#64748b;margin-bottom:25px;max-width:600px;margin-left:auto;margin-right:auto;line-height:1.6}}
.cta .btn{{display:inline-block;padding:15px 40px;background:linear-gradient(135deg,#065f46,#10b981);color:white;text-decoration:none;border-radius:12px;font-weight:800;font-size:1rem;box-shadow:0 8px 24px rgba(16,185,129,0.35);transition:0.3s}}
.cta .btn:hover{{transform:translateY(-2px);box-shadow:0 12px 32px rgba(16,185,129,0.45)}}
</style>
</head>
<body>

<div class="hero">
  <h1>AGRI<span>SÉNÉGAL</span></h1>
  <p>La plateforme agricole connectée du Sénégal — IA, satellite, mobile money au service des producteurs</p>
  <div class="badges">
    <span>🌾 {nb_producteurs} producteurs</span>
    <span>📍 {nb_parcelles} parcelles</span>
    <span>🌱 {nb_cultures} cultures</span>
    <span>🛰️ NDVI temps réel</span>
  </div>
</div>

<div class="container">

  <div class="stats">
    <div class="stat">
      <div class="v">{nb_producteurs}</div>
      <div class="l">Producteurs</div>
    </div>
    <div class="stat">
      <div class="v">{nb_parcelles}</div>
      <div class="l">Parcelles</div>
    </div>
    <div class="stat">
      <div class="v">{prod_totale/1000:.0f}t</div>
      <div class="l">Production</div>
    </div>
    <div class="stat">
      <div class="v">{nb_cultures}</div>
      <div class="l">Cultures</div>
    </div>
  </div>

  <h2><i class="fas fa-chart-line"></i> Prix du marché</h2>
  <div class="prix-grid">
"""
    for p in prix:
        content += f"""
    <div class="prix-card">
      <div class="nom"><i class="fas {p['icone'] or 'fa-seedling'}" style="color:#10b981"></i> {p['culture_nom'] or '-'}</div>
      <div class="wolof">{p['nom_wolof'] or ''}</div>
      <div class="prix">{_fmt_fcfa(p['prix_moyen'])}/kg</div>
      <div class="tendance">{p['marche'] or 'Marché national'}</div>
    </div>
"""
    if not prix:
        content += '<div class="prix-card"><p style="color:#64748b">Prix à venir</p></div>'

    content += """
  </div>

  <h2><i class="fas fa-seedling"></i> Nos cultures</h2>
  <div class="cultures-grid">
"""
    for cu in cultures:
        content += f"""
    <div class="culture-card">
      <div class="head">
        <div class="icon"><i class="fas {cu['icone'] or 'fa-seedling'}"></i></div>
        <div>
          <div class="nom">{cu['nom']}</div>
          <div class="wolof">{cu['nom_wolof'] or ''}</div>
        </div>
      </div>
      <div class="info">
        <div>
          <div class="lbl">Prix moyen</div>
          <div class="val">{_fmt_fcfa(cu['prix_moyen_kg'])}/kg</div>
        </div>
        <div>
          <div class="lbl">Rendement</div>
          <div class="val">{cu['rendement_theorique_t_ha'] or '-'} t/ha</div>
        </div>
      </div>
    </div>
"""
    content += """
  </div>

  <div class="cta" style="margin-top:60px">
    <h3><i class="fas fa-handshake"></i> Vous êtes producteur ?</h3>
    <p>Rejoignez AgriSénégal et bénéficiez de l'IA, du suivi satellite, du mobile money et de notre réseau d'acheteurs partenaires.</p>
    <a href="/login" class="btn"><i class="fas fa-right-to-bracket"></i> Espace producteur</a>
  </div>

</div>

<footer>
  <div>&copy; 2026 <strong>AGRISÉNÉGAL</strong> — Tous droits réservés</div>
  <div class="sub">
    <i class="fas fa-code"></i> Développé par <strong>OMEGA INFORMATIQUE</strong> · Dakar, Sénégal · UEMOA
  </div>
</footer>

</body>
</html>
"""
    return render_template_string(content)


@portail_bp.route('/portail/api/prix')
def portail_api_prix():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT pm.*, c.nom AS culture_nom, c.nom_wolof
                 FROM prix_marche pm
                 LEFT JOIN cultures c ON pm.culture_id = c.id
                 ORDER BY pm.date_releve DESC LIMIT 20""")
    rows = c.fetchall()
    conn.close()
    return jsonify(prix=[dict(r) for r in rows])


@portail_bp.route('/portail/api/cultures')
def portail_api_cultures():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT nom, nom_wolof, icone, prix_moyen_kg,
                        rendement_theorique_t_ha, cycle_jours_min, cycle_jours_max
                 FROM cultures WHERE actif=1 ORDER BY nom""")
    rows = c.fetchall()
    conn.close()
    return jsonify(cultures=[dict(r) for r in rows])
