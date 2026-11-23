"""
Cache QR codes — Évite la regénération à chaque requête
"""
import os
import sqlite3
import qrcode
import io
import hashlib

CACHE_DIR = "/app/data/qrcodes"
DB_PATH = "/app/data/pointage_v2.db"

os.makedirs(CACHE_DIR, exist_ok=True)


def get_qr_image_bytes(employe_id):
    """Retourne les bytes PNG du QR code, avec cache"""
    cache_path = os.path.join(CACHE_DIR, f"emp_{employe_id}.png")

    # 1. Vérifier le cache
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                return f.read(), True  # depuis cache
        except Exception:
            pass

    # 2. Générer et mettre en cache
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT qr_code_data FROM employes WHERE id=?", (employe_id,))
        r = c.fetchone()
        conn.close()

        if not r or not r['qr_code_data']:
            return None, False

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=3,
        )
        qr.add_data(r['qr_code_data'])
        qr.make(fit=True)

        img = qr.make_image(fill_color="#0e7490", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        data = buf.getvalue()

        # Sauvegarder dans le cache
        try:
            with open(cache_path, 'wb') as f:
                f.write(data)
        except Exception:
            pass

        return data, False
    except Exception as e:
        print(f"[QR CACHE] Erreur: {e}")
        return None, False


def clear_cache(employe_id=None):
    """Vide le cache (pour un employé ou tout)"""
    import glob
    if employe_id:
        path = os.path.join(CACHE_DIR, f"emp_{employe_id}.png")
        if os.path.exists(path):
            os.remove(path)
    else:
        for f in glob.glob(os.path.join(CACHE_DIR, "emp_*.png")):
            try:
                os.remove(f)
            except Exception:
                pass
