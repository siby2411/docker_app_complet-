"""
📊 AgriSénégal V2 — Rapports & Exports
CSV · Synthèses · Analyses
"""
from flask import Blueprint, request, redirect, flash, Response, jsonify
from flask_login import current_user
import sqlite3
import csv
import io
from datetime import datetime

rapports_bp = Blueprint('rapports', __name__)
_deps = {}


def init_rapports(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(rapports_bp)
    print("[RAPPORTS] ✅ Module rapports complet enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='rapports', title='AgriSénégal'):
    return _deps['render_page'](content, active=active, page_title=title)


def _auth_required(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if not (current_user and current_user.is_authenticated):
            return redirect('/login')
        return f(*a, **k)
    return w


def _log(action, details=''):
    try:
        uid = None
        if current_user and current_user.is_authenticated:
            uid = current_user.id
        _deps['log_action'](uid, action, details)
    except Exception:
        pass


def _fmt_fcfa(m):
    if not m:
        return "0 F"
    return f"{int(m):,} F".replace(",", " ")


@rapports_bp.route('/rapports')
@_auth_required
def rapports_home():
    if current_user.role not in ('admin', 'direction', 'finance', 'cooperative'):
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()

    # KPIs
    c.execute("SELECT COUNT(*) FROM producteurs WHERE actif=1")
    nb_producteurs = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM parcelles WHERE actif=1")
    nb_parcelles = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(quantite_kg), 0) FROM recoltes")
    prod_totale = c.fetchone()[0]

    c.execute("""SELECT COALESCE(SUM(montant_total), 0) FROM ventes
                 WHERE statut_paiement='Payé'""")
    ca_total = c.fetchone()[0]

    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-file-invoice"></i> Rapports & Exports</h2>
        <div class="page-subtitle">Analyses et téléchargements CSV</div></div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-users"></i></div>
        <div class="stat-value">{nb_producteurs}</div>
        <div class="stat-label">Producteurs actifs</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-draw-polygon"></i></div>
        <div class="stat-value">{nb_parcelles}</div>
        <div class="stat-label">Parcelles</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-wheat-awn"></i></div>
        <div class="stat-value">{prod_totale/1000:.1f}t</div>
        <div class="stat-label">Production totale</div></div>
      <div class="stat-card blue"><div class="stat-icon"><i class="fas fa-money-bill-wave"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(ca_total)}</div>
        <div class="stat-label">CA total</div></div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px">
      <div class="card">
        <div class="card-header"><h3><i class="fas fa-users"></i> Producteurs</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">Liste complète avec localisation</p>
        <a href="/rapports/producteurs.csv" class="btn btn-primary btn-sm"><i class="fas fa-download"></i> CSV</a>
      </div>

      <div class="card">
        <div class="card-header"><h3><i class="fas fa-draw-polygon"></i> Parcelles</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">Parcelles avec GPS et cultures</p>
        <a href="/rapports/parcelles.csv" class="btn btn-primary btn-sm"><i class="fas fa-download"></i> CSV</a>
      </div>

      <div class="card">
        <div class="card-header"><h3><i class="fas fa-wheat-awn"></i> Récoltes</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">Historique de production</p>
        <a href="/rapports/recoltes.csv" class="btn btn-primary btn-sm"><i class="fas fa-download"></i> CSV</a>
      </div>

      <div class="card">
        <div class="card-header"><h3><i class="fas fa-money-bill-wave"></i> Ventes</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">Transactions commerciales</p>
        <a href="/rapports/ventes.csv" class="btn btn-primary btn-sm"><i class="fas fa-download"></i> CSV</a>
      </div>

      <div class="card">
        <div class="card-header"><h3><i class="fas fa-mobile-screen"></i> Mobile Money</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">Wave, OM, Free</p>
        <a href="/rapports/mobile-money.csv" class="btn btn-primary btn-sm"><i class="fas fa-download"></i> CSV</a>
      </div>

      <div class="card">
        <div class="card-header"><h3><i class="fas fa-cow"></i> Élevage</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">Troupeaux et animaux</p>
        <a href="/rapports/elevage.csv" class="btn btn-primary btn-sm"><i class="fas fa-download"></i> CSV</a>
      </div>

      <div class="card">
        <div class="card-header"><h3><i class="fas fa-cloud-sun"></i> Météo 30j</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">Données météo historiques</p>
        <a href="/rapports/meteo.csv" class="btn btn-primary btn-sm"><i class="fas fa-download"></i> CSV</a>
      </div>

      <div class="card">
        <div class="card-header"><h3><i class="fas fa-satellite"></i> NDVI Satellite</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">Indices de végétation</p>
        <a href="/rapports/ndvi.csv" class="btn btn-primary btn-sm"><i class="fas fa-download"></i> CSV</a>
      </div>
    </div>
    """
    return _render(content, active='rapports', title='Rapports')


def _csv_response(rows, headers, filename):
    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(headers)
    for row in rows:
        w.writerow([row[h] if h in row.keys() else '' for h in headers])
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


@rapports_bp.route('/rapports/producteurs.csv')
@_auth_required
def rapports_producteurs():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT p.code, p.nom, p.prenom, p.sexe, p.telephone,
                        p.exploitation_nom, p.superficie_totale,
                        v.nom AS village, r.nom AS region,
                        p.mobile_money_type, p.mobile_money_numero
                 FROM producteurs p
                 LEFT JOIN villages v ON p.village_id = v.id
                 LEFT JOIN departements d ON v.departement_id = d.id
                 LEFT JOIN regions r ON d.region_id = r.id
                 WHERE p.actif=1 ORDER BY p.nom""")
    rows = c.fetchall()
    conn.close()
    _log('EXPORT_PRODUCTEURS', f"{len(rows)} producteurs")
    return _csv_response(rows,
        ['code', 'nom', 'prenom', 'sexe', 'telephone', 'exploitation_nom',
         'superficie_totale', 'village', 'region', 'mobile_money_type', 'mobile_money_numero'],
        f'producteurs_{datetime.now().strftime("%Y%m%d")}.csv')


@rapports_bp.route('/rapports/parcelles.csv')
@_auth_required
def rapports_parcelles():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT pa.code, pa.nom, pa.superficie_ha, pa.latitude, pa.longitude,
                        pa.type_sol, pa.ph_sol, pa.irrigation_disponible,
                        p.nom AS producteur, p.code AS producteur_code
                 FROM parcelles pa
                 LEFT JOIN producteurs p ON pa.producteur_id = p.id
                 WHERE pa.actif=1 ORDER BY pa.code""")
    rows = c.fetchall()
    conn.close()
    _log('EXPORT_PARCELLES', f"{len(rows)} parcelles")
    return _csv_response(rows,
        ['code', 'nom', 'superficie_ha', 'latitude', 'longitude',
         'type_sol', 'ph_sol', 'irrigation_disponible', 'producteur', 'producteur_code'],
        f'parcelles_{datetime.now().strftime("%Y%m%d")}.csv')


@rapports_bp.route('/rapports/recoltes.csv')
@_auth_required
def rapports_recoltes():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT r.code, r.date_recolte, c.nom AS culture,
                        r.quantite_kg, r.qualite, r.humidite_pct,
                        r.destination, p.nom AS producteur, p.code AS producteur_code
                 FROM recoltes r
                 LEFT JOIN cultures c ON r.culture_id = c.id
                 LEFT JOIN producteurs p ON r.producteur_id = p.id
                 ORDER BY r.date_recolte DESC""")
    rows = c.fetchall()
    conn.close()
    _log('EXPORT_RECOLTES', f"{len(rows)} récoltes")
    return _csv_response(rows,
        ['code', 'date_recolte', 'culture', 'quantite_kg', 'qualite',
         'humidite_pct', 'destination', 'producteur', 'producteur_code'],
        f'recoltes_{datetime.now().strftime("%Y%m%d")}.csv')


@rapports_bp.route('/rapports/ventes.csv')
@_auth_required
def rapports_ventes():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT v.reference, v.date_vente, c.nom AS culture,
                        v.quantite_kg, v.prix_unitaire_kg, v.montant_total,
                        v.mode_paiement, v.statut_paiement,
                        p.nom AS producteur, v.acheteur_nom AS acheteur
                 FROM ventes v
                 LEFT JOIN cultures c ON v.culture_id = c.id
                 LEFT JOIN producteurs p ON v.producteur_id = p.id
                 ORDER BY v.date_vente DESC""")
    rows = c.fetchall()
    conn.close()
    _log('EXPORT_VENTES', f"{len(rows)} ventes")
    return _csv_response(rows,
        ['reference', 'date_vente', 'culture', 'quantite_kg', 'prix_unitaire_kg',
         'montant_total', 'mode_paiement', 'statut_paiement', 'producteur', 'acheteur'],
        f'ventes_{datetime.now().strftime("%Y%m%d")}.csv')


@rapports_bp.route('/rapports/mobile-money.csv')
@_auth_required
def rapports_mm():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT t.reference, t.date_transaction, t.fournisseur,
                        t.type_transaction, t.montant, t.statut,
                        p.nom AS producteur, p.code AS producteur_code
                 FROM transactions_mobile t
                 LEFT JOIN producteurs p ON t.producteur_id = p.id
                 ORDER BY t.date_transaction DESC""")
    rows = c.fetchall()
    conn.close()
    _log('EXPORT_MOBILE_MONEY', f"{len(rows)} transactions")
    return _csv_response(rows,
        ['reference', 'date_transaction', 'fournisseur', 'type_transaction',
         'montant', 'statut', 'producteur', 'producteur_code'],
        f'mobile_money_{datetime.now().strftime("%Y%m%d")}.csv')


@rapports_bp.route('/rapports/elevage.csv')
@_auth_required
def rapports_elevage():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT t.code, t.nom, e.nom AS espece, t.race,
                        t.effectif_total, t.mode_elevage, t.objectif,
                        p.nom AS producteur, p.code AS producteur_code
                 FROM troupeaux t
                 LEFT JOIN especes_animales e ON t.espece_id = e.id
                 LEFT JOIN producteurs p ON t.producteur_id = p.id
                 WHERE t.actif=1 ORDER BY t.code""")
    rows = c.fetchall()
    conn.close()
    _log('EXPORT_ELEVAGE', f"{len(rows)} troupeaux")
    return _csv_response(rows,
        ['code', 'nom', 'espece', 'race', 'effectif_total', 'mode_elevage',
         'objectif', 'producteur', 'producteur_code'],
        f'elevage_{datetime.now().strftime("%Y%m%d")}.csv')


@rapports_bp.route('/rapports/meteo.csv')
@_auth_required
def rapports_meteo():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT dm.date_mesure, s.nom AS station, dm.temperature_min,
                        dm.temperature_max, dm.temperature_moy, dm.humidite_pct,
                        dm.pluviometrie_mm, dm.vent_vitesse_kmh, dm.source
                 FROM donnees_meteo dm
                 LEFT JOIN stations_meteo s ON dm.station_id = s.id
                 WHERE dm.date_mesure >= date('now', '-30 days')
                 ORDER BY dm.date_mesure DESC""")
    rows = c.fetchall()
    conn.close()
    _log('EXPORT_METEO', f"{len(rows)} mesures")
    return _csv_response(rows,
        ['date_mesure', 'station', 'temperature_min', 'temperature_max',
         'temperature_moy', 'humidite_pct', 'pluviometrie_mm',
         'vent_vitesse_kmh', 'source'],
        f'meteo_{datetime.now().strftime("%Y%m%d")}.csv')


@rapports_bp.route('/rapports/ndvi.csv')
@_auth_required
def rapports_ndvi():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT i.date_image, pa.code AS parcelle, i.satellite,
                        i.ndvi_moyen, i.ndvi_min, i.ndvi_max, i.ndwi,
                        i.stress_hydrique, i.stress_azote
                 FROM images_satellite i
                 LEFT JOIN parcelles pa ON i.parcelle_id = pa.id
                 ORDER BY i.date_image DESC LIMIT 500""")
    rows = c.fetchall()
    conn.close()
    _log('EXPORT_NDVI', f"{len(rows)} images")
    return _csv_response(rows,
        ['date_image', 'parcelle', 'satellite', 'ndvi_moyen', 'ndvi_min',
         'ndvi_max', 'ndwi', 'stress_hydrique', 'stress_azote'],
        f'ndvi_{datetime.now().strftime("%Y%m%d")}.csv')
