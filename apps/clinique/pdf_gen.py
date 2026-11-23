"""
Génération PDF — Clinique Omega
Factures, Ordonnances, Bulletins d'analyse
Technologie : reportlab (pur Python)
"""
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Tentative d'import QR code
try:
    import qrcode
    QRCODE_OK = True
except ImportError:
    QRCODE_OK = False

# Couleurs Omega
OMEGA_DARK = colors.HexColor('#0a4d68')
OMEGA_BLUE = colors.HexColor('#088395')
OMEGA_CYAN = colors.HexColor('#05bfdb')
OMEGA_LIGHT = colors.HexColor('#f0f7f9')
OMEGA_GRAY = colors.HexColor('#64748b')


def _make_qr_image(data, size=80):
    """Génère un QR code en image reportlab"""
    if not QRCODE_OK:
        return None
    try:
        qr = qrcode.QRCode(version=1, box_size=5, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return Image(buf, width=size, height=size)
    except Exception as e:
        print(f"[PDF] QR error: {e}")
        return None


def _header_footer(canvas, doc, title='Document'):
    """En-tête et pied de page"""
    canvas.saveState()
    width, height = A4

    # Bandeau supérieur
    canvas.setFillColor(OMEGA_DARK)
    canvas.rect(0, height - 80, width, 80, fill=1, stroke=0)
    canvas.setFillColor(OMEGA_CYAN)
    canvas.rect(0, height - 84, width, 4, fill=1, stroke=0)

    # Titre
    canvas.setFillColor(colors.white)
    canvas.setFont('Helvetica-Bold', 20)
    canvas.drawString(20 * mm, height - 30, 'CLINIQUE OMEGA')
    canvas.setFont('Helvetica', 10)
    canvas.drawString(20 * mm, height - 42, 'Plateforme médicale — Dakar, Sénégal')

    # Titre du document
    canvas.setFont('Helvetica-Bold', 14)
    canvas.setFillColor(OMEGA_CYAN)
    canvas.drawRightString(width - 20 * mm, height - 30, title.upper())

    # Pied de page
    canvas.setFillColor(OMEGA_GRAY)
    canvas.setFont('Helvetica', 8)
    canvas.drawString(20 * mm, 15 * mm, 'OMEGA INFORMATIQUE — Solutions digitales médicales')
    canvas.drawRightString(width - 20 * mm, 15 * mm, f'Page {doc.page}')
    canvas.drawCentredString(width / 2, 15 * mm, f'Généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")}')

    canvas.restoreState()


def generer_facture_pdf(facture, patient, lignes):
    """Génère une facture PDF
    facture : dict avec numero, date_emission, montant_total, montant_paye, mode_paiement, statut, observations
    patient : dict avec nom, prenom, numero_dossier, telephone, assurance
    lignes : liste de dict avec designation, quantite, prix_unitaire, montant
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=100, bottomMargin=30 * mm
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('h1', parent=styles['Heading1'], fontSize=16, textColor=OMEGA_DARK, spaceAfter=10)
    h2 = ParagraphStyle('h2', parent=styles['Heading2'], fontSize=12, textColor=OMEGA_BLUE, spaceAfter=8, spaceBefore=12)
    normal = ParagraphStyle('normal', parent=styles['Normal'], fontSize=10)
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8, textColor=OMEGA_GRAY)

    story = []

    # Bloc infos patient + facture
    info_data = [
        [Paragraph('<b>Patient</b>', normal), Paragraph('<b>Facture</b>', normal)],
        [Paragraph(f"{patient.get('nom', '')} {patient.get('prenom', '')}<br/>"
                   f"N° dossier : {patient.get('numero_dossier', '-')}<br/>"
                   f"Tél : {patient.get('telephone', '-')}<br/>"
                   f"Assurance : {patient.get('assurance', 'Aucune')}", normal),
         Paragraph(f"N° : <b>{facture.get('numero', '')}</b><br/>"
                   f"Date : {facture.get('date_emission', '')[:10]}<br/>"
                   f"Statut : <b>{facture.get('statut', '-')}</b><br/>"
                   f"Mode : {facture.get('mode_paiement', '-')}", normal)]
    ]
    info_table = Table(info_data, colWidths=[90 * mm, 80 * mm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), OMEGA_LIGHT),
        ('TEXTCOLOR', (0, 0), (-1, 0), OMEGA_DARK),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    # Table des lignes
    data = [['Désignation', 'Qté', 'P.U.', 'Montant']]
    for l in lignes:
        data.append([
            l.get('designation', ''),
            str(l.get('quantite', 1)),
            f"{l.get('prix_unitaire', 0):,.0f}",
            f"{l.get('montant', 0):,.0f}"
        ])
    t = Table(data, colWidths=[100 * mm, 15 * mm, 30 * mm, 30 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), OMEGA_DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, OMEGA_LIGHT]),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Totaux
    total = float(facture.get('montant_total', 0))
    paye = float(facture.get('montant_paye', 0))
    reste = total - paye

    totaux_data = [
        ['Total à payer', f'{total:,.0f} FCFA'],
        ['Déjà payé', f'{paye:,.0f} FCFA'],
        ['Reste à payer', f'{reste:,.0f} FCFA'],
    ]
    tt = Table(totaux_data, colWidths=[130 * mm, 45 * mm], hAlign='RIGHT')
    tt.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#fee2e2') if reste > 0 else colors.HexColor('#dcfce7')),
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.HexColor('#991b1b') if reste > 0 else colors.HexColor('#166534')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(tt)

    # Observations
    if facture.get('observations'):
        story.append(Spacer(1, 15))
        story.append(Paragraph(f"<b>Observations :</b> {facture['observations']}", small))

    # QR code en bas
    if QRCODE_OK:
        story.append(Spacer(1, 15))
        qr_data = f"FAC-{facture.get('numero', '')}|{total:.0f}|{patient.get('numero_dossier', '')}"
        qr_img = _make_qr_image(qr_data, size=70)
        if qr_img:
            qr_table = Table([[qr_img, Paragraph('Scannez pour vérifier', small)]], colWidths=[80, 100])
            qr_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
            story.append(qr_table)

    doc.build(story, onFirstPage=lambda c, d: _header_footer(c, d, 'Facture'),
                       onLaterPages=lambda c, d: _header_footer(c, d, 'Facture'))
    return buf.getvalue()


def generer_ordonnance_pdf(consultation, patient, medecin, prescriptions):
    """Génère une ordonnance PDF"""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=100, bottomMargin=30 * mm
    )

    styles = getSampleStyleSheet()
    h2 = ParagraphStyle('h2', parent=styles['Heading2'], fontSize=12, textColor=OMEGA_BLUE, spaceAfter=8, spaceBefore=12)
    normal = ParagraphStyle('normal', parent=styles['Normal'], fontSize=10, leading=14)
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8, textColor=OMEGA_GRAY)

    story = []

    # Patient + Médecin
    info = [
        [Paragraph(f"<b>Patient :</b> {patient.get('nom', '')} {patient.get('prenom', '')}", normal),
         Paragraph(f"<b>Date :</b> {datetime.now().strftime('%d/%m/%Y')}", normal)],
        [Paragraph(f"<b>Âge :</b> {patient.get('age', '-')} ans | <b>Sexe :</b> {patient.get('sexe', '-')}", normal),
         Paragraph(f"<b>Dossier :</b> {patient.get('numero_dossier', '-')}", normal)],
        [Paragraph(f"<b>Médecin :</b> Dr {medecin.get('nom', '')} {medecin.get('prenom', '')}", normal),
         Paragraph(f"<b>Spécialité :</b> {medecin.get('specialite', '-')}", normal)],
        [Paragraph(f"<b>Diagnostic :</b> {consultation.get('diagnostic_principal', '-')}", normal), ''],
    ]
    t = Table(info, colWidths=[95 * mm, 75 * mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), OMEGA_LIGHT),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    story.append(Paragraph('<b>PRESCRIPTION</b>', h2))
    story.append(Spacer(1, 5))

    # Prescriptions numérotées
    for i, pr in enumerate(prescriptions, 1):
        story.append(Paragraph(
            f"<b>{i}. {pr.get('medicament', '')}</b> {pr.get('dosage', '')}<br/>"
            f"&nbsp;&nbsp;&nbsp;Posologie : {pr.get('posologie', '-')} — Durée : {pr.get('duree', '-')}<br/>"
            f"&nbsp;&nbsp;&nbsp;<i>{pr.get('instructions', '')}</i>",
            normal
        ))
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 30))
    story.append(Paragraph('Signature et cachet du médecin', small))
    story.append(Spacer(1, 40))
    story.append(Paragraph('_' * 50, small))

    # QR code
    if QRCODE_OK:
        qr_data = f"ORD-{consultation.get('numero', '')}|{patient.get('numero_dossier', '')}"
        qr_img = _make_qr_image(qr_data, size=60)
        if qr_img:
            story.append(Spacer(1, 15))
            story.append(qr_img)

    doc.build(story, onFirstPage=lambda c, d: _header_footer(c, d, 'Ordonnance'),
                       onLaterPages=lambda c, d: _header_footer(c, d, 'Ordonnance'))
    return buf.getvalue()


def generer_bulletin_analyse_pdf(analyse, patient, resultats):
    """Génère un bulletin d'analyse PDF"""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=100, bottomMargin=30 * mm
    )

    styles = getSampleStyleSheet()
    normal = ParagraphStyle('normal', parent=styles['Normal'], fontSize=10, leading=14)
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8, textColor=OMEGA_GRAY)
    h2 = ParagraphStyle('h2', parent=styles['Heading2'], fontSize=12, textColor=OMEGA_BLUE, spaceAfter=8)

    story = []

    # Patient
    info = [
        [Paragraph(f"<b>Patient :</b> {patient.get('nom', '')} {patient.get('prenom', '')}", normal),
         Paragraph(f"<b>N° analyse :</b> {analyse.get('numero', '-')}", normal)],
        [Paragraph(f"<b>Dossier :</b> {patient.get('numero_dossier', '-')}", normal),
         Paragraph(f"<b>Date :</b> {analyse.get('date_analyse', '')[:10]}", normal)],
        [Paragraph(f"<b>Type :</b> {analyse.get('type_analyse', '-')}", normal),
         Paragraph(f"<b>Statut :</b> {analyse.get('statut', '-')}", normal)],
    ]
    t = Table(info, colWidths=[95 * mm, 75 * mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), OMEGA_LIGHT),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # Résultats
    story.append(Paragraph('<b>RÉSULTATS</b>', h2))
    data = [['Paramètre', 'Résultat', 'Unité', 'Valeurs normales', 'Interprétation']]
    for r in resultats:
        data.append([
            r.get('parametre', ''),
            r.get('resultat', ''),
            r.get('unite', ''),
            r.get('valeurs_normales', '-'),
            r.get('interpretation', '-'),
        ])
    tt = Table(data, colWidths=[50 * mm, 30 * mm, 20 * mm, 40 * mm, 30 * mm])
    tt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), OMEGA_DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, OMEGA_LIGHT]),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    story.append(tt)

    # Commentaire
    if analyse.get('commentaire'):
        story.append(Spacer(1, 15))
        story.append(Paragraph(f"<b>Commentaire :</b> {analyse['commentaire']}", normal))

    # QR
    if QRCODE_OK:
        story.append(Spacer(1, 20))
        qr_data = f"LAB-{analyse.get('numero', '')}"
        qr_img = _make_qr_image(qr_data, size=60)
        if qr_img:
            story.append(qr_img)

    doc.build(story, onFirstPage=lambda c, d: _header_footer(c, d, 'Bulletin analyse'),
                       onLaterPages=lambda c, d: _header_footer(c, d, 'Bulletin analyse'))
    return buf.getvalue()


def generer_bon_hospitalisation_pdf(hopital, patient, medecin, salle):
    """Génère un bon d'hospitalisation PDF"""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=100, bottomMargin=30 * mm
    )

    styles = getSampleStyleSheet()
    normal = ParagraphStyle('normal', parent=styles['Normal'], fontSize=11, leading=16)
    h2 = ParagraphStyle('h2', parent=styles['Heading2'], fontSize=13, textColor=OMEGA_BLUE, spaceAfter=10)

    story = []
    story.append(Paragraph('BON D\'HOSPITALISATION', h2))
    story.append(Spacer(1, 10))

    info = [
        ['Patient', f"{patient.get('nom', '')} {patient.get('prenom', '')}"],
        ['N° dossier', patient.get('numero_dossier', '-')],
        ['N° hospitalisation', hopital.get('numero', '-')],
        ['Date entrée', hopital.get('date_entree', '')[:16]],
        ['Motif', hopital.get('motif', '-')],
        ['Diagnostic', hopital.get('diagnostic', '-')],
        ['Médecin référent', f"Dr {medecin.get('nom', '')} {medecin.get('prenom', '')}"],
        ['Chambre', f"{salle.get('nom', '-')} ({salle.get('batiment', '-')} - Étage {salle.get('etage', '-')})"],
        ['Lit', hopital.get('lit_numero', '-')],
        ['Coût journalier', f"{hopital.get('cout_journalier', 0):,.0f} FCFA"],
    ]
    t = Table(info, colWidths=[60 * mm, 110 * mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (0, -1), OMEGA_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t)

    story.append(Spacer(1, 30))
    story.append(Paragraph('Le patient est admis pour hospitalisation selon les modalités ci-dessus.', normal))
    story.append(Spacer(1, 40))
    story.append(Paragraph('Signature du médecin : _____________', normal))
    story.append(Spacer(1, 20))
    story.append(Paragraph('Signature du patient : _____________', normal))

    doc.build(story, onFirstPage=lambda c, d: _header_footer(c, d, 'Bon hospitalisation'),
                       onLaterPages=lambda c, d: _header_footer(c, d, 'Bon hospitalisation'))
    return buf.getvalue()


print("[PDF_GEN] ✅ Module PDF chargé (reportlab)")
