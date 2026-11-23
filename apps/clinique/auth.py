"""
Module d'authentification et RBAC pour la Clinique Omega
Rôles : admin, medecin, infirmier, caisse, patient
"""
import sqlite3
import os
import hashlib
from functools import wraps
from flask import redirect, session, request, flash, render_template_string
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "/app/data/clinique.db")


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def hash_password(password):
    """Hash SHA256 simple (bcrypt nécessite compilation native)"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def init_auth(app):
    """Initialise Flask-Login, les routes login/logout et le user_loader"""
    from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user

    app.secret_key = getattr(app, 'secret_key', None) or 'omega_clinique_2026_secret'
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_message_category = "warning"

    # S'assurer que la table utilisateurs existe
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS utilisateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        email TEXT,
        telephone TEXT,
        role TEXT NOT NULL DEFAULT 'patient',
        actif INTEGER DEFAULT 1,
        dernier_login TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    # Comptes de démonstration
    c.execute("SELECT COUNT(*) FROM utilisateurs")
    if c.fetchone()[0] == 0:
        seed_users = [
            ('admin',      hash_password('admin123'),   'Admin',   'Omega',     'admin@omega.sn',   '770000001', 'admin'),
            ('medecin1',   hash_password('medecin123'), 'Diallo',  'Aminata',   'a.diallo@omega.sn','770000002', 'medecin'),
            ('infirmier1', hash_password('infirm123'),  'Sow',     'Moussa',    'm.sow@omega.sn',   '770000003', 'infirmier'),
            ('caisse1',    hash_password('caisse123'),  'Ndiaye',  'Fatou',     'f.ndiaye@omega.sn','770000004', 'caisse'),
            ('patient1',   hash_password('patient123'), 'Ba',      'Ousmane',   'o.ba@omega.sn',    '770000005', 'patient'),
        ]
        c.executemany("""INSERT INTO utilisateurs
            (username, password_hash, nom, prenom, email, telephone, role)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", seed_users)
    conn.commit()
    conn.close()

    class User(UserMixin):
        def __init__(self, id, username, nom, prenom, role, email=''):
            self.id = id
            self.username = username
            self.nom = nom
            self.prenom = prenom
            self.role = role
            self.email = email

        def has_role(self, *roles):
            return self.role in roles

    @login_manager.user_loader
    def load_user(user_id):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM utilisateurs WHERE id=? AND actif=1", (user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return User(row['id'], row['username'], row['nom'], row['prenom'], row['role'], row['email'])
        return None

    # ==================== ROUTE LOGIN ====================
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            h = hash_password(password)
            conn = get_db()
            c = conn.cursor()
            c.execute("""SELECT * FROM utilisateurs
                WHERE username=? AND password_hash=? AND actif=1""", (username, h))
            row = c.fetchone()
            if row:
                c.execute("UPDATE utilisateurs SET dernier_login=? WHERE id=?",
                          (datetime.now().isoformat(), row['id']))
                conn.commit()
                conn.close()
                user = User(row['id'], row['username'], row['nom'], row['prenom'], row['role'], row['email'])
                login_user(user)
                log_action(row['id'], 'LOGIN', f"Rôle: {row['role']}")
                next_page = request.args.get('next')
                return redirect(next_page or '/')
            conn.close()
            flash("Identifiants invalides", "danger")

        return render_template_string(LOGIN_TEMPLATE)

    @app.route('/logout')
    def logout():
        try:
            from flask_login import current_user as cu
            if cu.is_authenticated:
                log_action(cu.id, 'LOGOUT', '')
        except Exception:
            pass
        logout_user()
        flash("Déconnexion réussie", "success")
        return redirect('/login')

    return login_manager


def role_required(*roles):
    """Décorateur : exige un ou plusieurs rôles"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                from flask_login import current_user
                if not current_user.is_authenticated:
                    flash("Veuillez vous connecter", "warning")
                    return redirect('/login')
                if roles and current_user.role not in roles:
                    flash(f"Accès refusé — rôle requis : {', '.join(roles)}", "danger")
                    return redirect('/')
            except Exception:
                return redirect('/login')
            return f(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(f):
    return role_required('admin')(f)


def staff_required(f):
    """Médecin, infirmier, admin"""
    return role_required('admin', 'medecin', 'infirmier')(f)


def medecin_required(f):
    return role_required('admin', 'medecin')(f)


def caisse_required(f):
    return role_required('admin', 'caisse')(f)


def log_action(user_id, action, details=''):
    """Log une action dans audit_log"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("""INSERT INTO audit_log (user_id, action, details, ip)
            VALUES (?, ?, ?, ?)""",
            (user_id, action, details, request.remote_addr if request else ''))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[LOG] {e}")


# ==================== TEMPLATE LOGIN ====================
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Clinique Omega — Connexion</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',sans-serif}
body{background:linear-gradient(135deg,#0a4d68 0%,#088395 50%,#05bfdb 100%);min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
.login-box{background:white;border-radius:20px;box-shadow:0 25px 60px rgba(0,0,0,0.3);width:100%;max-width:440px;overflow:hidden}
.login-header{background:linear-gradient(135deg,#0a4d68,#088395);padding:35px 30px 30px;text-align:center;color:white;position:relative;overflow:hidden}
.login-header::before{content:'';position:absolute;top:-50px;right:-50px;width:150px;height:150px;background:rgba(255,255,255,0.08);border-radius:50%}
.login-header::after{content:'';position:absolute;bottom:-30px;left:-30px;width:100px;height:100px;background:rgba(255,255,255,0.06);border-radius:50%}
.logo-circle{width:80px;height:80px;background:white;border-radius:50%;margin:0 auto 18px;display:flex;justify-content:center;align-items:center;box-shadow:0 8px 25px rgba(0,0,0,0.15);position:relative;z-index:1}
.logo-circle i{font-size:2.5rem;background:linear-gradient(135deg,#0a4d68,#05bfdb);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.login-header h1{font-size:1.7rem;font-weight:700;position:relative;z-index:1;letter-spacing:0.5px}
.login-header h1 span{color:#05bfdb;font-weight:300}
.login-header p{opacity:0.9;margin-top:6px;font-size:0.85rem;position:relative;z-index:1}
.login-body{padding:35px 30px}
.form-group{margin-bottom:18px}
.form-group label{display:block;font-weight:600;color:#0a4d68;margin-bottom:6px;font-size:0.85rem}
.input-group{position:relative}
.input-group i{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:#94a3b8;font-size:1rem}
.input-group input{width:100%;padding:13px 14px 13px 42px;border:2px solid #e2e8f0;border-radius:10px;font-size:0.95rem;transition:0.3s;background:#f8fafc}
.input-group input:focus{outline:none;border-color:#05bfdb;background:white;box-shadow:0 0 0 4px rgba(5,191,219,0.1)}
.btn-login{width:100%;padding:14px;background:linear-gradient(135deg,#0a4d68,#088395);color:white;border:none;border-radius:10px;font-weight:700;font-size:1rem;cursor:pointer;letter-spacing:0.5px;transition:0.3s;box-shadow:0 8px 20px rgba(10,77,104,0.3);margin-top:5px}
.btn-login:hover{transform:translateY(-2px);box-shadow:0 12px 25px rgba(10,77,104,0.4)}
.flash{padding:12px 15px;border-radius:8px;margin-bottom:18px;font-size:0.85rem;display:flex;align-items:center;gap:8px}
.flash-danger{background:#fee2e2;color:#991b1b;border-left:4px solid #dc2626}
.flash-success{background:#dcfce7;color:#166534;border-left:4px solid #16a34a}
.hint{text-align:center;margin-top:22px;padding-top:22px;border-top:1px dashed #cbd5e0;font-size:0.78rem;color:#64748b}
.hint code{background:#f1f5f9;padding:2px 6px;border-radius:4px;color:#0a4d68;font-weight:600}
.footer-brand{text-align:center;padding:15px;background:#f8fafc;font-size:0.75rem;color:#64748b;border-top:1px solid #e2e8f0}
.footer-brand strong{color:#0a4d68}
</style>
</head>
<body>
<div class="login-box">
  <div class="login-header">
    <div class="logo-circle"><i class="fas fa-heart-pulse"></i></div>
    <h1>CLINIQUE <span>OMEGA</span></h1>
    <p><i class="fas fa-shield-halved"></i> Plateforme médicale sécurisée</p>
  </div>
  <div class="login-body">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}{% for cat, msg in messages %}
        <div class="flash flash-{{cat}}"><i class="fas fa-circle-info"></i> {{msg}}</div>
      {% endfor %}{% endif %}
    {% endwith %}
    <form method="POST">
      <div class="form-group">
        <label>Nom d'utilisateur</label>
        <div class="input-group">
          <i class="fas fa-user"></i>
          <input type="text" name="username" placeholder="Entrez votre identifiant" required autofocus>
        </div>
      </div>
      <div class="form-group">
        <label>Mot de passe</label>
        <div class="input-group">
          <i class="fas fa-lock"></i>
          <input type="password" name="password" placeholder="Entrez votre mot de passe" required>
        </div>
      </div>
      <button type="submit" class="btn-login"><i class="fas fa-right-to-bracket"></i> Se connecter</button>
    </form>
    <div class="hint">
      <div style="margin-bottom:8px;font-weight:600;color:#0a4d68">Comptes de démonstration</div>
      <div>Admin : <code>admin</code> / <code>admin123</code></div>
      <div>Médecin : <code>medecin1</code> / <code>medecin123</code></div>
      <div>Infirmier : <code>infirmier1</code> / <code>infirm123</code></div>
      <div>Caisse : <code>caisse1</code> / <code>caisse123</code></div>
      <div>Patient : <code>patient1</code> / <code>patient123</code></div>
    </div>
  </div>
  <div class="footer-brand">
    Développé par <strong>OMEGA INFORMATIQUE</strong> — Dakar, Sénégal
  </div>
</div>
</body>
</html>
"""
