"""Génération PDF des bulletins avec QR code de vérification"""
# ==================== SAFE WEASYPRINT IMPORT ====================
try:
    from weasyprint import HTML
    WEASYPRINT_OK = True
except (ImportError, OSError) as e:
    print(f"[PDF] ⚠️ WeasyPrint indisponible: {e}")
    WEASYPRINT_OK = False
    HTML = None

    HTML
import qrcode
import io
import base64
import hashlib
from datetime import datetime


def generer_qr_base64(data):
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a1a2e", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()


def generer_hash_verification(etudiant, moyenne, semestre_nom="Année"):
    """Hash unique anti-fraude"""
    data = f"{etudiant['matricule']}|{etudiant['nom']}|{etudiant['prenom']}|{moyenne}|{semestre_nom}|OMEGA2026"
    return hashlib.sha256(data.encode()).hexdigest()[:16].upper()


def _mention(moyenne):
    if moyenne >= 16: return "Très Bien"
    if moyenne >= 14: return "Bien"
    if moyenne >= 12: return "Assez Bien"
    if moyenne >= 10: return "Passable"
    return "Insuffisant"


def generer_bulletin_pdf(etudiant, notes, stats, rang, total, semestre_nom="Année 2025-2026"):
    """Retourne (pdf_bytes, hash_verification)"""

    hash_verif = generer_hash_verification(etudiant, stats['moyenne'], semestre_nom)
    url_verif = f"https://omega-software.duckdns.org:8080/ecole/verifier/{hash_verif}"
    qr_base64 = generer_qr_base64(url_verif)

    mention = _mention(stats['moyenne'])
    date_emission = datetime.now().strftime("%d/%m/%Y à %H:%M")

    lignes_html = ""
    total_points = 0
    total_coefs = 0
    for n in notes:
        statut_class = "success" if (n['note_finale'] or 0) >= 10 else "danger"
        lignes_html += f"""
        <tr>
            <td>{n['matiere_nom']}</td>
            <td style="text-align:center;">{n['coefficient']}</td>
            <td style="text-align:center;">{n.get('credit', '-')}</td>
            <td style="text-align:center;">{n['note_cc'] if n['note_cc'] is not None else '-'}</td>
            <td style="text-align:center;">{n['note_tp'] if n['note_tp'] is not None else '-'}</td>
            <td style="text-align:center;">{n['note_examen'] if n['note_examen'] is not None else '-'}</td>
            <td style="text-align:center;"><strong>{n['note_finale'] if n['note_finale'] is not None else '-'}/20</strong></td>
            <td style="text-align:center;"><span class="badge badge-{statut_class}">{n['statut']}</span></td>
        </tr>
        """
        total_points += (n['note_finale'] or 0) * n['coefficient']
        total_coefs += n['coefficient']

    moyenne_generale = round(total_points / total_coefs, 2) if total_coefs else 0

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 15mm; }}
            * {{ margin:0; padding:0; box-sizing:border-box; font-family: 'DejaVu Sans', sans-serif; }}
            body {{ color:#1a1a2e; font-size:11px; }}
            .header {{
                border-bottom:3px solid #e94560; padding-bottom:12px;
                margin-bottom:20px; display:flex; justify-content:space-between;
            }}
            .header .logo h1 {{ font-size:1.6rem; color:#1a1a2e; }}
            .header .logo h1 span {{ color:#e94560; }}
            .header .logo p {{ color:#718096; font-size:0.75rem; margin-top:3px; }}
            .header .qr {{ text-align:center; }}
            .header .qr img {{ width:80px; height:80px; }}
            .header .qr small {{ display:block; color:#718096; font-size:0.65rem; margin-top:3px; }}
            h2.title {{
                text-align:center; color:#e94560; font-size:1.2rem;
                margin:15px 0; text-transform:uppercase; letter-spacing:1px;
            }}
            .info-grid {{
                display:grid; grid-template-columns:1fr 1fr; gap:10px;
                margin-bottom:15px; background:#f7fafc; padding:12px; border-radius:6px;
            }}
            .info-grid .row {{ display:flex; }}
            .info-grid .row strong {{ min-width:100px; color:#4a5568; }}
            .stats-grid {{
                display:grid; grid-template-columns:repeat(4, 1fr);
                gap:8px; margin-bottom:15px;
            }}
            .stat-box {{
                background:#f7fafc; padding:8px; border-radius:6px;
                text-align:center; border-left:3px solid #e94560;
            }}
            .stat-box .num {{ font-size:1.1rem; font-weight:700; color:#1a1a2e; }}
            .stat-box .label {{ font-size:0.6rem; color:#718096; text-transform:uppercase; }}
            table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
            th, td {{ padding:6px 8px; border-bottom:1px solid #e2e8f0; font-size:10px; }}
            th {{
                background:#1a1a2e; color:white; font-size:8px;
                text-transform:uppercase; letter-spacing:0.5px;
            }}
            tfoot td {{ background:#f7fafc; font-weight:bold; font-size:11px; }}
            .badge {{ padding:2px 6px; border-radius:10px; font-size:8px; font-weight:600; }}
            .badge-success {{ background:#d1fae5; color:#065f46; }}
            .badge-danger {{ background:#fee2e2; color:#991b1b; }}
            .mention-box {{
                margin-top:15px; padding:12px;
                background:linear-gradient(135deg,#1a1a2e,#0f3460);
                color:white; border-radius:6px; text-align:center;
            }}
            .mention-box .big {{ font-size:1.4rem; font-weight:900; color:#e94560; }}
            .mention-box .small {{ font-size:0.7rem; opacity:0.8; }}
            .signatures {{ margin-top:35px; display:flex; justify-content:space-around; }}
            .signatures div {{ text-align:center; }}
            .signatures .line {{
                border-top:1px solid #1a1a2e; width:150px;
                margin-top:35px; padding-top:4px; font-size:9px;
            }}
            .footer {{
                position:fixed; bottom:0; left:0; right:0;
                text-align:center; color:#a0aec0; font-size:7px;
                padding:6px; border-top:1px solid #e2e8f0;
            }}
            .verif-info {{
                margin-top:15px; padding:8px; background:#fef3c7;
                border-radius:4px; font-size:8px; color:#92400e;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">
                <h1>OMEGA <span>CONSULTING</span></h1>
                <p>Système LMD — Établissement d'enseignement supérieur</p>
                <p>Dakar, Sénégal — omega-software.duckdns.org</p>
            </div>
            <div class="qr">
                <img src="data:image/png;base64,{qr_base64}" alt="QR">
                <small>Vérifier en ligne</small>
            </div>
        </div>

        <h2 class="title">Bulletin de Notes — {semestre_nom}</h2>

        <div class="info-grid">
            <div class="row"><strong>Matricule :</strong> {etudiant['matricule']}</div>
            <div class="row"><strong>Classe :</strong> {etudiant.get('classe_nom', '-')}</div>
            <div class="row"><strong>Nom :</strong> {etudiant['nom']} {etudiant['prenom']}</div>
            <div class="row"><strong>Niveau :</strong> {etudiant.get('niveau_nom', '-')}</div>
            <div class="row"><strong>Né(e) le :</strong> {etudiant['date_naissance']}</div>
            <div class="row"><strong>Filière :</strong> {etudiant.get('filiere_nom', '-')}</div>
        </div>

        <div class="stats-grid">
            <div class="stat-box"><div class="num">{stats['moyenne']}/20</div><div class="label">Moyenne</div></div>
            <div class="stat-box"><div class="num">{rang}/{total}</div><div class="label">Rang</div></div>
            <div class="stat-box"><div class="num">{stats['validees']}</div><div class="label">Validées</div></div>
            <div class="stat-box"><div class="num">{mention}</div><div class="label">Mention</div></div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Matière</th><th>Coeff</th><th>Crédits</th>
                    <th>CC</th><th>TP</th><th>Examen</th>
                    <th>Note finale</th><th>Statut</th>
                </tr>
            </thead>
            <tbody>{lignes_html}</tbody>
            <tfoot>
                <tr>
                    <td colspan="6">MOYENNE GÉNÉRALE PONDÉRÉE</td>
                    <td style="text-align:center;">{moyenne_generale}/20</td>
                    <td></td>
                </tr>
            </tfoot>
        </table>

        <div class="mention-box">
            <div class="small">Mention obtenue</div>
            <div class="big">{mention.upper()}</div>
        </div>

        <div class="verif-info">
            <strong>🔒 Code de vérification :</strong> {hash_verif}
            — Scannez le QR ou visitez /verifier/{hash_verif}
        </div>

        <div class="signatures">
            <div><div class="line">Le Chef de Département</div></div>
            <div><div class="line">Le Directeur des Études</div></div>
            <div><div class="line">Le Directeur Général</div></div>
        </div>

        <div class="footer">
            Document généré automatiquement le {date_emission} — Omega Consulting © 2026
            <br>Ce bulletin est authentifiable via son code unique.
        </div>
    </body>
    </html>
    """

    pdf_bytes = HTML(string=html).write_pdf()
    return pdf_bytes, hash_verif
