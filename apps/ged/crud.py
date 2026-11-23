"""
Omega GED — Module CRUD
Dossiers · Documents · Catégories · Types · Tags · Services · Utilisateurs
Pattern : Blueprint + injection de dépendances (évite import circulaire)
"""
from flask import Blueprint, request, redirect, url_for, flash, jsonify, send_file, abort
from flask_login import current_user, login_required
import sqlite3
import os
import uuid
import hashlib
import mimetypes
import shutil
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

# ================================================================
# Blueprint + injection de dépendances
# ================================================================
crud_bp = Blueprint('crud', __name__)
_deps = {}


def init_crud(app, **kwargs):
    """Initialise le module CRUD avec les dépendances depuis main.py"""
    _deps.update(kwargs)
    app.register_blueprint(crud_bp)
    print("[CRUD] ✅ Module CRUD enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='dashboard', title='Omega GED'):
    return _deps['render_page'](content, active=active, page_title=title)


def _fmt(ko):
    return _deps['format_taille'](ko)


def _log(action, details='', user_id=None):
    """Wrapper compatible avec log_action(user_id, action, details)"""
    try:
        if user_id is None:
            try:
                from flask_login import current_user
                if current_user and current_user.is_authenticated:
                    user_id = current_user.id
            except Exception:
                pass
        _deps['log_action'](user_id, action, details)
    except Exception as e:
        print(f"[LOG CRUD] {e}")


def _admin_required(f):
    """Décorateur admin (délégué)"""
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if not (current_user and current_user.is_authenticated and current_user.role == 'admin'):
            flash("Accès réservé aux administrateurs", "danger")
            return redirect('/')
        return f(*a, **k)
    return w


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


# ================================================================
# HELPERS
# ================================================================
def _next_reference(conn, prefix='DOC'):
    """Génère une référence unique DOC-2026-0001"""
    year = datetime.now().year
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM documents WHERE reference LIKE ?", (f"{prefix}-{year}-%",))
    n = (c.fetchone()[0] or 0) + 1
    return f"{prefix}-{year}-{n:04d}"


def _slugify(txt):
    import unicodedata, re
    txt = unicodedata.normalize('NFKD', txt or '').encode('ascii', 'ignore').decode('ascii')
    txt = re.sub(r'[^a-zA-Z0-9]+', '-', txt).strip('-').lower()
    return txt[:80] or 'sans-nom'


def _list_categories(conn):
    c = conn.cursor()
    c.execute("SELECT * FROM categories WHERE actif=1 ORDER BY nom")
    return c.fetchall()


def _list_types(conn):
    c = conn.cursor()
    c.execute("SELECT * FROM types_documents WHERE actif=1 ORDER BY nom")
    return c.fetchall()


def _list_services(conn):
    c = conn.cursor()
    c.execute("SELECT * FROM services WHERE actif=1 ORDER BY nom")
    return c.fetchall()


def _list_tags(conn):
    c = conn.cursor()
    c.execute("SELECT * FROM tags ORDER BY nom")
    return c.fetchall()


def _list_users(conn):
    c = conn.cursor()
    c.execute("SELECT * FROM utilisateurs ORDER BY nom, prenom")
    return c.fetchall()


# ================================================================
# ==================== DOSSIERS ====================
# ================================================================
@crud_bp.route('/dossiers')
@_auth_required
def dossiers_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT d.*,
                 (SELECT COUNT(*) FROM documents WHERE dossier_id=d.id AND actif=1) AS nb_docs,
                 (SELECT COUNT(*) FROM dossiers WHERE parent_id=d.id AND actif=1) AS nb_sous,
                 p.nom AS parent_nom
                 FROM dossiers d
                 LEFT JOIN dossiers p ON d.parent_id=p.id
                 WHERE d.actif=1
                 ORDER BY d.parent_id NULLS FIRST, d.ordre, d.nom""")
    rows = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-folder"></i> Dossiers</h2>
        <div class="page-subtitle">Arborescence documentaire — {len(rows)} dossier(s) actif(s)</div>
      </div>
      <div style="display:flex;gap:10px">
        {'<a href="/dossiers/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau dossier</a>' if _can_write() else ''}
      </div>
    </div>

    <div class="card">
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Dossier</th><th>Parent</th><th>Documents</th><th>Sous-dossiers</th>
            <th>Créé le</th><th>Actions</th>
          </tr></thead>
          <tbody>
    """
    for d in rows:
        indent = "&nbsp;&nbsp;&nbsp;" if d['parent_id'] else ""
        icon = "fa-folder-open" if d['parent_id'] else "fa-folder"
        content += f"""
        <tr>
          <td>{indent}<i class="fas {icon}" style="color:#06b6d4"></i>
              <strong>{d['nom']}</strong>
              <div style="font-size:0.75rem;color:#94a3b8">{d['description'][:60] if d['description'] else ''}</div>
          </td>
          <td>{d['parent_nom'] or '<em style="color:#94a3b8">Racine</em>'}</td>
          <td><span class="badge badge-primary">{d['nb_docs']}</span></td>
          <td><span class="badge badge-info">{d['nb_sous']}</span></td>
          <td>{d['created_at'][:10] if d['created_at'] else '-'}</td>
          <td style="white-space:nowrap">
            <a href="/dossiers/{d['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
            {'<a href="/dossiers/'+str(d['id'])+'/modifier" class="btn btn-warning btn-sm"><i class="fas fa-pen"></i></a>' if _can_write() else ''}
            {'<a href="/dossiers/'+str(d['id'])+'/supprimer" class="btn btn-danger btn-sm" onclick="return confirm(&#39;Supprimer ce dossier ?&#39;)"><i class="fas fa-trash"></i></a>' if _can_write() else ''}
          </td>
        </tr>
        """
    if not rows:
        content += '<tr><td colspan="6" class="empty"><i class="fas fa-folder-open"></i><br>Aucun dossier</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='dossiers', title='Dossiers')


@crud_bp.route('/dossiers/nouveau', methods=['GET', 'POST'])
@_auth_required
def dossiers_new():
    if not _can_write():
        flash("Vous n'avez pas les droits pour créer un dossier", "danger")
        return redirect('/dossiers')

    conn = _db()
    if request.method == 'POST':
        nom = (request.form.get('nom') or '').strip()
        description = (request.form.get('description') or '').strip()
        parent_id = request.form.get('parent_id') or None
        if not nom:
            flash("Le nom est obligatoire", "warning")
        else:
            c = conn.cursor()
            try:
                # Générer un code unique
                c.execute("SELECT COUNT(*) FROM dossiers")
                n = (c.fetchone()[0] or 0) + 1
                code_dossier = f"DOS-{datetime.now().year}-{n:04d}"

                # Niveau (racine=0)
                niveau = 0
                if parent_id:
                    c.execute("SELECT niveau FROM dossiers WHERE id=?", (parent_id,))
                    row_p = c.fetchone()
                    if row_p and row_p[0] is not None:
                        niveau = (row_p[0] or 0) + 1

                # Chemin
                chemin = f"/{nom}"
                if parent_id:
                    c.execute("SELECT chemin FROM dossiers WHERE id=?", (parent_id,))
                    row_c = c.fetchone()
                    if row_c and row_c[0]:
                        chemin = f"{row_c[0]}/{nom}"

                # created_by
                created_by = current_user.id if (current_user and current_user.is_authenticated) else None

                c.execute("""INSERT INTO dossiers
                             (code, nom, description, parent_id, chemin, niveau,
                              created_by, created_at, updated_at, actif)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                          (code_dossier, nom, description, parent_id, chemin, niveau,
                           created_by,
                           datetime.now().isoformat(), datetime.now().isoformat()))
                new_id = c.lastrowid
                conn.commit()
                _log('CREATE_DOSSIER', f"Dossier '{nom}' créé (id={new_id})")
                flash(f"Dossier '{nom}' créé avec succès", "success")
                conn.close()
                return redirect(f'/dossiers/{new_id}')
            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    parents = []
    c = conn.cursor()
    c.execute("SELECT id, nom, parent_id FROM dossiers WHERE actif=1 ORDER BY nom")
    parents = c.fetchall()
    conn.close()

    options = '<option value="">— Aucun (racine) —</option>'
    for p in parents:
        indent = "&nbsp;&nbsp;&nbsp;" * (1 if p['parent_id'] else 0)
        options += f'<option value="{p["id"]}">{indent}{p["nom"]}</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-folder-plus"></i> Nouveau dossier</h2></div>
      <a href="/dossiers" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group form-full">
            <label>Nom du dossier *</label>
            <input type="text" name="nom" required placeholder="Ex : Contrats 2026">
          </div>
          <div class="form-group form-full">
            <label>Dossier parent</label>
            <select name="parent_id">{options}</select>
          </div>
          <div class="form-group form-full">
            <label>Description</label>
            <textarea name="description" rows="3" placeholder="Description facultative..."></textarea>
          </div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button type="submit" class="btn btn-primary"><i class="fas fa-check"></i> Créer</button>
          <a href="/dossiers" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>
    """
    return _render(content, active='dossiers', title='Nouveau dossier')


@crud_bp.route('/dossiers/<int:did>')
@_auth_required
def dossiers_detail(did):
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT d.*, p.nom AS parent_nom FROM dossiers d
                 LEFT JOIN dossiers p ON d.parent_id=p.id
                 WHERE d.id=? AND d.actif=1""", (did,))
    dossier = c.fetchone()
    if not dossier:
        conn.close()
        flash("Dossier introuvable", "danger")
        return redirect('/dossiers')

    c.execute("""SELECT * FROM dossiers WHERE parent_id=? AND actif=1 ORDER BY ordre, nom""", (did,))
    sous_dossiers = c.fetchall()

    c.execute("""SELECT d.*, cat.nom AS cat_nom, cat.couleur AS cat_couleur,
                        u.nom AS auteur_nom, u.prenom AS auteur_prenom
                 FROM documents d
                 LEFT JOIN categories cat ON d.categorie_id = cat.id
                 LEFT JOIN utilisateurs u ON d.auteur_id = u.id
                 WHERE d.dossier_id=? AND d.actif=1
                 ORDER BY d.date_upload DESC""", (did,))
    documents = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-folder-open"></i> {dossier['nom']}</h2>
        <div class="page-subtitle">
          {dossier['description'] or 'Aucune description'} ·
          Parent : {dossier['parent_nom'] or 'Racine'}
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/dossiers" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        {'<a href="/dossiers/'+str(did)+'/modifier" class="btn btn-warning"><i class="fas fa-pen"></i> Modifier</a>' if _can_write() else ''}
      </div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-file-alt"></i></div>
        <div class="stat-value">{len(documents)}</div>
        <div class="stat-label">Documents</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-folder"></i></div>
        <div class="stat-value">{len(sous_dossiers)}</div>
        <div class="stat-label">Sous-dossiers</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-folder"></i> Sous-dossiers</h3></div>
    """
    if sous_dossiers:
        for s in sous_dossiers:
            content += f"""
            <a href="/dossiers/{s['id']}" class="dossier-item">
              <div class="dossier-icon"><i class="fas fa-folder"></i></div>
              <div class="dossier-info">
                <div class="dossier-nom">{s['nom']}</div>
                <div class="dossier-meta">{s['description'][:80] if s['description'] else ''}</div>
              </div>
              <i class="fas fa-chevron-right" style="color:#94a3b8"></i>
            </a>"""
    else:
        content += '<div class="empty" style="padding:20px">Aucun sous-dossier</div>'

    content += """
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-file-alt"></i> Documents</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Réf</th><th>Titre</th><th>Catégorie</th><th>Auteur</th>
                   <th>Taille</th><th>Statut</th><th></th></tr></thead>
        <tbody>
    """
    for d in documents:
        content += f"""
        <tr>
          <td><strong>{d['reference']}</strong></td>
          <td>{d['titre'][:50]}</td>
          <td>{d['cat_nom'] or '-'}</td>
          <td>{d['auteur_prenom'] or ''} {d['auteur_nom'] or ''}</td>
          <td>{_fmt(d['fichier_taille_ko'] or 0)}</td>
          <td><span class="badge badge-info">{d['statut']}</span></td>
          <td><a href="/documents/{d['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a></td>
        </tr>"""
    if not documents:
        content += '<tr><td colspan="7" class="empty"><i class="fas fa-file-alt"></i><br>Aucun document</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='dossiers', title=dossier['nom'])


@crud_bp.route('/dossiers/<int:did>/modifier', methods=['GET', 'POST'])
@_auth_required
def dossiers_edit(did):
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/dossiers')

    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM dossiers WHERE id=? AND actif=1", (did,))
    dossier = c.fetchone()
    if not dossier:
        conn.close()
        flash("Dossier introuvable", "danger")
        return redirect('/dossiers')

    if request.method == 'POST':
        nom = (request.form.get('nom') or '').strip()
        description = (request.form.get('description') or '').strip()
        parent_id = request.form.get('parent_id') or None
        if parent_id and int(parent_id) == did:
            parent_id = None
        if not nom:
            flash("Nom obligatoire", "warning")
        else:
            c.execute("""UPDATE dossiers SET nom=?, description=?, parent_id=?,
                         updated_at=? WHERE id=?""",
                      (nom, description, parent_id, datetime.now().isoformat(), did))
            conn.commit()
            _log('UPDATE_DOSSIER', f"Dossier id={did} modifié")
            flash("Dossier mis à jour", "success")
            conn.close()
            return redirect(f'/dossiers/{did}')

    c.execute("SELECT id, nom, parent_id FROM dossiers WHERE actif=1 AND id<>? ORDER BY nom", (did,))
    parents = c.fetchall()
    conn.close()

    options = '<option value="">— Racine —</option>'
    for p in parents:
        sel = 'selected' if dossier['parent_id'] == p['id'] else ''
        indent = "&nbsp;&nbsp;&nbsp;" * (1 if p['parent_id'] else 0)
        options += f'<option value="{p["id"]}" {sel}>{indent}{p["nom"]}</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-pen"></i> Modifier dossier</h2></div>
      <a href="/dossiers/{did}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card">
      <form method="POST">
        <div class="form-grid">
          <div class="form-group form-full">
            <label>Nom *</label>
            <input type="text" name="nom" value="{dossier['nom']}" required>
          </div>
          <div class="form-group form-full">
            <label>Parent</label>
            <select name="parent_id">{options}</select>
          </div>
          <div class="form-group form-full">
            <label>Description</label>
            <textarea name="description" rows="3">{dossier['description'] or ''}</textarea>
          </div>
        </div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
          <a href="/dossiers/{did}" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>"""
    return _render(content, active='dossiers', title='Modifier dossier')


@crud_bp.route('/dossiers/<int:did>/supprimer')
@_auth_required
def dossiers_delete(did):
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/dossiers')
    conn = _db()
    c = conn.cursor()
    c.execute("UPDATE dossiers SET actif=0, updated_at=? WHERE id=?",
              (datetime.now().isoformat(), did))
    conn.commit()
    _log('DELETE_DOSSIER', f"Dossier id={did} archivé (soft delete)")
    conn.close()
    flash("Dossier supprimé", "success")
    return redirect('/dossiers')


# ================================================================
# ==================== DOCUMENTS ====================
# ================================================================
@crud_bp.route('/documents')
@_auth_required
def documents_list():
    q = (request.args.get('q') or '').strip()
    statut = request.args.get('statut') or ''
    cat_id = request.args.get('cat') or ''

    conn = _db()
    c = conn.cursor()
    sql = """SELECT d.*, cat.nom AS cat_nom, cat.couleur AS cat_couleur,
                    u.nom AS auteur_nom, u.prenom AS auteur_prenom,
                    dos.nom AS dossier_nom
             FROM documents d
             LEFT JOIN categories cat ON d.categorie_id = cat.id
             LEFT JOIN utilisateurs u ON d.auteur_id = u.id
             LEFT JOIN dossiers dos ON d.dossier_id = dos.id
             WHERE d.actif=1"""
    params = []
    if q:
        sql += " AND (d.titre LIKE ? OR d.reference LIKE ? OR d.description LIKE ?)"
        params += [f"%{q}%"] * 3
    if statut:
        sql += " AND d.statut=?"
        params.append(statut)
    if cat_id:
        sql += " AND d.categorie_id=?"
        params.append(cat_id)
    sql += " ORDER BY d.date_upload DESC LIMIT 200"
    c.execute(sql, params)
    docs = c.fetchall()

    cats = _list_categories(conn)
    conn.close()

    statuts = ['Brouillon', 'En validation', 'Publié', 'Archivé', 'À détruire']
    opt_cat = '<option value="">Toutes catégories</option>'
    for cat in cats:
        sel = 'selected' if str(cat['id']) == cat_id else ''
        opt_cat += f'<option value="{cat["id"]}" {sel}>{cat["nom"]}</option>'
    opt_statut = '<option value="">Tous statuts</option>'
    for s in statuts:
        sel = 'selected' if s == statut else ''
        opt_statut += f'<option value="{s}" {sel}>{s}</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-file-alt"></i> Documents</h2>
        <div class="page-subtitle">{len(docs)} document(s)</div></div>
      {'<a href="/upload" class="btn btn-primary"><i class="fas fa-upload"></i> Uploader</a>' if _can_write() else ''}
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:2;margin:0;min-width:220px">
          <label>Recherche</label>
          <input type="text" name="q" value="{q}" placeholder="Titre, référence...">
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:160px">
          <label>Catégorie</label>
          <select name="cat">{opt_cat}</select>
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Statut</label>
          <select name="statut">{opt_statut}</select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-search"></i> Filtrer</button>
        <a href="/documents" class="btn btn-info"><i class="fas fa-rotate"></i> Reset</a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Réf</th><th>Titre</th><th>Dossier</th><th>Catégorie</th>
          <th>Auteur</th><th>Taille</th><th>Date</th><th>Statut</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for d in docs:
        badge = 'badge-info'
        if d['statut'] == 'Publié': badge = 'badge-success'
        elif d['statut'] == 'En validation': badge = 'badge-warning'
        elif d['statut'] == 'Archivé': badge = 'badge-primary'
        lock = ' 🔒' if d['confidentiel'] else ''
        content += f"""
        <tr>
          <td><strong>{d['reference']}</strong></td>
          <td>{d['titre'][:45]}{lock}</td>
          <td><small>{d['dossier_nom'] or '-'}</small></td>
          <td><span class="badge" style="background:{d['cat_couleur'] or '#06b6d4'}20;color:{d['cat_couleur'] or '#0e7490'}">{d['cat_nom'] or '-'}</span></td>
          <td><small>{d['auteur_prenom'] or ''} {d['auteur_nom'] or ''}</small></td>
          <td>{_fmt(d['fichier_taille_ko'] or 0)}</td>
          <td><small>{d['date_upload'][:10] if d['date_upload'] else '-'}</small></td>
          <td><span class="badge {badge}">{d['statut']}</span></td>
          <td style="white-space:nowrap">
            <a href="/documents/{d['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
            <a href="/documents/{d['id']}/telecharger" class="btn btn-success btn-sm"><i class="fas fa-download"></i></a>
          </td>
        </tr>"""
    if not docs:
        content += '<tr><td colspan="9" class="empty"><i class="fas fa-file-alt"></i><br>Aucun document</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='documents', title='Documents')


@crud_bp.route('/documents/<int:did>')
@_auth_required
def documents_detail(did):
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT d.*, cat.nom AS cat_nom, cat.couleur AS cat_couleur,
                        u.nom AS auteur_nom, u.prenom AS auteur_prenom,
                        dos.nom AS dossier_nom, ty.nom AS type_nom
                 FROM documents d
                 LEFT JOIN categories cat ON d.categorie_id = cat.id
                 LEFT JOIN utilisateurs u ON d.auteur_id = u.id
                 LEFT JOIN dossiers dos ON d.dossier_id = dos.id
                 LEFT JOIN types_documents ty ON d.type_id = ty.id
                 WHERE d.id=? AND d.actif=1""", (did,))
    doc = c.fetchone()
    if not doc:
        conn.close()
        flash("Document introuvable", "danger")
        return redirect('/documents')

    c.execute("SELECT * FROM versions WHERE document_id=? ORDER BY numero DESC", (did,))
    versions = c.fetchall()

    c.execute("""SELECT t.* FROM tags t
                 INNER JOIN document_tags dt ON dt.tag_id=t.id
                 WHERE dt.document_id=?""", (did,))
    tags = c.fetchall()

    c.execute("""SELECT * FROM audit_log WHERE details LIKE ?
                 ORDER BY created_at DESC LIMIT 20""", (f"%doc={did}%",))
    historique = c.fetchall()
    conn.close()

    badge = 'badge-info'
    if doc['statut'] == 'Publié': badge = 'badge-success'
    elif doc['statut'] == 'En validation': badge = 'badge-warning'
    elif doc['statut'] == 'Archivé': badge = 'badge-primary'

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-file-alt"></i> {doc['titre']}</h2>
        <div class="page-subtitle">
          <strong>{doc['reference']}</strong> ·
          <span class="badge {badge}">{doc['statut']}</span>
          {(' <span class="badge badge-danger">🔒 Confidentiel</span>') if doc['confidentiel'] else ''}
        </div>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <a href="/documents" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        <a href="/documents/{did}/telecharger" class="btn btn-success"><i class="fas fa-download"></i> Télécharger</a>
        {'<a href="/documents/'+str(did)+'/modifier" class="btn btn-warning"><i class="fas fa-pen"></i> Modifier</a>' if _can_write() else ''}
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Informations</h3></div>
      <div class="form-grid">
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Référence</label>
             <div style="font-weight:700">{doc['reference']}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Catégorie</label>
             <div>{doc['cat_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Type</label>
             <div>{doc['type_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Dossier</label>
             <div>{doc['dossier_nom'] or '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Auteur</label>
             <div>{doc['auteur_prenom'] or ''} {doc['auteur_nom'] or ''}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Date upload</label>
             <div>{doc['date_upload'][:19] if doc['date_upload'] else '-'}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Taille</label>
             <div>{_fmt(doc['fichier_taille_ko'] or 0)}</div></div>
        <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Version</label>
             <div>{doc['version'] or 1}</div></div>
        <div class="form-full"><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Description</label>
             <div>{doc['description'] or '<em style="color:#94a3b8">Aucune</em>'}</div></div>
        <div class="form-full"><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Checksum SHA-256</label>
             <div style="font-family:monospace;font-size:0.75rem;color:#64748b;word-break:break-all">{doc['checksum'] or '-'}</div></div>
      </div>
    </div>
    """

    if tags:
        content += '<div class="card"><div class="card-header"><h3><i class="fas fa-tags"></i> Tags</h3></div>'
        for t in tags:
            content += f'<span class="badge" style="background:{t["couleur"] or "#06b6d4"};color:white;margin-right:6px">{t["nom"]}</span>'
        content += '</div>'

    if versions:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-code-branch"></i> Historique des versions</h3></div>
          <div class="table-wrap"><table>
            <thead><tr><th>N°</th><th>Fichier</th><th>Taille</th><th>Date</th><th>Commentaire</th></tr></thead>
            <tbody>"""
        for v in versions:
            content += f"""<tr>
              <td><span class="badge badge-primary">v{v['numero']}</span></td>
              <td>{v['nom_fichier'] or '-'}</td>
              <td>{_fmt(v['taille_ko'] or 0)}</td>
              <td>{v['created_at'][:19] if v['created_at'] else '-'}</td>
              <td>{v['commentaire'] or ''}</td>
            </tr>"""
        content += "</tbody></table></div></div>"

    if historique:
        content += """
        <div class="card">
          <div class="card-header"><h3><i class="fas fa-history"></i> Historique d'audit</h3></div>"""
        for h in historique:
            content += f"""
            <div style="padding:8px 0;border-bottom:1px dashed #f0fdff;display:flex;justify-content:space-between">
              <div><strong style="font-size:0.85rem">{h['action']}</strong>
                   <div style="font-size:0.78rem;color:#64748b">{h['details'] or ''}</div></div>
              <small style="color:#94a3b8">{h['created_at'][:16]}</small>
            </div>"""
        content += "</div>"

    return _render(content, active='documents', title=doc['titre'])


@crud_bp.route('/documents/<int:did>/modifier', methods=['GET', 'POST'])
@_auth_required
def documents_edit(did):
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

    if request.method == 'POST':
        titre = (request.form.get('titre') or '').strip()
        description = (request.form.get('description') or '').strip()
        cat_id = request.form.get('categorie_id') or None
        type_id = request.form.get('type_id') or None
        dossier_id = request.form.get('dossier_id') or None
        confidentiel = 1 if request.form.get('confidentiel') else 0
        date_destruction = request.form.get('date_destruction_prevue') or None

        if not titre:
            flash("Titre obligatoire", "warning")
        else:
            c.execute("""UPDATE documents SET titre=?, description=?, categorie_id=?,
                         type_id=?, dossier_id=?, confidentiel=?, date_destruction_prevue=?,
                         updated_at=? WHERE id=?""",
                      (titre, description, cat_id, type_id, dossier_id, confidentiel,
                       date_destruction, datetime.now().isoformat(), did))
            conn.commit()
            _log('UPDATE_DOCUMENT', f"doc={did} modifié")
            flash("Document mis à jour", "success")
            conn.close()
            return redirect(f'/documents/{did}')

    cats = _list_categories(conn)
    types = _list_types(conn)
    c.execute("SELECT id, nom FROM dossiers WHERE actif=1 ORDER BY nom")
    dossiers = c.fetchall()
    conn.close()

    opt_cat = '<option value="">—</option>'
    for cat in cats:
        sel = 'selected' if doc['categorie_id'] == cat['id'] else ''
        opt_cat += f'<option value="{cat["id"]}" {sel}>{cat["nom"]}</option>'
    opt_type = '<option value="">—</option>'
    for t in types:
        sel = 'selected' if doc['type_id'] == t['id'] else ''
        opt_type += f'<option value="{t["id"]}" {sel}>{t["nom"]}</option>'
    opt_dos = '<option value="">—</option>'
    for d in dossiers:
        sel = 'selected' if doc['dossier_id'] == d['id'] else ''
        opt_dos += f'<option value="{d["id"]}" {sel}>{d["nom"]}</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-pen"></i> Modifier document</h2></div>
      <a href="/documents/{did}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card"><form method="POST">
      <div class="form-grid">
        <div class="form-group form-full">
          <label>Titre *</label>
          <input type="text" name="titre" value="{doc['titre']}" required>
        </div>
        <div class="form-group"><label>Catégorie</label><select name="categorie_id">{opt_cat}</select></div>
        <div class="form-group"><label>Type</label><select name="type_id">{opt_type}</select></div>
        <div class="form-group"><label>Dossier</label><select name="dossier_id">{opt_dos}</select></div>
        <div class="form-group">
          <label>Date destruction prévue</label>
          <input type="date" name="date_destruction_prevue" value="{doc['date_destruction_prevue'] or ''}">
        </div>
        <div class="form-group form-full">
          <label>Description</label>
          <textarea name="description" rows="3">{doc['description'] or ''}</textarea>
        </div>
        <div class="form-group form-full">
          <label><input type="checkbox" name="confidentiel" {'checked' if doc['confidentiel'] else ''}> Document confidentiel 🔒</label>
        </div>
      </div>
      <div style="display:flex;gap:10px;margin-top:20px">
        <button class="btn btn-primary"><i class="fas fa-check"></i> Enregistrer</button>
        <a href="/documents/{did}" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
      </div>
    </form></div>"""
    return _render(content, active='documents', title='Modifier')


@crud_bp.route('/documents/<int:did>/telecharger')
@_auth_required
def documents_download(did):
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM documents WHERE id=? AND actif=1", (did,))
    doc = c.fetchone()
    conn.close()
    if not doc or not doc['fichier_path'] or not os.path.exists(doc['fichier_path']):
        flash("Fichier introuvable", "danger")
        return redirect('/documents')
    _log('DOWNLOAD_DOCUMENT', f"doc={did} téléchargé")
    return send_file(doc['fichier_path'], as_attachment=True,
                     download_name=doc['nom_fichier'] or f"doc_{did}")


# ================================================================
# ==================== CATÉGORIES ====================
# ================================================================
@crud_bp.route('/categories')
@_auth_required
def categories_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT cat.*,
                 (SELECT COUNT(*) FROM documents WHERE categorie_id=cat.id AND actif=1) AS nb_docs
                 FROM categories cat WHERE cat.actif=1 ORDER BY cat.nom""")
    cats = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-tags"></i> Catégories</h2>
        <div class="page-subtitle">{len(cats)} catégorie(s)</div></div>
      {'<a href="/categories/nouvelle" class="btn btn-primary"><i class="fas fa-plus"></i> Nouvelle</a>' if _can_validate() else ''}
    </div>
    <div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Couleur</th><th>Nom</th><th>Code</th><th>Durée conservation</th><th>Documents</th><th>Actions</th></tr></thead>
      <tbody>"""
    for cat in cats:
        content += f"""
        <tr>
          <td><div style="width:30px;height:30px;background:{cat['couleur'] or '#06b6d4'};border-radius:8px"></div></td>
          <td><strong>{cat['nom']}</strong><div style="font-size:0.75rem;color:#94a3b8">{cat['description'][:60] if cat['description'] else ''}</div></td>
          <td><code>{cat['code'] or '-'}</code></td>
          <td>{cat['duree_conservation_ans'] or '-'} ans</td>
          <td><span class="badge badge-primary">{cat['nb_docs']}</span></td>
          <td>
            {'<a href="/categories/'+str(cat['id'])+'/modifier" class="btn btn-warning btn-sm"><i class="fas fa-pen"></i></a>' if _can_validate() else ''}
            {'<a href="/categories/'+str(cat['id'])+'/supprimer" class="btn btn-danger btn-sm" onclick="return confirm(&#39;Supprimer ?&#39;)"><i class="fas fa-trash"></i></a>' if _can_validate() else ''}
          </td>
        </tr>"""
    if not cats:
        content += '<tr><td colspan="6" class="empty"><i class="fas fa-tags"></i><br>Aucune catégorie</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='admin', title='Catégories')


@crud_bp.route('/categories/nouvelle', methods=['GET', 'POST'])
@_auth_required
def categories_new():
    if not _can_validate():
        flash("Droits insuffisants", "danger")
        return redirect('/categories')
    if request.method == 'POST':
        nom = (request.form.get('nom') or '').strip()
        code = (request.form.get('code') or '').strip()
        couleur = request.form.get('couleur') or '#06b6d4'
        description = (request.form.get('description') or '').strip()
        duree = request.form.get('duree_conservation_ans') or None
        if not nom:
            flash("Nom obligatoire", "warning")
        else:
            conn = _db()
            c = conn.cursor()
            try:
                c.execute("""INSERT INTO categories (nom, code, couleur, description, duree_conservation_ans, actif, created_at)
                             VALUES (?,?,?,?,?,1,?)""",
                          (nom, code, couleur, description, duree, datetime.now().isoformat()))
                conn.commit()
                _log('CREATE_CATEGORIE', f"Catégorie '{nom}' créée")
                conn.close()
                flash("Catégorie créée", "success")
                return redirect('/categories')
            except Exception as e:
                conn.close()
                flash(f"Erreur : {e}", "danger")

    content = """
    <div class="page-header"><div><h2><i class="fas fa-tags"></i> Nouvelle catégorie</h2></div>
      <a href="/categories" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a></div>
    <div class="card"><form method="POST">
      <div class="form-grid">
        <div class="form-group"><label>Nom *</label><input name="nom" required></div>
        <div class="form-group"><label>Code</label><input name="code" placeholder="Ex: RH, FIN, JUR"></div>
        <div class="form-group"><label>Couleur</label><input type="color" name="couleur" value="#06b6d4"></div>
        <div class="form-group"><label>Durée conservation (ans)</label><input type="number" name="duree_conservation_ans" min="1" value="5"></div>
        <div class="form-group form-full"><label>Description</label><textarea name="description" rows="3"></textarea></div>
      </div>
      <button class="btn btn-primary" style="margin-top:20px"><i class="fas fa-check"></i> Créer</button>
    </form></div>"""
    return _render(content, active='admin', title='Nouvelle catégorie')


@crud_bp.route('/categories/<int:cid>/modifier', methods=['GET', 'POST'])
@_auth_required
def categories_edit(cid):
    if not _can_validate():
        flash("Droits insuffisants", "danger")
        return redirect('/categories')
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM categories WHERE id=?", (cid,))
    cat = c.fetchone()
    if not cat:
        conn.close()
        return redirect('/categories')
    if request.method == 'POST':
        c.execute("""UPDATE categories SET nom=?, code=?, couleur=?, description=?, duree_conservation_ans=?
                     WHERE id=?""",
                  ((request.form.get('nom') or '').strip(),
                   (request.form.get('code') or '').strip(),
                   request.form.get('couleur') or '#06b6d4',
                   (request.form.get('description') or '').strip(),
                   request.form.get('duree_conservation_ans') or None, cid))
        conn.commit()
        _log('UPDATE_CATEGORIE', f"Catégorie id={cid} modifiée")
        conn.close()
        flash("Catégorie mise à jour", "success")
        return redirect('/categories')

    content = f"""
    <div class="page-header"><div><h2><i class="fas fa-pen"></i> Modifier catégorie</h2></div>
      <a href="/categories" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a></div>
    <div class="card"><form method="POST">
      <div class="form-grid">
        <div class="form-group"><label>Nom *</label><input name="nom" value="{cat['nom']}" required></div>
        <div class="form-group"><label>Code</label><input name="code" value="{cat['code'] or ''}"></div>
        <div class="form-group"><label>Couleur</label><input type="color" name="couleur" value="{cat['couleur'] or '#06b6d4'}"></div>
        <div class="form-group"><label>Durée (ans)</label><input type="number" name="duree_conservation_ans" value="{cat['duree_conservation_ans'] or 5}"></div>
        <div class="form-group form-full"><label>Description</label><textarea name="description" rows="3">{cat['description'] or ''}</textarea></div>
      </div>
      <button class="btn btn-primary" style="margin-top:20px"><i class="fas fa-check"></i> Enregistrer</button>
    </form></div>"""
    conn.close()
    return _render(content, active='admin', title='Modifier catégorie')


@crud_bp.route('/categories/<int:cid>/supprimer')
@_auth_required
def categories_delete(cid):
    if not _can_validate():
        flash("Droits insuffisants", "danger")
        return redirect('/categories')
    conn = _db()
    c = conn.cursor()
    c.execute("UPDATE categories SET actif=0 WHERE id=?", (cid,))
    conn.commit()
    _log('DELETE_CATEGORIE', f"Catégorie id={cid} désactivée")
    conn.close()
    flash("Catégorie supprimée", "success")
    return redirect('/categories')


# ================================================================
# ==================== TYPES DOCUMENTS ====================
# ================================================================
@crud_bp.route('/types')
@_auth_required
def types_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT t.*,
                 (SELECT COUNT(*) FROM documents WHERE type_id=t.id AND actif=1) AS nb_docs
                 FROM types_documents t WHERE t.actif=1 ORDER BY t.nom""")
    types = c.fetchall()
    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-file"></i> Types de documents</h2>
        <div class="page-subtitle">{len(types)} type(s)</div></div>
      {'<a href="/types/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau</a>' if _can_validate() else ''}
    </div>
    <div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Nom</th><th>Extension</th><th>Description</th><th>Documents</th><th>Actions</th></tr></thead>
      <tbody>"""
    for t in types:
        content += f"""
        <tr><td><strong>{t['nom']}</strong></td>
            <td><code>.{t['extension'] or '?'}</code></td>
            <td>{t['description'][:60] if t['description'] else '-'}</td>
            <td><span class="badge badge-primary">{t['nb_docs']}</span></td>
            <td>
              {'<a href="/types/'+str(t['id'])+'/modifier" class="btn btn-warning btn-sm"><i class="fas fa-pen"></i></a>' if _can_validate() else ''}
              {'<a href="/types/'+str(t['id'])+'/supprimer" class="btn btn-danger btn-sm" onclick="return confirm(&#39;Supprimer ?&#39;)"><i class="fas fa-trash"></i></a>' if _can_validate() else ''}
            </td></tr>"""
    if not types:
        content += '<tr><td colspan="5" class="empty"><i class="fas fa-file"></i><br>Aucun type</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='admin', title='Types de documents')


@crud_bp.route('/types/nouveau', methods=['GET', 'POST'])
@_auth_required
def types_new():
    if not _can_validate():
        flash("Droits insuffisants", "danger")
        return redirect('/types')
    if request.method == 'POST':
        nom = (request.form.get('nom') or '').strip()
        ext = (request.form.get('extension') or '').strip().lstrip('.').lower()
        desc = (request.form.get('description') or '').strip()
        if not nom:
            flash("Nom obligatoire", "warning")
        else:
            conn = _db()
            c = conn.cursor()
            try:
                c.execute("""INSERT INTO types_documents (nom, extension, description, actif, created_at)
                             VALUES (?,?,?,1,?)""", (nom, ext, desc, datetime.now().isoformat()))
                conn.commit()
                _log('CREATE_TYPE', f"Type '{nom}' créé")
                conn.close()
                flash("Type créé", "success")
                return redirect('/types')
            except Exception as e:
                conn.close()
                flash(f"Erreur : {e}", "danger")

    content = """
    <div class="page-header"><div><h2><i class="fas fa-file"></i> Nouveau type</h2></div>
      <a href="/types" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a></div>
    <div class="card"><form method="POST">
      <div class="form-grid">
        <div class="form-group"><label>Nom *</label><input name="nom" required placeholder="Ex: Contrat"></div>
        <div class="form-group"><label>Extension</label><input name="extension" placeholder="pdf, docx..."></div>
        <div class="form-group form-full"><label>Description</label><textarea name="description" rows="3"></textarea></div>
      </div>
      <button class="btn btn-primary" style="margin-top:20px"><i class="fas fa-check"></i> Créer</button>
    </form></div>"""
    return _render(content, active='admin', title='Nouveau type')


@crud_bp.route('/types/<int:tid>/modifier', methods=['GET', 'POST'])
@_auth_required
def types_edit(tid):
    if not _can_validate():
        flash("Droits insuffisants", "danger")
        return redirect('/types')
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM types_documents WHERE id=?", (tid,))
    t = c.fetchone()
    if not t:
        conn.close()
        return redirect('/types')
    if request.method == 'POST':
        c.execute("""UPDATE types_documents SET nom=?, extension=?, description=? WHERE id=?""",
                  ((request.form.get('nom') or '').strip(),
                   (request.form.get('extension') or '').strip().lstrip('.').lower(),
                   (request.form.get('description') or '').strip(), tid))
        conn.commit()
        _log('UPDATE_TYPE', f"Type id={tid} modifié")
        conn.close()
        flash("Type mis à jour", "success")
        return redirect('/types')

    content = f"""
    <div class="page-header"><div><h2><i class="fas fa-pen"></i> Modifier type</h2></div>
      <a href="/types" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a></div>
    <div class="card"><form method="POST">
      <div class="form-grid">
        <div class="form-group"><label>Nom *</label><input name="nom" value="{t['nom']}" required></div>
        <div class="form-group"><label>Extension</label><input name="extension" value="{t['extension'] or ''}"></div>
        <div class="form-group form-full"><label>Description</label><textarea name="description" rows="3">{t['description'] or ''}</textarea></div>
      </div>
      <button class="btn btn-primary" style="margin-top:20px"><i class="fas fa-check"></i> Enregistrer</button>
    </form></div>"""
    conn.close()
    return _render(content, active='admin', title='Modifier type')


@crud_bp.route('/types/<int:tid>/supprimer')
@_auth_required
def types_delete(tid):
    if not _can_validate():
        flash("Droits insuffisants", "danger")
        return redirect('/types')
    conn = _db()
    c = conn.cursor()
    c.execute("UPDATE types_documents SET actif=0 WHERE id=?", (tid,))
    conn.commit()
    _log('DELETE_TYPE', f"Type id={tid} désactivé")
    conn.close()
    flash("Type supprimé", "success")
    return redirect('/types')


# ================================================================
# ==================== TAGS ====================
# ================================================================
@crud_bp.route('/tags')
@_auth_required
def tags_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT t.*,
                 (SELECT COUNT(*) FROM document_tags WHERE tag_id=t.id) AS nb_usage
                 FROM tags t ORDER BY t.nom""")
    tags = c.fetchall()
    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-tag"></i> Tags</h2>
        <div class="page-subtitle">{len(tags)} tag(s)</div></div>
      {'<a href="/tags/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau</a>' if _can_write() else ''}
    </div>
    <div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Couleur</th><th>Nom</th><th>Utilisations</th><th>Actions</th></tr></thead>
      <tbody>"""
    for t in tags:
        content += f"""
        <tr>
          <td><span class="badge" style="background:{t['couleur'] or '#06b6d4'};color:white">{t['nom']}</span></td>
          <td><strong>{t['nom']}</strong></td>
          <td><span class="badge badge-primary">{t['nb_usage']}</span></td>
          <td>
            {'<a href="/tags/'+str(t['id'])+'/supprimer" class="btn btn-danger btn-sm" onclick="return confirm(&#39;Supprimer ?&#39;)"><i class="fas fa-trash"></i></a>' if _can_write() else ''}
          </td></tr>"""
    if not tags:
        content += '<tr><td colspan="4" class="empty"><i class="fas fa-tag"></i><br>Aucun tag</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='admin', title='Tags')


@crud_bp.route('/tags/nouveau', methods=['GET', 'POST'])
@_auth_required
def tags_new():
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/tags')
    if request.method == 'POST':
        nom = (request.form.get('nom') or '').strip()
        couleur = request.form.get('couleur') or '#06b6d4'
        if not nom:
            flash("Nom obligatoire", "warning")
        else:
            conn = _db()
            c = conn.cursor()
            try:
                c.execute("INSERT INTO tags (nom, couleur) VALUES (?,?)", (nom, couleur))
                conn.commit()
                _log('CREATE_TAG', f"Tag '{nom}' créé")
                conn.close()
                flash("Tag créé", "success")
                return redirect('/tags')
            except Exception as e:
                conn.close()
                flash(f"Erreur : {e}", "danger")

    content = """
    <div class="page-header"><div><h2><i class="fas fa-tag"></i> Nouveau tag</h2></div>
      <a href="/tags" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a></div>
    <div class="card"><form method="POST">
      <div class="form-grid">
        <div class="form-group"><label>Nom *</label><input name="nom" required placeholder="Ex: urgent, 2026..."></div>
        <div class="form-group"><label>Couleur</label><input type="color" name="couleur" value="#06b6d4"></div>
      </div>
      <button class="btn btn-primary" style="margin-top:20px"><i class="fas fa-check"></i> Créer</button>
    </form></div>"""
    return _render(content, active='admin', title='Nouveau tag')


@crud_bp.route('/tags/<int:tid>/supprimer')
@_auth_required
def tags_delete(tid):
    if not _can_write():
        flash("Droits insuffisants", "danger")
        return redirect('/tags')
    conn = _db()
    c = conn.cursor()
    c.execute("DELETE FROM tags WHERE id=?", (tid,))
    conn.commit()
    _log('DELETE_TAG', f"Tag id={tid} supprimé")
    conn.close()
    flash("Tag supprimé", "success")
    return redirect('/tags')


# ================================================================
# ==================== SERVICES ====================
# ================================================================
@crud_bp.route('/services')
@_auth_required
def services_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT s.*,
                 (SELECT COUNT(*) FROM utilisateurs u WHERE u.service=s.nom) AS nb_users
                 FROM services s WHERE s.actif=1 ORDER BY s.nom""")
    services = c.fetchall()
    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-building"></i> Services / Directions</h2>
        <div class="page-subtitle">{len(services)} service(s)</div></div>
      {'<a href="/services/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Nouveau</a>' if _can_validate() else ''}
    </div>
    <div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Nom</th><th>Code</th><th>Responsable</th><th>Utilisateurs</th><th>Actions</th></tr></thead>
      <tbody>"""
    for s in services:
        content += f"""
        <tr>
          <td><strong>{s['nom']}</strong></td>
          <td><code>{s['code'] or '-'}</code></td>
          <td>{s['responsable'] or '-'}</td>
          <td><span class="badge badge-info">{s['nb_users']}</span></td>
          <td>
            {'<a href="/services/'+str(s['id'])+'/supprimer" class="btn btn-danger btn-sm" onclick="return confirm(&#39;Supprimer ?&#39;)"><i class="fas fa-trash"></i></a>' if _can_validate() else ''}
          </td></tr>"""
    if not services:
        content += '<tr><td colspan="5" class="empty"><i class="fas fa-building"></i><br>Aucun service</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='admin', title='Services')


@crud_bp.route('/services/nouveau', methods=['GET', 'POST'])
@_auth_required
def services_new():
    if not _can_validate():
        flash("Droits insuffisants", "danger")
        return redirect('/services')
    if request.method == 'POST':
        nom = (request.form.get('nom') or '').strip()
        code = (request.form.get('code') or '').strip()
        resp = (request.form.get('responsable') or '').strip()
        if not nom:
            flash("Nom obligatoire", "warning")
        else:
            conn = _db()
            c = conn.cursor()
            try:
                c.execute("""INSERT INTO services (nom, code, responsable, actif, created_at)
                             VALUES (?,?,?,1,?)""",
                          (nom, code, resp, datetime.now().isoformat()))
                conn.commit()
                _log('CREATE_SERVICE', f"Service '{nom}' créé")
                conn.close()
                flash("Service créé", "success")
                return redirect('/services')
            except Exception as e:
                conn.close()
                flash(f"Erreur : {e}", "danger")

    content = """
    <div class="page-header"><div><h2><i class="fas fa-building"></i> Nouveau service</h2></div>
      <a href="/services" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a></div>
    <div class="card"><form method="POST">
      <div class="form-grid">
        <div class="form-group"><label>Nom *</label><input name="nom" required placeholder="Ex: Direction Financière"></div>
        <div class="form-group"><label>Code</label><input name="code" placeholder="Ex: DAF"></div>
        <div class="form-group form-full"><label>Responsable</label><input name="responsable"></div>
      </div>
      <button class="btn btn-primary" style="margin-top:20px"><i class="fas fa-check"></i> Créer</button>
    </form></div>"""
    return _render(content, active='admin', title='Nouveau service')


@crud_bp.route('/services/<int:sid>/supprimer')
@_auth_required
def services_delete(sid):
    if not _can_validate():
        flash("Droits insuffisants", "danger")
        return redirect('/services')
    conn = _db()
    c = conn.cursor()
    c.execute("UPDATE services SET actif=0 WHERE id=?", (sid,))
    conn.commit()
    _log('DELETE_SERVICE', f"Service id={sid} désactivé")
    conn.close()
    flash("Service supprimé", "success")
    return redirect('/services')


# ================================================================
# ==================== UTILISATEURS ====================
# ================================================================
@crud_bp.route('/utilisateurs')
@_auth_required
@_admin_required
def utilisateurs_list():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT u.*, u.service AS service_nom
                 FROM utilisateurs u
                 ORDER BY u.nom, u.prenom""")
    users = c.fetchall()
    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-user-shield"></i> Utilisateurs</h2>
        <div class="page-subtitle">{len(users)} utilisateur(s)</div></div>
      <a href="/utilisateurs/nouveau" class="btn btn-primary"><i class="fas fa-user-plus"></i> Nouveau</a>
    </div>
    <div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Utilisateur</th><th>Email</th><th>Rôle</th><th>Service</th><th>Actif</th><th>Actions</th></tr></thead>
      <tbody>"""
    for u in users:
        content += f"""
        <tr>
          <td><strong>{u['prenom'] or ''} {u['nom'] or ''}</strong>
              <div style="font-size:0.75rem;color:#94a3b8">@{u['username'] or ''}</div></td>
          <td>{u['email'] or '-'}</td>
          <td><span class="badge badge-role-{u['role']}">{u['role']}</span></td>
          <td>{u['service_nom'] or '-'}</td>
          <td>{'✅' if u['actif'] else '❌'}</td>
          <td style="white-space:nowrap">
            <a href="/utilisateurs/{u['id']}/modifier" class="btn btn-warning btn-sm"><i class="fas fa-pen"></i></a>
            <a href="/utilisateurs/{u['id']}/supprimer" class="btn btn-danger btn-sm" onclick="return confirm(&#39;Désactiver cet utilisateur ?&#39;)"><i class="fas fa-user-slash"></i></a>
          </td>
        </tr>"""
    if not users:
        content += '<tr><td colspan="6" class="empty"><i class="fas fa-users"></i><br>Aucun utilisateur</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='utilisateurs', title='Utilisateurs')


@crud_bp.route('/utilisateurs/nouveau', methods=['GET', 'POST'])
@_auth_required
@_admin_required
def utilisateurs_new():
    conn = _db()
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip().lower()
        email = (request.form.get('email') or '').strip()
        nom = (request.form.get('nom') or '').strip()
        prenom = (request.form.get('prenom') or '').strip()
        role = request.form.get('role') or 'lecteur'
        service_nom = (request.form.get('service') or '').strip() or None
        password = request.form.get('password') or ''
        if not username or not password:
            flash("Username et mot de passe obligatoires", "warning")
        else:
            try:
                import hashlib as _h
                pwd_hash = _h.sha256(password.encode()).hexdigest()
                c = conn.cursor()
                c.execute("""INSERT INTO utilisateurs
                             (username, email, nom, prenom, role, service, password_hash, actif, created_at)
                             VALUES (?,?,?,?,?,?,?,1,?)""",
                          (username, email, nom, prenom, role, service_nom, pwd_hash,
                           datetime.now().isoformat()))
                conn.commit()
                _log('CREATE_USER', f"Utilisateur '{username}' créé (rôle={role})")
                conn.close()
                flash("Utilisateur créé", "success")
                return redirect('/utilisateurs')
            except Exception as e:
                flash(f"Erreur : {e}", "danger")

    services = _list_services(conn)
    conn.close()
    opt_srv = '<option value="">—</option>'
    for s in services:
        opt_srv += f'<option value="{s["nom"]}">{s["nom"]}</option>'

    roles = ['admin', 'archiviste', 'contributeur', 'lecteur', 'auditeur']
    opt_roles = ''.join(f'<option value="{r}">{r}</option>' for r in roles)

    content = f"""
    <div class="page-header"><div><h2><i class="fas fa-user-plus"></i> Nouvel utilisateur</h2></div>
      <a href="/utilisateurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a></div>
    <div class="card"><form method="POST">
      <div class="form-grid">
        <div class="form-group"><label>Username *</label><input name="username" required></div>
        <div class="form-group"><label>Email</label><input type="email" name="email"></div>
        <div class="form-group"><label>Nom</label><input name="nom"></div>
        <div class="form-group"><label>Prénom</label><input name="prenom"></div>
        <div class="form-group"><label>Rôle *</label><select name="role">{opt_roles}</select></div>
        <div class="form-group"><label>Service</label><select name="service">{opt_srv}</select></div>
        <div class="form-group form-full"><label>Mot de passe *</label><input type="password" name="password" required minlength="6"></div>
      </div>
      <button class="btn btn-primary" style="margin-top:20px"><i class="fas fa-check"></i> Créer</button>
    </form></div>"""
    return _render(content, active='utilisateurs', title='Nouvel utilisateur')


@crud_bp.route('/utilisateurs/<int:uid>/modifier', methods=['GET', 'POST'])
@_auth_required
@_admin_required
def utilisateurs_edit(uid):
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM utilisateurs WHERE id=?", (uid,))
    u = c.fetchone()
    if not u:
        conn.close()
        return redirect('/utilisateurs')

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        nom = (request.form.get('nom') or '').strip()
        prenom = (request.form.get('prenom') or '').strip()
        role = request.form.get('role') or u['role']
        service_nom = (request.form.get('service') or '').strip() or None
        actif = 1 if request.form.get('actif') else 0
        password = request.form.get('password') or ''
        if password:
            import hashlib as _h
            pwd_hash = _h.sha256(password.encode()).hexdigest()
            c.execute("""UPDATE utilisateurs SET email=?, nom=?, prenom=?, role=?,
                         service=?, actif=?, password_hash=? WHERE id=?""",
                      (email, nom, prenom, role, service_nom, actif, pwd_hash, uid))
        else:
            c.execute("""UPDATE utilisateurs SET email=?, nom=?, prenom=?, role=?,
                         service=?, actif=? WHERE id=?""",
                      (email, nom, prenom, role, service_nom, actif, uid))
        conn.commit()
        _log('UPDATE_USER', f"Utilisateur id={uid} modifié")
        flash("Utilisateur mis à jour", "success")
        conn.close()
        return redirect('/utilisateurs')

    services = _list_services(conn)
    conn.close()
    opt_srv = '<option value="">—</option>'
    for s in services:
        sel = 'selected' if u['service'] == s['nom'] else ''
        opt_srv += f'<option value="{s["nom"]}" {sel}>{s["nom"]}</option>'

    roles = ['admin', 'archiviste', 'contributeur', 'lecteur', 'auditeur']
    opt_roles = ''.join(f'<option value="{r}" {"selected" if u["role"]==r else ""}>{r}</option>' for r in roles)

    content = f"""
    <div class="page-header"><div><h2><i class="fas fa-pen"></i> Modifier utilisateur</h2></div>
      <a href="/utilisateurs" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a></div>
    <div class="card"><form method="POST">
      <div class="form-grid">
        <div class="form-group"><label>Username</label><input value="{u['username'] or ''}" disabled></div>
        <div class="form-group"><label>Email</label><input type="email" name="email" value="{u['email'] or ''}"></div>
        <div class="form-group"><label>Nom</label><input name="nom" value="{u['nom'] or ''}"></div>
        <div class="form-group"><label>Prénom</label><input name="prenom" value="{u['prenom'] or ''}"></div>
        <div class="form-group"><label>Rôle</label><select name="role">{opt_roles}</select></div>
        <div class="form-group"><label>Service</label><select name="service">{opt_srv}</select></div>
        <div class="form-group form-full">
          <label>Nouveau mot de passe (laisser vide pour ne pas changer)</label>
          <input type="password" name="password" minlength="6">
        </div>
        <div class="form-group form-full">
          <label><input type="checkbox" name="actif" {'checked' if u['actif'] else ''}> Compte actif</label>
        </div>
      </div>
      <button class="btn btn-primary" style="margin-top:20px"><i class="fas fa-check"></i> Enregistrer</button>
    </form></div>"""
    return _render(content, active='utilisateurs', title='Modifier utilisateur')


@crud_bp.route('/utilisateurs/<int:uid>/supprimer')
@_auth_required
@_admin_required
def utilisateurs_delete(uid):
    if uid == (current_user.id if hasattr(current_user, 'id') else None):
        flash("Impossible de désactiver votre propre compte", "warning")
        return redirect('/utilisateurs')
    conn = _db()
    c = conn.cursor()
    c.execute("UPDATE utilisateurs SET actif=0 WHERE id=?", (uid,))
    conn.commit()
    _log('DELETE_USER', f"Utilisateur id={uid} désactivé")
    conn.close()
    flash("Utilisateur désactivé", "success")
    return redirect('/utilisateurs')


# ================================================================
# ==================== API JSON (pour AJAX) ====================
# ================================================================
@crud_bp.route('/api/dossiers/tree')
@_auth_required
def api_dossiers_tree():
    conn = _db()
    c = conn.cursor()
    c.execute("SELECT id, nom, parent_id FROM dossiers WHERE actif=1 ORDER BY nom")
    rows = c.fetchall()
    conn.close()

    nodes = {r['id']: {'id': r['id'], 'nom': r['nom'], 'parent_id': r['parent_id'], 'children': []} for r in rows}
    roots = []
    for n in nodes.values():
        if n['parent_id'] and n['parent_id'] in nodes:
            nodes[n['parent_id']]['children'].append(n)
        else:
            roots.append(n)
    return jsonify(roots)
