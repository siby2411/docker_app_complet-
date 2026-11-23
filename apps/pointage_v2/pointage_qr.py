"""
📱 Pointage V2 — Scanner QR mobile
Interface web + API de validation QR codes
"""
from flask import Blueprint, request, redirect, flash, jsonify, render_template_string, send_file, Response
from flask_login import current_user
import sqlite3
import hashlib
import io
import os
from datetime import datetime, timedelta

qr_bp = Blueprint('qr', __name__)
_deps = {}

QR_DIR = "/app/data/qrcodes"


def init_qr(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(qr_bp)
    print("[QR] ✅ Module QR scan enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='dashboard', title='Omega Pointage'):
    return _deps['render_page'](content, active=active, page_title=title)


def _log(action, details='', entity=None, entity_id=None):
    try:
        uid = None
        if current_user and current_user.is_authenticated:
            uid = current_user.id
        _deps['log_action'](uid, action, details, entity=entity, entity_id=entity_id)
    except Exception:
        pass


def _auth_required(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if not (current_user and current_user.is_authenticated):
            return redirect('/login')
        return f(*a, **k)
    return w


def _can_scan():
    return current_user and current_user.role in ('admin', 'rh', 'chef', 'pointage')


def _generate_qr_content(employe):
    """Génère le contenu QR unique pour un employé"""
    timestamp = datetime.now().isoformat()
    data = f"EMP|{employe['matricule']}|{timestamp}|{employe['nom']}|{employe['prenom']}"
    qr_hash = hashlib.sha256(data.encode()).hexdigest()[:32]
    return f"POINTAGE|{employe['matricule']}|{qr_hash}", timestamp


# ================================================================
# ==================== SCANNER MOBILE ====================
# ================================================================
@qr_bp.route('/pointage/scan')
def scan_mobile():
    """Page scan mobile — accessible aux utilisateurs connectés"""
    if not (current_user and current_user.is_authenticated):
        return redirect('/login')

    if not _can_scan():
        flash("Accès réservé au personnel de pointage", "danger")
        return redirect('/')

    content = """
    <div class="page-header">
      <div><h2><i class="fas fa-qrcode"></i> Scanner QR</h2>
        <div class="page-subtitle">Pointez avec votre smartphone</div></div>
      <a href="/" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>

    <div class="card" style="padding:0;overflow:hidden">
      <div id="reader" style="width:100%;min-height:400px;background:#0e7490"></div>

      <div style="padding:20px;text-align:center;background:#f0fdff">
        <div id="status" style="font-size:1.1rem;font-weight:700;color:#0e7490;margin-bottom:15px">
          📷 Caméra active...
        </div>
        <button onclick="switchCamera()" class="btn btn-info" style="margin-right:10px">
          <i class="fas fa-camera-rotate"></i> Changer caméra
        </button>
        <button onclick="stopScanner()" class="btn btn-danger">
          <i class="fas fa-stop"></i> Arrêter
        </button>
      </div>
    </div>

    <div class="card" id="result-card" style="display:none;border-left:5px solid #10b981">
      <div class="card-header">
        <h3><i class="fas fa-check-circle" style="color:#10b981"></i> Pointage enregistré</h3>
      </div>
      <div id="result-content" style="padding:15px"></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-list"></i> Scans récents</h3></div>
      <div id="recent-scans"></div>
    </div>

    <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <script>
    let html5QrCode = null;
    let currentCameraId = null;
    let cameraFacingMode = 'environment';

    async function initScanner() {
      html5QrCode = new Html5Qrcode("reader");

      const config = {
        fps: 10,
        qrbox: { width: 250, height: 250 },
        aspectRatio: 1.0,
        formatsToSupport: [ Html5QrcodeSupportedFormats.QR_CODE ]
      };

      try {
        const cameras = await Html5Qrcode.getCameras();
        if (cameras && cameras.length) {
          // Chercher caméra arrière
          const backCam = cameras.find(c =>
            c.label.toLowerCase().includes('back') ||
            c.label.toLowerCase().includes('rear') ||
            c.label.toLowerCase().includes('environnement')
          );
          currentCameraId = backCam ? backCam.id : cameras[0].id;
        }

        await html5QrCode.start(
          currentCameraId || { facingMode: cameraFacingMode },
          config,
          onScanSuccess,
          onScanError
        );

        document.getElementById('status').innerHTML = '✅ Caméra active · Scannez un QR code';
      } catch (err) {
        document.getElementById('status').innerHTML = '❌ Erreur caméra : ' + err;
        console.error(err);
      }
    }

    function onScanSuccess(decodedText, decodedResult) {
      // Vibrer si supporté
      if (navigator.vibrate) navigator.vibrate(200);

      // Arrêter le scan
      if (html5QrCode) {
        html5QrCode.pause(true);
      }

      document.getElementById('status').innerHTML = '⏳ Traitement...';

      // Envoyer au serveur
      fetch('/pointage/scan/validate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          qr_content: decodedText,
          timestamp: new Date().toISOString()
        })
      })
      .then(r => r.json())
      .then(data => {
        showResult(data);
        setTimeout(() => {
          if (html5QrCode) html5QrCode.resume();
          document.getElementById('status').innerHTML = '✅ Prêt pour le prochain scan';
        }, 3000);
      })
      .catch(err => {
        showResult({statut: 'erreur', message: 'Erreur réseau'});
      });
    }

    function onScanError(err) {
      // Ignorer les erreurs de scan (normal, pas de QR visible)
    }

    function showResult(data) {
      const card = document.getElementById('result-card');
      const content = document.getElementById('result-content');

      card.style.display = 'block';

      if (data.statut === 'succes') {
        card.style.borderLeftColor = '#10b981';
        card.querySelector('h3').innerHTML = '<i class="fas fa-check-circle" style="color:#10b981"></i> Pointage enregistré';

        content.innerHTML = `
          <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap">
            <div style="width:70px;height:70px;background:linear-gradient(135deg,#0e7490,#06b6d4);border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-size:1.8rem;font-weight:900">
              ${data.employe.prenom[0]}${data.employe.nom[0]}
            </div>
            <div style="flex:1">
              <div style="font-size:1.4rem;font-weight:900;color:#0e7490">
                ${data.employe.prenom} ${data.employe.nom}
              </div>
              <div style="font-size:0.9rem;color:#64748b">
                ${data.employe.matricule} · ${data.employe.poste || 'Employé'}
              </div>
              <div style="margin-top:10px">
                <span class="badge badge-success" style="font-size:0.9rem;padding:8px 14px">
                  <i class="fas fa-${data.type_scan === 'entree' ? 'right-to-bracket' : 'right-from-bracket'}"></i>
                  ${data.type_scan === 'entree' ? 'ENTRÉE' : 'SORTIE'} à ${data.heure}
                </span>
              </div>
            </div>
          </div>
          ${data.duree ? `<div style="margin-top:15px;padding:12px;background:#d1fae5;border-radius:10px;text-align:center;font-weight:800;color:#065f46">
            Durée de travail : ${data.duree}
          </div>` : ''}
        `;
      } else if (data.statut === 'warning') {
        card.style.borderLeftColor = '#f59e0b';
        card.querySelector('h3').innerHTML = '<i class="fas fa-exclamation-triangle" style="color:#f59e0b"></i> Attention';
        content.innerHTML = `<div style="font-size:1.1rem;color:#92400e">${data.message}</div>`;
      } else {
        card.style.borderLeftColor = '#dc2626';
        card.querySelector('h3').innerHTML = '<i class="fas fa-xmark-circle" style="color:#dc2626"></i> Erreur';
        content.innerHTML = `<div style="font-size:1.1rem;color:#991b1b">${data.message}</div>`;
      }

      // Scroll vers le résultat
      card.scrollIntoView({behavior: 'smooth'});

      // Rafraîchir les scans récents
      loadRecentScans();
    }

    async function switchCamera() {
      if (html5QrCode) {
        try {
          await html5QrCode.stop();
          cameraFacingMode = cameraFacingMode === 'environment' ? 'user' : 'environment';
          currentCameraId = null;
          await initScanner();
        } catch (err) {
          console.error(err);
        }
      }
    }

    function stopScanner() {
      if (html5QrCode) {
        html5QrCode.stop().then(() => {
          document.getElementById('status').innerHTML = '⏹️ Scanner arrêté';
        });
      }
    }

    function loadRecentScans() {
      fetch('/pointage/scan/recent')
        .then(r => r.json())
        .then(data => {
          const container = document.getElementById('recent-scans');
          if (!data.scans || data.scans.length === 0) {
            container.innerHTML = '<div class="empty" style="padding:20px">Aucun scan récent</div>';
            return;
          }
          let html = '<div style="display:flex;flex-direction:column;gap:10px">';
          data.scans.forEach(s => {
            const color = s.type_scan === 'entree' ? '#10b981' : '#f59e0b';
            html += `
              <div style="padding:10px;background:#f0fdff;border-radius:10px;border-left:4px solid ${color};display:flex;justify-content:space-between">
                <div>
                  <strong>${s.employe_nom || s.matricule}</strong>
                  <div style="font-size:0.75rem;color:#64748b">${s.type_scan === 'entree' ? '🟢 Entrée' : '🟠 Sortie'}</div>
                </div>
                <div style="text-align:right;font-size:0.8rem;color:#64748b">
                  ${s.date_scan.slice(11, 16)}
                </div>
              </div>
            `;
          });
          html += '</div>';
          container.innerHTML = html;
        });
    }

    // Init
    document.addEventListener('DOMContentLoaded', () => {
      initScanner();
      loadRecentScans();
      setInterval(loadRecentScans, 10000);
    });
    </script>
    """
    return _render(content, active='scan', title='Scanner QR')


# ================================================================
# ==================== API VALIDATION QR ====================
# ================================================================
@qr_bp.route('/pointage/scan/validate', methods=['POST'])
def scan_validate():
    """Valide un QR code scanné et enregistre le pointage"""
    if not (current_user and current_user.is_authenticated):
        return jsonify(statut='erreur', message='Non authentifié'), 401

    if not _can_scan():
        return jsonify(statut='erreur', message='Accès refusé'), 403

    try:
        data = request.get_json() or {}
        qr_content = data.get('qr_content', '').strip()

        if not qr_content:
            return jsonify(statut='erreur', message='QR code vide')

        # Format attendu : POINTAGE|MATRICULE|HASH
        parts = qr_content.split('|')
        if len(parts) != 3 or parts[0] != 'POINTAGE':
            return jsonify(statut='erreur', message='QR code invalide')

        matricule = parts[1]
        qr_hash = parts[2]

        conn = _db()
        c = conn.cursor()

        # Chercher l'employé
        c.execute("""SELECT * FROM employes
                     WHERE matricule=? AND actif=1""", (matricule,))
        employe = c.fetchone()

        if not employe:
            conn.close()
            return jsonify(statut='erreur', message=f'Employé {matricule} introuvable')

        # Vérifier que le hash correspond
        expected_content = employe['qr_code_data'] if 'qr_code_data' in employe.keys() else None
        if expected_content != qr_content:
            conn.close()
            return jsonify(statut='erreur', message='QR code non valide (hash différent)')

        # Déterminer le type de scan (entrée ou sortie)
        today = datetime.now().date().isoformat()
        c.execute("""SELECT * FROM pointages
                     WHERE employe_id=? AND date_pointage=?
                     ORDER BY id DESC LIMIT 1""",
                  (employe['id'], today))
        dernier_pointage = c.fetchone()

        now = datetime.now()
        heure_actuelle = now.strftime('%H:%M')

        # Logique :
        # - Si pas de pointage aujourd'hui → ENTRÉE
        # - Si entrée existe sans sortie → SORTIE
        # - Si entrée + sortie → nouveau cycle (entrée)
        if not dernier_pointage:
            type_scan = 'entree'
            c.execute("""INSERT INTO pointages
                (employe_id, date_pointage, heure_entree, type_pointage,
                 mode, ip_source, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (employe['id'], today, heure_actuelle, 'Normal',
                 'QR Code', request.remote_addr or '', 'Normal',
                 now.isoformat()))
            pointage_id = c.lastrowid
            message = f"Entrée enregistrée à {heure_actuelle}"
            duree = None

        elif not dernier_pointage['heure_sortie']:
            # Calcul durée
            h_entree = dernier_pointage['heure_entree']
            if h_entree:
                try:
                    h1 = int(h_entree.split(':')[0]) * 60 + int(h_entree.split(':')[1])
                    h2 = int(heure_actuelle.split(':')[0]) * 60 + int(heure_actuelle.split(':')[1])
                    duree_min = h2 - h1 - 60  # -1h pause
                    heures_travaillees = duree_min / 60
                    heures_sup = max(0, heures_travaillees - 8)

                    c.execute("""UPDATE pointages SET
                        heure_sortie=?, duree_minutes=?, heures_travaillees=?,
                        heures_sup=?, updated_at=?
                        WHERE id=?""",
                        (heure_actuelle, duree_min, round(heures_travaillees, 2),
                         round(heures_sup, 2), now.isoformat(),
                         dernier_pointage['id']))

                    duree = f"{duree_min // 60}h{duree_min % 60:02d}"
                except Exception:
                    duree = None
            type_scan = 'sortie'
            pointage_id = dernier_pointage['id']
            message = f"Sortie enregistrée à {heure_actuelle}"
        else:
            # Nouveau cycle
            type_scan = 'entree'
            c.execute("""INSERT INTO pointages
                (employe_id, date_pointage, heure_entree, type_pointage,
                 mode, ip_source, statut, created_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (employe['id'], today, heure_actuelle, 'Normal',
                 'QR Code', request.remote_addr or '', 'Normal',
                 now.isoformat()))
            pointage_id = c.lastrowid
            message = f"Nouvelle entrée à {heure_actuelle}"
            duree = None

        # Enregistrer le scan
        c.execute("""INSERT INTO scans_qr
            (employe_id, matricule, qr_content, type_scan, date_scan,
             ip_source, user_agent, resultat, message, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (employe['id'], matricule, qr_content, type_scan,
             now.isoformat(), request.remote_addr or '',
             request.headers.get('User-Agent', '')[:200],
             'Succès', message, now.isoformat()))

        conn.commit()

        # Récupérer infos poste
        c.execute("""SELECT p.nom AS poste FROM postes p
                     WHERE p.id=?""", (employe['poste_id'],))
        poste_row = c.fetchone()
        poste_nom = poste_row['poste'] if poste_row else 'Employé'

        conn.close()

        _log(f'QR_SCAN_{type_scan.upper()}',
             f"Pointage QR {matricule} ({employe['nom']} {employe['prenom']})",
             entity='pointage', entity_id=pointage_id)

        return jsonify(
            statut='succes',
            message=message,
            type_scan=type_scan,
            heure=heure_actuelle,
            duree=duree,
            employe={
                'id': employe['id'],
                'matricule': employe['matricule'],
                'nom': employe['nom'],
                'prenom': employe['prenom'],
                'poste': poste_nom,
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(statut='erreur', message=f'Erreur serveur : {str(e)}'), 500


@qr_bp.route('/pointage/scan/recent')
def scan_recent():
    """Liste les derniers scans (5 dernières minutes)"""
    if not (current_user and current_user.is_authenticated):
        return jsonify(scans=[])

    try:
        conn = _db()
        c = conn.cursor()
        c.execute("""SELECT s.*, e.nom || ' ' || e.prenom AS employe_nom
                     FROM scans_qr s
                     LEFT JOIN employes e ON s.employe_id = e.id
                     WHERE s.date_scan >= datetime('now', '-5 minutes')
                     ORDER BY s.date_scan DESC LIMIT 10""")
        scans = [dict(r) for r in c.fetchall()]
        conn.close()
        return jsonify(scans=scans)
    except Exception:
        return jsonify(scans=[])


# ================================================================
# ==================== API GÉNÉRATION QR ====================
# ================================================================
@qr_bp.route('/api/employe/<int:eid>/qr-image')
def qr_image(eid):
    """Génère une image QR code pour un employé (PNG)"""
    if not (current_user and current_user.is_authenticated):
        return redirect('/login')

    import qrcode

    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM employes WHERE id=?", (eid,))
    employe = c.fetchone()
    conn.close()

    if not employe:
        return "Employé introuvable", 404

    qr_content = employe['qr_code_data'] if 'qr_code_data' in employe.keys() else None
    if not qr_content:
        return "QR code non généré", 404

    # Générer l'image QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_content)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0e7490", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    return send_file(buf, mimetype='image/png')


@qr_bp.route('/api/employe/<int:eid>/qr-badge')
def qr_badge(eid):
    """Génère un badge imprimable (HTML) avec QR code"""
    if not (current_user and current_user.is_authenticated):
        return redirect('/login')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT e.*, p.nom AS poste_nom, d.nom AS dep_nom
                 FROM employes e
                 LEFT JOIN postes p ON e.poste_id = p.id
                 LEFT JOIN departements d ON e.departement_id = d.id
                 WHERE e.id=?""", (eid,))
    e = c.fetchone()
    conn.close()

    if not e:
        return "Employé introuvable", 404

    qr_url = f"/api/employe/{eid}/qr-image"

    html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Badge — {e['prenom']} {e['nom']}</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}}
body{{background:#f0f2f5;padding:30px;display:flex;justify-content:center;align-items:center;min-height:100vh}}
.badge{{width:350px;height:550px;background:white;border-radius:24px;box-shadow:0 15px 40px rgba(0,0,0,0.2);overflow:hidden;position:relative}}
.header{{background:linear-gradient(135deg,#0e7490,#06b6d4);color:white;padding:25px 20px;text-align:center;position:relative}}
.header::after{{content:'';position:absolute;bottom:-15px;left:0;right:0;height:30px;background:white;border-radius:50% 50% 0 0 / 100% 100% 0 0}}
.header h1{{font-size:1.3rem;font-weight:900;letter-spacing:-0.3px}}
.header h1 span{{color:#a5f3fc}}
.header p{{font-size:0.7rem;text-transform:uppercase;letter-spacing:2px;font-weight:700;margin-top:5px;opacity:0.9}}
.photo{{text-align:center;margin-top:20px;margin-bottom:15px}}
.avatar{{width:110px;height:110px;background:linear-gradient(135deg,#0e7490,#06b6d4);border-radius:50%;display:inline-flex;align-items:center;justify-content:center;color:white;font-size:2.5rem;font-weight:900;border:5px solid white;box-shadow:0 8px 24px rgba(14,116,144,0.3)}}
.infos{{text-align:center;padding:0 20px;margin-bottom:15px}}
.infos .nom{{font-size:1.4rem;font-weight:900;color:#0e7490;line-height:1.2}}
.infos .matricule{{font-size:0.9rem;color:#06b6d4;font-weight:800;font-family:monospace;margin-top:5px}}
.infos .poste{{font-size:0.85rem;color:#64748b;margin-top:8px}}
.qr{{text-align:center;margin:20px 0}}
.qr img{{width:180px;height:180px;border:3px solid #0e7490;border-radius:12px;padding:8px;background:white}}
.footer{{position:absolute;bottom:0;left:0;right:0;background:linear-gradient(135deg,#0e7490,#155e75);color:white;padding:15px;text-align:center;font-size:0.7rem;letter-spacing:0.5px}}
.footer strong{{color:#a5f3fc}}
.actions{{text-align:center;margin-top:20px}}
.actions button{{padding:12px 24px;background:linear-gradient(135deg,#0e7490,#06b6d4);color:white;border:none;border-radius:10px;font-weight:700;cursor:pointer;font-size:0.9rem}}
@media print {{
  body{{background:white;padding:0}}
  .actions{{display:none}}
  .badge{{box-shadow:none;border:1px solid #ddd}}
}}
</style>
</head>
<body>
<div class="badge">
  <div class="header">
    <h1>OMEGA <span>POINTAGE</span></h1>
    <p>Carte employé</p>
  </div>

  <div class="photo">
    <div class="avatar">{e['prenom'][0] if e['prenom'] else ''}{e['nom'][0] if e['nom'] else ''}</div>
  </div>

  <div class="infos">
    <div class="nom">{e['prenom']} {e['nom']}</div>
    <div class="matricule">{e['matricule']}</div>
    <div class="poste">{e['poste_nom'] or 'Employé'}</div>
    <div class="poste">{e['dep_nom'] or ''}</div>
  </div>

  <div class="qr">
    <img src="{qr_url}" alt="QR Code">
  </div>

  <div class="footer">
    <strong>OMEGA POINTAGE</strong> · Dakar, Sénégal<br>
    Scan pour pointer
  </div>
</div>

<div class="actions">
  <button onclick="window.print()"><i class="fas fa-print"></i> Imprimer le badge</button>
</div>
</body>
</html>
"""
    return html


# ================================================================
# ==================== GÉNÉRATION AUTO À L'ENREGISTREMENT ====================
# ================================================================
@qr_bp.route('/api/employe/generate-qr', methods=['POST'])
def generate_qr_for_employe():
    """Génère un QR code pour un employé (appelé à l'enregistrement)"""
    if not (current_user and current_user.is_authenticated):
        return jsonify(statut='erreur', message='Non authentifié'), 401

    try:
        data = request.get_json() or {}
        employe_id = data.get('employe_id')

        if not employe_id:
            return jsonify(statut='erreur', message='employe_id requis'), 400

        conn = _db()
        c = conn.cursor()
        c.execute("SELECT * FROM employes WHERE id=?", (employe_id,))
        employe = c.fetchone()

        if not employe:
            conn.close()
            return jsonify(statut='erreur', message='Employé introuvable'), 404

        qr_content, timestamp = _generate_qr_content(employe)

        c.execute("""UPDATE employes SET
            qr_code_data=?, qr_generated_at=?
            WHERE id=?""",
            (qr_content, timestamp, employe_id))
        conn.commit()
        conn.close()

        return jsonify(statut='succes', qr_content=qr_content)

    except Exception as e:
        return jsonify(statut='erreur', message=str(e)), 500
