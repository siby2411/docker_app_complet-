"""
Omega Pointage V2 — Logique métier complète
Saisie pointage · Calcul heures · Plannings · Congés · Alertes · Export
"""
from flask import Blueprint, request, redirect, flash, jsonify, send_file, Response
from flask_login import current_user
import sqlite3
import io
import csv
from datetime import datetime, timedelta

pointage_bp = Blueprint('pointage', __name__)
_deps = {}


def init_pointage(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(pointage_bp)
    print("[POINTAGE] ✅ Module logique complet enregistré")


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


def _can_write():
    return current_user and current_user.role in ('admin', 'rh', 'chef', 'pointage')


def _fmt_duree(minutes):
    if not minutes:
        return "0h00"
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}h{m:02d}"


def _calc_duree(heure_entree, heure_sortie, pause_min=60):
    """Calcule durée en minutes entre 2 heures HH:MM"""
    if not (heure_entree and heure_sortie):
        return None
    try:
        he = int(heure_entree.split(':')[0]) * 60 + int(heure_entree.split(':')[1])
        hs = int(heure_sortie.split(':')[0]) * 60 + int(heure_sortie.split(':')[1])
        # Gérer passage minuit
        if hs < he:
            hs += 24 * 60
        return hs - he - pause_min
    except Exception:
        return None


def _calc_statut(heure_entree, tolerance_min=10):
    """Détermine si retard selon heure prévue 08:00"""
    if not heure_entree:
        return 'Normal'
    try:
        h = int(heure_entree.split(':')[0]) * 60 + int(heure_entree.split(':')[1])
        ref = 8 * 60  # 08:00
        if h > ref + tolerance_min:
            return 'Retard'
        return 'Normal'
    except Exception:
        return 'Normal'


# ================================================================
# ==================== SAISIE POINTAGE ====================
# ================================================================
@pointage_bp.route('/pointages/nouveau', methods=['GET', 'POST'])
@_auth_required
def pointage_nouveau():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/pointages')

    type_pointage = request.args.get('type') or 'entree'
    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        employe_id = request.form.get('employe_id')
        date_pointage = request.form.get('date_pointage') or datetime.now().date().isoformat()
        heure_entree = request.form.get('heure_entree') or None
        heure_sortie = request.form.get('heure_sortie') or None
        mode = request.form.get('mode') or 'Manuel'
        notes = (request.form.get('notes') or '').strip()

        if not employe_id:
            flash("Employé obligatoire", "warning")
            conn.close()
            return redirect('/pointages/nouveau')

        # Calculs auto
        duree_min = _calc_duree(heure_entree, heure_sortie)
        heures_travaillees = round(duree_min / 60, 2) if duree_min else None
        heures_sup = round(max(0, heures_travaillees - 8), 2) if heures_travaillees else 0
        statut = _calc_statut(heure_entree) if heure_entree else 'Normal'

        try:
            # Vérifier si pointage existe déjà ce jour
            c.execute("""SELECT id FROM pointages
                         WHERE employe_id=? AND date_pointage=?""",
                      (employe_id, date_pointage))
            existing = c.fetchone()

            if existing:
                # UPDATE
                c.execute("""UPDATE pointages SET
                    heure_entree=?, heure_sortie=?, duree_minutes=?,
                    heures_travaillees=?, heures_sup=?, statut=?, mode=?, notes=?
                    WHERE id=?""",
                    (heure_entree, heure_sortie, duree_min,
                     heures_travaillees, heures_sup, statut, mode, notes,
                     existing['id']))
                _log('UPDATE_POINTAGE', f"Pointage employé id={employe_id} MAJ",
                     entity='pointage', entity_id=existing['id'])
                flash(f"Pointage mis à jour ({statut})", "success")
            else:
                # INSERT
                ip = request.remote_addr or ''
                c.execute("""INSERT INTO pointages
                    (employe_id, date_pointage, heure_entree, heure_sortie,
                     mode, ip_source, duree_minutes, heures_travaillees,
                     heures_sup, statut, notes, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (employe_id, date_pointage, heure_entree, heure_sortie,
                     mode, ip, duree_min, heures_travaillees,
                     heures_sup, statut, notes, datetime.now().isoformat()))
                _log('CREATE_POINTAGE',
                     f"Pointage employé id={employe_id} le {date_pointage} ({statut})",
                     entity='pointage', entity_id=c.lastrowid)
                flash(f"Pointage enregistré ({statut})", "success")

            conn.commit()

            # Créer alerte si retard
            if statut == 'Retard':
                c.execute("""INSERT INTO alertes
                    (type_alerte, gravite, titre, message, employe_id, statut, created_at)
                    VALUES ('Retard', 'Info', 'Retard détecté',
                            ?, ?, 'Active', ?)""",
                    (f"Retard le {date_pointage} à {heure_entree}", employe_id,
                     datetime.now().isoformat()))
                conn.commit()

            conn.close()
            return redirect('/pointages')

        except Exception as e:
            import traceback
            traceback.print_exc()
            flash(f"Erreur : {e}", "danger")

    # GET : formulaire
    c.execute("SELECT id, matricule, nom, prenom FROM employes WHERE actif=1 ORDER BY nom")
    employes = c.fetchall()

    today = datetime.now()
    heure_now = today.strftime('%H:%M')

    # Heures pré-remplies selon type
    if type_pointage == 'entree':
        prefill_entree = heure_now
        prefill_sortie = ''
    elif type_pointage == 'sortie':
        prefill_entree = ''
        prefill_sortie = heure_now
    else:
        prefill_entree = ''
        prefill_sortie = ''

    conn.close()

    opt_e = '<option value="">— Choisir employé —</option>'
    for e in employes:
        opt_e += f'<option value="{e["id"]}">{e["prenom"]} {e["nom"]} ({e["matricule"]})</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-plus-circle"></i> Saisir un pointage</h2>
        <div class="page-subtitle">Entrée, sortie ou pointage complet</div></div>
      <a href="/pointages" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>

    <div class="card">
      <form method="POST" id="pointage-form">
        <div class="form-grid">
          <div class="form-group form-full">
            <label>Employé *</label>
            <select name="employe_id" required autofocus>{opt_e}</select>
          </div>

          <div class="form-group">
            <label>Date *</label>
            <input type="date" name="date_pointage" value="{today.date().isoformat()}" required>
          </div>

          <div class="form-group">
            <label>Mode</label>
            <select name="mode">
              <option value="Manuel">Manuel</option>
              <option value="Biométrique">Biométrique</option>
              <option value="Badge">Badge</option>
              <option value="Mobile">Mobile</option>
            </select>
          </div>

          <div class="form-group">
            <label>Heure ENTRÉE</label>
            <input type="time" name="heure_entree" id="h_entree" value="{prefill_entree}">
          </div>

          <div class="form-group">
            <label>Heure SORTIE</label>
            <input type="time" name="heure_sortie" id="h_sortie" value="{prefill_sortie}">
          </div>

          <div class="form-group form-full">
            <label>Notes</label>
            <textarea name="notes" rows="2" placeholder="Motif retard, mission, etc."></textarea>
          </div>
        </div>

        <div id="preview" style="margin:20px 0;padding:20px;background:linear-gradient(135deg,#f0fdff,#cffafe);border-radius:12px;border-left:5px solid #06b6d4;display:none">
          <div style="display:flex;gap:30px;flex-wrap:wrap;align-items:center">
            <div>
              <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Durée calculée</div>
              <div id="pv_duree" style="font-size:1.8rem;font-weight:900;color:#0e7490">0h00</div>
            </div>
            <div>
              <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Heures sup</div>
              <div id="pv_hs" style="font-size:1.4rem;font-weight:800;color:#f59e0b">0h</div>
            </div>
            <div>
              <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Statut estimé</div>
              <div id="pv_statut" style="font-size:1rem;font-weight:800">Normal</div>
            </div>
          </div>
        </div>

        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary" type="submit">
            <i class="fas fa-check"></i> Enregistrer le pointage
          </button>
          <a href="/pointages" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>

    <script>
    function updatePreview() {{
      const he = document.getElementById('h_entree').value;
      const hs = document.getElementById('h_sortie').value;
      const pv = document.getElementById('preview');

      if (!he || !hs) {{
        pv.style.display = 'none';
        return;
      }}

      const [h1, m1] = he.split(':').map(Number);
      const [h2, m2] = hs.split(':').map(Number);
      let diffMin = (h2 * 60 + m2) - (h1 * 60 + m1);
      if (diffMin < 0) diffMin += 24 * 60;
      diffMin -= 60; // pause

      const heures = diffMin / 60;
      const hs_val = Math.max(0, heures - 8);

      const h = Math.floor(diffMin / 60);
      const m = diffMin % 60;
      document.getElementById('pv_duree').textContent = h + 'h' + String(m).padStart(2, '0');
      document.getElementById('pv_hs').textContent = hs_val.toFixed(2) + 'h';

      const ref = 8 * 60 + 10; // 08h10
      const entreeMin = h1 * 60 + m1;
      const statut = entreeMin > ref ? 'Retard' : 'Normal';
      const stEl = document.getElementById('pv_statut');
      stEl.textContent = statut;
      stEl.style.color = statut === 'Retard' ? '#f59e0b' : '#10b981';

      pv.style.display = 'block';
    }}

    document.getElementById('h_entree').addEventListener('change', updatePreview);
    document.getElementById('h_sortie').addEventListener('change', updatePreview);

    // Preview initial
    updatePreview();
    </script>
    """
    return _render(content, active='pointage_new', title='Saisie pointage')


# ================================================================
# ==================== MES POINTAGES (self-service) ====================
# ================================================================
@pointage_bp.route('/mes-pointages')
@_auth_required
def mes_pointages():
    """Vue self-service pour l'employé connecté"""
    if not (current_user and current_user.employe_id):
        flash("Aucun employé lié à votre compte", "warning")
        return redirect('/')

    emp_id = current_user.employe_id
    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT * FROM pointages
                 WHERE employe_id=? AND strftime('%Y-%m', date_pointage)=?
                 ORDER BY date_pointage DESC""", (emp_id, mois))
    pointages = c.fetchall()

    c.execute("""SELECT COUNT(*) AS nb,
                        COALESCE(SUM(heures_travaillees),0) AS h,
                        COALESCE(SUM(heures_sup),0) AS hs,
                        SUM(CASE WHEN statut='Retard' THEN 1 ELSE 0 END) AS retards,
                        SUM(CASE WHEN statut='Absent' THEN 1 ELSE 0 END) AS absences
                 FROM pointages
                 WHERE employe_id=? AND strftime('%Y-%m', date_pointage)=?""", (emp_id, mois))
    stats = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-user-clock"></i> Mes pointages</h2>
        <div class="page-subtitle">Mois : {mois}</div></div>
      <form method="GET" style="display:flex;gap:10px">
        <input type="month" name="mois" value="{mois}"
               style="padding:10px 15px;border:2px solid #f1f5f9;border-radius:10px">
        <button class="btn btn-primary"><i class="fas fa-search"></i></button>
      </form>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-fingerprint"></i></div>
        <div class="stat-value">{stats['nb'] or 0}</div>
        <div class="stat-label">Pointages</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-hourglass"></i></div>
        <div class="stat-value">{stats['h'] or 0:.0f}h</div>
        <div class="stat-label">Heures</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-plus"></i></div>
        <div class="stat-value">{stats['hs'] or 0:.1f}h</div>
        <div class="stat-label">Heures sup</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-clock"></i></div>
        <div class="stat-value">{stats['retards'] or 0}</div>
        <div class="stat-label">Retards</div></div>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr><th>Date</th><th>Entrée</th><th>Sortie</th>
                   <th>Durée</th><th>H. sup</th><th>Statut</th></tr></thead>
        <tbody>"""
    for p in pointages:
        badge = 'badge-success'
        if p['statut'] == 'Retard': badge = 'badge-warning'
        elif p['statut'] == 'Absent': badge = 'badge-danger'
        content += f"""
        <tr>
          <td><strong>{p['date_pointage']}</strong></td>
          <td>{p['heure_entree'] or '-'}</td>
          <td>{p['heure_sortie'] or '-'}</td>
          <td>{_fmt_duree(p['duree_minutes'] or 0)}</td>
          <td>{p['heures_sup'] or 0:.1f}h</td>
          <td><span class="badge {badge}">{p['statut']}</span></td>
        </tr>"""
    if not pointages:
        content += '<tr><td colspan="6" class="empty"><i class="fas fa-fingerprint"></i><br>Aucun pointage ce mois</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='mes_pointages', title='Mes pointages')


# ================================================================
# ==================== RAPPORTS ====================
# ================================================================
@pointage_bp.route('/rapports')
@_auth_required
def rapports_home():
    if current_user.role not in ('admin', 'rh', 'chef'):
        flash("Accès réservé", "danger")
        return redirect('/')

    content = """
    <div class="page-header">
      <div><h2><i class="fas fa-file-invoice"></i> Rapports</h2>
        <div class="page-subtitle">Exports et analyses</div></div>
    </div>

    <div class="stats">
      <div class="stat-card">
        <div class="stat-icon"><i class="fas fa-calendar-check"></i></div>
        <div class="stat-value"><i class="fas fa-file-csv"></i></div>
        <div class="stat-label">Pointages du mois</div>
        <div style="margin-top:15px">
          <a href="/rapports/pointages-mois.csv" class="btn btn-primary btn-sm">
            <i class="fas fa-download"></i> Télécharger CSV
          </a>
        </div>
      </div>

      <div class="stat-card green">
        <div class="stat-icon"><i class="fas fa-users"></i></div>
        <div class="stat-value"><i class="fas fa-file-csv"></i></div>
        <div class="stat-label">État des salaires</div>
        <div style="margin-top:15px">
          <a href="/rapports/salaires-mois.csv" class="btn btn-success btn-sm">
            <i class="fas fa-download"></i> Télécharger CSV
          </a>
        </div>
      </div>

      <div class="stat-card gold">
        <div class="stat-icon"><i class="fas fa-clock"></i></div>
        <div class="stat-value"><i class="fas fa-file-csv"></i></div>
        <div class="stat-label">Retards du mois</div>
        <div style="margin-top:15px">
          <a href="/rapports/retards-mois.csv" class="btn btn-warning btn-sm">
            <i class="fas fa-download"></i> Télécharger CSV
          </a>
        </div>
      </div>

      <div class="stat-card purple">
        <div class="stat-icon"><i class="fas fa-plus"></i></div>
        <div class="stat-value"><i class="fas fa-file-csv"></i></div>
        <div class="stat-label">Heures sup</div>
        <div style="margin-top:15px">
          <a href="/rapports/hs-mois.csv" class="btn btn-purple btn-sm">
            <i class="fas fa-download"></i> Télécharger CSV
          </a>
        </div>
      </div>
    </div>
    """
    return _render(content, active='rapports', title='Rapports')


@pointage_bp.route('/rapports/pointages-mois.csv')
@_auth_required
def rapport_pointages_csv():
    if current_user.role not in ('admin', 'rh', 'chef'):
        return redirect('/')

    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT p.date_pointage, e.matricule, e.nom, e.prenom,
                        d.nom AS departement,
                        p.heure_entree, p.heure_sortie,
                        p.duree_minutes, p.heures_travaillees, p.heures_sup, p.statut
                 FROM pointages p
                 LEFT JOIN employes e ON p.employe_id = e.id
                 LEFT JOIN departements d ON e.departement_id = d.id
                 WHERE strftime('%Y-%m', p.date_pointage)=?
                 ORDER BY p.date_pointage, e.nom""", (mois,))
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(['Date', 'Matricule', 'Nom', 'Prénom', 'Département',
                'Entrée', 'Sortie', 'Durée (min)', 'Heures trav.', 'Heures sup', 'Statut'])
    for r in rows:
        w.writerow([r['date_pointage'], r['matricule'], r['nom'], r['prenom'],
                    r['departement'], r['heure_entree'] or '', r['heure_sortie'] or '',
                    r['duree_minutes'] or 0, r['heures_travaillees'] or 0,
                    r['heures_sup'] or 0, r['statut']])

    _log('RAPPORT_POINTAGES', f"Export pointages mois {mois} ({len(rows)} lignes)")
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=pointages_{mois}.csv'}
    )


@pointage_bp.route('/rapports/retards-mois.csv')
@_auth_required
def rapport_retards_csv():
    if current_user.role not in ('admin', 'rh', 'chef'):
        return redirect('/')
    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT p.date_pointage, e.matricule, e.nom, e.prenom,
                        p.heure_entree, p.notes
                 FROM pointages p
                 LEFT JOIN employes e ON p.employe_id = e.id
                 WHERE strftime('%Y-%m', p.date_pointage)=? AND p.statut='Retard'
                 ORDER BY p.date_pointage""", (mois,))
    rows = c.fetchall()
    conn.close()
    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(['Date', 'Matricule', 'Nom', 'Prénom', 'Heure arrivée', 'Notes'])
    for r in rows:
        w.writerow([r['date_pointage'], r['matricule'], r['nom'], r['prenom'],
                    r['heure_entree'], r['notes'] or ''])
    _log('RAPPORT_RETARDS', f"Export retards mois {mois}")
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=retards_{mois}.csv'}
    )


@pointage_bp.route('/rapports/hs-mois.csv')
@_auth_required
def rapport_hs_csv():
    if current_user.role not in ('admin', 'rh', 'chef'):
        return redirect('/')
    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT hs.date_hs, e.matricule, e.nom, e.prenom,
                        hs.nb_heures, hs.taux_majoration, hs.motif, hs.statut
                 FROM heures_sup hs
                 LEFT JOIN employes e ON hs.employe_id = e.id
                 WHERE strftime('%Y-%m', hs.date_hs)=?
                 ORDER BY hs.date_hs""", (mois,))
    rows = c.fetchall()
    conn.close()
    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(['Date', 'Matricule', 'Nom', 'Prénom', 'Heures', 'Majoration', 'Motif', 'Statut'])
    for r in rows:
        w.writerow([r['date_hs'], r['matricule'], r['nom'], r['prenom'],
                    r['nb_heures'], r['taux_majoration'], r['motif'] or '', r['statut']])
    _log('RAPPORT_HS', f"Export heures sup mois {mois}")
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=heures_sup_{mois}.csv'}
    )


@pointage_bp.route('/rapports/salaires-mois.csv')
@_auth_required
def rapport_salaires_csv():
    if current_user.role not in ('admin', 'rh'):
        return redirect('/')
    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')
    conn = _db()
    c = conn.cursor()

    # Récupérer tous les employés actifs + leurs heures du mois
    c.execute("""SELECT e.id, e.matricule, e.nom, e.prenom, e.salaire_base,
                        d.nom AS departement,
                        COALESCE(SUM(p.heures_travaillees), 0) AS heures,
                        COALESCE(SUM(p.heures_sup), 0) AS hs
                 FROM employes e
                 LEFT JOIN pointages p ON p.employe_id = e.id
                    AND strftime('%Y-%m', p.date_pointage)=?
                 LEFT JOIN departements d ON e.departement_id = d.id
                 WHERE e.actif=1
                 GROUP BY e.id
                 ORDER BY e.nom""", (mois,))
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(['Matricule', 'Nom', 'Prénom', 'Département',
                'Salaire base', 'Heures trav.', 'Heures sup', 'Salaire estimé'])
    for r in rows:
        salaire = r['salaire_base'] or 0
        hs_val = r['hs'] or 0
        # Heures sup majorées à 1.25
        taux_horaire = salaire / 173.33 if salaire else 0
        bonus_hs = taux_horaire * 1.25 * hs_val
        total = salaire + bonus_hs
        w.writerow([r['matricule'], r['nom'], r['prenom'], r['departement'] or '',
                    salaire, round(r['heures'], 2), round(hs_val, 2),
                    round(total, 2)])
    _log('RAPPORT_SALAIRES', f"Export salaires mois {mois}")
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=salaires_{mois}.csv'}
    )


# ================================================================
# ==================== API ====================
# ================================================================
@pointage_bp.route('/api/pointage-stats')
@_auth_required
def api_pointage_stats():
    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT COUNT(*) AS nb,
                        COALESCE(SUM(heures_travaillees),0) AS h,
                        COALESCE(SUM(heures_sup),0) AS hs,
                        SUM(CASE WHEN statut='Retard' THEN 1 ELSE 0 END) AS retards
                 FROM pointages
                 WHERE strftime('%Y-%m', date_pointage)=?""", (mois,))
    r = c.fetchone()
    conn.close()
    return jsonify(mois=mois, nb_pointages=r['nb'], heures_totales=r['h'],
                   heures_sup=r['hs'], retards=r['retards'])


@pointage_bp.route('/api/employe/<int:eid>/pointages')
@_auth_required
def api_employe_pointages(eid):
    mois = request.args.get('mois') or datetime.now().strftime('%Y-%m')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT date_pointage, heure_entree, heure_sortie,
                        heures_travaillees, heures_sup, statut
                 FROM pointages
                 WHERE employe_id=? AND strftime('%Y-%m', date_pointage)=?
                 ORDER BY date_pointage DESC""", (eid, mois))
    rows = c.fetchall()
    conn.close()
    return jsonify(pointages=[dict(r) for r in rows])
