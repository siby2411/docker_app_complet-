"""
📄 Omega Agro-Industrie — Génération PDF
Factures contrats · Factures exports · Rapports PDF
"""
from flask import Blueprint, send_file, redirect, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import io

pdf_bp = Blueprint('pdf_factures', __name__)
_deps = {}


def init_pdf(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(pdf_bp)
    print("[PDF] ✅ Module PDF enregistré")


def _db():
    return _deps['get_db']()


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


def _header(c, w, h, titre, sous_titre=""):
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    c.setFillColor(colors.HexColor('#1e40af'))
    c.rect(0, h - 30*mm, w, 30*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(15*mm, h - 15*mm, "OMEGA AGRO-INDUSTRIE")
    c.setFont('Helvetica', 9)
    c.drawString(15*mm, h - 21*mm, "Prolongement SM10 AGRO — Sadio Mané 🇸🇳")
    c.setFont('Helvetica-Bold', 13)
    c.drawRightString(w - 15*mm, h - 15*mm, titre)
    if sous_titre:
        c.setFont('Helvetica', 9)
        c.drawRightString(w - 15*mm, h - 21*mm, sous_titre)


def _footer(c, w):
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    c.setFillColor(colors.HexColor('#f9fafb'))
    c.rect(0, 0, w, 18*mm, fill=1, stroke=0)
    c.setFillColor(colors.grey)
    c.setFont('Helvetica', 7)
    c.drawString(15*mm, 12*mm, "OMEGA AGRO-INDUSTRIE · APIX Exonération 5 ans · Export UE certifié")
    c.drawString(15*mm, 8*mm, "Tél : +221 XX XXX XX XX · Email : contact@omega-agro.sn")
    c.drawRightString(w - 15*mm, 12*mm, f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    c.drawRightString(w - 15*mm, 8*mm, "HACCP · ISO 22000 · GlobalG.A.P.")


# ═══════════════════════════════════════════════════════════════
# 📄 FACTURE CONTRAT
# ═══════════════════════════════════════════════════════════════

@pdf_bp.route('/contrats/<int:cid>/facture.pdf')
@login_required
def facture_contrat(cid):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    db = _db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, pr.nom AS producteur_nom, pr.region, pr.telephone,
               pf.nom AS produit_nom, pf.unite
        FROM contrats_achat c
        LEFT JOIN producteurs pr ON pr.id = c.producteur_id
        LEFT JOIN produits_finis pf ON pf.id = c.produit_fini_id
        WHERE c.id = ?
    """, (cid,))
    ct = _row(cur)
    if not ct:
        flash('❌ Contrat introuvable', 'error')
        return redirect('/contrats')

    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=A4)
    w, h = A4

    _header(c, w, h, "FACTURE CONTRAT", ct.get('numero') or f'CTR-{cid}')

    y = h - 45*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(15*mm, y, "PRODUCTEUR")
    c.setFont('Helvetica', 10)
    y -= 6*mm
    c.drawString(15*mm, y, f"{ct.get('producteur_nom') or '—'}")
    y -= 5*mm
    c.drawString(15*mm, y, f"Région : {ct.get('region') or '—'}")
    y -= 5*mm
    c.drawString(15*mm, y, f"Téléphone : {ct.get('telephone') or '—'}")

    y = h - 45*mm
    c.setFont('Helvetica-Bold', 11)
    c.drawString(110*mm, y, "DÉTAILS")
    c.setFont('Helvetica', 10)
    y -= 6*mm
    c.drawString(110*mm, y, f"Date : {ct.get('date_signature') or '—'}")
    y -= 5*mm
    c.drawString(110*mm, y, f"Statut : {ct.get('statut') or '—'}")

    # Tableau
    y -= 20*mm
    c.setFillColor(colors.HexColor('#1f2937'))
    c.rect(15*mm, y - 8*mm, w - 30*mm, 8*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(18*mm, y - 5*mm, "Produit")
    c.drawString(80*mm, y - 5*mm, "Quantité")
    c.drawString(115*mm, y - 5*mm, "Prix unitaire")
    c.drawString(155*mm, y - 5*mm, "Montant")

    y -= 14*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica', 10)
    c.drawString(18*mm, y, f"{ct.get('produit_nom') or '—'}")
    c.drawString(80*mm, y, f"{ct.get('quantite') or 0} kg")
    c.drawString(115*mm, y, f"{ct.get('prix_unitaire') or 0:,.0f} FCFA/kg")
    c.drawString(155*mm, y, f"{ct.get('montant_total') or 0:,.0f} FCFA")

    # Total
    y -= 15*mm
    c.setFillColor(colors.HexColor('#f0fdf4'))
    c.rect(110*mm, y - 5*mm, w - 125*mm, 12*mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#047857'))
    c.setFont('Helvetica-Bold', 12)
    c.drawString(115*mm, y, "TOTAL")
    c.drawRightString(w - 18*mm, y, f"{ct.get('montant_total') or 0:,.0f} FCFA")

    # Mentions
    y -= 25*mm
    c.setFillColor(colors.grey)
    c.setFont('Helvetica', 8)
    c.drawString(15*mm, y, "Contrat sécurisé OMEGA AGRO-INDUSTRIE — Traçabilité QR du champ à l'assiette")
    y -= 5*mm
    c.drawString(15*mm, y, "Certifications : HACCP · ISO 22000 · GlobalG.A.P. · Bio UE 2018/848")

    _footer(c, w)
    c.showPage()
    c.save()
    pdf_buf.seek(0)

    _log('PDF_FACTURE_CONTRAT', f'Contrat #{cid}', 'contrats_achat', cid)
    return send_file(pdf_buf, mimetype='application/pdf',
                     download_name=f'facture_contrat_{ct.get("numero") or cid}.pdf')


# ═══════════════════════════════════════════════════════════════
# 📄 FACTURE EXPORT
# ═══════════════════════════════════════════════════════════════

@pdf_bp.route('/exports/<int:eid>/facture.pdf')
@login_required
def facture_export(eid):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    db = _db()
    cur = db.cursor()
    cur.execute("""
        SELECT e.*, pf.nom AS produit_nom, pf.unite
        FROM exports e
        LEFT JOIN produits_finis pf ON pf.id = e.produit_fini_id
        WHERE e.id = ?
    """, (eid,))
    ex = _row(cur)
    if not ex:
        flash('❌ Export introuvable', 'error')
        return redirect('/exports')

    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=A4)
    w, h = A4

    _header(c, w, h, "FACTURE EXPORT", ex.get('numero') or f'EXP-{eid}')

    y = h - 45*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(15*mm, y, "DESTINATION")
    c.setFont('Helvetica', 10)
    y -= 6*mm
    c.drawString(15*mm, y, f"{ex.get('destination') or '—'}")
    y -= 5*mm
    c.drawString(15*mm, y, f"Date : {ex.get('date_export') or '—'}")

    y = h - 45*mm
    c.setFont('Helvetica-Bold', 11)
    c.drawString(110*mm, y, "CERTIFICATIONS")
    c.setFont('Helvetica', 10)
    y -= 6*mm
    c.drawString(110*mm, y, f"UE : {'✅' if ex.get('certification_ue') else '❌'}")
    y -= 5*mm
    c.drawString(110*mm, y, f"USAID : {'✅' if ex.get('certification_usaid') else '❌'}")

    # Tableau
    y -= 20*mm
    c.setFillColor(colors.HexColor('#1f2937'))
    c.rect(15*mm, y - 8*mm, w - 30*mm, 8*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(18*mm, y - 5*mm, "Produit")
    c.drawString(90*mm, y - 5*mm, "Quantité")
    c.drawString(140*mm, y - 5*mm, "Valeur")

    y -= 14*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica', 10)
    c.drawString(18*mm, y, f"{ex.get('produit_nom') or '—'}")
    c.drawString(90*mm, y, f"{ex.get('quantite') or 0:,.1f} kg")
    c.drawString(140*mm, y, f"{ex.get('valeur_fcfa') or 0:,.0f} FCFA")

    y -= 15*mm
    c.setFillColor(colors.HexColor('#eff6ff'))
    c.rect(110*mm, y - 5*mm, w - 125*mm, 12*mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#1e40af'))
    c.setFont('Helvetica-Bold', 12)
    c.drawString(115*mm, y, "TOTAL")
    c.drawRightString(w - 18*mm, y, f"{ex.get('valeur_fcfa') or 0:,.0f} FCFA")

    y -= 25*mm
    c.setFillColor(colors.grey)
    c.setFont('Helvetica', 8)
    c.drawString(15*mm, y, "Export conforme UE — Traçabilité QR disponible sur /exports/tracabilite/<lot>")
    y -= 5*mm
    c.drawString(15*mm, y, "Normes : HACCP · ISO 22000 · GlobalG.A.P. · Bio UE 2018/848 · Résidus pesticides")

    _footer(c, w)
    c.showPage()
    c.save()
    pdf_buf.seek(0)

    _log('PDF_FACTURE_EXPORT', f'Export #{eid}', 'exports', eid)
    return send_file(pdf_buf, mimetype='application/pdf',
                     download_name=f'facture_export_{ex.get("numero") or eid}.pdf')


# ═══════════════════════════════════════════════════════════════
# 📄 RAPPORT SYNTHÈSE PDF
# ═══════════════════════════════════════════════════════════════

@pdf_bp.route('/rapports/synthese.pdf')
@login_required
def rapport_synthese_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    db = _db()
    cur = db.cursor()

    def sc(sql, default=0):
        try:
            cur.execute(sql)
            r = cur.fetchone()
            return r[0] if r and r[0] is not None else default
        except Exception:
            return default

    kpis = [
        ('👨‍🌾 Producteurs', sc("SELECT COUNT(*) FROM producteurs")),
        ('🌾 Récoltes', sc("SELECT COUNT(*) FROM recoltes")),
        ('🏭 OF total', sc("SELECT COUNT(*) FROM ordres_fabrication")),
        ('✅ OF terminés', sc("SELECT COUNT(*) FROM ordres_fabrication WHERE statut='termine'")),
        ('⚙️ Yield moyen %', round(sc("SELECT AVG(rendement) FROM ordres_fabrication WHERE rendement IS NOT NULL", 0) or 0, 1)),
        ('📦 Valeur stocks FCFA', f"{sc('''SELECT COALESCE(SUM(s.quantite*pf.prix_unitaire),0) FROM stocks_produits s LEFT JOIN produits_finis pf ON pf.id=s.produit_fini_id''', 0):,.0f}"),
        ('📄 Montant contrats FCFA', f"{sc('SELECT COALESCE(SUM(montant_total),0) FROM contrats_achat', 0):,.0f}"),
        ('🌍 Valeur exports FCFA', f"{sc('SELECT COALESCE(SUM(valeur_fcfa),0) FROM exports', 0):,.0f}"),
        ('🔬 Contrôles qualité', sc("SELECT COUNT(*) FROM controles_qualite")),
        ('⚠️ Non-conformités', sc("SELECT COUNT(*) FROM non_conformites")),
        ('🔍 Lots tracés', sc("SELECT COUNT(*) FROM tracabilite")),
        ('🎓 Sessions formation', sc("SELECT COUNT(*) FROM sessions_formation")),
    ]

    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=A4)
    w, h = A4

    _header(c, w, h, "RAPPORT SYNTHÈSE", datetime.now().strftime('%d/%m/%Y'))

    y = h - 45*mm
    c.setFillColor(colors.HexColor('#1f2937'))
    c.setFont('Helvetica-Bold', 13)
    c.drawString(15*mm, y, "📊 KPIs OMEGA AGRO-INDUSTRIE")

    y -= 12*mm
    c.setFont('Helvetica', 10)
    for label, val in kpis:
        c.setFillColor(colors.HexColor('#f9fafb'))
        c.rect(15*mm, y - 3*mm, w - 30*mm, 8*mm, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont('Helvetica-Bold', 10)
        c.drawString(18*mm, y, label)
        c.setFont('Helvetica', 11)
        c.setFillColor(colors.HexColor('#1e40af'))
        c.drawRightString(w - 18*mm, y, str(val))
        y -= 10*mm

    y -= 5*mm
    c.setFillColor(colors.HexColor('#f0fdf4'))
    c.rect(15*mm, y - 20*mm, w - 30*mm, 20*mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#047857'))
    c.setFont('Helvetica-Bold', 11)
    c.drawString(18*mm, y - 6*mm, "🌾 Impact projet")
    c.setFont('Helvetica', 9)
    c.setFillColor(colors.black)
    c.drawString(18*mm, y - 12*mm, "• +25% valeur ajoutée locale · 500 unités transformatrices cibles")
    c.drawString(18*mm, y - 17*mm, "• 40% pertes post-récolte adressées · 11,4 Md FCFA investissement")

    _footer(c, w)
    c.showPage()
    c.save()
    pdf_buf.seek(0)

    _log('PDF_RAPPORT', 'Rapport synthèse', 'rapports')
    return send_file(pdf_buf, mimetype='application/pdf',
                     download_name=f'rapport_omega_agro_{datetime.now().strftime("%Y%m%d")}.pdf')


@pdf_bp.route('/api/pdf/info')
@login_required
def api_pdf_info():
    return jsonify({
        'endpoints': [
            '/contrats/<id>/facture.pdf',
            '/exports/<id>/facture.pdf',
            '/rapports/synthese.pdf',
            '/exports/tracabilite/<lot>/etiquette.pdf'
        ],
        'library': 'reportlab 4.0.7',
        'formats': ['A4', 'A6'],
    })
