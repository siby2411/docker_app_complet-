"""
📊 MicroFinance 2.0 — Rapports & Statistiques BCEAO
Exports CSV · États réglementaires · Analyses
"""
from flask import Blueprint, request, redirect, flash, Response, jsonify
from flask_login import current_user
import sqlite3
import csv
import io
from datetime import datetime, timedelta

rapports_bp = Blueprint('rapports', __name__)
_deps = {}


def init_rapports(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(rapports_bp)
    print("[RAPPORTS] ✅ Module rapports complet enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='rapports', title='Rapports'):
    return _deps['render_page'](content, active=active, page_title=title)


def _auth_required(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if not (current_user and current_user.is_authenticated):
            return redirect('/login')
        return f(*a, **k)
    return w


def _can_report():
    return current_user and current_user.role in ('admin', 'directeur', 'analyste', 'auditeur')


def _fmt_fcfa(m):
    if not m:
        return "0 F"
    return f"{int(m):,} F".replace(",", " ")


def _fmt_pct(v):
    if v is None:
        return "0%"
    return f"{v:.1f}%"


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

    # KPIs
    c.execute("SELECT COUNT(*) FROM clients WHERE actif=1")
    nb_clients = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM credits WHERE statut='Actif'")
    nb_credits = c.fetchone()[0] or 0

    c.execute("SELECT COALESCE(SUM(solde_restant), 0) FROM credits WHERE statut='Actif'")
    encours = c.fetchone()[0] or 0

    c.execute("""SELECT COALESCE(SUM(montant_recu), 0) FROM remboursements
                 WHERE strftime('%Y-%m', date_paiement)=?""", (mois,))
    remboursements_mois = c.fetchone()[0] or 0

    c.execute("""SELECT COALESCE(SUM(solde), 0) FROM comptes_epargne WHERE statut='Actif'""")
    epargne = c.fetchone()[0] or 0

    c.execute("""SELECT COUNT(*) FROM echeances_credit WHERE statut='En retard'""")
    impayes = c.fetchone()[0] or 0

    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-file-invoice"></i> Rapports BCEAO</h2>
        <div class="page-subtitle">États réglementaires · Analyses · Exports</div></div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-users"></i></div>
        <div class="stat-value">{nb_clients}</div>
        <div class="stat-label">Clients</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-hand-holding-dollar"></i></div>
        <div class="stat-value">{nb_credits}</div>
        <div class="stat-label">Crédits actifs</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-coins"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(encours)}</div>
        <div class="stat-label">Encours total</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-triangle-exclamation"></i></div>
        <div class="stat-value">{impayes}</div>
        <div class="stat-label">Impayés</div></div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px">

      <div class="card" style="border-left:5px solid #0e7490">
        <h3 style="color:#0e7490;margin-bottom:10px"><i class="fas fa-users"></i> Clients</h3>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          Liste complète des clients avec KYC
        </p>
        <a href="/rapports/clients.csv" class="btn btn-primary btn-sm"><i class="fas fa-download"></i> CSV</a>
      </div>

      <div class="card" style="border-left:5px solid #10b981">
        <h3 style="color:#065f46;margin-bottom:10px"><i class="fas fa-hand-holding-dollar"></i> Crédits</h3>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          Portefeuille crédits avec statut
        </p>
        <a href="/rapports/credits.csv" class="btn btn-primary btn-sm"><i class="fas fa-download"></i> CSV</a>
      </div>

      <div class="card" style="border-left:5px solid #dc2626">
        <h3 style="color:#991b1b;margin-bottom:10px"><i class="fas fa-triangle-exclamation"></i> Impayés</h3>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          Échéances en retard avec jours
        </p>
        <a href="/rapports/impayes.csv" class="btn btn-primary btn-sm"><i class="fas fa-download"></i> CSV</a>
      </div>

      <div class="card" style="border-left:5px solid #f59e0b">
        <h3 style="color:#92400e;margin-bottom:10px"><i class="fas fa-calendar"></i> Échéancier</h3>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          Prochaines échéances 30 jours
        </p>
        <a href="/rapports/echeancier.csv" class="btn btn-primary btn-sm"><i class="fas fa-download"></i> CSV</a>
      </div>

      <div class="card" style="border-left:5px solid #7c3aed">
        <h3 style="color:#6d28d9;margin-bottom:10px"><i class="fas fa-piggy-bank"></i> Épargne</h3>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          Comptes et opérations épargne
        </p>
        <a href="/rapports/epargne.csv" class="btn btn-primary btn-sm"><i class="fas fa-download"></i> CSV</a>
      </div>

      <div class="card" style="border-left:5px solid #0891b2">
        <h3 style="color:#0e7490;margin-bottom:10px"><i class="fas fa-mobile-screen"></i> Mobile Money</h3>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          Transactions Wave, OM, Free
        </p>
        <a href="/rapports/mobile-money.csv" class="btn btn-primary btn-sm"><i class="fas fa-download"></i> CSV</a>
      </div>

      <div class="card" style="border-left:5px solid #16a34a">
        <h3 style="color:#065f46;margin-bottom:10px"><i class="fas fa-chart-line"></i> Statistiques</h3>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          Analyse par agence, produit, score
        </p>
        <a href="/statistiques" class="btn btn-primary btn-sm"><i class="fas fa-eye"></i> Voir</a>
      </div>

      <div class="card" style="border-left:5px solid #dc2626">
        <h3 style="color:#991b1b;margin-bottom:10px"><i class="fas fa-shield-halved"></i> Conformité</h3>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          Ratios BCEAO et provisions
        </p>
        <a href="/rapports/conformite" class="btn btn-primary btn-sm"><i class="fas fa-eye"></i> Voir</a>
      </div>

    </div>
    """
    return _render(content, active='rapports', title='Rapports BCEAO')


# ================================================================
# ==================== EXPORTS CSV ====================
# ================================================================
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


@rapports_bp.route('/rapports/clients.csv')
@_auth_required
def rapports_clients_csv():
    if not _can_report():
        return redirect('/')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT cl.code, cl.type_client, cl.nom, cl.prenom,
                        cl.date_naissance, cl.sexe, cl.telephone, cl.email,
                        cl.adresse, cl.ville, r.nom AS region,
                        cl.numero_cni, cl.profession, cl.revenu_mensuel,
                        cl.activite_principale, a.nom AS agence,
                        cl.statut, cl.date_adhesion, cl.kyc_statut, cl.score_interne
                 FROM clients cl
                 LEFT JOIN regions r ON cl.region_id = r.id
                 LEFT JOIN agences a ON cl.agence_id = a.id
                 WHERE cl.actif=1 ORDER BY cl.nom""")
    rows = c.fetchall()
    conn.close()

    _deps['log_action'](current_user.id, 'EXPORT_CLIENTS', f"{len(rows)} clients")

    return _csv_response(rows,
        ['code', 'type_client', 'nom', 'prenom', 'date_naissance', 'sexe',
         'telephone', 'email', 'adresse', 'ville', 'region', 'numero_cni',
         'profession', 'revenu_mensuel', 'activite_principale', 'agence',
         'statut', 'date_adhesion', 'kyc_statut', 'score_interne'],
        f'clients_{datetime.now().strftime("%Y%m%d")}.csv')


@rapports_bp.route('/rapports/credits.csv')
@_auth_required
def rapports_credits_csv():
    if not _can_report():
        return redirect('/')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT cr.reference, cl.code AS client_code, cl.nom AS client_nom,
                        cl.prenom AS client_prenom, p.nom AS produit,
                        cr.montant_principal, cr.taux_interet, cr.duree_mois,
                        cr.date_decaissement, cr.date_fin_prevue,
                        cr.montant_total_du, cr.montant_rembourse, cr.solde_restant,
                        cr.nb_echeances, cr.nb_echeances_payees,
                        cr.statut, cr.classification, a.nom AS agence
                 FROM credits cr
                 LEFT JOIN clients cl ON cr.client_id = cl.id
                 LEFT JOIN produits p ON cr.produit_id = p.id
                 LEFT JOIN agences a ON cr.agence_id = a.id
                 ORDER BY cr.date_decaissement DESC""")
    rows = c.fetchall()
    conn.close()

    _deps['log_action'](current_user.id, 'EXPORT_CREDITS', f"{len(rows)} crédits")

    return _csv_response(rows,
        ['reference', 'client_code', 'client_nom', 'client_prenom', 'produit',
         'montant_principal', 'taux_interet', 'duree_mois', 'date_decaissement',
         'date_fin_prevue', 'montant_total_du', 'montant_rembourse', 'solde_restant',
         'nb_echeances', 'nb_echeances_payees', 'statut', 'classification', 'agence'],
        f'credits_{datetime.now().strftime("%Y%m%d")}.csv')


@rapports_bp.route('/rapports/impayes.csv')
@_auth_required
def rapports_impayes_csv():
    if not _can_report():
        return redirect('/')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT cl.code AS client_code, cl.nom, cl.prenom, cl.telephone,
                        cr.reference AS credit_ref, p.nom AS produit,
                        ec.numero_echeance, ec.date_echeance,
                        ec.montant_total, ec.montant_restant,
                        ec.jours_retard, a.nom AS agence
                 FROM echeances_credit ec
                 INNER JOIN credits cr ON ec.credit_id = cr.id
                 INNER JOIN clients cl ON cr.client_id = cl.id
                 LEFT JOIN produits p ON cr.produit_id = p.id
                 LEFT JOIN agences a ON cr.agence_id = a.id
                 WHERE ec.statut IN ('En retard', 'Impayé') AND cr.statut='Actif'
                 ORDER BY ec.jours_retard DESC""")
    rows = c.fetchall()
    conn.close()

    _deps['log_action'](current_user.id, 'EXPORT_IMPAYES', f"{len(rows)} impayés")

    return _csv_response(rows,
        ['client_code', 'nom', 'prenom', 'telephone', 'credit_ref', 'produit',
         'numero_echeance', 'date_echeance', 'montant_total', 'montant_restant',
         'jours_retard', 'agence'],
        f'impayes_{datetime.now().strftime("%Y%m%d")}.csv')


@rapports_bp.route('/rapports/echeancier.csv')
@_auth_required
def rapports_echeancier_csv():
    if not _can_report():
        return redirect('/')

    date_limite = (datetime.now() + timedelta(days=30)).date().isoformat()

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT cl.code AS client_code, cl.nom, cl.prenom, cl.telephone,
                        cr.reference AS credit_ref,
                        ec.numero_echeance, ec.date_echeance,
                        ec.montant_capital, ec.montant_interets, ec.montant_total,
                        a.nom AS agence
                 FROM echeances_credit ec
                 INNER JOIN credits cr ON ec.credit_id = cr.id
                 INNER JOIN clients cl ON cr.client_id = cl.id
                 LEFT JOIN agences a ON cr.agence_id = a.id
                 WHERE ec.statut IN ('À venir', 'En retard')
                   AND date(ec.date_echeance) <= date(?)
                   AND cr.statut = 'Actif'
                 ORDER BY ec.date_echeance ASC""", (date_limite,))
    rows = c.fetchall()
    conn.close()

    _deps['log_action'](current_user.id, 'EXPORT_ECHEANCIER', f"{len(rows)} échéances")

    return _csv_response(rows,
        ['client_code', 'nom', 'prenom', 'telephone', 'credit_ref',
         'numero_echeance', 'date_echeance', 'montant_capital',
         'montant_interets', 'montant_total', 'agence'],
        f'echeancier_{datetime.now().strftime("%Y%m%d")}.csv')


@rapports_bp.route('/rapports/epargne.csv')
@_auth_required
def rapports_epargne_csv():
    if not _can_report():
        return redirect('/')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT ce.numero_compte, cl.code AS client_code,
                        cl.nom, cl.prenom, cl.telephone,
                        ce.solde, ce.solde_disponible,
                        ce.date_ouverture, ce.date_derniere_operation,
                        a.nom AS agence, ce.statut
                 FROM comptes_epargne ce
                 LEFT JOIN clients cl ON ce.client_id = cl.id
                 LEFT JOIN agences a ON ce.agence_id = a.id
                 WHERE ce.statut='Actif'
                 ORDER BY ce.solde DESC""")
    rows = c.fetchall()
    conn.close()

    _deps['log_action'](current_user.id, 'EXPORT_EPARGNE', f"{len(rows)} comptes")

    return _csv_response(rows,
        ['numero_compte', 'client_code', 'nom', 'prenom', 'telephone',
         'solde', 'solde_disponible', 'date_ouverture', 'date_derniere_operation',
         'agence', 'statut'],
        f'epargne_{datetime.now().strftime("%Y%m%d")}.csv')


@rapports_bp.route('/rapports/mobile-money.csv')
@_auth_required
def rapports_mm_csv():
    if not _can_report():
        return redirect('/')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT t.reference, t.date_initiation, t.fournisseur,
                        t.telephone, cl.code AS client_code,
                        cl.nom, cl.prenom, t.type_transaction,
                        t.montant, t.frais, t.statut
                 FROM transactions_mobile t
                 LEFT JOIN clients cl ON t.client_id = cl.id
                 ORDER BY t.date_initiation DESC LIMIT 10000""")
    rows = c.fetchall()
    conn.close()

    _deps['log_action'](current_user.id, 'EXPORT_MM', f"{len(rows)} transactions")

    return _csv_response(rows,
        ['reference', 'date_initiation', 'fournisseur', 'telephone',
         'client_code', 'nom', 'prenom', 'type_transaction',
         'montant', 'frais', 'statut'],
        f'mobile_money_{datetime.now().strftime("%Y%m%d")}.csv')


# ================================================================
# ==================== STATISTIQUES ====================
# ================================================================
@rapports_bp.route('/statistiques')
@_auth_required
def statistiques():
    if not _can_report():
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()

    # Par agence
    c.execute("""SELECT a.nom,
                        (SELECT COUNT(*) FROM clients WHERE agence_id=a.id AND actif=1) AS nb_clients,
                        (SELECT COUNT(*) FROM credits WHERE agence_id=a.id AND statut='Actif') AS nb_credits,
                        (SELECT COALESCE(SUM(solde_restant), 0) FROM credits WHERE agence_id=a.id AND statut='Actif') AS encours,
                        (SELECT COUNT(*) FROM echeances_credit ec
                         INNER JOIN credits cr ON ec.credit_id=cr.id
                         WHERE cr.agence_id=a.id AND ec.statut='En retard') AS nb_impayes
                 FROM agences a WHERE a.actif=1
                 ORDER BY encours DESC""")
    par_agence = c.fetchall()

    # Par produit
    c.execute("""SELECT p.nom, p.code,
                        COUNT(cr.id) AS nb,
                        COALESCE(SUM(cr.montant_principal), 0) AS total,
                        COALESCE(SUM(cr.solde_restant), 0) AS solde
                 FROM produits p
                 LEFT JOIN credits cr ON cr.produit_id=p.id AND cr.statut='Actif'
                 WHERE p.actif=1
                 GROUP BY p.id HAVING nb > 0
                 ORDER BY total DESC""")
    par_produit = c.fetchall()

    # Par score
    c.execute("""SELECT
                    SUM(CASE WHEN score >= 750 THEN 1 ELSE 0 END) AS excellent,
                    SUM(CASE WHEN score >= 650 AND score < 750 THEN 1 ELSE 0 END) AS bon,
                    SUM(CASE WHEN score >= 550 AND score < 650 THEN 1 ELSE 0 END) AS moyen,
                    SUM(CASE WHEN score >= 450 AND score < 550 THEN 1 ELSE 0 END) AS faible,
                    SUM(CASE WHEN score < 450 THEN 1 ELSE 0 END) AS tres_faible
                 FROM scores_credit""")
    par_score = c.fetchone()

    # Progression mensuelle (6 mois)
    c.execute("""SELECT strftime('%Y-%m', date_decaissement) AS mois,
                        COUNT(*) AS nb,
                        COALESCE(SUM(montant_principal), 0) AS montant
                 FROM credits
                 WHERE date(date_decaissement) >= date('now', '-6 months')
                 GROUP BY mois ORDER BY mois""")
    par_mois = c.fetchall()

    conn.close()

    max_encours = max([a['encours'] for a in par_agence], default=1)
    max_produit = max([p['total'] for p in par_produit], default=1)
    max_mois = max([m['montant'] for m in par_mois], default=1)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-chart-line"></i> Statistiques</h2>
        <div class="page-subtitle">Analyse du portefeuille SFD</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-building"></i> Performance par agence</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Agence</th><th>Clients</th><th>Crédits actifs</th>
                   <th>Encours</th><th>Impayés</th><th>Taux recouvrement</th></tr></thead>
        <tbody>
    """
    for a in par_agence:
        taux = 100 - ((a['nb_impayes'] or 0) * 100 / max(a['nb_credits'] or 1, 1))
        badge = 'badge-success' if taux > 90 else ('badge-warning' if taux > 75 else 'badge-danger')
        content += f"""
        <tr>
          <td><strong>{a['nom']}</strong></td>
          <td>{a['nb_clients']}</td>
          <td>{a['nb_credits']}</td>
          <td><strong>{_fmt_fcfa(a['encours'])}</strong></td>
          <td><span class="badge badge-danger">{a['nb_impayes']}</span></td>
          <td><span class="badge {badge}">{taux:.1f}%</span></td>
        </tr>"""
    content += "</tbody></table></div></div>"

    # Par produit
    content += """
    <div class="card">
      <div class="card-header"><h3><i class="fas fa-chart-pie"></i> Portefeuille par produit</h3></div>
    """
    for p in par_produit:
        pct = (p['total'] / max_produit * 100) if max_produit else 0
        content += f"""
        <div style="margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <span style="font-weight:700">{p['nom']} <small style="color:#94a3b8">({p['code']})</small></span>
            <strong style="color:#0e7490">{p['nb']} crédits · {_fmt_fcfa(p['total'])}</strong>
          </div>
          <div style="background:#f0fdff;border-radius:6px;height:10px;overflow:hidden">
            <div style="background:linear-gradient(90deg,#0e7490,#22d3ee);height:100%;width:{pct}%"></div>
          </div>
        </div>"""
    content += "</div>"

    # Par score
    total_scores = sum([v or 0 for v in [par_score['excellent'], par_score['bon'],
                                          par_score['moyen'], par_score['faible'],
                                          par_score['tres_faible']]])

    content += f"""
    <div class="card">
      <div class="card-header"><h3><i class="fas fa-robot"></i> Répartition par score IA</h3></div>
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:15px">
        <div style="text-align:center;padding:18px;background:#d1fae5;border-radius:12px">
          <div style="font-size:2rem;font-weight:900;color:#065f46">{par_score['excellent'] or 0}</div>
          <div style="font-size:0.75rem;font-weight:800;text-transform:uppercase;color:#065f46">Excellent</div>
          <div style="font-size:0.7rem;color:#64748b">≥ 750</div>
        </div>
        <div style="text-align:center;padding:18px;background:#dcfce7;border-radius:12px">
          <div style="font-size:2rem;font-weight:900;color:#15803d">{par_score['bon'] or 0}</div>
          <div style="font-size:0.75rem;font-weight:800;text-transform:uppercase;color:#15803d">Bon</div>
          <div style="font-size:0.7rem;color:#64748b">650-749</div>
        </div>
        <div style="text-align:center;padding:18px;background:#fef3c7;border-radius:12px">
          <div style="font-size:2rem;font-weight:900;color:#92400e">{par_score['moyen'] or 0}</div>
          <div style="font-size:0.75rem;font-weight:800;text-transform:uppercase;color:#92400e">Moyen</div>
          <div style="font-size:0.7rem;color:#64748b">550-649</div>
        </div>
        <div style="text-align:center;padding:18px;background:#fed7aa;border-radius:12px">
          <div style="font-size:2rem;font-weight:900;color:#9a3412">{par_score['faible'] or 0}</div>
          <div style="font-size:0.75rem;font-weight:800;text-transform:uppercase;color:#9a3412">Faible</div>
          <div style="font-size:0.7rem;color:#64748b">450-549</div>
        </div>
        <div style="text-align:center;padding:18px;background:#fee2e2;border-radius:12px">
          <div style="font-size:2rem;font-weight:900;color:#991b1b">{par_score['tres_faible'] or 0}</div>
          <div style="font-size:0.75rem;font-weight:800;text-transform:uppercase;color:#991b1b">Très faible</div>
          <div style="font-size:0.7rem;color:#64748b">&lt; 450</div>
        </div>
      </div>
    </div>"""

    # Progression mensuelle
    if par_mois:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-chart-bar"></i> Évolution mensuelle (6 mois)</h3></div>
        """
        for m in par_mois:
            pct = (m['montant'] / max_mois * 100) if max_mois else 0
            content += f"""
            <div style="margin-bottom:12px">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="font-weight:700">{m['mois']}</span>
                <strong style="color:#0e7490">{m['nb']} crédits · {_fmt_fcfa(m['montant'])}</strong>
              </div>
              <div style="background:#f0fdff;border-radius:6px;height:10px;overflow:hidden">
                <div style="background:linear-gradient(90deg,#0e7490,#22d3ee);height:100%;width:{pct}%"></div>
              </div>
            </div>"""
        content += "</div>"

    return _render(content, active='rapports', title='Statistiques')


@rapports_bp.route('/rapports/conformite')
@_auth_required
def conformite_bceao():
    if not _can_report():
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()

    # Encours total
    c.execute("SELECT COALESCE(SUM(solde_restant), 0) FROM credits WHERE statut='Actif'")
    encours = c.fetchone()[0] or 0

    # Classification
    c.execute("""SELECT classification,
                        COUNT(*) AS nb,
                        COALESCE(SUM(solde_restant), 0) AS montant
                 FROM credits WHERE statut='Actif'
                 GROUP BY classification""")
    classifications = c.fetchall()

    # Provisions
    provisions_map = {
        'Sain': 0,
        'Sous surveillance': 5,
        'Douteux': 50,
        'Compromis': 100
    }

    total_provision = 0
    classif_data = []
    for cl in classifications:
        taux = provisions_map.get(cl['classification'], 0)
        provision = int((cl['montant'] or 0) * taux / 100)
        total_provision += provision
        classif_data.append({
            'classification': cl['classification'],
            'nb': cl['nb'],
            'montant': cl['montant'],
            'taux': taux,
            'provision': provision
        })

    # Épargne
    c.execute("SELECT COALESCE(SUM(solde), 0) FROM comptes_epargne WHERE statut='Actif'")
    epargne = c.fetchone()[0] or 0

    # Ratio de liquidité
    c.execute("SELECT COALESCE(SUM(montant), 0) FROM transactions_mobile WHERE statut='Réussi'")
    transactions_mm = c.fetchone()[0] or 0

    ratio = (epargne / encours * 100) if encours else 0

    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-shield-halved"></i> Conformité BCEAO</h2>
        <div class="page-subtitle">Ratios réglementaires et provisions</div></div>
      <a href="/rapports" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-hand-holding-dollar"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(encours)}</div>
        <div class="stat-label">Encours crédits</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-piggy-bank"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(epargne)}</div>
        <div class="stat-label">Encours épargne</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-shield"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(total_provision)}</div>
        <div class="stat-label">Provisions totales</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-percent"></i></div>
        <div class="stat-value">{ratio:.1f}%</div>
        <div class="stat-label">Ratio épargne/crédit</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-layer-group"></i> Classification des crédits</h3></div>
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Classification</th><th>Nb crédits</th><th>Encours</th>
          <th>Taux provision</th><th>Provision</th>
        </tr></thead><tbody>
    """
    for c_data in classif_data:
        badge = 'badge-success' if c_data['classification'] == 'Sain' else \
                'badge-warning' if c_data['classification'] == 'Sous surveillance' else 'badge-danger'
        content += f"""
        <tr>
          <td><span class="badge {badge}">{c_data['classification']}</span></td>
          <td>{c_data['nb']}</td>
          <td><strong>{_fmt_fcfa(c_data['montant'])}</strong></td>
          <td>{c_data['taux']}%</td>
          <td><strong style="color:#dc2626">{_fmt_fcfa(c_data['provision'])}</strong></td>
        </tr>"""
    content += "</tbody></table></div></div>"

    content += f"""
    <div class="card" style="border-left:5px solid #0e7490">
      <div class="card-header"><h3><i class="fas fa-book"></i> Rappel réglementaire BCEAO</h3></div>
      <div style="color:#475569;font-size:0.9rem;line-height:1.8">
        <p><strong>Directive BCEAO n°02/2015</strong> — Classification des créances :</p>
        <ul style="margin-left:25px;margin-top:10px">
          <li><strong>Sain</strong> : paiement régulier, provision 0%</li>
          <li><strong>Sous surveillance</strong> : impayés 30-90 jours, provision 5%</li>
          <li><strong>Douteux</strong> : impayés 90-180 jours, provision 50%</li>
          <li><strong>Compromis</strong> : impayés > 180 jours, provision 100%</li>
        </ul>
        <p style="margin-top:15px">
          Le ratio minimal épargne/crédit recommandé est de <strong>30%</strong>.
          Votre ratio actuel : <strong>{ratio:.1f}%</strong>
        </p>
      </div>
    </div>"""

    return _render(content, active='rapports', title='Conformité BCEAO')
