"""
Module Comptabilité — Clinique Omega
Journal comptable, Rapport Z, Tableau de bord financier
"""
from flask import render_template_string, request, redirect, flash, jsonify
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "/app/data/clinique.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


try:
    from auth import role_required, admin_required, caisse_required
    from flask_login import current_user
except ImportError:
    def role_required(*r):
        def deco(f):
            return f
        return deco
    def admin_required(f):
        return f
    def caisse_required(f):
        return f
    current_user = None


def register_compta_routes(app, render_page):
    """Routes comptabilité"""

    # ==================== TABLEAU DE BORD FINANCIER ====================
    @app.route('/comptabilite')
    @caisse_required
    def comptabilite():
        conn = get_db()
        c = conn.cursor()

        # Aujourd'hui
        today = datetime.now().date().isoformat()
        c.execute("""SELECT
                        COUNT(*) as nb,
                        COALESCE(SUM(montant_total), 0) as total,
                        COALESCE(SUM(montant_paye), 0) as paye
                     FROM factures
                     WHERE date(date_emission) = ?""", (today,))
        row = c.fetchone()
        today_nb = row['nb']
        today_total = row['total']
        today_paye = row['paye']

        # Ce mois
        c.execute("""SELECT
                        COUNT(*) as nb,
                        COALESCE(SUM(montant_total), 0) as total,
                        COALESCE(SUM(montant_paye), 0) as paye
                     FROM factures
                     WHERE strftime('%Y-%m', date_emission) = strftime('%Y-%m', 'now')""")
        row = c.fetchone()
        mois_nb = row['nb']
        mois_total = row['total']
        mois_paye = row['paye']

        # Total général
        c.execute("""SELECT
                        COUNT(*) as nb,
                        COALESCE(SUM(montant_total), 0) as total,
                        COALESCE(SUM(montant_paye), 0) as paye
                     FROM factures""")
        row = c.fetchone()
        total_nb = row['nb']
        total_total = row['total']
        total_paye = row['paye']

        # Par mode de paiement
        c.execute("""SELECT mode_paiement, COUNT(*) as nb, COALESCE(SUM(montant_paye), 0) as total
                     FROM factures
                     WHERE mode_paiement IS NOT NULL AND mode_paiement != ''
                     GROUP BY mode_paiement
                     ORDER BY total DESC""")
        modes = c.fetchall()

        # Par mois (6 derniers)
        c.execute("""SELECT strftime('%Y-%m', date_emission) as mois,
                            COUNT(*) as nb,
                            COALESCE(SUM(montant_total), 0) as total,
                            COALESCE(SUM(montant_paye), 0) as paye
                     FROM factures
                     WHERE date_emission >= date('now', '-6 months')
                     GROUP BY mois ORDER BY mois DESC""")
        par_mois = c.fetchall()

        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-calculator"></i> Comptabilité</h2>
          <a href="/comptabilite/rapport-z" class="btn btn-primary"><i class="fas fa-receipt"></i> Rapport Z</a>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-calendar-day stat-icon"></i>
            <div class="stat-value">{today_paye:,.0f}</div>
            <div class="stat-label">Encaissé aujourd'hui</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-calendar-alt stat-icon"></i>
            <div class="stat-value">{mois_paye:,.0f}</div>
            <div class="stat-label">Encaissé ce mois</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-chart-line stat-icon"></i>
            <div class="stat-value">{total_paye:,.0f}</div>
            <div class="stat-label">Total encaissé (FCFA)</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-exclamation-triangle stat-icon"></i>
            <div class="stat-value">{total_total - total_paye:,.0f}</div>
            <div class="stat-label">Impayés (FCFA)</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-wallet"></i> Répartition par mode de paiement</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Mode</th><th>Nombre</th><th>Total</th><th>%</th></tr></thead>
              <tbody>
        """
        for m in modes:
            pct = (m['total'] / total_paye * 100) if total_paye > 0 else 0
            content += f"""<tr>
              <td><strong>{m['mode_paiement']}</strong></td>
              <td>{m['nb']}</td>
              <td><strong>{m['total']:,.0f}</strong> FCFA</td>
              <td>{pct:.1f}%</td>
            </tr>"""
        if not modes:
            content += '<tr><td colspan="4" class="empty">Aucune donnée</td></tr>'

        content += """
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-chart-column"></i> Historique mensuel</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Mois</th><th>Nb factures</th><th>Total émis</th><th>Encaissé</th><th>Taux</th></tr></thead>
              <tbody>
        """
        for m in par_mois:
            taux = (m['paye'] / m['total'] * 100) if m['total'] > 0 else 0
            content += f"""<tr>
              <td><strong>{m['mois']}</strong></td>
              <td>{m['nb']}</td>
              <td>{m['total']:,.0f} FCFA</td>
              <td style="color:#16a34a"><strong>{m['paye']:,.0f}</strong> FCFA</td>
              <td>{taux:.1f}%</td>
            </tr>"""
        if not par_mois:
            content += '<tr><td colspan="5" class="empty">Aucune donnée</td></tr>'

        content += "</tbody></table></div></div>"
        return render_page(content, active='comptabilite', page_title='Comptabilité')

    # ==================== RAPPORT Z ====================
    @app.route('/comptabilite/rapport-z')
    @caisse_required
    def rapport_z():
        # Date (par défaut aujourd'hui)
        date_str = request.args.get('date', datetime.now().date().isoformat())

        conn = get_db()
        c = conn.cursor()

        # Factures du jour
        c.execute("""SELECT f.*, p.nom as p_nom, p.prenom as p_prenom
                     FROM factures f
                     JOIN patients p ON f.patient_id = p.id
                     WHERE date(f.date_emission) = ?
                     ORDER BY f.date_emission""", (date_str,))
        factures = c.fetchall()

        # Totaux
        c.execute("""SELECT
                        COUNT(*) as nb,
                        COALESCE(SUM(montant_total), 0) as total,
                        COALESCE(SUM(montant_paye), 0) as paye
                     FROM factures
                     WHERE date(date_emission) = ?""", (date_str,))
        totaux = c.fetchone()

        # Par mode
        c.execute("""SELECT mode_paiement, COUNT(*) as nb, COALESCE(SUM(montant_paye), 0) as total
                     FROM factures
                     WHERE date(date_emission) = ?
                       AND mode_paiement IS NOT NULL AND mode_paiement != ''
                     GROUP BY mode_paiement
                     ORDER BY total DESC""", (date_str,))
        modes = c.fetchall()

        # Consultations du jour
        c.execute("""SELECT COUNT(*) FROM consultations WHERE date(date_consultation) = ?""", (date_str,))
        nb_consultations = c.fetchone()[0]

        # Hospitalisations actives
        c.execute("""SELECT COUNT(*) FROM hospitalisations WHERE statut='En cours'""")
        nb_hosp = c.fetchone()[0]

        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-receipt"></i> Rapport Z — {date_str}</h2>
          <div style="display:flex;gap:10px">
            <form method="GET" style="display:flex;gap:8px">
              <input type="date" name="date" value="{date_str}" style="padding:8px 12px;border:2px solid #e2e8f0;border-radius:6px">
              <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-search"></i></button>
            </form>
            <button onclick="window.print()" class="btn btn-info btn-sm"><i class="fas fa-print"></i> Imprimer</button>
          </div>
        </div>

        <div class="card">
          <div style="text-align:center;padding:20px;border-bottom:2px solid #05bfdb;margin-bottom:20px">
            <h1 style="color:#0a4d68">CLINIQUE <span style="color:#05bfdb">OMEGA</span></h1>
            <p style="color:#64748b;font-size:0.9rem">Rapport de caisse journalier</p>
            <p style="color:#0a4d68;font-weight:700;font-size:1.1rem">{date_str}</p>
          </div>

          <div class="stats">
            <div class="stat-card">
              <i class="fas fa-file-invoice stat-icon"></i>
              <div class="stat-value">{totaux['nb']}</div>
              <div class="stat-label">Factures</div>
            </div>
            <div class="stat-card green">
              <i class="fas fa-check-circle stat-icon"></i>
              <div class="stat-value">{totaux['paye']:,.0f}</div>
              <div class="stat-label">Encaissé</div>
            </div>
            <div class="stat-card purple">
              <i class="fas fa-stethoscope stat-icon"></i>
              <div class="stat-value">{nb_consultations}</div>
              <div class="stat-label">Consultations</div>
            </div>
            <div class="stat-card amber">
              <i class="fas fa-bed-pulse stat-icon"></i>
              <div class="stat-value">{nb_hosp}</div>
              <div class="stat-label">Hospit.</div>
            </div>
          </div>

          <h3 style="margin:25px 0 15px;color:#0a4d68;border-left:4px solid #05bfdb;padding-left:12px">
            <i class="fas fa-wallet"></i> Détail par mode de paiement
          </h3>
          <table style="width:100%;border-collapse:collapse">
            <thead><tr style="background:#f0f7f9"><th style="padding:10px;text-align:left">Mode</th><th style="padding:10px;text-align:right">Nb</th><th style="padding:10px;text-align:right">Total</th></tr></thead>
            <tbody>
        """
        for m in modes:
            content += f"""<tr style="border-bottom:1px solid #e2e8f0">
              <td style="padding:10px">{m['mode_paiement']}</td>
              <td style="padding:10px;text-align:right">{m['nb']}</td>
              <td style="padding:10px;text-align:right"><strong>{m['total']:,.0f} FCFA</strong></td>
            </tr>"""
        if not modes:
            content += '<tr><td colspan="3" style="padding:15px;text-align:center;color:#94a3b8">Aucun paiement</td></tr>'
        content += f"""
            <tr style="background:#dcfce7;font-weight:700">
              <td style="padding:12px">TOTAL</td>
              <td style="padding:12px;text-align:right">{totaux['nb']}</td>
              <td style="padding:12px;text-align:right;color:#16a34a;font-size:1.1rem">{totaux['paye']:,.0f} FCFA</td>
            </tr>
          </tbody></table>

          <h3 style="margin:30px 0 15px;color:#0a4d68;border-left:4px solid #05bfdb;padding-left:12px">
            <i class="fas fa-list"></i> Détail des factures
          </h3>
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Patient</th><th>Montant</th><th>Payé</th><th>Mode</th><th>Heure</th></tr></thead>
              <tbody>
        """
        for f in factures:
            content += f"""<tr>
              <td><strong>{f['numero']}</strong></td>
              <td>{f['p_nom']} {f['p_prenom']}</td>
              <td>{f['montant_total']:,.0f}</td>
              <td style="color:#16a34a">{f['montant_paye']:,.0f}</td>
              <td>{f['mode_paiement'] or '-'}</td>
              <td>{f['date_emission'][11:16]}</td>
            </tr>"""
        if not factures:
            content += '<tr><td colspan="6" class="empty">Aucune facture ce jour</td></tr>'

        content += f"""
          </tbody></table>
          </div>

          <div style="margin-top:30px;padding-top:20px;border-top:2px dashed #cbd5e0;text-align:center;color:#64748b;font-size:0.85rem">
            <p>Édité le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
            <p style="margin-top:8px"><strong>OMEGA INFORMATIQUE</strong> — Dakar, Sénégal</p>
          </div>
        </div>
        """
        return render_page(content, active='comptabilite', page_title=f'Rapport Z {date_str}')

    # ==================== API STATS FINANCIÈRES ====================
    @app.route('/api/compta/stats')
    @caisse_required
    def api_compta_stats():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT
                        COALESCE(SUM(montant_total), 0) as total,
                        COALESCE(SUM(montant_paye), 0) as paye
                     FROM factures""")
        row = c.fetchone()
        conn.close()
        return jsonify({
            'total_emis': row['total'],
            'total_encaisse': row['paye'],
            'impayes': row['total'] - row['paye'],
            'timestamp': datetime.now().isoformat()
        })

    print("[COMPTA] ✅ Routes comptabilité enregistrées")
