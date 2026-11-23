"""
📊 Pointage V2 — Statistiques & Récapitulatif mensuel
Calcul heures travaillées, absences, retards par employé
"""
from flask import Blueprint, request, redirect, flash, jsonify, Response
from flask_login import current_user
import sqlite3
import csv
import io
from datetime import datetime, timedelta
from calendar import monthrange

stats_bp = Blueprint('stats', __name__)
_deps = {}


def init_stats(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(stats_bp)
    print("[STATS] ✅ Module statistiques enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='recap', title='Omega Pointage'):
    return _deps['render_page'](content, active=active, page_title=title)


def _auth_required(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if not (current_user and current_user.is_authenticated):
            return redirect('/login')
        return f(*a, **k)
    return w


def _can_view():
    return current_user and current_user.role in ('admin', 'rh', 'chef')


def _log(action, details=''):
    try:
        uid = current_user.id if current_user and current_user.is_authenticated else None
        _deps['log_action'](uid, action, details)
    except Exception:
        pass


# ================================================================
# RÉCAP MENSUEL PAR EMPLOYÉ
# ================================================================
@stats_bp.route('/recap-mensuel')
@_auth_required
def recap_mensuel():
    if not _can_view():
        flash("Accès réservé RH/Admin", "danger")
        return redirect('/')

    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')

    conn = _db()
    c = conn.cursor()

    c.execute("""
        SELECT e.id, e.matricule, e.nom, e.prenom,
               p.nom AS poste_nom,
               d.nom AS departement_nom,
               e.salaire_base,
               COUNT(DISTINCT pt.date_pointage) AS nb_jours_pointes,
               COALESCE(SUM(pt.heures_travaillees), 0) AS total_heures,
               COALESCE(SUM(pt.heures_sup), 0) AS total_hs,
               COALESCE(SUM(pt.duree_minutes), 0) AS total_minutes,
               COALESCE(SUM(CASE WHEN pt.statut='Retard' THEN 1 ELSE 0 END), 0) AS nb_retards,
               COALESCE(SUM(CASE WHEN pt.statut='Absent' THEN 1 ELSE 0 END), 0) AS nb_absences,
               COALESCE(SUM(CASE WHEN pt.statut='Mission' THEN 1 ELSE 0 END), 0) AS nb_missions
        FROM employes e
        LEFT JOIN pointages pt ON pt.employe_id = e.id
            AND strftime('%Y-%m', pt.date_pointage) = ?
        LEFT JOIN postes p ON e.poste_id = p.id
        LEFT JOIN departements d ON e.departement_id = d.id
        WHERE e.actif = 1
        GROUP BY e.id
        ORDER BY e.nom, e.prenom
    """, (mois,))
    lignes = c.fetchall()

    c.execute("""
        SELECT COUNT(DISTINCT employe_id) AS nb_employes,
               COUNT(*) AS nb_pointages,
               COALESCE(SUM(heures_travaillees), 0) AS total_h,
               COALESCE(SUM(heures_sup), 0) AS total_hs,
               SUM(CASE WHEN statut='Retard' THEN 1 ELSE 0 END) AS retards,
               SUM(CASE WHEN statut='Absent' THEN 1 ELSE 0 END) AS absences
        FROM pointages
        WHERE strftime('%Y-%m', date_pointage) = ?
    """, (mois,))
    stats = c.fetchone()

    y, m = map(int, mois.split('-'))
    nb_jours_mois = monthrange(y, m)[1]
    jours_ouvres = 0
    for j in range(1, nb_jours_mois + 1):
        d = datetime(y, m, j)
        if d.weekday() < 5:
            jours_ouvres += 1

    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-chart-line"></i> Récap mensuel</h2>
        <div class="page-subtitle">Heures, absences, retards — {mois}</div></div>
      <div style="display:flex;gap:10px">
        <a href="/recap-mensuel.csv?mois={mois}" class="btn btn-primary">
          <i class="fas fa-download"></i> Export CSV
        </a>
      </div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-users"></i></div>
        <div class="stat-value">{stats['nb_employes'] or 0}</div>
        <div class="stat-label">Employés pointés</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-hourglass"></i></div>
        <div class="stat-value">{stats['total_h'] or 0:.0f}h</div>
        <div class="stat-label">Heures totales</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-plus"></i></div>
        <div class="stat-value">{stats['total_hs'] or 0:.1f}h</div>
        <div class="stat-label">Heures sup</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-user-xmark"></i></div>
        <div class="stat-value">{stats['absences'] or 0}</div>
        <div class="stat-label">Absences</div></div>
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px">
        <input type="month" name="mois" value="{mois}"
               style="flex:1;padding:12px 15px;border:2px solid #f1f5f9;border-radius:11px">
        <button class="btn btn-primary"><i class="fas fa-filter"></i> Filtrer</button>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Matricule</th><th>Employé</th><th>Poste</th>
          <th>Jours pointés</th><th>Heures</th><th>H. sup</th>
          <th>Retards</th><th>Absences</th><th>Salaire estimé</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for l in lignes:
        heures = l['total_heures'] or 0
        hs = l['total_hs'] or 0
        salaire_base = l['salaire_base'] or 0
        taux_horaire = salaire_base / 173.33 if salaire_base else 0
        bonus_hs = taux_horaire * 1.25 * hs
        salaire_estime = salaire_base + bonus_hs

        badge_abs = 'badge-success'
        if l['nb_absences'] and l['nb_absences'] > 3:
            badge_abs = 'badge-danger'
        elif l['nb_absences'] and l['nb_absences'] > 0:
            badge_abs = 'badge-warning'

        badge_ret = 'badge-success'
        if l['nb_retards'] and l['nb_retards'] > 5:
            badge_ret = 'badge-danger'
        elif l['nb_retards'] and l['nb_retards'] > 2:
            badge_ret = 'badge-warning'

        content += f"""
        <tr>
          <td><strong>{l['matricule']}</strong></td>
          <td>{l['prenom']} {l['nom']}</td>
          <td><small>{l['poste_nom'] or '-'}</small></td>
          <td><span class="badge badge-primary">{l['nb_jours_pointes'] or 0}/{jours_ouvres}</span></td>
          <td><strong>{heures:.1f}h</strong></td>
          <td>{hs:.1f}h</td>
          <td><span class="badge {badge_ret}">{l['nb_retards'] or 0}</span></td>
          <td><span class="badge {badge_abs}">{l['nb_absences'] or 0}</span></td>
          <td><small>{int(salaire_estime):,} F</small></td>
          <td>
            <a href="/employes/{l['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
          </td>
        </tr>"""
    if not lignes:
        content += '<tr><td colspan="10" class="empty">Aucune donnée</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='recap', title='Récap mensuel')


# ================================================================
# ABSENCES DÉTAILLÉES
# ================================================================
@stats_bp.route('/absences')
@_auth_required
def absences_mois():
    if not _can_view():
        flash("Accès réservé RH/Admin", "danger")
        return redirect('/')

    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')

    conn = _db()
    c = conn.cursor()

    c.execute("""
        SELECT pt.*, e.matricule, e.nom, e.prenom,
               p.nom AS poste_nom
        FROM pointages pt
        LEFT JOIN employes e ON pt.employe_id = e.id
        LEFT JOIN postes p ON e.poste_id = p.id
        WHERE strftime('%Y-%m', pt.date_pointage) = ?
          AND pt.statut IN ('Absent', 'Retard')
        ORDER BY pt.date_pointage DESC, e.nom
    """, (mois,))
    lignes = c.fetchall()

    c.execute("""
        SELECT e.id, e.matricule, e.nom, e.prenom,
               SUM(CASE WHEN pt.statut='Absent' THEN 1 ELSE 0 END) AS absences,
               SUM(CASE WHEN pt.statut='Retard' THEN 1 ELSE 0 END) AS retards
        FROM employes e
        LEFT JOIN pointages pt ON pt.employe_id = e.id
            AND strftime('%Y-%m', pt.date_pointage) = ?
        WHERE e.actif = 1
        GROUP BY e.id
        HAVING absences > 0 OR retards > 0
        ORDER BY absences DESC
    """, (mois,))
    recap = c.fetchall()

    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-user-xmark"></i> Absences & retards</h2>
        <div class="page-subtitle">Détail par employé — {mois}</div></div>
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px">
        <input type="month" name="mois" value="{mois}"
               style="flex:1;padding:12px 15px;border:2px solid #f1f5f9;border-radius:11px">
        <button class="btn btn-primary"><i class="fas fa-filter"></i> Filtrer</button>
      </form>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-trophy"></i> Top absences</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Employé</th><th>Matricule</th><th>Absences</th><th>Retards</th><th>Actions</th></tr></thead>
        <tbody>"""
    for r in recap[:10]:
        badge = 'badge-danger' if r['absences'] > 3 else 'badge-warning'
        content += f"""
        <tr>
          <td><strong>{r['prenom']} {r['nom']}</strong></td>
          <td>{r['matricule']}</td>
          <td><span class="badge {badge}">{r['absences']}</span></td>
          <td><span class="badge badge-warning">{r['retards']}</span></td>
          <td><a href="/employes/{r['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a></td>
        </tr>"""
    content += "</tbody></table></div></div>"

    content += """
    <div class="card">
      <div class="card-header"><h3><i class="fas fa-list"></i> Détail des incidents</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Date</th><th>Employé</th><th>Poste</th><th>Statut</th><th>Notes</th></tr></thead>
        <tbody>"""
    for l in lignes:
        badge = 'badge-danger' if l['statut'] == 'Absent' else 'badge-warning'
        content += f"""
        <tr>
          <td><strong>{l['date_pointage']}</strong></td>
          <td>{l['prenom']} {l['nom']}</td>
          <td><small>{l['poste_nom'] or '-'}</small></td>
          <td><span class="badge {badge}">{l['statut']}</span></td>
          <td><small>{l['notes'] or '-'}</small></td>
        </tr>"""
    if not lignes:
        content += '<tr><td colspan="5" class="empty">Aucune absence ce mois</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='absences', title='Absences')


# ================================================================
# EXPORT CSV
# ================================================================
@stats_bp.route('/recap-mensuel.csv')
@_auth_required
def recap_mensuel_csv():
    if not _can_view():
        return redirect('/')

    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')

    conn = _db()
    c = conn.cursor()
    c.execute("""
        SELECT e.matricule, e.nom, e.prenom, p.nom AS poste,
               COUNT(DISTINCT pt.date_pointage) AS jours,
               COALESCE(SUM(pt.heures_travaillees), 0) AS heures,
               COALESCE(SUM(pt.heures_sup), 0) AS hs,
               COALESCE(SUM(CASE WHEN pt.statut='Retard' THEN 1 ELSE 0 END), 0) AS retards,
               COALESCE(SUM(CASE WHEN pt.statut='Absent' THEN 1 ELSE 0 END), 0) AS absences,
               e.salaire_base
        FROM employes e
        LEFT JOIN pointages pt ON pt.employe_id = e.id
            AND strftime('%Y-%m', pt.date_pointage) = ?
        LEFT JOIN postes p ON e.poste_id = p.id
        WHERE e.actif = 1
        GROUP BY e.id
        ORDER BY e.nom, e.prenom
    """, (mois,))
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(['Matricule', 'Nom', 'Prénom', 'Poste', 'Jours pointés',
                'Heures', 'H. sup', 'Retards', 'Absences', 'Salaire base'])
    for r in rows:
        w.writerow([r['matricule'], r['nom'], r['prenom'], r['poste'],
                    r['jours'], round(r['heures'], 2), round(r['hs'], 2),
                    r['retards'], r['absences'], r['salaire_base']])

    _log('EXPORT_RECAP', f"Mois {mois} — {len(rows)} employés")

    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=recap_{mois}.csv'}
    )


# ================================================================
# API
# ================================================================
@stats_bp.route('/api/stats-employe/<int:eid>')
@_auth_required
def api_stats_employe(eid):
    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')

    conn = _db()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(DISTINCT date_pointage) AS jours,
               COALESCE(SUM(heures_travaillees), 0) AS heures,
               COALESCE(SUM(heures_sup), 0) AS hs,
               SUM(CASE WHEN statut='Retard' THEN 1 ELSE 0 END) AS retards,
               SUM(CASE WHEN statut='Absent' THEN 1 ELSE 0 END) AS absences
        FROM pointages
        WHERE employe_id = ? AND strftime('%Y-%m', date_pointage) = ?
    """, (eid, mois))
    r = c.fetchone()
    conn.close()

    return jsonify(
        employe_id=eid,
        mois=mois,
        jours=r['jours'] or 0,
        heures=r['heures'] or 0,
        heures_sup=r['hs'] or 0,
        retards=r['retards'] or 0,
        absences=r['absences'] or 0
    )
