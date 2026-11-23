"""
Omega Transport V2 — Rapports & Exports
CSV · Synthèses exploitation · Rentabilité par véhicule
"""
from flask import Blueprint, request, redirect, flash, jsonify, Response
from flask_login import current_user
import sqlite3
import io
import csv
from datetime import datetime, timedelta

rapports_bp = Blueprint('rapports', __name__)
_deps = {}


def init_rapports(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(rapports_bp)
    print("[RAPPORTS] ✅ Module rapports complet enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='rapports', title='Omega Transport'):
    return _deps['render_page'](content, active=active, page_title=title)


def _log(action, details=''):
    try:
        uid = None
        if current_user and current_user.is_authenticated:
            uid = current_user.id
        _deps['log_action'](uid, action, details)
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


def _can_report():
    return current_user and current_user.role in ('admin', 'directeur', 'chef_exploitation', 'caissier')


def _fmt_fcfa(m):
    if not m:
        return "0 F"
    return f"{int(m):,} F".replace(",", " ")


def _csv_response(rows, headers, filename):
    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(headers)
    for r in rows:
        w.writerow([r.get(h, '') if isinstance(r, dict) else r[i] for i, h in enumerate(headers)])
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


# ================================================================
# ==================== HUB RAPPORTS ====================
# ================================================================
@rapports_bp.route('/rapports')
@_auth_required
def rapports_home():
    if not _can_report():
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()
    mois = datetime.now().strftime('%Y-%m')

    # KPIs rapides
    c.execute("""SELECT COUNT(*) AS nb,
                        COALESCE(SUM(recette_reelle), 0) AS ca,
                        COALESCE(SUM(places_vendues), 0) AS passagers
                 FROM voyages
                 WHERE strftime('%Y-%m', date_voyage)=?""", (mois,))
    stats_mois = c.fetchone()

    c.execute("""SELECT COALESCE(SUM(montant_total), 0) AS cout,
                        COALESCE(SUM(litres), 0) AS litres
                 FROM carburant
                 WHERE strftime('%Y-%m', date_bon)=?""", (mois,))
    stats_carb = c.fetchone()

    c.execute("""SELECT COALESCE(SUM(cout_total), 0) AS cout FROM maintenance
                 WHERE strftime('%Y-%m', date_debut)=?""", (mois,))
    stats_maint = c.fetchone()

    c.execute("""SELECT COUNT(*) AS nb,
                        COALESCE(SUM(montant), 0) AS total
                 FROM amendes WHERE strftime('%Y-%m', date_amende)=?""", (mois,))
    stats_amendes = c.fetchone()

    # Alertes documents expirés
    c.execute("""SELECT COUNT(*) FROM documents_vehicules
                 WHERE date_expiration IS NOT NULL
                   AND date(date_expiration) < date('now')""")
    docs_expires = c.fetchone()[0]

    conn.close()

    benefice = stats_mois['ca'] - stats_carb['cout'] - stats_maint['cout']

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-file-invoice"></i> Rapports & Analyses</h2>
        <div class="page-subtitle">Bilan du mois {mois}</div></div>
    </div>

    <div class="stats">
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-money-bill-wave"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(stats_mois['ca'])}</div>
        <div class="stat-label">CA du mois</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-gas-pump"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(stats_carb['cout'])}</div>
        <div class="stat-label">Carburant</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-wrench"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(stats_maint['cout'])}</div>
        <div class="stat-label">Maintenance</div></div>
      <div class="stat-card {'green' if benefice > 0 else 'rose'}">
        <div class="stat-icon"><i class="fas fa-chart-line"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(benefice)}</div>
        <div class="stat-label">Bénéfice estimé</div></div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px">
      <div class="card">
        <div class="card-header"><h3><i class="fas fa-route"></i> Exploitation</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          Statistiques des voyages, taux de remplissage, ponctualité
        </p>
        <a href="/rapports/exploitation.csv" class="btn btn-primary btn-sm">
          <i class="fas fa-download"></i> Export CSV
        </a>
        <a href="/rapports/exploitation" class="btn btn-info btn-sm" style="margin-left:8px">
          <i class="fas fa-chart-line"></i> Voir
        </a>
      </div>

      <div class="card">
        <div class="card-header"><h3><i class="fas fa-bus"></i> Rentabilité véhicules</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          CA, coûts, marge par véhicule — top/flop
        </p>
        <a href="/rapports/rentabilite-vehicules.csv" class="btn btn-primary btn-sm">
          <i class="fas fa-download"></i> Export CSV
        </a>
        <a href="/rapports/rentabilite-vehicules" class="btn btn-info btn-sm" style="margin-left:8px">
          <i class="fas fa-chart-line"></i> Voir
        </a>
      </div>

      <div class="card">
        <div class="card-header"><h3><i class="fas fa-id-card"></i> Performance chauffeurs</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          Voyages, recettes, amendes, ponctualité
        </p>
        <a href="/rapports/chauffeurs.csv" class="btn btn-primary btn-sm">
          <i class="fas fa-download"></i> Export CSV
        </a>
        <a href="/rapports/chauffeurs" class="btn btn-info btn-sm" style="margin-left:8px">
          <i class="fas fa-chart-line"></i> Voir
        </a>
      </div>

      <div class="card">
        <div class="card-header"><h3><i class="fas fa-gas-pump"></i> Consommation carburant</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          Suivi, écarts théorique/réel, anomalies
        </p>
        <a href="/rapports/carburant.csv" class="btn btn-primary btn-sm">
          <i class="fas fa-download"></i> Export CSV
        </a>
        <a href="/rapports/carburant" class="btn btn-info btn-sm" style="margin-left:8px">
          <i class="fas fa-chart-line"></i> Voir
        </a>
      </div>

      <div class="card">
        <div class="card-header"><h3><i class="fas fa-ticket"></i> Billetterie du mois</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          Liste détaillée des billets vendus
        </p>
        <a href="/rapports/billets.csv" class="btn btn-primary btn-sm">
          <i class="fas fa-download"></i> Export CSV
        </a>
      </div>

      <div class="card">
        <div class="card-header"><h3><i class="fas fa-gavel"></i> Amendes</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          {stats_amendes['nb']} amende(s) — {_fmt_fcfa(stats_amendes['total'])}
        </p>
        <a href="/rapports/amendes.csv" class="btn btn-primary btn-sm">
          <i class="fas fa-download"></i> Export CSV
        </a>
      </div>

      <div class="card" style="border-left:5px solid #dc2626">
        <div class="card-header"><h3 style="color:#991b1b"><i class="fas fa-triangle-exclamation"></i> Documents expirés</h3></div>
        <p style="color:#991b1b;font-size:0.85rem;margin-bottom:15px">
          <strong>{docs_expires}</strong> document(s) expiré(s) — action urgente
        </p>
        <a href="/vehicules?statut=Actif" class="btn btn-danger btn-sm">
          <i class="fas fa-list"></i> Voir véhicules
        </a>
      </div>
    </div>
    """
    return _render(content, active='rapports', title='Rapports')


# ================================================================
# ==================== EXPLOITATION ====================
# ================================================================
@rapports_bp.route('/rapports/exploitation')
@_auth_required
def rapports_exploitation():
    if not _can_report():
        flash("Accès réservé", "danger")
        return redirect('/')

    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')

    conn = _db()
    c = conn.cursor()

    # Par ligne
    c.execute("""SELECT l.id, l.code, l.nom, l.ville_depart, l.ville_arrivee,
                        COUNT(vo.id) AS nb_voyages,
                        COALESCE(SUM(vo.places_vendues), 0) AS passagers,
                        COALESCE(SUM(vo.recette_reelle), 0) AS ca,
                        COALESCE(AVG(vo.places_vendues * 100.0 / NULLIF(vo.places_totales, 0)), 0) AS taux
                 FROM lignes l
                 LEFT JOIN voyages vo ON vo.ligne_id = l.id
                    AND strftime('%Y-%m', vo.date_voyage)=?
                 WHERE l.actif=1
                 GROUP BY l.id
                 ORDER BY ca DESC""", (mois,))
    par_ligne = c.fetchall()

    conn.close()

    max_ca = max([l['ca'] for l in par_ligne], default=1)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-chart-line"></i> Exploitation — {mois}</h2></div>
      <div style="display:flex;gap:10px">
        <a href="/rapports" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        <a href="/rapports/exploitation.csv?mois={mois}" class="btn btn-primary">
          <i class="fas fa-download"></i> Export CSV
        </a>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-route"></i> Performance par ligne</h3></div>
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Ligne</th><th>Trajet</th><th>Voyages</th>
          <th>Passagers</th><th>Taux remplissage</th><th>CA</th>
        </tr></thead><tbody>
    """
    for l in par_ligne:
        pct_bar = (l['ca'] / max_ca * 100) if max_ca else 0
        content += f"""
        <tr>
          <td><strong>{l['code']}</strong></td>
          <td>{l['ville_depart']} → {l['ville_arrivee']}</td>
          <td>{l['nb_voyages']}</td>
          <td>{l['passagers']}</td>
          <td>
            <div style="background:#f0fdff;border-radius:6px;height:20px;position:relative;overflow:hidden">
              <div style="background:linear-gradient(90deg,#0e7490,#22d3ee);height:100%;width:{l['taux']}%"></div>
              <div style="position:absolute;top:0;left:0;right:0;text-align:center;line-height:20px;font-weight:800;font-size:0.75rem;color:white;text-shadow:0 0 3px rgba(0,0,0,0.5)">
                {l['taux']:.1f}%
              </div>
            </div>
          </td>
          <td><strong>{_fmt_fcfa(l['ca'])}</strong></td>
        </tr>"""
    content += "</tbody></table></div></div>"
    return _render(content, active='rapports', title=f'Exploitation {mois}')


@rapports_bp.route('/rapports/exploitation.csv')
@_auth_required
def rapports_exploitation_csv():
    if not _can_report():
        return redirect('/')
    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT l.code, l.nom, l.ville_depart, l.ville_arrivee,
                        COUNT(vo.id) AS nb_voyages,
                        COALESCE(SUM(vo.places_vendues), 0) AS passagers,
                        COALESCE(SUM(vo.recette_reelle), 0) AS ca
                 FROM lignes l
                 LEFT JOIN voyages vo ON vo.ligne_id = l.id
                    AND strftime('%Y-%m', vo.date_voyage)=?
                 WHERE l.actif=1
                 GROUP BY l.id
                 ORDER BY ca DESC""", (mois,))
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(['Code', 'Nom', 'Départ', 'Arrivée', 'Nb voyages', 'Passagers', 'CA (FCFA)'])
    for r in rows:
        w.writerow([r['code'], r['nom'], r['ville_depart'], r['ville_arrivee'],
                    r['nb_voyages'], r['passagers'], r['ca']])
    _log('RAPPORT_EXPLOITATION', f"Export mois {mois}")
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=exploitation_{mois}.csv'}
    )


# ================================================================
# ==================== RENTABILITÉ VÉHICULES ====================
# ================================================================
@rapports_bp.route('/rapports/rentabilite-vehicules')
@_auth_required
def rapports_rentabilite():
    if not _can_report():
        flash("Accès réservé", "danger")
        return redirect('/')

    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT v.id, v.immatriculation, v.modele, v.kilometrage,
                        m.nom AS marque_nom,
                        COUNT(vo.id) AS nb_voyages,
                        COALESCE(SUM(vo.recette_reelle), 0) AS ca,
                        COALESCE(SUM(vo.places_vendues), 0) AS passagers,
                        (SELECT COALESCE(SUM(montant_total), 0) FROM carburant
                         WHERE vehicule_id=v.id AND strftime('%Y-%m', date_bon)=?) AS cout_carburant,
                        (SELECT COALESCE(SUM(cout_total), 0) FROM maintenance
                         WHERE vehicule_id=v.id AND strftime('%Y-%m', date_debut)=?) AS cout_maint
                 FROM vehicules v
                 LEFT JOIN marques m ON v.marque_id = m.id
                 LEFT JOIN voyages vo ON vo.vehicule_id = v.id
                    AND strftime('%Y-%m', vo.date_voyage)=?
                 WHERE v.actif=1
                 GROUP BY v.id
                 ORDER BY ca DESC""", (mois, mois, mois))
    vehicules = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-bus"></i> Rentabilité par véhicule — {mois}</h2></div>
      <div style="display:flex;gap:10px">
        <a href="/rapports" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        <a href="/rapports/rentabilite-vehicules.csv?mois={mois}" class="btn btn-primary">
          <i class="fas fa-download"></i> Export CSV
        </a>
      </div>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Immatriculation</th><th>Marque/Modèle</th><th>Voyages</th>
          <th>Passagers</th><th>CA</th><th>Carburant</th><th>Maintenance</th>
          <th>Marge nette</th><th>Km</th>
        </tr></thead><tbody>
    """
    for v in vehicules:
        marge = (v['ca'] or 0) - (v['cout_carburant'] or 0) - (v['cout_maint'] or 0)
        badge_m = 'badge-success' if marge > 0 else 'badge-danger'
        content += f"""
        <tr>
          <td><strong>{v['immatriculation']}</strong></td>
          <td>{v['marque_nom'] or ''} {v['modele'] or ''}</td>
          <td>{v['nb_voyages']}</td>
          <td>{v['passagers']}</td>
          <td><strong>{_fmt_fcfa(v['ca'])}</strong></td>
          <td style="color:#dc2626">-{_fmt_fcfa(v['cout_carburant'])}</td>
          <td style="color:#dc2626">-{_fmt_fcfa(v['cout_maint'])}</td>
          <td><span class="badge {badge_m}">{_fmt_fcfa(marge)}</span></td>
          <td><small>{v['kilometrage'] or 0} km</small></td>
        </tr>"""
    if not vehicules:
        content += '<tr><td colspan="9" class="empty">Aucune donnée</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='rapports', title='Rentabilité véhicules')


@rapports_bp.route('/rapports/rentabilite-vehicules.csv')
@_auth_required
def rapports_rentabilite_csv():
    if not _can_report():
        return redirect('/')
    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT v.immatriculation, v.modele, v.kilometrage,
                        COUNT(vo.id) AS nb_voyages,
                        COALESCE(SUM(vo.recette_reelle), 0) AS ca,
                        (SELECT COALESCE(SUM(montant_total), 0) FROM carburant
                         WHERE vehicule_id=v.id AND strftime('%Y-%m', date_bon)=?) AS cout_carburant,
                        (SELECT COALESCE(SUM(cout_total), 0) FROM maintenance
                         WHERE vehicule_id=v.id AND strftime('%Y-%m', date_debut)=?) AS cout_maint
                 FROM vehicules v
                 LEFT JOIN voyages vo ON vo.vehicule_id = v.id
                    AND strftime('%Y-%m', vo.date_voyage)=?
                 WHERE v.actif=1
                 GROUP BY v.id
                 ORDER BY ca DESC""", (mois, mois, mois))
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(['Immatriculation', 'Modèle', 'Km', 'Nb voyages', 'CA',
                'Carburant', 'Maintenance', 'Marge nette'])
    for r in rows:
        marge = (r['ca'] or 0) - (r['cout_carburant'] or 0) - (r['cout_maint'] or 0)
        w.writerow([r['immatriculation'], r['modele'], r['kilometrage'],
                    r['nb_voyages'], r['ca'], r['cout_carburant'],
                    r['cout_maint'], marge])
    _log('RAPPORT_RENTABILITE', f"Export mois {mois}")
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=rentabilite_{mois}.csv'}
    )


# ================================================================
# ==================== CHAUFFEURS ====================
# ================================================================
@rapports_bp.route('/rapports/chauffeurs')
@_auth_required
def rapports_chauffeurs():
    if not _can_report():
        flash("Accès réservé", "danger")
        return redirect('/')

    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT ch.id, ch.matricule, ch.nom, ch.prenom, ch.telephone,
                        COUNT(vo.id) AS nb_voyages,
                        COALESCE(SUM(vo.recette_reelle), 0) AS ca,
                        COALESCE(SUM(vo.places_vendues), 0) AS passagers,
                        (SELECT COUNT(*) FROM amendes WHERE chauffeur_id=ch.id
                         AND strftime('%Y-%m', date_amende)=?) AS nb_amendes,
                        (SELECT COALESCE(SUM(montant), 0) FROM amendes WHERE chauffeur_id=ch.id
                         AND strftime('%Y-%m', date_amende)=?) AS total_amendes
                 FROM chauffeurs ch
                 LEFT JOIN voyages vo ON vo.chauffeur_id = ch.id
                    AND strftime('%Y-%m', vo.date_voyage)=?
                 WHERE ch.actif=1
                 GROUP BY ch.id
                 ORDER BY ca DESC""", (mois, mois, mois))
    chauffeurs = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-id-card"></i> Performance chauffeurs — {mois}</h2></div>
      <div style="display:flex;gap:10px">
        <a href="/rapports" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        <a href="/rapports/chauffeurs.csv?mois={mois}" class="btn btn-primary">
          <i class="fas fa-download"></i> Export CSV
        </a>
      </div>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Matricule</th><th>Nom</th><th>Voyages</th>
          <th>Passagers</th><th>Recettes</th><th>Amendes</th><th>Montant amendes</th>
        </tr></thead><tbody>
    """
    for ch in chauffeurs:
        badge_a = 'badge-danger' if ch['nb_amendes'] > 0 else 'badge-success'
        content += f"""
        <tr>
          <td><strong>{ch['matricule']}</strong></td>
          <td>{ch['prenom']} {ch['nom']}
              <div style="font-size:0.72rem;color:#94a3b8">{ch['telephone'] or ''}</div></td>
          <td><span class="badge badge-primary">{ch['nb_voyages']}</span></td>
          <td>{ch['passagers']}</td>
          <td><strong>{_fmt_fcfa(ch['ca'])}</strong></td>
          <td><span class="badge {badge_a}">{ch['nb_amendes']}</span></td>
          <td>{_fmt_fcfa(ch['total_amendes'])}</td>
        </tr>"""
    if not chauffeurs:
        content += '<tr><td colspan="7" class="empty">Aucune donnée</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='rapports', title='Performance chauffeurs')


@rapports_bp.route('/rapports/chauffeurs.csv')
@_auth_required
def rapports_chauffeurs_csv():
    if not _can_report():
        return redirect('/')
    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT ch.matricule, ch.nom, ch.prenom, ch.telephone,
                        COUNT(vo.id) AS nb_voyages,
                        COALESCE(SUM(vo.recette_reelle), 0) AS ca,
                        (SELECT COUNT(*) FROM amendes WHERE chauffeur_id=ch.id
                         AND strftime('%Y-%m', date_amende)=?) AS nb_amendes
                 FROM chauffeurs ch
                 LEFT JOIN voyages vo ON vo.chauffeur_id = ch.id
                    AND strftime('%Y-%m', vo.date_voyage)=?
                 WHERE ch.actif=1
                 GROUP BY ch.id
                 ORDER BY ca DESC""", (mois, mois))
    rows = c.fetchall()
    conn.close()
    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(['Matricule', 'Nom', 'Prénom', 'Téléphone', 'Nb voyages', 'CA', 'Amendes'])
    for r in rows:
        w.writerow([r['matricule'], r['nom'], r['prenom'], r['telephone'],
                    r['nb_voyages'], r['ca'], r['nb_amendes']])
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=chauffeurs_{mois}.csv'}
    )


# ================================================================
# ==================== CARBURANT ====================
# ================================================================
@rapports_bp.route('/rapports/carburant')
@_auth_required
def rapports_carburant():
    if not _can_report():
        flash("Accès réservé", "danger")
        return redirect('/')

    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT v.id, v.immatriculation, v.consommation_base,
                        COUNT(cb.id) AS nb_bons,
                        COALESCE(SUM(cb.litres), 0) AS litres,
                        COALESCE(SUM(cb.montant_total), 0) AS cout,
                        COALESCE(AVG(cb.consommation_calculee), 0) AS conso_moy,
                        SUM(CASE WHEN cb.statut='Anomalie' THEN 1 ELSE 0 END) AS anomalies
                 FROM vehicules v
                 LEFT JOIN carburant cb ON cb.vehicule_id = v.id
                    AND strftime('%Y-%m', cb.date_bon)=?
                 WHERE v.actif=1
                 GROUP BY v.id
                 HAVING nb_bons > 0
                 ORDER BY cout DESC""", (mois,))
    rows = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-gas-pump"></i> Consommation carburant — {mois}</h2></div>
      <div style="display:flex;gap:10px">
        <a href="/rapports" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        <a href="/rapports/carburant.csv?mois={mois}" class="btn btn-primary">
          <i class="fas fa-download"></i> Export CSV
        </a>
      </div>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Véhicule</th><th>Bons</th><th>Litres</th><th>Coût</th>
          <th>Conso réelle</th><th>Conso base</th><th>Écart</th><th>Anomalies</th>
        </tr></thead><tbody>
    """
    for r in rows:
        ecart = ((r['conso_moy'] - r['consommation_base']) / r['consommation_base'] * 100) if r['consommation_base'] else 0
        badge_e = 'badge-danger' if abs(ecart) > 15 else 'badge-success'
        badge_a = 'badge-danger' if r['anomalies'] > 0 else 'badge-success'
        content += f"""
        <tr>
          <td><strong>{r['immatriculation']}</strong></td>
          <td>{r['nb_bons']}</td>
          <td><strong>{r['litres']:.0f} L</strong></td>
          <td>{_fmt_fcfa(r['cout'])}</td>
          <td>{r['conso_moy']:.1f} L/100</td>
          <td>{r['consommation_base']:.1f} L/100</td>
          <td><span class="badge {badge_e}">{ecart:+.1f}%</span></td>
          <td><span class="badge {badge_a}">{r['anomalies']}</span></td>
        </tr>"""
    if not rows:
        content += '<tr><td colspan="8" class="empty">Aucune donnée</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='rapports', title='Carburant')


@rapports_bp.route('/rapports/carburant.csv')
@_auth_required
def rapports_carburant_csv():
    if not _can_report():
        return redirect('/')
    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT v.immatriculation, v.consommation_base,
                        COUNT(cb.id) AS nb_bons,
                        COALESCE(SUM(cb.litres), 0) AS litres,
                        COALESCE(SUM(cb.montant_total), 0) AS cout,
                        COALESCE(AVG(cb.consommation_calculee), 0) AS conso_moy,
                        SUM(CASE WHEN cb.statut='Anomalie' THEN 1 ELSE 0 END) AS anomalies
                 FROM vehicules v
                 LEFT JOIN carburant cb ON cb.vehicule_id = v.id
                    AND strftime('%Y-%m', cb.date_bon)=?
                 WHERE v.actif=1
                 GROUP BY v.id
                 HAVING nb_bons > 0
                 ORDER BY cout DESC""", (mois,))
    rows = c.fetchall()
    conn.close()
    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(['Immatriculation', 'Bons', 'Litres', 'Coût', 'Conso réelle', 'Conso base', 'Anomalies'])
    for r in rows:
        w.writerow([r['immatriculation'], r['nb_bons'], r['litres'], r['cout'],
                    round(r['conso_moy'], 2), r['consommation_base'], r['anomalies']])
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=carburant_{mois}.csv'}
    )


# ================================================================
# ==================== BILLETS ====================
# ================================================================
@rapports_bp.route('/rapports/billets.csv')
@_auth_required
def rapports_billets_csv():
    if not _can_report():
        return redirect('/')
    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT b.numero, b.date_emission, b.passager_nom, b.passager_telephone,
                        b.numero_place, b.classe, b.prix, b.mode_paiement, b.statut,
                        l.code AS ligne, l.ville_depart, l.ville_arrivee,
                        vo.date_voyage, v.immatriculation
                 FROM billets b
                 LEFT JOIN voyages vo ON b.voyage_id = vo.id
                 LEFT JOIN lignes l ON vo.ligne_id = l.id
                 LEFT JOIN vehicules v ON vo.vehicule_id = v.id
                 WHERE strftime('%Y-%m', b.date_emission)=?
                 ORDER BY b.date_emission DESC""", (mois,))
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(['N° Billet', 'Date émission', 'Passager', 'Téléphone', 'Place',
                'Classe', 'Prix', 'Paiement', 'Statut',
                'Ligne', 'Départ', 'Arrivée', 'Date voyage', 'Véhicule'])
    for r in rows:
        w.writerow([r['numero'], r['date_emission'], r['passager_nom'],
                    r['passager_telephone'], r['numero_place'], r['classe'],
                    r['prix'], r['mode_paiement'], r['statut'],
                    r['ligne'], r['ville_depart'], r['ville_arrivee'],
                    r['date_voyage'], r['immatriculation']])
    _log('RAPPORT_BILLETS', f"Export {len(rows)} billets mois {mois}")
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=billets_{mois}.csv'}
    )


# ================================================================
# ==================== AMENDES ====================
# ================================================================
@rapports_bp.route('/rapports/amendes.csv')
@_auth_required
def rapports_amendes_csv():
    if not _can_report():
        return redirect('/')
    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT a.date_amende, a.motif, a.montant, a.lieu, a.autorite,
                        a.statut, v.immatriculation,
                        ch.nom AS ch_nom, ch.prenom AS ch_prenom
                 FROM amendes a
                 LEFT JOIN vehicules v ON a.vehicule_id = v.id
                 LEFT JOIN chauffeurs ch ON a.chauffeur_id = ch.id
                 WHERE strftime('%Y-%m', a.date_amende)=?
                 ORDER BY a.date_amende DESC""", (mois,))
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(['Date', 'Véhicule', 'Chauffeur', 'Motif', 'Montant', 'Lieu', 'Autorité', 'Statut'])
    for r in rows:
        w.writerow([r['date_amende'], r['immatriculation'], f"{r['ch_prenom'] or ''} {r['ch_nom'] or ''}".strip(),
                    r['motif'], r['montant'], r['lieu'], r['autorite'], r['statut']])
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=amendes_{mois}.csv'}
    )


# ================================================================
# ==================== AMENDES — VUE ====================
# ================================================================
@rapports_bp.route('/amendes')
@_auth_required
def amendes_list():
    if current_user.role not in ('admin', 'directeur', 'chef_exploitation'):
        flash("Accès réservé", "danger")
        return redirect('/')

    statut = request.args.get('statut') or ''
    conn = _db()
    c = conn.cursor()
    sql = """SELECT a.*, v.immatriculation,
                    ch.nom AS ch_nom, ch.prenom AS ch_prenom
             FROM amendes a
             LEFT JOIN vehicules v ON a.vehicule_id = v.id
             LEFT JOIN chauffeurs ch ON a.chauffeur_id = ch.id
             WHERE 1=1"""
    params = []
    if statut:
        sql += " AND a.statut=?"
        params.append(statut)
    sql += " ORDER BY a.date_amende DESC LIMIT 100"
    c.execute(sql, params)
    amendes = c.fetchall()

    c.execute("""SELECT COALESCE(SUM(montant), 0) AS total,
                        COUNT(*) AS nb,
                        SUM(CASE WHEN statut='À payer' THEN 1 ELSE 0 END) AS a_payer
                 FROM amendes""")
    stats = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-gavel"></i> Amendes</h2>
        <div class="page-subtitle">{len(amendes)} amende(s)</div></div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-file"></i></div>
        <div class="stat-value">{stats['nb']}</div>
        <div class="stat-label">Total amendes</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-money-bill"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(stats['total'])}</div>
        <div class="stat-label">Montant total</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-hourglass-half"></i></div>
        <div class="stat-value">{stats['a_payer']}</div>
        <div class="stat-label">À payer</div></div>
    </div>

    <div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Date</th><th>Véhicule</th><th>Chauffeur</th>
                 <th>Motif</th><th>Montant</th><th>Statut</th></tr></thead>
      <tbody>"""
    for a in amendes:
        badge = 'badge-danger' if a['statut'] == 'À payer' else 'badge-success'
        content += f"""
        <tr>
          <td>{a['date_amende']}</td>
          <td>{a['immatriculation'] or '-'}</td>
          <td>{a['ch_prenom'] or ''} {a['ch_nom'] or '-'}</td>
          <td>{a['motif']}</td>
          <td><strong>{_fmt_fcfa(a['montant'])}</strong></td>
          <td><span class="badge {badge}">{a['statut']}</span></td>
        </tr>"""
    if not amendes:
        content += '<tr><td colspan="6" class="empty">Aucune amende</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='amendes', title='Amendes')


# ================================================================
# ==================== MAINTENANCE ====================
# ================================================================
@rapports_bp.route('/maintenance')
@_auth_required
def maintenance_list():
    if current_user.role not in ('admin', 'directeur', 'chef_exploitation', 'mecano'):
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT m.*, v.immatriculation, v.modele
                 FROM maintenance m
                 LEFT JOIN vehicules v ON m.vehicule_id = v.id
                 ORDER BY m.date_debut DESC LIMIT 100""")
    maintenances = c.fetchall()

    c.execute("""SELECT COALESCE(SUM(cout_total), 0) AS total,
                        COUNT(*) AS nb,
                        SUM(CASE WHEN statut='En cours' THEN 1 ELSE 0 END) AS en_cours
                 FROM maintenance""")
    stats = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-wrench"></i> Maintenance</h2>
        <div class="page-subtitle">{len(maintenances)} intervention(s)</div></div>
      {'<a href="/maintenance/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle intervention</a>' if current_user.role in ('admin','directeur','chef_exploitation','mecano') else ''}
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-wrench"></i></div>
        <div class="stat-value">{stats['nb']}</div>
        <div class="stat-label">Interventions</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-money-bill"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(stats['total'])}</div>
        <div class="stat-label">Coût total</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-hourglass-half"></i></div>
        <div class="stat-value">{stats['en_cours']}</div>
        <div class="stat-label">En cours</div></div>
    </div>

    <div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Date</th><th>Véhicule</th><th>Type</th>
                 <th>Description</th><th>Garage</th><th>Coût</th><th>Statut</th></tr></thead>
      <tbody>"""
    for m in maintenances:
        badge = 'badge-success' if m['statut'] == 'Terminée' else 'badge-warning'
        content += f"""
        <tr>
          <td>{m['date_debut']}</td>
          <td><strong>{m['immatriculation'] or '-'}</strong>
              <div style="font-size:0.72rem;color:#94a3b8">{m['modele'] or ''}</div></td>
          <td>{m['type_maintenance'] or '-'}</td>
          <td><small>{m['description'][:60]}</small></td>
          <td>{m['garage'] or '-'}</td>
          <td><strong>{_fmt_fcfa(m['cout_total'])}</strong></td>
          <td><span class="badge {badge}">{m['statut']}</span></td>
        </tr>"""
    if not maintenances:
        content += '<tr><td colspan="7" class="empty">Aucune maintenance</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='maintenance', title='Maintenance')
