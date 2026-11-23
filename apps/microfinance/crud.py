"""
🏦 MicroFinance 2.0 — CRUD complet
Clients · Crédits · Épargne · Demandes · Remboursements · Recouvrement
"""
from flask import Blueprint, request, redirect, flash, jsonify
from flask_login import current_user
import sqlite3
from datetime import datetime, timedelta

crud_bp = Blueprint('crud', __name__)
_deps = {}


def init_crud(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(crud_bp)
    print("[CRUD] ✅ Module CRUD complet enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='dashboard', title='MicroFinance'):
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


def _can_write():
    return current_user and current_user.role in ('admin', 'directeur', 'agent')


def _can_validate():
    return current_user and current_user.role in ('admin', 'directeur')


def _fmt_fcfa(m):
    if not m:
        return "0 F"
    return f"{int(m):,} F".replace(",", " ")


def _fmt_pct(v):
    if v is None:
        return "0%"
    return f"{v:.1f}%"


def _fmt_date(d):
    if not d:
        return "-"
    return d[:10] if len(d) >= 10 else d


# ================================================================
# ==================== CLIENTS ====================
# ================================================================
@crud_bp.route('/clients')
@_auth_required
def clients_list():
    q = (request.args.get('q') or '').strip()
    statut = request.args.get('statut') or ''
    kyc = request.args.get('kyc') or ''
    agence_id = request.args.get('agence') or ''

    conn = _db()
    c = conn.cursor()
    sql = """SELECT cl.*, r.nom AS region_nom, a.nom AS agence_nom,
                    (SELECT COUNT(*) FROM credits WHERE client_id=cl.id AND statut='Actif') AS nb_credits,
                    (SELECT COALESCE(SUM(solde_restant), 0) FROM credits WHERE client_id=cl.id AND statut='Actif') AS encours
             FROM clients cl
             LEFT JOIN regions r ON cl.region_id = r.id
             LEFT JOIN agences a ON cl.agence_id = a.id
             WHERE cl.actif=1"""
    params = []
    if q:
        sql += " AND (cl.nom LIKE ? OR cl.prenom LIKE ? OR cl.code LIKE ? OR cl.telephone LIKE ?)"
        params += [f"%{q}%"] * 4
    if statut:
        sql += " AND cl.statut=?"
        params.append(statut)
    if kyc:
        sql += " AND cl.kyc_statut=?"
        params.append(kyc)
    if agence_id:
        sql += " AND cl.agence_id=?"
        params.append(agence_id)
    sql += " ORDER BY cl.nom, cl.prenom LIMIT 200"
    c.execute(sql, params)
    clients = c.fetchall()

    # Stats
    c.execute("SELECT COUNT(*) FROM clients WHERE actif=1")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM clients WHERE actif=1 AND kyc_statut='Validé'")
    kyc_ok = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM clients WHERE actif=1 AND statut='Actif'")
    actifs = c.fetchone()[0]

    c.execute("SELECT * FROM agences WHERE actif=1 ORDER BY nom")
    agences = c.fetchall()
    conn.close()

    opt_ag = '<option value="">Toutes agences</option>'
    for a in agences:
        sel = 'selected' if str(a['id']) == agence_id else ''
        opt_ag += f'<option value="{a["id"]}" {sel}>{a["nom"]}</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-users"></i> Clients</h2>
        <div class="page-subtitle">{len(clients)} client(s) affiché(s) sur {total}</div></div>
      {'<a href="/clients/nouveau" class="btn btn-primary"><i class="fas fa-user-plus"></i> Nouveau client</a>' if _can_write() else ''}
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-users"></i></div>
        <div class="stat-value">{total}</div>
        <div class="stat-label">Clients enregistrés</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-check-circle"></i></div>
        <div class="stat-value">{actifs}</div>
        <div class="stat-label">Clients actifs</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-id-card"></i></div>
        <div class="stat-value">{kyc_ok}</div>
        <div class="stat-label">KYC validés</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-clock"></i></div>
        <div class="stat-value">{total - kyc_ok}</div>
        <div class="stat-label">KYC en attente</div></div>
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:2;margin:0;min-width:200px">
          <label>Recherche</label>
          <input type="text" name="q" value="{q}" placeholder="Nom, code, téléphone...">
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>KYC</label>
          <select name="kyc">
            <option value="">Tous</option>
            <option value="Validé" {"selected" if kyc=="Validé" else ""}>Validé</option>
            <option value="En attente" {"selected" if kyc=="En attente" else ""}>En attente</option>
            <option value="Rejeté" {"selected" if kyc=="Rejeté" else ""}>Rejeté</option>
          </select>
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:180px">
          <label>Agence</label>
          <select name="agence">{opt_ag}</select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-search"></i> Filtrer</button>
        <a href="/clients" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Code</th><th>Client</th><th>Agence</th><th>Région</th>
          <th>Crédits</th><th>Encours</th><th>KYC</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for cl in clients:
        initiales = f"{cl['prenom'][0] if cl['prenom'] else ''}{cl['nom'][0] if cl['nom'] else ''}"
        kyc_badge = 'badge-success' if cl['kyc_statut'] == 'Validé' else ('badge-warning' if cl['kyc_statut'] == 'En attente' else 'badge-danger')

        content += f"""
        <tr>
          <td><strong>{cl['code']}</strong></td>
          <td>
            <div style="display:flex;align-items:center;gap:10px">
              <div style="width:36px;height:36px;background:linear-gradient(135deg,#0e7490,#06b6d4);border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-weight:800;font-size:0.85rem;flex-shrink:0">{initiales}</div>
              <div>
                <div style="font-weight:700">{cl['prenom'] or ''} {cl['nom']}</div>
                <div style="font-size:0.72rem;color:#94a3b8">{cl['telephone'] or '-'}</div>
              </div>
            </div>
          </td>
          <td>{cl['agence_nom'] or '-'}</td>
          <td><small>{cl['region_nom'] or '-'}</small></td>
          <td><span class="badge badge-primary">{cl['nb_credits']}</span></td>
          <td><small>{_fmt_fcfa(cl['encours'])}</small></td>
          <td><span class="badge {kyc_badge}">{cl['kyc_statut'] or '-'}</span></td>
          <td style="white-space:nowrap">
            <a href="/clients/{cl['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
            {'<a href="/clients/'+str(cl['id'])+'/modifier" class="btn btn-warning btn-sm"><i class="fas fa-pen"></i></a>' if _can_write() else ''}
          </td>
        </tr>"""
    if not clients:
        content += '<tr><td colspan="8" class="empty"><i class="fas fa-users"></i><br>Aucun client</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='clients', title='Clients')


@crud_bp.route('/clients/<int:cid>')
@_auth_required
def clients_detail(cid):
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT cl.*, r.nom AS region_nom, a.nom AS agence_nom
                 FROM clients cl
                 LEFT JOIN regions r ON cl.region_id = r.id
                 LEFT JOIN agences a ON cl.agence_id = a.id
                 WHERE cl.id=?""", (cid,))
    cl = c.fetchone()
    if not cl:
        conn.close()
        flash("Client introuvable", "danger")
        return redirect('/clients')

    # Crédits
    c.execute("""SELECT cr.*, p.nom AS produit_nom
                 FROM credits cr
                 LEFT JOIN produits p ON cr.produit_id = p.id
                 WHERE cr.client_id=?
                 ORDER BY cr.date_decaissement DESC""", (cid,))
    credits = c.fetchall()

    # Comptes épargne
    c.execute("""SELECT * FROM comptes_epargne WHERE client_id=? ORDER BY date_ouverture DESC""", (cid,))
    comptes = c.fetchall()

    # Scores IA
    c.execute("""SELECT * FROM scores_credit WHERE client_id=?
                 ORDER BY date_evaluation DESC LIMIT 5""", (cid,))
    scores = c.fetchall()

    # Documents KYC
    c.execute("""SELECT * FROM documents_kyc WHERE client_id=?
                 ORDER BY created_at DESC""", (cid,))
    documents = c.fetchall()

    # Stats
    c.execute("""SELECT COUNT(*) AS nb, COALESCE(SUM(solde_restant), 0) AS encours
                 FROM credits WHERE client_id=? AND statut='Actif'""", (cid,))
    stats_cr = c.fetchone()

    c.execute("""SELECT COALESCE(SUM(solde), 0) FROM comptes_epargne
                 WHERE client_id=? AND statut='Actif'""", (cid,))
    total_epargne = c.fetchone()[0] or 0

    conn.close()

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-user"></i> {cl['prenom'] or ''} {cl['nom']}</h2>
        <div class="page-subtitle">
          <strong>{cl['code']}</strong> · {cl['profession'] or 'Sans profession'} ·
          {cl['agence_nom'] or '-'} · KYC : {cl['kyc_statut']}
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/clients" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        {'<a href="/clients/'+str(cid)+'/modifier" class="btn btn-warning"><i class="fas fa-pen"></i> Modifier</a>' if _can_write() else ''}
      </div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-hand-holding-dollar"></i></div>
        <div class="stat-value">{stats_cr['nb']}</div>
        <div class="stat-label">Crédits actifs</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-money-bill"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(stats_cr['encours'])}</div>
        <div class="stat-label">Encours</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-piggy-bank"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(total_epargne)}</div>
        <div class="stat-label">Épargne</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-star"></i></div>
        <div class="stat-value">{cl['score_interne'] or 0}</div>
        <div class="stat-label">Score interne</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Code</label>
             <div style="font-weight:700">{cl['code']}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Type</label>
             <div>{cl['type_client'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Sexe</label>
             <div>{cl['sexe'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Naissance</label>
             <div>{_fmt_date(cl['date_naissance'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Téléphone</label>
             <div>{cl['telephone'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Email</label>
             <div>{cl['email'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">CNI</label>
             <div>{cl['numero_cni'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Profession</label>
             <div>{cl['profession'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Revenu mensuel</label>
             <div>{_fmt_fcfa(cl['revenu_mensuel'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Activité</label>
             <div>{cl['activite_principale'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Adhésion</label>
             <div>{_fmt_date(cl['date_adhesion'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Statut</label>
             <div><span class="badge badge-success">{cl['statut']}</span></div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3><i class="fas fa-hand-holding-dollar"></i> Crédits ({len(credits)})</h3>
        {'<a href="/credits/nouveau?client='+str(cid)+'" class="btn btn-primary btn-sm"><i class="fas fa-plus"></i> Nouveau crédit</a>' if _can_write() else ''}
      </div>
      <div class="table-wrap"><table>
        <thead><tr><th>Référence</th><th>Produit</th><th>Montant</th>
                   <th>Solde restant</th><th>Échéances</th><th>Statut</th><th></th></tr></thead>
        <tbody>"""
    for cr in credits:
        badge = 'badge-success' if cr['statut'] == 'Actif' else ('badge-info' if cr['statut'] == 'Remboursé' else 'badge-danger')
        content += f"""
        <tr>
          <td><small>{cr['reference']}</small></td>
          <td>{cr['produit_nom'] or '-'}</td>
          <td><strong>{_fmt_fcfa(cr['montant_principal'])}</strong></td>
          <td>{_fmt_fcfa(cr['solde_restant'])}</td>
          <td><span class="badge badge-primary">{cr['nb_echeances_payees']}/{cr['nb_echeances']}</span></td>
          <td><span class="badge {badge}">{cr['statut']}</span></td>
          <td><a href="/credits/{cr['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a></td>
        </tr>"""
    if not credits:
        content += '<tr><td colspan="7" class="empty">Aucun crédit</td></tr>'
    content += "</tbody></table></div></div>"

    # Comptes épargne
    if comptes:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-piggy-bank"></i> Comptes épargne</h3></div>
          <div class="table-wrap"><table>
            <thead><tr><th>N° Compte</th><th>Solde</th><th>Ouverture</th><th>Statut</th></tr></thead>
            <tbody>"""
        for cp in comptes:
            content += f"""
            <tr>
              <td><strong>{cp['numero_compte']}</strong></td>
              <td><strong>{_fmt_fcfa(cp['solde'])}</strong></td>
              <td>{_fmt_date(cp['date_ouverture'])}</td>
              <td><span class="badge badge-success">{cp['statut']}</span></td>
            </tr>"""
        content += "</tbody></table></div></div>"

    # Scores IA
    if scores:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-robot"></i> Historique des scores IA</h3></div>
          <div class="table-wrap"><table>
            <thead><tr><th>Date</th><th>Score</th><th>Niveau</th>
                       <th>Prob. défaut</th><th>Recommandation</th></tr></thead>
            <tbody>"""
        for s in scores:
            badge = 'badge-success' if s['score'] >= 650 else ('badge-warning' if s['score'] >= 500 else 'badge-danger')
            content += f"""
            <tr>
              <td>{_fmt_date(s['date_evaluation'])}</td>
              <td><span class="badge {badge}">{s['score']}</span></td>
              <td>{s['niveau'] or '-'}</td>
              <td>{_fmt_pct((s['probabilite_defaut'] or 0) * 100)}</td>
              <td><small>{s['recommandation'] or '-'}</small></td>
            </tr>"""
        content += "</tbody></table></div></div>"

    return _render(content, active='clients', title=cl['prenom'] + ' ' + cl['nom'])


@crud_bp.route('/clients/nouveau', methods=['GET', 'POST'])
@_auth_required
def clients_new():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/clients')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        nom = (request.form.get('nom') or '').strip()
        prenom = (request.form.get('prenom') or '').strip()
        telephone = (request.form.get('telephone') or '').strip()

        if not nom or not telephone:
            flash("Nom et téléphone obligatoires", "warning")
        else:
            try:
                c.execute("SELECT COUNT(*) FROM clients")
                n = (c.fetchone()[0] or 0) + 1
                code = f"CLI-{n:05d}"

                c.execute("""INSERT INTO clients
                    (code, type_client, nom, prenom, date_naissance, sexe, situation_familiale,
                     telephone, email, adresse, ville, region_id, numero_cni,
                     profession, revenu_mensuel, activite_principale,
                     agence_id, statut, date_adhesion, kyc_statut, actif)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                    (code, request.form.get('type_client') or 'Particulier',
                     nom, prenom,
                     request.form.get('date_naissance') or None,
                     request.form.get('sexe') or None,
                     request.form.get('situation_familiale') or None,
                     telephone,
                     (request.form.get('email') or '').strip(),
                     (request.form.get('adresse') or '').strip(),
                     (request.form.get('ville') or '').strip(),
                     request.form.get('region_id') or None,
                     (request.form.get('numero_cni') or '').strip(),
                     (request.form.get('profession') or '').strip(),
                     int(request.form.get('revenu_mensuel') or 0),
                     (request.form.get('activite_principale') or '').strip(),
                     request.form.get('agence_id') or None,
                     'Actif',
                     datetime.now().date().isoformat(),
                     'En attente'))
                new_id = c.lastrowid
                conn.commit()
                _log('CREATE_CLIENT', f"Client {prenom} {nom} ({code})",
                     entity='client', entity_id=new_id)
                flash(f"Client {prenom} {nom} créé", "success")
                conn.close()
                return redirect(f'/clients/{new_id}')
            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    c.execute("SELECT id, nom FROM regions ORDER BY nom")
    regions = c.fetchall()
    c.execute("SELECT id, nom FROM agences WHERE actif=1 ORDER BY nom")
    agences = c.fetchall()
    conn.close()

    opt_r = ''.join(f'<option value="{r["id"]}">{r["nom"]}</option>' for r in regions)
    opt_a = ''.join(f'<option value="{a["id"]}">{a["nom"]}</option>' for a in agences)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-user-plus"></i> Nouveau client</h2></div>
      <a href="/clients" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="form-group"><label>Type</label>
            <select name="type_client" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option>Particulier</option><option>Entreprise</option><option>Groupe</option>
            </select>
          </div>
          <div class="form-group"><label>Sexe</label>
            <select name="sexe" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="M">Masculin</option><option value="F">Féminin</option>
            </select>
          </div>
          <div class="form-group"><label>Nom *</label>
            <input type="text" name="nom" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Prénom</label>
            <input type="text" name="prenom" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Date de naissance</label>
            <input type="date" name="date_naissance" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Situation familiale</label>
            <select name="situation_familiale" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option>Célibataire</option><option>Marié(e)</option><option>Divorcé(e)</option><option>Veuf(ve)</option>
            </select>
          </div>
          <div class="form-group"><label>Téléphone *</label>
            <input type="text" name="telephone" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Email</label>
            <input type="email" name="email" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Adresse</label>
            <input type="text" name="adresse" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Ville</label>
            <input type="text" name="ville" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Région</label>
            <select name="region_id" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">—</option>{opt_r}
            </select>
          </div>
          <div class="form-group"><label>N° CNI</label>
            <input type="text" name="numero_cni" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Profession</label>
            <input type="text" name="profession" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Revenu mensuel (FCFA)</label>
            <input type="number" name="revenu_mensuel" value="0" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Activité principale</label>
            <input type="text" name="activite_principale" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Agence</label>
            <select name="agence_id" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">—</option>{opt_a}
            </select>
          </div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Créer le client</button>
          <a href="/clients" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='clients', title='Nouveau client')


@crud_bp.route('/clients/<int:cid>/modifier', methods=['GET', 'POST'])
@_auth_required
def clients_edit(cid):
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/clients')

    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM clients WHERE id=?", (cid,))
    cl = c.fetchone()
    if not cl:
        conn.close()
        return redirect('/clients')

    if request.method == 'POST':
        c.execute("""UPDATE clients SET
            nom=?, prenom=?, telephone=?, email=?, adresse=?, ville=?,
            region_id=?, numero_cni=?, profession=?, revenu_mensuel=?,
            activite_principale=?, agence_id=?, kyc_statut=?, updated_at=?
            WHERE id=?""",
            ((request.form.get('nom') or '').strip(),
             (request.form.get('prenom') or '').strip(),
             (request.form.get('telephone') or '').strip(),
             (request.form.get('email') or '').strip(),
             (request.form.get('adresse') or '').strip(),
             (request.form.get('ville') or '').strip(),
             request.form.get('region_id') or None,
             (request.form.get('numero_cni') or '').strip(),
             (request.form.get('profession') or '').strip(),
             int(request.form.get('revenu_mensuel') or 0),
             (request.form.get('activite_principale') or '').strip(),
             request.form.get('agence_id') or None,
             request.form.get('kyc_statut') or 'En attente',
             datetime.now().isoformat(), cid))
        conn.commit()
        _log('UPDATE_CLIENT', f"Client id={cid} modifié", entity='client', entity_id=cid)
        conn.close()
        flash("Client mis à jour", "success")
        return redirect(f'/clients/{cid}')

    c.execute("SELECT id, nom FROM regions ORDER BY nom")
    regions = c.fetchall()
    c.execute("SELECT id, nom FROM agences WHERE actif=1 ORDER BY nom")
    agences = c.fetchall()
    conn.close()

    def opt(items, cur):
        return ''.join(f'<option value="{i["id"]}" {"selected" if cur==i["id"] else ""}>{i["nom"]}</option>' for i in items)

    opt_kyc = ''
    for k in ['En attente', 'Validé', 'Rejeté']:
        sel = 'selected' if cl['kyc_statut'] == k else ''
        opt_kyc += f'<option value="{k}" {sel}>{k}</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-pen"></i> Modifier client</h2></div>
      <a href="/clients/{cid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="form-group"><label>Nom</label>
            <input type="text" name="nom" value="{cl['nom']}" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Prénom</label>
            <input type="text" name="prenom" value="{cl['prenom'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Téléphone</label>
            <input type="text" name="telephone" value="{cl['telephone'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Email</label>
            <input type="email" name="email" value="{cl['email'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Adresse</label>
            <input type="text" name="adresse" value="{cl['adresse'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Ville</label>
            <input type="text" name="ville" value="{cl['ville'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Région</label>
            <select name="region_id" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">—</option>{opt(regions, cl['region_id'])}
            </select>
          </div>
          <div class="form-group"><label>N° CNI</label>
            <input type="text" name="numero_cni" value="{cl['numero_cni'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Profession</label>
            <input type="text" name="profession" value="{cl['profession'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Revenu mensuel</label>
            <input type="number" name="revenu_mensuel" value="{cl['revenu_mensuel'] or 0}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Activité</label>
            <input type="text" name="activite_principale" value="{cl['activite_principale'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Agence</label>
            <select name="agence_id" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">—</option>{opt(agences, cl['agence_id'])}
            </select>
          </div>
          <div class="form-group"><label>Statut KYC</label>
            <select name="kyc_statut" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              {opt_kyc}
            </select>
          </div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
          <a href="/clients/{cid}" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='clients', title='Modifier client')


# ================================================================
# ==================== CRÉDITS ====================
# ================================================================
@crud_bp.route('/credits')
@_auth_required
def credits_list():
    statut = request.args.get('statut') or ''
    q = (request.args.get('q') or '').strip()

    conn = _db()
    c = conn.cursor()
    sql = """SELECT cr.*, cl.nom AS client_nom, cl.prenom AS client_prenom,
                    cl.code AS client_code, cl.telephone AS client_tel,
                    p.nom AS produit_nom, p.code AS produit_code,
                    a.nom AS agence_nom
             FROM credits cr
             LEFT JOIN clients cl ON cr.client_id = cl.id
             LEFT JOIN produits p ON cr.produit_id = p.id
             LEFT JOIN agences a ON cr.agence_id = a.id
             WHERE 1=1"""
    params = []
    if statut:
        sql += " AND cr.statut=?"
        params.append(statut)
    if q:
        sql += " AND (cl.nom LIKE ? OR cl.prenom LIKE ? OR cr.reference LIKE ?)"
        params += [f"%{q}%"] * 3
    sql += " ORDER BY cr.date_decaissement DESC LIMIT 200"
    c.execute(sql, params)
    credits = c.fetchall()

    # Stats
    c.execute("SELECT COUNT(*), COALESCE(SUM(montant_principal), 0) FROM credits WHERE statut='Actif'")
    row = c.fetchone()
    nb_actifs = row[0] or 0
    encours_total = row[1] or 0

    c.execute("SELECT COUNT(*), COALESCE(SUM(solde_restant), 0) FROM credits WHERE statut='En retard'")
    row = c.fetchone()
    nb_retard = row[0] or 0
    montant_retard = row[1] or 0

    c.execute("SELECT COUNT(*) FROM credits WHERE statut='Remboursé'")
    nb_rembourses = c.fetchone()[0] or 0

    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-hand-holding-dollar"></i> Crédits</h2>
        <div class="page-subtitle">{len(credits)} crédit(s)</div></div>
      {'<a href="/credits/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau crédit</a>' if _can_write() else ''}
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-hand-holding-dollar"></i></div>
        <div class="stat-value">{nb_actifs}</div>
        <div class="stat-label">Crédits actifs</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-coins"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(encours_total)}</div>
        <div class="stat-label">Encours total</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-triangle-exclamation"></i></div>
        <div class="stat-value">{nb_retard}</div>
        <div class="stat-label">En retard</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-check"></i></div>
        <div class="stat-value">{nb_rembourses}</div>
        <div class="stat-label">Remboursés</div></div>
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:2;margin:0;min-width:200px">
          <label>Recherche</label>
          <input type="text" name="q" value="{q}" placeholder="Référence, client..." style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Statut</label>
          <select name="statut" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
            <option value="">Tous</option>
            <option value="Actif" {"selected" if statut=="Actif" else ""}>Actif</option>
            <option value="En retard" {"selected" if statut=="En retard" else ""}>En retard</option>
            <option value="Remboursé" {"selected" if statut=="Remboursé" else ""}>Remboursé</option>
          </select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-search"></i> Filtrer</button>
        <a href="/credits" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Référence</th><th>Client</th><th>Produit</th>
          <th>Montant</th><th>Solde restant</th><th>Échéances</th>
          <th>Statut</th><th>Classification</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for cr in credits:
        badge = 'badge-success' if cr['statut'] == 'Actif' else ('badge-info' if cr['statut'] == 'Remboursé' else 'badge-danger')
        classif_badge = 'badge-success' if cr['classification'] == 'Sain' else ('badge-warning' if cr['classification'] == 'Sous surveillance' else 'badge-danger')

        content += f"""
        <tr>
          <td><small>{cr['reference']}</small></td>
          <td>
            <div style="font-weight:700">{cr['client_prenom'] or ''} {cr['client_nom'] or ''}</div>
            <div style="font-size:0.72rem;color:#94a3b8">{cr['client_code']}</div>
          </td>
          <td>{cr['produit_nom'] or '-'}</td>
          <td><strong>{_fmt_fcfa(cr['montant_principal'])}</strong></td>
          <td>{_fmt_fcfa(cr['solde_restant'])}</td>
          <td><span class="badge badge-primary">{cr['nb_echeances_payees']}/{cr['nb_echeances']}</span></td>
          <td><span class="badge {badge}">{cr['statut']}</span></td>
          <td><span class="badge {classif_badge}">{cr['classification']}</span></td>
          <td><a href="/credits/{cr['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a></td>
        </tr>"""
    if not credits:
        content += '<tr><td colspan="9" class="empty"><i class="fas fa-hand-holding-dollar"></i><br>Aucun crédit</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='credits', title='Crédits')


@crud_bp.route('/credits/<int:cid>')
@_auth_required
def credits_detail(cid):
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT cr.*, cl.nom AS client_nom, cl.prenom AS client_prenom,
                        cl.code AS client_code, cl.telephone AS client_tel,
                        p.nom AS produit_nom, p.code AS produit_code,
                        a.nom AS agence_nom
                 FROM credits cr
                 LEFT JOIN clients cl ON cr.client_id = cl.id
                 LEFT JOIN produits p ON cr.produit_id = p.id
                 LEFT JOIN agences a ON cr.agence_id = a.id
                 WHERE cr.id=?""", (cid,))
    cr = c.fetchone()
    if not cr:
        conn.close()
        flash("Crédit introuvable", "danger")
        return redirect('/credits')

    # Échéances
    c.execute("""SELECT * FROM echeances_credit WHERE credit_id=?
                 ORDER BY numero_echeance""", (cid,))
    echeances = c.fetchall()

    # Remboursements
    c.execute("""SELECT * FROM remboursements WHERE credit_id=?
                 ORDER BY date_paiement DESC""", (cid,))
    remboursements = c.fetchall()

    # Garanties
    c.execute("SELECT * FROM garanties WHERE credit_id=?", (cid,))
    garanties = c.fetchall()

    conn.close()

    badge = 'badge-success' if cr['statut'] == 'Actif' else ('badge-info' if cr['statut'] == 'Remboursé' else 'badge-danger')

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-hand-holding-dollar"></i> {cr['reference']}</h2>
        <div class="page-subtitle">
          {cr['client_prenom'] or ''} {cr['client_nom'] or ''} ({cr['client_code']}) ·
          <span class="badge {badge}">{cr['statut']}</span>
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/credits" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        {'<a href="/remboursements/nouveau?credit='+str(cid)+'" class="btn btn-success"><i class="fas fa-money-bill"></i> Enregistrer remboursement</a>' if _can_write() else ''}
      </div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-coins"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(cr['montant_principal'])}</div>
        <div class="stat-label">Montant principal</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-money-bill"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(cr['montant_rembourse'])}</div>
        <div class="stat-label">Remboursé</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-clock"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(cr['solde_restant'])}</div>
        <div class="stat-label">Solde restant</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-calendar"></i></div>
        <div class="stat-value">{cr['nb_echeances_payees']}/{cr['nb_echeances']}</div>
        <div class="stat-label">Échéances payées</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Détails du crédit</h3></div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Produit</label>
             <div style="font-weight:700">{cr['produit_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Taux intérêt</label>
             <div>{_fmt_pct(cr['taux_interet'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Durée</label>
             <div>{cr['duree_mois']} mois</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Date décaissement</label>
             <div>{_fmt_date(cr['date_decaissement'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Date fin prévue</label>
             <div>{_fmt_date(cr['date_fin_prevue'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Agence</label>
             <div>{cr['agence_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Intérêts totaux</label>
             <div>{_fmt_fcfa(cr['montant_interets'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Frais dossier</label>
             <div>{_fmt_fcfa(cr['montant_frais'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Assurance</label>
             <div>{_fmt_fcfa(cr['montant_assurance'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Total dû</label>
             <div style="font-weight:900;color:#0e7490">{_fmt_fcfa(cr['montant_total_du'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Classification</label>
             <div><span class="badge badge-success">{cr['classification']}</span></div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Jours retard</label>
             <div>{cr['jours_retard'] or 0} jours</div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-calendar-alt"></i> Échéancier ({len(echeances)} échéances)</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>N°</th><th>Date</th><th>Capital</th><th>Intérêts</th>
                   <th>Total</th><th>Payé</th><th>Statut</th><th>Retard</th></tr></thead>
        <tbody>"""
    for ec in echeances:
        badge_ec = 'badge-success' if ec['statut'] == 'Payé' else ('badge-warning' if ec['statut'] == 'À venir' else 'badge-danger')
        content += f"""
        <tr>
          <td><strong>#{ec['numero_echeance']}</strong></td>
          <td>{_fmt_date(ec['date_echeance'])}</td>
          <td>{_fmt_fcfa(ec['montant_capital'])}</td>
          <td>{_fmt_fcfa(ec['montant_interets'])}</td>
          <td><strong>{_fmt_fcfa(ec['montant_total'])}</strong></td>
          <td>{_fmt_fcfa(ec['montant_paye'])}</td>
          <td><span class="badge {badge_ec}">{ec['statut']}</span></td>
          <td>{ec['jours_retard'] or 0}j</td>
        </tr>"""
    content += "</tbody></table></div></div>"

    if remboursements:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-history"></i> Remboursements</h3></div>
          <div class="table-wrap"><table>
            <thead><tr><th>Référence</th><th>Date</th><th>Montant</th>
                       <th>Capital</th><th>Intérêts</th><th>Mode</th></tr></thead>
            <tbody>"""
        for r in remboursements:
            content += f"""
            <tr>
              <td><small>{r['reference']}</small></td>
              <td>{_fmt_date(r['date_paiement'])}</td>
              <td><strong>{_fmt_fcfa(r['montant_recu'])}</strong></td>
              <td>{_fmt_fcfa(r['montant_capital'])}</td>
              <td>{_fmt_fcfa(r['montant_interets'])}</td>
              <td><span class="badge badge-info">{r['mode_paiement']}</span></td>
            </tr>"""
        content += "</tbody></table></div></div>"

    return _render(content, active='credits', title=cr['reference'])


@crud_bp.route('/credits/nouveau', methods=['GET', 'POST'])
@_auth_required
def credits_new():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/credits')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        client_id = request.form.get('client_id')
        produit_id = request.form.get('produit_id')
        montant = int(request.form.get('montant_principal') or 0)
        duree = int(request.form.get('duree_mois') or 0)
        taux = float(request.form.get('taux_interet') or 0)

        if not client_id or not produit_id or montant <= 0 or duree <= 0:
            flash("Champs obligatoires manquants", "warning")
        else:
            try:
                # Calculs
                interets = int(montant * taux / 100 * duree / 12)
                frais = int(montant * 0.02) + 5000
                assurance = int(montant * 0.01)
                total_du = montant + interets + frais + assurance

                c.execute("SELECT COUNT(*) FROM credits")
                n = (c.fetchone()[0] or 0) + 1
                ref = f"CRD-{datetime.now().strftime('%Y%m%d')}-{n:04d}"

                date_dec = datetime.now()
                date_prem = date_dec + timedelta(days=30)
                date_fin = date_prem + timedelta(days=30*duree)

                c.execute("""INSERT INTO credits
                    (reference, client_id, produit_id, agence_id,
                     montant_principal, taux_interet, duree_mois,
                     date_decaissement, date_premiere_echeance, date_fin_prevue,
                     montant_interets, montant_frais, montant_assurance, montant_total_du,
                     capital_restant, solde_restant,
                     nb_echeances, statut, classification)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (ref, client_id, produit_id, request.form.get('agence_id') or None,
                     montant, taux, duree,
                     date_dec.date().isoformat(), date_prem.date().isoformat(), date_fin.date().isoformat(),
                     interets, frais, assurance, total_du,
                     montant, total_du,
                     duree, 'Actif', 'Sain'))
                credit_id = c.lastrowid

                # Créer échéances
                montant_echeance = int(total_du / duree)
                for j in range(duree):
                    date_ech = date_prem + timedelta(days=30*j)
                    c.execute("""INSERT INTO echeances_credit
                        (credit_id, numero_echeance, date_echeance,
                         montant_capital, montant_interets, montant_total,
                         montant_restant, statut)
                        VALUES (?,?,?,?,?,?,?,?)""",
                        (credit_id, j+1, date_ech.date().isoformat(),
                         int(montant_echeance * 0.7), int(montant_echeance * 0.3), montant_echeance,
                         montant_echeance, 'À venir'))

                conn.commit()
                _log('CREATE_CREDIT', f"Crédit {ref} de {_fmt_fcfa(montant)}",
                     entity='credit', entity_id=credit_id)
                flash(f"Crédit {ref} créé ({_fmt_fcfa(montant)})", "success")
                conn.close()
                return redirect(f'/credits/{credit_id}')

            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    # GET
    client_id_pre = request.args.get('client') or ''
    c.execute("SELECT id, code, nom, prenom FROM clients WHERE actif=1 ORDER BY nom LIMIT 200")
    clients = c.fetchall()
    c.execute("SELECT * FROM produits WHERE actif=1 ORDER BY nom")
    produits = c.fetchall()
    c.execute("SELECT id, nom FROM agences WHERE actif=1 ORDER BY nom")
    agences = c.fetchall()
    conn.close()

    opt_cl = ''
    for cl in clients:
        sel = 'selected' if str(cl['id']) == str(client_id_pre) else ''
        opt_cl += f'<option value="{cl["id"]}" {sel}>{cl["code"]} — {cl["prenom"] or ""} {cl["nom"]}</option>'

    opt_pr = ''.join(f'<option value="{p["id"]}">{p["nom"]} ({_fmt_fcfa(p["montant_min"])} - {_fmt_fcfa(p["montant_max"])})</option>' for p in produits)
    opt_ag = ''.join(f'<option value="{a["id"]}">{a["nom"]}</option>' for a in agences)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus"></i> Nouveau crédit</h2></div>
      <a href="/credits" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="form-group" style="grid-column:1/-1"><label>Client *</label>
            <select name="client_id" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">— Choisir —</option>{opt_cl}
            </select>
          </div>
          <div class="form-group" style="grid-column:1/-1"><label>Produit *</label>
            <select name="produit_id" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">— Choisir —</option>{opt_pr}
            </select>
          </div>
          <div class="form-group"><label>Montant (FCFA) *</label>
            <input type="number" name="montant_principal" required value="100000" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Durée (mois) *</label>
            <input type="number" name="duree_mois" required value="12" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Taux intérêt (%)</label>
            <input type="number" step="0.1" name="taux_interet" value="12" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Agence</label>
            <select name="agence_id" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">—</option>{opt_ag}
            </select>
          </div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Créer le crédit</button>
          <a href="/credits" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='credits', title='Nouveau crédit')


# ================================================================
# ==================== DEMANDES DE CRÉDIT ====================
# ================================================================
@crud_bp.route('/demandes')
@_auth_required
def demandes_list():
    statut = request.args.get('statut') or ''

    conn = _db()
    c = conn.cursor()
    sql = """SELECT d.*, cl.nom AS client_nom, cl.prenom AS client_prenom,
                    cl.code AS client_code, cl.telephone AS client_tel,
                    p.nom AS produit_nom, a.nom AS agence_nom
             FROM demandes_credit d
             LEFT JOIN clients cl ON d.client_id = cl.id
             LEFT JOIN produits p ON d.produit_id = p.id
             LEFT JOIN agences a ON d.agence_id = a.id
             WHERE 1=1"""
    params = []
    if statut:
        sql += " AND d.statut=?"
        params.append(statut)
    sql += " ORDER BY d.date_demande DESC LIMIT 200"
    c.execute(sql, params)
    demandes = c.fetchall()

    # Stats
    c.execute("SELECT COUNT(*) FROM demandes_credit WHERE statut='En analyse'")
    en_analyse = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM demandes_credit WHERE statut='Approuvé'")
    approuvees = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM demandes_credit WHERE statut='Rejeté'")
    rejetees = c.fetchone()[0] or 0
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-file-signature"></i> Demandes de crédit</h2>
        <div class="page-subtitle">{len(demandes)} demande(s)</div></div>
      {'<a href="/demandes/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle demande</a>' if _can_write() else ''}
    </div>

    <div class="stats">
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-clock"></i></div>
        <div class="stat-value">{en_analyse}</div>
        <div class="stat-label">En analyse</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-check"></i></div>
        <div class="stat-value">{approuvees}</div>
        <div class="stat-label">Approuvées</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-xmark"></i></div>
        <div class="stat-value">{rejetees}</div>
        <div class="stat-label">Rejetées</div></div>
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-list"></i></div>
        <div class="stat-value">{len(demandes)}</div>
        <div class="stat-label">Total affichées</div></div>
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;align-items:end">
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Statut</label>
          <select name="statut" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
            <option value="">Tous</option>
            <option value="En analyse" {"selected" if statut=="En analyse" else ""}>En analyse</option>
            <option value="Approuvé" {"selected" if statut=="Approuvé" else ""}>Approuvé</option>
            <option value="Rejeté" {"selected" if statut=="Rejeté" else ""}>Rejeté</option>
          </select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-filter"></i> Filtrer</button>
        <a href="/demandes" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Référence</th><th>Client</th><th>Produit</th>
          <th>Montant</th><th>Durée</th><th>Score IA</th>
          <th>Risque</th><th>Statut</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for d in demandes:
        badge = 'badge-warning' if d['statut'] == 'En analyse' else ('badge-success' if d['statut'] == 'Approuvé' else 'badge-danger')
        risque_badge = 'badge-success' if d['niveau_risque'] == 'Faible' else ('badge-warning' if d['niveau_risque'] == 'Moyen' else 'badge-danger')

        content += f"""
        <tr>
          <td><small>{d['reference']}</small></td>
          <td>
            <div style="font-weight:700">{d['client_prenom'] or ''} {d['client_nom'] or ''}</div>
            <div style="font-size:0.72rem;color:#94a3b8">{d['client_code']}</div>
          </td>
          <td>{d['produit_nom'] or '-'}</td>
          <td><strong>{_fmt_fcfa(d['montant_demande'])}</strong></td>
          <td>{d['duree_mois']} mois</td>
          <td><span class="badge badge-info">{d['score_ia'] or '-'}</span></td>
          <td><span class="badge {risque_badge}">{d['niveau_risque'] or '-'}</span></td>
          <td><span class="badge {badge}">{d['statut']}</span></td>
          <td style="white-space:nowrap">
            <a href="/demandes/{d['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
          </td>
        </tr>"""
    if not demandes:
        content += '<tr><td colspan="9" class="empty"><i class="fas fa-file-signature"></i><br>Aucune demande</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='demandes', title='Demandes de crédit')


@crud_bp.route('/demandes/<int:did>')
@_auth_required
def demandes_detail(did):
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT d.*, cl.nom AS client_nom, cl.prenom AS client_prenom,
                        cl.code AS client_code, cl.telephone AS client_tel,
                        cl.revenu_mensuel, cl.profession,
                        p.nom AS produit_nom, a.nom AS agence_nom
                 FROM demandes_credit d
                 LEFT JOIN clients cl ON d.client_id = cl.id
                 LEFT JOIN produits p ON d.produit_id = p.id
                 LEFT JOIN agences a ON d.agence_id = a.id
                 WHERE d.id=?""", (did,))
    d = c.fetchone()
    if not d:
        conn.close()
        flash("Demande introuvable", "danger")
        return redirect('/demandes')

    # Scores récents
    c.execute("""SELECT * FROM scores_credit WHERE client_id=?
                 ORDER BY date_evaluation DESC LIMIT 1""", (d['client_id'],))
    score = c.fetchone()

    conn.close()

    badge = 'badge-warning' if d['statut'] == 'En analyse' else ('badge-success' if d['statut'] == 'Approuvé' else 'badge-danger')

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-file-signature"></i> {d['reference']}</h2>
        <div class="page-subtitle">
          {d['client_prenom'] or ''} {d['client_nom'] or ''} ({d['client_code']}) ·
          <span class="badge {badge}">{d['statut']}</span>
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/demandes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
      </div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-coins"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(d['montant_demande'])}</div>
        <div class="stat-label">Montant demandé</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-calendar"></i></div>
        <div class="stat-value">{d['duree_mois']} mois</div>
        <div class="stat-label">Durée</div></div>
      <div class="stat-card purple"><div class="stat-icon"><i class="fas fa-robot"></i></div>
        <div class="stat-value">{d['score_ia'] or '-'}</div>
        <div class="stat-label">Score IA</div></div>
      <div class="stat-card {'rose' if d['niveau_risque']=='Élevé' else 'green'}">
        <div class="stat-icon"><i class="fas fa-shield-halved"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{d['niveau_risque'] or '-'}</div>
        <div class="stat-label">Niveau de risque</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Détails de la demande</h3></div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Client</label>
             <div style="font-weight:700">{d['client_prenom'] or ''} {d['client_nom'] or ''}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Profession</label>
             <div>{d['profession'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Revenu mensuel</label>
             <div>{_fmt_fcfa(d['revenu_mensuel'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Produit</label>
             <div>{d['produit_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Objet</label>
             <div>{d['objet_credit'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Activité</label>
             <div>{d['activite_financee'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Date demande</label>
             <div>{_fmt_date(d['date_demande'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Agence</label>
             <div>{d['agence_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Téléphone</label>
             <div>{d['client_tel'] or '-'}</div></div>
      </div>
    </div>

    {f'''
    <div class="card" style="border-left:5px solid #7c3aed">
      <div class="card-header"><h3><i class="fas fa-robot"></i> Analyse IA</h3></div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Score</label>
             <div style="font-size:1.5rem;font-weight:900;color:#0e7490">{score["score"]}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Niveau</label>
             <div><span class="badge badge-success">{score["niveau"]}</span></div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Prob. défaut</label>
             <div>{_fmt_pct((score["probabilite_defaut"] or 0) * 100)}</div></div>
        <div style="grid-column:1/-1"><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Recommandation</label>
             <div style="font-weight:700">{score["recommandation"] or "-"}</div></div>
      </div>
    </div>''' if score else ''}

    {f'''
    <div class="card">
      <div class="card-header"><h3><i class="fas fa-gavel"></i> Actions</h3></div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <a href="/demandes/{did}/approuver" class="btn btn-success" onclick="return confirm(&#39;Approuver cette demande ?&#39;)">
          <i class="fas fa-check"></i> Approuver
        </a>
        <a href="/demandes/{did}/rejeter" class="btn btn-danger" onclick="return confirm(&#39;Rejeter cette demande ?&#39;)">
          <i class="fas fa-xmark"></i> Rejeter
        </a>
      </div>
    </div>''' if _can_validate() and d['statut'] == 'En analyse' else ''}
    """
    return _render(content, active='demandes', title=d['reference'])


@crud_bp.route('/demandes/<int:did>/approuver', methods=['GET', 'POST'])
@_auth_required
def demandes_approuver(did):
    if not _can_validate():
        flash("Droits insuffisants", "danger")
        return redirect('/demandes')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        montant_approuve = int(request.form.get('montant_approuve') or 0)
        taux_approuve = float(request.form.get('taux_approuve') or 12)
        duree_approuvee = int(request.form.get('duree_approuvee') or 12)

        try:
            c.execute("""UPDATE demandes_credit SET
                statut='Approuvé', montant_approuve=?, taux_approuve=?,
                duree_approuvee=?, valide_par=?, date_validation=?
                WHERE id=?""",
                (montant_approuve, taux_approuve, duree_approuvee,
                 current_user.id, datetime.now().isoformat(), did))
            conn.commit()
            _log('DEMANDE_APPROUVEE', f"Demande id={did} approuvée",
                 entity='demande', entity_id=did)
            flash("Demande approuvée", "success")
            conn.close()
            return redirect('/demandes')
        except Exception as e:
            flash(f"Erreur : {e}", "danger")

    c.execute("SELECT * FROM demandes_credit WHERE id=?", (did,))
    d = c.fetchone()
    if not d:
        conn.close()
        return redirect('/demandes')
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2 style="color:#16a34a"><i class="fas fa-check"></i> Approuver la demande</h2></div>
      <a href="/demandes/{did}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card" style="border-left:5px solid #16a34a">
      <div style="padding:15px;background:#d1fae5;border-radius:12px;margin-bottom:20px">
        <strong>{d['reference']}</strong> — Montant demandé : {_fmt_fcfa(d['montant_demande'])}
      </div>
      <form method="POST">
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px">
          <div class="form-group"><label>Montant approuvé (FCFA)</label>
            <input type="number" name="montant_approuve" value="{d['montant_demande']}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Taux intérêt (%)</label>
            <input type="number" step="0.1" name="taux_approuve" value="12" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Durée (mois)</label>
            <input type="number" name="duree_approuvee" value="{d['duree_mois']}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
        </div>
        <button class="btn btn-success" style="margin-top:20px"><i class="fas fa-check"></i> Confirmer l'approbation</button>
      </form>
    </div>"""
    return _render(content, active='demandes', title='Approuver')


@crud_bp.route('/demandes/<int:did>/rejeter', methods=['GET', 'POST'])
@_auth_required
def demandes_rejeter(did):
    if not _can_validate():
        flash("Droits insuffisants", "danger")
        return redirect('/demandes')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        motif = (request.form.get('motif') or '').strip()
        if not motif:
            flash("Motif obligatoire", "warning")
        else:
            c.execute("""UPDATE demandes_credit SET
                statut='Rejeté', motif_rejet=?, valide_par=?, date_validation=?
                WHERE id=?""",
                (motif, current_user.id, datetime.now().isoformat(), did))
            conn.commit()
            _log('DEMANDE_REJETEE', f"Demande id={did} rejetée: {motif}",
                 entity='demande', entity_id=did)
            flash("Demande rejetée", "info")
            conn.close()
            return redirect('/demandes')

    c.execute("SELECT * FROM demandes_credit WHERE id=?", (did,))
    d = c.fetchone()
    conn.close()
    if not d:
        return redirect('/demandes')

    content = f"""
    <div class="page-header">
      <div><h2 style="color:#dc2626"><i class="fas fa-xmark"></i> Rejeter la demande</h2></div>
      <a href="/demandes/{did}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card" style="border-left:5px solid #dc2626">
      <div style="padding:15px;background:#fee2e2;border-radius:12px;margin-bottom:20px">
        <strong>{d['reference']}</strong> — {_fmt_fcfa(d['montant_demande'])}
      </div>
      <form method="POST">
        <div class="form-group"><label>Motif du rejet *</label>
          <textarea name="motif" rows="4" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></textarea>
        </div>
        <button class="btn btn-danger" style="margin-top:20px"><i class="fas fa-xmark"></i> Confirmer le rejet</button>
      </form>
    </div>"""
    return _render(content, active='demandes', title='Rejeter')


@crud_bp.route('/demandes/nouvelle', methods=['GET', 'POST'])
@_auth_required
def demandes_new():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/demandes')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        client_id = request.form.get('client_id')
        montant = int(request.form.get('montant_demande') or 0)
        duree = int(request.form.get('duree_mois') or 12)

        if not client_id or montant <= 0:
            flash("Client et montant obligatoires", "warning")
        else:
            try:
                c.execute("SELECT COUNT(*) FROM demandes_credit")
                n = (c.fetchone()[0] or 0) + 1
                ref = f"DEM-{datetime.now().strftime('%Y%m%d')}-{n:04d}"

                # Score IA simulé
                import random
                score_ia = random.randint(400, 800)
                niveau_risque = 'Faible' if score_ia >= 650 else ('Moyen' if score_ia >= 500 else 'Élevé')

                c.execute("""INSERT INTO demandes_credit
                    (reference, client_id, produit_id, agence_id,
                     montant_demande, duree_mois, objet_credit, activite_financee,
                     date_demande, statut, score_ia, niveau_risque)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (ref, client_id,
                     request.form.get('produit_id') or None,
                     request.form.get('agence_id') or None,
                     montant, duree,
                     (request.form.get('objet_credit') or '').strip(),
                     (request.form.get('activite_financee') or '').strip(),
                     datetime.now().date().isoformat(),
                     'En analyse', score_ia, niveau_risque))
                new_id = c.lastrowid
                conn.commit()
                _log('CREATE_DEMANDE', f"Demande {ref} de {_fmt_fcfa(montant)}",
                     entity='demande', entity_id=new_id)
                flash(f"Demande {ref} créée (score IA: {score_ia})", "success")
                conn.close()
                return redirect(f'/demandes/{new_id}')
            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    c.execute("SELECT id, code, nom, prenom FROM clients WHERE actif=1 ORDER BY nom LIMIT 200")
    clients = c.fetchall()
    c.execute("SELECT id, nom FROM produits WHERE actif=1 ORDER BY nom")
    produits = c.fetchall()
    c.execute("SELECT id, nom FROM agences WHERE actif=1 ORDER BY nom")
    agences = c.fetchall()
    conn.close()

    opt_cl = ''.join(f'<option value="{cl["id"]}">{cl["code"]} — {cl["prenom"] or ""} {cl["nom"]}</option>' for cl in clients)
    opt_pr = ''.join(f'<option value="{p["id"]}">{p["nom"]}</option>' for p in produits)
    opt_ag = ''.join(f'<option value="{a["id"]}">{a["nom"]}</option>' for a in agences)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus"></i> Nouvelle demande de crédit</h2></div>
      <a href="/demandes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="form-group" style="grid-column:1/-1"><label>Client *</label>
            <select name="client_id" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">— Choisir —</option>{opt_cl}
            </select>
          </div>
          <div class="form-group"><label>Produit</label>
            <select name="produit_id" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">—</option>{opt_pr}
            </select>
          </div>
          <div class="form-group"><label>Agence</label>
            <select name="agence_id" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">—</option>{opt_ag}
            </select>
          </div>
          <div class="form-group"><label>Montant demandé (FCFA) *</label>
            <input type="number" name="montant_demande" required value="100000" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Durée (mois)</label>
            <input type="number" name="duree_mois" value="12" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group" style="grid-column:1/-1"><label>Objet du crédit</label>
            <input type="text" name="objet_credit" placeholder="Ex: Achat marchandises" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group" style="grid-column:1/-1"><label>Activité financée</label>
            <input type="text" name="activite_financee" placeholder="Ex: Commerce" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Soumettre la demande</button>
          <a href="/demandes" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='demandes', title='Nouvelle demande')
