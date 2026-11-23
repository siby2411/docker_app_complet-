"""
Omega Transport V2 — CRUD complet
Véhicules · Chauffeurs · Lignes · Voyages · Utilisateurs · Maintenance
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


def _render(content, active='dashboard', title='Omega Transport'):
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
    return current_user and current_user.role in ('admin', 'directeur', 'chef_exploitation')


def _can_operate():
    return current_user and current_user.role in ('admin', 'directeur', 'chef_exploitation',
                                                   'guichetier', 'controleur', 'caissier')


def _fmt_fcfa(m):
    if not m:
        return "0 F"
    return f"{int(m):,} F".replace(",", " ")


def _fmt_km(km):
    if not km:
        return "0 km"
    return f"{int(km):,} km".replace(",", " ")


# ================================================================
# ==================== VEHICULES ====================
# ================================================================
@crud_bp.route('/vehicules')
@_auth_required
def vehicules_list():
    q = (request.args.get('q') or '').strip()
    statut = request.args.get('statut') or ''
    type_id = request.args.get('type') or ''

    conn = _db()
    c = conn.cursor()
    sql = """SELECT v.*, m.nom AS marque_nom,
                    t.nom AS type_nom, t.icone,
                    s.nom AS site_nom
             FROM vehicules v
             LEFT JOIN marques m ON v.marque_id = m.id
             LEFT JOIN types_vehicules t ON v.type_id = t.id
             LEFT JOIN sites s ON v.site_id = s.id
             WHERE v.actif=1"""
    params = []
    if q:
        sql += " AND (v.immatriculation LIKE ? OR v.modele LIKE ? OR v.vin LIKE ?)"
        params += [f"%{q}%"] * 3
    if statut:
        sql += " AND v.statut=?"
        params.append(statut)
    if type_id:
        sql += " AND v.type_id=?"
        params.append(type_id)
    sql += " ORDER BY v.immatriculation"
    c.execute(sql, params)
    vehicules = c.fetchall()

    c.execute("SELECT * FROM types_vehicules WHERE actif=1 ORDER BY nom")
    types = c.fetchall()
    conn.close()

    opt_type = '<option value="">Tous types</option>'
    for t in types:
        sel = 'selected' if str(t['id']) == type_id else ''
        opt_type += f'<option value="{t["id"]}" {sel}>{t["nom"]}</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-bus"></i> Véhicules</h2>
        <div class="page-subtitle">{len(vehicules)} véhicule(s) dans le parc</div></div>
      {'<a href="/vehicules/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau véhicule</a>' if _can_write() else ''}
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:2;margin:0;min-width:200px">
          <label>Recherche</label>
          <input type="text" name="q" value="{q}" placeholder="Immat, modèle, VIN...">
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Type</label>
          <select name="type">{opt_type}</select>
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Statut</label>
          <select name="statut">
            <option value="">Tous</option>
            <option value="Actif" {"selected" if statut=="Actif" else ""}>Actif</option>
            <option value="En maintenance" {"selected" if statut=="En maintenance" else ""}>En maintenance</option>
            <option value="Hors service" {"selected" if statut=="Hors service" else ""}>Hors service</option>
            <option value="Vendu" {"selected" if statut=="Vendu" else ""}>Vendu</option>
          </select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-search"></i> Filtrer</button>
        <a href="/vehicules" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Immatriculation</th><th>Marque / Modèle</th><th>Type</th>
          <th>Capacité</th><th>Km</th><th>Conso base</th>
          <th>Statut</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for v in vehicules:
        badge = 'badge-success'
        if v['statut'] == 'En maintenance': badge = 'badge-warning'
        elif v['statut'] == 'Hors service': badge = 'badge-danger'
        elif v['statut'] == 'Vendu': badge = 'badge-info'
        content += f"""
        <tr>
          <td>
            <div style="display:flex;align-items:center;gap:10px">
              <div style="width:36px;height:36px;background:linear-gradient(135deg,#0e7490,#06b6d4);border-radius:8px;display:flex;align-items:center;justify-content:center;color:white;font-size:1rem">
                <i class="fas {v['icone'] or 'fa-bus'}"></i>
              </div>
              <div>
                <strong>{v['immatriculation']}</strong>
                <div style="font-size:0.72rem;color:#94a3b8">{v['annee'] or '-'}</div>
              </div>
            </div>
          </td>
          <td>{v['marque_nom'] or '-'} <div style="font-size:0.75rem;color:#94a3b8">{v['modele'] or ''}</div></td>
          <td>{v['type_nom'] or '-'}</td>
          <td><span class="badge badge-primary">{v['capacite_places']} places</span></td>
          <td><small>{_fmt_km(v['kilometrage'])}</small></td>
          <td><small>{v['consommation_base'] or 0} L/100</small></td>
          <td><span class="badge {badge}">{v['statut']}</span></td>
          <td style="white-space:nowrap">
            <a href="/vehicules/{v['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
            {'<a href="/vehicules/'+str(v['id'])+'/modifier" class="btn btn-warning btn-sm"><i class="fas fa-pen"></i></a>' if _can_write() else ''}
          </td>
        </tr>"""
    if not vehicules:
        content += '<tr><td colspan="8" class="empty"><i class="fas fa-bus"></i><br>Aucun véhicule</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='vehicules', title='Véhicules')


@crud_bp.route('/vehicules/<int:vid>')
@_auth_required
def vehicules_detail(vid):
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT v.*, m.nom AS marque_nom, t.nom AS type_nom, t.icone,
                        s.nom AS site_nom,
                        (SELECT nom || ' ' || prenom FROM chauffeurs WHERE id=v.chauffeur_principal_id) AS chauffeur_principal
                 FROM vehicules v
                 LEFT JOIN marques m ON v.marque_id = m.id
                 LEFT JOIN types_vehicules t ON v.type_id = t.id
                 LEFT JOIN sites s ON v.site_id = s.id
                 WHERE v.id=?""", (vid,))
    v = c.fetchone()
    if not v:
        conn.close()
        flash("Véhicule introuvable", "danger")
        return redirect('/vehicules')

    # Documents
    c.execute("""SELECT * FROM documents_vehicules WHERE vehicule_id=?
                 ORDER BY date_expiration DESC""", (vid,))
    documents = c.fetchall()

    # Carburant récent
    c.execute("""SELECT * FROM carburant WHERE vehicule_id=?
                 ORDER BY date_bon DESC LIMIT 10""", (vid,))
    carburants = c.fetchall()

    # Maintenance
    c.execute("""SELECT * FROM maintenance WHERE vehicule_id=?
                 ORDER BY date_debut DESC LIMIT 10""", (vid,))
    maintenances = c.fetchall()

    # Voyages récents
    c.execute("""SELECT vo.*, l.code AS ligne_code, l.ville_depart, l.ville_arrivee
                 FROM voyages vo
                 LEFT JOIN lignes l ON vo.ligne_id = l.id
                 WHERE vo.vehicule_id=?
                 ORDER BY vo.date_voyage DESC LIMIT 10""", (vid,))
    voyages = c.fetchall()

    # Stats mois
    mois = datetime.now().strftime('%Y-%m')
    c.execute("""SELECT COUNT(*) AS nb,
                        COALESCE(SUM(recette_reelle), 0) AS ca,
                        COALESCE(SUM(places_vendues), 0) AS passagers
                 FROM voyages
                 WHERE vehicule_id=? AND strftime('%Y-%m', date_voyage)=?""",
              (vid, mois))
    stats_v = c.fetchone()

    # Consommation réelle
    c.execute("""SELECT COALESCE(SUM(litres), 0) AS litres,
                        COALESCE(SUM(montant_total), 0) AS cout,
                        COALESCE(AVG(ecart_pct), 0) AS ecart_moyen
                 FROM carburant
                 WHERE vehicule_id=? AND strftime('%Y-%m', date_bon)=?""",
              (vid, mois))
    stats_c = c.fetchone()

    # Coût maintenance mois
    c.execute("""SELECT COALESCE(SUM(cout_total), 0) AS cout
                 FROM maintenance
                 WHERE vehicule_id=? AND strftime('%Y-%m', date_debut)=?""",
              (vid, mois))
    cout_maint = c.fetchone()['cout']

    conn.close()

    badge = 'badge-success'
    if v['statut'] == 'En maintenance': badge = 'badge-warning'
    elif v['statut'] == 'Hors service': badge = 'badge-danger'

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-bus"></i> {v['immatriculation']}</h2>
        <div class="page-subtitle">
          {v['marque_nom'] or ''} {v['modele'] or ''} ({v['annee'] or '-'}) ·
          <span class="badge {badge}">{v['statut']}</span>
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/vehicules" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        {'<a href="/vehicules/'+str(vid)+'/modifier" class="btn btn-warning"><i class="fas fa-pen"></i> Modifier</a>' if _can_write() else ''}
      </div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-route"></i></div>
        <div class="stat-value">{stats_v['nb']}</div>
        <div class="stat-label">Voyages ce mois</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-money-bill-wave"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(stats_v['ca'])}</div>
        <div class="stat-label">CA ce mois</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-users"></i></div>
        <div class="stat-value">{stats_v['passagers']}</div>
        <div class="stat-label">Passagers</div></div>
      <div class="stat-card purple"><div class="stat-icon"><i class="fas fa-gas-pump"></i></div>
        <div class="stat-value">{stats_c['litres']:.0f}L</div>
        <div class="stat-label">Carburant</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations techniques</h3></div>
      <div class="form-grid">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Immatriculation</label>
             <div style="font-weight:700">{v['immatriculation']}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">VIN</label>
             <div style="font-family:monospace">{v['vin'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Marque / Modèle</label>
             <div>{v['marque_nom'] or ''} {v['modele'] or ''}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Année</label>
             <div>{v['annee'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Capacité</label>
             <div>{v['capacite_places']} places assises</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Carburant</label>
             <div>{v['carburant_type'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Kilométrage</label>
             <div>{_fmt_km(v['kilometrage'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Conso. base</label>
             <div>{v['consommation_base']} L/100 km</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Site</label>
             <div>{v['site_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Chauffeur principal</label>
             <div>{v['chauffeur_principal'] or '-'}</div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-file-alt"></i> Documents</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Type</th><th>Numéro</th><th>Émission</th><th>Expiration</th><th>Statut</th></tr></thead>
        <tbody>"""
    for d in documents:
        jours = 0
        try:
            exp = datetime.fromisoformat(d['date_expiration']) if d['date_expiration'] else None
            jours = (exp - datetime.now()).days if exp else 9999
        except:
            pass
        if jours < 0:
            badge_d = 'badge-danger'
            label = f'Expiré ({abs(jours)}j)'
        elif jours < 30:
            badge_d = 'badge-warning'
            label = f'Expire dans {jours}j'
        else:
            badge_d = 'badge-success'
            label = f'Valide ({jours}j)'
        content += f"""
        <tr>
          <td><strong>{d['type_document']}</strong></td>
          <td><small>{d['numero'] or '-'}</small></td>
          <td>{d['date_emission'] or '-'}</td>
          <td>{d['date_expiration'] or '-'}</td>
          <td><span class="badge {badge_d}">{label}</span></td>
        </tr>"""
    if not documents:
        content += '<tr><td colspan="5" class="empty">Aucun document</td></tr>'
    content += "</tbody></table></div></div>"

    # Carburant
    content += """
    <div class="card">
      <div class="card-header"><h3><i class="fas fa-gas-pump"></i> Carburant (10 derniers)</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Date</th><th>Litres</th><th>Montant</th>
                   <th>Conso réelle</th><th>Théorique</th><th>Écart</th></tr></thead>
        <tbody>"""
    for cb in carburants:
        badge_c = 'badge-danger' if cb['statut'] == 'Anomalie' else 'badge-success'
        content += f"""
        <tr>
          <td>{cb['date_bon']}</td>
          <td>{cb['litres']} L</td>
          <td>{_fmt_fcfa(cb['montant_total'])}</td>
          <td>{cb['consommation_calculee'] or '-'} L/100</td>
          <td>{cb['consommation_theorique'] or '-'} L/100</td>
          <td><span class="badge {badge_c}">{cb['ecart_pct'] or 0:+.1f}%</span></td>
        </tr>"""
    if not carburants:
        content += '<tr><td colspan="6" class="empty">Aucun bon carburant</td></tr>'
    content += "</tbody></table></div></div>"

    # Maintenance
    content += """
    <div class="card">
      <div class="card-header"><h3><i class="fas fa-wrench"></i> Maintenance (10 dernières)</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Date</th><th>Type</th><th>Description</th>
                   <th>Coût</th><th>Statut</th></tr></thead>
        <tbody>"""
    for m in maintenances:
        content += f"""
        <tr>
          <td>{m['date_debut']}</td>
          <td>{m['type_maintenance'] or '-'}</td>
          <td><small>{m['description'][:50]}</small></td>
          <td>{_fmt_fcfa(m['cout_total'])}</td>
          <td><span class="badge badge-info">{m['statut']}</span></td>
        </tr>"""
    if not maintenances:
        content += '<tr><td colspan="5" class="empty">Aucune maintenance</td></tr>'
    content += "</tbody></table></div></div>"

    # Voyages
    content += """
    <div class="card">
      <div class="card-header"><h3><i class="fas fa-calendar-check"></i> Voyages (10 derniers)</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Date</th><th>Ligne</th><th>Départ</th>
                   <th>Places</th><th>Recette</th><th>Statut</th></tr></thead>
        <tbody>"""
    for vv in voyages:
        content += f"""
        <tr>
          <td>{vv['date_voyage']}</td>
          <td><strong>{vv['ligne_code'] or '-'}</strong></td>
          <td><small>{vv['ville_depart']} → {vv['ville_arrivee']}</small></td>
          <td>{vv['places_vendues']}/{vv['places_totales']}</td>
          <td>{_fmt_fcfa(vv['recette_reelle'])}</td>
          <td><span class="badge badge-info">{vv['statut']}</span></td>
        </tr>"""
    if not voyages:
        content += '<tr><td colspan="6" class="empty">Aucun voyage</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='vehicules', title=v['immatriculation'])


@crud_bp.route('/vehicules/nouveau', methods=['GET', 'POST'])
@_auth_required
def vehicules_new():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/vehicules')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        immat = (request.form.get('immatriculation') or '').strip().upper()
        if not immat:
            flash("Immatriculation obligatoire", "warning")
        else:
            try:
                c.execute("""INSERT INTO vehicules
                    (immatriculation, marque_id, modele, type_id, annee, vin, couleur,
                     capacite_places, carburant_type, consommation_base, kilometrage,
                     date_acquisition, prix_acquisition, site_id, statut, actif, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)""",
                    (immat,
                     request.form.get('marque_id') or None,
                     (request.form.get('modele') or '').strip(),
                     request.form.get('type_id') or None,
                     int(request.form.get('annee') or 0) or None,
                     (request.form.get('vin') or '').strip(),
                     (request.form.get('couleur') or '').strip(),
                     int(request.form.get('capacite_places') or 0),
                     request.form.get('carburant_type') or 'Diesel',
                     float(request.form.get('consommation_base') or 0),
                     int(request.form.get('kilometrage') or 0),
                     request.form.get('date_acquisition') or None,
                     int(request.form.get('prix_acquisition') or 0) or None,
                     request.form.get('site_id') or None,
                     request.form.get('statut') or 'Actif',
                     datetime.now().isoformat(), datetime.now().isoformat()))
                new_id = c.lastrowid
                conn.commit()
                _log('CREATE_VEHICULE', f"Véhicule {immat} créé", entity='vehicule', entity_id=new_id)
                flash(f"Véhicule '{immat}' créé", "success")
                conn.close()
                return redirect(f'/vehicules/{new_id}')
            except sqlite3.IntegrityError:
                flash("Cette immatriculation existe déjà", "danger")
            except Exception as e:
                flash(f"Erreur : {e}", "danger")

    c.execute("SELECT * FROM marques WHERE actif=1 ORDER BY nom")
    marques = c.fetchall()
    c.execute("SELECT * FROM types_vehicules WHERE actif=1 ORDER BY nom")
    types = c.fetchall()
    c.execute("SELECT * FROM sites WHERE actif=1 ORDER BY nom")
    sites = c.fetchall()
    conn.close()

    opt_m = ''.join(f'<option value="{m["id"]}">{m["nom"]}</option>' for m in marques)
    opt_t = ''.join(f'<option value="{t["id"]}">{t["nom"]}</option>' for t in types)
    opt_s = ''.join(f'<option value="{s["id"]}">{s["nom"]}</option>' for s in sites)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus"></i> Nouveau véhicule</h2></div>
      <a href="/vehicules" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group"><label>Immatriculation *</label>
            <input type="text" name="immatriculation" required placeholder="DK-1234-AB"></div>
          <div class="form-group"><label>VIN</label>
            <input type="text" name="vin" placeholder="17 caractères"></div>
          <div class="form-group"><label>Marque</label>
            <select name="marque_id"><option value="">—</option>{opt_m}</select></div>
          <div class="form-group"><label>Modèle</label>
            <input type="text" name="modele" placeholder="Coaster, Sprinter..."></div>
          <div class="form-group"><label>Type</label>
            <select name="type_id"><option value="">—</option>{opt_t}</select></div>
          <div class="form-group"><label>Année</label>
            <input type="number" name="annee" min="1990" max="2030" value="{datetime.now().year}"></div>
          <div class="form-group"><label>Couleur</label>
            <input type="text" name="couleur"></div>
          <div class="form-group"><label>Capacité places *</label>
            <input type="number" name="capacite_places" required value="30"></div>
          <div class="form-group"><label>Carburant</label>
            <select name="carburant_type">
              <option>Diesel</option><option>Essence</option><option>Hybride</option><option>Électrique</option>
            </select></div>
          <div class="form-group"><label>Consommation base (L/100km)</label>
            <input type="number" step="0.1" name="consommation_base" value="22.0"></div>
          <div class="form-group"><label>Kilométrage actuel</label>
            <input type="number" name="kilometrage" value="0"></div>
          <div class="form-group"><label>Date acquisition</label>
            <input type="date" name="date_acquisition" value="{datetime.now().date().isoformat()}"></div>
          <div class="form-group"><label>Prix acquisition (FCFA)</label>
            <input type="number" name="prix_acquisition" value="0"></div>
          <div class="form-group"><label>Site</label>
            <select name="site_id"><option value="">—</option>{opt_s}</select></div>
          <div class="form-group"><label>Statut</label>
            <select name="statut">
              <option>Actif</option><option>En maintenance</option><option>Hors service</option>
            </select></div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Créer</button>
          <a href="/vehicules" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='vehicules', title='Nouveau véhicule')


@crud_bp.route('/vehicules/<int:vid>/modifier', methods=['GET', 'POST'])
@_auth_required
def vehicules_edit(vid):
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/vehicules')
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM vehicules WHERE id=?", (vid,))
    v = c.fetchone()
    if not v:
        conn.close()
        flash("Introuvable", "danger")
        return redirect('/vehicules')

    if request.method == 'POST':
        c.execute("""UPDATE vehicules SET
            marque_id=?, modele=?, type_id=?, annee=?, vin=?, couleur=?,
            capacite_places=?, carburant_type=?, consommation_base=?, kilometrage=?,
            date_acquisition=?, prix_acquisition=?, site_id=?, statut=?, updated_at=?
            WHERE id=?""",
            (request.form.get('marque_id') or None,
             (request.form.get('modele') or '').strip(),
             request.form.get('type_id') or None,
             int(request.form.get('annee') or 0) or None,
             (request.form.get('vin') or '').strip(),
             (request.form.get('couleur') or '').strip(),
             int(request.form.get('capacite_places') or 0),
             request.form.get('carburant_type') or 'Diesel',
             float(request.form.get('consommation_base') or 0),
             int(request.form.get('kilometrage') or 0),
             request.form.get('date_acquisition') or None,
             int(request.form.get('prix_acquisition') or 0) or None,
             request.form.get('site_id') or None,
             request.form.get('statut') or 'Actif',
             datetime.now().isoformat(), vid))
        conn.commit()
        _log('UPDATE_VEHICULE', f"Véhicule id={vid} modifié", entity='vehicule', entity_id=vid)
        conn.close()
        flash("Véhicule mis à jour", "success")
        return redirect(f'/vehicules/{vid}')

    c.execute("SELECT * FROM marques WHERE actif=1 ORDER BY nom")
    marques = c.fetchall()
    c.execute("SELECT * FROM types_vehicules WHERE actif=1 ORDER BY nom")
    types = c.fetchall()
    c.execute("SELECT * FROM sites WHERE actif=1 ORDER BY nom")
    sites = c.fetchall()
    conn.close()

    def opt(items, cur):
        return ''.join(f'<option value="{i["id"]}" {"selected" if cur==i["id"] else ""}>{i["nom"]}</option>' for i in items)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-pen"></i> Modifier véhicule</h2></div>
      <a href="/vehicules/{vid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group"><label>Marque</label>
            <select name="marque_id"><option value="">—</option>{opt(marques, v['marque_id'])}</select></div>
          <div class="form-group"><label>Modèle</label>
            <input type="text" name="modele" value="{v['modele'] or ''}"></div>
          <div class="form-group"><label>Type</label>
            <select name="type_id"><option value="">—</option>{opt(types, v['type_id'])}</select></div>
          <div class="form-group"><label>Année</label>
            <input type="number" name="annee" value="{v['annee'] or ''}"></div>
          <div class="form-group"><label>VIN</label>
            <input type="text" name="vin" value="{v['vin'] or ''}"></div>
          <div class="form-group"><label>Couleur</label>
            <input type="text" name="couleur" value="{v['couleur'] or ''}"></div>
          <div class="form-group"><label>Capacité</label>
            <input type="number" name="capacite_places" value="{v['capacite_places'] or 0}"></div>
          <div class="form-group"><label>Conso base</label>
            <input type="number" step="0.1" name="consommation_base" value="{v['consommation_base'] or 0}"></div>
          <div class="form-group"><label>Kilométrage</label>
            <input type="number" name="kilometrage" value="{v['kilometrage'] or 0}"></div>
          <div class="form-group"><label>Site</label>
            <select name="site_id"><option value="">—</option>{opt(sites, v['site_id'])}</select></div>
          <div class="form-group"><label>Statut</label>
            <select name="statut">
              <option value="Actif" {"selected" if v['statut']=='Actif' else ''}>Actif</option>
              <option value="En maintenance" {"selected" if v['statut']=='En maintenance' else ''}>En maintenance</option>
              <option value="Hors service" {"selected" if v['statut']=='Hors service' else ''}>Hors service</option>
              <option value="Vendu" {"selected" if v['statut']=='Vendu' else ''}>Vendu</option>
            </select></div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
          <a href="/vehicules/{vid}" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='vehicules', title='Modifier véhicule')


# ================================================================
# ==================== CHAUFFEURS ====================
# ================================================================
@crud_bp.route('/chauffeurs')
@_auth_required
def chauffeurs_list():
    q = (request.args.get('q') or '').strip()

    conn = _db()
    c = conn.cursor()
    sql = """SELECT ch.*,
                    s.nom AS site_nom,
                    (SELECT immatriculation FROM vehicules WHERE chauffeur_principal_id=ch.id LIMIT 1) AS vehicule_immat
             FROM chauffeurs ch
             LEFT JOIN sites s ON ch.site_id = s.id
             WHERE ch.actif=1"""
    params = []
    if q:
        sql += " AND (ch.nom LIKE ? OR ch.prenom LIKE ? OR ch.matricule LIKE ? OR ch.telephone LIKE ?)"
        params += [f"%{q}%"] * 4
    sql += " ORDER BY ch.nom, ch.prenom"
    c.execute(sql, params)
    chauffeurs = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-id-card"></i> Chauffeurs</h2>
        <div class="page-subtitle">{len(chauffeurs)} chauffeur(s)</div></div>
      {'<a href="/chauffeurs/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau chauffeur</a>' if _can_write() else ''}
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px">
        <input type="text" name="q" value="{q}" placeholder="Nom, matricule, téléphone..."
               style="flex:1;padding:12px 15px;border:2px solid #f1f5f9;border-radius:11px">
        <button class="btn btn-primary"><i class="fas fa-search"></i></button>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Matricule</th><th>Nom complet</th><th>Téléphone</th>
          <th>Permis</th><th>Expiration</th><th>Véhicule</th>
          <th>Statut</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for ch in chauffeurs:
        jours_permis = 0
        try:
            exp = datetime.fromisoformat(ch['date_expiration_permis']) if ch['date_expiration_permis'] else None
            jours_permis = (exp - datetime.now()).days if exp else 9999
        except:
            pass
        if jours_permis < 0:
            badge_p = 'badge-danger'
            label_p = 'Expiré'
        elif jours_permis < 60:
            badge_p = 'badge-warning'
            label_p = f'{jours_permis}j'
        else:
            badge_p = 'badge-success'
            label_p = 'OK'

        statut_badge = 'badge-success' if ch['statut'] == 'Disponible' else 'badge-warning'

        content += f"""
        <tr>
          <td><strong>{ch['matricule']}</strong></td>
          <td>
            <div style="font-weight:700">{ch['prenom']} {ch['nom']}</div>
            <div style="font-size:0.72rem;color:#94a3b8">{ch['experience_annees']} ans exp.</div>
          </td>
          <td>{ch['telephone'] or '-'}</td>
          <td><span class="badge badge-primary">{ch['categorie_permis'] or '-'}</span></td>
          <td><span class="badge {badge_p}">{label_p}</span></td>
          <td><small>{ch['vehicule_immat'] or '-'}</small></td>
          <td><span class="badge {statut_badge}">{ch['statut']}</span></td>
          <td style="white-space:nowrap">
            <a href="/chauffeurs/{ch['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
            {'<a href="/chauffeurs/'+str(ch['id'])+'/modifier" class="btn btn-warning btn-sm"><i class="fas fa-pen"></i></a>' if _can_write() else ''}
          </td>
        </tr>"""
    if not chauffeurs:
        content += '<tr><td colspan="8" class="empty"><i class="fas fa-id-card"></i><br>Aucun chauffeur</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='chauffeurs', title='Chauffeurs')


@crud_bp.route('/chauffeurs/<int:cid>')
@_auth_required
def chauffeurs_detail(cid):
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT ch.*, s.nom AS site_nom
                 FROM chauffeurs ch
                 LEFT JOIN sites s ON ch.site_id = s.id
                 WHERE ch.id=?""", (cid,))
    ch = c.fetchone()
    if not ch:
        conn.close()
        flash("Chauffeur introuvable", "danger")
        return redirect('/chauffeurs')

    # Visites médicales
    c.execute("""SELECT * FROM visites_medicales WHERE chauffeur_id=?
                 ORDER BY date_visite DESC LIMIT 5""", (cid,))
    visites = c.fetchall()

    # Voyages récents
    c.execute("""SELECT vo.*, l.code AS ligne_code, l.ville_depart, l.ville_arrivee
                 FROM voyages vo
                 LEFT JOIN lignes l ON vo.ligne_id = l.id
                 WHERE vo.chauffeur_id=?
                 ORDER BY vo.date_voyage DESC LIMIT 10""", (cid,))
    voyages = c.fetchall()

    # Sanctions
    c.execute("""SELECT * FROM sanctions WHERE chauffeur_id=?
                 ORDER BY date_sanction DESC LIMIT 5""", (cid,))
    sanctions = c.fetchall()

    # Amendes
    c.execute("""SELECT * FROM amendes WHERE chauffeur_id=?
                 ORDER BY date_amende DESC LIMIT 5""", (cid,))
    amendes = c.fetchall()

    # Stats mois
    mois = datetime.now().strftime('%Y-%m')
    c.execute("""SELECT COUNT(*) AS nb,
                        COALESCE(SUM(recette_reelle), 0) AS ca,
                        COALESCE(SUM(places_vendues), 0) AS passagers
                 FROM voyages
                 WHERE chauffeur_id=? AND strftime('%Y-%m', date_voyage)=?""",
              (cid, mois))
    stats = c.fetchone()

    conn.close()

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-id-card"></i> {ch['prenom']} {ch['nom']}</h2>
        <div class="page-subtitle">
          <strong>{ch['matricule']}</strong> · Permis {ch['categorie_permis'] or '-'} ·
          {ch['experience_annees']} ans d'expérience
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/chauffeurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        {'<a href="/chauffeurs/'+str(cid)+'/modifier" class="btn btn-warning"><i class="fas fa-pen"></i> Modifier</a>' if _can_write() else ''}
      </div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-route"></i></div>
        <div class="stat-value">{stats['nb']}</div>
        <div class="stat-label">Voyages ce mois</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-money-bill-wave"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(stats['ca'])}</div>
        <div class="stat-label">Recettes générées</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-users"></i></div>
        <div class="stat-value">{stats['passagers']}</div>
        <div class="stat-label">Passagers</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-gavel"></i></div>
        <div class="stat-value">{len(amendes)}</div>
        <div class="stat-label">Amendes</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
      <div class="form-grid">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Matricule</label>
             <div style="font-weight:700">{ch['matricule']}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Téléphone</label>
             <div>{ch['telephone'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">CNI</label>
             <div>{ch['numero_cni'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">N° Permis</label>
             <div>{ch['numero_permis'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Catégorie permis</label>
             <div>{ch['categorie_permis'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Expiration permis</label>
             <div>{ch['date_expiration_permis'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Site</label>
             <div>{ch['site_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Statut</label>
             <div><span class="badge badge-success">{ch['statut']}</span></div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-heart-pulse"></i> Visites médicales</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Date</th><th>Prochaine</th><th>Médecin</th><th>Résultat</th></tr></thead>
        <tbody>"""
    for v in visites:
        badge_v = 'badge-success' if v['resultat'] == 'Apte' else 'badge-warning'
        content += f"""
        <tr>
          <td>{v['date_visite']}</td>
          <td>{v['date_prochaine'] or '-'}</td>
          <td>{v['medecin'] or '-'}</td>
          <td><span class="badge {badge_v}">{v['resultat']}</span></td>
        </tr>"""
    if not visites:
        content += '<tr><td colspan="4" class="empty">Aucune visite</td></tr>'
    content += "</tbody></table></div></div>"

    # Voyages
    content += """
    <div class="card">
      <div class="card-header"><h3><i class="fas fa-calendar-check"></i> Voyages récents</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Date</th><th>Ligne</th><th>Trajet</th>
                   <th>Places</th><th>Recette</th><th>Statut</th></tr></thead>
        <tbody>"""
    for vv in voyages:
        content += f"""
        <tr>
          <td>{vv['date_voyage']}</td>
          <td><strong>{vv['ligne_code'] or '-'}</strong></td>
          <td><small>{vv['ville_depart']} → {vv['ville_arrivee']}</small></td>
          <td>{vv['places_vendues']}/{vv['places_totales']}</td>
          <td>{_fmt_fcfa(vv['recette_reelle'])}</td>
          <td><span class="badge badge-info">{vv['statut']}</span></td>
        </tr>"""
    if not voyages:
        content += '<tr><td colspan="6" class="empty">Aucun voyage</td></tr>'
    content += "</tbody></table></div></div>"

    # Amendes
    if amendes:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-gavel"></i> Amendes</h3></div>
          <div class="table-wrap"><table>
            <thead><tr><th>Date</th><th>Motif</th><th>Montant</th><th>Statut</th></tr></thead>
            <tbody>"""
        for a in amendes:
            badge_a = 'badge-danger' if a['statut'] == 'À payer' else 'badge-success'
            content += f"""
            <tr>
              <td>{a['date_amende']}</td>
              <td>{a['motif']}</td>
              <td>{_fmt_fcfa(a['montant'])}</td>
              <td><span class="badge {badge_a}">{a['statut']}</span></td>
            </tr>"""
        content += "</tbody></table></div></div>"

    return _render(content, active='chauffeurs', title=ch['prenom'] + ' ' + ch['nom'])


@crud_bp.route('/chauffeurs/nouveau', methods=['GET', 'POST'])
@_auth_required
def chauffeurs_new():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/chauffeurs')
    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        nom = (request.form.get('nom') or '').strip()
        prenom = (request.form.get('prenom') or '').strip()
        if not nom or not prenom:
            flash("Nom et prénom obligatoires", "warning")
        else:
            c.execute("SELECT COUNT(*) FROM chauffeurs")
            n = (c.fetchone()[0] or 0) + 1
            matricule = f"CHA{n:04d}"

            try:
                c.execute("""INSERT INTO chauffeurs
                    (matricule, nom, prenom, telephone, date_naissance, adresse,
                     numero_cni, numero_cnss, numero_permis, categorie_permis,
                     date_permis, date_expiration_permis, experience_annees,
                     site_id, statut, actif, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)""",
                    (matricule, nom, prenom,
                     (request.form.get('telephone') or '').strip(),
                     request.form.get('date_naissance') or None,
                     (request.form.get('adresse') or '').strip(),
                     (request.form.get('numero_cni') or '').strip(),
                     (request.form.get('numero_cnss') or '').strip(),
                     (request.form.get('numero_permis') or '').strip(),
                     request.form.get('categorie_permis') or 'D',
                     request.form.get('date_permis') or None,
                     request.form.get('date_expiration_permis') or None,
                     int(request.form.get('experience_annees') or 0),
                     request.form.get('site_id') or None,
                     'Disponible',
                     datetime.now().isoformat(), datetime.now().isoformat()))
                new_id = c.lastrowid
                conn.commit()
                _log('CREATE_CHAUFFEUR', f"Chauffeur {prenom} {nom} créé", entity='chauffeur', entity_id=new_id)
                flash(f"Chauffeur '{prenom} {nom}' créé", "success")
                conn.close()
                return redirect(f'/chauffeurs/{new_id}')
            except Exception as e:
                flash(f"Erreur : {e}", "danger")

    c.execute("SELECT * FROM sites WHERE actif=1 ORDER BY nom")
    sites = c.fetchall()
    conn.close()
    opt_s = ''.join(f'<option value="{s["id"]}">{s["nom"]}</option>' for s in sites)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus"></i> Nouveau chauffeur</h2></div>
      <a href="/chauffeurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card"><form method="POST">
      <div class="form-grid">
        <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
        <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" required></div>
        <div class="form-group"><label>Téléphone</label><input type="text" name="telephone"></div>
        <div class="form-group"><label>Date naissance</label><input type="date" name="date_naissance"></div>
        <div class="form-group"><label>N° CNI</label><input type="text" name="numero_cni"></div>
        <div class="form-group"><label>N° CNSS</label><input type="text" name="numero_cnss"></div>
        <div class="form-group"><label>N° Permis</label><input type="text" name="numero_permis"></div>
        <div class="form-group"><label>Catégorie permis</label>
          <select name="categorie_permis">
            <option>A</option><option>B</option><option>C</option><option value="D" selected>D</option><option>E</option>
          </select>
        </div>
        <div class="form-group"><label>Date permis</label><input type="date" name="date_permis"></div>
        <div class="form-group"><label>Expiration permis</label><input type="date" name="date_expiration_permis"></div>
        <div class="form-group"><label>Années d'expérience</label><input type="number" name="experience_annees" value="0"></div>
        <div class="form-group"><label>Site</label><select name="site_id"><option value="">—</option>{opt_s}</select></div>
        <div class="form-group form-full"><label>Adresse</label><textarea name="adresse" rows="2"></textarea></div>
      </div>
      <button class="btn btn-primary" style="margin-top:20px"><i class="fas fa-check"></i> Créer</button>
    </form></div>"""
    return _render(content, active='chauffeurs', title='Nouveau chauffeur')


@crud_bp.route('/chauffeurs/<int:cid>/modifier', methods=['GET', 'POST'])
@_auth_required
def chauffeurs_edit(cid):
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/chauffeurs')
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM chauffeurs WHERE id=?", (cid,))
    ch = c.fetchone()
    if not ch:
        conn.close()
        return redirect('/chauffeurs')

    if request.method == 'POST':
        c.execute("""UPDATE chauffeurs SET
            nom=?, prenom=?, telephone=?, date_naissance=?, adresse=?,
            numero_cni=?, numero_cnss=?, numero_permis=?, categorie_permis=?,
            date_permis=?, date_expiration_permis=?, experience_annees=?,
            site_id=?, statut=?, updated_at=?
            WHERE id=?""",
            ((request.form.get('nom') or '').strip(),
             (request.form.get('prenom') or '').strip(),
             (request.form.get('telephone') or '').strip(),
             request.form.get('date_naissance') or None,
             (request.form.get('adresse') or '').strip(),
             (request.form.get('numero_cni') or '').strip(),
             (request.form.get('numero_cnss') or '').strip(),
             (request.form.get('numero_permis') or '').strip(),
             request.form.get('categorie_permis') or 'D',
             request.form.get('date_permis') or None,
             request.form.get('date_expiration_permis') or None,
             int(request.form.get('experience_annees') or 0),
             request.form.get('site_id') or None,
             request.form.get('statut') or 'Disponible',
             datetime.now().isoformat(), cid))
        conn.commit()
        _log('UPDATE_CHAUFFEUR', f"Chauffeur id={cid} modifié", entity='chauffeur', entity_id=cid)
        conn.close()
        flash("Chauffeur mis à jour", "success")
        return redirect(f'/chauffeurs/{cid}')

    c.execute("SELECT * FROM sites WHERE actif=1 ORDER BY nom")
    sites = c.fetchall()
    conn.close()
    def opt(items, cur):
        return ''.join(f'<option value="{i["id"]}" {"selected" if cur==i["id"] else ""}>{i["nom"]}</option>' for i in items)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-pen"></i> Modifier chauffeur</h2></div>
      <a href="/chauffeurs/{cid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card"><form method="POST">
      <div class="form-grid">
        <div class="form-group"><label>Nom</label><input type="text" name="nom" value="{ch['nom']}" required></div>
        <div class="form-group"><label>Prénom</label><input type="text" name="prenom" value="{ch['prenom']}" required></div>
        <div class="form-group"><label>Téléphone</label><input type="text" name="telephone" value="{ch['telephone'] or ''}"></div>
        <div class="form-group"><label>N° Permis</label><input type="text" name="numero_permis" value="{ch['numero_permis'] or ''}"></div>
        <div class="form-group"><label>Catégorie</label>
          <select name="categorie_permis">
            {''.join(f'<option value="{c_}" {"selected" if ch["categorie_permis"]==c_ else ""}>{c_}</option>' for c_ in ['A','B','C','D','E'])}
          </select></div>
        <div class="form-group"><label>Expiration permis</label>
          <input type="date" name="date_expiration_permis" value="{ch['date_expiration_permis'] or ''}"></div>
        <div class="form-group"><label>Expérience (ans)</label>
          <input type="number" name="experience_annees" value="{ch['experience_annees'] or 0}"></div>
        <div class="form-group"><label>Site</label>
          <select name="site_id"><option value="">—</option>{opt(sites, ch['site_id'])}</select></div>
        <div class="form-group"><label>Statut</label>
          <select name="statut">
            <option value="Disponible" {"selected" if ch['statut']=='Disponible' else ''}>Disponible</option>
            <option value="En mission" {"selected" if ch['statut']=='En mission' else ''}>En mission</option>
            <option value="Congé" {"selected" if ch['statut']=='Congé' else ''}>Congé</option>
            <option value="Inactif" {"selected" if ch['statut']=='Inactif' else ''}>Inactif</option>
          </select></div>
        <div class="form-group form-full"><label>Adresse</label>
          <textarea name="adresse" rows="2">{ch['adresse'] or ''}</textarea></div>
      </div>
      <button class="btn btn-primary" style="margin-top:20px"><i class="fas fa-check"></i> Enregistrer</button>
    </form></div>"""
    return _render(content, active='chauffeurs', title='Modifier chauffeur')


# ================================================================
# ==================== LIGNES ====================
# ================================================================
@crud_bp.route('/lignes')
@_auth_required
def lignes_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT l.*,
                 (SELECT COUNT(*) FROM voyages WHERE ligne_id=l.id) AS nb_voyages,
                 (SELECT COUNT(*) FROM horaires WHERE ligne_id=l.id) AS nb_horaires
                 FROM lignes l WHERE l.actif=1 ORDER BY l.code""")
    lignes = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-route"></i> Lignes / Itinéraires</h2>
        <div class="page-subtitle">{len(lignes)} ligne(s) active(s)</div></div>
      {'<a href="/lignes/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle ligne</a>' if _can_write() else ''}
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Code</th><th>Trajet</th><th>Distance</th><th>Durée</th>
          <th>Tarif base</th><th>Voyages</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for l in lignes:
        content += f"""
        <tr>
          <td><strong>{l['code']}</strong></td>
          <td>
            <div style="font-weight:700">{l['ville_depart']} → {l['ville_arrivee']}</div>
            <div style="font-size:0.72rem;color:#94a3b8">{l['nom']}</div>
          </td>
          <td>{l['distance_km']} km</td>
          <td>{l['duree_minutes']} min</td>
          <td><strong>{_fmt_fcfa(l['tarif_base'])}</strong></td>
          <td><span class="badge badge-primary">{l['nb_voyages']}</span></td>
          <td>
            <a href="/lignes/{l['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
          </td>
        </tr>"""
    if not lignes:
        content += '<tr><td colspan="7" class="empty"><i class="fas fa-route"></i><br>Aucune ligne</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='lignes', title='Lignes')


@crud_bp.route('/lignes/<int:lid>')
@_auth_required
def lignes_detail(lid):
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM lignes WHERE id=?", (lid,))
    ligne = c.fetchone()
    if not ligne:
        conn.close()
        return redirect('/lignes')

    c.execute("SELECT * FROM horaires WHERE ligne_id=? ORDER BY heure_depart", (lid,))
    horaires = c.fetchall()

    c.execute("""SELECT vo.*, v.immatriculation, ch.nom AS ch_nom, ch.prenom AS ch_prenom
                 FROM voyages vo
                 LEFT JOIN vehicules v ON vo.vehicule_id = v.id
                 LEFT JOIN chauffeurs ch ON vo.chauffeur_id = ch.id
                 WHERE vo.ligne_id=?
                 ORDER BY vo.date_voyage DESC LIMIT 15""", (lid,))
    voyages = c.fetchall()

    # Stats
    mois = datetime.now().strftime('%Y-%m')
    c.execute("""SELECT COUNT(*) AS nb,
                        COALESCE(SUM(recette_reelle), 0) AS ca,
                        COALESCE(SUM(places_vendues), 0) AS passagers,
                        COALESCE(AVG(places_vendues * 100.0 / NULLIF(places_totales, 0)), 0) AS taux
                 FROM voyages
                 WHERE ligne_id=? AND strftime('%Y-%m', date_voyage)=?""",
              (lid, mois))
    stats = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-route"></i> {ligne['code']}</h2>
        <div class="page-subtitle">{ligne['ville_depart']} → {ligne['ville_arrivee']} · {ligne['distance_km']} km</div>
      </div>
      <a href="/lignes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-calendar-check"></i></div>
        <div class="stat-value">{stats['nb']}</div>
        <div class="stat-label">Voyages ce mois</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-money-bill-wave"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(stats['ca'])}</div>
        <div class="stat-label">CA ce mois</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-users"></i></div>
        <div class="stat-value">{stats['passagers']}</div>
        <div class="stat-label">Passagers</div></div>
      <div class="stat-card purple"><div class="stat-icon"><i class="fas fa-percent"></i></div>
        <div class="stat-value">{stats['taux']:.1f}%</div>
        <div class="stat-label">Taux remplissage</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Détails</h3></div>
      <div class="form-grid">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Code</label>
             <div style="font-weight:700">{ligne['code']}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Distance</label>
             <div>{ligne['distance_km']} km</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Durée</label>
             <div>{ligne['duree_minutes']} minutes</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Tarif 2ème</label>
             <div>{_fmt_fcfa(ligne['tarif_2eme'] or ligne['tarif_base'])}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Tarif 1ère</label>
             <div>{_fmt_fcfa(ligne['tarif_1ere'] or 0)}</div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-clock"></i> Horaires de départ</h3></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">"""
    for h in horaires:
        content += f'<span class="badge badge-primary" style="font-size:0.9rem;padding:8px 14px">{h["heure_depart"]}</span>'
    if not horaires:
        content += '<div class="empty">Aucun horaire</div>'
    content += "</div></div>"

    content += """
    <div class="card">
      <div class="card-header"><h3><i class="fas fa-history"></i> Derniers voyages</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Date</th><th>Heure</th><th>Véhicule</th><th>Chauffeur</th>
                   <th>Places</th><th>Recette</th><th>Statut</th></tr></thead>
        <tbody>"""
    for v in voyages:
        content += f"""
        <tr>
          <td>{v['date_voyage']}</td>
          <td>{v['heure_depart_prevue'] or '-'}</td>
          <td>{v['immatriculation'] or '-'}</td>
          <td>{v['ch_prenom'] or ''} {v['ch_nom'] or '-'}</td>
          <td>{v['places_vendues']}/{v['places_totales']}</td>
          <td>{_fmt_fcfa(v['recette_reelle'])}</td>
          <td><span class="badge badge-info">{v['statut']}</span></td>
        </tr>"""
    if not voyages:
        content += '<tr><td colspan="7" class="empty">Aucun voyage</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='lignes', title=ligne['code'])


# ================================================================
# ==================== VOYAGES ====================
# ================================================================
@crud_bp.route('/voyages')
@_auth_required
def voyages_list():
    date = request.args.get('date') or datetime.now().date().isoformat()
    statut = request.args.get('statut') or ''

    conn = _db()
    c = conn.cursor()
    sql = """SELECT vo.*, l.code AS ligne_code, l.ville_depart, l.ville_arrivee,
                    v.immatriculation, v.modele,
                    ch.nom AS chauffeur_nom, ch.prenom AS chauffeur_prenom
             FROM voyages vo
             LEFT JOIN lignes l ON vo.ligne_id = l.id
             LEFT JOIN vehicules v ON vo.vehicule_id = v.id
             LEFT JOIN chauffeurs ch ON vo.chauffeur_id = ch.id
             WHERE vo.date_voyage=?"""
    params = [date]
    if statut:
        sql += " AND vo.statut=?"
        params.append(statut)
    sql += " ORDER BY vo.heure_depart_prevue"
    c.execute(sql, params)
    voyages = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-calendar-check"></i> Voyages</h2>
        <div class="page-subtitle">{len(voyages)} voyage(s) le {date}</div></div>
      {'<a href="/voyages/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau voyage</a>' if _can_write() else ''}
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Date</label>
          <input type="date" name="date" value="{date}">
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Statut</label>
          <select name="statut">
            <option value="">Tous</option>
            <option value="Programmé" {"selected" if statut=="Programmé" else ""}>Programmé</option>
            <option value="En cours" {"selected" if statut=="En cours" else ""}>En cours</option>
            <option value="Terminé" {"selected" if statut=="Terminé" else ""}>Terminé</option>
            <option value="Annulé" {"selected" if statut=="Annulé" else ""}>Annulé</option>
          </select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-filter"></i> Filtrer</button>
        <a href="/voyages" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Heure</th><th>N° Voyage</th><th>Ligne</th><th>Véhicule</th>
          <th>Chauffeur</th><th>Places</th><th>Recette</th><th>Statut</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for v in voyages:
        badge = 'badge-info'
        if v['statut'] == 'Terminé': badge = 'badge-success'
        elif v['statut'] == 'En cours': badge = 'badge-warning'
        elif v['statut'] == 'Annulé': badge = 'badge-danger'
        content += f"""
        <tr>
          <td><strong>{v['heure_depart_prevue'] or '-'}</strong></td>
          <td><small>{v['numero']}</small></td>
          <td>
            <div style="font-weight:700">{v['ligne_code'] or '-'}</div>
            <div style="font-size:0.72rem;color:#94a3b8">{v['ville_depart']} → {v['ville_arrivee']}</div>
          </td>
          <td>{v['immatriculation'] or '-'}</td>
          <td>{v['chauffeur_prenom'] or ''} {v['chauffeur_nom'] or '-'}</td>
          <td><span class="badge badge-primary">{v['places_vendues']}/{v['places_totales']}</span></td>
          <td>{_fmt_fcfa(v['recette_reelle'])}</td>
          <td><span class="badge {badge}">{v['statut']}</span></td>
          <td>
            <a href="/voyages/{v['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
            {'<a href="/billets/nouveau?voyage='+str(v['id'])+'" class="btn btn-success btn-sm"><i class="fas fa-ticket"></i></a>' if _can_operate() and v['statut'] in ('Programmé','En cours') else ''}
          </td>
        </tr>"""
    if not voyages:
        content += '<tr><td colspan="9" class="empty"><i class="fas fa-calendar-check"></i><br>Aucun voyage</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='voyages', title='Voyages')


@crud_bp.route('/voyages/<int:vid>')
@_auth_required
def voyages_detail(vid):
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT vo.*, l.code AS ligne_code, l.ville_depart, l.ville_arrivee,
                        l.distance_km, l.tarif_base,
                        v.immatriculation, v.modele, v.capacite_places,
                        ch.nom AS chauffeur_nom, ch.prenom AS chauffeur_prenom, ch.telephone AS ch_tel
                 FROM voyages vo
                 LEFT JOIN lignes l ON vo.ligne_id = l.id
                 LEFT JOIN vehicules v ON vo.vehicule_id = v.id
                 LEFT JOIN chauffeurs ch ON vo.chauffeur_id = ch.id
                 WHERE vo.id=?""", (vid,))
    v = c.fetchone()
    if not v:
        conn.close()
        flash("Voyage introuvable", "danger")
        return redirect('/voyages')

    # Billets
    c.execute("""SELECT * FROM billets WHERE voyage_id=? ORDER BY numero_place""", (vid,))
    billets = c.fetchall()

    conn.close()

    total_billets = sum(b['prix'] for b in billets)
    ecart = (v['recette_reelle'] or 0) - total_billets

    badge = 'badge-info'
    if v['statut'] == 'Terminé': badge = 'badge-success'
    elif v['statut'] == 'En cours': badge = 'badge-warning'
    elif v['statut'] == 'Annulé': badge = 'badge-danger'

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-calendar-check"></i> {v['numero']}</h2>
        <div class="page-subtitle">
          {v['ligne_code']} · {v['ville_depart']} → {v['ville_arrivee']} ·
          <span class="badge {badge}">{v['statut']}</span>
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/voyages" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        {'<a href="/billets/nouveau?voyage='+str(vid)+'" class="btn btn-success"><i class="fas fa-ticket"></i> Vendre billet</a>' if _can_operate() and v['statut'] in ('Programmé','En cours') else ''}
        {'<a href="/voyages/'+str(vid)+'/feuille-route" class="btn btn-purple"><i class="fas fa-file-pdf"></i> Feuille de route</a>' if _can_operate() else ''}
      </div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-ticket"></i></div>
        <div class="stat-value">{len(billets)}</div>
        <div class="stat-label">Billets vendus</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-money-bill-wave"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(total_billets)}</div>
        <div class="stat-label">Total billets</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-coins"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(v['recette_reelle'] or 0)}</div>
        <div class="stat-label">Recette déclarée</div></div>
      <div class="stat-card {'rose' if ecart != 0 else ''}"><div class="stat-icon"><i class="fas fa-triangle-exclamation"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(ecart)}</div>
        <div class="stat-label">Écart</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Détails du voyage</h3></div>
      <div class="form-grid">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Date</label>
             <div style="font-weight:700">{v['date_voyage']}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Départ prévu</label>
             <div>{v['heure_depart_prevue'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Départ réel</label>
             <div>{v['heure_depart_reelle'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Arrivée prévue</label>
             <div>{v['heure_arrivee_prevue'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Véhicule</label>
             <div>{v['immatriculation'] or '-'} ({v['modele'] or '-'})</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Chauffeur</label>
             <div>{v['chauffeur_prenom'] or ''} {v['chauffeur_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Distance</label>
             <div>{v['distance_km'] or '-'} km</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Places</label>
             <div>{v['places_vendues']}/{v['places_totales']}</div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3><i class="fas fa-ticket"></i> Billets vendus ({len(billets)})</h3>
      </div>
      <div class="table-wrap"><table>
        <thead><tr><th>N° Billet</th><th>Passager</th><th>Place</th>
                   <th>Classe</th><th>Prix</th><th>Paiement</th><th>Date</th></tr></thead>
        <tbody>"""
    for b in billets:
        content += f"""
        <tr>
          <td><small>{b['numero']}</small></td>
          <td><strong>{b['passager_nom'] or '-'}</strong>
              <div style="font-size:0.72rem;color:#94a3b8">{b['passager_telephone'] or ''}</div></td>
          <td><span class="badge badge-primary">#{b['numero_place']}</span></td>
          <td>{b['classe']}</td>
          <td><strong>{_fmt_fcfa(b['prix'])}</strong></td>
          <td><small>{b['mode_paiement'] or '-'}</small></td>
          <td><small>{b['date_emission'][:16] if b['date_emission'] else '-'}</small></td>
        </tr>"""
    if not billets:
        content += '<tr><td colspan="7" class="empty">Aucun billet vendu</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='voyages', title=v['numero'])


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
    c.execute("""SELECT u.*, s.nom AS site_nom
                 FROM utilisateurs u
                 LEFT JOIN sites s ON u.site_id = s.id
                 ORDER BY u.nom, u.prenom""")
    users = c.fetchall()
    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-user-shield"></i> Utilisateurs</h2>
        <div class="page-subtitle">{len(users)} utilisateur(s)</div></div>
    </div>
    <div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Username</th><th>Nom</th><th>Rôle</th>
                 <th>Site</th><th>Actif</th><th>Dernier login</th></tr></thead>
      <tbody>"""
    for u in users:
        content += f"""
        <tr>
          <td><strong>{u['username']}</strong></td>
          <td>{u['prenom'] or ''} {u['nom'] or ''}</td>
          <td><span class="badge badge-role-{u['role']}">{u['role']}</span></td>
          <td>{u['site_nom'] or '-'}</td>
          <td>{'✅' if u['actif'] else '❌'}</td>
          <td><small>{u['dernier_login'][:16] if u['dernier_login'] else '-'}</small></td>
        </tr>"""
    content += "</tbody></table></div></div>"
    return _render(content, active='utilisateurs', title='Utilisateurs')


# ================================================================
# ==================== AUDIT ====================
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
    c.execute("SELECT COUNT(*) FROM vehicules WHERE actif=1")
    nb_v = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM chauffeurs WHERE actif=1")
    nb_ch = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM voyages WHERE date_voyage=date('now')")
    nb_voy = c.fetchone()[0]
    conn.close()
    return jsonify(vehicules=nb_v, chauffeurs=nb_ch, voyages_jour=nb_voy,
                   timestamp=datetime.now().isoformat())


@crud_bp.route('/api/voyages/du-jour')
@_auth_required
def api_voyages_jour():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT vo.id, vo.numero, vo.heure_depart_prevue,
                        l.code AS ligne, l.ville_depart, l.ville_arrivee,
                        v.immatriculation, vo.places_vendues, vo.places_totales
                 FROM voyages vo
                 LEFT JOIN lignes l ON vo.ligne_id = l.id
                 LEFT JOIN vehicules v ON vo.vehicule_id = v.id
                 WHERE vo.date_voyage=date('now')
                 ORDER BY vo.heure_depart_prevue""")
    rows = c.fetchall()
    conn.close()
    return jsonify(voyages=[dict(r) for r in rows])
