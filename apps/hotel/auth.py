"""
Module d'authentification et RBAC pour Gestion Hôtelière Omega
Rôles : admin, directeur, receptionniste, gouvernante, femme_chambre
"""
import sqlite3
import os
import hashlib
from functools import wraps
from flask import redirect, session, request, flash, render_template_string
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "/app/data/hotel.db")


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def init_auth(app):
    from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user

    app.secret_key = getattr(app, 'secret_key', None) or 'omega_hotel_2026_secret'
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = "Veuillez vous connecter pour accéder au système hôtelier."
    login_manager.login_message_category = "warning"

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
        role TEXT NOT NULL DEFAULT 'femme_chambre',
        actif INTEGER DEFAULT 1,
        dernier_login TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("SELECT COUNT(*) FROM utilisateurs")
    if c.fetchone()[0] == 0:
        seed = [
            ('admin',       hash_password('admin123'),       'Admin',   'Omega',    'admin@omega-hotel.sn',   '770000001', 'admin'),
            ('directeur1',  hash_password('directeur123'),   'Diop',    'Mamadou',  'dir@omega-hotel.sn',     '770000002', 'directeur'),
            ('reception1',  hash_password('reception123'),   'Ndiaye',  'Fatou',    'recep@omega-hotel.sn',   '770000003', 'receptionniste'),
            ('gouvernante1',hash_password('gouvernante123'), 'Fall',    'Aminata',  'gov@omega-hotel.sn',     '770000004', 'gouvernante'),
            ('menage1',     hash_password('menage123'),      'Ba',      'Moussa',   'menage@omega-hotel.sn',  '770000005', 'femme_chambre'),
        ]
        c.executemany("""INSERT INTO utilisateurs
            (username, password_hash, nom, prenom, email, telephone, role)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", seed)
    conn.commit()
    conn.close()

    class User(UserMixin):
        def __init__(self, id, username, nom, prenom, role, email='', telephone=''):
            self.id = id
            self.username = username
            self.nom = nom
            self.prenom = prenom
            self.role = role
            self.email = email
            self.telephone = telephone

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
            return User(row['id'], row['username'], row['nom'], row['prenom'],
                        row['role'], row['email'], row['telephone'])
        return None

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            h = hash_password(password)
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM utilisateurs WHERE username=? AND password_hash=? AND actif=1",
                      (username, h))
            row = c.fetchone()
            if row:
                c.execute("UPDATE utilisateurs SET dernier_login=? WHERE id=?",
                          (datetime.now().isoformat(), row['id']))
                conn.commit()
                conn.close()
                user = User(row['id'], row['username'], row['nom'], row['prenom'],
                            row['role'], row['email'], row['telephone'])
                login_user(user)
                log_action(row['id'], 'LOGIN', f"Rôle: {row['role']}")
                nxt = request.args.get('next') or '/'
                return redirect(nxt)
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


def directeur_required(f):
    return role_required('admin', 'directeur')(f)


def reception_required(f):
    return role_required('admin', 'directeur', 'receptionniste')(f)


def staff_required(f):
    return role_required('admin', 'directeur', 'receptionniste', 'gouvernante')(f)


def menage_required(f):
    return role_required('admin', 'directeur', 'gouvernante', 'femme_chambre')(f)


def log_action(user_id, action, details=''):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, action TEXT NOT NULL, details TEXT,
            ip TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("INSERT INTO audit_log (user_id, action, details, ip) VALUES (?, ?, ?, ?)",
                  (user_id, action, details, request.remote_addr if request else ''))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[LOG] {e}")


LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Omega Hôtel — Connexion</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}
body{background:linear-gradient(135deg,#451a03 0%,#92400e 50%,#d97706 100%);min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
.login-box{background:white;border-radius:24px;box-shadow:0 25px 60px rgba(0,0,0,0.4);width:100%;max-width:440px;overflow:hidden}
.login-header{background:linear-gradient(135deg,#451a03,#92400e);padding:40px 30px 30px;text-align:center;color:white;position:relative;overflow:hidden}
.login-header::before{content:'';position:absolute;top:-60px;right:-60px;width:180px;height:180px;background:rgba(255,215,0,0.15);border-radius:50%}
.login-header::after{content:'';position:absolute;bottom:-40px;left:-40px;width:120px;height:120px;background:rgba(255,215,0,0.1);border-radius:50%}
.logo-circle{width:90px;height:90px;background:white;border-radius:50%;margin:0 auto 20px;display:flex;justify-content:center;align-items:center;box-shadow:0 10px 30px rgba(0,0,0,0.2);position:relative;z-index:1}
.logo-circle i{font-size:2.5rem;background:linear-gradient(135deg,#92400e,#d97706);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.login-header h1{font-size:1.8rem;font-weight:800;position:relative;z-index:1;letter-spacing:0.5px}
.login-header h1 span{color:#fbbf24}
.login-header p{opacity:0.95;margin-top:8px;font-size:0.9rem;position:relative;z-index:1}
.login-body{padding:35px 30px}
.form-group{margin-bottom:18px}
.form-group label{display:block;font-weight:700;color:#92400e;margin-bottom:6px;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.5px}
.input-group{position:relative}
.input-group i{position:absolute;left:15px;top:50%;transform:translateY(-50%);color:#94a3b8;font-size:1rem}
.input-group input{width:100%;padding:14px 14px 14px 44px;border:2px solid #e2e8f0;border-radius:12px;font-size:0.95rem;transition:0.3s;background:#f8fafc}
.input-group input:focus{outline:none;border-color:#d97706;background:white;box-shadow:0 0 0 4px rgba(217,119,6,0.12)}
.btn-login{width:100%;padding:15px;background:linear-gradient(135deg,#92400e,#d97706);color:white;border:none;border-radius:12px;font-weight:800;font-size:1rem;cursor:pointer;letter-spacing:0.5px;transition:0.3s;box-shadow:0 10px 25px rgba(146,64,14,0.35);margin-top:8px}
.btn-login:hover{transform:translateY(-2px);box-shadow:0 15px 35px rgba(146,64,14,0.45)}
.flash{padding:12px 15px;border-radius:10px;margin-bottom:18px;font-size:0.85rem;display:flex;align-items:center;gap:8px}
.flash-danger{background:#fee2e2;color:#991b1b;border-left:4px solid #dc2626}
.flash-success{background:#dcfce7;color:#166534;border-left:4px solid #16a34a}
.flash-warning{background:#fef3c7;color:#92400e;border-left:4px solid #f59e0b}
.hint{text-align:center;margin-top:22px;padding-top:22px;border-top:1px dashed #cbd5e0;font-size:0.75rem;color:#64748b}
.hint code{background:#fffbeb;padding:2px 8px;border-radius:5px;color:#92400e;font-weight:700}
.footer-brand{text-align:center;padding:15px;background:#fffbeb;font-size:0.75rem;color:#64748b;border-top:1px solid #fde68a}
.footer-brand strong{color:#92400e}
.stars{color:#fbbf24;font-size:0.9rem;letter-spacing:2px}
</style>
</head>
<body>
<div class="login-box">
  <div class="login-header">
    <div class="logo-circle"><i class="fas fa-hotel"></i></div>
    <h1>OMEGA <span>HÔTEL</span></h1>
    <p class="stars">★★★★★</p>
    <p><i class="fas fa-crown"></i> Gestion hôtelière premium</p>
  </div>
  <div class="login-body">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}{% for cat, msg in messages %}
        <div class="flash flash-{{cat}}"><i class="fas fa-circle-info"></i> {{msg}}</div>
      {% endfor %}{% endif %}
    {% endwith %}
    <form method="POST">
      <div class="form-group">
        <label>Identifiant</label>
        <div class="input-group"><i class="fas fa-user"></i>
          <input type="text" name="username" placeholder="Entrez votre identifiant" required autofocus>
        </div>
      </div>
      <div class="form-group">
        <label>Mot de passe</label>
        <div class="input-group"><i class="fas fa-lock"></i>
          <input type="password" name="password" placeholder="Mot de passe" required>
        </div>
      </div>
      <button type="submit" class="btn-login"><i class="fas fa-arrow-right-to-bracket"></i> Se connecter</button>
    </form>
    <div class="hint">
      <div style="margin-bottom:8px;font-weight:700;color:#92400e">Comptes de démonstration</div>
      <div>Admin : <code>admin</code> / <code>admin123</code></div>
      <div>Directeur : <code>directeur1</code> / <code>directeur123</code></div>
      <div>Réceptionniste : <code>reception1</code> / <code>reception123</code></div>
      <div>Gouvernante : <code>gouvernante1</code> / <code>gouvernante123</code></div>
      <div>Femme de chambre : <code>menage1</code> / <code>menage123</code></div>
    </div>
  </div>
  <div class="footer-brand">Développé par <strong>OMEGA INFORMATIQUE</strong> — Dakar, Sénégal</div>
</div>
</body>
</html>
"""
