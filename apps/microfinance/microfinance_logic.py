"""
🏦 MicroFinance 2.0 — Logique métier
Épargne · Remboursements · Recouvrement · Caisse
"""
from flask import Blueprint, request, redirect, flash, jsonify, Response
from flask_login import current_user
import sqlite3
import csv
import io
from datetime import datetime, timedelta

logic_bp = Blueprint('logic', __name__)
_deps = {}


def init_microfinance(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(logic_bp)
    print("[LOGIC] ✅ Module logique complet enregistré")


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
    return current_user and current_user.role in ('admin', 'directeur', 'agent', 'caissier')


def _can_validate():
    return current_user and current_user.role in ('admin', 'directeur')


def _fmt_fcfa(m):
    if not m:
        return "0 F"
    return f"{int(m):,} F".replace(",", " ")


def _fmt_date(d):
    if not d:
        return "-"
    return d[:10] if len(d) >= 10 else d


# ================================================================
# ==================== ÉPARGNE ====================
# ================================================================
@logic_bp.route('/epargne')
@_auth_required
def epargne_list():
    q = (request.args.get('q') or '').strip()

    conn = _db()
    c = conn.cursor()
    sql = """SELECT ce.*, cl.nom AS client_nom, cl.prenom AS client_prenom,
                    cl.code AS client_code, cl.telephone AS client_tel,
                    a.nom AS agence_nom
             FROM comptes_epargne ce
             LEFT JOIN clients cl ON ce.client_id = cl.id
             LEFT JOIN agences a ON ce.agence_id = a.id
             WHERE ce.statut='Actif'"""
    params = []
    if q:
        sql += " AND (cl.nom LIKE ? OR cl.prenom LIKE ? OR ce.numero_compte LIKE ?)"
        params += [f"%{q}%"] * 3
    sql += " ORDER BY ce.date_ouverture DESC LIMIT 200"
    c.execute(sql, params)
    comptes = c.fetchall()

    # Stats
    c.execute("SELECT COUNT(*), COALESCE(SUM(solde), 0) FROM comptes_epargne WHERE statut='Actif'")
    row = c.fetchone()
    nb_comptes = row[0] or 0
    solde_total = row[1] or 0

    mois = datetime.now().strftime('%Y-%m')
    c.execute("""SELECT COUNT(*), COALESCE(SUM(montant), 0) FROM operations_epargne
                 WHERE strftime('%Y-%m', date_operation)=? AND type_operation='Dépôt'""", (mois,))
    row = c.fetchone()
    nb_depots_mois = row[0] or 0
    depots_mois = row[1] or 0

    c.execute("""SELECT COUNT(*), COALESCE(SUM(montant), 0) FROM operations_epargne
                 WHERE strftime('%Y-%m', date_operation)=? AND type_operation='Retrait'""", (mois,))
    row = c.fetchone()
    nb_retraits_mois = row[0] or 0
    retraits_mois = row[1] or 0

    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-piggy-bank"></i> Comptes épargne</h2>
        <div class="page-subtitle">{len(comptes)} compte(s) actif(s)</div></div>
      {'<a href="/epargne/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau compte</a>' if _can_write() else ''}
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-piggy-bank"></i></div>
        <div class="stat-value">{nb_comptes}</div>
        <div class="stat-label">Comptes actifs</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-coins"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(solde_total)}</div>
        <div class="stat-label">Encours épargne</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-arrow-down"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(depots_mois)}</div>
        <div class="stat-label">Dépôts (mois)</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-arrow-up"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(retraits_mois)}</div>
        <div class="stat-label">Retraits (mois)</div></div>
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;align-items:end">
        <div class="form-group" style="flex:1;margin:0">
          <label>Recherche</label>
          <input type="text" name="q" value="{q}" placeholder="N° compte, client..."
                 style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
        </div>
        <button class="btn btn-primary"><i class="fas fa-search"></i> Filtrer</button>
        <a href="/epargne" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>N° Compte</th><th>Client</th><th>Agence</th>
          <th>Solde</th><th>Disponible</th><th>Ouverture</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for cp in comptes:
        content += f"""
        <tr>
          <td><strong>{cp['numero_compte']}</strong></td>
          <td>
            <div style="font-weight:700">{cp['client_prenom'] or ''} {cp['client_nom'] or ''}</div>
            <div style="font-size:0.72rem;color:#94a3b8">{cp['client_code']} · {cp['client_tel'] or ''}</div>
          </td>
          <td>{cp['agence_nom'] or '-'}</td>
          <td><strong style="color:#10b981">{_fmt_fcfa(cp['solde'])}</strong></td>
          <td>{_fmt_fcfa(cp['solde_disponible'])}</td>
          <td>{_fmt_date(cp['date_ouverture'])}</td>
          <td style="white-space:nowrap">
            <a href="/epargne/{cp['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
            {'<a href="/epargne/'+str(cp["id"])+'/operation" class="btn btn-success btn-sm"><i class="fas fa-money-bill"></i></a>' if _can_write() else ''}
          </td>
        </tr>"""
    if not comptes:
        content += '<tr><td colspan="7" class="empty"><i class="fas fa-piggy-bank"></i><br>Aucun compte</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='epargne', title='Épargne')


@logic_bp.route('/epargne/<int:cid>')
@_auth_required
def epargne_detail(cid):
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT ce.*, cl.nom AS client_nom, cl.prenom AS client_prenom,
                        cl.code AS client_code, cl.telephone AS client_tel,
                        a.nom AS agence_nom
                 FROM comptes_epargne ce
                 LEFT JOIN clients cl ON ce.client_id = cl.id
                 LEFT JOIN agences a ON ce.agence_id = a.id
                 WHERE ce.id=?""", (cid,))
    cp = c.fetchone()
    if not cp:
        conn.close()
        flash("Compte introuvable", "danger")
        return redirect('/epargne')

    c.execute("""SELECT * FROM operations_epargne WHERE compte_id=?
                 ORDER BY date_operation DESC LIMIT 50""", (cid,))
    operations = c.fetchall()

    # Stats
    c.execute("""SELECT
                    COALESCE(SUM(CASE WHEN type_operation='Dépôt' THEN montant ELSE 0 END), 0) AS depots,
                    COALESCE(SUM(CASE WHEN type_operation='Retrait' THEN montant ELSE 0 END), 0) AS retraits,
                    COUNT(*) AS nb_operations
                 FROM operations_epargne WHERE compte_id=?""", (cid,))
    stats = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-piggy-bank"></i> {cp['numero_compte']}</h2>
        <div class="page-subtitle">
          {cp['client_prenom'] or ''} {cp['client_nom'] or ''} ({cp['client_code']}) ·
          {cp['agence_nom'] or '-'}
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/epargne" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        {'<a href="/epargne/'+str(cid)+'/operation" class="btn btn-success"><i class="fas fa-money-bill"></i> Nouvelle opération</a>' if _can_write() else ''}
      </div>
    </div>

    <div class="stats">
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-coins"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(cp['solde'])}</div>
        <div class="stat-label">Solde actuel</div></div>
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-arrow-down"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(stats['depots'])}</div>
        <div class="stat-label">Total dépôts</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-arrow-up"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(stats['retraits'])}</div>
        <div class="stat-label">Total retraits</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-list"></i></div>
        <div class="stat-value">{stats['nb_operations']}</div>
        <div class="stat-label">Opérations</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-history"></i> Historique des opérations</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Référence</th><th>Date</th><th>Type</th>
                   <th>Montant</th><th>Solde après</th><th>Mode</th></tr></thead>
        <tbody>"""
    for op in operations:
        badge = 'badge-success' if op['type_operation'] == 'Dépôt' else 'badge-danger'
        signe = '+' if op['type_operation'] == 'Dépôt' else '-'
        content += f"""
        <tr>
          <td><small>{op['reference']}</small></td>
          <td>{_fmt_date(op['date_operation'])}</td>
          <td><span class="badge {badge}">{op['type_operation']}</span></td>
          <td><strong style="color:{'#10b981' if op['type_operation']=='Dépôt' else '#dc2626'}">{signe}{_fmt_fcfa(op['montant'])}</strong></td>
          <td>{_fmt_fcfa(op['solde_apres'])}</td>
          <td><small>{op['mode_paiement'] or '-'}</small></td>
        </tr>"""
    if not operations:
        content += '<tr><td colspan="6" class="empty">Aucune opération</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='epargne', title=cp['numero_compte'])


@logic_bp.route('/epargne/<int:cid>/operation', methods=['GET', 'POST'])
@_auth_required
def epargne_operation(cid):
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/epargne')

    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM comptes_epargne WHERE id=?", (cid,))
    cp = c.fetchone()
    if not cp:
        conn.close()
        flash("Compte introuvable", "danger")
        return redirect('/epargne')

    if request.method == 'POST':
        type_op = request.form.get('type_operation') or 'Dépôt'
        montant = int(request.form.get('montant') or 0)
        mode = request.form.get('mode_paiement') or 'Espèces'
        observation = (request.form.get('observation') or '').strip()

        if montant <= 0:
            flash("Montant invalide", "warning")
        elif type_op == 'Retrait' and montant > cp['solde_disponible']:
            flash("Solde insuffisant", "danger")
        else:
            try:
                solde_avant = cp['solde']
                if type_op == 'Dépôt':
                    nouveau_solde = solde_avant + montant
                else:
                    nouveau_solde = solde_avant - montant

                c.execute("SELECT COUNT(*) FROM operations_epargne")
                n = (c.fetchone()[0] or 0) + 1
                ref = f"OP-{datetime.now().strftime('%Y%m%d')}-{n:05d}"

                c.execute("""INSERT INTO operations_epargne
                    (reference, compte_id, type_operation, montant,
                     solde_avant, solde_apres, mode_paiement,
                     caissier_id, date_operation, observation)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (ref, cid, type_op, montant,
                     solde_avant, nouveau_solde, mode,
                     current_user.id, datetime.now().isoformat(), observation))

                c.execute("""UPDATE comptes_epargne SET
                    solde=?, solde_disponible=?, date_derniere_operation=?
                    WHERE id=?""",
                    (nouveau_solde, nouveau_solde,
                     datetime.now().date().isoformat(), cid))

                conn.commit()
                _log('OPERATION_EPARGNE',
                     f"{type_op} de {_fmt_fcfa(montant)} sur compte {cp['numero_compte']}",
                     entity='compte', entity_id=cid)
                flash(f"{type_op} de {_fmt_fcfa(montant)} enregistré", "success")
                conn.close()
                return redirect(f'/epargne/{cid}')
            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    conn.close()

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-money-bill"></i> Nouvelle opération</h2>
        <div class="page-subtitle">{cp['numero_compte']} — Solde : {_fmt_fcfa(cp['solde'])}</div>
      </div>
      <a href="/epargne/{cid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="form-group"><label>Type d'opération *</label>
            <select name="type_operation" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="Dépôt">💰 Dépôt</option>
              <option value="Retrait">💸 Retrait</option>
            </select>
          </div>
          <div class="form-group"><label>Montant (FCFA) *</label>
            <input type="number" name="montant" required min="100" value="10000"
                   style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Mode de paiement</label>
            <select name="mode_paiement" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option>Espèces</option>
              <option>Wave</option>
              <option>Orange Money</option>
              <option>Free Money</option>
              <option>Chèque</option>
            </select>
          </div>
          <div class="form-group"><label>Observation</label>
            <input type="text" name="observation" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
          <a href="/epargne/{cid}" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='epargne', title='Opération')


@logic_bp.route('/epargne/nouveau', methods=['GET', 'POST'])
@_auth_required
def epargne_new():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/epargne')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        client_id = request.form.get('client_id')
        if not client_id:
            flash("Client obligatoire", "warning")
        else:
            try:
                # Générer numéro unique
                c.execute("SELECT COUNT(*) FROM comptes_epargne")
                n = (c.fetchone()[0] or 0) + 1
                num_compte = f"EP{n:06d}"

                c.execute("""INSERT INTO comptes_epargne
                    (numero_compte, client_id, agence_id, solde,
                     solde_disponible, date_ouverture, statut)
                    VALUES (?,?,?,0,0,?,?)""",
                    (num_compte, client_id,
                     request.form.get('agence_id') or None,
                     datetime.now().date().isoformat(), 'Actif'))
                new_id = c.lastrowid
                conn.commit()
                _log('CREATE_COMPTE_EPARGNE', f"Compte {num_compte} créé",
                     entity='compte', entity_id=new_id)
                flash(f"Compte {num_compte} créé", "success")
                conn.close()
                return redirect(f'/epargne/{new_id}')
            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    c.execute("SELECT id, code, nom, prenom FROM clients WHERE actif=1 ORDER BY nom LIMIT 200")
    clients = c.fetchall()
    c.execute("SELECT id, nom FROM agences WHERE actif=1 ORDER BY nom")
    agences = c.fetchall()
    conn.close()

    opt_cl = ''.join(f'<option value="{cl["id"]}">{cl["code"]} — {cl["prenom"] or ""} {cl["nom"]}</option>' for cl in clients)
    opt_ag = ''.join(f'<option value="{a["id"]}">{a["nom"]}</option>' for a in agences)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus"></i> Nouveau compte épargne</h2></div>
      <a href="/epargne" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="form-group" style="grid-column:1/-1"><label>Client *</label>
            <select name="client_id" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">— Choisir —</option>{opt_cl}
            </select>
          </div>
          <div class="form-group"><label>Agence</label>
            <select name="agence_id" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">—</option>{opt_ag}
            </select>
          </div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Créer le compte</button>
          <a href="/epargne" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='epargne', title='Nouveau compte')


# ================================================================
# ==================== REMBOURSEMENTS ========================
# ================================================================
@logic_bp.route('/remboursements')
@_auth_required
def remboursements_list():
    date_f = request.args.get('date') or datetime.now().date().isoformat()
    q = (request.args.get('q') or '').strip()

    conn = _db()
    c = conn.cursor()
    sql = """SELECT r.*, cr.reference AS credit_ref,
                    cl.nom AS client_nom, cl.prenom AS client_prenom,
                    cl.code AS client_code, cl.telephone AS client_tel
             FROM remboursements r
             LEFT JOIN credits cr ON r.credit_id = cr.id
             LEFT JOIN clients cl ON r.client_id = cl.id
             WHERE date(r.date_paiement) = ?"""
    params = [date_f]
    if q:
        sql += " AND (cl.nom LIKE ? OR cl.prenom LIKE ? OR r.reference LIKE ?)"
        params += [f"%{q}%"] * 3
    sql += " ORDER BY r.date_paiement DESC LIMIT 200"
    c.execute(sql, params)
    remboursements = c.fetchall()

    # Stats
    c.execute("""SELECT COUNT(*), COALESCE(SUM(montant_recu), 0)
                 FROM remboursements WHERE date(date_paiement) = ?""", (date_f,))
    row = c.fetchone()
    nb_jour = row[0] or 0
    montant_jour = row[1] or 0

    mois = datetime.now().strftime('%Y-%m')
    c.execute("""SELECT COUNT(*), COALESCE(SUM(montant_recu), 0)
                 FROM remboursements WHERE strftime('%Y-%m', date_paiement) = ?""", (mois,))
    row = c.fetchone()
    nb_mois = row[0] or 0
    montant_mois = row[1] or 0

    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-money-bill-wave"></i> Remboursements</h2>
        <div class="page-subtitle">Journée du {date_f}</div></div>
      {'<a href="/remboursements/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau remboursement</a>' if _can_write() else ''}
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-calendar-day"></i></div>
        <div class="stat-value">{nb_jour}</div>
        <div class="stat-label">Aujourd'hui</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-coins"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(montant_jour)}</div>
        <div class="stat-label">Montant jour</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-calendar-month"></i></div>
        <div class="stat-value">{nb_mois}</div>
        <div class="stat-label">Ce mois</div></div>
      <div class="stat-card purple"><div class="stat-icon"><i class="fas fa-chart-line"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(montant_mois)}</div>
        <div class="stat-label">Montant mois</div></div>
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Date</label>
          <input type="date" name="date" value="{date_f}"
                 style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
        </div>
        <div class="form-group" style="flex:2;margin:0;min-width:200px">
          <label>Recherche</label>
          <input type="text" name="q" value="{q}" placeholder="Référence, client..."
                 style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
        </div>
        <button class="btn btn-primary"><i class="fas fa-filter"></i> Filtrer</button>
        <a href="/remboursements" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Référence</th><th>Date</th><th>Client</th><th>Crédit</th>
          <th>Montant</th><th>Capital</th><th>Intérêts</th><th>Mode</th>
        </tr></thead><tbody>
    """
    for r in remboursements:
        content += f"""
        <tr>
          <td><small>{r['reference']}</small></td>
          <td>{_fmt_date(r['date_paiement'])}</td>
          <td>
            <div style="font-weight:700">{r['client_prenom'] or ''} {r['client_nom'] or ''}</div>
            <div style="font-size:0.72rem;color:#94a3b8">{r['client_code']}</div>
          </td>
          <td><small>{r['credit_ref']}</small></td>
          <td><strong style="color:#10b981">{_fmt_fcfa(r['montant_recu'])}</strong></td>
          <td>{_fmt_fcfa(r['montant_capital'])}</td>
          <td>{_fmt_fcfa(r['montant_interets'])}</td>
          <td><span class="badge badge-info">{r['mode_paiement']}</span></td>
        </tr>"""
    if not remboursements:
        content += '<tr><td colspan="8" class="empty"><i class="fas fa-money-bill-wave"></i><br>Aucun remboursement</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='remboursements', title='Remboursements')


@logic_bp.route('/remboursements/nouveau', methods=['GET', 'POST'])
@_auth_required
def remboursements_new():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/remboursements')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        credit_id = request.form.get('credit_id')
        montant = int(request.form.get('montant_recu') or 0)
        mode = request.form.get('mode_paiement') or 'Espèces'

        if not credit_id or montant <= 0:
            flash("Crédit et montant obligatoires", "warning")
        else:
            try:
                # Récupérer le crédit
                c.execute("SELECT * FROM credits WHERE id=?", (credit_id,))
                cr = c.fetchone()
                if not cr:
                    flash("Crédit introuvable", "danger")
                else:
                    # Prendre la 1ère échéance en attente
                    c.execute("""SELECT * FROM echeances_credit
                                 WHERE credit_id=? AND statut IN ('À venir', 'En retard')
                                 ORDER BY numero_echeance LIMIT 1""", (credit_id,))
                    ech = c.fetchone()

                    capital = int(montant * 0.7)
                    interets = int(montant * 0.3)

                    c.execute("SELECT COUNT(*) FROM remboursements")
                    n = (c.fetchone()[0] or 0) + 1
                    ref = f"RMB-{datetime.now().strftime('%Y%m%d')}-{n:05d}"

                    c.execute("""INSERT INTO remboursements
                        (reference, credit_id, echeance_id, client_id,
                         montant_recu, montant_capital, montant_interets,
                         mode_paiement, caissier_id, date_paiement)
                        VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (ref, credit_id, ech['id'] if ech else None, cr['client_id'],
                         montant, capital, interets, mode,
                         current_user.id, datetime.now().date().isoformat()))

                    # Mettre à jour échéance
                    if ech:
                        c.execute("""UPDATE echeances_credit SET
                            montant_paye=?, montant_restant=0,
                            date_paiement=?, statut='Payé'
                            WHERE id=?""",
                            (montant, datetime.now().date().isoformat(), ech['id']))

                    # Mettre à jour crédit
                    nouveau_rembourse = (cr['montant_rembourse'] or 0) + montant
                    nouveau_solde = cr['montant_total_du'] - nouveau_rembourse
                    nb_payees = (cr['nb_echeances_payees'] or 0) + 1

                    statut = 'Remboursé' if nouveau_solde <= 0 else 'Actif'

                    c.execute("""UPDATE credits SET
                        montant_rembourse=?, solde_restant=?,
                        nb_echeances_payees=?, statut=?, updated_at=?
                        WHERE id=?""",
                        (nouveau_rembourse, max(0, nouveau_solde),
                         nb_payees, statut, datetime.now().isoformat(), credit_id))

                    conn.commit()
                    _log('REMBOURSEMENT', f"Remboursement {ref} de {_fmt_fcfa(montant)}",
                         entity='remboursement', entity_id=c.lastrowid)
                    flash(f"Remboursement {ref} enregistré", "success")
                    conn.close()
                    return redirect('/remboursements')
            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    # GET
    credit_pre = request.args.get('credit') or ''
    c.execute("""SELECT cr.id, cr.reference, cr.solde_restant,
                        cl.nom, cl.prenom, cl.code
                 FROM credits cr
                 LEFT JOIN clients cl ON cr.client_id = cl.id
                 WHERE cr.statut IN ('Actif', 'En retard')
                 ORDER BY cr.date_decaissement DESC LIMIT 200""")
    credits = c.fetchall()
    conn.close()

    opt_cr = ''
    for cr in credits:
        sel = 'selected' if str(cr['id']) == str(credit_pre) else ''
        opt_cr += f'<option value="{cr["id"]}" {sel}>{cr["reference"]} — {cr["prenom"] or ""} {cr["nom"]} — {_fmt_fcfa(cr["solde_restant"])}</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus"></i> Nouveau remboursement</h2></div>
      <a href="/remboursements" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="form-group" style="grid-column:1/-1"><label>Crédit *</label>
            <select name="credit_id" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">— Choisir un crédit —</option>{opt_cr}
            </select>
          </div>
          <div class="form-group"><label>Montant reçu (FCFA) *</label>
            <input type="number" name="montant_recu" required value="10000" min="1000"
                   style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Mode de paiement</label>
            <select name="mode_paiement" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option>Espèces</option>
              <option>Wave</option>
              <option>Orange Money</option>
              <option>Free Money</option>
              <option>Chèque</option>
            </select>
          </div>
        </div>
        <div style="padding:20px;background:#f0fdff;border-radius:12px;margin-top:20px;border-left:5px solid #06b6d4">
          <p style="font-size:0.85rem;color:#475569">
            <strong>Info :</strong> Le montant sera réparti en 70% capital et 30% intérêts.
            L'échéance la plus ancienne sera automatiquement marquée comme payée.
          </p>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer le paiement</button>
          <a href="/remboursements" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='remboursements', title='Nouveau remboursement')


# ================================================================
# ==================== RECOUVREMENT ========================
# ================================================================
@logic_bp.route('/recouvrement')
@_auth_required
def recouvrement_home():
    conn = _db()
    c = conn.cursor()

    # Échéances en retard
    c.execute("""SELECT ec.*, cr.reference AS credit_ref,
                        cl.id AS client_id, cl.nom AS client_nom, cl.prenom AS client_prenom,
                        cl.telephone AS client_tel, cl.code AS client_code,
                        a.nom AS agence_nom
                 FROM echeances_credit ec
                 INNER JOIN credits cr ON ec.credit_id = cr.id
                 INNER JOIN clients cl ON cr.client_id = cl.id
                 LEFT JOIN agences a ON cr.agence_id = a.id
                 WHERE ec.statut IN ('En retard', 'Impayé')
                   AND cr.statut = 'Actif'
                 ORDER BY ec.jours_retard DESC LIMIT 200""")
    impayes = c.fetchall()

    # Stats par tranche
    c.execute("""SELECT
                    SUM(CASE WHEN jours_retard BETWEEN 1 AND 30 THEN 1 ELSE 0 END) AS t1,
                    SUM(CASE WHEN jours_retard BETWEEN 31 AND 90 THEN 1 ELSE 0 END) AS t2,
                    SUM(CASE WHEN jours_retard > 90 THEN 1 ELSE 0 END) AS t3,
                    COALESCE(SUM(montant_restant), 0) AS total
                 FROM echeances_credit WHERE statut IN ('En retard', 'Impayé')""")
    stats = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-phone"></i> Recouvrement</h2>
        <div class="page-subtitle">{len(impayes)} impayé(s) à traiter</div></div>
    </div>

    <div class="stats">
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-clock"></i></div>
        <div class="stat-value">{stats['t1'] or 0}</div>
        <div class="stat-label">1-30 jours</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-exclamation-triangle"></i></div>
        <div class="stat-value">{stats['t2'] or 0}</div>
        <div class="stat-label">31-90 jours</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-fire"></i></div>
        <div class="stat-value">{stats['t3'] or 0}</div>
        <div class="stat-label">+90 jours</div></div>
      <div class="stat-card purple"><div class="stat-icon"><i class="fas fa-coins"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(stats['total'])}</div>
        <div class="stat-label">Montant total</div></div>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Client</th><th>Crédit</th><th>Échéance</th><th>Montant</th>
          <th>Retard</th><th>Agence</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for e in impayes:
        jours = e['jours_retard'] or 0
        if jours <= 30:
            badge = 'badge-warning'
        elif jours <= 90:
            badge = 'badge-danger'
        else:
            badge = 'badge-danger'

        content += f"""
        <tr>
          <td>
            <div style="font-weight:700">{e['client_prenom'] or ''} {e['client_nom'] or ''}</div>
            <div style="font-size:0.72rem;color:#94a3b8">{e['client_code']} · {e['client_tel'] or ''}</div>
          </td>
          <td><small>{e['credit_ref']}</small></td>
          <td>{_fmt_date(e['date_echeance'])}</td>
          <td><strong style="color:#dc2626">{_fmt_fcfa(e['montant_restant'])}</strong></td>
          <td><span class="badge {badge}">{jours}j</span></td>
          <td><small>{e['agence_nom'] or '-'}</small></td>
          <td>
            <a href="/credits/{e['credit_id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
          </td>
        </tr>"""
    if not impayes:
        content += '<tr><td colspan="7" class="empty"><i class="fas fa-check-circle" style="color:#10b981"></i><br>Aucun impayé</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='recouvrement', title='Recouvrement')


@logic_bp.route('/recouvrement/export.csv')
@_auth_required
def recouvrement_export():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT cl.code, cl.nom, cl.prenom, cl.telephone,
                        cr.reference, ec.date_echeance, ec.montant_restant, ec.jours_retard
                 FROM echeances_credit ec
                 INNER JOIN credits cr ON ec.credit_id = cr.id
                 INNER JOIN clients cl ON cr.client_id = cl.id
                 WHERE ec.statut IN ('En retard', 'Impayé') AND cr.statut='Actif'
                 ORDER BY ec.jours_retard DESC""")
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(['Code client', 'Nom', 'Prénom', 'Téléphone', 'Crédit', 'Échéance', 'Montant', 'Jours retard'])
    for r in rows:
        w.writerow([r['code'], r['nom'], r['prenom'], r['telephone'],
                    r['reference'], r['date_echeance'], r['montant_restant'], r['jours_retard']])

    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=recouvrement_{datetime.now().strftime("%Y%m%d")}.csv'}
    )
