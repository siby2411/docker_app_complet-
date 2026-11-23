"""
🌾 AgriSénégal V2 — Logique métier
Récoltes · Itinéraire technique · Mobile Money · Statistiques
"""
from flask import Blueprint, request, redirect, flash, jsonify, Response
from flask_login import current_user
import sqlite3
import csv
import io
from datetime import datetime, timedelta

agri_bp = Blueprint('agri', __name__)
_deps = {}


def init_agri(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(agri_bp)
    print("[AGRI] ✅ Module logique complet enregistré")


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


def _can_produce():
    return current_user and current_user.role in ('admin', 'direction', 'cooperative', 'producteur', 'technicien')


def _fmt_kg(kg):
    if not kg:
        return "0 kg"
    if kg >= 1000:
        return f"{kg/1000:.2f} t"
    return f"{int(kg)} kg"


def _fmt_fcfa(m):
    if not m:
        return "0 F"
    return f"{int(m):,} F".replace(",", " ")


# ================================================================
# ==================== RÉCOLTES ====================
# ================================================================
@agri_bp.route('/recoltes')
@_auth_required
def recoltes_list():
    if not _can_produce():
        flash("Accès réservé", "danger")
        return redirect('/')

    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT r.*, c.nom AS culture_nom, c.icone, c.prix_moyen_kg,
                        p.nom AS producteur_nom, p.prenom AS producteur_prenom,
                        pa.code AS parcelle_code, pa.superficie_ha
                 FROM recoltes r
                 LEFT JOIN cultures c ON r.culture_id = c.id
                 LEFT JOIN producteurs p ON r.producteur_id = p.id
                 LEFT JOIN parcelles pa ON r.parcelle_id = pa.id
                 WHERE strftime('%Y-%m', r.date_recolte)=?
                 ORDER BY r.date_recolte DESC LIMIT 200""", (mois,))
    recoltes = c.fetchall()

    # Stats
    c.execute("""SELECT COUNT(*) AS nb, COALESCE(SUM(quantite_kg), 0) AS qte,
                        COALESCE(AVG(quantite_kg), 0) AS moy
                 FROM recoltes WHERE strftime('%Y-%m', date_recolte)=?""", (mois,))
    stats = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-wheat-awn"></i> Récoltes</h2>
        <div class="page-subtitle">{len(recoltes)} récolte(s) — {mois}</div></div>
      {'<a href="/recoltes/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle récolte</a>' if _can_produce() else ''}
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-wheat-awn"></i></div>
        <div class="stat-value">{stats['nb']}</div>
        <div class="stat-label">Récoltes du mois</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-weight-hanging"></i></div>
        <div class="stat-value">{_fmt_kg(stats['qte'])}</div>
        <div class="stat-label">Production totale</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-chart-line"></i></div>
        <div class="stat-value">{_fmt_kg(stats['moy'])}</div>
        <div class="stat-label">Récolte moyenne</div></div>
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
          <th>Code</th><th>Date</th><th>Culture</th><th>Producteur</th>
          <th>Parcelle</th><th>Quantité</th><th>Rendement</th>
          <th>Qualité</th><th>Destination</th>
        </tr></thead><tbody>
    """
    for r in recoltes:
        rendement = (r['quantite_kg'] / r['superficie_ha']) if (r['superficie_ha'] and r['quantite_kg']) else 0
        badge_q = 'badge-success'
        if r['qualite'] == 'Moyenne': badge_q = 'badge-warning'
        elif r['qualite'] == 'Médiocre': badge_q = 'badge-danger'
        content += f"""
        <tr>
          <td><small>{r['code']}</small></td>
          <td>{r['date_recolte']}</td>
          <td><i class="fas {r['icone'] or 'fa-seedling'}" style="color:#10b981"></i> {r['culture_nom']}</td>
          <td>{r['producteur_prenom'] or ''} {r['producteur_nom'] or ''}</td>
          <td><small>{r['parcelle_code'] or '-'}</small></td>
          <td><strong>{_fmt_kg(r['quantite_kg'])}</strong></td>
          <td><small>{rendement/1000:.2f} t/ha</small></td>
          <td><span class="badge {badge_q}">{r['qualite'] or '-'}</span></td>
          <td><small>{r['destination'] or '-'}</small></td>
        </tr>"""
    if not recoltes:
        content += '<tr><td colspan="9" class="empty"><i class="fas fa-wheat-awn"></i><br>Aucune récolte</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='recoltes', title='Récoltes')


@agri_bp.route('/recoltes/nouvelle', methods=['GET', 'POST'])
@_auth_required
def recoltes_new():
    if not _can_produce():
        flash("Accès réservé", "danger")
        return redirect('/recoltes')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        culture_parcelle_id = request.form.get('culture_parcelle_id')
        quantite = float(request.form.get('quantite_kg') or 0)

        if not culture_parcelle_id or quantite <= 0:
            flash("Campagne et quantité obligatoires", "warning")
        else:
            try:
                # Récupérer infos
                c.execute("""SELECT cp.*, pa.producteur_id, pa.id AS parcelle_id,
                                    pa.superficie_ha, cp.culture_id
                             FROM cultures_parcelles cp
                             LEFT JOIN parcelles pa ON cp.parcelle_id = pa.id
                             WHERE cp.id=?""", (culture_parcelle_id,))
                cp = c.fetchone()

                if not cp:
                    flash("Campagne introuvable", "warning")
                else:
                    # Générer code
                    c.execute("SELECT COUNT(*) FROM recoltes")
                    n = (c.fetchone()[0] or 0) + 1
                    code = f"REC-{datetime.now().year}-{n:05d}"

                    c.execute("""INSERT INTO recoltes
                        (code, culture_parcelle_id, producteur_id, parcelle_id, culture_id,
                         date_recolte, quantite_kg, qualite, humidite_pct, destination,
                         prix_vente_kg, acheteur, notes, created_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (code, culture_parcelle_id, cp['producteur_id'], cp['parcelle_id'], cp['culture_id'],
                         request.form.get('date_recolte') or datetime.now().date().isoformat(),
                         quantite,
                         request.form.get('qualite') or 'Bonne',
                         float(request.form.get('humidite_pct') or 0) or None,
                         request.form.get('destination') or 'Stock',
                         int(request.form.get('prix_vente_kg') or 0) or None,
                         (request.form.get('acheteur') or '').strip(),
                         (request.form.get('notes') or '').strip(),
                         datetime.now().isoformat()))
                    rec_id = c.lastrowid

                    # Mettre à jour la culture
                    superficie = cp['superficie_ha'] or 1
                    rendement_t_ha = (quantite / 1000) / superficie

                    c.execute("""UPDATE cultures_parcelles SET
                        date_reelle_recolte=?, etat='Récolté', rendement_obtenu_t_ha=?
                        WHERE id=?""",
                        (request.form.get('date_recolte') or datetime.now().date().isoformat(),
                         round(rendement_t_ha, 3), culture_parcelle_id))

                    # Mettre à jour stock
                    c.execute("""SELECT id FROM stocks_produits
                                 WHERE producteur_id=? AND culture_id=?""",
                              (cp['producteur_id'], cp['culture_id']))
                    stock_row = c.fetchone()
                    if stock_row:
                        c.execute("""UPDATE stocks_produits SET
                            quantite_kg = quantite_kg + ?,
                            date_derniere_entree=?,
                            updated_at=?
                            WHERE id=?""",
                            (quantite, datetime.now().date().isoformat(),
                             datetime.now().isoformat(), stock_row['id']))
                    else:
                        c.execute("""INSERT INTO stocks_produits
                            (producteur_id, culture_id, qualite, quantite_kg,
                             prix_revient_kg, date_derniere_entree, emplacement, updated_at)
                            VALUES (?,?,?,?,?,?,?,?)""",
                            (cp['producteur_id'], cp['culture_id'],
                             request.form.get('qualite') or 'Bonne',
                             quantite, 150,
                             datetime.now().date().isoformat(),
                             'Magasin', datetime.now().isoformat()))

                    conn.commit()
                    _log('CREATE_RECOLTE',
                         f"Récolte {code} : {quantite}kg sur parcelle {cp['parcelle_id']}",
                         entity='recolte', entity_id=rec_id)
                    flash(f"Récolte {code} enregistrée ({_fmt_kg(quantite)})", "success")
                    conn.close()
                    return redirect('/recoltes')
            except Exception as e:
                import traceback; traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    # GET : campagnes en cours
    c.execute("""SELECT cp.id, cp.date_semis, cp.etat,
                        c.nom AS culture_nom, c.icone,
                        pa.code AS parcelle_code, pa.superficie_ha,
                        p.nom AS producteur_nom, p.prenom AS producteur_prenom
                 FROM cultures_parcelles cp
                 LEFT JOIN cultures c ON cp.culture_id = c.id
                 LEFT JOIN parcelles pa ON cp.parcelle_id = pa.id
                 LEFT JOIN producteurs p ON pa.producteur_id = p.id
                 WHERE cp.etat IN ('Semé', 'En croissance', 'Maturité')
                 ORDER BY cp.date_semis DESC""")
    campagnes = c.fetchall()
    conn.close()

    opt_cp = ''
    for cp in campagnes:
        opt_cp += f'<option value="{cp["id"]}">{cp["parcelle_code"]} — {cp["culture_nom"]} · semé le {cp["date_semis"]} · {cp["producteur_prenom"] or ""} {cp["producteur_nom"] or ""}</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-wheat-awn"></i> Nouvelle récolte</h2>
        <div class="page-subtitle">Enregistrer la production</div></div>
      <a href="/recoltes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group form-full">
            <label>Campagne (parcelle × culture) *</label>
            <select name="culture_parcelle_id" required>
              <option value="">— Choisir une campagne en cours —</option>{opt_cp}
            </select>
          </div>
          <div class="form-group"><label>Date de récolte *</label>
            <input type="date" name="date_recolte" value="{datetime.now().date().isoformat()}" required></div>
          <div class="form-group"><label>Quantité (kg) *</label>
            <input type="number" step="0.1" name="quantite_kg" required value="500"></div>
          <div class="form-group"><label>Qualité</label>
            <select name="qualite">
              <option>Excellente</option><option selected>Bonne</option>
              <option>Moyenne</option><option>Médiocre</option>
            </select>
          </div>
          <div class="form-group"><label>Humidité (%)</label>
            <input type="number" step="0.1" name="humidite_pct" placeholder="12"></div>
          <div class="form-group"><label>Destination</label>
            <select name="destination">
              <option>Stock</option><option>Vente directe</option>
              <option>Coopérative</option><option>Autoconsommation</option>
            </select>
          </div>
          <div class="form-group"><label>Prix vente (FCFA/kg)</label>
            <input type="number" name="prix_vente_kg" value="0"></div>
          <div class="form-group"><label>Acheteur</label>
            <input type="text" name="acheteur" placeholder="Nom de l'acheteur"></div>
          <div class="form-group form-full"><label>Notes</label>
            <textarea name="notes" rows="2"></textarea></div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer la récolte</button>
          <a href="/recoltes" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='recoltes', title='Nouvelle récolte')


# ================================================================
# ==================== ITINÉRAIRE TECHNIQUE ====================
# ================================================================
@agri_bp.route('/itineraire/<int:cp_id>')
@_auth_required
def itineraire_list(cp_id):
    if not _can_produce():
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT cp.*, c.nom AS culture_nom, c.icone,
                        pa.code AS parcelle_code, pa.superficie_ha,
                        p.nom AS producteur_nom, p.prenom AS producteur_prenom
                 FROM cultures_parcelles cp
                 LEFT JOIN cultures c ON cp.culture_id = c.id
                 LEFT JOIN parcelles pa ON cp.parcelle_id = pa.id
                 LEFT JOIN producteurs p ON pa.producteur_id = p.id
                 WHERE cp.id=?""", (cp_id,))
    cp = c.fetchone()
    if not cp:
        conn.close()
        flash("Campagne introuvable", "danger")
        return redirect('/cultures')

    c.execute("""SELECT * FROM itineraire_technique
                 WHERE culture_parcelle_id=?
                 ORDER BY date_operation DESC""", (cp_id,))
    operations = c.fetchall()

    c.execute("SELECT COALESCE(SUM(cout), 0) AS total FROM itineraire_technique WHERE culture_parcelle_id=?", (cp_id,))
    cout_total = c.fetchone()['total']
    conn.close()

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-tasks"></i> Itinéraire technique</h2>
        <div class="page-subtitle">
          {cp['parcelle_code']} — <i class="fas {cp['icone'] or 'fa-seedling'}"></i> {cp['culture_nom']}
          · semé le {cp['date_semis']}
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/parcelles/{cp['parcelle_id'] if 'parcelle_id' in cp.keys() else ''}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        {'<a href="/itineraire/'+str(cp_id)+'/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle opération</a>' if _can_produce() else ''}
      </div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-tasks"></i></div>
        <div class="stat-value">{len(operations)}</div>
        <div class="stat-label">Opérations</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-coins"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(cout_total)}</div>
        <div class="stat-label">Coût total</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-ruler-combined"></i></div>
        <div class="stat-value">{cp['superficie_ha'] or '-'} ha</div>
        <div class="stat-label">Superficie</div></div>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Date</th><th>Type d'opération</th><th>Description</th>
          <th>Produit</th><th>Quantité</th><th>Coût</th><th>Statut</th>
        </tr></thead><tbody>
    """
    for op in operations:
        badge = 'badge-success'
        if op['statut'] == 'Planifié': badge = 'badge-info'
        elif op['statut'] == 'En cours': badge = 'badge-warning'
        content += f"""
        <tr>
          <td>{op['date_operation']}</td>
          <td><strong>{op['type_operation']}</strong></td>
          <td><small>{op['description'] or '-'}</small></td>
          <td>{op['produit_utilise'] or '-'}</td>
          <td>{op['quantite'] or '-'} {op['unite'] or ''}</td>
          <td>{_fmt_fcfa(op['cout'])}</td>
          <td><span class="badge {badge}">{op['statut']}</span></td>
        </tr>"""
    if not operations:
        content += '<tr><td colspan="7" class="empty">Aucune opération enregistrée</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='cultures', title='Itinéraire technique')


@agri_bp.route('/itineraire/<int:cp_id>/nouvelle', methods=['GET', 'POST'])
@_auth_required
def itineraire_new(cp_id):
    if not _can_produce():
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        c.execute("""INSERT INTO itineraire_technique
            (culture_parcelle_id, type_operation, date_operation, description,
             produit_utilise, quantite, unite, cout, operateur, statut, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (cp_id,
             request.form.get('type_operation') or 'Autre',
             request.form.get('date_operation') or datetime.now().date().isoformat(),
             (request.form.get('description') or '').strip(),
             (request.form.get('produit_utilise') or '').strip(),
             float(request.form.get('quantite') or 0) or None,
             request.form.get('unite') or 'kg',
             int(request.form.get('cout') or 0),
             (request.form.get('operateur') or '').strip(),
             request.form.get('statut') or 'Réalisé',
             datetime.now().isoformat()))
        conn.commit()
        _log('CREATE_ITINERAIRE', f"Opération ajoutée pour campagne id={cp_id}",
             entity='itineraire', entity_id=c.lastrowid)
        flash("Opération enregistrée", "success")
        conn.close()
        return redirect(f'/itineraire/{cp_id}')

    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus"></i> Nouvelle opération</h2></div>
      <a href="/itineraire/{cp_id}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group"><label>Type d'opération *</label>
            <select name="type_operation" required>
              <option>Labour</option><option>Semis</option><option>Fertilisation</option>
              <option>Traitement phytosanitaire</option><option>Irrigation</option>
              <option>Désherbage</option><option>Récolte</option><option>Autre</option>
            </select>
          </div>
          <div class="form-group"><label>Date *</label>
            <input type="date" name="date_operation" value="{datetime.now().date().isoformat()}" required></div>
          <div class="form-group form-full"><label>Description</label>
            <textarea name="description" rows="2"></textarea></div>
          <div class="form-group"><label>Produit utilisé</label>
            <input type="text" name="produit_utilise" placeholder="Ex: NPK 15-15-15"></div>
          <div class="form-group"><label>Quantité</label>
            <input type="number" step="0.1" name="quantite"></div>
          <div class="form-group"><label>Unité</label>
            <select name="unite">
              <option>kg</option><option>L</option><option>sac</option><option>unité</option>
            </select>
          </div>
          <div class="form-group"><label>Coût (FCFA)</label>
            <input type="number" name="cout" value="0"></div>
          <div class="form-group"><label>Opérateur</label>
            <input type="text" name="operateur"></div>
          <div class="form-group"><label>Statut</label>
            <select name="statut">
              <option>Réalisé</option><option>En cours</option><option>Planifié</option>
            </select>
          </div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
          <a href="/itineraire/{cp_id}" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='cultures', title='Nouvelle opération')


# ================================================================
# ==================== MOBILE MONEY ====================
# ================================================================
@agri_bp.route('/mobile-money')
@_auth_required
def mobile_money_list():
    if current_user.role not in ('admin', 'direction', 'finance'):
        flash("Accès réservé", "danger")
        return redirect('/')

    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')
    fournisseur = request.args.get('fournisseur') or ''

    conn = _db()
    c = conn.cursor()
    sql = """SELECT t.*, p.nom AS producteur_nom, p.prenom AS producteur_prenom
             FROM transactions_mobile t
             LEFT JOIN producteurs p ON t.producteur_id = p.id
             WHERE strftime('%Y-%m', t.date_transaction)=?"""
    params = [mois]
    if fournisseur:
        sql += " AND t.fournisseur=?"
        params.append(fournisseur)
    sql += " ORDER BY t.date_transaction DESC LIMIT 200"
    c.execute(sql, params)
    transactions = c.fetchall()

    # Stats par fournisseur
    c.execute("""SELECT fournisseur,
                        COUNT(*) AS nb,
                        COALESCE(SUM(montant), 0) AS total
                 FROM transactions_mobile
                 WHERE strftime('%Y-%m', date_transaction)=? AND statut='Réussi'
                 GROUP BY fournisseur""", (mois,))
    stats_fournisseurs = c.fetchall()

    # Total
    c.execute("""SELECT COUNT(*) AS nb, COALESCE(SUM(montant), 0) AS total
                 FROM transactions_mobile
                 WHERE strftime('%Y-%m', date_transaction)=? AND statut='Réussi'""", (mois,))
    stats = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-mobile-screen"></i> Transactions Mobile Money</h2>
        <div class="page-subtitle">{len(transactions)} transactions — {mois}</div></div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-list"></i></div>
        <div class="stat-value">{stats['nb']}</div>
        <div class="stat-label">Transactions réussies</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-money-bill-wave"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(stats['total'])}</div>
        <div class="stat-label">Montant total</div></div>
    """
    for sf in stats_fournisseurs:
        color = '#10b981' if sf['fournisseur'] == 'Wave' else ('#f97316' if sf['fournisseur'] == 'Orange Money' else '#dc2626')
        content += f"""
      <div class="stat-card" style="border-left-color:{color}">
        <div class="stat-icon" style="color:{color}"><i class="fas fa-mobile-screen"></i></div>
        <div class="stat-value" style="font-size:1.2rem">{_fmt_fcfa(sf['total'])}</div>
        <div class="stat-label">{sf['fournisseur']} ({sf['nb']})</div>
      </div>
    """
    content += "</div>"

    content += f"""
    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap">
        <input type="month" name="mois" value="{mois}"
               style="flex:1;padding:12px 15px;border:2px solid #f1f5f9;border-radius:11px">
        <select name="fournisseur" style="flex:1;padding:12px 15px;border:2px solid #f1f5f9;border-radius:11px">
          <option value="">Tous fournisseurs</option>
          <option value="Wave" {"selected" if fournisseur=="Wave" else ""}>Wave</option>
          <option value="Orange Money" {"selected" if fournisseur=="Orange Money" else ""}>Orange Money</option>
          <option value="Free Money" {"selected" if fournisseur=="Free Money" else ""}>Free Money</option>
        </select>
        <button class="btn btn-primary"><i class="fas fa-filter"></i> Filtrer</button>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Date</th><th>Référence</th><th>Fournisseur</th>
          <th>Producteur</th><th>Type</th><th>Montant</th><th>Statut</th>
        </tr></thead><tbody>
    """
    for t in transactions:
        color = '#10b981' if t['fournisseur'] == 'Wave' else ('#f97316' if t['fournisseur'] == 'Orange Money' else '#dc2626')
        badge = 'badge-success'
        if t['statut'] == 'En attente': badge = 'badge-warning'
        elif t['statut'] == 'Échoué': badge = 'badge-danger'
        content += f"""
        <tr>
          <td><small>{t['date_transaction'][:16] if t['date_transaction'] else '-'}</small></td>
          <td><small>{t['reference']}</small></td>
          <td><span class="badge" style="background:{color}20;color:{color}">{t['fournisseur']}</span></td>
          <td>{t['producteur_prenom'] or ''} {t['producteur_nom'] or ''}</td>
          <td>{t['type_transaction']}</td>
          <td><strong>{_fmt_fcfa(t['montant'])}</strong></td>
          <td><span class="badge {badge}">{t['statut']}</span></td>
        </tr>"""
    if not transactions:
        content += '<tr><td colspan="7" class="empty">Aucune transaction</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='finance', title='Mobile Money')


# ================================================================
# ==================== STATISTIQUES ====================
# ================================================================
@agri_bp.route('/statistiques')
@_auth_required
def statistiques():
    if current_user.role not in ('admin', 'direction', 'finance'):
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()

    # Par région
    c.execute("""SELECT r.nom,
                        COUNT(DISTINCT p.id) AS nb_producteurs,
                        COALESCE(SUM(pa.superficie_ha), 0) AS superficie
                 FROM regions r
                 LEFT JOIN departements d ON d.region_id = r.id
                 LEFT JOIN villages v ON v.departement_id = d.id
                 LEFT JOIN producteurs p ON p.village_id = v.id AND p.actif=1
                 LEFT JOIN parcelles pa ON pa.producteur_id = p.id AND pa.actif=1
                 GROUP BY r.id
                 ORDER BY superficie DESC""")
    par_region = c.fetchall()

    # Top producteurs
    c.execute("""SELECT p.nom, p.prenom, p.code,
                        COALESCE(SUM(r.quantite_kg), 0) AS production
                 FROM producteurs p
                 LEFT JOIN recoltes r ON r.producteur_id = p.id
                 WHERE p.actif=1
                 GROUP BY p.id
                 ORDER BY production DESC LIMIT 10""")
    top_producteurs = c.fetchall()

    # Production par culture
    c.execute("""SELECT c.nom, c.icone,
                        COALESCE(SUM(r.quantite_kg), 0) AS production,
                        COUNT(DISTINCT r.producteur_id) AS nb_producteurs
                 FROM cultures c
                 LEFT JOIN recoltes r ON r.culture_id = c.id
                 GROUP BY c.id
                 HAVING production > 0
                 ORDER BY production DESC LIMIT 10""")
    par_culture = c.fetchall()

    # Ventes par mois
    c.execute("""SELECT strftime('%Y-%m', date_vente) AS mois,
                        COUNT(*) AS nb,
                        COALESCE(SUM(montant_total), 0) AS total
                 FROM ventes
                 WHERE date(date_vente) >= date('now', '-6 months')
                 GROUP BY mois ORDER BY mois""")
    ventes_mois = c.fetchall()

    conn.close()

    max_prod = max([x['production'] for x in par_culture], default=1)
    max_sup = max([x['superficie'] for x in par_region], default=1)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-chart-line"></i> Statistiques</h2>
        <div class="page-subtitle">Analyses agricoles du Sénégal</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-map"></i> Répartition par région</h3></div>
    """
    for r in par_region:
        pct = (r['superficie'] / max_sup * 100) if max_sup else 0
        content += f"""
        <div style="margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <span style="font-weight:700">{r['nom']}</span>
            <strong style="color:#10b981">{r['nb_producteurs']} producteurs · {r['superficie']:.0f} ha</strong>
          </div>
          <div style="background:#f0fdf4;border-radius:6px;height:10px;overflow:hidden">
            <div style="background:linear-gradient(90deg,#065f46,#10b981);height:100%;width:{pct}%"></div>
          </div>
        </div>"""
    content += "</div>"

    content += """
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div class="card">
        <div class="card-header"><h3><i class="fas fa-trophy"></i> Top 10 producteurs</h3></div>
        <div class="table-wrap"><table>
          <thead><tr><th>#</th><th>Producteur</th><th>Production</th></tr></thead>
          <tbody>"""
    for i, p in enumerate(top_producteurs, 1):
        content += f"""
        <tr>
          <td><span class="badge badge-primary">#{i}</span></td>
          <td>{p['prenom'] or ''} {p['nom'] or ''}</td>
          <td><strong>{_fmt_kg(p['production'])}</strong></td>
        </tr>"""
    content += "</tbody></table></div></div>"

    content += """
      <div class="card">
        <div class="card-header"><h3><i class="fas fa-seedling"></i> Production par culture</h3></div>"""
    for cu in par_culture:
        pct = (cu['production'] / max_prod * 100) if max_prod else 0
        content += f"""
        <div style="margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <span style="font-weight:700"><i class="fas {cu['icone'] or 'fa-seedling'}" style="color:#10b981"></i> {cu['nom']}</span>
            <strong style="color:#10b981">{_fmt_kg(cu['production'])}</strong>
          </div>
          <div style="background:#f0fdf4;border-radius:6px;height:8px;overflow:hidden">
            <div style="background:linear-gradient(90deg,#065f46,#34d399);height:100%;width:{pct}%"></div>
          </div>
          <div style="font-size:0.72rem;color:#94a3b8;margin-top:3px">{cu['nb_producteurs']} producteurs</div>
        </div>"""
    content += "</div></div>"

    # Ventes par mois
    if ventes_mois:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-money-bill-wave"></i> Ventes par mois</h3></div>
          <div class="table-wrap"><table>
            <thead><tr><th>Mois</th><th>Nb ventes</th><th>CA total</th></tr></thead>
            <tbody>"""
        for v in ventes_mois:
            content += f"""
            <tr>
              <td><strong>{v['mois']}</strong></td>
              <td>{v['nb']}</td>
              <td><strong>{_fmt_fcfa(v['total'])}</strong></td>
            </tr>"""
        content += "</tbody></table></div></div>"

    return _render(content, active='statistiques', title='Statistiques')


# ================================================================
# ==================== API ====================
# ================================================================
@agri_bp.route('/api/stats-agri')
@_auth_required
def api_stats_agri():
    conn = _db()
    c = conn.cursor()

    c.execute("""SELECT COALESCE(SUM(quantite_kg), 0) AS total FROM recoltes""")
    prod_totale = c.fetchone()['total']

    c.execute("""SELECT COALESCE(SUM(montant_total), 0) AS total FROM ventes
                 WHERE statut_paiement='Payé'""")
    ca_total = c.fetchone()['total']

    c.execute("""SELECT COUNT(*) FROM transactions_mobile WHERE statut='Réussi'""")
    nb_mm = c.fetchone()[0]

    conn.close()
    return jsonify(production_totale_kg=prod_totale,
                   chiffre_affaires_fcfa=ca_total,
                   transactions_mobile=nb_mm,
                   timestamp=datetime.now().isoformat())
