"""
Module CRUD complet pour Clinique Omega
Patients, Médecins, Personnel, Départements, Salles, Consultations,
Prescriptions, Hospitalisations, Factures, Rendez-vous
"""
from flask import render_template_string, request, redirect, flash, jsonify
import sqlite3
from datetime import datetime

DB_PATH = "/app/data/clinique.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def gen_numero(prefix, table):
    """Génère un numéro séquentiel PREFIX-YYYY-NNNN"""
    conn = get_db()
    c = conn.cursor()
    year = datetime.now().year
    c.execute(f"SELECT COUNT(*) FROM {table}")
    n = c.fetchone()[0] + 1
    conn.close()
    return f"{prefix}-{year}-{n:04d}"


# ==================== DÉCORATEURS (importés depuis auth) ====================
try:
    from auth import role_required, admin_required, staff_required, medecin_required, caisse_required, log_action
    from flask_login import current_user
except ImportError:
    def role_required(*r):
        def deco(f): return f
        return deco
    def admin_required(f): return f
    def staff_required(f): return f
    def medecin_required(f): return f
    def caisse_required(f): return f
    def log_action(*a, **k): pass
    current_user = None


def register_crud_routes(app, render_page):
    """Enregistre toutes les routes CRUD sur l'app Flask"""

    # ==================== PATIENTS ====================
    @app.route('/patients/nouveau', methods=['GET', 'POST'])
    @staff_required
    def patient_nouveau():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                numero = gen_numero('PAT', 'patients')
                carte = f"CM-{datetime.now().strftime('%y%m%d%H%M%S')}"

                c.execute("""INSERT INTO patients
                    (numero_dossier, carte_medicale, nom, prenom, date_naissance,
                     lieu_naissance, sexe, groupe_sanguin, telephone, telephone_urgence,
                     email, adresse, ville, region, profession, situation_matrimoniale,
                     personne_contact, allergies, antecedents_medicaux, traitement_en_cours,
                     assurance, numero_assurance, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (numero, carte,
                     request.form['nom'].strip(),
                     request.form['prenom'].strip(),
                     request.form['date_naissance'],
                     request.form.get('lieu_naissance', ''),
                     request.form['sexe'],
                     request.form.get('groupe_sanguin', ''),
                     request.form['telephone'].strip(),
                     request.form.get('telephone_urgence', ''),
                     request.form.get('email', ''),
                     request.form.get('adresse', ''),
                     request.form.get('ville', ''),
                     request.form.get('region', ''),
                     request.form.get('profession', ''),
                     request.form.get('situation_matrimoniale', ''),
                     request.form.get('personne_contact', ''),
                     request.form.get('allergies', ''),
                     request.form.get('antecedents_medicaux', ''),
                     request.form.get('traitement_en_cours', ''),
                     request.form.get('assurance', ''),
                     request.form.get('numero_assurance', '')))
                conn.commit()
                patient_id = c.lastrowid
                conn.close()

                if current_user and current_user.is_authenticated:
                    log_action(current_user.id, 'CREATE_PATIENT', f'{numero} - {request.form["nom"]} {request.form["prenom"]}')

                flash(f"✅ Patient {numero} créé avec succès", "success")
                return redirect(f'/patients/{patient_id}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = """
        <div class="page-header">
          <h2><i class="fas fa-user-plus"></i> Nouveau Patient</h2>
        </div>
        <div class="card">
          <form method="POST">
            <h3 style="margin-bottom:15px;color:#0a4d68"><i class="fas fa-id-card"></i> Informations personnelles</h3>
            <div class="form-grid">
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" required></div>
              <div class="form-group"><label>Date de naissance *</label><input type="date" name="date_naissance" required></div>
              <div class="form-group"><label>Lieu de naissance</label><input type="text" name="lieu_naissance"></div>
              <div class="form-group"><label>Sexe *</label>
                <select name="sexe" required>
                  <option value="">-- Sélectionner --</option>
                  <option value="M">Masculin</option>
                  <option value="F">Féminin</option>
                </select>
              </div>
              <div class="form-group"><label>Groupe sanguin</label>
                <select name="groupe_sanguin">
                  <option value="">-- Inconnu --</option>
                  <option>O+</option><option>O-</option>
                  <option>A+</option><option>A-</option>
                  <option>B+</option><option>B-</option>
                  <option>AB+</option><option>AB-</option>
                </select>
              </div>
            </div>

            <h3 style="margin:25px 0 15px;color:#0a4d68"><i class="fas fa-phone"></i> Coordonnées</h3>
            <div class="form-grid">
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" required></div>
              <div class="form-group"><label>Téléphone urgence</label><input type="tel" name="telephone_urgence"></div>
              <div class="form-group"><label>Email</label><input type="email" name="email"></div>
              <div class="form-group"><label>Adresse</label><input type="text" name="adresse"></div>
              <div class="form-group"><label>Ville</label><input type="text" name="ville"></div>
              <div class="form-group"><label>Région</label><input type="text" name="region"></div>
            </div>

            <h3 style="margin:25px 0 15px;color:#0a4d68"><i class="fas fa-briefcase"></i> Situation</h3>
            <div class="form-grid">
              <div class="form-group"><label>Profession</label><input type="text" name="profession"></div>
              <div class="form-group"><label>Situation matrimoniale</label>
                <select name="situation_matrimoniale">
                  <option value="">--</option>
                  <option>Célibataire</option><option>Marié(e)</option>
                  <option>Divorcé(e)</option><option>Veuf(ve)</option>
                </select>
              </div>
              <div class="form-group"><label>Personne à contacter</label><input type="text" name="personne_contact"></div>
            </div>

            <h3 style="margin:25px 0 15px;color:#0a4d68"><i class="fas fa-heart-pulse"></i> Informations médicales</h3>
            <div class="form-grid">
              <div class="form-group form-full"><label>Allergies connues</label><textarea name="allergies" rows="2" placeholder="Ex : Pénicilline, arachides..."></textarea></div>
              <div class="form-group form-full"><label>Antécédents médicaux</label><textarea name="antecedents_medicaux" rows="2"></textarea></div>
              <div class="form-group form-full"><label>Traitement en cours</label><textarea name="traitement_en_cours" rows="2"></textarea></div>
            </div>

            <h3 style="margin:25px 0 15px;color:#0a4d68"><i class="fas fa-shield-halved"></i> Assurance</h3>
            <div class="form-grid">
              <div class="form-group"><label>Assurance</label>
                <select name="assurance">
                  <option value="">Aucune</option>
                  <option>IPM</option><option>SUNU</option>
                  <option>Mutuelles</option><option>AXA</option>
                  <option>Autre</option>
                </select>
              </div>
              <div class="form-group"><label>N° assurance</label><input type="text" name="numero_assurance"></div>
            </div>

            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/patients" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='patients', page_title='Nouveau patient')

    @app.route('/patients/<int:pid>')
    @staff_required
    def patient_detail(pid):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM patients WHERE id=?", (pid,))
        p = c.fetchone()
        if not p:
            conn.close()
            flash("Patient introuvable", "danger")
            return redirect('/patients')

        c.execute("""SELECT c.*, m.nom as m_nom, m.prenom as m_prenom
                     FROM consultations c
                     LEFT JOIN medecins m ON c.medecin_id = m.id
                     WHERE c.patient_id = ? ORDER BY c.date_consultation DESC""", (pid,))
        consultations = c.fetchall()

        c.execute("""SELECT h.*, s.nom as salle_nom, s.batiment
                     FROM hospitalisations h
                     LEFT JOIN salles s ON h.salle_id = s.id
                     WHERE h.patient_id = ? ORDER BY h.date_entree DESC""", (pid,))
        hospitalisations = c.fetchall()

        c.execute("""SELECT * FROM factures WHERE patient_id = ? ORDER BY date_emission DESC""", (pid,))
        factures = c.fetchall()
        conn.close()

        # Calcul âge
        try:
            naiss = datetime.fromisoformat(p['date_naissance'])
            age = (datetime.now() - naiss).days // 365
        except:
            age = '?'

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user"></i> {p['nom']} {p['prenom']}</h2>
          <div style="display:flex;gap:10px">
            <a href="/patients/{pid}/modifier" class="btn btn-warning"><i class="fas fa-edit"></i> Modifier</a>
            <a href="/consultations/nouvelle?patient_id={pid}" class="btn btn-primary"><i class="fas fa-stethoscope"></i> Nouvelle consultation</a>
            <a href="/factures/nouvelle?patient_id={pid}" class="btn btn-success"><i class="fas fa-file-invoice"></i> Nouvelle facture</a>
          </div>
        </div>

        <div class="stats">
          <div class="stat-card">
            <i class="fas fa-id-card stat-icon"></i>
            <div class="stat-value" style="font-size:1.2rem">{p['numero_dossier']}</div>
            <div class="stat-label">N° Dossier</div>
          </div>
          <div class="stat-card green">
            <i class="fas fa-fingerprint stat-icon"></i>
            <div class="stat-value" style="font-size:1.2rem">{p['carte_medicale']}</div>
            <div class="stat-label">Carte médicale</div>
          </div>
          <div class="stat-card purple">
            <i class="fas fa-cake-candles stat-icon"></i>
            <div class="stat-value">{age} ans</div>
            <div class="stat-label">Âge</div>
          </div>
          <div class="stat-card rose">
            <i class="fas fa-droplet stat-icon"></i>
            <div class="stat-value">{p['groupe_sanguin'] or '?'}</div>
            <div class="stat-label">Groupe sanguin</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-user-circle"></i> Informations</h3></div>
          <div class="form-grid" style="gap:20px">
            <div><strong>Sexe :</strong> {'Masculin' if p['sexe']=='M' else 'Féminin'}</div>
            <div><strong>Né(e) le :</strong> {p['date_naissance']} {('à ' + p['lieu_naissance']) if p['lieu_naissance'] else ''}</div>
            <div><strong>Téléphone :</strong> {p['telephone']}</div>
            <div><strong>Urgence :</strong> {p['telephone_urgence'] or '-'}</div>
            <div><strong>Email :</strong> {p['email'] or '-'}</div>
            <div><strong>Adresse :</strong> {p['adresse'] or '-'}, {p['ville'] or ''} {p['region'] or ''}</div>
            <div><strong>Profession :</strong> {p['profession'] or '-'}</div>
            <div><strong>Situation :</strong> {p['situation_matrimoniale'] or '-'}</div>
            <div><strong>Assurance :</strong> {p['assurance'] or 'Aucune'} {('(' + p['numero_assurance'] + ')') if p['numero_assurance'] else ''}</div>
            <div><strong>Personne à contacter :</strong> {p['personne_contact'] or '-'}</div>
          </div>
          {'<div style="margin-top:15px;padding:12px;background:#fee2e2;border-radius:8px;border-left:4px solid #dc2626"><strong>⚠️ Allergies :</strong> ' + p['allergies'] + '</div>' if p['allergies'] else ''}
          {'<div style="margin-top:10px;padding:12px;background:#fef3c7;border-radius:8px;border-left:4px solid #f59e0b"><strong>📋 Antécédents :</strong> ' + p['antecedents_medicaux'] + '</div>' if p['antecedents_medicaux'] else ''}
          {'<div style="margin-top:10px;padding:12px;background:#dbeafe;border-radius:8px;border-left:4px solid #2563eb"><strong>💊 Traitement :</strong> ' + p['traitement_en_cours'] + '</div>' if p['traitement_en_cours'] else ''}
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-stethoscope"></i> Consultations ({len(consultations)})</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Date</th><th>Médecin</th><th>Motif</th><th>Diagnostic</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for cs in consultations:
            badge = 'badge-success' if cs['statut']=='Terminé' else 'badge-warning'
            content += f"""<tr>
              <td><strong>{cs['numero']}</strong></td>
              <td>{cs['date_consultation'][:10]}</td>
              <td>Dr {cs['m_nom'] or '?'} {cs['m_prenom'] or ''}</td>
              <td>{cs['motif'][:40] if cs['motif'] else '-'}</td>
              <td>{cs['diagnostic_principal'][:35] if cs['diagnostic_principal'] else '-'}</td>
              <td><span class="badge {badge}">{cs['statut']}</span></td>
            </tr>"""
        if not consultations:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-inbox"></i><br>Aucune consultation</td></tr>'

        content += """
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-bed-pulse"></i> Hospitalisations ({})</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Entrée</th><th>Sortie</th><th>Chambre</th><th>Motif</th><th>Statut</th></tr></thead>
              <tbody>
        """.format(len(hospitalisations))
        for h in hospitalisations:
            badge = 'badge-warning' if h['statut']=='En cours' else 'badge-success'
            content += f"""<tr>
              <td><strong>{h['numero']}</strong></td>
              <td>{h['date_entree'][:10]}</td>
              <td>{h['date_sortie'][:10] if h['date_sortie'] else '-'}</td>
              <td>{h['salle_nom'] or '-'} ({h['batiment'] or ''})</td>
              <td>{h['motif'][:35] if h['motif'] else '-'}</td>
              <td><span class="badge {badge}">{h['statut']}</span></td>
            </tr>"""
        if not hospitalisations:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-inbox"></i><br>Aucune hospitalisation</td></tr>'

        content += """
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-file-invoice-dollar"></i> Factures ({})</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Date</th><th>Montant</th><th>Payé</th><th>Reste</th><th>Statut</th></tr></thead>
              <tbody>
        """.format(len(factures))
        for f in factures:
            reste = f['montant_total'] - f['montant_paye']
            badge = 'badge-success' if f['statut']=='Payé' else ('badge-warning' if f['statut']=='Partiel' else 'badge-danger')
            content += f"""<tr>
              <td><strong>{f['numero']}</strong></td>
              <td>{f['date_emission'][:10]}</td>
              <td><strong>{f['montant_total']:,.0f}</strong> FCFA</td>
              <td style="color:#16a34a">{f['montant_paye']:,.0f}</td>
              <td style="color:#dc2626">{reste:,.0f}</td>
              <td><span class="badge {badge}">{f['statut']}</span></td>
            </tr>"""
        if not factures:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-inbox"></i><br>Aucune facture</td></tr>'

        content += """
              </tbody>
            </table>
          </div>
        </div>
        """
        return render_page(content, active='patients', page_title=f"{p['nom']} {p['prenom']}")

    @app.route('/patients/<int:pid>/modifier', methods=['GET', 'POST'])
    @staff_required
    def patient_modifier(pid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE patients SET
                    nom=?, prenom=?, date_naissance=?, lieu_naissance=?, sexe=?,
                    groupe_sanguin=?, telephone=?, telephone_urgence=?, email=?,
                    adresse=?, ville=?, region=?, profession=?, situation_matrimoniale=?,
                    personne_contact=?, allergies=?, antecedents_medicaux=?,
                    traitement_en_cours=?, assurance=?, numero_assurance=?
                    WHERE id=?""",
                    (request.form['nom'], request.form['prenom'], request.form['date_naissance'],
                     request.form.get('lieu_naissance', ''), request.form['sexe'],
                     request.form.get('groupe_sanguin', ''), request.form['telephone'],
                     request.form.get('telephone_urgence', ''), request.form.get('email', ''),
                     request.form.get('adresse', ''), request.form.get('ville', ''),
                     request.form.get('region', ''), request.form.get('profession', ''),
                     request.form.get('situation_matrimoniale', ''),
                     request.form.get('personne_contact', ''),
                     request.form.get('allergies', ''), request.form.get('antecedents_medicaux', ''),
                     request.form.get('traitement_en_cours', ''),
                     request.form.get('assurance', ''), request.form.get('numero_assurance', ''),
                     pid))
                conn.commit()
                conn.close()
                if current_user and current_user.is_authenticated:
                    log_action(current_user.id, 'UPDATE_PATIENT', f'ID {pid}')
                flash("✅ Patient mis à jour", "success")
                return redirect(f'/patients/{pid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM patients WHERE id=?", (pid,))
        p = c.fetchone()
        conn.close()

        if not p:
            flash("Patient introuvable", "danger")
            return redirect('/patients')

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user-edit"></i> Modifier {p['nom']} {p['prenom']}</h2>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{p['nom']}" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" value="{p['prenom']}" required></div>
              <div class="form-group"><label>Date de naissance *</label><input type="date" name="date_naissance" value="{p['date_naissance']}" required></div>
              <div class="form-group"><label>Lieu de naissance</label><input type="text" name="lieu_naissance" value="{p['lieu_naissance'] or ''}"></div>
              <div class="form-group"><label>Sexe *</label>
                <select name="sexe" required>
                  <option value="M" {"selected" if p['sexe']=='M' else ""}>Masculin</option>
                  <option value="F" {"selected" if p['sexe']=='F' else ""}>Féminin</option>
                </select>
              </div>
              <div class="form-group"><label>Groupe sanguin</label>
                <select name="groupe_sanguin">
                  <option value="">-- Inconnu --</option>
                  {''.join(f'<option {"selected" if p["groupe_sanguin"]==g else ""}>{g}</option>' for g in ['O+','O-','A+','A-','B+','B-','AB+','AB-'])}
                </select>
              </div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" value="{p['telephone']}" required></div>
              <div class="form-group"><label>Urgence</label><input type="tel" name="telephone_urgence" value="{p['telephone_urgence'] or ''}"></div>
              <div class="form-group"><label>Email</label><input type="email" name="email" value="{p['email'] or ''}"></div>
              <div class="form-group"><label>Adresse</label><input type="text" name="adresse" value="{p['adresse'] or ''}"></div>
              <div class="form-group"><label>Ville</label><input type="text" name="ville" value="{p['ville'] or ''}"></div>
              <div class="form-group"><label>Région</label><input type="text" name="region" value="{p['region'] or ''}"></div>
              <div class="form-group"><label>Profession</label><input type="text" name="profession" value="{p['profession'] or ''}"></div>
              <div class="form-group"><label>Situation matrimoniale</label>
                <select name="situation_matrimoniale">
                  <option value="">--</option>
                  {''.join(f'<option {"selected" if p["situation_matrimoniale"]==s else ""}>{s}</option>' for s in ['Célibataire','Marié(e)','Divorcé(e)','Veuf(ve)'])}
                </select>
              </div>
              <div class="form-group"><label>Personne à contacter</label><input type="text" name="personne_contact" value="{p['personne_contact'] or ''}"></div>
              <div class="form-group form-full"><label>Allergies</label><textarea name="allergies" rows="2">{p['allergies'] or ''}</textarea></div>
              <div class="form-group form-full"><label>Antécédents médicaux</label><textarea name="antecedents_medicaux" rows="2">{p['antecedents_medicaux'] or ''}</textarea></div>
              <div class="form-group form-full"><label>Traitement en cours</label><textarea name="traitement_en_cours" rows="2">{p['traitement_en_cours'] or ''}</textarea></div>
              <div class="form-group"><label>Assurance</label>
                <select name="assurance">
                  <option value="">Aucune</option>
                  {''.join(f'<option {"selected" if p["assurance"]==a else ""}>{a}</option>' for a in ['IPM','SUNU','Mutuelles','AXA','Autre'])}
                </select>
              </div>
              <div class="form-group"><label>N° assurance</label><input type="text" name="numero_assurance" value="{p['numero_assurance'] or ''}"></div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/patients/{pid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/patients/{pid}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer la suppression ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='patients', page_title=f'Modifier {p["nom"]}')

    @app.route('/patients/<int:pid>/supprimer')
    @admin_required
    def patient_supprimer(pid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE patients SET actif=0 WHERE id=?", (pid,))
            conn.commit()
            conn.close()
            if current_user and current_user.is_authenticated:
                log_action(current_user.id, 'DELETE_PATIENT', f'ID {pid}')
            flash("✅ Patient archivé", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/patients')


    # ==================== CONSULTATIONS ====================
    @app.route('/consultations/nouvelle', methods=['GET', 'POST'])
    @medecin_required
    def consultation_nouvelle():
        conn = get_db()
        c = conn.cursor()

        if request.method == 'POST':
            try:
                numero = gen_numero('CON', 'consultations')
                c.execute("""INSERT INTO consultations
                    (numero, patient_id, medecin_id, departement_id, date_consultation,
                     motif, temperature, tension, pouls, poids, taille, spo2, glycemie,
                     examen_clinique, diagnostic_principal, code_cim10, diagnostic_secondaire,
                     conduite_tenue, observations, cout, statut)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (numero, int(request.form['patient_id']),
                     int(request.form['medecin_id']),
                     int(request.form['departement_id']) if request.form.get('departement_id') else None,
                     datetime.now().isoformat(),
                     request.form['motif'],
                     float(request.form.get('temperature') or 0) or None,
                     request.form.get('tension', ''),
                     int(request.form.get('pouls') or 0) or None,
                     float(request.form.get('poids') or 0) or None,
                     float(request.form.get('taille') or 0) or None,
                     int(request.form.get('spo2') or 0) or None,
                     float(request.form.get('glycemie') or 0) or None,
                     request.form.get('examen_clinique', ''),
                     request.form.get('diagnostic_principal', ''),
                     request.form.get('code_cim10', ''),
                     request.form.get('diagnostic_secondaire', ''),
                     request.form.get('conduite_tenue', ''),
                     request.form.get('observations', ''),
                     float(request.form.get('cout') or 0),
                     request.form.get('statut', 'En cours')))
                conn.commit()
                cons_id = c.lastrowid

                # Créer facture automatique
                if float(request.form.get('cout') or 0) > 0:
                    num_facture = gen_numero('FAC', 'factures')
                    c.execute("""INSERT INTO factures
                        (numero, patient_id, date_emission, montant_total, statut, observations)
                        VALUES (?, ?, ?, ?, 'Impayé', ?)""",
                        (num_facture, int(request.form['patient_id']),
                         datetime.now().isoformat(), float(request.form['cout']),
                         f'Consultation {numero}'))
                    facture_id = c.lastrowid
                    c.execute("""INSERT INTO lignes_facture
                        (facture_id, designation, quantite, prix_unitaire, montant)
                        VALUES (?, ?, 1, ?, ?)""",
                        (facture_id, f'Consultation - {request.form["motif"]}',
                         float(request.form['cout']), float(request.form['cout'])))
                    conn.commit()

                conn.close()
                if current_user and current_user.is_authenticated:
                    log_action(current_user.id, 'CREATE_CONSULTATION', f'{numero}')
                flash(f"✅ Consultation {numero} enregistrée", "success")
                return redirect(f'/consultations/{cons_id}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        # GET : afficher formulaire
        c.execute("SELECT id, numero_dossier, nom, prenom FROM patients WHERE actif=1 ORDER BY nom")
        patients = c.fetchall()
        c.execute("SELECT id, nom, prenom, specialite FROM medecins WHERE actif=1 ORDER BY nom")
        medecins = c.fetchall()
        c.execute("SELECT id, nom FROM departements WHERE actif=1 ORDER BY nom")
        departements = c.fetchall()
        c.execute("SELECT code, libelle FROM cim10 ORDER BY code")
        cim10 = c.fetchall()
        conn.close()

        patients_opts = "".join(f'<option value="{p["id"]}">{p["numero_dossier"]} - {p["nom"]} {p["prenom"]}</option>' for p in patients)
        medecins_opts = "".join(f'<option value="{m["id"]}">Dr {m["nom"]} {m["prenom"]} ({m["specialite"]})</option>' for m in medecins)
        depts_opts = "".join(f'<option value="{d["id"]}">{d["nom"]}</option>' for d in departements)
        cim10_opts = "".join(f'<option value="{c_["code"]}">{c_["code"]} - {c_["libelle"]}</option>' for c_ in cim10)

        patient_id_pre = request.args.get('patient_id', '')

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-stethoscope"></i> Nouvelle Consultation</h2>
        </div>
        <div class="card">
          <form method="POST">
            <h3 style="margin-bottom:15px;color:#0a4d68"><i class="fas fa-users"></i> Patient & Médecin</h3>
            <div class="form-grid">
              <div class="form-group"><label>Patient *</label>
                <select name="patient_id" required>
                  <option value="">-- Sélectionner --</option>
                  {patients_opts}
                </select>
              </div>
              <div class="form-group"><label>Médecin *</label>
                <select name="medecin_id" required>
                  <option value="">-- Sélectionner --</option>
                  {medecins_opts}
                </select>
              </div>
              <div class="form-group"><label>Département</label>
                <select name="departement_id">
                  <option value="">--</option>
                  {depts_opts}
                </select>
              </div>
              <div class="form-group"><label>Motif *</label><input type="text" name="motif" required placeholder="Ex : Fièvre, douleur..."></div>
            </div>

            <h3 style="margin:25px 0 15px;color:#0a4d68"><i class="fas fa-heart-pulse"></i> Constantes vitales</h3>
            <div class="form-grid">
              <div class="form-group"><label>Température (°C)</label><input type="number" step="0.1" name="temperature" placeholder="37.0"></div>
              <div class="form-group"><label>Tension artérielle</label><input type="text" name="tension" placeholder="12/8"></div>
              <div class="form-group"><label>Pouls (bpm)</label><input type="number" name="pouls" placeholder="80"></div>
              <div class="form-group"><label>Poids (kg)</label><input type="number" step="0.1" name="poids" placeholder="70"></div>
              <div class="form-group"><label>Taille (m)</label><input type="number" step="0.01" name="taille" placeholder="1.75"></div>
              <div class="form-group"><label>SpO2 (%)</label><input type="number" name="spo2" placeholder="98"></div>
              <div class="form-group"><label>Glycémie (g/L)</label><input type="number" step="0.01" name="glycemie"></div>
            </div>

            <h3 style="margin:25px 0 15px;color:#0a4d68"><i class="fas fa-notes-medical"></i> Diagnostic</h3>
            <div class="form-grid">
              <div class="form-group form-full"><label>Examen clinique</label><textarea name="examen_clinique" rows="2"></textarea></div>
              <div class="form-group"><label>Diagnostic principal</label><input type="text" name="diagnostic_principal"></div>
              <div class="form-group"><label>Code CIM-10</label>
                <select name="code_cim10">
                  <option value="">-- Sélectionner --</option>
                  {cim10_opts}
                </select>
              </div>
              <div class="form-group form-full"><label>Diagnostic secondaire</label><input type="text" name="diagnostic_secondaire"></div>
              <div class="form-group form-full"><label>Conduite à tenir / Traitement</label><textarea name="conduite_tenue" rows="3"></textarea></div>
              <div class="form-group form-full"><label>Observations</label><textarea name="observations" rows="2"></textarea></div>
            </div>

            <h3 style="margin:25px 0 15px;color:#0a4d68"><i class="fas fa-money-bill-wave"></i> Facturation</h3>
            <div class="form-grid">
              <div class="form-group"><label>Coût consultation (FCFA)</label><input type="number" name="cout" value="15000"></div>
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  <option value="En cours">En cours</option>
                  <option value="Terminé">Terminé</option>
                </select>
              </div>
            </div>

            <div style="margin-top:25px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer la consultation</button>
              <a href="/consultations" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        <script>
          // Pré-sélectionner patient
          const preId = "{patient_id_pre}";
          if (preId) {{
            document.querySelector('select[name="patient_id"]').value = preId;
          }}
        </script>
        """
        return render_page(content, active='consultations', page_title='Nouvelle consultation')

    @app.route('/consultations/<int:cid>')
    @medecin_required
    def consultation_detail(cid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT c.*, p.nom as p_nom, p.prenom as p_prenom, p.numero_dossier,
                     p.date_naissance, p.sexe, p.telephone, p.allergies,
                     m.nom as m_nom, m.prenom as m_prenom, m.specialite,
                     d.nom as dept_nom
                     FROM consultations c
                     JOIN patients p ON c.patient_id = p.id
                     LEFT JOIN medecins m ON c.medecin_id = m.id
                     LEFT JOIN departements d ON c.departement_id = d.id
                     WHERE c.id = ?""", (cid,))
        cons = c.fetchone()
        if not cons:
            conn.close()
            flash("Consultation introuvable", "danger")
            return redirect('/consultations')

        c.execute("SELECT * FROM prescriptions WHERE consultation_id = ?", (cid,))
        prescriptions = c.fetchall()
        conn.close()

        try:
            naiss = datetime.fromisoformat(cons['date_naissance'])
            age = (datetime.now() - naiss).days // 365
        except:
            age = '?'

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-stethoscope"></i> Consultation {cons['numero']}</h2>
          <div style="display:flex;gap:10px">
            <a href="/consultations/{cid}/prescription" class="btn btn-primary"><i class="fas fa-prescription"></i> Ajouter prescription</a>
            <a href="/consultations" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-user"></i> Patient</h3></div>
          <div class="form-grid">
            <div><strong>Nom :</strong> {cons['p_nom']} {cons['p_prenom']}</div>
            <div><strong>Dossier :</strong> {cons['numero_dossier']}</div>
            <div><strong>Âge :</strong> {age} ans</div>
            <div><strong>Sexe :</strong> {'M' if cons['sexe']=='M' else 'F'}</div>
            <div><strong>Téléphone :</strong> {cons['telephone']}</div>
            <div><strong>Date :</strong> {cons['date_consultation'][:19]}</div>
          </div>
          {('<div style="margin-top:10px;padding:10px;background:#fee2e2;border-radius:6px"><strong>⚠️ Allergies :</strong> ' + cons['allergies'] + '</div>') if cons['allergies'] else ''}
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-heart-pulse"></i> Constantes vitales</h3></div>
          <div class="stats">
            <div class="stat-card"><div class="stat-value">{cons['temperature'] or '-'}</div><div class="stat-label">Température °C</div></div>
            <div class="stat-card"><div class="stat-value">{cons['tension'] or '-'}</div><div class="stat-label">Tension</div></div>
            <div class="stat-card"><div class="stat-value">{cons['pouls'] or '-'}</div><div class="stat-label">Pouls</div></div>
            <div class="stat-card"><div class="stat-value">{cons['poids'] or '-'}</div><div class="stat-label">Poids kg</div></div>
            <div class="stat-card"><div class="stat-value">{cons['taille'] or '-'}</div><div class="stat-label">Taille m</div></div>
            <div class="stat-card"><div class="stat-value">{cons['spo2'] or '-'}</div><div class="stat-label">SpO2 %</div></div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-notes-medical"></i> Diagnostic</h3></div>
          <p><strong>Motif :</strong> {cons['motif']}</p>
          {('<p><strong>Examen clinique :</strong> ' + cons['examen_clinique'] + '</p>') if cons['examen_clinique'] else ''}
          <p><strong>Diagnostic principal :</strong> {cons['diagnostic_principal'] or '-'} {('(' + cons['code_cim10'] + ')') if cons['code_cim10'] else ''}</p>
          {('<p><strong>Diagnostic secondaire :</strong> ' + cons['diagnostic_secondaire'] + '</p>') if cons['diagnostic_secondaire'] else ''}
          {('<p><strong>Conduite à tenir :</strong> ' + cons['conduite_tenue'] + '</p>') if cons['conduite_tenue'] else ''}
          {('<p><strong>Observations :</strong> ' + cons['observations'] + '</p>') if cons['observations'] else ''}
        </div>

        <div class="card">
          <div class="card-header"><h3><i class="fas fa-prescription"></i> Prescriptions ({len(prescriptions)})</h3>
            <a href="/consultations/{cid}/prescription" class="btn btn-primary btn-sm"><i class="fas fa-plus"></i> Ajouter</a>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Médicament</th><th>Dosage</th><th>Posologie</th><th>Durée</th><th>Instructions</th></tr></thead>
              <tbody>
        """
        for pr in prescriptions:
            content += f"""<tr>
              <td><strong>{pr['medicament']}</strong></td>
              <td>{pr['dosage'] or '-'}</td>
              <td>{pr['posologie'] or '-'}</td>
              <td>{pr['duree'] or '-'}</td>
              <td>{pr['instructions'] or '-'}</td>
            </tr>"""
        if not prescriptions:
            content += '<tr><td colspan="5" class="empty"><i class="fas fa-inbox"></i><br>Aucune prescription</td></tr>'

        content += """
              </tbody>
            </table>
          </div>
        </div>
        """
        return render_page(content, active='consultations', page_title=f'Consultation {cons["numero"]}')

    @app.route('/consultations/<int:cid>/prescription', methods=['GET', 'POST'])
    @medecin_required
    def consultation_prescription(cid):
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute("""INSERT INTO prescriptions
                    (consultation_id, medicament, dosage, posologie, duree, instructions)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (cid, request.form['medicament'], request.form.get('dosage', ''),
                     request.form.get('posologie', ''), request.form.get('duree', ''),
                     request.form.get('instructions', '')))
                conn.commit()
                conn.close()
                flash("✅ Prescription ajoutée", "success")
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")
            return redirect(f'/consultations/{cid}')

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-prescription"></i> Ajouter une Prescription</h2>
        </div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group form-full"><label>Médicament *</label><input type="text" name="medicament" required placeholder="Ex : Paracétamol 500mg"></div>
              <div class="form-group"><label>Dosage</label><input type="text" name="dosage" placeholder="Ex : 500mg"></div>
              <div class="form-group"><label>Posologie</label><input type="text" name="posologie" placeholder="Ex : 3x/jour"></div>
              <div class="form-group"><label>Durée</label><input type="text" name="duree" placeholder="Ex : 7 jours"></div>
              <div class="form-group form-full"><label>Instructions</label><textarea name="instructions" rows="2" placeholder="Ex : Après les repas"></textarea></div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/consultations/{cid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='consultations', page_title='Nouvelle prescription')

    print("[CRUD] ✅ Routes patients + consultations enregistrées")


    # ==================== MÉDECINS ====================
    @app.route('/medecins/nouveau', methods=['GET', 'POST'])
    @admin_required
    def medecin_nouveau():
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                code = f"MED-{datetime.now().strftime('%y%m%d%H%M%S')}"
                c.execute("""INSERT INTO medecins
                    (code, nom, prenom, specialite, num_ordre, telephone, email,
                     departement_id, annees_experience, tarif_consultation, biographie, langues, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (code, request.form['nom'], request.form['prenom'], request.form['specialite'],
                     request.form.get('num_ordre', ''), request.form['telephone'],
                     request.form.get('email', ''),
                     int(request.form['departement_id']) if request.form.get('departement_id') else None,
                     int(request.form.get('annees_experience') or 0),
                     float(request.form.get('tarif_consultation') or 0),
                     request.form.get('biographie', ''),
                     request.form.get('langues', '')))
                conn.commit()
                conn.close()
                if current_user and current_user.is_authenticated:
                    log_action(current_user.id, 'CREATE_MEDECIN', code)
                flash(f"✅ Médecin {code} créé", "success")
                return redirect('/medecins')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom FROM departements WHERE actif=1 ORDER BY nom")
        depts = c.fetchall()
        conn.close()
        depts_opts = "".join(f'<option value="{d["id"]}">{d["nom"]}</option>' for d in depts)

        content = f"""
        <div class="page-header"><h2><i class="fas fa-user-doctor"></i> Nouveau Médecin</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" required></div>
              <div class="form-group"><label>Spécialité *</label><input type="text" name="specialite" required placeholder="Ex : Cardiologie"></div>
              <div class="form-group"><label>N° Ordre</label><input type="text" name="num_ordre"></div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email"></div>
              <div class="form-group"><label>Département</label><select name="departement_id"><option value="">--</option>{depts_opts}</select></div>
              <div class="form-group"><label>Années d'expérience</label><input type="number" name="annees_experience" value="0"></div>
              <div class="form-group"><label>Tarif consultation (FCFA)</label><input type="number" name="tarif_consultation" value="15000"></div>
              <div class="form-group"><label>Langues parlées</label><input type="text" name="langues" placeholder="Français, Wolof, Anglais"></div>
              <div class="form-group form-full"><label>Biographie</label><textarea name="biographie" rows="3"></textarea></div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/medecins" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='medecins', page_title='Nouveau médecin')

    @app.route('/medecins/<int:mid>')
    @staff_required
    def medecin_detail(mid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT m.*, d.nom as dept_nom FROM medecins m
                     LEFT JOIN departements d ON m.departement_id = d.id WHERE m.id=?""", (mid,))
        m = c.fetchone()
        if not m:
            conn.close()
            flash("Médecin introuvable", "danger")
            return redirect('/medecins')

        c.execute("""SELECT c.*, p.nom as p_nom, p.prenom as p_prenom
                     FROM consultations c JOIN patients p ON c.patient_id = p.id
                     WHERE c.medecin_id = ? ORDER BY c.date_consultation DESC LIMIT 20""", (mid,))
        consultations = c.fetchall()

        c.execute("SELECT COUNT(*) FROM consultations WHERE medecin_id=?", (mid,))
        total_cons = c.fetchone()[0]
        conn.close()

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-user-doctor"></i> Dr {m['nom']} {m['prenom']}</h2>
          <div style="display:flex;gap:10px">
            <a href="/medecins/{mid}/modifier" class="btn btn-warning"><i class="fas fa-edit"></i> Modifier</a>
            <a href="/medecins" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>
        <div class="stats">
          <div class="stat-card"><i class="fas fa-stethoscope stat-icon"></i><div class="stat-value">{total_cons}</div><div class="stat-label">Consultations</div></div>
          <div class="stat-card green"><i class="fas fa-award stat-icon"></i><div class="stat-value">{m['annees_experience']} ans</div><div class="stat-label">Expérience</div></div>
          <div class="stat-card purple"><i class="fas fa-money-bill stat-icon"></i><div class="stat-value">{m['tarif_consultation']:,.0f}</div><div class="stat-label">Tarif FCFA</div></div>
        </div>
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
          <div class="form-grid">
            <div><strong>Code :</strong> {m['code']}</div>
            <div><strong>Spécialité :</strong> {m['specialite']}</div>
            <div><strong>N° Ordre :</strong> {m['num_ordre'] or '-'}</div>
            <div><strong>Département :</strong> {m['dept_nom'] or '-'}</div>
            <div><strong>Téléphone :</strong> {m['telephone']}</div>
            <div><strong>Email :</strong> {m['email'] or '-'}</div>
            <div><strong>Langues :</strong> {m['langues'] or '-'}</div>
          </div>
          {('<p style="margin-top:15px"><strong>Biographie :</strong> ' + m['biographie'] + '</p>') if m['biographie'] else ''}
        </div>
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-clock-rotate-left"></i> Dernières consultations</h3></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>N°</th><th>Patient</th><th>Motif</th><th>Date</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for cs in consultations:
            badge = 'badge-success' if cs['statut']=='Terminé' else 'badge-warning'
            content += f"""<tr>
              <td><strong>{cs['numero']}</strong></td>
              <td>{cs['p_nom']} {cs['p_prenom']}</td>
              <td>{cs['motif'][:40] if cs['motif'] else '-'}</td>
              <td>{cs['date_consultation'][:10]}</td>
              <td><span class="badge {badge}">{cs['statut']}</span></td>
            </tr>"""
        if not consultations:
            content += '<tr><td colspan="5" class="empty"><i class="fas fa-inbox"></i><br>Aucune consultation</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='medecins', page_title=f'Dr {m["nom"]}')

    @app.route('/medecins/<int:mid>/modifier', methods=['GET', 'POST'])
    @admin_required
    def medecin_modifier(mid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE medecins SET
                    nom=?, prenom=?, specialite=?, num_ordre=?, telephone=?, email=?,
                    departement_id=?, annees_experience=?, tarif_consultation=?,
                    biographie=?, langues=? WHERE id=?""",
                    (request.form['nom'], request.form['prenom'], request.form['specialite'],
                     request.form.get('num_ordre', ''), request.form['telephone'],
                     request.form.get('email', ''),
                     int(request.form['departement_id']) if request.form.get('departement_id') else None,
                     int(request.form.get('annees_experience') or 0),
                     float(request.form.get('tarif_consultation') or 0),
                     request.form.get('biographie', ''), request.form.get('langues', ''), mid))
                conn.commit()
                conn.close()
                flash("✅ Médecin mis à jour", "success")
                return redirect(f'/medecins/{mid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM medecins WHERE id=?", (mid,))
        m = c.fetchone()
        c.execute("SELECT id, nom FROM departements WHERE actif=1 ORDER BY nom")
        depts = c.fetchall()
        conn.close()
        depts_opts = "".join(f'<option value="{d["id"]}" {"selected" if m["departement_id"]==d["id"] else ""}>{d["nom"]}</option>' for d in depts)

        content = f"""
        <div class="page-header"><h2><i class="fas fa-user-edit"></i> Modifier Dr {m['nom']} {m['prenom']}</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{m['nom']}" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" value="{m['prenom']}" required></div>
              <div class="form-group"><label>Spécialité *</label><input type="text" name="specialite" value="{m['specialite']}" required></div>
              <div class="form-group"><label>N° Ordre</label><input type="text" name="num_ordre" value="{m['num_ordre'] or ''}"></div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" value="{m['telephone']}" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email" value="{m['email'] or ''}"></div>
              <div class="form-group"><label>Département</label><select name="departement_id"><option value="">--</option>{depts_opts}</select></div>
              <div class="form-group"><label>Expérience</label><input type="number" name="annees_experience" value="{m['annees_experience']}"></div>
              <div class="form-group"><label>Tarif</label><input type="number" name="tarif_consultation" value="{m['tarif_consultation']}"></div>
              <div class="form-group"><label>Langues</label><input type="text" name="langues" value="{m['langues'] or ''}"></div>
              <div class="form-group form-full"><label>Biographie</label><textarea name="biographie" rows="3">{m['biographie'] or ''}</textarea></div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/medecins/{mid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/medecins/{mid}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='medecins', page_title='Modifier médecin')

    @app.route('/medecins/<int:mid>/supprimer')
    @admin_required
    def medecin_supprimer(mid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE medecins SET actif=0 WHERE id=?", (mid,))
            conn.commit()
            conn.close()
            flash("✅ Médecin archivé", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/medecins')


    # ==================== DÉPARTEMENTS ====================
    @app.route('/departements/nouveau', methods=['GET', 'POST'])
    @admin_required
    def departement_nouveau():
        if request.method == 'POST':
            conn = get_db()
            c = conn.cursor()
            try:
                code = request.form.get('code') or f"DEP-{datetime.now().strftime('%y%m%d%H%M%S')}"
                c.execute("""INSERT INTO departements (code, nom, description, telephone, email, actif)
                    VALUES (?, ?, ?, ?, ?, 1)""",
                    (code, request.form['nom'], request.form.get('description', ''),
                     request.form.get('telephone', ''), request.form.get('email', '')))
                conn.commit()
                conn.close()
                flash(f"✅ Département {code} créé", "success")
                return redirect('/departements')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        content = """
        <div class="page-header"><h2><i class="fas fa-building"></i> Nouveau Département</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code *</label><input type="text" name="code" required placeholder="Ex : DEP-CARD"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required placeholder="Ex : Cardiologie"></div>
              <div class="form-group"><label>Téléphone</label><input type="tel" name="telephone"></div>
              <div class="form-group"><label>Email</label><input type="email" name="email"></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="3"></textarea></div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/departements" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='departements', page_title='Nouveau département')

    @app.route('/departements/<int:did>/modifier', methods=['GET', 'POST'])
    @admin_required
    def departement_modifier(did):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE departements SET code=?, nom=?, description=?, telephone=?, email=? WHERE id=?""",
                    (request.form['code'], request.form['nom'], request.form.get('description', ''),
                     request.form.get('telephone', ''), request.form.get('email', ''), did))
                conn.commit()
                conn.close()
                flash("✅ Département mis à jour", "success")
                return redirect('/departements')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM departements WHERE id=?", (did,))
        d = c.fetchone()
        conn.close()

        content = f"""
        <div class="page-header"><h2><i class="fas fa-edit"></i> Modifier {d['nom']}</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code *</label><input type="text" name="code" value="{d['code']}" required></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{d['nom']}" required></div>
              <div class="form-group"><label>Téléphone</label><input type="tel" name="telephone" value="{d['telephone'] or ''}"></div>
              <div class="form-group"><label>Email</label><input type="email" name="email" value="{d['email'] or ''}"></div>
              <div class="form-group form-full"><label>Description</label><textarea name="description" rows="3">{d['description'] or ''}</textarea></div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/departements" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/departements/{did}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='departements', page_title='Modifier département')

    @app.route('/departements/<int:did>/supprimer')
    @admin_required
    def departement_supprimer(did):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE departements SET actif=0 WHERE id=?", (did,))
            conn.commit()
            conn.close()
            flash("✅ Département archivé", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/departements')


    # ==================== SALLES ====================
    @app.route('/salles/nouvelle', methods=['GET', 'POST'])
    @admin_required
    def salle_nouvelle():
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                code = request.form.get('code') or f"SAL-{datetime.now().strftime('%y%m%d%H%M%S')}"
                c.execute("""INSERT INTO salles
                    (code, nom, site_id, departement_id, batiment, etage, type, capacite, equipements, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (code, request.form['nom'],
                     int(request.form['site_id']),
                     int(request.form['departement_id']) if request.form.get('departement_id') else None,
                     request.form['batiment'], int(request.form.get('etage') or 0),
                     request.form['type'], int(request.form.get('capacite') or 1),
                     request.form.get('equipements', '')))
                conn.commit()
                conn.close()
                flash(f"✅ Salle {code} créée", "success")
                return redirect('/salles')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom FROM sites WHERE actif=1 ORDER BY nom")
        sites = c.fetchall()
        c.execute("SELECT id, nom FROM departements WHERE actif=1 ORDER BY nom")
        depts = c.fetchall()
        conn.close()
        sites_opts = "".join(f'<option value="{s["id"]}">{s["nom"]}</option>' for s in sites)
        depts_opts = "".join(f'<option value="{d["id"]}">{d["nom"]}</option>' for d in depts)

        content = f"""
        <div class="page-header"><h2><i class="fas fa-door-open"></i> Nouvelle Salle</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code *</label><input type="text" name="code" required placeholder="Ex : A101"></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required placeholder="Ex : Consultation Cardio 1"></div>
              <div class="form-group"><label>Site *</label><select name="site_id" required><option value="">--</option>{sites_opts}</select></div>
              <div class="form-group"><label>Département</label><select name="departement_id"><option value="">--</option>{depts_opts}</select></div>
              <div class="form-group"><label>Bâtiment *</label><input type="text" name="batiment" required placeholder="Ex : A"></div>
              <div class="form-group"><label>Étage *</label><input type="number" name="etage" value="0" required></div>
              <div class="form-group"><label>Type *</label>
                <select name="type" required>
                  <option value="Consultation">Consultation</option>
                  <option value="Chambre">Chambre</option>
                  <option value="Urgence">Urgence</option>
                  <option value="Bloc">Bloc opératoire</option>
                  <option value="Imagerie">Imagerie</option>
                  <option value="Laboratoire">Laboratoire</option>
                </select>
              </div>
              <div class="form-group"><label>Capacité (lits)</label><input type="number" name="capacite" value="1"></div>
              <div class="form-group form-full"><label>Équipements</label><textarea name="equipements" rows="2" placeholder="Ex : Échographe, tensiomètre..."></textarea></div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/salles" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='salles', page_title='Nouvelle salle')

    @app.route('/salles/<int:sid>/modifier', methods=['GET', 'POST'])
    @admin_required
    def salle_modifier(sid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE salles SET code=?, nom=?, site_id=?, departement_id=?,
                    batiment=?, etage=?, type=?, capacite=?, equipements=? WHERE id=?""",
                    (request.form['code'], request.form['nom'],
                     int(request.form['site_id']),
                     int(request.form['departement_id']) if request.form.get('departement_id') else None,
                     request.form['batiment'], int(request.form.get('etage') or 0),
                     request.form['type'], int(request.form.get('capacite') or 1),
                     request.form.get('equipements', ''), sid))
                conn.commit()
                conn.close()
                flash("✅ Salle mise à jour", "success")
                return redirect('/salles')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM salles WHERE id=?", (sid,))
        s = c.fetchone()
        c.execute("SELECT id, nom FROM sites WHERE actif=1 ORDER BY nom")
        sites = c.fetchall()
        c.execute("SELECT id, nom FROM departements WHERE actif=1 ORDER BY nom")
        depts = c.fetchall()
        conn.close()
        sites_opts = "".join(f'<option value="{si["id"]}" {"selected" if si["id"]==s["site_id"] else ""}>{si["nom"]}</option>' for si in sites)
        depts_opts = "".join(f'<option value="{d["id"]}" {"selected" if d["id"]==s["departement_id"] else ""}>{d["nom"]}</option>' for d in depts)
        types = ['Consultation','Chambre','Urgence','Bloc','Imagerie','Laboratoire']

        content = f"""
        <div class="page-header"><h2><i class="fas fa-edit"></i> Modifier Salle {s['code']}</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Code *</label><input type="text" name="code" value="{s['code']}" required></div>
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{s['nom']}" required></div>
              <div class="form-group"><label>Site *</label><select name="site_id" required>{sites_opts}</select></div>
              <div class="form-group"><label>Département</label><select name="departement_id"><option value="">--</option>{depts_opts}</select></div>
              <div class="form-group"><label>Bâtiment *</label><input type="text" name="batiment" value="{s['batiment']}" required></div>
              <div class="form-group"><label>Étage *</label><input type="number" name="etage" value="{s['etage']}" required></div>
              <div class="form-group"><label>Type *</label>
                <select name="type" required>
                  {''.join(f'<option value="{t}" {"selected" if s["type"]==t else ""}>{t}</option>' for t in types)}
                </select>
              </div>
              <div class="form-group"><label>Capacité</label><input type="number" name="capacite" value="{s['capacite']}"></div>
              <div class="form-group form-full"><label>Équipements</label><textarea name="equipements" rows="2">{s['equipements'] or ''}</textarea></div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/salles" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/salles/{sid}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='salles', page_title='Modifier salle')

    @app.route('/salles/<int:sid>/supprimer')
    @admin_required
    def salle_supprimer(sid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE salles SET actif=0 WHERE id=?", (sid,))
            conn.commit()
            conn.close()
            flash("✅ Salle archivée", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/salles')


    # ==================== PERSONNEL ====================
    @app.route('/personnel/nouveau', methods=['GET', 'POST'])
    @admin_required
    def personnel_nouveau():
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                code = f"PER-{datetime.now().strftime('%y%m%d%H%M%S')}"
                c.execute("""INSERT INTO personnel
                    (code, nom, prenom, fonction, telephone, email, departement_id, date_embauche, actif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (code, request.form['nom'], request.form['prenom'], request.form['fonction'],
                     request.form['telephone'], request.form.get('email', ''),
                     int(request.form['departement_id']) if request.form.get('departement_id') else None,
                     request.form.get('date_embauche', datetime.now().strftime('%Y-%m-%d'))))
                conn.commit()
                conn.close()
                flash(f"✅ Personnel {code} créé", "success")
                return redirect('/personnel')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, nom FROM departements WHERE actif=1 ORDER BY nom")
        depts = c.fetchall()
        conn.close()
        depts_opts = "".join(f'<option value="{d["id"]}">{d["nom"]}</option>' for d in depts)

        content = f"""
        <div class="page-header"><h2><i class="fas fa-user-nurse"></i> Nouveau Personnel</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" required></div>
              <div class="form-group"><label>Fonction *</label>
                <select name="fonction" required>
                  <option value="Infirmier(ère)">Infirmier(ère)</option>
                  <option value="Aide-soignant(e)">Aide-soignant(e)</option>
                  <option value="Sage-femme">Sage-femme</option>
                  <option value="Secrétaire médicale">Secrétaire médicale</option>
                  <option value="Technicien laboratoire">Technicien laboratoire</option>
                  <option value="Agent d'accueil">Agent d'accueil</option>
                </select>
              </div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email"></div>
              <div class="form-group"><label>Département</label><select name="departement_id"><option value="">--</option>{depts_opts}</select></div>
              <div class="form-group"><label>Date d'embauche</label><input type="date" name="date_embauche" value="{datetime.now().strftime('%Y-%m-%d')}"></div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/personnel" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='personnel', page_title='Nouveau personnel')

    @app.route('/personnel/<int:pid>/modifier', methods=['GET', 'POST'])
    @admin_required
    def personnel_modifier(pid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE personnel SET nom=?, prenom=?, fonction=?, telephone=?,
                    email=?, departement_id=?, date_embauche=? WHERE id=?""",
                    (request.form['nom'], request.form['prenom'], request.form['fonction'],
                     request.form['telephone'], request.form.get('email', ''),
                     int(request.form['departement_id']) if request.form.get('departement_id') else None,
                     request.form.get('date_embauche', ''), pid))
                conn.commit()
                conn.close()
                flash("✅ Personnel mis à jour", "success")
                return redirect('/personnel')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM personnel WHERE id=?", (pid,))
        p = c.fetchone()
        c.execute("SELECT id, nom FROM departements WHERE actif=1 ORDER BY nom")
        depts = c.fetchall()
        conn.close()
        depts_opts = "".join(f'<option value="{d["id"]}" {"selected" if d["id"]==p["departement_id"] else ""}>{d["nom"]}</option>' for d in depts)
        fonctions = ['Infirmier(ère)','Aide-soignant(e)','Sage-femme','Secrétaire médicale','Technicien laboratoire',"Agent d'accueil"]

        content = f"""
        <div class="page-header"><h2><i class="fas fa-user-edit"></i> Modifier {p['nom']} {p['prenom']}</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Nom *</label><input type="text" name="nom" value="{p['nom']}" required></div>
              <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" value="{p['prenom']}" required></div>
              <div class="form-group"><label>Fonction *</label>
                <select name="fonction" required>
                  {''.join(f'<option {"selected" if p["fonction"]==f else ""}>{f}</option>' for f in fonctions)}
                </select>
              </div>
              <div class="form-group"><label>Téléphone *</label><input type="tel" name="telephone" value="{p['telephone']}" required></div>
              <div class="form-group"><label>Email</label><input type="email" name="email" value="{p['email'] or ''}"></div>
              <div class="form-group"><label>Département</label><select name="departement_id"><option value="">--</option>{depts_opts}</select></div>
              <div class="form-group"><label>Date d'embauche</label><input type="date" name="date_embauche" value="{p['date_embauche'] or ''}"></div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/personnel" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
              <a href="/personnel/{pid}/supprimer" class="btn btn-danger" onclick="return confirm('Confirmer ?')"><i class="fas fa-trash"></i> Supprimer</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='personnel', page_title='Modifier personnel')

    @app.route('/personnel/<int:pid>/supprimer')
    @admin_required
    def personnel_supprimer(pid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("UPDATE personnel SET actif=0 WHERE id=?", (pid,))
            conn.commit()
            conn.close()
            flash("✅ Personnel archivé", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/personnel')


    print("[CRUD] ✅ Routes médecins + départements + salles + personnel enregistrées")


    # ==================== FACTURES ====================
    @app.route('/factures/nouvelle', methods=['GET', 'POST'])
    @caisse_required
    def facture_nouvelle():
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                numero = gen_numero('FAC', 'factures')
                c.execute("""INSERT INTO factures
                    (numero, patient_id, date_emission, montant_total, montant_paye,
                     mode_paiement, statut, observations)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (numero, int(request.form['patient_id']),
                     datetime.now().isoformat(),
                     float(request.form.get('montant_total') or 0),
                     float(request.form.get('montant_paye') or 0),
                     request.form.get('mode_paiement', ''),
                     request.form.get('statut', 'Impayé'),
                     request.form.get('observations', '')))
                facture_id = c.lastrowid

                # Lignes de facture
                designations = request.form.getlist('designation[]')
                quantites = request.form.getlist('quantite[]')
                prix = request.form.getlist('prix_unitaire[]')

                for d, q, pu in zip(designations, quantites, prix):
                    if d and pu:
                        qty = int(q or 1)
                        pu_f = float(pu or 0)
                        c.execute("""INSERT INTO lignes_facture
                            (facture_id, designation, quantite, prix_unitaire, montant)
                            VALUES (?, ?, ?, ?, ?)""",
                            (facture_id, d, qty, pu_f, qty * pu_f))

                conn.commit()
                conn.close()
                flash(f"✅ Facture {numero} créée", "success")
                return redirect(f'/factures/{facture_id}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, numero_dossier, nom, prenom FROM patients WHERE actif=1 ORDER BY nom")
        patients = c.fetchall()
        conn.close()
        patients_opts = "".join(f'<option value="{p["id"]}">{p["numero_dossier"]} - {p["nom"]} {p["prenom"]}</option>' for p in patients)
        patient_id_pre = request.args.get('patient_id', '')

        content = f"""
        <div class="page-header"><h2><i class="fas fa-file-invoice"></i> Nouvelle Facture</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Patient *</label><select name="patient_id" required><option value="">--</option>{patients_opts}</select></div>
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  <option value="Impayé">Impayé</option>
                  <option value="Partiel">Partiel</option>
                  <option value="Payé">Payé</option>
                </select>
              </div>
              <div class="form-group"><label>Mode de paiement</label>
                <select name="mode_paiement">
                  <option value="">--</option>
                  <option>Espèces</option><option>Wave</option>
                  <option>Orange Money</option><option>Virement</option>
                  <option>Chèque</option>
                </select>
              </div>
              <div class="form-group"><label>Montant payé (FCFA)</label><input type="number" name="montant_paye" value="0"></div>
            </div>

            <h3 style="margin:25px 0 15px;color:#0a4d68"><i class="fas fa-list"></i> Lignes de facture</h3>
            <div id="lignes">
              <div class="ligne form-grid" style="margin-bottom:10px">
                <div class="form-group"><label>Désignation</label><input type="text" name="designation[]" placeholder="Ex : Consultation"></div>
                <div class="form-group"><label>Quantité</label><input type="number" name="quantite[]" value="1"></div>
                <div class="form-group"><label>Prix unitaire</label><input type="number" name="prix_unitaire[]" placeholder="15000"></div>
              </div>
            </div>
            <button type="button" class="btn btn-info btn-sm" onclick="ajouterLigne()"><i class="fas fa-plus"></i> Ajouter une ligne</button>

            <div class="form-group" style="margin-top:20px"><label>Observations</label><textarea name="observations" rows="2"></textarea></div>
            <input type="hidden" name="montant_total" id="montant_total" value="0">

            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Créer la facture</button>
              <a href="/facturation" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        <script>
          function ajouterLigne() {{
            const container = document.getElementById('lignes');
            const newLigne = document.createElement('div');
            newLigne.className = 'ligne form-grid';
            newLigne.style.marginBottom = '10px';
            newLigne.innerHTML = `
              <div class="form-group"><label>Désignation</label><input type="text" name="designation[]"></div>
              <div class="form-group"><label>Quantité</label><input type="number" name="quantite[]" value="1"></div>
              <div class="form-group"><label>Prix unitaire</label><input type="number" name="prix_unitaire[]"></div>
            `;
            container.appendChild(newLigne);
          }}
          const preId = "{patient_id_pre}";
          if (preId) document.querySelector('select[name="patient_id"]').value = preId;
        </script>
        """
        return render_page(content, active='facturation', page_title='Nouvelle facture')

    @app.route('/factures/<int:fid>')
    @caisse_required
    def facture_detail(fid):
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT f.*, p.nom as p_nom, p.prenom as p_prenom, p.numero_dossier,
                     p.telephone, p.assurance FROM factures f
                     JOIN patients p ON f.patient_id = p.id WHERE f.id=?""", (fid,))
        f = c.fetchone()
        if not f:
            conn.close()
            flash("Facture introuvable", "danger")
            return redirect('/facturation')

        c.execute("SELECT * FROM lignes_facture WHERE facture_id=?", (fid,))
        lignes = c.fetchall()
        conn.close()

        reste = f['montant_total'] - f['montant_paye']

        content = f"""
        <div class="page-header">
          <h2><i class="fas fa-file-invoice"></i> Facture {f['numero']}</h2>
          <div style="display:flex;gap:10px">
            <a href="/factures/{fid}/modifier" class="btn btn-warning"><i class="fas fa-edit"></i> Modifier</a>
            <a href="/facturation" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
          </div>
        </div>
        <div class="card">
          <div style="text-align:center;padding:20px;border-bottom:2px solid #05bfdb;margin-bottom:20px">
            <h1 style="color:#0a4d68">CLINIQUE <span style="color:#05bfdb">OMEGA</span></h1>
            <p style="color:#64748b">Facture N° <strong>{f['numero']}</strong></p>
          </div>
          <div class="form-grid">
            <div><strong>Patient :</strong> {f['p_nom']} {f['p_prenom']}</div>
            <div><strong>Dossier :</strong> {f['numero_dossier']}</div>
            <div><strong>Téléphone :</strong> {f['telephone']}</div>
            <div><strong>Assurance :</strong> {f['assurance'] or 'Aucune'}</div>
            <div><strong>Date :</strong> {f['date_emission'][:10]}</div>
            <div><strong>Mode paiement :</strong> {f['mode_paiement'] or '-'}</div>
          </div>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Désignation</th><th>Qté</th><th>Prix unitaire</th><th>Montant</th></tr></thead>
              <tbody>
        """
        for l in lignes:
            content += f"""<tr>
              <td>{l['designation']}</td>
              <td>{l['quantite']}</td>
              <td>{l['prix_unitaire']:,.0f} FCFA</td>
              <td><strong>{l['montant']:,.0f} FCFA</strong></td>
            </tr>"""
        content += f"""
              </tbody>
              <tfoot>
                <tr style="background:#f0f7f9">
                  <td colspan="3" style="text-align:right"><strong>TOTAL</strong></td>
                  <td><strong>{f['montant_total']:,.0f} FCFA</strong></td>
                </tr>
                <tr style="background:#dcfce7">
                  <td colspan="3" style="text-align:right"><strong>PAYÉ</strong></td>
                  <td><strong style="color:#16a34a">{f['montant_paye']:,.0f} FCFA</strong></td>
                </tr>
                <tr style="background:{'#fee2e2' if reste > 0 else '#dcfce7'}">
                  <td colspan="3" style="text-align:right"><strong>RESTE À PAYER</strong></td>
                  <td><strong style="color:{'#dc2626' if reste > 0 else '#16a34a'}">{reste:,.0f} FCFA</strong></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
        """
        return render_page(content, active='facturation', page_title=f'Facture {f["numero"]}')

    @app.route('/factures/<int:fid>/modifier', methods=['GET', 'POST'])
    @caisse_required
    def facture_modifier(fid):
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""UPDATE factures SET montant_total=?, montant_paye=?,
                    mode_paiement=?, statut=?, observations=? WHERE id=?""",
                    (float(request.form.get('montant_total') or 0),
                     float(request.form.get('montant_paye') or 0),
                     request.form.get('mode_paiement', ''),
                     request.form.get('statut', 'Impayé'),
                     request.form.get('observations', ''), fid))
                conn.commit()
                conn.close()
                flash("✅ Facture mise à jour", "success")
                return redirect(f'/factures/{fid}')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT * FROM factures WHERE id=?", (fid,))
        f = c.fetchone()
        conn.close()
        modes = ['', 'Espèces', 'Wave', 'Orange Money', 'Virement', 'Chèque']

        content = f"""
        <div class="page-header"><h2><i class="fas fa-edit"></i> Modifier Facture {f['numero']}</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Montant total</label><input type="number" name="montant_total" value="{f['montant_total']}"></div>
              <div class="form-group"><label>Montant payé</label><input type="number" name="montant_paye" value="{f['montant_paye']}"></div>
              <div class="form-group"><label>Mode paiement</label>
                <select name="mode_paiement">
                  {''.join(f'<option value="{m}" {"selected" if f["mode_paiement"]==m else ""}>{m or "--"}</option>' for m in modes)}
                </select>
              </div>
              <div class="form-group"><label>Statut</label>
                <select name="statut">
                  {''.join(f'<option value="{s}" {"selected" if f["statut"]==s else ""}>{s}</option>' for s in ['Impayé','Partiel','Payé'])}
                </select>
              </div>
              <div class="form-group form-full"><label>Observations</label><textarea name="observations" rows="2">{f['observations'] or ''}</textarea></div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Enregistrer</button>
              <a href="/factures/{fid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='facturation', page_title='Modifier facture')


    # ==================== HOSPITALISATIONS ====================
    @app.route('/hospitalisations/nouvelle', methods=['GET', 'POST'])
    @medecin_required
    def hospitalisation_nouvelle():
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                numero = gen_numero('HOS', 'hospitalisations')
                c.execute("""INSERT INTO hospitalisations
                    (numero, patient_id, medecin_referent_id, salle_id, lit_numero,
                     date_entree, motif, diagnostic, cout_journalier, statut)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'En cours')""",
                    (numero, int(request.form['patient_id']),
                     int(request.form['medecin_referent_id']) if request.form.get('medecin_referent_id') else None,
                     int(request.form['salle_id']),
                     request.form.get('lit_numero', ''),
                     datetime.now().isoformat(),
                     request.form['motif'],
                     request.form.get('diagnostic', ''),
                     float(request.form.get('cout_journalier') or 0)))
                conn.commit()
                conn.close()
                flash(f"✅ Hospitalisation {numero} enregistrée", "success")
                return redirect('/hospitalisations')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, numero_dossier, nom, prenom FROM patients WHERE actif=1 ORDER BY nom")
        patients = c.fetchall()
        c.execute("SELECT id, nom, prenom FROM medecins WHERE actif=1 ORDER BY nom")
        medecins = c.fetchall()
        c.execute("""SELECT s.id, s.code, s.nom, s.batiment, s.etage, s.type, s.capacite,
                     d.nom as dept_nom FROM salles s
                     LEFT JOIN departements d ON s.departement_id = d.id
                     WHERE s.actif=1 ORDER BY s.batiment, s.etage, s.code""")
        salles = c.fetchall()
        conn.close()

        patients_opts = "".join(f'<option value="{p["id"]}">{p["numero_dossier"]} - {p["nom"]} {p["prenom"]}</option>' for p in patients)
        medecins_opts = "".join(f'<option value="{m["id"]}">Dr {m["nom"]} {m["prenom"]}</option>' for m in medecins)
        salles_opts = "".join(f'<option value="{s["id"]}">{s["code"]} - {s["nom"]} (Bat. {s["batiment"]}, Étage {s["etage"]})</option>' for s in salles)
        patient_id_pre = request.args.get('patient_id', '')

        content = f"""
        <div class="page-header"><h2><i class="fas fa-bed-pulse"></i> Nouvelle Hospitalisation</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Patient *</label><select name="patient_id" required><option value="">--</option>{patients_opts}</select></div>
              <div class="form-group"><label>Médecin référent</label><select name="medecin_referent_id"><option value="">--</option>{medecins_opts}</select></div>
              <div class="form-group"><label>Chambre / Salle *</label><select name="salle_id" required><option value="">--</option>{salles_opts}</select></div>
              <div class="form-group"><label>N° de lit</label><input type="text" name="lit_numero" placeholder="Ex : A101-1"></div>
              <div class="form-group form-full"><label>Motif d'hospitalisation *</label><input type="text" name="motif" required></div>
              <div class="form-group form-full"><label>Diagnostic</label><textarea name="diagnostic" rows="2"></textarea></div>
              <div class="form-group"><label>Coût journalier (FCFA)</label><input type="number" name="cout_journalier" value="25000"></div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Hospitaliser</button>
              <a href="/hospitalisations" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        <script>
          const preId = "{patient_id_pre}";
          if (preId) document.querySelector('select[name="patient_id"]').value = preId;
        </script>
        """
        return render_page(content, active='hospitalisations', page_title='Nouvelle hospitalisation')

    @app.route('/hospitalisations/<int:hid>/sortie')
    @medecin_required
    def hospitalisation_sortie(hid):
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("""UPDATE hospitalisations SET date_sortie=?, statut='Terminé' WHERE id=?""",
                      (datetime.now().isoformat(), hid))
            conn.commit()
            conn.close()
            flash("✅ Sortie enregistrée", "success")
        except Exception as e:
            conn.close()
            flash(f"❌ Erreur : {e}", "danger")
        return redirect('/hospitalisations')


    # ==================== RENDEZ-VOUS ====================
    @app.route('/rendez-vous/nouveau', methods=['GET', 'POST'])
    @staff_required
    def rdv_nouveau():
        conn = get_db()
        c = conn.cursor()
        if request.method == 'POST':
            try:
                c.execute("""INSERT INTO rendez_vous
                    (patient_id, medecin_id, date_rdv, heure_rdv, motif, statut, notes)
                    VALUES (?, ?, ?, ?, ?, 'Programmé', ?)""",
                    (int(request.form['patient_id']),
                     int(request.form['medecin_id']),
                     request.form['date_rdv'],
                     request.form['heure_rdv'],
                     request.form.get('motif', ''),
                     request.form.get('notes', '')))
                conn.commit()
                conn.close()
                flash("✅ Rendez-vous programmé", "success")
                return redirect('/rendez-vous')
            except Exception as e:
                conn.close()
                flash(f"❌ Erreur : {e}", "danger")

        c.execute("SELECT id, numero_dossier, nom, prenom FROM patients WHERE actif=1 ORDER BY nom")
        patients = c.fetchall()
        c.execute("SELECT id, nom, prenom, specialite FROM medecins WHERE actif=1 ORDER BY nom")
        medecins = c.fetchall()
        conn.close()
        patients_opts = "".join(f'<option value="{p["id"]}">{p["numero_dossier"]} - {p["nom"]} {p["prenom"]}</option>' for p in patients)
        medecins_opts = "".join(f'<option value="{m["id"]}">Dr {m["nom"]} {m["prenom"]} ({m["specialite"]})</option>' for m in medecins)

        content = f"""
        <div class="page-header"><h2><i class="fas fa-calendar-plus"></i> Nouveau Rendez-vous</h2></div>
        <div class="card">
          <form method="POST">
            <div class="form-grid">
              <div class="form-group"><label>Patient *</label><select name="patient_id" required><option value="">--</option>{patients_opts}</select></div>
              <div class="form-group"><label>Médecin *</label><select name="medecin_id" required><option value="">--</option>{medecins_opts}</select></div>
              <div class="form-group"><label>Date *</label><input type="date" name="date_rdv" required></div>
              <div class="form-group"><label>Heure *</label><input type="time" name="heure_rdv" required></div>
              <div class="form-group form-full"><label>Motif</label><input type="text" name="motif"></div>
              <div class="form-group form-full"><label>Notes</label><textarea name="notes" rows="2"></textarea></div>
            </div>
            <div style="margin-top:20px;display:flex;gap:10px">
              <button type="submit" class="btn btn-success"><i class="fas fa-save"></i> Programmer</button>
              <a href="/rendez-vous" class="btn btn-info"><i class="fas fa-arrow-left"></i> Annuler</a>
            </div>
          </form>
        </div>
        """
        return render_page(content, active='rendez_vous', page_title='Nouveau rendez-vous')

    @app.route('/rendez-vous')
    @staff_required
    def rdv_liste():
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT r.*, p.nom as p_nom, p.prenom as p_prenom, p.numero_dossier,
                     m.nom as m_nom, m.prenom as m_prenom
                     FROM rendez_vous r
                     JOIN patients p ON r.patient_id = p.id
                     JOIN medecins m ON r.medecin_id = m.id
                     ORDER BY r.date_rdv DESC, r.heure_rdv LIMIT 100""")
        rows = c.fetchall()
        conn.close()

        content = """
        <div class="page-header">
          <h2><i class="fas fa-calendar-check"></i> Rendez-vous</h2>
          <a href="/rendez-vous/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau RDV</a>
        </div>
        <div class="card">
          <div class="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Heure</th><th>Patient</th><th>Médecin</th><th>Motif</th><th>Statut</th></tr></thead>
              <tbody>
        """
        for r in rows:
            badge = 'badge-info' if r['statut']=='Programmé' else 'badge-success'
            content += f"""<tr>
              <td><strong>{r['date_rdv']}</strong></td>
              <td><i class="fas fa-clock" style="color:#05bfdb"></i> {r['heure_rdv']}</td>
              <td>{r['p_nom']} {r['p_prenom']}<br><small style="color:#94a3b8">{r['numero_dossier']}</small></td>
              <td>Dr {r['m_nom']} {r['m_prenom']}</td>
              <td>{r['motif'] or '-'}</td>
              <td><span class="badge {badge}">{r['statut']}</span></td>
            </tr>"""
        if not rows:
            content += '<tr><td colspan="6" class="empty"><i class="fas fa-calendar"></i><br>Aucun rendez-vous</td></tr>'
        content += "</tbody></table></div></div>"
        return render_page(content, active='rendez_vous', page_title='Rendez-vous')


    print("[CRUD] ✅ Routes factures + hospitalisations + rendez-vous enregistrées")
