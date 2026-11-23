"""
Module CRUD complet pour Omega Hôtel
Chambres, Types chambres, Clients, Réservations, Tarifs, Utilisateurs
"""
from flask import render_template_string, request, redirect, flash, jsonify
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "/app/data/hotel.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def gen_code(prefix, table):
    conn = get_db()
    c = conn.cursor()
    year = datetime.now().year
    c.execute(f"SELECT COUNT(*) FROM {table}")
    n = c.fetchone()[0] + 1
    conn.close()
    return f"{prefix}-{year}-{n:04d}"


try:
    from auth import (role_required, admin_required, directeur_required,
                      reception_required, staff_required, menage_required, log_action)
    from flask_login import current_user
except ImportError:
    def role_required(*r):
        def d(f): return f
        return d
    def admin_required(f): return f
    def directeur_required(f): return f
    def reception_required(f): return f
    def staff_required(f): return f
    def menage_required(f): return f
    def log_action(*a, **k): pass
    current_user = None


def register_crud_routes(app, render_page):
    """Enregistre toutes les routes CRUD Hôtel"""

    # ==================== CHAMBRES ====================
    @app.route('/chambres')
    @staff_required
    def chambres_liste():
        conn = get_db()
        c = conn.cursor()

        statut_filter = request.args.get('statut', '')
        type_filter = request.args.get('type', '')
        etage_filter = request.args.get('etage', '')

        query = """SELECT ch.*, tc.nom as type_nom, tc.capacite_adultes, tc.capacite_enfants,
                          tc.superficie_m2, e.numero as etage_num
                   FROM chambres ch
                   JOIN types_chambres tc ON ch.type_id = tc.id
                   JOIN etages e ON ch.etage_id = e.id
                   WHERE ch.actif=1"""
        params = []

        if statut_filter:
            query += " AND ch.statut = ?"
            params.append(statut_filter)
        if type_filter:
            query += " AND ch.type_id = ?"
            params.append(int(type_filter))
        if etage_filter:
            query += " AND ch.etage_id = ?"
            params.append(int(etage_filter))

        query += " ORDER BY ch.numero"
        c.execute(query, params)
        rows = c.fetchall()

        # Stats
        c.execute("SELECT COUNT(*) FROM chambres WHERE actif=1")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM chambres WHERE statut='Occupée' AND actif=1")
        occupees = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM chambres WHERE statut='Disponible' AND actif=1")
        dispo = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM chambres WHERE etat_proprete IN ('À nettoyer', 'En cours') AND actif=1")
        a_nettoyer = c.fetchone()[0]

        # Types + étages pour filtres
        c.execute("SELECT id, nom FROM types_chambres WHERE actif=1 ORDER BY ordre")
        types = c.fetchall()
        c.execute("SELECT id, numero, nom FROM etages ORDER BY numero")
        etages = c.fetchall()
        conn.close()

        types_opts = "".join(f'<option value="{t["id"]}" {"selected" if type_filter == str(t["id"]) else ""}>{t["nom"]}</option>' for t in types)
        etages_opts = "".join(f'<option value="{e["id"]}" {"selected" if etage_filter == str(e["id"]) else ""}>Étage {e["numero"]}</option>' for e in etages)
        statuts = ['Disponible', 'Occupée', 'Réservée', 'Maintenance', 'Hors service']
        statuts_opts = "".join(f'<option value="{s}" {"selected" if statut_filter == s else ""}>{s}</option>' for s in statuts)

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-bed"></i> Chambres</h2>
            <div class="page-subtitle">{len(rows)} chambre(s) affichée(s)</div>
          </div>
          <a href="/chambres/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle chambre</a>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-bed stat-icon"></i>
            <div class="stat-value">{total}</div>
            <div class="stat-label">Total chambres</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-user stat-icon"></i>
            <div class="stat-value">{occupees}</div>
            <div class="stat-label">Occupées</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-check stat-icon"></i>
            <div class="stat-value">{dispo}</div>
            <div class="stat-label">Disponibles</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-broom stat-icon"></i>
            <div class="stat-value">{a_nettoyer}</div>
            <div class="stat-label">À nettoyer</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Inventaire des chambres</h3>
            <form method="GET" style="display:flex;gap:8px;flex-wrap:wrap">
              <select name="statut" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous statuts</option>
                {statuts_opts}
              </select>
              <select name="type" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous types</option>
                {types_opts}
              </select>
              <select name="etage" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous étages</option>
                {etages_opts}
              </select>
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>N°</th><th>Type</th><th>Étage</th><th>Vue</th>
                  <th>Capacité</th><th>Statut</th><th>Propreté</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
        """
        for ch in rows:
            statut_badge = 'badge-success'
            if ch['statut'] == 'Occupée': statut_badge = 'badge-danger'
            elif ch['statut'] == 'Réservée': statut_badge = 'badge-info'
            elif ch['statut'] == 'Maintenance': statut_badge = 'badge-warning'
            elif ch['statut'] == 'Hors service': statut_badge = 'badge-danger'

            proprete_badge = 'badge-success'
            if ch['etat_proprete'] == 'À nettoyer': proprete_badge = 'badge-warning'
            elif ch['etat_proprete'] == 'En cours': proprete_badge = 'badge-info'
            elif ch['etat_proprete'] == 'Sale': proprete_badge = 'badge-danger'

            content += f"""
            <tr>
              <td><strong style="font-size:1.1rem">{ch['numero']}</strong></td>
              <td><strong>{ch['type_nom']}</strong></td>
              <td>Étage {ch['etage_num']}</td>
              <td>{ch['vue'] or '-'}</td>
              <td>{ch['capacite_adultes']}A + {ch['capacite_enfants']}E</td>
              <td><span class="badge {statut_badge}">{ch['statut']}</span></td>
              <td><span class="badge {proprete_badge}">{ch['etat_proprete']}</span></td>
              <td>
                <a href="/chambres/{ch['id']}" class="btn btn-info btn-sm" title="Voir"><i class="fas fa-eye"></i></a>
                <a href="/chambres/{ch['id']}/modifier" class="btn btn-warning btn-sm" title="Modifier"><i class="fas fa-edit"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-bed"></i><br>Aucune chambre</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='chambres', page_title='Chambres')

    @app.route('/chambres/nouvelle', methods=['GET', 'POST'])
    @directeur_required
    def chambre_nouvelle():
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                c.execute("""INSERT INTO chambres
                    (numero, type_id, etage_id, vue, statut, etat_proprete, notes, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                    (request.form['numero'], int(request.form['type_id']),
                     int(request.form['etage_id']), request.form.get('vue', ''),
                     request.form.get('statut', 'Disponible'),
                     request.form.get('etat_proprete', 'Propre'),
                     request.form.get('notes', '')))
                conn.commit()
                conn.close()
                flash(f"✅ Chambre {request.form['numero']} créée", "success")
                return redirect('/chambres')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom FROM types_chambres WHERE actif=1 ORDER BY ordre")
        types = c.fetchall()
        c.execute("SELECT id, numero, nom FROM etages ORDER BY numero")
        etages = c.fetchall()
        conn.close()

        types_opts = "".join(f'<option value="{t["id"]}">{t["nom"]}</option>' for t in types)
        etages_opts = "".join(f'<option value="{e["id"]}">Étage {e["numero"]} - {e["nom"]}</option>' for e in etages)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-bed"></i> Nouvelle Chambre</h2>
          <a href="/chambres" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Numéro *</label><input type="text" name="numero" required placeholder="101"></div>
              <div class="form-group"><label>Type *</label><select name="type_id" required><option value="">--</option>{types_opts}</select></div>
              <div class="form-group"><label>Étage *</label><select name="etage_id" required><option value="">--</option>{etages_opts}</select></div>
              <div class="form-group"><label>Vue</label>
                <select name="vue">
                  <option value="">--</option>
                  <option>Mer</option><option>Jardin</option>
                  <option>Piscine</option><option>Ville</option>
                  <option>Panoramique</option>
                </select>
              </div>
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  <option value="Disponible">Disponible</option>
                  <option value="Occupée">Occupée</option>
                  <option value="Réservée">Réservée</option>
                  <option value="Maintenance">Maintenance</option>
                  <option value="Hors service">Hors service</option>
                </select>
              </div>
              <div class="form-group"><label>État propreté</label>
                <select name="etat_proprete">
                  <option value="Propre">Propre</option>
                  <option value="À nettoyer">À nettoyer</option>
                  <option value="En cours">En cours</option>
                  <option value="Sale">Sale</option>
                </select>
              </div>
              <div class="form-group form-full"><label>Notes</label><textarea name="notes" rows="2"></textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/chambres" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='chambres', page_title='Nouvelle chambre')

    @app.route('/chambres/<int:cid>')
    @staff_required
    def chambre_detail(cid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT ch.*, tc.nom as type_nom, tc.description as type_desc,
                            tc.equipements, tc.superficie_m2, tc.lit_principal,
                            e.numero as etage_num, e.nom as etage_nom
                     FROM chambres ch
                     JOIN types_chambres tc ON ch.type_id = tc.id
                     JOIN etages e ON ch.etage_id = e.id
                     WHERE ch.id=?""", (cid,))
        ch = c.fetchone()
        if not ch:
            conn.close()
            flash("Chambre introuvable", "danger")
            return redirect('/chambres')

        # Réservation actuelle
        c.execute("""SELECT r.*, cl.nom, cl.prenom, cl.telephone
                     FROM reservations r
                     JOIN clients cl ON r.client_id = cl.id
                     WHERE r.chambre_id = ? AND r.statut IN ('Confirmée', 'En cours')
                       AND date(r.date_arrivee) <= date('now')
                       AND date(r.date_depart) >= date('now')
                     LIMIT 1""", (cid,))
        reservation_actuelle = c.fetchone()

        # Tâches housekeeping
        c.execute("""SELECT * FROM taches_housekeeping WHERE chambre_id = ?
                     ORDER BY date_creation DESC LIMIT 5""", (cid,))
        taches = c.fetchall()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-bed"></i> Chambre {ch['numero']}</h2>
          <div style="display:flex;gap:10px">
            <a href="/chambres/{cid}/modifier" class="btn btn-warning"><i class="fas fa-edit"></i> Modifier</a>
            <a href="/chambres" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-door-open stat-icon"></i>
            <div class="stat-value" style="font-size:1.3rem">Chambre {ch['numero']}</div>
            <div class="stat-label">Numéro</div>
          </div>
          <div class="stat-card gold">
            <i class="fas fa-tag stat-icon"></i>
            <div class="stat-value" style="font-size:1.1rem">{ch['type_nom']}</div>
            <div class="stat-label">Type</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-ruler-combined stat-icon"></i>
            <div class="stat-value">{ch['superficie_m2']:.0f} m²</div>
            <div class="stat-label">Superficie</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-eye stat-icon"></i>
            <div class="stat-value" style="font-size:1.1rem">{ch['vue'] or 'Standard'}</div>
            <div class="stat-label">Vue</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
          <div class="form-grid">
            <div><strong>Étage :</strong> {ch['etage_num']} - {ch['etage_nom'] or ''}</div>
            <div><strong>Lit principal :</strong> {ch['lit_principal'] or '-'}</div>
            <div><strong>Capacité :</strong> {ch['capacite_adultes']} adultes + {ch['capacite_enfants']} enfants</div>
            <div><strong>Statut :</strong> <span class="badge badge-info">{ch['statut']}</span></div>
            <div><strong>Propreté :</strong> <span class="badge badge-success">{ch['etat_proprete']}</span></div>
            <div><strong>Dernière maintenance :</strong> {ch['derniere_maintenance'] or '-'}</div>
          </div>
          {('<p style="margin-top:15px"><strong>Équipements :</strong> ' + ch['equipements'] + '</p>') if ch['equipements'] else ''}
          {('<p style="margin-top:10px"><strong>Notes :</strong> ' + ch['notes'] + '</p>') if ch['notes'] else ''}
        </div>
        """

        if reservation_actuelle:
            content += f"""
            <div class="card" style="border-left:5px solid #10b981">
              <div class="card-header"><h3><i class="fas fa-user-check"></i> Client actuel</h3></div>
              <div class="form-grid">
                <div><strong>Client :</strong> {reservation_actuelle['nom']} {reservation_actuelle['prenom']}</div>
                <div><strong>Téléphone :</strong> {reservation_actuelle['telephone']}</div>
                <div><strong>Réservation :</strong> {reservation_actuelle['numero']}</div>
                <div><strong>Période :</strong> {reservation_actuelle['date_arrivee']} → {reservation_actuelle['date_depart']}</div>
              </div>
            </div>
            """
        else:
            content += '<div class="card"><div class="empty"><i class="fas fa-check-circle" style="color:#10b981"></i><br>Chambre libre actuellement</div></div>'

        if taches:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-broom"></i> Tâches housekeeping récentes</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>N°</th><th>Type</th><th>Priorité</th><th>Statut</th><th>Date</th></tr></thead>
                  <tbody>
            """
            for t in taches:
                content += f"""
                <tr>
                  <td><strong>{t['numero']}</strong></td>
                  <td>{t['type_tache']}</td>
                  <td>{t['priorite']}</td>
                  <td><span class="badge badge-info">{t['statut']}</span></td>
                  <td>{t['date_creation'][:16]}</td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        return render_page(content, active='chambres', page_title=f"Chambre {ch['numero']}")

    @app.route('/chambres/<int:cid>/modifier', methods=['GET', 'POST'])
    @directeur_required
    def chambre_modifier(cid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE chambres SET
                    numero=?, type_id=?, etage_id=?, vue=?, statut=?,
                    etat_proprete=?, notes=? WHERE id=?""",
                    (request.form['numero'], int(request.form['type_id']),
                     int(request.form['etage_id']), request.form.get('vue', ''),
                     request.form.get('statut', 'Disponible'),
                     request.form.get('etat_proprete', 'Propre'),
                     request.form.get('notes', ''), cid))
                conn.commit()
                conn.close()
                flash("✅ Chambre mise à jour", "success")
                return redirect(f'/chambres/{cid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM chambres WHERE id=?", (cid,))
        ch = c.fetchone()
        c.execute("SELECT id, nom FROM types_chambres WHERE actif=1 ORDER BY ordre")
        types = c.fetchall()
        c.execute("SELECT id, numero, nom FROM etages ORDER BY numero")
        etages = c.fetchall()
        conn.close()

        types_opts = "".join(f'<option value="{t["id"]}" {"selected" if t["id"]==ch["type_id"] else ""}>{t["nom"]}</option>' for t in types)
        etages_opts = "".join(f'<option value="{e["id"]}" {"selected" if e["id"]==ch["etage_id"] else ""}>Étage {e["numero"]}</option>' for e in etages)
        statuts = ['Disponible', 'Occupée', 'Réservée', 'Maintenance', 'Hors service']
        proprete = ['Propre', 'À nettoyer', 'En cours', 'Sale']

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-edit"></i> Modifier Chambre {ch['numero']}</h2>
          <a href="/chambres/{cid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Numéro *</label><input type="text" name="numero" value="{ch['numero']}" required></div>
              <div class="form-group"><label>Type *</label><select name="type_id" required>{types_opts}</select></div>
              <div class="form-group"><label>Étage *</label><select name="etage_id" required>{etages_opts}</select></div>
              <div class="form-group"><label>Vue</label>
                <select name="vue">
                  <option value="">--</option>
                  {''.join(f'<option {"selected" if ch["vue"]==v else ""}>{v}</option>' for v in ["Mer", "Jardin", "Piscine", "Ville", "Panoramique"])}
                </select>
              </div>
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  {''.join(f'<option value="{s}" {"selected" if ch["statut"]==s else ""}>{s}</option>' for s in statuts)}
                </select>
              </div>
              <div class="form-group"><label>Propreté</label>
                <select name="etat_proprete">
                  {''.join(f'<option value="{p}" {"selected" if ch["etat_proprete"]==p else ""}>{p}</option>' for p in proprete)}
                </select>
              </div>
              <div class="form-group form-full"><label>Notes</label><textarea name="notes" rows="2">{ch['notes'] or ''}</textarea></div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/chambres/{cid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/chambres/{cid}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='chambres', page_title='Modifier chambre')

    @app.route('/chambres/<int:cid>/supprimer')
    @admin_required
    def chambre_supprimer(cid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE chambres SET actif=0 WHERE id=?", (cid,))
            conn.commit()
            conn.close()
            if current_user:
                log_action(current_user.id, 'DELETE_CHAMBRE', f'ID {cid}')
            flash("✅ Chambre archivée", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/chambres')

    print("[CRUD] ✅ Routes chambres enregistrées")

    # ==================== CLIENTS ====================
    @app.route('/clients')
    @reception_required
    def clients_liste():
        conn = get_db()
        c = conn.cursor()

        search = request.args.get('q', '').strip()
        type_filter = request.args.get('type', '')
        vip_filter = request.args.get('vip', '')

        query = "SELECT * FROM clients WHERE actif=1"
        params = []

        if search:
            query += """ AND (nom LIKE ? OR prenom LIKE ? OR telephone LIKE ?
                        OR email LIKE ? OR code LIKE ? OR societe LIKE ?)"""
            params.extend([f'%{search}%'] * 6)

        if type_filter:
            query += " AND type_client = ?"
            params.append(type_filter)

        if vip_filter == 'vip':
            query += " AND vip = 1"

        query += " ORDER BY nom"
        c.execute(query, params)
        rows = c.fetchall()

        c.execute("SELECT COUNT(*) FROM clients WHERE actif=1")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM clients WHERE actif=1 AND vip=1")
        nb_vip = c.fetchone()[0]
        conn.close()

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-users"></i> Clients</h2>
            <div class="page-subtitle">{len(rows)} client(s) · {nb_vip} VIP</div>
          </div>
          <a href="/clients/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau client</a>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-users stat-icon"></i>
            <div class="stat-value">{total}</div>
            <div class="stat-label">Total clients</div>
          </div>
          <div class="stat-card gold">
            <i class="fas fa-crown stat-icon"></i>
            <div class="stat-value">{nb_vip}</div>
            <div class="stat-label">Clients VIP</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> Liste des clients</h3>
            <form method="GET" style="display:flex;gap:8px;flex-wrap:wrap">
              <input type="text" name="q" value="{search}" placeholder="Rechercher..." style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px;width:200px">
              <select name="type" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous types</option>
                <option value="Particulier" {"selected" if type_filter == "Particulier" else ""}>Particulier</option>
                <option value="Entreprise" {"selected" if type_filter == "Entreprise" else ""}>Entreprise</option>
              </select>
              <select name="vip" style="padding:8px 12px;border:2px solid #f1f5f9;border-radius:8px">
                <option value="">Tous</option>
                <option value="vip" {"selected" if vip_filter == "vip" else ""}>VIP uniquement</option>
              </select>
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Code</th><th>Nom</th><th>Type</th><th>Contact</th>
                  <th>Ville/Pays</th><th>Séjours</th><th>CA total</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
        """
        for cl in rows:
            vip_badge = '<span class="badge badge-vip"><i class="fas fa-crown"></i> VIP</span>' if cl['vip'] else ''
            type_badge = 'badge-info' if cl['type_client'] == 'Entreprise' else 'badge-primary'

            content += f"""
            <tr>
              <td><strong>{cl['code']}</strong></td>
              <td>
                {vip_badge}
                <strong>{cl['nom']} {cl['prenom'] or ''}</strong>
                {f'<br><small style="color:#94a3b8">{cl["societe"]}</small>' if cl['societe'] else ''}
              </td>
              <td><span class="badge {type_badge}">{cl['type_client']}</span></td>
              <td>
                <i class="fas fa-phone" style="color:#d97706"></i> {cl['telephone']}<br>
                <small style="color:#94a3b8">{cl['email'] or '-'}</small>
              </td>
              <td>{cl['ville'] or '-'}<br><small>{cl['pays'] or ''}</small></td>
              <td><span class="badge badge-gold">{cl['nb_sejours']}</span></td>
              <td><strong style="color:#92400e">{cl['total_depense']:,.0f}</strong> FCFA</td>
              <td>
                <a href="/clients/{cl['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
                <a href="/clients/{cl['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a>
              </td>
            </tr>
            """
        if not rows:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-users"></i><br>Aucun client</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='clients', page_title='Clients')

    @app.route('/clients/nouveau', methods=['GET', 'POST'])
    @reception_required
    def client_nouveau():
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                code = request.form.get('code') or gen_code('CLI', 'clients')
                c.execute("""INSERT INTO clients
                    (code, type_client, civilite, nom, prenom, date_naissance, nationalite, sexe,
                     piece_type, piece_numero, telephone, telephone_secondaire, email,
                     adresse, ville, pays, societe, numero_tva, preferences, allergies, vip, notes, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (code, request.form.get('type_client', 'Particulier'),
                     request.form.get('civilite', ''), request.form['nom'],
                     request.form.get('prenom', ''), request.form.get('date_naissance') or None,
                     request.form.get('nationalite', 'Sénégalaise'),
                     request.form.get('sexe', ''),
                     request.form.get('piece_type', ''), request.form.get('piece_numero', ''),
                     request.form['telephone'], request.form.get('telephone_secondaire', ''),
                     request.form.get('email', ''),
                     request.form.get('adresse', ''), request.form.get('ville', ''),
                     request.form.get('pays', 'Sénégal'),
                     request.form.get('societe', ''), request.form.get('numero_tva', ''),
                     request.form.get('preferences', ''), request.form.get('allergies', ''),
                     1 if request.form.get('vip') else 0,
                     request.form.get('notes', '')))
                conn.commit()
                cli_id = c.lastrowid
                conn.close()
                flash(f"✅ Client {code} créé", "success")
                return redirect(f'/clients/{cli_id}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = """
        <div class="page-header">
          <h2><i class="fas fa-user-plus"></i> Nouveau Client</h2>
          <a href="/clients" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <h3 style="margin-bottom:20px;color:#92400e"><i class="fas fa-user"></i> Informations</h3>
            <div class="form-grid">
              <div class="form-group"><label>Type de client *</label>
                <select name="type_client" required>
                  <option value="Particulier">Particulier</option>
                  <option value="Entreprise">Entreprise</option>
                </select>
              </div>
              <div class="form-group"><label>Civilité</label>
                <select name="civilite">
                  <option value="">--</option>
                  <option>M.</option><option>Mme</option><option>Mlle</option>
                </select>
              </div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group"><label>Prénom</label><input type="text" name="prenom"></div>
              <div class="form-group"><label>Date naissance</label><input type="date" name="date_naissance"></div>
              <div class="form-group"><label>Sexe</label>
                <select name="sexe">
                  <option value="">--</option>
                  <option value="M">Masculin</option>
                  <option value="F">Féminin</option>
                </select>
              </div>
              <div class="form-group"><label>Nationalité</label><input type="text" name="nationalite" value="Sénégalaise"></div>
              <div class="form-group"><label>Type pièce</label>
                <select name="piece_type">
                  <option value="">--</option>
                  <option>CNI</option><option>Passeport</option>
                  <option>Permis</option><option>Carte séjour</option>
                </select>
              </div>
              <div class="form-group"><label>Numéro pièce</label><input type="text" name="piece_numero"></div>
              <div class="form-group"><label>SOCIÉTÉ (si entreprise)</label><input type="text" name="societe"></div>
              <div class="form-group"><label>N° TVA</label><input type="text" name="numero_tva"></div>
            </div>

            <h3 style="margin:25px 0 20px;color:#92400e"><i class="fas fa-phone"></i> Contact</h3>
            <div class="form-grid">
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" required></div>
              <div class="form-group"><label>Téléphone 2</label><input type="tel" name="telephone_secondaire"></div>
              <div class="form-group"><label>Email</label><input type="email" name="email"></div>
              <div class="form-group"><label>Adresse</label><input type="text" name="adresse"></div>
              <div class="form-group"><label>Ville</label><input type="text" name="ville" value="Dakar"></div>
              <div class="form-group"><label>Pays</label><input type="text" name="pays" value="Sénégal"></div>
            </div>

            <h3 style="margin:25px 0 20px;color:#92400e"><i class="fas fa-star"></i> Préférences</h3>
            <div class="form-grid">
              <div class="form-group form-full"><label>Préférences (chambre, étage...)</label><textarea name="preferences" rows="2"></textarea></div>
              <div class="form-group form-full"><label>Allergies</label><textarea name="allergies" rows="2"></textarea></div>
              <div class="form-group form-full"><label>Notes</label><textarea name="notes" rows="2"></textarea></div>
              <div class="form-group" style="display:flex;align-items:center;gap:8px">
                <input type="checkbox" name="vip" style="width:auto">
                <label style="margin:0">Client VIP</label>
              </div>
            </div>

            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/clients" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='clients', page_title='Nouveau client')

    @app.route('/clients/<int:cid>')
    @reception_required
    def client_detail(cid):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM clients WHERE id=?", (cid,))
        cl = c.fetchone()
        if not cl:
            conn.close()
            flash("Client introuvable", "danger")
            return redirect('/clients')

        # Historique réservations
        c.execute("""SELECT r.*, ch.numero as chambre_numero, tc.nom as type_nom
                     FROM reservations r
                     LEFT JOIN chambres ch ON r.chambre_id = ch.id
                     JOIN types_chambres tc ON r.type_chambre_id = tc.id
                     WHERE r.client_id = ?
                     ORDER BY r.date_arrivee DESC""", (cid,))
        reservations = c.fetchall()

        # Factures
        c.execute("SELECT * FROM factures WHERE client_id = ? ORDER BY date_facture DESC", (cid,))
        factures = c.fetchall()
        conn.close()

        vip_badge = '<span class="badge badge-vip"><i class="fas fa-crown"></i> VIP</span>' if cl['vip'] else ''

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user"></i> {cl['nom']} {cl['prenom'] or ''} {vip_badge}</h2>
          <div style="display:flex;gap:10px">
            <a href="/reservations/nouvelle?client_id={cid}" class="btn btn-gold"><i class="fas fa-calendar-plus"></i> Nouvelle réservation</a>
            <a href="/clients/{cid}/modifier" class="btn btn-warning"><i class="fas fa-edit"></i> Modifier</a>
            <a href="/clients" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-id-card stat-icon"></i>
            <div class="stat-value" style="font-size:1.2rem">{cl['code']}</div>
            <div class="stat-label">Code client</div>
          </div>
          <div class="stat-card gold">
            <i class="fas fa-bed stat-icon"></i>
            <div class="stat-value">{cl['nb_sejours']}</div>
            <div class="stat-label">Séjours</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-coins stat-icon"></i>
            <div class="stat-value">{cl['total_depense']:,.0f}</div>
            <div class="stat-label">CA total (FCFA)</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-star stat-icon"></i>
            <div class="stat-value">{cl['points_fidelite']}</div>
            <div class="stat-label">Points fidélité</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
          <div class="form-grid">
            <div><strong>Type :</strong> {cl['type_client']}</div>
            <div><strong>Civilité :</strong> {cl['civilite'] or '-'}</div>
            <div><strong>Nom complet :</strong> {cl['nom']} {cl['prenom'] or ''}</div>
            <div><strong>Date naissance :</strong> {cl['date_naissance'] or '-'}</div>
            <div><strong>Nationalité :</strong> {cl['nationalite'] or '-'}</div>
            <div><strong>Pièce :</strong> {cl['piece_type'] or ''} {cl['piece_numero'] or ''}</div>
            <div><strong>Téléphone :</strong> {cl['telephone']}</div>
            <div><strong>Téléphone 2 :</strong> {cl['telephone_secondaire'] or '-'}</div>
            <div><strong>Email :</strong> {cl['email'] or '-'}</div>
            <div><strong>Adresse :</strong> {cl['adresse'] or '-'}</div>
            <div><strong>Ville :</strong> {cl['ville'] or '-'}</div>
            <div><strong>Pays :</strong> {cl['pays'] or '-'}</div>
            <div><strong>Société :</strong> {cl['societe'] or '-'}</div>
            <div><strong>N° TVA :</strong> {cl['numero_tva'] or '-'}</div>
          </div>
          {('<p style="margin-top:15px;padding:12px;background:#fffbeb;border-radius:10px;border-left:4px solid #d97706"><strong>⭐ Préférences :</strong> ' + cl['preferences'] + '</p>') if cl['preferences'] else ''}
          {('<p style="margin-top:10px;padding:12px;background:#fee2e2;border-radius:10px;border-left:4px solid #dc2626"><strong>⚠️ Allergies :</strong> ' + cl['allergies'] + '</p>') if cl['allergies'] else ''}
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-history"></i> Historique des séjours ({len(reservations)})</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Chambre</th><th>Type</th><th>Arrivée</th><th>Départ</th><th>Nuits</th><th>Total</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for r in reservations:
            badge = 'badge-success' if r['statut'] == 'Confirmée' else 'badge-info'
            content += f"""
            <tr>
              <td><strong>{r['numero']}</strong></td>
              <td>{r['chambre_numero'] or '-'}</td>
              <td>{r['type_nom']}</td>
              <td>{r['date_arrivee']}</td>
              <td>{r['date_depart']}</td>
              <td>{r['nb_nuits']}j</td>
              <td><strong>{r['total']:,.0f}</strong> FCFA</td>
              <td><span class="badge {badge}">{r['statut']}</span></td>
            </tr>
            """
        if not reservations:
            content += '<tr><td colspan="8" class="empty">Aucune réservation</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='clients', page_title=f"{cl['nom']} {cl['prenom'] or ''}")

    @app.route('/clients/<int:cid>/modifier', methods=['GET', 'POST'])
    @reception_required
    def client_modifier(cid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE clients SET
                    type_client=?, civilite=?, nom=?, prenom=?, date_naissance=?, nationalite=?, sexe=?,
                    piece_type=?, piece_numero=?, telephone=?, telephone_secondaire=?, email=?,
                    adresse=?, ville=?, pays=?, societe=?, numero_tva=?, preferences=?, allergies=?,
                    vip=?, notes=? WHERE id=?""",
                    (request.form.get('type_client', 'Particulier'),
                     request.form.get('civilite', ''), request.form['nom'],
                     request.form.get('prenom', ''), request.form.get('date_naissance') or None,
                     request.form.get('nationalite', 'Sénégalaise'), request.form.get('sexe', ''),
                     request.form.get('piece_type', ''), request.form.get('piece_numero', ''),
                     request.form['telephone'], request.form.get('telephone_secondaire', ''),
                     request.form.get('email', ''),
                     request.form.get('adresse', ''), request.form.get('ville', ''),
                     request.form.get('pays', 'Sénégal'),
                     request.form.get('societe', ''), request.form.get('numero_tva', ''),
                     request.form.get('preferences', ''), request.form.get('allergies', ''),
                     1 if request.form.get('vip') else 0,
                     request.form.get('notes', ''), cid))
                conn.commit()
                conn.close()
                flash("✅ Client mis à jour", "success")
                return redirect(f'/clients/{cid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM clients WHERE id=?", (cid,))
        cl = c.fetchone()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user-edit"></i> Modifier {cl['nom']} {cl['prenom'] or ''}</h2>
          <a href="/clients/{cid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Type</label>
                <select name="type_client">
                  {''.join(f'<option value="{t}" {"selected" if cl["type_client"]==t else ""}>{t}</option>' for t in ["Particulier", "Entreprise"])}
                </select>
              </div>
              <div class="form-group"><label>Civilité</label>
                <select name="civilite">
                  <option value="">--</option>
                  {''.join(f'<option {"selected" if cl["civilite"]==c_ else ""}>{c_}</option>' for c_ in ["M.", "Mme", "Mlle"])}
                </select>
              </div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{cl['nom']}" required></div>
              <div class="form-group"><label>Prénom</label><input type="text" name="prenom" value="{cl['prenom'] or ''}"></div>
              <div class="form-group"><label>Date naissance</label><input type="date" name="date_naissance" value="{cl['date_naissance'] or ''}"></div>
              <div class="form-group"><label>Sexe</label>
                <select name="sexe">
                  <option value="">--</option>
                  <option value="M" {"selected" if cl['sexe']=='M' else ""}>Masculin</option>
                  <option value="F" {"selected" if cl['sexe']=='F' else ""}>Féminin</option>
                </select>
              </div>
              <div class="form-group"><label>Nationalité</label><input type="text" name="nationalite" value="{cl['nationalite'] or ''}"></div>
              <div class="form-group"><label>Type pièce</label>
                <select name="piece_type">
                  <option value="">--</option>
                  {''.join(f'<option {"selected" if cl["piece_type"]==p else ""}>{p}</option>' for p in ["CNI", "Passeport", "Permis", "Carte séjour"])}
                </select>
              </div>
              <div class="form-group"><label>N° pièce</label><input type="text" name="piece_numero" value="{cl['piece_numero'] or ''}"></div>
              <div class="form-group"><label>Société</label><input type="text" name="societe" value="{cl['societe'] or ''}"></div>
              <div class="form-group"><label>N° TVA</label><input type="text" name="numero_tva" value="{cl['numero_tva'] or ''}"></div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" value="{cl['telephone']}" required></div>
              <div class="form-group"><label>Téléphone 2</label><input type="tel" name="telephone_secondaire" value="{cl['telephone_secondaire'] or ''}"></div>
              <div class="form-group"><label>Email</label><input type="email" name="email" value="{cl['email'] or ''}"></div>
              <div class="form-group"><label>Adresse</label><input type="text" name="adresse" value="{cl['adresse'] or ''}"></div>
              <div class="form-group"><label>Ville</label><input type="text" name="ville" value="{cl['ville'] or ''}"></div>
              <div class="form-group"><label>Pays</label><input type="text" name="pays" value="{cl['pays'] or ''}"></div>
              <div class="form-group form-full"><label>Préférences</label><textarea name="preferences" rows="2">{cl['preferences'] or ''}</textarea></div>
              <div class="form-group form-full"><label>Allergies</label><textarea name="allergies" rows="2">{cl['allergies'] or ''}</textarea></div>
              <div class="form-group form-full"><label>Notes</label><textarea name="notes" rows="2">{cl['notes'] or ''}</textarea></div>
              <div class="form-group" style="display:flex;align-items:center;gap:8px">
                <input type="checkbox" name="vip" style="width:auto" {"checked" if cl['vip'] else ""}>
                <label style="margin:0">Client VIP</label>
              </div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/clients/{cid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='clients', page_title='Modifier client')

    print("[CRUD] ✅ Routes clients enregistrées")

    # ==================== TYPES DE CHAMBRES ====================
    @app.route('/types-chambres')
    @directeur_required
    def types_chambres_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT tc.*,
                     (SELECT COUNT(*) FROM chambres WHERE type_id = tc.id AND actif=1) as nb_chambres
                     FROM types_chambres tc WHERE tc.actif=1 ORDER BY tc.ordre""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-tags"></i> Types de chambres</h2>
            <div class="page-subtitle">Catégories de chambres de l'établissement</div>
          </div>
          <a href="/types-chambres/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau type</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Type</th><th>Capacité</th><th>Superficie</th><th>Lit</th><th>Chambres</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for t in rows:
            content += f"""
            <tr>
              <td><strong>{t['code']}</strong></td>
              <td>
                <strong>{t['nom']}</strong><br>
                <small style="color:#94a3b8">{t['description'] or ''}</small>
              </td>
              <td>{t['capacite_adultes']}A + {t['capacite_enfants']}E</td>
              <td>{t['superficie_m2']:.0f} m²</td>
              <td>{t['lit_principal'] or '-'} × {t['nb_lits']}</td>
              <td><span class="badge badge-gold">{t['nb_chambres']}</span></td>
              <td>
                <a href="/types-chambres/{t['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a>
              </td>
            </tr>
            """
        content += "</tbody></table></div></div>"
        return render_page(content, active='chambres', page_title='Types de chambres')

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
            <div class="page-subtitle">Gestion des accès et rôles</div>
          </div>
          <a href="/utilisateurs/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvel utilisateur</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Username</th><th>Nom</th><th>Contact</th><th>Rôle</th><th>Dernière connexion</th><th>Statut</th><th>Actions</th></tr></thead>
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
              <td>{u['dernier_login'][:16] if u['dernier_login'] else 'Jamais'}</td>
              <td><span class="badge {statut_badge}">{'Actif' if u['actif'] else 'Inactif'}</span></td>
              <td>
                <a href="/utilisateurs/{u['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i></a>
              </td>
            </tr>
            """
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
                    (username, password_hash, nom, prenom, email, telephone, role, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                    (request.form['username'], h, request.form['nom'],
                     request.form['prenom'], request.form.get('email', ''),
                     request.form.get('telephone', ''), request.form['role']))
                conn.commit()
                conn.close()
                flash(f"✅ Utilisateur {request.form['username']} créé", "success")
                return redirect('/utilisateurs')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = """
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
                  <option value="femme_chambre">Femme de chambre</option>
                  <option value="gouvernante">Gouvernante</option>
                  <option value="receptionniste">Réceptionniste</option>
                  <option value="directeur">Directeur</option>
                  <option value="admin">Administrateur</option>
                </select>
              </div>
            </div>
            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/utilisateurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='utilisateurs', page_title='Nouvel utilisateur')

    print("[CRUD] ✅ Routes utilisateurs enregistrées")
