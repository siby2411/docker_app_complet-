"""
Omega Transport V2 — Portail public
Consultation anonyme des lignes et horaires
"""
from flask import Blueprint, render_template_string, request, redirect, jsonify
from datetime import datetime
import sqlite3

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


# ================================================================
# ==================== PORTAIL PUBLIC ====================
# ================================================================
@portail_bp.route('/portail')
def portail_index():
    conn = _db()
    c = conn.cursor()

    # Lignes actives
    c.execute("""SELECT l.*,
                 (SELECT GROUP_CONCAT(heure_depart, ', ') FROM horaires WHERE ligne_id=l.id AND actif=1 LIMIT 5) AS horaires
                 FROM lignes l WHERE l.actif=1 ORDER BY l.code""")
    lignes = c.fetchall()

    # Stats
    c.execute("SELECT COUNT(*) FROM vehicules WHERE actif=1")
    nb_v = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM chauffeurs WHERE actif=1")
    nb_ch = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM sites WHERE actif=1")
    nb_sites = c.fetchone()[0]
    c.execute("""SELECT COALESCE(SUM(places_vendues), 0) FROM voyages
                 WHERE date(date_voyage) >= date('now', '-30 days')""")
    passagers_mois = c.fetchone()[0] or 0
    conn.close()

    content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Omega Transport — Portail public</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}}
body{{background:#f0fdff;color:#0e7490;min-height:100vh}}

.hero{{background:linear-gradient(135deg,#0e7490 0%,#06b6d4 50%,#22d3ee 100%);color:white;padding:60px 30px;text-align:center;position:relative;overflow:hidden}}
.hero::before{{content:'';position:absolute;top:-100px;right:-100px;width:350px;height:350px;background:rgba(165,243,252,0.15);border-radius:50%}}
.hero::after{{content:'';position:absolute;bottom:-120px;left:-80px;width:280px;height:280px;background:rgba(165,243,252,0.1);border-radius:50%}}
.hero h1{{font-size:2.8rem;font-weight:900;letter-spacing:-1.5px;margin-bottom:15px;position:relative;z-index:1}}
.hero h1 span{{color:#a5f3fc}}
.hero p{{font-size:1.1rem;opacity:0.95;max-width:600px;margin:0 auto;position:relative;z-index:1}}
.hero .badges{{margin-top:25px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap;position:relative;z-index:1}}
.hero .badges span{{background:rgba(255,255,255,0.15);padding:8px 16px;border-radius:20px;font-size:0.8rem;font-weight:800;backdrop-filter:blur(10px)}}

.container{{max-width:1200px;margin:0 auto;padding:40px 25px}}

.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin-bottom:40px}}
.stat{{background:white;border-radius:18px;padding:25px;text-align:center;box-shadow:0 6px 20px rgba(14,116,144,0.08);border-top:4px solid #06b6d4}}
.stat .v{{font-size:2.5rem;font-weight:900;color:#0e7490;line-height:1}}
.stat .l{{font-size:0.8rem;color:#64748b;text-transform:uppercase;font-weight:800;letter-spacing:1px;margin-top:8px}}

h2{{font-size:1.5rem;color:#0e7490;font-weight:900;margin-bottom:20px;display:flex;align-items:center;gap:12px}}
h2 i{{color:#06b6d4}}

.lignes-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:20px}}
.ligne-card{{background:white;border-radius:18px;padding:22px;box-shadow:0 6px 20px rgba(14,116,144,0.08);transition:0.3s;border-left:5px solid #06b6d4}}
.ligne-card:hover{{transform:translateY(-5px);box-shadow:0 12px 30px rgba(14,116,144,0.15)}}
.ligne-card .head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px}}
.ligne-card .code{{font-size:1.1rem;font-weight:900;color:#0e7490}}
.ligne-card .trajet{{font-size:1.15rem;font-weight:800;color:#0e7490;margin-bottom:5px}}
.ligne-card .distance{{font-size:0.8rem;color:#94a3b8}}
.ligne-card .prices{{display:flex;gap:15px;margin-top:15px;padding-top:15px;border-top:1px solid #f0fdff}}
.ligne-card .price{{flex:1}}
.ligne-card .price .lbl{{font-size:0.7rem;color:#64748b;text-transform:uppercase;font-weight:800}}
.ligne-card .price .val{{font-size:1.2rem;font-weight:900;color:#06b6d4}}
.ligne-card .horaires{{font-size:0.75rem;color:#64748b;margin-top:10px;font-family:monospace}}

.btn{{padding:12px 24px;border:none;border-radius:10px;cursor:pointer;font-weight:700;text-decoration:none;display:inline-flex;align-items:center;gap:8px;transition:0.3s;font-size:0.9rem}}
.btn-primary{{background:linear-gradient(135deg,#0e7490,#06b6d4);color:white;box-shadow:0 6px 16px rgba(14,116,144,0.3)}}
.btn-primary:hover{{transform:translateY(-2px)}}

footer{{background:linear-gradient(135deg,#0e7490,#155e75);color:white;padding:40px 20px;text-align:center;margin-top:60px}}
footer strong{{color:#a5f3fc}}
footer .sub{{font-size:0.8rem;opacity:0.75;margin-top:10px}}
</style>
</head>
<body>

<div class="hero">
  <h1>OMEGA <span>TRANSPORT</span></h1>
  <p>Consultez nos lignes, horaires et tarifs en temps réel. Réservez votre place auprès de nos guichets.</p>
  <div class="badges">
    <span>🇸🇳 Sénégal</span>
    <span>🚌 {nb_v} véhicules</span>
    <span>👨‍✈️ {nb_ch} chauffeurs</span>
    <span>📍 {nb_sites} gares</span>
  </div>
</div>

<div class="container">

  <div class="stats">
    <div class="stat">
      <div class="v">{len(lignes)}</div>
      <div class="l">Lignes actives</div>
    </div>
    <div class="stat">
      <div class="v">{nb_v}</div>
      <div class="l">Véhicules</div>
    </div>
    <div class="stat">
      <div class="v">{passagers_mois}</div>
      <div class="l">Passagers / 30j</div>
    </div>
    <div class="stat">
      <div class="v">{nb_ch}</div>
      <div class="l">Chauffeurs</div>
    </div>
  </div>

  <h2><i class="fas fa-route"></i> Nos lignes & horaires</h2>

  <div class="lignes-grid">
"""
    for l in lignes:
        content += f"""
    <div class="ligne-card">
      <div class="head">
        <span class="code">{l['code']}</span>
        <span style="font-size:0.75rem;color:#06b6d4;font-weight:800">{l['distance_km']} km</span>
      </div>
      <div class="trajet">
        <i class="fas fa-arrow-right" style="color:#06b6d4;font-size:0.8rem"></i>
        {l['ville_depart']} → {l['ville_arrivee']}
      </div>
      <div class="distance">
        <i class="fas fa-clock"></i> {l['duree_minutes']} minutes de trajet
      </div>
      <div class="prices">
        <div class="price">
          <div class="lbl">2ème classe</div>
          <div class="val">{_fmt_fcfa(l['tarif_2eme'] or l['tarif_base'])}</div>
        </div>
        <div class="price">
          <div class="lbl">1ère classe</div>
          <div class="val">{_fmt_fcfa(l['tarif_1ere'] or 0)}</div>
        </div>
      </div>
      <div class="horaires">
        <i class="fas fa-clock"></i> Départs : {l['horaires'] or 'À consulter'}
      </div>
    </div>
"""
    content += """
  </div>

  <div style="text-align:center;margin-top:50px">
    <p style="color:#64748b;margin-bottom:20px">
      <i class="fas fa-info-circle"></i> Pour réserver ou acheter un billet, rendez-vous à nos guichets ou contactez-nous.
    </p>
  </div>

</div>

<footer>
  <div>&copy; 2026 <strong>OMEGA TRANSPORT</strong> — Tous droits réservés</div>
  <div class="sub">
    <i class="fas fa-code"></i> Développé par <strong>OMEGA INFORMATIQUE</strong> · Dakar, Sénégal · UEMOA
  </div>
</footer>

</body>
</html>
"""
    return render_template_string(content)


@portail_bp.route('/portail/ligne/<int:lid>')
def portail_ligne(lid):
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM lignes WHERE id=? AND actif=1", (lid,))
    ligne = c.fetchone()
    if not ligne:
        conn.close()
        return redirect('/portail')

    c.execute("SELECT * FROM horaires WHERE ligne_id=? AND actif=1 ORDER BY heure_depart", (lid,))
    horaires = c.fetchall()

    # Prochains voyages
    c.execute("""SELECT vo.*, v.immatriculation
                 FROM voyages vo
                 LEFT JOIN vehicules v ON vo.vehicule_id = v.id
                 WHERE vo.ligne_id=? AND date(vo.date_voyage) >= date('now')
                   AND vo.statut IN ('Programmé','En cours')
                 ORDER BY vo.date_voyage, vo.heure_depart_prevue LIMIT 10""", (lid,))
    voyages = c.fetchall()
    conn.close()

    content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{ligne['code']} — Omega Transport</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}}
body{{background:#f0fdff;color:#0e7490}}
.header{{background:linear-gradient(135deg,#0e7490,#06b6d4);color:white;padding:40px 30px}}
.header h1{{font-size:2.2rem;font-weight:900;margin-bottom:8px}}
.header p{{opacity:0.9}}
.container{{max-width:900px;margin:0 auto;padding:30px 25px}}
.card{{background:white;border-radius:18px;padding:28px;box-shadow:0 6px 20px rgba(14,116,144,0.06);margin-bottom:20px}}
h3{{font-size:1.2rem;margin-bottom:15px;color:#0e7490}}
.info-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.info-grid .lbl{{font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800}}
.info-grid .val{{font-size:1.1rem;font-weight:900;color:#0e7490;margin-top:5px}}
.horaires{{display:flex;gap:8px;flex-wrap:wrap}}
.horaire{{background:#cffafe;color:#155e75;padding:10px 18px;border-radius:10px;font-weight:800;font-size:1rem}}
table{{width:100%;border-collapse:collapse;margin-top:15px}}
th,td{{padding:12px;border-bottom:1px solid #f0fdff;text-align:left}}
th{{background:#f0fdff;font-size:0.75rem;text-transform:uppercase;font-weight:800;color:#0e7490}}
.btn{{display:inline-block;padding:10px 20px;background:linear-gradient(135deg,#0e7490,#06b6d4);color:white;text-decoration:none;border-radius:10px;font-weight:700;margin-top:15px}}
</style>
</head>
<body>

<div class="header">
  <div style="max-width:900px;margin:0 auto">
    <h1>{ligne['code']}</h1>
    <p><i class="fas fa-map-marker-alt"></i> {ligne['ville_depart']} → {ligne['ville_arrivee']}</p>
  </div>
</div>

<div class="container">

  <div class="card">
    <h3><i class="fas fa-info-circle"></i> Informations</h3>
    <div class="info-grid">
      <div><div class="lbl">Distance</div><div class="val">{ligne['distance_km']} km</div></div>
      <div><div class="lbl">Durée</div><div class="val">{ligne['duree_minutes']} min</div></div>
      <div><div class="lbl">Tarif 2ème classe</div><div class="val">{_fmt_fcfa(ligne['tarif_2eme'] or ligne['tarif_base'])}</div></div>
      <div><div class="lbl">Tarif 1ère classe</div><div class="val">{_fmt_fcfa(ligne['tarif_1ere'] or 0)}</div></div>
    </div>
  </div>

  <div class="card">
    <h3><i class="fas fa-clock"></i> Horaires de départ</h3>
    <div class="horaires">"""
    for h in horaires:
        content += f'<span class="horaire">{h["heure_depart"]}</span>'
    if not horaires:
        content += '<p>Horaires à consulter au guichet</p>'
    content += """
    </div>
  </div>
"""
    if voyages:
        content += """
  <div class="card">
    <h3><i class="fas fa-calendar-check"></i> Prochains départs</h3>
    <table>
      <thead><tr><th>Date</th><th>Heure</th><th>Véhicule</th><th>Places libres</th></tr></thead>
      <tbody>"""
        for v in voyages:
            dispo = (v['places_totales'] or 0) - (v['places_vendues'] or 0)
            content += f"""
        <tr>
          <td>{v['date_voyage']}</td>
          <td><strong>{v['heure_depart_prevue']}</strong></td>
          <td>{v['immatriculation'] or '-'}</td>
          <td><span style="background:{'#d1fae5' if dispo > 5 else '#fee2e2'};color:{'#065f46' if dispo > 5 else '#991b1b'};padding:4px 10px;border-radius:8px;font-weight:800">{dispo} places</span></td>
        </tr>"""
        content += "</tbody></table></div>"

    content += """
  <div style="text-align:center;margin-top:30px">
    <a href="/portail" class="btn"><i class="fas fa-arrow-left"></i> Retour au portail</a>
  </div>

</div>
</body>
</html>
"""
    return render_template_string(content)


@portail_bp.route('/portail/api/lignes')
def portail_api_lignes():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT id, code, nom, ville_depart, ville_arrivee,
                        distance_km, duree_minutes, tarif_base, tarif_1ere, tarif_2eme
                 FROM lignes WHERE actif=1 ORDER BY code""")
    rows = c.fetchall()
    conn.close()
    return jsonify(lignes=[dict(r) for r in rows])
