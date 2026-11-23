# -*- coding: utf-8 -*-
"""
🚗 OMEGA AUTO — Gestion Parc Automobile (Vente & Location)
Port 9029 · Marché CEDEAO · Design Premium
"""
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_from_directory, Response,
                   abort, make_response)
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta
from io import BytesIO
import sqlite3
import os
import json
import uuid
import qrcode
import random

# ═══════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════
DB_PATH = '/app/data/auto.db'
UPLOAD_DIR = '/app/uploads'
VEHICULES_DIR = os.path.join(UPLOAD_DIR, 'vehicules')
PAPIERS_DIR = os.path.join(UPLOAD_DIR, 'papiers')
ALLOWED_IMG = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_DOC = {'pdf', 'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_VID = {'mp4', 'webm', 'mov'}

for d in (VEHICULES_DIR, PAPIERS_DIR):
    os.makedirs(d, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'omega-auto-cedeao-2026-premium-secret')
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Veuillez vous connecter."

# ═══════════════════════════════════════════════════════════
# HELPERS DB
# ═══════════════════════════════════════════════════════════
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def query(sql, params=(), one=False):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    if one:
        return rows[0] if rows else None
    return rows

def execute(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def audit(action, entity=None, entity_id=None, details=None):
    try:
        execute("""
            INSERT INTO audit_log (user_id, action, entity, entity_id, details, ip, created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (getattr(current_user, 'id', None) if current_user and current_user.is_authenticated else None,
              action, entity, entity_id, details,
              request.remote_addr if request else None,
              datetime.now().isoformat()))
    except Exception:
        pass

def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

def save_upload(file, subdir, allowed):
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename, allowed):
        return None
    ext = file.filename.rsplit('.', 1)[1].lower()
    fname = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(subdir, fname)
    file.save(path)
    return fname

def fmt_money(v):
    try:
        v = float(v or 0)
    except Exception:
        return "0 FCFA"
    return f"{int(v):,}".replace(',', ' ') + " FCFA"

def fmt_date(d):
    if not d:
        return "—"
    try:
        return datetime.fromisoformat(str(d)[:19]).strftime('%d/%m/%Y')
    except Exception:
        return str(d)[:10]

app.jinja_env.filters['money'] = fmt_money
app.jinja_env.filters['dte'] = fmt_date

# ═══════════════════════════════════════════════════════════
# USER MODEL
# ═══════════════════════════════════════════════════════════
class User(UserMixin):
    def __init__(self, row):
        self.id = row['id']
        self.username = row['username']
        self.role = row['role']
        self.nom_complet = row['nom_complet'] or row['username']
        self.email = row['email']
        self.telephone = row['telephone']
        self.agence = row['agence']
        self.whatsapp = row['whatsapp']

    def is_admin(self):
        return self.role == 'admin'

    def is_directeur(self):
        return self.role in ('admin', 'directeur')

    def is_commercial(self):
        return self.role in ('admin', 'directeur', 'commercial')

@login_manager.user_loader
def load_user(user_id):
    row = query("SELECT * FROM users WHERE id=? AND actif=1", (user_id,), one=True)
    return User(row) if row else None

def admin_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash("Accès réservé administrateur.", "error")
            return redirect(url_for('dashboard'))
        return f(*a, **kw)
    return wrap

def role_required(*roles):
    def deco(f):
        @wraps(f)
        def wrap(*a, **kw):
            if not current_user.is_authenticated or current_user.role not in roles:
                flash("Accès non autorisé.", "error")
                return redirect(url_for('dashboard'))
            return f(*a, **kw)
        return wrap
    return deco

# ═══════════════════════════════════════════════════════════
# CONTEXT PROCESSOR
# ═══════════════════════════════════════════════════════════
@app.context_processor
def inject_globals():
    try:
        stats = {
            'vehicules_total': query("SELECT COUNT(*) c FROM vehicules", one=True)['c'],
            'vehicules_dispo': query("SELECT COUNT(*) c FROM vehicules WHERE statut='disponible'", one=True)['c'],
            'clients_total': query("SELECT COUNT(*) c FROM clients", one=True)['c'],
            'ventes_mois': query("SELECT COUNT(*) c FROM ventes WHERE statut='livree'", one=True)['c'],
            'locations_actives': query("SELECT COUNT(*) c FROM locations WHERE statut IN ('reservee','en_cours')", one=True)['c'],
            'alertes_papiers': query("""
                SELECT COUNT(*) c FROM papiers
                WHERE date_expiration IS NOT NULL
                  AND date(date_expiration) <= date('now', '+30 days')
                  AND statut != 'expire'
            """, one=True)['c'],
        }
    except Exception:
        stats = {k: 0 for k in ('vehicules_total', 'vehicules_dispo', 'clients_total',
                                'ventes_mois', 'locations_actives', 'alertes_papiers')}
    return {'stats_sidebar': stats, 'now': datetime.now()}

# ═══════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════
@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/health')
def health():
    return jsonify(status='ok', app='omega-auto', port=9029,
                   time=datetime.now().isoformat())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        row = query("SELECT * FROM users WHERE username=? AND actif=1", (username,), one=True)
        if row and check_password_hash(row['password_hash'], password):
            login_user(User(row))
            audit('login', 'user', row['id'])
            flash(f"Bienvenue {row['nom_complet'] or username} 🚗", "success")
            nxt = request.args.get('next')
            return redirect(nxt or url_for('dashboard'))
        flash("Identifiants invalides.", "error")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    audit('logout', 'user', current_user.id)
    logout_user()
    flash("Déconnexion réussie.", "success")
    return redirect(url_for('login'))

# ═══════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════
@app.route('/')
@login_required
def dashboard():
    kpi = {}
    kpi['vehicules_total'] = query("SELECT COUNT(*) c FROM vehicules", one=True)['c']
    kpi['vehicules_dispo'] = query("SELECT COUNT(*) c FROM vehicules WHERE statut='disponible'", one=True)['c']
    kpi['vehicules_vendus'] = query("SELECT COUNT(*) c FROM vehicules WHERE statut='vendu'", one=True)['c']
    kpi['vehicules_location'] = query("SELECT COUNT(*) c FROM vehicules WHERE disponible_location=1 AND statut='disponible'", one=True)['c']
    kpi['clients_total'] = query("SELECT COUNT(*) c FROM clients", one=True)['c']
    kpi['ca_ventes'] = query("SELECT COALESCE(SUM(montant_ttc),0) c FROM ventes WHERE statut='livree'", one=True)['c']
    kpi['ca_locations'] = query("SELECT COALESCE(SUM(montant_total),0) c FROM locations WHERE statut IN ('terminee','en_cours')", one=True)['c']
    kpi['marge_totale'] = query("SELECT COALESCE(SUM(marge),0) c FROM ventes WHERE statut='livree'", one=True)['c']
    kpi['valeur_stock'] = query("SELECT COALESCE(SUM(prix_vente),0) c FROM vehicules WHERE statut='disponible'", one=True)['c']
    kpi['ventes_mois'] = query("""
        SELECT COUNT(*) c FROM ventes
        WHERE statut='livree' AND strftime('%Y-%m', date_vente) = strftime('%Y-%m','now')
    """, one=True)['c']
    kpi['locations_actives'] = query("SELECT COUNT(*) c FROM locations WHERE statut IN ('reservee','en_cours')", one=True)['c']

    top_marques = query("""
        SELECT m.nom, COUNT(v.id) nb, COALESCE(SUM(v.montant_ttc),0) ca
        FROM ventes v
        JOIN vehicules veh ON veh.id = v.vehicule_id
        JOIN marques m ON m.id = veh.marque_id
        WHERE v.statut='livree'
        GROUP BY m.id ORDER BY nb DESC LIMIT 5
    """)

    ventes_mois = query("""
        SELECT strftime('%Y-%m', date_vente) mois,
               COUNT(*) nb,
               COALESCE(SUM(montant_ttc),0) ca
        FROM ventes
        WHERE statut='livree'
          AND date(date_vente) >= date('now','-6 months')
        GROUP BY mois ORDER BY mois
    """)

    locs_mois = query("""
        SELECT strftime('%Y-%m', date_debut) mois,
               COUNT(*) nb,
               COALESCE(SUM(montant_total),0) ca
        FROM locations
        WHERE date(date_debut) >= date('now','-6 months')
        GROUP BY mois ORDER BY mois
    """)

    alertes = query("""
        SELECT p.*, v.code AS veh_code, v.immatriculation, m.nom AS marque_nom
        FROM papiers p
        JOIN vehicules v ON v.id = p.vehicule_id
        LEFT JOIN marques m ON m.id = v.marque_id
        WHERE p.date_expiration IS NOT NULL
          AND date(p.date_expiration) <= date('now', '+60 days')
        ORDER BY p.date_expiration ASC LIMIT 10
    """)

    dernieres_ventes = query("""
        SELECT v.*, c.nom AS client_nom, c.prenom AS client_prenom,
               veh.code AS veh_code, veh.immatriculation
        FROM ventes v
        LEFT JOIN clients c ON c.id = v.client_id
        LEFT JOIN vehicules veh ON veh.id = v.vehicule_id
        ORDER BY v.id DESC LIMIT 8
    """)

    dernieres_locations = query("""
        SELECT l.*, c.nom AS client_nom, c.prenom AS client_prenom,
               veh.code AS veh_code, veh.immatriculation
        FROM locations l
        LEFT JOIN clients c ON c.id = l.client_id
        LEFT JOIN vehicules veh ON veh.id = l.vehicule_id
        ORDER BY l.id DESC LIMIT 8
    """)

    stock_agences = query("""
        SELECT a.nom, COUNT(v.id) nb,
               COALESCE(SUM(v.prix_vente),0) valeur
        FROM agences a
        LEFT JOIN vehicules v ON v.agence_id = a.id AND v.statut='disponible'
        GROUP BY a.id ORDER BY nb DESC
    """)

    return render_template('dashboard.html',
                           kpi=kpi,
                           top_marques=top_marques,
                           ventes_mois=ventes_mois,
                           locs_mois=locs_mois,
                           alertes=alertes,
                           dernieres_ventes=dernieres_ventes,
                           dernieres_locations=dernieres_locations,
                           stock_agences=stock_agences)

# ═══════════════════════════════════════════════════════════
# UPLOADS
# ═══════════════════════════════════════════════════════════
@app.route('/uploads/<path:subpath>/<filename>')
@login_required
def uploaded_file(subpath, filename):
    safe_sub = subpath if subpath in ('vehicules', 'papiers') else 'vehicules'
    directory = os.path.join(UPLOAD_DIR, safe_sub)
    return send_from_directory(directory, filename)

# ═══════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═══════════════════════════════════════════════════════════
@app.errorhandler(404)
def e404(e):
    return render_template('404.html'), 404

@app.errorhandler(413)
def e413(e):
    flash("Fichier trop volumineux (max 200 Mo).", "error")
    return redirect(request.referrer or url_for('dashboard'))

@app.errorhandler(500)
def e500(e):
    return render_template('500.html', error=str(e)), 500



# ═══════════════════════════════════════════════════════════
# BLOC 2 — AGENCES · MARQUES · MODELES · VEHICULES
# ═══════════════════════════════════════════════════════════

# ─── AGENCES ───
@app.route('/agences')
@login_required
def agences_list():
    q = request.args.get('q', '').strip()
    statut = request.args.get('statut', '').strip()
    sql = """SELECT a.*,
                    (SELECT COUNT(*) FROM vehicules v WHERE v.agence_id=a.id) nb_vehicules,
                    (SELECT COUNT(*) FROM vehicules v WHERE v.agence_id=a.id AND v.statut='disponible') nb_dispo
             FROM agences a WHERE 1=1"""
    params = []
    if q:
        sql += " AND (a.nom LIKE ? OR a.ville LIKE ? OR a.telephone LIKE ?)"
        params += [f'%{q}%'] * 3
    if statut:
        sql += " AND a.statut=?"
        params.append(statut)
    sql += " ORDER BY a.nom"
    agences = query(sql, params)
    return render_template('agences/list.html', agences=agences, q=q, statut=statut)

@app.route('/agences/nouveau', methods=['GET', 'POST'])
@login_required
@admin_required
def agence_new():
    if request.method == 'POST':
        f = request.form
        aid = execute("""
            INSERT INTO agences (code, nom, type, adresse, ville, region, pays, telephone,
                                  whatsapp, email, responsable, latitude, longitude,
                                  horaires, statut, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            f.get('code') or None, f.get('nom'), f.get('type'),
            f.get('adresse'), f.get('ville'), f.get('region'),
            f.get('pays') or 'Sénégal', f.get('telephone'), f.get('whatsapp'),
            f.get('email'), f.get('responsable'),
            float(f.get('latitude') or 0), float(f.get('longitude') or 0),
            f.get('horaires'), f.get('statut') or 'actif',
            datetime.now().isoformat()
        ))
        audit('create', 'agence', aid)
        flash("✅ Agence créée.", "success")
        return redirect(url_for('agences_list'))
    return render_template('agences/form.html', agence=None)

@app.route('/agences/<int:aid>/editer', methods=['GET', 'POST'])
@login_required
@admin_required
def agence_edit(aid):
    agence = query("SELECT * FROM agences WHERE id=?", (aid,), one=True)
    if not agence:
        abort(404)
    if request.method == 'POST':
        f = request.form
        execute("""
            UPDATE agences SET nom=?, type=?, adresse=?, ville=?, region=?, pays=?,
                telephone=?, whatsapp=?, email=?, responsable=?, latitude=?, longitude=?,
                horaires=?, statut=?
            WHERE id=?
        """, (f.get('nom'), f.get('type'), f.get('adresse'), f.get('ville'), f.get('region'),
              f.get('pays') or 'Sénégal', f.get('telephone'), f.get('whatsapp'),
              f.get('email'), f.get('responsable'),
              float(f.get('latitude') or 0), float(f.get('longitude') or 0),
              f.get('horaires'), f.get('statut') or 'actif', aid))
        audit('update', 'agence', aid)
        flash("✅ Agence mise à jour.", "success")
        return redirect(url_for('agences_list'))
    return render_template('agences/form.html', agence=agence)

@app.route('/agences/<int:aid>/supprimer', methods=['POST'])
@login_required
@admin_required
def agence_delete(aid):
    nb = query("SELECT COUNT(*) c FROM vehicules WHERE agence_id=?", (aid,), one=True)['c']
    if nb > 0:
        flash(f"❌ Impossible : {nb} véhicule(s) rattaché(s).", "error")
    else:
        execute("DELETE FROM agences WHERE id=?", (aid,))
        audit('delete', 'agence', aid)
        flash("🗑️ Agence supprimée.", "success")
    return redirect(url_for('agences_list'))

@app.route('/agences/<int:aid>')
@login_required
def agence_detail(aid):
    agence = query("SELECT * FROM agences WHERE id=?", (aid,), one=True)
    if not agence:
        abort(404)
    vehicules = query("""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom
        FROM vehicules v
        LEFT JOIN marques m ON m.id = v.marque_id
        LEFT JOIN modeles mo ON mo.id = v.modele_id
        WHERE v.agence_id=? ORDER BY v.id DESC LIMIT 50
    """, (aid,))
    kpi = {
        'total': query("SELECT COUNT(*) c FROM vehicules WHERE agence_id=?", (aid,), one=True)['c'],
        'dispo': query("SELECT COUNT(*) c FROM vehicules WHERE agence_id=? AND statut='disponible'", (aid,), one=True)['c'],
        'valeur': query("SELECT COALESCE(SUM(prix_vente),0) c FROM vehicules WHERE agence_id=? AND statut='disponible'", (aid,), one=True)['c'],
    }
    return render_template('agences/detail.html', agence=agence, vehicules=vehicules, kpi=kpi)

# ─── MARQUES ───
@app.route('/marques')
@login_required
def marques_list():
    marques = query("""
        SELECT m.*,
               (SELECT COUNT(*) FROM modeles mo WHERE mo.marque_id=m.id) nb_modeles,
               (SELECT COUNT(*) FROM vehicules v WHERE v.marque_id=m.id) nb_vehicules
        FROM marques m ORDER BY m.ordre, m.nom
    """)
    return render_template('marques/list.html', marques=marques)

@app.route('/marques/nouvelle', methods=['GET', 'POST'])
@login_required
def marque_new():
    if request.method == 'POST':
        f = request.form
        nom = f.get('nom', '').strip()
        slug = f.get('slug', '').strip() or nom.lower().replace(' ', '-')
        try:
            mid = execute("""
                INSERT INTO marques (nom, slug, pays_origine, logo_url, ordre, created_at)
                VALUES (?,?,?,?,?,?)
            """, (nom, slug, f.get('pays_origine'), f.get('logo_url'),
                  int(f.get('ordre') or 0), datetime.now().isoformat()))
            audit('create', 'marque', mid)
            flash("✅ Marque créée.", "success")
            return redirect(url_for('marques_list'))
        except sqlite3.IntegrityError:
            flash("❌ Cette marque existe déjà.", "error")
    return render_template('marques/form.html', marque=None)

@app.route('/marques/<int:mid>/editer', methods=['GET', 'POST'])
@login_required
def marque_edit(mid):
    marque = query("SELECT * FROM marques WHERE id=?", (mid,), one=True)
    if not marque:
        abort(404)
    if request.method == 'POST':
        f = request.form
        execute("""
            UPDATE marques SET nom=?, slug=?, pays_origine=?, logo_url=?, ordre=? WHERE id=?
        """, (f.get('nom'), f.get('slug'), f.get('pays_origine'),
              f.get('logo_url'), int(f.get('ordre') or 0), mid))
        audit('update', 'marque', mid)
        flash("✅ Marque mise à jour.", "success")
        return redirect(url_for('marques_list'))
    return render_template('marques/form.html', marque=marque)

@app.route('/marques/<int:mid>/supprimer', methods=['POST'])
@login_required
@admin_required
def marque_delete(mid):
    nb = query("SELECT COUNT(*) c FROM vehicules WHERE marque_id=?", (mid,), one=True)['c']
    if nb > 0:
        flash(f"❌ {nb} véhicule(s) utilisent cette marque.", "error")
    else:
        execute("DELETE FROM modeles WHERE marque_id=?", (mid,))
        execute("DELETE FROM marques WHERE id=?", (mid,))
        audit('delete', 'marque', mid)
        flash("🗑️ Marque supprimée.", "success")
    return redirect(url_for('marques_list'))

# ─── MODELES ───
@app.route('/modeles')
@login_required
def modeles_list():
    marque_id = request.args.get('marque_id', type=int)
    sql = """SELECT mo.*, m.nom AS marque_nom,
                    (SELECT COUNT(*) FROM vehicules v WHERE v.modele_id=mo.id) nb_vehicules
             FROM modeles mo LEFT JOIN marques m ON m.id=mo.marque_id WHERE 1=1"""
    params = []
    if marque_id:
        sql += " AND mo.marque_id=?"
        params.append(marque_id)
    sql += " ORDER BY m.nom, mo.nom"
    modeles = query(sql, params)
    marques = query("SELECT * FROM marques ORDER BY nom")
    return render_template('modeles/list.html', modeles=modeles, marques=marques, marque_id=marque_id)

@app.route('/modeles/nouveau', methods=['GET', 'POST'])
@login_required
def modele_new():
    if request.method == 'POST':
        f = request.form
        mid = execute("""
            INSERT INTO modeles (marque_id, nom, type, annee_debut, annee_fin,
                                   carburant, transmission, created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (int(f.get('marque_id')), f.get('nom'), f.get('type'),
              int(f.get('annee_debut') or 0), int(f.get('annee_fin') or 0),
              f.get('carburant'), f.get('transmission'), datetime.now().isoformat()))
        audit('create', 'modele', mid)
        flash("✅ Modèle créé.", "success")
        return redirect(url_for('modeles_list'))
    marques = query("SELECT * FROM marques ORDER BY nom")
    return render_template('modeles/form.html', modele=None, marques=marques)

@app.route('/modeles/<int:mid>/editer', methods=['GET', 'POST'])
@login_required
def modele_edit(mid):
    modele = query("SELECT * FROM modeles WHERE id=?", (mid,), one=True)
    if not modele:
        abort(404)
    if request.method == 'POST':
        f = request.form
        execute("""
            UPDATE modeles SET marque_id=?, nom=?, type=?, annee_debut=?, annee_fin=?,
                carburant=?, transmission=? WHERE id=?
        """, (int(f.get('marque_id')), f.get('nom'), f.get('type'),
              int(f.get('annee_debut') or 0), int(f.get('annee_fin') or 0),
              f.get('carburant'), f.get('transmission'), mid))
        audit('update', 'modele', mid)
        flash("✅ Modèle mis à jour.", "success")
        return redirect(url_for('modeles_list'))
    marques = query("SELECT * FROM marques ORDER BY nom")
    return render_template('modeles/form.html', modele=modele, marques=marques)

@app.route('/modeles/<int:mid>/supprimer', methods=['POST'])
@login_required
def modele_delete(mid):
    nb = query("SELECT COUNT(*) c FROM vehicules WHERE modele_id=?", (mid,), one=True)['c']
    if nb > 0:
        flash(f"❌ {nb} véhicule(s) utilisent ce modèle.", "error")
    else:
        execute("DELETE FROM modeles WHERE id=?", (mid,))
        audit('delete', 'modele', mid)
        flash("🗑️ Modèle supprimé.", "success")
    return redirect(url_for('modeles_list'))

# ─── API JSON ───
@app.route('/api/modeles/<int:marque_id>')
@login_required
def api_modeles(marque_id):
    rows = query("SELECT id, nom, type FROM modeles WHERE marque_id=? ORDER BY nom", (marque_id,))
    return jsonify([dict(r) for r in rows])

@app.route('/api/vehicules/disponibles')
@login_required
def api_vehicules_dispo():
    mode = request.args.get('mode', 'vente')
    field = 'disponible_vente' if mode == 'vente' else 'disponible_location'
    rows = query(f"""
        SELECT v.id, v.code, v.immatriculation, v.prix_vente, v.prix_location_jour,
               m.nom AS marque, mo.nom AS modele
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        WHERE v.statut='disponible' AND v.{field}=1
        ORDER BY m.nom, mo.nom
    """)
    return jsonify([dict(r) for r in rows])

# ─── VEHICULES ───
@app.route('/vehicules')
@login_required
def vehicules_list():
    q = request.args.get('q', '').strip()
    marque_id = request.args.get('marque_id', type=int)
    agence_id = request.args.get('agence_id', type=int)
    etat = request.args.get('etat', '').strip()
    statut = request.args.get('statut', '').strip()
    type_v = request.args.get('type', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 12

    where = " WHERE 1=1"
    params = []
    if q:
        where += " AND (v.code LIKE ? OR v.immatriculation LIKE ? OR v.description LIKE ? OR m.nom LIKE ?)"
        params += [f'%{q}%'] * 4
    if marque_id:
        where += " AND v.marque_id=?"; params.append(marque_id)
    if agence_id:
        where += " AND v.agence_id=?"; params.append(agence_id)
    if etat:
        where += " AND v.etat=?"; params.append(etat)
    if statut:
        where += " AND v.statut=?"; params.append(statut)
    if type_v:
        where += " AND v.type=?"; params.append(type_v)

    total = query(f"""
        SELECT COUNT(*) c FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id {where}
    """, params, one=True)['c']

    offset = (page - 1) * per_page
    vehicules = query(f"""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom, a.nom AS agence_nom
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        LEFT JOIN agences a ON a.id=v.agence_id
        {where}
        ORDER BY v.id DESC LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    pages = (total + per_page - 1) // per_page
    marques = query("SELECT * FROM marques ORDER BY nom")
    agences = query("SELECT * FROM agences ORDER BY nom")

    return render_template('vehicules/list.html',
                           vehicules=vehicules, marques=marques, agences=agences,
                           q=q, marque_id=marque_id, agence_id=agence_id,
                           etat=etat, statut=statut, type_v=type_v,
                           page=page, pages=pages, total=total)

@app.route('/vehicules/nouveau', methods=['GET', 'POST'])
@login_required
def vehicule_new():
    if request.method == 'POST':
        f = request.form
        prix_achat = float(f.get('prix_achat') or 0)
        prix_vente = float(f.get('prix_vente') or 0)
        prix_loc_jour = float(f.get('prix_location_jour') or 0)
        marge = prix_vente - prix_achat

        vid = execute("""
            INSERT INTO vehicules (code, agence_id, marque_id, modele_id, immatriculation,
                vin_chassis, type, etat, annee, kilometrage, carburant, transmission,
                couleur, nb_portes, nb_places, puissance_ch, cylindree_cm3,
                prix_achat, prix_vente, prix_location_jour, prix_location_semaine,
                prix_location_mois, marge_estimee,
                disponible_vente, disponible_location, description, equipements,
                statut, date_acquisition, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            f.get('code') or None,
            int(f.get('agence_id')) if f.get('agence_id') else None,
            int(f.get('marque_id')) if f.get('marque_id') else None,
            int(f.get('modele_id')) if f.get('modele_id') else None,
            f.get('immatriculation'),
            f.get('vin_chassis'), f.get('type'), f.get('etat') or 'occasion',
            int(f.get('annee') or 0), float(f.get('kilometrage') or 0),
            f.get('carburant'), f.get('transmission'), f.get('couleur'),
            int(f.get('nb_portes') or 4), int(f.get('nb_places') or 5),
            int(f.get('puissance_ch') or 0), int(f.get('cylindree_cm3') or 0),
            prix_achat, prix_vente,
            prix_loc_jour,
            float(f.get('prix_location_semaine') or 0),
            float(f.get('prix_location_mois') or 0),
            marge,
            1 if f.get('disponible_vente') else 0,
            1 if f.get('disponible_location') else 0,
            f.get('description'), f.get('equipements'),
            'disponible',
            f.get('date_acquisition') or datetime.now().strftime('%Y-%m-%d'),
            datetime.now().isoformat()
        ))

        photo = request.files.get('photo_principale')
        if photo and photo.filename:
            fname = save_upload(photo, VEHICULES_DIR, ALLOWED_IMG)
            if fname:
                execute("UPDATE vehicules SET photo_principale=? WHERE id=?", (fname, vid))
                execute("""
                    INSERT INTO vehicule_photos (vehicule_id, chemin, legende, categorie, ordre, created_at)
                    VALUES (?,?,?,?,?,?)
                """, (vid, fname, 'Photo principale', 'principale', 0, datetime.now().isoformat()))

        for idx, f_ in enumerate(request.files.getlist('galerie')):
            if f_ and f_.filename:
                fname = save_upload(f_, VEHICULES_DIR, ALLOWED_IMG)
                if fname:
                    execute("""
                        INSERT INTO vehicule_photos (vehicule_id, chemin, legende, categorie, ordre, created_at)
                        VALUES (?,?,?,?,?,?)
                    """, (vid, fname, f'Photo {idx+1}', 'galerie', idx + 1, datetime.now().isoformat()))

        video = request.files.get('video')
        if video and video.filename:
            fname = save_upload(video, VEHICULES_DIR, ALLOWED_VID)
            if fname:
                execute("""
                    INSERT INTO vehicule_videos (vehicule_id, chemin, titre, categorie, created_at)
                    VALUES (?,?,?,?,?)
                """, (vid, fname, 'Walkaround 360°', 'walkaround', datetime.now().isoformat()))

        audit('create', 'vehicule', vid)
        flash("✅ Véhicule créé avec succès.", "success")
        return redirect(url_for('vehicule_detail', vid=vid))

    marques = query("SELECT * FROM marques ORDER BY nom")
    agences = query("SELECT * FROM agences ORDER BY nom")
    return render_template('vehicules/form.html', vehicule=None, marques=marques, agences=agences)

@app.route('/vehicules/<int:vid>/editer', methods=['GET', 'POST'])
@login_required
def vehicule_edit(vid):
    vehicule = query("SELECT * FROM vehicules WHERE id=?", (vid,), one=True)
    if not vehicule:
        abort(404)
    if request.method == 'POST':
        f = request.form
        prix_achat = float(f.get('prix_achat') or 0)
        prix_vente = float(f.get('prix_vente') or 0)
        marge = prix_vente - prix_achat
        execute("""
            UPDATE vehicules SET agence_id=?, marque_id=?, modele_id=?, immatriculation=?,
                vin_chassis=?, type=?, etat=?, annee=?, kilometrage=?, carburant=?,
                transmission=?, couleur=?, nb_portes=?, nb_places=?, puissance_ch=?,
                cylindree_cm3=?, prix_achat=?, prix_vente=?, prix_location_jour=?,
                prix_location_semaine=?, prix_location_mois=?, marge_estimee=?,
                disponible_vente=?, disponible_location=?, description=?, equipements=?,
                statut=?, date_acquisition=?
            WHERE id=?
        """, (
            int(f.get('agence_id')) if f.get('agence_id') else None,
            int(f.get('marque_id')) if f.get('marque_id') else None,
            int(f.get('modele_id')) if f.get('modele_id') else None,
            f.get('immatriculation'), f.get('vin_chassis'), f.get('type'),
            f.get('etat') or 'occasion', int(f.get('annee') or 0),
            float(f.get('kilometrage') or 0), f.get('carburant'),
            f.get('transmission'), f.get('couleur'),
            int(f.get('nb_portes') or 4), int(f.get('nb_places') or 5),
            int(f.get('puissance_ch') or 0), int(f.get('cylindree_cm3') or 0),
            prix_achat, prix_vente,
            float(f.get('prix_location_jour') or 0),
            float(f.get('prix_location_semaine') or 0),
            float(f.get('prix_location_mois') or 0),
            marge,
            1 if f.get('disponible_vente') else 0,
            1 if f.get('disponible_location') else 0,
            f.get('description'), f.get('equipements'),
            f.get('statut') or 'disponible',
            f.get('date_acquisition'), vid
        ))

        photo = request.files.get('photo_principale')
        if photo and photo.filename:
            fname = save_upload(photo, VEHICULES_DIR, ALLOWED_IMG)
            if fname:
                execute("UPDATE vehicules SET photo_principale=? WHERE id=?", (fname, vid))

        for idx, f_ in enumerate(request.files.getlist('galerie')):
            if f_ and f_.filename:
                fname = save_upload(f_, VEHICULES_DIR, ALLOWED_IMG)
                if fname:
                    execute("""
                        INSERT INTO vehicule_photos (vehicule_id, chemin, legende, categorie, ordre, created_at)
                        VALUES (?,?,?,?,?,?)
                    """, (vid, fname, f'Ajout {idx+1}', 'galerie', 99 + idx, datetime.now().isoformat()))

        video = request.files.get('video')
        if video and video.filename:
            fname = save_upload(video, VEHICULES_DIR, ALLOWED_VID)
            if fname:
                execute("""
                    INSERT INTO vehicule_videos (vehicule_id, chemin, titre, categorie, created_at)
                    VALUES (?,?,?,?,?)
                """, (vid, fname, 'Walkaround', 'walkaround', datetime.now().isoformat()))

        audit('update', 'vehicule', vid)
        flash("✅ Véhicule mis à jour.", "success")
        return redirect(url_for('vehicule_detail', vid=vid))

    marques = query("SELECT * FROM marques ORDER BY nom")
    agences = query("SELECT * FROM agences ORDER BY nom")
    modeles = query("SELECT * FROM modeles WHERE marque_id=? ORDER BY nom", (vehicule['marque_id'],)) if vehicule['marque_id'] else []
    return render_template('vehicules/form.html', vehicule=vehicule, marques=marques,
                           agences=agences, modeles=modeles)

@app.route('/vehicules/<int:vid>')
@login_required
def vehicule_detail(vid):
    v = query("""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom,
               a.nom AS agence_nom, a.ville AS agence_ville, a.telephone AS agence_tel
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        LEFT JOIN agences a ON a.id=v.agence_id
        WHERE v.id=?
    """, (vid,), one=True)
    if not v:
        abort(404)

    photos = query("SELECT * FROM vehicule_photos WHERE vehicule_id=? ORDER BY ordre, id", (vid,))
    videos = query("SELECT * FROM vehicule_videos WHERE vehicule_id=? ORDER BY id DESC", (vid,))
    papiers = query("SELECT * FROM papiers WHERE vehicule_id=? ORDER BY date_expiration DESC", (vid,))
    entretiens = query("SELECT * FROM entretiens WHERE vehicule_id=? ORDER BY date_entretien DESC", (vid,))
    ventes = query("""
        SELECT v.*, c.nom AS client_nom, c.prenom AS client_prenom
        FROM ventes v LEFT JOIN clients c ON c.id=v.client_id
        WHERE v.vehicule_id=? ORDER BY v.id DESC
    """, (vid,))
    locations = query("""
        SELECT l.*, c.nom AS client_nom, c.prenom AS client_prenom
        FROM locations l LEFT JOIN clients c ON c.id=l.client_id
        WHERE l.vehicule_id=? ORDER BY l.id DESC
    """, (vid,))
    douane = query("SELECT * FROM douane WHERE vehicule_id=? ORDER BY id DESC", (vid,))

    qr_data = f"AUTO|VEH|{vid}|{v['immatriculation'] or v['code']}"
    return render_template('vehicules/detail.html', v=v, photos=photos, videos=videos,
                           papiers=papiers, entretiens=entretiens, ventes=ventes,
                           locations=locations, douane=douane, qr_data=qr_data)

@app.route('/vehicules/<int:vid>/supprimer', methods=['POST'])
@login_required
@admin_required
def vehicule_delete(vid):
    nb_v = query("SELECT COUNT(*) c FROM ventes WHERE vehicule_id=?", (vid,), one=True)['c']
    nb_l = query("SELECT COUNT(*) c FROM locations WHERE vehicule_id=?", (vid,), one=True)['c']
    if nb_v or nb_l:
        flash(f"❌ Impossible : {nb_v} vente(s), {nb_l} location(s) liées.", "error")
    else:
        execute("DELETE FROM vehicule_photos WHERE vehicule_id=?", (vid,))
        execute("DELETE FROM vehicule_videos WHERE vehicule_id=?", (vid,))
        execute("DELETE FROM papiers WHERE vehicule_id=?", (vid,))
        execute("DELETE FROM entretiens WHERE vehicule_id=?", (vid,))
        execute("DELETE FROM vehicules WHERE id=?", (vid,))
        audit('delete', 'vehicule', vid)
        flash("🗑️ Véhicule supprimé.", "success")
    return redirect(url_for('vehicules_list'))

@app.route('/vehicules/<int:vid>/photo/<int:pid>/supprimer', methods=['POST'])
@login_required
def vehicule_photo_delete(vid, pid):
    execute("DELETE FROM vehicule_photos WHERE id=? AND vehicule_id=?", (pid, vid))
    flash("🗑️ Photo supprimée.", "success")
    return redirect(url_for('vehicule_detail', vid=vid))

@app.route('/vehicules/<int:vid>/photo/<int:pid>/principale', methods=['POST'])
@login_required
def vehicule_photo_principale(vid, pid):
    p = query("SELECT chemin FROM vehicule_photos WHERE id=? AND vehicule_id=?", (pid, vid), one=True)
    if p:
        execute("UPDATE vehicules SET photo_principale=? WHERE id=?", (p['chemin'], vid))
        flash("⭐ Photo principale définie.", "success")
    return redirect(url_for('vehicule_detail', vid=vid))

@app.route('/vehicules/<int:vid>/qr')
@login_required
def vehicule_qr(vid):
    v = query("SELECT * FROM vehicules WHERE id=?", (vid,), one=True)
    if not v:
        abort(404)
    data = f"AUTO|VEH|{vid}|{v['immatriculation'] or v['code']}|{v['vin_chassis'] or ''}"
    img = qrcode.make(data)
    buf = BytesIO()
    img.save(buf, format='PNG')
    return Response(buf.getvalue(), mimetype='image/png')



# ═══════════════════════════════════════════════════════════
# BLOC 3 — CLIENTS · VENTES · LOCATIONS · PAIEMENTS
# ═══════════════════════════════════════════════════════════

# ─── HELPERS METIER ───
def calc_score_client(client_id):
    try:
        c = query("SELECT * FROM clients WHERE id=?", (client_id,), one=True)
        if not c:
            return 0
        score = 50
        score += min(30, (c['nb_achats'] or 0) * 10)
        score += min(15, (c['nb_locations'] or 0) * 3)
        depense = c['total_depense'] or 0
        if depense > 20_000_000:
            score += 15
        elif depense > 10_000_000:
            score += 10
        elif depense > 5_000_000:
            score += 5
        retards = query("""
            SELECT COUNT(*) c FROM paiements
            WHERE client_id=? AND statut='retard'
        """, (client_id,), one=True)['c']
        score -= retards * 8
        try:
            ancien = datetime.fromisoformat(c['created_at'])
            mois = max(0, (datetime.now() - ancien).days // 30)
            score += min(10, mois)
        except Exception:
            pass
        return max(0, min(100, int(score)))
    except Exception:
        return 50

def recalc_score(client_id):
    s = calc_score_client(client_id)
    execute("UPDATE clients SET score=? WHERE id=?", (s, client_id))
    return s

def prochain_numero_vente():
    today = datetime.now().strftime('%Y%m%d')
    row = query("""
        SELECT numero FROM ventes
        WHERE numero LIKE ?
        ORDER BY id DESC LIMIT 1
    """, (f'VTE-{today}-%',), one=True)
    if row and row['numero']:
        try:
            n = int(row['numero'].split('-')[-1]) + 1
        except Exception:
            n = 1
    else:
        n = 1
    return f"VTE-{today}-{n:04d}"

def prochain_numero_location():
    today = datetime.now().strftime('%Y%m%d')
    row = query("""
        SELECT numero FROM locations
        WHERE numero LIKE ?
        ORDER BY id DESC LIMIT 1
    """, (f'LOC-{today}-%',), one=True)
    if row and row['numero']:
        try:
            n = int(row['numero'].split('-')[-1]) + 1
        except Exception:
            n = 1
    else:
        n = 1
    return f"LOC-{today}-{n:04d}"

def check_dispo_vente(vehicule_id):
    v = query("SELECT * FROM vehicules WHERE id=?", (vehicule_id,), one=True)
    if not v:
        return False, "Véhicule introuvable"
    if v['statut'] == 'vendu':
        return False, "Véhicule déjà vendu"
    if not v['disponible_vente']:
        return False, "Véhicule non disponible à la vente"
    return True, ""

def check_dispo_location(vehicule_id, date_debut, date_fin, exclude_loc_id=None):
    v = query("SELECT * FROM vehicules WHERE id=?", (vehicule_id,), one=True)
    if not v:
        return False, "Véhicule introuvable"
    if not v['disponible_location']:
        return False, "Véhicule non disponible à la location"
    if v['statut'] == 'vendu':
        return False, "Véhicule vendu"
    sql = """
        SELECT COUNT(*) c FROM locations
        WHERE vehicule_id=?
          AND statut IN ('reservee','en_cours')
          AND date(date_debut) <= date(?)
          AND date(date_fin_prevue) >= date(?)
    """
    params = [vehicule_id, date_fin, date_debut]
    if exclude_loc_id:
        sql += " AND id != ?"
        params.append(exclude_loc_id)
    overlap = query(sql, params, one=True)['c']
    if overlap:
        return False, f"Véhicule déjà réservé sur cette période ({overlap} location(s))"
    return True, ""

def calcul_prix_location(vehicule_id, date_debut, date_fin):
    v = query("SELECT * FROM vehicules WHERE id=?", (vehicule_id,), one=True)
    if not v:
        return 0, 0, 0
    try:
        d1 = datetime.fromisoformat(date_debut).date()
        d2 = datetime.fromisoformat(date_fin).date()
        jours = max(1, (d2 - d1).days)
    except Exception:
        jours = 1
    tarif_jour = v['prix_location_jour'] or 0
    tarif_semaine = v['prix_location_semaine'] or 0
    tarif_mois = v['prix_location_mois'] or 0
    if jours >= 30 and tarif_mois > 0:
        mois = jours // 30
        reste = jours % 30
        montant = mois * tarif_mois + reste * tarif_jour
    elif jours >= 7 and tarif_semaine > 0:
        semaines = jours // 7
        reste = jours % 7
        montant = semaines * tarif_semaine + reste * tarif_jour
    else:
        montant = jours * tarif_jour
    return jours, tarif_jour, montant

# ─── CLIENTS ───
@app.route('/clients')
@login_required
def clients_list():
    q = request.args.get('q', '').strip()
    type_c = request.args.get('type', '').strip()
    ville = request.args.get('ville', '').strip()
    statut = request.args.get('statut', '').strip()
    tri = request.args.get('tri', 'recent')
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 20

    where = " WHERE 1=1"
    params = []
    if q:
        where += """ AND (nom LIKE ? OR prenom LIKE ? OR telephone LIKE ?
                          OR code LIKE ? OR email LIKE ?)"""
        params += [f'%{q}%'] * 5
    if type_c:
        where += " AND type=?"; params.append(type_c)
    if ville:
        where += " AND ville=?"; params.append(ville)
    if statut:
        where += " AND statut=?"; params.append(statut)

    order = {
        'recent': 'id DESC',
        'nom': 'nom ASC, prenom ASC',
        'score': 'score DESC',
        'depense': 'total_depense DESC',
        'achats': 'nb_achats DESC',
        'locations': 'nb_locations DESC',
    }.get(tri, 'id DESC')

    total = query(f"SELECT COUNT(*) c FROM clients {where}", params, one=True)['c']
    offset = (page - 1) * per_page
    clients = query(f"""
        SELECT * FROM clients {where}
        ORDER BY {order} LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    villes = [r['ville'] for r in query("""
        SELECT DISTINCT ville FROM clients WHERE ville IS NOT NULL AND ville != ''
        ORDER BY ville
    """)]

    pages = (total + per_page - 1) // per_page
    return render_template('clients/list.html',
                           clients=clients, villes=villes,
                           q=q, type_c=type_c, ville=ville, statut=statut, tri=tri,
                           page=page, pages=pages, total=total)

@app.route('/clients/nouveau', methods=['GET', 'POST'])
@login_required
def client_new():
    if request.method == 'POST':
        f = request.form
        try:
            cid = execute("""
                INSERT INTO clients (code, nom, prenom, type, telephone, whatsapp, email,
                    adresse, ville, pays, piece_identite, permis_conduire,
                    score, nb_achats, nb_locations, total_depense, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,0,0,0,'actif',?)
            """, (
                None, f.get('nom'), f.get('prenom'), f.get('type') or 'particulier',
                f.get('telephone'), f.get('whatsapp') or f.get('telephone'),
                f.get('email'), f.get('adresse'), f.get('ville'),
                f.get('pays') or 'Sénégal', f.get('piece_identite'),
                f.get('permis_conduire'), datetime.now().isoformat()
            ))
            recalc_score(cid)
            audit('create', 'client', cid)
            flash("✅ Client créé.", "success")
            return redirect(url_for('client_detail', cid=cid))
        except sqlite3.IntegrityError:
            flash("❌ Téléphone déjà utilisé.", "error")
    return render_template('clients/form.html', client=None)

@app.route('/clients/<int:cid>/editer', methods=['GET', 'POST'])
@login_required
def client_edit(cid):
    client = query("SELECT * FROM clients WHERE id=?", (cid,), one=True)
    if not client:
        abort(404)
    if request.method == 'POST':
        f = request.form
        try:
            execute("""
                UPDATE clients SET nom=?, prenom=?, type=?, telephone=?, whatsapp=?,
                    email=?, adresse=?, ville=?, pays=?, piece_identite=?,
                    permis_conduire=?, statut=?
                WHERE id=?
            """, (
                f.get('nom'), f.get('prenom'), f.get('type') or 'particulier',
                f.get('telephone'), f.get('whatsapp'), f.get('email'),
                f.get('adresse'), f.get('ville'), f.get('pays') or 'Sénégal',
                f.get('piece_identite'), f.get('permis_conduire'),
                f.get('statut') or 'actif', cid
            ))
            recalc_score(cid)
            audit('update', 'client', cid)
            flash("✅ Client mis à jour.", "success")
            return redirect(url_for('client_detail', cid=cid))
        except sqlite3.IntegrityError:
            flash("❌ Téléphone déjà utilisé par un autre client.", "error")
    return render_template('clients/form.html', client=client)

@app.route('/clients/<int:cid>')
@login_required
def client_detail(cid):
    client = query("SELECT * FROM clients WHERE id=?", (cid,), one=True)
    if not client:
        abort(404)

    ventes = query("""
        SELECT v.*, veh.code AS veh_code, veh.immatriculation,
               m.nom AS marque_nom, mo.nom AS modele_nom
        FROM ventes v
        LEFT JOIN vehicules veh ON veh.id=v.vehicule_id
        LEFT JOIN marques m ON m.id=veh.marque_id
        LEFT JOIN modeles mo ON mo.id=veh.modele_id
        WHERE v.client_id=? ORDER BY v.id DESC
    """, (cid,))

    locations = query("""
        SELECT l.*, veh.code AS veh_code, veh.immatriculation,
               m.nom AS marque_nom, mo.nom AS modele_nom
        FROM locations l
        LEFT JOIN vehicules veh ON veh.id=l.vehicule_id
        LEFT JOIN marques m ON m.id=veh.marque_id
        LEFT JOIN modeles mo ON mo.id=veh.modele_id
        WHERE l.client_id=? ORDER BY l.id DESC
    """, (cid,))

    paiements = query("""
        SELECT * FROM paiements WHERE client_id=? ORDER BY id DESC
    """, (cid,))

    kpi = {
        'ca_total': sum((v['montant_ttc'] or 0) for v in ventes if v['statut'] == 'livree')
                    + sum((l['montant_total'] or 0) for l in locations if l['statut'] in ('terminee', 'en_cours')),
        'impayes': sum((v['reste_a_payer'] or 0) for v in ventes if v['statut'] != 'annulee'),
        'nb_ventes': len(ventes),
        'nb_locations': len(locations),
        'score': client['score'] or 0,
    }

    return render_template('clients/detail.html', client=client,
                           ventes=ventes, locations=locations,
                           paiements=paiements, kpi=kpi)

@app.route('/clients/<int:cid>/supprimer', methods=['POST'])
@login_required
@admin_required
def client_delete(cid):
    nb_v = query("SELECT COUNT(*) c FROM ventes WHERE client_id=?", (cid,), one=True)['c']
    nb_l = query("SELECT COUNT(*) c FROM locations WHERE client_id=?", (cid,), one=True)['c']
    if nb_v or nb_l:
        flash(f"❌ Impossible : {nb_v} vente(s), {nb_l} location(s).", "error")
    else:
        execute("DELETE FROM clients WHERE id=?", (cid,))
        audit('delete', 'client', cid)
        flash("🗑️ Client supprimé.", "success")
    return redirect(url_for('clients_list'))

@app.route('/clients/<int:cid>/recalculer-score', methods=['POST'])
@login_required
def client_recalc(cid):
    s = recalc_score(cid)
    flash(f"🔄 Score recalculé : {s}/100", "success")
    return redirect(url_for('client_detail', cid=cid))

@app.route('/api/clients/recherche')
@login_required
def api_clients_search():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    rows = query("""
        SELECT id, code, nom, prenom, telephone, score
        FROM clients
        WHERE nom LIKE ? OR prenom LIKE ? OR telephone LIKE ? OR code LIKE ?
        ORDER BY nom LIMIT 15
    """, (f'%{q}%',) * 4)
    return jsonify([dict(r) for r in rows])

# ─── VENTES ───
@app.route('/ventes')
@login_required
def ventes_list():
    q = request.args.get('q', '').strip()
    statut = request.args.get('statut', '').strip()
    mode = request.args.get('mode', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 20

    where = " WHERE 1=1"
    params = []
    if q:
        where += """ AND (v.numero LIKE ? OR c.nom LIKE ? OR c.prenom LIKE ?
                          OR veh.code LIKE ? OR veh.immatriculation LIKE ?)"""
        params += [f'%{q}%'] * 5
    if statut:
        where += " AND v.statut=?"; params.append(statut)
    if mode:
        where += " AND v.mode_paiement=?"; params.append(mode)

    total = query(f"""
        SELECT COUNT(*) c FROM ventes v
        LEFT JOIN clients c ON c.id=v.client_id
        LEFT JOIN vehicules veh ON veh.id=v.vehicule_id
        {where}
    """, params, one=True)['c']

    offset = (page - 1) * per_page
    ventes = query(f"""
        SELECT v.*, c.nom AS client_nom, c.prenom AS client_prenom, c.telephone AS client_tel,
               veh.code AS veh_code, veh.immatriculation, veh.photo_principale,
               m.nom AS marque_nom, mo.nom AS modele_nom,
               u.nom_complet AS vendeur_nom
        FROM ventes v
        LEFT JOIN clients c ON c.id=v.client_id
        LEFT JOIN vehicules veh ON veh.id=v.vehicule_id
        LEFT JOIN marques m ON m.id=veh.marque_id
        LEFT JOIN modeles mo ON mo.id=veh.modele_id
        LEFT JOIN users u ON u.id=v.vendeur_id
        {where}
        ORDER BY v.id DESC LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    kpi = {
        'total': total,
        'livrees': query("SELECT COUNT(*) c FROM ventes WHERE statut='livree'", one=True)['c'],
        'en_cours': query("SELECT COUNT(*) c FROM ventes WHERE statut IN ('devis','acompte')", one=True)['c'],
        'ca': query("SELECT COALESCE(SUM(montant_ttc),0) c FROM ventes WHERE statut='livree'", one=True)['c'],
        'impayes': query("SELECT COALESCE(SUM(reste_a_payer),0) c FROM ventes WHERE statut NOT IN ('livree','annulee')", one=True)['c'],
    }

    pages = (total + per_page - 1) // per_page
    return render_template('ventes/list.html', ventes=ventes, kpi=kpi,
                           q=q, statut=statut, mode=mode,
                           page=page, pages=pages)

@app.route('/ventes/nouvelle', methods=['GET', 'POST'])
@login_required
def vente_new():
    if request.method == 'POST':
        f = request.form
        vehicule_id = int(f.get('vehicule_id') or 0)
        client_id = int(f.get('client_id') or 0)

        ok, msg = check_dispo_vente(vehicule_id)
        if not ok:
            flash(f"❌ {msg}", "error")
            return redirect(request.url)

        v = query("SELECT * FROM vehicules WHERE id=?", (vehicule_id,), one=True)
        prix_vente = float(f.get('prix_vente') or v['prix_vente'] or 0)
        prix_achat = v['prix_achat'] or 0
        remise = float(f.get('remise') or 0)
        montant_ttc = prix_vente - remise
        acompte = float(f.get('acompte') or 0)
        reste = max(0, montant_ttc - acompte)
        marge = prix_vente - prix_achat - remise

        mode_paiement = f.get('mode_paiement') or 'especes'
        type_vente = f.get('type_vente') or 'comptant'

        statut = 'devis'
        if type_vente == 'comptant' and acompte >= montant_ttc:
            statut = 'livree'
        elif acompte > 0:
            statut = 'acompte'

        numero = prochain_numero_vente()
        vid = execute("""
            INSERT INTO ventes (numero, vehicule_id, client_id, vendeur_id, agence_id,
                date_vente, prix_vente, prix_achat, marge, remise, montant_ttc,
                acompte, reste_a_payer, mode_paiement, type_vente,
                duree_credit_mois, statut, notes, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            numero, vehicule_id, client_id, current_user.id,
            v['agence_id'],
            f.get('date_vente') or datetime.now().strftime('%Y-%m-%d'),
            prix_vente, prix_achat, marge, remise, montant_ttc,
            acompte, reste, mode_paiement, type_vente,
            int(f.get('duree_credit_mois') or 0),
            statut, f.get('notes'),
            datetime.now().isoformat()
        ))

        if acompte > 0:
            execute("""
                INSERT INTO paiements (type, reference_id, client_id, montant, mode,
                    operateur, telephone, statut, date_paiement, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, ('vente', vid, client_id, acompte, mode_paiement,
                  f.get('operateur'), f.get('telephone_paiement'),
                  'valide', datetime.now().strftime('%Y-%m-%d'),
                  datetime.now().isoformat()))

        if statut == 'livree':
            execute("UPDATE vehicules SET statut='vendu' WHERE id=?", (vehicule_id,))
            recalc_score(client_id)

        audit('create', 'vente', vid, numero)
        flash(f"✅ Vente {numero} enregistrée ({statut}).", "success")
        return redirect(url_for('vente_detail', vente_id=vid))

    vehicules = query("""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        WHERE v.statut='disponible' AND v.disponible_vente=1
        ORDER BY m.nom, mo.nom
    """)
    clients = query("SELECT * FROM clients WHERE statut='actif' ORDER BY nom LIMIT 200")
    return render_template('ventes/form.html', vente=None,
                           vehicules=vehicules, clients=clients)

@app.route('/ventes/<int:vente_id>')
@login_required
def vente_detail(vente_id):
    vente = query("""
        SELECT v.*, c.nom AS client_nom, c.prenom AS client_prenom,
               c.telephone AS client_tel, c.email AS client_email,
               c.adresse AS client_adresse, c.code AS client_code, c.score AS client_score,
               veh.code AS veh_code, veh.immatriculation, veh.photo_principale,
               veh.annee, veh.kilometrage, veh.vin_chassis,
               m.nom AS marque_nom, mo.nom AS modele_nom,
               a.nom AS agence_nom, a.adresse AS agence_adresse, a.telephone AS agence_tel,
               u.nom_complet AS vendeur_nom, u.email AS vendeur_email
        FROM ventes v
        LEFT JOIN clients c ON c.id=v.client_id
        LEFT JOIN vehicules veh ON veh.id=v.vehicule_id
        LEFT JOIN marques m ON m.id=veh.marque_id
        LEFT JOIN modeles mo ON mo.id=veh.modele_id
        LEFT JOIN agences a ON a.id=v.agence_id
        LEFT JOIN users u ON u.id=v.vendeur_id
        WHERE v.id=?
    """, (vente_id,), one=True)
    if not vente:
        abort(404)

    paiements = query("""
        SELECT * FROM paiements WHERE type='vente' AND reference_id=?
        ORDER BY id DESC
    """, (vente_id,))

    return render_template('ventes/detail.html', vente=vente, paiements=paiements)

@app.route('/ventes/<int:vente_id>/statut', methods=['POST'])
@login_required
def vente_statut(vente_id):
    new_statut = request.form.get('statut', '').strip()
    allowed = ('devis', 'acompte', 'livree', 'annulee')
    if new_statut not in allowed:
        flash("❌ Statut invalide.", "error")
        return redirect(url_for('vente_detail', vente_id=vente_id))

    vente = query("SELECT * FROM ventes WHERE id=?", (vente_id,), one=True)
    if not vente:
        abort(404)

    execute("UPDATE ventes SET statut=? WHERE id=?", (new_statut, vente_id))

    if new_statut == 'livree':
        execute("UPDATE vehicules SET statut='vendu' WHERE id=?", (vente['vehicule_id'],))
        recalc_score(vente['client_id'])
    elif new_statut == 'annulee':
        execute("""UPDATE vehicules SET statut='disponible' WHERE id=? AND statut!='vendu'""",
                (vente['vehicule_id'],))

    audit('status', 'vente', vente_id, new_statut)
    flash(f"✅ Vente passée à « {new_statut} ».", "success")
    return redirect(url_for('vente_detail', vente_id=vente_id))

@app.route('/ventes/<int:vente_id>/paiement', methods=['POST'])
@login_required
def vente_paiement(vente_id):
    vente = query("SELECT * FROM ventes WHERE id=?", (vente_id,), one=True)
    if not vente:
        abort(404)
    f = request.form
    montant = float(f.get('montant') or 0)
    if montant <= 0:
        flash("❌ Montant invalide.", "error")
        return redirect(url_for('vente_detail', vente_id=vente_id))

    execute("""
        INSERT INTO paiements (type, reference_id, client_id, montant, mode,
            operateur, telephone, reference_transaction, statut, date_paiement, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, ('vente', vente_id, vente['client_id'], montant,
          f.get('mode') or 'especes', f.get('operateur'), f.get('telephone'),
          f.get('reference_transaction'), 'valide',
          f.get('date_paiement') or datetime.now().strftime('%Y-%m-%d'),
          datetime.now().isoformat()))

    new_acompte = (vente['acompte'] or 0) + montant
    new_reste = max(0, (vente['montant_ttc'] or 0) - new_acompte)

    new_statut = vente['statut']
    if new_reste <= 0 and vente['statut'] in ('devis', 'acompte'):
        new_statut = 'livree'

    execute("UPDATE ventes SET acompte=?, reste_a_payer=?, statut=? WHERE id=?",
            (new_acompte, new_reste, new_statut, vente_id))

    if new_statut == 'livree':
        execute("UPDATE vehicules SET statut='vendu' WHERE id=?", (vente['vehicule_id'],))
        recalc_score(vente['client_id'])

    audit('payment', 'vente', vente_id, f'{montant}')
    flash(f"💰 Paiement {fmt_money(montant)} enregistré.", "success")
    return redirect(url_for('vente_detail', vente_id=vente_id))

@app.route('/ventes/<int:vente_id>/supprimer', methods=['POST'])
@login_required
@admin_required
def vente_delete(vente_id):
    vente = query("SELECT * FROM ventes WHERE id=?", (vente_id,), one=True)
    if not vente:
        abort(404)
    execute("DELETE FROM paiements WHERE type='vente' AND reference_id=?", (vente_id,))
    execute("DELETE FROM ventes WHERE id=?", (vente_id,))
    if vente['statut'] == 'livree':
        execute("""UPDATE vehicules SET statut='disponible' WHERE id=? AND statut='vendu'""",
                (vente['vehicule_id'],))
    audit('delete', 'vente', vente_id)
    flash("🗑️ Vente supprimée.", "success")
    return redirect(url_for('ventes_list'))

@app.route('/ventes/<int:vente_id>/contrat')
@login_required
def vente_contrat(vente_id):
    vente = query("""
        SELECT v.*, c.nom AS client_nom, c.prenom AS client_prenom,
               c.telephone AS client_tel, c.adresse AS client_adresse,
               c.piece_identite, c.code AS client_code,
               veh.code AS veh_code, veh.immatriculation, veh.vin_chassis,
               veh.annee, veh.kilometrage, veh.couleur,
               m.nom AS marque_nom, mo.nom AS modele_nom,
               a.nom AS agence_nom, a.adresse AS agence_adresse, a.telephone AS agence_tel,
               u.nom_complet AS vendeur_nom
        FROM ventes v
        LEFT JOIN clients c ON c.id=v.client_id
        LEFT JOIN vehicules veh ON veh.id=v.vehicule_id
        LEFT JOIN marques m ON m.id=veh.marque_id
        LEFT JOIN modeles mo ON mo.id=veh.modele_id
        LEFT JOIN agences a ON a.id=v.agence_id
        LEFT JOIN users u ON u.id=v.vendeur_id
        WHERE v.id=?
    """, (vente_id,), one=True)
    if not vente:
        abort(404)
    return render_template('ventes/contrat.html', vente=vente)

# ─── LOCATIONS ───
@app.route('/locations')
@login_required
def locations_list():
    q = request.args.get('q', '').strip()
    statut = request.args.get('statut', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 20

    where = " WHERE 1=1"
    params = []
    if q:
        where += """ AND (l.numero LIKE ? OR c.nom LIKE ? OR c.prenom LIKE ?
                          OR veh.code LIKE ? OR veh.immatriculation LIKE ?)"""
        params += [f'%{q}%'] * 5
    if statut:
        where += " AND l.statut=?"; params.append(statut)

    total = query(f"""
        SELECT COUNT(*) c FROM locations l
        LEFT JOIN clients c ON c.id=l.client_id
        LEFT JOIN vehicules veh ON veh.id=l.vehicule_id
        {where}
    """, params, one=True)['c']

    offset = (page - 1) * per_page
    locations = query(f"""
        SELECT l.*, c.nom AS client_nom, c.prenom AS client_prenom, c.telephone AS client_tel,
               veh.code AS veh_code, veh.immatriculation, veh.photo_principale,
               m.nom AS marque_nom, mo.nom AS modele_nom
        FROM locations l
        LEFT JOIN clients c ON c.id=l.client_id
        LEFT JOIN vehicules veh ON veh.id=l.vehicule_id
        LEFT JOIN marques m ON m.id=veh.marque_id
        LEFT JOIN modeles mo ON mo.id=veh.modele_id
        {where}
        ORDER BY l.id DESC LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    kpi = {
        'total': total,
        'en_cours': query("SELECT COUNT(*) c FROM locations WHERE statut='en_cours'", one=True)['c'],
        'reservees': query("SELECT COUNT(*) c FROM locations WHERE statut='reservee'", one=True)['c'],
        'terminees': query("SELECT COUNT(*) c FROM locations WHERE statut='terminee'", one=True)['c'],
        'ca': query("SELECT COALESCE(SUM(montant_total),0) c FROM locations WHERE statut IN ('terminee','en_cours')", one=True)['c'],
    }

    pages = (total + per_page - 1) // per_page
    return render_template('locations/list.html', locations=locations, kpi=kpi,
                           q=q, statut=statut, page=page, pages=pages)

@app.route('/locations/nouvelle', methods=['GET', 'POST'])
@login_required
def location_new():
    if request.method == 'POST':
        f = request.form
        vehicule_id = int(f.get('vehicule_id') or 0)
        client_id = int(f.get('client_id') or 0)
        date_debut = f.get('date_debut')
        date_fin = f.get('date_fin_prevue')

        if not (vehicule_id and client_id and date_debut and date_fin):
            flash("❌ Champs obligatoires manquants.", "error")
            return redirect(request.url)

        ok, msg = check_dispo_location(vehicule_id, date_debut, date_fin)
        if not ok:
            flash(f"❌ {msg}", "error")
            return redirect(request.url)

        jours, tarif_j, montant_ht = calcul_prix_location(vehicule_id, date_debut, date_fin)
        caution = float(f.get('caution') or 0)
        frais_sup = float(f.get('frais_supplementaires') or 0)
        montant_total = montant_ht + frais_sup

        v = query("SELECT * FROM vehicules WHERE id=?", (vehicule_id,), one=True)
        numero = prochain_numero_location()

        lid = execute("""
            INSERT INTO locations (numero, vehicule_id, client_id, agence_id,
                date_debut, date_fin_prevue, duree_jours, km_depart,
                tarif_journalier, montant_ht, caution, frais_supplementaires,
                montant_total, statut, carburant_depart, etat_depart, notes, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            numero, vehicule_id, client_id, v['agence_id'],
            date_debut, date_fin, jours, float(f.get('km_depart') or v['kilometrage'] or 0),
            tarif_j, montant_ht, caution, frais_sup,
            montant_total, 'reservee',
            f.get('carburant_depart') or 'plein',
            f.get('etat_depart'), f.get('notes'),
            datetime.now().isoformat()
        ))

        if caution > 0:
            execute("""
                INSERT INTO paiements (type, reference_id, client_id, montant, mode,
                    statut, date_paiement, created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, ('location_caution', lid, client_id, caution,
                  f.get('mode_paiement') or 'especes', 'valide',
                  datetime.now().strftime('%Y-%m-%d'), datetime.now().isoformat()))

        audit('create', 'location', lid, numero)
        flash(f"✅ Location {numero} créée ({jours} jour(s)).", "success")
        return redirect(url_for('location_detail', loc_id=lid))

    vehicules = query("""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        WHERE v.statut='disponible' AND v.disponible_location=1
        ORDER BY m.nom, mo.nom
    """)
    clients = query("SELECT * FROM clients WHERE statut='actif' ORDER BY nom LIMIT 200")
    return render_template('locations/form.html', location=None,
                           vehicules=vehicules, clients=clients)

@app.route('/locations/<int:loc_id>')
@login_required
def location_detail(loc_id):
    loc = query("""
        SELECT l.*, c.nom AS client_nom, c.prenom AS client_prenom,
               c.telephone AS client_tel, c.email AS client_email,
               c.adresse AS client_adresse, c.code AS client_code,
               c.piece_identite, c.permis_conduire, c.score AS client_score,
               veh.code AS veh_code, veh.immatriculation, veh.photo_principale,
               veh.annee, veh.kilometrage AS veh_km, veh.vin_chassis, veh.couleur,
               m.nom AS marque_nom, mo.nom AS modele_nom,
               a.nom AS agence_nom, a.adresse AS agence_adresse, a.telephone AS agence_tel
        FROM locations l
        LEFT JOIN clients c ON c.id=l.client_id
        LEFT JOIN vehicules veh ON veh.id=l.vehicule_id
        LEFT JOIN marques m ON m.id=veh.marque_id
        LEFT JOIN modeles mo ON mo.id=veh.modele_id
        LEFT JOIN agences a ON a.id=l.agence_id
        WHERE l.id=?
    """, (loc_id,), one=True)
    if not loc:
        abort(404)

    paiements = query("""
        SELECT * FROM paiements
        WHERE (type='location' OR type='location_caution') AND reference_id=?
        ORDER BY id DESC
    """, (loc_id,))

    jours_restants = 0
    if loc['statut'] in ('reservee', 'en_cours') and loc['date_fin_prevue']:
        try:
            fin = datetime.fromisoformat(loc['date_fin_prevue']).date()
            jours_restants = (fin - datetime.now().date()).days
        except Exception:
            pass

    return render_template('locations/detail.html', loc=loc,
                           paiements=paiements, jours_restants=jours_restants)

@app.route('/locations/<int:loc_id>/demarrer', methods=['POST'])
@login_required
def location_demarrer(loc_id):
    loc = query("SELECT * FROM locations WHERE id=?", (loc_id,), one=True)
    if not loc:
        abort(404)
    if loc['statut'] != 'reservee':
        flash("❌ Seule une location réservée peut être démarrée.", "error")
        return redirect(url_for('location_detail', loc_id=loc_id))

    f = request.form
    execute("""
        UPDATE locations SET statut='en_cours', km_depart=?,
            carburant_depart=?, etat_depart=?
        WHERE id=?
    """, (float(f.get('km_depart') or loc['km_depart'] or 0),
          f.get('carburant_depart') or loc['carburant_depart'] or 'plein',
          f.get('etat_depart') or loc['etat_depart'],
          loc_id))

    execute("UPDATE vehicules SET statut='en_location' WHERE id=?", (loc['vehicule_id'],))
    audit('start', 'location', loc_id)
    flash("🚙 Location démarrée — véhicule sorti.", "success")
    return redirect(url_for('location_detail', loc_id=loc_id))

@app.route('/locations/<int:loc_id>/retour', methods=['POST'])
@login_required
def location_retour(loc_id):
    loc = query("SELECT * FROM locations WHERE id=?", (loc_id,), one=True)
    if not loc:
        abort(404)
    if loc['statut'] not in ('en_cours', 'reservee'):
        flash("❌ Location déjà terminée ou annulée.", "error")
        return redirect(url_for('location_detail', loc_id=loc_id))

    f = request.form
    km_retour = float(f.get('km_retour') or 0)
    km_depart = loc['km_depart'] or 0
    km_parcourus = max(0, km_retour - km_depart)

    jours = loc['duree_jours'] or 1
    km_inclus = jours * 250
    frais_km = 0
    if km_parcourus > km_inclus:
        km_sup = km_parcourus - km_inclus
        frais_km = km_sup * 100

    frais_divers = float(f.get('frais_divers') or 0)
    frais_sup_total = (loc['frais_supplementaires'] or 0) + frais_km + frais_divers
    montant_total = (loc['montant_ht'] or 0) + frais_sup_total

    execute("""
        UPDATE locations SET statut='terminee', date_retour_reelle=?,
            km_retour=?, km_parcourus=?, carburant_retour=?, etat_retour=?,
            frais_supplementaires=?, montant_total=?
        WHERE id=?
    """, (
        f.get('date_retour_reelle') or datetime.now().strftime('%Y-%m-%d'),
        km_retour, km_parcourus,
        f.get('carburant_retour') or 'plein',
        f.get('etat_retour'),
        frais_sup_total, montant_total, loc_id
    ))

    montant_paye = float(f.get('montant_paye') or 0)
    if montant_paye > 0:
        execute("""
            INSERT INTO paiements (type, reference_id, client_id, montant, mode,
                statut, date_paiement, created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, ('location', loc_id, loc['client_id'], montant_paye,
              f.get('mode_paiement') or 'especes', 'valide',
              datetime.now().strftime('%Y-%m-%d'), datetime.now().isoformat()))

    caution = loc['caution'] or 0
    if caution > 0 and frais_sup_total == 0:
        execute("""
            INSERT INTO paiements (type, reference_id, client_id, montant, mode,
                statut, date_paiement, created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, ('location_remboursement', loc_id, loc['client_id'], -caution,
              'especes', 'valide',
              datetime.now().strftime('%Y-%m-%d'), datetime.now().isoformat()))

    execute("""UPDATE vehicules SET statut='disponible',
               kilometrage = COALESCE(?, kilometrage) WHERE id=?""",
            (km_retour, loc['vehicule_id']))
    recalc_score(loc['client_id'])

    audit('return', 'location', loc_id, f'km={km_parcourus}')
    flash(f"✅ Retour enregistré — {km_parcourus} km parcourus.", "success")
    return redirect(url_for('location_detail', loc_id=loc_id))

@app.route('/locations/<int:loc_id>/annuler', methods=['POST'])
@login_required
def location_annuler(loc_id):
    loc = query("SELECT * FROM locations WHERE id=?", (loc_id,), one=True)
    if not loc:
        abort(404)
    execute("UPDATE locations SET statut='annulee' WHERE id=?", (loc_id,))
    execute("""UPDATE vehicules SET statut='disponible' WHERE id=? AND statut!='vendu'""",
            (loc['vehicule_id'],))
    audit('cancel', 'location', loc_id)
    flash("🚫 Location annulée.", "success")
    return redirect(url_for('location_detail', loc_id=loc_id))

@app.route('/locations/<int:loc_id>/prolonger', methods=['POST'])
@login_required
def location_prolonger(loc_id):
    loc = query("SELECT * FROM locations WHERE id=?", (loc_id,), one=True)
    if not loc:
        abort(404)
    if loc['statut'] not in ('reservee', 'en_cours'):
        flash("❌ Impossible de prolonger cette location.", "error")
        return redirect(url_for('location_detail', loc_id=loc_id))

    nouvelle_fin = request.form.get('nouvelle_date_fin')
    if not nouvelle_fin:
        flash("❌ Nouvelle date manquante.", "error")
        return redirect(url_for('location_detail', loc_id=loc_id))

    if nouvelle_fin <= loc['date_fin_prevue']:
        flash("❌ La nouvelle date doit être postérieure.", "error")
        return redirect(url_for('location_detail', loc_id=loc_id))

    ok, msg = check_dispo_location(loc['vehicule_id'], loc['date_debut'],
                                    nouvelle_fin, exclude_loc_id=loc_id)
    if not ok:
        flash(f"❌ {msg}", "error")
        return redirect(url_for('location_detail', loc_id=loc_id))

    jours, tarif_j, montant_ht = calcul_prix_location(
        loc['vehicule_id'], loc['date_debut'], nouvelle_fin)
    execute("""
        UPDATE locations SET date_fin_prevue=?, duree_jours=?,
            tarif_journalier=?, montant_ht=?, montant_total=montant_ht+frais_supplementaires
        WHERE id=?
    """, (nouvelle_fin, jours, tarif_j, montant_ht, loc_id))

    audit('extend', 'location', loc_id, nouvelle_fin)
    flash(f"✅ Location prolongée jusqu'au {fmt_date(nouvelle_fin)}.", "success")
    return redirect(url_for('location_detail', loc_id=loc_id))

@app.route('/locations/<int:loc_id>/contrat')
@login_required
def location_contrat(loc_id):
    loc = query("""
        SELECT l.*, c.nom AS client_nom, c.prenom AS client_prenom,
               c.telephone AS client_tel, c.adresse AS client_adresse,
               c.piece_identite, c.permis_conduire, c.code AS client_code,
               veh.code AS veh_code, veh.immatriculation, veh.vin_chassis,
               veh.annee, veh.couleur, veh.kilometrage AS veh_km,
               m.nom AS marque_nom, mo.nom AS modele_nom,
               a.nom AS agence_nom, a.adresse AS agence_adresse, a.telephone AS agence_tel
        FROM locations l
        LEFT JOIN clients c ON c.id=l.client_id
        LEFT JOIN vehicules veh ON veh.id=l.vehicule_id
        LEFT JOIN marques m ON m.id=veh.marque_id
        LEFT JOIN modeles mo ON mo.id=veh.modele_id
        LEFT JOIN agences a ON a.id=l.agence_id
        WHERE l.id=?
    """, (loc_id,), one=True)
    if not loc:
        abort(404)
    return render_template('locations/contrat.html', loc=loc)

@app.route('/locations/<int:loc_id>/etat-lieux/<mode>')
@login_required
def location_etat_lieux(loc_id, mode):
    if mode not in ('depart', 'retour'):
        abort(404)
    loc = query("""
        SELECT l.*, c.nom AS client_nom, c.prenom AS client_prenom,
               c.telephone AS client_tel, c.permis_conduire,
               veh.code AS veh_code, veh.immatriculation, veh.couleur,
               m.nom AS marque_nom, mo.nom AS modele_nom,
               a.nom AS agence_nom, a.adresse AS agence_adresse, a.telephone AS agence_tel
        FROM locations l
        LEFT JOIN clients c ON c.id=l.client_id
        LEFT JOIN vehicules veh ON veh.id=l.vehicule_id
        LEFT JOIN marques m ON m.id=veh.marque_id
        LEFT JOIN modeles mo ON mo.id=veh.modele_id
        LEFT JOIN agences a ON a.id=l.agence_id
        WHERE l.id=?
    """, (loc_id,), one=True)
    if not loc:
        abort(404)
    return render_template('locations/etat_lieux.html', loc=loc, mode=mode)

# ─── PAIEMENTS ───
@app.route('/paiements')
@login_required
def paiements_list():
    type_p = request.args.get('type', '').strip()
    mode = request.args.get('mode', '').strip()
    statut = request.args.get('statut', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 30

    where = " WHERE 1=1"
    params = []
    if type_p:
        where += " AND p.type=?"; params.append(type_p)
    if mode:
        where += " AND p.mode=?"; params.append(mode)
    if statut:
        where += " AND p.statut=?"; params.append(statut)
    if date_from:
        where += " AND date(p.date_paiement) >= date(?)"; params.append(date_from)
    if date_to:
        where += " AND date(p.date_paiement) <= date(?)"; params.append(date_to)

    total = query(f"SELECT COUNT(*) c FROM paiements p {where}", params, one=True)['c']
    offset = (page - 1) * per_page
    paiements = query(f"""
        SELECT p.*, c.nom AS client_nom, c.prenom AS client_prenom, c.telephone AS client_tel
        FROM paiements p
        LEFT JOIN clients c ON c.id=p.client_id
        {where}
        ORDER BY p.id DESC LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    kpi = {
        'total': query(f"SELECT COALESCE(SUM(montant),0) c FROM paiements p {where}",
                       params, one=True)['c'],
        'aujourdhui': query("""
            SELECT COALESCE(SUM(montant),0) c FROM paiements
            WHERE date(date_paiement)=date('now')
        """, one=True)['c'],
        'mobile_money': query("""
            SELECT COALESCE(SUM(montant),0) c FROM paiements
            WHERE mode IN ('orange_money','wave','free_money')
        """, one=True)['c'],
        'nb_transactions': total,
    }

    pages = (total + per_page - 1) // per_page
    return render_template('paiements/list.html', paiements=paiements, kpi=kpi,
                           type_p=type_p, mode=mode, statut=statut,
                           date_from=date_from, date_to=date_to,
                           page=page, pages=pages)

@app.route('/paiements/<int:pid>/supprimer', methods=['POST'])
@login_required
@admin_required
def paiement_delete(pid):
    execute("DELETE FROM paiements WHERE id=?", (pid,))
    audit('delete', 'paiement', pid)
    flash("🗑️ Paiement supprimé.", "success")
    return redirect(request.referrer or url_for('paiements_list'))


 






# ═══════════════════════════════════════════════════════════
# BLOC 5A — RECHERCHE + PORTAIL MOBILE (routes manquantes)
# ═══════════════════════════════════════════════════════════

# ─── RECHERCHE GLOBALE ───
@app.route('/recherche', endpoint='recherche_globale')
@login_required
def recherche_globale():
    q = request.args.get('q', '').strip()
    resultats = {'vehicules': [], 'clients': [], 'ventes': [], 'locations': []}
    if q and len(q) >= 2:
        resultats['vehicules'] = query("""
            SELECT v.id, v.code, v.immatriculation,
                   m.nom || ' ' || COALESCE(mo.nom,'') AS designation
            FROM vehicules v
            LEFT JOIN marques m ON m.id=v.marque_id
            LEFT JOIN modeles mo ON mo.id=v.modele_id
            WHERE v.code LIKE ? OR v.immatriculation LIKE ? OR v.vin_chassis LIKE ?
            LIMIT 10
        """, (f'%{q}%',) * 3)
        resultats['clients'] = query("""
            SELECT id, code, nom || ' ' || COALESCE(prenom,'') AS designation, telephone
            FROM clients
            WHERE nom LIKE ? OR prenom LIKE ? OR telephone LIKE ? OR code LIKE ?
            LIMIT 10
        """, (f'%{q}%',) * 4)
        resultats['ventes'] = query("""
            SELECT id, numero, montant_ttc, date_vente FROM ventes
            WHERE numero LIKE ? LIMIT 10
        """, (f'%{q}%',))
        resultats['locations'] = query("""
            SELECT id, numero, date_debut, date_fin_prevue FROM locations
            WHERE numero LIKE ? LIMIT 10
        """, (f'%{q}%',))
    return render_template('recherche.html', q=q, resultats=resultats)


# ─── PORTAIL MOBILE CLIENT (PUBLIC) ───
@app.route('/mobile', endpoint='mobile_home')
def mobile_home():
    marques = query("""
        SELECT DISTINCT m.id, m.nom,
               (SELECT COUNT(*) FROM vehicules v WHERE v.marque_id=m.id
                AND v.statut='disponible') nb
        FROM marques m
        WHERE EXISTS (SELECT 1 FROM vehicules v WHERE v.marque_id=m.id AND v.statut='disponible')
        ORDER BY m.nom
    """)
    vehicules_vedette = query("""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom, a.ville AS agence_ville
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        LEFT JOIN agences a ON a.id=v.agence_id
        WHERE v.statut='disponible' AND v.photo_principale IS NOT NULL
        ORDER BY v.id DESC LIMIT 6
    """)
    kpi = {
        'total_dispo': query("SELECT COUNT(*) c FROM vehicules WHERE statut='disponible'", one=True)['c'],
        'total_location': query("SELECT COUNT(*) c FROM vehicules WHERE statut='disponible' AND disponible_location=1", one=True)['c'],
        'total_marques': len(marques),
        'agences': query("SELECT COUNT(*) c FROM agences WHERE statut='actif'", one=True)['c'],
    }
    return render_template('mobile/home.html', marques=marques,
                           vehicules=vehicules_vedette, kpi=kpi)


@app.route('/mobile/catalogue', endpoint='mobile_catalogue')
def mobile_catalogue():
    q = request.args.get('q', '').strip()
    marque_id = request.args.get('marque_id', type=int)
    type_v = request.args.get('type', '').strip()
    carburant = request.args.get('carburant', '').strip()
    etat = request.args.get('etat', '').strip()
    budget_max = request.args.get('budget_max', type=float)
    mode = request.args.get('mode', 'vente')
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 12

    field = 'disponible_vente' if mode == 'vente' else 'disponible_location'
    where = f" WHERE v.statut='disponible' AND v.{field}=1"
    params = []
    if q:
        where += " AND (m.nom LIKE ? OR mo.nom LIKE ? OR v.description LIKE ?)"
        params += [f'%{q}%'] * 3
    if marque_id:
        where += " AND v.marque_id=?"; params.append(marque_id)
    if type_v:
        where += " AND v.type=?"; params.append(type_v)
    if carburant:
        where += " AND v.carburant=?"; params.append(carburant)
    if etat:
        where += " AND v.etat=?"; params.append(etat)
    if budget_max:
        col = 'prix_vente' if mode == 'vente' else 'prix_location_jour'
        where += f" AND v.{col} <= ?"; params.append(budget_max)

    total = query(f"""
        SELECT COUNT(*) c FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        {where}
    """, params, one=True)['c']

    offset = (page - 1) * per_page
    vehicules = query(f"""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom, a.ville AS agence_ville
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        LEFT JOIN agences a ON a.id=v.agence_id
        {where}
        ORDER BY v.id DESC LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    marques = query("SELECT * FROM marques ORDER BY nom")
    types = [r['type'] for r in query("""
        SELECT DISTINCT type FROM vehicules WHERE type IS NOT NULL AND type != ''
    """)]
    carburants = [r['carburant'] for r in query("""
        SELECT DISTINCT carburant FROM vehicules WHERE carburant IS NOT NULL AND carburant != ''
    """)]

    pages = (total + per_page - 1) // per_page
    return render_template('mobile/catalogue.html',
                           vehicules=vehicules, marques=marques,
                           types=types, carburants=carburants,
                           q=q, marque_id=marque_id, type_v=type_v,
                           carburant=carburant, etat=etat, budget_max=budget_max,
                           mode=mode, page=page, pages=pages, total=total)


@app.route('/mobile/vehicule/<int:vid>', endpoint='mobile_vehicule')
def mobile_vehicule(vid):
    v = query("""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom,
               a.nom AS agence_nom, a.ville AS agence_ville,
               a.adresse AS agence_adresse, a.telephone AS agence_tel,
               a.whatsapp AS agence_wa, a.horaires AS agence_horaires
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        LEFT JOIN agences a ON a.id=v.agence_id
        WHERE v.id=? AND v.statut != 'vendu'
    """, (vid,), one=True)
    if not v:
        abort(404)

    photos = query("SELECT * FROM vehicule_photos WHERE vehicule_id=? ORDER BY ordre, id", (vid,))
    videos = query("SELECT * FROM vehicule_videos WHERE vehicule_id=? ORDER BY id DESC", (vid,))
    similaires = query("""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        WHERE v.statut='disponible' AND v.id != ? AND v.marque_id = ?
        ORDER BY v.id DESC LIMIT 4
    """, (vid, v['marque_id']))
    return render_template('mobile/vehicule.html', v=v, photos=photos,
                           videos=videos, similaires=similaires)


@app.route('/mobile/reserver/<int:vid>', methods=['GET', 'POST'], endpoint='mobile_reserver')
def mobile_reserver(vid):
    v = query("""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom,
               a.nom AS agence_nom, a.telephone AS agence_tel
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        LEFT JOIN agences a ON a.id=v.agence_id
        WHERE v.id=? AND v.statut='disponible'
    """, (vid,), one=True)
    if not v:
        flash("Véhicule indisponible.", "error")
        return redirect(url_for('mobile_catalogue'))

    if request.method == 'POST':
        f = request.form
        nom = f.get('nom', '').strip()
        telephone = f.get('telephone', '').strip()
        type_demande = f.get('type_demande', 'vente')

        if not (nom and telephone):
            flash("❌ Nom et téléphone obligatoires.", "error")
            return redirect(request.url)

        client = query("SELECT * FROM clients WHERE telephone=?", (telephone,), one=True)
        if not client:
            cid = execute("""
                INSERT INTO clients (code, nom, prenom, type, telephone, whatsapp, email,
                    ville, pays, score, nb_achats, nb_locations, total_depense, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,0,0,0,'actif',?)
            """, (None, nom, f.get('prenom'),
                  'particulier', telephone, telephone, f.get('email'),
                  f.get('ville'), 'Sénégal', 50, datetime.now().isoformat()))
            client_id = cid
        else:
            client_id = client['id']

        if type_demande == 'location' and f.get('date_debut') and f.get('date_fin'):
            jours, tarif_j, montant_ht = calcul_prix_location(
                vid, f.get('date_debut'), f.get('date_fin'))
            numero = prochain_numero_location()
            lid = execute("""
                INSERT INTO locations (numero, vehicule_id, client_id, agence_id,
                    date_debut, date_fin_prevue, duree_jours, tarif_journalier,
                    montant_ht, caution, montant_total, statut, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (numero, vid, client_id, v['agence_id'],
                  f.get('date_debut'), f.get('date_fin'), jours, tarif_j,
                  montant_ht, 0, montant_ht, 'reservee',
                  f"Demande mobile : {f.get('message', '')[:200]}",
                  datetime.now().isoformat()))
            reference = numero
        else:
            numero = prochain_numero_vente()
            mid = execute("""
                INSERT INTO ventes (numero, vehicule_id, client_id, vendeur_id, agence_id,
                    date_vente, prix_vente, prix_achat, marge, remise, montant_ttc,
                    acompte, reste_a_payer, mode_paiement, type_vente, statut, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (numero, vid, client_id, None, v['agence_id'],
                  datetime.now().strftime('%Y-%m-%d'),
                  v['prix_vente'], v['prix_achat'] or 0,
                  (v['prix_vente'] or 0) - (v['prix_achat'] or 0),
                  0, v['prix_vente'], 0, v['prix_vente'],
                  'especes', 'comptant', 'devis',
                  f"Demande mobile : {f.get('message', '')[:200]}",
                  datetime.now().isoformat()))
            reference = numero

        envoyer_whatsapp(
            v['agence_tel'] or '+221770000000',
            f"🔔 *Nouvelle demande mobile*\n\n"
            f"Véhicule : {v['marque_nom']} {v['modele_nom']} ({v['code']})\n"
            f"Type : {type_demande}\n"
            f"Client : {nom} {f.get('prenom', '')}\n"
            f"Tél : {telephone}\n"
            f"Réf. : {reference}\n\n"
            f"Message : {f.get('message', '—')[:200]}",
            type_msg='reservation_mobile',
            vehicule_id=vid, client_id=client_id
        )

        recalc_score(client_id)
        audit('mobile_reservation', type_demande, None, reference)
        flash(f"✅ Demande enregistrée ! Réf. {reference}. Nous vous contactons sous 24h.", "success")
        return redirect(url_for('mobile_confirmation', reference=reference))

    return render_template('mobile/reserver.html', v=v)


@app.route('/mobile/confirmation/<reference>', endpoint='mobile_confirmation')
def mobile_confirmation(reference):
    vente = query("""
        SELECT v.*, c.nom AS client_nom, c.prenom AS client_prenom,
               veh.code AS veh_code, veh.immatriculation,
               m.nom AS marque_nom, mo.nom AS modele_nom
        FROM ventes v
        LEFT JOIN clients c ON c.id=v.client_id
        LEFT JOIN vehicules veh ON veh.id=v.vehicule_id
        LEFT JOIN marques m ON m.id=veh.marque_id
        LEFT JOIN modeles mo ON mo.id=veh.modele_id
        WHERE v.numero=?
    """, (reference,), one=True)

    location = None
    if not vente:
        location = query("""
            SELECT l.*, c.nom AS client_nom, c.prenom AS client_prenom,
                   veh.code AS veh_code, veh.immatriculation,
                   m.nom AS marque_nom, mo.nom AS modele_nom
            FROM locations l
            LEFT JOIN clients c ON c.id=l.client_id
            LEFT JOIN vehicules veh ON veh.id=l.vehicule_id
            LEFT JOIN marques m ON m.id=veh.marque_id
            LEFT JOIN modeles mo ON mo.id=veh.modele_id
            WHERE l.numero=?
        """, (reference,), one=True)

    return render_template('mobile/confirmation.html',
                           reference=reference, vente=vente, location=location)


@app.route('/mobile/suivi', methods=['GET', 'POST'], endpoint='mobile_suivi')
def mobile_suivi():
    resultats = []
    q = ''
    if request.method == 'POST':
        q = request.form.get('q', '').strip()
        if q:
            ventes = query("""
                SELECT v.*, c.nom AS client_nom, c.prenom AS client_prenom,
                       veh.code AS veh_code, m.nom AS marque_nom, mo.nom AS modele_nom
                FROM ventes v
                LEFT JOIN clients c ON c.id=v.client_id
                LEFT JOIN vehicules veh ON veh.id=v.vehicule_id
                LEFT JOIN marques m ON m.id=veh.marque_id
                LEFT JOIN modeles mo ON mo.id=veh.modele_id
                WHERE v.numero=? OR c.telephone=?
                ORDER BY v.id DESC LIMIT 20
            """, (q, q))
            locations = query("""
                SELECT l.*, c.nom AS client_nom, c.prenom AS client_prenom,
                       veh.code AS veh_code, m.nom AS marque_nom, mo.nom AS modele_nom
                FROM locations l
                LEFT JOIN clients c ON c.id=l.client_id
                LEFT JOIN vehicules veh ON veh.id=l.vehicule_id
                LEFT JOIN marques m ON m.id=veh.marque_id
                LEFT JOIN modeles mo ON mo.id=veh.modele_id
                WHERE l.numero=? OR c.telephone=?
                ORDER BY l.id DESC LIMIT 20
            """, (q, q))
            for v in ventes:
                resultats.append({'type': 'vente', 'data': v})
            for l in locations:
                resultats.append({'type': 'location', 'data': l})

    return render_template('mobile/suivi.html', resultats=resultats, q=q)


@app.route('/mobile/contact', endpoint='mobile_contact')
def mobile_contact():
    agences = query("SELECT * FROM agences WHERE statut='actif' ORDER BY ville, nom")
    return render_template('mobile/contact.html', agences=agences)



# ═══════════════════════════════════════════════════════════
# BLOC 4 — PAPIERS · ENTRETIENS · DOUANE · WHATSAPP · QR
# ═══════════════════════════════════════════════════════════

# ─── HELPERS PAPIERS ───
def jours_restants(date_expiration):
    if not date_expiration:
        return None
    try:
        exp = datetime.fromisoformat(str(date_expiration)[:10]).date()
        return (exp - datetime.now().date()).days
    except Exception:
        return None

def statut_papier(date_expiration):
    j = jours_restants(date_expiration)
    if j is None:
        return 'valide'
    if j < 0:
        return 'expire'
    if j <= 7:
        return 'critique'
    if j <= 30:
        return 'bientot'
    return 'valide'

def maj_statuts_papiers():
    papiers = query("""
        SELECT p.*, v.code AS veh_code, v.immatriculation
        FROM papiers p
        LEFT JOIN vehicules v ON v.id=p.vehicule_id
        WHERE p.date_expiration IS NOT NULL
    """)
    changes = 0
    for p in papiers:
        s = statut_papier(p['date_expiration'])
        if s != p['statut']:
            execute("UPDATE papiers SET statut=? WHERE id=?", (s, p['id']))
            changes += 1
    return changes

def generer_qr_papier(papier_id):
    p = query("""
        SELECT p.*, v.immatriculation, v.vin_chassis, v.code AS veh_code
        FROM papiers p
        LEFT JOIN vehicules v ON v.id=p.vehicule_id
        WHERE p.id=?
    """, (papier_id,), one=True)
    if not p:
        return None
    payload = {
        'app': 'OMEGA_AUTO', 'type': 'PAPIER', 'pid': p['id'],
        'veh_code': p['veh_code'], 'immat': p['immatriculation'],
        'vin': p['vin_chassis'], 'papier_type': p['type'],
        'numero': p['numero'], 'emission': p['date_emission'],
        'expiration': p['date_expiration'],
        'ts': datetime.now().isoformat(),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(',', ':'))

def verifier_qr_payload(payload_json):
    try:
        d = json.loads(payload_json)
    except Exception:
        return False, "QR illisible", None
    if d.get('app') != 'OMEGA_AUTO':
        return False, "QR non-OMEGA", None
    if d.get('type') == 'PAPIER':
        p = query("""
            SELECT p.*, v.immatriculation, v.vin_chassis, v.code AS veh_code
            FROM papiers p LEFT JOIN vehicules v ON v.id=p.vehicule_id
            WHERE p.id=?
        """, (d.get('pid'),), one=True)
        if not p:
            return False, "❌ Document inconnu — FRAUDE POSSIBLE", d
        alerts = []
        if p['numero'] != d.get('numero'):
            alerts.append("Numéro divergent")
        if p['immatriculation'] != d.get('immat'):
            alerts.append("Immatriculation divergente")
        if p['vin_chassis'] != d.get('vin'):
            alerts.append("VIN divergent")
        if alerts:
            return False, "🚨 FRAUDE : " + " · ".join(alerts), d
        s = statut_papier(p['date_expiration'])
        if s == 'expire':
            return False, "⚠️ Document EXPIRÉ", d
        return True, f"✅ Document authentique ({p['type']})", d
    return False, "Type inconnu", d


# ─── PAPIERS ───
@app.route('/papiers')
@login_required
def papiers_list():
    vehicule_id = request.args.get('vehicule_id', type=int)
    type_p = request.args.get('type', '').strip()
    statut = request.args.get('statut', '').strip()
    q = request.args.get('q', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 30

    where = " WHERE 1=1"
    params = []
    if vehicule_id:
        where += " AND p.vehicule_id=?"; params.append(vehicule_id)
    if type_p:
        where += " AND p.type=?"; params.append(type_p)
    if statut:
        where += " AND p.statut=?"; params.append(statut)
    if q:
        where += " AND (p.numero LIKE ? OR v.code LIKE ? OR v.immatriculation LIKE ?)"
        params += [f'%{q}%'] * 3

    total = query(f"""
        SELECT COUNT(*) c FROM papiers p
        LEFT JOIN vehicules v ON v.id=p.vehicule_id {where}
    """, params, one=True)['c']

    offset = (page - 1) * per_page
    papiers = query(f"""
        SELECT p.*, v.code AS veh_code, v.immatriculation,
               m.nom AS marque_nom, mo.nom AS modele_nom
        FROM papiers p
        LEFT JOIN vehicules v ON v.id=p.vehicule_id
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        {where}
        ORDER BY p.date_expiration ASC, p.id DESC
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    kpi = {
        'total': total,
        'valides': query("SELECT COUNT(*) c FROM papiers WHERE statut='valide'", one=True)['c'],
        'bientot': query("SELECT COUNT(*) c FROM papiers WHERE statut='bientot'", one=True)['c'],
        'critiques': query("SELECT COUNT(*) c FROM papiers WHERE statut='critique'", one=True)['c'],
        'expires': query("SELECT COUNT(*) c FROM papiers WHERE statut='expire'", one=True)['c'],
    }

    pages = (total + per_page - 1) // per_page
    return render_template('papiers/list.html', papiers=papiers, kpi=kpi,
                           vehicule_id=vehicule_id, type_p=type_p, statut=statut, q=q,
                           page=page, pages=pages)

@app.route('/papiers/nouveau', methods=['GET', 'POST'])
@login_required
def papier_new():
    vehicule_id = request.args.get('vehicule_id', type=int)
    if request.method == 'POST':
        f = request.form
        vid = int(f.get('vehicule_id') or 0)
        if not vid:
            flash("❌ Véhicule obligatoire.", "error")
            return redirect(request.url)
        pid = execute("""
            INSERT INTO papiers (vehicule_id, type, numero, date_emission, date_expiration,
                fichier_path, compagnie, montant, statut, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (vid, f.get('type'), f.get('numero'),
              f.get('date_emission') or None, f.get('date_expiration') or None,
              None, f.get('compagnie'), float(f.get('montant') or 0),
              statut_papier(f.get('date_expiration')), datetime.now().isoformat()))
        fichier = request.files.get('fichier')
        if fichier and fichier.filename:
            fname = save_upload(fichier, PAPIERS_DIR, ALLOWED_DOC)
            if fname:
                execute("UPDATE papiers SET fichier_path=? WHERE id=?", (fname, pid))
        audit('create', 'papier', pid)
        flash("✅ Papier enregistré.", "success")
        return redirect(url_for('papier_detail', pid=pid))
    vehicules = query("""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        WHERE v.statut != 'vendu' ORDER BY v.code
    """)
    return render_template('papiers/form.html', papier=None,
                           vehicules=vehicules, vehicule_id=vehicule_id)

@app.route('/papiers/<int:pid>')
@login_required
def papier_detail(pid):
    p = query("""
        SELECT p.*, v.code AS veh_code, v.immatriculation, v.vin_chassis,
               v.photo_principale, v.id AS vehicule_id,
               m.nom AS marque_nom, mo.nom AS modele_nom
        FROM papiers p
        LEFT JOIN vehicules v ON v.id=p.vehicule_id
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        WHERE p.id=?
    """, (pid,), one=True)
    if not p:
        abort(404)
    jours = jours_restants(p['date_expiration'])
    qr_payload = generer_qr_papier(pid)
    return render_template('papiers/detail.html', p=p, jours=jours, qr_payload=qr_payload)

@app.route('/papiers/<int:pid>/editer', methods=['GET', 'POST'])
@login_required
def papier_edit(pid):
    p = query("SELECT * FROM papiers WHERE id=?", (pid,), one=True)
    if not p:
        abort(404)
    if request.method == 'POST':
        f = request.form
        execute("""
            UPDATE papiers SET type=?, numero=?, date_emission=?, date_expiration=?,
                compagnie=?, montant=?, statut=? WHERE id=?
        """, (f.get('type'), f.get('numero'),
              f.get('date_emission') or None, f.get('date_expiration') or None,
              f.get('compagnie'), float(f.get('montant') or 0),
              statut_papier(f.get('date_expiration')), pid))
        fichier = request.files.get('fichier')
        if fichier and fichier.filename:
            fname = save_upload(fichier, PAPIERS_DIR, ALLOWED_DOC)
            if fname:
                execute("UPDATE papiers SET fichier_path=? WHERE id=?", (fname, pid))
        audit('update', 'papier', pid)
        flash("✅ Papier mis à jour.", "success")
        return redirect(url_for('papier_detail', pid=pid))
    vehicules = query("""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        ORDER BY v.code
    """)
    return render_template('papiers/form.html', papier=p, vehicules=vehicules)

@app.route('/papiers/<int:pid>/supprimer', methods=['POST'])
@login_required
@admin_required
def papier_delete(pid):
    execute("DELETE FROM papiers WHERE id=?", (pid,))
    audit('delete', 'papier', pid)
    flash("🗑️ Papier supprimé.", "success")
    return redirect(url_for('papiers_list'))

@app.route('/papiers/<int:pid>/qr')
@login_required
def papier_qr(pid):
    payload = generer_qr_papier(pid)
    if not payload:
        abort(404)
    img = qrcode.make(payload)
    buf = BytesIO()
    img.save(buf, format='PNG')
    return Response(buf.getvalue(), mimetype='image/png')

@app.route('/papiers/verifier', methods=['GET', 'POST'])
@login_required
def papier_verifier():
    result = None
    data = None
    if request.method == 'POST':
        payload = request.form.get('payload', '').strip()
        if payload:
            ok, message, data = verifier_qr_payload(payload)
            result = {'ok': ok, 'message': message}
            audit('verify_qr', 'papier', details=message[:200] if message else None)
    return render_template('papiers/verifier.html', result=result, data=data)

@app.route('/papiers/scan')
@login_required
def papier_scan():
    return render_template('papiers/scan.html')

@app.route('/papiers/scan/submit', methods=['POST'])
@login_required
def papier_scan_submit():
    payload = (request.json or {}).get('payload', '') if request.is_json else request.form.get('payload', '')
    if not payload:
        return jsonify(ok=False, message="Aucun payload"), 400
    ok, message, data = verifier_qr_payload(payload)
    return jsonify(ok=ok, message=message, data=data)

@app.route('/papiers/alertes')
@login_required
def papiers_alertes():
    maj_statuts_papiers()
    alertes = {
        'expires': query("""SELECT p.*, v.code AS veh_code, v.immatriculation
            FROM papiers p LEFT JOIN vehicules v ON v.id=p.vehicule_id
            WHERE p.statut='expire' ORDER BY p.date_expiration"""),
        'critiques': query("""SELECT p.*, v.code AS veh_code, v.immatriculation
            FROM papiers p LEFT JOIN vehicules v ON v.id=p.vehicule_id
            WHERE p.statut='critique' ORDER BY p.date_expiration"""),
        'bientot': query("""SELECT p.*, v.code AS veh_code, v.immatriculation
            FROM papiers p LEFT JOIN vehicules v ON v.id=p.vehicule_id
            WHERE p.statut='bientot' ORDER BY p.date_expiration"""),
    }
    return render_template('papiers/alertes.html', alertes=alertes)

@app.route('/papiers/recalculer-statuts', methods=['POST'])
@login_required
def papiers_recalcul():
    n = maj_statuts_papiers()
    flash(f"🔄 {n} statut(s) mis à jour.", "success")
    return redirect(request.referrer or url_for('papiers_list'))

# ─── ENTRETIENS ───
@app.route('/entretiens')
@login_required
def entretiens_list():
    vehicule_id = request.args.get('vehicule_id', type=int)
    q = request.args.get('q', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 30

    where = " WHERE 1=1"
    params = []
    if vehicule_id:
        where += " AND e.vehicule_id=?"; params.append(vehicule_id)
    if q:
        where += " AND (e.description LIKE ? OR e.garage LIKE ? OR v.code LIKE ?)"
        params += [f'%{q}%'] * 3

    total = query(f"""
        SELECT COUNT(*) c FROM entretiens e
        LEFT JOIN vehicules v ON v.id=e.vehicule_id {where}
    """, params, one=True)['c']

    offset = (page - 1) * per_page
    entretiens = query(f"""
        SELECT e.*, v.code AS veh_code, v.immatriculation,
               m.nom AS marque_nom, mo.nom AS modele_nom
        FROM entretiens e
        LEFT JOIN vehicules v ON v.id=e.vehicule_id
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        {where}
        ORDER BY e.date_entretien DESC, e.id DESC
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    kpi = {
        'total': total,
        'cout_total': query("SELECT COALESCE(SUM(cout),0) c FROM entretiens", one=True)['c'],
        'ce_mois': query("""SELECT COUNT(*) c FROM entretiens
            WHERE strftime('%Y-%m', date_entretien)=strftime('%Y-%m','now')""", one=True)['c'],
        'cout_mois': query("""SELECT COALESCE(SUM(cout),0) c FROM entretiens
            WHERE strftime('%Y-%m', date_entretien)=strftime('%Y-%m','now')""", one=True)['c'],
    }
    pages = (total + per_page - 1) // per_page
    return render_template('entretiens/list.html', entretiens=entretiens, kpi=kpi,
                           vehicule_id=vehicule_id, q=q, page=page, pages=pages)

@app.route('/entretiens/nouveau', methods=['GET', 'POST'])
@login_required
def entretien_new():
    vehicule_id = request.args.get('vehicule_id', type=int)
    if request.method == 'POST':
        f = request.form
        eid = execute("""
            INSERT INTO entretiens (vehicule_id, type, description, kilometrage, cout,
                garage, date_entretien, prochain_km, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (int(f.get('vehicule_id') or 0), f.get('type'), f.get('description'),
              float(f.get('kilometrage') or 0), float(f.get('cout') or 0),
              f.get('garage'), f.get('date_entretien') or datetime.now().strftime('%Y-%m-%d'),
              float(f.get('prochain_km') or 0), datetime.now().isoformat()))
        km = float(f.get('kilometrage') or 0)
        if km > 0:
            v = query("SELECT kilometrage FROM vehicules WHERE id=?",
                      (f.get('vehicule_id'),), one=True)
            if v and km > (v['kilometrage'] or 0):
                execute("UPDATE vehicules SET kilometrage=? WHERE id=?",
                        (km, f.get('vehicule_id')))
        audit('create', 'entretien', eid)
        flash("✅ Entretien enregistré.", "success")
        return redirect(url_for('entretien_detail', eid=eid))
    vehicules = query("""SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        ORDER BY v.code""")
    return render_template('entretiens/form.html', entretien=None,
                           vehicules=vehicules, vehicule_id=vehicule_id)

@app.route('/entretiens/<int:eid>')
@login_required
def entretien_detail(eid):
    e = query("""SELECT e.*, v.code AS veh_code, v.immatriculation, v.kilometrage AS veh_km,
               m.nom AS marque_nom, mo.nom AS modele_nom
        FROM entretiens e
        LEFT JOIN vehicules v ON v.id=e.vehicule_id
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        WHERE e.id=?""", (eid,), one=True)
    if not e:
        abort(404)
    historique = query("SELECT * FROM entretiens WHERE vehicule_id=? ORDER BY date_entretien DESC",
                       (e['vehicule_id'],))
    total_cout = sum((h['cout'] or 0) for h in historique)
    return render_template('entretiens/detail.html', e=e,
                           historique=historique, total_cout=total_cout)

@app.route('/entretiens/<int:eid>/editer', methods=['GET', 'POST'])
@login_required
def entretien_edit(eid):
    e = query("SELECT * FROM entretiens WHERE id=?", (eid,), one=True)
    if not e:
        abort(404)
    if request.method == 'POST':
        f = request.form
        execute("""UPDATE entretiens SET type=?, description=?, kilometrage=?, cout=?,
                garage=?, date_entretien=?, prochain_km=? WHERE id=?""",
                (f.get('type'), f.get('description'), float(f.get('kilometrage') or 0),
                 float(f.get('cout') or 0), f.get('garage'), f.get('date_entretien'),
                 float(f.get('prochain_km') or 0), eid))
        audit('update', 'entretien', eid)
        flash("✅ Entretien mis à jour.", "success")
        return redirect(url_for('entretien_detail', eid=eid))
    vehicules = query("""SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        ORDER BY v.code""")
    return render_template('entretiens/form.html', entretien=e, vehicules=vehicules)

@app.route('/entretiens/<int:eid>/supprimer', methods=['POST'])
@login_required
@admin_required
def entretien_delete(eid):
    execute("DELETE FROM entretiens WHERE id=?", (eid,))
    audit('delete', 'entretien', eid)
    flash("🗑️ Entretien supprimé.", "success")
    return redirect(url_for('entretiens_list'))

@app.route('/vehicules/<int:vid>/historique')
@login_required
def vehicule_historique(vid):
    v = query("""SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        WHERE v.id=?""", (vid,), one=True)
    if not v:
        abort(404)
    entretiens = query("SELECT * FROM entretiens WHERE vehicule_id=? ORDER BY date_entretien", (vid,))
    papiers = query("SELECT * FROM papiers WHERE vehicule_id=? ORDER BY date_expiration", (vid,))
    total_cout = sum((e['cout'] or 0) for e in entretiens)
    return render_template('vehicules/historique.html', v=v, entretiens=entretiens,
                           papiers=papiers, total_cout=total_cout)

# ─── DOUANE ───
@app.route('/douane')
@login_required
def douane_list():
    statut = request.args.get('statut', '').strip()
    q = request.args.get('q', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 30

    where = " WHERE 1=1"
    params = []
    if statut:
        where += " AND d.statut=?"; params.append(statut)
    if q:
        where += " AND (d.numero_declaration LIKE ? OR d.bureau_douane LIKE ? OR v.code LIKE ?)"
        params += [f'%{q}%'] * 3

    total = query(f"""SELECT COUNT(*) c FROM douane d
        LEFT JOIN vehicules v ON v.id=d.vehicule_id {where}""", params, one=True)['c']

    offset = (page - 1) * per_page
    dossiers = query(f"""SELECT d.*, v.code AS veh_code, v.immatriculation, v.annee,
               m.nom AS marque_nom, mo.nom AS modele_nom
        FROM douane d
        LEFT JOIN vehicules v ON v.id=d.vehicule_id
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        {where} ORDER BY d.id DESC LIMIT ? OFFSET ?""", params + [per_page, offset])

    kpi = {
        'total': total,
        'en_cours': query("SELECT COUNT(*) c FROM douane WHERE statut='en_cours'", one=True)['c'],
        'dedouanes': query("SELECT COUNT(*) c FROM douane WHERE statut='dedouane'", one=True)['c'],
        'droits_total': query("SELECT COALESCE(SUM(droits_taxes),0) c FROM douane", one=True)['c'],
        'valeur_caf': query("SELECT COALESCE(SUM(valeur_caf),0) c FROM douane", one=True)['c'],
    }
    pages = (total + per_page - 1) // per_page
    return render_template('douane/list.html', dossiers=dossiers, kpi=kpi,
                           statut=statut, q=q, page=page, pages=pages)

@app.route('/douane/nouveau', methods=['GET', 'POST'])
@login_required
def douane_new():
    vehicule_id = request.args.get('vehicule_id', type=int)
    if request.method == 'POST':
        f = request.form
        did = execute("""INSERT INTO douane (vehicule_id, numero_declaration, bureau_douane,
                pays_origine, date_import, valeur_caf, droits_taxes, statut,
                date_dedouanement, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (int(f.get('vehicule_id') or 0), f.get('numero_declaration'),
             f.get('bureau_douane'), f.get('pays_origine'), f.get('date_import'),
             float(f.get('valeur_caf') or 0), float(f.get('droits_taxes') or 0),
             f.get('statut') or 'en_cours', f.get('date_dedouanement') or None,
             datetime.now().isoformat()))
        audit('create', 'douane', did)
        flash("✅ Dossier douane créé.", "success")
        return redirect(url_for('douane_detail', did=did))
    vehicules = query("""SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        ORDER BY v.code""")
    return render_template('douane/form.html', dossier=None,
                           vehicules=vehicules, vehicule_id=vehicule_id)

@app.route('/douane/<int:did>')
@login_required
def douane_detail(did):
    d = query("""SELECT d.*, v.code AS veh_code, v.immatriculation, v.vin_chassis,
               v.annee, v.prix_achat, v.photo_principale,
               m.nom AS marque_nom, mo.nom AS modele_nom
        FROM douane d
        LEFT JOIN vehicules v ON v.id=d.vehicule_id
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        WHERE d.id=?""", (did,), one=True)
    if not d:
        abort(404)
    total_import = (d['valeur_caf'] or 0) + (d['droits_taxes'] or 0)
    return render_template('douane/detail.html', d=d, total_import=total_import)

@app.route('/douane/<int:did>/editer', methods=['GET', 'POST'])
@login_required
def douane_edit(did):
    d = query("SELECT * FROM douane WHERE id=?", (did,), one=True)
    if not d:
        abort(404)
    if request.method == 'POST':
        f = request.form
        execute("""UPDATE douane SET numero_declaration=?, bureau_douane=?, pays_origine=?,
                date_import=?, valeur_caf=?, droits_taxes=?, statut=?, date_dedouanement=?
            WHERE id=?""",
            (f.get('numero_declaration'), f.get('bureau_douane'), f.get('pays_origine'),
             f.get('date_import'), float(f.get('valeur_caf') or 0),
             float(f.get('droits_taxes') or 0), f.get('statut') or 'en_cours',
             f.get('date_dedouanement') or None, did))
        audit('update', 'douane', did)
        flash("✅ Dossier mis à jour.", "success")
        return redirect(url_for('douane_detail', did=did))
    vehicules = query("""SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        ORDER BY v.code""")
    return render_template('douane/form.html', dossier=d, vehicules=vehicules)

@app.route('/douane/<int:did>/supprimer', methods=['POST'])
@login_required
@admin_required
def douane_delete(did):
    execute("DELETE FROM douane WHERE id=?", (did,))
    audit('delete', 'douane', did)
    flash("🗑️ Dossier douane supprimé.", "success")
    return redirect(url_for('douane_list'))

# ─── WHATSAPP ───
def envoyer_whatsapp(destinataire, message, type_msg='manuel',
                     vehicule_id=None, client_id=None):
    if not destinataire:
        return None
    tel = ''.join(c for c in str(destinataire) if c.isdigit() or c == '+')
    wid = execute("""INSERT INTO whatsapp_log (destinataire, type, vehicule_id, client_id,
            message, statut, mode, date_envoi, created_at)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (tel, type_msg, vehicule_id, client_id, message,
         'envoye', 'simulation', datetime.now().isoformat(), datetime.now().isoformat()))
    audit('whatsapp', 'message', wid, f"to={tel}")
    return wid

@app.route('/whatsapp')
@login_required
def whatsapp_dashboard():
    type_msg = request.args.get('type', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 30

    where = " WHERE 1=1"
    params = []
    if type_msg:
        where += " AND w.type=?"; params.append(type_msg)

    total = query(f"SELECT COUNT(*) c FROM whatsapp_log w {where}", params, one=True)['c']
    offset = (page - 1) * per_page
    messages = query(f"""SELECT w.*, c.nom AS client_nom, c.prenom AS client_prenom,
               v.code AS veh_code
        FROM whatsapp_log w
        LEFT JOIN clients c ON c.id=w.client_id
        LEFT JOIN vehicules v ON v.id=w.vehicule_id
        {where} ORDER BY w.id DESC LIMIT ? OFFSET ?""", params + [per_page, offset])

    kpi = {
        'total': total,
        'aujourdhui': query("SELECT COUNT(*) c FROM whatsapp_log WHERE date(date_envoi)=date('now')", one=True)['c'],
        'catalogue': query("SELECT COUNT(*) c FROM whatsapp_log WHERE type='catalogue'", one=True)['c'],
        'relances': query("SELECT COUNT(*) c FROM whatsapp_log WHERE type='relance'", one=True)['c'],
        'confirmations': query("SELECT COUNT(*) c FROM whatsapp_log WHERE type='confirmation'", one=True)['c'],
    }
    pages = (total + per_page - 1) // per_page
    return render_template('whatsapp/dashboard.html', messages=messages, kpi=kpi,
                           type_msg=type_msg, page=page, pages=pages)

@app.route('/whatsapp/envoyer', methods=['GET', 'POST'])
@login_required
def whatsapp_envoyer():
    vehicule_id = request.args.get('vehicule_id', type=int)
    client_id = request.args.get('client_id', type=int)
    if request.method == 'POST':
        f = request.form
        destinataire = f.get('destinataire') or f.get('telephone')
        message = f.get('message', '').strip()
        if destinataire and message:
            envoyer_whatsapp(destinataire, message, type_msg=f.get('template') or 'manuel',
                             vehicule_id=int(f.get('vehicule_id') or 0) or None,
                             client_id=int(f.get('client_id') or 0) or None)
            flash("📱 Message WhatsApp envoyé.", "success")
            return redirect(url_for('whatsapp_dashboard'))
        flash("❌ Destinataire et message obligatoires.", "error")
    clients = query("SELECT * FROM clients WHERE statut='actif' ORDER BY nom LIMIT 300")
    vehicules = query("""SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        WHERE v.statut='disponible' ORDER BY m.nom, mo.nom LIMIT 300""")
    client = query("SELECT * FROM clients WHERE id=?", (client_id,), one=True) if client_id else None
    vehicule = query("""SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom
        FROM vehicules v LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id WHERE v.id=?""",
        (vehicule_id,), one=True) if vehicule_id else None
    return render_template('whatsapp/envoyer.html', clients=clients,
                           vehicules=vehicules, client=client, vehicule=vehicule)

@app.route('/whatsapp/catalogue/<int:vid>', methods=['POST'])
@login_required
def whatsapp_catalogue(vid):
    tel = request.form.get('telephone', '').strip()
    if not tel:
        flash("❌ Numéro manquant.", "error")
        return redirect(url_for('vehicule_detail', vid=vid))
    v = query("""SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom,
               a.nom AS agence_nom, a.telephone AS agence_tel
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        LEFT JOIN agences a ON a.id=v.agence_id
        WHERE v.id=?""", (vid,), one=True)
    message = (f"🚗 *OMEGA AUTO — {v['marque_nom']} {v['modele_nom']}*\n\n"
               f"📅 {v['annee']} · 🛣️ {int(v['kilometrage'] or 0)} km\n"
               f"💰 {fmt_money(v['prix_vente'])}\n"
               f"📍 {v['agence_nom']} · {v['agence_tel']}\nRéf. {v['code']}")
    envoyer_whatsapp(tel, message, type_msg='catalogue', vehicule_id=vid)
    flash("📱 Catalogue envoyé.", "success")
    return redirect(url_for('vehicule_detail', vid=vid))

@app.route('/whatsapp/relance-client/<int:cid>', methods=['POST'])
@login_required
def whatsapp_relance_client(cid):
    c = query("SELECT * FROM clients WHERE id=?", (cid,), one=True)
    if not c:
        abort(404)
    message = request.form.get('message') or (
        f"👋 Bonjour {c['prenom'] or ''} {c['nom']},\n\n"
        f"Nouveaux véhicules disponibles chez OMEGA AUTO !\nMerci 🙏")
    envoyer_whatsapp(c['whatsapp'] or c['telephone'], message, type_msg='relance', client_id=cid)
    flash("📱 Relance envoyée.", "success")
    return redirect(url_for('client_detail', cid=cid))

@app.route('/whatsapp/relance-location/<int:loc_id>', methods=['POST'])
@login_required
def whatsapp_relance_location(loc_id):
    loc = query("""SELECT l.*, c.nom AS client_nom, c.prenom AS client_prenom,
               c.telephone AS client_tel, c.whatsapp AS client_wa,
               v.code AS veh_code, m.nom AS marque_nom, mo.nom AS modele_nom
        FROM locations l
        LEFT JOIN clients c ON c.id=l.client_id
        LEFT JOIN vehicules v ON v.id=l.vehicule_id
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        WHERE l.id=?""", (loc_id,), one=True)
    if not loc:
        abort(404)
    message = (f"⏰ *Rappel OMEGA AUTO*\n\nVotre location du "
               f"{loc['marque_nom']} {loc['modele_nom']} ({loc['veh_code']})\n"
               f"se termine le *{fmt_date(loc['date_fin_prevue'])}*.\nMerci de nous contacter.")
    envoyer_whatsapp(loc['client_wa'] or loc['client_tel'], message,
                     type_msg='rappel_location', vehicule_id=loc['vehicule_id'],
                     client_id=loc['client_id'])
    flash("📱 Rappel envoyé.", "success")
    return redirect(url_for('location_detail', loc_id=loc_id))

@app.route('/whatsapp/<int:wid>/supprimer', methods=['POST'])
@login_required
@admin_required
def whatsapp_delete(wid):
    execute("DELETE FROM whatsapp_log WHERE id=?", (wid,))
    flash("🗑️ Message supprimé.", "success")
    return redirect(url_for('whatsapp_dashboard'))

# ─── ANTI-FRAUDE ───
@app.route('/anti-fraude')
@login_required
def anti_fraude_dashboard():
    expires = query("""SELECT p.*, v.code AS veh_code, v.immatriculation
        FROM papiers p LEFT JOIN vehicules v ON v.id=p.vehicule_id
        WHERE p.statut='expire' ORDER BY p.date_expiration LIMIT 50""")
    doublons_immat = query("""SELECT immatriculation, COUNT(*) nb
        FROM vehicules WHERE immatriculation IS NOT NULL AND immatriculation != ''
        GROUP BY immatriculation HAVING nb > 1""")
    doublons_vin = query("""SELECT vin_chassis, COUNT(*) nb
        FROM vehicules WHERE vin_chassis IS NOT NULL AND vin_chassis != ''
        GROUP BY vin_chassis HAVING nb > 1""")
    locs_suspectes = query("""SELECT l.*, c.nom AS client_nom, c.prenom AS client_prenom,
               v.code AS veh_code, v.immatriculation
        FROM locations l
        LEFT JOIN clients c ON c.id=l.client_id
        LEFT JOIN vehicules v ON v.id=l.vehicule_id
        WHERE l.notes IS NULL OR l.notes = ''
        ORDER BY l.id DESC LIMIT 20""")
    kpi = {
        'expires': query("SELECT COUNT(*) c FROM papiers WHERE statut='expire'", one=True)['c'],
        'doublons_immat': len(doublons_immat),
        'doublons_vin': len(doublons_vin),
        'locs_suspectes': len(locs_suspectes),
    }
    return render_template('anti_fraude/dashboard.html',
                           expires=expires, doublons_immat=doublons_immat,
                           doublons_vin=doublons_vin, locs_suspectes=locs_suspectes,
                           kpi=kpi)

@app.route('/anti-fraude/verifier', methods=['GET', 'POST'])
@login_required
def anti_fraude_verifier():
    return redirect(url_for('papier_verifier'))



# ═══════════════════════════════════════════════════════════
# BLOC 5 — RAPPORTS · EXPORTS · ADMIN · API
# ═══════════════════════════════════════════════════════════

# ─── HELPERS RAPPORTS ───
def parse_periode():
    periode = request.args.get('periode', 'mois')
    today = datetime.now().date()
    if periode == 'jour':
        d1 = d2 = today
        label = f"Aujourd'hui ({d1.strftime('%d/%m/%Y')})"
    elif periode == 'semaine':
        d1 = today - timedelta(days=today.weekday())
        d2 = today
        label = "Cette semaine"
    elif periode == 'mois':
        d1 = today.replace(day=1)
        d2 = today
        label = f"{d1.strftime('%B %Y')}"
    elif periode == 'trimestre':
        q = (today.month - 1) // 3
        d1 = today.replace(month=q * 3 + 1, day=1)
        d2 = today
        label = f"T{q + 1} {today.year}"
    elif periode == 'annee':
        d1 = today.replace(month=1, day=1)
        d2 = today
        label = f"Année {today.year}"
    elif periode == 'custom':
        try:
            d1 = datetime.fromisoformat(request.args.get('date_from', '')).date()
            d2 = datetime.fromisoformat(request.args.get('date_to', '')).date()
            label = f"{d1.strftime('%d/%m/%Y')} → {d2.strftime('%d/%m/%Y')}"
        except Exception:
            d1 = today.replace(day=1)
            d2 = today
            label = "Période personnalisée"
    else:
        d1 = today.replace(day=1)
        d2 = today
        label = "Ce mois"
    return d1.isoformat(), d2.isoformat(), label, periode

def csv_response(rows, headers, filename):
    def gen():
        yield '\ufeff'
        yield ','.join(f'"{h}"' for h in headers) + '\n'
        for r in rows:
            line = []
            for h in headers:
                v = r.get(h, '') if isinstance(r, dict) else ''
                v = str(v).replace('"', '""')
                line.append(f'"{v}"')
            yield ','.join(line) + '\n'
    return Response(gen(), mimetype='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})

# ─── RAPPORTS ───
@app.route('/rapports')
@login_required
def rapports_home():
    return render_template('rapports/home.html')

@app.route('/rapports/ventes')
@login_required
def rapports_ventes():
    d1, d2, label, periode = parse_periode()
    kpi = {
        'nb_ventes': query("""
            SELECT COUNT(*) c FROM ventes
            WHERE statut='livree' AND date(date_vente) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
        'ca': query("""
            SELECT COALESCE(SUM(montant_ttc),0) c FROM ventes
            WHERE statut='livree' AND date(date_vente) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
        'marge': query("""
            SELECT COALESCE(SUM(marge),0) c FROM ventes
            WHERE statut='livree' AND date(date_vente) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
    }
    kpi['panier_moyen'] = round(kpi['ca'] / kpi['nb_ventes'], 0) if kpi['nb_ventes'] else 0
    kpi['taux_marge'] = round(100 * kpi['marge'] / kpi['ca'], 1) if kpi['ca'] else 0

    par_marque = query("""
        SELECT m.nom AS marque, COUNT(v.id) nb,
               COALESCE(SUM(v.montant_ttc),0) ca,
               COALESCE(SUM(v.marge),0) marge
        FROM ventes v
        JOIN vehicules veh ON veh.id=v.vehicule_id
        JOIN marques m ON m.id=veh.marque_id
        WHERE v.statut='livree' AND date(v.date_vente) BETWEEN ? AND ?
        GROUP BY m.id ORDER BY ca DESC
    """, (d1, d2))

    par_agence = query("""
        SELECT a.nom AS agence, COUNT(v.id) nb, COALESCE(SUM(v.montant_ttc),0) ca
        FROM ventes v
        JOIN agences a ON a.id=v.agence_id
        WHERE v.statut='livree' AND date(v.date_vente) BETWEEN ? AND ?
        GROUP BY a.id ORDER BY ca DESC
    """, (d1, d2))

    par_vendeur = query("""
        SELECT COALESCE(u.nom_complet,'—') AS vendeur, COUNT(v.id) nb,
               COALESCE(SUM(v.montant_ttc),0) ca,
               COALESCE(SUM(v.marge),0) marge
        FROM ventes v
        LEFT JOIN users u ON u.id=v.vendeur_id
        WHERE v.statut='livree' AND date(v.date_vente) BETWEEN ? AND ?
        GROUP BY u.id ORDER BY ca DESC
    """, (d1, d2))

    par_mode = query("""
        SELECT mode_paiement, COUNT(*) nb, COALESCE(SUM(montant_ttc),0) ca
        FROM ventes
        WHERE statut='livree' AND date(date_vente) BETWEEN ? AND ?
        GROUP BY mode_paiement ORDER BY ca DESC
    """, (d1, d2))

    evolution = query("""
        SELECT date(date_vente) jour, COUNT(*) nb, COALESCE(SUM(montant_ttc),0) ca
        FROM ventes
        WHERE statut='livree' AND date(date_vente) BETWEEN ? AND ?
        GROUP BY jour ORDER BY jour
    """, (d1, d2))

    return render_template('rapports/ventes.html',
                           kpi=kpi, par_marque=par_marque, par_agence=par_agence,
                           par_vendeur=par_vendeur, par_mode=par_mode,
                           evolution=evolution, label=label, periode=periode,
                           d1=d1, d2=d2)

@app.route('/rapports/locations')
@login_required
def rapports_locations():
    d1, d2, label, periode = parse_periode()
    kpi = {
        'nb': query("""
            SELECT COUNT(*) c FROM locations WHERE date(date_debut) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
        'ca': query("""
            SELECT COALESCE(SUM(montant_total),0) c FROM locations
            WHERE statut IN ('terminee','en_cours') AND date(date_debut) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
        'jours': query("""
            SELECT COALESCE(SUM(duree_jours),0) c FROM locations
            WHERE date(date_debut) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
        'km': query("""
            SELECT COALESCE(SUM(km_parcourus),0) c FROM locations
            WHERE statut='terminee' AND date(date_debut) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
    }
    kpi['duree_moy'] = round(kpi['jours'] / kpi['nb'], 1) if kpi['nb'] else 0
    kpi['ca_jour'] = round(kpi['ca'] / kpi['jours'], 0) if kpi['jours'] else 0

    par_vehicule = query("""
        SELECT veh.code AS vehicule, veh.immatriculation,
               m.nom AS marque, mo.nom AS modele,
               COUNT(l.id) nb, COALESCE(SUM(l.duree_jours),0) jours,
               COALESCE(SUM(l.montant_total),0) ca
        FROM locations l
        JOIN vehicules veh ON veh.id=l.vehicule_id
        LEFT JOIN marques m ON m.id=veh.marque_id
        LEFT JOIN modeles mo ON mo.id=veh.modele_id
        WHERE date(l.date_debut) BETWEEN ? AND ?
        GROUP BY veh.id ORDER BY ca DESC LIMIT 20
    """, (d1, d2))

    par_client = query("""
        SELECT c.nom, c.prenom, c.telephone, COUNT(l.id) nb,
               COALESCE(SUM(l.montant_total),0) ca
        FROM locations l
        JOIN clients c ON c.id=l.client_id
        WHERE date(l.date_debut) BETWEEN ? AND ?
        GROUP BY c.id ORDER BY ca DESC LIMIT 20
    """, (d1, d2))

    evolution = query("""
        SELECT date(date_debut) jour, COUNT(*) nb, COALESCE(SUM(montant_total),0) ca
        FROM locations
        WHERE date(date_debut) BETWEEN ? AND ?
        GROUP BY jour ORDER BY jour
    """, (d1, d2))

    return render_template('rapports/locations.html',
                           kpi=kpi, par_vehicule=par_vehicule, par_client=par_client,
                           evolution=evolution, label=label, periode=periode,
                           d1=d1, d2=d2)

@app.route('/rapports/stock')
@login_required
def rapports_stock():
    kpi = {
        'valeur_totale': query("SELECT COALESCE(SUM(prix_vente),0) c FROM vehicules WHERE statut='disponible'", one=True)['c'],
        'valeur_achat': query("SELECT COALESCE(SUM(prix_achat),0) c FROM vehicules WHERE statut='disponible'", one=True)['c'],
        'nb_total': query("SELECT COUNT(*) c FROM vehicules WHERE statut='disponible'", one=True)['c'],
        'nb_location': query("SELECT COUNT(*) c FROM vehicules WHERE statut='disponible' AND disponible_location=1", one=True)['c'],
        'marge_latente': query("SELECT COALESCE(SUM(prix_vente-prix_achat),0) c FROM vehicules WHERE statut='disponible'", one=True)['c'],
    }
    kpi['marge_pct'] = round(100 * kpi['marge_latente'] / kpi['valeur_achat'], 1) if kpi['valeur_achat'] else 0

    par_agence = query("""
        SELECT a.nom AS agence, a.ville, COUNT(v.id) nb,
               COALESCE(SUM(v.prix_achat),0) valeur_achat,
               COALESCE(SUM(v.prix_vente),0) valeur_vente,
               COALESCE(SUM(v.prix_vente-v.prix_achat),0) marge
        FROM agences a
        LEFT JOIN vehicules v ON v.agence_id=a.id AND v.statut='disponible'
        GROUP BY a.id ORDER BY valeur_vente DESC
    """)

    par_marque = query("""
        SELECT m.nom AS marque, COUNT(v.id) nb,
               COALESCE(SUM(v.prix_achat),0) valeur_achat,
               COALESCE(SUM(v.prix_vente),0) valeur_vente
        FROM marques m
        LEFT JOIN vehicules v ON v.marque_id=m.id AND v.statut='disponible'
        GROUP BY m.id HAVING nb > 0 ORDER BY valeur_vente DESC
    """)

    par_etat = query("""
        SELECT etat, COUNT(*) nb, COALESCE(SUM(prix_vente),0) valeur
        FROM vehicules WHERE statut='disponible'
        GROUP BY etat ORDER BY valeur DESC
    """)

    par_annee = query("""
        SELECT annee, COUNT(*) nb, COALESCE(SUM(prix_vente),0) valeur
        FROM vehicules WHERE statut='disponible' AND annee > 0
        GROUP BY annee ORDER BY annee DESC
    """)

    depreciation = query("""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom,
               (strftime('%Y','now') - v.annee) AS age
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        WHERE v.statut='disponible' AND v.annee > 0
          AND (strftime('%Y','now') - v.annee) >= 5
        ORDER BY age DESC LIMIT 30
    """)

    immo = query("""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom,
               CAST(julianday('now') - julianday(v.date_acquisition) AS INTEGER) AS jours
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        WHERE v.statut='disponible' AND v.date_acquisition IS NOT NULL
          AND julianday('now') - julianday(v.date_acquisition) > 90
        ORDER BY jours DESC LIMIT 30
    """)

    return render_template('rapports/stock.html',
                           kpi=kpi, par_agence=par_agence, par_marque=par_marque,
                           par_etat=par_etat, par_annee=par_annee,
                           depreciation=depreciation, immo=immo)

@app.route('/rapports/clients')
@login_required
def rapports_clients():
    kpi = {
        'total': query("SELECT COUNT(*) c FROM clients", one=True)['c'],
        'actifs': query("SELECT COUNT(*) c FROM clients WHERE statut='actif'", one=True)['c'],
        'acheteurs': query("SELECT COUNT(*) c FROM clients WHERE nb_achats > 0", one=True)['c'],
        'locataires': query("SELECT COUNT(*) c FROM clients WHERE nb_locations > 0", one=True)['c'],
        'score_moyen': query("SELECT COALESCE(AVG(score),0) c FROM clients", one=True)['c'],
        'ca_total': query("SELECT COALESCE(SUM(total_depense),0) c FROM clients", one=True)['c'],
    }
    kpi['score_moyen'] = round(kpi['score_moyen'], 1)

    top_clients = query("""
        SELECT * FROM clients WHERE total_depense > 0
        ORDER BY total_depense DESC LIMIT 20
    """)

    par_ville = query("""
        SELECT COALESCE(ville,'Non renseigné') AS ville,
               COUNT(*) nb, COALESCE(SUM(total_depense),0) ca
        FROM clients GROUP BY ville ORDER BY ca DESC
    """)

    par_type = query("""
        SELECT type, COUNT(*) nb, COALESCE(SUM(total_depense),0) ca
        FROM clients GROUP BY type ORDER BY ca DESC
    """)

    par_score = query("""
        SELECT
            CASE
                WHEN score >= 80 THEN '80-100 (Excellent)'
                WHEN score >= 60 THEN '60-79 (Bon)'
                WHEN score >= 40 THEN '40-59 (Moyen)'
                ELSE '0-39 (Risque)'
            END AS tranche,
            COUNT(*) nb
        FROM clients GROUP BY tranche ORDER BY tranche DESC
    """)

    return render_template('rapports/clients.html',
                           kpi=kpi, top_clients=top_clients,
                           par_ville=par_ville, par_type=par_type,
                           par_score=par_score)

@app.route('/rapports/paiements')
@login_required
def rapports_paiements():
    d1, d2, label, periode = parse_periode()
    kpi = {
        'total': query("""
            SELECT COALESCE(SUM(montant),0) c FROM paiements
            WHERE date(date_paiement) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
        'nb': query("""
            SELECT COUNT(*) c FROM paiements
            WHERE date(date_paiement) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
        'ventes': query("""
            SELECT COALESCE(SUM(montant),0) c FROM paiements
            WHERE type='vente' AND date(date_paiement) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
        'locations': query("""
            SELECT COALESCE(SUM(montant),0) c FROM paiements
            WHERE type LIKE 'location%' AND date(date_paiement) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
    }

    par_mode = query("""
        SELECT mode, COUNT(*) nb, COALESCE(SUM(montant),0) total
        FROM paiements
        WHERE date(date_paiement) BETWEEN ? AND ?
        GROUP BY mode ORDER BY total DESC
    """, (d1, d2))

    par_type = query("""
        SELECT type, COUNT(*) nb, COALESCE(SUM(montant),0) total
        FROM paiements
        WHERE date(date_paiement) BETWEEN ? AND ?
        GROUP BY type ORDER BY total DESC
    """, (d1, d2))

    evolution = query("""
        SELECT date(date_paiement) jour, COUNT(*) nb,
               COALESCE(SUM(montant),0) total
        FROM paiements
        WHERE date(date_paiement) BETWEEN ? AND ?
        GROUP BY jour ORDER BY jour
    """, (d1, d2))

    return render_template('rapports/paiements.html',
                           kpi=kpi, par_mode=par_mode, par_type=par_type,
                           evolution=evolution, label=label, periode=periode,
                           d1=d1, d2=d2)

@app.route('/rapports/marges')
@login_required
def rapports_marges():
    d1, d2, label, periode = parse_periode()
    kpi = {
        'ca': query("""
            SELECT COALESCE(SUM(montant_ttc),0) c FROM ventes
            WHERE statut='livree' AND date(date_vente) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
        'cout': query("""
            SELECT COALESCE(SUM(prix_achat),0) c FROM ventes
            WHERE statut='livree' AND date(date_vente) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
        'marge': query("""
            SELECT COALESCE(SUM(marge),0) c FROM ventes
            WHERE statut='livree' AND date(date_vente) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
        'remises': query("""
            SELECT COALESCE(SUM(remise),0) c FROM ventes
            WHERE statut='livree' AND date(date_vente) BETWEEN ? AND ?
        """, (d1, d2), one=True)['c'],
    }
    kpi['taux'] = round(100 * kpi['marge'] / kpi['ca'], 1) if kpi['ca'] else 0

    top_ventes = query("""
        SELECT v.id, v.numero, v.date_vente, v.montant_ttc, v.prix_achat, v.marge, v.remise,
               m.nom AS marque_nom, mo.nom AS modele_nom,
               veh.code AS veh_code, veh.immatriculation,
               c.nom AS client_nom, c.prenom AS client_prenom
        FROM ventes v
        JOIN vehicules veh ON veh.id=v.vehicule_id
        JOIN marques m ON m.id=veh.marque_id
        JOIN modeles mo ON mo.id=veh.modele_id
        LEFT JOIN clients c ON c.id=v.client_id
        WHERE v.statut='livree' AND date(v.date_vente) BETWEEN ? AND ?
        ORDER BY v.marge DESC LIMIT 20
    """, (d1, d2))

    top_marges_neg = query("""
        SELECT v.id, v.numero, v.date_vente, v.montant_ttc, v.prix_achat, v.marge,
               m.nom AS marque_nom, mo.nom AS modele_nom, veh.code AS veh_code
        FROM ventes v
        JOIN vehicules veh ON veh.id=v.vehicule_id
        JOIN marques m ON m.id=veh.marque_id
        JOIN modeles mo ON mo.id=veh.modele_id
        WHERE v.statut='livree' AND date(v.date_vente) BETWEEN ? AND ? AND v.marge < 0
        ORDER BY v.marge ASC LIMIT 10
    """, (d1, d2))

    par_marque = query("""
        SELECT m.nom AS marque, COUNT(v.id) nb,
               COALESCE(SUM(v.montant_ttc),0) ca,
               COALESCE(SUM(v.marge),0) marge,
               ROUND(AVG(v.marge),0) marge_moy
        FROM ventes v
        JOIN vehicules veh ON veh.id=v.vehicule_id
        JOIN marques m ON m.id=veh.marque_id
        WHERE v.statut='livree' AND date(v.date_vente) BETWEEN ? AND ?
        GROUP BY m.id ORDER BY marge DESC
    """, (d1, d2))

    return render_template('rapports/marges.html',
                           kpi=kpi, top_ventes=top_ventes, top_marges_neg=top_marges_neg,
                           par_marque=par_marque, label=label, periode=periode,
                           d1=d1, d2=d2)

@app.route('/rapports/depreciation')
@login_required
def rapports_depreciation():
    vehicules = query("""
        SELECT v.*, m.nom AS marque_nom, mo.nom AS modele_nom,
               a.nom AS agence_nom,
               COALESCE(strftime('%Y','now') - v.annee, 0) AS age,
               CAST(julianday('now') - julianday(COALESCE(v.date_acquisition, v.created_at)) AS INTEGER) AS jours_stock
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        LEFT JOIN agences a ON a.id=v.agence_id
        WHERE v.statut='disponible'
        ORDER BY age DESC, jours_stock DESC
    """)

    total_valeur = sum((v['prix_vente'] or 0) for v in vehicules)
    total_valeur_corrigee = 0
    enriched = []
    for v in vehicules:
        age = v['age'] or 0
        depr_pct = min(60, age * 6)
        valeur_corrigee = (v['prix_vente'] or 0) * (1 - depr_pct / 100)
        total_valeur_corrigee += valeur_corrigee
        enriched.append({
            'v': v,
            'age': age,
            'jours_stock': v['jours_stock'] or 0,
            'depr_pct': depr_pct,
            'valeur_corrigee': valeur_corrigee,
            'perte': (v['prix_vente'] or 0) - valeur_corrigee,
        })

    perte_totale = total_valeur - total_valeur_corrigee

    kpi = {
        'total_valeur': total_valeur,
        'valeur_corrigee': total_valeur_corrigee,
        'perte_totale': perte_totale,
        'taux_depr': round(100 * perte_totale / total_valeur, 1) if total_valeur else 0,
        'nb_total': len(vehicules),
        'nb_plus_5ans': sum(1 for v in vehicules if (v['age'] or 0) >= 5),
        'nb_immo_90j': sum(1 for v in vehicules if (v['jours_stock'] or 0) > 90),
    }

    return render_template('rapports/depreciation.html',
                           kpi=kpi, vehicules=enriched)

# ─── EXPORTS CSV ───
@app.route('/export/vehicules.csv')
@login_required
def export_vehicules():
    rows = query("""
        SELECT v.code, v.immatriculation, m.nom AS marque, mo.nom AS modele,
               v.annee, v.etat, v.kilometrage, v.carburant, v.transmission,
               v.couleur, v.prix_achat, v.prix_vente, v.prix_location_jour,
               v.statut, a.nom AS agence, v.date_acquisition
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        LEFT JOIN agences a ON a.id=v.agence_id
        ORDER BY v.code
    """)
    dicts = [dict(r) for r in rows]
    headers = ['code', 'immatriculation', 'marque', 'modele', 'annee', 'etat',
               'kilometrage', 'carburant', 'transmission', 'couleur',
               'prix_achat', 'prix_vente', 'prix_location_jour', 'statut',
               'agence', 'date_acquisition']
    return csv_response(dicts, headers,
                        f"vehicules_{datetime.now().strftime('%Y%m%d')}.csv")

@app.route('/export/clients.csv')
@login_required
def export_clients():
    rows = query("""
        SELECT code, nom, prenom, type, telephone, whatsapp, email,
               ville, pays, piece_identite, permis_conduire,
               score, nb_achats, nb_locations, total_depense, statut, created_at
        FROM clients ORDER BY code
    """)
    dicts = [dict(r) for r in rows]
    headers = ['code', 'nom', 'prenom', 'type', 'telephone', 'whatsapp', 'email',
               'ville', 'pays', 'piece_identite', 'permis_conduire',
               'score', 'nb_achats', 'nb_locations', 'total_depense', 'statut', 'created_at']
    return csv_response(dicts, headers,
                        f"clients_{datetime.now().strftime('%Y%m%d')}.csv")

@app.route('/export/ventes.csv')
@login_required
def export_ventes():
    d1, d2, label, periode = parse_periode()
    rows = query("""
        SELECT v.numero, v.date_vente, v.statut,
               veh.code AS vehicule, veh.immatriculation,
               m.nom AS marque, mo.nom AS modele,
               c.nom AS client_nom, c.prenom AS client_prenom, c.telephone AS client_tel,
               v.prix_vente, v.remise, v.montant_ttc, v.acompte, v.reste_a_payer,
               v.marge, v.mode_paiement, v.type_vente
        FROM ventes v
        LEFT JOIN vehicules veh ON veh.id=v.vehicule_id
        LEFT JOIN marques m ON m.id=veh.marque_id
        LEFT JOIN modeles mo ON mo.id=veh.modele_id
        LEFT JOIN clients c ON c.id=v.client_id
        WHERE date(v.date_vente) BETWEEN ? AND ?
        ORDER BY v.date_vente DESC
    """, (d1, d2))
    dicts = [dict(r) for r in rows]
    headers = ['numero', 'date_vente', 'statut', 'vehicule', 'immatriculation',
               'marque', 'modele', 'client_nom', 'client_prenom', 'client_tel',
               'prix_vente', 'remise', 'montant_ttc', 'acompte', 'reste_a_payer',
               'marge', 'mode_paiement', 'type_vente']
    return csv_response(dicts, headers, f"ventes_{d1}_{d2}.csv")

@app.route('/export/locations.csv')
@login_required
def export_locations():
    d1, d2, label, periode = parse_periode()
    rows = query("""
        SELECT l.numero, l.date_debut, l.date_fin_prevue, l.date_retour_reelle,
               l.statut, l.duree_jours, l.km_depart, l.km_retour, l.km_parcourus,
               veh.code AS vehicule, veh.immatriculation,
               m.nom AS marque, mo.nom AS modele,
               c.nom AS client_nom, c.prenom AS client_prenom, c.telephone AS client_tel,
               l.tarif_journalier, l.montant_ht, l.caution,
               l.frais_supplementaires, l.montant_total
        FROM locations l
        LEFT JOIN vehicules veh ON veh.id=l.vehicule_id
        LEFT JOIN marques m ON m.id=veh.marque_id
        LEFT JOIN modeles mo ON mo.id=veh.modele_id
        LEFT JOIN clients c ON c.id=l.client_id
        WHERE date(l.date_debut) BETWEEN ? AND ?
        ORDER BY l.date_debut DESC
    """, (d1, d2))
    dicts = [dict(r) for r in rows]
    headers = ['numero', 'date_debut', 'date_fin_prevue', 'date_retour_reelle',
               'statut', 'duree_jours', 'km_depart', 'km_retour', 'km_parcourus',
               'vehicule', 'immatriculation', 'marque', 'modele',
               'client_nom', 'client_prenom', 'client_tel',
               'tarif_journalier', 'montant_ht', 'caution',
               'frais_supplementaires', 'montant_total']
    return csv_response(dicts, headers, f"locations_{d1}_{d2}.csv")

@app.route('/export/paiements.csv')
@login_required
def export_paiements():
    d1, d2, label, periode = parse_periode()
    rows = query("""
        SELECT p.date_paiement, p.type, p.montant, p.mode, p.operateur,
               p.reference_transaction, p.statut,
               c.code AS client_code, c.nom AS client_nom, c.prenom AS client_prenom,
               c.telephone AS client_tel
        FROM paiements p
        LEFT JOIN clients c ON c.id=p.client_id
        WHERE date(p.date_paiement) BETWEEN ? AND ?
        ORDER BY p.date_paiement DESC
    """, (d1, d2))
    dicts = [dict(r) for r in rows]
    headers = ['date_paiement', 'type', 'montant', 'mode', 'operateur',
               'reference_transaction', 'statut',
               'client_code', 'client_nom', 'client_prenom', 'client_tel']
    return csv_response(dicts, headers, f"paiements_{d1}_{d2}.csv")

@app.route('/export/stock.csv')
@login_required
def export_stock():
    rows = query("""
        SELECT v.code, v.immatriculation, v.vin_chassis, m.nom AS marque,
               mo.nom AS modele, v.annee, v.etat, v.kilometrage,
               v.couleur, v.carburant, v.transmission,
               v.prix_achat, v.prix_vente,
               (v.prix_vente - v.prix_achat) AS marge_potentielle,
               a.nom AS agence, v.date_acquisition,
               CAST(julianday('now') - julianday(COALESCE(v.date_acquisition, v.created_at)) AS INTEGER) AS jours_stock
        FROM vehicules v
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        LEFT JOIN agences a ON a.id=v.agence_id
        WHERE v.statut='disponible'
        ORDER BY jours_stock DESC
    """)
    dicts = [dict(r) for r in rows]
    headers = ['code', 'immatriculation', 'vin_chassis', 'marque', 'modele',
               'annee', 'etat', 'kilometrage', 'couleur', 'carburant', 'transmission',
               'prix_achat', 'prix_vente', 'marge_potentielle',
               'agence', 'date_acquisition', 'jours_stock']
    return csv_response(dicts, headers, f"stock_{datetime.now().strftime('%Y%m%d')}.csv")

@app.route('/export/entretiens.csv')
@login_required
def export_entretiens():
    rows = query("""
        SELECT e.date_entretien, e.type, e.description, e.kilometrage, e.cout,
               e.garage, e.prochain_km,
               v.code AS vehicule, v.immatriculation,
               m.nom AS marque, mo.nom AS modele
        FROM entretiens e
        LEFT JOIN vehicules v ON v.id=e.vehicule_id
        LEFT JOIN marques m ON m.id=v.marque_id
        LEFT JOIN modeles mo ON mo.id=v.modele_id
        ORDER BY e.date_entretien DESC
    """)
    dicts = [dict(r) for r in rows]
    headers = ['date_entretien', 'type', 'description', 'kilometrage', 'cout',
               'garage', 'prochain_km', 'vehicule', 'immatriculation', 'marque', 'modele']
    return csv_response(dicts, headers,
                        f"entretiens_{datetime.now().strftime('%Y%m%d')}.csv")

# ─── AUDIT ───
@app.route('/audit')
@login_required
@admin_required
def audit_list():
    action = request.args.get('action', '').strip()
    entity = request.args.get('entity', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 50

    where = " WHERE 1=1"
    params = []
    if action:
        where += " AND a.action=?"; params.append(action)
    if entity:
        where += " AND a.entity=?"; params.append(entity)

    total = query(f"SELECT COUNT(*) c FROM audit_log a {where}", params, one=True)['c']
    offset = (page - 1) * per_page
    logs = query(f"""
        SELECT a.*, u.nom_complet AS user_nom, u.username
        FROM audit_log a
        LEFT JOIN users u ON u.id=a.user_id
        {where}
        ORDER BY a.id DESC LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    actions = [r['action'] for r in query("SELECT DISTINCT action FROM audit_log ORDER BY action")]
    entities = [r['entity'] for r in query("SELECT DISTINCT entity FROM audit_log WHERE entity IS NOT NULL ORDER BY entity")]

    pages = (total + per_page - 1) // per_page
    return render_template('audit/list.html', logs=logs,
                           actions=actions, entities=entities,
                           action=action, entity=entity,
                           page=page, pages=pages, total=total)

# ─── UTILISATEURS ───
@app.route('/utilisateurs')
@login_required
@admin_required
def users_list():
    users = query("""
        SELECT u.*, (SELECT COUNT(*) FROM ventes v WHERE v.vendeur_id=u.id) nb_ventes
        FROM users u ORDER BY u.id
    """)
    return render_template('users/list.html', users=users)

@app.route('/utilisateurs/nouveau', methods=['GET', 'POST'])
@login_required
@admin_required
def user_new():
    if request.method == 'POST':
        f = request.form
        try:
            uid = execute("""
                INSERT INTO users (username, password_hash, role, nom_complet,
                    email, telephone, agence, whatsapp, actif, created_at)
                VALUES (?,?,?,?,?,?,?,?,1,?)
            """, (f.get('username'),
                  generate_password_hash(f.get('password') or 'changeme123'),
                  f.get('role') or 'commercial',
                  f.get('nom_complet'), f.get('email'),
                  f.get('telephone'), f.get('agence'),
                  f.get('whatsapp') or f.get('telephone'),
                  datetime.now().isoformat()))
            audit('create', 'user', uid)
            flash("✅ Utilisateur créé.", "success")
            return redirect(url_for('users_list'))
        except sqlite3.IntegrityError:
            flash("❌ Nom d'utilisateur déjà pris.", "error")
    return render_template('users/form.html', user=None)

@app.route('/utilisateurs/<int:uid>/editer', methods=['GET', 'POST'])
@login_required
@admin_required
def user_edit(uid):
    u = query("SELECT * FROM users WHERE id=?", (uid,), one=True)
    if not u:
        abort(404)
    if request.method == 'POST':
        f = request.form
        pw = f.get('password', '').strip()
        if pw:
            execute("""
                UPDATE users SET username=?, password_hash=?, role=?, nom_complet=?,
                    email=?, telephone=?, agence=?, whatsapp=?, actif=?
                WHERE id=?
            """, (f.get('username'), generate_password_hash(pw),
                  f.get('role'), f.get('nom_complet'), f.get('email'),
                  f.get('telephone'), f.get('agence'), f.get('whatsapp'),
                  1 if f.get('actif') else 0, uid))
        else:
            execute("""
                UPDATE users SET username=?, role=?, nom_complet=?, email=?,
                    telephone=?, agence=?, whatsapp=?, actif=?
                WHERE id=?
            """, (f.get('username'), f.get('role'), f.get('nom_complet'),
                  f.get('email'), f.get('telephone'), f.get('agence'),
                  f.get('whatsapp'), 1 if f.get('actif') else 0, uid))
        audit('update', 'user', uid)
        flash("✅ Utilisateur mis à jour.", "success")
        return redirect(url_for('users_list'))
    return render_template('users/form.html', user=u)

@app.route('/utilisateurs/<int:uid>/supprimer', methods=['POST'])
@login_required
@admin_required
def user_delete(uid):
    if uid == current_user.id:
        flash("❌ Impossible de supprimer votre propre compte.", "error")
    else:
        execute("DELETE FROM users WHERE id=?", (uid,))
        audit('delete', 'user', uid)
        flash("🗑️ Utilisateur supprimé.", "success")
    return redirect(url_for('users_list'))

@app.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    if request.method == 'POST':
        f = request.form
        pw = f.get('password', '').strip()
        if pw:
            execute("""
                UPDATE users SET password_hash=?, nom_complet=?, email=?,
                    telephone=?, whatsapp=? WHERE id=?
            """, (generate_password_hash(pw), f.get('nom_complet'),
                  f.get('email'), f.get('telephone'), f.get('whatsapp'),
                  current_user.id))
            flash("✅ Mot de passe et profil mis à jour.", "success")
        else:
            execute("""
                UPDATE users SET nom_complet=?, email=?, telephone=?, whatsapp=?
                WHERE id=?
            """, (f.get('nom_complet'), f.get('email'),
                  f.get('telephone'), f.get('whatsapp'), current_user.id))
            flash("✅ Profil mis à jour.", "success")
        return redirect(url_for('profil'))

    u = query("SELECT * FROM users WHERE id=?", (current_user.id,), one=True)
    return render_template('users/profil.html', u=u)

# ─── API STATS ───
@app.route('/api/stats/dashboard')
@login_required
def api_stats_dashboard():
    return jsonify({
        'vehicules': {
            'total': query("SELECT COUNT(*) c FROM vehicules", one=True)['c'],
            'dispo': query("SELECT COUNT(*) c FROM vehicules WHERE statut='disponible'", one=True)['c'],
            'vendus': query("SELECT COUNT(*) c FROM vehicules WHERE statut='vendu'", one=True)['c'],
        },
        'clients': query("SELECT COUNT(*) c FROM clients", one=True)['c'],
        'ventes': {
            'mois': query("""
                SELECT COUNT(*) c FROM ventes WHERE statut='livree'
                AND strftime('%Y-%m', date_vente)=strftime('%Y-%m','now')
            """, one=True)['c'],
            'ca_mois': query("""
                SELECT COALESCE(SUM(montant_ttc),0) c FROM ventes WHERE statut='livree'
                AND strftime('%Y-%m', date_vente)=strftime('%Y-%m','now')
            """, one=True)['c'],
        },
        'locations': {
            'actives': query("SELECT COUNT(*) c FROM locations WHERE statut IN ('reservee','en_cours')", one=True)['c'],
        },
        'alertes_papiers': query("""
            SELECT COUNT(*) c FROM papiers WHERE statut IN ('critique','expire')
        """, one=True)['c'],
    })

@app.route('/api/stats/ventes-7j')
@login_required
def api_stats_ventes_7j():
    rows = query("""
        SELECT date(date_vente) jour, COUNT(*) nb, COALESCE(SUM(montant_ttc),0) ca
        FROM ventes
        WHERE statut='livree' AND date(date_vente) >= date('now','-7 days')
        GROUP BY jour ORDER BY jour
    """)
    return jsonify([dict(r) for r in rows])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)

