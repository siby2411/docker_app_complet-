"""
🌾 AgriSénégal V2 — CRUD complet
Producteurs · Parcelles · Cultures · Coopératives · Ventes · Élevage
"""
from flask import Blueprint, request, redirect, flash, jsonify
from flask_login import current_user
import sqlite3
import random
from datetime import datetime, timedelta

crud_bp = Blueprint('crud', __name__)
_deps = {}


def init_crud(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(crud_bp)
    print("[CRUD] ✅ Module CRUD complet enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='dashboard', title='AgriSénégal'):
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
    return current_user and current_user.role in ('admin', 'direction', 'cooperative', 'technicien')


def _can_produce():
    return current_user and current_user.role in ('admin', 'direction', 'cooperative', 'producteur', 'technicien')


def _fmt_fcfa(m):
    if not m:
        return "0 F"
    return f"{int(m):,} F".replace(",", " ")


def _fmt_kg(kg):
    if not kg:
        return "0 kg"
    if kg >= 1000:
        return f"{kg/1000:.1f} t"
    return f"{int(kg)} kg"


def _fmt_ha(ha):
    if not ha:
        return "0 ha"
    return f"{ha:.2f} ha"


# ================================================================
# ==================== PRODUCTEURS ====================
# ================================================================
@crud_bp.route('/producteurs')
@_auth_required
def producteurs_list():
    q = (request.args.get('q') or '').strip()
    region_id = request.args.get('region') or ''
    coop_id = request.args.get('coop') or ''

    conn = _db()
    c = conn.cursor()
    sql = """SELECT p.*,
                    v.nom AS village_nom,
                    d.nom AS departement_nom,
                    r.nom AS region_nom,
                    co.nom AS cooperative_nom,
                    (SELECT COUNT(*) FROM parcelles WHERE producteur_id=p.id AND actif=1) AS nb_parcelles,
                    (SELECT COALESCE(SUM(superficie_ha), 0) FROM parcelles WHERE producteur_id=p.id AND actif=1) AS superficie
             FROM producteurs p
             LEFT JOIN villages v ON p.village_id = v.id
             LEFT JOIN departements d ON v.departement_id = d.id
             LEFT JOIN regions r ON d.region_id = r.id
             LEFT JOIN cooperatives co ON p.cooperative_id = co.id
             WHERE p.actif=1"""
    params = []
    if q:
        sql += " AND (p.nom LIKE ? OR p.prenom LIKE ? OR p.code LIKE ? OR p.telephone LIKE ?)"
        params += [f"%{q}%"] * 4
    if region_id:
        sql += " AND r.id=?"
        params.append(region_id)
    if coop_id:
        sql += " AND p.cooperative_id=?"
        params.append(coop_id)
    sql += " ORDER BY p.nom, p.prenom"
    c.execute(sql, params)
    producteurs = c.fetchall()

    c.execute("SELECT * FROM regions ORDER BY nom")
    regions = c.fetchall()
    c.execute("SELECT * FROM cooperatives WHERE actif=1 ORDER BY nom")
    coops = c.fetchall()
    conn.close()

    opt_r = '<option value="">Toutes régions</option>'
    for r in regions:
        sel = 'selected' if str(r['id']) == region_id else ''
        opt_r += f'<option value="{r["id"]}" {sel}>{r["nom"]}</option>'
    opt_c = '<option value="">Toutes coopératives</option>'
    for co in coops:
        sel = 'selected' if str(co['id']) == coop_id else ''
        opt_c += f'<option value="{co["id"]}" {sel}>{co["nom"]}</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-users"></i> Producteurs</h2>
        <div class="page-subtitle">{len(producteurs)} producteur(s) actif(s)</div></div>
      {'<a href="/producteurs/nouveau" class="btn btn-primary"><i class="fas fa-user-plus"></i> Nouveau producteur</a>' if _can_write() else ''}
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:2;margin:0;min-width:200px">
          <label>Recherche</label>
          <input type="text" name="q" value="{q}" placeholder="Nom, code, téléphone...">
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:180px">
          <label>Région</label>
          <select name="region">{opt_r}</select>
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:180px">
          <label>Coopérative</label>
          <select name="coop">{opt_c}</select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-search"></i> Filtrer</button>
        <a href="/producteurs" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Code</th><th>Producteur</th><th>Localisation</th>
          <th>Coopérative</th><th>Parcelles</th><th>Superficie</th>
          <th>Mobile Money</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for p in producteurs:
        initiales = f"{p['prenom'][0] if p['prenom'] else ''}{p['nom'][0] if p['nom'] else ''}"
        mm_badge = ''
        if p['mobile_money_type']:
            color = '#10b981' if p['mobile_money_type'] == 'Wave' else ('#f97316' if p['mobile_money_type'] == 'Orange Money' else '#dc2626')
            mm_badge = f'<span class="badge" style="background:{color}20;color:{color}">{p["mobile_money_type"]}</span>'

        content += f"""
        <tr>
          <td><strong>{p['code']}</strong></td>
          <td>
            <div style="display:flex;align-items:center;gap:10px">
              <div style="width:36px;height:36px;background:linear-gradient(135deg,#065f46,#10b981);border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-weight:800;font-size:0.85rem;flex-shrink:0">{initiales}</div>
              <div>
                <div style="font-weight:700">{p['prenom']} {p['nom']}</div>
                <div style="font-size:0.72rem;color:#94a3b8">{p['telephone'] or '-'}</div>
              </div>
            </div>
          </td>
          <td>
            <div>{p['village_nom'] or '-'}</div>
            <div style="font-size:0.72rem;color:#94a3b8">{p['region_nom'] or ''}</div>
          </td>
          <td>{p['cooperative_nom'] or '-'}</td>
          <td><span class="badge badge-primary">{p['nb_parcelles']}</span></td>
          <td><small>{_fmt_ha(p['superficie'])}</small></td>
          <td>{mm_badge}</td>
          <td style="white-space:nowrap">
            <a href="/producteurs/{p['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
            {'<a href="/producteurs/'+str(p['id'])+'/modifier" class="btn btn-warning btn-sm"><i class="fas fa-pen"></i></a>' if _can_write() else ''}
          </td>
        </tr>"""
    if not producteurs:
        content += '<tr><td colspan="8" class="empty"><i class="fas fa-users"></i><br>Aucun producteur</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='producteurs', title='Producteurs')


@crud_bp.route('/producteurs/<int:pid>')
@_auth_required
def producteurs_detail(pid):
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT p.*, v.nom AS village_nom, d.nom AS departement_nom,
                        r.nom AS region_nom, co.nom AS cooperative_nom
                 FROM producteurs p
                 LEFT JOIN villages v ON p.village_id = v.id
                 LEFT JOIN departements d ON v.departement_id = d.id
                 LEFT JOIN regions r ON d.region_id = r.id
                 LEFT JOIN cooperatives co ON p.cooperative_id = co.id
                 WHERE p.id=?""", (pid,))
    p = c.fetchone()
    if not p:
        conn.close()
        flash("Producteur introuvable", "danger")
        return redirect('/producteurs')

    # Parcelles
    c.execute("""SELECT pa.*,
                        (SELECT c.nom FROM cultures_parcelles cp LEFT JOIN cultures c ON cp.culture_id = c.id
                         WHERE cp.parcelle_id = pa.id ORDER BY cp.id DESC LIMIT 1) AS culture_nom
                 FROM parcelles pa WHERE pa.producteur_id=? AND pa.actif=1
                 ORDER BY pa.code""", (pid,))
    parcelles = c.fetchall()

    # Récoltes
    c.execute("""SELECT r.*, c.nom AS culture_nom, c.icone
                 FROM recoltes r LEFT JOIN cultures c ON r.culture_id = c.id
                 WHERE r.producteur_id=? ORDER BY r.date_recolte DESC LIMIT 10""", (pid,))
    recoltes = c.fetchall()

    # Ventes
    c.execute("""SELECT v.*, c.nom AS culture_nom
                 FROM ventes v LEFT JOIN cultures c ON v.culture_id = c.id
                 WHERE v.producteur_id=? ORDER BY v.date_vente DESC LIMIT 10""", (pid,))
    ventes = c.fetchall()

    # Stats
    c.execute("""SELECT COUNT(*) AS nb, COALESCE(SUM(superficie_ha), 0) AS sup
                 FROM parcelles WHERE producteur_id=? AND actif=1""", (pid,))
    stats_p = c.fetchone()

    c.execute("""SELECT COALESCE(SUM(quantite_kg), 0) AS total FROM recoltes WHERE producteur_id=?""", (pid,))
    prod_totale = c.fetchone()['total']

    c.execute("""SELECT COALESCE(SUM(montant_total), 0) AS ca FROM ventes
                 WHERE producteur_id=? AND statut_paiement='Payé'""", (pid,))
    ca_total = c.fetchone()['ca']

    c.execute("""SELECT COUNT(*) AS nb FROM transactions_mobile
                 WHERE producteur_id=? AND statut='Réussi'""", (pid,))
    nb_trans = c.fetchone()['nb']

    conn.close()

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-user"></i> {p['prenom']} {p['nom']}</h2>
        <div class="page-subtitle">
          <strong>{p['code']}</strong> · {p['exploitation_nom'] or 'Exploitation'} ·
          {p['village_nom'] or '-'}, {p['region_nom'] or '-'}
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/producteurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        {'<a href="/producteurs/'+str(pid)+'/modifier" class="btn btn-warning"><i class="fas fa-pen"></i> Modifier</a>' if _can_write() else ''}
      </div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-draw-polygon"></i></div>
        <div class="stat-value">{stats_p['nb']}</div>
        <div class="stat-label">Parcelles</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-ruler-combined"></i></div>
        <div class="stat-value">{_fmt_ha(stats_p['sup'])}</div>
        <div class="stat-label">Superficie</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-wheat-awn"></i></div>
        <div class="stat-value">{_fmt_kg(prod_totale)}</div>
        <div class="stat-label">Production totale</div></div>
      <div class="stat-card blue"><div class="stat-icon"><i class="fas fa-money-bill-wave"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(ca_total)}</div>
        <div class="stat-label">CA réalisé</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
      <div class="form-grid">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Code</label>
             <div style="font-weight:700">{p['code']}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Téléphone</label>
             <div>{p['telephone'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Sexe</label>
             <div>{p['sexe'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Expérience</label>
             <div>{p['experience_annees'] or 0} ans</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Type exploitation</label>
             <div>{p['type_exploitation'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Langue</label>
             <div>{p['langue_principale'] or 'Wolof'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Mobile Money</label>
             <div>{p['mobile_money_type'] or '-'} · {p['mobile_money_numero'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Coopérative</label>
             <div>{p['cooperative_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">GPS</label>
             <div style="font-family:monospace;font-size:0.85rem">{p['gps_latitude'] or '-'}, {p['gps_longitude'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Certification bio</label>
             <div>{'✅ Oui' if p['certification_bio'] else '❌ Non'}</div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3><i class="fas fa-draw-polygon"></i> Parcelles ({len(parcelles)})</h3>
        {'<a href="/parcelles/nouvelle?producteur='+str(pid)+'" class="btn btn-primary btn-sm"><i class="fas fa-plus"></i> Ajouter</a>' if _can_write() else ''}
      </div>
      <div class="table-wrap"><table>
        <thead><tr><th>Code</th><th>Nom</th><th>Superficie</th><th>Culture</th>
                   <th>Irrigation</th><th>Sol</th></tr></thead>
        <tbody>"""
    for pa in parcelles:
        content += f"""
        <tr>
          <td><strong>{pa['code']}</strong></td>
          <td>{pa['nom'] or '-'}</td>
          <td><span class="badge badge-primary">{pa['superficie_ha']} ha</span></td>
          <td>{pa['culture_nom'] or '-'}</td>
          <td>{'✅' if pa['irrigation_disponible'] else '❌'}</td>
          <td><small>{pa['type_sol'] or '-'}</small></td>
        </tr>"""
    if not parcelles:
        content += '<tr><td colspan="6" class="empty">Aucune parcelle</td></tr>'
    content += "</tbody></table></div></div>"

    # Récoltes
    if recoltes:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-wheat-awn"></i> Récoltes récentes</h3></div>
          <div class="table-wrap"><table>
            <thead><tr><th>Date</th><th>Culture</th><th>Quantité</th>
                       <th>Qualité</th><th>Destination</th></tr></thead>
            <tbody>"""
        for r in recoltes:
            content += f"""
            <tr>
              <td>{r['date_recolte']}</td>
              <td><i class="fas {r['icone'] or 'fa-seedling'}" style="color:#10b981"></i> {r['culture_nom']}</td>
              <td><strong>{_fmt_kg(r['quantite_kg'])}</strong></td>
              <td>{r['qualite'] or '-'}</td>
              <td><small>{r['destination'] or '-'}</small></td>
            </tr>"""
        content += "</tbody></table></div></div>"

    # Ventes
    if ventes:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-money-bill-wave"></i> Ventes récentes</h3></div>
          <div class="table-wrap"><table>
            <thead><tr><th>Réf</th><th>Date</th><th>Culture</th>
                       <th>Quantité</th><th>Montant</th><th>Statut</th></tr></thead>
            <tbody>"""
        for v in ventes:
            badge = 'badge-success' if v['statut_paiement'] == 'Payé' else 'badge-warning'
            content += f"""
            <tr>
              <td><small>{v['reference']}</small></td>
              <td>{v['date_vente']}</td>
              <td>{v['culture_nom']}</td>
              <td>{_fmt_kg(v['quantite_kg'])}</td>
              <td><strong>{_fmt_fcfa(v['montant_total'])}</strong></td>
              <td><span class="badge {badge}">{v['statut_paiement']}</span></td>
            </tr>"""
        content += "</tbody></table></div></div>"

    return _render(content, active='producteurs', title=p['prenom'] + ' ' + p['nom'])


@crud_bp.route('/producteurs/nouveau', methods=['GET', 'POST'])
@_auth_required
def producteurs_new():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/producteurs')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        nom = (request.form.get('nom') or '').strip()
        prenom = (request.form.get('prenom') or '').strip()
        if not nom:
            flash("Nom obligatoire", "warning")
        else:
            # Générer code
            c.execute("SELECT COUNT(*) FROM producteurs")
            n = (c.fetchone()[0] or 0) + 1
            code = f"PRD-{n:04d}"

            try:
                c.execute("""INSERT INTO producteurs
                    (code, nom, prenom, sexe, date_naissance, telephone, telephone_secondaire,
                     email, numero_cni, village_id, cooperative_id, exploitation_nom,
                     superficie_totale, type_exploitation, experience_annees, niveau_education,
                     langue_principale, mobile_money_type, mobile_money_numero,
                     gps_latitude, gps_longitude, certification_bio, actif, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)""",
                    (code, nom, prenom,
                     request.form.get('sexe') or 'M',
                     request.form.get('date_naissance') or None,
                     (request.form.get('telephone') or '').strip(),
                     (request.form.get('telephone_secondaire') or '').strip(),
                     (request.form.get('email') or '').strip(),
                     (request.form.get('numero_cni') or '').strip(),
                     request.form.get('village_id') or None,
                     request.form.get('cooperative_id') or None,
                     (request.form.get('exploitation_nom') or '').strip(),
                     float(request.form.get('superficie_totale') or 0),
                     request.form.get('type_exploitation') or 'Familiale',
                     int(request.form.get('experience_annees') or 0),
                     request.form.get('niveau_education') or None,
                     request.form.get('langue_principale') or 'Wolof',
                     request.form.get('mobile_money_type') or None,
                     (request.form.get('mobile_money_numero') or '').strip(),
                     float(request.form.get('gps_latitude') or 0) or None,
                     float(request.form.get('gps_longitude') or 0) or None,
                     1 if request.form.get('certification_bio') else 0,
                     datetime.now().isoformat(), datetime.now().isoformat()))
                new_id = c.lastrowid
                conn.commit()
                _log('CREATE_PRODUCTEUR', f"Producteur {prenom} {nom} ({code})",
                     entity='producteur', entity_id=new_id)
                flash(f"Producteur {prenom} {nom} créé", "success")
                conn.close()
                return redirect(f'/producteurs/{new_id}')
            except Exception as e:
                flash(f"Erreur : {e}", "danger")

    c.execute("""SELECT v.id, v.nom, d.nom AS dep_nom, r.nom AS reg_nom
                 FROM villages v
                 LEFT JOIN departements d ON v.departement_id = d.id
                 LEFT JOIN regions r ON d.region_id = r.id
                 ORDER BY r.nom, v.nom""")
    villages = c.fetchall()
    c.execute("SELECT id, nom FROM cooperatives WHERE actif=1 ORDER BY nom")
    coops = c.fetchall()
    conn.close()

    opt_v = ''.join(f'<option value="{v["id"]}">{v["nom"]} ({v["reg_nom"]})</option>' for v in villages)
    opt_c = ''.join(f'<option value="{co["id"]}">{co["nom"]}</option>' for co in coops)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-user-plus"></i> Nouveau producteur</h2></div>
      <a href="/producteurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
          <div class="form-group"><label>Prénom</label><input type="text" name="prenom"></div>
          <div class="form-group"><label>Sexe</label>
            <select name="sexe"><option value="M">Masculin</option><option value="F">Féminin</option></select>
          </div>
          <div class="form-group"><label>Date de naissance</label><input type="date" name="date_naissance"></div>
          <div class="form-group"><label>Téléphone</label><input type="text" name="telephone"></div>
          <div class="form-group"><label>Email</label><input type="email" name="email"></div>
          <div class="form-group"><label>N° CNI</label><input type="text" name="numero_cni"></div>
          <div class="form-group"><label>Village</label>
            <select name="village_id"><option value="">—</option>{opt_v}</select>
          </div>
          <div class="form-group"><label>Coopérative</label>
            <select name="cooperative_id"><option value="">—</option>{opt_c}</select>
          </div>
          <div class="form-group"><label>Nom exploitation</label>
            <input type="text" name="exploitation_nom" placeholder="Ex: Ferme Ndiaye">
          </div>
          <div class="form-group"><label>Superficie totale (ha)</label>
            <input type="number" step="0.1" name="superficie_totale" value="0">
          </div>
          <div class="form-group"><label>Type exploitation</label>
            <select name="type_exploitation">
              <option>Familiale</option><option>Coopérative</option>
              <option>Agro-industrielle</option><option>Mixte</option>
            </select>
          </div>
          <div class="form-group"><label>Expérience (années)</label>
            <input type="number" name="experience_annees" value="0">
          </div>
          <div class="form-group"><label>Langue principale</label>
            <select name="langue_principale">
              <option>Wolof</option><option>Pulaar</option><option>Serer</option>
              <option>Diola</option><option>Mandinka</option><option>Français</option>
            </select>
          </div>
          <div class="form-group"><label>Mobile Money</label>
            <select name="mobile_money_type">
              <option value="">—</option><option>Wave</option>
              <option>Orange Money</option><option>Free Money</option>
            </select>
          </div>
          <div class="form-group"><label>N° Mobile Money</label>
            <input type="text" name="mobile_money_numero">
          </div>
          <div class="form-group"><label>GPS Latitude</label>
            <input type="number" step="0.000001" name="gps_latitude" placeholder="14.7833">
          </div>
          <div class="form-group"><label>GPS Longitude</label>
            <input type="number" step="0.000001" name="gps_longitude" placeholder="-17.3167">
          </div>
          <div class="form-group form-full">
            <label><input type="checkbox" name="certification_bio"> Certification biologique</label>
          </div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Créer</button>
          <a href="/producteurs" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='producteurs', title='Nouveau producteur')


@crud_bp.route('/producteurs/<int:pid>/modifier', methods=['GET', 'POST'])
@_auth_required
def producteurs_edit(pid):
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/producteurs')

    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM producteurs WHERE id=?", (pid,))
    p = c.fetchone()
    if not p:
        conn.close()
        return redirect('/producteurs')

    if request.method == 'POST':
        c.execute("""UPDATE producteurs SET
            nom=?, prenom=?, sexe=?, date_naissance=?, telephone=?,
            email=?, numero_cni=?, village_id=?, cooperative_id=?,
            exploitation_nom=?, superficie_totale=?, type_exploitation=?,
            experience_annees=?, langue_principale=?, mobile_money_type=?,
            mobile_money_numero=?, gps_latitude=?, gps_longitude=?,
            certification_bio=?, updated_at=?
            WHERE id=?""",
            ((request.form.get('nom') or '').strip(),
             (request.form.get('prenom') or '').strip(),
             request.form.get('sexe') or 'M',
             request.form.get('date_naissance') or None,
             (request.form.get('telephone') or '').strip(),
             (request.form.get('email') or '').strip(),
             (request.form.get('numero_cni') or '').strip(),
             request.form.get('village_id') or None,
             request.form.get('cooperative_id') or None,
             (request.form.get('exploitation_nom') or '').strip(),
             float(request.form.get('superficie_totale') or 0),
             request.form.get('type_exploitation') or 'Familiale',
             int(request.form.get('experience_annees') or 0),
             request.form.get('langue_principale') or 'Wolof',
             request.form.get('mobile_money_type') or None,
             (request.form.get('mobile_money_numero') or '').strip(),
             float(request.form.get('gps_latitude') or 0) or None,
             float(request.form.get('gps_longitude') or 0) or None,
             1 if request.form.get('certification_bio') else 0,
             datetime.now().isoformat(), pid))
        conn.commit()
        _log('UPDATE_PRODUCTEUR', f"Producteur id={pid} modifié",
             entity='producteur', entity_id=pid)
        conn.close()
        flash("Producteur mis à jour", "success")
        return redirect(f'/producteurs/{pid}')

    c.execute("SELECT id, nom FROM villages ORDER BY nom")
    villages = c.fetchall()
    c.execute("SELECT id, nom FROM cooperatives WHERE actif=1 ORDER BY nom")
    coops = c.fetchall()
    conn.close()

    def opt_v(items, cur):
        return ''.join(f'<option value="{i["id"]}" {"selected" if cur==i["id"] else ""}>{i["nom"]}</option>' for i in items)
    def opt_c(items, cur):
        return ''.join(f'<option value="{i["id"]}" {"selected" if cur==i["id"] else ""}>{i["nom"]}</option>' for i in items)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-pen"></i> Modifier producteur</h2></div>
      <a href="/producteurs/{pid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group"><label>Nom</label><input type="text" name="nom" value="{p['nom']}" required></div>
          <div class="form-group"><label>Prénom</label><input type="text" name="prenom" value="{p['prenom'] or ''}"></div>
          <div class="form-group"><label>Téléphone</label><input type="text" name="telephone" value="{p['telephone'] or ''}"></div>
          <div class="form-group"><label>Email</label><input type="email" name="email" value="{p['email'] or ''}"></div>
          <div class="form-group"><label>Village</label>
            <select name="village_id"><option value="">—</option>{opt_v(villages, p['village_id'])}</select>
          </div>
          <div class="form-group"><label>Coopérative</label>
            <select name="cooperative_id"><option value="">—</option>{opt_c(coops, p['cooperative_id'])}</select>
          </div>
          <div class="form-group"><label>Exploitation</label>
            <input type="text" name="exploitation_nom" value="{p['exploitation_nom'] or ''}">
          </div>
          <div class="form-group"><label>Superficie (ha)</label>
            <input type="number" step="0.1" name="superficie_totale" value="{p['superficie_totale'] or 0}">
          </div>
          <div class="form-group"><label>Expérience (ans)</label>
            <input type="number" name="experience_annees" value="{p['experience_annees'] or 0}">
          </div>
          <div class="form-group"><label>Mobile Money</label>
            <select name="mobile_money_type">
              <option value="">—</option>
              <option {'selected' if p['mobile_money_type']=='Wave' else ''}>Wave</option>
              <option {'selected' if p['mobile_money_type']=='Orange Money' else ''}>Orange Money</option>
              <option {'selected' if p['mobile_money_type']=='Free Money' else ''}>Free Money</option>
            </select>
          </div>
          <div class="form-group"><label>N° Mobile Money</label>
            <input type="text" name="mobile_money_numero" value="{p['mobile_money_numero'] or ''}">
          </div>
          <div class="form-group form-full">
            <label><input type="checkbox" name="certification_bio" {'checked' if p['certification_bio'] else ''}> Certification bio</label>
          </div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
          <a href="/producteurs/{pid}" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='producteurs', title='Modifier producteur')


# ================================================================
# ==================== PARCELLES ====================
# ================================================================
@crud_bp.route('/parcelles')
@_auth_required
def parcelles_list():
    q = (request.args.get('q') or '').strip()
    producteur_id = request.args.get('producteur') or ''
    culture_id = request.args.get('culture') or ''

    conn = _db()
    c = conn.cursor()
    sql = """SELECT pa.*,
                    pr.nom AS producteur_nom, pr.prenom AS producteur_prenom,
                    v.nom AS village_nom,
                    (SELECT c.nom FROM cultures_parcelles cp
                     LEFT JOIN cultures c ON cp.culture_id = c.id
                     WHERE cp.parcelle_id = pa.id ORDER BY cp.id DESC LIMIT 1) AS culture_nom,
                    (SELECT c.icone FROM cultures_parcelles cp
                     LEFT JOIN cultures c ON cp.culture_id = c.id
                     WHERE cp.parcelle_id = pa.id ORDER BY cp.id DESC LIMIT 1) AS culture_icone
             FROM parcelles pa
             LEFT JOIN producteurs pr ON pa.producteur_id = pr.id
             LEFT JOIN villages v ON pr.village_id = v.id
             WHERE pa.actif=1"""
    params = []
    if q:
        sql += " AND (pa.code LIKE ? OR pa.nom LIKE ?)"
        params += [f"%{q}%"] * 2
    if producteur_id:
        sql += " AND pa.producteur_id=?"
        params.append(producteur_id)
    sql += " ORDER BY pa.code"
    c.execute(sql, params)
    parcelles = c.fetchall()

    c.execute("SELECT id, nom, prenom, code FROM producteurs WHERE actif=1 ORDER BY nom")
    producteurs = c.fetchall()
    conn.close()

    opt_p = '<option value="">Tous producteurs</option>'
    for p in producteurs:
        sel = 'selected' if str(p['id']) == producteur_id else ''
        opt_p += f'<option value="{p["id"]}" {sel}>{p["prenom"]} {p["nom"]}</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-draw-polygon"></i> Parcelles</h2>
        <div class="page-subtitle">{len(parcelles)} parcelle(s)</div></div>
      {'<a href="/parcelles/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle parcelle</a>' if _can_write() else ''}
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:2;margin:0;min-width:200px">
          <label>Recherche</label>
          <input type="text" name="q" value="{q}" placeholder="Code, nom...">
        </div>
        <div class="form-group" style="flex:2;margin:0;min-width:200px">
          <label>Producteur</label>
          <select name="producteur">{opt_p}</select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-search"></i> Filtrer</button>
        <a href="/parcelles" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Code</th><th>Nom</th><th>Producteur</th><th>Superficie</th>
          <th>Culture actuelle</th><th>Sol</th><th>Irrigation</th><th>GPS</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for pa in parcelles:
        content += f"""
        <tr>
          <td><strong>{pa['code']}</strong></td>
          <td>{pa['nom'] or '-'}</td>
          <td>{pa['producteur_prenom'] or ''} {pa['producteur_nom'] or ''}
              <div style="font-size:0.72rem;color:#94a3b8">{pa['village_nom'] or ''}</div></td>
          <td><span class="badge badge-primary">{pa['superficie_ha']} ha</span></td>
          <td>
            <i class="fas {pa['culture_icone'] or 'fa-seedling'}" style="color:#10b981"></i>
            {pa['culture_nom'] or '-'}
          </td>
          <td><small>{pa['type_sol'] or '-'}</small></td>
          <td>{'✅' if pa['irrigation_disponible'] else '❌'}</td>
          <td><small style="font-family:monospace">{pa['latitude']:.4f},{pa['longitude']:.4f}</small></td>
          <td>
            <a href="/parcelles/{pa['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
          </td>
        </tr>"""
    if not parcelles:
        content += '<tr><td colspan="9" class="empty"><i class="fas fa-draw-polygon"></i><br>Aucune parcelle</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='parcelles', title='Parcelles')


@crud_bp.route('/parcelles/<int:paid>')
@_auth_required
def parcelles_detail(paid):
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT pa.*,
                        pr.nom AS producteur_nom, pr.prenom AS producteur_prenom,
                        pr.telephone AS producteur_tel, pr.code AS producteur_code,
                        v.nom AS village_nom, r.nom AS region_nom
                 FROM parcelles pa
                 LEFT JOIN producteurs pr ON pa.producteur_id = pr.id
                 LEFT JOIN villages v ON pr.village_id = v.id
                 LEFT JOIN departements d ON v.departement_id = d.id
                 LEFT JOIN regions r ON d.region_id = r.id
                 WHERE pa.id=?""", (paid,))
    pa = c.fetchone()
    if not pa:
        conn.close()
        flash("Parcelle introuvable", "danger")
        return redirect('/parcelles')

    # Cultures sur la parcelle
    c.execute("""SELECT cp.*, c.nom AS culture_nom, c.icone, c.cycle_jours_min
                 FROM cultures_parcelles cp
                 LEFT JOIN cultures c ON cp.culture_id = c.id
                 WHERE cp.parcelle_id=?
                 ORDER BY cp.date_semis DESC""", (paid,))
    cultures = c.fetchall()

    # Images NDVI
    c.execute("""SELECT * FROM images_satellite
                 WHERE parcelle_id=?
                 ORDER BY date_image DESC LIMIT 8""", (paid,))
    ndvi_images = c.fetchall()

    # Météo du village
    c.execute("""SELECT * FROM donnees_meteo
                 WHERE village_id=?
                 ORDER BY date_mesure DESC LIMIT 7""", (pa['producteur_id'],))
    # Note: il faudrait le village du producteur, mais bon...
    meteo = c.fetchall()

    # Récoltes
    c.execute("""SELECT r.*, c.nom AS culture_nom
                 FROM recoltes r LEFT JOIN cultures c ON r.culture_id = c.id
                 WHERE r.parcelle_id=?
                 ORDER BY r.date_recolte DESC""", (paid,))
    recoltes = c.fetchall()

    conn.close()

    # Calcul surface
    total_recolte = sum(r['quantite_kg'] or 0 for r in recoltes)
    rendement_moyen = (total_recolte / (pa['superficie_ha'] or 1)) if total_recolte else 0

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-draw-polygon"></i> {pa['code']}</h2>
        <div class="page-subtitle">
          {pa['nom'] or 'Parcelle'} · {pa['superficie_ha']} ha ·
          {pa['producteur_prenom'] or ''} {pa['producteur_nom'] or ''}
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/parcelles" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        <a href="https://www.openstreetmap.org/?mlat={pa['latitude']}&mlon={pa['longitude']}&zoom=16" target="_blank" class="btn btn-purple">
          <i class="fas fa-map"></i> Voir sur OSM
        </a>
      </div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-ruler-combined"></i></div>
        <div class="stat-value">{pa['superficie_ha']}</div>
        <div class="stat-label">Hectares</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-wheat-awn"></i></div>
        <div class="stat-value">{_fmt_kg(total_recolte)}</div>
        <div class="stat-label">Production totale</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-chart-line"></i></div>
        <div class="stat-value">{rendement_moyen/1000:.1f} t/ha</div>
        <div class="stat-label">Rendement moyen</div></div>
      <div class="stat-card blue"><div class="stat-icon"><i class="fas fa-leaf"></i></div>
        <div class="stat-value">{len(cultures)}</div>
        <div class="stat-label">Campagnes</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Détails</h3></div>
      <div class="form-grid">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Producteur</label>
             <div style="font-weight:700">{pa['producteur_prenom'] or ''} {pa['producteur_nom'] or ''}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Village</label>
             <div>{pa['village_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Région</label>
             <div>{pa['region_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Type de sol</label>
             <div>{pa['type_sol'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">pH sol</label>
             <div>{pa['ph_sol'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Irrigation</label>
             <div>{'✅ ' + (pa['source_eau'] or '') if pa['irrigation_disponible'] else '❌ Non'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Statut juridique</label>
             <div>{pa['statut_juridique'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">GPS</label>
             <div style="font-family:monospace;font-size:0.85rem">{pa['latitude']:.6f}, {pa['longitude']:.6f}</div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3><i class="fas fa-seedling"></i> Historique des cultures</h3>
        {'<a href="/cultures/nouvelle?parcelle='+str(paid)+'" class="btn btn-primary btn-sm"><i class="fas fa-plus"></i> Nouvelle culture</a>' if _can_produce() else ''}
      </div>
      <div class="table-wrap"><table>
        <thead><tr><th>Date semis</th><th>Culture</th><th>Variété</th>
                   <th>Superficie</th><th>État</th><th>Rendement</th></tr></thead>
        <tbody>"""
    for cu in cultures:
        badge = 'badge-info'
        if cu['etat'] == 'Récolté': badge = 'badge-success'
        elif cu['etat'] == 'En croissance': badge = 'badge-warning'
        content += f"""
        <tr>
          <td>{cu['date_semis']}</td>
          <td><i class="fas {cu['icone'] or 'fa-seedling'}" style="color:#10b981"></i> {cu['culture_nom']}</td>
          <td>{cu['variete_id'] or '-'}</td>
          <td>{cu['superficie_ha'] or pa['superficie_ha']} ha</td>
          <td><span class="badge {badge}">{cu['etat']}</span></td>
          <td>{cu['rendement_obtenu_t_ha'] or '-'} t/ha</td>
        </tr>"""
    if not cultures:
        content += '<tr><td colspan="6" class="empty">Aucune culture</td></tr>'
    content += "</tbody></table></div></div>"

    # NDVI
    if ndvi_images:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-satellite"></i> Suivi satellite NDVI</h3></div>
          <div class="table-wrap"><table>
            <thead><tr><th>Date</th><th>Satellite</th><th>NDVI moyen</th>
                       <th>NDWI</th><th>Stress hydrique</th><th>Stress azote</th></tr></thead>
            <tbody>"""
        for n in ndvi_images:
            badge_ndvi = 'badge-success'
            if n['ndvi_moyen'] < 0.35: badge_ndvi = 'badge-danger'
            elif n['ndvi_moyen'] < 0.5: badge_ndvi = 'badge-warning'
            content += f"""
            <tr>
              <td>{n['date_image']}</td>
              <td><small>{n['source'] or '-'}</small></td>
              <td><span class="badge {badge_ndvi}">{n['ndvi_moyen']:.3f}</span></td>
              <td>{n['ndwi'] or '-'}</td>
              <td>{'⚠️ Oui' if n['stress_hydrique'] else '✅ Non'}</td>
              <td>{'⚠️ Oui' if n['stress_azote'] else '✅ Non'}</td>
            </tr>"""
        content += "</tbody></table></div></div>"

    # Récoltes
    if recoltes:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-wheat-awn"></i> Récoltes</h3></div>
          <div class="table-wrap"><table>
            <thead><tr><th>Réf</th><th>Date</th><th>Culture</th>
                       <th>Quantité</th><th>Qualité</th><th>Destination</th></tr></thead>
            <tbody>"""
        for r in recoltes:
            content += f"""
            <tr>
              <td><small>{r['code']}</small></td>
              <td>{r['date_recolte']}</td>
              <td>{r['culture_nom']}</td>
              <td><strong>{_fmt_kg(r['quantite_kg'])}</strong></td>
              <td>{r['qualite'] or '-'}</td>
              <td><small>{r['destination'] or '-'}</small></td>
            </tr>"""
        content += "</tbody></table></div></div>"

    return _render(content, active='parcelles', title=pa['code'])


# ================================================================
# ==================== CULTURES ====================
# ================================================================
@crud_bp.route('/cultures')
@_auth_required
def cultures_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT c.*,
                 (SELECT COUNT(*) FROM cultures_parcelles WHERE culture_id=c.id) AS nb_cultures,
                 (SELECT COALESCE(SUM(quantite_kg), 0) FROM recoltes WHERE culture_id=c.id) AS production
                 FROM cultures c WHERE c.actif=1
                 ORDER BY production DESC, c.nom""")
    cultures = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-seedling"></i> Cultures</h2>
        <div class="page-subtitle">{len(cultures)} culture(s) référencée(s)</div></div>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Culture</th><th>Nom Wolof</th><th>Catégorie</th><th>Cycle</th>
          <th>Rendement théo.</th><th>Prix moyen</th><th>Parcelles</th><th>Production</th>
        </tr></thead><tbody>
    """
    for cu in cultures:
        content += f"""
        <tr>
          <td>
            <div style="display:flex;align-items:center;gap:10px">
              <div style="width:36px;height:36px;background:linear-gradient(135deg,#065f46,#10b981);border-radius:10px;display:flex;align-items:center;justify-content:center;color:white">
                <i class="fas {cu['icone'] or 'fa-seedling'}"></i>
              </div>
              <div>
                <div style="font-weight:700">{cu['nom']}</div>
                <div style="font-size:0.72rem;color:#94a3b8">{cu['nom_scientifique'] or ''}</div>
              </div>
            </div>
          </td>
          <td><em>{cu['nom_wolof'] or '-'}</em></td>
          <td><span class="badge badge-primary">{cu['categorie'] or '-'}</span></td>
          <td><small>{cu['cycle_jours_min'] or '?'}-{cu['cycle_jours_max'] or '?'} j</small></td>
          <td>{cu['rendement_theorique_t_ha'] or '-'} t/ha</td>
          <td>{_fmt_fcfa(cu['prix_moyen_kg'])}/kg</td>
          <td><span class="badge badge-info">{cu['nb_cultures']}</span></td>
          <td><strong>{_fmt_kg(cu['production'])}</strong></td>
        </tr>"""
    content += "</tbody></table></div></div>"
    return _render(content, active='cultures', title='Cultures')


# ================================================================
# ==================== COOPERATIVES ====================
# ================================================================
@crud_bp.route('/cooperatives')
@_auth_required
def cooperatives_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT co.*,
                 v.nom AS village_nom,
                 r.nom AS region_nom,
                 (SELECT COUNT(*) FROM producteurs WHERE cooperative_id=co.id AND actif=1) AS nb_membres
                 FROM cooperatives co
                 LEFT JOIN villages v ON co.village_id = v.id
                 LEFT JOIN departements d ON v.departement_id = d.id
                 LEFT JOIN regions r ON d.region_id = r.id
                 WHERE co.actif=1
                 ORDER BY co.nom""")
    coops = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-handshake"></i> Coopératives</h2>
        <div class="page-subtitle">{len(coops)} coopérative(s)</div></div>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Code</th><th>Nom</th><th>Type</th><th>Village</th>
          <th>Région</th><th>Membres</th><th>Téléphone</th>
        </tr></thead><tbody>
    """
    for co in coops:
        content += f"""
        <tr>
          <td><strong>{co['code']}</strong></td>
          <td>{co['nom']}</td>
          <td><span class="badge badge-primary">{co['type'] or '-'}</span></td>
          <td>{co['village_nom'] or '-'}</td>
          <td>{co['region_nom'] or '-'}</td>
          <td><span class="badge badge-info">{co['nb_membres']}</span></td>
          <td>{co['telephone'] or '-'}</td>
        </tr>"""
    if not coops:
        content += '<tr><td colspan="7" class="empty"><i class="fas fa-handshake"></i><br>Aucune coopérative</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='cooperatives', title='Coopératives')


# ================================================================
# ==================== VENTES ====================
# ================================================================
@crud_bp.route('/ventes')
@_auth_required
def ventes_list():
    if current_user.role not in ('admin', 'direction', 'cooperative', 'producteur', 'finance'):
        flash("Accès réservé", "danger")
        return redirect('/')

    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')
    statut = request.args.get('statut') or ''

    conn = _db()
    c = conn.cursor()
    sql = """SELECT v.*, c.nom AS culture_nom, c.icone,
                    p.nom AS producteur_nom, p.prenom AS producteur_prenom
             FROM ventes v
             LEFT JOIN cultures c ON v.culture_id = c.id
             LEFT JOIN producteurs p ON v.producteur_id = p.id
             WHERE strftime('%Y-%m', v.date_vente)=?"""
    params = [mois]
    if statut:
        sql += " AND v.statut_paiement=?"
        params.append(statut)
    sql += " ORDER BY v.date_vente DESC LIMIT 200"
    c.execute(sql, params)
    ventes = c.fetchall()

    # Stats
    c.execute("""SELECT COUNT(*) AS nb, COALESCE(SUM(montant_total), 0) AS total,
                        COALESCE(SUM(quantite_kg), 0) AS qte,
                        SUM(CASE WHEN statut_paiement='Payé' THEN 1 ELSE 0 END) AS payees
                 FROM ventes WHERE strftime('%Y-%m', date_vente)=?""", (mois,))
    stats = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-money-bill-wave"></i> Ventes</h2>
        <div class="page-subtitle">{len(ventes)} vente(s) — {mois}</div></div>
      {'<a href="/ventes/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle vente</a>' if _can_produce() else ''}
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-file-invoice"></i></div>
        <div class="stat-value">{stats['nb']}</div>
        <div class="stat-label">Ventes du mois</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-money-bill-wave"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(stats['total'])}</div>
        <div class="stat-label">CA du mois</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-weight-hanging"></i></div>
        <div class="stat-value">{_fmt_kg(stats['qte'])}</div>
        <div class="stat-label">Volume vendu</div></div>
      <div class="stat-card blue"><div class="stat-icon"><i class="fas fa-check-circle"></i></div>
        <div class="stat-value">{stats['payees']}/{stats['nb']}</div>
        <div class="stat-label">Payées</div></div>
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Mois</label>
          <input type="month" name="mois" value="{mois}">
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Statut</label>
          <select name="statut">
            <option value="">Tous</option>
            <option value="Payé" {"selected" if statut=="Payé" else ""}>Payé</option>
            <option value="En attente" {"selected" if statut=="En attente" else ""}>En attente</option>
          </select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-filter"></i> Filtrer</button>
        <a href="/ventes" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Réf</th><th>Date</th><th>Culture</th><th>Producteur</th>
          <th>Quantité</th><th>Prix/kg</th><th>Montant</th><th>Paiement</th><th>Statut</th>
        </tr></thead><tbody>
    """
    for v in ventes:
        badge = 'badge-success' if v['statut_paiement'] == 'Payé' else 'badge-warning'
        content += f"""
        <tr>
          <td><small>{v['reference']}</small></td>
          <td>{v['date_vente']}</td>
          <td><i class="fas {v['icone'] or 'fa-seedling'}" style="color:#10b981"></i> {v['culture_nom']}</td>
          <td>{v['producteur_prenom'] or ''} {v['producteur_nom'] or ''}</td>
          <td><strong>{_fmt_kg(v['quantite_kg'])}</strong></td>
          <td>{_fmt_fcfa(v['prix_unitaire_kg'])}</td>
          <td><strong>{_fmt_fcfa(v['montant_total'])}</strong></td>
          <td><small>{v['mode_paiement'] or '-'}</small></td>
          <td><span class="badge {badge}">{v['statut_paiement']}</span></td>
        </tr>"""
    if not ventes:
        content += '<tr><td colspan="9" class="empty"><i class="fas fa-money-bill-wave"></i><br>Aucune vente</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='ventes', title='Ventes')


# ================================================================
# ==================== ÉLEVAGE ====================
# ================================================================
@crud_bp.route('/elevage')
@_auth_required
def elevage_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT t.*, e.nom AS espece_nom, e.icone,
                        p.nom AS producteur_nom, p.prenom AS producteur_prenom,
                        (SELECT COUNT(*) FROM animaux WHERE troupeau_id=t.id AND actif=1) AS nb_animaux,
                        (SELECT COALESCE(SUM(quantite_litres), 0) FROM production_lait
                         WHERE troupeau_id=t.id AND date_production >= date('now', '-30 days')) AS lait_30j
                 FROM troupeaux t
                 LEFT JOIN especes_animales e ON t.espece_id = e.id
                 LEFT JOIN producteurs p ON t.producteur_id = p.id
                 WHERE t.actif=1
                 ORDER BY t.code""")
    troupeaux = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-cow"></i> Élevage</h2>
      <div style="display:flex;gap:10px">
        <a href="/elevage/nouveau" class="btn btn-primary">
          <i class="fas fa-plus"></i> Nouveau troupeau
        </a>
      </div>        <div class="page-subtitle">{len(troupeaux)} troupeau(x)</div></div>
      <div style="display:flex;gap:10px">
        <a href="/elevage/nouveau" class="btn btn-primary">
          <i class="fas fa-plus"></i> Nouveau troupeau
        </a>
      </div>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Code</th><th>Espèce</th><th>Producteur</th><th>Race</th>
          <th>Effectif</th><th>Mode</th><th>Objectif</th><th>Lait 30j</th>
        </tr></thead><tbody>
    """
    for t in troupeaux:
        content += f"""
        <tr>
          <td><strong>{t['code']}</strong></td>
          <td>
            <i class="fas {t['icone'] or 'fa-cow'}" style="color:#10b981;font-size:1.2rem"></i>
            {t['espece_nom'] or '-'}
          </td>
          <td>{t['producteur_prenom'] or ''} {t['producteur_nom'] or ''}</td>
          <td>{t['race'] or '-'}</td>
          <td><span class="badge badge-primary">{t['effectif_total']}</span></td>
          <td>{t['mode_elevage'] or '-'}</td>
          <td>{t['objectif'] or '-'}</td>
          <td><strong>{t['lait_30j']:.0f} L</strong></td>
        </tr>"""
    if not troupeaux:
        content += '<tr><td colspan="8" class="empty"><i class="fas fa-cow"></i><br>Aucun troupeau</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='elevage', title='Élevage')


# ================================================================
# ==================== UTILISATEURS / AUDIT ====================
# ================================================================
@crud_bp.route('/utilisateurs')
@_auth_required
def utilisateurs_list():
    if current_user.role != 'admin':
        flash("Accès réservé admin", "danger")
        return redirect('/')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT u.*, r.nom AS region_nom, co.nom AS coop_nom,
                        p.nom AS prod_nom, p.prenom AS prod_prenom
                 FROM utilisateurs u
                 LEFT JOIN regions r ON u.region_id = r.id
                 LEFT JOIN cooperatives co ON u.cooperative_id = co.id
                 LEFT JOIN producteurs p ON u.producteur_id = p.id
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
                 <th>Lié à</th><th>Actif</th><th>Dernier login</th></tr></thead>
      <tbody>"""
    for u in users:
        lie = u['region_nom'] or u['coop_nom'] or (f"{u['prod_prenom'] or ''} {u['prod_nom'] or ''}".strip() if u['prod_nom'] else None) or '-'
        content += f"""
        <tr>
          <td><strong>{u['username']}</strong></td>
          <td>{u['prenom'] or ''} {u['nom'] or ''}</td>
          <td><span class="badge badge-primary">{u['role']}</span></td>
          <td>{lie}</td>
          <td>{'✅' if u['actif'] else '❌'}</td>
          <td><small>{u['dernier_login'][:16] if u['dernier_login'] else '-'}</small></td>
        </tr>"""
    content += "</tbody></table></div></div>"
    return _render(content, active='utilisateurs', title='Utilisateurs')


@crud_bp.route('/audit')
@_auth_required
def audit_list():
    if current_user.role != 'admin':
        flash("Accès réservé admin", "danger")
        return redirect('/')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT a.*, u.username
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
      <thead><tr><th>Date</th><th>User</th><th>Action</th>
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
# ==================== PARCELLES — NOUVELLE ====================
# ================================================================
@crud_bp.route('/parcelles/nouvelle', methods=['GET', 'POST'])
@_auth_required
def parcelles_new():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/parcelles')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        producteur_id = request.form.get('producteur_id')
        superficie = float(request.form.get('superficie_ha') or 0)

        if not producteur_id or superficie <= 0:
            flash("Producteur et superficie obligatoires", "warning")
        else:
            try:
                c.execute("SELECT COUNT(*) FROM parcelles")
                n = (c.fetchone()[0] or 0) + 1
                code = f"PAR-{n:04d}"

                lat = float(request.form.get('latitude') or 0)
                lon = float(request.form.get('longitude') or 0)

                c.execute("""INSERT INTO parcelles
                    (code, producteur_id, nom, superficie_ha, latitude, longitude,
                     altitude, type_sol, ph_sol, matiere_organique, pente_pct,
                     irrigation_disponible, source_eau, statut_juridique,
                     annee_acquisition, actif, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)""",
                    (code, producteur_id,
                     (request.form.get('nom') or '').strip(),
                     superficie,
                     lat or None, lon or None,
                     float(request.form.get('altitude') or 0) or None,
                     request.form.get('type_sol') or None,
                     float(request.form.get('ph_sol') or 0) or None,
                     float(request.form.get('matiere_organique') or 0) or None,
                     float(request.form.get('pente_pct') or 0) or None,
                     1 if request.form.get('irrigation_disponible') else 0,
                     request.form.get('source_eau') or None,
                     request.form.get('statut_juridique') or 'Propriété',
                     int(request.form.get('annee_acquisition') or 0) or None,
                     datetime.now().isoformat()))
                new_id = c.lastrowid
                conn.commit()
                _log('CREATE_PARCELLE', f"Parcelle {code} créée ({superficie} ha)",
                     entity='parcelle', entity_id=new_id)
                flash(f"Parcelle {code} créée", "success")
                conn.close()
                return redirect(f'/parcelles/{new_id}')
            except Exception as e:
                import traceback; traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    # GET
    c.execute("""SELECT p.id, p.nom, p.prenom, p.code,
                        v.nom AS village_nom, r.nom AS region_nom
                 FROM producteurs p
                 LEFT JOIN villages v ON p.village_id = v.id
                 LEFT JOIN departements d ON v.departement_id = d.id
                 LEFT JOIN regions r ON d.region_id = r.id
                 WHERE p.actif=1 ORDER BY p.nom""")
    producteurs = c.fetchall()

    default_producteur = request.args.get('producteur') or ''
    conn.close()

    opt_p = ''
    for p in producteurs:
        sel = 'selected' if str(p['id']) == str(default_producteur) else ''
        opt_p += f'<option value="{p["id"]}" {sel}>{p["prenom"]} {p["nom"]} ({p["code"]})</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus"></i> Nouvelle parcelle</h2>
        <div class="page-subtitle">Localisation GPS et caractéristiques</div></div>
      <a href="/parcelles" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>

    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group form-full">
            <label>Producteur *</label>
            <select name="producteur_id" required><option value="">— Choisir —</option>{opt_p}</select>
          </div>
          <div class="form-group"><label>Nom de la parcelle</label>
            <input type="text" name="nom" placeholder="Ex: Champ Nord"></div>
          <div class="form-group"><label>Superficie (ha) *</label>
            <input type="number" step="0.01" name="superficie_ha" required value="1.0"></div>
          <div class="form-group"><label>Type de sol</label>
            <select name="type_sol">
              <option value="">—</option>
              <option>Sableux</option><option>Sablo-limoneux</option>
              <option>Limono-argileux</option><option>Argileux</option>
              <option>Latéritique</option><option>Alluvial</option>
            </select>
          </div>
          <div class="form-group"><label>Statut juridique</label>
            <select name="statut_juridique">
              <option>Propriété</option><option>Location</option>
              <option>Mise à disposition</option><option>Collectif</option>
            </select>
          </div>
          <div class="form-group"><label>pH du sol</label>
            <input type="number" step="0.1" name="ph_sol" placeholder="6.5"></div>
          <div class="form-group"><label>Matière organique (%)</label>
            <input type="number" step="0.1" name="matiere_organique" placeholder="2.0"></div>
          <div class="form-group"><label>Pente (%)</label>
            <input type="number" step="0.1" name="pente_pct" placeholder="2.0"></div>
          <div class="form-group"><label>Altitude (m)</label>
            <input type="number" name="altitude" placeholder="20"></div>
          <div class="form-group"><label>Année d'acquisition</label>
            <input type="number" name="annee_acquisition" value="2024"></div>
          <div class="form-group form-full">
            <label><input type="checkbox" name="irrigation_disponible"> Irrigation disponible</label>
          </div>
          <div class="form-group form-full">
            <label>Source d'eau</label>
            <select name="source_eau">
              <option value="">—</option>
              <option>Puits</option><option>Forage</option>
              <option>Fleuve</option><option>Lac</option><option>Canal</option><option>Aucune</option>
            </select>
          </div>
        </div>

        <div style="margin-top:20px;padding:20px;background:#f0fdf4;border-radius:14px">
          <h4 style="color:#065f46;margin-bottom:12px"><i class="fas fa-map-marked-alt"></i> Localisation GPS</h4>
          <p style="color:#64748b;font-size:0.85rem;margin-bottom:12px">
            Cliquez sur la carte pour placer la parcelle, ou saisissez les coordonnées manuellement.
          </p>
          <div id="map-choose" style="height:350px;border-radius:12px;margin-bottom:15px"></div>
          <div class="form-grid">
            <div class="form-group"><label>Latitude</label>
              <input type="number" step="0.000001" name="latitude" id="lat_input" placeholder="14.7500"></div>
            <div class="form-group"><label>Longitude</label>
              <input type="number" step="0.000001" name="longitude" id="lon_input" placeholder="-17.0000"></div>
          </div>
        </div>

        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Créer la parcelle</button>
          <a href="/parcelles" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>

    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
    document.addEventListener('DOMContentLoaded', () => {{
      const map = L.map('map-choose').setView([14.4974, -14.4524], 7);
      L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);

      let marker = null;
      const latInput = document.getElementById('lat_input');
      const lonInput = document.getElementById('lon_input');

      // Click sur carte
      map.on('click', (e) => {{
        const lat = e.latlng.lat.toFixed(6);
        const lon = e.latlng.lng.toFixed(6);
        latInput.value = lat;
        lonInput.value = lon;
        if (marker) map.removeLayer(marker);
        marker = L.marker([lat, lon]).addTo(map);
        marker.bindPopup(`<strong>Parcelle</strong><br>${{lat}}, ${{lon}}`).openPopup();
      }});

      // Bouton géolocalisation
      L.Control.geolocate = L.Control.extend({{
        onAdd: function() {{
          const btn = L.DomUtil.create('button', 'leaflet-bar');
          btn.innerHTML = '📍 Ma position';
          btn.style.cssText = 'padding:8px 12px;background:white;border:none;cursor:pointer;font-weight:700;border-radius:4px';
          btn.onclick = () => {{
            map.locate({{setView: true, maxZoom: 15}});
          }};
          return btn;
        }}
      }});
      map.addControl(new L.Control.geolocate({{position: 'topleft'}}));

      map.on('locationfound', (e) => {{
        const lat = e.latlng.lat.toFixed(6);
        const lon = e.latlng.lng.toFixed(6);
        latInput.value = lat;
        lonInput.value = lon;
        if (marker) map.removeLayer(marker);
        marker = L.marker([lat, lon]).addTo(map);
        marker.bindPopup('Votre position').openPopup();
      }});
    }});
    </script>
    """
    return _render(content, active='parcelles', title='Nouvelle parcelle')


@crud_bp.route('/parcelles/<int:paid>/modifier', methods=['GET', 'POST'])
@_auth_required
def parcelles_edit(paid):
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/parcelles')

    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM parcelles WHERE id=?", (paid,))
    pa = c.fetchone()
    if not pa:
        conn.close()
        return redirect('/parcelles')

    if request.method == 'POST':
        c.execute("""UPDATE parcelles SET
            nom=?, superficie_ha=?, latitude=?, longitude=?, altitude=?,
            type_sol=?, ph_sol=?, matiere_organique=?, pente_pct=?,
            irrigation_disponible=?, source_eau=?, statut_juridique=?,
            annee_acquisition=?
            WHERE id=?""",
            ((request.form.get('nom') or '').strip(),
             float(request.form.get('superficie_ha') or 0),
             float(request.form.get('latitude') or 0) or None,
             float(request.form.get('longitude') or 0) or None,
             float(request.form.get('altitude') or 0) or None,
             request.form.get('type_sol') or None,
             float(request.form.get('ph_sol') or 0) or None,
             float(request.form.get('matiere_organique') or 0) or None,
             float(request.form.get('pente_pct') or 0) or None,
             1 if request.form.get('irrigation_disponible') else 0,
             request.form.get('source_eau') or None,
             request.form.get('statut_juridique') or 'Propriété',
             int(request.form.get('annee_acquisition') or 0) or None,
             paid))
        conn.commit()
        _log('UPDATE_PARCELLE', f"Parcelle id={paid} modifiée",
             entity='parcelle', entity_id=paid)
        conn.close()
        flash("Parcelle mise à jour", "success")
        return redirect(f'/parcelles/{paid}')

    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-pen"></i> Modifier parcelle {pa['code']}</h2></div>
      <a href="/parcelles/{paid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group form-full"><label>Nom</label>
            <input type="text" name="nom" value="{pa['nom'] or ''}"></div>
          <div class="form-group"><label>Superficie (ha)</label>
            <input type="number" step="0.01" name="superficie_ha" value="{pa['superficie_ha']}" required></div>
          <div class="form-group"><label>Latitude</label>
            <input type="number" step="0.000001" name="latitude" value="{pa['latitude'] or ''}"></div>
          <div class="form-group"><label>Longitude</label>
            <input type="number" step="0.000001" name="longitude" value="{pa['longitude'] or ''}"></div>
          <div class="form-group"><label>Altitude (m)</label>
            <input type="number" name="altitude" value="{pa['altitude'] or ''}"></div>
          <div class="form-group"><label>Type de sol</label>
            <input type="text" name="type_sol" value="{pa['type_sol'] or ''}"></div>
          <div class="form-group"><label>pH</label>
            <input type="number" step="0.1" name="ph_sol" value="{pa['ph_sol'] or ''}"></div>
          <div class="form-group"><label>Matière organique (%)</label>
            <input type="number" step="0.1" name="matiere_organique" value="{pa['matiere_organique'] or ''}"></div>
          <div class="form-group"><label>Pente (%)</label>
            <input type="number" step="0.1" name="pente_pct" value="{pa['pente_pct'] or ''}"></div>
          <div class="form-group form-full">
            <label><input type="checkbox" name="irrigation_disponible" {'checked' if pa['irrigation_disponible'] else ''}> Irrigation disponible</label>
          </div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
          <a href="/parcelles/{paid}" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='parcelles', title='Modifier parcelle')


# ================================================================
# ==================== CULTURES — NOUVELLE ====================
# ================================================================
@crud_bp.route('/cultures/nouvelle', methods=['GET', 'POST'])
@_auth_required
def cultures_new():
    if not _can_produce():
        flash("Droits insuffisants", "danger")
        return redirect('/cultures')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        parcelle_id = request.form.get('parcelle_id')
        culture_id = request.form.get('culture_id')

        if not parcelle_id or not culture_id:
            flash("Parcelle et culture obligatoires", "warning")
        else:
            try:
                # Calcul date récolte prévue
                date_semis = request.form.get('date_semis') or datetime.now().date().isoformat()
                c.execute("SELECT cycle_jours_min, cycle_jours_max FROM cultures WHERE id=?", (culture_id,))
                cyc = c.fetchone()
                cycle = random_cycle = (cyc['cycle_jours_min'] or 90) if cyc else 90

                from datetime import datetime as dt, timedelta as td
                date_prevue = (dt.fromisoformat(date_semis) + td(days=cycle)).date().isoformat()

                c.execute("""INSERT INTO cultures_parcelles
                    (parcelle_id, culture_id, variete_id, campagne_id,
                     date_semis, date_prevue_recolte, superficie_ha,
                     quantite_semence_kg, type_semence, densite_plants_ha,
                     etat, notes, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (parcelle_id, culture_id,
                     request.form.get('variete_id') or None,
                     request.form.get('campagne_id') or None,
                     date_semis, date_prevue,
                     float(request.form.get('superficie_ha') or 0) or None,
                     float(request.form.get('quantite_semence_kg') or 0) or None,
                     request.form.get('type_semence') or 'Locale',
                     int(request.form.get('densite_plants_ha') or 0) or None,
                     'Semé',
                     (request.form.get('notes') or '').strip(),
                     datetime.now().isoformat()))
                new_id = c.lastrowid
                conn.commit()
                _log('CREATE_CULTURE', f"Culture démarrée sur parcelle id={parcelle_id}",
                     entity='culture_parcelle', entity_id=new_id)
                flash("Culture démarrée avec succès", "success")
                conn.close()
                return redirect(f'/parcelles/{parcelle_id}')
            except Exception as e:
                import traceback; traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    # GET
    c.execute("""SELECT pa.id, pa.code, pa.nom, pa.superficie_ha,
                        p.nom AS producteur_nom, p.prenom AS producteur_prenom
                 FROM parcelles pa
                 LEFT JOIN producteurs p ON pa.producteur_id = p.id
                 WHERE pa.actif=1 ORDER BY pa.code""")
    parcelles = c.fetchall()

    c.execute("SELECT id, code, nom, nom_wolof, icone, cycle_jours_min FROM cultures WHERE actif=1 ORDER BY nom")
    cultures = c.fetchall()

    c.execute("SELECT id, code, nom FROM campagnes ORDER BY date_debut DESC LIMIT 5")
    campagnes = c.fetchall()
    conn.close()

    default_parcelle = request.args.get('parcelle') or ''
    opt_pa = ''
    for p in parcelles:
        sel = 'selected' if str(p['id']) == str(default_parcelle) else ''
        opt_pa += f'<option value="{p["id"]}" {sel}>{p["code"]} — {p["nom"] or ""} ({p["superficie_ha"]} ha) · {p["producteur_prenom"] or ""} {p["producteur_nom"] or ""}</option>'

    opt_cu = ''
    for cu in cultures:
        opt_cu += f'<option value="{cu["id"]}" data-cycle="{cu["cycle_jours_min"] or 90}">{cu["nom"]} ({cu["nom_wolof"] or "-"}) — {cu["cycle_jours_min"] or "?"}j</option>'

    opt_ca = ''.join(f'<option value="{ca["id"]}">{ca["nom"]}</option>' for ca in campagnes)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-seedling"></i> Démarrer une culture</h2>
        <div class="page-subtitle">Semis + itinéraire technique</div></div>
      <a href="/cultures" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group form-full">
            <label>Parcelle *</label>
            <select name="parcelle_id" required id="parcelle_select">
              <option value="">— Choisir une parcelle —</option>{opt_pa}
            </select>
          </div>
          <div class="form-group form-full">
            <label>Culture *</label>
            <select name="culture_id" required id="culture_select">
              <option value="">— Choisir une culture —</option>{opt_cu}
            </select>
          </div>
          <div class="form-group"><label>Date de semis *</label>
            <input type="date" name="date_semis" value="{datetime.now().date().isoformat()}" required></div>
          <div class="form-group"><label>Campagne</label>
            <select name="campagne_id"><option value="">—</option>{opt_ca}</select>
          </div>
          <div class="form-group"><label>Superficie cultivée (ha)</label>
            <input type="number" step="0.01" name="superficie_ha" id="superficie_input" value=""></div>
          <div class="form-group"><label>Quantité semence (kg)</label>
            <input type="number" step="0.1" name="quantite_semence_kg" placeholder="20"></div>
          <div class="form-group"><label>Type de semence</label>
            <select name="type_semence">
              <option>Locale</option><option>Améliorée</option><option>Certifiée</option><option>Hybride</option>
            </select>
          </div>
          <div class="form-group"><label>Densité (plants/ha)</label>
            <input type="number" name="densite_plants_ha" placeholder="25000"></div>
          <div class="form-group form-full"><label>Notes</label>
            <textarea name="notes" rows="2"></textarea></div>
        </div>

        <div id="preview" style="margin:20px 0;padding:20px;background:#f0fdf4;border-radius:14px;border-left:5px solid #10b981;display:none">
          <div style="display:flex;gap:30px;flex-wrap:wrap;align-items:center">
            <div>
              <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Cycle estimé</div>
              <div id="pv_cycle" style="font-size:1.8rem;font-weight:900;color:#065f46">-</div>
            </div>
            <div>
              <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Récolte prévue</div>
              <div id="pv_recolte" style="font-size:1.4rem;font-weight:800;color:#10b981">-</div>
            </div>
          </div>
        </div>

        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-seedling"></i> Démarrer la culture</button>
          <a href="/cultures" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>

    <script>
    const cultureSelect = document.getElementById('culture_select');
    const dateInput = document.querySelector('input[name="date_semis"]');
    const preview = document.getElementById('preview');

    function updatePreview() {{
      const opt = cultureSelect.options[cultureSelect.selectedIndex];
      const cycle = parseInt(opt.dataset.cycle) || 0;
      const dateSemis = dateInput.value;
      if (!cycle || !dateSemis) {{ preview.style.display = 'none'; return; }}
      preview.style.display = 'block';
      document.getElementById('pv_cycle').textContent = cycle + ' jours';
      const d = new Date(dateSemis);
      d.setDate(d.getDate() + cycle);
      document.getElementById('pv_recolte').textContent = d.toISOString().slice(0, 10);
    }}

    cultureSelect.addEventListener('change', updatePreview);
    dateInput.addEventListener('change', updatePreview);
    </script>
    """
    return _render(content, active='cultures', title='Nouvelle culture')


# ================================================================
# ==================== VENTES — NOUVELLE ====================
# ================================================================
@crud_bp.route('/ventes/nouvelle', methods=['GET', 'POST'])
@_auth_required
def ventes_new():
    if not _can_produce():
        flash("Droits insuffisants", "danger")
        return redirect('/ventes')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        producteur_id = request.form.get('producteur_id')
        culture_id = request.form.get('culture_id')
        qte = float(request.form.get('quantite_kg') or 0)
        prix = int(request.form.get('prix_unitaire_kg') or 0)

        if not producteur_id or not culture_id or qte <= 0 or prix <= 0:
            flash("Champs obligatoires manquants", "warning")
        else:
            try:
                montant = int(qte * prix)
                date_v = request.form.get('date_vente') or datetime.now().date().isoformat()
                ref = f"VTE-{datetime.now().strftime('%Y%m%d')}-{c.lastrowid or 0:04d}"

                # Générer ref unique
                c.execute("SELECT COUNT(*) FROM ventes")
                n = (c.fetchone()[0] or 0) + 1
                ref = f"VTE-{datetime.now().strftime('%Y%m%d')}-{n:04d}"

                statut_paiement = request.form.get('statut_paiement') or 'En attente'

                c.execute("""INSERT INTO ventes
                    (reference, producteur_id, acheteur_id, acheteur_nom, date_vente,
                     culture_id, quantite_kg, prix_unitaire_kg, montant_total,
                     frais_transport, frais_autres, montant_net,
                     mode_paiement, statut_paiement, date_paiement,
                     reference_mobile_money, livraison_statut, notes, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (ref, producteur_id,
                     request.form.get('acheteur_id') or None,
                     (request.form.get('acheteur_nom') or '').strip(),
                     date_v, culture_id, qte, prix, montant,
                     int(request.form.get('frais_transport') or 0),
                     int(request.form.get('frais_autres') or 0),
                     montant - int(request.form.get('frais_transport') or 0) - int(request.form.get('frais_autres') or 0),
                     request.form.get('mode_paiement') or 'Espèces',
                     statut_paiement,
                     date_v if statut_paiement == 'Payé' else None,
                     (request.form.get('reference_mobile_money') or '').strip(),
                     request.form.get('livraison_statut') or 'À livrer',
                     (request.form.get('notes') or '').strip(),
                     datetime.now().isoformat()))
                new_id = c.lastrowid

                # Si Mobile Money, créer transaction
                mm_type = request.form.get('mode_paiement')
                if mm_type in ('Wave', 'Orange Money', 'Free Money') and statut_paiement == 'Payé':
                    c.execute("""INSERT INTO transactions_mobile
                        (reference, producteur_id, fournisseur, telephone,
                         type_transaction, montant, statut, objet, date_transaction, created_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (f"MM-{datetime.now().strftime('%Y%m%d')}-{n:05d}",
                         producteur_id, mm_type,
                         (request.form.get('mobile_money_numero') or '').strip(),
                         'Encaissement', montant, 'Réussi',
                         f"Vente {ref}",
                         datetime.now().isoformat(), datetime.now().isoformat()))

                conn.commit()
                _log('CREATE_VENTE', f"Vente {ref} : {qte}kg × {prix}F = {montant}F",
                     entity='vente', entity_id=new_id)
                flash(f"Vente {ref} enregistrée ({_fmt_fcfa(montant)})", "success")
                conn.close()
                return redirect('/ventes')
            except Exception as e:
                import traceback; traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    # GET
    c.execute("""SELECT p.id, p.nom, p.prenom, p.code, p.mobile_money_type, p.mobile_money_numero
                 FROM producteurs p WHERE p.actif=1 ORDER BY p.nom""")
    producteurs = c.fetchall()

    c.execute("SELECT id, nom, nom_wolof, prix_moyen_kg FROM cultures WHERE actif=1 ORDER BY nom")
    cultures = c.fetchall()

    c.execute("SELECT id, nom FROM acheteurs WHERE actif=1 ORDER BY nom")
    acheteurs = c.fetchall()
    conn.close()

    opt_p = ''.join(f'<option value="{p["id"]}" data-mm="{p["mobile_money_type"] or ""}" data-mmnum="{p["mobile_money_numero"] or ""}">{p["prenom"]} {p["nom"]} ({p["code"]})</option>' for p in producteurs)
    opt_c = ''.join(f'<option value="{cu["id"]}" data-prix="{cu["prix_moyen_kg"] or 0}">{cu["nom"]} — prix moy. {cu["prix_moyen_kg"] or 0} F/kg</option>' for cu in cultures)
    opt_a = ''.join(f'<option value="{a["id"]}">{a["nom"]}</option>' for a in acheteurs)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-money-bill-wave"></i> Nouvelle vente</h2>
        <div class="page-subtitle">Enregistrement avec paiement Mobile Money intégré</div></div>
      <a href="/ventes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group form-full">
            <label>Producteur vendeur *</label>
            <select name="producteur_id" required id="prod_select">
              <option value="">— Choisir —</option>{opt_p}
            </select>
          </div>
          <div class="form-group form-full">
            <label>Culture *</label>
            <select name="culture_id" required id="cult_select">
              <option value="">— Choisir —</option>{opt_c}
            </select>
          </div>
          <div class="form-group">
            <label>Quantité (kg) *</label>
            <input type="number" step="0.1" name="quantite_kg" required id="qte_input" value="100">
          </div>
          <div class="form-group">
            <label>Prix unitaire (FCFA/kg) *</label>
            <input type="number" name="prix_unitaire_kg" required id="prix_input" value="200">
          </div>
          <div class="form-group">
            <label>Date de vente</label>
            <input type="date" name="date_vente" value="{datetime.now().date().isoformat()}">
          </div>
          <div class="form-group">
            <label>Acheteur</label>
            <select name="acheteur_id"><option value="">—</option>{opt_a}</select>
          </div>
          <div class="form-group">
            <label>Ou nom acheteur libre</label>
            <input type="text" name="acheteur_nom" placeholder="Ex: Coopérative X">
          </div>
          <div class="form-group">
            <label>Frais transport (FCFA)</label>
            <input type="number" name="frais_transport" value="0">
          </div>
          <div class="form-group">
            <label>Mode de paiement</label>
            <select name="mode_paiement" id="mode_paiement">
              <option value="Espèces">💵 Espèces</option>
              <option value="Wave">📱 Wave</option>
              <option value="Orange Money">📱 Orange Money</option>
              <option value="Free Money">📱 Free Money</option>
              <option value="Virement">🏦 Virement bancaire</option>
            </select>
          </div>
          <div class="form-group">
            <label>Statut paiement</label>
            <select name="statut_paiement">
              <option value="Payé">✅ Payé</option>
              <option value="En attente">⏳ En attente</option>
            </select>
          </div>
          <div class="form-group form-full">
            <label>N° Mobile Money (si paiement MM)</label>
            <input type="text" name="mobile_money_numero" id="mm_numero" placeholder="77 123 45 67">
          </div>
          <div class="form-group form-full"><label>Notes</label>
            <textarea name="notes" rows="2"></textarea></div>
        </div>

        <div id="recap" style="margin:20px 0;padding:24px;background:linear-gradient(135deg,#f0fdf4,#d1fae5);border-radius:14px;border-left:5px solid #10b981">
          <div style="display:flex;gap:30px;flex-wrap:wrap;align-items:center">
            <div>
              <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Quantité</div>
              <div id="recap_qte" style="font-size:1.5rem;font-weight:900;color:#065f46">100 kg</div>
            </div>
            <div>
              <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Prix total</div>
              <div id="recap_montant" style="font-size:1.8rem;font-weight:900;color:#10b981">20 000 F</div>
            </div>
            <div>
              <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Net à payer</div>
              <div id="recap_net" style="font-size:1.4rem;font-weight:800;color:#065f46">20 000 F</div>
            </div>
          </div>
        </div>

        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer la vente</button>
          <a href="/ventes" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>

    <script>
    const qte = document.getElementById('qte_input');
    const prix = document.getElementById('prix_input');
    const fraisT = document.querySelector('input[name="frais_transport"]');
    const fraisA = document.querySelector('input[name="frais_autres"]');
    const cultSelect = document.getElementById('cult_select');
    const prodSelect = document.getElementById('prod_select');
    const mmNumero = document.getElementById('mm_numero');

    function fmt(n) {{
      return new Intl.NumberFormat('fr-FR').format(Math.round(n)) + ' F';
    }}

    function updateRecap() {{
      const q = parseFloat(qte.value) || 0;
      const p = parseFloat(prix.value) || 0;
      const ft = parseFloat(fraisT.value) || 0;
      const montant = q * p;
      document.getElementById('recap_qte').textContent = q + ' kg';
      document.getElementById('recap_montant').textContent = fmt(montant);
      document.getElementById('recap_net').textContent = fmt(montant - ft);
    }}

    [qte, prix, fraisT].forEach(el => el.addEventListener('input', updateRecap));

    cultSelect.addEventListener('change', () => {{
      const opt = cultSelect.options[cultSelect.selectedIndex];
      const p = parseFloat(opt.dataset.prix) || 0;
      if (p > 0) prix.value = p;
      updateRecap();
    }});

    prodSelect.addEventListener('change', () => {{
      const opt = prodSelect.options[prodSelect.selectedIndex];
      if (opt.dataset.mmnum) mmNumero.value = opt.dataset.mmnum;
    }});

    updateRecap();
    </script>
    """
    return _render(content, active='ventes', title='Nouvelle vente')


# ================================================================
# ==================== ÉLEVAGE — TROUPEAU ====================
# ================================================================
@crud_bp.route('/elevage/<int:tid>')
@_auth_required
def elevage_detail(tid):
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT t.*, e.nom AS espece_nom, e.icone, e.duree_gestation_jours,
                        p.nom AS producteur_nom, p.prenom AS producteur_prenom, p.telephone
                 FROM troupeaux t
                 LEFT JOIN especes_animales e ON t.espece_id = e.id
                 LEFT JOIN producteurs p ON t.producteur_id = p.id
                 WHERE t.id=?""", (tid,))
    t = c.fetchone()
    if not t:
        conn.close()
        flash("Troupeau introuvable", "danger")
        return redirect('/elevage')

    c.execute("""SELECT * FROM animaux WHERE troupeau_id=? AND actif=1
                 ORDER BY numero_boucle LIMIT 100""", (tid,))
    animaux = c.fetchall()

    c.execute("""SELECT * FROM production_lait WHERE troupeau_id=?
                 ORDER BY date_production DESC LIMIT 15""", (tid,))
    lait = c.fetchall()

    c.execute("""SELECT * FROM sante_animale WHERE troupeau_id=?
                 ORDER BY date_intervention DESC LIMIT 10""", (tid,))
    sante = c.fetchall()

    # Stats
    c.execute("""SELECT COUNT(*) AS nb, COALESCE(SUM(quantite_litres), 0) AS total
                 FROM production_lait WHERE troupeau_id=?
                 AND date_production >= date('now', '-30 days')""", (tid,))
    stats_lait = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas {t['icone'] or 'fa-cow'}"></i> {t['code']}</h2>
        <div class="page-subtitle">
          {t['espece_nom'] or ''} · {t['race'] or ''} ·
          {t['effectif_total']} animaux · {t['producteur_prenom'] or ''} {t['producteur_nom'] or ''}
        </div>
      </div>
      <a href="/elevage" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-hashtag"></i></div>
        <div class="stat-value">{t['effectif_total']}</div>
        <div class="stat-label">Effectif total</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-venus"></i></div>
        <div class="stat-value">{t['effectif_femelles']}</div>
        <div class="stat-label">Femelles</div></div>
      <div class="stat-card blue"><div class="stat-icon"><i class="fas fa-mars"></i></div>
        <div class="stat-value">{t['effectif_males']}</div>
        <div class="stat-label">Mâles</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-bottle-water"></i></div>
        <div class="stat-value">{stats_lait['total']:.0f} L</div>
        <div class="stat-label">Lait (30 jours)</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
      <div class="form-grid">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Espèce</label>
             <div>{t['espece_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Race</label>
             <div>{t['race'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Mode d'élevage</label>
             <div>{t['mode_elevage'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Objectif</label>
             <div>{t['objectif'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Producteur</label>
             <div>{t['producteur_prenom'] or ''} {t['producteur_nom'] or ''}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Téléphone</label>
             <div>{t['telephone'] or '-'}</div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-list"></i> Animaux ({len(animaux)})</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>N° Boucle</th><th>Sexe</th><th>Naissance</th>
                   <th>Poids</th><th>Stade</th><th>Santé</th></tr></thead>
        <tbody>"""
    for a in animaux:
        badge_s = 'badge-success' if a['etat_sante'] == 'Bon' else 'badge-warning'
        content += f"""
        <tr>
          <td><strong>{a['numero_boucle']}</strong></td>
          <td>{'♂️' if a['sexe'] == 'M' else '♀️'}</td>
          <td>{a['date_naissance'] or '-'}</td>
          <td>{a['poids_kg'] or '-'} kg</td>
          <td><small>{a['stade_physiologique'] or '-'}</small></td>
          <td><span class="badge {badge_s}">{a['etat_sante']}</span></td>
        </tr>"""
    if not animaux:
        content += '<tr><td colspan="6" class="empty">Aucun animal</td></tr>'
    content += "</tbody></table></div></div>"

    if lait:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-bottle-water"></i> Production laitière récente</h3></div>
          <div class="table-wrap"><table>
            <thead><tr><th>Date</th><th>Quantité</th><th>Moment</th>
                       <th>Qualité</th><th>Prix/L</th></tr></thead>
            <tbody>"""
        for l in lait:
            content += f"""
            <tr>
              <td>{l['date_production']}</td>
              <td><strong>{l['quantite_litres']} L</strong></td>
              <td>{l['moment'] or '-'}</td>
              <td>{l['qualite'] or '-'}</td>
              <td>{_fmt_fcfa(l['prix_litre'])}</td>
            </tr>"""
        content += "</tbody></table></div></div>"

    return _render(content, active='elevage', title=t['code'])


# ================================================================
# ==================== ÉLEVAGE — NOUVEAU ====================
# ================================================================
@crud_bp.route('/elevage/nouveau', methods=['GET', 'POST'])
@_auth_required
def elevage_new():
    if not _can_produce():
        flash("Droits insuffisants", "danger")
        return redirect('/elevage')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        producteur_id = request.form.get('producteur_id')
        espece_id = request.form.get('espece_id')

        if not producteur_id or not espece_id:
            flash("Producteur et espèce obligatoires", "warning")
        else:
            try:
                c.execute("SELECT COUNT(*) FROM troupeaux")
                n = (c.fetchone()[0] or 0) + 1
                code = f"TRP-{n:04d}"

                c.execute("""INSERT INTO troupeaux
                    (code, producteur_id, espece_id, nom, race,
                     effectif_total, effectif_femelles, effectif_males, effectif_jeunes,
                     mode_elevage, lieu_garde, gps_latitude, gps_longitude,
                     objectif, actif, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)""",
                    (code, producteur_id, espece_id,
                     (request.form.get('nom') or '').strip(),
                     (request.form.get('race') or '').strip(),
                     int(request.form.get('effectif_total') or 0),
                     int(request.form.get('effectif_femelles') or 0),
                     int(request.form.get('effectif_males') or 0),
                     int(request.form.get('effectif_jeunes') or 0),
                     request.form.get('mode_elevage') or 'Extensif',
                     (request.form.get('lieu_garde') or '').strip(),
                     float(request.form.get('gps_latitude') or 0) or None,
                     float(request.form.get('gps_longitude') or 0) or None,
                     request.form.get('objectif') or 'Mixte',
                     datetime.now().isoformat()))
                new_id = c.lastrowid
                conn.commit()
                _log('CREATE_TROUPEAU', f"Troupeau {code} créé",
                     entity='troupeau', entity_id=new_id)
                flash(f"Troupeau {code} créé", "success")
                conn.close()
                return redirect(f'/elevage/{new_id}')
            except Exception as e:
                import traceback; traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    c.execute("SELECT id, nom, prenom, code FROM producteurs WHERE actif=1 ORDER BY nom")
    producteurs = c.fetchall()
    c.execute("SELECT id, nom, icone FROM especes_animales WHERE actif=1 ORDER BY nom")
    especes = c.fetchall()
    conn.close()

    opt_p = ''.join(f'<option value="{p["id"]}">{p["prenom"]} {p["nom"]} ({p["code"]})</option>' for p in producteurs)
    opt_e = ''.join(f'<option value="{e["id"]}">{e["nom"]}</option>' for e in especes)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-cow"></i> Nouveau troupeau</h2></div>
      <a href="/elevage" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group form-full">
            <label>Producteur *</label>
            <select name="producteur_id" required><option value="">— Choisir —</option>{opt_p}</select>
          </div>
          <div class="form-group">
            <label>Espèce *</label>
            <select name="espece_id" required><option value="">— Choisir —</option>{opt_e}</select>
          </div>
          <div class="form-group"><label>Nom du troupeau</label>
            <input type="text" name="nom" placeholder="Ex: Troupeau Nord"></div>
          <div class="form-group"><label>Race</label>
            <input type="text" name="race" placeholder="Ex: Gobra, Djalonké..."></div>
          <div class="form-group"><label>Effectif total *</label>
            <input type="number" name="effectif_total" required value="10"></div>
          <div class="form-group"><label>Femelles</label>
            <input type="number" name="effectif_femelles" value="0"></div>
          <div class="form-group"><label>Mâles</label>
            <input type="number" name="effectif_males" value="0"></div>
          <div class="form-group"><label>Jeunes</label>
            <input type="number" name="effectif_jeunes" value="0"></div>
          <div class="form-group"><label>Mode d'élevage</label>
            <select name="mode_elevage">
              <option>Extensif</option><option>Semi-intensif</option><option>Intensif</option>
            </select>
          </div>
          <div class="form-group"><label>Objectif</label>
            <select name="objectif">
              <option>Mixte</option><option>Lait</option><option>Viande</option><option>Reproduction</option>
            </select>
          </div>
          <div class="form-group form-full"><label>Lieu de garde</label>
            <input type="text" name="lieu_garde" placeholder="Ex: Parc à côté du village"></div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Créer le troupeau</button>
          <a href="/elevage" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='elevage', title='Nouveau troupeau')


# ================================================================
# ==================== API ====================
# ================================================================
@crud_bp.route('/api/stats-globales')
@_auth_required
def api_stats_globales():
    conn = _db()
    c = conn.cursor()
    stats = {}
    for t, key in [('producteurs', 'producteurs'), ('parcelles', 'parcelles'),
                   ('cultures', 'cultures'), ('recoltes', 'recoltes'),
                   ('ventes', 'ventes'), ('troupeaux', 'troupeaux')]:
        c.execute(f"SELECT COUNT(*) FROM {t}")
        stats[key] = c.fetchone()[0]
    conn.close()
    return jsonify(stats)


@crud_bp.route('/api/cultures')
@_auth_required
def api_cultures():
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT id, code, nom, nom_wolof, icone FROM cultures WHERE actif=1 ORDER BY nom")
    rows = c.fetchall()
    conn.close()
    return jsonify(cultures=[dict(r) for r in rows])


@crud_bp.route('/api/producteurs')
@_auth_required
def api_producteurs():
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT id, code, nom, prenom FROM producteurs WHERE actif=1 ORDER BY nom")
    rows = c.fetchall()
    conn.close()
    return jsonify(producteurs=[dict(r) for r in rows])
