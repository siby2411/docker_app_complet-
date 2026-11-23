"""
Module Imagerie médicale — Clinique Omega
Radiologie, échographie, scanners
"""
from flask import request, redirect, flash
import sqlite3
from datetime import datetime

DB_PATH = "/app/data/clinique.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


try:
    from auth import role_required, admin_required, staff_required, medecin_required
    from flask_login import current_user
except ImportError:
    def role_required(*r):
        def deco(f): return f
        return deco
    def admin_required(f): return f
    def staff_required(f): return f
    def medecin_required(f): return f
    current_user = None


def _init_imagerie_tables():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS types_examens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        modalite TEXT,
        prix REAL DEFAULT 0,
        preparation TEXT,
        actif INTEGER DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS examens_imagerie (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        patient_id INTEGER NOT NULL,
        medecin_prescripteur_id INTEGER,
        medecin_radiologue_id INTEGER,
        type_examen_id INTEGER NOT NULL,
        date_prescription TEXT NOT NULL,
        date_examen TEXT,
        indication TEXT,
        conclusion TEXT,
        compte_rendu TEXT,
        statut TEXT DEFAULT 'Prescrit',
        fichier_reference TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Seed types d'examens
    c.execute("SELECT COUNT(*) FROM types_examens")
    if c.fetchone()[0] == 0:
        types = [
            ('RX-THX', 'Radiographie thoracique', 'Radiologie', 15000, 'Aucune'),
            ('RX-ABD', 'Radiographie abdomen', 'Radiologie', 15000, 'À jeun 6h'),
            ('RX-GEN', 'Radiographie genou', 'Radiologie', 12000, 'Aucune'),
            ('ECH-ABD', 'Échographie abdominale', 'Échographie', 25000, 'À jeun 8h, vessie pleine'),
            ('ECH-OBS', 'Échographie obstétricale', 'Échographie', 20000, 'Vessie pleine'),
            ('ECH-CAR', 'Échographie cardiaque', 'Échographie', 35000, 'Aucune'),
            ('SCAN-CER', 'Scanner cérébral', 'Scanner', 80000, 'À jeun 6h'),
            ('SCAN-THX', 'Scanner thoracique', 'Scanner', 90000, 'À jeun 6h'),
            ('IRM-CER', 'IRM cérébrale', 'IRM', 150000, 'Retirer objets métalliques'),
            ('MAM', 'Mammographie', 'Mammographie', 30000, 'Éviter déodorant'),
        ]
        for t in types:
            c.execute("""INSERT INTO types_examens
                (code, nom, modalite, prix, preparation) VALUES (?, ?, ?, ?, ?)""", t)

    conn.commit()
    conn.close()


def register_imagerie_routes(app, render_page):
    _init_imagerie_tables()

    # ==================== LISTE ====================
    @app.route('/imagerie')
    @staff_required
    def imagerie_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT e.*, p.nom as p_nom, p.prenom as p_prenom, p.numero_dossier,
                            t.nom as type_nom, t.code as type_code, t.modalite
                     FROM examens_imagerie e
                     JOIN patients p ON e.patient_id = p.id
                     JOIN types_examens t ON e.type_examen_id = t.id
                     ORDER BY e.date_prescription DESC LIMIT 100""")
        rows = c.fetchall()

        c.execute("SELECT COUNT(*) FROM examens_imagerie WHERE statut='Prescrit'")
        prescrits = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM examens_imagerie WHERE statut='Réalisé'")
        realises = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM examens_imagerie")
        total = c.fetchone()[0]
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-x-ray"></i> Imagerie médicale</h2>
          <a href="/imagerie/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle prescription</a>
        </div>
        <div class="stats">
          <div class="stat-card"><i class="fas fa-x-ray stat-icon"></i><div class="stat-value">{total}</div><div class="stat-label">Total examens</div></div>
          <div class="stat-card amber"><i class="fas fa-clock stat-icon"></i><div class="stat-value">{prescrits}</div><div class="stat-label">Prescrits</div></div>
          <div class="stat-card green"><i class="fas fa-check-circle stat-icon"></i><div class="stat-value">{realises}</div><div class="stat-label">Réalisés</div></div>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Patient</th><th>Examen</th><th>Date</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for e in rows:
            badge = 'badge-success' if e['statut'] == 'Réalisé' else ('badge-warning' if e['statut'] == 'En cours' else 'badge-info')
            content += f"""<tr>
              <td><strong>{e['numero']}</strong></td>
              <td>{e['p_nom']} {e['p_prenom']}<br><small style="color:#94a3b8">{e['numero_dossier']}</small></td>
              <td><span class="badge badge-info">{e['type_code']}</span> {e['type_nom']}<br><small>{e['modalite']}</small></td>
              <td>{e['date_prescription'][:10]}</td>
              <td><span class="badge {badge}">{e['statut']}</span></td>
              <td><a href="/imagerie/{e['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a></td>
            </tr>"""
        if not rows:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-x-ray"></i><br>Aucun examen</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='imagerie', page_title='Imagerie')

    # ==================== NOUVELLE PRESCRIPTION ====================
    @app.route('/imagerie/nouvelle', methods=['GET', 'POST'])
    @medecin_required
    def imagerie_nouvelle():
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                year = datetime.now().year
                c.execute("SELECT COUNT(*) FROM examens_imagerie")
                n = c.fetchone()[0] + 1
                numero = f"IMG-{year}-{n:04d}"

                c.execute("""INSERT INTO examens_imagerie
                    (numero, patient_id, medecin_prescripteur_id, type_examen_id,
                     date_prescription, indication, statut)
                    VALUES (?, ?, ?, ?, ?, ?, 'Prescrit')""",
                    (numero, int(request.form['patient_id']),
                     int(request.form['medecin_id']),
                     int(request.form['type_examen_id']),
                     datetime.now().isoformat(),
                     request.form.get('indication', '')))
                ex_id = c.lastrowid
                conn.commit()
                conn.close()
                flash(f"✅ Examen {numero} prescrit", "success")
                return redirect(f'/imagerie/{ex_id}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, numero_dossier, nom, prenom FROM patients WHERE actif=1 ORDER BY nom")
        patients = c.fetchall()
        c.execute("SELECT id, nom, prenom, specialite FROM medecins WHERE actif=1 ORDER BY nom")
        medecins = c.fetchall()
        c.execute("SELECT id, code, nom, modalite, prix, preparation FROM types_examens WHERE actif=1 ORDER BY modalite, nom")
        types = c.fetchall()
        conn.close()

        patients_opts = "".join(f'<option value="{p["id"]}">{p["numero_dossier"]} - {p["nom"]} {p["prenom"]}</option>' for p in patients)
        medecins_opts = "".join(f'<option value="{m["id"]}">Dr {m["nom"]} {m["prenom"]}</option>' for m in medecins)
        types_opts = "".join(f'<option value="{t["id"]}">{t["code"]} - {t["nom"]} ({t["modalite"]}) — {t["prix"]:,.0f} FCFA</option>' for t in types)
        patient_id_pre = request.args.get('patient_id', '')

        content = f"""
        <div class="page-header"><h2><i class="fas fa-x-ray"></i> Nouvelle Prescription d'Imagerie</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Patient *</label>
                <select name="patient_id" required><option value="">--</option>{patients_opts}</select>
              </div>
              <div class="form-group"><label>Médecin prescripteur *</label>
                <select name="medecin_id" required><option value="">--</option>{medecins_opts}</select>
              </div>
              <div class="form-group form-full"><label>Type d'examen *</label>
                <select name="type_examen_id" required><option value="">--</option>{types_opts}</select>
              </div>
              <div class="form-group form-full"><label>Indication clinique</label>
                <textarea name="indication" rows="3" placeholder="Motif médical de l'examen..."></textarea>
              </div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Prescrire</button>
              <a href="/imagerie" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        <script>
          const preId = "{patient_id_pre}";
          if (preId) document.querySelector('select[name="patient_id"]').value = preId;
        </script>
        """
        return render_page(content, active='imagerie', page_title='Nouvel examen')

    # ==================== DÉTAIL / COMPTE RENDU ====================
    @app.route('/imagerie/<int:eid>', methods=['GET', 'POST'])
    @staff_required
    def imagerie_detail(eid):
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                c.execute("""UPDATE examens_imagerie
                    SET date_examen=?, conclusion=?, compte_rendu=?, statut=?,
                        medecin_radiologue_id=?, fichier_reference=?
                    WHERE id=?""",
                    (datetime.now().isoformat() if request.form.get('statut') == 'Réalisé' else None,
                     request.form.get('conclusion', ''),
                     request.form.get('compte_rendu', ''),
                     request.form.get('statut', 'Prescrit'),
                     int(request.form['medecin_radiologue_id']) if request.form.get('medecin_radiologue_id') else None,
                     request.form.get('fichier_reference', ''),
                     eid))
                conn.commit()
                conn.close()
                flash("✅ Compte rendu enregistré", "success")
                return redirect(f'/imagerie/{eid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("""SELECT e.*, p.nom as p_nom, p.prenom as p_prenom, p.numero_dossier,
                            p.date_naissance, p.sexe,
                            t.nom as type_nom, t.code as type_code, t.modalite, t.preparation, t.prix,
                            mp.nom as mp_nom, mp.prenom as mp_prenom
                     FROM examens_imagerie e
                     JOIN patients p ON e.patient_id = p.id
                     JOIN types_examens t ON e.type_examen_id = t.id
                     LEFT JOIN medecins mp ON e.medecin_prescripteur_id = mp.id
                     WHERE e.id=?""", (eid,))
        ex = c.fetchone()
        if not ex:
            conn.close()
            flash("Examen introuvable", "danger")
            return redirect('/imagerie')

        c.execute("SELECT id, nom, prenom FROM medecins WHERE actif=1 ORDER BY nom")
        radiologues = c.fetchall()
        conn.close()

        radiologues_opts = "".join(f'<option value="{r["id"]}" {"selected" if ex["medecin_radiologue_id"]==r["id"] else ""}>Dr {r["nom"]} {r["prenom"]}</option>' for r in radiologues)

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-x-ray"></i> Examen {ex['numero']}</h2>
          <a href="/imagerie" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        </div>

        <div class="card">
          <div class="form-grid">
            <div><strong>Patient :</strong> {ex['p_nom']} {ex['p_prenom']}</div>
            <div><strong>Dossier :</strong> {ex['numero_dossier']}</div>
            <div><strong>Examen :</strong> {ex['type_code']} — {ex['type_nom']}</div>
            <div><strong>Modalité :</strong> {ex['modalite']}</div>
            <div><strong>Date prescription :</strong> {ex['date_prescription'][:16]}</div>
            <div><strong>Médecin prescripteur :</strong> Dr {ex['mp_nom'] or '?'} {ex['mp_prenom'] or ''}</div>
            <div><strong>Prix :</strong> {ex['prix']:,.0f} FCFA</div>
            <div><strong>Préparation :</strong> {ex['preparation'] or 'Aucune'}</div>
          </div>
          {f'<div style="margin-top:15px;padding:12px;background:#fef3c7;border-radius:8px"><strong>Indication :</strong> {ex["indication"]}</div>' if ex['indication'] else ''}
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-notes-medical"></i> Compte rendu</h3></div>
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  <option value="Prescrit" {"selected" if ex['statut']=='Prescrit' else ""}>Prescrit</option>
                  <option value="En cours" {"selected" if ex['statut']=='En cours' else ""}>En cours</option>
                  <option value="Réalisé" {"selected" if ex['statut']=='Réalisé' else ""}>Réalisé</option>
                </select>
              </div>
              <div class="form-group"><label>Médecin radiologue</label>
                <select name="medecin_radiologue_id">
                  <option value="">--</option>
                  {radiologues_opts}
                </select>
              </div>
              <div class="form-group form-full"><label>Conclusion</label>
                <input type="text" name="conclusion" value="{ex['conclusion'] or ''}" placeholder="Résumé diagnostique">
              </div>
              <div class="form-group form-full"><label>Compte rendu détaillé</label>
                <textarea name="compte_rendu" rows="8" placeholder="Description détaillée des observations...">{ex['compte_rendu'] or ''}</textarea>
              </div>
              <div class="form-group form-full"><label>Référence fichier (image/PDF)</label>
                <input type="text" name="fichier_reference" value="{ex['fichier_reference'] or ''}" placeholder="Ex : /dossiers/imagerie/IMG-2026-0001.jpg">
              </div>
            </div>
            <div style="margin-top:20px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer le compte rendu</button>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='imagerie', page_title=f"Examen {ex['numero']}")

    print("[IMAGERIE] ✅ Routes imagerie enregistrées")
