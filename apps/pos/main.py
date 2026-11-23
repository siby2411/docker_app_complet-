from fastapi import FastAPI, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
import os
import json
import secrets
import hashlib
import calendar

app = FastAPI(title="Omega POS Restaurant Pro", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "/app/data/pos.db"
STATIC_DIR = "/app/static"

for dir_path in [os.path.dirname(DB_PATH), STATIC_DIR]:
    os.makedirs(dir_path, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}?check_same_thread=False&timeout=30"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==================== MODELES ====================

class Produit(Base):
    __tablename__ = "produits"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    nom = Column(String, nullable=False)
    description = Column(Text)
    prix = Column(Float, default=0)
    stock = Column(Integer, default=0)
    unite = Column(String, default="pièce")
    date_creation = Column(DateTime, default=func.now())
    statut = Column(String, default="Actif")

class Caissier(Base):
    __tablename__ = "caissiers"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    nom = Column(String, nullable=False)
    prenom = Column(String)
    email = Column(String, unique=True)
    password = Column(String)
    date_creation = Column(DateTime, default=func.now())
    statut = Column(String, default="Actif")

class SessionCaissier(Base):
    __tablename__ = "sessions_caissier"
    id = Column(Integer, primary_key=True, index=True)
    caissier_id = Column(Integer, ForeignKey("caissiers.id"))
    token = Column(String, unique=True, index=True)
    date_debut = Column(DateTime, default=func.now())
    date_fin = Column(DateTime)
    ip_address = Column(String)
    statut = Column(String, default="Active")

class Commande(Base):
    __tablename__ = "commandes"
    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String, unique=True, index=True)
    caissier_id = Column(Integer, ForeignKey("caissiers.id"))
    table_numero = Column(Integer)
    date_commande = Column(DateTime, default=func.now())
    statut = Column(String, default="Payée")
    montant_total = Column(Float, default=0)
    type_paiement = Column(String, default="Espèces")

class CommandeDetail(Base):
    __tablename__ = "commande_details"
    id = Column(Integer, primary_key=True, index=True)
    commande_id = Column(Integer, ForeignKey("commandes.id"))
    produit_id = Column(Integer, ForeignKey("produits.id"))
    quantite = Column(Integer, default=1)
    prix_unitaire = Column(Float, default=0)
    total = Column(Float, default=0)

# ==================== INITIALISATION ====================

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Base de données initialisée")
        db = SessionLocal()
        
        if db.query(Caissier).count() == 0:
            admin = Caissier(
                code="CAI0001",
                nom="Admin",
                prenom="System",
                email="admin@pos.com",
                password=hashlib.sha256("admin123".encode()).hexdigest(),
                statut="Actif"
            )
            db.add(admin)
            
            produits = [
                Produit(code="PRD0001", nom="Poulet DG", prix=4500, stock=50),
                Produit(code="PRD0002", nom="Thieboudienne", prix=3500, stock=40),
                Produit(code="PRD0003", nom="Yassa Poulet", prix=4000, stock=30),
                Produit(code="PRD0004", nom="Spaghetti", prix=2500, stock=60),
            ]
            for p in produits:
                db.add(p)
            
            db.commit()
        db.close()
        print("✅ Données initiales ajoutées")
    except Exception as e:
        print(f"⚠️ Erreur: {e}")

init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== FONCTION POUR GÉNÉRER LE TEMPLATE ====================

def get_template(content, active_page="pos", caissier_nom="Non connecté", is_connected=False):
    """Génère le template complet avec le contenu injecté"""
    
    # Menu avec l'état actif
    menu_items = [
        ("/pos", "fa-home", "POS", "pos"),
        ("/pos/produits", "fa-box", "Produits", "produits"),
        ("/pos/commandes", "fa-receipt", "Commandes", "commandes"),
        ("/pos/stats", "fa-chart-bar", "Statistiques", "stats"),
        ("/pos/etats", "fa-file-alt", "États Période", "etats"),
        ("/pos/produits/ajouter", "fa-plus-circle", "Ajouter Produit", "ajouter_produit"),
        ("/pos/caissiers", "fa-users", "Caissiers", "caissiers"),
        ("/pos/caissiers/ajouter", "fa-user-plus", "Ajouter Caissier", "ajouter_caissier"),
    ]
    
    menu_html = ""
    for url, icon, label, key in menu_items:
        active = "active" if key == active_page else ""
        menu_html += f'<a href="{url}" class="nav-link {active}"><i class="fas {icon}"></i> {label}</a>'
    
    # Bouton déconnexion
    logout_btn = ""
    if is_connected:
        logout_btn = '''
            <button onclick="deconnexion()" class="btn btn-omega-danger btn-sm-omega">
                <i class="fas fa-sign-out-alt"></i> Déconnexion
            </button>
        '''
    
    # Statut session
    session_status = '● Connecté' if is_connected else '● Hors ligne'
    session_color = '#34d399' if is_connected else '#fbbf24'
    
    return f'''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Omega POS Restaurant Pro</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --omega-primary: #ff6f00;
            --omega-primary-dark: #e65100;
            --omega-secondary: #1a237e;
            --omega-dark: #0a0e17;
            --omega-card-bg: rgba(255,255,255,0.04);
            --omega-border: rgba(255,255,255,0.06);
            --omega-text: rgba(255,255,255,0.85);
            --omega-text-muted: rgba(255,255,255,0.4);
        }}
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ background: var(--omega-dark); color: #fff; font-family: 'Inter', sans-serif; min-height: 100vh; }}
        .navbar-omega {{
            background: linear-gradient(135deg, #1a237e, #0d47a1) !important;
            border-bottom: 3px solid var(--omega-primary);
            box-shadow: 0 4px 30px rgba(0,0,0,0.4);
            padding: 12px 0;
        }}
        .navbar-omega .navbar-brand {{ font-weight: 800; font-size: 1.4rem; color: #fff !important; letter-spacing: -0.5px; }}
        .navbar-omega .navbar-brand span {{ color: var(--omega-primary); }}
        .navbar-omega .navbar-brand i {{ margin-right: 8px; }}
        .navbar-omega .badge-omega {{
            background: rgba(255,111,0,0.15);
            color: var(--omega-primary);
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.7rem;
            border: 1px solid rgba(255,111,0,0.15);
            font-weight: 600;
            letter-spacing: 0.5px;
        }}
        .navbar-omega .caissier-info {{
            color: rgba(255,255,255,0.6);
            font-size: 0.75rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .navbar-omega .caissier-info i {{ color: var(--omega-primary); }}
        .nav-omega {{
            background: var(--omega-card-bg);
            padding: 8px;
            border-radius: 12px;
            border: 1px solid var(--omega-border);
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }}
        .nav-omega .nav-link {{
            color: rgba(255,255,255,0.6) !important;
            border-radius: 8px;
            padding: 8px 18px;
            font-size: 0.85rem;
            font-weight: 500;
            transition: all 0.3s;
            border: 1px solid transparent;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .nav-omega .nav-link:hover {{
            background: rgba(255,111,0,0.08);
            color: var(--omega-primary) !important;
            border-color: rgba(255,111,0,0.1);
        }}
        .nav-omega .nav-link.active {{
            background: var(--omega-primary);
            color: #0a0e17 !important;
            font-weight: 600;
            border-color: var(--omega-primary);
            box-shadow: 0 4px 15px rgba(255,111,0,0.2);
        }}
        .card-omega {{
            background: var(--omega-card-bg);
            backdrop-filter: blur(10px);
            border: 1px solid var(--omega-border);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            transition: all 0.3s;
        }}
        .card-omega:hover {{ border-color: rgba(255,111,0,0.15); }}
        .card-omega .card-title {{
            color: var(--omega-primary);
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .btn-omega-primary {{
            background: var(--omega-primary);
            color: #0a0e17;
            border: none;
            padding: 8px 24px;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }}
        .btn-omega-primary:hover {{
            background: var(--omega-primary-dark);
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(255,111,0,0.3);
            color: #0a0e17;
        }}
        .btn-omega-success {{
            background: #34d399;
            color: #0a0e17;
            border: none;
            padding: 8px 24px;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }}
        .btn-omega-success:hover {{
            background: #2dcc8a;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(52,211,153,0.3);
            color: #0a0e17;
        }}
        .btn-omega-danger {{
            background: #ef4444;
            color: #fff;
            border: none;
            padding: 8px 24px;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }}
        .btn-omega-danger:hover {{
            background: #dc2626;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(239,68,68,0.3);
            color: #fff;
        }}
        .btn-omega-info {{
            background: #60a5fa;
            color: #0a0e17;
            border: none;
            padding: 8px 24px;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }}
        .btn-omega-info:hover {{
            background: #3b82f6;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(96,165,250,0.3);
            color: #0a0e17;
        }}
        .btn-sm-omega {{ padding: 4px 14px; font-size: 0.75rem; }}
        .btn-block-omega {{ width: 100%; display: block; }}
        .table-omega {{ color: #fff; border-collapse: collapse; width: 100%; }}
        .table-omega thead th {{
            color: var(--omega-text-muted);
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 2px solid var(--omega-border);
            padding: 12px 10px;
            font-weight: 600;
        }}
        .table-omega tbody td {{
            color: var(--omega-text);
            border-bottom: 1px solid var(--omega-border);
            padding: 12px 10px;
            font-size: 0.85rem;
        }}
        .table-omega tbody tr:hover {{ background: rgba(255,255,255,0.02); }}
        .badge-omega-paye, .badge-omega-actif {{
            background: rgba(52,211,153,0.15);
            color: #34d399;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.65rem;
            font-weight: 600;
        }}
        .badge-omega-inactif {{
            background: rgba(239,68,68,0.15);
            color: #ef4444;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.65rem;
            font-weight: 600;
        }}
        .stat-omega {{
            background: var(--omega-card-bg);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid var(--omega-border);
            transition: all 0.3s;
        }}
        .stat-omega:hover {{
            border-color: rgba(255,111,0,0.2);
            transform: translateY(-2px);
        }}
        .stat-omega .num {{ font-size: 2.2rem; font-weight: 800; color: var(--omega-primary); }}
        .stat-omega .label {{
            color: var(--omega-text-muted);
            font-size: 0.7rem;
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .product-card-omega {{
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            padding: 16px 12px;
            text-align: center;
            border: 1px solid var(--omega-border);
            cursor: pointer;
            transition: all 0.3s;
        }}
        .product-card-omega:hover {{
            background: rgba(255,111,0,0.08);
            border-color: var(--omega-primary);
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(255,111,0,0.1);
        }}
        .product-card-omega .name {{ font-size: 0.9rem; font-weight: 600; }}
        .product-card-omega .price {{ font-size: 1rem; color: var(--omega-primary); font-weight: 700; margin: 4px 0; }}
        .product-card-omega .stock {{ font-size: 0.65rem; color: rgba(255,255,255,0.3); }}
        .cart-item-omega {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--omega-border);
        }}
        .cart-item-omega:last-child {{ border-bottom: none; }}
        .cart-item-omega .item-info {{ flex: 1; }}
        .cart-item-omega .item-info .name {{ font-size: 0.9rem; font-weight: 500; }}
        .cart-item-omega .item-info .price {{ font-size: 0.8rem; color: var(--omega-primary); }}
        .cart-item-omega .item-qty {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .cart-item-omega .item-qty button {{
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--omega-border);
            color: #fff;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.3s;
        }}
        .cart-item-omega .item-qty button:hover {{
            background: var(--omega-primary);
            border-color: var(--omega-primary);
            transform: scale(1.1);
        }}
        .cart-item-omega .item-qty span {{ min-width: 24px; text-align: center; font-weight: 600; font-size: 1rem; }}
        .cart-total-omega {{
            text-align: right;
            padding: 16px 0;
            font-size: 1.3rem;
            border-top: 2px solid var(--omega-primary);
            margin-top: 12px;
        }}
        .cart-total-omega span {{ color: var(--omega-primary); font-weight: 700; font-size: 1.5rem; }}
        .form-control-omega {{
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid var(--omega-border) !important;
            color: #fff !important;
            border-radius: 8px !important;
            padding: 10px 14px !important;
            font-size: 0.9rem !important;
            transition: all 0.3s !important;
        }}
        .form-control-omega:focus {{
            border-color: var(--omega-primary) !important;
            box-shadow: 0 0 0 0.25rem rgba(255,111,0,0.1) !important;
            background: rgba(255,111,0,0.05) !important;
        }}
        .form-control-omega::placeholder {{ color: rgba(255,255,255,0.2) !important; }}
        .form-label-omega {{ color: var(--omega-text-muted); font-size: 0.85rem; margin-bottom: 4px; font-weight: 500; }}
        .login-box {{
            max-width: 420px;
            margin: 60px auto;
            padding: 40px;
            background: var(--omega-card-bg);
            border-radius: 16px;
            border: 1px solid var(--omega-border);
            backdrop-filter: blur(10px);
        }}
        .login-box h2 {{ text-align: center; color: var(--omega-primary); margin-bottom: 30px; font-weight: 700; }}
        .pos-layout-omega {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .pos-products-omega {{ max-height: 550px; overflow-y: auto; padding-right: 5px; }}
        .pos-products-omega::-webkit-scrollbar {{ width: 4px; }}
        .pos-products-omega::-webkit-scrollbar-track {{ background: rgba(255,255,255,0.05); border-radius: 4px; }}
        .pos-products-omega::-webkit-scrollbar-thumb {{ background: var(--omega-primary); border-radius: 4px; }}
        .pos-cart-omega {{ max-height: 550px; overflow-y: auto; padding-right: 5px; }}
        .pos-cart-omega::-webkit-scrollbar {{ width: 4px; }}
        .pos-cart-omega::-webkit-scrollbar-track {{ background: rgba(255,255,255,0.05); border-radius: 4px; }}
        .pos-cart-omega::-webkit-scrollbar-thumb {{ background: var(--omega-primary); border-radius: 4px; }}
        .grid-4-omega {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
        .grid-2-omega {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
        .footer-omega {{
            text-align: center;
            padding: 20px;
            margin-top: 30px;
            border-top: 1px solid var(--omega-border);
            color: var(--omega-text-muted);
            font-size: 0.8rem;
        }}
        .footer-omega span {{ color: var(--omega-primary); font-weight: 600; }}
        @media (max-width: 992px) {{ .pos-layout-omega {{ grid-template-columns: 1fr; }} }}
        @media (max-width: 768px) {{
            .grid-4-omega {{ grid-template-columns: 1fr 1fr; }}
            .grid-2-omega {{ grid-template-columns: 1fr; }}
            .navbar-omega .navbar-brand {{ font-size: 1.1rem; }}
            .login-box {{ margin: 30px 15px; padding: 25px; }}
            .stat-omega .num {{ font-size: 1.6rem; }}
        }}
        @media (max-width: 480px) {{ .grid-4-omega {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>

<nav class="navbar navbar-omega navbar-expand-lg">
    <div class="container">
        <a class="navbar-brand" href="/pos"><i class="fas fa-utensils"></i> OMEGA <span>POS</span></a>
        <div class="d-flex align-items-center gap-3 flex-wrap">
            <div class="caissier-info">
                <i class="fas fa-user-circle"></i>
                <span id="caissier-nom">{caissier_nom}</span>
                <span id="session-status" style="color:{session_color};font-size:0.6rem;">{session_status}</span>
            </div>
            <span class="badge-omega"><i class="fas fa-cash-register"></i> Restaurant Pro</span>
            {logout_btn}
        </div>
    </div>
</nav>

<div class="container mt-3">
    <div class="nav-omega d-flex flex-wrap gap-1" id="main-menu">
        {menu_html}
    </div>

    <div id="app-content">
        {content}
    </div>
</div>

<footer class="footer-omega">
    &copy; 2026 <span>Omega Consulting</span> &mdash; Informatique & Management &mdash; Sénégal
</footer>

<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    function deconnexion() {{
        if(confirm('Voulez-vous vous déconnecter ?')) {{
            localStorage.clear();
            window.location.href = '/pos/login';
        }}
    }}
</script>
</body>
</html>
'''

# ==================== ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def index():
    return RedirectResponse(url="/pos")

@app.get("/pos/login", response_class=HTMLResponse)
async def login_page():
    login_content = '''
    <div class="login-box">
        <h2><i class="fas fa-sign-in-alt"></i> Connexion</h2>
        <form id="login-form" onsubmit="return loginUser(event)">
            <div class="mb-3">
                <label class="form-label-omega">Email</label>
                <input type="email" id="login-email" class="form-control form-control-omega" placeholder="admin@pos.com" required>
            </div>
            <div class="mb-3">
                <label class="form-label-omega">Mot de passe</label>
                <input type="password" id="login-password" class="form-control form-control-omega" placeholder="••••••••" required>
            </div>
            <button type="submit" class="btn btn-omega-primary btn-block-omega">
                <i class="fas fa-sign-in-alt"></i> Se connecter
            </button>
        </form>
        <div id="login-error" style="color:#ef4444;margin-top:15px;text-align:center;display:none;"></div>
        <div style="text-align:center;margin-top:15px;color:rgba(255,255,255,0.3);font-size:0.75rem;">
            <p>Compte admin: <strong>admin@pos.com</strong> / <strong>admin123</strong></p>
        </div>
    </div>
    <script>
        function loginUser(e) {
            e.preventDefault();
            var email = document.getElementById('login-email').value;
            var password = document.getElementById('login-password').value;
            
            fetch('/pos/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, password: password })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    localStorage.setItem('pos_token', data.token);
                    localStorage.setItem('caissier_id', data.caissier_id);
                    localStorage.setItem('caissier_nom', data.caissier_nom);
                    window.location.href = '/pos';
                } else {
                    document.getElementById('login-error').textContent = data.message;
                    document.getElementById('login-error').style.display = 'block';
                }
            })
            .catch(err => {
                document.getElementById('login-error').textContent = 'Erreur: ' + err.message;
                document.getElementById('login-error').style.display = 'block';
            });
            return false;
        }
    </script>
    '''
    # Pour la page de login, on cache le menu
    return get_template(login_content, active_page="login", caissier_nom="Non connecté", is_connected=False)

@app.get("/pos", response_class=HTMLResponse)
async def pos_page(request: Request, db: Session = Depends(get_db)):
    # Vérifier la session via le header
    caissier_nom = request.headers.get('X-Caissier-Nom', 'Non connecté')
    is_connected = request.headers.get('X-Is-Connected', 'false') == 'true'
    
    produits = db.query(Produit).filter(Produit.statut == "Actif").all()
    caissiers = db.query(Caissier).filter(Caissier.statut == "Actif").all()
    
    caissier_options = ""
    for c in caissiers:
        caissier_options += f'<option value="{c.id}">{c.nom} {c.prenom}</option>'
    
    content = f'''
    <div class="pos-layout-omega">
        <div class="card-omega pos-products-omega">
            <div class="card-title"><i class="fas fa-utensils"></i> Produits</div>
            <div class="grid-4-omega">
    '''
    
    for p in produits:
        content += f'''
        <div class="product-card-omega" onclick="addToCart({p.id}, '{p.nom}', {p.prix})">
            <div class="name">{p.nom}</div>
            <div class="price">{p.prix:,.0f} FCFA</div>
            <div class="stock">Stock: {p.stock}</div>
        </div>
        '''
    
    content += f'''
            </div>
        </div>
        
        <div class="card-omega pos-cart-omega">
            <div class="card-title"><i class="fas fa-shopping-cart"></i> Panier</div>
            <div id="cart-items"></div>
            <div class="cart-total-omega">
                Total: <span id="cart-total">0</span> FCFA
            </div>
            <div class="d-grid gap-2 d-md-flex mt-3">
                <button class="btn btn-omega-success flex-grow-1" onclick="validateOrder()"><i class="fas fa-check"></i> Valider</button>
                <button class="btn btn-omega-danger flex-grow-1" onclick="clearCart()"><i class="fas fa-trash"></i> Vider</button>
            </div>
            <div class="mt-3">
                <div class="row g-2">
                    <div class="col-6">
                        <label class="form-label-omega">Table</label>
                        <input type="number" id="table-number" class="form-control form-control-omega" value="1">
                    </div>
                    <div class="col-6">
                        <label class="form-label-omega">Paiement</label>
                        <select id="payment-type" class="form-control form-control-omega">
                            <option value="Espèces">Espèces</option>
                            <option value="Carte">Carte</option>
                            <option value="Orange Money">Orange Money</option>
                            <option value="Wave">Wave</option>
                        </select>
                    </div>
                </div>
                <div class="mt-2">
                    <label class="form-label-omega">Caissier</label>
                    <select id="caissier-select" class="form-control form-control-omega">
                        {caissier_options}
                    </select>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        var cart = [];
        var caissierId = localStorage.getItem('caissier_id') || 1;
        
        function addToCart(id, nom, prix) {{
            var existing = cart.find(item => item.id === id);
            if (existing) {{
                existing.quantite += 1;
            }} else {{
                cart.push({{ id: id, nom: nom, prix: prix, quantite: 1 }});
            }}
            updateCart();
        }}
        
        function updateCart() {{
            var html = '';
            var total = 0;
            cart.forEach(function(item, index) {{
                var itemTotal = item.prix * item.quantite;
                total += itemTotal;
                html += `
                    <div class="cart-item-omega">
                        <div class="item-info">
                            <div class="name">${{item.nom}}</div>
                            <div class="price">${{item.prix.toLocaleString()}} FCFA</div>
                        </div>
                        <div class="item-qty">
                            <button onclick="updateQty(${{index}}, -1)">-</button>
                            <span>${{item.quantite}}</span>
                            <button onclick="updateQty(${{index}}, 1)">+</button>
                            <button onclick="removeItem(${{index}})" class="btn btn-omega-danger" style="width:28px;height:28px;border-radius:50%;padding:0;font-size:0.9rem;">×</button>
                        </div>
                    </div>
                `;
            }});
            document.getElementById('cart-items').innerHTML = html;
            document.getElementById('cart-total').textContent = total.toLocaleString();
        }}
        
        function updateQty(index, delta) {{
            cart[index].quantite += delta;
            if (cart[index].quantite <= 0) {{
                cart.splice(index, 1);
            }}
            updateCart();
        }}
        
        function removeItem(index) {{
            cart.splice(index, 1);
            updateCart();
        }}
        
        function clearCart() {{
            cart = [];
            updateCart();
        }}
        
        function validateOrder() {{
            if (cart.length === 0) {{
                alert('Panier vide !');
                return;
            }}
            
            var table = document.getElementById('table-number').value;
            var paiement = document.getElementById('payment-type').value;
            var caissier_id = document.getElementById('caissier-select').value;
            
            fetch('/pos/api/commande', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ 
                    items: cart, 
                    table: table, 
                    paiement: paiement,
                    caissier_id: caissier_id
                }})
            }})
            .then(res => res.json())
            .then(data => {{
                if (data.status === 'success') {{
                    alert('✅ Commande validée !\\nNuméro: ' + data.commande.numero + '\\nTotal: ' + data.commande.total.toLocaleString() + ' FCFA');
                    clearCart();
                    window.location.reload();
                }} else {{
                    alert('❌ Erreur: ' + data.message);
                }}
            }})
            .catch(err => {{
                alert('❌ Erreur réseau: ' + err.message);
            }});
        }}
    </script>
    '''
    return get_template(content, active_page="pos", caissier_nom=caissier_nom, is_connected=is_connected)

@app.get("/pos/produits", response_class=HTMLResponse)
async def produits_page(request: Request, db: Session = Depends(get_db)):
    caissier_nom = request.headers.get('X-Caissier-Nom', 'Non connecté')
    is_connected = request.headers.get('X-Is-Connected', 'false') == 'true'
    
    produits = db.query(Produit).all()
    
    content = '''
    <div class="card-omega">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
            <div class="card-title mb-0"><i class="fas fa-box"></i> Produits</div>
            <a href="/pos/produits/ajouter" class="btn btn-omega-success btn-sm-omega"><i class="fas fa-plus"></i> Ajouter</a>
        </div>
        <div class="table-responsive">
            <table class="table table-omega">
                <thead>
                    <tr>
                        <th>Code</th>
                        <th>Nom</th>
                        <th>Prix</th>
                        <th>Stock</th>
                        <th>Statut</th>
                    </tr>
                </thead>
                <tbody>
    '''
    
    for p in produits:
        badge = "badge-omega-actif" if p.statut == "Actif" else "badge-omega-inactif"
        content += f'''
        <tr>
            <td><strong>{p.code}</strong></td>
            <td>{p.nom}</td>
            <td>{p.prix:,.0f} FCFA</td>
            <td>{p.stock}</td>
            <td><span class="{badge}">{p.statut}</span></td>
        </tr>
        '''
    
    content += '''
                </tbody>
            </table>
        </div>
    </div>
    '''
    return get_template(content, active_page="produits", caissier_nom=caissier_nom, is_connected=is_connected)

@app.get("/pos/produits/ajouter", response_class=HTMLResponse)
async def ajouter_produit_page(request: Request):
    caissier_nom = request.headers.get('X-Caissier-Nom', 'Non connecté')
    is_connected = request.headers.get('X-Is-Connected', 'false') == 'true'
    
    content = '''
    <div class="card-omega" style="max-width:600px;margin:0 auto;">
        <div class="card-title"><i class="fas fa-plus-circle"></i> Ajouter un Produit</div>
        <form method="POST" action="/pos/produits/ajouter">
            <div class="row g-2">
                <div class="col-12">
                    <label class="form-label-omega">Nom *</label>
                    <input type="text" name="nom" class="form-control form-control-omega" required>
                </div>
                <div class="col-6">
                    <label class="form-label-omega">Prix *</label>
                    <input type="number" name="prix" step="0.01" min="0" class="form-control form-control-omega" required>
                </div>
                <div class="col-6">
                    <label class="form-label-omega">Stock</label>
                    <input type="number" name="stock" min="0" value="0" class="form-control form-control-omega">
                </div>
                <div class="col-12">
                    <label class="form-label-omega">Unité</label>
                    <select name="unite" class="form-control form-control-omega">
                        <option value="pièce">pièce</option>
                        <option value="portion">portion</option>
                    </select>
                </div>
                <div class="col-12">
                    <button type="submit" class="btn btn-omega-success btn-block-omega"><i class="fas fa-save"></i> Enregistrer</button>
                </div>
                <div class="col-12">
                    <a href="/pos/produits" class="btn btn-omega-info btn-block-omega"><i class="fas fa-arrow-left"></i> Retour</a>
                </div>
            </div>
        </form>
    </div>
    '''
    return get_template(content, active_page="ajouter_produit", caissier_nom=caissier_nom, is_connected=is_connected)

@app.post("/pos/produits/ajouter")
async def create_produit(
    nom: str = Form(...),
    prix: float = Form(...),
    stock: int = Form(0),
    unite: str = Form("pièce"),
    db: Session = Depends(get_db)
):
    try:
        count = db.query(Produit).count() + 1
        code = f"PRD{count:04d}"
        produit = Produit(code=code, nom=nom, prix=prix, stock=stock, unite=unite, statut="Actif")
        db.add(produit)
        db.commit()
        return RedirectResponse(url="/pos/produits", status_code=303)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/pos/commandes", response_class=HTMLResponse)
async def commandes_page(request: Request, db: Session = Depends(get_db)):
    caissier_nom = request.headers.get('X-Caissier-Nom', 'Non connecté')
    is_connected = request.headers.get('X-Is-Connected', 'false') == 'true'
    
    commandes = db.query(Commande).order_by(Commande.id.desc()).limit(50).all()
    
    content = '''
    <div class="card-omega">
        <div class="card-title"><i class="fas fa-receipt"></i> Dernières Commandes</div>
        <div class="table-responsive">
            <table class="table table-omega">
                <thead>
                    <tr>
                        <th>Numéro</th>
                        <th>Table</th>
                        <th>Total</th>
                        <th>Statut</th>
                        <th>Caissier</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
    '''
    
    for c in commandes:
        caissier = db.query(Caissier).filter(Caissier.id == c.caissier_id).first()
        nom_caissier = f"{caissier.nom} {caissier.prenom}" if caissier else "N/A"
        content += f'''
        <tr>
            <td><strong>{c.numero}</strong></td>
            <td>{c.table_numero}</td>
            <td>{c.montant_total:,.0f} FCFA</td>
            <td><span class="badge-omega-paye">{c.statut}</span></td>
            <td>{nom_caissier}</td>
            <td>{c.date_commande.strftime("%d/%m %H:%M")}</td>
        </tr>
        '''
    
    content += '''
                </tbody>
            </table>
        </div>
    </div>
    '''
    return get_template(content, active_page="commandes", caissier_nom=caissier_nom, is_connected=is_connected)

@app.get("/pos/stats", response_class=HTMLResponse)
async def stats_page(request: Request, db: Session = Depends(get_db)):
    caissier_nom = request.headers.get('X-Caissier-Nom', 'Non connecté')
    is_connected = request.headers.get('X-Is-Connected', 'false') == 'true'
    
    total_commandes = db.query(Commande).count()
    total_ventes = db.query(Commande).filter(Commande.statut == "Payée").count()
    montant_total = db.query(func.sum(Commande.montant_total)).filter(Commande.statut == "Payée").scalar() or 0
    
    top_produits = db.query(
        CommandeDetail.produit_id,
        func.sum(CommandeDetail.quantite).label('total_qte'),
        func.sum(CommandeDetail.total).label('total_montant')
    ).group_by(CommandeDetail.produit_id).order_by(func.sum(CommandeDetail.quantite).desc()).limit(5).all()
    
    top_html = ""
    for tp in top_produits:
        produit = db.query(Produit).filter(Produit.id == tp.produit_id).first()
        if produit:
            top_html += f'<tr><td>{produit.nom}</td><td>{tp.total_qte}</td><td>{tp.total_montant:,.0f} FCFA</td></tr>'
    if not top_html:
        top_html = '<tr><td colspan="3" style="text-align:center;color:rgba(255,255,255,0.3);">Aucune donnée</td></tr>'
    
    stats_caissier = db.query(
        Caissier.nom, Caissier.prenom,
        func.count(Commande.id).label('nb_ventes'),
        func.sum(Commande.montant_total).label('total')
    ).join(Commande, Commande.caissier_id == Caissier.id)\
     .filter(Commande.statut == "Payée")\
     .group_by(Caissier.id).all()
    
    caissier_html = ""
    for sc in stats_caissier:
        caissier_html += f'<tr><td>{sc.nom} {sc.prenom}</td><td>{sc.nb_ventes}</td><td>{sc.total:,.0f} FCFA</td></tr>'
    if not caissier_html:
        caissier_html = '<tr><td colspan="3" style="text-align:center;color:rgba(255,255,255,0.3);">Aucune donnée</td></tr>'
    
    content = f'''
    <div class="row g-3 mb-3">
        <div class="col-md-4">
            <div class="stat-omega">
                <div class="num">{total_commandes}</div>
                <div class="label">Total Commandes</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="stat-omega">
                <div class="num">{total_ventes}</div>
                <div class="label">Ventes Finalisées</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="stat-omega">
                <div class="num">{montant_total:,.0f} FCFA</div>
                <div class="label">Chiffre d\'Affaires</div>
            </div>
        </div>
    </div>
    
    <div class="grid-2-omega">
        <div class="card-omega">
            <div class="card-title"><i class="fas fa-trophy"></i> Top 5 Meilleurs Produits</div>
            <div class="table-responsive">
                <table class="table table-omega">
                    <thead>
                        <tr>
                            <th>Produit</th>
                            <th>Quantité</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>{top_html}</tbody>
                </table>
            </div>
        </div>
        
        <div class="card-omega">
            <div class="card-title"><i class="fas fa-user-tie"></i> Performance par Caissier</div>
            <div class="table-responsive">
                <table class="table table-omega">
                    <thead>
                        <tr>
                            <th>Caissier</th>
                            <th>Ventes</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>{caissier_html}</tbody>
                </table>
            </div>
        </div>
    </div>
    '''
    return get_template(content, active_page="stats", caissier_nom=caissier_nom, is_connected=is_connected)

@app.get("/pos/etats", response_class=HTMLResponse)
async def etats_page(request: Request, db: Session = Depends(get_db)):
    caissier_nom = request.headers.get('X-Caissier-Nom', 'Non connecté')
    is_connected = request.headers.get('X-Is-Connected', 'false') == 'true'
    
    mois = request.query_params.get('mois', datetime.now().strftime('%Y-%m'))
    caissier_id = request.query_params.get('caissier_id', '')
    
    try:
        annee, mois_num = map(int, mois.split('-'))
        date_debut = datetime(annee, mois_num, 1)
        dernier_jour = calendar.monthrange(annee, mois_num)[1]
        date_fin = datetime(annee, mois_num, dernier_jour, 23, 59, 59)
    except:
        date_debut = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        date_fin = datetime.now().replace(day=1, hour=23, minute=59, second=59)
    
    query = db.query(Commande).filter(
        Commande.date_commande >= date_debut,
        Commande.date_commande <= date_fin,
        Commande.statut == "Payée"
    )
    
    if caissier_id and caissier_id != '':
        query = query.filter(Commande.caissier_id == int(caissier_id))
    
    commandes = query.order_by(Commande.date_commande.desc()).all()
    
    total_commandes = len(commandes)
    montant_total = sum(c.montant_total for c in commandes)
    
    ventes_jour = db.query(
        func.date(Commande.date_commande).label('date'),
        func.count(Commande.id).label('nb_ventes'),
        func.sum(Commande.montant_total).label('total')
    ).filter(
        Commande.date_commande >= date_debut,
        Commande.date_commande <= date_fin,
        Commande.statut == "Payée"
    ).group_by(func.date(Commande.date_commande)).order_by(func.date(Commande.date_commande)).all()
    
    jour_html = ""
    for vj in ventes_jour:
        jour_html += f'<tr><td>{vj.date}</td><td>{vj.nb_ventes}</td><td>{vj.total:,.0f} FCFA</td></tr>'
    if not jour_html:
        jour_html = '<tr><td colspan="3" style="text-align:center;color:rgba(255,255,255,0.3);">Aucune donnée</td></tr>'
    
    caissiers = db.query(Caissier).filter(Caissier.statut == "Actif").all()
    caissier_options = '<option value="">Tous les caissiers</option>'
    for c in caissiers:
        selected = 'selected' if str(c.id) == caissier_id else ''
        caissier_options += f'<option value="{c.id}" {selected}>{c.nom} {c.prenom}</option>'
    
    commandes_html = ""
    for c in commandes:
        caissier = db.query(Caissier).filter(Caissier.id == c.caissier_id).first()
        nom_caissier = f"{caissier.nom} {caissier.prenom}" if caissier else "N/A"
        commandes_html += f'''
        <tr>
            <td><strong>{c.numero}</strong></td>
            <td>{c.table_numero}</td>
            <td>{c.montant_total:,.0f} FCFA</td>
            <td>{nom_caissier}</td>
            <td>{c.date_commande.strftime("%d/%m/%Y %H:%M")}</td>
        </tr>
        '''
    
    if not commandes_html:
        commandes_html = '<tr><td colspan="5" style="text-align:center;color:rgba(255,255,255,0.3);">Aucune commande pour cette période</td></tr>'
    
    content = f'''
    <div class="card-omega">
        <div class="card-title"><i class="fas fa-file-alt"></i> États de la Période</div>
        
        <form method="GET" action="/pos/etats" class="d-flex gap-2 flex-wrap mb-3">
            <div>
                <label class="form-label-omega">Mois:</label>
                <select name="mois" class="form-control form-control-omega" onchange="this.form.submit()">
                    <option value="2026-01">Janvier 2026</option>
                    <option value="2026-02">Février 2026</option>
                    <option value="2026-03">Mars 2026</option>
                    <option value="2026-04">Avril 2026</option>
                    <option value="2026-05">Mai 2026</option>
                    <option value="2026-06">Juin 2026</option>
                    <option value="2026-07">Juillet 2026</option>
                    <option value="2026-08">Août 2026</option>
                    <option value="2026-09">Septembre 2026</option>
                    <option value="2026-10">Octobre 2026</option>
                    <option value="2026-11">Novembre 2026</option>
                    <option value="2026-12">Décembre 2026</option>
                </select>
            </div>
            <div>
                <label class="form-label-omega">Caissier:</label>
                <select name="caissier_id" class="form-control form-control-omega" onchange="this.form.submit()">
                    {caissier_options}
                </select>
            </div>
            <div class="d-flex align-items-end">
                <button type="submit" class="btn btn-omega-primary"><i class="fas fa-search"></i> Filtrer</button>
            </div>
        </form>
        
        <div class="row g-3 mb-3">
            <div class="col-md-6">
                <div class="stat-omega">
                    <div class="num">{total_commandes}</div>
                    <div class="label">Commandes</div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="stat-omega">
                    <div class="num">{montant_total:,.0f} FCFA</div>
                    <div class="label">Chiffre d\'Affaires</div>
                </div>
            </div>
        </div>
        
        <div class="grid-2-omega mb-3">
            <div class="card-omega">
                <div class="card-title"><i class="fas fa-calendar-day"></i> Ventes par Jour</div>
                <div class="table-responsive">
                    <table class="table table-omega">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Nb Commandes</th>
                                <th>Total</th>
                            </tr>
                        </thead>
                        <tbody>{jour_html}</tbody>
                    </table>
                </div>
            </div>
            
            <div class="card-omega">
                <div class="card-title"><i class="fas fa-list"></i> Détail des Commandes</div>
                <div class="table-responsive" style="max-height:300px;overflow-y:auto;">
                    <table class="table table-omega">
                        <thead>
                            <tr>
                                <th>Numéro</th>
                                <th>Table</th>
                                <th>Total</th>
                                <th>Caissier</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody>{commandes_html}</tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    '''
    return get_template(content, active_page="etats", caissier_nom=caissier_nom, is_connected=is_connected)

@app.get("/pos/caissiers", response_class=HTMLResponse)
async def caissiers_page(request: Request, db: Session = Depends(get_db)):
    caissier_nom = request.headers.get('X-Caissier-Nom', 'Non connecté')
    is_connected = request.headers.get('X-Is-Connected', 'false') == 'true'
    
    caissiers = db.query(Caissier).all()
    
    content = '''
    <div class="card-omega">
        <div class="card-title"><i class="fas fa-users"></i> Liste des Caissiers</div>
        <div class="table-responsive">
            <table class="table table-omega">
                <thead>
                    <tr>
                        <th>Code</th>
                        <th>Nom & Prénom</th>
                        <th>Email</th>
                        <th>Statut</th>
                    </tr>
                </thead>
                <tbody>
    '''
    
    for c in caissiers:
        badge = "badge-omega-actif" if c.statut == "Actif" else "badge-omega-inactif"
        content += f'''
        <tr>
            <td><strong>{c.code}</strong></td>
            <td>{c.nom} {c.prenom}</td>
            <td>{c.email}</td>
            <td><span class="{badge}">{c.statut}</span></td>
        </tr>
        '''
    
    content += '''
                </tbody>
            </table>
        </div>
    </div>
    '''
    return get_template(content, active_page="caissiers", caissier_nom=caissier_nom, is_connected=is_connected)

@app.get("/pos/caissiers/ajouter", response_class=HTMLResponse)
async def ajouter_caissier_page(request: Request):
    caissier_nom = request.headers.get('X-Caissier-Nom', 'Non connecté')
    is_connected = request.headers.get('X-Is-Connected', 'false') == 'true'
    
    content = '''
    <div class="card-omega" style="max-width:600px;margin:0 auto;">
        <div class="card-title"><i class="fas fa-user-plus"></i> Ajouter un Caissier</div>
        <form method="POST" action="/pos/caissiers/ajouter">
            <div class="row g-2">
                <div class="col-12">
                    <label class="form-label-omega">Nom *</label>
                    <input type="text" name="nom" class="form-control form-control-omega" required>
                </div>
                <div class="col-12">
                    <label class="form-label-omega">Prénom *</label>
                    <input type="text" name="prenom" class="form-control form-control-omega" required>
                </div>
                <div class="col-12">
                    <label class="form-label-omega">Email *</label>
                    <input type="email" name="email" class="form-control form-control-omega" required>
                </div>
                <div class="col-12">
                    <label class="form-label-omega">Mot de passe *</label>
                    <input type="password" name="password" class="form-control form-control-omega" required>
                </div>
                <div class="col-12">
                    <label class="form-label-omega">Confirmer *</label>
                    <input type="password" name="password_confirm" class="form-control form-control-omega" required>
                </div>
                <div class="col-12">
                    <button type="submit" class="btn btn-omega-success btn-block-omega"><i class="fas fa-save"></i> Enregistrer</button>
                </div>
                <div class="col-12">
                    <a href="/pos/caissiers" class="btn btn-omega-info btn-block-omega"><i class="fas fa-arrow-left"></i> Retour</a>
                </div>
            </div>
        </form>
    </div>
    '''
    return get_template(content, active_page="ajouter_caissier", caissier_nom=caissier_nom, is_connected=is_connected)

@app.post("/pos/caissiers/ajouter")
async def create_caissier(
    nom: str = Form(...),
    prenom: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        if password != password_confirm:
            return RedirectResponse(url="/pos/caissiers/ajouter", status_code=303)
        
        existing = db.query(Caissier).filter(Caissier.email == email).first()
        if existing:
            return RedirectResponse(url="/pos/caissiers/ajouter", status_code=303)
        
        count = db.query(Caissier).count() + 1
        code = f"CAI{count:04d}"
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        caissier = Caissier(
            code=code,
            nom=nom,
            prenom=prenom,
            email=email,
            password=hashed_password,
            statut="Actif"
        )
        db.add(caissier)
        db.commit()
        return RedirectResponse(url="/pos/caissiers", status_code=303)
    except Exception as e:
        return RedirectResponse(url="/pos/caissiers/ajouter", status_code=303)

# ==================== API ====================

@app.post("/pos/api/login")
async def login(data: dict, db: Session = Depends(get_db)):
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return {"status": "error", "message": "Email et mot de passe requis"}
    
    hashed = hashlib.sha256(password.encode()).hexdigest()
    caissier = db.query(Caissier).filter(Caissier.email == email, Caissier.password == hashed, Caissier.statut == "Actif").first()
    
    if not caissier:
        return {"status": "error", "message": "Identifiants incorrects"}
    
    token = secrets.token_hex(32)
    
    session = SessionCaissier(
        caissier_id=caissier.id,
        token=token,
        date_debut=datetime.now(),
        ip_address="192.168.1.90",
        statut="Active"
    )
    db.add(session)
    db.commit()
    
    return {
        "status": "success",
        "token": token,
        "caissier_id": caissier.id,
        "caissier_nom": f"{caissier.nom} {caissier.prenom}"
    }

@app.post("/pos/api/commande")
async def create_commande(data: dict, db: Session = Depends(get_db)):
    try:
        items = data.get('items', [])
        table = data.get('table', 1)
        paiement = data.get('paiement', 'Espèces')
        caissier_id = data.get('caissier_id', 1)
        
        if not items:
            return {"status": "error", "message": "Panier vide"}
        
        count = db.query(Commande).count() + 1
        numero = f"CMD{count:04d}"
        total = sum(item['prix'] * item['quantite'] for item in items)
        
        commande = Commande(
            numero=numero,
            caissier_id=caissier_id,
            table_numero=table,
            type_paiement=paiement,
            montant_total=total,
            statut="Payée",
            date_commande=datetime.now()
        )
        db.add(commande)
        db.commit()
        db.refresh(commande)
        
        for item in items:
            detail = CommandeDetail(
                commande_id=commande.id,
                produit_id=item['id'],
                quantite=item['quantite'],
                prix_unitaire=item['prix'],
                total=item['prix'] * item['quantite']
            )
            db.add(detail)
            produit = db.query(Produit).filter(Produit.id == item['id']).first()
            if produit:
                produit.stock -= item['quantite']
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Commande {numero} créée",
            "commande": {"numero": numero, "total": total, "table": table}
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
