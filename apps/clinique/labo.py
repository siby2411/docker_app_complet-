"""
Module Laboratoire — Clinique Omega
Analyses médicales, résultats, bulletins
"""
from flask import render_template_string, request, redirect, flash, Response
import sqlite3
from datetime import datetime
from io import BytesIO

DB_PATH = "/app/data/clinique.db"

# Import PDF
try:
    from pdf_gen import generer_bulletin_analyse_pdf
    PDF_OK = True
except ImportError as e:
    print(f"[LABO] ⚠️ PDF indisponible: {e}")
    PDF_OK = False


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


try:
    from auth import role_required, admin_required, staff_required, medecin_required, log_action
    from flask_login import current_user
except ImportError:
    def role_required(*r):
        def deco(f): return f
        return deco
    def admin_required(f): return f
    def staff_required(f): return f
    def medecin_required(f): return f
    def log_action(*a, **k): pass
    current_user = None


def _init_labo_tables():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS types_analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
        categorie TEXT,
        prix REAL DEFAULT 0,
        parametres TEXT,
        actif INTEGER DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        patient_id INTEGER NOT NULL,
        medecin_id INTEGER,
        consultation_id INTEGER,
        type_analyse_id INTEGER NOT NULL,
        date_analyse TEXT NOT NULL,
        date_resultat TEXT,
        statut TEXT DEFAULT 'En attente',
        commentaire TEXT,
        technicien_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS resultats_analyse (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analyse_id INTEGER NOT NULL,
        parametre TEXT NOT NULL,
        resultat TEXT,
        unite TEXT,
        valeurs_normales TEXT,
        interpretation TEXT
    )""")

    # Seed types d'analyses si vide
    c.execute("SELECT COUNT(*) FROM types_analyses")
    if c.fetchone()[0] == 0:
        types = [
            ('NFS', 'Numération formule sanguine', 'Hématologie', 8000,
             'Globules rouges|Hémoglobine|Hématocrite|Globules blancs|Plaquettes'),
            ('GLY', 'Glycémie à jeun', 'Biochimie', 3000, 'Glycémie'),
            ('GRP', 'Groupe sanguin + Rhésus', 'Hématologie', 2500, 'Groupe|Rhésus'),
            ('PAL', 'Test paludisme (TDR)', 'Parasitologie', 2000, 'Résultat TDR'),
            ('URI', 'Urine - ECBU', 'Biochimie', 5000, 'Leucocytes|Nitrites|pH|Densite'),
            ('CREA', 'Créatinine sérique', 'Biochimie', 4000, 'Créatinine'),
            ('TRIG', 'Triglycérides', 'Biochimie', 3500, 'Triglycérides'),
            ('CHOL', 'Cholestérol total', 'Biochimie', 3500, 'Cholestérol'),
            ('TSH', 'TSH (Thyroïde)', 'Hormonologie', 12000, 'TSH'),
            ('VIH', 'Test VIH', 'Sérologie', 3000, 'Résultat'),
            ('HEP', 'Hépatite B (AgHBs)', 'Sérologie', 5000, 'Résultat'),
            ('WID', 'Widal (fièvre typhoïde)', 'Sérologie', 6000, 'TO|TH'),
        ]
        for t in types:
            c.execute("""INSERT INTO types_analyses
                (code, nom, categorie, prix, parametres) VALUES (?, ?, ?, ?, ?)""", t)

    conn.commit()
    conn.close()


def register_labo_routes(app, render_page):
    _init_labo_tables()

    # ==================== LISTE DES ANALYSES ====================
    @app.route('/labo')
    @staff_required
    def labo_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT a.*, p.nom as p_nom, p.prenom as p_prenom, p.numero_dossier,
                            t.nom as type_nom, t.code as type_code
                     FROM analyses a
                     JOIN patients p ON a.patient_id = p.id
                     JOIN types_analyses t ON a.type_analyse_id = t.id
                     ORDER BY a.date_analyse DESC LIMIT 100""")
        rows = c.fetchall()

        c.execute("SELECT COUNT(*) FROM analyses WHERE statut='En attente'")
        en_attente = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM analyses WHERE statut='Terminé'")
        termines = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM analyses")
        total = c.fetchone()[0]
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-flask"></i> Laboratoire d'analyses</h2>
          <a href="/labo/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle analyse</a>
        </div>

        <div class="stats">
          <div class="stat-card"><i class="fas fa-flask stat-icon"></i><div class="stat-value">{total}</div><div class="stat-label">Total analyses</div></div>
          <div class="stat-card amber"><i class="fas fa-hourglass-half stat-icon"></i><div class="stat-value">{en_attente}</div><div class="stat-label">En attente</div></div>
          <div class="stat-card green"><i class="fas fa-check-circle stat-icon"></i><div class="stat-value">{termines}</div><div class="stat-label">Terminées</div></div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-list"></i> Analyses récentes</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Patient</th><th>Type</th><th>Date</th><th>Statut</th><th>Actions</th></tr></thead>
              <tbody>
        """
        for a in rows:
            badge = 'badge-success' if a['statut'] == 'Terminé' else ('badge-warning' if a['statut'] == 'En cours' else 'badge-info')
            content += f"""<tr>
              <td><strong>{a['numero']}</strong></td>
              <td>{a['p_nom']} {a['p_prenom']}<br><small style="color:#94a3b8">{a['numero_dossier']}</small></td>
              <td><span class="badge badge-info">{a['type_code']}</span> {a['type_nom']}</td>
              <td>{a['date_analyse'][:10]}</td>
              <td><span class="badge {badge}">{a['statut']}</span></td>
              <td>
                <a href="/labo/{a['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
                <a href="/labo/{a['id']}/pdf" class="btn btn-primary btn-sm" target="_blank"><i class="fas fa-file-pdf"></i></a>
              </td>
            </tr>"""
        if not rows:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-flask"></i><br>Aucune analyse</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='labo', page_title='Laboratoire')

    # ==================== NOUVELLE ANALYSE ====================
    @app.route('/labo/nouvelle', methods=['GET', 'POST'])
    @staff_required
    def labo_nouvelle():
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                year = datetime.now().year
                c.execute("SELECT COUNT(*) FROM analyses")
                n = c.fetchone()[0] + 1
                numero = f"LAB-{year}-{n:04d}"

                c.execute("""INSERT INTO analyses
                    (numero, patient_id, medecin_id, consultation_id, type_analyse_id,
                     date_analyse, statut, technicien_id)
                    VALUES (?, ?, ?, ?, ?, ?, 'En attente', ?)""",
                    (numero, int(request.form['patient_id']),
                     int(request.form['medecin_id']) if request.form.get('medecin_id') else None,
                     int(request.form['consultation_id']) if request.form.get('consultation_id') else None,
                     int(request.form['type_analyse_id']),
                     datetime.now().isoformat(),
                     current_user.id if current_user else None))
                analyse_id = c.lastrowid

                # Créer les lignes de résultats (vides) selon le type
                c.execute("SELECT parametres FROM types_analyses WHERE id=?", (int(request.form['type_analyse_id']),))
                row = c.fetchone()
                if row and row['parametres']:
                    params = row['parametres'].split('|')
                    for p in params:
                        c.execute("""INSERT INTO resultats_analyse
                            (analyse_id, parametre) VALUES (?, ?)""", (analyse_id, p.strip()))

                conn.commit()
                conn.close()
                flash(f"✅ Analyse {numero} créée", "success")
                return redirect(f'/labo/{analyse_id}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        # GET
        c.execute("SELECT id, numero_dossier, nom, prenom FROM patients WHERE actif=1 ORDER BY nom")
        patients = c.fetchall()
        c.execute("SELECT id, nom, prenom, specialite FROM medecins WHERE actif=1 ORDER BY nom")
        medecins = c.fetchall()
        c.execute("SELECT id, code, nom, categorie, prix FROM types_analyses WHERE actif=1 ORDER BY categorie, nom")
        types = c.fetchall()
        conn.close()

        patients_opts = "".join(f'<option value="{p["id"]}">{p["numero_dossier"]} - {p["nom"]} {p["prenom"]}</option>' for p in patients)
        medecins_opts = "".join(f'<option value="{m["id"]}">Dr {m["nom"]} {m["prenom"]}</option>' for m in medecins)
        types_opts = "".join(f'<option value="{t["id"]}">{t["code"]} - {t["nom"]} ({t["categorie"]}) — {t["prix"]:,.0f} FCFA</option>' for t in types)
        patient_id_pre = request.args.get('patient_id', '')

        content = f"""
        <div class="page-header"><h2><i class="fas fa-flask"></i> Nouvelle Analyse</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Patient *</label>
                <select name="patient_id" required>
                  <option value="">-- Sélectionner --</option>
                  {patients_opts}
                </select>
              </div>
              <div class="form-group"><label>Médecin prescripteur</label>
                <select name="medecin_id">
                  <option value="">--</option>
                  {medecins_opts}
                </select>
              </div>
              <div class="form-group form-full"><label>Type d'analyse *</label>
                <select name="type_analyse_id" required>
                  <option value="">-- Sélectionner --</option>
                  {types_opts}
                </select>
              </div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Créer l'analyse</button>
              <a href="/labo" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        <script>
          const preId = "{patient_id_pre}";
          if (preId) document.querySelector('select[name="patient_id"]').value = preId;
        </script>
        """
        return render_page(content, active='labo', page_title='Nouvelle analyse')

    # ==================== DÉTAIL / SAISIE RÉSULTATS ====================
    @app.route('/labo/<int:aid>', methods=['GET', 'POST'])
    @staff_required
    def labo_detail(aid):
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                # Mettre à jour les résultats
                for key, val in request.form.items():
                    if key.startswith('resultat_'):
                        result_id = int(key.replace('resultat_', ''))
                        interpretation = request.form.get(f'interpretation_{result_id}', '')
                        unite = request.form.get(f'unite_{result_id}', '')
                        vn = request.form.get(f'vn_{result_id}', '')
                        c.execute("""UPDATE resultats_analyse
                            SET resultat=?, unite=?, valeurs_normales=?, interpretation=?
                            WHERE id=?""",
                            (val, unite, vn, interpretation, result_id))

                # Mettre à jour le statut de l'analyse
                nouveau_statut = request.form.get('statut', 'En cours')
                commentaire = request.form.get('commentaire', '')
                c.execute("""UPDATE analyses SET statut=?, commentaire=?,
                            date_resultat=? WHERE id=?""",
                    (nouveau_statut, commentaire,
                     datetime.now().isoformat() if nouveau_statut == 'Terminé' else None,
                     aid))
                conn.commit()
                conn.close()
                flash("✅ Résultats enregistrés", "success")
                return redirect(f'/labo/{aid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("""SELECT a.*, p.nom as p_nom, p.prenom as p_prenom, p.numero_dossier,
                            p.date_naissance, p.sexe,
                            m.nom as m_nom, m.prenom as m_prenom,
                            t.nom as type_nom, t.code as type_code, t.categorie
                     FROM analyses a
                     JOIN patients p ON a.patient_id = p.id
                     LEFT JOIN medecins m ON a.medecin_id = m.id
                     JOIN types_analyses t ON a.type_analyse_id = t.id
                     WHERE a.id=?""", (aid,))
        analyse = c.fetchone()
        if not analyse:
            conn.close()
            flash("Analyse introuvable", "danger")
            return redirect('/labo')

        c.execute("SELECT * FROM resultats_analyse WHERE analyse_id=? ORDER BY id", (aid,))
        resultats = c.fetchall()
        conn.close()

        try:
            naiss = datetime.fromisoformat(analyse['date_naissance'])
            age = (datetime.now() - naiss).days // 365
        except Exception:
            age = '?'

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-flask"></i> Analyse {analyse['numero']}</h2>
          <div style="display:flex;gap:10px">
            <a href="/labo/{aid}/pdf" class="btn btn-primary" target="_blank"><i class="fas fa-file-pdf"></i> Bulletin PDF</a>
            <a href="/labo" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="card">
          <div class="form-grid">
            <div><strong>Patient :</strong> {analyse['p_nom']} {analyse['p_prenom']}</div>
            <div><strong>Dossier :</strong> {analyse['numero_dossier']}</div>
            <div><strong>Âge :</strong> {age} ans ({analyse['sexe']})</div>
            <div><strong>Type :</strong> {analyse['type_code']} — {analyse['type_nom']}</div>
            <div><strong>Date :</strong> {analyse['date_analyse'][:16]}</div>
            <div><strong>Médecin :</strong> Dr {analyse['m_nom'] or '?'} {analyse['m_prenom'] or ''}</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-notes-medical"></i> Résultats</h3></div>
          <form method="POST">
            <div class="table-wrap">
              <table>
                <thead><tr><th>Paramètre</th><th>Résultat</th><th>Unité</th><th>Valeurs normales</th><th>Interprétation</th></tr></thead>
                <tbody>
        """
        for r in resultats:
            content += f"""<tr>
              <td><strong>{r['parametre']}</strong></td>
              <td><input type="text" name="resultat_{r['id']}" value="{r['resultat'] or ''}" style="width:100%;padding:6px;border:2px solid #e2e8f0;border-radius:5px"></td>
              <td><input type="text" name="unite_{r['id']}" value="{r['unite'] or ''}" style="width:80px;padding:6px;border:2px solid #e2e8f0;border-radius:5px"></td>
              <td><input type="text" name="vn_{r['id']}" value="{r['valeurs_normales'] or ''}" style="width:100%;padding:6px;border:2px solid #e2e8f0;border-radius:5px"></td>
              <td>
                <select name="interpretation_{r['id']}" style="padding:6px;border:2px solid #e2e8f0;border-radius:5px">
                  <option value="" {"selected" if not r['interpretation'] else ""}>—</option>
                  <option value="Normal" {"selected" if r['interpretation']=='Normal' else ""}>Normal</option>
                  <option value="Anormal" {"selected" if r['interpretation']=='Anormal' else ""}>Anormal</option>
                  <option value="Élevé" {"selected" if r['interpretation']=='Élevé' else ""}>Élevé</option>
                  <option value="Bas" {"selected" if r['interpretation']=='Bas' else ""}>Bas</option>
                </select>
              </td>
            </tr>"""
        if not resultats:
            content += '<tr><td colspan="5" class="empty">Aucun paramètre défini</td></tr>'

        content += f"""
                </tbody>
              </table>
            </div>
            <div class="form-grid" style="margin-top:20px">
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  <option value="En attente" {"selected" if analyse['statut']=='En attente' else ""}>En attente</option>
                  <option value="En cours" {"selected" if analyse['statut']=='En cours' else ""}>En cours</option>
                  <option value="Terminé" {"selected" if analyse['statut']=='Terminé' else ""}>Terminé</option>
                </select>
              </div>
              <div class="form-group form-full"><label>Commentaire</label>
                <textarea name="commentaire" rows="2">{analyse['commentaire'] or ''}</textarea>
              </div>
            </div>
            <div style="margin-top:20px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer les résultats</button>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='labo', page_title=f"Analyse {analyse['numero']}")

    # ==================== PDF BULLETIN ====================
    @app.route('/labo/<int:aid>/pdf')
    @staff_required
    def labo_pdf(aid):
        if not PDF_OK:
            flash("Génération PDF indisponible", "warning")
            return redirect(f'/labo/{aid}')

        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT a.*, p.nom as p_nom, p.prenom as p_prenom, p.numero_dossier,
                            t.nom as type_nom, t.code as type_code
                     FROM analyses a
                     JOIN patients p ON a.patient_id = p.id
                     JOIN types_analyses t ON a.type_analyse_id = t.id
                     WHERE a.id=?""", (aid,))
        analyse = c.fetchone()
        if not analyse:
            conn.close()
            flash("Analyse introuvable", "danger")
            return redirect('/labo')

        c.execute("SELECT * FROM resultats_analyse WHERE analyse_id=?", (aid,))
        resultats = [dict(r) for r in c.fetchall()]
        conn.close()

        patient = {
            'nom': analyse['p_nom'], 'prenom': analyse['p_prenom'],
            'numero_dossier': analyse['numero_dossier'],
        }
        analyse_d = {
            'numero': analyse['numero'],
            'date_analyse': analyse['date_analyse'],
            'type_analyse': analyse['type_nom'],
            'statut': analyse['statut'],
            'commentaire': analyse['commentaire'],
        }
        try:
            pdf_bytes = generer_bulletin_analyse_pdf(analyse_d, patient, resultats)
            return Response(
                pdf_bytes, mimetype='application/pdf',
                headers={'Content-Disposition': f'inline; filename="analyse-{analyse["numero"]}.pdf"'}
            )
        except Exception as e:
            flash(f"Erreur PDF: {e}", "danger")
            return redirect(f'/labo/{aid}')

    # ==================== TYPES D'ANALYSES (admin) ====================
    @app.route('/labo/types')
    @admin_required
    def labo_types():
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM types_analyses WHERE actif=1 ORDER BY categorie, nom")
        types = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <h2><i class="fas fa-list"></i> Types d'analyses</h2>
          <a href="/labo/types/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau type</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Nom</th><th>Catégorie</th><th>Prix</th><th>Paramètres</th></tr></thead>
              <tbody>
        """
        for t in types:
            content += f"""<tr>
              <td><strong>{t['code']}</strong></td>
              <td>{t['nom']}</td>
              <td><span class="badge badge-info">{t['categorie'] or '-'}</span></td>
              <td>{t['prix']:,.0f} FCFA</td>
              <td><small>{t['parametres'] or '-'}</small></td>
            </tr>"""
        content += "</tbody></table></div></div>"
        return render_page(content, active='labo', page_title="Types d'analyses")

    @app.route('/labo/types/nouveau', methods=['GET', 'POST'])
    @admin_required
    def labo_type_nouveau():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute("""INSERT INTO types_analyses
                    (code, nom, categorie, prix, parametres, actif)
                    VALUES (?, ?, ?, ?, ?, 1)""",
                    (request.form['code'], request.form['nom'],
                     request.form.get('categorie', ''),
                     float(request.form.get('prix') or 0),
                     request.form.get('parametres', '')))
                conn.commit()
                conn.close()
                flash("✅ Type d'analyse créé", "success")
                return redirect('/labo/types')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = """
        <div class="page-header"><h2><i class="fas fa-plus"></i> Nouveau Type d'Analyse</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code *</label><input type="text" name="code" required placeholder="Ex : NFS"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required placeholder="Ex : Numération formule sanguine"></div>
              <div class="form-group"><label>Catégorie</label>
                <select name="categorie">
                  <option value="">--</option>
                  <option>Hématologie</option>
                  <option>Biochimie</option>
                  <option>Parasitologie</option>
                  <option>Hormonologie</option>
                  <option>Sérologie</option>
                  <option>Microbiologie</option>
                  <option>Urine</option>
                </select>
              </div>
              <div class="form-group"><label>Prix (FCFA)</label><input type="number" name="prix" value="0"></div>
              <div class="form-group form-full"><label>Paramètres (séparés par |)</label>
                <textarea name="parametres" rows="3" placeholder="Globules rouges|Hémoglobine|Hématocrite|Leucocytes|Plaquettes"></textarea>
              </div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/labo/types" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='labo', page_title='Nouveau type analyse')

    print("[LABO] ✅ Routes laboratoire enregistrées")
