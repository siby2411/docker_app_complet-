from flask import Flask, render_template_string, request, redirect, url_for, jsonify, flash, session
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
from datetime import datetime, timedelta
import json
import os
import secrets
import hashlib
import time

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

DB_PATH = "/app/data/commerciale.db"
os.makedirs("/app/data", exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            nom TEXT NOT NULL,
            prenom TEXT,
            email TEXT,
            telephone TEXT,
            adresse TEXT,
            ville TEXT,
            pays TEXT DEFAULT 'Senegal',
            type TEXT DEFAULT 'Particulier',
            secteur_activite TEXT,
            date_creation TEXT,
            statut TEXT DEFAULT 'Actif'
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS produits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            nom TEXT NOT NULL,
            description TEXT,
            categorie TEXT,
            prix_achat REAL DEFAULT 0,
            prix_vente REAL DEFAULT 0,
            quantite INTEGER DEFAULT 0,
            seuil_alerte INTEGER DEFAULT 5,
            date_creation TEXT,
            statut TEXT DEFAULT 'Actif'
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS factures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            client_id INTEGER NOT NULL,
            date_facture TEXT,
            date_echeance TEXT,
            statut TEXT DEFAULT 'En attente',
            montant_ht REAL DEFAULT 0,
            tva REAL DEFAULT 18,
            montant_ttc REAL DEFAULT 0,
            observations TEXT,
            date_creation TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)
    
    c.execute("SELECT COUNT(*) FROM clients")
    if c.fetchone()[0] == 0:
        clients = [
            ("CLT0001", "Sarr", "Aliou", "aliou.sarr@client.sn", "771234569", "Dakar", "Dakar", "Senegal", "Entreprise", "Distribution"),
            ("CLT0002", "Ba", "Aissatou", "aissatou.ba@client.sn", "772345680", "Thies", "Thies", "Senegal", "Particulier", "Services")
        ]
        c.executemany("INSERT INTO clients (code, nom, prenom, email, telephone, adresse, ville, pays, type, secteur_activite) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", clients)
        
        produits = [
            ("PRD0001", "Ordinateur Portable", "Laptop 15 pouces", "Informatique", 450000, 650000, 25, 5),
            ("PRD0002", "Papier A4", "Ramette 500 feuilles", "Fourniture", 2000, 3500, 100, 20)
        ]
        c.executemany("INSERT INTO produits (code, nom, description, categorie, prix_achat, prix_vente, quantite, seuil_alerte) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", produits)
        
        conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return get_db()

HTML_BASE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Omega Business</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; font-family:"Segoe UI",sans-serif; }
        body { background:#f0f4f8; }
        .header { background:linear-gradient(135deg,#1a237e,#0d47a1); padding:15px 30px; display:flex; justify-content:space-between; align-items:center; border-bottom:4px solid #ff6f00; flex-wrap:wrap; gap:10px; }
        .header h1 { color:white; font-size:1.5rem; }
        .header h1 span { color:#ff6f00; }
        .nav { background:white; padding:0 20px; display:flex; gap:2px; border-bottom:2px solid #e2e8f0; flex-wrap:wrap; }
        .nav a { padding:12px 18px; color:#4a5568; text-decoration:none; border-bottom:3px solid transparent; transition:0.3s; font-size:0.9rem; display:flex; align-items:center; gap:6px; }
        .nav a:hover { color:#1a237e; border-bottom-color:#1a237e; background:#f7fafc; }
        .container { max-width:1400px; margin:20px auto; padding:0 20px; }
        .card { background:white; border-radius:12px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,0.05); margin-top:20px; overflow-x:auto; }
        .card-header { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:15px; }
        .btn { padding:8px 16px; border:none; border-radius:6px; cursor:pointer; font-weight:600; display:inline-flex; align-items:center; gap:6px; text-decoration:none; transition:0.3s; font-size:0.85rem; }
        .btn-primary { background:#1a237e; color:white; }
        .btn-success { background:#2e7d32; color:white; }
        .btn-info { background:#1565c0; color:white; }
        .btn-sm { padding:4px 10px; font-size:0.75rem; }
        .footer { background:#1a237e; color:#a8b2d1; text-align:center; padding:15px; margin-top:30px; border-top:4px solid #ff6f00; font-size:0.85rem; }
        .footer span { color:#ff6f00; }
        .form-container { background:white; border-radius:12px; padding:25px; max-width:800px; margin:0 auto; box-shadow:0 2px 8px rgba(0,0,0,0.05); }
        .form-group { margin-bottom:12px; }
        .form-group label { display:block; font-weight:600; color:#4a5568; margin-bottom:4px; font-size:0.9rem; }
        .form-group input, .form-group select { width:100%; padding:8px 12px; border:2px solid #e2e8f0; border-radius:6px; font-size:0.9rem; }
        .form-row { display:grid; grid-template-columns:1fr 1fr; gap:15px; }
        @media (max-width:768px){ .form-row { grid-template-columns:1fr; } }
    </style>
</head>
<body>
<header class="header">
    <div><h1>💼 OMEGA <span>BUSINESS</span></h1></div>
</header>
<nav class="nav">
    <a href="/commerciale/"><i class="fas fa-home"></i> Dashboard</a>
    <a href="/commerciale/clients"><i class="fas fa-users"></i> Clients</a>
    <a href="/commerciale/produits"><i class="fas fa-box"></i> Produits</a>
    <a href="/commerciale/factures"><i class="fas fa-file-invoice"></i> Factures</a>
</nav>
<div class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="flash flash-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
</div>
<footer class="footer">&copy; 2026 <span>Omega Consulting</span> - Business</footer>
</body>
</html>
'''

@app.route("/")
def index():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM clients")
    total_clients = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM produits")
    total_produits = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM factures WHERE statut='En attente'")
    factures_attente = c.fetchone()[0]
    conn.close()
    
    content = '<div class="card"><h2>Dashboard</h2>'
    content += '<p>Total Clients: ' + str(total_clients) + '</p>'
    content += '<p>Total Produits: ' + str(total_produits) + '</p>'
    content += '<p>Factures en attente: ' + str(factures_attente) + '</p>'
    content += '</div>'
    return render_template_string(HTML_BASE.replace('{% block content %}{% endblock %}', content))

@app.route("/clients")
def clients():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM clients WHERE statut='Actif' ORDER BY nom")
    clients = c.fetchall()
    conn.close()
    
    content = '<div class="card"><div class="card-header"><h2>Clients</h2><a href="/commerciale/clients/ajouter" class="btn btn-success">Ajouter</a></div><table><thead><tr><th>Code</th><th>Nom</th><th>Telephone</th><th>Type</th><th>Actions</th></tr></thead><tbody>'
    for c in clients:
        content += '<tr><td>' + str(c[1]) + '</td><td>' + str(c[2]) + ' ' + str(c[3] or '') + '</td><td>' + str(c[6]) + '</td><td>' + str(c[9]) + '</td><td><a href="/commerciale/clients/' + str(c[0]) + '" class="btn btn-info btn-sm">Voir</a></td></tr>'
    content += '</tbody></table></div>'
    return render_template_string(HTML_BASE.replace('{% block content %}{% endblock %}', content))

@app.route("/clients/ajouter", methods=["GET", "POST"])
def ajouter_client():
    if request.method == "POST":
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO clients (code, nom, prenom, email, telephone, adresse, ville, pays, type, secteur_activite, date_creation, statut) VALUES ('', ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'Actif')", 
                 (request.form['nom'], request.form.get('prenom', ''), request.form.get('email', ''), request.form['telephone'], request.form.get('adresse', ''), request.form.get('ville', ''), request.form.get('pays', 'Senegal'), request.form.get('type', 'Particulier'), request.form.get('secteur_activite', '')))
        conn.commit()
        conn.close()
        flash('Client ajoute', 'success')
        return redirect("/commerciale/clients")
    
    content = '''
    <div class="form-container">
        <h2>Ajouter un Client</h2>
        <form method="POST">
            <div class="form-row">
                <div class="form-group"><label>Nom *</label><input type="text" name="nom" required></div>
                <div class="form-group"><label>Prenom</label><input type="text" name="prenom"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Telephone *</label><input type="text" name="telephone" required></div>
                <div class="form-group"><label>Email</label><input type="email" name="email"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Adresse</label><input type="text" name="adresse"></div>
                <div class="form-group"><label>Ville</label><input type="text" name="ville"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Type</label>
                    <select name="type">
                        <option value="Particulier">Particulier</option>
                        <option value="Entreprise">Entreprise</option>
                    </select>
                </div>
                <div class="form-group"><label>Secteur</label>
                    <select name="secteur_activite">
                        <option value="">Non specifie</option>
                        <option value="Distribution">Distribution</option>
                        <option value="Services">Services</option>
                        <option value="Industrie">Industrie</option>
                    </select>
                </div>
            </div>
            <button type="submit" class="btn btn-success" style="width:100%;">Enregistrer</button>
        </form>
        <br><a href="/commerciale/clients" class="btn btn-info">Retour</a>
    </div>
    '''
    return render_template_string(HTML_BASE.replace('{% block content %}{% endblock %}', content))

@app.route("/produits")
def produits():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM produits WHERE statut='Actif' ORDER BY nom")
    produits = c.fetchall()
    conn.close()
    
    content = '<div class="card"><div class="card-header"><h2>Produits</h2><a href="/commerciale/produits/ajouter" class="btn btn-success">Ajouter</a></div><table><thead><tr><th>Code</th><th>Nom</th><th>Prix Vente</th><th>Stock</th><th>Actions</th></tr></thead><tbody>'
    for p in produits:
        content += '<tr><td>' + str(p[1]) + '</td><td>' + str(p[2]) + '</td><td>' + str(p[6]) + ' FCFA</td><td>' + str(p[7]) + '</td><td><a href="/commerciale/produits/' + str(p[0]) + '" class="btn btn-info btn-sm">Voir</a></td></tr>'
    content += '</tbody></table></div>'
    return render_template_string(HTML_BASE.replace('{% block content %}{% endblock %}', content))

@app.route("/factures")
def factures():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT f.*, cl.nom, cl.prenom FROM factures f JOIN clients cl ON f.client_id = cl.id ORDER BY f.id DESC")
    factures = c.fetchall()
    conn.close()
    
    content = '<div class="card"><div class="card-header"><h2>Factures</h2><a href="/commerciale/factures/ajouter" class="btn btn-success">Nouvelle Facture</a></div><table><thead><tr><th>Numero</th><th>Client</th><th>Montant</th><th>Statut</th><th>Actions</th></tr></thead><tbody>'
    for f in factures:
        content += '<tr><td>' + str(f[1]) + '</td><td>' + str(f[11]) + ' ' + str(f[12] or '') + '</td><td>' + str(f[9]) + ' FCFA</td><td>' + str(f[5]) + '</td><td><a href="/commerciale/factures/' + str(f[0]) + '" class="btn btn-info btn-sm">Voir</a></td></tr>'
    content += '</tbody></table></div>'
    return render_template_string(HTML_BASE.replace('{% block content %}{% endblock %}', content))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
