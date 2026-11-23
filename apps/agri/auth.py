"""
🌾 AgriSénégal V2 — Authentification & Autorisations
7 rôles : admin, direction, cooperative, producteur, technicien, finance, acheteur
"""
from flask import request, redirect, flash, render_template_string
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
import sqlite3
import hashlib
from datetime import datetime

DB_PATH = "/app/data/agri.db"
login_manager = LoginManager()
_auth_ok = False


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _hash(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()


class User(UserMixin):
    def __init__(self, row):
        self.id = row['id']
        self.username = row['username']
        self.nom = row['nom'] or ''
        self.prenom = row['prenom'] or ''
        self.email = row['email'] or ''
        self.role = row['role'] or 'producteur'
        self.producteur_id = row['producteur_id'] if 'producteur_id' in row.keys() else None
        self.cooperative_id = row['cooperative_id'] if 'cooperative_id' in row.keys() else None
        self.village_id = row['village_id'] if 'village_id' in row.keys() else None
        self.region_id = row['region_id'] if 'region_id' in row.keys() else None
        self.langue = row['langue'] if 'langue' in row.keys() else 'fr'
        self.actif = row['actif'] if 'actif' in row.keys() else 1

    def is_active(self):
        return bool(self.actif)

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM utilisateurs WHERE id=?", (user_id,))
        row = c.fetchone()
        conn.close()
        return User(row) if row else None
    except Exception as e:
        print(f"[AUTH] load_user: {e}")
        return None


def log_action(user_id, action, details='', entity=None, entity_id=None):
    try:
        conn = get_db()
        c = conn.cursor()
        ip = ua = ''
        try:
            ip = request.remote_addr or ''
            ua = request.headers.get('User-Agent', '')[:200]
        except Exception:
            pass
        c.execute("""INSERT INTO audit_log
            (user_id, action, entity, entity_id, details, ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, action, entity, entity_id, details, ip, ua))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[LOG] {e}")


def role_required(*roles):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not (current_user and current_user.is_authenticated):
                return redirect('/login')
            if current_user.role not in roles:
                flash("Accès non autorisé", "danger")
                return redirect('/')
            return f(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not (current_user and current_user.is_authenticated and current_user.role == 'admin'):
            flash("Réservé administrateurs", "danger")
            return redirect('/')
        return f(*args, **kwargs)
    return wrapper


def staff_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not (current_user and current_user.is_authenticated and
                current_user.role in ('admin', 'direction', 'cooperative', 'technicien', 'finance')):
            flash("Accès réservé au personnel", "danger")
            return redirect('/')
        return f(*args, **kwargs)
    return wrapper


def producer_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not (current_user and current_user.is_authenticated and
                current_user.role in ('admin', 'direction', 'cooperative', 'producteur', 'technicien')):
            flash("Accès réservé producteurs", "danger")
            return redirect('/')
        return f(*args, **kwargs)
    return wrapper


def init_auth(app):
    global _auth_ok
    login_manager.init_app(app)
    login_manager.login_view = 'auth_login'
    login_manager.login_message = 'Veuillez vous connecter'
    login_manager.login_message_category = 'warning'

    @app.route('/login', methods=['GET', 'POST'])
    def auth_login():
        if request.method == 'POST':
            username = (request.form.get('username') or '').strip().lower()
            password = request.form.get('password') or ''
            if not username or not password:
                flash("Username et mot de passe requis", "warning")
                return redirect('/login')

            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM utilisateurs WHERE username=? AND actif=1", (username,))
            row = c.fetchone()

            if row and row['password_hash'] == _hash(password):
                user = User(row)
                login_user(user, remember=True)
                try:
                    c.execute("UPDATE utilisateurs SET dernier_login=? WHERE id=?",
                              (datetime.now().isoformat(), row['id']))
                    conn.commit()
                except Exception:
                    pass
                conn.close()
                log_action(user.id, 'LOGIN', f"Connexion depuis {request.remote_addr}")
                flash(f"Bienvenue {user.prenom} !", "success")
                return redirect('/')
            else:
                conn.close()
                flash("Identifiants invalides", "danger")
                return redirect('/login')

        return render_login_page()

    @app.route('/logout')
    def auth_logout():
        try:
            if current_user and current_user.is_authenticated:
                log_action(current_user.id, 'LOGOUT', 'Déconnexion')
                logout_user()
        except Exception:
            pass
        flash("Déconnecté", "info")
        return redirect('/login')

    _auth_ok = True
    print("[AUTH] ✅ Module auth complet chargé")


def render_login_page():
    html = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AgriSénégal — Connexion</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}
body{background:linear-gradient(135deg,#065f46 0%,#10b981 50%,#34d399 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;position:relative;overflow:hidden}
body::before{content:'';position:absolute;top:-100px;right:-100px;width:400px;height:400px;background:rgba(255,255,255,0.1);border-radius:50%}
body::after{content:'';position:absolute;bottom:-150px;left:-100px;width:500px;height:500px;background:rgba(255,255,255,0.08);border-radius:50%}
.login-box{background:white;border-radius:24px;padding:50px 40px;max-width:460px;width:100%;box-shadow:0 25px 60px rgba(0,0,0,0.3);position:relative;z-index:1}
.logo{text-align:center;margin-bottom:32px}
.logo-icon{width:90px;height:90px;background:linear-gradient(135deg,#065f46,#10b981);border-radius:22px;display:flex;align-items:center;justify-content:center;color:white;font-size:2.6rem;margin:0 auto 20px;box-shadow:0 12px 32px rgba(16,185,129,0.4)}
.logo h1{font-size:1.7rem;color:#065f46;font-weight:900;letter-spacing:-0.5px}
.logo h1 span{color:#10b981}
.logo p{color:#64748b;font-size:0.82rem;margin-top:8px;letter-spacing:1.5px;text-transform:uppercase;font-weight:700}
.form-group{margin-bottom:20px}
.form-group label{display:block;color:#065f46;font-weight:800;margin-bottom:8px;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.5px}
.form-group .input-wrap{position:relative}
.form-group .input-wrap i{position:absolute;left:16px;top:50%;transform:translateY(-50%);color:#10b981;font-size:1rem}
.form-group input{width:100%;padding:14px 16px 14px 46px;border:2px solid #f1f5f9;border-radius:12px;font-size:0.95rem;background:#f8fafc;transition:0.3s}
.form-group input:focus{outline:none;border-color:#10b981;background:white;box-shadow:0 0 0 4px rgba(16,185,129,0.1)}
.btn-login{width:100%;padding:15px;background:linear-gradient(135deg,#065f46,#10b981);color:white;border:none;border-radius:12px;font-weight:800;font-size:1rem;cursor:pointer;transition:0.3s;box-shadow:0 8px 24px rgba(16,185,129,0.35)}
.btn-login:hover{transform:translateY(-2px);box-shadow:0 12px 32px rgba(16,185,129,0.45)}
.flash{padding:14px 18px;border-radius:12px;margin-bottom:20px;font-size:0.9rem;font-weight:600;display:flex;align-items:center;gap:10px}
.flash-danger{background:#fee2e2;color:#991b1b;border-left:4px solid #dc2626}
.flash-success{background:#d1fae5;color:#065f46;border-left:4px solid #10b981}
.flash-warning{background:#fef3c7;color:#92400e;border-left:4px solid #f59e0b}
.flash-info{background:#dbeafe;color:#1e40af;border-left:4px solid #3b82f6}
.demo-accounts{margin-top:24px;padding-top:24px;border-top:2px dashed #d1fae5}
.demo-accounts h4{font-size:0.75rem;color:#64748b;text-transform:uppercase;letter-spacing:1.5px;font-weight:800;margin-bottom:12px;text-align:center}
.demo-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.demo-account{background:#ecfdf5;padding:8px 12px;border-radius:8px;font-size:0.7rem;cursor:pointer;transition:0.2s;text-align:center;border:1px solid #a7f3d0}
.demo-account:hover{background:#a7f3d0;transform:translateY(-2px)}
.demo-account strong{display:block;font-weight:800;color:#065f46;font-size:0.75rem}
.demo-account span{color:#10b981;font-family:monospace;font-size:0.68rem}
.kente-banner{position:absolute;top:0;left:0;right:0;height:6px;background:linear-gradient(90deg,#065f46,#10b981,#34d399,#fbbf24,#10b981)}
</style>
</head>
<body>
<div class="login-box">
  <div class="kente-banner"></div>
  <div class="logo">
    <div class="logo-icon"><i class="fas fa-seedling"></i></div>
    <h1>AGRI<span>SÉNÉGAL</span></h1>
    <p>Agriculture connectée · Sénégal</p>
  </div>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="flash flash-{{ cat }}"><i class="fas fa-circle-info"></i> {{ msg }}</div>
    {% endfor %}
  {% endwith %}

  <form method="POST">
    <div class="form-group">
      <label>Identifiant</label>
      <div class="input-wrap">
        <i class="fas fa-user"></i>
        <input type="text" name="username" required autofocus placeholder="admin">
      </div>
    </div>
    <div class="form-group">
      <label>Mot de passe</label>
      <div class="input-wrap">
        <i class="fas fa-lock"></i>
        <input type="password" name="password" required placeholder="••••••••">
      </div>
    </div>
    <button type="submit" class="btn-login">
      <i class="fas fa-right-to-bracket"></i> Se connecter
    </button>
  </form>

  <div class="demo-accounts">
    <h4>Comptes de démonstration</h4>
    <div class="demo-grid">
      <div class="demo-account" onclick="fill('admin','admin123')">
        <strong>Admin</strong><span>admin / admin123</span>
      </div>
      <div class="demo-account" onclick="fill('direction','dir123')">
        <strong>Direction</strong><span>direction / dir123</span>
      </div>
      <div class="demo-account" onclick="fill('coop1','coop123')">
        <strong>Coopérative</strong><span>coop1 / coop123</span>
      </div>
      <div class="demo-account" onclick="fill('prod1','prod123')">
        <strong>Producteur</strong><span>prod1 / prod123</span>
      </div>
      <div class="demo-account" onclick="fill('tech1','tech123')">
        <strong>Technicien</strong><span>tech1 / tech123</span>
      </div>
      <div class="demo-account" onclick="fill('fin1','fin123')">
        <strong>Finance</strong><span>fin1 / fin123</span>
      </div>
    </div>
  </div>
</div>
<script>
function fill(u, p) {
  document.querySelector('input[name="username"]').value = u;
  document.querySelector('input[name="password"]').value = p;
  document.querySelector('input[name="username"]').focus();
}
</script>
</body>
</html>
"""
    return render_template_string(html)
