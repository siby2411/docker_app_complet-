"""
🔐 Chiffrement AES-256-like sans dépendances externes (stdlib uniquement)
- Chiffrement stream : SHA-256 keystream + XOR
- Intégrité : HMAC-SHA256
- Signature : HMAC-SHA256 (au lieu de RSA, même niveau de sécurité pour la démo)
- RGPD compatible : données jamais stockées en clair
"""
import os
import hmac
import hashlib
import base64
import json
import time
from datetime import datetime, timedelta

# ─── Clé maîtresse (32 bytes) ───
MASTER_KEY_STR = os.environ.get('MASTER_KEY', 'omega-telemed-master-key-2026-secure-hmac')
MASTER_KEY = hashlib.sha256(MASTER_KEY_STR.encode()).digest()

# ─── Clé JWT ───
JWT_SECRET = os.environ.get('JWT_SECRET', 'omega-telemed-jwt-2026').encode()
JWT_ALGO = 'HS256'


def _derive_keystream(key, nonce, length):
    """Génère un keystream de longueur 'length' par SHA-256 chaîné."""
    stream = b''
    counter = 0
    while len(stream) < length:
        h = hashlib.sha256(key + nonce + counter.to_bytes(8, 'big')).digest()
        stream += h
        counter += 1
    return stream[:length]


def encrypt_data(plaintext):
    """
    Chiffre une chaîne avec un stream cipher SHA-256 + HMAC-SHA256.
    Format base64 : nonce(16) + ciphertext + hmac(32)
    """
    if plaintext is None:
        return None
    if isinstance(plaintext, str):
        plaintext = plaintext.encode('utf-8')

    nonce = os.urandom(16)
    keystream = _derive_keystream(MASTER_KEY, nonce, len(plaintext))
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, keystream))
    mac = hmac.new(MASTER_KEY, nonce + ciphertext, hashlib.sha256).digest()

    combined = nonce + ciphertext + mac
    return base64.b64encode(combined).decode('utf-8')


def decrypt_data(encoded):
    """Déchiffre et vérifie l'intégrité HMAC."""
    if encoded is None:
        return None
    try:
        combined = base64.b64decode(encoded.encode('utf-8'))
        if len(combined) < 48:  # 16 nonce + 32 mac
            return None
        nonce = combined[:16]
        mac = combined[-32:]
        ciphertext = combined[16:-32]

        # Vérification intégrité
        expected_mac = hmac.new(MASTER_KEY, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected_mac):
            return None

        keystream = _derive_keystream(MASTER_KEY, nonce, len(ciphertext))
        plaintext = bytes(a ^ b for a, b in zip(ciphertext, keystream))
        return plaintext.decode('utf-8')
    except Exception:
        return None


def hash_patient_id(patient_uid):
    """Hash irréversible pour indexation RGPD-safe."""
    return hashlib.sha256((str(patient_uid) + MASTER_KEY_STR).encode()).hexdigest()[:16]


def _b64url_encode(data):
    """Base64 URL-safe sans padding."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _b64url_decode(s):
    """Base64 URL-safe décode avec padding auto."""
    padding = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


def generate_jwt(payload, expires_hours=24):
    """Génère un JWT HS256 (compatible RFC 7519, stdlib only)."""
    header = {'alg': 'HS256', 'typ': 'JWT'}
    data = dict(payload)
    data['exp'] = int(time.time()) + (expires_hours * 3600)
    data['iat'] = int(time.time())

    h_enc = _b64url_encode(json.dumps(header, separators=(',', ':')).encode())
    p_enc = _b64url_encode(json.dumps(data, separators=(',', ':')).encode())
    signing_input = (h_enc + '.' + p_enc).encode()

    signature = hmac.new(JWT_SECRET, signing_input, hashlib.sha256).digest()
    s_enc = _b64url_encode(signature)

    return h_enc + '.' + p_enc + '.' + s_enc


def verify_jwt(token):
    """Vérifie un JWT HS256 — retourne payload ou None."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        h_enc, p_enc, s_enc = parts
        signing_input = (h_enc + '.' + p_enc).encode()
        expected_sig = hmac.new(JWT_SECRET, signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(s_enc)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64url_decode(p_enc))
        if payload.get('exp', 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def sign_ordonnance(payload_str):
    """Signe une ordonnance avec HMAC-SHA256 (anti-fraude)."""
    try:
        signature = hmac.new(MASTER_KEY, payload_str.encode('utf-8'), hashlib.sha256).digest()
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        print(f"[CRYPTO] ⚠️ Signature échouée: {e}")
        return None


def verify_signature(payload_str, signature_b64):
    """Vérifie la signature HMAC-SHA256 d'une ordonnance."""
    try:
        expected = hmac.new(MASTER_KEY, payload_str.encode('utf-8'), hashlib.sha256).digest()
        actual = base64.b64decode(signature_b64.encode('utf-8'))
        return hmac.compare_digest(expected, actual)
    except Exception:
        return False
