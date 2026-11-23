"""
🌾 Omega Agro-Industrie — CRUD complet
Producteurs · Produits finis · Production · Stocks · Contrats · Fournisseurs
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


def _render(content, active='dashboard', title='Omega Agro'):
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
    return current_user and current_user.role in ('admin', 'directeur', 'production')


def _can_validate():
    return current_user and current_user.role in ('admin', 'directeur')


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


def _fmt_date(d):
    if not d:
        return "-"
    return d[:10] if len(d) >= 10 else d


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
    sql = """SELECT p.*, r.nom AS region_nom, co.nom AS coop_nom,
                    (SELECT COUNT(*) FROM parcelles WHERE producteur_id=p.id) AS nb_parcelles,
                    (SELECT COUNT(*) FROM recoltes WHERE producteur_id=p.id) AS nb_recoltes,
                    (SELECT COALESCE(SUM(quantite_kg), 0) FROM recoltes WHERE producteur_id=p.id) AS total_kg
             FROM producteurs p
             LEFT JOIN regions r ON p.region_id = r.id
             LEFT JOIN cooperatives co ON p.cooperative_id = co.id
             WHERE p.actif=1"""
    params = []
    if q:
        sql += " AND (p.nom LIKE ? OR p.prenom LIKE ? OR p.code LIKE ? OR p.telephone LIKE ?)"
        params += [f"%{q}%"] * 4
    if region_id:
        sql += " AND p.region_id=?"
        params.append(region_id)
    if coop_id:
        sql += " AND p.cooperative_id=?"
        params.append(coop_id)
    sql += " ORDER BY p.nom, p.prenom LIMIT 200"
    c.execute(sql, params)
    producteurs = c.fetchall()

    # Stats
    c.execute("SELECT COUNT(*) FROM producteurs WHERE actif=1")
    total = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(superficie_ha), 0) FROM producteurs WHERE actif=1")
    superficie = c.fetchone()[0] or 0

    c.execute("SELECT * FROM regions ORDER BY nom")
    regions = c.fetchall()
    c.execute("SELECT id, nom FROM cooperatives ORDER BY nom")
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
        <div class="page-subtitle">{len(producteurs)} producteur(s) · {superficie:.1f} ha</div></div>
      {'<a href="/producteurs/nouveau" class="btn btn-primary"><i class="fas fa-user-plus"></i> Nouveau producteur</a>' if _can_write() else ''}
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:2;margin:0;min-width:200px">
          <label>Recherche</label>
          <input type="text" name="q" value="{q}" placeholder="Nom, code, téléphone..." style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:180px">
          <label>Région</label>
          <select name="region" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">{opt_r}</select>
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:180px">
          <label>Coopérative</label>
          <select name="coop" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">{opt_c}</select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-search"></i> Filtrer</button>
        <a href="/producteurs" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Code</th><th>Producteur</th><th>Village/Région</th><th>Coopérative</th>
          <th>Parcelles</th><th>Production</th><th>Mobile Money</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for p in producteurs:
        initiales = f"{p['prenom'][0] if p['prenom'] else ''}{p['nom'][0] if p['nom'] else ''}"
        mm = ''
        if p['mobile_money_type']:
            color = '#10b981' if p['mobile_money_type'] == 'Wave' else ('#f97316' if p['mobile_money_type'] == 'Orange Money' else '#dc2626')
            mm = f'<span class="badge" style="background:{color}20;color:{color}">{p["mobile_money_type"]}</span>'

        content += f"""
        <tr>
          <td><strong>{p['code']}</strong></td>
          <td>
            <div style="display:flex;align-items:center;gap:10px">
              <div style="width:36px;height:36px;background:linear-gradient(135deg,#065f46,#10b981);border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-weight:800;font-size:0.85rem;flex-shrink:0">{initiales}</div>
              <div>
                <div style="font-weight:700">{p['prenom'] or ''} {p['nom']}</div>
                <div style="font-size:0.72rem;color:#94a3b8">{p['telephone'] or '-'}</div>
              </div>
            </div>
          </td>
          <td>
            <div>{p['village'] or '-'}</div>
            <div style="font-size:0.72rem;color:#94a3b8">{p['region_nom'] or '-'}</div>
          </td>
          <td>{p['coop_nom'] or '-'}</td>
          <td><span class="badge badge-primary">{p['nb_parcelles']}</span></td>
          <td><small>{_fmt_kg(p['total_kg'])}</small></td>
          <td>{mm}</td>
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
    c.execute("""SELECT p.*, r.nom AS region_nom, co.nom AS coop_nom
                 FROM producteurs p
                 LEFT JOIN regions r ON p.region_id = r.id
                 LEFT JOIN cooperatives co ON p.cooperative_id = co.id
                 WHERE p.id=?""", (pid,))
    p = c.fetchone()
    if not p:
        conn.close()
        flash("Producteur introuvable", "danger")
        return redirect('/producteurs')

    c.execute("SELECT * FROM parcelles WHERE producteur_id=? AND actif=1", (pid,))
    parcelles = c.fetchall()

    c.execute("""SELECT * FROM recoltes WHERE producteur_id=?
                 ORDER BY date_recolte DESC LIMIT 20""", (pid,))
    recoltes = c.fetchall()

    c.execute("""SELECT * FROM livraisons_producteurs WHERE producteur_id=?
                 ORDER BY date_livraison DESC LIMIT 20""", (pid,))
    livraisons = c.fetchall()

    c.execute("""SELECT * FROM contrats_achat WHERE producteur_id=?
                 ORDER BY date_signature DESC LIMIT 10""", (pid,))
    contrats = c.fetchall()

    # Stats
    c.execute("""SELECT COUNT(*) AS nb, COALESCE(SUM(quantite_kg), 0) AS total
                 FROM recoltes WHERE producteur_id=?""", (pid,))
    stats_rec = c.fetchone()

    conn.close()

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-user"></i> {p['prenom'] or ''} {p['nom']}</h2>
        <div class="page-subtitle">
          <strong>{p['code']}</strong> · {p['village'] or '-'}, {p['region_nom'] or '-'} ·
          {p['produits_agricoles'] or 'Producteur'}
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/producteurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        {'<a href="/producteurs/'+str(pid)+'/modifier" class="btn btn-warning"><i class="fas fa-pen"></i> Modifier</a>' if _can_write() else ''}
      </div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-draw-polygon"></i></div>
        <div class="stat-value">{len(parcelles)}</div>
        <div class="stat-label">Parcelles</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-ruler-combined"></i></div>
        <div class="stat-value">{p['superficie_ha'] or 0:.1f}</div>
        <div class="stat-label">Hectares</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-wheat-awn"></i></div>
        <div class="stat-value">{stats_rec['nb'] or 0}</div>
        <div class="stat-label">Récoltes</div></div>
      <div class="stat-card blue"><div class="stat-icon"><i class="fas fa-weight-hanging"></i></div>
        <div class="stat-value">{_fmt_kg(stats_rec['total'])}</div>
        <div class="stat-label">Production totale</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Code</label>
             <div style="font-weight:700">{p['code']}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Téléphone</label>
             <div>{p['telephone'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Sexe</label>
             <div>{p['sexe'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Coopérative</label>
             <div>{p['coop_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Type exploitation</label>
             <div>{p['type_exploitation'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Mobile Money</label>
             <div>{p['mobile_money_type'] or '-'} · {p['mobile_money_numero'] or '-'}</div></div>
        <div class="form-full" style="grid-column:1/-1">
          <label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Produits agricoles</label>
          <div>{p['produits_agricoles'] or '-'}</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3><i class="fas fa-draw-polygon"></i> Parcelles ({len(parcelles)})</h3>
      </div>
      <div class="table-wrap"><table>
        <thead><tr><th>Code</th><th>Nom</th><th>Superficie</th>
                   <th>Cultures</th><th>Irrigation</th><th>Bio</th></tr></thead>
        <tbody>"""
    for pa in parcelles:
        content += f"""
        <tr>
          <td><strong>{pa['code']}</strong></td>
          <td>{pa['nom'] or '-'}</td>
          <td><span class="badge badge-primary">{pa['superficie_ha']} ha</span></td>
          <td>{pa['cultures_principales'] or '-'}</td>
          <td>{'✅' if pa['irrigation_disponible'] else '❌'}</td>
          <td>{'🌿 Oui' if pa['certification_bio'] else 'Non'}</td>
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
            <thead><tr><th>Code</th><th>Date</th><th>Produit</th>
                       <th>Quantité</th><th>Qualité</th><th>Statut</th></tr></thead>
            <tbody>"""
        for r in recoltes:
            badge = 'badge-success' if r['statut'] == 'Transformée' else ('badge-info' if r['statut'] == 'Livrée' else 'badge-warning')
            content += f"""
            <tr>
              <td><small>{r['code']}</small></td>
              <td>{_fmt_date(r['date_recolte'])}</td>
              <td><strong>{r['produit']}</strong></td>
              <td>{_fmt_kg(r['quantite_kg'])}</td>
              <td><span class="badge badge-primary">{r['qualite'] or '-'}</span></td>
              <td><span class="badge {badge}">{r['statut']}</span></td>
            </tr>"""
        content += "</tbody></table></div></div>"

    # Livraisons
    if livraisons:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-truck"></i> Livraisons à l'usine</h3></div>
          <div class="table-wrap"><table>
            <thead><tr><th>Référence</th><th>Date</th><th>Produit</th>
                       <th>Quantité nette</th><th>Montant</th><th>Paiement</th></tr></thead>
            <tbody>"""
        for l in livraisons:
            badge_p = 'badge-success' if l['statut_paiement'] == 'Payé' else 'badge-warning'
            content += f"""
            <tr>
              <td><small>{l['reference']}</small></td>
              <td>{_fmt_date(l['date_livraison'])}</td>
              <td>{l['produit']}</td>
              <td><strong>{_fmt_kg(l['poids_net_kg'])}</strong></td>
              <td>{_fmt_fcfa(l['montant_total'])}</td>
              <td><span class="badge {badge_p}">{l['statut_paiement']}</span></td>
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
            try:
                c.execute("SELECT COUNT(*) FROM producteurs")
                n = (c.fetchone()[0] or 0) + 1
                code = f"PRD-{n:05d}"

                c.execute("""INSERT INTO producteurs
                    (code, nom, prenom, sexe, telephone, email, adresse, village,
                     region_id, superficie_ha, type_exploitation, produits_agricoles,
                     cooperative_id, mobile_money_type, mobile_money_numero, actif)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                    (code, nom, prenom,
                     request.form.get('sexe') or 'M',
                     (request.form.get('telephone') or '').strip(),
                     (request.form.get('email') or '').strip(),
                     (request.form.get('adresse') or '').strip(),
                     (request.form.get('village') or '').strip(),
                     request.form.get('region_id') or None,
                     float(request.form.get('superficie_ha') or 0),
                     request.form.get('type_exploitation') or 'Familiale',
                     (request.form.get('produits_agricoles') or '').strip(),
                     request.form.get('cooperative_id') or None,
                     request.form.get('mobile_money_type') or None,
                     (request.form.get('mobile_money_numero') or '').strip()))
                new_id = c.lastrowid
                conn.commit()
                _log('CREATE_PRODUCTEUR', f"Producteur {prenom} {nom} ({code})",
                     entity='producteur', entity_id=new_id)
                flash(f"Producteur {prenom} {nom} créé", "success")
                conn.close()
                return redirect(f'/producteurs/{new_id}')
            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    c.execute("SELECT id, nom FROM regions ORDER BY nom")
    regions = c.fetchall()
    c.execute("SELECT id, nom FROM cooperatives ORDER BY nom")
    coops = c.fetchall()
    conn.close()

    opt_r = ''.join(f'<option value="{r["id"]}">{r["nom"]}</option>' for r in regions)
    opt_c = ''.join(f'<option value="{co["id"]}">{co["nom"]}</option>' for co in coops)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-user-plus"></i> Nouveau producteur</h2></div>
      <a href="/producteurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="form-group"><label>Nom *</label>
            <input type="text" name="nom" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Prénom</label>
            <input type="text" name="prenom" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Sexe</label>
            <select name="sexe" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="M">Masculin</option><option value="F">Féminin</option>
            </select></div>
          <div class="form-group"><label>Téléphone</label>
            <input type="text" name="telephone" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Email</label>
            <input type="email" name="email" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Village</label>
            <input type="text" name="village" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Région</label>
            <select name="region_id" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">—</option>{opt_r}
            </select></div>
          <div class="form-group"><label>Coopérative</label>
            <select name="cooperative_id" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">—</option>{opt_c}
            </select></div>
          <div class="form-group"><label>Superficie (ha)</label>
            <input type="number" step="0.1" name="superficie_ha" value="0" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Type exploitation</label>
            <select name="type_exploitation" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option>Familiale</option><option>Coopérative</option><option>Agro-industrielle</option>
            </select></div>
          <div class="form-group"><label>Produits agricoles</label>
            <input type="text" name="produits_agricoles" placeholder="Mangue, Cajou..." style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Mobile Money</label>
            <select name="mobile_money_type" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">—</option><option>Wave</option><option>Orange Money</option><option>Free Money</option>
            </select></div>
          <div class="form-group"><label>N° Mobile Money</label>
            <input type="text" name="mobile_money_numero" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
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
            nom=?, prenom=?, sexe=?, telephone=?, email=?, adresse=?, village=?,
            region_id=?, superficie_ha=?, type_exploitation=?, produits_agricoles=?,
            cooperative_id=?, mobile_money_type=?, mobile_money_numero=?
            WHERE id=?""",
            ((request.form.get('nom') or '').strip(),
             (request.form.get('prenom') or '').strip(),
             request.form.get('sexe') or 'M',
             (request.form.get('telephone') or '').strip(),
             (request.form.get('email') or '').strip(),
             (request.form.get('adresse') or '').strip(),
             (request.form.get('village') or '').strip(),
             request.form.get('region_id') or None,
             float(request.form.get('superficie_ha') or 0),
             request.form.get('type_exploitation') or 'Familiale',
             (request.form.get('produits_agricoles') or '').strip(),
             request.form.get('cooperative_id') or None,
             request.form.get('mobile_money_type') or None,
             (request.form.get('mobile_money_numero') or '').strip(),
             pid))
        conn.commit()
        _log('UPDATE_PRODUCTEUR', f"Producteur id={pid} modifié",
             entity='producteur', entity_id=pid)
        conn.close()
        flash("Producteur mis à jour", "success")
        return redirect(f'/producteurs/{pid}')

    c.execute("SELECT id, nom FROM regions ORDER BY nom")
    regions = c.fetchall()
    c.execute("SELECT id, nom FROM cooperatives ORDER BY nom")
    coops = c.fetchall()
    conn.close()

    def opt(items, cur):
        return ''.join(f'<option value="{i["id"]}" {"selected" if cur==i["id"] else ""}>{i["nom"]}</option>' for i in items)

    opt_mm = ''
    for mm in ['', 'Wave', 'Orange Money', 'Free Money']:
        sel = 'selected' if p['mobile_money_type'] == mm else ''
        opt_mm += f'<option value="{mm}" {sel}>{mm or "—"}</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-pen"></i> Modifier producteur</h2></div>
      <a href="/producteurs/{pid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="form-group"><label>Nom</label>
            <input type="text" name="nom" value="{p['nom']}" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Prénom</label>
            <input type="text" name="prenom" value="{p['prenom'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Téléphone</label>
            <input type="text" name="telephone" value="{p['telephone'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Email</label>
            <input type="email" name="email" value="{p['email'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Village</label>
            <input type="text" name="village" value="{p['village'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Région</label>
            <select name="region_id" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">—</option>{opt(regions, p['region_id'])}
            </select></div>
          <div class="form-group"><label>Coopérative</label>
            <select name="cooperative_id" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">—</option>{opt(coops, p['cooperative_id'])}
            </select></div>
          <div class="form-group"><label>Superficie (ha)</label>
            <input type="number" step="0.1" name="superficie_ha" value="{p['superficie_ha'] or 0}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Produits</label>
            <input type="text" name="produits_agricoles" value="{p['produits_agricoles'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Mobile Money</label>
            <select name="mobile_money_type" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">{opt_mm}</select></div>
          <div class="form-group"><label>N° MM</label>
            <input type="text" name="mobile_money_numero" value="{p['mobile_money_numero'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
          <a href="/producteurs/{pid}" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='producteurs', title='Modifier producteur')


# ================================================================
# ==================== PRODUITS FINIS ====================
# ================================================================
@crud_bp.route('/produits')
@_auth_required
def produits_list():
    q = (request.args.get('q') or '').strip()
    categorie = request.args.get('categorie') or ''

    conn = _db()
    c = conn.cursor()
    sql = """SELECT p.*,
                    (SELECT COALESCE(SUM(quantite_kg), 0) FROM stocks_produits WHERE produit_id=p.id) AS stock_kg,
                    (SELECT COUNT(*) FROM ordres_fabrication WHERE produit_fini_id=p.id) AS nb_of
             FROM produits_finis p
             WHERE p.actif=1"""
    params = []
    if q:
        sql += " AND (p.nom LIKE ? OR p.code LIKE ?)"
        params += [f"%{q}%"] * 2
    if categorie:
        sql += " AND p.categorie=?"
        params.append(categorie)
    sql += " ORDER BY p.categorie, p.nom"
    c.execute(sql, params)
    produits = c.fetchall()

    c.execute("SELECT DISTINCT categorie FROM produits_finis WHERE actif=1 ORDER BY categorie")
    categories = c.fetchall()
    conn.close()

    opt_cat = '<option value="">Toutes catégories</option>'
    for cat in categories:
        sel = 'selected' if cat['categorie'] == categorie else ''
        opt_cat += f'<option value="{cat["categorie"]}" {sel}>{cat["categorie"]}</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-box"></i> Produits finis</h2>
        <div class="page-subtitle">{len(produits)} référence(s)</div></div>
      {'<a href="/produits/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau produit</a>' if _can_write() else ''}
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:2;margin:0;min-width:200px">
          <label>Recherche</label>
          <input type="text" name="q" value="{q}" placeholder="Nom, code..." style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:180px">
          <label>Catégorie</label>
          <select name="categorie" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">{opt_cat}</select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-search"></i> Filtrer</button>
        <a href="/produits" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Code</th><th>Produit</th><th>Catégorie</th><th>Conditionnement</th>
          <th>Prix revient</th><th>Prix vente</th><th>Marge</th><th>Stock</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for p in produits:
        marge = 0
        if p['prix_revient'] and p['prix_vente']:
            marge = (p['prix_vente'] - p['prix_revient']) / p['prix_revient'] * 100

        content += f"""
        <tr>
          <td><strong>{p['code']}</strong></td>
          <td>
            <div style="font-weight:700">{p['nom']}</div>
            <div style="font-size:0.72rem;color:#94a3b8">{p['matiere_premiere'] or ''}</div>
          </td>
          <td><span class="badge badge-primary">{p['categorie'] or '-'}</span></td>
          <td><small>{p['conditionnement'] or '-'}</small></td>
          <td>{_fmt_fcfa(p['prix_revient'])}</td>
          <td><strong style="color:#10b981">{_fmt_fcfa(p['prix_vente'])}</strong></td>
          <td><span class="badge badge-success">{marge:.0f}%</span></td>
          <td><small>{_fmt_kg(p['stock_kg'])}</small></td>
          <td style="white-space:nowrap">
            <a href="/produits/{p['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
            {'<a href="/produits/'+str(p['id'])+'/modifier" class="btn btn-warning btn-sm"><i class="fas fa-pen"></i></a>' if _can_write() else ''}
          </td>
        </tr>"""
    if not produits:
        content += '<tr><td colspan="9" class="empty"><i class="fas fa-box"></i><br>Aucun produit</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='produits', title='Produits finis')


@crud_bp.route('/produits/<int:pid>')
@_auth_required
def produits_detail(pid):
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM produits_finis WHERE id=?", (pid,))
    p = c.fetchone()
    if not p:
        conn.close()
        flash("Produit introuvable", "danger")
        return redirect('/produits')

    c.execute("""SELECT * FROM stocks_produits WHERE produit_id=?
                 ORDER BY date_fabrication DESC LIMIT 30""", (pid,))
    stocks = c.fetchall()

    c.execute("""SELECT * FROM ordres_fabrication WHERE produit_fini_id=?
                 ORDER BY date_debut DESC LIMIT 20""", (pid,))
    of_list = c.fetchall()

    # Stats
    c.execute("""SELECT COALESCE(SUM(quantite_kg), 0) AS total FROM stocks_produits WHERE produit_id=?""", (pid,))
    stock_total = c.fetchone()['total']

    conn.close()

    marge_pct = 0
    if p['prix_revient'] and p['prix_vente']:
        marge_pct = (p['prix_vente'] - p['prix_revient']) / p['prix_revient'] * 100
    marge_fcfa = (p['prix_vente'] or 0) - (p['prix_revient'] or 0)

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-box"></i> {p['nom']}</h2>
        <div class="page-subtitle">
          <strong>{p['code']}</strong> · {p['categorie'] or '-'} · {p['sous_categorie'] or ''}
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/produits" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        {'<a href="/produits/'+str(pid)+'/modifier" class="btn btn-warning"><i class="fas fa-pen"></i> Modifier</a>' if _can_write() else ''}
      </div>
    </div>

    <div class="stats">
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-warehouse"></i></div>
        <div class="stat-value">{_fmt_kg(stock_total)}</div>
        <div class="stat-label">Stock disponible</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-tag"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(p['prix_revient'])}</div>
        <div class="stat-label">Prix de revient</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-euro-sign"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(p['prix_vente'])}</div>
        <div class="stat-label">Prix de vente</div></div>
      <div class="stat-card purple"><div class="stat-icon"><i class="fas fa-percent"></i></div>
        <div class="stat-value">{marge_pct:.0f}%</div>
        <div class="stat-label">Marge ({_fmt_fcfa(marge_fcfa)})</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Fiche produit</h3></div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Code</label>
             <div style="font-weight:700">{p['code']}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Matière première</label>
             <div>{p['matiere_premiere'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Code SH (douane)</label>
             <div style="font-family:monospace">{p['code_sh'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Conditionnement</label>
             <div>{p['conditionnement'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Durée conservation</label>
             <div>{p['duree_conservation_mois'] or '-'} mois</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Température</label>
             <div>{p['temperature_conservation'] or '-'}</div></div>
        <div style="grid-column:1/-1"><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Certifications</label>
             <div>{p['certifications'] or '-'}</div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-warehouse"></i> Stocks par lot</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Lot</th><th>Site</th><th>Quantité</th>
                   <th>Fabrication</th><th>Péremption</th><th>Emplacement</th></tr></thead>
        <tbody>"""
    for s in stocks:
        content += f"""
        <tr>
          <td><strong>{s['lot']}</strong></td>
          <td><small>Site {s['site_id']}</small></td>
          <td><strong>{_fmt_kg(s['quantite_kg'])}</strong></td>
          <td>{_fmt_date(s['date_fabrication'])}</td>
          <td>{_fmt_date(s['date_peremption'])}</td>
          <td><small>{s['emplacement'] or '-'}</small></td>
        </tr>"""
    if not stocks:
        content += '<tr><td colspan="6" class="empty">Aucun stock</td></tr>'
    content += "</tbody></table></div></div>"

    if of_list:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-industry"></i> Ordres de fabrication</h3></div>
          <div class="table-wrap"><table>
            <thead><tr><th>Référence</th><th>Quantité</th><th>Lot</th>
                       <th>Rendement</th><th>Statut</th><th>Date</th></tr></thead>
            <tbody>"""
        for of in of_list:
            badge = 'badge-success' if of['statut'] == 'Terminé' else ('badge-warning' if of['statut'] == 'En cours' else 'badge-info')
            content += f"""
            <tr>
              <td><small>{of['reference']}</small></td>
              <td>{_fmt_kg(of['quantite_kg'])}</td>
              <td><small>{of['lot_production']}</small></td>
              <td>{of['rendement_pct'] or 0:.1f}%</td>
              <td><span class="badge {badge}">{of['statut']}</span></td>
              <td>{_fmt_date(of['date_debut'])}</td>
            </tr>"""
        content += "</tbody></table></div></div>"

    return _render(content, active='produits', title=p['nom'])


@crud_bp.route('/produits/nouveau', methods=['GET', 'POST'])
@_auth_required
def produits_new():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/produits')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        nom = (request.form.get('nom') or '').strip()
        if not nom:
            flash("Nom obligatoire", "warning")
        else:
            try:
                c.execute("SELECT COUNT(*) FROM produits_finis")
                n = (c.fetchone()[0] or 0) + 1
                code = f"PF-{n:04d}"

                c.execute("""INSERT INTO produits_finis
                    (code, nom, categorie, sous_categorie, description, matiere_premiere,
                     unite, conditionnement, duree_conservation_mois, temperature_conservation,
                     certifications, prix_revient, prix_vente, code_sh, actif)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                    (code, nom,
                     request.form.get('categorie') or '',
                     request.form.get('sous_categorie') or '',
                     (request.form.get('description') or '').strip(),
                     (request.form.get('matiere_premiere') or '').strip(),
                     'kg',
                     (request.form.get('conditionnement') or '').strip(),
                     int(request.form.get('duree_conservation_mois') or 12),
                     (request.form.get('temperature_conservation') or '').strip(),
                     (request.form.get('certifications') or '').strip(),
                     int(request.form.get('prix_revient') or 0),
                     int(request.form.get('prix_vente') or 0),
                     (request.form.get('code_sh') or '').strip()))
                new_id = c.lastrowid
                conn.commit()
                _log('CREATE_PRODUIT', f"Produit {nom} ({code})",
                     entity='produit', entity_id=new_id)
                flash(f"Produit {nom} créé", "success")
                conn.close()
                return redirect(f'/produits/{new_id}')
            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus"></i> Nouveau produit fini</h2></div>
      <a href="/produits" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="form-group" style="grid-column:1/-1"><label>Nom du produit *</label>
            <input type="text" name="nom" required placeholder="Ex: Mangue séchée premium" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Catégorie</label>
            <input type="text" name="categorie" placeholder="Mangue, Cajou, Légumes..." style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Sous-catégorie</label>
            <input type="text" name="sous_categorie" placeholder="Séchée, Pulpe, Confiture..." style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Matière première</label>
            <input type="text" name="matiere_premiere" placeholder="Mangue, Cajou..." style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Conditionnement</label>
            <input type="text" name="conditionnement" placeholder="sachet 200g, bouteille 1L..." style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Durée conservation (mois)</label>
            <input type="number" name="duree_conservation_mois" value="12" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Température conservation</label>
            <input type="text" name="temperature_conservation" placeholder="18-20°C" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Prix de revient (FCFA/kg)</label>
            <input type="number" name="prix_revient" value="0" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Prix de vente (FCFA/kg)</label>
            <input type="number" name="prix_vente" value="0" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Code SH (douane)</label>
            <input type="text" name="code_sh" placeholder="0810.10" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Certifications</label>
            <input type="text" name="certifications" placeholder="HACCP, ISO 22000..." style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group" style="grid-column:1/-1"><label>Description</label>
            <textarea name="description" rows="3" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></textarea></div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Créer</button>
          <a href="/produits" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='produits', title='Nouveau produit')


@crud_bp.route('/produits/<int:pid>/modifier', methods=['GET', 'POST'])
@_auth_required
def produits_edit(pid):
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/produits')

    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM produits_finis WHERE id=?", (pid,))
    p = c.fetchone()
    if not p:
        conn.close()
        return redirect('/produits')

    if request.method == 'POST':
        c.execute("""UPDATE produits_finis SET
            nom=?, categorie=?, sous_categorie=?, description=?, matiere_premiere=?,
            conditionnement=?, duree_conservation_mois=?, temperature_conservation=?,
            certifications=?, prix_revient=?, prix_vente=?, code_sh=?
            WHERE id=?""",
            ((request.form.get('nom') or '').strip(),
             request.form.get('categorie') or '',
             request.form.get('sous_categorie') or '',
             (request.form.get('description') or '').strip(),
             (request.form.get('matiere_premiere') or '').strip(),
             (request.form.get('conditionnement') or '').strip(),
             int(request.form.get('duree_conservation_mois') or 12),
             (request.form.get('temperature_conservation') or '').strip(),
             (request.form.get('certifications') or '').strip(),
             int(request.form.get('prix_revient') or 0),
             int(request.form.get('prix_vente') or 0),
             (request.form.get('code_sh') or '').strip(),
             pid))
        conn.commit()
        _log('UPDATE_PRODUIT', f"Produit id={pid} modifié", entity='produit', entity_id=pid)
        conn.close()
        flash("Produit mis à jour", "success")
        return redirect(f'/produits/{pid}')

    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-pen"></i> Modifier produit</h2></div>
      <a href="/produits/{pid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="form-group" style="grid-column:1/-1"><label>Nom</label>
            <input type="text" name="nom" value="{p['nom']}" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Catégorie</label>
            <input type="text" name="categorie" value="{p['categorie'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Sous-catégorie</label>
            <input type="text" name="sous_categorie" value="{p['sous_categorie'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Matière première</label>
            <input type="text" name="matiere_premiere" value="{p['matiere_premiere'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Conditionnement</label>
            <input type="text" name="conditionnement" value="{p['conditionnement'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Durée conservation (mois)</label>
            <input type="number" name="duree_conservation_mois" value="{p['duree_conservation_mois'] or 12}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Température</label>
            <input type="text" name="temperature_conservation" value="{p['temperature_conservation'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Prix revient</label>
            <input type="number" name="prix_revient" value="{p['prix_revient'] or 0}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Prix vente</label>
            <input type="number" name="prix_vente" value="{p['prix_vente'] or 0}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Code SH</label>
            <input type="text" name="code_sh" value="{p['code_sh'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group"><label>Certifications</label>
            <input type="text" name="certifications" value="{p['certifications'] or ''}" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px"></div>
          <div class="form-group" style="grid-column:1/-1"><label>Description</label>
            <textarea name="description" rows="3" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">{p['description'] or ''}</textarea></div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
          <a href="/produits/{pid}" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='produits', title='Modifier produit')
