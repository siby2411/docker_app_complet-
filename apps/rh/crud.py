"""
Module CRUD complet pour Omega RH
Employés, Départements, Postes, Contrats, Utilisateurs
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


def gen_code(prefix, table):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"SELECT COUNT(*) FROM {table}")
    n = c.fetchone()[0] + 1
    conn.close()
    return f"{prefix}-{n:04d}"


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


def register_crud_routes(app, render_page):
    """Enregistre toutes les routes CRUD RH"""

    # ==================== EMPLOYÉS ====================
    @app.route('/employes')
    @staff_required
    def employes_liste():
        conn = get_db()
        c = conn.cursor()

        search = request.args.get('q', '').strip()
        dept_filter = request.args.get('departement', '')
        statut_filter = request.args.get('statut', '')
        contrat_filter = request.args.get('contrat', '')

        query = """SELECT e.*, p.intitule as poste_nom, d.nom as dept_nom,
                          s.nom as site_nom
                   FROM employes e
                   LEFT JOIN postes p ON e.poste_id = p.id
                   LEFT JOIN departements d ON e.departement_id = d.id
                   LEFT JOIN sites s ON e.site_id = s.id
                   WHERE e.actif=1"""
        params = []

        if search:
            query += """ AND (e.nom LIKE ? OR e.prenom LIKE ? OR e.matricule LIKE ?
                        OR e.email LIKE ? OR e.telephone LIKE ?)"""
            params.extend([f'%{search}%'] * 5)

        if dept_filter:
            query += " AND e.departement_id = ?"
            params.append(int(dept_filter))

        if statut_filter:
            query += " AND e.statut = ?"
            params.append(statut_filter)

        if contrat_filter:
            query += " AND e.type_contrat = ?"
            params.append(contrat_filter)

        query += " ORDER BY e.nom, e.prenom"
        c.execute(query, params)
        rows = c.fetchall()

        # Listes pour filtres
        c.execute("SELECT id, nom FROM departements WHERE actif=1 ORDER BY nom")
        departements = c.fetchall()
        conn.close()

        depts_opts = "".join(f'<option value="{d["id"]}" {"selected" if dept_filter == str(d["id"]) else ""}>{d["nom"]}</option>' for d in departements)
        statuts = ['Actif', 'Congé', 'Suspendu', 'Démission', 'Retraite', 'Licencié']
        statuts_opts = "".join(f'<option value="{s}" {"selected" if statut_filter == s else ""}>{s}</option>' for s in statuts)
        contrats = ['CDI', 'CDD', 'Stage', 'Intérim', 'Freelance']
        contrats_opts = "".join(f'<option value="{c_}" {"selected" if contrat_filter == c_ else ""}>{c_}</option>' for c_ in contrats)

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-users"></i> Employés</h2>
            <div class="page-subtitle">{len(rows)} employé(s) trouvé(s)</div>
          </div>
          <a href="/employes/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvel employé</a>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Liste du personnel</h3>
            <form method="GET" style="display:flex;gap:8px;flex-wrap:wrap">
              <input type="text" name="q" value="{search}" placeholder="Nom, matricule, tél..." style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px;width:200px">
              <select name="departement" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous départements</option>
                {depts_opts}
              </select>
              <select name="statut" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous statuts</option>
                {statuts_opts}
              </select>
              <select name="contrat" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous contrats</option>
                {contrats_opts}
              </select>
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Matricule</th><th>Nom & Prénom</th><th>Poste</th>
                  <th>Département</th><th>Contrat</th><th>Salaire</th>
                  <th>Statut</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
        """
        for e in rows:
            statut_badge = 'badge-success'
            if e['statut'] == 'Congé': statut_badge = 'badge-info'
            elif e['statut'] == 'Suspendu': statut_badge = 'badge-warning'
            elif e['statut'] in ['Démission', 'Licencié', 'Retraite']: statut_badge = 'badge-danger'

            contrat_badge = 'badge-primary'
            if e['type_contrat'] == 'CDD': contrat_badge = 'badge-warning'
            elif e['type_contrat'] == 'Stage': contrat_badge = 'badge-info'

            salaire_total = e['salaire_base'] + (e['prime_transport'] or 0) + (e['prime_logement'] or 0) + (e['prime_autre'] or 0)

            content += f"""
            <tr>
              <td><strong>{e['matricule']}</strong></td>
              <td>
                <div style="font-weight:700">{e['nom']} {e['prenom']}</div>
                <small style="color:#94a3b8">{e['email'] or e['telephone']}</small>
              </td>
              <td>{e['poste_nom'] or '-'}</td>
              <td>{e['dept_nom'] or '-'}</td>
              <td><span class="badge {contrat_badge}">{e['type_contrat']}</span></td>
              <td><strong style="color:#7c3aed">{salaire_total:,.0f}</strong> FCFA</td>
              <td><span class="badge {statut_badge}">{e['statut']}</span></td>
              <td>
                <a href="/employes/{e['id']}" class="btn btn-info btn-sm" title="Voir"><i class="fas fa-eye"></i></a>
                <a href="/employes/{e['id']}/modifier" class="btn btn-warning btn-sm" title="Modifier"><i class="fas fa-edit"></i></a>
                <a href="/employes/{e['id']}/supprimer" class="btn btn-danger btn-sm" title="Supprimer" onclick="return confirm('Confirmer la suppression ?')"><i class="fas fa-trash"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-users"></i><br>Aucun employé</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='employes', page_title='Employés')

    @app.route('/employes/nouveau', methods=['GET', 'POST'])
    @rh_required
    def employe_nouveau():
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                matricule = request.form.get('matricule') or gen_code('EMP', 'employes')

                c.execute("""INSERT INTO employes
                    (matricule, nom, prenom, date_naissance, lieu_naissance, sexe,
                     situation_matrimoniale, nombre_enfants, nationalite,
                     cni, numero_css, numero_ipres,
                     telephone, telephone_urgence, email, adresse, ville, region,
                     poste_id, departement_id, site_id, manager_id,
                     date_embauche, date_fin_contrat, type_contrat, statut,
                     salaire_base, prime_transport, prime_logement, prime_autre,
                     banque, rib, mode_paiement, notes, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (matricule, request.form['nom'], request.form['prenom'],
                     request.form['date_naissance'], request.form.get('lieu_naissance', ''),
                     request.form['sexe'], request.form.get('situation_matrimoniale', ''),
                     int(request.form.get('nombre_enfants') or 0),
                     request.form.get('nationalite', 'Sénégalaise'),
                     request.form.get('cni', ''), request.form.get('numero_css', ''),
                     request.form.get('numero_ipres', ''),
                     request.form['telephone'], request.form.get('telephone_urgence', ''),
                     request.form.get('email', ''), request.form.get('adresse', ''),
                     request.form.get('ville', ''), request.form.get('region', ''),
                     int(request.form['poste_id']) if request.form.get('poste_id') else None,
                     int(request.form['departement_id']) if request.form.get('departement_id') else None,
                     int(request.form['site_id']) if request.form.get('site_id') else None,
                     int(request.form['manager_id']) if request.form.get('manager_id') else None,
                     request.form['date_embauche'],
                     request.form.get('date_fin_contrat') or None,
                     request.form.get('type_contrat', 'CDI'),
                     request.form.get('statut', 'Actif'),
                     float(request.form.get('salaire_base') or 0),
                     float(request.form.get('prime_transport') or 0),
                     float(request.form.get('prime_logement') or 0),
                     float(request.form.get('prime_autre') or 0),
                     request.form.get('banque', ''), request.form.get('rib', ''),
                     request.form.get('mode_paiement', 'Virement'),
                     request.form.get('notes', '')))
                conn.commit()
                emp_id = c.lastrowid
                conn.close()

                if current_user:
                    log_action(current_user.id, 'CREATE_EMPLOYE', matricule)

                flash(f"✅ Employé {matricule} créé avec succès", "success")
                return redirect(f'/employes/{emp_id}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        # GET
        c.execute("SELECT id, nom FROM departements WHERE actif=1 ORDER BY nom")
        departements = c.fetchall()
        c.execute("SELECT id, intitule, departement_id FROM postes WHERE actif=1 ORDER BY intitule")
        postes = c.fetchall()
        c.execute("SELECT id, nom FROM sites WHERE actif=1 ORDER BY nom")
        sites = c.fetchall()
        c.execute("SELECT id, nom, prenom, matricule FROM employes WHERE actif=1 ORDER BY nom")
        managers = c.fetchall()
        conn.close()

        depts_opts = "".join(f'<option value="{d["id"]}">{d["nom"]}</option>' for d in departements)
        postes_opts = "".join(f'<option value="{p["id"]}">{p["intitule"]}</option>' for p in postes)
        sites_opts = "".join(f'<option value="{s["id"]}">{s["nom"]}</option>' for s in sites)
        managers_opts = "".join(f'<option value="{m["id"]}">{m["nom"]} {m["prenom"]} ({m["matricule"]})</option>' for m in managers)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user-plus"></i> Nouvel Employé</h2>
          <a href="/employes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <h3 style="margin-bottom:20px;color:#7c3aed"><i class="fas fa-user"></i> Informations personnelles</h3>
            <div class="form-grid">
              <div class="form-group"><label>Matricule (auto si vide)</label><input type="text" name="matricule" placeholder="EMP-2026-0001"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" required></div>
              <div class="form-group"><label>Date de naissance *</label><input type="date" name="date_naissance" required></div>
              <div class="form-group"><label>Lieu de naissance</label><input type="text" name="lieu_naissance"></div>
              <div class="form-group"><label>Sexe *</label>
                <select name="sexe" required>
                  <option value="">--</option>
                  <option value="M">Masculin</option>
                  <option value="F">Féminin</option>
                </select>
              </div>
              <div class="form-group"><label>Situation matrimoniale</label>
                <select name="situation_matrimoniale">
                  <option value="">--</option>
                  <option>Célibataire</option><option>Marié(e)</option>
                  <option>Divorcé(e)</option><option>Veuf(ve)</option>
                </select>
              </div>
              <div class="form-group"><label>Nombre d'enfants</label><input type="number" name="nombre_enfants" value="0" min="0"></div>
              <div class="form-group"><label>Nationalité</label><input type="text" name="nationalite" value="Sénégalaise"></div>
            </div>

            <h3 style="margin:25px 0 20px;color:#7c3aed"><i class="fas fa-id-card"></i> Pièces d'identité</h3>
            <div class="form-grid">
              <div class="form-group"><label>CNI</label><input type="text" name="cni" placeholder="Numéro CNI"></div>
              <div class="form-group"><label>N° CSS</label><input type="text" name="numero_css"></div>
              <div class="form-group"><label>N° IPRES</label><input type="text" name="numero_ipres"></div>
            </div>

            <h3 style="margin:25px 0 20px;color:#7c3aed"><i class="fas fa-phone"></i> Coordonnées</h3>
            <div class="form-grid">
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" required></div>
              <div class="form-group"><label>Téléphone urgence</label><input type="tel" name="telephone_urgence"></div>
              <div class="form-group"><label>Email</label><input type="email" name="email"></div>
              <div class="form-group"><label>Adresse</label><input type="text" name="adresse"></div>
              <div class="form-group"><label>Ville</label><input type="text" name="ville" value="Dakar"></div>
              <div class="form-group"><label>Région</label><input type="text" name="region" value="Dakar"></div>
            </div>

            <h3 style="margin:25px 0 20px;color:#7c3aed"><i class="fas fa-briefcase"></i> Affectation</h3>
            <div class="form-grid">
              <div class="form-group"><label>Poste</label><select name="poste_id"><option value="">--</option>{postes_opts}</select></div>
              <div class="form-group"><label>Département</label><select name="departement_id"><option value="">--</option>{depts_opts}</select></div>
              <div class="form-group"><label>Site</label><select name="site_id"><option value="">--</option>{sites_opts}</select></div>
              <div class="form-group"><label>Manager</label><select name="manager_id"><option value="">--</option>{managers_opts}</select></div>
            </div>

            <h3 style="margin:25px 0 20px;color:#7c3aed"><i class="fas fa-file-contract"></i> Contrat</h3>
            <div class="form-grid">
              <div class="form-group"><label>Type de contrat *</label>
                <select name="type_contrat" required>
                  <option value="CDI">CDI</option>
                  <option value="CDD">CDD</option>
                  <option value="Stage">Stage</option>
                  <option value="Intérim">Intérim</option>
                  <option value="Freelance">Freelance</option>
                </select>
              </div>
              <div class="form-group"><label>Date d'embauche *</label><input type="date" name="date_embauche" required></div>
              <div class="form-group"><label>Date de fin (si CDD)</label><input type="date" name="date_fin_contrat"></div>
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  <option value="Actif">Actif</option>
                  <option value="Congé">Congé</option>
                  <option value="Suspendu">Suspendu</option>
                </select>
              </div>
            </div>

            <h3 style="margin:25px 0 20px;color:#7c3aed"><i class="fas fa-money-bill-wave"></i> Rémunération</h3>
            <div class="form-grid">
              <div class="form-group"><label>Salaire de base (FCFA) *</label><input type="number" name="salaire_base" step="0.01" value="0" required></div>
              <div class="form-group"><label>Prime de transport</label><input type="number" name="prime_transport" step="0.01" value="25000"></div>
              <div class="form-group"><label>Prime de logement</label><input type="number" name="prime_logement" step="0.01" value="0"></div>
              <div class="form-group"><label>Autres primes</label><input type="number" name="prime_autre" step="0.01" value="0"></div>
              <div class="form-group"><label>Banque</label><input type="text" name="banque" placeholder="CBAO, Ecobank..."></div>
              <div class="form-group"><label>RIB</label><input type="text" name="rib"></div>
              <div class="form-group"><label>Mode de paiement</label>
                <select name="mode_paiement">
                  <option value="Virement">Virement bancaire</option>
                  <option value="Wave">Wave</option>
                  <option value="Orange Money">Orange Money</option>
                  <option value="Espèces">Espèces</option>
                </select>
              </div>
            </div>

            <div class="form-group form-full" style="margin-top:15px"><label>Notes internes</label><textarea name="notes" rows="2"></textarea></div>

            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer l'employé</button>
              <a href="/employes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='employes', page_title='Nouvel employé')

    @app.route('/employes/<int:eid>')
    @staff_required
    def employe_detail(eid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT e.*, p.intitule as poste_nom, d.nom as dept_nom,
                            s.nom as site_nom, m.nom as manager_nom, m.prenom as manager_prenom
                     FROM employes e
                     LEFT JOIN postes p ON e.poste_id = p.id
                     LEFT JOIN departements d ON e.departement_id = d.id
                     LEFT JOIN sites s ON e.site_id = s.id
                     LEFT JOIN employes m ON e.manager_id = m.id
                     WHERE e.id=?""", (eid,))
        e = c.fetchone()
        if not e:
            conn.close()
            flash("Employé introuvable", "danger")
            return redirect('/employes')

        # Congés
        c.execute("""SELECT cg.*, tc.nom as type_nom, tc.couleur FROM conges cg
                     JOIN types_conges tc ON cg.type_conge_id = tc.id
                     WHERE cg.employe_id = ?
                     ORDER BY cg.date_debut DESC LIMIT 10""", (eid,))
        conges = c.fetchall()

        # Bulletins paie
        c.execute("""SELECT * FROM bulletins_paie WHERE employe_id = ?
                     ORDER BY annee DESC, mois DESC LIMIT 12""", (eid,))
        bulletins = c.fetchall()

        # Pointages récents
        c.execute("""SELECT * FROM pointages WHERE employe_id = ?
                     ORDER BY date_pointage DESC LIMIT 10""", (eid,))
        pointages = c.fetchall()

        # Contrats
        c.execute("""SELECT * FROM contrats WHERE employe_id = ?
                     ORDER BY date_debut DESC""", (eid,))
        contrats = c.fetchall()

        # Formations
        c.execute("""SELECT f.titre, f.date_debut, f.date_fin, fe.statut, fe.note
                     FROM formations_employes fe
                     JOIN formations f ON fe.formation_id = f.id
                     WHERE fe.employe_id = ?
                     ORDER BY f.date_debut DESC LIMIT 5""", (eid,))
        formations = c.fetchall()

        conn.close()

        try:
            naiss = datetime.fromisoformat(e['date_naissance'])
            age = (datetime.now() - naiss).days // 365
        except Exception:
            age = '?'

        try:
            emb = datetime.fromisoformat(e['date_embauche'])
            anciennete = (datetime.now() - emb).days // 365
        except Exception:
            anciennete = '?'

        salaire_total = e['salaire_base'] + (e['prime_transport'] or 0) + (e['prime_logement'] or 0) + (e['prime_autre'] or 0)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user-circle"></i> {e['nom']} {e['prenom']}</h2>
          <div style="display:flex;gap:10px">
            <a href="/pointages/nouveau?employe_id={eid}" class="btn btn-success"><i class="fas fa-clock"></i> Pointage</a>
            <a href="/conges/nouveau?employe_id={eid}" class="btn btn-primary"><i class="fas fa-calendar-plus"></i> Congé</a>
            <a href="/employes/{eid}/modifier" class="btn btn-warning"><i class="fas fa-edit"></i> Modifier</a>
            <a href="/employes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-id-badge stat-icon"></i>
            <div class="stat-value" style="font-size:1.2rem">{e['matricule']}</div>
            <div class="stat-label">Matricule</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-briefcase stat-icon"></i>
            <div class="stat-value" style="font-size:1.1rem">{e['poste_nom'] or '-'}</div>
            <div class="stat-label">Poste</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-calendar stat-icon"></i>
            <div class="stat-value">{anciennete} ans</div>
            <div class="stat-label">Ancienneté</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-money-bill-wave stat-icon"></i>
            <div class="stat-value">{salaire_total:,.0f}</div>
            <div class="stat-label">Salaire brut (FCFA)</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations personnelles</h3></div>
          <div class="form-grid">
            <div><strong>Nom complet :</strong> {e['nom']} {e['prenom']}</div>
            <div><strong>Date de naissance :</strong> {e['date_naissance']} ({age} ans)</div>
            <div><strong>Lieu de naissance :</strong> {e['lieu_naissance'] or '-'}</div>
            <div><strong>Sexe :</strong> {'Masculin' if e['sexe'] == 'M' else 'Féminin'}</div>
            <div><strong>Situation :</strong> {e['situation_matrimoniale'] or '-'}</div>
            <div><strong>Enfants :</strong> {e['nombre_enfants']}</div>
            <div><strong>Nationalité :</strong> {e['nationalite']}</div>
            <div><strong>CNI :</strong> {e['cni'] or '-'}</div>
            <div><strong>N° CSS :</strong> {e['numero_css'] or '-'}</div>
            <div><strong>N° IPRES :</strong> {e['numero_ipres'] or '-'}</div>
            <div><strong>Téléphone :</strong> {e['telephone']}</div>
            <div><strong>Urgence :</strong> {e['telephone_urgence'] or '-'}</div>
            <div><strong>Email :</strong> {e['email'] or '-'}</div>
            <div><strong>Adresse :</strong> {e['adresse'] or '-'}</div>
            <div><strong>Ville :</strong> {e['ville'] or '-'}, {e['region'] or ''}</div>
            <div><strong>Banque :</strong> {e['banque'] or '-'}</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-briefcase"></i> Situation professionnelle</h3></div>
          <div class="form-grid">
            <div><strong>Poste :</strong> {e['poste_nom'] or '-'}</div>
            <div><strong>Département :</strong> {e['dept_nom'] or '-'}</div>
            <div><strong>Site :</strong> {e['site_nom'] or '-'}</div>
            <div><strong>Manager :</strong> {e['manager_nom'] or '-'} {e['manager_prenom'] or ''}</div>
            <div><strong>Type de contrat :</strong> <span class="badge badge-primary">{e['type_contrat']}</span></div>
            <div><strong>Statut :</strong> <span class="badge badge-success">{e['statut']}</span></div>
            <div><strong>Date d'embauche :</strong> {e['date_embauche']}</div>
            <div><strong>Fin de contrat :</strong> {e['date_fin_contrat'] or 'Indéterminée'}</div>
            <div><strong>Salaire de base :</strong> {e['salaire_base']:,.0f} FCFA</div>
            <div><strong>Prime transport :</strong> {e['prime_transport']:,.0f} FCFA</div>
            <div><strong>Prime logement :</strong> {e['prime_logement']:,.0f} FCFA</div>
            <div><strong>Autres primes :</strong> {e['prime_autre']:,.0f} FCFA</div>
            <div><strong>Mode paiement :</strong> {e['mode_paiement'] or '-'}</div>
            <div><strong>RIB :</strong> {e['rib'] or '-'}</div>
          </div>
        </div>
        """

        if bulletins:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-file-invoice-dollar"></i> Derniers bulletins de paie</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Période</th><th>Brut</th><th>Retenues</th><th>Net à payer</th><th>Statut</th></tr></thead>
                  <tbody>
            """
            for b in bulletins:
                badge = 'badge-success' if b['statut'] == 'Payé' else ('badge-warning' if b['statut'] == 'Validé' else 'badge-info')
                content += f"""
                <tr>
                  <td><strong>{b['mois']:02d}/{b['annee']}</strong></td>
                  <td>{b['salaire_brut']:,.0f} FCFA</td>
                  <td>{b['total_retenues']:,.0f} FCFA</td>
                  <td><strong style="color:#059669">{b['salaire_net']:,.0f} FCFA</strong></td>
                  <td><span class="badge {badge}">{b['statut']}</span></td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        if conges:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-calendar-check"></i> Historique des congés</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Type</th><th>Période</th><th>Jours</th><th>Statut</th></tr></thead>
                  <tbody>
            """
            for cg in conges:
                badge = 'badge-success' if cg['statut'] == 'Approuvé' else ('badge-warning' if cg['statut'] == 'En attente' else 'badge-danger')
                content += f"""
                <tr>
                  <td><span class="badge" style="background:{cg['type_couleur']}20;color:{cg['type_couleur']}">{cg['type_nom']}</span></td>
                  <td>{cg['date_debut']} → {cg['date_fin']}</td>
                  <td><strong>{cg['nb_jours']}j</strong></td>
                  <td><span class="badge {badge}">{cg['statut']}</span></td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        if pointages:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-clock"></i> Derniers pointages</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Date</th><th>Arrivée</th><th>Départ</th><th>Heures</th><th>Retard</th></tr></thead>
                  <tbody>
            """
            for p in pointages:
                retard = f'<span class="badge badge-warning">{p["retard_minutes"]}min</span>' if p['retard_minutes'] > 0 else '<span class="badge badge-success">À l\'heure</span>'
                content += f"""
                <tr>
                  <td><strong>{p['date_pointage']}</strong></td>
                  <td>{p['heure_arrivee'] or '-'}</td>
                  <td>{p['heure_depart'] or '-'}</td>
                  <td>{p['heures_travaillees']:.2f}h</td>
                  <td>{retard}</td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        if contrats:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-file-contract"></i> Contrats</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>N°</th><th>Type</th><th>Début</th><th>Fin</th><th>Salaire</th><th>Statut</th></tr></thead>
                  <tbody>
            """
            for ct in contrats:
                badge = 'badge-success' if ct['statut'] == 'Actif' else 'badge-info'
                content += f"""
                <tr>
                  <td><strong>{ct['numero']}</strong></td>
                  <td><span class="badge badge-primary">{ct['type_contrat']}</span></td>
                  <td>{ct['date_debut']}</td>
                  <td>{ct['date_fin'] or 'Indéterminée'}</td>
                  <td>{ct['salaire_mensuel']:,.0f} FCFA</td>
                  <td><span class="badge {badge}">{ct['statut']}</span></td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        return render_page(content, active='employes', page_title=f"{e['nom']} {e['prenom']}")

    @app.route('/employes/<int:eid>/modifier', methods=['GET', 'POST'])
    @rh_required
    def employe_modifier(eid):
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                c.execute("""UPDATE employes SET
                    nom=?, prenom=?, date_naissance=?, lieu_naissance=?, sexe=?,
                    situation_matrimoniale=?, nombre_enfants=?, nationalite=?,
                    cni=?, numero_css=?, numero_ipres=?,
                    telephone=?, telephone_urgence=?, email=?, adresse=?, ville=?, region=?,
                    poste_id=?, departement_id=?, site_id=?, manager_id=?,
                    date_embauche=?, date_fin_contrat=?, type_contrat=?, statut=?,
                    salaire_base=?, prime_transport=?, prime_logement=?, prime_autre=?,
                    banque=?, rib=?, mode_paiement=?, notes=?
                    WHERE id=?""",
                    (request.form['nom'], request.form['prenom'], request.form['date_naissance'],
                     request.form.get('lieu_naissance', ''), request.form['sexe'],
                     request.form.get('situation_matrimoniale', ''),
                     int(request.form.get('nombre_enfants') or 0),
                     request.form.get('nationalite', 'Sénégalaise'),
                     request.form.get('cni', ''), request.form.get('numero_css', ''),
                     request.form.get('numero_ipres', ''),
                     request.form['telephone'], request.form.get('telephone_urgence', ''),
                     request.form.get('email', ''), request.form.get('adresse', ''),
                     request.form.get('ville', ''), request.form.get('region', ''),
                     int(request.form['poste_id']) if request.form.get('poste_id') else None,
                     int(request.form['departement_id']) if request.form.get('departement_id') else None,
                     int(request.form['site_id']) if request.form.get('site_id') else None,
                     int(request.form['manager_id']) if request.form.get('manager_id') else None,
                     request.form['date_embauche'],
                     request.form.get('date_fin_contrat') or None,
                     request.form.get('type_contrat', 'CDI'),
                     request.form.get('statut', 'Actif'),
                     float(request.form.get('salaire_base') or 0),
                     float(request.form.get('prime_transport') or 0),
                     float(request.form.get('prime_logement') or 0),
                     float(request.form.get('prime_autre') or 0),
                     request.form.get('banque', ''), request.form.get('rib', ''),
                     request.form.get('mode_paiement', 'Virement'),
                     request.form.get('notes', ''),
                     eid))
                conn.commit()
                conn.close()
                if current_user:
                    log_action(current_user.id, 'UPDATE_EMPLOYE', f'ID {eid}')
                flash("✅ Employé mis à jour", "success")
                return redirect(f'/employes/{eid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM employes WHERE id=?", (eid,))
        e = c.fetchone()
        c.execute("SELECT id, nom FROM departements WHERE actif=1 ORDER BY nom")
        departements = c.fetchall()
        c.execute("SELECT id, intitule FROM postes WHERE actif=1 ORDER BY intitule")
        postes = c.fetchall()
        c.execute("SELECT id, nom FROM sites WHERE actif=1 ORDER BY nom")
        sites = c.fetchall()
        c.execute("SELECT id, nom, prenom, matricule FROM employes WHERE actif=1 AND id != ? ORDER BY nom", (eid,))
        managers = c.fetchall()
        conn.close()

        depts_opts = "".join(f'<option value="{d["id"]}" {"selected" if d["id"]==e["departement_id"] else ""}>{d["nom"]}</option>' for d in departements)
        postes_opts = "".join(f'<option value="{p["id"]}" {"selected" if p["id"]==e["poste_id"] else ""}>{p["intitule"]}</option>' for p in postes)
        sites_opts = "".join(f'<option value="{s["id"]}" {"selected" if s["id"]==e["site_id"] else ""}>{s["nom"]}</option>' for s in sites)
        managers_opts = "".join(f'<option value="{m["id"]}" {"selected" if m["id"]==e["manager_id"] else ""}>{m["nom"]} {m["prenom"]} ({m["matricule"]})</option>' for m in managers)
        contrats_types = ['CDI', 'CDD', 'Stage', 'Intérim', 'Freelance']
        statuts = ['Actif', 'Congé', 'Suspendu', 'Démission', 'Retraite', 'Licencié']

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user-edit"></i> Modifier {e['nom']} {e['prenom']}</h2>
          <a href="/employes/{eid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Matricule (non modifiable)</label><input type="text" value="{e['matricule']}" disabled></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{e['nom']}" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" value="{e['prenom']}" required></div>
              <div class="form-group"><label>Date de naissance *</label><input type="date" name="date_naissance" value="{e['date_naissance']}" required></div>
              <div class="form-group"><label>Lieu de naissance</label><input type="text" name="lieu_naissance" value="{e['lieu_naissance'] or ''}"></div>
              <div class="form-group"><label>Sexe *</label>
                <select name="sexe" required>
                  <option value="M" {"selected" if e['sexe']=='M' else ""}>Masculin</option>
                  <option value="F" {"selected" if e['sexe']=='F' else ""}>Féminin</option>
                </select>
              </div>
              <div class="form-group"><label>Situation matrimoniale</label>
                <select name="situation_matrimoniale">
                  <option value="">--</option>
                  {''.join(f'<option {"selected" if e["situation_matrimoniale"]==s else ""}>{s}</option>' for s in ["Célibataire", "Marié(e)", "Divorcé(e)", "Veuf(ve)"])}
                </select>
              </div>
              <div class="form-group"><label>Nombre d'enfants</label><input type="number" name="nombre_enfants" value="{e['nombre_enfants']}"></div>
              <div class="form-group"><label>Nationalité</label><input type="text" name="nationalite" value="{e['nationalite']}"></div>
              <div class="form-group"><label>CNI</label><input type="text" name="cni" value="{e['cni'] or ''}"></div>
              <div class="form-group"><label>N° CSS</label><input type="text" name="numero_css" value="{e['numero_css'] or ''}"></div>
              <div class="form-group"><label>N° IPRES</label><input type="text" name="numero_ipres" value="{e['numero_ipres'] or ''}"></div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" value="{e['telephone']}" required></div>
              <div class="form-group"><label>Urgence</label><input type="tel" name="telephone_urgence" value="{e['telephone_urgence'] or ''}"></div>
              <div class="form-group"><label>Email</label><input type="email" name="email" value="{e['email'] or ''}"></div>
              <div class="form-group"><label>Adresse</label><input type="text" name="adresse" value="{e['adresse'] or ''}"></div>
              <div class="form-group"><label>Ville</label><input type="text" name="ville" value="{e['ville'] or ''}"></div>
              <div class="form-group"><label>Région</label><input type="text" name="region" value="{e['region'] or ''}"></div>
              <div class="form-group"><label>Poste</label><select name="poste_id"><option value="">--</option>{postes_opts}</select></div>
              <div class="form-group"><label>Département</label><select name="departement_id"><option value="">--</option>{depts_opts}</select></div>
              <div class="form-group"><label>Site</label><select name="site_id"><option value="">--</option>{sites_opts}</select></div>
              <div class="form-group"><label>Manager</label><select name="manager_id"><option value="">--</option>{managers_opts}</select></div>
              <div class="form-group"><label>Type contrat</label>
                <select name="type_contrat">
                  {''.join(f'<option value="{t}" {"selected" if e["type_contrat"]==t else ""}>{t}</option>' for t in contrats_types)}
                </select>
              </div>
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  {''.join(f'<option value="{s}" {"selected" if e["statut"]==s else ""}>{s}</option>' for s in statuts)}
                </select>
              </div>
              <div class="form-group"><label>Date embauche *</label><input type="date" name="date_embauche" value="{e['date_embauche']}" required></div>
              <div class="form-group"><label>Date fin contrat</label><input type="date" name="date_fin_contrat" value="{e['date_fin_contrat'] or ''}"></div>
              <div class="form-group"><label>Salaire base *</label><input type="number" name="salaire_base" step="0.01" value="{e['salaire_base']}" required></div>
              <div class="form-group"><label>Prime transport</label><input type="number" name="prime_transport" step="0.01" value="{e['prime_transport']}"></div>
              <div class="form-group"><label>Prime logement</label><input type="number" name="prime_logement" step="0.01" value="{e['prime_logement']}"></div>
              <div class="form-group"><label>Autres primes</label><input type="number" name="prime_autre" step="0.01" value="{e['prime_autre']}"></div>
              <div class="form-group"><label>Banque</label><input type="text" name="banque" value="{e['banque'] or ''}"></div>
              <div class="form-group"><label>RIB</label><input type="text" name="rib" value="{e['rib'] or ''}"></div>
              <div class="form-group"><label>Mode paiement</label>
                <select name="mode_paiement">
                  {''.join(f'<option value="{m}" {"selected" if e["mode_paiement"]==m else ""}>{m}</option>' for m in ["Virement", "Wave", "Orange Money", "Espèces"])}
                </select>
              </div>
            </div>
            <div class="form-group form-full" style="margin-top:15px"><label>Notes internes</label><textarea name="notes" rows="2">{e['notes'] or ''}</textarea></div>

            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/employes/{eid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/employes/{eid}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer la suppression ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='employes', page_title='Modifier employé')

    @app.route('/employes/<int:eid>/supprimer')
    @drh_required
    def employe_supprimer(eid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE employes SET actif=0 WHERE id=?", (eid,))
            conn.commit()
            conn.close()
            if current_user:
                log_action(current_user.id, 'DELETE_EMPLOYE', f'ID {eid}')
            flash("✅ Employé archivé", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/employes')

    print("[CRUD] ✅ Routes employés enregistrées")

    # ==================== DÉPARTEMENTS ====================
    @app.route('/departements')
    @rh_required
    def departements_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT d.*, s.nom as site_nom,
                     (SELECT COUNT(*) FROM employes WHERE departement_id = d.id AND actif=1) as nb_employes,
                     (SELECT COUNT(*) FROM postes WHERE departement_id = d.id AND actif=1) as nb_postes
                     FROM departements d
                     LEFT JOIN sites s ON d.site_id = s.id
                     WHERE d.actif=1 ORDER BY d.nom""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-sitemap"></i> Départements</h2>
            <div class="page-subtitle">Structure organisationnelle</div>
          </div>
          <a href="/departements/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau département</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Département</th><th>Site</th><th>Employés</th><th>Postes</th><th>Budget annuel</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for d in rows:
            content += f"""
            <tr>
              <td><strong>{d['code']}</strong></td>
              <td>
                <strong>{d['nom']}</strong><br>
                <small style="color:#94a3b8">{d['description'] or ''}</small>
              </td>
              <td>{d['site_nom'] or '-'}</td>
              <td><span class="badge badge-primary">{d['nb_employes']}</span></td>
              <td><span class="badge badge-info">{d['nb_postes']}</span></td>
              <td><strong style="color:#7c3aed">{d['budget_annuel']:,.0f}</strong> FCFA</td>
              <td>
                <a href="/departements/{d['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a>
                <a href="/departements/{d['id']}/supprimer" class="btn btn-danger btn-sm" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="7" class="empty"><i class="fas fa-sitemap"></i><br>Aucun département</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='departements', page_title='Départements')

    @app.route('/departements/nouveau', methods=['GET', 'POST'])
    @drh_required
    def departement_nouveau():
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                code = request.form.get('code') or gen_code('DEPT', 'departements')
                c.execute("""INSERT INTO departements (code, nom, description, site_id, budget_annuel, actif)
                    VALUES (?, ?, ?, ?, ?, 1)""",
                    (code, request.form['nom'], request.form.get('description', ''),
                     int(request.form['site_id']) if request.form.get('site_id') else None,
                     float(request.form.get('budget_annuel') or 0)))
                conn.commit()
                conn.close()
                flash(f"✅ Département {code} créé", "success")
                return redirect('/departements')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom FROM sites WHERE actif=1 ORDER BY nom")
        sites = c.fetchall()
        conn.close()
        sites_opts = "".join(f'<option value="{s["id"]}">{s["nom"]}</option>' for s in sites)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-sitemap"></i> Nouveau Département</h2>
          <a href="/departements" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code (auto si vide)</label><input type="text" name="code" placeholder="DEPT-0001"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="2"></textarea></div>
              <div class="form-group"><label>Site</label><select name="site_id"><option value="">--</option>{sites_opts}</select></div>
              <div class="form-group"><label>Budget annuel (FCFA)</label><input type="number" name="budget_annuel" step="0.01" value="0"></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/departements" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='departements', page_title='Nouveau département')

    @app.route('/departements/<int:did>/modifier', methods=['GET', 'POST'])
    @drh_required
    def departement_modifier(did):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE departements SET code=?, nom=?, description=?, site_id=?, budget_annuel=? WHERE id=?""",
                    (request.form['code'], request.form['nom'], request.form.get('description', ''),
                     int(request.form['site_id']) if request.form.get('site_id') else None,
                     float(request.form.get('budget_annuel') or 0), did))
                conn.commit()
                conn.close()
                flash("✅ Département mis à jour", "success")
                return redirect('/departements')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM departements WHERE id=?", (did,))
        d = c.fetchone()
        c.execute("SELECT id, nom FROM sites WHERE actif=1 ORDER BY nom")
        sites = c.fetchall()
        conn.close()
        sites_opts = "".join(f'<option value="{s["id"]}" {"selected" if s["id"]==d["site_id"] else ""}>{s["nom"]}</option>' for s in sites)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-edit"></i> Modifier {d['nom']}</h2>
          <a href="/departements" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code *</label><input type="text" name="code" value="{d['code']}" required></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{d['nom']}" required></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="2">{d['description'] or ''}</textarea></div>
              <div class="form-group"><label>Site</label><select name="site_id"><option value="">--</option>{sites_opts}</select></div>
              <div class="form-group"><label>Budget annuel</label><input type="number" name="budget_annuel" step="0.01" value="{d['budget_annuel']}"></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/departements" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/departements/{did}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='departements', page_title='Modifier département')

    @app.route('/departements/<int:did>/supprimer')
    @admin_required
    def departement_supprimer(did):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE departements SET actif=0 WHERE id=?", (did,))
            conn.commit()
            conn.close()
            flash("✅ Département archivé", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/departements')

    print("[CRUD] ✅ Routes départements enregistrées")

    # ==================== POSTES ====================
    @app.route('/postes')
    @rh_required
    def postes_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT p.*, d.nom as dept_nom,
                     (SELECT COUNT(*) FROM employes WHERE poste_id = p.id AND actif=1) as nb_employes
                     FROM postes p
                     LEFT JOIN departements d ON p.departement_id = d.id
                     WHERE p.actif=1 ORDER BY d.nom, p.intitule""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-briefcase"></i> Postes</h2>
            <div class="page-subtitle">Grille des emplois et salaires</div>
          </div>
          <a href="/postes/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau poste</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Intitulé</th><th>Département</th><th>Catégorie</th><th>Niveau</th><th>Salaire min - max</th><th>Employés</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for p in rows:
            content += f"""
            <tr>
              <td><strong>{p['code']}</strong></td>
              <td><strong>{p['intitule']}</strong><br><small style="color:#94a3b8">{p['description'] or ''}</small></td>
              <td>{p['dept_nom'] or '-'}</td>
              <td><span class="badge badge-primary">{p['categorie'] or '-'}</span></td>
              <td><span class="badge badge-info">{p['niveau'] or '-'}</span></td>
              <td><strong>{p['salaire_min']:,.0f}</strong> → <strong>{p['salaire_max']:,.0f}</strong> FCFA</td>
              <td><span class="badge badge-success">{p['nb_employes']}</span></td>
              <td>
                <a href="/postes/{p['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a>
                <a href="/postes/{p['id']}/supprimer" class="btn btn-danger btn-sm" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-briefcase"></i><br>Aucun poste</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='postes', page_title='Postes')

    @app.route('/postes/nouveau', methods=['GET', 'POST'])
    @rh_required
    def poste_nouveau():
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                code = request.form.get('code') or gen_code('P', 'postes')
                c.execute("""INSERT INTO postes (code, intitule, description, departement_id,
                    categorie, niveau, salaire_min, salaire_max, competences, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (code, request.form['intitule'], request.form.get('description', ''),
                     int(request.form['departement_id']) if request.form.get('departement_id') else None,
                     request.form.get('categorie', ''), request.form.get('niveau', ''),
                     float(request.form.get('salaire_min') or 0),
                     float(request.form.get('salaire_max') or 0),
                     request.form.get('competences', '')))
                conn.commit()
                conn.close()
                flash(f"✅ Poste {code} créé", "success")
                return redirect('/postes')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom FROM departements WHERE actif=1 ORDER BY nom")
        departements = c.fetchall()
        conn.close()
        depts_opts = "".join(f'<option value="{d["id"]}">{d["nom"]}</option>' for d in departements)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-briefcase"></i> Nouveau Poste</h2>
          <a href="/postes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code (auto si vide)</label><input type="text" name="code" placeholder="P-0001"></div>
              <div class="form-group"><label>Intitulé *</label><input type="text" name="intitule" required></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="2"></textarea></div>
              <div class="form-group"><label>Département</label><select name="departement_id"><option value="">--</option>{depts_opts}</select></div>
              <div class="form-group"><label>Catégorie</label>
                <select name="categorie">
                  <option value="">--</option>
                  <option>Direction</option><option>Cadre</option>
                  <option>Agent</option><option>Ouvrier</option>
                </select>
              </div>
              <div class="form-group"><label>Niveau</label>
                <select name="niveau">
                  <option value="">--</option>
                  <option>A</option><option>B</option>
                  <option>C</option><option>D</option>
                </select>
              </div>
              <div class="form-group"><label>Salaire min (FCFA)</label><input type="number" name="salaire_min" step="0.01" value="0"></div>
              <div class="form-group"><label>Salaire max (FCFA)</label><input type="number" name="salaire_max" step="0.01" value="0"></div>
              <div class="form-group form-full"><label>Compétences requises</label><textarea name="competences" rows="2"></textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/postes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='postes', page_title='Nouveau poste')

    @app.route('/postes/<int:pid>/modifier', methods=['GET', 'POST'])
    @rh_required
    def poste_modifier(pid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE postes SET code=?, intitule=?, description=?, departement_id=?,
                    categorie=?, niveau=?, salaire_min=?, salaire_max=?, competences=? WHERE id=?""",
                    (request.form['code'], request.form['intitule'], request.form.get('description', ''),
                     int(request.form['departement_id']) if request.form.get('departement_id') else None,
                     request.form.get('categorie', ''), request.form.get('niveau', ''),
                     float(request.form.get('salaire_min') or 0),
                     float(request.form.get('salaire_max') or 0),
                     request.form.get('competences', ''), pid))
                conn.commit()
                conn.close()
                flash("✅ Poste mis à jour", "success")
                return redirect('/postes')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM postes WHERE id=?", (pid,))
        p = c.fetchone()
        c.execute("SELECT id, nom FROM departements WHERE actif=1 ORDER BY nom")
        departements = c.fetchall()
        conn.close()
        depts_opts = "".join(f'<option value="{d["id"]}" {"selected" if d["id"]==p["departement_id"] else ""}>{d["nom"]}</option>' for d in departements)
        cats = ['Direction', 'Cadre', 'Agent', 'Ouvrier']
        niveaux = ['A', 'B', 'C', 'D']

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-edit"></i> Modifier {p['intitule']}</h2>
          <a href="/postes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code *</label><input type="text" name="code" value="{p['code']}" required></div>
              <div class="form-group"><label>Intitulé *</label><input type="text" name="intitule" value="{p['intitule']}" required></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="2">{p['description'] or ''}</textarea></div>
              <div class="form-group"><label>Département</label><select name="departement_id"><option value="">--</option>{depts_opts}</select></div>
              <div class="form-group"><label>Catégorie</label>
                <select name="categorie">
                  <option value="">--</option>
                  {''.join(f'<option {"selected" if p["categorie"]==c_ else ""}>{c_}</option>' for c_ in cats)}
                </select>
              </div>
              <div class="form-group"><label>Niveau</label>
                <select name="niveau">
                  <option value="">--</option>
                  {''.join(f'<option {"selected" if p["niveau"]==n else ""}>{n}</option>' for n in niveaux)}
                </select>
              </div>
              <div class="form-group"><label>Salaire min</label><input type="number" name="salaire_min" step="0.01" value="{p['salaire_min']}"></div>
              <div class="form-group"><label>Salaire max</label><input type="number" name="salaire_max" step="0.01" value="{p['salaire_max']}"></div>
              <div class="form-group form-full"><label>Compétences</label><textarea name="competences" rows="2">{p['competences'] or ''}</textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/postes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/postes/{pid}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='postes', page_title='Modifier poste')

    @app.route('/postes/<int:pid>/supprimer')
    @drh_required
    def poste_supprimer(pid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE postes SET actif=0 WHERE id=?", (pid,))
            conn.commit()
            conn.close()
            flash("✅ Poste archivé", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/postes')

    print("[CRUD] ✅ Routes postes enregistrées")

    # ==================== CONTRATS ====================
    @app.route('/contrats')
    @rh_required
    def contrats_liste():
        conn = get_db()
        c = conn.cursor()
        statut_filter = request.args.get('statut', '')
        query = """SELECT ct.*, e.nom, e.prenom, e.matricule
                   FROM contrats ct
                   JOIN employes e ON ct.employe_id = e.id
                   WHERE 1=1"""
        params = []
        if statut_filter:
            query += " AND ct.statut = ?"
            params.append(statut_filter)
        query += " ORDER BY ct.date_debut DESC"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-file-contract"></i> Contrats</h2>
            <div class="page-subtitle">{len(rows)} contrat(s)</div>
          </div>
          <div style="display:flex;gap:10px">
            <a href="/contrats?statut=Actif" class="btn btn-success btn-sm">Actifs</a>
            <a href="/contrats?statut=Terminé" class="btn btn-info btn-sm">Terminés</a>
            <a href="/contrats" class="btn btn-primary btn-sm">Tous</a>
          </div>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>N° Contrat</th><th>Employé</th><th>Type</th><th>Début</th><th>Fin</th><th>Salaire</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for ct in rows:
            badge = 'badge-success' if ct['statut'] == 'Actif' else 'badge-info'
            content += f"""
            <tr>
              <td><strong>{ct['numero']}</strong></td>
              <td>{ct['nom']} {ct['prenom']}<br><small style="color:#94a3b8">{ct['matricule']}</small></td>
              <td><span class="badge badge-primary">{ct['type_contrat']}</span></td>
              <td>{ct['date_debut']}</td>
              <td>{ct['date_fin'] or 'Indéterminée'}</td>
              <td><strong>{ct['salaire_mensuel']:,.0f}</strong> FCFA</td>
              <td><span class="badge {badge}">{ct['statut']}</span></td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="7" class="empty"><i class="fas fa-file-contract"></i><br>Aucun contrat</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='contrats', page_title='Contrats')

    print("[CRUD] ✅ Routes contrats enregistrées")

    # ==================== UTILISATEURS ====================
    @app.route('/utilisateurs')
    @admin_required
    def utilisateurs_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT u.*, e.nom as emp_nom, e.prenom as emp_prenom, e.matricule
                     FROM utilisateurs u
                     LEFT JOIN employes e ON u.employe_id = e.id
                     ORDER BY u.role, u.nom""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-user-shield"></i> Utilisateurs</h2>
            <div class="page-subtitle">Gestion des accès et rôles</div>
          </div>
          <a href="/utilisateurs/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvel utilisateur</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Username</th><th>Nom</th><th>Contact</th><th>Rôle</th><th>Employé lié</th><th>Dernière connexion</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for u in rows:
            role_badge = f'badge-role-{u["role"]}'
            statut_badge = 'badge-success' if u['actif'] else 'badge-danger'
            content += f"""
            <tr>
              <td><strong>{u['username']}</strong></td>
              <td>{u['nom']} {u['prenom']}</td>
              <td>{u['email'] or '-'}<br><small>{u['telephone'] or ''}</small></td>
              <td><span class="badge {role_badge}">{u['role']}</span></td>
              <td>{u['emp_nom'] or '-'} {u['emp_prenom'] or ''} {('(' + u['matricule'] + ')') if u['matricule'] else ''}</td>
              <td>{u['dernier_login'][:16] if u['dernier_login'] else 'Jamais'}</td>
              <td><span class="badge {statut_badge}">{'Actif' if u['actif'] else 'Inactif'}</span></td>
              <td>
                <a href="/utilisateurs/{u['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-user-shield"></i><br>Aucun utilisateur</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='utilisateurs', page_title='Utilisateurs')

    @app.route('/utilisateurs/nouveau', methods=['GET', 'POST'])
    @admin_required
    def utilisateur_nouveau():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                from auth import hash_password
                h = hash_password(request.form['password'])
                c.execute("""INSERT INTO utilisateurs
                    (username, password_hash, nom, prenom, email, telephone, role, employe_id, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (request.form['username'], h, request.form['nom'],
                     request.form['prenom'], request.form.get('email', ''),
                     request.form.get('telephone', ''), request.form['role'],
                     int(request.form['employe_id']) if request.form.get('employe_id') else None))
                conn.commit()
                conn.close()
                flash(f"✅ Utilisateur {request.form['username']} créé", "success")
                return redirect('/utilisateurs')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, nom, prenom, matricule FROM employes WHERE actif=1 ORDER BY nom")
        employes = c.fetchall()
        conn.close()
        emp_opts = "".join(f'<option value="{e["id"]}">{e["nom"]} {e["prenom"]} ({e["matricule"]})</option>' for e in employes)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user-plus"></i> Nouvel Utilisateur</h2>
          <a href="/utilisateurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Username *</label><input type="text" name="username" required></div>
              <div class="form-group"><label>Mot de passe *</label><input type="password" name="password" required minlength="6"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email"></div>
              <div class="form-group"><label>Téléphone</label><input type="tel" name="telephone"></div>
              <div class="form-group"><label>Rôle *</label>
                <select name="role" required>
                  <option value="employe">Employé</option>
                  <option value="manager">Manager</option>
                  <option value="rh">RH</option>
                  <option value="drh">DRH</option>
                  <option value="admin">Administrateur</option>
                </select>
              </div>
              <div class="form-group"><label>Employé lié</label><select name="employe_id"><option value="">--</option>{emp_opts}</select></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/utilisateurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='utilisateurs', page_title='Nouvel utilisateur')

    @app.route('/utilisateurs/<int:uid>/modifier', methods=['GET', 'POST'])
    @admin_required
    def utilisateur_modifier(uid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                if request.form.get('password'):
                    from auth import hash_password
                    h = hash_password(request.form['password'])
                    c.execute("UPDATE utilisateurs SET password_hash=? WHERE id=?", (h, uid))

                c.execute("""UPDATE utilisateurs SET username=?, nom=?, prenom=?, email=?,
                    telephone=?, role=?, employe_id=?, actif=? WHERE id=?""",
                    (request.form['username'], request.form['nom'], request.form['prenom'],
                     request.form.get('email', ''), request.form.get('telephone', ''),
                     request.form['role'],
                     int(request.form['employe_id']) if request.form.get('employe_id') else None,
                     1 if request.form.get('actif') else 0,
                     uid))
                conn.commit()
                conn.close()
                flash("✅ Utilisateur mis à jour", "success")
                return redirect('/utilisateurs')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM utilisateurs WHERE id=?", (uid,))
        u = c.fetchone()
        c.execute("SELECT id, nom, prenom, matricule FROM employes WHERE actif=1 ORDER BY nom")
        employes = c.fetchall()
        conn.close()
        emp_opts = "".join(f'<option value="{e["id"]}" {"selected" if e["id"]==u["employe_id"] else ""}>{e["nom"]} {e["prenom"]} ({e["matricule"]})</option>' for e in employes)
        roles = ['employe', 'manager', 'rh', 'drh', 'admin']

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user-edit"></i> Modifier {u['username']}</h2>
          <a href="/utilisateurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Username *</label><input type="text" name="username" value="{u['username']}" required></div>
              <div class="form-group"><label>Nouveau mot de passe (vide = inchangé)</label><input type="password" name="password" minlength="6"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{u['nom']}" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" value="{u['prenom']}" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email" value="{u['email'] or ''}"></div>
              <div class="form-group"><label>Téléphone</label><input type="tel" name="telephone" value="{u['telephone'] or ''}"></div>
              <div class="form-group"><label>Rôle *</label>
                <select name="role" required>
                  {''.join(f'<option value="{r}" {"selected" if u["role"]==r else ""}>{r.capitalize()}</option>' for r in roles)}
                </select>
              </div>
              <div class="form-group"><label>Employé lié</label><select name="employe_id"><option value="">--</option>{emp_opts}</select></div>
              <div class="form-group" style="display:flex;align-items:center;gap:8px;margin-top:30px">
                <input type="checkbox" name="actif" style="width:auto" {"checked" if u['actif'] else ""}>
                <label style="margin:0">Compte actif</label>
              </div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/utilisateurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='utilisateurs', page_title='Modifier utilisateur')

    print("[CRUD] ✅ Routes utilisateurs enregistrées")
