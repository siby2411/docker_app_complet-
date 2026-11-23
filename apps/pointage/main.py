from fastapi import FastAPI, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
import os
import qrcode
import secrets
import time
import io
import logging

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Omega Pointage RH Pro", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dossiers
DB_PATH = "/app/data/pointage.db"
STATIC_DIR = "/app/static"
QRCODE_DIR = "/app/static/qrcodes"

# Créer les dossiers
for dir_path in [os.path.dirname(DB_PATH), STATIC_DIR, QRCODE_DIR]:
    os.makedirs(dir_path, exist_ok=True)
    logger.info(f"Dossier créé/vérifié: {dir_path}")

# Monter le dossier static
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# SQLAlchemy setup
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}?check_same_thread=False&timeout=30"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Employe(Base):
    __tablename__ = "employes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    matricule = Column(String, unique=True, index=True)
    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    telephone = Column(String)
    departement = Column(String)
    poste = Column(String)
    salaire_base = Column(Float, default=0)
    qrcode = Column(String)
    date_creation = Column(DateTime, default=func.now())
    statut = Column(String, default="Actif")

class Pointage(Base):
    __tablename__ = "pointages"
    id = Column(Integer, primary_key=True, index=True)
    employe_id = Column(Integer, ForeignKey("employes.id"))
    type_pointage = Column(String)
    date_pointage = Column(DateTime, default=func.now())
    mode = Column(String, default="QR_CODE")
    statut = Column(String, default="Valide")

class Planning(Base):
    __tablename__ = "plannings"
    id = Column(Integer, primary_key=True, index=True)
    employe_id = Column(Integer, ForeignKey("employes.id"))
    date_debut = Column(DateTime)
    date_fin = Column(DateTime)
    heure_debut = Column(String)
    heure_fin = Column(String)
    type_jour = Column(String)
    observations = Column(Text)

class Paie(Base):
    __tablename__ = "paies"
    id = Column(Integer, primary_key=True, index=True)
    employe_id = Column(Integer, ForeignKey("employes.id"))
    mois = Column(String)
    heures_normales = Column(Float, default=0)
    heures_supplementaires = Column(Float, default=0)
    jours_presents = Column(Integer, default=0)
    jours_absences = Column(Integer, default=0)
    montant_brut = Column(Float, default=0)
    montant_net = Column(Float, default=0)
    statut = Column(String, default="Calcule")

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Base de données initialisée")
    except Exception as e:
        logger.error(f"Erreur création tables: {e}")
        time.sleep(2)
        Base.metadata.create_all(bind=engine)

init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generer_matricule(db):
    count = db.query(Employe).count() + 1
    return f"EMP{count:04d}"

def generer_qrcode(employe):
    """Génère un QR Code et retourne le chemin"""
    try:
        qr_data = f"EMP:{employe.id}:{employe.matricule}:{employe.nom}:{employe.prenom}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#0d47a1", back_color="white")
        
        filename = f"{employe.matricule}.png"
        filepath = os.path.join(QRCODE_DIR, filename)
        qr_img.save(filepath)
        logger.info(f"QR Code généré: {filepath}")
        
        return f"static/qrcodes/{filename}"
    except Exception as e:
        logger.error(f"Erreur génération QR Code: {e}")
        return None

# ==================== HTML TEMPLATE ====================
HTML_BASE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Omega Pointage RH Pro</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; font-family:"Segoe UI",sans-serif; }
        body { background:#0a0e17; color:#fff; min-height:100vh; }
        .header { background:linear-gradient(135deg,#0d47a1,#1a237e); padding:15px 30px; display:flex; justify-content:space-between; align-items:center; border-bottom:3px solid #00d4ff; flex-wrap:wrap; gap:10px; }
        .header h1 { font-size:1.5rem; }
        .header h1 span { color:#00d4ff; }
        .header .badge { background:rgba(0,212,255,0.15); color:#00d4ff; padding:6px 18px; border-radius:20px; font-size:0.8rem; border:1px solid rgba(0,212,255,0.1); }
        .container { max-width:1400px; margin:0 auto; padding:20px; }
        .menu { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:20px; }
        .menu a { padding:10px 22px; background:rgba(255,255,255,0.05); color:#fff; text-decoration:none; border-radius:10px; transition:0.3s; border:1px solid rgba(255,255,255,0.05); font-size:0.9rem; }
        .menu a:hover, .menu a.active { background:#00d4ff; color:#0a0e17; border-color:#00d4ff; }
        .menu a i { margin-right:8px; }
        .card { background:rgba(255,255,255,0.05); backdrop-filter:blur(10px); border-radius:12px; padding:20px; border:1px solid rgba(255,255,255,0.05); margin-bottom:20px; }
        .card h2 { font-size:1.1rem; margin-bottom:15px; color:#00d4ff; }
        .card h2 i { margin-right:10px; }
        table { width:100%; border-collapse:collapse; }
        th, td { padding:12px; text-align:left; border-bottom:1px solid rgba(255,255,255,0.05); }
        th { color:rgba(255,255,255,0.5); font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; }
        td { color:rgba(255,255,255,0.85); }
        .badge-status { padding:4px 14px; border-radius:20px; font-size:0.7rem; font-weight:600; display:inline-block; }
        .badge-present { background:rgba(52,211,153,0.15); color:#34d399; }
        .badge-absent { background:rgba(239,68,68,0.15); color:#ef4444; }
        .badge-actif { background:rgba(52,211,153,0.15); color:#34d399; }
        .badge-inactif { background:rgba(239,68,68,0.15); color:#ef4444; }
        .btn { padding:8px 20px; border:none; border-radius:8px; cursor:pointer; font-weight:600; transition:0.3s; text-decoration:none; display:inline-flex; align-items:center; gap:6px; font-size:0.85rem; }
        .btn-primary { background:#00d4ff; color:#0a0e17; }
        .btn-success { background:#34d399; color:#0a0e17; }
        .btn-info { background:#60a5fa; color:#0a0e17; }
        .btn-sm { padding:4px 12px; font-size:0.75rem; }
        .form-container { max-width:600px; margin:0 auto; }
        .form-group { margin-bottom:15px; }
        .form-group label { display:block; color:rgba(255,255,255,0.7); margin-bottom:5px; font-size:0.9rem; }
        .form-group input, .form-group select { width:100%; padding:10px 15px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); border-radius:8px; color:#fff; font-size:0.95rem; }
        .form-group input:focus { outline:none; border-color:#00d4ff; }
        .form-row { display:grid; grid-template-columns:1fr 1fr; gap:15px; }
        .stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:15px; margin-bottom:20px; }
        .stat { background:rgba(255,255,255,0.05); padding:20px; border-radius:12px; text-align:center; }
        .stat .num { font-size:2.5rem; font-weight:700; color:#00d4ff; }
        .stat .label { color:rgba(255,255,255,0.5); font-size:0.85rem; margin-top:5px; }
        .scanner-container { max-width:500px; margin:0 auto; }
        #reader { width:100%; max-width:500px; margin:0 auto; background:rgba(0,0,0,0.3); border-radius:12px; padding:10px; }
        .qrcode-container { text-align:center; padding:20px; }
        .qrcode-container img { max-width:250px; border:2px solid rgba(255,255,255,0.1); border-radius:12px; padding:10px; background:#fff; }
        @media (max-width:768px) { .form-row { grid-template-columns:1fr; } .header { flex-direction:column; text-align:center; } }
    </style>
</head>
<body>
    <header class="header">
        <h1><i class="fas fa-fingerprint"></i> OMEGA <span>POINTAGE PRO</span></h1>
        <span class="badge"><i class="fas fa-qrcode"></i> RH v2.0</span>
    </header>
    
    <div class="container">
        <nav class="menu">
            <a href="/pointage/" class="active"><i class="fas fa-home"></i> Dashboard</a>
            <a href="/pointage/employes"><i class="fas fa-users"></i> Employés</a>
            <a href="/pointage/pointage"><i class="fas fa-clock"></i> Pointage</a>
            <a href="/pointage/paie"><i class="fas fa-money-bill-wave"></i> Paie</a>
            <a href="/pointage/scanner"><i class="fas fa-qrcode"></i> Scanner</a>
            <a href="/pointage/statistiques"><i class="fas fa-chart-bar"></i> Statistiques</a>
        </nav>
        
        <div id="app-content">
            <!-- Le contenu sera injecté ici -->
        </div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html5-qrcode/2.3.8/html5-qrcode.min.js"></script>
</body>
</html>
'''

# ==================== ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def index(db: Session = Depends(get_db)):
    try:
        total_employes = db.query(Employe).filter(Employe.statut == "Actif").count()
        
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        pointages_aujourdhui = db.query(Pointage).filter(
            Pointage.date_pointage >= today_start,
            Pointage.date_pointage <= today_end
        ).all()
        
        presents = len([p for p in pointages_aujourdhui if p.type_pointage == "ENTREE"])
        
        derniers = db.query(Pointage).order_by(Pointage.date_pointage.desc()).limit(10).all()
        
        rows = ""
        for p in derniers:
            employe = db.query(Employe).filter(Employe.id == p.employe_id).first()
            nom = f"{employe.nom} {employe.prenom}" if employe else "Inconnu"
            badge = "badge-present" if p.type_pointage == "ENTREE" else "badge-absent"
            rows += f"<tr><td>{nom}</td><td><span class='badge-status {badge}'>{p.type_pointage}</span></td><td>{p.date_pointage.strftime('%d/%m %H:%M')}</td><td>{p.mode}</td></tr>"
        
        content = f'''
        <div class="stats">
            <div class="stat"><div class="num">{total_employes}</div><div class="label">Employés</div></div>
            <div class="stat"><div class="num">{presents}</div><div class="label">Présents</div></div>
            <div class="stat"><div class="num">{len(pointages_aujourdhui)}</div><div class="label">Pointages Aujourd\'hui</div></div>
        </div>
        
        <div class="card">
            <h2><i class="fas fa-clock"></i> Derniers Pointages</h2>
            <table>
                <thead><tr><th>Employé</th><th>Type</th><th>Date</th><th>Mode</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        
        <div class="card">
            <h2><i class="fas fa-qrcode"></i> Scanner Rapide</h2>
            <div class="scanner-container">
                <div id="reader"></div>
                <div id="scanner-result" style="margin-top:15px;text-align:center;padding:15px;border-radius:8px;"></div>
            </div>
        </div>
        
        <script>
        function onScanSuccess(decodedText) {{
            document.getElementById('scanner-result').innerHTML = '<i class="fas fa-spinner fa-spin"></i> Traitement...';
            document.getElementById('scanner-result').style.background = 'rgba(52,211,153,0.1)';
            document.getElementById('scanner-result').style.border = '1px solid rgba(52,211,153,0.2)';
            
            fetch('/pointage/api/pointage/scan', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ code: decodedText }})
            }})
            .then(res => res.json())
            .then(data => {{
                if (data.status === 'success') {{
                    document.getElementById('scanner-result').innerHTML = `
                        <div style="color:#34d399;font-size:1.1rem;">✅ ${{data.message}}</div>
                        <div style="color:rgba(255,255,255,0.5);margin-top:5px;">${{data.employe ? data.employe.nom + ' ' + data.employe.prenom : ''}}</div>
                    `;
                    setTimeout(() => {{ location.reload(); }}, 2000);
                }} else {{
                    document.getElementById('scanner-result').style.background = 'rgba(239,68,68,0.1)';
                    document.getElementById('scanner-result').style.border = '1px solid rgba(239,68,68,0.2)';
                    document.getElementById('scanner-result').innerHTML = `<div style="color:#ef4444;">❌ ${{data.message}}</div>`;
                }}
            }})
            .catch(err => {{
                document.getElementById('scanner-result').style.background = 'rgba(239,68,68,0.1)';
                document.getElementById('scanner-result').style.border = '1px solid rgba(239,68,68,0.2)';
                document.getElementById('scanner-result').innerHTML = `<div style="color:#ef4444;">❌ Erreur: ${{err.message}}</div>`;
            }});
        }}
        
        function onScanError(errorMessage) {{}}
        
        if (document.getElementById('reader')) {{
            let html5QrCode = new Html5Qrcode("reader");
            const config = {{ fps: 10, qrbox: {{ width: 300, height: 300 }}, aspectRatio: 1.0 }};
            html5QrCode.start({{ facingMode: "environment" }}, config, onScanSuccess, onScanError)
                .catch(err => console.log('Scanner error:', err));
        }}
        </script>
        '''
        
        return HTML_BASE.replace('<div id="app-content">\n            <!-- Le contenu sera injecté ici -->\n        </div>', content)
    except Exception as e:
        logger.error(f"Erreur index: {e}")
        return HTML_BASE.replace('<div id="app-content">\n            <!-- Le contenu sera injecté ici -->\n        </div>', '<div class="card"><h2>Erreur</h2><p>Une erreur est survenue</p></div>')

@app.get("/employes", response_class=HTMLResponse)
async def employes_page(db: Session = Depends(get_db)):
    employes = db.query(Employe).all()
    
    rows = ""
    for e in employes:
        badge = "badge-actif" if e.statut == "Actif" else "badge-inactif"
        qr_display = "✅" if e.qrcode else "❌"
        rows += f'''
        <tr>
            <td><strong>{e.matricule}</strong></td>
            <td>{e.nom} {e.prenom}</td>
            <td>{e.email}</td>
            <td>{e.departement or '-'}</td>
            <td><span class="badge-status {badge}">{e.statut}</span></td>
            <td>{qr_display}</td>
            <td>
                <a href="/pointage/employes/{e.id}/qrcode" class="btn btn-primary btn-sm"><i class="fas fa-qrcode"></i> QR</a>
            </td>
        </tr>
        '''
    
    content = f'''
    <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:15px;">
            <h2><i class="fas fa-users"></i> Employés</h2>
            <a href="/pointage/employes/ajouter" class="btn btn-success"><i class="fas fa-plus"></i> Ajouter</a>
        </div>
        <table>
            <thead><tr><th>Matricule</th><th>Nom</th><th>Email</th><th>Département</th><th>Statut</th><th>QR</th><th>Actions</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    '''
    
    return HTML_BASE.replace('<div id="app-content">\n            <!-- Le contenu sera injecté ici -->\n        </div>', content)

@app.get("/employes/ajouter", response_class=HTMLResponse)
async def ajouter_employe_page():
    content = '''
    <div class="card">
        <h2><i class="fas fa-user-plus"></i> Ajouter un Employé</h2>
        <div class="form-container">
            <form method="POST" action="/pointage/employes/ajouter">
                <div class="form-row">
                    <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
                    <div class="form-group"><label>Prénom *</label><input type="text" name="prenom" required></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Email *</label><input type="email" name="email" required></div>
                    <div class="form-group"><label>Téléphone</label><input type="text" name="telephone"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Département</label><input type="text" name="departement"></div>
                    <div class="form-group"><label>Poste</label><input type="text" name="poste"></div>
                </div>
                <button type="submit" class="btn btn-success" style="width:100%;"><i class="fas fa-save"></i> Enregistrer</button>
            </form>
        </div>
        <br><a href="/pointage/employes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    '''
    return HTML_BASE.replace('<div id="app-content">\n            <!-- Le contenu sera injecté ici -->\n        </div>', content)

@app.post("/employes/ajouter")
async def create_employe(
    nom: str = Form(...),
    prenom: str = Form(...),
    email: str = Form(...),
    telephone: str = Form(None),
    departement: str = Form(None),
    poste: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        matricule = generer_matricule(db)
        code = f"EMP{datetime.now().strftime('%Y%m%d')}{secrets.token_hex(4).upper()}"
        
        employe = Employe(
            code=code,
            matricule=matricule,
            nom=nom,
            prenom=prenom,
            email=email,
            telephone=telephone,
            departement=departement,
            poste=poste,
            statut="Actif"
        )
        db.add(employe)
        db.commit()
        db.refresh(employe)
        
        # Générer le QR Code
        qr_path = generer_qrcode(employe)
        if qr_path:
            employe.qrcode = qr_path
            db.commit()
            logger.info(f"QR Code généré pour {employe.nom} {employe.prenom}")
        else:
            logger.warning(f"Échec génération QR Code pour {employe.nom} {employe.prenom}")
        
        return RedirectResponse(url="/pointage/employes", status_code=303)
    except Exception as e:
        logger.error(f"Erreur création employé: {e}")
        return RedirectResponse(url="/pointage/employes", status_code=303)

@app.get("/employes/{id}/qrcode", response_class=HTMLResponse)
async def employe_qrcode(id: int, db: Session = Depends(get_db)):
    try:
        employe = db.query(Employe).filter(Employe.id == id).first()
        if not employe:
            return RedirectResponse(url="/pointage/employes")
        
        # Si le QR Code n'existe pas, le générer
        if not employe.qrcode:
            qr_path = generer_qrcode(employe)
            if qr_path:
                employe.qrcode = qr_path
                db.commit()
        
        # Vérifier si le fichier existe
        if employe.qrcode:
            filepath = f"/app/{employe.qrcode}"
            if not os.path.exists(filepath):
                qr_path = generer_qrcode(employe)
                if qr_path:
                    employe.qrcode = qr_path
                    db.commit()
        
        # Construire l'URL du QR Code
        qr_url = f"/pointage/{employe.qrcode}" if employe.qrcode else ""
        
        content = f'''
        <div class="card">
            <h2><i class="fas fa-qrcode"></i> QR Code - {employe.nom} {employe.prenom}</h2>
            <div class="qrcode-container">
                {f'<img src="{qr_url}" alt="QR Code">' if qr_url else '<p style="color:#ef4444;">QR Code non disponible</p>'}
                <div style="margin-top:15px;">
                    <p><strong>Matricule:</strong> {employe.matricule}</p>
                    <p><strong>Nom:</strong> {employe.nom} {employe.prenom}</p>
                    <p><strong>Email:</strong> {employe.email}</p>
                    <p><strong>Département:</strong> {employe.departement or '-'}</p>
                </div>
                <div style="margin-top:20px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap;">
                    {f'<a href="{qr_url}" download class="btn btn-success"><i class="fas fa-download"></i> Télécharger PNG</a>' if qr_url else ''}
                    <a href="/pointage/employes" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
                </div>
            </div>
        </div>
        '''
        
        return HTML_BASE.replace('<div id="app-content">\n            <!-- Le contenu sera injecté ici -->\n        </div>', content)
    except Exception as e:
        logger.error(f"Erreur QR Code: {e}")
        return RedirectResponse(url="/pointage/employes")

@app.get("/static/qrcodes/{filename}")
async def serve_qrcode(filename: str):
    """Sert le fichier QR Code"""
    filepath = os.path.join(QRCODE_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="image/png")
    return JSONResponse({"error": "Fichier non trouvé"}, status_code=404)

@app.get("/pointage", response_class=HTMLResponse)
async def pointage_page(db: Session = Depends(get_db)):
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    pointages = db.query(Pointage).filter(
        Pointage.date_pointage >= today_start,
        Pointage.date_pointage <= today_end
    ).order_by(Pointage.date_pointage.desc()).all()
    
    rows = ""
    for p in pointages:
        employe = db.query(Employe).filter(Employe.id == p.employe_id).first()
        nom = f"{employe.nom} {employe.prenom}" if employe else "Inconnu"
        badge = "badge-present" if p.type_pointage == "ENTREE" else "badge-absent"
        rows += f"<tr><td>{nom}</td><td><span class='badge-status {badge}'>{p.type_pointage}</span></td><td>{p.date_pointage.strftime('%d/%m/%Y %H:%M')}</td><td>{p.mode}</td></tr>"
    
    content = f'''
    <div class="card">
        <h2><i class="fas fa-clock"></i> Pointages du Jour</h2>
        <table>
            <thead><tr><th>Employé</th><th>Type</th><th>Date</th><th>Mode</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    '''
    
    return HTML_BASE.replace('<div id="app-content">\n            <!-- Le contenu sera injecté ici -->\n        </div>', content)

@app.get("/scanner", response_class=HTMLResponse)
async def scanner_page():
    content = '''
    <div class="card">
        <h2><i class="fas fa-qrcode"></i> Scanner QR Code</h2>
        <div class="scanner-container">
            <div id="reader"></div>
            <div id="scanner-result" style="margin-top:15px;text-align:center;padding:15px;border-radius:8px;"></div>
        </div>
    </div>
    
    <script>
    function onScanSuccess(decodedText) {
        document.getElementById('scanner-result').innerHTML = '<i class="fas fa-spinner fa-spin"></i> Traitement...';
        document.getElementById('scanner-result').style.background = 'rgba(52,211,153,0.1)';
        document.getElementById('scanner-result').style.border = '1px solid rgba(52,211,153,0.2)';
        
        fetch('/pointage/api/pointage/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: decodedText })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                document.getElementById('scanner-result').innerHTML = `
                    <div style="color:#34d399;font-size:1.1rem;">✅ ${data.message}</div>
                    <div style="color:rgba(255,255,255,0.5);margin-top:5px;">${data.employe ? data.employe.nom + ' ' + data.employe.prenom : ''}</div>
                `;
                setTimeout(() => { location.reload(); }, 2000);
            } else {
                document.getElementById('scanner-result').style.background = 'rgba(239,68,68,0.1)';
                document.getElementById('scanner-result').style.border = '1px solid rgba(239,68,68,0.2)';
                document.getElementById('scanner-result').innerHTML = `<div style="color:#ef4444;">❌ ${data.message}</div>`;
            }
        })
        .catch(err => {
            document.getElementById('scanner-result').style.background = 'rgba(239,68,68,0.1)';
            document.getElementById('scanner-result').style.border = '1px solid rgba(239,68,68,0.2)';
            document.getElementById('scanner-result').innerHTML = `<div style="color:#ef4444;">❌ Erreur: ${err.message}</div>`;
        });
    }
    
    function onScanError(errorMessage) {}
    
    if (document.getElementById('reader')) {
        let html5QrCode = new Html5Qrcode("reader");
        const config = { fps: 10, qrbox: { width: 350, height: 350 }, aspectRatio: 1.0 };
        html5QrCode.start({ facingMode: "environment" }, config, onScanSuccess, onScanError)
            .catch(err => console.log('Scanner error:', err));
    }
    </script>
    '''
    
    return HTML_BASE.replace('<div id="app-content">\n            <!-- Le contenu sera injecté ici -->\n        </div>', content)

@app.get("/paie", response_class=HTMLResponse)
async def paie_page(db: Session = Depends(get_db)):
    mois_actuel = datetime.now().strftime("%Y-%m")
    paies = db.query(Paie).filter(Paie.mois == mois_actuel).all()
    
    rows = ""
    for p in paies:
        employe = db.query(Employe).filter(Employe.id == p.employe_id).first()
        nom = f"{employe.nom} {employe.prenom}" if employe else "Inconnu"
        rows += f"<tr><td>{nom}</td><td>{p.heures_normales:.1f}h</td><td>{p.jours_presents}j</td><td>{p.montant_brut:,.0f} FCFA</td><td>{p.montant_net:,.0f} FCFA</td></tr>"
    
    content = f'''
    <div class="card">
        <h2><i class="fas fa-money-bill-wave"></i> Paie - {mois_actuel}</h2>
        <table>
            <thead><tr><th>Employé</th><th>Heures</th><th>Jours Présents</th><th>Brut</th><th>Net</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    '''
    
    return HTML_BASE.replace('<div id="app-content">\n            <!-- Le contenu sera injecté ici -->\n        </div>', content)

@app.get("/statistiques", response_class=HTMLResponse)
async def statistiques_page(db: Session = Depends(get_db)):
    total = db.query(Employe).filter(Employe.statut == "Actif").count()
    inactifs = db.query(Employe).filter(Employe.statut == "Inactif").count()
    
    content = f'''
    <div class="stats">
        <div class="stat"><div class="num">{total}</div><div class="label">Employés Actifs</div></div>
        <div class="stat"><div class="num">{inactifs}</div><div class="label">Employés Inactifs</div></div>
        <div class="stat"><div class="num">{total + inactifs}</div><div class="label">Total Employés</div></div>
    </div>
    '''
    
    return HTML_BASE.replace('<div id="app-content">\n            <!-- Le contenu sera injecté ici -->\n        </div>', content)

# ==================== API ====================

@app.post("/api/pointage/scan")
async def scan_pointage(data: dict, db: Session = Depends(get_db)):
    code = data.get('code')
    if not code:
        return {"status": "error", "message": "Code QR invalide"}
    
    try:
        parts = code.split(':')
        if len(parts) >= 2 and parts[0] == 'EMP':
            employe_id = int(parts[1])
        else:
            employe = db.query(Employe).filter(Employe.matricule == code).first()
            if not employe:
                return {"status": "error", "message": "Employé non trouvé"}
            employe_id = employe.id
    except:
        employe = db.query(Employe).filter(Employe.matricule == code).first()
        if not employe:
            return {"status": "error", "message": "Employé non trouvé"}
        employe_id = employe.id
    
    employe = db.query(Employe).filter(Employe.id == employe_id).first()
    if not employe:
        return {"status": "error", "message": "Employé non trouvé"}
    
    if employe.statut != "Actif":
        return {"status": "error", "message": "Employé inactif"}
    
    dernier = db.query(Pointage).filter(
        Pointage.employe_id == employe.id
    ).order_by(Pointage.date_pointage.desc()).first()
    
    if not dernier or dernier.type_pointage == "SORTIE":
        type_pointage = "ENTREE"
        message = f"Bonjour {employe.nom} {employe.prenom} !"
    else:
        type_pointage = "SORTIE"
        message = f"Au revoir {employe.nom} {employe.prenom} !"
    
    pointage = Pointage(
        employe_id=employe.id,
        type_pointage=type_pointage,
        date_pointage=datetime.now(),
        mode="QR_CODE",
        statut="Valide"
    )
    db.add(pointage)
    db.commit()
    
    return {
        "status": "success",
        "message": message,
        "employe": {
            "nom": employe.nom,
            "prenom": employe.prenom,
            "type": type_pointage,
            "matricule": employe.matricule
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
