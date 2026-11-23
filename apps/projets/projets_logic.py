"""
Module Logique Métier Projets
WBS, Tâches, Gantt, Dépendances, Ressources, Risques, EVM, Budget, Timesheets
"""
from flask import render_template_string, request, redirect, flash, jsonify
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "/app/data/projets.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def gen_code(prefix, table):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"SELECT COUNT(*) FROM {table}")
    n = c.fetchone()[0] + 1
    conn.close()
    return f"{prefix}-{n:04d}"


def recalculer_evm(projet_id, conn=None):
    """Recalcule les indicateurs EVM d'un projet"""
    close_after = False
    if conn is None:
        conn = get_db()
        close_after = True

    c = conn.cursor()

    # BAC = Budget at Completion (budget prévu)
    c.execute("SELECT budget_prevu FROM projets WHERE id=?", (projet_id,))
    row = c.fetchone()
    bac = row['budget_prevu'] if row else 0

    # PV = Planned Value (valeur planifiée = avancement prévu x BAC)
    c.execute("""SELECT COALESCE(SUM(cout_prevu), 0) FROM taches
                 WHERE projet_id = ? AND statut != 'Annulée'""", (projet_id,))
    pv = c.fetchone()[0]

    # EV = Earned Value (valeur acquise = avancement x budget)
    c.execute("""SELECT COALESCE(SUM(cout_prevu * avancement_pct / 100), 0)
                 FROM taches WHERE projet_id = ? AND statut != 'Annulée'""", (projet_id,))
    ev = c.fetchone()[0]

    # AC = Actual Cost (coût réel)
    c.execute("""SELECT COALESCE(SUM(cout_reel), 0) FROM taches
                 WHERE projet_id = ?""", (projet_id,))
    ac = c.fetchone()[0]

    # Indicateurs
    sv = ev - pv
    cv = ev - ac
    spi = (ev / pv) if pv > 0 else 1.0
    cpi = (ev / ac) if ac > 0 else 1.0
    eac = (bac / cpi) if cpi > 0 else bac
    etc = eac - ac
    vac = bac - eac
    tcpi = ((bac - ev) / (bac - ac)) if (bac - ac) > 0 else 1.0

    today = datetime.now().isoformat()

    c.execute("""INSERT INTO evm
        (projet_id, date_mesure, pv, ev, ac, bac, sv, cv, spi, cpi, eac, etc, vac, tcpi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (projet_id, today, pv, ev, ac, bac, sv, cv, spi, cpi, eac, etc, vac, tcpi))

    if close_after:
        conn.commit()
        conn.close()

    return {
        'pv': pv, 'ev': ev, 'ac': ac, 'bac': bac,
        'sv': sv, 'cv': cv, 'spi': spi, 'cpi': cpi,
        'eac': eac, 'etc': etc, 'vac': vac, 'tcpi': tcpi
    }


try:
    from auth import (role_required, admin_required, directeur_required,
                      chef_required, staff_required, membre_required, log_action)
    from flask_login import current_user
except ImportError:
    def role_required(*r):
        def d(f): return f
        return d
    def admin_required(f): return f
    def directeur_required(f): return f
    def chef_required(f): return f
    def staff_required(f): return f
    def membre_required(f): return f
    def log_action(*a, **k): pass
    current_user = None


def register_projets_routes(app, render_page):
    """Enregistre toutes les routes logique métier Projets"""

    # ==================== TÂCHES ====================
    @app.route('/taches')
    @membre_required
    def taches_liste():
        conn = get_db()
        c = conn.cursor()

        projet_filter = request.args.get('projet_id', '')
        statut_filter = request.args.get('statut', '')
        resp_filter = request.args.get('responsable', '')
        search = request.args.get('q', '').strip()

        query = """SELECT t.*, p.nom as projet_nom, p.code as projet_code,
                          u.nom as resp_nom, u.prenom as resp_prenom
                   FROM taches t
                   JOIN projets p ON t.projet_id = p.id
                   LEFT JOIN utilisateurs u ON t.responsable_id = u.id
                   WHERE 1=1"""
        params = []

        if projet_filter:
            query += " AND t.projet_id = ?"
            params.append(int(projet_filter))
        if statut_filter:
            query += " AND t.statut = ?"
            params.append(statut_filter)
        if resp_filter:
            query += " AND t.responsable_id = ?"
            params.append(int(resp_filter))
        if search:
            query += " AND (t.nom LIKE ? OR t.code LIKE ?)"
            params.extend([f'%{search}%'] * 2)

        query += " ORDER BY t.date_debut_prevue ASC, t.priorite DESC LIMIT 500"
        c.execute(query, params)
        rows = c.fetchall()

        # Filtres
        c.execute("SELECT id, code, nom FROM projets WHERE actif=1 ORDER BY nom")
        projets = c.fetchall()
        c.execute("SELECT id, nom, prenom FROM utilisateurs WHERE actif=1 ORDER BY nom")
        users = c.fetchall()

        # Stats
        c.execute("SELECT COUNT(*) FROM taches WHERE statut='En cours'")
        en_cours = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM taches WHERE statut='À faire'")
        a_faire = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM taches WHERE statut='Terminée'")
        terminees = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM taches WHERE statut='En retard'")
        retards = c.fetchone()[0]
        conn.close()

        projets_opts = "".join(f'<option value="{p["id"]}" {"selected" if projet_filter == str(p["id"]) else ""}>{p["code"]} - {p["nom"][:30]}</option>' for p in projets)
        users_opts = "".join(f'<option value="{u["id"]}" {"selected" if resp_filter == str(u["id"]) else ""}>{u["prenom"]} {u["nom"]}</option>' for u in users)
        statuts = ['À faire', 'En cours', 'En revue', 'Terminée', 'Bloquée', 'En retard']
        statuts_opts = "".join(f'<option value="{s}" {"selected" if statut_filter == s else ""}>{s}</option>' for s in statuts)

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-tasks"></i> Tâches</h2>
            <div class="page-subtitle">{len(rows)} tâche(s)</div>
          </div>
          <a href="/taches/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle tâche</a>
        </div>

        <div class="stats">
          <div class="stat-card blue">
            <i class="fas fa-list stat-icon"></i>
            <div class="stat-value">{a_faire}</div>
            <div class="stat-label">À faire</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-spinner stat-icon"></i>
            <div class="stat-value">{en_cours}</div>
            <div class="stat-label">En cours</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-check stat-icon"></i>
            <div class="stat-value">{terminees}</div>
            <div class="stat-label">Terminées</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-exclamation stat-icon"></i>
            <div class="stat-value">{retards}</div>
            <div class="stat-label">En retard</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Liste des tâches</h3>
            <form method="GET" style="display:flex;gap:8px;flex-wrap:wrap">
              <select name="projet_id" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous projets</option>
                {projets_opts}
              </select>
              <select name="statut" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous statuts</option>
                {statuts_opts}
              </select>
              <select name="responsable" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous responsables</option>
                {users_opts}
              </select>
              <input type="text" name="q" value="{search}" placeholder="Code, nom..." style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px;width:150px">
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Code</th><th>Tâche</th><th>Projet</th><th>Responsable</th>
                  <th>Dates</th><th>Effort</th><th>Avanc.</th><th>Statut</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
        """
        for t in rows:
            statut_badge = 'badge-info'
            if t['statut'] == 'En cours': statut_badge = 'badge-warning'
            elif t['statut'] == 'Terminée': statut_badge = 'badge-success'
            elif t['statut'] in ['En retard', 'Bloquée']: statut_badge = 'badge-danger'

            av = t['avancement_pct'] or 0
            cc = '<span class="badge badge-danger" style="font-size:0.6rem;padding:2px 6px">CC</span> ' if t['chemin_critique'] else ''

            content += f"""
            <tr>
              <td><strong>{t['code']}</strong><br><small style="color:#94a3b8">{t['wbs_code'] or ''}</small></td>
              <td>{cc}<strong>{t['nom'][:40]}</strong></td>
              <td><small>{t['projet_code']}<br>{t['projet_nom'][:25]}</small></td>
              <td>{t['resp_prenom'] or '?'} {t['resp_nom'] or ''}</td>
              <td><small>{t['date_debut_prevue'] or '?'} → {t['date_fin_prevue'] or '?'}</small></td>
              <td>{t['effort_estime']:.0f}h</td>
              <td>
                <strong>{av:.0f}%</strong>
                <div style="background:#eff6ff;border-radius:6px;height:6px;margin-top:4px;overflow:hidden">
                  <div style="background:#2563eb;height:100%;width:{av}%"></div>
                </div>
              </td>
              <td><span class="badge {statut_badge}">{t['statut']}</span></td>
              <td>
                <a href="/taches/{t['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
                <a href="/taches/{t['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="9" class="empty"><i class="fas fa-tasks"></i><br>Aucune tâche</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='taches', page_title='Tâches')

    @app.route('/taches/nouvelle', methods=['GET', 'POST'])
    @chef_required
    def tache_nouvelle():
        conn = get_db()
        c = conn.cursor()
        projet_id_pre = request.args.get('projet_id', '')

        if request.method == 'POST':
            try:
                code = gen_code('T', 'taches')
                projet_id = int(request.form['projet_id'])
                date_debut = request.form.get('date_debut_prevue', '')
                date_fin = request.form.get('date_fin_prevue', '')

                effort = float(request.form.get('effort_estime') or 0)
                cout_prevu = float(request.form.get('cout_prevu') or 0)

                c.execute("""INSERT INTO taches
                    (code, projet_id, phase_id, wbs_code, wbs_niveau, parent_id, nom, description,
                     type_tache, responsable_id, priorite, complexite,
                     date_debut_prevue, date_fin_prevue, effort_estime, cout_prevu,
                     statut, jalon, chemin_critique, methode_agile, story_points, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (code, projet_id,
                     int(request.form['phase_id']) if request.form.get('phase_id') else None,
                     request.form.get('wbs_code', ''), int(request.form.get('wbs_niveau') or 1),
                     int(request.form['parent_id']) if request.form.get('parent_id') else None,
                     request.form['nom'], request.form.get('description', ''),
                     request.form.get('type_tache', 'Tâche'),
                     int(request.form['responsable_id']) if request.form.get('responsable_id') else None,
                     request.form.get('priorite', 'Normale'),
                     int(request.form.get('complexite') or 1),
                     date_debut, date_fin, effort, cout_prevu,
                     request.form.get('statut', 'À faire'),
                     1 if request.form.get('jalon') else 0,
                     1 if request.form.get('chemin_critique') else 0,
                     request.form.get('methode_agile', ''),
                     int(request.form.get('story_points') or 0),
                     request.form.get('notes', '')))
                conn.commit()
                conn.close()

                if current_user:
                    log_action(current_user.id, 'CREATE_TACHE', code)

                flash(f"✅ Tâche {code} créée", "success")
                return redirect(f'/taches?projet_id={projet_id}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, code, nom FROM projets WHERE actif=1 ORDER BY nom")
        projets = c.fetchall()
        c.execute("SELECT id, nom, prenom FROM utilisateurs WHERE actif=1 ORDER BY nom")
        users = c.fetchall()
        c.execute("SELECT id, nom FROM phases WHERE projet_id = ? ORDER BY ordre", (int(projet_id_pre) if projet_id_pre else 0,))
        phases = c.fetchall()
        conn.close()

        projets_opts = "".join(f'<option value="{p["id"]}" {"selected" if str(p["id"])==projet_id_pre else ""}>{p["code"]} - {p["nom"][:40]}</option>' for p in projets)
        users_opts = "".join(f'<option value="{u["id"]}">{u["prenom"]} {u["nom"]}</option>' for u in users)
        phases_opts = "".join(f'<option value="{ph["id"]}">{ph["nom"]}</option>' for ph in phases)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-plus"></i> Nouvelle Tâche</h2>
          <a href="/taches" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group form-full"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="2"></textarea></div>
              <div class="form-group"><label>Projet *</label><select name="projet_id" required><option value="">--</option>{projets_opts}</select></div>
              <div class="form-group"><label>Phase</label><select name="phase_id"><option value="">--</option>{phases_opts}</select></div>
              <div class="form-group"><label>Responsable</label><select name="responsable_id"><option value="">--</option>{users_opts}</select></div>
              <div class="form-group"><label>Type</label>
                <select name="type_tache">
                  <option value="Tâche">Tâche</option>
                  <option value="Jalon">Jalon</option>
                  <option value="Lot de travail">Lot de travail</option>
                  <option value="Livrable">Livrable</option>
                  <option value="User Story">User Story</option>
                </select>
              </div>
              <div class="form-group"><label>WBS Code</label><input type="text" name="wbs_code" placeholder="1.2.3"></div>
              <div class="form-group"><label>Priorité</label>
                <select name="priorite">
                  <option value="Basse">Basse</option>
                  <option value="Normale" selected>Normale</option>
                  <option value="Haute">Haute</option>
                  <option value="Critique">Critique</option>
                </select>
              </div>
              <div class="form-group"><label>Date début prévue</label><input type="date" name="date_debut_prevue"></div>
              <div class="form-group"><label>Date fin prévue</label><input type="date" name="date_fin_prevue"></div>
              <div class="form-group"><label>Effort estimé (heures)</label><input type="number" name="effort_estime" step="0.5" value="0"></div>
              <div class="form-group"><label>Coût prévu (FCFA)</label><input type="number" name="cout_prevu" step="100" value="0"></div>
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  <option value="À faire">À faire</option>
                  <option value="En cours">En cours</option>
                  <option value="Terminée">Terminée</option>
                </select>
              </div>
              <div class="form-group"><label>Story Points (Agile)</label><input type="number" name="story_points" value="0"></div>
              <div class="form-group" style="display:flex;align-items:center;gap:8px;margin-top:30px">
                <input type="checkbox" name="chemin_critique" style="width:auto">
                <label style="margin:0">Chemin critique</label>
              </div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Créer</button>
              <a href="/taches" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='taches', page_title='Nouvelle tâche')

    @app.route('/taches/<int:tid>', methods=['GET', 'POST'])
    @membre_required
    def tache_detail(tid):
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            # Mise à jour rapide de l'avancement
            try:
                av = float(request.form.get('avancement_pct') or 0)
                statut = request.form.get('statut', 'En cours')
                effort_reel = float(request.form.get('effort_consomme') or 0)
                cout_reel = float(request.form.get('cout_reel') or 0)

                c.execute("""UPDATE taches SET
                    avancement_pct=?, statut=?, effort_consomme=?, cout_reel=?
                    WHERE id=?""", (av, statut, effort_reel, cout_reel, tid))
                conn.commit()

                # Recalculer EVM du projet
                c.execute("SELECT projet_id FROM taches WHERE id=?", (tid,))
                t = c.fetchone()
                if t:
                    recalculer_evm(t['projet_id'], conn)

                conn.close()
                flash("✅ Tâche mise à jour", "success")
                return redirect(f'/taches/{tid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("""SELECT t.*, p.nom as projet_nom, p.code as projet_code,
                            u.nom as resp_nom, u.prenom as resp_prenom
                     FROM taches t
                     JOIN projets p ON t.projet_id = p.id
                     LEFT JOIN utilisateurs u ON t.responsable_id = u.id
                     WHERE t.id=?""", (tid,))
        t = c.fetchone()
        if not t:
            conn.close()
            flash("Tâche introuvable", "danger")
            return redirect('/taches')

        # Dépendances
        c.execute("""SELECT d.*, t1.code as src_code, t1.nom as src_nom,
                            t2.code as cible_code, t2.nom as cible_nom
                     FROM dependances d
                     JOIN taches t1 ON d.tache_source_id = t1.id
                     JOIN taches t2 ON d.tache_cible_id = t2.id
                     WHERE d.tache_source_id = ? OR d.tache_cible_id = ?""", (tid, tid))
        deps = c.fetchall()

        # Affectations
        c.execute("""SELECT a.*, u.nom, u.prenom FROM affectations a
                     JOIN utilisateurs u ON a.utilisateur_id = u.id
                     WHERE a.tache_id = ?""", (tid,))
        affectations = c.fetchall()

        # Timesheets
        c.execute("""SELECT ft.*, u.nom, u.prenom FROM feuilles_temps ft
                     JOIN utilisateurs u ON ft.utilisateur_id = u.id
                     WHERE ft.tache_id = ? ORDER BY ft.date_jour DESC""", (tid,))
        timesheets = c.fetchall()
        conn.close()

        statut_badge = 'badge-info'
        if t['statut'] == 'En cours': statut_badge = 'badge-warning'
        elif t['statut'] == 'Terminée': statut_badge = 'badge-success'
        elif t['statut'] in ['En retard', 'Bloquée']: statut_badge = 'badge-danger'

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-tasks"></i> {t['code']} — {t['nom'][:50]}</h2>
          <div style="display:flex;gap:10px">
            <a href="/taches/{tid}/modifier" class="btn btn-warning"><i class="fas fa-edit"></i> Modifier</a>
            <a href="/taches?projet_id={t['projet_id']}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="kpi-grid">
          <div class="kpi-card" style="border-top-color:#2563eb">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#1e3a8a,#2563eb)">
              <i class="fas fa-info-circle"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Statut</div>
              <div class="kpi-value" style="font-size:1.1rem">{t['statut']}</div>
              <div class="kpi-sub">{t['priorite']} · Niveau {t['complexite']}</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#10b981">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#10b981,#22c55e)">
              <i class="fas fa-chart-line"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Avancement</div>
              <div class="kpi-value">{t['avancement_pct'] or 0:.0f}%</div>
              <div class="kpi-sub">{t['effort_consomme']:.0f}h / {t['effort_estime']:.0f}h</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#f59e0b">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#d97706,#f59e0b)">
              <i class="fas fa-money-bill-wave"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Coût</div>
              <div class="kpi-value">{t['cout_reel']/1e6:.1f}M</div>
              <div class="kpi-sub">Prévu : {t['cout_prevu']/1e6:.1f}M FCFA</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#dc2626">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#dc2626,#ef4444)">
              <i class="fas fa-flag"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Criticité</div>
              <div class="kpi-value" style="font-size:1.1rem">{'⚠️ Chemin critique' if t['chemin_critique'] else 'Normal'}</div>
              <div class="kpi-sub">{t['wbs_code'] or ''}</div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-edit"></i> Mise à jour rapide</h3></div>
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Avancement (%)</label><input type="number" name="avancement_pct" step="1" min="0" max="100" value="{t['avancement_pct'] or 0}"></div>
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  {''.join(f'<option value="{s}" {"selected" if t["statut"]==s else ""}>{s}</option>' for s in ["À faire", "En cours", "En revue", "Terminée", "Bloquée", "En retard"])}
                </select>
              </div>
              <div class="form-group"><label>Effort consommé (h)</label><input type="number" name="effort_consomme" step="0.5" value="{t['effort_consomme']:.1f}"></div>
              <div class="form-group"><label>Coût réel (FCFA)</label><input type="number" name="cout_reel" step="100" value="{t['cout_reel']:.0f}"></div>
            </div>
            <div style="margin-top:15px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
            </div>
          </form>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Détails</h3></div>
          <div class="form-grid">
            <div><strong>Projet :</strong> {t['projet_code']} - {t['projet_nom'][:40]}</div>
            <div><strong>Responsable :</strong> {t['resp_prenom'] or '?'} {t['resp_nom'] or ''}</div>
            <div><strong>Type :</strong> {t['type_tache']}</div>
            <div><strong>WBS :</strong> {t['wbs_code'] or '-'} (niveau {t['wbs_niveau']})</div>
            <div><strong>Date début prévue :</strong> {t['date_debut_prevue'] or '-'}</div>
            <div><strong>Date fin prévue :</strong> {t['date_fin_prevue'] or '-'}</div>
            <div><strong>Date début réelle :</strong> {t['date_debut_reelle'] or '-'}</div>
            <div><strong>Date fin réelle :</strong> {t['date_fin_reelle'] or '-'}</div>
            <div><strong>Effort estimé :</strong> {t['effort_estime']:.1f}h</div>
            <div><strong>Effort consommé :</strong> {t['effort_consomme']:.1f}h</div>
            <div><strong>Story points :</strong> {t['story_points']}</div>
            <div><strong>Méthode agile :</strong> {t['methode_agile'] or '-'}</div>
          </div>
          {('<p style="margin-top:15px;padding:12px;background:#f0f9ff;border-radius:10px"><strong>Description :</strong><br>' + t['description'] + '</p>') if t['description'] else ''}
        </div>
        """

        if deps:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-project-diagram"></i> Dépendances</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Source</th><th>→</th><th>Cible</th><th>Type</th><th>Décalage</th></tr></thead>
                  <tbody>
            """
            for d in deps:
                content += f"""
                <tr>
                  <td><strong>{d['src_code']}</strong> {d['src_nom'][:30]}</td>
                  <td>→</td>
                  <td><strong>{d['cible_code']}</strong> {d['cible_nom'][:30]}</td>
                  <td><span class="badge badge-info">{d['type_dependance']}</span></td>
                  <td>{d['decalage_jours']} jours</td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        if affectations:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-users"></i> Affectations</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Membre</th><th>Charge</th><th>Allocation</th><th>Taux horaire</th><th>Coût prévu</th></tr></thead>
                  <tbody>
            """
            for a in affectations:
                content += f"""
                <tr>
                  <td><strong>{a['prenom']} {a['nom']}</strong></td>
                  <td>{a['charge_heures']:.0f}h</td>
                  <td>{a['taux_allocation']}%</td>
                  <td>{a['taux_horaire']:,.0f} FCFA</td>
                  <td>{a['cout_prevu']:,.0f} FCFA</td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        if timesheets:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-clock"></i> Feuilles de temps</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Date</th><th>Membre</th><th>Heures</th><th>Description</th><th>Statut</th></tr></thead>
                  <tbody>
            """
            for ft in timesheets:
                badge = 'badge-success' if ft['statut'] == 'Validé' else 'badge-warning'
                content += f"""
                <tr>
                  <td>{ft['date_jour']}</td>
                  <td>{ft['prenom']} {ft['nom']}</td>
                  <td><strong>{ft['heures']:.1f}h</strong></td>
                  <td>{ft['description'] or '-'}</td>
                  <td><span class="badge {badge}">{ft['statut']}</span></td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        return render_page(content, active='taches', page_title=t['nom'][:50])

    @app.route('/taches/<int:tid>/modifier', methods=['GET', 'POST'])
    @chef_required
    def tache_modifier(tid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE taches SET
                    nom=?, description=?, projet_id=?, phase_id=?, responsable_id=?,
                    type_tache=?, wbs_code=?, priorite=?, complexite=?,
                    date_debut_prevue=?, date_fin_prevue=?, effort_estime=?, cout_prevu=?,
                    avancement_pct=?, statut=?, chemin_critique=?, story_points=?, notes=?
                    WHERE id=?""",
                    (request.form['nom'], request.form.get('description', ''),
                     int(request.form['projet_id']),
                     int(request.form['phase_id']) if request.form.get('phase_id') else None,
                     int(request.form['responsable_id']) if request.form.get('responsable_id') else None,
                     request.form.get('type_tache', 'Tâche'),
                     request.form.get('wbs_code', ''),
                     request.form.get('priorite', 'Normale'),
                     int(request.form.get('complexite') or 1),
                     request.form.get('date_debut_prevue') or None,
                     request.form.get('date_fin_prevue') or None,
                     float(request.form.get('effort_estime') or 0),
                     float(request.form.get('cout_prevu') or 0),
                     float(request.form.get('avancement_pct') or 0),
                     request.form.get('statut', 'À faire'),
                     1 if request.form.get('chemin_critique') else 0,
                     int(request.form.get('story_points') or 0),
                     request.form.get('notes', ''),
                     tid))
                conn.commit()
                conn.close()
                flash("✅ Tâche mise à jour", "success")
                return redirect(f'/taches/{tid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM taches WHERE id=?", (tid,))
        t = c.fetchone()
        c.execute("SELECT id, code, nom FROM projets WHERE actif=1 ORDER BY nom")
        projets = c.fetchall()
        c.execute("SELECT id, nom, prenom FROM utilisateurs WHERE actif=1 ORDER BY nom")
        users = c.fetchall()
        conn.close()

        projets_opts = "".join(f'<option value="{p["id"]}" {"selected" if p["id"]==t["projet_id"] else ""}>{p["code"]} - {p["nom"][:40]}</option>' for p in projets)
        users_opts = "".join(f'<option value="{u["id"]}" {"selected" if u["id"]==t["responsable_id"] else ""}>{u["prenom"]} {u["nom"]}</option>' for u in users)
        statuts = ['À faire', 'En cours', 'En revue', 'Terminée', 'Bloquée', 'En retard']
        types = ['Tâche', 'Jalon', 'Lot de travail', 'Livrable', 'User Story']

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-edit"></i> Modifier {t['code']}</h2>
          <a href="/taches/{tid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group form-full"><label>Nom *</label><input type="text" name="nom" value="{t['nom']}" required></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="2">{t['description'] or ''}</textarea></div>
              <div class="form-group"><label>Projet *</label><select name="projet_id" required>{projets_opts}</select></div>
              <div class="form-group"><label>Responsable</label><select name="responsable_id"><option value="">--</option>{users_opts}</select></div>
              <div class="form-group"><label>Type</label>
                <select name="type_tache">
                  {''.join(f'<option value="{ty}" {"selected" if t["type_tache"]==ty else ""}>{ty}</option>' for ty in types)}
                </select>
              </div>
              <div class="form-group"><label>WBS Code</label><input type="text" name="wbs_code" value="{t['wbs_code'] or ''}"></div>
              <div class="form-group"><label>Priorité</label>
                <select name="priorite">
                  {''.join(f'<option value="{pr}" {"selected" if t["priorite"]==pr else ""}>{pr}</option>' for pr in ["Basse", "Normale", "Haute", "Critique"])}
                </select>
              </div>
              <div class="form-group"><label>Complexité (1-5)</label><input type="number" name="complexite" min="1" max="5" value="{t['complexite']}"></div>
              <div class="form-group"><label>Date début</label><input type="date" name="date_debut_prevue" value="{t['date_debut_prevue'] or ''}"></div>
              <div class="form-group"><label>Date fin</label><input type="date" name="date_fin_prevue" value="{t['date_fin_prevue'] or ''}"></div>
              <div class="form-group"><label>Effort estimé (h)</label><input type="number" name="effort_estime" step="0.5" value="{t['effort_estime']:.1f}"></div>
              <div class="form-group"><label>Coût prévu (FCFA)</label><input type="number" name="cout_prevu" step="100" value="{t['cout_prevu']:.0f}"></div>
              <div class="form-group"><label>Avancement (%)</label><input type="number" name="avancement_pct" min="0" max="100" value="{t['avancement_pct'] or 0}"></div>
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  {''.join(f'<option value="{s}" {"selected" if t["statut"]==s else ""}>{s}</option>' for s in statuts)}
                </select>
              </div>
              <div class="form-group"><label>Story Points</label><input type="number" name="story_points" value="{t['story_points']}"></div>
              <div class="form-group" style="display:flex;align-items:center;gap:8px;margin-top:30px">
                <input type="checkbox" name="chemin_critique" style="width:auto" {"checked" if t['chemin_critique'] else ""}>
                <label style="margin:0">Chemin critique</label>
              </div>
              <div class="form-group form-full"><label>Notes</label><textarea name="notes" rows="2">{t['notes'] or ''}</textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/taches/{tid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='taches', page_title='Modifier tâche')

    print("[PROJETS_LOGIC] ✅ Routes tâches enregistrées")

    # ==================== RISQUES ====================
    @app.route('/risques')
    @chef_required
    def risques_liste():
        conn = get_db()
        c = conn.cursor()

        projet_filter = request.args.get('projet_id', '')
        statut_filter = request.args.get('statut', '')

        query = """SELECT r.*, p.nom as projet_nom, p.code as projet_code,
                          u.nom as resp_nom, u.prenom as resp_prenom
                   FROM risques r
                   JOIN projets p ON r.projet_id = p.id
                   LEFT JOIN utilisateurs u ON r.responsable_id = u.id
                   WHERE 1=1"""
        params = []

        if projet_filter:
            query += " AND r.projet_id = ?"
            params.append(int(projet_filter))
        if statut_filter:
            query += " AND r.statut = ?"
            params.append(statut_filter)

        query += """ ORDER BY CASE r.niveau_risque
                     WHEN 'Critique' THEN 1 WHEN 'Élevé' THEN 2
                     WHEN 'Moyen' THEN 3 ELSE 4 END, r.criticite DESC"""
        c.execute(query, params)
        rows = c.fetchall()

        # Filtres
        c.execute("SELECT id, code, nom FROM projets WHERE actif=1 ORDER BY nom")
        projets = c.fetchall()

        # Stats
        c.execute("SELECT COUNT(*) FROM risques WHERE statut='Ouvert'")
        ouverts = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM risques WHERE niveau_risque='Critique' AND statut='Ouvert'")
        critiques = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM risques WHERE niveau_risque='Élevé' AND statut='Ouvert'")
        eleves = c.fetchone()[0]
        conn.close()

        projets_opts = "".join(f'<option value="{p["id"]}" {"selected" if projet_filter == str(p["id"]) else ""}>{p["code"]}</option>' for p in projets)
        statuts = ['Ouvert', 'En cours de traitement', 'Atténué', 'Clos', 'Survenu']
        statuts_opts = "".join(f'<option value="{s}" {"selected" if statut_filter == s else ""}>{s}</option>' for s in statuts)

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-exclamation-triangle"></i> Registre des Risques</h2>
            <div class="page-subtitle">{len(rows)} risque(s)</div>
          </div>
          <a href="/risques/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau risque</a>
        </div>

        <div class="stats">
          <div class="stat-card amber">
            <i class="fas fa-list stat-icon"></i>
            <div class="stat-value">{ouverts}</div>
            <div class="stat-label">Ouverts</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-fire stat-icon"></i>
            <div class="stat-value">{critiques}</div>
            <div class="stat-label">Critiques</div>
          </div>
          <div class="stat-card">
            <i class="fas fa-exclamation stat-icon"></i>
            <div class="stat-value">{eleves}</div>
            <div class="stat-label">Élevés</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Registre</h3>
            <form method="GET" style="display:flex;gap:8px">
              <select name="projet_id" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous projets</option>
                {projets_opts}
              </select>
              <select name="statut" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous statuts</option>
                {statuts_opts}
              </select>
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Code</th><th>Risque</th><th>Projet</th>
                  <th>P × I</th><th>Criticité</th><th>Niveau</th>
                  <th>Responsable</th><th>Statut</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
        """
        for r in rows:
            color = '#dc2626' if r['niveau_risque'] == 'Critique' else ('#f59e0b' if r['niveau_risque'] == 'Élevé' else ('#0891b2' if r['niveau_risque'] == 'Moyen' else '#10b981'))
            statut_badge = 'badge-danger' if r['statut'] == 'Ouvert' else ('badge-warning' if r['statut'] == 'En cours de traitement' else 'badge-success')

            content += f"""
            <tr>
              <td><strong>{r['code']}</strong></td>
              <td>
                <div style="font-weight:700">{r['titre'][:45]}</div>
                <small style="color:#94a3b8">{r['categorie'] or ''}</small>
              </td>
              <td><small>{r['projet_code']}<br>{r['projet_nom'][:25]}</small></td>
              <td><strong>{r['probabilite']} × {r['impact']} = {r['criticite']}</strong></td>
              <td>{r['criticite']}</td>
              <td><span class="badge" style="background:{color}20;color:{color}">{r['niveau_risque']}</span></td>
              <td>{r['resp_prenom'] or '?'} {r['resp_nom'] or ''}</td>
              <td><span class="badge {statut_badge}">{r['statut']}</span></td>
              <td>
                <a href="/risques/{r['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="9" class="empty"><i class="fas fa-check-circle" style="color:#10b981"></i><br>Aucun risque 🎉</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='risques', page_title='Risques')

    @app.route('/risques/nouveau', methods=['GET', 'POST'])
    @chef_required
    def risque_nouveau():
        conn = get_db()
        c = conn.cursor()
        projet_id_pre = request.args.get('projet_id', '')

        if request.method == 'POST':
            try:
                code = gen_code('RSK', 'risques')
                prob = int(request.form.get('probabilite') or 1)
                impact = int(request.form.get('impact') or 1)
                criticite = prob * impact

                if criticite >= 15:
                    niveau = 'Critique'
                elif criticite >= 10:
                    niveau = 'Élevé'
                elif criticite >= 5:
                    niveau = 'Moyen'
                else:
                    niveau = 'Faible'

                c.execute("""INSERT INTO risques
                    (code, projet_id, titre, description, categorie, type_risque,
                     probabilite, impact, criticite, niveau_risque,
                     date_identification, identifie_par, responsable_id, strategie,
                     plan_mitigation, plan_contigence, cout_mitigation, date_echeance, statut, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (code, int(request.form['projet_id']),
                     request.form['titre'], request.form.get('description', ''),
                     request.form.get('categorie', ''),
                     request.form.get('type_risque', 'Menace'),
                     prob, impact, criticite, niveau,
                     datetime.now().isoformat(),
                     current_user.id if current_user else None,
                     int(request.form['responsable_id']) if request.form.get('responsable_id') else None,
                     request.form.get('strategie', 'Réduire'),
                     request.form.get('plan_mitigation', ''),
                     request.form.get('plan_contigence', ''),
                     float(request.form.get('cout_mitigation') or 0),
                     request.form.get('date_echeance') or None,
                     'Ouvert',
                     request.form.get('notes', '')))
                conn.commit()
                conn.close()

                if current_user:
                    log_action(current_user.id, 'CREATE_RISQUE', code)

                flash(f"✅ Risque {code} créé ({niveau})", "success")
                return redirect(f'/risques?projet_id={request.form["projet_id"]}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, code, nom FROM projets WHERE actif=1 ORDER BY nom")
        projets = c.fetchall()
        c.execute("SELECT id, nom, prenom FROM utilisateurs WHERE actif=1 ORDER BY nom")
        users = c.fetchall()
        conn.close()

        projets_opts = "".join(f'<option value="{p["id"]}" {"selected" if str(p["id"])==projet_id_pre else ""}>{p["code"]} - {p["nom"][:40]}</option>' for p in projets)
        users_opts = "".join(f'<option value="{u["id"]}">{u["prenom"]} {u["nom"]}</option>' for u in users)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-exclamation-triangle"></i> Nouveau Risque</h2>
          <a href="/risques" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <h3 style="margin-bottom:20px;color:#1e3a8a"><i class="fas fa-info-circle"></i> Identification</h3>
            <div class="form-grid">
              <div class="form-group form-full"><label>Titre du risque *</label><input type="text" name="titre" required></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="3"></textarea></div>
              <div class="form-group"><label>Projet *</label><select name="projet_id" required><option value="">--</option>{projets_opts}</select></div>
              <div class="form-group"><label>Catégorie</label>
                <select name="categorie">
                  <option value="">--</option>
                  <option>Technique</option><option>Financier</option>
                  <option>Réglementaire</option><option>Social</option>
                  <option>Naturel</option><option>Approvisionnement</option>
                  <option>Ressources humaines</option><option>Externe</option>
                </select>
              </div>
              <div class="form-group"><label>Type</label>
                <select name="type_risque">
                  <option value="Menace">Menace</option>
                  <option value="Opportunité">Opportunité</option>
                </select>
              </div>
              <div class="form-group"><label>Responsable</label><select name="responsable_id"><option value="">--</option>{users_opts}</select></div>
            </div>

            <h3 style="margin:25px 0 20px;color:#1e3a8a"><i class="fas fa-chart-line"></i> Analyse probabilité × impact</h3>
            <div class="form-grid">
              <div class="form-group"><label>Probabilité (1-5)</label>
                <select name="probabilite" required>
                  <option value="1">1 - Très faible</option>
                  <option value="2">2 - Faible</option>
                  <option value="3">3 - Moyenne</option>
                  <option value="4">4 - Élevée</option>
                  <option value="5">5 - Très élevée</option>
                </select>
              </div>
              <div class="form-group"><label>Impact (1-5)</label>
                <select name="impact" required>
                  <option value="1">1 - Très faible</option>
                  <option value="2">2 - Faible</option>
                  <option value="3">3 - Moyen</option>
                  <option value="4">4 - Élevé</option>
                  <option value="5">5 - Très élevé</option>
                </select>
              </div>
            </div>

            <h3 style="margin:25px 0 20px;color:#1e3a8a"><i class="fas fa-shield-halved"></i> Réponse au risque</h3>
            <div class="form-grid">
              <div class="form-group"><label>Stratégie</label>
                <select name="strategie">
                  <option value="Éviter">Éviter</option>
                  <option value="Réduire" selected>Réduire</option>
                  <option value="Transférer">Transférer</option>
                  <option value="Accepter">Accepter</option>
                  <option value="Exploiter">Exploiter (opportunité)</option>
                </select>
              </div>
              <div class="form-group"><label>Coût mitigation (FCFA)</label><input type="number" name="cout_mitigation" step="1000" value="0"></div>
              <div class="form-group form-full"><label>Plan de mitigation</label><textarea name="plan_mitigation" rows="3"></textarea></div>
              <div class="form-group form-full"><label>Plan de contingence</label><textarea name="plan_contigence" rows="3"></textarea></div>
              <div class="form-group"><label>Date échéance</label><input type="date" name="date_echeance"></div>
            </div>

            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Créer le risque</button>
              <a href="/risques" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='risques', page_title='Nouveau risque')

    @app.route('/risques/<int:rid>')
    @chef_required
    def risque_detail(rid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT r.*, p.nom as projet_nom, p.code as projet_code,
                            u.nom as resp_nom, u.prenom as resp_prenom
                     FROM risques r
                     JOIN projets p ON r.projet_id = p.id
                     LEFT JOIN utilisateurs u ON r.responsable_id = u.id
                     WHERE r.id=?""", (rid,))
        r = c.fetchone()
        if not r:
            conn.close()
            flash("Risque introuvable", "danger")
            return redirect('/risques')

        # Actions liées
        c.execute("SELECT * FROM actions WHERE risque_id=? ORDER BY date_echeance", (rid,))
        actions = c.fetchall()
        conn.close()

        color = '#dc2626' if r['niveau_risque'] == 'Critique' else ('#f59e0b' if r['niveau_risque'] == 'Élevé' else '#0891b2')

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-exclamation-triangle"></i> {r['code']} — {r['titre'][:60]}</h2>
          <a href="/risques" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>

        <div class="kpi-grid">
          <div class="kpi-card" style="border-top-color:{color}">
            <div class="kpi-icon" style="background:{color}">
              <i class="fas fa-fire"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Niveau</div>
              <div class="kpi-value">{r['niveau_risque']}</div>
              <div class="kpi-sub">Criticité {r['criticite']}</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#2563eb">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#1e3a8a,#2563eb)">
              <i class="fas fa-calculator"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">P × I</div>
              <div class="kpi-value">{r['probabilite']} × {r['impact']}</div>
              <div class="kpi-sub">= {r['criticite']}</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#10b981">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#10b981,#22c55e)">
              <i class="fas fa-shield-halved"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Stratégie</div>
              <div class="kpi-value" style="font-size:1.2rem">{r['strategie']}</div>
              <div class="kpi-sub">Coût mitig. : {r['cout_mitigation']:,.0f} FCFA</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#f59e0b">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#d97706,#f59e0b)">
              <i class="fas fa-clock"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Statut</div>
              <div class="kpi-value" style="font-size:1.1rem">{r['statut']}</div>
              <div class="kpi-sub">Échéance : {r['date_echeance'] or '-'}</div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Détails</h3></div>
          <div class="form-grid">
            <div><strong>Projet :</strong> {r['projet_code']} - {r['projet_nom'][:40]}</div>
            <div><strong>Catégorie :</strong> {r['categorie'] or '-'}</div>
            <div><strong>Type :</strong> {r['type_risque']}</div>
            <div><strong>Responsable :</strong> {r['resp_prenom'] or '?'} {r['resp_nom'] or ''}</div>
            <div><strong>Date identification :</strong> {r['date_identification'][:10]}</div>
            <div><strong>Échéance :</strong> {r['date_echeance'] or '-'}</div>
          </div>
          {('<p style="margin-top:15px;padding:12px;background:#f0f9ff;border-radius:10px"><strong>Description :</strong><br>' + r['description'] + '</p>') if r['description'] else ''}
          {('<p style="margin-top:10px;padding:12px;background:#dcfce7;border-radius:10px;border-left:4px solid #10b981"><strong>✅ Plan de mitigation :</strong><br>' + r['plan_mitigation'] + '</p>') if r['plan_mitigation'] else ''}
          {('<p style="margin-top:10px;padding:12px;background:#fef3c7;border-radius:10px;border-left:4px solid #f59e0b"><strong>⚠️ Plan de contingence :</strong><br>' + r['plan_contigence'] + '</p>') if r['plan_contigence'] else ''}
        </div>
        """

        if actions:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-tasks"></i> Actions liées</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Code</th><th>Action</th><th>Échéance</th><th>Priorité</th><th>Statut</th><th>Avancement</th></tr></thead>
                  <tbody>
            """
            for a in actions:
                badge = 'badge-success' if a['statut'] == 'Terminée' else ('badge-warning' if a['statut'] == 'En cours' else 'badge-info')
                content += f"""
                <tr>
                  <td><strong>{a['code']}</strong></td>
                  <td>{a['titre'][:50]}</td>
                  <td>{a['date_echeance'] or '-'}</td>
                  <td>{a['priorite']}</td>
                  <td><span class="badge {badge}">{a['statut']}</span></td>
                  <td>{a['avancement_pct']:.0f}%</td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        return render_page(content, active='risques', page_title=r['titre'][:50])

    print("[PROJETS_LOGIC] ✅ Routes risques enregistrées")

    # ==================== EVM ====================
    @app.route('/evm')
    @directeur_required
    def evm_dashboard():
        conn = get_db()
        c = conn.cursor()

        projet_filter = request.args.get('projet_id', '')

        # Tous les projets
        c.execute("SELECT id, code, nom, budget_prevu FROM projets WHERE actif=1 ORDER BY nom")
        projets = c.fetchall()

        # Mesures EVM
        if projet_filter:
            c.execute("""SELECT e.*, p.nom as projet_nom, p.code as projet_code
                         FROM evm e JOIN projets p ON e.projet_id = p.id
                         WHERE e.projet_id = ?
                         ORDER BY e.date_mesure DESC LIMIT 50""", (int(projet_filter),))
        else:
            c.execute("""SELECT e.*, p.nom as projet_nom, p.code as projet_code
                         FROM evm e JOIN projets p ON e.projet_id = p.id
                         ORDER BY e.date_mesure DESC LIMIT 50""")
        mesures = c.fetchall()

        # Dernières mesures par projet
        c.execute("""SELECT e.*, p.nom as projet_nom, p.code as projet_code
                     FROM evm e
                     JOIN projets p ON e.projet_id = p.id
                     WHERE e.id IN (
                        SELECT MAX(id) FROM evm GROUP BY projet_id
                     )
                     ORDER BY e.spi ASC""")
        derniers = c.fetchall()
        conn.close()

        projets_opts = "".join(f'<option value="{p["id"]}" {"selected" if projet_filter == str(p["id"]) else ""}>{p["code"]} - {p["nom"][:40]}</option>' for p in projets)

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-chart-line"></i> EVM — Earned Value Management</h2>
            <div class="page-subtitle">Analyse de la performance projets (PMI/PMBOK)</div>
          </div>
          <form method="GET">
            <select name="projet_id" onchange="this.form.submit()" style="padding:10px 15px;border:2px solid #f1f5f9;border-radius:10px;font-weight:600">
              <option value="">Tous les projets</option>
              {projets_opts}
            </select>
          </form>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-chart-bar"></i> Dernières mesures par projet</h3></div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Projet</th><th>Date</th>
                  <th>PV</th><th>EV</th><th>AC</th>
                  <th>SPI</th><th>CPI</th>
                  <th>EAC</th><th>VAC</th><th>Performance</th>
                </tr>
              </thead>
              <tbody>
        """
        for e in derniers:
            spi_class = 'evm-good' if e['spi'] >= 0.95 else ('evm-warning' if e['spi'] >= 0.85 else 'evm-bad')
            cpi_class = 'evm-good' if e['cpi'] >= 0.95 else ('evm-warning' if e['cpi'] >= 0.85 else 'evm-bad')

            content += f"""
            <tr>
              <td><strong>{e['projet_code']}</strong><br><small>{e['projet_nom'][:30]}</small></td>
              <td>{e['date_mesure'][:10]}</td>
              <td>{e['pv']/1e6:.1f}M</td>
              <td>{e['ev']/1e6:.1f}M</td>
              <td>{e['ac']/1e6:.1f}M</td>
              <td><span class="evm-badge {spi_class}">{e['spi']:.2f}</span></td>
              <td><span class="evm-badge {cpi_class}">{e['cpi']:.2f}</span></td>
              <td>{e['eac']/1e9:.2f}B</td>
              <td style="color:{'#dc2626' if e['vac'] < 0 else '#10b981'}"><strong>{e['vac']/1e6:.1f}M</strong></td>
              <td>
                {'🟢' if e['spi'] >= 0.95 and e['cpi'] >= 0.95 else ('🟡' if e['spi'] >= 0.85 and e['cpi'] >= 0.85 else '🔴')}
              </td>
            </tr>
            """
        if not derniers:
            content += '<tr><td colspan="10" class="empty">Aucune mesure EVM</td></tr>'
        content += "</tbody></table></div></div>"

        if mesures:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-history"></i> Historique des mesures</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Date</th><th>Projet</th><th>PV</th><th>EV</th><th>AC</th><th>SPI</th><th>CPI</th><th>EAC</th><th>TCPI</th></tr></thead>
                  <tbody>
            """
            for m in mesures:
                content += f"""
                <tr>
                  <td>{m['date_mesure'][:10]}</td>
                  <td><small>{m['projet_code']}</small></td>
                  <td>{m['pv']/1e6:.1f}M</td>
                  <td>{m['ev']/1e6:.1f}M</td>
                  <td>{m['ac']/1e6:.1f}M</td>
                  <td><strong>{m['spi']:.2f}</strong></td>
                  <td><strong>{m['cpi']:.2f}</strong></td>
                  <td>{m['eac']/1e9:.2f}B</td>
                  <td>{m['tcpi']:.2f}</td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        return render_page(content, active='evm', page_title='EVM')

    @app.route('/evm/recalculer/<int:pid>')
    @directeur_required
    def evm_recalculer(pid):
        try:
            recalculer_evm(pid)
            flash("✅ EVM recalculé", "success")
        except Exception as e:
            flash(f"❌ Erreur : {e}", "danger")
        return redirect(f'/evm?projet_id={pid}')

    print("[PROJETS_LOGIC] ✅ Routes EVM enregistrées")

    # ==================== TIMESHEETS ====================
    @app.route('/feuilles-temps')
    @membre_required
    def feuilles_temps_liste():
        conn = get_db()
        c = conn.cursor()

        user_filter = request.args.get('user_id', '')
        projet_filter = request.args.get('projet_id', '')
        statut_filter = request.args.get('statut', '')

        query = """SELECT ft.*, u.nom, u.prenom, p.code as projet_code, p.nom as projet_nom,
                          t.code as tache_code, t.nom as tache_nom
                   FROM feuilles_temps ft
                   JOIN utilisateurs u ON ft.utilisateur_id = u.id
                   JOIN projets p ON ft.projet_id = p.id
                   LEFT JOIN taches t ON ft.tache_id = t.id
                   WHERE 1=1"""
        params = []

        if user_filter:
            query += " AND ft.utilisateur_id = ?"
            params.append(int(user_filter))
        if projet_filter:
            query += " AND ft.projet_id = ?"
            params.append(int(projet_filter))
        if statut_filter:
            query += " AND ft.statut = ?"
            params.append(statut_filter)

        query += " ORDER BY ft.date_jour DESC LIMIT 200"
        c.execute(query, params)
        rows = c.fetchall()

        # Stats
        c.execute("""SELECT COALESCE(SUM(heures), 0) FROM feuilles_temps
                     WHERE date_jour >= date('now', '-30 days')""")
        heures_30j = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM feuilles_temps WHERE statut='En attente'")
        en_attente = c.fetchone()[0]
        conn.close()

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-clock"></i> Feuilles de temps</h2>
            <div class="page-subtitle">{len(rows)} entrée(s)</div>
          </div>
          <a href="/feuilles-temps/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle entrée</a>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-clock stat-icon"></i>
            <div class="stat-value">{heures_30j:.0f}h</div>
            <div class="stat-label">Heures (30j)</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-hourglass-half stat-icon"></i>
            <div class="stat-value">{en_attente}</div>
            <div class="stat-label">En attente validation</div>
          </div>
        </div>

        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Membre</th><th>Projet</th><th>Tâche</th><th>Heures</th><th>Description</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for ft in rows:
            badge = 'badge-success' if ft['statut'] == 'Validé' else 'badge-warning'
            content += f"""
            <tr>
              <td><strong>{ft['date_jour']}</strong></td>
              <td>{ft['prenom']} {ft['nom']}</td>
              <td><small>{ft['projet_code']}</small></td>
              <td><small>{ft['tache_code'] or '-'}</small></td>
              <td><strong>{ft['heures']:.1f}h</strong></td>
              <td>{ft['description'] or '-'}</td>
              <td><span class="badge {badge}">{ft['statut']}</span></td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="7" class="empty">Aucune feuille de temps</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='feuilles', page_title='Timesheets')

    @app.route('/feuilles-temps/nouvelle', methods=['GET', 'POST'])
    @membre_required
    def feuille_temps_nouvelle():
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                c.execute("""INSERT INTO feuilles_temps
                    (utilisateur_id, projet_id, tache_id, date_jour, heures, description, statut)
                    VALUES (?, ?, ?, ?, ?, ?, 'En attente')""",
                    (int(request.form['utilisateur_id']),
                     int(request.form['projet_id']),
                     int(request.form['tache_id']) if request.form.get('tache_id') else None,
                     request.form['date_jour'],
                     float(request.form['heures']),
                     request.form.get('description', '')))
                conn.commit()
                conn.close()
                flash("✅ Feuille de temps créée", "success")
                return redirect('/feuilles-temps')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom, prenom FROM utilisateurs WHERE actif=1 ORDER BY nom")
        users = c.fetchall()
        c.execute("SELECT id, code, nom FROM projets WHERE actif=1 ORDER BY nom")
        projets = c.fetchall()
        conn.close()

        users_opts = "".join(f'<option value="{u["id"]}" {"selected" if current_user and u["id"]==current_user.id else ""}>{u["prenom"]} {u["nom"]}</option>' for u in users)
        projets_opts = "".join(f'<option value="{p["id"]}">{p["code"]} - {p["nom"][:40]}</option>' for p in projets)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-plus"></i> Nouvelle Feuille de temps</h2>
          <a href="/feuilles-temps" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Membre *</label><select name="utilisateur_id" required>{users_opts}</select></div>
              <div class="form-group"><label>Projet *</label><select name="projet_id" required><option value="">--</option>{projets_opts}</select></div>
              <div class="form-group"><label>Date *</label><input type="date" name="date_jour" value="{datetime.now().date().isoformat()}" required></div>
              <div class="form-group"><label>Heures *</label><input type="number" name="heures" step="0.5" min="0.5" max="24" value="8" required></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="3" placeholder="Travaux réalisés..."></textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/feuilles-temps" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='feuilles', page_title='Nouvelle feuille')

    print("[PROJETS_LOGIC] ✅ Routes timesheets enregistrées")

    # ==================== RAPPORTS ====================
    @app.route('/rapports')
    @directeur_required
    def rapports():
        conn = get_db()
        c = conn.cursor()

        try:
            # KPIs portefeuille
            c.execute("SELECT COUNT(*) FROM projets WHERE actif=1")
            row = c.fetchone()
            total_projets = row[0] if row else 0

            c.execute("SELECT COUNT(*) FROM projets WHERE actif=1 AND statut='En cours'")
            row = c.fetchone()
            projets_en_cours = row[0] if row else 0

            c.execute("SELECT COALESCE(SUM(budget_prevu), 0), COALESCE(SUM(budget_consomme), 0) FROM projets WHERE actif=1")
            row = c.fetchone()
            budget_total = row[0] if row else 0
            budget_consomme = row[1] if row else 0

            c.execute("SELECT COALESCE(AVG(avancement_pct), 0) FROM projets WHERE actif=1")
            row = c.fetchone()
            avancement_moyen = row[0] if row else 0

            # Risques
            c.execute("SELECT COUNT(*) FROM risques WHERE statut='Ouvert'")
            row = c.fetchone()
            risques_ouverts = row[0] if row else 0

            c.execute("SELECT COUNT(*) FROM risques WHERE statut='Ouvert' AND niveau_risque IN ('Critique','Élevé')")
            row = c.fetchone()
            risques_critiques = row[0] if row else 0

            # Projets par type
            c.execute("""SELECT type_projet, COUNT(*) as nb,
                                COALESCE(SUM(budget_prevu), 0) as budget
                         FROM projets WHERE actif=1
                         GROUP BY type_projet ORDER BY budget DESC""")
            par_type = c.fetchall()

            # Projets par santé
            c.execute("""SELECT sante_projet, COUNT(*) as nb FROM projets
                         WHERE actif=1 GROUP BY sante_projet""")
            par_sante = c.fetchall()

            # Clients top
            c.execute("""SELECT cl.nom, COUNT(p.id) as nb_projets,
                                COALESCE(SUM(p.budget_prevu), 0) as budget
                         FROM clients cl
                         LEFT JOIN projets p ON p.client_id = cl.id AND p.actif=1
                         WHERE cl.actif=1
                         GROUP BY cl.id HAVING nb_projets > 0
                         ORDER BY budget DESC LIMIT 10""")
            top_clients = c.fetchall()

            # Budget par programme
            c.execute("""SELECT pr.nom, COALESCE(SUM(p.budget_prevu), 0) as budget
                         FROM programmes pr
                         LEFT JOIN projets p ON p.programme_id = pr.id AND p.actif=1
                         WHERE pr.actif=1
                         GROUP BY pr.id ORDER BY budget DESC""")
            par_programme = c.fetchall()

            conn.close()

            content = f"""
            <div class="page-header">
              <div>
                <h2><i class="fas fa-chart-line"></i> Rapports & Analyses</h2>
                <div class="page-subtitle">Vision stratégique portefeuille UEMOA</div>
              </div>
            </div>

            <div class="kpi-grid">
              <div class="kpi-card" style="border-top-color:#2563eb">
                <div class="kpi-icon" style="background:linear-gradient(135deg,#1e3a8a,#2563eb)">
                  <i class="fas fa-project-diagram"></i>
                </div>
                <div class="kpi-content">
                  <div class="kpi-label">Projets actifs</div>
                  <div class="kpi-value">{total_projets}</div>
                  <div class="kpi-sub">{projets_en_cours} en cours</div>
                </div>
              </div>

              <div class="kpi-card" style="border-top-color:#f59e0b">
                <div class="kpi-icon" style="background:linear-gradient(135deg,#d97706,#f59e0b)">
                  <i class="fas fa-money-bill-wave"></i>
                </div>
                <div class="kpi-content">
                  <div class="kpi-label">Budget total</div>
                  <div class="kpi-value">{budget_total/1e9:.1f}B</div>
                  <div class="kpi-sub">FCFA · Consommé {budget_consomme/1e9:.1f}B</div>
                </div>
              </div>

              <div class="kpi-card" style="border-top-color:#10b981">
                <div class="kpi-icon" style="background:linear-gradient(135deg,#10b981,#22c55e)">
                  <i class="fas fa-chart-line"></i>
                </div>
                <div class="kpi-content">
                  <div class="kpi-label">Avancement moyen</div>
                  <div class="kpi-value">{avancement_moyen:.0f}%</div>
                  <div class="kpi-sub">Global portefeuille</div>
                </div>
              </div>

              <div class="kpi-card" style="border-top-color:#dc2626">
                <div class="kpi-icon" style="background:linear-gradient(135deg,#dc2626,#ef4444)">
                  <i class="fas fa-exclamation-triangle"></i>
                </div>
                <div class="kpi-content">
                  <div class="kpi-label">Risques ouverts</div>
                  <div class="kpi-value">{risques_ouverts}</div>
                  <div class="kpi-sub">{risques_critiques} critiques/élevés</div>
                </div>
              </div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
              <div class="card">
                <div class="card-header"><h3><i class="fas fa-tags"></i> Budget par type de projet</h3></div>
                <div class="table-wrap">
                  <table>
                    <thead><tr><th>Type</th><th>Nb projets</th><th>Budget</th></tr></thead>
                    <tbody>
            """
            for t in par_type:
                content += f"""
                <tr>
                  <td><strong>{t['type_projet']}</strong></td>
                  <td>{t['nb']}</td>
                  <td><strong style="color:#2563eb">{t['budget']/1e9:.1f}B</strong> FCFA</td>
                </tr>
                """
            if not par_type:
                content += '<tr><td colspan="3" class="empty">Aucune donnée</td></tr>'
            content += "</tbody></table></div></div>"

            content += """
              <div class="card">
                <div class="card-header"><h3><i class="fas fa-heartbeat"></i> Santé du portefeuille</h3></div>
            """
            for s in par_sante:
                color = '#10b981' if s['sante_projet'] == 'Vert' else ('#f59e0b' if s['sante_projet'] == 'Jaune' else '#dc2626')
                pct = (s['nb'] / total_projets * 100) if total_projets else 0
                content += f"""
                <div style="margin-bottom:15px">
                  <div style="display:flex;justify-content:space-between;margin-bottom:5px">
                    <span style="font-weight:700">
                      <span class="health-dot" style="background:{color}"></span>{s['sante_projet']}
                    </span>
                    <strong style="color:{color}">{s['nb']} projets ({pct:.0f}%)</strong>
                  </div>
                  <div style="background:#eff6ff;border-radius:6px;height:10px;overflow:hidden">
                    <div style="background:{color};height:100%;width:{pct}%"></div>
                  </div>
                </div>
                """
            content += "</div></div>"

            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-briefcase"></i> Top 10 clients</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>#</th><th>Client</th><th>Projets</th><th>Budget total</th></tr></thead>
                  <tbody>
            """
            for i, cl in enumerate(top_clients, 1):
                medal = '🥇' if i == 1 else ('🥈' if i == 2 else ('🥉' if i == 3 else ''))
                content += f"""
                <tr>
                  <td><strong>{medal} {i}</strong></td>
                  <td>{cl['nom'][:50]}</td>
                  <td>{cl['nb_projets']}</td>
                  <td><strong style="color:#2563eb">{cl['budget']/1e9:.2f}B</strong> FCFA</td>
                </tr>
                """
            content += "</tbody></table></div></div>"

            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-layer-group"></i> Budget par programme</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Programme</th><th>Budget</th><th>Répartition</th></tr></thead>
                  <tbody>
            """
            max_b = max([p['budget'] for p in par_programme], default=1)
            for p in par_programme:
                pct = (p['budget'] / max_b * 100) if max_b else 0
                content += f"""
                <tr>
                  <td><strong>{p['nom'][:50]}</strong></td>
                  <td><strong>{p['budget']/1e9:.2f}B</strong> FCFA</td>
                  <td>
                    <div style="background:#eff6ff;border-radius:6px;height:16px;overflow:hidden;width:200px">
                      <div style="background:linear-gradient(90deg,#1e3a8a,#2563eb);height:100%;width:{pct}%"></div>
                    </div>
                  </td>
                </tr>
                """
            content += "</tbody></table></div></div>"

            return render_page(content, active='rapports', page_title='Rapports')

        except Exception as e:
            import traceback
            traceback.print_exc()
            conn.close()
            flash(f"Erreur rapports : {e}", "danger")
            return redirect('/')

    print("[PROJETS_LOGIC] ✅ Routes rapports enregistrées")
