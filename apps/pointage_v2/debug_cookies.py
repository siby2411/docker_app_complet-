"""
Debug cookies — Aide au diagnostic des problèmes de session mobile
"""
from flask import Blueprint, request, jsonify, make_response, redirect
import json

debug_bp = Blueprint('debug', __name__)


def init_debug(app, **kwargs):
    app.register_blueprint(debug_bp)
    print("[DEBUG] ✅ Module debug enregistré")


@debug_bp.route('/debug-cookies')
def debug_cookies():
    """Affiche les infos de cookies/session du navigateur"""
    from flask import session, current_app
    
    # Infos navigateur
    ua = request.headers.get('User-Agent', '')
    accept = request.headers.get('Accept', '')
    cookies = request.cookies.to_dict()
    
    # Détecter mobile
    is_mobile = any(x in ua.lower() for x in ['mobile', 'android', 'iphone', 'ipad'])
    
    info = {
        'navigateur': ua[:200],
        'accept': accept,
        'mobile': is_mobile,
        'cookies_recus': list(cookies.keys()),
        'session_actuelle': dict(session) if session else {},
        'ip_client': request.remote_addr,
        'host': request.host,
        'secure_cookies_config': {
            'SESSION_COOKIE_SECURE': current_app.config.get('SESSION_COOKIE_SECURE'),
            'SESSION_COOKIE_SAMESITE': current_app.config.get('SESSION_COOKIE_SAMESITE'),
            'SESSION_COOKIE_HTTPONLY': current_app.config.get('SESSION_COOKIE_HTTPONLY'),
        },
    }
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Debug Cookies</title>
<style>
body{{font-family:system-ui;padding:20px;background:#f0fdff;color:#0e7490}}
.card{{background:white;border-radius:16px;padding:20px;margin-bottom:15px;box-shadow:0 4px 12px rgba(0,0,0,0.08)}}
h1{{color:#0e7490;margin-bottom:15px}}
h2{{color:#06b6d4;font-size:1rem;margin-bottom:10px}}
pre{{background:#f8fafc;padding:12px;border-radius:8px;overflow-x:auto;font-size:0.75rem}}
.ok{{color:#10b981;font-weight:800}}
.ko{{color:#dc2626;font-weight:800}}
.badge{{display:inline-block;padding:4px 10px;border-radius:20px;font-size:0.75rem;font-weight:800;margin:2px}}
.badge-green{{background:#d1fae5;color:#065f46}}
.badge-red{{background:#fee2e2;color:#991b1b}}
.badge-blue{{background:#dbeafe;color:#1e40af}}
</style>
</head>
<body>

<h1>🔍 Debug Cookies — Pointage V2</h1>

<div class="card">
  <h2>📱 Détection navigateur</h2>
  <div class="badge {'badge-green' if is_mobile else 'badge-blue'}">
    {'MOBILE' if is_mobile else 'DESKTOP'}
  </div>
  <pre>{ua[:300]}</pre>
</div>

<div class="card">
  <h2>🍪 Cookies reçus par le serveur</h2>
  <div>
    {''.join(f'<span class="badge {"badge-green" if c in ["session", "remember_token"] else "badge-blue"}">{c}</span>' for c in cookies.keys()) or '<span class="badge badge-red">AUCUN COOKIE</span>'}
  </div>
  <pre>{json.dumps(cookies, indent=2)}</pre>
</div>

<div class="card">
  <h2>🔐 Session Flask actuelle</h2>
  <pre>{json.dumps(dict(session), indent=2) if session else "AUCUNE SESSION — Cookies non conservés !"}</pre>
</div>

<div class="card">
  <h2>⚙️ Config cookies serveur</h2>
  <table style="width:100%;font-size:0.9rem">
    <tr><td><b>SESSION_COOKIE_SECURE</b></td><td>{current_app.config.get('SESSION_COOKIE_SECURE')}</td></tr>
    <tr><td><b>SESSION_COOKIE_SAMESITE</b></td><td>{current_app.config.get('SESSION_COOKIE_SAMESITE')}</td></tr>
    <tr><td><b>SESSION_COOKIE_HTTPONLY</b></td><td>{current_app.config.get('SESSION_COOKIE_HTTPONLY')}</td></tr>
    <tr><td><b>Host</b></td><td>{request.host}</td></tr>
    <tr><td><b>IP Client</b></td><td>{request.remote_addr}</td></tr>
  </table>
</div>

<div class="card">
  <h2>🧪 Test de cookie manuel</h2>
  <p style="font-size:0.9rem;margin-bottom:15px">Cliquez pour définir un cookie de test :</p>
  <a href="/debug-cookies/set" style="display:inline-block;padding:12px 20px;background:#10b981;color:white;text-decoration:none;border-radius:10px;font-weight:700;margin-right:8px">
    1️⃣ Définir cookie test
  </a>
  <a href="/debug-cookies" style="display:inline-block;padding:12px 20px;background:#0891b2;color:white;text-decoration:none;border-radius:10px;font-weight:700">
    2️⃣ Recharger cette page
  </a>
  <p style="font-size:0.85rem;color:#64748b;margin-top:15px">
    Si après ces 2 étapes, vous ne voyez PAS <code>test_cookie</code> dans la liste ci-dessus → <b>le navigateur bloque les cookies</b>.
  </p>
</div>

</body>
</html>
"""
    return html


@debug_bp.route('/debug-cookies/set')
def debug_set_cookie():
    """Définit un cookie de test"""
    response = make_response(redirect('/debug-cookies'))
    response.set_cookie('test_cookie', 'valeur_test_123', max_age=3600, httponly=False, samesite='Lax')
    return response


@debug_bp.route('/debug-cookies/clear')
def debug_clear_cookies():
    """Efface tous les cookies"""
    response = make_response(redirect('/debug-cookies'))
    for c in ['session', 'remember_token', 'test_cookie']:
        response.delete_cookie(c)
    return response


@debug_bp.route('/debug-login-test', methods=['GET', 'POST'])
def debug_login_test():
    """Formulaire de login simplifié pour test"""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        from flask import session
        session['debug_user'] = username
        session['debug_time'] = str(__import__('datetime').datetime.now())
        return redirect('/debug-cookies')
    
    return """
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Debug Login</title>
    <style>
    body{font-family:system-ui;padding:20px;background:#f0fdff;max-width:400px;margin:0 auto}
    input{width:100%;padding:12px;margin:8px 0;border:2px solid #a5f3fc;border-radius:10px;font-size:1rem}
    button{width:100%;padding:14px;background:linear-gradient(135deg,#0e7490,#06b6d4);color:white;border:none;border-radius:10px;font-weight:800;font-size:1rem;margin-top:10px}
    </style>
    </head>
    <body>
    <h1>🔐 Debug Login</h1>
    <form method="POST">
      <input type="text" name="username" placeholder="Username" required>
      <input type="password" name="password" placeholder="Password" required>
      <button type="submit">Tester login</button>
    </form>
    <p style="margin-top:20px;font-size:0.85rem;color:#64748b">
      Après login, vous verrez la session dans /debug-cookies
    </p>
    </body>
    </html>
    """
