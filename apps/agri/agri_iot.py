"""
🌡️ AgriSénégal V2 — IoT Agricole
Capteurs humidité sol · Stations météo · Ingestion données
"""
from flask import Blueprint, request, redirect, flash, jsonify
from flask_login import current_user
import sqlite3
import random
from datetime import datetime, timedelta

agri_iot_bp = Blueprint('agri_iot', __name__)
_deps = {}


def init_agri_iot(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(agri_iot_bp)
    print("[IOT] ✅ Module IoT complet enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='iot', title='AgriSénégal IoT'):
    return _deps['render_page'](content, active=active, page_title=title)


def _log(action, details='', entity=None, entity_id=None):
    try:
        uid = None
        if current_user and current_user.is_authenticated:
            uid = current_user.id
        _deps['log_action'](uid, action, details, entity=entity, entity_id=entity_id)
    except Exception:
        pass


def _auth_required(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if not (current_user and current_user.is_authenticated):
            return redirect('/login')
        return f(*a, **k)
    return w


@agri_iot_bp.route('/iot')
@_auth_required
def iot_home():
    if current_user.role not in ('admin', 'direction', 'cooperative', 'technicien'):
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()

    # Stations météo
    c.execute("""SELECT s.*, r.nom AS region_nom
                 FROM stations_meteo s
                 LEFT JOIN regions r ON s.region_id = r.id
                 WHERE s.actif=1""")
    stations = c.fetchall()

    # Dernières mesures
    c.execute("""SELECT dm.*, s.nom AS station_nom
                 FROM donnees_meteo dm
                 LEFT JOIN stations_meteo s ON dm.station_id = s.id
                 ORDER BY dm.date_mesure DESC LIMIT 20""")
    mesures = c.fetchall()

    # Stats
    c.execute("""SELECT COUNT(*) AS nb,
                        AVG(temperature_moy) AS temp_moy,
                        AVG(humidite_pct) AS humidite_moy,
                        COALESCE(SUM(pluviometrie_mm), 0) AS pluvio
                 FROM donnees_meteo
                 WHERE date_mesure >= date('now', '-30 days')""")
    stats = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-microchip"></i> IoT Agricole</h2>
        <div class="page-subtitle">Capteurs sol · Stations météo · Alertes temps réel</div></div>
      <a href="/iot/simuler" class="btn btn-primary">
        <i class="fas fa-play"></i> Simuler mesures
      </a>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-broadcast-tower"></i></div>
        <div class="stat-value">{len(stations)}</div>
        <div class="stat-label">Stations actives</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-temperature-half"></i></div>
        <div class="stat-value">{stats['temp_moy'] or 0:.1f}°C</div>
        <div class="stat-label">Temp. moyenne 30j</div></div>
      <div class="stat-card blue"><div class="stat-icon"><i class="fas fa-droplet"></i></div>
        <div class="stat-value">{stats['humidite_moy'] or 0:.0f}%</div>
        <div class="stat-label">Humidité moyenne</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-cloud-rain"></i></div>
        <div class="stat-value">{stats['pluvio'] or 0:.0f} mm</div>
        <div class="stat-label">Pluie 30 jours</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-broadcast-tower"></i> Stations météo</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Code</th><th>Nom</th><th>Type</th><th>Région</th>
                   <th>GPS</th><th>Statut</th></tr></thead>
        <tbody>"""
    for s in stations:
        badge = 'badge-success' if s['statut'] == 'Active' else 'badge-warning'
        content += f"""
        <tr>
          <td><strong>{s['code']}</strong></td>
          <td>{s['nom']}</td>
          <td><span class="badge badge-primary">{s['type'] or '-'}</span></td>
          <td>{s['region_nom'] or '-'}</td>
          <td><small style="font-family:monospace">{s['latitude']:.3f}, {s['longitude']:.3f}</small></td>
          <td><span class="badge {badge}">{s['statut']}</span></td>
        </tr>"""
    if not stations:
        content += '<tr><td colspan="6" class="empty">Aucune station</td></tr>'
    content += "</tbody></table></div></div>"

    content += """
    <div class="card">
      <div class="card-header"><h3><i class="fas fa-chart-line"></i> Dernières mesures</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Date</th><th>Station</th><th>Temp. moy</th>
                   <th>Humidité</th><th>Pluie</th><th>Vent</th></tr></thead>
        <tbody>"""
    for m in mesures:
        temp_color = '#10b981'
        if (m['temperature_moy'] or 0) > 35: temp_color = '#dc2626'
        elif (m['temperature_moy'] or 0) > 30: temp_color = '#f59e0b'
        content += f"""
        <tr>
          <td>{m['date_mesure']}</td>
          <td>{m['station_nom'] or '-'}</td>
          <td><strong style="color:{temp_color}">{m['temperature_moy'] or 0:.1f}°C</strong></td>
          <td>{m['humidite_pct'] or 0:.0f}%</td>
          <td>{m['pluviometrie_mm'] or 0:.1f} mm</td>
          <td>{m['vent_vitesse_kmh'] or 0:.0f} km/h</td>
        </tr>"""
    content += "</tbody></table></div></div>"

    return _render(content, active='iot', title='IoT Agricole')


@agri_iot_bp.route('/iot/simuler')
@_auth_required
def iot_simuler():
    if current_user.role not in ('admin', 'direction', 'technicien'):
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()

    # Récupérer les stations
    c.execute("SELECT id FROM stations_meteo WHERE actif=1")
    stations = c.fetchall()

    nb_insertions = 0
    for s in stations:
        # Simuler 3 mesures
        for jour in range(3):
            d = datetime.now() - timedelta(days=jour)
            temp_min = random.uniform(18, 26)
            temp_max = random.uniform(30, 40)

            c.execute("""INSERT INTO donnees_meteo
                (station_id, date_mesure, temperature_min, temperature_max,
                 temperature_moy, humidite_pct, pluviometrie_mm,
                 vent_vitesse_kmh, vent_direction, source)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (s['id'], d.date().isoformat(),
                 round(temp_min, 1), round(temp_max, 1),
                 round((temp_min + temp_max) / 2, 1),
                 random.randint(30, 85),
                 round(random.uniform(0, 20), 1),
                 round(random.uniform(5, 25), 1),
                 random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']),
                 'IoT'))
            nb_insertions += 1

    conn.commit()
    conn.close()

    _log('IOT_SIMULATION', f"{nb_insertions} mesures IoT simulées")
    flash(f"{nb_insertions} mesures IoT simulées", "success")
    return redirect('/iot')


# ================================================================
# API IoT (pour capteurs externes)
# ================================================================
@agri_iot_bp.route('/api/iot/mesure', methods=['POST'])
def api_iot_mesure():
    """Endpoint pour capteurs IoT externes (sans auth pour MVP)"""
    try:
        data = request.get_json() or {}
        station_code = data.get('station_code')
        temp = data.get('temperature')
        humidite = data.get('humidite')
        pluvio = data.get('pluviometrie', 0)

        if not station_code:
            return jsonify(error='station_code requis'), 400

        conn = _db()
        c = conn.cursor()
        c.execute("SELECT id FROM stations_meteo WHERE code=?", (station_code,))
        row = c.fetchone()

        if not row:
            conn.close()
            return jsonify(error='station introuvable'), 404

        c.execute("""INSERT INTO donnees_meteo
            (station_id, date_mesure, temperature_moy, humidite_pct,
             pluviometrie_mm, source)
            VALUES (?,?,?,?,?,?)""",
            (row['id'], datetime.now().date().isoformat(),
             temp, humidite, pluvio, 'API'))
        conn.commit()
        conn.close()

        return jsonify(status='ok', station=station_code)

    except Exception as e:
        return jsonify(error=str(e)), 500


@agri_iot_bp.route('/api/iot/stats')
@_auth_required
def api_iot_stats():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT COUNT(*) AS nb FROM stations_meteo WHERE actif=1""")
    nb_stations = c.fetchone()['nb']
    c.execute("""SELECT COUNT(*) AS nb FROM donnees_meteo
                 WHERE date_mesure >= date('now', '-7 days')""")
    nb_mesures = c.fetchone()['nb']
    conn.close()
    return jsonify(stations=nb_stations, mesures_7j=nb_mesures)
