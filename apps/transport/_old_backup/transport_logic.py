"""
Omega Transport V2 — Logique métier complète
Billetterie QR · Contrôle recettes · Carburant anti-détournement · Feuille de route
"""
from flask import Blueprint, request, redirect, flash, jsonify, Response, render_template_string
from flask_login import current_user
import sqlite3
import hashlib
import io
import os
import random
import string
from datetime import datetime, timedelta

transport_bp = Blueprint('transport', __name__)
_deps = {}


def init_transport(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(transport_bp)
    print("[TRANSPORT] ✅ Module logique complet enregistré")


def _db():
    return _deps['get_db']()


def _render(content, active='dashboard', title='Omega Transport'):
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


def _can_operate():
    return current_user and current_user.role in ('admin', 'directeur', 'chef_exploitation',
                                                   'guichetier', 'controleur', 'caissier')


def _can_validate():
    return current_user and current_user.role in ('admin', 'directeur', 'chef_exploitation')


def _fmt_fcfa(m):
    if not m:
        return "0 F"
    return f"{int(m):,} F".replace(",", " ")


def _fmt_km(km):
    if not km:
        return "0 km"
    return f"{int(km):,} km".replace(",", " ")


def _hash(txt):
    return hashlib.sha256(txt.encode()).hexdigest()


def _gen_numero_billet():
    """BIL-20260916-A1B2C3"""
    today = datetime.now().strftime('%Y%m%d')
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"BIL-{today}-{suffix}"


def _gen_numero_voyage():
    today = datetime.now().strftime('%Y%m%d')
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"VOY-{today}-{suffix}"


def _next_voyage_id():
    """Retourne le prochain numéro de voyage disponible"""
    return _gen_numero_voyage()


# ================================================================
# ==================== BILLETTERIE ====================
# ================================================================
@transport_bp.route('/billets')
@_auth_required
def billets_list():
    if not _can_operate():
        flash("Accès réservé au personnel", "danger")
        return redirect('/')

    date = request.args.get('date') or datetime.now().date().isoformat()
    voyage_id = request.args.get('voyage') or ''
    q = (request.args.get('q') or '').strip()

    conn = _db()
    c = conn.cursor()
    sql = """SELECT b.*,
                    vo.numero AS voyage_numero, vo.date_voyage, vo.heure_depart_prevue,
                    l.code AS ligne_code, l.ville_depart, l.ville_arrivee,
                    v.immatriculation
             FROM billets b
             LEFT JOIN voyages vo ON b.voyage_id = vo.id
             LEFT JOIN lignes l ON vo.ligne_id = l.id
             LEFT JOIN vehicules v ON vo.vehicule_id = v.id
             WHERE date(b.date_emission) = ?"""
    params = [date]
    if voyage_id:
        sql += " AND b.voyage_id=?"
        params.append(voyage_id)
    if q:
        sql += " AND (b.numero LIKE ? OR b.passager_nom LIKE ? OR b.passager_telephone LIKE ?)"
        params += [f"%{q}%"] * 3
    sql += " ORDER BY b.date_emission DESC LIMIT 200"
    c.execute(sql, params)
    billets = c.fetchall()

    # Stats
    c.execute("""SELECT COUNT(*) AS nb, COALESCE(SUM(prix), 0) AS total
                 FROM billets WHERE date(date_emission)=?""", (date,))
    stats = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-ticket"></i> Billetterie</h2>
        <div class="page-subtitle">{len(billets)} billet(s) — {date}</div></div>
      <a href="/billets/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Vendre un billet</a>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-ticket"></i></div>
        <div class="stat-value">{stats['nb']}</div>
        <div class="stat-label">Billets vendus</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-money-bill-wave"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(stats['total'])}</div>
        <div class="stat-label">Recette totale</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-coins"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(stats['total'] // max(stats['nb'], 1))}</div>
        <div class="stat-label">Prix moyen</div></div>
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Date</label>
          <input type="date" name="date" value="{date}">
        </div>
        <div class="form-group" style="flex:2;margin:0;min-width:200px">
          <label>Recherche</label>
          <input type="text" name="q" value="{q}" placeholder="N° billet, passager, téléphone...">
        </div>
        <button class="btn btn-primary"><i class="fas fa-search"></i> Filtrer</button>
        <a href="/billets" class="btn btn-info"><i class="fas fa-rotate"></i></a>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>N° Billet</th><th>Voyage</th><th>Trajet</th>
          <th>Passager</th><th>Place</th><th>Prix</th><th>Paiement</th><th>Heure</th>
        </tr></thead><tbody>
    """
    for b in billets:
        content += f"""
        <tr>
          <td><strong>{b['numero']}</strong></td>
          <td><small>{b['ligne_code'] or '-'}</small>
              <div style="font-size:0.72rem;color:#94a3b8">{b['heure_depart_prevue'] or ''}</div></td>
          <td><small>{b['ville_depart'] or ''} → {b['ville_arrivee'] or ''}</small></td>
          <td><strong>{b['passager_nom'] or '-'}</strong>
              <div style="font-size:0.72rem;color:#94a3b8">{b['passager_telephone'] or ''}</div></td>
          <td><span class="badge badge-primary">#{b['numero_place'] or '-'}</span></td>
          <td><strong>{_fmt_fcfa(b['prix'])}</strong></td>
          <td><small>{b['mode_paiement'] or '-'}</small></td>
          <td><small>{b['date_emission'][11:16] if b['date_emission'] else '-'}</small></td>
        </tr>"""
    if not billets:
        content += '<tr><td colspan="8" class="empty"><i class="fas fa-ticket"></i><br>Aucun billet</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='billets', title='Billetterie')


@transport_bp.route('/billets/nouveau', methods=['GET', 'POST'])
@_auth_required
def billets_nouveau():
    if not _can_operate():
        flash("Accès réservé au personnel", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        voyage_id = request.form.get('voyage_id')
        passager_nom = (request.form.get('passager_nom') or '').strip()
        passager_tel = (request.form.get('passager_telephone') or '').strip()
        classe = request.form.get('classe') or '2ème'
        numero_place = request.form.get('numero_place')
        prix = int(request.form.get('prix') or 0)
        mode_paiement = request.form.get('mode_paiement') or 'Espèces'

        if not (voyage_id and passager_nom and prix > 0):
            flash("Voyage, passager et prix obligatoires", "warning")
        else:
            try:
                # Vérifier le voyage
                c.execute("SELECT * FROM voyages WHERE id=?", (voyage_id,))
                voy = c.fetchone()
                if not voy:
                    flash("Voyage introuvable", "danger")
                elif voy['places_vendues'] >= voy['places_totales']:
                    flash("Voyage complet", "warning")
                else:
                    # Générer numéro + hash QR
                    num_billet = _gen_numero_billet()
                    qr_data = f"{num_billet}|{voyage_id}|{numero_place or 0}|{prix}"
                    qr_hash = _hash(qr_data)

                    c.execute("""INSERT INTO billets
                        (numero, voyage_id, passager_nom, passager_telephone,
                         numero_place, classe, prix, statut, mode_paiement,
                         vendeur_id, qr_code, checksum, date_emission)
                        VALUES (?,?,?,?,?,?,?,'Vendu',?,?,?,?,?)""",
                        (num_billet, voyage_id, passager_nom, passager_tel,
                         int(numero_place) if numero_place else None,
                         classe, prix, mode_paiement,
                         current_user.id, qr_hash[:32], qr_hash,
                         datetime.now().isoformat()))
                    billet_id = c.lastrowid

                    # Mettre à jour le voyage
                    c.execute("""UPDATE voyages SET
                        places_vendues = places_vendues + 1,
                        places_disponibles = places_totales - places_vendues - 1,
                        recette_attendue = recette_attendue + ?
                        WHERE id=?""", (prix, voyage_id))

                    conn.commit()
                    _log('CREATE_BILLET',
                         f"Billet {num_billet} vendu ({passager_nom})",
                         entity='billet', entity_id=billet_id)
                    flash(f"Billet {num_billet} vendu !", "success")
                    conn.close()
                    return redirect(f'/billets/{billet_id}')

            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    # GET : formulaire
    voyage_id = request.args.get('voyage') or ''
    c.execute("""SELECT vo.*, l.code AS ligne_code, l.ville_depart, l.ville_arrivee,
                        l.tarif_base, l.tarif_1ere, l.tarif_2eme,
                        v.immatriculation, v.capacite_places
                 FROM voyages vo
                 LEFT JOIN lignes l ON vo.ligne_id = l.id
                 LEFT JOIN vehicules v ON vo.vehicule_id = v.id
                 WHERE vo.statut IN ('Programmé', 'En cours')
                   AND date(vo.date_voyage) >= date('now')
                 ORDER BY vo.date_voyage, vo.heure_depart_prevue LIMIT 100""")
    voyages = c.fetchall()
    conn.close()

    opt_v = '<option value="">— Choisir un voyage —</option>'
    for v in voyages:
        sel = 'selected' if str(v['id']) == voyage_id else ''
        places_dispo = (v['places_totales'] or 0) - (v['places_vendues'] or 0)
        opt_v += f'<option value="{v["id"]}" {sel} data-prix="{v["tarif_base"]}" data-prix1="{v["tarif_1ere"] or 0}" data-places="{places_dispo}">{v["ligne_code"]} · {v["ville_depart"]}→{v["ville_arrivee"]} · {v["heure_depart_prevue"]} · {places_dispo} places</option>'

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-ticket"></i> Vendre un billet</h2>
        <div class="page-subtitle">Billetterie avec QR code anti-fraude</div></div>
      <a href="/billets" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>

    <div class="card">
      <form method="POST" id="billet-form">
        <div class="form-grid">
          <div class="form-group form-full">
            <label>Voyage *</label>
            <select name="voyage_id" id="voyage_select" required>
              {opt_v}
            </select>
          </div>

          <div class="form-group form-full">
            <label>Nom du passager *</label>
            <input type="text" name="passager_nom" required placeholder="Ex: Mamadou Diop" autofocus>
          </div>

          <div class="form-group">
            <label>Téléphone passager</label>
            <input type="text" name="passager_telephone" placeholder="77 123 45 67">
          </div>

          <div class="form-group">
            <label>Classe</label>
            <select name="classe" id="classe_select">
              <option value="2ème">2ème classe</option>
              <option value="1ère">1ère classe (VIP)</option>
            </select>
          </div>

          <div class="form-group">
            <label>Numéro de place</label>
            <input type="number" name="numero_place" min="1" max="60" placeholder="Auto si vide">
          </div>

          <div class="form-group">
            <label>Prix (FCFA) *</label>
            <input type="number" name="prix" id="prix_input" required value="0">
          </div>

          <div class="form-group">
            <label>Mode de paiement</label>
            <select name="mode_paiement">
              <option>Espèces</option>
              <option>Wave</option>
              <option>Orange Money</option>
              <option>Carte bancaire</option>
              <option>Virement</option>
            </select>
          </div>
        </div>

        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-primary"><i class="fas fa-ticket"></i> Vendre le billet</button>
          <a href="/billets" class="btn btn-info"><i class="fas fa-xmark"></i> Annuler</a>
        </div>
      </form>
    </div>

    <script>
    const select = document.getElementById('voyage_select');
    const prixInput = document.getElementById('prix_input');
    const classeSelect = document.getElementById('classe_select');

    function updatePrix() {{
      const opt = select.options[select.selectedIndex];
      if (!opt.value) {{ prixInput.value = 0; return; }}
      const prix2 = parseFloat(opt.dataset.prix) || 0;
      const prix1 = parseFloat(opt.dataset.prix1) || prix2 * 1.5;
      if (classeSelect.value === '1ère') {{
        prixInput.value = Math.round(prix1);
      }} else {{
        prixInput.value = Math.round(prix2);
      }}
    }}

    select.addEventListener('change', updatePrix);
    classeSelect.addEventListener('change', updatePrix);
    if (select.value) updatePrix();
    </script>
    """
    return _render(content, active='billets', title='Vendre un billet')


@transport_bp.route('/billets/<int:bid>')
@_auth_required
def billets_detail(bid):
    if not _can_operate():
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT b.*,
                        vo.numero AS voyage_numero, vo.date_voyage, vo.heure_depart_prevue,
                        l.code AS ligne_code, l.ville_depart, l.ville_arrivee,
                        v.immatriculation, v.modele
                 FROM billets b
                 LEFT JOIN voyages vo ON b.voyage_id = vo.id
                 LEFT JOIN lignes l ON vo.ligne_id = l.id
                 LEFT JOIN vehicules v ON vo.vehicule_id = v.id
                 WHERE b.id=?""", (bid,))
    b = c.fetchone()
    conn.close()

    if not b:
        flash("Billet introuvable", "danger")
        return redirect('/billets')

    # QR code URL (API Google Chart ou autre service public)
    qr_data = f"{b['numero']}|{b['voyage_id']}|{b['numero_place']}|{b['prix']}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={qr_data}"

    content = f"""
    <div class="page-header">
      <div>
        <h2><i class="fas fa-ticket"></i> Billet {b['numero']}</h2>
        <div class="page-subtitle">Émis le {b['date_emission'][:19] if b['date_emission'] else '-'}</div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/billets" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
        <button onclick="window.print()" class="btn btn-primary"><i class="fas fa-print"></i> Imprimer</button>
      </div>
    </div>

    <div class="card" style="background:linear-gradient(135deg,#f0fdff,#cffafe)">
      <div style="display:grid;grid-template-columns:2fr 1fr;gap:30px;align-items:center">
        <div>
          <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Voyage</div>
          <div style="font-size:1.5rem;font-weight:900;color:#0e7490;margin-bottom:5px">
            {b['ville_depart']} → {b['ville_arrivee']}
          </div>
          <div style="font-size:0.9rem;color:#06b6d4;font-weight:700">{b['ligne_code']}</div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:30px">
            <div>
              <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;font-weight:800">Passager</div>
              <div style="font-weight:800">{b['passager_nom']}</div>
            </div>
            <div>
              <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;font-weight:800">Téléphone</div>
              <div>{b['passager_telephone'] or '-'}</div>
            </div>
            <div>
              <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;font-weight:800">Date</div>
              <div style="font-weight:700">{b['date_voyage']}</div>
            </div>
            <div>
              <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;font-weight:800">Heure départ</div>
              <div style="font-weight:700">{b['heure_depart_prevue'] or '-'}</div>
            </div>
            <div>
              <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;font-weight:800">Place</div>
              <div style="font-size:1.3rem;font-weight:900;color:#06b6d4">#{b['numero_place'] or '-'}</div>
            </div>
            <div>
              <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;font-weight:800">Classe</div>
              <div><span class="badge badge-primary">{b['classe']}</span></div>
            </div>
            <div>
              <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;font-weight:800">Véhicule</div>
              <div style="font-weight:700">{b['immatriculation'] or '-'}</div>
            </div>
            <div>
              <div style="font-size:0.7rem;color:#64748b;text-transform:uppercase;font-weight:800">Prix payé</div>
              <div style="font-size:1.3rem;font-weight:900;color:#16a34a">{_fmt_fcfa(b['prix'])}</div>
            </div>
          </div>

          <div style="margin-top:25px;font-size:0.75rem;color:#64748b;font-family:monospace">
            Hash: {b['checksum'][:32] if b['checksum'] else '-'}...
          </div>
        </div>

        <div style="text-align:center;background:white;padding:20px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1)">
          <img src="{qr_url}" alt="QR code" style="width:200px;height:200px">
          <div style="margin-top:12px;font-size:0.7rem;color:#64748b;font-weight:700">
            SCANNEZ POUR VÉRIFIER
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3><i class="fas fa-info-circle"></i> Actions</h3></div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        {'<a href="/billets/'+str(bid)+'/embarquer" class="btn btn-success"><i class="fas fa-check"></i> Marquer comme embarqué</a>' if b['statut']=='Vendu' else ''}
        {'<a href="/billets/'+str(bid)+'/annuler" class="btn btn-danger" onclick="return confirm(&#39;Annuler ce billet ?&#39;)"><i class="fas fa-xmark"></i> Annuler</a>' if b['statut']=='Vendu' and _can_validate() else ''}
      </div>
    </div>
    """
    return _render(content, active='billets', title=b['numero'])


@transport_bp.route('/billets/<int:bid>/embarquer')
@_auth_required
def billets_embarquer(bid):
    if not _can_operate():
        flash("Accès réservé", "danger")
        return redirect('/')
    conn = _db()
    c = conn.cursor()
    c.execute("""UPDATE billets SET statut='Embarqué',
                 date_embarquement=?, controleur_id=? WHERE id=?""",
              (datetime.now().isoformat(), current_user.id, bid))
    conn.commit()
    _log('BILLET_EMBARQUE', f"Billet id={bid} embarqué", entity='billet', entity_id=bid)
    conn.close()
    flash("Billet marqué comme embarqué", "success")
    return redirect(f'/billets/{bid}')


@transport_bp.route('/billets/<int:bid>/annuler', methods=['GET', 'POST'])
@_auth_required
def billets_annuler(bid):
    if not _can_validate():
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()
    c.execute("SELECT * FROM billets WHERE id=?", (bid,))
    b = c.fetchone()
    if not b:
        conn.close()
        flash("Introuvable", "danger")
        return redirect('/billets')

    if request.method == 'POST':
        motif = (request.form.get('motif') or '').strip()
        rembourse = int(request.form.get('montant_rembourse') or 0)

        c.execute("""UPDATE billets SET statut='Annulé' WHERE id=?""", (bid,))
        c.execute("""INSERT INTO annulations
            (billet_id, motif, montant_rembourse, statut, valide_par, date_validation, created_at)
            VALUES (?, ?, ?, 'Validé', ?, ?, ?)""",
            (bid, motif, rembourse, current_user.id, datetime.now().isoformat(),
             datetime.now().isoformat()))
        # Décrémenter le voyage
        c.execute("""UPDATE voyages SET
            places_vendues = MAX(0, places_vendues - 1),
            places_disponibles = places_totales - places_vendues + 1
            WHERE id=?""", (b['voyage_id'],))
        conn.commit()
        _log('BILLET_ANNULE', f"Billet {b['numero']} annulé — motif: {motif}",
             entity='billet', entity_id=bid)
        conn.close()
        flash("Billet annulé", "success")
        return redirect('/billets')

    conn.close()
    content = f"""
    <div class="page-header">
      <div><h2 style="color:#991b1b"><i class="fas fa-xmark"></i> Annuler un billet</h2></div>
      <a href="/billets/{bid}" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>
    <div class="card" style="border-left:5px solid #dc2626">
      <div style="padding:15px;background:#fee2e2;border-radius:12px;margin-bottom:20px">
        <strong style="color:#991b1b">Billet {b['numero']}</strong>
        <div>{b['passager_nom']} — {_fmt_fcfa(b['prix'])}</div>
      </div>
      <form method="POST">
        <div class="form-group">
          <label>Motif d'annulation *</label>
          <textarea name="motif" rows="3" required></textarea>
        </div>
        <div class="form-group">
          <label>Montant à rembourser (FCFA)</label>
          <input type="number" name="montant_rembourse" value="{b['prix']}">
        </div>
        <button class="btn btn-danger"><i class="fas fa-xmark"></i> Confirmer l'annulation</button>
      </form>
    </div>"""
    return _render(content, active='billets', title='Annuler billet')


@transport_bp.route('/billets/scan')
@_auth_required
def billets_scan():
    """Interface de scan/vérification des billets"""
    if not _can_operate():
        flash("Accès réservé", "danger")
        return redirect('/')

    billet_num = request.args.get('num') or ''
    billet = None
    message = None

    if billet_num:
        conn = _db()
        c = conn.cursor()
        c.execute("""SELECT b.*, vo.date_voyage, vo.heure_depart_prevue,
                            l.ville_depart, l.ville_arrivee
                     FROM billets b
                     LEFT JOIN voyages vo ON b.voyage_id = vo.id
                     LEFT JOIN lignes l ON vo.ligne_id = l.id
                     WHERE b.numero=?""", (billet_num,))
        billet = c.fetchone()
        conn.close()

        if not billet:
            message = ('danger', 'Billet inexistant !')
        elif billet['statut'] == 'Annulé':
            message = ('danger', 'Billet annulé !')
        elif billet['statut'] == 'Embarqué':
            message = ('warning', 'Billet déjà utilisé !')
        else:
            message = ('success', 'Billet valide ✓')

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-qrcode"></i> Vérification de billets</h2>
        <div class="page-subtitle">Scannez ou saisissez le numéro du billet</div></div>
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px">
        <input type="text" name="num" value="{billet_num}" placeholder="BIL-20260916-XXXXXX"
               style="flex:1;padding:14px 18px;border:2px solid #f1f5f9;border-radius:11px;font-size:1.1rem;font-family:monospace">
        <button class="btn btn-primary" style="padding:14px 28px">
          <i class="fas fa-search"></i> Vérifier
        </button>
      </form>
    </div>
    """
    if message:
        cat, msg = message
        content += f'<div class="flash flash-{cat}"><i class="fas fa-circle-info"></i> {msg}</div>'

    if billet:
        content += f"""
        <div class="card">
          <div class="form-grid">
            <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Billet</label>
                 <div style="font-weight:900;font-family:monospace">{billet['numero']}</div></div>
            <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Statut</label>
                 <div><span class="badge badge-primary">{billet['statut']}</span></div></div>
            <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Passager</label>
                 <div style="font-weight:700">{billet['passager_nom']}</div></div>
            <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Place</label>
                 <div style="font-weight:700">#{billet['numero_place'] or '-'}</div></div>
            <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Trajet</label>
                 <div>{billet['ville_depart']} → {billet['ville_arrivee']}</div></div>
            <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Date</label>
                 <div>{billet['date_voyage']} à {billet['heure_depart_prevue']}</div></div>
            <div><label style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Prix</label>
                 <div style="font-weight:900;color:#16a34a">{_fmt_fcfa(billet['prix'])}</div></div>
        </div>"""
        if billet['statut'] == 'Vendu':
            content += f"""
            <div style="margin-top:20px">
              <a href="/billets/{billet['id']}/embarquer" class="btn btn-success" style="padding:15px 30px;font-size:1.1rem">
                <i class="fas fa-check"></i> VALIDER L'EMBARQUEMENT
              </a>
            </div>"""
        content += "</div>"

    return _render(content, active='billets', title='Scan billets')


# ================================================================
# ==================== CONTRÔLE RECETTES ========================
# ================================================================
@transport_bp.route('/recettes')
@_auth_required
def recettes_list():
    if not _can_validate() and current_user.role != 'caissier':
        flash("Accès réservé", "danger")
        return redirect('/')

    date = request.args.get('date') or datetime.now().date().isoformat()

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT vo.*, l.code AS ligne_code, l.ville_depart, l.ville_arrivee,
                        v.immatriculation,
                        (SELECT COALESCE(SUM(prix), 0) FROM billets WHERE voyage_id=vo.id AND statut IN ('Vendu','Embarqué')) AS total_billets,
                        (SELECT COUNT(*) FROM billets WHERE voyage_id=vo.id AND statut IN ('Vendu','Embarqué')) AS nb_billets
                 FROM voyages vo
                 LEFT JOIN lignes l ON vo.ligne_id = l.id
                 LEFT JOIN vehicules v ON vo.vehicule_id = v.id
                 WHERE vo.date_voyage=?
                 ORDER BY vo.heure_depart_prevue""", (date,))
    voyages = c.fetchall()

    # Stats
    total_billets = sum(v['total_billets'] or 0 for v in voyages)
    total_declare = sum(v['recette_reelle'] or 0 for v in voyages)
    ecart_global = total_declare - total_billets

    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-money-bill-wave"></i> Contrôle des recettes</h2>
        <div class="page-subtitle">Vérification quotidienne — {date}</div></div>
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-ticket"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(total_billets)}</div>
        <div class="stat-label">Total billets</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-coins"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(total_declare)}</div>
        <div class="stat-label">Recette déclarée</div></div>
      <div class="stat-card {'rose' if abs(ecart_global) > 5000 else 'gold'}">
        <div class="stat-icon"><i class="fas fa-triangle-exclamation"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(ecart_global)}</div>
        <div class="stat-label">Écart global</div></div>
      <div class="stat-card purple"><div class="stat-icon"><i class="fas fa-route"></i></div>
        <div class="stat-value">{len(voyages)}</div>
        <div class="stat-label">Voyages</div></div>
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;align-items:end">
        <div class="form-group" style="flex:1;margin:0">
          <label>Date</label>
          <input type="date" name="date" value="{date}">
        </div>
        <button class="btn btn-primary"><i class="fas fa-filter"></i> Filtrer</button>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Heure</th><th>Ligne</th><th>Véhicule</th>
          <th>Billets</th><th>Recette attendue</th><th>Recette déclarée</th><th>Écart</th><th>Statut</th><th>Actions</th>
        </tr></thead><tbody>
    """
    for v in voyages:
        attendu = v['total_billets'] or 0
        declare = v['recette_reelle'] or 0
        ecart = declare - attendu
        ecart_pct = (ecart / attendu * 100) if attendu > 0 else 0

        # Statut auto
        if v['statut'] != 'Terminé':
            badge = 'badge-info'
            label = v['statut']
        elif abs(ecart_pct) < 5:
            badge = 'badge-success'
            label = 'Conforme'
        elif abs(ecart_pct) < 15:
            badge = 'badge-warning'
            label = 'Écart modéré'
        else:
            badge = 'badge-danger'
            label = 'ANOMALIE'

        content += f"""
        <tr>
          <td><strong>{v['heure_depart_prevue'] or '-'}</strong></td>
          <td>{v['ligne_code'] or '-'}
              <div style="font-size:0.72rem;color:#94a3b8">{v['ville_depart']} → {v['ville_arrivee']}</div></td>
          <td>{v['immatriculation'] or '-'}</td>
          <td><span class="badge badge-primary">{v['nb_billets']} billets</span></td>
          <td><strong>{_fmt_fcfa(attendu)}</strong></td>
          <td><strong>{_fmt_fcfa(declare)}</strong></td>
          <td>
            <span class="badge {'badge-success' if abs(ecart) < 5000 else 'badge-danger'}">
              {_fmt_fcfa(ecart)} ({ecart_pct:+.1f}%)
            </span>
          </td>
          <td><span class="badge {badge}">{label}</span></td>
          <td>
            <a href="/voyages/{v['id']}" class="btn btn-info btn-sm"><i class="fas fa-eye"></i></a>
          </td>
        </tr>"""
    if not voyages:
        content += '<tr><td colspan="9" class="empty"><i class="fas fa-money-bill-wave"></i><br>Aucun voyage</td></tr>'
    content += "</tbody></table></div></div>"
    return _render(content, active='recettes', title='Recettes')


# ================================================================
# ==================== CARBURANT ANTI-DÉTOURNEMENT ====================
# ================================================================
@transport_bp.route('/carburant')
@_auth_required
def carburant_list():
    if current_user.role not in ('admin', 'directeur', 'chef_exploitation', 'mecano'):
        flash("Accès réservé", "danger")
        return redirect('/')

    date_debut = request.args.get('debut') or (datetime.now() - timedelta(days=30)).date().isoformat()
    date_fin = request.args.get('fin') or datetime.now().date().isoformat()
    filtre = request.args.get('filtre') or ''

    conn = _db()
    c = conn.cursor()
    sql = """SELECT cb.*, v.immatriculation, v.modele,
                    ch.nom AS chauffeur_nom, ch.prenom AS chauffeur_prenom
             FROM carburant cb
             LEFT JOIN vehicules v ON cb.vehicule_id = v.id
             LEFT JOIN chauffeurs ch ON cb.chauffeur_id = ch.id
             WHERE date(cb.date_bon) BETWEEN ? AND ?"""
    params = [date_debut, date_fin]
    if filtre == 'anomalie':
        sql += " AND cb.statut='Anomalie'"
    sql += " ORDER BY cb.date_bon DESC LIMIT 200"
    c.execute(sql, params)
    carburants = c.fetchall()

    # Stats
    c.execute("""SELECT COALESCE(SUM(litres), 0) AS litres,
                        COALESCE(SUM(montant_total), 0) AS cout,
                        COUNT(*) AS nb,
                        SUM(CASE WHEN statut='Anomalie' THEN 1 ELSE 0 END) AS nb_anomalies
                 FROM carburant
                 WHERE date(date_bon) BETWEEN ? AND ?""", (date_debut, date_fin))
    stats = c.fetchone()
    conn.close()

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-gas-pump"></i> Carburant</h2>
        <div class="page-subtitle">{len(carburants)} bons — {date_debut} → {date_fin}</div></div>
      {'<a href="/carburant/nouveau" class="btn btn-primary"><i class="fas fa-plus"></i> Saisir bon</a>' if current_user.role in ('admin','directeur','chef_exploitation') else ''}
    </div>

    <div class="stats">
      <div class="stat-card"><div class="stat-icon"><i class="fas fa-gas-pump"></i></div>
        <div class="stat-value">{stats['litres']:.0f} L</div>
        <div class="stat-label">Litres totaux</div></div>
      <div class="stat-card green"><div class="stat-icon"><i class="fas fa-money-bill-wave"></i></div>
        <div class="stat-value" style="font-size:1.4rem">{_fmt_fcfa(stats['cout'])}</div>
        <div class="stat-label">Coût total</div></div>
      <div class="stat-card gold"><div class="stat-icon"><i class="fas fa-file"></i></div>
        <div class="stat-value">{stats['nb']}</div>
        <div class="stat-label">Bons carburant</div></div>
      <div class="stat-card {'rose' if stats['nb_anomalies'] > 0 else 'green'}">
        <div class="stat-icon"><i class="fas fa-triangle-exclamation"></i></div>
        <div class="stat-value">{stats['nb_anomalies']}</div>
        <div class="stat-label">Anomalies détectées</div></div>
    </div>

    <div class="card">
      <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Début</label>
          <input type="date" name="debut" value="{date_debut}">
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Fin</label>
          <input type="date" name="fin" value="{date_fin}">
        </div>
        <div class="form-group" style="flex:1;margin:0;min-width:150px">
          <label>Filtre</label>
          <select name="filtre">
            <option value="">Tous</option>
            <option value="anomalie" {"selected" if filtre=="anomalie" else ""}>Anomalies uniquement</option>
          </select>
        </div>
        <button class="btn btn-primary"><i class="fas fa-filter"></i> Filtrer</button>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Date</th><th>Véhicule</th><th>Chauffeur</th><th>Litres</th>
          <th>Montant</th><th>Conso réelle</th><th>Théorique</th><th>Écart</th><th>Statut</th>
        </tr></thead><tbody>
    """
    for cb in carburants:
        badge_c = 'badge-danger' if cb['statut'] == 'Anomalie' else 'badge-success'
        ecart = cb['ecart_pct'] or 0
        content += f"""
        <tr>
          <td><strong>{cb['date_bon']}</strong></td>
          <td>{cb['immatriculation'] or '-'}
              <div style="font-size:0.72rem;color:#94a3b8">{cb['modele'] or ''}</div></td>
          <td>{cb['chauffeur_prenom'] or ''} {cb['chauffeur_nom'] or '-'}</td>
          <td><strong>{cb['litres']} L</strong></td>
          <td>{_fmt_fcfa(cb['montant_total'])}</td>
          <td><small>{cb['consommation_calculee'] or '-'} L/100</small></td>
          <td><small>{cb['consommation_theorique'] or '-'} L/100</small></td>
          <td>
            <span class="badge {'badge-danger' if abs(ecart) > 15 else 'badge-info'}">
              {ecart:+.1f}%
            </span>
          </td>
          <td><span class="badge {badge_c}">{cb['statut']}</span></td>
        </tr>"""
    if not carburants:
        content += '<tr><td colspan="9" class="empty"><i class="fas fa-gas-pump"></i><br>Aucun bon carburant</td></tr>'
    content += "</tbody></table></div></div>"

    # Section anomalies
    anomalies = [cb for cb in carburants if cb['statut'] == 'Anomalie']
    if anomalies:
        content += """
        <div class="card" style="border-left:5px solid #dc2626">
          <div class="card-header"><h3 style="color:#991b1b"><i class="fas fa-triangle-exclamation"></i> Anomalies détectées (détournement suspecté)</h3></div>
          <p style="color:#64748b;font-size:0.85rem;margin-bottom:15px">
            Ces bons présentent un écart > 15% entre consommation réelle et théorique.
            Une vérification avec le chauffeur est recommandée.
          </p>"""
        for cb in anomalies[:5]:
            content += f"""
            <div style="padding:12px;background:#fee2e2;border-radius:10px;margin-bottom:8px">
              <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px">
                <div>
                  <strong>{cb['immatriculation']}</strong> — {cb['chauffeur_prenom']} {cb['chauffeur_nom']}
                  <div style="font-size:0.78rem;color:#991b1b">
                    {cb['date_bon']} · {cb['litres']} L · Écart {cb['ecart_pct']:+.1f}%
                  </div>
                </div>
                <div style="font-weight:900;color:#991b1b">{_fmt_fcfa(cb['montant_total'])}</div>
              </div>
            </div>"""
        content += "</div>"

    return _render(content, active='carburant', title='Carburant')


@transport_bp.route('/carburant/nouveau', methods=['GET', 'POST'])
@_auth_required
def carburant_nouveau():
    if current_user.role not in ('admin', 'directeur', 'chef_exploitation'):
        flash("Accès réservé", "danger")
        return redirect('/carburant')

    conn = _db()
    c = conn.cursor()

    if request.method == 'POST':
        vehicule_id = request.form.get('vehicule_id')
        chauffeur_id = request.form.get('chauffeur_id') or None
        date_bon = request.form.get('date_bon') or datetime.now().date().isoformat()
        litres = float(request.form.get('litres') or 0)
        prix_litre = int(request.form.get('prix_litre') or 990)
        kilometrage = int(request.form.get('kilometrage') or 0)
        station = (request.form.get('station') or '').strip()

        if not vehicule_id or litres <= 0:
            flash("Véhicule et litres obligatoires", "warning")
        else:
            try:
                # Calcul auto de la consommation théorique
                c.execute("SELECT consommation_base, kilometrage FROM vehicules WHERE id=?", (vehicule_id,))
                v = c.fetchone()
                conso_base = v['consommation_base'] or 22.0
                km_avant = v['kilometrage'] or 0
                km_parcourus = max(0, kilometrage - km_avant) if kilometrage > km_avant else 0

                conso_theorique = (km_parcourus * conso_base) / 100 if km_parcourus > 0 else 0
                conso_reelle = litres
                ecart_pct = ((conso_reelle - conso_theorique) / conso_theorique * 100) if conso_theorique > 0 else 0

                statut = 'Anomalie' if abs(ecart_pct) > 15 and conso_theorique > 0 else 'Normal'

                num_bon = f"BON-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

                c.execute("""INSERT INTO carburant
                    (numero_bon, vehicule_id, chauffeur_id, date_bon,
                     litres, prix_litre, montant_total, kilometrage, station,
                     consommation_calculee, consommation_theorique, ecart_pct, statut, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (num_bon, vehicule_id, chauffeur_id, date_bon,
                     litres, prix_litre, int(litres * prix_litre), kilometrage, station,
                     round(conso_reelle, 2), round(conso_theorique, 2),
                     round(ecart_pct, 2), statut, datetime.now().isoformat()))

                # Mettre à jour le km du véhicule
                if kilometrage > (v['kilometrage'] or 0):
                    c.execute("UPDATE vehicules SET kilometrage=? WHERE id=?",
                              (kilometrage, vehicule_id))

                conn.commit()
                _log('CREATE_CARBURANT',
                     f"Bon carburant {num_bon} — {litres}L pour véhicule id={vehicule_id}",
                     entity='carburant', entity_id=c.lastrowid)

                if statut == 'Anomalie':
                    flash(f"⚠️ Bon {num_bon} enregistré AVEC ANOMALIE (écart {ecart_pct:+.1f}%)", "warning")
                else:
                    flash(f"Bon {num_bon} enregistré ({litres}L)", "success")

                conn.close()
                return redirect('/carburant')
            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Erreur : {e}", "danger")

    c.execute("SELECT id, immatriculation, modele, kilometrage FROM vehicules WHERE actif=1 ORDER BY immatriculation")
    vehicules = c.fetchall()
    c.execute("SELECT id, nom, prenom, matricule FROM chauffeurs WHERE actif=1 ORDER BY nom")
    chauffeurs = c.fetchall()
    conn.close()

    opt_v = ''.join(f'<option value="{v["id"]}" data-km="{v["kilometrage"] or 0}">{v["immatriculation"]} — {v["modele"] or ""}</option>' for v in vehicules)
    opt_c = ''.join(f'<option value="{ch["id"]}">{ch["prenom"]} {ch["nom"]}</option>' for ch in chauffeurs)

    content = f"""
    <div class="page-header">
      <div><h2><i class="fas fa-gas-pump"></i> Nouveau bon carburant</h2>
        <div class="page-subtitle">Détection automatique des anomalies</div></div>
      <a href="/carburant" class="btn btn-info"><i class="fas fa-arrow-left"></i> Retour</a>
    </div>

    <div class="card">
      <form method="POST" id="carb-form">
        <div class="form-grid">
          <div class="form-group form-full">
            <label>Véhicule *</label>
            <select name="vehicule_id" id="vehicule_select" required>
              <option value="">— Choisir —</option>{opt_v}
            </select>
          </div>
          <div class="form-group">
            <label>Chauffeur</label>
            <select name="chauffeur_id"><option value="">—</option>{opt_c}</select>
          </div>
          <div class="form-group">
            <label>Date *</label>
            <input type="date" name="date_bon" value="{datetime.now().date().isoformat()}" required>
          </div>
          <div class="form-group">
            <label>Litres *</label>
            <input type="number" step="0.1" name="litres" id="litres" required value="80">
          </div>
          <div class="form-group">
            <label>Prix au litre (FCFA)</label>
            <input type="number" name="prix_litre" value="990">
          </div>
          <div class="form-group">
            <label>Kilométrage actuel</label>
            <input type="number" name="kilometrage" id="km_input" value="0">
          </div>
          <div class="form-group">
            <label>Station</label>
            <input type="text" name="station" placeholder="Total, Shell, Petro Sen...">
          </div>
        </div>

        <div id="preview" style="margin:20px 0;padding:20px;background:linear-gradient(135deg,#f0fdff,#cffafe);border-radius:12px;border-left:5px solid #06b6d4;display:none">
          <div style="display:flex;gap:30px;flex-wrap:wrap;align-items:center">
            <div>
              <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Litres</div>
              <div id="pv_litres" style="font-size:1.8rem;font-weight:900;color:#0e7490">0 L</div>
            </div>
            <div>
              <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">Montant</div>
              <div id="pv_montant" style="font-size:1.4rem;font-weight:800;color:#16a34a">0 F</div>
            </div>
            <div>
              <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800">KM parcourus</div>
              <div id="pv_km" style="font-size:1.2rem;font-weight:700;color:#06b6d4">-</div>
            </div>
          </div>
        </div>

        <button class="btn btn-primary" style="margin-top:20px"><i class="fas fa-check"></i> Enregistrer le bon</button>
      </form>
    </div>

    <script>
    const vSelect = document.getElementById('vehicule_select');
    const litres = document.getElementById('litres');
    const kmInput = document.getElementById('km_input');
    const prixInput = document.querySelector('input[name="prix_litre"]');
    const preview = document.getElementById('preview');

    let km_initial = 0;

    function updatePreview() {{
      const l = parseFloat(litres.value) || 0;
      const p = parseFloat(prixInput.value) || 0;
      const km = parseFloat(kmInput.value) || 0;

      if (l <= 0) {{ preview.style.display = 'none'; return; }}
      preview.style.display = 'block';

      document.getElementById('pv_litres').textContent = l + ' L';
      document.getElementById('pv_montant').textContent = new Intl.NumberFormat('fr-FR').format(Math.round(l * p)) + ' F';

      if (km > 0 && km_initial > 0) {{
        const diff = km - km_initial;
        const cible = document.getElementById('pv_km');
        cible.textContent = diff + ' km';
        if (diff > 0) {{
          const consoTheo = (diff * 22) / 100;
          const ecart = ((l - consoTheo) / consoTheo * 100);
          if (Math.abs(ecart) > 15) {{
            cible.style.color = '#dc2626';
            cible.textContent = diff + ' km (⚠️ écart ' + ecart.toFixed(1) + '%)';
          }} else {{
            cible.style.color = '#10b981';
          }}
        }}
      }}
    }}

    vSelect.addEventListener('change', () => {{
      const opt = vSelect.options[vSelect.selectedIndex];
      km_initial = parseFloat(opt.dataset.km) || 0;
      kmInput.value = km_initial;
      updatePreview();
    }});

    litres.addEventListener('input', updatePreview);
    kmInput.addEventListener('input', updatePreview);
    prixInput.addEventListener('input', updatePreview);
    </script>
    """
    return _render(content, active='carburant', title='Nouveau bon carburant')


# ================================================================
# ==================== FEUILLE DE ROUTE ====================
# ================================================================
@transport_bp.route('/voyages/<int:vid>/feuille-route')
@_auth_required
def voyages_feuille_route(vid):
    if not _can_operate():
        flash("Accès réservé", "danger")
        return redirect('/')

    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT vo.*, l.code AS ligne_code, l.nom AS ligne_nom,
                        l.ville_depart, l.ville_arrivee, l.distance_km, l.duree_minutes,
                        v.immatriculation, v.modele, v.capacite_places,
                        ch.nom AS chauffeur_nom, ch.prenom AS chauffeur_prenom, ch.telephone AS ch_tel,
                        ch.numero_permis
                 FROM voyages vo
                 LEFT JOIN lignes l ON vo.ligne_id = l.id
                 LEFT JOIN vehicules v ON vo.vehicule_id = v.id
                 LEFT JOIN chauffeurs ch ON vo.chauffeur_id = ch.id
                 WHERE vo.id=?""", (vid,))
    v = c.fetchone()
    if not v:
        conn.close()
        flash("Voyage introuvable", "danger")
        return redirect('/voyages')

    c.execute("""SELECT numero, passager_nom, passager_telephone, numero_place, classe, prix, mode_paiement
                 FROM billets WHERE voyage_id=? AND statut IN ('Vendu','Embarqué')
                 ORDER BY numero_place""", (vid,))
    billets = c.fetchall()
    conn.close()

    total_billets = sum(b['prix'] for b in billets)

    html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Feuille de route — {v['numero']}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}}
body{{padding:30px;background:white;color:#0e7490}}
.header{{text-align:center;border-bottom:3px solid #06b6d4;padding-bottom:20px;margin-bottom:30px}}
.header h1{{font-size:1.8rem;font-weight:900;color:#0e7490;letter-spacing:-0.5px}}
.header .ref{{font-size:0.85rem;color:#64748b;margin-top:6px;font-family:monospace}}
.info-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:30px}}
.info-block{{background:#f0fdff;padding:15px;border-radius:10px;border-left:4px solid #06b6d4}}
.info-block h3{{font-size:0.75rem;color:#64748b;text-transform:uppercase;font-weight:800;margin-bottom:8px}}
.info-block .val{{font-size:1.05rem;font-weight:700;color:#0e7490}}
table{{width:100%;border-collapse:collapse;margin-top:20px}}
th,td{{padding:10px;border:1px solid #cffafe;text-align:left;font-size:0.85rem}}
th{{background:#cffafe;font-weight:800;text-transform:uppercase;font-size:0.72rem}}
.total{{text-align:right;margin-top:20px;font-size:1.2rem;font-weight:900;color:#0e7490}}
.footer{{margin-top:40px;padding-top:20px;border-top:2px dashed #cffafe;display:flex;justify-content:space-between;font-size:0.8rem;color:#64748b}}
.signature{{margin-top:50px;display:grid;grid-template-columns:1fr 1fr;gap:60px}}
.signature-box{{border-top:2px solid #0e7490;padding-top:10px;text-align:center;font-size:0.8rem}}
@media print {{
  body{{padding:10px}}
  .no-print{{display:none}}
}}
</style>
</head>
<body>
<div class="no-print" style="text-align:right;margin-bottom:20px">
  <button onclick="window.print()" style="padding:12px 24px;background:linear-gradient(135deg,#0e7490,#06b6d4);color:white;border:none;border-radius:10px;font-weight:700;cursor:pointer">
    🖨️ Imprimer
  </button>
  <a href="/voyages/{vid}" style="margin-left:10px;padding:12px 24px;background:#64748b;color:white;text-decoration:none;border-radius:10px;font-weight:700">← Retour</a>
</div>

<div class="header">
  <h1>OMEGA TRANSPORT — FEUILLE DE ROUTE</h1>
  <div class="ref">Voyage {v['numero']} · Édité le {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
</div>

<div class="info-grid">
  <div class="info-block">
    <h3>Ligne</h3>
    <div class="val">{v['ligne_code']} — {v['ville_depart']} → {v['ville_arrivee']}</div>
  </div>
  <div class="info-block">
    <h3>Date & Heure</h3>
    <div class="val">{v['date_voyage']} à {v['heure_depart_prevue'] or '-'}</div>
  </div>
  <div class="info-block">
    <h3>Véhicule</h3>
    <div class="val">{v['immatriculation']} ({v['modele'] or '-'}) — {v['capacite_places']} places</div>
  </div>
  <div class="info-block">
    <h3>Chauffeur</h3>
    <div class="val">{v['chauffeur_prenom'] or ''} {v['chauffeur_nom'] or '-'}</div>
    <div style="font-size:0.75rem;color:#64748b;margin-top:4px">
      Tél: {v['ch_tel'] or '-'} · Permis: {v['numero_permis'] or '-'}
    </div>
  </div>
  <div class="info-block">
    <h3>Distance</h3>
    <div class="val">{v['distance_km']} km · {v['duree_minutes']} min</div>
  </div>
  <div class="info-block">
    <h3>Occupation</h3>
    <div class="val">{v['places_vendues']}/{v['places_totales']} places</div>
  </div>
</div>

<h2 style="font-size:1.1rem;margin-bottom:10px;color:#0e7490">
  Liste des passagers ({len(billets)})
</h2>
<table>
  <thead>
    <tr>
      <th>N° Place</th>
      <th>N° Billet</th>
      <th>Nom passager</th>
      <th>Téléphone</th>
      <th>Classe</th>
      <th>Prix</th>
      <th>Paiement</th>
      <th>Émargement</th>
    </tr>
  </thead>
  <tbody>
"""
    for b in billets:
        html += f"""
    <tr>
      <td><strong>#{b['numero_place'] or '-'}</strong></td>
      <td><small>{b['numero']}</small></td>
      <td>{b['passager_nom']}</td>
      <td>{b['passager_telephone'] or ''}</td>
      <td>{b['classe']}</td>
      <td>{_fmt_fcfa(b['prix'])}</td>
      <td>{b['mode_paiement']}</td>
      <td style="width:100px"></td>
    </tr>"""
    html += f"""
  </tbody>
</table>

<div class="total">
  Total recette billets : {_fmt_fcfa(total_billets)}
</div>

<div class="signature">
  <div class="signature-box">Signature Chauffeur<br><br><br></div>
  <div class="signature-box">Visa Contrôleur<br><br><br></div>
</div>

<div class="footer">
  <div>Omega Transport V2 — Feuille de route générée automatiquement</div>
  <div>{v['numero']}</div>
</div>

</body>
</html>
"""
    return Response(html, mimetype='text/html')


# ================================================================
# ==================== API ====================
# ================================================================
@transport_bp.route('/api/voyage/<int:vid>/billets')
@_auth_required
def api_voyage_billets(vid):
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT id, numero, passager_nom, numero_place, prix, statut
                 FROM billets WHERE voyage_id=? ORDER BY numero_place""", (vid,))
    rows = c.fetchall()
    conn.close()
    return jsonify(billets=[dict(r) for r in rows])


@transport_bp.route('/api/carburant/stats')
@_auth_required
def api_carburant_stats():
    conn = _db()
    c = conn.cursor()
    c.execute("""SELECT COUNT(*) AS nb,
                        COALESCE(SUM(litres), 0) AS litres,
                        COALESCE(SUM(montant_total), 0) AS cout,
                        SUM(CASE WHEN statut='Anomalie' THEN 1 ELSE 0 END) AS anomalies
                 FROM carburant
                 WHERE strftime('%Y-%m', date_bon)=strftime('%Y-%m', 'now')""")
    r = c.fetchone()
    conn.close()
    return jsonify(mois=datetime.now().strftime('%Y-%m'), nb_bons=r['nb'],
                   litres=r['litres'], cout=r['cout'], anomalies=r['anomalies'])
