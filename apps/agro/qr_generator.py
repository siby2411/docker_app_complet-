"""
📱 Omega Agro-Industrie — Générateur de QR codes
Traçabilité champ → assiette · Étiquettes PDF
"""
from flask import Blueprint, send_file, jsonify, request, redirect, flash
from flask_login import login_required, current_user
from datetime import datetime
import qrcode
import io

qr_bp = Blueprint('qr_generator', __name__)
_deps = {}


def init_qr(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(qr_bp)
    print("[QR] ✅ Module QR codes enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='export', title='QR'):
    return _deps['render_page'](content, active=active, page_title=title)


def _rows(cur):
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _row(cur):
    cols = [c[0] for c in cur.description]
    r = cur.fetchone()
    return dict(zip(cols, r)) if r else None


def _log(action, details='', entity=None, entity_id=None):
    try:
        uid = current_user.id if (current_user and current_user.is_authenticated) else None
        _deps['log_action'](uid, action, details, entity=entity, entity_id=entity_id)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# 📱 QR CODE IMAGE
# ═══════════════════════════════════════════════════════════════

def _generate_qr(data, size=10):
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=size,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f766e", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


@qr_bp.route('/qr/<lot>.png')
def qr_image(lot):
    """QR code image pour un lot — accessible sans login (étiquette publique)."""
    qr_data = f"OMEGA-AGRO|LOT:{lot}"
    buf = _generate_qr(qr_data, size=10)
    return send_file(buf, mimetype='image/png',
                     download_name=f'qr_{lot}.png')


@qr_bp.route('/qr/url.png')
def qr_url():
    """QR code pour l'URL courante (utilisé dans le portail)."""
    target = request.args.get('url', 'http://localhost:9016/portail/public')
    buf = _generate_qr(target, size=8)
    return send_file(buf, mimetype='image/png')


@qr_bp.route('/exports/tracabilite/<lot>/qr')
@login_required
def tracabilite_qr(lot):
    """Page fiche traçabilité enrichie avec QR code."""
    db = _db()
    cur = db.cursor()
    try:
        cur.execute("""
            SELECT t.*, pf.nom AS produit_nom, pf.unite,
                   pr.nom AS producteur_nom, pr.region,
                   r.date_recolte, r.quantite AS qte_recolte
            FROM tracabilite t
            LEFT JOIN produits_finis pf ON pf.id = t.produit_fini_id
            LEFT JOIN producteurs pr ON pr.id = t.producteur_id
            LEFT JOIN recoltes r ON r.id = t.recolte_id
            WHERE t.numero_lot = ? OR t.qr_code = ?
            LIMIT 1
        """, (lot, lot))
        t = _row(cur)
    except Exception as e:
        t = None
        flash(f'Erreur : {e}', 'error')

    if not t:
        flash(f'❌ Lot {lot} introuvable', 'error')
        return redirect('/exports')

    qr_url = f"/qr/{lot}.png"
    tracabilite_url = f"http://localhost:9016/exports/tracabilite/{lot}"

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">🔍 Fiche traçabilité — Lot {lot}</h1>
      <a href="/exports" style="background:#e5e7eb;color:#374151;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">← Exports</a>
    </div>

    <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px">
      <div style="background:#fff;padding:28px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
        <div style="background:linear-gradient(135deg,#10b981,#047857);color:#fff;padding:18px;border-radius:10px;margin-bottom:20px">
          <div style="font-size:13px;opacity:.9">🌾 Du champ à l'assiette — Conforme UE</div>
          <div style="font-size:24px;font-weight:700;margin-top:6px">{t.get('produit_nom') or '—'}</div>
          <div style="font-size:13px;opacity:.9">Lot {t.get('numero_lot') or lot}</div>
        </div>

        <table style="width:100%;border-collapse:collapse">
          <tr><td style="padding:12px;background:#f9fafb;font-weight:600;width:220px">🔢 N° lot</td><td style="padding:12px">{t.get('numero_lot') or '—'}</td></tr>
          <tr><td style="padding:12px;background:#f9fafb;font-weight:600">📦 Produit fini</td><td style="padding:12px">{t.get('produit_nom') or '—'} ({t.get('unite') or 'u'})</td></tr>
          <tr><td style="padding:12px;background:#f9fafb;font-weight:600">👨‍🌾 Producteur</td><td style="padding:12px">{t.get('producteur_nom') or '—'}</td></tr>
          <tr><td style="padding:12px;background:#f9fafb;font-weight:600">🗺 Région</td><td style="padding:12px">{t.get('region') or '—'}</td></tr>
          <tr><td style="padding:12px;background:#f9fafb;font-weight:600">🌾 Date récolte</td><td style="padding:12px">{t.get('date_recolte') or '—'}</td></tr>
          <tr><td style="padding:12px;background:#f9fafb;font-weight:600">⚖️ Quantité récoltée</td><td style="padding:12px">{t.get('qte_recolte') or 0} kg</td></tr>
          <tr><td style="padding:12px;background:#f9fafb;font-weight:600">📅 Créé le</td><td style="padding:12px">{t.get('created_at') or '—'}</td></tr>
          <tr><td style="padding:12px;background:#f9fafb;font-weight:600">✅ Statut</td><td style="padding:12px"><span style="background:#10b981;color:#fff;padding:3px 10px;border-radius:12px;font-size:12px">{t.get('statut') or 'OK'}</span></td></tr>
        </table>

        <div style="margin-top:22px;padding:16px;background:#f0fdf4;border-left:4px solid #10b981;border-radius:8px">
          <strong>✅ Conformité UE :</strong> HACCP · ISO 22000 · GlobalG.A.P. · Bio UE 2018/848
        </div>
      </div>

      <div style="background:#fff;padding:28px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.1);text-align:center">
        <h3 style="margin-top:0;color:#1f2937">📱 QR Code</h3>
        <img src="{qr_url}" alt="QR Lot {lot}" style="width:100%;max-width:260px;border:2px solid #e5e7eb;border-radius:12px">
        <div style="margin-top:16px">
          <a href="{qr_url}" download style="display:inline-block;background:#3b82f6;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;font-size:13px">⬇ Télécharger PNG</a>
        </div>
        <div style="margin-top:20px;padding:12px;background:#f9fafb;border-radius:8px;font-size:12px;color:#6b7280">
          Scannez pour consulter<br>
          <code style="font-size:11px">{tracabilite_url}</code>
        </div>
        <div style="margin-top:14px">
          <a href="/exports/tracabilite/{lot}/etiquette.pdf" style="display:inline-block;background:#10b981;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;font-size:13px">🖨 Étiquette PDF</a>
        </div>
      </div>
    </div>
    """
    return _render(content, active='export', title=f'Traçabilité {lot}')


# ═══════════════════════════════════════════════════════════════
# 📄 ÉTIQUETTE PDF avec QR
# ═══════════════════════════════════════════════════════════════

@qr_bp.route('/exports/tracabilite/<lot>/etiquette.pdf')
@login_required
def etiquette_pdf(lot):
    from reportlab.lib.pagesizes import A6
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.lib import colors

    db = _db()
    cur = db.cursor()
    cur.execute("""
        SELECT t.*, pf.nom AS produit_nom, pf.unite,
               pr.nom AS producteur_nom, pr.region,
               r.date_recolte
        FROM tracabilite t
        LEFT JOIN produits_finis pf ON pf.id = t.produit_fini_id
        LEFT JOIN producteurs pr ON pr.id = t.producteur_id
        LEFT JOIN recoltes r ON r.id = t.recolte_id
        WHERE t.numero_lot = ? OR t.qr_code = ?
        LIMIT 1
    """, (lot, lot))
    t = _row(cur)
    if not t:
        flash('❌ Lot introuvable', 'error')
        return redirect('/exports')

    # Générer QR
    qr_img = qrcode.make(f"OMEGA-AGRO|LOT:{lot}")
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format='PNG')
    qr_buf.seek(0)

    # Générer PDF A6
    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=A6)
    w, h = A6  # 105 x 148 mm

    # Bandeau vert
    c.setFillColor(colors.HexColor('#10b981'))
    c.rect(0, h - 22*mm, w, 22*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(8*mm, h - 10*mm, "OMEGA AGRO-INDUSTRIE")
    c.setFont('Helvetica', 8)
    c.drawString(8*mm, h - 15*mm, "Traçabilité — Du champ à l'assiette")

    # QR code
    qr_size = 45*mm
    qr_x = w - qr_size - 8*mm
    qr_y = h - 22*mm - qr_size - 8*mm
    c.drawImage(ImageReader(qr_buf), qr_x, qr_y, qr_size, qr_size)

    # Infos texte
    c.setFillColor(colors.black)
    y = h - 30*mm
    c.setFont('Helvetica-Bold', 9)
    c.drawString(8*mm, y, f"LOT : {t.get('numero_lot') or lot}")
    y -= 6*mm
    c.setFont('Helvetica', 8)
    c.drawString(8*mm, y, f"Produit : {t.get('produit_nom') or '—'}")
    y -= 5*mm
    c.drawString(8*mm, y, f"Producteur : {t.get('producteur_nom') or '—'}")
    y -= 5*mm
    c.drawString(8*mm, y, f"Région : {t.get('region') or '—'}")
    y -= 5*mm
    c.drawString(8*mm, y, f"Récolte : {t.get('date_recolte') or '—'}")

    # Conformité bas
    c.setFillColor(colors.HexColor('#f0fdf4'))
    c.rect(8*mm, 12*mm, w - 16*mm, 12*mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#047857'))
    c.setFont('Helvetica-Bold', 7)
    c.drawString(10*mm, 19*mm, "✅ HACCP  |  ISO 22000  |  GlobalG.A.P.  |  Bio UE 2018/848")
    c.setFont('Helvetica', 6)
    c.setFillColor(colors.grey)
    c.drawString(10*mm, 15*mm, f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    c.drawString(10*mm, 8*mm, "OMEGA AGRO-INDUSTRIE — Prolongement SM10 AGRO (Sadio Mané) 🇸🇳")

    c.showPage()
    c.save()
    pdf_buf.seek(0)

    _log('QR_ETIQUETTE', f'Étiquette PDF lot {lot}', 'tracabilite')
    return send_file(pdf_buf, mimetype='application/pdf',
                     download_name=f'etiquette_{lot}.pdf')


@qr_bp.route('/api/qr/stats')
@login_required
def api_qr_stats():
    db = _db()
    cur = db.cursor()
    try:
        cur.execute("SELECT COUNT(*) AS n FROM tracabilite WHERE numero_lot IS NOT NULL")
        r = _row(cur) or {}
    except Exception:
        r = {}
    return jsonify({'lots_avec_qr': r.get('n', 0), 'prefix': 'OMEGA-AGRO|LOT:'})
