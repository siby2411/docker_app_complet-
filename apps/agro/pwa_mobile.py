"""
📱 Omega Agro-Industrie — PWA Mobile Offline-First
Saisie récolte terrain · Scan QR · Sync auto · Mode déconnecté
"""
from flask import Blueprint, request, redirect, flash, jsonify, send_file, render_template_string
from flask_login import login_required, current_user
from datetime import datetime
import io
import json
import os

pwa_bp = Blueprint('pwa_mobile', __name__)
_deps = {}

# Chemin des fichiers statiques PWA
PWA_STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static_pwa')


def init_pwa(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(pwa_bp)
    _ensure_tables()
    print("[PWA] ✅ Module PWA Mobile enregistré")


# Alias compatibilité
def init_agro_pwa(app, **kwargs):
    return init_pwa(app, **kwargs)


def _db():
    return _deps['get_db']()


def _render(content, active='mobile', title='Mobile'):
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
    """Crée les tables PWA si absentes."""
    try:
        db = _db()
        cur = db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pwa_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE NOT NULL,
                user_id INTEGER,
                user_agent TEXT,
                last_sync TEXT,
                created_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pwa_sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                user_id INTEGER,
                action TEXT NOT NULL,
                payload TEXT NOT NULL,
                statut TEXT DEFAULT 'pending',
                erreur TEXT,
                created_at TEXT,
                synced_at TEXT
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_pwa_sync_statut
            ON pwa_sync_queue(statut, device_id)
        """)
        db.commit()
        print("[PWA] ✅ Tables PWA prêtes")
    except Exception as e:
        print(f"[PWA] ⚠️ {e}")


# ═══════════════════════════════════════════════════════════════
# 📱 HUB MOBILE
# ═══════════════════════════════════════════════════════════════

@pwa_bp.route('/mobile')
@login_required
def mobile_hub():
    content = """
    <link rel="manifest" href="/static_pwa/manifest.json">
    <meta name="theme-color" content="#10b981">

    <div style="max-width:600px;margin:0 auto">
      <div style="background:linear-gradient(135deg,#10b981,#047857);color:#fff;padding:24px;border-radius:16px;margin-bottom:20px;text-align:center">
        <div style="font-size:44px">📱</div>
        <h1 style="margin:8px 0 4px;font-size:22px">OMEGA AGRO Mobile</h1>
        <p style="margin:0;opacity:.9;font-size:13px">Saisie terrain · Hors-ligne · Sync auto</p>
        <div id="pwa-status" style="margin-top:12px;font-size:12px;opacity:.9">⏳ Vérification...</div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px">
        <a href="/mobile/recolte" style="text-decoration:none">
          <div style="background:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.08)">
            <div style="font-size:32px">🌾</div>
            <div style="font-weight:700;color:#1f2937;margin-top:8px">Nouvelle récolte</div>
            <div style="font-size:12px;color:#6b7280;margin-top:4px">Saisie offline</div>
          </div>
        </a>
        <a href="/mobile/livraison" style="text-decoration:none">
          <div style="background:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.08)">
            <div style="font-size:32px">📦</div>
            <div style="font-weight:700;color:#1f2937;margin-top:8px">Livraison</div>
            <div style="font-size:12px;color:#6b7280;margin-top:4px">Vers transformateur</div>
          </div>
        </a>
        <a href="/mobile/scan" style="text-decoration:none">
          <div style="background:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.08)">
            <div style="font-size:32px">📷</div>
            <div style="font-weight:700;color:#1f2937;margin-top:8px">Scanner QR</div>
            <div style="font-size:12px;color:#6b7280;margin-top:4px">Vérifier un lot</div>
          </div>
        </a>
        <a href="/mobile/sync" style="text-decoration:none">
          <div style="background:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.08)">
            <div style="font-size:32px">🔄</div>
            <div style="font-weight:700;color:#1f2937;margin-top:8px">Synchroniser</div>
            <div style="font-size:12px;color:#6b7280;margin-top:4px"><span id="pending-count">0</span> en attente</div>
          </div>
        </a>
      </div>

      <div style="background:#fff;padding:18px;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,.08);margin-bottom:20px">
        <h3 style="margin:0 0 12px;color:#1f2937;font-size:15px">📊 Ma journée</h3>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
          <div>
            <div style="font-size:11px;color:#6b7280">Récoltes</div>
            <div style="font-size:22px;font-weight:700;color:#10b981" id="stat-recoltes">—</div>
          </div>
          <div>
            <div style="font-size:11px;color:#6b7280">Livraisons</div>
            <div style="font-size:22px;font-weight:700;color:#3b82f6" id="stat-livraisons">—</div>
          </div>
        </div>
      </div>

      <button id="btn-install" style="display:none;width:100%;background:#1f2937;color:#fff;padding:16px;border:none;border-radius:12px;font-weight:700;font-size:15px;cursor:pointer">
        ⬇ Installer l'app sur mon téléphone
      </button>

      <div style="text-align:center;margin-top:16px;font-size:11px;color:#9ca3af">
        OMEGA AGRO-INDUSTRIE v3.2 · Prolongement SM10 AGRO 🇸🇳
      </div>
    </div>

    <script src="/static_pwa/pwa.js"></script>
    <script>
      PWA.init();
      PWA.updateStatus('pwa-status');
      PWA.updatePendingCount('pending-count');
    </script>
    """
    return _render(content, active='mobile', title='Mobile')


# ═══════════════════════════════════════════════════════════════
# 📝 FORMULAIRE RÉCOLTE
# ═══════════════════════════════════════════════════════════════

@pwa_bp.route('/mobile/recolte')
@login_required
def mobile_recolte():
    db = _db()
    cur = db.cursor()
    cur.execute("SELECT id, nom, region FROM producteurs ORDER BY nom LIMIT 500")
    producteurs = _rows(cur)
    opts = ''.join(f'<option value="{p["id"]}">{p["nom"]} — {p.get("region") or ""}</option>' for p in producteurs)

    content = f"""
    <link rel="manifest" href="/static_pwa/manifest.json">
    <div style="max-width:600px;margin:0 auto">
      <div style="background:#10b981;color:#fff;padding:16px;border-radius:12px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center">
        <a href="/mobile" style="color:#fff;text-decoration:none;font-size:20px">←</a>
        <div style="font-weight:700">🌾 Nouvelle récolte</div>
        <div style="font-size:12px" id="online-status">●</div>
      </div>

      <form id="recolte-form" style="background:#fff;padding:20px;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,.08)">
        <div style="margin-bottom:16px">
          <label style="font-weight:600;font-size:13px;color:#374151">Producteur *</label>
          <select name="producteur_id" required style="width:100%;padding:14px;border:2px solid #e5e7eb;border-radius:10px;margin-top:6px;font-size:15px">
            <option value="">— Sélectionner —</option>{opts}
          </select>
        </div>

        <div style="margin-bottom:16px">
          <label style="font-weight:600;font-size:13px;color:#374151">Produit *</label>
          <select name="produit" required style="width:100%;padding:14px;border:2px solid #e5e7eb;border-radius:10px;margin-top:6px;font-size:15px">
            <option value="">— Sélectionner —</option>
            <option value="Mangue">🥭 Mangue</option>
            <option value="Noix de cajou">🥜 Noix de cajou</option>
            <option value="Légumes">🥬 Légumes</option>
            <option value="Tomate">🍅 Tomate</option>
            <option value="Oignon">🧅 Oignon</option>
          </select>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
          <div>
            <label style="font-weight:600;font-size:13px;color:#374151">Quantité (kg) *</label>
            <input type="number" step="0.1" name="quantite" required placeholder="0" style="width:100%;padding:14px;border:2px solid #e5e7eb;border-radius:10px;margin-top:6px;font-size:15px">
          </div>
          <div>
            <label style="font-weight:600;font-size:13px;color:#374151">Prix/kg (FCFA)</label>
            <input type="number" step="1" name="prix_unitaire" placeholder="0" style="width:100%;padding:14px;border:2px solid #e5e7eb;border-radius:10px;margin-top:6px;font-size:15px">
          </div>
        </div>

        <div style="margin-bottom:16px">
          <label style="font-weight:600;font-size:13px;color:#374151">Date récolte</label>
          <input type="date" name="date_recolte" value="{datetime.now().strftime('%Y-%m-%d')}" style="width:100%;padding:14px;border:2px solid #e5e7eb;border-radius:10px;margin-top:6px;font-size:15px">
        </div>

        <div style="margin-bottom:16px">
          <label style="font-weight:600;font-size:13px;color:#374151">Notes (optionnel)</label>
          <textarea name="notes" rows="3" placeholder="Qualité, météo, observations..." style="width:100%;padding:14px;border:2px solid #e5e7eb;border-radius:10px;margin-top:6px;font-size:15px"></textarea>
        </div>

        <div id="form-msg" style="display:none;padding:12px;border-radius:10px;margin-bottom:16px;font-size:13px"></div>

        <button type="submit" style="width:100%;background:#10b981;color:#fff;padding:16px;border:none;border-radius:12px;font-weight:700;font-size:16px;cursor:pointer">
          💾 Enregistrer la récolte
        </button>
      </form>

      <div style="text-align:center;margin-top:16px;font-size:11px;color:#9ca3af">
        💡 Fonctionne hors-ligne — sync auto quand reconnecté
      </div>
    </div>

    <script src="/static_pwa/pwa.js"></script>
    <script>
      PWA.init();
      PWA.updateStatus('online-status');

      document.getElementById('recolte-form').addEventListener('submit', async (e) => {{
        e.preventDefault();
        const form = e.target;
        const data = {{
          producteur_id: parseInt(form.producteur_id.value),
          produit: form.produit.value,
          quantite: parseFloat(form.quantite.value),
          prix_unitaire: parseFloat(form.prix_unitaire.value || 0),
          date_recolte: form.date_recolte.value,
          notes: form.notes.value
        }};

        const result = await PWA.submitOrQueue('recolte', data);
        const msg = document.getElementById('form-msg');
        msg.style.display = 'block';

        if (result.queued) {{
          msg.style.background = '#fef3c7';
          msg.style.color = '#92400e';
          msg.innerHTML = '📴 Hors-ligne : récolte mise en file d\\'attente. Sync auto quand reconnecté.';
        }} else if (result.ok) {{
          msg.style.background = '#d1fae5';
          msg.style.color = '#065f46';
          msg.innerHTML = '✅ Récolte enregistrée !';
          form.reset();
        }} else {{
          msg.style.background = '#fee2e2';
          msg.style.color = '#991b1b';
          msg.innerHTML = '❌ Erreur : ' + (result.error || 'inconnue');
        }}

        PWA.updatePendingCount('pending-count');
        window.scrollTo({{top: 0, behavior: 'smooth'}});
      }});
    </script>
    """
    return _render(content, active='mobile', title='Nouvelle récolte')


# ═══════════════════════════════════════════════════════════════
# 📦 FORMULAIRE LIVRAISON
# ═══════════════════════════════════════════════════════════════

@pwa_bp.route('/mobile/livraison')
@login_required
def mobile_livraison():
    db = _db()
    cur = db.cursor()
    cur.execute("SELECT id, nom, region FROM producteurs ORDER BY nom LIMIT 500")
    producteurs = _rows(cur)
    opts = ''.join(f'<option value="{p["id"]}">{p["nom"]} — {p.get("region") or ""}</option>' for p in producteurs)

    content = f"""
    <link rel="manifest" href="/static_pwa/manifest.json">
    <div style="max-width:600px;margin:0 auto">
      <div style="background:#3b82f6;color:#fff;padding:16px;border-radius:12px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center">
        <a href="/mobile" style="color:#fff;text-decoration:none;font-size:20px">←</a>
        <div style="font-weight:700">📦 Livraison</div>
        <div style="font-size:12px" id="online-status">●</div>
      </div>

      <form id="livraison-form" style="background:#fff;padding:20px;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,.08)">
        <div style="margin-bottom:16px">
          <label style="font-weight:600;font-size:13px;color:#374151">Producteur *</label>
          <select name="producteur_id" required style="width:100%;padding:14px;border:2px solid #e5e7eb;border-radius:10px;margin-top:6px;font-size:15px">
            <option value="">— Sélectionner —</option>{opts}
          </select>
        </div>

        <div style="margin-bottom:16px">
          <label style="font-weight:600;font-size:13px;color:#374151">Type livraison *</label>
          <select name="type" required style="width:100%;padding:14px;border:2px solid #e5e7eb;border-radius:10px;margin-top:6px;font-size:15px">
            <option value="usine">🏭 Vers usine transformation</option>
            <option value="marche">🛒 Vers marché</option>
            <option value="export">✈️ Vers port export</option>
          </select>
        </div>

        <div style="margin-bottom:16px">
          <label style="font-weight:600;font-size:13px;color:#374151">N° lot (optionnel)</label>
          <input type="text" name="numero_lot" placeholder="LOT-2026-XXXX" style="width:100%;padding:14px;border:2px solid #e5e7eb;border-radius:10px;margin-top:6px;font-size:15px">
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
          <div>
            <label style="font-weight:600;font-size:13px;color:#374151">Quantité (kg) *</label>
            <input type="number" step="0.1" name="quantite" required placeholder="0" style="width:100%;padding:14px;border:2px solid #e5e7eb;border-radius:10px;margin-top:6px;font-size:15px">
          </div>
          <div>
            <label style="font-weight:600;font-size:13px;color:#374151">Destination</label>
            <input type="text" name="destination" placeholder="Ex: Dakar" style="width:100%;padding:14px;border:2px solid #e5e7eb;border-radius:10px;margin-top:6px;font-size:15px">
          </div>
        </div>

        <div id="form-msg" style="display:none;padding:12px;border-radius:10px;margin-bottom:16px;font-size:13px"></div>

        <button type="submit" style="width:100%;background:#3b82f6;color:#fff;padding:16px;border:none;border-radius:12px;font-weight:700;font-size:16px;cursor:pointer">
          📤 Enregistrer la livraison
        </button>
      </form>
    </div>

    <script src="/static_pwa/pwa.js"></script>
    <script>
      PWA.init();
      PWA.updateStatus('online-status');

      document.getElementById('livraison-form').addEventListener('submit', async (e) => {{
        e.preventDefault();
        const form = e.target;
        const data = {{
          producteur_id: parseInt(form.producteur_id.value),
          type: form.type.value,
          numero_lot: form.numero_lot.value,
          quantite: parseFloat(form.quantite.value),
          destination: form.destination.value
        }};

        const result = await PWA.submitOrQueue('livraison', data);
        const msg = document.getElementById('form-msg');
        msg.style.display = 'block';

        if (result.queued) {{
          msg.style.background = '#fef3c7'; msg.style.color = '#92400e';
          msg.innerHTML = '📴 Mise en file d\\'attente — sync auto.';
        }} else if (result.ok) {{
          msg.style.background = '#dbeafe'; msg.style.color = '#1e40af';
          msg.innerHTML = '✅ Livraison enregistrée !';
          form.reset();
        }} else {{
          msg.style.background = '#fee2e2'; msg.style.color = '#991b1b';
          msg.innerHTML = '❌ Erreur : ' + (result.error || 'inconnue');
        }}
        PWA.updatePendingCount('pending-count');
      }});
    </script>
    """
    return _render(content, active='mobile', title='Livraison')


# ═══════════════════════════════════════════════════════════════
# 📷 SCANNER QR
# ═══════════════════════════════════════════════════════════════

@pwa_bp.route('/mobile/scan')
@login_required
def mobile_scan():
    content = """
    <link rel="manifest" href="/static_pwa/manifest.json">
    <div style="max-width:600px;margin:0 auto">
      <div style="background:#8b5cf6;color:#fff;padding:16px;border-radius:12px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center">
        <a href="/mobile" style="color:#fff;text-decoration:none;font-size:20px">←</a>
        <div style="font-weight:700">📷 Scanner QR</div>
        <div></div>
      </div>

      <div style="background:#fff;padding:20px;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,.08)">
        <div id="scanner-container" style="position:relative;background:#000;border-radius:12px;overflow:hidden;aspect-ratio:1;max-width:400px;margin:0 auto">
          <video id="qr-video" style="width:100%;height:100%;object-fit:cover"></video>
          <div style="position:absolute;inset:20%;border:3px solid #10b981;border-radius:12px;pointer-events:none"></div>
        </div>

        <div id="scan-result" style="margin-top:16px;padding:16px;background:#f9fafb;border-radius:10px;text-align:center;color:#6b7280;font-size:14px">
          En attente d'un QR code...
        </div>

        <div style="margin-top:16px">
          <label style="font-weight:600;font-size:13px;color:#374151">Ou saisir manuellement un N° de lot</label>
          <div style="display:flex;gap:8px;margin-top:6px">
            <input type="text" id="manual-lot" placeholder="LOT-2026-XXXX" style="flex:1;padding:14px;border:2px solid #e5e7eb;border-radius:10px;font-size:15px">
            <button onclick="lookupLot()" style="background:#8b5cf6;color:#fff;padding:14px 20px;border:none;border-radius:10px;font-weight:600;cursor:pointer">🔍</button>
          </div>
        </div>
      </div>
    </div>

    <script src="/static_pwa/pwa.js"></script>
    <script>
      PWA.init();
      PWA.startQrScanner('qr-video', (result) => {
        const div = document.getElementById('scan-result');
        div.style.background = '#d1fae5';
        div.style.color = '#065f46';
        div.innerHTML = '✅ QR détecté : <strong>' + result + '</strong><br><a href="/exports/tracabilite/' + result + '" style="color:#047857">Voir la fiche lot →</a>';
      });

      async function lookupLot() {
        const lot = document.getElementById('manual-lot').value.trim();
        if (!lot) return;
        const div = document.getElementById('scan-result');
        try {
          const r = await fetch('/api/tracabilite/qr/' + lot, { credentials: 'same-origin' });
          const data = await r.json();
          if (data.error) {
            div.style.background = '#fee2e2'; div.style.color = '#991b1b';
            div.innerHTML = '❌ ' + data.error;
          } else {
            div.style.background = '#d1fae5'; div.style.color = '#065f46';
            div.innerHTML = '✅ Lot trouvé : <a href="/exports/tracabilite/' + lot + '" style="color:#047857">Voir la fiche →</a>';
          }
        } catch (e) {
          div.innerHTML = '❌ Erreur réseau';
        }
      }
    </script>
    """
    return _render(content, active='mobile', title='Scanner QR')


# ═══════════════════════════════════════════════════════════════
# 🔄 PAGE SYNC
# ═══════════════════════════════════════════════════════════════

@pwa_bp.route('/mobile/sync')
@login_required
def mobile_sync():
    content = """
    <link rel="manifest" href="/static_pwa/manifest.json">
    <div style="max-width:600px;margin:0 auto">
      <div style="background:#f59e0b;color:#fff;padding:16px;border-radius:12px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center">
        <a href="/mobile" style="color:#fff;text-decoration:none;font-size:20px">←</a>
        <div style="font-weight:700">🔄 Synchronisation</div>
        <div></div>
      </div>

      <div style="background:#fff;padding:20px;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,.08);margin-bottom:16px">
        <div style="text-align:center;margin-bottom:20px">
          <div style="font-size:48px" id="sync-icon">📴</div>
          <h3 style="margin:8px 0 4px;color:#1f2937">File d'attente locale</h3>
          <div style="font-size:36px;font-weight:700;color:#f59e0b" id="queue-count">0</div>
          <div style="font-size:12px;color:#6b7280">élément(s) en attente</div>
        </div>

        <button id="btn-sync" onclick="doSync()" style="width:100%;background:#f59e0b;color:#fff;padding:16px;border:none;border-radius:12px;font-weight:700;font-size:16px;cursor:pointer">
          🔄 Synchroniser maintenant
        </button>

        <div id="sync-msg" style="margin-top:16px;font-size:13px;text-align:center;color:#6b7280"></div>
      </div>

      <div style="background:#fff;padding:20px;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,.08)">
        <h3 style="margin:0 0 12px;color:#1f2937;font-size:15px">📋 Éléments en attente</h3>
        <div id="queue-list" style="font-size:13px;color:#6b7280">Chargement...</div>
      </div>
    </div>

    <script src="/static_pwa/pwa.js"></script>
    <script>
      PWA.init();
      loadQueue();

      async function loadQueue() {
        const q = await PWA.getQueue();
        document.getElementById('queue-count').textContent = q.length;
        const list = document.getElementById('queue-list');
        if (q.length === 0) {
          list.innerHTML = '<p style="text-align:center;color:#10b981">✅ Aucun élément en attente</p>';
          document.getElementById('sync-icon').textContent = '✅';
          return;
        }
        document.getElementById('sync-icon').textContent = '📴';
        list.innerHTML = q.map(item =>
          '<div style="padding:10px;background:#f9fafb;border-radius:8px;margin-bottom:8px">' +
          '<strong>' + (item.action === 'recolte' ? '🌾 Récolte' : '📦 Livraison') + '</strong> — ' +
          new Date(item.created_at).toLocaleString('fr-FR') +
          '</div>'
        ).join('');
      }

      async function doSync() {
        const btn = document.getElementById('btn-sync');
        const msg = document.getElementById('sync-msg');
        btn.disabled = true; btn.textContent = '⏳ Synchronisation...';
        msg.textContent = '';

        const result = await PWA.syncQueue();
        msg.innerHTML = '✅ ' + result.synced + ' synchronisé(s), ' + result.failed + ' échec(s)';
        btn.disabled = false; btn.textContent = '🔄 Synchroniser maintenant';
        loadQueue();
      }
    </script>
    """
    return _render(content, active='mobile', title='Synchronisation')


# ═══════════════════════════════════════════════════════════════
# 📡 API SYNC
# ═══════════════════════════════════════════════════════════════

@pwa_bp.route('/api/pwa/register', methods=['POST'])
@login_required
def api_pwa_register():
    """Enregistre un device PWA."""
    db = _db()
    cur = db.cursor()
    data = request.get_json() or {}
    device_id = data.get('device_id')
    if not device_id:
        return jsonify({'error': 'device_id requis'}), 400

    try:
        cur.execute("""
            INSERT INTO pwa_devices (device_id, user_id, user_agent, last_sync, created_at)
            VALUES (?,?,?,?,?)
            ON CONFLICT(device_id) DO UPDATE SET last_sync=excluded.last_sync
        """, (device_id, current_user.id, request.headers.get('User-Agent', ''),
              datetime.now().isoformat(), datetime.now().isoformat()))
        db.commit()
        return jsonify({'ok': True, 'device_id': device_id})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@pwa_bp.route('/api/pwa/sync', methods=['POST'])
@login_required
def api_pwa_sync():
    """
    Reçoit une batch de soumissions offline.
    Payload : { device_id, items: [{action, payload, created_at}] }
    """
    db = _db()
    cur = db.cursor()
    data = request.get_json() or {}
    device_id = data.get('device_id', 'unknown')
    items = data.get('items', [])

    if not items:
        return jsonify({'ok': True, 'synced': 0, 'failed': 0, 'details': []})

    synced = 0
    failed = 0
    details = []

    for item in items:
        action = item.get('action')
        payload = item.get('payload') or {}
        created = item.get('created_at') or datetime.now().isoformat()

        try:
            if action == 'recolte':
                _sync_recolte(cur, payload, created)
                synced += 1
                details.append({'action': action, 'status': 'ok'})
            elif action == 'livraison':
                _sync_livraison(cur, payload, created)
                synced += 1
                details.append({'action': action, 'status': 'ok'})
            else:
                failed += 1
                details.append({'action': action, 'status': 'error', 'error': 'action inconnue'})
        except Exception as e:
            failed += 1
            details.append({'action': action, 'status': 'error', 'error': str(e)})

    # Update device last_sync
    try:
        cur.execute("""
            UPDATE pwa_devices SET last_sync=?
            WHERE device_id=?
        """, (datetime.now().isoformat(), device_id))
    except Exception:
        pass

    db.commit()
    _log('PWA_SYNC', f'{synced} sync, {failed} failed', 'pwa_sync_queue')
    return jsonify({'ok': True, 'synced': synced, 'failed': failed, 'details': details})


def _sync_recolte(cur, payload, created_at):
    """Insère une récolte depuis le payload PWA."""
    producteur_id = int(payload.get('producteur_id') or 0)
    produit = payload.get('produit') or 'Inconnu'
    quantite = float(payload.get('quantite') or 0)
    prix_unit = float(payload.get('prix_unitaire') or 0)
    date_recolte = payload.get('date_recolte') or datetime.now().strftime('%Y-%m-%d')
    notes = payload.get('notes') or '[PWA mobile]'

    # Note : la table recoltes a une structure à adapter selon ton schéma réel
    # On tente une insertion minimale
    cur.execute("""
        INSERT INTO recoltes
        (producteur_id, produit, quantite, prix_unitaire, date_recolte, notes, created_at)
        VALUES (?,?,?,?,?,?,?)
    """, (producteur_id, produit, quantite, prix_unit, date_recolte, notes, created_at))


def _sync_livraison(cur, payload, created_at):
    """Insère une livraison depuis le payload PWA."""
    producteur_id = int(payload.get('producteur_id') or 0)
    typ = payload.get('type') or 'usine'
    numero_lot = payload.get('numero_lot') or f"PWA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    quantite = float(payload.get('quantite') or 0)
    destination = payload.get('destination') or '—'

    cur.execute("""
        INSERT INTO livraisons
        (producteur_id, type, numero_lot, quantite, destination, statut, created_at)
        VALUES (?,?,?,?,?,'recu',?)
    """, (producteur_id, typ, numero_lot, quantite, destination, created_at))


@pwa_bp.route('/api/pwa/queue', methods=['GET'])
@login_required
def api_pwa_queue():
    """Retourne la file d'attente serveur (utile debug)."""
    db = _db()
    cur = db.cursor()
    cur.execute("""
        SELECT * FROM pwa_sync_queue ORDER BY id DESC LIMIT 100
    """)
    return jsonify(_rows(cur))


@pwa_bp.route('/api/pwa/stats', methods=['GET'])
@login_required
def api_pwa_stats():
    db = _db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM pwa_devices")
    devices = (_row(cur) or {}).get('n', 0)
    cur.execute("SELECT COUNT(*) AS n FROM pwa_sync_queue WHERE statut='pending'")
    pending = (_row(cur) or {}).get('n', 0)
    cur.execute("SELECT COUNT(*) AS n FROM pwa_sync_queue WHERE statut='synced'")
    synced = (_row(cur) or {}).get('n', 0)
    return jsonify({
        'devices': devices,
        'pending': pending,
        'synced': synced,
    })


# ═══════════════════════════════════════════════════════════════
# 📁 FICHIERS STATIQUES PWA
# ═══════════════════════════════════════════════════════════════

@pwa_bp.route('/static_pwa/manifest.json')
def pwa_manifest():
    manifest = {
        "name": "OMEGA AGRO Mobile",
        "short_name": "OMEGA AGRO",
        "description": "Plateforme agro-industrielle Sénégal — Sadio Mané",
        "start_url": "/mobile",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#10b981",
        "theme_color": "#10b981",
        "lang": "fr",
        "icons": [
            {"src": "/static_pwa/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/static_pwa/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
        ],
        "shortcuts": [
            {"name": "Nouvelle récolte", "url": "/mobile/recolte", "icons": [{"src": "/static_pwa/icon-192.png", "sizes": "192x192"}]},
            {"name": "Scanner QR", "url": "/mobile/scan", "icons": [{"src": "/static_pwa/icon-192.png", "sizes": "192x192"}]}
        ]
    }
    return jsonify(manifest)


@pwa_bp.route('/static_pwa/sw.js')
def pwa_sw():
    """Service Worker — cache offline-first."""
    sw_code = """
// OMEGA AGRO PWA Service Worker v3.2
const CACHE_NAME = 'omega-agro-v3.2';
const OFFLINE_URLS = [
  '/mobile',
  '/mobile/recolte',
  '/mobile/livraison',
  '/mobile/scan',
  '/mobile/sync',
  '/static_pwa/pwa.js',
  '/static_pwa/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(OFFLINE_URLS).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  // Ne pas cacher les POST / API
  if (req.method !== 'GET' || req.url.includes('/api/')) {
    return;
  }
  event.respondWith(
    fetch(req).then((resp) => {
      const copy = resp.clone();
      caches.open(CACHE_NAME).then((cache) => cache.put(req, copy)).catch(() => {});
      return resp;
    }).catch(() => caches.match(req).then((r) => r || caches.match('/mobile')))
  );
});
"""
    return send_file(io.BytesIO(sw_code.encode()), mimetype='application/javascript')


@pwa_bp.route('/static_pwa/pwa.js')
def pwa_js():
    """Script PWA principal — IndexedDB + Sync + QR scanner."""
    js_code = r"""
// OMEGA AGRO PWA v3.2
const PWA = (() => {
  const DB_NAME = 'omega_agro_pwa';
  const DB_VERSION = 1;
  const STORE = 'sync_queue';
  let db = null;

  async function openDb() {
    if (db) return db;
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = (e) => {
        const d = e.target.result;
        if (!d.objectStoreNames.contains(STORE)) {
          d.createObjectStore(STORE, { keyPath: 'id', autoIncrement: true });
        }
      };
      req.onsuccess = () => { db = req.result; resolve(db); };
      req.onerror = () => reject(req.error);
    });
  }

  function getDeviceId() {
    let id = localStorage.getItem('omega_device_id');
    if (!id) {
      id = 'dev_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem('omega_device_id', id);
    }
    return id;
  }

  async function queueAdd(action, payload) {
    const d = await openDb();
    return new Promise((resolve, reject) => {
      const tx = d.transaction(STORE, 'readwrite');
      const req = tx.objectStore(STORE).add({
        action, payload,
        created_at: new Date().toISOString()
      });
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function queueGetAll() {
    const d = await openDb();
    return new Promise((resolve, reject) => {
      const tx = d.transaction(STORE, 'readonly');
      const req = tx.objectStore(STORE).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  }

  async function queueClear() {
    const d = await openDb();
    return new Promise((resolve, reject) => {
      const tx = d.transaction(STORE, 'readwrite');
      const req = tx.objectStore(STORE).clear();
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  }

  async function submitOrQueue(action, payload) {
    // Toujours tenter online d'abord
    if (navigator.onLine) {
      try {
        const r = await fetch('/api/pwa/sync', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            device_id: getDeviceId(),
            items: [{ action, payload, created_at: new Date().toISOString() }]
          })
        });
        const data = await r.json();
        if (r.ok && data.synced > 0) {
          return { ok: true, queued: false };
        }
        throw new Error(data.error || 'sync failed');
      } catch (e) {
        // Fallback → queue
        await queueAdd(action, payload);
        return { ok: false, queued: true };
      }
    }
    // Offline → queue
    await queueAdd(action, payload);
    return { ok: false, queued: true };
  }

  async function syncQueue() {
    const items = await queueGetAll();
    if (items.length === 0) return { synced: 0, failed: 0 };

    try {
      const r = await fetch('/api/pwa/sync', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: getDeviceId(),
          items: items.map(i => ({ action: i.action, payload: i.payload, created_at: i.created_at }))
        })
      });
      const data = await r.json();
      if (r.ok && data.failed === 0) {
        await queueClear();
      }
      return { synced: data.synced || 0, failed: data.failed || 0 };
    } catch (e) {
      return { synced: 0, failed: items.length, error: e.message };
    }
  }

  function updateStatus(elId) {
    const el = document.getElementById(elId);
    if (!el) return;
    const update = () => {
      el.innerHTML = navigator.onLine ? '🟢 En ligne' : '🔴 Hors-ligne';
    };
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    update();
  }

  async function updatePendingCount(elId) {
    const el = document.getElementById(elId);
    if (!el) return;
    const items = await queueGetAll();
    el.textContent = items.length;
    return items.length;
  }

  function startQrScanner(videoId, callback) {
    const video = document.getElementById(videoId);
    if (!video) return;

    // Charger jsQR depuis CDN (fallback)
    if (!window.jsQR) {
      const s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js';
      s.onload = () => initScanner();
      document.head.appendChild(s);
    } else {
      initScanner();
    }

    function initScanner() {
      navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        .then((stream) => {
          video.srcObject = stream;
          video.setAttribute('playsinline', true);
          video.play();
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          const scan = () => {
            if (video.readyState === video.HAVE_ENOUGH_DATA) {
              canvas.width = video.videoWidth;
              canvas.height = video.videoHeight;
              ctx.drawImage(video, 0, 0);
              const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
              if (window.jsQR) {
                const code = window.jsQR(img.data, img.width, img.height);
                if (code && code.data) {
                  if (callback) callback(code.data);
                  return;
                }
              }
            }
            requestAnimationFrame(scan);
          };
          scan();
        })
        .catch((err) => {
          const div = document.getElementById('scan-result');
          if (div) {
            div.style.background = '#fee2e2';
            div.style.color = '#991b1b';
            div.textContent = '❌ Caméra non accessible : ' + err.message;
          }
        });
    }
  }

  async function init() {
    // Enregistrer le device
    if (navigator.onLine) {
      try {
        await fetch('/api/pwa/register', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ device_id: getDeviceId() })
        });
      } catch (e) { /* ignore */ }
    }

    // Service Worker
    if ('serviceWorker' in navigator) {
      try {
        await navigator.serviceWorker.register('/static_pwa/sw.js');
      } catch (e) { /* ignore */ }
    }

    // PWA Install prompt
    let deferredPrompt;
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      const btn = document.getElementById('btn-install');
      if (btn) {
        btn.style.display = 'block';
        btn.onclick = async () => {
          deferredPrompt.prompt();
          const { outcome } = await deferredPrompt.userChoice;
          btn.style.display = 'none';
        };
      }
    });

    // Auto-sync à la reconnexion
    window.addEventListener('online', () => {
      syncQueue().then(() => {
        updatePendingCount('pending-count');
        if (document.getElementById('queue-count')) {
          loadQueue && loadQueue();
        }
      });
    });
  }

  return {
    init,
    submitOrQueue,
    syncQueue,
    getQueue: queueGetAll,
    updateStatus,
    updatePendingCount,
    startQrScanner,
    getDeviceId,
  };
})();
"""
    return send_file(io.BytesIO(js_code.encode()), mimetype='application/javascript')


@pwa_bp.route('/static_pwa/icon-192.png')
@pwa_bp.route('/static_pwa/icon-512.png')
def pwa_icon():
    """Icône PWA générée dynamiquement (carré vert avec 🌾)."""
    from PIL import Image, ImageDraw, ImageFont
    size = 512 if '512' in request.path else 192
    img = Image.new('RGB', (size, size), color=(16, 185, 129))
    draw = ImageDraw.Draw(img)

    # Cercle blanc
    margin = size // 8
    draw.ellipse([margin, margin, size - margin, size - margin], fill=(255, 255, 255))

    # Emoji / texte
    try:
        font_size = size // 2
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
    text = "OA"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, (size - th) / 2 - bbox[1]), text, fill=(16, 185, 129), font=font)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


# ═══════════════════════════════════════════════════════════════
# 📊 API STATS
# ═══════════════════════════════════════════════════════════════

@pwa_bp.route('/api/pwa/health')
def pwa_health():
    return jsonify({'status': 'ok', 'module': 'pwa_mobile', 'version': '3.2'})
