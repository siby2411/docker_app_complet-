"""Communication : SMS (Orange/Wave) + Email SMTP"""
import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import requests

DB_PATH = "/app/data/ecole.db"


def get_db():
    os.makedirs("/app/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_config(cle, default=""):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT valeur FROM config_communication WHERE cle=?", (cle,))
        row = c.fetchone()
        conn.close()
        return row['valeur'] if row and row['valeur'] else default
    except Exception:
        return default


def log_notification(type_notif, destinataire, contenu, sujet=None,
                     etudiant_id=None, statut="En attente", provider=None,
                     erreur=None, reference=None):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""INSERT INTO notifications
            (type, destinataire, sujet, contenu, etudiant_id, statut, provider, erreur, reference)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (type_notif, destinataire, sujet, contenu, etudiant_id,
             statut, provider, erreur, reference))
        nid = c.lastrowid
        conn.commit()
        conn.close()
        return nid
    except Exception as e:
        print(f"[NOTIF] {e}")
        return None


def envoyer_sms(destinataire, message, etudiant_id=None):
    provider = get_config("sms_provider", "simulation")

    if provider == "simulation":
        print(f"[SMS SIM] → {destinataire}: {message}")
        log_notification("SMS", destinataire, message, etudiant_id=etudiant_id,
                        statut="Envoyé", provider="simulation",
                        reference=f"SIM-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        return True, "Simulation OK"

    if provider == "orange":
        api_key = get_config("sms_api_key")
        if not api_key:
            log_notification("SMS", destinataire, message, etudiant_id=etudiant_id,
                            statut="Échec", provider="orange", erreur="API key manquante")
            return False, "API key Orange manquante"
        try:
            url = "https://api.orange.com/smsmessaging/v1/outbound/tel%3A%2B2210000/requests"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"outboundSMSMessageRequest": {
                "address": f"tel:+221{destinataire.lstrip('+').lstrip('221')}",
                "senderAddress": "tel:+2210000",
                "outboundSMSTextMessage": {"message": message}}}
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code in (200, 201):
                log_notification("SMS", destinataire, message, etudiant_id=etudiant_id,
                                statut="Envoyé", provider="orange")
                return True, "SMS envoyé"
            log_notification("SMS", destinataire, message, etudiant_id=etudiant_id,
                            statut="Échec", provider="orange", erreur=f"HTTP {r.status_code}")
            return False, f"Erreur Orange {r.status_code}"
        except Exception as e:
            log_notification("SMS", destinataire, message, etudiant_id=etudiant_id,
                            statut="Échec", provider="orange", erreur=str(e))
            return False, str(e)

    log_notification("SMS", destinataire, message, etudiant_id=etudiant_id,
                    statut="Échec", provider=provider, erreur="Provider inconnu")
    return False, f"Provider inconnu : {provider}"


def envoyer_email(destinataire, sujet, contenu_html, contenu_texte=None, etudiant_id=None):
    host = get_config("email_smtp_host", "")
    port = int(get_config("email_smtp_port", "587"))
    user = get_config("email_smtp_user", "")
    pwd = get_config("email_smtp_pass", "")
    from_addr = get_config("email_from", "noreply@omega.sn")

    if not host or not user or not pwd:
        print(f"[EMAIL SIM] → {destinataire}: {sujet}")
        log_notification("EMAIL", destinataire, contenu_html, sujet=sujet,
                        etudiant_id=etudiant_id, statut="Envoyé", provider="simulation")
        return True, "Simulation OK"

    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = sujet
        msg['From'] = from_addr
        msg['To'] = destinataire
        if contenu_texte:
            msg.attach(MIMEText(contenu_texte, 'plain', 'utf-8'))
        msg.attach(MIMEText(contenu_html, 'html', 'utf-8'))

        srv = smtplib.SMTP(host, port, timeout=15)
        srv.starttls()
        srv.login(user, pwd)
        srv.send_message(msg)
        srv.quit()

        log_notification("EMAIL", destinataire, contenu_html, sujet=sujet,
                        etudiant_id=etudiant_id, statut="Envoyé", provider="smtp")
        return True, "Email envoyé"
    except Exception as e:
        log_notification("EMAIL", destinataire, contenu_html, sujet=sujet,
                        etudiant_id=etudiant_id, statut="Échec", provider="smtp", erreur=str(e))
        return False, str(e)


def notifier_absence(etudiant_id, date_presence, matiere_nom, statut):
    if get_config("notif_absence", "1") != "1":
        return False, "Désactivé"
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT nom, prenom, matricule, telephone_parent, email_parent,
        telephone, email FROM etudiants WHERE id=?""", (etudiant_id,))
    e = c.fetchone()
    conn.close()
    if not e:
        return False, "Étudiant introuvable"

    msg = (f"OMEGA ECOLE : Votre enfant {e['nom']} {e['prenom']} "
           f"({e['matricule']}) a été marqué(e) {statut} en {matiere_nom} "
           f"le {date_presence}. Merci de justifier.")

    tel = e['telephone_parent'] or e['telephone']
    mail = e['email_parent'] or e['email']

    if tel:
        envoyer_sms(tel, msg, etudiant_id)
    if mail:
        html = f"""<html><body style="font-family:Arial; padding:20px;">
        <h2 style="color:#e94560;">OMEGA ECOLE — Notification</h2>
        <p>Votre enfant <strong>{e['nom']} {e['prenom']}</strong>
        ({e['matricule']}) a été marqué(e) <strong>{statut}</strong>
        en <strong>{matiere_nom}</strong> le <strong>{date_presence}</strong>.</p>
        <p>Merci de justifier auprès de l'administration.</p>
        </body></html>"""
        envoyer_email(mail, "Notification absence", html, etudiant_id=etudiant_id)

    return True, "OK"


def notifier_paiement(etudiant_id, montant, mois, statut_paiement):
    if get_config("notif_paiement", "1") != "1":
        return False, "Désactivé"
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT nom, prenom, matricule, telephone_parent, email_parent,
        telephone, email FROM etudiants WHERE id=?""", (etudiant_id,))
    e = c.fetchone()
    conn.close()
    if not e:
        return False, "Étudiant introuvable"

    emoji = "OK" if statut_paiement == "Payé" else "EN ATTENTE"
    msg = (f"OMEGA ECOLE : Paiement {emoji} - {e['matricule']} {e['nom']} {e['prenom']} : "
           f"{montant:,.0f} FCFA pour {mois}.")

    tel = e['telephone_parent'] or e['telephone']
    mail = e['email_parent'] or e['email']
    if tel:
        envoyer_sms(tel, msg, etudiant_id)
    if mail:
        html = f"""<html><body style="font-family:Arial; padding:20px;">
        <h2 style="color:{'#2ecc71' if statut_paiement=='Payé' else '#f39c12'};">Paiement {statut_paiement}</h2>
        <p><strong>{e['nom']} {e['prenom']}</strong> ({e['matricule']})</p>
        <p>Montant : {montant:,.0f} FCFA — Mois : {mois}</p>
        </body></html>"""
        envoyer_email(mail, f"Paiement {statut_paiement}", html, etudiant_id=etudiant_id)
    return True, "OK"


def notifier_notes_publiees(classe_id, semestre_id):
    if get_config("notif_notes", "1") != "1":
        return False, "Désactivé"
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT e.id, e.nom, e.prenom, e.matricule,
        e.telephone_parent, email_parent, telephone, email,
        (SELECT SUM(n.note_finale * m.coefficient) / SUM(m.coefficient)
         FROM notes n JOIN matieres m ON n.matiere_id=m.id
         WHERE n.etudiant_id=e.id AND n.semestre_id=? AND n.note_finale IS NOT NULL) as moyenne
        FROM etudiants e WHERE e.classe_id=? AND e.statut='Actif'""",
        (semestre_id, classe_id))
    etudiants = c.fetchall()
    conn.close()

    count = 0
    for e in etudiants:
        moy = round(e['moyenne'], 2) if e['moyenne'] else 'N/A'
        msg = (f"OMEGA ECOLE : Notes disponibles pour {e['nom']} {e['prenom']} "
               f"({e['matricule']}). Moyenne : {moy}/20.")
        tel = e['telephone_parent'] or e['telephone']
        if tel:
            envoyer_sms(tel, msg, e['id'])
            count += 1
    return True, f"{count} notifications"
