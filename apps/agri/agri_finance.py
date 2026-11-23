"""
💰 AgriSénégal V2 — Module Finance
Crédits · Subventions · Assurances · Élevage
"""
from flask import Blueprint, request, redirect, flash, jsonify
from flask_login import current_user
import sqlite3
from datetime import datetime

finance_bp = Blueprint('agri_finance', __name__)
_deps = {}


def init_agri_finance(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(finance_bp)
    print("[FINANCE] ✅ Module Finance complet enregistré")


def _db(): return _deps['get_db']()
def _render(content, active='finance', title='AgriSénégal Finance'):
    return _deps['render_page'](content, active=active, page_title=title)


def _auth_required(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if not (current_user and current_user.is_authenticated):
            return redirect('/login')
        return f(*a, **k)
    return w


def _fmt_fcfa(m):
    if not m: return "0 F"
    return f"{int(m):,} F".replace(",", " ")


# ================================================================
# ==================== /finance (hub) ====================
# ================================================================
@finance_bp.route('/finance')
@_auth_required
def finance_home():
    conn = _db()
    c = conn.cursor()

    # Stats
    c.execute("SELECT COUNT(*) AS nb, COALESCE(SUM(montant_accorde), 0) AS total FROM credits")
    credits = c.fetchone()

    c.execute("SELECT COUNT(*) AS nb, COALESCE(SUM(montant), 0) AS total FROM subventions")
    subventions = c.fetchone()

    c.execute("SELECT COUNT(*) AS nb, COALESCE(SUM(prime), 0) AS total FROM assurances_agricoles")
    assurances = c.fetchone()

    c.execute("SELECT COUNT(*) AS nb, COALESCE(SUM(montant), 0) AS total FROM transactions_mobile WHERE statut='Réussi'")
    mm = c.fetchone()

    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-coins"></i> Finance</h2>
        <div class="page-subtitle">Crédits · Subventions · Assurances · Mobile Money</div></div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-hand-holding-dollar"></i></div>
        <div class="stat-value">{credits['nb']}</div>
        <div class="stat-label">Crédits</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-gift"></i></div>
        <div class="stat-value">{subventions['nb']}</div>
        <div class="stat-label">Subventions</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-shield-halved"></i></div>
        <div class="stat-value">{assurances['nb']}</div>
        <div class="stat-label">Assurances</div></div>
      <div class="stat-card blue"><div class="stat-icon"><i class="fas fa-mobile-screen"></i></div>
        <div class="stat-value">{mm['nb']}</div>
        <div class="stat-label">Transactions MM</div></div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px">
      <div class="card" style="border-left:5px solid #10b981">
        <h3 style="color:#065f46;margin-bottom:10px"><i class="fas fa-hand-holding-dollar"></i> Crédits</h3>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          {credits['nb']} crédit(s) — {_fmt_fcfa(credits['total'])}
        </p>
        <a href="/credits" class="btn btn-primary btn-sm"><i class="fas fa-eye"></i> Voir</a>
      </div>

      <div class="card" style="border-left:5px solid #f59e0b">
        <h3 style="color:#92400e;margin-bottom:10px"><i class="fas fa-gift"></i> Subventions</h3>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          {subventions['nb']} subvention(s) — {_fmt_fcfa(subventions['total'])}
        </p>
        <a href="/subventions" class="btn btn-primary btn-sm"><i class="fas fa-eye"></i> Voir</a>
      </div>

      <div class="card" style="border-left:5px solid #7c3aed">
        <h3 style="color:#6d28d9;margin-bottom:10px"><i class="fas fa-shield-halved"></i> Assurances</h3>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          {assurances['nb']} assurance(s) — {_fmt_fcfa(assurances['total'])}
        </p>
        <a href="/assurances" class="btn btn-primary btn-sm"><i class="fas fa-eye"></i> Voir</a>
      </div>

      <div class="card" style="border-left:5px solid #0ea5e9">
        <h3 style="color:#0369a1;margin-bottom:10px"><i class="fas fa-mobile-screen"></i> Mobile Money</h3>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          {mm['nb']} transaction(s) — {_fmt_fcfa(mm['total'])}
        </p>
        <a href="/mobile-money" class="btn btn-primary btn-sm"><i class="fas fa-eye"></i> Voir</a>
      </div>

      <div class="card" style="border-left:5px solid #0891b2">
        <h3 style="color:#0e7490;margin-bottom:10px"><i class="fas fa-cow"></i> Élevage</h3>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          Troupeaux, animaux, production laitière
        </p>
        <a href="/elevage" class="btn btn-primary btn-sm"><i class="fas fa-eye"></i> Voir</a>
      </div>

      <div class="card" style="border-left:5px solid #dc2626">
        <h3 style="color:#991b1b;margin-bottom:10px"><i class="fas fa-plus-circle"></i> Nouveaux dossiers</h3>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">
          <a href="/credits/nouveau" class="btn btn-success btn-sm"><i class="fas fa-plus"></i> Crédit</a>
          <a href="/elevage/nouveau" class="btn btn-info btn-sm"><i class="fas fa-plus"></i> Troupeau</a>
        </div>
      </div>
    </div>
    """
    return _render(content, active='finance', title='Finance')


# ================================================================
# ==================== CRÉDITS ====================
# ================================================================
@finance_bp.route('/credits')
@_auth_required
def credits_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT cr.*, p.nom AS prod_nom, p.prenom AS prod_prenom,
                        i.nom AS institution_nom
                 FROM credits cr
                 LEFT JOIN producteurs p ON cr.producteur_id = p.id
                 LEFT JOIN institutions_financement i ON cr.institution_id = i.id
                 ORDER BY cr.date_demande DESC LIMIT 100""")
    credits = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-hand-holding-dollar"></i> Crédits</h2>
        <div class="page-subtitle">{len(credits)} crédit(s)</div></div>
      <a href="/credits/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau crédit</a>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Référence</th><th>Producteur</th><th>Institution</th>
          <th>Montant</th><th>Taux</th><th>Statut</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for cr in credits:
        badge = 'badge-warning'
        if cr['statut'] == 'Décaissé': badge = 'badge-success'
        elif cr['statut'] == 'Remboursé': badge = 'badge-info'
        content += f"""
        <tr>
          <td><small>{cr['reference']}</small></td>
          <td>{cr['prod_prenom'] or ''} {cr['prod_nom'] or ''}</td>
          <td>{cr['institution_nom'] or '-'}</td>
          <td><strong>{_fmt_fcfa(cr['montant_accorde'] or cr['montant_demande'])}</strong></td>
          <td>{cr['taux_interet'] or 0}%</td>
          <td><span class="badge {badge}">{cr['statut']}</span></td>
          <td>
            <a href="/credits/{cr['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
          </td>
        </tr>"""
    if not credits:
        content += '<tr><td colspan="7" class="empty"><i class="fas fa-hand-holding-dollar"></i><br>Aucun crédit</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='finance', title='Crédits')


@finance_bp.route('/credits/nouveau', methods=['GET', 'POST'])
@_auth_required
def credits_new():
    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        producteur_id = request.form.get('producteur_id')
        montant = int(request.form.get('montant') or 0)
        if not producteur_id or montant <= 0:
            flash("Producteur et montant obligatoires", "warning")
        else:
            c.execute("SELECT COUNT(*) FROM credits")
            n = (c.fetchone()[0] or 0) + 1
            ref = f"CRD-{datetime.now().strftime('%Y%m%d')}-{n:04d}"

            c.execute("""INSERT INTO credits
                (reference, producteur_id, institution_id, type_credit,
                 montant_demande, taux_interet, duree_mois, date_demande,
                 statut, objet, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (ref, producteur_id,
                 request.form.get('institution_id') or None,
                 request.form.get('type_credit') or 'Campagne agricole',
                 montant,
                 float(request.form.get('taux_interet') or 0),
                 int(request.form.get('duree_mois') or 12),
                 datetime.now().date().isoformat(),
                 'Demandé',
                 (request.form.get('objet') or '').strip(),
                 datetime.now().isoformat()))
            conn.commit()
            flash(f"Crédit {ref} créé", "success")
            conn.close()
            return redirect('/credits')

    c.execute("SELECT id, nom, prenom FROM producteurs WHERE actif=1 ORDER BY nom")
    producteurs = c.fetchall()
    c.execute("SELECT id, nom FROM institutions_financement WHERE actif=1 ORDER BY nom")
    institutions = c.fetchall()
    conn.close()

    opt_p = ''.join(f'<option value="{p["id"]}">{p["prenom"]} {p["nom"]}</option>' for p in producteurs)
    opt_i = ''.join(f'<option value="{i["id"]}">{i["nom"]}</option>' for i in institutions)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus"></i> Nouveau crédit</h2></div>
      <a href="/credits" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card"><form method="POST">
      <div class="form-grid">
        <div class="form-group form-full"><label>Producteur *</label>
          <select name="producteur_id" required><option value="">—</option>{opt_p}</select></div>
        <div class="form-group"><label>Institution</label>
          <select name="institution_id"><option value="">—</option>{opt_i}</select></div>
        <div class="form-group"><label>Montant (FCFA) *</label>
          <input type="number" name="montant" required value="500000"></div>
        <div class="form-group"><label>Taux (%)</label>
          <input type="number" step="0.1" name="taux_interet" value="10"></div>
        <div class="form-group"><label>Durée (mois)</label>
          <input type="number" name="duree_mois" value="12"></div>
        <div class="form-group"><label>Type</label>
          <select name="type_credit">
            <option>Campagne agricole</option><option>Équipement</option><option>Intrants</option>
          </select></div>
        <div class="form-group form-full"><label>Objet</label>
          <input type="text" name="objet" placeholder="Ex: Achat semences"></div>
      </div>
      <button class="btn btn-primary" style="margin-top:20px"><i class="fas fa-check"></i> Créer le crédit</button>
    </form></div>"""
    return _render(content, active='finance', title='Nouveau crédit')


# ================================================================
# ==================== SUBVENTIONS ====================
# ================================================================
@finance_bp.route('/subventions')
@_auth_required
def subventions_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT * FROM subventions ORDER BY date_attribution DESC LIMIT 100""")
    subv = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-gift"></i> Subventions</h2>
        <div class="page-subtitle">{len(subv)} subvention(s)</div></div>
    </div>
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Référence</th><th>Programme</th><th>Bailleur</th>
          <th>Montant</th><th>Statut</th><th>Date</th>
        </tr></thead><tbody>
    """
    for s in subv:
        badge = 'badge-success' if s['statut'] == 'Décaissé' else 'badge-warning'
        content += f"""
        <tr>
          <td><small>{s['reference']}</small></td>
          <td>{s['programme'] or '-'}</td>
          <td>{s['bailleur'] or '-'}</td>
          <td><strong>{_fmt_fcfa(s['montant'])}</strong></td>
          <td><span class="badge {badge}">{s['statut']}</span></td>
          <td>{s['date_attribution'] or '-'}</td>
        </tr>"""
    if not subv:
        content += '<tr><td colspan="6" class="empty">Aucune subvention</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='finance', title='Subventions')


# ================================================================
# ==================== ASSURANCES ====================
# ================================================================
@finance_bp.route('/assurances')
@_auth_required
def assurances_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT a.*, p.nom AS prod_nom, p.prenom AS prod_prenom
                 FROM assurances_agricoles a
                 LEFT JOIN producteurs p ON a.producteur_id = p.id
                 ORDER BY a.date_souscription DESC LIMIT 100""")
    ass = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-shield-halved"></i> Assurances agricoles</h2>
        <div class="page-subtitle">{len(ass)} assurance(s)</div></div>
    </div>
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Référence</th><th>Producteur</th><th>Type</th>
          <th>Capital</th><th>Prime</th><th>Statut</th>
        </tr></thead><tbody>
    """
    for a in ass:
        content += f"""
        <tr>
          <td><small>{a['reference']}</small></td>
          <td>{a['prod_prenom'] or ''} {a['prod_nom'] or ''}</td>
          <td>{a['type_assurance'] or '-'}</td>
          <td>{_fmt_fcfa(a['capital_assure'])}</td>
          <td>{_fmt_fcfa(a['prime'])}</td>
          <td><span class="badge badge-success">{a['statut']}</span></td>
        </tr>"""
    if not ass:
        content += '<tr><td colspan="6" class="empty">Aucune assurance</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='finance', title='Assurances')


# ================================================================
# ==================== ÉLEVAGE (complété) ====================
# ================================================================
@finance_bp.route('/elevage/nouveau', methods=['GET', 'POST'])
@_auth_required
def elevage_new():
    """Créer un nouveau troupeau / éleveur"""
    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        producteur_id = request.form.get('producteur_id')
        espece_id = request.form.get('espece_id')
        effectif = int(request.form.get('effectif_total') or 0)

        if not producteur_id or not espece_id or effectif <= 0:
            flash("Tous les champs obligatoires", "warning")
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
                     effectif,
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

                # Créer un enregistrement producteur si nécessaire
                c.execute("""UPDATE producteurs SET
                    type_exploitation = CASE
                        WHEN type_exploitation = 'Familiale' THEN 'Agro-pastorale'
                        ELSE type_exploitation
                    END
                    WHERE id=?""", (producteur_id,))

                conn.commit()
                _log_action('CREATE_TROUPEAU', f"Troupeau {code} créé ({effectif} têtes)",
                           entity='troupeau', entity_id=new_id)
                flash(f"Troupeau {code} créé avec succès", "success")
                conn.close()
                return redirect('/elevage')

            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    # GET
    c.execute("SELECT id, nom, prenom, code FROM producteurs WHERE actif=1 ORDER BY nom")
    producteurs = c.fetchall()
    c.execute("SELECT id, nom, icone FROM especes_animales WHERE actif=1 ORDER BY nom")
    especes = c.fetchall()
    conn.close()

    opt_p = ''.join(f'<option value="{p["id"]}">{p["prenom"]} {p["nom"]} ({p["code"]})</option>' for p in producteurs)
    opt_e = ''.join(f'<option value="{e["id"]}">{e["nom"]}</option>' for e in especes)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-cow"></i> Nouveau troupeau (Éleveur)</h2>
        <div class="page-subtitle">Enregistrer un élevage</div></div>
      <a href="/elevage" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>

    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group form-full">
            <label>Producteur / Éleveur *</label>
            <select name="producteur_id" required>
              <option value="">— Choisir —</option>{opt_p}
            </select>
          </div>
          <div class="form-group">
            <label>Espèce *</label>
            <select name="espece_id" required>
              <option value="">— Choisir —</option>{opt_e}
            </select>
          </div>
          <div class="form-group">
            <label>Nom du troupeau</label>
            <input type="text" name="nom" placeholder="Ex: Troupeau Nord">
          </div>
          <div class="form-group">
            <label>Race</label>
            <input type="text" name="race" placeholder="Ex: Gobra, Djalonké...">
          </div>
          <div class="form-group">
            <label>Effectif total *</label>
            <input type="number" name="effectif_total" required value="10">
          </div>
          <div class="form-group">
            <label>Femelles</label>
            <input type="number" name="effectif_femelles" value="0">
          </div>
          <div class="form-group">
            <label>Mâles</label>
            <input type="number" name="effectif_males" value="0">
          </div>
          <div class="form-group">
            <label>Jeunes</label>
            <input type="number" name="effectif_jeunes" value="0">
          </div>
          <div class="form-group">
            <label>Mode d'élevage</label>
            <select name="mode_elevage">
              <option>Extensif</option>
              <option>Semi-intensif</option>
              <option>Intensif</option>
              <option>Transhumance</option>
            </select>
          </div>
          <div class="form-group">
            <label>Objectif</label>
            <select name="objectif">
              <option>Mixte</option>
              <option>Lait</option>
              <option>Viande</option>
              <option>Reproduction</option>
            </select>
          </div>
          <div class="form-group form-full">
            <label>Lieu de garde</label>
            <input type="text" name="lieu_garde" placeholder="Ex: Parc à côté du village">
          </div>
          <div class="form-group">
            <label>GPS Latitude</label>
            <input type="number" step="0.000001" name="gps_latitude" placeholder="14.7500">
          </div>
          <div class="form-group">
            <label>GPS Longitude</label>
            <input type="number" step="0.000001" name="gps_longitude" placeholder="-16.9333">
          </div>
        </div>

        <div style="padding:20px;background:#f0fdf4;border-radius:12px;margin-top:20px;border-left:5px solid #10b981">
          <h4 style="color:#065f46;margin-bottom:8px"><i class="fas fa-info-circle"></i> Info</h4>
          <p style="font-size:0.85rem;color:#475569">
            Le producteur sera automatiquement marqué comme <strong>Agro-pastoral</strong> s'il ne l'est pas déjà.
          </p>
        </div>

        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Créer le troupeau</button>
          <a href="/elevage" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='elevage', title='Nouveau troupeau')


def _log_action(action, details='', entity=None, entity_id=None):
    try:
        uid = None
        if current_user and current_user.is_authenticated:
            uid = current_user.id
        _deps['log_action'](uid, action, details, entity=entity, entity_id=entity_id)
    except Exception:
        pass
