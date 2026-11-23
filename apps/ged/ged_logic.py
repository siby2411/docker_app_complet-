"""
Omega GED — Logique métier
Upload sécurisé · Workflow · Recherche full-text · Audit RGPD · Cycle de vie
Compatible Python 3.10 (aucun backslash dans f-string)
"""
from flask import Blueprint, request, redirect, url_for, flash, jsonify, send_file, Response
from flask_login import current_user
import sqlite3
import os
import uuid
import hashlib
import mimetypes
import shutil
import csv
import io
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

ged_bp = Blueprint('ged', __name__)
_deps = {}


def init_ged(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(ged_bp)
    print("[GED] ✅ Module GED Logic enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='dashboard', title='Omega GED'):
    return _deps['render_page'](content, active=active, page_title=title)


def _fmt(ko):
    return _deps['format_taille'](ko)


def _log(action, details=''):
    """Wrapper compatible avec log_action(user_id, action, details)"""
    try:
        user_id = None
        try:
            from flask_login import current_user
            if current_user and current_user.is_authenticated:
                user_id = current_user.id
        except Exception:
            pass
        _deps['log_action'](user_id, action, details)
    except Exception as e:
        print(f"[LOG GED] {e}")


def _auth_required(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if not (current_user and current_user.is_authenticated):
            return redirect('/login')
        return f(*a, **k)
    return w


def _can_write():
    return current_user and current_user.role in ('admin', 'archiviste', 'contributeur')


def _can_validate():
    return current_user and current_user.role in ('admin', 'archiviste')


def _is_admin():
    return current_user and current_user.role == 'admin'


# ================================================================
# HELPERS
# ================================================================
ALLOWED_EXT = {
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods',
    'txt', 'csv', 'rtf', 'md',
    'jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp',
    'zip', 'rar', '7z', 'tar', 'gz',
    'dwg', 'dxf', 'shp', 'kml',
    'mp3', 'mp4', 'wav', 'avi', 'mov'
}


def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def _safe_name(orig):
    base = secure_filename(orig) or 'fichier'
    return base


def _next_reference(conn, prefix='DOC'):
    year = datetime.now().year
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM documents WHERE reference LIKE ?", (f"{prefix}-{year}-%",))
    n = (c.fetchone()[0] or 0) + 1
    return f"{prefix}-{year}-{n:04d}"


# ================================================================
# UPLOAD
# ================================================================
@ged_bp.route('/upload', methods=['GET', 'POST'])
@_auth_required
def upload():
    if not _can_write():
        flash("Droits insuffisants pour uploader", "danger")
        return redirect('/documents')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        titre = (request.form.get('titre') or '').strip()
        description = (request.form.get('description') or '').strip()
        cat_id = request.form.get('categorie_id') or None
        type_document_id = request.form.get('type_document_id') or None
        dossier_id = request.form.get('dossier_id') or None
        confidentiel = 1 if request.form.get('confidentiel') else 0
        date_destruction = request.form.get('date_destruction_prevue') or None
        tags_raw = (request.form.get('tags') or '').strip()

        fichiers = request.files.getlist('fichiers')
        fichiers = [f for f in fichiers if f and f.filename]

        if not titre and not fichiers:
            flash("Titre ou au moins un fichier requis", "warning")
        elif not fichiers:
            flash("Aucun fichier sélectionné", "warning")
        else:
            upload_dir = _deps.get('UPLOAD_FOLDER', '/app/data/documents')
            os.makedirs(upload_dir, exist_ok=True)
            created = []
            for fichier in fichiers:
                orig_name = fichier.filename
                if not _allowed(orig_name):
                    flash(f"Extension refusée : {orig_name}", "warning")
                    continue
                safe = _safe_name(orig_name)
                ext = safe.rsplit('.', 1)[1].lower() if '.' in safe else ''
                uid = uuid.uuid4().hex[:12]
                storage_name = f"{uid}_{safe}"
                storage_path = os.path.join(upload_dir, storage_name)
                fichier.save(storage_path)
                taille_ko = os.path.getsize(storage_path) / 1024
                sha256 = _sha256(storage_path)

                ref = _next_reference(conn)
                titre_final = titre if titre else os.path.splitext(orig_name)[0]

                try:
                    c.execute("""INSERT INTO documents
                        (reference, titre, description, categorie_id, type_document_id, dossier_id,
                         auteur_id, fichier_nom, fichier_chemin, fichier_taille_ko, extension,
                         sha256, confidentiel, statut, version_actuelle, date_upload,
                         date_destruction_prevue, actif, created_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)""",
                        (ref, titre_final, description, cat_id, type_document_id, dossier_id,
                         current_user.id, orig_name, storage_path, taille_ko, ext,
                         sha256, confidentiel, 'Brouillon', 1,
                         datetime.now().isoformat(), date_destruction,
                         datetime.now().isoformat()))
                    doc_id = c.lastrowid

                    # Version initiale
                    c.execute("""INSERT INTO document_versions
                        (document_id, numero_version, fichier_nom, fichier_chemin, fichier_taille_ko,
                         sha256, commentaire, auteur_id, created_at)
                        VALUES (?,?,?,?,?,?,?,?,?)""",
                        (doc_id, 1, orig_name, storage_path, taille_ko,
                         sha256, 'Version initiale', current_user.id, datetime.now().isoformat()))

                    # Tags
                    if tags_raw:
                        for tag_nom in [t.strip() for t in tags_raw.split(',') if t.strip()]:
                            c.execute("SELECT id FROM tags WHERE nom=?", (tag_nom,))
                            row = c.fetchone()
                            if row:
                                tag_id = row['id']
                            else:
                                c.execute("INSERT INTO tags (nom, couleur) VALUES (?,?)",
                                          (tag_nom, '#06b6d4'))
                                tag_id = c.lastrowid
                            try:
                                c.execute("INSERT INTO document_tags (document_id, tag_id) VALUES (?,?)",
                                          (doc_id, tag_id))
                            except Exception:
                                pass

                    conn.commit()
                    created.append(ref)
                    _log('UPLOAD_DOCUMENT', f"doc={doc_id} ref={ref} fichier={orig_name}")

                except Exception as e:
                    conn.rollback()
                    flash(f"Erreur upload {orig_name} : {e}", "danger")

            if created:
                flash(f"{len(created)} document(s) uploadé(s) : {', '.join(created)}", "success")
                conn.close()
                return redirect('/documents')

    cats = _list_categories(conn)
    types = _list_types(conn)
    c.execute("SELECT id, nom FROM dossiers WHERE actif=1 ORDER BY nom")
    dossiers = c.fetchall()
    conn.close()

    opt_cat = '<option value="">—</option>' + ''.join(
        f'<option value="{x["id"]}">{x["nom"]}</option>' for x in cats)
    opt_type = '<option value="">—</option>' + ''.join(
        f'<option value="{x["id"]}">{x["nom"]}</option>' for x in types)
    opt_dos = '<option value="">—</option>' + ''.join(
        f'<option value="{x["id"]}">{x["nom"]}</option>' for x in dossiers)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-upload"></i> Upload de documents</h2>
        <div class="page-subtitle">Taille max : 100 Mo par fichier · Extensions autorisées : PDF, DOCX, XLSX, JPG, DWG...</div></div>
      <a href="/documents" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>

    <div class="card">
      <form method="POST" enctype="multipart/form-data">
        <div class="form-grid">
          <div class="form-group form-full">
            <label>Fichiers * <small>(plusieurs possibles)</small></label>
            <input type="file" name="fichiers" multiple required
                   style="padding:15px;background:#f0fdff;border:2px dashed #06b6d4;border-radius:12px;width:100%">
          </div>
          <div class="form-group form-full">
            <label>Titre <small>(si vide = nom du fichier)</small></label>
            <input type="text" name="titre" placeholder="Ex : Contrat de prestation 2026">
          </div>
          <div class="form-group"><label>Catégorie</label><select name="categorie_id">{opt_cat}</select></div>
          <div class="form-group"><label>Type</label><select name="type_document_id">{opt_type}</select></div>
          <div class="form-group"><label>Dossier</label><select name="dossier_id">{opt_dos}</select></div>
          <div class="form-group">
            <label>Date destruction prévue</label>
            <input type="date" name="date_destruction_prevue">
          </div>
          <div class="form-group form-full">
            <label>Tags <small>(séparés par virgules)</small></label>
            <input type="text" name="tags" placeholder="urgent, 2026, contrat">
          </div>
          <div class="form-group form-full">
            <label>Description</label>
            <textarea name="description" rows="3"></textarea>
          </div>
          <div class="form-group form-full">
            <label><input type="checkbox" name="confidentiel"> Marquer comme confidentiel 🔒</label>
          </div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-cloud-upload-alt"></i> Uploader</button>
          <a href="/documents" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>
    """
    return _render(content, active='upload', title='Upload')


def _list_categories(conn):
    c = conn.cursor()
    c.execute("SELECT * FROM categories WHERE actif=1 ORDER BY nom")
    return c.fetchall()


def _list_types(conn):
    c = conn.cursor()
    c.execute("SELECT * FROM types_documents WHERE actif=1 ORDER BY nom")
    return c.fetchall()


# ================================================================
# WORKFLOW — validation
# ================================================================
@ged_bp.route('/workflow')
@_auth_required
def workflow():
    if not _can_validate():
        flash("Accès réservé archivistes/admin", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT d.*, cat.nom AS cat_nom, cat.couleur AS cat_couleur,
                        u.nom AS auteur_nom, u.prenom AS auteur_prenom
                 FROM documents d
                 LEFT JOIN categories cat ON d.categorie_id=cat.id
                 LEFT JOIN utilisateurs u ON d.auteur_id=u.id
                 WHERE d.actif=1 AND d.statut IN ('En validation','Brouillon')
                 ORDER BY d.date_upload DESC""")
    docs = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-check-double"></i> Validations en attente</h2>
        <div class="page-subtitle">{len(docs)} document(s) à valider</div></div>
    </div>
    <div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Réf</th><th>Titre</th><th>Auteur</th><th>Catégorie</th>
                 <th>Date</th><th>Statut</th><th>Actions</th></tr></thead><tbody>
    """
    for d in docs:
        content += f"""
        <tr>
          <td><strong>{d['reference']}</strong></td>
          <td>{d['titre'][:50]}</td>
          <td>{d['auteur_prenom'] or ''} {d['auteur_nom'] or ''}</td>
          <td>{d['cat_nom'] or '-'}</td>
          <td><small>{d['date_upload'][:10] if d['date_upload'] else '-'}</small></td>
          <td><span class="badge badge-warning">{d['statut']}</span></td>
          <td style="white-space:nowrap">
            <a href="/documents/{d['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
            <a href="/workflow/{d['id']}/publier" class="btn btn-success btn-sm"
               onclick="return confirm(&#39;Publier ce document ?&#39;)"><i class="fas fa-check"></i> Publier</a>
            <a href="/workflow/{d['id']}/rejeter" class="btn btn-danger btn-sm"
               onclick="return confirm(&#39;Rejeter ce document ?&#39;)"><i class="fas fa-xmark"></i> Rejeter</a>
          </td>
        </tr>"""
    if not docs:
        content += '<tr><td colspan="7" class="empty"><i class="fas fa-check-double"></i><br>Aucun document en attente</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='workflow', title='Workflow')


@ged_bp.route('/documents/<int:did>/soumettre')
@_auth_required
def documents_soumettre(did):
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/documents')
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM documents WHERE id=? AND actif=1", (did,))
    doc = c.fetchone()
    if not doc:
        conn.close()
        flash("Document introuvable", "danger")
        return redirect('/documents')
    c.execute("UPDATE documents SET statut='En validation', updated_at=? WHERE id=?",
              (datetime.now().isoformat(), did))
    conn.commit()
    _log('WORKFLOW_SOUMETTRE', f"doc={did} soumis à validation")
    conn.close()
    flash("Document soumis à validation", "success")
    return redirect(f'/documents/{did}')


@ged_bp.route('/workflow/<int:did>/publier', methods=['GET', 'POST'])
@_auth_required
def workflow_publier(did):
    if not _can_validate():
        flash("Accès réservé archivistes/admin", "danger")
        return redirect('/')
    conn = _db()
    c = conn.cursor()
    if request.method == 'POST':
        commentaire = (request.form.get('commentaire') or '').strip()
        c.execute("""UPDATE documents SET statut='Publié', date_publication=?,
                     valideur_id=?, updated_at=? WHERE id=?""",
                  (datetime.now().isoformat(), current_user.id,
                   datetime.now().isoformat(), did))
        conn.commit()
        _log('WORKFLOW_PUBLIER', f"doc={did} publié — {commentaire}")
        conn.close()
        flash("Document publié", "success")
        return redirect('/workflow')

    c.execute("SELECT * FROM documents WHERE id=?", (did,))
    doc = c.fetchone()
    conn.close()
    if not doc:
        flash("Document introuvable", "danger")
        return redirect('/workflow')

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-check"></i> Publier le document</h2></div>
      <a href="/workflow" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <div style="padding:15px;background:#f0fdff;border-radius:12px;margin-bottom:20px">
        <strong>{doc['reference']}</strong> — {doc['titre']}
      </div>
      <form method="POST">
        <div class="form-group">
          <label>Commentaire de validation (optionnel)</label>
          <textarea name="commentaire" rows="3"></textarea>
        </div>
        <div style="display:flex;gap:10px">
          <button class="btn btn-success"><i class="fas fa-check"></i> Confirmer publication</button>
          <a href="/workflow" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='workflow', title='Publier')


@ged_bp.route('/workflow/<int:did>/rejeter', methods=['GET', 'POST'])
@_auth_required
def workflow_rejeter(did):
    if not _can_validate():
        flash("Accès réservé archivistes/admin", "danger")
        return redirect('/')
    conn = _db()
    c = conn.cursor()
    if request.method == 'POST':
        motif = (request.form.get('motif') or '').strip()
        if not motif:
            flash("Motif obligatoire", "warning")
        else:
            c.execute("""UPDATE documents SET statut='Brouillon', updated_at=? WHERE id=?""",
                      (datetime.now().isoformat(), did))
            conn.commit()
            _log('WORKFLOW_REJETER', f"doc={did} rejeté — motif: {motif}")
            conn.close()
            flash("Document rejeté", "success")
            return redirect('/workflow')

    c.execute("SELECT * FROM documents WHERE id=?", (did,))
    doc = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-xmark"></i> Rejeter le document</h2></div>
      <a href="/workflow" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <div style="padding:15px;background:#fee2e2;border-radius:12px;margin-bottom:20px">
        <strong>{doc['reference']}</strong> — {doc['titre']}
      </div>
      <form method="POST">
        <div class="form-group">
          <label>Motif du rejet *</label>
          <textarea name="motif" rows="3" required></textarea>
        </div>
        <div style="display:flex;gap:10px">
          <button class="btn btn-danger"><i class="fas fa-xmark"></i> Confirmer rejet</button>
          <a href="/workflow" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='workflow', title='Rejeter')


# ================================================================
# RECHERCHE FULL-TEXT
# ================================================================
@ged_bp.route('/recherche')
@_auth_required
def recherche():
    q = (request.args.get('q') or '').strip()
    results = []
    conn = _db()
    if q:
        c = conn.cursor()
        like = f"%{q}%"
        c.execute("""SELECT DISTINCT d.*, cat.nom AS cat_nom, cat.couleur AS cat_couleur,
                            u.nom AS auteur_nom, u.prenom AS auteur_prenom,
                            dos.nom AS dossier_nom
                     FROM documents d
                     LEFT JOIN categories cat ON d.categorie_id=cat.id
                     LEFT JOIN utilisateurs u ON d.auteur_id=u.id
                     LEFT JOIN dossiers dos ON d.dossier_id=dos.id
                     LEFT JOIN document_tags dt ON dt.document_id=d.id
                     LEFT JOIN tags t ON t.id=dt.tag_id
                     WHERE d.actif=1 AND (
                        d.titre LIKE ? OR d.reference LIKE ? OR d.description LIKE ?
                        OR d.fichier_nom LIKE ? OR d.sha256 LIKE ?
                        OR t.nom LIKE ? OR cat.nom LIKE ? OR dos.nom LIKE ?
                     )
                     ORDER BY d.date_upload DESC LIMIT 100""",
                  (like, like, like, like, like, like, like, like))
        results = c.fetchall()
        _log('RECHERCHE', f"q='{q}' → {len(results)} résultat(s)")
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-search"></i> Recherche documentaire</h2>
        <div class="page-subtitle">Recherche full-text sur titre, description, référence, tags, catégorie</div></div>
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px">
        <input type="text" name="q" value="{q}" placeholder="Rechercher un document..."
               style="flex:1;padding:14px 18px;border:2px solid #f1f5f9;border-radius:11px;font-size:1rem;background:#f8fafc">
        <button class="btn btn-primary" style="padding:14px 28px">
          <i class="fas fa-search"></i> Rechercher
        </button>
      </form>
    </div>
    """

    if q:
        content += f"""
        <div class="card">
          <div class="card-header">
            <h3><i class="fas fa-list"></i> {len(results)} résultat(s) pour « {q} »</h3>
          </div>
          <div class="table-wrap"><table>
            <thead><tr><th>Réf</th><th>Titre</th><th>Dossier</th><th>Catégorie</th>
                       <th>Auteur</th><th>Date</th><th></th></tr></thead><tbody>
        """
        for d in results:
            content += f"""
            <tr>
              <td><strong>{d['reference']}</strong></td>
              <td>{d['titre'][:60]}</td>
              <td><small>{d['dossier_nom'] or '-'}</small></td>
              <td><span class="badge" style="background:{d['cat_couleur'] or '#06b6d4'}20;color:{d['cat_couleur'] or '#0e7490'}">{d['cat_nom'] or '-'}</span></td>
              <td><small>{d['auteur_prenom'] or ''} {d['auteur_nom'] or ''}</small></td>
              <td><small>{d['date_upload'][:10] if d['date_upload'] else '-'}</small></td>
              <td><a href="/documents/{d['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a></td>
            </tr>"""
        if not results:
            content += '<tr><td colspan="7" class="empty"><i class="fas fa-search"></i><br>Aucun résultat</td></tr>'
        content += "</tbody></table></div></div>"
    else:
        content += """
        <div class="card">
          <div class="empty">
            <i class="fas fa-magnifying-glass"></i>
            <h3 style="color:#0e7490;margin-top:10px">Que recherchez-vous ?</h3>
            <p style="color:#64748b;margin-top:8px">Tapez un mot-clé : titre, référence, tag, catégorie, nom de fichier...</p>
          </div>
        </div>"""

    return _render(content, active='recherche', title='Recherche')


# ================================================================
# AUDIT RGPD
# ================================================================
@ged_bp.route('/audit')
@_auth_required
def audit():
    if current_user.role not in ('admin', 'auditeur'):
        flash("Accès réservé aux administrateurs et auditeurs", "danger")
        return redirect('/')

    page = int(request.args.get('page', 1))
    per_page = 50
    offset = (page - 1) * per_page
    action_filter = request.args.get('action') or ''
    user_filter = request.args.get('user') or ''

    conn = _db()
    c = conn.cursor()
    where = []
    params = []
    if action_filter:
        where.append("a.action LIKE ?")
        params.append(f"%{action_filter}%")
    if user_filter:
        where.append("(u.nom LIKE ? OR u.prenom LIKE ?)")
        params += [f"%{user_filter}%", f"%{user_filter}%"]
    where_sql = "WHERE " + " AND ".join(where) if where else ""

    c.execute(f"SELECT COUNT(*) FROM audit_log a LEFT JOIN utilisateurs u ON a.user_id=u.id {where_sql}", params)
    total = c.fetchone()[0] or 0

    c.execute(f"""SELECT a.*, u.nom AS user_nom, u.prenom AS user_prenom, u.role AS user_role
                  FROM audit_log a LEFT JOIN utilisateurs u ON a.user_id=u.id
                  {where_sql}
                  ORDER BY a.created_at DESC LIMIT ? OFFSET ?""",
              params + [per_page, offset])
    logs = c.fetchall()

    # Stats
    c.execute("SELECT COUNT(*) FROM audit_log")
    total_logs = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(DISTINCT user_id) FROM audit_log")
    total_users = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM audit_log WHERE date(created_at) = date('now')")
    logs_today = c.fetchone()[0] or 0
    conn.close()

    pages = (total + per_page - 1) // per_page

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-history"></i> Journal d&#39;audit RGPD</h2>
        <div class="page-subtitle">Traçabilité complète — Conformité RGPD & ISO 15489</div></div>
      <a href="/audit/export" class="btn btn-success"><i class="fas fa-download"></i> Export CSV</a>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-list"></i></div>
        <div class="stat-value">{total_logs}</div><div class="stat-label">Événements total</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-calendar-day"></i></div>
        <div class="stat-value">{logs_today}</div><div class="stat-label">Aujourd&#39;hui</div></div>
      <div class="stat-card purple"><div class="stat-icon"><i class="fas fa-users"></i></div>
        <div class="stat-value">{total_users}</div><div class="stat-label">Utilisateurs actifs</div></div>
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:1;margin:0;min-width:200px">
          <label>Action</label>
          <input type="text" name="action" value="{action_filter}" placeholder="UPLOAD_DOCUMENT...">
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:200px">
          <label>Utilisateur</label>
          <input type="text" name="user" value="{user_filter}" placeholder="Nom ou prénom">
        </div>
        <button class="btn btn-primary"><i class="fas fa-filter"></i> Filtrer</button>
        <a href="/audit" class="btn btn-info"><i class="fas fa-rotate"></i> Reset</a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr><th>Date</th><th>Utilisateur</th><th>Rôle</th><th>Action</th>
                   <th>Détails</th><th>IP</th></tr></thead><tbody>
    """
    for log in logs:
        content += f"""
        <tr>
          <td><small>{log['created_at'][:19] if log['created_at'] else '-'}</small></td>
          <td><strong>{log['user_prenom'] or '?'} {log['user_nom'] or ''}</strong></td>
          <td><span class="badge badge-role-{log['user_role'] or 'lecteur'}">{log['user_role'] or '-'}</span></td>
          <td><code style="font-size:0.75rem">{log['action']}</code></td>
          <td><small>{log['details'][:80] if log['details'] else ''}</small></td>
          <td><small style="font-family:monospace">{log['ip'] or '-'}</small></td>
        </tr>"""
    if not logs:
        content += '<tr><td colspan="6" class="empty"><i class="fas fa-history"></i><br>Aucun événement</td></tr>'
    content += "</tbody></table></div>"

    if pages > 1:
        content += '<div style="display:flex;gap:8px;justify-content:center;margin-top:20px">'
        if page > 1:
            content += f'<a href="?page={page-1}&action={action_filter}&user={user_filter}" class="btn btn-info btn-sm"><i class="fas fa-chevron-left"></i> Précédent</a>'
        content += f'<span style="padding:8px 16px;font-weight:700">Page {page} / {pages}</span>'
        if page < pages:
            content += f'<a href="?page={page+1}&action={action_filter}&user={user_filter}" class="btn btn-info btn-sm">Suivant <i class="fas fa-chevron-right"></i></a>'
        content += '</div>'

    content += "</div>"
    return _render(content, active='audit', title='Audit RGPD')


@ged_bp.route('/audit/export')
@_auth_required
def audit_export():
    if current_user.role not in ('admin', 'auditeur'):
        flash("Accès réservé", "danger")
        return redirect('/')
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT a.id, a.created_at, u.username, u.nom, u.prenom, u.role,
                        a.action, a.details, a.ip
                 FROM audit_log a LEFT JOIN utilisateurs u ON a.user_id=u.id
                 ORDER BY a.created_at DESC LIMIT 10000""")
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    w = csv.writer(output, delimiter=';')
    w.writerow(['ID', 'Date', 'Username', 'Nom', 'Prénom', 'Rôle', 'Action', 'Détails', 'IP'])
    for r in rows:
        w.writerow([r['id'], r['created_at'], r['username'], r['nom'], r['prenom'],
                    r['role'], r['action'], r['details'], r['ip']])
    _log('AUDIT_EXPORT', f"Export de {len(rows)} événements")
    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=audit_rgpd_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'}
    )


# ================================================================
# CYCLE DE VIE (DUA, destruction)
# ================================================================
@ged_bp.route('/cycle-vie')
@_auth_required
def cycle_vie():
    if not _can_validate():
        flash("Accès réservé archivistes/admin", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()

    # Documents à détruire (30j)
    c.execute("""SELECT d.*, cat.nom AS cat_nom, cat.duree_conservation_ans AS cat_duree
                 FROM documents d
                 LEFT JOIN categories cat ON d.categorie_id=cat.id
                 WHERE d.actif=1 AND d.date_destruction_prevue IS NOT NULL
                   AND date(d.date_destruction_prevue) <= date('now', '+30 days')
                 ORDER BY d.date_destruction_prevue ASC""")
    a_detruire = c.fetchall()

    # Documents dépassant DUA
    c.execute("""SELECT d.*, cat.nom AS cat_nom, cat.duree_conservation_ans
                 FROM documents d
                 INNER JOIN categories cat ON d.categorie_id=cat.id
                 WHERE d.actif=1 AND cat.duree_conservation_ans IS NOT NULL
                   AND date(d.date_upload, '+' || cat.duree_conservation_ans || ' years') <= date('now')""")
    dua_depasse = c.fetchall()

    # Archivés
    c.execute("SELECT COUNT(*) FROM documents WHERE actif=1 AND statut='Archivé'")
    nb_archives = c.fetchone()[0] or 0
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-recycle"></i> Cycle de vie documentaire</h2>
        <div class="page-subtitle">Politique de conservation — Conformité ISO 15489</div></div>
    </div>

    <div class="stats">
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-hourglass-half"></i></div>
        <div class="stat-value">{len(a_detruire)}</div>
        <div class="stat-label">À détruire (30j)</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-triangle-exclamation"></i></div>
        <div class="stat-value">{len(dua_depasse)}</div>
        <div class="stat-label">DUA dépassée</div></div>
      <div class="stat-card purple"><div class="stat-icon"><i class="fas fa-archive"></i></div>
        <div class="stat-value">{nb_archives}</div>
        <div class="stat-label">Documents archivés</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3 style="color:#991b1b"><i class="fas fa-fire"></i> Documents à détruire (30 jours)</h3></div>
    """
    if a_detruire:
        content += '<div class="table-wrap"><table><thead><tr><th>Réf</th><th>Titre</th><th>Catégorie</th><th>Date destruction</th><th>Action</th></tr></thead><tbody>'
        for d in a_detruire:
            content += f"""
            <tr>
              <td><strong>{d['reference']}</strong></td>
              <td>{d['titre'][:50]}</td>
              <td>{d['cat_nom'] or '-'}</td>
              <td><span class="badge badge-danger">{d['date_destruction_prevue']}</span></td>
              <td>
                <a href="/cycle-vie/{d['id']}/detruire" class="btn btn-danger btn-sm"
                   onclick="return confirm(&#39;Détruire définitivement ? Action irréversible.&#39;)">
                   <i class="fas fa-fire"></i> Détruire</a>
              </td>
            </tr>"""
        content += "</tbody></table></div>"
    else:
        content += '<div class="empty" style="padding:20px"><i class="fas fa-check-circle" style="color:#10b981"></i><br>Aucune destruction imminente</div>'
    content += "</div>"

    content += """
    <div class="card">
      <div class="card-header"><h3 style="color:#92400e"><i class="fas fa-triangle-exclamation"></i> DUA dépassée (à archiver)</h3></div>
    """
    if dua_depasse:
        content += '<div class="table-wrap"><table><thead><tr><th>Réf</th><th>Titre</th><th>Catégorie</th><th>DUA</th><th>Action</th></tr></thead><tbody>'
        for d in dua_depasse:
            content += f"""
            <tr>
              <td><strong>{d['reference']}</strong></td>
              <td>{d['titre'][:50]}</td>
              <td>{d['cat_nom'] or '-'}</td>
              <td><span class="badge badge-warning">{d['duree_conservation_ans']} ans</span></td>
              <td>
                <a href="/cycle-vie/{d['id']}/archiver" class="btn btn-purple btn-sm">
                   <i class="fas fa-archive"></i> Archiver</a>
              </td>
            </tr>"""
        content += "</tbody></table></div>"
    else:
        content += '<div class="empty" style="padding:20px"><i class="fas fa-check-circle" style="color:#10b981"></i><br>Aucune DUA dépassée</div>'
    content += "</div>"

    return _render(content, active='cycle', title='Cycle de vie')


@ged_bp.route('/cycle-vie/<int:did>/detruire', methods=['GET', 'POST'])
@_auth_required
def cycle_detruire(did):
    if not _can_validate():
        flash("Accès réservé archivistes/admin", "danger")
        return redirect('/')
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM documents WHERE id=? AND actif=1", (did,))
    doc = c.fetchone()
    if not doc:
        conn.close()
        flash("Document introuvable", "danger")
        return redirect('/cycle-vie')

    if request.method == 'POST':
        motif = (request.form.get('motif') or '').strip()
        # Soft delete + déplacement physique
        c.execute("""UPDATE documents SET actif=0, statut='Détruit',
                     updated_at=? WHERE id=?""", (datetime.now().isoformat(), did))
        conn.commit()
        _log('DESTRUCTION', f"doc={did} ref={doc['reference']} — motif: {motif}")

        # Déplacer le fichier vers archives
        try:
            arch_dir = _deps.get('ARCHIVE_FOLDER', '/app/data/archives')
            os.makedirs(arch_dir, exist_ok=True)
            if doc['fichier_chemin'] and os.path.exists(doc['fichier_chemin']):
                dest = os.path.join(arch_dir, f"DETRUIT_{datetime.now().strftime('%Y%m%d')}_{os.path.basename(doc['fichier_chemin'])}")
                shutil.move(doc['fichier_chemin'], dest)
        except Exception:
            pass

        conn.close()
        flash(f"Document {doc['reference']} détruit", "success")
        return redirect('/cycle-vie')

    content = f"""
    <div class="page-header">
      <div><h2 style="color:#991b1b"><i class="fas fa-fire"></i> Détruire un document</h2></div>
      <a href="/cycle-vie" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card" style="border-left:5px solid #dc2626">
      <div style="padding:15px;background:#fee2e2;border-radius:12px;margin-bottom:20px">
        <strong style="color:#991b1b">⚠️ Action irréversible</strong>
        <div style="margin-top:8px"><strong>{doc['reference']}</strong> — {doc['titre']}</div>
      </div>
      <form method="POST">
        <div class="form-group">
          <label>Motif de destruction *</label>
          <textarea name="motif" rows="3" required placeholder="Conformément à la politique de conservation..."></textarea>
        </div>
        <button class="btn btn-danger" onclick="return confirm(&#39;Confirmer destruction ?&#39;)">
          <i class="fas fa-fire"></i> Détruire définitivement
        </button>
      </form>
    </div>"""
    return _render(content, active='cycle', title='Détruire')


@ged_bp.route('/cycle-vie/<int:did>/archiver')
@_auth_required
def cycle_archiver(did):
    if not _can_validate():
        flash("Accès réservé", "danger")
        return redirect('/')
    conn = _db()
    c = conn.cursor()
    c.execute("UPDATE documents SET statut='Archivé', updated_at=? WHERE id=?",
              (datetime.now().isoformat(), did))
    conn.commit()
    _log('ARCHIVAGE', f"doc={did} archivé")
    conn.close()
    flash("Document archivé", "success")
    return redirect('/cycle-vie')


# ================================================================
# STATISTIQUES
# ================================================================
@ged_bp.route('/statistiques')
@_auth_required
def statistiques():
    if not _can_validate():
        flash("Accès réservé archivistes/admin", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()

    c.execute("SELECT statut, COUNT(*) as nb FROM documents WHERE actif=1 GROUP BY statut")
    par_statut = c.fetchall()

    c.execute("""SELECT cat.nom, cat.couleur, COUNT(d.id) as nb,
                        COALESCE(SUM(d.fichier_taille_ko),0) as taille
                 FROM categories cat LEFT JOIN documents d ON d.categorie_id=cat.id AND d.actif=1
                 WHERE cat.actif=1 GROUP BY cat.id HAVING nb>0 ORDER BY nb DESC""")
    par_cat = c.fetchall()

    c.execute("""SELECT u.prenom, u.nom, u.role, COUNT(d.id) as nb
                 FROM utilisateurs u LEFT JOIN documents d ON d.auteur_id=u.id AND d.actif=1
                 GROUP BY u.id HAVING nb>0 ORDER BY nb DESC LIMIT 10""")
    par_auteur = c.fetchall()

    c.execute("""SELECT strftime('%Y-%m', date_upload) AS mois, COUNT(*) AS nb
                 FROM documents WHERE actif=1 AND date_upload IS NOT NULL
                   AND date(date_upload) >= date('now','-6 months')
                 GROUP BY mois ORDER BY mois""")
    par_mois = c.fetchall()

    c.execute("SELECT COUNT(*) FROM documents WHERE actif=1")
    total = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM dossiers WHERE actif=1")
    total_dos = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(fichier_taille_ko),0) FROM documents WHERE actif=1")
    taille = c.fetchone()[0] or 0
    conn.close()

    max_cat = max([x['nb'] for x in par_cat], default=1)
    max_mois = max([x['nb'] for x in par_mois], default=1)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-chart-line"></i> Statistiques GED</h2>
        <div class="page-subtitle">Vue analytique du patrimoine documentaire</div></div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-file-alt"></i></div>
        <div class="stat-value">{total}</div><div class="stat-label">Documents actifs</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-folder"></i></div>
        <div class="stat-value">{total_dos}</div><div class="stat-label">Dossiers</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-database"></i></div>
        <div class="stat-value">{_fmt(taille)}</div><div class="stat-label">Volume total</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-chart-bar"></i> Répartition par statut</h3></div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px">
    """
    for s in par_statut:
        content += f"""
        <div style="padding:18px;background:#f0fdff;border-radius:12px;text-align:center;border-left:4px solid #06b6d4">
          <div style="font-size:2rem;font-weight:900;color:#0e7490">{s['nb']}</div>
          <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800;letter-spacing:0.5px">{s['statut']}</div>
        </div>"""
    content += "</div></div>"

    content += """
    <div class="card">
      <div class="card-header"><h3><i class="fas fa-chart-pie"></i> Top catégories</h3></div>"""
    for cat in par_cat:
        pct = (cat['nb'] / max_cat * 100) if max_cat else 0
        content += f"""
        <div style="margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <span style="font-weight:700;font-size:0.88rem">{cat['nom']}</span>
            <strong style="color:#0e7490">{cat['nb']} docs · {_fmt(cat['taille'])}</strong>
          </div>
          <div style="background:#f0fdff;border-radius:6px;height:10px;overflow:hidden">
            <div style="background:{cat['couleur'] or '#06b6d4'};height:100%;width:{pct}%"></div>
          </div>
        </div>"""
    content += "</div>"

    content += """
    <div class="card">
      <div class="card-header"><h3><i class="fas fa-users"></i> Top contributeurs</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Utilisateur</th><th>Rôle</th><th>Documents</th></tr></thead><tbody>"""
    for a in par_auteur:
        content += f"""
        <tr>
          <td><strong>{a['prenom'] or ''} {a['nom'] or ''}</strong></td>
          <td><span class="badge badge-role-{a['role']}">{a['role']}</span></td>
          <td><span class="badge badge-primary">{a['nb']}</span></td>
        </tr>"""
    if not par_auteur:
        content += '<tr><td colspan="3" class="empty">Aucune donnée</td></tr>'
    content += "</tbody></table></div></div>"

    if par_mois:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-calendar"></i> Évolution mensuelle (6 derniers mois)</h3></div>
        """
        for m in par_mois:
            pct = (m['nb'] / max_mois * 100) if max_mois else 0
            content += f"""
            <div style="margin-bottom:12px">
              <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="font-weight:700;font-size:0.85rem">{m['mois'] or '?'}</span>
                <strong style="color:#0e7490">{m['nb']} docs</strong>
              </div>
              <div style="background:#f0fdff;border-radius:6px;height:10px;overflow:hidden">
                <div style="background:linear-gradient(90deg,#0e7490,#22d3ee);height:100%;width:{pct}%"></div>
              </div>
            </div>"""
        content += "</div>"

    return _render(content, active='stats', title='Statistiques')


# ================================================================
# API JSON
# ================================================================
@ged_bp.route('/api/stats')
@_auth_required
def api_stats():
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM documents WHERE actif=1")
    docs = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM dossiers WHERE actif=1")
    dos = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(fichier_taille_ko),0) FROM documents WHERE actif=1")
    taille = c.fetchone()[0] or 0
    conn.close()
    return jsonify(documents=docs, dossiers=dos, taille_ko=taille,
                   taille_str=_fmt(taille), timestamp=datetime.now().isoformat())


@ged_bp.route('/api/recherche')
@_auth_required
def api_recherche():
    q = (request.args.get('q') or '').strip()
    if not q or len(q) < 2:
        return jsonify(results=[])
    conn = _db()
    c = conn.cursor()
    like = f"%{q}%"
    c.execute("""SELECT id, reference, titre FROM documents
                 WHERE actif=1 AND (titre LIKE ? OR reference LIKE ?)
                 ORDER BY date_upload DESC LIMIT 20""", (like, like))
    rows = c.fetchall()
    conn.close()
    return jsonify(results=[{'id': r['id'], 'ref': r['reference'], 'titre': r['titre']} for r in rows])
