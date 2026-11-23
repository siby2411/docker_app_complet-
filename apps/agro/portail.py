"""
🌐 Omega Agro-Industrie — Portail projet
Présentation · Méthodologie · APIX exonération · Contact
"""
from flask import Blueprint, request, redirect, flash, jsonify, render_template_string
from flask_login import current_user, login_required
from datetime import datetime

portail_bp = Blueprint('portail', __name__)
_deps = {}


def init_portail(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(portail_bp)
    print("[PORTAIL] ✅ Module portail enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='portail', title='Portail'):
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


# ═══════════════════════════════════════════════════════════════
# 🌐 PORTAIL PROJET
# ═══════════════════════════════════════════════════════════════

@portail_bp.route('/portail/projet')
@login_required
def portail_projet():
    content = """
    <div style="background:linear-gradient(135deg,#1e40af,#3b82f6);color:#fff;padding:30px;border-radius:12px;margin-bottom:24px">
      <h1 style="margin:0;font-size:28px">🌾 OMEGA AGRO-INDUSTRIE</h1>
      <p style="margin:10px 0 0;opacity:.95;font-size:15px">Prolongement de <strong>SM10 AGRO</strong> au Sénégal — Initiative de l'international footballeur <strong>Sadio Mané</strong></p>
      <div style="display:flex;gap:20px;margin-top:16px;flex-wrap:wrap">
        <div><strong style="font-size:22px">11,4 Milliards</strong><br><small style="opacity:.85">FCFA investissement</small></div>
        <div><strong style="font-size:22px">1ère</strong><br><small style="opacity:.85">au Sénégal (mangue + cajou)</small></div>
        <div><strong style="font-size:22px">500</strong><br><small style="opacity:.85">unités transformatrices cibles</small></div>
        <div><strong style="font-size:22px">+25%</strong><br><small style="opacity:.85">valeur ajoutée locale</small></div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px">
      <div style="background:#fff;padding:24px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
        <h2 style="margin-top:0;color:#1f2937;font-size:18px">🥭 Filières intégrées</h2>
        <ul style="line-height:2;color:#374151;margin:0;padding-left:20px">
          <li><strong>Mangue</strong> — transformation (pulpe, séchage, jus)</li>
          <li><strong>Noix de cajou</strong> — décorticage, torréfaction</li>
          <li><strong>Fruits & légumes</strong> — chaîne complète</li>
          <li><strong>Étude technique</strong> — matériels agricoles</li>
          <li><strong>Énergie</strong> — panneaux solaires</li>
        </ul>
      </div>
      <div style="background:#fff;padding:24px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
        <h2 style="margin-top:0;color:#1f2937;font-size:18px">🎯 Problématique résolue</h2>
        <div style="background:#fef2f2;border-left:4px solid #ef4444;padding:14px;border-radius:8px;margin-bottom:12px">
          <strong style="color:#b91c1c">40% des récoltes perdues</strong><br>
          <small>faute de transformation locale</small>
        </div>
        <p style="color:#374151;margin:0">Solution intégrée : transformation locale + traçabilité QR + export UE certifié</p>
      </div>
    </div>

    <div style="background:#fff;padding:24px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.1);margin-bottom:24px">
      <h2 style="margin-top:0;color:#1f2937;font-size:18px">🛠 Méthodologie — Chaîne de valeur agricole</h2>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px">
        <div style="background:#f0f9ff;padding:16px;border-radius:10px;border-left:4px solid #3b82f6">
          <strong>🏭 Transformation</strong><br><small>Moulins, huileries, conserveries</small>
        </div>
        <div style="background:#f0fdf4;padding:16px;border-radius:10px;border-left:4px solid #10b981">
          <strong>📦 Traçabilité QR</strong><br><small>Du champ à l'assiette</small>
        </div>
        <div style="background:#fffbeb;padding:16px;border-radius:10px;border-left:4px solid #f59e0b">
          <strong>🚛 Logistique</strong><br><small>Producteurs ↔ transformateurs</small>
        </div>
        <div style="background:#faf5ff;padding:16px;border-radius:10px;border-left:4px solid #a855f7">
          <strong>💰 Contrats d'achat</strong><br><small>Sécurisation revenus</small>
        </div>
        <div style="background:#fef2f2;padding:16px;border-radius:10px;border-left:4px solid #ef4444">
          <strong>🔬 Contrôle qualité</strong><br><small>Labo virtuel HACCP</small>
        </div>
        <div style="background:#eef2ff;padding:16px;border-radius:10px;border-left:4px solid #6366f1">
          <strong>🌍 Export UE</strong><br><small>Certifications ISO 22000</small>
        </div>
      </div>
    </div>

    <div style="background:linear-gradient(135deg,#7c3aed,#5b21b6);color:#fff;padding:24px;border-radius:12px">
      <h2 style="margin-top:0;font-size:18px">🎓 Centre de formation intégré</h2>
      <p style="opacity:.95;margin:0">Formation des producteurs aux bonnes pratiques agricoles, à la transformation et aux normes d'export UE.</p>
    </div>
    """
    return _render(content, active='portail', title='Projet OMEGA AGRO')


@portail_bp.route('/portail/apix')
@login_required
def portail_apix():
    content = """
    <div style="background:linear-gradient(135deg,#10b981,#047857);color:#fff;padding:30px;border-radius:12px;margin-bottom:24px">
      <h1 style="margin:0;font-size:26px">📋 APIX — Agence de Promotion des Investissements et des Grands Travaux</h1>
      <p style="margin:10px 0 0;opacity:.95">Demande d'exonération sur l'importation de matériels — Durée : <strong>5 ans</strong></p>
    </div>

    <div style="background:#fff;padding:24px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.1);margin-bottom:20px">
      <h2 style="margin-top:0;color:#1f2937;font-size:18px">🎯 Objet de la demande</h2>
      <p style="color:#374151;line-height:1.8">
        Conformément au cahier des charges du projet <strong>OMEGA AGRO-INDUSTRIE</strong>, prolongement de SM10 AGRO au Sénégal,
        nous sollicitons auprès de l'APIX une exonération totale des droits et taxes sur l'importation
        des matériels stratégiques pour une durée de <strong>5 ans</strong>.
      </p>
    </div>

    <div style="background:#fff;padding:24px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.1);margin-bottom:20px">
      <h2 style="margin-top:0;color:#1f2937;font-size:18px">📦 Matériels concernés</h2>
      <table style="width:100%;border-collapse:collapse">
        <thead>
          <tr style="background:#f9fafb">
            <th style="padding:12px;text-align:left">Catégorie</th>
            <th style="padding:12px;text-align:left">Détail</th>
            <th style="padding:12px;text-align:right">Valeur estimée</th>
          </tr>
        </thead>
        <tbody>
          <tr><td style="padding:12px;border-bottom:1px solid #f3f4f6">🏭 Lignes de transformation</td><td style="padding:12px;border-bottom:1px solid #f3f4f6">Moulins, huileries, conserveries</td><td style="padding:12px;border-bottom:1px solid #f3f4f6;text-align:right">4,2 Md FCFA</td></tr>
          <tr><td style="padding:12px;border-bottom:1px solid #f3f4f6">☀️ Panneaux solaires</td><td style="padding:12px;border-bottom:1px solid #f3f4f6">Énergie renouvelable pour les sites</td><td style="padding:12px;border-bottom:1px solid #f3f4f6;text-align:right">1,8 Md FCFA</td></tr>
          <tr><td style="padding:12px;border-bottom:1px solid #f3f4f6">🚜 Matériels agricoles</td><td style="padding:12px;border-bottom:1px solid #f3f4f6">Tracteurs, outils, irrigation</td><td style="padding:12px;border-bottom:1px solid #f3f4f6;text-align:right">2,5 Md FCFA</td></tr>
          <tr><td style="padding:12px;border-bottom:1px solid #f3f4f6">📦 Équipements emballage</td><td style="padding:12px;border-bottom:1px solid #f3f4f6">Conditionnement, étiquetage</td><td style="padding:12px;border-bottom:1px solid #f3f4f6;text-align:right">1,4 Md FCFA</td></tr>
          <tr><td style="padding:12px;border-bottom:1px solid #f3f4f6">🔬 Labo qualité</td><td style="padding:12px;border-bottom:1px solid #f3f4f6">HACCP, analyses</td><td style="padding:12px;border-bottom:1px solid #f3f4f6;text-align:right">0,8 Md FCFA</td></tr>
          <tr><td style="padding:12px;border-bottom:1px solid #f3f4f6">🎓 Centre de formation</td><td style="padding:12px;border-bottom:1px solid #f3f4f6">Équipements pédagogiques</td><td style="padding:12px;border-bottom:1px solid #f3f4f6;text-align:right">0,7 Md FCFA</td></tr>
          <tr style="background:#f0fdf4;font-weight:700"><td style="padding:12px" colspan="2">TOTAL</td><td style="padding:12px;text-align:right;color:#047857">11,4 Md FCFA</td></tr>
        </tbody>
      </table>
    </div>

    <div style="background:#fff;padding:24px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
      <h2 style="margin-top:0;color:#1f2937;font-size:18px">📞 Contact APIX</h2>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div>
          <strong>Agence de Promotion des Investissements et des Grands Travaux</strong><br>
          <small style="color:#6b7280">Rue Aimé Césaire, Dakar, Sénégal</small>
        </div>
        <div>
          <strong>Site web :</strong> <a href="https://www.investinsenegal.com" target="_blank" style="color:#3b82f6">investinsenegal.com</a><br>
          <strong>Email :</strong> <a href="mailto:contact@apix.sn" style="color:#3b82f6">contact@apix.sn</a>
        </div>
      </div>
    </div>
    """
    return _render(content, active='portail', title='APIX Exonération')


@portail_bp.route('/portail/public')
def portail_public():
    """Page publique — accessible sans login."""
    content = """
    <div style="text-align:center;padding:40px 20px">
      <h1 style="color:#1f2937;font-size:32px">🌾 OMEGA AGRO-INDUSTRIE</h1>
      <p style="color:#6b7280;font-size:17px;max-width:700px;margin:18px auto">Prolongement de SM10 AGRO au Sénégal — transformation mangue, noix de cajou, fruits et légumes</p>
      <div style="display:flex;gap:30px;justify-content:center;margin:30px 0;flex-wrap:wrap">
        <div><strong style="color:#1e40af;font-size:24px">11,4 Md</strong><br><small style="color:#6b7280">FCFA investissement</small></div>
        <div><strong style="color:#1e40af;font-size:24px">500</strong><br><small style="color:#6b7280">unités cibles</small></div>
        <div><strong style="color:#1e40af;font-size:24px">+25%</strong><br><small style="color:#6b7280">valeur locale</small></div>
      </div>
      <a href="/login" style="background:#10b981;color:#fff;padding:14px 36px;border-radius:10px;text-decoration:none;font-weight:700;font-size:16px">🔐 Accéder à la plateforme</a>
    </div>
    """
    return _render(content, active='portail', title='Accueil OMEGA AGRO')
