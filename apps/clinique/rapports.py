"""
Module Rapports & Statistiques pour Clinique Omega
"""
from flask import render_template_string, request, jsonify
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "/app/data/clinique.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


try:
    from auth import admin_required, staff_required, caisse_required
except ImportError:
    def admin_required(f): return f
    def staff_required(f): return f
    def caisse_required(f): return f


def register_rapports_routes(app, render_page):
    """Enregistre les routes de rapports et statistiques"""

    @app.route('/rapports')
    @staff_required
    def rapports():
        conn = get_db()
        c = conn.cursor()

        # Statistiques générales
        c.execute("SELECT COUNT(*) FROM patients WHERE actif=1")
        total_patients = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM medecins WHERE actif=1")
        total_medecins = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM consultations")
        total_consultations = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM hospitalisations WHERE statut='En cours'")
        hosp_en_cours = c.fetchone()[0]

        # Statistiques financières
        c.execute("""SELECT COALESCE(SUM(montant_total),0) as emis,
                            COALESCE(SUM(montant_paye),0) as paye
                     FROM factures""")
        row = c.fetchone()
        total_emis = row['emis']
        total_paye = row['paye']
        total_impaye = total_emis - total_paye

        # Top 5 diagnostics
        c.execute("""SELECT diagnostic_principal, COUNT(*) as nb
                     FROM consultations
                     WHERE diagnostic_principal IS NOT NULL AND diagnostic_principal != ''
                     GROUP BY diagnostic_principal
                     ORDER BY nb DESC LIMIT 5""")
        top_diagnostics = c.fetchall()

        # Consultations par mois
        c.execute("""SELECT strftime('%Y-%m', date_consultation) as mois, COUNT(*) as nb
                     FROM consultations
                     WHERE date_consultation >= date('now', '-6 months')
                     GROUP BY mois ORDER BY mois""")
        cons_par_mois = c.fetchall()

        # Occupation des lits
        c.execute("""SELECT s.code, s.nom, s.type, s.capacite,
                            COUNT(h.id) as occupe
                     FROM salles s
                     LEFT JOIN hospitalisations h ON h.salle_id = s.id AND h.statut='En cours'
                     WHERE s.actif=1 AND s.type IN ('Chambre', 'Urgence')
                     GROUP BY s.id ORDER BY s.batiment, s.code""")
        occupation = c.fetchall()

        # Patients par département
        c.execute("""SELECT d.nom as dept, COUNT(DISTINCT c.patient_id) as nb
                     FROM consultations c
                     JOIN departements d ON c.departement_id = d.id
                     WHERE c.departement_id IS NOT NULL
                     GROUP BY d.id ORDER BY nb DESC""")
        patients_par_dept = c.fetchall()

        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-chart-line"></i> Rapports & Statistiques</h2>
          <div class="page-subtitle">Tableau de bord analytique de la clinique</div>
        </div>

        <div class="stats">
          <div class="stat-card"><i class="fas fa-hospital-user stat-icon"></i><div class="stat-value">{total_patients}</div><div class="stat-label">Patients</div></div>
          <div class="stat-card green"><i class="fas fa-user-doctor stat-icon"></i><div class="stat-value">{total_medecins}</div><div class="stat-label">Médecins</div></div>
          <div class="stat-card purple"><i class="fas fa-stethoscope stat-icon"></i><div class="stat-value">{total_consultations}</div><div class="stat-label">Consultations</div></div>
          <div class="stat-card amber"><i class="fas fa-bed-pulse stat-icon"></i><div class="stat-value">{hosp_en_cours}</div><div class="stat-label">Hospitalisations</div></div>
        </div>

        <div class="stats">
          <div class="stat-card"><i class="fas fa-file-invoice stat-icon"></i><div class="stat-value">{total_emis:,.0f}</div><div class="stat-label">CA Total (FCFA)</div></div>
          <div class="stat-card green"><i class="fas fa-check-circle stat-icon"></i><div class="stat-value">{total_paye:,.0f}</div><div class="stat-label">Encaissé (FCFA)</div></div>
          <div class="stat-card rose"><i class="fas fa-exclamation-triangle stat-icon"></i><div class="stat-value">{total_impaye:,.0f}</div><div class="stat-label">Impayés (FCFA)</div></div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-chart-bar"></i> Top 5 diagnostics</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Diagnostic</th><th>Nombre de cas</th><th>Barre</th></tr></thead>
              <tbody>
        """
        max_nb = max([d['nb'] for d in top_diagnostics], default=1)
        for d in top_diagnostics:
            pct = int((d['nb'] / max_nb) * 100)
            content += f"""<tr>
              <td><strong>{d['diagnostic_principal']}</strong></td>
              <td>{d['nb']}</td>
              <td><div style="background:#e2e8f0;border-radius:6px;height:20px;width:100%;overflow:hidden"><div style="background:linear-gradient(90deg,#0a4d68,#05bfdb);height:100%;width:{pct}%"></div></div></td>
            </tr>"""
        if not top_diagnostics:
            content += '<tr><td colspan="3" class="empty">Aucune donnée</td></tr>'

        content += """
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-calendar"></i> Consultations par mois</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Mois</th><th>Nombre de consultations</th><th>Barre</th></tr></thead>
              <tbody>
        """
        max_mois = max([m['nb'] for m in cons_par_mois], default=1)
        for m in cons_par_mois:
            pct = int((m['nb'] / max_mois) * 100)
            content += f"""<tr>
              <td><strong>{m['mois']}</strong></td>
              <td>{m['nb']}</td>
              <td><div style="background:#e2e8f0;border-radius:6px;height:20px;width:100%;overflow:hidden"><div style="background:linear-gradient(90deg,#16a34a,#22c55e);height:100%;width:{pct}%"></div></div></td>
            </tr>"""
        if not cons_par_mois:
            content += '<tr><td colspan="3" class="empty">Aucune donnée</td></tr>'

        content += """
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-bed"></i> Occupation des lits</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Salle</th><th>Type</th><th>Capacité</th><th>Occupé</th><th>Disponible</th><th>Taux</th></tr></thead>
              <tbody>
        """
        for o in occupation:
            dispo = o['capacite'] - o['occupe']
            taux = int((o['occupe'] / o['capacite'] * 100) if o['capacite'] > 0 else 0)
            color = '#16a34a' if taux < 50 else ('#f59e0b' if taux < 80 else '#dc2626')
            content += f"""<tr>
              <td><strong>{o['code']}</strong></td>
              <td>{o['nom']}</td>
              <td>{o['type']}</td>
              <td>{o['capacite']}</td>
              <td>{o['occupe']}</td>
              <td>{dispo}</td>
              <td><span style="color:{color};font-weight:700">{taux}%</span></td>
            </tr>"""
        if not occupation:
            content += '<tr><td colspan="7" class="empty">Aucune donnée</td></tr>'

        content += """
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-building"></i> Patients par département</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Département</th><th>Patients</th><th>Barre</th></tr></thead>
              <tbody>
        """
        max_dept = max([d['nb'] for d in patients_par_dept], default=1)
        for d in patients_par_dept:
            pct = int((d['nb'] / max_dept) * 100)
            content += f"""<tr>
              <td><strong>{d['dept']}</strong></td>
              <td>{d['nb']}</td>
              <td><div style="background:#e2e8f0;border-radius:6px;height:20px;width:100%;overflow:hidden"><div style="background:linear-gradient(90deg,#7c3aed,#a855f7);height:100%;width:{pct}%"></div></div></td>
            </tr>"""
        if not patients_par_dept:
            content += '<tr><td colspan="3" class="empty">Aucune donnée</td></tr>'

        content += """
              </tbody>
            </table>
          </div>
        </div>
        """
        return render_page(content, active='rapports', page_title='Rapports')

    @app.route('/api/stats')
    @staff_required
    def api_stats():
        """API JSON pour statistiques"""
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM patients WHERE actif=1")
        patients = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM consultations")
        consultations = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM hospitalisations WHERE statut='En cours'")
        hosp = c.fetchone()[0]
        conn.close()
        return jsonify({
            'patients': patients,
            'consultations': consultations,
            'hospitalisations': hosp,
            'timestamp': datetime.now().isoformat()
        })

    print("[RAPPORTS] ✅ Routes enregistrées")
