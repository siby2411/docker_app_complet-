"""
Portail Directeur + Chef projet + Membre + Gantt
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


def register_portail_routes(app, render_page):
    """Portails par rôle Projets"""

    # ==================== PORTAIL DIRECTEUR ====================
    @app.route('/directeur/accueil')
    @directeur_required
    def directeur_accueil():
        conn = get_db()
        c = conn.cursor()

        # KPIs stratégiques
        c.execute("SELECT COUNT(*) FROM projets WHERE actif=1")
        row = c.fetchone()
        total_projets = row[0] if row else 0

        c.execute("SELECT COUNT(*) FROM projets WHERE actif=1 AND statut='En cours'")
        row = c.fetchone()
        en_cours = row[0] if row else 0

        c.execute("SELECT COALESCE(SUM(budget_prevu), 0) FROM projets WHERE actif=1")
        row = c.fetchone()
        budget_total = row[0] if row else 0

        c.execute("SELECT COALESCE(SUM(budget_consomme), 0) FROM projets WHERE actif=1")
        row = c.fetchone()
        budget_consomme = row[0] if row else 0

        c.execute("SELECT COALESCE(AVG(avancement_pct), 0) FROM projets WHERE actif=1")
        row = c.fetchone()
        avancement_moyen = row[0] if row else 0

        # Écart budgétaire
        ecart_budget = budget_total - budget_consomme

        # Risques critiques
        c.execute("""SELECT COUNT(*) FROM risques WHERE statut='Ouvert'
                     AND niveau_risque IN ('Critique','Élevé')""")
        row = c.fetchone()
        risques_critiques = row[0] if row else 0

        # Projets santé
        c.execute("SELECT COUNT(*) FROM projets WHERE actif=1 AND sante_projet='Vert'")
        row = c.fetchone()
        projets_verts = row[0] if row else 0

        c.execute("SELECT COUNT(*) FROM projets WHERE actif=1 AND sante_projet='Jaune'")
        row = c.fetchone()
        projets_jaunes = row[0] if row else 0

        c.execute("SELECT COUNT(*) FROM projets WHERE actif=1 AND sante_projet='Rouge'")
        row = c.fetchone()
        projets_rouges = row[0] if row else 0

        # Top 5 projets par budget
        c.execute("""SELECT p.*, cl.nom as client_nom
                     FROM projets p
                     LEFT JOIN clients cl ON p.client_id = cl.id
                     WHERE p.actif=1
                     ORDER BY p.budget_prevu DESC LIMIT 5""")
        top_projets = c.fetchall()

        # EVM derniers
        c.execute("""SELECT e.*, p.nom as projet_nom, p.code as projet_code
                     FROM evm e
                     JOIN projets p ON e.projet_id = p.id
                     WHERE e.id IN (SELECT MAX(id) FROM evm GROUP BY projet_id)
                     ORDER BY e.spi ASC LIMIT 5""")
        evm_critiques = c.fetchall()

        # Budget par programme
        c.execute("""SELECT pr.nom, COALESCE(SUM(p.budget_prevu), 0) as budget
                     FROM programmes pr
                     LEFT JOIN projets p ON p.programme_id = pr.id AND p.actif=1
                     WHERE pr.actif=1
                     GROUP BY pr.id ORDER BY budget DESC""")
        par_programme = c.fetchall()

        conn.close()

        content = f"""
        <div class="hero">
          <h1>Bonjour <span>{current_user.prenom}</span> 👋</h1>
          <p>Espace Directeur — Pilotage stratégique du portefeuille UEMOA</p>
          <div class="certifs">
            <span>Portefeuille {total_projets} projets</span>
            <span>Budget {budget_total/1e9:.1f}B FCFA</span>
            <span>{en_cours} en cours</span>
          </div>
        </div>

        <div class="kpi-grid">
          <div class="kpi-card" style="border-top-color:#2563eb">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#1e3a8a,#2563eb)">
              <i class="fas fa-project-diagram"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Portefeuille</div>
              <div class="kpi-value">{total_projets}</div>
              <div class="kpi-sub">{en_cours} projets en cours</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#f59e0b">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#d97706,#f59e0b)">
              <i class="fas fa-coins"></i>
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
              <div class="kpi-label">Risques critiques</div>
              <div class="kpi-value">{risques_critiques}</div>
              <div class="kpi-sub">Nécessitent attention</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#7c3aed">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#7c3aed,#a855f7)">
              <i class="fas fa-wallet"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Écart budgétaire</div>
              <div class="kpi-value">{ecart_budget/1e9:.1f}B</div>
              <div class="kpi-sub">FCFA restants</div>
            </div>
          </div>

          <div class="kpi-card" style="border-top-color:#0891b2">
            <div class="kpi-icon" style="background:linear-gradient(135deg,#0891b2,#06b6d4)">
              <i class="fas fa-heartbeat"></i>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Santé portefeuille</div>
              <div class="kpi-value">
                <span class="health-dot health-vert"></span>{projets_verts}
                <span class="health-dot health-jaune" style="margin-left:8px"></span>{projets_jaunes}
                <span class="health-dot health-rouge" style="margin-left:8px"></span>{projets_rouges}
              </div>
              <div class="kpi-sub">Vert / Jaune / Rouge</div>
            </div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="card">
            <div class="card-header"><h3><i class="fas fa-crown"></i> Top 5 projets par budget</h3></div>
            <div class="table-wrap">
              <table>
                <thead><tr><th>Code</th><th>Projet</th><th>Client</th><th>Budget</th></tr></thead>
                <tbody>
        """
        for p in top_projets:
            content += f"""
            <tr>
              <td><strong>{p['code']}</strong></td>
              <td>
                <div style="font-weight:700">{p['nom'][:35]}</div>
                <small style="color:#94a3b8">{p['type_projet']}</small>
              </td>
              <td>{p['client_nom'][:20] if p['client_nom'] else '-'}</td>
              <td><strong style="color:#2563eb">{p['budget_prevu']/1e9:.2f}B</strong> FCFA</td>
            </tr>
            """
        content += "</tbody></table></div></div>"

        content += """
          <div class="card" style="border-left:5px solid #dc2626">
            <div class="card-header"><h3 style="color:#991b1b"><i class="fas fa-chart-line"></i> Projets en difficulté (SPI faible)</h3></div>
            <div class="table-wrap">
              <table>
                <thead><tr><th>Projet</th><th>SPI</th><th>CPI</th><th>EAC</th></tr></thead>
                <tbody>
        """
        for e in evm_critiques:
            spi_color = '#dc2626' if e['spi'] < 0.85 else ('#f59e0b' if e['spi'] < 0.95 else '#10b981')
            cpi_color = '#dc2626' if e['cpi'] < 0.85 else ('#f59e0b' if e['cpi'] < 0.95 else '#10b981')
            content += f"""
            <tr>
              <td><small>{e['projet_code']}<br>{e['projet_nom'][:30]}</small></td>
              <td><span class="evm-badge" style="background:{spi_color}20;color:{spi_color}">{e['spi']:.2f}</span></td>
              <td><span class="evm-badge" style="background:{cpi_color}20;color:{cpi_color}">{e['cpi']:.2f}</span></td>
              <td><strong>{e['eac']/1e9:.2f}B</strong></td>
            </tr>
            """
        content += "</tbody></table></div></div>"

        content += """
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-layer-group"></i> Budget par programme</h3></div>
        """
        max_b = max([p['budget'] for p in par_programme], default=1)
        for p in par_programme:
            pct = (p['budget'] / max_b * 100) if max_b else 0
            content += f"""
            <div style="margin-bottom:15px">
              <div style="display:flex;justify-content:space-between;margin-bottom:5px">
                <span style="font-weight:700;font-size:0.9rem">{p['nom'][:45]}</span>
                <strong style="color:#2563eb">{p['budget']/1e9:.2f}B FCFA</strong>
              </div>
              <div style="background:#eff6ff;border-radius:6px;height:12px;overflow:hidden">
                <div style="background:linear-gradient(90deg,#1e3a8a,#2563eb);height:100%;width:{pct}%"></div>
              </div>
            </div>
            """
        content += "</div>"

        return render_page(content, active='directeur', page_title='Espace Directeur')

    print("[PORTAIL] ✅ Routes directeur enregistrées")

    # ==================== PORTAIL CHEF PROJET ====================
    @app.route('/chef/accueil')
    @chef_required
    def chef_accueil():
        conn = get_db()
        c = conn.cursor()

        # Mes projets
        c.execute("""SELECT p.*, cl.nom as client_nom,
                            (SELECT COUNT(*) FROM taches WHERE projet_id = p.id) as nb_taches,
                            (SELECT COUNT(*) FROM risques WHERE projet_id = p.id AND statut='Ouvert') as nb_risques
                     FROM projets p
                     LEFT JOIN clients cl ON p.client_id = cl.id
                     WHERE p.actif=1 AND p.chef_projet_id = ?
                     ORDER BY p.priorite DESC, p.date_fin_prevue ASC""",
                  (current_user.id if current_user else 0,))
        mes_projets = c.fetchall()

        # Mes tâches
        c.execute("""SELECT t.*, p.nom as projet_nom, p.code as projet_code
                     FROM taches t
                     JOIN projets p ON t.projet_id = p.id
                     WHERE t.responsable_id = ? AND t.statut IN ('À faire', 'En cours')
                     ORDER BY t.date_fin_prevue ASC LIMIT 10""",
                  (current_user.id if current_user else 0,))
        mes_taches = c.fetchall()

        # Mes risques
        c.execute("""SELECT r.*, p.nom as projet_nom
                     FROM risques r
                     JOIN projets p ON r.projet_id = p.id
                     WHERE r.responsable_id = ? AND r.statut='Ouvert'
                     ORDER BY r.criticite DESC LIMIT 10""",
                  (current_user.id if current_user else 0,))
        mes_risques = c.fetchall()

        # Stats
        nb_projets = len(mes_projets)
        budget_total = sum(p['budget_prevu'] for p in mes_projets)
        avancement_moyen = (sum(p['avancement_pct'] or 0 for p in mes_projets) / nb_projets) if nb_projets else 0

        conn.close()

        content = f"""
        <div class="hero" style="background:linear-gradient(135deg,#7c3aed,#a855f7)">
          <h1>Bonjour <span>{current_user.prenom}</span> 👋</h1>
          <p>Espace Chef de Projet — Mes projets et priorités</p>
        </div>

        <div class="stats">
          <div class="stat-card purple">
            <i class="fas fa-project-diagram stat-icon"></i>
            <div class="stat-value">{nb_projets}</div>
            <div class="stat-label">Mes projets</div>
          </div>
          <div class="stat-card gold">
            <i class="fas fa-money-bill-wave stat-icon"></i>
            <div class="stat-value">{budget_total/1e9:.1f}B</div>
            <div class="stat-label">Budget total</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-chart-line stat-icon"></i>
            <div class="stat-value">{avancement_moyen:.0f}%</div>
            <div class="stat-label">Avancement moyen</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-exclamation-triangle stat-icon"></i>
            <div class="stat-value">{len(mes_risques)}</div>
            <div class="stat-label">Risques actifs</div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-bottom:25px">
          <a href="/taches/nouvelle" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:25px;border-left:5px solid #7c3aed">
              <i class="fas fa-tasks" style="font-size:2rem;color:#7c3aed;margin-bottom:10px"></i>
              <div style="font-weight:800">Nouvelle tâche</div>
            </div>
          </a>
          <a href="/risques/nouveau" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:25px;border-left:5px solid #dc2626">
              <i class="fas fa-exclamation-triangle" style="font-size:2rem;color:#dc2626;margin-bottom:10px"></i>
              <div style="font-weight:800">Nouveau risque</div>
            </div>
          </a>
          <a href="/planning" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:25px;border-left:5px solid #2563eb">
              <i class="fas fa-calendar-alt" style="font-size:2rem;color:#2563eb;margin-bottom:10px"></i>
              <div style="font-weight:800">Voir Gantt</div>
            </div>
          </a>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-project-diagram"></i> Mes projets</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Projet</th><th>Client</th><th>Budget</th><th>Avanc.</th><th>Santé</th><th>Tâches</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for p in mes_projets:
            health_class = 'health-vert' if p['sante_projet'] == 'Vert' else ('health-jaune' if p['sante_projet'] == 'Jaune' else 'health-rouge')
            av = p['avancement_pct'] or 0
            content += f"""
            <tr>
              <td><strong>{p['code']}</strong></td>
              <td>{p['nom'][:40]}</td>
              <td>{p['client_nom'][:20] if p['client_nom'] else '-'}</td>
              <td><strong>{p['budget_prevu']/1e6:,.0f}M</strong> FCFA</td>
              <td>
                <strong>{av:.0f}%</strong>
                <div style="background:#eff6ff;border-radius:6px;height:6px;margin-top:4px;overflow:hidden">
                  <div style="background:#7c3aed;height:100%;width:{av}%"></div>
                </div>
              </td>
              <td><span class="health-dot {health_class}"></span>{p['sante_projet']}</td>
              <td><span class="badge badge-primary">{p['nb_taches']}</span></td>
              <td><a href="/projets/{p['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a></td>
            </tr>
            """
        if not mes_projets:
            content += '<tr><td colspan="8" class="empty">Aucun projet assigné</td></tr>'
        content += "</tbody></table></div></div>"

        content += """
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div class="card">
            <div class="card-header"><h3><i class="fas fa-tasks"></i> Mes tâches prioritaires</h3></div>
        """
        for t in mes_taches:
            badge = 'badge-warning' if t['statut'] == 'En cours' else 'badge-info'
            content += f"""
            <div style="padding:12px 0;border-bottom:1px dashed #f0f9ff">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <strong style="font-size:0.9rem">{t['code']}</strong>
                <span class="badge {badge}">{t['statut']}</span>
              </div>
              <div style="font-weight:700;font-size:0.85rem;margin-top:4px">{t['nom'][:50]}</div>
              <small style="color:#94a3b8">📅 {t['date_fin_prevue'] or '?'} · {t['avancement_pct'] or 0:.0f}%</small>
            </div>
            """
        if not mes_taches:
            content += '<div class="empty" style="padding:20px">Aucune tâche assignée</div>'
        content += "</div>"

        content += """
          <div class="card" style="border-left:5px solid #dc2626">
            <div class="card-header"><h3 style="color:#991b1b"><i class="fas fa-exclamation-triangle"></i> Mes risques</h3></div>
        """
        for r in mes_risques:
            color = '#dc2626' if r['niveau_risque'] == 'Critique' else ('#f59e0b' if r['niveau_risque'] == 'Élevé' else '#10b981')
            content += f"""
            <div style="padding:10px 0;border-bottom:1px dashed #fee2e2">
              <div style="display:flex;justify-content:space-between">
                <strong style="font-size:0.85rem">{r['code']}</strong>
                <span class="badge" style="background:{color}20;color:{color}">{r['niveau_risque']}</span>
              </div>
              <div style="font-size:0.85rem;color:#475569;margin-top:4px">{r['titre'][:60]}</div>
            </div>
            """
        if not mes_risques:
            content += '<div class="empty" style="padding:20px"><i class="fas fa-check-circle" style="color:#10b981"></i><br>Aucun risque 🎉</div>'
        content += "</div></div>"

        return render_page(content, active='chef', page_title='Espace Chef')

    print("[PORTAIL] ✅ Routes chef enregistrées")

    # ==================== PORTAIL MEMBRE ====================
    @app.route('/membre/accueil')
    @membre_required
    def membre_accueil():
        conn = get_db()
        c = conn.cursor()

        user_id = current_user.id if current_user else 0

        # Mes tâches
        c.execute("""SELECT t.*, p.nom as projet_nom, p.code as projet_code
                     FROM taches t
                     JOIN projets p ON t.projet_id = p.id
                     WHERE t.responsable_id = ? AND t.statut IN ('À faire', 'En cours')
                     ORDER BY t.date_fin_prevue ASC""", (user_id,))
        mes_taches = c.fetchall()

        # Mes heures cette semaine
        c.execute("""SELECT COALESCE(SUM(heures), 0) FROM feuilles_temps
                     WHERE utilisateur_id = ? AND date_jour >= date('now', '-7 days')""", (user_id,))
        row = c.fetchone()
        heures_semaine = row[0] if row else 0

        # Mes heures ce mois
        c.execute("""SELECT COALESCE(SUM(heures), 0) FROM feuilles_temps
                     WHERE utilisateur_id = ? AND strftime('%Y-%m', date_jour) = strftime('%Y-%m', 'now')""", (user_id,))
        row = c.fetchone()
        heures_mois = row[0] if row else 0

        # Mes timesheets
        c.execute("""SELECT ft.*, p.nom as projet_nom
                     FROM feuilles_temps ft
                     JOIN projets p ON ft.projet_id = p.id
                     WHERE ft.utilisateur_id = ?
                     ORDER BY ft.date_jour DESC LIMIT 10""", (user_id,))
        mes_timesheets = c.fetchall()

        conn.close()

        content = f"""
        <div class="hero" style="background:linear-gradient(135deg,#10b981,#22c55e)">
          <h1>Bonjour <span>{current_user.prenom}</span> 👋</h1>
          <p>Espace Membre — Mes tâches et timesheets</p>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-tasks stat-icon"></i>
            <div class="stat-value">{len(mes_taches)}</div>
            <div class="stat-label">Tâches actives</div>
          </div>
          <div class="stat-card blue">
            <i class="fas fa-clock stat-icon"></i>
            <div class="stat-value">{heures_semaine:.0f}h</div>
            <div class="stat-label">Cette semaine</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-calendar stat-icon"></i>
            <div class="stat-value">{heures_mois:.0f}h</div>
            <div class="stat-label">Ce mois</div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:15px;margin-bottom:25px">
          <a href="/feuilles-temps/nouvelle" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:30px;border-left:5px solid #2563eb">
              <i class="fas fa-clock" style="font-size:2.5rem;color:#2563eb;margin-bottom:15px"></i>
              <div style="font-weight:800;font-size:1.1rem">Saisir mes heures</div>
            </div>
          </a>
          <a href="/taches" style="text-decoration:none">
            <div class="card" style="text-align:center;padding:30px;border-left:5px solid #7c3aed">
              <i class="fas fa-tasks" style="font-size:2.5rem;color:#7c3aed;margin-bottom:15px"></i>
              <div style="font-weight:800;font-size:1.1rem">Mes tâches</div>
            </div>
          </a>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-tasks"></i> Mes tâches en cours</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Tâche</th><th>Projet</th><th>Échéance</th><th>Avanc.</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for t in mes_taches:
            badge = 'badge-warning' if t['statut'] == 'En cours' else 'badge-info'
            av = t['avancement_pct'] or 0
            content += f"""
            <tr>
              <td><strong>{t['code']}</strong></td>
              <td>{t['nom'][:45]}</td>
              <td><small>{t['projet_code']}</small></td>
              <td>{t['date_fin_prevue'] or '-'}</td>
              <td>
                <strong>{av:.0f}%</strong>
                <div style="background:#eff6ff;border-radius:6px;height:6px;margin-top:4px;overflow:hidden">
                  <div style="background:#10b981;height:100%;width:{av}%"></div>
                </div>
              </td>
              <td><span class="badge {badge}">{t['statut']}</span></td>
              <td><a href="/taches/{t['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a></td>
            </tr>
            """
        if not mes_taches:
            content += '<tr><td colspan="7" class="empty"><i class="fas fa-check-circle" style="color:#10b981"></i><br>Aucune tâche active 🎉</td></tr>'
        content += "</tbody></table></div></div>"

        if mes_timesheets:
            content += """
            <div class="card">
              <div class="card-header"><h3><i class="fas fa-clock"></i> Mes dernières saisies</h3></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Date</th><th>Projet</th><th>Heures</th><th>Description</th><th>Statut</th></tr></thead>
                  <tbody>
            """
            for ft in mes_timesheets:
                badge = 'badge-success' if ft['statut'] == 'Validé' else 'badge-warning'
                content += f"""
                <tr>
                  <td>{ft['date_jour']}</td>
                  <td><small>{ft['projet_nom'][:30]}</small></td>
                  <td><strong>{ft['heures']:.1f}h</strong></td>
                  <td>{ft['description'] or '-'}</td>
                  <td><span class="badge {badge}">{ft['statut']}</span></td>
                </tr>
                """
            content += "</tbody></table></div></div>"

        return render_page(content, active='membre', page_title='Espace Membre')

    print("[PORTAIL] ✅ Routes membre enregistrées")

    # ==================== GANTT / PLANNING ====================
    @app.route('/planning')
    @chef_required
    def planning():
        conn = get_db()
        c = conn.cursor()

        projet_filter = request.args.get('projet_id', '')

        if not projet_filter:
            # Prendre le premier projet actif
            c.execute("SELECT id FROM projets WHERE actif=1 AND statut='En cours' ORDER BY id LIMIT 1")
            row = c.fetchone()
            if row:
                projet_filter = str(row['id'])

        c.execute("SELECT id, code, nom FROM projets WHERE actif=1 ORDER BY nom")
        projets = c.fetchall()

        taches = []
        if projet_filter:
            c.execute("""SELECT t.*, u.nom as resp_nom, u.prenom as resp_prenom
                         FROM taches t
                         LEFT JOIN utilisateurs u ON t.responsable_id = u.id
                         WHERE t.projet_id = ? ORDER BY t.date_debut_prevue""",
                      (int(projet_filter),))
            taches = c.fetchall()

        # Calculer min/max dates
        if taches:
            dates_debut = [t['date_debut_prevue'] for t in taches if t['date_debut_prevue']]
            dates_fin = [t['date_fin_prevue'] for t in taches if t['date_fin_prevue']]

            date_min = min(dates_debut) if dates_debut else datetime.now().date().isoformat()
            date_max = max(dates_fin) if dates_fin else (datetime.now().date() + timedelta(days=90)).isoformat()

            try:
                d_min = datetime.fromisoformat(date_min)
                d_max = datetime.fromisoformat(date_max)
                total_jours = (d_max - d_min).days + 1
            except Exception:
                d_min = datetime.now()
                total_jours = 90
        else:
            d_min = datetime.now()
            total_jours = 90

        conn.close()

        projets_opts = "".join(f'<option value="{p["id"]}" {"selected" if projet_filter == str(p["id"]) else ""}>{p["code"]} - {p["nom"][:40]}</option>' for p in projets)

        content = f"""
        <div class="page-header">
          <div>
            <h2><i class="fas fa-calendar-alt"></i> Planning Gantt</h2>
            <div class="page-subtitle">Vue temporelle des tâches — Chemin critique</div>
          </div>
          <form method="GET">
            <select name="projet_id" onchange="this.form.submit()" style="padding:10px 15px;border:2px solid #f1f5f9;border-radius:10px;font-weight:600">
              {projets_opts}
            </select>
          </form>
        </div>

        <div class="card" style="overflow-x:auto">
          <div class="card-header">
            <h3><i class="fas fa-bars-staggered"></i> Diagramme de Gantt</h3>
            <div style="display:flex;gap:15px;font-size:0.75rem">
              <span><span style="display:inline-block;width:20px;height:10px;background:#2563eb;border-radius:2px;margin-right:5px"></span>Normale</span>
              <span><span style="display:inline-block;width:20px;height:10px;background:#dc2626;border-radius:2px;margin-right:5px"></span>Chemin critique</span>
              <span><span style="display:inline-block;width:20px;height:10px;background:#10b981;border-radius:2px;margin-right:5px"></span>Terminée</span>
            </div>
          </div>
        """

        if taches:
            content += f"""
            <div style="min-width:1000px;padding:10px 0">
                <div style="display:grid;grid-template-columns:300px 1fr;gap:15px;margin-bottom:15px;font-size:0.75rem;color:#64748b;font-weight:800">
                    <div>TÂCHE</div>
                    <div style="display:grid;grid-template-columns:repeat({min(total_jours, 30)},1fr);gap:2px">
            """
            # Afficher les dates par tranche
            for i in range(0, min(total_jours, 30), 7):
                try:
                    d = d_min + timedelta(days=i)
                    content += f'<div style="text-align:center">{d.strftime("%d/%m")}</div>'
                except Exception:
                    pass
            content += """
                    </div>
                </div>
            """
            for t in taches:
                try:
                    t_start = datetime.fromisoformat(t['date_debut_prevue']) if t['date_debut_prevue'] else d_min
                    t_end = datetime.fromisoformat(t['date_fin_prevue']) if t['date_fin_prevue'] else d_min
                    offset = (t_start - d_min).days
                    duration = max(1, (t_end - t_start).days)
                except Exception:
                    offset = 0
                    duration = 5

                # Couleur selon statut / chemin critique
                if t['statut'] == 'Terminée':
                    bar_color = '#10b981'
                elif t['chemin_critique']:
                    bar_color = '#dc2626'
                else:
                    bar_color = '#2563eb'

                # Position (en %)
                offset_pct = (offset / 30) * 100
                duration_pct = (duration / 30) * 100

                # Ajuster pour ne pas déborder
                if offset_pct + duration_pct > 100:
                    duration_pct = 100 - offset_pct
                    if duration_pct < 2:
                        duration_pct = 2

                content += f"""
                <div style="display:grid;grid-template-columns:300px 1fr;gap:15px;padding:8px 0;border-bottom:1px dashed #f0f9ff;align-items:center">
                    <div>
                        <div style="font-weight:700;font-size:0.85rem">{t['code']} · {t['nom'][:35]}</div>
                        <small style="color:#94a3b8">{t['resp_prenom'] or '?'} {t['resp_nom'] or ''} · {t['avancement_pct'] or 0:.0f}%</small>
                    </div>
                    <div style="position:relative;height:25px;background:#f0f9ff;border-radius:6px;overflow:hidden">
                        <div style="position:absolute;left:{offset_pct}%;width:{duration_pct}%;height:100%;background:{bar_color};border-radius:6px;display:flex;align-items:center;justify-content:center;color:white;font-size:0.7rem;font-weight:800">
                            {t['avancement_pct'] or 0:.0f}%
                        </div>
                    </div>
                </div>
                """
            content += "</div>"

        else:
            content += '<div class="empty"><i class="fas fa-calendar-alt"></i><br>Aucune tâche à afficher</div>'

        content += "</div>"

        return render_page(content, active='planning', page_title='Gantt')

    print("[PORTAIL] ✅ Routes planning enregistrées")
