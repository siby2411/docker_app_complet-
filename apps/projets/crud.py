"""
Module CRUD complet pour Omega Projets
Portefeuilles, Programmes, Projets, Phases, Clients, Fournisseurs, Utilisateurs
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


def register_crud_routes(app, render_page):
    """Enregistre toutes les routes CRUD Projets"""

    # ==================== PROJETS ====================
    @app.route('/projets')
    @membre_required
    def projets_liste():
        conn = get_db()
        c = conn.cursor()

        statut_filter = request.args.get('statut', '')
        type_filter = request.args.get('type', '')
        search = request.args.get('q', '').strip()
        sante_filter = request.args.get('sante', '')

        query = """SELECT p.*, cl.nom as client_nom,
                          u.nom as chef_nom, u.prenom as chef_prenom,
                          pr.nom as prog_nom,
                          (SELECT COUNT(*) FROM taches WHERE projet_id = p.id) as nb_taches,
                          (SELECT COUNT(*) FROM risques WHERE projet_id = p.id AND statut='Ouvert') as nb_risques
                   FROM projets p
                   LEFT JOIN clients cl ON p.client_id = cl.id
                   LEFT JOIN utilisateurs u ON p.chef_projet_id = u.id
                   LEFT JOIN programmes pr ON p.programme_id = pr.id
                   WHERE p.actif=1"""
        params = []

        if statut_filter:
            query += " AND p.statut = ?"
            params.append(statut_filter)
        if type_filter:
            query += " AND p.type_projet = ?"
            params.append(type_filter)
        if sante_filter:
            query += " AND p.sante_projet = ?"
            params.append(sante_filter)
        if search:
            query += " AND (p.code LIKE ? OR p.nom LIKE ?)"
            params.extend([f'%{search}%'] * 2)

        query += " ORDER BY p.priorite DESC, p.date_fin_prevue ASC"
        c.execute(query, params)
        rows = c.fetchall()

        # Stats
        c.execute("SELECT COUNT(*) FROM projets WHERE actif=1")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM projets WHERE actif=1 AND statut='En cours'")
        en_cours = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(budget_prevu), 0), COALESCE(SUM(budget_consomme), 0) FROM projets WHERE actif=1")
        budgets = c.fetchone()
        c.execute("SELECT COUNT(*) FROM projets WHERE actif=1 AND sante_projet='Rouge'")
        rouges = c.fetchone()[0]
        conn.close()

        statuts = ['En préparation', 'En cours', 'En attente', 'Suspendu', 'Terminé', 'Annulé']
        types = ['Construction', 'IT/Télécoms', 'IT/Digital', 'Énergie', 'Conseil', 'Formation', 'Recherche']
        santes = ['Vert', 'Jaune', 'Rouge']

        statuts_opts = "".join(f'<option value="{s}" {"selected" if statut_filter == s else ""}>{s}</option>' for s in statuts)
        types_opts = "".join(f'<option value="{t}" {"selected" if type_filter == t else ""}>{t}</option>' for t in types)
        santes_opts = "".join(f'<option value="{s}" {"selected" if sante_filter == s else ""}>{s}</option>' for s in santes)

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-project-diagram"></i> Projets</h2>
            <div class="page-subtitle">{len(rows)} projet(s) · Budget {budgets[0]/1e9:.1f}B FCFA</div>
          </div>
          <a href="/projets/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau projet</a>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-project-diagram stat-icon"></i>
            <div class="stat-value">{total}</div>
            <div class="stat-label">Total projets</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-play stat-icon"></i>
            <div class="stat-value">{en_cours}</div>
            <div class="stat-label">En cours</div>
          </div>
          <div class="stat-card gold">
            <i class="fas fa-money-bill-wave stat-icon"></i>
            <div class="stat-value">{budgets[0]/1e9:.1f}B</div>
            <div class="stat-label">Budget total</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-exclamation-triangle stat-icon"></i>
            <div class="stat-value">{rouges}</div>
            <div class="stat-label">En rouge</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Liste des projets</h3>
            <form method="GET" style="display:flex;gap:8px;flex-wrap:wrap">
              <input type="text" name="q" value="{search}" placeholder="Code ou nom..." style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px;width:180px">
              <select name="statut" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous statuts</option>
                {statuts_opts}
              </select>
              <select name="type" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous types</option>
                {types_opts}
              </select>
              <select name="sante" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Toutes santés</option>
                {santes_opts}
              </select>
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Code</th><th>Projet</th><th>Client</th><th>Chef</th>
                  <th>Budget</th><th>Avanc.</th><th>Santé</th><th>Tâches</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
        """
        for p in rows:
            health_class = 'health-vert' if p['sante_projet'] == 'Vert' else ('health-jaune' if p['sante_projet'] == 'Jaune' else 'health-rouge')
            badge_statut = 'badge-success' if p['statut'] == 'En cours' else ('badge-info' if p['statut'] == 'En préparation' else ('badge-warning' if p['statut'] == 'En attente' else 'badge-danger'))
            av = p['avancement_pct'] or 0

            content += f"""
            <tr>
              <td><strong>{p['code']}</strong></td>
              <td>
                <div style="font-weight:700">{p['nom'][:45]}</div>
                <small style="color:#94a3b8">{p['type_projet']} · {p['methodologie']} · <span class="badge {badge_statut}" style="font-size:0.6rem;padding:2px 6px">{p['statut']}</span></small>
              </td>
              <td>{p['client_nom'][:20] if p['client_nom'] else '-'}</td>
              <td>{p['chef_prenom'] or '?'} {p['chef_nom'] or ''}</td>
              <td><strong>{p['budget_prevu']/1e6:,.0f}M</strong><br><small style="color:#94a3b8">FCFA</small></td>
              <td>
                <strong style="color:#2563eb">{av:.0f}%</strong>
                <div style="background:#eff6ff;border-radius:6px;height:6px;margin-top:4px;overflow:hidden">
                  <div style="background:#2563eb;height:100%;width:{av}%"></div>
                </div>
              </td>
              <td><span class="health-dot {health_class}"></span>{p['sante_projet']}</td>
              <td>
                <span class="badge badge-primary">{p['nb_taches']}</span>
                {'<br><small style="color:#dc2626">⚠️ ' + str(p['nb_risques']) + ' risq.</small>' if p['nb_risques'] > 0 else ''}
              </td>
              <td>
                <a href="/projets/{p['id']}" class="btn btn-info btn-sm" title="Voir"><i class="fas fa-eye"></i></a>
                <a href="/projets/{p['id']}/modifier" class="btn btn-warning btn-sm" title="Modifier"><i class="fas fa-edit"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="9" class="empty"><i class="fas fa-project-diagram"></i><br>Aucun projet</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='projets', page_title='Projets')

    @app.route('/projets/nouveau', methods=['GET', 'POST'])
    @chef_required
    def projet_nouveau():
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                code = request.form.get('code') or gen_code('PRJ', 'projets')

                date_debut = request.form.get('date_debut_prevue', '')
                date_fin = request.form.get('date_fin_prevue', '')
                duree = 0
                try:
                    if date_debut and date_fin:
                        dd = datetime.fromisoformat(date_debut)
                        df = datetime.fromisoformat(date_fin)
                        duree = (df - dd).days
                except Exception:
                    pass

                c.execute("""INSERT INTO projets
                    (code, nom, description, programme_id, client_id, chef_projet_id, site_id,
                     type_projet, methodologie, priorite, complexite,
                     date_debut_prevue, date_fin_prevue, duree_jours, budget_prevu, devise,
                     marge_cible, statut, sante_projet, objectifs, perimetre, exclusions,
                     hypotheses, contraintes, notes, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (code, request.form['nom'], request.form.get('description', ''),
                     int(request.form['programme_id']) if request.form.get('programme_id') else None,
                     int(request.form['client_id']) if request.form.get('client_id') else None,
                     int(request.form['chef_projet_id']) if request.form.get('chef_projet_id') else None,
                     int(request.form['site_id']) if request.form.get('site_id') else None,
                     request.form.get('type_projet', 'Construction'),
                     request.form.get('methodologie', 'Hybride'),
                     request.form.get('priorite', 'Normale'),
                     request.form.get('complexite', 'Moyenne'),
                     date_debut, date_fin, duree,
                     float(request.form.get('budget_prevu') or 0),
                     request.form.get('devise', 'FCFA'),
                     float(request.form.get('marge_cible') or 0),
                     request.form.get('statut', 'En préparation'),
                     request.form.get('sante_projet', 'Vert'),
                     request.form.get('objectifs', ''),
                     request.form.get('perimetre', ''),
                     request.form.get('exclusions', ''),
                     request.form.get('hypotheses', ''),
                     request.form.get('contraintes', ''),
                     request.form.get('notes', '')))
                conn.commit()
                proj_id = c.lastrowid
                conn.close()

                if current_user:
                    log_action(current_user.id, 'CREATE_PROJET', code)

                flash(f"✅ Projet {code} créé", "success")
                return redirect(f'/projets/{proj_id}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        # Listes pour selects
        c.execute("SELECT id, nom FROM programmes WHERE actif=1 ORDER BY nom")
        programmes = c.fetchall()
        c.execute("SELECT id, nom FROM clients WHERE actif=1 ORDER BY nom")
        clients = c.fetchall()
        c.execute("SELECT id, nom, prenom FROM utilisateurs WHERE actif=1 AND role IN ('chef_projet','directeur','admin') ORDER BY nom")
        chefs = c.fetchall()
        c.execute("SELECT id, nom FROM sites WHERE actif=1 ORDER BY nom")
        sites = c.fetchall()
        conn.close()

        prog_opts = "".join(f'<option value="{p["id"]}">{p["nom"]}</option>' for p in programmes)
        clients_opts = "".join(f'<option value="{cl["id"]}">{cl["nom"]}</option>' for cl in clients)
        chefs_opts = "".join(f'<option value="{ch["id"]}">{ch["prenom"]} {ch["nom"]}</option>' for ch in chefs)
        sites_opts = "".join(f'<option value="{s["id"]}">{s["nom"]}</option>' for s in sites)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-plus"></i> Nouveau Projet</h2>
          <a href="/projets" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <h3 style="margin-bottom:20px;color:#1e3a8a"><i class="fas fa-info-circle"></i> Identification</h3>
            <div class="form-grid">
              <div class="form-group"><label>Code (auto si vide)</label><input type="text" name="code" placeholder="PRJ-0001"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="2"></textarea></div>
              <div class="form-group"><label>Programme</label><select name="programme_id"><option value="">--</option>{prog_opts}</select></div>
              <div class="form-group"><label>Client</label><select name="client_id"><option value="">--</option>{clients_opts}</select></div>
              <div class="form-group"><label>Chef de projet</label><select name="chef_projet_id"><option value="">--</option>{chefs_opts}</select></div>
              <div class="form-group"><label>Site</label><select name="site_id"><option value="">--</option>{sites_opts}</select></div>
            </div>

            <h3 style="margin:25px 0 20px;color:#1e3a8a"><i class="fas fa-cog"></i> Classification</h3>
            <div class="form-grid">
              <div class="form-group"><label>Type de projet</label>
                <select name="type_projet">
                  <option value="Construction">Construction / BTP</option>
                  <option value="IT/Télécoms">IT / Télécoms</option>
                  <option value="IT/Digital">IT / Digital</option>
                  <option value="Énergie">Énergie</option>
                  <option value="Conseil">Conseil</option>
                  <option value="Formation">Formation</option>
                  <option value="Recherche">Recherche</option>
                </select>
              </div>
              <div class="form-group"><label>Méthodologie</label>
                <select name="methodologie">
                  <option value="Waterfall">Waterfall (cascade)</option>
                  <option value="Agile">Agile / Scrum</option>
                  <option value="Hybride" selected>Hybride</option>
                  <option value="PRINCE2">PRINCE2</option>
                </select>
              </div>
              <div class="form-group"><label>Priorité</label>
                <select name="priorite">
                  <option value="Basse">Basse</option>
                  <option value="Normale" selected>Normale</option>
                  <option value="Haute">Haute</option>
                  <option value="Critique">Critique</option>
                </select>
              </div>
              <div class="form-group"><label>Complexité</label>
                <select name="complexite">
                  <option value="Faible">Faible</option>
                  <option value="Moyenne" selected>Moyenne</option>
                  <option value="Élevée">Élevée</option>
                  <option value="Très élevée">Très élevée</option>
                </select>
              </div>
            </div>

            <h3 style="margin:25px 0 20px;color:#1e3a8a"><i class="fas fa-calendar"></i> Planning & Budget</h3>
            <div class="form-grid">
              <div class="form-group"><label>Date début prévue</label><input type="date" name="date_debut_prevue"></div>
              <div class="form-group"><label>Date fin prévue</label><input type="date" name="date_fin_prevue"></div>
              <div class="form-group"><label>Budget prévu (FCFA)</label><input type="number" name="budget_prevu" step="1000" value="0"></div>
              <div class="form-group"><label>Devise</label>
                <select name="devise">
                  <option value="FCFA">FCFA</option>
                  <option value="EUR">EUR</option>
                  <option value="USD">USD</option>
                </select>
              </div>
              <div class="form-group"><label>Marge cible (%)</label><input type="number" name="marge_cible" step="0.1" value="0"></div>
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  <option value="En préparation" selected>En préparation</option>
                  <option value="En cours">En cours</option>
                  <option value="En attente">En attente</option>
                  <option value="Suspendu">Suspendu</option>
                </select>
              </div>
              <div class="form-group"><label>Santé projet</label>
                <select name="sante_projet">
                  <option value="Vert" selected>🟢 Vert</option>
                  <option value="Jaune">🟡 Jaune</option>
                  <option value="Rouge">🔴 Rouge</option>
                </select>
              </div>
            </div>

            <h3 style="margin:25px 0 20px;color:#1e3a8a"><i class="fas fa-scroll"></i> Cadrage PMI</h3>
            <div class="form-grid">
              <div class="form-group form-full"><label>Objectifs</label><textarea name="objectifs" rows="2"></textarea></div>
              <div class="form-group form-full"><label>Périmètre</label><textarea name="perimetre" rows="2"></textarea></div>
              <div class="form-group form-full"><label>Exclusions</label><textarea name="exclusions" rows="2"></textarea></div>
              <div class="form-group form-full"><label>Hypothèses</label><textarea name="hypotheses" rows="2"></textarea></div>
              <div class="form-group form-full"><label>Contraintes</label><textarea name="contraintes" rows="2"></textarea></div>
              <div class="form-group form-full"><label>Notes</label><textarea name="notes" rows="2"></textarea></div>
            </div>

            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Créer le projet</button>
              <a href="/projets" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='projets', page_title='Nouveau projet')

    @app.route('/projets/<int:pid>')
    @membre_required
    def projet_detail(pid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT p.*, cl.nom as client_nom, u.nom as chef_nom, u.prenom as chef_prenom,
                            pr.nom as prog_nom, s.nom as site_nom
                     FROM projets p
                     LEFT JOIN clients cl ON p.client_id = cl.id
                     LEFT JOIN utilisateurs u ON p.chef_projet_id = u.id
                     LEFT JOIN programmes pr ON p.programme_id = pr.id
                     LEFT JOIN sites s ON p.site_id = s.id
                     WHERE p.id=?""", (pid,))
        p = c.fetchone()
        if not p:
            conn.close()
            flash("Projet introuvable", "danger")
            return redirect('/projets')

        # Équipe
        c.execute("""SELECT pe.*, u.nom, u.prenom, u.email, u.specialite
                     FROM projet_equipe pe JOIN utilisateurs u ON pe.utilisateur_id = u.id
                     WHERE pe.projet_id = ? AND pe.actif=1 ORDER BY pe.role_projet""", (pid,))
        equipe = c.fetchall()

        # Phases
        c.execute("SELECT * FROM phases WHERE projet_id = ? ORDER BY ordre", (pid,))
        phases = c.fetchall()

        # Tâches récentes
        c.execute("""SELECT t.*, u.nom as resp_nom, u.prenom as resp_prenom
                     FROM taches t
                     LEFT JOIN utilisateurs u ON t.responsable_id = u.id
                     WHERE t.projet_id = ? ORDER BY t.date_debut_prevue LIMIT 15""", (pid,))
        taches = c.fetchall()

        # Risques
        c.execute("SELECT * FROM risques WHERE projet_id = ? AND statut='Ouvert' ORDER BY criticite DESC", (pid,))
        risques = c.fetchall()

        # Jalons
        c.execute("SELECT * FROM jalons WHERE projet_id = ? ORDER BY date_prevue", (pid,))
        jalons = c.fetchall()

        # EVM dernier
        c.execute("SELECT * FROM evm WHERE projet_id = ? ORDER BY date_mesure DESC LIMIT 1", (pid,))
        evm = c.fetchone()

        # Stats
        c.execute("""SELECT COUNT(*) as total,
                     SUM(CASE WHEN statut='Terminée' THEN 1 ELSE 0 END) as terminees,
                     SUM(CASE WHEN statut='En cours' THEN 1 ELSE 0 END) as en_cours
                     FROM taches WHERE projet_id=?""", (pid,))
        taches_stats = c.fetchone()
        conn.close()

        health_class = 'health-vert' if p['sante_projet'] == 'Vert' else ('health-jaune' if p['sante_projet'] == 'Jaune' else 'health-rouge')
        av = p['avancement_pct'] or 0

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-project-diagram"></i> {p['nom']}</h2>
          <div style="display:flex;gap:10px">
            <a href="/taches/nouvelle?projet_id={pid}" class="btn btn-success"><i class="fas fa-tasks"></i> Nouvelle tâche</a>
            <a href="/risques/nouveau?projet_id={pid}" class="btn btn-warning"><i class="fas fa-exclamation-triangle"></i> Risque</a>
            <a href="/projets/{pid}/modifier" class="btn btn-warning"><i class="fas fa-edit"></i> Modifier</a>
            <a href="/projets" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="kpi-grid">
          <div class="kpi-card" style="border-top-color:#2563eb">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#1e3a8a,#2563eb)">
              <i class="fas fa-info-circle"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Statut</div>
              <div class="kpi-value" style="font-size:1.2rem"><span class="health-dot {health_class}"></span>{p['statut']}</div>
              <div class="kpi-sub">Santé : {p['sante_projet']}</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#10b981">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#10b981,#22c55e)">
              <i class="fas fa-chart-line"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Avancement</div>
              <div class="kpi-value">{av:.0f}%</div>
              <div class="kpi-sub">{taches_stats['terminees'] or 0}/{taches_stats['total'] or 0} tâches terminées</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#f59e0b">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#d97706,#f59e0b)">
              <i class="fas fa-money-bill-wave"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Budget</div>
              <div class="kpi-value">{p['budget_prevu']/1e6:,.0f}M</div>
              <div class="kpi-sub">FCFA · Consommé {p['budget_consomme']/1e6:,.0f}M</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#dc2626">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#dc2626,#ef4444)">
              <i class="fas fa-exclamation-triangle"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Risques ouverts</div>
              <div class="kpi-value">{len(risques)}</div>
              <div class="kpi-sub">{sum(1 for r in risques if r['niveau_risque'] in ('Critique', 'Élevé'))} critiques</div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations générales</h3></div>
          <div class="form-grid">
            <div><strong>Code :</strong> {p['code']}</div>
            <div><strong>Type :</strong> {p['type_projet']}</div>
            <div><strong>Méthodologie :</strong> {p['methodologie']}</div>
            <div><strong>Priorité :</strong> {p['priorite']}</div>
            <div><strong>Complexité :</strong> {p['complexite']}</div>
            <div><strong>Client :</strong> {p['client_nom'] or '-'}</div>
            <div><strong>Chef projet :</strong> {p['chef_prenom'] or '?'} {p['chef_nom'] or ''}</div>
            <div><strong>Programme :</strong> {p['prog_nom'] or '-'}</div>
            <div><strong>Site :</strong> {p['site_nom'] or '-'}</div>
            <div><strong>Date début prévue :</strong> {p['date_debut_prevue'] or '-'}</div>
            <div><strong>Date fin prévue :</strong> {p['date_fin_prevue'] or '-'}</div>
            <div><strong>Durée :</strong> {p['duree_jours']} jours</div>
          </div>
          {('<p style="margin-top:15px;padding:12px;background:#f0f9ff;border-radius:10px"><strong>Description :</strong><br>' + p['description'] + '</p>') if p['description'] else ''}
          {('<p style="margin-top:10px;padding:12px;background:#f0f9ff;border-radius:10px"><strong>Objectifs :</strong><br>' + p['objectifs'] + '</p>') if p['objectifs'] else ''}
          {('<p style="margin-top:10px;padding:12px;background:#f0f9ff;border-radius:10px"><strong>Périmètre :</strong><br>' + p['perimetre'] + '</p>') if p['perimetre'] else ''}
        </div>
        """

        if equipe:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-users"></i> Équipe projet</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Nom</th><th>Rôle projet</th><th>Spécialité</th><th>Taux horaire</th><th>Affecté depuis</th></tr></thead>
                  <tbody>
            """
            for e in equipe:
                content += f"""
                <tr>
                  <td><strong>{e['prenom']} {e['nom']}</strong></td>
                  <td><span class="badge badge-primary">{e['role_projet']}</span></td>
                  <td>{e['specialite'] or '-'}</td>
                  <td>{e['taux_horaire']:,.0f} FCFA/h</td>
                  <td>{e['date_affectation']}</td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        if phases:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-layer-group"></i> Phases</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Code</th><th>Phase</th><th>Début</th><th>Fin</th><th>Budget</th><th>Avancement</th><th>Statut</th></tr></thead>
                  <tbody>
            """
            for ph in phases:
                av_ph = ph['avancement_pct'] or 0
                content += f"""
                <tr>
                  <td><strong>{ph['code']}</strong></td>
                  <td>{ph['nom']}</td>
                  <td>{ph['date_debut'] or '-'}</td>
                  <td>{ph['date_fin'] or '-'}</td>
                  <td>{ph['budget_alloue']/1e6:,.0f}M FCFA</td>
                  <td>
                    <strong>{av_ph:.0f}%</strong>
                    <div style="background:#eff6ff;border-radius:6px;height:6px;margin-top:4px;overflow:hidden">
                      <div style="background:#2563eb;height:100%;width:{av_ph}%"></div>
                    </div>
                  </td>
                  <td><span class="badge badge-info">{ph['statut']}</span></td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        if jalons:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-flag-checkered"></i> Jalons</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Code</th><th>Jalon</th><th>Date prévue</th><th>Date réelle</th><th>Statut</th></tr></thead>
                  <tbody>
            """
            for j in jalons:
                badge = 'badge-success' if j['statut'] == 'Atteint' else ('badge-warning' if j['statut'] == 'En cours' else 'badge-info')
                content += f"""
                <tr>
                  <td><strong>{j['code']}</strong></td>
                  <td>{j['nom']}</td>
                  <td>{j['date_prevue']}</td>
                  <td>{j['date_reelle'] or '-'}</td>
                  <td><span class="badge {badge}">{j['statut']}</span></td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        if taches:
            content += """
            <div class="card">
              <div class="card-header">
                <h3><i class="fas fa-tasks"></i> Tâches récentes</h3>
                <a href="/taches?projet_id=""" + str(pid) + """" class="btn btn-primary btn-sm">Voir tout</a>
              </div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Code</th><th>Tâche</th><th>Responsable</th><th>Début</th><th>Fin</th><th>Avanc.</th><th>Statut</th></tr></thead>
                  <tbody>
            """
            for t in taches:
                badge = 'badge-success' if t['statut'] == 'Terminée' else ('badge-warning' if t['statut'] == 'En cours' else 'badge-info')
                av_t = t['avancement_pct'] or 0
                content += f"""
                <tr>
                  <td><strong>{t['code']}</strong></td>
                  <td>{t['nom'][:40]}</td>
                  <td>{t['resp_prenom'] or '?'} {t['resp_nom'] or ''}</td>
                  <td>{t['date_debut_prevue'] or '-'}</td>
                  <td>{t['date_fin_prevue'] or '-'}</td>
                  <td><strong>{av_t:.0f}%</strong></td>
                  <td><span class="badge {badge}">{t['statut']}</span></td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        if risques:
            content += """
            <div class="card" style="border-left:5px solid #dc2626">
              <div class="card-header"><h3 style="color:#991b1b"><i class="fas fa-exclamation-triangle"></i> Risques ouverts</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Code</th><th>Risque</th><th>Prob.</th><th>Impact</th><th>Criticité</th><th>Niveau</th><th>Statut</th></tr></thead>
                  <tbody>
            """
            for r in risques:
                color = '#dc2626' if r['niveau_risque'] == 'Critique' else ('#f59e0b' if r['niveau_risque'] == 'Élevé' else '#10b981')
                content += f"""
                <tr>
                  <td><strong>{r['code']}</strong></td>
                  <td>{r['titre'][:50]}</td>
                  <td>{r['probabilite']}</td>
                  <td>{r['impact']}</td>
                  <td>{r['criticite']}</td>
                  <td><span class="badge" style="background:{color}20;color:{color}">{r['niveau_risque']}</span></td>
                  <td><span class="badge badge-warning">{r['statut']}</span></td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        return render_page(content, active='projets', page_title=p['nom'][:50])

    @app.route('/projets/<int:pid>/modifier', methods=['GET', 'POST'])
    @chef_required
    def projet_modifier(pid):
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                date_debut = request.form.get('date_debut_prevue', '')
                date_fin = request.form.get('date_fin_prevue', '')
                duree = 0
                try:
                    if date_debut and date_fin:
                        dd = datetime.fromisoformat(date_debut)
                        df = datetime.fromisoformat(date_fin)
                        duree = (df - dd).days
                except Exception:
                    pass

                c.execute("""UPDATE projets SET
                    nom=?, description=?, programme_id=?, client_id=?, chef_projet_id=?, site_id=?,
                    type_projet=?, methodologie=?, priorite=?, complexite=?,
                    date_debut_prevue=?, date_fin_prevue=?, duree_jours=?, budget_prevu=?, devise=?,
                    marge_cible=?, avancement_pct=?, statut=?, sante_projet=?,
                    objectifs=?, perimetre=?, exclusions=?, hypotheses=?, contraintes=?, notes=?
                    WHERE id=?""",
                    (request.form['nom'], request.form.get('description', ''),
                     int(request.form['programme_id']) if request.form.get('programme_id') else None,
                     int(request.form['client_id']) if request.form.get('client_id') else None,
                     int(request.form['chef_projet_id']) if request.form.get('chef_projet_id') else None,
                     int(request.form['site_id']) if request.form.get('site_id') else None,
                     request.form.get('type_projet', 'Construction'),
                     request.form.get('methodologie', 'Hybride'),
                     request.form.get('priorite', 'Normale'),
                     request.form.get('complexite', 'Moyenne'),
                     date_debut, date_fin, duree,
                     float(request.form.get('budget_prevu') or 0),
                     request.form.get('devise', 'FCFA'),
                     float(request.form.get('marge_cible') or 0),
                     float(request.form.get('avancement_pct') or 0),
                     request.form.get('statut', 'En préparation'),
                     request.form.get('sante_projet', 'Vert'),
                     request.form.get('objectifs', ''),
                     request.form.get('perimetre', ''),
                     request.form.get('exclusions', ''),
                     request.form.get('hypotheses', ''),
                     request.form.get('contraintes', ''),
                     request.form.get('notes', ''),
                     pid))
                conn.commit()
                conn.close()
                if current_user:
                    log_action(current_user.id, 'UPDATE_PROJET', f'ID {pid}')
                flash("✅ Projet mis à jour", "success")
                return redirect(f'/projets/{pid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM projets WHERE id=?", (pid,))
        p = c.fetchone()
        c.execute("SELECT id, nom FROM programmes WHERE actif=1 ORDER BY nom")
        programmes = c.fetchall()
        c.execute("SELECT id, nom FROM clients WHERE actif=1 ORDER BY nom")
        clients = c.fetchall()
        c.execute("SELECT id, nom, prenom FROM utilisateurs WHERE actif=1 AND role IN ('chef_projet','directeur','admin') ORDER BY nom")
        chefs = c.fetchall()
        c.execute("SELECT id, nom FROM sites WHERE actif=1 ORDER BY nom")
        sites = c.fetchall()
        conn.close()

        prog_opts = "".join(f'<option value="{p2["id"]}" {"selected" if p2["id"]==p["programme_id"] else ""}>{p2["nom"]}</option>' for p2 in programmes)
        clients_opts = "".join(f'<option value="{cl["id"]}" {"selected" if cl["id"]==p["client_id"] else ""}>{cl["nom"]}</option>' for cl in clients)
        chefs_opts = "".join(f'<option value="{ch["id"]}" {"selected" if ch["id"]==p["chef_projet_id"] else ""}>{ch["prenom"]} {ch["nom"]}</option>' for ch in chefs)
        sites_opts = "".join(f'<option value="{s["id"]}" {"selected" if s["id"]==p["site_id"] else ""}>{s["nom"]}</option>' for s in sites)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-edit"></i> Modifier {p['nom'][:50]}</h2>
          <a href="/projets/{pid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code (non modifiable)</label><input type="text" value="{p['code']}" disabled></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{p['nom']}" required></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="2">{p['description'] or ''}</textarea></div>
              <div class="form-group"><label>Programme</label><select name="programme_id"><option value="">--</option>{prog_opts}</select></div>
              <div class="form-group"><label>Client</label><select name="client_id"><option value="">--</option>{clients_opts}</select></div>
              <div class="form-group"><label>Chef projet</label><select name="chef_projet_id"><option value="">--</option>{chefs_opts}</select></div>
              <div class="form-group"><label>Site</label><select name="site_id"><option value="">--</option>{sites_opts}</select></div>
              <div class="form-group"><label>Type</label>
                <select name="type_projet">
                  {''.join(f'<option value="{t}" {"selected" if p["type_projet"]==t else ""}>{t}</option>' for t in ["Construction", "IT/Télécoms", "IT/Digital", "Énergie", "Conseil", "Formation", "Recherche"])}
                </select>
              </div>
              <div class="form-group"><label>Méthodologie</label>
                <select name="methodologie">
                  {''.join(f'<option value="{m}" {"selected" if p["methodologie"]==m else ""}>{m}</option>' for m in ["Waterfall", "Agile", "Hybride", "PRINCE2"])}
                </select>
              </div>
              <div class="form-group"><label>Priorité</label>
                <select name="priorite">
                  {''.join(f'<option value="{pr}" {"selected" if p["priorite"]==pr else ""}>{pr}</option>' for pr in ["Basse", "Normale", "Haute", "Critique"])}
                </select>
              </div>
              <div class="form-group"><label>Complexité</label>
                <select name="complexite">
                  {''.join(f'<option value="{cx}" {"selected" if p["complexite"]==cx else ""}>{cx}</option>' for cx in ["Faible", "Moyenne", "Élevée", "Très élevée"])}
                </select>
              </div>
              <div class="form-group"><label>Date début</label><input type="date" name="date_debut_prevue" value="{p['date_debut_prevue'] or ''}"></div>
              <div class="form-group"><label>Date fin</label><input type="date" name="date_fin_prevue" value="{p['date_fin_prevue'] or ''}"></div>
              <div class="form-group"><label>Budget prévu</label><input type="number" name="budget_prevu" step="1000" value="{p['budget_prevu']}"></div>
              <div class="form-group"><label>Devise</label>
                <select name="devise">
                  {''.join(f'<option value="{d}" {"selected" if p["devise"]==d else ""}>{d}</option>' for d in ["FCFA", "EUR", "USD"])}
                </select>
              </div>
              <div class="form-group"><label>Marge cible (%)</label><input type="number" name="marge_cible" step="0.1" value="{p['marge_cible']}"></div>
              <div class="form-group"><label>Avancement (%)</label><input type="number" name="avancement_pct" step="1" min="0" max="100" value="{p['avancement_pct']}"></div>
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  {''.join(f'<option value="{s}" {"selected" if p["statut"]==s else ""}>{s}</option>' for s in ["En préparation", "En cours", "En attente", "Suspendu", "Terminé", "Annulé"])}
                </select>
              </div>
              <div class="form-group"><label>Santé</label>
                <select name="sante_projet">
                  {''.join(f'<option value="{s}" {"selected" if p["sante_projet"]==s else ""}>{s}</option>' for s in ["Vert", "Jaune", "Rouge"])}
                </select>
              </div>
              <div class="form-group form-full"><label>Objectifs</label><textarea name="objectifs" rows="2">{p['objectifs'] or ''}</textarea></div>
              <div class="form-group form-full"><label>Périmètre</label><textarea name="perimetre" rows="2">{p['perimetre'] or ''}</textarea></div>
              <div class="form-group form-full"><label>Exclusions</label><textarea name="exclusions" rows="2">{p['exclusions'] or ''}</textarea></div>
              <div class="form-group form-full"><label>Hypothèses</label><textarea name="hypotheses" rows="2">{p['hypotheses'] or ''}</textarea></div>
              <div class="form-group form-full"><label>Contraintes</label><textarea name="contraintes" rows="2">{p['contraintes'] or ''}</textarea></div>
              <div class="form-group form-full"><label>Notes</label><textarea name="notes" rows="2">{p['notes'] or ''}</textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/projets/{pid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='projets', page_title='Modifier projet')

    @app.route('/projets/<int:pid>/supprimer')
    @directeur_required
    def projet_supprimer(pid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE projets SET actif=0 WHERE id=?", (pid,))
            conn.commit()
            conn.close()
            if current_user:
                log_action(current_user.id, 'DELETE_PROJET', f'ID {pid}')
            flash("✅ Projet archivé", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/projets')

    print("[CRUD] ✅ Routes projets enregistrées")

    # ==================== CLIENTS ====================
    @app.route('/clients')
    @chef_required
    def clients_liste():
        conn = get_db()
        c = conn.cursor()
        search = request.args.get('q', '').strip()
        query = "SELECT * FROM clients WHERE actif=1"
        params = []
        if search:
            query += " AND (nom LIKE ? OR contact_nom LIKE ? OR telephone LIKE ?)"
            params.extend([f'%{search}%'] * 3)
        query += " ORDER BY nom"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-briefcase"></i> Clients</h2>
            <div class="page-subtitle">{len(rows)} client(s)</div>
          </div>
          <a href="/clients/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau client</a>
        </div>
        <div class="card">
          <div class="card-header">
            <form method="GET" style="display:flex;gap:8px">
              <input type="text" name="q" value="{search}" placeholder="Rechercher..." style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px;width:250px">
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Nom</th><th>Contact</th><th>Téléphone</th><th>Ville</th><th>Secteur</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for cl in rows:
            content += f"""
            <tr>
              <td><strong>{cl['code']}</strong></td>
              <td>{cl['nom']}</td>
              <td>{cl['contact_nom'] or '-'}</td>
              <td>{cl['telephone']}</td>
              <td>{cl['ville'] or '-'}, {cl['pays'] or ''}</td>
              <td><span class="badge badge-info">{cl['secteur'] or '-'}</span></td>
              <td>
                <a href="/clients/{cl['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="7" class="empty">Aucun client</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='clients', page_title='Clients')

    @app.route('/clients/nouveau', methods=['GET', 'POST'])
    @chef_required
    def client_nouveau():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                code = request.form.get('code') or gen_code('CLI', 'clients')
                c.execute("""INSERT INTO clients
                    (code, type_client, nom, contact_nom, telephone, email, adresse, ville, pays,
                     nif, rccm, secteur, conditions_paiement, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (code, request.form.get('type_client', 'Entreprise'),
                     request.form['nom'], request.form.get('contact_nom', ''),
                     request.form['telephone'], request.form.get('email', ''),
                     request.form.get('adresse', ''), request.form.get('ville', ''),
                     request.form.get('pays', 'Sénégal'),
                     request.form.get('nif', ''), request.form.get('rccm', ''),
                     request.form.get('secteur', ''),
                     request.form.get('conditions_paiement', '')))
                conn.commit()
                conn.close()
                flash(f"✅ Client {code} créé", "success")
                return redirect('/clients')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = """
        <div class="page-header">
          <h2><i class="fas fa-briefcase"></i> Nouveau Client</h2>
          <a href="/clients" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code (auto si vide)</label><input type="text" name="code"></div>
              <div class="form-group"><label>Type</label>
                <select name="type_client">
                  <option value="Entreprise">Entreprise</option>
                  <option value="Ministère">Ministère</option>
                  <option value="Banque">Banque</option>
                  <option value="ONG">ONG</option>
                  <option value="Particulier">Particulier</option>
                </select>
              </div>
              <div class="form-group form-full"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group"><label>Contact principal</label><input type="text" name="contact_nom"></div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email"></div>
              <div class="form-group"><label>Adresse</label><input type="text" name="adresse"></div>
              <div class="form-group"><label>Ville</label><input type="text" name="ville" value="Dakar"></div>
              <div class="form-group"><label>Pays</label><input type="text" name="pays" value="Sénégal"></div>
              <div class="form-group"><label>NIF</label><input type="text" name="nif"></div>
              <div class="form-group"><label>RCCM</label><input type="text" name="rccm"></div>
              <div class="form-group"><label>Secteur</label><input type="text" name="secteur"></div>
              <div class="form-group form-full"><label>Conditions de paiement</label><textarea name="conditions_paiement" rows="2"></textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Créer</button>
              <a href="/clients" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='clients', page_title='Nouveau client')

    @app.route('/clients/<int:cid>/modifier', methods=['GET', 'POST'])
    @chef_required
    def client_modifier(cid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE clients SET
                    type_client=?, nom=?, contact_nom=?, telephone=?, email=?,
                    adresse=?, ville=?, pays=?, nif=?, rccm=?, secteur=?, conditions_paiement=?
                    WHERE id=?""",
                    (request.form.get('type_client', 'Entreprise'), request.form['nom'],
                     request.form.get('contact_nom', ''), request.form['telephone'],
                     request.form.get('email', ''), request.form.get('adresse', ''),
                     request.form.get('ville', ''), request.form.get('pays', 'Sénégal'),
                     request.form.get('nif', ''), request.form.get('rccm', ''),
                     request.form.get('secteur', ''), request.form.get('conditions_paiement', ''),
                     cid))
                conn.commit()
                conn.close()
                flash("✅ Client mis à jour", "success")
                return redirect('/clients')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM clients WHERE id=?", (cid,))
        cl = c.fetchone()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-edit"></i> Modifier {cl['nom']}</h2>
          <a href="/clients" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code</label><input type="text" value="{cl['code']}" disabled></div>
              <div class="form-group"><label>Type</label>
                <select name="type_client">
                  {''.join(f'<option value="{t}" {"selected" if cl["type_client"]==t else ""}>{t}</option>' for t in ["Entreprise", "Ministère", "Banque", "ONG", "Particulier"])}
                </select>
              </div>
              <div class="form-group form-full"><label>Nom *</label><input type="text" name="nom" value="{cl['nom']}" required></div>
              <div class="form-group"><label>Contact</label><input type="text" name="contact_nom" value="{cl['contact_nom'] or ''}"></div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" value="{cl['telephone']}" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email" value="{cl['email'] or ''}"></div>
              <div class="form-group"><label>Adresse</label><input type="text" name="adresse" value="{cl['adresse'] or ''}"></div>
              <div class="form-group"><label>Ville</label><input type="text" name="ville" value="{cl['ville'] or ''}"></div>
              <div class="form-group"><label>Pays</label><input type="text" name="pays" value="{cl['pays'] or ''}"></div>
              <div class="form-group"><label>NIF</label><input type="text" name="nif" value="{cl['nif'] or ''}"></div>
              <div class="form-group"><label>RCCM</label><input type="text" name="rccm" value="{cl['rccm'] or ''}"></div>
              <div class="form-group"><label>Secteur</label><input type="text" name="secteur" value="{cl['secteur'] or ''}"></div>
              <div class="form-group form-full"><label>Conditions paiement</label><textarea name="conditions_paiement" rows="2">{cl['conditions_paiement'] or ''}</textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/clients" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='clients', page_title='Modifier client')

    print("[CRUD] ✅ Routes clients enregistrées")

    # ==================== UTILISATEURS ====================
    @app.route('/utilisateurs')
    @admin_required
    def utilisateurs_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM utilisateurs ORDER BY role, nom")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-user-shield"></i> Utilisateurs</h2>
            <div class="page-subtitle">Gestion des accès</div>
          </div>
          <a href="/utilisateurs/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvel utilisateur</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Username</th><th>Nom</th><th>Spécialité</th><th>Taux horaire</th><th>Rôle</th><th>Dernière connexion</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for u in rows:
            role_badge = f'badge-role-{u["role"]}'
            statut_badge = 'badge-success' if u['actif'] else 'badge-danger'
            content += f"""
            <tr>
              <td><strong>{u['username']}</strong></td>
              <td>{u['prenom']} {u['nom']}<br><small style="color:#94a3b8">{u['email'] or ''}</small></td>
              <td>{u['specialite'] or '-'}</td>
              <td>{u['taux_horaire']:,.0f} FCFA/h</td>
              <td><span class="badge {role_badge}">{u['role']}</span></td>
              <td>{u['dernier_login'][:16] if u['dernier_login'] else 'Jamais'}</td>
              <td><span class="badge {statut_badge}">{'Actif' if u['actif'] else 'Inactif'}</span></td>
            </tr>
            """
        content += "</tbody></table></div></div>"
        return render_page(content, active='utilisateurs', page_title='Utilisateurs')

    print("[CRUD] ✅ Routes utilisateurs enregistrées")
