"""
Omega Pointage V2 — CRUD complet
Employés · Pointages · Congés · Plannings · Sites · Départements
Postes · Terminaux · Utilisateurs · Paramètres
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


def _render(content, active='dashboard', title='Omega Pointage'):
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


def _admin_or_rh(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if not (current_user and current_user.is_authenticated and
                current_user.role in ('admin', 'rh')):
            flash("Accès réservé RH/Admin", "danger")
            return redirect('/')
        return f(*a, **k)
    return w


def _can_write():
    return current_user and current_user.role in ('admin', 'rh', 'chef', 'pointage')


def _fmt_duree(minutes):
    if not minutes:
        return "0h00"
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}h{m:02d}"


def _fmt_fcfa(montant):
    if not montant:
        return "0 F"
    return f"{int(montant):,} F".replace(",", " ")


# ================================================================
# ==================== EMPLOYES ====================
# ================================================================
@crud_bp.route('/employes')
@_auth_required
def employes_list():
    q = (request.args.get('q') or '').strip()
    dep = request.args.get('dep') or ''
    site = request.args.get('site') or ''

    conn = _db()
    c = conn.cursor()

    sql = """SELECT e.*,
                    p.nom AS poste_nom, p.code AS poste_code,
                    d.nom AS departement_nom, d.code AS departement_code,
                    s.nom AS site_nom
             FROM employes e
             LEFT JOIN postes p ON e.poste_id = p.id
             LEFT JOIN departements d ON e.departement_id = d.id
             LEFT JOIN sites s ON e.site_id = s.id
             WHERE e.actif=1"""
    params = []
    if q:
        sql += " AND (e.nom LIKE ? OR e.prenom LIKE ? OR e.matricule LIKE ? OR e.telephone LIKE ?)"
        params += [f"%{q}%"] * 4
    if dep:
        sql += " AND e.departement_id=?"
        params.append(dep)
    if site:
        sql += " AND e.site_id=?"
        params.append(site)
    sql += " ORDER BY e.nom, e.prenom"
    c.execute(sql, params)
    employes = c.fetchall()

    c.execute("SELECT * FROM departements WHERE actif=1 ORDER BY nom")
    departements = c.fetchall()
    c.execute("SELECT * FROM sites WHERE actif=1 ORDER BY nom")
    sites = c.fetchall()
    conn.close()

    opt_dep = '<option value="">Tous départements</option>'
    for d in departements:
        sel = 'selected' if str(d['id']) == dep else ''
        opt_dep += f'<option value="{d["id"]}" {sel}>{d["nom"]}</option>'
    opt_site = '<option value="">Tous sites</option>'
    for s in sites:
        sel = 'selected' if str(s['id']) == site else ''
        opt_site += f'<option value="{s["id"]}" {sel}>{s["nom"]}</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-users"></i> Employés</h2>
        <div class="page-subtitle">{len(employes)} employé(s) actif(s)</div></div>
      {'<a href="/employes/nouveau" class="btn btn-primary"><i class="fas fa-user-plus"></i> Nouvel employé</a>' if _can_write() else ''}
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:2;margin:0;min-width:200px">
          <label>Recherche</label>
          <input type="text" name="q" value="{q}" placeholder="Nom, matricule, téléphone...">
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:180px">
          <label>Département</label>
          <select name="dep">{opt_dep}</select>
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:180px">
          <label>Site</label>
          <select name="site">{opt_site}</select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-search"></i> Filtrer</button>
        <a href="/employes" class="btn btn-info"><i class="fas fa-rotate"></i> Reset</a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Matricule</th><th>Nom complet</th><th>Poste</th>
          <th>Département</th><th>Site</th><th>Téléphone</th>
          <th>Salaire</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for e in employes:
        content += f"""
        <tr>
          <td><strong>{e['matricule']}</strong></td>
          <td>
            <div style="font-weight:700">{e['prenom']} {e['nom']}</div>
            <div style="font-size:0.72rem;color:#94a3b8">{e['email'] or ''}</div>
          </td>
          <td>{e['poste_nom'] or '-'}</td>
          <td><span class="badge badge-primary">{e['departement_code'] or '-'}</span></td>
          <td>{e['site_nom'] or '-'}</td>
          <td><small>{e['telephone'] or '-'}</small></td>
          <td><small>{_fmt_fcfa(e['salaire_base'])}</small></td>
          <td style="white-space:nowrap">
            <a href="/employes/{e['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
            {'<a href="/employes/'+str(e['id'])+'/modifier" class="btn btn-warning btn-sm"><i class="fas fa-pen"></i></a>' if _can_write() else ''}
          </td>
        </tr>"""
    if not employes:
        content += '<tr><td colspan="8" class="empty"><i class="fas fa-users"></i><br>Aucun employé</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='employes', title='Employés')


@crud_bp.route('/employes/<int:eid>')
@_auth_required
def employes_detail(eid):
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT e.*, p.nom AS poste_nom, d.nom AS departement_nom,
                        s.nom AS site_nom
                 FROM employes e
                 LEFT JOIN postes p ON e.poste_id = p.id
                 LEFT JOIN departements d ON e.departement_id = d.id
                 LEFT JOIN sites s ON e.site_id = s.id
                 WHERE e.id=?""", (eid,))
    e = c.fetchone()
    if not e:
        conn.close()
        flash("Employé introuvable", "danger")
        return redirect('/employes')

    # Pointages récents
    c.execute("""SELECT * FROM pointages WHERE employe_id=?
                 ORDER BY date_pointage DESC LIMIT 15""", (eid,))
    pointages = c.fetchall()

    # Congés
    c.execute("""SELECT c.*, tc.nom AS type_nom FROM conges c
                 LEFT JOIN types_conges tc ON c.type_conge_id = tc.id
                 WHERE c.employe_id=? ORDER BY c.date_debut DESC LIMIT 10""", (eid,))
    conges = c.fetchall()

    # Stats mois en cours
    mois = datetime.now().strftime('%Y-%m')
    c.execute("""SELECT COUNT(*) AS nb,
                        COALESCE(SUM(heures_travaillees),0) AS h,
                        COALESCE(SUM(heures_sup),0) AS hs,
                        SUM(CASE WHEN statut='Retard' THEN 1 ELSE 0 END) AS retards,
                        SUM(CASE WHEN statut='Absent' THEN 1 ELSE 0 END) AS absences
                 FROM pointages
                 WHERE employe_id=? AND strftime('%Y-%m', date_pointage)=?""", (eid, mois))
    stats = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-user"></i> {e['prenom']} {e['nom']}</h2>
        <div class="page-subtitle">
          <strong>{e['matricule']}</strong> · {e['poste_nom'] or '-'} · {e['departement_nom'] or '-'}
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/employes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        {'<a href="/employes/'+str(eid)+'/modifier" class="btn btn-warning"><i class="fas fa-pen"></i> Modifier</a>' if _can_write() else ''}
        {'<a href="/api/employe/'+str(eid)+'/qr-badge" target="_blank" class="btn btn-success"><i class="fas fa-qrcode"></i> Badge QR</a>' if _can_write() else ''}
      </div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-fingerprint"></i></div>
        <div class="stat-value">{stats['nb'] if stats else 0}</div>
        <div class="stat-label">Pointages ce mois</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-hourglass"></i></div>
        <div class="stat-value">{(stats['h'] if stats else 0):.0f}h</div>
        <div class="stat-label">Heures travaillées</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-plus"></i></div>
        <div class="stat-value">{(stats['hs'] if stats else 0):.1f}h</div>
        <div class="stat-label">Heures sup</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-clock"></i></div>
        <div class="stat-value">{(stats['retards'] if stats else 0)}</div>
        <div class="stat-label">Retards</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
      <div class="form-grid">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Matricule</label>
             <div style="font-weight:700">{e['matricule']}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Date embauche</label>
             <div>{e['date_embauche'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Type contrat</label>
             <div>{e['type_contrat'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Salaire base</label>
             <div>{_fmt_fcfa(e['salaire_base'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Téléphone</label>
             <div>{e['telephone'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Email</label>
             <div>{e['email'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Site</label>
             <div>{e['site_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Mode paiement</label>
             <div>{e['mode_paiement'] or '-'}</div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-fingerprint"></i> Derniers pointages</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Date</th><th>Entrée</th><th>Sortie</th><th>Durée</th><th>H. sup</th><th>Statut</th></tr></thead>
        <tbody>"""
    for p in pointages:
        badge = 'badge-success'
        if p['statut'] == 'Retard': badge = 'badge-warning'
        elif p['statut'] == 'Absent': badge = 'badge-danger'
        content += f"""
        <tr>
          <td>{p['date_pointage']}</td>
          <td>{p['heure_entree'] or '-'}</td>
          <td>{p['heure_sortie'] or '-'}</td>
          <td>{_fmt_duree(p['duree_minutes'] or 0)}</td>
          <td>{p['heures_sup'] or 0:.1f}h</td>
          <td><span class="badge {badge}">{p['statut']}</span></td>
        </tr>"""
    if not pointages:
        content += '<tr><td colspan="6" class="empty">Aucun pointage</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='employes', title=e['prenom'] + ' ' + e['nom'])


@crud_bp.route('/employes/nouveau', methods=['GET', 'POST'])
@_auth_required
def employes_new():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/employes')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        matricule = (request.form.get('matricule') or '').strip()
        if not matricule:
            # Auto-générer
            c.execute("SELECT COUNT(*) FROM employes")
            n = (c.fetchone()[0] or 0) + 1
            matricule = f"EMP{n:04d}"

        nom = (request.form.get('nom') or '').strip()
        prenom = (request.form.get('prenom') or '').strip()

        if not nom or not prenom:
            flash("Nom et prénom obligatoires", "warning")
        else:
            try:
                c.execute("""INSERT INTO employes
                    (matricule, nom, prenom, sexe, telephone, email, poste_id,
                     departement_id, site_id, date_embauche, type_contrat,
                     salaire_base, mode_paiement, actif, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)""",
                    (matricule, nom, prenom,
                     request.form.get('sexe') or 'M',
                     (request.form.get('telephone') or '').strip(),
                     (request.form.get('email') or '').strip(),
                     request.form.get('poste_id') or None,
                     request.form.get('departement_id') or None,
                     request.form.get('site_id') or None,
                     request.form.get('date_embauche') or datetime.now().date().isoformat(),
                     request.form.get('type_contrat') or 'CDI',
                     int(request.form.get('salaire_base') or 0),
                     request.form.get('mode_paiement') or 'Virement',
                     datetime.now().isoformat(), datetime.now().isoformat()))
                new_id = c.lastrowid
                conn.commit()
                _log('CREATE_EMPLOYE', f"Employé {prenom} {nom} créé (mat={matricule})",
                     entity='employe', entity_id=new_id)
                flash(f"Employé '{prenom} {nom}' créé", "success")
                conn.close()
                return redirect(f'/employes/{new_id}')
            except Exception as e:
                flash(f"Erreur : {e}", "danger")

    c.execute("SELECT * FROM postes WHERE actif=1 ORDER BY nom")
    postes = c.fetchall()
    c.execute("SELECT * FROM departements WHERE actif=1 ORDER BY nom")
    deps = c.fetchall()
    c.execute("SELECT * FROM sites WHERE actif=1 ORDER BY nom")
    sites = c.fetchall()
    conn.close()

    opt_p = ''.join(f'<option value="{p["id"]}">{p["nom"]}</option>' for p in postes)
    opt_d = ''.join(f'<option value="{d["id"]}">{d["nom"]}</option>' for d in deps)
    opt_s = ''.join(f'<option value="{s["id"]}">{s["nom"]}</option>' for s in sites)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-user-plus"></i> Nouvel employé</h2></div>
      <a href="/employes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group">
            <label>Matricule</label>
            <input type="text" name="matricule" placeholder="Auto si vide">
          </div>
          <div class="form-group">
            <label>Sexe</label>
            <select name="sexe">
              <option value="M">Masculin</option>
              <option value="F">Féminin</option>
            </select>
          </div>
          <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
          <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" required></div>
          <div class="form-group"><label>Téléphone</label><input type="text" name="telephone"></div>
          <div class="form-group"><label>Email</label><input type="email" name="email"></div>
          <div class="form-group"><label>Poste</label><select name="poste_id"><option value="">—</option>{opt_p}</select></div>
          <div class="form-group"><label>Département</label><select name="departement_id"><option value="">—</option>{opt_d}</select></div>
          <div class="form-group"><label>Site</label><select name="site_id"><option value="">—</option>{opt_s}</select></div>
          <div class="form-group"><label>Date embauche</label><input type="date" name="date_embauche" value="{datetime.now().date().isoformat()}"></div>
          <div class="form-group"><label>Type contrat</label>
            <select name="type_contrat">
              <option>CDI</option><option>CDD</option><option>Stage</option>
              <option>Intérim</option><option>Prestataire</option>
            </select>
          </div>
          <div class="form-group"><label>Salaire base (FCFA)</label><input type="number" name="salaire_base" value="0"></div>
          <div class="form-group"><label>Mode paiement</label>
            <select name="mode_paiement">
              <option>Virement</option><option>Espèces</option>
              <option>Chèque</option><option>Mobile Money</option>
            </select>
          </div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Créer</button>
          <a href="/employes" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='employes', title='Nouvel employé')


@crud_bp.route('/employes/<int:eid>/modifier', methods=['GET', 'POST'])
@_auth_required
def employes_edit(eid):
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/employes')

    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM employes WHERE id=?", (eid,))
    e = c.fetchone()
    if not e:
        conn.close()
        flash("Employé introuvable", "danger")
        return redirect('/employes')

    if request.method == 'POST':
        c.execute("""UPDATE employes SET
            nom=?, prenom=?, sexe=?, telephone=?, email=?,
            poste_id=?, departement_id=?, site_id=?, date_embauche=?,
            type_contrat=?, salaire_base=?, mode_paiement=?, updated_at=?
            WHERE id=?""",
            ((request.form.get('nom') or '').strip(),
             (request.form.get('prenom') or '').strip(),
             request.form.get('sexe') or 'M',
             (request.form.get('telephone') or '').strip(),
             (request.form.get('email') or '').strip(),
             request.form.get('poste_id') or None,
             request.form.get('departement_id') or None,
             request.form.get('site_id') or None,
             request.form.get('date_embauche') or None,
             request.form.get('type_contrat') or 'CDI',
             int(request.form.get('salaire_base') or 0),
             request.form.get('mode_paiement') or 'Virement',
             datetime.now().isoformat(), eid))
        conn.commit()
        _log('UPDATE_EMPLOYE', f"Employé id={eid} modifié",
             entity='employe', entity_id=eid)
        conn.close()
        flash("Employé mis à jour", "success")
        return redirect(f'/employes/{eid}')

    c.execute("SELECT * FROM postes WHERE actif=1 ORDER BY nom")
    postes = c.fetchall()
    c.execute("SELECT * FROM departements WHERE actif=1 ORDER BY nom")
    deps = c.fetchall()
    c.execute("SELECT * FROM sites WHERE actif=1 ORDER BY nom")
    sites = c.fetchall()
    conn.close()

    def opt(items, current, label='nom'):
        return ''.join(f'<option value="{i["id"]}" {"selected" if current==i["id"] else ""}>{i[label]}</option>' for i in items)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-pen"></i> Modifier employé</h2></div>
      <a href="/employes/{eid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group"><label>Nom</label><input type="text" name="nom" value="{e['nom']}" required></div>
          <div class="form-group"><label>Prénom</label><input type="text" name="prenom" value="{e['prenom']}" required></div>
          <div class="form-group"><label>Sexe</label>
            <select name="sexe">
              <option value="M" {"selected" if e['sexe']=='M' else ''}>Masculin</option>
              <option value="F" {"selected" if e['sexe']=='F' else ''}>Féminin</option>
            </select>
          </div>
          <div class="form-group"><label>Téléphone</label><input type="text" name="telephone" value="{e['telephone'] or ''}"></div>
          <div class="form-group"><label>Email</label><input type="email" name="email" value="{e['email'] or ''}"></div>
          <div class="form-group"><label>Poste</label>
            <select name="poste_id"><option value="">—</option>{opt(postes, e['poste_id'])}</select>
          </div>
          <div class="form-group"><label>Département</label>
            <select name="departement_id"><option value="">—</option>{opt(deps, e['departement_id'])}</select>
          </div>
          <div class="form-group"><label>Site</label>
            <select name="site_id"><option value="">—</option>{opt(sites, e['site_id'])}</select>
          </div>
          <div class="form-group"><label>Date embauche</label><input type="date" name="date_embauche" value="{e['date_embauche'] or ''}"></div>
          <div class="form-group"><label>Salaire base</label><input type="number" name="salaire_base" value="{e['salaire_base'] or 0}"></div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
          <a href="/employes/{eid}" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='employes', title='Modifier employé')


# ================================================================
# ==================== POINTAGES ====================
# ================================================================
@crud_bp.route('/pointages')
@_auth_required
def pointages_list():
    date = request.args.get('date') or datetime.now().date().isoformat()
    employe_id = request.args.get('employe') or ''
    statut = request.args.get('statut') or ''

    conn = _db()
    c = conn.cursor()
    sql = """SELECT p.*, e.matricule, e.nom, e.prenom,
                    d.nom AS departement_nom
             FROM pointages p
             LEFT JOIN employes e ON p.employe_id = e.id
             LEFT JOIN departements d ON e.departement_id = d.id
             WHERE p.date_pointage = ?"""
    params = [date]
    if employe_id:
        sql += " AND p.employe_id = ?"
        params.append(employe_id)
    if statut:
        sql += " AND p.statut = ?"
        params.append(statut)
    sql += " ORDER BY p.heure_entree DESC"
    c.execute(sql, params)
    pointages = c.fetchall()

    c.execute("SELECT id, matricule, nom, prenom FROM employes WHERE actif=1 ORDER BY nom")
    employes = c.fetchall()
    conn.close()

    opt_emp = '<option value="">Tous employés</option>'
    for e in employes:
        sel = 'selected' if str(e['id']) == employe_id else ''
        opt_emp += f'<option value="{e["id"]}" {sel}>{e["prenom"]} {e["nom"]} ({e["matricule"]})</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-fingerprint"></i> Pointages</h2>
        <div class="page-subtitle">{len(pointages)} pointage(s) le {date}</div></div>
      {'<a href="/pointages/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau pointage</a>' if _can_write() else ''}
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Date</label>
          <input type="date" name="date" value="{date}">
        </div>
        <div class="form-group" style="flex:2;margin:0;min-width:220px">
          <label>Employé</label>
          <select name="employe">{opt_emp}</select>
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Statut</label>
          <select name="statut">
            <option value="">Tous</option>
            <option value="Normal" {"selected" if statut=="Normal" else ""}>Normal</option>
            <option value="Retard" {"selected" if statut=="Retard" else ""}>Retard</option>
            <option value="Absent" {"selected" if statut=="Absent" else ""}>Absent</option>
          </select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-filter"></i> Filtrer</button>
        <a href="/pointages" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Employé</th><th>Matricule</th><th>Entrée</th><th>Sortie</th>
          <th>Durée</th><th>H. sup</th><th>Statut</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for p in pointages:
        badge = 'badge-success'
        if p['statut'] == 'Retard': badge = 'badge-warning'
        elif p['statut'] == 'Absent': badge = 'badge-danger'
        content += f"""
        <tr>
          <td><strong>{p['prenom']} {p['nom']}</strong>
              <div style="font-size:0.7rem;color:#94a3b8">{p['departement_nom'] or '-'}</div></td>
          <td><small>{p['matricule']}</small></td>
          <td>{p['heure_entree'] or '-'}</td>
          <td>{p['heure_sortie'] or '-'}</td>
          <td>{_fmt_duree(p['duree_minutes'] or 0)}</td>
          <td>{p['heures_sup'] or 0:.1f}h</td>
          <td><span class="badge {badge}">{p['statut']}</span></td>
          <td>
            {'<a href="/pointages/'+str(p["id"])+'/modifier" class="btn btn-warning btn-sm"><i class="fas fa-pen"></i></a>' if _can_write() else ''}
          </td>
        </tr>"""
    if not pointages:
        content += '<tr><td colspan="8" class="empty"><i class="fas fa-fingerprint"></i><br>Aucun pointage</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='pointages', title='Pointages')


@crud_bp.route('/pointages/<int:pid>/modifier', methods=['GET', 'POST'])
@_auth_required
def pointages_edit(pid):
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/pointages')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT p.*, e.nom, e.prenom, e.matricule
                 FROM pointages p LEFT JOIN employes e ON p.employe_id = e.id
                 WHERE p.id=?""", (pid,))
    p = c.fetchone()
    if not p:
        conn.close()
        flash("Pointage introuvable", "danger")
        return redirect('/pointages')

    if request.method == 'POST':
        entree = request.form.get('heure_entree') or None
        sortie = request.form.get('heure_sortie') or None

        # Recalcul durée
        duree_min = None
        heures_sup = 0
        if entree and sortie:
            h_e = int(entree.split(':')[0]) * 60 + int(entree.split(':')[1])
            h_s = int(sortie.split(':')[0]) * 60 + int(sortie.split(':')[1])
            duree_min = h_s - h_e - 60  # -1h pause
            heures_sup = max(0, duree_min / 60 - 8)

        c.execute("""UPDATE pointages SET
            heure_entree=?, heure_sortie=?, duree_minutes=?,
            heures_sup=?, statut=?, notes=?
            WHERE id=?""",
            (entree, sortie, duree_min, round(heures_sup, 2),
             request.form.get('statut') or 'Normal',
             (request.form.get('notes') or '').strip(), pid))
        conn.commit()
        _log('UPDATE_POINTAGE', f"Pointage id={pid} modifié",
             entity='pointage', entity_id=pid)
        conn.close()
        flash("Pointage mis à jour", "success")
        return redirect('/pointages')

    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-pen"></i> Modifier pointage</h2></div>
      <a href="/pointages" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <div style="padding:15px;background:#f0fdff;border-radius:12px;margin-bottom:20px">
        <strong>{p['prenom']} {p['nom']}</strong> ({p['matricule']}) — {p['date_pointage']}
      </div>
      <form method="POST">
        <div class="form-grid">
          <div class="form-group"><label>Heure entrée</label>
            <input type="time" name="heure_entree" value="{p['heure_entree'] or ''}"></div>
          <div class="form-group"><label>Heure sortie</label>
            <input type="time" name="heure_sortie" value="{p['heure_sortie'] or ''}"></div>
          <div class="form-group"><label>Statut</label>
            <select name="statut">
              <option value="Normal" {"selected" if p['statut']=='Normal' else ''}>Normal</option>
              <option value="Retard" {"selected" if p['statut']=='Retard' else ''}>Retard</option>
              <option value="Absent" {"selected" if p['statut']=='Absent' else ''}>Absent</option>
              <option value="Mission" {"selected" if p['statut']=='Mission' else ''}>Mission</option>
              <option value="Congé" {"selected" if p['statut']=='Congé' else ''}>Congé</option>
            </select>
          </div>
          <div class="form-group form-full"><label>Notes</label>
            <textarea name="notes" rows="2">{p['notes'] or ''}</textarea></div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
          <a href="/pointages" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='pointages', title='Modifier pointage')


# ================================================================
# ==================== CONGES ====================
# ================================================================
@crud_bp.route('/conges')
@_auth_required
def conges_list():
    statut = request.args.get('statut') or ''
    conn = _db()
    c = conn.cursor()
    sql = """SELECT c.*, e.matricule, e.nom, e.prenom,
                    tc.nom AS type_nom, tc.couleur AS type_couleur
             FROM conges c
             LEFT JOIN employes e ON c.employe_id = e.id
             LEFT JOIN types_conges tc ON c.type_conge_id = tc.id
             WHERE 1=1"""
    params = []
    if statut:
        sql += " AND c.statut=?"
        params.append(statut)
    sql += " ORDER BY c.date_debut DESC LIMIT 100"
    c.execute(sql, params)
    conges = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plane-departure"></i> Congés</h2>
        <div class="page-subtitle">{len(conges)} demande(s)</div></div>
      {'<a href="/conges/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle demande</a>' if _can_write() else ''}
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px">
        <select name="statut" style="flex:1;padding:12px 15px;border:2px solid #f1f5f9;border-radius:11px">
          <option value="">Tous statuts</option>
          <option value="En attente" {"selected" if statut=="En attente" else ""}>En attente</option>
          <option value="Approuvé" {"selected" if statut=="Approuvé" else ""}>Approuvé</option>
          <option value="Refusé" {"selected" if statut=="Refusé" else ""}>Refusé</option>
        </select>
        <button class="btn btn-primary"><i class="fas fa-filter"></i> Filtrer</button>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Employé</th><th>Type</th><th>Du</th><th>Au</th>
          <th>Jours</th><th>Motif</th><th>Statut</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for cg in conges:
        badge = 'badge-warning'
        if cg['statut'] == 'Approuvé': badge = 'badge-success'
        elif cg['statut'] == 'Refusé': badge = 'badge-danger'
        content += f"""
        <tr>
          <td><strong>{cg['prenom']} {cg['nom']}</strong>
              <div style="font-size:0.72rem;color:#94a3b8">{cg['matricule']}</div></td>
          <td><span class="badge" style="background:{cg['type_couleur'] or '#06b6d4'};color:white">{cg['type_nom'] or '-'}</span></td>
          <td>{cg['date_debut']}</td>
          <td>{cg['date_fin']}</td>
          <td><span class="badge badge-primary">{cg['nb_jours']} j</span></td>
          <td><small>{cg['motif'][:40] if cg['motif'] else '-'}</small></td>
          <td><span class="badge {badge}">{cg['statut']}</span></td>
          <td style="white-space:nowrap">
            {'<a href="/conges/'+str(cg["id"])+'/approuver" class="btn btn-success btn-sm"><i class="fas fa-check"></i></a>' if cg['statut']=='En attente' and current_user.role in ('admin','rh','chef') else ''}
            {'<a href="/conges/'+str(cg["id"])+'/refuser" class="btn btn-danger btn-sm"><i class="fas fa-xmark"></i></a>' if cg['statut']=='En attente' and current_user.role in ('admin','rh','chef') else ''}
          </td>
        </tr>"""
    if not conges:
        content += '<tr><td colspan="8" class="empty"><i class="fas fa-plane-departure"></i><br>Aucune demande</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='conges', title='Congés')


@crud_bp.route('/conges/nouveau', methods=['GET', 'POST'])
@_auth_required
def conges_new():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/conges')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        employe_id = request.form.get('employe_id')
        type_id = request.form.get('type_conge_id')
        date_debut = request.form.get('date_debut')
        date_fin = request.form.get('date_fin')
        motif = (request.form.get('motif') or '').strip()

        if not (employe_id and type_id and date_debut and date_fin):
            flash("Tous les champs obligatoires", "warning")
        else:
            d1 = datetime.fromisoformat(date_debut)
            d2 = datetime.fromisoformat(date_fin)
            nb_jours = (d2 - d1).days + 1

            c.execute("""INSERT INTO conges
                (employe_id, type_conge_id, date_debut, date_fin, nb_jours,
                 motif, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (employe_id, type_id, date_debut, date_fin, nb_jours,
                 motif, 'En attente', datetime.now().isoformat()))
            conn.commit()
            _log('CREATE_CONGE', f"Demande de congé pour employé id={employe_id}",
                 entity='conge', entity_id=c.lastrowid)
            flash("Demande de congé créée", "success")
            conn.close()
            return redirect('/conges')

    c.execute("SELECT id, matricule, nom, prenom FROM employes WHERE actif=1 ORDER BY nom")
    employes = c.fetchall()
    c.execute("SELECT * FROM types_conges WHERE actif=1 ORDER BY nom")
    types = c.fetchall()
    conn.close()

    opt_e = ''.join(f'<option value="{e["id"]}">{e["prenom"]} {e["nom"]} ({e["matricule"]})</option>' for e in employes)
    opt_t = ''.join(f'<option value="{t["id"]}">{t["nom"]} ({t["jours_par_an"]} j/an)</option>' for t in types)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus"></i> Nouvelle demande de congé</h2></div>
      <a href="/conges" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group form-full"><label>Employé *</label>
            <select name="employe_id" required><option value="">— Choisir —</option>{opt_e}</select></div>
          <div class="form-group form-full"><label>Type de congé *</label>
            <select name="type_conge_id" required><option value="">— Choisir —</option>{opt_t}</select></div>
          <div class="form-group"><label>Date début *</label><input type="date" name="date_debut" required></div>
          <div class="form-group"><label>Date fin *</label><input type="date" name="date_fin" required></div>
          <div class="form-group form-full"><label>Motif</label>
            <textarea name="motif" rows="3"></textarea></div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Créer la demande</button>
          <a href="/conges" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='conges', title='Nouveau congé')


@crud_bp.route('/conges/<int:cid>/approuver')
@_auth_required
def conges_approuver(cid):
    if current_user.role not in ('admin', 'rh', 'chef'):
        flash("Droits insuffisants", "danger")
        return redirect('/conges')
    conn = _db()
    c = conn.cursor()
    c.execute("""UPDATE conges SET statut='Approuvé',
                 valide_par=?, date_validation=? WHERE id=?""",
              (current_user.id, datetime.now().isoformat(), cid))
    conn.commit()
    _log('CONGE_APPROUVE', f"Congé id={cid} approuvé", entity='conge', entity_id=cid)
    conn.close()
    flash("Congé approuvé", "success")
    return redirect('/conges')


@crud_bp.route('/conges/<int:cid>/refuser')
@_auth_required
def conges_refuser(cid):
    if current_user.role not in ('admin', 'rh', 'chef'):
        flash("Droits insuffisants", "danger")
        return redirect('/conges')
    conn = _db()
    c = conn.cursor()
    c.execute("""UPDATE conges SET statut='Refusé',
                 valide_par=?, date_validation=? WHERE id=?""",
              (current_user.id, datetime.now().isoformat(), cid))
    conn.commit()
    _log('CONGE_REFUSE', f"Congé id={cid} refusé", entity='conge', entity_id=cid)
    conn.close()
    flash("Congé refusé", "info")
    return redirect('/conges')


# ================================================================
# ==================== PLANNINGS ====================
# ================================================================
@crud_bp.route('/plannings')
@_auth_required
def plannings_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT pl.*, e.matricule, e.nom, e.prenom,
                        st.nom AS shift_nom, st.couleur AS shift_couleur,
                        s.nom AS site_nom
                 FROM plannings pl
                 LEFT JOIN employes e ON pl.employe_id = e.id
                 LEFT JOIN shift_types st ON pl.shift_type_id = st.id
                 LEFT JOIN sites s ON pl.site_id = s.id
                 WHERE date(pl.date_planning) >= date('now', '-7 days')
                 ORDER BY pl.date_planning DESC LIMIT 100""")
    plannings = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-calendar-days"></i> Plannings</h2>
        <div class="page-subtitle">{len(plannings)} planning(s)</div></div>
      {'<a href="/plannings/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau</a>' if _can_write() else ''}
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Date</th><th>Employé</th><th>Shift</th>
          <th>Horaire</th><th>Site</th><th>Statut</th>
        </tr></thead><tbody>
    """
    for pl in plannings:
        content += f"""
        <tr>
          <td><strong>{pl['date_planning']}</strong></td>
          <td>{pl['prenom']} {pl['nom']}</td>
          <td><span class="badge" style="background:{pl['shift_couleur'] or '#06b6d4'};color:white">{pl['shift_nom'] or '-'}</span></td>
          <td><small>{pl['heure_debut_prevue'] or '-'} → {pl['heure_fin_prevue'] or '-'}</small></td>
          <td>{pl['site_nom'] or '-'}</td>
          <td><span class="badge badge-info">{pl['statut']}</span></td>
        </tr>"""
    if not plannings:
        content += '<tr><td colspan="6" class="empty"><i class="fas fa-calendar-days"></i><br>Aucun planning</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='plannings', title='Plannings')


# ================================================================
# ==================== HEURES SUP ====================
# ================================================================
@crud_bp.route('/heures-sup')
@_auth_required
def heures_sup_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT hs.*, e.matricule, e.nom, e.prenom
                 FROM heures_sup hs
                 LEFT JOIN employes e ON hs.employe_id = e.id
                 ORDER BY hs.date_hs DESC LIMIT 100""")
    hs = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus-circle"></i> Heures supplémentaires</h2>
        <div class="page-subtitle">{len(hs)} enregistrement(s)</div></div>
      {'<a href="/heures-sup/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Saisir HS</a>' if _can_write() else ''}
    </div>
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Date</th><th>Employé</th><th>Heures</th>
          <th>Majoration</th><th>Motif</th><th>Statut</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for h in hs:
        badge = 'badge-warning' if h['statut'] == 'En attente' else (
            'badge-success' if h['statut'] == 'Approuvé' else 'badge-danger')
        content += f"""
        <tr>
          <td><strong>{h['date_hs']}</strong></td>
          <td>{h['prenom']} {h['nom']}</td>
          <td><span class="badge badge-primary">{h['nb_heures']:.1f}h</span></td>
          <td><small>×{h['taux_majoration']}</small></td>
          <td><small>{h['motif'][:40] if h['motif'] else '-'}</small></td>
          <td><span class="badge {badge}">{h['statut']}</span></td>
          <td>
            {'<a href="/heures-sup/'+str(h["id"])+'/approuver" class="btn btn-success btn-sm"><i class="fas fa-check"></i></a>' if h['statut']=='En attente' and current_user.role in ('admin','rh','chef') else ''}
          </td>
        </tr>"""
    if not hs:
        content += '<tr><td colspan="7" class="empty"><i class="fas fa-plus-circle"></i><br>Aucune heure sup</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='hs', title='Heures sup')


@crud_bp.route('/heures-sup/nouveau', methods=['GET', 'POST'])
@_auth_required
def heures_sup_new():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/heures-sup')
    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        try:
            c.execute("""INSERT INTO heures_sup
                (employe_id, date_hs, nb_heures, taux_majoration, motif, statut, created_at)
                VALUES (?,?,?,?,?,?,?)""",
                (request.form.get('employe_id'),
                 request.form.get('date_hs'),
                 float(request.form.get('nb_heures') or 0),
                 float(request.form.get('taux_majoration') or 1.25),
                 (request.form.get('motif') or '').strip(),
                 'En attente', datetime.now().isoformat()))
            conn.commit()
            _log('CREATE_HS', f"Heures sup pour employé id={request.form.get('employe_id')}")
            flash("Heures sup enregistrées", "success")
            conn.close()
            return redirect('/heures-sup')
        except Exception as e:
            flash(f"Erreur : {e}", "danger")

    c.execute("SELECT id, matricule, nom, prenom FROM employes WHERE actif=1 ORDER BY nom")
    employes = c.fetchall()
    conn.close()

    opt_e = ''.join(f'<option value="{e["id"]}">{e["prenom"]} {e["nom"]} ({e["matricule"]})</option>' for e in employes)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus-circle"></i> Saisir heures sup</h2></div>
      <a href="/heures-sup" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card"><form method="POST">
      <div class="form-grid">
        <div class="form-group form-full"><label>Employé *</label>
          <select name="employe_id" required><option value="">— Choisir —</option>{opt_e}</select></div>
        <div class="form-group"><label>Date *</label>
          <input type="date" name="date_hs" required value="{datetime.now().date().isoformat()}"></div>
        <div class="form-group"><label>Nombre d'heures *</label>
          <input type="number" step="0.5" name="nb_heures" required value="2"></div>
        <div class="form-group"><label>Taux majoration</label>
          <select name="taux_majoration">
            <option value="1.25">×1.25 (jour normal)</option>
            <option value="1.5">×1.5 (nuit/weekend)</option>
            <option value="2.0">×2.0 (jour férié)</option>
          </select>
        </div>
        <div class="form-group form-full"><label>Motif</label>
          <textarea name="motif" rows="2"></textarea></div>
      </div>
      <button class="btn btn-primary" style="margin-top:20px"><i class="fas fa-check"></i> Enregistrer</button>
    </form></div>"""
    return _render(content, active='hs', title='Saisir HS')


@crud_bp.route('/heures-sup/<int:hid>/approuver')
@_auth_required
def heures_sup_approuver(hid):
    if current_user.role not in ('admin', 'rh', 'chef'):
        flash("Droits insuffisants", "danger")
        return redirect('/heures-sup')
    conn = _db()
    c = conn.cursor()
    c.execute("""UPDATE heures_sup SET statut='Approuvé',
                 valide_par=?, date_validation=? WHERE id=?""",
              (current_user.id, datetime.now().isoformat(), hid))
    conn.commit()
    _log('HS_APPROUVE', f"Heures sup id={hid} approuvées")
    conn.close()
    flash("Heures sup approuvées", "success")
    return redirect('/heures-sup')


# ================================================================
# ==================== SITES / DEPARTEMENTS / POSTES ====================
# ================================================================
@crud_bp.route('/sites')
@_auth_required
def sites_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT s.*,
                 (SELECT COUNT(*) FROM employes WHERE site_id=s.id AND actif=1) AS nb_emp
                 FROM sites s WHERE s.actif=1 ORDER BY s.nom""")
    sites = c.fetchall()
    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-building"></i> Sites</h2>
        <div class="page-subtitle">{len(sites)} site(s)</div></div>
    </div>
    <div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Code</th><th>Nom</th><th>Ville</th><th>Téléphone</th><th>Employés</th></tr></thead>
      <tbody>"""
    for s in sites:
        content += f"""
        <tr>
          <td><strong>{s['code']}</strong></td>
          <td>{s['nom']}</td>
          <td>{s['ville'] or '-'}</td>
          <td>{s['telephone'] or '-'}</td>
          <td><span class="badge badge-primary">{s['nb_emp']}</span></td>
        </tr>"""
    content += "</tbody></table></div></div>"
    return _render(content, active='sites', title='Sites')


@crud_bp.route('/departements')
@_auth_required
def departements_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT d.*, s.nom AS site_nom,
                 (SELECT COUNT(*) FROM employes WHERE departement_id=d.id AND actif=1) AS nb_emp
                 FROM departements d
                 LEFT JOIN sites s ON d.site_id = s.id
                 WHERE d.actif=1 ORDER BY d.nom""")
    deps = c.fetchall()
    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-sitemap"></i> Départements</h2>
        <div class="page-subtitle">{len(deps)} département(s)</div></div>
    </div>
    <div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Code</th><th>Nom</th><th>Site</th><th>Employés</th></tr></thead>
      <tbody>"""
    for d in deps:
        content += f"""
        <tr>
          <td><strong>{d['code']}</strong></td>
          <td>{d['nom']}</td>
          <td>{d['site_nom'] or '-'}</td>
          <td><span class="badge badge-primary">{d['nb_emp']}</span></td>
        </tr>"""
    content += "</tbody></table></div></div>"
    return _render(content, active='departements', title='Départements')


# ================================================================
# ==================== TERMINAUX ====================
# ================================================================
@crud_bp.route('/terminaux')
@_auth_required
def terminaux_list():
    if current_user.role not in ('admin', 'rh'):
        flash("Accès réservé", "danger")
        return redirect('/')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT t.*, s.nom AS site_nom FROM terminaux t
                 LEFT JOIN sites s ON t.site_id = s.id
                 ORDER BY t.nom""")
    terminaux = c.fetchall()
    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-microchip"></i> Terminaux de pointage</h2>
        <div class="page-subtitle">{len(terminaux)} terminal(aux)</div></div>
    </div>
    <div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Code</th><th>Nom</th><th>Type</th><th>Site</th>
                 <th>IP</th><th>N° série</th><th>Statut</th></tr></thead>
      <tbody>"""
    for t in terminaux:
        badge = 'badge-success' if t['statut'] == 'Actif' else 'badge-warning'
        content += f"""
        <tr>
          <td><strong>{t['code']}</strong></td>
          <td>{t['nom']}</td>
          <td>{t['type'] or '-'}</td>
          <td>{t['site_nom'] or '-'}</td>
          <td><small>{t['adresse_ip'] or '-'}</small></td>
          <td><small>{t['numero_serie'] or '-'}</small></td>
          <td><span class="badge {badge}">{t['statut']}</span></td>
        </tr>"""
    content += "</tbody></table></div></div>"
    return _render(content, active='terminaux', title='Terminaux')


# ================================================================
# ==================== UTILISATEURS ====================
# ================================================================
@crud_bp.route('/utilisateurs')
@_auth_required
def utilisateurs_list():
    if current_user.role != 'admin':
        flash("Accès réservé admin", "danger")
        return redirect('/')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT u.*, e.nom AS emp_nom, e.prenom AS emp_prenom
                 FROM utilisateurs u
                 LEFT JOIN employes e ON u.employe_id = e.id
                 ORDER BY u.nom, u.prenom""")
    users = c.fetchall()
    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-user-shield"></i> Utilisateurs</h2>
        <div class="page-subtitle">{len(users)} utilisateur(s)</div></div>
      <a href="/utilisateurs/nouveau" class="btn btn-primary"><i class="fas fa-user-plus"></i> Nouveau</a>
    </div>
    <div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Username</th><th>Nom</th><th>Rôle</th>
                 <th>Employé lié</th><th>Actif</th><th>Dernier login</th></tr></thead>
      <tbody>"""
    for u in users:
        content += f"""
        <tr>
          <td><strong>{u['username']}</strong></td>
          <td>{u['prenom'] or ''} {u['nom'] or ''}</td>
          <td><span class="badge badge-role-{u['role']}">{u['role']}</span></td>
          <td><small>{u['emp_prenom'] or ''} {u['emp_nom'] or '-'}</small></td>
          <td>{'✅' if u['actif'] else '❌'}</td>
          <td><small>{u['dernier_login'][:16] if u['dernier_login'] else '-'}</small></td>
        </tr>"""
    content += "</tbody></table></div></div>"
    return _render(content, active='utilisateurs', title='Utilisateurs')


# ================================================================
# ==================== AUDIT ========================
# ================================================================
@crud_bp.route('/audit')
@_auth_required
def audit_list():
    if current_user.role != 'admin':
        flash("Accès réservé admin", "danger")
        return redirect('/')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT a.*, u.username, u.nom, u.prenom
                 FROM audit_log a
                 LEFT JOIN utilisateurs u ON a.user_id = u.id
                 ORDER BY a.created_at DESC LIMIT 200""")
    logs = c.fetchall()
    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-history"></i> Journal d'audit</h2>
        <div class="page-subtitle">{len(logs)} événement(s)</div></div>
    </div>
    <div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Date</th><th>Utilisateur</th><th>Action</th>
                 <th>Détails</th><th>IP</th></tr></thead>
      <tbody>"""
    for a in logs:
        content += f"""
        <tr>
          <td><small>{a['created_at'][:19]}</small></td>
          <td><strong>{a['username'] or '?'}</strong></td>
          <td><code>{a['action']}</code></td>
          <td><small>{(a['details'] or '')[:60]}</small></td>
          <td><small>{a['ip'] or '-'}</small></td>
        </tr>"""
    content += "</tbody></table></div></div>"
    return _render(content, active='audit', title='Audit')


# ================================================================
# ==================== API ====================
# ================================================================
@crud_bp.route('/api/stats')
@_auth_required
def api_stats():
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM employes WHERE actif=1")
    nb_emp = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM pointages WHERE date_pointage=date('now')")
    nb_point = c.fetchone()[0]
    conn.close()
    return jsonify(employes=nb_emp, pointages_jour=nb_point,
                   timestamp=datetime.now().isoformat())


@crud_bp.route('/api/employes')
@_auth_required
def api_employes():
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT id, matricule, nom, prenom FROM employes WHERE actif=1 ORDER BY nom")
    rows = c.fetchall()
    conn.close()
    return jsonify(employes=[dict(r) for r in rows])
