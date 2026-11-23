"""
📱 MicroFinance 2.0 — Mobile Money
Wave · Orange Money · Free Money
"""
from flask import Blueprint, request, redirect, flash, jsonify
from flask_login import current_user
import sqlite3
import random
from datetime import datetime, timedelta

mm_bp = Blueprint('mm', __name__)
_deps = {}


def init_mobile_money(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(mm_bp)
    print("[MM] ✅ Module Mobile Money complet enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='mm', title='Mobile Money'):
    return _deps['render_page'](content, active=active, page_title=title)


def _auth_required(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if not (current_user and current_user.is_authenticated):
            return redirect('/login')
        return f(*a, **k)
    return w


def _can_operate():
    return current_user and current_user.role in ('admin', 'directeur', 'caissier', 'agent')


def _fmt_fcfa(m):
    if not m:
        return "0 F"
    return f"{int(m):,} F".replace(",", " ")


def _fmt_date(d):
    if not d:
        return "-"
    return d[:16] if len(d) >= 16 else d


# ================================================================
# ==================== MOBILE MONEY — LISTE ====================
# ================================================================
@mm_bp.route('/mobile-money')
@_auth_required
def mm_home():
    if not _can_operate():
        flash("Accès réservé", "danger")
        return redirect('/')

    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')
    fournisseur = request.args.get('fournisseur') or ''

    conn = _db()
    c = conn.cursor()

    sql = """SELECT t.*, cl.nom AS client_nom, cl.prenom AS client_prenom,
                    cl.code AS client_code
             FROM transactions_mobile t
             LEFT JOIN clients cl ON t.client_id = cl.id
             WHERE strftime('%Y-%m', t.date_initiation) = ?"""
    params = [mois]
    if fournisseur:
        sql += " AND t.fournisseur=?"
        params.append(fournisseur)
    sql += " ORDER BY t.date_initiation DESC LIMIT 200"
    c.execute(sql, params)
    transactions = c.fetchall()

    # Stats par fournisseur
    c.execute("""SELECT fournisseur,
                        COUNT(*) AS nb,
                        COALESCE(SUM(montant), 0) AS total
                 FROM transactions_mobile
                 WHERE strftime('%Y-%m', date_initiation)=? AND statut='Réussi'
                 GROUP BY fournisseur""", (mois,))
    stats_fournisseurs = c.fetchall()

    # Total mois
    c.execute("""SELECT COUNT(*) AS nb, COALESCE(SUM(montant), 0) AS total,
                        SUM(CASE WHEN statut='Réussi' THEN 1 ELSE 0 END) AS reussies
                 FROM transactions_mobile
                 WHERE strftime('%Y-%m', date_initiation)=?""", (mois,))
    stats_mois = c.fetchone()

    # Total all-time
    c.execute("""SELECT COALESCE(SUM(montant), 0) AS total FROM transactions_mobile
                 WHERE statut='Réussi'""")
    total_all = c.fetchone()['total']

    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-mobile-screen"></i> Mobile Money</h2>
        <div class="page-subtitle">Transactions Wave · Orange Money · Free Money — {mois}</div></div>
      {'<a href="/mobile-money/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle transaction</a>' if _can_operate() else ''}
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-list"></i></div>
        <div class="stat-value">{stats_mois['nb'] or 0}</div>
        <div class="stat-label">Transactions (mois)</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-money-bill-wave"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(stats_mois['total'])}</div>
        <div class="stat-label">Montant mois</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-check-circle"></i></div>
        <div class="stat-value">{stats_mois['reussies'] or 0}</div>
        <div class="stat-label">Réussies</div></div>
      <div class="stat-card purple"><div class="stat-icon"><i class="fas fa-database"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(total_all)}</div>
        <div class="stat-label">Total historique</div></div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:20px;margin-bottom:25px">
    """
    for sf in stats_fournisseurs:
        color = '#10b981' if sf['fournisseur'] == 'Wave' else ('#f97316' if sf['fournisseur'] == 'Orange Money' else '#dc2626')
        content += f"""
      <div class="card" style="border-left:5px solid {color};padding:20px">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div>
            <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">{sf['fournisseur']}</div>
            <div style="font-size:1.5rem;font-weight:900;color:{color};margin-top:5px">{_fmt_fcfa(sf['total'])}</div>
            <div style="font-size:0.75rem;color:#94a3b8;margin-top:3px">{sf['nb']} transactions</div>
          </div>
          <i class="fas fa-mobile-screen" style="font-size:2rem;color:{color};opacity:0.3"></i>
        </div>
      </div>
    """
    content += "</div>"

    content += f"""
    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Mois</label>
          <input type="month" name="mois" value="{mois}"
                 style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:180px">
          <label>Fournisseur</label>
          <select name="fournisseur" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
            <option value="">Tous</option>
            <option value="Wave" {"selected" if fournisseur=="Wave" else ""}>Wave</option>
            <option value="Orange Money" {"selected" if fournisseur=="Orange Money" else ""}>Orange Money</option>
            <option value="Free Money" {"selected" if fournisseur=="Free Money" else ""}>Free Money</option>
          </select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-filter"></i> Filtrer</button>
        <a href="/mobile-money" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Référence</th><th>Date</th><th>Fournisseur</th><th>Client</th>
          <th>Type</th><th>Montant</th><th>Statut</th>
        </tr></thead><tbody>
    """
    for t in transactions:
        color = '#10b981' if t['fournisseur'] == 'Wave' else ('#f97316' if t['fournisseur'] == 'Orange Money' else '#dc2626')
        badge = 'badge-success' if t['statut'] == 'Réussi' else ('badge-warning' if t['statut'] == 'En attente' else 'badge-danger')

        content += f"""
        <tr>
          <td><small>{t['reference']}</small></td>
          <td><small>{_fmt_date(t['date_initiation'])}</small></td>
          <td><span class="badge" style="background:{color}20;color:{color}">{t['fournisseur']}</span></td>
          <td>
            <div style="font-weight:700">{t['client_prenom'] or ''} {t['client_nom'] or ''}</div>
            <div style="font-size:0.72rem;color:#94a3b8">{t['client_code'] or '-'}</div>
          </td>
          <td><span class="badge badge-info">{t['type_transaction']}</span></td>
          <td><strong>{_fmt_fcfa(t['montant'])}</strong></td>
          <td><span class="badge {badge}">{t['statut']}</span></td>
        </tr>"""
    if not transactions:
        content += '<tr><td colspan="7" class="empty"><i class="fas fa-mobile-screen"></i><br>Aucune transaction</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='mm', title='Mobile Money')


# ================================================================
# ==================== MOBILE MONEY — NOUVELLE ====================
# ================================================================
@mm_bp.route('/mobile-money/nouvelle', methods=['GET', 'POST'])
@_auth_required
def mm_new():
    if not _can_operate():
        flash("Accès réservé", "danger")
        return redirect('/mobile-money')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        client_id = request.form.get('client_id')
        fournisseur = request.form.get('fournisseur') or 'Wave'
        telephone = (request.form.get('telephone') or '').strip()
        type_t = request.form.get('type_transaction') or 'Dépôt'
        montant = int(request.form.get('montant') or 0)

        if not client_id or not telephone or montant <= 0:
            flash("Tous les champs obligatoires", "warning")
        else:
            try:
                c.execute("SELECT COUNT(*) FROM transactions_mobile")
                n = (c.fetchone()[0] or 0) + 1
                ref = f"MM-{datetime.now().strftime('%Y%m%d')}-{n:05d}"

                # Simulation : statut aléatoire (90% réussi)
                statut = 'Réussi' if random.random() < 0.9 else random.choice(['En attente', 'Échoué'])
                frais = int(montant * 0.01) if montant > 5000 else 0

                c.execute("""INSERT INTO transactions_mobile
                    (reference, client_id, fournisseur, telephone,
                     type_transaction, montant, frais, statut,
                     date_initiation, date_completion)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (ref, client_id, fournisseur, telephone,
                     type_t, montant, frais, statut,
                     datetime.now().isoformat(),
                     datetime.now().isoformat() if statut == 'Réussi' else None))

                conn.commit()
                _deps['log_action'](current_user.id, 'MM_TRANSACTION',
                                    f"{type_t} {fournisseur} de {_fmt_fcfa(montant)}",
                                    entity='transaction', entity_id=c.lastrowid)
                flash(f"Transaction {ref} : {statut}", "success" if statut == 'Réussi' else "warning")
                conn.close()
                return redirect('/mobile-money')
            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    c.execute("SELECT id, code, nom, prenom, telephone FROM clients WHERE actif=1 ORDER BY nom LIMIT 200")
    clients = c.fetchall()
    conn.close()

    opt_cl = ''.join(
        f'<option value="{cl["id"]}" data-tel="{cl["telephone"] or ""}">{cl["code"]} — {cl["prenom"] or ""} {cl["nom"]}</option>'
        for cl in clients)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus"></i> Nouvelle transaction Mobile Money</h2></div>
      <a href="/mobile-money" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="form-group" style="grid-column:1/-1"><label>Client *</label>
            <select name="client_id" id="client_select" required
                    style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="">— Choisir —</option>{opt_cl}
            </select>
          </div>
          <div class="form-group"><label>Fournisseur *</label>
            <select name="fournisseur" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option value="Wave">📱 Wave</option>
              <option value="Orange Money">📱 Orange Money</option>
              <option value="Free Money">📱 Free Money</option>
            </select>
          </div>
          <div class="form-group"><label>Téléphone Mobile Money *</label>
            <input type="text" name="telephone" id="tel_input" required placeholder="77 123 45 67"
                   style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
          <div class="form-group"><label>Type de transaction *</label>
            <select name="type_transaction" required style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
              <option>Dépôt</option>
              <option>Retrait</option>
              <option>Remboursement</option>
              <option>Paiement</option>
              <option>Transfert</option>
            </select>
          </div>
          <div class="form-group"><label>Montant (FCFA) *</label>
            <input type="number" name="montant" required min="100" value="10000"
                   style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
          </div>
        </div>

        <div style="padding:20px;background:#f0fdff;border-radius:12px;margin-top:20px;border-left:5px solid #06b6d4">
          <h4 style="color:#0e7490;margin-bottom:8px"><i class="fas fa-info-circle"></i> Simulation</h4>
          <p style="font-size:0.85rem;color:#475569">
            Les frais sont de <strong>1%</strong> pour les montants &gt; 5 000 F.
            La transaction est simulée : 90% de réussite.
          </p>
        </div>

        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
          <a href="/mobile-money" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>

    <script>
    document.getElementById('client_select').addEventListener('change', function() {{
      const opt = this.options[this.selectedIndex];
      const tel = opt.dataset.tel;
      if (tel) document.getElementById('tel_input').value = tel;
    }});
    </script>"""
    return _render(content, active='mm', title='Nouvelle transaction')


# ================================================================
# ==================== LCB-FT ========================
# ================================================================
@mm_bp.route('/lcb-ft')
@_auth_required
def lcb_ft_home():
    if current_user.role not in ('admin', 'auditeur'):
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()

    # Stats
    c.execute("SELECT COUNT(*) FROM declarations_soupcon WHERE statut='À analyser'")
    a_analyser = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM declarations_soupcon WHERE statut='Transmis CENTIF'")
    transmises = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM alertes_lcb WHERE statut='Active'")
    alertes_actives = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM listes_surveillance WHERE actif=1")
    listes = c.fetchone()[0] or 0

    # Déclarations récentes
    c.execute("""SELECT d.*, cl.nom AS client_nom, cl.prenom AS client_prenom,
                        cl.code AS client_code
                 FROM declarations_soupcon d
                 LEFT JOIN clients cl ON d.client_id = cl.id
                 ORDER BY d.date_detection DESC LIMIT 30""")
    declarations = c.fetchall()

    # Alertes
    c.execute("""SELECT a.*, cl.nom AS client_nom, cl.prenom AS client_prenom
                 FROM alertes_lcb a
                 LEFT JOIN clients cl ON a.client_id = cl.id
                 WHERE a.statut='Active'
                 ORDER BY a.created_at DESC LIMIT 20""")
    alertes = c.fetchall()

    # Transactions suspectes (montant > 5M)
    c.execute("""SELECT t.*, cl.nom AS client_nom, cl.prenom AS client_prenom
                 FROM transactions_mobile t
                 LEFT JOIN clients cl ON t.client_id = cl.id
                 WHERE t.montant >= 5000000 AND t.statut='Réussi'
                 ORDER BY t.date_initiation DESC LIMIT 10""")
    suspectes = c.fetchall()

    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-shield-halved"></i> LCB-FT</h2>
        <div class="page-subtitle">Lutte contre le Blanchiment & le Financement du Terrorisme</div></div>
    </div>

    <div class="stats">
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-file-signature"></i></div>
        <div class="stat-value">{a_analyser}</div>
        <div class="stat-label">À analyser</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-paper-plane"></i></div>
        <div class="stat-value">{transmises}</div>
        <div class="stat-label">Transmises CENTIF</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-bell"></i></div>
        <div class="stat-value">{alertes_actives}</div>
        <div class="stat-label">Alertes actives</div></div>
      <div class="stat-card purple"><div class="stat-icon"><i class="fas fa-list"></i></div>
        <div class="stat-value">{listes}</div>
        <div class="stat-label">Listes surveillance</div></div>
    </div>


    <div class="card">
      <div class="card-header"><h3><i class="fas fa-file-signature"></i> Déclarations de soupçon</h3></div>
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Référence</th><th>Date</th><th>Client</th>
          <th>Type alerte</th><th>Niveau</th><th>Montant</th><th>Statut</th>
        </tr></thead><tbody>
    """
    for d in declarations:
        badge_statut = 'badge-warning' if d['statut'] == 'À analyser' else 'badge-success'
        badge_risque = 'badge-danger' if d['niveau_risque'] == 'Élevé' else 'badge-warning'

        content += f"""
        <tr>
          <td><small>{d['reference']}</small></td>
          <td>{_fmt_date(d['date_detection'])}</td>
          <td>{d['client_prenom'] or ''} {d['client_nom'] or ''}</td>
          <td><span class="badge badge-info">{d['type_alerte'] or '-'}</span></td>
          <td><span class="badge {badge_risque}">{d['niveau_risque'] or '-'}</span></td>
          <td><strong>{_fmt_fcfa(d['montant_implique'])}</strong></td>
          <td><span class="badge {badge_statut}">{d['statut']}</span></td>
        </tr>"""
    if not declarations:
        content += '<tr><td colspan="7" class="empty">Aucune déclaration</td></tr>'
    content += "</tbody></table></div></div>"

    # Alertes
    if alertes:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-bell"></i> Alertes actives</h3></div>
          <div class="table-wrap"><table>
            <thead><tr><th>Date</th><th>Client</th><th>Type</th>
                       <th>Description</th><th>Gravité</th></tr></thead>
            <tbody>"""
        for a in alertes:
            badge = 'badge-danger' if a['gravite'] == 'Critique' else 'badge-warning'
            content += f"""
            <tr>
              <td>{_fmt_date(a['created_at'])}</td>
              <td>{a['client_prenom'] or ''} {a['client_nom'] or ''}</td>
              <td>{a['type_alerte'] or '-'}</td>
              <td><small>{a['description'] or '-'}</small></td>
              <td><span class="badge {badge}">{a['gravite']}</span></td>
            </tr>"""
        content += "</tbody></table></div></div>"

    content += """
    <div class="card" style="border-left:5px solid #0e7490">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Conformité LCB-FT</h3></div>
      <p style="color:#475569;line-height:1.7;font-size:0.9rem">
        Ce module assure la conformité avec la <strong>Directive BCEAO n°02/2015</strong> et la
        <strong>Loi sénégalaise n°2018-03</strong> relative à la lutte contre le blanchiment de capitaux.
        Les transactions suspectes sont automatiquement détectées selon les seuils réglementaires.
      </p>
    </div>
    """
    return _render(content, active='lcb', title='LCB-FT')
