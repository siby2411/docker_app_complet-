"""
Portail Patient + Portail Médecin
Vue personnelle adaptée au rôle connecté
"""
from flask import render_template_string, request, redirect, flash
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "/app/data/clinique.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


try:
    from auth import role_required, log_action
    from flask_login import current_user
except ImportError:
    def role_required(*r):
        def deco(f):
            return f
        return deco
    def log_action(*a, **k):
        pass
    current_user = None


def _get_patient_for_user(user):
    """Trouve le patient lié à l'utilisateur connecté"""
    if not user:
        return None
    conn = get_db()
    c = conn.cursor()

    # Essai 1 : colonne user_id (si migration passée)
    try:
        c.execute("SELECT * FROM patients WHERE user_id = ? LIMIT 1", (user.id,))
        p = c.fetchone()
        if p:
            conn.close()
            return p
    except Exception:
        pass

    # Essai 2 : par email
    if hasattr(user, 'email') and user.email:
        c.execute("SELECT * FROM patients WHERE email = ? LIMIT 1", (user.email,))
        p = c.fetchone()
        if p:
            conn.close()
            return p

    # Essai 3 : patient1 -> id 1
    if user.username and user.username.startswith('patient'):
        try:
            pid = int(user.username.replace('patient', ''))
            c.execute("SELECT * FROM patients WHERE id = ? LIMIT 1", (pid,))
            p = c.fetchone()
            if p:
                conn.close()
                return p
        except Exception:
            pass

    conn.close()
    return None


def register_portail_routes(app, render_page):
    """Portail patient — vue personnelle"""

    # ==================== MES INFORMATIONS ====================
    @app.route('/mes-infos')
    @role_required('patient')
    def mes_infos():
        patient = _get_patient_for_user(current_user)
        if not patient:
            flash("Aucun dossier patient associé à votre compte", "warning")
            content = '''
            <div class="card">
              <div class="empty">
                <i class="fas fa-user-slash"></i>
                <h3>Aucun dossier patient</h3>
                <p>Votre compte n'est lié à aucun dossier. Contactez l'accueil.</p>
              </div>
            </div>
            '''
            return render_page(content, active='dashboard', page_title='Mes informations')

        try:
            naiss = datetime.fromisoformat(patient['date_naissance'])
            age = (datetime.now() - naiss).days // 365
        except Exception:
            age = '?'

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user-circle"></i> Mes informations</h2>
          <div class="page-subtitle">Dossier {patient['numero_dossier']}</div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-id-card stat-icon"></i>
            <div class="stat-value" style="font-size:1.1rem">{patient['numero_dossier']}</div>
            <div class="stat-label">N° Dossier</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-fingerprint stat-icon"></i>
            <div class="stat-value" style="font-size:1.1rem">{patient['carte_medicale']}</div>
            <div class="stat-label">Carte médicale</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-cake-candles stat-icon"></i>
            <div class="stat-value">{age} ans</div>
            <div class="stat-label">Âge</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-droplet stat-icon"></i>
            <div class="stat-value">{patient['groupe_sanguin'] or '?'}</div>
            <div class="stat-label">Groupe sanguin</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-address-card"></i> Coordonnées</h3></div>
          <div class="form-grid">
            <div><strong>Nom :</strong> {patient['nom']} {patient['prenom']}</div>
            <div><strong>Sexe :</strong> {'Masculin' if patient['sexe'] == 'M' else 'Féminin'}</div>
            <div><strong>Date de naissance :</strong> {patient['date_naissance']}</div>
            <div><strong>Lieu :</strong> {patient['lieu_naissance'] or '-'}</div>
            <div><strong>Téléphone :</strong> {patient['telephone']}</div>
            <div><strong>Urgence :</strong> {patient['telephone_urgence'] or '-'}</div>
            <div><strong>Email :</strong> {patient['email'] or '-'}</div>
            <div><strong>Adresse :</strong> {patient['adresse'] or '-'}</div>
            <div><strong>Ville :</strong> {patient['ville'] or '-'}</div>
            <div><strong>Région :</strong> {patient['region'] or '-'}</div>
            <div><strong>Assurance :</strong> {patient['assurance'] or 'Aucune'}</div>
            <div><strong>N° assurance :</strong> {patient['numero_assurance'] or '-'}</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-heart-pulse"></i> Informations médicales</h3></div>
          <div style="display:flex;flex-direction:column;gap:12px">
            <div style="padding:12px;background:{'#fee2e2' if patient['allergies'] else '#f0f7f9'};border-radius:8px;border-left:4px solid {'#dc2626' if patient['allergies'] else '#05bfdb'}">
              <strong>⚠️ Allergies :</strong> {patient['allergies'] or 'Aucune connue'}
            </div>
            <div style="padding:12px;background:#fef3c7;border-radius:8px;border-left:4px solid #f59e0b">
              <strong>📋 Antécédents :</strong> {patient['antecedents_medicaux'] or 'Aucun'}
            </div>
            <div style="padding:12px;background:#dbeafe;border-radius:8px;border-left:4px solid #2563eb">
              <strong>💊 Traitement en cours :</strong> {patient['traitement_en_cours'] or 'Aucun'}
            </div>
          </div>
        </div>
        """
        return render_page(content, active='dashboard', page_title='Mes informations')

    # ==================== MES RENDEZ-VOUS ====================
    @app.route('/mes-rdv')
    @role_required('patient')
    def mes_rdv():
        patient = _get_patient_for_user(current_user)
        if not patient:
            flash("Aucun dossier patient associé", "warning")
            return redirect('/')

        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT r.*, m.nom as m_nom, m.prenom as m_prenom, m.specialite
                     FROM rendez_vous r
                     JOIN medecins m ON r.medecin_id = m.id
                     WHERE r.patient_id = ?
                     ORDER BY r.date_rdv DESC, r.heure_rdv DESC""", (patient['id'],))
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <h2><i class="fas fa-calendar-check"></i> Mes rendez-vous</h2>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Heure</th><th>Médecin</th><th>Motif</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for r in rows:
            badge = 'badge-info' if r['statut'] == 'Programmé' else 'badge-success'
            content += f"""<tr>
              <td><strong>{r['date_rdv']}</strong></td>
              <td><i class="fas fa-clock" style="color:#05bfdb"></i> {r['heure_rdv']}</td>
              <td>Dr {r['m_nom']} {r['m_prenom']}<br><small style="color:#94a3b8">{r['specialite']}</small></td>
              <td>{r['motif'] or '-'}</td>
              <td><span class="badge {badge}">{r['statut']}</span></td>
            </tr>"""
        if not rows:
            content += '<tr><td colspan="5" class="empty"><i class="fas fa-calendar-xmark"></i><br>Aucun rendez-vous</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='dashboard', page_title='Mes rendez-vous')

    # ==================== MES CONSULTATIONS ====================
    @app.route('/mes-consultations')
    @role_required('patient')
    def mes_consultations():
        patient = _get_patient_for_user(current_user)
        if not patient:
            return redirect('/')

        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT c.*, m.nom as m_nom, m.prenom as m_prenom, m.specialite
                     FROM consultations c
                     LEFT JOIN medecins m ON c.medecin_id = m.id
                     WHERE c.patient_id = ?
                     ORDER BY c.date_consultation DESC""", (patient['id'],))
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <h2><i class="fas fa-stethoscope"></i> Mon historique médical</h2>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Date</th><th>Médecin</th><th>Motif</th><th>Diagnostic</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for cs in rows:
            badge = 'badge-success' if cs['statut'] == 'Terminé' else 'badge-warning'
            content += f"""<tr>
              <td><strong>{cs['numero']}</strong></td>
              <td>{cs['date_consultation'][:10]}</td>
              <td>Dr {cs['m_nom'] or '?'} {cs['m_prenom'] or ''}</td>
              <td>{cs['motif'][:40] if cs['motif'] else '-'}</td>
              <td>{cs['diagnostic_principal'][:35] if cs['diagnostic_principal'] else '-'}</td>
              <td><span class="badge {badge}">{cs['statut']}</span></td>
            </tr>"""
        if not rows:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-inbox"></i><br>Aucune consultation</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='dashboard', page_title='Mes consultations')

    # ==================== MES FACTURES ====================
    @app.route('/mes-factures')
    @role_required('patient')
    def mes_factures():
        patient = _get_patient_for_user(current_user)
        if not patient:
            return redirect('/')

        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT * FROM factures WHERE patient_id = ?
                     ORDER BY date_emission DESC""", (patient['id'],))
        rows = c.fetchall()
        conn.close()

        total_du = sum((f['montant_total'] - f['montant_paye']) for f in rows)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-file-invoice-dollar"></i> Mes factures</h2>
        </div>
        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-file-invoice stat-icon"></i>
            <div class="stat-value">{len(rows)}</div>
            <div class="stat-label">Factures</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-exclamation-triangle stat-icon"></i>
            <div class="stat-value">{total_du:,.0f}</div>
            <div class="stat-label">Solde dû (FCFA)</div>
          </div>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Date</th><th>Montant</th><th>Payé</th><th>Reste</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for f in rows:
            reste = f['montant_total'] - f['montant_paye']
            badge = 'badge-success' if f['statut'] == 'Payé' else ('badge-warning' if f['statut'] == 'Partiel' else 'badge-danger')
            content += f"""<tr>
              <td><strong>{f['numero']}</strong></td>
              <td>{f['date_emission'][:10]}</td>
              <td><strong>{f['montant_total']:,.0f}</strong> FCFA</td>
              <td style="color:#16a34a">{f['montant_paye']:,.0f}</td>
              <td style="color:{'#dc2626' if reste > 0 else '#16a34a'}"><strong>{reste:,.0f}</strong></td>
              <td><span class="badge {badge}">{f['statut']}</span></td>
            </tr>"""
        if not rows:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-inbox"></i><br>Aucune facture</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='dashboard', page_title='Mes factures')

    # ==================== PORTAIL MÉDECIN : AGENDA ====================
    @app.route('/medecin/agenda')
    @role_required('admin', 'medecin')
    def medecin_agenda():
        # Trouver le médecin associé à l'utilisateur connecté
        medecin = None
        if current_user:
            conn = get_db()
            c = conn.cursor()
            # Essai par user_id
            try:
                c.execute("SELECT * FROM medecins WHERE user_id = ? LIMIT 1", (current_user.id,))
                medecin = c.fetchone()
            except Exception:
                pass
            # Essai par username (medecin1 -> id 1)
            if not medecin and current_user.username.startswith('medecin'):
                try:
                    mid = int(current_user.username.replace('medecin', ''))
                    c.execute("SELECT * FROM medecins WHERE id = ?", (mid,))
                    medecin = c.fetchone()
                except Exception:
                    pass
            conn.close()

        # Aujourd'hui et demain
        today = datetime.now().date()
        week_end = today + timedelta(days=7)

        conn = get_db()
        c = conn.cursor()
        if medecin:
            c.execute("""SELECT r.*, p.nom as p_nom, p.prenom as p_prenom, p.numero_dossier
                         FROM rendez_vous r
                         JOIN patients p ON r.patient_id = p.id
                         WHERE r.medecin_id = ?
                           AND r.date_rdv BETWEEN ? AND ?
                         ORDER BY r.date_rdv, r.heure_rdv""",
                      (medecin['id'], today.isoformat(), week_end.isoformat()))
        else:
            c.execute("""SELECT r.*, p.nom as p_nom, p.prenom as p_prenom, p.numero_dossier
                         FROM rendez_vous r
                         JOIN patients p ON r.patient_id = p.id
                         WHERE r.date_rdv BETWEEN ? AND ?
                         ORDER BY r.date_rdv, r.heure_rdv""",
                      (today.isoformat(), week_end.isoformat()))
        rdvs = c.fetchall()
        conn.close()

        med_name = f"Dr {medecin['nom']} {medecin['prenom']}" if medecin else "Tous les médecins"

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-calendar-days"></i> Agenda — 7 prochains jours</h2>
          <div class="page-subtitle">{med_name}</div>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Heure</th><th>Patient</th><th>Motif</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for r in rdvs:
            badge = 'badge-info' if r['statut'] == 'Programmé' else 'badge-success'
            content += f"""<tr>
              <td><strong>{r['date_rdv']}</strong></td>
              <td><i class="fas fa-clock" style="color:#05bfdb"></i> {r['heure_rdv']}</td>
              <td>{r['p_nom']} {r['p_prenom']}<br><small style="color:#94a3b8">{r['numero_dossier']}</small></td>
              <td>{r['motif'] or '-'}</td>
              <td><span class="badge {badge}">{r['statut']}</span></td>
            </tr>"""
        if not rdvs:
            content += '<tr><td colspan="5" class="empty"><i class="fas fa-calendar"></i><br>Aucun rendez-vous cette semaine</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='dashboard', page_title='Agenda médecin')

    # ==================== PORTAIL MÉDECIN : FILE D'ATTENTE ====================
    @app.route('/medecin/file-attente')
    @role_required('admin', 'medecin', 'infirmier')
    def medecin_file_attente():
        conn = get_db()
        c = conn.cursor()
        # Consultations du jour en cours
        c.execute("""SELECT c.*, p.nom as p_nom, p.prenom as p_prenom, p.numero_dossier,
                            m.nom as m_nom, m.prenom as m_prenom
                     FROM consultations c
                     JOIN patients p ON c.patient_id = p.id
                     LEFT JOIN medecins m ON c.medecin_id = m.id
                     WHERE date(c.date_consultation) = date('now')
                       AND c.statut = 'En cours'
                     ORDER BY c.date_consultation ASC""")
        rows = c.fetchall()
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-users-line"></i> File d'attente</h2>
          <div class="page-subtitle">Consultations en cours aujourd'hui</div>
        </div>
        <div class="stats">
          <div class="stat-card amber">
            <i class="fas fa-hourglass-half stat-icon"></i>
            <div class="stat-value">{len(rows)}</div>
            <div class="stat-label">Patients en attente</div>
          </div>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Patient</th><th>Médecin</th><th>Motif</th><th>Heure arrivée</th><th>Action</th></tr></thead>
              <tbody>
        """
        for cs in rows:
            content += f"""<tr>
              <td><strong>{cs['numero']}</strong></td>
              <td>{cs['p_nom']} {cs['p_prenom']}<br><small style="color:#94a3b8">{cs['numero_dossier']}</small></td>
              <td>Dr {cs['m_nom'] or '?'} {cs['m_prenom'] or ''}</td>
              <td>{cs['motif'][:40] if cs['motif'] else '-'}</td>
              <td>{cs['date_consultation'][11:19]}</td>
              <td><a href="/consultations/{cs['id']}" class="btn btn-primary btn-sm"><i class="fas fa-arrow-right"></i> Traiter</a></td>
            </tr>"""
        if not rows:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-check-circle"></i><br>Aucun patient en attente</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='dashboard', page_title="File d'attente")

    print("[PORTAIL] ✅ Routes portail patient + médecin enregistrées")
