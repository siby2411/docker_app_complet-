"""
📲 Omega Agro-Industrie — SMS & Notifications
Alerte stock · NC · Contrats · Mode simulation (pas de vraie API)
"""
from flask import Blueprint, request, redirect, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import sqlite3
import json
import os

sms_bp = Blueprint('sms_notifications', __name__)
_deps = {}

# Mode simulation par défaut (aucune clé API requise)
SMS_MODE = os.environ.get('SMS_MODE', 'simulation')  # simulation | orange | twilio


def init_sms(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(sms_bp)
    _ensure_table()
    print(f"[SMS] ✅ Module SMS & Notifications enregistré (mode: {SMS_MODE})")


def _db():
    return _deps['get_db']()


def _render(content, active='sms', title='SMS'):
    return _deps['render_page'](content, active=active, page_title=title)


def _rows(cur):
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _row(cur):
    cols = [c[0] for c in cur.description]
    r = cur.fetchone()
    return dict(zip(cols, r)) if r else None


def _log(action, details='', entity=None, entity_id=None):
    try:
        uid = current_user.id if (current_user and current_user.is_authenticated) else None
        _deps['log_action'](uid, action, details, entity=entity, entity_id=entity_id)
    except Exception:
        pass


def _ensure_table():
    try:
        db = _db()
        cur = db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sms_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                destinataire TEXT NOT NULL,
                message TEXT NOT NULL,
                statut TEXT DEFAULT 'envoye',
                mode TEXT,
                date_envoi TEXT,
                created_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titre TEXT NOT NULL,
                message TEXT,
                type TEXT DEFAULT 'info',
                entity TEXT,
                entity_id INTEGER,
                lu INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        db.commit()
    except Exception as e:
        print(f"[SMS] ⚠️ Erreur création tables : {e}")


def _send_sms(destinataire, message):
    """Envoi SMS — mode simulation par défaut (aucune dépendance externe)."""
    if SMS_MODE == 'simulation':
        print(f"[SMS-SIMU] → {destinataire} : {message[:80]}...")
        return True, 'simulation'

    if SMS_MODE == 'orange':
        # Intégration Orange SMS API (Sénégal)
        import requests
        try:
            token = os.environ.get('ORANGE_SMS_TOKEN', '')
            url = "https://api.orange.com/smsmessaging/v1/outbound/tel%3A%2B2210000/requests"
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            payload = {
                "outboundSMSMessageRequest": {
                    "address": f"tel:+221{destinataire.lstrip('+221')}",
                    "senderAddress": "tel:+2210000",
                    "outboundSMSTextMessage": {"message": message}
                }
            }
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            return r.status_code in (200, 201), 'orange'
        except Exception as e:
            print(f"[SMS-ORANGE] ❌ {e}")
            return False, 'orange'

    if SMS_MODE == 'twilio':
        import requests
        try:
            sid = os.environ.get('TWILIO_SID', '')
            token = os.environ.get('TWILIO_TOKEN', '')
            from_num = os.environ.get('TWILIO_FROM', '')
            url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
            r = requests.post(url, auth=(sid, token), data={
                'From': from_num, 'To': f'+221{destinataire.lstrip("+221")}', 'Body': message
            }, timeout=10)
            return r.status_code in (200, 201), 'twilio'
        except Exception as e:
            print(f"[SMS-TWILIO] ❌ {e}")
            return False, 'twilio'

    return False, 'unknown'


# ═══════════════════════════════════════════════════════════════
# 📲 ENVOI SMS MANUEL
# ═══════════════════════════════════════════════════════════════

@sms_bp.route('/sms')
@login_required
def sms_index():
    db = _db()
    cur = db.cursor()
    _ensure_table()
    cur.execute("SELECT * FROM sms_log ORDER BY id DESC LIMIT 100")
    logs = _rows(cur)

    cur.execute("SELECT COUNT(*) AS n FROM sms_log")
    total = (_row(cur) or {}).get('n', 0)

    rows_html = ''
    for l in logs:
        statut_color = '#10b981' if l.get('statut') == 'envoye' else '#ef4444'
        rows_html += f"""
        <tr>
          <td>{l.get('destinataire')}</td>
          <td>{l.get('message', '')[:60]}{'...' if len(l.get('message', '')) > 60 else ''}</td>
          <td><span style="background:{statut_color};color:#fff;padding:3px 10px;border-radius:12px;font-size:11px">{l.get('statut')}</span></td>
          <td>{l.get('mode') or '—'}</td>
          <td>{l.get('date_envoi') or '—'}</td>
        </tr>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">📲 SMS & Notifications</h1>
      <div style="display:flex;gap:10px">
        <a href="/notifications" style="background:#8b5cf6;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">🔔 Notifications</a>
        <a href="/sms/envoyer" style="background:#10b981;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">+ Envoyer SMS</a>
      </div>
    </div>

    <div style="background:linear-gradient(135deg,#f59e0b,#b45309);color:#fff;padding:18px;border-radius:12px;margin-bottom:22px">
      <div style="font-size:13px;opacity:.9">📡 Mode SMS actif : <strong>{SMS_MODE}</strong></div>
      <div style="font-size:12px;opacity:.85;margin-top:6px">
        {'🧪 Mode simulation — aucun SMS réel envoyé (développement)' if SMS_MODE == 'simulation' else '🔴 Mode production — SMS réels envoyés'}
      </div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:22px">
      <div style="background:linear-gradient(135deg,#3b82f6,#1e40af);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Total SMS</div>
        <div style="font-size:26px;font-weight:700">{total}</div>
      </div>
      <div style="background:linear-gradient(135deg,#10b981,#047857);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Mode</div>
        <div style="font-size:20px;font-weight:700">{SMS_MODE}</div>
      </div>
      <div style="background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">API disponibles</div>
        <div style="font-size:14px;font-weight:600;margin-top:6px">Orange · Twilio · Simulation</div>
      </div>
    </div>

    <div style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <table style="width:100%;border-collapse:collapse">
        <thead style="background:#1f2937;color:#fff">
          <tr>
            <th style="padding:12px;text-align:left">Destinataire</th>
            <th style="padding:12px;text-align:left">Message</th>
            <th style="padding:12px;text-align:left">Statut</th>
            <th style="padding:12px;text-align:left">Mode</th>
            <th style="padding:12px;text-align:left">Date</th>
          </tr>
        </thead>
        <tbody>{rows_html or '<tr><td colspan="5" style="padding:40px;text-align:center;color:#9ca3af">Aucun SMS envoyé</td></tr>'}</tbody>
      </table>
    </div>
    """
    return _render(content, active='sms', title='SMS')


@sms_bp.route('/sms/envoyer', methods=['GET', 'POST'])
@login_required
def sms_envoyer():
    db = _db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            destinataire = (request.form.get('destinataire') or '').strip()
            message = (request.form.get('message') or '').strip()
            if not destinataire or not message:
                raise ValueError('Destinataire et message requis')

            ok, mode = _send_sms(destinataire, message)
            statut = 'envoye' if ok else 'echec'

            cur.execute("""
                INSERT INTO sms_log (destinataire, message, statut, mode, date_envoi, created_at)
                VALUES (?,?,?,?,?,?)
            """, (destinataire, message, statut, mode,
                  datetime.now().strftime('%Y-%m-%d %H:%M'),
                  datetime.now().isoformat()))
            db.commit()
            _log('SMS_SEND', f'→ {destinataire} : {message[:40]}', 'sms_log')
            flash(f'{"✅ SMS envoyé" if ok else "❌ Échec"} ({mode})', 'success' if ok else 'error')
            return redirect('/sms')
        except Exception as e:
            db.rollback()
            flash(f'❌ {e}', 'error')

    # Raccourcis producteurs
    cur.execute("SELECT id, nom, telephone, region FROM producteurs WHERE telephone IS NOT NULL LIMIT 20")
    producteurs = _rows(cur)
    opts_prod = ''.join(f'<option value="{p.get("telephone")}">{p.get("nom")} — {p.get("telephone")}</option>' for p in producteurs)

    content = f"""
    <h1 style="color:#1f2937">📲 Envoyer un SMS</h1>
    <form method="post" style="background:#fff;padding:28px;border-radius:12px;max-width:720px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <div style="margin-bottom:18px">
        <label style="font-weight:600">Raccourci producteur</label>
        <select onchange="document.querySelector('input[name=destinataire]').value=this.value" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
          <option value="">— Choisir un producteur —</option>{opts_prod}
        </select>
      </div>
      <div style="margin-bottom:18px">
        <label style="font-weight:600">Destinataire *</label>
        <input type="text" name="destinataire" required placeholder="+221771234567" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
      </div>
      <div style="margin-bottom:18px">
        <label style="font-weight:600">Message * (max 160 car.)</label>
        <textarea name="message" required maxlength="160" rows="4" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px" placeholder="Ex: OMEGA AGRO : Votre livraison de mangues est prévue demain 8h."></textarea>
      </div>
      <div style="background:#fef3c7;padding:12px;border-radius:8px;margin-bottom:18px;font-size:13px;color:#92400e">
        📡 Mode actuel : <strong>{SMS_MODE}</strong> — {'Aucun SMS réel envoyé' if SMS_MODE == 'simulation' else 'Envoi réel'}
      </div>
      <div>
        <button type="submit" style="background:#10b981;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-weight:600;cursor:pointer">📤 Envoyer</button>
        <a href="/sms" style="margin-left:12px;color:#6b7280">Annuler</a>
      </div>
    </form>
    """
    return _render(content, active='sms', title='Envoyer SMS')


@sms_bp.route('/api/sms/alerte-stock', methods=['POST', 'GET'])
@login_required
def api_sms_alerte_stock():
    """Envoie un SMS pour chaque stock en alerte (utilisable en cron)."""
    db = _db()
    cur = db.cursor()
    try:
        cur.execute("""
            SELECT s.id, s.quantite, s.seuil_alerte, pf.nom AS produit_nom
            FROM stocks_produits s
            LEFT JOIN produits_finis pf ON pf.id = s.produit_fini_id
            WHERE s.quantite <= s.seuil_alerte
        """)
        alertes = _rows(cur)
    except Exception:
        alertes = []

    # Récupérer le 1er admin
    cur.execute("SELECT telephone FROM users WHERE role='admin' AND telephone IS NOT NULL LIMIT 1")
    admin = _row(cur)
    destinataire = (admin or {}).get('telephone') or '+221000000000'

    resultats = []
    for a in alertes:
        msg = f"OMEGA AGRO ALERTE STOCK: {a.get('produit_nom')} qte={a.get('quantite')} <= seuil={a.get('seuil_alerte')}"
        ok, mode = _send_sms(destinataire, msg)
        cur.execute("""
            INSERT INTO sms_log (destinataire, message, statut, mode, date_envoi, created_at)
            VALUES (?,?,?,?,?,?)
        """, (destinataire, msg, 'envoye' if ok else 'echec', mode,
              datetime.now().strftime('%Y-%m-%d %H:%M'), datetime.now().isoformat()))
        resultats.append({'produit': a.get('produit_nom'), 'ok': ok})

    db.commit()
    return jsonify({'alertes': len(alertes), 'destinataire': destinataire, 'resultats': resultats})


# ═══════════════════════════════════════════════════════════════
# 🔔 NOTIFICATIONS INTERNES
# ═══════════════════════════════════════════════════════════════

@sms_bp.route('/notifications')
@login_required
def notifications_liste():
    db = _db()
    cur = db.cursor()
    _ensure_table()

    # Auto-générer les notifications d'alerte si table vide
    cur.execute("SELECT COUNT(*) FROM notifications")
    n = (cur.fetchone() or [0])[0]
    if n == 0:
        _auto_generate_notifications(db)

    cur.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT 100")
    notifs = _rows(cur)

    cur.execute("SELECT COUNT(*) FROM notifications WHERE lu=0")
    non_lues = (cur.fetchone() or [0])[0]

    rows_html = ''
    for n in notifs:
        type_color = {'info': '#3b82f6', 'warning': '#f59e0b',
                      'success': '#10b981', 'danger': '#ef4444'}.get(n.get('type'), '#6b7280')
        bg = '#fff' if n.get('lu') else '#f0f9ff'
        rows_html += f"""
        <tr style="background:{bg}">
          <td><span style="background:{type_color};color:#fff;padding:3px 10px;border-radius:12px;font-size:11px">{n.get('type')}</span></td>
          <td><strong>{n.get('titre')}</strong></td>
          <td>{n.get('message') or '—'}</td>
          <td>{'✅ Lu' if n.get('lu') else '🔵 Non lu'}</td>
          <td>{n.get('created_at', '')[:16]}</td>
        </tr>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">🔔 Notifications <span style="background:#ef4444;color:#fff;padding:3px 12px;border-radius:12px;font-size:14px;margin-left:10px">{non_lues}</span></h1>
      <a href="/sms" style="background:#e5e7eb;color:#374151;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">← SMS</a>
    </div>

    <div style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <table style="width:100%;border-collapse:collapse">
        <thead style="background:#1f2937;color:#fff">
          <tr>
            <th style="padding:12px;text-align:left">Type</th>
            <th style="padding:12px;text-align:left">Titre</th>
            <th style="padding:12px;text-align:left">Message</th>
            <th style="padding:12px;text-align:left">Statut</th>
            <th style="padding:12px;text-align:left">Date</th>
          </tr>
        </thead>
        <tbody>{rows_html or '<tr><td colspan="5" style="padding:40px;text-align:center;color:#9ca3af">Aucune notification</td></tr>'}</tbody>
      </table>
    </div>
    """
    return _render(content, active='sms', title='Notifications')


def _auto_generate_notifications(db):
    cur = db.cursor()
    notifs = []

    # Alertes stock
    try:
        cur.execute("""
            SELECT pf.nom, s.quantite, s.seuil_alerte
            FROM stocks_produits s LEFT JOIN produits_finis pf ON pf.id=s.produit_fini_id
            WHERE s.quantite <= s.seuil_alerte LIMIT 10
        """)
        for r in cur.fetchall():
            notifs.append(('warning', f'⚠ Stock bas : {r[0]}',
                           f'Quantité {r[1]} ≤ seuil {r[2]}', 'stocks_produits'))
    except Exception:
        pass

    # Non-conformités
    try:
        cur.execute("SELECT COUNT(*) FROM non_conformites WHERE statut='ouverte'")
        n = (cur.fetchone() or [0])[0]
        if n:
            notifs.append(('danger', f'{n} non-conformité(s) ouverte(s)',
                           'Consulter le registre NC', 'non_conformites'))
    except Exception:
        pass

    # Exports UE en attente certification
    try:
        cur.execute("SELECT COUNT(*) FROM exports WHERE certification_ue=0")
        n = (cur.fetchone() or [0])[0]
        if n:
            notifs.append(('info', f'{n} export(s) sans certification UE',
                           'À certifier avant expédition', 'exports'))
    except Exception:
        pass

    # Contrats en attente
    try:
        cur.execute("SELECT COUNT(*) FROM contrats_achat WHERE statut='en_attente'")
        n = (cur.fetchone() or [0])[0]
        if n:
            notifs.append(('warning', f'{n} contrat(s) en attente de signature',
                           'À signer rapidement', 'contrats_achat'))
    except Exception:
        pass

    # Formations planifiées
    try:
        cur.execute("SELECT COUNT(*) FROM sessions_formation WHERE statut='planifiee'")
        n = (cur.fetchone() or [0])[0]
        if n:
            notifs.append(('success', f'{n} session(s) de formation planifiée(s)',
                           'Centre de formation OMEGA AGRO', 'sessions_formation'))
    except Exception:
        pass

    for type_, titre, msg, entity in notifs:
        cur.execute("""
            INSERT INTO notifications (titre, message, type, entity, lu, created_at)
            VALUES (?,?,?,?,0,?)
        """, (titre, msg, type_, entity, datetime.now().isoformat()))
    db.commit()


@sms_bp.route('/api/notifications/count')
@login_required
def api_notifications_count():
    db = _db()
    cur = db.cursor()
    _ensure_table()
    cur.execute("SELECT COUNT(*) FROM notifications WHERE lu=0")
    n = (cur.fetchone() or [0])[0]
    return jsonify({'non_lues': n})


@sms_bp.route('/api/notifications/lire-tout', methods=['POST'])
@login_required
def api_notifications_lire_tout():
    db = _db()
    cur = db.cursor()
    _ensure_table()
    cur.execute("UPDATE notifications SET lu=1")
    db.commit()
    return jsonify({'ok': True})


@sms_bp.route('/api/sms/stats')
@login_required
def api_sms_stats():
    db = _db()
    cur = db.cursor()
    _ensure_table()
    cur.execute("""
        SELECT statut, COUNT(*) AS n FROM sms_log GROUP BY statut
    """)
    return jsonify({'mode': SMS_MODE, 'stats': _rows(cur)})
