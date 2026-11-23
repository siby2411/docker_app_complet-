"""
Portail DRH + Manager + RH
Vues personnalisées par rôle
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


def register_portail_routes(app, render_page):
    """Portails par rôle RH"""

    # ==================== PORTAIL DRH ====================
    @app.route('/drh/accueil')
    @drh_required
    def drh_accueil():
        conn = get_db()
        c = conn.cursor()

        # KPIs stratégiques
        c.execute("SELECT COUNT(*) FROM employes WHERE actif=1 AND statut='Actif'")
        effectif = c.fetchone()[0]

        c.execute("""SELECT COALESCE(SUM(salaire_base + prime_transport + prime_logement + prime_autre), 0)
                     FROM employes WHERE actif=1 AND statut='Actif'""")
        masse_salariale = c.fetchone()[0]

        c.execute("""SELECT COALESCE(SUM(salaire_net), 0) FROM bulletins_paie
                     WHERE strftime('%Y-%m', date_emission) = strftime('%Y-%m', 'now')""")
        net_mois = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM conges WHERE statut='En attente'")
        conges_a_valider = c.fetchone()[0]

        c.execute("""SELECT COUNT(*) FROM bulletins_paie WHERE statut='Brouillon'""")
        bulletins_brouillon = c.fetchone()[0]

        c.execute("""SELECT COUNT(*) FROM candidats WHERE statut IN ('Nouveau', 'Présélectionné')""")
        candidats_actifs = c.fetchone()[0]

        # Turnover année
        c.execute("""SELECT COUNT(*) FROM employes
                     WHERE statut IN ('Démission', 'Licencié', 'Retraite')
                     AND strftime('%Y', date_fin_contrat) = strftime('%Y', 'now')""")
        departs = c.fetchone()[0]

        c.execute("""SELECT COUNT(*) FROM employes
                     WHERE strftime('%Y', date_embauche) = strftime('%Y', 'now')""")
        embauches = c.fetchone()[0]

        # Effectif par département
        c.execute("""SELECT d.nom, COUNT(e.id) as nb,
                            COALESCE(SUM(e.salaire_base), 0) as masse
                     FROM departements d
                     LEFT JOIN employes e ON e.departement_id = d.id AND e.actif=1
                     WHERE d.actif=1 GROUP BY d.id ORDER BY nb DESC""")
        par_dept = c.fetchall()

        # Contrats expirant
        c.execute("""SELECT ct.*, e.nom, e.prenom, e.matricule
                     FROM contrats ct
                     JOIN employes e ON ct.employe_id = e.id
                     WHERE ct.statut='Actif' AND ct.date_fin IS NOT NULL
                       AND date(ct.date_fin) <= date('now', '+90 days')
                       AND date(ct.date_fin) >= date('now')
                     ORDER BY ct.date_fin ASC LIMIT 10""")
        contrats_expirants = c.fetchall()

        # Congés à valider
        c.execute("""SELECT cg.*, e.nom, e.prenom, e.matricule, tc.nom as type_nom, tc.couleur
                     FROM conges cg
                     JOIN employes e ON cg.employe_id = e.id
                     JOIN types_conges tc ON cg.type_conge_id = tc.id
                     WHERE cg.statut='En attente'
                     ORDER BY cg.created_at ASC LIMIT 10""")
        conges = c.fetchall()

        conn.close()

        content = f"""
        <div class="hero" style="background:linear-gradient(135deg,#4c1d95,#7c3aed)">
          <h1>Bonjour <span>{current_user.prenom}</span> 👋</h1>
          <p>Espace DRH — Pilotage stratégique du capital humain</p>
        </div>

        <div class="kpi-grid">
          <div class="kpi-card" style="border-top-color:#7c3aed">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#7c3aed,#a855f7)">
              <i class="fas fa-users"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Effectif actif</div>
              <div class="kpi-value">{effectif}</div>
            </div>
          </div>
          <div class="kpi-card" style="border-top-color:#10b981">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#10b981,#22c55e)">
              <i class="fas fa-money-bill-wave"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Masse salariale mensuelle</div>
              <div class="kpi-value">{masse_salariale:,.0f}</div>
            </div>
          </div>
          <div class="kpi-card" style="border-top-color:#0891b2">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#0891b2,#06b6d4)">
              <i class="fas fa-coins"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Net payé ce mois</div>
              <div class="kpi-value">{net_mois:,.0f}</div>
            </div>
          </div>
          <div class="kpi-card" style="border-top-color:#f59e0b">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#f59e0b,#fbbf24)">
              <i class="fas fa-hourglass-half"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Congés à valider</div>
              <div class="kpi-value">{conges_a_valider}</div>
            </div>
          </div>
          <div class="kpi-card" style="border-top-color:#ec4899">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#ec4899,#f472b6)">
              <i class="fas fa-file-invoice-dollar"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Bulletins en brouillon</div>
              <div class="kpi-value">{bulletins_brouillon}</div>
            </div>
          </div>
          <div class="kpi-card" style="border-top-color:#a855f7">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#a855f7,#c084fc)">
              <i class="fas fa-user-plus"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Candidats actifs</div>
              <div class="kpi-value">{candidats_actifs}</div>
            </div>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card green">
            <i class="fas fa-arrow-up stat-icon"></i>
            <div class="stat-value">{embauches}</div>
            <div class="stat-label">Embauches {datetime.now().year}</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-arrow-down stat-icon"></i>
            <div class="stat-value">{departs}</div>
            <div class="stat-label">Départs {datetime.now().year}</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-percentage stat-icon"></i>
            <div class="stat-value">{round((departs/effectif*100) if effectif else 0, 1)}%</div>
            <div class="stat-label">Taux de turnover</div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="card">
            <div class="card-header">
              <h3><i class="fas fa-check-circle"></i> Congés à valider</h3>
              <a href="/conges?statut=En%20attente" class="btn btn-primary btn-sm">Voir tout</a>
            </div>
        """
        if conges:
            for cg in conges:
                content += f"""
                <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px dashed #f3e8ff">
                  <div>
                    <div style="font-weight:700;font-size:0.9rem">{cg['nom']} {cg['prenom']}</div>
                    <small style="color:#94a3b8">
                      <span class="badge" style="background:{cg['couleur']}20;color:{cg['couleur']}">{cg['type_nom']}</span>
                      {cg['date_debut']} → {cg['date_fin']} · {cg['nb_jours']}j
                    </small>
                  </div>
                  <a href="/conges/{cg['id']}" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i></a>
                </div>
                """
        else:
            content += '<div class="empty" style="padding:30px"><i class="fas fa-check-circle" style="color:#10b981"></i><br>Aucune demande en attente 🎉</div>'

        content += """
          </div>

          <div class="card">
            <div class="card-header"><h3><i class="fas fa-sitemap"></i> Effectif par département</h3></div>
        """
        for d in par_dept:
            pct = (d['nb'] / effectif * 100) if effectif else 0
            content += f"""
            <div style="margin-bottom:12px">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="font-weight:700;font-size:0.85rem">{d['nom']}</span>
                <span><strong>{d['nb']}</strong> · {d['masse']:,.0f} FCFA</span>
              </div>
              <div style="background:#f3e8ff;border-radius:6px;height:8px;overflow:hidden">
                <div style="background:linear-gradient(90deg,#7c3aed,#a855f7);height:100%;width:{pct}%"></div>
              </div>
            </div>
            """
        content += "</div></div>"

        if contrats_expirants:
            content += """
            <div class="card" style="border-left:5px solid #f59e0b">
              <div class="card-header"><h3 style="color:#92400e"><i class="fas fa-exclamation-triangle"></i> Contrats expirant dans 90 jours</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>N°</th><th>Employé</th><th>Type</th><th>Date fin</th><th>Jours restants</th></tr></thead>
                  <tbody>
            """
            today = datetime.now().date()
            for ct in contrats_expirants:
                try:
                    fin = datetime.fromisoformat(ct['date_fin']).date()
                    jours = (fin - today).days
                    color = '#dc2626' if jours <= 30 else '#f59e0b'
                except Exception:
                    jours = '?'
                    color = '#64748b'

                content += f"""
                <tr>
                  <td><strong>{ct['numero']}</strong></td>
                  <td>{ct['nom']} {ct['prenom']}<br><small style="color:#94a3b8">{ct['matricule']}</small></td>
                  <td><span class="badge badge-primary">{ct['type_contrat']}</span></td>
                  <td>{ct['date_fin']}</td>
                  <td><span class="badge" style="background:{color}20;color:{color}">{jours} jours</span></td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        return render_page(content, active='drh', page_title='Espace DRH')

    print("[PORTAIL] ✅ Routes DRH enregistrées")

    # ==================== PORTAIL MANAGER ====================
    @app.route('/manager/accueil')
    @manager_required
    def manager_accueil():
        conn = get_db()
        c = conn.cursor()

        # Trouver le département du manager
        dept_id = current_user.departement_id if current_user else None

        if dept_id:
            c.execute("""SELECT COUNT(*) FROM employes
                         WHERE departement_id = ? AND actif=1 AND statut='Actif'""", (dept_id,))
            effectif = c.fetchone()[0]

            c.execute("""SELECT COALESCE(SUM(salaire_base), 0) FROM employes
                         WHERE departement_id = ? AND actif=1 AND statut='Actif'""", (dept_id,))
            masse = c.fetchone()[0]

            c.execute("""SELECT cg.*, e.nom, e.prenom, e.matricule, tc.nom as type_nom, tc.couleur
                         FROM conges cg
                         JOIN employes e ON cg.employe_id = e.id
                         JOIN types_conges tc ON cg.type_conge_id = tc.id
                         WHERE e.departement_id = ? AND cg.statut='En attente'
                         ORDER BY cg.created_at ASC""", (dept_id,))
            conges_a_valider = c.fetchall()

            c.execute("""SELECT e.*, p.intitule as poste_nom
                         FROM employes e LEFT JOIN postes p ON e.poste_id = p.id
                         WHERE e.departement_id = ? AND e.actif=1
                         ORDER BY e.nom""", (dept_id,))
            equipe = c.fetchall()
        else:
            effectif = 0
            masse = 0
            conges_a_valider = []
            equipe = []

        # Présence aujourd'hui dans mon département
        if dept_id:
            c.execute("""SELECT COUNT(DISTINCT pt.employe_id) FROM pointages pt
                         JOIN employes e ON pt.employe_id = e.id
                         WHERE e.departement_id = ? AND pt.date_pointage = date('now')""", (dept_id,))
            presents = c.fetchone()[0]
        else:
            presents = 0

        conn.close()

        content = f"""
        <div class="hero" style="background:linear-gradient(135deg,#f59e0b,#fbbf24)">
          <h1>Bonjour <span>{current_user.prenom}</span> 👋</h1>
          <p>Espace Manager — Pilotage de mon équipe</p>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-users stat-icon"></i>
            <div class="stat-value">{effectif}</div>
            <div class="stat-label">Membres de mon équipe</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-coins stat-icon"></i>
            <div class="stat-value">{masse:,.0f}</div>
            <div class="stat-label">Masse salariale base</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-hourglass-half stat-icon"></i>
            <div class="stat-value">{len(conges_a_valider)}</div>
            <div class="stat-label">Congés à valider</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-user-check stat-icon"></i>
            <div class="stat-value">{presents}</div>
            <div class="stat-label">Présents aujourd'hui</div>
          </div>
        </div>
        """

        if conges_a_valider:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-hourglass-half"></i> Demandes de congés à valider</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Employé</th><th>Type</th><th>Période</th><th>Jours</th><th>Actions</th></tr></thead>
                  <tbody>
            """
            for cg in conges_a_valider:
                content += f"""
                <tr>
                  <td><strong>{cg['nom']} {cg['prenom']}</strong><br><small style="color:#94a3b8">{cg['matricule']}</small></td>
                  <td><span class="badge" style="background:{cg['couleur']}20;color:{cg['couleur']}">{cg['type_nom']}</span></td>
                  <td>{cg['date_debut']} → {cg['date_fin']}</td>
                  <td><strong>{cg['nb_jours']}j</strong></td>
                  <td><a href="/conges/{cg['id']}" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Traiter</a></td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        if equipe:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-users"></i> Mon équipe</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Matricule</th><th>Nom</th><th>Poste</th><th>Type contrat</th><th>Ancienneté</th><th>Actions</th></tr></thead>
                  <tbody>
            """
            for e in equipe:
                try:
                    emb = datetime.fromisoformat(e['date_embauche'])
                    anc = (datetime.now() - emb).days // 365
                except Exception:
                    anc = '?'

                content += f"""
                <tr>
                  <td><strong>{e['matricule']}</strong></td>
                  <td>{e['nom']} {e['prenom']}</td>
                  <td>{e['poste_nom'] or '-'}</td>
                  <td><span class="badge badge-primary">{e['type_contrat']}</span></td>
                  <td>{anc} ans</td>
                  <td><a href="/employes/{e['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a></td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        return render_page(content, active='manager', page_title='Espace Manager')

    print("[PORTAIL] ✅ Routes manager enregistrées")

    # ==================== PORTAIL RH (opérations) ====================
    @app.route('/rh/accueil')
    @rh_required
    def rh_accueil():
        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM employes WHERE actif=1 AND statut='Actif'")
        effectif = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM conges WHERE statut='En attente'")
        conges = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM bulletins_paie WHERE statut='Brouillon'")
        bulletins = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM candidats WHERE statut='Nouveau'")
        candidats = c.fetchone()[0]

        # Actions rapides (derniers employés)
        c.execute("""SELECT * FROM employes WHERE actif=1 ORDER BY created_at DESC LIMIT 5""")
        recents = c.fetchall()

        conn.close()

        content = f"""
        <div class="hero" style="background:linear-gradient(135deg,#0891b2,#06b6d4)">
          <h1>Bonjour <span>{current_user.prenom}</span> 👋</h1>
          <p>Espace RH — Opérations quotidiennes</p>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-users stat-icon"></i>
            <div class="stat-value">{effectif}</div>
            <div class="stat-label">Employés actifs</div>
          </div>
          <div class="stat-card amber">
            <i class="fas fa-calendar-check stat-icon"></i>
            <div class="stat-value">{conges}</div>
            <div class="stat-label">Congés à traiter</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-file-invoice-dollar stat-icon"></i>
            <div class="stat-value">{bulletins}</div>
            <div class="stat-label">Bulletins brouillon</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-user-plus stat-icon"></i>
            <div class="stat-value">{candidats}</div>
            <div class="stat-label">Nouveaux candidats</div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-bottom:25px">
          <a href="/employes/nouveau" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:25px;border-left:5px solid #7c3aed">
              <i class="fas fa-user-plus" style="font-size:2rem;color:#7c3aed;margin-bottom:10px"></i>
              <div style="font-weight:800;color:#4c1d95;font-size:0.9rem">Nouvel employé</div>
            </div>
          </a>
          <a href="/conges/nouveau" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:25px;border-left:5px solid #10b981">
              <i class="fas fa-calendar-plus" style="font-size:2rem;color:#10b981;margin-bottom:10px"></i>
              <div style="font-weight:800;color:#4c1d95;font-size:0.9rem">Saisir congé</div>
            </div>
          </a>
          <a href="/pointages/nouveau" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:25px;border-left:5px solid #0891b2">
              <i class="fas fa-clock" style="font-size:2rem;color:#0891b2;margin-bottom:10px"></i>
              <div style="font-weight:800;color:#4c1d95;font-size:0.9rem">Pointage</div>
            </div>
          </a>
          <a href="/paie/generer" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:25px;border-left:5px solid #f59e0b">
              <i class="fas fa-cogs" style="font-size:2rem;color:#f59e0b;margin-bottom:10px"></i>
              <div style="font-weight:800;color:#4c1d95;font-size:0.9rem">Générer paie</div>
            </div>
          </a>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-clock-rotate-left"></i> Derniers employés ajoutés</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Matricule</th><th>Nom</th><th>Date embauche</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for e in recents:
            content += f"""
            <tr>
              <td><strong>{e['matricule']}</strong></td>
              <td>{e['nom']} {e['prenom']}</td>
              <td>{e['date_embauche']}</td>
              <td><a href="/employes/{e['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a></td>
            </tr>
            """
        content += "</tbody></table></div></div>"
        return render_page(content, active='rh', page_title='Espace RH')

    print("[PORTAIL] ✅ Routes RH enregistrées")

    # ==================== CALENDRIER ÉQUIPE ====================
    @app.route('/calendrier-equipe')
    @manager_required
    def calendrier_equipe():
        conn = get_db()
        c = conn.cursor()

        dept_id = current_user.departement_id if current_user else None

        # Congés approuvés des 60 prochains jours
        today = datetime.now().date().isoformat()
        future = (datetime.now().date() + timedelta(days=60)).isoformat()

        if dept_id:
            c.execute("""SELECT cg.*, e.nom, e.prenom, e.matricule, tc.nom as type_nom, tc.couleur
                         FROM conges cg
                         JOIN employes e ON cg.employe_id = e.id
                         JOIN types_conges tc ON cg.type_conge_id = tc.id
                         WHERE e.departement_id = ? AND cg.statut='Approuvé'
                           AND cg.date_fin >= ? AND cg.date_debut <= ?
                         ORDER BY cg.date_debut ASC""",
                      (dept_id, today, future))
        else:
            c.execute("""SELECT cg.*, e.nom, e.prenom, e.matricule, tc.nom as type_nom, tc.couleur
                         FROM conges cg
                         JOIN employes e ON cg.employe_id = e.id
                         JOIN types_conges tc ON cg.type_conge_id = tc.id
                         WHERE cg.statut='Approuvé'
                           AND cg.date_fin >= ? AND cg.date_debut <= ?
                         ORDER BY cg.date_debut ASC""",
                      (today, future))

        conges = c.fetchall()
        conn.close()

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-calendar-alt"></i> Calendrier de l'équipe</h2>
            <div class="page-subtitle">Congés des 60 prochains jours</div>
          </div>
          <a href="/manager/accueil" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>

        <div class="card">
        """

        if not conges:
            content += '<div class="empty"><i class="fas fa-calendar-check" style="color:#10b981"></i><br>Aucun congé prévu dans les 60 prochains jours</div>'
        else:
            # Grouper par semaine
            for cg in conges:
                content += f"""
                <div style="display:flex;align-items:center;gap:15px;padding:12px 0;border-bottom:1px dashed #f3e8ff">
                  <div style="width:100px;text-align:center">
                    <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;font-weight:700">Du</div>
                    <div style="font-weight:900;color:#4c1d95">{cg['date_debut'][:10]}</div>
                  </div>
                  <div style="width:100px;text-align:center">
                    <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;font-weight:700">Au</div>
                    <div style="font-weight:900;color:#4c1d95">{cg['date_fin'][:10]}</div>
                  </div>
                  <div style="flex:1">
                    <div style="font-weight:800;color:#4c1d95">{cg['nom']} {cg['prenom']}</div>
                    <small style="color:#94a3b8">{cg['matricule']}</small>
                  </div>
                  <div>
                    <span class="badge" style="background:{cg['couleur']}20;color:{cg['couleur']}">{cg['type_nom']}</span>
                  </div>
                  <div style="width:60px;text-align:right">
                    <strong style="color:#7c3aed">{cg['nb_jours']}j</strong>
                  </div>
                </div>
                """

        content += "</div>"
        return render_page(content, active='manager', page_title='Calendrier équipe')

    print("[PORTAIL] ✅ Routes calendrier enregistrées")
