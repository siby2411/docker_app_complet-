"""
Portail Directeur + Réception + Gouvernante
Vues personnalisées par rôle + planning chambres
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


def register_portail_routes(app, render_page):
    """Portails par rôle Hôtel"""

    # ==================== PORTAIL DIRECTEUR ====================
    @app.route('/directeur/accueil')
    @directeur_required
    def directeur_accueil():
        conn = get_db()
        c = conn.cursor()

        # KPIs stratégiques
        c.execute("SELECT COUNT(*) FROM chambres WHERE actif=1")
        total_chambres = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM sejours WHERE statut='En cours'")
        occupees = c.fetchone()[0]

        taux_occ = (occupees / total_chambres * 100) if total_chambres else 0

        # CA du mois
        c.execute("""SELECT COALESCE(SUM(montant), 0) FROM paiements
                     WHERE strftime('%Y-%m', date_paiement) = strftime('%Y-%m', 'now')""")
        ca_mois = c.fetchone()[0]

        # CA par département
        c.execute("""SELECT COALESCE(SUM(sous_total_hebergement), 0),
                            COALESCE(SUM(sous_total_resto), 0),
                            COALESCE(SUM(sous_total_services), 0)
                     FROM factures
                     WHERE strftime('%Y-%m', date_facture) = strftime('%Y-%m', 'now')""")
        ca_departements = c.fetchone()

        # ADR et RevPAR
        c.execute("""SELECT COALESCE(AVG(tarif_nuit), 0) FROM reservations
                     WHERE statut IN ('Confirmée', 'En cours', 'Terminée')
                     AND strftime('%Y-%m', date_arrivee) = strftime('%Y-%m', 'now')""")
        adr = c.fetchone()[0]

        # Impayés
        c.execute("""SELECT COALESCE(SUM(total - montant_paye), 0)
                     FROM factures WHERE statut != 'Payé'""")
        impayes = c.fetchone()[0]

        # Réservations à venir
        c.execute("""SELECT COUNT(*) FROM reservations
                     WHERE statut IN ('Confirmée', 'En attente')
                     AND date_arrivee >= date('now')""")
        res_a_venir = c.fetchone()[0]

        # Top 5 clients
        c.execute("""SELECT nom, prenom, societe, nb_sejours, total_depense
                     FROM clients WHERE nb_sejours > 0
                     ORDER BY total_depense DESC LIMIT 5""")
        top_clients = c.fetchall()

        # Effectif en cours
        c.execute("SELECT COUNT(*) FROM utilisateurs WHERE actif=1")
        nb_employes = c.fetchone()[0]

        # Taux occupation par jour (7 derniers)
        c.execute("""SELECT date(date_checkin) as jour, COUNT(*) as nb
                     FROM sejours
                     WHERE date_checkin >= date('now', '-7 days')
                     GROUP BY jour ORDER BY jour""")
        occupation_jours = c.fetchall()

        # Sources de réservation
        c.execute("""SELECT source, COUNT(*) as nb, COALESCE(SUM(total), 0) as ca
                     FROM reservations
                     WHERE strftime('%Y-%m', date_arrivee) = strftime('%Y-%m', 'now')
                     GROUP BY source ORDER BY ca DESC""")
        par_source = c.fetchall()

        conn.close()

        content = f"""
        <div class="hero" style="background:linear-gradient(135deg,#451a03,#92400e)">
          <div class="stars">★★★★★</div>
          <h1>Bonjour <span>{current_user.prenom}</span> 👋</h1>
          <p>Espace Directeur — Pilotage stratégique de l'établissement</p>
        </div>

        <div class="kpi-grid">
          <div class="kpi-card" style="border-top-color:#10b981">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#10b981,#22c55e)">
              <i class="fas fa-percentage"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Taux d'occupation</div>
              <div class="kpi-value">{taux_occ:.1f}%</div>
              <div class="kpi-sub">{occupees} / {total_chambres} chambres</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#d97706">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#92400e,#d97706)">
              <i class="fas fa-coins"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">CA du mois</div>
              <div class="kpi-value">{ca_mois:,.0f}</div>
              <div class="kpi-sub">FCFA</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#0891b2">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#0891b2,#06b6d4)">
              <i class="fas fa-tag"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">ADR (Tarif moyen)</div>
              <div class="kpi-value">{adr:,.0f}</div>
              <div class="kpi-sub">FCFA / nuit</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#dc2626">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#dc2626,#ef4444)">
              <i class="fas fa-exclamation-triangle"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Impayés</div>
              <div class="kpi-value">{impayes:,.0f}</div>
              <div class="kpi-sub">FCFA</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#7c3aed">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#7c3aed,#a855f7)">
              <i class="fas fa-calendar-check"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Réservations à venir</div>
              <div class="kpi-value">{res_a_venir}</div>
              <div class="kpi-sub">Confirmées</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#fbbf24">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#d97706,#fbbf24)">
              <i class="fas fa-users"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Équipe</div>
              <div class="kpi-value">{nb_employes}</div>
              <div class="kpi-sub">Employés actifs</div>
            </div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="card">
            <div class="card-header"><h3><i class="fas fa-chart-pie"></i> CA par département (mois)</h3></div>
        """
        if ca_departements:
            total_ca = sum([ca_departements[0], ca_departements[1], ca_departements[2]])
            for label, val, color, icon in [
                ('Hébergement', ca_departements[0], '#d97706', 'fa-bed'),
                ('Restaurant', ca_departements[1], '#10b981', 'fa-utensils'),
                ('Services', ca_departements[2], '#0891b2', 'fa-concierge-bell'),
            ]:
                pct = (val / total_ca * 100) if total_ca else 0
                content += f"""
                <div style="margin-bottom:15px">
                  <div style="display:flex;justify-content:space-between;margin-bottom:5px">
                    <span style="font-weight:700;font-size:0.9rem">
                      <i class="fas {icon}" style="color:{color}"></i> {label}
                    </span>
                    <strong style="color:{color}">{val:,.0f} FCFA ({pct:.0f}%)</strong>
                  </div>
                  <div style="background:#fffbeb;border-radius:6px;height:12px;overflow:hidden">
                    <div style="background:{color};height:100%;width:{pct}%"></div>
                  </div>
                </div>
                """
        content += "</div>"

        content += """
          <div class="card">
            <div class="card-header"><h3><i class="fas fa-globe"></i> Sources de réservation</h3></div>
        """
        for s in par_source:
            content += f"""
            <div style="display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px dashed #fffbeb">
              <span style="font-weight:700">{s['source'] or 'Direct'}</span>
              <div style="text-align:right">
                <strong style="color:#92400e;display:block">{s['ca']:,.0f} FCFA</strong>
                <small style="color:#94a3b8">{s['nb']} réservation(s)</small>
              </div>
            </div>
            """
        if not par_source:
            content += '<div class="empty" style="padding:20px">Aucune donnée</div>'
        content += "</div></div>"

        if top_clients:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-crown"></i> Top 5 clients</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>#</th><th>Client</th><th>Séjours</th><th>CA</th></tr></thead>
                  <tbody>
            """
            for i, cl in enumerate(top_clients, 1):
                medal = '🥇' if i == 1 else ('🥈' if i == 2 else ('🥉' if i == 3 else ''))
                content += f"""
                <tr>
                  <td><strong>{medal} {i}</strong></td>
                  <td>{cl['nom']} {cl['prenom'] or ''}<br><small style="color:#94a3b8">{cl['societe'] or ''}</small></td>
                  <td><span class="badge badge-gold">{cl['nb_sejours']}</span></td>
                  <td><strong style="color:#92400e">{cl['total_depense']:,.0f}</strong> FCFA</td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        return render_page(content, active='directeur', page_title='Espace Directeur')

    print("[PORTAIL] ✅ Routes directeur enregistrées")

    # ==================== PORTAIL RÉCEPTION ====================
    @app.route('/reception/accueil')
    @reception_required
    def reception_accueil():
        conn = get_db()
        c = conn.cursor()

        today = datetime.now().date().isoformat()

        # Arrivées du jour
        c.execute("""SELECT r.*, cl.nom, cl.prenom, cl.telephone, cl.vip,
                            ch.numero as chambre_numero, tc.nom as type_nom
                     FROM reservations r
                     JOIN clients cl ON r.client_id = cl.id
                     LEFT JOIN chambres ch ON r.chambre_id = ch.id
                     JOIN types_chambres tc ON r.type_chambre_id = tc.id
                     WHERE date(r.date_arrivee) = ?
                       AND r.statut IN ('Confirmée', 'En attente')
                     ORDER BY r.date_arrivee""", (today,))
        arrivees = c.fetchall()

        # Départs du jour
        c.execute("""SELECT s.*, cl.nom, cl.prenom, ch.numero as chambre_numero,
                            r.numero as res_numero
                     FROM sejours s
                     JOIN clients cl ON s.client_id = cl.id
                     JOIN chambres ch ON s.chambre_id = ch.id
                     JOIN reservations r ON s.reservation_id = r.id
                     WHERE s.statut='En cours'
                       AND date(r.date_depart) <= ?
                     ORDER BY r.date_depart""", (today,))
        departs = c.fetchall()

        # Chambres disponibles
        c.execute("""SELECT ch.*, tc.nom as type_nom
                     FROM chambres ch
                     JOIN types_chambres tc ON ch.type_id = tc.id
                     WHERE ch.actif=1 AND ch.statut='Disponible'
                     ORDER BY ch.numero LIMIT 20""")
        chambres_dispo = c.fetchall()

        # Réservations du jour (nouvelles)
        c.execute("""SELECT COUNT(*) FROM reservations
                     WHERE date(created_at) = ?""", (today,))
        nouvelles_res = c.fetchone()[0]

        # Check-ins faits
        c.execute("""SELECT COUNT(*) FROM sejours WHERE date(date_checkin) = ?""", (today,))
        checkins_faits = c.fetchone()[0]

        # Encaissements du jour
        c.execute("""SELECT COALESCE(SUM(montant), 0) FROM paiements
                     WHERE date(date_paiement) = ?""", (today,))
        encaissements = c.fetchone()[0]

        conn.close()

        content = f"""
        <div class="hero" style="background:linear-gradient(135deg,#0891b2,#06b6d4)">
          <h1>Bonjour <span>{current_user.prenom}</span> 👋</h1>
          <p>Espace Réception — Opérations du jour</p>
        </div>

        <div class="stats">
          <div class="stat-card green">
            <i class="fas fa-plane-arrival stat-icon"></i>
            <div class="stat-value">{len(arrivees)}</div>
            <div class="stat-label">Arrivées prévues</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-plane-departure stat-icon"></i>
            <div class="stat-value">{len(departs)}</div>
            <div class="stat-label">Départs prévus</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-door-open stat-icon"></i>
            <div class="stat-value">{len(chambres_dispo)}</div>
            <div class="stat-label">Chambres disponibles</div>
          </div>
          <div class="stat-card">
            <i class="fas fa-money-bill-wave stat-icon"></i>
            <div class="stat-value">{encaissements:,.0f}</div>
            <div class="stat-label">Encaissé (FCFA)</div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:25px">
          <a href="/reservations/nouvelle" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:30px;border-left:5px solid #d97706;cursor:pointer">
              <i class="fas fa-calendar-plus" style="font-size:2.5rem;color:#d97706;margin-bottom:15px"></i>
              <div style="font-size:1.1rem;font-weight:900;color:#451a03">Nouvelle réservation</div>
              <div style="color:#64748b;font-size:0.85rem;margin-top:5px">Enregistrer un nouveau client</div>
            </div>
          </a>
          <a href="/sejours" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:30px;border-left:5px solid #10b981;cursor:pointer">
              <i class="fas fa-sign-out-alt" style="font-size:2.5rem;color:#10b981;margin-bottom:15px"></i>
              <div style="font-size:1.1rem;font-weight:900;color:#451a03">Check-out en cours</div>
              <div style="color:#64748b;font-size:0.85rem;margin-top:5px">{len(departs)} séjour(s) à clôturer</div>
            </div>
          </a>
        </div>

        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-plane-arrival"></i> Arrivées du jour ({len(arrivees)})</h3>
            <a href="/reservations" class="btn btn-primary btn-sm">Voir tout</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Client</th><th>Chambre</th><th>Type</th><th>Nuits</th><th>Total</th><th>Solde</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for r in arrivees:
            vip = '<span class="badge badge-vip"><i class="fas fa-crown"></i></span> ' if r['vip'] else ''
            content += f"""
            <tr>
              <td><strong>{r['numero']}</strong></td>
              <td>{vip}{r['nom']} {r['prenom']}<br><small style="color:#94a3b8">{r['telephone']}</small></td>
              <td>{r['chambre_numero'] or 'À attribuer'}</td>
              <td>{r['type_nom']}</td>
              <td>{r['nb_nuits']}j</td>
              <td><strong style="color:#92400e">{r['total']:,.0f}</strong> FCFA</td>
              <td><strong style="color:#dc2626">{r['solde']:,.0f}</strong></td>
              <td>
                {f'<a href="/sejours/checkin/{r["id"]}" class="btn btn-success btn-sm"><i class="fas fa-check"></i> Check-in</a>' if r['chambre_id'] else f'<a href="/reservations/{r["id"]}" class="btn btn-warning btn-sm"><i class="fas fa-bed"></i> Attribuer</a>'}
              </td>
            </tr>
            """
        if not arrivees:
            content += '<tr><td colspan="8" class="empty"><i class="fas fa-check-circle" style="color:#10b981"></i><br>Aucune arrivée prévue aujourd\'hui 🎉</td></tr>'
        content += "</tbody></table></div></div>"

        if departs:
            content += """
            <div class="card">
              <div class="card-header">
                <h3><i class="fas fa-plane-departure"></i> Départs à traiter</h3>
              </div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Client</th><th>Chambre</th><th>Check-in</th><th>Réservation</th><th>Actions</th></tr></thead>
                  <tbody>
            """
            for d in departs:
                content += f"""
                <tr>
                  <td><strong>{d['nom']} {d['prenom']}</strong></td>
                  <td><span class="badge badge-gold">Ch. {d['chambre_numero']}</span></td>
                  <td>{d['date_checkin'][:10]}</td>
                  <td>{d['res_numero']}</td>
                  <td>
                    <a href="/sejours/checkout/{d['id']}" class="btn btn-warning btn-sm"><i class="fas fa-sign-out-alt"></i> Check-out</a>
                  </td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        return render_page(content, active='reception', page_title='Espace Réception')

    print("[PORTAIL] ✅ Routes réception enregistrées")

    # ==================== PORTAIL GOUVERNANTE ====================
    @app.route('/gouvernante/accueil')
    @menage_required
    def gouvernante_accueil():
        conn = get_db()
        c = conn.cursor()

        # Tâches en cours
        c.execute("""SELECT t.*, ch.numero as chambre_numero,
                            u.nom as u_nom, u.prenom as u_prenom
                     FROM taches_housekeeping t
                     JOIN chambres ch ON t.chambre_id = ch.id
                     LEFT JOIN utilisateurs u ON t.assignee_a = u.id
                     WHERE t.statut IN ('À faire', 'En cours')
                     ORDER BY CASE t.priorite WHEN 'Urgente' THEN 1 WHEN 'Haute' THEN 2 ELSE 3 END,
                              t.date_creation DESC""")
        taches = c.fetchall()

        # Chambres à nettoyer
        c.execute("""SELECT ch.numero, ch.etat_proprete, tc.nom as type_nom
                     FROM chambres ch
                     JOIN types_chambres tc ON ch.type_id = tc.id
                     WHERE ch.actif=1 AND ch.etat_proprete IN ('À nettoyer', 'En cours', 'Sale')
                     ORDER BY ch.numero""")
        a_nettoyer = c.fetchall()

        # Stats
        c.execute("SELECT COUNT(*) FROM taches_housekeeping WHERE statut='À faire'")
        a_faire = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM taches_housekeeping WHERE statut='En cours'")
        en_cours = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM taches_housekeeping WHERE statut='Terminée' AND date(date_fin)=date('now')")
        terminees_jour = c.fetchone()[0]

        # Femmes de chambre actives
        c.execute("""SELECT u.id, u.nom, u.prenom,
                     (SELECT COUNT(*) FROM taches_housekeeping WHERE assignee_a=u.id AND statut IN ('À faire','En cours')) as nb_taches
                     FROM utilisateurs u
                     WHERE u.role='femme_chambre' AND u.actif=1""")
        equipe = c.fetchall()

        conn.close()

        content = f"""
        <div class="hero" style="background:linear-gradient(135deg,#10b981,#22c55e)">
          <h1>Bonjour <span>{current_user.prenom}</span> 👋</h1>
          <p>Espace Gouvernante — Gestion du housekeeping</p>
        </div>

        <div class="stats">
          <div class="stat-card amber">
            <i class="fas fa-list stat-icon"></i>
            <div class="stat-value">{a_faire}</div>
            <div class="stat-label">Tâches à faire</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-spinner stat-icon"></i>
            <div class="stat-value">{en_cours}</div>
            <div class="stat-label">En cours</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-check stat-icon"></i>
            <div class="stat-value">{terminees_jour}</div>
            <div class="stat-label">Terminées aujourd'hui</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-bed stat-icon"></i>
            <div class="stat-value">{len(a_nettoyer)}</div>
            <div class="stat-label">Chambres à nettoyer</div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px">
          <div class="card">
            <div class="card-header">
              <h3><i class="fas fa-tasks"></i> Tâches en cours</h3>
              <a href="/housekeeping" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Voir tout</a>
            </div>
            <div class="table-wrap">
              <table>
                <thead><tr><th>N°</th><th>Chambre</th><th>Type</th><th>Priorité</th><th>Assignée à</th><th>Statut</th></tr></thead>
                <tbody>
        """
        for t in taches:
            prio_badge = 'badge-success'
            if t['priorite'] == 'Urgente': prio_badge = 'badge-danger'
            elif t['priorite'] == 'Haute': prio_badge = 'badge-warning'

            statut_badge = 'badge-warning' if t['statut'] == 'À faire' else 'badge-info'

            content += f"""
            <tr>
              <td><strong>{t['numero']}</strong></td>
              <td><span class="badge badge-gold">Ch. {t['chambre_numero']}</span></td>
              <td>{t['type_tache']}</td>
              <td><span class="badge {prio_badge}">{t['priorite']}</span></td>
              <td>{t['u_prenom'] or 'Non assignée'} {t['u_nom'] or ''}</td>
              <td><span class="badge {statut_badge}">{t['statut']}</span></td>
            </tr>
            """
        if not taches:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-check-circle" style="color:#10b981"></i><br>Aucune tâche en attente 🎉</td></tr>'
        content += "</tbody></table></div></div>"

        content += """
          <div>
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-users"></i> Mon équipe</h3></div>
        """
        for e in equipe:
            content += f"""
            <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px dashed #fffbeb">
              <div>
                <div style="font-weight:700">{e['prenom']} {e['nom']}</div>
              </div>
              <span class="badge {'badge-warning' if e['nb_taches'] > 0 else 'badge-success'}">
                {e['nb_taches']} tâche(s)
              </span>
            </div>
            """
        if not equipe:
            content += '<div class="empty" style="padding:20px">Aucune femme de chambre</div>'
        content += "</div>"

        if a_nettoyer:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-broom"></i> Chambres à nettoyer</h3></div>
            """
            for ch in a_nettoyer[:10]:
                proprete_color = '#dc2626' if ch['etat_proprete'] == 'Sale' else '#f59e0b'
                content += f"""
                <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px dashed #fffbeb">
                  <div>
                    <strong>Ch. {ch['numero']}</strong>
                    <br><small style="color:#94a3b8">{ch['type_nom']}</small>
                  </div>
                  <span class="badge" style="background:{proprete_color}20;color:{proprete_color}">{ch['etat_proprete']}</span>
                </div>
                """
            content += "</div>"

        content += "</div></div>"

        return render_page(content, active='gouvernante', page_title='Espace Gouvernante')

    print("[PORTAIL] ✅ Routes gouvernante enregistrées")

    # ==================== PLANNING CHAMBRES ====================
    @app.route('/planning-chambres')
    @reception_required
    def planning_chambres():
        conn = get_db()
        c = conn.cursor()

        # Récupérer toutes les chambres avec statut
        c.execute("""SELECT ch.id, ch.numero, ch.statut, ch.etat_proprete, ch.vue,
                            tc.nom as type_nom, tc.capacite_adultes,
                            e.numero as etage_num
                     FROM chambres ch
                     JOIN types_chambres tc ON ch.type_id = tc.id
                     JOIN etages e ON ch.etage_id = e.id
                     WHERE ch.actif=1
                     ORDER BY ch.numero""")
        chambres = c.fetchall()

        # Réservations en cours pour chaque chambre
        reservations_par_chambre = {}
        for ch in chambres:
            c.execute("""SELECT r.*, cl.nom, cl.prenom
                         FROM reservations r
                         JOIN clients cl ON r.client_id = cl.id
                         WHERE r.chambre_id = ?
                           AND r.statut IN ('Confirmée', 'En cours')
                           AND date(r.date_depart) >= date('now')
                         ORDER BY r.date_arrivee LIMIT 1""", (ch['id'],))
            reservations_par_chambre[ch['id']] = c.fetchone()

        conn.close()

        # Grouper par étage
        par_etage = {}
        for ch in chambres:
            if ch['etage_num'] not in par_etage:
                par_etage[ch['etage_num']] = []
            par_etage[ch['etage_num']].append(ch)

        content = """
        <div class="page-header">
          <div>
            <h2><i class="fas fa-th"></i> Planning des chambres</h2>
            <div class="page-subtitle">Vue temps réel de l'occupation</div>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card green">
            <i class="fas fa-check stat-icon"></i>
            <div class="stat-value">Disponible</div>
            <div class="stat-label">Chambre prête</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-user stat-icon"></i>
            <div class="stat-value">Occupée</div>
            <div class="stat-label">Client en séjour</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-calendar-check stat-icon"></i>
            <div class="stat-value">Réservée</div>
            <div class="stat-label">Réservation confirmée</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-tools stat-icon"></i>
            <div class="stat-value">Maintenance</div>
            <div class="stat-label">Hors service</div>
          </div>
        </div>
        """

        for etage_num in sorted(par_etage.keys()):
            content += f"""
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-building"></i> Étage {etage_num}</h3></div>
              <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px">
            """
            for ch in par_etage[etage_num]:
                color = '#10b981'
                if ch['statut'] == 'Occupée': color = '#dc2626'
                elif ch['statut'] == 'Réservée': color = '#0891b2'
                elif ch['statut'] == 'Maintenance': color = '#f59e0b'

                client_info = ''
                if reservations_par_chambre.get(ch['id']):
                    r = reservations_par_chambre[ch['id']]
                    client_info = f'<div style="font-size:0.7rem;color:#94a3b8;margin-top:4px">{r["nom"][:15]}...</div>'

                content += f"""
                <div class="chambre-card" style="border-left-color:{color};padding:12px">
                  <div class="num" style="font-size:1.1rem">Ch. {ch['numero']}</div>
                  <div class="type" style="font-size:0.7rem">{ch['type_nom']}</div>
                  <div style="font-size:0.75rem;color:#94a3b8;margin-top:4px">{ch['vue'] or ''}</div>
                  <div class="status" style="background:{color}20;color:{color};font-size:0.65rem;margin-top:8px">{ch['statut']}</div>
                  {client_info}
                </div>
                """
            content += "</div></div>"

        return render_page(content, active='planning', page_title='Planning chambres')

    print("[PORTAIL] ✅ Routes planning enregistrées")
