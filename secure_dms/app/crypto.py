"""
Envelope encryption:
  - Each file gets its own random Data Encryption Key (DEK), AES-256-GCM.
  - The DEK itself is encrypted ("wrapped") by a single MASTER_KEY (Fernet),
    which lives only in .env / server environment, never in the database.
  - A database leak alone exposes only wrapped DEKs and ciphertext,
    both useless without MASTER_KEY.
"""
import os
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .config import MASTER_KEY

_master_fernet = Fernet(MASTER_KEY)


def hash_bytes(data: bytes) -> str:
    """SHA-256 of plaintext -- the 'legal' hash proving original content."""
    return hashlib.sha256(data).hexdigest()


def encrypt_file(plaintext: bytes):
    """Returns (ciphertext, nonce, encrypted_dek)."""
    dek = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    aesgcm = AESGCM(dek)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    encrypted_dek = _master_fernet.encrypt(dek)
    return ciphertext, nonce, encrypted_dek


def decrypt_file(ciphertext: bytes, nonce: bytes, encrypted_dek: bytes) -> bytes:
    dek = _master_fernet.decrypt(encrypted_dek)
    aesgcm = AESGCM(dek)
    return aesgcm.decrypt(nonce, ciphertext, None)
