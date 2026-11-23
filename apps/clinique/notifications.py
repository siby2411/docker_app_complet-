"""
Module Notifications — Clinique Omega
Envoi SMS, Email, rappels RDV
"""
from flask import request, redirect, flash
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "/app/data/clinique.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


try:
    from auth import role_required, admin_required, staff_required
    from flask_login import current_user
except ImportError:
    def role_required(*r):
        def deco(f): return f
        return deco
    def admin_required(f): return f
    def staff_required(f): return f
    current_user = None


def _init_notif_tables():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        destinataire_type TEXT NOT NULL,
        destinataire_id INTEGER,
        destinataire TEXT NOT NULL,
        canal TEXT NOT NULL,
        sujet TEXT,
        message TEXT NOT NULL,
        statut TEXT DEFAULT 'En attente',
        reference TEXT,
        error_message TEXT,
        date_envoi TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS templates_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        canal TEXT NOT NULL,
        sujet TEXT,
        contenu TEXT NOT NULL,
        actif INTEGER DEFAULT 1
    )""")

    # Seed templates
    c.execute("SELECT COUNT(*) FROM templates_notifications")
    if c.fetchone()[0] == 0:
        templates = [
            ('RDV_RAPPEL', 'Rappel RDV', 'SMS',
             None,
             'Bonjour {nom}, rappel de votre RDV à la Clinique Omega le {date} à {heure} avec Dr {medecin}. Répondez NON pour annuler.'),
            ('RDV_CONFIRM', 'Confirmation RDV', 'SMS',
             None,
             'Bonjour {nom}, votre RDV est confirmé pour le {date} à {heure} avec Dr {medecin}. Clinique Omega.'),
            ('FACTURE', 'Facture disponible', 'EMAIL',
             'Votre facture Clinique Omega',
             'Bonjour {nom},\n\nVotre facture {numero} d\'un montant de {montant} FCFA est disponible.\n\nCordialement,\nClinique Omega'),
            ('RESULTAT', 'Résultats disponibles', 'EMAIL',
             'Vos résultats d\'analyses',
             'Bonjour {nom},\n\nVos résultats d\'analyses ({type}) sont disponibles. Connectez-vous au portail patient.\n\nClinique Omega'),
        ]
        for t in templates:
            c.execute("""INSERT INTO templates_notifications
                (code, nom, canal, sujet, contenu) VALUES (?, ?, ?, ?, ?)""", t)

    conn.commit()
    conn.close()


def register_notifications_routes(app, render_page):
    _init_notif_tables()

    # ==================== LISTE ====================
    @app.route('/notifications')
    @admin_required
    def notifications_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT * FROM notifications ORDER BY created_at DESC LIMIT 100""")
        rows = c.fetchall()

        c.execute("SELECT COUNT(*) FROM notifications WHERE statut='Envoyé'")
        envoyes = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM notifications WHERE statut='En attente'")
        en_attente = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM notifications WHERE statut='Échec'")
        echecs = c.fetchone()[0]
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-bell"></i> Notifications</h2>
          <div style="display:flex;gap:10px">
            <a href="/notifications/nouvelle" class="btn btn-primary"><i class="fas fa-paper-plane"></i> Envoyer</a>
            <a href="/notifications/templates" class="btn btn-info"><i class="fas fa-file-lines"></i> Templates</a>
          </div>
        </div>
        <div class="stats">
          <div class="stat-card green"><i class="fas fa-check stat-icon"></i><div class="stat-value">{envoyes}</div><div class="stat-label">Envoyés</div></div>
          <div class="stat-card amber"><i class="fas fa-clock stat-icon"></i><div class="stat-value">{en_attente}</div><div class="stat-label">En attente</div></div>
          <div class="stat-card rose"><i class="fas fa-times stat-icon"></i><div class="stat-value">{echecs}</div><div class="stat-label">Échecs</div></div>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Destinataire</th><th>Canal</th><th>Message</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for n in rows:
            badge = 'badge-success' if n['statut'] == 'Envoyé' else ('badge-warning' if n['statut'] == 'En attente' else 'badge-danger')
            msg_court = (n['message'][:60] + '...') if len(n['message']) > 60 else n['message']
            content += f"""<tr>
              <td>{n['created_at'][:16]}</td>
              <td>{n['destinataire']}</td>
              <td><span class="badge badge-info">{n['canal']}</span></td>
              <td>{msg_court}</td>
              <td><span class="badge {badge}">{n['statut']}</span></td>
            </tr>"""
        if not rows:
            content += '<tr><td colspan="5" class="empty"><i class="fas fa-bell-slash"></i><br>Aucune notification</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='notifications', page_title='Notifications')

    # ==================== NOUVELLE ====================
    @app.route('/notifications/nouvelle', methods=['GET', 'POST'])
    @admin_required
    def notifications_nouvelle():
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                destinataire = request.form.get('destinataire', '').strip()
                canal = request.form['canal']
                sujet = request.form.get('sujet', '')
                message = request.form['message']

                c.execute("""INSERT INTO notifications
                    (destinataire_type, destinataire, canal, sujet, message, statut)
                    VALUES (?, ?, ?, ?, ?, 'En attente')""",
                    (request.form.get('destinataire_type', 'manuel'),
                     destinataire, canal, sujet, message))
                notif_id = c.lastrowid
                conn.commit()
                conn.close()
                flash(f"✅ Notification #{notif_id} enregistrée (en attente d'envoi)", "success")
                return redirect('/notifications')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, numero_dossier, nom, prenom, telephone, email FROM patients WHERE actif=1 ORDER BY nom LIMIT 200")
        patients = c.fetchall()
        c.execute("SELECT id, code, nom, canal FROM templates_notifications WHERE actif=1")
        templates = c.fetchall()
        conn.close()

        patients_opts = "".join(f'<option value="{p["id"]}" data-tel="{p["telephone"]}" data-email="{p["email"] or ""}">{p["numero_dossier"]} - {p["nom"]} {p["prenom"]}</option>' for p in patients)
        templates_opts = "".join(f'<option value="{t["id"]}" data-canal="{t["canal"]}">{t["nom"]} ({t["canal"]})</option>' for t in templates)

        content = f"""
        <div class="page-header"><h2><i class="fas fa-paper-plane"></i> Nouvelle Notification</h2></div>
        <div class="card">
          <form method="POST" id="notifForm">
            <div class="form-grid">
              <div class="form-group"><label>Type destinataire</label>
                <select name="destinataire_type">
                  <option value="manuel">Manuel</option>
                  <option value="patient">Patient (auto)</option>
                </select>
              </div>
              <div class="form-group"><label>Patient (optionnel)</label>
                <select id="patientSelect" onchange="remplirPatient()">
                  <option value="">-- Sélectionner pour autocompléter --</option>
                  {patients_opts}
                </select>
              </div>
              <div class="form-group form-full"><label>Destinataire (téléphone ou email) *</label>
                <input type="text" name="destinataire" id="destinataire" required>
              </div>
              <div class="form-group"><label>Canal *</label>
                <select name="canal" required>
                  <option value="SMS">SMS</option>
                  <option value="EMAIL">Email</option>
                </select>
              </div>
              <div class="form-group"><label>Template</label>
                <select onchange="remplirTemplate()">
                  <option value="">-- Choisir --</option>
                  {templates_opts}
                </select>
              </div>
              <div class="form-group form-full"><label>Sujet (Email)</label>
                <input type="text" name="sujet" id="sujet">
              </div>
              <div class="form-group form-full"><label>Message *</label>
                <textarea name="message" id="message" rows="5" required></textarea>
              </div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/notifications" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        <script>
          function remplirPatient() {{
            const sel = document.getElementById('patientSelect');
            const opt = sel.options[sel.selectedIndex];
            const tel = opt.getAttribute('data-tel');
            const email = opt.getAttribute('data-email');
            const canal = document.querySelector('select[name="canal"]').value;
            document.getElementById('destinataire').value = canal === 'EMAIL' ? (email || '') : (tel || '');
          }}

          function remplirTemplate() {{
            // Templates statiques pour l'instant
            const select = event.target;
            const opt = select.options[select.selectedIndex];
            const txt = opt.textContent;
            if (txt.includes('Rappel RDV')) {{
              document.querySelector('select[name="canal"]').value = 'SMS';
              document.getElementById('message').value = 'Bonjour {{nom}}, rappel de votre RDV à la Clinique Omega le {{date}} à {{heure}} avec Dr {{medecin}}.';
            }} else if (txt.includes('Confirmation')) {{
              document.querySelector('select[name="canal"]').value = 'SMS';
              document.getElementById('message').value = 'Bonjour {{nom}}, votre RDV est confirmé pour le {{date}} à {{heure}}. Clinique Omega.';
            }} else if (txt.includes('Facture')) {{
              document.querySelector('select[name="canal"]').value = 'EMAIL';
              document.getElementById('sujet').value = 'Votre facture Clinique Omega';
              document.getElementById('message').value = 'Bonjour,\\n\\nVotre facture est disponible.\\n\\nClinique Omega';
            }}
          }}
        </script>
        """
        return render_page(content, active='notifications', page_title='Nouvelle notification')

    # ==================== TEMPLATES ====================
    @app.route('/notifications/templates')
    @admin_required
    def notifications_templates():
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM templates_notifications WHERE actif=1 ORDER BY nom")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <h2><i class="fas fa-file-lines"></i> Templates de notifications</h2>
          <a href="/notifications" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Nom</th><th>Canal</th><th>Sujet</th><th>Contenu</th></tr></thead>
              <tbody>
        """
        for t in rows:
            content += f"""<tr>
              <td><strong>{t['code']}</strong></td>
              <td>{t['nom']}</td>
              <td><span class="badge badge-info">{t['canal']}</span></td>
              <td>{t['sujet'] or '-'}</td>
              <td><small>{t['contenu'][:80]}</small></td>
            </tr>"""
        content += "</tbody></table></div></div>"
        return render_page(content, active='notifications', page_title='Templates')

    # ==================== RAPPELS RDV (BULK) ====================
    @app.route('/notifications/rappels-rdv', methods=['POST'])
    @admin_required
    def notifications_rappels_rdv():
        """Génère des notifications pour tous les RDV de demain"""
        conn = get_db()
        c = conn.cursor()

        demain = (datetime.now() + timedelta(days=1)).date().isoformat()
        c.execute("""SELECT r.*, p.nom as p_nom, p.prenom as p_prenom, p.telephone,
                            m.nom as m_nom, m.prenom as m_prenom
                     FROM rendez_vous r
                     JOIN patients p ON r.patient_id = p.id
                     JOIN medecins m ON r.medecin_id = m.id
                     WHERE r.date_rdv = ? AND r.statut = 'Programmé'""", (demain,))
        rdvs = c.fetchall()

        count = 0
        for r in rdvs:
            message = f"Bonjour {r['p_nom']}, rappel de votre RDV à la Clinique Omega demain {r['date_rdv']} à {r['heure_rdv']} avec Dr {r['m_nom']}."
            c.execute("""INSERT INTO notifications
                (destinataire_type, destinataire_id, destinataire, canal, message, statut, reference)
                VALUES ('patient', ?, ?, 'SMS', ?, 'En attente', ?)""",
                (r['patient_id'], r['telephone'], message, f"RDV-{r['id']}"))
            count += 1

        conn.commit()
        conn.close()
        flash(f"✅ {count} rappels RDV générés (en attente d'envoi)", "success")
        return redirect('/notifications')

    print("[NOTIFICATIONS] ✅ Routes notifications enregistrées")
