"""Export Excel avec openpyxl"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from io import BytesIO
from datetime import datetime


def _style_header(ws, row=1):
    font = Font(bold=True, color="FFFFFF", size=11)
    fill = PatternFill(start_color="1A1A2E", end_color="1A1A2E", fill_type="solid")
    border = Border(left=Side(style='thin', color='E2E8F0'),
                    right=Side(style='thin', color='E2E8F0'),
                    top=Side(style='thin', color='E2E8F0'),
                    bottom=Side(style='thin', color='E2E8F0'))
    for cell in ws[row]:
        cell.font = font
        cell.fill = fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border


def _auto_width(ws):
    for col in ws.columns:
        max_len = 0
        letter = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            except Exception:
                pass
        ws.column_dimensions[letter].width = min(max_len + 3, 40)


def exporter_etudiants(etudiants):
    wb = Workbook()
    ws = wb.active
    ws.title = "Étudiants"
    ws.append(["Matricule", "Nom", "Prénom", "Date naissance",
               "Sexe", "Téléphone", "Email", "Classe", "Statut"])
    for e in etudiants:
        ws.append([e['matricule'], e['nom'], e['prenom'], e['date_naissance'],
                   e['sexe'], e['telephone'], e['email'],
                   e.get('classe_nom', '-'), e['statut']])
    _style_header(ws)
    _auto_width(ws)
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.read()


def exporter_notes_classe(classe_nom, notes):
    wb = Workbook()
    ws = wb.active
    ws.title = "Notes"
    ws.append(["OMEGA CONSULTING — Relevé de notes"])
    ws.merge_cells('A1:I1')
    ws['A1'].font = Font(bold=True, size=14, color="E94560")
    ws['A1'].alignment = Alignment(horizontal='center')
    ws.append([f"Classe : {classe_nom}", "", "",
               f"Généré le : {datetime.now().strftime('%d/%m/%Y %H:%M')}"])
    ws.append([])
    ws.append(["Matricule", "Nom", "Prénom", "Matière",
               "Coeff", "CC", "Examen", "Note finale", "Statut"])
    header_row = ws.max_row
    for n in notes:
        ws.append([n['matricule'], n['nom'], n['prenom'], n['matiere_nom'],
                   n['coefficient'], n['note_cc'], n['note_examen'],
                   n['note_finale'], n['statut']])
    _style_header(ws, header_row)
    _auto_width(ws)
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.read()


def exporter_paiements(paiements):
    wb = Workbook()
    ws = wb.active
    ws.title = "Paiements"
    ws.append(["OMEGA CONSULTING — Suivi paiements"])
    ws.merge_cells('A1:G1')
    ws['A1'].font = Font(bold=True, size=14, color="E94560")
    ws['A1'].alignment = Alignment(horizontal='center')
    ws.append([])
    ws.append(["Étudiant", "Matricule", "Montant (FCFA)", "Mois",
               "Mode", "Date", "Statut"])
    header_row = ws.max_row
    total = 0
    for p in paiements:
        ws.append([f"{p['nom']} {p['prenom']}", p['matricule'], p['montant'],
                   p['mois'], p['mode_paiement'] or '-',
                   p['date_paiement'][:10] if p['date_paiement'] else '-',
                   p['statut']])
        if p['statut'] == 'Payé':
            total += p['montant'] or 0
    ws.append([])
    ws.append(["", "", "TOTAL PAYÉ :", total, "", "", ""])
    tr = ws.max_row
    ws.cell(row=tr, column=3).font = Font(bold=True)
    ws.cell(row=tr, column=4).font = Font(bold=True, color="2ECC71")
    _style_header(ws, header_row)
    _auto_width(ws)
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.read()


def exporter_bulletin_etudiant(etudiant, notes, stats):
    wb = Workbook()
    ws = wb.active
    ws.title = "Bulletin"
    ws.append(["OMEGA CONSULTING — Bulletin de notes"])
    ws.merge_cells('A1:H1')
    ws['A1'].font = Font(bold=True, size=16, color="E94560")
    ws['A1'].alignment = Alignment(horizontal='center')
    ws.append([])
    ws.append(["Matricule :", etudiant['matricule'], "", "Classe :", etudiant.get('classe_nom', '-')])
    ws.append(["Nom :", f"{etudiant['nom']} {etudiant['prenom']}", "", "Statut :", etudiant['statut']])
    ws.append([])
    ws.append(["Matière", "Coeff", "Crédits", "CC", "TP", "Examen", "Note finale", "Statut"])
    header_row = ws.max_row
    total_p = 0
    total_c = 0
    for n in notes:
        ws.append([n['matiere_nom'], n['coefficient'], n.get('credit', '-'),
                   n['note_cc'] or '-', n['note_tp'] or '-', n['note_examen'] or '-',
                   n['note_finale'], n['statut']])
        total_p += (n['note_finale'] or 0) * n['coefficient']
        total_c += n['coefficient']
    moy = round(total_p / total_c, 2) if total_c else 0
    ws.append([])
    ws.append(["MOYENNE GÉNÉRALE :", moy])
    mr = ws.max_row
    ws.cell(row=mr, column=1).font = Font(bold=True)
    ws.cell(row=mr, column=2).font = Font(bold=True, color="E94560", size=12)
    _style_header(ws, header_row)
    _auto_width(ws)
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.read()
