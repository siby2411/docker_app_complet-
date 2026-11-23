"""
Omega GED — Portail public
Consultation anonyme des documents publiés non confidentiels
"""
from flask import Blueprint, request, redirect, flash, jsonify
from datetime import datetime

portail_bp = Blueprint('portail', __name__)
_deps = {}


def init_portail(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(portail_bp)
    print("[PORTAIL] ✅ Module Portail enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='portail', title='Portail GED'):
    return _deps['render_page'](content, active=active, page_title=title)


def _fmt(ko):
    return _deps['format_taille'](ko)


@portail_bp.route('/portail')
def portail_index():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT d.*, cat.nom AS cat_nom, cat.couleur AS cat_couleur
                 FROM documents d
                 LEFT JOIN categories cat ON d.categorie_id=cat.id
                 WHERE d.actif=1 AND d.statut='Publié' AND d.confidentiel=0
                 ORDER BY d.date_upload DESC LIMIT 50""")
    docs = c.fetchall()

    c.execute("""SELECT COUNT(*) FROM documents
                 WHERE actif=1 AND statut='Publié' AND confidentiel=0""")
    total = c.fetchone()[0] or 0
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-globe"></i> Portail public</h2>
        <div class="page-subtitle">{total} document(s) publié(s) consultable(s)</div></div>
    </div>
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr><th>Réf</th><th>Titre</th><th>Catégorie</th><th>Taille</th><th>Date</th><th></th></tr></thead>
        <tbody>
    """
    for d in docs:
        content += f"""
        <tr>
          <td><strong>{d['reference']}</strong></td>
          <td>{d['titre'][:60]}</td>
          <td>{d['cat_nom'] or '-'}</td>
          <td>{_fmt(d['fichier_taille_ko'] or 0)}</td>
          <td><small>{d['date_upload'][:10] if d['date_upload'] else '-'}</small></td>
          <td><a href="/documents/{d['id']}/telecharger" class="btn btn-info btn-sm"><i class="fas fa-download"></i></a></td>
        </tr>"""
    if not docs:
        content += '<tr><td colspan="6" class="empty"><i class="fas fa-globe"></i><br>Aucun document public</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='portail', title='Portail public')
