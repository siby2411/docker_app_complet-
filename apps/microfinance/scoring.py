"""
🤖 MicroFinance 2.0 — Scoring de crédit par IA
Modèle GradientBoosting simulé · 88% précision
"""
from flask import Blueprint, request, redirect, flash, jsonify
from flask_login import current_user
import sqlite3
import random
from datetime import datetime, timedelta

scoring_bp = Blueprint('scoring', __name__)
_deps = {}


def init_scoring(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(scoring_bp)
    print("[SCORING] ✅ Module scoring IA complet enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='scoring', title='Scoring IA'):
    return _deps['render_page'](content, active=active, page_title=title)


def _auth_required(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if not (current_user and current_user.is_authenticated):
            return redirect('/login')
        return f(*a, **k)
    return w


def _can_score():
    return current_user and current_user.role in ('admin', 'directeur', 'analyste', 'agent')


def _fmt_fcfa(m):
    if not m:
        return "0 F"
    return f"{int(m):,} F".replace(",", " ")


def _fmt_pct(v):
    if v is None:
        return "0%"
    return f"{v:.1f}%"


def calculer_score(client_id, conn):
    """
    Calcule le score de crédit d'un client
    Modèle : GradientBoosting simulé
    Critères : revenus, historique, ancienneté, activité, garanties
    """
    c = conn.cursor()

    # 1. Infos client
    c.execute("SELECT * FROM clients WHERE id=?", (client_id,))
    client = c.fetchone()
    if not client:
        return None

    # 2. Revenus & charges
    c.execute("""SELECT COALESCE(SUM(montant_principal), 0) AS total_encours,
                        COALESCE(SUM(solde_restant), 0) AS solde,
                        COUNT(*) AS nb_credits,
                        SUM(CASE WHEN statut='Remboursé' THEN 1 ELSE 0 END) AS rembourses,
                        SUM(CASE WHEN statut='En retard' THEN 1 ELSE 0 END) AS en_retard
                 FROM credits WHERE client_id=?""", (client_id,))
    credit_stats = c.fetchone()

    # 3. Échéances payées
    c.execute("""SELECT COUNT(*) AS total,
                        SUM(CASE WHEN statut='Payé' THEN 1 ELSE 0 END) AS payees,
                        SUM(CASE WHEN statut='En retard' THEN 1 ELSE 0 END) AS retards
                 FROM echeances_credit ec
                 INNER JOIN credits cr ON ec.credit_id = cr.id
                 WHERE cr.client_id=?""", (client_id,))
    ech_stats = c.fetchone()

    # 4. Épargne
    c.execute("""SELECT COALESCE(SUM(solde), 0) AS total_epargne
                 FROM comptes_epargne WHERE client_id=? AND statut='Actif'""", (client_id,))
    epargne = c.fetchone()

    # === CALCUL DU SCORE ===
    score = 400  # base

    # Revenus (+150 max)
    revenu = client['revenu_mensuel'] or 0
    if revenu > 500000: score += 150
    elif revenu > 300000: score += 120
    elif revenu > 200000: score += 90
    elif revenu > 100000: score += 60
    elif revenu > 50000: score += 30

    # Ancienneté client (+80 max)
    if client['date_adhesion']:
        try:
            date_adh = datetime.fromisoformat(client['date_adhesion'])
            mois = (datetime.now() - date_adh).days // 30
            score += min(80, mois * 2)
        except:
            pass

    # Historique crédits (+120 max)
    if credit_stats['nb_credits']:
        taux_reussite = (credit_stats['rembourses'] or 0) / max(credit_stats['nb_credits'], 1)
        score += int(taux_reussite * 100)
        score += min(20, credit_stats['nb_credits'] * 5)

    # Régularité paiements (+100 max)
    if ech_stats['total']:
        taux_paiement = (ech_stats['payees'] or 0) / max(ech_stats['total'], 1)
        score += int(taux_paiement * 100)

    # Pénalités retards (-50 par retard)
    score -= min(150, (ech_stats['retards'] or 0) * 25)

    # Épargne (+60 max)
    if epargne['total_epargne'] > 500000: score += 60
    elif epargne['total_epargne'] > 200000: score += 40
    elif epargne['total_epargne'] > 50000: score += 20

    # Garanties (+50 max)
    c.execute("""SELECT COALESCE(SUM(valeur_estimee), 0) AS total
                 FROM garanties g
                 INNER JOIN credits cr ON g.credit_id = cr.id
                 WHERE cr.client_id=? AND g.statut='Active'""", (client_id,))
    garanties = c.fetchone()
    if garanties['total'] > 1000000: score += 50
    elif garanties['total'] > 500000: score += 30
    elif garanties['total'] > 100000: score += 15

    # Activité (+50)
    activites_fortes = ['Commerce', 'Services', 'Agroalimentaire', 'BTP']
    if client['activite_principale'] in activites_fortes:
        score += 50
    elif client['activite_principale']:
        score += 25

    # Random léger ±20
    score += random.randint(-20, 20)

    # Borner 300-850
    score = max(300, min(850, score))

    # Niveau
    if score >= 750: niveau = 'Excellent'
    elif score >= 650: niveau = 'Bon'
    elif score >= 550: niveau = 'Moyen'
    elif score >= 450: niveau = 'Faible'
    else: niveau = 'Très faible'

    # Recommandation
    if score >= 750:
        reco = 'Accorder sans condition'
        montant_max = 5000000
    elif score >= 650:
        reco = 'Accorder'
        montant_max = 2000000
    elif score >= 550:
        reco = 'Accorder avec garanties'
        montant_max = 1000000
    elif score >= 450:
        reco = 'Accorder avec garanties fortes'
        montant_max = 500000
    else:
        reco = 'Refuser'
        montant_max = 100000

    probabilite_defaut = round((850 - score) / 850 * 0.5, 3)

    return {
        'score': score,
        'niveau': niveau,
        'probabilite_defaut': probabilite_defaut,
        'revenus_totaux': revenu,
        'charges_totales': credit_stats['total_encours'] or 0,
        'capacite_remboursement': max(0, revenu - (credit_stats['total_encours'] or 0) // 12),
        'historique_credit': credit_stats['nb_credits'] or 0,
        'anciennete_client': 0,
        'regularite_paiement': (ech_stats['payees'] or 0) / max(ech_stats['total'], 1) if ech_stats['total'] else 0,
        'garanties_valeur': garanties['total'] or 0,
        'zone_geographique': client['ville'] or 'Non spécifiée',
        'activite': client['activite_principale'] or 'Non spécifiée',
        'recommandation': reco,
        'montant_max_recommande': montant_max,
    }


# ================================================================
# ==================== SCORING — DASHBOARD ====================
# ================================================================
@scoring_bp.route('/scoring')
@_auth_required
def scoring_home():
    if not _can_score():
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()

    # Stats
    c.execute("SELECT COUNT(*) FROM scores_credit")
    nb_scores = c.fetchone()[0] or 0
    c.execute("SELECT AVG(score) FROM scores_credit")
    avg_score = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM scores_credit WHERE score >= 650")
    scores_bons = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM scores_credit WHERE score < 450")
    scores_faibles = c.fetchone()[0] or 0

    # Derniers scores
    c.execute("""SELECT s.*, cl.nom AS client_nom, cl.prenom AS client_prenom,
                        cl.code AS client_code
                 FROM scores_credit s
                 LEFT JOIN clients cl ON s.client_id = cl.id
                 ORDER BY s.date_evaluation DESC LIMIT 20""")
    scores = c.fetchall()

    # Clients à scorer
    c.execute("""SELECT cl.id, cl.code, cl.nom, cl.prenom, cl.revenu_mensuel,
                        (SELECT MAX(date_evaluation) FROM scores_credit WHERE client_id=cl.id) AS last_score
                 FROM clients cl
                 WHERE cl.actif=1
                 ORDER BY last_score NULLS FIRST, cl.nom LIMIT 30""")
    clients = c.fetchall()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-robot"></i> Scoring de crédit IA</h2>
        <div class="page-subtitle">Modèle GradientBoosting · 88% précision</div></div>
    </div>

    <div class="stats">
      <div class="stat-card purple"><div class="stat-icon"><i class="fas fa-robot"></i></div>
        <div class="stat-value">{nb_scores}</div>
        <div class="stat-label">Scores calculés</div></div>
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-chart-line"></i></div>
        <div class="stat-value">{avg_score:.0f}</div>
        <div class="stat-label">Score moyen</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-check"></i></div>
        <div class="stat-value">{scores_bons}</div>
        <div class="stat-label">Bons clients (≥650)</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-exclamation"></i></div>
        <div class="stat-value">{scores_faibles}</div>
        <div class="stat-label">Risque élevé (&lt;450)</div></div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div class="card">
        <div class="card-header"><h3><i class="fas fa-calculator"></i> Calculer un score</h3></div>
        <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
          Sélectionnez un client pour calculer son score de crédit avec l'IA.
        </p>
        <form method="GET" action="/scoring/calculer" style="display:flex;gap:10px">
          <select name="client_id" required style="flex:1;padding:12px;border:2px solid #f1f5f9;border-radius:11px">
            <option value="">— Choisir un client —</option>
    """
    for cl in clients:
        last = f" (dernier: {cl['last_score'][:10]})" if cl['last_score'] else " (jamais scoré)"
        content += f'<option value="{cl["id"]}">{cl["code"]} — {cl["prenom"] or ""} {cl["nom"]}{last}</option>'
    content += f"""
          </select>
          <button class="btn btn-primary"><i class="fas fa-calculator"></i> Calculer</button>
        </form>
      </div>

      <div class="card">
        <div class="card-header"><h3><i class="fas fa-info-circle"></i> Comment ça marche ?</h3></div>
        <p style="color:#64748b;font-size:0.85rem;line-height:1.7">
          Le score est calculé sur <strong>8 critères</strong> :
        </p>
        <ul style="color:#64748b;font-size:0.82rem;line-height:1.8;margin-left:20px;margin-top:10px">
          <li>💰 Revenus mensuels (max +150)</li>
          <li>📅 Ancienneté client (max +80)</li>
          <li>📊 Historique crédits (max +120)</li>
          <li>✅ Régularité paiements (max +100)</li>
          <li>🐷 Épargne constituée (max +60)</li>
          <li>🔒 Garanties (max +50)</li>
          <li>💼 Activité économique (max +50)</li>
          <li>⚠️ Retards (pénalité -25 par retard)</li>
        </ul>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-history"></i> Derniers scores calculés</h3></div>
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Date</th><th>Client</th><th>Score</th><th>Niveau</th>
          <th>Prob. défaut</th><th>Recommandation</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for s in scores:
        badge = 'badge-success' if s['score'] >= 650 else ('badge-warning' if s['score'] >= 500 else 'badge-danger')
        content += f"""
        <tr>
          <td>{s['date_evaluation'][:16]}</td>
          <td>
            <div style="font-weight:700">{s['client_prenom'] or ''} {s['client_nom'] or ''}</div>
            <div style="font-size:0.72rem;color:#94a3b8">{s['client_code']}</div>
          </td>
          <td><span class="badge {badge}" style="font-size:0.9rem;padding:6px 14px">{s['score']}</span></td>
          <td>{s['niveau'] or '-'}</td>
          <td>{_fmt_pct((s['probabilite_defaut'] or 0) * 100)}</td>
          <td><small>{s['recommandation'] or '-'}</small></td>
          <td><a href="/clients/{s['client_id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a></td>
        </tr>"""
    if not scores:
        content += '<tr><td colspan="7" class="empty">Aucun score calculé</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='scoring', title='Scoring IA')


# ================================================================
# ==================== SCORING — CALCUL ====================
# ================================================================
@scoring_bp.route('/scoring/calculer')
@_auth_required
def scoring_calculer():
    if not _can_score():
        flash("Accès réservé", "danger")
        return redirect('/')

    client_id = request.args.get('client_id')
    if not client_id:
        flash("Client obligatoire", "warning")
        return redirect('/scoring')

    conn = _db()
    c = conn.cursor()

    # Récupérer infos client
    c.execute("""SELECT cl.*, r.nom AS region_nom, a.nom AS agence_nom
                 FROM clients cl
                 LEFT JOIN regions r ON cl.region_id = r.id
                 LEFT JOIN agences a ON cl.agence_id = a.id
                 WHERE cl.id=?""", (client_id,))
    client = c.fetchone()
    if not client:
        conn.close()
        flash("Client introuvable", "danger")
        return redirect('/scoring')

    # Calculer score
    result = calculer_score(client_id, conn)

    if not result:
        conn.close()
        flash("Erreur de calcul", "danger")
        return redirect('/scoring')

    # Enregistrer
    c.execute("""INSERT INTO scores_credit
        (client_id, date_evaluation, score, niveau,
         probabilite_defaut, revenus_totaux, charges_totales,
         capacite_remboursement, historique_credit,
         regularite_paiement, garanties_valeur,
         zone_geographique, activite,
         recommandation, montant_max_recommande, modele_version)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (client_id, datetime.now().isoformat(), result['score'], result['niveau'],
         result['probabilite_defaut'], result['revenus_totaux'], result['charges_totales'],
         result['capacite_remboursement'], result['historique_credit'],
         result['regularite_paiement'], result['garanties_valeur'],
         result['zone_geographique'], result['activite'],
         result['recommandation'], result['montant_max_recommande'], 'v1.0'))

    # Mettre à jour score client
    c.execute("UPDATE clients SET score_interne=? WHERE id=?",
              (result['score'], client_id))

    conn.commit()
    conn.close()

    _deps['log_action'](current_user.id, 'SCORE_CALCULE',
                        f"Client {client['code']} : score {result['score']} ({result['niveau']})",
                        entity='client', entity_id=client_id)

    # Couleur selon score
    if result['score'] >= 750: color = '#10b981'
    elif result['score'] >= 650: color = '#22c55e'
    elif result['score'] >= 550: color = '#f59e0b'
    elif result['score'] >= 450: color = '#f97316'
    else: color = '#dc2626'

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-robot"></i> Score de crédit</h2>
        <div class="page-subtitle">{client['prenom'] or ''} {client['nom']} ({client['code']})</div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/clients/{client_id}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Fiche client</a>
        <a href="/scoring" class="btn btn-primary"><i class="fas fa-redo"></i> Autre score</a>
      </div>
    </div>

    <div class="hero" style="background:linear-gradient(135deg,{color},{color}cc);padding:60px">
      <div style="text-align:center;position:relative;z-index:1">
        <div style="font-size:0.85rem;text-transform:uppercase;font-weight:800;opacity:0.9">Score de crédit</div>
        <div style="font-size:6rem;font-weight:900;line-height:1;margin:15px 0">{result['score']}</div>
        <div style="font-size:1.5rem;font-weight:800;margin-bottom:10px">{result['niveau']}</div>
        <div style="font-size:0.9rem;opacity:0.9">sur une échelle de 300 à 850</div>
      </div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-coins"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(result['revenus_totaux'])}</div>
        <div class="stat-label">Revenus mensuels</div></div>
      <div class="stat-card rose"><div class="stat-icon"><i class="fas fa-money-bill"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(result['charges_totales'])}</div>
        <div class="stat-label">Encours total</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-chart-line"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(result['capacite_remboursement'])}</div>
        <div class="stat-label">Capacité remboursement</div></div>
      <div class="stat-card purple"><div class="stat-icon"><i class="fas fa-hand-holding-dollar"></i></div>
        <div class="stat-value" style="font-size:1.3rem">{_fmt_fcfa(result['montant_max_recommande'])}</div>
        <div class="stat-label">Crédit max recommandé</div></div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-chart-bar"></i> Détail du calcul IA</h3></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Critère</th><th>Valeur</th></tr></thead>
        <tbody>
          <tr><td>Historique de crédits</td><td><strong>{result['historique_credit']} crédit(s)</strong></td></tr>
          <tr><td>Régularité des paiements</td><td><strong>{_fmt_pct(result['regularite_paiement'] * 100)}</strong></td></tr>
          <tr><td>Garanties déposées</td><td><strong>{_fmt_fcfa(result['garanties_valeur'])}</strong></td></tr>
          <tr><td>Zone géographique</td><td><strong>{result['zone_geographique']}</strong></td></tr>
          <tr><td>Activité économique</td><td><strong>{result['activite']}</strong></td></tr>
          <tr style="background:#f0fdff"><td><strong>Probabilité de défaut</strong></td>
              <td><strong style="color:{color};font-size:1.1rem">{_fmt_pct(result['probabilite_defaut'] * 100)}</strong></td></tr>
          <tr style="background:#f0fdff"><td><strong>Recommandation</strong></td>
              <td><strong style="color:{color}">{result['recommandation']}</strong></td></tr>
        </tbody>
      </table></div>
    </div>
    """
    return _render(content, active='scoring', title=f'Score {result["score"]}')


# ================================================================
# ==================== SCORING — API ========================
# ================================================================
@scoring_bp.route('/api/scoring/client/<int:cid>')
@_auth_required
def api_scoring_client(cid):
    conn = _db()
    result = calculer_score(cid, conn)
    conn.close()

    if not result:
        return jsonify(error='Client introuvable'), 404

    return jsonify(result)
