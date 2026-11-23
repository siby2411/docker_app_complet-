"""
🌡️ Omega Agro-Industrie — IoT Capteurs
Chaîne du froid · HACCP · Alertes SMS · Rapport conformité UE
"""
from flask import Blueprint, request, redirect, flash, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import io
import json
import math
import random

iot_bp = Blueprint('iot_sensors', __name__)
_deps = {}


def init_iot(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(iot_bp)
    _ensure_tables()
    print("[IOT] ✅ Module IoT capteurs enregistré")


# Alias compatibilité
def init_agro_iot(app, **kwargs):
    return init_iot(app, **kwargs)


def _db():
    return _deps['get_db']()


def _render(content, active='iot', title='IoT'):
    return _deps['render_page'](content, active=active, page_title=title)


def _log(action, details='', entity=None, entity_id=None):
    try:
        uid = current_user.id if (current_user and current_user.is_authenticated) else None
        _deps['log_action'](uid, action, details, entity=entity, entity_id=entity_id)
    except Exception:
        pass


def _rows(cur):
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _row(cur):
    cols = [c[0] for c in cur.description]
    r = cur.fetchone()
    return dict(zip(cols, r)) if r else None


def _ensure_tables():
    """Crée les tables IoT si absentes."""
    try:
        db = _db()
        cur = db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS iot_capteurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                nom TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'temperature',
                site TEXT,
                emplacement TEXT,
                seuil_min REAL DEFAULT 10,
                seuil_max REAL DEFAULT 14,
                unite TEXT DEFAULT '°C',
                actif INTEGER DEFAULT 1,
                produit_lie TEXT,
                created_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS iot_mesures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capteur_id INTEGER NOT NULL,
                valeur REAL NOT NULL,
                hors_seuil INTEGER DEFAULT 0,
                date_mesure TEXT,
                created_at TEXT,
                FOREIGN KEY(capteur_id) REFERENCES iot_capteurs(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS iot_alertes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capteur_id INTEGER NOT NULL,
                mesure_id INTEGER,
                valeur REAL,
                seuil_depasse TEXT,
                message TEXT,
                traitee INTEGER DEFAULT 0,
                date_alerte TEXT,
                created_at TEXT,
                FOREIGN KEY(capteur_id) REFERENCES iot_capteurs(id)
            )
        """)
        db.commit()

        # Seed capteurs si vide
        cur.execute("SELECT COUNT(*) FROM iot_capteurs")
        if (cur.fetchone() or [0])[0] == 0:
            _seed_capteurs(cur)
            db.commit()
            print("[IOT] ✅ Capteurs démo créés")
    except Exception as e:
        print(f"[IOT] ⚠️ {e}")


def _seed_capteurs(cur):
    """Crée des capteurs démo réalistes pour le Sénégal."""
    capteurs = [
        # (code, nom, type, site, emplacement, min, max, unite, produit)
        ('TEMP-DKR-01', 'Entrepôt frigorifique Dakar Nord', 'temperature', 'Dakar', 'Zone A — mangues', 10.0, 13.5, '°C', 'Mangue'),
        ('TEMP-DKR-02', 'Entrepôt frigorifique Dakar Sud', 'temperature', 'Dakar', 'Zone B — cajou', 15.0, 20.0, '°C', 'Noix de cajou'),
        ('HUM-DKR-01', 'Contrôle humidité Dakar', 'humidite', 'Dakar', 'Zone A — mangues', 60.0, 75.0, '%', 'Mangue'),
        ('TEMP-THS-01', 'Chambre froide Thiès', 'temperature', 'Thiès', 'Ligne transformation', 11.0, 13.0, '°C', 'Mangue'),
        ('TEMP-THS-02', 'Séchoir solaire Thiès', 'temperature', 'Thiès', 'Séchage mangue', 45.0, 65.0, '°C', 'Mangue séchée'),
        ('HUM-THS-01', 'Humidité séchoir Thiès', 'humidite', 'Thiès', 'Séchage', 5.0, 10.0, '%', 'Mangue séchée'),
        ('TEMP-ZIG-01', 'Entrepôt Ziguinchor', 'temperature', 'Ziguinchor', 'Cajou brut', 18.0, 25.0, '°C', 'Noix de cajou'),
        ('HUM-ZIG-01', 'Humidité Ziguinchor', 'humidite', 'Ziguinchor', 'Cajou — anti-aflatoxine', 5.0, 8.0, '%', 'Noix de cajou'),
        ('CO2-DKR-01', 'Qualité air Dakar', 'co2', 'Dakar', 'Chambre mangues', 300.0, 800.0, 'ppm', 'Mangue'),
        ('TEMP-STL-01', 'Entrepôt Saint-Louis', 'temperature', 'Saint-Louis', 'Légumes', 4.0, 8.0, '°C', 'Légumes'),
    ]
    for code, nom, typ, site, empl, smin, smax, unite, prod in capteurs:
        cur.execute("""
            INSERT INTO iot_capteurs
            (code, nom, type, site, emplacement, seuil_min, seuil_max, unite, actif, produit_lie, created_at)
            VALUES (?,?,?,?,?,?,?,?,1,?,?)
        """, (code, nom, typ, site, empl, smin, smax, unite, prod, datetime.now().isoformat()))


def _simuler_valeur(capteur):
    """Simule une mesure réaliste selon le type et les seuils."""
    typ = capteur.get('type', 'temperature')
    smin = capteur.get('seuil_min') or 0
    smax = capteur.get('seuil_max') or 100
    mid = (smin + smax) / 2
    amp = (smax - smin) / 2

    # Variation sinusoïdale + bruit
    t = datetime.now().timestamp() / 3600  # heures
    base = mid + math.sin(t) * amp * 0.6
    bruit = random.uniform(-amp * 0.3, amp * 0.3)
    valeur = base + bruit

    # Occasionnellement hors seuil (5% du temps)
    if random.random() < 0.05:
        if random.random() < 0.5:
            valeur = smin - random.uniform(0.5, 2)
        else:
            valeur = smax + random.uniform(0.5, 2)

    return round(valeur, 2)


# ═══════════════════════════════════════════════════════════════
# 🌡️ DASHBOARD IOT LIVE
# ═══════════════════════════════════════════════════════════════

@iot_bp.route('/iot/dashboard')
@login_required
def iot_dashboard():
    db = _db()
    cur = db.cursor()
    cur.execute("SELECT * FROM iot_capteurs WHERE actif=1 ORDER BY site, code")
    capteurs = _rows(cur)

    # Dernière mesure par capteur
    cartes_html = ''
    total_alertes = 0
    for c in capteurs:
        cur.execute("""
            SELECT valeur, hors_seuil, date_mesure FROM iot_mesures
            WHERE capteur_id=? ORDER BY id DESC LIMIT 1
        """, (c['id'],))
        last = _row(cur)

        # Stats 24h
        cur.execute("""
            SELECT COUNT(*) AS n, AVG(valeur) AS moy, MIN(valeur) AS mn, MAX(valeur) AS mx,
                   SUM(hors_seuil) AS nb_hs
            FROM iot_mesures WHERE capteur_id=?
            AND date_mesure >= ?
        """, (c['id'], (datetime.now() - timedelta(hours=24)).isoformat()))
        stats = _row(cur) or {}

        val = last.get('valeur') if last else None
        hs = last.get('hors_seuil', 0) if last else 0
        if hs:
            total_alertes += 1

        color = '#ef4444' if hs else '#10b981'
        bg_grad = f"linear-gradient(135deg,{'#ef4444,#b91c1c' if hs else '#10b981,#047857'})"
        val_str = f"{val:.1f} {c.get('unite')}" if val is not None else '—'

        cartes_html += f"""
        <a href="/iot/capteurs/{c['id']}" style="text-decoration:none;color:inherit">
          <div style="background:{bg_grad};color:#fff;padding:18px;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,.1);cursor:pointer">
            <div style="font-size:12px;opacity:.9">{c.get('site') or '—'} · {c.get('code')}</div>
            <div style="font-size:14px;font-weight:600;margin:4px 0 10px">{c.get('nom')}</div>
            <div style="font-size:36px;font-weight:700">{val_str}</div>
            <div style="font-size:12px;opacity:.85;margin-top:8px">
              📊 24h : {stats.get('nb_hs') or 0} hors seuil / {stats.get('n') or 0} mesures
            </div>
            <div style="font-size:11px;opacity:.75;margin-top:4px">
              Seuils : {c.get('seuil_min')} – {c.get('seuil_max')} {c.get('unite')}
            </div>
          </div>
        </a>"""

    # Stats globales
    cur.execute("SELECT COUNT(*) AS n FROM iot_capteurs WHERE actif=1")
    nb_capteurs = (_row(cur) or {}).get('n', 0)

    cur.execute("""
        SELECT COUNT(*) AS n FROM iot_mesures
        WHERE date_mesure >= ?
    """, ((datetime.now() - timedelta(hours=24)).isoformat(),))
    nb_mesures_24h = (_row(cur) or {}).get('n', 0)

    cur.execute("SELECT COUNT(*) AS n FROM iot_alertes WHERE traitee=0")
    nb_alertes_ouvertes = (_row(cur) or {}).get('n', 0)

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">🌡️ IoT — Chaîne du froid & HACCP</h1>
      <div style="display:flex;gap:10px">
        <a href="/iot/capteurs/nouveau" style="background:#10b981;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">+ Capteur</a>
        <a href="/iot/alertes" style="background:#ef4444;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">🚨 Alertes ({nb_alertes_ouvertes})</a>
        <a href="/iot/rapport-haccp.pdf" style="background:#1e40af;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">📄 Rapport HACCP</a>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:22px">
      <div style="background:linear-gradient(135deg,#3b82f6,#1e40af);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Capteurs actifs</div>
        <div style="font-size:28px;font-weight:700">{nb_capteurs}</div>
      </div>
      <div style="background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Mesures 24h</div>
        <div style="font-size:28px;font-weight:700">{nb_mesures_24h}</div>
      </div>
      <div style="background:linear-gradient(135deg,#ef4444,#b91c1c);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Alertes ouvertes</div>
        <div style="font-size:28px;font-weight:700">{nb_alertes_ouvertes}</div>
      </div>
      <div style="background:linear-gradient(135deg,#10b981,#047857);color:#fff;padding:16px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Conformité HACCP</div>
        <div style="font-size:28px;font-weight:700">{'✅' if total_alertes == 0 else f'{nb_capteurs - total_alertes}/{nb_capteurs}'}</div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px">
      {cartes_html or '<p style="color:#9ca3af">Aucun capteur actif</p>'}
    </div>

    <div style="margin-top:22px;padding:14px;background:#f0f9ff;border-left:4px solid #3b82f6;border-radius:8px;font-size:13px;color:#1e40af">
      ⏱ <strong>Polling automatique</strong> : la page se rafraîchit toutes les 30s.
      <a href="/api/iot/live" style="color:#1e40af;text-decoration:underline">API live JSON</a> ·
      <a href="/iot/simuler" style="color:#1e40af;text-decoration:underline">🎲 Simuler mesures</a>
    </div>

    <script>
      setTimeout(() => location.reload(), 30000);
    </script>
    """
    return _render(content, active='iot', title='IoT Dashboard')


@iot_bp.route('/iot/capteurs')
@login_required
def iot_capteurs_liste():
    db = _db()
    cur = db.cursor()
    cur.execute("SELECT * FROM iot_capteurs ORDER BY site, code")
    capteurs = _rows(cur)

    rows_html = ''
    for c in capteurs:
        cur.execute("""
            SELECT valeur, hors_seuil FROM iot_mesures
            WHERE capteur_id=? ORDER BY id DESC LIMIT 1
        """, (c['id'],))
        last = _row(cur) or {}
        val = last.get('valeur')
        hs = last.get('hors_seuil', 0)
        badge = '<span style="background:#ef4444;color:#fff;padding:3px 10px;border-radius:12px;font-size:11px">⚠ ALERTE</span>' if hs else '<span style="background:#10b981;color:#fff;padding:3px 10px;border-radius:12px;font-size:11px">OK</span>'
        rows_html += f"""
        <tr>
          <td><strong>{c.get('code')}</strong></td>
          <td>{c.get('nom')}</td>
          <td>{c.get('type')}</td>
          <td>{c.get('site') or '—'}</td>
          <td>{c.get('emplacement') or '—'}</td>
          <td style="text-align:right">{f"{val:.1f}" if val is not None else '—'} {c.get('unite')}</td>
          <td style="text-align:center">{c.get('seuil_min')} – {c.get('seuil_max')}</td>
          <td>{badge}</td>
          <td>
            <a href="/iot/capteurs/{c['id']}" style="color:#3b82f6;text-decoration:none;font-weight:600">👁 Détail</a>
          </td>
        </tr>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">🌡️ Capteurs IoT — {len(capteurs)}</h1>
      <a href="/iot/capteurs/nouveau" style="background:#10b981;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">+ Nouveau capteur</a>
    </div>

    <div style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <table style="width:100%;border-collapse:collapse">
        <thead style="background:#1f2937;color:#fff">
          <tr>
            <th style="padding:12px;text-align:left">Code</th>
            <th style="padding:12px;text-align:left">Nom</th>
            <th style="padding:12px;text-align:left">Type</th>
            <th style="padding:12px;text-align:left">Site</th>
            <th style="padding:12px;text-align:left">Emplacement</th>
            <th style="padding:12px;text-align:right">Dernière mesure</th>
            <th style="padding:12px;text-align:center">Seuils</th>
            <th style="padding:12px;text-align:left">État</th>
            <th style="padding:12px;text-align:left">Action</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    """
    return _render(content, active='iot', title='Capteurs IoT')


@iot_bp.route('/iot/capteurs/nouveau', methods=['GET', 'POST'])
@login_required
def iot_capteur_nouveau():
    db = _db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            code = request.form.get('code', '').strip().upper()
            nom = request.form.get('nom', '').strip()
            typ = request.form.get('type') or 'temperature'
            site = request.form.get('site') or ''
            empl = request.form.get('emplacement') or ''
            smin = float(request.form.get('seuil_min') or 0)
            smax = float(request.form.get('seuil_max') or 100)
            unite = request.form.get('unite') or '°C'
            produit = request.form.get('produit_lie') or ''

            cur.execute("""
                INSERT INTO iot_capteurs
                (code, nom, type, site, emplacement, seuil_min, seuil_max, unite, actif, produit_lie, created_at)
                VALUES (?,?,?,?,?,?,?,?,1,?,?)
            """, (code, nom, typ, site, empl, smin, smax, unite, produit,
                  datetime.now().isoformat()))
            db.commit()
            _log('IOT_CAPTEUR_CREATE', f'{code} — {nom}', 'iot_capteurs')
            flash(f'✅ Capteur {code} créé', 'success')
            return redirect('/iot/capteurs')
        except Exception as e:
            db.rollback()
            flash(f'❌ {e}', 'error')

    content = """
    <h1 style="color:#1f2937">🌡️ Nouveau capteur IoT</h1>
    <form method="post" style="background:#fff;padding:28px;border-radius:12px;max-width:720px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
        <div>
          <label style="font-weight:600">Code *</label>
          <input type="text" name="code" required placeholder="TEMP-DKR-03" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Type *</label>
          <select name="type" required style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
            <option value="temperature">🌡️ Température</option>
            <option value="humidite">💧 Humidité</option>
            <option value="co2">💨 CO2</option>
            <option value="ph">🧪 pH</option>
          </select>
        </div>
        <div style="grid-column:1/-1">
          <label style="font-weight:600">Nom *</label>
          <input type="text" name="nom" required placeholder="Entrepôt frigorifique Dakar" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Site</label>
          <input type="text" name="site" placeholder="Dakar / Thiès / Ziguinchor" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Emplacement</label>
          <input type="text" name="emplacement" placeholder="Zone A — mangues" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Seuil minimum *</label>
          <input type="number" step="0.1" name="seuil_min" required value="10" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Seuil maximum *</label>
          <input type="number" step="0.1" name="seuil_max" required value="14" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
        </div>
        <div>
          <label style="font-weight:600">Unité</label>
          <select name="unite" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
            <option value="°C">°C</option>
            <option value="%">%</option>
            <option value="ppm">ppm</option>
            <option value="pH">pH</option>
          </select>
        </div>
        <div>
          <label style="font-weight:600">Produit lié</label>
          <select name="produit_lie" style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;margin-top:6px">
            <option value="">— Aucun —</option>
            <option value="Mangue">🥭 Mangue</option>
            <option value="Noix de cajou">🥜 Noix de cajou</option>
            <option value="Légumes">🥬 Légumes</option>
            <option value="Mangue séchée">🥭 Mangue séchée</option>
          </select>
        </div>
      </div>
      <div style="margin-top:24px">
        <button type="submit" style="background:#10b981;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-weight:600;cursor:pointer">💾 Créer</button>
        <a href="/iot/capteurs" style="margin-left:12px;color:#6b7280">Annuler</a>
      </div>
    </form>
    """
    return _render(content, active='iot', title='Nouveau capteur')


@iot_bp.route('/iot/capteurs/<int:cid>')
@login_required
def iot_capteur_detail(cid):
    db = _db()
    cur = db.cursor()
    cur.execute("SELECT * FROM iot_capteurs WHERE id=?", (cid,))
    c = _row(cur)
    if not c:
        flash('❌ Capteur introuvable', 'error')
        return redirect('/iot/capteurs')

    # Mesures 7 derniers jours
    cur.execute("""
        SELECT valeur, hors_seuil, date_mesure
        FROM iot_mesures WHERE capteur_id=?
        AND date_mesure >= ?
        ORDER BY date_mesure DESC LIMIT 200
    """, (cid, (datetime.now() - timedelta(days=7)).isoformat()))
    mesures = _rows(cur)

    # Alertes
    cur.execute("""
        SELECT * FROM iot_alertes WHERE capteur_id=?
        ORDER BY id DESC LIMIT 30
    """, (cid,))
    alertes = _rows(cur)

    # Sparkline simple (SVG)
    vals = [m.get('valeur') for m in mesures[:50]]
    sparkline = ''
    if vals:
        mn, mx = min(vals), max(vals)
        rng = mx - mn or 1
        W, H = 600, 120
        pts = []
        for i, v in enumerate(vals):
            x = (i / max(1, len(vals)-1)) * W
            y = H - ((v - mn) / rng) * H
            pts.append(f"{x:.1f},{y:.1f}")
        polyline = " ".join(pts)
        sparkline = f"""
        <svg viewBox="0 0 {W} {H}" style="width:100%;height:120px;background:#f9fafb;border-radius:8px">
          <polyline fill="none" stroke="#3b82f6" stroke-width="2" points="{polyline}" />
        </svg>
        <div style="display:flex;justify-content:space-between;font-size:11px;color:#6b7280;margin-top:4px">
          <span>min: {mn:.1f} {c.get('unite')}</span>
          <span>{len(vals)} mesures</span>
          <span>max: {mx:.1f} {c.get('unite')}</span>
        </div>
        """

    alertes_html = ''
    for a in alertes:
        alertes_html += f"""
        <tr>
          <td>{a.get('date_alerte')}</td>
          <td style="text-align:right">{a.get('valeur'):.1f} {c.get('unite')}</td>
          <td>{a.get('seuil_depasse')}</td>
          <td>{a.get('message')}</td>
          <td>{'✅' if a.get('traitee') else '🔴 Ouverte'}</td>
        </tr>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">🌡️ {c.get('nom')}</h1>
      <div style="display:flex;gap:10px">
        <a href="/iot/capteurs" style="background:#e5e7eb;color:#374151;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">← Capteurs</a>
        <a href="/api/iot/capteurs/{cid}/hist" style="background:#8b5cf6;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">📊 JSON</a>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:22px">
      <div style="background:linear-gradient(135deg,#3b82f6,#1e40af);color:#fff;padding:18px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Code</div>
        <div style="font-size:18px;font-weight:700">{c.get('code')}</div>
      </div>
      <div style="background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:#fff;padding:18px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Site</div>
        <div style="font-size:18px;font-weight:700">{c.get('site') or '—'}</div>
      </div>
      <div style="background:linear-gradient(135deg,#10b981,#047857);color:#fff;padding:18px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Seuils</div>
        <div style="font-size:18px;font-weight:700">{c.get('seuil_min')} – {c.get('seuil_max')} {c.get('unite')}</div>
      </div>
      <div style="background:linear-gradient(135deg,#f59e0b,#b45309);color:#fff;padding:18px;border-radius:10px">
        <div style="font-size:12px;opacity:.9">Produit lié</div>
        <div style="font-size:18px;font-weight:700">{c.get('produit_lie') or '—'}</div>
      </div>
    </div>

    <div style="background:#fff;padding:22px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.1);margin-bottom:20px">
      <h3 style="margin-top:0;color:#1f2937">📈 Historique 7 jours</h3>
      {sparkline or '<p style="color:#9ca3af">Aucune mesure</p>'}
    </div>

    <div style="background:#fff;padding:22px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <h3 style="margin-top:0;color:#1f2937">🚨 Alertes récentes</h3>
      <table style="width:100%;border-collapse:collapse">
        <thead>
          <tr style="background:#f9fafb">
            <th style="padding:10px;text-align:left">Date</th>
            <th style="padding:10px;text-align:right">Valeur</th>
            <th style="padding:10px;text-align:left">Seuil dépassé</th>
            <th style="padding:10px;text-align:left">Message</th>
            <th style="padding:10px;text-align:left">État</th>
          </tr>
        </thead>
        <tbody>{alertes_html or '<tr><td colspan="5" style="padding:30px;text-align:center;color:#9ca3af">Aucune alerte</td></tr>'}</tbody>
      </table>
    </div>
    """
    return _render(content, active='iot', title=c.get('nom', 'Capteur'))


@iot_bp.route('/iot/alertes')
@login_required
def iot_alertes():
    db = _db()
    cur = db.cursor()
    cur.execute("""
        SELECT a.*, c.code AS capteur_code, c.nom AS capteur_nom, c.unite
        FROM iot_alertes a
        LEFT JOIN iot_capteurs c ON c.id = a.capteur_id
        ORDER BY a.id DESC LIMIT 200
    """)
    alertes = _rows(cur)

    rows_html = ''
    for a in alertes:
        color = '#10b981' if a.get('traitee') else '#ef4444'
        rows_html += f"""
        <tr>
          <td>{a.get('date_alerte', '')[:16]}</td>
          <td><strong>{a.get('capteur_code')}</strong><br><small style="color:#9ca3af">{a.get('capteur_nom')}</small></td>
          <td style="text-align:right">{a.get('valeur'):.1f} {a.get('unite') or ''}</td>
          <td>{a.get('seuil_depasse')}</td>
          <td>{a.get('message')}</td>
          <td><span style="background:{color};color:#fff;padding:3px 10px;border-radius:12px;font-size:11px">{'✅ Traitée' if a.get('traitee') else '🔴 Ouverte'}</span></td>
        </tr>"""

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h1 style="margin:0;color:#1f2937">🚨 Alertes IoT — {len(alertes)}</h1>
      <a href="/iot/dashboard" style="background:#e5e7eb;color:#374151;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">← Dashboard</a>
    </div>

    <div style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <table style="width:100%;border-collapse:collapse">
        <thead style="background:#1f2937;color:#fff">
          <tr>
            <th style="padding:12px;text-align:left">Date</th>
            <th style="padding:12px;text-align:left">Capteur</th>
            <th style="padding:12px;text-align:right">Valeur</th>
            <th style="padding:12px;text-align:left">Seuil</th>
            <th style="padding:12px;text-align:left">Message</th>
            <th style="padding:12px;text-align:left">État</th>
          </tr>
        </thead>
        <tbody>{rows_html or '<tr><td colspan="6" style="padding:40px;text-align:center;color:#9ca3af">Aucune alerte</td></tr>'}</tbody>
      </table>
    </div>
    """
    return _render(content, active='iot', title='Alertes IoT')


# ═══════════════════════════════════════════════════════════════
# 🎲 SIMULATION MESURES
# ═══════════════════════════════════════════════════════════════

@iot_bp.route('/iot/simuler')
@login_required
def iot_simuler():
    """Génère des mesures pour tous les capteurs actifs."""
    db = _db()
    cur = db.cursor()
    cur.execute("SELECT * FROM iot_capteurs WHERE actif=1")
    capteurs = _rows(cur)

    n_mesures = 0
    n_alertes = 0

    for c in capteurs:
        valeur = _simuler_valeur(c)
        smin = c.get('seuil_min') or 0
        smax = c.get('seuil_max') or 100
        hs = 1 if (valeur < smin or valeur > smax) else 0

        cur.execute("""
            INSERT INTO iot_mesures
            (capteur_id, valeur, hors_seuil, date_mesure, created_at)
            VALUES (?,?,?,?,?)
        """, (c['id'], valeur, hs, datetime.now().isoformat(), datetime.now().isoformat()))
        mesure_id = cur.lastrowid
        n_mesures += 1

        if hs:
            seuil_depasse = f"min ({smin})" if valeur < smin else f"max ({smax})"
            msg = f"{c.get('nom')} : {valeur:.1f}{c.get('unite')} hors seuil {seuil_depasse}"
            cur.execute("""
                INSERT INTO iot_alertes
                (capteur_id, mesure_id, valeur, seuil_depasse, message, traitee, date_alerte, created_at)
                VALUES (?,?,?,?,?,0,?,?)
            """, (c['id'], mesure_id, valeur, seuil_depasse, msg,
                  datetime.now().isoformat(), datetime.now().isoformat()))
            n_alertes += 1

            # Notification interne
            try:
                cur.execute("""
                    INSERT INTO notifications (titre, message, type, entity, lu, created_at)
                    VALUES (?,?,?,?,0,?)
                """, (f"⚠ IoT alerte : {c.get('nom')}", msg, 'warning', 'iot_capteurs',
                      datetime.now().isoformat()))
            except Exception:
                pass

    db.commit()
    _log('IOT_SIMULATE', f'{n_mesures} mesures, {n_alertes} alertes', 'iot_mesures')
    flash(f'🎲 {n_mesures} mesures générées — {n_alertes} alertes', 'success')
    return redirect('/iot/dashboard')


# ═══════════════════════════════════════════════════════════════
# 📄 RAPPORT HACCP PDF
# ═══════════════════════════════════════════════════════════════

@iot_bp.route('/iot/rapport-haccp.pdf')
@login_required
def iot_rapport_haccp():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors

    db = _db()
    cur = db.cursor()

    # Récupérer tous les capteurs + stats 30j
    cur.execute("SELECT * FROM iot_capteurs WHERE actif=1 ORDER BY site, code")
    capteurs = _rows(cur)

    stats_30j = []
    for c in capteurs:
        cur.execute("""
            SELECT COUNT(*) AS n, AVG(valeur) AS moy, MIN(valeur) AS mn, MAX(valeur) AS mx,
                   SUM(hors_seuil) AS nb_hs
            FROM iot_mesures WHERE capteur_id=?
            AND date_mesure >= ?
        """, (c['id'], (datetime.now() - timedelta(days=30)).isoformat()))
        s = _row(cur) or {}
        stats_30j.append({
            'capteur': c,
            'n': s.get('n') or 0,
            'moy': s.get('moy') or 0,
            'mn': s.get('mn') or 0,
            'mx': s.get('mx') or 0,
            'nb_hs': s.get('nb_hs') or 0,
        })

    # Alertes 30j
    cur.execute("""
        SELECT COUNT(*) AS n FROM iot_alertes WHERE date_alerte >= ?
    """, ((datetime.now() - timedelta(days=30)).isoformat(),))
    nb_alertes_30j = (_row(cur) or {}).get('n', 0)

    # PDF
    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=A4)
    w, h = A4

    # Header
    c.setFillColor(colors.HexColor('#1e40af'))
    c.rect(0, h - 32*mm, w, 32*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 18)
    c.drawString(15*mm, h - 15*mm, "OMEGA AGRO-INDUSTRIE")
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, h - 21*mm, "Rapport conformité HACCP — Chaîne du froid")
    c.setFont('Helvetica-Bold', 12)
    c.drawRightString(w - 15*mm, h - 15*mm, "RAPPORT HACCP")
    c.setFont('Helvetica', 9)
    c.drawRightString(w - 15*mm, h - 21*mm, datetime.now().strftime('%d/%m/%Y'))
    c.setFont('Helvetica', 9)
    c.drawString(15*mm, h - 27*mm, "Période : 30 derniers jours · Normes UE 852/2004 · ISO 22000")

    # Synthèse
    y = h - 45*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(15*mm, y, "📊 SYNTHÈSE")
    y -= 8*mm
    c.setFont('Helvetica', 10)
    c.drawString(15*mm, y, f"Capteurs actifs : {len(capteurs)}")
    c.drawString(80*mm, y, f"Alertes 30j : {nb_alertes_30j}")
    y -= 6*mm
    total_mesures = sum(s['n'] for s in stats_30j)
    c.drawString(15*mm, y, f"Mesures totales : {total_mesures}")
    taux_conformite = 100 - (sum(s['nb_hs'] for s in stats_30j) / total_mesures * 100) if total_mesures else 100
    c.drawString(80*mm, y, f"Conformité : {taux_conformite:.1f}%")

    # Tableau capteurs
    y -= 15*mm
    c.setFillColor(colors.HexColor('#1f2937'))
    c.rect(15*mm, y - 7*mm, w - 30*mm, 7*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(17*mm, y - 4.5*mm, "Code")
    c.drawString(45*mm, y - 4.5*mm, "Site")
    c.drawString(85*mm, y - 4.5*mm, "Seuils")
    c.drawString(115*mm, y - 4.5*mm, "Moy")
    c.drawString(135*mm, y - 4.5*mm, "Min/Max")
    c.drawString(165*mm, y - 4.5*mm, "HS")

    y -= 12*mm
    c.setFillColor(colors.black)
    c.setFont('Helvetica', 8)
    for s in stats_30j:
        cap = s['capteur']
        c.drawString(17*mm, y, cap.get('code', '')[:12])
        c.drawString(45*mm, y, (cap.get('site') or '')[:15])
        c.drawString(85*mm, y, f"{cap.get('seuil_min')}-{cap.get('seuil_max')}{cap.get('unite','')}"[:18])
        c.drawString(115*mm, y, f"{s['moy']:.1f}")
        c.drawString(135*mm, y, f"{s['mn']:.1f}/{s['mx']:.1f}")
        hs_color = colors.HexColor('#ef4444') if s['nb_hs'] > 0 else colors.HexColor('#10b981')
        c.setFillColor(hs_color)
        c.drawString(165*mm, y, str(s['nb_hs']))
        c.setFillColor(colors.black)
        y -= 5*mm
        if y < 40*mm:
            c.showPage()
            y = h - 20*mm

    # Conclusion
    y -= 10*mm
    if y < 50*mm:
        c.showPage()
        y = h - 30*mm
    c.setFillColor(colors.HexColor('#f0fdf4'))
    c.rect(15*mm, y - 25*mm, w - 30*mm, 25*mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#047857'))
    c.setFont('Helvetica-Bold', 11)
    c.drawString(18*mm, y - 6*mm, "✅ CONCLUSION CONFORMITÉ")
    c.setFont('Helvetica', 9)
    c.setFillColor(colors.black)
    if taux_conformite >= 98:
        verdict = f"Conformité excellente ({taux_conformite:.1f}%). Chaîne du froid conforme UE 852/2004."
    elif taux_conformite >= 95:
        verdict = f"Conformité satisfaisante ({taux_conformite:.1f}%). Surveiller les écarts."
    else:
        verdict = f"⚠ Conformité à améliorer ({taux_conformite:.1f}%). Actions correctives requises."
    c.drawString(18*mm, y - 12*mm, verdict)
    c.drawString(18*mm, y - 18*mm, "Normes : HACCP · ISO 22000 · UE 852/2004 · GlobalG.A.P.")

    # Footer
    c.setFillColor(colors.grey)
    c.setFont('Helvetica', 7)
    c.drawString(15*mm, 10*mm, "OMEGA AGRO-INDUSTRIE — Prolongement SM10 AGRO (Sadio Mané) 🇸🇳")
    c.drawRightString(w - 15*mm, 10*mm, f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    c.showPage()
    c.save()
    pdf_buf.seek(0)

    _log('IOT_RAPPORT_HACCP', f'Rapport 30j — {len(capteurs)} capteurs', 'iot_capteurs')
    return send_file(pdf_buf, mimetype='application/pdf',
                     download_name=f'rapport_haccp_{datetime.now().strftime("%Y%m%d")}.pdf')


# ═══════════════════════════════════════════════════════════════
# 📊 API JSON
# ═══════════════════════════════════════════════════════════════

@iot_bp.route('/api/iot/live')
@login_required
def api_iot_live():
    db = _db()
    cur = db.cursor()
    cur.execute("SELECT * FROM iot_capteurs WHERE actif=1 ORDER BY site, code")
    capteurs = _rows(cur)
    result = []
    for c in capteurs:
        cur.execute("""
            SELECT valeur, hors_seuil, date_mesure FROM iot_mesures
            WHERE capteur_id=? ORDER BY id DESC LIMIT 1
        """, (c['id'],))
        last = _row(cur) or {}
        result.append({
            'code': c.get('code'),
            'nom': c.get('nom'),
            'site': c.get('site'),
            'type': c.get('type'),
            'unite': c.get('unite'),
            'seuil_min': c.get('seuil_min'),
            'seuil_max': c.get('seuil_max'),
            'valeur': last.get('valeur'),
            'hors_seuil': last.get('hors_seuil', 0),
            'date_mesure': last.get('date_mesure'),
        })
    return jsonify({'capteurs': result, 'count': len(result),
                    'timestamp': datetime.now().isoformat()})


@iot_bp.route('/api/iot/capteurs/<int:cid>/hist')
@login_required
def api_iot_hist(cid):
    db = _db()
    cur = db.cursor()
    days = int(request.args.get('days') or 7)
    cur.execute("""
        SELECT valeur, hors_seuil, date_mesure FROM iot_mesures
        WHERE capteur_id=? AND date_mesure >= ?
        ORDER BY date_mesure ASC LIMIT 500
    """, (cid, (datetime.now() - timedelta(days=days)).isoformat()))
    return jsonify(_rows(cur))


@iot_bp.route('/api/iot/stats')
@login_required
def api_iot_stats():
    db = _db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM iot_capteurs WHERE actif=1")
    n_cap = (_row(cur) or {}).get('n', 0)
    cur.execute("""
        SELECT COUNT(*) AS n FROM iot_mesures WHERE date_mesure >= ?
    """, ((datetime.now() - timedelta(hours=24)).isoformat(),))
    n_mes = (_row(cur) or {}).get('n', 0)
    cur.execute("SELECT COUNT(*) AS n FROM iot_alertes WHERE traitee=0")
    n_alertes = (_row(cur) or {}).get('n', 0)
    return jsonify({
        'capteurs_actifs': n_cap,
        'mesures_24h': n_mes,
        'alertes_ouvertes': n_alertes,
    })


@iot_bp.route('/api/iot/simuler-batch', methods=['POST'])
@login_required
def api_simuler_batch():
    """Endpoint cron-friendly : simule N mesures."""
    n = int(request.args.get('n') or 1)
    for _ in range(min(n, 100)):
        db = _db()
        cur = db.cursor()
        cur.execute("SELECT * FROM iot_capteurs WHERE actif=1")
        for c in _rows(cur):
            v = _simuler_valeur(c)
            smin = c.get('seuil_min') or 0
            smax = c.get('seuil_max') or 100
            hs = 1 if (v < smin or v > smax) else 0
            cur.execute("""
                INSERT INTO iot_mesures (capteur_id, valeur, hors_seuil, date_mesure, created_at)
                VALUES (?,?,?,?,?)
            """, (c['id'], v, hs, datetime.now().isoformat(), datetime.now().isoformat()))
        db.commit()
    return jsonify({'ok': True, 'mesures_generees': n})
