"""
Module Logique Métier RH
Congés, Pointages, Paie (IPRES/CSS/IRPP), Formations, Évaluations,
Recrutement, Absences, Notes de frais, Prêts/Avances
"""
from flask import render_template_string, request, redirect, flash, jsonify
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "/app/data/rh.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def gen_numero(prefix, table):
    conn = get_db()
    c = conn.cursor()
    year = datetime.now().year
    c.execute(f"SELECT COUNT(*) FROM {table}")
    n = c.fetchone()[0] + 1
    conn.close()
    return f"{prefix}-{year}-{n:04d}"


def calculer_irpp(salaire_imposable):
    """Calcul IRPP Sénégal (barème progressif)"""
    # Barème IRPP Sénégal simplifié (à ajuster selon CGI)
    tranches = [
        (0, 50000, 0),          # Exonéré
        (50001, 130000, 20),     # 20%
        (130001, 230000, 25),    # 25%
        (230001, 320000, 30),    # 30%
        (320001, 520000, 35),    # 35%
        (520001, 750000, 40),    # 40%
        (750001, float('inf'), 45),  # 45%
    ]

    irpp = 0
    for min_t, max_t, taux in tranches:
        if salaire_imposable > min_t:
            tranche_imposable = min(salaire_imposable, max_t) - min_t
            irpp += tranche_imposable * taux / 100
    return irpp


def calculer_bulletin(employe, mois, annee, primes_extra=None, heures_sup=0):
    """
    Calcule un bulletin de paie complet avec IPRES, CSS, IRPP, CFCE
    Conforme Code du Travail Sénégal
    """
    primes_extra = primes_extra or {}

    # ============= GAINS =============
    salaire_base = employe['salaire_base'] or 0
    prime_transport = employe['prime_transport'] or 0
    prime_logement = employe['prime_logement'] or 0
    prime_autre = employe['prime_autre'] or 0

    # Prime d'ancienneté (2% par an, max 30%)
    anciennete_ans = 0
    try:
        if employe['date_embauche']:
            emb = datetime.fromisoformat(employe['date_embauche'])
            anciennete_ans = (datetime.now() - emb).days // 365
    except Exception:
        pass
    prime_anciennete = salaire_base * min(anciennete_ans * 2, 30) / 100

    # Heures supplémentaires (majoration 60%)
    taux_horaire = salaire_base / 173.33  # 40h/semaine
    montant_hsup = heures_sup * taux_horaire * 1.6

    brut_imposable = salaire_base + prime_logement + prime_anciennete + montant_hsup
    brut_total = brut_imposable + prime_transport + prime_autre

    # ============= COTISATIONS SALARIALES =============
    # IPRES salariale : 5.6% plafonné à 432 000 FCFA
    base_ipres = min(brut_imposable, 432000)
    ipres_sal = base_ipres * 5.6 / 100

    # CSS salariale : 3% plafonné à 63 000 FCFA
    base_css = min(brut_imposable, 63000)
    css_sal = base_css * 3.0 / 100

    # CFCE salariale : 3% sur brut imposable
    cfce_sal = brut_imposable * 3.0 / 100

    # ============= IRPP =============
    salaire_imposable = brut_imposable - ipres_sal - css_sal - cfce_sal
    irpp = calculer_irpp(salaire_imposable)

    # ============= TOTAL RETENUES =============
    total_retenues = ipres_sal + css_sal + cfce_sal + irpp

    # ============= NET À PAYER =============
    salaire_net = brut_total - total_retenues

    # ============= COTISATIONS PATRONALES =============
    ipres_pat = min(brut_imposable, 432000) * 8.4 / 100
    css_pat = min(brut_imposable, 63000) * 9.0 / 100
    cfce_pat = brut_imposable * 3.0 / 100
    fnp_pat = brut_imposable * 2.0 / 100

    cout_employeur = brut_total + ipres_pat + css_pat + cfce_pat + fnp_pat

    return {
        'salaire_base': salaire_base,
        'prime_transport': prime_transport,
        'prime_logement': prime_logement,
        'prime_anciennete': prime_anciennete,
        'prime_autre': prime_autre,
        'heures_sup': heures_sup,
        'montant_hsup': montant_hsup,
        'salaire_brut': brut_total,
        'ipres_sal': ipres_sal,
        'css_sal': css_sal,
        'cfce_sal': cfce_sal,
        'irpp': irpp,
        'total_retenues': total_retenues,
        'salaire_net': salaire_net,
        'ipres_pat': ipres_pat,
        'css_pat': css_pat,
        'cfce_pat': cfce_pat,
        'fnp_pat': fnp_pat,
        'cout_employeur': cout_employeur,
        'base_ipres': base_ipres,
        'base_css': base_css,
        'salaire_imposable': salaire_imposable,
    }


try:
    from auth import (role_required, admin_required, drh_required,
                      rh_required, manager_required, staff_required, log_action)
    from flask_login import current_user
except ImportError:
    def role_required(*r):
        def d(f): return f
        return d
    def admin_required(f): return f
    def drh_required(f): return f
    def rh_required(f): return f
    def manager_required(f): return f
    def staff_required(f): return f
    def log_action(*a, **k): pass
    current_user = None


def register_rh_routes(app, render_page):
    """Enregistre toutes les routes logique métier RH"""

    # ==================== CONGÉS ====================
    @app.route('/conges')
    @staff_required
    def conges_liste():
        conn = get_db()
        c = conn.cursor()

        statut_filter = request.args.get('statut', '')
        employe_filter = request.args.get('employe', '')

        query = """SELECT cg.*, e.nom, e.prenom, e.matricule,
                          tc.nom as type_nom, tc.couleur
                   FROM conges cg
                   JOIN employes e ON cg.employe_id = e.id
                   JOIN types_conges tc ON cg.type_conge_id = tc.id
                   WHERE 1=1"""
        params = []

        if statut_filter:
            query += " AND cg.statut = ?"
            params.append(statut_filter)
        if employe_filter:
            query += " AND cg.employe_id = ?"
            params.append(int(employe_filter))

        query += " ORDER BY cg.created_at DESC LIMIT 200"
        c.execute(query, params)
        rows = c.fetchall()

        # Stats
        c.execute("SELECT COUNT(*) FROM conges WHERE statut='En attente'")
        en_attente = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM conges WHERE statut='Approuvé' AND date_debut >= date('now')")
        a_venir = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM conges WHERE statut='Approuvé' AND date_debut <= date('now') AND date_fin >= date('now')")
        en_cours = c.fetchone()[0]

        conn.close()

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-calendar-check"></i> Congés & Absences</h2>
            <div class="page-subtitle">Gestion des demandes de congés</div>
          </div>
          <a href="/conges/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle demande</a>
        </div>

        <div class="stats">
          <div class="stat-card amber">
            <i class="fas fa-hourglass-half stat-icon"></i>
            <div class="stat-value">{en_attente}</div>
            <div class="stat-label">En attente</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-calendar-plus stat-icon"></i>
            <div class="stat-value">{a_venir}</div>
            <div class="stat-label">À venir</div>
          </div>
          <div class="stat-card">
            <i class="fas fa-user-clock stat-icon"></i>
            <div class="stat-value">{en_cours}</div>
            <div class="stat-label">En cours</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Demandes</h3>
            <form method="GET" style="display:flex;gap:8px">
              <select name="statut" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous statuts</option>
                <option value="En attente" {"selected" if statut_filter == "En attente" else ""}>En attente</option>
                <option value="Approuvé" {"selected" if statut_filter == "Approuvé" else ""}>Approuvé</option>
                <option value="Refusé" {"selected" if statut_filter == "Refusé" else ""}>Refusé</option>
                <option value="En cours" {"selected" if statut_filter == "En cours" else ""}>En cours</option>
              </select>
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>N°</th><th>Employé</th><th>Type</th><th>Période</th>
                  <th>Jours</th><th>Statut</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
        """
        for cg in rows:
            badge = 'badge-warning'
            if cg['statut'] == 'Approuvé': badge = 'badge-success'
            elif cg['statut'] == 'Refusé': badge = 'badge-danger'
            elif cg['statut'] == 'En cours': badge = 'badge-info'

            content += f"""
            <tr>
              <td><strong>{cg['numero']}</strong></td>
              <td>{cg['nom']} {cg['prenom']}<br><small style="color:#94a3b8">{cg['matricule']}</small></td>
              <td><span class="badge" style="background:{cg['couleur']}20;color:{cg['couleur']}">{cg['type_nom']}</span></td>
              <td>{cg['date_debut']} → {cg['date_fin']}</td>
              <td><strong>{cg['nb_jours']}j</strong></td>
              <td><span class="badge {badge}">{cg['statut']}</span></td>
              <td>
                <a href="/conges/{cg['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="7" class="empty"><i class="fas fa-calendar-check"></i><br>Aucune demande</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='conges', page_title='Congés')

    @app.route('/conges/nouveau', methods=['GET', 'POST'])
    @staff_required
    def conge_nouveau():
        conn = get_db()
        c = conn.cursor()
        employe_id_pre = request.args.get('employe_id', '')

        if request.method == 'POST':
            try:
                numero = gen_numero('CG', 'conges')
                date_debut = request.form['date_debut']
                date_fin = request.form['date_fin']

                # Calcul jours
                try:
                    dd = datetime.fromisoformat(date_debut)
                    df = datetime.fromisoformat(date_fin)
                    nb_jours = (df - dd).days + 1
                except Exception:
                    nb_jours = float(request.form.get('nb_jours') or 0)

                c.execute("""INSERT INTO conges
                    (numero, employe_id, type_conge_id, date_debut, date_fin, nb_jours,
                     motif, statut, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'En attente', ?)""",
                    (numero, int(request.form['employe_id']),
                     int(request.form['type_conge_id']),
                     date_debut, date_fin, nb_jours,
                     request.form.get('motif', ''),
                     datetime.now().isoformat()))
                conn.commit()
                conn.close()

                if current_user:
                    log_action(current_user.id, 'CREATE_CONGE', numero)

                flash(f"✅ Demande de congé {numero} créée", "success")
                return redirect('/conges')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom, prenom, matricule FROM employes WHERE actif=1 ORDER BY nom")
        employes = c.fetchall()
        c.execute("SELECT * FROM types_conges WHERE actif=1 ORDER BY nom")
        types = c.fetchall()
        conn.close()

        emp_opts = "".join(f'<option value="{e["id"]}" {"selected" if str(e["id"])==employe_id_pre else ""}>{e["nom"]} {e["prenom"]} ({e["matricule"]})</option>' for e in employes)
        types_opts = "".join(f'<option value="{t["id"]}">{t["nom"]} ({t["jours_par_an"]}j/an)</option>' for t in types)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-calendar-plus"></i> Nouvelle Demande de Congé</h2>
          <a href="/conges" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Employé *</label>
                <select name="employe_id" required>
                  <option value="">-- Sélectionner --</option>
                  {emp_opts}
                </select>
              </div>
              <div class="form-group"><label>Type de congé *</label>
                <select name="type_conge_id" required>
                  <option value="">-- Sélectionner --</option>
                  {types_opts}
                </select>
              </div>
              <div class="form-group"><label>Date début *</label><input type="date" name="date_debut" required></div>
              <div class="form-group"><label>Date fin *</label><input type="date" name="date_fin" required></div>
              <div class="form-group form-full"><label>Motif</label><textarea name="motif" rows="2"></textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Soumettre la demande</button>
              <a href="/conges" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='conges', page_title='Nouvelle demande')

    @app.route('/conges/<int:cid>')
    @staff_required
    def conge_detail(cid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT cg.*, e.nom, e.prenom, e.matricule, e.telephone,
                            tc.nom as type_nom, tc.couleur,
                            v.nom as valideur_nom, v.prenom as valideur_prenom
                     FROM conges cg
                     JOIN employes e ON cg.employe_id = e.id
                     JOIN types_conges tc ON cg.type_conge_id = tc.id
                     LEFT JOIN employes v ON cg.valideur_id = v.id
                     WHERE cg.id=?""", (cid,))
        cg = c.fetchone()
        if not cg:
            conn.close()
            flash("Demande introuvable", "danger")
            return redirect('/conges')
        conn.close()

        badge = 'badge-warning'
        if cg['statut'] == 'Approuvé': badge = 'badge-success'
        elif cg['statut'] == 'Refusé': badge = 'badge-danger'

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-calendar-check"></i> Congé {cg['numero']}</h2>
          <a href="/conges" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
          <div class="form-grid">
            <div><strong>Employé :</strong> {cg['nom']} {cg['prenom']} ({cg['matricule']})</div>
            <div><strong>Téléphone :</strong> {cg['telephone'] or '-'}</div>
            <div><strong>Type :</strong> <span class="badge" style="background:{cg['couleur']}20;color:{cg['couleur']}">{cg['type_nom']}</span></div>
            <div><strong>Statut :</strong> <span class="badge {badge}">{cg['statut']}</span></div>
            <div><strong>Période :</strong> {cg['date_debut']} → {cg['date_fin']}</div>
            <div><strong>Nombre de jours :</strong> <strong>{cg['nb_jours']} jours</strong></div>
          </div>
          {('<p style="margin-top:15px"><strong>Motif :</strong> ' + cg['motif'] + '</p>') if cg['motif'] else ''}
          {('<p style="margin-top:10px"><strong>Validé par :</strong> ' + (cg['valideur_nom'] or '') + ' ' + (cg['valideur_prenom'] or '') + ' le ' + (cg['date_validation'][:10] if cg['date_validation'] else '')) if cg['valideur_id'] else ''}
        </div>

        {f'''
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-gavel"></i> Actions de validation</h3></div>
          <div style="display:flex;gap:10px">
            <form method="POST" action="/conges/{cid}/approuver" style="flex:1">
              <input type="text" name="commentaire" placeholder="Commentaire (optionnel)" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:8px;margin-bottom:10px">
              <button type="submit" class="btn btn-success" style="width:100%;justify-content:center">
                <i class="fas fa-check"></i> Approuver
              </button>
            </form>
            <form method="POST" action="/conges/{cid}/refuser" style="flex:1">
              <input type="text" name="commentaire" placeholder="Motif du refus" style="width:100%;padding:12px;border:2px solid #f1f5f9;border-radius:8px;margin-bottom:10px">
              <button type="submit" class="btn btn-danger" style="width:100%;justify-content:center">
                <i class="fas fa-times"></i> Refuser
              </button>
            </form>
          </div>
        </div>
        ''' if cg['statut'] == 'En attente' and current_user and current_user.role in ['admin','drh','rh','manager'] else ''}
        """
        return render_page(content, active='conges', page_title=f'Congé {cg["numero"]}')

    @app.route('/conges/<int:cid>/approuver', methods=['POST'])
    @manager_required
    def conge_approuver(cid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("""UPDATE conges SET statut='Approuvé', valideur_id=?,
                         date_validation=?, commentaire_validation=?
                         WHERE id=?""",
                      (current_user.id if current_user else None,
                       datetime.now().isoformat(),
                       request.form.get('commentaire', ''), cid))
            conn.commit()
            conn.close()
            if current_user:
                log_action(current_user.id, 'APPROVE_CONGE', f'ID {cid}')
            flash("✅ Congé approuvé", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect(f'/conges/{cid}')

    @app.route('/conges/<int:cid>/refuser', methods=['POST'])
    @manager_required
    def conge_refuser(cid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("""UPDATE conges SET statut='Refusé', valideur_id=?,
                         date_validation=?, commentaire_validation=?
                         WHERE id=?""",
                      (current_user.id if current_user else None,
                       datetime.now().isoformat(),
                       request.form.get('commentaire', ''), cid))
            conn.commit()
            conn.close()
            if current_user:
                log_action(current_user.id, 'REFUSE_CONGE', f'ID {cid}')
            flash("✅ Congé refusé", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect(f'/conges/{cid}')

    print("[RH_LOGIC] ✅ Routes congés enregistrées")

    # ==================== POINTAGES ====================
    @app.route('/pointages')
    @staff_required
    def pointages_liste():
        conn = get_db()
        c = conn.cursor()

        date_filter = request.args.get('date', datetime.now().date().isoformat())

        c.execute("""SELECT pt.*, e.nom, e.prenom, e.matricule, e.departement_id,
                            d.nom as dept_nom
                     FROM pointages pt
                     JOIN employes e ON pt.employe_id = e.id
                     LEFT JOIN departements d ON e.departement_id = d.id
                     WHERE pt.date_pointage = ?
                     ORDER BY pt.heure_arrivee DESC""", (date_filter,))
        rows = c.fetchall()

        # Stats
        c.execute("""SELECT COUNT(*) FROM pointages WHERE date_pointage = ?""", (date_filter,))
        total_pointages = c.fetchone()[0]

        c.execute("""SELECT COUNT(*) FROM pointages WHERE date_pointage = ? AND retard_minutes > 0""",
                  (date_filter,))
        retards = c.fetchone()[0]

        c.execute("""SELECT COALESCE(SUM(heures_travaillees), 0) FROM pointages WHERE date_pointage = ?""",
                  (date_filter,))
        heures_total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM employes WHERE actif=1 AND statut='Actif'")
        effectif = c.fetchone()[0]

        conn.close()
        absents = effectif - total_pointages

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-clock"></i> Pointages</h2>
            <div class="page-subtitle">Suivi de présence du {date_filter}</div>
          </div>
          <div style="display:flex;gap:10px">
            <form method="GET" style="display:flex;gap:8px">
              <input type="date" name="date" value="{date_filter}" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
            <a href="/pointages/nouveau" class="btn btn-success"><i class="fas fa-plus"></i> Pointer</a>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card green">
            <i class="fas fa-user-check stat-icon"></i>
            <div class="stat-value">{total_pointages}</div>
            <div class="stat-label">Présents</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-user-times stat-icon"></i>
            <div class="stat-value">{absents}</div>
            <div class="stat-label">Absents</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-hourglass-half stat-icon"></i>
            <div class="stat-value">{retards}</div>
            <div class="stat-label">Retards</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-business-time stat-icon"></i>
            <div class="stat-value">{heures_total:.1f}h</div>
            <div class="stat-label">Heures totales</div>
          </div>
        </div>

        <div class="card">
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Employé</th><th>Département</th><th>Arrivée</th>
                  <th>Départ</th><th>Heures</th><th>Retard</th><th>Mode</th>
                </tr>
              </thead>
              <tbody>
        """
        for p in rows:
            retard_badge = '<span class="badge badge-success">À l\'heure</span>'
            if p['retard_minutes'] > 0:
                retard_badge = f'<span class="badge badge-warning">{p["retard_minutes"]}min</span>'

            content += f"""
            <tr>
              <td><strong>{p['nom']} {p['prenom']}</strong><br><small style="color:#94a3b8">{p['matricule']}</small></td>
              <td>{p['dept_nom'] or '-'}</td>
              <td>{p['heure_arrivee'] or '-'}</td>
              <td>{p['heure_depart'] or '-'}</td>
              <td><strong>{p['heures_travaillees']:.2f}h</strong></td>
              <td>{retard_badge}</td>
              <td><span class="badge badge-info">{p['mode_pointage'] or '-'}</span></td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="7" class="empty"><i class="fas fa-clock"></i><br>Aucun pointage</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='pointages', page_title='Pointages')

    @app.route('/pointages/nouveau', methods=['GET', 'POST'])
    @staff_required
    def pointage_nouveau():
        conn = get_db()
        c = conn.cursor()
        employe_id_pre = request.args.get('employe_id', '')

        if request.method == 'POST':
            try:
                employe_id = int(request.form['employe_id'])
                date_pointage = request.form.get('date_pointage') or datetime.now().date().isoformat()
                heure_arrivee = request.form.get('heure_arrivee') or None
                heure_depart = request.form.get('heure_depart') or None

                # Calcul heures
                heures_travaillees = 0
                retard = 0
                if heure_arrivee and heure_depart:
                    try:
                        h1 = datetime.strptime(heure_arrivee, '%H:%M')
                        h2 = datetime.strptime(heure_depart, '%H:%M')
                        heures_travaillees = (h2 - h1).seconds / 3600
                        # Retard après 8h30
                        h_ref = datetime.strptime('08:30', '%H:%M')
                        if h1 > h_ref:
                            retard = int((h1 - h_ref).seconds / 60)
                    except Exception:
                        pass

                c.execute("""INSERT INTO pointages
                    (employe_id, date_pointage, heure_arrivee, heure_depart,
                     heures_travaillees, retard_minutes, mode_pointage, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (employe_id, date_pointage, heure_arrivee, heure_depart,
                     heures_travaillees, retard,
                     request.form.get('mode_pointage', 'Manuel'),
                     request.form.get('notes', ''),
                     datetime.now().isoformat()))
                conn.commit()
                conn.close()
                flash("✅ Pointage enregistré", "success")
                return redirect('/pointages')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom, prenom, matricule FROM employes WHERE actif=1 ORDER BY nom")
        employes = c.fetchall()
        conn.close()
        emp_opts = "".join(f'<option value="{e["id"]}" {"selected" if str(e["id"])==employe_id_pre else ""}>{e["nom"]} {e["prenom"]} ({e["matricule"]})</option>' for e in employes)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-clock"></i> Nouveau Pointage</h2>
          <a href="/pointages" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Employé *</label>
                <select name="employe_id" required>
                  <option value="">-- Sélectionner --</option>
                  {emp_opts}
                </select>
              </div>
              <div class="form-group"><label>Date *</label><input type="date" name="date_pointage" value="{datetime.now().date().isoformat()}" required></div>
              <div class="form-group"><label>Heure d'arrivée</label><input type="time" name="heure_arrivee" value="08:30"></div>
              <div class="form-group"><label>Heure de départ</label><input type="time" name="heure_depart" value="17:30"></div>
              <div class="form-group"><label>Mode de pointage</label>
                <select name="mode_pointage">
                  <option value="Manuel">Manuel</option>
                  <option value="QR">QR Code</option>
                  <option value="Badge">Badge</option>
                  <option value="Biométrie">Biométrie</option>
                  <option value="Mobile">Mobile</option>
                </select>
              </div>
              <div class="form-group form-full"><label>Notes</label><textarea name="notes" rows="2"></textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/pointages" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='pointages', page_title='Nouveau pointage')

    print("[RH_LOGIC] ✅ Routes pointages enregistrées")

    # ==================== PAIE ====================
    @app.route('/paie')
    @rh_required
    def paie_liste():
        conn = get_db()
        c = conn.cursor()

        mois_filter = request.args.get('mois', '')
        annee_filter = request.args.get('annee', str(datetime.now().year))
        statut_filter = request.args.get('statut', '')

        query = """SELECT b.*, e.nom, e.prenom, e.matricule, e.departement_id,
                          d.nom as dept_nom
                   FROM bulletins_paie b
                   JOIN employes e ON b.employe_id = e.id
                   LEFT JOIN departements d ON e.departement_id = d.id
                   WHERE b.annee = ?"""
        params = [int(annee_filter)]

        if mois_filter:
            query += " AND b.mois = ?"
            params.append(int(mois_filter))
        if statut_filter:
            query += " AND b.statut = ?"
            params.append(statut_filter)

        query += " ORDER BY b.annee DESC, b.mois DESC, e.nom"
        c.execute(query, params)
        rows = c.fetchall()

        # Stats
        c.execute("""SELECT COALESCE(SUM(salaire_brut), 0), COALESCE(SUM(salaire_net), 0),
                     COALESCE(SUM(irpp), 0), COALESCE(SUM(ipres_sal) + SUM(css_sal) + SUM(cfce_sal), 0)
                     FROM bulletins_paie WHERE annee = ?""", (int(annee_filter),))
        stats = c.fetchone()

        conn.close()

        mois_opts = "".join(f'<option value="{m}" {"selected" if mois_filter == str(m) else ""}>{m:02d}</option>' for m in range(1, 13))
        annees_opts = "".join(f'<option value="{y}" {"selected" if annee_filter == str(y) else ""}>{y}</option>' for y in range(2024, datetime.now().year + 2))

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-money-bill-wave"></i> Paie</h2>
            <div class="page-subtitle">Bulletins de paie - {annee_filter}</div>
          </div>
          <a href="/paie/generer" class="btn btn-success"><i class="fas fa-cogs"></i> Générer la paie</a>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-money-bill stat-icon"></i>
            <div class="stat-value">{stats[0]:,.0f}</div>
            <div class="stat-label">Masse salariale brute</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-hand-holding-usd stat-icon"></i>
            <div class="stat-value">{stats[1]:,.0f}</div>
            <div class="stat-label">Net à payer</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-percentage stat-icon"></i>
            <div class="stat-value">{stats[2]:,.0f}</div>
            <div class="stat-label">IRPP collecté</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-shield-halved stat-icon"></i>
            <div class="stat-value">{stats[3]:,.0f}</div>
            <div class="stat-label">Cotisations sociales</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Bulletins</h3>
            <form method="GET" style="display:flex;gap:8px">
              <select name="mois" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous mois</option>
                {mois_opts}
              </select>
              <select name="annee" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                {annees_opts}
              </select>
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>N°</th><th>Employé</th><th>Département</th>
                  <th>Période</th><th>Brut</th><th>Retenues</th><th>Net</th>
                  <th>Statut</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
        """
        for b in rows:
            badge = 'badge-success' if b['statut'] == 'Payé' else ('badge-warning' if b['statut'] == 'Validé' else 'badge-info')
            content += f"""
            <tr>
              <td><strong>{b['numero']}</strong></td>
              <td>{b['nom']} {b['prenom']}<br><small style="color:#94a3b8">{b['matricule']}</small></td>
              <td>{b['dept_nom'] or '-'}</td>
              <td><strong>{b['mois']:02d}/{b['annee']}</strong></td>
              <td>{b['salaire_brut']:,.0f}</td>
              <td>{b['total_retenues']:,.0f}</td>
              <td><strong style="color:#059669">{b['salaire_net']:,.0f}</strong></td>
              <td><span class="badge {badge}">{b['statut']}</span></td>
              <td>
                <a href="/paie/bulletin/{b['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="9" class="empty"><i class="fas fa-file-invoice-dollar"></i><br>Aucun bulletin</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='paie', page_title='Paie')

    @app.route('/paie/generer', methods=['GET', 'POST'])
    @drh_required
    def paie_generer():
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                mois = int(request.form['mois'])
                annee = int(request.form['annee'])

                # Vérifier si déjà généré
                c.execute("""SELECT COUNT(*) FROM bulletins_paie WHERE mois=? AND annee=?""",
                          (mois, annee))
                if c.fetchone()[0] > 0 and not request.form.get('forcer'):
                    conn.close()
                    flash(f"⚠️ Bulletins {mois:02d}/{annee} déjà générés. Cochez 'Forcer' pour régénérer.", "warning")
                    return redirect('/paie/generer')

                # Récupérer tous les employés actifs
                c.execute("""SELECT * FROM employes WHERE actif=1 AND statut='Actif'""")
                employes = c.fetchall()

                count = 0
                for emp in employes:
                    # Calcul du bulletin
                    bulletin = calculer_bulletin(emp, mois, annee)

                    numero = f"BP-{annee}-{mois:02d}-{emp['matricule']}"

                    c.execute("""INSERT INTO bulletins_paie
                        (numero, employe_id, mois, annee, date_emission,
                         salaire_brut, primes_total, heures_sup_total,
                         cotisations_salariales, cotisations_patronales,
                         irpp, cfce, total_retenues, salaire_net, cout_employeur,
                         jours_travailles, statut, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Brouillon', ?)""",
                        (numero, emp['id'], mois, annee,
                         datetime.now().isoformat(),
                         bulletin['salaire_brut'],
                         bulletin['prime_transport'] + bulletin['prime_logement'] + bulletin['prime_anciennete'] + bulletin['prime_autre'],
                         bulletin['heures_sup'],
                         bulletin['ipres_sal'] + bulletin['css_sal'] + bulletin['cfse_sal'] if 'cfse_sal' in bulletin else bulletin['ipres_sal'] + bulletin['css_sal'] + bulletin['cfce_sal'],
                         bulletin['ipres_pat'] + bulletin['css_pat'] + bulletin['cfce_pat'] + bulletin['fnp_pat'],
                         bulletin['irpp'],
                         bulletin['cfce_sal'],
                         bulletin['total_retenues'],
                         bulletin['salaire_net'],
                         bulletin['cout_employeur'],
                         22, datetime.now().isoformat()))
                    count += 1

                conn.commit()
                conn.close()

                if current_user:
                    log_action(current_user.id, 'GENERATE_PAIE', f'{mois:02d}/{annee} - {count} bulletins')

                flash(f"✅ {count} bulletins générés pour {mois:02d}/{annee}", "success")
                return redirect('/paie')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        conn.close()
        mois_opts = "".join(f'<option value="{m}" {"selected" if m == datetime.now().month else ""}>{m:02d}</option>' for m in range(1, 13))
        annees_opts = "".join(f'<option value="{y}" {"selected" if y == datetime.now().year else ""}>{y}</option>' for y in range(2024, datetime.now().year + 2))

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-cogs"></i> Générer la paie</h2>
          <a href="/paie" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <div style="padding:20px;background:#fef3c7;border-radius:12px;border-left:4px solid #f59e0b;margin-bottom:20px">
            <strong style="color:#92400e"><i class="fas fa-exclamation-triangle"></i> Information</strong>
            <p style="color:#92400e;margin-top:8px;font-size:0.9rem">
              La génération calcule automatiquement :
              <br>• Salaire de base + primes + ancienneté
              <br>• IPRES (5.6% salarié / 8.4% patronal)
              <br>• CSS (3% salarié / 9% patronal)
              <br>• IRPP barème progressif
              <br>• CFCE (3%) et FNP (2%)
            </p>
          </div>

          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Mois *</label><select name="mois" required>{mois_opts}</select></div>
              <div class="form-group"><label>Année *</label><select name="annee" required>{annees_opts}</select></div>
              <div class="form-group form-full" style="display:flex;align-items:center;gap:8px">
                <input type="checkbox" name="forcer" style="width:auto">
                <label style="margin:0">Forcer la régénération (écrase les bulletins existants)</label>
              </div>
            </div>
            <div style="margin-top:25px">
              <button type="submit" class="btn btn-success" style="padding:15px 30px;font-size:1rem">
                <i class="fas fa-play"></i> Lancer la génération
              </button>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='paie', page_title='Générer la paie')

    @app.route('/paie/bulletin/<int:bid>')
    @rh_required
    def paie_bulletin(bid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT b.*, e.nom, e.prenom, e.matricule, e.cni,
                            e.numero_css, e.numero_ipres, e.salaire_base,
                            e.prime_transport, e.prime_logement, e.prime_autre,
                            e.banque, e.rib, e.date_embauche, e.type_contrat,
                            d.nom as dept_nom, p.intitule as poste_nom
                     FROM bulletins_paie b
                     JOIN employes e ON b.employe_id = e.id
                     LEFT JOIN departements d ON e.departement_id = d.id
                     LEFT JOIN postes p ON e.poste_id = p.id
                     WHERE b.id=?""", (bid,))
        b = c.fetchone()
        if not b:
            conn.close()
            flash("Bulletin introuvable", "danger")
            return redirect('/paie')
        conn.close()

        # Recalculer pour afficher le détail
        employe_dict = dict(b)
        bulletin = calculer_bulletin(employe_dict, b['mois'], b['annee'])

        mois_noms = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                     'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']

        content = f"""
        <style>
        .bulletin-paie {{ background:white; max-width:900px; margin:20px auto; padding:35px; box-shadow:0 4px 20px rgba(0,0,0,0.08); border-radius:8px; }}
        .bulletin-paie .entete {{ text-align:center; padding-bottom:20px; border-bottom:3px solid #7c3aed; margin-bottom:25px; }}
        .bulletin-paie h1 {{ color:#7c3aed; font-size:1.8rem; }}
        .bulletin-paie .sub {{ color:#64748b; font-size:0.85rem; }}
        .bulletin-paie table {{ width:100%; border-collapse:collapse; margin:15px 0; }}
        .bulletin-paie th, .bulletin-paie td {{ padding:8px 10px; text-align:left; font-size:0.85rem; border-bottom:1px solid #f3e8ff; }}
        .bulletin-paie th {{ background:#f3e8ff; color:#7c3aed; font-weight:800; font-size:0.75rem; text-transform:uppercase; }}
        .bulletin-paie .montant {{ text-align:right; font-weight:700; }}
        .bulletin-paie .total {{ background:#f3e8ff; font-weight:900; color:#4c1d95; font-size:1rem; }}
        .bulletin-paie .net {{ background:#d1fae5; font-weight:900; color:#065f46; font-size:1.15rem; padding:15px; }}
        @media print {{
          body * {{ visibility: hidden; }}
          .bulletin-paie, .bulletin-paie * {{ visibility: visible; }}
          .bulletin-paie {{ position: absolute; left: 0; top: 0; box-shadow: none; }}
          .no-print {{ display: none !important; }}
        }}
        </style>

        <div class="no-print" style="text-align:center;margin-bottom:15px">
          <button onclick="window.print()" class="btn btn-primary"><i class="fas fa-print"></i> Imprimer</button>
          <a href="/paie" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>

        <div class="bulletin-paie">
          <div class="entete">
            <h1>OMEGA INFORMATIQUE</h1>
            <div class="sub">Dakar, Sénégal · NIF : SN-123456789</div>
            <div class="sub" style="margin-top:10px;font-size:1rem;font-weight:800;color:#4c1d95">
              BULLETIN DE PAIE — {mois_noms[b['mois']]} {b['annee']}
            </div>
            <div class="sub">N° {b['numero']}</div>
          </div>

          <table>
            <tr>
              <th colspan="2">Salarié</th>
              <th colspan="2">Contrat</th>
            </tr>
            <tr>
              <td><strong>Nom :</strong> {b['nom']} {b['prenom']}</td>
              <td><strong>Matricule :</strong> {b['matricule']}</td>
              <td><strong>Type :</strong> {b['type_contrat']}</td>
              <td><strong>Embauche :</strong> {b['date_embauche']}</td>
            </tr>
            <tr>
              <td><strong>CNI :</strong> {b['cni'] or '-'}</td>
              <td><strong>CSS :</strong> {b['numero_css'] or '-'}</td>
              <td><strong>IPRES :</strong> {b['numero_ipres'] or '-'}</td>
              <td><strong>Poste :</strong> {b['poste_nom'] or '-'}</td>
            </tr>
          </table>

          <table>
            <thead>
              <tr><th>Désignation</th><th style="text-align:right">Base</th><th style="text-align:right">Taux</th><th style="text-align:right">Montant</th></tr>
            </thead>
            <tbody>
              <tr style="background:#f0fdf4"><td colspan="4"><strong>GAINS</strong></td></tr>
              <tr><td>Salaire de base</td><td class="montant">{bulletin['salaire_base']:,.0f}</td><td class="montant">-</td><td class="montant">{bulletin['salaire_base']:,.0f}</td></tr>
              <tr><td>Prime de transport</td><td class="montant">-</td><td class="montant">-</td><td class="montant">{bulletin['prime_transport']:,.0f}</td></tr>
              <tr><td>Prime de logement</td><td class="montant">-</td><td class="montant">-</td><td class="montant">{bulletin['prime_logement']:,.0f}</td></tr>
              <tr><td>Prime d'ancienneté</td><td class="montant">{bulletin['salaire_base']:,.0f}</td><td class="montant">-</td><td class="montant">{bulletin['prime_anciennete']:,.0f}</td></tr>
              <tr class="total"><td>SALAIRE BRUT</td><td></td><td></td><td class="montant">{bulletin['salaire_brut']:,.0f} FCFA</td></tr>

              <tr style="background:#fee2e2"><td colspan="4"><strong>RETENUES SALARIALES</strong></td></tr>
              <tr><td>IPRES (5.6%)</td><td class="montant">{bulletin['base_ipres']:,.0f}</td><td class="montant">5.6%</td><td class="montant">-{bulletin['ipres_sal']:,.0f}</td></tr>
              <tr><td>CSS (3%)</td><td class="montant">{bulletin['base_css']:,.0f}</td><td class="montant">3.0%</td><td class="montant">-{bulletin['css_sal']:,.0f}</td></tr>
              <tr><td>CFCE (3%)</td><td class="montant">{bulletin['salaire_imposable']:,.0f}</td><td class="montant">3.0%</td><td class="montant">-{bulletin['cfce_sal']:,.0f}</td></tr>
              <tr><td>IRPP</td><td class="montant">{bulletin['salaire_imposable']:,.0f}</td><td class="montant">Barème</td><td class="montant">-{bulletin['irpp']:,.0f}</td></tr>
              <tr class="total" style="background:#fee2e2;color:#991b1b">
                <td>TOTAL RETENUES</td><td></td><td></td><td class="montant">-{bulletin['total_retenues']:,.0f} FCFA</td>
              </tr>
            </tbody>
          </table>

          <table>
            <tr class="net">
              <td style="font-size:1.2rem">NET À PAYER</td>
              <td class="montant" style="font-size:1.4rem">{bulletin['salaire_net']:,.0f} FCFA</td>
            </tr>
          </table>

          <table>
            <thead><tr><th colspan="2">Charges patronales (pour information)</th></tr></thead>
            <tr><td>IPRES patronale (8.4%)</td><td class="montant">{bulletin['ipres_pat']:,.0f} FCFA</td></tr>
            <tr><td>CSS patronale (9%)</td><td class="montant">{bulletin['css_pat']:,.0f} FCFA</td></tr>
            <tr><td>CFCE patronale (3%)</td><td class="montant">{bulletin['cfce_pat']:,.0f} FCFA</td></tr>
            <tr><td>FNP (2%)</td><td class="montant">{bulletin['fnp_pat']:,.0f} FCFA</td></tr>
            <tr class="total"><td>COÛT TOTAL EMPLOYEUR</td><td class="montant">{bulletin['cout_employeur']:,.0f} FCFA</td></tr>
          </table>

          <div style="margin-top:30px;padding-top:20px;border-top:2px dashed #cbd5e0;text-align:center;color:#64748b;font-size:0.8rem">
            <p>Mode de paiement : <strong>{b['mode_paiement'] or 'Virement'}</strong> · {b['banque'] or '-'} · RIB : {b['rib'] or '-'}</p>
            <p style="margin-top:10px">Édité le {b['date_emission'][:10]} · <strong>OMEGA INFORMATIQUE</strong> — Dakar, Sénégal</p>
          </div>
        </div>
        """
        return render_page(content, active='paie', page_title=f"Bulletin {b['numero']}")

    @app.route('/paie/bulletin/<int:bid>/valider')
    @drh_required
    def paie_valider(bid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE bulletins_paie SET statut='Validé' WHERE id=?", (bid,))
            conn.commit()
            conn.close()
            flash("✅ Bulletin validé", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect(f'/paie/bulletin/{bid}')

    @app.route('/paie/bulletin/<int:bid>/payer')
    @drh_required
    def paie_payer(bid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("""UPDATE bulletins_paie SET statut='Payé', date_paiement=?
                         WHERE id=?""", (datetime.now().isoformat(), bid))
            conn.commit()
            conn.close()
            flash("✅ Bulletin marqué comme payé", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect(f'/paie/bulletin/{bid}')

    print("[RH_LOGIC] ✅ Routes paie enregistrées")

    # ==================== FORMATIONS ====================
    @app.route('/formations')
    @staff_required
    def formations_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT f.*,
                     (SELECT COUNT(*) FROM formations_employes WHERE formation_id = f.id) as nb_inscrits
                     FROM formations f ORDER BY f.date_debut DESC""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-graduation-cap"></i> Formations</h2>
            <div class="page-subtitle">Développement des compétences</div>
          </div>
          <a href="/formations/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle formation</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Titre</th><th>Organisme</th><th>Dates</th><th>Durée</th><th>Coût</th><th>Inscrits</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for f in rows:
            content += f"""
            <tr>
              <td><strong>{f['code']}</strong></td>
              <td><strong>{f['titre']}</strong><br><small style="color:#94a3b8">{f['categorie'] or ''}</small></td>
              <td>{f['organisme'] or '-'}</td>
              <td>{f['date_debut'] or '?'} → {f['date_fin'] or '?'}</td>
              <td>{f['duree_heures'] or 0}h</td>
              <td>{f['cout_total']:,.0f} FCFA</td>
              <td><span class="badge badge-primary">{f['nb_inscrits']}</span></td>
              <td>
                <a href="/formations/{f['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-graduation-cap"></i><br>Aucune formation</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='formations', page_title='Formations')

    @app.route('/formations/nouvelle', methods=['GET', 'POST'])
    @rh_required
    def formation_nouvelle():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                code = gen_numero('FORM', 'formations')
                c.execute("""INSERT INTO formations
                    (code, titre, description, categorie, organisme, formateur,
                     date_debut, date_fin, duree_heures, cout_total, lieu, nb_places, statut)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (code, request.form['titre'],
                     request.form.get('description', ''),
                     request.form.get('categorie', ''),
                     request.form.get('organisme', ''),
                     request.form.get('formateur', ''),
                     request.form.get('date_debut') or None,
                     request.form.get('date_fin') or None,
                     int(request.form.get('duree_heures') or 0),
                     float(request.form.get('cout_total') or 0),
                     request.form.get('lieu', ''),
                     int(request.form.get('nb_places') or 0),
                     request.form.get('statut', 'Planifiée')))
                conn.commit()
                conn.close()
                flash(f"✅ Formation {code} créée", "success")
                return redirect('/formations')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = """
        <div class="page-header">
          <h2><i class="fas fa-graduation-cap"></i> Nouvelle Formation</h2>
          <a href="/formations" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Titre *</label><input type="text" name="titre" required></div>
              <div class="form-group"><label>Catégorie</label>
                <select name="categorie">
                  <option value="">--</option>
                  <option>Technique</option><option>Management</option>
                  <option>Langues</option><option>Sécurité</option>
                  <option>Qualité</option><option>Bureautique</option>
                  <option>Commerce</option><option>Autre</option>
                </select>
              </div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="2"></textarea></div>
              <div class="form-group"><label>Organisme</label><input type="text" name="organisme"></div>
              <div class="form-group"><label>Formateur</label><input type="text" name="formateur"></div>
              <div class="form-group"><label>Date début</label><input type="date" name="date_debut"></div>
              <div class="form-group"><label>Date fin</label><input type="date" name="date_fin"></div>
              <div class="form-group"><label>Durée (heures)</label><input type="number" name="duree_heures" value="0"></div>
              <div class="form-group"><label>Coût total (FCFA)</label><input type="number" name="cout_total" step="0.01" value="0"></div>
              <div class="form-group"><label>Lieu</label><input type="text" name="lieu"></div>
              <div class="form-group"><label>Nombre de places</label><input type="number" name="nb_places" value="0"></div>
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  <option value="Planifiée">Planifiée</option>
                  <option value="En cours">En cours</option>
                  <option value="Terminée">Terminée</option>
                  <option value="Annulée">Annulée</option>
                </select>
              </div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/formations" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='formations', page_title='Nouvelle formation')

    @app.route('/formations/<int:fid>')
    @staff_required
    def formation_detail(fid):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM formations WHERE id=?", (fid,))
        f = c.fetchone()
        if not f:
            conn.close()
            flash("Formation introuvable", "danger")
            return redirect('/formations')

        c.execute("""SELECT fe.*, e.nom, e.prenom, e.matricule
                     FROM formations_employes fe
                     JOIN employes e ON fe.employe_id = e.id
                     WHERE fe.formation_id = ?
                     ORDER BY e.nom""", (fid,))
        inscrits = c.fetchall()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-graduation-cap"></i> {f['titre']}</h2>
          <div style="display:flex;gap:10px">
            <a href="/formations/{fid}/inscrire" class="btn btn-success"><i class="fas fa-user-plus"></i> Inscrire</a>
            <a href="/formations" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="card">
          <div class="form-grid">
            <div><strong>Code :</strong> {f['code']}</div>
            <div><strong>Catégorie :</strong> {f['categorie'] or '-'}</div>
            <div><strong>Organisme :</strong> {f['organisme'] or '-'}</div>
            <div><strong>Formateur :</strong> {f['formateur'] or '-'}</div>
            <div><strong>Dates :</strong> {f['date_debut'] or '?'} → {f['date_fin'] or '?'}</div>
            <div><strong>Durée :</strong> {f['duree_heures']} heures</div>
            <div><strong>Coût total :</strong> {f['cout_total']:,.0f} FCFA</div>
            <div><strong>Lieu :</strong> {f['lieu'] or '-'}</div>
          </div>
          {('<p style="margin-top:15px"><strong>Description :</strong> ' + f['description'] + '</p>') if f['description'] else ''}
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-users"></i> Participants ({len(inscrits)})</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Employé</th><th>Statut</th><th>Note</th><th>Appréciation</th></tr></thead>
              <tbody>
        """
        for i in inscrits:
            badge = 'badge-info' if i['statut'] == 'Inscrit' else ('badge-success' if i['statut'] == 'Terminé' else 'badge-warning')
            content += f"""
            <tr>
              <td>{i['nom']} {i['prenom']}<br><small style="color:#94a3b8">{i['matricule']}</small></td>
              <td><span class="badge {badge}">{i['statut']}</span></td>
              <td>{i['note'] if i['note'] else '-'}</td>
              <td>{i['appreciation'] or '-'}</td>
            </tr>
            """
        if not inscrits:
            content += '<tr><td colspan="4" class="empty">Aucun inscrit</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='formations', page_title=f['titre'])

    @app.route('/formations/<int:fid>/inscrire', methods=['GET', 'POST'])
    @rh_required
    def formation_inscrire(fid):
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                employes_ids = request.form.getlist('employe_ids')
                for eid in employes_ids:
                    c.execute("""SELECT id FROM formations_employes WHERE formation_id=? AND employe_id=?""",
                              (fid, int(eid)))
                    if not c.fetchone():
                        c.execute("""INSERT INTO formations_employes
                            (formation_id, employe_id, statut, created_at)
                            VALUES (?, ?, 'Inscrit', ?)""",
                            (fid, int(eid), datetime.now().isoformat()))
                conn.commit()
                conn.close()
                flash(f"✅ {len(employes_ids)} employé(s) inscrits", "success")
                return redirect(f'/formations/{fid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT id, nom, prenom, matricule FROM employes WHERE actif=1
                     AND id NOT IN (SELECT employe_id FROM formations_employes WHERE formation_id=?)
                     ORDER BY nom""", (fid,))
        employes = c.fetchall()
        conn.close()

        emp_checkboxes = "".join(f'''
            <div style="padding:10px;border-bottom:1px solid #f3e8ff;display:flex;align-items:center;gap:10px">
              <input type="checkbox" name="employe_ids" value="{e['id']}" style="width:auto">
              <label style="margin:0;cursor:pointer">{e['nom']} {e['prenom']} <small style="color:#94a3b8">({e['matricule']})</small></label>
            </div>
        ''' for e in employes)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user-plus"></i> Inscrire des employés</h2>
          <a href="/formations/{fid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div style="max-height:400px;overflow-y:auto;border:2px solid #f1f5f9;border-radius:12px;padding:10px;margin-bottom:20px">
              {emp_checkboxes if emp_checkboxes else '<div class="empty" style="padding:20px">Tous les employés sont déjà inscrits</div>'}
            </div>
            <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Inscrire la sélection</button>
          </form>
        </div>
        """
        return render_page(content, active='formations', page_title='Inscrire')

    print("[RH_LOGIC] ✅ Routes formations enregistrées")

    # ==================== ÉVALUATIONS ====================
    @app.route('/evaluations')
    @staff_required
    def evaluations_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT ev.*, e.nom, e.prenom, e.matricule,
                            eva.nom as eval_nom, eva.prenom as eval_prenom
                     FROM evaluations ev
                     JOIN employes e ON ev.employe_id = e.id
                     LEFT JOIN employes eva ON ev.evaluateur_id = eva.id
                     ORDER BY ev.annee DESC, ev.date_evaluation DESC LIMIT 100""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-star"></i> Évaluations</h2>
            <div class="page-subtitle">Performance et développement</div>
          </div>
          <a href="/evaluations/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle évaluation</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Employé</th><th>Évaluateur</th><th>Période</th><th>Note globale</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for ev in rows:
            note_color = '#10b981' if ev['note_globale'] >= 14 else ('#f59e0b' if ev['note_globale'] >= 10 else '#dc2626')
            badge = 'badge-success' if ev['statut'] == 'Validée' else ('badge-warning' if ev['statut'] == 'En cours' else 'badge-info')
            content += f"""
            <tr>
              <td><strong>{ev['numero']}</strong></td>
              <td>{ev['nom']} {ev['prenom']}<br><small style="color:#94a3b8">{ev['matricule']}</small></td>
              <td>{ev['eval_nom'] or '-'} {ev['eval_prenom'] or ''}</td>
              <td>{ev['periode']} {ev['annee']}</td>
              <td><strong style="color:{note_color};font-size:1.1rem">{ev['note_globale']:.2f}/20</strong></td>
              <td><span class="badge {badge}">{ev['statut']}</span></td>
              <td>
                <a href="/evaluations/{ev['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="7" class="empty"><i class="fas fa-star"></i><br>Aucune évaluation</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='evaluations', page_title='Évaluations')

    @app.route('/evaluations/nouvelle', methods=['GET', 'POST'])
    @manager_required
    def evaluation_nouvelle():
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                numero = gen_numero('EVAL', 'evaluations')
                c.execute("""INSERT INTO evaluations
                    (numero, employe_id, evaluateur_id, periode, annee, date_evaluation,
                     note_globale, note_objectifs, note_competences, note_comportement,
                     points_forts, points_ameliorer, objectifs_prochaine_periode,
                     statut, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Brouillon', ?)""",
                    (numero, int(request.form['employe_id']),
                     int(request.form['evaluateur_id']) if request.form.get('evaluateur_id') else None,
                     request.form.get('periode', 'Annuelle'),
                     int(request.form['annee']),
                     datetime.now().isoformat(),
                     float(request.form.get('note_globale') or 0),
                     float(request.form.get('note_objectifs') or 0),
                     float(request.form.get('note_competences') or 0),
                     float(request.form.get('note_comportement') or 0),
                     request.form.get('points_forts', ''),
                     request.form.get('points_ameliorer', ''),
                     request.form.get('objectifs_prochaine_periode', ''),
                     datetime.now().isoformat()))
                conn.commit()
                conn.close()
                flash(f"✅ Évaluation {numero} créée", "success")
                return redirect('/evaluations')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom, prenom, matricule FROM employes WHERE actif=1 ORDER BY nom")
        employes = c.fetchall()
        conn.close()

        emp_opts = "".join(f'<option value="{e["id"]}">{e["nom"]} {e["prenom"]} ({e["matricule"]})</option>' for e in employes)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-star"></i> Nouvelle Évaluation</h2>
          <a href="/evaluations" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Employé *</label><select name="employe_id" required><option value="">--</option>{emp_opts}</select></div>
              <div class="form-group"><label>Évaluateur</label><select name="evaluateur_id"><option value="">--</option>{emp_opts}</select></div>
              <div class="form-group"><label>Période</label>
                <select name="periode">
                  <option value="Annuelle">Annuelle</option>
                  <option value="Semestrielle">Semestrielle</option>
                  <option value="Trimestrielle">Trimestrielle</option>
                  <option value="Probatoire">Probatoire</option>
                </select>
              </div>
              <div class="form-group"><label>Année *</label><input type="number" name="annee" value="{datetime.now().year}" required></div>
              <div class="form-group"><label>Note objectifs (/20)</label><input type="number" name="note_objectifs" step="0.01" min="0" max="20" value="0"></div>
              <div class="form-group"><label>Note compétences (/20)</label><input type="number" name="note_competences" step="0.01" min="0" max="20" value="0"></div>
              <div class="form-group"><label>Note comportement (/20)</label><input type="number" name="note_comportement" step="0.01" min="0" max="20" value="0"></div>
              <div class="form-group"><label>Note globale (/20)</label><input type="number" name="note_globale" step="0.01" min="0" max="20" value="0"></div>
              <div class="form-group form-full"><label>Points forts</label><textarea name="points_forts" rows="2"></textarea></div>
              <div class="form-group form-full"><label>Points à améliorer</label><textarea name="points_ameliorer" rows="2"></textarea></div>
              <div class="form-group form-full"><label>Objectifs prochaine période</label><textarea name="objectifs_prochaine_periode" rows="2"></textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Créer</button>
              <a href="/evaluations" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='evaluations', page_title='Nouvelle évaluation')

    @app.route('/evaluations/<int:evid>')
    @staff_required
    def evaluation_detail(evid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT ev.*, e.nom, e.prenom, e.matricule,
                            eva.nom as eval_nom, eva.prenom as eval_prenom
                     FROM evaluations ev
                     JOIN employes e ON ev.employe_id = e.id
                     LEFT JOIN employes eva ON ev.evaluateur_id = eva.id
                     WHERE ev.id=?""", (evid,))
        ev = c.fetchone()
        if not ev:
            conn.close()
            flash("Évaluation introuvable", "danger")
            return redirect('/evaluations')
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-star"></i> Évaluation {ev['numero']}</h2>
          <a href="/evaluations" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-trophy stat-icon"></i>
            <div class="stat-value">{ev['note_globale']:.1f}</div>
            <div class="stat-label">Note globale /20</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-bullseye stat-icon"></i>
            <div class="stat-value">{ev['note_objectifs']:.1f}</div>
            <div class="stat-label">Objectifs /20</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-brain stat-icon"></i>
            <div class="stat-value">{ev['note_competences']:.1f}</div>
            <div class="stat-label">Compétences /20</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-users stat-icon"></i>
            <div class="stat-value">{ev['note_comportement']:.1f}</div>
            <div class="stat-label">Comportement /20</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
          <div class="form-grid">
            <div><strong>Employé :</strong> {ev['nom']} {ev['prenom']} ({ev['matricule']})</div>
            <div><strong>Évaluateur :</strong> {ev['eval_nom'] or '-'} {ev['eval_prenom'] or ''}</div>
            <div><strong>Période :</strong> {ev['periode']} {ev['annee']}</div>
            <div><strong>Date :</strong> {ev['date_evaluation'][:10]}</div>
            <div><strong>Statut :</strong> <span class="badge badge-info">{ev['statut']}</span></div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-comment"></i> Commentaires</h3></div>
          <div style="display:flex;flex-direction:column;gap:15px">
            <div style="padding:15px;background:#f0fdf4;border-radius:10px;border-left:4px solid #10b981">
              <strong style="color:#065f46">Points forts</strong>
              <p style="margin-top:8px;color:#475569">{ev['points_forts'] or 'Non renseigné'}</p>
            </div>
            <div style="padding:15px;background:#fef3c7;border-radius:10px;border-left:4px solid #f59e0b">
              <strong style="color:#92400e">Points à améliorer</strong>
              <p style="margin-top:8px;color:#475569">{ev['points_ameliorer'] or 'Non renseigné'}</p>
            </div>
            <div style="padding:15px;background:#dbeafe;border-radius:10px;border-left:4px solid #3b82f6">
              <strong style="color:#1e40af">Objectifs prochaine période</strong>
              <p style="margin-top:8px;color:#475569">{ev['objectifs_prochaine_periode'] or 'Non renseigné'}</p>
            </div>
          </div>
        </div>
        """
        return render_page(content, active='evaluations', page_title=f'Évaluation {ev["numero"]}')

    print("[RH_LOGIC] ✅ Routes évaluations enregistrées")

    # ==================== RECRUTEMENT ====================
    @app.route('/recrutement')
    @rh_required
    def recrutement_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT o.*, d.nom as dept_nom,
                     (SELECT COUNT(*) FROM candidats WHERE offre_id = o.id) as nb_candidats
                     FROM offres_emploi o
                     LEFT JOIN departements d ON o.departement_id = d.id
                     ORDER BY o.date_publication DESC""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-user-plus"></i> Recrutement</h2>
            <div class="page-subtitle">Offres d'emploi et candidatures</div>
          </div>
          <a href="/recrutement/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle offre</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Référence</th><th>Titre</th><th>Département</th><th>Type</th><th>Publication</th><th>Candidats</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for o in rows:
            badge = 'badge-success' if o['statut'] == 'Ouverte' else 'badge-info'
            content += f"""
            <tr>
              <td><strong>{o['reference']}</strong></td>
              <td><strong>{o['titre']}</strong></td>
              <td>{o['dept_nom'] or '-'}</td>
              <td><span class="badge badge-primary">{o['type_contrat'] or '-'}</span></td>
              <td>{o['date_publication'][:10]}</td>
              <td><span class="badge badge-warning">{o['nb_candidats']}</span></td>
              <td><span class="badge {badge}">{o['statut']}</span></td>
              <td>
                <a href="/recrutement/{o['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-user-plus"></i><br>Aucune offre</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='recrutement', page_title='Recrutement')

    @app.route('/recrutement/nouvelle', methods=['GET', 'POST'])
    @rh_required
    def recrutement_nouvelle():
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                reference = gen_numero('OFF', 'offres_emploi')
                c.execute("""INSERT INTO offres_emploi
                    (reference, titre, description, departement_id, type_contrat, lieu,
                     salaire_min, salaire_max, date_publication, date_cloture, nb_postes, statut)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (reference, request.form['titre'],
                     request.form.get('description', ''),
                     int(request.form['departement_id']) if request.form.get('departement_id') else None,
                     request.form.get('type_contrat', 'CDI'),
                     request.form.get('lieu', ''),
                     float(request.form.get('salaire_min') or 0),
                     float(request.form.get('salaire_max') or 0),
                     datetime.now().date().isoformat(),
                     request.form.get('date_cloture') or None,
                     int(request.form.get('nb_postes') or 1),
                     'Ouverte'))
                conn.commit()
                conn.close()
                flash(f"✅ Offre {reference} créée", "success")
                return redirect('/recrutement')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom FROM departements WHERE actif=1 ORDER BY nom")
        departements = c.fetchall()
        conn.close()
        depts_opts = "".join(f'<option value="{d["id"]}">{d["nom"]}</option>' for d in departements)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user-plus"></i> Nouvelle Offre</h2>
          <a href="/recrutement" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group form-full"><label>Titre *</label><input type="text" name="titre" required></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="3"></textarea></div>
              <div class="form-group"><label>Département</label><select name="departement_id"><option value="">--</option>{depts_opts}</select></div>
              <div class="form-group"><label>Type contrat</label>
                <select name="type_contrat">
                  <option value="CDI">CDI</option><option value="CDD">CDD</option>
                  <option value="Stage">Stage</option><option value="Intérim">Intérim</option>
                </select>
              </div>
              <div class="form-group"><label>Lieu</label><input type="text" name="lieu" value="Dakar"></div>
              <div class="form-group"><label>Salaire min (FCFA)</label><input type="number" name="salaire_min" value="0"></div>
              <div class="form-group"><label>Salaire max (FCFA)</label><input type="number" name="salaire_max" value="0"></div>
              <div class="form-group"><label>Date clôture</label><input type="date" name="date_cloture"></div>
              <div class="form-group"><label>Nb de postes</label><input type="number" name="nb_postes" value="1"></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Créer l'offre</button>
              <a href="/recrutement" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='recrutement', page_title='Nouvelle offre')

    @app.route('/recrutement/<int:oid>')
    @rh_required
    def recrutement_detail(oid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT o.*, d.nom as dept_nom FROM offres_emploi o
                     LEFT JOIN departements d ON o.departement_id = d.id WHERE o.id=?""", (oid,))
        o = c.fetchone()
        if not o:
            conn.close()
            flash("Offre introuvable", "danger")
            return redirect('/recrutement')

        c.execute("""SELECT * FROM candidats WHERE offre_id = ? ORDER BY created_at DESC""", (oid,))
        candidats = c.fetchall()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user-plus"></i> {o['titre']}</h2>
          <div style="display:flex;gap:10px">
            <a href="/recrutement/{oid}/candidat" class="btn btn-success"><i class="fas fa-plus"></i> Ajouter candidat</a>
            <a href="/recrutement" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="card">
          <div class="form-grid">
            <div><strong>Référence :</strong> {o['reference']}</div>
            <div><strong>Département :</strong> {o['dept_nom'] or '-'}</div>
            <div><strong>Type :</strong> {o['type_contrat'] or '-'}</div>
            <div><strong>Lieu :</strong> {o['lieu'] or '-'}</div>
            <div><strong>Salaire :</strong> {o['salaire_min']:,.0f} - {o['salaire_max']:,.0f} FCFA</div>
            <div><strong>Publication :</strong> {o['date_publication'][:10]}</div>
            <div><strong>Clôture :</strong> {o['date_cloture'] or 'Non définie'}</div>
            <div><strong>Postes :</strong> {o['nb_postes']}</div>
          </div>
          {('<p style="margin-top:15px"><strong>Description :</strong> ' + o['description'] + '</p>') if o['description'] else ''}
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-users"></i> Candidats ({len(candidats)})</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Nom</th><th>Contact</th><th>Expérience</th><th>Prétentions</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for c_ in candidats:
            badge = 'badge-info' if c_['statut'] == 'Nouveau' else ('badge-success' if c_['statut'] == 'Recruté' else 'badge-warning')
            content += f"""
            <tr>
              <td><strong>{c_['nom']} {c_['prenom']}</strong></td>
              <td>{c_['email'] or '-'}<br><small>{c_['telephone']}</small></td>
              <td>{c_['experience_annees']} ans</td>
              <td>{c_['pretentions_salariales']:,.0f} FCFA</td>
              <td><span class="badge {badge}">{c_['statut']}</span></td>
            </tr>
            """
        if not candidats:
            content += '<tr><td colspan="5" class="empty">Aucun candidat</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='recrutement', page_title=o['titre'])

    @app.route('/recrutement/<int:oid>/candidat', methods=['GET', 'POST'])
    @rh_required
    def recrutement_candidat(oid):
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute("""INSERT INTO candidats
                    (offre_id, nom, prenom, email, telephone, date_naissance, adresse,
                     diplome, experience_annees, pretentions_salariales, statut, source, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Nouveau', ?, ?)""",
                    (oid, request.form['nom'], request.form['prenom'],
                     request.form.get('email', ''), request.form['telephone'],
                     request.form.get('date_naissance') or None,
                     request.form.get('adresse', ''),
                     request.form.get('diplome', ''),
                     int(request.form.get('experience_annees') or 0),
                     float(request.form.get('pretentions_salariales') or 0),
                     request.form.get('source', ''),
                     datetime.now().isoformat()))
                conn.commit()
                conn.close()
                flash("✅ Candidat ajouté", "success")
                return redirect(f'/recrutement/{oid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user-plus"></i> Nouveau Candidat</h2>
          <a href="/recrutement/{oid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" required></div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email"></div>
              <div class="form-group"><label>Date naissance</label><input type="date" name="date_naissance"></div>
              <div class="form-group"><label>Adresse</label><input type="text" name="adresse"></div>
              <div class="form-group"><label>Diplôme</label><input type="text" name="diplome"></div>
              <div class="form-group"><label>Expérience (années)</label><input type="number" name="experience_annees" value="0"></div>
              <div class="form-group"><label>Prétentions salariales</label><input type="number" name="pretentions_salariales" step="0.01" value="0"></div>
              <div class="form-group"><label>Source</label><input type="text" name="source" placeholder="LinkedIn, recommandation..."></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Ajouter</button>
              <a href="/recrutement/{oid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='recrutement', page_title='Nouveau candidat')

    print("[RH_LOGIC] ✅ Routes recrutement enregistrées")

    # ==================== RAPPORTS ====================
    @app.route('/rapports')
    @rh_required
    def rapports():
        conn = get_db()
        c = conn.cursor()

        # Effectif par genre
        c.execute("""SELECT sexe, COUNT(*) as nb FROM employes WHERE actif=1 AND statut='Actif' GROUP BY sexe""")
        par_genre = c.fetchall()

        # Effectif par type contrat
        c.execute("""SELECT type_contrat, COUNT(*) as nb FROM employes WHERE actif=1 AND statut='Actif' GROUP BY type_contrat""")
        par_contrat = c.fetchall()

        # Effectif par département
        c.execute("""SELECT d.nom, COUNT(e.id) as nb FROM departements d
                     LEFT JOIN employes e ON e.departement_id = d.id AND e.actif=1
                     WHERE d.actif=1 GROUP BY d.id ORDER BY nb DESC""")
        par_dept = c.fetchall()

        # Masse salariale par département
        c.execute("""SELECT d.nom, COALESCE(SUM(e.salaire_base), 0) as masse
                     FROM departements d LEFT JOIN employes e ON e.departement_id = d.id AND e.actif=1
                     WHERE d.actif=1 GROUP BY d.id ORDER BY masse DESC""")
        masse_dept = c.fetchall()

        # Effectif par ancienneté
        c.execute("""SELECT
                     SUM(CASE WHEN julianday('now') - julianday(date_embauche) < 365 THEN 1 ELSE 0 END) as moins_1,
                     SUM(CASE WHEN julianday('now') - julianday(date_embauche) BETWEEN 365 AND 1825 THEN 1 ELSE 0 END) as de_1_a_5,
                     SUM(CASE WHEN julianday('now') - julianday(date_embauche) > 1825 THEN 1 ELSE 0 END) as plus_5
                     FROM employes WHERE actif=1 AND statut='Actif'""")
        anciennete = c.fetchone()

        # Congés par type (année en cours)
        c.execute("""SELECT tc.nom, tc.couleur, COUNT(cg.id) as nb
                     FROM types_conges tc
                     LEFT JOIN conges cg ON cg.type_conge_id = tc.id
                         AND strftime('%Y', cg.date_debut) = strftime('%Y', 'now')
                     WHERE tc.actif=1 GROUP BY tc.id ORDER BY nb DESC""")
        conges_par_type = c.fetchall()

        # Turnover (départs cette année)
        c.execute("""SELECT COUNT(*) FROM employes
                     WHERE statut IN ('Démission', 'Licencié', 'Retraite')
                     AND strftime('%Y', date_fin_contrat) = strftime('%Y', 'now')""")
        departs = c.fetchone()[0]

        # Embauchés cette année
        c.execute("""SELECT COUNT(*) FROM employes
                     WHERE strftime('%Y', date_embauche) = strftime('%Y', 'now')""")
        embauches = c.fetchone()[0]

        conn.close()

        total_effectif = sum(g['nb'] for g in par_genre)
        hommes = next((g['nb'] for g in par_genre if g['sexe'] == 'M'), 0)
        femmes = next((g['nb'] for g in par_genre if g['sexe'] == 'F'), 0)

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-chart-line"></i> Rapports RH</h2>
            <div class="page-subtitle">Analyses et statistiques du capital humain</div>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-users stat-icon"></i>
            <div class="stat-value">{total_effectif}</div>
            <div class="stat-label">Effectif total</div>
          </div>
          <div class="stat-card pink">
            <i class="fas fa-venus stat-icon"></i>
            <div class="stat-value">{femmes}</div>
            <div class="stat-label">Femmes ({int(femmes/total_effectif*100) if total_effectif else 0}%)</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-mars stat-icon"></i>
            <div class="stat-value">{hommes}</div>
            <div class="stat-label">Hommes ({int(hommes/total_effectif*100) if total_effectif else 0}%)</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-user-plus stat-icon"></i>
            <div class="stat-value">{embauches}</div>
            <div class="stat-label">Embauches année</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-user-minus stat-icon"></i>
            <div class="stat-value">{departs}</div>
            <div class="stat-label">Départs année</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-sitemap"></i> Effectif par département</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Département</th><th>Effectif</th><th>%</th><th>Masse salariale</th></tr></thead>
              <tbody>
        """
        for d in par_dept:
            pct = (d['nb'] / total_effectif * 100) if total_effectif else 0
            masse = next((m['masse'] for m in masse_dept if m['nom'] == d['nom']), 0)
            content += f"""
            <tr>
              <td><strong>{d['nom']}</strong></td>
              <td>{d['nb']}</td>
              <td>{pct:.1f}%</td>
              <td><strong style="color:#7c3aed">{masse:,.0f}</strong> FCFA</td>
            </tr>
            """
        content += "</tbody></table></div></div>"

        content += """
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="card">
            <div class="card-header"><h3><i class="fas fa-file-signature"></i> Par type de contrat</h3></div>
        """
        for ct in par_contrat:
            pct = (ct['nb'] / total_effectif * 100) if total_effectif else 0
            content += f"""
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px dashed #f3e8ff">
              <span style="font-weight:700">{ct['type_contrat']}</span>
              <span><strong>{ct['nb']}</strong> ({pct:.1f}%)</span>
            </div>
            """
        content += "</div>"

        content += """
          <div class="card">
            <div class="card-header"><h3><i class="fas fa-hourglass-half"></i> Par ancienneté</h3></div>
        """
        if anciennete:
            a = anciennete
            content += f"""
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px dashed #f3e8ff">
              <span style="font-weight:700">&lt; 1 an</span><strong>{a['moins_1'] or 0}</strong>
            </div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px dashed #f3e8ff">
              <span style="font-weight:700">1 à 5 ans</span><strong>{a['de_1_a_5'] or 0}</strong>
            </div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px dashed #f3e8ff">
              <span style="font-weight:700">&gt; 5 ans</span><strong>{a['plus_5'] or 0}</strong>
            </div>
            """
        content += "</div></div>"

        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-calendar-check"></i> Congés par type (année en cours)</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Type</th><th>Nombre</th><th>Répartition</th></tr></thead>
              <tbody>
        """
        max_cg = max([c_['nb'] for c_ in conges_par_type], default=1)
        for cg in conges_par_type:
            pct = int((cg['nb'] / max_cg) * 100) if max_cg else 0
            content += f"""
            <tr>
              <td><span class="badge" style="background:{cg['couleur']}20;color:{cg['couleur']}">{cg['nom']}</span></td>
              <td><strong>{cg['nb']}</strong></td>
              <td>
                <div style="background:#f3e8ff;border-radius:6px;height:16px;overflow:hidden;width:200px">
                  <div style="background:{cg['couleur'] or '#7c3aed'};height:100%;width:{pct}%"></div>
                </div>
              </td>
            </tr>
            """
        content += "</tbody></table></div></div>"
        return render_page(content, active='rapports', page_title='Rapports RH')

    print("[RH_LOGIC] ✅ Routes rapports enregistrées")

    # ==================== MES DEMANDES (employé) ====================
    @app.route('/mes-conges')
    @role_required('employe')
    def mes_conges():
        conn = get_db()
        c = conn.cursor()
        emp_id = current_user.employe_id if current_user else None

        if not emp_id:
            conn.close()
            flash("Aucun employé lié à votre compte", "warning")
            return redirect('/mon-espace')

        c.execute("""SELECT cg.*, tc.nom as type_nom, tc.couleur
                     FROM conges cg
                     JOIN types_conges tc ON cg.type_conge_id = tc.id
                     WHERE cg.employe_id = ?
                     ORDER BY cg.date_debut DESC""", (emp_id,))
        conges = c.fetchall()

        # Solde congés annuels
        c.execute("""SELECT tc.jours_par_an, COALESCE(SUM(cg.nb_jours), 0) as pris
                     FROM types_conges tc
                     LEFT JOIN conges cg ON cg.type_conge_id = tc.id AND cg.employe_id = ?
                         AND cg.statut = 'Approuvé'
                         AND strftime('%Y', cg.date_debut) = strftime('%Y', 'now')
                     WHERE tc.code = 'CA'""", (emp_id,))
        solde = c.fetchone()
        conn.close()

        solde_total = (solde['jours_par_an'] if solde else 30) or 30
        solde_pris = solde['pris'] if solde else 0
        solde_restant = solde_total - solde_pris

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-calendar-check"></i> Mes congés</h2>
            <div class="page-subtitle">Mes demandes et mon solde</div>
          </div>
          <a href="/conges/nouveau?employe_id={emp_id}" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle demande</a>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-calendar-day stat-icon"></i>
            <div class="stat-value">{solde_total}</div>
            <div class="stat-label">Jours annuels</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-check stat-icon"></i>
            <div class="stat-value">{solde_pris:.0f}</div>
            <div class="stat-label">Jours pris</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-calendar-plus stat-icon"></i>
            <div class="stat-value">{solde_restant:.0f}</div>
            <div class="stat-label">Solde restant</div>
          </div>
        </div>

        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Type</th><th>Période</th><th>Jours</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for cg in conges:
            badge = 'badge-warning'
            if cg['statut'] == 'Approuvé': badge = 'badge-success'
            elif cg['statut'] == 'Refusé': badge = 'badge-danger'
            content += f"""
            <tr>
              <td><strong>{cg['numero']}</strong></td>
              <td><span class="badge" style="background:{cg['couleur']}20;color:{cg['couleur']}">{cg['type_nom']}</span></td>
              <td>{cg['date_debut']} → {cg['date_fin']}</td>
              <td><strong>{cg['nb_jours']}j</strong></td>
              <td><span class="badge {badge}">{cg['statut']}</span></td>
            </tr>
            """
        if not conges:
            content += '<tr><td colspan="5" class="empty"><i class="fas fa-calendar-check"></i><br>Aucune demande</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='mes_conges', page_title='Mes congés')

    @app.route('/mes-bulletins')
    @role_required('employe')
    def mes_bulletins():
        conn = get_db()
        c = conn.cursor()
        emp_id = current_user.employe_id if current_user else None

        if not emp_id:
            conn.close()
            flash("Aucun employé lié", "warning")
            return redirect('/mon-espace')

        c.execute("""SELECT * FROM bulletins_paie WHERE employe_id = ?
                     ORDER BY annee DESC, mois DESC""", (emp_id,))
        bulletins = c.fetchall()

        # YTD
        c.execute("""SELECT COALESCE(SUM(salaire_brut), 0), COALESCE(SUM(salaire_net), 0)
                     FROM bulletins_paie WHERE employe_id = ?
                     AND strftime('%Y', date_emission) = strftime('%Y', 'now')""", (emp_id,))
        ytd = c.fetchone()
        conn.close()

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-file-invoice-dollar"></i> Mes bulletins de paie</h2>
            <div class="page-subtitle">Historique de ma rémunération</div>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-money-bill stat-icon"></i>
            <div class="stat-value">{ytd[0]:,.0f}</div>
            <div class="stat-label">Brut cumulé {datetime.now().year}</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-hand-holding-usd stat-icon"></i>
            <div class="stat-value">{ytd[1]:,.0f}</div>
            <div class="stat-label">Net cumulé {datetime.now().year}</div>
          </div>
        </div>

        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Période</th><th>Brut</th><th>Retenues</th><th>Net</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for b in bulletins:
            badge = 'badge-success' if b['statut'] == 'Payé' else 'badge-info'
            content += f"""
            <tr>
              <td><strong>{b['numero']}</strong></td>
              <td><strong>{b['mois']:02d}/{b['annee']}</strong></td>
              <td>{b['salaire_brut']:,.0f} FCFA</td>
              <td>{b['total_retenues']:,.0f} FCFA</td>
              <td><strong style="color:#059669">{b['salaire_net']:,.0f} FCFA</strong></td>
              <td><span class="badge {badge}">{b['statut']}</span></td>
              <td>
                <a href="/paie/bulletin/{b['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
              </td>
            </tr>
            """
        if not bulletins:
            content += '<tr><td colspan="7" class="empty"><i class="fas fa-file-invoice-dollar"></i><br>Aucun bulletin</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='mes_bulletins', page_title='Mes bulletins')

    @app.route('/mon-espace')
    @role_required('employe')
    def mon_espace():
        conn = get_db()
        c = conn.cursor()
        emp_id = current_user.employe_id if current_user else None

        if not emp_id:
            conn.close()
            content = """
            <div class="card">
              <div class="empty">
                <i class="fas fa-user-slash"></i>
                <h3>Aucun dossier employé lié</h3>
                <p>Contactez les RH pour lier votre compte à votre dossier.</p>
              </div>
            </div>
            """
            return render_page(content, active='mon_espace', page_title='Mon espace')

        c.execute("""SELECT e.*, p.intitule as poste_nom, d.nom as dept_nom, s.nom as site_nom
                     FROM employes e
                     LEFT JOIN postes p ON e.poste_id = p.id
                     LEFT JOIN departements d ON e.departement_id = d.id
                     LEFT JOIN sites s ON e.site_id = s.id
                     WHERE e.id=?""", (emp_id,))
        e = c.fetchone()

        # Derniers pointages
        c.execute("""SELECT * FROM pointages WHERE employe_id = ?
                     ORDER BY date_pointage DESC LIMIT 5""", (emp_id,))
        pointages = c.fetchall()

        # Solde congés
        c.execute("""SELECT COALESCE(SUM(nb_jours), 0) FROM conges
                     WHERE employe_id = ? AND statut='Approuvé'
                     AND strftime('%Y', date_debut) = strftime('%Y', 'now')""", (emp_id,))
        conges_pris = c.fetchone()[0]

        conn.close()

        try:
            emb = datetime.fromisoformat(e['date_embauche'])
            anciennete = (datetime.now() - emb).days // 365
        except Exception:
            anciennete = '?'

        salaire_total = (e['salaire_base'] or 0) + (e['prime_transport'] or 0) + (e['prime_logement'] or 0) + (e['prime_autre'] or 0)

        content = f"""
        <div class="hero">
          <h1>Bonjour <span>{e['prenom']}</span> 👋</h1>
          <p>Bienvenue sur votre espace personnel · {e['matricule']}</p>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-briefcase stat-icon"></i>
            <div class="stat-value" style="font-size:1.1rem">{e['poste_nom'] or '-'}</div>
            <div class="stat-label">Mon poste</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-calendar stat-icon"></i>
            <div class="stat-value">{anciennete} ans</div>
            <div class="stat-label">Ancienneté</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-money-bill-wave stat-icon"></i>
            <div class="stat-value">{salaire_total:,.0f}</div>
            <div class="stat-label">Salaire brut (FCFA)</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-calendar-check stat-icon"></i>
            <div class="stat-value">{conges_pris:.0f}j</div>
            <div class="stat-label">Congés pris</div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-bottom:25px">
          <a href="/mes-conges" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:25px;border-left:5px solid #10b981">
              <i class="fas fa-calendar-plus" style="font-size:2rem;color:#10b981;margin-bottom:10px"></i>
              <div style="font-weight:800;color:#4c1d95">Mes congés</div>
            </div>
          </a>
          <a href="/mes-bulletins" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:25px;border-left:5px solid #7c3aed">
              <i class="fas fa-file-invoice-dollar" style="font-size:2rem;color:#7c3aed;margin-bottom:10px"></i>
              <div style="font-weight:800;color:#4c1d95">Mes bulletins</div>
            </div>
          </a>
          <a href="/employes/{emp_id}" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:25px;border-left:5px solid #0891b2">
              <i class="fas fa-user-circle" style="font-size:2rem;color:#0891b2;margin-bottom:10px"></i>
              <div style="font-weight:800;color:#4c1d95">Ma fiche</div>
            </div>
          </a>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Mon dossier</h3></div>
          <div class="form-grid">
            <div><strong>Matricule :</strong> {e['matricule']}</div>
            <div><strong>Nom :</strong> {e['nom']} {e['prenom']}</div>
            <div><strong>Poste :</strong> {e['poste_nom'] or '-'}</div>
            <div><strong>Département :</strong> {e['dept_nom'] or '-'}</div>
            <div><strong>Site :</strong> {e['site_nom'] or '-'}</div>
            <div><strong>Type contrat :</strong> {e['type_contrat']}</div>
            <div><strong>Date embauche :</strong> {e['date_embauche']}</div>
            <div><strong>Salaire base :</strong> {e['salaire_base']:,.0f} FCFA</div>
            <div><strong>Téléphone :</strong> {e['telephone']}</div>
            <div><strong>Email :</strong> {e['email'] or '-'}</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-clock"></i> Mes derniers pointages</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Arrivée</th><th>Départ</th><th>Heures</th></tr></thead>
              <tbody>
        """
        for p in pointages:
            content += f"""
            <tr>
              <td><strong>{p['date_pointage']}</strong></td>
              <td>{p['heure_arrivee'] or '-'}</td>
              <td>{p['heure_depart'] or '-'}</td>
              <td>{p['heures_travaillees']:.2f}h</td>
            </tr>
            """
        if not pointages:
            content += '<tr><td colspan="4" class="empty">Aucun pointage</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='mon_espace', page_title='Mon espace')

    print("[RH_LOGIC] ✅ Routes employé + rapports enregistrées")
